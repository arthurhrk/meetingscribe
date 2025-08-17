# -*- coding: utf-8 -*-
"""
Sistema de Monitoramento de Performance - MeetingScribe
Coleta e gerencia métricas de performance para dashboard Raycast
"""

import time
import threading
import json
import psutil
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import statistics
from collections import deque, defaultdict

@dataclass
class PerformanceMetric:
    """Representa uma métrica de performance individual"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    category: str
    tags: Dict[str, str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário serializável"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class TranscriptionMetrics:
    """Métricas específicas de transcrição"""
    duration: float
    audio_length: float
    model_size: str
    chunks_count: int
    processing_time: float
    cache_hits: int
    memory_used: float
    gpu_used: bool
    success: bool
    error_message: Optional[str] = None

@dataclass
class SystemMetrics:
    """Métricas do sistema"""
    cpu_percent: float
    memory_percent: float
    gpu_memory_used: float
    disk_usage_percent: float
    active_processes: int
    cache_size: float

class PerformanceMonitor:
    """
    Monitor principal de performance com thread dedicada
    Coleta métricas contínuas e as expõe para o Raycast
    """
    
    def __init__(self, 
                 storage_path: str = "storage/metrics",
                 max_metrics: int = 10000,
                 collection_interval: float = 5.0):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.max_metrics = max_metrics
        self.collection_interval = collection_interval
        
        # Thread-safe storage
        self._lock = threading.RLock()
        self._metrics: deque = deque(maxlen=max_metrics)
        self._aggregated_metrics: Dict[str, Any] = {}
        self._transcription_history: List[TranscriptionMetrics] = []
        
        # Monitoring thread
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Callbacks para eventos
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Estatísticas em tempo real
        self._real_time_stats = {
            'transcriptions_today': 0,
            'average_processing_time': 0.0,
            'cache_hit_rate': 0.0,
            'memory_efficiency': 0.0,
            'system_health': 'optimal'
        }
        
        self._init_storage()
    
    def _init_storage(self):
        """Inicializa arquivos de storage"""
        try:
            self._load_persisted_metrics()
        except Exception as e:
            print(f"Warning: Could not load persisted metrics: {e}")
    
    def start_monitoring(self):
        """Inicia monitoramento contínuo"""
        if self._monitoring:
            return
            
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="PerformanceMonitor"
        )
        self._monitor_thread.start()
        
        self.add_metric(
            name="monitoring_started",
            value=1,
            unit="bool",
            category="system"
        )
    
    def stop_monitoring(self):
        """Para monitoramento"""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        
        self._persist_metrics()
        
        self.add_metric(
            name="monitoring_stopped", 
            value=1,
            unit="bool",
            category="system"
        )
    
    def _monitoring_loop(self):
        """Loop principal de coleta de métricas"""
        while self._monitoring:
            try:
                self._collect_system_metrics()
                self._update_aggregated_metrics()
                self._update_real_time_stats()
                time.sleep(self.collection_interval)
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self):
        """Coleta métricas do sistema"""
        try:
            # CPU e Memória
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Disco
            disk = psutil.disk_usage(self.storage_path.parent)
            
            # Processos
            active_processes = len(psutil.pids())
            
            # GPU (se disponível)
            gpu_memory = self._get_gpu_memory_usage()
            
            # Cache size
            cache_size = self._get_cache_size()
            
            system_metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                gpu_memory_used=gpu_memory,
                disk_usage_percent=disk.percent,
                active_processes=active_processes,
                cache_size=cache_size
            )
            
            # Adiciona métricas individuais
            self.add_metric("cpu_usage", cpu_percent, "percent", "system")
            self.add_metric("memory_usage", memory.percent, "percent", "system")
            self.add_metric("disk_usage", disk.percent, "percent", "system")
            self.add_metric("cache_size", cache_size, "MB", "cache")
            
        except Exception as e:
            print(f"Error collecting system metrics: {e}")
    
    def _get_gpu_memory_usage(self) -> float:
        """Obtém uso de memória GPU (se disponível)"""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.cuda.memory_allocated() / 1024**2  # MB
        except ImportError:
            pass
        return 0.0
    
    def _get_cache_size(self) -> float:
        """Obtém tamanho do cache de modelos"""
        try:
            from .model_cache import ModelCache
            cache = ModelCache.get_instance()
            return cache.get_memory_usage() / 1024**2  # MB
        except ImportError:
            return 0.0
    
    def add_metric(self, 
                   name: str, 
                   value: float, 
                   unit: str, 
                   category: str,
                   tags: Dict[str, str] = None):
        """Adiciona uma métrica"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            category=category,
            tags=tags or {}
        )
        
        with self._lock:
            self._metrics.append(metric)
        
        # Executa callbacks
        for callback in self._callbacks.get(name, []):
            try:
                callback(metric)
            except Exception as e:
                print(f"Error in metric callback: {e}")
    
    def add_transcription_metrics(self, metrics: TranscriptionMetrics):
        """Adiciona métricas de transcrição"""
        with self._lock:
            self._transcription_history.append(metrics)
            
            # Limita histórico
            if len(self._transcription_history) > 1000:
                self._transcription_history = self._transcription_history[-1000:]
        
        # Adiciona métricas individuais
        self.add_metric("transcription_duration", metrics.duration, "seconds", "transcription",
                       {"model": metrics.model_size, "success": str(metrics.success)})
        self.add_metric("processing_time", metrics.processing_time, "seconds", "transcription")
        self.add_metric("cache_hits", metrics.cache_hits, "count", "cache")
        self.add_metric("chunks_processed", metrics.chunks_count, "count", "transcription")
    
    def get_metrics_for_raycast(self) -> Dict[str, Any]:
        """
        Retorna métricas formatadas para consumo do Raycast
        """
        with self._lock:
            recent_metrics = list(self._metrics)[-100:]  # Últimas 100 métricas
            
            # Estatísticas básicas
            stats = {
                "timestamp": datetime.now().isoformat(),
                "system": self._get_system_summary(),
                "transcription": self._get_transcription_summary(),
                "cache": self._get_cache_summary(),
                "realtime": self._real_time_stats.copy(),
                "recent_metrics": [m.to_dict() for m in recent_metrics[-20:]]
            }
            
            return stats
    
    def _get_system_summary(self) -> Dict[str, Any]:
        """Resumo das métricas do sistema"""
        try:
            recent_system = [m for m in list(self._metrics)[-50:] if m.category == "system"]
            
            if not recent_system:
                return {"status": "no_data"}
            
            cpu_values = [m.value for m in recent_system if m.name == "cpu_usage"]
            memory_values = [m.value for m in recent_system if m.name == "memory_usage"]
            
            return {
                "cpu_avg": statistics.mean(cpu_values) if cpu_values else 0,
                "cpu_max": max(cpu_values) if cpu_values else 0,
                "memory_avg": statistics.mean(memory_values) if memory_values else 0,
                "memory_max": max(memory_values) if memory_values else 0,
                "status": self._get_system_health_status()
            }
        except Exception:
            return {"status": "error"}
    
    def _get_transcription_summary(self) -> Dict[str, Any]:
        """Resumo das métricas de transcrição"""
        try:
            recent_transcriptions = self._transcription_history[-10:]
            
            if not recent_transcriptions:
                return {"status": "no_transcriptions"}
            
            success_rate = sum(1 for t in recent_transcriptions if t.success) / len(recent_transcriptions)
            avg_processing_time = statistics.mean([t.processing_time for t in recent_transcriptions])
            total_cache_hits = sum(t.cache_hits for t in recent_transcriptions)
            
            return {
                "total_today": len([t for t in self._transcription_history 
                                  if (datetime.now() - datetime.fromisoformat(str(t.duration))).days == 0]),
                "success_rate": success_rate * 100,
                "avg_processing_time": avg_processing_time,
                "cache_hits_total": total_cache_hits,
                "status": "healthy" if success_rate > 0.9 else "degraded"
            }
        except Exception:
            return {"status": "error"}
    
    def _get_cache_summary(self) -> Dict[str, Any]:
        """Resumo das métricas de cache"""
        try:
            cache_metrics = [m for m in list(self._metrics)[-100:] if m.category == "cache"]
            
            if not cache_metrics:
                return {"status": "no_data"}
            
            cache_size_values = [m.value for m in cache_metrics if m.name == "cache_size"]
            cache_hits_values = [m.value for m in cache_metrics if m.name == "cache_hits"]
            
            return {
                "current_size_mb": cache_size_values[-1] if cache_size_values else 0,
                "total_hits": sum(cache_hits_values),
                "hit_rate": self._calculate_cache_hit_rate(),
                "status": "optimal"
            }
        except Exception:
            return {"status": "error"}
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calcula taxa de acerto do cache"""
        try:
            recent_transcriptions = self._transcription_history[-20:]
            if not recent_transcriptions:
                return 0.0
            
            total_requests = len(recent_transcriptions)
            total_hits = sum(t.cache_hits for t in recent_transcriptions if t.cache_hits > 0)
            
            return (total_hits / total_requests) * 100 if total_requests > 0 else 0.0
        except Exception:
            return 0.0
    
    def _get_system_health_status(self) -> str:
        """Determina status de saúde do sistema"""
        try:
            recent_metrics = list(self._metrics)[-20:]
            cpu_values = [m.value for m in recent_metrics if m.name == "cpu_usage"]
            memory_values = [m.value for m in recent_metrics if m.name == "memory_usage"]
            
            if cpu_values and memory_values:
                avg_cpu = statistics.mean(cpu_values)
                avg_memory = statistics.mean(memory_values)
                
                if avg_cpu > 80 or avg_memory > 85:
                    return "critical"
                elif avg_cpu > 60 or avg_memory > 70:
                    return "warning"
                else:
                    return "optimal"
            
            return "unknown"
        except Exception:
            return "error"
    
    def _update_aggregated_metrics(self):
        """Atualiza métricas agregadas"""
        try:
            with self._lock:
                recent_metrics = list(self._metrics)[-100:]
                
                # Agrupa por categoria
                by_category = defaultdict(list)
                for metric in recent_metrics:
                    by_category[metric.category].append(metric)
                
                # Calcula agregações
                self._aggregated_metrics = {}
                for category, metrics in by_category.items():
                    if metrics:
                        values = [m.value for m in metrics]
                        self._aggregated_metrics[category] = {
                            "count": len(values),
                            "avg": statistics.mean(values),
                            "min": min(values),
                            "max": max(values),
                            "latest": values[-1] if values else 0
                        }
        except Exception as e:
            print(f"Error updating aggregated metrics: {e}")
    
    def _update_real_time_stats(self):
        """Atualiza estatísticas em tempo real"""
        try:
            today = datetime.now().date()
            transcriptions_today = len([
                t for t in self._transcription_history 
                if datetime.fromisoformat(str(t.duration)).date() == today
            ])
            
            recent_transcriptions = self._transcription_history[-10:]
            avg_processing_time = (
                statistics.mean([t.processing_time for t in recent_transcriptions])
                if recent_transcriptions else 0.0
            )
            
            cache_hit_rate = self._calculate_cache_hit_rate()
            
            # Eficiência de memória (baseada no uso vs disponível)
            recent_memory = [m for m in list(self._metrics)[-10:] if m.name == "memory_usage"]
            memory_efficiency = (
                100 - statistics.mean([m.value for m in recent_memory])
                if recent_memory else 100.0
            )
            
            self._real_time_stats.update({
                'transcriptions_today': transcriptions_today,
                'average_processing_time': avg_processing_time,
                'cache_hit_rate': cache_hit_rate,
                'memory_efficiency': memory_efficiency,
                'system_health': self._get_system_health_status()
            })
            
        except Exception as e:
            print(f"Error updating real-time stats: {e}")
    
    def _persist_metrics(self):
        """Persiste métricas em disco"""
        try:
            metrics_file = self.storage_path / "performance_metrics.json"
            
            with self._lock:
                data = {
                    "metrics": [m.to_dict() for m in list(self._metrics)[-1000:]],
                    "transcription_history": [asdict(t) for t in self._transcription_history[-100:]],
                    "aggregated": self._aggregated_metrics,
                    "realtime_stats": self._real_time_stats,
                    "last_updated": datetime.now().isoformat()
                }
            
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error persisting metrics: {e}")
    
    def _load_persisted_metrics(self):
        """Carrega métricas persistidas"""
        metrics_file = self.storage_path / "performance_metrics.json"
        
        if not metrics_file.exists():
            return
        
        try:
            with open(metrics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Carrega métricas
            for metric_data in data.get("metrics", []):
                metric = PerformanceMetric(
                    name=metric_data["name"],
                    value=metric_data["value"],
                    unit=metric_data["unit"],
                    timestamp=datetime.fromisoformat(metric_data["timestamp"]),
                    category=metric_data["category"],
                    tags=metric_data.get("tags", {})
                )
                self._metrics.append(metric)
            
            # Carrega histórico de transcrições
            for trans_data in data.get("transcription_history", []):
                trans = TranscriptionMetrics(**trans_data)
                self._transcription_history.append(trans)
            
            # Carrega dados agregados
            self._aggregated_metrics = data.get("aggregated", {})
            self._real_time_stats = data.get("realtime_stats", self._real_time_stats)
            
        except Exception as e:
            print(f"Error loading persisted metrics: {e}")
    
    def add_callback(self, metric_name: str, callback: Callable):
        """Adiciona callback para métrica específica"""
        self._callbacks[metric_name].append(callback)
    
    def export_metrics_report(self, format: str = "json") -> str:
        """Exporta relatório completo de métricas"""
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.get_metrics_for_raycast(),
            "detailed_metrics": [m.to_dict() for m in list(self._metrics)],
            "transcription_history": [asdict(t) for t in self._transcription_history],
            "aggregated_metrics": self._aggregated_metrics
        }
        
        if format.lower() == "json":
            return json.dumps(report_data, indent=2, ensure_ascii=False)
        
        # Adicionar outros formatos no futuro (CSV, HTML, etc.)
        return json.dumps(report_data, indent=2, ensure_ascii=False)

# Singleton global
_performance_monitor: Optional[PerformanceMonitor] = None

def get_performance_monitor() -> PerformanceMonitor:
    """Obtém instância singleton do monitor de performance"""
    global _performance_monitor
    
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        _performance_monitor.start_monitoring()
    
    return _performance_monitor

def init_performance_monitoring(auto_start: bool = True) -> PerformanceMonitor:
    """Inicializa sistema de monitoramento de performance"""
    monitor = get_performance_monitor()
    
    if auto_start and not monitor._monitoring:
        monitor.start_monitoring()
    
    return monitor

# Context manager para medição de performance
class PerformanceTimer:
    """Context manager para medir tempo de execução"""
    
    def __init__(self, 
                 name: str, 
                 category: str = "timing",
                 tags: Dict[str, str] = None):
        self.name = name
        self.category = category
        self.tags = tags or {}
        self.start_time = None
        self.monitor = get_performance_monitor()
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.monitor.add_metric(
                name=self.name,
                value=duration,
                unit="seconds",
                category=self.category,
                tags=self.tags
            )

# Decorator para medição automática
def monitor_performance(name: str = None, category: str = "function"):
    """Decorator para monitoramento automático de performance"""
    def decorator(func):
        metric_name = name or f"{func.__module__}.{func.__name__}"
        
        def wrapper(*args, **kwargs):
            with PerformanceTimer(metric_name, category):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator