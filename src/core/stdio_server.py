"""
STDIO Server (JSON-RPC simples) para MeetingScribe

Mantém o processo vivo e aceita comandos JSON via stdin, emitindo
respostas em stdout. Útil para Raycast reduzir latência ao evitar
recarregar modelos e estado entre chamadas.
"""

from __future__ import annotations

import sys
import json
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional

from loguru import logger


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    return obj


def _ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"interface_version": "1.0", "status": "success", "data": _to_jsonable(data)}


def _err(code: str, message: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {"interface_version": "1.0", "status": "error", "error": {"code": code, "message": message, "details": details or {}}}


def _write(obj: Dict[str, Any], req_id: Any | None = None) -> None:
    envelope = {"id": req_id, "result": obj} if req_id is not None else obj
    sys.stdout.write(json.dumps(envelope, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _emit_event(event: str, payload: Dict[str, Any]) -> None:
    line = {"event": event, **payload}
    sys.stdout.write(json.dumps(line, ensure_ascii=False) + "\n")
    sys.stdout.flush()


_recorder: Optional["AudioRecorder"] = None
_record_session_id: Optional[str] = None

_tx_manager: Optional["AsyncTranscriptionManager"] = None


def _handle(method: str, params: Dict[str, Any] | None) -> Dict[str, Any]:
    try:
        if method == "ping":
            return _ok({"pong": True})

        if method == "devices.list":
            from device_manager import DeviceManager

            with DeviceManager() as dm:  # type: ignore[attr-defined]
                devices = dm.list_all_devices()
                return _ok({"devices": devices})

        if method == "system.status":
            from src.core import get_system_info

            info = get_system_info()
            return _ok({"system": info})

        if method == "files.list":
            # params: type: recordings|transcriptions|exports, limit (opcional)
            from config import settings
            from src.core.file_manager import list_transcriptions
            ftype = (params or {}).get("type", "transcriptions")
            limit = (params or {}).get("limit")
            if ftype == "transcriptions":
                items = list_transcriptions(limit)
                data = [
                    {
                        "filename": t.filename,
                        "path": str(t.path),
                        "created": t.created.isoformat(),
                        "duration": t.duration,
                        "language": t.language,
                        "model": t.model,
                    }
                    for t in items
                ]
                return _ok({"items": data})
            elif ftype == "recordings":
                rec_dir = settings.recordings_dir
                files = sorted(rec_dir.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True) if rec_dir.exists() else []
                if isinstance(limit, int):
                    files = files[:limit]
                data = [
                    {
                        "filename": f.name,
                        "path": str(f),
                        "size": f.stat().st_size,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    }
                    for f in files
                ]
                return _ok({"items": data})
            elif ftype == "exports":
                exp_dir = settings.exports_dir
                files = sorted(exp_dir.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True) if exp_dir.exists() else []
                if isinstance(limit, int):
                    files = files[:limit]
                data = [
                    {
                        "filename": f.name,
                        "path": str(f),
                        "size": f.stat().st_size,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    }
                    for f in files
                ]
                return _ok({"items": data})
            else:
                return _err("E_VALIDATION", "Tipo inválido. Use recordings|transcriptions|exports")

        if method == "record.start":
            # params: device_id (str|int, opcional), duration (int, opcional), filename (str, opcional)
            global _recorder, _record_session_id
            from time import sleep, time
            from datetime import datetime
            from device_manager import DeviceManager, AudioDevice
            from audio_recorder import AudioRecorder, RecordingConfig

            if _recorder is not None and getattr(_recorder, "_recording", False):
                return _err("E_CONFLICT", "Já existe uma gravação em andamento")

            device_id = None
            duration = None
            filename = None
            stream = False
            if params:
                device_id = params.get("device_id")
                duration = params.get("duration")
                filename = params.get("filename")
                stream = bool(params.get("stream", False))

            # Escolha de dispositivo
            with DeviceManager() as dm:  # type: ignore[attr-defined]
                devices = dm.list_all_devices()
                device: Optional[AudioDevice] = None
                if device_id is not None:
                    for d in devices:
                        if str(d.index) == str(device_id) or d.name == device_id:
                            device = d
                            break
                if device is None:
                    # fallback: padrão do sistema
                    device = dm.get_default_speakers()
                    if device is None and devices:
                        device = devices[0]

            if device is None:
                return _err("E_AUDIO_DEVICE", "Nenhum dispositivo de áudio disponível")

            config = RecordingConfig(device=device)
            _recorder = AudioRecorder(config)
            # Callback de progresso opcional
            progress_cb = None
            if stream:
                def progress_cb(seconds: float):  # type: ignore
                    _emit_event("record.progress", {
                        "session_id": _record_session_id,
                        "seconds": seconds,
                    })
            _record_session_id = f"rec-{int(time())}"
            path = _recorder.start_recording(filename=filename, progress_callback=progress_cb)

            # Se duração fornecida, parar automaticamente (modo conveniente)
            if isinstance(duration, (int, float)) and duration > 0:
                sleep(float(duration))
                try:
                    _recorder.stop_recording()
                finally:
                    _recorder = None

            # Evento de início
            if stream:
                _emit_event("record.started", {"session_id": _record_session_id, "file_path": path})

            return _ok({
                "session_id": _record_session_id,
                "file_path": path
            })

        if method == "record.stop":
            global _recorder, _record_session_id
            if _recorder is None or not getattr(_recorder, "_recording", False):
                return _err("E_NOT_FOUND", "Nenhuma gravação em andamento")
            try:
                path = _recorder.stop_recording()
                sid = _record_session_id
                _recorder = None
                _record_session_id = None
                _emit_event("record.completed", {"session_id": sid, "file_path": path})
                return _ok({"session_id": sid, "file_path": path})
            except Exception as e:
                return _err("E_INTERNAL", str(e))

        if method == "transcription.start":
            # params: audio_path (str), model (str, opcional), language (str, opcional), use_chunked (bool)
            global _tx_manager
            from pathlib import Path
            from src.core.async_integration import AsyncTranscriptionManager, AsyncTranscriptionRequest
            from src.core.async_processor import TaskPriority
            from src.transcription.transcriber import WhisperModelSize

            audio_path = None
            model = "base"
            language = None
            use_chunked = True
            stream = False
            if params:
                audio_path = params.get("audio_path")
                model = params.get("model", model)
                language = params.get("language", language)
                use_chunked = params.get("use_chunked", use_chunked)
                stream = bool(params.get("stream", False))
            if not audio_path:
                return _err("E_VALIDATION", "Campo 'audio_path' é obrigatório")

            # Mapear model string para enum se possível
            try:
                model_enum = WhisperModelSize(model.upper()) if isinstance(model, str) else model
            except Exception:
                model_enum = WhisperModelSize.BASE

            if _tx_manager is None:
                _tx_manager = AsyncTranscriptionManager()

            req = AsyncTranscriptionRequest(
                audio_path=Path(audio_path),
                model_size=model_enum,
                use_chunked=bool(use_chunked),
                language=language,
                priority=TaskPriority.NORMAL,
            )
            job_id = _tx_manager.submit_transcription(req)
            if not job_id:
                return _err("E_INTERNAL", "Falha ao iniciar transcrição")
            # Conectar callbacks para emitir eventos
            if stream:
                task = _tx_manager.get_task_status(job_id)
                if task is not None:
                    def on_progress(p: float, message: str):
                        _emit_event("transcription.progress", {
                            "job_id": job_id,
                            "progress": p,
                            "message": message,
                        })
                    def on_complete(result: Any):
                        # Emite apenas metadados essenciais
                        meta = {
                            "language": getattr(result, "language", None),
                            "total_duration": getattr(result, "total_duration", None),
                            "processing_time": getattr(result, "processing_time", None),
                        }
                        _emit_event("transcription.completed", {"job_id": job_id, "result": meta})
                    def on_error(exc: Exception):
                        _emit_event("transcription.error", {"job_id": job_id, "message": str(exc)})
                    task.progress_callback = on_progress
                    task.completion_callback = on_complete
                    task.error_callback = on_error
                _emit_event("transcription.started", {"job_id": job_id, "audio_path": audio_path})
            return _ok({"job_id": job_id})

        if method == "export.run":
            # params: filename (base name da transcrição), format (txt|json|srt|vtt|xml|csv), output (opcional)
            from config import settings
            from src.core.file_manager import find_transcription
            from src.transcription.exporter import TranscriptionExporter, ExportFormat
            from src.transcription.transcriber import TranscriptionResult, TranscriptionSegment
            from datetime import datetime

            if not params or not params.get("filename") or not params.get("format"):
                return _err("E_VALIDATION", "Campos 'filename' e 'format' são obrigatórios")

            filename = params["filename"]
            fmt_str = str(params["format"]).lower()
            out = params.get("output")

            # Carregar JSON de transcrição salvo e construir TranscriptionResult mínimo
            tf = find_transcription(filename)
            if tf is None:
                return _err("E_NOT_FOUND", "Transcrição não encontrada")
            data = json.loads(Path(tf.path).read_text(encoding="utf-8"))

            # Mapear para estrutura esperada
            try:
                segments_data = data.get("segments") or data.get("transcription", {}).get("segments") or []
                segments = [
                    TranscriptionSegment(
                        id=s.get("id", i + 1),
                        text=s.get("text", ""),
                        start=s.get("start") or s.get("start_time") or 0.0,
                        end=s.get("end") or s.get("end_time") or 0.0,
                        confidence=s.get("confidence", 0.0),
                        speaker=s.get("speaker"),
                        language=s.get("language"),
                    )
                    for i, s in enumerate(segments_data)
                ]
                result = TranscriptionResult(
                    full_text=data.get("text") or data.get("transcription", {}).get("full_text", ""),
                    language=data.get("language") or data.get("metadata", {}).get("language"),
                    duration=data.get("duration") or data.get("metadata", {}).get("duration"),
                    word_count=data.get("word_count") or data.get("metadata", {}).get("word_count", 0),
                    confidence_avg=data.get("confidence") or data.get("metadata", {}).get("confidence_avg", 0.0),
                    processing_time=data.get("processing_time") or data.get("metadata", {}).get("processing_time", 0.0),
                    model_size=data.get("model") or data.get("metadata", {}).get("model_size", "base"),
                    segments=segments,
                )
            except Exception as e:
                return _err("E_INTERNAL", f"Falha ao mapear transcrição: {e}")

            try:
                exporter = TranscriptionExporter()
                export_dir = settings.exports_dir
                base_output = Path(out) if out else (export_dir / filename)
                fmt = ExportFormat(fmt_str)
                out_path = exporter.export(result, base_output, fmt)
                return _ok({"export_path": str(out_path)})
            except Exception as e:
                return _err("E_INTERNAL", str(e))

        if method == "job.status":
            global _tx_manager
            if _tx_manager is None:
                return _err("E_NOT_FOUND", "Gerenciador de tarefas não inicializado")
            job_id = params.get("job_id") if params else None
            if not job_id:
                return _err("E_VALIDATION", "Campo 'job_id' é obrigatório")
            task = _tx_manager.get_task_status(job_id)
            if not task:
                return _err("E_NOT_FOUND", "Job não encontrado")
            return _ok({
                "job_id": task.task_id,
                "state": task.status,
                "progress": task.progress,
                "message": task.progress_message,
                "duration": task.duration,
            })

        if method == "job.cancel":
            global _tx_manager
            if _tx_manager is None:
                return _err("E_NOT_FOUND", "Gerenciador de tarefas não inicializado")
            job_id = params.get("job_id") if params else None
            if not job_id:
                return _err("E_VALIDATION", "Campo 'job_id' é obrigatório")
            task = _tx_manager.get_task_status(job_id)
            if not task:
                return _err("E_NOT_FOUND", "Job não encontrado")
            task.cancel()
            return _ok({"job_id": job_id, "state": task.status})

        return _err("E_NOT_IMPLEMENTED", f"Método não implementado: {method}")
    except Exception as e:
        return _err("E_INTERNAL", str(e))


def serve_stdio() -> int:
    try:
        # Remover sinks de console para não poluir stdout
        try:
            logger.remove()
        except Exception:
            pass

        # Loop de leitura
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                req_id = req.get("id")
                method = req.get("method")
                params = req.get("params")
                if not method:
                    _write(_err("E_VALIDATION", "Campo 'method' é obrigatório"), req_id)
                    continue
                res = _handle(method, params)
                _write(res, req_id)
            except json.JSONDecodeError as e:
                _write(_err("E_VALIDATION", f"JSON inválido: {e}"), None)
            except Exception as e:
                _write(_err("E_INTERNAL", str(e)), None)
        return 0
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(serve_stdio())
