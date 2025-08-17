# -*- coding: utf-8 -*-
"""
Integração de Compressão Inteligente - MeetingScribe
Integra o sistema de compressão inteligente com cache e streaming
"""

from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple
import time

from .intelligent_compression import (
    IntelligentCompressor,
    CompressionConfig,
    CompressionAlgorithm,
    CompressionStrategy,
    create_intelligent_compressor
)

from .file_cache import get_file_cache, FileCache, CacheEntry
from .streaming_processor import AudioStreamer, StreamConfig, create_audio_streamer

class CompressedCacheEntry(CacheEntry):
    """Entrada de cache com compressão inteligente"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compression_algorithm: Optional[CompressionAlgorithm] = None
        self.compression_level: int = 6
        self.compression_metrics: Optional[Dict[str, Any]] = None

class IntelligentFileCache(FileCache):
    """
    Cache de arquivos com compressão inteligente integrada
    
    Estende o FileCache com:
    - Compressão automática baseada em análise de conteúdo
    - Seleção adaptativa de algoritmos
    - Otimização contínua baseada em performance
    - Integração transparente com transcriber
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Configurar compressor inteligente
        compression_config = CompressionConfig()
        compression_config.strategy = CompressionStrategy.INTELLIGENT
        compression_config.analyze_before_compress = True
        compression_config.background_compression = True
        compression_config.adaptive_threshold = 0.05  # 5% melhoria mínima
        
        self.compressor = create_intelligent_compressor(compression_config)
        
        # Estatísticas avançadas
        self._compression_stats = {
            'intelligent_compressions': 0,
            'algorithm_switches': 0,
            'adaptive_optimizations': 0,
            'auto_compressions': 0,
            'compression_time_saved': 0.0,
            'space_saved_mb': 0.0,
            'failed_compressions': 0,
            'algorithm_performance': {},
            'content_type_stats': {}
        }
        
        # Configurações adaptativas
        self._adaptive_config = {
            'min_file_size_kb': 10,           # Não comprimir < 10KB
            'max_compression_time_s': 30,     # Timeout para compressão
            'target_compression_ratio': 0.7,  # Ratio alvo
            'background_queue_size': 50,      # Tamanho máximo da fila
            'analysis_interval_s': 300,       # Análise a cada 5min
            'auto_optimize_threshold': 0.1    # 10% melhoria para auto-otimizar
        }
        
        # Thread de otimização adaptativa
        self._last_optimization = time.time()
        
        # Hooks para integração
        self._integration_hooks = []
    
    def _compress_data_intelligent(self, content: Any, content_type: str, 
                                 file_path: Optional[Path] = None) -> Tuple[bytes, Dict[str, Any]]:
        """
        Comprime dados usando compressão inteligente
        
        Args:
            content: Dados para comprimir
            content_type: Tipo do conteúdo (audio_data, transcription, etc.)
            file_path: Caminho original do arquivo (para análise)
            
        Returns:
            Tuple com (dados_comprimidos, metadados_compressão)
        """
        start_time = time.time()
        
        try:
            # Preparar dados para compressão
            if isinstance(content, str):
                data_bytes = content.encode('utf-8')
            elif isinstance(content, bytes):
                data_bytes = content
            else:
                # Serializar objetos complexos
                import pickle
                data_bytes = pickle.dumps(content)
            
            # Verificar se vale a pena comprimir
            size_kb = len(data_bytes) / 1024
            if size_kb < self._adaptive_config['min_file_size_kb']:
                return data_bytes, {
                    'algorithm': 'none',
                    'ratio': 1.0,
                    'reason': f'file_too_small_{size_kb:.1f}kb'
                }
            
            # Análise inteligente do conteúdo
            if file_path and file_path.exists():
                # Usar arquivo original para análise
                profile = self.compressor.analyze_file(file_path)
                algorithm = profile.recommended_algorithm
                level = profile.recommended_level
                analysis_reason = "file_analysis"
            else:
                # Análise baseada no tipo de conteúdo
                algorithm, level, analysis_reason = self._select_algorithm_by_content_type(
                    content_type, data_bytes
                )
            
            # Executar compressão
            compressed_data, metrics = self.compressor.compress_data(data_bytes, algorithm, level)
            compression_time = time.time() - start_time
            
            # Verificar se compressão foi efetiva
            if metrics.compression_ratio > self._adaptive_config['target_compression_ratio']:
                # Compressão ineficiente, retornar dados originais
                return data_bytes, {
                    'algorithm': 'none',
                    'ratio': 1.0,
                    'reason': f'inefficient_compression_{metrics.compression_ratio:.3f}'
                }
            
            # Verificar timeout
            if compression_time > self._adaptive_config['max_compression_time_s']:
                return data_bytes, {
                    'algorithm': 'none',
                    'ratio': 1.0,
                    'reason': f'timeout_{compression_time:.1f}s'
                }
            
            # Atualizar estatísticas
            self._update_compression_stats(content_type, algorithm, metrics, compression_time)
            
            # Metadados da compressão
            compression_metadata = {
                'algorithm': algorithm.value,
                'level': level,
                'ratio': metrics.compression_ratio,
                'time': compression_time,
                'original_size': len(data_bytes),
                'compressed_size': len(compressed_data),
                'savings_bytes': len(data_bytes) - len(compressed_data),
                'reason': analysis_reason,
                'content_type': content_type
            }
            
            # Notificar hooks
            self._notify_integration_hooks('compression_completed', compression_metadata)
            
            return compressed_data, compression_metadata
            
        except Exception as e:
            # Em caso de erro, retornar dados originais
            self._compression_stats['failed_compressions'] += 1
            error_time = time.time() - start_time
            
            return data_bytes, {
                'algorithm': 'none',
                'ratio': 1.0,
                'reason': f'error_{str(e)[:50]}',
                'error_time': error_time
            }
    
    def _select_algorithm_by_content_type(self, content_type: str, data: bytes) -> Tuple[CompressionAlgorithm, int, str]:
        """
        Seleciona algoritmo baseado no tipo de conteúdo
        
        Returns:
            Tuple com (algorithm, level, reason)
        """
        
        # Análise rápida de entropia
        entropy = self._calculate_entropy_fast(data[:1024])  # Amostra de 1KB
        
        if content_type == 'audio_data':
            # Dados de áudio - geralmente já comprimidos ou de baixa entropia
            if entropy > 6.0:
                # Alta entropia - provavelmente já comprimido
                return CompressionAlgorithm.NONE, 0, "audio_high_entropy"
            else:
                # Baixa entropia - pode se beneficiar de compressão rápida
                return CompressionAlgorithm.LZ4 if hasattr(self.compressor, 'LZ4_AVAILABLE') and self.compressor.LZ4_AVAILABLE else CompressionAlgorithm.GZIP, 3, "audio_low_entropy"
        
        elif content_type in ['transcription', 'metadata']:
            # Texto/JSON - comprime muito bem
            if len(data) > 100 * 1024:  # > 100KB
                return CompressionAlgorithm.ZSTD if hasattr(self.compressor, 'ZSTD_AVAILABLE') and self.compressor.ZSTD_AVAILABLE else CompressionAlgorithm.LZMA, 6, "text_large"
            else:
                return CompressionAlgorithm.GZIP, 6, "text_small"
        
        elif content_type == 'cache_data':
            # Dados de cache - balanceado
            return CompressionAlgorithm.ZSTD if hasattr(self.compressor, 'ZSTD_AVAILABLE') and self.compressor.ZSTD_AVAILABLE else CompressionAlgorithm.GZIP, 4, "cache_balanced"
        
        else:
            # Tipo desconhecido - usar algoritmo seguro
            return CompressionAlgorithm.GZIP, 6, "unknown_type"
    
    def _calculate_entropy_fast(self, data: bytes) -> float:
        """Calcula entropia rápida para análise"""
        if not data:
            return 0.0
        
        # Frequência simplificada
        freq = [0] * 256
        for byte in data:
            freq[byte] += 1
        
        # Entropia Shannon simplificada
        entropy = 0.0
        length = len(data)
        
        for count in freq:
            if count > 0:
                prob = count / length
                entropy -= prob * (prob.bit_length() - 1) if prob > 0 else 0
        
        return min(entropy, 8.0)  # Max 8 bits
    
    def _update_compression_stats(self, content_type: str, algorithm: CompressionAlgorithm, 
                                metrics, compression_time: float):
        """Atualiza estatísticas de compressão"""
        
        # Estatísticas gerais
        self._compression_stats['intelligent_compressions'] += 1
        self._compression_stats['compression_time_saved'] += compression_time
        self._compression_stats['space_saved_mb'] += (metrics.original_size - metrics.compressed_size) / (1024 * 1024)
        
        # Estatísticas por algoritmo
        alg_name = algorithm.value
        if alg_name not in self._compression_stats['algorithm_performance']:
            self._compression_stats['algorithm_performance'][alg_name] = {
                'count': 0,
                'avg_ratio': 0.0,
                'avg_time': 0.0,
                'total_saved': 0
            }
        
        alg_stats = self._compression_stats['algorithm_performance'][alg_name]
        alg_stats['count'] += 1
        
        # Média móvel
        count = alg_stats['count']
        alg_stats['avg_ratio'] = (alg_stats['avg_ratio'] * (count - 1) + metrics.compression_ratio) / count
        alg_stats['avg_time'] = (alg_stats['avg_time'] * (count - 1) + compression_time) / count
        alg_stats['total_saved'] += metrics.original_size - metrics.compressed_size
        
        # Estatísticas por tipo de conteúdo
        if content_type not in self._compression_stats['content_type_stats']:
            self._compression_stats['content_type_stats'][content_type] = {
                'count': 0,
                'avg_ratio': 0.0,
                'preferred_algorithm': alg_name
            }
        
        type_stats = self._compression_stats['content_type_stats'][content_type]
        type_stats['count'] += 1
        count = type_stats['count']
        type_stats['avg_ratio'] = (type_stats['avg_ratio'] * (count - 1) + metrics.compression_ratio) / count
        
        # Atualizar algoritmo preferido se este teve melhor performance
        current_best = self._compression_stats['algorithm_performance'].get(type_stats['preferred_algorithm'], {})
        current_performance = current_best.get('avg_ratio', 1.0)
        
        if alg_stats['avg_ratio'] < current_performance:  # Menor ratio = melhor compressão
            type_stats['preferred_algorithm'] = alg_name
            self._compression_stats['algorithm_switches'] += 1
    
    def _notify_integration_hooks(self, event: str, data: Dict[str, Any]):
        """Notifica hooks de integração"""
        for hook in self._integration_hooks:
            try:
                hook(event, data)
            except Exception as e:
                print(f"Erro em hook de integração: {e}")
    
    def add_integration_hook(self, hook: Callable):
        """Adiciona hook para eventos de integração"""
        self._integration_hooks.append(hook)
    
    def cache_with_intelligent_compression(self, key: str, file_path: Path, 
                                         content_type: str = "auto",
                                         force_analysis: bool = False) -> bool:
        """
        Adiciona arquivo ao cache com compressão inteligente
        
        Args:
            key: Chave do cache
            file_path: Caminho do arquivo
            content_type: Tipo do conteúdo ou "auto" para detectar
            force_analysis: Forçar nova análise mesmo se já em cache
            
        Returns:
            True se bem-sucedido
        """
        try:
            if not file_path.exists():
                return False
            
            # Detectar tipo de conteúdo automaticamente
            if content_type == "auto":
                content_type = self._detect_content_type(file_path)
            
            # Verificar se já está em cache
            if not force_analysis and self.contains(key):
                return True
            
            # Ler arquivo
            if content_type == "audio_data":
                # Para áudio, pode precisar de tratamento especial
                with open(file_path, 'rb') as f:
                    content = f.read()
            elif content_type in ["transcription", "metadata"]:
                # Para texto/JSON
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                # Binário genérico
                with open(file_path, 'rb') as f:
                    content = f.read()
            
            # Comprimir inteligentemente
            compressed_data, compression_metadata = self._compress_data_intelligent(
                content, content_type, file_path
            )
            
            # Criar entrada de cache comprimida
            entry = CompressedCacheEntry(
                file_path=file_path,
                content=compressed_data,
                content_type=content_type,
                size_bytes=len(compressed_data),
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=0
            )
            
            # Adicionar metadados de compressão
            entry.compression_metrics = compression_metadata
            if compression_metadata['algorithm'] != 'none':
                entry.compression_algorithm = CompressionAlgorithm(compression_metadata['algorithm'])
                entry.compression_level = compression_metadata['level']
            
            # Adicionar ao cache
            self.put(key, entry)
            
            # Otimização adaptativa periódica
            current_time = time.time()
            if current_time - self._last_optimization > self._adaptive_config['analysis_interval_s']:
                self._optimize_compression_settings()
                self._last_optimization = current_time
            
            return True
            
        except Exception as e:
            print(f"Erro ao cachear com compressão inteligente {file_path}: {e}")
            return False
    
    def _detect_content_type(self, file_path: Path) -> str:
        """Detecta tipo de conteúdo baseado na extensão"""
        suffix = file_path.suffix.lower()
        
        if suffix in ['.wav', '.mp3', '.flac', '.m4a', '.ogg']:
            return "audio_data"
        elif suffix in ['.txt', '.json', '.srt', '.vtt']:
            return "transcription"
        elif suffix in ['.meta', '.info', '.log']:
            return "metadata"
        else:
            return "binary_data"
    
    def _optimize_compression_settings(self):
        """Otimiza configurações de compressão baseado em performance histórica"""
        try:
            self._compression_stats['adaptive_optimizations'] += 1
            
            # Analisar performance dos algoritmos
            best_algorithms = {}
            for content_type, stats in self._compression_stats['content_type_stats'].items():
                if stats['count'] > 5:  # Mínimo de amostras
                    best_algorithms[content_type] = stats['preferred_algorithm']
            
            # Atualizar configurações adaptativas baseado nos resultados
            total_compressions = self._compression_stats['intelligent_compressions']
            if total_compressions > 50:  # Só otimizar com dados suficientes
                
                # Ajustar limite mínimo de arquivo baseado na eficiência
                avg_small_file_ratio = self._get_avg_compression_ratio_for_small_files()
                if avg_small_file_ratio > 0.9:  # Pouca compressão em arquivos pequenos
                    self._adaptive_config['min_file_size_kb'] = min(
                        self._adaptive_config['min_file_size_kb'] * 1.5, 50
                    )
                
                # Ajustar timeout baseado na velocidade média
                avg_time = self._compression_stats['compression_time_saved'] / total_compressions
                if avg_time > 10.0:  # Muito lento
                    self._adaptive_config['max_compression_time_s'] = max(
                        self._adaptive_config['max_compression_time_s'] * 0.8, 10
                    )
            
            self._notify_integration_hooks('optimization_completed', {
                'best_algorithms': best_algorithms,
                'adaptive_config': self._adaptive_config.copy()
            })
            
        except Exception as e:
            print(f"Erro na otimização adaptativa: {e}")
    
    def _get_avg_compression_ratio_for_small_files(self) -> float:
        """Calcula ratio médio de compressão para arquivos pequenos"""
        # Implementação simplificada - poderia ser mais sofisticada
        return 0.85  # Placeholder
    
    def get_compression_analytics(self) -> Dict[str, Any]:
        """Retorna analytics detalhadas de compressão"""
        total_compressions = self._compression_stats['intelligent_compressions']
        
        analytics = {
            'overview': {
                'total_intelligent_compressions': total_compressions,
                'total_space_saved_mb': round(self._compression_stats['space_saved_mb'], 2),
                'avg_compression_time': round(
                    self._compression_stats['compression_time_saved'] / max(1, total_compressions), 3
                ),
                'failed_compressions': self._compression_stats['failed_compressions'],
                'success_rate': round(
                    total_compressions / max(1, total_compressions + self._compression_stats['failed_compressions']) * 100, 1
                )
            },
            'algorithm_performance': self._compression_stats['algorithm_performance'],
            'content_type_optimization': self._compression_stats['content_type_stats'],
            'adaptive_settings': self._adaptive_config.copy(),
            'recommendations': self._generate_optimization_recommendations()
        }
        
        return analytics
    
    def _generate_optimization_recommendations(self) -> List[Dict[str, str]]:
        """Gera recomendações de otimização baseado nos dados"""
        recommendations = []
        
        # Analisar algoritmos subutilizados
        alg_performance = self._compression_stats['algorithm_performance']
        
        # Recomendar ZSTD se disponível e não usado
        if 'zstd' not in alg_performance and hasattr(self.compressor, 'ZSTD_AVAILABLE'):
            recommendations.append({
                'type': 'algorithm',
                'priority': 'high',
                'message': 'Consider installing zstandard for better compression',
                'action': 'pip install zstandard'
            })
        
        # Recomendar LZ4 para velocidade
        if 'lz4' not in alg_performance and hasattr(self.compressor, 'LZ4_AVAILABLE'):
            recommendations.append({
                'type': 'algorithm',
                'priority': 'medium',
                'message': 'Consider installing lz4 for faster compression',
                'action': 'pip install lz4'
            })
        
        # Analisar eficiência geral
        if self._compression_stats['intelligent_compressions'] > 20:
            avg_ratio = sum(
                stats['avg_ratio'] * stats['count'] 
                for stats in alg_performance.values()
            ) / sum(stats['count'] for stats in alg_performance.values())
            
            if avg_ratio > 0.8:
                recommendations.append({
                    'type': 'efficiency',
                    'priority': 'medium',
                    'message': 'Low compression efficiency detected',
                    'action': 'Review content types and compression policies'
                })
        
        return recommendations
    
    def integrate_with_transcriber(self, transcriber_instance):
        """
        Integra cache inteligente com transcriber
        
        Args:
            transcriber_instance: Instância do transcriber para integrar
        """
        try:
            # Adicionar hook para cachear resultados de transcrição automaticamente
            def transcription_hook(event: str, data: Dict[str, Any]):
                if event == 'transcription_completed':
                    file_path = data.get('audio_file')
                    transcription = data.get('transcription')
                    
                    if file_path and transcription:
                        # Cachear áudio original com compressão inteligente
                        audio_key = f"audio:{Path(file_path).stem}"
                        self.cache_with_intelligent_compression(
                            audio_key, Path(file_path), "audio_data"
                        )
                        
                        # Cachear transcrição
                        trans_key = f"transcription:{Path(file_path).stem}"
                        self.cache_with_intelligent_compression(
                            trans_key, Path(transcription), "transcription"
                        )
            
            self.add_integration_hook(transcription_hook)
            
            # Se o transcriber tem método para adicionar hooks, usar
            if hasattr(transcriber_instance, 'add_hook'):
                transcriber_instance.add_hook(transcription_hook)
            
            return True
            
        except Exception as e:
            print(f"Erro integrando com transcriber: {e}")
            return False


# Factory function
def create_intelligent_cache(cache_config=None, compression_strategy=CompressionStrategy.INTELLIGENT) -> IntelligentFileCache:
    """
    Cria instância do cache inteligente
    
    Args:
        cache_config: Configuração do cache
        compression_strategy: Estratégia de compressão
        
    Returns:
        Instância do IntelligentFileCache
    """
    cache = IntelligentFileCache(cache_config)
    
    # Configurar estratégia de compressão
    cache.compressor.config.strategy = compression_strategy
    
    return cache


# Singleton global para facilitar uso
_intelligent_cache: Optional[IntelligentFileCache] = None

def get_intelligent_cache() -> IntelligentFileCache:
    """Retorna instância singleton do cache inteligente"""
    global _intelligent_cache
    
    if _intelligent_cache is None:
        _intelligent_cache = create_intelligent_cache()
    
    return _intelligent_cache
    
    def _compress_data_intelligent(self, content: Any, content_type: str, file_path: Optional[Path] = None) -> Tuple[bytes, float, Dict[str, Any]]:
        """
        Comprime dados usando compressão inteligente
        
        Returns:
            Tuple com (dados_comprimidos, compression_ratio, metadados)
        """
        try:
            # Serializar conteúdo
            if isinstance(content, bytes):
                raw_data = content
            else:
                import pickle
                raw_data = pickle.dumps(content)
            
            original_size = len(raw_data)
            
            # Se temos caminho do arquivo, analisar para escolher algoritmo
            algorithm = None
            level = None
            
            if file_path and file_path.exists():
                try:
                    profile = self.compressor.analyze_file(file_path)
                    algorithm = profile.recommended_algorithm
                    level = profile.recommended_level
                    
                    # Se algoritmo é NONE, usar compressão mínima
                    if algorithm == CompressionAlgorithm.NONE:
                        algorithm = CompressionAlgorithm.GZIP
                        level = 1
                        
                except Exception:
                    # Fallback para análise de conteúdo
                    pass
            
            # Se não conseguiu analisar, usar heurística baseada no tipo
            if algorithm is None:
                algorithm, level = self._choose_algorithm_by_content_type(content_type, original_size)
            
            # Comprimir dados
            compressed_data, metrics = self.compressor.compress_data(raw_data, algorithm, level)
            
            self._compression_stats['intelligent_compressions'] += 1
            
            # Verificar se vale a pena usar compressão inteligente vs gzip padrão
            if metrics.compression_ratio > 0.95:  # < 5% de economia
                # Usar gzip simples como fallback
                import gzip
                compressed_data = gzip.compress(raw_data, compresslevel=6)
                compression_ratio = len(compressed_data) / original_size
                
                compression_metadata = {
                    'algorithm': 'gzip_fallback',
                    'level': 6,
                    'intelligent_used': False,
                    'fallback_reason': 'low_compression_ratio'
                }
            else:
                compression_ratio = metrics.compression_ratio
                compression_metadata = {
                    'algorithm': metrics.algorithm.value,
                    'level': metrics.level,
                    'intelligent_used': True,
                    'compression_time': metrics.compression_time,
                    'speed_mbps': metrics.speed_mbps,
                    'efficiency_score': metrics.efficiency_score
                }
            
            return compressed_data, compression_ratio, compression_metadata
            
        except Exception as e:
            # Fallback para compressão gzip padrão
            import gzip
            compressed_data = gzip.compress(raw_data, compresslevel=6)
            compression_ratio = len(compressed_data) / original_size
            
            compression_metadata = {
                'algorithm': 'gzip_fallback',
                'level': 6,
                'intelligent_used': False,
                'fallback_reason': f'error: {str(e)}'
            }
            
            return compressed_data, compression_ratio, compression_metadata
    
    def _choose_algorithm_by_content_type(self, content_type: str, size: int) -> Tuple[CompressionAlgorithm, int]:
        """Escolhe algoritmo baseado no tipo de conteúdo"""
        
        if content_type == 'audio_data':
            # Dados de áudio geralmente já são comprimidos
            return CompressionAlgorithm.LZ4 if hasattr(self.compressor, 'LZ4_AVAILABLE') and self.compressor.__class__.LZ4_AVAILABLE else CompressionAlgorithm.GZIP, 3
        
        elif content_type == 'transcription':
            # Texto se comprime muito bem
            return CompressionAlgorithm.LZMA, 6
        
        elif content_type == 'metadata':
            # Metadados são pequenos, usar compressão rápida
            return CompressionAlgorithm.GZIP, 3
        
        elif size > 1024 * 1024:  # > 1MB
            # Arquivos grandes - usar balanceado
            return CompressionAlgorithm.ZSTD if hasattr(self.compressor, 'ZSTD_AVAILABLE') and self.compressor.__class__.ZSTD_AVAILABLE else CompressionAlgorithm.GZIP, 6
        
        else:
            # Padrão - balanceado
            return CompressionAlgorithm.GZIP, 6
    
    def _decompress_data_intelligent(self, compressed_data: bytes, compression_metadata: Dict[str, Any], content_type: str) -> Any:
        """Descomprime dados usando informações de compressão"""
        
        try:
            algorithm_name = compression_metadata.get('algorithm', 'gzip')
            
            if algorithm_name == 'gzip_fallback' or not compression_metadata.get('intelligent_used', False):
                # Usar descompressão gzip padrão
                import gzip
                raw_data = gzip.decompress(compressed_data)
            else:
                # Usar descompressão inteligente
                try:
                    algorithm = CompressionAlgorithm(algorithm_name)
                    raw_data = self.compressor.decompress_data(compressed_data, algorithm)
                except Exception:
                    # Fallback para gzip
                    import gzip
                    raw_data = gzip.decompress(compressed_data)
            
            # Deserializar se necessário
            if content_type in ['transcription', 'metadata'] or not isinstance(raw_data, bytes):
                try:
                    import pickle
                    return pickle.loads(raw_data)
                except:
                    return raw_data
            else:
                return raw_data
                
        except Exception as e:
            raise Exception(f"Falha na descompressão: {e}")
    
    def put(self, file_path: Union[str, Path], content: Any, content_type: str = "raw_bytes") -> bool:
        """
        Adiciona conteúdo ao cache com compressão inteligente
        """
        path = Path(file_path)
        cache_key = self._generate_cache_key(path)
        
        try:
            with self._lock:
                # Verificar se já existe e é válido
                if cache_key in self._cache:
                    existing_entry = self._cache[cache_key]
                    if self._is_entry_valid(existing_entry):
                        # Mover para o final (LRU)
                        self._cache.move_to_end(cache_key)
                        return True
                
                # Comprimir usando sistema inteligente
                compressed_data, compression_ratio, compression_metadata = self._compress_data_intelligent(
                    content, content_type, path
                )
                
                compressed_size = len(compressed_data)
                
                # Verificar limite de memória
                if not self._check_memory_limit(compressed_size):
                    self._evict_entries(compressed_size)
                
                # Criar entrada de cache
                entry = CompressedCacheEntry(
                    key=cache_key,
                    file_path=path,
                    content=compressed_data,
                    content_type=content_type,
                    size_bytes=compressed_size,
                    created_at=datetime.now(),
                    accessed_at=datetime.now(),
                    access_count=1,
                    ttl_hours=self.config.ttl_hours,
                    compression_ratio=compression_ratio
                )
                
                # Adicionar metadados de compressão inteligente
                entry.compression_algorithm = compression_metadata.get('algorithm')
                entry.compression_level = compression_metadata.get('level', 6)
                entry.compression_metrics = compression_metadata
                
                # Adicionar ao cache
                self._cache[cache_key] = entry
                self._memory_usage += compressed_size
                self._stats['puts'] += 1
                
                # Salvar entry se persistência estiver habilitada
                if self.config.persistence_enabled:
                    self._save_entry_to_disk(entry)
                
                return True
                
        except Exception as e:
            self._stats['errors'] += 1
            self.logger.error(f"Erro ao adicionar ao cache: {e}")
            return False
    
    def get(self, file_path: Union[str, Path]) -> Optional[Any]:
        """
        Recupera conteúdo do cache com descompressão inteligente
        """
        path = Path(file_path)
        cache_key = self._generate_cache_key(path)
        
        try:
            with self._lock:
                if cache_key in self._cache:
                    entry = self._cache[cache_key]
                    
                    # Verificar validade
                    if not self._is_entry_valid(entry):
                        del self._cache[cache_key]
                        self._memory_usage -= entry.size_bytes
                        self._stats['evictions'] += 1
                        return None
                    
                    # Atualizar estatísticas de acesso
                    entry.accessed_at = datetime.now()
                    entry.access_count += 1
                    
                    # Mover para o final (LRU)
                    self._cache.move_to_end(cache_key)
                    
                    # Descomprimir usando sistema inteligente
                    if hasattr(entry, 'compression_metrics') and entry.compression_metrics:
                        decompressed_content = self._decompress_data_intelligent(
                            entry.content, 
                            entry.compression_metrics, 
                            entry.content_type
                        )
                    else:
                        # Fallback para método original
                        decompressed_content = self._decompress_data(
                            entry.content, 
                            entry.compression_ratio, 
                            entry.content_type
                        )
                    
                    self._stats['hits'] += 1
                    return decompressed_content
                else:
                    self._stats['misses'] += 1
                    return None
                    
        except Exception as e:
            self._stats['errors'] += 1
            self.logger.error(f"Erro ao recuperar do cache: {e}")
            return None
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de compressão inteligente"""
        
        base_stats = super().get_stats()
        
        # Adicionar estatísticas de compressão inteligente
        intelligent_stats = {
            'intelligent_compressions': self._compression_stats['intelligent_compressions'],
            'algorithm_switches': self._compression_stats['algorithm_switches'],
            'adaptive_optimizations': self._compression_stats['adaptive_optimizations']
        }
        
        # Analisar uso de algoritmos
        algorithm_usage = {}
        total_intelligent = 0
        
        for entry in self._cache.values():
            if hasattr(entry, 'compression_metrics') and entry.compression_metrics:
                algorithm = entry.compression_metrics.get('algorithm', 'unknown')
                if algorithm not in algorithm_usage:
                    algorithm_usage[algorithm] = 0
                algorithm_usage[algorithm] += 1
                
                if entry.compression_metrics.get('intelligent_used', False):
                    total_intelligent += 1
        
        intelligent_stats.update({
            'algorithm_usage': algorithm_usage,
            'intelligent_ratio': total_intelligent / max(1, len(self._cache)),
            'compressor_stats': self.compressor.get_algorithm_stats()
        })
        
        base_stats.update(intelligent_stats)
        return base_stats

class StreamingWithCompression:
    """
    Classe que combina streaming de áudio com compressão inteligente
    """
    
    def __init__(self, stream_config: StreamConfig = None, compression_config: CompressionConfig = None):
        self.stream_config = stream_config or StreamConfig()
        self.compression_config = compression_config or CompressionConfig()
        
        # Habilitar cache no streaming
        self.stream_config.enable_cache = True
        
        # Criar componentes
        self.streamer = create_audio_streamer(self.stream_config)
        self.compressor = create_intelligent_compressor(self.compression_config)
        self.cache = IntelligentFileCache()
    
    def stream_and_compress(self, file_path: Path, output_dir: Optional[Path] = None):
        """
        Combina streaming de áudio com compressão inteligente dos chunks
        """
        if output_dir is None:
            output_dir = file_path.parent / "compressed_chunks"
        
        output_dir.mkdir(exist_ok=True)
        
        compressed_chunks = []
        
        # Stream do arquivo em chunks
        for chunk_id, chunk in enumerate(self.streamer.stream_file(file_path)):
            # Comprimir chunk
            chunk_path = output_dir / f"chunk_{chunk_id:04d}.bin"
            
            # Serializar chunk
            chunk_data = {
                'audio_data': chunk.data.tobytes(),
                'sample_rate': chunk.sample_rate,
                'start_time': chunk.start_time,
                'end_time': chunk.end_time,
                'chunk_id': chunk.chunk_id,
                'metadata': chunk.metadata
            }
            
            # Comprimir e salvar
            result = self.compressor.compress_file(
                chunk_path.with_suffix('.tmp'),  # Arquivo temporário
                chunk_path,
                algorithm=None,  # Deixar o sistema escolher
                level=None
            )
            
            if result['success']:
                compressed_chunks.append({
                    'chunk_id': chunk_id,
                    'path': str(chunk_path),
                    'compression_info': result
                })
                
                # Adicionar ao cache
                self.cache.put(chunk_path, chunk_data, 'audio_chunk')
        
        return compressed_chunks
    
    def get_combined_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas combinadas de streaming e compressão"""
        
        streaming_stats = self.streamer.get_stats()
        compression_stats = self.cache.get_compression_stats()
        
        return {
            'streaming': streaming_stats,
            'compression': compression_stats,
            'integration': {
                'cache_enabled': self.stream_config.enable_cache,
                'intelligent_compression': True,
                'combined_optimization': True
            }
        }

# Factory functions
def create_intelligent_file_cache(config=None) -> IntelligentFileCache:
    """Cria cache de arquivos com compressão inteligente"""
    return IntelligentFileCache(config)

def create_streaming_with_compression(
    stream_config: StreamConfig = None, 
    compression_config: CompressionConfig = None
) -> StreamingWithCompression:
    """Cria sistema combinado de streaming e compressão"""
    return StreamingWithCompression(stream_config, compression_config)

# Substituir o cache padrão por versão inteligente
_intelligent_cache_instance = None
_cache_lock = threading.Lock()

def get_intelligent_file_cache(config=None) -> IntelligentFileCache:
    """Singleton para cache inteligente"""
    global _intelligent_cache_instance
    
    with _cache_lock:
        if _intelligent_cache_instance is None:
            _intelligent_cache_instance = create_intelligent_file_cache(config)
        return _intelligent_cache_instance

def shutdown_intelligent_file_cache():
    """Shutdown do cache inteligente"""
    global _intelligent_cache_instance
    
    with _cache_lock:
        if _intelligent_cache_instance is not None:
            _intelligent_cache_instance.shutdown()
            _intelligent_cache_instance = None