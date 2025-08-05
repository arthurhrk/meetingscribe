"""
Sistema de Transcrição com Whisper
Módulo principal para transcrição de áudio usando faster-whisper.
"""

import time
import gc
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
    """Configuração para transcrição."""
    model_size: WhisperModelSize = WhisperModelSize.BASE
    language: Optional[str] = None  # None para auto-detecção
    compute_type: str = "float16"  # float16, float32, int8
    device: str = "auto"  # auto, cpu, cuda
    beam_size: int = 5
    temperature: float = 0.0
    compression_ratio_threshold: float = 2.4
    log_prob_threshold: float = -1.0
    no_speech_threshold: float = 0.6
    condition_on_previous_text: bool = True
    word_timestamps: bool = True
    vad_filter: bool = True
    vad_parameters: Dict[str, Any] = field(default_factory=lambda: {
        "threshold": 0.5,
        "min_speech_duration_ms": 250,
        "max_speech_duration_s": 30,
        "min_silence_duration_ms": 2000,
        "speech_pad_ms": 400
    })


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
        
        logger.info(f"Transcritor inicializado - Modelo: {self.config.model_size.value}")
    
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
        Carrega o modelo Whisper.
        
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
                
                logger.info(f"Usando dispositivo: {device}")
                logger.info(f"Tipo de computação: {self.config.compute_type}")
                
                if progress:
                    progress.update(0.3, f"Baixando modelo {self.config.model_size.value}...")
                
                self._model = WhisperModel(
                    self.config.model_size.value,
                    device=device,
                    compute_type=self.config.compute_type,
                    download_root=None,  # Usar diretório padrão
                    local_files_only=False
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
            if progress:
                progress.update(0.1, "Preparando transcrição...")
            
            logger.info(f"Iniciando transcrição: {audio_path}")
            
            # Configurar parâmetros
            transcribe_language = language or self.config.language
            
            segments = []
            segment_generator = self._model.transcribe(
                str(audio_path),
                language=transcribe_language,
                beam_size=self.config.beam_size,
                temperature=self.config.temperature,
                compression_ratio_threshold=self.config.compression_ratio_threshold,
                log_prob_threshold=self.config.log_prob_threshold,
                no_speech_threshold=self.config.no_speech_threshold,
                condition_on_previous_text=self.config.condition_on_previous_text,
                word_timestamps=self.config.word_timestamps,
                vad_filter=self.config.vad_filter,
                vad_parameters=self.config.vad_parameters
            )
            
            if progress:
                progress.update(0.2, "Processando áudio...")
            
            # Processar segmentos
            detected_language = None
            total_duration = 0.0
            segment_id = 0
            
            for segment_info, segment_list in segment_generator:
                # Informações do áudio
                if detected_language is None:
                    detected_language = segment_info.language
                    if progress:
                        progress.update(0.3, f"Idioma detectado: {detected_language}")
                
                # Processar cada segmento
                for segment in segment_list:
                    if self._cancel_requested:
                        logger.warning("Transcrição cancelada pelo usuário")
                        break
                    
                    # Criar segmento de transcrição
                    transcription_segment = TranscriptionSegment(
                        id=segment_id,
                        text=segment.text,
                        start=segment.start,
                        end=segment.end,
                        confidence=getattr(segment, 'avg_logprob', 0.0),
                        language=detected_language
                    )
                    
                    segments.append(transcription_segment)
                    total_duration = max(total_duration, segment.end)
                    segment_id += 1
                    
                    # Atualizar progresso
                    if progress and total_duration > 0:
                        # Estimativa grosseira do progresso
                        estimated_progress = min(0.9, 0.3 + (total_duration / (total_duration + 10)) * 0.6)
                        progress.update(estimated_progress, f"Processando: {len(segments)} segmentos")
                
                if self._cancel_requested:
                    break
            
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
        """Limpa recursos do modelo."""
        try:
            with self._lock:
                if self._model is not None:
                    del self._model
                    self._model = None
                    
                self._model_loaded = False
                
                # Forçar garbage collection
                gc.collect()
                
                if TORCH_AVAILABLE and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                logger.info("Recursos do transcritor liberados")
        
        except Exception as e:
            logger.warning(f"Erro ao limpar recursos: {e}")


def create_transcriber(
    model_size: WhisperModelSize = WhisperModelSize.BASE,
    language: Optional[str] = None,
    use_gpu: bool = True
) -> WhisperTranscriber:
    """
    Factory function para criar um transcritor configurado.
    
    Args:
        model_size: Tamanho do modelo Whisper
        language: Idioma específico (None para auto-detecção)
        use_gpu: Se deve usar GPU quando disponível
        
    Returns:
        WhisperTranscriber configurado
    """
    config = TranscriptionConfig(
        model_size=model_size,
        language=language,
        device="auto" if use_gpu else "cpu",
        compute_type="float16" if use_gpu else "float32"
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