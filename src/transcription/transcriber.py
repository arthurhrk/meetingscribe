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
                        self._model, cache_hit = create_cached_model(
                            self.config.model_size.value,
                            device,
                            compute_type
                        )
                        
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
            
            # Configurar parâmetros
            transcribe_language = language or self.config.language
            
            segments = []
            
            # Detectar se é áudio longo (>5 min) para usar modo qualidade
            audio_size_mb = audio_path.stat().st_size / (1024 * 1024)
            is_large_file = audio_size_mb > 10  # >10MB considerado grande
            
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
            
            logger.success(f"Transcrição concluída em {processing_time:.2f}s - {len(segments)} segmentos")
            return result
        
        except Exception as e:
            error_msg = f"Erro na transcrição: {str(e)}"
            logger.error(error_msg)
            
            if progress:
                progress.update(0.0, f"Erro: {str(e)}")
            
            raise TranscriptionError(error_msg) from e
    
    def cancel_transcription(self) -> None:
        """Cancela a transcrição em andamento."""
        self._cancel_requested = True
        logger.info("Cancelamento de transcrição solicitado")
    
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