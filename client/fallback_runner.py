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
