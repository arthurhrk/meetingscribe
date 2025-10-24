# MeetingScribe v2.0 - Detailed Use Cases

> **Real-world scenarios** based on consultant workflow with specific system behaviors.

## 👤 Primary Persona: Arthur - Senior Consultant

**Context**: Conducts 4-8 client meetings daily via Teams, needs professional transcripts for deliverables, values efficiency and quality over features.

---

## 📋 Core Use Cases

### **UC-001: Morning System Check**

#### **Scenario**: Arthur starts his workday
**Frequency**: Daily (once)  
**Duration**: <30 seconds  
**Criticality**: High

#### **Preconditions**
- Windows system boot complete
- MeetingScribe daemon auto-started with Windows
- Raycast extension installed and configured

#### **Main Flow**
1. **System Status Check**
   - Arthur opens Raycast (`Cmd + Space`)
   - Types "meeting" → selects "MeetingScribe Status"
   - System shows: `✅ Ready | Memory: 280MB | Models: base,large loaded`

2. **Quick Configuration Verification**
   - Status shows: `🎧 Audio: USB Headset + Speakers (Loopback)`  
   - Status shows: `🌐 Language: pt-BR (auto-detect enabled)`
   - Status shows: `🏢 Teams Integration: Auto-prompt enabled`

3. **Today's Adjustments** (if needed)
   - If different language expected: `meetingscribe config language es`
   - If different audio setup: auto-detected, no action needed

#### **Expected Results**
- Arthur confirms system ready in <10 seconds
- Any configuration issues clearly displayed
- Confidence to proceed with day's meetings

#### **Alternative Flows**
- **Service Not Running**: Status shows restart option, one-click resolution
- **Model Not Loaded**: Status shows loading progress, estimates completion time
- **Audio Issues**: Status shows detected devices, suggests optimal configuration

---

### **UC-002: Teams Meeting Auto-Detection & Recording**

#### **Scenario**: Arthur joins a client meeting via Teams
**Frequency**: 4-8x daily  
**Duration**: 5-90 minutes per meeting  
**Criticality**: Critical

#### **Preconditions**
- MeetingScribe daemon running
- Teams integration enabled (`auto-prompt` mode)
- Audio devices connected and detected

#### **Main Flow**
1. **Teams Meeting Join**
   - Arthur clicks Teams meeting link or joins via app
   - Teams audio subsystem activates (microphone/speaker access)
   - System detects Teams.exe audio capture within 10 seconds

2. **Smart Recording Prompt**
   - Discrete Windows notification appears:  
     ```
     🎙️ MeetingScribe
     Teams meeting detected. Record this session?
     [Always for Teams] [Yes] [No] [Settings]
     ```
   - Notification times out to "No" after 15 seconds (non-intrusive)

3. **Recording Initiation** (if Yes selected)
   - System icon changes: `🎙️ → 🔴` (recording indicator)
   - Audio capture begins from optimal source:
     - Priority 1: Speakers (Loopback) - captures all participants
     - Priority 2: Microphone Array - captures Arthur's voice
   - No interruption to Teams meeting flow

4. **Background Operation**
   - Recording continues transparently
   - System monitors Teams process health
   - Memory usage tracked, cleanup performed as needed
   - Live audio level monitoring (no storage, just health check)

5. **Meeting End Detection**
   - Teams audio stream ends OR Teams.exe closes
   - System detects end condition within 30 seconds
   - Discrete notification: 
     ```
     🎙️ Recording Complete (42:33)
     Auto-transcribe now? [Yes] [Later] [Delete]
     ```

6. **Post-Meeting Processing**
   - If "Yes": Queues transcription job with current language settings
   - If "Later": Saves recording, adds to pending queue
   - If "Delete": Removes recording file, no transcription
   - Recording file: `~/storage/recordings/2025-01-15_14-30_teams_42m33s.wav`

#### **Expected Results**
- Zero manual setup required
- Professional quality audio captured
- Client meeting uninterrupted by system
- Recording ready for transcription immediately

#### **Alternative Flows**
- **Device Conflict**: Teams uses different device → System adapts, uses next priority
- **Multiple Meetings**: Overlapping meetings → Separate recording sessions
- **Connection Issues**: Teams reconnects → Recording continues seamlessly
- **Battery Low**: System prompts to disable auto-detection until plugged in

---

### **UC-003: Dynamic Audio Device Management**

#### **Scenario**: Arthur's audio setup changes during the day
**Frequency**: 2-4x daily  
**Duration**: Instant adaptation  
**Criticality**: High

#### **Preconditions**
- System monitoring audio device changes
- Device preferences configured or learned
- Active recording may be in progress

#### **Main Flow - Device Connection**
1. **New Device Detection**
   - Arthur connects Bluetooth AirPods
   - Windows system recognizes device within 5 seconds
   - MeetingScribe detects new audio endpoint immediately

2. **Smart Device Switching**
   - System evaluates device priority:
     ```
     Current: USB Headset (microphone + speakers)
     New: AirPods Pro (microphone + speakers + noise cancellation)
     Decision: Switch to AirPods (higher quality profile)
     ```

3. **Seamless Transition**
   - If recording active: Graceful handoff with <2 second gap
   - System icon briefly shows: `🎧 → AirPods Pro`
   - Configuration automatically updated for next session

4. **User Notification**
   - Discrete notification: `🎧 Now using: AirPods Pro`
   - No action required from Arthur
   - Option to "Undo" if switch was undesired

#### **Main Flow - Device Disconnection**
1. **Device Loss Detection**
   - Arthur disconnects USB headset to move to meeting room
   - System detects device removal within 3 seconds
   - Active recording may be affected

2. **Intelligent Fallback**
   - System switches to best available alternative:
     ```
     Lost: USB Headset
     Available: Laptop Speakers, Laptop Microphone, AirPods
     Decision: AirPods Pro (if connected) OR Laptop combo
     ```

3. **Continuity Preservation**
   - Recording continues without interruption
   - Audio quality maintained at highest possible level
   - Gap in recording: <5 seconds maximum

#### **Expected Results**
- Arthur never manually manages audio devices
- System always uses best available audio setup
- Recording quality optimized automatically
- Smooth transitions during meetings

---

### **UC-004: Manual Emergency Recording**

#### **Scenario**: Unexpected important conversation needs recording
**Frequency**: 1-2x weekly  
**Duration**: 2-30 minutes  
**Criticality**: High

#### **Preconditions**
- Raycast accessible
- System daemon running
- Audio devices available

#### **Main Flow**
1. **Emergency Trigger**
   - Client calls unexpectedly with critical information
   - Arthur realizes conversation should be recorded
   - Needs to start recording within 10 seconds

2. **Quick Access via Raycast**
   - Arthur: `Cmd + Space` → "record"
   - Raycast shows: `🎙️ Record Audio`
   - Arthur presses `Enter`

3. **Instant Recording Setup**
   - System shows 3-second countdown: `Recording in 3... 2... 1...`
   - Auto-selects optimal device: `🎧 Using: AirPods Pro (microphone)`
   - Recording begins immediately
   - System icon: `🔴 Recording 00:07`

4. **Live Recording Management**
   - Raycast shortcut available: `Cmd + Space` → "stop recording"
   - Alternative CLI: `Cmd + T` → `meetingscribe stop`
   - System tray icon clickable for quick stop
   - Live timer visible: `🔴 15:43 recording`

5. **Recording Completion**
   - Arthur stops via any method
   - Immediate options displayed:
     ```
     🎙️ Recording Saved (15:43)
     Transcribe now? [Yes] [Yes (Large Model)] [Later]
     Language: [pt-BR ▼] [Auto-detect]
     ```

#### **Expected Results**
- Recording active within 10 seconds of decision
- High-quality audio capture
- Multiple stop methods available
- Immediate transcription options

#### **Alternative Flows**
- **Device Busy**: System prompts for alternative device or shares current
- **Storage Full**: System offers to delete old recordings or change location
- **Background App**: Recording starts even if Arthur switches to other applications

---

### **UC-005: Batch Processing End-of-Day**

#### **Scenario**: Arthur processes all day's recordings before leaving office
**Frequency**: Daily  
**Duration**: 5 minutes setup + background processing  
**Criticality**: Medium

#### **Preconditions**
- Multiple recordings accumulated throughout day
- System has processing capacity available
- Large model loaded or available

#### **Main Flow**
1. **Batch Review**
   - Arthur opens CLI: `meetingscribe recent --pending`
   - System shows:
     ```
     📝 Pending Transcriptions (4 items):
     
     1. teams_14-30_42m33s.wav     [Client A - Strategy]
     2. manual_16-15_08m12s.wav    [Urgent call]  
     3. teams_17-00_35m48s.wav     [Client B - Review]
     4. teams_18-30_22m15s.wav     [Internal standup]
     
     Total: 1h 48m 48s audio
     Est. processing time: 18-25 minutes
     ```

2. **Batch Configuration**
   - Arthur sets preferences:
     ```
     meetingscribe batch-process \
       --language pt-BR \
       --model large-v3 \
       --format txt,srt \
       --organize-by date
     ```

3. **Processing Execution**
   - System queues all items with optimal resource allocation
   - Progress shown: `Processing 1/4: Client A Strategy (42% complete)`
   - Arthur continues other work while processing runs
   - System manages CPU/memory to maintain responsiveness

4. **Completion Notification**
   - System notification:
     ```
     ✅ Batch Processing Complete
     4/4 transcriptions successful
     Saved to: ~/storage/exports/2025-01-15/
     Quality score: 96% average
     ```

5. **Results Review**
   - Files organized:
     ```
     exports/2025-01-15/
     ├── 14-30_client-a-strategy.txt
     ├── 14-30_client-a-strategy.srt
     ├── 16-15_urgent-call.txt
     ├── 17-00_client-b-review.txt
     └── 18-30_internal-standup.txt
     ```

#### **Expected Results**
- All recordings processed with highest quality
- Files organized for easy client delivery
- Arthur's work uninterrupted during processing
- Clear success/failure reporting

---

### **UC-006: Raycast Command Center**

#### **Scenario**: Arthur manages all MeetingScribe functions via Raycast
**Frequency**: 10-15x daily  
**Duration**: 1-5 seconds per command  
**Criticality**: High

#### **Main Flow - Status Check**
```
Cmd + Space → "meeting status" → Enter
🟢 MeetingScribe Ready
├─ 🎧 Audio: AirPods Pro + Speakers (Loopback)
├─ 🌐 Language: pt-BR (auto-detect enabled)  
├─ 📊 Memory: 295MB (2 models loaded)
├─ 🔄 Active: Recording Teams meeting (12:43)
└─ ⏳ Queue: 1 pending transcription
```

#### **Main Flow - Quick Record**
```
Cmd + Space → "record" → Enter
🎙️ Quick Record
├─ Device: AirPods Pro ✓
├─ Language: pt-BR ✓
├─ Quality: Large model ✓
└─ [Start Recording] [Settings] [Cancel]
```

#### **Main Flow - Emergency Stop**
```
Cmd + Space → "stop" → Enter
⏹️ Stop Recording? (15:43 elapsed)
├─ Save & Transcribe Now [Enter]
├─ Save for Later [Cmd+L]  
├─ Delete Recording [Cmd+D]
└─ Cancel [Esc]
```

#### **Main Flow - Recent Files**
```
Cmd + Space → "recent" → Enter
📁 Recent Transcriptions
├─ 14:30 Client Strategy Session (42m) ✓
├─ 16:15 Urgent Call (8m) ✓
├─ 17:00 Client Review (35m) ⏳ Processing...
└─ 18:30 Internal Standup (22m) 📝 Pending
```

#### **Main Flow - Quick Export**  
```
Cmd + Space → "export client strategy" → Enter
📤 Export Options
├─ Format: TXT ✓ SRT ✓ JSON
├─ Destination: Desktop
├─ Filename: client-strategy-2025-01-15
└─ [Export Now] [Email] [Copy to Clipboard]
```

#### **Expected Results**
- Every CLI function accessible via Raycast
- Consistent UI patterns across all commands
- Keyboard shortcuts for power users
- Visual feedback for all actions

---

## 🔄 Error Handling & Edge Cases

### **EC-001: Teams Integration Failures**

#### **Scenario**: Teams detection not working
**Detection**: User reports missing auto-record prompts
**Resolution Path**:
1. `meetingscribe diagnose teams` → runs connectivity tests
2. Shows Teams.exe status, audio permissions, integration health
3. Offers repair options: reset integration, update permissions, restart service
4. Fallback: Manual recording via Raycast always available

### **EC-002: Audio Device Conflicts**

#### **Scenario**: Multiple applications competing for audio devices
**Detection**: Recording starts but captures silence or distorted audio
**Resolution Path**:
1. System detects low audio levels within 10 seconds
2. Auto-switches to alternative device if available
3. User notification: "Audio issue detected, switched to backup device"
4. Option to retry with different device or troubleshoot

### **EC-003: Storage/Memory Exhaustion**

#### **Scenario**: System running low on resources
**Detection**: Automated monitoring triggers alerts
**Resolution Path**:
1. **Storage Low**: Offers to delete old recordings, change storage location
2. **Memory High**: Unloads unused models, optimizes current processing
3. **CPU Overload**: Reduces transcription quality temporarily, queues jobs
4. Always maintains recording capability as highest priority

### **EC-004: Language Detection Failures**

#### **Scenario**: Meeting in unexpected language or mixed languages
**Detection**: Low transcription confidence scores
**Resolution Path**:
1. System prompts: "Low confidence detected, try different language?"
2. Offers top 3 detected languages based on audio analysis
3. User can retry transcription with different language
4. Option to split audio and process segments separately

---

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Analisar requisitos funcionais do consultor", "status": "completed", "activeForm": "Analisando requisitos funcionais do consultor"}, {"content": "Criar documento de requisitos funcionais", "status": "completed", "activeForm": "Criando documento de requisitos funcionais"}, {"content": "Detalhar casos de uso baseados no workflow do consultor", "status": "completed", "activeForm": "Detalhando casos de uso baseados no workflow do consultor"}, {"content": "Definir crit\u00e9rios de sucesso orientados ao usu\u00e1rio", "status": "in_progress", "activeForm": "Definindo crit\u00e9rios de sucesso orientados ao usu\u00e1rio"}, {"content": "Documentar trade-offs e limita\u00e7\u00f5es", "status": "pending", "activeForm": "Documentando trade-offs e limita\u00e7\u00f5es"}]