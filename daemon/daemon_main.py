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
    from config import settings, setup_directories, setup_logging
    from daemon.stdio_core import run_stdio
    from src.teams import get_detector, start_teams_monitoring, stop_teams_monitoring
    from src.audio import get_smart_selector
    
    # Optional advanced components (future enhancement)
    try:
        from daemon.resource_manager import ResourceManager
        HAS_RESOURCE_MANAGER = True
    except ImportError:
        ResourceManager = None
        HAS_RESOURCE_MANAGER = False
        
    try:
        from daemon.health_monitor import HealthMonitor
        HAS_HEALTH_MONITOR = True
    except ImportError:
        HealthMonitor = None
        HAS_HEALTH_MONITOR = False
        
except ImportError as e:
    logger.error(f"Failed to import daemon dependencies: {e}")
    sys.exit(1)


class DaemonMain:
    """
    Main daemon orchestrator for always-ready system.
    
    Phase 1.5 implementation with critical must-have features:
    - Teams detection integration
    - Smart device selection
    - Always-ready STDIO server
    - Basic resource management
    """
    
    def __init__(self):
        """Initialize daemon main process."""
        self.running = False
        self.stdio_thread: Optional[threading.Thread] = None
        self.teams_detector = None
        self.smart_selector = None
        
        # Optional advanced components
        self.resource_manager = None
        self.health_monitor = None
        
        # Threading components for Windows Service context
        self.main_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
    def run(self):
        """
        Start daemon with all critical components.
        
        Phase 1.5 implementation focuses on must-have features:
        - Always-ready STDIO server
        - Teams detection monitoring
        - Smart device selection
        """
        logger.info("MeetingScribe Daemon v2 starting...")
        
        try:
            # Setup system
            self._setup_system()
            
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
        """Main daemon loop executed in separate thread."""
        try:
            logger.info("Starting daemon main loop")
            
            # Initialize critical components
            self._initialize_components()
            
            # Start STDIO server
            self._start_stdio_server()
            
            # Start Teams monitoring
            self._start_teams_monitoring()
            
            # Initialize optional advanced components
            self._initialize_advanced_components()
            
            self.running = True
            logger.info("✅ MeetingScribe Daemon fully operational - accepting client connections")
            
            # Main processing loop
            self._main_processing_loop()
            
        except Exception as e:
            logger.error(f"Daemon main loop error: {e}")
        finally:
            self._cleanup_components()
    
    def _setup_system(self) -> None:
        """Setup system directories and logging"""
        setup_directories()
        setup_logging()
        logger.info("System directories and logging initialized")
    
    def _initialize_components(self) -> None:
        """Initialize critical daemon components"""
        # Initialize Teams detector
        self.teams_detector = get_detector()
        
        # Setup Teams detection callbacks
        self.teams_detector.on_meeting_detected = self._on_teams_meeting_detected
        self.teams_detector.on_meeting_ended = self._on_teams_meeting_ended
        self.teams_detector.on_state_changed = self._on_teams_state_changed
        
        # Initialize smart device selector
        self.smart_selector = get_smart_selector()
        
        logger.info("Critical components initialized (Teams detection, smart device selection)")
    
    def _initialize_advanced_components(self) -> None:
        """Initialize optional advanced components"""
        try:
            # Initialize resource manager if available
            if HAS_RESOURCE_MANAGER and ResourceManager:
                logger.info("Initializing resource manager...")
                self.resource_manager = ResourceManager()
                # Note: ResourceManager.initialize() would be async, 
                # for Phase 1.5 we skip advanced resource management
                logger.info("Resource manager initialized")
            else:
                logger.info("Resource manager not available, skipping")
                
            # Initialize health monitor if available
            if HAS_HEALTH_MONITOR and HealthMonitor:
                logger.info("Initializing health monitor...")
                self.health_monitor = HealthMonitor()
                logger.info("Health monitor initialized")
            else:
                logger.info("Health monitor not available, using basic monitoring")
                
        except Exception as e:
            logger.warning(f"Advanced components initialization failed: {e}")
            # Continue without advanced components
    
    def _start_stdio_server(self) -> None:
        """Start STDIO JSON-RPC server in background thread"""
        def stdio_worker():
            try:
                logger.info("Starting STDIO JSON-RPC server")
                run_stdio()  # This blocks until stdin closes
            except Exception as e:
                logger.error(f"STDIO server error: {e}")
                self.running = False
        
        self.stdio_thread = threading.Thread(target=stdio_worker, daemon=True)
        self.stdio_thread.start()
        logger.info("STDIO server thread started")
    
    def _start_teams_monitoring(self) -> None:
        """Start Teams meeting detection monitoring"""
        success = start_teams_monitoring()
        if success:
            logger.info("Teams monitoring started successfully")
        else:
            logger.warning("Teams monitoring failed to start")
    
    def _main_processing_loop(self) -> None:
        """
        Main daemon processing loop.
        
        Keeps daemon alive and performs periodic health checks.
        """
        last_health_check = time.time()
        health_check_interval = 60  # seconds
        
        while self.running and not self.stop_event.is_set():
            try:
                # Periodic health checks
                current_time = time.time()
                if current_time - last_health_check >= health_check_interval:
                    self._perform_health_check()
                    last_health_check = current_time
                
                # Sleep with stop event check
                self.stop_event.wait(1)  # 1 second timeout
                
            except Exception as e:
                logger.error(f"Error in main processing loop: {e}")
                time.sleep(5)  # Sleep longer on error
    
    def _perform_health_check(self) -> None:
        """Perform basic health checks"""
        try:
            # Check STDIO thread health
            if self.stdio_thread and not self.stdio_thread.is_alive():
                logger.warning("STDIO thread died, attempting restart")
                self._start_stdio_server()
            
            # Check Teams monitoring health
            if self.teams_detector and not self.teams_detector._running:
                logger.warning("Teams monitoring stopped, restarting")
                start_teams_monitoring()
            
            # Log memory usage if psutil available
            try:
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / (1024 * 1024)
                
                # Log warning if memory usage exceeds 500MB (FR-001 specifies <300MB idle)
                if memory_mb > 500:
                    logger.warning(f"High memory usage: {memory_mb:.1f}MB")
                else:
                    logger.debug(f"Memory usage: {memory_mb:.1f}MB")
                    
            except Exception:
                pass  # psutil not available
                
            # Use advanced health monitor if available
            if self.health_monitor and hasattr(self.health_monitor, 'periodic_check'):
                try:
                    # For Phase 1.5, we call synchronous version if available
                    if hasattr(self.health_monitor, 'sync_periodic_check'):
                        self.health_monitor.sync_periodic_check()
                except Exception as e:
                    logger.debug(f"Advanced health check failed: {e}")
                    
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    def _on_teams_meeting_detected(self, detection) -> None:
        """Callback for Teams meeting detection"""
        logger.info(f"Teams meeting detected: {detection.window_title}")
        logger.info(f"Meeting details: process={detection.process_name}, "
                   f"audio_active={detection.audio_active}, "
                   f"confidence={detection.confidence:.2f}")
        
        # Future enhancement: Auto-prompt user for recording
        # This would implement FR-002 Teams Integration
    
    def _on_teams_meeting_ended(self, detection) -> None:
        """Callback for Teams meeting end"""
        logger.info(f"Teams meeting ended: {detection.window_title}")
    
    def _on_teams_state_changed(self, old_state, new_state) -> None:
        """Callback for Teams detection state changes"""
        logger.debug(f"Teams detection state: {old_state.value} -> {new_state.value}")
    
    def _cleanup_components(self) -> None:
        """Cleanup daemon components"""
        logger.info("Cleaning up daemon components...")
        
        try:
            # Stop Teams monitoring
            if self.teams_detector:
                stop_teams_monitoring()
            
            # Advanced cleanup if available
            if self.resource_manager and hasattr(self.resource_manager, 'cleanup'):
                try:
                    # For Phase 1.5, call synchronous cleanup if available
                    if hasattr(self.resource_manager, 'sync_cleanup'):
                        self.resource_manager.sync_cleanup()
                except Exception as e:
                    logger.debug(f"Advanced resource cleanup failed: {e}")
            
            if self.health_monitor and hasattr(self.health_monitor, 'stop'):
                try:
                    if hasattr(self.health_monitor, 'sync_stop'):
                        self.health_monitor.sync_stop()
                except Exception as e:
                    logger.debug(f"Advanced health monitor stop failed: {e}")
            
            logger.info("Daemon cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
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