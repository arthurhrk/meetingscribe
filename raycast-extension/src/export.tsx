import {
  ActionPanel,
  Action,
  List,
  Form,
  showToast,
  Toast,
  getPreferenceValues,
  popToRoot,
} from "@raycast/api";
import { useState, useEffect } from "react";
import { exec } from "child_process";
import { promisify } from "util";

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
}

const exportFormats = [
  { title: "TXT - Texto simples com timestamps", value: "txt" },
  { title: "JSON - Estruturado com metadados", value: "json" },
  { title: "SRT - Legendas para vídeo", value: "srt" },
  { title: "VTT - WebVTT para web", value: "vtt" },
  { title: "XML - Estruturado para processamento", value: "xml" },
  { title: "CSV - Planilha com dados segmentados", value: "csv" },
];

export default function QuickExport() {
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string>("");
  const preferences = getPreferenceValues<Preferences>();

  useEffect(() => {
    loadTranscriptions();
  }, []);

  async function loadTranscriptions() {
    try {
      setIsLoading(true);
      const { stdout } = await execAsync(
        `cd "${preferences.projectPath}" && ${preferences.pythonPath} main.py --list-transcriptions --json --limit 10`,
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

  async function quickExport(filename: string, format: string) {
    try {
      showToast({
        style: Toast.Style.Animated,
        title: "Exportando...",
        message: `${filename} → ${format.toUpperCase()}`,
      });

      await execAsync(
        `cd "${preferences.projectPath}" && ${preferences.pythonPath} main.py --export "${filename}" --format ${format}`,
      );

      showToast({
        style: Toast.Style.Success,
        title: "Exportação concluída!",
        message: `Arquivo salvo em ${format.toUpperCase()}`,
      });
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Erro na exportação",
        message: String(error),
      });
    }
  }

  async function handleFormSubmit(values: { format: string }) {
    await quickExport(selectedFile, values.format);
    popToRoot();
  }

  if (showForm) {
    return (
      <Form
        actions={
          <ActionPanel>
            <Action.SubmitForm title="Exportar" onSubmit={handleFormSubmit} />
            <Action
              title="Voltar"
              onAction={() => setShowForm(false)}
              shortcut={{ modifiers: ["cmd"], key: "backspace" }}
            />
          </ActionPanel>
        }
      >
        <Form.Description text={`Exportando: ${selectedFile}`} />
        <Form.Dropdown id="format" title="Formato" defaultValue="txt">
          {exportFormats.map((format) => (
            <Form.Dropdown.Item
              key={format.value}
              value={format.value}
              title={format.title}
            />
          ))}
        </Form.Dropdown>
      </Form>
    );
  }

  return (
    <List
      isLoading={isLoading}
      searchBarPlaceholder="Buscar transcrições para exportar..."
    >
      <List.Section title="Transcrições Disponíveis para Exportação">
        {transcriptions.map((transcription) => (
          <List.Item
            key={transcription.filename}
            title={transcription.filename}
            subtitle={`${transcription.duration} • ${transcription.language} • ${transcription.created}`}
            accessories={[{ text: transcription.model }]}
            actions={
              <ActionPanel>
                <ActionPanel.Section title="Exportação Rápida">
                  <Action
                    title="Txt"
                    onAction={() => quickExport(transcription.filename, "txt")}
                  />
                  <Action
                    title="JSON"
                    onAction={() => quickExport(transcription.filename, "json")}
                  />
                  <Action
                    title="Srt"
                    onAction={() => quickExport(transcription.filename, "srt")}
                  />
                </ActionPanel.Section>
                <ActionPanel.Section title="Mais Opções">
                  <Action
                    title="Escolher Formato…"
                    onAction={() => {
                      setSelectedFile(transcription.filename);
                      setShowForm(true);
                    }}
                  />
                </ActionPanel.Section>
                <ActionPanel.Section title="Atualizar">
                  <Action
                    title="Atualizar Lista"
                    onAction={loadTranscriptions}
                    shortcut={{ modifiers: ["cmd"], key: "r" }}
                  />
                </ActionPanel.Section>
              </ActionPanel>
            }
          />
        ))}
      </List.Section>

      {transcriptions.length > 0 && (
        <List.Section title="Exportação da Última Transcrição">
          <List.Item
            title="🚀 Export Último Arquivo"
            subtitle={`${transcriptions[0].filename} (mais recente)`}
            accessories={[{ text: "Última transcrição" }]}
            actions={
              <ActionPanel>
                <Action
                  title="Txt (rápido)"
                  onAction={() =>
                    quickExport(transcriptions[0].filename, "txt")
                  }
                />
                <Action
                  title="JSON (rápido)"
                  onAction={() =>
                    quickExport(transcriptions[0].filename, "json")
                  }
                />
                <Action
                  title="Escolher Formato…"
                  onAction={() => {
                    setSelectedFile(transcriptions[0].filename);
                    setShowForm(true);
                  }}
                />
              </ActionPanel>
            }
          />
        </List.Section>
      )}
    </List>
  );
}
