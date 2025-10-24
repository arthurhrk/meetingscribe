#!/usr/bin/env python3
"""
Record Worker - Processo worker que executa a gravação
Este script roda em background e mantém o processo vivo até completar
"""

import sys
import time
from pathlib import Path

def main():
    """Worker que mantém gravação rodando"""
    if len(sys.argv) < 4:
        sys.exit(1)

    duration = int(sys.argv[1])
    timestamp = sys.argv[2]
    filename = sys.argv[3]

    try:
        from audio_recorder import AudioRecorder
        from loguru import logger

        # Criar gravador
        recorder = AudioRecorder()

        # Auto-detect device
        success = recorder.set_device_auto()
        if not success:
            logger.error("Failed to auto-detect device")
            sys.exit(1)

        # Configurar duração
        if duration:
            recorder._config.max_duration = duration

        # Iniciar gravação
        filepath = recorder.start_recording(filename=filename)
        logger.info(f"Worker: Recording started - {filepath}")

        # Aguardar duração + buffer
        time.sleep(duration + 2)

        # Parar e salvar
        if recorder.is_recording():
            stats = recorder.stop_recording()
            logger.info(f"Worker: Recording saved - {stats.filename} ({stats.file_size} bytes)")

        recorder.close()
        sys.exit(0)

    except Exception as e:
        print(f"Worker error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
