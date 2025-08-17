"""
API REST do MeetingScribe

Expõe funcionalidades via HTTP para integração com Raycast e outras interfaces.
Utiliza FastAPI para performance e documentação automática.

Author: MeetingScribe Team
Version: 1.1.0
Python: >=3.8
"""

from .main import app, get_app

__all__ = ["app", "get_app"]