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
import { useState, useEffect } from "react";
import * as fs from "fs";
import * as path from "path";

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

  // Poll for active recordings
  useEffect(() => {
    const { projectPath } = getPreferenceValues<Preferences>();
    const statusDir = path.join(projectPath, "storage", "status");

    const checkActiveRecordings = () => {
      try {
        // Check if status directory exists
        if (!fs.existsSync(statusDir)) {
          fs.mkdirSync(statusDir, { recursive: true });
          setActiveRecordings([]);
          setIsLoading(false);
          return;
        }

        // Read all status files
        const files = fs.readdirSync(statusDir).filter((f) => f.endsWith(".json"));

        if (files.length === 0) {
          setActiveRecordings([]);
          setIsLoading(false);
          return;
        }

        const recordings: RecordingStatus[] = [];

        for (const file of files) {
          try {
            const content = fs.readFileSync(path.join(statusDir, file), "utf8");
            const status: RecordingStatus = JSON.parse(content);
            recordings.push(status);
          } catch (err) {
            console.error(`Error reading status file ${file}:`, err);
          }
        }

        setActiveRecordings(recordings);
        setIsLoading(false);
      } catch (err) {
        console.error("Error checking active recordings:", err);
        setError(err instanceof Error ? err.message : String(err));
        setIsLoading(false);
      }
    };

    // Initial check
    checkActiveRecordings();

    // Poll every 500ms
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

      const warningMessage =
        !recording.has_audio && elapsed > 3
          ? "\n\n⚠️ **Warning**: No audio detected yet. Check if audio is playing.\n"
          : "";

      return `
# ${statusIcon} ${recording.status === "recording" ? "Recording in Progress" : recording.status}

${progressBar} ${duration > 0 ? `**${progress.toFixed(1)}%**` : ""}

## Status
- **Session**: ${recording.session_id}
- **Time**: ${elapsed}s ${isManual ? "(Manual - no limit)" : `/ ${duration}s (${remaining}s remaining)`}
- **Quality**: ${recording.quality_info?.name || recording.quality || "N/A"}
- **Device**: ${recording.device || "N/A"}
- **Audio**: ${recording.sample_rate || 0}Hz, ${recording.channels || 0}ch
- **Audio Detected**: ${recording.has_audio ? "✅ Yes" : "⏳ Waiting..."}
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
                const { projectPath } = getPreferenceValues<Preferences>();
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
