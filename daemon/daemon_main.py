"""
Daemon Main Process

Core daemon process inspirado na arquitetura do Krisp AI.
Gerencia model persistence, multi-client connections e background processing.
"""

import asyncio
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import settings
    from daemon.resource_manager import ResourceManager
    from daemon.health_monitor import HealthMonitor
    from daemon.stdio_core import StdioCore
except ImportError as e:
    logger.error(f"Failed to import daemon dependencies: {e}")
    sys.exit(1)


class DaemonMain:
    """
    Processo principal do daemon MeetingScribe.
    
    Arquitetura inspirada no Krisp AI:
    - Model pre-loading para startup rápido
    - Multi-client connection handling
    - Background task processing
    - Health monitoring e recovery
    """
    
    def __init__(self):
        """Inicializa o daemon principal."""
        self.running = False
        self.resource_manager: Optional[ResourceManager] = None
        self.health_monitor: Optional[HealthMonitor] = None
        self.stdio_core: Optional[StdioCore] = None
        
        # Threading components (since Windows Service context)
        self.main_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
    def run(self):
        """
        Inicia o daemon principal.
        
        Executa em contexto Windows Service, então usa threading
        ao invés de asyncio event loop direto.
        """
        logger.info("MeetingScribe daemon starting...")
        
        try:
            # Setup signal handlers (if not in service context)
            if not self._is_service_context():
                self._setup_signal_handlers()
            
            # Start main daemon thread
            self.main_thread = threading.Thread(target=self._run_main_loop, daemon=False)
            self.main_thread.start()
            
            # Keep main thread alive
            self.main_thread.join()
            
        except Exception as e:
            logger.error(f"Daemon startup failed: {e}")
            raise
    
    def stop_gracefully(self):
        """Para o daemon graciosamente."""
        logger.info("MeetingScribe daemon stopping...")
        
        self.running = False
        self.stop_event.set()
        
        # Wait for main thread to finish
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=30)
        
        logger.info("MeetingScribe daemon stopped")
    
    def _run_main_loop(self):
        """Loop principal do daemon executado em thread separada."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run async main logic
            loop.run_until_complete(self._async_main())
            
        except Exception as e:
            logger.error(f"Daemon main loop error: {e}")
        finally:
            try:
                loop.close()
            except:
                pass
    
    async def _async_main(self):
        """Lógica principal assíncrona do daemon."""
        try:
            # Startup sequence
            await self._startup_sequence()
            
            # Main loop
            await self._main_processing_loop()
            
        except Exception as e:
            logger.error(f"Daemon async main error: {e}")
            raise
        finally:
            await self._shutdown_sequence()
    
    async def _startup_sequence(self):
        """
        Sequência de inicialização do daemon.
        
        Inspirada no Krisp AI:
        1. Pre-load modelos base para startup rápido
        2. Inicializar connection manager
        3. Inicializar health monitoring
        4. Configurar stdio core para communication
        """
        logger.info("Daemon startup sequence beginning...")
        
        # 1. Initialize resource manager (model pre-loading)
        logger.info("Initializing resource manager...")
        self.resource_manager = ResourceManager()
        await self.resource_manager.initialize()
        logger.info("Resource manager initialized with base models loaded")
        
        # 2. Initialize stdio core for client communication
        logger.info("Initializing stdio core...")
        self.stdio_core = StdioCore(self.resource_manager)
        await self.stdio_core.start()
        logger.info("Stdio core initialized and listening")
        
        # 3. Initialize health monitor
        logger.info("Initializing health monitor...")
        self.health_monitor = HealthMonitor(
            resource_manager=self.resource_manager,
            stdio_core=self.stdio_core
        )
        await self.health_monitor.start()
        logger.info("Health monitor started")
        
        self.running = True
        logger.info("✅ MeetingScribe daemon ready - accepting client connections")
    
    async def _main_processing_loop(self):
        """
        Loop principal de processamento.
        
        Mantém daemon alive e executa tarefas periódicas:
        - Health checks
        - Resource cleanup
        - Connection monitoring
        """
        while self.running and not self.stop_event.is_set():
            try:
                # Health monitoring check
                if self.health_monitor:
                    await self.health_monitor.periodic_check()
                
                # Resource maintenance
                if self.resource_manager:
                    await self.resource_manager.periodic_maintenance()
                
                # Sleep with stop event check
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in main processing loop: {e}")
                # Continue running unless critical error
                await asyncio.sleep(5)
    
    async def _shutdown_sequence(self):
        """Sequência de shutdown gracioso."""
        logger.info("Daemon shutdown sequence beginning...")
        
        # Stop health monitor
        if self.health_monitor:
            logger.info("Stopping health monitor...")
            await self.health_monitor.stop()
        
        # Stop stdio core
        if self.stdio_core:
            logger.info("Stopping stdio core...")
            await self.stdio_core.stop()
        
        # Cleanup resource manager
        if self.resource_manager:
            logger.info("Cleaning up resource manager...")
            await self.resource_manager.cleanup()
        
        logger.info("Daemon shutdown sequence complete")
    
    def _setup_signal_handlers(self):
        """Configura signal handlers para shutdown gracioso."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.stop_gracefully()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _is_service_context(self) -> bool:
        """Verifica se está executando em contexto Windows Service."""
        # Simple heuristic: check if stdin is not a tty
        return not sys.stdin.isatty()


def main():
    """Entry point para execução standalone (não-service)."""
    daemon = DaemonMain()
    
    try:
        daemon.run()
    except KeyboardInterrupt:
        logger.info("Daemon interrupted by user")
        daemon.stop_gracefully()
    except Exception as e:
        logger.error(f"Daemon failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())