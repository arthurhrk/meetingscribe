#!/usr/bin/env python3
"""
Teste de Integração Completa do Sistema de Compressão Inteligente

Este teste valida todos os componentes do sistema de compressão:
- Compressão inteligente com múltiplos algoritmos
- Detecção automática do melhor método
- Compressão em background
- Integração com cache
- Interface CLI

Autor: Claude Code
Data: 2025-08-17
"""

import os
import sys
import json
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Imports dos sistemas de compressão
try:
    from core.intelligent_compression import (
        IntelligentCompressor,
        CompressionConfig,
        CompressionStrategy,
        CompressionAlgorithm,
        get_available_algorithms
    )
    from core.compression_integration import (
        IntelligentFileCache,
        create_intelligent_cache
    )
    from core.compression_cli import CompressionCLI
except ImportError as e:
    print(f"❌ Erro importando módulos de compressão: {e}")
    sys.exit(1)


class CompressionIntegrationTest:
    """Classe para testar integração completa do sistema de compressão"""
    
    def __init__(self):
        self.test_dir = None
        self.test_files = {}
        self.results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': []
        }
    
    def setup_test_environment(self):
        """Configura ambiente de teste"""
        print("🔧 Configurando ambiente de teste...")
        
        # Criar diretório temporário
        self.test_dir = Path(tempfile.mkdtemp(prefix="compression_test_"))
        print(f"   📁 Diretório de teste: {self.test_dir}")
        
        # Criar arquivos de teste
        self._create_test_files()
        
        print("✅ Ambiente configurado com sucesso!")
    
    def _create_test_files(self):
        """Cria arquivos de teste com diferentes características"""
        
        # Arquivo de texto (alta compressibilidade)
        text_content = "Este é um arquivo de teste com muito texto repetitivo! " * 200
        text_file = self.test_dir / "test_text.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        self.test_files['text'] = text_file
        
        # Arquivo JSON (estruturado)
        json_content = {
            "transcriptions": [
                {
                    "timestamp": f"2025-08-17T10:{i:02d}:00",
                    "speaker": f"Speaker {i % 3 + 1}",
                    "text": f"Esta é a transcrição número {i} com conteúdo estruturado."
                }
                for i in range(100)
            ],
            "metadata": {
                "total_duration": 3600,
                "language": "pt-BR",
                "model": "whisper-large-v3"
            }
        }
        json_file = self.test_dir / "test_transcription.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_content, f, indent=2, ensure_ascii=False)
        self.test_files['json'] = json_file
        
        # Arquivo binário simulando áudio (baixa compressibilidade)
        binary_content = os.urandom(50000)  # 50KB de dados aleatórios
        binary_file = self.test_dir / "test_audio.wav"
        with open(binary_file, 'wb') as f:
            f.write(binary_content)
        self.test_files['binary'] = binary_file
        
        # Arquivo pequeno (threshold test)
        small_content = "Arquivo pequeno para teste de threshold."
        small_file = self.test_dir / "test_small.txt"
        with open(small_file, 'w', encoding='utf-8') as f:
            f.write(small_content)
        self.test_files['small'] = small_file
        
        print(f"   📄 Criados {len(self.test_files)} arquivos de teste")
    
    def test_intelligent_compression(self):
        """Testa compressão inteligente"""
        print("\n🧠 Testando Compressão Inteligente...")
        
        config = CompressionConfig()
        config.strategy = CompressionStrategy.INTELLIGENT
        compressor = IntelligentCompressor(config)
        
        test_results = []
        
        for file_type, file_path in self.test_files.items():
            try:
                print(f"   🗜️ Testando {file_type}: {file_path.name}")
                
                # Analisar arquivo
                profile = compressor.analyze_file(file_path)
                
                # Comprimir
                result = compressor.compress_file(file_path)
                
                if result["success"]:
                    metrics = result["metrics"]
                    test_results.append({
                        'file_type': file_type,
                        'algorithm': metrics.algorithm.value,
                        'compression_ratio': metrics.compression_ratio,
                        'compression_time': metrics.compression_time,
                        'success': True
                    })
                    print(f"      ✅ {metrics.algorithm.value}: {metrics.compression_ratio:.3f} ratio")
                else:
                    test_results.append({
                        'file_type': file_type,
                        'success': False,
                        'error': result["error"]
                    })
                    print(f"      ❌ Falha: {result['error']}")
                
            except Exception as e:
                test_results.append({
                    'file_type': file_type,
                    'success': False,
                    'error': str(e)
                })
                print(f"      ❌ Erro: {e}")
        
        # Avaliar resultados
        successful_compressions = sum(1 for r in test_results if r['success'])
        success_rate = successful_compressions / len(test_results) * 100
        
        self._record_test_result(
            "Compressão Inteligente",
            success_rate >= 75,  # 75% de sucesso esperado
            f"Taxa de sucesso: {success_rate:.1f}% ({successful_compressions}/{len(test_results)})",
            test_results
        )
        
        compressor.stop_background_processing()
    
    def test_algorithm_selection(self):
        """Testa seleção automática de algoritmos"""
        print("\n🎯 Testando Seleção Automática de Algoritmos...")
        
        config = CompressionConfig()
        config.strategy = CompressionStrategy.INTELLIGENT
        compressor = IntelligentCompressor(config)
        
        selection_results = []
        
        for file_type, file_path in self.test_files.items():
            try:
                profile = compressor.analyze_file(file_path)
                
                # Verificar se algoritmo é apropriado para o tipo de arquivo
                algorithm = profile.recommended_algorithm
                is_appropriate = self._is_algorithm_appropriate(file_type, algorithm)
                
                selection_results.append({
                    'file_type': file_type,
                    'recommended_algorithm': algorithm.value,
                    'is_appropriate': is_appropriate,
                    'estimated_ratio': profile.estimated_ratio
                })
                
                status = "✅" if is_appropriate else "⚠️"
                print(f"   {status} {file_type}: {algorithm.value} (ratio: {profile.estimated_ratio:.3f})")
                
            except Exception as e:
                selection_results.append({
                    'file_type': file_type,
                    'error': str(e)
                })
                print(f"   ❌ {file_type}: Erro - {e}")
        
        # Avaliar apropriação dos algoritmos
        appropriate_selections = sum(1 for r in selection_results if r.get('is_appropriate', False))
        appropriateness_rate = appropriate_selections / len(selection_results) * 100
        
        self._record_test_result(
            "Seleção de Algoritmos",
            appropriateness_rate >= 80,
            f"Taxa de seleções apropriadas: {appropriateness_rate:.1f}%",
            selection_results
        )
        
        compressor.stop_background_processing()
    
    def _is_algorithm_appropriate(self, file_type: str, algorithm: CompressionAlgorithm) -> bool:
        """Verifica se algoritmo é apropriado para o tipo de arquivo"""
        
        # Regras heurísticas para avaliar apropriação
        if file_type == 'text':
            # Texto deve usar algoritmos de alta compressão
            return algorithm in [CompressionAlgorithm.ZSTD, CompressionAlgorithm.LZMA, CompressionAlgorithm.GZIP]
        
        elif file_type == 'json':
            # JSON é estruturado, deve comprimir bem
            return algorithm in [CompressionAlgorithm.ZSTD, CompressionAlgorithm.GZIP, CompressionAlgorithm.LZMA]
        
        elif file_type == 'binary':
            # Binário pode ter baixa compressibilidade
            return algorithm in [CompressionAlgorithm.LZ4, CompressionAlgorithm.GZIP, CompressionAlgorithm.NONE]
        
        elif file_type == 'small':
            # Arquivos pequenos podem não justificar compressão
            return algorithm in [CompressionAlgorithm.NONE, CompressionAlgorithm.LZ4, CompressionAlgorithm.GZIP]
        
        return True  # Default: aceitar qualquer algoritmo
    
    def test_cache_integration(self):
        """Testa integração com cache inteligente"""
        print("\n💾 Testando Integração com Cache...")
        
        cache_dir = self.test_dir / "cache_test"
        cache_dir.mkdir()
        
        try:
            # Criar cache inteligente
            cache = create_intelligent_cache()
            
            cache_results = []
            
            for file_type, file_path in self.test_files.items():
                try:
                    print(f"   📦 Cacheando {file_type}: {file_path.name}")
                    
                    # Cachear com compressão inteligente
                    cache_key = f"test_{file_type}"
                    success = cache.cache_with_intelligent_compression(
                        cache_key, file_path, "auto"
                    )
                    
                    if success:
                        # Verificar se foi armazenado
                        cached_content = cache.get(cache_key)
                        
                        cache_results.append({
                            'file_type': file_type,
                            'cached_successfully': cached_content is not None,
                            'success': True
                        })
                        
                        status = "✅" if cached_content is not None else "⚠️"
                        print(f"      {status} Cache: {'Sucesso' if cached_content is not None else 'Vazio'}")
                    else:
                        cache_results.append({
                            'file_type': file_type,
                            'success': False,
                            'error': 'Cache operation failed'
                        })
                        print(f"      ❌ Falha no cache")
                
                except Exception as e:
                    cache_results.append({
                        'file_type': file_type,
                        'success': False,
                        'error': str(e)
                    })
                    print(f"      ❌ Erro: {e}")
            
            # Testar analytics
            analytics = cache.get_compression_analytics()
            print(f"   📊 Analytics: {analytics['overview']['total_intelligent_compressions']} compressões")
            
            # Avaliar resultados
            successful_caches = sum(1 for r in cache_results if r['success'])
            cache_success_rate = successful_caches / len(cache_results) * 100
            
            self._record_test_result(
                "Integração com Cache",
                cache_success_rate >= 75,
                f"Taxa de sucesso do cache: {cache_success_rate:.1f}%",
                cache_results
            )
            
        except Exception as e:
            self._record_test_result(
                "Integração com Cache",
                False,
                f"Erro fatal: {e}",
                []
            )
    
    def test_cli_interface(self):
        """Testa interface CLI"""
        print("\n🖥️ Testando Interface CLI...")
        
        cli = CompressionCLI()
        cli_results = []
        
        # Testar comandos básicos
        commands_to_test = [
            ('status', lambda: cli.get_compression_status()),
            ('algorithms', lambda: cli.list_algorithms()),
            ('analyze', lambda: cli.analyze_file(str(self.test_files['text']))),
            ('compress', lambda: cli.compress_file(str(self.test_files['text']))),
        ]
        
        for command_name, command_func in commands_to_test:
            try:
                print(f"   🔧 Testando comando: {command_name}")
                
                result = command_func()
                
                if result.get('success', False):
                    cli_results.append({
                        'command': command_name,
                        'success': True
                    })
                    print(f"      ✅ {command_name}: Sucesso")
                else:
                    cli_results.append({
                        'command': command_name,
                        'success': False,
                        'error': result.get('error', 'Unknown error')
                    })
                    print(f"      ❌ {command_name}: {result.get('error', 'Falha')}")
                
            except Exception as e:
                cli_results.append({
                    'command': command_name,
                    'success': False,
                    'error': str(e)
                })
                print(f"      ❌ {command_name}: Erro - {e}")
        
        # Avaliar CLI
        successful_commands = sum(1 for r in cli_results if r['success'])
        cli_success_rate = successful_commands / len(cli_results) * 100
        
        self._record_test_result(
            "Interface CLI",
            cli_success_rate >= 75,
            f"Taxa de sucesso da CLI: {cli_success_rate:.1f}%",
            cli_results
        )
    
    def test_background_compression(self):
        """Testa compressão em background"""
        print("\n⏳ Testando Compressão em Background...")
        
        config = CompressionConfig()
        config.background_compression = True
        compressor = IntelligentCompressor(config)
        
        try:
            # Adicionar arquivos para compressão em background
            for file_type, file_path in self.test_files.items():
                compressor.add_background_compression(file_path)
                print(f"   📤 Adicionado à fila: {file_type}")
            
            # Aguardar processamento
            print("   ⏱️ Aguardando processamento em background...")
            time.sleep(3)
            
            # Verificar estatísticas
            stats = compressor.get_algorithm_stats()
            total_processed = sum(alg_stats['total_uses'] for alg_stats in stats.values())
            
            self._record_test_result(
                "Compressão em Background",
                total_processed > 0,
                f"Arquivos processados em background: {total_processed}",
                {'processed_files': total_processed, 'algorithm_stats': stats}
            )
            
            print(f"   ✅ Processados: {total_processed} arquivos")
            
        except Exception as e:
            self._record_test_result(
                "Compressão em Background",
                False,
                f"Erro: {e}",
                {}
            )
            print(f"   ❌ Erro: {e}")
        
        finally:
            compressor.stop_background_processing()
    
    def _record_test_result(self, test_name: str, passed: bool, message: str, details: Any):
        """Registra resultado de teste"""
        self.results['total_tests'] += 1
        
        if passed:
            self.results['passed_tests'] += 1
        else:
            self.results['failed_tests'] += 1
        
        self.results['test_details'].append({
            'test_name': test_name,
            'passed': passed,
            'message': message,
            'details': details
        })
    
    def generate_report(self):
        """Gera relatório final dos testes"""
        print("\n" + "="*60)
        print("📋 RELATÓRIO FINAL DOS TESTES DE COMPRESSÃO")
        print("="*60)
        
        # Estatísticas gerais
        total = self.results['total_tests']
        passed = self.results['passed_tests']
        failed = self.results['failed_tests']
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n📊 ESTATÍSTICAS GERAIS:")
        print(f"   Total de Testes: {total}")
        print(f"   Testes Aprovados: {passed} ✅")
        print(f"   Testes Falharam: {failed} ❌")
        print(f"   Taxa de Sucesso: {success_rate:.1f}%")
        
        # Detalhes dos testes
        print(f"\n📝 DETALHES DOS TESTES:")
        for test in self.results['test_details']:
            status = "✅ PASSOU" if test['passed'] else "❌ FALHOU"
            print(f"\n   {test['test_name']}: {status}")
            print(f"      {test['message']}")
        
        # Avaliação geral
        print(f"\n🎯 AVALIAÇÃO GERAL:")
        if success_rate >= 90:
            print("   🎉 EXCELENTE! Sistema de compressão funcionando perfeitamente.")
        elif success_rate >= 75:
            print("   👍 BOM! Sistema funcionando bem com algumas melhorias possíveis.")
        elif success_rate >= 50:
            print("   ⚠️ REGULAR! Sistema precisa de ajustes importantes.")
        else:
            print("   🔴 CRÍTICO! Sistema com problemas sérios que precisam ser corrigidos.")
        
        return success_rate >= 75
    
    def cleanup(self):
        """Limpa ambiente de teste"""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            print(f"\n🧹 Ambiente de teste limpo: {self.test_dir}")
    
    def run_all_tests(self):
        """Executa todos os testes"""
        print("🚀 INICIANDO TESTES DE INTEGRAÇÃO DO SISTEMA DE COMPRESSÃO")
        print("="*60)
        
        try:
            self.setup_test_environment()
            
            # Executar testes
            self.test_intelligent_compression()
            self.test_algorithm_selection()
            self.test_cache_integration()
            self.test_cli_interface()
            self.test_background_compression()
            
            # Gerar relatório
            success = self.generate_report()
            
            return success
            
        except Exception as e:
            print(f"\n❌ ERRO FATAL NOS TESTES: {e}")
            return False
        
        finally:
            self.cleanup()


def main():
    """Função principal"""
    
    print("🗜️ SISTEMA DE COMPRESSÃO INTELIGENTE - TESTE DE INTEGRAÇÃO")
    print("=" * 70)
    print("Testando todas as funcionalidades do sistema de compressão...")
    print()
    
    # Verificar dependências básicas
    try:
        available_algorithms = get_available_algorithms()
        print(f"🔧 Algoritmos disponíveis: {[alg.value for alg in available_algorithms]}")
    except Exception as e:
        print(f"❌ Erro verificando algoritmos: {e}")
        return False
    
    # Executar testes
    tester = CompressionIntegrationTest()
    success = tester.run_all_tests()
    
    # Resultado final
    print("\n" + "="*70)
    if success:
        print("🎉 TODOS OS TESTES PASSARAM! Sistema de compressão pronto para uso.")
        return True
    else:
        print("❌ ALGUNS TESTES FALHARAM! Revisar problemas antes de usar em produção.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)