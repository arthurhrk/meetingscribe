import { getPreferenceValues, showToast, Toast } from "@raycast/api";
import { createStdioClient, StdioClient, StdioResult, Preferences } from "./stdio";

/**
 * Daemon-aware client for MeetingScribe Raycast extension.
 * 
 * Automatically detects and connects to daemon, with fallback to direct process execution.
 * Provides a unified interface for all MeetingScribe operations.
 */
export class DaemonClient {
  private client: StdioClient | null = null;
  private preferences: Preferences;

  constructor() {
    this.preferences = getPreferenceValues<Preferences>();
  }

  /**
   * Initialize the client connection (daemon or direct process)
   */
  async initialize(): Promise<void> {
    if (this.client) {
      return; // Already initialized
    }

    try {
      this.client = await createStdioClient(
        this.preferences.pythonPath,
        this.preferences.projectPath,
        (event) => {
          // Handle events if needed
          console.log('Daemon event:', event);
        }
      );

      // Show connection mode to user
      const usingDaemon = this.client.isUsingDaemon();
      await showToast({
        style: Toast.Style.Success,
        title: usingDaemon ? "Connected to Daemon" : "Direct Mode",
        message: usingDaemon 
          ? "Using background service for faster operations" 
          : "Running in compatibility mode",
      });

    } catch (error) {
      await showToast({
        style: Toast.Style.Failure,
        title: "Connection Failed",
        message: error instanceof Error ? error.message : "Unknown error",
      });
      throw error;
    }
  }

  /**
   * Execute a command via daemon or direct process
   */
  async execute<T = StdioResult>(method: string, params?: any): Promise<T> {
    if (!this.client) {
      await this.initialize();
    }

    if (!this.client) {
      throw new Error("Failed to initialize client");
    }

    try {
      return await this.client.request<T>(method, params);
    } catch (error) {
      // Show user-friendly error
      await showToast({
        style: Toast.Style.Failure,
        title: "Command Failed",
        message: error instanceof Error ? error.message : "Unknown error",
      });
      throw error;
    }
  }

  /**
   * Check if using daemon mode
   */
  isUsingDaemon(): boolean {
    return this.client?.isUsingDaemon() ?? false;
  }

  /**
   * Cleanup client connection
   */
  cleanup(): void {
    if (this.client) {
      this.client.stop();
      this.client = null;
    }
  }

  // Convenience methods for common operations
  
  /**
   * List available audio devices
   */
  async listAudioDevices(): Promise<any[]> {
    const result = await this.execute("audio.list_devices");
    return result.data?.devices ?? [];
  }

  /**
   * Start recording with specified device
   */
  async startRecording(deviceId: string): Promise<StdioResult> {
    return await this.execute("record.start", { device_id: deviceId });
  }

  /**
   * Stop current recording
   */
  async stopRecording(): Promise<StdioResult> {
    return await this.execute("record.stop");
  }

  /**
   * Get recording status
   */
  async getRecordingStatus(): Promise<StdioResult> {
    return await this.execute("record.status");
  }

  /**
   * Transcribe audio file
   */
  async transcribeFile(filePath: string, options?: { model?: string; language?: string }): Promise<StdioResult> {
    return await this.execute("transcription.transcribe_file", {
      file_path: filePath,
      model: options?.model || this.preferences.defaultModel,
      language: options?.language || "auto",
    });
  }

  /**
   * Get recent recordings
   */
  async getRecentRecordings(limit: number = 10): Promise<any[]> {
    const result = await this.execute("storage.list_recordings", { limit });
    return result.data?.recordings ?? [];
  }

  /**
   * Export transcription
   */
  async exportTranscription(transcriptionId: string, format: string, outputPath?: string): Promise<StdioResult> {
    return await this.execute("export.transcription", {
      transcription_id: transcriptionId,
      format,
      output_path: outputPath,
    });
  }

  /**
   * Get system status
   */
  async getSystemStatus(): Promise<StdioResult> {
    return await this.execute("system.status");
  }

  /**
   * Ping daemon/service
   */
  async ping(): Promise<StdioResult> {
    return await this.execute("system.ping");
  }
}

// Global client instance for reuse across commands
let globalClient: DaemonClient | null = null;

/**
 * Get or create global daemon client instance
 */
export function getDaemonClient(): DaemonClient {
  if (!globalClient) {
    globalClient = new DaemonClient();
  }
  return globalClient;
}

/**
 * Cleanup global daemon client
 */
export function cleanupDaemonClient(): void {
  if (globalClient) {
    globalClient.cleanup();
    globalClient = null;
  }
}
