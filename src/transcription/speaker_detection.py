"""
Sistema de Detecção de Speakers
Módulo para identificação e diarização de speakers usando pyannote.audio.
"""

import gc
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict

from loguru import logger

try:
    import torch
    from pyannote.audio import Pipeline, Model
    from pyannote.core import Annotation, Segment
    PYANNOTE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"pyannote.audio não disponível: {e}")
    PYANNOTE_AVAILABLE = False
    # Mock classes para evitar erros
    class Pipeline: pass
    class Model: pass
    class Annotation: pass
    class Segment: pass


class SpeakerDetectionError(Exception):
    """Exceções relacionadas à detecção de speakers."""
    pass


class ModelNotAvailableError(SpeakerDetectionError):
    """Erro quando modelo pyannote não está disponível."""
    pass


class DiarizationModel(Enum):
    """Modelos disponíveis para diarização."""
    DEFAULT = "pyannote/speaker-diarization-3.1"
    SEGMENTATION = "pyannote/segmentation-3.0"


@dataclass
class SpeakerSegment:
    """Representa um segmento com speaker identificado."""
    start: float
    end: float
    speaker: str
    confidence: float = 0.0
    
    @property
    def duration(self) -> float:
        """Duração do segmento em segundos."""
        return max(0.0, self.end - self.start)


@dataclass 
class SpeakerInfo:
    """Informações sobre um speaker detectado."""
    id: str
    label: str  # Nome personalizado
    total_duration: float = 0.0
    segment_count: int = 0
    avg_confidence: float = 0.0
    first_appearance: float = 0.0
    last_appearance: float = 0.0
    
    def update_stats(self, segments: List[SpeakerSegment]) -> None:
        """Atualiza estatísticas baseado nos segmentos."""
        speaker_segments = [seg for seg in segments if seg.speaker == self.id]
        
        if not speaker_segments:
            return
        
        self.segment_count = len(speaker_segments)
        self.total_duration = sum(seg.duration for seg in speaker_segments)
        self.avg_confidence = sum(seg.confidence for seg in speaker_segments) / len(speaker_segments)
        self.first_appearance = min(seg.start for seg in speaker_segments)
        self.last_appearance = max(seg.end for seg in speaker_segments)


@dataclass
class DiarizationResult:
    """Resultado da diarização de speakers."""
    segments: List[SpeakerSegment] = field(default_factory=list)
    speakers: Dict[str, SpeakerInfo] = field(default_factory=dict)
    total_duration: float = 0.0
    processing_time: float = 0.0
    num_speakers: int = 0
    
    def __post_init__(self):
        """Calcula estatísticas após inicialização."""
        self._update_statistics()
    
    def _update_statistics(self) -> None:
        """Atualiza estatísticas dos speakers."""
        # Agrupar segmentos por speaker
        speaker_segments = defaultdict(list)
        for segment in self.segments:
            speaker_segments[segment.speaker].append(segment)
        
        # Criar/atualizar SpeakerInfo
        for speaker_id, segments in speaker_segments.items():
            if speaker_id not in self.speakers:
                self.speakers[speaker_id] = SpeakerInfo(
                    id=speaker_id,
                    label=f"Speaker {speaker_id}"
                )
            
            self.speakers[speaker_id].update_stats(self.segments)
        
        self.num_speakers = len(self.speakers)
        
        if self.segments:
            self.total_duration = max(seg.end for seg in self.segments)
    
    def get_speaker_at_time(self, timestamp: float) -> Optional[str]:
        """Retorna o speaker ativo em um determinado timestamp."""
        for segment in self.segments:
            if segment.start <= timestamp <= segment.end:
                return segment.speaker
        return None
    
    def get_dominant_speaker(self) -> Optional[str]:
        """Retorna o speaker que mais falou."""
        if not self.speakers:
            return None
        
        return max(
            self.speakers.keys(),
            key=lambda spk: self.speakers[spk].total_duration
        )
    
    def rename_speaker(self, old_id: str, new_label: str) -> bool:
        """Renomeia um speaker."""
        if old_id not in self.speakers:
            return False
        
        self.speakers[old_id].label = new_label
        return True


class SpeakerDetectionProgress:
    """Callback para progresso da detecção de speakers."""
    
    def __init__(self, callback: Optional[Callable[[float, str], None]] = None):
        self.callback = callback
        self._current_progress = 0.0
        self._current_status = "Iniciando detecção de speakers..."
    
    def update(self, progress: float, status: str = ""):
        """Atualiza o progresso."""
        self._current_progress = progress
        self._current_status = status or self._current_status
        
        if self.callback:
            self.callback(progress, self._current_status)
    
    @property
    def progress(self) -> float:
        return self._current_progress
    
    @property
    def status(self) -> str:
        return self._current_status


class SpeakerDetector:
    """
    Detector de speakers usando pyannote.audio.
    
    Identifica quantos speakers únicos existem em um áudio e 
    quando cada um está falando.
    """
    
    def __init__(
        self,
        model_name: str = DiarizationModel.DEFAULT.value,
        device: str = "auto",
        use_auth_token: Optional[str] = None
    ):
        if not PYANNOTE_AVAILABLE:
            raise ModelNotAvailableError(
                "pyannote.audio não está disponível. "
                "Instale com: pip install pyannote.audio"
            )
        
        self.model_name = model_name
        self.device = self._detect_device() if device == "auto" else device
        self.use_auth_token = use_auth_token
        
        self._pipeline: Optional[Pipeline] = None
        self._model_loaded = False
        self._cancel_requested = False
        self._lock = threading.Lock()
        
        logger.info(f"SpeakerDetector inicializado - Modelo: {model_name}")
        logger.info(f"Dispositivo: {self.device}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    @property
    def is_model_loaded(self) -> bool:
        """Verifica se o modelo está carregado."""
        return self._model_loaded and self._pipeline is not None
    
    def _detect_device(self) -> str:
        """Detecta o melhor dispositivo disponível."""
        try:
            if torch.cuda.is_available():
                logger.info("CUDA detectado para speaker detection")
                return "cuda"
            else:
                logger.info("Usando CPU para speaker detection")
                return "cpu"
        except:
            return "cpu"
    
    def load_model(self, progress: Optional[SpeakerDetectionProgress] = None) -> None:
        """
        Carrega o pipeline de diarização.
        
        Args:
            progress: Callback opcional para progresso
            
        Raises:
            ModelNotAvailableError: Se falhar ao carregar o modelo
        """
        if self.is_model_loaded:
            logger.debug("Pipeline já está carregado")
            return
        
        try:
            if progress:
                progress.update(0.1, "Carregando pipeline de diarização...")
            
            logger.info(f"Carregando pipeline: {self.model_name}")
            
            with self._lock:
                # Tentar carregar o pipeline
                try:
                    self._pipeline = Pipeline.from_pretrained(
                        self.model_name,
                        use_auth_token=self.use_auth_token
                    )
                except Exception as e:
                    # Se falhar, tentar modelo alternativo
                    logger.warning(f"Falha ao carregar {self.model_name}: {e}")
                    logger.info("Tentando modelo de segmentação alternativo...")
                    
                    if progress:
                        progress.update(0.3, "Tentando modelo alternativo...")
                    
                    self._pipeline = Pipeline.from_pretrained(
                        DiarizationModel.SEGMENTATION.value,
                        use_auth_token=self.use_auth_token
                    )
                
                if progress:
                    progress.update(0.7, "Configurando dispositivo...")
                
                # Configurar dispositivo
                if hasattr(self._pipeline, 'to'):
                    self._pipeline = self._pipeline.to(torch.device(self.device))
                
                self._model_loaded = True
                
                if progress:
                    progress.update(1.0, "Pipeline carregado com sucesso!")
                
                logger.success(f"Pipeline de speaker detection carregado")
        
        except Exception as e:
            error_msg = f"Falha ao carregar pipeline: {str(e)}"
            logger.error(error_msg)
            
            if progress:
                progress.update(0.0, f"Erro: {str(e)}")
            
            raise ModelNotAvailableError(error_msg) from e
    
    def detect_speakers(
        self,
        audio_path: Path,
        progress: Optional[SpeakerDetectionProgress] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> DiarizationResult:
        """
        Detecta speakers em um arquivo de áudio.
        
        Args:
            audio_path: Caminho para o arquivo de áudio
            progress: Callback opcional para progresso
            min_speakers: Número mínimo de speakers esperados
            max_speakers: Número máximo de speakers esperados
            
        Returns:
            DiarizationResult com os speakers detectados
            
        Raises:
            SpeakerDetectionError: Se falhar na detecção
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
                progress.update(0.1, "Analisando arquivo de áudio...")
            
            logger.info(f"Iniciando detecção de speakers: {audio_path}")
            
            # Configurar parâmetros do pipeline
            pipeline_params = {}
            if min_speakers is not None:
                pipeline_params['min_speakers'] = min_speakers
            if max_speakers is not None:
                pipeline_params['max_speakers'] = max_speakers
            
            if progress:
                progress.update(0.3, "Executando diarização...")
            
            # Executar diarização
            diarization: Annotation = self._pipeline(str(audio_path), **pipeline_params)
            
            if self._cancel_requested:
                raise SpeakerDetectionError("Detecção cancelada pelo usuário")
            
            if progress:
                progress.update(0.8, "Processando resultados...")
            
            # Converter para nosso formato
            segments = []
            for segment, _, speaker in diarization.itertracks(yield_label=True):
                if self._cancel_requested:
                    break
                
                speaker_segment = SpeakerSegment(
                    start=segment.start,
                    end=segment.end,
                    speaker=speaker,
                    confidence=1.0  # pyannote não fornece confidence por padrão
                )
                segments.append(speaker_segment)
            
            if self._cancel_requested:
                raise SpeakerDetectionError("Detecção cancelada pelo usuário")
            
            # Criar resultado
            processing_time = time.time() - start_time
            
            result = DiarizationResult(
                segments=segments,
                processing_time=processing_time
            )
            
            if progress:
                progress.update(1.0, f"Detecção concluída! {result.num_speakers} speakers encontrados")
            
            logger.success(
                f"Speaker detection concluída em {processing_time:.2f}s - "
                f"{result.num_speakers} speakers, {len(segments)} segmentos"
            )
            
            return result
        
        except Exception as e:
            error_msg = f"Erro na detecção de speakers: {str(e)}"
            logger.error(error_msg)
            
            if progress:
                progress.update(0.0, f"Erro: {str(e)}")
            
            raise SpeakerDetectionError(error_msg) from e
    
    def cancel_detection(self) -> None:
        """Cancela a detecção em andamento."""
        self._cancel_requested = True
        logger.info("Cancelamento de speaker detection solicitado")
    
    def cleanup(self) -> None:
        """Limpa recursos do modelo."""
        try:
            with self._lock:
                if self._pipeline is not None:
                    del self._pipeline
                    self._pipeline = None
                
                self._model_loaded = False
                
                # Forçar garbage collection
                gc.collect()
                
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                logger.info("Recursos do speaker detector liberados")
        
        except Exception as e:
            logger.warning(f"Erro ao limpar recursos: {e}")


def merge_transcription_with_speakers(
    transcription_segments: List,  # TranscriptionSegment
    speaker_segments: List[SpeakerSegment],
    overlap_threshold: float = 0.5
) -> List:
    """
    Combina segmentos de transcrição com detecção de speakers.
    
    Args:
        transcription_segments: Segmentos da transcrição (Whisper)
        speaker_segments: Segmentos dos speakers (pyannote)
        overlap_threshold: Threshold para considerar sobreposição
        
    Returns:
        Lista de segmentos de transcrição com speakers atribuídos
    """
    merged_segments = []
    
    for trans_seg in transcription_segments:
        # Encontrar o speaker que mais se sobrepõe com este segmento
        best_speaker = None
        best_overlap = 0.0
        
        for spk_seg in speaker_segments:
            # Calcular sobreposição
            overlap_start = max(trans_seg.start, spk_seg.start)
            overlap_end = min(trans_seg.end, spk_seg.end)
            overlap_duration = max(0.0, overlap_end - overlap_start)
            
            # Calcular porcentagem de sobreposição
            trans_duration = max(0.1, trans_seg.end - trans_seg.start)
            overlap_pct = overlap_duration / trans_duration
            
            if overlap_pct > best_overlap and overlap_pct >= overlap_threshold:
                best_overlap = overlap_pct
                best_speaker = spk_seg.speaker
        
        # Atualizar segmento com speaker
        trans_seg.speaker = best_speaker
        merged_segments.append(trans_seg)
    
    return merged_segments


# Factory functions
def create_speaker_detector(
    model_name: str = DiarizationModel.DEFAULT.value,
    device: str = "auto",
    use_auth_token: Optional[str] = None
) -> SpeakerDetector:
    """
    Factory function para criar um detector de speakers.
    
    Args:
        model_name: Nome do modelo pyannote
        device: Dispositivo para processamento
        use_auth_token: Token de autenticação Hugging Face
        
    Returns:
        SpeakerDetector configurado
    """
    return SpeakerDetector(model_name, device, use_auth_token)


def detect_speakers_in_audio(
    audio_path: Path,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None
) -> DiarizationResult:
    """
    Função de conveniência para detectar speakers em um arquivo.
    
    Args:
        audio_path: Caminho para o arquivo
        progress_callback: Callback para progresso
        min_speakers: Número mínimo de speakers
        max_speakers: Número máximo de speakers
        
    Returns:
        DiarizationResult
    """
    progress = SpeakerDetectionProgress(progress_callback) if progress_callback else None
    
    with create_speaker_detector() as detector:
        return detector.detect_speakers(audio_path, progress, min_speakers, max_speakers)