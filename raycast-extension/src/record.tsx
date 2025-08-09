import {
  ActionPanel,
  Action,
  List,
  showToast,
  Toast,
  getPreferenceValues,
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

interface AudioDevice {
  id: string;
  name: string;
  isDefault: boolean;
  isLoopback: boolean;
  isSystemDefault?: boolean;
  maxInputChannels?: number;
  maxOutputChannels?: number;
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
      
      // Usar --recording-only para filtrar apenas dispositivos adequados para gravação
      const { stdout } = await execAsync(
        `cd "${preferences.projectPath}" && ${preferences.pythonPath} device_manager.py --list-json --recording-only`,
      );

      const deviceData = JSON.parse(stdout);
      
      // Mapear dados para interface AudioDevice
      const mappedDevices: AudioDevice[] = deviceData.map((device: any) => ({
        id: device.id,
        name: device.name,
        isDefault: device.is_default || device.is_system_default || false,
        isLoopback: device.is_loopback || false,
        isSystemDefault: device.is_system_default || false,
        maxInputChannels: device.max_input_channels || 0,
        maxOutputChannels: device.max_output_channels || 0,
      }));
      
      setDevices(mappedDevices);
      console.log("Loaded devices:", mappedDevices);
    } catch (error) {
      console.error("Error loading devices:", error);
      showToast({
        style: Toast.Style.Failure,
        title: "Erro ao carregar dispositivos",
        message: `Erro: ${error instanceof Error ? error.message : 'Erro desconhecido'}`,
      });
      console.error("Erro:", error);
    } finally {
      setIsLoading(false);
    }
  }

  async function startRecording(deviceId: string) {
    try {
      console.log("Starting recording with device:", deviceId);
      console.log("Python path:", preferences.pythonPath);
      console.log("Project path:", preferences.projectPath);
      
      const command = `cd "${preferences.projectPath}" && ${preferences.pythonPath} main.py --record --device "${deviceId}"`;
      console.log("Executing command:", command);

      showToast({
        style: Toast.Style.Animated,
        title: "Iniciando gravação...",
        message: "Preparando dispositivos de áudio",
      });

      const { stdout, stderr } = await execAsync(command);
      
      console.log("Command stdout:", stdout);
      if (stderr) {
        console.error("Command stderr:", stderr);
      }

      showToast({
        style: Toast.Style.Success,
        title: "Gravação iniciada!",
        message: "Use 'ms status' para acompanhar o progresso",
      });
    } catch (error) {
      console.error("Error starting recording:", error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("Full error:", errorMessage);
      
      showToast({
        style: Toast.Style.Failure,
        title: "Erro ao iniciar gravação",
        message: `Erro detalhado: ${errorMessage.substring(0, 200)}`,
      });
    }
  }

  return (
    <List
      isLoading={isLoading}
      searchBarPlaceholder="Buscar dispositivos de áudio..."
    >
      <List.Section title="Dispositivos de Áudio Disponíveis">
        {devices.map((device) => (
          <List.Item
            key={device.id}
            title={device.name}
            subtitle={
              device.isSystemDefault 
                ? "Sistema Padrão" 
                : device.isDefault 
                ? "Padrão" 
                : device.maxInputChannels 
                ? `${device.maxInputChannels} canais de entrada` 
                : ""
            }
            accessories={[
              { text: device.isSystemDefault ? "🏠" : device.isLoopback ? "🔄" : "🎤" },
              { text: device.isDefault || device.isSystemDefault ? "🎯" : "" },
              { text: device.maxInputChannels ? `In:${device.maxInputChannels}` : "" },
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
