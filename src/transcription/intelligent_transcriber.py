"""
Transcritor Inteligente com Speaker Detection
Sistema integrado que combina Whisper + pyannote.audio para transcrição completa.
"""

import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, replace

from loguru import logger

from .transcriber import (
    WhisperTranscriber, TranscriptionResult, TranscriptionConfig, 
    TranscriptionProgress, WhisperModelSize, TranscriptionError
)
from .speaker_detection import (
    SpeakerDetector, DiarizationResult, SpeakerDetectionProgress,
    SpeakerDetectionError, ModelNotAvailableError, merge_transcription_with_speakers
)


@dataclass
class IntelligentTranscriptionConfig:
    """Configuração para transcrição inteligente com speakers."""
    # Configurações do Whisper
    whisper_model: WhisperModelSize = WhisperModelSize.BASE
    whisper_language: Optional[str] = None
    whisper_device: str = "auto"
    
    # Configurações de Speaker Detection
    enable_speaker_detection: bool = True
    speaker_model: str = "pyannote/speaker-diarization-3.1"
    speaker_device: str = "auto"
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None
    
    # Configurações gerais
    overlap_threshold: float = 0.5  # Threshold para merger de segmentos
    
    def to_transcription_config(self) -> TranscriptionConfig:
        """Converte para TranscriptionConfig do Whisper."""
        from .transcriber import TranscriptionConfig
        
        return TranscriptionConfig(
            model_size=self.whisper_model,
            language=self.whisper_language,
            device=self.whisper_device
        )


class IntelligentProgress:
    """Progress tracking para transcrição inteligente."""
    
    def __init__(self, callback: Optional[Callable[[float, str], None]] = None):
        self.callback = callback
        self._whisper_weight = 0.6  # 60% do tempo na transcrição
        self._speaker_weight = 0.4  # 40% do tempo na diarização
        
        self._current_phase = "idle"
        self._whisper_progress = 0.0
        self._speaker_progress = 0.0
    
    def _update_total_progress(self):
        """Calcula progresso total baseado nas fases."""
        if self._current_phase == "transcription":
            total = self._whisper_progress * self._whisper_weight
        elif self._current_phase == "speaker_detection":
            total = self._whisper_weight + (self._speaker_progress * self._speaker_weight)
        elif self._current_phase == "merging":
            total = 0.95
        elif self._current_phase == "completed":
            total = 1.0
        else:
            total = 0.0
        
        return min(1.0, max(0.0, total))
    
    def update_whisper(self, progress: float, status: str):
        """Atualiza progresso do Whisper."""
        self._current_phase = "transcription"
        self._whisper_progress = progress
        
        total_progress = self._update_total_progress()
        full_status = f"[Transcrição] {status}"
        
        if self.callback:
            self.callback(total_progress, full_status)
    
    def update_speaker(self, progress: float, status: str):
        """Atualiza progresso do Speaker Detection."""
        self._current_phase = "speaker_detection"
        self._speaker_progress = progress
        
        total_progress = self._update_total_progress()
        full_status = f"[Speakers] {status}"
        
        if self.callback:
            self.callback(total_progress, full_status)
    
    def update_merge(self, status: str = "Combinando transcrição com speakers..."):
        """Atualiza para fase de merge."""
        self._current_phase = "merging"
        total_progress = self._update_total_progress()
        
        if self.callback:
            self.callback(total_progress, f"[Integração] {status}")
    
    def complete(self, status: str = "Transcrição inteligente concluída!"):
        """Marca como completo."""
        self._current_phase = "completed"
        
        if self.callback:
            self.callback(1.0, status)


@dataclass
class IntelligentTranscriptionResult:
    """Resultado da transcrição inteligente."""
    transcription: TranscriptionResult
    diarization: Optional[DiarizationResult] = None
    processing_time: float = 0.0
    speakers_detected: bool = False
    
    @property
    def has_speakers(self) -> bool:
        """Verifica se há informação de speakers."""
        return self.speakers_detected and self.diarization is not None
    
    @property
    def num_speakers(self) -> int:
        """Número de speakers detectados."""
        if self.has_speakers:
            return self.diarization.num_speakers
        return 0
    
    @property
    def speaker_info(self) -> Dict[str, Any]:
        """Informações dos speakers detectados."""
        if not self.has_speakers:
            return {}
        
        info = {}
        for speaker_id, speaker in self.diarization.speakers.items():
            info[speaker_id] = {
                "label": speaker.label,
                "duration": speaker.total_duration,
                "segments": speaker.segment_count,
                "confidence": speaker.avg_confidence,
                "percentage": (speaker.total_duration / self.diarization.total_duration) * 100
            }
        
        return info
    
    def get_formatted_text_with_speakers(self) -> str:
        """Retorna texto formatado com speakers identificados."""
        lines = []
        
        for segment in self.transcription.segments:
            timestamp = f"[{self._format_time(segment.start)} -> {self._format_time(segment.end)}]"
            
            if segment.speaker:
                # Buscar label personalizado se disponível
                speaker_label = segment.speaker
                if self.has_speakers and segment.speaker in self.diarization.speakers:
                    speaker_label = self.diarization.speakers[segment.speaker].label
                
                lines.append(f"{timestamp} {speaker_label}: {segment.text.strip()}")
            else:
                lines.append(f"{timestamp} {segment.text.strip()}")
        
        return "\n".join(lines)
    
    def _format_time(self, seconds: float) -> str:
        """Formata tempo em MM:SS."""
        mins, secs = divmod(int(seconds), 60)
        return f"{mins:02d}:{secs:02d}"


class IntelligentTranscriber:
    """
    Transcritor inteligente que combina Whisper com Speaker Detection.
    
    Executa transcrição de áudio e identificação de speakers de forma integrada,
    produzindo transcrições com speakers identificados.
    """
    
    def __init__(self, config: Optional[IntelligentTranscriptionConfig] = None):
        self.config = config or IntelligentTranscriptionConfig()
        
        self._whisper_transcriber: Optional[WhisperTranscriber] = None
        self._speaker_detector: Optional[SpeakerDetector] = None
        
        logger.info("IntelligentTranscriber inicializado")
        logger.info(f"Speaker detection: {'habilitado' if self.config.enable_speaker_detection else 'desabilitado'}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def transcribe_with_speakers(
        self,
        audio_path: Path,
        progress: Optional[IntelligentProgress] = None
    ) -> IntelligentTranscriptionResult:
        """
        Executa transcrição inteligente com detecção de speakers.
        
        Args:
            audio_path: Caminho para o arquivo de áudio
            progress: Callback opcional para progresso
            
        Returns:
            IntelligentTranscriptionResult com transcrição e speakers
            
        Raises:
            TranscriptionError: Se falhar na transcrição
            SpeakerDetectionError: Se falhar na detecção (quando habilitada)
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_path}")
        
        start_time = time.time()
        logger.info(f"Iniciando transcrição inteligente: {audio_path}")
        
        try:
            # ETAPA 1: Transcrição com Whisper
            logger.info("Etapa 1: Transcrevendo áudio com Whisper...")
            
            whisper_config = self.config.to_transcription_config()
            self._whisper_transcriber = WhisperTranscriber(whisper_config)
            
            # Criar progress callback para Whisper
            whisper_progress = None
            if progress:
                whisper_progress = TranscriptionProgress(progress.update_whisper)
            
            transcription_result = self._whisper_transcriber.transcribe_file(
                audio_path, whisper_progress, self.config.whisper_language
            )
            
            logger.success(f"Transcrição concluída: {len(transcription_result.segments)} segmentos")
            
            # ETAPA 2: Detecção de Speakers (se habilitada)
            diarization_result = None
            speakers_detected = False
            
            if self.config.enable_speaker_detection:
                try:
                    logger.info("Etapa 2: Detectando speakers...")
                    
                    self._speaker_detector = SpeakerDetector(
                        model_name=self.config.speaker_model,
                        device=self.config.speaker_device
                    )
                    
                    # Criar progress callback para Speaker Detection
                    speaker_progress = None
                    if progress:
                        speaker_progress = SpeakerDetectionProgress(progress.update_speaker)
                    
                    diarization_result = self._speaker_detector.detect_speakers(
                        audio_path,
                        speaker_progress,
                        self.config.min_speakers,
                        self.config.max_speakers
                    )
                    
                    speakers_detected = True
                    logger.success(f"Speaker detection concluída: {diarization_result.num_speakers} speakers")
                    
                except (SpeakerDetectionError, ModelNotAvailableError) as e:
                    logger.warning(f"Falha na detecção de speakers: {e}")
                    logger.info("Continuando apenas com transcrição...")
                    speakers_detected = False
            
            # ETAPA 3: Combinar resultados
            if speakers_detected and diarization_result:
                if progress:
                    progress.update_merge("Combinando transcrição com speakers...")
                
                logger.info("Etapa 3: Combinando transcrição com speakers...")
                
                # Fazer merge dos segmentos
                merged_segments = merge_transcription_with_speakers(
                    transcription_result.segments,
                    diarization_result.segments,
                    self.config.overlap_threshold
                )
                
                # Atualizar resultado da transcrição
                transcription_result.segments = merged_segments
                
                logger.success("Merge concluído com sucesso")
            
            # Finalizar
            total_time = time.time() - start_time
            
            result = IntelligentTranscriptionResult(
                transcription=transcription_result,
                diarization=diarization_result,
                processing_time=total_time,
                speakers_detected=speakers_detected
            )
            
            if progress:
                if speakers_detected:
                    progress.complete(f"Concluído! {result.num_speakers} speakers, {len(transcription_result.segments)} segmentos")
                else:
                    progress.complete(f"Concluído! {len(transcription_result.segments)} segmentos")
            
            logger.success(f"Transcrição inteligente concluída em {total_time:.2f}s")
            
            return result
        
        except Exception as e:
            error_msg = f"Erro na transcrição inteligente: {str(e)}"
            logger.error(error_msg)
            raise TranscriptionError(error_msg) from e
    
    def cleanup(self):
        """Limpa recursos dos transcritores."""
        try:
            if self._whisper_transcriber:
                self._whisper_transcriber.cleanup()
                self._whisper_transcriber = None
            
            if self._speaker_detector:
                self._speaker_detector.cleanup()
                self._speaker_detector = None
            
            logger.info("Recursos do transcritor inteligente liberados")
        
        except Exception as e:
            logger.warning(f"Erro ao limpar recursos: {e}")


# Factory functions
def create_intelligent_transcriber(
    whisper_model: WhisperModelSize = WhisperModelSize.BASE,
    enable_speakers: bool = True,
    language: Optional[str] = None
) -> IntelligentTranscriber:
    """
    Factory function para criar um transcritor inteligente.
    
    Args:
        whisper_model: Modelo Whisper a usar
        enable_speakers: Se deve detectar speakers
        language: Idioma específico
        
    Returns:
        IntelligentTranscriber configurado
    """
    config = IntelligentTranscriptionConfig(
        whisper_model=whisper_model,
        whisper_language=language,
        enable_speaker_detection=enable_speakers
    )
    
    return IntelligentTranscriber(config)


def transcribe_with_speakers(
    audio_path: Path,
    whisper_model: WhisperModelSize = WhisperModelSize.BASE,
    enable_speakers: bool = True,
    language: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> IntelligentTranscriptionResult:
    """
    Função de conveniência para transcrição inteligente.
    
    Args:
        audio_path: Caminho para o arquivo
        whisper_model: Modelo Whisper
        enable_speakers: Se deve detectar speakers
        language: Idioma específico
        progress_callback: Callback para progresso
        
    Returns:
        IntelligentTranscriptionResult
    """
    progress = IntelligentProgress(progress_callback) if progress_callback else None
    
    with create_intelligent_transcriber(whisper_model, enable_speakers, language) as transcriber:
        return transcriber.transcribe_with_speakers(audio_path, progress)