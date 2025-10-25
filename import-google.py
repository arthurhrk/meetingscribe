import google.generativeai as genai
import os
import time
from pathlib import Path
import soundfile as sf
import numpy as np
from scipy import signal
from google.api_core import retry
from google.api_core import exceptions

# --- ConfiguraÃ§Ã£o ---
# Coloque sua API Key aqui
# (Ã‰ mais seguro usar variÃ¡veis de ambiente, mas isso funciona para testes)
API_KEY = "AIzaSyAX3uH8jFWJP1wXeZ21UvfgUmRwbXV-wIc"

# Defina o caminho para o seu arquivo de Ã¡udio
# Ex: "C:/Users/SeuNome/Desktop/meu_audio.wav" ou "audios/teste.wav"
AUDIO_FILE_PATH = r"C:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe\storage\recordings\2025-08-05-JulioBlanco.m4a"

# ConfiguraÃ§Ãµes de otimizaÃ§Ã£o de Ã¡udio
# NOTA: A otimizaÃ§Ã£o requer ffmpeg instalado para formatos como M4A
# Se ffmpeg nÃ£o estiver disponÃ­vel, defina como False
OPTIMIZE_AUDIO = False  # Se True, converte para mono 16kHz WAV antes de enviar
TARGET_SAMPLE_RATE = 16000  # 16kHz Ã© suficiente para transcriÃ§Ã£o de voz
TARGET_CHANNELS = 1  # Mono (voz nÃ£o precisa de estÃ©reo)

# Timeout em segundos (ajuste conforme necessÃ¡rio)
REQUEST_TIMEOUT = 300  # 5 minutos

# --------------------

def optimize_audio(input_path: str) -> tuple[str, float]:
    """
    Converte e otimiza o arquivo de Ã¡udio para reduzir tamanho mantendo qualidade.

    OtimizaÃ§Ãµes aplicadas:
    - ConversÃ£o para mono (1 canal)
    - ReduÃ§Ã£o para 16kHz (suficiente para voz humana)
    - Formato WAV (compatÃ­vel e sem perdas)

    Returns:
        tuple: (caminho do arquivo otimizado, tamanho em MB)
    """
    print(f"[OtimizaÃ§Ã£o] Carregando arquivo original...")

    file_path = Path(input_path)
    original_size = file_path.stat().st_size / (1024 * 1024)

    try:
        # Tenta ler o arquivo de Ã¡udio com soundfile (WAV, FLAC, OGG)
        audio_data, sample_rate = sf.read(str(file_path))
    except Exception as e:
        # Se falhar, tenta com pydub (suporta mais formatos, mas precisa de ffmpeg)
        print(f"[OtimizaÃ§Ã£o] soundfile falhou, tentando pydub...")
        try:
            from pydub import AudioSegment

            # Carrega o arquivo
            audio_segment = AudioSegment.from_file(str(file_path))

            # Converte para mono
            if audio_segment.channels > 1 and TARGET_CHANNELS == 1:
                audio_segment = audio_segment.set_channels(1)

            # Reamostra
            if audio_segment.frame_rate != TARGET_SAMPLE_RATE:
                audio_segment = audio_segment.set_frame_rate(TARGET_SAMPLE_RATE)

            # Salva como WAV temporÃ¡rio
            temp_path = file_path.parent / f"{file_path.stem}_optimized.wav"
            audio_segment.export(str(temp_path), format="wav", parameters=["-ac", "1", "-ar", str(TARGET_SAMPLE_RATE)])

            optimized_size = temp_path.stat().st_size / (1024 * 1024)
            reduction = ((original_size - optimized_size) / original_size) * 100

            print(f"[OtimizaÃ§Ã£o] Original: {audio_segment.frame_rate}Hz, {audio_segment.channels}ch, {original_size:.2f}MB")
            print(f"[OtimizaÃ§Ã£o] Otimizado: {TARGET_SAMPLE_RATE}Hz, {TARGET_CHANNELS}ch, {optimized_size:.2f}MB")
            print(f"[OtimizaÃ§Ã£o] ReduÃ§Ã£o: {reduction:.1f}%")

            return str(temp_path), optimized_size

        except ImportError:
            raise Exception("pydub nÃ£o estÃ¡ instalado. Instale com: pip install pydub")
        except Exception as pydub_error:
            raise Exception(f"Erro ao processar Ã¡udio com pydub (ffmpeg pode estar faltando): {pydub_error}")

    # Detecta nÃºmero de canais
    if len(audio_data.shape) > 1:
        channels = audio_data.shape[1]
    else:
        channels = 1

    print(f"[OtimizaÃ§Ã£o] Original: {sample_rate}Hz, {channels}ch, {original_size:.2f}MB")

    # Converte para mono se necessÃ¡rio
    if len(audio_data.shape) > 1 and TARGET_CHANNELS == 1:
        audio_data = np.mean(audio_data, axis=1)

    # Reamostra se necessÃ¡rio
    if sample_rate != TARGET_SAMPLE_RATE:
        # Calcula nÃºmero de amostras na nova taxa
        num_samples = int(len(audio_data) * TARGET_SAMPLE_RATE / sample_rate)
        audio_data = signal.resample(audio_data, num_samples)

    # Normaliza para 16-bit integer range
    audio_data = np.clip(audio_data, -1.0, 1.0)
    audio_data = (audio_data * 32767).astype(np.int16)

    # Salva como WAV otimizado
    temp_path = file_path.parent / f"{file_path.stem}_optimized.wav"
    sf.write(str(temp_path), audio_data, TARGET_SAMPLE_RATE, subtype='PCM_16')

    optimized_size = temp_path.stat().st_size / (1024 * 1024)
    reduction = ((original_size - optimized_size) / original_size) * 100

    print(f"[OtimizaÃ§Ã£o] Otimizado: {TARGET_SAMPLE_RATE}Hz, {TARGET_CHANNELS}ch, {optimized_size:.2f}MB")
    print(f"[OtimizaÃ§Ã£o] ReduÃ§Ã£o: {reduction:.1f}%")

    return str(temp_path), optimized_size

try:
    # Verifica informaÃ§Ãµes do arquivo antes de comeÃ§ar
    file_path = Path(AUDIO_FILE_PATH)
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo nÃ£o encontrado: {AUDIO_FILE_PATH}")

    original_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"Arquivo original: {file_path.name}")
    print(f"Tamanho: {original_size_mb:.2f} MB")
    print(f"Formato: {file_path.suffix}")
    print()

    # Otimiza o Ã¡udio se configurado
    upload_file_path = AUDIO_FILE_PATH
    optimized_file = None

    if OPTIMIZE_AUDIO:
        print("=" * 60)
        print("OTIMIZAÃ‡ÃƒO DE ÃUDIO")
        print("=" * 60)
        optimized_file, optimized_size = optimize_audio(AUDIO_FILE_PATH)
        upload_file_path = optimized_file
        print(f"\nArquivo a ser enviado: {Path(optimized_file).name}")
        print(f"Tamanho final: {optimized_size:.2f} MB")
        print("=" * 60)
        print()

    # 1. Configura a API Key na biblioteca
    genai.configure(api_key=API_KEY)

    # 2. Faz o upload do seu arquivo de Ã¡udio para a API do Gemini
    #    Isso Ã© necessÃ¡rio para que o modelo possa "ouvir" o Ã¡udio.
    print(f"[1/4] Fazendo upload do arquivo...")
    upload_start = time.time()

    # Tenta upload com retry
    max_retries = 3
    for attempt in range(max_retries):
        try:
            audio_file = genai.upload_file(path=upload_file_path)
            upload_time = time.time() - upload_start
            print(f"      Upload concluÃ­do em {upload_time:.1f}s")
            print(f"      URI: {audio_file.uri}")
            break
        except exceptions.ServiceUnavailable as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # 2s, 4s, 6s
                print(f"      Erro de conexÃ£o (tentativa {attempt + 1}/{max_retries})")
                print(f"      Aguardando {wait_time}s antes de tentar novamente...")
                time.sleep(wait_time)
            else:
                raise
        except Exception as e:
            raise

    print()

    # Aguarda o processamento do arquivo
    print(f"[2/4] Aguardando processamento do arquivo...")
    process_start = time.time()
    while audio_file.state.name == "PROCESSING":
        print("      Processando...", end="\r")
        time.sleep(2)
        audio_file = genai.get_file(audio_file.name)

    process_time = time.time() - process_start

    if audio_file.state.name == "FAILED":
        raise Exception(f"Falha no processamento do arquivo: {audio_file.state.name}")

    print(f"      Processamento concluÃ­do em {process_time:.1f}s")
    print()

    # 3. Seleciona o modelo (gemini-1.5-pro Ã© Ã³timo para Ã¡udio)
    model = genai.GenerativeModel('models/gemini-2.0-flash-exp')

    # ConfiguraÃ§Ã£o com timeout
    generation_config = {
        "temperature": 0.1,  # Baixa temperatura para transcriÃ§Ã£o mais precisa
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
    }

    # 4. Envia o Ã¡udio e um prompt de texto juntos
    #    O prompt diz ao modelo qual tarefa executar.
    print(f"[3/4] Enviando solicitaÃ§Ã£o de transcriÃ§Ã£o para o modelo...")
    prompt = """Transcreva este Ã¡udio em portuguÃªs brasileiro palavra por palavra, exatamente como foi dito.

Formato da transcriÃ§Ã£o:
- Use pontuaÃ§Ã£o adequada
- Mantenha a ordem cronolÃ³gica
- Indique pausas longas com [...]
- Se houver mÃºltiplos falantes, indique com "Pessoa 1:", "Pessoa 2:", etc.
"""

    transcription_start = time.time()
    response = model.generate_content(
        [prompt, audio_file],
        generation_config=generation_config,
        request_options={"timeout": REQUEST_TIMEOUT}
    )
    transcription_time = time.time() - transcription_start
    print(f"      TranscriÃ§Ã£o concluÃ­da em {transcription_time:.1f}s")
    print()

    # 5. Imprime o resultado da transcriÃ§Ã£o
    print("[4/4] Resultado:")
    print("\n" + "="*80)
    print("TRANSCRIÃ‡ÃƒO")
    print("="*80)
    print(response.text)
    print("="*80)
    print()

    # Resumo de timing
    total_time = upload_time + process_time + transcription_time
    print(f"Tempo total: {total_time:.1f}s")
    print(f"  - Upload: {upload_time:.1f}s")
    print(f"  - Processamento: {process_time:.1f}s")
    print(f"  - TranscriÃ§Ã£o: {transcription_time:.1f}s")
    print()

    # (Opcional) Exclui o arquivo temporÃ¡rio dos servidores do Gemini
    genai.delete_file(audio_file.name)
    print(f"Arquivo temporÃ¡rio removido da API.")

    # Remove arquivo otimizado local se foi criado
    if optimized_file and Path(optimized_file).exists():
        Path(optimized_file).unlink()
        print(f"Arquivo otimizado local removido.")

except FileNotFoundError as e:
    print(f"\n--- ERRO ---")
    print(f"Arquivo nÃ£o encontrado: {AUDIO_FILE_PATH}")
    print("Por favor, verifique o nome e o caminho do arquivo.")
except TimeoutError as e:
    print(f"\n--- TIMEOUT ---")
    print(f"A operaÃ§Ã£o excedeu o tempo limite de {REQUEST_TIMEOUT}s")
    print("PossÃ­veis soluÃ§Ãµes:")
    print("  1. Aumente o valor de REQUEST_TIMEOUT no cÃ³digo")
    print("  2. Use um arquivo de Ã¡udio menor")
    print("  3. Tente novamente mais tarde")
except exceptions.ServiceUnavailable as e:
    print(f"\n--- ERRO DE CONEXÃƒO ---")
    print(f"NÃ£o foi possÃ­vel conectar Ã  API do Google (503 Service Unavailable)")
    print()
    print("PossÃ­veis causas:")
    print("  1. Firewall ou proxy corporativo bloqueando a conexÃ£o")
    print("  2. API do Google temporariamente indisponÃ­vel")
    print("  3. Arquivo muito grande (30MB) para a conexÃ£o atual")
    print()
    print("SoluÃ§Ãµes sugeridas:")
    print("  1. Verifique se estÃ¡ conectado Ã  VPN corporativa e tente desconectar")
    print("  2. Tente usar uma rede diferente (nÃ£o corporativa)")
    print("  3. Ative OPTIMIZE_AUDIO = True no cÃ³digo (reduz tamanho do arquivo)")
    print("     NOTA: Requer ffmpeg instalado")
    print("  4. Use um arquivo de Ã¡udio menor para testar")
    print("  5. Aguarde alguns minutos e tente novamente")
except Exception as e:
    # Captura outros erros (ex: API Key invÃ¡lida, problema de permissÃ£o)
    print(f"\n--- ERRO ---")
    print(f"Tipo: {type(e).__name__}")
    print(f"Mensagem: {e}")

    # Tenta limpar arquivos se foram criados
    try:
        if 'audio_file' in locals():
            genai.delete_file(audio_file.name)
            print(f"\nArquivo temporÃ¡rio removido da API apÃ³s erro.")
    except:
        pass

    try:
        if 'optimized_file' in locals() and optimized_file and Path(optimized_file).exists():
            Path(optimized_file).unlink()
            print(f"Arquivo otimizado local removido apÃ³s erro.")
    except:
        pass
