"""
MeetingScribe v2.0 - Compatibility Wrapper

Wrapper de compatibilidade que redireciona para client/cli_main.py.
Mantém entrada padrão 'python main.py' funcionando identicamente ao v1.0.

ARQUITETURA v2.0:
- Este arquivo é apenas um wrapper para compatibilidade
- Implementação real em client/cli_main.py
- Preserva 100% funcionalidade v1.0
"""

import sys
from pathlib import Path

# Redirect to refactored CLI main
sys.path.insert(0, str(Path(__file__).parent / "client"))

try:
    from cli_main import main
    
    if __name__ == "__main__":
        sys.exit(main())
        
except ImportError as e:
    print(f"❌ Erro ao carregar MeetingScribe v2.0: {e}")
    print("\\nFallback para v1.0:")
    print("Execute: python main_v1_backup.py")
    sys.exit(1)