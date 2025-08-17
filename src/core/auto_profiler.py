# -*- coding: utf-8 -*-
"""
Sistema de Profiling Automático - MeetingScribe
Identifica bottlenecks automaticamente durante transcrições e gera relatórios
"""

import time
import threading
import psutil
import cProfile
import pstats
import io
import traceback
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Callable, Tuple
from pathlib import Path
from collections import defaultdict, deque
from contextlib import contextmanager
import statistics
import json

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

@dataclass
class BottleneckDetection:
    """Detecção de gargalo de performance"""
    type: str  # 'cpu', 'memory', 'io', 'gpu', 'model_loading'
    severity: str  # 'low', 'medium', 'high', 'critical'
    component: str  # Componente específico afetado
    metric_value: float
    threshold_value: float
    description: str
    suggestion: str
    timestamp: datetime
    duration: float = 0.0
    context: Dict[str, Any] = None

@dataclass
class ProfilingReport:
    """Relatório completo de profiling"""
    session_id: str
    start_time: datetime
    end_time: datetime
    total_duration: float
    operation: str  # 'transcription', 'model_loading', etc.
    bottlenecks: List[BottleneckDetection]
    performance_summary: Dict[str, Any]
    detailed_metrics: Dict[str, Any]
    recommendations: List[str]
    cprofile_stats: Optional[str] = None

@dataclass
class SystemSnapshot:
    """Snapshot do estado do sistema"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_io_read: float
    disk_io_write: float
    gpu_memory_mb: float
    gpu_utilization: float
    active_threads: int
    open_files: int

class AutoProfiler:
    """
    Profiler automático que monitora performance e identifica bottlenecks
    """
    
    def __init__(self, 
                 storage_path: str = "storage/profiling",
                 sampling_interval: float = 0.5,
                 max_reports: int = 100):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.sampling_interval = sampling_interval
        self.max_reports = max_reports
        
        # Thread-safe storage
        self._lock = threading.RLock()
        self._active_sessions: Dict[str, Dict] = {}
        self._completed_reports: deque = deque(maxlen=max_reports)
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Thresholds para detecção de bottlenecks
        self.thresholds = {
            'cpu_high': 80.0,
            'cpu_critical': 95.0,
            'memory_high': 75.0,
            'memory_critical': 90.0,
            'gpu_memory_high': 80.0,
            'gpu_memory_critical': 95.0,
            'disk_io_high': 50.0,  # MB/s
            'model_load_slow': 10.0,  # seconds
            'transcription_slow': 2.0,  # ratio (processing_time / audio_length)
        }
        
        # Performance baseline
        self._baseline_metrics: Dict[str, float] = {}
        self._baseline_samples = 0
        
        # Active profiling sessions
        self._active_profilers: Dict[str, cProfile.Profile] = {}
        
        self._init_baseline()
    
    def _init_baseline(self):
        """Inicializa baseline de performance do sistema"""
        try:
            # Coleta algumas amostras iniciais para estabelecer baseline
            samples = []
            for _ in range(5):
                snapshot = self._take_system_snapshot()
                samples.append(snapshot)
                time.sleep(0.1)
            
            if samples:
                self._baseline_metrics = {
                    'cpu_avg': statistics.mean([s.cpu_percent for s in samples]),
                    'memory_avg': statistics.mean([s.memory_percent for s in samples]),
                    'gpu_memory_avg': statistics.mean([s.gpu_memory_mb for s in samples]),
                }
                self._baseline_samples = len(samples)
                
        except Exception as e:
            print(f"Warning: Could not establish performance baseline: {e}")
    
    def start_profiling_session(self, 
                               operation: str,
                               context: Dict[str, Any] = None) -> str:
        """
        Inicia uma sessão de profiling
        
        Args:
            operation: Tipo de operação ('transcription', 'model_loading', etc.)
            context: Contexto adicional da operação
            
        Returns:
            session_id: ID único da sessão
        """
        session_id = f"{operation}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        with self._lock:
            # Configurar sessão
            session_data = {
                'session_id': session_id,
                'operation': operation,
                'start_time': datetime.now(),
                'context': context or {},
                'snapshots': [],
                'bottlenecks': [],
                'events': []
            }
            
            self._active_sessions[session_id] = session_data
            
            # Iniciar cProfile se necessário
            if operation in ['transcription', 'model_loading']:
                profiler = cProfile.Profile()
                profiler.enable()
                self._active_profilers[session_id] = profiler
            
            # Iniciar monitoramento se não estiver ativo
            if not self._monitoring:
                self._start_monitoring()
        
        return session_id
    
    def end_profiling_session(self, session_id: str) -> ProfilingReport:
        """
        Finaliza uma sessão de profiling e gera relatório
        
        Args:
            session_id: ID da sessão
            
        Returns:
            ProfilingReport: Relatório completo da sessão
        """
        with self._lock:
            if session_id not in self._active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session_data = self._active_sessions.pop(session_id)
            
            # Parar cProfile se estiver ativo
            cprofile_stats = None
            if session_id in self._active_profilers:
                profiler = self._active_profilers.pop(session_id)
                profiler.disable()
                
                # Capturar stats
                s = io.StringIO()
                ps = pstats.Stats(profiler, stream=s)
                ps.sort_stats('cumulative')
                ps.print_stats(20)  # Top 20 functions
                cprofile_stats = s.getvalue()
            
            # Tomar snapshot final
            final_snapshot = self._take_system_snapshot()
            session_data['snapshots'].append(final_snapshot)
            
            # Analisar sessão e detectar bottlenecks
            end_time = datetime.now()
            total_duration = (end_time - session_data['start_time']).total_seconds()
            
            # Detectar bottlenecks finais
            final_bottlenecks = self._analyze_session_bottlenecks(session_data)
            session_data['bottlenecks'].extend(final_bottlenecks)
            
            # Gerar relatório
            report = ProfilingReport(
                session_id=session_id,
                start_time=session_data['start_time'],
                end_time=end_time,
                total_duration=total_duration,
                operation=session_data['operation'],
                bottlenecks=session_data['bottlenecks'],
                performance_summary=self._generate_performance_summary(session_data),
                detailed_metrics=self._generate_detailed_metrics(session_data),
                recommendations=self._generate_recommendations(session_data['bottlenecks']),
                cprofile_stats=cprofile_stats
            )
            
            # Salvar relatório
            self._save_report(report)
            self._completed_reports.append(report)
            
            return report
    
    def add_profiling_event(self, 
                           session_id: str, 
                           event_type: str, 
                           description: str,
                           metrics: Dict[str, Any] = None):
        """Adiciona evento específico à sessão de profiling"""
        with self._lock:
            if session_id in self._active_sessions:
                event = {
                    'timestamp': datetime.now(),
                    'type': event_type,
                    'description': description,
                    'metrics': metrics or {},
                    'system_snapshot': self._take_system_snapshot()
                }
                self._active_sessions[session_id]['events'].append(event)
                
                # Analisar se este evento causou um bottleneck
                bottleneck = self._analyze_event_bottleneck(event, session_id)
                if bottleneck:
                    self._active_sessions[session_id]['bottlenecks'].append(bottleneck)
    
    def _start_monitoring(self):
        """Inicia thread de monitoramento"""
        if self._monitoring:
            return
            
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="AutoProfiler"
        )
        self._monitor_thread.start()
    
    def _monitoring_loop(self):
        """Loop principal de monitoramento"""
        while self._monitoring:
            try:
                if self._active_sessions:
                    self._monitor_active_sessions()
                else:
                    # Parar monitoramento se não há sessões ativas
                    self._monitoring = False
                    break
                    
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                print(f"Error in profiling monitoring loop: {e}")
                time.sleep(self.sampling_interval)
    
    def _monitor_active_sessions(self):
        """Monitora sessões ativas"""
        snapshot = self._take_system_snapshot()
        
        with self._lock:
            for session_id, session_data in self._active_sessions.items():
                # Adicionar snapshot à sessão
                session_data['snapshots'].append(snapshot)
                
                # Detectar bottlenecks em tempo real
                bottleneck = self._detect_realtime_bottleneck(snapshot, session_data)
                if bottleneck:
                    session_data['bottlenecks'].append(bottleneck)
    
    def _take_system_snapshot(self) -> SystemSnapshot:
        """Captura snapshot do estado atual do sistema"""
        try:
            # CPU e Memória
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            disk_read = disk_io.read_bytes / 1024 / 1024 if disk_io else 0  # MB
            disk_write = disk_io.write_bytes / 1024 / 1024 if disk_io else 0  # MB
            
            # GPU (se disponível)
            gpu_memory = 0.0
            gpu_util = 0.0
            if TORCH_AVAILABLE and torch.cuda.is_available():
                try:
                    gpu_memory = torch.cuda.memory_allocated() / 1024**2  # MB
                    gpu_util = torch.cuda.utilization() if hasattr(torch.cuda, 'utilization') else 0.0
                except:
                    pass
            
            # Processos e threads
            current_process = psutil.Process()
            active_threads = current_process.num_threads()
            open_files = len(current_process.open_files())
            
            return SystemSnapshot(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available_mb=memory.available / 1024**2,
                disk_io_read=disk_read,
                disk_io_write=disk_write,
                gpu_memory_mb=gpu_memory,
                gpu_utilization=gpu_util,
                active_threads=active_threads,
                open_files=open_files
            )
            
        except Exception as e:
            print(f"Error taking system snapshot: {e}")
            return SystemSnapshot(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available_mb=0.0,
                disk_io_read=0.0,
                disk_io_write=0.0,
                gpu_memory_mb=0.0,
                gpu_utilization=0.0,
                active_threads=0,
                open_files=0
            )
    
    def _detect_realtime_bottleneck(self, 
                                   snapshot: SystemSnapshot, 
                                   session_data: Dict) -> Optional[BottleneckDetection]:
        """Detecta bottlenecks em tempo real"""
        
        # CPU bottleneck
        if snapshot.cpu_percent > self.thresholds['cpu_critical']:
            return BottleneckDetection(
                type='cpu',
                severity='critical',
                component='system_cpu',
                metric_value=snapshot.cpu_percent,
                threshold_value=self.thresholds['cpu_critical'],
                description=f"CPU usage critical: {snapshot.cpu_percent:.1f}%",
                suggestion="Consider using a smaller Whisper model or enable chunk processing",
                timestamp=snapshot.timestamp,
                context={'operation': session_data['operation']}
            )
        elif snapshot.cpu_percent > self.thresholds['cpu_high']:
            return BottleneckDetection(
                type='cpu',
                severity='high',
                component='system_cpu',
                metric_value=snapshot.cpu_percent,
                threshold_value=self.thresholds['cpu_high'],
                description=f"High CPU usage detected: {snapshot.cpu_percent:.1f}%",
                suggestion="Monitor CPU usage and consider optimizations",
                timestamp=snapshot.timestamp,
                context={'operation': session_data['operation']}
            )
        
        # Memory bottleneck
        if snapshot.memory_percent > self.thresholds['memory_critical']:
            return BottleneckDetection(
                type='memory',
                severity='critical',
                component='system_memory',
                metric_value=snapshot.memory_percent,
                threshold_value=self.thresholds['memory_critical'],
                description=f"Memory usage critical: {snapshot.memory_percent:.1f}%",
                suggestion="Enable memory optimization or use smaller model",
                timestamp=snapshot.timestamp,
                context={'operation': session_data['operation']}
            )
        elif snapshot.memory_percent > self.thresholds['memory_high']:
            return BottleneckDetection(
                type='memory',
                severity='high',
                component='system_memory',
                metric_value=snapshot.memory_percent,
                threshold_value=self.thresholds['memory_high'],
                description=f"High memory usage: {snapshot.memory_percent:.1f}%",
                suggestion="Monitor memory usage and enable cleanup",
                timestamp=snapshot.timestamp,
                context={'operation': session_data['operation']}
            )
        
        # GPU Memory bottleneck
        if TORCH_AVAILABLE and snapshot.gpu_memory_mb > 0:
            try:
                total_gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**2
                gpu_usage_percent = (snapshot.gpu_memory_mb / total_gpu_memory) * 100
                
                if gpu_usage_percent > self.thresholds['gpu_memory_critical']:
                    return BottleneckDetection(
                        type='gpu_memory',
                        severity='critical',
                        component='gpu_memory',
                        metric_value=gpu_usage_percent,
                        threshold_value=self.thresholds['gpu_memory_critical'],
                        description=f"GPU memory critical: {gpu_usage_percent:.1f}%",
                        suggestion="Clear GPU cache or use CPU mode",
                        timestamp=snapshot.timestamp,
                        context={'operation': session_data['operation']}
                    )
            except:
                pass
        
        return None
    
    def _analyze_event_bottleneck(self, 
                                event: Dict, 
                                session_id: str) -> Optional[BottleneckDetection]:
        """Analisa se um evento específico causou bottleneck"""
        
        if event['type'] == 'model_loading':
            load_time = event['metrics'].get('load_time', 0)
            if load_time > self.thresholds['model_load_slow']:
                return BottleneckDetection(
                    type='model_loading',
                    severity='medium' if load_time < 20 else 'high',
                    component='whisper_model',
                    metric_value=load_time,
                    threshold_value=self.thresholds['model_load_slow'],
                    description=f"Slow model loading: {load_time:.2f}s",
                    suggestion="Enable model caching or use smaller model",
                    timestamp=event['timestamp'],
                    duration=load_time,
                    context=event['metrics']
                )
        
        elif event['type'] == 'transcription_chunk':
            processing_time = event['metrics'].get('processing_time', 0)
            audio_length = event['metrics'].get('audio_length', 1)
            ratio = processing_time / audio_length if audio_length > 0 else 0
            
            if ratio > self.thresholds['transcription_slow']:
                return BottleneckDetection(
                    type='transcription_slow',
                    severity='medium' if ratio < 5 else 'high',
                    component='transcription_engine',
                    metric_value=ratio,
                    threshold_value=self.thresholds['transcription_slow'],
                    description=f"Slow transcription: {ratio:.1f}x realtime",
                    suggestion="Consider GPU acceleration or smaller model",
                    timestamp=event['timestamp'],
                    duration=processing_time,
                    context=event['metrics']
                )
        
        return None
    
    def _analyze_session_bottlenecks(self, session_data: Dict) -> List[BottleneckDetection]:
        """Analisa bottlenecks da sessão completa"""
        bottlenecks = []
        
        if not session_data['snapshots']:
            return bottlenecks
        
        # Analisar tendências de CPU
        cpu_values = [s.cpu_percent for s in session_data['snapshots']]
        avg_cpu = statistics.mean(cpu_values)
        max_cpu = max(cpu_values)
        
        # Comparar com baseline
        baseline_cpu = self._baseline_metrics.get('cpu_avg', 20.0)
        if avg_cpu > baseline_cpu * 2:  # 2x acima do baseline
            bottlenecks.append(BottleneckDetection(
                type='cpu_trend',
                severity='medium',
                component='session_cpu',
                metric_value=avg_cpu,
                threshold_value=baseline_cpu * 2,
                description=f"Session CPU usage {avg_cpu:.1f}% is {avg_cpu/baseline_cpu:.1f}x above baseline",
                suggestion="Investigate CPU-intensive operations in this session",
                timestamp=session_data['start_time'],
                context={'baseline_cpu': baseline_cpu, 'max_cpu': max_cpu}
            ))
        
        # Analisar I/O patterns
        if len(session_data['snapshots']) > 1:
            io_reads = [s.disk_io_read for s in session_data['snapshots']]
            io_writes = [s.disk_io_write for s in session_data['snapshots']]
            
            max_read_rate = max(io_reads[i] - io_reads[i-1] 
                               for i in range(1, len(io_reads))) if len(io_reads) > 1 else 0
            max_write_rate = max(io_writes[i] - io_writes[i-1] 
                                for i in range(1, len(io_writes))) if len(io_writes) > 1 else 0
            
            if max_read_rate > self.thresholds['disk_io_high']:
                bottlenecks.append(BottleneckDetection(
                    type='disk_io',
                    severity='medium',
                    component='disk_read',
                    metric_value=max_read_rate,
                    threshold_value=self.thresholds['disk_io_high'],
                    description=f"High disk read rate: {max_read_rate:.1f} MB/s",
                    suggestion="Consider file caching or SSD storage",
                    timestamp=session_data['start_time'],
                    context={'max_write_rate': max_write_rate}
                ))
        
        return bottlenecks
    
    def _generate_performance_summary(self, session_data: Dict) -> Dict[str, Any]:
        """Gera resumo de performance da sessão"""
        if not session_data['snapshots']:
            return {}
        
        snapshots = session_data['snapshots']
        
        return {
            'duration_seconds': (datetime.now() - session_data['start_time']).total_seconds(),
            'cpu_stats': {
                'avg': statistics.mean([s.cpu_percent for s in snapshots]),
                'max': max([s.cpu_percent for s in snapshots]),
                'min': min([s.cpu_percent for s in snapshots])
            },
            'memory_stats': {
                'avg': statistics.mean([s.memory_percent for s in snapshots]),
                'max': max([s.memory_percent for s in snapshots]),
                'min': min([s.memory_percent for s in snapshots])
            },
            'gpu_stats': {
                'avg_memory_mb': statistics.mean([s.gpu_memory_mb for s in snapshots]),
                'max_memory_mb': max([s.gpu_memory_mb for s in snapshots])
            },
            'bottlenecks_count': len(session_data['bottlenecks']),
            'events_count': len(session_data['events']),
            'samples_count': len(snapshots)
        }
    
    def _generate_detailed_metrics(self, session_data: Dict) -> Dict[str, Any]:
        """Gera métricas detalhadas da sessão"""
        return {
            'session_id': session_data['session_id'],
            'operation': session_data['operation'],
            'context': session_data['context'],
            'timeline': [
                {
                    'timestamp': event['timestamp'].isoformat(),
                    'type': event['type'],
                    'description': event['description'],
                    'metrics': event['metrics']
                }
                for event in session_data['events']
            ],
            'system_snapshots': [
                {
                    'timestamp': s.timestamp.isoformat(),
                    'cpu': s.cpu_percent,
                    'memory': s.memory_percent,
                    'gpu_memory': s.gpu_memory_mb
                }
                for s in session_data['snapshots'][-10:]  # Últimos 10 snapshots
            ]
        }
    
    def _generate_recommendations(self, bottlenecks: List[BottleneckDetection]) -> List[str]:
        """Gera recomendações baseadas nos bottlenecks detectados"""
        recommendations = []
        
        # Agrupar bottlenecks por tipo
        bottleneck_types = defaultdict(list)
        for bottleneck in bottlenecks:
            bottleneck_types[bottleneck.type].append(bottleneck)
        
        # CPU recommendations
        if 'cpu' in bottleneck_types or 'cpu_trend' in bottleneck_types:
            recommendations.append("🔧 **CPU Optimization**: Consider using a smaller Whisper model (tiny/base) or enable chunk processing for large files")
            recommendations.append("⚡ **Performance**: Enable GPU acceleration if available to reduce CPU load")
        
        # Memory recommendations
        if 'memory' in bottleneck_types:
            recommendations.append("💾 **Memory Management**: Enable automatic memory cleanup and use smaller batch sizes")
            recommendations.append("🗄️ **Model Size**: Consider using a smaller Whisper model to reduce memory usage")
        
        # GPU recommendations
        if 'gpu_memory' in bottleneck_types:
            recommendations.append("🎮 **GPU Memory**: Clear GPU cache between operations or use mixed precision")
            recommendations.append("⚖️ **Fallback**: Consider CPU mode for very large files")
        
        # Model loading recommendations
        if 'model_loading' in bottleneck_types:
            recommendations.append("🚀 **Model Cache**: Enable model caching to avoid repeated loading")
            recommendations.append("📦 **Model Selection**: Use appropriate model size for your hardware")
        
        # Transcription speed recommendations
        if 'transcription_slow' in bottleneck_types:
            recommendations.append("🎯 **Processing Speed**: Enable GPU acceleration and optimize chunk sizes")
            recommendations.append("🔀 **Parallel Processing**: Use async processing for multiple files")
        
        # I/O recommendations
        if 'disk_io' in bottleneck_types:
            recommendations.append("💿 **Storage**: Use SSD storage for better I/O performance")
            recommendations.append("🗂️ **Caching**: Enable file caching to reduce disk reads")
        
        # General recommendations if no specific bottlenecks
        if not recommendations:
            recommendations.append("✅ **Performance**: System performing well, no major bottlenecks detected")
            recommendations.append("📊 **Monitoring**: Continue monitoring for performance trends")
        
        return recommendations
    
    def _save_report(self, report: ProfilingReport):
        """Salva relatório em disco"""
        try:
            report_file = self.storage_path / f"profile_report_{report.session_id}.json"
            
            # Converter para formato serializável
            report_data = {
                'session_id': report.session_id,
                'start_time': report.start_time.isoformat(),
                'end_time': report.end_time.isoformat(),
                'total_duration': report.total_duration,
                'operation': report.operation,
                'bottlenecks': [asdict(b) for b in report.bottlenecks],
                'performance_summary': report.performance_summary,
                'detailed_metrics': report.detailed_metrics,
                'recommendations': report.recommendations,
                'cprofile_stats': report.cprofile_stats
            }
            
            # Converter timestamps em bottlenecks
            for bottleneck in report_data['bottlenecks']:
                if 'timestamp' in bottleneck and hasattr(bottleneck['timestamp'], 'isoformat'):
                    bottleneck['timestamp'] = bottleneck['timestamp'].isoformat()
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
                
        except Exception as e:
            print(f"Error saving profiling report: {e}")
    
    def get_recent_reports(self, limit: int = 10) -> List[ProfilingReport]:
        """Obtém relatórios recentes"""
        with self._lock:
            return list(self._completed_reports)[-limit:]
    
    def get_bottleneck_summary(self) -> Dict[str, Any]:
        """Obtém resumo dos bottlenecks recentes"""
        recent_reports = self.get_recent_reports(20)
        
        if not recent_reports:
            return {'status': 'no_data'}
        
        # Agregar bottlenecks
        bottleneck_types = defaultdict(int)
        severity_counts = defaultdict(int)
        total_bottlenecks = 0
        
        for report in recent_reports:
            for bottleneck in report.bottlenecks:
                bottleneck_types[bottleneck.type] += 1
                severity_counts[bottleneck.severity] += 1
                total_bottlenecks += 1
        
        return {
            'total_sessions': len(recent_reports),
            'total_bottlenecks': total_bottlenecks,
            'avg_bottlenecks_per_session': total_bottlenecks / len(recent_reports),
            'bottleneck_types': dict(bottleneck_types),
            'severity_distribution': dict(severity_counts),
            'top_bottleneck': max(bottleneck_types.items(), key=lambda x: x[1])[0] if bottleneck_types else None
        }
    
    def stop_monitoring(self):
        """Para o monitoramento e finaliza todas as sessões ativas"""
        self._monitoring = False
        
        # Finalizar sessões ativas
        with self._lock:
            active_session_ids = list(self._active_sessions.keys())
            
        for session_id in active_session_ids:
            try:
                self.end_profiling_session(session_id)
            except Exception as e:
                print(f"Error ending session {session_id}: {e}")


# Context manager para profiling automático
@contextmanager
def auto_profile(operation: str, context: Dict[str, Any] = None):
    """Context manager para profiling automático de operações"""
    
    try:
        from .performance_monitor import get_performance_monitor
        PERFORMANCE_MONITOR_AVAILABLE = True
    except ImportError:
        PERFORMANCE_MONITOR_AVAILABLE = False
    
    # Profiler sempre disponível
    profiler = AutoProfiler()
    session_id = profiler.start_profiling_session(operation, context)
    
    try:
        yield session_id
    finally:
        report = profiler.end_profiling_session(session_id)
        
        # Integrar com monitor de performance se disponível
        if PERFORMANCE_MONITOR_AVAILABLE:
            try:
                monitor = get_performance_monitor()
                
                # Adicionar métricas de profiling
                monitor.add_metric(
                    f"profiling_{operation}_duration",
                    report.total_duration,
                    "seconds",
                    "profiling"
                )
                
                monitor.add_metric(
                    f"profiling_{operation}_bottlenecks",
                    len(report.bottlenecks),
                    "count",
                    "profiling"
                )
                
            except Exception as e:
                print(f"Error integrating with performance monitor: {e}")


# Singleton global
_auto_profiler: Optional[AutoProfiler] = None

def get_auto_profiler() -> AutoProfiler:
    """Obtém instância singleton do auto profiler"""
    global _auto_profiler
    
    if _auto_profiler is None:
        _auto_profiler = AutoProfiler()
    
    return _auto_profiler