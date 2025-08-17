"""
Gerenciador Avançado de Memória

Sistema inteligente para monitoramento e otimização do uso de memória
durante operações de transcrição e processamento de áudio.

Author: MeetingScribe Team
Version: 1.1.0
Python: >=3.8
"""

import gc
import threading
import time
import psutil
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import weakref
from contextlib import contextmanager

from loguru import logger

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class MemoryPressureLevel(str, Enum):
    """Níveis de pressão de memória."""
    LOW = "low"           # < 60% de uso
    MODERATE = "moderate" # 60-80% de uso  
    HIGH = "high"         # 80-90% de uso
    CRITICAL = "critical" # > 90% de uso


class MemoryOptimizationStrategy(str, Enum):
    """Estratégias de otimização de memória."""
    CONSERVATIVE = "conservative"  # Limpeza mínima
    BALANCED = "balanced"         # Limpeza moderada
    AGGRESSIVE = "aggressive"     # Limpeza máxima


@dataclass
class MemoryStats:
    """Estatísticas de uso de memória."""
    total_memory_gb: float
    used_memory_gb: float
    available_memory_gb: float
    memory_percent: float
    
    # Memória específica do processo
    process_memory_mb: float
    process_memory_percent: float
    
    # Memória de GPU (se disponível)
    gpu_memory_used_mb: Optional[float] = None
    gpu_memory_total_mb: Optional[float] = None
    gpu_memory_percent: Optional[float] = None
    
    # Objetos Python
    python_objects_count: int = 0
    
    @property
    def pressure_level(self) -> MemoryPressureLevel:
        """Determina nível de pressão de memória."""
        if self.memory_percent < 60:
            return MemoryPressureLevel.LOW
        elif self.memory_percent < 80:
            return MemoryPressureLevel.MODERATE
        elif self.memory_percent < 90:
            return MemoryPressureLevel.HIGH
        else:
            return MemoryPressureLevel.CRITICAL


@dataclass
class MemoryManagerConfig:
    """Configuração do gerenciador de memória."""
    # Limites de memória
    max_memory_usage_percent: float = 85.0
    warning_threshold_percent: float = 75.0
    critical_threshold_percent: float = 90.0
    
    # Configurações de monitoramento
    monitoring_interval_seconds: float = 10.0
    enable_auto_cleanup: bool = True
    enable_proactive_gc: bool = True
    
    # Estratégias de otimização
    default_strategy: MemoryOptimizationStrategy = MemoryOptimizationStrategy.BALANCED
    
    # Configurações específicas
    max_cache_size_mb: float = 2048  # 2GB
    max_chunk_memory_mb: float = 512  # 512MB por chunk
    
    # Callbacks
    memory_warning_callback: Optional[Callable[[MemoryStats], None]] = None
    memory_critical_callback: Optional[Callable[[MemoryStats], None]] = None


class MemoryTracker:
    """Rastreador de objetos em memória."""
    
    def __init__(self):
        self._tracked_objects: Dict[str, List[weakref.ref]] = {}
        self._object_sizes: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def register_object(self, obj: Any, category: str, size_mb: float = 0.0):
        """Registra objeto para rastreamento."""
        with self._lock:
            if category not in self._tracked_objects:
                self._tracked_objects[category] = []
                self._object_sizes[category] = 0.0
            
            # Criar weak reference
            weak_ref = weakref.ref(obj, lambda ref: self._cleanup_reference(ref, category))
            self._tracked_objects[category].append(weak_ref)
            self._object_sizes[category] += size_mb
    
    def _cleanup_reference(self, ref: weakref.ref, category: str):
        """Remove referência morta."""
        with self._lock:
            if category in self._tracked_objects:
                try:
                    self._tracked_objects[category].remove(ref)
                except ValueError:
                    pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas dos objetos rastreados."""
        with self._lock:
            stats = {}
            total_objects = 0
            total_memory_mb = 0.0
            
            for category, refs in self._tracked_objects.items():
                # Limpar referências mortas
                alive_refs = [ref for ref in refs if ref() is not None]
                self._tracked_objects[category] = alive_refs
                
                alive_count = len(alive_refs)
                category_memory = self._object_sizes[category] * (alive_count / len(refs)) if refs else 0
                
                stats[category] = {
                    'count': alive_count,
                    'memory_mb': category_memory
                }
                
                total_objects += alive_count
                total_memory_mb += category_memory
            
            stats['total'] = {
                'objects': total_objects,
                'memory_mb': total_memory_mb
            }
            
            return stats
    
    def cleanup_category(self, category: str) -> int:
        """Força limpeza de uma categoria específica."""
        with self._lock:
            if category not in self._tracked_objects:
                return 0
            
            refs = self._tracked_objects[category]
            cleaned = 0
            
            for ref in refs[:]:  # Cópia da lista
                obj = ref()
                if obj is not None:
                    # Tentar limpar objeto se tiver método cleanup
                    if hasattr(obj, 'cleanup'):
                        try:
                            obj.cleanup()
                            cleaned += 1
                        except Exception as e:
                            logger.warning(f"Erro ao limpar objeto {type(obj)}: {e}")
            
            return cleaned


class MemoryManager:
    """
    Gerenciador inteligente de memória.
    
    Monitora uso de memória e aplica otimizações automáticas
    para manter performance e estabilidade.
    """
    
    def __init__(self, config: Optional[MemoryManagerConfig] = None):
        """
        Inicializa o gerenciador de memória.
        
        Args:
            config: Configuração do gerenciador
        """
        self.config = config or MemoryManagerConfig()
        self.tracker = MemoryTracker()
        
        # Estado interno
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = False
        self._lock = threading.Lock()
        
        # Estatísticas
        self._last_stats: Optional[MemoryStats] = None
        self._gc_count = 0
        self._cleanup_count = 0
        
        logger.info(f"Gerenciador de memória inicializado - limite: {self.config.max_memory_usage_percent}%")
    
    def get_current_stats(self) -> MemoryStats:
        """Obtém estatísticas atuais de memória."""
        # Memória do sistema
        memory = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info()
        
        stats = MemoryStats(
            total_memory_gb=memory.total / (1024**3),
            used_memory_gb=memory.used / (1024**3),
            available_memory_gb=memory.available / (1024**3),
            memory_percent=memory.percent,
            process_memory_mb=process_memory.rss / (1024**2),
            process_memory_percent=(process_memory.rss / memory.total) * 100
        )
        
        # Memória de GPU se disponível
        if TORCH_AVAILABLE and torch.cuda.is_available():
            try:
                gpu_memory = torch.cuda.memory_stats()
                allocated = gpu_memory.get('allocated_bytes.all.current', 0)
                reserved = gpu_memory.get('reserved_bytes.all.current', 0)
                
                # Obter memória total da GPU
                device_props = torch.cuda.get_device_properties(0)
                total_memory = device_props.total_memory
                
                stats.gpu_memory_used_mb = allocated / (1024**2)
                stats.gpu_memory_total_mb = total_memory / (1024**2)
                stats.gpu_memory_percent = (allocated / total_memory) * 100
                
            except Exception as e:
                logger.debug(f"Erro ao obter estatísticas de GPU: {e}")
        
        # Contagem de objetos Python
        if hasattr(gc, 'get_stats'):
            gc_stats = gc.get_stats()
            stats.python_objects_count = sum(stat['collections'] for stat in gc_stats)
        
        self._last_stats = stats
        return stats
    
    def check_memory_pressure(self) -> MemoryPressureLevel:
        """Verifica nível atual de pressão de memória."""
        stats = self.get_current_stats()
        return stats.pressure_level
    
    def optimize_memory(self, strategy: Optional[MemoryOptimizationStrategy] = None) -> Dict[str, Any]:
        """
        Otimiza uso de memória aplicando estratégia especificada.
        
        Args:
            strategy: Estratégia de otimização
            
        Returns:
            Dict com resultados da otimização
        """
        if strategy is None:
            strategy = self.config.default_strategy
        
        logger.info(f"Iniciando otimização de memória - estratégia: {strategy}")
        
        stats_before = self.get_current_stats()
        results = {
            'strategy': strategy,
            'memory_before_mb': stats_before.process_memory_mb,
            'memory_freed_mb': 0.0,
            'actions_taken': []
        }
        
        try:
            # 1. Garbage collection Python
            if strategy in [MemoryOptimizationStrategy.BALANCED, MemoryOptimizationStrategy.AGGRESSIVE]:
                collected = self._perform_garbage_collection()
                if collected > 0:
                    results['actions_taken'].append(f"Python GC: {collected} objetos coletados")
                    self._gc_count += 1
            
            # 2. Limpeza de cache do modelo
            if strategy == MemoryOptimizationStrategy.AGGRESSIVE:
                freed_cache = self._cleanup_model_cache()
                if freed_cache > 0:
                    results['actions_taken'].append(f"Cache de modelos: {freed_cache:.1f}MB liberados")
            
            # 3. Limpeza de objetos rastreados
            if strategy in [MemoryOptimizationStrategy.BALANCED, MemoryOptimizationStrategy.AGGRESSIVE]:
                cleaned_objects = self._cleanup_tracked_objects()
                if cleaned_objects > 0:
                    results['actions_taken'].append(f"Objetos rastreados: {cleaned_objects} limpos")
                    self._cleanup_count += 1
            
            # 4. Limpeza de cache GPU
            if TORCH_AVAILABLE and torch.cuda.is_available():
                if strategy == MemoryOptimizationStrategy.AGGRESSIVE:
                    self._cleanup_gpu_cache()
                    results['actions_taken'].append("Cache GPU limpo")
            
            # 5. Limpeza de arrays NumPy
            if NUMPY_AVAILABLE and strategy == MemoryOptimizationStrategy.AGGRESSIVE:
                self._cleanup_numpy_arrays()
                results['actions_taken'].append("Arrays NumPy otimizados")
            
            # Calcular memória liberada
            stats_after = self.get_current_stats()
            memory_freed = stats_before.process_memory_mb - stats_after.process_memory_mb
            results['memory_freed_mb'] = max(0, memory_freed)
            results['memory_after_mb'] = stats_after.process_memory_mb
            
            logger.success(f"Otimização concluída - {memory_freed:.1f}MB liberados")
            
        except Exception as e:
            logger.error(f"Erro na otimização de memória: {e}")
            results['error'] = str(e)
        
        return results
    
    def _perform_garbage_collection(self) -> int:
        """Executa coleta de lixo otimizada."""
        # Forçar coleta de todas as gerações
        collected = 0
        for generation in range(3):
            collected += gc.collect(generation)
        
        logger.debug(f"Garbage collection: {collected} objetos coletados")
        return collected
    
    def _cleanup_model_cache(self) -> float:
        """Limpa cache de modelos se disponível."""
        try:
            from src.core.model_cache import get_model_cache
            cache = get_model_cache()
            
            stats_before = cache.get_stats()
            memory_before = stats_before['memory_usage_mb']
            
            # Limpar modelos menos usados se acima do limite
            if memory_before > self.config.max_cache_size_mb:
                # Forçar eviction de alguns modelos
                while (cache.get_stats()['memory_usage_mb'] > self.config.max_cache_size_mb * 0.8 
                       and len(cache._cache) > 1):
                    cache._evict_model()
                
                stats_after = cache.get_stats()
                memory_freed = memory_before - stats_after['memory_usage_mb']
                return memory_freed
            
        except Exception as e:
            logger.debug(f"Erro ao limpar cache de modelos: {e}")
        
        return 0.0
    
    def _cleanup_tracked_objects(self) -> int:
        """Limpa objetos rastreados."""
        cleaned = 0
        
        # Limpar objetos por categoria baseado na pressão
        pressure = self.check_memory_pressure()
        
        if pressure in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL]:
            # Limpar chunks antigos
            cleaned += self.tracker.cleanup_category('audio_chunks')
            
        if pressure == MemoryPressureLevel.CRITICAL:
            # Limpeza mais agressiva
            cleaned += self.tracker.cleanup_category('transcription_results')
            cleaned += self.tracker.cleanup_category('temp_files')
        
        return cleaned
    
    def _cleanup_gpu_cache(self):
        """Limpa cache de GPU."""
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    
    def _cleanup_numpy_arrays(self):
        """Otimiza arrays NumPy."""
        # Forçar limpeza de arrays temporários
        if NUMPY_AVAILABLE:
            # NumPy não tem cache explícito, mas gc.collect ajuda
            pass
    
    def start_monitoring(self):
        """Inicia monitoramento automático de memória."""
        if self._monitoring:
            logger.warning("Monitoramento já está ativo")
            return
        
        self._monitoring = True
        self._stop_monitoring = False
        
        def monitor_worker():
            logger.info("Monitoramento de memória iniciado")
            
            while not self._stop_monitoring:
                try:
                    stats = self.get_current_stats()
                    pressure = stats.pressure_level
                    
                    # Verificar thresholds
                    if stats.memory_percent >= self.config.critical_threshold_percent:
                        logger.critical(f"Memória crítica: {stats.memory_percent:.1f}%")
                        
                        if self.config.memory_critical_callback:
                            self.config.memory_critical_callback(stats)
                        
                        if self.config.enable_auto_cleanup:
                            self.optimize_memory(MemoryOptimizationStrategy.AGGRESSIVE)
                    
                    elif stats.memory_percent >= self.config.warning_threshold_percent:
                        logger.warning(f"Memória alta: {stats.memory_percent:.1f}%")
                        
                        if self.config.memory_warning_callback:
                            self.config.memory_warning_callback(stats)
                        
                        if self.config.enable_auto_cleanup:
                            self.optimize_memory(MemoryOptimizationStrategy.BALANCED)
                    
                    # GC proativo
                    if (self.config.enable_proactive_gc and 
                        pressure in [MemoryPressureLevel.MODERATE, MemoryPressureLevel.HIGH]):
                        gc.collect(0)  # Coleta rápida da geração 0
                    
                    time.sleep(self.config.monitoring_interval_seconds)
                    
                except Exception as e:
                    logger.error(f"Erro no monitoramento de memória: {e}")
                    time.sleep(5)  # Intervalo menor em caso de erro
        
        self._monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Para monitoramento automático."""
        if not self._monitoring:
            return
        
        self._stop_monitoring = True
        self._monitoring = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        
        logger.info("Monitoramento de memória parado")
    
    @contextmanager
    def memory_context(self, 
                      cleanup_on_exit: bool = True,
                      strategy: Optional[MemoryOptimizationStrategy] = None):
        """Context manager para gestão automática de memória."""
        stats_before = self.get_current_stats()
        logger.debug(f"Iniciando contexto de memória - {stats_before.process_memory_mb:.1f}MB")
        
        try:
            yield self
        finally:
            if cleanup_on_exit:
                results = self.optimize_memory(strategy)
                logger.debug(f"Contexto finalizado - {results['memory_freed_mb']:.1f}MB liberados")
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo das operações do gerenciador."""
        current_stats = self.get_current_stats()
        tracker_stats = self.tracker.get_stats()
        
        return {
            'current_memory': {
                'system_percent': current_stats.memory_percent,
                'process_mb': current_stats.process_memory_mb,
                'pressure_level': current_stats.pressure_level.value
            },
            'gpu_memory': {
                'used_mb': current_stats.gpu_memory_used_mb,
                'total_mb': current_stats.gpu_memory_total_mb,
                'percent': current_stats.gpu_memory_percent
            } if current_stats.gpu_memory_used_mb else None,
            'tracked_objects': tracker_stats,
            'operations': {
                'gc_runs': self._gc_count,
                'cleanup_runs': self._cleanup_count
            },
            'monitoring': {
                'active': self._monitoring,
                'interval_seconds': self.config.monitoring_interval_seconds
            }
        }
    
    def register_object(self, obj: Any, category: str, size_mb: float = 0.0):
        """Registra objeto para rastreamento de memória."""
        self.tracker.register_object(obj, category, size_mb)
    
    def cleanup(self):
        """Limpa recursos do gerenciador."""
        self.stop_monitoring()
        
        # Limpeza final
        if self.config.enable_auto_cleanup:
            self.optimize_memory(MemoryOptimizationStrategy.CONSERVATIVE)
        
        logger.info("Gerenciador de memória finalizado")


# =============================================================================
# SINGLETON GLOBAL
# =============================================================================

_global_memory_manager: Optional[MemoryManager] = None
_manager_lock = threading.Lock()


def get_memory_manager() -> MemoryManager:
    """Retorna instância singleton do gerenciador global."""
    global _global_memory_manager
    
    if _global_memory_manager is None:
        with _manager_lock:
            if _global_memory_manager is None:
                config = MemoryManagerConfig()
                _global_memory_manager = MemoryManager(config)
                logger.info("Gerenciador global de memória inicializado")
    
    return _global_memory_manager


def shutdown_memory_manager():
    """Finaliza gerenciador global."""
    global _global_memory_manager
    
    if _global_memory_manager is not None:
        _global_memory_manager.cleanup()
        _global_memory_manager = None


# =============================================================================
# FACTORY FUNCTIONS E UTILITIES
# =============================================================================

def optimize_memory_now(strategy: MemoryOptimizationStrategy = MemoryOptimizationStrategy.BALANCED) -> Dict[str, Any]:
    """Otimiza memória imediatamente usando o gerenciador global."""
    manager = get_memory_manager()
    return manager.optimize_memory(strategy)


def get_memory_stats() -> MemoryStats:
    """Obtém estatísticas atuais de memória."""
    manager = get_memory_manager()
    return manager.get_current_stats()


def check_memory_pressure() -> MemoryPressureLevel:
    """Verifica nível atual de pressão de memória."""
    manager = get_memory_manager()
    return manager.check_memory_pressure()


@contextmanager
def managed_memory(strategy: Optional[MemoryOptimizationStrategy] = None):
    """Context manager para gestão automática de memória."""
    manager = get_memory_manager()
    with manager.memory_context(cleanup_on_exit=True, strategy=strategy):
        yield manager


def register_for_cleanup(obj: Any, category: str, size_mb: float = 0.0):
    """Registra objeto para limpeza automática."""
    manager = get_memory_manager()
    manager.register_object(obj, category, size_mb)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "MemoryManager",
    "MemoryManagerConfig",
    "MemoryStats",
    "MemoryPressureLevel",
    "MemoryOptimizationStrategy",
    "get_memory_manager",
    "shutdown_memory_manager",
    "optimize_memory_now",
    "get_memory_stats",
    "check_memory_pressure",
    "managed_memory",
    "register_for_cleanup"
]