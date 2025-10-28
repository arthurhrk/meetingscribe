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

function estimateDuration(sizeBytes: number, quality: string = "professional"): string {
  // Professional quality: ~11 MB/min = 183,333 bytes/sec
  // Standard: ~10 MB/min = 166,667 bytes/sec
  // Quick: ~2 MB/min = 33,333 bytes/sec
  const bytesPerSecond = 183333; // Default to professional
  const seconds = Math.round(sizeBytes / bytesPerSecond);

  if (seconds < 60) return `~${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return remainingSeconds > 0 ? `~${minutes}m ${remainingSeconds}s` : `~${minutes}m`;
}

function RenameForm({ recording, onRename }: { recording: Recording; onRename: (oldPath: string, newName: string) => void }) {
  const { pop } = useNavigation();
  const [newName, setNewName] = useState(recording.filename.replace(".wav", ""));

  function handleSubmit() {
    if (!newName.trim()) {
      showToast({ style: Toast.Style.Failure, title: "Invalid name", message: "Name cannot be empty" });
      return;
    }

    const finalName = newName.trim().endsWith(".wav") ? newName.trim() : `${newName.trim()}.wav`;
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
        text={`${newName.trim() || "filename"}.wav`}
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

  useEffect(() => {
    loadRecordings();
  }, []);

  function loadRecordings() {
    try {
      setIsLoading(true);

      const recordingsDir = path.join(projectPath, "storage", "recordings");

      // Check if directory exists
      if (!fs.existsSync(recordingsDir)) {
        showToast({
          style: Toast.Style.Failure,
          title: "Recordings folder not found",
          message: "No recordings directory exists yet",
        });
        setRecordings([]);
        setIsLoading(false);
        return;
      }

      // Read all WAV files
      const files = fs.readdirSync(recordingsDir)
        .filter(f => f.endsWith(".wav"))
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
            durationEstimate: estimateDuration(stats.size),
          };
        })
        .sort((a, b) => b.createdDate.getTime() - a.createdDate.getTime()); // Newest first

      setRecordings(files);
      setIsLoading(false);
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Error loading recordings",
        message: error instanceof Error ? error.message : String(error),
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
        showToast({
          style: Toast.Style.Success,
          title: "Deleted",
          message: recording.filename,
        });
        loadRecordings();
      } catch (error) {
        showToast({
          style: Toast.Style.Failure,
          title: "Error deleting",
          message: error instanceof Error ? error.message : String(error),
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
        showToast({
          style: Toast.Style.Failure,
          title: "File already exists",
          message: newName,
        });
        return;
      }

      fs.renameSync(oldPath, newPath);
      showToast({
        style: Toast.Style.Success,
        title: "Renamed",
        message: newName,
      });
      loadRecordings();
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Error renaming",
        message: error instanceof Error ? error.message : String(error),
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
      showToast({
        style: Toast.Style.Failure,
        title: "API Key Missing",
        message: "Please configure Google Gemini API Key in extension preferences",
      });
      return;
    }

    const transcriptDir = path.join(projectPath, "storage", "transcriptions");
    const transcriptPath = path.join(transcriptDir, recording.filename.replace(".wav", ".md"));

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

    const toast = await showToast({
      style: Toast.Style.Animated,
      title: "Starting transcription...",
      message: recording.filename,
    });

    console.log(`[Transcription] Starting for: ${recording.fullPath}`);

    try {
      const scriptPath = path.join(projectPath, "scripts", "import_google.py");

      const args = [
        scriptPath,
        recording.fullPath,
        "--api-key",
        geminiApiKey,
        "--model",
        geminiModel || "models/gemini-1.5-flash",
        "--output-file",
        transcriptPath,
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
            const result = JSON.parse(stdout);

            if (result.success) {
              toast.style = Toast.Style.Success;
              toast.title = "Transcription Complete";
              toast.message = `Saved to: ${path.basename(result.transcript_file)}`;
            } else {
              toast.style = Toast.Style.Failure;
              toast.title = "Transcription Failed";
              toast.message = result.error || "Unknown error";
            }
          } catch (e) {
            toast.style = Toast.Style.Failure;
            toast.title = "Error parsing response";
            toast.message = stdout || stderr;
          }
        } else {
          toast.style = Toast.Style.Failure;
          toast.title = "Transcription Failed";
          toast.message = stderr || `Process exited with code ${code}`;
        }

        loadRecordings(); // Refresh to show transcript file
      });

      process.on("error", (error) => {
        console.error(`[Transcription] Process error: ${error.message}`);
        toast.style = Toast.Style.Failure;
        toast.title = "Error starting transcription";
        toast.message = error.message;
      });
    } catch (error) {
      toast.style = Toast.Style.Failure;
      toast.title = "Error";
      toast.message = error instanceof Error ? error.message : String(error);
    }
  }

  function openTranscript(recording: Recording) {
    const transcriptDir = path.join(getPreferenceValues<Preferences>().projectPath, "storage", "transcriptions");
    const transcriptPath = path.join(transcriptDir, recording.filename.replace(".wav", ".md"));
    if (fs.existsSync(transcriptPath)) {
      open(transcriptPath);
    } else {
      showToast({
        style: Toast.Style.Failure,
        title: "Transcript Not Found",
        message: "Please transcribe this recording first",
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
          const transcriptPath = path.join(transcriptDir, recording.filename.replace(".wav", ".md"));
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
                        shortcut={{ modifiers: ["cmd"], key: "t" }}
                        onAction={() => openTranscript(recording)}
                      />
                    )}
                    <Action
                      title={hasTranscript ? "Transcribe Again" : "Transcribe with Gemini"}
                      icon={Icon.SpeechBubble}
                      shortcut={{ modifiers: ["cmd", "shift"], key: "t" }}
                      onAction={() => transcribeRecording(recording)}
                    />
                    <Action.Push
                      title="Rename"
                      icon={Icon.Pencil}
                      shortcut={{ modifiers: ["cmd"], key: "r" }}
                      target={<RenameForm recording={recording} onRename={renameRecording} />}
                    />
                    <Action
                      title="Delete"
                      icon={Icon.Trash}
                      style={Action.Style.Destructive}
                      shortcut={{ modifiers: ["cmd"], key: "backspace" }}
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
                      shortcut={{ modifiers: ["cmd"], key: "c" }}
                    />
                  </ActionPanel.Section>
                  <ActionPanel.Section title="Refresh">
                    <Action
                      title="Refresh List"
                      icon={Icon.ArrowClockwise}
                      shortcut={{ modifiers: ["cmd", "shift"], key: "r" }}
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
