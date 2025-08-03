"""
MeetingScribe - Entry Point Principal

Sistema de transcrição inteligente para reuniões usando OpenAI Whisper.
Processamento 100% local com identificação de speakers e interface Rica.

Author: MeetingScribe Team
Version: 1.0.0
Python: >=3.8
"""

import sys
import traceback
from pathlib import Path
from typing import NoReturn, Optional

from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.text import Text

try:
    from config import settings, setup_directories, setup_logging
except ImportError as e:
    print(f"❌ Erro crítico ao importar configurações: {e}")
    print("Certifique-se de que:")
    print("• O arquivo config.py existe no diretório raiz")
    print("• As dependências estão instaladas: pip install -r requirements.txt")
    print("• Execute: python system_check.py para diagnóstico completo")
    sys.exit(1)

console = Console()

def show_welcome_message() -> None:
    """
    Exibe mensagem de boas-vindas estilizada usando Rich.
    
    Mostra informações sobre o aplicativo, versão e funcionalidades
    principais em um painel colorido e bem formatado.
    
    Returns:
        None
        
    Raises:
        RuntimeError: Se houver erro ao acessar configurações do settings
    """
    try:
        welcome_text = Text()
        welcome_text.append("🎤 ", style="bold blue")
        welcome_text.append("MeetingScribe", style="bold blue")
        welcome_text.append(f" v{settings.app_version}", style="dim")
        welcome_text.append("\n\nSistema inteligente de transcrição de reuniões", style="white")
        welcome_text.append("\nPowered by OpenAI Whisper", style="dim")
        
        panel = Panel(
            welcome_text,
            title="🎯 Bem-vindo",
            border_style="blue",
            padding=(1, 2)
        )
        
        console.print()
        console.print(panel)
        console.print()
        
    except Exception as e:
        logger.error(f"Erro ao exibir mensagem de boas-vindas: {e}")
        console.print("❌ [red]Erro ao carregar interface de boas-vindas[/red]")
        raise RuntimeError(f"Falha na inicialização da interface: {e}") from e

def initialize_system() -> None:
    """
    Inicializa todos os componentes essenciais do sistema.
    
    Executa sequencialmente:
    1. Configuração e criação de diretórios necessários
    2. Inicialização do sistema de logging
    3. Verificação e validação das configurações
    
    Returns:
        None
        
    Raises:
        FileNotFoundError: Se não conseguir criar diretórios necessários
        PermissionError: Se não tiver permissões adequadas
        RuntimeError: Se houver falha na inicialização de componentes críticos
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        
        # Task 1: Configuração de diretórios
        task1 = progress.add_task("Configurando diretórios...", total=None)
        try:
            setup_directories()
            progress.update(task1, description="✅ Diretórios configurados")
            logger.debug(f"Diretórios criados em: {settings.base_dir}")
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error(f"Falha crítica ao configurar diretórios: {e}")
            progress.update(task1, description="❌ Erro nos diretórios")
            raise RuntimeError(f"Não foi possível criar estrutura de diretórios: {e}") from e
        except Exception as e:
            logger.error(f"Erro inesperado na configuração de diretórios: {e}")
            progress.update(task1, description="❌ Erro nos diretórios")
            raise RuntimeError(f"Falha inesperada na configuração: {e}") from e
        
        # Task 2: Inicialização do logging
        task2 = progress.add_task("Inicializando logging...", total=None)
        try:
            setup_logging()
            logger.info("Sistema MeetingScribe iniciado com sucesso")
            progress.update(task2, description="✅ Logging inicializado")
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"Falha ao configurar logging: {e}")
            progress.update(task2, description="❌ Erro no logging")
            raise RuntimeError(f"Não foi possível configurar sistema de logs: {e}") from e
        except Exception as e:
            progress.update(task2, description="❌ Erro no logging")
            raise RuntimeError(f"Falha inesperada no logging: {e}") from e
        
        # Task 3: Verificação de configurações
        task3 = progress.add_task("Verificando configurações...", total=None)
        try:
            # Validações básicas de configuração
            if not hasattr(settings, 'app_name') or not settings.app_name:
                raise ValueError("Nome da aplicação não configurado")
            
            if not hasattr(settings, 'app_version') or not settings.app_version:
                raise ValueError("Versão da aplicação não configurada")
            
            if settings.debug:
                logger.debug("Modo DEBUG ativado - logs verbosos habilitados")
                logger.debug(f"Configurações carregadas: {settings.model_dump()}")
            
            progress.update(task3, description="✅ Configurações verificadas")
            
        except (ValueError, AttributeError) as e:
            logger.error(f"Configurações inválidas detectadas: {e}")
            progress.update(task3, description="❌ Erro nas configurações")
            raise RuntimeError(f"Configurações do sistema inválidas: {e}") from e
        except Exception as e:
            logger.error(f"Erro inesperado na verificação: {e}")
            progress.update(task3, description="❌ Erro nas configurações")
            raise RuntimeError(f"Falha na verificação do sistema: {e}") from e

def show_main_menu() -> None:
    """
    Exibe o menu principal da aplicação com opções disponíveis.
    
    Apresenta as funcionalidades principais em um painel estilizado,
    incluindo gravação, transcrição, gerenciamento e configurações.
    
    Returns:
        None
        
    Note:
        Todas as opções atualmente são placeholders para desenvolvimento futuro.
    """
    menu_options = [
        "1. 🎙️  Iniciar nova gravação",
        "2. 📝  Transcrever arquivo existente", 
        "3. 📁  Gerenciar transcrições",
        "4. ⚙️  Configurações",
        "5. 📊  Relatórios",
        "6. ❌  Sair"
    ]
    
    try:
        console.print(Panel(
            "\n".join(menu_options),
            title="📋 Menu Principal",
            border_style="cyan"
        ))
        logger.debug("Menu principal exibido com sucesso")
    except Exception as e:
        logger.error(f"Erro ao exibir menu principal: {e}")
        console.print("❌ [red]Erro ao carregar menu principal[/red]")
        # Fallback para menu simples em texto
        console.print("\nMenu Principal:")
        for option in menu_options:
            console.print(f"  {option}")

def handle_menu_choice() -> None:
    """
    Processa e executa as escolhas do usuário no menu principal.
    
    Mantém um loop interativo até que o usuário escolha sair.
    Cada opção é logada e executa funcionalidades placeholder.
    
    Returns:
        None
        
    Raises:
        KeyboardInterrupt: Se o usuário interromper com Ctrl+C
        RuntimeError: Se houver erro crítico na interface
    """
    valid_choices = ["1", "2", "3", "4", "5", "6"]
    
    while True:
        try:
            console.print()
            choice = Prompt.ask(
                "Escolha uma opção",
                choices=valid_choices,
                default="6"
            )
            
            # Log da escolha do usuário
            logger.debug(f"Usuário selecionou opção: {choice}")
            
            if choice == "1":
                console.print("🎙️ [yellow]Funcionalidade de gravação em desenvolvimento...[/yellow]")
                logger.info("Usuário solicitou: Nova gravação")
                
            elif choice == "2":
                console.print("📝 [yellow]Funcionalidade de transcrição em desenvolvimento...[/yellow]")
                logger.info("Usuário solicitou: Transcrever arquivo")
                
            elif choice == "3":
                console.print("📁 [yellow]Gerenciador de transcrições em desenvolvimento...[/yellow]")
                logger.info("Usuário solicitou: Gerenciar transcrições")
                
            elif choice == "4":
                console.print("⚙️ [yellow]Painel de configurações em desenvolvimento...[/yellow]")
                logger.info("Usuário solicitou: Configurações")
                
            elif choice == "5":
                console.print("📊 [yellow]Sistema de relatórios em desenvolvimento...[/yellow]")
                logger.info("Usuário solicitou: Relatórios")
                
            elif choice == "6":
                try:
                    if Confirm.ask("Deseja realmente sair?"):
                        console.print("👋 [green]Obrigado por usar o MeetingScribe![/green]")
                        logger.info("Usuário encerrou o sistema normalmente")
                        break
                    else:
                        logger.debug("Usuário cancelou a saída")
                except KeyboardInterrupt:
                    console.print("\n👋 [yellow]Saída forçada pelo usuário[/yellow]")
                    logger.info("Usuário forçou a saída com Ctrl+C")
                    break
            
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n\n🛑 [yellow]Operação interrompida pelo usuário[/yellow]")
            logger.info("Menu interrompido pelo usuário (Ctrl+C)")
            break
            
        except Exception as e:
            logger.error(f"Erro no processamento do menu: {e}")
            console.print(f"❌ [red]Erro no menu: {e}[/red]")
            console.print("Tentando continuar...")
            
            # Verificar se ainda é possível continuar
            try:
                if not Confirm.ask("Continuar usando o aplicativo?", default=True):
                    break
            except Exception:
                logger.error("Interface crítica falhou - encerrando")
                break

def main() -> int:
    """
    Função principal e entry point do MeetingScribe.
    
    Coordena a inicialização completa do sistema, exibição da interface
    e execução do loop principal da aplicação.
    
    Returns:
        int: Código de saída (0 para sucesso, 1 para erro)
        
    Raises:
        SystemExit: Em caso de erro crítico que impeça a execução
    """
    exit_code = 0
    
    try:
        # Fase 1: Interface inicial
        logger.info(f"=== Iniciando {settings.app_name} v{settings.app_version} ===")
        show_welcome_message()
        
        # Fase 2: Inicialização do sistema
        logger.info("Iniciando processo de inicialização do sistema")
        initialize_system()
        
        # Fase 3: Confirmação de inicialização
        console.print("✅ [green]Sistema inicializado com sucesso![/green]")
        console.print()
        logger.info("Sistema MeetingScribe totalmente operacional")
        
        # Fase 4: Interface principal
        show_main_menu()
        handle_menu_choice()
        
        logger.info("Aplicação encerrada normalmente")
        
    except KeyboardInterrupt:
        console.print("\n\n🛑 [yellow]Operação cancelada pelo usuário[/yellow]")
        logger.info("Sistema interrompido pelo usuário (Ctrl+C)")
        exit_code = 130  # Código padrão Unix para SIGINT
        
    except RuntimeError as e:
        # Erros de runtime específicos do sistema
        error_msg = f"Erro de execução: {str(e)}"
        console.print(f"\n❌ [red]{error_msg}[/red]")
        logger.error(error_msg)
        
        if hasattr(settings, 'debug') and settings.debug:
            console.print("\n📋 [dim]Detalhes técnicos:[/dim]")
            console.print(traceback.format_exc())
        
        _show_troubleshooting_tips()
        exit_code = 1
        
    except (ImportError, ModuleNotFoundError) as e:
        # Erros de dependências
        error_msg = f"Dependência ausente: {str(e)}"
        console.print(f"\n❌ [red]{error_msg}[/red]")
        logger.error(error_msg)
        
        console.print("\n💡 [yellow]Soluções sugeridas:[/yellow]")
        console.print("• Execute: pip install -r requirements.txt")
        console.print("• Verifique se está no ambiente virtual correto")
        console.print("• Execute: python system_check.py")
        
        exit_code = 2
        
    except Exception as e:
        # Catch-all para erros inesperados
        error_msg = f"Erro crítico inesperado: {str(e)}"
        console.print(f"\n❌ [red]{error_msg}[/red]")
        
        # Tentar logar se possível
        try:
            logger.critical(f"{error_msg}\n{traceback.format_exc()}")
        except Exception:
            pass  # Se logging falhar, não podemos fazer nada
        
        if hasattr(settings, 'debug') and settings.debug:
            console.print("\n📋 [dim]Stack trace completo:[/dim]")
            console.print(traceback.format_exc())
        
        _show_troubleshooting_tips()
        exit_code = 3
    
    finally:
        # Cleanup final
        try:
            logger.info(f"Encerrando MeetingScribe com código: {exit_code}")
        except Exception:
            pass  # Ignorar erros no cleanup
    
    return exit_code


def _show_troubleshooting_tips() -> None:
    """
    Exibe dicas de resolução de problemas para o usuário.
    
    Função auxiliar interna para mostrar informações de diagnóstico
    quando ocorrem erros no sistema.
    
    Returns:
        None
    """
    console.print("\n💡 [yellow]Dicas para resolução:[/yellow]")
    console.print("• Execute 'python system_check.py' para verificar o sistema")
    console.print("• Verifique se todas as dependências estão instaladas")
    console.print("• Consulte os logs em 'logs/meetingscribe.log'")
    console.print("• Verifique permissões de escrita nos diretórios")
    console.print("• Tente executar como administrador se necessário")

if __name__ == "__main__":
    sys.exit(main())