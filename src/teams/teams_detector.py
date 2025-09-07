"""Teams Detection Module

Detects Microsoft Teams meetings automatically by monitoring:
1. Teams.exe process activity
2. Audio stream capture patterns
3. Meeting state changes

Supports both Teams app and browser-based Teams meetings.
"""

from __future__ import annotations

import time
import psutil
import threading
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

try:
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

logger = logging.getLogger(__name__)


class MeetingState(Enum):
    IDLE = "idle"
    DETECTED = "detected"  
    RECORDING = "recording"
    ENDING = "ending"


@dataclass
class MeetingDetection:
    """Information about detected Teams meeting"""
    process_name: str
    window_title: str
    pid: int
    audio_active: bool
    detection_time: float
    confidence: float  # 0.0 to 1.0


class TeamsDetector:
    """Monitors system for Teams meeting activity"""
    
    def __init__(self, poll_interval: float = 2.0):
        self.poll_interval = poll_interval
        self.state = MeetingState.IDLE
        self.current_detection: Optional[MeetingDetection] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.on_meeting_detected: Optional[Callable[[MeetingDetection], None]] = None
        self.on_meeting_ended: Optional[Callable[[MeetingDetection], None]] = None
        self.on_state_changed: Optional[Callable[[MeetingState, MeetingState], None]] = None
        
        # Detection patterns
        self.teams_process_names = {
            "Teams.exe",
            "ms-teams.exe", 
            "Teams_webkit2gtk.exe"
        }
        
        self.teams_window_patterns = {
            "Microsoft Teams",
            "Teams Meeting",
            "Meeting -",
            "Call -"
        }
        
        self.browser_meeting_patterns = {
            "Teams - Microsoft",
            "Meeting | Microsoft Teams",
            "Teams meeting"
        }

    def start_monitoring(self) -> bool:
        """Start background monitoring thread"""
        if self._running:
            return True
            
        if not HAS_WIN32:
            logger.warning("Win32 libraries not available, Teams detection limited")
            
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Teams detection monitoring started")
        return True

    def stop_monitoring(self) -> None:
        """Stop background monitoring"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info("Teams detection monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self._running:
            try:
                previous_state = self.state
                detection = self._detect_teams_meeting()
                
                if detection and self.state == MeetingState.IDLE:
                    self._transition_to_detected(detection)
                elif not detection and self.state in (MeetingState.DETECTED, MeetingState.RECORDING):
                    self._transition_to_ending()
                elif not detection and self.state == MeetingState.ENDING:
                    self._transition_to_idle()
                
                # Notify state changes
                if self.state != previous_state and self.on_state_changed:
                    self.on_state_changed(previous_state, self.state)
                    
            except Exception as e:
                logger.error(f"Error in Teams detection loop: {e}")
                
            time.sleep(self.poll_interval)

    def _detect_teams_meeting(self) -> Optional[MeetingDetection]:
        """Detect if Teams meeting is currently active"""
        
        # Method 1: Direct Teams process detection
        teams_detection = self._detect_teams_process()
        if teams_detection:
            return teams_detection
            
        # Method 2: Browser-based Teams detection
        browser_detection = self._detect_browser_teams()
        if browser_detection:
            return browser_detection
            
        return None

    def _detect_teams_process(self) -> Optional[MeetingDetection]:
        """Detect Teams via native app process"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] in self.teams_process_names:
                        # Found Teams process, check if in meeting
                        window_title = self._get_window_title_for_pid(proc.info['pid'])
                        
                        if self._is_meeting_window(window_title):
                            audio_active = self._check_audio_activity(proc.info['pid'])
                            
                            confidence = 0.9 if audio_active else 0.7
                            
                            return MeetingDetection(
                                process_name=proc.info['name'],
                                window_title=window_title or "Teams",
                                pid=proc.info['pid'],
                                audio_active=audio_active,
                                detection_time=time.time(),
                                confidence=confidence
                            )
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Error detecting Teams process: {e}")
            
        return None

    def _detect_browser_teams(self) -> Optional[MeetingDetection]:
        """Detect Teams meeting in browser"""
        if not HAS_WIN32:
            return None
            
        try:
            browser_processes = self._get_browser_processes()
            
            for proc_info in browser_processes:
                window_title = self._get_window_title_for_pid(proc_info['pid'])
                
                if self._is_browser_meeting_window(window_title):
                    audio_active = self._check_audio_activity(proc_info['pid'])
                    
                    confidence = 0.8 if audio_active else 0.6
                    
                    return MeetingDetection(
                        process_name=f"{proc_info['name']} (browser)",
                        window_title=window_title or "Teams (Browser)",
                        pid=proc_info['pid'],
                        audio_active=audio_active,
                        detection_time=time.time(),
                        confidence=confidence
                    )
                    
        except Exception as e:
            logger.error(f"Error detecting browser Teams: {e}")
            
        return None

    def _get_browser_processes(self) -> list[Dict[str, Any]]:
        """Get list of browser processes"""
        browser_names = {
            "chrome.exe", "msedge.exe", "firefox.exe", 
            "brave.exe", "opera.exe", "vivaldi.exe"
        }
        
        browsers = []
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] in browser_names:
                    browsers.append(proc.info)
        except Exception:
            pass
            
        return browsers

    def _get_window_title_for_pid(self, pid: int) -> Optional[str]:
        """Get window title for given process ID"""
        if not HAS_WIN32:
            return None
            
        try:
            def enum_windows_callback(hwnd, titles):
                if win32gui.IsWindowVisible(hwnd):
                    _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if window_pid == pid:
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            titles.append(title)
                return True
            
            titles = []
            win32gui.EnumWindows(enum_windows_callback, titles)
            
            # Return most relevant title
            for title in titles:
                if any(pattern in title for pattern in 
                      self.teams_window_patterns.union(self.browser_meeting_patterns)):
                    return title
                    
            return titles[0] if titles else None
            
        except Exception as e:
            logger.debug(f"Could not get window title for PID {pid}: {e}")
            return None

    def _is_meeting_window(self, window_title: Optional[str]) -> bool:
        """Check if window title indicates Teams meeting"""
        if not window_title:
            return False
            
        return any(pattern in window_title for pattern in self.teams_window_patterns)

    def _is_browser_meeting_window(self, window_title: Optional[str]) -> bool:
        """Check if browser window title indicates Teams meeting"""
        if not window_title:
            return False
            
        return any(pattern in window_title for pattern in self.browser_meeting_patterns)

    def _check_audio_activity(self, pid: int) -> bool:
        """Check if process has active audio streams"""
        try:
            # Simple heuristic: check if process has audio-related handles
            # More sophisticated implementation would use Windows Audio APIs
            proc = psutil.Process(pid)
            
            # Check CPU usage as proxy for audio processing
            cpu_percent = proc.cpu_percent(interval=0.1)
            return cpu_percent > 1.0  # Active processing threshold
            
        except Exception:
            return False

    def _transition_to_detected(self, detection: MeetingDetection) -> None:
        """Transition to DETECTED state"""
        self.state = MeetingState.DETECTED
        self.current_detection = detection
        
        logger.info(f"Teams meeting detected: {detection.window_title} (confidence: {detection.confidence:.2f})")
        
        if self.on_meeting_detected:
            self.on_meeting_detected(detection)

    def _transition_to_ending(self) -> None:
        """Transition to ENDING state"""
        self.state = MeetingState.ENDING
        logger.info("Teams meeting ending detected")

    def _transition_to_idle(self) -> None:
        """Transition to IDLE state"""
        previous_detection = self.current_detection
        self.state = MeetingState.IDLE
        self.current_detection = None
        
        logger.info("Teams meeting ended")
        
        if previous_detection and self.on_meeting_ended:
            self.on_meeting_ended(previous_detection)

    def get_current_state(self) -> Dict[str, Any]:
        """Get current detector state"""
        return {
            "state": self.state.value,
            "detection": {
                "process_name": self.current_detection.process_name,
                "window_title": self.current_detection.window_title,
                "pid": self.current_detection.pid,
                "audio_active": self.current_detection.audio_active,
                "detection_time": self.current_detection.detection_time,
                "confidence": self.current_detection.confidence
            } if self.current_detection else None,
            "monitoring": self._running
        }

    def force_detection(self, process_name: str = "Manual", window_title: str = "Manual Trigger") -> None:
        """Force a detection event (for testing)"""
        detection = MeetingDetection(
            process_name=process_name,
            window_title=window_title,
            pid=0,
            audio_active=True,
            detection_time=time.time(),
            confidence=1.0
        )
        self._transition_to_detected(detection)


# Global detector instance
_detector_instance: Optional[TeamsDetector] = None


def get_detector() -> TeamsDetector:
    """Get global Teams detector instance"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = TeamsDetector()
    return _detector_instance


def start_teams_monitoring() -> bool:
    """Start global Teams monitoring"""
    return get_detector().start_monitoring()


def stop_teams_monitoring() -> None:
    """Stop global Teams monitoring"""
    if _detector_instance:
        _detector_instance.stop_monitoring()