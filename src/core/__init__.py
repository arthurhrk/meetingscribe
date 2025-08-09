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
    
    # Enums
    "PerformanceLevel",
    "GPUVendor",
    "PresetType",
    "ComputeType",
    
    # Factory functions
    "create_settings_manager",
    "get_system_info"
]