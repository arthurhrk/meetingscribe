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
  { value: 30, label: "30 seconds", icon: Icon.Clock },
  { value: 60, label: "1 minute", icon: Icon.Clock },
  { value: 120, label: "2 minutes", icon: Icon.Clock },
  { value: 300, label: "5 minutes", icon: Icon.Video },
  { value: 600, label: "10 minutes", icon: Icon.Video },
  { value: 900, label: "15 minutes", icon: Icon.Video },
  { value: 1800, label: "30 minutes", icon: Icon.Video },
  { value: 3600, label: "60 minutes", icon: Icon.Video },
];

// Active recording state
let activeRecordingProcess: any = null;
let activeSessionId: string | null = null;

export default function StartRecording() {
  const [selectedQuality, setSelectedQuality] = useState<string>("professional");
  const [isRecording, setIsRecording] = useState(false);
  const [recordingStatus, setRecordingStatus] = useState<RecordingStatus | null>(null);
  const [statusCheckInterval, setStatusCheckInterval] = useState<NodeJS.Timer | null>(null);

  // Monitor status file for real-time updates
  useEffect(() => {
    if (isRecording && activeSessionId) {
      const { projectPath } = getPreferenceValues<Preferences>();
      const statusFile = path.join(projectPath, "storage", "status", `${activeSessionId}.json`);

      const interval = setInterval(() => {
        try {
          if (fs.existsSync(statusFile)) {
            const content = fs.readFileSync(statusFile, "utf8");
            const status: RecordingStatus = JSON.parse(content);
            setRecordingStatus(status);

            // Check if completed or error
            if (status.status === "completed") {
              setIsRecording(false);
              clearInterval(interval);
              showToast({
                style: Toast.Style.Success,
                title: "Recording Completed",
                message: `File saved: ${status.filename} (${status.file_size_mb} MB)`,
              });
            } else if (status.status === "error") {
              setIsRecording(false);
              clearInterval(interval);
              showToast({
                style: Toast.Style.Failure,
                title: "Recording Failed",
                message: status.error || "Unknown error",
              });
            }
          }
        } catch (error) {
          console.error("Error reading status file:", error);
        }
      }, 500); // Check every 500ms for smooth updates

      setStatusCheckInterval(interval);

      return () => {
        if (interval) clearInterval(interval);
      };
    }
  }, [isRecording, activeSessionId]);

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

      const { pythonPath, projectPath } = getPreferenceValues<Preferences>();

      // Validate paths
      if (!projectPath || !fs.existsSync(projectPath)) {
        throw new Error("Invalid project path in preferences");
      }

      const scriptPath = path.join(projectPath, "record_with_status.py");
      if (!fs.existsSync(scriptPath)) {
        throw new Error(`Script not found: ${scriptPath}`);
      }

      // Generate session ID
      const sessionId = `rec-${Date.now()}`;
      activeSessionId = sessionId;

      await showToast({
        style: Toast.Style.Animated,
        title: "Starting Recording",
        message: `${duration}s - ${quality} quality`,
      });

      // Start recording process
      const child = spawn(pythonPath, [scriptPath, duration.toString(), quality, sessionId], {
        cwd: projectPath,
        windowsHide: true,
        detached: false,
        stdio: ["ignore", "pipe", "pipe"],
      });

      activeRecordingProcess = child;

      let jsonReceived = false;
      let buffer = "";

      child.stdout?.setEncoding("utf8");
      child.stdout?.on("data", (data) => {
        if (!jsonReceived) {
          buffer += data.toString();
          const lines = buffer.split("\n");
          for (const line of lines) {
            if (line.trim().startsWith("{")) {
              try {
                const parsed = JSON.parse(line.trim());
                jsonReceived = true;

                if (parsed.status === "success") {
                  showToast({
                    style: Toast.Style.Success,
                    title: "Recording Started",
                    message: `Monitor progress below`,
                  });
                }
                return;
              } catch (e) {
                // Continue reading
              }
            }
          }
        }
      });

      child.stderr?.on("data", (data) => {
        console.error("Recording error:", data.toString());
      });

      child.on("error", (error) => {
        if (!jsonReceived) {
          setIsRecording(false);
          showToast({
            style: Toast.Style.Failure,
            title: "Failed to Start",
            message: error.message,
          });
        }
      });

      child.on("exit", (code) => {
        setIsRecording(false);
        activeRecordingProcess = null;
        activeSessionId = null;

        if (code !== 0 && !recordingStatus) {
          showToast({
            style: Toast.Style.Failure,
            title: "Recording Failed",
            message: `Process exited with code ${code}`,
          });
        }
      });

      // Safety timeout
      setTimeout(() => {
        if (!jsonReceived) {
          setIsRecording(false);
          showToast({
            style: Toast.Style.Failure,
            title: "Timeout",
            message: "Recording failed to start within 8 seconds",
          });
        }
      }, 8000);
    } catch (error) {
      setIsRecording(false);
      const errorMsg = error instanceof Error ? error.message : String(error);
      await showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: errorMsg,
      });
    }
  }

  // Render recording status view
  if (isRecording && recordingStatus) {
    const progress = recordingStatus.progress || 0;
    const elapsed = recordingStatus.elapsed || 0;
    const duration = recordingStatus.duration || 0;
    const remaining = duration - elapsed;

    const progressBar = "█".repeat(Math.floor(progress / 5)) + "░".repeat(20 - Math.floor(progress / 5));

    const markdown = `
# 🔴 Recording in Progress

${progressBar} **${progress.toFixed(1)}%**

## Status
- **Time**: ${elapsed}s / ${duration}s (${remaining}s remaining)
- **Quality**: ${recordingStatus.quality_info?.name || recordingStatus.quality}
- **Device**: ${recordingStatus.device || "N/A"}
- **Audio**: ${recordingStatus.sample_rate}Hz, ${recordingStatus.channels}ch
- **Audio Detected**: ${recordingStatus.has_audio ? "✅ Yes" : "⏳ Waiting..."}
- **Frames Captured**: ${recordingStatus.frames_captured || 0}

## File Info
- **Filename**: ${recordingStatus.filename}
- **Expected Size**: ${recordingStatus.quality_info?.size_per_min || "N/A"}

${!recordingStatus.has_audio && elapsed > 3 ? "\n⚠️ **Warning**: No audio detected yet. Check if Teams is playing audio." : ""}

---

*Recording will automatically save when complete*
`;

    return (
      <Detail
        markdown={markdown}
        actions={
          <ActionPanel>
            <Action
              title="Refresh Status"
              icon={Icon.ArrowClockwise}
              onAction={() => {
                // Status updates automatically
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
        {DURATION_PRESETS.map((preset) => (
          <List.Item
            key={preset.value}
            title={preset.label}
            icon={preset.icon}
            accessories={[
              {
                text: RECORDING_QUALITIES.find((q) => q.id === selectedQuality)?.sizePerMin || "",
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
        ))}
      </List.Section>

      <List.Section title="Quality Info">
        {RECORDING_QUALITIES.map((quality) => (
          <List.Item
            key={quality.id}
            title={`${quality.icon} ${quality.name}`}
            subtitle={quality.description}
            accessories={[{ text: quality.sizePerMin }]}
          />
        ))}
      </List.Section>
    </List>
  );
}
