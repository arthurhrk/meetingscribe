#!/usr/bin/env python3
"""
Script de teste para otimização de transcrição
Testa diferentes configurações para melhorar velocidade e qualidade.
"""

import time
from pathlib import Path
import json
from src.transcription.transcriber import (
    WhisperTranscriber, 
    TranscriptionConfig, 
    WhisperModelSize,
    TranscriptionProgress
)
from loguru import logger

def test_transcription_configurations():
    """Testa diferentes configurações de transcrição."""
    
    audio_file = Path("storage/recordings/2025-08-04-Cravo.m4a")
    
    if not audio_file.exists():
        logger.error(f"Arquivo não encontrado: {audio_file}")
        return
    
    # Analisar tamanho do arquivo
    file_size_mb = audio_file.stat().st_size / (1024 * 1024)
    logger.info(f"Arquivo de teste: {audio_file} ({file_size_mb:.1f} MB)")
    
    # Configurações para testar (ordem: mais rápida para mais precisa)
    test_configs = [
        {
            "name": "ULTRA_RÁPIDO_TINY", 
            "model": WhisperModelSize.TINY,
            "config": TranscriptionConfig(
                model_size=WhisperModelSize.TINY,
                language="pt",
                compute_type="int8",  # Mais rápido
                device="cpu",
                beam_size=1,  # Mais rápido
                temperature=0.0,
                condition_on_previous_text=False,  # Mais rápido
                vad_filter=True,
                vad_parameters={
                    "threshold": 0.3,  # Menos rigoroso
                    "min_speech_duration_ms": 100,
                    "max_speech_duration_s": 10,  # Chunks pequenos
                    "min_silence_duration_ms": 300,
                    "speech_pad_ms": 50
                }
            )
        },
        {
            "name": "BALANCEADO_BASE",
            "model": WhisperModelSize.BASE, 
            "config": TranscriptionConfig(
                model_size=WhisperModelSize.BASE,
                language="pt",
                compute_type="int8",
                device="cpu", 
                beam_size=1,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters={
                    "threshold": 0.4,
                    "min_speech_duration_ms": 200,
                    "max_speech_duration_s": 20,
                    "min_silence_duration_ms": 500,
                    "speech_pad_ms": 200
                }
            )
        }
    ]
    
    results = []
    
    for test_config in test_configs:
        logger.info(f"\n{'='*50}")
        logger.info(f"TESTANDO: {test_config['name']}")
        logger.info(f"{'='*50}")
        
        # Progress callback
        def progress_callback(progress: float, status: str):
            print(f"\rProgresso: {progress*100:.1f}% - {status}", end="", flush=True)
        
        progress = TranscriptionProgress(progress_callback)
        
        try:
            start_time = time.time()
            
            # Criar transcritor com configuração específica
            transcriber = WhisperTranscriber(test_config['config'])
            
            # Transcrever
            result = transcriber.transcribe_file(audio_file, progress, language="pt")
            
            # Cleanup
            transcriber.cleanup()
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Avaliar resultado
            test_result = {
                "config_name": test_config['name'],
                "model_size": test_config['config'].model_size.value,
                "total_time": total_time,
                "audio_duration": result.duration,
                "realtime_factor": result.duration / total_time if total_time > 0 else 0,
                "segments_count": len(result.segments),
                "confidence_avg": result.confidence_avg,
                "word_count": result.word_count,
                "text_preview": result.full_text[:200] + "..." if len(result.full_text) > 200 else result.full_text
            }
            
            results.append(test_result)
            
            print(f"\n\n✅ RESULTADO {test_config['name']}:")
            print(f"   Tempo total: {total_time:.1f}s")
            print(f"   Duração áudio: {result.duration:.1f}s")  
            print(f"   Fator tempo real: {test_result['realtime_factor']:.2f}x")
            print(f"   Segmentos: {len(result.segments)}")
            print(f"   Confiança média: {result.confidence_avg:.3f}")
            print(f"   Preview: {test_result['text_preview']}")
            
            # Se for muito lento (>30min), parar nos próximos testes
            if total_time > 1800:  # 30 minutos
                logger.warning(f"Teste {test_config['name']} muito lento ({total_time/60:.1f} min), parando aqui")
                break
                
        except Exception as e:
            logger.error(f"Erro no teste {test_config['name']}: {e}")
            print(f"\n❌ FALHOU: {test_config['name']} - {e}")
            continue
    
    # Salvar resultados
    results_file = Path("test_transcription_results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Relatório final
    print(f"\n{'='*60}")
    print("RELATÓRIO FINAL")
    print(f"{'='*60}")
    
    if results:
        # Encontrar melhor configuração
        best_speed = min(results, key=lambda x: x['total_time'])
        best_quality = max(results, key=lambda x: x['confidence_avg'])
        
        print(f"🚀 MAIS RÁPIDO: {best_speed['config_name']} ({best_speed['total_time']:.1f}s)")
        print(f"🎯 MELHOR QUALIDADE: {best_quality['config_name']} (conf: {best_quality['confidence_avg']:.3f})")
        
        for result in results:
            status = "✅ RECOMENDADO" if result['total_time'] < 300 else "⚠️ LENTO"
            print(f"\n{status} {result['config_name']}:")
            print(f"   Tempo: {result['total_time']:.1f}s ({result['realtime_factor']:.1f}x tempo real)")
            print(f"   Qualidade: {result['confidence_avg']:.3f}")
    else:
        print("❌ Nenhum teste foi bem-sucedido")
    
    print(f"\nResultados salvos em: {results_file}")

def test_model_size_detection():
    """Testa detecção automática de qualidade por modelo"""
    
    print("\n[*] Testando detecção automática por modelo")
    print("=" * 50)
    
    models_to_test = [
        (WhisperModelSize.TINY, False),
        (WhisperModelSize.BASE, False),
        (WhisperModelSize.SMALL, False),
        (WhisperModelSize.MEDIUM, True),
        (WhisperModelSize.LARGE_V3, True)
    ]
    
    for model, expected_quality in models_to_test:
        # Simular lógica do main.py
        quality_mode = model in [WhisperModelSize.MEDIUM, WhisperModelSize.LARGE_V2, WhisperModelSize.LARGE_V3]
        status = "[OK]" if quality_mode == expected_quality else "[ERRO]"
        print(f"{status} {model.value}: quality_mode={quality_mode}")

if __name__ == "__main__":
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    
    test_transcription_configurations()