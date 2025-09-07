from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Optional, Dict


class _StdioTransport:
    """Minimal STDIO transport spawning daemon.stdio_core as a subprocess."""

    def __init__(self) -> None:
        self.process: Optional[asyncio.subprocess.Process] = None
        self._futures: Dict[int, asyncio.Future] = {}
        self._next_id = 1

    async def connect(self) -> None:
        if self.process:
            return
        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "daemon.stdio_core",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        assert self.process and self.process.stdout
        while True:
            line = await self.process.stdout.readline()
            if not line:
                # Process ended
                # Fail pending futures
                for fut in list(self._futures.values()):
                    if not fut.done():
                        fut.set_exception(ConnectionError("Daemon closed"))
                self._futures.clear()
                break
            try:
                msg = json.loads(line.decode().strip())
                req_id = msg.get("id")
                fut = self._futures.pop(req_id, None)
                if fut and not fut.done():
                    fut.set_result(msg)
            except Exception:
                continue

    async def request(self, method: str, params: Optional[dict[str, Any]] = None, timeout: float = 5.0) -> dict[str, Any]:
        assert self.process and self.process.stdin
        req_id = self._next_id
        self._next_id += 1
        req = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._futures[req_id] = fut
        self.process.stdin.write((json.dumps(req) + "\n").encode())
        await self.process.stdin.drain()
        return await asyncio.wait_for(fut, timeout=timeout)


class DaemonClient:
    """Daemon client using STDIO transport (Phase 1).

    Future phases will add Named Pipes and Windows Service discovery.
    """

    def __init__(self) -> None:
        self.connected: bool = False
        self.transport = None

    async def connect(self, timeout: float = 0.8) -> None:
        # Try Named Pipes first
        try:
            from .transport.namedpipe_transport import NamedPipeTransport
            self.transport = NamedPipeTransport()
            await asyncio.wait_for(self.transport.connect(timeout=timeout), timeout=timeout)
        except Exception:
            # Fallback to STDIO
            self.transport = _StdioTransport()
            await asyncio.wait_for(self.transport.connect(), timeout=timeout)
        # Simple ping to validate
        resp = await self.transport.request("ping", {}, timeout=timeout)
        if "result" in resp and resp["result"].get("status") == "success":
            self.connected = True
        else:
            raise ConnectionError("Daemon did not respond to ping")

    async def request(self, method: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if not self.connected:
            raise ConnectionError("Daemon not connected")
        return await self.transport.request(method, params or {})
