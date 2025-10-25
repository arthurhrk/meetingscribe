# Transcription Feature - Google Gemini Integration

## Overview

MeetingScribe now supports **cloud-based audio transcription** using Google's Gemini API. This feature allows you to automatically transcribe recorded meetings directly from the Raycast extension.

## Features

- **Automatic Transcription**: Transcribe recordings with a single command
- **Model Selection**: Choose between Gemini 2.0 Flash (faster, cheaper) or Gemini 1.5 Pro (more accurate)
- **Audio Optimization**: Optionally reduce file size before upload (16kHz mono WAV)
- **Progress Tracking**: Monitor transcription status in real-time
- **Transcript Management**: View, open, and manage transcriptions

## Setup

### 1. Get Google Gemini API Key

1. Visit https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Create a new API key
4. Copy the API key

### 2. Configure Raycast Extension

1. Open Raycast
2. Search for "MeetingScribe"
3. Press `Cmd + ,` to open preferences
4. Configure the following:
   - **Google Gemini API Key**: Paste your API key
   - **Gemini Model**: Choose your preferred model
     - `Gemini 2.0 Flash`: Faster, cheaper, good for most use cases
     - `Gemini 1.5 Pro`: More accurate, better for complex audio
   - **Optimize Audio**: Enable to reduce file size (requires ffmpeg)

### 3. Install Python Dependencies

```bash
# Activate virtual environment
cd meetingscribe
venv\Scripts\activate

# Install transcription dependencies
pip install -r requirements.txt
```

### 4. (Optional) Install ffmpeg for Audio Optimization

If you want to enable audio optimization for non-WAV files:

```bash
# Windows (using winget)
winget install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

## Usage

### Transcribe from Recent Recordings

1. Open Raycast
2. Search "Recent Recordings"
3. Select a recording
4. Press `Cmd + Shift + T` to transcribe
5. Wait for transcription to complete (notification will appear)

### View Transcriptions

**Method 1: From Recent Recordings**
- Open "Recent Recordings"
- Recordings with transcriptions show a document icon 📄
- Press `Cmd + T` to open the transcript

**Method 2: From Transcript Status**
- Open "Transcript Status" command
- View all transcriptions in one place
- Open transcript or play original audio

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd + Shift + T` | Transcribe selected recording |
| `Cmd + T` | Open transcript (if exists) |
| `Cmd + P` | Play audio (in Transcript Status) |
| `Cmd + Backspace` | Delete transcript |
| `Cmd + C` | Copy transcript path |
| `Cmd + Shift + R` | Refresh list |

## How It Works

### Transcription Pipeline

1. **Audio File Selection**: Choose recording from Recent Recordings
2. **API Key Validation**: Check if Gemini API key is configured
3. **Audio Optimization** (optional):
   - Convert to mono (1 channel)
   - Reduce sample rate to 16kHz
   - Convert to WAV format
   - Reduces file size by ~60-70%
4. **Upload to Gemini**: Upload audio file to Google servers
5. **Processing**: Gemini processes audio on their servers
6. **Transcription**: Gemini model generates text transcription
7. **Save Results**: Save transcript as `.txt` file next to audio
8. **Cleanup**: Remove temporary optimized file (if created)

### File Structure

```
storage/recordings/
├── meeting-2025-01-15.wav          # Original audio
├── meeting-2025-01-15_transcription.txt  # Transcript
├── meeting-2025-01-16.wav
└── meeting-2025-01-16_transcription.txt
```

### Transcript Format

Transcripts are saved as `.txt` files with the following structure:

```
TRANSCRIÇÃO - meeting-2025-01-15.wav
================================================================================
Modelo: models/gemini-2.0-flash-exp
Tempo de upload: 6.8s
Tempo de processamento: 0.0s
Tempo de transcrição: 51.9s
================================================================================

[Transcription text in Portuguese...]
```

## Models Comparison

### Gemini 2.0 Flash (Recommended)
- **Speed**: Very fast (~50-60s for 30MB file)
- **Cost**: Lower cost per request
- **Quality**: Good for most meetings
- **Best for**: General meetings, quick transcriptions

### Gemini 1.5 Pro
- **Speed**: Slower than Flash
- **Cost**: Higher cost per request
- **Quality**: Excellent, better with technical terms
- **Best for**: Important meetings, complex audio, multiple speakers

## Pricing

Google Gemini API pricing (as of 2025):
- **Gemini 2.0 Flash**: Free tier available, then pay-per-use
- **Gemini 1.5 Pro**: Free tier available, then pay-per-use

Check current pricing at: https://ai.google.dev/pricing

## Troubleshooting

### "API Key Missing" Error
**Solution**: Configure API key in Raycast preferences (`Cmd + ,`)

### "Connection Error (503 Service Unavailable)"
**Possible causes**:
- Corporate firewall/proxy blocking Google APIs
- API temporarily unavailable
- File too large for current connection

**Solutions**:
1. Try different network (non-corporate)
2. Enable "Optimize Audio" to reduce file size
3. Wait a few minutes and try again

### "ffmpeg not found" (with audio optimization enabled)
**Solution**: Install ffmpeg or disable audio optimization

### Transcription Takes Too Long
**Solutions**:
1. Use Gemini 2.0 Flash instead of Pro
2. Enable audio optimization
3. Check network speed

### Poor Transcription Quality
**Solutions**:
1. Use Gemini 1.5 Pro instead of Flash
2. Ensure audio recording quality is good
3. Check that audio is clear and not too noisy

## Technical Details

### Python Script: `transcribe_audio.py`

Located in project root, callable from command line:

```bash
python transcribe_audio.py <audio_file> \
  --api-key <key> \
  --model models/gemini-2.0-flash-exp \
  [--optimize] \
  [--timeout 300]
```

**Returns**: JSON response with transcription results

### Raycast Integration

The extension calls the Python script via `spawn` and captures JSON output:

```typescript
const process = spawn(pythonPath, [
  scriptPath,
  audioFilePath,
  "--api-key", apiKey,
  "--model", model,
  ...(optimize ? ["--optimize"] : [])
]);
```

### Audio Optimization Details

When enabled:
- **Input**: Any audio format (WAV, M4A, MP3, etc.)
- **Output**: 16kHz mono WAV
- **Reduction**: Typically 60-70% smaller
- **Quality**: Sufficient for speech transcription
- **Processing time**: ~2-5 seconds for 30MB file

## Privacy & Security

### Data Handling
- Audio files are uploaded to Google servers for processing
- Transcriptions are processed by Google Gemini AI
- Google may retain data according to their privacy policy
- **Recommendation**: Review Google's data handling policies for sensitive meetings

### API Key Security
- API keys are stored in Raycast preferences (encrypted)
- Never committed to version control
- Passed via command-line arguments (not visible in process list)

### Best Practices
1. Use separate API key for each project
2. Rotate API keys regularly
3. Monitor API usage in Google Cloud Console
4. Review transcriptions for sensitive information
5. Delete transcripts after use if they contain confidential data

## Limitations

1. **File Size**: Maximum file size depends on Google API limits (~100MB)
2. **Duration**: Longer recordings take more time to transcribe
3. **Languages**: Optimized for Portuguese, but supports multiple languages
4. **Network**: Requires stable internet connection
5. **Cost**: API usage may incur costs after free tier

## Future Enhancements

- [ ] Real-time transcription progress indicator
- [ ] Batch transcription (multiple files at once)
- [ ] Speaker diarization (identify different speakers)
- [ ] Custom vocabulary for technical terms
- [ ] Export transcripts to other formats (PDF, DOCX)
- [ ] Local transcription option (Whisper model)
- [ ] Transcription editing interface

## Support

For issues or questions:
1. Check [troubleshooting section](#troubleshooting)
2. Review [Google Gemini API docs](https://ai.google.dev/docs)
3. Open an issue on GitHub

## Credits

- **Transcription**: Google Gemini API
- **Audio Processing**: soundfile, scipy, pydub
- **Integration**: MeetingScribe + Raycast
