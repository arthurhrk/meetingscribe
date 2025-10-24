#!/usr/bin/env python3
"""
GRAVADOR PARA RAYCAST - Versão melhorada
Usa threading para continuar gravação após retornar JSON
"""
import sys
import json
import time
import threading
from datetime import datetime
from pathlib import Path

def record_audio(duration: int, filename: str, filepath: Path):
    """Thread worker que grava o áudio"""
    try:
        from audio_recorder import AudioRecorder

        recorder = AudioRecorder()
        success = recorder.set_device_auto()
        if not success:
            return

        recorder._config.max_duration = duration
        recorder.start_recording(filename=filename)

        # Aguardar gravação completar
        time.sleep(duration + 2)

        # Salvar forçado
        if recorder._frames:
            import wave
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with wave.open(str(filepath), 'wb') as wav_file:
                wav_file.setnchannels(recorder._config.channels)
                wav_file.setsampwidth(recorder._audio.get_sample_size(recorder._config.format))
                wav_file.setframerate(recorder._config.sample_rate)
                wav_file.writeframes(b''.join(recorder._frames))

        recorder.close()
    except Exception as e:
        # Log error but don't crash
        with open('storage/logs/raycast_error.log', 'a') as f:
            f.write(f"{datetime.now()}: {str(e)}\n")

def main():
    # Parse args
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    # Gerar identificadores
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.wav"
    filepath = Path("storage/recordings") / filename

    # RETORNAR JSON IMEDIATAMENTE
    result = {
        "status": "success",
        "data": {
            "session_id": f"rec-{timestamp}",
            "file_path": str(filepath).replace("/", "\\"),
            "duration": duration
        }
    }
    print(json.dumps(result), flush=True)

    # Iniciar gravação em thread NON-DAEMON
    # Non-daemon threads mantém o processo vivo até completarem
    thread = threading.Thread(
        target=record_audio,
        args=(duration, filename, filepath),
        daemon=False  # CRITICAL: must not be daemon
    )
    thread.start()

    # Manter processo vivo até thread completar
    thread.join()

if __name__ == "__main__":
    main()
