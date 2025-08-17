# -*- coding: utf-8 -*-
"""
CLI Interface para Métricas de Performance - Raycast Integration
Expõe métricas do sistema para consumo pelo Raycast Extension
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from .performance_monitor import get_performance_monitor, PerformanceMonitor


class RaycastMetricsCLI:
    """
    Interface CLI para exposição de métricas ao Raycast
    Fornece comandos específicos para diferentes tipos de métricas
    """
    
    def __init__(self):
        self.monitor = get_performance_monitor()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Retorna dados completos para o dashboard principal
        """
        try:
            metrics = self.monitor.get_metrics_for_raycast()
            
            # Enriquece com dados específicos para Raycast
            dashboard = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "overview": {
                        "system_health": metrics["realtime"]["system_health"],
                        "transcriptions_today": metrics["realtime"]["transcriptions_today"],
                        "cache_hit_rate": f"{metrics['realtime']['cache_hit_rate']:.1f}%",
                        "avg_processing_time": f"{metrics['realtime']['average_processing_time']:.2f}s",
                        "memory_efficiency": f"{metrics['realtime']['memory_efficiency']:.1f}%"
                    },
                    "system": {
                        "cpu_usage": f"{metrics['system']['cpu_avg']:.1f}%",
                        "memory_usage": f"{metrics['system']['memory_avg']:.1f}%",
                        "status": metrics['system']['status'],
                        "peak_cpu": f"{metrics['system']['cpu_max']:.1f}%",
                        "peak_memory": f"{metrics['system']['memory_max']:.1f}%"
                    },
                    "transcription": {
                        "success_rate": f"{metrics['transcription']['success_rate']:.1f}%",
                        "total_today": metrics['transcription']['total_today'],
                        "avg_time": f"{metrics['transcription']['avg_processing_time']:.2f}s",
                        "cache_hits": metrics['transcription']['cache_hits_total'],
                        "status": metrics['transcription']['status']
                    },
                    "cache": {
                        "size": f"{metrics['cache']['current_size_mb']:.1f} MB",
                        "hit_rate": f"{metrics['cache']['hit_rate']:.1f}%",
                        "total_hits": metrics['cache']['total_hits'],
                        "status": metrics['cache']['status']
                    }
                }
            }
            
            return dashboard
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Status condensado do sistema para quick view
        """
        try:
            metrics = self.monitor.get_metrics_for_raycast()
            
            status = {
                "status": "success",
                "health": metrics["realtime"]["system_health"],
                "cpu": f"{metrics['system']['cpu_avg']:.0f}%",
                "memory": f"{metrics['system']['memory_avg']:.0f}%",
                "transcriptions": metrics["realtime"]["transcriptions_today"],
                "cache_hits": f"{metrics['realtime']['cache_hit_rate']:.0f}%",
                "timestamp": datetime.now().isoformat()
            }
            
            # Determina cor/ícone para Raycast
            health = metrics["realtime"]["system_health"]
            if health == "optimal":
                status["icon"] = "✅"
                status["color"] = "green"
            elif health == "warning":
                status["icon"] = "⚠️"
                status["color"] = "yellow"
            elif health == "critical":
                status["icon"] = "🔴"
                status["color"] = "red"
            else:
                status["icon"] = "❓"
                status["color"] = "gray"
            
            return status
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "icon": "💥",
                "color": "red"
            }
    
    def get_transcription_metrics(self) -> Dict[str, Any]:
        """
        Métricas específicas de transcrição
        """
        try:
            metrics = self.monitor.get_metrics_for_raycast()
            transcription = metrics.get("transcription", {})
            
            return {
                "status": "success",
                "data": {
                    "today_total": transcription.get("total_today", 0),
                    "success_rate": f"{transcription.get('success_rate', 0):.1f}%",
                    "average_time": f"{transcription.get('avg_processing_time', 0):.2f}s",
                    "cache_efficiency": f"{metrics['realtime']['cache_hit_rate']:.1f}%",
                    "status": transcription.get("status", "unknown"),
                    "recent_transcriptions": self._get_recent_transcriptions_summary()
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _get_recent_transcriptions_summary(self) -> List[Dict[str, Any]]:
        """
        Resumo das transcrições recentes
        """
        try:
            recent = self.monitor._transcription_history[-5:]  # Últimas 5
            
            summary = []
            for trans in recent:
                summary.append({
                    "duration": f"{trans.audio_length:.1f}s",
                    "processing_time": f"{trans.processing_time:.2f}s",
                    "model": trans.model_size,
                    "chunks": trans.chunks_count,
                    "success": trans.success,
                    "cache_hits": trans.cache_hits > 0
                })
            
            return summary
            
        except Exception:
            return []
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Status detalhado do cache
        """
        try:
            metrics = self.monitor.get_metrics_for_raycast()
            cache = metrics.get("cache", {})
            
            return {
                "status": "success",
                "data": {
                    "current_size": cache.get("current_size_mb", 0),
                    "hit_rate": f"{cache.get('hit_rate', 0):.1f}%",
                    "total_hits": cache.get("total_hits", 0),
                    "status": cache.get("status", "unknown"),
                    "efficiency": self._calculate_cache_efficiency()
                }
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": str(e)
            }
    
    def _calculate_cache_efficiency(self) -> str:
        """
        Calcula eficiência do cache para display
        """
        try:
            hit_rate = self.monitor._calculate_cache_hit_rate()
            
            if hit_rate >= 80:
                return "Excellent"
            elif hit_rate >= 60:
                return "Good"
            elif hit_rate >= 40:
                return "Fair"
            else:
                return "Poor"
                
        except Exception:
            return "Unknown"
    
    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """
        Tendências de performance nas últimas N horas
        """
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            with self.monitor._lock:
                recent_metrics = [
                    m for m in self.monitor._metrics 
                    if m.timestamp >= cutoff
                ]
            
            # Agrupa por hora
            hourly_data = {}
            for metric in recent_metrics:
                hour_key = metric.timestamp.strftime("%H:00")
                
                if hour_key not in hourly_data:
                    hourly_data[hour_key] = {
                        "cpu": [], "memory": [], "transcriptions": 0
                    }
                
                if metric.name == "cpu_usage":
                    hourly_data[hour_key]["cpu"].append(metric.value)
                elif metric.name == "memory_usage":
                    hourly_data[hour_key]["memory"].append(metric.value)
                elif metric.name == "transcription_duration":
                    hourly_data[hour_key]["transcriptions"] += 1
            
            # Calcula médias
            trends = []
            for hour, data in sorted(hourly_data.items()):
                trends.append({
                    "hour": hour,
                    "cpu_avg": sum(data["cpu"]) / len(data["cpu"]) if data["cpu"] else 0,
                    "memory_avg": sum(data["memory"]) / len(data["memory"]) if data["memory"] else 0,
                    "transcriptions": data["transcriptions"]
                })
            
            return {
                "status": "success",
                "period": f"Last {hours} hours",
                "data": trends
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def export_report(self, format: str = "json") -> Dict[str, Any]:
        """
        Exporta relatório completo para análise
        """
        try:
            report_content = self.monitor.export_metrics_report(format)
            
            # Salva arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.{format.lower()}"
            report_path = Path("storage/reports") / filename
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            return {
                "status": "success",
                "message": f"Report exported to {report_path}",
                "file_path": str(report_path),
                "size_kb": len(report_content) / 1024
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


def main():
    """
    Ponto de entrada CLI para Raycast
    """
    parser = argparse.ArgumentParser(description="MeetingScribe Performance Metrics CLI")
    parser.add_argument("command", choices=[
        "dashboard", "status", "transcription", "cache", "trends", "export"
    ], help="Command to execute")
    parser.add_argument("--format", default="json", help="Output format")
    parser.add_argument("--hours", type=int, default=24, help="Hours for trends")
    
    args = parser.parse_args()
    
    cli = RaycastMetricsCLI()
    
    # Executa comando
    if args.command == "dashboard":
        result = cli.get_dashboard_data()
    elif args.command == "status":
        result = cli.get_system_status()
    elif args.command == "transcription":
        result = cli.get_transcription_metrics()
    elif args.command == "cache":
        result = cli.get_cache_status()
    elif args.command == "trends":
        result = cli.get_performance_trends(args.hours)
    elif args.command == "export":
        result = cli.export_report(args.format)
    else:
        result = {"status": "error", "message": "Unknown command"}
    
    # Output JSON para Raycast
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()