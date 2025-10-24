"""
GRAVADOR PARA RAYCAST - Imprime JSON e grava
"""
import sys
import json
from datetime import datetime

# IMPRIMIR JSON PRIMEIRO (para Raycast)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30
filename = f"recording_{timestamp}.wav"
filepath = f"storage\\recordings\\{filename}"

result = {
    "status": "success",
    "data": {
        "session_id": f"rec-{timestamp}",
        "file_path": filepath,
        "duration": duration
    }
}
print(json.dumps(result), flush=True)

# Agora gravar
import time
from audio_recorder import AudioRecorder

recorder = AudioRecorder()
recorder.set_device_auto()
recorder._config.max_duration = duration
recorder.start_recording(filename=filename)

# Aguardar
time.sleep(duration + 2)

# Salvar forçado
if recorder._frames:
    import wave
    from pathlib import Path

    filepath_obj = Path(filepath)
    filepath_obj.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(filepath_obj), 'wb') as wav_file:
        wav_file.setnchannels(recorder._config.channels)
        wav_file.setsampwidth(recorder._audio.get_sample_size(recorder._config.format))
        wav_file.setframerate(recorder._config.sample_rate)
        wav_file.writeframes(b''.join(recorder._frames))

recorder.close()
