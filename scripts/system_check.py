import sys
import importlib
import json
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

# Add project root to Python path so we can import from src/
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

console = Console()

# Verificar se é modo JSON antes de inicializar logs
JSON_MODE = '--json' in sys.argv

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
    dependencies = ['rich', 'loguru', 'pydantic', 'python-dotenv', 'pyaudiowpatch']
    results = {}
    
    for dep in dependencies:
        try:
            if dep == 'pyaudiowpatch':
                # Verificação especial para pyaudiowpatch
                try:
                    module = importlib.import_module('pyaudiowpatch')
                    version = getattr(module, '__version__', 'Desconhecida')
                    results[dep] = (True, f"v{version}")
                except ImportError:
                    # Fallback para pyaudio padrão
                    try:
                        module = importlib.import_module('pyaudio')
                        version = getattr(module, '__version__', 'Desconhecida')
                        results[dep] = (True, f"pyaudio v{version} (fallback)")
                    except ImportError:
                        results[dep] = (False, "Não instalado")
            else:
                module = importlib.import_module(dep.replace('-', '_'))
                version = getattr(module, '__version__', 'Desconhecida')
                results[dep] = (True, f"v{version}")
        except ImportError:
            results[dep] = (False, "Não instalado")
    
    return results

def check_directory_structure() -> Dict[str, Tuple[bool, str]]:
    """Verifica a estrutura de diretórios do projeto"""
    base_dir = Path(__file__).parent.parent  # scripts/ -> project root
    required_dirs = {
        'src': base_dir / 'src',
        'storage': base_dir / 'storage',
        'scripts': base_dir / 'scripts',
        'docs': base_dir / 'docs',
        'tests': base_dir / 'tests',
        'storage/recordings': base_dir / 'storage' / 'recordings',
        'storage/logs': base_dir / 'storage' / 'logs'
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
    config_path = Path(__file__).parent.parent / 'src' / 'config.py'  # Now in src/

    if config_path.exists():
        return True, "Arquivo existe"
    else:
        return False, "Arquivo não encontrado"

def check_audio_system() -> Dict[str, Tuple[bool, str]]:
    """Verifica sistema de áudio e dispositivos disponíveis"""
    results = {}
    
    # Silenciar logs se estiver em modo JSON
    if JSON_MODE:
        import os
        os.environ['LOG_LEVEL'] = 'CRITICAL'
        # Silenciar stderr temporariamente para evitar logs coloridos
        import sys
        from io import StringIO
        original_stderr = sys.stderr
        sys.stderr = StringIO()
    
    # Verificar se pyaudiowpatch está disponível
    try:
        import pyaudiowpatch as pyaudio
        results['PyAudio WASAPI'] = (True, "Disponível")
        
        # Verificar se consegue inicializar
        try:
            audio = pyaudio.PyAudio()
            device_count = audio.get_device_count()
            
            # Verificar WASAPI
            wasapi_available = False
            loopback_devices = 0
            
            for i in range(device_count):
                try:
                    device_info = audio.get_device_info_by_index(i)
                    host_api_info = audio.get_host_api_info_by_index(device_info['hostApi'])
                    
                    if 'wasapi' in host_api_info['name'].lower():
                        wasapi_available = True
                        
                        # Verificar se é loopback
                        device_name = device_info['name'].lower()
                        if ('loopback' in device_name or 
                            device_info['maxInputChannels'] > 0 and device_info['maxOutputChannels'] == 0):
                            loopback_devices += 1
                
                except Exception:
                    continue
            
            audio.terminate()
            
            results['WASAPI Support'] = (wasapi_available, "Disponível" if wasapi_available else "Não encontrado")
            results['Loopback Devices'] = (loopback_devices > 0, f"{loopback_devices} encontrados" if loopback_devices > 0 else "Nenhum encontrado")
            results['Total Devices'] = (device_count > 0, f"{device_count} dispositivos")
            
        except Exception as e:
            results['PyAudio Init'] = (False, f"Erro: {e}")
            
    except ImportError:
        results['PyAudio WASAPI'] = (False, "Não instalado")
        
        # Tentar pyaudio padrão
        try:
            import pyaudio
            results['PyAudio Standard'] = (True, "Disponível (limitado)")
        except ImportError:
            results['PyAudio Standard'] = (False, "Não instalado")
    
    # Verificar módulos de áudio do projeto
    try:
        from src.audio import DeviceManager
        results['DeviceManager'] = (True, "Módulo carregado")

        # Testar DeviceManager
        try:
            dm = DeviceManager()
            devices = dm.list_all_devices()

            results['Device Detection'] = (len(devices) > 0, f"{len(devices)} dispositivos detectados")
        except Exception as e:
            results['Device Detection'] = (False, f"Erro: {e}")

    except ImportError as e:
        results['DeviceManager'] = (False, f"Erro de importação: {e}")

    # Verificar AudioRecorder
    try:
        from src.audio import AudioRecorder
        results['AudioRecorder'] = (True, "Módulo carregado")

        try:
            recorder = AudioRecorder()
            results['Recorder Config'] = (True, f"AudioRecorder instanciado")
            recorder.close()
        except Exception as e:
            results['Recorder Config'] = (False, f"Erro: {e}")

    except ImportError as e:
        results['AudioRecorder'] = (False, f"Erro de importação: {e}")
    
    # Restaurar stderr se foi silenciado
    if JSON_MODE and 'original_stderr' in locals():
        import sys
        sys.stderr = original_stderr
    
    return results

def create_status_table(checks: Dict[str, List[Tuple[str, bool, str]]]) -> Table:
    """Cria uma tabela com o status das verificações"""
    table = Table(title="[SEARCH] Status do Sistema MeetingScribe", box=box.ROUNDED)
    
    table.add_column("Categoria", style="bold cyan", min_width=15)
    table.add_column("Componente", style="bold", min_width=20)
    table.add_column("Status", justify="center", min_width=8)
    table.add_column("Detalhes", min_width=25)
    
    for category, items in checks.items():
        for i, (component, status, details) in enumerate(items):
            status_icon = "[OK]" if status else "[ERROR]"
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
    parser = argparse.ArgumentParser(description='MeetingScribe System Check')
    parser.add_argument('--json', action='store_true', help='Output em formato JSON')
    args = parser.parse_args()
    
    # Executar verificações
    python_ok, python_details = check_python_version()
    dependencies = check_dependencies()
    directories = check_directory_structure()
    config_ok, config_details = check_config_file()
    audio_system = check_audio_system()
    
    # Calcular resumo
    total_checks = 2 + len(dependencies) + len(directories) + len(audio_system)
    passed_checks = (
        int(python_ok) + 
        int(config_ok) + 
        sum(status for status, _ in dependencies.values()) + 
        sum(status for status, _ in directories.values()) +
        sum(status for status, _ in audio_system.values())
    )
    
    if args.json:
        # Output JSON para Raycast
        components = []
        
        # Sistema
        components.append({"name": "Python", "status": "ok" if python_ok else "error", "message": python_details, "icon": "✅" if python_ok else "❌"})
        components.append({"name": "Configuração", "status": "ok" if config_ok else "error", "message": config_details, "icon": "✅" if config_ok else "❌"})
        
        # Dependências
        for dep, (status, details) in dependencies.items():
            components.append({"name": dep, "status": "ok" if status else "error", "message": details, "icon": "✅" if status else "❌"})
        
        # Diretórios
        for dir_name, (status, details) in directories.items():
            components.append({"name": f"Dir: {dir_name}", "status": "ok" if status else "error", "message": details, "icon": "✅" if status else "❌"})
        
        # Sistema de Áudio
        for component, (status, details) in audio_system.items():
            components.append({"name": f"Audio: {component}", "status": "ok" if status else "error", "message": details, "icon": "✅" if status else "❌"})
        
        # Informações de hardware (simulado)
        hardware = {
            "cpu": "Intel/AMD CPU",
            "memory": "8GB+ RAM",
            "gpu": "Integrated/Dedicated GPU",
            "audio_devices": len(audio_system)
        }
        
        # Modelos Whisper (simulado)
        models = [
            {"name": "tiny", "size": "39MB", "status": "available"},
            {"name": "base", "size": "74MB", "status": "available"},
            {"name": "small", "size": "244MB", "status": "available"},
            {"name": "medium", "size": "769MB", "status": "available"},
            {"name": "large-v3", "size": "1550MB", "status": "available"}
        ]
        
        result = {
            "overall": "success" if passed_checks == total_checks else "error",
            "components": components,
            "hardware": hardware,
            "models": models
        }
        
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return passed_checks == total_checks
    
    # Interactive mode (original)
    console.print(Panel(
        "[bold blue]Sistema de Verificacao do MeetingScribe[/bold blue]\n"
        "Verificando componentes essenciais...",
        title="[MIC] MeetingScribe",
        border_style="blue"
    ))
    
    console.print()
    
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
        ],
        "Sistema de Áudio": [
            (component, status, details) for component, (status, details) in audio_system.items()
        ]
    }
    
    # Mostrar tabela
    table = create_status_table(checks)
    console.print(table)
    
    console.print()
    
    if passed_checks == total_checks:
        console.print(Panel(
            f"[bold green][OK] Todos os {total_checks} checks passaram![/bold green]\n"
            "Sistema pronto para uso.",
            title="[SUCCESS] Sucesso",
            border_style="green"
        ))
    else:
        failed_checks = total_checks - passed_checks
        console.print(Panel(
            f"[bold red][ERROR] {failed_checks} de {total_checks} checks falharam[/bold red]\n"
            "Verifique os itens marcados em vermelho acima.",
            title="[ERROR] Problemas Encontrados",
            border_style="red"
        ))
    
    return passed_checks == total_checks

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)