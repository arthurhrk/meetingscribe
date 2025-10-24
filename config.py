from pathlib import Path
from typing import Optional
import os
from pydantic_settings import BaseSettings
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """MeetingScribe Configuration - Audio Recording Focus"""

    app_name: str = "MeetingScribe"
    app_version: str = "2.0.0"
    debug: bool = True
    log_level: str = "INFO"

    # Directory structure
    base_dir: Path = Path(__file__).parent
    storage_dir: Path = base_dir / "storage"
    logs_dir: Path = base_dir / "logs"
    recordings_dir: Path = storage_dir / "recordings"

    # Audio recording settings (high-quality for Teams)
    audio_sample_rate: int = 48000  # 48kHz - professional quality
    audio_channels: int = 2         # Stereo
    chunk_duration: int = 30        # Recording chunk size in seconds

    # Recording defaults
    default_recording_duration: int = 300  # 5 minutes default
    max_recording_duration: int = 7200     # 2 hours max

    model_config = {"env_file": ".env", "case_sensitive": False}

def setup_directories():
    """Create required directories for MeetingScribe"""
    settings = Settings()

    directories = [
        settings.storage_dir,
        settings.logs_dir,
        settings.recordings_dir
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Directory ready: {directory}")

def setup_logging():
    settings = Settings()
    
    logger.remove()
    logger.add(
        settings.logs_dir / "meetingscribe.log",
        rotation="10 MB",
        retention="1 month",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )
    
    if settings.debug:
        logger.add(
            lambda msg: print(msg, end=""),
            level="DEBUG",
            format="{time:HH:mm:ss} | {level} | {message}"
        )

settings = Settings()