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
    sub.add_parser("devices", help="List audio devices")
    rec_start = sub.add_parser("record-start", help="Start recording (until stop or duration)")
    rec_start.add_argument("--duration", type=int, default=None, help="Max duration in seconds")
    rec_stop = sub.add_parser("record-stop", help="Stop current recording")
    trans = sub.add_parser("transcribe", help="Transcribe an audio file and save TXT")
    trans.add_argument("file", help="Path to audio file")
    export = sub.add_parser("export", help="Export transcription from audio file")
    export.add_argument("file", help="Path to audio file")
    export.add_argument("--format", default="txt", help="Format: txt|json|srt|vtt|xml|csv")
    return parser


class DaemonExecutor:
    def __init__(self, daemon_client: DaemonClient, ui: RichUI) -> None:
        self.daemon_client = daemon_client
        self.ui = ui

    async def execute(self, args: argparse.Namespace) -> int:
        if args.command == "status":
            return await self._do_status()
        if args.command == "devices":
            return await self._do_devices()
        if args.command == "record-start":
            return await self._do_record_start(args)
        if args.command == "record-stop":
            return await self._do_record_stop()
        if args.command == "transcribe":
            return await self._do_transcribe(args)
        if args.command == "export":
            return await self._do_export(args)
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

    async def _do_devices(self) -> int:
        resp = await self.daemon_client.request("devices.list", {})
        result = resp.get("result") or {}
        if result.get("status") != "success":
            self.ui.show_error("Failed to list devices from daemon")
            return 2
        devices = result.get("data", {}).get("devices", [])
        self.ui.device_table(devices)
        self.ui.show_success(f"Devices listed: {len(devices)}")
        return 0

    async def _do_record_start(self, args) -> int:
        params = {}
        if args.duration:
            params["duration"] = int(args.duration)
        resp = await self.daemon_client.request("record.start", params)
        result = resp.get("result") or {}
        if result.get("status") != "success":
            self.ui.show_error("Failed to start recording")
            return 2
        data = result.get("data", {})
        self.ui.show_success(f"Recording started: {data.get('session_id')} -> {data.get('file_path')}")
        return 0

    async def _do_record_stop(self) -> int:
        resp = await self.daemon_client.request("record.stop", {})
        result = resp.get("result") or {}
        if result.get("status") != "success":
            self.ui.show_error("Failed to stop recording")
            return 2
        data = result.get("data", {})
        self.ui.show_success(f"Recording saved: {data.get('file_path')} ({int(data.get('duration',0))}s)")
        return 0

    async def _do_transcribe(self, args) -> int:
        resp = await self.daemon_client.request("transcribe.start", {"file": args.file})
        result = resp.get("result") or {}
        if result.get("status") != "success":
            self.ui.show_error("Failed to transcribe")
            return 2
        data = result.get("data", {})
        self.ui.show_success(f"Transcribed to: {data.get('output')} (lang={data.get('language')})")
        return 0

    async def _do_export(self, args) -> int:
        resp = await self.daemon_client.request("export.run", {"file": args.file, "format": args.format})
        result = resp.get("result") or {}
        if result.get("status") != "success":
            self.ui.show_error("Failed to export")
            return 2
        data = result.get("data", {})
        self.ui.show_success(f"Exported: {data.get('output')} ({data.get('format')})")
        return 0


class FallbackExecutor:
    def __init__(self, runner: FallbackRunner, ui: RichUI) -> None:
        self.runner = runner
        self.ui = ui

    async def execute(self, args: argparse.Namespace) -> int:
        if args.command == "status":
            return self._do_status()
        if args.command == "devices":
            return self._do_devices()
        if args.command == "record-start":
            return self._do_record_start(args)
        if args.command == "record-stop":
            return self._do_record_stop()
        if args.command == "transcribe":
            return self._do_transcribe(args)
        if args.command == "export":
            return self._do_export(args)
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

    def _do_devices(self) -> int:
        devices = self.runner.devices()
        self.ui.device_table(devices)
        self.ui.show_success(f"Devices listed: {len(devices)}")
        return 0

    def _do_record_start(self, args) -> int:
        res = self.runner.record_start(duration=getattr(args, "duration", None))
        if res.get("status") != "success":
            self.ui.show_error(res.get("error", {}).get("message", "Failed to start"))
            return 2
        data = res.get("data", {})
        self.ui.show_success(f"Recording started: {data.get('session_id')} -> {data.get('file_path')}")
        return 0

    def _do_record_stop(self) -> int:
        res = self.runner.record_stop()
        if res.get("status") != "success":
            self.ui.show_error(res.get("error", {}).get("message", "Failed to stop"))
            return 2
        data = res.get("data", {})
        self.ui.show_success(f"Recording saved: {data.get('file_path')} ({int(data.get('duration',0))}s)")
        return 0

    def _do_transcribe(self, args) -> int:
        # Fallback: run synchronous minimal transcription/export TXT via daemon-equivalent path if available
        try:
            from src.transcription import transcribe_audio_file
            from src.transcription import export_transcription, ExportFormat
            from config import settings
            result = transcribe_audio_file(Path(args.file))  # type: ignore
            out_dir = settings.transcriptions_dir
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{Path(args.file).stem}_transcription.txt"
            export_transcription(result, out_path, ExportFormat.TXT)  # type: ignore
            self.ui.show_success(f"Transcribed to: {out_path}")
            return 0
        except Exception as e:
            self.ui.show_error(f"Transcription failed: {e}")
            return 2

    def _do_export(self, args) -> int:
        try:
            from src.transcription import transcribe_audio_file
            from src.transcription import export_transcription, ExportFormat
            from config import settings
            fmt = args.format.lower()
            try:
                fmt_enum = ExportFormat(fmt)  # type: ignore
            except Exception:
                self.ui.show_error(f"Unsupported format: {fmt}")
                return 2
            result = transcribe_audio_file(Path(args.file))  # type: ignore
            out_dir = settings.exports_dir
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{Path(args.file).stem}.{fmt}"
            export_transcription(result, out_path, fmt_enum)  # type: ignore
            self.ui.show_success(f"Exported: {out_path} ({fmt})")
            return 0
        except Exception as e:
            self.ui.show_error(f"Export failed: {e}")
            return 2


async def main() -> int:
    console = Console()
    ui = RichUI(console)
    parser = build_parser()
    args = parser.parse_args()

    executor = await create_executor(ui)
    return await executor.execute(args)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
