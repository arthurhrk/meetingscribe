"""
Runtime CLI agnóstico para MeetingScribe

Fornece comandos JSON estáveis e um modo inicial de STDIO runner
sem depender de HTTP. Ideal para consumo pela extensão Raycast.
"""

from __future__ import annotations

import sys
import json
import argparse
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    # Evitar logs no stdout para não poluir JSON
    logger.remove()
except Exception:
    pass


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    return obj


def _response_ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "interface_version": "1.0",
        "status": "success",
        "data": _to_jsonable(data),
    }


def _response_err(code: str, message: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "interface_version": "1.0",
        "status": "error",
        "error": {"code": code, "message": message, "details": details or {}},
    }


def cmd_devices_list() -> int:
    try:
        from device_manager import DeviceManager

        with DeviceManager() as dm:  # type: ignore[attr-defined]
            devices = dm.list_all_devices()
            payload = {"devices": devices}
            print(json.dumps(_response_ok(payload), ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps(_response_err("E_AUDIO_DEVICE", str(e))))
        return 20


def cmd_system_status() -> int:
    try:
        from src.core import get_system_info

        info = get_system_info()
        print(json.dumps(_response_ok({"system": info}), ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps(_response_err("E_INTERNAL", str(e))))
        return 30


def cmd_record_start(device_id: Optional[str], duration: Optional[float], filename: Optional[str]) -> int:
    """Gravação direta e bloqueante (requer duration)."""
    if not duration or duration <= 0:
        print(json.dumps(_response_err("E_VALIDATION", "'duration' é obrigatório para CLI de execução única")))
        return 10
    try:
        from time import sleep
        from device_manager import DeviceManager
        from audio_recorder import AudioRecorder, RecordingConfig

        # Seleção de dispositivo
        with DeviceManager() as dm:  # type: ignore[attr-defined]
            devices = dm.list_all_devices()
            device = None
            if device_id is not None:
                for d in devices:
                    if str(d.index) == str(device_id) or d.name == device_id:
                        device = d
                        break
            if device is None:
                device = dm.get_default_speakers() or (devices[0] if devices else None)
            if device is None:
                print(json.dumps(_response_err("E_AUDIO_DEVICE", "Nenhum dispositivo de áudio disponível")))
                return 20

        recorder = AudioRecorder(RecordingConfig(device=device))
        path = recorder.start_recording(filename=filename)
        sleep(float(duration))
        recorder.stop_recording()
        print(json.dumps(_response_ok({"file_path": path}), ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps(_response_err("E_INTERNAL", str(e))))
        return 30


def cmd_transcribe_file(audio_path: str, model: Optional[str], language: Optional[str]) -> int:
    """Transcrição síncrona (bloqueante) para CLI de execução única."""
    try:
        from pathlib import Path
        from src.transcription.transcriber import create_transcriber, WhisperModelSize

        model_enum = WhisperModelSize((model or "base").upper())
        transcriber = create_transcriber(model_enum)
        with transcriber:
            result = transcriber.transcribe_file(Path(audio_path), progress=None, language=language)
        # Serializar campos importantes
        out = {
            "full_text": getattr(result, "full_text", None),
            "language": getattr(result, "language", None),
            "total_duration": getattr(result, "total_duration", None),
            "processing_time": getattr(result, "processing_time", None),
        }
        print(json.dumps(_response_ok({"result": out}), ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps(_response_err("E_INTERNAL", str(e))))
        return 30


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="runtime-cli", description="Runtime CLI JSON agnóstico")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("devices", help="Listar dispositivos de áudio em JSON")
    sub.add_parser("system", help="Status do sistema em JSON")

    p_rec = sub.add_parser("record-start", help="Iniciar gravação bloqueante por duração")
    p_rec.add_argument("--device-id", dest="device_id")
    p_rec.add_argument("--duration", type=float, required=True)
    p_rec.add_argument("--filename")

    p_tx = sub.add_parser("transcribe", help="Transcrever arquivo (bloqueante)")
    p_tx.add_argument("audio_path")
    p_tx.add_argument("--model")
    p_tx.add_argument("--language")

    args = parser.parse_args(argv)

    if args.command == "devices":
        return cmd_devices_list()
    if args.command == "system":
        return cmd_system_status()
    if args.command == "record-start":
        return cmd_record_start(args.device_id, args.duration, args.filename)
    if args.command == "transcribe":
        return cmd_transcribe_file(args.audio_path, args.model, args.language)

    print(json.dumps(_response_err("E_VALIDATION", "Comando desconhecido")))
    return 10


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
