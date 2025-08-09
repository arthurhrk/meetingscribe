from pathlib import Path
from typing import Optional
import os
from pydantic_settings import BaseSettings
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    app_name: str = "MeetingScribe"
    app_version: str = "1.0.0"
    debug: bool = True
    log_level: str = "DEBUG"
    
    base_dir: Path = Path(__file__).parent
    storage_dir: Path = base_dir / "storage"
    models_dir: Path = base_dir / "models"
    logs_dir: Path = base_dir / "logs"
    recordings_dir: Path = storage_dir / "recordings"
    transcriptions_dir: Path = storage_dir / "transcriptions"
    exports_dir: Path = storage_dir / "exports"
    
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    chunk_duration: int = 30
    
    whisper_model: str = "base"
    whisper_language: str = "pt"
    whisper_device: str = "auto"
    
    model_config = {"env_file": ".env", "case_sensitive": False}

def setup_directories():
    settings = Settings()
    
    directories = [
        settings.storage_dir,
        settings.models_dir,
        settings.logs_dir,
        settings.recordings_dir,
        settings.transcriptions_dir,
        settings.exports_dir
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Diretório criado/verificado: {directory}")

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