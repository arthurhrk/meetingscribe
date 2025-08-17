"""
Domain Models para MeetingScribe

Modelos de dados usando Pydantic seguindo padrões do config.py atual.
Todos os modelos herdam de BaseModel com validação automática,
serialização JSON e integração com Settings existente.

Author: MeetingScribe Team
Version: 1.1.0
Python: >=3.8
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Literal
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, validator, root_validator
from pydantic.types import conint, confloat, constr

# Importação compatível com config.py atual
from config import settings


# =============================================================================
# ENUMS E CONSTANTES
# =============================================================================

class RecordingStatus(str, Enum):
    """Status de gravação compatível com audio_recorder.py atual."""
    IDLE = "idle"
    INITIALIZING = "initializing" 
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    ERROR = "error"


class TranscriptionStatus(str, Enum):
    """Status de transcrição compatível com transcriber.py atual."""
    PENDING = "pending"
    LOADING_MODEL = "loading_model"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AudioFormat(str, Enum):
    """Formatos de áudio suportados."""
    WAV = "wav"
    MP3 = "mp3" 
    M4A = "m4a"
    FLAC = "flac"
    OGG = "ogg"


class ExportFormat(str, Enum):
    """Formatos de exportação compatíveis com exporter.py atual."""
    TXT = "txt"
    JSON = "json"
    SRT = "srt"
    VTT = "vtt"
    XML = "xml"
    CSV = "csv"


class WhisperModelSize(str, Enum):
    """Tamanhos de modelo Whisper compatíveis com transcriber.py atual."""
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"


class DeviceType(str, Enum):
    """Tipos de dispositivo de áudio."""
    INPUT = "input"
    OUTPUT = "output"
    LOOPBACK = "loopback"
    UNKNOWN = "unknown"


# =============================================================================
# MODELOS BASE
# =============================================================================

class BaseTimestampedModel(BaseModel):
    """Modelo base com timestamps automáticos."""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        """Atualiza timestamp automaticamente."""
        return v or datetime.now()


class BaseFileModel(BaseModel):
    """Modelo base para arquivos com validação de existência."""
    path: Path
    filename: str = Field(..., min_length=1)
    size_bytes: conint(ge=0)
    created_at: datetime = Field(default_factory=datetime.now)
    
    @validator('path')
    def validate_path_exists(cls, v):
        """Valida que o arquivo existe no filesystem."""
        if not v.exists():
            raise ValueError(f"Arquivo não encontrado: {v}")
        if not v.is_file():
            raise ValueError(f"Path não é um arquivo: {v}")
        return v
    
    @validator('filename', pre=True, always=True)
    def set_filename_from_path(cls, v, values):
        """Define filename automaticamente a partir do path."""
        if 'path' in values and values['path']:
            return values['path'].name
        return v
    
    @validator('size_bytes', pre=True, always=True)
    def set_size_from_file(cls, v, values):
        """Define tamanho automaticamente a partir do arquivo."""
        if v is None and 'path' in values and values['path']:
            try:
                return values['path'].stat().st_size
            except (OSError, AttributeError):
                return 0
        return v
    
    @property
    def size_mb(self) -> float:
        """Tamanho em MB."""
        return self.size_bytes / (1024 * 1024)
    
    @property
    def extension(self) -> str:
        """Extensão do arquivo."""
        return self.path.suffix.lower().lstrip('.')


# =============================================================================
# MODELOS DE DISPOSITIVO
# =============================================================================

class AudioDevice(BaseModel):
    """
    Dispositivo de áudio compatível com device_manager.py atual.
    Integra com Settings para valores padrão.
    """
    
    # Identificação do dispositivo
    id: str = Field(..., description="ID único do dispositivo")
    index: conint(ge=0) = Field(..., description="Índice do dispositivo no sistema")
    name: constr(min_length=1) = Field(..., description="Nome do dispositivo")
    
    # Capacidades de áudio
    max_input_channels: conint(ge=0) = Field(0, description="Canais de entrada máximos")
    max_output_channels: conint(ge=0) = Field(0, description="Canais de saída máximos")
    
    # Configurações de áudio com defaults do Settings
    sample_rate: conint(ge=8000, le=192000) = Field(
        default_factory=lambda: settings.audio_sample_rate,
        description="Taxa de amostragem em Hz"
    )
    channels: conint(ge=1, le=8) = Field(
        default_factory=lambda: settings.audio_channels,
        description="Número de canais"
    )
    
    # Informações do sistema
    host_api: str = Field(..., description="API de host (WASAPI, MME, etc.)")
    device_type: DeviceType = Field(DeviceType.UNKNOWN, description="Tipo do dispositivo")
    
    # Status e flags
    is_default: bool = Field(False, description="Dispositivo padrão do sistema")
    is_loopback: bool = Field(False, description="Dispositivo de loopback")
    is_available: bool = Field(True, description="Dispositivo disponível")
    
    # Metadados
    driver_version: Optional[str] = Field(None, description="Versão do driver")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('device_type', pre=True, always=True)
    def determine_device_type(cls, v, values):
        """Determina tipo do dispositivo baseado nas capacidades."""
        if v != DeviceType.UNKNOWN:
            return v
            
        max_input = values.get('max_input_channels', 0)
        max_output = values.get('max_output_channels', 0)
        is_loopback = values.get('is_loopback', False)
        
        if is_loopback:
            return DeviceType.LOOPBACK
        elif max_input > 0 and max_output == 0:
            return DeviceType.INPUT
        elif max_output > 0 and max_input == 0:
            return DeviceType.OUTPUT
        else:
            return DeviceType.UNKNOWN
    
    @validator('sample_rate')
    def validate_sample_rate_compatibility(cls, v):
        """Valida compatibilidade da sample rate."""
        common_rates = [8000, 16000, 22050, 44100, 48000, 96000, 192000]
        if v not in common_rates:
            # Warning: taxa não comum, mas não impede
            pass
        return v
    
    def supports_recording(self) -> bool:
        """Verifica se dispositivo suporta gravação."""
        return (self.max_input_channels > 0 or 
                self.is_loopback or 
                self.device_type in [DeviceType.INPUT, DeviceType.LOOPBACK])
    
    def supports_playback(self) -> bool:
        """Verifica se dispositivo suporta reprodução."""
        return (self.max_output_channels > 0 or 
                self.device_type == DeviceType.OUTPUT)
    
    class Config:
        """Configuração Pydantic."""
        json_encoders = {
            DeviceType: lambda v: v.value
        }


# =============================================================================
# MODELOS DE GRAVAÇÃO
# =============================================================================

class RecordingConfiguration(BaseModel):
    """
    Configuração de gravação compatível com audio_recorder.py atual.
    """
    
    # Configurações básicas
    sample_rate: conint(ge=8000, le=192000) = Field(
        default_factory=lambda: settings.audio_sample_rate
    )
    channels: conint(ge=1, le=8) = Field(
        default_factory=lambda: settings.audio_channels
    )
    chunk_size: conint(ge=256, le=8192) = Field(1024, description="Tamanho do buffer em frames")
    
    # Formato de saída
    audio_format: AudioFormat = Field(AudioFormat.WAV)
    bit_depth: Literal[16, 24, 32] = Field(16, description="Profundidade de bits")
    
    # Limites e controles
    max_duration_seconds: Optional[conint(ge=1)] = Field(None, description="Duração máxima")
    auto_stop_silence_seconds: Optional[confloat(ge=1.0)] = Field(None)
    
    # Diretório de saída
    output_directory: Path = Field(
        default_factory=lambda: settings.recordings_dir,
        description="Diretório para gravações"
    )
    
    # Configurações avançadas
    noise_reduction: bool = Field(False)
    auto_gain_control: bool = Field(False)
    enable_monitoring: bool = Field(True)
    
    @validator('output_directory')
    def validate_output_directory(cls, v):
        """Valida diretório de saída."""
        if not v.exists():
            v.mkdir(parents=True, exist_ok=True)
        if not v.is_dir():
            raise ValueError(f"Output directory deve ser um diretório: {v}")
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_audio_configuration(cls, values):
        """Valida configuração de áudio completa."""
        sample_rate = values.get('sample_rate')
        channels = values.get('channels')
        chunk_size = values.get('chunk_size')
        
        # Validar chunk size baseado na sample rate
        if sample_rate and chunk_size:
            min_chunk = sample_rate // 100  # Mínimo 10ms
            max_chunk = sample_rate // 10   # Máximo 100ms
            if not (min_chunk <= chunk_size <= max_chunk):
                values['chunk_size'] = min(max(chunk_size, min_chunk), max_chunk)
        
        return values


class RecordingSession(BaseTimestampedModel):
    """
    Sessão de gravação compatível com RecordingStats atual.
    """
    
    # Identificação única
    id: UUID = Field(default_factory=uuid4, description="ID único da sessão")
    
    # Configuração da sessão
    device: AudioDevice = Field(..., description="Dispositivo de gravação")
    configuration: RecordingConfiguration = Field(..., description="Configuração de gravação")
    
    # Controle de estado
    status: RecordingStatus = Field(RecordingStatus.IDLE)
    
    # Timestamps
    start_time: Optional[datetime] = Field(None, description="Início da gravação")
    end_time: Optional[datetime] = Field(None, description="Fim da gravação")
    pause_duration_seconds: float = Field(0.0, description="Tempo total pausado")
    
    # Estatísticas
    samples_recorded: conint(ge=0) = Field(0, description="Total de samples gravados")
    peak_amplitude: confloat(ge=0.0, le=1.0) = Field(0.0, description="Amplitude pico")
    average_amplitude: confloat(ge=0.0, le=1.0) = Field(0.0, description="Amplitude média")
    
    # Arquivo resultante
    output_file: Optional[Path] = Field(None, description="Arquivo de saída")
    
    # Erro (se houver)
    error_message: Optional[str] = Field(None)
    error_code: Optional[str] = Field(None)
    
    @validator('end_time')
    def validate_end_after_start(cls, v, values):
        """Valida que end_time é posterior a start_time."""
        start_time = values.get('start_time')
        if v and start_time and v <= start_time:
            raise ValueError("end_time deve ser posterior a start_time")
        return v
    
    @property
    def duration_seconds(self) -> float:
        """Duração da gravação em segundos."""
        if self.start_time and self.end_time:
            total = (self.end_time - self.start_time).total_seconds()
            return max(0, total - self.pause_duration_seconds)
        return 0.0
    
    @property
    def is_active(self) -> bool:
        """Verifica se sessão está ativa."""
        return self.status in [RecordingStatus.RECORDING, RecordingStatus.PAUSED]
    
    @property
    def is_completed(self) -> bool:
        """Verifica se sessão foi completada com sucesso."""
        return self.status == RecordingStatus.COMPLETED and self.output_file is not None
    
    def get_recording_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas compatíveis com RecordingStats atual."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration_seconds,
            "samples_recorded": self.samples_recorded,
            "peak_amplitude": self.peak_amplitude,
            "average_amplitude": self.average_amplitude,
            "file_size": self.output_file.stat().st_size if self.output_file and self.output_file.exists() else 0,
            "filename": self.output_file.name if self.output_file else None
        }


# =============================================================================
# MODELOS DE ARQUIVO
# =============================================================================

class AudioFile(BaseFileModel):
    """
    Arquivo de áudio com validação e metadados.
    Compatível com estrutura storage/recordings/ atual.
    """
    
    # Propriedades de áudio
    duration_seconds: confloat(ge=0.0) = Field(..., description="Duração em segundos")
    sample_rate: conint(ge=8000, le=192000) = Field(..., description="Taxa de amostragem")
    channels: conint(ge=1, le=8) = Field(..., description="Número de canais")
    bit_depth: conint(ge=8, le=32) = Field(16, description="Profundidade de bits")
    audio_format: AudioFormat = Field(..., description="Formato do arquivo")
    
    # Metadados de gravação
    recording_session_id: Optional[UUID] = Field(None, description="ID da sessão de gravação")
    device_name: Optional[str] = Field(None, description="Nome do dispositivo usado")
    
    # Análise de qualidade
    peak_amplitude: confloat(ge=0.0, le=1.0) = Field(0.0)
    rms_amplitude: confloat(ge=0.0, le=1.0) = Field(0.0)
    signal_to_noise_ratio: Optional[confloat(ge=0.0)] = Field(None)
    
    # Metadados adicionais
    title: Optional[str] = Field(None, description="Título do arquivo")
    description: Optional[str] = Field(None, description="Descrição")
    tags: List[str] = Field(default_factory=list, description="Tags")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('audio_format', pre=True, always=True)
    def set_format_from_extension(cls, v, values):
        """Define formato automaticamente da extensão."""
        if 'path' in values and values['path']:
            ext = values['path'].suffix.lower().lstrip('.')
            try:
                return AudioFormat(ext)
            except ValueError:
                pass
        return v or AudioFormat.WAV
    
    @validator('duration_seconds', pre=True)
    def validate_duration_positive(cls, v):
        """Valida que duração é positiva."""
        if v <= 0:
            raise ValueError("Duração deve ser positiva")
        return v
    
    @property
    def duration_formatted(self) -> str:
        """Duração formatada (HH:MM:SS)."""
        hours, remainder = divmod(int(self.duration_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
    
    @property
    def bitrate_kbps(self) -> int:
        """Bitrate estimado em kbps."""
        return int((self.sample_rate * self.channels * self.bit_depth) / 1000)
    
    def get_file_info(self) -> Dict[str, Any]:
        """Informações completas do arquivo."""
        return {
            "path": str(self.path),
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "size_mb": self.size_mb,
            "duration_seconds": self.duration_seconds,
            "duration_formatted": self.duration_formatted,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bit_depth": self.bit_depth,
            "audio_format": self.audio_format.value,
            "bitrate_kbps": self.bitrate_kbps,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# MODELOS DE TRANSCRIÇÃO
# =============================================================================

class TranscriptionSegment(BaseModel):
    """
    Segmento de transcrição compatível com transcriber.py atual.
    """
    
    id: conint(ge=0) = Field(..., description="ID do segmento")
    text: constr(min_length=1) = Field(..., description="Texto transcrito")
    
    # Timestamps
    start_time: confloat(ge=0.0) = Field(..., description="Tempo de início em segundos")
    end_time: confloat(ge=0.0) = Field(..., description="Tempo de fim em segundos")
    
    # Qualidade e confiança
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Nível de confiança")
    
    # Metadados opcionais
    speaker_id: Optional[str] = Field(None, description="ID do falante identificado")
    speaker_name: Optional[str] = Field(None, description="Nome do falante")
    language: Optional[str] = Field(None, description="Idioma detectado")
    
    # Dados técnicos
    tokens: List[str] = Field(default_factory=list, description="Tokens da transcrição")
    word_timestamps: List[Dict[str, Any]] = Field(default_factory=list)
    
    @validator('end_time')
    def validate_end_after_start(cls, v, values):
        """Valida que end_time é posterior a start_time."""
        start_time = values.get('start_time')
        if start_time is not None and v <= start_time:
            raise ValueError("end_time deve ser posterior a start_time")
        return v
    
    @property
    def duration_seconds(self) -> float:
        """Duração do segmento."""
        return self.end_time - self.start_time
    
    @property
    def words_per_minute(self) -> float:
        """Palavras por minuto no segmento."""
        word_count = len(self.text.split())
        if self.duration_seconds > 0:
            return (word_count / self.duration_seconds) * 60
        return 0.0
    
    def format_timestamp(self, time_seconds: float) -> str:
        """Formata timestamp para exibição."""
        minutes, seconds = divmod(int(time_seconds), 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    @property
    def formatted_text(self) -> str:
        """Texto formatado com timestamp."""
        start_fmt = self.format_timestamp(self.start_time)
        end_fmt = self.format_timestamp(self.end_time)
        speaker = f" ({self.speaker_name})" if self.speaker_name else ""
        return f"[{start_fmt} -> {end_fmt}]{speaker} {self.text.strip()}"


class TranscriptionResult(BaseTimestampedModel):
    """
    Resultado de transcrição compatível com transcriber.py atual.
    Integra com Settings para valores padrão.
    """
    
    # Arquivo fonte
    audio_file: AudioFile = Field(..., description="Arquivo de áudio transcrito")
    
    # Resultado da transcrição
    segments: List[TranscriptionSegment] = Field(default_factory=list)
    full_text: str = Field("", description="Texto completo concatenado")
    
    # Configuração usada
    model_used: WhisperModelSize = Field(
        default_factory=lambda: WhisperModelSize(settings.whisper_model),
        description="Modelo Whisper usado"
    )
    language: str = Field(
        default_factory=lambda: settings.whisper_language,
        description="Idioma da transcrição"
    )
    
    # Métricas de qualidade
    confidence_average: confloat(ge=0.0, le=1.0) = Field(0.0)
    confidence_minimum: confloat(ge=0.0, le=1.0) = Field(0.0)
    
    # Estatísticas
    total_duration: confloat(ge=0.0) = Field(0.0, description="Duração total em segundos")
    processing_time: confloat(ge=0.0) = Field(0.0, description="Tempo de processamento")
    word_count: conint(ge=0) = Field(0, description="Total de palavras")
    
    # Detecção de speakers (se habilitada)
    speakers_detected: List[str] = Field(default_factory=list)
    speaker_segments: Dict[str, List[int]] = Field(default_factory=dict)
    
    # Metadados
    transcription_job_id: Optional[UUID] = Field(None)
    export_formats: List[ExportFormat] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('full_text', pre=True, always=True)
    def generate_full_text(cls, v, values):
        """Gera texto completo a partir dos segmentos."""
        if not v and 'segments' in values:
            segments = values['segments']
            if segments:
                return " ".join([seg.text.strip() for seg in segments])
        return v
    
    @validator('word_count', pre=True, always=True)
    def calculate_word_count(cls, v, values):
        """Calcula contagem de palavras."""
        if v == 0 and 'full_text' in values:
            full_text = values['full_text']
            if full_text:
                return len(full_text.split())
        return v
    
    @validator('confidence_average', pre=True, always=True)
    def calculate_average_confidence(cls, v, values):
        """Calcula confiança média."""
        if v == 0.0 and 'segments' in values:
            segments = values['segments']
            if segments:
                total_confidence = sum(seg.confidence for seg in segments)
                return total_confidence / len(segments)
        return v
    
    @validator('confidence_minimum', pre=True, always=True)
    def calculate_minimum_confidence(cls, v, values):
        """Calcula confiança mínima."""
        if v == 0.0 and 'segments' in values:
            segments = values['segments']
            if segments:
                return min(seg.confidence for seg in segments)
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_consistency(cls, values):
        """Valida consistência entre campos."""
        segments = values.get('segments', [])
        audio_file = values.get('audio_file')
        
        if segments and audio_file:
            # Validar que segmentos não excedem duração do áudio
            max_end_time = max((seg.end_time for seg in segments), default=0.0)
            if max_end_time > audio_file.duration_seconds * 1.1:  # 10% tolerance
                raise ValueError("Segmentos excedem duração do áudio")
        
        return values
    
    @property
    def formatted_text(self) -> str:
        """Texto formatado com timestamps por segmento."""
        return "\n".join([seg.formatted_text for seg in self.segments])
    
    @property
    def words_per_minute(self) -> float:
        """Palavras por minuto médias."""
        if self.total_duration > 0:
            return (self.word_count / self.total_duration) * 60
        return 0.0
    
    @property
    def processing_speed_ratio(self) -> float:
        """Ratio velocidade processamento vs duração áudio."""
        if self.processing_time > 0:
            return self.total_duration / self.processing_time
        return 0.0
    
    def get_segments_by_speaker(self, speaker_id: str) -> List[TranscriptionSegment]:
        """Retorna segmentos de um falante específico."""
        return [seg for seg in self.segments if seg.speaker_id == speaker_id]
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Métricas de qualidade da transcrição."""
        return {
            "confidence_average": self.confidence_average,
            "confidence_minimum": self.confidence_minimum,
            "word_count": self.word_count,
            "words_per_minute": self.words_per_minute,
            "processing_speed_ratio": self.processing_speed_ratio,
            "speakers_count": len(self.speakers_detected),
            "segments_count": len(self.segments),
            "model_used": self.model_used.value,
            "language": self.language
        }


# =============================================================================
# MODELOS DE EXPORTAÇÃO
# =============================================================================

class ExportJob(BaseTimestampedModel):
    """Job de exportação de transcrição."""
    
    id: UUID = Field(default_factory=uuid4)
    transcription_result: TranscriptionResult = Field(...)
    formats: List[ExportFormat] = Field(...)
    output_directory: Path = Field(default_factory=lambda: settings.exports_dir)
    
    # Status
    status: Literal["pending", "processing", "completed", "failed"] = Field("pending")
    progress: confloat(ge=0.0, le=1.0) = Field(0.0)
    
    # Resultados
    exported_files: List[Path] = Field(default_factory=list)
    error_message: Optional[str] = Field(None)
    
    @validator('output_directory')
    def validate_export_directory(cls, v):
        """Valida diretório de exportação."""
        if not v.exists():
            v.mkdir(parents=True, exist_ok=True)
        return v


# =============================================================================
# MODELOS DE SISTEMA
# =============================================================================

class SystemStatus(BaseModel):
    """Status do sistema compatível com system_check.py atual."""
    
    # Status geral
    overall_status: Literal["healthy", "warning", "error"] = Field("healthy")
    
    # Componentes
    python_version: str = Field(...)
    dependencies_status: Dict[str, bool] = Field(default_factory=dict)
    audio_system_status: Dict[str, Any] = Field(default_factory=dict)
    storage_status: Dict[str, Any] = Field(default_factory=dict)
    
    # Recursos
    available_devices: List[AudioDevice] = Field(default_factory=list)
    available_models: List[WhisperModelSize] = Field(default_factory=list)
    
    # Métricas
    uptime_seconds: confloat(ge=0.0) = Field(0.0)
    total_recordings: conint(ge=0) = Field(0)
    total_transcriptions: conint(ge=0) = Field(0)
    
    # Timestamps
    last_check: datetime = Field(default_factory=datetime.now)
    
    def to_system_check_format(self) -> Dict[str, Any]:
        """Converte para formato compatível com system_check.py."""
        return {
            "overall": "success" if self.overall_status == "healthy" else "error",
            "components": [
                {
                    "name": name,
                    "status": "ok" if status else "error",
                    "icon": "✅" if status else "❌"
                }
                for name, status in self.dependencies_status.items()
            ],
            "hardware": {
                "audio_devices": len(self.available_devices),
                "whisper_models": len(self.available_models)
            }
        }


# =============================================================================
# CONFIGURAÇÃO GLOBAL PYDANTIC
# =============================================================================

# Configuração global para todos os modelos
class GlobalConfig:
    """Configuração global Pydantic."""
    
    # Serialização
    json_encoders = {
        datetime: lambda v: v.isoformat(),
        Path: lambda v: str(v),
        UUID: lambda v: str(v),
    }
    
    # Validação
    validate_assignment = True
    use_enum_values = True
    arbitrary_types_allowed = True
    
    # Schemas
    schema_extra = {
        "examples": {}
    }


# Aplicar configuração a todos os modelos
for model_class in [
    AudioDevice, RecordingConfiguration, RecordingSession, 
    AudioFile, TranscriptionSegment, TranscriptionResult,
    ExportJob, SystemStatus
]:
    if hasattr(model_class, 'Config'):
        # Merge configurations
        for attr, value in GlobalConfig.__dict__.items():
            if not attr.startswith('_'):
                setattr(model_class.Config, attr, value)
    else:
        model_class.Config = GlobalConfig


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "RecordingStatus",
    "TranscriptionStatus", 
    "AudioFormat",
    "ExportFormat",
    "WhisperModelSize",
    "DeviceType",
    
    # Base Models
    "BaseTimestampedModel",
    "BaseFileModel",
    
    # Domain Models
    "AudioDevice",
    "RecordingConfiguration",
    "RecordingSession",
    "AudioFile",
    "TranscriptionSegment",
    "TranscriptionResult",
    "ExportJob",
    "SystemStatus",
]