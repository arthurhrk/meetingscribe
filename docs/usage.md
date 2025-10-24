# MeetingScribe Usage Guide

Complete guide for recording Teams meetings with high-quality audio.

## Table of Contents
- [Getting Started](#getting-started)
- [Recording via Raycast](#recording-via-raycast)
- [Recording via CLI](#recording-via-cli)
- [Managing Recordings](#managing-recordings)
- [Audio Quality Tips](#audio-quality-tips)
- [Troubleshooting](#troubleshooting)

## Getting Started

### First-Time Setup

1. **Verify your system:**
```bash
cd meetingscribe
python system_check.py
```

This checks:
- Python version (3.10+)
- Audio devices available
- WASAPI support
- Required packages

2. **Test a quick recording:**
```bash
python -m src.cli.main record 5
```

This records 5 seconds to `storage/recordings/` as a test.

3. **Configure Raycast:**
   - Open Raycast Settings
   - Go to Extensions → MeetingScribe
   - Set **Project Path**: Full path to your meetingscribe folder
   - Set **Python Path**: `./venv/Scripts/python.exe` or full path

## Recording via Raycast

### Basic Recording

1. **Launch Raycast**: `Alt+Space` (Windows) or `⌘+Space` (Mac)
2. **Type**: "Start Recording"
3. **Choose duration**:
   - 30 seconds (quick test)
   - 60 seconds (1 minute)
   - 2 minutes
   - 5 minutes (typical standup)
   - 10 minutes
   - 15 minutes
   - 30 minutes (typical meeting)

4. **Recording starts automatically**
   - You'll see a success toast notification
   - Recording runs in background
   - File is saved when complete

### During Recording

- **Don't close Raycast** immediately - let it confirm start
- **Teams audio is captured** automatically via loopback
- **Recording continues** even if you close Raycast
- **File saves automatically** to `storage/recordings/`

### After Recording

Check your recordings:
1. Navigate to `storage/recordings/`
2. Files are named: `recording_YYYYMMDD_HHMMSS.wav`
3. Use Raycast "Recent Recordings" to browse

## Recording via CLI

### Quick Record

```bash
# Record for 30 seconds (default)
python -m src.cli.main record

# Record for specific duration (in seconds)
python -m src.cli.main record 60
python -m src.cli.main record 300  # 5 minutes
python -m src.cli.main record 1800 # 30 minutes
```

### Check System Status

```bash
python -m src.cli.main status
```

Shows:
- Available audio devices
- WASAPI loopback devices
- Device channels and capabilities

## Managing Recordings

### File Organization

Recordings are saved to: `storage/recordings/`

Example structure:
```
storage/recordings/
├── recording_20240124_143022.wav  # Jan 24, 2024 at 14:30:22
├── recording_20240124_150000.wav
└── recording_20240125_091500.wav
```

### File Format

- **Format**: WAV (uncompressed)
- **Sample Rate**: 48,000 Hz (48kHz)
- **Bit Depth**: 16-bit
- **Channels**: Stereo (2 channels)
- **Size**: ~10 MB per minute

### Viewing Recent Recordings

Via Raycast:
1. Open Raycast
2. Type "Recent Recordings"
3. Browse, play, or open in file explorer

### Backing Up Recordings

Simple backup script:
```bash
# Copy to backup location
xcopy storage\recordings\*.wav D:\Backups\Recordings\ /D /Y

# Or use robocopy for incremental backup
robocopy storage\recordings D:\Backups\Recordings *.wav /S
```

## Audio Quality Tips

### Best Practices

1. **Use loopback device** (auto-selected)
   - Captures system audio directly
   - No microphone needed
   - Best quality possible

2. **Test before important meetings**
   ```bash
   python -m src.cli.main record 5
   ```
   Verify the WAV file plays correctly

3. **Check Teams audio settings**
   - Ensure Teams audio is not muted
   - Use good quality speakers or headphones
   - Check volume is audible but not distorted

4. **Close unnecessary apps**
   - Reduces CPU usage
   - Prevents audio interference
   - Ensures smooth recording

### Optimizing Quality

Edit `config.py` for custom settings:

```python
# Maximum quality (larger files)
audio_sample_rate = 48000  # 48kHz
audio_channels = 2         # Stereo
audio_format = paInt16     # 16-bit

# Lower quality (smaller files)
audio_sample_rate = 16000  # 16kHz
audio_channels = 1         # Mono
audio_format = paInt16     # 16-bit
```

### Storage Management

| Duration | File Size (48kHz, 16-bit, Stereo) |
|----------|-----------------------------------|
| 5 min    | ~50 MB                           |
| 10 min   | ~100 MB                          |
| 30 min   | ~300 MB                          |
| 60 min   | ~600 MB                          |

**Recommendation**: Keep at least 5GB free space on your drive.

## Troubleshooting

### Recording Not Starting

**Symptom**: Error message when starting recording

**Solutions**:
1. Run system check:
   ```bash
   python system_check.py
   ```

2. Check Python path in Raycast settings:
   - Use full path: `C:\Users\...\meetingscribe\venv\Scripts\python.exe`
   - Or activate venv: `venv\Scripts\activate`

3. Verify audio device:
   ```bash
   python -m src.cli.main status
   ```
   Should show at least one loopback device

### No Audio in Recording

**Symptom**: WAV file created but silent

**Solutions**:
1. **Check Teams audio**:
   - Unmute Teams
   - Ensure participants are speaking
   - Test with system sounds (play a video)

2. **Check device selection**:
   ```bash
   python -m src.cli.main status
   ```
   Look for "loopback" devices - these capture system audio

3. **Test with system audio**:
   - Play music/video while recording
   - Recording should capture any system audio

### File Not Created

**Symptom**: Recording completes but no file in storage/recordings/

**Solutions**:
1. Check directory exists:
   ```bash
   dir storage\recordings
   ```
   If missing: `mkdir storage\recordings`

2. Check disk space:
   ```bash
   wmic logicaldisk get caption,freespace
   ```

3. Check logs:
   ```bash
   type logs\meetingscribe.log | findstr ERROR
   ```

### Raycast Can't Find Python

**Symptom**: "Python not found" or timeout errors

**Solutions**:
1. **Use full path**:
   ```
   C:\Users\YourName\Documents\meetingscribe\venv\Scripts\python.exe
   ```

2. **Verify path**:
   ```bash
   where python
   venv\Scripts\python.exe --version
   ```

3. **Reinstall venv**:
   ```bash
   python -m venv venv --clear
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Poor Audio Quality

**Symptom**: Recording is muffled or distorted

**Solutions**:
1. **Check sample rate** in `config.py`:
   ```python
   audio_sample_rate = 48000  # Use 48kHz for best quality
   ```

2. **Use stereo**:
   ```python
   audio_channels = 2  # Stereo capture
   ```

3. **Check Teams quality**:
   - Teams Settings → Devices → Speaker
   - Disable automatic volume adjustment
   - Set to 100% volume

### Recording Stops Early

**Symptom**: Recording stops before duration ends

**Solutions**:
1. **Check CPU usage**: Close unnecessary apps
2. **Check RAM**: Ensure 2GB+ free
3. **Check disk space**: Need ~10MB per minute
4. **Review logs**:
   ```bash
   type logs\meetingscribe.log
   ```

## Advanced Usage

### Custom Recording Script

Create your own recording script:

```python
from src.audio import AudioRecorder
from pathlib import Path

# Initialize recorder
recorder = AudioRecorder()
recorder.set_device_auto()  # Auto-select best device

# Configure
recorder._config.max_duration = 600  # 10 minutes

# Start recording
recorder.start_recording(filename="my_meeting.wav")

# Recording happens automatically
# File saved to storage/recordings/my_meeting.wav
```

### Batch Recording

Record multiple sessions:

```bash
# Record 3 sessions of 5 minutes each
for /L %i in (1,1,3) do (
  python -m src.cli.main record 300
  timeout /t 60 /nobreak
)
```

### Scheduled Recording

Use Windows Task Scheduler:
1. Create task
2. Trigger: Schedule time
3. Action: `python -m src.cli.main record 1800`
4. Start in: Your meetingscribe directory

---

## Need Help?

- **System issues**: Run `python system_check.py`
- **Check logs**: `logs/meetingscribe.log`
- **Test recording**: `python -m src.cli.main record 5`
- **Review README**: See main [README.md](../README.md)
