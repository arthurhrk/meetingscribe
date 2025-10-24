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
import { useState, useEffect, useRef } from "react";
import { exec } from "child_process";
import { promisify } from "util";
import { StdioClient } from "./stdio";
import { runCliJSON } from "./cli";

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
    loadTranscriptions();
    return () => clientRef.current?.stop();
  }, []);

  async function loadTranscriptions() {
    try {
      setIsLoading(true);
      const resp: any = runnerMode === "stdio"
        ? await clientRef.current?.request("files.list", { type: "transcriptions", limit: 20 })
        : await runCliJSON(["-m", "src.core.runtime_cli", "files", "transcriptions", "--limit", "20"]);
      const items = resp?.data?.items || [];
      setTranscriptions(items);
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

      const res: any = runnerMode === "stdio"
        ? await clientRef.current?.request("export.run", { filename, format })
        : await runCliJSON(["-m", "src.core.runtime_cli", "export", filename, "--format", format]);
      if (res?.status !== "success") {
        throw new Error(res?.error?.message || "Falha na exportação");
      }

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
