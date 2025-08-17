"""
Processador de Chunks de Áudio Otimizado

Sistema inteligente para processamento de áudio em chunks,
otimizando performance e memória durante transcrição.

Author: MeetingScribe Team
Version: 1.1.0
Python: >=3.8
"""

import gc
import time
import threading
from pathlib import Path
from typing import List, Optional, Generator, Tuple, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

from loguru import logger

try:
    import torch
    import torchaudio
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


class ChunkStrategy(str, Enum):
    """Estratégias de divisão em chunks."""
    TIME_BASED = "time_based"           # Chunks por tempo fixo
    SILENCE_BASED = "silence_based"     # Chunks baseados em silêncio
    ADAPTIVE = "adaptive"               # Adaptativo por conteúdo
    VOICE_ACTIVITY = "voice_activity"   # Baseado em atividade de voz


@dataclass
class ChunkConfig:
    """Configuração para processamento de chunks."""
    strategy: ChunkStrategy = ChunkStrategy.ADAPTIVE
    chunk_duration: float = 30.0  # segundos
    overlap_duration: float = 2.0  # segundos de sobreposição
    min_chunk_duration: float = 5.0   # mínimo para chunk válido
    max_chunk_duration: float = 60.0  # máximo para chunk
    
    # Configurações para detecção de silêncio
    silence_threshold_db: float = -40.0
    min_silence_duration: float = 0.5
    
    # Configurações de performance
    parallel_processing: bool = True
    max_workers: int = 2
    memory_limit_mb: float = 1024  # 1GB por chunk
    
    # Configurações de qualidade
    sample_rate: int = 16000
    normalize_audio: bool = True
    remove_noise: bool = False


@dataclass
class AudioChunk:
    """Representa um chunk de áudio."""
    chunk_id: int
    start_time: float
    end_time: float
    duration: float
    audio_data: bytes
    sample_rate: int
    channels: int
    
    # Metadados
    has_speech: bool = True
    confidence: float = 1.0
    noise_level: float = 0.0
    
    @property
    def memory_usage_mb(self) -> float:
        """Calcula uso de memória em MB."""
        return len(self.audio_data) / (1024 * 1024)


@dataclass
class ChunkProcessingResult:
    """Resultado do processamento de chunks."""
    chunks: List[AudioChunk] = field(default_factory=list)
    total_duration: float = 0.0
    total_chunks: int = 0
    processing_time: float = 0.0
    memory_usage_mb: float = 0.0
    strategy_used: str = ""
    
    # Estatísticas
    speech_chunks: int = 0
    silence_chunks: int = 0
    average_chunk_duration: float = 0.0


class AudioChunkProcessor:
    """
    Processador inteligente de chunks de áudio.
    
    Otimiza processamento dividindo áudio em chunks
    inteligentes baseados em conteúdo e estratégias.
    """
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        """
        Inicializa o processador de chunks.
        
        Args:
            config: Configuração do processador
        """
        self.config = config or ChunkConfig()
        self._lock = threading.Lock()
        
        logger.info(f"Processador de chunks inicializado - estratégia: {self.config.strategy}")
    
    def process_audio_file(
        self, 
        audio_path: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> ChunkProcessingResult:
        """
        Processa arquivo de áudio em chunks otimizados.
        
        Args:
            audio_path: Caminho para arquivo de áudio
            progress_callback: Callback para progresso
            
        Returns:
            ChunkProcessingResult: Resultado do processamento
        """
        start_time = time.time()
        
        if progress_callback:
            progress_callback(0.1, "Carregando arquivo de áudio...")
        
        # Carregar áudio
        audio_data, sample_rate = self._load_audio_file(audio_path)
        duration = len(audio_data) / sample_rate
        
        if progress_callback:
            progress_callback(0.2, f"Áudio carregado: {duration:.1f}s")
        
        # Detectar estratégia ideal se configurado como adaptativo
        if self.config.strategy == ChunkStrategy.ADAPTIVE:
            strategy = self._detect_optimal_strategy(audio_data, sample_rate, duration)
            logger.info(f"Estratégia adaptativa selecionada: {strategy}")
        else:
            strategy = self.config.strategy
        
        if progress_callback:
            progress_callback(0.3, f"Dividindo em chunks ({strategy})...")
        
        # Dividir em chunks
        chunks = self._create_chunks(audio_data, sample_rate, strategy, progress_callback)
        
        if progress_callback:
            progress_callback(0.8, "Finalizando processamento...")
        
        # Calcular estatísticas
        processing_time = time.time() - start_time
        
        result = ChunkProcessingResult(
            chunks=chunks,
            total_duration=duration,
            total_chunks=len(chunks),
            processing_time=processing_time,
            memory_usage_mb=sum(chunk.memory_usage_mb for chunk in chunks),
            strategy_used=strategy.value,
            speech_chunks=sum(1 for chunk in chunks if chunk.has_speech),
            silence_chunks=sum(1 for chunk in chunks if not chunk.has_speech),
            average_chunk_duration=sum(chunk.duration for chunk in chunks) / len(chunks) if chunks else 0
        )
        
        if progress_callback:
            progress_callback(1.0, f"Processamento concluído: {len(chunks)} chunks")
        
        logger.success(f"Áudio processado em {processing_time:.2f}s - {len(chunks)} chunks criados")
        return result
    
    def _load_audio_file(self, audio_path: Path) -> Tuple[any, int]:
        """Carrega arquivo de áudio usando a melhor biblioteca disponível."""
        
        if TORCH_AVAILABLE and LIBROSA_AVAILABLE:
            # Preferir torchaudio + librosa para melhor performance
            try:
                waveform, sample_rate = torchaudio.load(str(audio_path))
                # Converter para mono se necessário
                if waveform.shape[0] > 1:
                    waveform = torch.mean(waveform, dim=0, keepdim=True)
                
                # Resample se necessário
                if sample_rate != self.config.sample_rate:
                    resampler = torchaudio.transforms.Resample(sample_rate, self.config.sample_rate)
                    waveform = resampler(waveform)
                    sample_rate = self.config.sample_rate
                
                audio_data = waveform.squeeze().numpy()
                logger.debug(f"Áudio carregado com torchaudio: {len(audio_data)} samples, {sample_rate}Hz")
                return audio_data, sample_rate
                
            except Exception as e:
                logger.warning(f"Falha com torchaudio, tentando librosa: {e}")
        
        if LIBROSA_AVAILABLE:
            try:
                audio_data, sample_rate = librosa.load(
                    str(audio_path), 
                    sr=self.config.sample_rate,
                    mono=True
                )
                logger.debug(f"Áudio carregado com librosa: {len(audio_data)} samples, {sample_rate}Hz")
                return audio_data, sample_rate
                
            except Exception as e:
                logger.warning(f"Falha com librosa, tentando pydub: {e}")
        
        if PYDUB_AVAILABLE:
            try:
                audio = AudioSegment.from_file(str(audio_path))
                
                # Converter para mono e sample rate desejado
                if audio.channels > 1:
                    audio = audio.set_channels(1)
                
                if audio.frame_rate != self.config.sample_rate:
                    audio = audio.set_frame_rate(self.config.sample_rate)
                
                # Converter para numpy array
                audio_data = audio.get_array_of_samples()
                
                # Normalizar para float32
                import numpy as np
                audio_data = np.array(audio_data, dtype=np.float32)
                if audio.sample_width == 2:  # 16-bit
                    audio_data = audio_data / 32768.0
                elif audio.sample_width == 4:  # 32-bit
                    audio_data = audio_data / 2147483648.0
                
                sample_rate = audio.frame_rate
                logger.debug(f"Áudio carregado com pydub: {len(audio_data)} samples, {sample_rate}Hz")
                return audio_data, sample_rate
                
            except Exception as e:
                logger.error(f"Falha com pydub: {e}")
        
        raise RuntimeError("Nenhuma biblioteca de áudio disponível para carregar arquivo")
    
    def _detect_optimal_strategy(self, audio_data, sample_rate: int, duration: float) -> ChunkStrategy:
        """Detecta estratégia ideal baseada nas características do áudio."""
        
        # Áudio muito curto - usar chunks baseados em tempo
        if duration < 60:
            return ChunkStrategy.TIME_BASED
        
        # Áudio longo com possíveis pausas - usar detecção de silêncio
        if duration > 300:  # 5 minutos
            silence_ratio = self._analyze_silence_ratio(audio_data, sample_rate)
            if silence_ratio > 0.2:  # 20% de silêncio
                return ChunkStrategy.SILENCE_BASED
        
        # Para maioria dos casos, usar voice activity
        return ChunkStrategy.VOICE_ACTIVITY
    
    def _analyze_silence_ratio(self, audio_data, sample_rate: int) -> float:
        """Analisa a proporção de silêncio no áudio."""
        try:
            import numpy as np
            
            # Calcular RMS em janelas
            window_size = int(0.1 * sample_rate)  # 100ms windows
            windows = len(audio_data) // window_size
            
            silence_count = 0
            threshold = 10 ** (self.config.silence_threshold_db / 20)
            
            for i in range(windows):
                start = i * window_size
                end = start + window_size
                window = audio_data[start:end]
                
                rms = np.sqrt(np.mean(window ** 2))
                if rms < threshold:
                    silence_count += 1
            
            return silence_count / windows if windows > 0 else 0
            
        except Exception as e:
            logger.warning(f"Erro na análise de silêncio: {e}")
            return 0.1  # Valor conservativo
    
    def _create_chunks(
        self, 
        audio_data, 
        sample_rate: int, 
        strategy: ChunkStrategy,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> List[AudioChunk]:
        """Cria chunks baseado na estratégia selecionada."""
        
        if strategy == ChunkStrategy.TIME_BASED:
            return self._create_time_based_chunks(audio_data, sample_rate, progress_callback)
        elif strategy == ChunkStrategy.SILENCE_BASED:
            return self._create_silence_based_chunks(audio_data, sample_rate, progress_callback)
        elif strategy == ChunkStrategy.VOICE_ACTIVITY:
            return self._create_voice_activity_chunks(audio_data, sample_rate, progress_callback)
        else:
            # Fallback para time-based
            return self._create_time_based_chunks(audio_data, sample_rate, progress_callback)
    
    def _create_time_based_chunks(
        self, 
        audio_data, 
        sample_rate: int,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> List[AudioChunk]:
        """Cria chunks baseados em tempo fixo com sobreposição."""
        import numpy as np
        
        chunks = []
        duration = len(audio_data) / sample_rate
        
        chunk_samples = int(self.config.chunk_duration * sample_rate)
        overlap_samples = int(self.config.overlap_duration * sample_rate)
        step_samples = chunk_samples - overlap_samples
        
        chunk_id = 0
        position = 0
        
        while position < len(audio_data):
            # Calcular limites do chunk
            start_sample = position
            end_sample = min(position + chunk_samples, len(audio_data))
            
            # Extrair chunk
            chunk_audio = audio_data[start_sample:end_sample]
            
            # Verificar se chunk tem duração mínima
            chunk_duration = len(chunk_audio) / sample_rate
            if chunk_duration < self.config.min_chunk_duration:
                break
            
            # Converter para bytes (16-bit)
            chunk_audio_int16 = (chunk_audio * 32767).astype(np.int16)
            chunk_bytes = chunk_audio_int16.tobytes()
            
            # Criar chunk
            chunk = AudioChunk(
                chunk_id=chunk_id,
                start_time=start_sample / sample_rate,
                end_time=end_sample / sample_rate,
                duration=chunk_duration,
                audio_data=chunk_bytes,
                sample_rate=sample_rate,
                channels=1,
                has_speech=True,  # Assumir que tem fala
                confidence=1.0
            )
            
            chunks.append(chunk)
            
            # Atualizar progresso
            if progress_callback:
                progress = 0.3 + (0.5 * (position / len(audio_data)))
                progress_callback(progress, f"Chunk {chunk_id + 1} criado")
            
            chunk_id += 1
            position += step_samples
        
        logger.info(f"Criados {len(chunks)} chunks baseados em tempo")
        return chunks
    
    def _create_silence_based_chunks(
        self, 
        audio_data, 
        sample_rate: int,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> List[AudioChunk]:
        """Cria chunks baseados em detecção de silêncio."""
        import numpy as np
        
        # Detectar segmentos de silêncio
        silence_segments = self._detect_silence_segments(audio_data, sample_rate)
        
        if not silence_segments:
            # Fallback para time-based se não encontrar silêncios
            logger.info("Nenhum silêncio detectado, usando chunks baseados em tempo")
            return self._create_time_based_chunks(audio_data, sample_rate, progress_callback)
        
        chunks = []
        chunk_id = 0
        last_end = 0
        
        for silence_start, silence_end in silence_segments:
            # Criar chunk do último final até início do silêncio
            if silence_start - last_end > self.config.min_chunk_duration * sample_rate:
                chunk_audio = audio_data[last_end:silence_start]
                chunk_duration = len(chunk_audio) / sample_rate
                
                # Dividir chunk se muito longo
                if chunk_duration > self.config.max_chunk_duration:
                    sub_chunks = self._split_long_chunk(
                        chunk_audio, sample_rate, chunk_id, last_end / sample_rate
                    )
                    chunks.extend(sub_chunks)
                    chunk_id += len(sub_chunks)
                else:
                    # Converter para bytes
                    chunk_audio_int16 = (chunk_audio * 32767).astype(np.int16)
                    chunk_bytes = chunk_audio_int16.tobytes()
                    
                    chunk = AudioChunk(
                        chunk_id=chunk_id,
                        start_time=last_end / sample_rate,
                        end_time=silence_start / sample_rate,
                        duration=chunk_duration,
                        audio_data=chunk_bytes,
                        sample_rate=sample_rate,
                        channels=1,
                        has_speech=True,
                        confidence=0.9
                    )
                    
                    chunks.append(chunk)
                    chunk_id += 1
            
            last_end = silence_end
            
            # Atualizar progresso
            if progress_callback:
                progress = 0.3 + (0.5 * (silence_end / len(audio_data)))
                progress_callback(progress, f"Processando silêncios...")
        
        # Chunk final
        if last_end < len(audio_data):
            final_chunk_audio = audio_data[last_end:]
            chunk_duration = len(final_chunk_audio) / sample_rate
            
            if chunk_duration >= self.config.min_chunk_duration:
                final_chunk_audio_int16 = (final_chunk_audio * 32767).astype(np.int16)
                chunk_bytes = final_chunk_audio_int16.tobytes()
                
                chunk = AudioChunk(
                    chunk_id=chunk_id,
                    start_time=last_end / sample_rate,
                    end_time=len(audio_data) / sample_rate,
                    duration=chunk_duration,
                    audio_data=chunk_bytes,
                    sample_rate=sample_rate,
                    channels=1,
                    has_speech=True,
                    confidence=0.9
                )
                
                chunks.append(chunk)
        
        logger.info(f"Criados {len(chunks)} chunks baseados em silêncio")
        return chunks
    
    def _create_voice_activity_chunks(
        self, 
        audio_data, 
        sample_rate: int,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> List[AudioChunk]:
        """Cria chunks baseados em atividade de voz (VAD simples)."""
        import numpy as np
        
        # VAD simples baseado em energia
        window_size = int(0.02 * sample_rate)  # 20ms windows
        hop_size = window_size // 2
        
        energy_threshold = self._calculate_energy_threshold(audio_data, window_size, hop_size)
        voice_segments = []
        
        is_voice = False
        voice_start = 0
        
        for i in range(0, len(audio_data) - window_size, hop_size):
            window = audio_data[i:i + window_size]
            energy = np.sum(window ** 2)
            
            if energy > energy_threshold:
                if not is_voice:
                    voice_start = i
                    is_voice = True
            else:
                if is_voice:
                    voice_segments.append((voice_start, i))
                    is_voice = False
        
        # Fechar último segmento se necessário
        if is_voice:
            voice_segments.append((voice_start, len(audio_data)))
        
        # Consolidar segmentos próximos e criar chunks
        chunks = []
        chunk_id = 0
        
        consolidated_segments = self._consolidate_voice_segments(voice_segments, sample_rate)
        
        for start, end in consolidated_segments:
            chunk_audio = audio_data[start:end]
            chunk_duration = len(chunk_audio) / sample_rate
            
            if chunk_duration >= self.config.min_chunk_duration:
                # Dividir se muito longo
                if chunk_duration > self.config.max_chunk_duration:
                    sub_chunks = self._split_long_chunk(
                        chunk_audio, sample_rate, chunk_id, start / sample_rate
                    )
                    chunks.extend(sub_chunks)
                    chunk_id += len(sub_chunks)
                else:
                    chunk_audio_int16 = (chunk_audio * 32767).astype(np.int16)
                    chunk_bytes = chunk_audio_int16.tobytes()
                    
                    chunk = AudioChunk(
                        chunk_id=chunk_id,
                        start_time=start / sample_rate,
                        end_time=end / sample_rate,
                        duration=chunk_duration,
                        audio_data=chunk_bytes,
                        sample_rate=sample_rate,
                        channels=1,
                        has_speech=True,
                        confidence=0.8
                    )
                    
                    chunks.append(chunk)
                    chunk_id += 1
            
            # Atualizar progresso
            if progress_callback:
                progress = 0.3 + (0.5 * (end / len(audio_data)))
                progress_callback(progress, f"Chunk {chunk_id} processado")
        
        logger.info(f"Criados {len(chunks)} chunks baseados em atividade de voz")
        return chunks
    
    def _calculate_energy_threshold(self, audio_data, window_size: int, hop_size: int) -> float:
        """Calcula threshold de energia para VAD."""
        import numpy as np
        
        energies = []
        for i in range(0, len(audio_data) - window_size, hop_size):
            window = audio_data[i:i + window_size]
            energy = np.sum(window ** 2)
            energies.append(energy)
        
        # Usar percentil 60 como threshold
        return np.percentile(energies, 60) if energies else 0.0
    
    def _consolidate_voice_segments(self, segments: List[Tuple[int, int]], sample_rate: int) -> List[Tuple[int, int]]:
        """Consolida segmentos de voz próximos."""
        if not segments:
            return []
        
        consolidated = []
        current_start, current_end = segments[0]
        
        gap_threshold = int(0.5 * sample_rate)  # 500ms
        
        for start, end in segments[1:]:
            if start - current_end <= gap_threshold:
                # Consolidar com segmento atual
                current_end = end
            else:
                # Adicionar segmento atual e iniciar novo
                consolidated.append((current_start, current_end))
                current_start, current_end = start, end
        
        # Adicionar último segmento
        consolidated.append((current_start, current_end))
        
        return consolidated
    
    def _detect_silence_segments(self, audio_data, sample_rate: int) -> List[Tuple[int, int]]:
        """Detecta segmentos de silêncio no áudio."""
        import numpy as np
        
        window_size = int(0.01 * sample_rate)  # 10ms windows
        threshold = 10 ** (self.config.silence_threshold_db / 20)
        min_silence_samples = int(self.config.min_silence_duration * sample_rate)
        
        silence_segments = []
        is_silence = False
        silence_start = 0
        
        for i in range(0, len(audio_data) - window_size, window_size):
            window = audio_data[i:i + window_size]
            rms = np.sqrt(np.mean(window ** 2))
            
            if rms < threshold:
                if not is_silence:
                    silence_start = i
                    is_silence = True
            else:
                if is_silence and (i - silence_start) >= min_silence_samples:
                    silence_segments.append((silence_start, i))
                is_silence = False
        
        return silence_segments
    
    def _split_long_chunk(
        self, 
        chunk_audio, 
        sample_rate: int, 
        base_chunk_id: int, 
        start_time: float
    ) -> List[AudioChunk]:
        """Divide chunk longo em chunks menores."""
        import numpy as np
        
        sub_chunks = []
        chunk_samples = int(self.config.chunk_duration * sample_rate)
        overlap_samples = int(self.config.overlap_duration * sample_rate)
        step_samples = chunk_samples - overlap_samples
        
        position = 0
        sub_id = 0
        
        while position < len(chunk_audio):
            end_pos = min(position + chunk_samples, len(chunk_audio))
            sub_audio = chunk_audio[position:end_pos]
            
            sub_duration = len(sub_audio) / sample_rate
            if sub_duration < self.config.min_chunk_duration:
                break
            
            sub_audio_int16 = (sub_audio * 32767).astype(np.int16)
            chunk_bytes = sub_audio_int16.tobytes()
            
            sub_chunk = AudioChunk(
                chunk_id=f"{base_chunk_id}_{sub_id}",
                start_time=start_time + (position / sample_rate),
                end_time=start_time + (end_pos / sample_rate),
                duration=sub_duration,
                audio_data=chunk_bytes,
                sample_rate=sample_rate,
                channels=1,
                has_speech=True,
                confidence=0.9
            )
            
            sub_chunks.append(sub_chunk)
            position += step_samples
            sub_id += 1
        
        return sub_chunks
    
    def get_chunk_as_file(self, chunk: AudioChunk, output_path: Path) -> Path:
        """Salva chunk como arquivo de áudio temporário."""
        import wave
        
        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(chunk.channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(chunk.sample_rate)
            wav_file.writeframes(chunk.audio_data)
        
        return output_path
    
    def cleanup_chunks(self, chunks: List[AudioChunk]) -> None:
        """Limpa memória dos chunks."""
        for chunk in chunks:
            chunk.audio_data = b''  # Limpar dados de áudio
        
        gc.collect()
        logger.debug(f"Memória de {len(chunks)} chunks liberada")


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_chunk_processor(
    strategy: ChunkStrategy = ChunkStrategy.ADAPTIVE,
    chunk_duration: float = 30.0,
    parallel_processing: bool = True
) -> AudioChunkProcessor:
    """
    Factory function para criar processador de chunks.
    
    Args:
        strategy: Estratégia de divisão
        chunk_duration: Duração base dos chunks
        parallel_processing: Habilitar processamento paralelo
        
    Returns:
        AudioChunkProcessor configurado
    """
    config = ChunkConfig(
        strategy=strategy,
        chunk_duration=chunk_duration,
        parallel_processing=parallel_processing
    )
    
    return AudioChunkProcessor(config)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "AudioChunkProcessor",
    "ChunkConfig", 
    "ChunkStrategy",
    "AudioChunk",
    "ChunkProcessingResult",
    "create_chunk_processor"
]