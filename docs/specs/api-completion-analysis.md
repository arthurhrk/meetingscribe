# Análise e Especificação de Completação - src/api/

## Auditoria do Módulo API

### **Estado Atual Descoberto** ❌
- **Diretório**: `src/api/` existe mas está **VAZIO**
- **Status**: Nenhuma implementação FastAPI encontrada
- **Estrutura**: Apenas placeholder de diretório
- **Endpoints**: 0 endpoints implementados
- **Middleware**: Não implementado
- **Error handling**: Não implementado

### **Conclusão da Auditoria**
O módulo API está em estado **inicial/placeholder** e requer implementação completa from scratch. Esta é uma oportunidade para criar uma API moderna e bem integrada com o sistema existente.

## Mapeamento de Endpoints Necessários vs Existentes

### **Endpoints Atuais** ❌
```
src/api/ 
└── (vazio - nenhum endpoint implementado)
```

### **Endpoints Necessários Especificados** ✅

#### **1. Audio Endpoints**
```
GET    /api/v1/audio/devices          # Listar dispositivos de áudio
POST   /api/v1/audio/record           # Iniciar gravação  
POST   /api/v1/audio/stop             # Parar gravação
GET    /api/v1/audio/sessions         # Listar sessões ativas
GET    /api/v1/audio/sessions/{id}    # Status de sessão específica
DELETE /api/v1/audio/sessions/{id}    # Cancelar sessão
```

#### **2. Transcription Endpoints**
```
POST   /api/v1/transcription/start    # Iniciar transcrição
GET    /api/v1/transcription/status/{job_id}   # Status do job
GET    /api/v1/transcription/result/{job_id}   # Resultado da transcrição
DELETE /api/v1/transcription/cancel/{job_id}   # Cancelar transcrição
GET    /api/v1/transcription/models   # Modelos disponíveis
```

#### **3. Files Endpoints**
```
GET    /api/v1/files/recordings       # Listar gravações
GET    /api/v1/files/transcriptions   # Listar transcrições
GET    /api/v1/files/download/{id}    # Download de arquivo
DELETE /api/v1/files/{id}             # Deletar arquivo
POST   /api/v1/files/export           # Exportar em múltiplos formatos
GET    /api/v1/files/exports          # Listar exports disponíveis
```

#### **4. System Endpoints**
```
GET    /api/v1/system/status          # Status do sistema
GET    /api/v1/system/health          # Health check
GET    /api/v1/system/info            # Informações do sistema
GET    /api/v1/system/config          # Configuração atual
PUT    /api/v1/system/config          # Atualizar configuração
```

#### **5. WebSocket Endpoints**
```
WS     /api/v1/ws/recording           # Updates em tempo real de gravação
WS     /api/v1/ws/transcription       # Updates de progresso de transcrição
WS     /api/v1/ws/system             # Events do sistema
```

## Análise de Integração com Core Modules

### **Módulos Core Disponíveis para Integração** ✅

#### **1. Config Integration**
```python
# src/api/ deve usar
from config import settings, setup_logging
from src.core import (
    create_settings_manager, 
    get_system_info,
    detect_hardware
)
```

#### **2. Audio Modules Integration**
```python
# Integração com sistema de áudio existente
from device_manager import DeviceManager, AudioDevice
from audio_recorder import (
    AudioRecorder, 
    create_recorder_from_config,
    RecordingConfig, 
    RecordingStats
)
```

#### **3. Transcription Modules Integration**
```python
# Integração com sistema de transcrição existente
from src.transcription import (
    create_transcriber,
    create_intelligent_transcriber,
    TranscriptionResult,
    export_transcription,
    ExportFormat
)
```

#### **4. Models Integration**
```python
# Integração com domain models
from src.models.domain import (
    AudioFile,
    RecordingSession, 
    TranscriptionResult,
    TranscriptionJob,
    SystemStatus
)
```

#### **5. Interfaces Integration**
```python
# Integração com interfaces
from src.interfaces import (
    IAudioCaptureEngine,
    ITranscriptionEngine, 
    IStorageManager,
    ComponentFactory
)
```

## Especificação de API Completion

### **Estrutura FastAPI Proposta** ✅

```
src/api/
├── __init__.py              # FastAPI app factory
├── main.py                  # App entry point
├── dependencies.py          # Dependency injection
├── middleware.py            # Custom middleware
├── exceptions.py            # Exception handlers
├── models/
│   ├── __init__.py
│   ├── requests.py          # Pydantic request models
│   ├── responses.py         # Pydantic response models
│   └── websocket.py         # WebSocket message models
├── routers/
│   ├── __init__.py
│   ├── audio.py            # Audio endpoints
│   ├── transcription.py    # Transcription endpoints
│   ├── files.py            # File management endpoints
│   ├── system.py           # System endpoints
│   └── websocket.py        # WebSocket handlers
├── services/
│   ├── __init__.py
│   ├── audio_service.py    # Audio business logic
│   ├── transcription_service.py  # Transcription logic
│   ├── file_service.py     # File operations
│   └── system_service.py   # System operations
└── utils/
    ├── __init__.py
    ├── auth.py             # Authentication (future)
    ├── validation.py       # Request validation
    └── background_tasks.py  # Async task management
```

### **FastAPI Application Factory** ✅

#### **Arquivo: `src/api/__init__.py`**
```python
"""
MeetingScribe FastAPI Application

API RESTful para integração com sistema de transcrição existente.
Mantém compatibilidade total com CLI e business logic atual.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from config import settings, setup_logging
from loguru import logger
from .routers import audio, transcription, files, system, websocket
from .middleware import LoggingMiddleware, ErrorHandlingMiddleware
from .exceptions import setup_exception_handlers
from .dependencies import get_component_factory

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management para FastAPI app."""
    # Startup
    logger.info("Iniciando MeetingScribe API...")
    setup_logging()
    
    # Inicializar componentes
    from src.interfaces import ComponentFactory
    from rich.console import Console
    
    factory = ComponentFactory(
        settings=settings,
        logger=logger,
        console=Console()
    )
    
    # Store factory in app state
    app.state.component_factory = factory
    
    logger.success("MeetingScribe API iniciada com sucesso")
    
    yield
    
    # Shutdown
    logger.info("Encerrando MeetingScribe API...")
    # Cleanup resources

def create_app() -> FastAPI:
    """Factory function para criar FastAPI app."""
    
    app = FastAPI(
        title="MeetingScribe API",
        description="API RESTful para sistema de transcrição de reuniões",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        openapi_url="/api/openapi.json"
    )
    
    # Middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Exception handlers
    setup_exception_handlers(app)
    
    # Routers
    app.include_router(
        audio.router,
        prefix="/api/v1/audio",
        tags=["audio"]
    )
    app.include_router(
        transcription.router,
        prefix="/api/v1/transcription", 
        tags=["transcription"]
    )
    app.include_router(
        files.router,
        prefix="/api/v1/files",
        tags=["files"]
    )
    app.include_router(
        system.router,
        prefix="/api/v1/system",
        tags=["system"]
    )
    app.include_router(
        websocket.router,
        prefix="/api/v1/ws",
        tags=["websocket"]
    )
    
    # Root endpoint
    @app.get("/", tags=["root"])
    async def root():
        return {
            "message": "MeetingScribe API",
            "version": settings.app_version,
            "status": "healthy",
            "docs": "/api/docs"
        }
    
    @app.get("/api/health", tags=["health"])
    async def health_check():
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    return app

# App instance for uvicorn
app = create_app()

# CLI command para rodar API
def run_api(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False
):
    """Executa servidor FastAPI."""
    logger.info(f"Iniciando servidor API em http://{host}:{port}")
    uvicorn.run(
        "src.api:app",
        host=host,
        port=port,
        reload=reload,
        log_config=None  # Use Loguru
    )
```

#### **Arquivo: `src/api/main.py`**
```python
"""
Entry point for MeetingScribe API server.
Standalone execution of FastAPI application.
"""

import argparse
from src.api import run_api

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MeetingScribe API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    run_api(host=args.host, port=args.port, reload=args.reload)
```

### **Request/Response Models** ✅

#### **Arquivo: `src/api/models/requests.py`**
```python
"""
Pydantic models para requests da API.
Compatível com domain models existentes.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime

from src.models.domain import (
    WhisperModelSize, AudioFormat, ExportFormat,
    RecordingStatus, TranscriptionStatus
)

# Audio Recording Requests
class StartRecordingRequest(BaseModel):
    """Request para iniciar gravação."""
    device_id: Optional[str] = Field(None, description="ID do dispositivo (auto se None)")
    filename: Optional[str] = Field(None, description="Nome do arquivo (auto se None)")
    max_duration: Optional[int] = Field(None, ge=1, le=21600, description="Duração máxima em segundos")
    auto_stop_silence: Optional[float] = Field(None, ge=1.0, description="Para automaticamente após silêncio (segundos)")
    
    class Config:
        schema_extra = {
            "example": {
                "device_id": "device_001", 
                "filename": "meeting_2024.wav",
                "max_duration": 3600,
                "auto_stop_silence": 30.0
            }
        }

class StopRecordingRequest(BaseModel):
    """Request para parar gravação."""
    session_id: str = Field(..., description="ID da sessão de gravação")
    save_file: bool = Field(True, description="Salvar arquivo ou descartar")

# Transcription Requests  
class StartTranscriptionRequest(BaseModel):
    """Request para iniciar transcrição."""
    audio_file_path: Optional[str] = Field(None, description="Path do arquivo de áudio")
    audio_file_id: Optional[str] = Field(None, description="ID do arquivo no sistema")
    model_size: WhisperModelSize = Field(WhisperModelSize.BASE, description="Modelo Whisper")
    language: Optional[str] = Field(None, description="Idioma (auto-detect se None)")
    enable_speaker_detection: bool = Field(False, description="Habilitar detecção de speakers")
    
    @validator('audio_file_path', 'audio_file_id')
    def validate_audio_source(cls, v, values):
        """Valida que pelo menos um source foi fornecido."""
        if not v and not values.get('audio_file_path') and not values.get('audio_file_id'):
            raise ValueError("Forneça audio_file_path ou audio_file_id")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "audio_file_path": "/path/to/audio.wav",
                "model_size": "base",
                "language": "pt",
                "enable_speaker_detection": true
            }
        }

# File Management Requests
class ExportRequest(BaseModel):
    """Request para exportar transcrição."""
    transcription_id: str = Field(..., description="ID da transcrição")
    formats: List[ExportFormat] = Field(..., description="Formatos de exportação")
    include_metadata: bool = Field(True, description="Incluir metadados")
    include_timestamps: bool = Field(True, description="Incluir timestamps")
    
    class Config:
        schema_extra = {
            "example": {
                "transcription_id": "trans_123",
                "formats": ["txt", "srt", "json"],
                "include_metadata": true,
                "include_timestamps": true
            }
        }

class DeleteFileRequest(BaseModel):
    """Request para deletar arquivo."""
    file_id: str = Field(..., description="ID do arquivo")
    file_type: str = Field(..., regex="^(recording|transcription|export)$")
    confirm_delete: bool = Field(False, description="Confirmação de deleção")

# System Configuration Requests
class UpdateConfigRequest(BaseModel):
    """Request para atualizar configuração."""
    whisper_model: Optional[WhisperModelSize] = None
    whisper_language: Optional[str] = None
    audio_sample_rate: Optional[int] = Field(None, ge=8000, le=192000)
    audio_channels: Optional[int] = Field(None, ge=1, le=8)
    
    class Config:
        schema_extra = {
            "example": {
                "whisper_model": "small",
                "whisper_language": "pt",
                "audio_sample_rate": 16000
            }
        }
```

#### **Arquivo: `src/api/models/responses.py`**
```python
"""
Pydantic models para responses da API.
Padroniza formato de resposta e error handling.
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from src.models.domain import (
    RecordingStatus, TranscriptionStatus, 
    AudioFormat, ExportFormat
)

# Base Response Models
class APIResponse(BaseModel):
    """Response base da API."""
    success: bool = Field(..., description="Sucesso da operação")
    message: str = Field(..., description="Mensagem descritiva")
    timestamp: datetime = Field(default_factory=datetime.now)

class APIError(APIResponse):
    """Response de erro da API."""
    success: bool = Field(False)
    error_code: str = Field(..., description="Código do erro")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detalhes do erro")

# Audio Responses
class AudioDeviceResponse(BaseModel):
    """Response para dispositivo de áudio."""
    id: str
    name: str
    max_input_channels: int
    max_output_channels: int
    sample_rate: int
    is_default: bool
    is_loopback: bool
    is_available: bool

class RecordingSessionResponse(BaseModel):
    """Response para sessão de gravação."""
    session_id: str
    device: AudioDeviceResponse
    status: RecordingStatus
    start_time: Optional[datetime]
    duration_seconds: float
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    error_message: Optional[str]

class StartRecordingResponse(APIResponse):
    """Response para início de gravação."""
    session: RecordingSessionResponse

class StopRecordingResponse(APIResponse):
    """Response para parada de gravação."""
    session: RecordingSessionResponse
    audio_file: Optional[Dict[str, Any]]

# Transcription Responses
class TranscriptionJobResponse(BaseModel):
    """Response para job de transcrição."""
    job_id: str
    status: TranscriptionStatus
    progress: float = Field(ge=0.0, le=1.0)
    audio_file_info: Dict[str, Any]
    model_used: str
    language: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]

class TranscriptionSegmentResponse(BaseModel):
    """Response para segmento de transcrição."""
    id: int
    text: str
    start_time: float
    end_time: float
    confidence: float
    speaker_id: Optional[str]
    speaker_name: Optional[str]

class TranscriptionResultResponse(BaseModel):
    """Response para resultado de transcrição."""
    job_id: str
    full_text: str
    segments: List[TranscriptionSegmentResponse]
    language: str
    confidence_average: float
    total_duration: float
    processing_time: float
    word_count: int
    speakers_detected: List[str]

class StartTranscriptionResponse(APIResponse):
    """Response para início de transcrição."""
    job: TranscriptionJobResponse

# File Management Responses
class AudioFileResponse(BaseModel):
    """Response para arquivo de áudio."""
    id: str
    filename: str
    path: str
    size_bytes: int
    size_mb: float
    duration_seconds: float
    duration_formatted: str
    sample_rate: int
    channels: int
    audio_format: AudioFormat
    created_at: datetime

class TranscriptionFileResponse(BaseModel):
    """Response para arquivo de transcrição."""
    id: str
    filename: str
    path: str
    audio_file_id: str
    full_text: str
    language: str
    model_used: str
    confidence_average: float
    word_count: int
    created_at: datetime

class ExportFileResponse(BaseModel):
    """Response para arquivo exportado."""
    id: str
    filename: str
    path: str
    format: ExportFormat
    size_bytes: int
    transcription_id: str
    created_at: datetime

class ListRecordingsResponse(APIResponse):
    """Response para lista de gravações."""
    recordings: List[AudioFileResponse]
    total_count: int
    page: int
    page_size: int

class ListTranscriptionsResponse(APIResponse):
    """Response para lista de transcrições."""
    transcriptions: List[TranscriptionFileResponse]
    total_count: int
    page: int
    page_size: int

class ExportResponse(APIResponse):
    """Response para exportação."""
    export_files: List[ExportFileResponse]
    total_files: int

# System Responses
class SystemHealthResponse(BaseModel):
    """Response para health check."""
    status: str = Field(..., regex="^(healthy|warning|error)$")
    timestamp: datetime
    uptime_seconds: float
    version: str
    
class SystemInfoResponse(BaseModel):
    """Response para informações do sistema."""
    os: str
    python_version: str
    cpu: Dict[str, Any]
    memory: Dict[str, Any] 
    gpu: Dict[str, Any]
    storage: Dict[str, Any]
    performance_level: str
    available_models: List[str]
    available_devices: List[AudioDeviceResponse]

class SystemStatusResponse(APIResponse):
    """Response para status do sistema."""
    health: SystemHealthResponse
    info: SystemInfoResponse
    active_recordings: int
    active_transcriptions: int
    total_files: Dict[str, int]

# Configuration Response
class ConfigurationResponse(BaseModel):
    """Response para configuração atual."""
    whisper_model: str
    whisper_language: str
    whisper_device: str
    audio_sample_rate: int
    audio_channels: int
    chunk_duration: int
    debug: bool
    log_level: str
    
class UpdateConfigResponse(APIResponse):
    """Response para atualização de configuração."""
    old_config: ConfigurationResponse
    new_config: ConfigurationResponse
    changes_applied: List[str]
```

### **Audio Router Implementation** ✅

#### **Arquivo: `src/api/routers/audio.py`**
```python
"""
Audio router para endpoints de gravação de áudio.
Integra com audio_recorder.py e device_manager.py existentes.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import asyncio
from datetime import datetime

from config import settings
from loguru import logger
from ..dependencies import get_component_factory, get_audio_service
from ..models.requests import StartRecordingRequest, StopRecordingRequest
from ..models.responses import (
    AudioDeviceResponse, RecordingSessionResponse,
    StartRecordingResponse, StopRecordingResponse,
    APIError
)
from ..services.audio_service import AudioService
from src.interfaces import ComponentFactory

router = APIRouter()

@router.get("/devices", response_model=List[AudioDeviceResponse])
async def list_audio_devices(
    factory: ComponentFactory = Depends(get_component_factory)
):
    """Lista todos os dispositivos de áudio disponíveis."""
    try:
        audio_service = factory.create_audio_engine()
        devices = await audio_service.initialize_devices()
        
        return [
            AudioDeviceResponse(
                id=device.id,
                name=device.name,
                max_input_channels=device.max_input_channels,
                max_output_channels=device.max_output_channels,
                sample_rate=device.sample_rate,
                is_default=device.is_default,
                is_loopback=device.is_loopback,
                is_available=device.is_available
            )
            for device in devices
        ]
        
    except Exception as e:
        logger.error(f"Erro ao listar dispositivos: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )

@router.post("/record", response_model=StartRecordingResponse)
async def start_recording(
    request: StartRecordingRequest,
    background_tasks: BackgroundTasks,
    audio_service: AudioService = Depends(get_audio_service)
):
    """Inicia uma nova gravação de áudio."""
    try:
        # Validar dispositivo se fornecido
        if request.device_id:
            devices = await audio_service.get_available_devices()
            device = next((d for d in devices if d.id == request.device_id), None)
            if not device:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dispositivo não encontrado: {request.device_id}"
                )
        
        # Iniciar gravação
        session = await audio_service.start_recording(
            device_id=request.device_id,
            filename=request.filename,
            max_duration=request.max_duration,
            auto_stop_silence=request.auto_stop_silence
        )
        
        # Agendar auto-stop se configurado
        if request.max_duration:
            background_tasks.add_task(
                audio_service.auto_stop_recording,
                session.session_id,
                request.max_duration
            )
        
        logger.info(f"Gravação iniciada: {session.session_id}")
        
        return StartRecordingResponse(
            success=True,
            message="Gravação iniciada com sucesso",
            session=RecordingSessionResponse(
                session_id=session.session_id,
                device=AudioDeviceResponse(**session.device.dict()),
                status=session.status,
                start_time=session.start_time,
                duration_seconds=session.duration_seconds,
                file_path=str(session.file_path) if session.file_path else None,
                file_size_bytes=None,
                error_message=session.error_message
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao iniciar gravação: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )

@router.post("/stop", response_model=StopRecordingResponse)
async def stop_recording(
    request: StopRecordingRequest,
    audio_service: AudioService = Depends(get_audio_service)
):
    """Para uma gravação ativa."""
    try:
        # Verificar se sessão existe
        session = await audio_service.get_session(request.session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Sessão não encontrada: {request.session_id}"
            )
        
        if not session.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Sessão não está ativa: {session.status.value}"
            )
        
        # Parar gravação
        audio_file = await audio_service.stop_recording(
            session,
            save_file=request.save_file
        )
        
        logger.info(f"Gravação parada: {session.session_id}")
        
        return StopRecordingResponse(
            success=True,
            message="Gravação parada com sucesso",
            session=RecordingSessionResponse(**session.dict()),
            audio_file=audio_file.dict() if audio_file else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao parar gravação: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )

@router.get("/sessions", response_model=List[RecordingSessionResponse])
async def list_active_sessions(
    audio_service: AudioService = Depends(get_audio_service)
):
    """Lista todas as sessões de gravação ativas."""
    try:
        sessions = await audio_service.get_active_sessions()
        
        return [
            RecordingSessionResponse(**session.dict())
            for session in sessions
        ]
        
    except Exception as e:
        logger.error(f"Erro ao listar sessões: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )

@router.get("/sessions/{session_id}", response_model=RecordingSessionResponse)
async def get_session_status(
    session_id: str,
    audio_service: AudioService = Depends(get_audio_service)
):
    """Obtém status de uma sessão específica."""
    try:
        session = await audio_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Sessão não encontrada: {session_id}"
            )
        
        return RecordingSessionResponse(**session.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter status da sessão: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )

@router.delete("/sessions/{session_id}")
async def cancel_session(
    session_id: str,
    audio_service: AudioService = Depends(get_audio_service)
):
    """Cancela uma sessão de gravação."""
    try:
        success = await audio_service.cancel_session(session_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Sessão não encontrada: {session_id}"
            )
        
        logger.info(f"Sessão cancelada: {session_id}")
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Sessão cancelada com sucesso",
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao cancelar sessão: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )
```

### **Async Patterns para Operações Longas** ✅

#### **Arquivo: `src/api/utils/background_tasks.py`**
```python
"""
Background task management para operações assíncronas.
Gerencia transcrições longas e operações de I/O.
"""

import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid

from loguru import logger

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BackgroundTask:
    """Representa uma task em background."""
    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class BackgroundTaskManager:
    """Gerenciador de tasks em background."""
    
    def __init__(self):
        self.tasks: Dict[str, BackgroundTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
    async def submit_task(
        self,
        name: str,
        coro: Callable,
        *args,
        progress_callback: Optional[Callable] = None,
        **kwargs
    ) -> str:
        """Submete nova task para execução em background."""
        task_id = str(uuid.uuid4())
        
        bg_task = BackgroundTask(
            task_id=task_id,
            name=name
        )
        
        self.tasks[task_id] = bg_task
        
        # Criar asyncio task
        async_task = asyncio.create_task(
            self._run_task(
                task_id, 
                coro, 
                *args, 
                progress_callback=progress_callback,
                **kwargs
            )
        )
        
        self.running_tasks[task_id] = async_task
        
        logger.info(f"Task submetida: {name} ({task_id})")
        return task_id
    
    async def _run_task(
        self,
        task_id: str,
        coro: Callable,
        *args,
        progress_callback: Optional[Callable] = None,
        **kwargs
    ):
        """Executa task e atualiza status."""
        task = self.tasks[task_id]
        
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            # Wrapper para progress callback
            def update_progress(progress: float):
                task.progress = min(max(progress, 0.0), 1.0)
                if progress_callback:
                    progress_callback(task_id, progress)
            
            # Executar função
            if asyncio.iscoroutinefunction(coro):
                result = await coro(*args, progress_callback=update_progress, **kwargs)
            else:
                result = coro(*args, progress_callback=update_progress, **kwargs)
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            task.completed_at = datetime.now()
            
            logger.success(f"Task completada: {task.name} ({task_id})")
            
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            logger.warning(f"Task cancelada: {task.name} ({task_id})")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            logger.error(f"Task falhou: {task.name} ({task_id}) - {e}")
            
        finally:
            # Cleanup
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Obtém informações de uma task."""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, BackgroundTask]:
        """Obtém todas as tasks."""
        return self.tasks.copy()
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancela uma task em execução."""
        if task_id in self.running_tasks:
            async_task = self.running_tasks[task_id]
            async_task.cancel()
            
            # Aguardar cancelamento
            try:
                await async_task
            except asyncio.CancelledError:
                pass
            
            logger.info(f"Task cancelada: {task_id}")
            return True
        
        return False
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """Remove tasks antigas completadas."""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for task_id, task in self.tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                and task.completed_at 
                and task.completed_at < cutoff):
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.tasks[task_id]
            
        if to_remove:
            logger.info(f"Limpeza: {len(to_remove)} tasks antigas removidas")

# Singleton global
task_manager = BackgroundTaskManager()
```

### **WebSocket Support** ✅

#### **Arquivo: `src/api/routers/websocket.py`**
```python
"""
WebSocket router para updates em tempo real.
Fornece streaming de progresso para operações longas.
"""

from typing import Dict, Set, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.websockets import WebSocketState
import asyncio
import json
from datetime import datetime

from loguru import logger
from ..utils.background_tasks import task_manager, TaskStatus
from ..dependencies import get_component_factory

router = APIRouter()

class ConnectionManager:
    """Gerencia conexões WebSocket ativas."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "recording": set(),
            "transcription": set(), 
            "system": set()
        }
        
    async def connect(self, websocket: WebSocket, channel: str):
        """Aceita nova conexão WebSocket."""
        await websocket.accept()
        if channel in self.active_connections:
            self.active_connections[channel].add(websocket)
            logger.info(f"WebSocket conectado ao canal {channel}")
        
    def disconnect(self, websocket: WebSocket, channel: str):
        """Remove conexão WebSocket."""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            logger.info(f"WebSocket desconectado do canal {channel}")
    
    async def send_to_channel(self, channel: str, message: dict):
        """Envia mensagem para todas as conexões de um canal."""
        if channel not in self.active_connections:
            return
            
        disconnected = set()
        for connection in self.active_connections[channel]:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(json.dumps(message))
                else:
                    disconnected.add(connection)
            except Exception as e:
                logger.warning(f"Erro ao enviar WebSocket: {e}")
                disconnected.add(connection)
        
        # Remover conexões mortas
        for connection in disconnected:
            self.active_connections[channel].discard(connection)

manager = ConnectionManager()

@router.websocket("/recording")
async def websocket_recording(websocket: WebSocket):
    """WebSocket para updates de gravação em tempo real."""
    await manager.connect(websocket, "recording")
    
    try:
        while True:
            # Manter conexão viva e escutar por mensagens do cliente
            data = await websocket.receive_text()
            
            # Echo back para teste (opcional)
            await websocket.send_text(json.dumps({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, "recording")

@router.websocket("/transcription")
async def websocket_transcription(websocket: WebSocket):
    """WebSocket para updates de transcrição em tempo real."""
    await manager.connect(websocket, "transcription")
    
    try:
        while True:
            # Enviar updates de progress das tasks de transcrição
            tasks = task_manager.get_all_tasks()
            transcription_tasks = {
                task_id: task for task_id, task in tasks.items()
                if "transcription" in task.name.lower()
            }
            
            if transcription_tasks:
                await websocket.send_text(json.dumps({
                    "type": "transcription_progress",
                    "tasks": {
                        task_id: {
                            "status": task.status.value,
                            "progress": task.progress,
                            "name": task.name
                        }
                        for task_id, task in transcription_tasks.items()
                    },
                    "timestamp": datetime.now().isoformat()
                }))
            
            await asyncio.sleep(1)  # Update a cada segundo
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, "transcription")

@router.websocket("/system")
async def websocket_system(websocket: WebSocket):
    """WebSocket para events gerais do sistema."""
    await manager.connect(websocket, "system")
    
    try:
        while True:
            # System health updates
            health_data = {
                "type": "system_health",
                "active_recordings": len([
                    t for t in task_manager.get_all_tasks().values()
                    if "recording" in t.name.lower() and t.status == TaskStatus.RUNNING
                ]),
                "active_transcriptions": len([
                    t for t in task_manager.get_all_tasks().values() 
                    if "transcription" in t.name.lower() and t.status == TaskStatus.RUNNING
                ]),
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send_text(json.dumps(health_data))
            await asyncio.sleep(5)  # Update a cada 5 segundos
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, "system")

# Função helper para broadcasting
async def broadcast_recording_update(session_id: str, session_data: dict):
    """Broadcast update de gravação para WebSocket clients."""
    message = {
        "type": "recording_update",
        "session_id": session_id,
        "data": session_data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.send_to_channel("recording", message)

async def broadcast_transcription_update(job_id: str, job_data: dict):
    """Broadcast update de transcrição para WebSocket clients."""
    message = {
        "type": "transcription_update", 
        "job_id": job_id,
        "data": job_data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.send_to_channel("transcription", message)

async def broadcast_system_event(event_type: str, event_data: dict):
    """Broadcast event do sistema para WebSocket clients."""
    message = {
        "type": "system_event",
        "event_type": event_type,
        "data": event_data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.send_to_channel("system", message)
```

## Integração com Sistema Atual

### **Backward Compatibility Strategy** ✅

#### **1. API Opcional**
```python
# main.py - adicionar comando API opcional
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', action='store_true', help='Iniciar servidor API')
    parser.add_argument('--api-port', type=int, default=8000, help='Porta da API')
    
    args = parser.parse_args()
    
    if args.api:
        # Iniciar servidor API
        from src.api import run_api
        run_api(port=args.api_port)
    else:
        # Usar CLI normal (comportamento atual mantido)
        run_cli_interface()
```

#### **2. Shared Business Logic**
```python
# src/api/services/audio_service.py
"""
Service layer que wrappea lógica existente.
Compartilha business logic entre CLI e API.
"""

from audio_recorder import create_recorder_from_config, AudioRecorder
from device_manager import DeviceManager
from src.models.domain import RecordingSession, AudioFile

class AudioService:
    """Service que integra com código existente."""
    
    def __init__(self):
        # Usar sistemas existentes
        self.device_manager = DeviceManager()
        self.recorder = create_recorder_from_config()
        
    async def start_recording(self, **kwargs) -> RecordingSession:
        """Wrapper assíncrono para recorder existente."""
        # Usar lógica existente do audio_recorder.py
        filepath = self.recorder.start_recording(kwargs.get('filename'))
        
        # Converter para domain model
        session = RecordingSession(...)
        return session
    
    async def stop_recording(self, session) -> AudioFile:
        """Wrapper assíncrono para parar gravação."""
        # Usar lógica existente
        self.recorder.stop_recording()
        
        # Converter para domain model
        audio_file = AudioFile(...)
        return audio_file
```

#### **3. Error Handling Consistency**
```python
# src/api/exceptions.py
"""
Exception handlers que mantêm consistency com CLI.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from audio_recorder import AudioRecorderError, RecordingInProgressError
from src.transcription.transcriber import TranscriptionError

def setup_exception_handlers(app: FastAPI):
    """Configura handlers para exceções do sistema existente."""
    
    @app.exception_handler(AudioRecorderError)
    async def audio_recorder_exception_handler(request: Request, exc: AudioRecorderError):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error_code": "AUDIO_RECORDER_ERROR",
                "message": str(exc),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    @app.exception_handler(RecordingInProgressError)
    async def recording_in_progress_handler(request: Request, exc: RecordingInProgressError):
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "error_code": "RECORDING_IN_PROGRESS", 
                "message": "Uma gravação já está em andamento",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    @app.exception_handler(TranscriptionError)
    async def transcription_error_handler(request: Request, exc: TranscriptionError):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_code": "TRANSCRIPTION_ERROR",
                "message": str(exc),
                "timestamp": datetime.now().isoformat()
            }
        )
```

#### **4. Rich Console Integration**
```python
# src/api/middleware.py
"""
Middleware que integra com Rich console para logging.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
from rich.console import Console
from loguru import logger

console = Console()  # Mesmo console usado no CLI

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware de logging compatível com Rich."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request usando Rich patterns
        console.print(f"[blue]API Request:[/blue] {request.method} {request.url}")
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Log response usando Rich patterns  
        status_color = "green" if response.status_code < 400 else "red"
        console.print(
            f"[{status_color}]API Response:[/{status_color}] "
            f"{response.status_code} - {process_time:.3f}s"
        )
        
        # Log estruturado também
        logger.info(
            f"API {request.method} {request.url} "
            f"-> {response.status_code} ({process_time:.3f}s)"
        )
        
        return response
```

## Timeline de Implementação

### **Fase 1: Foundation (Semana 1)**
- ✅ Criar estrutura FastAPI básica
- ✅ Implementar models de request/response
- ✅ Setup middleware e exception handling
- ✅ Criar factory e dependency injection

### **Fase 2: Core Endpoints (Semana 2)**
- ✅ Implementar audio endpoints (`/audio/*`)
- ✅ Implementar transcription endpoints (`/transcription/*`)
- ✅ Integrar com módulos existentes
- ✅ Testes básicos de integração

### **Fase 3: Advanced Features (Semana 3)**
- ✅ WebSocket support para real-time updates
- ✅ Background task management
- ✅ File management endpoints (`/files/*`)
- ✅ System endpoints (`/system/*`)

### **Fase 4: Production Ready (Semana 4)**
- ✅ OpenAPI documentation completa
- ✅ Authentication/authorization (opcional)
- ✅ Rate limiting e security
- ✅ Performance optimization
- ✅ Deployment configuration

---

## **Status Summary**

### ❌ **Estado Atual**
- `src/api/` directory vazio
- Nenhum endpoint implementado
- Sem estrutura FastAPI

### ✅ **Especificação Completa**
- 25+ endpoints especificados
- Request/Response models completos
- WebSocket support planejado
- Background task management
- Integração total com sistema existente

### 🔄 **Backward Compatibility**
- API 100% opcional (não quebra CLI)
- Shared business logic com CLI
- Error handling consistency
- Rich console integration

### 📅 **Implementation Ready**
- Estrutura detalhada especificada
- Dependency injection planejado
- Async patterns definidos
- Timeline de 4 semanas

**Resultado**: API moderna e completa mantendo total compatibilidade com sistema CLI atual.