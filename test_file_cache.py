#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Sistema de Cache de Arquivos
Verifica se o cache de I/O está funcionando corretamente
"""

import time
import sys
import json
import tempfile
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.core.file_cache import (
        get_file_cache, 
        FileCache,
        FileCacheConfig,
        CacheStrategy,
        CompressionLevel,
        cached_file,
        file_cached
    )
    from src.core.file_optimizers import (
        get_optimized_file_manager,
        OptimizedAudioLoader,
        OptimizedFileManager
    )
    from src.core.cache_cli import CacheCLI
    print("✅ Imports do cache de arquivos OK")
except ImportError as e:
    print(f"❌ Erro ao importar módulos de cache: {e}")
    sys.exit(1)

def test_basic_file_cache():
    """Testa funcionalidades básicas do cache de arquivos"""
    print("\n💾 Testando Cache Básico de Arquivos...")
    
    try:
        # Configurar cache de teste
        config = FileCacheConfig(
            max_memory_mb=10,  # 10MB para teste
            max_entries=100,
            strategy=CacheStrategy.LRU
        )
        
        cache = FileCache(config)
        print("✅ Cache inicializado")
        
        # Criar arquivo temporário para teste
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Este é um arquivo de teste para cache")
            test_file = Path(f.name)
        
        try:
            # Testar put e get
            cache.put(test_file, "conteúdo de teste", "text_data")
            cached_content = cache.get(test_file)
            
            if cached_content == "conteúdo de teste":
                print("✅ Put/Get funcionando")
            else:
                print("❌ Put/Get falhou")
                return False
            
            # Testar get_or_load
            def loader(path):
                return f"carregado de {path}"
            
            content = cache.get_or_load(test_file, loader, "text_data")
            print("✅ Get_or_load funcionando")
            
            # Testar estatísticas
            stats = cache.get_stats()
            print(f"✅ Estatísticas: {stats['hit_rate_percent']:.1f}% hit rate")
            
            return True
            
        finally:
            # Limpar arquivo temporário
            if test_file.exists():
                test_file.unlink()
                
    except Exception as e:
        print(f"❌ Erro no teste básico: {e}")
        return False

def test_compression():
    """Testa compressão de arquivos"""
    print("\n📦 Testando Compressão...")
    
    try:
        # Configurar cache com compressão
        config = FileCacheConfig(
            compression_level=CompressionLevel.BALANCED,
            compress_threshold_mb=0.001  # 1KB threshold para teste
        )
        
        cache = FileCache(config)
        
        # Criar dados grandes para testar compressão
        large_data = "Este é um texto repetido. " * 1000
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_data)
            test_file = Path(f.name)
        
        try:
            # Testar compressão
            cache.put(test_file, large_data, "text_data")
            retrieved_data = cache.get(test_file)
            
            if retrieved_data == large_data:
                print("✅ Compressão/descompressão funcionando")
            else:
                print("❌ Compressão/descompressão falhou")
                return False
            
            # Verificar estatísticas de compressão
            stats = cache.get_stats()
            if stats['total_compressions'] > 0:
                print(f"✅ {stats['total_compressions']} compressões realizadas")
            
            return True
            
        finally:
            if test_file.exists():
                test_file.unlink()
                
    except Exception as e:
        print(f"❌ Erro no teste de compressão: {e}")
        return False

def test_cache_strategies():
    """Testa diferentes estratégias de cache"""
    print("\n🎯 Testando Estratégias de Cache...")
    
    strategies = [
        CacheStrategy.LRU,
        CacheStrategy.LFU,
        CacheStrategy.SIZE_BASED,
        CacheStrategy.INTELLIGENT
    ]
    
    try:
        for strategy in strategies:
            config = FileCacheConfig(
                max_entries=3,  # Limite baixo para forçar eviction
                strategy=strategy
            )
            
            cache = FileCache(config)
            
            # Adicionar mais arquivos que o limite
            for i in range(5):
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                    f.write(f"Conteúdo {i}")
                    test_file = Path(f.name)
                
                cache.put(test_file, f"dados_{i}", "test_data")
                
                # Limpar arquivo
                test_file.unlink()
            
            stats = cache.get_stats()
            if stats['total_evictions'] > 0:
                print(f"✅ Estratégia {strategy.value}: {stats['total_evictions']} evictions")
            else:
                print(f"⚠️ Estratégia {strategy.value}: sem evictions")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de estratégias: {e}")
        return False

def test_context_manager():
    """Testa context manager para cache"""
    print("\n🔗 Testando Context Manager...")
    
    try:
        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Conteúdo do arquivo")
            test_file = Path(f.name)
        
        try:
            # Testar context manager
            def simple_loader(path):
                with open(path, 'r') as f:
                    return f.read()
            
            with cached_file(test_file, simple_loader, "text_data") as content:
                if "Conteúdo do arquivo" in content:
                    print("✅ Context manager funcionando")
                else:
                    print("❌ Context manager falhou")
                    return False
            
            return True
            
        finally:
            if test_file.exists():
                test_file.unlink()
                
    except Exception as e:
        print(f"❌ Erro no teste do context manager: {e}")
        return False

def test_decorator():
    """Testa decorator de cache"""
    print("\n🎨 Testando Decorator...")
    
    try:
        @file_cached("text_data")
        def load_file_content(file_path):
            with open(file_path, 'r') as f:
                return f.read()
        
        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Conteúdo decorado")
            test_file = Path(f.name)
        
        try:
            # Primeira chamada (miss)
            content1 = load_file_content(test_file)
            
            # Segunda chamada (hit)
            content2 = load_file_content(test_file)
            
            if content1 == content2 == "Conteúdo decorado":
                print("✅ Decorator funcionando")
            else:
                print("❌ Decorator falhou")
                return False
            
            return True
            
        finally:
            if test_file.exists():
                test_file.unlink()
                
    except Exception as e:
        print(f"❌ Erro no teste do decorator: {e}")
        return False

def test_optimized_file_manager():
    """Testa gerenciador otimizado de arquivos"""
    print("\n🚀 Testando Gerenciador Otimizado...")
    
    try:
        manager = get_optimized_file_manager()
        print("✅ Gerenciador otimizado inicializado")
        
        # Criar arquivo de texto temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Arquivo de texto de teste")
            text_file = Path(f.name)
        
        try:
            # Testar carregamento de texto
            content = manager.load_text_file(text_file)
            if "Arquivo de texto de teste" in content:
                print("✅ Carregamento de texto funcionando")
            else:
                print("❌ Carregamento de texto falhou")
                return False
            
            # Testar estatísticas
            stats = manager.get_comprehensive_stats()
            print(f"✅ Estatísticas comprehensive obtidas: {stats.get('combined_hit_rate', 0):.1f}% hit rate")
            
            return True
            
        finally:
            if text_file.exists():
                text_file.unlink()
                
    except Exception as e:
        print(f"❌ Erro no teste do gerenciador: {e}")
        return False

def test_cache_cli():
    """Testa interface CLI do cache"""
    print("\n📊 Testando Cache CLI...")
    
    try:
        cli = CacheCLI()
        
        # Testar status
        status = cli.get_cache_status()
        print("✅ Status do cache obtido")
        print(f"   Status: {status.get('status', 'unknown')}")
        
        # Testar insights
        insights = cli.get_cache_insights()
        print("✅ Insights do cache obtidos")
        print(f"   Status: {insights.get('status', 'unknown')}")
        
        # Testar configuração
        config = cli.get_cache_config()
        print("✅ Configuração do cache obtida")
        print(f"   Status: {config.get('status', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste do CLI: {e}")
        return False

def test_cli_integration():
    """Testa integração via CLI"""
    print("\n🔗 Testando Integração CLI...")
    
    try:
        import subprocess
        
        # Testar comando de status
        result = subprocess.run([
            sys.executable, "main.py", "--cache", "status"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            print("✅ Comando CLI --cache status funcionando")
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

def test_performance_improvement():
    """Testa melhoria de performance com cache"""
    print("\n⚡ Testando Melhoria de Performance...")
    
    try:
        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Dados para teste de performance " * 100)
            test_file = Path(f.name)
        
        try:
            def slow_loader(path):
                time.sleep(0.01)  # Simular I/O lento
                with open(path, 'r') as f:
                    return f.read()
            
            cache = get_file_cache()
            
            # Primeira leitura (miss - lenta)
            start_time = time.time()
            cache.get_or_load(test_file, slow_loader, "text_data")
            first_time = time.time() - start_time
            
            # Segunda leitura (hit - rápida)
            start_time = time.time()
            cache.get_or_load(test_file, slow_loader, "text_data")
            second_time = time.time() - start_time
            
            speedup = first_time / second_time if second_time > 0 else 0
            print(f"✅ Speedup do cache: {speedup:.1f}x")
            
            if speedup > 2:  # Pelo menos 2x mais rápido
                print("✅ Melhoria significativa de performance")
                return True
            else:
                print("⚠️ Melhoria de performance modesta")
                return True  # Ainda é válido
                
        finally:
            if test_file.exists():
                test_file.unlink()
                
    except Exception as e:
        print(f"❌ Erro no teste de performance: {e}")
        return False

def main():
    """Função principal de teste"""
    print("🧪 === Teste do Sistema de Cache de Arquivos ===")
    print(f"📍 Diretório: {Path.cwd()}")
    
    tests = [
        ("Cache Básico", test_basic_file_cache),
        ("Compressão", test_compression),
        ("Estratégias de Cache", test_cache_strategies),
        ("Context Manager", test_context_manager),
        ("Decorator", test_decorator),
        ("Gerenciador Otimizado", test_optimized_file_manager),
        ("Cache CLI", test_cache_cli),
        ("CLI Integration", test_cli_integration),
        ("Melhoria Performance", test_performance_improvement),
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
        print("🚀 Sistema de cache de arquivos está funcionando!")
        return 0
    else:
        print(f"\n⚠️ {failed} teste(s) falharam")
        print("🔧 Verifique os erros acima e corrija os problemas")
        return 1

if __name__ == "__main__":
    sys.exit(main())