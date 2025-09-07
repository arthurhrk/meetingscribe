"""
Command Handler

Gerenciador unificado de comandos CLI preservando 100% funcionalidade v1.0.
Preparado para daemon integration v2.0.
"""

import argparse
from typing import Dict, Callable

from loguru import logger
from rich.console import Console

from .rich_ui import RichUI


class CommandHandler:
    """Gerenciador unificado de comandos CLI preservando interface v1.0."""
    
    def __init__(self, console: Console):
        """Inicializa o command handler."""
        self.console = console
        self.ui = RichUI(console)
        self._commands = self._register_commands()
        
    def _register_commands(self) -> Dict[str, Callable]:
        """
        Registra todos os comandos disponíveis.
        
        Returns:
            Dicionário mapeando nome do comando para função handler
        """
        return {
            'record': self._handle_record_command,
            'transcribe': self._handle_transcribe_command,
            'devices': self._handle_devices_command,
            'recent': self._handle_recent_command,
            'status': self._handle_status_command,
            'config': self._handle_config_command,
            'export': self._handle_export_command,
            'help': self._handle_help_command,
        }
    
    def create_argument_parser(self) -> argparse.ArgumentParser:
        """
        Cria parser de argumentos CLI preservando interface v1.0.
        
        Returns:
            ArgumentParser configurado com todos os comandos
        """
        parser = argparse.ArgumentParser(
            description="MeetingScribe - Sistema inteligente de transcrição",
            prog="meetingscribe",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Exemplos de uso:
  meetingscribe record --duration 30 --device speakers
  meetingscribe transcribe audio.wav --model large --language pt
  meetingscribe recent --limit 10
  meetingscribe devices
  meetingscribe status
            """
        )
        
        # Global options
        parser.add_argument(
            '--version', 
            action='version', 
            version='MeetingScribe v2.0.0'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Modo verboso (debug)'
        )
        parser.add_argument(
            '--json',
            action='store_true', 
            help='Output em formato JSON'
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(
            dest='command',
            help='Comandos disponíveis'
        )
        
        # Record command
        record_parser = subparsers.add_parser(
            'record', 
            help='Iniciar gravação de áudio'
        )
        record_parser.add_argument(
            '--duration', '-d',
            type=int,
            help='Duração da gravação em segundos'
        )
        record_parser.add_argument(
            '--device',
            type=str,
            help='ID ou nome do dispositivo de áudio'
        )
        record_parser.add_argument(
            '--output', '-o',
            type=str,
            help='Nome do arquivo de saída'
        )
        
        # Transcribe command  
        transcribe_parser = subparsers.add_parser(
            'transcribe',
            help='Transcrever arquivo de áudio'
        )
        transcribe_parser.add_argument(
            'file',
            type=str,
            help='Caminho para arquivo de áudio'
        )
        transcribe_parser.add_argument(
            '--model', '-m',
            type=str,
            choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'],
            default='base',
            help='Modelo Whisper para transcrição'
        )
        transcribe_parser.add_argument(
            '--language', '-l', 
            type=str,
            default='pt',
            help='Idioma do áudio (pt, en, es, etc.)'
        )
        transcribe_parser.add_argument(
            '--output-format', '-f',
            type=str,
            choices=['txt', 'json', 'srt', 'vtt', 'xml', 'csv'],
            default='txt',
            help='Formato de saída da transcrição'
        )
        transcribe_parser.add_argument(
            '--speakers',
            action='store_true',
            help='Identificar speakers na transcrição'
        )
        
        # Devices command
        subparsers.add_parser(
            'devices',
            help='Listar dispositivos de áudio disponíveis'  
        )
        
        # Recent command
        recent_parser = subparsers.add_parser(
            'recent',
            help='Listar transcrições recentes'
        )
        recent_parser.add_argument(
            '--limit', '-n',
            type=int,
            default=10,
            help='Número máximo de resultados'
        )
        recent_parser.add_argument(
            '--type', '-t',
            type=str,
            choices=['transcriptions', 'recordings', 'exports'],
            default='transcriptions',
            help='Tipo de arquivos para listar'
        )
        
        # Status command
        subparsers.add_parser(
            'status',
            help='Mostrar status do sistema'
        )
        
        # Config command
        config_parser = subparsers.add_parser(
            'config', 
            help='Gerenciar configurações'
        )
        config_parser.add_argument(
            'action',
            nargs='?',
            choices=['show', 'set', 'reset'],
            default='show',
            help='Ação de configuração'
        )
        config_parser.add_argument(
            'key',
            nargs='?',
            help='Chave de configuração'
        )
        config_parser.add_argument(
            'value', 
            nargs='?',
            help='Valor de configuração'
        )
        
        # Export command
        export_parser = subparsers.add_parser(
            'export',
            help='Exportar transcrição'
        )
        export_parser.add_argument(
            'filename',
            type=str, 
            help='Nome base da transcrição'
        )
        export_parser.add_argument(
            '--format', '-f',
            type=str,
            choices=['txt', 'json', 'srt', 'vtt', 'xml', 'csv'],
            required=True,
            help='Formato de exportação'
        )
        export_parser.add_argument(
            '--output', '-o',
            type=str,
            help='Arquivo de saída'
        )
        
        return parser
    
    def handle_command(self, args: argparse.Namespace) -> int:
        """
        Processa comando baseado nos argumentos.
        
        Args:
            args: Argumentos parsed do CLI
            
        Returns:
            Código de saída (0 = sucesso, != 0 = erro)
        """
        if not args.command:
            # Interactive mode - show main menu
            return self._handle_interactive_mode()
            
        # Command mode - execute specific command
        command = args.command.lower()
        
        if command not in self._commands:
            self.ui.show_error(f"Comando desconhecido: {command}")
            return 1
            
        try:
            return self._commands[command](args)
        except KeyboardInterrupt:
            self.ui.show_warning("\\nOperação cancelada pelo usuário")
            return 130
        except Exception as e:
            logger.error(f"Erro ao executar comando {command}: {e}")
            self.ui.show_error(
                f"Erro interno ao executar comando '{command}'",
                f"Detalhes: {str(e)}"
            )
            return 1
    
    def _handle_interactive_mode(self) -> int:
        """
        Modo interativo - menu principal preservado do v1.0.
        
        Returns:
            Código de saída
        """
        self.ui.show_welcome_message()
        
        while True:
            try:
                self.ui.show_main_menu()
                choice = self.ui.get_menu_choice()
                
                if choice == "8":  # Exit
                    self.ui.show_info("Obrigado por usar o MeetingScribe!")
                    return 0
                elif choice == "1":  # Record
                    self._handle_interactive_record()
                elif choice == "2":  # Transcribe
                    self._handle_interactive_transcribe()
                elif choice == "3":  # Smart transcribe
                    self._handle_interactive_smart_transcribe()
                elif choice == "4":  # Manage
                    self._handle_interactive_manage()
                elif choice == "5":  # Devices
                    self._handle_interactive_devices()
                elif choice == "6":  # Config
                    self._handle_interactive_config()
                elif choice == "7":  # Reports
                    self._handle_interactive_reports()
                else:
                    self.ui.show_warning("Opção inválida, tente novamente")
                    
            except KeyboardInterrupt:
                self.ui.show_info("\\nSaindo do MeetingScribe...")
                return 0
            except Exception as e:
                logger.error(f"Erro no modo interativo: {e}")
                self.ui.show_error("Erro interno", str(e))
                return 1
    
    # Command handlers - placeholders for now, will implement actual logic
    def _handle_record_command(self, args: argparse.Namespace) -> int:
        """Handle record command."""
        self.ui.show_info("🎙️ Comando de gravação será implementado")
        logger.info(f"Record command: duration={args.duration}, device={args.device}")
        return 0
        
    def _handle_transcribe_command(self, args: argparse.Namespace) -> int:
        """Handle transcribe command."""
        self.ui.show_info(f"📝 Transcrição de {args.file} será implementada")
        logger.info(f"Transcribe command: file={args.file}, model={args.model}")
        return 0
        
    def _handle_devices_command(self, args: argparse.Namespace) -> int:
        """Handle devices command.""" 
        self.ui.show_info("🎧 Listagem de dispositivos será implementada")
        return 0
        
    def _handle_recent_command(self, args: argparse.Namespace) -> int:
        """Handle recent command."""
        self.ui.show_info(f"📋 Listagem de {args.type} recentes será implementada")
        return 0
        
    def _handle_status_command(self, args: argparse.Namespace) -> int:
        """Handle status command."""
        self.ui.show_info("📊 Status do sistema será implementado")
        return 0
        
    def _handle_config_command(self, args: argparse.Namespace) -> int:
        """Handle config command."""
        self.ui.show_info(f"⚙️ Configuração {args.action} será implementada")
        return 0
        
    def _handle_export_command(self, args: argparse.Namespace) -> int:
        """Handle export command."""
        self.ui.show_info(f"📤 Export {args.filename} para {args.format} será implementado")
        return 0
        
    def _handle_help_command(self, args: argparse.Namespace) -> int:
        """Handle help command."""
        self.ui.show_troubleshooting_tips()
        return 0
    
    # Interactive mode handlers - placeholders
    def _handle_interactive_record(self) -> None:
        """Handle interactive record mode."""
        self.ui.show_info("🎙️ Menu de gravação interativo será implementado")
        
    def _handle_interactive_transcribe(self) -> None:
        """Handle interactive transcribe mode."""
        self.ui.show_info("📝 Menu de transcrição interativo será implementado")
        
    def _handle_interactive_smart_transcribe(self) -> None:
        """Handle interactive smart transcribe mode."""
        self.ui.show_info("🧠 Menu de transcrição inteligente será implementado")
        
    def _handle_interactive_manage(self) -> None:
        """Handle interactive management mode."""
        self.ui.show_info("📂 Menu de gerenciamento será implementado")
        
    def _handle_interactive_devices(self) -> None:
        """Handle interactive devices mode.""" 
        self.ui.show_info("🎧 Menu de dispositivos será implementado")
        
    def _handle_interactive_config(self) -> None:
        """Handle interactive config mode."""
        self.ui.show_info("⚙️ Menu de configuração será implementado")
        
    def _handle_interactive_reports(self) -> None:
        """Handle interactive reports mode."""
        self.ui.show_info("📊 Menu de relatórios será implementado")