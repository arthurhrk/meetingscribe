"""Memory Optimization Module

Implements FR-001 requirement for <300MB RAM in idle state.

This module provides real-time memory monitoring, automated cleanup,
and optimization strategies to maintain the Always-Ready System
requirement of <300MB memory usage in idle state.

Key Features:
- Real-time memory monitoring with alert system
- Automatic cleanup callbacks for memory pressure
- Progressive alert levels with appropriate responses
- Garbage collection optimization for daemon processes
- Memory usage history and analytics

Usage:
    from daemon.memory_optimizer import start_memory_monitoring, is_memory_within_target
    
    # Start monitoring with 30-second intervals
    start_memory_monitoring(interval=30.0)
    
    # Check compliance
    if is_memory_within_target():
        print("Memory usage within FR-001 target")
"""

from __future__ import annotations

import gc
import time
import threading
import weakref
from typing import Dict, Any, Optional, List, Callable
import logging
from dataclasses import dataclass
from enum import Enum

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)


class MemoryAlert(Enum):
    """Memory usage alert levels for FR-001 compliance monitoring"""
    NORMAL = "normal"      # <200MB - optimal range
    WARNING = "warning"    # 200-300MB - approaching target
    CRITICAL = "critical"  # 300-400MB - over FR-001 target
    EMERGENCY = "emergency"  # >400MB - requires immediate action


@dataclass
class MemoryUsage:
    """
    Memory usage statistics snapshot.
    
    Attributes:
        rss_mb: Resident Set Size in MB (actual physical memory used)
        vms_mb: Virtual Memory Size in MB (total virtual memory)
        percent: Percentage of total system memory used
        alert_level: Current alert level based on FR-001 targets
        timestamp: Unix timestamp when measurement was taken
    """
    rss_mb: float
    vms_mb: float
    percent: float
    alert_level: MemoryAlert
    timestamp: float
    
    def is_within_target(self, target_mb: float = 300.0) -> bool:
        """Check if memory usage is within FR-001 target"""
        return self.rss_mb <= target_mb


class MemoryOptimizer:
    """
    Optimizes memory usage for FR-001 Always-Ready System compliance.
    
    Monitors memory usage in real-time and triggers cleanup procedures
    when usage exceeds target thresholds. Uses a multi-level alert system
    to provide appropriate responses based on memory pressure severity.
    """
    
    def __init__(self, target_idle_mb: float = 300.0):
        """
        Initialize memory optimizer.
        
        Args:
            target_idle_mb: FR-001 target memory usage in MB (default 300)
        """
        self.target_idle_mb = target_idle_mb
        self.monitoring_enabled = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Monitoring state
        self.current_usage: Optional[MemoryUsage] = None
        self.usage_history: List[MemoryUsage] = []
        self.max_history_items = 100
        
        # Cleanup callbacks for memory pressure
        self.cleanup_callbacks: List[Callable[[], None]] = []
        
        # Alert callbacks for different severity levels
        self.alert_callbacks: Dict[MemoryAlert, List[Callable[[MemoryUsage], None]]] = {
            level: [] for level in MemoryAlert
        }
        
        # Setup garbage collection optimization
        self._setup_gc_optimization()
    
    def start_monitoring(self, interval: float = 30.0) -> bool:
        """
        Start memory monitoring thread.
        
        Args:
            interval: Monitoring interval in seconds
            
        Returns:
            bool: True if monitoring started successfully
        """
        if not HAS_PSUTIL:
            logger.warning("psutil not available, memory monitoring disabled")
            return False
            
        if self.monitoring_enabled:
            logger.debug("Memory monitoring already running")
            return True
            
        try:
            self.monitoring_enabled = True
            self.stop_event.clear()
            
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                args=(interval,),
                daemon=True,
                name="MemoryMonitor"
            )
            self.monitoring_thread.start()
            
            logger.info(f"Memory monitoring started (target: <{self.target_idle_mb}MB)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start memory monitoring: {e}")
            self.monitoring_enabled = False
            return False
    
    def stop_monitoring(self) -> None:
        """Stop memory monitoring thread gracefully"""
        if not self.monitoring_enabled:
            return
            
        self.monitoring_enabled = False
        self.stop_event.set()
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)
            
        logger.info("Memory monitoring stopped")
    
    def get_current_usage(self) -> Optional[MemoryUsage]:
        """
        Get current memory usage statistics.
        
        Returns:
            MemoryUsage object or None if psutil not available
        """
        if not HAS_PSUTIL:
            return None
            
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            rss_mb = memory_info.rss / (1024 * 1024)
            vms_mb = memory_info.vms / (1024 * 1024)
            
            alert_level = self._calculate_alert_level(rss_mb)
            
            usage = MemoryUsage(
                rss_mb=rss_mb,
                vms_mb=vms_mb,
                percent=memory_percent,
                alert_level=alert_level,
                timestamp=time.time()
            )
            
            self.current_usage = usage
            return usage
            
        except Exception as e:
            logger.error(f"Failed to get memory usage: {e}")
            return None
    
    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a cleanup callback for memory pressure situations.
        
        Args:
            callback: Function to call when memory cleanup is needed
        """
        self.cleanup_callbacks.append(callback)
        logger.debug(f"Registered memory cleanup callback")
    
    def register_alert_callback(self, level: MemoryAlert, callback: Callable[[MemoryUsage], None]) -> None:
        """
        Register an alert callback for specific memory alert level.
        
        Args:
            level: Memory alert level to respond to
            callback: Function to call when alert level is reached
        """
        self.alert_callbacks[level].append(callback)
        logger.debug(f"Registered {level.value} alert callback")
    
    def is_within_target(self) -> bool:
        """Check if current memory usage is within FR-001 target"""
        if not self.current_usage:
            return True  # Assume OK if no data available
        return self.current_usage.is_within_target(self.target_idle_mb)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive memory usage statistics.
        
        Returns:
            Dictionary with current usage, compliance status, and configuration
        """
        if not self.current_usage:
            return {"error": "No usage data available"}
            
        return {
            "current_mb": self.current_usage.rss_mb,
            "target_mb": self.target_idle_mb,
            "within_target": self.is_within_target(),
            "alert_level": self.current_usage.alert_level.value,
            "virtual_mb": self.current_usage.vms_mb,
            "percent_of_system": self.current_usage.percent,
            "monitoring_enabled": self.monitoring_enabled,
            "cleanup_callbacks": len(self.cleanup_callbacks)
        }
    
    def _monitoring_loop(self, interval: float) -> None:
        """Main memory monitoring loop (runs in separate thread)"""
        logger.debug("Memory monitoring loop started")
        
        while self.monitoring_enabled and not self.stop_event.is_set():
            try:
                usage = self.get_current_usage()
                if usage:
                    self._process_usage_measurement(usage)
                    
                # Sleep with stop event check
                self.stop_event.wait(interval)
                
            except Exception as e:
                logger.error(f"Error in memory monitoring loop: {e}")
                self.stop_event.wait(10.0)  # Longer sleep on error
    
    def _process_usage_measurement(self, usage: MemoryUsage) -> None:
        """Process a memory usage measurement and trigger appropriate responses"""
        # Add to history
        self.usage_history.append(usage)
        if len(self.usage_history) > self.max_history_items:
            self.usage_history.pop(0)
        
        # Check for alert level changes
        previous_level = (self.usage_history[-2].alert_level 
                         if len(self.usage_history) >= 2 
                         else MemoryAlert.NORMAL)
        
        if usage.alert_level != previous_level:
            self._trigger_alert(usage)
        
        # Log usage based on alert level
        if usage.alert_level == MemoryAlert.NORMAL:
            logger.debug(f"Memory usage: {usage.rss_mb:.1f}MB (normal)")
        elif usage.alert_level == MemoryAlert.WARNING:
            logger.warning(f"Memory usage: {usage.rss_mb:.1f}MB (approaching FR-001 limit)")
        elif usage.alert_level == MemoryAlert.CRITICAL:
            logger.error(f"Memory usage: {usage.rss_mb:.1f}MB (over FR-001 target)")
            self._trigger_memory_cleanup()
        elif usage.alert_level == MemoryAlert.EMERGENCY:
            logger.critical(f"Memory usage: {usage.rss_mb:.1f}MB (emergency)")
            self._trigger_emergency_cleanup()
    
    def _calculate_alert_level(self, rss_mb: float) -> MemoryAlert:
        """Calculate appropriate alert level based on memory usage"""
        if rss_mb < 200:
            return MemoryAlert.NORMAL
        elif rss_mb < self.target_idle_mb:  # <300MB
            return MemoryAlert.WARNING
        elif rss_mb < 400:
            return MemoryAlert.CRITICAL
        else:
            return MemoryAlert.EMERGENCY
    
    def _trigger_alert(self, usage: MemoryUsage) -> None:
        """Trigger alert callbacks for memory usage level"""
        callbacks = self.alert_callbacks.get(usage.alert_level, [])
        
        for callback in callbacks:
            try:
                callback(usage)
            except Exception as e:
                logger.error(f"Memory alert callback failed: {e}")
    
    def _trigger_memory_cleanup(self) -> None:
        """Trigger memory cleanup procedures for CRITICAL alert level"""
        logger.info("Triggering memory cleanup procedures")
        
        cleanup_performed = False
        
        # Run registered cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
                cleanup_performed = True
                logger.debug("Cleanup callback executed")
            except Exception as e:
                logger.error(f"Cleanup callback failed: {e}")
        
        # Force garbage collection
        self._force_gc()
        cleanup_performed = True
        
        if cleanup_performed:
            # Check if cleanup was effective
            time.sleep(1.0)  # Allow cleanup to take effect
            new_usage = self.get_current_usage()
            if new_usage and new_usage.rss_mb < self.target_idle_mb:
                logger.info(f"✅ Memory cleanup successful: {new_usage.rss_mb:.1f}MB")
            else:
                logger.warning("⚠️ Memory cleanup had limited effect")
    
    def _trigger_emergency_cleanup(self) -> None:
        """Trigger emergency memory cleanup for EMERGENCY alert level"""
        logger.critical("Triggering emergency memory cleanup")
        
        # Run normal cleanup first
        self._trigger_memory_cleanup()
        
        # Additional emergency measures
        try:
            # Force multiple GC cycles
            for _ in range(3):
                self._force_gc()
                time.sleep(0.1)
                
            logger.info("Emergency memory cleanup completed")
            
        except Exception as e:
            logger.error(f"Emergency cleanup failed: {e}")
    
    def _force_gc(self) -> None:
        """Force garbage collection and log results"""
        before = gc.get_count()
        collected = gc.collect()
        after = gc.get_count()
        
        logger.debug(f"Garbage collection: collected {collected} objects")
    
    def _setup_gc_optimization(self) -> None:
        """Setup garbage collection optimization for daemon usage pattern"""
        # Tune GC thresholds for long-running daemon process
        # More frequent generation 0 collection, standard for others
        gc.set_threshold(700, 10, 10)
        
        # Enable GC debugging in development mode only
        if logger.level <= logging.DEBUG:
            gc.set_debug(gc.DEBUG_STATS)


# Global memory optimizer instance
_memory_optimizer: Optional[MemoryOptimizer] = None


def get_memory_optimizer() -> MemoryOptimizer:
    """Get global memory optimizer instance"""
    global _memory_optimizer
    if _memory_optimizer is None:
        _memory_optimizer = MemoryOptimizer()
    return _memory_optimizer


def start_memory_monitoring(interval: float = 30.0) -> bool:
    """
    Start memory monitoring for FR-001 compliance.
    
    Args:
        interval: Monitoring interval in seconds
        
    Returns:
        bool: True if monitoring started successfully
    """
    return get_memory_optimizer().start_monitoring(interval)


def stop_memory_monitoring() -> None:
    """Stop memory monitoring"""
    get_memory_optimizer().stop_monitoring()


def get_current_memory_usage() -> Optional[MemoryUsage]:
    """Get current memory usage statistics"""
    return get_memory_optimizer().get_current_usage()


def is_memory_within_target() -> bool:
    """Check if memory usage is within FR-001 target (<300MB)"""
    return get_memory_optimizer().is_within_target()


def register_memory_cleanup_callback(callback: Callable[[], None]) -> None:
    """Register a callback for memory cleanup situations"""
    get_memory_optimizer().register_cleanup_callback(callback)


def get_memory_stats() -> Dict[str, Any]:
    """Get comprehensive memory usage statistics"""
    return get_memory_optimizer().get_usage_stats()