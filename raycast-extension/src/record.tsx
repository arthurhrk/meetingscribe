import { ActionPanel, Action, List, showToast, Toast, getPreferenceValues } from "@raycast/api";
import { useState, useEffect } from "react";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

interface Preferences {
  pythonPath: string;
  projectPath: string;
  defaultModel: string;
}

interface AudioDevice {
  id: string;
  name: string;
  isDefault: boolean;
  isLoopback: boolean;
}

export default function StartRecording() {
  const [devices, setDevices] = useState<AudioDevice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const preferences = getPreferenceValues<Preferences>();

  useEffect(() => {
    loadAudioDevices();
  }, []);

  async function loadAudioDevices() {
    try {
      setIsLoading(true);
      const { stdout } = await execAsync(
        `cd "${preferences.projectPath}" && ${preferences.pythonPath} device_manager.py --list-json`
      );
      
      const deviceData = JSON.parse(stdout);
      setDevices(deviceData);
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Erro ao carregar dispositivos",
        message: "Verifique se o MeetingScribe está configurado corretamente"
      });
      console.error("Erro:", error);
    } finally {
      setIsLoading(false);
    }
  }

  async function startRecording(deviceId: string) {
    try {
      showToast({
        style: Toast.Style.Animated,
        title: "Iniciando gravação...",
        message: "Preparando dispositivos de áudio"
      });

      const { stdout } = await execAsync(
        `cd "${preferences.projectPath}" && ${preferences.pythonPath} main.py --record --device "${deviceId}"`
      );

      showToast({
        style: Toast.Style.Success,
        title: "Gravação iniciada!",
        message: "Use 'ms status' para acompanhar o progresso"
      });
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Erro ao iniciar gravação",
        message: String(error)
      });
    }
  }

  return (
    <List isLoading={isLoading} searchBarPlaceholder="Buscar dispositivos de áudio...">
      <List.Section title="Dispositivos de Áudio Disponíveis">
        {devices.map((device) => (
          <List.Item
            key={device.id}
            title={device.name}
            subtitle={device.isDefault ? "Padrão" : ""}
            accessories={[
              { text: device.isLoopback ? "Loopback" : "Input" },
              { text: device.isDefault ? "🎯" : "" }
            ]}
            actions={
              <ActionPanel>
                <Action
                  title="Iniciar Gravação"
                  onAction={() => startRecording(device.id)}
                />
                <Action
                  title="Atualizar Lista"
                  onAction={loadAudioDevices}
                  shortcut={{ modifiers: ["cmd"], key: "r" }}
                />
              </ActionPanel>
            }
          />
        ))}
      </List.Section>
    </List>
  );
}