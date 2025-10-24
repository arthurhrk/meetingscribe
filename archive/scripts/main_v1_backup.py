"""
MeetingScribe - Entry Point Principal

Sistema de transcrição inteligente para reuniões usando OpenAI Whisper.
Processamento 100% local com identificação de speakers e interface Rica.

Author: MeetingScribe Team
Version: 1.0.0
Python: >=3.8
"""

import sys
import time
import traceback
import argparse
import json
from datetime import datetime
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
    from device_manager import DeviceManager, AudioDeviceError, WASAPINotAvailableError
    from audio_recorder import AudioRecorder, create_recorder_from_config, AudioRecorderError, RecordingInProgressError
    from src.transcription import (
        create_transcriber, WhisperModelSize, TranscriptionProgress,
        export_transcription, ExportFormat, TranscriptionError,
        create_intelligent_transcriber, IntelligentProgress, transcribe_with_speakers,
        SpeakerDetectionError, ModelNotAvailableError, save_transcription_txt
    )
    from src.core import (
        create_settings_manager, get_system_info, PerformanceLevel,
        MeetingScribeConfig, PresetType
    )
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
        welcome_text.append("[MIC] ", style="bold blue")
        welcome_text.append("MeetingScribe", style="bold blue")
        welcome_text.append(f" v{settings.app_version}", style="dim")
        welcome_text.append("\n\nSistema inteligente de transcrição de reuniões", style="white")
        welcome_text.append("\nPowered by OpenAI Whisper", style="dim")
        
        panel = Panel(
            welcome_text,
            title="[TARGET] Bem-vindo",
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
        Algumas opções são funcionais, outras são placeholders para desenvolvimento futuro.
    """
    menu_options = [
        "1. [MIC]    Iniciar nova gravacao",
        "2. [FILE]   Transcrever arquivo existente", 
        "3. [SPEAKER] Transcricao inteligente com identificacao de speakers",
        "4. [FOLDER] Gerenciar transcricoes",
        "5. [AUDIO]  Dispositivos de audio",
        "6. [CONFIG] Configuracoes",
        "7. [REPORT] Relatorios",
        "8. [EXIT]   Sair"
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

def show_recording_menu() -> None:
    """
    Exibe menu de gravação de áudio com controle interativo.
    
    Permite iniciar, parar e monitorar gravações em tempo real
    usando dispositivos WASAPI detectados automaticamente.
    
    Returns:
        None
    """
    logger.info("Usuário acessou menu de gravação")
    
    try:
        console.print(Panel(
            "[bold cyan]Sistema de Gravacao de Audio[/bold cyan]\n"
            "Pressione Ctrl+C a qualquer momento para cancelar",
            title="[MIC] Gravacao de Audio",
            border_style="cyan"
        ))
        
        with create_recorder_from_config() as recorder:
            # Mostrar dispositivo configurado
            if recorder._config:
                console.print(f"\n[bold blue]Dispositivo Configurado:[/bold blue]")
                console.print(f"[green][OK][/green] {recorder._config.device.name}")
                console.print(f"     API: {recorder._config.device.host_api}")
                console.print(f"     Taxa: {recorder._config.sample_rate} Hz")
                console.print(f"     Canais: {recorder._config.channels}")
                console.print(f"     Loopback: {'Sim' if recorder._config.device.is_loopback else 'Nao'}")
            else:
                console.print("[red][ERROR][/red] Nenhum dispositivo configurado")
                return
            
            # Obter nome do arquivo
            console.print(f"\n[bold blue]Configuracao da Gravacao:[/bold blue]")
            filename = Prompt.ask(
                "Nome do arquivo (sem extensao)",
                default=f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Duração máxima opcional
            duration_str = Prompt.ask(
                "Duracao maxima em segundos (Enter = sem limite)",
                default=""
            )
            
            max_duration = None
            if duration_str.strip():
                try:
                    max_duration = int(duration_str)
                    recorder._config.max_duration = max_duration
                except ValueError:
                    console.print("[yellow][WARN][/yellow] Duracao invalida, usando sem limite")
            
            # Confirmar início
            if not Confirm.ask(f"\nIniciar gravacao '{filename}'?"):
                console.print("[yellow][CANCELLED][/yellow] Gravacao cancelada pelo usuario")
                return
            
            # Iniciar gravação
            console.print(f"\n[bold green]Iniciando gravacao...[/bold green]")
            
            def progress_callback(duration: float):
                mins, secs = divmod(int(duration), 60)
                print(f"\r[bold blue]Gravando:[/bold blue] {mins:02d}:{secs:02d}", end="", flush=True)
            
            try:
                filepath = recorder.start_recording(filename, progress_callback)
                
                console.print(f"[green][OK][/green] Gravacao iniciada!")
                console.print(f"Arquivo: {filepath}")
                
                if max_duration:
                    console.print(f"Duracao maxima: {max_duration} segundos")
                
                console.print(f"\n[bold yellow]Pressione Enter para parar a gravacao...[/bold yellow]")
                
                # Aguardar input do usuário ou duração máxima
                import select
                import sys
                
                start_time = time.time()
                
                while recorder.is_recording():
                    # Verificar se há input disponível (apenas em sistemas Unix-like)
                    if sys.platform != "win32":
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            input()
                            break
                    else:
                        # Para Windows, usar uma abordagem diferente
                        try:
                            import msvcrt
                            if msvcrt.kbhit():
                                if msvcrt.getch() == b'\r':  # Enter
                                    break
                        except ImportError:
                            # Fallback: aguardar por tempo ou input
                            time.sleep(0.1)
                    
                    # Atualizar progresso
                    current_time = time.time()
                    duration = current_time - start_time
                    progress_callback(duration)
                    
                    # Verificar duração máxima
                    if max_duration and duration >= max_duration:
                        break
                    
                    time.sleep(0.1)
                
                # Parar gravação
                console.print(f"\n\n[bold blue]Parando gravacao...[/bold blue]")
                stats = recorder.stop_recording()
                
                # Mostrar resultados
                console.print(f"[green][SUCCESS][/green] Gravacao concluida!")
                console.print(f"\n[bold blue]Estatisticas:[/bold blue]")
                console.print(f"Arquivo: {stats.filename}")
                console.print(f"Duracao: {stats.duration:.2f} segundos")
                console.print(f"Tamanho: {stats.file_size:,} bytes")
                console.print(f"Inicio: {stats.start_time.strftime('%H:%M:%S')}")
                console.print(f"Fim: {stats.end_time.strftime('%H:%M:%S')}")
                
            except RecordingInProgressError:
                console.print("[red][ERROR][/red] Ja existe uma gravacao em andamento")
                
            except KeyboardInterrupt:
                console.print(f"\n\n[yellow][CANCELLED][/yellow] Gravacao cancelada pelo usuario")
                if recorder.is_recording():
                    try:
                        stats = recorder.stop_recording()
                        console.print(f"Gravacao parcial salva: {stats.filename}")
                    except Exception as e:
                        logger.warning(f"Erro ao salvar gravação cancelada: {e}")
                
    except AudioRecorderError as e:
        logger.error(f"Erro no gravador: {e}")
        console.print(f"[red][ERROR][/red] Erro no gravador: {e}")
        
    except Exception as e:
        logger.error(f"Erro inesperado no menu de gravação: {e}")
        console.print(f"[red][ERROR][/red] Erro inesperado: {e}")
    
    # Pausa para o usuário ver as informações
    console.print(f"\n[dim]Pressione Enter para continuar...[/dim]")
    input()


def show_audio_devices_menu() -> None:
    """
    Exibe menu de dispositivos de áudio com detecção automática.
    
    Utiliza o DeviceManager para listar e detectar dispositivos disponíveis,
    com foco em dispositivos WASAPI loopback para gravação.
    
    Returns:
        None
    """
    logger.info("Usuário acessou menu de dispositivos de áudio")
    
    try:
        console.print(Panel(
            "[bold cyan]Detectando dispositivos de audio...[/bold cyan]",
            title="[AUDIO] Dispositivos de Audio",
            border_style="cyan"
        ))
        
        with DeviceManager() as dm:
            # Detectar dispositivo padrão
            console.print("\n[bold blue]Dispositivo Padrao de Speakers:[/bold blue]")
            default_speakers = dm.get_default_speakers()
            
            if default_speakers:
                console.print(f"[green][OK][/green] {default_speakers.name}")
                console.print(f"     API: {default_speakers.host_api}")
                console.print(f"     Canais: {default_speakers.max_output_channels} saida, {default_speakers.max_input_channels} entrada")
                console.print(f"     Taxa: {default_speakers.default_sample_rate} Hz")
                console.print(f"     Loopback: {'Sim' if default_speakers.is_loopback else 'Nao'}")
            else:
                console.print("[red][ERROR][/red] Nenhum dispositivo padrao encontrado")
            
            # Listar dispositivos WASAPI
            console.print(f"\n[bold blue]Dispositivos WASAPI Disponiveis:[/bold blue]")
            wasapi_devices = dm.get_devices_by_api('Windows WASAPI')
            
            if wasapi_devices:
                for device in wasapi_devices:
                    status_tags = []
                    if device.is_loopback:
                        status_tags.append("[green][LOOP][/green]")
                    if device.is_default:
                        status_tags.append("[yellow][DEFAULT][/yellow]")
                    
                    status = " ".join(status_tags) if status_tags else ""
                    
                    console.print(f"[{device.index:2d}] {device.name}")
                    if status:
                        console.print(f"     Status: {status}")
                    console.print(f"     In: {device.max_input_channels} | Out: {device.max_output_channels}")
                    
            else:
                console.print("[red][ERROR][/red] Nenhum dispositivo WASAPI encontrado")
            
            # Mostrar total de dispositivos
            all_devices = dm.list_all_devices()
            console.print(f"\n[dim]Total: {len(all_devices)} dispositivos detectados no sistema[/dim]")
            
    except WASAPINotAvailableError:
        logger.warning("WASAPI não disponível para o usuário")
        console.print("[red][ERROR][/red] WASAPI nao disponivel - funcionalidades limitadas")
        console.print("Instale drivers de audio atualizados ou execute como administrador")
        
    except AudioDeviceError as e:
        logger.error(f"Erro no sistema de áudio: {e}")
        console.print(f"[red][ERROR][/red] Erro no sistema de audio: {e}")
        
    except Exception as e:
        logger.error(f"Erro inesperado no menu de áudio: {e}")
        console.print(f"[red][ERROR][/red] Erro inesperado: {e}")
    
    # Pausa para o usuário ver as informações
    console.print(f"\n[dim]Pressione Enter para continuar...[/dim]")
    input()


def show_transcription_menu() -> None:
    """
    Exibe menu de transcrição de arquivos de áudio existentes.
    
    Permite selecionar arquivos de áudio, escolher modelo Whisper
    e configurar opções de transcrição e exportação.
    
    Returns:
        None
    """
    logger.info("Usuário acessou menu de transcrição")
    
    try:
        console.print(Panel(
            "[bold cyan]Sistema de Transcricao de Audio[/bold cyan]\n"
            "Transcreva arquivos de audio existentes usando IA",
            title="[FILE] Transcricao de Arquivos",
            border_style="cyan"
        ))
        
        # Solicitar arquivo de áudio
        console.print(f"\n[bold blue]Selecao do Arquivo:[/bold blue]")
        
        # Verificar diretório de gravações
        recordings_dir = Path(settings.base_dir) / "storage" / "recordings"
        if recordings_dir.exists():
            recordings = list(recordings_dir.glob("*.wav"))
            if recordings:
                console.print(f"[green][INFO][/green] Encontradas {len(recordings)} gravacoes:")
                for i, recording in enumerate(recordings, 1):
                    size_mb = recording.stat().st_size / (1024 * 1024)
                    console.print(f"  {i}. {recording.name} ({size_mb:.1f} MB)")
                
                choice = Prompt.ask(
                    "Use uma gravacao existente? (Digite o numero ou 'N' para outro arquivo)",
                    default="N"
                )
                
                if choice.isdigit() and 1 <= int(choice) <= len(recordings):
                    audio_file = recordings[int(choice) - 1]
                else:
                    audio_file = None
            else:
                audio_file = None
        else:
            audio_file = None
        
        # Se não escolheu gravação existente, solicitar caminho
        if audio_file is None:
            file_path = Prompt.ask("Caminho completo do arquivo de audio")
            audio_file = Path(file_path)
            
            if not audio_file.exists():
                console.print(f"[red][ERROR][/red] Arquivo nao encontrado: {audio_file}")
                return
        
        console.print(f"[green][OK][/green] Arquivo selecionado: {audio_file.name}")
        file_size = audio_file.stat().st_size / (1024 * 1024)
        console.print(f"Tamanho: {file_size:.1f} MB")
        
        # Configuração do modelo
        console.print(f"\n[bold blue]Configuracao do Modelo:[/bold blue]")
        
        model_choices = {
            "1": ("tiny", "Mais rápido, menor precisão"),
            "2": ("base", "Equilibrio entre velocidade e precisão"),  
            "3": ("small", "Boa precisão, velocidade média"),
            "4": ("medium", "Alta precisão, mais lento"),
            "5": ("large-v3", "Máxima precisão, muito lento")
        }
        
        for key, (model, desc) in model_choices.items():
            console.print(f"  {key}. {model.upper()}: {desc}")
        
        model_choice = Prompt.ask(
            "Escolha o modelo Whisper",
            choices=list(model_choices.keys()),
            default="2"
        )
        
        model_name = model_choices[model_choice][0]
        model_size = WhisperModelSize(model_name)
        
        # Idioma (opcional)
        language = Prompt.ask(
            "Idioma do audio (Enter = auto-deteccao, ex: 'pt', 'en')",
            default=""
        ).strip()
        
        if not language:
            language = None
        
        # Configurar progresso
        console.print(f"\n[bold green]Iniciando transcricao...[/bold green]")
        console.print(f"Modelo: {model_name.upper()}")
        console.print(f"Idioma: {language or 'Auto-deteccao'}")
        console.print(f"Arquivo: {audio_file.name}")
        
        def progress_callback(progress: float, status: str):
            percentage = int(progress * 100)
            bar_length = 30
            filled_length = int(bar_length * progress)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            print(f"\r[bold blue]Progresso:[/bold blue] [{bar}] {percentage:3d}% | {status}", end="", flush=True)
        
        try:
            # Executar transcrição
            with create_transcriber(model_size, language) as transcriber:
                progress = TranscriptionProgress(progress_callback)
                result = transcriber.transcribe_file(audio_file, progress, language)
            
            # Mostrar resultados
            console.print(f"\n\n[green][SUCCESS][/green] Transcricao concluida!")
            console.print(f"\n[bold blue]Resultados:[/bold blue]")
            console.print(f"Idioma detectado: {result.language}")
            console.print(f"Duracao: {result.duration:.1f} segundos")
            console.print(f"Segmentos: {len(result.segments)}")
            console.print(f"Palavras: {result.word_count}")
            console.print(f"Confianca media: {result.confidence_avg:.2f}")
            console.print(f"Tempo de processamento: {result.processing_time:.1f}s")
            
            # Mostrar prévia do texto
            console.print(f"\n[bold blue]Previa do Texto:[/bold blue]")
            preview = result.full_text[:200] + "..." if len(result.full_text) > 200 else result.full_text
            console.print(Panel(preview, border_style="dim"))
            
            # Perguntar sobre exportação
            if Confirm.ask("\nDeseja exportar a transcricao?"):
                # Configurar exportação
                export_formats = {
                    "1": ("txt", "Texto simples"),
                    "2": ("json", "JSON estruturado"),
                    "3": ("srt", "Legenda SRT"),
                    "4": ("vtt", "Legenda WebVTT")
                }
                
                console.print(f"\n[bold blue]Formatos de Exportacao:[/bold blue]")
                for key, (fmt, desc) in export_formats.items():
                    console.print(f"  {key}. {fmt.upper()}: {desc}")
                
                format_choice = Prompt.ask(
                    "Escolha o formato",
                    choices=list(export_formats.keys()),
                    default="1"
                )
                
                export_format_name = export_formats[format_choice][0]
                export_format = ExportFormat(export_format_name)
                
                # Nome do arquivo de saída
                default_name = audio_file.stem + "_transcricao"
                output_name = Prompt.ask(
                    "Nome do arquivo de saida (sem extensao)",
                    default=default_name
                )
                
                # Diretório de saída
                output_dir = Path(settings.base_dir) / "storage" / "transcriptions"
                output_path = output_dir / output_name
                
                # Exportar
                console.print(f"\n[bold blue]Exportando...[/bold blue]")
                final_path = export_transcription(result, output_path, export_format)
                
                console.print(f"[green][SUCCESS][/green] Transcricao exportada!")
                console.print(f"Arquivo: {final_path}")
                
                # Opção de abrir arquivo
                if Confirm.ask("Abrir o arquivo agora?", default=False):
                    try:
                        import os
                        os.startfile(str(final_path))  # Windows
                    except (ImportError, AttributeError):
                        try:
                            import subprocess
                            subprocess.run(["xdg-open", str(final_path)])  # Linux
                        except FileNotFoundError:
                            console.print("[yellow][WARN][/yellow] Nao foi possivel abrir o arquivo automaticamente")
        
        except TranscriptionError as e:
            console.print(f"\n[red][ERROR][/red] Erro na transcricao: {e}")
            logger.error(f"Erro na transcrição: {e}")
        
        except KeyboardInterrupt:
            console.print(f"\n\n[yellow][CANCELLED][/yellow] Transcricao cancelada pelo usuario")
            logger.info("Transcrição cancelada pelo usuário")
        
        except Exception as e:
            console.print(f"\n[red][ERROR][/red] Erro inesperado: {e}")
            logger.error(f"Erro inesperado na transcrição: {e}")
    
    except Exception as e:
        logger.error(f"Erro inesperado no menu de transcrição: {e}")
        console.print(f"[red][ERROR][/red] Erro no menu: {e}")
    
    # Pausa para o usuário ver as informações
    console.print(f"\n[dim]Pressione Enter para continuar...[/dim]")
    input()


def show_transcription_manager() -> None:
    """
    Exibe gerenciador de transcrições existentes.
    
    Permite visualizar, abrir, exportar e deletar transcrições
    armazenadas no sistema.
    
    Returns:
        None
    """
    logger.info("Usuário acessou gerenciador de transcrições")
    
    try:
        console.print(Panel(
            "[bold cyan]Gerenciador de Transcricoes[/bold cyan]\n"
            "Visualize e gerencie suas transcricoes existentes",
            title="[FOLDER] Gerenciador de Transcricoes",
            border_style="cyan"
        ))
        
        # Verificar diretórios
        transcriptions_dir = Path(settings.base_dir) / "storage" / "transcriptions"
        recordings_dir = Path(settings.base_dir) / "storage" / "recordings"
        
        # Buscar transcrições
        transcription_files = []
        if transcriptions_dir.exists():
            for ext in ["*.txt", "*.json", "*.srt", "*.vtt"]:
                transcription_files.extend(list(transcriptions_dir.glob(ext)))
        
        # Buscar gravações
        recording_files = []
        if recordings_dir.exists():
            recording_files = list(recordings_dir.glob("*.wav"))
        
        if not transcription_files and not recording_files:
            console.print("\n[yellow][INFO][/yellow] Nenhuma transcrição ou gravação encontrada.")
            console.print("Execute uma gravação ou transcrição primeiro.")
            return
        
        while True:
            console.print(f"\n[bold blue]Opcoes Disponiveis:[/bold blue]")
            console.print("1. [FOLDER] Listar transcricoes")
            console.print("2. [FILE] Listar gravacoes")
            console.print("3. [SEARCH] Buscar por nome")
            console.print("4. [CLEAN] Limpar arquivos antigos")
            console.print("5. [REPORT] Estatisticas")
            console.print("6. [EXIT] Voltar ao menu principal")
            
            choice = Prompt.ask(
                "Escolha uma opcao",
                choices=["1", "2", "3", "4", "5", "6"],
                default="6"
            )
            
            if choice == "1":
                _show_transcription_list(transcriptions_dir)
            elif choice == "2":
                _show_recordings_list(recordings_dir)
            elif choice == "3":
                _search_files(transcriptions_dir, recordings_dir)
            elif choice == "4":
                _cleanup_old_files(transcriptions_dir, recordings_dir)
            elif choice == "5":
                _show_statistics(transcriptions_dir, recordings_dir)
            elif choice == "6":
                break
    
    except Exception as e:
        logger.error(f"Erro no gerenciador de transcrições: {e}")
        console.print(f"[red][ERROR][/red] Erro no gerenciador: {e}")
    
    # Pausa para o usuário ver as informações
    console.print(f"\n[dim]Pressione Enter para continuar...[/dim]")
    input()


def _show_transcription_list(transcriptions_dir: Path) -> None:
    """Lista transcrições existentes."""
    if not transcriptions_dir.exists():
        console.print("[yellow][INFO][/yellow] Diretório de transcrições não existe.")
        return
    
    files = {}
    for ext in ["*.txt", "*.json", "*.srt", "*.vtt"]:
        for file in transcriptions_dir.glob(ext):
            files[file.name] = file
    
    if not files:
        console.print("[yellow][INFO][/yellow] Nenhuma transcrição encontrada.")
        return
    
    console.print(f"\n[bold blue]Transcricoes Encontradas ({len(files)}):[/bold blue]")
    
    for i, (name, path) in enumerate(sorted(files.items()), 1):
        size_kb = path.stat().st_size / 1024
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        console.print(f"  {i:2d}. {name}")
        console.print(f"      Tamanho: {size_kb:.1f} KB | Modificado: {modified.strftime('%d/%m/%Y %H:%M')}")
    
    # Opções de ação
    if Confirm.ask("\nDeseja abrir alguma transcrição?"):
        choice = Prompt.ask(f"Digite o número (1-{len(files)})")
        
        if choice.isdigit() and 1 <= int(choice) <= len(files):
            selected_file = list(files.values())[int(choice) - 1]
            
            try:
                import os
                os.startfile(str(selected_file))  # Windows
                console.print(f"[green][OK][/green] Abrindo: {selected_file.name}")
            except (ImportError, AttributeError):
                try:
                    import subprocess
                    subprocess.run(["xdg-open", str(selected_file)])  # Linux
                    console.print(f"[green][OK][/green] Abrindo: {selected_file.name}")
                except FileNotFoundError:
                    console.print(f"[yellow][WARN][/yellow] Não foi possível abrir automaticamente")
                    console.print(f"Caminho: {selected_file}")


def _show_recordings_list(recordings_dir: Path) -> None:
    """Lista gravações existentes."""
    if not recordings_dir.exists():
        console.print("[yellow][INFO][/yellow] Diretório de gravações não existe.")
        return
    
    recordings = list(recordings_dir.glob("*.wav"))
    if not recordings:
        console.print("[yellow][INFO][/yellow] Nenhuma gravação encontrada.")
        return
    
    console.print(f"\n[bold blue]Gravacoes Encontradas ({len(recordings)}):[/bold blue]")
    
    for i, recording in enumerate(sorted(recordings), 1):
        size_mb = recording.stat().st_size / (1024 * 1024)
        modified = datetime.fromtimestamp(recording.stat().st_mtime)
        console.print(f"  {i:2d}. {recording.name}")
        console.print(f"      Tamanho: {size_mb:.1f} MB | Modificado: {modified.strftime('%d/%m/%Y %H:%M')}")
    
    # Opção de transcrever
    if Confirm.ask("\nDeseja transcrever alguma gravação?"):
        choice = Prompt.ask(f"Digite o número (1-{len(recordings)})")
        
        if choice.isdigit() and 1 <= int(choice) <= len(recordings):
            selected_recording = recordings[int(choice) - 1]
            console.print(f"[green][OK][/green] Redirecionando para transcrição de: {selected_recording.name}")
            # Aqui poderia integrar com o menu de transcrição
            show_transcription_menu()


def _search_files(transcriptions_dir: Path, recordings_dir: Path) -> None:
    """Busca arquivos por nome."""
    search_term = Prompt.ask("Digite o termo de busca").lower()
    
    found_files = []
    
    # Buscar transcrições
    if transcriptions_dir.exists():
        for ext in ["*.txt", "*.json", "*.srt", "*.vtt"]:
            for file in transcriptions_dir.glob(ext):
                if search_term in file.name.lower():
                    found_files.append(("Transcrição", file))
    
    # Buscar gravações
    if recordings_dir.exists():
        for file in recordings_dir.glob("*.wav"):
            if search_term in file.name.lower():
                found_files.append(("Gravação", file))
    
    if not found_files:
        console.print(f"[yellow][INFO][/yellow] Nenhum arquivo encontrado com '{search_term}'.")
        return
    
    console.print(f"\n[bold blue]Resultados da Busca '{search_term}' ({len(found_files)}):[/bold blue]")
    
    for i, (file_type, path) in enumerate(found_files, 1):
        size = path.stat().st_size / (1024 * 1024 if file_type == "Gravação" else 1024)
        unit = "MB" if file_type == "Gravação" else "KB"
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        
        console.print(f"  {i:2d}. [{file_type}] {path.name}")
        console.print(f"      Tamanho: {size:.1f} {unit} | Modificado: {modified.strftime('%d/%m/%Y %H:%M')}")


def _cleanup_old_files(transcriptions_dir: Path, recordings_dir: Path) -> None:
    """Remove arquivos antigos."""
    from datetime import timedelta
    
    days = Prompt.ask("Remover arquivos mais antigos que quantos dias?", default="30")
    
    try:
        days_threshold = int(days)
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        old_files = []
        
        # Verificar transcrições
        if transcriptions_dir.exists():
            for ext in ["*.txt", "*.json", "*.srt", "*.vtt"]:
                for file in transcriptions_dir.glob(ext):
                    if datetime.fromtimestamp(file.stat().st_mtime) < cutoff_date:
                        old_files.append(file)
        
        # Verificar gravações
        if recordings_dir.exists():
            for file in recordings_dir.glob("*.wav"):
                if datetime.fromtimestamp(file.stat().st_mtime) < cutoff_date:
                    old_files.append(file)
        
        if not old_files:
            console.print(f"[green][OK][/green] Nenhum arquivo mais antigo que {days_threshold} dias encontrado.")
            return
        
        console.print(f"\n[yellow][WARN][/yellow] Encontrados {len(old_files)} arquivos antigos:")
        
        total_size = 0
        for file in old_files:
            size_mb = file.stat().st_size / (1024 * 1024)
            total_size += size_mb
            console.print(f"  • {file.name} ({size_mb:.1f} MB)")
        
        console.print(f"\nEspaço total a ser liberado: {total_size:.1f} MB")
        
        if Confirm.ask("Confirma a remoção destes arquivos?", default=False):
            removed_count = 0
            for file in old_files:
                try:
                    file.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Erro ao remover {file.name}: {e}")
            
            console.print(f"[green][OK][/green] {removed_count} arquivos removidos com sucesso.")
            if removed_count < len(old_files):
                console.print(f"[yellow][WARN][/yellow] {len(old_files) - removed_count} arquivos não puderam ser removidos.")
    
    except ValueError:
        console.print("[red][ERROR][/red] Número de dias inválido.")


def _show_statistics(transcriptions_dir: Path, recordings_dir: Path) -> None:
    """Mostra estatísticas dos arquivos."""
    stats = {
        "transcriptions": {"count": 0, "size": 0, "types": {}},
        "recordings": {"count": 0, "size": 0}
    }
    
    # Estatísticas de transcrições
    if transcriptions_dir.exists():
        for ext in ["*.txt", "*.json", "*.srt", "*.vtt"]:
            files = list(transcriptions_dir.glob(ext))
            ext_clean = ext[2:]  # Remove *.
            stats["transcriptions"]["types"][ext_clean] = len(files)
            
            for file in files:
                stats["transcriptions"]["count"] += 1
                stats["transcriptions"]["size"] += file.stat().st_size
    
    # Estatísticas de gravações
    if recordings_dir.exists():
        for file in recordings_dir.glob("*.wav"):
            stats["recordings"]["count"] += 1
            stats["recordings"]["size"] += file.stat().st_size
    
    console.print(f"\n[bold blue]Estatisticas do Sistema:[/bold blue]")
    
    # Transcrições
    trans_size_mb = stats["transcriptions"]["size"] / (1024 * 1024)
    console.print(f"\n📄 Transcrições:")
    console.print(f"   Total: {stats['transcriptions']['count']} arquivos ({trans_size_mb:.1f} MB)")
    
    for file_type, count in stats["transcriptions"]["types"].items():
        if count > 0:
            console.print(f"   • {file_type.upper()}: {count} arquivos")
    
    # Gravações
    rec_size_mb = stats["recordings"]["size"] / (1024 * 1024)
    console.print(f"\n🎵 Gravações:")
    console.print(f"   Total: {stats['recordings']['count']} arquivos ({rec_size_mb:.1f} MB)")
    
    # Total
    total_count = stats["transcriptions"]["count"] + stats["recordings"]["count"]
    total_size_mb = trans_size_mb + rec_size_mb
    
    console.print(f"\n📊 Resumo Geral:")
    console.print(f"   Arquivos totais: {total_count}")
    console.print(f"   Espaço utilizado: {total_size_mb:.1f} MB")
    
    if total_size_mb > 1024:
        console.print(f"   Espaço utilizado: {total_size_mb / 1024:.1f} GB")


def show_intelligent_transcription_menu() -> None:
    """
    Exibe menu de transcrição inteligente com detecção de speakers.
    
    Sistema completo que combina Whisper + pyannote.audio para:
    - Transcrição de alta qualidade
    - Identificação automática de speakers
    - Rotulagem inteligente de participantes
    - Separação por vozes únicas
    
    Returns:
        None
    """
    logger.info("Usuário acessou menu de transcrição inteligente com speaker detection")
    
    try:
        # Verificar capacidades do sistema
        settings_manager = create_settings_manager()
        system_info = get_system_info()
        can_use_speakers = system_info["can_use_speakers"]
        
        console.print(Panel(
            "[bold cyan]🎤 Transcrição Inteligente com Speaker Detection[/bold cyan]\n\n"
            "Sistema avançado que combina:\n"
            "• [bold green]OpenAI Whisper[/bold green] - Transcrição de alta qualidade\n"
            "• [bold blue]pyannote.audio[/bold blue] - Identificação de speakers\n"
            "• [bold yellow]IA Híbrida[/bold yellow] - Rotulagem automática de participantes\n\n"
            f"Status do Sistema: {'[green]✓ Compatível[/green]' if can_use_speakers else '[red]⚠ Limitado[/red]'}\n"
            f"Preset Recomendado: [bold]{system_info['recommended_preset'].title()}[/bold]",
            title="🧠 [SPEAKER] Sistema de IA Híbrida",
            border_style="cyan"
        ))
        
        # Solicitar arquivo de áudio
        console.print(f"\n[bold blue]Selecao do Arquivo:[/bold blue]")
        
        # Verificar diretório de gravações
        recordings_dir = Path(settings.base_dir) / "storage" / "recordings"
        if recordings_dir.exists():
            recordings = list(recordings_dir.glob("*.wav"))
            if recordings:
                console.print(f"[green][INFO][/green] Encontradas {len(recordings)} gravacoes:")
                for i, recording in enumerate(recordings, 1):
                    size_mb = recording.stat().st_size / (1024 * 1024)
                    console.print(f"  {i}. {recording.name} ({size_mb:.1f} MB)")
                
                choice = Prompt.ask(
                    "Use uma gravacao existente? (Digite o numero ou 'N' para outro arquivo)",
                    default="N"
                )
                
                if choice.isdigit() and 1 <= int(choice) <= len(recordings):
                    audio_file = recordings[int(choice) - 1]
                else:
                    audio_file = None
            else:
                audio_file = None
        else:
            audio_file = None
        
        # Se não escolheu gravação existente, solicitar caminho
        if audio_file is None:
            file_path = Prompt.ask("Caminho completo do arquivo de audio")
            audio_file = Path(file_path)
            
            if not audio_file.exists():
                console.print(f"[red][ERROR][/red] Arquivo nao encontrado: {audio_file}")
                return
        
        console.print(f"[green][OK][/green] Arquivo selecionado: {audio_file.name}")
        file_size = audio_file.stat().st_size / (1024 * 1024)
        console.print(f"Tamanho: {file_size:.1f} MB")
        
        # Configuração do modelo Whisper com sistema inteligente
        console.print(f"\n[bold blue]🤖 Configuração Inteligente do Modelo:[/bold blue]")
        
        # Carregar configuração atual
        current_config = settings_manager.get_current_config()
        recommended_model = system_info["recommended_preset"]
        
        console.print(f"[dim]Hardware detectado: {system_info['cpu']['name']}[/dim]")
        console.print(f"[dim]Performance Level: {system_info['performance_level'].upper()}[/dim]")
        console.print(f"[dim]Memória disponível: {system_info['memory']['available']}[/dim]")
        
        model_choices = {
            "1": ("tiny", "🚀 Mais rápido, menor precisão (~1x)", "Para testes rápidos"),
            "2": ("base", "⚖️ Equilibrio velocidade/precisão (~3x)", "Recomendado geral"),  
            "3": ("small", "🎯 Boa precisão, velocidade média (~5x)", "Boa qualidade"),
            "4": ("medium", "💎 Alta precisão, mais lento (~8x)", "Qualidade profissional"),
            "5": ("large-v3", "🏆 Máxima precisão, muito lento (~15x)", "Máxima qualidade")
        }
        
        console.print(f"\n[yellow]Modelo recomendado para seu sistema: {current_config.whisper.model_size.upper()}[/yellow]")
        
        for key, (model, speed_desc, use_case) in model_choices.items():
            marker = " [bold green]← RECOMENDADO[/bold green]" if model == current_config.whisper.model_size else ""
            console.print(f"  {key}. {speed_desc}{marker}")
            console.print(f"     [dim]Uso: {use_case}[/dim]")
        
        model_choice = Prompt.ask(
            "Escolha o modelo Whisper",
            choices=list(model_choices.keys()),
            default="2"
        )
        
        model_name = model_choices[model_choice][0]
        model_size = WhisperModelSize(model_name)
        
        # Idioma (opcional)
        language = Prompt.ask(
            "Idioma do audio (Enter = auto-deteccao, ex: 'pt', 'en')",
            default=""
        ).strip()
        
        if not language:
            language = None
        
        # Configurações de Speaker Detection com IA
        console.print(f"\n[bold blue]🗣️ Configuração de Speaker Detection:[/bold blue]")
        
        if not can_use_speakers:
            console.print("[red]⚠ AVISO:[/red] Seu sistema tem memória limitada para speaker detection")
            console.print("[dim]Recomendamos pelo menos 4GB de RAM disponível para melhor performance[/dim]")
        
        enable_speakers = Confirm.ask(
            "🤖 Ativar identificação automática de speakers?", 
            default=can_use_speakers
        )
        
        min_speakers = None
        max_speakers = None
        speaker_mode = "auto"
        
        if enable_speakers:
            console.print(f"\n[bold green]Configuração Avançada de Speakers:[/bold green]")
            
            # Modo de detecção
            speaker_modes = {
                "1": ("auto", "🎯 Automático", "IA detecta o número ideal"),
                "2": ("meeting", "👥 Reunião (2-8 pessoas)", "Otimizado para reuniões"),
                "3": ("interview", "🎙️ Entrevista (2-3 pessoas)", "Ideal para entrevistas"),
                "4": ("lecture", "📚 Palestra (1-2 speakers)", "Apresentações/aulas"),
                "5": ("custom", "⚙️ Personalizado", "Controle manual completo")
            }
            
            for key, (mode, desc, info) in speaker_modes.items():
                console.print(f"  {key}. {desc}")
                console.print(f"     [dim]{info}[/dim]")
            
            mode_choice = Prompt.ask(
                "Tipo de conteúdo de áudio",
                choices=list(speaker_modes.keys()),
                default="1"
            )
            
            speaker_mode = speaker_modes[mode_choice][0]
            
            # Configurações baseadas no modo
            if speaker_mode == "meeting":
                min_speakers, max_speakers = 2, 8
            elif speaker_mode == "interview":
                min_speakers, max_speakers = 2, 3
            elif speaker_mode == "lecture":
                min_speakers, max_speakers = 1, 2
            elif speaker_mode == "custom":
                min_str = Prompt.ask(
                    "Número mínimo de speakers esperados (Enter = automático)",
                    default=""
                ).strip()
                
                max_str = Prompt.ask(
                    "Número máximo de speakers esperados (Enter = automático)",
                    default=""
                ).strip()
                
                if min_str.isdigit():
                    min_speakers = int(min_str)
                if max_str.isdigit():
                    max_speakers = int(max_str)
            
            # Mostrar configuração escolhida
            if min_speakers or max_speakers:
                min_str = str(min_speakers) if min_speakers else "Auto"
                max_str = str(max_speakers) if max_speakers else "Auto"
                console.print(f"[green]✓[/green] Modo: {speaker_modes[mode_choice][1]} ({min_str}-{max_str} speakers)")
            else:
                console.print(f"[green]✓[/green] Modo: {speaker_modes[mode_choice][1]}")
        else:
            console.print("[yellow]⚠[/yellow] Speaker detection desabilitada - apenas transcrição Whisper")
        
        # Confirmar configurações com informações detalhadas
        console.print(f"\n[bold green]📋 Resumo da Configuração:[/bold green]")
        console.print(f"🎵 Arquivo: {audio_file.name} ({file_size:.1f} MB)")
        console.print(f"🤖 Modelo Whisper: {model_name.upper()} ({model_choices[model_choice][1]})")
        console.print(f"🌍 Idioma: {language or 'Auto-detecção'}")
        console.print(f"🗣️ Speaker Detection: {'✅ Habilitado' if enable_speakers else '❌ Desabilitado'}")
        if enable_speakers:
            mode_name = speaker_modes[mode_choice][1] if 'mode_choice' in locals() else "Auto"
            console.print(f"   Modo: {mode_name}")
            if min_speakers or max_speakers:
                min_str = str(min_speakers) if min_speakers else "Auto"
                max_str = str(max_speakers) if max_speakers else "Auto"
                console.print(f"   Range: {min_str} - {max_str} speakers")
        
        # Estimativa de tempo baseada no modelo e tamanho do arquivo
        duration_estimate = file_size * 0.5  # Estimativa base
        if model_name == "tiny":
            time_multiplier = 0.3
        elif model_name == "base":
            time_multiplier = 0.5
        elif model_name == "small":
            time_multiplier = 0.8
        elif model_name == "medium":
            time_multiplier = 1.2
        else:  # large-v3
            time_multiplier = 2.0
        
        estimated_time = duration_estimate * time_multiplier
        if enable_speakers:
            estimated_time *= 1.5  # Speaker detection adds overhead
        
        console.print(f"⏱️ Tempo estimado: ~{estimated_time:.1f} minutos")
        console.print(f"💾 Hardware: {system_info['performance_level'].upper()} ({system_info['memory']['available']} RAM)")
        
        if not Confirm.ask("\n🚀 Iniciar transcrição inteligente?"):
            console.print("[yellow]❌ CANCELADO[/yellow] Transcrição cancelada pelo usuário")
            logger.info("Transcrição inteligente cancelada pelo usuário")
            return
        
        # Configurar progresso
        console.print(f"\n[bold green]Iniciando transcricao inteligente...[/bold green]")
        
        def progress_callback(progress: float, status: str):
            percentage = int(progress * 100)
            bar_length = 40
            filled_length = int(bar_length * progress)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            print(f"\r[bold blue]Progresso:[/bold blue] [{bar}] {percentage:3d}% | {status}", end="", flush=True)
        
        try:
            # Executar transcrição inteligente
            result = transcribe_with_speakers(
                audio_path=audio_file,
                whisper_model=model_size,
                enable_speakers=enable_speakers,
                language=language,
                progress_callback=progress_callback
            )
            
            # Mostrar resultados com interface rica
            console.print(f"\n\n🎉 [bold green]TRANSCRIÇÃO INTELIGENTE CONCLUÍDA![/bold green]")
            console.print()
            
            # Painel com resultados da transcrição
            transcription_info = (
                f"🌍 Idioma detectado: [bold]{result.transcription.language.upper()}[/bold]\n"
                f"⏱️ Duração: [bold]{result.transcription.duration:.1f}s[/bold] ({result.transcription.duration/60:.1f} min)\n"
                f"📝 Segmentos: [bold]{len(result.transcription.segments)}[/bold]\n"
                f"🔤 Palavras: [bold]{result.transcription.word_count:,}[/bold]\n"
                f"🎯 Confiança média: [bold]{result.transcription.confidence_avg:.1%}[/bold]\n"
                f"⚡ Tempo de processamento: [bold]{result.processing_time:.1f}s[/bold]"
            )
            
            console.print(Panel(
                transcription_info,
                title="🤖 [WHISPER] Resultados da Transcrição",
                border_style="green"
            ))
            
            if result.has_speakers:
                # Painel com resultados de speaker detection
                speaker_info_lines = [
                    f"🗣️ Speakers identificados: [bold]{result.num_speakers}[/bold]",
                    ""
                ]
                
                # Estatísticas detalhadas dos speakers
                for speaker_id, info in result.speaker_info.items():
                    participation = info['percentage']
                    duration = info['duration']
                    segments = info['segments']
                    
                    # Barra visual da participação
                    bar_length = int(participation / 5)  # Max 20 chars
                    bar = "█" * bar_length + "░" * (20 - bar_length)
                    
                    speaker_info_lines.append(
                        f"👤 {info['label']}: [bold]{duration:.1f}s[/bold] ({participation:.1f}%) - {segments} segmentos"
                    )
                    speaker_info_lines.append(f"   [{bar}]")
                    speaker_info_lines.append("")
                
                console.print(Panel(
                    "\n".join(speaker_info_lines),
                    title="🎭 [SPEAKERS] Análise de Participação",
                    border_style="blue"
                ))
            else:
                console.print(Panel(
                    "[yellow]⚠️ Speaker Detection não foi executada ou falhou[/yellow]\n"
                    "Possíveis causas:\n"
                    "• Memória insuficiente\n"
                    "• Modelo pyannote.audio não disponível\n"
                    "• Áudio muito curto ou sem múltiplos speakers",
                    title="🔇 [SPEAKERS] Status",
                    border_style="yellow"
                ))
            
            # Mostrar prévia do texto
            console.print(f"\n[bold blue]Previa do Texto:[/bold blue]")
            if result.has_speakers:
                preview = result.get_formatted_text_with_speakers()[:300]
            else:
                preview = result.transcription.full_text[:300]
            
            preview += "..." if len(preview) >= 300 else ""
            console.print(Panel(preview, border_style="dim"))
            
            # Perguntar sobre exportação
            if Confirm.ask("\nDeseja exportar a transcricao?"):
                # Configurar exportação
                export_formats = {
                    "1": ("txt", "Texto simples"),
                    "2": ("json", "JSON estruturado"),
                    "3": ("srt", "Legenda SRT"),
                    "4": ("vtt", "Legenda WebVTT")
                }
                
                console.print(f"\n[bold blue]Formatos de Exportacao:[/bold blue]")
                for key, (fmt, desc) in export_formats.items():
                    console.print(f"  {key}. {fmt.upper()}: {desc}")
                
                format_choice = Prompt.ask(
                    "Escolha o formato",
                    choices=list(export_formats.keys()),
                    default="1"
                )
                
                export_format_name = export_formats[format_choice][0]
                export_format = ExportFormat(export_format_name)
                
                # Nome do arquivo de saída
                suffix = "_speakers" if result.has_speakers else "_transcricao"
                default_name = audio_file.stem + suffix
                output_name = Prompt.ask(
                    "Nome do arquivo de saida (sem extensao)",
                    default=default_name
                )
                
                # Diretório de saída
                output_dir = Path(settings.base_dir) / "storage" / "transcriptions"
                output_path = output_dir / output_name
                
                # Exportar usando o resultado da transcrição (que já tem speakers se disponível)
                console.print(f"\n[bold blue]Exportando...[/bold blue]")
                final_path = export_transcription(result.transcription, output_path, export_format)
                
                console.print(f"[green][SUCCESS][/green] Transcricao exportada!")
                console.print(f"Arquivo: {final_path}")
                
                # Opção de abrir arquivo
                if Confirm.ask("Abrir o arquivo agora?", default=False):
                    try:
                        import os
                        os.startfile(str(final_path))  # Windows
                    except (ImportError, AttributeError):
                        try:
                            import subprocess
                            subprocess.run(["xdg-open", str(final_path)])  # Linux
                        except FileNotFoundError:
                            console.print("[yellow][WARN][/yellow] Nao foi possivel abrir o arquivo automaticamente")
        
        except (TranscriptionError, SpeakerDetectionError, ModelNotAvailableError) as e:
            console.print(f"\n[red][ERROR][/red] Erro na transcricao inteligente: {e}")
            logger.error(f"Erro na transcrição inteligente: {e}")
            
            if isinstance(e, (SpeakerDetectionError, ModelNotAvailableError)):
                console.print(f"\n[yellow][INFO][/yellow] Tentando continuar apenas com transcricao...")
                # Aqui poderia fazer fallback para transcrição normal
        
        except KeyboardInterrupt:
            console.print(f"\n\n[yellow][CANCELLED][/yellow] Transcricao cancelada pelo usuario")
            logger.info("Transcrição inteligente cancelada pelo usuário")
        
        except Exception as e:
            console.print(f"\n[red][ERROR][/red] Erro inesperado: {e}")
            logger.error(f"Erro inesperado na transcrição inteligente: {e}")
    
    except Exception as e:
        logger.error(f"Erro inesperado no menu de transcrição inteligente: {e}")
        console.print(f"[red][ERROR][/red] Erro no menu: {e}")
    
    # Pausa para o usuário ver as informações
    console.print(f"\n[dim]Pressione Enter para continuar...[/dim]")
    input()


def show_configuration_menu() -> None:
    """
    Exibe menu de configuração do sistema.
    
    Permite gerenciar presets, configurações personalizadas, 
    informações de hardware e otimizações de performance.
    
    Returns:
        None
    """
    logger.info("Usuário acessou menu de configurações")
    
    try:
        # Inicializar gerenciador de configurações
        settings_manager = create_settings_manager()
        
        console.print(Panel(
            "[bold cyan]Sistema de Configuracao MeetingScribe[/bold cyan]\n"
            "Gerencie presets, otimize performance e customize configuracoes\n"
            "Powered by deteccao automatica de hardware",
            title="[CONFIG] Configuracoes do Sistema",
            border_style="cyan"
        ))
        
        while True:
            console.print(f"\n[bold blue]Opcoes de Configuracao:[/bold blue]")
            console.print("1. [INFO]    Informacoes do sistema")
            console.print("2. [PRESET]  Gerenciar presets")
            console.print("3. [CUSTOM]  Configuracao personalizada")
            console.print("4. [BACKUP]  Backup e restauracao")
            console.print("5. [MODELS]  Gerenciar modelos baixados")
            console.print("6. [EXIT]    Voltar ao menu principal")
            
            choice = Prompt.ask(
                "Escolha uma opcao",
                choices=["1", "2", "3", "4", "5", "6"],
                default="6"
            )
            
            if choice == "1":
                _show_system_info(settings_manager)
            elif choice == "2":
                _show_preset_management(settings_manager)
            elif choice == "3":
                _show_custom_configuration(settings_manager)
            elif choice == "4":
                _show_backup_management(settings_manager)
            elif choice == "5":
                _show_model_management()
            elif choice == "6":
                break
    
    except Exception as e:
        logger.error(f"Erro no menu de configurações: {e}")
        console.print(f"[red][ERROR][/red] Erro no menu de configurações: {e}")
    
    # Pausa para o usuário ver as informações
    console.print(f"\n[dim]Pressione Enter para continuar...[/dim]")
    input()


def _show_system_info(settings_manager) -> None:
    """Mostra informações detalhadas do sistema."""
    try:
        console.print("\n[bold blue]Detectando hardware...[/bold blue]")
        
        with console.status("Analisando sistema..."):
            system_info = get_system_info()
            specs = settings_manager.system_specs
        
        console.print(f"\n[bold green]Informacoes do Sistema:[/bold green]")
        
        # Sistema Operacional
        console.print(f"\n🖥️  [bold]Sistema:[/bold]")
        console.print(f"   OS: {system_info['os']}")
        console.print(f"   Python: {system_info['python']}")
        
        # CPU
        cpu_info = system_info['cpu']
        cpu_score_color = "green" if cpu_info['score'] >= 70 else "yellow" if cpu_info['score'] >= 50 else "red"
        console.print(f"\n🔧 [bold]CPU:[/bold]")
        console.print(f"   Nome: {cpu_info['name']}")
        console.print(f"   Cores: {cpu_info['cores']}")
        console.print(f"   Frequencia: {cpu_info['frequency']}")
        console.print(f"   Score: [{cpu_score_color}]{cpu_info['score']}/100[/{cpu_score_color}]")
        
        # Memória
        memory_info = system_info['memory']
        memory_score_color = "green" if memory_info['score'] >= 70 else "yellow" if memory_info['score'] >= 50 else "red"
        console.print(f"\n💾 [bold]Memoria RAM:[/bold]")
        console.print(f"   Total: {memory_info['total']}")
        console.print(f"   Disponivel: {memory_info['available']}")
        console.print(f"   Score: [{memory_score_color}]{memory_info['score']}/100[/{memory_score_color}]")
        
        # GPU
        gpu_info = system_info['gpu']
        console.print(f"\n🎮 [bold]GPU:[/bold]")
        if gpu_info['cuda']:
            gpu_score_color = "green" if gpu_info['score'] >= 70 else "yellow" if gpu_info['score'] >= 50 else "red"
            console.print(f"   Nome: {gpu_info['name']}")
            console.print(f"   Memoria: {gpu_info['memory']}")
            console.print(f"   CUDA: [green]Disponivel[/green]")
            console.print(f"   Score: [{gpu_score_color}]{gpu_info['score']}/100[/{gpu_score_color}]")
        else:
            console.print(f"   Status: [yellow]GPU nao disponivel ou sem CUDA[/yellow]")
            console.print(f"   Processamento: CPU apenas")
        
        # Armazenamento
        storage_info = system_info['storage']
        storage_score_color = "green" if storage_info['score'] >= 70 else "yellow" if storage_info['score'] >= 50 else "red"
        console.print(f"\n💿 [bold]Armazenamento:[/bold]")
        console.print(f"   Disponivel: {storage_info['available']}")
        console.print(f"   Tipo: {storage_info['type']}")
        console.print(f"   Score: [{storage_score_color}]{storage_info['score']}/100[/{storage_score_color}]")
        
        # Performance Geral
        level = system_info['performance_level']
        level_colors = {
            "extreme": "bright_green",
            "high": "green", 
            "medium": "yellow",
            "low": "red"
        }
        level_color = level_colors.get(level, "white")
        
        console.print(f"\n⚡ [bold]Performance Geral:[/bold]")
        console.print(f"   Nivel: [{level_color}]{level.upper()}[/{level_color}]")
        console.print(f"   Preset Recomendado: [cyan]{system_info['recommended_preset'].upper()}[/cyan]")
        console.print(f"   Speaker Detection: [{'green' if system_info['can_use_speakers'] else 'yellow'}]{'Suportado' if system_info['can_use_speakers'] else 'Limitado'}[/{'green' if system_info['can_use_speakers'] else 'yellow'}]")
        
        # Recomendações
        console.print(f"\n💡 [bold blue]Recomendacoes:[/bold blue]")
        
        if level == "extreme":
            console.print("   • Use preset QUALITY para maxima precisao")
            console.print("   • Ative speaker detection para melhor experiencia")
            console.print("   • Considere modelo large-v3 para transcricoes importantes")
        elif level == "high":
            console.print("   • Preset BALANCED oferece melhor custo-beneficio")
            console.print("   • GPU disponivel - use para modelos maiores")
            console.print("   • Speaker detection funcionara bem")
        elif level == "medium":
            console.print("   • Preset BALANCED e ideal para seu sistema")
            console.print("   • Considere modelo small ou base")
            console.print("   • Speaker detection pode ser mais lento")
        else:
            console.print("   • Use preset SPEED para melhor experiencia")
            console.print("   • Modelos tiny ou base sao recomendados")
            console.print("   • Speaker detection pode nao funcionar bem")
    
    except Exception as e:
        logger.error(f"Erro ao mostrar informações do sistema: {e}")
        console.print(f"[red][ERROR][/red] Erro ao detectar hardware: {e}")


def _show_preset_management(settings_manager) -> None:
    """Gerencia presets de configuração."""
    try:
        current_config = settings_manager.get_current_config()
        presets = settings_manager.preset_manager.list_presets()
        
        console.print(f"\n[bold blue]Presets Disponiveis:[/bold blue]")
        console.print(f"Configuracao atual: [cyan]{current_config.preset_type.upper()}[/cyan]")
        
        for i, preset in enumerate(presets, 1):
            name = preset['name']
            display_name = preset['display_name']
            description = preset['description']
            
            # Marcar preset atual
            marker = " [green][ATIVO][/green]" if name == current_config.preset_type else ""
            
            console.print(f"\n{i}. [bold]{display_name}[/bold]{marker}")
            console.print(f"   {description}")
            
            # Mostrar features principais
            features = preset['features'][:2]  # Mostrar apenas 2 features principais
            for feature in features:
                console.print(f"   • {feature}")
        
        console.print(f"\n[bold blue]Opcoes:[/bold blue]")
        console.print("A. Aplicar preset")
        console.print("B. Ver detalhes de um preset")
        console.print("C. Voltar")
        
        choice = Prompt.ask("Escolha uma opcao", choices=["a", "A", "b", "B", "c", "C"], default="C")
        
        if choice.lower() == "a":
            # Aplicar preset
            preset_choice = Prompt.ask(
                f"Qual preset aplicar? (1-{len(presets)})",
                choices=[str(i) for i in range(1, len(presets) + 1)]
            )
            
            selected_preset = presets[int(preset_choice) - 1]
            preset_name = selected_preset['name']
            
            if Confirm.ask(f"Aplicar preset '{selected_preset['display_name']}'?"):
                new_config = settings_manager.apply_preset(preset_name)
                if new_config:
                    console.print(f"[green][SUCCESS][/green] Preset '{selected_preset['display_name']}' aplicado!")
                    console.print("As novas configuracoes serao usadas na proxima transcricao.")
                else:
                    console.print(f"[red][ERROR][/red] Erro ao aplicar preset")
        
        elif choice.lower() == "b":
            # Ver detalhes
            preset_choice = Prompt.ask(
                f"Ver detalhes de qual preset? (1-{len(presets)})",
                choices=[str(i) for i in range(1, len(presets) + 1)]
            )
            
            selected_preset = presets[int(preset_choice) - 1]
            
            console.print(f"\n[bold cyan]Detalhes: {selected_preset['display_name']}[/bold cyan]")
            console.print(f"Descricao: {selected_preset['description']}")
            
            console.print(f"\n[bold]Configuracoes:[/bold]")
            config = selected_preset['config']
            console.print(f"• Modelo Whisper: {config.whisper.model_size}")
            console.print(f"• Dispositivo: {config.whisper.device}")
            console.print(f"• Compute Type: {config.whisper.compute_type}")
            console.print(f"• Speaker Detection: {'Habilitado' if config.speaker.enabled else 'Desabilitado'}")
            
            console.print(f"\n[bold]Recomendado para:[/bold]")
            for item in selected_preset['recommended_for']:
                console.print(f"• {item}")
    
    except Exception as e:
        logger.error(f"Erro no gerenciamento de presets: {e}")
        console.print(f"[red][ERROR][/red] Erro: {e}")


def _show_custom_configuration(settings_manager) -> None:
    """Interface para configuração personalizada."""
    console.print(f"\n[yellow][INFO][/yellow] Configuracao personalizada em desenvolvimento...")
    console.print("Em breve voce podera:")
    console.print("• Configurar cada parametro individualmente")
    console.print("• Salvar configuracoes personalizadas")
    console.print("• Testar configuracoes antes de aplicar")
    console.print("• Criar seus proprios presets")


def _show_backup_management(settings_manager) -> None:
    """Gerencia backups de configuração."""
    try:
        backups = settings_manager.list_backups()
        
        console.print(f"\n[bold blue]Backups de Configuracao:[/bold blue]")
        
        if not backups:
            console.print("[yellow][INFO][/yellow] Nenhum backup encontrado")
            return
        
        console.print(f"Encontrados {len(backups)} backups:")
        
        for i, backup in enumerate(backups[:10], 1):  # Mostrar apenas 10 mais recentes
            timestamp = backup.stem.replace("config_backup_", "")
            # Formatar timestamp
            try:
                from datetime import datetime
                dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                formatted_time = dt.strftime("%d/%m/%Y %H:%M:%S")
            except:
                formatted_time = timestamp
            
            size_kb = backup.stat().st_size / 1024
            console.print(f"  {i:2d}. {formatted_time} ({size_kb:.1f} KB)")
        
        console.print(f"\n[bold blue]Opcoes:[/bold blue]")
        console.print("1. Restaurar backup")
        console.print("2. Criar backup atual")
        console.print("3. Limpar backups antigos")
        console.print("4. Voltar")
        
        choice = Prompt.ask("Escolha uma opcao", choices=["1", "2", "3", "4"], default="4")
        
        if choice == "1" and backups:
            backup_choice = Prompt.ask(
                f"Restaurar qual backup? (1-{min(len(backups), 10)})",
                choices=[str(i) for i in range(1, min(len(backups), 10) + 1)]
            )
            
            selected_backup = backups[int(backup_choice) - 1]
            
            if Confirm.ask(f"Restaurar backup de {selected_backup.stem}?"):
                if settings_manager.restore_backup(selected_backup):
                    console.print("[green][SUCCESS][/green] Backup restaurado com sucesso!")
                else:
                    console.print("[red][ERROR][/red] Erro ao restaurar backup")
        
        elif choice == "2":
            current_config = settings_manager.get_current_config()
            backup_file = settings_manager._create_backup()
            console.print(f"[green][SUCCESS][/green] Backup criado: {backup_file.name}")
        
        elif choice == "3":
            removed_count = settings_manager.cleanup_old_backups(keep_count=5)
            console.print(f"[green][SUCCESS][/green] {removed_count} backups antigos removidos")
    
    except Exception as e:
        logger.error(f"Erro no gerenciamento de backups: {e}")
        console.print(f"[red][ERROR][/red] Erro: {e}")


def _show_model_management() -> None:
    """Gerencia modelos baixados."""
    console.print(f"\n[yellow][INFO][/yellow] Gerenciamento de modelos em desenvolvimento...")
    console.print("Em breve voce podera:")
    console.print("• Ver modelos Whisper baixados")
    console.print("• Ver modelos pyannote baixados")
    console.print("• Limpar cache de modelos")
    console.print("• Pre-baixar modelos para uso offline")
    console.print("• Ver espaco usado por modelos")


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
    valid_choices = ["1", "2", "3", "4", "5", "6", "7", "8"]
    
    while True:
        try:
            console.print()
            choice = Prompt.ask(
                "Escolha uma opção",
                choices=valid_choices,
                default="8"
            )
            
            # Log da escolha do usuário
            logger.debug(f"Usuário selecionou opção: {choice}")
            
            if choice == "1":
                show_recording_menu()
                logger.info("Usuário solicitou: Nova gravação")
                
            elif choice == "2":
                show_transcription_menu()
                logger.info("Usuário solicitou: Transcrever arquivo")
                
            elif choice == "3":
                show_intelligent_transcription_menu()
                logger.info("Usuário solicitou: Transcrição com speakers")
                
            elif choice == "4":
                show_transcription_manager()
                logger.info("Usuário solicitou: Gerenciar transcrições")
                
            elif choice == "5":
                show_audio_devices_menu()
                
            elif choice == "6":
                show_configuration_menu()
                logger.info("Usuário solicitou: Configurações")
                
            elif choice == "7":
                console.print("[REPORT] [yellow]Sistema de relatorios em desenvolvimento...[/yellow]")
                logger.info("Usuário solicitou: Relatórios")
                
            elif choice == "8":
                try:
                    if Confirm.ask("Deseja realmente sair?"):
                        console.print("[WAVE] [green]Obrigado por usar o MeetingScribe![/green]")
                        logger.info("Usuário encerrou o sistema normalmente")
                        break
                    else:
                        logger.debug("Usuário cancelou a saída")
                except KeyboardInterrupt:
                    console.print("\n[WAVE] [yellow]Saida forcada pelo usuario[/yellow]")
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

def handle_cli_commands(args) -> int:
    """Handle command line interface commands for Raycast extension."""
    try:
        if args.list_transcriptions:
            from src.core.file_manager import list_transcriptions
            transcriptions = list_transcriptions(limit=args.limit if hasattr(args, 'limit') else None)
            if args.json:
                print(json.dumps([{
                    'filename': t.filename,
                    'path': str(t.path),
                    'created': t.created.isoformat(),
                    'duration': f"{t.duration:.1f}s",
                    'model': t.model,
                    'language': t.language,
                    'size': f"{t.path.stat().st_size} bytes" if t.path.exists() else "0 bytes"
                } for t in transcriptions], indent=2))
            return 0
            
        elif args.record:
            # Use a robust fallback approach for recording
            try:
                device_manager = DeviceManager()
                device = None
                
                # Try to get specified device or find a working one
                if args.device:
                    if args.device == "system_input":
                        device = device_manager.get_system_default_input()
                    elif args.device == "system_output":
                        device = device_manager.get_system_default_output()
                    else:
                        try:
                            device_id = int(args.device)
                            # Skip known problematic device 10 for now
                            if device_id == 10:
                                print(json.dumps({"error": "Device 10 currently unavailable. Try device 8 (WASAPI) or 3 (MME)"}), file=sys.stderr)
                                return 1
                            device = device_manager.get_device_by_index(device_id)
                        except ValueError:
                            print(json.dumps({"error": "Invalid device ID"}), file=sys.stderr)
                            return 1
                else:
                    # Auto-select best available device
                    devices = device_manager.list_all_devices()
                    for d in devices:
                        if d.is_loopback and d.max_input_channels > 0 and d.index != 10:
                            device = d
                            break
                    
                    if not device:
                        # Fallback to any working device
                        for d in devices:
                            if d.max_input_channels > 0:
                                device = d
                                break
                
                if not device:
                    print(json.dumps({"error": "No suitable audio device found"}), file=sys.stderr)
                    return 1
                    
                if device.max_input_channels == 0:
                    print(json.dumps({"error": f"Device '{device.name}' has no input channels"}), file=sys.stderr)
                    return 1
                    
            except Exception as e:
                print(json.dumps({"error": f"Device detection failed: {str(e)}"}), file=sys.stderr)
                return 1
                
            from audio_recorder import AudioRecorder
            from datetime import datetime
            import threading
            import signal
            import os
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_recording_{timestamp}.wav"
            recording_path = settings.recordings_dir / filename
            
            # Create recorder with specific device
            from audio_recorder import RecordingConfig
            
            config = RecordingConfig(
                device=device,
                sample_rate=int(device.default_sample_rate),  # Use device's native sample rate
                channels=min(device.max_input_channels, 2) if device.max_input_channels > 0 else 1,  # Limit to max 2 channels
                output_dir=settings.recordings_dir,
                max_duration=args.duration if hasattr(args, 'duration') and args.duration else None
            )
            
            recorder = AudioRecorder(config=config)
            
            # Start recording
            try:
                filepath = recorder.start_recording(filename)
                print(json.dumps({
                    "status": "Recording started", 
                    "device": device.name,
                    "file": filepath,
                    "message": "Recording will continue until process is stopped (Ctrl+C)"
                }))
            except Exception as e:
                print(json.dumps({"error": f"Failed to start recording: {str(e)}"}), file=sys.stderr)
                return 1
            
            
            # Record with timeout safety
            try:
                duration = args.duration if hasattr(args, 'duration') and args.duration else 30  # Default 30s max
                print(f"Recording for up to {duration} seconds...", file=sys.stderr)
                
                # Use timeout to prevent hanging
                import threading
                stop_event = threading.Event()
                
                def timeout_handler():
                    time.sleep(duration + 2)  # Safety buffer
                    if not stop_event.is_set():
                        print("Timeout reached, forcing stop", file=sys.stderr)
                        stop_event.set()
                
                timeout_thread = threading.Thread(target=timeout_handler, daemon=True)
                timeout_thread.start()
                
                # Monitor recording with safety checks
                start_time = time.time()
                while recorder.is_recording() and not stop_event.is_set():
                    elapsed = time.time() - start_time
                    if elapsed >= duration:
                        print("Duration limit reached", file=sys.stderr)
                        break
                    time.sleep(0.1)
                    
                stop_event.set()  # Signal timeout thread to exit
                        
            except KeyboardInterrupt:
                print("\nUser interrupted recording", file=sys.stderr)
            finally:
                try:
                    # Force stop with timeout
                    if recorder.is_recording():
                        print("Stopping recording...", file=sys.stderr)
                        stats = recorder.stop_recording()
                        
                        if stats and stats.filename:
                            file_path = Path(stats.filename)
                            file_size = file_path.stat().st_size if file_path.exists() else 0
                            print(json.dumps({
                                "status": "Recording completed",
                                "file": str(stats.filename),
                                "size_bytes": file_size,
                                "duration": f"{stats.duration:.1f}s"
                            }))
                        else:
                            print(json.dumps({"error": "Recording stopped but no file created"}), file=sys.stderr)
                    else:
                        print(json.dumps({"warning": "Recording was not active"}), file=sys.stderr)
                        
                except Exception as e:
                    print(json.dumps({"error": f"Stop recording failed: {str(e)}"}), file=sys.stderr)
                finally:
                    try:
                        recorder.close()
                    except Exception:
                        pass  # Ignore cleanup errors
            
            return 0
            
        elif args.transcribe:
            audio_path = Path(args.transcribe)
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            
            # Usar chunked transcriber para arquivos grandes (> 10MB) ou modelos grandes
            model_name = args.model if args.model else "base"
            use_chunked = file_size_mb > 10 or model_name in ["medium", "large-v2", "large-v3"]
            
            if use_chunked:
                print(f"Arquivo grande ({file_size_mb:.1f}MB) - usando transcrição por chunks com QUALIDADE otimizada")
                from src.transcription.chunked_transcriber import transcribe_large_file
                
                try:
                    # Mapear string para enum
                    try:
                        if model_name == "large-v2":
                            model_enum = WhisperModelSize.LARGE_V2
                        elif model_name == "large-v3":
                            model_enum = WhisperModelSize.LARGE_V3
                        else:
                            model_enum = WhisperModelSize(model_name.upper())
                    except:
                        model_enum = WhisperModelSize.BASE  # fallback
                    
                    saved_path = transcribe_large_file(
                        audio_path, 
                        model_size=model_enum,  # Usar enum
                        chunk_duration=300  # 5 minutos por chunk
                    )
                    print(f"Transcrição salva em: {saved_path}")
                    
                    # Read result for JSON output
                    result_text = saved_path.read_text(encoding='utf-8')
                    print(json.dumps({"status": "completed", "text": "Processado por chunks", "transcription_path": str(saved_path)}))
                    
                except Exception as e:
                    print(json.dumps({"status": "error", "message": str(e)}))
                    return 1
            else:
                # Processamento normal para arquivos pequenos
                try:
                    if args.model == "large-v2":
                        model_enum = WhisperModelSize.LARGE_V2
                    elif args.model == "large-v3":
                        model_enum = WhisperModelSize.LARGE_V3
                    elif args.model:
                        model_enum = WhisperModelSize(args.model.upper())
                    else:
                        model_enum = WhisperModelSize.BASE
                except:
                    model_enum = WhisperModelSize.BASE
                
                # Usar modo qualidade para todos os modelos medium e large
                quality_mode = model_enum in [WhisperModelSize.MEDIUM, WhisperModelSize.LARGE_V2, WhisperModelSize.LARGE_V3]
                
                transcriber = create_transcriber(
                    model_size=model_enum,
                    language=args.language if args.language != 'auto' else None,
                    quality_mode=quality_mode
                )
                
                # Process file
                result = transcriber.transcribe_file(audio_path)
                
                # Save transcription automatically in TXT format
                audio_name = audio_path.stem
                from datetime import datetime as dt
                timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
                transcription_path = settings.transcriptions_dir / f"{audio_name}_transcription_{timestamp}.txt"
                
                saved_path = save_transcription_txt(result, transcription_path)
                print(f"Transcrição salva em: {saved_path}")
                
                # Export if format specified
                if args.export_format:
                    export_path = export_transcription(
                        result, 
                        ExportFormat(args.export_format.upper()),
                        Path(args.transcribe).stem
                    )
                    print(json.dumps({"status": "completed", "export_path": str(export_path), "transcription_path": str(saved_path)}))
                else:
                    print(json.dumps({"status": "completed", "text": result.full_text, "transcription_path": str(saved_path)}))
            
            return 0
            
        elif args.export:
            # Export existing transcription
            from src.core.file_manager import find_transcription
            transcription = find_transcription(args.export)
            if not transcription:
                print(json.dumps({"error": "Transcription not found"}))
                return 1
                
            export_path = export_transcription(
                transcription,
                ExportFormat(args.format.upper()) if args.format else ExportFormat.TXT,
                Path(args.export).stem
            )
            print(json.dumps({"status": "exported", "path": str(export_path)}))
            return 0
            
        elif args.performance:
            # Performance monitoring commands
            try:
                from src.core.raycast_metrics_cli import RaycastMetricsCLI
                cli = RaycastMetricsCLI()
                
                if args.performance == "status":
                    result = cli.get_system_status()
                elif args.performance == "dashboard":
                    result = cli.get_dashboard_data()
                elif args.performance == "metrics":
                    result = cli.get_transcription_metrics()
                elif args.performance == "cache":
                    result = cli.get_cache_status()
                elif args.performance == "trends":
                    hours = getattr(args, 'hours', 24)
                    result = cli.get_performance_trends(hours)
                elif args.performance == "export":
                    result = cli.export_report(args.performance_format)
                else:
                    result = {"error": f"Unknown performance command: {args.performance}"}
                
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
                
            except ImportError:
                print(json.dumps({"error": "Performance monitoring not available"}))
                return 1
            except Exception as e:
                print(json.dumps({"error": f"Performance command failed: {str(e)}"}))
                return 1
                
        elif args.profiling:
            # Profiling commands
            try:
                from src.core.profiler_cli import ProfilerCLI
                cli = ProfilerCLI()
                
                if args.profiling == "summary":
                    result = cli.get_bottleneck_summary()
                elif args.profiling == "reports":
                    result = cli.get_detailed_reports(args.profiling_limit)
                elif args.profiling == "insights":
                    result = cli.get_performance_insights()
                elif args.profiling == "suggestions":
                    result = cli.get_optimization_suggestions()
                elif args.profiling == "export":
                    result = cli.export_profiling_report(args.performance_format)
                else:
                    result = {"error": f"Unknown profiling command: {args.profiling}"}
                
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
                
            except ImportError:
                print(json.dumps({"error": "Auto profiling not available"}))
                return 1
            except Exception as e:
                print(json.dumps({"error": f"Profiling command failed: {str(e)}"}))
                return 1
                
        elif args.cache:
            # Cache management commands
            try:
                from src.core.cache_cli import CacheCLI
                cli = CacheCLI()
                
                if args.cache == "status":
                    result = cli.get_cache_status()
                elif args.cache == "insights":
                    result = cli.get_cache_insights()
                elif args.cache == "optimize":
                    result = cli.optimize_cache()
                elif args.cache == "clear":
                    result = cli.clear_cache()
                elif args.cache == "preload":
                    if not args.cache_directory:
                        result = {"error": "Directory required for preload command"}
                    else:
                        result = cli.preload_directory(args.cache_directory)
                elif args.cache == "config":
                    result = cli.get_cache_config()
                else:
                    result = {"error": f"Unknown cache command: {args.cache}"}
                
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
                
            except ImportError:
                print(json.dumps({"error": "File cache not available"}))
                return 1
            except Exception as e:
                print(json.dumps({"error": f"Cache command failed: {str(e)}"}))
                return 1
        
        elif args.streaming:
            # Streaming management commands
            try:
                from src.core.streaming_cli import StreamingCLI
                cli = StreamingCLI()
                
                if args.streaming == "status":
                    result = cli.get_streaming_status()
                elif args.streaming == "analyze":
                    if not args.streaming_file:
                        result = {"error": "File required for analyze command"}
                    else:
                        result = cli.analyze_file(args.streaming_file)
                elif args.streaming == "test":
                    if not args.streaming_file:
                        result = {"error": "File required for test command"}
                    else:
                        result = cli.stream_test(args.streaming_file, args.streaming_config)
                elif args.streaming == "insights":
                    result = cli.get_streaming_insights()
                elif args.streaming == "benchmark":
                    if not args.streaming_file:
                        result = {"error": "File required for benchmark command"}
                    else:
                        result = cli.benchmark_strategies(args.streaming_file)
                else:
                    result = {"error": f"Unknown streaming command: {args.streaming}"}
                
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
                
            except ImportError:
                print(json.dumps({"error": "Streaming processor not available"}))
                return 1
            except Exception as e:
                print(json.dumps({"error": f"Streaming command failed: {str(e)}"}))
                return 1
            
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return 1
        
    return 0

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
    # Parse command line arguments for CLI mode
    parser = argparse.ArgumentParser(description='MeetingScribe - Sistema de transcrição inteligente')
    parser.add_argument('--list-transcriptions', action='store_true', help='Lista transcrições disponíveis')
    parser.add_argument('--json', action='store_true', help='Output em formato JSON')
    parser.add_argument('--limit', type=int, help='Limita número de resultados')
    parser.add_argument('--record', action='store_true', help='Inicia gravação')
    parser.add_argument('--device', help='ID do dispositivo de áudio')
    parser.add_argument('--transcribe', help='Arquivo para transcrever')
    parser.add_argument('--model', help='Modelo Whisper (tiny, base, small, medium, large-v3)')
    parser.add_argument('--language', help='Idioma para transcrição')
    parser.add_argument('--export-format', help='Formato de exportação (txt, json, srt, vtt, csv, xml)')
    parser.add_argument('--export', help='Nome do arquivo para exportar')
    parser.add_argument('--format', help='Formato para exportação')
    parser.add_argument('--speakers', action='store_true', help='Ativar detecção de speakers')
    parser.add_argument('--duration', type=int, help='Duração da gravação em segundos (para CLI)', default=None)
    parser.add_argument('--performance', help='Comando de performance (status, dashboard, metrics, export)')
    parser.add_argument('--performance-format', default='json', help='Formato de saída para performance')
    parser.add_argument('--profiling', help='Comando de profiling (summary, reports, insights, suggestions, export)')
    parser.add_argument('--profiling-limit', type=int, default=5, help='Limite de resultados para profiling')
    parser.add_argument('--cache', help='Comando de cache (status, insights, optimize, clear, preload, config)')
    parser.add_argument('--cache-directory', help='Diretório para comando preload do cache')
    parser.add_argument('--streaming', help='Comando de streaming (status, analyze, test, insights, benchmark)')
    parser.add_argument('--streaming-file', help='Arquivo para comandos de streaming')
    parser.add_argument('--streaming-config', help='Configuração JSON para streaming')
    
    args = parser.parse_args()
    
    # If CLI arguments provided, handle them instead of interactive mode
    if any([args.list_transcriptions, args.record, args.transcribe, args.export, args.performance, args.profiling, args.cache, args.streaming]):
        return handle_cli_commands(args)
    
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