"""
Módulo de Transcrição do MeetingScribe
Sistema completo para transcrição de áudio usando Whisper + Speaker Detection.
"""

from .transcriber import (
    WhisperTranscriber,
    TranscriptionResult,
    TranscriptionSegment,
    TranscriptionConfig,
    TranscriptionProgress,
    WhisperModelSize,
    TranscriptionStatus,
    TranscriptionError,
    ModelLoadError,
    create_transcriber,
    transcribe_audio_file
)

from .exporter import (
    TranscriptionExporter,
    ExportFormat,
    export_transcription,
    save_transcription_txt,
    save_transcription_json,
    save_transcription_srt,
    save_transcription_vtt
)

from .speaker_detection import (
    SpeakerDetector,
    SpeakerDetectionProgress,
    SpeakerSegment,
    SpeakerInfo,
    DiarizationResult,
    DiarizationModel,
    SpeakerDetectionError,
    ModelNotAvailableError,
    create_speaker_detector,
    detect_speakers_in_audio,
    merge_transcription_with_speakers
)

from .intelligent_transcriber import (
    IntelligentTranscriber,
    IntelligentTranscriptionConfig,
    IntelligentTranscriptionResult,
    IntelligentProgress,
    create_intelligent_transcriber,
    transcribe_with_speakers
)

__all__ = [
    # Core transcription
    "WhisperTranscriber",
    "TranscriptionResult", 
    "TranscriptionSegment",
    "TranscriptionConfig",
    "TranscriptionProgress",
    
    # Speaker detection
    "SpeakerDetector",
    "SpeakerDetectionProgress",
    "SpeakerSegment",
    "SpeakerInfo",
    "DiarizationResult",
    
    # Intelligent transcription (Whisper + Speakers)
    "IntelligentTranscriber",
    "IntelligentTranscriptionConfig",
    "IntelligentTranscriptionResult",
    "IntelligentProgress",
    
    # Enums
    "WhisperModelSize",
    "TranscriptionStatus",
    "ExportFormat",
    "DiarizationModel",
    
    # Exceptions
    "TranscriptionError",
    "ModelLoadError",
    "SpeakerDetectionError",
    "ModelNotAvailableError",
    
    # Factory functions
    "create_transcriber",
    "transcribe_audio_file",
    "create_speaker_detector",
    "detect_speakers_in_audio",
    "create_intelligent_transcriber",
    "transcribe_with_speakers",
    
    # Integration functions
    "merge_transcription_with_speakers",
    
    # Export functions
    "TranscriptionExporter",
    "export_transcription",
    "save_transcription_txt",
    "save_transcription_json", 
    "save_transcription_srt",
    "save_transcription_vtt"
]