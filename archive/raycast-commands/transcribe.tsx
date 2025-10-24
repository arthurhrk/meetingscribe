import {
  ActionPanel,
  Action,
  Form,
  showToast,
  Toast,
  getPreferenceValues,
} from "@raycast/api";
import { useEffect, useRef, useState } from "react";
import { StdioClient } from "./stdio";
import { runCliJSON } from "./cli";

interface Preferences {
  pythonPath: string;
  projectPath: string;
  defaultModel: string;
}

interface FormValues {
  audioFile: string[];
  model: string;
  language: string;
  speakerDetection: boolean;
  exportFormat: string;
}

const whisperModels = [
  { title: "Tiny (Mais rapido)", value: "tiny" },
  { title: "Base (Equilibrado)", value: "base" },
  { title: "Small (Boa precisao)", value: "small" },
  { title: "Medium (Alta precisao)", value: "medium" },
  { title: "Large-v3 (Maxima precisao)", value: "large-v3" },
];

const languages = [
  { title: "Auto-detectar", value: "auto" },
  { title: "Portugues", value: "pt" },
  { title: "English", value: "en" },
  { title: "Espanol", value: "es" },
  { title: "Francais", value: "fr" },
  { title: "Deutsch", value: "de" },
  { title: "Italiano", value: "it" },
];

const exportFormats = [
  { title: "TXT (Texto simples)", value: "txt" },
  { title: "JSON (Estruturado)", value: "json" },
  { title: "SRT (Legendas)", value: "srt" },
  { title: "VTT (WebVTT)", value: "vtt" },
  { title: "CSV (Planilha)", value: "csv" },
];

export default function TranscribeFile() {
  const [isLoading, setIsLoading] = useState(false);
  const preferences = getPreferenceValues<Preferences>();
  const clientRef = useRef<StdioClient | null>(null);
  const runnerMode = (preferences as any).runnerMode || "stdio";
  const [lastJobId, setLastJobId] = useState<string | null>(null);

  useEffect(() => {
    if (runnerMode === "stdio") {
      clientRef.current = new StdioClient(
        preferences.pythonPath,
        preferences.projectPath,
        (evt) => {
          if (evt.event === "transcription.progress") {
            const pct = Math.round((evt.progress ?? 0) * 100);
            showToast({ style: Toast.Style.Animated, title: `Transcrevendo... ${pct}%`, message: evt.message });
          } else if (evt.event === "transcription.completed") {
            showToast({ style: Toast.Style.Success, title: "Transcricao concluida" });
          } else if (evt.event === "transcription.error") {
            showToast({ style: Toast.Style.Failure, title: "Erro na transcricao", message: evt.message });
          }
        }
      );
      clientRef.current.start();
    }
    return () => clientRef.current?.stop();
  }, []);

  async function handleSubmit(values: FormValues) {
    if (!values.audioFile || values.audioFile.length === 0) {
      showToast({ style: Toast.Style.Failure, title: "Erro", message: "Selecione um arquivo de audio" });
      return;
    }

    try {
      setIsLoading(true);
      showToast({ style: Toast.Style.Animated, title: "Iniciando transcricao..." });

      const audioFilePath = values.audioFile[0];
      if (runnerMode === "stdio") {
        const params: any = {
          audio_path: audioFilePath,
          model: values.model,
          language: values.language === "auto" ? undefined : values.language,
          stream: true,
        };
        const res: any = await clientRef.current?.request("transcription.start", params);
        const jobId = res?.data?.job_id;
        setLastJobId(jobId || null);
      } else {
        const args = ["-m", "src.core.runtime_cli", "transcribe", audioFilePath, "--model", values.model];
        if (values.language !== "auto") {
          args.push("--language", values.language);
        }
        await runCliJSON(args);
        showToast({ style: Toast.Style.Success, title: "Transcricao concluida (CLI)" });
      }

      showToast({ style: Toast.Style.Animated, title: "Transcricao iniciada" });
    } catch (error) {
      showToast({ style: Toast.Style.Failure, title: "Erro na transcricao", message: String(error) });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Form
      isLoading={isLoading}
      actions={
        <ActionPanel>
          <Action.SubmitForm title="Iniciar Transcricao" onSubmit={handleSubmit} />
          {lastJobId && (
            <Action
              title="Cancelar Transcricao"
              onAction={async () => {
                try {
                  await clientRef.current?.request("job.cancel", { job_id: lastJobId });
                  showToast({ style: Toast.Style.Success, title: "Transcricao cancelada" });
                  setLastJobId(null);
                } catch (e) {
                  showToast({ style: Toast.Style.Failure, title: "Falha ao cancelar" });
                }
              }}
            />
          )}
        </ActionPanel>
      }
    >
      <Form.FilePicker
        id="audioFile"
        title="Arquivo de audio"
        allowMultipleSelection={false}
        canChooseDirectories={false}
        canChooseFiles={true}
        storeValue={true}
      />

      <Form.Separator />

      <Form.Dropdown id="model" title="Modelo Whisper" defaultValue={preferences.defaultModel} storeValue={true}>
        {whisperModels.map((model) => (
          <Form.Dropdown.Item key={model.value} value={model.value} title={model.title} />
        ))}
      </Form.Dropdown>

      <Form.Dropdown id="language" title="Idioma" defaultValue="auto" storeValue={true}>
        {languages.map((lang) => (
          <Form.Dropdown.Item key={lang.value} value={lang.value} title={lang.title} />
        ))}
      </Form.Dropdown>

      <Form.Separator />

      <Form.Checkbox
        id="speakerDetection"
        title="Identificacao de Speakers"
        label="Ativar deteccao de participantes"
        defaultValue={false}
        storeValue={true}
      />

      <Form.Dropdown id="exportFormat" title="Formato de Exportacao" defaultValue="txt" storeValue={true}>
        {exportFormats.map((format) => (
          <Form.Dropdown.Item key={format.value} value={format.value} title={format.title} />
        ))}
      </Form.Dropdown>
    </Form>
  );
}

