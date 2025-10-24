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
from src.audio import AudioRecorder, AudioRecorderError
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
    if not filename:
        filename = f"recording_{timestamp}.wav"

    filepath = Path(settings.recordings_dir) / filename

    # Return JSON immediately
    result = {
        "status": "success",
        "data": {
            "session_id": f"rec-{timestamp}",
            "file_path": str(filepath),
            "filename": filename,
            "duration": duration,
            "message": "Recording started successfully"
        }
    }

    # Start recording in background thread
    def record_worker():
        """Background worker for recording"""
        try:
            recorder = AudioRecorder()

            # Auto-select best device (WASAPI loopback preferred)
            if not recorder.set_device_auto():
                logger.error("Failed to select audio device")
                return

            # Configure duration
            recorder._config.max_duration = duration

            # Start recording
            recorder.start_recording(filename=filename)
            logger.info(f"Recording started: {filename} ({duration}s)")

            # Wait for completion
            time.sleep(duration + 2)

            # Stop recording
            if recorder.is_recording():
                recorder.stop_recording()
                logger.info(f"Recording completed: {filepath}")

            recorder.close()

        except AudioRecorderError as e:
            logger.error(f"Recording error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    # Start non-daemon thread (keeps process alive)
    thread = threading.Thread(target=record_worker, daemon=False)
    thread.start()

    return result


def main():
    """Main CLI entry point"""
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
            result = quick_record(duration=duration)
            print(json.dumps(result), flush=True)

            # Wait for recording to complete
            time.sleep(duration + 3)
            return

        elif command == "status":
            # System status check
            from src.audio import DeviceManager

            try:
                dm = DeviceManager()
                devices = dm.list_devices()

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
    print("Use: python -m src.cli.main record <duration>")
    print()


if __name__ == "__main__":
    main()
