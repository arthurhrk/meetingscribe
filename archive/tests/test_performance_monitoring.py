#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Sistema de Monitoramento de Performance
Verifica se todas as funcionalidades de performance estão funcionando
"""

import time
import json
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.core.performance_monitor import (
        get_performance_monitor, 
        TranscriptionMetrics, 
        PerformanceTimer
    )
    from src.core.raycast_metrics_cli import RaycastMetricsCLI
    print("✅ Imports do monitoramento de performance OK")
except ImportError as e:
    print(f"❌ Erro ao importar módulos de performance: {e}")
    sys.exit(1)

def test_performance_monitor():
    """Testa o monitor de performance"""
    print("\n🔍 Testando Performance Monitor...")
    
    try:
        # Inicializar monitor
        monitor = get_performance_monitor()
        print("✅ Monitor inicializado")
        
        # Testar adição de métrica
        monitor.add_metric("test_metric", 42.0, "test_unit", "test_category")
        print("✅ Métrica adicionada")
        
        # Testar métricas de transcrição
        test_metrics = TranscriptionMetrics(
            duration=10.5,
            audio_length=10.5,
            model_size="base",
            chunks_count=1,
            processing_time=2.3,
            cache_hits=1,
            memory_used=150.0,
            gpu_used=False,
            success=True
        )
        
        monitor.add_transcription_metrics(test_metrics)
        print("✅ Métricas de transcrição adicionadas")
        
        # Testar obtenção de métricas
        raycast_metrics = monitor.get_metrics_for_raycast()
        print("✅ Métricas para Raycast obtidas")
        print(f"   Sistema: {raycast_metrics['system']['status']}")
        print(f"   Cache: {raycast_metrics['cache']['status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste do monitor: {e}")
        return False

def test_performance_timer():
    """Testa o timer de performance"""
    print("\n⏱️ Testando Performance Timer...")
    
    try:
        # Testar context manager
        with PerformanceTimer("test_operation", "test"):
            time.sleep(0.1)  # Simular operação
        
        print("✅ Performance Timer funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste do timer: {e}")
        return False

def test_raycast_cli():
    """Testa a interface CLI para Raycast"""
    print("\n📊 Testando Raycast CLI...")
    
    try:
        cli = RaycastMetricsCLI()
        
        # Testar status do sistema
        status = cli.get_system_status()
        print("✅ Status do sistema obtido")
        print(f"   Health: {status.get('health', 'unknown')}")
        
        # Testar dashboard
        dashboard = cli.get_dashboard_data()
        print("✅ Dashboard obtido")
        print(f"   Status: {dashboard.get('status', 'unknown')}")
        
        # Testar cache
        cache_status = cli.get_cache_status()
        print("✅ Status do cache obtido")
        print(f"   Status: {cache_status.get('status', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste do CLI: {e}")
        return False

def test_cli_integration():
    """Testa integração com main.py via CLI"""
    print("\n🔗 Testando Integração CLI...")
    
    try:
        import subprocess
        
        # Testar comando de status
        result = subprocess.run([
            sys.executable, "main.py", "--performance", "status"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            print("✅ Comando CLI --performance status funcionando")
            print(f"   Health: {data.get('health', 'unknown')}")
        else:
            print(f"❌ Comando CLI falhou: {result.stderr}")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout no comando CLI")
        return False
    except Exception as e:
        print(f"❌ Erro no teste CLI: {e}")
        return False

def test_metric_persistence():
    """Testa persistência de métricas"""
    print("\n💾 Testando Persistência de Métricas...")
    
    try:
        monitor = get_performance_monitor()
        
        # Adicionar algumas métricas
        for i in range(5):
            monitor.add_metric(f"test_persist_{i}", float(i), "count", "test")
        
        # Forçar persistência
        monitor._persist_metrics()
        print("✅ Métricas persistidas")
        
        # Verificar arquivo
        metrics_file = Path("storage/metrics/performance_metrics.json")
        if metrics_file.exists():
            print("✅ Arquivo de métricas existe")
            
            with open(metrics_file, 'r') as f:
                data = json.load(f)
            
            if data.get('metrics'):
                print(f"✅ {len(data['metrics'])} métricas salvas")
            else:
                print("❌ Nenhuma métrica encontrada no arquivo")
                return False
        else:
            print("❌ Arquivo de métricas não encontrado")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de persistência: {e}")
        return False

def run_performance_benchmark():
    """Executa benchmark básico do sistema"""
    print("\n🚀 Executando Benchmark de Performance...")
    
    try:
        monitor = get_performance_monitor()
        
        # Simular várias operações
        operations = [
            ("cpu_intensive", lambda: sum(i**2 for i in range(10000))),
            ("memory_allocation", lambda: [i for i in range(100000)]),
            ("file_operation", lambda: Path("test_file.tmp").write_text("test")),
        ]
        
        results = []
        
        for name, operation in operations:
            with PerformanceTimer(name, "benchmark") as timer:
                operation()
                time.sleep(0.01)  # Pequena pausa
            
            # A métrica foi automaticamente adicionada pelo timer
            results.append(name)
        
        # Limpar arquivo temporário
        test_file = Path("test_file.tmp")
        if test_file.exists():
            test_file.unlink()
        
        print(f"✅ Benchmark concluído: {len(results)} operações")
        
        # Obter resumo das métricas
        metrics = monitor.get_metrics_for_raycast()
        print(f"✅ Métricas coletadas: {len(metrics.get('recent_metrics', []))} recentes")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no benchmark: {e}")
        return False

def main():
    """Função principal de teste"""
    print("🧪 === Teste do Sistema de Monitoramento de Performance ===")
    print(f"📍 Diretório: {Path.cwd()}")
    
    tests = [
        ("Performance Monitor", test_performance_monitor),
        ("Performance Timer", test_performance_timer),
        ("Raycast CLI", test_raycast_cli),
        ("CLI Integration", test_cli_integration),
        ("Metric Persistence", test_metric_persistence),
        ("Performance Benchmark", run_performance_benchmark),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 TESTE: {test_name}")
        print('='*50)
        
        try:
            if test_func():
                print(f"✅ {test_name}: PASSOU")
                passed += 1
            else:
                print(f"❌ {test_name}: FALHOU")
                failed += 1
        except Exception as e:
            print(f"💥 {test_name}: ERRO - {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print("📊 RESUMO DOS TESTES")
    print('='*50)
    print(f"✅ Passaram: {passed}")
    print(f"❌ Falharam: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("🚀 Sistema de monitoramento de performance está funcionando!")
        return 0
    else:
        print(f"\n⚠️ {failed} teste(s) falharam")
        print("🔧 Verifique os erros acima e corrija os problemas")
        return 1

if __name__ == "__main__":
    sys.exit(main())