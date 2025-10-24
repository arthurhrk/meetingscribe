#!/usr/bin/env python3
"""
Quick Record - Inicia gravação e mantém processo vivo

Fluxo:
1. Parse argumentos
2. Gera timestamp e filepath
3. IMPRIME JSON IMEDIATAMENTE (Raycast recebe e mostra sucesso)
4. Importa módulos (audio_recorder)
5. Inicia gravação (loopback); se não houver frames após 1s, tenta microfone
6. Aguarda completar e salva
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime


def main():
    # Parse args
    duration = 30
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except Exception:
            pass

    # Gerar identificadores
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.wav"
    filepath = Path("storage/recordings") / filename

    # RETORNAR JSON IMEDIATAMENTE - antes de imports pesados!
    result = {
        "status": "success",
        "data": {
            "session_id": f"quick-{timestamp}",
            "file_path": str(filepath),
            "duration": duration,
        },
    }
    print(json.dumps(result), flush=True)

    # Agora fazer imports pesados e iniciar gravação
    try:
        from audio_recorder import AudioRecorder
        from device_manager import DeviceManager

        # Loopback primeiro
        recorder = AudioRecorder()
        success = recorder.set_device_auto()
        if not success:
            sys.exit(1)

        if duration:
            recorder._config.max_duration = duration

        recorder.start_recording(filename=filename)

        # Checagem após 1s: se não há frames, tentar microfone padrão
        time.sleep(1.0)
        try:
            has_frames = len(recorder._frames) > 0
        except Exception:
            has_frames = False

        if not has_frames:
            try:
                recorder.close()
                # Fallback para microfone
                rec2 = AudioRecorder()
                with DeviceManager() as dm:
                    mic = dm.get_system_default_input() or next(
                        (d for d in dm.get_recording_capable_devices() if not d.is_loopback),
                        None,
                    )
                if mic is None:
                    sys.exit(1)

                # Reconfigurar gravador com microfone
                # Reutiliza RecordingConfig dataclass do gravador
                from audio_recorder import RecordingConfig

                rec2._config = RecordingConfig(
                    device=mic,
                    sample_rate=int(mic.default_sample_rate or 16000),
                    channels=min(mic.max_input_channels or 1, 2),
                )
                if duration:
                    rec2._config.max_duration = duration
                rec2.start_recording(filename=filename)
                recorder = rec2
            except Exception:
                # Se falhar fallback, continua com loopback mesmo assim
                pass

        # Manter vivo até completar
        # (já consideramos 1s acima caso fallback) 
        remaining = max(0, duration + 3 - 1)
        time.sleep(remaining)

        # Finalizar e fechar
        try:
            if recorder.is_recording():
                recorder.stop_recording()
        except Exception:
            pass
        finally:
            try:
                recorder.close()
            except Exception:
                pass

    except Exception:
        # Já imprimimos JSON de sucesso; sair silenciosamente
        sys.exit(1)


if __name__ == "__main__":
    main()

