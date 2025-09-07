"""Fast Startup Optimization Module

Implements FR-001 requirement for <3s response time through:
1. Lazy loading strategies
2. Parallel component initialization  
3. Precompiled module caching
4. Critical path optimization
"""

from __future__ import annotations

import time
import threading
import concurrent.futures
from typing import Dict, Any, Optional, Callable
import logging
from pathlib import Path
import sys

logger = logging.getLogger(__name__)


class FastStartupManager:
    """Manages fast startup optimizations for always-ready system"""
    
    def __init__(self):
        self.startup_time = 0.0
        self.component_timings: Dict[str, float] = {}
        self.preload_cache: Dict[str, Any] = {}
        self.initialization_futures: Dict[str, concurrent.futures.Future] = {}
        
        # Target times per FR-001
        self.target_total_time = 3.0  # seconds
        self.target_critical_path = 1.5  # seconds for critical components
        
    def optimized_startup(self) -> bool:
        """
        Execute optimized startup sequence targeting <3s total time.
        
        Returns:
            bool: True if startup completed within target time
        """
        start_time = time.time()
        logger.info("Starting optimized startup sequence (target: <3s)")
        
        try:
            # Phase 1: Critical path components (parallel) - Target <1.5s
            self._initialize_critical_path()
            
            # Phase 2: Background components (async) - Overlap with Phase 1
            self._initialize_background_components()
            
            # Phase 3: Wait for critical components only
            self._wait_for_critical_components()
            
            total_time = time.time() - start_time
            self.startup_time = total_time
            
            success = total_time < self.target_total_time
            
            if success:
                logger.success(f"✅ Fast startup completed in {total_time:.2f}s (target: <3s)")
            else:
                logger.warning(f"⚠️ Startup took {total_time:.2f}s (exceeded 3s target)")
                
            self._log_component_timings()
            return success
            
        except Exception as e:
            logger.error(f"Fast startup failed: {e}")
            return False
    
    def _initialize_critical_path(self) -> None:
        """Initialize critical components in parallel for fastest response time"""
        logger.debug("Phase 1: Initializing critical path components")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Critical component futures
            futures = {
                'system_setup': executor.submit(self._setup_system_fast),
                'stdio_server': executor.submit(self._prepare_stdio_server),
                'device_manager': executor.submit(self._initialize_device_manager_fast),
                'config_validation': executor.submit(self._validate_config_fast)
            }
            
            # Store futures for later waiting
            self.initialization_futures.update(futures)
            
            # Log when each critical component starts
            for name, future in futures.items():
                logger.debug(f"Started critical component: {name}")
    
    def _initialize_background_components(self) -> None:
        """Initialize non-critical components in background"""
        logger.debug("Phase 2: Starting background component initialization")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Background component futures (don't block startup)
            background_futures = {
                'teams_detector': executor.submit(self._initialize_teams_detector_lazy),
                'smart_selector': executor.submit(self._initialize_smart_selector_lazy),
                'advanced_components': executor.submit(self._initialize_advanced_components_lazy)
            }
            
            # Store for cleanup, but don't wait for these
            self.initialization_futures.update(background_futures)
    
    def _wait_for_critical_components(self) -> None:
        """Wait only for critical path components with timeout"""
        logger.debug("Phase 3: Waiting for critical components")
        
        critical_components = ['system_setup', 'stdio_server', 'device_manager', 'config_validation']
        
        for name in critical_components:
            if name in self.initialization_futures:
                try:
                    future = self.initialization_futures[name]
                    result = future.result(timeout=2.0)  # 2s timeout per component
                    
                    if result:
                        logger.debug(f"✅ {name} initialized successfully")
                    else:
                        logger.warning(f"⚠️ {name} initialization returned false")
                        
                except concurrent.futures.TimeoutError:
                    logger.error(f"❌ {name} initialization timed out (>2s)")
                except Exception as e:
                    logger.error(f"❌ {name} initialization failed: {e}")
    
    def _setup_system_fast(self) -> bool:
        """Fast system setup with caching and minimal I/O"""
        component_start = time.time()
        
        try:
            # Skip heavy operations on subsequent startups
            if 'system_setup' in self.preload_cache:
                logger.debug("Using cached system setup")
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
            import sys
            
            # Cache imports
            self.preload_cache['stdio_imports'] = {'json': json, 'sys': sys}
            
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
                logger.debug("Device manager import successful")
                
                self.preload_cache['device_manager'] = DeviceManager
                
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
            
            # Basic validation only
            required_dirs = [
                settings.storage_dir,
                settings.recordings_dir,
                settings.transcriptions_dir
            ]
            
            for dir_path in required_dirs:
                if not dir_path.exists():
                    logger.debug(f"Creating missing directory: {dir_path}")
                    dir_path.mkdir(parents=True, exist_ok=True)
            
            elapsed = time.time() - component_start
            self.component_timings['config_validation'] = elapsed
            
            logger.debug(f"Config validated in {elapsed:.3f}s")
            return True
            
        except Exception as e:
            logger.error(f"Fast config validation failed: {e}")
            return False
    
    def _initialize_teams_detector_lazy(self) -> bool:
        """Lazy initialization of Teams detector (background)"""
        component_start = time.time()
        
        try:
            # Import without starting monitoring
            from src.teams import get_detector
            
            detector = get_detector()
            # Don't start monitoring yet - that's expensive
            
            self.preload_cache['teams_detector'] = detector
            
            elapsed = time.time() - component_start
            self.component_timings['teams_detector'] = elapsed
            
            logger.debug(f"Teams detector initialized lazily in {elapsed:.3f}s")
            return True
            
        except Exception as e:
            logger.debug(f"Teams detector lazy init failed: {e}")
            return False
    
    def _initialize_smart_selector_lazy(self) -> bool:
        """Lazy initialization of smart device selector (background)"""
        component_start = time.time()
        
        try:
            from src.audio import get_smart_selector
            
            selector = get_smart_selector()
            # Don't load preferences or scan devices yet
            
            self.preload_cache['smart_selector'] = selector
            
            elapsed = time.time() - component_start
            self.component_timings['smart_selector'] = elapsed
            
            logger.debug(f"Smart selector initialized lazily in {elapsed:.3f}s")
            return True
            
        except Exception as e:
            logger.debug(f"Smart selector lazy init failed: {e}")
            return False
    
    def _initialize_advanced_components_lazy(self) -> bool:
        """Lazy initialization of advanced/optional components (background)"""
        component_start = time.time()
        
        try:
            # Try to import optional advanced components without initializing
            try:
                from daemon.resource_manager import ResourceManager
                self.preload_cache['resource_manager'] = ResourceManager
            except ImportError:
                pass
                
            try:
                from daemon.health_monitor import HealthMonitor
                self.preload_cache['health_monitor'] = HealthMonitor
            except ImportError:
                pass
            
            elapsed = time.time() - component_start
            self.component_timings['advanced_components'] = elapsed
            
            logger.debug(f"Advanced components checked in {elapsed:.3f}s")
            return True
            
        except Exception as e:
            logger.debug(f"Advanced components check failed: {e}")
            return False
    
    def _log_component_timings(self) -> None:
        """Log detailed timing breakdown for optimization"""
        logger.info("Startup timing breakdown:")
        
        total_measured = 0.0
        for component, timing in self.component_timings.items():
            logger.info(f"  {component}: {timing:.3f}s")
            total_measured += timing
            
        logger.info(f"Total startup time: {self.startup_time:.3f}s")
        logger.info(f"Measured components: {total_measured:.3f}s")
        
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
        """Get a cached component from preload cache"""
        return self.preload_cache.get(component_name)
    
    def is_startup_complete(self) -> bool:
        """Check if startup is complete within target time"""
        return 0 < self.startup_time < self.target_total_time
    
    def get_startup_metrics(self) -> Dict[str, Any]:
        """Get startup performance metrics"""
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
    """Execute optimized startup sequence"""
    return get_startup_manager().optimized_startup()


def get_startup_metrics() -> Dict[str, Any]:
    """Get current startup performance metrics"""
    return get_startup_manager().get_startup_metrics()


def get_cached_component(component_name: str) -> Optional[Any]:
    """Get a cached component from fast startup"""
    return get_startup_manager().get_cached_component(component_name)