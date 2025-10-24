from __future__ import annotations

import json
import threading
from typing import Optional

try:
    import win32pipe
    import win32file
    import pywintypes
except Exception:  # pragma: no cover
    win32pipe = None  # type: ignore
    win32file = None  # type: ignore
    pywintypes = None  # type: ignore

from . import stdio_core


class NamedPipeServer:
    """Minimal single-client named pipe server reusing stdio_core handler."""

    def __init__(self, pipe_name: str = r"\\.\pipe\MeetingScribe") -> None:
        self.pipe_name = pipe_name
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if win32pipe is None:
            return
        self._thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _serve_loop(self) -> None:
        while not self._stop.is_set():
            try:
                handle = win32pipe.CreateNamedPipe(
                    self.pipe_name,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    1,
                    4096,
                    4096,
                    0,
                    None,
                )
                try:
                    win32pipe.ConnectNamedPipe(handle, None)
                    # Serve one client until disconnect
                    while not self._stop.is_set():
                        hr, data = win32file.ReadFile(handle, 4096)
                        if not data:
                            break
                        for line in data.splitlines():
                            try:
                                req = json.loads(line.decode().strip())
                                req_id = req.get("id")
                                method = req.get("method")
                                params = req.get("params") or {}
                                result = stdio_core._handle(method, params)  # reuse logic
                                resp = {"jsonrpc": "2.0", "id": req_id}
                                if result.get("status") == "success":
                                    resp["result"] = result
                                else:
                                    resp["error"] = result.get("error", {"code": "E_UNKNOWN"})
                                win32file.WriteFile(handle, (json.dumps(resp) + "\n").encode())
                            except Exception:
                                continue
                finally:
                    try:
                        win32file.CloseHandle(handle)
                    except Exception:
                        pass
            except Exception:
                continue

