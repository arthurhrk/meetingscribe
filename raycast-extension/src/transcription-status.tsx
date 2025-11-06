import {
  ActionPanel,
  Action,
  List,
  Detail,
  showToast,
  Toast,
  getPreferenceValues,
  Icon,
  Color,
  open,
  confirmAlert,
  Alert,
} from "@raycast/api";
import { useState, useEffect, useRef, useCallback } from "react";
import * as fs from "fs";
import * as path from "path";

interface Preferences {
  pythonPath: string;
  projectPath: string;
}

interface TranscriptionStatus {
  sessionId: string;
  filename: string;
  audioFilename: string;
  step: string;
  stepNumber: number;
  totalSteps: number;
  progress: number;
  message: string;
  isCompleted?: boolean;
  recordingDate?: string; // ISO string or localized string for display
  recordingTimestamp?: number; // Unix timestamp for reliable date formatting
  transcriptPath?: string;
}

function TranscriptionDetailView({
  transcription,
}: {
  transcription: TranscriptionStatus;
  projectPath: string;
}) {
  const getProgressBar = (progress: number): string => {
    const filled = Math.floor(progress / 5);
    const empty = 20 - filled;
    return "█".repeat(filled) + "░".repeat(empty);
  };

  const getStepIcon = (step: string): string => {
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
  };

  return (
    <Detail
      markdown={`${getStepIcon(transcription.step)} **${transcription.step.charAt(0).toUpperCase() + transcription.step.slice(1)}** ${transcription.stepNumber}/${transcription.totalSteps} • ${transcription.progress}%

${getProgressBar(transcription.progress)}

${transcription.message}`}
      metadata={
        <Detail.Metadata>
          <Detail.Metadata.Label
            title="File"
            text={transcription.audioFilename}
          />
          <Detail.Metadata.Label
            title="Recorded"
            text={transcription.recordingDate || "Unknown"}
          />
          <Detail.Metadata.Separator />
          <Detail.Metadata.Label
            title="Step"
            text={`${transcription.step} (${transcription.stepNumber}/${transcription.totalSteps})`}
          />
          <Detail.Metadata.Label
            title="Progress"
            text={`${transcription.progress}%`}
          />
          <Detail.Metadata.Label
            title="Status"
            text={transcription.message}
          />
          <Detail.Metadata.Label
            title="State"
            text={transcription.isCompleted ? "✅ Completed" : "⏳ In Progress"}
          />
        </Detail.Metadata>
      }
      actions={
        <ActionPanel>
          <Action
            title="Copy Audio Filename"
            icon={Icon.CopyClipboard}
            shortcut={{
              macOS: { modifiers: ["cmd"], key: "c" },
              windows: { modifiers: ["ctrl"], key: "c" },
            }}
            onAction={() => {
              showToast({
                style: Toast.Style.Success,
                title: "Copied to Clipboard",
                message: transcription.audioFilename,
              });
            }}
          />
          <Action
            title="Copy Session ID"
            icon={Icon.CopyClipboard}
            onAction={() => {
              showToast({
                style: Toast.Style.Success,
                title: "Copied to Clipboard",
                message: transcription.sessionId,
              });
            }}
          />
        </ActionPanel>
      }
    />
  );
}

export default function TranscriptionProgress() {
  const [transcriptions, setTranscriptions] = useState<TranscriptionStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { projectPath } = getPreferenceValues<Preferences>();

  useEffect(() => {
    loadProgressStatus();
    // Poll for updates every 200ms for faster status updates (reduced from 500ms)
    const interval = setInterval(loadProgressStatus, 200);
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
            let recordingDate: string | undefined = undefined;
            let recordingTimestamp: number | undefined = undefined;

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
                recordingTimestamp = recordings[0].time;
                recordingDate = new Date(recordings[0].time).toLocaleString();
              }
            }

            // Check if transcription is completed (step 4 = saving with 100% progress)
            const isCompleted = status.progress === 100 && status.step === "saving";
            const transcriptPath = isCompleted ? findTranscriptFile(audioFilename) : undefined;

            return {
              sessionId,
              filename,
              audioFilename,
              step: status.step || "unknown",
              stepNumber: status.step_number || 0,
              totalSteps: status.total_steps || 4,
              progress: status.progress || 0,
              message: isCompleted ? "Transcription complete" : (status.message || "Processing..."),
              recordingDate,
              recordingTimestamp,
              isCompleted,
              transcriptPath,
            };
          } catch (e) {
            // Skip files that can't be read
            return null;
          }
        })
        .filter((item) => item !== null)
        .sort((a, b) => parseInt(b!.sessionId) - parseInt(a!.sessionId)); // Newest first

      // Only update state if the data has actually changed to prevent re-render loops
      if (JSON.stringify(files) !== JSON.stringify(transcriptions)) {
        setTranscriptions(files);
      }
      setIsLoading(false);
    } catch (error) {
      console.error("[TranscriptionStatus] Error loading status:", error);
      setIsLoading(false);
    }
  }

  function openInFinder(filePath: string) {
    open(path.dirname(filePath));
  }

  function findTranscriptFile(audioFilename: string): string | undefined {
    try {
      const transcriptDir = path.join(projectPath, "storage", "transcriptions");

      if (!fs.existsSync(transcriptDir)) {
        return undefined;
      }

      // Generate expected transcript filename (replace audio extension with .md)
      const baseName = audioFilename.replace(/\.(wav|m4a)$/, "");
      const transcriptPath = path.join(transcriptDir, `${baseName}.md`);

      if (fs.existsSync(transcriptPath)) {
        return transcriptPath;
      }

      return undefined;
    } catch (error) {
      console.error("[TranscriptionStatus] Error finding transcript file:", error);
      return undefined;
    }
  }

  function openTranscript(transcriptPath: string) {
    try {
      console.log(`[TranscriptionStatus] Opening transcript: ${transcriptPath}`);
      open(transcriptPath);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      console.error(`[TranscriptionStatus] Error opening transcript: ${errorMsg}`);
      showToast({
        style: Toast.Style.Failure,
        title: "Error Opening Transcript",
        message: errorMsg,
      });
    }
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
      console.log(`[TranscriptionStatus] Attempting to delete: ${statusFile}`);
      if (fs.existsSync(statusFile)) {
        fs.unlinkSync(statusFile);
        console.log(`[TranscriptionStatus] File deleted successfully`);
        const successMsg = `Progress File Deleted: Session ${sessionId} removed`;
        console.log(`[TranscriptionStatus] ${successMsg}`);
        showToast({
          style: Toast.Style.Success,
          title: "Progress File Deleted",
          message: `Session ${sessionId} removed`,
        });
        loadProgressStatus();
      } else {
        console.log(`[TranscriptionStatus] File not found: ${statusFile}`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      console.error(`[TranscriptionStatus] Error deleting progress file: ${errorMsg}`);
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

  function formatDateShort(timestamp?: number): string {
    if (!timestamp) {
      return "unknown";
    }
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: '2-digit' }).toLowerCase();
  }

  if (transcriptions.length === 0 && !isLoading) {
    return (
      <List>
        <List.EmptyView
          icon={Icon.SpeechBubble}
          title="No Transcriptions in Progress"
          description="Start a transcription from 'Recent Recordings'"
        />
      </List>
    );
  }

  return (
    <List isLoading={isLoading} searchBarPlaceholder="Search transcriptions...">
      <List.Section title={`${transcriptions.length} transcriptions`}>
        {transcriptions.map((transcription) => (
          <List.Item
            key={transcription.sessionId}
            title={transcription.audioFilename}
            subtitle={transcription.isCompleted ? `${transcription.message} (${formatDateShort(transcription.recordingTimestamp)})` : `${getStepIcon(transcription.step)} [${transcription.step.charAt(0).toUpperCase() + transcription.step.slice(1)}] ${transcription.message}`}
            icon={transcription.isCompleted ? Icon.CheckCircle : Icon.Clock}
            accessories={[
              {
                text: `${transcription.progress}%`,
                tooltip: `Progress: ${transcription.progress}% (Step ${transcription.stepNumber}/${transcription.totalSteps})`,
              },
            ]}
            detail={
              <List.Item.Detail
                markdown={`
# Transcription Status

## Recording Date
\`${transcription.recordingDate || "Unknown"}\`

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
                      title="Recording Date"
                      text={transcription.recordingDate || "Unknown"}
                    />
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
                  <Action.Push
                    title="Show Details"
                    icon={Icon.Eye}
                    shortcut={{
                      macOS: { modifiers: ["cmd"], key: "d" },
                      windows: { modifiers: ["ctrl"], key: "d" },
                    }}
                    target={
                      <TranscriptionDetailView
                        transcription={transcription}
                        projectPath={projectPath}
                      />
                    }
                  />
                  {transcription.isCompleted && transcription.transcriptPath && (
                    <Action
                      title="Open Transcription"
                      icon={Icon.Document}
                      shortcut={{
                        macOS: { modifiers: ["cmd"], key: "o" },
                        windows: { modifiers: ["ctrl"], key: "o" },
                      }}
                      onAction={() => openTranscript(transcription.transcriptPath!)}
                    />
                  )}
                  <Action
                    title="Open Status Folder"
                    icon={Icon.Finder}
                    onAction={() => openInFinder(path.join(projectPath, "storage", "status"))}
                  />
                  <Action
                    title="Refresh List"
                    icon={Icon.ArrowClockwise}
                    shortcut={{
                      macOS: { modifiers: ["cmd", "shift"], key: "r" },
                      windows: { modifiers: ["ctrl", "shift"], key: "r" },
                    }}
                    onAction={loadProgressStatus}
                  />
                </ActionPanel.Section>
                <ActionPanel.Section title="Cleanup">
                  <Action
                    title="Delete Progress File"
                    icon={Icon.Trash}
                    style={Action.Style.Destructive}
                    shortcut={{
                      macOS: { modifiers: ["cmd"], key: "backspace" },
                      windows: { modifiers: ["ctrl", "shift"], key: "d" },
                    }}
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
