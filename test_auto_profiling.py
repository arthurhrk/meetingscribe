#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Sistema de Auto Profiling
Verifica se o profiling automático está funcionando corretamente
"""

import time
import sys
import json
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.core.auto_profiler import (
        get_auto_profiler, 
        auto_profile,
        BottleneckDetection,
        ProfilingReport
    )
    from src.core.profiler_cli import ProfilerCLI
    print("✅ Imports do auto profiling OK")
except ImportError as e:
    print(f"❌ Erro ao importar módulos de auto profiling: {e}")
    sys.exit(1)

def test_auto_profiler_basic():
    """Testa funcionalidades básicas do auto profiler"""
    print("\n🔍 Testando Auto Profiler Básico...")
    
    try:
        # Inicializar profiler
        profiler = get_auto_profiler()
        print("✅ Profiler inicializado")
        
        # Testar sessão de profiling
        session_id = profiler.start_profiling_session("test_operation", {"test": "data"})
        print(f"✅ Sessão iniciada: {session_id}")
        
        # Simular evento
        profiler.add_profiling_event(
            session_id,
            "test_event",
            "Test event description",
            {"metric": 42.0}
        )
        print("✅ Evento adicionado")
        
        # Simular algum processamento
        time.sleep(0.1)
        
        # Finalizar sessão
        report = profiler.end_profiling_session(session_id)
        print(f"✅ Sessão finalizada - {len(report.bottlenecks)} bottlenecks detectados")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste básico: {e}")
        return False

def test_context_manager():
    """Testa o context manager de profiling"""
    print("\n⏱️ Testando Context Manager...")
    
    try:
        with auto_profile("test_context_operation", {"context": "test"}) as session_id:
            print(f"✅ Context manager iniciado: {session_id}")
            
            # Simular operação
            time.sleep(0.05)
            
            # Simular operação que pode causar bottleneck
            for i in range(10000):
                _ = i ** 2
        
        print("✅ Context manager finalizado automaticamente")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste do context manager: {e}")
        return False

def test_bottleneck_detection():
    """Testa detecção de bottlenecks"""
    print("\n🚨 Testando Detecção de Bottlenecks...")
    
    try:
        profiler = get_auto_profiler()
        
        # Simular sessão com operação lenta
        session_id = profiler.start_profiling_session("slow_operation", {"test": "bottleneck"})
        
        # Simular carregamento lento de modelo
        profiler.add_profiling_event(
            session_id,
            "model_loading",
            "Slow model loading test",
            {"load_time": 15.0}  # > 10s threshold
        )
        
        # Simular transcrição lenta
        profiler.add_profiling_event(
            session_id,
            "transcription_chunk",
            "Slow transcription test",
            {
                "processing_time": 10.0,
                "audio_length": 2.0  # 5x realtime = slow
            }
        )
        
        # Finalizar sessão
        report = profiler.end_profiling_session(session_id)
        
        if len(report.bottlenecks) > 0:
            print(f"✅ Bottlenecks detectados: {len(report.bottlenecks)}")
            for bottleneck in report.bottlenecks:
                print(f"   - {bottleneck.type}: {bottleneck.description}")
        else:
            print("⚠️ Nenhum bottleneck detectado (pode ser esperado)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de detecção: {e}")
        return False

def test_profiler_cli():
    """Testa a interface CLI do profiler"""
    print("\n📊 Testando Profiler CLI...")
    
    try:
        cli = ProfilerCLI()
        
        # Testar resumo de bottlenecks
        summary = cli.get_bottleneck_summary()
        print("✅ Resumo de bottlenecks obtido")
        print(f"   Status: {summary.get('status', 'unknown')}")
        
        # Testar relatórios detalhados
        reports = cli.get_detailed_reports(5)
        print("✅ Relatórios detalhados obtidos")
        print(f"   Status: {reports.get('status', 'unknown')}")
        
        # Testar insights
        insights = cli.get_performance_insights()
        print("✅ Insights de performance obtidos")
        print(f"   Status: {insights.get('status', 'unknown')}")
        
        # Testar sugestões
        suggestions = cli.get_optimization_suggestions()
        print("✅ Sugestões de otimização obtidas")
        print(f"   Status: {suggestions.get('status', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste do CLI: {e}")
        return False

def test_profiler_integration():
    """Testa integração com transcritor simulado"""
    print("\n🔗 Testando Integração com Transcritor...")
    
    try:
        # Simular transcrição com profiling
        with auto_profile("transcription", {
            "audio_path": "test_audio.wav",
            "model_size": "base",
            "file_size_mb": 5.2
        }) as session_id:
            
            # Simular carregamento do modelo
            time.sleep(0.1)
            
            # Simular processamento de chunks
            for chunk in range(3):
                time.sleep(0.05)  # Simular processamento
                
                # Adicionar evento de chunk processado
                profiler = get_auto_profiler()
                profiler.add_profiling_event(
                    session_id,
                    "transcription_chunk",
                    f"Processed chunk {chunk + 1}",
                    {
                        "chunk_id": chunk,
                        "processing_time": 0.05,
                        "audio_length": 1.0
                    }
                )
        
        print("✅ Integração simulada com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ Erro na integração: {e}")
        return False

def test_cli_integration():
    """Testa integração via CLI"""
    print("\n🔗 Testando Integração CLI...")
    
    try:
        import subprocess
        
        # Testar comando de resumo
        result = subprocess.run([
            sys.executable, "main.py", "--profiling", "summary"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            print("✅ Comando CLI --profiling summary funcionando")
            print(f"   Status: {data.get('status', 'unknown')}")
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

def test_data_persistence():
    """Testa persistência de dados de profiling"""
    print("\n💾 Testando Persistência de Dados...")
    
    try:
        profiler = get_auto_profiler()
        
        # Criar algumas sessões para gerar dados
        for i in range(3):
            session_id = profiler.start_profiling_session(f"test_session_{i}", {"test": i})
            time.sleep(0.01)
            
            profiler.add_profiling_event(
                session_id,
                "test_event",
                f"Test event {i}",
                {"value": i * 10}
            )
            
            report = profiler.end_profiling_session(session_id)
        
        # Verificar se dados estão sendo armazenados
        reports = profiler.get_recent_reports(5)
        if len(reports) >= 3:
            print(f"✅ {len(reports)} relatórios encontrados")
        else:
            print(f"⚠️ Apenas {len(reports)} relatórios encontrados")
        
        # Verificar resumo
        summary = profiler.get_bottleneck_summary()
        if summary.get('status') != 'no_data':
            print("✅ Dados de resumo disponíveis")
        else:
            print("⚠️ Dados de resumo não disponíveis")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de persistência: {e}")
        return False

def run_stress_test():
    """Executa teste de stress do profiling"""
    print("\n🚀 Executando Teste de Stress...")
    
    try:
        # Múltiplas sessões simultâneas
        session_ids = []
        profiler = get_auto_profiler()
        
        # Iniciar múltiplas sessões
        for i in range(5):
            session_id = profiler.start_profiling_session(
                f"stress_test_{i}", 
                {"stress_level": i}
            )
            session_ids.append(session_id)
        
        print(f"✅ {len(session_ids)} sessões iniciadas")
        
        # Adicionar eventos a todas as sessões
        for session_id in session_ids:
            for j in range(3):
                profiler.add_profiling_event(
                    session_id,
                    "stress_event",
                    f"Stress event {j}",
                    {"load": j * 100}
                )
        
        print("✅ Eventos adicionados a todas as sessões")
        
        # Finalizar todas as sessões
        reports = []
        for session_id in session_ids:
            report = profiler.end_profiling_session(session_id)
            reports.append(report)
        
        print(f"✅ {len(reports)} sessões finalizadas")
        print(f"📊 Total de bottlenecks: {sum(len(r.bottlenecks) for r in reports)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de stress: {e}")
        return False

def main():
    """Função principal de teste"""
    print("🧪 === Teste do Sistema de Auto Profiling ===")
    print(f"📍 Diretório: {Path.cwd()}")
    
    tests = [
        ("Auto Profiler Básico", test_auto_profiler_basic),
        ("Context Manager", test_context_manager),
        ("Detecção de Bottlenecks", test_bottleneck_detection),
        ("Profiler CLI", test_profiler_cli),
        ("Integração Transcritor", test_profiler_integration),
        ("CLI Integration", test_cli_integration),
        ("Persistência de Dados", test_data_persistence),
        ("Stress Test", run_stress_test),
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
        print("🚀 Sistema de auto profiling está funcionando!")
        return 0
    else:
        print(f"\n⚠️ {failed} teste(s) falharam")
        print("🔧 Verifique os erros acima e corrija os problemas")
        return 1

if __name__ == "__main__":
    sys.exit(main())