import {
  ActionPanel,
  Action,
  List,
  showToast,
  Toast,
  getPreferenceValues,
  Detail,
  Icon,
} from "@raycast/api";
import { useState, useEffect } from "react";
import { spawn } from "child_process";
import * as fs from "fs";
import * as path from "path";

interface Preferences {
  pythonPath: string;
  projectPath: string;
  defaultModel: string;
  runnerMode?: string;
}

interfacaudioDevice {
  id: string;
  name: string;
  isDefault: boolean;
  isLoopback: boolean;
  maxInputChannels?: number;
}

// Keep references to child processes so they are not GC'd
const activeRecordings = new Map<string, any>();

export default function StartRecording() {
  const [devices, setDevices] = useStataudioDevice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [inputMode, setInputMode] = useState<"auto" | "mic" | "loopback">("auto");

  useEffect(() => {
    // Simple mode: always auto-detect device
    setDevices([
      {
        id: "auto",
        name: "Auto-detect (melhor dispositivo)",
        isDefault: true,
        isLoopback: true,
        maxInputChannels: 2,
      },
    ]);
    setIsLoading(false);
  }, []);

  async function startRecording(deviceName: string, Duracaon: number = 30) {
    if (isRecording) {
      await showToast({ style: Toast.Style.Failure, title: "JÃ¡ estÃ¡ gravando", message: "Aguarde terminar" });
      return;
    }

    try {
      setIsRecording(true);

      const minutes = Duracaon >= 60 ? Math.floor(Duracaon / 60) : 0;
      const seconds = Duracaon % 60;
      const timeDisplay = minutes > 0 ? `${minutes}min${seconds > 0 ? ` ${seconds}s` : ""}` : `${seconds}s`;

      await showToast({ style: Toast.Style.Animated, title: "Iniciando gravaÃ§Ã£o", message: `DuraÃ§Ã£o: ${timeDisplay}` });

      const { pythonPath, projectPath } = getPreferenceValues<Preferences>();

      if (!projectPath || !projectPath.trim() || !fs.existsSync(projectPath)) {
        await showToast({
          style: Toast.Style.Failure,
          title: "ConfiguraÃ§Ã£o incompleta",
          message: "Defina 'Project Path' nas preferÃªncias do Raycast",
        });
        setIsRecording(false);
        return;
      }

      // Always use quick_record.py (prints JSON immediately, then records)
      let scriptPath = path.join(projectPath, "quick_record.py");
      if (!fs.existsSync(scriptPath)) {
        // Fallback to archive/scripts/quick_record.py
        const alt = path.join(projectPath, "archive", "scripts", "quick_record.py");
        if (fs.existsSync(alt)) {
          scriptPath = alt;
        } else {
          await showToast({
            style: Toast.Style.Failure,
            title: "Script nao encontrado",
            message: `quick_record.py nao esta¡ em ${projectPath}`,
          });
          setIsRecording(false);
          return;
        }
      }

      const response = await new Promise<any>((resolve, reject) => {
        const child = spawn(pythonPath, [scriptPath, Duracaon.toString(), '--input', (inputMode || 'auto')], {
          cwd: projectPath,
          windowsHide: true,
          detached: false,
        audio: ["ignore", "pipe", "pipe"],
        });

        let jsonReceived = false;
        let buffer = "";
        let stderrBuffer = "";

        child.stdout?.setEncoding("utf8");
        child.stdout?.on("data", (data) => {
          if (!jsonReceived) {
            buffer += data.toString();
            const lines = buffer.split("\n");
            for (const line of lines) {
              if (line.trim().startsWith("{")) {
                try {
                  const parsed = JSON.parse(line.trim());
                  jsonReceived = true;

                  const sessionId = parsed.data?.session_id || "unknown";
                  activeRecordings.set(sessionId, child);
                  child.on("exit", () => activeRecordings.delete(sessionId));

                  resolve(parsed);
                  return;
                } catch (e) {
                  // keep reading until valid JSON
                }
              }
            }
          }
        });

        child.stderr?.on("data", (data) => {
          stderrBuffer += data.toString();
        });

        child.on("error", (error) => {
          if (!jsonReceived) {
            const err = stderrBuffer ? new Error(`${error.message} | ${stderrBuffer.substring(0, 200)}`) : error;
            reject(err as Error);
          }
        });

        // Safety timeout for the initial JSON
        setTimeout(() => {
          if (!jsonReceived) {
            const hint = stderrBuffer ? ` | stderr: ${stderrBuffer.substring(0, 200)}` : "";
            reject(new Error("Timeout waiting for recording to start" + hint));
          }
        }, 8000);
      });

      if (response.status === "success") {
        const data = response.data || {};
        const filePath = data.file_path as string;
        const filename = filePath ? filePath.split("\\").pop() : "recording.wav";

        await showToast({ style: Toast.Style.Success, title: "GravaÃ§Ã£o iniciada", message: `${timeDisplay} - ${filename}` });

        // Post-check: verify file creation after expected Duracaon
        const absPath = path.isAbsolute(filePath) ? filePath : path.resolve(projectPath, filePath);
        setTimeout(() => {
          try {
            if (fs.existsSync(absPath)) {
              showToast({ style: Toast.Style.Success, title: "Arquivo salvo", message: filename });
            } else {
              showToast({
                style: Toast.Style.Failure,
                title: "Falha ao salvar",
                message: `Nao encontrei ${filename}. Dica: toque algumaudio do sistema ou tente novamente.`,
              });
            }
          } catch {
            // ignore post-check errors
          }
        }, (Duracaon + 4) * 1000);
      } else {
        throw new Error(response.error?.message || "Failed to start recording");
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      const isTimeout = errorMsg.toLowerCase().includes("timeout");
      await showToast({
        style: Toast.Style.Failure,
        title: "Erro ao iniciar",
        message: isTimeout ? "Timeout - verifique Python e dependencias" : errorMsg.substring(0, 100),
      });
    } finally {
      setIsRecording(false);
    }
  }

  if (error) {
    return (
      <Detail
        markdown={`# Erro ao carregar\n\n${error}\n\nVerifique:\n- Python configurado\n- Caminho do projeto correto\n- dependencias instaladas`}
      />
    );
  }

  return (
    <List isLoading={isLoading} searchBarPlaceholder="Escolha a duracao da gravacao...">
      <List.Section title="Duracao da Gravacao">
        {devices.map((device) => (
          <List.Item
            key={device.id}
            title={isRecording ? "Gravando..." : device.name}
            subtitle={isRecording ? "Aguarde terminar" : "Selecione o tempo desejado"}
            icon={isRecording ? Icon.CircleFilled : Icon.Microphone}
            accessories={[{ text: `Entrada: ${inputMode}` }]}
            actions={
              <ActionPanel>
                <Action title="Gravar 30s" onAction={() => startRecording(device.name, 30)} icon={Icon.Circle} />
                <Action title="Gravar 60s" onAction={() => startRecording(device.name, 60)} icon={Icon.Circle} />
                <Action title="Gravar 2min" onAction={() => startRecording(device.name, 120)} icon={Icon.Circle} />
                <Action title="Gravar 5min" onAction={() => startRecording(device.name, 300)} icon={Icon.Video} />
                <Action title="Gravar 10min" onAction={() => startRecording(device.name, 600)} icon={Icon.Video} />
                <Action title="Gravar 15min" onAction={() => startRecording(device.name, 900)} icon={Icon.Video} />
                <Action title="Gravar 30min" onAction={() => startRecording(device.name, 1800)} icon={Icon.Video} />
                <ActionPanel.Section title="Modo de entrada">
                  <Action title={`Modo: Auto${inputMode==='auto'?' (ativo)':''}`} onAction={() => setInputMode('auto')} icon={Icon.Dot} />
                  <Action title={`Modo: Microfone${inputMode==='mic'?' (ativo)':''}`} onAction={() => setInputMode('mic')} icon={Icon.Microphone} />
                  <Action title={`Modo: Loopback${inputMode==='loopback'?' (ativo)':''}`} onAction={() => setInputMode('loopback')} icon={Icon.ArrowClockwise} />
                </ActionPanel.Section>
              </ActionPanel>
            }
          />
        ))}
      </List.Section>

      <List.Section title="Informacoes">
        <List.Item
          icon={Icon.Info}
          title="Como funciona"
          subtitle="Auto-detecta o melhor dispositivo audio disponivel"
        />
        <List.Item
          icon={Icon.Gear}
          title="Configuracoes"
          subtitle="Defina Python e o caminho do projeto nas preferencias"
        />
      </List.Section>
    </List>
  );
}







