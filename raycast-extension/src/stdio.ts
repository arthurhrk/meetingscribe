import { spawn, ChildProcessWithoutNullStreams } from "child_process";
import * as net from "net";
import * as fs from "fs";
import * as path from "path";

export type StdioEvent = { event: string; [key: string]: any };
export type StdioResult = { status: string; data?: any; error?: { code: string; message: string } };

export interface Preferences {
  pythonPath: string;
  projectPath: string;
  defaultModel: string;
}

type PendingResolver = (res: StdioResult) => void;

export class StdioClient {
  private proc: ChildProcessWithoutNullStreams | null = null;
  private pipe: net.Socket | null = null;
  private nextId = 1;
  private pending = new Map<number, PendingResolver>();
  private buffer = "";
  private useDaemon = false;
  private static readonly PIPE_NAME = "\\\\.\\pipe\\MeetingScribe";

  constructor(
    private pythonPath: string,
    private projectPath: string,
    private onEvent?: (evt: StdioEvent) => void,
  ) {}

  async start(): Promise<void> {
    // Try daemon connection first
    if (await this.tryConnectToDaemon()) {
      this.useDaemon = true;
      return;
    }
    
    // Fallback to direct process spawn
    if (this.proc) return;
    this.proc = spawn(this.pythonPath, ["-m", "src.core.stdio_server"], {
      cwd: this.projectPath,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });

    this.proc.stdout.setEncoding("utf8");
    this.proc.stdout.on("data", (chunk) => this.handleData(chunk));
    this.proc.on("exit", () => {
      this.proc = null;
      this.pending.clear();
    });
  }
  
  private async tryConnectToDaemon(): Promise<boolean> {
    try {
      // Check if daemon is running by trying to connect to named pipe
      await this.connectToPipe();
      return true;
    } catch {
      return false;
    }
  }
  
  private async connectToPipe(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.pipe = net.createConnection({ path: StdioClient.PIPE_NAME }, () => {
        resolve();
      });
      
      this.pipe.on('error', reject);
      this.pipe.on('data', (chunk) => this.handleData(chunk));
      this.pipe.on('close', () => {
        this.pipe = null;
        this.pending.clear();
      });
    });
  }
  
  private handleData(chunk: any): void {
    this.buffer += String(chunk);
    let idx;
    while ((idx = this.buffer.indexOf("\n")) >= 0) {
      const line = this.buffer.slice(0, idx).trim();
      this.buffer = this.buffer.slice(idx + 1);
      if (!line) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.event) {
          this.onEvent?.(msg as StdioEvent);
        } else if (typeof msg.id === "number" && msg.result) {
          const cb = this.pending.get(msg.id);
          if (cb) {
            this.pending.delete(msg.id);
            cb(msg.result as StdioResult);
          }
        }
      } catch (e) {
        // Ignore unparsable lines
      }
    }
  }

  stop() {
    if (this.useDaemon && this.pipe) {
      try { this.pipe.end(); } catch {}
      this.pipe = null;
    } else {
      try { this.proc?.kill(); } catch {}
      this.proc = null;
    }
    this.pending.clear();
  }

  request<T = StdioResult>(method: string, params?: any): Promise<T> {
    return new Promise((resolve, reject) => {
      let writable = false;
      
      if (this.useDaemon && this.pipe) {
        writable = this.pipe.writable;
      } else if (this.proc && this.proc.stdin) {
        writable = this.proc.stdin.writable;
      }
      
      if (!writable) {
        return reject(new Error("STDIO server not running"));
      }
      
      const id = this.nextId++;
      this.pending.set(id, (res) => resolve(res as unknown as T));
      const req = { id, method, params };
      const message = JSON.stringify(req) + "\n";
      
      if (this.useDaemon && this.pipe) {
        this.pipe.write(message);
      } else if (this.proc && this.proc.stdin) {
        this.proc.stdin.write(message);
      }
    });
  }
  
  isUsingDaemon(): boolean {
    return this.useDaemon;
  }
}

/**
 * Create and start a STDIO client with automatic daemon detection
 */
export async function createStdioClient(
  pythonPath: string,
  projectPath: string,
  onEvent?: (evt: StdioEvent) => void
): Promise<StdioClient> {
  const client = new StdioClient(pythonPath, projectPath, onEvent);
  await client.start();
  return client;
}

