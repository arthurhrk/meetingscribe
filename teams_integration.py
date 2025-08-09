"""
Integração automática com Microsoft Teams
Detecta reuniões ativas e inicia gravação automaticamente
"""

import time
import psutil
import wmi
from datetime import datetime
from pathlib import Path
from loguru import logger
from config import settings
from device_manager import DeviceManager
from audio_recorder import AudioRecorder
import threading
import json


class TeamsIntegration:
    """
    Monitora Microsoft Teams e automatiza gravações durante reuniões
    """
    
    def __init__(self):
        self.is_monitoring = False
        self.current_meeting = None
        self.recorder = None
        self.device_manager = None
        self.monitor_thread = None
        self.recording_active = False
        
        # Configurações
        self.check_interval = 5  # segundos
        self.auto_start_delay = 3  # segundos após detectar reunião
        
        logger.info("Teams Integration inicializado")
    
    def is_teams_running(self) -> bool:
        """Verifica se o Microsoft Teams está rodando"""
        try:
            for process in psutil.process_iter(['pid', 'name']):
                if process.info['name'] and 'teams' in process.info['name'].lower():
                    return True
            return False
        except Exception as e:
            logger.warning(f"Erro ao verificar Teams: {e}")
            return False
    
    def is_in_meeting(self) -> dict:
        """
        Detecta se está em uma reunião ativa
        Retorna informações da reunião ou None
        """
        try:
            # Método 1: Verificar processos do Teams
            teams_processes = []
            for process in psutil.process_iter(['pid', 'name', 'cmdline']):
                if process.info['name'] and 'teams' in process.info['name'].lower():
                    teams_processes.append(process)
            
            if not teams_processes:
                return None
            
            # Método 2: Verificar janelas ativas (Windows específico)
            try:
                import win32gui
                import win32process
                
                def enum_windows_callback(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        window_title = win32gui.GetWindowText(hwnd)
                        if window_title and ('meeting' in window_title.lower() or 
                                           'teams' in window_title.lower() or
                                           'microsoft teams' in window_title.lower()):
                            
                            # Verificar se é uma janela de reunião ativa
                            if any(keyword in window_title.lower() for keyword in [
                                'meeting', 'call', 'reunião', 'chamada', '|'
                            ]):
                                windows.append({
                                    'title': window_title,
                                    'hwnd': hwnd
                                })
                
                windows = []
                win32gui.EnumWindows(enum_windows_callback, windows)
                
                if windows:
                    # Pegar a primeira reunião encontrada
                    meeting_window = windows[0]
                    return {
                        'detected': True,
                        'title': meeting_window['title'],
                        'start_time': datetime.now().isoformat(),
                        'source': 'teams_window'
                    }
            
            except ImportError:
                logger.warning("pywin32 não disponível - usando detecção básica")
            
            # Método 3: Verificar uso de CPU/Rede do Teams (indicador de chamada ativa)
            for process in teams_processes:
                try:
                    cpu_percent = process.cpu_percent(interval=1)
                    if cpu_percent > 5:  # Teams usando CPU = provável reunião
                        return {
                            'detected': True,
                            'title': f'Teams Meeting (CPU: {cpu_percent:.1f}%)',
                            'start_time': datetime.now().isoformat(),
                            'source': 'cpu_activity'
                        }
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao detectar reunião: {e}")
            return None
    
    def get_active_audio_devices(self) -> dict:
        """
        Obtém os dispositivos de áudio ativos no Windows
        """
        try:
            if not self.device_manager:
                self.device_manager = DeviceManager()
            
            # Pegar dispositivos ativos do Windows
            active_devices = {
                'default_speaker': None,
                'default_microphone': None,
                'available_devices': []
            }
            
            # Usar device_manager para encontrar dispositivos WASAPI ativos
            devices = self.device_manager.list_all_devices()
            
            # Encontrar dispositivo de saída padrão (para captura de loopback)
            default_speaker = self.device_manager.get_default_speakers()
            if default_speaker:
                active_devices['default_speaker'] = {
                    'name': default_speaker.get('name', 'Unknown'),
                    'index': default_speaker.get('index', -1),
                    'api': default_speaker.get('api', 'Unknown')
                }
            
            active_devices['available_devices'] = devices
            
            return active_devices
            
        except Exception as e:
            logger.error(f"Erro ao obter dispositivos ativos: {e}")
            return {'default_speaker': None, 'available_devices': []}
    
    def start_auto_recording(self, meeting_info: dict) -> bool:
        """
        Inicia gravação automática para a reunião detectada
        """
        try:
            if self.recording_active:
                logger.info("Gravação já está ativa")
                return True
            
            logger.info(f"Iniciando gravação automática para: {meeting_info['title']}")
            
            # Obter dispositivos ativos
            audio_devices = self.get_active_audio_devices()
            
            if not audio_devices['default_speaker']:
                logger.error("Nenhum dispositivo de áudio ativo encontrado")
                return False
            
            # Criar nome do arquivo baseado na reunião
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            meeting_name = meeting_info['title'].replace(' ', '_')[:50]  # Limitar nome
            filename = f"teams_meeting_{meeting_name}_{timestamp}.wav"
            
            # Configurar gravador com dispositivo ativo
            if not self.recorder:
                self.recorder = AudioRecorder()
            
            # Usar dispositivo de loopback ativo
            device_name = audio_devices['default_speaker']['name']
            success = self.recorder.set_device_by_name(device_name)
            
            if not success:
                logger.error(f"Não foi possível configurar dispositivo: {device_name}")
                return False
            
            # Iniciar gravação
            recording_path = settings.recordings_dir / filename
            success = self.recorder.start_recording(str(recording_path))
            
            if success:
                self.recording_active = True
                self.current_meeting = {
                    **meeting_info,
                    'recording_path': str(recording_path),
                    'device_used': device_name
                }
                
                logger.success(f"Gravação iniciada: {recording_path}")
                return True
            else:
                logger.error("Falha ao iniciar gravação")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao iniciar gravação automática: {e}")
            return False
    
    def stop_auto_recording(self) -> str:
        """
        Para gravação automática e retorna caminho do arquivo
        """
        try:
            if not self.recording_active or not self.recorder:
                logger.info("Nenhuma gravação ativa para parar")
                return None
            
            recording_path = self.recorder.stop_recording()
            self.recording_active = False
            
            if recording_path and self.current_meeting:
                logger.success(f"Gravação finalizada: {recording_path}")
                
                # Salvar metadados da reunião
                metadata = {
                    'meeting_info': self.current_meeting,
                    'end_time': datetime.now().isoformat(),
                    'recording_file': recording_path
                }
                
                metadata_path = Path(recording_path).with_suffix('.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Metadados salvos: {metadata_path}")
                
                self.current_meeting = None
                return recording_path
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao parar gravação: {e}")
            return None
    
    def monitor_loop(self):
        """
        Loop principal de monitoramento
        """
        logger.info("Iniciando monitoramento de reuniões Teams")
        last_meeting_state = False
        
        while self.is_monitoring:
            try:
                # Verificar se Teams está rodando
                if not self.is_teams_running():
                    if self.recording_active:
                        logger.info("Teams fechado - parando gravação")
                        self.stop_auto_recording()
                    
                    time.sleep(self.check_interval)
                    continue
                
                # Verificar se está em reunião
                meeting_info = self.is_in_meeting()
                in_meeting = meeting_info is not None
                
                # Estado mudou para "em reunião"
                if in_meeting and not last_meeting_state:
                    logger.info(f"Reunião detectada: {meeting_info['title']}")
                    
                    # Aguardar alguns segundos e verificar novamente
                    time.sleep(self.auto_start_delay)
                    
                    # Verificar se ainda está em reunião
                    if self.is_in_meeting():
                        self.start_auto_recording(meeting_info)
                
                # Estado mudou para "fora de reunião"  
                elif not in_meeting and last_meeting_state:
                    logger.info("Reunião finalizada")
                    if self.recording_active:
                        self.stop_auto_recording()
                
                last_meeting_state = in_meeting
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Erro no loop de monitoramento: {e}")
                time.sleep(self.check_interval)
    
    def start_monitoring(self):
        """
        Inicia monitoramento automático em thread separada
        """
        if self.is_monitoring:
            logger.info("Monitoramento já está ativo")
            return False
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.success("Monitoramento automático iniciado")
        return True
    
    def stop_monitoring(self):
        """
        Para monitoramento automático
        """
        if not self.is_monitoring:
            return False
        
        logger.info("Parando monitoramento...")
        self.is_monitoring = False
        
        # Parar gravação ativa se houver
        if self.recording_active:
            self.stop_auto_recording()
        
        # Aguardar thread terminar
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
        
        # Limpar recursos
        if self.recorder:
            self.recorder.close()
            self.recorder = None
        
        if self.device_manager:
            self.device_manager.close()
            self.device_manager = None
        
        logger.success("Monitoramento parado")
        return True
    
    def get_status(self) -> dict:
        """
        Retorna status atual do monitoramento
        """
        return {
            'monitoring_active': self.is_monitoring,
            'teams_running': self.is_teams_running(),
            'in_meeting': self.is_in_meeting() is not None,
            'recording_active': self.recording_active,
            'current_meeting': self.current_meeting
        }


# Funções de conveniência para uso direto
def start_teams_monitoring():
    """Inicia monitoramento global do Teams"""
    global _teams_integration
    if '_teams_integration' not in globals():
        _teams_integration = TeamsIntegration()
    
    return _teams_integration.start_monitoring()

def stop_teams_monitoring():
    """Para monitoramento global do Teams"""
    global _teams_integration
    if '_teams_integration' in globals():
        return _teams_integration.stop_monitoring()
    return False

def get_teams_status():
    """Obtém status do monitoramento"""
    global _teams_integration
    if '_teams_integration' in globals():
        return _teams_integration.get_status()
    
    return {
        'monitoring_active': False,
        'teams_running': False,
        'in_meeting': False,
        'recording_active': False,
        'current_meeting': None
    }


if __name__ == "__main__":
    # Teste da integração
    teams = TeamsIntegration()
    
    print("=== Teams Integration Test ===")
    print(f"Teams running: {teams.is_teams_running()}")
    print(f"In meeting: {teams.is_in_meeting()}")
    print(f"Audio devices: {teams.get_active_audio_devices()}")
    
    # Testar monitoramento por 30 segundos
    print("\nIniciando monitoramento por 30 segundos...")
    teams.start_monitoring()
    
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("\nParando...")
    
    teams.stop_monitoring()
    print("Teste finalizado.")