"""
Sistema de Transcrição com Whisper
Módulo principal para transcrição de áudio usando faster-whisper.
"""

import time
import gc
import contextlib
from pathlib import Path
from typing import Dict, List, Optional, Generator, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from faster_whisper import WhisperModel

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
from loguru import logger

# Importar cache de modelos
try:
    from src.core.model_cache import create_cached_model, get_model_cache
    MODEL_CACHE_AVAILABLE = True
except ImportError:
    MODEL_CACHE_AVAILABLE = False
    logger.debug("Cache de modelos não disponível")

# Importar gerenciador de memória
try:
    from src.core.memory_manager import get_memory_manager, register_for_cleanup, managed_memory
    MEMORY_MANAGER_AVAILABLE = True
except ImportError:
    MEMORY_MANAGER_AVAILABLE = False
    logger.debug("Gerenciador de memória não disponível")

# Importar monitor de performance
try:
    from src.core.performance_monitor import (
        get_performance_monitor, 
        TranscriptionMetrics, 
        PerformanceTimer,
        monitor_performance
    )
    PERFORMANCE_MONITOR_AVAILABLE = True
except ImportError:
    PERFORMANCE_MONITOR_AVAILABLE = False
    logger.debug("Monitor de performance não disponível")

# Importar auto profiler
try:
    from src.core.auto_profiler import get_auto_profiler, auto_profile
    AUTO_PROFILER_AVAILABLE = True
except ImportError:
    AUTO_PROFILER_AVAILABLE = False
    logger.debug("Auto profiler não disponível")

# Importar cache de arquivos
try:
    from src.core.file_optimizers import get_optimized_file_manager
    FILE_CACHE_AVAILABLE = True
except ImportError:
    FILE_CACHE_AVAILABLE = False
    logger.debug("Cache de arquivos não disponível")

# Importar streaming processor
try:
    from src.core.streaming_processor import (
        create_audio_streamer,
        StreamConfig,
        StreamingStrategy,
        AudioStreamer,
        streaming_audio
    )
    STREAMING_AVAILABLE = True
except ImportError:
    STREAMING_AVAILABLE = False
    logger.debug("Streaming processor não disponível")


class WhisperModelSize(Enum):
    """Tamanhos disponíveis do modelo Whisper."""
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"


class TranscriptionStatus(Enum):
    """Status possíveis da transcrição."""
    PENDING = "pending"
    LOADING_MODEL = "loading_model"
    TRANSCRIBING = "transcribing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TranscriptionSegment:
    """Representa um segmento da transcrição."""
    id: int
    text: str
    start: float
    end: float
    confidence: float = 0.0
    speaker: Optional[str] = None
    language: Optional[str] = None


@dataclass
class TranscriptionResult:
    """Resultado completo da transcrição."""
    segments: List[TranscriptionSegment] = field(default_factory=list)
    language: Optional[str] = None
    duration: float = 0.0
    model_size: str = "base"
    processing_time: float = 0.0
    confidence_avg: float = 0.0
    word_count: int = 0
    
    @property
    def full_text(self) -> str:
        """Retorna o texto completo da transcrição."""
        return " ".join([segment.text.strip() for segment in self.segments])
    
    @property
    def formatted_text(self) -> str:
        """Retorna texto formatado com timestamps."""
        lines = []
        for segment in self.segments:
            timestamp = f"[{self._format_time(segment.start)} -> {self._format_time(segment.end)}]"
            speaker = f" ({segment.speaker})" if segment.speaker else ""
            lines.append(f"{timestamp}{speaker} {segment.text.strip()}")
        return "\n".join(lines)
    
    def _format_time(self, seconds: float) -> str:
        """Formata tempo em MM:SS."""
        mins, secs = divmod(int(seconds), 60)
        return f"{mins:02d}:{secs:02d}"


@dataclass
class TranscriptionConfig:
    """Configuração para transcrição otimizada."""
    model_size: WhisperModelSize = WhisperModelSize.BASE  # Modelo balanceado por padrão
    language: Optional[str] = None  # None para auto-detecção
    compute_type: str = "float32"  # float16 para GPU, float32 para CPU, int8 para velocidade máxima
    device: str = "auto"  # auto, cpu, cuda
    beam_size: int = 5  # Aumentado para melhor qualidade
    temperature: float = 0.0  # Temperatura baixa para consistência
    compression_ratio_threshold: float = 2.4
    log_prob_threshold: float = -1.0
    no_speech_threshold: float = 0.6
    condition_on_previous_text: bool = True  # Habilitado para melhor contexto
    word_timestamps: bool = True
    vad_filter: bool = True  # VAD crítico para performance
    vad_parameters: Dict[str, Any] = field(default_factory=lambda: {
        "threshold": 0.5,
        "min_speech_duration_ms": 250,
        "max_speech_duration_s": 60,  # Chunks maiores para melhor contexto
        "min_silence_duration_ms": 1000,  
        "speech_pad_ms": 400  # Mais padding para capturar início/fim
    })
    # Novos parâmetros de otimização
    batch_size: int = 1  # Para processamento em lote
    chunk_length: int = 30  # Tamanho do chunk em segundos
    # Configurações específicas para qualidade
    quality_mode: bool = False  # Modo alta qualidade para áudios grandes


class TranscriptionError(Exception):
    """Exceções relacionadas à transcrição."""
    pass


class ModelLoadError(TranscriptionError):
    """Erro ao carregar modelo Whisper."""
    pass


class TranscriptionProgress:
    """Callback para progresso da transcrição."""
    
    def __init__(self, callback: Optional[Callable[[float, str], None]] = None):
        self.callback = callback
        self._current_progress = 0.0
        self._current_status = "Iniciando..."
    
    def update(self, progress: float, status: str = ""):
        """Atualiza o progresso."""
        self._current_progress = progress
        self._current_status = status
        if self.callback:
            self.callback(progress, status)
    
    @property
    def progress(self) -> float:
        return self._current_progress
    
    @property
    def status(self) -> str:
        return self._current_status


class WhisperTranscriber:
    """
    Transcritor principal usando faster-whisper.
    
    Gerencia modelos Whisper e executa transcrições com suporte a
    progresso em tempo real, detecção de idioma e timestamps.
    """
    
    def __init__(self, config: Optional[TranscriptionConfig] = None):
        self.config = config or TranscriptionConfig()
        self._model: Optional[WhisperModel] = None
        self._model_loaded = False
        self._cancel_requested = False
        self._lock = threading.Lock()
        
        # Registrar no gerenciador de memória
        if MEMORY_MANAGER_AVAILABLE:
            memory_manager = get_memory_manager()
            estimated_size = self._estimate_transcriber_size()
            register_for_cleanup(self, 'transcribers', estimated_size)
        
        logger.info(f"Transcritor inicializado - Modelo: {self.config.model_size.value}")
    
    def _estimate_transcriber_size(self) -> float:
        """Estima tamanho em MB do transcritor baseado no modelo."""
        size_estimates = {
            WhisperModelSize.TINY: 50,
            WhisperModelSize.BASE: 100,
            WhisperModelSize.SMALL: 200,
            WhisperModelSize.MEDIUM: 400,
            WhisperModelSize.LARGE_V2: 800,
            WhisperModelSize.LARGE_V3: 800
        }
        return size_estimates.get(self.config.model_size, 200)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    @property
    def is_model_loaded(self) -> bool:
        """Verifica se o modelo está carregado."""
        return self._model_loaded and self._model is not None
    
    def load_model(self, progress: Optional[TranscriptionProgress] = None) -> None:
        """
        Carrega o modelo Whisper usando cache inteligente.
        
        Args:
            progress: Callback opcional para progresso
            
        Raises:
            ModelLoadError: Se falhar ao carregar o modelo
        """
        if self.is_model_loaded:
            logger.debug("Modelo já está carregado")
            return
        
        try:
            if progress:
                progress.update(0.1, "Inicializando modelo Whisper...")
            
            logger.info(f"Carregando modelo Whisper: {self.config.model_size.value}")
            
            with self._lock:
                # Detectar dispositivo automaticamente
                device = self._detect_device() if self.config.device == "auto" else self.config.device
                
                # Otimizar compute_type baseado no dispositivo
                if device == "cuda":
                    compute_type = "float16"  # Mais rápido na GPU
                elif device == "cpu":
                    compute_type = "int8"  # Quantização para CPU
                else:
                    compute_type = self.config.compute_type
                
                logger.info(f"Usando dispositivo: {device}, compute_type: {compute_type}")
                
                # Tentar usar cache primeiro
                if MODEL_CACHE_AVAILABLE:
                    if progress:
                        progress.update(0.3, "Verificando cache de modelos...")
                    
                    try:
                        model_load_start = time.time()
                        self._model, cache_hit = create_cached_model(
                            self.config.model_size.value,
                            device,
                            compute_type
                        )
                        model_load_time = time.time() - model_load_start
                        
                        # Atualizar métricas de cache
                        performance_metrics['cache_hits'] = 1 if cache_hit else 0
                        
                        # Evento de profiling para carregamento do modelo
                        if AUTO_PROFILER_AVAILABLE and profiling_session_id:
                            try:
                                profiler.add_profiling_event(
                                    profiling_session_id,
                                    'model_loading',
                                    f"Model {self.config.model_size.value} loaded ({'from cache' if cache_hit else 'fresh load'})",
                                    {
                                        'load_time': model_load_time,
                                        'cache_hit': cache_hit,
                                        'model_size': self.config.model_size.value,
                                        'device': device,
                                        'compute_type': compute_type
                                    }
                                )
                            except Exception as e:
                                logger.debug(f"Erro ao adicionar evento de profiling: {e}")
                        
                        if cache_hit:
                            logger.success(f"Modelo {self.config.model_size.value} obtido do cache!")
                            if progress:
                                progress.update(0.9, "Modelo carregado do cache")
                        else:
                            logger.info(f"Modelo {self.config.model_size.value} carregado e adicionado ao cache")
                            if progress:
                                progress.update(0.8, "Modelo carregado e cached")
                                
                    except Exception as e:
                        logger.warning(f"Falha no cache, carregando diretamente: {e}")
                        # Fallback para carregamento direto
                        if progress:
                            progress.update(0.3, f"Carregando modelo {self.config.model_size.value}...")
                        
                        self._model = WhisperModel(
                            self.config.model_size.value,
                            device=device,
                            compute_type=compute_type,
                            download_root=None,
                            local_files_only=False,
                            cpu_threads=4
                        )
                else:
                    # Cache não disponível, carregamento direto
                    if progress:
                        progress.update(0.3, f"Carregando modelo {self.config.model_size.value}...")
                    
                    self._model = WhisperModel(
                        self.config.model_size.value,
                        device=device,
                        compute_type=compute_type,
                        download_root=None,
                        local_files_only=False,
                        cpu_threads=4
                    )
                
                if progress:
                    progress.update(0.8, "Validando modelo...")
                
                # Modelo carregado com sucesso - pular teste se torch não disponível
                if TORCH_AVAILABLE:
                    test_audio = torch.zeros(16000, dtype=torch.float32)  # 1 segundo de silêncio
                    list(self._model.transcribe(test_audio, beam_size=1, language="en"))
                
                self._model_loaded = True
                
                if progress:
                    progress.update(1.0, "Modelo carregado com sucesso!")
                
                logger.success(f"Modelo {self.config.model_size.value} carregado com sucesso")
        
        except Exception as e:
            error_msg = f"Falha ao carregar modelo Whisper: {str(e)}"
            logger.error(error_msg)
            
            if progress:
                progress.update(0.0, f"Erro: {str(e)}")
            
            raise ModelLoadError(error_msg) from e
    
    def _detect_device(self) -> str:
        """Detecta o melhor dispositivo disponível."""
        if TORCH_AVAILABLE and torch.cuda.is_available():
            logger.info("CUDA detectado - usando GPU")
            return "cuda"
        else:
            logger.info("CUDA não disponível - usando CPU")
            return "cpu"
    
    def _process_segment(self, segment, segments: List[TranscriptionSegment], segment_id: int, language: str) -> None:
        """Helper method to process a single segment."""
        transcription_segment = TranscriptionSegment(
            id=segment_id,
            text=segment.text,
            start=segment.start,
            end=segment.end,
            confidence=getattr(segment, 'avg_logprob', 0.0),
            language=language
        )
        segments.append(transcription_segment)
    
    def transcribe_file(
        self,
        audio_path: Path,
        progress: Optional[TranscriptionProgress] = None,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcreve um arquivo de áudio.
        
        Args:
            audio_path: Caminho para o arquivo de áudio
            progress: Callback opcional para progresso
            language: Idioma específico (None para auto-detecção)
            
        Returns:
            TranscriptionResult com os resultados
            
        Raises:
            TranscriptionError: Se falhar na transcrição
            FileNotFoundError: Se arquivo não existir
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_path}")
        
        if not self.is_model_loaded:
            self.load_model(progress)
        
        self._cancel_requested = False
        start_time = time.time()
        
        # Inicializar métricas de performance
        performance_metrics = {
            'cache_hits': 0,
            'chunks_count': 1,
            'gpu_used': False,
            'success': False,
            'error_message': None
        }
        
        # Inicializar auto profiling
        profiling_session_id = None
        if AUTO_PROFILER_AVAILABLE:
            try:
                profiler = get_auto_profiler()
                profiling_context = {
                    'audio_path': str(audio_path),
                    'model_size': self.config.model_size.value,
                    'language': language,
                    'file_size_mb': audio_path.stat().st_size / (1024 * 1024)
                }
                profiling_session_id = profiler.start_profiling_session('transcription', profiling_context)
            except Exception as e:
                logger.debug(f"Erro ao iniciar profiling: {e}")
        
        try:
            # Monitorar memória no início da transcrição
            if MEMORY_MANAGER_AVAILABLE:
                memory_manager = get_memory_manager()
                initial_stats = memory_manager.get_current_stats()
                if initial_stats.pressure_level.value in ['high', 'critical']:
                    logger.warning(f"Pressão de memória detectada: {initial_stats.pressure_level.value}")
                    memory_manager.optimize_memory()
            
            if progress:
                progress.update(0.1, "Preparando transcrição...")
            
            logger.info(f"Iniciando transcrição: {audio_path}")
            
            # Detectar se está usando GPU
            performance_metrics['gpu_used'] = device == "cuda" if TORCH_AVAILABLE else False
            
            # Pré-carregar metadados do arquivo no cache se disponível
            if FILE_CACHE_AVAILABLE:
                try:
                    file_manager = get_optimized_file_manager()
                    audio_metadata = file_manager.audio_loader.load_metadata(audio_path)
                    logger.debug(f"Arquivo de áudio: {audio_metadata.duration:.1f}s, {audio_metadata.format}, {audio_metadata.file_size / 1024 / 1024:.1f}MB")
                    
                    # Evento de profiling para metadados
                    if AUTO_PROFILER_AVAILABLE and profiling_session_id:
                        profiler.add_profiling_event(
                            profiling_session_id,
                            'audio_metadata_loaded',
                            f"Audio metadata cached: {audio_metadata.duration:.1f}s",
                            {
                                'duration': audio_metadata.duration,
                                'sample_rate': audio_metadata.sample_rate,
                                'channels': audio_metadata.channels,
                                'format': audio_metadata.format,
                                'file_size_mb': audio_metadata.file_size / 1024 / 1024
                            }
                        )
                except Exception as e:
                    logger.debug(f"Erro ao carregar metadados no cache: {e}")
            
            # Configurar parâmetros
            transcribe_language = language or self.config.language
            
            segments = []
            
            # Detectar se é áudio longo (>5 min) para usar modo qualidade
            audio_size_mb = audio_path.stat().st_size / (1024 * 1024)
            is_large_file = audio_size_mb > 10  # >10MB considerado grande
            is_very_large_file = audio_size_mb > 100  # >100MB requer streaming
            
            if is_large_file or self.config.quality_mode:
                # Parâmetros otimizados para QUALIDADE em áudios grandes
                optimized_params = {
                    "language": transcribe_language,
                    "beam_size": self.config.beam_size,  # 5 para melhor qualidade
                    "temperature": 0.0,
                    "compression_ratio_threshold": self.config.compression_ratio_threshold,
                    "log_prob_threshold": self.config.log_prob_threshold,
                    "no_speech_threshold": self.config.no_speech_threshold,
                    "condition_on_previous_text": self.config.condition_on_previous_text,  # True para contexto
                    "word_timestamps": True,
                    "vad_filter": True,
                    "vad_parameters": self.config.vad_parameters  # Usar config completa
                }
                logger.info(f"Modo QUALIDADE ativado - Arquivo grande ({audio_size_mb:.1f}MB) - beam_size={self.config.beam_size}")
            else:
                # Parâmetros otimizados para VELOCIDADE em áudios pequenos
                optimized_params = {
                    "language": transcribe_language,
                    "beam_size": 1,  # Mais rápido
                    "temperature": 0.0,  # Determinístico
                    "compression_ratio_threshold": self.config.compression_ratio_threshold,
                    "log_prob_threshold": self.config.log_prob_threshold,
                    "no_speech_threshold": self.config.no_speech_threshold,
                    "condition_on_previous_text": False,  # Mais rápido
                    "word_timestamps": True,
                    "vad_filter": True,  # Essencial para velocidade
                    "vad_parameters": {
                        "threshold": 0.4,  # Menos rigoroso = mais rápido
                        "min_speech_duration_ms": 100,  # Menor duração
                        "max_speech_duration_s": 20,  # Chunks menores
                        "min_silence_duration_ms": 500,  # Detecção mais rápida
                        "speech_pad_ms": 100  # Menos padding
                    }
                }
                logger.info(f"Modo VELOCIDADE ativado - Arquivo pequeno ({audio_size_mb:.1f}MB)")
            
            # Verificar se deve usar streaming para arquivos muito grandes
            if is_very_large_file and STREAMING_AVAILABLE:
                logger.info(f"Arquivo muito grande ({audio_size_mb:.1f}MB) - usando streaming")
                transcription_result = self._transcribe_with_streaming(
                    audio_path, optimized_params, progress, profiling_session_id
                )
            else:
                logger.info(f"Iniciando transcrição com faster-whisper - beam_size={optimized_params['beam_size']}, vad=True")
                
                transcription_result = self._model.transcribe(
                    str(audio_path),
                    **optimized_params
                )
            
            if progress:
                progress.update(0.2, "Processando áudio...")
            
            # Processar segmentos com progresso em tempo real
            detected_language = None
            total_duration = 0.0
            segment_id = 0
            processed_segments = 0
            
            # Processar resultado do faster-whisper
            # O transcribe() retorna uma tupla (segments, info)
            if progress:
                progress.update(0.2, "Processando segmentos...")
                
            try:
                # Extrair segments e informações
                segments_iter, info = transcription_result
                detected_language = info.language if hasattr(info, 'language') else "pt"
                
                # Calcular duração estimada para progresso
                estimated_duration = getattr(info, 'duration', 300.0)  # Default 5 min se não disponível
                
                if progress:
                    progress.update(0.3, f"Idioma detectado: {detected_language}")
                
                # Processar cada segmento com progresso detalhado
                for segment in segments_iter:
                    if self._cancel_requested:
                        logger.warning("Transcrição cancelada pelo usuário")
                        break
                    
                    self._process_segment(segment, segments, segment_id, detected_language)
                    
                    # Atualizar progresso baseado no tempo processado
                    processed_segments += 1
                    if progress and processed_segments % 5 == 0:  # Atualizar a cada 5 segmentos
                        current_time = segment.end if hasattr(segment, 'end') else 0
                        progress_pct = 0.3 + (0.6 * min(current_time / estimated_duration, 1.0))
                        progress.update(progress_pct, f"Processando: {processed_segments} segmentos")
                    segment_id += 1
                    total_duration = max(total_duration, segment.end)
                    
                    # Evento de profiling a cada 10 segmentos
                    if AUTO_PROFILER_AVAILABLE and profiling_session_id and processed_segments % 10 == 0:
                        try:
                            current_time_processed = time.time() - start_time
                            profiler.add_profiling_event(
                                profiling_session_id,
                                'transcription_progress',
                                f"Processed {processed_segments} segments",
                                {
                                    'segments_processed': processed_segments,
                                    'processing_time': current_time_processed,
                                    'audio_length': total_duration,
                                    'realtime_ratio': current_time_processed / total_duration if total_duration > 0 else 0
                                }
                            )
                        except Exception as e:
                            logger.debug(f"Erro ao adicionar evento de progresso: {e}")
                    
                    # Atualizar progresso periodicamente
                    if progress and segment_id % 5 == 0:
                        estimated_progress = min(0.9, 0.3 + (segment_id * 0.6) / max(segment_id + 20, 50))
                        progress.update(estimated_progress, f"Processando: {segment_id} segmentos")
                        
            except Exception as e:
                logger.error(f"Erro ao processar segmentos: {e}")
                raise TranscriptionError(f"Falha no processamento: {str(e)}")
            
            if self._cancel_requested:
                raise TranscriptionError("Transcrição cancelada pelo usuário")
            
            if progress:
                progress.update(0.95, "Finalizando transcrição...")
            
            # Calcular estatísticas
            processing_time = time.time() - start_time
            confidence_avg = sum(s.confidence for s in segments) / len(segments) if segments else 0.0
            word_count = sum(len(s.text.split()) for s in segments)
            
            # Marcar como sucesso
            performance_metrics['success'] = True
            
            result = TranscriptionResult(
                segments=segments,
                language=detected_language,
                duration=total_duration,
                model_size=self.config.model_size.value,
                processing_time=processing_time,
                confidence_avg=confidence_avg,
                word_count=word_count
            )
            
            if progress:
                progress.update(1.0, "Transcrição concluída!")
            
            # Registrar resultado para limpeza automática
            if MEMORY_MANAGER_AVAILABLE:
                result_size_mb = len(segments) * 0.5  # Estimativa aproximada
                register_for_cleanup(result, 'transcription_results', result_size_mb)
                
                # Otimizar memória após transcrição longa
                if processing_time > 30:  # > 30 segundos
                    memory_manager = get_memory_manager()
                    memory_manager.optimize_memory()
            
            # Enviar métricas para o monitor de performance
            if PERFORMANCE_MONITOR_AVAILABLE:
                try:
                    monitor = get_performance_monitor()
                    
                    # Calcular memória usada (estimativa)
                    memory_used = 0.0
                    if MEMORY_MANAGER_AVAILABLE:
                        current_stats = memory_manager.get_current_stats()
                        memory_used = current_stats.memory_usage_mb
                    
                    # Criar métricas de transcrição
                    trans_metrics = TranscriptionMetrics(
                        duration=total_duration,
                        audio_length=total_duration,
                        model_size=self.config.model_size.value,
                        chunks_count=performance_metrics['chunks_count'],
                        processing_time=processing_time,
                        cache_hits=performance_metrics['cache_hits'],
                        memory_used=memory_used,
                        gpu_used=performance_metrics['gpu_used'],
                        success=performance_metrics['success'],
                        error_message=performance_metrics['error_message']
                    )
                    
                    monitor.add_transcription_metrics(trans_metrics)
                    
                except Exception as e:
                    logger.debug(f"Erro ao enviar métricas de performance: {e}")
            
            # Finalizar profiling session
            if AUTO_PROFILER_AVAILABLE and profiling_session_id:
                try:
                    profiler.add_profiling_event(
                        profiling_session_id,
                        'transcription_completed',
                        f"Transcription completed successfully",
                        {
                            'total_segments': len(segments),
                            'total_duration': processing_time,
                            'audio_length': total_duration,
                            'word_count': word_count,
                            'confidence_avg': confidence_avg,
                            'success': True
                        }
                    )
                    
                    # Finalizar sessão de profiling
                    profiling_report = profiler.end_profiling_session(profiling_session_id)
                    logger.debug(f"Profiling completed - {len(profiling_report.bottlenecks)} bottlenecks detected")
                    
                except Exception as e:
                    logger.debug(f"Erro ao finalizar profiling: {e}")
            
            logger.success(f"Transcrição concluída em {processing_time:.2f}s - {len(segments)} segmentos")
            return result
        
        except Exception as e:
            error_msg = f"Erro na transcrição: {str(e)}"
            logger.error(error_msg)
            
            # Enviar métricas de erro
            if PERFORMANCE_MONITOR_AVAILABLE:
                try:
                    monitor = get_performance_monitor()
                    processing_time = time.time() - start_time
                    
                    performance_metrics['success'] = False
                    performance_metrics['error_message'] = str(e)
                    
                    trans_metrics = TranscriptionMetrics(
                        duration=0.0,
                        audio_length=0.0,
                        model_size=self.config.model_size.value,
                        chunks_count=performance_metrics['chunks_count'],
                        processing_time=processing_time,
                        cache_hits=performance_metrics['cache_hits'],
                        memory_used=0.0,
                        gpu_used=performance_metrics['gpu_used'],
                        success=performance_metrics['success'],
                        error_message=performance_metrics['error_message']
                    )
                    
                    monitor.add_transcription_metrics(trans_metrics)
                    
                except Exception as monitor_error:
                    logger.debug(f"Erro ao enviar métricas de erro: {monitor_error}")
            
            # Finalizar profiling com erro
            if AUTO_PROFILER_AVAILABLE and profiling_session_id:
                try:
                    profiler.add_profiling_event(
                        profiling_session_id,
                        'transcription_error',
                        f"Transcription failed: {str(e)}",
                        {
                            'error_type': type(e).__name__,
                            'error_message': str(e),
                            'processing_time': time.time() - start_time,
                            'success': False
                        }
                    )
                    
                    # Finalizar sessão de profiling
                    profiling_report = profiler.end_profiling_session(profiling_session_id)
                    logger.debug(f"Profiling completed with error - {len(profiling_report.bottlenecks)} bottlenecks detected")
                    
                except Exception as profiling_error:
                    logger.debug(f"Erro ao finalizar profiling com erro: {profiling_error}")
            
            if progress:
                progress.update(0.0, f"Erro: {str(e)}")
            
            raise TranscriptionError(error_msg) from e
    
    def cancel_transcription(self) -> None:
        """Cancela a transcrição em andamento."""
        self._cancel_requested = True
        logger.info("Cancelamento de transcrição solicitado")
    
    def _transcribe_with_streaming(
        self, 
        audio_path: Path, 
        optimized_params: Dict[str, Any],
        progress: Optional[TranscriptionProgress] = None,
        profiling_session_id: Optional[str] = None
    ) -> Generator:
        """
        Transcreve arquivo grande usando streaming otimizado.
        
        Args:
            audio_path: Caminho do arquivo de áudio
            optimized_params: Parâmetros otimizados para transcrição
            progress: Callback de progresso
            profiling_session_id: ID da sessão de profiling
            
        Yields:
            Segmentos de transcrição processados
        """
        if not STREAMING_AVAILABLE:
            logger.warning("Streaming não disponível, usando método tradicional")
            return self._model.transcribe(str(audio_path), **optimized_params)
        
        # Configurar streaming baseado no tamanho do arquivo
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        
        # Configuração inteligente do streaming
        stream_config = StreamConfig()
        
        if file_size_mb > 1000:  # > 1GB
            stream_config.strategy = StreamingStrategy.MEMORY_AWARE
            stream_config.chunk_size_seconds = 60.0
            stream_config.buffer_size_mb = 512
            stream_config.quality_mode = True
        elif file_size_mb > 500:  # > 500MB
            stream_config.strategy = StreamingStrategy.INTELLIGENT
            stream_config.chunk_size_seconds = 45.0
            stream_config.buffer_size_mb = 256
        else:  # 100-500MB
            stream_config.strategy = StreamingStrategy.ADAPTIVE_CHUNK
            stream_config.chunk_size_seconds = 30.0
            stream_config.buffer_size_mb = 128
        
        stream_config.enable_cache = FILE_CACHE_AVAILABLE
        
        logger.info(f"Streaming config: {stream_config.strategy.value}, chunk={stream_config.chunk_size_seconds}s")
        
        # Evento de profiling para início do streaming
        if AUTO_PROFILER_AVAILABLE and profiling_session_id:
            try:
                profiler = get_auto_profiler()
                profiler.add_profiling_event(
                    profiling_session_id,
                    'streaming_started',
                    f"Started streaming transcription: {stream_config.strategy.value}",
                    {
                        'file_size_mb': file_size_mb,
                        'strategy': stream_config.strategy.value,
                        'chunk_size': stream_config.chunk_size_seconds,
                        'buffer_size_mb': stream_config.buffer_size_mb
                    }
                )
            except Exception as e:
                logger.debug(f"Erro ao registrar evento de profiling: {e}")
        
        try:
            # Criar streamer
            streamer = create_audio_streamer(stream_config)
            
            total_segments = []
            chunk_count = 0
            total_chunks_estimated = max(1, int(file_size_mb / 10))  # Estimativa baseada no tamanho
            
            def process_chunk(chunk):
                """Processa chunk individual com Whisper"""
                nonlocal chunk_count
                chunk_count += 1
                
                if self._cancel_requested:
                    return None
                
                # Atualizar progresso
                if progress:
                    progress_value = min(0.9, 0.2 + (chunk_count / total_chunks_estimated) * 0.7)
                    progress.update(
                        progress_value, 
                        f"Transcrevendo chunk {chunk_count}/{total_chunks_estimated} (streaming)..."
                    )
                
                # Criar arquivo temporário para o chunk
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                
                try:
                    # Salvar chunk como arquivo temporário
                    import soundfile as sf
                    sf.write(str(temp_path), chunk.data, chunk.sample_rate)
                    
                    # Transcrever chunk individual
                    chunk_result = self._model.transcribe(str(temp_path), **optimized_params)
                    
                    # Ajustar timestamps baseado no tempo do chunk
                    chunk_segments = []
                    for segment in chunk_result[0]:  # [0] para segmentos
                        adjusted_segment = TranscriptionSegment(
                            id=len(total_segments) + len(chunk_segments),
                            text=segment.text.strip(),
                            start=segment.start + chunk.start_time,
                            end=segment.end + chunk.start_time,
                            confidence=getattr(segment, 'avg_logprob', 0.0) if hasattr(segment, 'avg_logprob') else 0.0
                        )
                        chunk_segments.append(adjusted_segment)
                    
                    logger.debug(f"Chunk {chunk_count}: {len(chunk_segments)} segmentos, {chunk.start_time:.1f}s-{chunk.end_time:.1f}s")
                    return chunk_segments
                    
                except Exception as e:
                    logger.error(f"Erro ao processar chunk {chunk_count}: {e}")
                    return []
                    
                finally:
                    # Limpar arquivo temporário
                    if temp_path.exists():
                        temp_path.unlink()
            
            # Processar chunks com streaming
            for chunk in streamer.stream_file(audio_path, process_chunk):
                if self._cancel_requested:
                    break
                
                # Os segmentos já foram processados pelo process_chunk
                if hasattr(chunk, 'processed_segments'):
                    total_segments.extend(chunk.processed_segments)
            
            # Obter estatísticas de streaming
            streaming_stats = streamer.get_stats()
            
            # Evento de profiling para fim do streaming
            if AUTO_PROFILER_AVAILABLE and profiling_session_id:
                try:
                    profiler.add_profiling_event(
                        profiling_session_id,
                        'streaming_completed',
                        f"Streaming transcription completed: {chunk_count} chunks",
                        {
                            'chunks_processed': chunk_count,
                            'total_segments': len(total_segments),
                            'cache_hit_rate': streaming_stats.get('cache_hit_rate', 0),
                            'processing_time': streaming_stats.get('processing_time', 0),
                            'io_time': streaming_stats.get('io_time', 0)
                        }
                    )
                except Exception as e:
                    logger.debug(f"Erro ao registrar fim do streaming: {e}")
            
            logger.info(f"Streaming concluído: {chunk_count} chunks, {len(total_segments)} segmentos")
            
            # Simular resultado do faster-whisper
            class StreamingResult:
                def __init__(self, segments, language_info):
                    self._segments = segments
                    self.language = language_info.get('language', 'unknown')
                    self.language_probability = language_info.get('language_probability', 0.0)
                
                def __iter__(self):
                    return iter(self._segments)
                
                def __getitem__(self, index):
                    if index == 0:
                        return self._segments
                    elif index == 1:
                        return {
                            'language': self.language,
                            'language_probability': self.language_probability
                        }
                    else:
                        raise IndexError("StreamingResult index out of range")
            
            # Criar resultado compatível
            return StreamingResult(
                total_segments,
                {'language': optimized_params.get('language', 'unknown'), 'language_probability': 0.95}
            )
            
        except Exception as e:
            logger.error(f"Erro durante streaming: {e}")
            # Fallback para método tradicional
            logger.info("Fallback para transcrição tradicional")
            return self._model.transcribe(str(audio_path), **optimized_params)
    
    def cleanup(self) -> None:
        """Limpa recursos do modelo (mas mantém no cache global)."""
        try:
            with self._lock:
                if self._model is not None:
                    # Não deletar o modelo se estiver usando cache - apenas desreferenciar
                    if MODEL_CACHE_AVAILABLE:
                        logger.debug("Modelo mantido no cache global, apenas desreferenciando")
                        self._model = None
                    else:
                        # Cache não disponível, limpar normalmente
                        del self._model
                        self._model = None
                    
                self._model_loaded = False
                
                # Garbage collection leve
                gc.collect()
                
                logger.info("Recursos do transcritor liberados")
        
        except Exception as e:
            logger.warning(f"Erro ao limpar recursos: {e}")


def create_transcriber(
    model_size: WhisperModelSize = WhisperModelSize.BASE,
    language: Optional[str] = None,
    use_gpu: bool = False,  # Mudado para False por padrão para evitar problemas
    quality_mode: bool = False  # Novo parâmetro para modo qualidade
) -> WhisperTranscriber:
    """
    Factory function para criar um transcritor configurado.
    
    Args:
        model_size: Tamanho do modelo Whisper
        language: Idioma específico (None para auto-detecção)
        use_gpu: Se deve usar GPU quando disponível
        quality_mode: Ativa modo alta qualidade (beam_size=5, context=True)
        
    Returns:
        WhisperTranscriber configurado
    """
    # Auto-detectar GPU disponível
    try:
        import torch
        gpu_available = torch.cuda.is_available() and use_gpu
    except ImportError:
        gpu_available = False
    
    config = TranscriptionConfig(
        model_size=model_size,
        language=language,
        device="auto" if gpu_available else "cpu",
        compute_type="float16" if gpu_available else "float32",
        quality_mode=quality_mode
    )
    
    return WhisperTranscriber(config)


def transcribe_audio_file(
    audio_path: Path,
    model_size: WhisperModelSize = WhisperModelSize.BASE,
    language: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> TranscriptionResult:
    """
    Função de conveniência para transcrever um arquivo.
    
    Args:
        audio_path: Caminho para o arquivo
        model_size: Tamanho do modelo
        language: Idioma específico
        progress_callback: Callback para progresso
        
    Returns:
        TranscriptionResult
    """
    progress = TranscriptionProgress(progress_callback) if progress_callback else None
    
    with create_transcriber(model_size, language) as transcriber:
        return transcriber.transcribe_file(audio_path, progress, language)