"""
Audio Recorder para MeetingScribe

Módulo responsável pela gravação de áudio usando dispositivos WASAPI loopback.
Permite captura de áudio do sistema para transcrição posterior.

Author: MeetingScribe Team
Version: 1.0.0
Python: >=3.8
"""

import wave
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field

from loguru import logger
from device_manager import DeviceManager, AudioDevice, AudioDeviceError

try:
    import pyaudiowpatch as pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    try:
        import pyaudio
        PYAUDIO_AVAILABLE = True
        logger.warning("Usando pyaudio padrão - funcionalidades WASAPI limitadas")
    except ImportError:
        PYAUDIO_AVAILABLE = False
        logger.error("PyAudio não disponível")


@dataclass
class RecordingConfig:
    """
    Configuração para gravação de áudio.
    
    Attributes:
        device: Dispositivo de áudio para gravação
        sample_rate: Taxa de amostragem em Hz
        channels: Número de canais de áudio
        chunk_size: Tamanho do buffer em frames
        format: Formato de áudio PyAudio
        max_duration: Duração máxima em segundos (None = sem limite)
        output_dir: Diretório para salvar gravações
    """
    device: AudioDevice
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    format: int = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None
    max_duration: Optional[int] = None
    output_dir: Path = field(default_factory=lambda: Path("storage/recordings"))


@dataclass
class RecordingStats:
    """
    Estatísticas de uma gravação.
    
    Attributes:
        start_time: Timestamp de início
        end_time: Timestamp de fim
        duration: Duração em segundos
        file_size: Tamanho do arquivo em bytes
        samples_recorded: Total de samples gravados
        filename: Nome do arquivo gerado
    """
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0
    file_size: int = 0
    samples_recorded: int = 0
    filename: Optional[str] = None


class AudioRecorderError(Exception):
    """Exceção customizada para erros do gravador de áudio."""
    pass


class RecordingInProgressError(AudioRecorderError):
    """Exceção para quando uma gravação já está em progresso."""
    pass


class AudioRecorder:
    """
    Gravador de áudio para captura de sistema usando WASAPI loopback.
    
    Permite gravação contínua de áudio do sistema com controle de início/parada,
    monitoramento de progresso e estatísticas detalhadas.
    """
    
    def __init__(self, config: Optional[RecordingConfig] = None):
        """
        Inicializa o gravador de áudio.
        
        Args:
            config: Configuração de gravação. Se None, usa configuração padrão.
            
        Raises:
            AudioRecorderError: Se não conseguir inicializar o sistema de áudio
        """
        if not PYAUDIO_AVAILABLE:
            raise AudioRecorderError(
                "PyAudio não disponível. Instale: pip install pyaudiowpatch"
            )
        
        self._config = config
        self._audio = None
        self._stream = None
        self._recording = False
        self._recording_thread = None
        self._frames = []
        self._stats = None
        self._progress_callback = None
        
        self._initialize_audio_system()
    
    def _initialize_audio_system(self) -> None:
        """
        Inicializa o sistema de áudio PyAudio.
        
        Raises:
            AudioRecorderError: Se não conseguir inicializar
        """
        try:
            self._audio = pyaudio.PyAudio()
            logger.info("Sistema de áudio para gravação inicializado")
        except Exception as e:
            logger.error(f"Falha ao inicializar sistema de áudio: {e}")
            raise AudioRecorderError(f"Não foi possível inicializar PyAudio: {e}") from e
    
    def set_device_auto(self) -> bool:
        """
        Configura automaticamente o melhor dispositivo disponível.
        
        Returns:
            bool: True se conseguiu configurar um dispositivo
        """
        try:
            with DeviceManager() as dm:
                device = dm.get_default_speakers()
                
                if device:
                    # Configurar para usar dispositivo WASAPI loopback se disponível
                    wasapi_devices = dm.get_devices_by_api('Windows WASAPI')
                    loopback_devices = [d for d in wasapi_devices if d.is_loopback]
                    
                    if loopback_devices:
                        # Preferir dispositivo loopback que corresponda ao padrão
                        for loopback in loopback_devices:
                            if device.name.lower() in loopback.name.lower():
                                device = loopback
                                break
                        else:
                            # Se não encontrar correspondência, usar primeiro loopback
                            device = loopback_devices[0]
                    
                    self._config = RecordingConfig(
                        device=device,
                        sample_rate=int(device.default_sample_rate),
                        channels=min(device.max_input_channels, 2) or 1
                    )
                    
                    logger.info(f"Dispositivo configurado automaticamente: {device.name}")
                    return True
                
                logger.warning("Nenhum dispositivo adequado encontrado")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao configurar dispositivo automaticamente: {e}")
            return False
    
    def start_recording(self, filename: Optional[str] = None, 
                       progress_callback: Optional[Callable[[float], None]] = None) -> str:
        """
        Inicia uma nova gravação.
        
        Args:
            filename: Nome do arquivo (sem extensão). Se None, usa timestamp.
            progress_callback: Callback chamado com duração atual em segundos
            
        Returns:
            str: Caminho completo do arquivo que será criado
            
        Raises:
            RecordingInProgressError: Se já houver gravação em andamento
            AudioRecorderError: Se não conseguir iniciar gravação
        """
        if self._recording:
            raise RecordingInProgressError("Gravação já está em progresso")
        
        if not self._config:
            logger.info("Configuração não definida, detectando automaticamente...")
            if not self.set_device_auto():
                raise AudioRecorderError("Não foi possível configurar dispositivo de áudio")
        
        # Gerar nome do arquivo
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_{timestamp}"
        
        # Garantir extensão .wav
        if not filename.endswith('.wav'):
            filename += '.wav'
        
        # Criar caminho completo
        self._config.output_dir.mkdir(parents=True, exist_ok=True)
        filepath = self._config.output_dir / filename
        
        # Configurar callback de progresso
        self._progress_callback = progress_callback
        
        # Inicializar estatísticas
        self._stats = RecordingStats(
            start_time=datetime.now(),
            filename=str(filepath)
        )
        
        # Limpar frames anteriores
        self._frames = []
        
        try:
            # Abrir stream de áudio
            self._stream = self._audio.open(
                format=self._config.format,
                channels=self._config.channels,
                rate=self._config.sample_rate,
                input=True,
                input_device_index=self._config.device.index,
                frames_per_buffer=self._config.chunk_size,
                as_loopback=getattr(self._config.device, 'is_loopback', False)
            )
            
            logger.info(f"Stream de áudio aberto para dispositivo {self._config.device.name}")
            
            # Iniciar thread de gravação
            self._recording = True
            self._recording_thread = threading.Thread(target=self._recording_worker)
            self._recording_thread.daemon = True
            self._recording_thread.start()
            
            logger.info(f"Gravação iniciada: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Erro ao iniciar gravação: {e}")
            self._cleanup_recording()
            raise AudioRecorderError(f"Falha ao iniciar gravação: {e}") from e
    
    def _recording_worker(self) -> None:
        """
        Worker thread que realiza a gravação contínua.
        """
        logger.debug("Thread de gravação iniciada")
        
        try:
            start_time = time.time()
            
            while self._recording:
                # Verificar limite de duração
                current_time = time.time()
                duration = current_time - start_time
                
                if (self._config.max_duration and 
                    duration >= self._config.max_duration):
                    logger.info(f"Duração máxima atingida: {self._config.max_duration}s")
                    break
                
                # Ler dados do stream
                try:
                    data = self._stream.read(self._config.chunk_size, exception_on_overflow=False)
                    self._frames.append(data)
                    self._stats.samples_recorded += self._config.chunk_size
                    
                    # Chamar callback de progresso
                    if self._progress_callback:
                        try:
                            self._progress_callback(duration)
                        except Exception as e:
                            logger.warning(f"Erro no callback de progresso: {e}")
                    
                except Exception as e:
                    logger.warning(f"Erro ao ler dados de áudio: {e}")
                    # Continuar gravação mesmo com erros pontuais
                    
        except Exception as e:
            logger.error(f"Erro crítico na thread de gravação: {e}")
            
        finally:
            logger.debug("Thread de gravação finalizada")
    
    def stop_recording(self) -> RecordingStats:
        """
        Para a gravação atual e salva o arquivo.
        
        Returns:
            RecordingStats: Estatísticas da gravação
            
        Raises:
            AudioRecorderError: Se não houver gravação em andamento ou erro ao salvar
        """
        if not self._recording:
            raise AudioRecorderError("Nenhuma gravação em andamento")
        
        logger.info("Parando gravação...")
        
        # Parar gravação
        self._recording = False
        
        # Aguardar thread finalizar
        if self._recording_thread:
            self._recording_thread.join(timeout=5.0)
            if self._recording_thread.is_alive():
                logger.warning("Thread de gravação não finalizou no tempo esperado")
        
        # Fechar stream
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
                logger.debug("Stream de áudio fechado")
            except Exception as e:
                logger.warning(f"Erro ao fechar stream: {e}")
            finally:
                self._stream = None
        
        # Finalizar estatísticas
        self._stats.end_time = datetime.now()
        self._stats.duration = (self._stats.end_time - self._stats.start_time).total_seconds()
        
        # Salvar arquivo
        try:
            self._save_recording()
            logger.info(f"Gravação salva: {self._stats.filename}")
        except Exception as e:
            logger.error(f"Erro ao salvar gravação: {e}")
            raise AudioRecorderError(f"Falha ao salvar arquivo: {e}") from e
        
        return self._stats
    
    def _save_recording(self) -> None:
        """
        Salva os frames gravados em arquivo WAV.
        
        Raises:
            AudioRecorderError: Se não conseguir salvar o arquivo
        """
        if not self._frames:
            raise AudioRecorderError("Nenhum dado de áudio para salvar")
        
        try:
            with wave.open(self._stats.filename, 'wb') as wav_file:
                wav_file.setnchannels(self._config.channels)
                wav_file.setsampwidth(self._audio.get_sample_size(self._config.format))
                wav_file.setframerate(self._config.sample_rate)
                wav_file.writeframes(b''.join(self._frames))
            
            # Atualizar estatísticas
            file_path = Path(self._stats.filename)
            self._stats.file_size = file_path.stat().st_size
            
            logger.debug(f"Arquivo WAV salvo: {self._stats.file_size} bytes")
            
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo WAV: {e}")
            raise AudioRecorderError(f"Falha ao escrever arquivo: {e}") from e
    
    def is_recording(self) -> bool:
        """
        Verifica se há gravação em andamento.
        
        Returns:
            bool: True se estiver gravando
        """
        return self._recording
    
    def get_current_stats(self) -> Optional[RecordingStats]:
        """
        Obtém estatísticas da gravação atual.
        
        Returns:
            Optional[RecordingStats]: Estatísticas ou None se não estiver gravando
        """
        if not self._stats:
            return None
        
        # Atualizar duração atual se estiver gravando
        if self._recording:
            current_time = datetime.now()
            self._stats.duration = (current_time - self._stats.start_time).total_seconds()
        
        return self._stats
    
    def _cleanup_recording(self) -> None:
        """
        Limpa recursos de gravação em caso de erro.
        """
        self._recording = False
        
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            finally:
                self._stream = None
        
        self._frames = []
        self._stats = None
    
    def close(self) -> None:
        """
        Finaliza o gravador e libera recursos.
        """
        if self._recording:
            try:
                self.stop_recording()
            except Exception as e:
                logger.warning(f"Erro ao parar gravação durante fechamento: {e}")
        
        if self._audio:
            try:
                self._audio.terminate()
                logger.info("Sistema de áudio do gravador finalizado")
            except Exception as e:
                logger.warning(f"Erro ao finalizar PyAudio: {e}")
            finally:
                self._audio = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_recorder_from_config() -> AudioRecorder:
    """
    Cria um gravador usando configurações do settings.
    
    Returns:
        AudioRecorder: Gravador configurado
        
    Raises:
        AudioRecorderError: Se não conseguir criar o gravador
    """
    try:
        from config import settings
        
        recorder = AudioRecorder()
        
        if recorder.set_device_auto():
            # Atualizar configuração com settings
            recorder._config.sample_rate = settings.audio_sample_rate
            recorder._config.channels = settings.audio_channels
            recorder._config.output_dir = settings.recordings_dir
            
            logger.info("Gravador criado com configurações do sistema")
            return recorder
        else:
            raise AudioRecorderError("Não foi possível configurar dispositivo automaticamente")
            
    except ImportError:
        logger.warning("Configurações não disponíveis, usando padrões")
        recorder = AudioRecorder()
        recorder.set_device_auto()
        return recorder


def main():
    """
    Função principal para teste e demonstração do AudioRecorder.
    """
    logger.info("Iniciando demonstração do Audio Recorder")
    
    try:
        with create_recorder_from_config() as recorder:
            print("\n[AUDIO] DEMONSTRACAO DO GRAVADOR DE AUDIO")
            print("="*50)
            
            # Mostrar configuração
            config = recorder._config
            if config:
                print(f"Dispositivo: {config.device.name}")
                print(f"API: {config.device.host_api}")
                print(f"Taxa: {config.sample_rate} Hz")
                print(f"Canais: {config.channels}")
                print(f"Loopback: {'Sim' if config.device.is_loopback else 'Nao'}")
            else:
                print("Nenhuma configuracao disponivel")
                return
            
            # Testar gravação curta
            print(f"\nIniciando gravacao de teste (5 segundos)...")
            
            def progress_callback(duration):
                print(f"\rGravando: {duration:.1f}s", end="", flush=True)
            
            filepath = recorder.start_recording(
                filename="teste_gravacao",
                progress_callback=progress_callback
            )
            
            # Aguardar 5 segundos
            time.sleep(5)
            
            # Parar gravação
            print(f"\nParando gravacao...")
            stats = recorder.stop_recording()
            
            # Mostrar resultados
            print(f"\n[OK] Gravacao concluida!")
            print(f"Arquivo: {stats.filename}")
            print(f"Duracao: {stats.duration:.2f} segundos")
            print(f"Tamanho: {stats.file_size} bytes")
            print(f"Samples: {stats.samples_recorded}")
            
    except AudioRecorderError as e:
        logger.error(f"Erro no gravador: {e}")
        print(f"[ERROR] Erro no gravador: {e}")
        
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        print(f"[ERROR] Erro inesperado: {e}")


if __name__ == "__main__":
    main()