"""
Domain Services para MeetingScribe

Implementa a camada de domínio com lógica de negócio avançada.
Integra com todos os componentes existentes mantendo compatibilidade total.

Services implementados:
- AudioProcessingService: Validação e estratégias de processamento de áudio
- TranscriptionQualityService: Controle de qualidade e métricas avançadas
- WorkflowOrchestrationService: Orquestração de workflows end-to-end

Author: MeetingScribe Team
Version: 1.1.0
Python: >=3.8
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from loguru import logger
from pydantic import BaseModel, Field, validator

# Importações internas
from config import settings
from src.models.domain import (
    AudioFile, AudioDevice, RecordingSession, RecordingConfiguration,
    TranscriptionResult, TranscriptionSegment, WhisperModelSize,
    AudioFormat, RecordingStatus, TranscriptionStatus, DeviceType
)

# Importações condicionais para evitar erros
try:
    from src.core.hardware_detection import SystemSpecs, detect_hardware
    HARDWARE_DETECTION_AVAILABLE = True
except ImportError:
    HARDWARE_DETECTION_AVAILABLE = False
    logger.debug("Hardware detection não disponível - usando fallbacks")


# =============================================================================
# ENUMS E TIPOS DE APOIO
# =============================================================================

class ProcessingStrategy(str, Enum):
    """Estratégias de processamento de áudio."""
    FAST = "fast"              # Processamento rápido com menor qualidade
    BALANCED = "balanced"      # Equilibrio entre velocidade e qualidade
    QUALITY = "quality"        # Máxima qualidade, menor velocidade
    ADAPTIVE = "adaptive"      # Adaptativo baseado no hardware


class QualityLevel(str, Enum):
    """Níveis de qualidade de transcrição."""
    POOR = "poor"           # 0-40%
    FAIR = "fair"           # 40-60%
    GOOD = "good"           # 60-80%
    EXCELLENT = "excellent" # 80%+


class WorkflowStatus(str, Enum):
    """Status de workflow de processamento."""
    CREATED = "created"
    VALIDATING = "validating"
    PREPROCESSING = "preprocessing"
    TRANSCRIBING = "transcribing"
    POST_PROCESSING = "post_processing"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProcessingRecommendation:
    """Recomendação de processamento de áudio."""
    strategy: ProcessingStrategy
    whisper_model: WhisperModelSize
    device: str
    expected_duration_minutes: float
    confidence_level: float
    quality_score: float
    reasoning: str


@dataclass
class QualityAssessment:
    """Avaliação de qualidade de transcrição."""
    overall_level: QualityLevel
    confidence_score: float
    accuracy_estimate: float
    issues_detected: List[str]
    suggestions: List[str]
    metrics: Dict[str, float]


@dataclass
class WorkflowStep:
    """Passo individual de workflow."""
    name: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: float
    success: bool
    error_message: Optional[str]
    metadata: Dict[str, Any]


# =============================================================================
# SERVIÇO DE PROCESSAMENTO DE ÁUDIO
# =============================================================================

class AudioProcessingService:
    """
    Serviço de domínio para processamento inteligente de áudio.
    
    Responsabilidades:
    - Validação avançada de arquivos de áudio
    - Recomendações de estratégia de processamento
    - Otimização baseada no hardware disponível
    - Estimativas de tempo e qualidade
    """
    
    def __init__(self):
        """Inicializa o serviço com detecção de hardware."""
        self.system_specs = None
        if HARDWARE_DETECTION_AVAILABLE:
            try:
                self.system_specs = detect_hardware()
                logger.info(f"Hardware detectado: {self.system_specs.overall_performance_level.value}")
            except Exception as e:
                logger.warning(f"Erro na detecção de hardware: {e}")
        
        # Cache de validações
        self._validation_cache: Dict[str, bool] = {}
        self._recommendation_cache: Dict[str, ProcessingRecommendation] = {}
    
    def validate_audio_file(self, audio_file: AudioFile) -> Tuple[bool, List[str]]:
        """
        Valida arquivo de áudio para processamento.
        
        Args:
            audio_file: Arquivo de áudio a ser validado
            
        Returns:
            Tuple[bool, List[str]]: (válido, lista de problemas)
        """
        cache_key = f"{audio_file.path}_{audio_file.size_bytes}"
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key], []
        
        issues = []
        
        try:
            # Validação básica de existência
            if not audio_file.path.exists():
                issues.append("Arquivo não encontrado")
                return False, issues
            
            # Validação de tamanho
            if audio_file.size_mb > 500:  # 500MB limit
                issues.append("Arquivo muito grande (>500MB)")
            elif audio_file.size_mb < 0.01:  # 10KB minimum
                issues.append("Arquivo muito pequeno (<10KB)")
            
            # Validação de duração
            if audio_file.duration_seconds < 1:
                issues.append("Duração muito curta (<1 segundo)")
            elif audio_file.duration_seconds > 10800:  # 3 horas
                issues.append("Duração muito longa (>3 horas)")
            
            # Validação de sample rate
            if audio_file.sample_rate < 8000:
                issues.append("Sample rate muito baixo (<8kHz)")
            elif audio_file.sample_rate > 48000:
                issues.append("Sample rate desnecessariamente alto (>48kHz)")
            
            # Validação de formato
            supported_formats = {AudioFormat.WAV, AudioFormat.MP3, AudioFormat.M4A}
            if audio_file.audio_format not in supported_formats:
                issues.append(f"Formato não suportado: {audio_file.audio_format}")
            
            # Validação de qualidade de áudio
            if audio_file.peak_amplitude < 0.1:
                issues.append("Sinal de áudio muito baixo")
            elif audio_file.peak_amplitude > 0.95:
                issues.append("Possível clipping de áudio")
            
            # Validação SNR se disponível
            if audio_file.signal_to_noise_ratio is not None:
                if audio_file.signal_to_noise_ratio < 10:
                    issues.append("Relação sinal/ruído muito baixa")
            
            is_valid = len(issues) == 0
            self._validation_cache[cache_key] = is_valid
            
            logger.debug(f"Validação de áudio: {is_valid}, problemas: {len(issues)}")
            return is_valid, issues
            
        except Exception as e:
            logger.error(f"Erro na validação de áudio: {e}")
            issues.append(f"Erro interno na validação: {str(e)}")
            return False, issues
    
    def recommend_processing_strategy(self, audio_file: AudioFile) -> ProcessingRecommendation:
        """
        Recomenda estratégia de processamento baseada no arquivo e hardware.
        
        Args:
            audio_file: Arquivo de áudio para análise
            
        Returns:
            ProcessingRecommendation: Recomendação completa
        """
        cache_key = f"{audio_file.path}_{audio_file.duration_seconds}_{audio_file.size_mb}"
        if cache_key in self._recommendation_cache:
            return self._recommendation_cache[cache_key]
        
        try:
            # Análise das características do arquivo
            duration_minutes = audio_file.duration_seconds / 60
            file_complexity = self._assess_file_complexity(audio_file)
            
            # Determinar estratégia baseada no hardware e arquivo
            strategy = self._determine_strategy(audio_file, file_complexity)
            
            # Selecionar modelo Whisper apropriado
            whisper_model = self._select_whisper_model(strategy, file_complexity)
            
            # Determinar dispositivo de processamento
            device = self._select_processing_device(strategy)
            
            # Estimar tempo de processamento
            expected_duration = self._estimate_processing_time(
                duration_minutes, whisper_model, device
            )
            
            # Calcular confiança e qualidade esperadas
            confidence_level = self._estimate_confidence(audio_file, whisper_model)
            quality_score = self._estimate_quality_score(strategy, whisper_model, file_complexity)
            
            # Gerar explicação
            reasoning = self._generate_reasoning(
                strategy, whisper_model, device, file_complexity
            )
            
            recommendation = ProcessingRecommendation(
                strategy=strategy,
                whisper_model=whisper_model,
                device=device,
                expected_duration_minutes=expected_duration,
                confidence_level=confidence_level,
                quality_score=quality_score,
                reasoning=reasoning
            )
            
            self._recommendation_cache[cache_key] = recommendation
            logger.info(f"Estratégia recomendada: {strategy.value}, modelo: {whisper_model.value}")
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Erro na recomendação de estratégia: {e}")
            # Fallback seguro
            return ProcessingRecommendation(
                strategy=ProcessingStrategy.BALANCED,
                whisper_model=WhisperModelSize.BASE,
                device="cpu",
                expected_duration_minutes=duration_minutes * 0.5,
                confidence_level=0.7,
                quality_score=0.6,
                reasoning="Estratégia padrão devido a erro na análise"
            )
    
    def _assess_file_complexity(self, audio_file: AudioFile) -> float:
        """Avalia complexidade do arquivo (0.0 - 1.0)."""
        complexity = 0.0
        
        # Duração (arquivos mais longos são mais complexos)
        duration_factor = min(audio_file.duration_seconds / 3600, 1.0)  # Normalizar para 1h
        complexity += duration_factor * 0.3
        
        # Sample rate (maior = mais complexo)
        rate_factor = min(audio_file.sample_rate / 48000, 1.0)
        complexity += rate_factor * 0.2
        
        # Canais (estéreo = mais complexo)
        channel_factor = min(audio_file.channels / 2, 1.0)
        complexity += channel_factor * 0.1
        
        # Qualidade do sinal
        if audio_file.signal_to_noise_ratio:
            # SNR baixo = mais complexo
            snr_factor = max(0, 1.0 - (audio_file.signal_to_noise_ratio / 30))
            complexity += snr_factor * 0.2
        
        # Amplitude (muito baixa ou alta = mais complexo)
        amp_deviation = abs(audio_file.peak_amplitude - 0.7)  # Ideal ~0.7
        complexity += min(amp_deviation, 0.3) * 0.2
        
        return min(complexity, 1.0)
    
    def _determine_strategy(self, audio_file: AudioFile, complexity: float) -> ProcessingStrategy:
        """Determina estratégia baseada no hardware e complexidade."""
        if not self.system_specs:
            return ProcessingStrategy.BALANCED
        
        perf_level = self.system_specs.overall_performance_level.value
        duration_hours = audio_file.duration_seconds / 3600
        
        # Lógica de decisão estratégica
        if perf_level == "extreme":
            if complexity > 0.7 or duration_hours > 2:
                return ProcessingStrategy.QUALITY
            else:
                return ProcessingStrategy.ADAPTIVE
        elif perf_level == "high":
            if complexity > 0.8:
                return ProcessingStrategy.BALANCED
            else:
                return ProcessingStrategy.ADAPTIVE
        elif perf_level == "medium":
            if duration_hours > 1:
                return ProcessingStrategy.FAST
            else:
                return ProcessingStrategy.BALANCED
        else:  # low
            return ProcessingStrategy.FAST
    
    def _select_whisper_model(self, strategy: ProcessingStrategy, complexity: float) -> WhisperModelSize:
        """Seleciona modelo Whisper baseado na estratégia."""
        if self.system_specs:
            # Usar recomendação do hardware como base
            recommended = WhisperModelSize(self.system_specs.recommended_whisper_model)
        else:
            recommended = WhisperModelSize.BASE
        
        # Ajustar baseado na estratégia
        model_mapping = {
            ProcessingStrategy.FAST: {
                WhisperModelSize.LARGE_V3: WhisperModelSize.MEDIUM,
                WhisperModelSize.MEDIUM: WhisperModelSize.SMALL,
                WhisperModelSize.SMALL: WhisperModelSize.BASE,
                WhisperModelSize.BASE: WhisperModelSize.TINY,
                WhisperModelSize.TINY: WhisperModelSize.TINY
            },
            ProcessingStrategy.QUALITY: {
                WhisperModelSize.TINY: WhisperModelSize.BASE,
                WhisperModelSize.BASE: WhisperModelSize.SMALL,
                WhisperModelSize.SMALL: WhisperModelSize.MEDIUM,
                WhisperModelSize.MEDIUM: WhisperModelSize.LARGE_V3,
                WhisperModelSize.LARGE_V3: WhisperModelSize.LARGE_V3
            }
        }
        
        if strategy in model_mapping:
            return model_mapping[strategy].get(recommended, recommended)
        
        return recommended
    
    def _select_processing_device(self, strategy: ProcessingStrategy) -> str:
        """Seleciona dispositivo de processamento."""
        if not self.system_specs:
            return "cpu"
        
        recommended_device = self.system_specs.recommended_device
        
        # Para estratégia FAST, sempre preferir CPU se GPU não for muito superior
        if strategy == ProcessingStrategy.FAST and recommended_device == "cuda":
            if (self.system_specs.gpu and 
                self.system_specs.gpu.performance_score < 80):
                return "cpu"
        
        return recommended_device
    
    def _estimate_processing_time(self, duration_minutes: float, 
                                model: WhisperModelSize, device: str) -> float:
        """Estima tempo de processamento em minutos."""
        # Fatores base por modelo
        model_factors = {
            WhisperModelSize.TINY: 0.1,
            WhisperModelSize.BASE: 0.2,
            WhisperModelSize.SMALL: 0.3,
            WhisperModelSize.MEDIUM: 0.5,
            WhisperModelSize.LARGE_V3: 0.8
        }
        
        base_factor = model_factors.get(model, 0.3)
        
        # Ajustar por dispositivo
        if device == "cuda" and self.system_specs and self.system_specs.gpu:
            gpu_factor = max(0.3, 1.0 - (self.system_specs.gpu.performance_score / 100))
            base_factor *= gpu_factor
        elif device == "cpu" and self.system_specs:
            cpu_factor = max(0.5, 1.0 - (self.system_specs.cpu.performance_score / 100))
            base_factor *= cpu_factor
        
        estimated_time = duration_minutes * base_factor
        
        # Adicionar overhead
        overhead = min(2.0, duration_minutes * 0.1)  # Max 2 min overhead
        
        return estimated_time + overhead
    
    def _estimate_confidence(self, audio_file: AudioFile, model: WhisperModelSize) -> float:
        """Estima nível de confiança da transcrição."""
        base_confidence = 0.7
        
        # Ajustar por qualidade do modelo
        model_bonus = {
            WhisperModelSize.TINY: 0.0,
            WhisperModelSize.BASE: 0.05,
            WhisperModelSize.SMALL: 0.1,
            WhisperModelSize.MEDIUM: 0.15,
            WhisperModelSize.LARGE_V3: 0.2
        }.get(model, 0.1)
        
        # Ajustar por qualidade do áudio
        if audio_file.peak_amplitude > 0.3:
            audio_bonus = 0.1
        else:
            audio_bonus = -0.1
        
        # Ajustar por SNR se disponível
        snr_bonus = 0.0
        if audio_file.signal_to_noise_ratio:
            if audio_file.signal_to_noise_ratio > 20:
                snr_bonus = 0.1
            elif audio_file.signal_to_noise_ratio < 10:
                snr_bonus = -0.15
        
        confidence = base_confidence + model_bonus + audio_bonus + snr_bonus
        return max(0.3, min(0.95, confidence))
    
    def _estimate_quality_score(self, strategy: ProcessingStrategy, 
                              model: WhisperModelSize, complexity: float) -> float:
        """Estima score de qualidade final."""
        # Score base por estratégia
        strategy_scores = {
            ProcessingStrategy.FAST: 0.6,
            ProcessingStrategy.BALANCED: 0.75,
            ProcessingStrategy.QUALITY: 0.9,
            ProcessingStrategy.ADAPTIVE: 0.8
        }
        
        base_score = strategy_scores[strategy]
        
        # Bonus do modelo
        model_bonus = {
            WhisperModelSize.TINY: -0.1,
            WhisperModelSize.BASE: 0.0,
            WhisperModelSize.SMALL: 0.05,
            WhisperModelSize.MEDIUM: 0.1,
            WhisperModelSize.LARGE_V3: 0.15
        }.get(model, 0.0)
        
        # Penalidade por complexidade
        complexity_penalty = complexity * 0.15
        
        quality = base_score + model_bonus - complexity_penalty
        return max(0.4, min(0.95, quality))
    
    def _generate_reasoning(self, strategy: ProcessingStrategy, model: WhisperModelSize, 
                          device: str, complexity: float) -> str:
        """Gera explicação da recomendação."""
        parts = []
        
        # Estratégia
        strategy_reasons = {
            ProcessingStrategy.FAST: "Prioriza velocidade para processamento rápido",
            ProcessingStrategy.BALANCED: "Equilibra velocidade e qualidade",
            ProcessingStrategy.QUALITY: "Prioriza máxima qualidade de transcrição",
            ProcessingStrategy.ADAPTIVE: "Adapta-se às condições do sistema"
        }
        parts.append(strategy_reasons[strategy])
        
        # Modelo
        if model in [WhisperModelSize.LARGE_V3, WhisperModelSize.MEDIUM]:
            parts.append(f"Modelo {model.value} para alta precisão")
        else:
            parts.append(f"Modelo {model.value} otimizado para o hardware")
        
        # Dispositivo
        if device == "cuda":
            parts.append("GPU CUDA para aceleração")
        else:
            parts.append("CPU para compatibilidade")
        
        # Complexidade
        if complexity > 0.7:
            parts.append("Arquivo complexo requer processamento cuidadoso")
        elif complexity < 0.3:
            parts.append("Arquivo simples permite processamento otimizado")
        
        return ". ".join(parts) + "."


# =============================================================================
# SERVIÇO DE QUALIDADE DE TRANSCRIÇÃO
# =============================================================================

class TranscriptionQualityService:
    """
    Serviço de domínio para controle de qualidade de transcrições.
    
    Responsabilidades:
    - Análise de qualidade pós-transcrição
    - Detecção de problemas comuns
    - Sugestões de melhoria
    - Métricas avançadas de qualidade
    """
    
    def __init__(self):
        """Inicializa o serviço de qualidade."""
        self.quality_thresholds = {
            'confidence_min': 0.6,
            'confidence_avg': 0.75,
            'words_per_minute_min': 60,
            'words_per_minute_max': 300,
            'segment_length_max': 30.0,
            'gap_length_max': 5.0
        }
        
        # Cache de avaliações
        self._assessment_cache: Dict[str, QualityAssessment] = {}
    
    def assess_transcription_quality(self, result: TranscriptionResult) -> QualityAssessment:
        """
        Avalia qualidade completa de uma transcrição.
        
        Args:
            result: Resultado da transcrição para análise
            
        Returns:
            QualityAssessment: Avaliação completa da qualidade
        """
        cache_key = f"{result.audio_file.path}_{len(result.segments)}_{result.confidence_average}"
        if cache_key in self._assessment_cache:
            return self._assessment_cache[cache_key]
        
        try:
            # Análises individuais
            confidence_issues = self._analyze_confidence(result)
            timing_issues = self._analyze_timing(result)
            content_issues = self._analyze_content(result)
            technical_issues = self._analyze_technical_aspects(result)
            
            # Consolidar problemas
            all_issues = confidence_issues + timing_issues + content_issues + technical_issues
            
            # Calcular métricas
            metrics = self._calculate_quality_metrics(result)
            
            # Determinar nível de qualidade geral
            overall_level = self._determine_quality_level(metrics, len(all_issues))
            
            # Gerar sugestões
            suggestions = self._generate_suggestions(all_issues, metrics, result)
            
            # Calcular scores finais
            confidence_score = self._calculate_confidence_score(result, metrics)
            accuracy_estimate = self._estimate_accuracy(result, metrics, len(all_issues))
            
            assessment = QualityAssessment(
                overall_level=overall_level,
                confidence_score=confidence_score,
                accuracy_estimate=accuracy_estimate,
                issues_detected=all_issues,
                suggestions=suggestions,
                metrics=metrics
            )
            
            self._assessment_cache[cache_key] = assessment
            logger.info(f"Qualidade avaliada: {overall_level.value}, confiança: {confidence_score:.2f}")
            
            return assessment
            
        except Exception as e:
            logger.error(f"Erro na avaliação de qualidade: {e}")
            # Fallback básico
            return QualityAssessment(
                overall_level=QualityLevel.FAIR,
                confidence_score=result.confidence_average,
                accuracy_estimate=0.7,
                issues_detected=[f"Erro na análise: {str(e)}"],
                suggestions=["Tente novamente a transcrição"],
                metrics={}
            )
    
    def _analyze_confidence(self, result: TranscriptionResult) -> List[str]:
        """Analisa problemas relacionados à confiança."""
        issues = []
        
        if result.confidence_average < self.quality_thresholds['confidence_avg']:
            issues.append(f"Confiança média baixa: {result.confidence_average:.2f}")
        
        if result.confidence_minimum < self.quality_thresholds['confidence_min']:
            issues.append(f"Confiança mínima muito baixa: {result.confidence_minimum:.2f}")
        
        # Analisar variação de confiança
        if result.segments:
            confidences = [seg.confidence for seg in result.segments]
            confidence_std = self._calculate_std(confidences)
            if confidence_std > 0.25:
                issues.append("Grande variação na confiança entre segmentos")
        
        return issues
    
    def _analyze_timing(self, result: TranscriptionResult) -> List[str]:
        """Analisa problemas de timing."""
        issues = []
        
        if not result.segments:
            return issues
        
        # Verificar segmentos muito longos
        long_segments = [seg for seg in result.segments 
                        if seg.duration_seconds > self.quality_thresholds['segment_length_max']]
        if long_segments:
            issues.append(f"{len(long_segments)} segmentos muito longos (>{self.quality_thresholds['segment_length_max']}s)")
        
        # Verificar gaps muito grandes
        gaps = []
        for i in range(len(result.segments) - 1):
            gap = result.segments[i + 1].start_time - result.segments[i].end_time
            if gap > self.quality_thresholds['gap_length_max']:
                gaps.append(gap)
        
        if gaps:
            issues.append(f"{len(gaps)} gaps grandes entre segmentos (max: {max(gaps):.1f}s)")
        
        # Verificar sobreposições
        overlaps = []
        for i in range(len(result.segments) - 1):
            if result.segments[i].end_time > result.segments[i + 1].start_time:
                overlaps.append(i)
        
        if overlaps:
            issues.append(f"{len(overlaps)} sobreposições entre segmentos")
        
        return issues
    
    def _analyze_content(self, result: TranscriptionResult) -> List[str]:
        """Analisa problemas de conteúdo."""
        issues = []
        
        # Verificar palavras por minuto
        if result.words_per_minute < self.quality_thresholds['words_per_minute_min']:
            issues.append(f"Ritmo muito lento: {result.words_per_minute:.0f} PPM")
        elif result.words_per_minute > self.quality_thresholds['words_per_minute_max']:
            issues.append(f"Ritmo muito rápido: {result.words_per_minute:.0f} PPM")
        
        # Verificar texto vazio ou muito curto
        if result.word_count < 5:
            issues.append("Texto muito curto ou vazio")
        
        # Detectar possíveis problemas no texto
        text_lower = result.full_text.lower()
        
        # Repetições excessivas
        words = text_lower.split()
        if len(words) > 10:
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            most_frequent = max(word_freq.values())
            if most_frequent > len(words) * 0.3:
                issues.append("Muitas repetições de palavras")
        
        # Caracteres estranhos ou não-textuais
        strange_chars = sum(1 for char in result.full_text if not (char.isalnum() or char.isspace() or char in '.,!?;:-()[]"\''))
        if strange_chars > len(result.full_text) * 0.05:
            issues.append("Muitos caracteres não-textuais")
        
        return issues
    
    def _analyze_technical_aspects(self, result: TranscriptionResult) -> List[str]:
        """Analisa aspectos técnicos."""
        issues = []
        
        # Verificar tempo de processamento
        if result.processing_speed_ratio < 0.1:
            issues.append("Processamento muito lento")
        elif result.processing_speed_ratio > 10:
            issues.append("Processamento suspeito de rápido")
        
        # Verificar consistência de idioma
        if result.language != settings.whisper_language and settings.whisper_language != "auto":
            issues.append(f"Idioma detectado ({result.language}) difere do configurado")
        
        # Verificar uso de speaker detection
        if len(result.speakers_detected) > 1 and not any(seg.speaker_id for seg in result.segments):
            issues.append("Múltiplos speakers detectados mas segmentos não atribuídos")
        
        return issues
    
    def _calculate_quality_metrics(self, result: TranscriptionResult) -> Dict[str, float]:
        """Calcula métricas detalhadas de qualidade."""
        metrics = {}
        
        # Métricas básicas
        metrics['confidence_average'] = result.confidence_average
        metrics['confidence_minimum'] = result.confidence_minimum
        metrics['words_per_minute'] = result.words_per_minute
        metrics['processing_speed_ratio'] = result.processing_speed_ratio
        
        if result.segments:
            # Métricas de timing
            durations = [seg.duration_seconds for seg in result.segments]
            metrics['segment_duration_avg'] = sum(durations) / len(durations)
            metrics['segment_duration_std'] = self._calculate_std(durations)
            
            # Métricas de confiança
            confidences = [seg.confidence for seg in result.segments]
            metrics['confidence_std'] = self._calculate_std(confidences)
            
            # Densidade de palavras
            word_counts = [len(seg.text.split()) for seg in result.segments]
            metrics['words_per_segment_avg'] = sum(word_counts) / len(word_counts)
            
            # Distribuição de confiança
            high_conf_segments = sum(1 for c in confidences if c > 0.8)
            metrics['high_confidence_ratio'] = high_conf_segments / len(confidences)
            
            low_conf_segments = sum(1 for c in confidences if c < 0.6)
            metrics['low_confidence_ratio'] = low_conf_segments / len(confidences)
        
        # Métricas de arquivo
        if result.audio_file:
            metrics['audio_duration_minutes'] = result.audio_file.duration_seconds / 60
            metrics['compression_ratio'] = result.total_duration / result.audio_file.duration_seconds
        
        return metrics
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calcula desvio padrão."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _determine_quality_level(self, metrics: Dict[str, float], issue_count: int) -> QualityLevel:
        """Determina nível geral de qualidade."""
        # Score baseado em métricas
        confidence_score = metrics.get('confidence_average', 0.5) * 40
        
        # Penalidade por problemas
        issue_penalty = min(issue_count * 10, 30)
        
        # Bonus por alta confiança consistente
        high_conf_ratio = metrics.get('high_confidence_ratio', 0.0)
        consistency_bonus = high_conf_ratio * 20
        
        # Score final
        total_score = confidence_score + consistency_bonus - issue_penalty
        
        if total_score >= 80:
            return QualityLevel.EXCELLENT
        elif total_score >= 60:
            return QualityLevel.GOOD
        elif total_score >= 40:
            return QualityLevel.FAIR
        else:
            return QualityLevel.POOR
    
    def _calculate_confidence_score(self, result: TranscriptionResult, metrics: Dict[str, float]) -> float:
        """Calcula score de confiança ajustado."""
        base_confidence = result.confidence_average
        
        # Ajustar por consistência
        confidence_std = metrics.get('confidence_std', 0.0)
        consistency_factor = max(0.8, 1.0 - confidence_std)
        
        # Ajustar por qualidade técnica
        speed_ratio = metrics.get('processing_speed_ratio', 1.0)
        if 0.5 <= speed_ratio <= 5.0:  # Range normal
            technical_factor = 1.0
        else:
            technical_factor = 0.9
        
        adjusted_confidence = base_confidence * consistency_factor * technical_factor
        return max(0.0, min(1.0, adjusted_confidence))
    
    def _estimate_accuracy(self, result: TranscriptionResult, metrics: Dict[str, float], issue_count: int) -> float:
        """Estima precisão da transcrição."""
        # Base na confiança
        base_accuracy = result.confidence_average * 0.9  # Slightly lower than confidence
        
        # Ajustar por problemas detectados
        issue_factor = max(0.7, 1.0 - (issue_count * 0.05))
        
        # Ajustar por modelo usado
        model_factors = {
            WhisperModelSize.TINY: 0.85,
            WhisperModelSize.BASE: 0.90,
            WhisperModelSize.SMALL: 0.93,
            WhisperModelSize.MEDIUM: 0.96,
            WhisperModelSize.LARGE_V3: 0.98
        }
        model_factor = model_factors.get(result.model_used, 0.90)
        
        estimated_accuracy = base_accuracy * issue_factor * model_factor
        return max(0.3, min(0.95, estimated_accuracy))
    
    def _generate_suggestions(self, issues: List[str], metrics: Dict[str, float], 
                            result: TranscriptionResult) -> List[str]:
        """Gera sugestões de melhoria."""
        suggestions = []
        
        # Sugestões baseadas em problemas específicos
        issue_text = " ".join(issues).lower()
        
        if "confiança" in issue_text:
            if result.model_used in [WhisperModelSize.TINY, WhisperModelSize.BASE]:
                suggestions.append("Considere usar um modelo Whisper maior")
            suggestions.append("Verifique a qualidade do áudio original")
        
        if "timing" in issue_text or "gap" in issue_text:
            suggestions.append("Considere usar configurações de VAD mais sensíveis")
        
        if "ritmo" in issue_text:
            suggestions.append("Verifique se o áudio não está acelerado ou muito lento")
        
        if "repetições" in issue_text:
            suggestions.append("Áudio pode conter loops ou ecos")
        
        if "caracteres não-textuais" in issue_text:
            suggestions.append("Considere pré-processamento de áudio para redução de ruído")
        
        # Sugestões baseadas em métricas
        if metrics.get('confidence_std', 0) > 0.3:
            suggestions.append("Qualidade de áudio varia muito - considere normalização")
        
        if metrics.get('processing_speed_ratio', 1.0) < 0.5:
            suggestions.append("Considere usar modelo menor ou hardware mais potente")
        
        # Sugestões gerais se não há problemas específicos
        if not suggestions and len(issues) > 0:
            suggestions.append("Considere melhorar a qualidade do áudio de entrada")
            suggestions.append("Experimente diferentes configurações de processamento")
        
        return suggestions[:5]  # Limitar a 5 sugestões


# =============================================================================
# SERVIÇO DE ORQUESTRAÇÃO DE WORKFLOW
# =============================================================================

class WorkflowOrchestrationService:
    """
    Serviço de domínio para orquestração de workflows complexos.
    
    Responsabilidades:
    - Coordenação de workflows end-to-end
    - Gestão de estado de processamento
    - Recuperação de erros e retry logic
    - Monitoramento de progresso
    """
    
    def __init__(self):
        """Inicializa o serviço de orquestração."""
        self.audio_service = AudioProcessingService()
        self.quality_service = TranscriptionQualityService()
        
        # Estado de workflows ativos
        self._active_workflows: Dict[str, Dict[str, Any]] = {}
        self._workflow_history: List[Dict[str, Any]] = []
        
        # Configurações de retry
        self.retry_config = {
            'max_retries': 3,
            'retry_delay_seconds': 5,
            'backoff_multiplier': 2
        }
    
    async def execute_complete_workflow(self, audio_file: AudioFile, 
                                      custom_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executa workflow completo de processamento.
        
        Args:
            audio_file: Arquivo de áudio para processar
            custom_config: Configurações customizadas opcionais
            
        Returns:
            Dict com resultado completo do workflow
        """
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{audio_file.path.stem}"
        
        # Inicializar workflow
        workflow_state = {
            'id': workflow_id,
            'audio_file': audio_file,
            'status': WorkflowStatus.CREATED,
            'steps': [],
            'start_time': datetime.now(),
            'end_time': None,
            'custom_config': custom_config or {},
            'results': {},
            'errors': []
        }
        
        self._active_workflows[workflow_id] = workflow_state
        
        try:
            logger.info(f"Iniciando workflow completo: {workflow_id}")
            
            # Passo 1: Validação
            await self._execute_step(workflow_state, "validation", self._step_validation)
            
            # Passo 2: Análise e recomendação
            await self._execute_step(workflow_state, "analysis", self._step_analysis)
            
            # Passo 3: Pré-processamento
            await self._execute_step(workflow_state, "preprocessing", self._step_preprocessing)
            
            # Passo 4: Transcrição (simulada - integração com transcriber real)
            await self._execute_step(workflow_state, "transcription", self._step_transcription)
            
            # Passo 5: Análise de qualidade
            await self._execute_step(workflow_state, "quality_analysis", self._step_quality_analysis)
            
            # Passo 6: Pós-processamento
            await self._execute_step(workflow_state, "post_processing", self._step_post_processing)
            
            # Finalizar workflow
            workflow_state['status'] = WorkflowStatus.COMPLETED
            workflow_state['end_time'] = datetime.now()
            
            logger.success(f"Workflow completado com sucesso: {workflow_id}")
            
            # Mover para histórico
            self._workflow_history.append(workflow_state.copy())
            del self._active_workflows[workflow_id]
            
            return {
                'workflow_id': workflow_id,
                'status': 'completed',
                'duration_seconds': (workflow_state['end_time'] - workflow_state['start_time']).total_seconds(),
                'steps_completed': len(workflow_state['steps']),
                'results': workflow_state['results']
            }
            
        except Exception as e:
            logger.error(f"Erro no workflow {workflow_id}: {e}")
            workflow_state['status'] = WorkflowStatus.FAILED
            workflow_state['end_time'] = datetime.now()
            workflow_state['errors'].append(str(e))
            
            # Mover para histórico mesmo com erro
            self._workflow_history.append(workflow_state.copy())
            if workflow_id in self._active_workflows:
                del self._active_workflows[workflow_id]
            
            return {
                'workflow_id': workflow_id,
                'status': 'failed',
                'error': str(e),
                'steps_completed': len(workflow_state['steps']),
                'results': workflow_state.get('results', {})
            }
    
    async def _execute_step(self, workflow_state: Dict[str, Any], step_name: str, 
                           step_function) -> None:
        """Executa um passo individual do workflow."""
        step = WorkflowStep(
            name=step_name,
            status="starting",
            start_time=datetime.now(),
            end_time=None,
            duration_seconds=0.0,
            success=False,
            error_message=None,
            metadata={}
        )
        
        workflow_state['steps'].append(step)
        workflow_state['status'] = getattr(WorkflowStatus, step_name.upper(), WorkflowStatus.CREATED)
        
        retries = 0
        while retries <= self.retry_config['max_retries']:
            try:
                logger.info(f"Executando passo: {step_name} (tentativa {retries + 1})")
                
                # Executar função do passo
                step_result = await step_function(workflow_state)
                
                # Sucesso
                step.end_time = datetime.now()
                step.duration_seconds = (step.end_time - step.start_time).total_seconds()
                step.success = True
                step.status = "completed"
                step.metadata = step_result or {}
                
                logger.success(f"Passo {step_name} completado em {step.duration_seconds:.2f}s")
                break
                
            except Exception as e:
                retries += 1
                step.error_message = str(e)
                
                if retries > self.retry_config['max_retries']:
                    # Falha final
                    step.end_time = datetime.now()
                    step.duration_seconds = (step.end_time - step.start_time).total_seconds()
                    step.status = "failed"
                    
                    logger.error(f"Passo {step_name} falhou após {retries} tentativas: {e}")
                    raise
                else:
                    # Retry
                    delay = self.retry_config['retry_delay_seconds'] * (self.retry_config['backoff_multiplier'] ** (retries - 1))
                    logger.warning(f"Passo {step_name} falhou, tentando novamente em {delay}s: {e}")
                    await asyncio.sleep(delay)
    
    async def _step_validation(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Passo de validação do arquivo."""
        audio_file = workflow_state['audio_file']
        
        is_valid, issues = self.audio_service.validate_audio_file(audio_file)
        
        if not is_valid:
            raise ValueError(f"Arquivo inválido: {', '.join(issues)}")
        
        workflow_state['results']['validation'] = {
            'valid': is_valid,
            'issues': issues
        }
        
        return {'issues_count': len(issues)}
    
    async def _step_analysis(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Passo de análise e recomendação."""
        audio_file = workflow_state['audio_file']
        
        recommendation = self.audio_service.recommend_processing_strategy(audio_file)
        
        workflow_state['results']['analysis'] = {
            'strategy': recommendation.strategy.value,
            'whisper_model': recommendation.whisper_model.value,
            'device': recommendation.device,
            'expected_duration_minutes': recommendation.expected_duration_minutes,
            'confidence_level': recommendation.confidence_level,
            'quality_score': recommendation.quality_score,
            'reasoning': recommendation.reasoning
        }
        
        return {
            'strategy': recommendation.strategy.value,
            'model': recommendation.whisper_model.value
        }
    
    async def _step_preprocessing(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Passo de pré-processamento."""
        # Simular pré-processamento
        await asyncio.sleep(0.5)  # Simular tempo de processamento
        
        workflow_state['results']['preprocessing'] = {
            'completed': True,
            'optimizations_applied': ['noise_reduction', 'normalization']
        }
        
        return {'optimizations': 2}
    
    async def _step_transcription(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Passo de transcrição (simulado)."""
        audio_file = workflow_state['audio_file']
        analysis_result = workflow_state['results']['analysis']
        
        # Simular transcrição baseada na duração
        processing_time = analysis_result['expected_duration_minutes'] * 60
        await asyncio.sleep(min(2.0, processing_time * 0.1))  # Simular tempo proporcional
        
        # Criar resultado simulado de transcrição
        # Em implementação real, aqui chamaria o transcriber
        mock_result = self._create_mock_transcription_result(audio_file, analysis_result)
        
        workflow_state['results']['transcription'] = {
            'model_used': analysis_result['whisper_model'],
            'device_used': analysis_result['device'],
            'processing_time_seconds': processing_time,
            'segments_count': len(mock_result.segments),
            'word_count': mock_result.word_count,
            'confidence_average': mock_result.confidence_average
        }
        
        # Armazenar resultado para próximos passos
        workflow_state['_transcription_result'] = mock_result
        
        return {
            'segments': len(mock_result.segments),
            'words': mock_result.word_count
        }
    
    async def _step_quality_analysis(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Passo de análise de qualidade."""
        transcription_result = workflow_state.get('_transcription_result')
        
        if not transcription_result:
            raise ValueError("Resultado de transcrição não encontrado")
        
        quality_assessment = self.quality_service.assess_transcription_quality(transcription_result)
        
        workflow_state['results']['quality_analysis'] = {
            'overall_level': quality_assessment.overall_level.value,
            'confidence_score': quality_assessment.confidence_score,
            'accuracy_estimate': quality_assessment.accuracy_estimate,
            'issues_count': len(quality_assessment.issues_detected),
            'issues': quality_assessment.issues_detected,
            'suggestions': quality_assessment.suggestions,
            'metrics': quality_assessment.metrics
        }
        
        return {
            'quality_level': quality_assessment.overall_level.value,
            'issues': len(quality_assessment.issues_detected)
        }
    
    async def _step_post_processing(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Passo de pós-processamento."""
        # Simular pós-processamento
        await asyncio.sleep(0.3)
        
        workflow_state['results']['post_processing'] = {
            'completed': True,
            'exports_prepared': ['txt', 'json', 'srt'],
            'optimizations': ['text_cleanup', 'timestamp_adjustment']
        }
        
        return {'exports': 3}
    
    def _create_mock_transcription_result(self, audio_file: AudioFile, 
                                        analysis_result: Dict[str, Any]) -> TranscriptionResult:
        """Cria resultado mock de transcrição para demonstração."""
        from src.models.domain import TranscriptionSegment, TranscriptionResult
        
        # Criar segmentos mock baseados na duração
        duration = audio_file.duration_seconds
        segment_count = max(1, int(duration / 10))  # ~10s por segmento
        
        segments = []
        for i in range(segment_count):
            start_time = i * (duration / segment_count)
            end_time = min((i + 1) * (duration / segment_count), duration)
            
            # Simular confiança baseada na qualidade esperada
            base_confidence = analysis_result.get('confidence_level', 0.7)
            confidence = base_confidence + ((-0.1 + 0.2 * i / segment_count) if segment_count > 1 else 0)
            confidence = max(0.3, min(0.95, confidence))
            
            segment = TranscriptionSegment(
                id=i,
                text=f"Segmento de exemplo {i + 1} com texto simulado.",
                start_time=start_time,
                end_time=end_time,
                confidence=confidence
            )
            segments.append(segment)
        
        # Criar resultado
        result = TranscriptionResult(
            audio_file=audio_file,
            segments=segments,
            model_used=WhisperModelSize(analysis_result['whisper_model']),
            language="pt",
            total_duration=duration,
            processing_time=analysis_result.get('expected_duration_minutes', 1.0) * 60
        )
        
        return result
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Obtém status de um workflow."""
        if workflow_id in self._active_workflows:
            return self._active_workflows[workflow_id]
        
        # Buscar no histórico
        for workflow in self._workflow_history:
            if workflow['id'] == workflow_id:
                return workflow
        
        return None
    
    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """Lista workflows ativos."""
        return list(self._active_workflows.values())
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas de workflows."""
        total_workflows = len(self._workflow_history) + len(self._active_workflows)
        completed_workflows = sum(1 for w in self._workflow_history if w['status'] == WorkflowStatus.COMPLETED)
        failed_workflows = sum(1 for w in self._workflow_history if w['status'] == WorkflowStatus.FAILED)
        
        return {
            'total_workflows': total_workflows,
            'active_workflows': len(self._active_workflows),
            'completed_workflows': completed_workflows,
            'failed_workflows': failed_workflows,
            'success_rate': completed_workflows / max(1, len(self._workflow_history))
        }


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_audio_processing_service() -> AudioProcessingService:
    """Factory para AudioProcessingService."""
    return AudioProcessingService()


def create_transcription_quality_service() -> TranscriptionQualityService:
    """Factory para TranscriptionQualityService."""
    return TranscriptionQualityService()


def create_workflow_orchestration_service() -> WorkflowOrchestrationService:
    """Factory para WorkflowOrchestrationService."""
    return WorkflowOrchestrationService()


def create_all_domain_services() -> Dict[str, Any]:
    """Factory para todos os serviços de domínio."""
    return {
        'audio_processing': create_audio_processing_service(),
        'transcription_quality': create_transcription_quality_service(),
        'workflow_orchestration': create_workflow_orchestration_service()
    }
