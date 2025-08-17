"""
Módulo Core do MeetingScribe
Funcionalidades centrais: detecção de hardware, configurações e presets.
"""

# Temporariamente desabilitado devido a problemas com py-cpuinfo
try:
    from .hardware_detection import (
        HardwareDetector,
        SystemSpecs,
        CPUInfo,
        GPUInfo,
        MemoryInfo,
        StorageInfo,
        PerformanceLevel,
        GPUVendor,
        detect_hardware
    )
    HARDWARE_DETECTION_AVAILABLE = True
except Exception as e:
    # Criar stubs/fallbacks
    class HardwareDetector:
        pass
    class SystemSpecs:
        pass
    class CPUInfo:
        pass
    class GPUInfo:
        pass
    class MemoryInfo:
        pass
    class StorageInfo:
        pass
    class PerformanceLevel:
        BASIC = "BASIC"
    class GPUVendor:
        UNKNOWN = "UNKNOWN"
    def detect_hardware():
        return None
    HARDWARE_DETECTION_AVAILABLE = False

from .settings_manager import (
    SettingsManager,
    PresetManager,
    MeetingScribeConfig,
    WhisperSettings,
    SpeakerSettings,
    AudioSettings,
    ExportSettings,
    PerformanceSettings,
    PresetType,
    ComputeType,
    create_settings_manager,
    get_system_info
)

from .domain_services import (
    AudioProcessingService,
    TranscriptionQualityService,
    WorkflowOrchestrationService,
    ProcessingStrategy,
    QualityLevel,
    WorkflowStatus,
    ProcessingRecommendation,
    QualityAssessment,
    WorkflowStep,
    create_audio_processing_service,
    create_transcription_quality_service,
    create_workflow_orchestration_service,
    create_all_domain_services
)

from .model_cache import (
    ModelCache,
    CacheStrategy,
    ModelCacheEntry,
    get_model_cache,
    create_cached_model,
    shutdown_model_cache
)

from .audio_chunk_processor import (
    AudioChunkProcessor,
    ChunkConfig,
    ChunkStrategy,
    AudioChunk,
    ChunkProcessingResult,
    create_chunk_processor
)

from .memory_manager import (
    MemoryManager,
    MemoryManagerConfig,
    MemoryStats,
    MemoryPressureLevel,
    MemoryOptimizationStrategy,
    get_memory_manager,
    shutdown_memory_manager,
    optimize_memory_now,
    get_memory_stats,
    check_memory_pressure,
    managed_memory,
    register_for_cleanup
)

from .async_processor import (
    AsyncProcessor,
    AsyncProcessorConfig,
    AsyncTask,
    TaskStatus,
    TaskPriority,
    AsyncTranscriptionQueue,
    get_async_processor,
    shutdown_async_processor,
    transcribe_async
)

from .async_integration import (
    AsyncTranscriptionManager,
    AsyncTranscriptionRequest,
    get_transcription_manager,
    transcribe_file_async,
    wait_for_transcription,
    get_async_stats,
    cancel_transcription,
    list_active_transcriptions
)

__all__ = [
    # Hardware detection
    "HardwareDetector",
    "SystemSpecs",
    "CPUInfo",
    "GPUInfo", 
    "MemoryInfo",
    "StorageInfo",
    "detect_hardware",
    
    # Settings management
    "SettingsManager",
    "PresetManager",
    "MeetingScribeConfig",
    "WhisperSettings",
    "SpeakerSettings",
    "AudioSettings",
    "ExportSettings",
    "PerformanceSettings",
    
    # Domain Services
    "AudioProcessingService",
    "TranscriptionQualityService",
    "WorkflowOrchestrationService",
    
    # Domain Enums
    "ProcessingStrategy",
    "QualityLevel",
    "WorkflowStatus",
    
    # Domain Data Classes
    "ProcessingRecommendation",
    "QualityAssessment",
    "WorkflowStep",
    
    # Enums
    "PerformanceLevel",
    "GPUVendor",
    "PresetType",
    "ComputeType",
    
    # Model Cache
    "ModelCache",
    "CacheStrategy",
    "ModelCacheEntry",
    
    # Audio Chunk Processing
    "AudioChunkProcessor",
    "ChunkConfig",
    "ChunkStrategy", 
    "AudioChunk",
    "ChunkProcessingResult",
    
    # Memory Management
    "MemoryManager",
    "MemoryManagerConfig",
    "MemoryStats",
    "MemoryPressureLevel",
    "MemoryOptimizationStrategy",
    
    # Async Processing
    "AsyncProcessor",
    "AsyncProcessorConfig",
    "AsyncTask",
    "TaskStatus", 
    "TaskPriority",
    "AsyncTranscriptionQueue",
    
    # Async Integration
    "AsyncTranscriptionManager",
    "AsyncTranscriptionRequest",
    
    # Factory functions
    "create_settings_manager",
    "get_system_info",
    "create_audio_processing_service",
    "create_transcription_quality_service",
    "create_workflow_orchestration_service",
    "create_all_domain_services",
    "get_model_cache",
    "create_cached_model",
    "shutdown_model_cache",
    "create_chunk_processor",
    "get_memory_manager",
    "shutdown_memory_manager",
    "optimize_memory_now",
    "get_memory_stats",
    "check_memory_pressure",
    "managed_memory",
    "register_for_cleanup",
    "get_async_processor",
    "shutdown_async_processor",
    "transcribe_async",
    "get_transcription_manager",
    "transcribe_file_async",
    "wait_for_transcription",
    "get_async_stats",
    "cancel_transcription",
    "list_active_transcriptions"
]