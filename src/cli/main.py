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

from loguru import logger
from audio import AudioRecorder, AudioRecorderError
from config import settings


def quick_record(duration: int = 30, filename: Optional[str] = None) -> dict:
    """
    Quick recording function for Raycast integration.
    Returns JSON immediately, continues recording in background.

    Args:
        duration: Recording duration in seconds
        filename: Optional custom filename

    Returns:
        dict: Status and recording info
    """
    # Generate identifiers
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"rec-{timestamp}"
    if not filename:
        filename = f"recording_{timestamp}.wav"

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

            # Configure duration
            recorder._config.max_duration = duration

            # Start recording
            recorder.start_recording(filename=filename)
            logger.info(f"Recording started: {filename} ({duration}s)")

            # Write initial status
            status_file.write_text(json.dumps({
                "status": "recording",
                "session_id": session_id,
                "filename": filename,
                "duration": duration,
                "elapsed": 0,
                "progress": 0
            }))

            # Update status every second
            for i in range(duration):
                time.sleep(1)
                elapsed = int(time.time() - start_time)
                progress = min(100, int((elapsed / duration) * 100))

                status_file.write_text(json.dumps({
                    "status": "recording",
                    "session_id": session_id,
                    "filename": filename,
                    "duration": duration,
                    "elapsed": elapsed,
                    "progress": progress
                }))

            # Stop recording
            recorder.stop_recording()
            logger.info(f"Recording completed: {filepath}")

            recorder.close()

            # Wait a moment for file to be fully written
            time.sleep(1)

            # Get file size
            file_size_mb = round(filepath.stat().st_size / (1024 * 1024), 2) if filepath.exists() else 0

            # Write completion status
            status_file.write_text(json.dumps({
                "status": "completed",
                "session_id": session_id,
                "filename": filename,
                "duration": duration,
                "file_size_mb": file_size_mb
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

    # Disable console logging when called with arguments (Raycast/CLI mode)
    # This prevents log messages from appearing as "errors" in Raycast
    if len(sys.argv) > 1:
        # Remove console handler, keep only file logging
        logger.remove()
        from config import settings
        logger.add(
            settings.logs_dir / "meetingscribe.log",
            rotation="10 MB",
            retention="1 month",
            level=settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
        )

    print("=" * 60)
    print("MeetingScribe - Teams Recording")
    print("=" * 60)
    print()

    # Check if called with arguments (Raycast integration)
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "record":
            # Quick record mode
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            result, thread = quick_record(duration=duration)
            print(json.dumps(result), flush=True)

            # Wait for recording to complete
            thread.join()
            return

        elif command == "status":
            # System status check
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

    # Interactive mode
    print("Interactive mode coming soon...")
    print("Use: python -m cli record <duration>")
    print("     python -m cli status")
    print()


if __name__ == "__main__":
    main()
