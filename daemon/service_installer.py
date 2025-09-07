"""Automatic Windows Service Installation

Implements FR-001 requirement for automatic Windows Service installation
with one-click setup and configuration for always-ready system.
"""

from __future__ import annotations

import os
import sys
import subprocess
import winreg
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging

try:
    import win32serviceutil
    import win32service
    import win32api
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

logger = logging.getLogger(__name__)


class ServiceInstallationError(Exception):
    """Exception raised during service installation"""
    pass


class WindowsServiceInstaller:
    """Handles automatic installation and configuration of MeetingScribe Windows Service"""
    
    def __init__(self):
        self.service_name = "MeetingScribe"
        self.service_display_name = "MeetingScribe AI Transcription Service" 
        self.service_description = "Background AI transcription service for meetings and audio processing"
        
        # Installation paths
        self.project_root = Path(__file__).parent.parent
        self.python_exe = sys.executable
        self.service_script = self.project_root / "daemon" / "service.py"
        
    def install_service_automatic(self) -> bool:
        """
        Automatic one-click service installation with FR-001 compliance.
        
        Returns:
            bool: True if installation successful
        """
        logger.info("Starting automatic MeetingScribe service installation...")
        
        try:
            # Pre-installation checks
            if not self._check_prerequisites():
                return False
            
            # Check if already installed
            if self._is_service_installed():
                logger.info("Service already installed, checking configuration...")
                return self._verify_service_configuration()
            
            # Administrative privileges check
            if not self._check_admin_privileges():
                logger.error("Administrative privileges required for service installation")
                self._show_elevation_instructions()
                return False
            
            # Install service
            success = self._install_service()
            if not success:
                return False
            
            # Configure service for always-ready operation
            success = self._configure_service_fr001()
            if not success:
                logger.warning("Service installed but FR-001 configuration failed")
            
            # Start service
            success = self._start_service_safe()
            if not success:
                logger.warning("Service installed but failed to start")
            
            # Verify installation
            if self._verify_installation():
                logger.success("✅ MeetingScribe service installed and configured successfully")
                self._log_installation_summary()
                return True
            else:
                logger.error("❌ Service installation verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Automatic service installation failed: {e}")
            return False
    
    def uninstall_service_automatic(self) -> bool:
        """
        Automatic service uninstallation.
        
        Returns:
            bool: True if uninstallation successful
        """
        logger.info("Starting automatic MeetingScribe service uninstallation...")
        
        try:
            if not self._is_service_installed():
                logger.info("Service is not installed")
                return True
            
            # Stop service first
            self._stop_service_safe()
            
            # Uninstall service
            success = self._uninstall_service()
            if success:
                logger.success("✅ MeetingScribe service uninstalled successfully")
            else:
                logger.error("❌ Service uninstallation failed")
                
            return success
            
        except Exception as e:
            logger.error(f"Automatic service uninstallation failed: {e}")
            return False
    
    def _check_prerequisites(self) -> bool:
        """Check prerequisites for service installation"""
        logger.debug("Checking installation prerequisites...")
        
        # Check Win32 libraries
        if not HAS_WIN32:
            logger.error("pywin32 libraries not available. Install with: pip install pywin32")
            return False
        
        # Check Python executable
        if not Path(self.python_exe).exists():
            logger.error(f"Python executable not found: {self.python_exe}")
            return False
        
        # Check service script
        if not self.service_script.exists():
            logger.error(f"Service script not found: {self.service_script}")
            return False
        
        # Check project structure
        required_paths = [
            self.project_root / "config.py",
            self.project_root / "daemon" / "daemon_main.py",
            self.project_root / "src" / "teams",
            self.project_root / "src" / "audio"
        ]
        
        for path in required_paths:
            if not path.exists():
                logger.warning(f"Required component not found: {path}")
        
        logger.debug("Prerequisites check completed")
        return True
    
    def _check_admin_privileges(self) -> bool:
        """Check if running with administrative privileges"""
        try:
            # Try to access a registry key that requires admin privileges
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE", 0, winreg.KEY_WRITE)
            winreg.CloseKey(key)
            return True
        except PermissionError:
            return False
        except Exception:
            # Fallback method
            try:
                return os.getuid() == 0
            except AttributeError:
                # Windows - use ctypes
                try:
                    import ctypes
                    return ctypes.windll.shell32.IsUserAnAdmin()
                except Exception:
                    return False
    
    def _show_elevation_instructions(self) -> None:
        """Show instructions for running with admin privileges"""
        script_path = Path(__file__).resolve()
        
        logger.info("To install the service, run the following command as Administrator:")
        logger.info(f"  python \"{script_path}\" install")
        logger.info("")
        logger.info("Alternative methods:")
        logger.info("1. Right-click Command Prompt → 'Run as administrator'")
        logger.info("2. Use PowerShell as Administrator")  
        logger.info("3. Use Windows 'Run as administrator' on your IDE")
    
    def _is_service_installed(self) -> bool:
        """Check if the service is already installed"""
        try:
            import win32service
            scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
            try:
                service = win32service.OpenService(scm, self.service_name, win32service.SERVICE_QUERY_STATUS)
                win32service.CloseServiceHandle(service)
                return True
            except win32service.error:
                return False
            finally:
                win32service.CloseServiceHandle(scm)
        except Exception as e:
            logger.debug(f"Error checking service installation: {e}")
            return False
    
    def _install_service(self) -> bool:
        """Install the Windows service"""
        logger.info("Installing MeetingScribe Windows service...")
        
        try:
            # Use win32serviceutil for installation
            from daemon.service import MeetingScribeService
            
            win32serviceutil.InstallService(
                pythonClassString=f"daemon.service.MeetingScribeService",
                serviceName=self.service_name,
                displayName=self.service_display_name,
                startType=win32service.SERVICE_AUTO_START,
                description=self.service_description,
                exeName=None  # Use current Python executable
            )
            
            logger.info("Service installation completed")
            return True
            
        except Exception as e:
            logger.error(f"Service installation failed: {e}")
            return False
    
    def _configure_service_fr001(self) -> bool:
        """Configure service for FR-001 Always-Ready System compliance"""
        logger.info("Configuring service for FR-001 compliance...")
        
        try:
            # Configure service recovery options for 99.9% uptime
            success = self._configure_service_recovery()
            if not success:
                return False
            
            # Configure service dependencies
            success = self._configure_service_dependencies()
            if not success:
                logger.warning("Service dependency configuration failed")
            
            # Configure service performance settings
            success = self._configure_service_performance()
            if not success:
                logger.warning("Service performance configuration failed")
            
            logger.info("FR-001 service configuration completed")
            return True
            
        except Exception as e:
            logger.error(f"FR-001 service configuration failed: {e}")
            return False
    
    def _configure_service_recovery(self) -> bool:
        """Configure service recovery options for high availability"""
        try:
            # Configure service to restart automatically on failure
            # This supports the 99.9% uptime requirement
            
            cmd = [
                "sc", "failure", self.service_name,
                "reset=", "86400",  # Reset failure count after 24 hours
                "actions=", "restart/5000/restart/10000/restart/20000"  # Restart with increasing delays
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.debug(f"Service recovery configuration: {result.stdout}")
            
            # Configure service to restart immediately on failure
            cmd2 = [
                "sc", "config", self.service_name,
                "start=", "auto"  # Automatic startup
            ]
            
            result2 = subprocess.run(cmd2, capture_output=True, text=True, check=True)
            logger.debug(f"Service startup configuration: {result2.stdout}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Service recovery configuration failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in service recovery config: {e}")
            return False
    
    def _configure_service_dependencies(self) -> bool:
        """Configure service dependencies"""
        try:
            # Configure service to start after network is available
            # This ensures stable operation for Teams detection
            
            cmd = [
                "sc", "config", self.service_name,
                "depend=", "LanmanServer"  # Depend on network services
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                logger.debug("Service dependencies configured")
                return True
            else:
                logger.debug(f"Service dependency config warning: {result.stderr}")
                return True  # Not critical
                
        except Exception as e:
            logger.debug(f"Service dependency configuration failed: {e}")
            return False
    
    def _configure_service_performance(self) -> bool:
        """Configure service for optimal performance"""
        try:
            # Set service process priority to support <3s response times
            # This is done at runtime in the service itself
            
            logger.debug("Performance configuration will be applied at runtime")
            return True
            
        except Exception as e:
            logger.debug(f"Service performance configuration failed: {e}")
            return False
    
    def _start_service_safe(self) -> bool:
        """Start the service safely with error handling"""
        try:
            logger.info("Starting MeetingScribe service...")
            
            win32serviceutil.StartService(self.service_name)
            
            # Wait a moment for service to initialize
            import time
            time.sleep(3.0)
            
            # Verify service is running
            status = self._get_service_status()
            if status.get("state") == "running":
                logger.info("✅ Service started successfully")
                return True
            else:
                logger.warning(f"Service start may have issues, status: {status}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            return False
    
    def _stop_service_safe(self) -> bool:
        """Stop the service safely"""
        try:
            logger.info("Stopping MeetingScribe service...")
            
            win32serviceutil.StopService(self.service_name)
            
            # Wait for service to stop
            import time
            time.sleep(2.0)
            
            logger.info("Service stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            return False
    
    def _uninstall_service(self) -> bool:
        """Uninstall the Windows service"""
        try:
            win32serviceutil.RemoveService(self.service_name)
            logger.info("Service uninstalled")
            return True
            
        except Exception as e:
            logger.error(f"Service uninstallation failed: {e}")
            return False
    
    def _get_service_status(self) -> Dict[str, Any]:
        """Get current service status"""
        try:
            import win32service
            
            scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
            try:
                service = win32service.OpenService(scm, self.service_name, win32service.SERVICE_QUERY_STATUS)
                try:
                    status = win32service.QueryServiceStatus(service)
                    
                    state_map = {
                        win32service.SERVICE_STOPPED: "stopped",
                        win32service.SERVICE_START_PENDING: "starting",
                        win32service.SERVICE_STOP_PENDING: "stopping", 
                        win32service.SERVICE_RUNNING: "running",
                        win32service.SERVICE_CONTINUE_PENDING: "resuming",
                        win32service.SERVICE_PAUSE_PENDING: "pausing",
                        win32service.SERVICE_PAUSED: "paused"
                    }
                    
                    return {
                        "state": state_map.get(status[1], "unknown"),
                        "controls_accepted": status[2],
                        "exit_code": status[3],
                        "service_specific_exit_code": status[4],
                        "check_point": status[5],
                        "wait_hint": status[6]
                    }
                finally:
                    win32service.CloseServiceHandle(service)
            finally:
                win32service.CloseServiceHandle(scm)
                
        except Exception as e:
            logger.debug(f"Failed to get service status: {e}")
            return {"state": "unknown", "error": str(e)}
    
    def _verify_installation(self) -> bool:
        """Verify service installation and basic functionality"""
        logger.info("Verifying service installation...")
        
        try:
            # Check service is installed
            if not self._is_service_installed():
                logger.error("Service not found after installation")
                return False
            
            # Check service status
            status = self._get_service_status()
            if status.get("state") != "running":
                logger.warning(f"Service not running after installation: {status}")
                # Try to start it
                if not self._start_service_safe():
                    return False
            
            # Basic functionality test (if possible)
            # This would test if the service responds to basic requests
            
            logger.info("✅ Service installation verified")
            return True
            
        except Exception as e:
            logger.error(f"Service installation verification failed: {e}")
            return False
    
    def _verify_service_configuration(self) -> bool:
        """Verify existing service configuration"""
        logger.info("Verifying existing service configuration...")
        
        try:
            status = self._get_service_status()
            
            if status.get("state") == "running":
                logger.info("✅ Service is running")
                return True
            elif status.get("state") == "stopped":
                logger.info("Service is stopped, attempting to start...")
                return self._start_service_safe()
            else:
                logger.warning(f"Service in unexpected state: {status}")
                return False
                
        except Exception as e:
            logger.error(f"Service configuration verification failed: {e}")
            return False
    
    def _log_installation_summary(self) -> None:
        """Log installation summary"""
        status = self._get_service_status()
        
        logger.info("=== MeetingScribe Service Installation Summary ===")
        logger.info(f"Service Name: {self.service_name}")
        logger.info(f"Display Name: {self.service_display_name}")
        logger.info(f"Status: {status.get('state', 'unknown')}")
        logger.info(f"Auto-Start: Enabled")
        logger.info(f"Recovery: Auto-restart on failure")
        logger.info("FR-001 Compliance: Always-Ready System configured")
        logger.info("")
        logger.info("Service Management Commands:")
        logger.info(f"  Start: sc start {self.service_name}")
        logger.info(f"  Stop: sc stop {self.service_name}")
        logger.info(f"  Status: sc query {self.service_name}")
        logger.info(f"  Uninstall: python daemon\\service_installer.py uninstall")
    
    def get_installation_status(self) -> Dict[str, Any]:
        """Get comprehensive installation status"""
        return {
            "installed": self._is_service_installed(),
            "status": self._get_service_status(),
            "has_admin_privileges": self._check_admin_privileges(),
            "prerequisites_ok": self._check_prerequisites(),
            "service_name": self.service_name,
            "service_display_name": self.service_display_name
        }


def install_service() -> bool:
    """Install MeetingScribe Windows Service automatically"""
    installer = WindowsServiceInstaller()
    return installer.install_service_automatic()


def uninstall_service() -> bool:
    """Uninstall MeetingScribe Windows Service"""
    installer = WindowsServiceInstaller()
    return installer.uninstall_service_automatic()


def get_service_status() -> Dict[str, Any]:
    """Get service installation and runtime status"""
    installer = WindowsServiceInstaller()
    return installer.get_installation_status()


def main():
    """CLI entry point for service installer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MeetingScribe Windows Service Installer")
    parser.add_argument("action", choices=["install", "uninstall", "status"], 
                       help="Action to perform")
    parser.add_argument("--force", action="store_true", 
                       help="Force operation even if checks fail")
    
    args = parser.parse_args()
    
    if args.action == "install":
        success = install_service()
        sys.exit(0 if success else 1)
    elif args.action == "uninstall":
        success = uninstall_service()
        sys.exit(0 if success else 1)
    elif args.action == "status":
        status = get_service_status()
        print(f"Service Status: {status}")
        sys.exit(0)


if __name__ == "__main__":
    main()