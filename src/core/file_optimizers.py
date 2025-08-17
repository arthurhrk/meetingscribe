# -*- coding: utf-8 -*-
"""
Otimizadores Específicos de Arquivos - MeetingScribe
Carregadores otimizados para diferentes tipos de arquivos de áudio e dados
"""

import os
import time
from pathlib import Path
from typing import Union, Dict, Any, Optional, Tuple, List
import numpy as np
from dataclasses import dataclass

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

from .file_cache import get_file_cache, file_cached, CacheStrategy, FileCacheConfig

@dataclass
class AudioMetadata:
    """Metadados de arquivo de áudio"""
    sample_rate: int
    channels: int
    duration: float
    format: str
    bitrate: Optional[int] = None
    file_size: int = 0
    codec: Optional[str] = None

class OptimizedAudioLoader:
    """
    Carregador otimizado de arquivos de áudio com cache inteligente
    """
    
    def __init__(self, cache_config: FileCacheConfig = None):
        self.cache = get_file_cache(cache_config)
        
        # Preferências de bibliotecas por formato
        self.format_preferences = {
            '.wav': ['soundfile', 'librosa', 'pydub'],
            '.mp3': ['pydub', 'librosa'],
            '.m4a': ['pydub', 'librosa'],
            '.flac': ['soundfile', 'librosa', 'pydub'],
            '.ogg': ['librosa', 'pydub'],
            '.aac': ['pydub', 'librosa']
        }
    
    @file_cached('audio_metadata')
    def load_metadata(self, file_path: Union[str, Path]) -> AudioMetadata:
        """
        Carrega metadados do arquivo de áudio (com cache)
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")
        
        file_size = path.stat().st_size
        format_ext = path.suffix.lower()
        
        # Tentar diferentes bibliotecas baseado na preferência
        libraries = self.format_preferences.get(format_ext, ['librosa', 'soundfile', 'pydub'])
        
        for lib in libraries:
            try:
                if lib == 'soundfile' and SOUNDFILE_AVAILABLE:
                    return self._load_metadata_soundfile(path, file_size)
                elif lib == 'librosa' and LIBROSA_AVAILABLE:
                    return self._load_metadata_librosa(path, file_size)
                elif lib == 'pydub' and PYDUB_AVAILABLE:
                    return self._load_metadata_pydub(path, file_size)
            except Exception as e:
                print(f"Failed to load metadata with {lib}: {e}")
                continue
        
        # Fallback básico
        return AudioMetadata(
            sample_rate=44100,  # Assumir padrão
            channels=2,
            duration=0.0,
            format=format_ext,
            file_size=file_size
        )
    
    def _load_metadata_soundfile(self, path: Path, file_size: int) -> AudioMetadata:
        """Carrega metadados usando soundfile"""
        info = sf.info(str(path))
        
        return AudioMetadata(
            sample_rate=info.samplerate,
            channels=info.channels,
            duration=info.duration,
            format=info.format,
            file_size=file_size,
            codec=info.subtype
        )
    
    def _load_metadata_librosa(self, path: Path, file_size: int) -> AudioMetadata:
        """Carrega metadados usando librosa"""
        # Usar librosa.get_duration é mais rápido que carregar o áudio completo
        duration = librosa.get_duration(path=str(path))
        
        # Para sample rate, precisamos carregar uma pequena amostra
        y, sr = librosa.load(str(path), duration=0.1)  # Apenas 0.1s
        channels = 1 if y.ndim == 1 else y.shape[0]
        
        return AudioMetadata(
            sample_rate=sr,
            channels=channels,
            duration=duration,
            format=path.suffix.lower(),
            file_size=file_size
        )
    
    def _load_metadata_pydub(self, path: Path, file_size: int) -> AudioMetadata:
        """Carrega metadados usando pydub"""
        audio = AudioSegment.from_file(str(path))
        
        return AudioMetadata(
            sample_rate=audio.frame_rate,
            channels=audio.channels,
            duration=len(audio) / 1000.0,  # pydub usa milliseconds
            format=path.suffix.lower(),
            file_size=file_size,
            bitrate=audio.frame_rate * audio.frame_width * 8 * audio.channels
        )
    
    @file_cached('audio_data')
    def load_audio_data(self, 
                        file_path: Union[str, Path], 
                        target_sr: Optional[int] = None,
                        mono: bool = True,
                        offset: float = 0.0,
                        duration: Optional[float] = None) -> Tuple[np.ndarray, int]:
        """
        Carrega dados de áudio otimizado (com cache)
        
        Args:
            file_path: Caminho do arquivo
            target_sr: Sample rate alvo (None para manter original)
            mono: Converter para mono
            offset: Offset em segundos
            duration: Duração em segundos (None para arquivo completo)
            
        Returns:
            Tuple[audio_data, sample_rate]
        """
        path = Path(file_path)
        format_ext = path.suffix.lower()
        
        # Estratégia baseada no tamanho do arquivo
        file_size_mb = path.stat().st_size / (1024 * 1024)
        
        if file_size_mb > 100:  # Arquivos muito grandes (>100MB)
            return self._load_audio_streaming(path, target_sr, mono, offset, duration)
        elif file_size_mb > 20:  # Arquivos médios (>20MB)
            return self._load_audio_chunked(path, target_sr, mono, offset, duration)
        else:  # Arquivos pequenos
            return self._load_audio_standard(path, target_sr, mono, offset, duration)
    
    def _load_audio_standard(self, 
                           path: Path, 
                           target_sr: Optional[int],
                           mono: bool,
                           offset: float,
                           duration: Optional[float]) -> Tuple[np.ndarray, int]:
        """Carregamento padrão para arquivos pequenos"""
        format_ext = path.suffix.lower()
        libraries = self.format_preferences.get(format_ext, ['librosa'])
        
        for lib in libraries:
            try:
                if lib == 'librosa' and LIBROSA_AVAILABLE:
                    y, sr = librosa.load(
                        str(path),
                        sr=target_sr,
                        mono=mono,
                        offset=offset,
                        duration=duration
                    )
                    return y, sr
                elif lib == 'soundfile' and SOUNDFILE_AVAILABLE:
                    return self._load_with_soundfile(path, target_sr, mono, offset, duration)
                elif lib == 'pydub' and PYDUB_AVAILABLE:
                    return self._load_with_pydub(path, target_sr, mono, offset, duration)
            except Exception as e:
                print(f"Failed to load audio with {lib}: {e}")
                continue
        
        raise RuntimeError(f"Could not load audio file {path}")
    
    def _load_audio_chunked(self, 
                          path: Path, 
                          target_sr: Optional[int],
                          mono: bool,
                          offset: float,
                          duration: Optional[float]) -> Tuple[np.ndarray, int]:
        """Carregamento por chunks para arquivos médios"""
        # Usar soundfile para carregamento eficiente por chunks
        if SOUNDFILE_AVAILABLE:
            try:
                with sf.SoundFile(str(path)) as f:
                    sr = f.samplerate
                    
                    # Calcular range de samples
                    start_sample = int(offset * sr)
                    if duration:
                        samples_to_read = int(duration * sr)
                    else:
                        samples_to_read = len(f) - start_sample
                    
                    # Ler chunk
                    f.seek(start_sample)
                    audio_data = f.read(samples_to_read)
                    
                    # Converter para numpy array
                    if audio_data.ndim > 1 and mono:
                        audio_data = np.mean(audio_data, axis=1)
                    
                    # Resample se necessário
                    if target_sr and target_sr != sr:
                        if LIBROSA_AVAILABLE:
                            audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=target_sr)
                            sr = target_sr
                    
                    return audio_data.astype(np.float32), sr
            except Exception as e:
                print(f"Chunked loading failed: {e}")
        
        # Fallback para carregamento padrão
        return self._load_audio_standard(path, target_sr, mono, offset, duration)
    
    def _load_audio_streaming(self, 
                            path: Path, 
                            target_sr: Optional[int],
                            mono: bool,
                            offset: float,
                            duration: Optional[float]) -> Tuple[np.ndarray, int]:
        """Carregamento streaming para arquivos muito grandes"""
        # Para arquivos muito grandes, usar abordagem de streaming
        if SOUNDFILE_AVAILABLE:
            try:
                chunk_size = 44100 * 10  # 10 segundos por chunk
                chunks = []
                
                with sf.SoundFile(str(path)) as f:
                    sr = f.samplerate
                    start_sample = int(offset * sr)
                    
                    if duration:
                        end_sample = start_sample + int(duration * sr)
                    else:
                        end_sample = len(f)
                    
                    f.seek(start_sample)
                    
                    while f.tell() < end_sample:
                        remaining = end_sample - f.tell()
                        to_read = min(chunk_size, remaining)
                        
                        chunk = f.read(to_read)
                        if len(chunk) == 0:
                            break
                        
                        chunks.append(chunk)
                
                # Concatenar chunks
                if chunks:
                    audio_data = np.concatenate(chunks, axis=0)
                    
                    # Converter para mono se necessário
                    if audio_data.ndim > 1 and mono:
                        audio_data = np.mean(audio_data, axis=1)
                    
                    # Resample se necessário
                    if target_sr and target_sr != sr:
                        if LIBROSA_AVAILABLE:
                            audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=target_sr)
                            sr = target_sr
                    
                    return audio_data.astype(np.float32), sr
                    
            except Exception as e:
                print(f"Streaming loading failed: {e}")
        
        # Fallback final
        return self._load_audio_standard(path, target_sr, mono, offset, duration)
    
    def _load_with_soundfile(self, 
                           path: Path, 
                           target_sr: Optional[int],
                           mono: bool,
                           offset: float,
                           duration: Optional[float]) -> Tuple[np.ndarray, int]:
        """Carregamento com soundfile"""
        with sf.SoundFile(str(path)) as f:
            sr = f.samplerate
            
            start_sample = int(offset * sr)
            if duration:
                samples_to_read = int(duration * sr)
            else:
                samples_to_read = len(f) - start_sample
            
            f.seek(start_sample)
            audio_data = f.read(samples_to_read)
            
            if audio_data.ndim > 1 and mono:
                audio_data = np.mean(audio_data, axis=1)
            
            if target_sr and target_sr != sr and LIBROSA_AVAILABLE:
                audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=target_sr)
                sr = target_sr
            
            return audio_data.astype(np.float32), sr
    
    def _load_with_pydub(self, 
                        path: Path, 
                        target_sr: Optional[int],
                        mono: bool,
                        offset: float,
                        duration: Optional[float]) -> Tuple[np.ndarray, int]:
        """Carregamento com pydub"""
        audio = AudioSegment.from_file(str(path))
        
        # Aplicar offset e duration
        start_ms = int(offset * 1000)
        if duration:
            end_ms = start_ms + int(duration * 1000)
            audio = audio[start_ms:end_ms]
        else:
            audio = audio[start_ms:]
        
        # Converter para mono se necessário
        if mono and audio.channels > 1:
            audio = audio.set_channels(1)
        
        # Converter sample rate se necessário
        if target_sr and target_sr != audio.frame_rate:
            audio = audio.set_frame_rate(target_sr)
        
        # Converter para numpy
        audio_data = np.array(audio.get_array_of_samples(), dtype=np.float32)
        
        # Normalizar
        if audio.sample_width == 2:  # 16-bit
            audio_data /= 32768.0
        elif audio.sample_width == 4:  # 32-bit
            audio_data /= 2147483648.0
        
        return audio_data, audio.frame_rate
    
    def preload_files(self, file_paths: List[Union[str, Path]], target_sr: int = 16000):
        """
        Pré-carrega arquivos no cache para acesso rápido
        """
        for file_path in file_paths:
            try:
                # Carregar metadados primeiro
                metadata = self.load_metadata(file_path)
                
                # Decidir se vale a pena pré-carregar baseado no tamanho
                if metadata.file_size < 50 * 1024 * 1024:  # < 50MB
                    # Pré-carregar dados de áudio
                    self.load_audio_data(file_path, target_sr=target_sr)
                    print(f"Preloaded: {file_path}")
                else:
                    print(f"Skipped preload (too large): {file_path}")
                    
            except Exception as e:
                print(f"Failed to preload {file_path}: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        return self.cache.get_stats()


class OptimizedFileManager:
    """
    Gerenciador otimizado de arquivos com cache inteligente
    """
    
    def __init__(self, cache_config: FileCacheConfig = None):
        if cache_config is None:
            cache_config = FileCacheConfig(
                max_memory_mb=2048,  # 2GB para gerenciador de arquivos
                strategy=CacheStrategy.INTELLIGENT,
                ttl_hours=48  # 48 horas para arquivos
            )
        
        self.cache = get_file_cache(cache_config)
        self.audio_loader = OptimizedAudioLoader(cache_config)
    
    @file_cached('transcription_data')
    def load_transcription(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Carrega arquivo de transcrição (com cache)"""
        path = Path(file_path)
        
        if path.suffix.lower() == '.json':
            import json
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(path, 'r', encoding='utf-8') as f:
                return {'text': f.read()}
    
    @file_cached('binary_data')
    def load_binary_file(self, file_path: Union[str, Path]) -> bytes:
        """Carrega arquivo binário (com cache)"""
        with open(file_path, 'rb') as f:
            return f.read()
    
    @file_cached('text_data')
    def load_text_file(self, file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
        """Carrega arquivo de texto (com cache)"""
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    
    def prefetch_directory(self, directory: Union[str, Path], patterns: List[str] = None):
        """
        Pré-carrega arquivos de um diretório baseado em padrões
        """
        if patterns is None:
            patterns = ['*.wav', '*.mp3', '*.m4a', '*.json', '*.txt']
        
        dir_path = Path(directory)
        files_to_preload = []
        
        for pattern in patterns:
            files_to_preload.extend(dir_path.glob(pattern))
        
        # Ordenar por tamanho (menores primeiro)
        files_to_preload.sort(key=lambda p: p.stat().st_size)
        
        for file_path in files_to_preload:
            try:
                if file_path.suffix.lower() in ['.wav', '.mp3', '.m4a', '.flac']:
                    self.audio_loader.load_metadata(file_path)
                elif file_path.suffix.lower() == '.json':
                    self.load_transcription(file_path)
                elif file_path.suffix.lower() in ['.txt', '.srt', '.vtt']:
                    self.load_text_file(file_path)
                    
                print(f"Prefetched: {file_path.name}")
                
            except Exception as e:
                print(f"Failed to prefetch {file_path}: {e}")
    
    def optimize_cache(self):
        """Otimiza o cache removendo arquivos antigos e não utilizados"""
        self.cache.optimize()
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas abrangentes do sistema de cache"""
        cache_stats = self.cache.get_stats()
        audio_stats = self.audio_loader.get_cache_stats()
        
        return {
            'file_cache': cache_stats,
            'audio_cache': audio_stats,
            'combined_memory_mb': cache_stats['memory_usage_mb'] + audio_stats['memory_usage_mb'],
            'combined_hit_rate': (cache_stats['total_hits'] + audio_stats['total_hits']) / 
                               max(1, cache_stats['total_hits'] + cache_stats['total_misses'] + 
                                   audio_stats['total_hits'] + audio_stats['total_misses']) * 100
        }


# Instância global otimizada
_optimized_file_manager: Optional[OptimizedFileManager] = None

def get_optimized_file_manager() -> OptimizedFileManager:
    """Obtém instância singleton do gerenciador otimizado"""
    global _optimized_file_manager
    
    if _optimized_file_manager is None:
        _optimized_file_manager = OptimizedFileManager()
    
    return _optimized_file_manager