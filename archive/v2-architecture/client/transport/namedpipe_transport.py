from __future__ import annotations

import asyncio
import json
from typing import Optional, Dict, Any

try:
    import win32pipe
    import win32file
    import pywintypes
except Exception:  # pragma: no cover
    win32pipe = None  # type: ignore
    win32file = None  # type: ignore
    pywintypes = None  # type: no cover


class NamedPipeTransport:
    """Named Pipes transport for Windows (client-side).

    Minimal client that connects to an existing pipe server and sends
    newline-delimited JSON-RPC messages. If pywin32 is unavailable,
    connection will fail quickly so callers can fallback to STDIO.
    """

    def __init__(self, pipe_name: str = r"\\.\pipe\MeetingScribe") -> None:
        self.pipe_name = pipe_name
        self.handle = None
        self._futures: Dict[int, asyncio.Future] = {}
        self._next_id = 1
        self._reader_task: Optional[asyncio.Task] = None

    async def connect(self, timeout: float = 1.0) -> None:
        if win32pipe is None:
            raise ConnectionError("pywin32 not available")
        # Quick wait for pipe
        try:
            win32pipe.WaitNamedPipe(self.pipe_name, int(timeout * 1000))
        except pywintypes.error as e:  # type: ignore
            raise ConnectionError(f"Pipe not available: {e}")
        # Open the pipe
        try:
            self.handle = win32file.CreateFile(
                self.pipe_name,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,  # type: ignore
                0,
                None,
                win32file.OPEN_EXISTING,  # type: ignore
                0,
                None,
            )
        except pywintypes.error as e:  # type: ignore
            raise ConnectionError(f"Failed to open pipe: {e}")

        loop = asyncio.get_event_loop()
        self._reader_task = loop.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        # Blocking reads off-thread
        loop = asyncio.get_event_loop()
        while self.handle:
            try:
                def _read_once():
                    hr, data = win32file.ReadFile(self.handle, 4096)  # type: ignore
                    return data
                data: bytes = await loop.run_in_executor(None, _read_once)
                if not data:
                    break
                for line in data.splitlines():
                    try:
                        msg = json.loads(line.decode().strip())
                        req_id = msg.get("id")
                        fut = self._futures.pop(req_id, None)
                        if fut and not fut.done():
                            fut.set_result(msg)
                    except Exception:
                        continue
            except Exception:
                # Close and fail pending futures
                for fut in list(self._futures.values()):
                    if not fut.done():
                        fut.set_exception(ConnectionError("Pipe closed"))
                self._futures.clear()
                break

    async def request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 5.0) -> Dict[str, Any]:
        if not self.handle:
            raise ConnectionError("Not connected")
        req_id = self._next_id
        self._next_id += 1
        req = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
        data = (json.dumps(req) + "\n").encode()
        # Blocking write off-thread
        loop = asyncio.get_event_loop()
        def _write_once():
            win32file.WriteFile(self.handle, data)  # type: ignore
        await loop.run_in_executor(None, _write_once)
        fut: asyncio.Future = loop.create_future()
        self._futures[req_id] = fut
        return await asyncio.wait_for(fut, timeout=timeout)

    async def close(self) -> None:
        if self.handle:
            try:
                self.handle.Close()  # type: ignore
            except Exception:
                pass
            self.handle = None
        if self._reader_task:
            try:
                await asyncio.wait_for(self._reader_task, timeout=0.2)
            except Exception:
                pass
            self._reader_task = None

