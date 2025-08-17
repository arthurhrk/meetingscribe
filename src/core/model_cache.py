"""
Cache Inteligente de Modelos Whisper

Sistema de cache para otimizar carregamento de modelos Whisper,
reduzindo drasticamente tempo de inicialização e uso de memória.

Author: MeetingScribe Team
Version: 1.1.0
Python: >=3.8
"""

import gc
import time
import threading
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from loguru import logger
from faster_whisper import WhisperModel

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from config import settings


class CacheStrategy(str, Enum):
    """Estratégias de cache."""
    LRU = "lru"          # Least Recently Used
    LFU = "lfu"          # Least Frequently Used
    TTL = "ttl"          # Time To Live
    ADAPTIVE = "adaptive" # Adaptativo baseado no uso


@dataclass
class ModelCacheEntry:
    """Entrada do cache de modelo."""
    model: WhisperModel
    model_size: str
    device: str
    compute_type: str
    
    # Metadados de uso
    created_at: datetime
    last_used: datetime
    use_count: int
    memory_usage_mb: float
    
    # Configurações do modelo
    config_hash: str
    
    def update_usage(self) -> None:
        """Atualiza estatísticas de uso."""
        self.last_used = datetime.now()
        self.use_count += 1
    
    @property
    def age_minutes(self) -> float:
        """Idade do modelo em minutos."""
        return (datetime.now() - self.created_at).total_seconds() / 60
    
    @property
    def idle_minutes(self) -> float:
        """Tempo ocioso em minutos."""
        return (datetime.now() - self.last_used).total_seconds() / 60


class ModelCache:
    """
    Cache inteligente para modelos Whisper.
    
    Características:
    - Cache LRU com limite de memória
    - Preload de modelos frequentes
    - Limpeza automática
    - Monitoramento de uso
    """
    
    def __init__(
        self,
        max_models: int = 3,
        max_memory_mb: float = 8192,  # 8GB
        cache_strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
        ttl_minutes: int = 30,
        preload_common: bool = True
    ):
        """
        Inicializa o cache de modelos.
        
        Args:
            max_models: Número máximo de modelos em cache
            max_memory_mb: Memória máxima em MB
            cache_strategy: Estratégia de eviction
            ttl_minutes: TTL para estratégia TTL
            preload_common: Precarregar modelos comuns
        """
        self.max_models = max_models
        self.max_memory_mb = max_memory_mb
        self.cache_strategy = cache_strategy
        self.ttl_minutes = ttl_minutes
        self.preload_common = preload_common
        
        # Cache principal
        self._cache: Dict[str, ModelCacheEntry] = {}
        self._lock = threading.RLock()
        
        # Estatísticas
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'memory_usage_mb': 0.0,
            'preloads': 0
        }
        
        # Thread de limpeza
        self._cleanup_thread = None
        self._stop_cleanup = False
        
        logger.info(f"Cache de modelos inicializado - max_models: {max_models}, max_memory: {max_memory_mb}MB")
        
        # Iniciar limpeza automática
        self._start_cleanup_thread()
        
        # Preload se habilitado
        if preload_common:
            self._preload_common_models()
    
    def _generate_cache_key(self, model_size: str, device: str, compute_type: str) -> str:
        """Gera chave única para o cache."""
        return f"{model_size}_{device}_{compute_type}"
    
    def _calculate_model_memory(self, model_size: str, device: str) -> float:
        """Estima uso de memória do modelo em MB."""
        # Estimativas baseadas em observações reais
        memory_estimates = {
            'tiny': {'cpu': 150, 'cuda': 200},
            'base': {'cpu': 300, 'cuda': 400},
            'small': {'cpu': 600, 'cuda': 800},
            'medium': {'cpu': 1200, 'cuda': 1600},
            'large-v2': {'cpu': 2400, 'cuda': 3200},
            'large-v3': {'cpu': 2400, 'cuda': 3200}
        }
        
        base_memory = memory_estimates.get(model_size, {'cpu': 500, 'cuda': 700})
        return base_memory.get(device, base_memory['cpu'])
    
    def get_model(
        self,
        model_size: str,
        device: str = "auto",
        compute_type: str = "auto"
    ) -> Tuple[WhisperModel, bool]:
        """
        Obtém modelo do cache ou carrega novo.
        
        Args:
            model_size: Tamanho do modelo
            device: Dispositivo (auto, cpu, cuda)
            compute_type: Tipo de computação (auto, float32, float16, int8)
            
        Returns:
            Tuple[WhisperModel, bool]: (modelo, cache_hit)
        """
        # Normalizar parâmetros
        if device == "auto":
            device = self._detect_device()
        if compute_type == "auto":
            compute_type = self._auto_compute_type(device)
        
        cache_key = self._generate_cache_key(model_size, device, compute_type)
        
        with self._lock:
            # Verificar cache hit
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                entry.update_usage()
                self._stats['hits'] += 1
                
                logger.debug(f"Cache HIT para {cache_key} (uso #{entry.use_count})")
                return entry.model, True
            
            # Cache miss - carregar modelo
            self._stats['misses'] += 1
            logger.info(f"Cache MISS para {cache_key} - carregando modelo")
            
            # Verificar espaço disponível
            estimated_memory = self._calculate_model_memory(model_size, device)
            self._ensure_cache_space(estimated_memory)
            
            # Carregar modelo
            model = self._load_model(model_size, device, compute_type)
            
            # Adicionar ao cache
            entry = ModelCacheEntry(
                model=model,
                model_size=model_size,
                device=device,
                compute_type=compute_type,
                created_at=datetime.now(),
                last_used=datetime.now(),
                use_count=1,
                memory_usage_mb=estimated_memory,
                config_hash=cache_key
            )
            
            self._cache[cache_key] = entry
            self._update_memory_stats()
            
            logger.success(f"Modelo {cache_key} carregado e adicionado ao cache")
            return model, False
    
    def _detect_device(self) -> str:
        """Detecta melhor dispositivo disponível."""
        if TORCH_AVAILABLE and torch.cuda.is_available():
            return "cuda"
        return "cpu"
    
    def _auto_compute_type(self, device: str) -> str:
        """Seleciona melhor compute type para o dispositivo."""
        if device == "cuda":
            return "float16"  # Mais rápido na GPU
        return "int8"  # Quantização para CPU
    
    def _load_model(self, model_size: str, device: str, compute_type: str) -> WhisperModel:
        """Carrega modelo Whisper com configurações otimizadas."""
        start_time = time.time()
        
        try:
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=None,
                local_files_only=False,
                cpu_threads=4 if device == "cpu" else 0
            )
            
            load_time = time.time() - start_time
            logger.info(f"Modelo {model_size} carregado em {load_time:.2f}s")
            
            return model
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo {model_size}: {e}")
            raise
    
    def _ensure_cache_space(self, required_memory_mb: float) -> None:
        """Garante espaço no cache para novo modelo."""
        # Verificar limite de modelos
        while len(self._cache) >= self.max_models:
            self._evict_model()
        
        # Verificar limite de memória
        while (self._stats['memory_usage_mb'] + required_memory_mb) > self.max_memory_mb:
            if not self._cache:
                break
            self._evict_model()
    
    def _evict_model(self) -> None:
        """Remove modelo do cache usando estratégia configurada."""
        if not self._cache:
            return
        
        if self.cache_strategy == CacheStrategy.LRU:
            # Remover menos recentemente usado
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k].last_used)
        elif self.cache_strategy == CacheStrategy.LFU:
            # Remover menos frequentemente usado
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k].use_count)
        elif self.cache_strategy == CacheStrategy.TTL:
            # Remover expirados primeiro
            expired = [k for k, v in self._cache.items() 
                      if v.age_minutes > self.ttl_minutes]
            if expired:
                oldest_key = expired[0]
            else:
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k].created_at)
        else:  # ADAPTIVE
            # Estratégia adaptativa: considerar idade, uso e memória
            scores = {}
            for key, entry in self._cache.items():
                # Score menor = mais provável de ser removido
                age_score = entry.age_minutes / 60  # Normalizar por hora
                usage_score = 1.0 / max(entry.use_count, 1)
                memory_score = entry.memory_usage_mb / 1000  # Normalizar por GB
                idle_score = entry.idle_minutes / 30  # Normalizar por 30min
                
                scores[key] = age_score + usage_score + memory_score + idle_score
            
            oldest_key = min(scores.keys(), key=lambda k: scores[k])
        
        # Remover modelo
        entry = self._cache.pop(oldest_key)
        self._cleanup_model(entry)
        self._stats['evictions'] += 1
        self._update_memory_stats()
        
        logger.info(f"Modelo {oldest_key} removido do cache (estratégia: {self.cache_strategy})")
    
    def _cleanup_model(self, entry: ModelCacheEntry) -> None:
        """Limpa recursos do modelo."""
        try:
            del entry.model
            gc.collect()
            
            if TORCH_AVAILABLE and torch.cuda.is_available():
                torch.cuda.empty_cache()
                
        except Exception as e:
            logger.warning(f"Erro ao limpar modelo: {e}")
    
    def _update_memory_stats(self) -> None:
        """Atualiza estatísticas de memória."""
        total_memory = sum(entry.memory_usage_mb for entry in self._cache.values())
        self._stats['memory_usage_mb'] = total_memory
    
    def _preload_common_models(self) -> None:
        """Precarrega modelos comuns baseado no hardware."""
        try:
            device = self._detect_device()
            
            # Determinar modelos para preload baseado no hardware
            if device == "cuda":
                models_to_preload = ["base", "small"]
            else:
                models_to_preload = ["tiny", "base"]
            
            for model_size in models_to_preload:
                try:
                    self.get_model(model_size, device)
                    self._stats['preloads'] += 1
                    logger.info(f"Modelo {model_size} precarregado com sucesso")
                except Exception as e:
                    logger.warning(f"Falha ao precarregar modelo {model_size}: {e}")
                    
        except Exception as e:
            logger.error(f"Erro no preload de modelos: {e}")
    
    def _start_cleanup_thread(self) -> None:
        """Inicia thread de limpeza automática."""
        def cleanup_worker():
            while not self._stop_cleanup:
                try:
                    time.sleep(300)  # 5 minutos
                    
                    with self._lock:
                        # Remover modelos expirados (TTL)
                        expired_keys = [
                            k for k, v in self._cache.items()
                            if v.idle_minutes > self.ttl_minutes
                        ]
                        
                        for key in expired_keys:
                            entry = self._cache.pop(key)
                            self._cleanup_model(entry)
                            logger.debug(f"Modelo {key} expirado removido (idle: {entry.idle_minutes:.1f}min)")
                        
                        if expired_keys:
                            self._update_memory_stats()
                            
                        # Garbage collection
                        gc.collect()
                        
                        if TORCH_AVAILABLE and torch.cuda.is_available():
                            torch.cuda.empty_cache()
                            
                except Exception as e:
                    logger.error(f"Erro na limpeza automática: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.debug("Thread de limpeza automática iniciada")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        with self._lock:
            hit_rate = self._stats['hits'] / max(self._stats['hits'] + self._stats['misses'], 1)
            
            return {
                'models_cached': len(self._cache),
                'memory_usage_mb': self._stats['memory_usage_mb'],
                'memory_limit_mb': self.max_memory_mb,
                'memory_usage_pct': (self._stats['memory_usage_mb'] / self.max_memory_mb) * 100,
                'hit_rate': hit_rate,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'preloads': self._stats['preloads'],
                'models': [
                    {
                        'key': key,
                        'model_size': entry.model_size,
                        'device': entry.device,
                        'memory_mb': entry.memory_usage_mb,
                        'age_minutes': entry.age_minutes,
                        'idle_minutes': entry.idle_minutes,
                        'use_count': entry.use_count
                    }
                    for key, entry in self._cache.items()
                ]
            }
    
    def clear_cache(self) -> None:
        """Limpa todo o cache."""
        with self._lock:
            for entry in self._cache.values():
                self._cleanup_model(entry)
            
            self._cache.clear()
            self._update_memory_stats()
            
            logger.info("Cache de modelos limpo")
    
    def warm_up(self, model_configs: list) -> None:
        """Aquece o cache com modelos específicos."""
        for config in model_configs:
            try:
                model_size = config.get('model_size', 'base')
                device = config.get('device', 'auto')
                compute_type = config.get('compute_type', 'auto')
                
                self.get_model(model_size, device, compute_type)
                logger.info(f"Cache aquecido com modelo {model_size}")
                
            except Exception as e:
                logger.warning(f"Falha ao aquecer cache com {config}: {e}")
    
    def shutdown(self) -> None:
        """Finaliza o cache e limpa recursos."""
        self._stop_cleanup = True
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        self.clear_cache()
        logger.info("Cache de modelos finalizado")


# =============================================================================
# SINGLETON GLOBAL
# =============================================================================

_global_cache: Optional[ModelCache] = None
_cache_lock = threading.Lock()


def get_model_cache() -> ModelCache:
    """Retorna instância singleton do cache global."""
    global _global_cache
    
    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                _global_cache = ModelCache(
                    max_models=getattr(settings, 'model_cache_max_models', 3),
                    max_memory_mb=getattr(settings, 'model_cache_max_memory_mb', 8192),
                    preload_common=getattr(settings, 'model_cache_preload', True)
                )
                logger.info("Cache global de modelos inicializado")
    
    return _global_cache


def shutdown_model_cache() -> None:
    """Finaliza cache global."""
    global _global_cache
    
    if _global_cache is not None:
        _global_cache.shutdown()
        _global_cache = None


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_cached_model(
    model_size: str,
    device: str = "auto",
    compute_type: str = "auto"
) -> Tuple[WhisperModel, bool]:
    """
    Factory function para obter modelo do cache global.
    
    Args:
        model_size: Tamanho do modelo
        device: Dispositivo
        compute_type: Tipo de computação
        
    Returns:
        Tuple[WhisperModel, bool]: (modelo, foi_cache_hit)
    """
    cache = get_model_cache()
    return cache.get_model(model_size, device, compute_type)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ModelCache",
    "CacheStrategy",
    "ModelCacheEntry",
    "get_model_cache",
    "create_cached_model",
    "shutdown_model_cache"
]