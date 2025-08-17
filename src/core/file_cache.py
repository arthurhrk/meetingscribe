# -*- coding: utf-8 -*-
"""
Sistema de Cache de Arquivos - MeetingScribe
Cache inteligente para otimização de I/O de arquivos de áudio e dados
"""

import os
import time
import threading
import hashlib
import pickle
import gzip
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union, Callable
from collections import OrderedDict
import weakref
from enum import Enum
import psutil

@dataclass
class CacheEntry:
    """Entrada do cache de arquivo"""
    key: str
    file_path: Path
    content: Any
    content_type: str  # 'audio_data', 'metadata', 'transcription', 'raw_bytes'
    size_bytes: int
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    compression_ratio: float = 1.0
    checksum: str = ""
    
    def update_access(self):
        """Atualiza informações de acesso"""
        self.last_accessed = datetime.now()
        self.access_count += 1

class CacheStrategy(Enum):
    """Estratégias de cache"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    SIZE_BASED = "size_based"  # Baseado no tamanho
    INTELLIGENT = "intelligent"  # Combinação inteligente

class CompressionLevel(Enum):
    """Níveis de compressão"""
    NONE = 0
    FAST = 1
    BALANCED = 6
    MAXIMUM = 9

@dataclass
class FileCacheConfig:
    """Configuração do cache de arquivos"""
    max_memory_mb: int = 1024  # 1GB padrão
    max_entries: int = 1000
    ttl_hours: int = 24
    strategy: CacheStrategy = CacheStrategy.INTELLIGENT
    compression_level: CompressionLevel = CompressionLevel.BALANCED
    compress_threshold_mb: float = 5.0
    auto_cleanup_interval: int = 300  # 5 minutos
    persist_cache: bool = True
    cache_dir: str = "storage/cache"
    preload_patterns: List[str] = field(default_factory=lambda: ["*.wav", "*.mp3", "*.m4a"])

class FileCache:
    """
    Cache inteligente de arquivos com compressão e persistência
    """
    
    def __init__(self, config: FileCacheConfig = None):
        self.config = config or FileCacheConfig()
        
        # Thread-safe storage
        self._lock = threading.RLock()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._memory_usage = 0
        
        # Cache directory
        self.cache_dir = Path(self.config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'compressions': 0,
            'decompressions': 0,
            'disk_reads': 0,
            'disk_writes': 0
        }
        
        # Background cleanup
        self._cleanup_timer: Optional[threading.Timer] = None
        self._shutdown = False
        
        # Weak references para auto-cleanup
        self._weak_refs: Dict[str, weakref.ref] = {}
        
        # Pre-load patterns
        self._file_watchers: Dict[str, Any] = {}
        
        self._start_background_tasks()
        self._load_persistent_cache()
    
    def _generate_cache_key(self, file_path: Union[str, Path]) -> str:
        """Gera chave única para o arquivo"""
        path = Path(file_path)
        
        # Incluir path, size e modification time para detectar mudanças
        try:
            stat = path.stat()
            key_data = f"{path.absolute()}:{stat.st_size}:{stat.st_mtime}"
            return hashlib.md5(key_data.encode()).hexdigest()
        except (OSError, FileNotFoundError):
            # Fallback para path apenas
            return hashlib.md5(str(path.absolute()).encode()).hexdigest()
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calcula checksum dos dados"""
        return hashlib.sha256(data[:1024]).hexdigest()  # Primeiros 1KB para performance
    
    def _compress_data(self, data: Any, content_type: str) -> tuple[bytes, float]:
        """Comprime dados se necessário"""
        try:
            # Serializar dados
            if isinstance(data, bytes):
                raw_data = data
            else:
                raw_data = pickle.dumps(data)
            
            original_size = len(raw_data)
            
            # Aplicar compressão se o arquivo for grande o suficiente
            if original_size > (self.config.compress_threshold_mb * 1024 * 1024):
                compressed_data = gzip.compress(raw_data, compresslevel=self.config.compression_level.value)
                compression_ratio = len(compressed_data) / original_size
                self._stats['compressions'] += 1
                return compressed_data, compression_ratio
            else:
                return raw_data, 1.0
                
        except Exception as e:
            print(f"Error compressing data: {e}")
            return pickle.dumps(data) if not isinstance(data, bytes) else data, 1.0
    
    def _decompress_data(self, compressed_data: bytes, compression_ratio: float, content_type: str) -> Any:
        """Descomprime dados"""
        try:
            # Se foi comprimido, descomprimir
            if compression_ratio < 1.0:
                raw_data = gzip.decompress(compressed_data)
                self._stats['decompressions'] += 1
            else:
                raw_data = compressed_data
            
            # Deserializar se não for bytes puro
            if content_type == 'raw_bytes':
                return raw_data
            else:
                return pickle.loads(raw_data)
                
        except Exception as e:
            print(f"Error decompressing data: {e}")
            # Tentar retornar dados brutos
            try:
                return pickle.loads(compressed_data)
            except:
                return compressed_data
    
    def put(self, 
            file_path: Union[str, Path], 
            content: Any, 
            content_type: str = 'raw_bytes',
            force: bool = False) -> bool:
        """
        Adiciona arquivo ao cache
        
        Args:
            file_path: Caminho do arquivo
            content: Conteúdo a ser cacheado
            content_type: Tipo do conteúdo ('audio_data', 'metadata', 'transcription', 'raw_bytes')
            force: Forçar cache mesmo se existir
            
        Returns:
            bool: True se foi cacheado com sucesso
        """
        try:
            path = Path(file_path)
            cache_key = self._generate_cache_key(path)
            
            with self._lock:
                # Verificar se já existe (a menos que force=True)
                if not force and cache_key in self._cache:
                    return True
                
                # Comprimir dados
                compressed_data, compression_ratio = self._compress_data(content, content_type)
                size_bytes = len(compressed_data)
                
                # Verificar se cabe na memória
                if not self._ensure_space(size_bytes):
                    return False
                
                # Calcular checksum
                checksum = self._calculate_checksum(compressed_data)
                
                # Criar entrada
                entry = CacheEntry(
                    key=cache_key,
                    file_path=path,
                    content=compressed_data,
                    content_type=content_type,
                    size_bytes=size_bytes,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    compression_ratio=compression_ratio,
                    checksum=checksum
                )
                
                # Adicionar ao cache
                self._cache[cache_key] = entry
                self._memory_usage += size_bytes
                
                # Persistir se configurado
                if self.config.persist_cache:
                    self._persist_entry(entry)
                
                return True
                
        except Exception as e:
            print(f"Error caching file {file_path}: {e}")
            return False
    
    def get(self, file_path: Union[str, Path]) -> Optional[Any]:
        """
        Obtém arquivo do cache
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Conteúdo do arquivo ou None se não estiver no cache
        """
        try:
            path = Path(file_path)
            cache_key = self._generate_cache_key(path)
            
            with self._lock:
                if cache_key in self._cache:
                    entry = self._cache[cache_key]
                    
                    # Verificar se não expirou (TTL)
                    if self._is_expired(entry):
                        self._remove_entry(cache_key)
                        self._stats['misses'] += 1
                        return None
                    
                    # Atualizar acesso
                    entry.update_access()
                    
                    # Mover para o final (LRU)
                    self._cache.move_to_end(cache_key)
                    
                    # Descomprimir e retornar
                    content = self._decompress_data(
                        entry.content, 
                        entry.compression_ratio, 
                        entry.content_type
                    )
                    
                    self._stats['hits'] += 1
                    return content
                else:
                    self._stats['misses'] += 1
                    return None
                    
        except Exception as e:
            print(f"Error getting cached file {file_path}: {e}")
            self._stats['misses'] += 1
            return None
    
    def get_or_load(self, 
                    file_path: Union[str, Path], 
                    loader: Callable[[Path], Any],
                    content_type: str = 'raw_bytes') -> Any:
        """
        Obtém do cache ou carrega do disco
        
        Args:
            file_path: Caminho do arquivo
            loader: Função para carregar o arquivo do disco
            content_type: Tipo do conteúdo
            
        Returns:
            Conteúdo do arquivo
        """
        # Tentar obter do cache primeiro
        cached_content = self.get(file_path)
        if cached_content is not None:
            return cached_content
        
        # Carregar do disco
        try:
            path = Path(file_path)
            content = loader(path)
            
            # Adicionar ao cache
            self.put(file_path, content, content_type)
            self._stats['disk_reads'] += 1
            
            return content
            
        except Exception as e:
            print(f"Error loading file {file_path}: {e}")
            raise
    
    def remove(self, file_path: Union[str, Path]) -> bool:
        """Remove arquivo do cache"""
        try:
            cache_key = self._generate_cache_key(file_path)
            
            with self._lock:
                if cache_key in self._cache:
                    self._remove_entry(cache_key)
                    return True
                return False
                
        except Exception as e:
            print(f"Error removing cached file {file_path}: {e}")
            return False
    
    def clear(self):
        """Limpa todo o cache"""
        with self._lock:
            self._cache.clear()
            self._memory_usage = 0
            self._weak_refs.clear()
            
        # Limpar cache persistente
        if self.config.persist_cache:
            try:
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
            except Exception as e:
                print(f"Error clearing persistent cache: {e}")
    
    def _ensure_space(self, required_bytes: int) -> bool:
        """Garante espaço suficiente no cache"""
        # Verificar limite de memória
        max_memory_bytes = self.config.max_memory_mb * 1024 * 1024
        
        while (self._memory_usage + required_bytes > max_memory_bytes or 
               len(self._cache) >= self.config.max_entries):
            
            if not self._cache:
                return False
            
            # Aplicar estratégia de eviction
            evicted = self._evict_entry()
            if not evicted:
                return False
        
        return True
    
    def _evict_entry(self) -> bool:
        """Remove entrada baseado na estratégia configurada"""
        if not self._cache:
            return False
        
        strategy = self.config.strategy
        
        if strategy == CacheStrategy.LRU:
            # Remove o menos recentemente usado (primeiro da OrderedDict)
            key_to_remove = next(iter(self._cache))
        elif strategy == CacheStrategy.LFU:
            # Remove o menos frequentemente usado
            key_to_remove = min(self._cache.keys(), 
                               key=lambda k: self._cache[k].access_count)
        elif strategy == CacheStrategy.TTL:
            # Remove o mais antigo
            key_to_remove = min(self._cache.keys(), 
                               key=lambda k: self._cache[k].created_at)
        elif strategy == CacheStrategy.SIZE_BASED:
            # Remove o maior arquivo
            key_to_remove = max(self._cache.keys(), 
                               key=lambda k: self._cache[k].size_bytes)
        else:  # INTELLIGENT
            # Estratégia inteligente: combina idade, frequência e tamanho
            key_to_remove = self._intelligent_eviction()
        
        self._remove_entry(key_to_remove)
        self._stats['evictions'] += 1
        return True
    
    def _intelligent_eviction(self) -> str:
        """Estratégia inteligente de eviction"""
        now = datetime.now()
        scores = {}
        
        for key, entry in self._cache.items():
            # Fatores de score (menor score = maior prioridade para remoção)
            age_hours = (now - entry.last_accessed).total_seconds() / 3600
            access_frequency = entry.access_count / max(age_hours, 0.1)
            size_factor = entry.size_bytes / (1024 * 1024)  # MB
            
            # Score combinado (quanto menor, maior prioridade para remoção)
            score = access_frequency / (age_hours + 1) / (size_factor + 1)
            scores[key] = score
        
        # Retornar chave com menor score
        return min(scores.keys(), key=lambda k: scores[k])
    
    def _remove_entry(self, cache_key: str):
        """Remove entrada específica do cache"""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            self._memory_usage -= entry.size_bytes
            del self._cache[cache_key]
            
            # Remover weak reference
            if cache_key in self._weak_refs:
                del self._weak_refs[cache_key]
            
            # Remover cache persistente
            if self.config.persist_cache:
                cache_file = self.cache_dir / f"{cache_key}.cache"
                if cache_file.exists():
                    try:
                        cache_file.unlink()
                    except Exception as e:
                        print(f"Error removing persistent cache file: {e}")
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Verifica se entrada expirou"""
        if self.config.ttl_hours <= 0:
            return False
        
        ttl = timedelta(hours=self.config.ttl_hours)
        return datetime.now() - entry.created_at > ttl
    
    def _persist_entry(self, entry: CacheEntry):
        """Persiste entrada em disco"""
        try:
            cache_file = self.cache_dir / f"{entry.key}.cache"
            
            # Dados para persistir (sem o conteúdo comprimido para economizar espaço)
            persist_data = {
                'key': entry.key,
                'file_path': str(entry.file_path),
                'content_type': entry.content_type,
                'size_bytes': entry.size_bytes,
                'created_at': entry.created_at.isoformat(),
                'last_accessed': entry.last_accessed.isoformat(),
                'access_count': entry.access_count,
                'compression_ratio': entry.compression_ratio,
                'checksum': entry.checksum,
                'content': entry.content  # Incluir conteúdo comprimido
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(persist_data, f)
                
            self._stats['disk_writes'] += 1
            
        except Exception as e:
            print(f"Error persisting cache entry: {e}")
    
    def _load_persistent_cache(self):
        """Carrega cache persistente na inicialização"""
        if not self.config.persist_cache:
            return
        
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)
                    
                    # Recriar entrada
                    entry = CacheEntry(
                        key=data['key'],
                        file_path=Path(data['file_path']),
                        content=data['content'],
                        content_type=data['content_type'],
                        size_bytes=data['size_bytes'],
                        created_at=datetime.fromisoformat(data['created_at']),
                        last_accessed=datetime.fromisoformat(data['last_accessed']),
                        access_count=data['access_count'],
                        compression_ratio=data['compression_ratio'],
                        checksum=data['checksum']
                    )
                    
                    # Verificar se arquivo ainda existe e não mudou
                    if (entry.file_path.exists() and 
                        self._generate_cache_key(entry.file_path) == entry.key):
                        
                        # Verificar se não expirou
                        if not self._is_expired(entry):
                            self._cache[entry.key] = entry
                            self._memory_usage += entry.size_bytes
                        else:
                            # Remover arquivo expirado
                            cache_file.unlink()
                    else:
                        # Arquivo mudou ou não existe mais
                        cache_file.unlink()
                        
                except Exception as e:
                    print(f"Error loading cache file {cache_file}: {e}")
                    # Remover arquivo corrompido
                    try:
                        cache_file.unlink()
                    except:
                        pass
                        
        except Exception as e:
            print(f"Error loading persistent cache: {e}")
    
    def _start_background_tasks(self):
        """Inicia tarefas de background"""
        self._schedule_cleanup()
    
    def _schedule_cleanup(self):
        """Agenda próxima limpeza automática"""
        if self._shutdown:
            return
        
        self._cleanup_timer = threading.Timer(
            self.config.auto_cleanup_interval,
            self._background_cleanup
        )
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()
    
    def _background_cleanup(self):
        """Limpeza automática em background"""
        try:
            with self._lock:
                # Remover entradas expiradas
                expired_keys = [
                    key for key, entry in self._cache.items()
                    if self._is_expired(entry)
                ]
                
                for key in expired_keys:
                    self._remove_entry(key)
                
                # Verificar weak references
                dead_refs = [
                    key for key, ref in self._weak_refs.items()
                    if ref() is None
                ]
                
                for key in dead_refs:
                    if key in self._cache:
                        self._remove_entry(key)
            
            # Agendar próxima limpeza
            self._schedule_cleanup()
            
        except Exception as e:
            print(f"Error in background cleanup: {e}")
            self._schedule_cleanup()
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'entries_count': len(self._cache),
                'memory_usage_mb': self._memory_usage / (1024 * 1024),
                'memory_limit_mb': self.config.max_memory_mb,
                'memory_usage_percent': (self._memory_usage / (self.config.max_memory_mb * 1024 * 1024)) * 100,
                'hit_rate_percent': hit_rate,
                'total_hits': self._stats['hits'],
                'total_misses': self._stats['misses'],
                'total_evictions': self._stats['evictions'],
                'total_compressions': self._stats['compressions'],
                'total_decompressions': self._stats['decompressions'],
                'total_disk_reads': self._stats['disk_reads'],
                'total_disk_writes': self._stats['disk_writes'],
                'config': {
                    'strategy': self.config.strategy.value,
                    'compression_level': self.config.compression_level.value,
                    'ttl_hours': self.config.ttl_hours,
                    'max_entries': self.config.max_entries
                }
            }
    
    def optimize(self):
        """Otimiza o cache manualmente"""
        with self._lock:
            # Remover entradas expiradas
            expired_keys = [
                key for key, entry in self._cache.items()
                if self._is_expired(entry)
            ]
            
            for key in expired_keys:
                self._remove_entry(key)
            
            # Forçar garbage collection
            import gc
            gc.collect()
    
    def shutdown(self):
        """Finaliza o cache e persiste dados"""
        self._shutdown = True
        
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
        
        # Persistir cache atual
        if self.config.persist_cache:
            with self._lock:
                for entry in self._cache.values():
                    self._persist_entry(entry)


# Singleton global
_file_cache: Optional[FileCache] = None

def get_file_cache(config: FileCacheConfig = None) -> FileCache:
    """Obtém instância singleton do cache de arquivos"""
    global _file_cache
    
    if _file_cache is None:
        _file_cache = FileCache(config)
    
    return _file_cache

def shutdown_file_cache():
    """Finaliza o cache de arquivos"""
    global _file_cache
    
    if _file_cache is not None:
        _file_cache.shutdown()
        _file_cache = None

# Context manager para cache temporário
class cached_file:
    """Context manager para cache temporário de arquivo"""
    
    def __init__(self, 
                 file_path: Union[str, Path], 
                 loader: Callable[[Path], Any],
                 content_type: str = 'raw_bytes'):
        self.file_path = file_path
        self.loader = loader
        self.content_type = content_type
        self.cache = get_file_cache()
    
    def __enter__(self):
        return self.cache.get_or_load(self.file_path, self.loader, self.content_type)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Não remove automaticamente, deixa para o cache gerenciar
        pass

# Decorador para cache de função
def file_cached(content_type: str = 'raw_bytes'):
    """Decorator para cache automático de funções que carregam arquivos"""
    def decorator(func):
        def wrapper(file_path, *args, **kwargs):
            cache = get_file_cache()
            
            def loader(path):
                return func(path, *args, **kwargs)
            
            return cache.get_or_load(file_path, loader, content_type)
        
        return wrapper
    return decorator