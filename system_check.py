import sys
import importlib
from pathlib import Path
from typing import List, Tuple, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

def check_python_version() -> Tuple[bool, str]:
    """Verifica se a versão do Python é >= 3.8"""
    version = sys.version_info
    required_version = (3, 8)
    
    if version >= required_version:
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"Python {version.major}.{version.minor}.{version.micro} (Requerido: >= 3.8)"

def check_dependencies() -> Dict[str, Tuple[bool, str]]:
    """Verifica se as dependências estão instaladas"""
    dependencies = ['rich', 'loguru', 'pydantic', 'python-dotenv']
    results = {}
    
    for dep in dependencies:
        try:
            module = importlib.import_module(dep.replace('-', '_'))
            version = getattr(module, '__version__', 'Desconhecida')
            results[dep] = (True, f"v{version}")
        except ImportError:
            results[dep] = (False, "Não instalado")
    
    return results

def check_directory_structure() -> Dict[str, Tuple[bool, str]]:
    """Verifica a estrutura de diretórios do projeto"""
    base_dir = Path(__file__).parent
    required_dirs = {
        'src': base_dir / 'src',
        'storage': base_dir / 'storage',
        'models': base_dir / 'models',
        'logs': base_dir / 'logs',
        'tests': base_dir / 'tests',
        'storage/recordings': base_dir / 'storage' / 'recordings',
        'storage/transcriptions': base_dir / 'storage' / 'transcriptions',
        'storage/exports': base_dir / 'storage' / 'exports'
    }
    
    results = {}
    for name, path in required_dirs.items():
        if path.exists() and path.is_dir():
            results[name] = (True, "Existe")
        else:
            results[name] = (False, "Não encontrado")
    
    return results

def check_config_file() -> Tuple[bool, str]:
    """Verifica se o arquivo config.py existe"""
    config_path = Path(__file__).parent / 'config.py'
    
    if config_path.exists():
        return True, "Arquivo existe"
    else:
        return False, "Arquivo não encontrado"

def create_status_table(checks: Dict[str, List[Tuple[str, bool, str]]]) -> Table:
    """Cria uma tabela com o status das verificações"""
    table = Table(title="🔍 Status do Sistema MeetingScribe", box=box.ROUNDED)
    
    table.add_column("Categoria", style="bold cyan", min_width=15)
    table.add_column("Componente", style="bold", min_width=20)
    table.add_column("Status", justify="center", min_width=8)
    table.add_column("Detalhes", min_width=25)
    
    for category, items in checks.items():
        for i, (component, status, details) in enumerate(items):
            status_icon = "✅" if status else "❌"
            status_color = "green" if status else "red"
            
            category_display = category if i == 0 else ""
            
            table.add_row(
                category_display,
                component,
                Text(status_icon, style=status_color),
                details
            )
            
            if i < len(items) - 1:
                table.add_row("", "", "", "")
    
    return table

def main():
    """Executa todas as verificações do sistema"""
    console.print(Panel(
        "[bold blue]Sistema de Verificação do MeetingScribe[/bold blue]\n"
        "Verificando componentes essenciais...",
        title="🎤 MeetingScribe",
        border_style="blue"
    ))
    
    console.print()
    
    # Executar verificações
    python_ok, python_details = check_python_version()
    dependencies = check_dependencies()
    directories = check_directory_structure()
    config_ok, config_details = check_config_file()
    
    # Organizar resultados
    checks = {
        "Sistema": [
            ("Python", python_ok, python_details),
            ("Configuração", config_ok, config_details)
        ],
        "Dependências": [
            (dep, status, details) for dep, (status, details) in dependencies.items()
        ],
        "Diretórios": [
            (dir_name, status, details) for dir_name, (status, details) in directories.items()
        ]
    }
    
    # Mostrar tabela
    table = create_status_table(checks)
    console.print(table)
    
    # Resumo
    total_checks = 2 + len(dependencies) + len(directories)
    passed_checks = (
        int(python_ok) + 
        int(config_ok) + 
        sum(status for status, _ in dependencies.values()) + 
        sum(status for status, _ in directories.values())
    )
    
    console.print()
    
    if passed_checks == total_checks:
        console.print(Panel(
            f"[bold green]✅ Todos os {total_checks} checks passaram![/bold green]\n"
            "Sistema pronto para uso.",
            title="✅ Sucesso",
            border_style="green"
        ))
    else:
        failed_checks = total_checks - passed_checks
        console.print(Panel(
            f"[bold red]❌ {failed_checks} de {total_checks} checks falharam[/bold red]\n"
            "Verifique os itens marcados em vermelho acima.",
            title="❌ Problemas Encontrados",
            border_style="red"
        ))
    
    return passed_checks == total_checks

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)