"""Audio Processing and Device Management Module

High-quality audio recording for Teams meetings using WASAPI.
Provides device management and intelligent audio capture.
Supports dual-stream recording (speaker + microphone) for complete meeting capture.
"""

from .recorder import AudioRecorder, RecordingConfig, AudioRecorderError, RecordingQuality
from .devices import DeviceManager, AudioDevice, AudioDeviceError
from .dual_recorder import DualStreamRecorder, DualRecordingConfig, DualRecordingStats, DualStreamRecorderError

__all__ = [
    "AudioRecorder",
    "RecordingConfig",
    "AudioRecorderError",
    "RecordingQuality",
    "DeviceManager",
    "AudioDevice",
    "AudioDeviceError",
    "DualStreamRecorder",
    "DualRecordingConfig",
    "DualRecordingStats",
    "DualStreamRecorderError"
]