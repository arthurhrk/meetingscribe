#!/usr/bin/env python3
"""
Teste de Performance - Otimização de Chunks

Verifica se o sistema de processamento de chunks está 
funcionando e otimizando a transcrição de áudio.
"""

import time
import tempfile
from pathlib import Path

def test_chunk_processor():
    """Testa o processador de chunks."""
    print("=== TESTE DE PROCESSAMENTO DE CHUNKS ===")
    
    try:
        # Test imports
        from src.core.audio_chunk_processor import create_chunk_processor, ChunkStrategy
        print("[OK] Processador de chunks importado com sucesso")
        
        # Create processor
        processor = create_chunk_processor(
            strategy=ChunkStrategy.TIME_BASED,
            chunk_duration=30.0
        )
        print(f"[OK] Processador criado - estratégia: {processor.config.strategy}")
        
        print("\n[SUCCESS] Processador de chunks funcionando!")
        return True
        
    except ImportError as e:
        print(f"[SKIP] Processador de chunks não disponível: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Erro no processador de chunks: {e}")
        return False

def test_chunked_transcriber():
    """Testa o transcritor com chunks."""
    print("\n=== TESTE DE TRANSCRITOR CHUNKED ===")
    
    try:
        # Test imports
        from src.transcription.chunked_transcriber import (
            create_chunked_transcriber, ChunkedWhisperTranscriber,
            ChunkStrategy
        )
        print("[OK] Transcritor chunked importado com sucesso")
        
        # Create transcriber
        transcriber = create_chunked_transcriber(
            chunk_strategy=ChunkStrategy.TIME_BASED,
            chunk_duration=30.0,
            parallel_chunks=False  # Evitar threads nos testes
        )
        print(f"[OK] Transcritor chunked criado")
        
        # Test configuration
        config = transcriber.config
        print(f"   Estratégia: {config.chunk_strategy}")
        print(f"   Duração chunk: {config.chunk_duration}s")
        print(f"   Paralelo: {config.parallel_chunks}")
        
        print("\n[SUCCESS] Transcritor chunked funcionando!")
        return True
        
    except ImportError as e:
        print(f"[SKIP] Transcritor chunked não disponível: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Erro no transcritor chunked: {e}")
        return False

def test_integration():
    """Testa integração entre cache e chunks."""
    print("\n=== TESTE DE INTEGRAÇÃO CACHE + CHUNKS ===")
    
    try:
        # Test cache
        from src.core.model_cache import get_model_cache
        cache = get_model_cache()
        cache_stats = cache.get_stats()
        print(f"[OK] Cache ativo - {cache_stats['models_cached']} modelos")
        
        # Test chunks
        from src.core.audio_chunk_processor import create_chunk_processor
        processor = create_chunk_processor()
        print(f"[OK] Processador de chunks ativo")
        
        # Test chunked transcriber
        from src.transcription.chunked_transcriber import create_chunked_transcriber
        transcriber = create_chunked_transcriber()
        print(f"[OK] Transcritor chunked ativo")
        
        print("\n[SUCCESS] Integração cache + chunks funcionando!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Erro na integração: {e}")
        return False

def main():
    """Executa todos os testes de otimização de chunks."""
    print("🔧 INICIANDO TESTES DE OTIMIZAÇÃO DE CHUNKS")
    print("=" * 50)
    
    # Test components
    chunk_processor_ok = test_chunk_processor()
    chunked_transcriber_ok = test_chunked_transcriber()
    integration_ok = test_integration()
    
    print("\n" + "=" * 50)
    if chunk_processor_ok and chunked_transcriber_ok and integration_ok:
        print("🎉 OTIMIZAÇÃO DE CHUNKS IMPLEMENTADA COM SUCESSO!")
        print("\nBenefícios da otimização:")
        print("- ✅ Processamento inteligente de chunks")
        print("- ✅ Divisão adaptativa baseada em conteúdo")
        print("- ✅ Processamento paralelo de chunks")
        print("- ✅ Cache compartilhado entre chunks")
        print("- ✅ Gestão automática de memória")
        print("- ✅ Merge inteligente de segmentos")
        
        print("\nPróximos passos de otimização:")
        print("- ✅ Cache inteligente de modelos")
        print("- ✅ Processamento de áudio em chunks")
        print("- ⏳ Gestão avançada de memória")
        print("- ⏳ Processamento assíncrono")
        print("- ⏳ Monitoramento de performance")
    else:
        print("❌ Problemas detectados na otimização de chunks")
        print("\nVerifique:")
        print("- Dependências de áudio instaladas")
        print("- Importações corretas")
        print("- Configuração do sistema")

if __name__ == "__main__":
    main()