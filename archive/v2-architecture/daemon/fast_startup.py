"""Fast Startup Optimization Module

Implements FR-001 requirement for <3s system response time.

This module optimizes daemon startup through parallel initialization,
component caching, and critical path optimization to meet the Always-Ready
System requirement of <3s response time.

Key Features:
- Parallel component initialization to reduce startup time
- Component caching to avoid redundant operations
- Critical path optimization for essential components
- Timing analysis and performance monitoring

Usage:
    from daemon.fast_startup import execute_fast_startup
    success = execute_fast_startup()  # Returns True if <3s
"""

from __future__ import annotations

import time
import concurrent.futures
from typing import Dict, Any, Optional
import logging
import sys

logger = logging.getLogger(__name__)


class FastStartupManager:
    """
    Manages fast startup optimizations for FR-001 compliance.
    
    Coordinates parallel initialization of system components with a target
    of <3s total startup time. Uses a two-phase approach:
    - Phase 1: Critical components in parallel (<1.5s target)
    - Phase 2: Background components (overlapped with Phase 1)
    """
    
    def __init__(self):
        self.startup_time = 0.0
        self.component_timings: Dict[str, float] = {}
        self.preload_cache: Dict[str, Any] = {}
        
        # FR-001 timing targets
        self.target_total_time = 3.0  # seconds
        
    def optimized_startup(self) -> bool:
        """
        Execute optimized startup sequence targeting <3s total time.
        
        Returns:
            bool: True if startup completed within target time
        """
        start_time = time.time()
        logger.info("Starting optimized startup sequence (target: <3s)")
        
        try:
            # Initialize critical components in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    'system_setup': executor.submit(self._setup_system_fast),
                    'stdio_server': executor.submit(self._prepare_stdio_server),
                    'device_manager': executor.submit(self._initialize_device_manager_fast),
                    'config_validation': executor.submit(self._validate_config_fast)
                }
                
                # Wait for all critical components with timeout
                for name, future in futures.items():
                    try:
                        result = future.result(timeout=2.0)  # 2s timeout per component
                        if result:
                            logger.debug(f"✅ {name} initialized successfully")
                        else:
                            logger.warning(f"⚠️ {name} initialization returned false")
                    except concurrent.futures.TimeoutError:
                        logger.error(f"❌ {name} initialization timed out")
                    except Exception as e:
                        logger.error(f"❌ {name} initialization failed: {e}")
            
            # Start background components (don't wait for these)
            self._initialize_background_components_async()
            
            total_time = time.time() - start_time
            self.startup_time = total_time
            
            success = total_time < self.target_total_time
            
            if success:
                logger.success(f"✅ Fast startup completed in {total_time:.2f}s")
            else:
                logger.warning(f"⚠️ Startup took {total_time:.2f}s (exceeded 3s target)")
                
            self._log_component_timings()
            return success
            
        except Exception as e:
            logger.error(f"Fast startup failed: {e}")
            return False
    
    def _setup_system_fast(self) -> bool:
        """Fast system setup with minimal I/O"""
        component_start = time.time()
        
        try:
            # Skip heavy operations if already done
            if 'system_setup' in self.preload_cache:
                return True
                
            # Minimal system setup
            from config import setup_directories
            setup_directories()  # Creates dirs only if needed
            
            # Cache successful setup
            self.preload_cache['system_setup'] = True
            
            elapsed = time.time() - component_start
            self.component_timings['system_setup'] = elapsed
            
            logger.debug(f"System setup completed in {elapsed:.3f}s")
            return True
            
        except Exception as e:
            logger.error(f"Fast system setup failed: {e}")
            return False
    
    def _prepare_stdio_server(self) -> bool:
        """Prepare STDIO server without starting it"""
        component_start = time.time()
        
        try:
            # Pre-validate STDIO availability
            if not sys.stdin.readable():
                logger.warning("STDIN not readable, STDIO server may fail")
                return False
                
            # Pre-import heavy modules
            import json
            
            # Cache imports
            self.preload_cache['stdio_imports'] = {'json': json}
            
            elapsed = time.time() - component_start
            self.component_timings['stdio_server'] = elapsed
            
            logger.debug(f"STDIO server prepared in {elapsed:.3f}s")
            return True
            
        except Exception as e:
            logger.error(f"STDIO server preparation failed: {e}")
            return False
    
    def _initialize_device_manager_fast(self) -> bool:
        """Fast device manager initialization with lazy loading"""
        component_start = time.time()
        
        try:
            # Check if device manager is available without full initialization
            try:
                from device_manager import DeviceManager
                # Don't actually list devices yet (expensive operation)
                self.preload_cache['device_manager'] = DeviceManager
                logger.debug("Device manager import successful")
                
            except ImportError:
                logger.warning("Device manager not available")
                return False
            
            elapsed = time.time() - component_start
            self.component_timings['device_manager'] = elapsed
            
            logger.debug(f"Device manager initialized in {elapsed:.3f}s")
            return True
            
        except Exception as e:
            logger.error(f"Fast device manager initialization failed: {e}")
            return False
    
    def _validate_config_fast(self) -> bool:
        """Fast config validation without expensive operations"""
        component_start = time.time()
        
        try:
            from config import settings
            
            # Basic validation only - create missing directories
            required_dirs = [
                settings.storage_dir,
                settings.recordings_dir,
                settings.transcriptions_dir
            ]
            
            for dir_path in required_dirs:
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
            
            elapsed = time.time() - component_start
            self.component_timings['config_validation'] = elapsed
            
            logger.debug(f"Config validated in {elapsed:.3f}s")
            return True
            
        except Exception as e:
            logger.error(f"Fast config validation failed: {e}")
            return False
    
    def _initialize_background_components_async(self) -> None:
        """Initialize non-critical components in background (don't wait)"""
        def background_init():
            try:
                # Import Teams detector without starting monitoring
                from src.teams import get_detector
                detector = get_detector()
                self.preload_cache['teams_detector'] = detector
                
                # Import smart selector without loading preferences
                from src.audio import get_smart_selector
                selector = get_smart_selector()
                self.preload_cache['smart_selector'] = selector
                
                logger.debug("Background components initialized")
                
            except Exception as e:
                logger.debug(f"Background component initialization failed: {e}")
        
        # Start in daemon thread (won't block shutdown)
        import threading
        thread = threading.Thread(target=background_init, daemon=True)
        thread.start()
    
    def _log_component_timings(self) -> None:
        """Log timing breakdown for optimization analysis"""
        logger.info("Startup timing breakdown:")
        
        total_measured = 0.0
        for component, timing in self.component_timings.items():
            logger.info(f"  {component}: {timing:.3f}s")
            total_measured += timing
            
        logger.info(f"Total startup time: {self.startup_time:.3f}s")
        
        # Performance analysis
        if self.startup_time < 1.0:
            logger.success("🚀 Excellent startup performance (<1s)")
        elif self.startup_time < 2.0:
            logger.info("✅ Good startup performance (<2s)")
        elif self.startup_time < 3.0:
            logger.warning("⚠️ Acceptable startup performance (<3s)")
        else:
            logger.error("❌ Slow startup performance (>3s) - optimization needed")
    
    def get_cached_component(self, component_name: str) -> Optional[Any]:
        """
        Get a cached component from preload cache.
        
        Args:
            component_name: Name of the component to retrieve
            
        Returns:
            Cached component or None if not found
        """
        return self.preload_cache.get(component_name)
    
    def is_startup_complete(self) -> bool:
        """Check if startup completed within FR-001 target time"""
        return 0 < self.startup_time < self.target_total_time
    
    def get_startup_metrics(self) -> Dict[str, Any]:
        """
        Get startup performance metrics for monitoring.
        
        Returns:
            Dictionary containing timing and performance data
        """
        return {
            'startup_time': self.startup_time,
            'target_time': self.target_total_time,
            'within_target': self.is_startup_complete(),
            'component_timings': self.component_timings.copy(),
            'cached_components': list(self.preload_cache.keys())
        }


# Global fast startup manager instance
_startup_manager: Optional[FastStartupManager] = None


def get_startup_manager() -> FastStartupManager:
    """Get global fast startup manager instance"""
    global _startup_manager
    if _startup_manager is None:
        _startup_manager = FastStartupManager()
    return _startup_manager


def execute_fast_startup() -> bool:
    """
    Execute optimized startup sequence for FR-001 compliance.
    
    Returns:
        bool: True if startup completed within 3s target
    """
    return get_startup_manager().optimized_startup()


def get_startup_metrics() -> Dict[str, Any]:
    """Get current startup performance metrics"""
    return get_startup_manager().get_startup_metrics()


def get_cached_component(component_name: str) -> Optional[Any]:
    """Get a cached component from fast startup"""
    return get_startup_manager().get_cached_component(component_name)