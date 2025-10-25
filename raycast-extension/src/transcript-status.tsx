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
} from "@raycast/api";
import { useState, useEffect } from "react";
import * as fs from "fs";
import * as path from "path";

interface Preferences {
  pythonPath: string;
  projectPath: string;
}

interface Transcription {
  audioFile: string;
  audioFilename: string;
  transcriptFile: string;
  transcriptFilename: string;
  createdDate: Date;
  createdDisplay: string;
  audioSizeBytes: number;
  audioSizeDisplay: string;
  transcriptSizeBytes: number;
  transcriptSizeDisplay: string;
  hasAudio: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

export default function TranscriptStatus() {
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { projectPath } = getPreferenceValues<Preferences>();

  useEffect(() => {
    loadTranscriptions();
  }, []);

  function loadTranscriptions() {
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
        setTranscriptions([]);
        setIsLoading(false);
        return;
      }

      // Find all transcription files
      const files = fs
        .readdirSync(recordingsDir)
        .filter((f) => f.endsWith("_transcription.txt"))
        .map((filename) => {
          const transcriptPath = path.join(recordingsDir, filename);
          const transcriptStats = fs.statSync(transcriptPath);

          // Derive audio filename
          const audioFilename = filename.replace("_transcription.txt", ".wav");
          const audioPath = path.join(recordingsDir, audioFilename);
          const hasAudio = fs.existsSync(audioPath);

          let audioStats: fs.Stats | null = null;
          if (hasAudio) {
            audioStats = fs.statSync(audioPath);
          }

          return {
            audioFile: audioPath,
            audioFilename: audioFilename,
            transcriptFile: transcriptPath,
            transcriptFilename: filename,
            createdDate: transcriptStats.mtime,
            createdDisplay: transcriptStats.mtime.toLocaleString(),
            audioSizeBytes: audioStats ? audioStats.size : 0,
            audioSizeDisplay: audioStats ? formatBytes(audioStats.size) : "N/A",
            transcriptSizeBytes: transcriptStats.size,
            transcriptSizeDisplay: formatBytes(transcriptStats.size),
            hasAudio,
          };
        })
        .sort((a, b) => b.createdDate.getTime() - a.createdDate.getTime()); // Newest first

      setTranscriptions(files);
      setIsLoading(false);
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Error loading transcriptions",
        message: error instanceof Error ? error.message : String(error),
      });
      setIsLoading(false);
    }
  }

  function openTranscript(transcription: Transcription) {
    open(transcription.transcriptFile);
  }

  function openAudio(transcription: Transcription) {
    if (transcription.hasAudio) {
      open(transcription.audioFile);
    } else {
      showToast({
        style: Toast.Style.Failure,
        title: "Audio File Not Found",
        message: "The original audio file has been deleted or moved",
      });
    }
  }

  function openInFinder(filePath: string) {
    open(path.dirname(filePath));
  }

  async function deleteTranscript(transcription: Transcription) {
    try {
      fs.unlinkSync(transcription.transcriptFile);
      showToast({
        style: Toast.Style.Success,
        title: "Transcript Deleted",
        message: transcription.transcriptFilename,
      });
      loadTranscriptions();
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Error deleting transcript",
        message: error instanceof Error ? error.message : String(error),
      });
    }
  }

  if (transcriptions.length === 0 && !isLoading) {
    return (
      <List>
        <List.EmptyView
          icon={Icon.Document}
          title="No Transcriptions Yet"
          description="Transcribe recordings from 'Recent Recordings' command using Cmd+Shift+T"
        />
      </List>
    );
  }

  return (
    <List isLoading={isLoading} searchBarPlaceholder="Search transcriptions...">
      <List.Section title={`${transcriptions.length} Transcription${transcriptions.length !== 1 ? "s" : ""}`}>
        {transcriptions.map((transcription) => (
          <List.Item
            key={transcription.transcriptFile}
            title={transcription.audioFilename.replace(".wav", "")}
            subtitle={transcription.createdDisplay}
            icon={{
              source: Icon.Document,
              tintColor: transcription.hasAudio ? Color.Green : Color.Red,
            }}
            accessories={[
              {
                text: transcription.transcriptSizeDisplay,
                icon: Icon.Document,
                tooltip: "Transcript size",
              },
              ...(transcription.hasAudio
                ? [
                    {
                      text: transcription.audioSizeDisplay,
                      icon: Icon.Microphone,
                      tooltip: "Audio size",
                    },
                  ]
                : [
                    {
                      icon: Icon.ExclamationMark,
                      tooltip: "Audio file missing",
                    },
                  ]),
            ]}
            actions={
              <ActionPanel>
                <ActionPanel.Section title="Actions">
                  <Action
                    title="Open Transcript"
                    icon={Icon.Document}
                    onAction={() => openTranscript(transcription)}
                  />
                  {transcription.hasAudio && (
                    <Action
                      title="Play Audio"
                      icon={Icon.Play}
                      shortcut={{ modifiers: ["cmd"], key: "p" }}
                      onAction={() => openAudio(transcription)}
                    />
                  )}
                  <Action
                    title="Delete Transcript"
                    icon={Icon.Trash}
                    style={Action.Style.Destructive}
                    shortcut={{ modifiers: ["cmd"], key: "backspace" }}
                    onAction={() => deleteTranscript(transcription)}
                  />
                </ActionPanel.Section>
                <ActionPanel.Section title="View">
                  <Action
                    title="Open in Finder"
                    icon={Icon.Finder}
                    onAction={() => openInFinder(transcription.transcriptFile)}
                  />
                  <Action.CopyToClipboard
                    title="Copy Transcript Path"
                    content={transcription.transcriptFile}
                    shortcut={{ modifiers: ["cmd"], key: "c" }}
                  />
                  {transcription.hasAudio && (
                    <Action.CopyToClipboard
                      title="Copy Audio Path"
                      content={transcription.audioFile}
                      shortcut={{ modifiers: ["cmd", "shift"], key: "c" }}
                    />
                  )}
                </ActionPanel.Section>
                <ActionPanel.Section title="Refresh">
                  <Action
                    title="Refresh List"
                    icon={Icon.ArrowClockwise}
                    shortcut={{ modifiers: ["cmd", "shift"], key: "r" }}
                    onAction={loadTranscriptions}
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
