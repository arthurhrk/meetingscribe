from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import platform
import shutil

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    psutil = None  # type: ignore

from config import settings, setup_directories


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

