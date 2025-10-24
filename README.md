# MeetingScribe

**High-quality audio recording for Teams meetings with instant Raycast access.**

Record Microsoft Teams meetings with professional-grade audio quality (48kHz, 16-bit) using WASAPI loopback capture. Launch recordings instantly via Raycast with a simple keyboard shortcut.

## Features

- **Instant Recording**: Start recording with a single Raycast command
- **High-Quality Audio**: WASAPI loopback capture at 48kHz for crystal-clear audio
- **Smart Device Detection**: Automatically selects the best audio device
- **Teams Integration**: Designed specifically for Microsoft Teams meetings
- **100% Local**: All processing happens on your machine, no cloud services

## Quick Start (Windows)

### Prerequisites
- Windows 10/11 (WASAPI support)
- Python 3.10+
- 4GB+ RAM recommended
- Raycast for Windows (or macOS with Windows bridge)

### Installation

1. **Clone and setup Python environment:**
```bash
git clone https://github.com/yourusername/meetingscribe.git
cd meetingscribe

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. **Test your setup:**
```bash
python system_check.py
```

3. **Install Raycast Extension:**
```bash
cd raycast-extension
npm install
npm run dev
```

4. **Configure Raycast:**
   - Open Raycast preferences
   - Find MeetingScribe extension
   - Set `Project Path` to your MeetingScribe directory
   - Set `Python Path` to `./venv/Scripts/python.exe` (or just `python`)

## Usage

### Via Raycast (Recommended)

1. Open Raycast (⌘+Space or Alt+Space)
2. Type "Start Recording"
3. Select duration (30s, 1min, 5min, 10min, 30min)
4. Recording starts automatically!

Files are saved to: `storage/recordings/`

### Via CLI

```bash
# Quick record for 30 seconds
python -m src.cli.main record 30

# Check system status
python -m src.cli.main status
```

## Project Structure

```
meetingscribe/
├── src/
│   ├── audio/              # Audio recording engine
│   │   ├── recorder.py     # Core AudioRecorder class
│   │   └── devices.py      # Device detection and management
│   ├── teams/              # Teams integration
│   │   └── detector.py     # Teams process detection
│   └── cli/                # Command-line interface
│       └── main.py         # CLI entry point
│
├── raycast-extension/      # Raycast launcher
│   └── src/
│       ├── record.tsx      # Start recording command
│       ├── recent.tsx      # View recent recordings
│       └── status.tsx      # System status
│
├── storage/
│   └── recordings/         # Audio files (WAV)
│
├── config.py               # Configuration
├── system_check.py         # System diagnostics
└── requirements.txt        # Python dependencies
```

## Configuration

Edit [config.py](config.py) to customize:

```python
# Audio quality settings
audio_sample_rate = 48000   # Hz (CD quality)
audio_channels = 2          # Stereo
audio_format = paInt16      # 16-bit depth

# Storage locations
recordings_dir = "storage/recordings"
logs_dir = "logs"
```

## Raycast Commands

### 1. Start Recording
Launch audio recording with selectable duration.
- **Keywords**: record, gravação, audio, meeting

### 2. Recent Recordings
View and manage your recent recordings.
- **Keywords**: recent, recordings, histórico

### 3. System Status
Check audio devices and system health.
- **Keywords**: status, system, devices

## Troubleshooting

### No audio devices found
- Run `python system_check.py` to diagnose
- Ensure WASAPI is enabled (Windows Audio)
- Try installing: `pip install pyaudiowpatch`

### Recording file not created
- Check `logs/meetingscribe.log` for errors
- Verify `storage/recordings/` directory exists
- Ensure sufficient disk space

### Raycast can't find Python
- Use full path: `C:\path\to\venv\Scripts\python.exe`
- Or activate venv first: `venv\Scripts\activate`

### Permission issues
- Run as Administrator (once) to configure audio access
- Check antivirus isn't blocking audio capture

## Technical Details

### Audio Capture
- **Method**: WASAPI Loopback
- **Quality**: 48kHz, 16-bit, Stereo
- **Format**: WAV (uncompressed)
- **Latency**: < 100ms

### System Requirements
- **CPU**: Any modern dual-core processor
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: ~10MB per minute of audio (stereo WAV)
- **OS**: Windows 10 (1809+) or Windows 11

## Development

See [CLAUDE.md](CLAUDE.md) for development guidelines and architecture details.

### Common commands:
```bash
# Install dev dependencies
pip install -r requirements.txt

# Run system check
python system_check.py

# Test recording (30 seconds)
python -m src.cli.main record 30

# Build Raycast extension
cd raycast-extension && npm run build
```

## Archive

Previous versions and experimental features are archived in:
- `archive/scripts/` - Old recording implementations
- `archive/v2-architecture/` - Client-daemon architecture experiments
- `archive/docs/` - Historical troubleshooting documentation

## License

MIT License - see [LICENSE](LICENSE)

## Contributing

This is a focused tool for Teams recording. If you'd like to contribute:
1. Keep it simple and focused on high-quality audio recording
2. Maintain Windows WASAPI as the primary capture method
3. Ensure Raycast integration remains smooth and fast

---

**Made with focus on quality and simplicity.**
