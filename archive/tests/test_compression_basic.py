#!/usr/bin/env python3
"""
Teste Básico do Sistema de Compressão
"""

import os
import sys
import gzip
import lzma
import tempfile
from pathlib import Path

def test_basic_compression():
    """Teste básico de compressão"""
    print("=== Teste Básico de Compressão ===")
    
    # Dados de teste
    test_text = "Este eh um teste de compressao com dados repetitivos! " * 100
    test_data = test_text.encode('utf-8')
    print(f"Dados originais: {len(test_data)} bytes")
    
    results = []
    
    # Teste GZIP
    try:
        compressed = gzip.compress(test_data)
        decompressed = gzip.decompress(compressed)
        
        if decompressed == test_data:
            ratio = len(compressed) / len(test_data)
            print(f"GZIP: OK - {len(compressed)} bytes (ratio: {ratio:.3f})")
            results.append(True)
        else:
            print("GZIP: FALHA - Descompressao incorreta")
            results.append(False)
    except Exception as e:
        print(f"GZIP: ERRO - {e}")
        results.append(False)
    
    # Teste LZMA
    try:
        compressed = lzma.compress(test_data)
        decompressed = lzma.decompress(compressed)
        
        if decompressed == test_data:
            ratio = len(compressed) / len(test_data)
            print(f"LZMA: OK - {len(compressed)} bytes (ratio: {ratio:.3f})")
            results.append(True)
        else:
            print("LZMA: FALHA - Descompressao incorreta")
            results.append(False)
    except Exception as e:
        print(f"LZMA: ERRO - {e}")
        results.append(False)
    
    # Teste ZSTD (opcional)
    try:
        import zstandard as zstd
        cctx = zstd.ZstdCompressor()
        compressed = cctx.compress(test_data)
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed)
        
        if decompressed == test_data:
            ratio = len(compressed) / len(test_data)
            print(f"ZSTD: OK - {len(compressed)} bytes (ratio: {ratio:.3f})")
            results.append(True)
        else:
            print("ZSTD: FALHA - Descompressao incorreta")
            results.append(False)
    except ImportError:
        print("ZSTD: NAO DISPONIVEL")
    except Exception as e:
        print(f"ZSTD: ERRO - {e}")
        results.append(False)
    
    success_rate = sum(results) / len(results) * 100 if results else 0
    print(f"\nResultado: {sum(results)}/{len(results)} algoritmos funcionando ({success_rate:.1f}%)")
    
    return success_rate >= 50

def test_file_compression():
    """Teste de compressão de arquivos"""
    print("\n=== Teste de Compressão de Arquivos ===")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Criar arquivo de teste
            test_file = temp_path / "test.txt"
            test_content = "Arquivo de teste para compressao " * 100
            
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            original_size = test_file.stat().st_size
            print(f"Arquivo criado: {original_size} bytes")
            
            # Comprimir arquivo
            compressed_file = temp_path / "test.txt.gz"
            
            with open(test_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            compressed_size = compressed_file.stat().st_size
            ratio = compressed_size / original_size
            print(f"Arquivo comprimido: {compressed_size} bytes (ratio: {ratio:.3f})")
            
            # Descomprimir
            decompressed_file = temp_path / "test_recovered.txt"
            
            with gzip.open(compressed_file, 'rb') as f_in:
                with open(decompressed_file, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            # Verificar integridade
            with open(test_file, 'r', encoding='utf-8') as f1:
                with open(decompressed_file, 'r', encoding='utf-8') as f2:
                    if f1.read() == f2.read():
                        print("Descompressao: OK - Dados integros")
                        return True
                    else:
                        print("Descompressao: FALHA - Dados corrompidos")
                        return False
    
    except Exception as e:
        print(f"ERRO: {e}")
        return False

def test_compression_cli():
    """Teste da CLI de compressão"""
    print("\n=== Teste da CLI de Compressão ===")
    
    cli_path = Path("src/core/compression_cli.py")
    
    if cli_path.exists():
        print(f"CLI encontrada: {cli_path}")
        
        try:
            import subprocess
            result = subprocess.run([
                sys.executable, str(cli_path), "algorithms"
            ], capture_output=True, text=True, timeout=15, cwd=os.getcwd())
            
            if result.returncode == 0:
                try:
                    import json
                    data = json.loads(result.stdout)
                    if data.get("success") and "available_algorithms" in data:
                        algorithms = data["available_algorithms"]
                        print(f"CLI: OK - {len(algorithms)} algoritmos disponíveis")
                        return True
                    else:
                        print("CLI: FALHA - Resposta inválida")
                        return False
                except:
                    print("CLI: FALHA - JSON inválido")
                    return False
            else:
                print(f"CLI: ERRO - Código de saída: {result.returncode}")
                if result.stderr:
                    print(f"Erro: {result.stderr[:200]}")
                return False
                
        except subprocess.TimeoutExpired:
            print("CLI: TIMEOUT")
            return False
        except Exception as e:
            print(f"CLI: ERRO - {e}")
            return False
    else:
        print(f"CLI: NAO ENCONTRADA - {cli_path}")
        return False

def test_raycast_files():
    """Teste dos arquivos Raycast"""
    print("\n=== Teste dos Arquivos Raycast ===")
    
    raycast_files = [
        "raycast-extension/src/compression.tsx",
        "raycast-extension/package.json"
    ]
    
    found_files = 0
    for file_path in raycast_files:
        if Path(file_path).exists():
            found_files += 1
            print(f"Encontrado: {file_path}")
        else:
            print(f"Ausente: {file_path}")
    
    success = found_files >= len(raycast_files) * 0.5  # 50% dos arquivos
    print(f"Raycast: {'OK' if success else 'FALHA'} - {found_files}/{len(raycast_files)} arquivos")
    
    return success

def main():
    """Função principal"""
    print("TESTE BASICO DO SISTEMA DE COMPRESSAO")
    print("=" * 50)
    
    tests = [
        ("Compressao Basica", test_basic_compression),
        ("Compressao de Arquivos", test_file_compression), 
        ("CLI de Compressao", test_compression_cli),
        ("Arquivos Raycast", test_raycast_files)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"ERRO no teste {test_name}: {e}")
            results.append((test_name, False))
    
    # Relatório final
    print("\n" + "=" * 50)
    print("RELATORIO FINAL")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\nEstatisticas:")
    print(f"  Total: {total}")
    print(f"  Passou: {passed}")
    print(f"  Falhou: {total - passed}")
    print(f"  Taxa de Sucesso: {success_rate:.1f}%")
    
    print(f"\nDetalhes:")
    for test_name, result in results:
        status = "PASSOU" if result else "FALHOU"
        print(f"  {test_name}: {status}")
    
    if success_rate >= 75:
        print(f"\nResultado: SUCESSO - Sistema funcionando bem!")
        return True
    else:
        print(f"\nResultado: PROBLEMAS - Alguns componentes precisam de atencao.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTeste interrompido.")
        sys.exit(1)
    except Exception as e:
        print(f"\nErro fatal: {e}")
        sys.exit(1)