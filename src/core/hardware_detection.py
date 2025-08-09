"""
Sistema de Detecção de Hardware
Detecta automaticamente capacidades do sistema para otimização de performance.
"""

import os
import psutil
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from loguru import logger

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.debug("PyTorch não disponível para detecção de GPU")

# cpuinfo será importado sob demanda para evitar crashes na inicialização
CPU_INFO_AVAILABLE = None  # Será definido quando necessário


class PerformanceLevel(Enum):
    """Níveis de performance do sistema."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class GPUVendor(Enum):
    """Fornecedores de GPU suportados."""
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    UNKNOWN = "unknown"


@dataclass
class CPUInfo:
    """Informações da CPU."""
    name: str
    cores_physical: int
    cores_logical: int
    frequency_max: float  # GHz
    frequency_current: float  # GHz
    architecture: str
    cache_l3: Optional[int] = None  # MB
    
    @property
    def performance_score(self) -> int:
        """Score de performance da CPU (0-100)."""
        base_score = min(self.cores_logical * 5, 40)  # Max 40 pts por cores
        freq_score = min(self.frequency_max * 10, 40)  # Max 40 pts por frequência
        arch_bonus = 20 if "64" in self.architecture else 10  # Bonus arquitetura
        
        return min(100, int(base_score + freq_score + arch_bonus))


@dataclass
class GPUInfo:
    """Informações da GPU."""
    name: str
    vendor: GPUVendor
    memory_total: int  # MB
    memory_available: int  # MB
    cuda_available: bool = False
    cuda_version: Optional[str] = None
    compute_capability: Optional[Tuple[int, int]] = None
    
    @property
    def performance_score(self) -> int:
        """Score de performance da GPU (0-100)."""
        if not self.cuda_available:
            return 0
        
        memory_score = min(self.memory_total // 100, 50)  # Max 50 pts por memória
        vendor_bonus = {
            GPUVendor.NVIDIA: 30,
            GPUVendor.AMD: 20,
            GPUVendor.INTEL: 10,
            GPUVendor.UNKNOWN: 5
        }.get(self.vendor, 5)
        
        compute_bonus = 0
        if self.compute_capability:
            major, minor = self.compute_capability
            compute_bonus = min(major * 5 + minor, 20)
        
        return min(100, memory_score + vendor_bonus + compute_bonus)


@dataclass
class MemoryInfo:
    """Informações da memória RAM."""
    total: int  # MB
    available: int  # MB
    used: int  # MB
    percent_used: float
    
    @property
    def performance_score(self) -> int:
        """Score baseado na memória disponível."""
        available_gb = self.available / 1024
        
        if available_gb >= 16:
            return 100
        elif available_gb >= 8:
            return 80
        elif available_gb >= 4:
            return 60
        elif available_gb >= 2:
            return 40
        else:
            return 20


@dataclass
class StorageInfo:
    """Informações do armazenamento."""
    total: int  # MB
    available: int  # MB
    used: int  # MB
    percent_used: float
    is_ssd: bool
    
    @property
    def performance_score(self) -> int:
        """Score baseado no tipo e espaço disponível."""
        base_score = 60 if self.is_ssd else 30
        
        available_gb = self.available / 1024
        space_bonus = min(available_gb // 10, 20)  # Bonus por espaço
        
        return min(100, int(base_score + space_bonus))


@dataclass
class SystemSpecs:
    """Especificações completas do sistema."""
    os_name: str
    os_version: str
    python_version: str
    cpu: CPUInfo
    memory: MemoryInfo
    storage: StorageInfo
    gpu: Optional[GPUInfo] = None
    
    @property
    def overall_performance_level(self) -> PerformanceLevel:
        """Nível geral de performance do sistema."""
        cpu_score = self.cpu.performance_score
        memory_score = self.memory.performance_score
        gpu_score = self.gpu.performance_score if self.gpu else 0
        storage_score = self.storage.performance_score
        
        # Peso: CPU=40%, GPU=30%, Memory=20%, Storage=10%
        overall_score = (
            cpu_score * 0.4 +
            gpu_score * 0.3 +
            memory_score * 0.2 +
            storage_score * 0.1
        )
        
        if overall_score >= 85:
            return PerformanceLevel.EXTREME
        elif overall_score >= 70:
            return PerformanceLevel.HIGH
        elif overall_score >= 50:
            return PerformanceLevel.MEDIUM
        else:
            return PerformanceLevel.LOW
    
    @property
    def recommended_whisper_model(self) -> str:
        """Modelo Whisper recomendado baseado nas specs."""
        level = self.overall_performance_level
        gpu_available = self.gpu and self.gpu.cuda_available
        
        recommendations = {
            PerformanceLevel.EXTREME: "large-v3" if gpu_available else "medium",
            PerformanceLevel.HIGH: "medium" if gpu_available else "small", 
            PerformanceLevel.MEDIUM: "small" if gpu_available else "base",
            PerformanceLevel.LOW: "base" if gpu_available else "tiny"
        }
        
        return recommendations[level]
    
    @property
    def recommended_device(self) -> str:
        """Dispositivo recomendado para processamento."""
        if self.gpu and self.gpu.cuda_available and self.gpu.memory_available > 2000:
            return "cuda"
        else:
            return "cpu"
    
    @property
    def can_handle_speaker_detection(self) -> bool:
        """Verifica se o sistema suporta speaker detection."""
        # Requer pelo menos 4GB RAM disponível
        return self.memory.available >= 4000


class HardwareDetector:
    """Detector de hardware do sistema."""
    
    def __init__(self):
        logger.info("Iniciando detecção de hardware...")
    
    def detect_system_specs(self) -> SystemSpecs:
        """Detecta todas as especificações do sistema."""
        try:
            os_info = self._detect_os()
            cpu_info = self._detect_cpu()
            memory_info = self._detect_memory()
            storage_info = self._detect_storage()
            gpu_info = self._detect_gpu()
            python_version = platform.python_version()
            
            specs = SystemSpecs(
                os_name=os_info[0],
                os_version=os_info[1],
                python_version=python_version,
                cpu=cpu_info,
                memory=memory_info,
                storage=storage_info,
                gpu=gpu_info
            )
            
            logger.success(f"Hardware detectado - Performance: {specs.overall_performance_level.value}")
            return specs
        
        except Exception as e:
            logger.error(f"Erro na detecção de hardware: {e}")
            raise
    
    def _detect_os(self) -> Tuple[str, str]:
        """Detecta sistema operacional."""
        system = platform.system()
        version = platform.version()
        
        if system == "Windows":
            release = platform.release()
            return f"Windows {release}", version
        elif system == "Darwin":
            return "macOS", platform.mac_ver()[0]
        elif system == "Linux":
            try:
                import distro
                return f"Linux ({distro.name()})", distro.version()
            except ImportError:
                return "Linux", platform.release()
        else:
            return system, version
    
    def _detect_cpu(self) -> CPUInfo:
        """Detecta informações da CPU."""
        try:
            # Tentar importar cpuinfo sob demanda
            global CPU_INFO_AVAILABLE
            if CPU_INFO_AVAILABLE is None:
                try:
                    import cpuinfo
                    CPU_INFO_AVAILABLE = True
                except (ImportError, Exception) as e:
                    CPU_INFO_AVAILABLE = False
                    logger.debug(f"py-cpuinfo não disponível - usando fallback: {e}")
            
            if CPU_INFO_AVAILABLE:
                info = cpuinfo.get_cpu_info()
                name = info.get('brand_raw', 'Unknown CPU')
                arch = info.get('arch_string_raw', platform.machine())
                cache_l3 = info.get('l3_cache_size', None)
                if cache_l3:
                    cache_l3 = int(cache_l3) // (1024 * 1024)  # Convert to MB
            else:
                name = platform.processor() or "Unknown CPU"
                arch = platform.machine()
                cache_l3 = None
            
            cores_physical = psutil.cpu_count(logical=False) or 1
            cores_logical = psutil.cpu_count(logical=True) or 1
            
            # Frequências
            freq_info = psutil.cpu_freq()
            if freq_info:
                freq_max = freq_info.max / 1000 if freq_info.max else 2.0  # GHz
                freq_current = freq_info.current / 1000 if freq_info.current else 2.0  # GHz
            else:
                freq_max = freq_current = 2.0  # Default
            
            return CPUInfo(
                name=name,
                cores_physical=cores_physical,
                cores_logical=cores_logical,
                frequency_max=freq_max,
                frequency_current=freq_current,
                architecture=arch,
                cache_l3=cache_l3
            )
        
        except Exception as e:
            logger.warning(f"Erro na detecção de CPU: {e}")
            return CPUInfo(
                name="Unknown CPU",
                cores_physical=1,
                cores_logical=1,
                frequency_max=2.0,
                frequency_current=2.0,
                architecture=platform.machine()
            )
    
    def _detect_memory(self) -> MemoryInfo:
        """Detecta informações da memória."""
        try:
            memory = psutil.virtual_memory()
            
            return MemoryInfo(
                total=memory.total // (1024 * 1024),  # MB
                available=memory.available // (1024 * 1024),  # MB
                used=memory.used // (1024 * 1024),  # MB
                percent_used=memory.percent
            )
        
        except Exception as e:
            logger.warning(f"Erro na detecção de memória: {e}")
            return MemoryInfo(
                total=8192,  # Default 8GB
                available=4096,  # Default 4GB available
                used=4096,
                percent_used=50.0
            )
    
    def _detect_storage(self) -> StorageInfo:
        """Detecta informações do armazenamento."""
        try:
            # Detectar armazenamento do diretório atual
            current_path = Path.cwd()
            usage = psutil.disk_usage(str(current_path))
            
            # Tentar detectar se é SSD
            is_ssd = self._detect_ssd(current_path)
            
            return StorageInfo(
                total=usage.total // (1024 * 1024),  # MB
                available=usage.free // (1024 * 1024),  # MB
                used=usage.used // (1024 * 1024),  # MB
                percent_used=(usage.used / usage.total) * 100,
                is_ssd=is_ssd
            )
        
        except Exception as e:
            logger.warning(f"Erro na detecção de armazenamento: {e}")
            return StorageInfo(
                total=500000,  # Default 500GB
                available=250000,  # Default 250GB available
                used=250000,
                percent_used=50.0,
                is_ssd=True  # Assume SSD por padrão
            )
    
    def _detect_ssd(self, path: Path) -> bool:
        """Tenta detectar se o armazenamento é SSD."""
        try:
            if platform.system() == "Windows":
                # No Windows, assumir SSD por padrão (maioria dos sistemas modernos)
                return True
            elif platform.system() == "Linux":
                # No Linux, verificar rotational
                import subprocess
                result = subprocess.run(
                    ["lsblk", "-d", "-o", "name,rota"],
                    capture_output=True, text=True
                )
                return "0" in result.stdout  # 0 = SSD, 1 = HDD
            else:
                return True  # Default para macOS
        except:
            return True  # Default assume SSD
    
    def _detect_gpu(self) -> Optional[GPUInfo]:
        """Detecta informações da GPU."""
        if not TORCH_AVAILABLE:
            logger.debug("PyTorch não disponível - pulando detecção de GPU")
            return None
        
        try:
            if not torch.cuda.is_available():
                logger.debug("CUDA não disponível")
                return None
            
            device_count = torch.cuda.device_count()
            if device_count == 0:
                return None
            
            # Usar primeira GPU disponível
            device = torch.cuda.get_device_properties(0)
            
            # Detectar vendor
            name = device.name.lower()
            if "nvidia" in name or "geforce" in name or "quadro" in name or "tesla" in name:
                vendor = GPUVendor.NVIDIA
            elif "radeon" in name or "amd" in name:
                vendor = GPUVendor.AMD
            elif "intel" in name:
                vendor = GPUVendor.INTEL
            else:
                vendor = GPUVendor.UNKNOWN
            
            # Memória
            memory_total = device.total_memory // (1024 * 1024)  # MB
            memory_reserved = torch.cuda.memory_reserved(0) // (1024 * 1024)  # MB
            memory_available = memory_total - memory_reserved
            
            # CUDA version
            cuda_version = torch.version.cuda
            
            # Compute capability
            compute_capability = (device.major, device.minor)
            
            return GPUInfo(
                name=device.name,
                vendor=vendor,
                memory_total=memory_total,
                memory_available=memory_available,
                cuda_available=True,
                cuda_version=cuda_version,
                compute_capability=compute_capability
            )
        
        except Exception as e:
            logger.warning(f"Erro na detecção de GPU: {e}")
            return None


# Factory function
def detect_hardware() -> SystemSpecs:
    """
    Função de conveniência para detectar hardware do sistema.
    
    Returns:
        SystemSpecs com todas as informações do sistema
    """
    detector = HardwareDetector()
    return detector.detect_system_specs()