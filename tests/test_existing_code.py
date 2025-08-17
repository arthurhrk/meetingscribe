"""
Comprehensive tests for existing MeetingScribe codebase.

Tests the current implementation to ensure stability before architecture evolution.
Covers config.py, main.py, system_check.py with extensive scenarios.

Author: MeetingScribe Team
Python: >=3.8
Framework: pytest
"""

import pytest
import os
import sys
import json
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO
import subprocess

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import modules under test
import config
from config import Settings, setup_directories, setup_logging
import main
import system_check


class TestConfigModule:
    """Test suite for config.py module."""

    def test_settings_default_values(self):
        """Test Settings class default values."""
        settings = Settings()
        
        assert settings.app_name == "MeetingScribe"
        assert settings.app_version == "1.0.0"
        assert settings.debug is True
        assert settings.log_level == "DEBUG"
        assert settings.audio_sample_rate == 16000
        assert settings.audio_channels == 1
        assert settings.chunk_duration == 30
        assert settings.whisper_model == "base"
        assert settings.whisper_language == "pt"
        assert settings.whisper_device == "auto"

    def test_settings_paths_resolution(self):
        """Test that path attributes resolve correctly."""
        settings = Settings()
        
        # Test base directory resolution
        assert settings.base_dir.exists()
        assert settings.base_dir.is_dir()
        
        # Test relative path construction
        assert settings.storage_dir == settings.base_dir / "storage"
        assert settings.models_dir == settings.base_dir / "models"
        assert settings.logs_dir == settings.base_dir / "logs"
        assert settings.recordings_dir == settings.base_dir / "storage" / "recordings"
        assert settings.transcriptions_dir == settings.base_dir / "storage" / "transcriptions"
        assert settings.exports_dir == settings.base_dir / "storage" / "exports"

    @patch.dict(os.environ, {
        'APP_NAME': 'TestApp',
        'DEBUG': 'false',
        'AUDIO_SAMPLE_RATE': '44100',
        'WHISPER_MODEL': 'large-v3'
    })
    def test_settings_environment_variables(self):
        """Test Settings loading from environment variables."""
        settings = Settings()
        
        assert settings.app_name == "TestApp"
        assert settings.debug is False
        assert settings.audio_sample_rate == 44100
        assert settings.whisper_model == "large-v3"

    def test_settings_validation_types(self):
        """Test Pydantic type validation."""
        # Test valid values
        settings = Settings(
            audio_sample_rate=48000,
            audio_channels=2,
            debug=False
        )
        assert settings.audio_sample_rate == 48000
        assert settings.audio_channels == 2
        assert settings.debug is False

        # Test invalid types (should raise ValidationError)
        with pytest.raises(Exception):  # Pydantic ValidationError
            Settings(audio_sample_rate="invalid")

    @patch('config.Path.mkdir')
    def test_setup_directories_success(self, mock_mkdir):
        """Test successful directory setup."""
        with patch('config.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.storage_dir = Path("/test/storage")
            mock_settings.models_dir = Path("/test/models")
            mock_settings.logs_dir = Path("/test/logs")
            mock_settings.recordings_dir = Path("/test/storage/recordings")
            mock_settings.transcriptions_dir = Path("/test/storage/transcriptions")
            mock_settings.exports_dir = Path("/test/storage/exports")
            
            mock_settings_class.return_value = mock_settings
            
            with patch('config.logger') as mock_logger:
                setup_directories()
                
                # Verify mkdir called for each directory
                assert mock_mkdir.call_count == 6
                mock_mkdir.assert_has_calls([
                    call(parents=True, exist_ok=True),
                    call(parents=True, exist_ok=True),
                    call(parents=True, exist_ok=True),
                    call(parents=True, exist_ok=True),
                    call(parents=True, exist_ok=True),
                    call(parents=True, exist_ok=True)
                ], any_order=True)
                
                # Verify logging
                assert mock_logger.info.call_count == 6

    @patch('config.Path.mkdir')
    def test_setup_directories_permission_error(self, mock_mkdir):
        """Test directory setup with permission error."""
        mock_mkdir.side_effect = PermissionError("Permission denied")
        
        with patch('config.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.storage_dir = Path("/test/storage")
            mock_settings.models_dir = Path("/test/models")
            mock_settings.logs_dir = Path("/test/logs")
            mock_settings.recordings_dir = Path("/test/storage/recordings")
            mock_settings.transcriptions_dir = Path("/test/storage/transcriptions")
            mock_settings.exports_dir = Path("/test/storage/exports")
            
            mock_settings_class.return_value = mock_settings
            
            with pytest.raises(PermissionError):
                setup_directories()

    @patch('config.logger')
    def test_setup_logging_configuration(self, mock_logger):
        """Test logging setup configuration."""
        with patch('config.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.logs_dir = Path("/test/logs")
            mock_settings.log_level = "INFO"
            mock_settings.debug = True
            
            mock_settings_class.return_value = mock_settings
            
            setup_logging()
            
            # Verify logger configuration calls
            mock_logger.remove.assert_called_once()
            assert mock_logger.add.call_count == 2  # File + console logging
            
            # Verify file logging configuration
            file_log_call = mock_logger.add.call_args_list[0]
            assert "rotation" in file_log_call[1]
            assert "retention" in file_log_call[1]
            assert file_log_call[1]["level"] == "INFO"

    @patch('config.logger')
    def test_setup_logging_debug_disabled(self, mock_logger):
        """Test logging setup with debug disabled."""
        with patch('config.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.logs_dir = Path("/test/logs")
            mock_settings.log_level = "ERROR"
            mock_settings.debug = False
            
            mock_settings_class.return_value = mock_settings
            
            setup_logging()
            
            # Verify only file logging when debug is disabled
            mock_logger.remove.assert_called_once()
            assert mock_logger.add.call_count == 1  # Only file logging

    def test_settings_singleton_behavior(self):
        """Test that settings behaves as expected for singleton pattern."""
        # The module creates a global settings instance
        assert hasattr(config, 'settings')
        assert isinstance(config.settings, Settings)
        
        # Verify it's accessible and has expected values
        assert config.settings.app_name == "MeetingScribe"


class TestMainModule:
    """Test suite for main.py module."""

    @patch('main.console')
    @patch('main.settings')
    def test_show_welcome_message_success(self, mock_settings, mock_console):
        """Test successful welcome message display."""
        mock_settings.app_version = "1.0.0"
        
        main.show_welcome_message()
        
        # Verify console.print was called
        assert mock_console.print.call_count >= 3  # Empty line + Panel + Empty line

    @patch('main.console')
    @patch('main.settings')
    @patch('main.logger')
    def test_show_welcome_message_error_handling(self, mock_logger, mock_settings, mock_console):
        """Test welcome message error handling."""
        mock_settings.app_version = "1.0.0"
        mock_console.print.side_effect = [None, Exception("Console error"), None]
        
        with pytest.raises(RuntimeError):
            main.show_welcome_message()
        
        # Verify error was logged
        mock_logger.error.assert_called_once()

    @patch('main.setup_directories')
    @patch('main.setup_logging')
    @patch('main.logger')
    @patch('main.console')
    def test_initialize_system_success(self, mock_console, mock_logger, mock_setup_logging, mock_setup_directories):
        """Test successful system initialization."""
        # Mock Progress context manager
        mock_progress = MagicMock()
        mock_task = MagicMock()
        mock_progress.add_task.return_value = mock_task
        
        with patch('main.Progress') as mock_progress_class:
            mock_progress_class.return_value.__enter__.return_value = mock_progress
            
            main.initialize_system()
            
            # Verify setup functions were called
            mock_setup_directories.assert_called_once()
            mock_setup_logging.assert_called_once()
            
            # Verify progress tasks were created
            assert mock_progress.add_task.call_count == 3

    @patch('main.setup_directories')
    @patch('main.logger')
    @patch('main.console')
    def test_initialize_system_directory_error(self, mock_console, mock_logger, mock_setup_directories):
        """Test initialization with directory setup error."""
        mock_setup_directories.side_effect = PermissionError("Permission denied")
        
        mock_progress = MagicMock()
        with patch('main.Progress') as mock_progress_class:
            mock_progress_class.return_value.__enter__.return_value = mock_progress
            
            with pytest.raises(RuntimeError):
                main.initialize_system()
            
            # Verify error was logged
            mock_logger.error.assert_called()

    @patch('main.setup_directories')
    @patch('main.setup_logging')
    @patch('main.logger')
    @patch('main.console')
    def test_initialize_system_logging_error(self, mock_console, mock_logger, mock_setup_logging, mock_setup_directories):
        """Test initialization with logging setup error."""
        mock_setup_logging.side_effect = FileNotFoundError("Log directory not found")
        
        mock_progress = MagicMock()
        with patch('main.Progress') as mock_progress_class:
            mock_progress_class.return_value.__enter__.return_value = mock_progress
            
            with pytest.raises(RuntimeError):
                main.initialize_system()

    @patch('main.settings')
    @patch('main.logger')
    @patch('main.console')
    def test_initialize_system_configuration_validation(self, mock_console, mock_logger, mock_settings):
        """Test initialization configuration validation."""
        # Test missing app_name
        mock_settings.app_name = ""
        
        mock_progress = MagicMock()
        with patch('main.Progress') as mock_progress_class:
            mock_progress_class.return_value.__enter__.return_value = mock_progress
            with patch('main.setup_directories'), patch('main.setup_logging'):
                
                with pytest.raises(RuntimeError):
                    main.initialize_system()

    def test_module_imports(self):
        """Test that all required modules can be imported."""
        # This test ensures all imports in main.py work
        import main
        
        # Verify key functions exist
        assert hasattr(main, 'initialize_system')
        assert hasattr(main, 'show_welcome_message')
        assert callable(main.initialize_system)
        assert callable(main.show_welcome_message)

    @patch('main.sys.argv', ['main.py', '--json'])
    def test_json_mode_detection(self):
        """Test JSON mode detection from command line."""
        # Reload module to trigger JSON_MODE detection
        import importlib
        importlib.reload(main)
        
        # Verify JSON_MODE is set (this is a module-level variable)
        # Since it's set during import, we need to check indirectly


class TestSystemCheckModule:
    """Test suite for system_check.py module."""

    def test_check_python_version_valid(self):
        """Test Python version check with valid version."""
        with patch('system_check.sys.version_info', (3, 9, 0)):
            is_valid, details = system_check.check_python_version()
            
            assert is_valid is True
            assert "Python 3.9.0" in details

    def test_check_python_version_invalid(self):
        """Test Python version check with invalid version."""
        with patch('system_check.sys.version_info', (3, 7, 0)):
            is_valid, details = system_check.check_python_version()
            
            assert is_valid is False
            assert "Python 3.7.0" in details
            assert "Requerido: >= 3.8" in details

    @patch('system_check.importlib.import_module')
    def test_check_dependencies_all_available(self, mock_import):
        """Test dependency check when all dependencies are available."""
        mock_module = Mock()
        mock_module.__version__ = "1.0.0"
        mock_import.return_value = mock_module
        
        result = system_check.check_dependencies()
        
        assert len(result) == 5  # Expected number of dependencies
        for dep_name, (status, details) in result.items():
            if dep_name != 'pyaudiowpatch':  # Special handling for pyaudiowpatch
                assert status is True
                assert "v1.0.0" in details

    @patch('system_check.importlib.import_module')
    def test_check_dependencies_missing(self, mock_import):
        """Test dependency check with missing dependencies."""
        mock_import.side_effect = ImportError("Module not found")
        
        result = system_check.check_dependencies()
        
        for dep_name, (status, details) in result.items():
            assert status is False
            assert "Não instalado" in details

    @patch('system_check.importlib.import_module')
    def test_check_dependencies_pyaudiowpatch_fallback(self, mock_import):
        """Test pyaudiowpatch fallback to regular pyaudio."""
        def import_side_effect(module_name):
            if module_name == 'pyaudiowpatch':
                raise ImportError("pyaudiowpatch not found")
            elif module_name == 'pyaudio':
                mock_module = Mock()
                mock_module.__version__ = "0.2.11"
                return mock_module
            else:
                mock_module = Mock()
                mock_module.__version__ = "1.0.0"
                return mock_module
        
        mock_import.side_effect = import_side_effect
        
        result = system_check.check_dependencies()
        
        assert result['pyaudiowpatch'][0] is True
        assert "pyaudio v0.2.11 (fallback)" in result['pyaudiowpatch'][1]

    def test_check_directory_structure_all_exist(self):
        """Test directory structure check when all directories exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # Create required directories
            required_dirs = [
                'src', 'storage', 'models', 'logs', 'tests',
                'storage/recordings', 'storage/transcriptions', 'storage/exports'
            ]
            
            for dir_name in required_dirs:
                (base_path / dir_name).mkdir(parents=True, exist_ok=True)
            
            with patch('system_check.Path(__file__).parent', base_path):
                result = system_check.check_directory_structure()
                
                for dir_name, (status, details) in result.items():
                    assert status is True
                    assert details == "Existe"

    def test_check_directory_structure_missing_dirs(self):
        """Test directory structure check with missing directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            with patch('system_check.Path(__file__).parent', base_path):
                result = system_check.check_directory_structure()
                
                for dir_name, (status, details) in result.items():
                    assert status is False
                    assert details == "Não encontrado"

    def test_check_config_file_exists(self):
        """Test config file check when file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            config_file = base_path / 'config.py'
            config_file.touch()
            
            with patch('system_check.Path(__file__).parent', base_path):
                is_valid, details = system_check.check_config_file()
                
                assert is_valid is True
                assert details == "Arquivo existe"

    def test_check_config_file_missing(self):
        """Test config file check when file is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            with patch('system_check.Path(__file__).parent', base_path):
                is_valid, details = system_check.check_config_file()
                
                assert is_valid is False
                assert details == "Arquivo não encontrado"

    @patch('system_check.JSON_MODE', True)
    @patch('system_check.os.environ', {'LOG_LEVEL': 'CRITICAL'})
    @patch('system_check.sys.stderr', StringIO())
    def test_check_audio_system_json_mode(self):
        """Test audio system check in JSON mode."""
        with patch('system_check.importlib.import_module') as mock_import:
            mock_import.side_effect = ImportError("pyaudiowpatch not available")
            
            result = system_check.check_audio_system()
            
            assert 'PyAudio WASAPI' in result
            assert result['PyAudio WASAPI'][0] is False

    @patch('system_check.importlib.import_module')
    def test_check_audio_system_pyaudio_available(self, mock_import):
        """Test audio system check with pyaudiowpatch available."""
        mock_pyaudio = Mock()
        mock_audio_instance = Mock()
        mock_audio_instance.get_device_count.return_value = 5
        mock_audio_instance.get_device_info_by_index.return_value = {
            'name': 'Test Device',
            'hostApi': 0,
            'maxInputChannels': 2,
            'maxOutputChannels': 0
        }
        mock_audio_instance.get_host_api_info_by_index.return_value = {
            'name': 'WASAPI'
        }
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        def import_side_effect(module_name):
            if module_name == 'pyaudiowpatch':
                return mock_pyaudio
            else:
                raise ImportError("Module not found")
        
        mock_import.side_effect = import_side_effect
        
        result = system_check.check_audio_system()
        
        assert result['PyAudio WASAPI'][0] is True
        assert result['Total Devices'][0] is True
        assert "5 dispositivos" in result['Total Devices'][1]

    def test_create_status_table(self):
        """Test status table creation."""
        test_checks = {
            "Sistema": [
                ("Python", True, "Python 3.9.0"),
                ("Config", False, "Não encontrado")
            ],
            "Audio": [
                ("WASAPI", True, "Disponível")
            ]
        }
        
        table = system_check.create_status_table(test_checks)
        
        # Verify table structure
        assert table.title is not None
        assert len(table.columns) == 4

    @patch('system_check.subprocess.run')
    def test_main_json_output(self, mock_subprocess):
        """Test main function with JSON output."""
        # Mock all check functions
        with patch('system_check.check_python_version', return_value=(True, "Python 3.9.0")), \
             patch('system_check.check_dependencies', return_value={"rich": (True, "v1.0.0")}), \
             patch('system_check.check_directory_structure', return_value={"src": (True, "Existe")}), \
             patch('system_check.check_config_file', return_value=(True, "Arquivo existe")), \
             patch('system_check.check_audio_system', return_value={"WASAPI": (True, "Disponível")}), \
             patch('system_check.sys.argv', ['system_check.py', '--json']):
            
            # Capture stdout
            with patch('builtins.print') as mock_print:
                result = system_check.main()
                
                assert result is True
                # Verify JSON output was printed
                mock_print.assert_called()
                
                # Check if the output looks like JSON
                output_call = mock_print.call_args[0][0]
                try:
                    json.loads(output_call)
                except json.JSONDecodeError:
                    pytest.fail("Output is not valid JSON")

    def test_main_interactive_mode(self):
        """Test main function in interactive mode."""
        with patch('system_check.check_python_version', return_value=(True, "Python 3.9.0")), \
             patch('system_check.check_dependencies', return_value={"rich": (True, "v1.0.0")}), \
             patch('system_check.check_directory_structure', return_value={"src": (True, "Existe")}), \
             patch('system_check.check_config_file', return_value=(True, "Arquivo existe")), \
             patch('system_check.check_audio_system', return_value={"WASAPI": (True, "Disponível")}), \
             patch('system_check.sys.argv', ['system_check.py']), \
             patch('system_check.console') as mock_console:
            
            result = system_check.main()
            
            assert result is True
            # Verify console output
            assert mock_console.print.call_count >= 2

    def test_main_with_failures(self):
        """Test main function with some checks failing."""
        with patch('system_check.check_python_version', return_value=(False, "Python 3.7.0")), \
             patch('system_check.check_dependencies', return_value={"rich": (False, "Não instalado")}), \
             patch('system_check.check_directory_structure', return_value={"src": (False, "Não encontrado")}), \
             patch('system_check.check_config_file', return_value=(False, "Arquivo não encontrado")), \
             patch('system_check.check_audio_system', return_value={"WASAPI": (False, "Não disponível")}), \
             patch('system_check.sys.argv', ['system_check.py']), \
             patch('system_check.console'):
            
            result = system_check.main()
            
            assert result is False


class TestFileSystemOperations:
    """Test file system operations across modules."""

    def test_path_handling_windows_compatibility(self):
        """Test path handling for Windows compatibility."""
        settings = Settings()
        
        # Verify Path objects are used (Windows-compatible)
        assert isinstance(settings.base_dir, Path)
        assert isinstance(settings.storage_dir, Path)
        
        # Test path joining
        test_path = settings.base_dir / "test" / "subdir"
        assert isinstance(test_path, Path)

    @patch('config.Path.mkdir')
    def test_directory_creation_with_permissions(self, mock_mkdir):
        """Test directory creation with permission handling."""
        mock_mkdir.side_effect = [None, PermissionError("Access denied"), None]
        
        with patch('config.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.storage_dir = Path("/test/storage")
            mock_settings.models_dir = Path("/test/models")
            mock_settings.logs_dir = Path("/test/logs")
            mock_settings.recordings_dir = Path("/test/storage/recordings")
            mock_settings.transcriptions_dir = Path("/test/storage/transcriptions")
            mock_settings.exports_dir = Path("/test/storage/exports")
            
            mock_settings_class.return_value = mock_settings
            
            with pytest.raises(PermissionError):
                setup_directories()

    def test_path_resolution_edge_cases(self):
        """Test path resolution edge cases."""
        settings = Settings()
        
        # Test that paths are absolute or properly resolved
        assert settings.base_dir.is_absolute() or settings.base_dir.resolve().is_absolute()
        
        # Test nested path construction
        nested_path = settings.storage_dir / "recordings" / "subdirectory"
        assert nested_path.parent.parent == settings.storage_dir


class TestRichUIComponents:
    """Test Rich UI components and console output."""

    @patch('main.console')
    def test_console_panel_creation(self, mock_console):
        """Test Rich Panel creation in welcome message."""
        with patch('main.settings') as mock_settings:
            mock_settings.app_version = "1.0.0"
            
            main.show_welcome_message()
            
            # Verify Panel was created and printed
            assert mock_console.print.called
            
            # Check that a Panel object was passed to print
            print_calls = mock_console.print.call_args_list
            panel_call = next((call for call in print_calls if call[0]), None)
            assert panel_call is not None

    @patch('main.console')
    def test_progress_bar_creation(self, mock_console):
        """Test Progress bar creation in initialization."""
        mock_progress = MagicMock()
        
        with patch('main.Progress') as mock_progress_class, \
             patch('main.setup_directories'), \
             patch('main.setup_logging'), \
             patch('main.settings'):
            
            mock_progress_class.return_value.__enter__.return_value = mock_progress
            
            main.initialize_system()
            
            # Verify Progress context manager was used
            mock_progress_class.assert_called_once()

    def test_rich_text_formatting(self):
        """Test Rich Text object creation and formatting."""
        from rich.text import Text
        from rich.panel import Panel
        
        # Test creating Text object like in show_welcome_message
        text = Text()
        text.append("[MIC] ", style="bold blue")
        text.append("MeetingScribe", style="bold blue")
        text.append(" v1.0.0", style="dim")
        
        # Verify text content
        assert "[MIC] " in str(text)
        assert "MeetingScribe" in str(text)
        
        # Test Panel creation
        panel = Panel(text, title="Test", border_style="blue")
        assert panel.title == "Test"


class TestLoggingBehavior:
    """Test Loguru logging behavior and configuration."""

    @patch('config.logger')
    def test_logging_file_rotation(self, mock_logger):
        """Test logging file rotation configuration."""
        with patch('config.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.logs_dir = Path("/test/logs")
            mock_settings.log_level = "DEBUG"
            mock_settings.debug = True
            
            mock_settings_class.return_value = mock_settings
            
            setup_logging()
            
            # Verify rotation parameter was set
            file_log_call = mock_logger.add.call_args_list[0]
            assert file_log_call[1]["rotation"] == "10 MB"
            assert file_log_call[1]["retention"] == "1 month"

    @patch('config.logger')
    def test_logging_format_configuration(self, mock_logger):
        """Test logging format configuration."""
        with patch('config.Settings') as mock_settings_class:
            mock_settings = Mock()
            mock_settings.logs_dir = Path("/test/logs")
            mock_settings.log_level = "INFO"
            mock_settings.debug = False
            
            mock_settings_class.return_value = mock_settings
            
            setup_logging()
            
            # Verify format string
            file_log_call = mock_logger.add.call_args_list[0]
            format_str = file_log_call[1]["format"]
            assert "{time:" in format_str
            assert "{level}" in format_str
            assert "{message}" in format_str

    @patch('config.logger')
    def test_logging_level_configuration(self, mock_logger):
        """Test different logging levels."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        
        for level in levels:
            with patch('config.Settings') as mock_settings_class:
                mock_settings = Mock()
                mock_settings.logs_dir = Path("/test/logs")
                mock_settings.log_level = level
                mock_settings.debug = False
                
                mock_settings_class.return_value = mock_settings
                
                setup_logging()
                
                # Verify level was set correctly
                file_log_call = mock_logger.add.call_args_list[0]
                assert file_log_call[1]["level"] == level
                
                # Reset for next iteration
                mock_logger.reset_mock()


class TestPerformanceAndTiming:
    """Test performance characteristics and timing."""

    def test_settings_instantiation_time(self):
        """Test Settings instantiation performance."""
        start_time = time.time()
        
        for _ in range(100):
            Settings()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should be able to create 100 Settings instances in under 1 second
        assert total_time < 1.0

    @patch('main.setup_directories')
    @patch('main.setup_logging')
    def test_initialize_system_timing(self, mock_setup_logging, mock_setup_directories):
        """Test initialization system timing."""
        with patch('main.console'), \
             patch('main.Progress') as mock_progress_class, \
             patch('main.settings'):
            
            mock_progress = MagicMock()
            mock_progress_class.return_value.__enter__.return_value = mock_progress
            
            start_time = time.time()
            main.initialize_system()
            end_time = time.time()
            
            initialization_time = end_time - start_time
            
            # Initialization should be fast (under 0.1 seconds when mocked)
            assert initialization_time < 0.1

    def test_dependency_check_timing(self):
        """Test dependency check performance."""
        with patch('system_check.importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.__version__ = "1.0.0"
            mock_import.return_value = mock_module
            
            start_time = time.time()
            result = system_check.check_dependencies()
            end_time = time.time()
            
            check_time = end_time - start_time
            
            # Dependency check should be fast
            assert check_time < 0.5
            assert len(result) > 0


class TestIntegrationBetweenModules:
    """Test integration between different modules."""

    def test_config_to_main_integration(self):
        """Test integration between config and main modules."""
        # Test that main can access config settings
        assert hasattr(main, 'settings')
        
        # Test that config functions are accessible from main
        with patch('main.setup_directories') as mock_setup_directories, \
             patch('main.setup_logging') as mock_setup_logging, \
             patch('main.console'), \
             patch('main.Progress') as mock_progress_class:
            
            mock_progress = MagicMock()
            mock_progress_class.return_value.__enter__.return_value = mock_progress
            
            main.initialize_system()
            
            # Verify config functions were called
            mock_setup_directories.assert_called_once()
            mock_setup_logging.assert_called_once()

    def test_system_check_to_config_integration(self):
        """Test integration between system_check and config modules."""
        # Test that system_check can validate config
        with patch('system_check.Path(__file__).parent') as mock_parent:
            mock_parent.return_value = Path("/test")
            (mock_parent.return_value / "config.py").touch = Mock()
            (mock_parent.return_value / "config.py").exists = Mock(return_value=True)
            
            with patch.object(Path, 'exists', return_value=True):
                is_valid, details = system_check.check_config_file()
                
                assert is_valid is True

    @patch('main.console')
    def test_full_startup_sequence(self, mock_console):
        """Test full startup sequence integration."""
        with patch('main.setup_directories'), \
             patch('main.setup_logging'), \
             patch('main.Progress') as mock_progress_class, \
             patch('main.settings') as mock_settings:
            
            mock_settings.app_version = "1.0.0"
            mock_settings.app_name = "MeetingScribe"
            
            mock_progress = MagicMock()
            mock_progress_class.return_value.__enter__.return_value = mock_progress
            
            # Test initialization followed by welcome message
            main.initialize_system()
            main.show_welcome_message()
            
            # Verify both functions completed successfully
            assert mock_console.print.called

    def test_error_propagation_between_modules(self):
        """Test error propagation between modules."""
        # Test that config errors propagate to main
        with patch('main.setup_directories') as mock_setup_directories:
            mock_setup_directories.side_effect = PermissionError("Access denied")
            
            with patch('main.console'), \
                 patch('main.Progress') as mock_progress_class:
                
                mock_progress = MagicMock()
                mock_progress_class.return_value.__enter__.return_value = mock_progress
                
                with pytest.raises(RuntimeError):
                    main.initialize_system()


class TestErrorConditionsAndEdgeCases:
    """Test error conditions and edge cases."""

    def test_missing_environment_file(self):
        """Test behavior when .env file is missing."""
        # This should not raise an error, just use defaults
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.app_name == "MeetingScribe"  # Default value

    def test_invalid_environment_values(self):
        """Test handling of invalid environment values."""
        with patch.dict(os.environ, {'AUDIO_SAMPLE_RATE': 'invalid_number'}):
            with pytest.raises(Exception):  # Pydantic ValidationError
                Settings()

    def test_file_system_full_scenario(self):
        """Test behavior when file system is full."""
        with patch('config.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = OSError("No space left on device")
            
            with patch('config.Settings') as mock_settings_class:
                mock_settings = Mock()
                mock_settings.storage_dir = Path("/test/storage")
                mock_settings_class.return_value = mock_settings
                
                with pytest.raises(OSError):
                    setup_directories()

    def test_permission_denied_scenarios(self):
        """Test various permission denied scenarios."""
        # Test directory creation permission denied
        with patch('config.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Permission denied")
            
            with patch('config.Settings'):
                with pytest.raises(PermissionError):
                    setup_directories()

    @patch('main.console')
    def test_console_output_failure(self, mock_console):
        """Test handling of console output failures."""
        mock_console.print.side_effect = Exception("Console error")
        
        with patch('main.settings') as mock_settings:
            mock_settings.app_version = "1.0.0"
            
            # Should raise RuntimeError due to console failure
            with pytest.raises(RuntimeError):
                main.show_welcome_message()

    def test_import_error_handling(self):
        """Test handling of import errors in system_check."""
        with patch('system_check.importlib.import_module') as mock_import:
            mock_import.side_effect = ImportError("Module not found")
            
            result = system_check.check_dependencies()
            
            # All dependencies should be marked as not available
            for dep_name, (status, details) in result.items():
                assert status is False


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--durations=10"
    ])