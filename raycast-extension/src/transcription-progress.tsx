import {
  ActionPanel,
  Action,
  List,
  showToast,
  Toast,
  getPreferenceValues,
  Icon,
  Color,
  open,
  confirmAlert,
  Alert,
} from "@raycast/api";
import { useState, useEffect } from "react";
import * as fs from "fs";
import * as path from "path";

interface Preferences {
  pythonPath: string;
  projectPath: string;
}

interface TranscriptionProgress {
  sessionId: string;
  filename: string;
  audioFilename: string;
  step: string;
  stepNumber: number;
  totalSteps: number;
  progress: number;
  message: string;
}

export default function TranscriptionProgress() {
  const [transcriptions, setTranscriptions] = useState<TranscriptionProgress[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { projectPath } = getPreferenceValues<Preferences>();

  useEffect(() => {
    loadProgressStatus();
    // Poll for updates every 500ms
    const interval = setInterval(loadProgressStatus, 500);
    return () => clearInterval(interval);
  }, []);

  function loadProgressStatus() {
    try {
      const statusDir = path.join(projectPath, "storage", "status");

      // Check if directory exists
      if (!fs.existsSync(statusDir)) {
        setTranscriptions([]);
        setIsLoading(false);
        return;
      }

      // Find all transcribe_* status files
      const files = fs
        .readdirSync(statusDir)
        .filter((f) => f.startsWith("transcribe_") && f.endsWith(".json"))
        .map((filename) => {
          const statusPath = path.join(statusDir, filename);
          const sessionId = filename.replace("transcribe_", "").replace(".json", "");

          try {
            const content = fs.readFileSync(statusPath, "utf8");
            const status = JSON.parse(content);

            // Try to find the audio filename from recent recordings
            const recordingsDir = path.join(projectPath, "storage", "recordings");
            let audioFilename = "Unknown recording";

            if (fs.existsSync(recordingsDir)) {
              // Get the most recently modified audio file as a guess
              const recordings = fs
                .readdirSync(recordingsDir)
                .filter((f) => f.endsWith(".wav") || f.endsWith(".m4a"))
                .map((f) => ({
                  name: f,
                  time: fs.statSync(path.join(recordingsDir, f)).mtime.getTime(),
                }))
                .sort((a, b) => b.time - a.time);

              if (recordings.length > 0) {
                audioFilename = recordings[0].name;
              }
            }

            return {
              sessionId,
              filename,
              audioFilename,
              step: status.step || "unknown",
              stepNumber: status.step_number || 0,
              totalSteps: status.total_steps || 4,
              progress: status.progress || 0,
              message: status.message || "Processing...",
            };
          } catch (e) {
            // Skip files that can't be read
            return null;
          }
        })
        .filter((item): item is TranscriptionProgress => item !== null)
        .sort((a, b) => parseInt(b.sessionId) - parseInt(a.sessionId)); // Newest first

      setTranscriptions(files);
      setIsLoading(false);
    } catch (error) {
      console.error("[TranscriptionProgress] Error loading status:", error);
      setIsLoading(false);
    }
  }

  function openInFinder(filePath: string) {
    open(path.dirname(filePath));
  }

  async function deleteProgressFile(sessionId: string) {
    const confirmed = await confirmAlert({
      title: "Delete Progress File",
      message: `Are you sure you want to delete the progress file for session ${sessionId}?`,
      primaryAction: {
        title: "Delete",
        style: Alert.ActionStyle.Destructive,
      },
    });

    if (!confirmed) {
      return;
    }

    try {
      const statusDir = path.join(projectPath, "storage", "status");
      const statusFile = path.join(statusDir, `transcribe_${sessionId}.json`);
      console.log(`[TranscriptionProgress] Attempting to delete: ${statusFile}`);
      if (fs.existsSync(statusFile)) {
        fs.unlinkSync(statusFile);
        console.log(`[TranscriptionProgress] File deleted successfully`);
        const successMsg = `Progress File Deleted: Session ${sessionId} removed`;
        console.log(`[TranscriptionProgress] ${successMsg}`);
        showToast({
          style: Toast.Style.Success,
          title: "Progress File Deleted",
          message: `Session ${sessionId} removed`,
        });
        loadProgressStatus();
      } else {
        console.log(`[TranscriptionProgress] File not found: ${statusFile}`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      console.error(`[TranscriptionProgress] Error deleting progress file: ${errorMsg}`);
      showToast({
        style: Toast.Style.Failure,
        title: "Error Deleting Progress File",
        message: errorMsg,
      });
    }
  }

  function getProgressBar(progress: number): string {
    const filled = Math.floor(progress / 5);
    const empty = 20 - filled;
    return "█".repeat(filled) + "░".repeat(empty);
  }

  function getStepIcon(step: string): string {
    switch (step) {
      case "uploading":
        return "📤";
      case "processing":
        return "⚙️";
      case "transcribing":
        return "🎤";
      case "saving":
        return "💾";
      default:
        return "⏳";
    }
  }

  if (transcriptions.length === 0 && !isLoading) {
    return (
      <List>
        <List.EmptyView
          icon={Icon.SpeechBubble}
          title="No Transcriptions in Progress"
          description="Start a transcription from 'Recent Recordings' command using Cmd+Shift+T"
        />
      </List>
    );
  }

  return (
    <List isLoading={isLoading} searchBarPlaceholder="Search transcriptions...">
      <List.Section title={`${transcriptions.length} in Progress`}>
        {transcriptions.map((transcription) => (
          <List.Item
            key={transcription.sessionId}
            title={transcription.audioFilename}
            subtitle={`${getStepIcon(transcription.step)} [${transcription.step.charAt(0).toUpperCase() + transcription.step.slice(1)}] ${transcription.message}`}
            icon={Icon.SpeechBubble}
            accessories={[
              {
                text: `${transcription.progress}%`,
                tooltip: `Progress: ${transcription.progress}% (Step ${transcription.stepNumber}/${transcription.totalSteps})`,
              },
            ]}
            detail={
              <List.Item.Detail
                markdown={`
# Transcription Progress

## File
\`${transcription.audioFilename}\`

## Step
**${transcription.step.charAt(0).toUpperCase() + transcription.step.slice(1)}** (${transcription.stepNumber}/${transcription.totalSteps})

## Progress
\`${getProgressBar(transcription.progress)}\` ${transcription.progress}%

## Status
${transcription.message}

---

**Session ID:** \`${transcription.sessionId}\`
`}
                metadata={
                  <List.Item.Detail.Metadata>
                    <List.Item.Detail.Metadata.Label title="File" text={transcription.audioFilename} />
                    <List.Item.Detail.Metadata.Label
                      title="Step"
                      text={`${transcription.stepNumber}/${transcription.totalSteps}`}
                    />
                    <List.Item.Detail.Metadata.Label title="Progress" text={`${transcription.progress}%`} />
                    <List.Item.Detail.Metadata.Label title="Status" text={transcription.message} />
                  </List.Item.Detail.Metadata>
                }
              />
            }
            actions={
              <ActionPanel>
                <ActionPanel.Section title="View">
                  <Action
                    title="Open Status Folder"
                    icon={Icon.Finder}
                    onAction={() => openInFinder(path.join(projectPath, "storage", "status"))}
                  />
                  <Action
                    title="Refresh List"
                    icon={Icon.ArrowClockwise}
                    shortcut={{ modifiers: ["cmd", "shift"], key: "r" }}
                    onAction={loadProgressStatus}
                  />
                </ActionPanel.Section>
                <ActionPanel.Section title="Cleanup">
                  <Action
                    title="Delete Progress File"
                    icon={Icon.Trash}
                    style={Action.Style.Destructive}
                    shortcut={{ modifiers: ["cmd"], key: "backspace" }}
                    onAction={() => {
                      deleteProgressFile(transcription.sessionId).catch((error) => {
                        console.error(`[TranscriptionProgress] Delete action error: ${error}`);
                      });
                    }}
                  />
                </ActionPanel.Section>
              </ActionPanel>
            }
          />
        ))}
      </List.Section>
    </List>
  );
}
