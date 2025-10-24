import {
  ActionPanel,
  Action,
  List,
  showToast,
  Toast,
  getPreferenceValues,
  Detail,
} from "@raycast/api";
import { useState, useEffect, useRef } from "react";
import { exec } from "child_process";
import { promisify } from "util";
const execAsync = promisify(exec);
import { readFileSync, existsSync } from "fs";
import { StdioClient } from "./stdio";
import { runCliJSON } from "./cli";

interface Preferences {
  pythonPath: string;
  projectPath: string;
  defaultModel: string;
}

interface Transcription {
  filename: string;
  path: string;
  created: string;
  duration: string;
  model: string;
  language: string;
  size: string;
}

export default function RecentTranscriptions() {
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const preferences = getPreferenceValues<Preferences>();
  const clientRef = useRef<StdioClient | null>(null);
  const runnerMode = (preferences as any).runnerMode || "stdio";

  useEffect(() => {
    if (runnerMode === "stdio") {
      clientRef.current = new StdioClient(
        preferences.pythonPath,
        preferences.projectPath,
        undefined
      );
      clientRef.current.start();
    }
    loadRecentTranscriptions();
    return () => clientRef.current?.stop();
  }, []);

  async function loadRecentTranscriptions() {
    try {
      setIsLoading(true);
      const resp: any =
        runnerMode === "stdio"
          ? await clientRef.current?.request("files.list", { type: "transcriptions", limit: 20 })
          : await runCliJSON(["-m", "src.core.runtime_cli", "files", "transcriptions", "--limit", "20"]);
      const items = resp?.data?.items || [];
      setTranscriptions(items);
    } catch (error) {
      showToast({ style: Toast.Style.Failure, title: "Erro ao carregar transcricoes", message: "Verifique se existem transcricoes disponiveis" });
    } finally {
      setIsLoading(false);
    }
  }

  async function openTranscription(path: string) {
    try {
      await execAsync(`code "${path}"`);
      showToast({ style: Toast.Style.Success, title: "Arquivo aberto", message: "Transcricao aberta no editor" });
    } catch (error) {
      showToast({ style: Toast.Style.Failure, title: "Erro ao abrir arquivo", message: String(error) });
    }
  }

  async function exportTranscription(filename: string, format: string) {
    try {
      showToast({ style: Toast.Style.Animated, title: "Exportando...", message: `Formato: ${format.toUpperCase()}` });
      await execAsync(
        `cd "${preferences.projectPath}" && ${preferences.pythonPath} main.py --export "${filename}" --format ${format}`
      );
      showToast({ style: Toast.Style.Success, title: "Exportacao concluida!", message: `Arquivo exportado em ${format.toUpperCase()}` });
    } catch (error) {
      showToast({ style: Toast.Style.Failure, title: "Erro na exportacao", message: String(error) });
    }
  }

  function getTranscriptionPreview(path: string): string {
    try {
      if (existsSync(path)) {
        const content = readFileSync(path, "utf-8");
        return content.substring(0, 200) + (content.length > 200 ? "..." : "");
      }
      return "Preview nao disponivel";
    } catch {
      return "Erro ao carregar preview";
    }
  }

  return (
    <List isLoading={isLoading} searchBarPlaceholder="Buscar transcricoes...">
      <List.Section title="Transcricoes Recentes">
        {transcriptions.map((transcription) => (
          <List.Item
            key={transcription.filename}
            title={transcription.filename}
            subtitle={`${transcription.duration} | ${transcription.language} | ${transcription.model}`}
            accessories={[{ text: transcription.created }, { text: transcription.size }]}
            actions={
              <ActionPanel>
                <ActionPanel.Section title="Visualizar">
                  <Action.Push
                    title="Ver Preview"
                    target={
                      <Detail
                        markdown={`# ${transcription.filename}\n\n**Criado:** ${transcription.created}\n**Duracao:** ${transcription.duration}\n**Modelo:** ${transcription.model}\n**Idioma:** ${transcription.language}\n\n---\n\n${getTranscriptionPreview(transcription.path)}`}
                        actions={
                          <ActionPanel>
                            <Action title="Abrir Arquivo Completo" onAction={() => openTranscription(transcription.path)} />
                          </ActionPanel>
                        }
                      />
                    }
                  />
                  <Action title="Abrir No Editor" onAction={() => openTranscription(transcription.path)} />
                </ActionPanel.Section>
                <ActionPanel.Section title="Exportar">
                  <Action title="Exportar Como Txt" onAction={() => exportTranscription(transcription.filename, "txt")} />
                  <Action title="Exportar Como JSON" onAction={() => exportTranscription(transcription.filename, "json")} />
                  <Action title="Exportar Como Srt" onAction={() => exportTranscription(transcription.filename, "srt")} />
                </ActionPanel.Section>
                <ActionPanel.Section title="Atualizar">
                  <Action title="Atualizar Lista" onAction={loadRecentTranscriptions} shortcut={{ modifiers: ["cmd"], key: "r" }} />
                </ActionPanel.Section>
              </ActionPanel>
            }
          />
        ))}
      </List.Section>
    </List>
  );
}

