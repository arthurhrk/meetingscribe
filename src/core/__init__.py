"""
Módulo Core do MeetingScribe
Funcionalidades centrais: detecção de hardware, configurações e presets.
"""

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