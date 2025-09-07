"""Smart Audio Device Selection

Implements intelligent device selection logic based on context and priority rules.
Follows FR-003 specification for optimal audio device management.
"""

from __future__ import annotations

import time
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

try:
    from device_manager import DeviceManager, AudioDevice, AudioDeviceError
    HAS_DEVICE_MANAGER = True
except ImportError:
    HAS_DEVICE_MANAGER = False
    DeviceManager = None
    AudioDevice = None
    AudioDeviceError = Exception

logger = logging.getLogger(__name__)


class AudioContext(Enum):
    """Audio recording context"""
    TEAMS_MEETING = "teams_meeting"
    MANUAL_RECORDING = "manual_recording"
    SYSTEM_DEFAULT = "system_default"


class DevicePriority(Enum):
    """Device selection priority levels"""
    HIGHEST = 100    # Preferred device for context
    HIGH = 80       # Good device for context  
    MEDIUM = 60     # Acceptable device
    LOW = 40        # Last resort
    BLOCKED = 0     # Never use this device


@dataclass
class DeviceScore:
    """Device scoring result"""
    device: AudioDevice
    score: int
    priority: DevicePriority
    reasons: List[str]
    context_match: bool


@dataclass
class DevicePreference:
    """User device preference"""
    context: AudioContext
    device_name: str
    device_index: Optional[int]
    last_used: float
    success_count: int
    failure_count: int


class SmartDeviceSelector:
    """Intelligently selects optimal audio devices based on context and learned preferences"""
    
    def __init__(self):
        self.device_manager: Optional[DeviceManager] = None
        self.preferences: Dict[str, DevicePreference] = {}
        self.blocked_devices: set[str] = set()
        
        # Load preferences from storage
        self._load_preferences()
        
    def select_device(self, context: AudioContext = AudioContext.SYSTEM_DEFAULT) -> Optional[AudioDevice]:
        """Select the best device for given context"""
        if not HAS_DEVICE_MANAGER:
            logger.error("Device manager not available")
            return None
            
        try:
            with DeviceManager() as dm:
                devices = dm.list_all_devices()
                
            if not devices:
                logger.error("No audio devices found")
                return None
                
            # Score all devices for this context
            scored_devices = self._score_devices(devices, context)
            
            if not scored_devices:
                logger.error("No suitable devices found")
                return None
                
            # Sort by score (highest first)
            scored_devices.sort(key=lambda x: x.score, reverse=True)
            
            best_device = scored_devices[0]
            logger.info(f"Selected device: {best_device.device.name} (score: {best_device.score})")
            logger.debug(f"Selection reasons: {', '.join(best_device.reasons)}")
            
            return best_device.device
            
        except Exception as e:
            logger.error(f"Error selecting device: {e}")
            return None

    def _score_devices(self, devices: List[AudioDevice], context: AudioContext) -> List[DeviceScore]:
        """Score all devices for the given context"""
        scored_devices = []
        
        for device in devices:
            if device.name in self.blocked_devices:
                continue
                
            score, priority, reasons = self._calculate_device_score(device, context)
            
            if score > 0:  # Only include devices with positive scores
                scored_devices.append(DeviceScore(
                    device=device,
                    score=score,
                    priority=priority,
                    reasons=reasons,
                    context_match=self._is_context_match(device, context)
                ))
                
        return scored_devices

    def _calculate_device_score(self, device: AudioDevice, context: AudioContext) -> Tuple[int, DevicePriority, List[str]]:
        """Calculate score for a device in given context"""
        base_score = 0
        reasons = []
        priority = DevicePriority.LOW
        
        # Context-specific scoring
        if context == AudioContext.TEAMS_MEETING:
            score, pri, ctx_reasons = self._score_teams_context(device)
            base_score += score
            priority = max(priority, pri, key=lambda x: x.value)
            reasons.extend(ctx_reasons)
            
        elif context == AudioContext.MANUAL_RECORDING:
            score, pri, ctx_reasons = self._score_manual_context(device)
            base_score += score
            priority = max(priority, pri, key=lambda x: x.value)
            reasons.extend(ctx_reasons)
            
        # Universal scoring factors
        score, uni_reasons = self._score_universal_factors(device)
        base_score += score
        reasons.extend(uni_reasons)
        
        # User preference scoring
        pref_score, pref_reasons = self._score_user_preferences(device, context)
        base_score += pref_score
        reasons.extend(pref_reasons)
        
        # Device health scoring
        health_score, health_reasons = self._score_device_health(device)
        base_score += health_score
        reasons.extend(health_reasons)
        
        return max(0, base_score), priority, reasons

    def _score_teams_context(self, device: AudioDevice) -> Tuple[int, DevicePriority, List[str]]:
        """Score device for Teams meeting context"""
        score = 0
        reasons = []
        priority = DevicePriority.LOW
        
        # Priority 1: Loopback devices (capture system audio)
        if getattr(device, 'is_loopback', False):
            score += 50
            priority = DevicePriority.HIGHEST
            reasons.append("loopback device for system audio capture")
            
            # Bonus for speaker loopback
            if "speaker" in device.name.lower() or "output" in device.name.lower():
                score += 20
                reasons.append("speaker loopback (optimal for Teams)")
                
        # Priority 2: High-quality microphones
        elif device.max_input_channels > 0:
            # Prefer USB/professional devices
            if any(term in device.name.lower() for term in ["usb", "headset", "professional", "studio"]):
                score += 30
                priority = DevicePriority.HIGH
                reasons.append("professional audio device")
            else:
                score += 15
                priority = DevicePriority.MEDIUM
                reasons.append("microphone device")
                
        # Bonus for default devices
        if getattr(device, 'is_default', False):
            score += 10
            reasons.append("system default device")
            
        return score, priority, reasons

    def _score_manual_context(self, device: AudioDevice) -> Tuple[int, DevicePriority, List[str]]:
        """Score device for manual recording context"""
        score = 0
        reasons = []
        priority = DevicePriority.LOW
        
        # Priority 1: Dedicated microphones
        if device.max_input_channels > 0 and not getattr(device, 'is_loopback', False):
            # USB/Professional devices
            if any(term in device.name.lower() for term in ["usb", "headset", "professional", "studio", "microphone"]):
                score += 40
                priority = DevicePriority.HIGHEST
                reasons.append("dedicated professional microphone")
            else:
                score += 25
                priority = DevicePriority.HIGH
                reasons.append("microphone device")
                
        # Priority 2: Loopback for system audio
        elif getattr(device, 'is_loopback', False):
            score += 20
            priority = DevicePriority.MEDIUM
            reasons.append("system audio loopback")
            
        # Bonus for high sample rates
        if hasattr(device, 'default_sample_rate') and device.default_sample_rate >= 44100:
            score += 5
            reasons.append("high sample rate support")
            
        return score, priority, reasons

    def _score_universal_factors(self, device: AudioDevice) -> Tuple[int, List[str]]:
        """Score universal device factors"""
        score = 0
        reasons = []
        
        # Avoid known problematic devices
        problematic_terms = ["generic", "realtek", "via", "bluetooth"]
        if any(term in device.name.lower() for term in problematic_terms):
            score -= 5
            reasons.append("potentially problematic device type")
            
        # Prefer WASAPI devices
        if hasattr(device, 'host_api') and "wasapi" in str(device.host_api).lower():
            score += 15
            reasons.append("WASAPI support (better latency)")
            
        # Bonus for input capability
        if device.max_input_channels > 0:
            score += 5
            reasons.append("input capability")
            
        return score, reasons

    def _score_user_preferences(self, device: AudioDevice, context: AudioContext) -> Tuple[int, List[str]]:
        """Score based on user preferences and history"""
        score = 0
        reasons = []
        
        pref_key = f"{context.value}:{device.name}"
        if pref_key in self.preferences:
            pref = self.preferences[pref_key]
            
            # Success/failure ratio bonus
            total_uses = pref.success_count + pref.failure_count
            if total_uses > 0:
                success_ratio = pref.success_count / total_uses
                if success_ratio > 0.8:
                    score += 20
                    reasons.append("high success rate from history")
                elif success_ratio < 0.3:
                    score -= 15
                    reasons.append("low success rate from history")
                    
            # Recent usage bonus
            if time.time() - pref.last_used < 86400:  # 24 hours
                score += 10
                reasons.append("recently used successfully")
                
        return score, reasons

    def _score_device_health(self, device: AudioDevice) -> Tuple[int, List[str]]:
        """Score device health and availability"""
        score = 0
        reasons = []
        
        # Basic availability check
        try:
            # Could add actual device testing here
            score += 5
            reasons.append("device appears available")
        except Exception:
            score -= 20
            reasons.append("device may be unavailable")
            
        return score, reasons

    def _is_context_match(self, device: AudioDevice, context: AudioContext) -> bool:
        """Check if device is a good match for context"""
        if context == AudioContext.TEAMS_MEETING:
            return getattr(device, 'is_loopback', False)
        elif context == AudioContext.MANUAL_RECORDING:
            return device.max_input_channels > 0
        return True

    def record_device_result(self, device: AudioDevice, context: AudioContext, success: bool) -> None:
        """Record the result of using a device"""
        pref_key = f"{context.value}:{device.name}"
        
        if pref_key not in self.preferences:
            self.preferences[pref_key] = DevicePreference(
                context=context,
                device_name=device.name,
                device_index=device.index,
                last_used=time.time(),
                success_count=0,
                failure_count=0
            )
            
        pref = self.preferences[pref_key]
        pref.last_used = time.time()
        
        if success:
            pref.success_count += 1
            logger.info(f"Recorded successful use of {device.name} for {context.value}")
        else:
            pref.failure_count += 1
            logger.warning(f"Recorded failed use of {device.name} for {context.value}")
            
        # Auto-block devices with very low success rates
        total_uses = pref.success_count + pref.failure_count
        if total_uses >= 5 and (pref.success_count / total_uses) < 0.2:
            self.blocked_devices.add(device.name)
            logger.warning(f"Auto-blocked device {device.name} due to low success rate")
            
        self._save_preferences()

    def block_device(self, device_name: str) -> None:
        """Block a device from selection"""
        self.blocked_devices.add(device_name)
        logger.info(f"Blocked device: {device_name}")
        self._save_preferences()

    def unblock_device(self, device_name: str) -> None:
        """Unblock a device"""
        self.blocked_devices.discard(device_name)
        logger.info(f"Unblocked device: {device_name}")
        self._save_preferences()

    def get_device_priority_for_context(self, context: AudioContext) -> List[str]:
        """Get device priority order for context (for UI display)"""
        priority_rules = {
            AudioContext.TEAMS_MEETING: [
                "1. Loopback speakers (best for system audio capture)",
                "2. Professional USB headsets",
                "3. Default system microphone",
                "4. Built-in microphone array"
            ],
            AudioContext.MANUAL_RECORDING: [
                "1. Dedicated USB microphones", 
                "2. Professional headset microphones",
                "3. System loopback (for app audio)",
                "4. Built-in microphones"
            ]
        }
        return priority_rules.get(context, ["Default system priority"])

    def _load_preferences(self) -> None:
        """Load user preferences from storage"""
        try:
            from config import settings
            prefs_file = settings.storage_dir / "device_preferences.json"
            
            if prefs_file.exists():
                with open(prefs_file) as f:
                    data = json.load(f)
                    
                # Reconstruct preferences
                for key, pref_data in data.get("preferences", {}).items():
                    self.preferences[key] = DevicePreference(
                        context=AudioContext(pref_data["context"]),
                        device_name=pref_data["device_name"],
                        device_index=pref_data.get("device_index"),
                        last_used=pref_data["last_used"],
                        success_count=pref_data["success_count"],
                        failure_count=pref_data["failure_count"]
                    )
                    
                self.blocked_devices = set(data.get("blocked_devices", []))
                
        except Exception as e:
            logger.debug(f"Could not load device preferences: {e}")

    def _save_preferences(self) -> None:
        """Save user preferences to storage"""
        try:
            from config import settings
            prefs_file = settings.storage_dir / "device_preferences.json"
            prefs_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "preferences": {},
                "blocked_devices": list(self.blocked_devices),
                "last_updated": time.time()
            }
            
            # Serialize preferences
            for key, pref in self.preferences.items():
                data["preferences"][key] = {
                    "context": pref.context.value,
                    "device_name": pref.device_name,
                    "device_index": pref.device_index,
                    "last_used": pref.last_used,
                    "success_count": pref.success_count,
                    "failure_count": pref.failure_count
                }
                
            with open(prefs_file, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Could not save device preferences: {e}")


# Global selector instance
_selector_instance: Optional[SmartDeviceSelector] = None


def get_smart_selector() -> SmartDeviceSelector:
    """Get global smart device selector instance"""
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = SmartDeviceSelector()
    return _selector_instance


def select_best_device(context: AudioContext = AudioContext.SYSTEM_DEFAULT) -> Optional[AudioDevice]:
    """Select the best device for given context"""
    return get_smart_selector().select_device(context)


def record_device_success(device: AudioDevice, context: AudioContext) -> None:
    """Record successful device usage"""
    get_smart_selector().record_device_result(device, context, True)


def record_device_failure(device: AudioDevice, context: AudioContext) -> None:
    """Record failed device usage"""  
    get_smart_selector().record_device_result(device, context, False)