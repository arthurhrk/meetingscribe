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

from .performance_monitor import (
    PerformanceMonitor,
    PerformanceMetric,
    TranscriptionMetrics,
    SystemMetrics,
    PerformanceTimer,
    get_performance_monitor,
    init_performance_monitoring,
    monitor_performance
)

from .raycast_metrics_cli import (
    RaycastMetricsCLI
)

from .auto_profiler import (
    AutoProfiler,
    BottleneckDetection,
    ProfilingReport,
    SystemSnapshot,
    get_auto_profiler,
    auto_profile
)

from .profiler_cli import (
    ProfilerCLI
)

from .file_cache import (
    FileCache,
    FileCacheConfig,
    CacheStrategy,
    CompressionLevel,
    CacheEntry,
    get_file_cache,
    shutdown_file_cache,
    cached_file,
    file_cached
)

from .file_optimizers import (
    OptimizedAudioLoader,
    OptimizedFileManager,
    AudioMetadata,
    get_optimized_file_manager
)

from .cache_cli import (
    CacheCLI
)

from .streaming_processor import (
    AudioStreamer,
    StreamConfig,
    StreamingStrategy,
    BufferStrategy,
    AudioChunk,
    StreamingStats,
    create_audio_streamer,
    stream_large_audio_file,
    streaming_audio
)

from .streaming_cli import (
    StreamingCLI
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
    
    # Performance Monitoring
    "PerformanceMonitor",
    "PerformanceMetric",
    "TranscriptionMetrics",
    "SystemMetrics",
    "PerformanceTimer",
    "RaycastMetricsCLI",
    
    # Auto Profiling
    "AutoProfiler",
    "BottleneckDetection",
    "ProfilingReport",
    "SystemSnapshot",
    "ProfilerCLI",
    
    # File Cache
    "FileCache",
    "FileCacheConfig",
    "CacheStrategy",
    "CompressionLevel",
    "CacheEntry",
    "OptimizedAudioLoader",
    "OptimizedFileManager",
    "AudioMetadata",
    "CacheCLI",
    
    # Streaming
    "AudioStreamer",
    "StreamConfig",
    "StreamingStrategy",
    "BufferStrategy",
    "AudioChunk",
    "StreamingStats",
    "StreamingCLI",
    
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
    "list_active_transcriptions",
    "get_performance_monitor",
    "init_performance_monitoring",
    "monitor_performance",
    "get_auto_profiler",
    "auto_profile",
    "get_file_cache",
    "shutdown_file_cache",
    "cached_file",
    "file_cached",
    "get_optimized_file_manager",
    "create_audio_streamer",
    "stream_large_audio_file",
    "streaming_audio"
]