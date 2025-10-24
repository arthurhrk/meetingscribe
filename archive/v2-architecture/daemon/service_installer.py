"""Windows Service Automatic Installer

Implements FR-001 requirement for automatic Windows Service installation
with one-click setup and configuration for Always-Ready System operation.

This module provides automated installation, configuration, and management
of the MeetingScribe Windows Service with FR-001 compliance features:
- Automatic service installation with admin privilege detection
- Service recovery configuration for 99.9% uptime requirement
- One-click setup with comprehensive verification
- Service status monitoring and management

Key Features:
- One-click automatic service installation and configuration
- Administrative privilege detection and elevation guidance
- Service recovery configuration (auto-restart on failure)
- FR-001 compliance verification and status reporting
- Comprehensive installation verification and troubleshooting

Usage:
    from daemon.service_installer import install_service, get_service_status
    
    # Install service automatically
    success = install_service()
    
    # Check service status
    status = get_service_status()
"""

from __future__ import annotations

import os
import sys
import subprocess
import winreg
from pathlib import Path
from typing import Dict, Any, Optional
import logging

try:
    import win32serviceutil
    import win32service
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

logger = logging.getLogger(__name__)


class ServiceInstallationError(Exception):
    """Exception raised during service installation"""
    pass


class WindowsServiceInstaller:
    """
    Handles automatic installation and configuration of MeetingScribe Windows Service.
    
    Provides one-click installation with FR-001 compliance configuration including:
    - Automatic startup configuration
    - Service recovery settings for high availability
    - Administrative privilege handling
    - Installation verification and status reporting
    """
    
    def __init__(self):
        self.service_name = "MeetingScribe"
        self.service_display_name = "MeetingScribe AI Transcription Service" 
        self.service_description = "Background AI transcription service for meetings and audio processing"
        
        # Installation paths
        self.project_root = Path(__file__).parent.parent
        self.service_script = self.project_root / "daemon" / "service.py"
        
    def install_service_automatic(self) -> bool:
        """
        Automatic one-click service installation with FR-001 compliance.
        
        Performs complete service installation including:
        - Prerequisites verification
        - Administrative privilege check
        - Service installation and configuration
        - FR-001 compliance setup (auto-restart, recovery)
        - Installation verification
        
        Returns:
            bool: True if installation successful
        """
        logger.info("Starting automatic MeetingScribe service installation...")
        
        try:
            # Check prerequisites
            if not self._check_prerequisites():
                return False
            
            # Check if already installed
            if self._is_service_installed():
                logger.info("Service already installed, verifying configuration...")
                return self._verify_service_configuration()
            
            # Check administrative privileges
            if not self._check_admin_privileges():
                logger.error("Administrative privileges required for service installation")
                self._show_elevation_instructions()
                return False
            
            # Install and configure service
            if not self._install_service():
                return False
            
            if not self._configure_service_fr001():
                logger.warning("Service installed but FR-001 configuration may be incomplete")
            
            # Start service and verify
            if not self._start_service_safe():
                logger.warning("Service installed but failed to start")
            
            if self._verify_installation():
                logger.info("✅ MeetingScribe service installed and configured successfully")
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
            if self._uninstall_service():
                logger.info("✅ MeetingScribe service uninstalled successfully")
                return True
            else:
                logger.error("❌ Service uninstallation failed")
                return False
                
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
        
        # Check service script exists
        if not self.service_script.exists():
            logger.error(f"Service script not found: {self.service_script}")
            return False
        
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
            # Fallback method using ctypes
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin()
            except Exception:
                return False
    
    def _show_elevation_instructions(self) -> None:
        """Show instructions for running with admin privileges"""
        logger.info("To install the service, run as Administrator:")
        logger.info("1. Right-click Command Prompt → 'Run as administrator'")
        logger.info("2. Use PowerShell as Administrator")  
        logger.info("3. Use 'Run as administrator' on your IDE")
        logger.info(f"4. Then run: python daemon\\service_installer.py install")
    
    def _is_service_installed(self) -> bool:
        """Check if the service is already installed"""
        try:
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
            # Import service class and install
            from daemon.service import MeetingScribeService
            
            win32serviceutil.InstallService(
                pythonClassString="daemon.service.MeetingScribeService",
                serviceName=self.service_name,
                displayName=self.service_display_name,
                startType=win32service.SERVICE_AUTO_START,
                description=self.service_description
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
            # Set service to restart automatically on failure
            cmd = [
                "sc", "failure", self.service_name,
                "reset=", "86400",  # Reset failure count after 24 hours
                "actions=", "restart/5000/restart/10000/restart/20000"  # Restart with delays
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.debug("Service recovery configuration completed")
            
            # Configure automatic startup
            cmd2 = [
                "sc", "config", self.service_name,
                "start=", "auto"
            ]
            
            subprocess.run(cmd2, capture_output=True, text=True, check=True)
            logger.debug("Service startup configuration completed")
            
            logger.info("FR-001 service configuration completed")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Service FR-001 configuration failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in service configuration: {e}")
            return False
    
    def _start_service_safe(self) -> bool:
        """Start the service safely with error handling"""
        try:
            logger.info("Starting MeetingScribe service...")
            
            win32serviceutil.StartService(self.service_name)
            
            # Wait for service to initialize
            import time
            time.sleep(3.0)
            
            # Verify service is running
            status = self._get_service_status()
            if status.get("state") == "running":
                logger.info("✅ Service started successfully")
                return True
            else:
                logger.warning(f"Service start uncertain, status: {status}")
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
                        "exit_code": status[3]
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
            if status.get("state") not in ["running", "starting"]:
                logger.warning(f"Service not running after installation: {status}")
                # Try to start it once more
                if not self._start_service_safe():
                    return False
            
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
        """Log installation summary with management information"""
        status = self._get_service_status()
        
        logger.info("=== MeetingScribe Service Installation Summary ===")
        logger.info(f"Service Name: {self.service_name}")
        logger.info(f"Display Name: {self.service_display_name}")
        logger.info(f"Status: {status.get('state', 'unknown')}")
        logger.info("Auto-Start: Enabled")
        logger.info("Recovery: Auto-restart on failure")
        logger.info("FR-001 Compliance: Always-Ready System configured")
        logger.info("")
        logger.info("Service Management Commands:")
        logger.info(f"  Start: sc start {self.service_name}")
        logger.info(f"  Stop: sc stop {self.service_name}")
        logger.info(f"  Status: sc query {self.service_name}")
        logger.info("  Uninstall: python daemon\\service_installer.py uninstall")
    
    def get_installation_status(self) -> Dict[str, Any]:
        """
        Get comprehensive installation status for monitoring.
        
        Returns:
            Dictionary containing installation status, service state, and configuration
        """
        return {
            "installed": self._is_service_installed(),
            "status": self._get_service_status(),
            "has_admin_privileges": self._check_admin_privileges(),
            "prerequisites_ok": self._check_prerequisites(),
            "service_name": self.service_name,
            "service_display_name": self.service_display_name
        }


def install_service() -> bool:
    """
    Install MeetingScribe Windows Service automatically.
    
    Performs one-click installation with FR-001 compliance configuration.
    Requires administrative privileges.
    
    Returns:
        bool: True if installation successful
    """
    installer = WindowsServiceInstaller()
    return installer.install_service_automatic()


def uninstall_service() -> bool:
    """
    Uninstall MeetingScribe Windows Service.
    
    Returns:
        bool: True if uninstallation successful
    """
    installer = WindowsServiceInstaller()
    return installer.uninstall_service_automatic()


def get_service_status() -> Dict[str, Any]:
    """
    Get comprehensive service installation and runtime status.
    
    Returns:
        Dictionary containing installation status, service state, and configuration
    """
    installer = WindowsServiceInstaller()
    return installer.get_installation_status()


def main():
    """CLI entry point for service installer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MeetingScribe Windows Service Installer")
    parser.add_argument("action", choices=["install", "uninstall", "status"], 
                       help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == "install":
        success = install_service()
        sys.exit(0 if success else 1)
    elif args.action == "uninstall":
        success = uninstall_service()
        sys.exit(0 if success else 1)
    elif args.action == "status":
        status = get_service_status()
        import json
        print(json.dumps(status, indent=2))
        sys.exit(0)


if __name__ == "__main__":
    main()