"""
Audio Recorder for MeetingScribe

Module responsible for audio recording using WASAPI loopback devices.
Enables system audio capture for subsequent transcription.

Author: MeetingScribe Team
Version: 1.0.0
Python: >=3.8
"""

import wave
import threading
import time
import struct
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
import locale

from loguru import logger
from .devices import DeviceManager, AudioDevice, AudioDeviceError

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

try:
    import pyaudiowpatch as pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    try:
        import pyaudio
        PYAUDIO_AVAILABLE = True
        logger.warning("Using standard pyaudio - WASAPI features limited")
    except ImportError:
        PYAUDIO_AVAILABLE = False
        logger.error("PyAudio not available")


# Recording Quality Presets
class RecordingQuality:
    """Predefined recording quality presets"""

    # Quick/Draft quality - smaller files, lower quality
    QUICK = {
        'sample_rate': 16000,
        'channels': 1,
        'chunk_size': 2048,
        'name': 'Quick (16kHz Mono)',
        'description': 'Smaller files, good for voice notes',
        'size_per_min': '2 MB/min'
    }

    # Standard quality - balanced
    STANDARD = {
        'sample_rate': 44100,
        'channels': 2,
        'chunk_size': 4096,
        'name': 'Standard (44.1kHz Stereo)',
        'description': 'CD quality, balanced file size',
        'size_per_min': '10 MB/min'
    }

    # Professional quality - high quality for Teams meetings
    PROFESSIONAL = {
        'sample_rate': 48000,
        'channels': 2,
        'chunk_size': 4096,
        'name': 'Professional (48kHz Stereo)',
        'description': 'Professional quality for meetings',
        'size_per_min': '11 MB/min'
    }

    # High quality - maximum quality
    HIGH = {
        'sample_rate': 96000,
        'channels': 2,
        'chunk_size': 8192,
        'name': 'High (96kHz Stereo)',
        'description': 'Maximum quality, larger files',
        'size_per_min': '22 MB/min'
    }

    @classmethod
    def get_all(cls) -> Dict[str, Dict]:
        """Get all quality presets"""
        return {
            'quick': cls.QUICK,
            'standard': cls.STANDARD,
            'professional': cls.PROFESSIONAL,
            'high': cls.HIGH
        }

    @classmethod
    def get(cls, quality_name: str) -> Dict:
        """Get specific quality preset by name"""
        qualities = cls.get_all()
        return qualities.get(quality_name.lower(), cls.PROFESSIONAL)


@dataclass
class RecordingConfig:
    """
    Configuration for audio recording.

    Attributes:
        device: Audio device for recording
        sample_rate: Sample rate in Hz
        channels: Number of audio channels
        chunk_size: Buffer size in frames
        format: PyAudio audio format
        max_duration: Maximum duration in seconds (None = unlimited)
        output_dir: Directory to save recordings
        audio_format: File format ('wav' or 'm4a')
    """
    device: AudioDevice
    sample_rate: int = 48000  # Professional quality
    channels: int = 2         # Stereo
    chunk_size: int = 4096    # Larger buffer for smoother recording
    format: int = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None
    max_duration: Optional[int] = None
    output_dir: Path = field(default_factory=lambda: Path("storage/recordings"))
    audio_format: str = "wav"  # 'wav' or 'm4a'


@dataclass
class RecordingStats:
    """
    Statistics from a recording.

    Attributes:
        start_time: Start timestamp
        end_time: End timestamp
        duration: Duration in seconds
        file_size: File size in bytes
        samples_recorded: Total samples recorded
        filename: Generated filename
    """
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0
    file_size: int = 0
    samples_recorded: int = 0
    filename: Optional[str] = None


class AudioRecorderError(Exception):
    """Custom exception for audio recorder errors."""
    pass


class RecordingInProgressError(AudioRecorderError):
    """Exception for when a recording is already in progress."""
    pass


class AudioRecorder:
    """
    Audio recorder for system audio capture using WASAPI loopback.

    Enables continuous system audio recording with start/stop control,
    progress monitoring, and detailed statistics.
    """
    
    def __init__(self, config: Optional[RecordingConfig] = None):
        """
        Initialize the audio recorder.

        Args:
            config: Recording configuration. If None, uses default configuration.

        Raises:
            AudioRecorderError: If unable to initialize audio system
        """
        if not PYAUDIO_AVAILABLE:
            raise AudioRecorderError(
                "PyAudio not available. Install: pip install pyaudiowpatch"
            )

        self._config = config
        self._audio = None
        self._stream = None
        self._recording = False
        self._recording_thread = None
        self._frames = []
        self._stats = None
        self._progress_callback = None
        self._frames_captured = 0
        self._has_audio_detected = False
        self._audio_threshold = 100  # RMS threshold for silence detection

        self._initialize_audio_system()
    
    def _initialize_audio_system(self) -> None:
        """
        Initialize the PyAudio audio system.

        Raises:
            AudioRecorderError: If unable to initialize
        """
        try:
            self._audio = pyaudio.PyAudio()
            logger.info("Audio system for recording initialized")
        except Exception as e:
            logger.error(f"Failed to initialize audio system: {e}")
            raise AudioRecorderError(f"Could not initialize PyAudio: {e}") from e
    
    def set_device_auto(self) -> bool:
        """
        Automatically configure the best available device.

        Returns:
            bool: True if successfully configured a device
        """
        try:
            with DeviceManager() as dm:
                # Use specific function for devices capable of recording
                recording_devices = dm.get_recording_capable_devices()

                if recording_devices:
                    # Get the first suitable device (already sorted by preference)
                    device = recording_devices[0]

                    # Check if it has valid input channels
                    if device.max_input_channels == 0:
                        logger.warning(f"Device {device.name} has no input channels, searching for alternative...")

                        # Search for devices with valid input channels
                        valid_devices = [d for d in recording_devices if d.max_input_channels > 0]
                        if valid_devices:
                            device = valid_devices[0]
                        else:
                            logger.error("No device with valid input channels found")
                            return False

                    channels = min(device.max_input_channels, 2) if device.max_input_channels > 0 else 1

                    self._config = RecordingConfig(
                        device=device,
                        sample_rate=int(device.default_sample_rate),
                        channels=channels
                    )

                    logger.info(f"Device configured automatically: {device.name} (channels: {channels})")
                    return True

                logger.warning("No suitable device for recording found")
                return False

        except Exception as e:
            logger.error(f"Error configuring device automatically: {e}")
            return False
    
    def start_recording(self, filename: Optional[str] = None,
                       progress_callback: Optional[Callable[[float], None]] = None) -> str:
        """
        Start a new recording.

        Args:
            filename: Filename (without extension). If None, uses timestamp.
            progress_callback: Callback called with current duration in seconds

        Returns:
            str: Full path of the file that will be created

        Raises:
            RecordingInProgressError: If a recording is already in progress
            AudioRecorderError: If unable to start recording
        """
        if self._recording:
            raise RecordingInProgressError("Recording is already in progress")

        if not self._config:
            logger.info("Configuration not defined, detecting automatically...")
            if not self.set_device_auto():
                raise AudioRecorderError("Could not configure audio device")

        # Generate filename
        if not filename:
            # Use local time for the filename timestamp (Windows-compatible)
            local_time = datetime.now().astimezone()
            # Format: YYYYMMDD_HHMMSS (local timezone)
            timestamp = local_time.strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_{timestamp}"
            logger.debug(f"Generated filename with local timestamp: {timestamp}")

        # Ensure correct extension based on format
        audio_format = self._config.audio_format.lower()
        expected_ext = f".{audio_format}"

        # Remove old extension if exists
        for ext in ['.wav', '.m4a', '.mp4']:
            if filename.endswith(ext):
                filename = filename[:-len(ext)]
                break

        # Add correct extension
        if not filename.endswith(expected_ext):
            filename += expected_ext

        # Create full path
        self._config.output_dir.mkdir(parents=True, exist_ok=True)
        filepath = self._config.output_dir / filename

        # Configure progress callback
        self._progress_callback = progress_callback

        # Initialize statistics
        self._stats = RecordingStats(
            start_time=datetime.now(),
            filename=str(filepath)
        )

        # Clear previous frames
        self._frames = []

        try:
            # Open audio stream with specific configuration for loopback
            stream_config = {
                'format': self._config.format,
                'channels': self._config.channels,
                'rate': self._config.sample_rate,
                'input': True,
                'input_device_index': self._config.device.index,
                'frames_per_buffer': self._config.chunk_size
            }

            # Special configuration for WASAPI loopback devices
            if hasattr(self._config.device, 'is_loopback') and self._config.device.is_loopback:
                logger.debug("Configuring stream for WASAPI loopback device")
                # For pyaudiowpatch, loopback devices don't need the as_loopback parameter
                # The device index already identifies the correct loopback device

            logger.debug(f"Stream configuration: {stream_config}")
            self._stream = self._audio.open(**stream_config)

            logger.info(f"Audio stream opened for device {self._config.device.name}")

            # Start recording thread
            self._recording = True
            self._recording_thread = threading.Thread(target=self._recording_worker)
            self._recording_thread.daemon = True
            self._recording_thread.start()

            logger.info(f"Recording started: {filepath}")

            return str(filepath)

        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            self._cleanup_recording()
            raise AudioRecorderError(f"Failed to start recording: {e}") from e

    def _calculate_audio_level(self, data: bytes) -> float:
        """
        Calculate the RMS (Root Mean Square) level of audio.

        Args:
            data: Audio data in bytes (Int16 format)

        Returns:
            float: RMS level of the audio
        """
        import struct
        try:
            # Convert bytes to list of samples (Int16)
            samples = struct.unpack(f'<{len(data)//2}h', data)

            # Calculate RMS (Root Mean Square)
            if samples:
                sum_of_squares = sum(s ** 2 for s in samples)
                rms = (sum_of_squares / len(samples)) ** 0.5
                return rms
            return 0.0
        except Exception as e:
            logger.debug(f"Error calculating audio level: {e}")
            return 0.0

    def _recording_worker(self) -> None:
        """
        Worker thread that performs continuous recording.
        """
        logger.debug("Recording thread started")

        try:
            start_time = time.time()

            while self._recording:
                # Check duration limit
                current_time = time.time()
                duration = current_time - start_time

                if (self._config.max_duration and
                    duration >= self._config.max_duration):
                    logger.info(f"Maximum duration reached: {self._config.max_duration}s")
                    self._recording = False
                    break

                # Read data from stream
                try:
                    if not self._stream or self._stream.is_stopped():
                        logger.error("Audio stream was interrupted")
                        break

                    # Try to read with timeout to avoid freezing
                    try:
                        data = self._stream.read(self._config.chunk_size, exception_on_overflow=False)
                        # logger.debug(f"Data read from stream: {len(data)} bytes")
                    except OSError as e:
                        logger.error(f"OSError while reading from stream: {e}")
                        if "unanticipated host error" in str(e) or "device unavailable" in str(e):
                            logger.error("WASAPI device not available, stopping recording")
                            break
                        raise

                    if len(data) > 0:
                        self._frames.append(data)
                        self._frames_captured += 1
                        self._stats.samples_recorded += self._config.chunk_size

                        # Detect audio (check once)
                        if not self._has_audio_detected:
                            audio_level = self._calculate_audio_level(data)
                            if audio_level > self._audio_threshold:
                                self._has_audio_detected = True
                                logger.info(f"Audio detected! Level: {audio_level:.2f}")
                    else:
                        logger.warning("No data captured from audio stream")

                    # Call progress callback
                    if self._progress_callback:
                        try:
                            self._progress_callback(duration)
                        except Exception as e:
                            logger.warning(f"Error in progress callback: {e}")

                    # Small pause to avoid 100% CPU usage
                    time.sleep(0.05)  # More pause time to reduce load

                except Exception as e:
                    logger.warning(f"Error reading audio data: {e}")
                    # If error is critical, stop recording
                    if "invalid" in str(e).lower() or "closed" in str(e).lower():
                        logger.error("Stream invalid, stopping recording")
                        break
                    # Continue recording for other types of errors

        except Exception as e:
            logger.error(f"Critical error in recording thread: {e}")

        finally:
            if self._stream and not self._stream.is_stopped():
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                    logger.debug("Audio stream closed by recording thread")
                except Exception as e:
                    logger.warning(f"Error closing stream in thread: {e}")
            logger.debug("Recording thread finished")
    
    def stop_recording(self) -> RecordingStats:
        """
        Stop the current recording and save the file.

        Returns:
            RecordingStats: Recording statistics

        Raises:
            AudioRecorderError: If no recording is in progress or error saving
        """
        # Check if there is data to save (instead of checking _recording flag)
        # Because max_duration may have set _recording = False but still needs to save
        if not self._frames and not self._stats:
            raise AudioRecorderError("No recording to save")

        logger.info("Stopping recording...")

        # Stop recording
        self._recording = False

        # Wait for thread to finish
        if self._recording_thread:
            self._recording_thread.join(timeout=5.0)
            if self._recording_thread.is_alive():
                logger.warning("Recording thread did not finish in the expected time")

        # Close stream (moved to _recording_worker)
        self._stream = None

        # Finalize statistics
        self._stats.end_time = datetime.now()
        self._stats.duration = (self._stats.end_time - self._stats.start_time).total_seconds()

        # Save file
        try:
            self._save_recording()
            logger.info(f"Recording saved: {self._stats.filename}")
        except Exception as e:
            logger.error(f"Error saving recording: {e}")
            raise AudioRecorderError(f"Failed to save file: {e}") from e

        return self._stats
    
    def _save_recording(self) -> None:
        """
        Save recorded frames to file (WAV or M4A).

        Raises:
            AudioRecorderError: If unable to save file
        """
        logger.debug(f"Attempting to save recording with {len(self._frames)} frames")
        if not self._frames:
            raise AudioRecorderError("No audio data to save")

        try:
            audio_format = self._config.audio_format.lower() if self._config.audio_format else "wav"
            logger.debug(f"Saving in format: {audio_format}")

            if audio_format == "m4a":
                logger.debug(f"Using M4A method for {self._stats.filename}")
                self._save_as_m4a()
            else:
                logger.debug(f"Using WAV method for {self._stats.filename}")
                self._save_as_wav()

            # Update statistics
            file_path = Path(self._stats.filename)
            self._stats.file_size = file_path.stat().st_size

            logger.debug(f"File {self._config.audio_format.upper()} saved: {self._stats.file_size} bytes")

        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise AudioRecorderError(f"Failed to write file: {e}") from e

    def _save_as_wav(self) -> None:
        """
        Save recorded frames to WAV file.

        Raises:
            Exception: If unable to save file
        """
        with wave.open(self._stats.filename, 'wb') as wav_file:
            wav_file.setnchannels(self._config.channels)
            wav_file.setsampwidth(self._audio.get_sample_size(self._config.format))
            wav_file.setframerate(self._config.sample_rate)
            wav_file.writeframes(b''.join(self._frames))

        logger.debug(f"WAV file saved: {self._stats.filename}")

    def _save_as_m4a(self) -> None:
        """
        Save recorded frames to M4A file (AAC compressed).

        Raises:
            Exception: If unable to save file
        """
        if not PYDUB_AVAILABLE:
            logger.error("pydub not available for M4A encoding")
            raise AudioRecorderError(
                "pydub not available for M4A encoding. Install with: pip install pydub"
            )

        try:
            logger.debug(f"Starting M4A encoding with pydub for {self._stats.filename}")
            logger.debug(f"Configuration: {self._config.channels} channels, {self._config.sample_rate}Hz, {len(self._frames)} frames")

            # Convert bytes to AudioSegment
            audio_data = b''.join(self._frames)
            logger.debug(f"Audio data: {len(audio_data)} bytes")

            audio = AudioSegment(
                audio_data,
                sample_width=self._audio.get_sample_size(self._config.format),
                frame_rate=self._config.sample_rate,
                channels=self._config.channels
            )

            logger.debug(f"AudioSegment created: {len(audio)}ms duration")

            # Export as M4A
            logger.debug(f"Exporting to M4A with AAC @ 256k")
            audio.export(
                self._stats.filename,
                format="mp4",  # pydub uses "mp4" format for M4A/AAC
                codec="aac",
                bitrate="256k"
            )

            logger.info(f"M4A file saved successfully: {self._stats.filename}")

        except ImportError as e:
            logger.error(f"Import error when saving M4A (ffmpeg not installed?): {e}")
            raise AudioRecorderError(
                f"Failed to encode M4A. Check if ffmpeg is installed: {e}"
            )
        except Exception as e:
            logger.error(f"Error saving M4A: {type(e).__name__}: {e}")
            raise AudioRecorderError(f"Failed to save M4A file: {e}") from e
    
    def is_recording(self) -> bool:
        """
        Check if a recording is in progress.

        Returns:
            bool: True if recording
        """
        return self._recording

    def get_device_name(self) -> Optional[str]:
        """
        Get the name of the device being used.

        Returns:
            str: Device name
        """
        if self._config and self._config.device:
            return self._config.device.name
        return None

    def get_sample_rate(self) -> Optional[int]:
        """
        Get the sample rate.

        Returns:
            int: Sample rate in Hz
        """
        if self._config:
            return self._config.sample_rate
        return None

    def get_channels(self) -> Optional[int]:
        """
        Get the number of audio channels.

        Returns:
            int: Number of channels
        """
        if self._config:
            return self._config.channels
        return None

    def get_frames_captured(self) -> int:
        """
        Get the number of frames captured.

        Returns:
            int: Number of frames
        """
        return self._frames_captured

    def has_audio_detected(self) -> bool:
        """
        Check if audio was detected.

        Returns:
            bool: True if audio was detected
        """
        return self._has_audio_detected

    def get_current_stats(self) -> Optional[RecordingStats]:
        """
        Get statistics of the current recording.

        Returns:
            Optional[RecordingStats]: Statistics or None if not recording
        """
        if not self._stats:
            return None

        # Update current duration if recording
        if self._recording:
            current_time = datetime.now()
            self._stats.duration = (current_time - self._stats.start_time).total_seconds()

        return self._stats

    def _cleanup_recording(self) -> None:
        """
        Clean up recording resources in case of error.
        """
        self._recording = False

        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            finally:
                self._stream = None

        self._frames = []
        self._stats = None

    def close(self) -> None:
        """
        Finalize the recorder and release resources.
        """
        if self._recording:
            try:
                self.stop_recording()
            except Exception as e:
                logger.warning(f"Error stopping recording during close: {e}")

        if self._audio:
            try:
                self._audio.terminate()
                logger.info("Recorder audio system terminated")
            except Exception as e:
                logger.warning(f"Error terminating PyAudio: {e}")
            finally:
                self._audio = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_recorder_from_config() -> AudioRecorder:
    """
    Create a recorder using settings configuration.

    Returns:
        AudioRecorder: Configured recorder

    Raises:
        AudioRecorderError: If unable to create recorder
    """
    try:
        from config import settings

        recorder = AudioRecorder()

        if recorder.set_device_auto():
            # Update configuration with settings
            recorder._config.sample_rate = settings.audio_sample_rate
            recorder._config.channels = settings.audio_channels
            recorder._config.output_dir = settings.recordings_dir

            logger.info("Recorder created with system configuration")
            return recorder
        else:
            raise AudioRecorderError("Could not configure device automatically")

    except ImportError:
        logger.warning("Configuration not available, using defaults")
        recorder = AudioRecorder()
        recorder.set_device_auto()
        return recorder


def main():
    """
    Main function for testing and demonstrating AudioRecorder.
    """
    logger.info("Starting Audio Recorder demonstration")

    try:
        with create_recorder_from_config() as recorder:
            print("\n[AUDIO] AUDIO RECORDER DEMONSTRATION")
            print("="*50)

            # Show configuration
            config = recorder._config
            if config:
                print(f"Device: {config.device.name}")
                print(f"API: {config.device.host_api}")
                print(f"Rate: {config.sample_rate} Hz")
                print(f"Channels: {config.channels}")
                print(f"Loopback: {'Yes' if config.device.is_loopback else 'No'}")
            else:
                print("No configuration available")
                return

            # Test short recording
            print(f"\nStarting test recording (5 seconds)...")

            def progress_callback(duration):
                print(f"\rRecording: {duration:.1f}s", end="", flush=True)

            filepath = recorder.start_recording(
                filename="test_recording",
                progress_callback=progress_callback
            )

            # Wait 5 seconds
            time.sleep(5)

            # Stop recording
            print(f"\nStopping recording...")
            stats = recorder.stop_recording()

            # Show results
            print(f"\n[OK] Recording completed!")
            print(f"File: {stats.filename}")
            print(f"Duration: {stats.duration:.2f} seconds")
            print(f"Size: {stats.file_size} bytes")
            print(f"Samples: {stats.samples_recorded}")

    except AudioRecorderError as e:
        logger.error(f"Recorder error: {e}")
        print(f"[ERROR] Recorder error: {e}")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"[ERROR] Unexpected error: {e}")


if __name__ == "__main__":
    main()