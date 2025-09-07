"""Teams Integration Module

Provides Microsoft Teams meeting detection and integration capabilities.
"""

from .teams_detector import (
    TeamsDetector,
    MeetingDetection, 
    MeetingState,
    get_detector,
    start_teams_monitoring,
    stop_teams_monitoring
)

__all__ = [
    "TeamsDetector",
    "MeetingDetection",
    "MeetingState", 
    "get_detector",
    "start_teams_monitoring",
    "stop_teams_monitoring"
]