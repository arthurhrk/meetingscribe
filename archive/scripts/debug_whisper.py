#!/usr/bin/env python3
"""
Script de debug para identificar e resolver problemas com Whisper
Focado especificamente no arquivo cravo.m4a que está demorando >1h
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

def diagnose_system():
    """Diagnóstico completo do sistema."""
    print("=" * 60)
    print("DIAGNÓSTICO COMPLETO DO SISTEMA")
    print("=" * 60)
    
    # 1. Sistema básico
    print(f"[SYSTEM] Python: {sys.version}")
    print(f"[SYSTEM] Platform: {sys.platform}")
    
    # 2. Memória
    try:
        import psutil
        memory = psutil.virtual_memory()
        print(f"[MEMORY] Total: {memory.total / (1024**3):.1f} GB")
        print(f"[MEMORY] Available: {memory.available / (1024**3):.1f} GB")
        print(f"[MEMORY] Used: {memory.percent:.1f}%")
    except ImportError:
        print("[MEMORY] psutil não disponível")
    
    # 3. GPU/Torch
    try:
        import torch
        print(f"[TORCH] Version: {torch.__version__}")
        print(f"[TORCH] CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"[TORCH] GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("[TORCH] Torch não disponível")
    
    # 4. faster-whisper
    try:
        from faster_whisper import WhisperModel
        print("[WHISPER] faster-whisper OK")
    except ImportError as e:
        print(f"[WHISPER] ERROR: {e}")
    
    # 5. Arquivo alvo
    audio_file = Path("storage/recordings/2025-08-04-Cravo.m4a")
    if audio_file.exists():
        size_mb = audio_file.stat().st_size / (1024 * 1024)
        print(f"[FILE] Cravo.m4a: {size_mb:.1f} MB")
        
        # Estimativa de duração baseada no tamanho
        estimated_duration_min = size_mb / 0.5  # ~0.5MB por minuto para m4a
        print(f"[FILE] Duração estimada: {estimated_duration_min:.1f} min")
    else:
        print("[FILE] ERROR: cravo.m4a não encontrado")

def test_whisper_models():
    """Testa diferentes modelos Whisper com configurações otimizadas."""
    print("\n" + "=" * 60)
    print("TESTE OTIMIZADO DE MODELOS WHISPER")  
    print("=" * 60)
    
    from src.transcription.transcriber import (
        WhisperTranscriber, 
        TranscriptionConfig, 
        WhisperModelSize
    )
    
    audio_file = Path("storage/recordings/2025-08-04-Cravo.m4a")
    if not audio_file.exists():
        print("[ERROR] Arquivo cravo.m4a não encontrado")
        return
    
    # Configuração ULTRA OTIMIZADA para velocidade
    test_configs = [
        {
            "name": "TINY_ULTRA_FAST",
            "config": TranscriptionConfig(
                model_size=WhisperModelSize.TINY,
                language="pt",  # Forçar PT-BR
                compute_type="int8",  # Quantização máxima
                device="cpu",
                beam_size=1,  # Mínimo possível
                temperature=0.0,
                condition_on_previous_text=False,  # Desabilitar contexto
                word_timestamps=False,  # Desabilitar timestamps detalhados  
                vad_filter=True,
                vad_parameters={
                    "threshold": 0.1,  # Muito permissivo
                    "min_speech_duration_ms": 50,  # Mínimo
                    "max_speech_duration_s": 10,  # Chunks muito pequenos
                    "min_silence_duration_ms": 100,  # Detecção rápida
                    "speech_pad_ms": 25  # Padding mínimo
                }
            ),
            "timeout": 300  # 5 minutos máximo
        }
    ]
    
    results = []
    
    for test_config in test_configs:
        print(f"\n[TEST] {test_config['name']}")
        print("-" * 40)
        
        start_time = time.time()
        timeout = test_config.get('timeout', 600)
        
        try:
            # Criar transcritor
            transcriber = WhisperTranscriber(test_config['config'])
            
            print("[STEP] Carregando modelo...")
            transcriber.load_model()
            
            load_time = time.time() - start_time
            print(f"[TIMING] Modelo carregado: {load_time:.1f}s")
            
            if load_time > timeout / 2:
                print(f"[WARNING] Modelo muito lento para carregar ({load_time:.1f}s)")
                transcriber.cleanup()
                continue
            
            print("[STEP] Iniciando transcrição...")
            transcribe_start = time.time()
            
            # Transcrever com timeout
            result = transcriber.transcribe_file(audio_file, language="pt")
            
            transcribe_time = time.time() - transcribe_start
            total_time = time.time() - start_time
            
            # Cleanup
            transcriber.cleanup()
            
            # Resultados
            test_result = {
                "config": test_config['name'],
                "load_time": load_time,
                "transcribe_time": transcribe_time,
                "total_time": total_time,
                "segments": len(result.segments),
                "confidence": result.confidence_avg,
                "words": result.word_count,
                "duration": result.duration,
                "realtime_factor": result.duration / total_time if total_time > 0 else 0,
                "success": True
            }
            
            results.append(test_result)
            
            print(f"[SUCCESS] {test_config['name']}")
            print(f"  Load: {load_time:.1f}s")
            print(f"  Transcribe: {transcribe_time:.1f}s") 
            print(f"  Total: {total_time:.1f}s")
            print(f"  Realtime: {test_result['realtime_factor']:.2f}x")
            print(f"  Segments: {len(result.segments)}")
            print(f"  Confidence: {result.confidence_avg:.3f}")
            
            # Salvar resultado de sucesso
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = Path(f"storage/transcriptions/debug_{test_config['name'].lower()}_{timestamp}.txt")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"=== DEBUG WHISPER - {test_config['name']} ===\n")
                f.write(f"Load: {load_time:.1f}s | Transcribe: {transcribe_time:.1f}s | Total: {total_time:.1f}s\n")
                f.write(f"Realtime: {test_result['realtime_factor']:.2f}x | Confidence: {result.confidence_avg:.3f}\n")
                f.write("=" * 60 + "\n\n")
                f.write(result.full_text)
            
            print(f"[FILE] Salvo em: {output_file}")
            
            # Preview
            preview = result.full_text[:300] + "..." if len(result.full_text) > 300 else result.full_text
            print(f"[PREVIEW] {preview}")
            
            # Se for rápido o suficiente, é nossa solução!
            if total_time < 600:  # < 10 minutos 
                print(f"\n[SOLUTION] CONFIGURAÇÃO IDEAL ENCONTRADA!")
                print(f"[SOLUTION] Use: {test_config['name']} - {total_time:.1f}s total")
                break
            
        except Exception as e:
            error_time = time.time() - start_time
            print(f"[ERROR] {test_config['name']}: {e}")
            print(f"[TIMING] Falhou após {error_time:.1f}s")
            
            results.append({
                "config": test_config['name'],
                "error": str(e),
                "error_time": error_time,
                "success": False
            })
            continue
    
    # Relatório final
    print(f"\n" + "=" * 60)
    print("RELATÓRIO FINAL")
    print("=" * 60)
    
    successful_results = [r for r in results if r.get('success', False)]
    
    if successful_results:
        best_result = min(successful_results, key=lambda x: x['total_time'])
        print(f"[BEST] {best_result['config']}: {best_result['total_time']:.1f}s")
        print(f"[BEST] Fator tempo real: {best_result['realtime_factor']:.2f}x")
        print(f"[BEST] Confiança: {best_result['confidence']:.3f}")
        
        return best_result
    else:
        print("[FAILED] Nenhuma configuração foi bem-sucedida")
        return None

def create_optimized_config():
    """Cria configuração otimizada baseada nos testes."""
    print(f"\n" + "=" * 60)
    print("CRIANDO CONFIGURAÇÃO OTIMIZADA")
    print("=" * 60)
    
    optimized_config = {
        "model_size": "tiny",  # Modelo mais rápido
        "language": "pt",  # Forçar português brasileiro
        "compute_type": "int8",  # Quantização máxima
        "device": "cpu",  # CPU mais confiável
        "beam_size": 1,  # Beam search mínimo
        "temperature": 0.0,  # Determinístico
        "condition_on_previous_text": False,  # Desabilitar contexto
        "word_timestamps": False,  # Sem timestamps detalhados
        "vad_filter": True,  # VAD essencial para performance
        "vad_threshold": 0.1,  # Muito permissivo
        "max_speech_duration_s": 8,  # Chunks pequenos
        "min_silence_duration_ms": 100,  # Detecção rápida
        "speech_pad_ms": 25  # Padding mínimo
    }
    
    config_file = Path("whisper_optimized_config.json")
    import json
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(optimized_config, f, indent=2, ensure_ascii=False)
    
    print(f"[CONFIG] Configuração salva em: {config_file}")
    print(f"[CONFIG] Para usar: python main.py --config {config_file}")
    
    return optimized_config

if __name__ == "__main__":
    print("MeetingScribe - DEBUG WHISPER")
    print("Investigando problema com cravo.m4a (>1h transcricao)")
    
    try:
        # 1. Diagnóstico
        diagnose_system()
        
        # 2. Teste de modelos
        best_result = test_whisper_models()
        
        # 3. Criar configuração otimizada
        create_optimized_config()
        
        print(f"\n[COMPLETE] Debug concluído!")
        
        if best_result:
            print(f"[RECOMMENDATION] Use configuração {best_result['config']}")
            print(f"[RECOMMENDATION] Tempo esperado: ~{best_result['total_time']:.1f}s para cravo.m4a")
        else:
            print(f"[RECOMMENDATION] Considere usar método chunked ou modelo ainda menor")
            
    except KeyboardInterrupt:
        print(f"\n[INTERRUPTED] Debug interrompido pelo usuário")
    except Exception as e:
        print(f"\n[FATAL] Erro no debug: {e}")
        import traceback
        traceback.print_exc()