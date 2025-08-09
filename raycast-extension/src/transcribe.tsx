import {
  ActionPanel,
  Action,
  Form,
  showToast,
  Toast,
  getPreferenceValues,
  popToRoot,
} from "@raycast/api";
import { useState } from "react";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

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
  { title: "Tiny (Mais rápido)", value: "tiny" },
  { title: "Base (Equilibrado)", value: "base" },
  { title: "Small (Boa precisão)", value: "small" },
  { title: "Medium (Alta precisão)", value: "medium" },
  { title: "Large-v3 (Máxima precisão)", value: "large-v3" },
];

const languages = [
  { title: "Auto-detectar", value: "auto" },
  { title: "Português", value: "pt" },
  { title: "English", value: "en" },
  { title: "Español", value: "es" },
  { title: "Français", value: "fr" },
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

  async function handleSubmit(values: FormValues) {
    if (!values.audioFile || values.audioFile.length === 0) {
      showToast({
        style: Toast.Style.Failure,
        title: "Erro",
        message: "Selecione um arquivo de áudio",
      });
      return;
    }

    try {
      setIsLoading(true);
      showToast({
        style: Toast.Style.Animated,
        title: "Iniciando transcrição...",
        message: `Modelo: ${values.model} | Idioma: ${values.language}`,
      });

      const audioFilePath = values.audioFile[0];
      let command = `cd "${preferences.projectPath}" && ${preferences.pythonPath} main.py --transcribe "${audioFilePath}" --model ${values.model}`;

      if (values.language !== "auto") {
        command += ` --language ${values.language}`;
      }

      if (values.speakerDetection) {
        command += ` --speakers`;
      }

      if (values.exportFormat !== "txt") {
        command += ` --export-format ${values.exportFormat}`;
      }

      await execAsync(command);

      showToast({
        style: Toast.Style.Success,
        title: "Transcrição concluída!",
        message: "Arquivo processado com sucesso",
      });

      popToRoot();
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Erro na transcrição",
        message: String(error),
      });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Form
      isLoading={isLoading}
      actions={
        <ActionPanel>
          <Action.SubmitForm
            title="Iniciar Transcrição"
            onSubmit={handleSubmit}
          />
        </ActionPanel>
      }
    >
      <Form.FilePicker
        id="audioFile"
        title="Arquivo de Áudio"
        allowMultipleSelection={false}
        canChooseDirectories={false}
        canChooseFiles={true}
        storeValue={true}
      />

      <Form.Separator />

      <Form.Dropdown
        id="model"
        title="Modelo Whisper"
        defaultValue={preferences.defaultModel}
        storeValue={true}
      >
        {whisperModels.map((model) => (
          <Form.Dropdown.Item
            key={model.value}
            value={model.value}
            title={model.title}
          />
        ))}
      </Form.Dropdown>

      <Form.Dropdown
        id="language"
        title="Idioma"
        defaultValue="auto"
        storeValue={true}
      >
        {languages.map((lang) => (
          <Form.Dropdown.Item
            key={lang.value}
            value={lang.value}
            title={lang.title}
          />
        ))}
      </Form.Dropdown>

      <Form.Separator />

      <Form.Checkbox
        id="speakerDetection"
        title="Identificação de Speakers"
        label="Ativar detecção de participantes"
        defaultValue={false}
        storeValue={true}
      />

      <Form.Dropdown
        id="exportFormat"
        title="Formato de Exportação"
        defaultValue="txt"
        storeValue={true}
      >
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
