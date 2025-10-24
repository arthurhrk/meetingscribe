#!/usr/bin/env python3
"""
Quick Record - Inicia gravação e mantém processo vivo (Raycast)

Fluxo:
1) Lê args (duração e --input)
2) Imprime JSON imediatamente (Raycast mostra feedback já)
3) Importa módulos pesados
4) Grava via loopback/mic conforme modo
5) Salva WAV ao final

Uso:
  python quick_record.py 30 --input auto|mic|loopback
  (padrão: auto)
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime


def _parse_input_mode(argv):
    mode = "auto"
    for i, a in enumerate(argv):
        if a.startswith("--input="):
            mode = a.split("=", 1)[1].strip().lower() or mode
        elif a == "--input" and i + 1 < len(argv):
            mode = argv[i + 1].strip().lower() or mode
    if mode not in {"auto", "mic", "loopback"}:
        mode = "auto"
    return mode


def main():
    # Parse args
    duration = 30
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except Exception:
            pass
    input_mode = _parse_input_mode(sys.argv[2:])

    # Identificadores
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.wav"
    filepath = Path("storage/recordings") / filename

    # JSON imediato
    print(
        json.dumps(
            {
                "status": "success",
                "data": {
                    "session_id": f"rec-{timestamp}",
                    "file_path": str(filepath),
                    "filename": filename,
                    "duration": duration,
                    "input_mode": input_mode,
                },
            }
        ),
        flush=True,
    )

    # Gravação
    try:
        from audio_recorder import AudioRecorder
        from device_manager import DeviceManager
        from audio_recorder import RecordingConfig

        def build_mic_recorder():
            rec2 = AudioRecorder()
            with DeviceManager() as dm:
                mic = dm.get_system_default_input() or next(
                    (d for d in dm.get_recording_capable_devices() if not d.is_loopback), None
                )
            if mic is None:
                return None
            rec2._config = RecordingConfig(
                device=mic,
                sample_rate=int(getattr(mic, "default_sample_rate", 16000) or 16000),
                channels=min(getattr(mic, "max_input_channels", 1) or 1, 2),
            )
            rec2._config.max_duration = duration
            return rec2

        recorder = None
        if input_mode == "mic":
            recorder = build_mic_recorder()
            if recorder is None:
                return
        else:
            # loopback ou auto
            recorder = AudioRecorder()
            success = recorder.set_device_auto()
            if not success:
                if input_mode == "loopback":
                    return
                recorder = build_mic_recorder()
                if recorder is None:
                    return

        recorder.start_recording(filename=filename)

        # No modo auto, se loopback não gera frames, tentar mic
        if input_mode == "auto":
            time.sleep(1.0)
            try:
                has_frames = len(recorder._frames) > 0
            except Exception:
                has_frames = False
            if not has_frames:
                try:
                    recorder.close()
                    recorder = build_mic_recorder()
                    if recorder is None:
                        return
                    recorder.start_recording(filename=filename)
                except Exception:
                    pass

        # Aguardar completar (buffer extra de 2s)
        time.sleep(duration + 2)
        if recorder.is_recording():
            try:
                recorder.stop_recording()
            except Exception:
                pass
        try:
            recorder.close()
        except Exception:
            pass

    except Exception:
        # JSON já foi enviado; falhar silenciosamente
        pass


if __name__ == "__main__":
    main()
