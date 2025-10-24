# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Focus

**MeetingScribe** is a focused tool for **high-quality Teams meeting audio recording** via Raycast.

**Core Purpose**: Record Microsoft Teams meetings with professional WASAPI audio quality, launched instantly via Raycast.

**NOT included**: Transcription, speaker detection, AI processing (focused purely on recording).

## Common Development Commands

### Python Application
```bash
# Run system check and diagnostics
python system_check.py

# Quick test recording (5 seconds)
python -m src.cli.main record 5

# Record for specific duration
python -m src.cli.main record 30  # 30 seconds
python -m src.cli.main record 300 # 5 minutes

# Check system status
python -m src.cli.main status

# Install dependencies
pip install -r requirements.txt

# Run with virtual environment (recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
```

### Raycast Extension (raycast-extension/)
```bash
# Development commands
npm run dev          # Start development mode
npm run build        # Build extension
npm run lint         # Check code style
npm run fix-lint     # Fix linting issues

# Testing Raycast commands
npx ray develop      # Development mode
npx ray build -e dist # Build for distribution
```

### Testing
```bash
# System verification
python system_check.py

# Test audio module
python -c "from src.audio import AudioRecorder; print('✓ Audio system ready')"

# Test device detection
python -c "from src.audio import DeviceManager; dm = DeviceManager(); print(f'✓ Found {len(dm.list_devices())} devices')"

# Quick 5-second test record
python -m src.cli.main record 5
```

## Architecture Overview

### Core Application Structure
Focused dual-platform audio recording system:
- **Python Core**: WASAPI audio recording engine with CLI interface
- **Raycast Extension**: TypeScript-based instant launcher

### Key Components

#### Python Core (`src/`)
- **`src/audio/recorder.py`** - Core AudioRecorder class (WASAPI capture)
- **`src/audio/devices.py`** - DeviceManager for device detection and selection
- **`src/teams/detector.py`** - Teams process detection (optional feature)
- **`src/teams/integration.py`** - Teams integration helpers
- **`src/cli/main.py`** - CLI entry point with quick_record() function

#### Root Directory Essentials
- **`config.py`** - Centralized configuration (audio settings, paths)
- **`system_check.py`** - System diagnostics and health checks
- **`requirements.txt`** - Minimal dependencies for audio recording

#### Storage Structure
- `storage/recordings/` - WAV audio files (48kHz, 16-bit, stereo)
- `logs/` - Application logs with rotation (Loguru)

#### Raycast Integration
- **3 focused commands**:
  1. `record.tsx` - Start recording (main command)
  2. `recent.tsx` - View recent recordings
  3. `status.tsx` - System and device status
- JSON-based communication protocol
- Calls Python CLI via spawn process

### Configuration System
Uses Pydantic BaseSettings with `.env` file support:
```python
# Audio quality (config.py)
audio_sample_rate = 48000  # Hz (professional quality)
audio_channels = 2         # Stereo
audio_format = paInt16     # 16-bit depth

# Storage
recordings_dir = "storage/recordings"
logs_dir = "logs"
```

### Audio Recording Pipeline
1. **Device Detection**: Auto-select best WASAPI loopback device
2. **WASAPI Capture**: High-quality loopback recording (48kHz, 16-bit)
3. **Background Recording**: Non-blocking thread keeps process alive
4. **WAV Export**: Uncompressed audio saved to storage/recordings/

### Integration Points
- **CLI Arguments**: `python -m src.cli.main record <duration>`
- **JSON Communication**: Python returns JSON to Raycast immediately
- **File System**: Structured storage in `storage/` directory
- **Logging**: Centralized with Loguru, file rotation

## Development Notes

### Dependencies Management
Core dependencies in `requirements.txt`:
```
pyaudiowpatch>=0.2.12.6  # WASAPI support (preferred)
pyaudio>=0.2.11          # Fallback audio
loguru>=0.7.0            # Logging
pydantic>=2.0.0          # Configuration
pydantic-settings>=2.0.0 # Settings management
psutil>=5.9.0            # Process management
wmi>=1.5.1               # Windows Management (Teams detection)
pywin32>=306             # Windows APIs
```

**No AI/ML dependencies**: Removed Whisper, PyAnnote, Torch - this is recording only.

### Cross-Platform Considerations
- **Primary**: Windows 10/11 (WASAPI loopback)
- **Raycast**: Works on Windows; macOS with Wine/bridge
- **Audio**: WASAPI is Windows-specific (core requirement)

### Performance Optimization
Lightweight and fast:
- No model loading (no AI processing)
- Direct WASAPI capture (~10MB/min at 48kHz stereo)
- Instant startup (< 1 second)
- Background threading for non-blocking recording

### Error Handling
Robust error handling for:
- Audio device detection failures
- WASAPI initialization errors
- File system operations
- Disk space validation
- Thread management

## Project Structure

```
meetingscribe/
├── src/
│   ├── audio/              # Core recording engine
│   │   ├── __init__.py
│   │   ├── recorder.py     # AudioRecorder class
│   │   └── devices.py      # DeviceManager class
│   ├── teams/              # Teams integration (optional)
│   │   ├── __init__.py
│   │   ├── detector.py     # Process detection
│   │   └── integration.py  # Helper functions
│   └── cli/                # Command-line interface
│       ├── __init__.py
│       └── main.py         # CLI entry point
│
├── raycast-extension/      # Raycast launcher
│   ├── src/
│   │   ├── record.tsx      # Main: start recording
│   │   ├── recent.tsx      # View recordings
│   │   └── status.tsx      # System status
│   ├── package.json        # 3 commands only
│   └── tsconfig.json
│
├── storage/
│   └── recordings/         # WAV files (48kHz, 16-bit, stereo)
│
├── archive/                # Old code and experiments
│   ├── scripts/           # Previous recording implementations
│   ├── docs/              # Historical documentation
│   └── v2-architecture/   # Archived daemon experiments
│
├── config.py              # Configuration (audio, paths)
├── system_check.py        # Diagnostics
├── requirements.txt       # Python dependencies
├── README.md             # User documentation
└── CLAUDE.md             # This file (dev guide)
```

## Development Workflow

### Adding New Features

1. **Audio Recording**: Modify `src/audio/recorder.py`
2. **Device Detection**: Update `src/audio/devices.py`
3. **CLI Commands**: Extend `src/cli/main.py`
4. **Raycast Commands**: Add to `raycast-extension/src/`

### Testing Changes

```bash
# 1. Test Python changes
python system_check.py
python -m src.cli.main record 5

# 2. Test Raycast integration
cd raycast-extension
npm run dev
# Open Raycast → "Start Recording"

# 3. Verify recording
# Check storage/recordings/ for WAV file
# Play file to verify audio quality
```

### Code Style

- **Python**: PEP 8, type hints encouraged
- **TypeScript**: ESLint config in raycast-extension/
- **Docstrings**: All public functions and classes
- **Comments**: Explain "why", not "what"

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
- [ ] Tested with `system_check.py` and quick recording

### Focus Principles

**This project is FOCUSED on recording only:**

❌ **Do NOT add**:
- Transcription features (removed)
- AI/ML processing (removed)
- Speaker detection (removed)
- Complex pipelines (removed)
- Performance dashboards (removed)

✅ **Do ADD**:
- Audio recording improvements
- Device detection enhancements
- Teams integration features
- Raycast UX improvements
- Recording quality optimizations

### Simplicity Over Complexity

- **Prefer**: Simple, direct solutions
- **Avoid**: Over-engineering, premature optimization
- **Goal**: Fast, reliable audio recording - nothing more

## Common Tasks

### Adding a Raycast Command

1. Create `raycast-extension/src/mycommand.tsx`
2. Add to `raycast-extension/package.json` commands array
3. Implement command logic (call Python CLI if needed)
4. Test with `npm run dev`

### Modifying Audio Quality

Edit [config.py](config.py):
```python
audio_sample_rate = 48000  # Hz (24000, 48000, 96000)
audio_channels = 2         # 1=Mono, 2=Stereo
audio_format = paInt16     # paInt16, paInt24, paInt32
```

### Adding Teams Detection

Teams integration exists in `src/teams/`:
- `detector.py` - Detect running Teams process
- `integration.py` - Helper functions

Example usage:
```python
from src.teams import TeamsDetector

detector = TeamsDetector()
if detector.is_teams_running():
    print("Teams is active")
```

## Archive

Previous implementations and experiments are in `archive/`:

- **`archive/scripts/`**: Old recording scripts (gravar*.py, quick_record*.py)
- **`archive/docs/`**: Historical troubleshooting docs
- **`archive/v2-architecture/`**: Daemon architecture experiments

These are preserved for reference but not active code.

## Troubleshooting for Developers

### Import Errors
```bash
# Ensure you're in project root
cd meetingscribe

# Activate venv
venv\Scripts\activate

# Reinstall
pip install -r requirements.txt
```

### Audio Device Not Found
```bash
# Check system
python system_check.py

# List devices manually
python -c "from src.audio import DeviceManager; dm = DeviceManager(); [print(d.name) for d in dm.list_devices()]"
```

### Raycast Not Working
1. Check Project Path in Raycast settings
2. Use full path to python.exe: `C:\...\venv\Scripts\python.exe`
3. Test CLI works: `python -m src.cli.main record 5`
4. Check logs: `type logs\meetingscribe.log`

---

**Remember**: This is a focused tool. Keep it simple, keep it fast, keep it reliable.
