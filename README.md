# MeetingScribe

**High-quality Teams meeting audio recorder** - Launch instantly via Raycast.

A focused tool for recording Microsoft Teams meetings with professional WASAPI audio quality.

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

**Command Line:**
```bash
# Record for 30 seconds (default)
python -m cli record 30

# Record for 5 minutes
python -m cli record 300

# Check system status
python -m cli status
```

**Raycast Extension:**
1. Import extension from `raycast-extension/`
2. Use command: "Start Recording"
3. Recordings saved to `storage/recordings/`

## Project Structure

```
meetingscribe/
├── src/                      # Core application
│   ├── audio/               # Recording engine (WASAPI)
│   ├── teams/               # Teams integration
│   ├── cli/                 # Command-line interface
│   └── config.py            # Configuration management
│
├── scripts/                  # Utility scripts
│   ├── bootstrap.py         # Setup and installation
│   ├── system_check.py      # System diagnostics
│   └── import_google.py     # Google transcription import
│
├── raycast-extension/        # Raycast launcher
│   └── src/                 # TypeScript commands
│
├── storage/                  # Runtime data
│   ├── recordings/          # WAV audio files
│   └── logs/                # Application logs
│
├── docs/                     # Documentation
│   ├── USER_GUIDE.md        # User documentation
│   ├── DEVELOPMENT.md       # Developer guide
│   └── ARCHITECTURE.md      # System design
│
├── tests/                    # Test suite
├── archive/                  # Historical code
├── tools/                    # Development tools
│
├── .env.example              # Configuration template
├── pyproject.toml            # Python project metadata
└── requirements.txt          # Python dependencies
```

## Features

✅ **High-Quality Audio**: 48kHz, 16-bit, stereo WASAPI recording
✅ **Instant Launch**: Raycast integration for quick access
✅ **Teams Optimized**: Automatic loopback device selection
✅ **Lightweight**: No AI/ML dependencies, fast startup
✅ **Professional**: Uncompressed WAV output

## Documentation

- **User Guide**: [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - Installation and usage
- **Developer Guide**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) - Contributing and development
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design

## Requirements

- **OS**: Windows 10/11 (WASAPI loopback)
- **Python**: 3.9+
- **Dependencies**: See `requirements.txt`

## Focus

**This is a RECORDING-ONLY tool**:
- ✅ Professional audio capture
- ✅ Teams meeting recording
- ✅ WASAPI loopback support
- ❌ No transcription (use import tools)
- ❌ No AI processing
- ❌ No speaker detection

## License

MIT License - See [LICENSE](LICENSE)

## Support

- Issues: [GitHub Issues](https://github.com/yourusername/meetingscribe/issues)
- Documentation: [docs/](docs/)
- System Check: `python scripts/system_check.py`
