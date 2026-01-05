"""
Dual Stream Audio Recorder for MeetingScribe

Records both system audio (speaker loopback) and microphone input simultaneously,
mixing them together into a single output file.

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
from typing import Optional, Callable, Dict, Any, List, Tuple
from dataclasses import dataclass, field

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


@dataclass
class DualRecordingConfig:
    """
    Configuration for dual-stream audio recording.

    Attributes:
        speaker_device: Audio device for speaker/loopback recording
        microphone_device: Audio device for microphone recording
        sample_rate: Sample rate in Hz (both streams normalized to this)
        channels: Number of output audio channels
        chunk_size: Buffer size in frames
        format: PyAudio audio format
        max_duration: Maximum duration in seconds (None = unlimited)
        output_dir: Directory to save recordings
        audio_format: File format ('wav' or 'm4a')
        mic_volume: Microphone volume multiplier (0.0-2.0, default 1.0)
        speaker_volume: Speaker volume multiplier (0.0-2.0, default 1.0)
    """
    speaker_device: Optional[AudioDevice] = None
    microphone_device: Optional[AudioDevice] = None
    sample_rate: int = 48000  # Professional quality
    channels: int = 2         # Stereo
    chunk_size: int = 4096    # Buffer size
    format: int = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None
    max_duration: Optional[int] = None
    output_dir: Path = field(default_factory=lambda: Path("storage/recordings"))
    audio_format: str = "wav"  # 'wav' or 'm4a'
    mic_volume: float = 1.0
    speaker_volume: float = 1.0


@dataclass
class DualRecordingStats:
    """
    Statistics from a dual-stream recording.

    Attributes:
        start_time: Start timestamp
        end_time: End timestamp
        duration: Duration in seconds
        file_size: File size in bytes
        samples_recorded: Total samples recorded
        filename: Generated filename
        speaker_device: Speaker device name
        microphone_device: Microphone device name
    """
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0
    file_size: int = 0
    samples_recorded: int = 0
    filename: Optional[str] = None
    speaker_device: Optional[str] = None
    microphone_device: Optional[str] = None


class DualStreamRecorderError(Exception):
    """Custom exception for dual stream recorder errors."""
    pass


class DualStreamRecorder:
    """
    Dual stream audio recorder for capturing both system audio and microphone.

    Records from speaker loopback and microphone simultaneously,
    mixing them into a single output file.
    """

    def __init__(self, config: Optional[DualRecordingConfig] = None):
        """
        Initialize the dual stream audio recorder.

        Args:
            config: Recording configuration. If None, uses default configuration.

        Raises:
            DualStreamRecorderError: If unable to initialize audio system
        """
        if not PYAUDIO_AVAILABLE:
            raise DualStreamRecorderError(
                "PyAudio not available. Install: pip install pyaudiowpatch"
            )

        self._config = config or DualRecordingConfig()
        self._audio = None
        self._speaker_stream = None
        self._mic_stream = None
        self._recording = False
        self._recording_thread = None
        self._frames: List[bytes] = []  # Mixed audio frames
        self._stats = None
        self._progress_callback = None
        self._frames_captured = 0
        self._has_audio_detected = False
        self._audio_threshold = 100
        self._lock = threading.Lock()

        if not NUMPY_AVAILABLE:
            logger.warning("NumPy not available - audio mixing will be limited (speaker-only fallback)")

        self._initialize_audio_system()

    def _initialize_audio_system(self) -> None:
        """Initialize the PyAudio audio system."""
        try:
            self._audio = pyaudio.PyAudio()
            logger.info("Dual stream audio system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize audio system: {e}")
            raise DualStreamRecorderError(f"Could not initialize PyAudio: {e}") from e

    def set_devices_auto(self) -> bool:
        """
        Automatically configure both speaker and microphone devices.

        Returns:
            bool: True if successfully configured both devices
        """
        try:
            with DeviceManager() as dm:
                # Get speaker/loopback device
                speaker_device = dm.get_default_speakers()
                if speaker_device and speaker_device.max_input_channels > 0:
                    self._config.speaker_device = speaker_device
                    logger.info(f"Speaker device configured: {speaker_device.name}")
                else:
                    # Fallback: search for any loopback device
                    recording_devices = dm.get_recording_capable_devices()
                    loopback_devices = [d for d in recording_devices if d.is_loopback]
                    if loopback_devices:
                        self._config.speaker_device = loopback_devices[0]
                        logger.info(f"Fallback speaker device: {loopback_devices[0].name}")
                    else:
                        logger.warning("No speaker/loopback device found")

                # Get microphone device
                mic_device = dm.get_system_default_input()
                if mic_device:
                    # Make sure it's not the same as the speaker device
                    if (self._config.speaker_device is None or
                        mic_device.index != self._config.speaker_device.index):
                        # Verify it's actually a microphone (not a loopback)
                        if not mic_device.is_loopback:
                            self._config.microphone_device = mic_device
                            logger.info(f"Microphone device configured: {mic_device.name}")
                        else:
                            # Find a non-loopback input device
                            all_devices = dm.list_all_devices()
                            mic_candidates = [
                                d for d in all_devices
                                if d.max_input_channels > 0
                                and not d.is_loopback
                                and ('microphone' in d.name.lower() or 'mic' in d.name.lower())
                            ]
                            if mic_candidates:
                                self._config.microphone_device = mic_candidates[0]
                                logger.info(f"Found microphone: {mic_candidates[0].name}")
                            else:
                                # Just find any non-loopback input
                                non_loopback_inputs = [
                                    d for d in all_devices
                                    if d.max_input_channels > 0 and not d.is_loopback
                                    and d.index != (self._config.speaker_device.index if self._config.speaker_device else -1)
                                ]
                                if non_loopback_inputs:
                                    self._config.microphone_device = non_loopback_inputs[0]
                                    logger.info(f"Using input device as mic: {non_loopback_inputs[0].name}")
                else:
                    logger.warning("No microphone device found")

                # Update sample rate based on devices
                if self._config.speaker_device:
                    self._config.sample_rate = int(self._config.speaker_device.default_sample_rate)
                    channels = min(self._config.speaker_device.max_input_channels, 2)
                    if channels > 0:
                        self._config.channels = channels

                # Log final configuration
                has_speaker = self._config.speaker_device is not None
                has_mic = self._config.microphone_device is not None
                logger.info(f"Dual recording config: speaker={has_speaker}, mic={has_mic}")

                return has_speaker  # At minimum we need the speaker

        except Exception as e:
            logger.error(f"Error configuring devices automatically: {e}")
            return False

    def _convert_audio_format(self, data: bytes, src_rate: int, dst_rate: int,
                              src_channels: int, dst_channels: int) -> bytes:
        """
        Convert audio data between different formats (sample rate and channels).

        Args:
            data: Input audio data
            src_rate: Source sample rate
            dst_rate: Destination sample rate
            src_channels: Source channel count
            dst_channels: Destination channel count

        Returns:
            bytes: Converted audio data
        """
        if src_rate == dst_rate and src_channels == dst_channels:
            return data

        try:
            # Convert bytes to numpy array
            samples = np.frombuffer(data, dtype=np.int16)

            # Handle channel conversion
            if src_channels != dst_channels:
                if src_channels == 1 and dst_channels == 2:
                    # Mono to stereo: duplicate the channel
                    samples = np.repeat(samples, 2)
                elif src_channels == 2 and dst_channels == 1:
                    # Stereo to mono: average channels
                    samples = samples.reshape(-1, 2).mean(axis=1).astype(np.int16)

            # Handle sample rate conversion (simple resampling)
            if src_rate != dst_rate:
                # Calculate new length
                new_length = int(len(samples) * dst_rate / src_rate)
                # Simple linear interpolation resampling
                indices = np.linspace(0, len(samples) - 1, new_length)
                samples = np.interp(indices, np.arange(len(samples)), samples).astype(np.int16)

            return samples.tobytes()

        except Exception as e:
            logger.warning(f"Audio format conversion failed: {e}, returning original")
            return data

    def _mix_audio_frames(self, speaker_data: bytes, mic_data: bytes) -> bytes:
        """
        Mix speaker and microphone audio data together.

        Args:
            speaker_data: Speaker audio data
            mic_data: Microphone audio data

        Returns:
            bytes: Mixed audio data
        """
        try:
            # Convert to numpy arrays
            speaker_samples = np.frombuffer(speaker_data, dtype=np.int16).astype(np.float32)
            mic_samples = np.frombuffer(mic_data, dtype=np.int16).astype(np.float32)

            # Apply volume adjustments
            speaker_samples *= self._config.speaker_volume
            mic_samples *= self._config.mic_volume

            # Ensure same length (pad shorter one with zeros)
            max_len = max(len(speaker_samples), len(mic_samples))
            if len(speaker_samples) < max_len:
                speaker_samples = np.pad(speaker_samples, (0, max_len - len(speaker_samples)))
            if len(mic_samples) < max_len:
                mic_samples = np.pad(mic_samples, (0, max_len - len(mic_samples)))

            # Mix the audio (simple addition with clipping prevention)
            mixed = speaker_samples + mic_samples

            # Normalize to prevent clipping
            max_val = np.max(np.abs(mixed))
            if max_val > 32767:
                mixed = mixed * (32767 / max_val)

            # Convert back to int16
            mixed = np.clip(mixed, -32768, 32767).astype(np.int16)

            return mixed.tobytes()

        except Exception as e:
            logger.warning(f"Audio mixing failed: {e}")
            # Return speaker data as fallback
            return speaker_data

    def start_recording(self, filename: Optional[str] = None,
                       progress_callback: Optional[Callable[[float], None]] = None) -> str:
        """
        Start a new dual-stream recording.

        Args:
            filename: Filename (without extension). If None, uses timestamp.
            progress_callback: Callback called with current duration in seconds

        Returns:
            str: Full path of the file that will be created

        Raises:
            DualStreamRecorderError: If unable to start recording
        """
        if self._recording:
            raise DualStreamRecorderError("Recording is already in progress")

        if not self._config.speaker_device:
            logger.info("No speaker device configured, detecting automatically...")
            if not self.set_devices_auto():
                raise DualStreamRecorderError("Could not configure audio devices")

        # Generate filename
        if not filename:
            local_time = datetime.now().astimezone()
            timestamp = local_time.strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_{timestamp}"

        # Ensure correct extension
        audio_format = self._config.audio_format.lower()
        expected_ext = f".{audio_format}"

        # Remove old extension if exists
        for ext in ['.wav', '.m4a', '.mp4']:
            if filename.endswith(ext):
                filename = filename[:-len(ext)]
                break

        if not filename.endswith(expected_ext):
            filename += expected_ext

        # Create full path
        self._config.output_dir.mkdir(parents=True, exist_ok=True)
        filepath = self._config.output_dir / filename

        # Configure progress callback
        self._progress_callback = progress_callback

        # Initialize statistics
        speaker_name = self._config.speaker_device.name if self._config.speaker_device else "None"
        mic_name = self._config.microphone_device.name if self._config.microphone_device else "None"

        self._stats = DualRecordingStats(
            start_time=datetime.now(),
            filename=str(filepath),
            speaker_device=speaker_name,
            microphone_device=mic_name
        )

        # Clear previous frames
        self._frames = []
        self._frames_captured = 0
        self._has_audio_detected = False

        try:
            # Open speaker stream
            if self._config.speaker_device:
                speaker_channels = min(self._config.speaker_device.max_input_channels, 2)
                if speaker_channels == 0:
                    speaker_channels = 2  # Default to stereo

                speaker_config = {
                    'format': self._config.format,
                    'channels': speaker_channels,
                    'rate': int(self._config.speaker_device.default_sample_rate),
                    'input': True,
                    'input_device_index': self._config.speaker_device.index,
                    'frames_per_buffer': self._config.chunk_size
                }
                logger.debug(f"Speaker stream config: {speaker_config}")
                self._speaker_stream = self._audio.open(**speaker_config)
                logger.info(f"Speaker stream opened: {self._config.speaker_device.name}")

            # Open microphone stream
            if self._config.microphone_device:
                mic_channels = min(self._config.microphone_device.max_input_channels, 2)
                if mic_channels == 0:
                    mic_channels = 1  # Default to mono for mic

                mic_config = {
                    'format': self._config.format,
                    'channels': mic_channels,
                    'rate': int(self._config.microphone_device.default_sample_rate),
                    'input': True,
                    'input_device_index': self._config.microphone_device.index,
                    'frames_per_buffer': self._config.chunk_size
                }
                logger.debug(f"Microphone stream config: {mic_config}")
                self._mic_stream = self._audio.open(**mic_config)
                logger.info(f"Microphone stream opened: {self._config.microphone_device.name}")

            # Start recording thread
            self._recording = True
            self._recording_thread = threading.Thread(target=self._recording_worker)
            self._recording_thread.daemon = True
            self._recording_thread.start()

            logger.info(f"Dual-stream recording started: {filepath}")

            return str(filepath)

        except Exception as e:
            logger.error(f"Error starting dual-stream recording: {e}")
            self._cleanup_recording()
            raise DualStreamRecorderError(f"Failed to start recording: {e}") from e

    def _calculate_audio_level(self, data: bytes) -> float:
        """Calculate the RMS level of audio."""
        try:
            samples = struct.unpack(f'<{len(data)//2}h', data)
            if samples:
                sum_of_squares = sum(s ** 2 for s in samples)
                rms = (sum_of_squares / len(samples)) ** 0.5
                return rms
            return 0.0
        except Exception:
            return 0.0

    def _recording_worker(self) -> None:
        """Worker thread that performs dual-stream recording."""
        logger.debug("Dual-stream recording thread started")

        # Get device parameters for format conversion
        speaker_rate = int(self._config.speaker_device.default_sample_rate) if self._config.speaker_device else self._config.sample_rate
        speaker_channels = min(self._config.speaker_device.max_input_channels, 2) if self._config.speaker_device else 2
        if speaker_channels == 0:
            speaker_channels = 2

        mic_rate = int(self._config.microphone_device.default_sample_rate) if self._config.microphone_device else self._config.sample_rate
        mic_channels = min(self._config.microphone_device.max_input_channels, 2) if self._config.microphone_device else 1
        if mic_channels == 0:
            mic_channels = 1

        target_rate = self._config.sample_rate
        target_channels = self._config.channels

        try:
            start_time = time.time()

            while self._recording:
                current_time = time.time()
                duration = current_time - start_time

                # Check duration limit
                if (self._config.max_duration and duration >= self._config.max_duration):
                    logger.info(f"Maximum duration reached: {self._config.max_duration}s")
                    self._recording = False
                    break

                try:
                    speaker_data = None
                    mic_data = None

                    # Read from speaker stream
                    if self._speaker_stream and not self._speaker_stream.is_stopped():
                        try:
                            speaker_data = self._speaker_stream.read(
                                self._config.chunk_size,
                                exception_on_overflow=False
                            )
                            # Convert to target format if needed
                            if NUMPY_AVAILABLE and speaker_data:
                                speaker_data = self._convert_audio_format(
                                    speaker_data, speaker_rate, target_rate,
                                    speaker_channels, target_channels
                                )
                        except Exception as e:
                            logger.warning(f"Error reading speaker stream: {e}")

                    # Read from microphone stream
                    if self._mic_stream and not self._mic_stream.is_stopped():
                        try:
                            mic_data = self._mic_stream.read(
                                self._config.chunk_size,
                                exception_on_overflow=False
                            )
                            # Convert to target format if needed
                            if NUMPY_AVAILABLE and mic_data:
                                mic_data = self._convert_audio_format(
                                    mic_data, mic_rate, target_rate,
                                    mic_channels, target_channels
                                )
                        except Exception as e:
                            logger.warning(f"Error reading microphone stream: {e}")

                    # Mix and store the audio
                    if speaker_data or mic_data:
                        with self._lock:
                            if speaker_data and mic_data and NUMPY_AVAILABLE:
                                # Mix both streams
                                mixed_data = self._mix_audio_frames(speaker_data, mic_data)
                                self._frames.append(mixed_data)
                            elif speaker_data:
                                self._frames.append(speaker_data)
                            elif mic_data:
                                self._frames.append(mic_data)

                            self._frames_captured += 1
                            self._stats.samples_recorded += self._config.chunk_size

                            # Detect audio
                            if not self._has_audio_detected:
                                data_to_check = speaker_data or mic_data
                                if data_to_check:
                                    audio_level = self._calculate_audio_level(data_to_check)
                                    if audio_level > self._audio_threshold:
                                        self._has_audio_detected = True
                                        logger.info(f"Audio detected! Level: {audio_level:.2f}")

                    # Call progress callback
                    if self._progress_callback:
                        try:
                            self._progress_callback(duration)
                        except Exception as e:
                            logger.warning(f"Error in progress callback: {e}")

                    # Small pause to avoid 100% CPU usage
                    time.sleep(0.01)

                except Exception as e:
                    logger.warning(f"Error in recording loop: {e}")
                    if "invalid" in str(e).lower() or "closed" in str(e).lower():
                        logger.error("Stream invalid, stopping recording")
                        break

        except Exception as e:
            logger.error(f"Critical error in recording thread: {e}")

        finally:
            # Close streams
            for stream, name in [(self._speaker_stream, "speaker"), (self._mic_stream, "microphone")]:
                if stream and not stream.is_stopped():
                    try:
                        stream.stop_stream()
                        stream.close()
                        logger.debug(f"{name.capitalize()} stream closed")
                    except Exception as e:
                        logger.warning(f"Error closing {name} stream: {e}")

            logger.debug("Dual-stream recording thread finished")

    def stop_recording(self) -> DualRecordingStats:
        """
        Stop the current recording and save the file.

        Returns:
            DualRecordingStats: Recording statistics

        Raises:
            DualStreamRecorderError: If no recording is in progress or error saving
        """
        if not self._frames and not self._stats:
            raise DualStreamRecorderError("No recording to save")

        logger.info("Stopping dual-stream recording...")

        self._recording = False

        # Wait for thread to finish
        if self._recording_thread:
            self._recording_thread.join(timeout=5.0)
            if self._recording_thread.is_alive():
                logger.warning("Recording thread did not finish in expected time")

        # Clear stream references
        self._speaker_stream = None
        self._mic_stream = None

        # Finalize statistics
        self._stats.end_time = datetime.now()
        self._stats.duration = (self._stats.end_time - self._stats.start_time).total_seconds()

        # Save file
        try:
            self._save_recording()
            logger.info(f"Recording saved: {self._stats.filename}")
        except Exception as e:
            logger.error(f"Error saving recording: {e}")
            raise DualStreamRecorderError(f"Failed to save file: {e}") from e

        return self._stats

    def _save_recording(self) -> None:
        """Save recorded frames to file (WAV or M4A)."""
        logger.debug(f"Saving recording with {len(self._frames)} frames")
        if not self._frames:
            raise DualStreamRecorderError("No audio data to save")

        try:
            audio_format = self._config.audio_format.lower()
            logger.debug(f"Saving in format: {audio_format}")

            if audio_format == "m4a":
                self._save_as_m4a()
            else:
                self._save_as_wav()

            # Update statistics
            file_path = Path(self._stats.filename)
            self._stats.file_size = file_path.stat().st_size

            logger.debug(f"File saved: {self._stats.file_size} bytes")

        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise DualStreamRecorderError(f"Failed to write file: {e}") from e

    def _save_as_wav(self) -> None:
        """Save recorded frames to WAV file."""
        with wave.open(self._stats.filename, 'wb') as wav_file:
            wav_file.setnchannels(self._config.channels)
            wav_file.setsampwidth(self._audio.get_sample_size(self._config.format))
            wav_file.setframerate(self._config.sample_rate)
            with self._lock:
                wav_file.writeframes(b''.join(self._frames))

        logger.debug(f"WAV file saved: {self._stats.filename}")

    def _save_as_m4a(self) -> None:
        """Save recorded frames to M4A file (AAC compressed)."""
        if not PYDUB_AVAILABLE:
            raise DualStreamRecorderError(
                "pydub not available for M4A encoding. Install with: pip install pydub"
            )

        try:
            with self._lock:
                audio_data = b''.join(self._frames)

            audio = AudioSegment(
                audio_data,
                sample_width=self._audio.get_sample_size(self._config.format),
                frame_rate=self._config.sample_rate,
                channels=self._config.channels
            )

            audio.export(
                self._stats.filename,
                format="mp4",
                codec="aac",
                bitrate="256k"
            )

            logger.info(f"M4A file saved: {self._stats.filename}")

        except Exception as e:
            logger.error(f"Error saving M4A: {e}")
            raise DualStreamRecorderError(f"Failed to save M4A file: {e}") from e

    def is_recording(self) -> bool:
        """Check if a recording is in progress."""
        return self._recording

    def get_device_names(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the names of both devices being used."""
        speaker = self._config.speaker_device.name if self._config.speaker_device else None
        mic = self._config.microphone_device.name if self._config.microphone_device else None
        return (speaker, mic)

    def get_sample_rate(self) -> int:
        """Get the sample rate."""
        return self._config.sample_rate

    def get_channels(self) -> int:
        """Get the number of audio channels."""
        return self._config.channels

    def get_frames_captured(self) -> int:
        """Get the number of frames captured."""
        return self._frames_captured

    def has_audio_detected(self) -> bool:
        """Check if audio was detected."""
        return self._has_audio_detected

    def get_current_stats(self) -> Optional[DualRecordingStats]:
        """Get statistics of the current recording."""
        if not self._stats:
            return None

        if self._recording:
            current_time = datetime.now()
            self._stats.duration = (current_time - self._stats.start_time).total_seconds()

        return self._stats

    def _cleanup_recording(self) -> None:
        """Clean up recording resources in case of error."""
        self._recording = False

        for stream in [self._speaker_stream, self._mic_stream]:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass

        self._speaker_stream = None
        self._mic_stream = None
        self._frames = []
        self._stats = None

    def close(self) -> None:
        """Finalize the recorder and release resources."""
        if self._recording:
            try:
                self.stop_recording()
            except Exception as e:
                logger.warning(f"Error stopping recording during close: {e}")

        if self._audio:
            try:
                self._audio.terminate()
                logger.info("Dual stream recorder audio system terminated")
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
