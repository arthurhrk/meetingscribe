from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional, List, Dict
import platform
import shutil

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    psutil = None  # type: ignore

from config import settings, setup_directories
try:
    from device_manager import DeviceManager
except Exception:  # pragma: no cover
    DeviceManager = None  # type: ignore
try:
    from audio_recorder import AudioRecorder, AudioRecorderError
except Exception:  # pragma: no cover
    AudioRecorder = None  # type: ignore
    AudioRecorderError = Exception  # type: ignore


@dataclass
class FallbackStatus:
    mode: str
    ready: bool
    os: str
    python: str
    base_dir: str
    storage_dirs: dict[str, bool]
    memory_mb: Optional[int]
    models_dir: str
    pyaudio_available: bool


class FallbackRunner:
    """Direct execution path reusing v1 environment.

    Phase 1: implements minimal 'status' information without touching v1 flows.
    """

    def __init__(self) -> None:
        setup_directories()
        self._recorder: Optional[AudioRecorder] = None  # type: ignore
        self._session_id: Optional[str] = None

    def status(self) -> FallbackStatus:
        # Readiness is true if basic folders exist and we can write logs/storage.
        dirs = {
            "storage": settings.storage_dir.exists(),
            "recordings": settings.recordings_dir.exists(),
            "transcriptions": settings.transcriptions_dir.exists(),
            "exports": settings.exports_dir.exists(),
            "logs": settings.logs_dir.exists(),
            "models": settings.models_dir.exists(),
        }
        ready = all(dirs.values())

        mem_mb: Optional[int] = None
        if psutil is not None:
            try:
                mem_mb = int(psutil.Process().memory_info().rss / (1024 * 1024))
            except Exception:
                mem_mb = None

        # Check if PyAudio is available (pyaudiowpatch preferred)
        pyaudio_available = False
        try:
            import pyaudiowpatch as _  # type: ignore
            pyaudio_available = True
        except Exception:
            try:
                import pyaudio as _  # type: ignore
                pyaudio_available = True
            except Exception:
                pyaudio_available = False

        return FallbackStatus(
            mode="direct",
            ready=ready,
            os=f"{platform.system()} {platform.release()}",
            python=platform.python_version(),
            base_dir=str(settings.base_dir),
            storage_dirs=dirs,
            memory_mb=mem_mb,
            models_dir=str(settings.models_dir),
            pyaudio_available=pyaudio_available,
        )

    def devices(self) -> List[Dict[str, Any]]:
        """Return audio devices using v1 DeviceManager (if available)."""
        if DeviceManager is None:
            return []
        try:
            with DeviceManager() as dm:  # type: ignore
                devices = dm.list_all_devices()  # type: ignore
                items: List[Dict[str, Any]] = []
                for d in devices:
                    dd = asdict(d)
                    items.append({
                        "index": dd.get("index"),
                        "name": dd.get("name"),
                        "host_api": dd.get("host_api"),
                        "is_loopback": dd.get("is_loopback"),
                        "is_default": dd.get("is_default"),
                        "in_channels": dd.get("max_input_channels"),
                        "out_channels": dd.get("max_output_channels"),
                        "default_sample_rate": dd.get("default_sample_rate"),
                    })
                return items
        except Exception:
            return []

    def record_start(self, duration: Optional[int] = None) -> Dict[str, Any]:
        if AudioRecorder is None:
            return {"status": "error", "error": {"code": "E_RECORDER", "message": "Recorder not available"}}
        if self._recorder and getattr(self._recorder, "is_recording")():  # type: ignore
            return {"status": "error", "error": {"code": "E_ALREADY", "message": "Recording already in progress"}}
        try:
            self._recorder = AudioRecorder()  # type: ignore
            ok = self._recorder.set_device_auto()  # type: ignore
            if not ok:
                return {"status": "error", "error": {"code": "E_DEVICE", "message": "No suitable device"}}
            if duration:
                self._recorder._config.max_duration = int(duration)  # type: ignore
            path = self._recorder.start_recording()  # type: ignore
            self._session_id = f"rec-{int(time.time())}"
            return {"status": "success", "data": {"session_id": self._session_id, "file_path": path}}
        except AudioRecorderError as e:  # type: ignore
            return {"status": "error", "error": {"code": "E_RECORD_START", "message": str(e)}}
        except Exception as e:
            return {"status": "error", "error": {"code": "E_UNKNOWN", "message": str(e)}}

    def record_stop(self) -> Dict[str, Any]:
        if not self._recorder:
            return {"status": "error", "error": {"code": "E_NO_SESSION", "message": "No active recording"}}
        try:
            stats = self._recorder.stop_recording()  # type: ignore
            sid = self._session_id
            self._recorder = None
            self._session_id = None
            return {"status": "success", "data": {
                "session_id": sid,
                "file_path": stats.filename,
                "duration": stats.duration,
                "size": stats.file_size,
            }}
        except Exception as e:
            return {"status": "error", "error": {"code": "E_RECORD_STOP", "message": str(e)}}
