"""
GRAVADOR COM DEBUG COMPLETO
"""
import sys
import json
from datetime import datetime
import time

print("DEBUG: Script iniciado", file=sys.stderr)

# IMPRIMIR JSON PRIMEIRO
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30
filename = f"recording_{timestamp}.wav"
filepath = f"storage\\recordings\\{filename}"

print("DEBUG: Gerando JSON...", file=sys.stderr)
result = {
    "status": "success",
    "data": {
        "session_id": f"rec-{timestamp}",
        "file_path": filepath,
        "duration": duration
    }
}
print(json.dumps(result), flush=True)
print("DEBUG: JSON enviado!", file=sys.stderr)

# Importar
print("DEBUG: Importando audio_recorder...", file=sys.stderr)
from audio_recorder import AudioRecorder
print("DEBUG: Import OK", file=sys.stderr)

# Criar recorder
print("DEBUG: Criando recorder...", file=sys.stderr)
recorder = AudioRecorder()
print("DEBUG: Recorder criado", file=sys.stderr)

# Auto-detect
print("DEBUG: Auto-detect...", file=sys.stderr)
recorder.set_device_auto()
print("DEBUG: Device OK", file=sys.stderr)

# Config
recorder._config.max_duration = duration
print(f"DEBUG: Iniciando gravação de {duration}s...", file=sys.stderr)

# Start
recorder.start_recording(filename=filename)
print("DEBUG: Gravação iniciada!", file=sys.stderr)

# Wait
print(f"DEBUG: Aguardando {duration}s...", file=sys.stderr)
time.sleep(duration + 2)
print("DEBUG: Tempo completo!", file=sys.stderr)

# Save
print("DEBUG: Salvando arquivo...", file=sys.stderr)
if recorder._frames:
    print(f"DEBUG: {len(recorder._frames)} frames capturados", file=sys.stderr)

    import wave
    from pathlib import Path

    filepath_obj = Path(filepath)
    filepath_obj.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(filepath_obj), 'wb') as wav_file:
        wav_file.setnchannels(recorder._config.channels)
        wav_file.setsampwidth(recorder._audio.get_sample_size(recorder._config.format))
        wav_file.setframerate(recorder._config.sample_rate)
        wav_file.writeframes(b''.join(recorder._frames))

    print(f"DEBUG: Arquivo salvo: {filepath}", file=sys.stderr)
    print(f"DEBUG: Tamanho: {filepath_obj.stat().st_size} bytes", file=sys.stderr)
else:
    print("DEBUG: ERRO - Nenhum frame!", file=sys.stderr)

print("DEBUG: Fechando recorder...", file=sys.stderr)
recorder.close()
print("DEBUG: Script finalizado!", file=sys.stderr)
