"""
Sistema de Gerenciamento de Configurações
Gerencia presets, configurações personalizadas e otimizações automáticas.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime

from loguru import logger

from .hardware_detection import SystemSpecs, PerformanceLevel, detect_hardware
from ..transcription import WhisperModelSize, DiarizationModel


class PresetType(Enum):
    """Tipos de presets disponíveis."""
    SPEED = "speed"          # Máxima velocidade
    BALANCED = "balanced"    # Equilibrio velocidade/qualidade
    QUALITY = "quality"      # Máxima qualidade
    CUSTOM = "custom"        # Configuração personalizada


class ComputeType(Enum):
    """Tipos de computação disponíveis."""
    FLOAT32 = "float32"
    FLOAT16 = "float16" 
    INT8 = "int8"


@dataclass
class WhisperSettings:
    """Configurações específicas do Whisper."""
    model_size: str = "base"
    language: Optional[str] = None
    device: str = "auto"
    compute_type: str = "float32"
    beam_size: int = 5
    temperature: float = 0.0
    condition_on_previous_text: bool = True
    word_timestamps: bool = True
    vad_filter: bool = True


@dataclass
class SpeakerSettings:
    """Configurações específicas do Speaker Detection."""
    enabled: bool = True
    model_name: str = "pyannote/speaker-diarization-3.1"
    device: str = "auto"
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None
    overlap_threshold: float = 0.5


@dataclass
class AudioSettings:
    """Configurações de áudio."""
    sample_rate: int = 44100
    channels: int = 2
    chunk_size: int = 1024
    buffer_duration: int = 30


@dataclass
class ExportSettings:
    """Configurações de exportação."""
    default_format: str = "txt"
    include_metadata: bool = True
    include_timestamps: bool = True
    auto_open: bool = False


@dataclass
class PerformanceSettings:
    """Configurações de performance."""
    max_workers: int = 4
    model_cache_limit: int = 2048  # MB
    auto_cleanup: bool = True
    use_gpu_when_available: bool = True


@dataclass
class MeetingScribeConfig:
    """Configuração completa do MeetingScribe."""
    preset_type: str = "balanced"
    whisper: WhisperSettings = field(default_factory=WhisperSettings)
    speaker: SpeakerSettings = field(default_factory=SpeakerSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    performance: PerformanceSettings = field(default_factory=PerformanceSettings)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    system_specs_snapshot: Optional[Dict[str, Any]] = None
    
    def update_modified_time(self):
        """Atualiza timestamp de modificação."""
        self.modified_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MeetingScribeConfig':
        """Cria configuração a partir de dicionário."""
        # Extrair sub-configurações
        whisper_data = data.get('whisper', {})
        speaker_data = data.get('speaker', {})
        audio_data = data.get('audio', {})
        export_data = data.get('export', {})
        performance_data = data.get('performance', {})
        
        return cls(
            preset_type=data.get('preset_type', 'balanced'),
            whisper=WhisperSettings(**whisper_data),
            speaker=SpeakerSettings(**speaker_data),
            audio=AudioSettings(**audio_data),
            export=ExportSettings(**export_data),
            performance=PerformanceSettings(**performance_data),
            created_at=data.get('created_at', datetime.now().isoformat()),
            modified_at=data.get('modified_at', datetime.now().isoformat()),
            system_specs_snapshot=data.get('system_specs_snapshot')
        )


class PresetManager:
    """Gerencia presets de configuração baseados no hardware."""
    
    def __init__(self, system_specs: SystemSpecs):
        self.system_specs = system_specs
        self.presets = self._generate_presets()
        logger.info(f"PresetManager inicializado para sistema {system_specs.overall_performance_level.value}")
    
    def _generate_presets(self) -> Dict[str, MeetingScribeConfig]:
        """Gera presets baseados nas especificações do sistema."""
        presets = {}
        
        # PRESET SPEED - Máxima velocidade
        speed_config = MeetingScribeConfig(preset_type="speed")
        speed_config.whisper.model_size = "tiny"
        speed_config.whisper.device = "cpu"  # CPU geralmente mais rápido para modelos pequenos
        speed_config.whisper.compute_type = "float32"
        speed_config.whisper.beam_size = 1  # Menor beam size
        speed_config.whisper.vad_filter = False  # Pular VAD para velocidade
        speed_config.speaker.enabled = False  # Pular speaker detection
        speed_config.performance.max_workers = self.system_specs.cpu.cores_logical
        presets["speed"] = speed_config
        
        # PRESET BALANCED - Equilibrio
        balanced_config = MeetingScribeConfig(preset_type="balanced")
        balanced_config.whisper.model_size = self.system_specs.recommended_whisper_model
        balanced_config.whisper.device = self.system_specs.recommended_device
        balanced_config.whisper.compute_type = "float16" if self.system_specs.gpu else "float32"
        balanced_config.speaker.enabled = self.system_specs.can_handle_speaker_detection
        balanced_config.performance.max_workers = min(4, self.system_specs.cpu.cores_logical)
        presets["balanced"] = balanced_config
        
        # PRESET QUALITY - Máxima qualidade
        quality_config = MeetingScribeConfig(preset_type="quality")
        
        # Escolher melhor modelo baseado no hardware
        if self.system_specs.overall_performance_level == PerformanceLevel.EXTREME:
            quality_config.whisper.model_size = "large-v3"
        elif self.system_specs.overall_performance_level == PerformanceLevel.HIGH:
            quality_config.whisper.model_size = "medium"
        else:
            quality_config.whisper.model_size = "small"
        
        quality_config.whisper.device = self.system_specs.recommended_device
        quality_config.whisper.compute_type = "float16" if self.system_specs.gpu else "float32"
        quality_config.whisper.beam_size = 5
        quality_config.whisper.temperature = 0.0  # Determinístico
        quality_config.speaker.enabled = True
        quality_config.speaker.model_name = "pyannote/speaker-diarization-3.1"  # Melhor modelo
        quality_config.performance.max_workers = 2  # Menos workers para mais qualidade
        presets["quality"] = quality_config
        
        # PRESET CUSTOM - Base para customização
        custom_config = MeetingScribeConfig(preset_type="custom")
        presets["custom"] = custom_config
        
        return presets
    
    def get_preset(self, preset_name: str) -> Optional[MeetingScribeConfig]:
        """Retorna um preset específico."""
        return self.presets.get(preset_name)
    
    def get_recommended_preset(self) -> str:
        """Retorna o preset recomendado baseado no hardware."""
        level = self.system_specs.overall_performance_level
        
        recommendations = {
            PerformanceLevel.EXTREME: "quality",
            PerformanceLevel.HIGH: "balanced", 
            PerformanceLevel.MEDIUM: "balanced",
            PerformanceLevel.LOW: "speed"
        }
        
        return recommendations[level]
    
    def list_presets(self) -> List[Dict[str, Any]]:
        """Lista todos os presets com descrições."""
        descriptions = {
            "speed": {
                "name": "Velocidade Máxima",
                "description": "Transcrição mais rápida possível",
                "features": ["Modelo Whisper tiny", "CPU otimizado", "Sem speaker detection"],
                "recommended_for": ["Rascunhos rápidos", "Testes", "Hardware limitado"]
            },
            "balanced": {
                "name": "Equilibrado",
                "description": "Melhor relação velocidade/qualidade",
                "features": ["Modelo automático baseado no hardware", "GPU quando disponível", "Speaker detection inteligente"],
                "recommended_for": ["Uso geral", "Reuniões de trabalho", "Entrevistas"]
            },
            "quality": {
                "name": "Qualidade Máxima", 
                "description": "Melhor qualidade possível",
                "features": ["Melhor modelo Whisper disponível", "Speaker detection avançado", "Configurações otimizadas"],
                "recommended_for": ["Transcrições finais", "Conteúdo profissional", "Arquivamento"]
            },
            "custom": {
                "name": "Personalizado",
                "description": "Configuração manual completa",
                "features": ["Controle total", "Todas as opções disponíveis", "Salvamento personalizado"],
                "recommended_for": ["Usuários avançados", "Casos específicos", "Experimentação"]
            }
        }
        
        result = []
        for preset_name, config in self.presets.items():
            info = descriptions.get(preset_name, {})
            result.append({
                "name": preset_name,
                "display_name": info.get("name", preset_name.title()),
                "description": info.get("description", ""),
                "features": info.get("features", []),
                "recommended_for": info.get("recommended_for", []),
                "config": config
            })
        
        return result


class SettingsManager:
    """Gerenciador principal de configurações."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.cwd() / "config"
        self.config_file = self.config_dir / "meetingscribe_config.json"
        self.backup_dir = self.config_dir / "backups"
        
        # Criar diretórios se não existirem
        self.config_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Detectar hardware
        self._system_specs = None
        self._preset_manager = None
        self._current_config = None
        
        logger.info(f"SettingsManager inicializado - Config dir: {self.config_dir}")
    
    @property
    def system_specs(self) -> SystemSpecs:
        """Especificações do sistema (lazy loading)."""
        if self._system_specs is None:
            logger.info("Detectando hardware do sistema...")
            self._system_specs = detect_hardware()
        return self._system_specs
    
    @property
    def preset_manager(self) -> PresetManager:
        """Gerenciador de presets (lazy loading)."""
        if self._preset_manager is None:
            self._preset_manager = PresetManager(self.system_specs)
        return self._preset_manager
    
    def load_config(self) -> MeetingScribeConfig:
        """Carrega configuração do arquivo ou cria padrão."""
        try:
            if self.config_file.exists():
                logger.info(f"Carregando configuração de: {self.config_file}")
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                config = MeetingScribeConfig.from_dict(data)
                self._current_config = config
                
                logger.success("Configuração carregada com sucesso")
                return config
            else:
                logger.info("Arquivo de configuração não encontrado - criando padrão")
                return self.create_default_config()
        
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            logger.info("Criando configuração padrão")
            return self.create_default_config()
    
    def save_config(self, config: MeetingScribeConfig, create_backup: bool = True) -> bool:
        """Salva configuração no arquivo."""
        try:
            # Criar backup se solicitado
            if create_backup and self.config_file.exists():
                self._create_backup()
            
            # Atualizar timestamps e specs
            config.update_modified_time()
            config.system_specs_snapshot = asdict(self.system_specs)
            
            # Salvar configuração
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            
            self._current_config = config
            logger.success(f"Configuração salva: {self.config_file}")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao salvar configuração: {e}")
            return False
    
    def create_default_config(self) -> MeetingScribeConfig:
        """Cria configuração padrão baseada no hardware."""
        recommended_preset = self.preset_manager.get_recommended_preset()
        config = self.preset_manager.get_preset(recommended_preset)
        
        if config:
            logger.info(f"Criando configuração padrão com preset: {recommended_preset}")
            self.save_config(config, create_backup=False)
            return config
        else:
            # Fallback para configuração básica
            logger.warning("Criando configuração fallback")
            config = MeetingScribeConfig()
            self.save_config(config, create_backup=False)
            return config
    
    def apply_preset(self, preset_name: str) -> Optional[MeetingScribeConfig]:
        """Aplica um preset específico."""
        preset_config = self.preset_manager.get_preset(preset_name)
        if preset_config:
            logger.info(f"Aplicando preset: {preset_name}")
            self.save_config(preset_config)
            return preset_config
        else:
            logger.error(f"Preset não encontrado: {preset_name}")
            return None
    
    def get_current_config(self) -> MeetingScribeConfig:
        """Retorna a configuração atual."""
        if self._current_config is None:
            self._current_config = self.load_config()
        return self._current_config
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Atualiza configuração atual com novos valores."""
        try:
            current = self.get_current_config()
            
            # Aplicar updates (implementação simples)
            for key, value in updates.items():
                if hasattr(current, key):
                    setattr(current, key, value)
                elif '.' in key:
                    # Suporte para nested updates (e.g., 'whisper.model_size')
                    parts = key.split('.')
                    obj = current
                    for part in parts[:-1]:
                        obj = getattr(obj, part)
                    setattr(obj, parts[-1], value)
            
            return self.save_config(current)
        
        except Exception as e:
            logger.error(f"Erro ao atualizar configuração: {e}")
            return False
    
    def _create_backup(self) -> Path:
        """Cria backup da configuração atual."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"config_backup_{timestamp}.json"
        
        try:
            import shutil
            shutil.copy2(self.config_file, backup_file)
            logger.debug(f"Backup criado: {backup_file}")
            return backup_file
        except Exception as e:
            logger.warning(f"Erro ao criar backup: {e}")
            return backup_file
    
    def list_backups(self) -> List[Path]:
        """Lista backups disponíveis."""
        try:
            backups = list(self.backup_dir.glob("config_backup_*.json"))
            return sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)
        except Exception as e:
            logger.error(f"Erro ao listar backups: {e}")
            return []
    
    def restore_backup(self, backup_file: Path) -> bool:
        """Restaura configuração de um backup."""
        try:
            if not backup_file.exists():
                logger.error(f"Backup não encontrado: {backup_file}")
                return False
            
            # Fazer backup da configuração atual
            self._create_backup()
            
            # Restaurar backup
            import shutil
            shutil.copy2(backup_file, self.config_file)
            
            # Recarregar configuração
            self._current_config = None
            self.load_config()
            
            logger.success(f"Configuração restaurada de: {backup_file}")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao restaurar backup: {e}")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """Remove backups antigos, mantendo apenas os mais recentes."""
        try:
            backups = self.list_backups()
            if len(backups) <= keep_count:
                return 0
            
            removed_count = 0
            for backup in backups[keep_count:]:
                try:
                    backup.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Erro ao remover backup {backup}: {e}")
            
            if removed_count > 0:
                logger.info(f"Removed {removed_count} old backups")
            
            return removed_count
        
        except Exception as e:
            logger.error(f"Erro na limpeza de backups: {e}")
            return 0


# Factory functions
def create_settings_manager(config_dir: Optional[Path] = None) -> SettingsManager:
    """
    Cria um gerenciador de configurações.
    
    Args:
        config_dir: Diretório de configuração personalizado
        
    Returns:
        SettingsManager configurado
    """
    return SettingsManager(config_dir)


def get_system_info() -> Dict[str, Any]:
    """
    Retorna informações resumidas do sistema.
    
    Returns:
        Dicionário com specs do sistema
    """
    specs = detect_hardware()
    return {
        "os": f"{specs.os_name} {specs.os_version}",
        "python": specs.python_version,
        "cpu": {
            "name": specs.cpu.name,
            "cores": f"{specs.cpu.cores_physical}C/{specs.cpu.cores_logical}T",
            "frequency": f"{specs.cpu.frequency_max:.1f} GHz",
            "score": specs.cpu.performance_score
        },
        "memory": {
            "total": f"{specs.memory.total // 1024:.1f} GB",
            "available": f"{specs.memory.available // 1024:.1f} GB",
            "score": specs.memory.performance_score
        },
        "gpu": {
            "name": specs.gpu.name if specs.gpu else "Não disponível",
            "memory": f"{specs.gpu.memory_total // 1024:.1f} GB" if specs.gpu else "N/A",
            "cuda": specs.gpu.cuda_available if specs.gpu else False,
            "score": specs.gpu.performance_score if specs.gpu else 0
        },
        "storage": {
            "available": f"{specs.storage.available // 1024:.1f} GB",
            "type": "SSD" if specs.storage.is_ssd else "HDD",
            "score": specs.storage.performance_score
        },
        "performance_level": specs.overall_performance_level.value,
        "recommended_preset": PresetManager(specs).get_recommended_preset(),
        "can_use_speakers": specs.can_handle_speaker_detection
    }