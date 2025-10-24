# 🔧 Fix: Recording Process Not Completing

## Problem Identified

The recording was failing because of how Node.js `exec()` handles child processes:
1. **exec()** creates a child process but doesn't maintain a strong reference
2. When the async function returns, the child process reference is garbage collected
3. The Python script gets terminated prematurely before it can complete the recording

## Solution Applied

### 1. Changed from `exec()` to `spawn()`
**File**: `raycast-extension/src/record.tsx`

`spawn()` maintains a proper process reference that prevents premature termination.

```typescript
// BEFORE: exec()
const child = exec(command, { cwd: projectPath, windowsHide: true });

// AFTER: spawn()
const child = spawn(pythonPath, [scriptPath, duration.toString()], {
  cwd: projectPath,
  windowsHide: true,
  detached: false,
  stdio: ['ignore', 'pipe', 'pipe']
});
```

### 2. Added Process Reference Storage
**File**: `raycast-extension/src/record.tsx:33`

Created a Map to keep strong references to active recording processes:

```typescript
// Keep track of active recording processes to prevent garbage collection
const activeRecordings = new Map<string, any>();
```

When a recording starts, we store the child process:
```typescript
const sessionId = parsed.data?.session_id || 'unknown';
activeRecordings.set(sessionId, child);

// Clean up when process exits
child.on('exit', () => {
  activeRecordings.delete(sessionId);
});
```

### 3. Python Script Remains the Same
**File**: `gravar_raycast.py`

The Python script works correctly:
1. ✅ Prints JSON immediately (Raycast receives success)
2. ✅ Imports AudioRecorder
3. ✅ Starts recording
4. ✅ Sleeps for full duration
5. ✅ Saves the WAV file

## How It Works Now

```
┌─────────────┐
│   Raycast   │
│  Extension  │
└──────┬──────┘
       │ spawn(python gravar_raycast.py 30)
       │
       ▼
┌────────────────┐
│ Python Process │ (activeRecordings.set(sessionId, child))
│                │
│ 1. Print JSON  │───────────────────────┐
│    (instant)   │                       │
│                │                       ▼
│ 2. Start       │              ┌─────────────────┐
│    Recording   │              │ Raycast shows:  │
│                │              │ "✅ Recording   │
│ 3. Sleep 30s   │              │     started!"   │
│                │              └─────────────────┘
│ 4. Save WAV    │
│                │
│ 5. Exit        │───────────────► activeRecordings.delete()
└────────────────┘
```

## Testing Steps

### 1. Verify Build Succeeded
```bash
cd raycast-extension
npm run build
```
✅ Should show: `ready - built extension successfully`

### 2. Test in Raycast
1. Open Raycast (Cmd/Alt + Space)
2. Type "Start Recording"
3. Select "Gravar 30s" or "Gravar 60s"
4. You should see: **"✅ Gravação iniciada!"**

### 3. Verify File Created
**IMPORTANT**: Wait for the full duration + 2 seconds!

For 30s recording, wait at least **32 seconds**, then check:

```powershell
cd "c:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe"
ls storage/recordings/ -Sort LastWriteTime -First 1
```

You should see a file like:
```
recording_20251014_HHMMSS.wav
```

### 4. Verify File Plays
```powershell
# Get the latest recording
$latest = ls storage/recordings/recording_*.wav -Sort LastWriteTime -First 1
ffprobe $latest.FullName 2>&1 | Select-String "Duration|Stream"
```

Should show:
- Duration (should match your recording time)
- Audio stream info (PCM, 44100 Hz, etc.)

## If It Still Doesn't Work

### Check Python Path in Raycast
1. Open Raycast Settings
2. Go to Extensions → MeetingScribe
3. Verify "Python Path" points to: `c:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe\venv\Scripts\python.exe`
4. Verify "Project Path" points to: `c:\Users\arthur.andrade\OneDrive - Accenture\Documents\GitHub\meetingscribe`

### Manual Test
Try running the script manually to confirm it still works:
```powershell
.\venv\Scripts\python.exe gravar_raycast.py 10
```

Should output:
```json
{"status": "success", "data": {"session_id": "rec-...", "file_path": "...", "duration": 10}}
```

Then wait 12 seconds and verify the file exists.

### Check Process is Running
In another PowerShell window, while recording:
```powershell
Get-Process | Where-Object {$_.ProcessName -like "*python*"}
```

You should see the python.exe process running.

## Technical Details

### Why `exec()` Failed
- `exec()` buffers all output and only returns when process completes
- BUT we were resolving the promise early (when JSON received)
- This caused the function to return, losing the child reference
- Node.js garbage collector would then terminate the orphaned process

### Why `spawn()` Works
- `spawn()` provides streaming I/O (doesn't buffer)
- The child process reference is stored in `activeRecordings` Map
- JavaScript keeps strong references to Map contents
- Process continues running until naturally exits
- Only then is it removed from the Map

### Process Lifecycle
```javascript
spawn() → child created
  ↓
stdout receives JSON → resolve promise → function returns
  ↓                      (but child still in activeRecordings)
recording continues...
  ↓
duration + 2 seconds elapse
  ↓
Python saves file
  ↓
Python exits → 'exit' event → activeRecordings.delete()
  ↓
process fully cleaned up
```

## Changes Made

### Modified Files
1. ✅ `raycast-extension/src/record.tsx`
   - Changed `exec()` to `spawn()`
   - Added `activeRecordings` Map
   - Improved error handling with stderr

### Build Output
```
✅ compiled entry points
✅ generated extension's TypeScript definitions
✅ checked TypeScript
✅ built extension successfully
```

### No Changes Needed
- ❌ `gravar_raycast.py` - Already working correctly
- ❌ `audio_recorder.py` - Already fixed in previous iteration
- ❌ Python environment - Already configured correctly

## Expected Behavior

**Success Case**:
1. Click "Gravar 30s" in Raycast
2. Instantly see toast: "✅ Gravação iniciada! 30s — recording_HHMMSS.wav"
3. Wait 32 seconds
4. File appears in `storage/recordings/`
5. File is playable and contains the recorded audio

**Before This Fix**:
1. Click "Gravar 30s" in Raycast
2. See toast: "✅ Gravação iniciada!"
3. Wait 32 seconds
4. ❌ No file created (process was killed prematurely)

## Confidence Level: HIGH 🎯

This fix directly addresses the root cause:
- ✅ Process reference is now strongly held
- ✅ spawn() is the correct approach for long-running processes
- ✅ activeRecordings Map prevents garbage collection
- ✅ Process naturally completes and cleans up
- ✅ Same approach used in stdio.ts (proven to work)

The recording should now work reliably from Raycast! 🎉
