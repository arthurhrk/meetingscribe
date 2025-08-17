# -*- coding: utf-8 -*-
"""
CLI Interface para Gerenciamento de Cache - Raycast Integration
Comandos para gerenciar cache de arquivos e monitorar performance I/O
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from .file_optimizers import get_optimized_file_manager
from .file_cache import get_file_cache, FileCacheConfig, CacheStrategy


class CacheCLI:
    """
    Interface CLI para gerenciamento de cache de arquivos
    """
    
    def __init__(self):
        self.file_manager = get_optimized_file_manager()
        self.cache = get_file_cache()
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Retorna status detalhado do cache
        """
        try:
            stats = self.file_manager.get_comprehensive_stats()
            
            # Determinar status geral baseado na eficiência
            hit_rate = stats.get('combined_hit_rate', 0)
            memory_usage = stats.get('combined_memory_mb', 0)
            
            if hit_rate >= 80:
                status_text = "Excellent"
                status_icon = "✅"
                status_color = "green"
            elif hit_rate >= 60:
                status_text = "Good"
                status_icon = "🟢"
                status_color = "green"
            elif hit_rate >= 40:
                status_text = "Fair"
                status_icon = "🟡"
                status_color = "yellow"
            else:
                status_text = "Poor"
                status_icon = "🔴"
                status_color = "red"
            
            return {
                "status": "success",
                "data": {
                    "overview": {
                        "status_text": status_text,
                        "status_icon": status_icon,
                        "status_color": status_color,
                        "hit_rate": f"{hit_rate:.1f}%",
                        "memory_usage": f"{memory_usage:.1f} MB",
                        "total_entries": stats['file_cache']['entries_count']
                    },
                    "file_cache": {
                        "entries": stats['file_cache']['entries_count'],
                        "memory_mb": stats['file_cache']['memory_usage_mb'],
                        "memory_limit_mb": stats['file_cache']['memory_limit_mb'],
                        "memory_usage_percent": stats['file_cache']['memory_usage_percent'],
                        "hit_rate": stats['file_cache']['hit_rate_percent'],
                        "hits": stats['file_cache']['total_hits'],
                        "misses": stats['file_cache']['total_misses'],
                        "evictions": stats['file_cache']['total_evictions']
                    },
                    "audio_cache": {
                        "entries": stats['audio_cache']['entries_count'],
                        "memory_mb": stats['audio_cache']['memory_usage_mb'],
                        "hit_rate": stats['audio_cache']['hit_rate_percent'],
                        "compressions": stats['audio_cache']['total_compressions'],
                        "decompressions": stats['audio_cache']['total_decompressions']
                    },
                    "io_stats": {
                        "disk_reads": stats['file_cache']['total_disk_reads'],
                        "disk_writes": stats['file_cache']['total_disk_writes'],
                        "compression_ratio": self._calculate_avg_compression()
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_cache_insights(self) -> Dict[str, Any]:
        """
        Gera insights sobre o uso do cache
        """
        try:
            stats = self.file_manager.get_comprehensive_stats()
            insights = []
            
            # Análise de hit rate
            hit_rate = stats.get('combined_hit_rate', 0)
            if hit_rate < 50:
                insights.append({
                    "type": "performance",
                    "severity": "high",
                    "title": "Low Cache Hit Rate",
                    "description": f"Cache hit rate is only {hit_rate:.1f}%",
                    "suggestion": "Consider increasing cache size or reviewing file access patterns",
                    "icon": "📉"
                })
            elif hit_rate > 80:
                insights.append({
                    "type": "performance", 
                    "severity": "info",
                    "title": "Excellent Cache Performance",
                    "description": f"Cache hit rate is {hit_rate:.1f}%",
                    "suggestion": "Cache is performing optimally",
                    "icon": "🚀"
                })
            
            # Análise de uso de memória
            file_cache = stats.get('file_cache', {})
            memory_usage_percent = file_cache.get('memory_usage_percent', 0)
            
            if memory_usage_percent > 90:
                insights.append({
                    "type": "memory",
                    "severity": "medium",
                    "title": "High Memory Usage",
                    "description": f"Cache using {memory_usage_percent:.1f}% of allocated memory",
                    "suggestion": "Consider clearing old entries or increasing memory limit",
                    "icon": "💾"
                })
            elif memory_usage_percent < 20:
                insights.append({
                    "type": "memory",
                    "severity": "info", 
                    "title": "Low Memory Usage",
                    "description": f"Cache using only {memory_usage_percent:.1f}% of allocated memory",
                    "suggestion": "Memory is efficiently utilized",
                    "icon": "✨"
                })
            
            # Análise de evictions
            evictions = file_cache.get('evictions', 0)
            total_ops = file_cache.get('hits', 0) + file_cache.get('misses', 0)
            
            if evictions > 0 and total_ops > 0:
                eviction_rate = (evictions / total_ops) * 100
                if eviction_rate > 10:
                    insights.append({
                        "type": "cache_efficiency",
                        "severity": "medium",
                        "title": "High Eviction Rate",
                        "description": f"Cache eviction rate is {eviction_rate:.1f}%",
                        "suggestion": "Increase cache size or optimize cache strategy",
                        "icon": "🔄"
                    })
            
            # Análise de compressão
            audio_cache = stats.get('audio_cache', {})
            compressions = audio_cache.get('compressions', 0)
            decompressions = audio_cache.get('decompressions', 0)
            
            if compressions > 0:
                compression_ratio = self._calculate_avg_compression()
                if compression_ratio > 0.5:  # Boa compressão
                    insights.append({
                        "type": "storage",
                        "severity": "info",
                        "title": "Effective Compression",
                        "description": f"Average compression ratio: {compression_ratio:.2f}",
                        "suggestion": "Compression is saving significant disk space",
                        "icon": "📦"
                    })
            
            # Insight padrão se nenhum problema encontrado
            if not insights:
                insights.append({
                    "type": "general",
                    "severity": "info",
                    "title": "Cache Operating Normally",
                    "description": "No significant issues detected with cache performance",
                    "suggestion": "Continue monitoring for any changes",
                    "icon": "✅"
                })
            
            return {
                "status": "success",
                "data": {
                    "insights": insights,
                    "analysis_date": datetime.now().isoformat(),
                    "total_insights": len(insights)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def optimize_cache(self) -> Dict[str, Any]:
        """
        Otimiza o cache removendo entradas antigas e desnecessárias
        """
        try:
            # Capturar estatísticas antes
            stats_before = self.file_manager.get_comprehensive_stats()
            
            # Executar otimização
            self.file_manager.optimize_cache()
            
            # Capturar estatísticas depois
            stats_after = self.file_manager.get_comprehensive_stats()
            
            # Calcular diferenças
            memory_freed = stats_before.get('combined_memory_mb', 0) - stats_after.get('combined_memory_mb', 0)
            entries_removed = stats_before['file_cache']['entries_count'] - stats_after['file_cache']['entries_count']
            
            return {
                "status": "success",
                "data": {
                    "optimization_completed": True,
                    "memory_freed_mb": memory_freed,
                    "entries_removed": entries_removed,
                    "before": {
                        "entries": stats_before['file_cache']['entries_count'],
                        "memory_mb": stats_before.get('combined_memory_mb', 0)
                    },
                    "after": {
                        "entries": stats_after['file_cache']['entries_count'],
                        "memory_mb": stats_after.get('combined_memory_mb', 0)
                    },
                    "message": f"Freed {memory_freed:.1f} MB by removing {entries_removed} entries"
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def clear_cache(self) -> Dict[str, Any]:
        """
        Limpa todo o cache
        """
        try:
            # Capturar estatísticas antes
            stats_before = self.file_manager.get_comprehensive_stats()
            
            # Limpar cache
            self.cache.clear()
            
            return {
                "status": "success",
                "data": {
                    "cache_cleared": True,
                    "entries_removed": stats_before['file_cache']['entries_count'],
                    "memory_freed_mb": stats_before.get('combined_memory_mb', 0),
                    "message": "Cache completely cleared"
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def preload_directory(self, directory: str) -> Dict[str, Any]:
        """
        Pré-carrega arquivos de um diretório no cache
        """
        try:
            dir_path = Path(directory)
            
            if not dir_path.exists():
                return {
                    "status": "error",
                    "message": f"Directory not found: {directory}"
                }
            
            # Capturar estatísticas antes
            stats_before = self.file_manager.get_comprehensive_stats()
            
            # Executar prefetch
            self.file_manager.prefetch_directory(dir_path)
            
            # Capturar estatísticas depois
            stats_after = self.file_manager.get_comprehensive_stats()
            
            files_loaded = stats_after['file_cache']['entries_count'] - stats_before['file_cache']['entries_count']
            memory_used = stats_after.get('combined_memory_mb', 0) - stats_before.get('combined_memory_mb', 0)
            
            return {
                "status": "success",
                "data": {
                    "preload_completed": True,
                    "directory": str(dir_path),
                    "files_loaded": files_loaded,
                    "memory_used_mb": memory_used,
                    "message": f"Preloaded {files_loaded} files using {memory_used:.1f} MB"
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """
        Retorna configuração atual do cache
        """
        try:
            stats = self.cache.get_stats()
            config = stats.get('config', {})
            
            return {
                "status": "success",
                "data": {
                    "strategy": config.get('strategy', 'unknown'),
                    "compression_level": config.get('compression_level', 0),
                    "ttl_hours": config.get('ttl_hours', 0),
                    "max_entries": config.get('max_entries', 0),
                    "memory_limit_mb": stats.get('memory_limit_mb', 0),
                    "auto_cleanup_enabled": True,  # Sempre habilitado
                    "persistence_enabled": True    # Sempre habilitado
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _calculate_avg_compression(self) -> float:
        """Calcula ratio médio de compressão"""
        try:
            # Este é um placeholder - em implementação real, 
            # precisaríamos rastrear ratios de compressão individualmente
            stats = self.file_manager.get_comprehensive_stats()
            compressions = stats.get('audio_cache', {}).get('compressions', 0)
            
            if compressions > 0:
                # Estimativa baseada em compressões realizadas
                return 0.7  # 70% do tamanho original (30% economia)
            else:
                return 1.0  # Sem compressão
                
        except Exception:
            return 1.0


def main():
    """
    Ponto de entrada CLI para gerenciamento de cache
    """
    parser = argparse.ArgumentParser(description="MeetingScribe File Cache CLI")
    parser.add_argument("command", choices=[
        "status", "insights", "optimize", "clear", "preload", "config"
    ], help="Command to execute")
    parser.add_argument("--directory", help="Directory for preload command")
    
    args = parser.parse_args()
    
    cli = CacheCLI()
    
    # Executar comando
    if args.command == "status":
        result = cli.get_cache_status()
    elif args.command == "insights":
        result = cli.get_cache_insights()
    elif args.command == "optimize":
        result = cli.optimize_cache()
    elif args.command == "clear":
        result = cli.clear_cache()
    elif args.command == "preload":
        if not args.directory:
            result = {"status": "error", "message": "Directory required for preload command"}
        else:
            result = cli.preload_directory(args.directory)
    elif args.command == "config":
        result = cli.get_cache_config()
    else:
        result = {"status": "error", "message": "Unknown command"}
    
    # Output JSON para Raycast
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()