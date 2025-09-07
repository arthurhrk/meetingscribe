from __future__ import annotations

import argparse
import asyncio
from typing import Any

from rich.console import Console

from .rich_ui import RichUI
from .daemon_client import DaemonClient
from .fallback_runner import FallbackRunner


async def create_executor(ui: RichUI):
    """Return an executor-like object with an 'execute' method.

    Phase 1: Always fallback (daemon connect raises timeout).
    """
    client = DaemonClient()
    try:
        await asyncio.wait_for(client.connect(), timeout=0.8)
        ui.show_status("Using daemon service (faster)")
        return DaemonExecutor(client, ui)
    except Exception:
        ui.show_status("Using direct mode (fallback)", style="yellow")
        return FallbackExecutor(FallbackRunner(), ui)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="meetingscribe",
        description="MeetingScribe v2 Client (Phase 1 skeleton)",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show system status (unified view)")
    return parser


class DaemonExecutor:
    def __init__(self, daemon_client: DaemonClient, ui: RichUI) -> None:
        self.daemon_client = daemon_client
        self.ui = ui

    async def execute(self, args: argparse.Namespace) -> int:
        if args.command == "status":
            return await self._do_status()
        self.ui.show_error("Unknown command")
        return 2

    async def _do_status(self) -> int:
        resp = await self.daemon_client.request("system.status", {})
        result = resp.get("result") or {}
        if result.get("status") != "success":
            self.ui.show_error("Failed to get status from daemon")
            return 2
        data = result.get("data", {})
        self.ui.show_banner("Unified Status (daemon)")
        fields = {
            "Mode": data.get("mode", "daemon"),
            "Ready": "Yes" if data.get("ready") else "No",
            "OS": data.get("os"),
            "Python": data.get("python"),
            "Base Dir": data.get("base_dir"),
            "Models Dir": data.get("models_dir"),
            "PyAudio": "Available" if data.get("pyaudio_available") else "Not found",
            "Iface": data.get("interface_version", "1.0"),
        }
        mem = data.get("memory_mb")
        if mem is not None:
            fields["Process RAM"] = f"{mem} MB"
        self.ui.kv_table("System", fields)
        storage = data.get("storage_dirs", {})
        self.ui.kv_table("Storage Dirs", {k: ("ok" if v else "missing") for k, v in storage.items()})
        self.ui.show_success("Status collected (daemon)")
        return 0


class FallbackExecutor:
    def __init__(self, runner: FallbackRunner, ui: RichUI) -> None:
        self.runner = runner
        self.ui = ui

    async def execute(self, args: argparse.Namespace) -> int:
        if args.command == "status":
            return self._do_status()
        self.ui.show_error("Unknown command")
        return 2

    def _do_status(self) -> int:
        status = self.runner.status()
        self.ui.show_banner("Unified Status (fallback)")
        fields = {
            "Mode": status.mode,
            "Ready": "Yes" if status.ready else "No",
            "OS": status.os,
            "Python": status.python,
            "Base Dir": status.base_dir,
            "Models Dir": status.models_dir,
            "PyAudio": "Available" if status.pyaudio_available else "Not found",
        }
        if status.memory_mb is not None:
            fields["Process RAM"] = f"{status.memory_mb} MB"
        self.ui.kv_table("System", fields)

        self.ui.kv_table("Storage Dirs", {k: ("ok" if v else "missing") for k, v in status.storage_dirs.items()})
        self.ui.show_success("Status collected (fallback)")
        return 0


async def main() -> int:
    console = Console()
    ui = RichUI(console)
    parser = build_parser()
    args = parser.parse_args()

    executor = await create_executor(ui)
    return await executor.execute(args)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
