# -*- coding: utf-8 -*-
"""
Sistema de Compressão Inteligente - MeetingScribe
Algoritmos adaptativos de compressão para otimizar armazenamento e performance
"""

import os
import gzip
import lzma
import bz2
import zlib
import time
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
from enum import Enum
import hashlib
import json
from collections import defaultdict, deque
import psutil

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

try:
    import lz4.frame as lz4
    LZ4_AVAILABLE = True
except ImportError:
    LZ4_AVAILABLE = False

class CompressionAlgorithm(Enum):
    """Algoritmos de compressão disponíveis"""
    GZIP = "gzip"
    LZMA = "lzma"
    BZ2 = "bz2"
    ZLIB = "zlib"
    ZSTD = "zstd"  # Zstandard (Facebook)
    LZ4 = "lz4"    # LZ4 (ultra fast)
    NONE = "none"

class CompressionLevel(Enum):
    """Níveis de compressão"""
    FASTEST = 1     # Prioriza velocidade
    FAST = 3        # Balanceado para velocidade
    BALANCED = 6    # Balanceado
    GOOD = 7        # Boa compressão
    BEST = 9        # Máxima compressão

class CompressionStrategy(Enum):
    """Estratégias de compressão"""
    SIZE_OPTIMIZED = "size_optimized"       # Foca no menor tamanho
    SPEED_OPTIMIZED = "speed_optimized"     # Foca na velocidade
    BALANCED = "balanced"                   # Balanceado
    ADAPTIVE = "adaptive"                   # Adapta baseado no conteúdo
    INTELLIGENT = "intelligent"             # ML-based selection

@dataclass
class CompressionMetrics:
    """Métricas de performance de compressão"""
    algorithm: CompressionAlgorithm
    level: int
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_time: float
    decompression_time: float
    speed_mbps: float
    efficiency_score: float

@dataclass
class FileProfile:
    """Perfil de um arquivo para análise de compressão"""
    path: Path
    size: int
    extension: str
    file_type: str
    entropy: float
    repetition_ratio: float
    text_ratio: float
    binary_ratio: float
    recommended_algorithm: CompressionAlgorithm
    recommended_level: int
    estimated_ratio: float

@dataclass
class CompressionConfig:
    """Configuração do sistema de compressão"""
    strategy: CompressionStrategy = CompressionStrategy.INTELLIGENT
    fallback_algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP
    fallback_level: CompressionLevel = CompressionLevel.BALANCED
    min_file_size: int = 1024  # 1KB - não comprimir arquivos menores
    max_file_size: int = 1024 * 1024 * 1024 * 2  # 2GB - limite máximo
    enable_caching: bool = True
    cache_metrics: bool = True
    background_compression: bool = True
    analyze_before_compress: bool = True
    adaptive_threshold: float = 0.1  # 10% melhoria mínima para adaptar
    benchmark_samples: int = 5  # Amostras para benchmark
    memory_limit_mb: int = 512  # Limite de memória para compressão

class IntelligentCompressor:
    """
    Sistema de compressão inteligente com seleção adaptativa de algoritmos
    """
    
    def __init__(self, config: CompressionConfig = None):
        self.config = config or CompressionConfig()
        self._metrics_cache: Dict[str, CompressionMetrics] = {}
        self._profile_cache: Dict[str, FileProfile] = {}
        self._algorithm_stats: Dict[CompressionAlgorithm, Dict[str, float]] = defaultdict(lambda: {
            'avg_ratio': 0.0,
            'avg_speed': 0.0,
            'success_count': 0,
            'total_count': 0
        })
        self._compression_history: deque = deque(maxlen=1000)
        self._lock = threading.RLock()
        
        # Background compression queue
        self._background_queue: deque = deque()
        self._background_thread: Optional[threading.Thread] = None
        self._stop_background = threading.Event()
        
        if self.config.background_compression:
            self._start_background_processor()
    
    def _start_background_processor(self):
        """Inicia thread de processamento em background"""
        if self._background_thread and self._background_thread.is_alive():
            return
            
        self._stop_background.clear()
        self._background_thread = threading.Thread(
            target=self._background_worker,
            daemon=True
        )
        self._background_thread.start()
    
    def _background_worker(self):
        """Worker thread para compressão em background"""
        while not self._stop_background.is_set():
            try:
                if self._background_queue:
                    with self._lock:
                        if self._background_queue:
                            task = self._background_queue.popleft()
                        else:
                            task = None
                    
                    if task:
                        self._process_background_task(task)
                
                # Sleep para evitar uso excessivo de CPU
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Erro no background worker: {e}")
                time.sleep(1)
    
    def _process_background_task(self, task):
        """Processa tarefa de compressão em background"""
        try:
            file_path, callback = task
            result = self.compress_file(file_path)
            if callback:
                callback(result)
        except Exception as e:
            print(f"Erro ao processar tarefa background: {e}")
    
    def analyze_file(self, file_path: Union[str, Path]) -> FileProfile:
        """
        Analisa arquivo para determinar o melhor algoritmo de compressão
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            FileProfile com recomendações
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")
        
        file_size = path.stat().st_size
        file_hash = self._get_file_hash(path)
        
        # Verificar cache
        if self.config.enable_caching and file_hash in self._profile_cache:
            return self._profile_cache[file_hash]
        
        # Análise do arquivo
        extension = path.suffix.lower()
        file_type = self._detect_file_type(path, extension)
        
        # Análise de conteúdo (amostra)
        sample_size = min(file_size, 8192)  # 8KB sample
        entropy, repetition_ratio, text_ratio, binary_ratio = self._analyze_content(path, sample_size)
        
        # Recomendação baseada na análise
        recommended_algorithm, recommended_level, estimated_ratio = self._recommend_compression(
            file_type, extension, file_size, entropy, repetition_ratio, text_ratio, binary_ratio
        )
        
        profile = FileProfile(
            path=path,
            size=file_size,
            extension=extension,
            file_type=file_type,
            entropy=entropy,
            repetition_ratio=repetition_ratio,
            text_ratio=text_ratio,
            binary_ratio=binary_ratio,
            recommended_algorithm=recommended_algorithm,
            recommended_level=recommended_level,
            estimated_ratio=estimated_ratio
        )
        
        # Cache do perfil
        if self.config.enable_caching:
            with self._lock:
                self._profile_cache[file_hash] = profile
        
        return profile
    
    def _get_file_hash(self, path: Path) -> str:
        """Gera hash do arquivo para cache"""
        stat = path.stat()
        # Hash baseado em path, tamanho e timestamp de modificação
        content = f"{path}:{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _detect_file_type(self, path: Path, extension: str) -> str:
        """Detecta tipo do arquivo"""
        audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac'}
        text_extensions = {'.txt', '.json', '.xml', '.csv', '.md', '.log'}
        binary_extensions = {'.exe', '.dll', '.so', '.bin', '.db'}
        
        if extension in audio_extensions:
            return "audio"
        elif extension in text_extensions:
            return "text"
        elif extension in binary_extensions:
            return "binary"
        else:
            return "unknown"
    
    def _analyze_content(self, path: Path, sample_size: int) -> Tuple[float, float, float, float]:
        """
        Analisa conteúdo do arquivo
        
        Returns:
            Tuple com (entropy, repetition_ratio, text_ratio, binary_ratio)
        """
        try:
            with open(path, 'rb') as f:
                sample = f.read(sample_size)
            
            if not sample:
                return 0.0, 0.0, 0.0, 1.0
            
            # Calcular entropia
            entropy = self._calculate_entropy(sample)
            
            # Calcular ratio de repetição
            repetition_ratio = self._calculate_repetition_ratio(sample)
            
            # Analisar conteúdo text vs binary
            text_chars = sum(1 for b in sample if 32 <= b <= 126 or b in [9, 10, 13])
            text_ratio = text_chars / len(sample)
            binary_ratio = 1.0 - text_ratio
            
            return entropy, repetition_ratio, text_ratio, binary_ratio
            
        except Exception:
            # Em caso de erro, retornar valores neutros
            return 5.0, 0.5, 0.5, 0.5
    
    def _calculate_entropy(self, data: bytes) -> float:
        """Calcula entropia dos dados"""
        if not data:
            return 0.0
        
        # Frequência de cada byte
        frequency = [0] * 256
        for byte in data:
            frequency[byte] += 1
        
        # Calcular entropia
        entropy = 0.0
        length = len(data)
        
        for count in frequency:
            if count > 0:
                probability = count / length
                entropy -= probability * (probability.bit_length() - 1)
        
        return entropy
    
    def _calculate_repetition_ratio(self, data: bytes) -> float:
        """Calcula ratio de bytes repetidos"""
        if len(data) < 2:
            return 0.0
        
        unique_bytes = len(set(data))
        total_bytes = len(data)
        
        # Ratio de repetição (quanto menor, mais repetitivo)
        repetition_ratio = unique_bytes / total_bytes
        return 1.0 - repetition_ratio
    
    def _recommend_compression(
        self, 
        file_type: str, 
        extension: str, 
        file_size: int,
        entropy: float, 
        repetition_ratio: float, 
        text_ratio: float, 
        binary_ratio: float
    ) -> Tuple[CompressionAlgorithm, int, float]:
        """
        Recomenda algoritmo e nível de compressão baseado na análise inteligente
        
        Returns:
            Tuple com (algorithm, level, estimated_ratio)
        """
        
        # Sistema de pontuação inteligente para seleção de algoritmo
        algorithm_scores = {}
        
        # Análise de estratégia baseada em contexto
        strategy = self.config.strategy
        
        # Estratégia adaptativa avançada
        if strategy == CompressionStrategy.INTELLIGENT:
            # Sistema ML-inspired de decisão baseado em múltiplos fatores
            
            # Análise de tipo de arquivo com peso
            file_type_weight = 0.3
            if file_type == "audio":
                if extension in ['.wav', '.flac', '.aiff']:  # Áudio não comprimido
                    algorithm_scores[CompressionAlgorithm.LZ4] = 0.8 if LZ4_AVAILABLE else 0
                    algorithm_scores[CompressionAlgorithm.GZIP] = 0.7
                    algorithm_scores[CompressionAlgorithm.ZSTD] = 0.9 if ZSTD_AVAILABLE else 0
                elif extension in ['.mp3', '.aac', '.ogg', '.m4a']:  # Já comprimido
                    algorithm_scores[CompressionAlgorithm.NONE] = 0.9
                    algorithm_scores[CompressionAlgorithm.LZ4] = 0.3 if LZ4_AVAILABLE else 0
                    return CompressionAlgorithm.NONE, 0, 1.0  # Skip compression
            
            elif file_type == "text":
                algorithm_scores[CompressionAlgorithm.ZSTD] = 0.9 if ZSTD_AVAILABLE else 0
                algorithm_scores[CompressionAlgorithm.LZMA] = 0.8
                algorithm_scores[CompressionAlgorithm.GZIP] = 0.7
                algorithm_scores[CompressionAlgorithm.BZ2] = 0.6
            
            elif file_type == "binary":
                algorithm_scores[CompressionAlgorithm.LZ4] = 0.6 if LZ4_AVAILABLE else 0
                algorithm_scores[CompressionAlgorithm.GZIP] = 0.7
                algorithm_scores[CompressionAlgorithm.ZSTD] = 0.8 if ZSTD_AVAILABLE else 0
            
            # Análise de entropia com peso
            entropy_weight = 0.25
            if entropy < 2.0:  # Muito baixa entropia - alta compressibilidade
                algorithm_scores[CompressionAlgorithm.LZMA] = algorithm_scores.get(CompressionAlgorithm.LZMA, 0) + 0.4
                algorithm_scores[CompressionAlgorithm.ZSTD] = algorithm_scores.get(CompressionAlgorithm.ZSTD, 0) + 0.3
            elif entropy < 4.0:  # Baixa entropia
                algorithm_scores[CompressionAlgorithm.ZSTD] = algorithm_scores.get(CompressionAlgorithm.ZSTD, 0) + 0.3
                algorithm_scores[CompressionAlgorithm.GZIP] = algorithm_scores.get(CompressionAlgorithm.GZIP, 0) + 0.2
            elif entropy > 6.0:  # Alta entropia - baixa compressibilidade
                algorithm_scores[CompressionAlgorithm.LZ4] = algorithm_scores.get(CompressionAlgorithm.LZ4, 0) + 0.4
                algorithm_scores[CompressionAlgorithm.NONE] = algorithm_scores.get(CompressionAlgorithm.NONE, 0) + 0.3
            
            # Análise de repetição com peso
            repetition_weight = 0.2
            if repetition_ratio > 0.5:  # Alta repetição
                algorithm_scores[CompressionAlgorithm.LZMA] = algorithm_scores.get(CompressionAlgorithm.LZMA, 0) + 0.3
                algorithm_scores[CompressionAlgorithm.BZ2] = algorithm_scores.get(CompressionAlgorithm.BZ2, 0) + 0.2
            elif repetition_ratio < 0.2:  # Baixa repetição
                algorithm_scores[CompressionAlgorithm.LZ4] = algorithm_scores.get(CompressionAlgorithm.LZ4, 0) + 0.2
            
            # Análise de tamanho de arquivo com peso
            size_weight = 0.15
            if file_size < 64 * 1024:  # < 64KB - arquivos pequenos
                algorithm_scores[CompressionAlgorithm.LZ4] = algorithm_scores.get(CompressionAlgorithm.LZ4, 0) + 0.3
                algorithm_scores[CompressionAlgorithm.GZIP] = algorithm_scores.get(CompressionAlgorithm.GZIP, 0) + 0.2
            elif file_size > 100 * 1024 * 1024:  # > 100MB - arquivos grandes
                algorithm_scores[CompressionAlgorithm.ZSTD] = algorithm_scores.get(CompressionAlgorithm.ZSTD, 0) + 0.3
                algorithm_scores[CompressionAlgorithm.LZ4] = algorithm_scores.get(CompressionAlgorithm.LZ4, 0) + 0.2
            
            # Análise de conteúdo texto vs binário
            content_weight = 0.1
            if text_ratio > 0.8:  # Principalmente texto
                algorithm_scores[CompressionAlgorithm.ZSTD] = algorithm_scores.get(CompressionAlgorithm.ZSTD, 0) + 0.2
                algorithm_scores[CompressionAlgorithm.LZMA] = algorithm_scores.get(CompressionAlgorithm.LZMA, 0) + 0.15
            elif binary_ratio > 0.8:  # Principalmente binário
                algorithm_scores[CompressionAlgorithm.LZ4] = algorithm_scores.get(CompressionAlgorithm.LZ4, 0) + 0.15
            
            # Considerar histórico de performance
            if hasattr(self, '_algorithm_stats') and self._algorithm_stats:
                history_weight = 0.1
                for alg, stats in self._algorithm_stats.items():
                    if stats['total_count'] > 0 and alg in algorithm_scores:
                        # Bonus baseado em success rate e velocidade
                        performance_bonus = (stats['success_count'] / stats['total_count']) * 0.1
                        speed_bonus = min(stats['avg_speed'] / 50.0, 0.05)  # Max 0.05 bonus
                        algorithm_scores[alg] += performance_bonus + speed_bonus
        
        else:
            # Estratégias tradicionais mais simples
            if strategy == CompressionStrategy.SIZE_OPTIMIZED:
                algorithm_scores = {
                    CompressionAlgorithm.LZMA: 0.9,
                    CompressionAlgorithm.BZ2: 0.8,
                    CompressionAlgorithm.ZSTD: 0.85 if ZSTD_AVAILABLE else 0,
                    CompressionAlgorithm.GZIP: 0.7
                }
            elif strategy == CompressionStrategy.SPEED_OPTIMIZED:
                algorithm_scores = {
                    CompressionAlgorithm.LZ4: 0.9 if LZ4_AVAILABLE else 0,
                    CompressionAlgorithm.GZIP: 0.8,
                    CompressionAlgorithm.ZLIB: 0.7,
                    CompressionAlgorithm.ZSTD: 0.6 if ZSTD_AVAILABLE else 0
                }
            elif strategy == CompressionStrategy.BALANCED:
                algorithm_scores = {
                    CompressionAlgorithm.ZSTD: 0.9 if ZSTD_AVAILABLE else 0,
                    CompressionAlgorithm.GZIP: 0.8,
                    CompressionAlgorithm.LZMA: 0.7,
                    CompressionAlgorithm.LZ4: 0.6 if LZ4_AVAILABLE else 0
                }
        
        # Remover algoritmos não disponíveis
        available_scores = {alg: score for alg, score in algorithm_scores.items() 
                           if alg in [CompressionAlgorithm.GZIP, CompressionAlgorithm.LZMA, 
                                     CompressionAlgorithm.BZ2, CompressionAlgorithm.ZLIB,
                                     CompressionAlgorithm.NONE] or
                           (alg == CompressionAlgorithm.ZSTD and ZSTD_AVAILABLE) or
                           (alg == CompressionAlgorithm.LZ4 and LZ4_AVAILABLE)}
        
        # Selecionar melhor algoritmo
        if not available_scores:
            # Fallback para GZIP se nenhum score foi calculado
            best_algorithm = CompressionAlgorithm.GZIP
            best_score = 0.5
        else:
            best_algorithm = max(available_scores, key=available_scores.get)
            best_score = available_scores[best_algorithm]
        
        # Determinar nível de compressão baseado no algoritmo e contexto
        if best_algorithm == CompressionAlgorithm.NONE:
            level = 0
            estimated_ratio = 1.0
        else:
            # Nível adaptativo baseado em múltiplos fatores
            base_level = 6  # Nível balanceado padrão
            
            # Ajustar baseado na estratégia
            if strategy == CompressionStrategy.SIZE_OPTIMIZED:
                base_level = 8
            elif strategy == CompressionStrategy.SPEED_OPTIMIZED:
                base_level = 3
            
            # Ajustar baseado na entropia
            if entropy < 3.0:  # Baixa entropia - pode usar nível maior
                base_level = min(base_level + 2, 9)
            elif entropy > 6.0:  # Alta entropia - usar nível menor
                base_level = max(base_level - 2, 1)
            
            # Ajustar baseado no tamanho do arquivo
            if file_size < 1024 * 1024:  # < 1MB - usar nível menor para velocidade
                base_level = max(base_level - 1, 1)
            elif file_size > 100 * 1024 * 1024:  # > 100MB - balance vs tempo
                if strategy != CompressionStrategy.SIZE_OPTIMIZED:
                    base_level = max(base_level - 1, 3)
            
            level = base_level
            
            # Estimar ratio de compressão baseado em características
            if best_algorithm == CompressionAlgorithm.LZMA:
                base_ratio = 0.4
            elif best_algorithm == CompressionAlgorithm.ZSTD:
                base_ratio = 0.5
            elif best_algorithm == CompressionAlgorithm.GZIP:
                base_ratio = 0.6
            elif best_algorithm == CompressionAlgorithm.LZ4:
                base_ratio = 0.7
            elif best_algorithm == CompressionAlgorithm.BZ2:
                base_ratio = 0.45
            elif best_algorithm == CompressionAlgorithm.ZLIB:
                base_ratio = 0.65
            else:
                base_ratio = 0.6
            
            # Ajustar ratio baseado em características do arquivo
            if entropy < 3.0 and repetition_ratio > 0.4:
                estimated_ratio = base_ratio * 0.7  # Muito compressível
            elif entropy > 6.0:
                estimated_ratio = base_ratio * 1.3  # Pouco compressível
            elif text_ratio > 0.8:
                estimated_ratio = base_ratio * 0.8  # Texto comprime bem
            else:
                estimated_ratio = base_ratio
            
            # Ajustar baseado no nível
            level_adjustment = (level - 6) * 0.05  # ±5% por nível
            estimated_ratio = max(0.1, min(1.0, estimated_ratio - level_adjustment))
        
        return best_algorithm, level, estimated_ratio
    
    def compress_data(
        self, 
        data: bytes, 
        algorithm: CompressionAlgorithm = None,
        level: int = None
    ) -> Tuple[bytes, CompressionMetrics]:
        """
        Comprime dados usando algoritmo especificado
        
        Args:
            data: Dados para comprimir
            algorithm: Algoritmo de compressão
            level: Nível de compressão
            
        Returns:
            Tuple com (dados_comprimidos, métricas)
        """
        if not data:
            raise ValueError("Dados vazios não podem ser comprimidos")
        
        original_size = len(data)
        
        # Usar algoritmo padrão se não especificado
        if algorithm is None:
            algorithm = self.config.fallback_algorithm
        
        if level is None:
            level = self.config.fallback_level.value
        
        # Verificar se vale a pena comprimir
        if original_size < self.config.min_file_size:
            algorithm = CompressionAlgorithm.NONE
        
        start_time = time.time()
        
        try:
            if algorithm == CompressionAlgorithm.NONE:
                compressed_data = data
            elif algorithm == CompressionAlgorithm.GZIP:
                compressed_data = gzip.compress(data, compresslevel=level)
            elif algorithm == CompressionAlgorithm.LZMA:
                compressed_data = lzma.compress(data, preset=level)
            elif algorithm == CompressionAlgorithm.BZ2:
                compressed_data = bz2.compress(data, compresslevel=level)
            elif algorithm == CompressionAlgorithm.ZLIB:
                compressed_data = zlib.compress(data, level=level)
            elif algorithm == CompressionAlgorithm.ZSTD and ZSTD_AVAILABLE:
                cctx = zstd.ZstdCompressor(level=level)
                compressed_data = cctx.compress(data)
            elif algorithm == CompressionAlgorithm.LZ4 and LZ4_AVAILABLE:
                compressed_data = lz4.compress(data, compression_level=level)
            else:
                # Fallback para gzip
                compressed_data = gzip.compress(data, compresslevel=6)
                algorithm = CompressionAlgorithm.GZIP
            
            compression_time = time.time() - start_time
            
            # Teste de descompressão para verificar integridade
            decomp_start = time.time()
            decompressed_data = self.decompress_data(compressed_data, algorithm)
            decompression_time = time.time() - decomp_start
            
            # Verificar integridade
            if decompressed_data != data:
                raise ValueError("Dados corrompidos após compressão/descompressão")
            
            # Calcular métricas
            compressed_size = len(compressed_data)
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
            speed_mbps = (original_size / (1024 * 1024)) / compression_time if compression_time > 0 else 0
            
            # Score de eficiência (combina ratio e velocidade)
            efficiency_score = (1.0 - compression_ratio) * 0.7 + min(speed_mbps / 100, 1.0) * 0.3
            
            metrics = CompressionMetrics(
                algorithm=algorithm,
                level=level,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                compression_time=compression_time,
                decompression_time=decompression_time,
                speed_mbps=speed_mbps,
                efficiency_score=efficiency_score
            )
            
            # Atualizar estatísticas
            self._update_algorithm_stats(algorithm, metrics)
            
            return compressed_data, metrics
            
        except Exception as e:
            # Em caso de erro, tentar fallback
            if algorithm != self.config.fallback_algorithm:
                return self.compress_data(data, self.config.fallback_algorithm, self.config.fallback_level.value)
            else:
                raise Exception(f"Falha na compressão: {e}")
    
    def decompress_data(self, data: bytes, algorithm: CompressionAlgorithm) -> bytes:
        """
        Descomprime dados usando algoritmo especificado
        
        Args:
            data: Dados comprimidos
            algorithm: Algoritmo usado na compressão
            
        Returns:
            Dados descomprimidos
        """
        if not data:
            return b''
        
        try:
            if algorithm == CompressionAlgorithm.NONE:
                return data
            elif algorithm == CompressionAlgorithm.GZIP:
                return gzip.decompress(data)
            elif algorithm == CompressionAlgorithm.LZMA:
                return lzma.decompress(data)
            elif algorithm == CompressionAlgorithm.BZ2:
                return bz2.decompress(data)
            elif algorithm == CompressionAlgorithm.ZLIB:
                return zlib.decompress(data)
            elif algorithm == CompressionAlgorithm.ZSTD and ZSTD_AVAILABLE:
                dctx = zstd.ZstdDecompressor()
                return dctx.decompress(data)
            elif algorithm == CompressionAlgorithm.LZ4 and LZ4_AVAILABLE:
                return lz4.decompress(data)
            else:
                raise ValueError(f"Algoritmo não suportado: {algorithm}")
                
        except Exception as e:
            raise Exception(f"Falha na descompressão: {e}")
    
    def compress_file(
        self, 
        file_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        algorithm: Optional[CompressionAlgorithm] = None,
        level: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Comprime arquivo completo
        
        Args:
            file_path: Arquivo de origem
            output_path: Arquivo de destino (opcional)
            algorithm: Algoritmo específico (opcional)
            level: Nível específico (opcional)
            
        Returns:
            Dicionário com resultados da compressão
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")
        
        file_size = path.stat().st_size
        
        # Verificar limites
        if file_size > self.config.max_file_size:
            return {
                "success": False,
                "error": f"Arquivo muito grande: {file_size / (1024*1024):.1f}MB > {self.config.max_file_size / (1024*1024):.1f}MB"
            }
        
        try:
            # Analisar arquivo se necessário
            if self.config.analyze_before_compress and algorithm is None:
                profile = self.analyze_file(path)
                algorithm = profile.recommended_algorithm
                level = profile.recommended_level
            
            # Usar padrões se não especificado
            if algorithm is None:
                algorithm = self.config.fallback_algorithm
            if level is None:
                level = self.config.fallback_level.value
            
            # Ler arquivo
            with open(path, 'rb') as f:
                data = f.read()
            
            # Comprimir
            compressed_data, metrics = self.compress_data(data, algorithm, level)
            
            # Determinar caminho de saída
            if output_path is None:
                output_path = path.with_suffix(path.suffix + f".{algorithm.value}")
            else:
                output_path = Path(output_path)
            
            # Salvar arquivo comprimido
            with open(output_path, 'wb') as f:
                f.write(compressed_data)
            
            # Salvar metadados
            metadata = {
                "original_file": str(path),
                "algorithm": algorithm.value,
                "level": level,
                "original_size": metrics.original_size,
                "compressed_size": metrics.compressed_size,
                "compression_ratio": metrics.compression_ratio,
                "timestamp": time.time()
            }
            
            metadata_path = output_path.with_suffix(output_path.suffix + ".meta")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Registrar na história
            with self._lock:
                self._compression_history.append({
                    "timestamp": time.time(),
                    "file": str(path),
                    "algorithm": algorithm.value,
                    "level": level,
                    "metrics": metrics
                })
            
            return {
                "success": True,
                "original_path": str(path),
                "compressed_path": str(output_path),
                "metadata_path": str(metadata_path),
                "metrics": metrics,
                "savings_bytes": metrics.original_size - metrics.compressed_size,
                "savings_percent": (1 - metrics.compression_ratio) * 100
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "original_path": str(path)
            }
    
    def _update_algorithm_stats(self, algorithm: CompressionAlgorithm, metrics: CompressionMetrics):
        """Atualiza estatísticas do algoritmo"""
        with self._lock:
            stats = self._algorithm_stats[algorithm]
            
            # Média móvel simples
            count = stats['total_count']
            stats['avg_ratio'] = (stats['avg_ratio'] * count + metrics.compression_ratio) / (count + 1)
            stats['avg_speed'] = (stats['avg_speed'] * count + metrics.speed_mbps) / (count + 1)
            stats['total_count'] = count + 1
            
            # Se compressão foi bem-sucedida (ratio < 1.0)
            if metrics.compression_ratio < 1.0:
                stats['success_count'] += 1
    
    def get_algorithm_stats(self) -> Dict[str, Dict[str, float]]:
        """Retorna estatísticas dos algoritmos"""
        with self._lock:
            return {
                alg.value: {
                    'avg_compression_ratio': stats['avg_ratio'],
                    'avg_speed_mbps': stats['avg_speed'],
                    'success_rate': stats['success_count'] / max(1, stats['total_count']),
                    'total_uses': stats['total_count']
                }
                for alg, stats in self._algorithm_stats.items()
            }
    
    def get_compression_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retorna histórico de compressões"""
        with self._lock:
            return list(self._compression_history)[-limit:]
    
    def benchmark_algorithms(
        self, 
        data: bytes,
        algorithms: Optional[List[CompressionAlgorithm]] = None
    ) -> Dict[CompressionAlgorithm, CompressionMetrics]:
        """
        Faz benchmark de algoritmos disponíveis
        
        Args:
            data: Dados para testar
            algorithms: Lista de algoritmos (None = todos disponíveis)
            
        Returns:
            Dicionário com métricas de cada algoritmo
        """
        if algorithms is None:
            algorithms = [
                CompressionAlgorithm.GZIP,
                CompressionAlgorithm.LZMA,
                CompressionAlgorithm.BZ2,
                CompressionAlgorithm.ZLIB
            ]
            
            if ZSTD_AVAILABLE:
                algorithms.append(CompressionAlgorithm.ZSTD)
            if LZ4_AVAILABLE:
                algorithms.append(CompressionAlgorithm.LZ4)
        
        results = {}
        
        for algorithm in algorithms:
            try:
                level = 6  # Nível balanceado para benchmark
                compressed_data, metrics = self.compress_data(data, algorithm, level)
                results[algorithm] = metrics
            except Exception as e:
                print(f"Erro ao testar {algorithm.value}: {e}")
        
        return results
    
    def add_background_compression(self, file_path: Union[str, Path], callback: Optional[Callable] = None):
        """Adiciona arquivo para compressão em background"""
        if self.config.background_compression:
            with self._lock:
                self._background_queue.append((Path(file_path), callback))
    
    def stop_background_processing(self):
        """Para processamento em background"""
        self._stop_background.set()
        if self._background_thread and self._background_thread.is_alive():
            self._background_thread.join(timeout=5.0)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_background_processing()


# Factory functions
def create_intelligent_compressor(config: CompressionConfig = None) -> IntelligentCompressor:
    """Cria instância do compressor inteligente"""
    return IntelligentCompressor(config)

def get_available_algorithms() -> List[CompressionAlgorithm]:
    """Retorna lista de algoritmos disponíveis"""
    available = [
        CompressionAlgorithm.GZIP,
        CompressionAlgorithm.LZMA,
        CompressionAlgorithm.BZ2,
        CompressionAlgorithm.ZLIB,
        CompressionAlgorithm.NONE
    ]
    
    if ZSTD_AVAILABLE:
        available.append(CompressionAlgorithm.ZSTD)
    if LZ4_AVAILABLE:
        available.append(CompressionAlgorithm.LZ4)
    
    return available

# Context manager para compressão automática
class auto_compression:
    """Context manager para compressão automática de arquivos"""
    
    def __init__(self, config: CompressionConfig = None):
        self.config = config
        self.compressor = None
        self.compressed_files = []
    
    def __enter__(self) -> IntelligentCompressor:
        self.compressor = create_intelligent_compressor(self.config)
        return self.compressor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.compressor:
            self.compressor.stop_background_processing()