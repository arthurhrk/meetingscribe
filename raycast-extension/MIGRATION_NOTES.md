# Raycast Extension - Path Migration Notes

## Changes Made After Project Reorganization

The main MeetingScribe project was reorganized, which required updating the Raycast extension paths.

### Python Script Paths Updated

| Old Path (Deleted) | New Approach |
|-------------------|--------------|
| `record_with_status.py` | `python -m cli record <duration>` |
| `record_manual.py` | CLI doesn't support manual mode yet |
| `transcribe_audio.py` | `scripts/import_google.py` |

### Files Modified

1. **`src/record.tsx`**
   - Updated to use CLI interface: `python -m cli record <duration>`
   - Removed references to deleted scripts
   - Manual recording mode disabled (not yet implemented in new CLI)

2. **`src/import-google.tsx`**
   - Updated path: `transcribe_audio.py` → `scripts/import_google.py`
   - Error message updated to reflect new path

3. **`src/recent.tsx`**
   - Updated path: `transcribe_audio.py` → `scripts/import_google.py`

### PYTHONPATH Configuration

All Raycast commands now use `python -m cli` instead of `python -m src.cli.main`. This requires:

1. **Setting PYTHONPATH** to include the `src/` directory
2. **Import Changes** in `src/cli/main.py`:
   - Changed from relative imports: `from ..audio import ...`
   - Changed to absolute imports: `from audio import ...`
   - This allows Python to find modules when `src/` is in PYTHONPATH
3. **Added `src/cli/__main__.py`**:
   - Allows running `python -m cli` directly (instead of `python -m cli.main`)
   - Eliminates RuntimeWarning about module execution
   - Cleaner command syntax

**In Raycast Extension:**
- The spawn() environment automatically sets `PYTHONPATH=src/` in `src/record.tsx`
- This allows the extension to run `python -m cli record <duration>` successfully

**For Command-Line Usage:**
```bash
# Windows (Command Prompt)
set PYTHONPATH=src
python -m cli record 30

# Windows (PowerShell)
$env:PYTHONPATH="src"
python -m cli record 30

# Unix/Linux/macOS
PYTHONPATH=src python -m cli record 30
```

**Why This Change:**
- Cleaner user-facing commands (no "src." prefix)
- Absolute imports work better with PYTHONPATH
- PYTHONPATH is set automatically in Raycast extension
- Consistent with modern Python package conventions

### How Recording Works Now

**Before (old standalone scripts):**
```bash
python record_with_status.py <duration> <quality> <session_id>
```

**After (new CLI interface):**
```bash
python -m cli record <duration>
```

The CLI automatically handles:
- Device selection (WASAPI loopback)
- Quality settings (48kHz stereo by default)
- File naming with timestamps
- JSON status output for Raycast

### How Transcription Works Now

**Before:**
```bash
python transcribe_audio.py <audio_file> --api-key <key> --model <model>
```

**After:**
```bash
python scripts/import_google.py <audio_file> --api-key <key> --model <model>
```

Same functionality, just moved to `scripts/` directory.

### Known Limitations

1. **Manual Recording Mode**: Not yet implemented in the new CLI
   - The old `record_manual.py` had start/stop functionality
   - Current workaround: Recording stops automatically after specified duration
   - Future: Add manual mode support to `cli.main`

2. **Recording Quality**: Currently uses project defaults (48kHz stereo)
   - Old scripts allowed quality selection (quick/standard/professional/high)
   - Future: Add quality parameters to CLI

### Testing Checklist

- [x] Build succeeds (`npm run build`)
- [ ] Start Recording command works
- [ ] Recording completes and saves WAV file
- [ ] Recent Recordings shows files
- [ ] Transcribe Audio with Gemini works
- [ ] System Status shows devices

### Future Improvements

1. Add quality parameter to CLI: `python -m cli record <duration> --quality professional`
2. Add manual mode to CLI: `python -m cli record --manual`
3. Consolidate all Raycast-Python communication through single interface
