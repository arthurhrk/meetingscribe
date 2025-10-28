# MeetingScribe

Local-first audio recording + transcription helper with a Raycast extension. This repo is organized to make it easy to install and to use only what is needed by the Raycast commands.

The Raycast extension focuses on these functions:
- Start Recording (system loopback or microphone)
- Recording Status (quick sanity and tips)
- Recent Recordings (open/export items)
- Import Google (helper script you can run from the repo)
- Transcript Status (basic visibility of files present)

If you just want to use the Raycast commands, you only need Python + a few dependencies and to point the extension to this repo folder.

## 1) Requirements

- Windows 10/11 or macOS (Raycast only runs on macOS; Python pieces also run on Windows)
- Python 3.10+
- Pip
- Node.js 18+ (for the Raycast extension dev/build)
- Raycast (macOS) with developer CLI installed

Audio deps (Windows):
- `pyaudiowpatch` (WASAPI loopback support)

## 2) Install (Python side)

From the repo root:

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

Notes:
- If you only want recording via the Raycast command, the key libs are `pyaudiowpatch` and `loguru` on Windows. The `requirements.txt` covers them.
- Loopback (system audio) on Windows depends on WASAPI; make sure your audio driver is active. If no system audio is playing, loopback may produce an almost-empty file; the tool falls back to microphone automatically in “auto” mode.

## 3) Install (Raycast extension)

On macOS with Raycast installed:

```bash
cd raycast-extension
npm install
npm run dev   # or: ray develop
```

Then in Raycast, open the extension preferences and set:
- `pythonPath`: e.g., `python` (or full path to your venv Python)
- `projectPath`: path to this repo root

The extension uses `quick_record.py` from the repository to record.

## 4) Commands overview (Raycast)

- Start Recording
  - Starts a new audio capture. In “auto” mode it prefers loopback (system audio); if it sees no frames, it falls back to microphone. You’ll see toasts for started/saved.
  - Files stored in `storage/recordings` as WAV.

- Recording Status
  - Shows basic info/tips for troubleshooting and quick checks.

- Recent Recordings
  - Lists recent items from `storage/recordings`. You can open or export.

- Import Google (script)
  - Use `import-google.py` from the repo root for Google-related imports. You can wrap it in Raycast (custom script command) or run by terminal.

- Transcript Status
  - Shows presence of transcript files in `storage/transcriptions` (if you use transcription flows).

## 5) Quick terminal checks

- Record 5s (loopback/mic auto):
```bash
python quick_record.py 5
```
Expected: prints a JSON line immediately and creates a WAV in `storage/recordings` within ~8–9s.

- Force loopback (play some audio):
```bash
python quick_record.py 10 --input loopback
```

- Force microphone:
```bash
python quick_record.py 10 --input mic
```

## 6) Repository layout (focused)

- `raycast-extension/` – the Raycast extension (icon, commands, UI)
- `quick_record.py` – fast recording script used by the extension
- `audio_recorder.py`, `device_manager.py`, `config.py` – core Python recorder + device selection
- `storage/` – output folders for recordings/transcriptions
- `requirements.txt` – Python dependencies
- `import-google.py` – helper for Google imports
- Other folders/files – kept for reference or future work (organized under descriptive names like `archive/`, `docs/`, etc.). Nothing is deleted.

## 7) Troubleshooting

- Icon not updating in Raycast
  - The extension uses `raycast-extension/icon.png`. If it doesn’t refresh, run `ray build -e dist` and restart Raycast.

- JSON manifest error on `npm run dev`
  - Ensure `raycast-extension/package.json` is valid UTF-8 (no BOM). This repo commits it as UTF-8 without BOM.

- No audio saved / tiny files
  - Loopback requires something to be playing. In “auto”, the recorder switches to microphone if loopback is silent.

## 8) License

MIT
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
python -m cli record 30

# Check system status
python -m cli status
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
python -m cli record 30

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
