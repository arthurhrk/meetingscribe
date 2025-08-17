# -*- coding: utf-8 -*-
"""
CLI Interface para Sistema de Compressão Inteligente - MeetingScribe
Interface de linha de comando para gerenciamento de compressão adaptativa
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import time

from .intelligent_compression import (
    IntelligentCompressor,
    CompressionConfig,
    CompressionStrategy,
    CompressionAlgorithm,
    CompressionLevel,
    create_intelligent_compressor,
    get_available_algorithms,
    auto_compression
)

class CompressionCLI:
    """
    Interface CLI para o sistema de compressão inteligente
    """
    
    def __init__(self):
        self.compressor: Optional[IntelligentCompressor] = None
    
    def get_compression_status(self) -> Dict[str, Any]:
        """Obtém status do sistema de compressão"""
        
        try:
            # Verificar algoritmos disponíveis
            available_algorithms = get_available_algorithms()
            
            # Configuração padrão
            default_config = CompressionConfig()
            
            # Verificar dependências opcionais
            dependencies = {}
            try:
                import zstandard
                dependencies['zstd'] = True
            except ImportError:
                dependencies['zstd'] = False
            
            try:
                import lz4
                dependencies['lz4'] = True
            except ImportError:
                dependencies['lz4'] = False
            
            # Inicializar compressor temporário para estatísticas
            with auto_compression(default_config) as compressor:
                stats = compressor.get_algorithm_stats()
            
            return {
                "status": "success",
                "data": {
                    "overview": {
                        "status_text": "Ready",
                        "status_icon": "✅",
                        "available_algorithms": len(available_algorithms),
                        "dependencies_ok": all(dependencies.values())
                    },
                    "algorithms": {
                        "available": [alg.value for alg in available_algorithms],
                        "recommended": {
                            "speed": "lz4" if dependencies['lz4'] else "gzip",
                            "balanced": "zstd" if dependencies['zstd'] else "gzip", 
                            "compression": "lzma"
                        }
                    },
                    "dependencies": dependencies,
                    "config": {
                        "strategy": default_config.strategy.value,
                        "min_file_size": default_config.min_file_size,
                        "max_file_size": default_config.max_file_size,
                        "background_compression": default_config.background_compression,
                        "analyze_before_compress": default_config.analyze_before_compress,
                        "memory_limit_mb": default_config.memory_limit_mb
                    },
                    "algorithm_stats": stats
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get compression status: {str(e)}"
            }
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analisa arquivo e recomenda configuração de compressão"""
        
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {
                    "status": "error",
                    "message": f"File not found: {file_path}"
                }
            
            config = CompressionConfig()
            config.analyze_before_compress = True
            
            with auto_compression(config) as compressor:
                profile = compressor.analyze_file(path)
            
            # Informações do arquivo
            file_info = {
                "path": str(path),
                "size_bytes": profile.size,
                "size_mb": profile.size / (1024 * 1024),
                "extension": profile.extension,
                "file_type": profile.file_type
            }
            
            # Análise de conteúdo
            content_analysis = {
                "entropy": round(profile.entropy, 3),
                "repetition_ratio": round(profile.repetition_ratio, 3),
                "text_ratio": round(profile.text_ratio, 3),
                "binary_ratio": round(profile.binary_ratio, 3)
            }
            
            # Recomendações
            recommendation = {
                "algorithm": profile.recommended_algorithm.value,
                "level": profile.recommended_level,
                "estimated_ratio": round(profile.estimated_ratio, 3),
                "estimated_savings_percent": round((1 - profile.estimated_ratio) * 100, 1),
                "reason": self._get_recommendation_reason(profile)
            }
            
            return {
                "status": "success",
                "data": {
                    "file_info": file_info,
                    "content_analysis": content_analysis,
                    "recommendation": recommendation,
                    "compressibility": self._assess_compressibility(profile)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to analyze file: {str(e)}"
            }
    
    def _get_recommendation_reason(self, profile) -> str:
        """Gera explicação da recomendação"""
        
        if profile.file_type == "audio":
            if profile.extension in ['.wav', '.flac']:
                return "Uncompressed audio file - can benefit from compression"
            else:
                return "Already compressed audio format - compression not recommended"
        
        elif profile.file_type == "text":
            return "Text file with high repetition - excellent compression candidate"
        
        elif profile.entropy < 3.0:
            return "Low entropy content with high repetition - strong compression recommended"
        
        elif profile.entropy > 6.0:
            return "High entropy content - limited compression benefits"
        
        else:
            return "Moderate compression potential - balanced approach recommended"
    
    def _assess_compressibility(self, profile) -> str:
        """Avalia potencial de compressão"""
        
        if profile.estimated_ratio < 0.3:
            return "Excellent"
        elif profile.estimated_ratio < 0.6:
            return "Good"
        elif profile.estimated_ratio < 0.8:
            return "Moderate"
        else:
            return "Poor"
    
    def compress_file(
        self, 
        file_path: str, 
        output_path: Optional[str] = None,
        algorithm: Optional[str] = None,
        level: Optional[int] = None
    ) -> Dict[str, Any]:
        """Comprime arquivo"""
        
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {
                    "status": "error",
                    "message": f"File not found: {file_path}"
                }
            
            # Configurar compressor
            config = CompressionConfig()
            config.analyze_before_compress = algorithm is None
            
            # Parse algoritmo se especificado
            compression_algorithm = None
            if algorithm:
                try:
                    compression_algorithm = CompressionAlgorithm(algorithm)
                except ValueError:
                    return {
                        "status": "error",
                        "message": f"Invalid algorithm: {algorithm}"
                    }
            
            with auto_compression(config) as compressor:
                result = compressor.compress_file(
                    path, 
                    output_path, 
                    compression_algorithm, 
                    level
                )
            
            if result["success"]:
                return {
                    "status": "success",
                    "data": {
                        "original_path": result["original_path"],
                        "compressed_path": result["compressed_path"],
                        "metadata_path": result.get("metadata_path"),
                        "compression_results": {
                            "algorithm": result["metrics"].algorithm.value,
                            "level": result["metrics"].level,
                            "original_size": result["metrics"].original_size,
                            "compressed_size": result["metrics"].compressed_size,
                            "compression_ratio": round(result["metrics"].compression_ratio, 3),
                            "compression_time": round(result["metrics"].compression_time, 3),
                            "speed_mbps": round(result["metrics"].speed_mbps, 2),
                            "efficiency_score": round(result["metrics"].efficiency_score, 3)
                        },
                        "savings": {
                            "bytes": result["savings_bytes"],
                            "percent": round(result["savings_percent"], 1),
                            "size_reduction": f"{result['savings_bytes'] / (1024*1024):.1f} MB"
                        }
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": result["error"]
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to compress file: {str(e)}"
            }
    
    def benchmark_file(self, file_path: str, sample_size: Optional[int] = None) -> Dict[str, Any]:
        """Executa benchmark de algoritmos em arquivo"""
        
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {
                    "status": "error",
                    "message": f"File not found: {file_path}"
                }
            
            file_size = path.stat().st_size
            
            # Determinar tamanho da amostra
            if sample_size is None:
                if file_size > 10 * 1024 * 1024:  # > 10MB
                    sample_size = 1024 * 1024  # 1MB sample
                elif file_size > 1024 * 1024:  # > 1MB
                    sample_size = 256 * 1024  # 256KB sample
                else:
                    sample_size = file_size  # Arquivo inteiro
            
            # Ler amostra
            with open(path, 'rb') as f:
                data = f.read(sample_size)
            
            if not data:
                return {
                    "status": "error",
                    "message": "Could not read file data"
                }
            
            # Executar benchmark
            config = CompressionConfig()
            with auto_compression(config) as compressor:
                results = compressor.benchmark_algorithms(data)
            
            # Processar resultados
            benchmark_results = {}
            best_algorithm = None
            best_score = 0
            
            for algorithm, metrics in results.items():
                benchmark_results[algorithm.value] = {
                    "compression_ratio": round(metrics.compression_ratio, 3),
                    "compression_time": round(metrics.compression_time, 3),
                    "decompression_time": round(metrics.decompression_time, 3),
                    "speed_mbps": round(metrics.speed_mbps, 2),
                    "efficiency_score": round(metrics.efficiency_score, 3),
                    "savings_percent": round((1 - metrics.compression_ratio) * 100, 1)
                }
                
                if metrics.efficiency_score > best_score:
                    best_score = metrics.efficiency_score
                    best_algorithm = algorithm.value
            
            return {
                "status": "success",
                "data": {
                    "file_info": {
                        "path": str(path),
                        "size": file_size,
                        "sample_size": sample_size,
                        "is_sample": sample_size < file_size
                    },
                    "benchmark_results": benchmark_results,
                    "recommendations": {
                        "best_overall": best_algorithm,
                        "best_compression": min(results.keys(), key=lambda k: results[k].compression_ratio).value,
                        "fastest": max(results.keys(), key=lambda k: results[k].speed_mbps).value
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to benchmark file: {str(e)}"
            }
    
    def get_compression_insights(self) -> Dict[str, Any]:
        """Obtém insights sobre performance de compressão"""
        
        try:
            insights = []
            
            # Verificar disponibilidade de algoritmos otimizados
            try:
                import zstandard
                zstd_available = True
            except ImportError:
                zstd_available = False
                insights.append({
                    "type": "optimization",
                    "severity": "medium",
                    "title": "Zstandard Not Available",
                    "description": "Zstandard (zstd) provides excellent compression with good speed",
                    "suggestion": "Install zstandard: pip install zstandard",
                    "icon": "⚡"
                })
            
            try:
                import lz4
                lz4_available = True
            except ImportError:
                lz4_available = False
                insights.append({
                    "type": "optimization",
                    "severity": "medium", 
                    "title": "LZ4 Not Available",
                    "description": "LZ4 provides ultra-fast compression for speed-critical scenarios",
                    "suggestion": "Install lz4: pip install lz4",
                    "icon": "🚀"
                })
            
            # Verificar estatísticas de uso
            config = CompressionConfig()
            with auto_compression(config) as compressor:
                stats = compressor.get_algorithm_stats()
                history = compressor.get_compression_history(10)
            
            if stats:
                # Analisar performance dos algoritmos
                for alg_name, alg_stats in stats.items():
                    if alg_stats['total_uses'] > 0:
                        if alg_stats['success_rate'] < 0.8:
                            insights.append({
                                "type": "performance",
                                "severity": "high",
                                "title": f"Low Success Rate for {alg_name}",
                                "description": f"Algorithm {alg_name} has {alg_stats['success_rate']*100:.1f}% success rate",
                                "suggestion": "Consider using a different algorithm or adjusting compression levels",
                                "icon": "⚠️"
                            })
                        
                        if alg_stats['avg_speed_mbps'] < 1.0:
                            insights.append({
                                "type": "performance",
                                "severity": "low",
                                "title": f"Slow Compression Speed for {alg_name}",
                                "description": f"Average speed: {alg_stats['avg_speed_mbps']:.1f} MB/s",
                                "suggestion": "Consider using faster algorithms like LZ4 for speed-critical scenarios",
                                "icon": "🐌"
                            })
            
            # Verificar memória disponível
            try:
                import psutil
                memory = psutil.virtual_memory()
                
                if memory.available < 512 * 1024 * 1024:  # < 512MB
                    insights.append({
                        "type": "memory",
                        "severity": "high",
                        "title": "Low Available Memory",
                        "description": f"Only {memory.available // (1024*1024)} MB available",
                        "suggestion": "Use lighter compression algorithms or smaller memory limits",
                        "icon": "🧠"
                    })
                elif memory.available > 4 * 1024 * 1024 * 1024:  # > 4GB
                    insights.append({
                        "type": "optimization",
                        "severity": "low",
                        "title": "High Memory Available",
                        "description": f"You have {memory.available // (1024*1024*1024)} GB available",
                        "suggestion": "Can use higher compression levels and larger buffers",
                        "icon": "💪"
                    })
            except ImportError:
                insights.append({
                    "type": "monitoring",
                    "severity": "low",
                    "title": "System Monitoring Unavailable", 
                    "description": "psutil not available for memory monitoring",
                    "suggestion": "Install psutil for better system monitoring",
                    "icon": "📊"
                })
            
            if not insights:
                insights.append({
                    "type": "status",
                    "severity": "info",
                    "title": "Compression System Ready",
                    "description": "Compression system is optimally configured",
                    "suggestion": "You can compress files efficiently with adaptive algorithms",
                    "icon": "✅"
                })
            
            return {
                "status": "success",
                "data": {
                    "insights": insights,
                    "total_insights": len(insights),
                    "high_priority": len([i for i in insights if i["severity"] == "high"]),
                    "medium_priority": len([i for i in insights if i["severity"] == "medium"]),
                    "low_priority": len([i for i in insights if i["severity"] == "low"]),
                    "algorithm_availability": {
                        "zstd": zstd_available,
                        "lz4": lz4_available,
                        "builtin": True
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get compression insights: {str(e)}"
            }
    
    def get_compression_config(self) -> Dict[str, Any]:
        """Obtém configuração atual de compressão"""
        
        try:
            config = CompressionConfig()
            available_algorithms = get_available_algorithms()
            
            return {
                "status": "success",
                "data": {
                    "current_config": {
                        "strategy": config.strategy.value,
                        "fallback_algorithm": config.fallback_algorithm.value,
                        "fallback_level": config.fallback_level.value,
                        "min_file_size": config.min_file_size,
                        "max_file_size": config.max_file_size,
                        "enable_caching": config.enable_caching,
                        "background_compression": config.background_compression,
                        "analyze_before_compress": config.analyze_before_compress,
                        "memory_limit_mb": config.memory_limit_mb
                    },
                    "available_algorithms": [alg.value for alg in available_algorithms],
                    "strategies": [strategy.value for strategy in CompressionStrategy],
                    "levels": [level.value for level in CompressionLevel],
                    "recommendations": {
                        "for_speed": "Use LZ4 or GZIP with level 1-3",
                        "for_size": "Use LZMA or ZSTD with level 7-9", 
                        "for_balance": "Use ZSTD or GZIP with level 4-6"
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get compression config: {str(e)}"
            }

def main():
    """Função principal do CLI"""
    
    parser = argparse.ArgumentParser(description='MeetingScribe Compression CLI')
    parser.add_argument('command', choices=['status', 'analyze', 'compress', 'benchmark', 'insights', 'config'])
    parser.add_argument('--file', help='File path for compression operations')
    parser.add_argument('--output', help='Output path for compressed file')
    parser.add_argument('--algorithm', help='Compression algorithm to use')
    parser.add_argument('--level', type=int, help='Compression level (1-9)')
    parser.add_argument('--sample-size', type=int, help='Sample size for benchmark (bytes)')
    
    args = parser.parse_args()
    
    cli = CompressionCLI()
    
    try:
        if args.command == 'status':
            result = cli.get_compression_status()
        elif args.command == 'analyze':
            if not args.file:
                result = {"status": "error", "message": "File path required for analyze command"}
            else:
                result = cli.analyze_file(args.file)
        elif args.command == 'compress':
            if not args.file:
                result = {"status": "error", "message": "File path required for compress command"}
            else:
                result = cli.compress_file(args.file, args.output, args.algorithm, args.level)
        elif args.command == 'benchmark':
            if not args.file:
                result = {"status": "error", "message": "File path required for benchmark command"}
            else:
                result = cli.benchmark_file(args.file, args.sample_size)
        elif args.command == 'insights':
            result = cli.get_compression_insights()
        elif args.command == 'config':
            result = cli.get_compression_config()
        else:
            result = {"status": "error", "message": f"Unknown command: {args.command}"}
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"CLI execution failed: {str(e)}"
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()