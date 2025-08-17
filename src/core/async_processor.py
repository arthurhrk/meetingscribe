"""
Sistema de Processamento Assíncrono

Implementa processamento assíncrono para operações de transcrição,
melhorando responsividade e permitindo operações concorrentes.

Author: MeetingScribe Team
Version: 1.1.0
Python: >=3.8
"""

import asyncio
import threading
import time
import queue
from pathlib import Path
from typing import (
    Dict, List, Optional, Callable, Any, Union, 
    Awaitable, TypeVar, Generic, Coroutine
)
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
import uuid
import weakref
from contextlib import asynccontextmanager

from loguru import logger

# Importações condicionais
try:
    from src.transcription.transcriber import (
        WhisperTranscriber, TranscriptionResult, TranscriptionProgress,
        WhisperModelSize, create_transcriber
    )
    from src.transcription.chunked_transcriber import (
        ChunkedWhisperTranscriber, create_chunked_transcriber
    )
    TRANSCRIPTION_AVAILABLE = True
except ImportError:
    TRANSCRIPTION_AVAILABLE = False
    logger.debug("Módulos de transcrição não disponíveis")

try:
    from src.core.memory_manager import get_memory_manager, managed_memory
    MEMORY_MANAGER_AVAILABLE = True
except ImportError:
    MEMORY_MANAGER_AVAILABLE = False


T = TypeVar('T')


class TaskStatus(str, Enum):
    """Status de uma tarefa assíncrona."""
    PENDING = "pending"       # Aguardando execução
    RUNNING = "running"       # Em execução
    COMPLETED = "completed"   # Concluída com sucesso
    FAILED = "failed"         # Falhou com erro
    CANCELLED = "cancelled"   # Cancelada pelo usuário


class TaskPriority(int, Enum):
    """Prioridade de execução de tarefas."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class AsyncTask(Generic[T]):
    """Representa uma tarefa assíncrona."""
    task_id: str
    name: str
    func: Callable[..., T]
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    
    # Metadados
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # Estado
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[T] = None
    error: Optional[Exception] = None
    progress: float = 0.0
    progress_message: str = ""
    
    # Callbacks
    progress_callback: Optional[Callable[[float, str], None]] = None
    completion_callback: Optional[Callable[[T], None]] = None
    error_callback: Optional[Callable[[Exception], None]] = None
    
    # Controle
    _cancel_event: threading.Event = field(default_factory=threading.Event)
    _future: Optional[Future] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Duração da execução em segundos."""
        if self.started_at is None:
            return None
        end_time = self.completed_at or time.time()
        return end_time - self.started_at
    
    @property
    def is_cancelled(self) -> bool:
        """Verifica se a tarefa foi cancelada."""
        return self._cancel_event.is_set()
    
    def cancel(self):
        """Cancela a execução da tarefa."""
        self._cancel_event.set()
        if self._future and not self._future.done():
            self._future.cancel()
        self.status = TaskStatus.CANCELLED
        logger.info(f"Tarefa {self.task_id} cancelada")
    
    def update_progress(self, progress: float, message: str = ""):
        """Atualiza progresso da tarefa."""
        self.progress = max(0.0, min(1.0, progress))
        self.progress_message = message
        
        if self.progress_callback:
            try:
                self.progress_callback(self.progress, message)
            except Exception as e:
                logger.warning(f"Erro no callback de progresso: {e}")


@dataclass 
class AsyncProcessorConfig:
    """Configuração do processador assíncrono."""
    # Pool de threads
    max_workers: int = 4
    thread_name_prefix: str = "AsyncProcessor"
    
    # Gerenciamento de tarefas
    max_concurrent_tasks: int = 3
    task_timeout_seconds: float = 3600  # 1 hora
    cleanup_interval_seconds: float = 300  # 5 minutos
    
    # Otimizações
    enable_memory_management: bool = True
    enable_progress_tracking: bool = True
    enable_task_queuing: bool = True
    
    # Callbacks globais
    global_progress_callback: Optional[Callable[[str, float, str], None]] = None
    global_completion_callback: Optional[Callable[[str, Any], None]] = None
    global_error_callback: Optional[Callable[[str, Exception], None]] = None


class AsyncTranscriptionQueue:
    """Fila inteligente para tarefas de transcrição."""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_size)
        self._tasks: Dict[str, AsyncTask] = {}
        self._lock = threading.RLock()
    
    def add_task(self, task: AsyncTask) -> bool:
        """Adiciona tarefa à fila."""
        with self._lock:
            if len(self._tasks) >= self.max_size:
                logger.warning("Fila de tarefas cheia")
                return False
            
            # Prioridade invertida para queue.PriorityQueue (menor número = maior prioridade)
            priority_score = -task.priority.value
            
            try:
                self._queue.put((priority_score, task.created_at, task), block=False)
                self._tasks[task.task_id] = task
                logger.debug(f"Tarefa {task.task_id} adicionada à fila (prioridade: {task.priority.name})")
                return True
            except queue.Full:
                logger.warning("Não foi possível adicionar tarefa à fila")
                return False
    
    def get_next_task(self, timeout: Optional[float] = None) -> Optional[AsyncTask]:
        """Obtém próxima tarefa da fila."""
        try:
            _, _, task = self._queue.get(timeout=timeout)
            return task
        except queue.Empty:
            return None
    
    def remove_task(self, task_id: str) -> bool:
        """Remove tarefa da fila."""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False
    
    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """Obtém tarefa por ID."""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[AsyncTask]:
        """Retorna todas as tarefas."""
        with self._lock:
            return list(self._tasks.values())
    
    def clear(self):
        """Limpa fila."""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            self._tasks.clear()
    
    @property
    def size(self) -> int:
        """Tamanho atual da fila."""
        return len(self._tasks)


class AsyncProcessor:
    """
    Processador assíncrono principal.
    
    Gerencia execução concorrente de tarefas de transcrição
    com controle de prioridade, progresso e recursos.
    """
    
    def __init__(self, config: Optional[AsyncProcessorConfig] = None):
        """
        Inicializa processador assíncrono.
        
        Args:
            config: Configuração do processador
        """
        self.config = config or AsyncProcessorConfig()
        
        # Pool de execução
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.max_workers,
            thread_name_prefix=self.config.thread_name_prefix
        )
        
        # Fila de tarefas
        self._task_queue = AsyncTranscriptionQueue()
        self._running_tasks: Dict[str, AsyncTask] = {}
        
        # Controle
        self._running = False
        self._worker_threads: List[threading.Thread] = []
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
        # Estatísticas
        self._stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_cancelled': 0,
            'total_processing_time': 0.0
        }
        
        logger.info(f"Processador assíncrono inicializado - workers: {self.config.max_workers}")
    
    def start(self):
        """Inicia o processador assíncrono."""
        if self._running:
            logger.warning("Processador já está executando")
            return
        
        self._running = True
        self._stop_event.clear()
        
        # Iniciar workers
        for i in range(self.config.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"{self.config.thread_name_prefix}-Worker-{i}",
                daemon=True
            )
            worker.start()
            self._worker_threads.append(worker)
        
        # Iniciar limpeza automática
        if self.config.cleanup_interval_seconds > 0:
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                name=f"{self.config.thread_name_prefix}-Cleanup",
                daemon=True
            )
            self._cleanup_thread.start()
        
        logger.info(f"Processador assíncrono iniciado com {len(self._worker_threads)} workers")
    
    def stop(self, timeout: float = 10.0):
        """Para o processador assíncrono."""
        if not self._running:
            return
        
        logger.info("Parando processador assíncrono...")
        
        self._running = False
        self._stop_event.set()
        
        # Cancelar tarefas em execução
        with self._lock:
            for task in self._running_tasks.values():
                task.cancel()
        
        # Aguardar workers finalizarem
        for worker in self._worker_threads:
            worker.join(timeout=timeout / len(self._worker_threads))
        
        # Aguardar cleanup thread
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=2.0)
        
        # Shutdown executor
        self._executor.shutdown(wait=True, timeout=timeout)
        
        logger.info("Processador assíncrono parado")
    
    def submit_task(
        self,
        func: Callable[..., T],
        *args,
        name: str = "Async Task",
        priority: TaskPriority = TaskPriority.NORMAL,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        completion_callback: Optional[Callable[[T], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
        **kwargs
    ) -> AsyncTask[T]:
        """
        Submete tarefa para execução assíncrona.
        
        Args:
            func: Função a ser executada
            *args: Argumentos posicionais
            name: Nome da tarefa
            priority: Prioridade de execução
            progress_callback: Callback de progresso
            completion_callback: Callback de conclusão
            error_callback: Callback de erro
            **kwargs: Argumentos nomeados
            
        Returns:
            AsyncTask: Objeto da tarefa
        """
        task_id = str(uuid.uuid4())
        
        task = AsyncTask(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            progress_callback=progress_callback,
            completion_callback=completion_callback,
            error_callback=error_callback
        )
        
        if self._task_queue.add_task(task):
            logger.info(f"Tarefa '{name}' submetida (ID: {task_id})")
            return task
        else:
            logger.error(f"Falha ao submeter tarefa '{name}'")
            task.status = TaskStatus.FAILED
            task.error = RuntimeError("Falha ao adicionar à fila")
            return task
    
    def _worker_loop(self):
        """Loop principal do worker."""
        worker_name = threading.current_thread().name
        logger.debug(f"Worker {worker_name} iniciado")
        
        while self._running and not self._stop_event.is_set():
            try:
                # Obter próxima tarefa
                task = self._task_queue.get_next_task(timeout=1.0)
                
                if task is None:
                    continue
                
                if task.is_cancelled:
                    self._task_queue.remove_task(task.task_id)
                    continue
                
                # Executar tarefa
                self._execute_task(task, worker_name)
                
            except Exception as e:
                logger.error(f"Erro no worker {worker_name}: {e}")
                time.sleep(1.0)
        
        logger.debug(f"Worker {worker_name} finalizado")
    
    def _execute_task(self, task: AsyncTask, worker_name: str):
        """Executa uma tarefa específica."""
        with self._lock:
            if len(self._running_tasks) >= self.config.max_concurrent_tasks:
                # Recolocar na fila se limite atingido
                self._task_queue.add_task(task)
                return
            
            self._running_tasks[task.task_id] = task
        
        try:
            logger.info(f"[{worker_name}] Executando: {task.name}")
            
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            
            # Callback de progresso global
            if self.config.global_progress_callback:
                self.config.global_progress_callback(task.task_id, 0.0, "Iniciando...")
            
            # Contexto de memória gerenciada
            memory_context = (managed_memory() if MEMORY_MANAGER_AVAILABLE 
                            else self._null_context())
            
            with memory_context:
                # Executar função
                if asyncio.iscoroutinefunction(task.func):
                    # Função assíncrona
                    result = self._run_async_function(task)
                else:
                    # Função síncrona
                    result = task.func(*task.args, **task.kwargs)
                
                if task.is_cancelled:
                    task.status = TaskStatus.CANCELLED
                    return
                
                # Sucesso
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                task.progress = 1.0
                task.progress_message = "Concluído"
                
                # Callbacks
                if task.completion_callback:
                    task.completion_callback(result)
                
                if self.config.global_completion_callback:
                    self.config.global_completion_callback(task.task_id, result)
                
                # Estatísticas
                self._stats['tasks_completed'] += 1
                if task.duration:
                    self._stats['total_processing_time'] += task.duration
                
                logger.success(f"[{worker_name}] Concluído: {task.name} ({task.duration:.2f}s)")
        
        except Exception as e:
            logger.error(f"[{worker_name}] Erro em {task.name}: {e}")
            
            task.error = e
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            
            # Callbacks de erro
            if task.error_callback:
                task.error_callback(e)
            
            if self.config.global_error_callback:
                self.config.global_error_callback(task.task_id, e)
            
            self._stats['tasks_failed'] += 1
        
        finally:
            # Remover da lista de execução
            with self._lock:
                self._running_tasks.pop(task.task_id, None)
                self._task_queue.remove_task(task.task_id)
    
    def _run_async_function(self, task: AsyncTask) -> Any:
        """Executa função assíncrona em thread separada."""
        # Criar novo loop para a thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Executar coroutine
            return loop.run_until_complete(task.func(*task.args, **task.kwargs))
        finally:
            loop.close()
    
    @asynccontextmanager
    async def _null_context(self):
        """Context manager nulo para compatibilidade."""
        yield
    
    def _cleanup_loop(self):
        """Loop de limpeza automática."""
        logger.debug("Thread de limpeza iniciada")
        
        while self._running and not self._stop_event.wait(self.config.cleanup_interval_seconds):
            try:
                self._cleanup_completed_tasks()
            except Exception as e:
                logger.error(f"Erro na limpeza automática: {e}")
        
        logger.debug("Thread de limpeza finalizada")
    
    def _cleanup_completed_tasks(self):
        """Remove tarefas concluídas antigas."""
        current_time = time.time()
        cleanup_count = 0
        
        # Obter tarefas para limpeza
        tasks_to_remove = []
        for task in self._task_queue.get_all_tasks():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                task.completed_at and 
                current_time - task.completed_at > 3600):  # 1 hora
                tasks_to_remove.append(task.task_id)
        
        # Remover tarefas antigas
        for task_id in tasks_to_remove:
            if self._task_queue.remove_task(task_id):
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.debug(f"Limpeza automática: {cleanup_count} tarefas removidas")
    
    def get_task_status(self, task_id: str) -> Optional[AsyncTask]:
        """Obtém status de uma tarefa."""
        # Verificar tarefas em execução
        task = self._running_tasks.get(task_id)
        if task:
            return task
        
        # Verificar fila
        return self._task_queue.get_task(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancela uma tarefa."""
        task = self.get_task_status(task_id)
        if task:
            task.cancel()
            self._stats['tasks_cancelled'] += 1
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do processador."""
        with self._lock:
            return {
                'running': self._running,
                'workers': len(self._worker_threads),
                'queue_size': self._task_queue.size,
                'running_tasks': len(self._running_tasks),
                'tasks_completed': self._stats['tasks_completed'],
                'tasks_failed': self._stats['tasks_failed'],
                'tasks_cancelled': self._stats['tasks_cancelled'],
                'total_processing_time': self._stats['total_processing_time'],
                'average_task_time': (
                    self._stats['total_processing_time'] / max(self._stats['tasks_completed'], 1)
                )
            }
    
    def get_running_tasks(self) -> List[AsyncTask]:
        """Retorna tarefas em execução."""
        with self._lock:
            return list(self._running_tasks.values())
    
    def get_queued_tasks(self) -> List[AsyncTask]:
        """Retorna tarefas na fila."""
        return [task for task in self._task_queue.get_all_tasks() 
                if task.status == TaskStatus.PENDING]
    
    def clear_completed_tasks(self):
        """Remove todas as tarefas concluídas."""
        removed = 0
        for task in self._task_queue.get_all_tasks():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                if self._task_queue.remove_task(task.task_id):
                    removed += 1
        
        logger.info(f"Limpeza manual: {removed} tarefas removidas")
        return removed
    
    def shutdown(self):
        """Finaliza processador e limpa recursos."""
        self.stop()
        self._task_queue.clear()
        logger.info("Processador assíncrono finalizado")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# =============================================================================
# FUNÇÃO DE CONVENIÊNCIA PARA TRANSCRIÇÃO ASSÍNCRONA
# =============================================================================

async def transcribe_async(
    audio_path: Path,
    model_size: WhisperModelSize = WhisperModelSize.BASE,
    use_chunked: bool = True,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> TranscriptionResult:
    """
    Transcreve áudio de forma assíncrona.
    
    Args:
        audio_path: Caminho do arquivo de áudio
        model_size: Tamanho do modelo Whisper
        use_chunked: Usar transcrição por chunks
        progress_callback: Callback de progresso
        
    Returns:
        TranscriptionResult: Resultado da transcrição
    """
    if not TRANSCRIPTION_AVAILABLE:
        raise RuntimeError("Módulos de transcrição não disponíveis")
    
    def sync_transcribe():
        if use_chunked:
            transcriber = create_chunked_transcriber(
                model_size=model_size,
                parallel_chunks=True
            )
        else:
            transcriber = create_transcriber(model_size=model_size)
        
        with transcriber:
            progress = None
            if progress_callback:
                from src.transcription.transcriber import TranscriptionProgress
                progress = TranscriptionProgress(progress_callback)
            
            return transcriber.transcribe_file(audio_path, progress)
    
    # Executar em thread separada
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, sync_transcribe)
    return result


# =============================================================================
# SINGLETON GLOBAL
# =============================================================================

_global_async_processor: Optional[AsyncProcessor] = None
_processor_lock = threading.Lock()


def get_async_processor() -> AsyncProcessor:
    """Retorna instância singleton do processador global."""
    global _global_async_processor
    
    if _global_async_processor is None:
        with _processor_lock:
            if _global_async_processor is None:
                config = AsyncProcessorConfig()
                _global_async_processor = AsyncProcessor(config)
                _global_async_processor.start()
                logger.info("Processador assíncrono global inicializado")
    
    return _global_async_processor


def shutdown_async_processor():
    """Finaliza processador global."""
    global _global_async_processor
    
    if _global_async_processor is not None:
        _global_async_processor.shutdown()
        _global_async_processor = None


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "AsyncProcessor",
    "AsyncProcessorConfig", 
    "AsyncTask",
    "TaskStatus",
    "TaskPriority",
    "AsyncTranscriptionQueue",
    "get_async_processor",
    "shutdown_async_processor",
    "transcribe_async"
]