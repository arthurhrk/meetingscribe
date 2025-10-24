#!/usr/bin/env python3
"""
Quick Record - Inicia gravação e mantém processo vivo

FLUXO:
1. Parse argumentos
2. Gera timestamp e filepath
3. IMPRIME JSON IMEDIATAMENTE (Raycast recebe e mostra sucesso)
4. Importa módulos pesados (audio_recorder)
5. Inicia gravação
6. Aguarda completar
7. Salva arquivo
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
        except:
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
            "duration": duration
        }
    }
    print(json.dumps(result), flush=True)

    # Agora fazer imports pesados e iniciar gravação
    try:
        from audio_recorder import AudioRecorder, AudioRecorderError

        recorder = AudioRecorder()
        success = recorder.set_device_auto()
        if not success:
            # Já imprimimos sucesso, então apenas log erro e exit
            sys.exit(1)

        if duration:
            recorder._config.max_duration = duration

        # Iniciar gravação
        recorder.start_recording(filename=filename)

        # Manter vivo até completar
        time.sleep(duration + 3)

        # Finalizar
        if recorder.is_recording():
            recorder.stop_recording()

        recorder.close()

    except Exception as e:
        # Já imprimimos JSON de sucesso, então apenas exit silenciosamente
        sys.exit(1)

if __name__ == "__main__":
    main()
