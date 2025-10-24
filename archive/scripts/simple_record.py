"""
SOLUÇÃO MAIS SIMPLES POSSÍVEL
- Imprime JSON instantaneamente
- Mantém processo vivo
- Salva arquivo garantido
"""
import sys
import json
from datetime import datetime

# IMPRIMIR JSON INSTANTANEAMENTE - ANTES DE QUALQUER COISA
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filepath = f"storage\\recordings\\recording_{timestamp}.wav"

print(json.dumps({
    "status": "success",
    "data": {
        "session_id": f"rec-{timestamp}",
        "file_path": filepath,
        "duration": int(sys.argv[1]) if len(sys.argv) > 1 else 30
    }
}))
sys.stdout.flush()

# Agora fazer a gravação real
import time
from audio_recorder import AudioRecorder

duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30

recorder = AudioRecorder()
recorder.set_device_auto()
recorder._config.max_duration = duration

recorder.start_recording(filename=f"recording_{timestamp}.wav")

# Aguardar completar
time.sleep(duration + 3)

# Salvar forçado
if recorder._frames:
    recorder._recording = False
    if recorder._stream:
        try:
            recorder._stream.stop_stream()
            recorder._stream.close()
        except:
            pass

    # Salvar arquivo
    import wave
    from pathlib import Path

    filepath_full = Path(f"storage/recordings/recording_{timestamp}.wav")
    filepath_full.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(filepath_full), 'wb') as wav_file:
        wav_file.setnchannels(recorder._config.channels)
        wav_file.setsampwidth(recorder._audio.get_sample_size(recorder._config.format))
        wav_file.setframerate(recorder._config.sample_rate)
        wav_file.writeframes(b''.join(recorder._frames))

recorder.close()
