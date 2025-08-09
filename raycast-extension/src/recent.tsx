import {
  ActionPanel,
  Action,
  List,
  showToast,
  Toast,
  getPreferenceValues,
  Detail,
} from "@raycast/api";
import { useState, useEffect } from "react";
import { exec } from "child_process";
import { promisify } from "util";
import { readFileSync, existsSync } from "fs";
// import { join } from "path"; // Unused import removed

const execAsync = promisify(exec);

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

  useEffect(() => {
    loadRecentTranscriptions();
  }, []);

  async function loadRecentTranscriptions() {
    try {
      setIsLoading(true);
      const { stdout } = await execAsync(
        `cd "${preferences.projectPath}" && ${preferences.pythonPath} main.py --list-transcriptions --json`,
      );

      // Extrair JSON do stdout, ignorando logs coloridos
      let jsonStr = stdout;
      const lines = stdout.split('\n');
      const jsonStartIndex = lines.findIndex(line => line.trim().startsWith('[') || line.trim().startsWith('{'));
      
      if (jsonStartIndex !== -1) {
        jsonStr = lines.slice(jsonStartIndex).join('\n');
        const jsonLines = jsonStr.split('\n');
        const jsonEndIndex = jsonLines.findLastIndex(line => line.trim().endsWith(']') || line.trim().endsWith('}'));
        
        if (jsonEndIndex !== -1) {
          jsonStr = jsonLines.slice(0, jsonEndIndex + 1).join('\n');
        }
      }

      const data = JSON.parse(jsonStr);
      setTranscriptions(data);
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Erro ao carregar transcrições",
        message: "Verifique se existem transcrições disponíveis",
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function openTranscription(path: string) {
    try {
      await execAsync(`code "${path}"`);
      showToast({
        style: Toast.Style.Success,
        title: "Arquivo aberto",
        message: "Transcrição aberta no editor",
      });
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Erro ao abrir arquivo",
        message: String(error),
      });
    }
  }

  async function exportTranscription(filename: string, format: string) {
    try {
      showToast({
        style: Toast.Style.Animated,
        title: "Exportando...",
        message: `Formato: ${format.toUpperCase()}`,
      });

      await execAsync(
        `cd "${preferences.projectPath}" && ${preferences.pythonPath} main.py --export "${filename}" --format ${format}`,
      );

      showToast({
        style: Toast.Style.Success,
        title: "Exportação concluída!",
        message: `Arquivo exportado em ${format.toUpperCase()}`,
      });
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Erro na exportação",
        message: String(error),
      });
    }
  }

  function getTranscriptionPreview(path: string): string {
    try {
      if (existsSync(path)) {
        const content = readFileSync(path, "utf-8");
        // Return first 200 characters as preview
        return content.substring(0, 200) + (content.length > 200 ? "..." : "");
      }
      return "Preview não disponível";
    } catch {
      return "Erro ao carregar preview";
    }
  }

  return (
    <List isLoading={isLoading} searchBarPlaceholder="Buscar transcrições...">
      <List.Section title="Transcrições Recentes">
        {transcriptions.map((transcription) => (
          <List.Item
            key={transcription.filename}
            title={transcription.filename}
            subtitle={`${transcription.duration} • ${transcription.language} • ${transcription.model}`}
            accessories={[
              { text: transcription.created },
              { text: transcription.size },
            ]}
            actions={
              <ActionPanel>
                <ActionPanel.Section title="Visualizar">
                  <Action.Push
                    title="Ver Preview"
                    target={
                      <Detail
                        markdown={`# ${transcription.filename}\n\n**Criado:** ${transcription.created}\n**Duração:** ${transcription.duration}\n**Modelo:** ${transcription.model}\n**Idioma:** ${transcription.language}\n\n---\n\n${getTranscriptionPreview(transcription.path)}`}
                        actions={
                          <ActionPanel>
                            <Action
                              title="Abrir Arquivo Completo"
                              onAction={() =>
                                openTranscription(transcription.path)
                              }
                            />
                          </ActionPanel>
                        }
                      />
                    }
                  />
                  <Action
                    title="Abrir No Editor"
                    onAction={() => openTranscription(transcription.path)}
                  />
                </ActionPanel.Section>
                <ActionPanel.Section title="Exportar">
                  <Action
                    title="Exportar Como Txt"
                    onAction={() =>
                      exportTranscription(transcription.filename, "txt")
                    }
                  />
                  <Action
                    title="Exportar Como JSON"
                    onAction={() =>
                      exportTranscription(transcription.filename, "json")
                    }
                  />
                  <Action
                    title="Exportar Como Srt"
                    onAction={() =>
                      exportTranscription(transcription.filename, "srt")
                    }
                  />
                </ActionPanel.Section>
                <ActionPanel.Section title="Atualizar">
                  <Action
                    title="Atualizar Lista"
                    onAction={loadRecentTranscriptions}
                    shortcut={{ modifiers: ["cmd"], key: "r" }}
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
