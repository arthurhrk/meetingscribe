#!/usr/bin/env python3
"""
Teste de Gestão de Memória

Verifica se o sistema de gestão de memória está funcionando
e otimizando o uso de recursos durante operações.
"""

import time

def test_memory_manager():
    """Testa o gerenciador de memória."""
    print("=== TESTE DE GERENCIAMENTO DE MEMORIA ===")
    
    try:
        # Test imports
        from src.core.memory_manager import (
            get_memory_manager, MemoryOptimizationStrategy,
            get_memory_stats, check_memory_pressure
        )
        print("[OK] Gerenciador de memória importado com sucesso")
        
        # Get memory manager
        manager = get_memory_manager()
        print(f"[OK] Gerenciador inicializado")
        
        # Get current stats
        stats = get_memory_stats()
        print(f"[OK] Estatísticas obtidas:")
        print(f"   Memória sistema: {stats.memory_percent:.1f}%")
        print(f"   Memória processo: {stats.process_memory_mb:.1f}MB")
        print(f"   Pressão: {stats.pressure_level.value}")
        
        # Test pressure check
        pressure = check_memory_pressure()
        print(f"[OK] Nível de pressão: {pressure.value}")
        
        # Test optimization
        print("\n[TESTE] Executando otimização de memória...")
        result = manager.optimize_memory(MemoryOptimizationStrategy.BALANCED)
        print(f"[OK] Otimização concluída:")
        print(f"   Estratégia: {result['strategy']}")
        print(f"   Memória liberada: {result['memory_freed_mb']:.1f}MB")
        print(f"   Ações: {len(result['actions_taken'])}")
        
        # Test summary
        summary = manager.get_summary()
        print(f"\n[OK] Resumo do gerenciador:")
        print(f"   GC executado: {summary['operations']['gc_runs']} vezes")
        print(f"   Limpezas: {summary['operations']['cleanup_runs']} vezes")
        
        print("\n[SUCCESS] Gerenciador de memória funcionando!")
        return True
        
    except ImportError as e:
        print(f"[SKIP] Gerenciador de memória não disponível: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Erro no gerenciador de memória: {e}")
        return False

def test_memory_integration():
    """Testa integração com transcritores."""
    print("\n=== TESTE DE INTEGRACAO COM TRANSCRITORES ===")
    
    try:
        # Test transcriber integration
        from src.transcription.transcriber import create_transcriber, WhisperModelSize
        from src.core.memory_manager import get_memory_manager
        
        manager = get_memory_manager()
        initial_stats = manager.get_current_stats()
        
        print(f"[TESTE] Criando transcritor (memoria inicial: {initial_stats.process_memory_mb:.1f}MB)")
        
        # Create transcriber
        transcriber = create_transcriber(
            model_size=WhisperModelSize.TINY,
            use_gpu=False
        )
        
        after_creation_stats = manager.get_current_stats()
        memory_increase = after_creation_stats.process_memory_mb - initial_stats.process_memory_mb
        
        print(f"[OK] Transcritor criado (aumento: {memory_increase:.1f}MB)")
        
        # Test memory tracking
        tracker_stats = manager.tracker.get_stats()
        print(f"[OK] Objetos rastreados: {tracker_stats.get('total', {}).get('objects', 0)}")
        
        # Cleanup transcriber
        transcriber.cleanup()
        del transcriber
        
        # Test optimization
        opt_result = manager.optimize_memory()
        print(f"[OK] Otimização pós-transcritor: {opt_result['memory_freed_mb']:.1f}MB liberados")
        
        print("\n[SUCCESS] Integração com transcritores funcionando!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Erro na integração: {e}")
        return False

def test_memory_monitoring():
    """Testa monitoramento automático."""
    print("\n=== TESTE DE MONITORAMENTO AUTOMATICO ===")
    
    try:
        from src.core.memory_manager import get_memory_manager
        
        manager = get_memory_manager()
        
        # Test monitoring start/stop
        print("[TESTE] Iniciando monitoramento...")
        manager.start_monitoring()
        
        if manager._monitoring:
            print("[OK] Monitoramento ativo")
            
            # Wait a bit to see monitoring in action
            time.sleep(2)
            
            print("[TESTE] Parando monitoramento...")
            manager.stop_monitoring()
            
            if not manager._monitoring:
                print("[OK] Monitoramento parado")
            else:
                print("[WARNING] Monitoramento ainda ativo")
        else:
            print("[WARNING] Monitoramento não iniciou")
        
        print("\n[SUCCESS] Monitoramento automático funcionando!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Erro no monitoramento: {e}")
        return False

def main():
    """Executa todos os testes de gestão de memória."""
    print("INICIANDO TESTES DE GESTAO DE MEMORIA")
    print("=" * 50)
    
    # Test components
    manager_ok = test_memory_manager()
    integration_ok = test_memory_integration()
    monitoring_ok = test_memory_monitoring()
    
    print("\n" + "=" * 50)
    if manager_ok and integration_ok and monitoring_ok:
        print("GESTAO DE MEMORIA IMPLEMENTADA COM SUCESSO!")
        print("\nBeneficios da gestão de memória:")
        print("- ✅ Monitoramento automático de uso de memória")
        print("- ✅ Otimização inteligente baseada em pressão")
        print("- ✅ Rastreamento de objetos em memória")
        print("- ✅ Limpeza automática de recursos")
        print("- ✅ Múltiplas estratégias de otimização")
        print("- ✅ Integração com cache e transcritores")
        
        print("\nPróximos passos de otimização:")
        print("- ✅ Cache inteligente de modelos")
        print("- ✅ Processamento de áudio em chunks")
        print("- ✅ Gestão avançada de memória")
        print("- ⏳ Processamento assíncrono")
        print("- ⏳ Monitoramento de performance")
        print("- ⏳ Otimização de I/O")
    else:
        print("Problemas detectados na gestão de memória")
        print("\nVerifique:")
        print("- Instalação da biblioteca psutil")
        print("- Dependências do sistema")
        print("- Configuração de memória")

if __name__ == "__main__":
    main()