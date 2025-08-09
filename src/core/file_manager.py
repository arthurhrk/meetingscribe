"""
File Manager para MeetingScribe

Módulo responsável pelo gerenciamento de arquivos de transcrições.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json
import os

from config import settings


@dataclass
class TranscriptionFile:
    """Representa um arquivo de transcrição."""
    filename: str
    path: Path
    created: datetime
    duration: float
    language: str
    model: str
    text: Optional[str] = None


def list_transcriptions(limit: Optional[int] = None) -> List[TranscriptionFile]:
    """
    Lista todas as transcrições disponíveis.
    
    Args:
        limit: Número máximo de transcrições a retornar
        
    Returns:
        Lista de TranscriptionFile ordenada por data (mais recente primeiro)
    """
    transcriptions = []
    transcriptions_dir = settings.transcriptions_dir
    
    if not transcriptions_dir.exists():
        return transcriptions
    
    # Buscar por arquivos .json de transcrição
    for json_file in transcriptions_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extrair informações do JSON
            transcription = TranscriptionFile(
                filename=json_file.stem,
                path=json_file,
                created=datetime.fromisoformat(data.get('created', '2023-01-01T00:00:00')),
                duration=data.get('duration', 0.0),
                language=data.get('language', 'unknown'),
                model=data.get('model', 'unknown'),
                text=data.get('text', '')
            )
            transcriptions.append(transcription)
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Ignorar arquivos JSON inválidos
            continue
    
    # Ordenar por data de criação (mais recente primeiro)
    transcriptions.sort(key=lambda t: t.created, reverse=True)
    
    # Aplicar limite se especificado
    if limit:
        transcriptions = transcriptions[:limit]
    
    return transcriptions


def find_transcription(filename: str) -> Optional[TranscriptionFile]:
    """
    Encontra uma transcrição específica pelo nome.
    
    Args:
        filename: Nome do arquivo (com ou sem extensão)
        
    Returns:
        TranscriptionFile se encontrado, None caso contrário
    """
    # Remover extensão se presente
    if filename.endswith('.json'):
        filename = filename[:-5]
    
    transcriptions_dir = settings.transcriptions_dir
    json_file = transcriptions_dir / f"{filename}.json"
    
    if not json_file.exists():
        return None
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return TranscriptionFile(
            filename=filename,
            path=json_file,
            created=datetime.fromisoformat(data.get('created', '2023-01-01T00:00:00')),
            duration=data.get('duration', 0.0),
            language=data.get('language', 'unknown'),
            model=data.get('model', 'unknown'),
            text=data.get('text', '')
        )
        
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def get_transcription_text(filename: str) -> Optional[str]:
    """
    Obtém apenas o texto de uma transcrição.
    
    Args:
        filename: Nome do arquivo de transcrição
        
    Returns:
        Texto da transcrição ou None se não encontrado
    """
    transcription = find_transcription(filename)
    return transcription.text if transcription else None


def delete_transcription(filename: str) -> bool:
    """
    Remove uma transcrição.
    
    Args:
        filename: Nome do arquivo de transcrição
        
    Returns:
        True se removido com sucesso, False caso contrário
    """
    transcription = find_transcription(filename)
    if not transcription:
        return False
    
    try:
        transcription.path.unlink()
        return True
    except OSError:
        return False