"""
Windows Service Wrapper

Windows Service implementation para MeetingScribe daemon.
Baseado na arquitetura do Krisp AI com auto-restart e recovery.
"""

import sys
import time
import traceback
from pathlib import Path

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
except ImportError:
    print("❌ pywin32 não instalado. Execute: pip install pywin32")
    sys.exit(1)

from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import setup_directories, setup_logging
    from daemon.daemon_main import DaemonMain
except ImportError as e:
    servicemanager.LogErrorMsg(f"Erro ao importar dependências: {e}")
    sys.exit(1)


class MeetingScribeService(win32serviceutil.ServiceFramework):
    """
    Windows Service para MeetingScribe daemon.
    
    Inspirado na arquitetura do Krisp AI com:
    - Auto-start com Windows
    - Auto-restart em caso de crash
    - Logging para Windows Event Log
    - Execução em contexto do usuário
    """
    
    _svc_name_ = "MeetingScribe"
    _svc_display_name_ = "MeetingScribe AI Transcription Service"
    _svc_description_ = "Background AI transcription service for meetings and audio processing"
    _svc_deps_ = None
    
    def __init__(self, args):
        """Inicializa o Windows Service."""
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.daemon_process = None
        self.running = False
        
    def SvcStop(self):
        """Para o serviço graciosamente."""
        servicemanager.LogInfoMsg("MeetingScribe Service stopping...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
        try:
            # Signal daemon to stop
            if self.daemon_process:
                self.daemon_process.stop_gracefully()
                
            # Wait for graceful shutdown (max 30 seconds)
            for i in range(30):
                if not self.running:
                    break
                time.sleep(1)
                
            self.running = False
            win32event.SetEvent(self.hWaitStop)
            
            servicemanager.LogInfoMsg("MeetingScribe Service stopped successfully")
            
        except Exception as e:
            servicemanager.LogErrorMsg(f"Error during service stop: {e}")
            win32event.SetEvent(self.hWaitStop)
        
    def SvcDoRun(self):
        """Execução principal do serviço."""
        servicemanager.LogInfoMsg("MeetingScribe Service starting...")
        
        try:
            # Setup system components
            self._setup_system()
            
            # Create and start daemon
            self.daemon_process = DaemonMain()
            self.running = True
            
            # Start daemon in separate thread-like manner
            self._run_daemon()
            
            # Wait for stop signal
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            
        except Exception as e:
            error_msg = f"Critical service error: {e}\\n{traceback.format_exc()}"
            servicemanager.LogErrorMsg(error_msg)
            logger.error(error_msg)
            raise
        
        servicemanager.LogInfoMsg("MeetingScribe Service exiting")
    
    def _setup_system(self):
        """Configura componentes do sistema."""
        try:
            # Setup directories and logging
            setup_directories()
            setup_logging()
            
            logger.info("MeetingScribe Service: System setup complete")
            servicemanager.LogInfoMsg("System setup complete")
            
        except Exception as e:
            error_msg = f"System setup failed: {e}"
            servicemanager.LogErrorMsg(error_msg)
            raise
    
    def _run_daemon(self):
        """Executa o daemon principal."""
        try:
            # Start daemon
            logger.info("Starting MeetingScribe daemon process")
            self.daemon_process.run()
            
        except Exception as e:
            error_msg = f"Daemon execution error: {e}\\n{traceback.format_exc()}"
            logger.error(error_msg)
            servicemanager.LogErrorMsg(error_msg)
            
            # Auto-restart logic (Krisp-inspired)
            self._attempt_restart()
    
    def _attempt_restart(self):
        """Tenta reiniciar o daemon em caso de falha."""
        max_retries = 3
        retry_delay = 10  # seconds
        
        for attempt in range(max_retries):
            if not self.running:
                break
                
            logger.warning(f"Attempting daemon restart {attempt + 1}/{max_retries}")
            servicemanager.LogWarningMsg(f"Daemon restart attempt {attempt + 1}")
            
            try:
                time.sleep(retry_delay)
                
                # Create new daemon instance
                self.daemon_process = DaemonMain()
                self.daemon_process.run()
                
                logger.info("Daemon restarted successfully")
                servicemanager.LogInfoMsg("Daemon restarted successfully")
                return
                
            except Exception as e:
                logger.error(f"Restart attempt {attempt + 1} failed: {e}")
                servicemanager.LogErrorMsg(f"Restart attempt {attempt + 1} failed: {e}")
        
        # All restart attempts failed
        logger.error("All restart attempts failed. Service will stop.")
        servicemanager.LogErrorMsg("All restart attempts failed. Service stopping.")
        self.running = False


def install_service():
    """Instala o Windows Service."""
    try:
        win32serviceutil.InstallService(
            MeetingScribeService._svc_reg_class_,
            MeetingScribeService._svc_name_,
            MeetingScribeService._svc_display_name_,
            startType=win32service.SERVICE_AUTO_START,
            description=MeetingScribeService._svc_description_
        )
        print(f"✅ Serviço '{MeetingScribeService._svc_display_name_}' instalado com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao instalar serviço: {e}")
        return False

def uninstall_service():
    """Remove o Windows Service."""
    try:
        win32serviceutil.RemoveService(MeetingScribeService._svc_name_)
        print(f"✅ Serviço '{MeetingScribeService._svc_display_name_}' removido com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao remover serviço: {e}")
        return False

def start_service():
    """Inicia o Windows Service."""
    try:
        win32serviceutil.StartService(MeetingScribeService._svc_name_)
        print(f"✅ Serviço '{MeetingScribeService._svc_display_name_}' iniciado")
        return True
    except Exception as e:
        print(f"❌ Erro ao iniciar serviço: {e}")
        return False

def stop_service():
    """Para o Windows Service."""
    try:
        win32serviceutil.StopService(MeetingScribeService._svc_name_)
        print(f"✅ Serviço '{MeetingScribeService._svc_display_name_}' parado")
        return True
    except Exception as e:
        print(f"❌ Erro ao parar serviço: {e}")
        return False

def service_status():
    """Verifica status do Windows Service."""
    try:
        import subprocess
        result = subprocess.run(
            ["sc", "query", MeetingScribeService._svc_name_],
            capture_output=True,
            text=True,
            check=True
        )
        
        if "RUNNING" in result.stdout:
            return "running"
        elif "STOPPED" in result.stdout:
            return "stopped"
        else:
            return "unknown"
            
    except subprocess.CalledProcessError:
        return "not_installed"


if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) == 1:
        # No arguments - try to start as service
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(MeetingScribeService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Handle install/remove/start/stop commands
        win32serviceutil.HandleCommandLine(MeetingScribeService)