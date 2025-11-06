#!/usr/bin/env python3
"""
MeetingScribe CLI - Teams Recording Focus
Simple interface for recording Teams meetings with high-quality audio.
"""

import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional


def quick_record(duration: int = 30, filename: Optional[str] = None, audio_format: str = "wav") -> dict:
    """
    Quick recording function for Raycast integration.
    Returns JSON immediately, continues recording in background.

    Args:
        duration: Recording duration in seconds
        filename: Optional custom filename
        audio_format: Audio format ('wav' or 'm4a')

    Returns:
        dict: Status and recording info
    """
    # Lazy import - only load when actually recording
    from loguru import logger
    from config import settings
    from audio import AudioRecorder, AudioRecorderError, RecordingQuality

    logger.debug(f"========================================")
    logger.debug(f"quick_record() called with:")
    logger.debug(f"  duration: {duration}")
    logger.debug(f"  filename: {filename}")
    logger.debug(f"  audio_format: {audio_format}")
    logger.debug(f"========================================")

    # Generate identifiers using local timezone (Windows-compatible)
    local_now = datetime.now().astimezone()
    timestamp = local_now.strftime("%Y%m%d_%H%M%S")
    session_id = f"rec-{timestamp}"
    if not filename:
        ext = audio_format.lower() if audio_format.lower() in ['wav', 'm4a'] else 'wav'
        filename = f"recording_{timestamp}.{ext}"
        logger.debug(f"Generated filename: {filename} (format: {audio_format})")

    filepath = Path(settings.recordings_dir) / filename
    status_file = Path(settings.status_dir) / f"{session_id}.json"

    # Ensure status directory exists
    settings.status_dir.mkdir(parents=True, exist_ok=True)

    # Return JSON immediately
    result = {
        "status": "success",
        "data": {
            "session_id": session_id,
            "file_path": str(filepath),
            "filename": filename,
            "duration": duration,
            "message": "Recording started successfully"
        }
    }

    # Start recording in background thread
    def record_worker():
        """Background worker for recording with status updates"""
        start_time = time.time()

        try:
            recorder = AudioRecorder()

            # Auto-select best device (WASAPI loopback preferred)
            if not recorder.set_device_auto():
                logger.error("Failed to select audio device")
                # Write error status
                status_file.write_text(json.dumps({
                    "status": "error",
                    "session_id": session_id,
                    "error": "Failed to select audio device"
                }))
                return

            # Handle manual mode (duration = -1)
            # Convert to 120 minutes (7200 seconds) as practical limit for manual mode
            max_duration = None if duration == -1 else duration
            effective_duration = 7200 if duration == -1 else duration
            is_manual_mode = duration == -1

            # Configure duration and format
            recorder._config.max_duration = max_duration
            recorder._config.audio_format = audio_format.lower()

            logger.debug(f"========================================")
            logger.debug(f"Recorder configuration:")
            logger.debug(f"  max_duration: {recorder._config.max_duration}")
            logger.debug(f"  audio_format: {recorder._config.audio_format}")
            logger.debug(f"  device: {recorder._config.device.name if recorder._config.device else 'None'}")
            logger.debug(f"  sample_rate: {recorder._config.sample_rate}")
            logger.debug(f"  channels: {recorder._config.channels}")
            logger.debug(f"========================================")

            # Start recording
            recorder.start_recording(filename=filename)
            logger.info(f"Recording started: {filename} ({duration}s, format: {audio_format})")

            # Write initial status with metadata
            quality_preset = RecordingQuality.get('professional')
            initial_display_duration = 0 if is_manual_mode else duration
            status_file.write_text(json.dumps({
                "status": "recording",
                "session_id": session_id,
                "filename": filename,
                "duration": initial_display_duration,
                "elapsed": 0,
                "progress": 0,
                "quality": "professional",
                "quality_info": {
                    "name": quality_preset['name'],
                    "description": quality_preset['description'],
                    "size_per_min": quality_preset['size_per_min']
                },
                "device": recorder.get_device_name(),
                "sample_rate": recorder.get_sample_rate(),
                "channels": recorder.get_channels(),
                "frames_captured": 0,
                "has_audio": False
            }))

            # Update status every second
            for i in range(effective_duration):
                time.sleep(1)
                elapsed = int(time.time() - start_time)

                # Check for stop signal file (for manual mode or graceful shutdown)
                # Frontend writes signals to storage/signals/, not storage/status/
                signals_dir = Path(settings.storage_dir) / "signals"
                stop_signal_file = signals_dir / f"{session_id}.stop"
                if stop_signal_file.exists():
                    logger.info(f"Stop signal received for session {session_id}")
                    try:
                        stop_signal_file.unlink()  # Clean up signal file
                    except Exception as e:
                        logger.warning(f"Could not delete stop signal file: {e}")
                    break

                # Calculate progress based on mode
                if is_manual_mode:
                    progress = 0  # Manual mode doesn't show percentage
                    display_duration = 0  # Indicate no time limit
                else:
                    progress = min(100, int((elapsed / duration) * 100))
                    display_duration = duration

                status_file.write_text(json.dumps({
                    "status": "recording",
                    "session_id": session_id,
                    "filename": filename,
                    "duration": display_duration,
                    "elapsed": elapsed,
                    "progress": progress,
                    "quality": "professional",
                    "quality_info": {
                        "name": quality_preset['name'],
                        "description": quality_preset['description'],
                        "size_per_min": quality_preset['size_per_min']
                    },
                    "device": recorder.get_device_name(),
                    "sample_rate": recorder.get_sample_rate(),
                    "channels": recorder.get_channels(),
                    "frames_captured": recorder.get_frames_captured(),
                    "has_audio": recorder.has_audio_detected()
                }))

            # Stop recording
            recorder.stop_recording()
            logger.info(f"Recording completed: {filepath}")

            recorder.close()

            # Wait a moment for file to be fully written
            time.sleep(1)

            # Get file size
            file_size_mb = round(filepath.stat().st_size / (1024 * 1024), 2) if filepath.exists() else 0

            # Write completion status with all metadata
            status_file.write_text(json.dumps({
                "status": "completed",
                "session_id": session_id,
                "filename": filename,
                "duration": duration,
                "file_size_mb": file_size_mb,
                "quality": "professional",
                "quality_info": {
                    "name": quality_preset['name'],
                    "description": quality_preset['description'],
                    "size_per_min": quality_preset['size_per_min']
                },
                "device": recorder.get_device_name(),
                "sample_rate": recorder.get_sample_rate(),
                "channels": recorder.get_channels(),
                "frames_captured": recorder.get_frames_captured(),
                "has_audio": recorder.has_audio_detected()
            }))

            logger.info(f"Status updated to completed: {file_size_mb}MB")

        except AudioRecorderError as e:
            logger.error(f"Recording error: {e}")
            status_file.write_text(json.dumps({
                "status": "error",
                "session_id": session_id,
                "error": f"Recording error: {str(e)}"
            }))
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            status_file.write_text(json.dumps({
                "status": "error",
                "session_id": session_id,
                "error": f"Unexpected error: {str(e)}"
            }))

    # Start non-daemon thread (keeps process alive)
    thread = threading.Thread(target=record_worker, daemon=False)
    thread.start()

    return result, thread


def main():
    """Main CLI entry point"""

    # Check if called with arguments (Raycast integration)
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "record":
            # Quick record mode - return JSON IMMEDIATELY before logging setup
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            audio_format = sys.argv[3] if len(sys.argv) > 3 else "wav"

            result, thread = quick_record(duration=duration, audio_format=audio_format)
            print(json.dumps(result), flush=True)

            # Wait for recording to complete (in background)
            thread.join()
            return

        elif command == "status":
            # System status check - lazy import
            from audio import DeviceManager

            try:
                dm = DeviceManager()
                devices = dm.list_all_devices()

                result = {
                    "status": "success",
                    "data": {
                        "devices_count": len(devices),
                        "devices": [
                            {
                                "name": d.name,
                                "is_loopback": d.is_loopback,
                                "channels": d.max_input_channels
                            }
                            for d in devices
                        ]
                    }
                }
                print(json.dumps(result), flush=True)
                return

            except Exception as e:
                result = {
                    "status": "error",
                    "message": str(e)
                }
                print(json.dumps(result), flush=True)
                return

    # Interactive mode - only initialize logging if running interactively
    from loguru import logger
    from config import settings

    logger.remove()
    logger.add(
        settings.logs_dir / "meetingscribe.log",
        rotation="10 MB",
        retention="1 month",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )

    print("=" * 60)
    print("MeetingScribe - Audio Recording")
    print("=" * 60)
    print()

    print("Interactive mode coming soon...")
    print("Use: python -m cli record <duration>")
    print("     python -m cli status")
    print()


if __name__ == "__main__":
    main()
