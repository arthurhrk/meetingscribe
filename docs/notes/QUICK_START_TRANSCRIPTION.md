# Quick Start: Transcription Feature

## 5-Minute Setup

### 1. Get API Key (2 minutes)
1. Go to https://makersuite.google.com/app/apikey
2. Sign in and create API key
3. Copy the key

### 2. Configure Raycast (1 minute)
1. Open Raycast
2. Type "Recent Recordings"
3. Press `Cmd + ,` for preferences
4. Paste API key in "Google Gemini API Key"
5. Select model: **Gemini 2.0 Flash** (recommended)

### 3. Install Dependencies (2 minutes)
```bash
cd meetingscribe
venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### Transcribe a Recording
1. Open Raycast → "Recent Recordings"
2. Select a recording
3. Press `Cmd + Shift + T`
4. Wait ~1 minute for 30MB file
5. Done! Transcript saved automatically

### View Transcriptions
**Option A**: From "Recent Recordings"
- Look for 📄 icon next to filename
- Press `Cmd + T` to open

**Option B**: From "Transcript Status"
- Open Raycast → "Transcript Status"
- See all transcriptions
- Press `Enter` to open

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Cmd + Shift + T` | Start transcription |
| `Cmd + T` | Open transcript |
| `Cmd + P` | Play audio |

## Tips

✅ **DO**:
- Use Gemini 2.0 Flash for quick transcriptions
- Enable "Optimize Audio" if you have ffmpeg installed
- Transcribe shorter recordings first to test

❌ **DON'T**:
- Don't transcribe very long meetings (>2 hours) without optimization
- Don't use on slow/unstable connections
- Don't forget to configure API key first

## Troubleshooting

**"API Key Missing"**
→ Configure key in Raycast preferences (`Cmd + ,`)

**"Connection Error"**
→ Try different network (not corporate VPN)
→ Enable audio optimization

**"Takes too long"**
→ Use Gemini 2.0 Flash instead of Pro
→ Enable audio optimization

## Next Steps

- Read full documentation: [TRANSCRIPTION_FEATURE.md](TRANSCRIPTION_FEATURE.md)
- Configure audio optimization
- Try both models to compare quality

---

**Need help?** Check [TRANSCRIPTION_FEATURE.md](TRANSCRIPTION_FEATURE.md) for detailed troubleshooting.
