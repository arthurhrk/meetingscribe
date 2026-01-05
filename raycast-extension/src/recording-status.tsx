import {
  ActionPanel,
  Action,
  Detail,
  showToast,
  Toast,
  getPreferenceValues,
  Icon,
  Color,
  open,
} from "@raycast/api";
import { useState, useEffect, useRef } from "react";
import * as fs from "fs";
import * as path from "path";
import { createStopSignal } from "./signals";

interface Preferences {
  pythonPath: string;
  projectPath: string;
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
  speaker_device?: string;
  microphone_device?: string;
  dual_recording?: boolean;
  mic_warning?: string;
  sample_rate?: number;
  channels?: number;
  message?: string;
  error?: string;
  file_size_mb?: number;
  file_path?: string;
}

export default function RecordingStatus() {
  const [activeRecordings, setActiveRecordings] = useState<RecordingStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stoppingSessionId, setStoppingSessionId] = useState<string | null>(null);
  const previousDataRef = useRef<string>("");

  const { projectPath } = getPreferenceValues<Preferences>();

  // Deep equality check - compare JSON serialization
  const hasDataChanged = (newRecordings: RecordingStatus[]): boolean => {
    const newData = JSON.stringify(newRecordings);
    if (newData === previousDataRef.current) {
      return false;
    }
    previousDataRef.current = newData;
    return true;
  };

  // Stop recording function
  async function stopRecording(sessionId: string) {
    setStoppingSessionId(sessionId);
    try {
      await showToast({
        style: Toast.Style.Animated,
        title: "Stopping Recording",
        message: "Sending stop signal...",
      });

      const success = createStopSignal(projectPath, sessionId);

      if (!success) {
        await showToast({
          style: Toast.Style.Failure,
          title: "Error Stopping",
          message: "Could not create stop signal",
        });
        setStoppingSessionId(null);
        return;
      }

      await showToast({
        style: Toast.Style.Success,
        title: "Stop Signal Sent",
        message: "Recording will finish shortly",
      });

      // Refresh after a short delay to show updated status
      setTimeout(() => {
        setStoppingSessionId(null);
      }, 1000);
    } catch (error) {
      console.error("[RecordingStatus] Error stopping recording:", error);
      await showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: error instanceof Error ? error.message : String(error),
      });
      setStoppingSessionId(null);
    }
  }

  // Poll for active recordings
  useEffect(() => {
    const statusDir = path.join(projectPath, "storage", "status");

    const checkActiveRecordings = () => {
      try {
        // Check if status directory exists
        if (!fs.existsSync(statusDir)) {
          fs.mkdirSync(statusDir, { recursive: true });
          if (hasDataChanged([])) {
            setActiveRecordings([]);
          }
          setIsLoading(false);
          return;
        }

        // Read all status files
        const files = fs.readdirSync(statusDir).filter((f) => f.endsWith(".json"));

        if (files.length === 0) {
          if (hasDataChanged([])) {
            setActiveRecordings([]);
          }
          setIsLoading(false);
          return;
        }

        // Sort files by modification time (newest first)
        const sortedFiles = files.sort((a, b) => {
          const aPath = path.join(statusDir, a);
          const bPath = path.join(statusDir, b);
          const aTime = fs.statSync(aPath).mtime.getTime();
          const bTime = fs.statSync(bPath).mtime.getTime();
          return bTime - aTime; // Newest first (descending order)
        });

        const recordings: RecordingStatus[] = [];

        for (const file of sortedFiles) {
          try {
            const content = fs.readFileSync(path.join(statusDir, file), "utf8");
            const status: RecordingStatus = JSON.parse(content);
            recordings.push(status);
          } catch (err) {
            console.error(`Error reading status file ${file}:`, err);
          }
        }

        // Only update state if data has actually changed
        if (hasDataChanged(recordings)) {
          setActiveRecordings(recordings);
        }
        setIsLoading(false);
      } catch (err) {
        console.error("Error checking active recordings:", err);
        setError(err instanceof Error ? err.message : String(err));
        setIsLoading(false);
      }
    };

    // Initial check
    checkActiveRecordings();

    const interval = setInterval(checkActiveRecordings, 500);

    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return <Detail markdown="# 🔄 Loading...\n\nChecking for active recordings..." />;
  }

  if (error) {
    return (
      <Detail
        markdown={`# ❌ Error\n\n${error}\n\nPlease check your project path in preferences.`}
        actions={
          <ActionPanel>
            <Action title="Retry" icon={Icon.ArrowClockwise} onAction={() => setIsLoading(true)} />
          </ActionPanel>
        }
      />
    );
  }

  if (activeRecordings.length === 0) {
    return (
      <Detail
        markdown={`# 📭 No Active Recordings

No recordings in progress right now.

## Quick Actions
- Start a new recording with **Start Recording** command
- View recent recordings with **Recent Recordings** command

---

*This view updates automatically every 500ms*
`}
        actions={
          <ActionPanel>
            <Action title="Refresh" icon={Icon.ArrowClockwise} onAction={() => setIsLoading(true)} />
          </ActionPanel>
        }
      />
    );
  }

  // Build markdown for all active recordings
  const markdown = activeRecordings
    .map((recording) => {
      const progress = recording.progress || 0;
      const elapsed = recording.elapsed || 0;
      const duration = recording.duration || 0;
      const remaining = duration > 0 ? duration - elapsed : 0;
      const isManual = duration === 0; // Manual recording (no time limit)

      const progressBar = duration > 0
        ? "█".repeat(Math.floor(progress / 5)) + "░".repeat(20 - Math.floor(progress / 5))
        : "🔴 Recording (Manual Mode)";

      const statusIcon =
        recording.status === "recording"
          ? "🔴"
          : recording.status === "completed"
          ? "✅"
          : recording.status === "error"
          ? "❌"
          : "⏳";

      // Build warning messages
      let warningMessage = "";
      if (recording.mic_warning) {
        warningMessage += `\n\n⚠️ **Warning**: ${recording.mic_warning}\n`;
      }
      if (!recording.has_audio && elapsed > 3) {
        warningMessage += "\n\n⚠️ **Warning**: No audio detected yet. Check if audio is playing.\n";
      }

      // Format device info - show dual recording status
      const deviceInfo = recording.dual_recording
        ? `Speaker: ${recording.speaker_device || "N/A"}\n- **Microphone**: ${recording.microphone_device || "N/A"}`
        : recording.device || "N/A";

      const recordingModeLabel = recording.dual_recording
        ? "Recording in Progress (Speaker + Mic)"
        : "Recording in Progress";

      return `
# ${statusIcon} ${recording.status === "recording" ? recordingModeLabel : recording.status}

${progressBar} ${duration > 0 ? `**${progress.toFixed(1)}%**` : ""}

## Status
- **Session**: ${recording.session_id}
- **Time**: ${elapsed}s ${isManual ? "(Manual - no limit)" : `/ ${duration}s (${remaining}s remaining)`}
- **Quality**: ${recording.quality_info?.name || recording.quality || "N/A"}
- **${recording.dual_recording ? "Devices" : "Device"}**: ${deviceInfo}
- **Audio**: ${recording.sample_rate || 0}Hz, ${recording.channels || 0}ch
- **Audio Detected**: ${recording.has_audio ? "Yes" : "Waiting..."}
- **Frames Captured**: ${recording.frames_captured || 0}

## File Info
- **Filename**: ${recording.filename || "N/A"}
- **Expected Size**: ${recording.quality_info?.size_per_min || "N/A"}
${recording.file_size_mb ? `- **Actual Size**: ${recording.file_size_mb} MB` : ""}

${warningMessage}

---
`;
    })
    .join("\n\n");

  const fullMarkdown = `${markdown}\n\n*Updates automatically every 500ms*\n\n*Tip: Keep this window open to monitor your recording*`;

  return (
    <Detail
      markdown={fullMarkdown}
      actions={
        <ActionPanel>
          {activeRecordings.length > 0 && activeRecordings[0].status === "recording" && (
            <Action
              title="⏹️ Stop This Recording"
              icon={Icon.Stop}
              style={Action.Style.Destructive}
              onAction={() => stopRecording(activeRecordings[0].session_id)}
            />
          )}
          <Action
            title="Refresh Status"
            icon={Icon.ArrowClockwise}
            onAction={() => {
              showToast({ style: Toast.Style.Success, title: "Status refreshed" });
            }}
          />
          {activeRecordings.length > 0 && activeRecordings[0].file_path && (
            <Action
              title="Open Recordings Folder"
              icon={Icon.Folder}
              onAction={() => {
                const recordingsPath = path.join(projectPath, "storage", "recordings");
                open(recordingsPath);
              }}
            />
          )}
        </ActionPanel>
      }
    />
  );
}
