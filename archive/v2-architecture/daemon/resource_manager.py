"""
Resource Manager for Model Persistence

FR-001 compliant resource management with intelligent model caching,
memory optimization, and Whisper model persistence.
"""

import gc
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Any, Set
import weakref

from loguru import logger

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not available, memory monitoring limited")

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False
    logger.warning("faster-whisper not available, model caching disabled")


class ModelResource:
    """Wrapper for cached model with usage tracking."""
    
    def __init__(self, model: Any, model_size: str, device: str):
        self.model = model
        self.model_size = model_size
        self.device = device
        self.created_at = time.time()
        self.last_used = time.time()
        self.usage_count = 0
        self.memory_mb = self._estimate_memory_usage()
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage based on model size."""
        # Rough estimates based on Whisper model sizes
        size_estimates = {
            'tiny': 100,     # ~100MB
            'base': 200,     # ~200MB  
            'small': 400,    # ~400MB
            'medium': 800,   # ~800MB
            'large': 1600,   # ~1600MB
            'large-v2': 1600,
            'large-v3': 1600,
        }
        return size_estimates.get(self.model_size, 500)
    
    def mark_used(self):
        """Mark model as recently used."""
        self.last_used = time.time()
        self.usage_count += 1
    
    def age_seconds(self) -> float:
        """Get age since last use in seconds."""
        return time.time() - self.last_used


class ResourceManager:
    """
    Model caching and resource management for FR-001 compliance.
    
    Features:
    - Intelligent model caching with LRU eviction
    - Memory pressure monitoring and cleanup
    - Pre-loading of base model for fast startup
    - Automatic garbage collection optimization
    """
    
    def __init__(self, max_memory_mb: float = 2000, cache_ttl: float = 300):
        """
        Initialize resource manager.
        
        Args:
            max_memory_mb: Maximum memory to use for cached models
            cache_ttl: Time-to-live for unused models in seconds
        """
        self.max_memory_mb = max_memory_mb
        self.cache_ttl = cache_ttl
        self.cached_models: Dict[str, ModelResource] = {}
        self.lock = threading.RLock()
        self.cleanup_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Model references for cleanup tracking
        self._model_refs: Set[weakref.ReferenceType] = set()
        
        logger.info(f"Resource manager initialized (max_memory: {max_memory_mb}MB, ttl: {cache_ttl}s)")
    
    def start(self) -> None:
        """Start resource manager background tasks."""
        with self.lock:
            if self.running:
                return
                
            self.running = True
            
            # Start cleanup thread
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                name="ResourceManager-Cleanup",
                daemon=True
            )
            self.cleanup_thread.start()
            
            logger.info("Resource manager started")
    
    def stop(self) -> None:
        """Stop resource manager and cleanup resources."""
        with self.lock:
            self.running = False
            
            # Clear all cached models
            self._clear_all_models()
            
            # Cleanup thread will exit on its own
            
            logger.info("Resource manager stopped")
    
    async def get_model(self, model_size: str, device: str = "auto") -> Optional[Any]:
        """
        Get or load a Whisper model with caching.
        
        Args:
            model_size: Whisper model size (tiny, base, small, etc.)
            device: Device to load model on (auto, cpu, cuda)
            
        Returns:
            WhisperModel instance or None if loading failed
        """
        if not HAS_WHISPER:
            logger.error("faster-whisper not available, cannot load models")
            return None
            
        cache_key = f"{model_size}_{device}"
        
        with self.lock:
            # Check if model is already cached
            if cache_key in self.cached_models:
                resource = self.cached_models[cache_key]
                resource.mark_used()
                logger.debug(f"Using cached model: {cache_key}")
                return resource.model
            
            # Check memory pressure before loading
            if not self._can_load_model(model_size):
                logger.warning(f"Cannot load {model_size} model due to memory pressure")
                # Try to free some memory
                self._evict_lru_models(aggressive=True)
                
                # Check again after cleanup
                if not self._can_load_model(model_size):
                    logger.error(f"Still cannot load {model_size} model after cleanup")
                    return None
            
            # Load new model
            logger.info(f"Loading new model: {cache_key}")
            try:
                model = self._load_whisper_model(model_size, device)
                if model is None:
                    return None
                
                # Cache the model
                resource = ModelResource(model, model_size, device)
                self.cached_models[cache_key] = resource
                
                # Add weak reference for cleanup tracking
                model_ref = weakref.ref(model, self._on_model_deleted)
                self._model_refs.add(model_ref)
                
                logger.info(f"Model cached: {cache_key} ({resource.memory_mb}MB)")
                return model
                
            except Exception as e:
                logger.error(f"Failed to load model {cache_key}: {e}")
                return None
    
    def _load_whisper_model(self, model_size: str, device: str) -> Optional[Any]:
        """Load Whisper model from disk or download."""
        try:
            # Use CPU for tiny/base models, GPU for larger ones if available
            if device == "auto":
                if model_size in ["tiny", "base"]:
                    device = "cpu"
                else:
                    try:
                        import torch
                        device = "cuda" if torch.cuda.is_available() else "cpu"
                    except ImportError:
                        device = "cpu"
            
            model = WhisperModel(
                model_size,
                device=device,
                compute_type="float16" if device == "cuda" else "int8",
                download_root=str(Path("models").absolute())
            )
            
            return model
            
        except Exception as e:
            logger.error(f"Whisper model loading failed: {e}")
            return None
    
    def _can_load_model(self, model_size: str) -> bool:
        """Check if we can load a model without exceeding memory limits."""
        estimated_usage = ModelResource(None, model_size, "cpu")._estimate_memory_usage()
        current_usage = self.get_total_cached_memory()
        
        return (current_usage + estimated_usage) <= self.max_memory_mb
    
    def get_total_cached_memory(self) -> float:
        """Get total estimated memory usage of cached models."""
        with self.lock:
            return sum(resource.memory_mb for resource in self.cached_models.values())
    
    def _evict_lru_models(self, aggressive: bool = False) -> None:
        """Evict least recently used models to free memory."""
        if not self.cached_models:
            return
            
        # Sort by last used time (oldest first)
        models_by_age = sorted(
            self.cached_models.items(),
            key=lambda x: x[1].last_used
        )
        
        freed_memory = 0
        evicted_count = 0
        target_memory = self.max_memory_mb * 0.7 if aggressive else self.max_memory_mb * 0.9
        
        for cache_key, resource in models_by_age:
            current_usage = self.get_total_cached_memory()
            
            if current_usage <= target_memory and not aggressive:
                break
                
            # Evict this model
            logger.info(f"Evicting cached model: {cache_key} (age: {resource.age_seconds():.1f}s)")
            del self.cached_models[cache_key]
            freed_memory += resource.memory_mb
            evicted_count += 1
            
            # Force garbage collection to actually free memory
            del resource
            gc.collect()
        
        if evicted_count > 0:
            logger.info(f"Evicted {evicted_count} models, freed ~{freed_memory:.1f}MB")
    
    def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while self.running:
            try:
                with self.lock:
                    # Remove expired models
                    expired_keys = []
                    current_time = time.time()
                    
                    for cache_key, resource in self.cached_models.items():
                        if current_time - resource.last_used > self.cache_ttl:
                            expired_keys.append(cache_key)
                    
                    for key in expired_keys:
                        logger.debug(f"Removing expired model: {key}")
                        del self.cached_models[key]
                    
                    # Check memory pressure
                    current_usage = self.get_total_cached_memory()
                    if current_usage > self.max_memory_mb * 0.8:
                        logger.debug("Memory pressure detected, evicting LRU models")
                        self._evict_lru_models()
                    
                    # Clean up dead weak references
                    dead_refs = [ref for ref in self._model_refs if ref() is None]
                    for ref in dead_refs:
                        self._model_refs.discard(ref)
                
                # Sleep for cleanup interval
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _clear_all_models(self) -> None:
        """Clear all cached models."""
        logger.info("Clearing all cached models")
        self.cached_models.clear()
        
        # Force garbage collection
        gc.collect()
    
    def _on_model_deleted(self, model_ref: weakref.ReferenceType) -> None:
        """Callback when a model is garbage collected."""
        self._model_refs.discard(model_ref)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            stats = {
                "cached_models": len(self.cached_models),
                "total_memory_mb": self.get_total_cached_memory(),
                "max_memory_mb": self.max_memory_mb,
                "memory_utilization": self.get_total_cached_memory() / self.max_memory_mb,
                "models": {}
            }
            
            for cache_key, resource in self.cached_models.items():
                stats["models"][cache_key] = {
                    "size": resource.model_size,
                    "device": resource.device,
                    "memory_mb": resource.memory_mb,
                    "usage_count": resource.usage_count,
                    "age_seconds": resource.age_seconds(),
                    "created_at": resource.created_at
                }
            
            return stats
    
    def preload_base_model(self) -> bool:
        """
        Preload base model for fast startup (FR-001 requirement).
        
        Returns:
            True if model was successfully preloaded
        """
        logger.info("Preloading base model for fast startup")
        
        try:
            # Load base model asynchronously
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            model = loop.run_until_complete(self.get_model("base", "auto"))
            loop.close()
            
            if model is not None:
                logger.info("✅ Base model preloaded successfully")
                return True
            else:
                logger.warning("❌ Base model preloading failed")
                return False
                
        except Exception as e:
            logger.error(f"Base model preloading error: {e}")
            return False


# Global resource manager instance
_resource_manager: Optional[ResourceManager] = None
_manager_lock = threading.Lock()


def get_resource_manager() -> ResourceManager:
    """Get global resource manager instance."""
    global _resource_manager
    
    with _manager_lock:
        if _resource_manager is None:
            _resource_manager = ResourceManager()
            _resource_manager.start()
        
        return _resource_manager


def cleanup_resource_manager() -> None:
    """Cleanup global resource manager."""
    global _resource_manager
    
    with _manager_lock:
        if _resource_manager is not None:
            _resource_manager.stop()
            _resource_manager = None