"""
Transcritor com Processamento de Chunks Otimizado

Sistema de transcrição otimizado que processa áudio em chunks
inteligentes para melhor performance e uso de memória.

Author: MeetingScribe Team
Version: 1.1.0
Python: >=3.8
"""

import time
import tempfile
from pathlib import Path
from typing import Optional, List, Callable, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from loguru import logger

from .transcriber import (
    WhisperTranscriber, TranscriptionConfig, TranscriptionResult,
    TranscriptionSegment, TranscriptionProgress, TranscriptionError,
    WhisperModelSize
)

from src.core.audio_chunk_processor import (
    AudioChunkProcessor, ChunkConfig, ChunkStrategy, 
    AudioChunk, ChunkProcessingResult, create_chunk_processor
)

# Importar gerenciador de memória
try:
    from src.core.memory_manager import (
        get_memory_manager, register_for_cleanup, managed_memory,
        MemoryOptimizationStrategy
    )
    MEMORY_MANAGER_AVAILABLE = True
except ImportError:
    MEMORY_MANAGER_AVAILABLE = False
    logger.debug("Gerenciador de memória não disponível")


@dataclass
class ChunkedTranscriptionConfig:
    """Configuração para transcrição em chunks."""
    # Configurações básicas do transcriber
    transcription_config: TranscriptionConfig
    
    # Configurações de chunks
    chunk_strategy: ChunkStrategy = ChunkStrategy.ADAPTIVE
    chunk_duration: float = 30.0
    overlap_duration: float = 2.0
    
    # Performance
    parallel_chunks: bool = True
    max_parallel_workers: int = 2
    memory_limit_per_chunk_mb: float = 512
    
    # Otimizações
    cache_chunks: bool = True
    cleanup_intermediate_files: bool = True
    merge_overlapping_segments: bool = True


class ChunkedWhisperTranscriber:
    """
    Transcritor otimizado com processamento de chunks.
    
    Divide áudio em chunks inteligentes e processa em paralelo
    para melhor performance e uso eficiente de memória.
    """
    
    def __init__(self, config: Optional[ChunkedTranscriptionConfig] = None):
        """
        Inicializa o transcritor com chunks.
        
        Args:
            config: Configuração do transcritor chunked
        """
        if config is None:
            config = ChunkedTranscriptionConfig(
                transcription_config=TranscriptionConfig()
            )
        
        self.config = config
        self.chunk_processor = None
        self._transcriber = None
        self._lock = threading.Lock()
        self._temp_files = []
        
        # Registrar no gerenciador de memória
        if MEMORY_MANAGER_AVAILABLE:
            estimated_size = 100  # MB estimado para transcritor chunked
            register_for_cleanup(self, 'chunked_transcribers', estimated_size)
        
        logger.info(f"Transcritor chunked inicializado - estratégia: {config.chunk_strategy}")
    
    def _initialize_components(self):
        """Inicializa componentes sob demanda."""
        if self.chunk_processor is None:
            chunk_config = ChunkConfig(
                strategy=self.config.chunk_strategy,
                chunk_duration=self.config.chunk_duration,
                overlap_duration=self.config.overlap_duration,
                parallel_processing=self.config.parallel_chunks,
                max_workers=self.config.max_parallel_workers,
                memory_limit_mb=self.config.memory_limit_per_chunk_mb
            )
            
            self.chunk_processor = AudioChunkProcessor(chunk_config)
        
        if self._transcriber is None:
            self._transcriber = WhisperTranscriber(self.config.transcription_config)
    
    def transcribe_file(
        self,
        audio_path: Path,
        progress: Optional[TranscriptionProgress] = None,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcreve arquivo usando processamento de chunks.
        
        Args:
            audio_path: Caminho para arquivo de áudio
            progress: Callback de progresso
            language: Idioma específico
            
        Returns:
            TranscriptionResult: Resultado consolidado
        """
        start_time = time.time()
        
        try:
            # Monitorar e otimizar memória no início
            if MEMORY_MANAGER_AVAILABLE:
                memory_manager = get_memory_manager()
                initial_stats = memory_manager.get_current_stats()
                if initial_stats.pressure_level.value in ['high', 'critical']:
                    logger.warning(f"Pressão de memória alta: {initial_stats.pressure_level.value}")
                    memory_manager.optimize_memory(MemoryOptimizationStrategy.BALANCED)
            
            # Inicializar componentes
            self._initialize_components()
            
            if progress:
                progress.update(0.05, "Inicializando transcrição chunked...")
            
            # Carregar modelo uma vez
            self._transcriber.load_model(progress)
            
            if progress:
                progress.update(0.15, "Processando áudio em chunks...")
            
            # Processar áudio em chunks
            chunk_result = self.chunk_processor.process_audio_file(
                audio_path, 
                self._create_chunk_progress_callback(progress, 0.15, 0.35)
            )
            
            if progress:
                progress.update(0.35, f"Transcrevendo {len(chunk_result.chunks)} chunks...")
            
            # Transcrever chunks
            if self.config.parallel_chunks and len(chunk_result.chunks) > 1:
                chunk_results = self._transcribe_chunks_parallel(
                    chunk_result.chunks, language, progress, 0.35, 0.85
                )
            else:
                chunk_results = self._transcribe_chunks_sequential(
                    chunk_result.chunks, language, progress, 0.35, 0.85
                )
            
            if progress:
                progress.update(0.85, "Consolidando resultados...")
            
            # Consolidar resultados
            final_result = self._consolidate_results(
                chunk_results, chunk_result, start_time
            )
            
            if progress:
                progress.update(0.95, "Limpando arquivos temporários...")
            
            # Limpeza
            self._cleanup_temp_files()
            
            # Otimizar memória após transcrição
            if MEMORY_MANAGER_AVAILABLE:
                memory_manager = get_memory_manager()
                # Registrar resultado final
                result_size_mb = len(final_result.segments) * 0.5
                register_for_cleanup(final_result, 'transcription_results', result_size_mb)
                
                # Otimização baseada no tempo de processamento
                if processing_time > 60:  # > 1 minuto
                    memory_manager.optimize_memory(MemoryOptimizationStrategy.AGGRESSIVE)
                elif processing_time > 30:  # > 30 segundos
                    memory_manager.optimize_memory(MemoryOptimizationStrategy.BALANCED)
            
            if progress:
                progress.update(1.0, "Transcrição chunked concluída!")
            
            processing_time = time.time() - start_time
            logger.success(
                f"Transcrição chunked concluída em {processing_time:.2f}s - "
                f"{len(final_result.segments)} segmentos"
            )
            
            return final_result
            
        except Exception as e:
            self._cleanup_temp_files()
            error_msg = f"Erro na transcrição chunked: {str(e)}"
            logger.error(error_msg)
            
            if progress:
                progress.update(0.0, f"Erro: {str(e)}")
            
            raise TranscriptionError(error_msg) from e
    
    def _create_chunk_progress_callback(
        self, 
        main_progress: Optional[TranscriptionProgress],
        start_pct: float,
        end_pct: float
    ) -> Optional[Callable[[float, str], None]]:
        """Cria callback de progresso para chunk processing."""
        if not main_progress:
            return None
        
        def chunk_progress(progress_pct: float, status: str):
            adjusted_progress = start_pct + (progress_pct * (end_pct - start_pct))
            main_progress.update(adjusted_progress, status)
        
        return chunk_progress
    
    def _transcribe_chunks_parallel(
        self,
        chunks: List[AudioChunk],
        language: Optional[str],
        progress: Optional[TranscriptionProgress],
        start_pct: float,
        end_pct: float
    ) -> List[TranscriptionResult]:
        """Transcreve chunks em paralelo."""
        results = [None] * len(chunks)
        progress_step = (end_pct - start_pct) / len(chunks)
        completed = 0
        
        with ThreadPoolExecutor(max_workers=self.config.max_parallel_workers) as executor:
            # Submeter tarefas
            future_to_index = {}
            
            for i, chunk in enumerate(chunks):
                future = executor.submit(self._transcribe_single_chunk, chunk, language, i)
                future_to_index[future] = i
            
            # Coletar resultados
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                
                try:
                    result = future.result()
                    results[index] = result
                    completed += 1
                    
                    if progress:
                        current_progress = start_pct + (completed * progress_step)
                        progress.update(current_progress, f"Chunk {completed}/{len(chunks)} transcrito")
                        
                except Exception as e:
                    logger.error(f"Erro ao transcrever chunk {index}: {e}")
                    # Criar resultado vazio para não quebrar a sequência
                    results[index] = TranscriptionResult()
        
        # Filtrar resultados None
        return [r for r in results if r is not None]
    
    def _transcribe_chunks_sequential(
        self,
        chunks: List[AudioChunk],
        language: Optional[str],
        progress: Optional[TranscriptionProgress],
        start_pct: float,
        end_pct: float
    ) -> List[TranscriptionResult]:
        """Transcreve chunks sequencialmente."""
        results = []
        progress_step = (end_pct - start_pct) / len(chunks)
        
        for i, chunk in enumerate(chunks):
            try:
                result = self._transcribe_single_chunk(chunk, language, i)
                results.append(result)
                
                if progress:
                    current_progress = start_pct + ((i + 1) * progress_step)
                    progress.update(current_progress, f"Chunk {i + 1}/{len(chunks)} transcrito")
                    
            except Exception as e:
                logger.error(f"Erro ao transcrever chunk {i}: {e}")
                # Continuar com próximo chunk
                continue
        
        return results
    
    def _transcribe_single_chunk(
        self, 
        chunk: AudioChunk, 
        language: Optional[str],
        chunk_index: int
    ) -> TranscriptionResult:
        """Transcreve um único chunk."""
        try:
            # Criar arquivo temporário para o chunk
            temp_dir = Path(tempfile.gettempdir()) / "meetingscribe_chunks"
            temp_dir.mkdir(exist_ok=True)
            
            temp_file = temp_dir / f"chunk_{chunk_index}_{chunk.chunk_id}.wav"
            
            # Salvar chunk como arquivo
            self.chunk_processor.get_chunk_as_file(chunk, temp_file)
            self._temp_files.append(temp_file)
            
            # Criar transcriber para este chunk (clone do principal)
            chunk_transcriber = WhisperTranscriber(self.config.transcription_config)
            
            # Compartilhar modelo carregado se possível
            if hasattr(self._transcriber, '_model') and self._transcriber._model:
                chunk_transcriber._model = self._transcriber._model
                chunk_transcriber._model_loaded = True
            
            # Transcrever
            result = chunk_transcriber.transcribe_file(temp_file, None, language)
            
            # Ajustar timestamps baseado no offset do chunk
            for segment in result.segments:
                segment.start += chunk.start_time
                segment.end += chunk.start_time
            
            # Limpar modelo do chunk transcriber para não duplicar na memória
            if hasattr(chunk_transcriber, '_model'):
                chunk_transcriber._model = None
                chunk_transcriber._model_loaded = False
            
            logger.debug(f"Chunk {chunk_index} transcrito: {len(result.segments)} segmentos")
            return result
            
        except Exception as e:
            logger.error(f"Erro na transcrição do chunk {chunk_index}: {e}")
            raise
    
    def _consolidate_results(
        self,
        chunk_results: List[TranscriptionResult],
        chunk_processing_result: ChunkProcessingResult,
        start_time: float
    ) -> TranscriptionResult:
        """Consolida resultados dos chunks em resultado final."""
        
        # Combinar todos os segmentos
        all_segments = []
        segment_id = 0
        
        for result in chunk_results:
            for segment in result.segments:
                # Atualizar ID do segmento
                segment.id = segment_id
                all_segments.append(segment)
                segment_id += 1
        
        # Remover sobreposições se configurado
        if self.config.merge_overlapping_segments and len(all_segments) > 1:
            all_segments = self._merge_overlapping_segments(all_segments)
        
        # Calcular estatísticas consolidadas
        total_processing_time = time.time() - start_time
        total_duration = chunk_processing_result.total_duration
        
        # Detectar idioma mais comum
        languages = [segment.language for segment in all_segments if segment.language]
        detected_language = max(set(languages), key=languages.count) if languages else None
        
        # Calcular confiança média
        confidences = [segment.confidence for segment in all_segments if segment.confidence > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Contar palavras
        word_count = sum(len(segment.text.split()) for segment in all_segments)
        
        # Criar resultado consolidado
        consolidated_result = TranscriptionResult(
            segments=all_segments,
            language=detected_language,
            duration=total_duration,
            model_size=self.config.transcription_config.model_size.value,
            processing_time=total_processing_time,
            confidence_avg=avg_confidence,
            word_count=word_count
        )
        
        logger.info(
            f"Resultados consolidados: {len(all_segments)} segmentos, "
            f"{word_count} palavras, {total_duration:.1f}s de áudio"
        )
        
        return consolidated_result
    
    def _merge_overlapping_segments(self, segments: List[TranscriptionSegment]) -> List[TranscriptionSegment]:
        """Remove sobreposições entre segmentos de chunks diferentes."""
        if len(segments) <= 1:
            return segments
        
        # Ordenar por tempo de início
        segments.sort(key=lambda s: s.start)
        
        merged = []
        current = segments[0]
        
        for next_segment in segments[1:]:
            # Verificar sobreposição
            if next_segment.start <= current.end:
                # Há sobreposição - mesclar ou escolher melhor
                overlap_duration = current.end - next_segment.start
                
                # Se sobreposição é pequena (<1s), mesclar
                if overlap_duration < 1.0:
                    # Ajustar final do atual para início do próximo
                    current.end = next_segment.start
                    merged.append(current)
                    current = next_segment
                else:
                    # Sobreposição grande - escolher segmento com melhor confiança
                    if next_segment.confidence > current.confidence:
                        current = next_segment
                    # Senão, manter o atual e pular o próximo
            else:
                # Sem sobreposição
                merged.append(current)
                current = next_segment
        
        # Adicionar último segmento
        merged.append(current)
        
        # Reajustar IDs
        for i, segment in enumerate(merged):
            segment.id = i
        
        logger.debug(f"Segmentos mesclados: {len(segments)} -> {len(merged)}")
        return merged
    
    def _cleanup_temp_files(self):
        """Limpa arquivos temporários criados."""
        if not self.config.cleanup_intermediate_files:
            return
        
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Arquivo temporário removido: {temp_file}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário {temp_file}: {e}")
        
        self._temp_files.clear()
    
    def cleanup(self):
        """Limpa recursos do transcritor."""
        self._cleanup_temp_files()
        
        if self._transcriber:
            self._transcriber.cleanup()
        
        if self.chunk_processor:
            # Limpar chunks se houver
            pass
        
        logger.info("Transcritor chunked limpo")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


# Manter compatibilidade com API existente
class ChunkedTranscriber(ChunkedWhisperTranscriber):
    """Alias para compatibilidade com código existente."""
    
    def __init__(self, chunk_duration: int = 300, overlap: int = 5):
        """
        Args:
            chunk_duration: Duração de cada chunk em segundos (5 min padrão)
            overlap: Sobreposição entre chunks em segundos
        """
        # Converter para nova API
        config = ChunkedTranscriptionConfig(
            transcription_config=TranscriptionConfig(),
            chunk_duration=float(chunk_duration),
            overlap_duration=float(overlap),
            parallel_chunks=False  # Manter compatibilidade
        )
        super().__init__(config)
    
    def transcribe_chunked(self, audio_path: Path, model_size: WhisperModelSize = WhisperModelSize.SMALL, quality_mode: bool = True) -> TranscriptionResult:
        """Método para compatibilidade."""
        # Atualizar configuração
        self.config.transcription_config.model_size = model_size
        self.config.transcription_config.quality_mode = quality_mode
        
        return self.transcribe_file(audio_path)


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_chunked_transcriber(
    model_size: WhisperModelSize = WhisperModelSize.BASE,
    language: Optional[str] = None,
    use_gpu: bool = False,
    chunk_strategy: ChunkStrategy = ChunkStrategy.ADAPTIVE,
    chunk_duration: float = 30.0,
    parallel_chunks: bool = True
) -> ChunkedWhisperTranscriber:
    """
    Cria transcritor chunked otimizado.
    
    Args:
        model_size: Tamanho do modelo Whisper
        language: Idioma específico
        use_gpu: Usar GPU se disponível
        chunk_strategy: Estratégia de divisão em chunks
        chunk_duration: Duração base dos chunks
        parallel_chunks: Processar chunks em paralelo
        
    Returns:
        ChunkedWhisperTranscriber configurado
    """
    
    # Configuração do transcriber base
    transcription_config = TranscriptionConfig(
        model_size=model_size,
        language=language,
        device="auto" if use_gpu else "cpu",
        compute_type="float16" if use_gpu else "int8"
    )
    
    # Configuração do chunked transcriber
    chunked_config = ChunkedTranscriptionConfig(
        transcription_config=transcription_config,
        chunk_strategy=chunk_strategy,
        chunk_duration=chunk_duration,
        parallel_chunks=parallel_chunks,
        max_parallel_workers=2 if parallel_chunks else 1
    )
    
    return ChunkedWhisperTranscriber(chunked_config)


def transcribe_with_chunks(
    audio_path: Path,
    model_size: WhisperModelSize = WhisperModelSize.BASE,
    language: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    chunk_strategy: ChunkStrategy = ChunkStrategy.ADAPTIVE
) -> TranscriptionResult:
    """
    Função de conveniência para transcrição com chunks.
    
    Args:
        audio_path: Caminho para arquivo de áudio
        model_size: Tamanho do modelo
        language: Idioma específico
        progress_callback: Callback de progresso
        chunk_strategy: Estratégia de chunks
        
    Returns:
        TranscriptionResult
    """
    progress = TranscriptionProgress(progress_callback) if progress_callback else None
    
    with create_chunked_transcriber(
        model_size=model_size,
        language=language,
        chunk_strategy=chunk_strategy
    ) as transcriber:
        return transcriber.transcribe_file(audio_path, progress, language)


def transcribe_large_file(audio_path: Path, model_size: WhisperModelSize = WhisperModelSize.SMALL, chunk_duration: int = 300) -> Path:
    """
    Transcreve arquivo grande dividindo em chunks e salva automaticamente.
    
    Args:
        audio_path: Caminho do arquivo de áudio
        model_size: Modelo Whisper a usar (tiny, small, medium, large-v3)
        chunk_duration: Duração de cada chunk em segundos
        
    Returns:
        Caminho do arquivo de transcrição salvo
    """
    from datetime import datetime
    from config import settings
    from .exporter import save_transcription_txt
    
    with ChunkedTranscriber(chunk_duration=chunk_duration) as chunked:
        result = chunked.transcribe_chunked(audio_path, model_size)
        
        # Salvar resultado
        audio_name = audio_path.stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = settings.transcriptions_dir / f"{audio_name}_chunked_{model_size.value}_{timestamp}.txt"
        
        saved_path = save_transcription_txt(result, output_path)
        logger.success(f"Transcrição salva: {saved_path}")
        
        return saved_path


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ChunkedWhisperTranscriber",
    "ChunkedTranscriptionConfig",
    "ChunkedTranscriber",  # Compatibilidade
    "create_chunked_transcriber",
    "transcribe_with_chunks",
    "transcribe_large_file"
]