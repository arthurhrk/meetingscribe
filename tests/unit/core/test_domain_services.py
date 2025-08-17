"""
Unit tests for domain services in src/core/domain_services.py.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime

# Mock objects from the interfaces to avoid real dependencies
from src.interfaces import AudioFile, TranscriptionResult, RecordingSession, WhisperModelSize, TranscriptionSegment

# Class to test
from src.core.domain_services import AudioProcessingService, TranscriptionQualityService, WorkflowOrchestrationService

@pytest.fixture
def mock_audio_file():
    """Fixture for a mock AudioFile."""
    return AudioFile(
        path=Path("/fake/path/test.wav"),
        filename="test.wav",
        size_bytes=16000 * 2 * 10, # 10 seconds
        duration_seconds=10.0,
        sample_rate=16000,
        channels=1,
        format="wav",
        created_at=datetime.now(),
        metadata={}
    )

@pytest.fixture
def mock_transcription_result():
    """Fixture for a mock TranscriptionResult."""
    return TranscriptionResult(
        job_id="job-123",
        full_text="Hello world this is a test.",
        language="en",
        confidence_average=0.95,
        total_duration=10.0,
        processing_time=5.0,
        word_count=6,
        speakers_detected=[],
        segments=[
            TranscriptionSegment(id=1, text="Hello world", start_time=0.5, end_time=4.5, confidence=0.98, speaker_id=None, speaker_name=None),
            TranscriptionSegment(id=2, text="this is a test.", start_time=5.0, end_time=9.5, confidence=0.92, speaker_id=None, speaker_name=None),
        ]
    )

class TestAudioProcessingService:
    """Tests for the AudioProcessingService."""

    def test_initialization(self):
        """Test that the service initializes correctly."""
        service = AudioProcessingService()
        assert service is not None
        assert service.logger is not None

    def test_validate_audio_file(self, mock_audio_file):
        """Test the audio file validation logic."""
        service = AudioProcessingService()
        warnings = service.validate_audio_file(mock_audio_file)
        assert len(warnings) == 0

        # Test with a problematic file
        mock_audio_file.duration_seconds = 0.5
        warnings = service.validate_audio_file(mock_audio_file)
        assert len(warnings) == 1
        assert "less than 1 second" in warnings[0]

    def test_estimate_transcription_time(self, mock_audio_file):
        """Test the transcription time estimation."""
        service = AudioProcessingService(hardware_specs={'performance_score': 100}) # Good hardware
        estimated_time = service.estimate_transcription_time(mock_audio_file, WhisperModelSize.BASE)
        assert estimated_time > 0
        # With good hardware, time should be a fraction of audio duration
        assert estimated_time < mock_audio_file.duration_seconds

    def test_recommend_processing_strategy(self, mock_audio_file):
        """Test the recommendation logic."""
        service = AudioProcessingService()
        recs = service.recommend_processing_strategy(mock_audio_file)
        assert recs['model_size'] == WhisperModelSize.BASE

        # Test with a long audio file
        mock_audio_file.duration_seconds = 1200 # 20 minutes
        recs = service.recommend_processing_strategy(mock_audio_file)
        assert recs['model_size'] == WhisperModelSize.SMALL


class TestTranscriptionQualityService:
    """Tests for the TranscriptionQualityService."""

    def test_calculate_quality_score(self, mock_transcription_result):
        """Test the quality score calculation."""
        service = TranscriptionQualityService()
        score = service.calculate_quality_score(mock_transcription_result)
        assert 80 < score <= 100

    def test_detect_quality_issues(self, mock_transcription_result):
        """Test the quality issue detection."""
        service = TranscriptionQualityService()
        issues = service.detect_quality_issues(mock_transcription_result)
        assert len(issues) == 0

        # Test with a low confidence result
        mock_transcription_result.confidence_average = 0.7
        issues = service.detect_quality_issues(mock_transcription_result)
        assert len(issues) == 1
        assert "Low average confidence" in issues[0]

    def test_suggest_improvements(self, mock_transcription_result):
        """Test the improvement suggestion logic."""
        service = TranscriptionQualityService()
        suggestions = service.suggest_improvements(mock_transcription_result)
        assert len(suggestions) == 1 # No speakers detected
        assert "speaker diarization" in suggestions[0]


@pytest.mark.asyncio
async def test_workflow_orchestration_service():
    """Placeholder test for the orchestration service."""
    # This is a more complex integration-style test and would require more setup.
    # For now, this is a basic placeholder.

    # 1. Setup Mocks
    mock_audio_engine = MagicMock()
    mock_transcription_engine = MagicMock()
    mock_storage_manager = MagicMock()

    # 2. Mock return values
    mock_session = MagicMock(spec=RecordingSession)
    mock_audio_file = MagicMock(spec=AudioFile)
    mock_transcription_job = MagicMock()
    mock_transcription_job.state = "completed"
    mock_transcription_job.result = MagicMock(spec=TranscriptionResult)


    mock_audio_engine.stop_recording.return_value = mock_audio_file
    mock_transcription_engine.transcribe.return_value = mock_transcription_job

    # 3. Instantiate Service
    service = WorkflowOrchestrationService(
        audio_engine=mock_audio_engine,
        transcription_engine=mock_transcription_engine,
        storage_manager=mock_storage_manager
    )

    # 4. Run workflow
    result_job = await service.process_recording_to_transcription(mock_session)

    # 5. Assert calls
    mock_audio_engine.stop_recording.assert_called_once_with(mock_session)
    mock_transcription_engine.transcribe.assert_called_once_with(mock_audio_file)
    mock_storage_manager.save_transcription.assert_called_once_with(
        mock_transcription_job.result, mock_audio_file
    )
    assert result_job is not None
