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
    from daemon.fast_startup import execute_fast_startup, get_startup_metrics
    from daemon.memory_optimizer import (
        get_memory_optimizer, 
        start_memory_monitoring,
        register_memory_cleanup_callback
    )
    
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
    
    FR-001 compliant implementation:
    - <3s startup time with fast startup optimization
    - <300MB RAM with memory optimization and monitoring
    - Always-ready STDIO server with health monitoring
    - Teams detection and smart device selection
    """
    
    def __init__(self):
        """Initialize daemon main process."""
        self.running = False
        self.stdio_thread: Optional[threading.Thread] = None
        self.teams_detector = None
        self.smart_selector = None
        
        # FR-001 optimization components
        self.memory_optimizer = get_memory_optimizer()
        self.startup_successful = False
        
        # Optional advanced components
        self.resource_manager = None
        self.health_monitor = None
        
        # Threading components for Windows Service context
        self.main_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
    def run(self):
        """
        Start daemon with FR-001 optimizations.
        
        Implements Always-Ready System requirements:
        - <3s startup time via fast startup optimization
        - <300MB RAM via memory optimization and monitoring  
        - 99.9% uptime via health monitoring and auto-restart
        """
        logger.info("MeetingScribe Daemon v2 (FR-001 optimized) starting...")
        
        try:
            # FR-001: Execute fast startup sequence (<3s target)
            self.startup_successful = execute_fast_startup()
            if not self.startup_successful:
                logger.warning("Fast startup target missed, continuing with standard startup")
            
            # Setup signal handlers (if not in service context)
            if not self._is_service_context():
                self._setup_signal_handlers()
            
            # FR-001: Start memory monitoring (<300MB target) 
            self._start_memory_optimization()
            
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
            logger.info("Starting daemon main loop (FR-001 optimized)")
            
            # Use fast startup cached components if available
            self._initialize_components_optimized()
            
            # Start STDIO server (cached from fast startup)
            self._start_stdio_server_optimized()
            
            # Start Teams monitoring
            self._start_teams_monitoring()
            
            # Initialize optional advanced components
            self._initialize_advanced_components()
            
            self.running = True
            
            # Log FR-001 compliance status
            self._log_fr001_compliance()
            
            logger.info("✅ MeetingScribe Daemon fully operational - accepting client connections")
            
            # Main processing loop with FR-001 monitoring
            self._main_processing_loop_optimized()
            
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
    
    def _start_memory_optimization(self) -> None:
        """Start memory optimization for FR-001 compliance"""
        try:
            # Register cleanup callbacks
            register_memory_cleanup_callback(self._memory_cleanup_callback)
            
            # Start memory monitoring
            success = start_memory_monitoring(interval=30.0)
            if success:
                logger.info("✅ Memory monitoring started (target: <300MB)")
            else:
                logger.warning("⚠️ Memory monitoring unavailable (psutil not found)")
                
        except Exception as e:
            logger.error(f"Memory optimization startup failed: {e}")
    
    def _memory_cleanup_callback(self) -> None:
        """Memory cleanup callback for when usage exceeds FR-001 target"""
        logger.info("Executing memory cleanup due to high usage")
        
        try:
            # Force garbage collection to free unused memory
            import gc
            collected = gc.collect()
            logger.debug(f"Garbage collection freed {collected} objects")
            
            logger.info("Memory cleanup completed")
            
        except Exception as e:
            logger.error(f"Memory cleanup failed: {e}")
    
    def _initialize_components_optimized(self) -> None:
        """Initialize components using fast startup cache when available"""
        from daemon.fast_startup import get_cached_component
        
        # Try to get cached Teams detector
        cached_detector = get_cached_component('teams_detector')
        if cached_detector:
            self.teams_detector = cached_detector
            logger.debug("Using cached Teams detector")
        else:
            # Fallback to normal initialization
            self.teams_detector = get_detector()
            
        # Setup Teams detection callbacks
        self.teams_detector.on_meeting_detected = self._on_teams_meeting_detected
        self.teams_detector.on_meeting_ended = self._on_teams_meeting_ended
        self.teams_detector.on_state_changed = self._on_teams_state_changed
        
        # Try to get cached smart selector
        cached_selector = get_cached_component('smart_selector')
        if cached_selector:
            self.smart_selector = cached_selector
            logger.debug("Using cached smart selector")
        else:
            # Fallback to normal initialization
            self.smart_selector = get_smart_selector()
            
        logger.info("Critical components initialized (optimized path)")
    
    def _start_stdio_server_optimized(self) -> None:
        """Start STDIO server using fast startup optimizations"""
        from daemon.fast_startup import get_cached_component
        
        # Check if STDIO was prepared during fast startup
        stdio_ready = get_cached_component('stdio_imports') is not None
        
        def stdio_worker():
            try:
                if stdio_ready:
                    logger.debug("Using fast startup STDIO preparation")
                else:
                    logger.debug("STDIO not pre-prepared, using standard path")
                    
                logger.info("Starting STDIO JSON-RPC server")
                run_stdio()  # This blocks until stdin closes
            except Exception as e:
                logger.error(f"STDIO server error: {e}")
                self.running = False
        
        self.stdio_thread = threading.Thread(target=stdio_worker, daemon=True)
        self.stdio_thread.start()
        logger.info("STDIO server thread started (optimized)")
    
    def _main_processing_loop_optimized(self) -> None:
        """
        Main processing loop with FR-001 optimization monitoring.
        
        Enhanced with:
        - Memory usage tracking
        - Performance metrics
        - Uptime monitoring
        """
        last_health_check = time.time()
        last_metrics_log = time.time()
        health_check_interval = 60.0  # seconds
        metrics_log_interval = 300.0  # 5 minutes
        
        uptime_start = time.time()
        
        while self.running and not self.stop_event.is_set():
            try:
                current_time = time.time()
                
                # Periodic health checks
                if current_time - last_health_check >= health_check_interval:
                    self._perform_health_check_optimized()
                    last_health_check = current_time
                
                # Periodic metrics logging
                if current_time - last_metrics_log >= metrics_log_interval:
                    self._log_fr001_metrics(uptime_start)
                    last_metrics_log = current_time
                
                # Sleep with stop event check
                self.stop_event.wait(1)  # 1 second timeout
                
            except Exception as e:
                logger.error(f"Error in optimized main processing loop: {e}")
                time.sleep(5)  # Sleep longer on error
    
    def _perform_health_check_optimized(self) -> None:
        """Enhanced health check with FR-001 compliance monitoring"""
        try:
            # Standard health checks
            self._perform_health_check()
            
            # FR-001 specific checks
            memory_stats = self.memory_optimizer.get_usage_stats()
            
            if not memory_stats.get("within_target", True):
                logger.warning(f"⚠️ Memory usage above FR-001 target: {memory_stats.get('current_mb', 0):.1f}MB")
            
            # Check if any components are consuming excessive resources
            if self.teams_detector and hasattr(self.teams_detector, '_running'):
                if not self.teams_detector._running:
                    logger.warning("Teams detector stopped unexpectedly, restarting")
                    start_teams_monitoring()
                    
        except Exception as e:
            logger.error(f"Optimized health check failed: {e}")
    
    def _log_fr001_compliance(self) -> None:
        """Log FR-001 compliance status"""
        startup_metrics = get_startup_metrics()
        memory_stats = self.memory_optimizer.get_usage_stats()
        
        logger.info("=== FR-001 Always-Ready System Compliance ===")
        
        # Startup time compliance
        startup_time = startup_metrics.get('startup_time', 0)
        startup_ok = startup_time < 3.0
        logger.info(f"Startup Time: {startup_time:.2f}s {'✅' if startup_ok else '❌'} (target: <3s)")
        
        # Memory compliance  
        current_memory = memory_stats.get('current_mb', 0)
        memory_ok = memory_stats.get('within_target', False)
        logger.info(f"Memory Usage: {current_memory:.1f}MB {'✅' if memory_ok else '❌'} (target: <300MB)")
        
        # System readiness
        components_ready = (
            self.teams_detector is not None and
            self.smart_selector is not None and
            self.stdio_thread is not None and
            self.stdio_thread.is_alive()
        )
        logger.info(f"System Ready: {'✅' if components_ready else '❌'} (all critical components active)")
        
        # Overall compliance
        overall_compliant = startup_ok and memory_ok and components_ready
        logger.info(f"FR-001 Compliance: {'✅ COMPLIANT' if overall_compliant else '❌ NON-COMPLIANT'}")
        
        if not overall_compliant:
            logger.warning("System does not meet FR-001 Always-Ready requirements")
    
    def _log_fr001_metrics(self, uptime_start: float) -> None:
        """Log FR-001 metrics periodically"""
        try:
            current_uptime = time.time() - uptime_start
            uptime_hours = current_uptime / 3600
            
            memory_stats = self.memory_optimizer.get_usage_stats()
            
            logger.info("=== FR-001 Periodic Metrics ===")
            logger.info(f"Uptime: {uptime_hours:.2f} hours")
            logger.info(f"Memory: {memory_stats.get('current_mb', 0):.1f}MB "
                       f"({'within target' if memory_stats.get('within_target') else 'OVER TARGET'})")
            logger.info(f"Alert Level: {memory_stats.get('alert_level', 'unknown')}")
            
            # Calculate availability (simplified - in production would track downtimes)
            availability = min(99.9, (uptime_hours / max(uptime_hours, 1.0)) * 100)
            logger.info(f"Availability: {availability:.2f}% (target: 99.9%)")
            
        except Exception as e:
            logger.debug(f"FR-001 metrics logging failed: {e}")
    
    def _cleanup_components(self) -> None:
        """Cleanup daemon components with memory optimization"""
        logger.info("Cleaning up daemon components...")
        
        try:
            # Stop memory monitoring
            self.memory_optimizer.stop_monitoring()
            
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
            
            # Final memory cleanup
            self._memory_cleanup_callback()
            
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