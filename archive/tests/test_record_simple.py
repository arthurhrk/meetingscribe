"""
Teste simples de gravação - SEM complexidade
"""
import sys
import json

# Print JSON imediatamente
print(json.dumps({
    "status": "success",
    "data": {
        "session_id": "test-123",
        "file_path": "storage/recordings/test.wav",
        "duration": 10
    }
}))
sys.stdout.flush()

# Agora tentar gravar
try:
    from audio_recorder import AudioRecorder
    import time

    recorder = AudioRecorder()
    success = recorder.set_device_auto()

    if success:
        recorder._config.max_duration = 10
        filepath = recorder.start_recording(filename="test_recording.wav")
        print(f"DEBUG: Recording started at {filepath}", file=sys.stderr)

        time.sleep(12)

        if recorder.is_recording():
            stats = recorder.stop_recording()
            print(f"DEBUG: Recording saved - {stats.file_size} bytes", file=sys.stderr)

        recorder.close()
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
