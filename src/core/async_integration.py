"""
Integração Assíncrona para MeetingScribe

Wrapper e utilitários para integrar processamento assíncrono
com a interface principal da aplicação.

Author: MeetingScribe Team
Version: 1.1.0
Python: >=3.8
"""

import time
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from concurrent.futures import Future

from loguru import logger
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID

try:
    from .async_processor import (
        get_async_processor, AsyncTask, TaskPriority, TaskStatus
    )
    from src.transcription.transcriber import WhisperModelSize, TranscriptionResult
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    logger.debug("Processamento assíncrono não disponível")


@dataclass
class AsyncTranscriptionRequest:
    """Solicitação de transcrição assíncrona."""
    audio_path: Path
    model_size: WhisperModelSize = WhisperModelSize.BASE
    use_chunked: bool = True
    use_gpu: bool = False
    language: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    
    # Callbacks
    progress_callback: Optional[Callable[[float, str], None]] = None
    completion_callback: Optional[Callable[[TranscriptionResult], None]] = None
    error_callback: Optional[Callable[[Exception], None]] = None


class AsyncTranscriptionManager:
    """
    Gerenciador para transcrições assíncronas.
    
    Facilita submissão e monitoramento de tarefas de transcrição
    com interface amigável para uso na aplicação principal.
    """
    
    def __init__(self):
        """Inicializa o gerenciador."""
        self._active_tasks: Dict[str, AsyncTask] = {}
        self._lock = threading.RLock()
        
        if not ASYNC_AVAILABLE:
            logger.warning("Processamento assíncrono não disponível")
    
    def submit_transcription(
        self,
        request: AsyncTranscriptionRequest,
        task_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Submete solicitação de transcrição assíncrona.
        
        Args:
            request: Dados da solicitação
            task_name: Nome personalizado da tarefa
            
        Returns:
            str: ID da tarefa ou None se falhou
        """
        if not ASYNC_AVAILABLE:
            logger.error("Processamento assíncrono não disponível")
            return None
        
        try:
            processor = get_async_processor()
            
            # Nome da tarefa
            if task_name is None:
                audio_name = request.audio_path.stem
                task_name = f"Transcrição: {audio_name}"
            
            # Função de transcrição
            def transcribe_sync():
                if request.use_chunked:
                    from src.transcription.chunked_transcriber import create_chunked_transcriber
                    transcriber = create_chunked_transcriber(
                        model_size=request.model_size,
                        use_gpu=request.use_gpu,
                        parallel_chunks=True
                    )
                else:
                    from src.transcription.transcriber import create_transcriber
                    transcriber = create_transcriber(
                        model_size=request.model_size,
                        use_gpu=request.use_gpu
                    )
                
                with transcriber:
                    # Criar wrapper de progresso
                    progress = None
                    if request.progress_callback:
                        from src.transcription.transcriber import TranscriptionProgress
                        progress = TranscriptionProgress(request.progress_callback)
                    
                    return transcriber.transcribe_file(
                        request.audio_path, 
                        progress, 
                        request.language
                    )
            
            # Submeter tarefa
            task = processor.submit_task(
                transcribe_sync,
                name=task_name,
                priority=request.priority,
                progress_callback=request.progress_callback,
                completion_callback=request.completion_callback,
                error_callback=request.error_callback
            )
            
            # Registrar tarefa ativa
            with self._lock:
                self._active_tasks[task.task_id] = task
            
            logger.info(f"Transcrição submetida: {task_name} (ID: {task.task_id})")
            return task.task_id
            
        except Exception as e:
            logger.error(f"Erro ao submeter transcrição: {e}")
            if request.error_callback:
                request.error_callback(e)
            return None
    
    def get_task_status(self, task_id: str) -> Optional[AsyncTask]:
        """Obtém status de uma tarefa."""
        if not ASYNC_AVAILABLE:
            return None
        
        processor = get_async_processor()
        return processor.get_task_status(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancela uma tarefa."""
        if not ASYNC_AVAILABLE:
            return False
        
        processor = get_async_processor()
        success = processor.cancel_task(task_id)
        
        if success:
            with self._lock:
                self._active_tasks.pop(task_id, None)
            logger.info(f"Tarefa {task_id} cancelada")
        
        return success
    
    def get_active_tasks(self) -> List[AsyncTask]:
        """Retorna lista de tarefas ativas."""
        if not ASYNC_AVAILABLE:
            return []
        
        processor = get_async_processor()
        return processor.get_running_tasks() + processor.get_queued_tasks()
    
    def wait_for_completion(
        self, 
        task_id: str, 
        timeout: Optional[float] = None,
        show_progress: bool = True
    ) -> Optional[TranscriptionResult]:
        """
        Aguarda conclusão de uma tarefa com progresso visual.
        
        Args:
            task_id: ID da tarefa
            timeout: Timeout em segundos
            show_progress: Mostrar barra de progresso
            
        Returns:
            TranscriptionResult ou None se falhou/timeout
        """
        if not ASYNC_AVAILABLE:
            return None
        
        start_time = time.time()
        
        # Configurar progresso visual
        if show_progress:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                TextColumn("[blue]{task.fields[status]}"),
                console=None
            )
            
            progress.start()
            progress_task_id = progress.add_task("Processando...", total=100, status="Iniciando")
        
        try:
            while True:
                # Verificar timeout
                if timeout and (time.time() - start_time) > timeout:
                    logger.warning(f"Timeout aguardando tarefa {task_id}")
                    return None
                
                # Obter status da tarefa
                task = self.get_task_status(task_id)
                if not task:
                    logger.error(f"Tarefa {task_id} não encontrada")
                    return None
                
                # Atualizar progresso visual
                if show_progress:
                    progress_pct = task.progress * 100
                    status_msg = task.progress_message or task.status.value
                    progress.update(
                        progress_task_id,
                        completed=progress_pct,
                        status=status_msg
                    )
                
                # Verificar se concluída
                if task.status == TaskStatus.COMPLETED:
                    if show_progress:
                        progress.update(progress_task_id, completed=100, status="Concluído!")
                        time.sleep(0.5)  # Mostrar 100% brevemente
                    
                    logger.success(f"Tarefa {task_id} concluída com sucesso")
                    return task.result
                
                elif task.status == TaskStatus.FAILED:
                    if show_progress:
                        progress.update(progress_task_id, status="Falhou!")
                    
                    logger.error(f"Tarefa {task_id} falhou: {task.error}")
                    return None
                
                elif task.status == TaskStatus.CANCELLED:
                    if show_progress:
                        progress.update(progress_task_id, status="Cancelada")
                    
                    logger.info(f"Tarefa {task_id} foi cancelada")
                    return None
                
                # Aguardar antes de verificar novamente
                time.sleep(0.5)
        
        finally:
            if show_progress:
                progress.stop()
            
            # Remover da lista de tarefas ativas
            with self._lock:
                self._active_tasks.pop(task_id, None)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do processamento assíncrono."""
        if not ASYNC_AVAILABLE:
            return {"available": False}
        
        processor = get_async_processor()
        stats = processor.get_stats()
        
        # Adicionar informações das tarefas ativas
        with self._lock:
            stats["active_transcriptions"] = len(self._active_tasks)
            stats["available"] = True
        
        return stats
    
    def cleanup_completed(self) -> int:
        """Remove tarefas concluídas da memória."""
        if not ASYNC_AVAILABLE:
            return 0
        
        processor = get_async_processor()
        return processor.clear_completed_tasks()


# =============================================================================
# INSTÂNCIA GLOBAL E FUNÇÕES DE CONVENIÊNCIA
# =============================================================================

_global_transcription_manager: Optional[AsyncTranscriptionManager] = None


def get_transcription_manager() -> AsyncTranscriptionManager:
    """Retorna instância global do gerenciador de transcrições."""
    global _global_transcription_manager
    
    if _global_transcription_manager is None:
        _global_transcription_manager = AsyncTranscriptionManager()
    
    return _global_transcription_manager


def transcribe_file_async(
    audio_path: Path,
    model_size: WhisperModelSize = WhisperModelSize.BASE,
    use_chunked: bool = True,
    priority: TaskPriority = TaskPriority.NORMAL,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    completion_callback: Optional[Callable[[TranscriptionResult], None]] = None,
    error_callback: Optional[Callable[[Exception], None]] = None
) -> Optional[str]:
    """
    Função de conveniência para transcrição assíncrona.
    
    Args:
        audio_path: Caminho do arquivo de áudio
        model_size: Tamanho do modelo Whisper
        use_chunked: Usar processamento por chunks
        priority: Prioridade da tarefa
        progress_callback: Callback de progresso
        completion_callback: Callback de conclusão
        error_callback: Callback de erro
        
    Returns:
        str: ID da tarefa ou None se falhou
    """
    manager = get_transcription_manager()
    
    request = AsyncTranscriptionRequest(
        audio_path=audio_path,
        model_size=model_size,
        use_chunked=use_chunked,
        priority=priority,
        progress_callback=progress_callback,
        completion_callback=completion_callback,
        error_callback=error_callback
    )
    
    return manager.submit_transcription(request)


def wait_for_transcription(
    task_id: str,
    timeout: Optional[float] = None,
    show_progress: bool = True
) -> Optional[TranscriptionResult]:
    """
    Aguarda conclusão de transcrição com progresso visual.
    
    Args:
        task_id: ID da tarefa
        timeout: Timeout em segundos
        show_progress: Mostrar progresso visual
        
    Returns:
        TranscriptionResult ou None
    """
    manager = get_transcription_manager()
    return manager.wait_for_completion(task_id, timeout, show_progress)


def get_async_stats() -> Dict[str, Any]:
    """Retorna estatísticas do processamento assíncrono."""
    manager = get_transcription_manager()
    return manager.get_stats()


def cancel_transcription(task_id: str) -> bool:
    """Cancela uma transcrição em andamento."""
    manager = get_transcription_manager()
    return manager.cancel_task(task_id)


def list_active_transcriptions() -> List[AsyncTask]:
    """Lista todas as transcrições ativas."""
    manager = get_transcription_manager()
    return manager.get_active_tasks()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "AsyncTranscriptionManager",
    "AsyncTranscriptionRequest",
    "get_transcription_manager",
    "transcribe_file_async",
    "wait_for_transcription",
    "get_async_stats",
    "cancel_transcription",
    "list_active_transcriptions"
]