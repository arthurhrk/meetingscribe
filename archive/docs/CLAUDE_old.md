# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Python Application
```bash
# Run the main application
python main.py

# Run system check and diagnostics
python system_check.py

# Install dependencies
pip install -r requirements.txt

# Run with virtual environment (recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### Raycast Extension (raycast-extension/)
```bash
# Development commands
npm run dev          # Start development mode
npm run build        # Build extension
npm run lint         # Check code style
npm run fix-lint     # Fix linting issues
npm run publish      # Publish to Raycast Store

# Testing Raycast commands
ray develop          # Development mode
ray build -e dist    # Build for distribution
```

### Testing
```bash
# System verification
python system_check.py

# Test imports and core functionality
python -c "import main; print('✓ All imports successful')"
python -c "from src.transcription import create_transcriber; print('✓ Transcription system ready')"
```

## Architecture Overview

### Core Application Structure
The project is a dual-platform AI transcription system:
- **Python Core**: Main transcription engine with CLI interface (`main.py`)
- **Raycast Extension**: TypeScript-based launcher for macOS users (`raycast-extension/`)

### Key Components

#### Python Core (Root directory)
- `config.py` - Centralized configuration with Pydantic BaseSettings
- `main.py` - Entry point with Rich-based CLI interface
- `audio_recorder.py` - WASAPI audio capture system
- `device_manager.py` - Audio device management
- `system_check.py` - System diagnostics and health checks

#### Transcription Engine (`src/transcription/`)
- `transcriber.py` - Core Whisper integration with faster-whisper
- `exporter.py` - Multi-format export (TXT, JSON, SRT, VTT, XML, CSV)
- `intelligent_transcriber.py` - Advanced features with speaker detection
- `speaker_detection.py` - Speaker identification using pyannote.audio

#### Storage Structure
- `storage/recordings/` - Audio files
- `storage/transcriptions/` - Raw transcription results  
- `storage/exports/` - Exported transcriptions in various formats
- `models/` - Cached Whisper models
- `logs/` - Application logs with rotation

#### Raycast Integration
- Bridge between Python CLI and TypeScript extension
- Commands: record, recent, transcribe, status, export
- JSON-based communication protocol
- Native macOS integration via Raycast API

### Configuration System
Uses Pydantic BaseSettings with `.env` file support:
- Audio settings (sample rate, channels)
- Whisper model configuration (size, language, device)
- Directory paths and storage locations
- Performance optimization settings

### AI Models and Performance
- **Whisper Models**: tiny, base, small, medium, large-v3
- **Speaker Detection**: pyannote.audio integration
- **Device Detection**: Auto GPU/CPU selection
- **Optimization**: Hardware-based performance presets

### Audio Processing Pipeline
1. WASAPI capture (Windows) with loopback device detection
2. Real-time monitoring and quality control
3. Whisper transcription with progress tracking
4. Optional speaker identification
5. Multi-format export with timestamps

### Integration Points
- **CLI Arguments**: JSON-based communication for Raycast
- **File System**: Structured storage in `storage/` directory
- **Logging**: Centralized with Loguru, file rotation
- **Configuration**: Environment variables and settings files

## Development Notes

### Dependencies Management
- Core Python dependencies in `requirements.txt`
- AI models downloaded automatically on first use
- Raycast extension uses standard npm package management

### Cross-Platform Considerations
- Primary support for Windows (WASAPI audio)
- Limited Linux/macOS audio capture capabilities
- Raycast extension is macOS-specific

### Performance Optimization
The system includes intelligent hardware detection and performance presets:
- Automatic GPU/CPU selection
- Model size recommendations based on hardware
- Memory management for large audio files

### Error Handling
Robust error handling throughout:
- Model loading failures with fallback options
- Audio device detection issues
- Transcription errors with detailed logging
- File system operations with proper validation

## Development Golden Rules

### Code Quality Standards
**GOLDEN RULE**: After successfully completing your goal, ask:
```
please clean up the code you worked on, remove any bloat you added, and document it very clearly
```

**Apply this rule to all code work:**
1. **Remove Bloat**: Delete unused imports, variables, functions, and comments
2. **Clean Architecture**: Ensure code follows existing patterns and conventions
3. **Clear Documentation**: Add concise, helpful comments and docstrings
4. **Consistent Style**: Match existing code formatting and naming conventions
5. **No Dead Code**: Remove temporary debugging code, print statements, and unused branches

**Before considering any task complete:**
- [ ] Code is clean and minimal
- [ ] Documentation is clear and helpful
- [ ] Follows project conventions
- [ ] No debugging artifacts remain
- [ ] All functions and classes have proper docstrings