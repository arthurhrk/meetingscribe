import {
  ActionPanel,
  Action,
  List,
  showToast,
  Toast,
  getPreferenceValues,
  Icon,
  Color,
  Form,
  useNavigation,
  confirmAlert,
  Alert,
  open,
} from "@raycast/api";
import { useState, useEffect } from "react";
import { spawn } from "child_process";
import * as fs from "fs";
import * as path from "path";
import TranscriptionProgress from "./transcription-status";

interface Preferences {
  pythonPath: string;
  projectPath: string;
  geminiApiKey?: string;
  geminiModel?: string;
  optimizeAudio?: boolean;
}

interface Recording {
  filename: string;
  fullPath: string;
  createdDate: Date;
  createdDisplay: string;
  sizeBytes: number;
  sizeDisplay: string;
  durationEstimate: string;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
}

function estimateDuration(sizeBytes: number, filename: string, quality: string = "professional"): string {
  // WAV quality rates (uncompressed)
  // - Professional: ~11 MB/min = 183,333 bytes/sec
  // - Standard: ~10 MB/min = 166,667 bytes/sec
  // - Quick: ~2 MB/min = 33,333 bytes/sec

  // M4A is approximately 1/3 the size of WAV for the same quality/duration
  // - Professional M4A: ~3.67 MB/min = 61,111 bytes/sec
  // - Standard M4A: ~3.33 MB/min = 55,556 bytes/sec
  // - Quick M4A: ~0.67 MB/min = 11,111 bytes/sec

  let bytesPerSecond = 183333; // Default to professional WAV

  if (filename.endsWith(".m4a")) {
    bytesPerSecond = 61111; // M4A professional quality
  }

  const seconds = Math.round(sizeBytes / bytesPerSecond);

  if (seconds < 60) return `~${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return remainingSeconds > 0 ? `~${minutes}m ${remainingSeconds}s` : `~${minutes}m`;
}

function RenameForm({ recording, onRename }: { recording: Recording; onRename: (oldPath: string, newName: string) => void }) {
  const { pop } = useNavigation();
  const [newName, setNewName] = useState(recording.filename.replace(/\.(wav|m4a)$/, ""));

  function handleSubmit() {
    if (!newName.trim()) {
      const errorMsg = "Name cannot be empty";
      console.error(`[RecentRecordings] ${errorMsg}`);
      showToast({ style: Toast.Style.Failure, title: "Invalid name", message: errorMsg });
      return;
    }

    // Preserve the original file extension (wav or m4a)
    const originalExt = recording.filename.match(/\.(wav|m4a)$/)?.[1] || "wav";
    const finalName = newName.trim().match(/\.(wav|m4a)$/) ? newName.trim() : `${newName.trim()}.${originalExt}`;
    onRename(recording.fullPath, finalName);
    pop();
  }

  return (
    <Form
      actions={
        <ActionPanel>
          <Action.SubmitForm title="Rename" onSubmit={handleSubmit} icon={Icon.Pencil} />
        </ActionPanel>
      }
    >
      <Form.TextField
        id="newName"
        title="New Name"
        placeholder="my-meeting"
        value={newName}
        onChange={setNewName}
      />
      <Form.Description
        title="Preview"
        text={`${newName.trim() || "filename"}.${recording.filename.match(/\.(wav|m4a)$/)?.[1] || "wav"}`}
      />
      <Form.Description
        title="Original"
        text={recording.filename}
      />
    </Form>
  );
}

export default function RecentRecordings() {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { projectPath } = getPreferenceValues<Preferences>();
  const { push } = useNavigation();

  useEffect(() => {
    loadRecordings();
  }, []);

  function loadRecordings() {
    try {
      setIsLoading(true);

      const recordingsDir = path.join(projectPath, "storage", "recordings");

      // Check if directory exists
      if (!fs.existsSync(recordingsDir)) {
        const errorMsg = "No recordings directory exists yet";
        console.warn(`[RecentRecordings] ${errorMsg}`);
        showToast({
          style: Toast.Style.Failure,
          title: "Recordings folder not found",
          message: errorMsg,
        });
        setRecordings([]);
        setIsLoading(false);
        return;
      }

      // Read all audio files (WAV and M4A)
      const files = fs.readdirSync(recordingsDir)
        .filter(f => f.endsWith(".wav") || f.endsWith(".m4a"))
        .map(filename => {
          const fullPath = path.join(recordingsDir, filename);
          const stats = fs.statSync(fullPath);

          return {
            filename,
            fullPath,
            createdDate: stats.mtime,
            createdDisplay: stats.mtime.toLocaleString(),
            sizeBytes: stats.size,
            sizeDisplay: formatBytes(stats.size),
            durationEstimate: estimateDuration(stats.size, filename),
          };
        })
        .sort((a, b) => b.createdDate.getTime() - a.createdDate.getTime()); // Newest first

      setRecordings(files);
      setIsLoading(false);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      console.error(`[RecentRecordings] Error loading recordings: ${errorMsg}`);
      showToast({
        style: Toast.Style.Failure,
        title: "Error loading recordings",
        message: errorMsg,
      });
      setIsLoading(false);
    }
  }

  async function deleteRecording(recording: Recording) {
    const confirmed = await confirmAlert({
      title: "Delete Recording",
      message: `Are you sure you want to delete "${recording.filename}"? This cannot be undone.`,
      primaryAction: {
        title: "Delete",
        style: Alert.ActionStyle.Destructive,
      },
    });

    if (confirmed) {
      try {
        fs.unlinkSync(recording.fullPath);
        const successMsg = `Deleted: ${recording.filename}`;
        console.log(`[RecentRecordings] ${successMsg}`);
        showToast({
          style: Toast.Style.Success,
          title: "Deleted",
          message: recording.filename,
        });
        loadRecordings();
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        console.error(`[RecentRecordings] Error deleting recording: ${errorMsg}`);
        showToast({
          style: Toast.Style.Failure,
          title: "Error deleting",
          message: errorMsg,
        });
      }
    }
  }

  function renameRecording(oldPath: string, newName: string) {
    try {
      const dir = path.dirname(oldPath);
      const newPath = path.join(dir, newName);

      // Check if file already exists
      if (fs.existsSync(newPath)) {
        const errorMsg = `File already exists: ${newName}`;
        console.warn(`[RecentRecordings] ${errorMsg}`);
        showToast({
          style: Toast.Style.Failure,
          title: "File already exists",
          message: newName,
        });
        return;
      }

      fs.renameSync(oldPath, newPath);
      const successMsg = `Renamed: ${newName}`;
      console.log(`[RecentRecordings] ${successMsg}`);
      showToast({
        style: Toast.Style.Success,
        title: "Renamed",
        message: newName,
      });
      loadRecordings();
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      console.error(`[RecentRecordings] Error renaming recording: ${errorMsg}`);
      showToast({
        style: Toast.Style.Failure,
        title: "Error renaming",
        message: errorMsg,
      });
    }
  }

  function openInFinder(filePath: string) {
    open(path.dirname(filePath));
  }

  function playRecording(filePath: string) {
    open(filePath);
  }

  async function transcribeRecording(recording: Recording) {
    const { pythonPath, projectPath, geminiApiKey, geminiModel, optimizeAudio } = getPreferenceValues<Preferences>();

    // Check if API key is configured
    if (!geminiApiKey || geminiApiKey.trim() === "") {
      const errorMsg = "Please configure Google Gemini API Key in extension preferences";
      console.error(`[RecentRecordings] ${errorMsg}`);
      showToast({
        style: Toast.Style.Failure,
        title: "API Key Missing",
        message: errorMsg,
      });
      return;
    }

    const transcriptDir = path.join(projectPath, "storage", "transcriptions");
    const transcriptPath = path.join(transcriptDir, recording.filename.replace(/\.(wav|m4a)$/, ".md"));

    // Check if transcription already exists
    const hasTranscript = fs.existsSync(transcriptPath);

    if (hasTranscript) {
      const confirmed = await confirmAlert({
        title: "Transcription Already Exists",
        message: `A transcription already exists for "${recording.filename}". Do you want to transcribe again?`,
        primaryAction: {
          title: "Transcribe Again",
          style: Alert.ActionStyle.Default,
        },
      });

      if (!confirmed) {
        return;
      }
    }

    console.log(`[Transcription] Starting for: ${recording.fullPath}`);

    // Generate session ID for progress tracking
    const sessionId = `transcribe_${Date.now()}`;
    const statusDir = path.join(projectPath, "storage", "status");
    const statusFile = path.join(statusDir, `${sessionId}.json`);

    try {
      // Create initial status file BEFORE spawning Python process to avoid race condition
      // This ensures the UI shows status immediately when it navigates to TranscriptionProgress
      fs.mkdirSync(statusDir, { recursive: true });
      fs.writeFileSync(
        statusFile,
        JSON.stringify({
          step: "starting",
          step_number: 0,
          total_steps: 4,
          progress: 0,
          message: "Starting transcription...",
        })
      );
      console.log(`[Transcription] Initial status file created: ${statusFile}`);

      const scriptPath = path.join(projectPath, "src", "transcriber.py");

      const args = [
        scriptPath,
        recording.fullPath,
        "--api-key",
        geminiApiKey,
        "--model",
        geminiModel || "models/gemini-1.5-flash",
        "--output-file",
        transcriptPath,
        "--session-id",
        sessionId,
      ];

      if (optimizeAudio) {
        args.push("--optimize");
      }

      const process = spawn(pythonPath, args, {
        cwd: projectPath,
      });

      let stdout = "";
      let stderr = "";

      process.stdout.on("data", (data) => {
        stdout += data.toString();
      });

      process.stderr.on("data", (data) => {
        stderr += data.toString();
      });

      process.on("close", (code) => {
        console.log(`[Transcription] Process exited with code: ${code}`);
        if (stdout) console.log(`[Transcription] stdout: ${stdout}`);
        if (stderr) console.log(`[Transcription] stderr: ${stderr}`);

        if (code === 0) {
          try {
            // Extract JSON from stdout - Python may output text before the JSON response
            // Find the last JSON line (starts with '{')
            const lines = stdout.split('\n').reverse();
            const jsonLine = lines.find(line => line.trim().startsWith('{'));

            if (!jsonLine) {
              throw new Error("No JSON response found in output");
            }

            const result = JSON.parse(jsonLine);

            if (result.success) {
              const successMsg = `Transcription Complete: Saved to ${path.basename(result.transcript_file)}`;
              console.log(`[Transcription] ${successMsg}`);
              showToast({
                style: Toast.Style.Success,
                title: "Transcription Complete",
                message: `Saved to: ${path.basename(result.transcript_file)}`,
              });
            } else {
              const errorMsg = result.error || "Unknown error";
              console.error(`[Transcription] Transcription failed: ${errorMsg}`);
              showToast({
                style: Toast.Style.Failure,
                title: "Transcription Failed",
                message: errorMsg,
              });
              console.log(`[Transcription] Progress file preserved as history: ${statusFile}`);
            }
          } catch (e) {
            const errorMsg = e instanceof Error ? e.message : (stdout || stderr || "Unknown error");
            console.error(`[Transcription] Error parsing response: ${errorMsg}`);
            showToast({
              style: Toast.Style.Failure,
              title: "Error parsing response",
              message: errorMsg,
            });
            console.log(`[Transcription] Progress file preserved as history: ${statusFile}`);
          }
        } else {
          const errorMsg = stderr || `Process exited with code ${code}`;
          console.error(`[Transcription] Process exited with code ${code}: ${errorMsg}`);
          showToast({
            style: Toast.Style.Failure,
            title: "Transcription Failed",
            message: errorMsg,
          });
          console.log(`[Transcription] Progress file preserved as history: ${statusFile}`);
        }

        loadRecordings(); // Refresh to show transcript file

        // Note: Progress files are preserved as history and can be deleted manually
        // via the Transcription Progress view if needed
      });

      process.on("error", (error) => {
        const errorMsg = error.message;
        console.error(`[Transcription] Process error: ${errorMsg}`);
        showToast({
          style: Toast.Style.Failure,
          title: "Error starting transcription",
          message: errorMsg,
        });
      });

      // Show toast and navigate to progress monitoring
      const startMsg = "Transcription Started: Navigating to progress view...";
      console.log(`[Transcription] ${startMsg}`);
      showToast({
        style: Toast.Style.Success,
        title: "Transcription Started",
        message: "Navigating to progress view...",
      });

      // Navigate to transcription progress view
      push(<TranscriptionProgress />);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      console.error(`[RecentRecordings] Error transcribing recording: ${errorMsg}`);
      showToast({
        style: Toast.Style.Failure,
        title: "Error",
        message: errorMsg,
      });
    }
  }

  function openTranscript(recording: Recording) {
    const transcriptDir = path.join(getPreferenceValues<Preferences>().projectPath, "storage", "transcriptions");
    const transcriptPath = path.join(transcriptDir, recording.filename.replace(/\.(wav|m4a)$/, ".md"));
    if (fs.existsSync(transcriptPath)) {
      open(transcriptPath);
    } else {
      const errorMsg = "Please transcribe this recording first";
      console.warn(`[RecentRecordings] ${errorMsg}`);
      showToast({
        style: Toast.Style.Failure,
        title: "Transcript Not Found",
        message: errorMsg,
      });
    }
  }

  if (recordings.length === 0 && !isLoading) {
    return (
      <List>
        <List.EmptyView
          icon={Icon.Microphone}
          title="No Recordings Yet"
          description="Start your first recording with 'Start Recording' command"
        />
      </List>
    );
  }

  return (
    <List isLoading={isLoading} searchBarPlaceholder="Search recordings...">
      <List.Section title={`${recordings.length} Recording${recordings.length !== 1 ? "s" : ""}`}>
        {recordings.map((recording) => {
          const transcriptDir = path.join(projectPath, "storage", "transcriptions");
          const transcriptPath = path.join(transcriptDir, recording.filename.replace(/\.(wav|m4a)$/, ".md"));
          const hasTranscript = fs.existsSync(transcriptPath);

          return (
            <List.Item
              key={recording.fullPath}
              title={recording.filename}
              subtitle={recording.createdDisplay}
              icon={Icon.Microphone}
              accessories={[
                { text: recording.durationEstimate, icon: Icon.Clock },
                { text: recording.sizeDisplay, icon: Icon.HardDrive },
                ...(hasTranscript ? [{ icon: Icon.Document, tooltip: "Transcription available" }] : []),
              ]}
              actions={
                <ActionPanel>
                  <ActionPanel.Section title="Actions">
                    <Action
                      title="Play Recording"
                      icon={Icon.Play}
                      onAction={() => playRecording(recording.fullPath)}
                    />
                    {hasTranscript && (
                      <Action
                        title="Open Transcript"
                        icon={Icon.Document}
                        shortcut={{
                          macOS: { modifiers: ["cmd"], key: "t" },
                          windows: { modifiers: ["ctrl"], key: "t" },
                        }}
                        onAction={() => openTranscript(recording)}
                      />
                    )}
                    <Action
                      title={hasTranscript ? "Transcribe Again" : "Transcribe with Gemini"}
                      icon={Icon.SpeechBubble}
                      shortcut={{
                        macOS: { modifiers: ["cmd", "shift"], key: "t" },
                        windows: { modifiers: ["ctrl", "shift"], key: "t" },
                      }}
                      onAction={() => transcribeRecording(recording)}
                    />
                    <Action.Push
                      title="Rename"
                      icon={Icon.Pencil}
                      shortcut={{
                        macOS: { modifiers: ["cmd"], key: "r" },
                        windows: { modifiers: ["ctrl"], key: "r" },
                      }}
                      target={<RenameForm recording={recording} onRename={renameRecording} />}
                    />
                    <Action
                      title="Delete"
                      icon={Icon.Trash}
                      style={Action.Style.Destructive}
                      shortcut={{
                        macOS: { modifiers: ["cmd"], key: "backspace" },
                        windows: { modifiers: ["ctrl", "shift"], key: "d" },
                      }}
                      onAction={() => deleteRecording(recording)}
                    />
                  </ActionPanel.Section>
                  <ActionPanel.Section title="View">
                    <Action
                      title="Open in Finder"
                      icon={Icon.Finder}
                      onAction={() => openInFinder(recording.fullPath)}
                    />
                    <Action.CopyToClipboard
                      title="Copy File Path"
                      content={recording.fullPath}
                      shortcut={{
                        macOS: { modifiers: ["cmd"], key: "c" },
                        windows: { modifiers: ["ctrl"], key: "c" },
                      }}
                    />
                  </ActionPanel.Section>
                  <ActionPanel.Section title="Refresh">
                    <Action
                      title="Refresh List"
                      icon={Icon.ArrowClockwise}
                      shortcut={{
                        macOS: { modifiers: ["cmd", "shift"], key: "r" },
                        windows: { modifiers: ["ctrl", "shift"], key: "r" },
                      }}
                      onAction={loadRecordings}
                    />
                  </ActionPanel.Section>
                </ActionPanel>
              }
            />
          );
        })}
      </List.Section>
    </List>
  );
}
