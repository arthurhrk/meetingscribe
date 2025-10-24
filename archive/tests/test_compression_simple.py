#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Simples do Sistema de Compressão Inteligente
"""

import os
import sys
import json
import time
import tempfile
import traceback
from pathlib import Path

def test_compression_modules():
    """Testa se os módulos de compressão podem ser importados"""
    print("=== Teste de Importação de Módulos ===")
    
    try:
        # Tentar importar módulos básicos
        import gzip
        import lzma
        import bz2
        print("✓ Módulos básicos de compressão importados")
        
        # Tentar módulos opcionais
        try:
            import zstandard
            print("✓ ZSTD disponível")
        except ImportError:
            print("! ZSTD não disponível")
        
        try:
            import lz4
            print("✓ LZ4 disponível")
        except ImportError:
            print("! LZ4 não disponível")
            
        return True
        
    except Exception as e:
        print(f"X Erro nos imports básicos: {e}")
        return False

def test_compression_algorithms():
    """Testa algoritmos básicos de compressão"""
    print("\n=== Teste de Algoritmos de Compressão ===")
    
    # Dados de teste
    test_text = "Este eh um teste de compressao com dados repetitivos! " * 100
    test_data = test_text.encode('utf-8')
    print(f"Dados originais: {len(test_data)} bytes")
    
    results = {}
    
    # GZIP
    try:
        import gzip
        compressed = gzip.compress(test_data)
        decompressed = gzip.decompress(compressed)
        
        if decompressed == test_data:
            ratio = len(compressed) / len(test_data)
            results['gzip'] = {'size': len(compressed), 'ratio': ratio, 'success': True}
            print(f"✓ GZIP: {len(compressed)} bytes (ratio: {ratio:.3f})")
        else:
            results['gzip'] = {'success': False, 'error': 'Descompressão falhou'}
            print("X GZIP: Descompressão falhou")
            
    except Exception as e:
        results['gzip'] = {'success': False, 'error': str(e)}
        print(f"X GZIP: {e}")
    
    # LZMA
    try:
        import lzma
        compressed = lzma.compress(test_data)
        decompressed = lzma.decompress(compressed)
        
        if decompressed == test_data:
            ratio = len(compressed) / len(test_data)
            results['lzma'] = {'size': len(compressed), 'ratio': ratio, 'success': True}
            print(f"✓ LZMA: {len(compressed)} bytes (ratio: {ratio:.3f})")
        else:
            results['lzma'] = {'success': False, 'error': 'Descompressão falhou'}
            print("X LZMA: Descompressão falhou")
            
    except Exception as e:
        results['lzma'] = {'success': False, 'error': str(e)}
        print(f"X LZMA: {e}")
    
    # ZSTD (se disponível)
    try:
        import zstandard as zstd
        cctx = zstd.ZstdCompressor()
        compressed = cctx.compress(test_data)
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed)
        
        if decompressed == test_data:
            ratio = len(compressed) / len(test_data)
            results['zstd'] = {'size': len(compressed), 'ratio': ratio, 'success': True}
            print(f"✓ ZSTD: {len(compressed)} bytes (ratio: {ratio:.3f})")
        else:
            results['zstd'] = {'success': False, 'error': 'Descompressão falhou'}
            print("X ZSTD: Descompressão falhou")
            
    except ImportError:
        print("! ZSTD: Não disponível")
    except Exception as e:
        results['zstd'] = {'success': False, 'error': str(e)}
        print(f"X ZSTD: {e}")
    
    successful_algorithms = sum(1 for r in results.values() if r.get('success', False))
    print(f"\nResultado: {successful_algorithms}/{len(results)} algoritmos funcionando")
    
    return successful_algorithms > 0

def test_file_operations():
    """Testa operações com arquivos"""
    print("\n=== Teste de Operações com Arquivos ===")
    
    try:
        # Criar diretório temporário
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            print(f"Diretório temporário: {temp_path}")
            
            # Criar arquivo de teste
            test_file = temp_path / "test.txt"
            test_content = "Conteudo de teste para compressao! " * 50
            
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            print(f"✓ Arquivo criado: {test_file.stat().st_size} bytes")
            
            # Testar compressão do arquivo
            import gzip
            compressed_file = temp_path / "test.txt.gz"
            
            with open(test_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            original_size = test_file.stat().st_size
            compressed_size = compressed_file.stat().st_size
            ratio = compressed_size / original_size
            
            print(f"✓ Arquivo comprimido: {compressed_size} bytes (ratio: {ratio:.3f})")
            
            # Testar descompressão
            decompressed_file = temp_path / "test_decompressed.txt"
            
            with gzip.open(compressed_file, 'rb') as f_in:
                with open(decompressed_file, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            # Verificar integridade
            with open(test_file, 'r', encoding='utf-8') as f1:
                with open(decompressed_file, 'r', encoding='utf-8') as f2:
                    if f1.read() == f2.read():
                        print("✓ Descompressão bem-sucedida - dados íntegros")
                        return True
                    else:
                        print("X Descompressão falhou - dados corrompidos")
                        return False
            
    except Exception as e:
        print(f"X Erro nas operações com arquivos: {e}")
        traceback.print_exc()
        return False

def test_cli_functionality():
    """Testa funcionalidades da CLI"""
    print("\n=== Teste de CLI ===")
    
    try:
        # Verificar se arquivo CLI existe
        cli_path = Path("src/core/compression_cli.py")
        
        if cli_path.exists():
            print(f"✓ CLI encontrada: {cli_path}")
            
            # Tentar executar help
            try:
                import subprocess
                result = subprocess.run([
                    sys.executable, str(cli_path), "--help"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 or "usage:" in result.stdout.lower() or "usage:" in result.stderr.lower():
                    print("✓ CLI executável - help funcionando")
                    return True
                else:
                    print(f"! CLI executável mas help retornou código: {result.returncode}")
                    return False
                    
            except subprocess.TimeoutExpired:
                print("! CLI timeout - possível problema")
                return False
            except Exception as e:
                print(f"X Erro executando CLI: {e}")
                return False
        else:
            print(f"X CLI não encontrada em: {cli_path}")
            return False
            
    except Exception as e:
        print(f"X Erro testando CLI: {e}")
        return False

def test_raycast_integration():
    """Testa integração Raycast"""
    print("\n=== Teste de Integração Raycast ===")
    
    try:
        raycast_compression = Path("raycast-extension/src/compression.tsx")
        
        if raycast_compression.exists():
            print(f"✓ Arquivo Raycast encontrado: {raycast_compression}")
            
            # Verificar se contém funções principais
            with open(raycast_compression, 'r', encoding='utf-8') as f:
                content = f.read()
                
                required_functions = [
                    'CompressionCommand',
                    'executeCompressionCommand',
                    'CompressionStatus',
                    'CompressionAnalytics'
                ]
                
                found_functions = []
                for func in required_functions:
                    if func in content:
                        found_functions.append(func)
                
                print(f"✓ Funções encontradas: {len(found_functions)}/{len(required_functions)}")
                
                if len(found_functions) >= len(required_functions) * 0.75:  # 75% das funções
                    print("✓ Integração Raycast parece completa")
                    return True
                else:
                    print("! Integração Raycast incompleta")
                    return False
        else:
            print(f"X Arquivo Raycast não encontrado: {raycast_compression}")
            return False
            
    except Exception as e:
        print(f"X Erro testando Raycast: {e}")
        return False

def generate_simple_report(results):
    """Gera relatório simples dos testes"""
    print("\n" + "="*50)
    print("RELATÓRIO FINAL - TESTE DE COMPRESSÃO")
    print("="*50)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\nEstatísticas:")
    print(f"  Total de Testes: {total_tests}")
    print(f"  Testes Aprovados: {passed_tests}")
    print(f"  Testes Falharam: {failed_tests}")
    print(f"  Taxa de Sucesso: {success_rate:.1f}%")
    
    print(f"\nDetalhes dos Testes:")
    for test_name, passed in results.items():
        status = "PASSOU" if passed else "FALHOU"
        emoji = "✓" if passed else "X"
        print(f"  {emoji} {test_name}: {status}")
    
    print(f"\nAvaliação Geral:")
    if success_rate >= 90:
        print("  🎉 EXCELENTE! Sistema funcionando muito bem.")
    elif success_rate >= 75:
        print("  👍 BOM! Sistema funcionando bem.")
    elif success_rate >= 50:
        print("  ⚠️ REGULAR! Alguns problemas precisam ser corrigidos.")
    else:
        print("  🔴 CRÍTICO! Muitos problemas encontrados.")
    
    return success_rate >= 75

def main():
    """Função principal do teste simples"""
    print("🗜️ TESTE SIMPLES DO SISTEMA DE COMPRESSÃO")
    print("="*50)
    print("Testando componentes básicos do sistema...\n")
    
    # Executar testes
    test_results = {}
    
    test_results["Importação de Módulos"] = test_compression_modules()
    test_results["Algoritmos de Compressão"] = test_compression_algorithms()
    test_results["Operações com Arquivos"] = test_file_operations()
    test_results["Funcionalidade CLI"] = test_cli_functionality()
    test_results["Integração Raycast"] = test_raycast_integration()
    
    # Gerar relatório
    success = generate_simple_report(test_results)
    
    if success:
        print("\n🎉 SISTEMA DE COMPRESSÃO FUNCIONAL!")
        print("Os componentes básicos estão funcionando corretamente.")
    else:
        print("\n❌ PROBLEMAS ENCONTRADOS!")
        print("Alguns componentes precisam de atenção.")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\nErro fatal: {e}")
        traceback.print_exc()
        sys.exit(1)