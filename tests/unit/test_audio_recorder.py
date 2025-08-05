"""
Testes unitários para AudioRecorder

Testa funcionalidades de gravação de áudio com mocks.

Author: MeetingScribe Team
Version: 1.0.0
Python: >=3.8
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audio_recorder import (
    AudioRecorder,
    RecordingConfig,
    RecordingStats,
    AudioRecorderError,
    RecordingInProgressError,
    create_recorder_from_config
)
from device_manager import AudioDevice


class TestRecordingConfig(unittest.TestCase):
    """Testes para RecordingConfig"""
    
    def test_recording_config_creation(self):
        """Testa criação de RecordingConfig"""
        device = AudioDevice(
            index=0,
            name="Test Device",
            max_input_channels=2,
            max_output_channels=2,
            default_sample_rate=44100.0,
            host_api="Windows WASAPI"
        )
        
        config = RecordingConfig(
            device=device,
            sample_rate=16000,
            channels=1,
            chunk_size=1024
        )
        
        self.assertEqual(config.device, device)
        self.assertEqual(config.sample_rate, 16000)
        self.assertEqual(config.channels, 1)
        self.assertEqual(config.chunk_size, 1024)
        self.assertIsNone(config.max_duration)
    
    def test_recording_config_defaults(self):
        """Testa valores padrão de RecordingConfig"""
        device = AudioDevice(0, "Test", 1, 1, 44100.0, "Test API")
        
        config = RecordingConfig(device=device)
        
        self.assertEqual(config.sample_rate, 16000)
        self.assertEqual(config.channels, 1)
        self.assertEqual(config.chunk_size, 1024)


class TestRecordingStats(unittest.TestCase):
    """Testes para RecordingStats"""
    
    def test_recording_stats_creation(self):
        """Testa criação de RecordingStats"""
        start_time = datetime.now()
        
        stats = RecordingStats(start_time=start_time)
        
        self.assertEqual(stats.start_time, start_time)
        self.assertIsNone(stats.end_time)
        self.assertEqual(stats.duration, 0.0)
        self.assertEqual(stats.file_size, 0)
        self.assertEqual(stats.samples_recorded, 0)
        self.assertIsNone(stats.filename)


class TestAudioRecorder(unittest.TestCase):
    """Testes para AudioRecorder"""
    
    def setUp(self):
        """Setup para cada teste"""
        self.mock_device = AudioDevice(
            index=0,
            name="Test Speakers [Loopback]",
            max_input_channels=2,
            max_output_channels=0,
            default_sample_rate=44100.0,
            host_api="Windows WASAPI",
            is_loopback=True
        )
        
        self.test_config = RecordingConfig(
            device=self.mock_device,
            sample_rate=16000,
            channels=1,
            output_dir=Path(tempfile.gettempdir())
        )
    
    @patch('audio_recorder.PYAUDIO_AVAILABLE', False)
    def test_audio_recorder_pyaudio_not_available(self):
        """Testa erro quando PyAudio não está disponível"""
        with self.assertRaises(AudioRecorderError):
            AudioRecorder()
    
    @patch('audio_recorder.pyaudio')
    def test_audio_recorder_initialization(self, mock_pyaudio):
        """Testa inicialização do AudioRecorder"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        with patch('audio_recorder.PYAUDIO_AVAILABLE', True):
            recorder = AudioRecorder(self.test_config)
            
            self.assertEqual(recorder._config, self.test_config)
            self.assertIsNotNone(recorder._audio)
            self.assertFalse(recorder._recording)
            
            recorder.close()
    
    @patch('audio_recorder.pyaudio')
    def test_set_device_auto(self, mock_pyaudio):
        """Testa configuração automática de dispositivo"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        with patch('audio_recorder.PYAUDIO_AVAILABLE', True):
            recorder = AudioRecorder()
            
            # Mock DeviceManager
            mock_dm = Mock()
            mock_dm.get_default_speakers.return_value = self.mock_device
            mock_dm.get_devices_by_api.return_value = [self.mock_device]
            
            with patch('audio_recorder.DeviceManager', return_value=mock_dm):
                result = recorder.set_device_auto()
                
                self.assertTrue(result)
                self.assertIsNotNone(recorder._config)
                self.assertEqual(recorder._config.device, self.mock_device)
            
            recorder.close()
    
    @patch('audio_recorder.pyaudio')
    def test_start_recording_success(self, mock_pyaudio):
        """Testa início de gravação bem-sucedido"""
        mock_audio_instance = Mock()
        mock_stream = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        mock_audio_instance.open.return_value = mock_stream
        
        with patch('audio_recorder.PYAUDIO_AVAILABLE', True):
            recorder = AudioRecorder(self.test_config)
            
            with patch('pathlib.Path.mkdir'):
                filepath = recorder.start_recording("test_recording")
                
                self.assertTrue(recorder.is_recording())
                self.assertIsNotNone(recorder._stats)
                self.assertEqual(recorder._stats.filename, filepath)
                
                # Verificar se stream foi aberto
                mock_audio_instance.open.assert_called_once()
                
                # Parar gravação
                recorder.stop_recording()
            
            recorder.close()
    
    @patch('audio_recorder.pyaudio')
    def test_start_recording_already_in_progress(self, mock_pyaudio):
        """Testa erro ao tentar iniciar gravação quando já está gravando"""
        mock_audio_instance = Mock()
        mock_stream = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        mock_audio_instance.open.return_value = mock_stream
        
        with patch('audio_recorder.PYAUDIO_AVAILABLE', True):
            recorder = AudioRecorder(self.test_config)
            recorder._recording = True  # Simular gravação em andamento
            
            with self.assertRaises(RecordingInProgressError):
                recorder.start_recording("test")
            
            recorder.close()
    
    @patch('audio_recorder.pyaudio')
    def test_stop_recording_success(self, mock_pyaudio):
        """Testa parada de gravação bem-sucedida"""
        mock_audio_instance = Mock()
        mock_stream = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        mock_audio_instance.open.return_value = mock_stream
        mock_audio_instance.get_sample_size.return_value = 2
        
        with patch('audio_recorder.PYAUDIO_AVAILABLE', True):
            recorder = AudioRecorder(self.test_config)
            
            # Simular gravação em andamento
            recorder._recording = True
            recorder._stream = mock_stream
            recorder._frames = [b'test_data'] * 10
            recorder._stats = RecordingStats(start_time=datetime.now())
            
            # Mock do arquivo wave
            mock_wave_file = Mock()
            
            with patch('wave.open', mock_open()) as mock_file:
                with patch('wave.open', return_value=mock_wave_file):
                    with patch('pathlib.Path.stat') as mock_stat:
                        mock_stat.return_value.st_size = 1024
                        
                        stats = recorder.stop_recording()
                        
                        self.assertFalse(recorder.is_recording())
                        self.assertIsNotNone(stats.end_time)
                        self.assertGreater(stats.duration, 0)
                        self.assertEqual(stats.file_size, 1024)
            
            recorder.close()
    
    @patch('audio_recorder.pyaudio')
    def test_stop_recording_not_in_progress(self, mock_pyaudio):
        """Testa erro ao tentar parar gravação quando não está gravando"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        with patch('audio_recorder.PYAUDIO_AVAILABLE', True):
            recorder = AudioRecorder(self.test_config)
            
            with self.assertRaises(AudioRecorderError):
                recorder.stop_recording()
            
            recorder.close()
    
    @patch('audio_recorder.pyaudio')
    def test_context_manager(self, mock_pyaudio):
        """Testa uso como context manager"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        with patch('audio_recorder.PYAUDIO_AVAILABLE', True):
            with AudioRecorder(self.test_config) as recorder:
                self.assertIsNotNone(recorder._audio)
            
            # Verificar se close foi chamado
            mock_audio_instance.terminate.assert_called_once()
    
    @patch('audio_recorder.pyaudio')
    def test_get_current_stats(self, mock_pyaudio):
        """Testa obtenção de estatísticas atuais"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        with patch('audio_recorder.PYAUDIO_AVAILABLE', True):
            recorder = AudioRecorder(self.test_config)
            
            # Sem gravação
            stats = recorder.get_current_stats()
            self.assertIsNone(stats)
            
            # Com gravação
            recorder._stats = RecordingStats(start_time=datetime.now())
            recorder._recording = True
            
            stats = recorder.get_current_stats()
            self.assertIsNotNone(stats)
            self.assertGreater(stats.duration, 0)
            
            recorder.close()


class TestCreateRecorderFromConfig(unittest.TestCase):
    """Testes para create_recorder_from_config"""
    
    @patch('audio_recorder.pyaudio')
    def test_create_recorder_from_config_success(self, mock_pyaudio):
        """Testa criação de recorder com configurações"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        mock_device = AudioDevice(0, "Test Device", 2, 0, 44100.0, "WASAPI", is_loopback=True)
        
        # Mock settings
        mock_settings = Mock()
        mock_settings.audio_sample_rate = 16000
        mock_settings.audio_channels = 1
        mock_settings.recordings_dir = Path("/test/recordings")
        
        with patch('audio_recorder.PYAUDIO_AVAILABLE', True):
            with patch('audio_recorder.settings', mock_settings):
                with patch('audio_recorder.AudioRecorder') as mock_recorder_class:
                    mock_recorder = Mock()
                    mock_recorder.set_device_auto.return_value = True
                    mock_recorder._config = Mock()
                    mock_recorder_class.return_value = mock_recorder
                    
                    recorder = create_recorder_from_config()
                    
                    self.assertIsNotNone(recorder)
                    mock_recorder.set_device_auto.assert_called_once()
    
    @patch('audio_recorder.pyaudio')
    def test_create_recorder_from_config_no_settings(self, mock_pyaudio):
        """Testa criação de recorder sem settings disponível"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        with patch('audio_recorder.PYAUDIO_AVAILABLE', True):
            with patch('audio_recorder.AudioRecorder') as mock_recorder_class:
                mock_recorder = Mock()
                mock_recorder.set_device_auto.return_value = True
                mock_recorder_class.return_value = mock_recorder
                
                # Simular ImportError para settings
                with patch.dict('sys.modules', {'config': None}):
                    recorder = create_recorder_from_config()
                    
                    self.assertIsNotNone(recorder)
                    mock_recorder.set_device_auto.assert_called_once()


if __name__ == '__main__':
    # Configurar logging para testes
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Executar testes
    unittest.main(verbosity=2)