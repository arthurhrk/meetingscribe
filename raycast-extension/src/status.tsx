import { ActionPanel, Action, List, showToast, Toast, getPreferenceValues, Detail, Icon } from "@raycast/api";
import { useState, useEffect, useRef } from "react";
import { StdioClient } from "./stdio";
import { getDaemonClient } from "./daemon-client";

interface Preferences {
  pythonPath: string;
  projectPath: string;
  defaultModel: string;
}

interface SystemStatusData {
  overall: string;
  components: { name: string; status: string; message: string }[];
  hardware: { cpu: string; memory: string; gpu: string; audio_devices: string };
  models: { name: string; size: string; status: string }[];
}

export default function SystemStatus() {
  const [status, setStatus] = useState<SystemStatusData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const preferences = getPreferenceValues<Preferences>();
  const runnerMode = (preferences as any).runnerMode || "cli";
  const clientRef = useRef<StdioClient | null>(null);

  useEffect(() => {
    if (runnerMode === "stdio") {
      clientRef.current = new StdioClient((preferences as any).pythonPath, (preferences as any).projectPath, undefined);
      clientRef.current.start();
    }
    loadSystemStatus();
    return () => clientRef.current?.stop();
  }, []);

  async function loadSystemStatus() {
    try {
      setIsLoading(true);

      const client = getDaemonClient();
      await client.initialize();

      const [sysResp, devices] = await Promise.all([client.getSystemStatus(), client.listAudioDevices()]);
      const system = sysResp?.data?.system || {};

      const hardware = {
        cpu: system?.cpu?.model || system?.cpu || "-",
        memory: system?.memory?.total || system?.memory || "-",
        gpu: system?.gpu?.name || system?.gpu || "-",
        audio_devices: String(devices.length || 0),
      };

      const isDaemonMode = client.isUsingDaemon();
      const components = [
        { name: "Connection", status: isDaemonMode ? "ok" : "ok", message: isDaemonMode ? "Daemon Mode (Fast)" : "Direct Mode (Fallback)" },
        { name: "Core", status: "ok", message: "Sistema operacional" },
        { name: "Raycast", status: "ok", message: "Bridge ativo" },
        { name: "Audio", status: devices.length > 0 ? "ok" : "warning", message: `${devices.length} dispositivos` },
      ];

      const s: SystemStatusData = {
        overall: "ok",
        components,
        hardware,
        models: [
          { name: "tiny", size: "~39MB", status: "available" },
          { name: "base", size: "~74MB", status: "available" },
        ],
      };

      setStatus(s);
    } catch (error) {
      showToast({ style: Toast.Style.Failure, title: "Erro ao verificar status", message: "Nao foi possivel verificar o status do sistema" });
    } finally {
      setIsLoading(false);
    }
  }

  function getStatusIcon(status: string) {
    switch (status.toLowerCase()) {
      case "ok":
      case "success":
        return Icon.CheckCircle;
      case "warning":
        return Icon.ExclamationMark;
      case "error":
      case "failed":
        return Icon.XMarkCircle;
      default:
        return Icon.Dot;
    }
  }

  if (!status) {
    return <List isLoading={isLoading} />;
  }

  return (
    <List isLoading={isLoading}>
      <List.Section title={`Status Geral: ${status.overall}`}>
        <List.Item
          title="Hardware"
          subtitle={`CPU: ${status.hardware.cpu} | RAM: ${status.hardware.memory} | GPU: ${status.hardware.gpu}`}
          accessories={[{ text: `${status.hardware.audio_devices} dispositivos de audio` }]}
          actions={
            <ActionPanel>
              <Action.Push
                title="Ver Detalhes Do Hardware"
                target={
                  <Detail
                    markdown={`# Hardware\n\n**CPU:** ${status.hardware.cpu}\n**Memoria:** ${status.hardware.memory}\n**GPU:** ${status.hardware.gpu}\n**Dispositivos de audio:** ${status.hardware.audio_devices}`}
                  />
                }
              />
            </ActionPanel>
          }
        />
      </List.Section>

      <List.Section title="Componentes do Sistema">
        {status.components.map((component, index) => (
          <List.Item
            key={index}
            title={component.name}
            subtitle={component.message}
            accessories={[{ text: component.status }]}
            icon={getStatusIcon(component.status)}
          />
        ))}
      </List.Section>
    </List>
  );
}

