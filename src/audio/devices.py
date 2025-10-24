"""
Device Manager para MeetingScribe

Gerencia dispositivos de áudio Windows usando pyaudiowpatch para captura WASAPI.
Responsável por detectar e configurar dispositivos de loopback para gravação
de áudio do sistema.

Author: MeetingScribe Team
Version: 1.0.0
Python: >=3.8
"""

import sys
import json
import argparse
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from loguru import logger

try:
    import pyaudiowpatch as pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    logger.warning("pyaudiowpatch não disponível - funcionalidades de áudio limitadas")
    try:
        import pyaudio
        PYAUDIO_AVAILABLE = True
        logger.info("Usando pyaudio padrão como fallback")
    except ImportError:
        PYAUDIO_AVAILABLE = False
        logger.error("Nenhuma biblioteca de áudio disponível")


@dataclass
class AudioDevice:
    """
    Representa um dispositivo de áudio com suas propriedades.
    
    Attributes:
        index: Índice do dispositivo no sistema
        name: Nome do dispositivo
        max_input_channels: Número máximo de canais de entrada
        max_output_channels: Número máximo de canais de saída
        default_sample_rate: Taxa de amostragem padrão
        host_api: API de host (WASAPI, MME, etc.)
        is_loopback: Se é um dispositivo de loopback
        is_default: Se é o dispositivo padrão do sistema
    """
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float
    host_api: str
    is_loopback: bool = False
    is_default: bool = False


class AudioDeviceError(Exception):
    """Exceção customizada para erros de dispositivos de áudio."""
    pass


class WASAPINotAvailableError(AudioDeviceError):
    """Exceção para quando WASAPI não está disponível."""
    pass


class DeviceManager:
    """
    Gerenciador de dispositivos de áudio para Windows.
    
    Utiliza pyaudiowpatch para acessar dispositivos WASAPI loopback,
    permitindo captura de áudio do sistema sem necessidade de configuração
    manual de mixer de áudio.
    """
    
    def __init__(self):
        """
        Inicializa o gerenciador de dispositivos.
        
        Raises:
            AudioDeviceError: Se não conseguir inicializar o sistema de áudio
            WASAPINotAvailableError: Se WASAPI não estiver disponível
        """
        self._audio = None
        self._devices_cache = None
        self._initialize_audio_system()
    
    def _initialize_audio_system(self) -> None:
        """
        Inicializa o sistema de áudio PyAudio.
        
        Raises:
            AudioDeviceError: Se não conseguir inicializar
            WASAPINotAvailableError: Se WASAPI não estiver disponível
        """
        if not PYAUDIO_AVAILABLE:
            raise AudioDeviceError(
                "Sistema de áudio não disponível. "
                "Instale pyaudiowpatch: pip install pyaudiowpatch"
            )
        
        try:
            self._audio = pyaudio.PyAudio()
            logger.info("Sistema de áudio inicializado com sucesso")
            
            # Verificar se WASAPI está disponível
            if not self._is_wasapi_available():
                raise WASAPINotAvailableError(
                    "WASAPI não está disponível neste sistema. "
                    "Funcionalidades de loopback não funcionarão."
                )
            
            logger.info("WASAPI detectado e disponível para uso")
            
        except Exception as e:
            logger.error(f"Falha ao inicializar sistema de áudio: {e}")
            raise AudioDeviceError(f"Não foi possível inicializar PyAudio: {e}") from e
    
    def _is_wasapi_available(self) -> bool:
        """
        Verifica se WASAPI está disponível no sistema.
        
        Returns:
            bool: True se WASAPI estiver disponível
        """
        try:
            host_api_count = self._audio.get_host_api_count()
            for i in range(host_api_count):
                host_api_info = self._audio.get_host_api_info_by_index(i)
                if host_api_info['name'].lower() == 'windows wasapi':
                    logger.debug(f"WASAPI encontrado no índice {i}")
                    return True
            
            logger.warning("WASAPI não encontrado nas APIs de host disponíveis")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade WASAPI: {e}")
            return False
    
    def get_default_speakers(self) -> Optional[AudioDevice]:
        """
        Detecta e retorna o dispositivo de speakers padrão com suporte a loopback.
        
        Procura especificamente por dispositivos WASAPI loopback que correspondem
        aos speakers padrão do sistema para captura de áudio de saída.
        
        Returns:
            Optional[AudioDevice]: Dispositivo de speakers padrão ou None se não encontrado
            
        Raises:
            AudioDeviceError: Se houver erro ao acessar dispositivos
        """
        logger.info("Procurando dispositivo de speakers padrão com suporte a loopback")
        
        try:
            devices = self.list_all_devices()
            
            # Primeiro, tentar encontrar dispositivo loopback explícito
            loopback_devices = [d for d in devices if d.is_loopback]
            
            if loopback_devices:
                # Preferir dispositivo padrão entre os loopbacks
                default_loopback = next((d for d in loopback_devices if d.is_default), None)
                if default_loopback:
                    logger.info(f"Dispositivo loopback padrão encontrado: {default_loopback.name}")
                    return default_loopback
                
                # Se não houver padrão, pegar o primeiro loopback
                first_loopback = loopback_devices[0]
                logger.info(f"Usando primeiro dispositivo loopback: {first_loopback.name}")
                return first_loopback
            
            # Fallback: procurar por dispositivos WASAPI de saída
            wasapi_output_devices = [
                d for d in devices 
                if d.host_api.lower() == 'windows wasapi' and d.max_output_channels > 0
            ]
            
            if wasapi_output_devices:
                # Preferir dispositivo padrão
                default_wasapi = next((d for d in wasapi_output_devices if d.is_default), None)
                if default_wasapi:
                    logger.info(f"Dispositivo WASAPI padrão encontrado: {default_wasapi.name}")
                    return default_wasapi
                
                # Se não houver padrão, pegar o primeiro
                first_wasapi = wasapi_output_devices[0]
                logger.info(f"Usando primeiro dispositivo WASAPI: {first_wasapi.name}")
                return first_wasapi
            
            logger.warning("Nenhum dispositivo WASAPI de saída encontrado")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao detectar speakers padrão: {e}")
            raise AudioDeviceError(f"Falha ao detectar dispositivo padrão: {e}") from e
    
    def list_all_devices(self, refresh_cache: bool = False) -> List[AudioDevice]:
        """
        Lista todos os dispositivos de áudio disponíveis no sistema.
        
        Args:
            refresh_cache: Se True, recarrega a lista de dispositivos
            
        Returns:
            List[AudioDevice]: Lista de todos os dispositivos disponíveis
            
        Raises:
            AudioDeviceError: Se houver erro ao listar dispositivos
        """
        if self._devices_cache is not None and not refresh_cache:
            logger.debug("Retornando dispositivos do cache")
            return self._devices_cache
        
        logger.info("Listando todos os dispositivos de áudio disponíveis")
        
        try:
            devices = []
            device_count = self._audio.get_device_count()
            
            logger.debug(f"Total de dispositivos detectados: {device_count}")
            
            for i in range(device_count):
                try:
                    device_info = self._audio.get_device_info_by_index(i)
                    host_api_info = self._audio.get_host_api_info_by_index(
                        device_info['hostApi']
                    )
                    
                    device = AudioDevice(
                        index=i,
                        name=device_info['name'],
                        max_input_channels=device_info['maxInputChannels'],
                        max_output_channels=device_info['maxOutputChannels'],
                        default_sample_rate=device_info['defaultSampleRate'],
                        host_api=host_api_info['name'],
                        is_loopback=self._is_loopback_device(device_info),
                        is_default=self._is_default_device(device_info, i)
                    )
                    
                    devices.append(device)
                    
                    logger.debug(
                        f"Dispositivo {i}: {device.name} "
                        f"(API: {device.host_api}, "
                        f"In: {device.max_input_channels}, "
                        f"Out: {device.max_output_channels}, "
                        f"Loopback: {device.is_loopback})"
                    )
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar dispositivo {i}: {e}")
                    continue
            
            self._devices_cache = devices
            logger.info(f"Total de {len(devices)} dispositivos listados com sucesso")
            
            return devices
            
        except Exception as e:
            logger.error(f"Erro ao listar dispositivos: {e}")
            raise AudioDeviceError(f"Falha ao listar dispositivos: {e}") from e
    
    def _is_loopback_device(self, device_info: Dict[str, Any]) -> bool:
        """
        Determina se um dispositivo é um dispositivo de loopback.
        
        Args:
            device_info: Informações do dispositivo do PyAudio
            
        Returns:
            bool: True se for um dispositivo de loopback
        """
        device_name = device_info['name'].lower()
        
        # Indicadores comuns de dispositivos loopback
        loopback_indicators = [
            'loopback',
            'stereo mix',
            'what u hear',
            'wave out mix',
            'speakers (',  # Formato comum do WASAPI loopback
            'headphones (',
        ]
        
        for indicator in loopback_indicators:
            if indicator in device_name:
                return True
        
        # Verificar se tem apenas canais de entrada (típico de loopback)
        if (device_info['maxInputChannels'] > 0 and 
            device_info['maxOutputChannels'] == 0 and
            'wasapi' in device_info.get('hostApi', 0)):
            return True
        
        return False
    
    def _is_default_device(self, device_info: Dict[str, Any], device_index: int) -> bool:
        """
        Verifica se um dispositivo é o dispositivo padrão do sistema.
        
        Args:
            device_info: Informações do dispositivo
            device_index: Índice do dispositivo
            
        Returns:
            bool: True se for o dispositivo padrão
        """
        try:
            # Verificar se é o dispositivo padrão de entrada
            default_input = self._audio.get_default_input_device_info()
            if default_input and default_input['index'] == device_index:
                return True
            
            # Verificar se é o dispositivo padrão de saída
            default_output = self._audio.get_default_output_device_info()
            if default_output and default_output['index'] == device_index:
                return True
            
        except Exception as e:
            logger.debug(f"Erro ao verificar dispositivo padrão para {device_index}: {e}")
        
        return False
    
    def get_device_by_index(self, index: int) -> Optional[AudioDevice]:
        """
        Obtém um dispositivo específico pelo seu índice.
        
        Args:
            index: Índice do dispositivo
            
        Returns:
            Optional[AudioDevice]: Dispositivo encontrado ou None
        """
        devices = self.list_all_devices()
        return next((d for d in devices if d.index == index), None)
    
    def get_devices_by_api(self, api_name: str) -> List[AudioDevice]:
        """
        Filtra dispositivos por API de host.
        
        Args:
            api_name: Nome da API (ex: 'Windows WASAPI', 'MME')
            
        Returns:
            List[AudioDevice]: Lista de dispositivos da API especificada
        """
        devices = self.list_all_devices()
        return [d for d in devices if api_name.lower() in d.host_api.lower()]
    
    def get_recording_capable_devices(self) -> List[AudioDevice]:
        """
        Filtra dispositivos adequados para gravação (com canais de entrada > 0).
        
        Returns:
            List[AudioDevice]: Lista de dispositivos que podem ser usados para gravação
        """
        devices = self.list_all_devices()
        recording_devices = [d for d in devices if d.max_input_channels > 0]
        
        # Ordenar por preferência: WASAPI loopback primeiro, depois default, depois outros
        def sort_key(device):
            score = 0
            if device.host_api.lower() == 'windows wasapi':
                score += 30
            if device.is_loopback:
                score += 20  
            if device.is_default:
                score += 10
            return -score  # Negativo para ordem decrescente
        
        return sorted(recording_devices, key=sort_key)
    
    def get_system_default_input(self) -> Optional[AudioDevice]:
        """
        Obtém o dispositivo de entrada padrão do sistema.
        
        Returns:
            Optional[AudioDevice]: Dispositivo de entrada padrão ou None
        """
        try:
            default_input_info = self._audio.get_default_input_device_info()
            if default_input_info:
                return self.get_device_by_index(default_input_info['index'])
        except Exception as e:
            logger.debug(f"Erro ao obter dispositivo de entrada padrão: {e}")
        return None
    
    def get_system_default_output(self) -> Optional[AudioDevice]:
        """
        Obtém o dispositivo de saída padrão do sistema.
        
        Returns:
            Optional[AudioDevice]: Dispositivo de saída padrão ou None
        """
        try:
            default_output_info = self._audio.get_default_output_device_info()
            if default_output_info:
                return self.get_device_by_index(default_output_info['index'])
        except Exception as e:
            logger.debug(f"Erro ao obter dispositivo de saída padrão: {e}")
        return None
    
    def print_device_info(self, device: AudioDevice) -> None:
        """
        Imprime informações detalhadas de um dispositivo.
        
        Args:
            device: Dispositivo para imprimir informações
        """
        print(f"\n{'='*50}")
        print(f"Dispositivo: {device.name}")
        print(f"{'='*50}")
        print(f"Índice: {device.index}")
        print(f"API de Host: {device.host_api}")
        print(f"Canais de Entrada: {device.max_input_channels}")
        print(f"Canais de Saída: {device.max_output_channels}")
        print(f"Taxa de Amostragem: {device.default_sample_rate} Hz")
        print(f"É Loopback: {'Sim' if device.is_loopback else 'Não'}")
        print(f"É Padrão: {'Sim' if device.is_default else 'Não'}")
        print(f"{'='*50}")
    
    def close(self) -> None:
        """
        Fecha o sistema de áudio e libera recursos.
        """
        if self._audio:
            try:
                self._audio.terminate()
                logger.info("Sistema de áudio finalizado")
            except Exception as e:
                logger.warning(f"Erro ao finalizar sistema de áudio: {e}")
            finally:
                self._audio = None
                self._devices_cache = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """
    Função principal para teste e demonstração do DeviceManager.
    """
    parser = argparse.ArgumentParser(description='MeetingScribe Device Manager')
    parser.add_argument('--list-json', action='store_true', help='Lista dispositivos em formato JSON')
    parser.add_argument('--recording-only', action='store_true', help='Lista apenas dispositivos adequados para gravação')
    args = parser.parse_args()
    
    if args.list_json:
        try:
            with DeviceManager() as dm:
                if args.recording_only:
                    # Lista apenas dispositivos adequados para gravação, com opções "Same as System"
                    devices = dm.get_recording_capable_devices()
                    device_list = []
                    
                    # Procurar melhor dispositivo de loopback padrão
                    default_speakers = dm.get_default_speakers()
                    if default_speakers and default_speakers.max_input_channels > 0:
                        device_list.append({
                            "id": "system_output",
                            "name": "Same as System (Output Loopback)",
                            "index": default_speakers.index,
                            "max_input_channels": default_speakers.max_input_channels,
                            "max_output_channels": default_speakers.max_output_channels,
                            "default_sample_rate": default_speakers.default_sample_rate,
                            "host_api": default_speakers.host_api,
                            "is_loopback": default_speakers.is_loopback,
                            "is_default": True,
                            "is_system_default": True
                        })
                    
                    # Adicionar opção para input padrão se for diferente e adequado
                    default_input = dm.get_system_default_input()
                    if (default_input and default_input.max_input_channels > 0 and 
                        (not default_speakers or default_input.index != default_speakers.index)):
                        device_list.append({
                            "id": "system_input",
                            "name": "Same as System (Microphone)",
                            "index": default_input.index,
                            "max_input_channels": default_input.max_input_channels,
                            "max_output_channels": default_input.max_output_channels,
                            "default_sample_rate": default_input.default_sample_rate,
                            "host_api": default_input.host_api,
                            "is_loopback": default_input.is_loopback,
                            "is_default": True,
                            "is_system_default": True
                        })
                    
                    # Adicionar dispositivos adequados para gravação (apenas com canais de entrada > 0)
                    for device in devices:
                        if device.max_input_channels > 0:  # Filtro adicional
                            device_dict = asdict(device)
                            device_dict['id'] = str(device.index)
                            device_dict['is_system_default'] = False
                            device_list.append(device_dict)
                else:
                    # Lista todos os dispositivos
                    devices = dm.list_all_devices()
                    device_list = []
                    
                    for device in devices:
                        device_dict = asdict(device)
                        device_dict['id'] = str(device.index)
                        device_dict['is_system_default'] = False
                        device_list.append(device_dict)
                
                print(json.dumps(device_list, indent=2, ensure_ascii=False))
                return
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            return
    
    # Original interactive mode
    logger.info("Iniciando demonstração do Device Manager")
    
    try:
        with DeviceManager() as dm:
            # Listar todos os dispositivos
            print("\n[AUDIO] LISTANDO TODOS OS DISPOSITIVOS DE AUDIO")
            print("="*60)
            
            devices = dm.list_all_devices()
            
            for device in devices:
                status_icons = []
                if device.is_default:
                    status_icons.append("[DEFAULT] Padrao")
                if device.is_loopback:
                    status_icons.append("[LOOP] Loopback")
                if device.host_api.lower() == 'windows wasapi':
                    status_icons.append("[WASAPI] WASAPI")
                
                status = " | ".join(status_icons) if status_icons else ""
                
                print(f"[{device.index:2d}] {device.name}")
                print(f"     API: {device.host_api}")
                print(f"     In: {device.max_input_channels} | Out: {device.max_output_channels}")
                if status:
                    print(f"     Status: {status}")
                print()
            
            # Detectar dispositivo padrão de speakers
            print("\n[SPEAKERS] DETECTANDO DISPOSITIVO PADRAO DE SPEAKERS")
            print("="*60)
            
            default_speakers = dm.get_default_speakers()
            
            if default_speakers:
                print("[OK] Dispositivo padrao encontrado!")
                dm.print_device_info(default_speakers)
            else:
                print("[ERROR] Nenhum dispositivo padrao encontrado")
            
            # Filtrar dispositivos WASAPI
            print("\n[WASAPI] DISPOSITIVOS WASAPI DISPONIVEIS")
            print("="*60)
            
            wasapi_devices = dm.get_devices_by_api('Windows WASAPI')
            
            if wasapi_devices:
                for device in wasapi_devices:
                    print(f"[{device.index}] {device.name}")
                    if device.is_loopback:
                        print("    [LOOP] Suporte a Loopback")
                    if device.is_default:
                        print("    [DEFAULT] Dispositivo Padrao")
                    print()
            else:
                print("[ERROR] Nenhum dispositivo WASAPI encontrado")
            
    except WASAPINotAvailableError:
        logger.error("WASAPI não está disponível neste sistema")
        print("[ERROR] WASAPI nao disponivel - funcionalidades de loopback limitadas")
        
    except AudioDeviceError as e:
        logger.error(f"Erro no sistema de áudio: {e}")
        print(f"[ERROR] Erro no sistema de audio: {e}")
        
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        print(f"[ERROR] Erro inesperado: {e}")


if __name__ == "__main__":
    main()