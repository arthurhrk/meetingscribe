from __future__ import annotations

import sys
import json
import time
import platform
from typing import Any, Dict

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None  # type: ignore

from config import settings, setup_directories, setup_logging
from dataclasses import asdict
from typing import List
try:
    from device_manager import DeviceManager, AudioDeviceError, WASAPINotAvailableError
except Exception:  # pragma: no cover
    DeviceManager = None  # type: ignore
    AudioDeviceError = Exception  # type: ignore
    WASAPINotAvailableError = Exception  # type: ignore


def _system_status() -> Dict[str, Any]:
    setup_directories()
    # logging init is safe to call multiple times
    try:
        setup_logging()
    except Exception:
        pass

    storage = {
        "storage": settings.storage_dir.exists(),
        "recordings": settings.recordings_dir.exists(),
        "transcriptions": settings.transcriptions_dir.exists(),
        "exports": settings.exports_dir.exists(),
        "logs": settings.logs_dir.exists(),
        "models": settings.models_dir.exists(),
    }
    mem_mb = None
    if psutil is not None:
        try:
            mem_mb = int(psutil.Process().memory_info().rss / (1024 * 1024))
        except Exception:
            mem_mb = None

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

    return {
        "mode": "daemon",
        "ready": all(storage.values()),
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "base_dir": str(settings.base_dir),
        "models_dir": str(settings.models_dir),
        "storage_dirs": storage,
        "memory_mb": mem_mb,
        "pyaudio_available": pyaudio_available,
        "timestamp": int(time.time()),
        "interface_version": "1.0",
    }


def _handle(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if method == "ping":
        return {"status": "success", "data": {"pong": True, "version": "2.0.0"}}
    if method == "system.status":
        return {"status": "success", "data": _system_status()}
    if method == "devices.list":
        try:
            if DeviceManager is None:
                raise AudioDeviceError("Device manager not available")
            with DeviceManager() as dm:  # type: ignore
                devices = dm.list_all_devices()  # type: ignore
                items = []
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
                return {"status": "success", "data": {"devices": items}}
        except WASAPINotAvailableError as e:  # type: ignore
            return {"status": "error", "error": {"code": "E_WASAPI", "message": str(e)}}
        except AudioDeviceError as e:  # type: ignore
            return {"status": "error", "error": {"code": "E_AUDIO", "message": str(e)}}
        except Exception as e:
            return {"status": "error", "error": {"code": "E_UNKNOWN", "message": str(e)}}
    return {"status": "error", "error": {"code": "E_NOT_IMPLEMENTED", "message": method}}


def run_stdio() -> None:
    """Simple JSON-RPC over STDIO loop.

    Reads newline-delimited JSON. Each object must have fields: jsonrpc, id, method, params.
    """
    stdin = sys.stdin
    stdout = sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params") or {}
            result = _handle(method, params)
            resp = {"jsonrpc": "2.0", "id": req_id}
            if result.get("status") == "success":
                resp["result"] = result
            else:
                resp["error"] = result.get("error", {"code": "E_UNKNOWN"})
        except Exception as e:  # pragma: no cover
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": "E_BAD_REQUEST", "message": str(e)}}
        stdout.write(json.dumps(resp) + "\n")
        stdout.flush()


if __name__ == "__main__":
    run_stdio()
