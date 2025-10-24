#!/usr/bin/env python3
"""
Teste rápido para transcrição do arquivo cravo.m4a
Foco em velocidade máxima com qualidade aceitável.
"""

import time
from pathlib import Path
from datetime import datetime
from src.transcription.transcriber import (
    WhisperTranscriber, 
    TranscriptionConfig, 
    WhisperModelSize,
    TranscriptionProgress
)
from src.transcription.chunked_transcriber import ChunkedTranscriber
from loguru import logger

def quick_transcribe_cravo():
    """Transcrição rápida e eficiente do arquivo cravo.m4a."""
    
    audio_file = Path("storage/recordings/2025-08-04-Cravo.m4a")
    
    if not audio_file.exists():
        logger.error(f"Arquivo não encontrado: {audio_file}")
        return
    
    file_size_mb = audio_file.stat().st_size / (1024 * 1024)
    logger.info(f"=== TRANSCRIÇÃO RÁPIDA CRAVO.M4A ===")
    logger.info(f"Arquivo: {file_size_mb:.1f} MB")
    
    # Configuração otimizada para VELOCIDADE MÁXIMA
    ultra_fast_config = TranscriptionConfig(
        model_size=WhisperModelSize.TINY,  # Modelo mais rápido
        language="pt",  # Forçar português
        compute_type="int8",  # Mais rápido
        device="cpu",  # CPU mais estável
        beam_size=1,  # Beam size mínimo = mais rápido
        temperature=0.0,  # Determinístico
        condition_on_previous_text=False,  # Desabilita contexto = mais rápido
        word_timestamps=False,  # Desabilita timestamps detalhados = mais rápido
        vad_filter=True,  # VAD essencial
        vad_parameters={
            "threshold": 0.2,  # Muito permissivo = mais rápido
            "min_speech_duration_ms": 50,  # Duração mínima baixa
            "max_speech_duration_s": 15,  # Chunks pequenos = mais rápido
            "min_silence_duration_ms": 200,  # Detecção rápida de silêncio
            "speech_pad_ms": 50  # Padding mínimo
        }
    )
    
    print("\n[RAPID] METODO 1: TRANSCRICAO DIRETA ULTRA-RAPIDA")
    print("=" * 50)
    
    def progress_callback(progress: float, status: str):
        print(f"[PROGRESS] {progress*100:.1f}% - {status}")
    
    progress = TranscriptionProgress(progress_callback)
    
    try:
        start_time = time.time()
        
        # Criar transcritor
        transcriber = WhisperTranscriber(ultra_fast_config)
        
        # Transcrever
        logger.info("[TARGET] Iniciando transcricao ultra-rapida...")
        result = transcriber.transcribe_file(audio_file, progress, language="pt")
        
        # Cleanup
        transcriber.cleanup()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Relatório
        print(f"\n[SUCCESS] TRANSCRICAO CONCLUIDA!")
        print(f"   Tempo total: {total_time:.1f}s ({total_time/60:.1f} min)")
        print(f"   Duracao audio: {result.duration:.1f}s ({result.duration/60:.1f} min)")
        print(f"   Fator tempo real: {result.duration/total_time:.2f}x")
        print(f"   Segmentos: {len(result.segments)}")
        print(f"   Palavras: {result.word_count}")
        print(f"   Confianca: {result.confidence_avg:.3f}")
        
        # Salvar resultado
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"storage/transcriptions/cravo_ultrafast_{timestamp}.txt")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=== TRANSCRICAO ULTRA-RAPIDA - CRAVO.M4A ===\n")
            f.write(f"Tempo: {total_time:.1f}s | Fator: {result.duration/total_time:.2f}x | Confianca: {result.confidence_avg:.3f}\n")
            f.write("=" * 60 + "\n\n")
            f.write(result.full_text)
        
        print(f"   [FILE] Salvo em: {output_path}")
        
        # Preview do texto
        preview = result.full_text[:500] + "..." if len(result.full_text) > 500 else result.full_text
        print(f"\n[PREVIEW]:\n{preview}")
        
        # Testar método chunked se for muito lento
        if total_time > 1800:  # >30 min
            print(f"\n[WARNING] Tempo muito alto ({total_time/60:.1f} min), testando metodo chunked...")
            test_chunked_method(audio_file)
        
    except Exception as e:
        logger.error(f"Erro na transcricao: {e}")
        print(f"\n[ERROR] ERRO: {e}")
        print("\n[FALLBACK] Tentando metodo chunked como fallback...")
        test_chunked_method(audio_file)

def test_chunked_method(audio_file: Path):
    """Teste do método chunked para arquivos grandes."""
    
    print(f"\n[CHUNKED] METODO 2: TRANSCRICAO CHUNKED")
    print("=" * 40)
    
    try:
        start_time = time.time()
        
        # Usar chunks de 2 minutos para máxima velocidade
        with ChunkedTranscriber(chunk_duration=120, overlap=5) as chunked:
            logger.info("[TARGET] Iniciando transcricao por chunks...")
            result = chunked.transcribe_chunked(
                audio_file, 
                model_size=WhisperModelSize.TINY,
                quality_mode=False  # Velocidade > qualidade
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Relatório
        print(f"\n[SUCCESS] CHUNKED CONCLUIDO!")
        print(f"   Tempo total: {total_time:.1f}s ({total_time/60:.1f} min)")
        print(f"   Duracao audio: {result.duration:.1f}s")
        print(f"   Fator tempo real: {result.duration/total_time:.2f}x")
        print(f"   Segmentos: {len(result.segments)}")
        print(f"   Palavras: {result.word_count}")
        
        # Salvar resultado chunked
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"storage/transcriptions/cravo_chunked_{timestamp}.txt")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=== TRANSCRICAO CHUNKED - CRAVO.M4A ===\n")
            f.write(f"Tempo: {total_time:.1f}s | Fator: {result.duration/total_time:.2f}x\n")
            f.write("=" * 60 + "\n\n")
            f.write(result.full_text)
        
        print(f"   [FILE] Salvo em: {output_path}")
        
    except Exception as e:
        logger.error(f"Erro chunked: {e}")
        print(f"\n[ERROR] ERRO CHUNKED: {e}")

if __name__ == "__main__":
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    
    print("MeetingScribe - Teste Rapido Cravo.m4a")
    print("Foco: MAXIMA VELOCIDADE com qualidade aceitavel")
    
    quick_transcribe_cravo()
    
    print(f"\n[COMPLETE] TESTE CONCLUIDO!")
    print(f"[INFO] Verifique os arquivos em storage/transcriptions/")