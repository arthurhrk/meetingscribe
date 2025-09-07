"""Audio Processing and Device Management Module

Provides intelligent audio device selection and processing capabilities.
"""

from .smart_selector import (
    SmartDeviceSelector,
    AudioContext,
    DevicePriority,
    DeviceScore,
    DevicePreference,
    get_smart_selector,
    select_best_device,
    record_device_success,
    record_device_failure
)

__all__ = [
    "SmartDeviceSelector",
    "AudioContext", 
    "DevicePriority",
    "DeviceScore",
    "DevicePreference",
    "get_smart_selector",
    "select_best_device", 
    "record_device_success",
    "record_device_failure"
]