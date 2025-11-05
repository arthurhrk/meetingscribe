# MeetingScribe

**High-quality Teams meeting audio recorder** - Launch instantly via Raycast.

A streamlined, production-ready tool for recording Microsoft Teams meetings with professional WASAPI audio quality. Lightweight, fast, and focused exclusively on recording.

## Quick Start

### Installation

1. **Clone and setup:**
```bash
git clone <repository-url>
cd meetingscribe
python scripts/bootstrap.py
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env if needed (defaults are optimized for Teams)
```

3. **Verify installation:**
```bash
python scripts/system_check.py
```

### Usage

**Raycast Extension (Recommended):**
1. Import extension from `raycast-extension/`
2. Configure preferences:
   - Python executable path
   - MeetingScribe project directory
   - Optional: Google Gemini API key (for transcription features)
3. Available commands:
   - **"Start Recording"** - Begin recording Teams meeting
   - **"Recent Recordings"** - Browse and manage audio files
   - **"Recording Status"** - Monitor active recording sessions
   - **"Transcription Progress"** - Track transcription jobs (if enabled)
4. Recordings automatically saved to `storage/recordings/`

**Command Line:**
```bash
# Record for 30 seconds
python -m cli record 30

# Record for 5 minutes with M4A format
python -m cli record 300 m4a

# Check system status and audio devices
python -m cli status
```

## Project Structure

```
meetingscribe/
├── src/                          # Core Python application
│   ├── audio/
│   │   ├── recorder.py          # WASAPI audio recording engine
│   │   ├── devices.py           # Audio device detection & selection
│   │   └── __init__.py
│   ├── teams/
│   │   ├── teams_detector.py    # Teams process detection
│   │   ├── integration.py       # Teams integration helpers
│   │   └── __init__.py
│   ├── cli/
│   │   ├── main.py              # CLI entry point & commands
│   │   ├── __main__.py
│   │   └── __init__.py
│   ├── config.py                # Pydantic-based configuration
│   └── transcriber.py           # Audio processing utilities
│
├── raycast-extension/            # Raycast launcher (TypeScript)
│   ├── src/
│   │   ├── record.tsx           # Start recording
│   │   ├── recent.tsx           # Browse recordings
│   │   ├── recording-status.tsx # Monitor recording sessions
│   │   ├── transcription-progress.tsx  # Track transcription
│   │   └── cli.ts               # Python CLI helper
│   ├── package.json
│   └── tsconfig.json
│
├── scripts/                      # Utility scripts
│   ├── bootstrap.py            # Setup & installation
│   └── system_check.py         # System diagnostics
│
├── storage/                      # Runtime data (generated)
│   ├── recordings/             # WAV/M4A audio files
│   ├── logs/                   # Application logs
│   └── transcription/          # Transcription progress
│
├── docs/                         # Documentation
│   ├── USER_GUIDE.md           # Installation & usage
│   ├── DEVELOPMENT.md          # Developer guide
│   ├── ARCHITECTURE.md         # System design
│   └── usage.md
│
├── tests/                        # Test suite
├── tools/                        # Development tools
├── .vscode/                      # VS Code settings
│
├── .env.example                  # Configuration template
├── pyproject.toml               # Python metadata
└── requirements.txt             # Python dependencies
```

## Features

✅ **Professional Audio Quality**: 48kHz, 16-bit, stereo WASAPI loopback recording
✅ **Multiple Formats**: WAV (uncompressed) and M4A (compressed) output options
✅ **Instant Raycast Launch**: Cmd+Space + "Start Recording" quick access
✅ **Auto Device Detection**: Intelligent WASAPI loopback selection
✅ **Real-Time Monitoring**: Live recording status and progress tracking
✅ **Lightweight**: Minimal dependencies, fast startup and low overhead
✅ **Teams Optimized**: Designed for Microsoft Teams meeting capture
✅ **Optional AI Transcription**: Integrate Google Gemini for transcription (separate feature)

## Documentation

- **User Guide**: [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - Installation and usage
- **Developer Guide**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) - Contributing and development
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design

## Requirements

- **OS**: Windows 10/11 (WASAPI loopback)
- **Python**: 3.9+
- **Dependencies**: See `requirements.txt`

## Design Philosophy

**Core Focus**: Exceptional audio capture, nothing else
- ✅ Professional WASAPI loopback recording
- ✅ Teams meeting optimization
- ✅ Configurable duration and formats
- ❌ No transcription (recording only)
- ❌ No speaker detection or analysis
- ❌ No built-in AI processing (optional external transcription)

**Why?** A focused tool does one thing exceptionally well. Record with confidence, transcribe separately with tools of your choice.

## Tech Stack

**Backend (Python)**
- `pyaudiowpatch` - WASAPI loopback support
- `pydantic` - Configuration & data validation
- `loguru` - Advanced logging
- `pywin32` - Windows audio APIs

**Frontend (Raycast Extension)**
- TypeScript & React
- Raycast API
- Real-time status monitoring

## Getting Started

1. Clone repository and run setup:
   ```bash
   python scripts/bootstrap.py
   ```

2. Verify your system:
   ```bash
   python scripts/system_check.py
   ```

3. Import Raycast extension from `raycast-extension/` directory

4. Configure preferences (Python path, project directory, optional API key)

5. Launch recording: `Cmd+Space` → "Start Recording"

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for:
- Development environment setup
- Common commands
- Testing procedures
- Contributing guidelines

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system design, component descriptions, and data flow.

## License

MIT License - See [LICENSE](LICENSE)

## Support & Feedback

- **System Check**: `python scripts/system_check.py` - Diagnose issues
- **Documentation**: [docs/](docs/) - Detailed guides
- **Issues**: Check documentation first, then file issues with system check output
