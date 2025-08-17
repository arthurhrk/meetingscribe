# -*- coding: utf-8 -*-
"""
Sistema de Streaming Otimizado - MeetingScribe
Processamento de arquivos grandes com streaming inteligente e buffer adaptativos
"""

import os
import time
import threading
import queue
from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterator, Optional, Dict, Any, List, Callable, Union, Tuple
from enum import Enum
import numpy as np
from collections import deque
import psutil

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

from .file_cache import get_file_cache

class StreamingStrategy(Enum):
    """Estratégias de streaming"""
    FIXED_CHUNK = "fixed_chunk"           # Chunks de tamanho fixo
    ADAPTIVE_CHUNK = "adaptive_chunk"     # Chunks que se adaptam ao sistema
    SLIDING_WINDOW = "sliding_window"     # Janela deslizante com overlap
    MEMORY_AWARE = "memory_aware"         # Baseado na memória disponível
    INTELLIGENT = "intelligent"           # Combinação otimizada

class BufferStrategy(Enum):
    """Estratégias de buffer"""
    SINGLE_BUFFER = "single"              # Buffer único
    DOUBLE_BUFFER = "double"              # Double buffering
    RING_BUFFER = "ring"                  # Buffer circular
    ADAPTIVE_BUFFER = "adaptive"          # Buffer que se adapta

@dataclass
class StreamConfig:
    """Configuração do streaming"""
    chunk_size_seconds: float = 30.0     # Tamanho base do chunk em segundos
    overlap_seconds: float = 2.0         # Overlap entre chunks
    buffer_size_mb: int = 512            # Tamanho do buffer em MB
    max_memory_mb: int = 1024            # Memória máxima a usar
    min_chunk_size: float = 5.0          # Chunk mínimo em segundos
    max_chunk_size: float = 300.0        # Chunk máximo em segundos
    target_sr: int = 16000               # Sample rate alvo
    strategy: StreamingStrategy = StreamingStrategy.INTELLIGENT
    buffer_strategy: BufferStrategy = BufferStrategy.ADAPTIVE_BUFFER
    prefetch_chunks: int = 2             # Chunks para pré-carregar
    enable_cache: bool = True            # Usar cache para chunks
    quality_mode: bool = False           # Modo qualidade vs velocidade

@dataclass
class AudioChunk:
    """Chunk de áudio para streaming"""
    data: np.ndarray
    sample_rate: int
    start_time: float
    end_time: float
    chunk_id: int
    overlap_start: float = 0.0
    overlap_end: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StreamingStats:
    """Estatísticas de streaming"""
    total_chunks: int = 0
    processed_chunks: int = 0
    cached_chunks: int = 0
    memory_usage_mb: float = 0.0
    processing_time: float = 0.0
    io_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    adaptive_adjustments: int = 0

class AudioStreamer:
    """
    Streaming otimizado de arquivos de áudio grandes
    """
    
    def __init__(self, config: StreamConfig = None):
        self.config = config or StreamConfig()
        self.stats = StreamingStats()
        
        # Buffer management
        self._buffers: deque = deque(maxlen=self.config.prefetch_chunks + 2)
        self._buffer_lock = threading.RLock()
        self._prefetch_queue: queue.Queue = queue.Queue(maxsize=self.config.prefetch_chunks)
        
        # Threading
        self._prefetch_thread: Optional[threading.Thread] = None
        self._stop_prefetch = threading.Event()
        
        # Cache integration
        self.cache = get_file_cache() if self.config.enable_cache else None
        
        # Adaptive parameters
        self._current_chunk_size = self.config.chunk_size_seconds
        self._performance_history: deque = deque(maxlen=10)
        
        # Memory monitoring
        self._memory_threshold = self.config.max_memory_mb * 0.8  # 80% threshold
    
    def stream_file(self, 
                   file_path: Union[str, Path],
                   processor: Callable[[AudioChunk], Any] = None) -> Iterator[AudioChunk]:
        """
        Stream arquivo de áudio em chunks otimizados
        
        Args:
            file_path: Caminho do arquivo
            processor: Função opcional para processar cada chunk
            
        Yields:
            AudioChunk: Chunks de áudio otimizados
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")
        
        # Detectar estratégia baseada no arquivo
        file_size_mb = path.stat().st_size / (1024 * 1024)
        strategy = self._determine_strategy(file_size_mb)
        
        # Inicializar streaming baseado na estratégia
        if strategy == StreamingStrategy.INTELLIGENT:
            yield from self._stream_intelligent(path, processor)
        elif strategy == StreamingStrategy.ADAPTIVE_CHUNK:
            yield from self._stream_adaptive(path, processor)
        elif strategy == StreamingStrategy.SLIDING_WINDOW:
            yield from self._stream_sliding_window(path, processor)
        elif strategy == StreamingStrategy.MEMORY_AWARE:
            yield from self._stream_memory_aware(path, processor)
        else:  # FIXED_CHUNK
            yield from self._stream_fixed_chunk(path, processor)
    
    def _determine_strategy(self, file_size_mb: float) -> StreamingStrategy:
        """Determina estratégia ótima baseada no arquivo e sistema"""
        
        # Verificar memória disponível
        available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
        
        if file_size_mb > 1000:  # Arquivos enormes (>1GB)
            return StreamingStrategy.MEMORY_AWARE
        elif file_size_mb > 200:  # Arquivos grandes (>200MB)
            if available_memory_mb > 4000:  # Sistema com muita RAM
                return StreamingStrategy.ADAPTIVE_CHUNK
            else:
                return StreamingStrategy.SLIDING_WINDOW
        elif file_size_mb > 50:  # Arquivos médios (>50MB)
            return StreamingStrategy.INTELLIGENT
        else:  # Arquivos pequenos
            return StreamingStrategy.FIXED_CHUNK
    
    def _stream_intelligent(self, path: Path, processor: Callable) -> Iterator[AudioChunk]:
        """Streaming inteligente que combina múltiplas estratégias"""
        
        # Analisar arquivo primeiro
        with sf.SoundFile(str(path)) as f:
            total_frames = len(f)
            sample_rate = f.samplerate
            duration = total_frames / sample_rate
        
        # Ajustar parâmetros baseado na análise
        optimal_chunk_size = self._calculate_optimal_chunk_size(duration, sample_rate)
        
        # Iniciar prefetch se necessário
        if duration > 60:  # > 1 minuto
            self._start_prefetch_thread(path, optimal_chunk_size)
        
        try:
            chunk_id = 0
            current_time = 0.0
            
            while current_time < duration:
                # Verificar memória e ajustar se necessário
                self._monitor_and_adjust_memory()
                
                chunk_start = max(0, current_time - self.config.overlap_seconds)
                chunk_end = min(duration, current_time + optimal_chunk_size)
                
                # Tentar obter do cache primeiro
                chunk = self._get_cached_chunk(path, chunk_start, chunk_end, chunk_id)
                
                if chunk is None:
                    # Carregar chunk
                    chunk = self._load_chunk(path, chunk_start, chunk_end, chunk_id)
                    
                    # Cache se habilitado
                    if self.cache:
                        self._cache_chunk(path, chunk)
                
                # Processar se necessário
                if processor:
                    start_time = time.time()
                    result = processor(chunk)
                    processing_time = time.time() - start_time
                    
                    # Ajustar chunk size baseado na performance
                    self._adapt_chunk_size(processing_time, optimal_chunk_size)
                
                self.stats.processed_chunks += 1
                yield chunk
                
                current_time += optimal_chunk_size - self.config.overlap_seconds
                chunk_id += 1
                
        finally:
            self._stop_prefetch_thread()
    
    def _stream_adaptive(self, path: Path, processor: Callable) -> Iterator[AudioChunk]:
        """Streaming com chunks adaptativos"""
        
        with sf.SoundFile(str(path)) as f:
            total_frames = len(f)
            sample_rate = f.samplerate
            duration = total_frames / sample_rate
        
        chunk_id = 0
        current_time = 0.0
        current_chunk_size = self.config.chunk_size_seconds
        
        while current_time < duration:
            # Monitorar sistema e ajustar chunk size
            memory_usage = psutil.virtual_memory().percent
            cpu_usage = psutil.cpu_percent(interval=0.1)
            
            # Ajustar chunk size baseado no sistema
            if memory_usage > 80:
                current_chunk_size = max(self.config.min_chunk_size, current_chunk_size * 0.8)
                self.stats.adaptive_adjustments += 1
            elif memory_usage < 50 and cpu_usage < 50:
                current_chunk_size = min(self.config.max_chunk_size, current_chunk_size * 1.2)
                self.stats.adaptive_adjustments += 1
            
            chunk_start = max(0, current_time - self.config.overlap_seconds)
            chunk_end = min(duration, current_time + current_chunk_size)
            
            chunk = self._load_chunk(path, chunk_start, chunk_end, chunk_id)
            
            if processor:
                processor(chunk)
            
            yield chunk
            
            current_time += current_chunk_size - self.config.overlap_seconds
            chunk_id += 1
    
    def _stream_sliding_window(self, path: Path, processor: Callable) -> Iterator[AudioChunk]:
        """Streaming com janela deslizante otimizada"""
        
        window_size = self.config.chunk_size_seconds
        step_size = window_size - self.config.overlap_seconds
        
        with sf.SoundFile(str(path)) as f:
            sample_rate = f.samplerate
            window_frames = int(window_size * sample_rate)
            step_frames = int(step_size * sample_rate)
            
            chunk_id = 0
            current_frame = 0
            
            while current_frame < len(f):
                f.seek(current_frame)
                
                # Ler janela
                frames_to_read = min(window_frames, len(f) - current_frame)
                audio_data = f.read(frames_to_read)
                
                if len(audio_data) == 0:
                    break
                
                # Converter para mono se necessário
                if audio_data.ndim > 1:
                    audio_data = np.mean(audio_data, axis=1)
                
                start_time = current_frame / sample_rate
                end_time = (current_frame + len(audio_data)) / sample_rate
                
                chunk = AudioChunk(
                    data=audio_data.astype(np.float32),
                    sample_rate=sample_rate,
                    start_time=start_time,
                    end_time=end_time,
                    chunk_id=chunk_id,
                    overlap_start=self.config.overlap_seconds if chunk_id > 0 else 0.0,
                    overlap_end=self.config.overlap_seconds if current_frame + window_frames < len(f) else 0.0
                )
                
                if processor:
                    processor(chunk)
                
                yield chunk
                
                current_frame += step_frames
                chunk_id += 1
    
    def _stream_memory_aware(self, path: Path, processor: Callable) -> Iterator[AudioChunk]:
        """Streaming consciente da memória disponível"""
        
        with sf.SoundFile(str(path)) as f:
            sample_rate = f.samplerate
            total_frames = len(f)
        
        chunk_id = 0
        current_frame = 0
        
        while current_frame < total_frames:
            # Calcular chunk size baseado na memória disponível
            available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
            
            # Usar 10% da memória disponível para o chunk
            target_memory_mb = min(available_memory_mb * 0.1, self.config.buffer_size_mb)
            
            # Calcular frames baseado na memória alvo
            bytes_per_frame = 4  # float32
            max_frames = int(target_memory_mb * 1024 * 1024 / bytes_per_frame)
            
            frames_to_read = min(max_frames, total_frames - current_frame)
            
            with sf.SoundFile(str(path)) as f:
                f.seek(current_frame)
                audio_data = f.read(frames_to_read)
            
            if len(audio_data) == 0:
                break
            
            # Converter para mono se necessário
            if audio_data.ndim > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            start_time = current_frame / sample_rate
            end_time = (current_frame + len(audio_data)) / sample_rate
            
            chunk = AudioChunk(
                data=audio_data.astype(np.float32),
                sample_rate=sample_rate,
                start_time=start_time,
                end_time=end_time,
                chunk_id=chunk_id,
                metadata={'memory_used_mb': target_memory_mb}
            )
            
            if processor:
                processor(chunk)
            
            yield chunk
            
            current_frame += frames_to_read
            chunk_id += 1
    
    def _stream_fixed_chunk(self, path: Path, processor: Callable) -> Iterator[AudioChunk]:
        """Streaming com chunks de tamanho fixo (fallback)"""
        
        chunk_size = self.config.chunk_size_seconds
        
        with sf.SoundFile(str(path)) as f:
            sample_rate = f.samplerate
            chunk_frames = int(chunk_size * sample_rate)
            
            chunk_id = 0
            current_frame = 0
            
            while current_frame < len(f):
                f.seek(current_frame)
                audio_data = f.read(chunk_frames)
                
                if len(audio_data) == 0:
                    break
                
                # Converter para mono se necessário
                if audio_data.ndim > 1:
                    audio_data = np.mean(audio_data, axis=1)
                
                start_time = current_frame / sample_rate
                end_time = (current_frame + len(audio_data)) / sample_rate
                
                chunk = AudioChunk(
                    data=audio_data.astype(np.float32),
                    sample_rate=sample_rate,
                    start_time=start_time,
                    end_time=end_time,
                    chunk_id=chunk_id
                )
                
                if processor:
                    processor(chunk)
                
                yield chunk
                
                current_frame += len(audio_data)
                chunk_id += 1
    
    def _calculate_optimal_chunk_size(self, duration: float, sample_rate: int) -> float:
        """Calcula tamanho ótimo de chunk baseado no arquivo e sistema"""
        
        # Fatores para considerar
        base_size = self.config.chunk_size_seconds
        
        # Ajustar baseado na duração do arquivo
        if duration > 3600:  # > 1 hora
            size_factor = 1.5
        elif duration > 1800:  # > 30 min
            size_factor = 1.2
        elif duration < 300:  # < 5 min
            size_factor = 0.8
        else:
            size_factor = 1.0
        
        # Ajustar baseado na memória disponível
        available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
        if available_memory_mb > 8000:  # > 8GB
            memory_factor = 1.3
        elif available_memory_mb < 2000:  # < 2GB
            memory_factor = 0.7
        else:
            memory_factor = 1.0
        
        # Ajustar baseado no modo de qualidade
        quality_factor = 1.3 if self.config.quality_mode else 1.0
        
        optimal_size = base_size * size_factor * memory_factor * quality_factor
        
        # Aplicar limites
        return max(self.config.min_chunk_size, 
                  min(self.config.max_chunk_size, optimal_size))
    
    def _load_chunk(self, path: Path, start_time: float, end_time: float, chunk_id: int) -> AudioChunk:
        """Carrega chunk específico do arquivo"""
        
        io_start = time.time()
        
        with sf.SoundFile(str(path)) as f:
            sample_rate = f.samplerate
            
            start_frame = int(start_time * sample_rate)
            end_frame = int(end_time * sample_rate)
            frames_to_read = end_frame - start_frame
            
            f.seek(start_frame)
            audio_data = f.read(frames_to_read)
        
        self.stats.io_time += time.time() - io_start
        
        # Converter para mono se necessário
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Resample se necessário
        if self.config.target_sr and self.config.target_sr != sample_rate:
            if LIBROSA_AVAILABLE:
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=self.config.target_sr)
                sample_rate = self.config.target_sr
        
        return AudioChunk(
            data=audio_data.astype(np.float32),
            sample_rate=sample_rate,
            start_time=start_time,
            end_time=end_time,
            chunk_id=chunk_id
        )
    
    def _get_cached_chunk(self, path: Path, start_time: float, end_time: float, chunk_id: int) -> Optional[AudioChunk]:
        """Tenta obter chunk do cache"""
        
        if not self.cache:
            return None
        
        cache_key = f"{path}:{start_time}:{end_time}"
        cached_data = self.cache.get(cache_key)
        
        if cached_data is not None:
            self.stats.cache_hits += 1
            self.stats.cached_chunks += 1
            return cached_data
        else:
            self.stats.cache_misses += 1
            return None
    
    def _cache_chunk(self, path: Path, chunk: AudioChunk):
        """Cache chunk para uso futuro"""
        
        if not self.cache:
            return
        
        cache_key = f"{path}:{chunk.start_time}:{chunk.end_time}"
        self.cache.put(cache_key, chunk, "audio_chunk")
    
    def _adapt_chunk_size(self, processing_time: float, current_size: float):
        """Adapta tamanho do chunk baseado na performance"""
        
        self._performance_history.append(processing_time)
        
        if len(self._performance_history) >= 3:
            avg_time = sum(self._performance_history) / len(self._performance_history)
            
            # Se processamento está lento, diminuir chunk
            if avg_time > current_size * 0.5:  # Mais que 50% do tempo do chunk
                self._current_chunk_size = max(self.config.min_chunk_size, 
                                             self._current_chunk_size * 0.8)
                self.stats.adaptive_adjustments += 1
            
            # Se processamento está rápido, aumentar chunk
            elif avg_time < current_size * 0.1:  # Menos que 10% do tempo do chunk
                self._current_chunk_size = min(self.config.max_chunk_size,
                                             self._current_chunk_size * 1.2)
                self.stats.adaptive_adjustments += 1
    
    def _monitor_and_adjust_memory(self):
        """Monitora uso de memória e ajusta se necessário"""
        
        memory_percent = psutil.virtual_memory().percent
        
        if memory_percent > 85:  # Memória crítica
            # Limpar cache de chunks se necessário
            if self.cache:
                self.cache.optimize()
            
            # Reduzir tamanho do chunk
            self._current_chunk_size = max(self.config.min_chunk_size,
                                         self._current_chunk_size * 0.7)
            self.stats.adaptive_adjustments += 1
    
    def _start_prefetch_thread(self, path: Path, chunk_size: float):
        """Inicia thread de prefetch para chunks futuros"""
        
        if self._prefetch_thread and self._prefetch_thread.is_alive():
            return
        
        self._stop_prefetch.clear()
        self._prefetch_thread = threading.Thread(
            target=self._prefetch_worker,
            args=(path, chunk_size),
            daemon=True
        )
        self._prefetch_thread.start()
    
    def _prefetch_worker(self, path: Path, chunk_size: float):
        """Worker thread para prefetch de chunks"""
        
        # Implementação simplificada do prefetch
        # Em produção, seria mais sofisticado
        pass
    
    def _stop_prefetch_thread(self):
        """Para thread de prefetch"""
        
        self._stop_prefetch.set()
        if self._prefetch_thread and self._prefetch_thread.is_alive():
            self._prefetch_thread.join(timeout=1.0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de streaming"""
        
        return {
            'total_chunks': self.stats.total_chunks,
            'processed_chunks': self.stats.processed_chunks,
            'cached_chunks': self.stats.cached_chunks,
            'memory_usage_mb': self.stats.memory_usage_mb,
            'processing_time': self.stats.processing_time,
            'io_time': self.stats.io_time,
            'cache_hit_rate': (self.stats.cache_hits / max(1, self.stats.cache_hits + self.stats.cache_misses)) * 100,
            'adaptive_adjustments': self.stats.adaptive_adjustments,
            'current_chunk_size': self._current_chunk_size,
            'config': {
                'strategy': self.config.strategy.value,
                'buffer_strategy': self.config.buffer_strategy.value,
                'chunk_size_seconds': self.config.chunk_size_seconds,
                'max_memory_mb': self.config.max_memory_mb
            }
        }


# Factory functions
def create_audio_streamer(config: StreamConfig = None) -> AudioStreamer:
    """Cria instância do streaming de áudio"""
    return AudioStreamer(config)

def stream_large_audio_file(file_path: Union[str, Path], 
                           processor: Callable[[AudioChunk], Any] = None,
                           config: StreamConfig = None) -> Iterator[AudioChunk]:
    """
    Função convenience para streaming de arquivo grande
    
    Args:
        file_path: Caminho do arquivo
        processor: Função para processar cada chunk
        config: Configuração personalizada
        
    Yields:
        AudioChunk: Chunks otimizados
    """
    streamer = create_audio_streamer(config)
    yield from streamer.stream_file(file_path, processor)

# Context manager para streaming
class streaming_audio:
    """Context manager para streaming de áudio"""
    
    def __init__(self, file_path: Union[str, Path], config: StreamConfig = None):
        self.file_path = file_path
        self.config = config
        self.streamer = None
    
    def __enter__(self) -> AudioStreamer:
        self.streamer = create_audio_streamer(self.config)
        return self.streamer
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.streamer:
            self.streamer._stop_prefetch_thread()