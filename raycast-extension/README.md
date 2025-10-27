# MeetingScribe Raycast Extension

Record Microsoft Teams meetings with professional-quality audio directly from Raycast.

## Features

- **Start Recording**: Launch high-quality audio recording instantly
- **Recent Recordings**: Browse and manage your recording library
- **Recording Status**: Monitor active recordings in real-time
- **System Status**: Check audio devices and system health
- **Import Google**: Transcribe recordings using Google Gemini (optional)

## Requirements

1. **MeetingScribe** installed and configured
2. **Raycast** (latest version)
3. **Python 3.9+** with virtual environment
4. **Windows 10/11** (required for WASAPI loopback capture)

## Setup

### 1. Install MeetingScribe

```bash
git clone <repository-url>
cd meetingscribe
python scripts/bootstrap.py
```

### 2. Configure Raycast Extension

Open Raycast Extension Preferences and set:

- **Python Path**: Path to your Python executable
  - Example: `.venv\Scripts\python.exe` (Windows)
  - Or full path: `C:\Users\username\meetingscribe\.venv\Scripts\python.exe`

- **Project Path**: Full path to MeetingScribe directory
  - Example: `C:\Users\username\meetingscribe`

### 3. Optional: Google Gemini API

For transcription features:
- Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- Add to preferences: **Google Gemini API Key**

## Usage

### Recording Commands

- **⌘ Space** → Type `Start Recording` → Choose quality and duration
- **⌘ Space** → Type `Recent Recordings` → Browse your files
- **⌘ Space** → Type `Recording Status` → Monitor active recordings
- **⌘ Space** → Type `System Status` → Check audio devices

### Recording Quality Options

- **Quick (16kHz Mono)**: ~2 MB/min - Voice notes
- **Standard (44.1kHz Stereo)**: ~10 MB/min - Balanced
- **Professional (48kHz Stereo)**: ~11 MB/min - Teams meetings (recommended)
- **High (96kHz Stereo)**: ~22 MB/min - Maximum quality

## Troubleshooting

### Python Path Not Found
- Ensure Python Path points to the correct executable
- Use absolute paths for clarity
- On Windows, use forward slashes or escaped backslashes

### Project Path Not Found
- Use the full absolute path to the MeetingScribe directory
- Verify the path exists and contains the `src/` folder

### No Audio Devices
- Run `System Status` command to check WASAPI devices
- Ensure your audio device is connected
- Windows only: WASAPI loopback is required

### Recording Not Capturing Audio
- Play some audio before starting recording
- Check that Teams is using the correct audio device
- Verify loopback device is selected in System Status

## Development

### Local Development

```bash
cd raycast-extension
npm install
npm run dev
```

### Build for Production

```bash
npm run build
npm run lint
```

## License

MIT - Same as the main MeetingScribe project
