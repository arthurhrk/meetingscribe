"""
GRAVADOR SIMPLES - SÓ GRAVA E PRONTO
Uso: python gravar.py 30  (grava 30 segundos)
"""
import sys
from audio_recorder import AudioRecorder
from datetime import datetime
import time

# Duração
duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30

print(f"Iniciando gravação de {duration} segundos...")

# Criar gravador
recorder = AudioRecorder()
recorder.set_device_auto()
recorder._config.max_duration = duration

# Nome do arquivo
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"recording_{timestamp}.wav"

# Iniciar
filepath = recorder.start_recording(filename=filename)
print(f"Gravando em: {filepath}")

# Aguardar
print(f"Aguarde {duration} segundos...")
time.sleep(duration + 2)

# Salvar
print("Salvando arquivo...")
if recorder._frames:
    import wave
    from pathlib import Path

    filepath_obj = Path(filepath)
    with wave.open(str(filepath_obj), 'wb') as wav_file:
        wav_file.setnchannels(recorder._config.channels)
        wav_file.setsampwidth(recorder._audio.get_sample_size(recorder._config.format))
        wav_file.setframerate(recorder._config.sample_rate)
        wav_file.writeframes(b''.join(recorder._frames))

    print(f"✓ Arquivo salvo: {filepath}")
    print(f"✓ Tamanho: {filepath_obj.stat().st_size} bytes")
else:
    print("✗ ERRO: Nenhum áudio capturado!")

recorder.close()
