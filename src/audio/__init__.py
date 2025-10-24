"""Audio Processing and Device Management Module

High-quality audio recording for Teams meetings using WASAPI.
Provides device management and intelligent audio capture.
"""

from .recorder import AudioRecorder, RecordingConfig, AudioRecorderError
from .devices import DeviceManager, AudioDevice, AudioDeviceError

__all__ = [
    "AudioRecorder",
    "RecordingConfig",
    "AudioRecorderError",
    "DeviceManager",
    "AudioDevice",
    "AudioDeviceError"
]