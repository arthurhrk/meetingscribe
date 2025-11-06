import {
  ActionPanel,
  Action,
  List,
  showToast,
  Toast,
  getPreferenceValues,
  Detail,
  Icon,
  Color,
} from "@raycast/api";
import { useState, useEffect } from "react";
import { spawn } from "child_process";
import * as fs from "fs";
import * as path from "path";

interface Preferences {
  pythonPath: string;
  projectPath: string;
  audioFormat?: string;
}

interface RecordingQuality {
  id: string;
  name: string;
  description: string;
  sizePerMin: string;
  icon: string;
  color: Color;
}

interface RecordingStatus {
  status: string;
  session_id: string;
  filename?: string;
  quality?: string;
  quality_info?: {
    name: string;
    description: string;
    size_per_min: string;
  };
  duration?: number;
  elapsed?: number;
  progress?: number;
  has_audio?: boolean;
  frames_captured?: number;
  device?: string;
  sample_rate?: number;
  channels?: number;
  message?: string;
  error?: string;
  file_size_mb?: number;
}

const RECORDING_QUALITIES: RecordingQuality[] = [
  {
    id: "quick",
    name: "Quick (16kHz Mono)",
    description: "Smaller files, good for voice notes",
    sizePerMin: "~2 MB/min",
    icon: "💬",
    color: Color.Blue,
  },
  {
    id: "standard",
    name: "Standard (44.1kHz Stereo)",
    description: "CD quality, balanced file size",
    sizePerMin: "~10 MB/min",
    icon: "🎵",
    color: Color.Green,
  },
  {
    id: "professional",
    name: "Professional (48kHz Stereo)",
    description: "Professional quality for meetings",
    sizePerMin: "~11 MB/min",
    icon: "🎙️",
    color: Color.Purple,
  },
  {
    id: "high",
    name: "High (96kHz Stereo)",
    description: "Maximum quality, larger files",
    sizePerMin: "~22 MB/min",
    icon: "💎",
    color: Color.Red,
  },
];

const DURATION_PRESETS = [
  { value: -1, label: "⏺️ Manual Mode (Start/Stop)", icon: Icon.Circle, special: true },
  { value: 30, label: "30 seconds", icon: Icon.Clock },
  { value: 60, label: "1 minute", icon: Icon.Clock },
  { value: 120, label: "2 minutes", icon: Icon.Clock },
  { value: 300, label: "5 minutes", icon: Icon.Clock },
  { value: 600, label: "10 minutes", icon: Icon.Clock },
  { value: 900, label: "15 minutes", icon: Icon.Clock },
  { value: 1800, label: "30 minutes", icon: Icon.Clock },
  { value: 3600, label: "60 minutes", icon: Icon.Clock },
];

// Active recording state
let activeRecordingProcess: any = null;
let activeSessionId: string | null = null;

export default function StartRecording() {
  const prefs = getPreferenceValues<Preferences>();
  const [selectedQuality, setSelectedQuality] = useState<string>("professional");
  const [isRecording, setIsRecording] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [recordingStatus, setRecordingStatus] = useState<RecordingStatus | null>(null);

  // Monitor status file for real-time updates
  useEffect(() => {
    if (isRecording && sessionId) {
      const statusFile = path.join(prefs.projectPath, "storage", "status", `${sessionId}.json`);

      console.log("[Record] Monitoring status file:", statusFile);
      console.log("[Record] Session ID:", sessionId);

      const interval = setInterval(() => {
        try {
          if (fs.existsSync(statusFile)) {
            const content = fs.readFileSync(statusFile, "utf8");
            const status: RecordingStatus = JSON.parse(content);

            // Only update state if status actually changed (prevents render loop)
            setRecordingStatus((prev) => {
              const hasChanged =
                !prev ||
                prev.status !== status.status ||
                prev.elapsed !== status.elapsed ||
                prev.progress !== status.progress;

              if (hasChanged) {
                console.log("[Record] Status updated:", {
                  status: status.status,
                  elapsed: status.elapsed,
                  progress: status.progress,
                });
                return status;
              }
              return prev;
            });

            // Check if completed or error
            if (status.status === "completed") {
              console.log("[Record] Recording completed:", status.filename);
              setIsRecording(false);
              clearInterval(interval);
              showToast({
                style: Toast.Style.Success,
                title: "Recording Completed",
                message: `File saved: ${status.filename} (${status.file_size_mb} MB)`,
              });
            } else if (status.status === "error") {
              console.error("[Record] Recording error:", status.error);
              setIsRecording(false);
              clearInterval(interval);
              showToast({
                style: Toast.Style.Failure,
                title: "Recording Failed",
                message: status.error || "Unknown error",
              });
            }
          } else {
            console.log("[Record] Status file not found yet:", statusFile);
          }
        } catch (error) {
          console.error("[Record] Error reading status file:", error);
        }
      }, 500); // Check every 500ms for smooth updates

      return () => {
        console.log("[Record] Cleaning up status monitoring");
        if (interval) clearInterval(interval);
      };
    }
  }, [isRecording, sessionId, prefs.projectPath]);

  async function startRecording(quality: string, duration: number) {
    if (isRecording) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Already Recording",
        message: "Please wait for current recording to finish",
      });
      return;
    }

    try {
      setIsRecording(true);

      // Debug: Print all preferences
      console.log("[Record] ========== PREFERENCES DEBUG ==========");
      console.log("[Record] prefs object:", JSON.stringify(prefs));
      console.log("[Record] prefs.pythonPath:", prefs.pythonPath);
      console.log("[Record] prefs.projectPath:", prefs.projectPath);
      console.log("[Record] prefs.audioFormat:", prefs.audioFormat);
      console.log("[Record] All preference keys:", Object.keys(prefs));
      console.log("[Record] All preference values:", Object.values(prefs));
      console.log("[Record] Type of prefs:", typeof prefs);
      console.log("[Record] ==========================================");

      // Validate paths
      if (!prefs.projectPath || !fs.existsSync(prefs.projectPath)) {
        throw new Error("Invalid project path in preferences");
      }

      // Check if manual mode (duration = -1)
      const isManualMode = duration === -1;

      // Use the new CLI interface instead of standalone scripts
      // No need to check for script existence - we'll use `python -m cli`

      const toastMessage = isManualMode
        ? `Manual mode - ${quality} quality`
        : `${duration}s - ${quality} quality`;

      await showToast({
        style: Toast.Style.Animated,
        title: "Starting Recording",
        message: toastMessage,
      });

      // Get audio format from preferences (default to 'wav' if not set)
      const audioFormat = (prefs.audioFormat && prefs.audioFormat !== '') ? prefs.audioFormat : "wav";

      console.log("[Record] audioFormat selected:", audioFormat);
      console.log("[Record] prefs.audioFormat value:", prefs.audioFormat);
      console.log("[Record] audioFormat is truthy:", !!prefs.audioFormat);

      // Start recording process using the new CLI interface
      // Command: python -m cli record <duration> <format>
      const args = ["-m", "cli", "record", duration.toString(), audioFormat];

      const fullCommand = `${prefs.pythonPath} ${args.join(" ")}`;
      console.log("[Record] ========================================");
      console.log("[Record] Full Command:", fullCommand);
      console.log("[Record] Python Path:", prefs.pythonPath);
      console.log("[Record] Arguments:", args);
      console.log("[Record] Arguments (JSON):", JSON.stringify(args));
      console.log("[Record] Working Directory:", prefs.projectPath);
      console.log("[Record] Audio Format Preference (prefs.audioFormat):", prefs.audioFormat);
      console.log("[Record] Audio Format (resolved):", audioFormat);
      console.log("[Record] Duration:", duration);
      console.log("[Record] Duration Type:", typeof duration);
      console.log("[Record] PYTHONPATH:", path.join(prefs.projectPath, "src"));
      console.log("[Record] ========================================");

      console.log("[Record] About to spawn with args:", args);
      console.log("[Record] Args length:", args.length);
      args.forEach((arg, i) => console.log(`[Record] args[${i}]:`, arg));

      const child = spawn(prefs.pythonPath, args, {
        cwd: prefs.projectPath,
        windowsHide: true,
        detached: false,
        stdio: ["ignore", "pipe", "pipe"],
        env: { ...process.env, PYTHONPATH: path.join(prefs.projectPath, "src") },
      });

      console.log("[Record] Process spawned. Child PID:", child.pid);

      activeRecordingProcess = child;

      let jsonReceived = false;
      let buffer = "";

      child.stdout?.setEncoding("utf8");
      child.stdout?.on("data", (data) => {
        console.log("[Record] Python stdout:", data.toString());

        if (!jsonReceived) {
          buffer += data.toString();
          const lines = buffer.split("\n");
          for (const line of lines) {
            if (line.trim().startsWith("{")) {
              try {
                const parsed = JSON.parse(line.trim());
                jsonReceived = true;

                console.log("[Record] Parsed JSON response:", parsed);

                if (parsed.status === "success" && parsed.data?.session_id) {
                  // Use the session_id from Python response
                  const receivedSessionId = parsed.data.session_id;
                  activeSessionId = receivedSessionId; // Keep for stopManualRecording
                  setSessionId(receivedSessionId); // Trigger useEffect

                  console.log("[Record] Session ID received:", receivedSessionId);

                  showToast({
                    style: Toast.Style.Success,
                    title: "Recording Started",
                    message: `Monitor progress below`,
                  });
                } else {
                  console.error("[Record] Unexpected JSON response:", parsed);
                }
                return;
              } catch (e) {
                console.error("[Record] JSON parse error:", e);
                // Continue reading
              }
            }
          }
        }
      });

      child.stderr?.on("data", (data) => {
        console.error("[Record] Python stderr:", data.toString());
      });

      child.on("error", (error) => {
        console.error("[Record] Process error:", error);
        if (!jsonReceived) {
          setIsRecording(false);
          setSessionId(null);
          showToast({
            style: Toast.Style.Failure,
            title: "Failed to Start",
            message: error.message,
          });
        }
      });

      child.on("exit", (code) => {
        console.log("[Record] Process exited with code:", code);
        setIsRecording(false);
        setSessionId(null);
        activeRecordingProcess = null;
        activeSessionId = null;

        if (code !== 0 && !recordingStatus) {
          console.error("[Record] Non-zero exit code without status");
          showToast({
            style: Toast.Style.Failure,
            title: "Recording Failed",
            message: `Process exited with code ${code}`,
          });
        }
      });

      // Safety timeout (increased to 10s as fallback)
      setTimeout(() => {
        if (!jsonReceived) {
          console.error("[Record] Timeout: No JSON response received within 10 seconds");
          setIsRecording(false);
          setSessionId(null);
          showToast({
            style: Toast.Style.Failure,
            title: "Timeout",
            message: "Recording failed to start within 10 seconds",
          });
        }
      }, 10000);
    } catch (error) {
      setIsRecording(false);
      setSessionId(null);
      const errorMsg = error instanceof Error ? error.message : String(error);
      await showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: errorMsg,
      });
    }
  }

  // Stop manual recording function
  async function stopManualRecording() {
    if (!activeSessionId) return;

    try {
      await showToast({
        style: Toast.Style.Animated,
        title: "Stopping Recording",
        message: "Finalizing audio file...",
      });

      // Note: The new CLI doesn't support manual stop yet
      // The recording will complete based on the duration specified
      // For now, just kill the process if it's still running
      if (activeRecordingProcess && !activeRecordingProcess.killed) {
        activeRecordingProcess.kill();
      }

      // Wait a bit for stop signal to be processed
      setTimeout(() => {
        showToast({
          style: Toast.Style.Success,
          title: "Stop Signal Sent",
          message: "Recording will finish shortly",
        });
      }, 1000);
    } catch (error) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Error Stopping",
        message: error instanceof Error ? error.message : String(error),
      });
    }
  }

  // Render recording status view
  if (isRecording && recordingStatus) {
    const progress = recordingStatus.progress || 0;
    const elapsed = recordingStatus.elapsed || 0;
    const duration = recordingStatus.duration || 0;
    const remaining = duration - elapsed;
    const isManualMode = duration === 0;

    const progressBar = isManualMode
      ? "🔴 Recording (Manual Mode)"
      : "█".repeat(Math.floor(progress / 5)) + "░".repeat(20 - Math.floor(progress / 5));

    const timeInfo = isManualMode
      ? `${elapsed}s (No time limit - press Stop when done)`
      : `${elapsed}s / ${duration}s (${remaining}s remaining)`;

    const markdown = `
# 🔴 Recording in Progress

${progressBar} ${!isManualMode ? `**${progress.toFixed(1)}%**` : ""}

## Recording Info
- **Filename**: ${recordingStatus.filename}
- **Time**: ${timeInfo}
- **Quality**: ${recordingStatus.quality_info?.name || recordingStatus.quality}
- **Device**: ${recordingStatus.device || "N/A"}
- **Audio**: ${recordingStatus.sample_rate}Hz, ${recordingStatus.channels}ch
- **Audio Detected**: ${recordingStatus.has_audio ? "✅ Yes" : "⏳ Waiting..."}
- **Frames Captured**: ${recordingStatus.frames_captured || 0}

${!recordingStatus.has_audio && elapsed > 3 ? "\n⚠️ **Warning**: No audio detected yet. Check if Teams is playing audio." : ""}

${isManualMode ? "\n\n💡 **Tip**: Press **Stop Recording** button below when you're done!" : ""}

---

*${isManualMode ? "Manual mode - use Stop button to finish" : "Recording will automatically save when complete"}*
`;

    return (
      <Detail
        markdown={markdown}
        actions={
          <ActionPanel>
            {isManualMode && (
              <Action
                title="⏹️ Stop Recording"
                icon={Icon.Stop}
                style={Action.Style.Destructive}
                onAction={stopManualRecording}
              />
            )}
            <Action
              title="Refresh Status"
              icon={Icon.ArrowClockwise}
              onAction={() => {
                showToast({ style: Toast.Style.Success, title: "Status refreshed" });
              }}
            />
          </ActionPanel>
        }
      />
    );
  }

  // Render quality and duration selection
  return (
    <List
      isLoading={false}
      searchBarPlaceholder="Select recording quality and duration..."
      searchBarAccessory={
        <List.Dropdown
          tooltip="Recording Quality"
          value={selectedQuality}
          onChange={setSelectedQuality}
        >
          {RECORDING_QUALITIES.map((quality) => (
            <List.Dropdown.Item
              key={quality.id}
              title={`${quality.icon} ${quality.name}`}
              value={quality.id}
            />
          ))}
        </List.Dropdown>
      }
    >
      <List.Section title="Recording Duration">
        {DURATION_PRESETS.map((preset) => {
          const selectedQualityObj = RECORDING_QUALITIES.find((q) => q.id === selectedQuality);
          const sizePerMin = selectedQualityObj?.sizePerMin || "";

          // Calculate expected size for this duration, accounting for format compression
          let expectedSize = sizePerMin;
          if (sizePerMin) {
            // Manual mode (value = -1) uses 1 minute as reference
            const durationSeconds = preset.value === -1 ? 60 : preset.value;
            if (durationSeconds > 0) {
              const minutesDuration = Math.ceil(durationSeconds / 60);
              const sizeMatch = sizePerMin.match(/(\d+\.?\d*)\s*MB/);
              if (sizeMatch) {
                let mbPerMin = parseFloat(sizeMatch[1]);

                // Apply compression factor for M4A format
                // M4A is typically 30-40% of WAV size (about 1/3)
                if (prefs.audioFormat === "m4a") {
                  mbPerMin = mbPerMin / 3;
                }

                const totalMb = Math.round(mbPerMin * minutesDuration);
                expectedSize = `~${totalMb}MB`;
              }
            }
          }

          return (
            <List.Item
              key={preset.value}
              title={preset.label}
              icon={preset.icon}
              accessories={[
                {
                  text: expectedSize,
                  icon: Icon.HardDrive,
                },
              ]}
              actions={
                <ActionPanel>
                  <Action
                    title={`Start Recording (${preset.label})`}
                    icon={Icon.Circle}
                    onAction={() => startRecording(selectedQuality, preset.value)}
                  />
                </ActionPanel>
              }
            />
          );
        })}
      </List.Section>
    </List>
  );
}
