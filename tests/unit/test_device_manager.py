"""
Testes unitários para DeviceManager

Testa funcionalidades de detecção e gerenciamento de dispositivos de áudio.

Author: MeetingScribe Team
Version: 1.0.0
Python: >=3.8
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from device_manager import (
    DeviceManager, 
    AudioDevice, 
    AudioDeviceError, 
    WASAPINotAvailableError
)


class TestAudioDevice(unittest.TestCase):
    """Testes para a classe AudioDevice"""
    
    def test_audio_device_creation(self):
        """Testa criação de AudioDevice"""
        device = AudioDevice(
            index=0,
            name="Test Device",
            max_input_channels=2,
            max_output_channels=2,
            default_sample_rate=44100.0,
            host_api="Windows WASAPI",
            is_loopback=True,
            is_default=True
        )
        
        self.assertEqual(device.index, 0)
        self.assertEqual(device.name, "Test Device")
        self.assertEqual(device.max_input_channels, 2)
        self.assertEqual(device.max_output_channels, 2)
        self.assertEqual(device.default_sample_rate, 44100.0)
        self.assertEqual(device.host_api, "Windows WASAPI")
        self.assertTrue(device.is_loopback)
        self.assertTrue(device.is_default)
    
    def test_audio_device_defaults(self):
        """Testa valores padrão de AudioDevice"""
        device = AudioDevice(
            index=1,
            name="Default Test",
            max_input_channels=1,
            max_output_channels=1,
            default_sample_rate=16000.0,
            host_api="MME"
        )
        
        self.assertFalse(device.is_loopback)
        self.assertFalse(device.is_default)


class TestDeviceManager(unittest.TestCase):
    """Testes para a classe DeviceManager"""
    
    def setUp(self):
        """Setup para cada teste"""
        self.mock_pyaudio = Mock()
        self.mock_audio_instance = Mock()
        self.mock_pyaudio.PyAudio.return_value = self.mock_audio_instance
    
    @patch('device_manager.pyaudio')
    def test_device_manager_initialization_success(self, mock_pyaudio):
        """Testa inicialização bem-sucedida do DeviceManager"""
        # Configurar mocks
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        # Mock para WASAPI disponível
        mock_audio_instance.get_host_api_count.return_value = 3
        mock_audio_instance.get_host_api_info_by_index.side_effect = [
            {'name': 'MME'},
            {'name': 'DirectSound'},
            {'name': 'Windows WASAPI'}
        ]
        
        with patch('device_manager.PYAUDIO_AVAILABLE', True):
            dm = DeviceManager()
            self.assertIsNotNone(dm._audio)
            dm.close()
    
    @patch('device_manager.pyaudio')
    def test_device_manager_wasapi_not_available(self, mock_pyaudio):
        """Testa comportamento quando WASAPI não está disponível"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        # Mock para WASAPI não disponível
        mock_audio_instance.get_host_api_count.return_value = 2
        mock_audio_instance.get_host_api_info_by_index.side_effect = [
            {'name': 'MME'},
            {'name': 'DirectSound'}
        ]
        
        with patch('device_manager.PYAUDIO_AVAILABLE', True):
            with self.assertRaises(WASAPINotAvailableError):
                DeviceManager()
    
    @patch('device_manager.PYAUDIO_AVAILABLE', False)
    def test_device_manager_pyaudio_not_available(self):
        """Testa erro quando PyAudio não está disponível"""
        with self.assertRaises(AudioDeviceError):
            DeviceManager()
    
    @patch('device_manager.pyaudio')
    def test_list_all_devices(self, mock_pyaudio):
        """Testa listagem de dispositivos"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        # Mock para WASAPI disponível
        mock_audio_instance.get_host_api_count.return_value = 1
        mock_audio_instance.get_host_api_info_by_index.return_value = {'name': 'Windows WASAPI'}
        
        # Mock para dispositivos
        mock_audio_instance.get_device_count.return_value = 2
        mock_audio_instance.get_device_info_by_index.side_effect = [
            {
                'name': 'Speakers',
                'maxInputChannels': 0,
                'maxOutputChannels': 2,
                'defaultSampleRate': 44100.0,
                'hostApi': 0
            },
            {
                'name': 'Speakers [Loopback]',
                'maxInputChannels': 2,
                'maxOutputChannels': 0,
                'defaultSampleRate': 44100.0,
                'hostApi': 0
            }
        ]
        
        mock_audio_instance.get_host_api_info_by_index.return_value = {'name': 'Windows WASAPI'}
        
        with patch('device_manager.PYAUDIO_AVAILABLE', True):
            dm = DeviceManager()
            devices = dm.list_all_devices()
            
            self.assertEqual(len(devices), 2)
            self.assertEqual(devices[0].name, 'Speakers')
            self.assertEqual(devices[1].name, 'Speakers [Loopback]')
            self.assertTrue(devices[1].is_loopback)
            
            dm.close()
    
    @patch('device_manager.pyaudio')
    def test_get_default_speakers(self, mock_pyaudio):
        """Testa detecção de speakers padrão"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        # Mock básico para inicialização
        mock_audio_instance.get_host_api_count.return_value = 1
        mock_audio_instance.get_host_api_info_by_index.return_value = {'name': 'Windows WASAPI'}
        
        with patch('device_manager.PYAUDIO_AVAILABLE', True):
            dm = DeviceManager()
            
            # Mock para list_all_devices
            mock_device = AudioDevice(
                index=1,
                name="Speakers [Loopback]",
                max_input_channels=2,
                max_output_channels=0,
                default_sample_rate=44100.0,
                host_api="Windows WASAPI",
                is_loopback=True,
                is_default=True
            )
            
            with patch.object(dm, 'list_all_devices', return_value=[mock_device]):
                default_speakers = dm.get_default_speakers()
                
                self.assertIsNotNone(default_speakers)
                self.assertEqual(default_speakers.name, "Speakers [Loopback]")
                self.assertTrue(default_speakers.is_loopback)
            
            dm.close()
    
    @patch('device_manager.pyaudio')
    def test_get_devices_by_api(self, mock_pyaudio):
        """Testa filtragem de dispositivos por API"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        # Mock básico para inicialização
        mock_audio_instance.get_host_api_count.return_value = 1
        mock_audio_instance.get_host_api_info_by_index.return_value = {'name': 'Windows WASAPI'}
        
        with patch('device_manager.PYAUDIO_AVAILABLE', True):
            dm = DeviceManager()
            
            # Mock devices com diferentes APIs
            mock_devices = [
                AudioDevice(0, "Device 1", 0, 2, 44100.0, "Windows WASAPI"),
                AudioDevice(1, "Device 2", 0, 2, 44100.0, "MME"),
                AudioDevice(2, "Device 3", 0, 2, 44100.0, "Windows WASAPI")
            ]
            
            with patch.object(dm, 'list_all_devices', return_value=mock_devices):
                wasapi_devices = dm.get_devices_by_api('Windows WASAPI')
                
                self.assertEqual(len(wasapi_devices), 2)
                self.assertEqual(wasapi_devices[0].name, "Device 1")
                self.assertEqual(wasapi_devices[1].name, "Device 3")
            
            dm.close()
    
    @patch('device_manager.pyaudio')
    def test_context_manager(self, mock_pyaudio):
        """Testa uso como context manager"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        # Mock básico para inicialização
        mock_audio_instance.get_host_api_count.return_value = 1
        mock_audio_instance.get_host_api_info_by_index.return_value = {'name': 'Windows WASAPI'}
        
        with patch('device_manager.PYAUDIO_AVAILABLE', True):
            with DeviceManager() as dm:
                self.assertIsNotNone(dm._audio)
            
            # Verificar se close foi chamado
            mock_audio_instance.terminate.assert_called_once()


class TestDeviceManagerHelpers(unittest.TestCase):
    """Testes para funções auxiliares do DeviceManager"""
    
    @patch('device_manager.pyaudio')
    def test_is_loopback_device_detection(self, mock_pyaudio):
        """Testa detecção de dispositivos loopback"""
        mock_audio_instance = Mock()
        mock_pyaudio.PyAudio.return_value = mock_audio_instance
        
        # Mock básico para inicialização
        mock_audio_instance.get_host_api_count.return_value = 1
        mock_audio_instance.get_host_api_info_by_index.return_value = {'name': 'Windows WASAPI'}
        
        with patch('device_manager.PYAUDIO_AVAILABLE', True):
            dm = DeviceManager()
            
            # Teste diferentes tipos de nomes de dispositivos
            test_cases = [
                ({'name': 'Speakers [Loopback]', 'maxInputChannels': 2, 'maxOutputChannels': 0}, True),
                ({'name': 'Stereo Mix', 'maxInputChannels': 2, 'maxOutputChannels': 0}, True),
                ({'name': 'What U Hear', 'maxInputChannels': 2, 'maxOutputChannels': 0}, True),
                ({'name': 'Regular Speakers', 'maxInputChannels': 0, 'maxOutputChannels': 2}, False),
                ({'name': 'Microphone', 'maxInputChannels': 1, 'maxOutputChannels': 0}, False),
            ]
            
            for device_info, expected in test_cases:
                result = dm._is_loopback_device(device_info)
                self.assertEqual(result, expected, f"Failed for device: {device_info['name']}")
            
            dm.close()


if __name__ == '__main__':
    # Configurar logging para testes
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Executar testes
    unittest.main(verbosity=2)