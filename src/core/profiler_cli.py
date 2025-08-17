# -*- coding: utf-8 -*-
"""
CLI Interface para Auto Profiler - Raycast Integration
Expõe funcionalidades de profiling para o Raycast Extension
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from .auto_profiler import get_auto_profiler, AutoProfiler, BottleneckDetection


class ProfilerCLI:
    """
    Interface CLI para Auto Profiler integrado com Raycast
    """
    
    def __init__(self):
        self.profiler = get_auto_profiler()
    
    def get_bottleneck_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo dos bottlenecks detectados
        """
        try:
            summary = self.profiler.get_bottleneck_summary()
            
            if summary.get('status') == 'no_data':
                return {
                    "status": "success",
                    "data": {
                        "message": "No profiling data available yet",
                        "total_sessions": 0,
                        "total_bottlenecks": 0,
                        "recommendations": [
                            "Start some transcriptions to begin collecting profiling data",
                            "Profiling data will appear here automatically"
                        ]
                    }
                }
            
            # Determinar status geral
            avg_bottlenecks = summary.get('avg_bottlenecks_per_session', 0)
            if avg_bottlenecks == 0:
                status_icon = "✅"
                status_text = "Excellent"
                status_color = "green"
            elif avg_bottlenecks < 1:
                status_icon = "🟢"
                status_text = "Good"
                status_color = "green"
            elif avg_bottlenecks < 3:
                status_icon = "🟡"
                status_text = "Fair"
                status_color = "yellow"
            else:
                status_icon = "🔴"
                status_text = "Needs Attention"
                status_color = "red"
            
            return {
                "status": "success",
                "data": {
                    "overview": {
                        "status_icon": status_icon,
                        "status_text": status_text,
                        "status_color": status_color,
                        "total_sessions": summary['total_sessions'],
                        "total_bottlenecks": summary['total_bottlenecks'],
                        "avg_bottlenecks": f"{avg_bottlenecks:.1f}"
                    },
                    "top_issues": self._format_top_issues(summary),
                    "severity_breakdown": summary.get('severity_distribution', {}),
                    "recommendations": self._generate_summary_recommendations(summary)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_detailed_reports(self, limit: int = 5) -> Dict[str, Any]:
        """
        Retorna relatórios detalhados de profiling
        """
        try:
            reports = self.profiler.get_recent_reports(limit)
            
            if not reports:
                return {
                    "status": "success",
                    "data": {
                        "message": "No profiling reports available",
                        "reports": []
                    }
                }
            
            formatted_reports = []
            for report in reports:
                formatted_report = {
                    "session_id": report.session_id,
                    "operation": report.operation,
                    "duration": f"{report.total_duration:.2f}s",
                    "start_time": report.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "bottlenecks_count": len(report.bottlenecks),
                    "performance_grade": self._calculate_performance_grade(report),
                    "top_bottlenecks": [
                        {
                            "type": b.type,
                            "severity": b.severity,
                            "description": b.description,
                            "suggestion": b.suggestion
                        }
                        for b in sorted(report.bottlenecks, 
                                      key=lambda x: {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(x.severity, 0),
                                      reverse=True)[:3]
                    ],
                    "performance_summary": report.performance_summary
                }
                formatted_reports.append(formatted_report)
            
            return {
                "status": "success",
                "data": {
                    "reports": formatted_reports,
                    "total_reports": len(reports)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """
        Gera insights de performance baseados nos dados de profiling
        """
        try:
            reports = self.profiler.get_recent_reports(20)
            
            if not reports:
                return {
                    "status": "success",
                    "data": {
                        "message": "Insufficient data for insights",
                        "insights": []
                    }
                }
            
            insights = []
            
            # Análise de tendências de CPU
            cpu_averages = []
            for report in reports:
                cpu_avg = report.performance_summary.get('cpu_stats', {}).get('avg', 0)
                if cpu_avg > 0:
                    cpu_averages.append(cpu_avg)
            
            if cpu_averages:
                avg_cpu = sum(cpu_averages) / len(cpu_averages)
                if avg_cpu > 70:
                    insights.append({
                        "type": "cpu_trend",
                        "severity": "medium",
                        "title": "High CPU Usage Trend",
                        "description": f"Average CPU usage is {avg_cpu:.1f}% across recent sessions",
                        "suggestion": "Consider using smaller Whisper models or enabling GPU acceleration",
                        "icon": "⚡"
                    })
            
            # Análise de bottlenecks recorrentes
            bottleneck_frequency = {}
            for report in reports:
                for bottleneck in report.bottlenecks:
                    bottleneck_frequency[bottleneck.type] = bottleneck_frequency.get(bottleneck.type, 0) + 1
            
            # Identificar bottlenecks mais comuns
            if bottleneck_frequency:
                most_common = max(bottleneck_frequency.items(), key=lambda x: x[1])
                if most_common[1] >= 3:  # Aparece em 3+ sessões
                    insights.append({
                        "type": "recurring_bottleneck",
                        "severity": "high",
                        "title": f"Recurring {most_common[0].replace('_', ' ').title()} Issues",
                        "description": f"Detected in {most_common[1]} recent sessions",
                        "suggestion": self._get_bottleneck_suggestion(most_common[0]),
                        "icon": "🔄"
                    })
            
            # Análise de performance por operação
            operation_performance = {}
            for report in reports:
                op = report.operation
                if op not in operation_performance:
                    operation_performance[op] = {'durations': [], 'bottlenecks': []}
                
                operation_performance[op]['durations'].append(report.total_duration)
                operation_performance[op]['bottlenecks'].extend(report.bottlenecks)
            
            # Identificar operações lentas
            for operation, data in operation_performance.items():
                if data['durations']:
                    avg_duration = sum(data['durations']) / len(data['durations'])
                    if operation == 'transcription' and avg_duration > 30:  # >30s para transcrição
                        insights.append({
                            "type": "slow_operation",
                            "severity": "medium",
                            "title": f"Slow {operation.title()} Performance",
                            "description": f"Average duration: {avg_duration:.1f}s",
                            "suggestion": "Consider chunk processing for large files",
                            "icon": "🐌"
                        })
            
            # Insight positivo se tudo está bem
            if not insights:
                insights.append({
                    "type": "good_performance",
                    "severity": "info",
                    "title": "System Running Smoothly",
                    "description": "No significant performance issues detected",
                    "suggestion": "Continue monitoring for optimal performance",
                    "icon": "✅"
                })
            
            return {
                "status": "success",
                "data": {
                    "insights": insights,
                    "analysis_period": f"Last {len(reports)} sessions",
                    "total_insights": len(insights)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_optimization_suggestions(self) -> Dict[str, Any]:
        """
        Gera sugestões de otimização baseadas no profiling
        """
        try:
            summary = self.profiler.get_bottleneck_summary()
            
            suggestions = []
            
            if summary.get('status') == 'no_data':
                suggestions = [
                    {
                        "category": "setup",
                        "priority": "low",
                        "title": "Start Profiling",
                        "description": "Begin using the system to collect performance data",
                        "action": "Run some transcriptions to generate profiling data"
                    }
                ]
            else:
                # Sugestões baseadas nos tipos de bottlenecks mais comuns
                bottleneck_types = summary.get('bottleneck_types', {})
                
                if 'cpu' in bottleneck_types or 'cpu_trend' in bottleneck_types:
                    suggestions.append({
                        "category": "performance",
                        "priority": "high",
                        "title": "CPU Optimization",
                        "description": "High CPU usage detected frequently",
                        "action": "Enable GPU acceleration or use smaller Whisper models"
                    })
                
                if 'memory' in bottleneck_types:
                    suggestions.append({
                        "category": "memory",
                        "priority": "high",
                        "title": "Memory Management",
                        "description": "Memory bottlenecks detected",
                        "action": "Enable memory optimization and use model caching"
                    })
                
                if 'model_loading' in bottleneck_types:
                    suggestions.append({
                        "category": "caching",
                        "priority": "medium",
                        "title": "Model Caching",
                        "description": "Slow model loading detected",
                        "action": "Ensure model cache is enabled and working properly"
                    })
                
                if 'transcription_slow' in bottleneck_types:
                    suggestions.append({
                        "category": "processing",
                        "priority": "medium",
                        "title": "Processing Speed",
                        "description": "Slow transcription performance",
                        "action": "Use GPU acceleration and optimize chunk sizes"
                    })
                
                # Sugestões gerais se pocos bottlenecks
                if len(bottleneck_types) == 0:
                    suggestions.append({
                        "category": "monitoring",
                        "priority": "low",
                        "title": "Performance Monitoring",
                        "description": "System performing well",
                        "action": "Continue monitoring for any performance changes"
                    })
            
            return {
                "status": "success",
                "data": {
                    "suggestions": suggestions,
                    "total_suggestions": len(suggestions)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def export_profiling_report(self, format: str = "json") -> Dict[str, Any]:
        """
        Exporta relatório completo de profiling
        """
        try:
            reports = self.profiler.get_recent_reports(50)  # Últimos 50 relatórios
            summary = self.profiler.get_bottleneck_summary()
            
            # Compilar dados
            export_data = {
                "generated_at": datetime.now().isoformat(),
                "report_type": "profiling_analysis",
                "summary": summary,
                "total_reports": len(reports),
                "detailed_reports": [],
                "insights": self.get_performance_insights()["data"],
                "optimization_suggestions": self.get_optimization_suggestions()["data"]
            }
            
            # Adicionar relatórios detalhados
            for report in reports:
                export_data["detailed_reports"].append({
                    "session_id": report.session_id,
                    "operation": report.operation,
                    "start_time": report.start_time.isoformat(),
                    "duration": report.total_duration,
                    "bottlenecks": [
                        {
                            "type": b.type,
                            "severity": b.severity,
                            "description": b.description,
                            "suggestion": b.suggestion,
                            "timestamp": b.timestamp.isoformat() if hasattr(b.timestamp, 'isoformat') else str(b.timestamp)
                        }
                        for b in report.bottlenecks
                    ],
                    "performance_summary": report.performance_summary
                })
            
            # Salvar arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"profiling_report_{timestamp}.{format.lower()}"
            report_path = Path("storage/reports") / filename
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "json":
                content = json.dumps(export_data, indent=2, ensure_ascii=False)
            else:
                content = json.dumps(export_data, indent=2, ensure_ascii=False)  # Fallback to JSON
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "status": "success",
                "message": f"Profiling report exported successfully",
                "file_path": str(report_path),
                "size_kb": len(content) / 1024,
                "reports_included": len(reports)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _format_top_issues(self, summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Formata os principais problemas detectados"""
        bottleneck_types = summary.get('bottleneck_types', {})
        
        # Ordenar por frequência
        sorted_types = sorted(bottleneck_types.items(), key=lambda x: x[1], reverse=True)
        
        top_issues = []
        for bottleneck_type, count in sorted_types[:5]:  # Top 5
            issue = {
                "type": bottleneck_type,
                "count": count,
                "description": self._get_bottleneck_description(bottleneck_type),
                "suggestion": self._get_bottleneck_suggestion(bottleneck_type)
            }
            top_issues.append(issue)
        
        return top_issues
    
    def _get_bottleneck_description(self, bottleneck_type: str) -> str:
        """Retorna descrição amigável do tipo de bottleneck"""
        descriptions = {
            'cpu': 'High CPU usage during processing',
            'memory': 'Memory usage exceeding safe limits',
            'gpu_memory': 'GPU memory running out of space',
            'model_loading': 'Slow model loading times',
            'transcription_slow': 'Transcription taking longer than expected',
            'disk_io': 'High disk I/O usage',
            'cpu_trend': 'CPU usage trending upward over time'
        }
        return descriptions.get(bottleneck_type, f'Performance issue: {bottleneck_type}')
    
    def _get_bottleneck_suggestion(self, bottleneck_type: str) -> str:
        """Retorna sugestão específica para o tipo de bottleneck"""
        suggestions = {
            'cpu': 'Use smaller Whisper model or enable GPU acceleration',
            'memory': 'Enable memory optimization and cleanup',
            'gpu_memory': 'Clear GPU cache or use CPU mode',
            'model_loading': 'Enable model caching',
            'transcription_slow': 'Use GPU acceleration and optimize chunk sizes',
            'disk_io': 'Use SSD storage or enable file caching',
            'cpu_trend': 'Monitor system and consider hardware upgrade'
        }
        return suggestions.get(bottleneck_type, 'Monitor this issue and consider optimization')
    
    def _calculate_performance_grade(self, report) -> str:
        """Calcula nota de performance para um relatório"""
        bottleneck_count = len(report.bottlenecks)
        critical_count = sum(1 for b in report.bottlenecks if b.severity == 'critical')
        high_count = sum(1 for b in report.bottlenecks if b.severity == 'high')
        
        if critical_count > 0:
            return "Poor"
        elif high_count > 2:
            return "Fair"
        elif bottleneck_count > 3:
            return "Good"
        else:
            return "Excellent"
    
    def _generate_summary_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas no resumo"""
        recommendations = []
        
        avg_bottlenecks = summary.get('avg_bottlenecks_per_session', 0)
        
        if avg_bottlenecks == 0:
            recommendations.append("🎉 Excellent performance! No bottlenecks detected")
            recommendations.append("📊 Continue monitoring for any performance changes")
        elif avg_bottlenecks < 1:
            recommendations.append("✅ Good performance with minimal issues")
            recommendations.append("🔍 Monitor the occasional bottlenecks")
        elif avg_bottlenecks < 3:
            recommendations.append("⚠️ Some performance issues detected")
            recommendations.append("🔧 Consider implementing suggested optimizations")
        else:
            recommendations.append("🚨 Multiple performance bottlenecks detected")
            recommendations.append("⚡ Immediate optimization recommended")
        
        return recommendations


def main():
    """
    Ponto de entrada CLI para profiling
    """
    parser = argparse.ArgumentParser(description="MeetingScribe Auto Profiler CLI")
    parser.add_argument("command", choices=[
        "summary", "reports", "insights", "suggestions", "export"
    ], help="Command to execute")
    parser.add_argument("--limit", type=int, default=5, help="Limit results")
    parser.add_argument("--format", default="json", help="Output format for export")
    
    args = parser.parse_args()
    
    cli = ProfilerCLI()
    
    # Executar comando
    if args.command == "summary":
        result = cli.get_bottleneck_summary()
    elif args.command == "reports":
        result = cli.get_detailed_reports(args.limit)
    elif args.command == "insights":
        result = cli.get_performance_insights()
    elif args.command == "suggestions":
        result = cli.get_optimization_suggestions()
    elif args.command == "export":
        result = cli.export_profiling_report(args.format)
    else:
        result = {"status": "error", "message": "Unknown command"}
    
    # Output JSON para Raycast
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()