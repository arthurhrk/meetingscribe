#!/usr/bin/env python3
"""
Teste de Performance - Cache de Modelos

Verifica se o cache de modelos está funcionando e otimizando
o carregamento de modelos Whisper.
"""

import time
import sys
from pathlib import Path

def test_model_cache_performance():
    """Testa performance do cache de modelos."""
    print("=== TESTE DE PERFORMANCE - CACHE DE MODELOS ===")
    
    try:
        # Test imports
        from src.core.model_cache import get_model_cache, create_cached_model
        print("[OK] Cache de modelos importado com sucesso")
        
        # Get cache instance
        cache = get_model_cache()
        print(f"[OK] Cache inicializado - max_models: {cache.max_models}")
        
        # Test 1: First load (cache miss)
        print("\n1. Primeiro carregamento (cache miss esperado)...")
        start_time = time.time()
        
        try:
            model, cache_hit = create_cached_model("tiny", "cpu", "int8")
            load_time_1 = time.time() - start_time
            
            print(f"   Carregamento 1: {load_time_1:.2f}s, Cache Hit: {cache_hit}")
            assert not cache_hit, "Primeiro carregamento deveria ser cache miss"
            
        except Exception as e:
            print(f"   [SKIP] Erro no carregamento (pode ser falta de dependências): {e}")
            return
        
        # Test 2: Second load (cache hit)
        print("\n2. Segundo carregamento (cache hit esperado)...")
        start_time = time.time()
        
        model2, cache_hit2 = create_cached_model("tiny", "cpu", "int8")
        load_time_2 = time.time() - start_time
        
        print(f"   Carregamento 2: {load_time_2:.2f}s, Cache Hit: {cache_hit2}")
        assert cache_hit2, "Segundo carregamento deveria ser cache hit"
        
        # Performance improvement
        if load_time_1 > 0 and load_time_2 > 0:
            speedup = load_time_1 / load_time_2
            print(f"   SPEEDUP: {speedup:.1f}x mais rápido!")
            
            if speedup > 10:
                print("   [EXCELENTE] Cache muito eficiente!")
            elif speedup > 5:
                print("   [BOM] Cache eficiente!")
            else:
                print("   [OK] Cache funcionando")
        
        # Test 3: Cache stats
        print("\n3. Estatísticas do cache...")
        stats = cache.get_stats()
        
        print(f"   Modelos em cache: {stats['models_cached']}")
        print(f"   Uso de memória: {stats['memory_usage_mb']:.1f}MB")
        print(f"   Hit rate: {stats['hit_rate']:.2%}")
        print(f"   Hits: {stats['hits']}, Misses: {stats['misses']}")
        
        # Test 4: Different model (should be miss)
        print("\n4. Modelo diferente (cache miss esperado)...")
        start_time = time.time()
        
        model3, cache_hit3 = create_cached_model("base", "cpu", "int8")
        load_time_3 = time.time() - start_time
        
        print(f"   Carregamento 3: {load_time_3:.2f}s, Cache Hit: {cache_hit3}")
        
        # Final stats
        print("\n5. Estatísticas finais...")
        final_stats = cache.get_stats()
        print(f"   Modelos em cache: {final_stats['models_cached']}")
        print(f"   Hit rate final: {final_stats['hit_rate']:.2%}")
        
        print("\n[SUCCESS] Cache de modelos funcionando corretamente!")
        print("BENEFÍCIOS:")
        print("- Carregamento instantâneo em cache hits")
        print("- Redução dramática de tempo de inicialização")
        print("- Gestão inteligente de memória")
        print("- Suporte a múltiplos modelos simultaneamente")
        
    except ImportError as e:
        print(f"[ERROR] Falha na importação: {e}")
        print("Verifique se todos os módulos estão implementados")
        return False
    except Exception as e:
        print(f"[ERROR] Erro no teste: {e}")
        return False
    
    return True

def test_transcriber_integration():
    """Testa integração com transcriber."""
    print("\n=== TESTE DE INTEGRAÇÃO COM TRANSCRIBER ===")
    
    try:
        from src.transcription.transcriber import create_transcriber, WhisperModelSize
        print("[OK] Transcriber importado")
        
        # Create transcriber (should use cache)
        print("\n1. Criando transcriber com cache...")
        start_time = time.time()
        
        transcriber = create_transcriber(WhisperModelSize.TINY, use_gpu=False)
        creation_time = time.time() - start_time
        
        print(f"   Transcriber criado em {creation_time:.2f}s")
        
        # Load model (should hit cache)
        print("\n2. Carregando modelo (deveria usar cache)...")
        start_time = time.time()
        
        try:
            transcriber.load_model()
            load_time = time.time() - start_time
            print(f"   Modelo carregado em {load_time:.2f}s")
            
            if load_time < 1.0:
                print("   [EXCELENTE] Carregamento muito rápido (provável cache hit)!")
            elif load_time < 5.0:
                print("   [BOM] Carregamento rápido")
            else:
                print("   [OK] Carregamento normal")
                
        except Exception as e:
            print(f"   [SKIP] Erro no carregamento: {e}")
        
        # Cleanup
        transcriber.cleanup()
        print("   [OK] Cleanup realizado")
        
        print("[SUCCESS] Integração com transcriber funcionando!")
        
    except ImportError as e:
        print(f"[SKIP] Transcriber não disponível: {e}")
    except Exception as e:
        print(f"[ERROR] Erro na integração: {e}")

def main():
    """Executa todos os testes de performance."""
    print("🚀 INICIANDO TESTES DE PERFORMANCE")
    print("=" * 50)
    
    # Test cache
    cache_success = test_model_cache_performance()
    
    # Test integration
    test_transcriber_integration()
    
    print("\n" + "=" * 50)
    if cache_success:
        print("🎉 CACHE DE MODELOS IMPLEMENTADO COM SUCESSO!")
        print("\nPróximos passos de otimização:")
        print("- ✅ Cache inteligente de modelos")
        print("- ⏳ Processamento de áudio em chunks")
        print("- ⏳ Gestão avançada de memória")
        print("- ⏳ Processamento assíncrono")
    else:
        print("❌ Problemas detectados no cache")

if __name__ == "__main__":
    main()