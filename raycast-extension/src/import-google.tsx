import { Action, ActionPanel, List, showToast, Toast, getPreferenceValues, Icon, open } from "@raycast/api";
import { useEffect, useState } from "react";
import * as fs from "fs";
import * as path from "path";
import { spawn } from "child_process";

interface Preferences {
  pythonPath: string;
  projectPath: string;
  geminiApiKey?: string;
  geminiModel?: string; // e.g., models/gemini-2.0-flash-exp
  optimizeAudio?: boolean;
}

interface AudioEntry {
  filePath: string;
  name: string;
  size: string;
  mtime: Date;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

export default function ImportGoogle() {
  const [items, setItems] = useState<AudioEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const prefs = getPreferenceValues<Preferences>();

  useEffect(() => {
    try {
      const dir = path.join(prefs.projectPath, "storage", "recordings");
      if (!fs.existsSync(dir)) {
        setItems([]);
        setIsLoading(false);
        return;
      }
      const files = fs
        .readdirSync(dir)
        .filter((f) => [".wav", ".mp3", ".m4a", ".flac", ".ogg"].some((ext) => f.toLowerCase().endsWith(ext)))
        .map((f) => {
          const p = path.join(dir, f);
          const st = fs.statSync(p);
          return { filePath: p, name: f, size: formatBytes(st.size), mtime: st.mtime } as AudioEntry;
        })
        .sort((a, b) => b.mtime.getTime() - a.mtime.getTime());
      setItems(files);
    } catch {
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  async function transcribe(entry: AudioEntry) {
    try {
      if (!prefs.geminiApiKey) {
        await showToast({ style: Toast.Style.Failure, title: "Missing Gemini API key", message: "Set in extension preferences" });
        return;
      }
      const script = path.join(prefs.projectPath, "transcribe_audio.py");
      if (!fs.existsSync(script)) {
        await showToast({ style: Toast.Style.Failure, title: "Script not found", message: "transcribe_audio.py is missing" });
        return;
      }
      await showToast({ style: Toast.Style.Animated, title: "Uploading to Gemini", message: entry.name });
      const args = [script, entry.filePath, "--api-key", prefs.geminiApiKey];
      if (prefs.geminiModel) {
        args.push("--model", prefs.geminiModel);
      }
      if (prefs.optimizeAudio) {
        args.push("--optimize");
      }
      const child = spawn(prefs.pythonPath, args, { cwd: prefs.projectPath, windowsHide: true });
      let out = "";
      let err = "";
      child.stdout.on("data", (d) => (out += d.toString()));
      child.stderr.on("data", (d) => (err += d.toString()));
      child.on("close", async (code) => {
        try {
          const res = JSON.parse(out || "{}");
          if (res.success) {
            await showToast({ style: Toast.Style.Success, title: "Transcription Complete", message: path.basename(res.transcript_file || "") });
            if (res.transcript_file) open(res.transcript_file);
          } else {
            await showToast({ style: Toast.Style.Failure, title: "Transcription Failed", message: res.error || err.substring(0, 120) });
          }
        } catch (e) {
          await showToast({ style: Toast.Style.Failure, title: "Unexpected Response", message: err.substring(0, 120) });
        }
      });
    } catch (e) {
      await showToast({ style: Toast.Style.Failure, title: "Error", message: (e as Error).message });
    }
  }

  return (
    <List isLoading={isLoading} searchBarPlaceholder="Select an audio file to transcribe with Gemini">
      <List.Section title={`${items.length} Audio File${items.length !== 1 ? "s" : ""}`}>
        {items.map((it) => (
          <List.Item
            key={it.filePath}
            title={it.name}
            subtitle={it.size}
            icon={Icon.Waveform}
            accessories={[{ date: it.mtime, tooltip: "Modified" }]}
            actions={
              <ActionPanel>
                <Action title="Transcribe with Google Gemini" icon={Icon.SpeechBubble} onAction={() => transcribe(it)} />
                <Action.OpenWith path={it.filePath} title="Open With..." />
                <Action.ShowInFinder path={it.filePath} />
              </ActionPanel>
            }
          />
        ))}
      </List.Section>
    </List>
  );
}

