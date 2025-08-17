# -*- coding: utf-8 -*-
"""
CLI Interface para Streaming Processor - MeetingScribe
Interface de linha de comando para gerenciamento de streaming de arquivos grandes
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import time

from .streaming_processor import (
    AudioStreamer,
    StreamConfig,
    StreamingStrategy,
    BufferStrategy,
    create_audio_streamer,
    streaming_audio
)

class StreamingCLI:
    """
    Interface CLI para o sistema de streaming
    """
    
    def __init__(self):
        self.streamer: Optional[AudioStreamer] = None
    
    def get_streaming_status(self) -> Dict[str, Any]:
        """Obtém status do sistema de streaming"""
        
        try:
            # Verificar se dependencies estão disponíveis
            try:
                import soundfile as sf
                import numpy as np
                dependencies_ok = True
                missing_deps = []
            except ImportError as e:
                dependencies_ok = False
                missing_deps = ["soundfile", "numpy"]
            
            # Verificar estratégias disponíveis
            available_strategies = [strategy.value for strategy in StreamingStrategy]
            
            # Configuração padrão
            default_config = StreamConfig()
            
            return {
                "status": "success",
                "data": {
                    "overview": {
                        "status_text": "Ready" if dependencies_ok else "Dependencies Missing",
                        "status_icon": "✅" if dependencies_ok else "❌",
                        "dependencies_ok": dependencies_ok,
                        "missing_deps": missing_deps
                    },
                    "capabilities": {
                        "strategies": available_strategies,
                        "buffer_strategies": [bs.value for bs in BufferStrategy],
                        "max_chunk_size": default_config.max_chunk_size,
                        "min_chunk_size": default_config.min_chunk_size
                    },
                    "current_config": {
                        "chunk_size_seconds": default_config.chunk_size_seconds,
                        "overlap_seconds": default_config.overlap_seconds,
                        "buffer_size_mb": default_config.buffer_size_mb,
                        "max_memory_mb": default_config.max_memory_mb,
                        "strategy": default_config.strategy.value,
                        "buffer_strategy": default_config.buffer_strategy.value,
                        "prefetch_chunks": default_config.prefetch_chunks,
                        "cache_enabled": default_config.enable_cache,
                        "quality_mode": default_config.quality_mode
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get streaming status: {str(e)}"
            }
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analisa arquivo e recomenda configuração de streaming"""
        
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {
                    "status": "error",
                    "message": f"File not found: {file_path}"
                }
            
            # Obter informações básicas do arquivo
            file_size_mb = path.stat().st_size / (1024 * 1024)
            
            # Analisar arquivo de áudio se possível
            audio_info = {}
            try:
                import soundfile as sf
                with sf.SoundFile(str(path)) as f:
                    audio_info = {
                        "duration": len(f) / f.samplerate,
                        "sample_rate": f.samplerate,
                        "channels": f.channels,
                        "frames": len(f)
                    }
            except:
                audio_info = {"error": "Could not analyze audio file"}
            
            # Recomendar estratégia
            if file_size_mb > 1000:
                recommended_strategy = StreamingStrategy.MEMORY_AWARE
                reason = "Very large file (>1GB) - memory-aware streaming recommended"
            elif file_size_mb > 200:
                recommended_strategy = StreamingStrategy.ADAPTIVE_CHUNK
                reason = "Large file (>200MB) - adaptive chunking recommended"
            elif file_size_mb > 50:
                recommended_strategy = StreamingStrategy.INTELLIGENT
                reason = "Medium file (>50MB) - intelligent streaming recommended"
            else:
                recommended_strategy = StreamingStrategy.FIXED_CHUNK
                reason = "Small file - fixed chunking sufficient"
            
            # Recomendar configuração
            recommended_config = StreamConfig()
            
            if file_size_mb > 500:
                recommended_config.chunk_size_seconds = 60.0
                recommended_config.buffer_size_mb = 1024
            elif file_size_mb > 100:
                recommended_config.chunk_size_seconds = 45.0
                recommended_config.buffer_size_mb = 512
            else:
                recommended_config.chunk_size_seconds = 30.0
                recommended_config.buffer_size_mb = 256
            
            recommended_config.strategy = recommended_strategy
            
            return {
                "status": "success",
                "data": {
                    "file_info": {
                        "path": str(path),
                        "size_mb": round(file_size_mb, 2),
                        "exists": True
                    },
                    "audio_info": audio_info,
                    "recommendation": {
                        "strategy": recommended_strategy.value,
                        "reason": reason,
                        "config": {
                            "chunk_size_seconds": recommended_config.chunk_size_seconds,
                            "overlap_seconds": recommended_config.overlap_seconds,
                            "buffer_size_mb": recommended_config.buffer_size_mb,
                            "max_memory_mb": recommended_config.max_memory_mb,
                            "strategy": recommended_config.strategy.value,
                            "buffer_strategy": recommended_config.buffer_strategy.value,
                            "prefetch_chunks": recommended_config.prefetch_chunks,
                            "quality_mode": recommended_config.quality_mode
                        }
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to analyze file: {str(e)}"
            }
    
    def stream_test(self, file_path: str, config_json: Optional[str] = None) -> Dict[str, Any]:
        """Executa teste de streaming em arquivo"""
        
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {
                    "status": "error",
                    "message": f"File not found: {file_path}"
                }
            
            # Parse config se fornecida
            config = StreamConfig()
            if config_json:
                try:
                    config_data = json.loads(config_json)
                    config.chunk_size_seconds = config_data.get("chunk_size_seconds", config.chunk_size_seconds)
                    config.overlap_seconds = config_data.get("overlap_seconds", config.overlap_seconds)
                    config.buffer_size_mb = config_data.get("buffer_size_mb", config.buffer_size_mb)
                    config.max_memory_mb = config_data.get("max_memory_mb", config.max_memory_mb)
                    
                    strategy_str = config_data.get("strategy", config.strategy.value)
                    config.strategy = StreamingStrategy(strategy_str)
                    
                    buffer_strategy_str = config_data.get("buffer_strategy", config.buffer_strategy.value)
                    config.buffer_strategy = BufferStrategy(buffer_strategy_str)
                    
                except (json.JSONDecodeError, ValueError) as e:
                    return {
                        "status": "error",
                        "message": f"Invalid config JSON: {str(e)}"
                    }
            
            # Criar streamer
            streamer = create_audio_streamer(config)
            
            # Executar teste de streaming
            start_time = time.time()
            chunk_count = 0
            total_duration = 0.0
            
            try:
                for chunk in streamer.stream_file(path):
                    chunk_count += 1
                    total_duration = chunk.end_time
                    
                    # Limitar teste para não demorar muito
                    if chunk_count >= 5:  # Apenas primeiros 5 chunks
                        break
                
                end_time = time.time()
                test_duration = end_time - start_time
                
                # Obter estatísticas
                stats = streamer.get_stats()
                
                return {
                    "status": "success",
                    "data": {
                        "test_results": {
                            "chunks_processed": chunk_count,
                            "test_duration_seconds": round(test_duration, 3),
                            "audio_duration_processed": round(total_duration, 3),
                            "processing_speed": round(total_duration / test_duration, 2) if test_duration > 0 else 0
                        },
                        "streaming_stats": stats,
                        "config_used": {
                            "strategy": config.strategy.value,
                            "chunk_size_seconds": config.chunk_size_seconds,
                            "buffer_strategy": config.buffer_strategy.value,
                            "buffer_size_mb": config.buffer_size_mb
                        }
                    }
                }
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Streaming test failed: {str(e)}"
                }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to run streaming test: {str(e)}"
            }
    
    def get_streaming_insights(self) -> Dict[str, Any]:
        """Obtém insights sobre performance de streaming"""
        
        try:
            insights = []
            
            # Verificar dependências
            missing_deps = []
            try:
                import soundfile as sf
            except ImportError:
                missing_deps.append("soundfile")
            
            try:
                import librosa
            except ImportError:
                missing_deps.append("librosa")
            
            if missing_deps:
                insights.append({
                    "type": "dependency",
                    "severity": "high",
                    "title": "Missing Dependencies",
                    "description": f"Missing audio processing libraries: {', '.join(missing_deps)}",
                    "suggestion": "Install missing dependencies: pip install soundfile librosa",
                    "icon": "📦"
                })
            
            # Verificar memória disponível
            try:
                import psutil
                memory = psutil.virtual_memory()
                
                if memory.available < 1024 * 1024 * 1024:  # < 1GB
                    insights.append({
                        "type": "memory",
                        "severity": "medium",
                        "title": "Low Available Memory",
                        "description": f"Only {memory.available // (1024*1024)} MB available",
                        "suggestion": "Close other applications or use smaller chunk sizes",
                        "icon": "🧠"
                    })
                elif memory.available > 8 * 1024 * 1024 * 1024:  # > 8GB
                    insights.append({
                        "type": "optimization",
                        "severity": "low",
                        "title": "High Memory Available",
                        "description": f"You have {memory.available // (1024*1024*1024)} GB available",
                        "suggestion": "Can use larger chunk sizes for better performance",
                        "icon": "🚀"
                    })
            except ImportError:
                insights.append({
                    "type": "monitoring",
                    "severity": "low",
                    "title": "System Monitoring Unavailable",
                    "description": "psutil not available for system monitoring",
                    "suggestion": "Install psutil for better system monitoring",
                    "icon": "📊"
                })
            
            # Verificar cache
            try:
                from .file_cache import get_file_cache
                cache = get_file_cache()
                cache_stats = cache.get_stats()
                
                if cache_stats['hit_rate_percent'] < 50:
                    insights.append({
                        "type": "cache",
                        "severity": "medium",
                        "title": "Low Cache Hit Rate",
                        "description": f"Cache hit rate is only {cache_stats['hit_rate_percent']:.1f}%",
                        "suggestion": "Consider increasing cache size or adjusting eviction strategy",
                        "icon": "💾"
                    })
            except:
                insights.append({
                    "type": "cache",
                    "severity": "low",
                    "title": "Cache Integration Available",
                    "description": "File cache can be integrated for better performance",
                    "suggestion": "Enable cache integration in streaming config",
                    "icon": "💽"
                })
            
            if not insights:
                insights.append({
                    "type": "status",
                    "severity": "info",
                    "title": "System Ready",
                    "description": "Streaming system is ready for optimal performance",
                    "suggestion": "You can start streaming large audio files efficiently",
                    "icon": "✅"
                })
            
            return {
                "status": "success",
                "data": {
                    "insights": insights,
                    "total_insights": len(insights),
                    "high_priority": len([i for i in insights if i["severity"] == "high"]),
                    "medium_priority": len([i for i in insights if i["severity"] == "medium"]),
                    "low_priority": len([i for i in insights if i["severity"] == "low"])
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get streaming insights: {str(e)}"
            }
    
    def benchmark_strategies(self, file_path: str) -> Dict[str, Any]:
        """Executa benchmark das diferentes estratégias de streaming"""
        
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {
                    "status": "error",
                    "message": f"File not found: {file_path}"
                }
            
            strategies_to_test = [
                StreamingStrategy.FIXED_CHUNK,
                StreamingStrategy.ADAPTIVE_CHUNK,
                StreamingStrategy.SLIDING_WINDOW,
                StreamingStrategy.MEMORY_AWARE,
                StreamingStrategy.INTELLIGENT
            ]
            
            results = {}
            
            for strategy in strategies_to_test:
                try:
                    config = StreamConfig()
                    config.strategy = strategy
                    config.chunk_size_seconds = 15.0  # Chunks menores para benchmark
                    
                    streamer = create_audio_streamer(config)
                    
                    start_time = time.time()
                    chunk_count = 0
                    
                    # Testar apenas primeiros chunks
                    for chunk in streamer.stream_file(path):
                        chunk_count += 1
                        if chunk_count >= 3:  # Limite para benchmark rápido
                            break
                    
                    end_time = time.time()
                    test_duration = end_time - start_time
                    
                    stats = streamer.get_stats()
                    
                    results[strategy.value] = {
                        "duration_seconds": round(test_duration, 3),
                        "chunks_processed": chunk_count,
                        "stats": stats
                    }
                    
                except Exception as e:
                    results[strategy.value] = {
                        "error": str(e)
                    }
            
            # Encontrar melhor estratégia
            best_strategy = None
            best_time = float('inf')
            
            for strategy, result in results.items():
                if "duration_seconds" in result and result["duration_seconds"] < best_time:
                    best_time = result["duration_seconds"]
                    best_strategy = strategy
            
            return {
                "status": "success",
                "data": {
                    "benchmark_results": results,
                    "best_strategy": best_strategy,
                    "best_time": best_time,
                    "recommendations": {
                        "fastest": best_strategy,
                        "most_adaptive": StreamingStrategy.INTELLIGENT.value,
                        "memory_efficient": StreamingStrategy.MEMORY_AWARE.value
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to run benchmark: {str(e)}"
            }

def main():
    """Função principal do CLI"""
    
    parser = argparse.ArgumentParser(description='MeetingScribe Streaming CLI')
    parser.add_argument('command', choices=['status', 'analyze', 'test', 'insights', 'benchmark'])
    parser.add_argument('--file', help='Audio file path for analysis/testing')
    parser.add_argument('--config', help='JSON configuration for streaming')
    
    args = parser.parse_args()
    
    cli = StreamingCLI()
    
    try:
        if args.command == 'status':
            result = cli.get_streaming_status()
        elif args.command == 'analyze':
            if not args.file:
                result = {"status": "error", "message": "File path required for analyze command"}
            else:
                result = cli.analyze_file(args.file)
        elif args.command == 'test':
            if not args.file:
                result = {"status": "error", "message": "File path required for test command"}
            else:
                result = cli.stream_test(args.file, args.config)
        elif args.command == 'insights':
            result = cli.get_streaming_insights()
        elif args.command == 'benchmark':
            if not args.file:
                result = {"status": "error", "message": "File path required for benchmark command"}
            else:
                result = cli.benchmark_strategies(args.file)
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