"""
Sistema de Exportação de Transcrições
Exporta transcrições em múltiplos formatos (TXT, JSON, SRT, VTT).
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime, timedelta

from loguru import logger

from .transcriber import TranscriptionResult, TranscriptionSegment


class ExportFormat(Enum):
    """Formatos de exportação disponíveis."""
    TXT = "txt"
    JSON = "json"
    SRT = "srt"
    VTT = "vtt"
    XML = "xml"
    CSV = "csv"


class ExportError(Exception):
    """Exceções relacionadas à exportação."""
    pass


class TranscriptionExporter:
    """
    Exportador de transcrições em múltiplos formatos.
    
    Suporta exportação em TXT, JSON, SRT, VTT, XML e CSV
    com metadados completos e timestamps.
    """
    
    def __init__(self, include_metadata: bool = True, include_timestamps: bool = True):
        self.include_metadata = include_metadata
        self.include_timestamps = include_timestamps
        logger.debug(f"Exportador inicializado - Metadata: {include_metadata}, Timestamps: {include_timestamps}")
    
    def export(
        self,
        result: TranscriptionResult,
        output_path: Path,
        format: ExportFormat,
        **kwargs
    ) -> Path:
        """
        Exporta a transcrição no formato especificado.
        
        Args:
            result: Resultado da transcrição
            output_path: Caminho de saída (com ou sem extensão)
            format: Formato de exportação
            **kwargs: Argumentos específicos do formato
            
        Returns:
            Path: Caminho do arquivo exportado
            
        Raises:
            ExportError: Se falhar na exportação
        """
        try:
            # Garantir extensão correta
            if not output_path.suffix:
                output_path = output_path.with_suffix(f".{format.value}")
            elif output_path.suffix[1:] != format.value:
                output_path = output_path.with_suffix(f".{format.value}")
            
            # Criar diretório se não existir
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Exportando transcrição para {format.value.upper()}: {output_path}")
            
            # Chamar método específico do formato
            export_methods = {
                ExportFormat.TXT: self._export_txt,
                ExportFormat.JSON: self._export_json,
                ExportFormat.SRT: self._export_srt,
                ExportFormat.VTT: self._export_vtt,
                ExportFormat.XML: self._export_xml,
                ExportFormat.CSV: self._export_csv
            }
            
            if format not in export_methods:
                raise ExportError(f"Formato não suportado: {format.value}")
            
            export_methods[format](result, output_path, **kwargs)
            
            logger.success(f"Transcrição exportada com sucesso: {output_path}")
            return output_path
        
        except Exception as e:
            error_msg = f"Erro ao exportar transcrição: {str(e)}"
            logger.error(error_msg)
            raise ExportError(error_msg) from e
    
    def _export_txt(self, result: TranscriptionResult, output_path: Path, **kwargs) -> None:
        """Exporta como texto simples."""
        content = []
        
        if self.include_metadata:
            content.extend([
                f"=== TRANSCRIÇÃO ===",
                f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                f"Idioma: {result.language or 'Auto-detectado'}",
                f"Modelo: {result.model_size}",
                f"Duração: {self._format_duration(result.duration)}",
                f"Palavras: {result.word_count}",
                f"Confiança média: {result.confidence_avg:.2f}",
                f"Tempo de processamento: {result.processing_time:.2f}s",
                "=" * 50,
                ""
            ])
        
        if self.include_timestamps:
            content.append(result.formatted_text)
        else:
            content.append(result.full_text)
        
        output_path.write_text("\n".join(content), encoding="utf-8")
    
    def _export_json(self, result: TranscriptionResult, output_path: Path, **kwargs) -> None:
        """Exporta como JSON estruturado."""
        data = {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "language": result.language,
                "model_size": result.model_size,
                "duration": result.duration,
                "word_count": result.word_count,
                "confidence_avg": result.confidence_avg,
                "processing_time": result.processing_time,
                "segment_count": len(result.segments)
            },
            "transcription": {
                "full_text": result.full_text,
                "segments": [
                    {
                        "id": segment.id,
                        "text": segment.text,
                        "start": segment.start,
                        "end": segment.end,
                        "confidence": segment.confidence,
                        "speaker": segment.speaker,
                        "language": segment.language
                    }
                    for segment in result.segments
                ]
            }
        }
        
        # Filtrar metadata se não incluído
        if not self.include_metadata:
            data = {"transcription": data["transcription"]}
        
        output_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def _export_srt(self, result: TranscriptionResult, output_path: Path, **kwargs) -> None:
        """Exporta como SRT (SubRip)."""
        lines = []
        
        for i, segment in enumerate(result.segments, 1):
            start_time = self._seconds_to_srt(segment.start)
            end_time = self._seconds_to_srt(segment.end)
            
            lines.extend([
                str(i),
                f"{start_time} --> {end_time}",
                segment.text.strip(),
                ""
            ])
        
        output_path.write_text("\n".join(lines), encoding="utf-8")
    
    def _export_vtt(self, result: TranscriptionResult, output_path: Path, **kwargs) -> None:
        """Exporta como VTT (WebVTT)."""
        lines = ["WEBVTT", ""]
        
        if self.include_metadata:
            lines.extend([
                f"NOTE Transcrição gerada em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                f"NOTE Idioma: {result.language or 'Auto-detectado'}",
                f"NOTE Modelo: {result.model_size}",
                f"NOTE Duração: {self._format_duration(result.duration)}",
                ""
            ])
        
        for segment in result.segments:
            start_time = self._seconds_to_vtt(segment.start)
            end_time = self._seconds_to_vtt(segment.end)
            
            lines.extend([
                f"{start_time} --> {end_time}",
                segment.text.strip(),
                ""
            ])
        
        output_path.write_text("\n".join(lines), encoding="utf-8")
    
    def _export_xml(self, result: TranscriptionResult, output_path: Path, **kwargs) -> None:
        """Exporta como XML estruturado."""
        root = ET.Element("transcription")
        
        if self.include_metadata:
            metadata = ET.SubElement(root, "metadata")
            ET.SubElement(metadata, "exported_at").text = datetime.now().isoformat()
            ET.SubElement(metadata, "language").text = result.language or "auto"
            ET.SubElement(metadata, "model_size").text = result.model_size
            ET.SubElement(metadata, "duration").text = str(result.duration)
            ET.SubElement(metadata, "word_count").text = str(result.word_count)
            ET.SubElement(metadata, "confidence_avg").text = str(result.confidence_avg)
            ET.SubElement(metadata, "processing_time").text = str(result.processing_time)
        
        segments_elem = ET.SubElement(root, "segments")
        
        for segment in result.segments:
            seg_elem = ET.SubElement(segments_elem, "segment")
            seg_elem.set("id", str(segment.id))
            seg_elem.set("start", str(segment.start))
            seg_elem.set("end", str(segment.end))
            seg_elem.set("confidence", str(segment.confidence))
            
            if segment.speaker:
                seg_elem.set("speaker", segment.speaker)
            if segment.language:
                seg_elem.set("language", segment.language)
            
            seg_elem.text = segment.text
        
        # Escrever XML formatado
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
    
    def _export_csv(self, result: TranscriptionResult, output_path: Path, **kwargs) -> None:
        """Exporta como CSV."""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['id', 'start', 'end', 'duration', 'text', 'confidence', 'speaker', 'language']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for segment in result.segments:
                writer.writerow({
                    'id': segment.id,
                    'start': segment.start,
                    'end': segment.end,
                    'duration': segment.end - segment.start,
                    'text': segment.text.strip(),
                    'confidence': segment.confidence,
                    'speaker': segment.speaker or '',
                    'language': segment.language or ''
                })
    
    def _seconds_to_srt(self, seconds: float) -> str:
        """Converte segundos para formato SRT (HH:MM:SS,mmm)."""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def _seconds_to_vtt(self, seconds: float) -> str:
        """Converte segundos para formato VTT (HH:MM:SS.mmm)."""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{milliseconds:03d}"
    
    def _format_duration(self, seconds: float) -> str:
        """Formata duração em formato legível."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h{minutes:02d}m{secs:02d}s"
        elif minutes > 0:
            return f"{minutes}m{secs:02d}s"
        else:
            return f"{secs}s"


# Funções de conveniência
def export_transcription(
    result: TranscriptionResult,
    output_path: Path,
    format: ExportFormat,
    include_metadata: bool = True,
    include_timestamps: bool = True,
    **kwargs
) -> Path:
    """
    Função de conveniência para exportar transcrição.
    
    Args:
        result: Resultado da transcrição
        output_path: Caminho de saída
        format: Formato de exportação
        include_metadata: Se deve incluir metadados
        include_timestamps: Se deve incluir timestamps
        **kwargs: Argumentos específicos do formato
        
    Returns:
        Path do arquivo exportado
    """
    exporter = TranscriptionExporter(include_metadata, include_timestamps)
    return exporter.export(result, output_path, format, **kwargs)


def save_transcription_txt(result: TranscriptionResult, output_path: Path) -> Path:
    """Salva como TXT."""
    return export_transcription(result, output_path, ExportFormat.TXT)


def save_transcription_json(result: TranscriptionResult, output_path: Path) -> Path:
    """Salva como JSON."""
    return export_transcription(result, output_path, ExportFormat.JSON)


def save_transcription_srt(result: TranscriptionResult, output_path: Path) -> Path:
    """Salva como SRT."""
    return export_transcription(result, output_path, ExportFormat.SRT)


def save_transcription_vtt(result: TranscriptionResult, output_path: Path) -> Path:
    """Salva como VTT."""
    return export_transcription(result, output_path, ExportFormat.VTT)