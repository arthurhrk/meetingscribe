"""
Device Manager for MeetingScribe

Manages Windows audio devices using pyaudiowpatch for WASAPI capture.
Responsible for detecting and configuring loopback devices for system
audio recording.

Author: MeetingScribe Team
Version: 1.0.0
Python: >=3.8
"""

import sys
import json
import argparse
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from loguru import logger

try:
    import pyaudiowpatch as pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    logger.warning("pyaudiowpatch not available - limited audio functionalities")
    try:
        import pyaudio
        PYAUDIO_AVAILABLE = True
        logger.info("Using standard pyaudio as a fallback")
    except ImportError:
        PYAUDIO_AVAILABLE = False
        logger.error("No audio library available")


@dataclass
class AudioDevice:
    """
    Represents an audio device with its properties.
    
    Attributes:
        index: Device index in the system
        name: Device name
        max_input_channels: Maximum number of input channels
        max_output_channels: Maximum number of output channels
        default_sample_rate: Default sample rate
        host_api: Host API (WASAPI, MME, etc.)
        is_loopback: Whether it is a loopback device
        is_default: Whether it is the system's default device
    """
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float
    host_api: str
    is_loopback: bool = False
    is_default: bool = False


class AudioDeviceError(Exception):
    """Custom exception for audio device errors."""
    pass


class WASAPINotAvailableError(AudioDeviceError):
    """Exception for when WASAPI is not available."""
    pass


class DeviceManager:
    """
    Audio device manager for Windows.
    
    Utiliza pyaudiowpatch para acessar dispositivos WASAPI loopback,
    allowing system audio capture without the need for manual
    audio mixer configuration.
    """
    
    def __init__(self):
        """
        Initializes the device manager.
        
        Raises:
            AudioDeviceError: If it fails to initialize the audio system
            WASAPINotAvailableError: If WASAPI is not available
        """
        self._audio = None
        self._devices_cache = None
        self._initialize_audio_system()
    
    def _initialize_audio_system(self) -> None:
        """
        Initializes the PyAudio audio system.
        
        Raises:
            AudioDeviceError: If it fails to initialize
            WASAPINotAvailableError: If WASAPI is not available
        """
        if not PYAUDIO_AVAILABLE:
            raise AudioDeviceError(
                "Audio system not available. "
                "Install pyaudiowpatch: pip install pyaudiowpatch"
            )
        
        try:
            self._audio = pyaudio.PyAudio()
            logger.info("Audio system initialized successfully")
            
            # Check if WASAPI is available
            if not self._is_wasapi_available():
                raise WASAPINotAvailableError(
                    "WASAPI is not available on this system. "
                    "Loopback functionalities will not work."
                )
            
            logger.info("WASAPI detected and available for use")
            
        except Exception as e:
            logger.error(f"Failed to initialize audio system: {e}")
            raise AudioDeviceError(f"Could not initialize PyAudio: {e}") from e
    
    def _is_wasapi_available(self) -> bool:
        """
        Checks if WASAPI is available on the system.
        
        Returns:
            bool: True if WASAPI is available
        """
        try:
            host_api_count = self._audio.get_host_api_count()
            for i in range(host_api_count):
                host_api_info = self._audio.get_host_api_info_by_index(i)
                if host_api_info['name'].lower() == 'windows wasapi':
                    logger.debug(f"WASAPI found at index {i}")
                    return True
            
            logger.warning("WASAPI not found in available host APIs")
            return False
            
        except Exception as e:
            logger.error(f"Error checking WASAPI availability: {e}")
            return False
    
    def get_default_speakers(self) -> Optional[AudioDevice]:
        """
        Detects and returns the default speakers device with loopback support.
        
        Specifically looks for WASAPI loopback devices that correspond
        to the system's default speakers for output audio capture.
        
        Returns:
            Optional[AudioDevice]: Default speakers device or None if not found
            
        Raises:
            AudioDeviceError: If there is an error accessing devices
        """
        logger.info("Looking for default speakers device with loopback support")
        
        try:
            devices = self.list_all_devices()
            # First, try to find an explicit loopback device
            loopback_devices = [d for d in devices if d.is_loopback]
            
            if loopback_devices:
                # Prefer default device among loopbacks
                default_loopback = next((d for d in loopback_devices if d.is_default), None)
                if default_loopback:
                    logger.info(f"Default loopback device found: {default_loopback.name}")
                    return default_loopback
                
                # If there is no default, take the first loopback
                first_loopback = loopback_devices[0]
                logger.info(f"Using first loopback device: {first_loopback.name}")
                return first_loopback
            
            # Fallback: look for WASAPI output devices
            wasapi_output_devices = [
                d for d in devices 
                if d.host_api.lower() == 'windows wasapi' and d.max_output_channels > 0
            ]
            
            if wasapi_output_devices:
                # Prefer default device
                default_wasapi = next((d for d in wasapi_output_devices if d.is_default), None)
                if default_wasapi:
                    logger.info(f"Default WASAPI device found: {default_wasapi.name}")
                    return default_wasapi
                
                # If there is no default, take the first one
                first_wasapi = wasapi_output_devices[0]
                logger.info(f"Using first WASAPI device: {first_wasapi.name}")
                return first_wasapi
            
            logger.warning("No WASAPI output device found")
            return None
            
        except Exception as e:
            logger.error(f"Error detecting default speakers: {e}")
            raise AudioDeviceError(f"Failed to detect default device: {e}") from e
    
    def list_all_devices(self, refresh_cache: bool = False) -> List[AudioDevice]:
        """
        Lists all available audio devices on the system.
        
        Args:
            refresh_cache: If True, reloads the device list
            
        Returns:
            List[AudioDevice]: List of all available devices
            
        Raises:
            AudioDeviceError: If there is an error listing devices
        """
        if self._devices_cache is not None and not refresh_cache:
            logger.debug("Returning devices from cache")
            return self._devices_cache
        
        logger.info("Listing all available audio devices")
        
        try:
            devices = []
            device_count = self._audio.get_device_count()
            
            logger.debug(f"Total devices detected: {device_count}")
            
            for i in range(device_count):
                try:
                    device_info = self._audio.get_device_info_by_index(i)
                    host_api_info = self._audio.get_host_api_info_by_index(
                        device_info['hostApi']
                    )
                    
                    device = AudioDevice(
                        index=i,
                        name=device_info['name'],
                        max_input_channels=device_info['maxInputChannels'],
                        max_output_channels=device_info['maxOutputChannels'],
                        default_sample_rate=device_info['defaultSampleRate'],
                        host_api=host_api_info['name'],
                        is_loopback=self._is_loopback_device(device_info),
                        is_default=self._is_default_device(device_info, i)
                    )
                    
                    devices.append(device)
                    
                    logger.debug(
                        f"Device {i}: {device.name} "
                        f"(API: {device.host_api}, "
                        f"In: {device.max_input_channels}, "
                        f"Out: {device.max_output_channels}, "
                        f"Loopback: {device.is_loopback})"
                    )
                    
                except Exception as e:
                    logger.warning(f"Error processing device {i}: {e}")
                    continue
            
            self._devices_cache = devices
            logger.info(f"Total of {len(devices)} devices listed successfully")
            
            return devices
            
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            raise AudioDeviceError(f"Failed to list devices: {e}") from e
    
    def _is_loopback_device(self, device_info: Dict[str, Any]) -> bool:
        """
        Determines if a device is a loopback device.
        
        Args:
            device_info: Device information from PyAudio
            
        Returns:
            bool: True if it is a loopback device
        """
        device_name = device_info['name'].lower()
        
        # Common indicators of loopback devices
        loopback_indicators = [
            'loopback',
            'stereo mix',
            'what u hear',
            'wave out mix',
            'speakers (',  # Formato comum do WASAPI loopback
            'headphones (',
        ]
        
        for indicator in loopback_indicators:
            if indicator in device_name:
                return True
        
        # Check if it only has input channels (typical for loopback)
        if (device_info['maxInputChannels'] > 0 and 
            device_info['maxOutputChannels'] == 0 and
            'wasapi' in device_info.get('hostApi', 0)):
            return True
        
        return False
    
    def _is_default_device(self, device_info: Dict[str, Any], device_index: int) -> bool:
        """
        Checks if a device is the system's default device.
        
        Args:
            device_info: Device information
            device_index: Device index
            
        Returns:
            bool: True if it is the default device
        """
        try:
            # Check if it is the default input device
            default_input = self._audio.get_default_input_device_info()
            if default_input and default_input['index'] == device_index:
                return True
            
            # Check if it is the default output device
            default_output = self._audio.get_default_output_device_info()
            if default_output and default_output['index'] == device_index:
                return True
            
        except Exception as e:
            logger.debug(f"Error checking default device for {device_index}: {e}")
        
        return False
    
    def get_device_by_index(self, index: int) -> Optional[AudioDevice]:
        """
        Gets a specific device by its index.
        
        Args:
            index: Device index
            
        Returns:
            Optional[AudioDevice]: Found device or None
        """
        devices = self.list_all_devices()
        return next((d for d in devices if d.index == index), None)
    
    def get_devices_by_api(self, api_name: str) -> List[AudioDevice]:
        """
        Filters devices by host API.
        
        Args:
            api_name: API name (e.g., 'Windows WASAPI', 'MME')
            
        Returns:
            List[AudioDevice]: List of devices from the specified API
        """
        devices = self.list_all_devices()
        return [d for d in devices if api_name.lower() in d.host_api.lower()]
    
    def get_recording_capable_devices(self) -> List[AudioDevice]:
        """
        Filters devices suitable for recording (with input channels > 0).
        
        Returns:
            List[AudioDevice]: List of devices that can be used for recording
        """
        devices = self.list_all_devices()
        recording_devices = [d for d in devices if d.max_input_channels > 0]
        # Sort by preference: WASAPI loopback first, then default, then others
        def sort_key(device):
            score = 0
            if device.host_api.lower() == 'windows wasapi':
                score += 30
            if device.is_loopback:
                score += 20  
            if device.is_default:
                score += 10
            return -score  # Negative for descending order
        
        return sorted(recording_devices, key=sort_key)
    
    def get_system_default_input(self) -> Optional[AudioDevice]:
        """
        Gets the system's default input device.
        
        Returns:
            Optional[AudioDevice]: Default input device or None
        """
        try:
            default_input_info = self._audio.get_default_input_device_info()
            if default_input_info:
                return self.get_device_by_index(default_input_info['index'])
        except Exception as e:
            logger.debug(f"Error getting default input device: {e}")
        return None
    
    def get_system_default_output(self) -> Optional[AudioDevice]:
        """
        Gets the system's default output device.
        
        Returns:
            Optional[AudioDevice]: Default output device or None
        """
        try:
            default_output_info = self._audio.get_default_output_device_info()
            if default_output_info:
                return self.get_device_by_index(default_output_info['index'])
        except Exception as e:
            logger.debug(f"Error getting default output device: {e}")
        return None
    
    def print_device_info(self, device: AudioDevice) -> None:
        """
        Prints detailed information for a device.
        
        Args:
            device: Device to print information for
        """
        print(f"\n{'='*50}")
        print(f"Device: {device.name}")
        print(f"{'='*50}")
        print(f"Index: {device.index}")
        print(f"Host API: {device.host_api}")
        print(f"Input Channels: {device.max_input_channels}")
        print(f"Output Channels: {device.max_output_channels}")
        print(f"Sample Rate: {device.default_sample_rate} Hz")
        print(f"Is Loopback: {'Yes' if device.is_loopback else 'No'}")
        print(f"Is Default: {'Yes' if device.is_default else 'No'}")
        print(f"{'='*50}")
    
    def close(self) -> None:
        """
        Closes the audio system and releases resources.
        """
        if self._audio:
            try:
                self._audio.terminate()
                logger.info("Audio system terminated")
            except Exception as e:
                logger.warning(f"Error terminating audio system: {e}")
            finally:
                self._audio = None
                self._devices_cache = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """
    Main function for testing and demonstrating the DeviceManager.
    """
    parser = argparse.ArgumentParser(description='MeetingScribe Device Manager')
    parser.add_argument('--list-json', action='store_true', help='List devices in JSON format')
    parser.add_argument('--recording-only', action='store_true', help='List only devices suitable for recording')
    args = parser.parse_args()
    
    if args.list_json:
        try:
            with DeviceManager() as dm:
                if args.recording_only:
                    # List only devices suitable for recording, with "Same as System" options
                    devices = dm.get_recording_capable_devices()
                    device_list = []
                    
                    # Find the best default loopback device
                    default_speakers = dm.get_default_speakers()
                    if default_speakers and default_speakers.max_input_channels > 0:
                        device_list.append({
                            "id": "system_output",
                            "name": "Same as System (Output Loopback)",
                            "index": default_speakers.index,
                            "max_input_channels": default_speakers.max_input_channels,
                            "max_output_channels": default_speakers.max_output_channels,
                            "default_sample_rate": default_speakers.default_sample_rate,
                            "host_api": default_speakers.host_api,
                            "is_loopback": default_speakers.is_loopback,
                            "is_default": True,
                            "is_system_default": True
                        })
                    
                    # Add option for default input if it's different and suitable
                    default_input = dm.get_system_default_input()
                    if (default_input and default_input.max_input_channels > 0 and 
                        (not default_speakers or default_input.index != default_speakers.index)):
                        device_list.append({
                            "id": "system_input",
                            "name": "Same as System (Microphone)",
                            "index": default_input.index,
                            "max_input_channels": default_input.max_input_channels,
                            "max_output_channels": default_input.max_output_channels,
                            "default_sample_rate": default_input.default_sample_rate,
                            "host_api": default_input.host_api,
                            "is_loopback": default_input.is_loopback,
                            "is_default": True,
                            "is_system_default": True
                        })
                    
                    # Add devices suitable for recording (only with input channels > 0)
                    for device in devices:
                        if device.max_input_channels > 0:  # Additional filter
                            device_dict = asdict(device)
                            device_dict['id'] = str(device.index)
                            device_dict['is_system_default'] = False
                            device_list.append(device_dict)
                else:
                    # List all devices
                    devices = dm.list_all_devices()
                    device_list = []
                    
                    for device in devices:
                        device_dict = asdict(device)
                        device_dict['id'] = str(device.index)
                        device_dict['is_system_default'] = False
                        device_list.append(device_dict)
                
                print(json.dumps(device_list, indent=2, ensure_ascii=False))
                return
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            return
    
    # Original interactive mode
    logger.info("Starting Device Manager demonstration")
    
    try:
        with DeviceManager() as dm:
            # List all devices
            print("\n[AUDIO] LISTING ALL AUDIO DEVICES")
            print("="*60)
            
            devices = dm.list_all_devices()
            
            for device in devices:
                status_icons = []
                if device.is_default:
                    status_icons.append("[DEFAULT] Default")
                if device.is_loopback:
                    status_icons.append("[LOOP] Loopback")
                if device.host_api.lower() == 'windows wasapi':
                    status_icons.append("[WASAPI] WASAPI")
                
                status = " | ".join(status_icons) if status_icons else ""
                
                print(f"[{device.index:2d}] {device.name}")
                print(f"     API: {device.host_api}")
                print(f"     In: {device.max_input_channels} | Out: {device.max_output_channels}")
                if status:
                    print(f"     Status: {status}")
                print()
            
            # Detect default speakers device
            print("\n[SPEAKERS] DETECTING DEFAULT SPEAKERS DEVICE")
            print("="*60)
            
            default_speakers = dm.get_default_speakers()
            
            if default_speakers:
                print("[OK] Default device found!")
                dm.print_device_info(default_speakers)
            else:
                print("[ERROR] No default device found")
            
            # Filter WASAPI devices
            print("\n[WASAPI] AVAILABLE WASAPI DEVICES")
            print("="*60)
            
            wasapi_devices = dm.get_devices_by_api('Windows WASAPI')
            
            if wasapi_devices:
                for device in wasapi_devices:
                    print(f"[{device.index}] {device.name}")
                    if device.is_loopback:
                        print("    [LOOP] Loopback support")
                    if device.is_default:
                        print("    [DEFAULT] Default Device")
                    print()
            else:
                print("[ERROR] No WASAPI device found")
            
    except WASAPINotAvailableError:
        logger.error("WASAPI is not available on this system")
        print("[ERROR] WASAPI not available - loopback functionalities are limited")
        
    except AudioDeviceError as e:
        logger.error(f"Audio system error: {e}")
        print(f"[ERROR] Audio system error: {e}")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"[ERROR] Unexpected error: {e}")


if __name__ == "__main__":
    main()