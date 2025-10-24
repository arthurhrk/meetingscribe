import {
  ActionPanel,
  Action,
  List,
  showToast,
  Toast,
  getPreferenceValues,
  Detail,
  confirmAlert,
  Alert,
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

interface TeamsStatus {
  monitoring_active: boolean;
  teams_running: boolean;
  in_meeting: boolean;
  recording_active: boolean;
  current_meeting?: {
    title: string;
    start_time: string;
    recording_path: string;
    device_used: string;
  };
}

export default function TeamsMonitor() {
  const [status, setStatus] = useState<TeamsStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const preferences = getPreferenceValues<Preferences>();

  useEffect(() => {
    loadTeamsStatus();
    // Atualizar status a cada 5 segundos
    const interval = setInterval(loadTeamsStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  async function loadTeamsStatus() {
    try {
      setIsLoading(true);
      const { stdout } = await execAsync(
        `cd "${preferences.projectPath}" && ${preferences.pythonPath} -c "from teams_integration import get_teams_status; import json; print(json.dumps(get_teams_status()))"`,
      );

      const statusData = JSON.parse(stdout);
      setStatus(statusData);
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Erro ao verificar Teams",
        message: "Não foi possível verificar status do Teams",
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function startMonitoring() {
    try {
      showToast({
        style: Toast.Style.Animated,
        title: "Iniciando monitoramento...",
        message: "Ativando detecção automática de reuniões",
      });

      await execAsync(
        `cd "${preferences.projectPath}" && ${preferences.pythonPath} -c "from teams_integration import start_teams_monitoring; start_teams_monitoring()"`,
      );

      showToast({
        style: Toast.Style.Success,
        title: "Monitoramento ativo!",
        message: "Gravação automática ligada para reuniões Teams",
      });

      await loadTeamsStatus();
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Erro ao iniciar monitoramento",
        message: "Não foi possível ativar o modo automático",
      });
    }
  }

  async function stopMonitoring() {
    try {
      const confirmed = await confirmAlert({
        title: "Parar monitoramento?",
        message: "Isso vai desativar a gravação automática de reuniões",
        primaryAction: {
          title: "Parar Monitoramento",
          style: Alert.ActionStyle.Destructive,
        },
        dismissAction: {
          title: "Cancelar",
        },
      });

      if (!confirmed) return;

      showToast({
        style: Toast.Style.Animated,
        title: "Parando monitoramento...",
        message: "Desativando detecção automática",
      });

      await execAsync(
        `cd "${preferences.projectPath}" && ${preferences.pythonPath} -c "from teams_integration import stop_teams_monitoring; stop_teams_monitoring()"`,
      );

      showToast({
        style: Toast.Style.Success,
        title: "Monitoramento parado",
        message: "Gravação automática desativada",
      });

      await loadTeamsStatus();
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Erro ao parar monitoramento",
        message: "Não foi possível desativar o modo automático",
      });
    }
  }

  async function forceStopRecording() {
    try {
      await execAsync(
        `cd "${preferences.projectPath}" && ${preferences.pythonPath} -c "from teams_integration import _teams_integration; _teams_integration.stop_auto_recording() if '_teams_integration' in globals() else None"`,
      );

      showToast({
        style: Toast.Style.Success,
        title: "Gravação finalizada",
        message: "Arquivo salvo com sucesso",
      });

      await loadTeamsStatus();
    } catch (error) {
      showToast({
        style: Toast.Style.Failure,
        title: "Erro ao parar gravação",
        message: "Não foi possível finalizar gravação",
      });
    }
  }

  function getStatusIcon(isActive: boolean): string {
    return isActive ? "✅" : "❌";
  }

  function getStatusColor(isActive: boolean): string {
    return isActive ? "#00AA00" : "#FF0000";
  }

  if (!status) {
    return <List isLoading={isLoading} />;
  }

  return (
    <List isLoading={isLoading}>
      <List.Section title="Teams Integration Status">
        <List.Item
          title="Monitoramento Automático"
          subtitle={
            status.monitoring_active
              ? "🟢 Ativo - Detectando reuniões automaticamente"
              : "🔴 Inativo - Clique para ativar"
          }
          icon={{
            source: getStatusIcon(status.monitoring_active),
            tintColor: getStatusColor(status.monitoring_active),
          }}
          actions={
            <ActionPanel>
              {!status.monitoring_active ? (
                <Action
                  title="Iniciar Monitoramento"
                  onAction={startMonitoring}
                  shortcut={{ modifiers: ["cmd"], key: "s" }}
                />
              ) : (
                <Action
                  title="Parar Monitoramento"
                  onAction={stopMonitoring}
                  shortcut={{ modifiers: ["cmd"], key: "x" }}
                />
              )}
              <Action
                title="Atualizar Status"
                onAction={loadTeamsStatus}
                shortcut={{ modifiers: ["cmd"], key: "r" }}
              />
            </ActionPanel>
          }
        />

        <List.Item
          title="Microsoft Teams"
          subtitle={
            status.teams_running
              ? "🟢 Aplicativo rodando"
              : "🔴 Teams não detectado"
          }
          icon={{
            source: getStatusIcon(status.teams_running),
            tintColor: getStatusColor(status.teams_running),
          }}
        />

        <List.Item
          title="Status da Reunião"
          subtitle={
            status.in_meeting
              ? "🟢 Em reunião ativa"
              : "🔴 Fora de reunião"
          }
          icon={{
            source: getStatusIcon(status.in_meeting),
            tintColor: getStatusColor(status.in_meeting),
          }}
        />

        <List.Item
          title="Gravação Ativa"
          subtitle={
            status.recording_active
              ? "🔴 Gravando agora"
              : "⚪ Nenhuma gravação"
          }
          icon={{
            source: status.recording_active ? "🔴" : "⚪",
            tintColor: status.recording_active ? "#FF0000" : "#888888",
          }}
          actions={
            status.recording_active ? (
              <ActionPanel>
                <Action
                  title="Parar Gravação"
                  onAction={forceStopRecording}
                  shortcut={{ modifiers: ["cmd"], key: "enter" }}
                />
              </ActionPanel>
            ) : undefined
          }
        />
      </List.Section>

      {status.current_meeting && (
        <List.Section title="Reunião Atual">
          <List.Item
            title={status.current_meeting.title}
            subtitle={`Iniciada: ${new Date(status.current_meeting.start_time).toLocaleTimeString()}`}
            accessories={[
              { text: `Dispositivo: ${status.current_meeting.device_used}` },
            ]}
            actions={
              <ActionPanel>
                <Action.Push
                  title="Ver Detalhes"
                  target={
                    <Detail
                      markdown={`# Reunião em Andamento
                      
**Título:** ${status.current_meeting.title}
**Início:** ${new Date(status.current_meeting.start_time).toLocaleString()}
**Arquivo:** ${status.current_meeting.recording_path}
**Dispositivo:** ${status.current_meeting.device_used}

## Status
✅ **Gravação ativa** - O áudio está sendo capturado automaticamente

## Ações disponíveis
- A gravação será finalizada automaticamente quando sair da reunião
- Ou você pode parar manualmente usando o botão "Parar Gravação"
- Após finalizada, a transcrição poderá ser feita automaticamente`}
                    />
                  }
                />
                <Action
                  title="Parar Gravação Manual"
                  onAction={forceStopRecording}
                />
              </ActionPanel>
            }
          />
        </List.Section>
      )}

      <List.Section title="Instruções">
        <List.Item
          title="Como usar o modo automático"
          subtitle="Clique para ver o guia completo"
          icon="💡"
          actions={
            <ActionPanel>
              <Action.Push
                title="Ver Guia"
                target={
                  <Detail
                    markdown={`# 🤖 Modo Automático MeetingScribe

## Como funciona

1. **Ative o monitoramento** clicando em "Iniciar Monitoramento"
2. **Entre em reuniões Teams normalmente**
3. **A gravação inicia automaticamente** 3 segundos após detectar a reunião
4. **A gravação para automaticamente** quando você sai da reunião
5. **O arquivo fica salvo** em \`storage/recordings/\`

## Detecção automática

✅ **Detecta automaticamente:**
- Quando você entra em reunião no Teams
- Usa o dispositivo de áudio ativo do Windows
- Captura áudio do sistema (o que você ouve)
- Nomes arquivos com base no título da reunião

✅ **Recursos inteligentes:**
- Monitoramento contínuo em background
- Não interfere com outras atividades
- Usa dispositivos de áudio padrão automaticamente
- Salva metadados da reunião junto com o áudio

## Privacidade & Segurança

🔒 **100% Local:**
- Nenhum dado enviado para serviços externos
- Processamento totalmente offline
- Arquivos ficam no seu computador
- Você controla todos os dados

## Configuração recomendada

1. **Deixe sempre ligado** para captura automática
2. **Configure dispositivos de áudio** no Windows como desejar
3. **Verifique espaço em disco** periodicamente
4. **Transcreveva arquivos** usando outros comandos do MeetingScribe

## Resolução de problemas

**Se não detectar reuniões:**
- Verifique se Teams está rodando
- Confirme que está realmente em uma chamada
- Teste com uma reunião de teste

**Se não gravar áudio:**
- Verifique dispositivos de áudio no Windows
- Confirme que há áudio sendo reproduzido
- Teste gravação manual primeiro`}
                  />
                }
              />
            </ActionPanel>
          }
        />
      </List.Section>
    </List>
  );
}