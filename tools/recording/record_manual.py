#!/usr/bin/env python3
"""
Manual Recording - Start/Stop without time limit

Creates a control file that can be used to stop the recording manually.
Useful for meetings where you don't know the duration in advance.

Usage:
    # Start manual recording
    python record_manual.py start <quality> [session_id]

    # Stop recording
    python record_manual.py stop <session_id>

    # Check status
    python record_manual.py status <session_id>

Example:
    python record_manual.py start professional my-meeting
    python record_manual.py stop my-meeting
"""

import sys
import json
import time
import threading
import signal
from pathlib import Path
from datetime import datetime
from typing import Optional


def create_status_file(session_id: str, status_data: dict):
    """Create/update a status file"""
    status_file = Path("storage") / "status" / f"{session_id}.json"
    status_file.parent.mkdir(parents=True, exist_ok=True)

    with open(status_file, 'w') as f:
        json.dump(status_data, f, indent=2)


def create_control_file(session_id: str):
    """Create a control file to signal stop"""
    control_file = Path("storage") / "control" / f"{session_id}.control"
    control_file.parent.mkdir(parents=True, exist_ok=True)
    control_file.write_text("recording")


def should_stop(session_id: str) -> bool:
    """Check if recording should stop"""
    control_file = Path("storage") / "control" / f"{session_id}.control"
    if not control_file.exists():
        return True  # File deleted = stop

    content = control_file.read_text().strip()
    return content == "stop"


def signal_stop(session_id: str):
    """Signal recording to stop"""
    control_file = Path("storage") / "control" / f"{session_id}.control"
    if control_file.exists():
        control_file.write_text("stop")
        return True
    return False


def get_status(session_id: str) -> Optional[dict]:
    """Get current status of a recording"""
    status_file = Path("storage") / "status" / f"{session_id}.json"
    if status_file.exists():
        with open(status_file, 'r') as f:
            return json.load(f)
    return None


def start_recording(quality: str, session_id: str):
    """Start a manual recording (no time limit)"""

    # Generate identifiers
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"manual_{session_id}_{timestamp}.wav"
    filepath = Path("storage/recordings") / filename

    # Create control file
    create_control_file(session_id)

    # Create initial status
    create_status_file(session_id, {
        "status": "starting",
        "session_id": session_id,
        "filename": filename,
        "file_path": str(filepath),
        "quality": quality,
        "duration": 0,  # 0 = manual mode, no time limit
        "elapsed": 0,
        "progress": 0,
        "has_audio": False,
        "manual_mode": True,
        "message": "Initializing manual recording..."
    })

    # Return JSON immediately
    result = {
        "status": "success",
        "data": {
            "session_id": session_id,
            "file_path": str(filepath).replace("/", "\\"),
            "filename": filename,
            "quality": quality,
            "manual_mode": True,
            "control_file": str(Path("storage/control") / f"{session_id}.control").replace("/", "\\"),
            "status_file": str(Path("storage/status") / f"{session_id}.json").replace("/", "\\"),
            "message": "Manual recording started - use 'stop' command to finish"
        }
    }
    print(json.dumps(result), flush=True)

    # Background recording
    def record_worker():
        start_time = time.time()

        try:
            from src.audio import AudioRecorder, AudioRecorderError, RecordingQuality

            # Update status
            create_status_file(session_id, {
                "status": "loading",
                "session_id": session_id,
                "filename": filename,
                "quality": quality,
                "duration": 0,
                "elapsed": 0,
                "manual_mode": True,
                "message": "Loading audio system..."
            })

            # Get quality settings
            quality_settings = RecordingQuality.get(quality)

            # Initialize recorder
            recorder = AudioRecorder()

            if not recorder.set_device_auto():
                create_status_file(session_id, {
                    "status": "error",
                    "session_id": session_id,
                    "manual_mode": True,
                    "message": "No audio device found",
                    "error": "Device not found"
                })
                return

            # Apply quality settings
            recorder._config.sample_rate = quality_settings['sample_rate']
            recorder._config.channels = quality_settings['channels']
            recorder._config.chunk_size = quality_settings['chunk_size']
            recorder._config.max_duration = None  # No time limit

            # Start recording
            create_status_file(session_id, {
                "status": "recording",
                "session_id": session_id,
                "filename": filename,
                "quality": quality,
                "quality_info": quality_settings,
                "duration": 0,
                "elapsed": 0,
                "has_audio": False,
                "manual_mode": True,
                "device": recorder._config.device.name,
                "sample_rate": recorder._config.sample_rate,
                "channels": recorder._config.channels,
                "message": "Recording... (manual mode - no time limit)"
            })

            recorder.start_recording(filename=filename)

            # Monitor until stop signal
            while not should_stop(session_id):
                elapsed = int(time.time() - start_time)
                has_audio = len(recorder._frames) > 0

                create_status_file(session_id, {
                    "status": "recording",
                    "session_id": session_id,
                    "filename": filename,
                    "quality": quality,
                    "quality_info": quality_settings,
                    "duration": 0,
                    "elapsed": elapsed,
                    "progress": 0,  # No progress in manual mode
                    "has_audio": has_audio,
                    "frames_captured": len(recorder._frames),
                    "manual_mode": True,
                    "device": recorder._config.device.name,
                    "sample_rate": recorder._config.sample_rate,
                    "channels": recorder._config.channels,
                    "message": f"Recording... {elapsed}s (manual mode)"
                })

                time.sleep(1)

            # Stop recording
            if recorder.is_recording():
                recorder.stop_recording()

            elapsed_final = int(time.time() - start_time)
            file_size = filepath.stat().st_size if filepath.exists() else 0

            # Final status
            create_status_file(session_id, {
                "status": "completed",
                "session_id": session_id,
                "filename": filename,
                "file_path": str(filepath),
                "quality": quality,
                "quality_info": quality_settings,
                "duration": 0,
                "elapsed": elapsed_final,
                "has_audio": True,
                "manual_mode": True,
                "file_size": file_size,
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "message": f"Recording completed - {elapsed_final}s recorded"
            })

            recorder.close()

            # Clean up control file
            control_file = Path("storage") / "control" / f"{session_id}.control"
            if control_file.exists():
                control_file.unlink()

        except Exception as e:
            create_status_file(session_id, {
                "status": "error",
                "session_id": session_id,
                "filename": filename,
                "quality": quality,
                "manual_mode": True,
                "elapsed": int(time.time() - start_time),
                "message": f"Recording error: {str(e)}",
                "error": str(e)
            })

    # Start recording thread
    thread = threading.Thread(target=record_worker, daemon=False, name="ManualRecorder")
    thread.start()
    thread.join()

    # Clean up after completion
    time.sleep(2)
    status_file = Path("storage") / "status" / f"{session_id}.json"
    if status_file.exists():
        status_file.unlink()


def stop_recording(session_id: str):
    """Stop a manual recording"""

    if signal_stop(session_id):
        result = {
            "status": "success",
            "message": f"Stop signal sent to recording {session_id}",
            "session_id": session_id
        }
    else:
        result = {
            "status": "error",
            "message": f"Recording {session_id} not found or already stopped",
            "session_id": session_id
        }

    print(json.dumps(result), flush=True)


def check_status_cmd(session_id: str):
    """Check status of a recording"""

    status = get_status(session_id)

    if status:
        print(json.dumps({"status": "success", "data": status}, indent=2), flush=True)
    else:
        print(json.dumps({
            "status": "error",
            "message": f"Recording {session_id} not found"
        }, indent=2), flush=True)


def main():
    if len(sys.argv) < 2:
        print("Usage: python record_manual.py <start|stop|status> [args...]")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "start":
        quality = sys.argv[2] if len(sys.argv) > 2 else "professional"
        session_id = sys.argv[3] if len(sys.argv) > 3 else f"manual-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_recording(quality, session_id)

    elif command == "stop":
        if len(sys.argv) < 3:
            print("Usage: python record_manual.py stop <session_id>")
            sys.exit(1)
        session_id = sys.argv[2]
        stop_recording(session_id)

    elif command == "status":
        if len(sys.argv) < 3:
            print("Usage: python record_manual.py status <session_id>")
            sys.exit(1)
        session_id = sys.argv[2]
        check_status_cmd(session_id)

    else:
        print(f"Unknown command: {command}")
        print("Valid commands: start, stop, status")
        sys.exit(1)


if __name__ == "__main__":
    main()
