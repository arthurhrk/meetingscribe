#!/usr/bin/env python3
"""
Record with Real-Time Status - For Raycast Integration

Creates a status file that Raycast can monitor in real-time to show:
- Recording progress
- Audio level detection
- Time elapsed
- Warnings/errors

Usage:
    python record_with_status.py <duration> <quality> [session_id]
    python record_with_status.py 300 professional rec-12345
"""

import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional


def create_status_file(session_id: str, status_data: dict):
    """Create/update a status file that Raycast can read"""
    status_file = Path("storage") / "status" / f"{session_id}.json"
    status_file.parent.mkdir(parents=True, exist_ok=True)

    with open(status_file, 'w') as f:
        json.dump(status_data, f, indent=2)


def main():
    """Main entry point with quality selection and real-time status"""

    # Parse arguments
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    quality = sys.argv[2] if len(sys.argv) > 2 else "professional"
    session_id = sys.argv[3] if len(sys.argv) > 3 else f"rec-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Generate identifiers
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.wav"
    filepath = Path("storage/recordings") / filename

    # Create initial status file
    create_status_file(session_id, {
        "status": "starting",
        "session_id": session_id,
        "filename": filename,
        "file_path": str(filepath),
        "quality": quality,
        "duration": duration,
        "elapsed": 0,
        "progress": 0,
        "has_audio": False,
        "message": "Initializing recording..."
    })

    # RETURN JSON IMMEDIATELY for Raycast
    result = {
        "status": "success",
        "data": {
            "session_id": session_id,
            "file_path": str(filepath).replace("/", "\\"),
            "filename": filename,
            "duration": duration,
            "quality": quality,
            "status_file": str(Path("storage/status") / f"{session_id}.json").replace("/", "\\"),
            "message": "Recording started successfully"
        }
    }
    print(json.dumps(result), flush=True)

    # Background recording worker
    def record_worker():
        """Record audio and update status in real-time"""
        start_time = time.time()

        try:
            # Import heavy modules after JSON response
            from src.audio import AudioRecorder, AudioRecorderError, RecordingQuality

            # Update status: loading
            create_status_file(session_id, {
                "status": "loading",
                "session_id": session_id,
                "filename": filename,
                "quality": quality,
                "duration": duration,
                "elapsed": 0,
                "progress": 0,
                "message": "Loading audio system..."
            })

            # Get quality settings
            quality_settings = RecordingQuality.get(quality)

            # Initialize recorder
            recorder = AudioRecorder()

            # Auto-select device
            if not recorder.set_device_auto():
                create_status_file(session_id, {
                    "status": "error",
                    "session_id": session_id,
                    "message": "No audio device found",
                    "error": "Device not found"
                })
                return

            # Apply quality settings
            recorder._config.sample_rate = quality_settings['sample_rate']
            recorder._config.channels = quality_settings['channels']
            recorder._config.chunk_size = quality_settings['chunk_size']
            recorder._config.max_duration = duration

            # Update status: recording
            create_status_file(session_id, {
                "status": "recording",
                "session_id": session_id,
                "filename": filename,
                "quality": quality,
                "quality_info": quality_settings,
                "duration": duration,
                "elapsed": 0,
                "progress": 0,
                "has_audio": False,
                "device": recorder._config.device.name,
                "sample_rate": recorder._config.sample_rate,
                "channels": recorder._config.channels,
                "message": "Recording..."
            })

            # Start recording
            recorder.start_recording(filename=filename)

            # Monitor progress and update status every second
            while time.time() - start_time < duration:
                elapsed = int(time.time() - start_time)
                progress = (elapsed / duration) * 100

                # Check if we're capturing audio
                has_audio = len(recorder._frames) > 0

                create_status_file(session_id, {
                    "status": "recording",
                    "session_id": session_id,
                    "filename": filename,
                    "quality": quality,
                    "quality_info": quality_settings,
                    "duration": duration,
                    "elapsed": elapsed,
                    "progress": round(progress, 1),
                    "has_audio": has_audio,
                    "frames_captured": len(recorder._frames),
                    "device": recorder._config.device.name,
                    "sample_rate": recorder._config.sample_rate,
                    "channels": recorder._config.channels,
                    "message": f"Recording... {elapsed}s / {duration}s"
                })

                time.sleep(1)

            # Stop recording
            if recorder.is_recording():
                recorder.stop_recording()

            # Get file size
            file_size = filepath.stat().st_size if filepath.exists() else 0

            # Final status: completed
            create_status_file(session_id, {
                "status": "completed",
                "session_id": session_id,
                "filename": filename,
                "file_path": str(filepath),
                "quality": quality,
                "quality_info": quality_settings,
                "duration": duration,
                "elapsed": duration,
                "progress": 100,
                "has_audio": True,
                "file_size": file_size,
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "message": "Recording completed successfully"
            })

            recorder.close()

        except Exception as e:
            # Error status
            create_status_file(session_id, {
                "status": "error",
                "session_id": session_id,
                "filename": filename,
                "quality": quality,
                "duration": duration,
                "elapsed": int(time.time() - start_time),
                "message": f"Recording error: {str(e)}",
                "error": str(e)
            })

    # Start recording thread
    thread = threading.Thread(target=record_worker, daemon=False, name="RecordWorker")
    thread.start()
    thread.join()

    # Clean up status file after completion
    time.sleep(2)
    status_file = Path("storage") / "status" / f"{session_id}.json"
    if status_file.exists():
        status_file.unlink()


if __name__ == "__main__":
    main()
