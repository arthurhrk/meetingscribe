"""
MeetingScribe Interfaces Package

Interfaces que se integram perfeitamente com o código atual, mantendo compatibilidade
total com config.Settings, Loguru logging, Rich console e error handling patterns.

Author: MeetingScribe Team
Version: 1.1.0
Python: >=3.8
"""

from typing import Protocol, runtime_checkable, Optional, List, Dict, Any, Union, AsyncGenerator, Callable
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import asyncio

# Compatibilidade com sistema existente
from config import Settings
from loguru import Logger
from rich.console import Console
from rich.progress import Progress, TaskID

# Import tipos existentes para compatibilidade
try:
    from device_manager import AudioDevice
    from audio_recorder import RecordingConfig, RecordingStats
    from src.transcription.transcriber import TranscriptionResult, TranscriptionSegment, WhisperModelSize
    from src.transcription.exporter import ExportFormat
except ImportError:
    # Fallback types if modules not available during development
    AudioDevice = Any
    RecordingConfig = Any
    RecordingStats = Any
    TranscriptionResult = Any
    TranscriptionSegment = Any
    WhisperModelSize = Any
    ExportFormat = Any


# =============================================================================
# ENUMS E CONSTANTES
# =============================================================================

class RecordingState(Enum):
    """Estados de gravação compatíveis com audio_recorder.py atual."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    ERROR = "error"


class TranscriptionState(Enum):
    """Estados de transcrição compatíveis com transcriber.py atual."""
    PENDING = "pending"
    LOADING_MODEL = "loading_model"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StorageType(Enum):
    """Tipos de storage compatíveis com estrutura atual."""
    RECORDING = "recording"
    TRANSCRIPTION = "transcription"
    EXPORT = "export"
    CACHE = "cache"


# =============================================================================
# DATA MODELS COMPATÍVEIS
# =============================================================================

@dataclass
class RecordingSession:
    """
    Sessão de gravação compatível com RecordingStats atual.
    Mantém interface com audio_recorder.py existente.
    """
    session_id: str
    device: AudioDevice
    config: RecordingConfig
    state: RecordingState = RecordingState.IDLE
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    file_path: Optional[Path] = None
    stats: Optional[RecordingStats] = None
    error_message: Optional[str] = None
    
    @property
    def is_active(self) -> bool:
        """Verifica se sessão está ativa."""
        return self.state in [RecordingState.RECORDING, RecordingState.PAUSED]
    
    @property
    def is_completed(self) -> bool:
        """Verifica se sessão foi completada."""
        return self.state == RecordingState.COMPLETED


@dataclass
class AudioFile:
    """
    Arquivo de áudio compatível com sistema atual.
    Integra com storage/recordings/ existente.
    """
    path: Path
    filename: str
    size_bytes: int
    duration_seconds: float
    sample_rate: int
    channels: int
    format: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def size_mb(self) -> float:
        """Tamanho em MB."""
        return self.size_bytes / (1024 * 1024)
    
    @property
    def duration_formatted(self) -> str:
        """Duração formatada (MM:SS)."""
        minutes, seconds = divmod(int(self.duration_seconds), 60)
        return f"{minutes:02d}:{seconds:02d}"


@dataclass
class TranscriptionJob:
    """
    Job de transcrição compatível com TranscriptionResult atual.
    """
    job_id: str
    audio_file: AudioFile
    model_size: WhisperModelSize
    language: Optional[str]
    state: TranscriptionState = TranscriptionState.PENDING
    progress: float = 0.0
    result: Optional[TranscriptionResult] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def processing_time(self) -> Optional[float]:
        """Tempo de processamento em segundos."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class StorageLocation:
    """
    Localização de storage compatível com estrutura atual.
    """
    type: StorageType
    path: Path
    relative_path: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# CALLBACK TYPES
# =============================================================================

# Compatível com callbacks existentes em audio_recorder.py
RecordingProgressCallback = Callable[[RecordingSession], None]
RecordingErrorCallback = Callable[[RecordingSession, Exception], None]

# Compatível com callbacks existentes em transcriber.py
TranscriptionProgressCallback = Callable[[TranscriptionJob], None]
TranscriptionCompleteCallback = Callable[[TranscriptionJob], None]
TranscriptionErrorCallback = Callable[[TranscriptionJob, Exception], None]


# =============================================================================
# INTERFACE BASE
# =============================================================================

@runtime_checkable
class IBaseComponent(Protocol):
    """
    Interface base para todos os componentes.
    Garante compatibilidade com config.Settings, Logger e Console atuais.
    """
    
    def __init__(
        self, 
        settings: Settings, 
        logger: Logger, 
        console: Optional[Console] = None
    ) -> None:
        """
        Inicializa componente com dependências do sistema atual.
        
        Args:
            settings: Instância Settings do config.py atual
            logger: Logger Loguru configurado no main.py
            console: Console Rich para feedback visual (opcional)
        """
        ...
    
    @property
    def is_initialized(self) -> bool:
        """Verifica se componente foi inicializado corretamente."""
        ...
    
    def get_status(self) -> Dict[str, Any]:
        """
        Retorna status do componente para integração com system_check.py.
        
        Returns:
            Dict compatível com system_check JSON output
        """
        ...
    
    def cleanup(self) -> None:
        """Limpa recursos do componente."""
        ...


# =============================================================================
# INTERFACE AUDIO CAPTURE ENGINE
# =============================================================================

@runtime_checkable
class IAudioCaptureEngine(IBaseComponent, Protocol):
    """
    Interface para engine de captura de áudio.
    Mantém compatibilidade total com device_manager.py e audio_recorder.py atuais.
    """
    
    def __init__(
        self, 
        settings: Settings, 
        logger: Logger, 
        console: Optional[Console] = None
    ) -> None:
        """
        Inicializa engine com configurações atuais.
        
        Args:
            settings: Settings do config.py atual
            logger: Logger configurado
            console: Console Rich para progress feedback
        """
        ...
    
    async def initialize_devices(self) -> List[AudioDevice]:
        """
        Inicializa e detecta dispositivos WASAPI.
        Compatível com device_manager.py atual.
        
        Returns:
            Lista de AudioDevice compatível com sistema atual
            
        Raises:
            AudioDeviceError: Erro de detecção de dispositivos
            WASAPINotAvailableError: WASAPI não disponível
        """
        ...
    
    def list_devices(self) -> List[AudioDevice]:
        """
        Lista dispositivos disponíveis.
        Compatível com DeviceManager.list_all_devices() atual.
        
        Returns:
            Lista de dispositivos de áudio
        """
        ...
    
    def get_default_device(self) -> Optional[AudioDevice]:
        """
        Obtém dispositivo padrão.
        Compatível com DeviceManager.get_default_speakers() atual.
        
        Returns:
            Dispositivo padrão ou None se não encontrado
        """
        ...
    
    async def start_recording(
        self,
        device_id: Optional[str] = None,
        filename: Optional[str] = None,
        config: Optional[RecordingConfig] = None,
        progress_callback: Optional[RecordingProgressCallback] = None,
        error_callback: Optional[RecordingErrorCallback] = None
    ) -> RecordingSession:
        """
        Inicia gravação de áudio.
        Compatível com AudioRecorder.start_recording() atual.
        
        Args:
            device_id: ID do dispositivo (None = padrão)
            filename: Nome do arquivo (None = automático)
            config: Configuração (None = padrão do settings)
            progress_callback: Callback de progresso
            error_callback: Callback de erro
            
        Returns:
            Sessão de gravação ativa
            
        Raises:
            RecordingInProgressError: Gravação já em andamento
            AudioRecorderError: Erro na gravação
        """
        ...
    
    def stop_recording(self, session: RecordingSession) -> AudioFile:
        """
        Para gravação e retorna arquivo.
        Compatível com AudioRecorder.stop_recording() atual.
        
        Args:
            session: Sessão de gravação ativa
            
        Returns:
            Arquivo de áudio gravado
            
        Raises:
            AudioRecorderError: Erro ao parar gravação
        """
        ...
    
    def pause_recording(self, session: RecordingSession) -> None:
        """
        Pausa gravação atual.
        
        Args:
            session: Sessão de gravação ativa
        """
        ...
    
    def resume_recording(self, session: RecordingSession) -> None:
        """
        Resume gravação pausada.
        
        Args:
            session: Sessão de gravação pausada
        """
        ...
    
    def get_active_sessions(self) -> List[RecordingSession]:
        """
        Retorna sessões de gravação ativas.
        
        Returns:
            Lista de sessões ativas
        """
        ...
    
    def get_recording_stats(self, session: RecordingSession) -> RecordingStats:
        """
        Obtém estatísticas de gravação.
        Compatível com RecordingStats atual.
        
        Args:
            session: Sessão de gravação
            
        Returns:
            Estatísticas compatíveis com audio_recorder.py
        """
        ...


# =============================================================================
# INTERFACE TRANSCRIPTION ENGINE
# =============================================================================

@runtime_checkable
class ITranscriptionEngine(IBaseComponent, Protocol):
    """
    Interface para engine de transcrição.
    Mantém compatibilidade total com transcriber.py e intelligent_transcriber.py atuais.
    """
    
    def __init__(
        self, 
        settings: Settings, 
        logger: Logger, 
        console: Optional[Console] = None
    ) -> None:
        """
        Inicializa engine com configurações Whisper atuais.
        
        Args:
            settings: Settings com configurações whisper_* atuais
            logger: Logger configurado
            console: Console para progress bars
        """
        ...
    
    async def initialize_model(
        self, 
        model_size: Optional[WhisperModelSize] = None
    ) -> bool:
        """
        Inicializa modelo Whisper.
        Compatível com create_transcriber() atual.
        
        Args:
            model_size: Tamanho do modelo (None = usar settings.whisper_model)
            
        Returns:
            True se inicialização bem-sucedida
            
        Raises:
            ModelNotAvailableError: Modelo não disponível
            TranscriptionError: Erro na inicialização
        """
        ...
    
    def get_supported_models(self) -> List[WhisperModelSize]:
        """
        Lista modelos Whisper suportados.
        Compatível com WhisperModelSize enum atual.
        
        Returns:
            Lista de modelos disponíveis
        """
        ...
    
    def get_model_info(self, model_size: WhisperModelSize) -> Dict[str, Any]:
        """
        Informações do modelo.
        
        Args:
            model_size: Tamanho do modelo
            
        Returns:
            Dict com informações (size, memory, speed, etc.)
        """
        ...
    
    async def transcribe(
        self,
        audio_file: AudioFile,
        model_size: Optional[WhisperModelSize] = None,
        language: Optional[str] = None,
        progress_callback: Optional[TranscriptionProgressCallback] = None,
        complete_callback: Optional[TranscriptionCompleteCallback] = None,
        error_callback: Optional[TranscriptionErrorCallback] = None
    ) -> TranscriptionJob:
        """
        Transcreve arquivo de áudio.
        Compatível com transcriber.transcribe_audio() atual.
        
        Args:
            audio_file: Arquivo para transcrição
            model_size: Modelo Whisper (None = settings)
            language: Idioma (None = auto-detect)
            progress_callback: Callback de progresso
            complete_callback: Callback de conclusão
            error_callback: Callback de erro
            
        Returns:
            Job de transcrição
            
        Raises:
            TranscriptionError: Erro na transcrição
        """
        ...
    
    async def transcribe_with_speakers(
        self,
        audio_file: AudioFile,
        enable_speaker_detection: bool = True,
        **kwargs
    ) -> TranscriptionJob:
        """
        Transcrição com detecção de speakers.
        Compatível com intelligent_transcriber.py atual.
        
        Args:
            audio_file: Arquivo para transcrição
            enable_speaker_detection: Habilitar detecção de speakers
            **kwargs: Argumentos adicionais para transcribe()
            
        Returns:
            Job de transcrição com speakers identificados
        """
        ...
    
    def get_active_jobs(self) -> List[TranscriptionJob]:
        """
        Lista jobs de transcrição ativos.
        
        Returns:
            Lista de jobs em execução
        """
        ...
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancela job de transcrição.
        
        Args:
            job_id: ID do job para cancelar
            
        Returns:
            True se cancelamento bem-sucedido
        """
        ...
    
    def get_job_status(self, job_id: str) -> Optional[TranscriptionJob]:
        """
        Status de job específico.
        
        Args:
            job_id: ID do job
            
        Returns:
            Job ou None se não encontrado
        """
        ...


# =============================================================================
# INTERFACE STORAGE MANAGER
# =============================================================================

@runtime_checkable
class IStorageManager(IBaseComponent, Protocol):
    """
    Interface para gerenciamento de storage.
    Mantém compatibilidade total com estrutura storage/ atual e file_manager.py.
    """
    
    def __init__(
        self, 
        settings: Settings, 
        logger: Logger, 
        console: Optional[Console] = None
    ) -> None:
        """
        Inicializa storage com diretórios atuais.
        
        Args:
            settings: Settings com paths storage_* atuais
            logger: Logger configurado
            console: Console para feedback
        """
        ...
    
    def validate_storage_structure(self) -> Dict[str, bool]:
        """
        Valida estrutura de diretórios.
        Compatível com system_check.check_directory_structure() atual.
        
        Returns:
            Dict com status de cada diretório
        """
        ...
    
    def save_recording(
        self,
        audio_data: bytes,
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AudioFile:
        """
        Salva gravação no storage/recordings/.
        Compatível com convenções de nomeação atuais.
        
        Args:
            audio_data: Dados de áudio em bytes
            filename: Nome do arquivo (None = automático)
            metadata: Metadados adicionais
            
        Returns:
            AudioFile salvo
            
        Raises:
            StorageError: Erro ao salvar arquivo
        """
        ...
    
    def save_transcription(
        self,
        result: TranscriptionResult,
        audio_file: AudioFile,
        filename: Optional[str] = None
    ) -> StorageLocation:
        """
        Salva transcrição no storage/transcriptions/.
        Compatível com formato JSON atual e save_transcription_txt().
        
        Args:
            result: Resultado da transcrição
            audio_file: Arquivo de áudio original
            filename: Nome do arquivo (None = automático)
            
        Returns:
            Localização do arquivo salvo
            
        Raises:
            StorageError: Erro ao salvar transcrição
        """
        ...
    
    def export_transcription(
        self,
        result: TranscriptionResult,
        formats: List[ExportFormat],
        output_dir: Optional[Path] = None
    ) -> List[StorageLocation]:
        """
        Exporta transcrição em múltiplos formatos.
        Compatível com exporter.py atual.
        
        Args:
            result: Resultado para exportar
            formats: Lista de formatos (TXT, JSON, SRT, etc.)
            output_dir: Diretório de saída (None = storage/exports/)
            
        Returns:
            Lista de arquivos exportados
            
        Raises:
            ExportError: Erro na exportação
        """
        ...
    
    def list_recordings(
        self,
        limit: Optional[int] = None,
        filter_by: Optional[Dict[str, Any]] = None
    ) -> List[AudioFile]:
        """
        Lista gravações disponíveis.
        
        Args:
            limit: Limite de resultados
            filter_by: Filtros (date, size, duration, etc.)
            
        Returns:
            Lista de arquivos de áudio
        """
        ...
    
    def list_transcriptions(
        self,
        limit: Optional[int] = None,
        filter_by: Optional[Dict[str, Any]] = None
    ) -> List[StorageLocation]:
        """
        Lista transcrições disponíveis.
        Compatível com file_manager.list_transcriptions() atual.
        
        Args:
            limit: Limite de resultados
            filter_by: Filtros aplicados
            
        Returns:
            Lista de transcrições
        """
        ...
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Estatísticas de storage.
        
        Returns:
            Dict com estatísticas (size, count, etc.) por tipo
        """
        ...
    
    def cleanup_old_files(
        self,
        storage_type: StorageType,
        days_old: int = 30,
        dry_run: bool = True
    ) -> List[Path]:
        """
        Remove arquivos antigos.
        
        Args:
            storage_type: Tipo de storage para limpar
            days_old: Arquivos mais antigos que X dias
            dry_run: Apenas simular (não deletar)
            
        Returns:
            Lista de arquivos que seriam/foram removidos
        """
        ...
    
    def backup_storage(
        self,
        backup_dir: Path,
        include_types: Optional[List[StorageType]] = None
    ) -> bool:
        """
        Backup de storage.
        
        Args:
            backup_dir: Diretório de backup
            include_types: Tipos a incluir (None = todos)
            
        Returns:
            True se backup bem-sucedido
        """
        ...


# =============================================================================
# INTERFACE UI CONTROLLER
# =============================================================================

@runtime_checkable
class IUIController(IBaseComponent, Protocol):
    """
    Interface para controle de UI.
    Compatível com Rich console patterns atuais em main.py.
    """
    
    def __init__(
        self, 
        settings: Settings, 
        logger: Logger, 
        console: Console
    ) -> None:
        """
        Inicializa controller com Console Rich atual.
        
        Args:
            settings: Settings do config.py
            logger: Logger configurado
            console: Console Rich global do main.py
        """
        ...
    
    def show_welcome_message(self) -> None:
        """
        Exibe mensagem de boas-vindas.
        Compatível com main.show_welcome_message() atual.
        """
        ...
    
    def show_recording_progress(
        self,
        session: RecordingSession,
        show_live_stats: bool = True
    ) -> Progress:
        """
        Exibe progresso de gravação.
        
        Args:
            session: Sessão de gravação
            show_live_stats: Mostrar estatísticas em tempo real
            
        Returns:
            Progress bar Rich
        """
        ...
    
    def show_transcription_progress(
        self,
        job: TranscriptionJob,
        show_model_info: bool = True
    ) -> Progress:
        """
        Exibe progresso de transcrição.
        
        Args:
            job: Job de transcrição
            show_model_info: Mostrar informações do modelo
            
        Returns:
            Progress bar Rich
        """
        ...
    
    def display_transcription_result(
        self,
        result: TranscriptionResult,
        show_confidence: bool = True,
        show_speakers: bool = True
    ) -> None:
        """
        Exibe resultado de transcrição formatado.
        
        Args:
            result: Resultado da transcrição
            show_confidence: Mostrar níveis de confiança
            show_speakers: Mostrar informações de speakers
        """
        ...
    
    def show_system_status(
        self,
        status_data: Dict[str, Any],
        detailed: bool = False
    ) -> None:
        """
        Exibe status do sistema.
        Compatível com system_check.py output.
        
        Args:
            status_data: Dados de status
            detailed: Modo detalhado
        """
        ...
    
    def show_error_message(
        self,
        error: Exception,
        context: Optional[str] = None,
        show_traceback: bool = False
    ) -> None:
        """
        Exibe mensagem de erro formatada.
        
        Args:
            error: Exceção ocorrida
            context: Contexto do erro
            show_traceback: Mostrar traceback completo
        """
        ...
    
    def prompt_user_input(
        self,
        message: str,
        choices: Optional[List[str]] = None,
        default: Optional[str] = None
    ) -> str:
        """
        Solicita entrada do usuário.
        
        Args:
            message: Mensagem do prompt
            choices: Opções disponíveis
            default: Valor padrão
            
        Returns:
            Entrada do usuário
        """
        ...
    
    def confirm_action(
        self,
        message: str,
        default: bool = False
    ) -> bool:
        """
        Confirmação de ação.
        
        Args:
            message: Mensagem de confirmação
            default: Valor padrão
            
        Returns:
            True se confirmado
        """
        ...


# =============================================================================
# FACTORY PATTERNS
# =============================================================================

class ComponentFactory:
    """
    Factory para criação de componentes com dependências injetadas.
    Garante compatibilidade com sistema atual.
    """
    
    def __init__(self, settings: Settings, logger: Logger, console: Console):
        """
        Inicializa factory com dependências do sistema atual.
        
        Args:
            settings: Settings do config.py
            logger: Logger Loguru configurado
            console: Console Rich global
        """
        self.settings = settings
        self.logger = logger
        self.console = console
    
    def create_audio_engine(self, implementation: str = "default") -> IAudioCaptureEngine:
        """
        Cria engine de áudio.
        
        Args:
            implementation: Implementação a usar
            
        Returns:
            Instância do engine
        """
        ...
    
    def create_transcription_engine(self, implementation: str = "whisper") -> ITranscriptionEngine:
        """
        Cria engine de transcrição.
        
        Args:
            implementation: Implementação a usar
            
        Returns:
            Instância do engine
        """
        ...
    
    def create_storage_manager(self, implementation: str = "filesystem") -> IStorageManager:
        """
        Cria gerenciador de storage.
        
        Args:
            implementation: Implementação a usar
            
        Returns:
            Instância do manager
        """
        ...
    
    def create_ui_controller(self, implementation: str = "rich") -> IUIController:
        """
        Cria controller de UI.
        
        Args:
            implementation: Implementação a usar
            
        Returns:
            Instância do controller
        """
        ...


# =============================================================================
# EXCEPTION CLASSES COMPATÍVEIS
# =============================================================================

# Importar exceções existentes para compatibilidade
try:
    from audio_recorder import AudioRecorderError, RecordingInProgressError
    from device_manager import AudioDeviceError, WASAPINotAvailableError
    from src.transcription.transcriber import TranscriptionError, ModelNotAvailableError
    from src.transcription.intelligent_transcriber import SpeakerDetectionError
    from src.transcription.exporter import ExportError
except ImportError:
    # Definir exceções se módulos não disponíveis
    class AudioRecorderError(Exception):
        """Erro no gravador de áudio."""
        pass
    
    class RecordingInProgressError(AudioRecorderError):
        """Gravação já em progresso."""
        pass
    
    class AudioDeviceError(Exception):
        """Erro em dispositivo de áudio."""
        pass
    
    class WASAPINotAvailableError(AudioDeviceError):
        """WASAPI não disponível."""
        pass
    
    class TranscriptionError(Exception):
        """Erro na transcrição."""
        pass
    
    class ModelNotAvailableError(TranscriptionError):
        """Modelo não disponível."""
        pass
    
    class SpeakerDetectionError(TranscriptionError):
        """Erro na detecção de speakers."""
        pass
    
    class ExportError(Exception):
        """Erro na exportação."""
        pass


# Novas exceções específicas das interfaces
class StorageError(Exception):
    """Erro no sistema de storage."""
    pass


class UIError(Exception):
    """Erro na interface de usuário."""
    pass


class ComponentInitializationError(Exception):
    """Erro na inicialização de componente."""
    pass


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "RecordingState",
    "TranscriptionState", 
    "StorageType",
    
    # Data Models
    "RecordingSession",
    "AudioFile",
    "TranscriptionJob",
    "StorageLocation",
    
    # Callback Types
    "RecordingProgressCallback",
    "RecordingErrorCallback",
    "TranscriptionProgressCallback",
    "TranscriptionCompleteCallback",
    "TranscriptionErrorCallback",
    
    # Interfaces
    "IBaseComponent",
    "IAudioCaptureEngine",
    "ITranscriptionEngine", 
    "IStorageManager",
    "IUIController",
    
    # Factory
    "ComponentFactory",
    
    # Exceptions
    "AudioRecorderError",
    "RecordingInProgressError",
    "AudioDeviceError",
    "WASAPINotAvailableError",
    "TranscriptionError",
    "ModelNotAvailableError",
    "SpeakerDetectionError",
    "ExportError",
    "StorageError",
    "UIError",
    "ComponentInitializationError",
]