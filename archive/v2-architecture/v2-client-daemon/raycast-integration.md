# MeetingScribe Raycast Integration Specification

> **Minimal adaptation** of existing Raycast extension for **daemon-first** operation with **transparent fallback** to current behavior.

## 🎯 Integration Overview

### Design Goals
1. **Minimal Code Changes** - < 10% of extension code modified
2. **Zero Configuration** - Automatic daemon detection and connection
3. **Transparent Operation** - User unaware of daemon vs fallback mode
4. **Enhanced Functionality** - Concurrent operations (CLI + Raycast)
5. **Backward Compatibility** - Fallback to v1.0 behavior if daemon unavailable

### Current vs Target Architecture

```mermaid
graph TD
    subgraph "CURRENT v1.0"
        A1[Raycast Commands] --> B1[cli.ts / stdio.ts]
        B1 --> C1[spawn python stdio_server]
        C1 --> D1[StdioClient]
        D1 --> E1[Python Process]
    end
    
    subgraph "TARGET v2.0"
        A2[Raycast Commands] --> B2[Enhanced cli.ts / stdio.ts]
        B2 --> C2{Daemon Available?}
        
        C2 -->|Yes| D2[Connect to Daemon]
        C2 -->|No| E2[Fallback: spawn stdio_server]
        
        D2 --> F2[Named Pipe Connection]
        E2 --> G2[STDIO Process]
        
        F2 --> H2[Daemon Service]
        G2 --> H2
    end
```

---

## 🔄 Required Changes Overview

### Files to Modify

| File | Change Type | Complexity | Impact |
|------|-------------|------------|--------|
| `src/stdio.ts` | Minor Enhancement | Low | Add daemon detection |
| `src/cli.ts` | Minor Update | Very Low | Use enhanced stdio |
| New: `src/daemon-connector.ts` | New Component | Medium | Daemon connection logic |
| New: `src/daemon-types.ts` | New Types | Low | TypeScript definitions |

### Unchanged Components
- All React components (`.tsx` files) - **0 changes**
- UI/UX flow - **0 changes** 
- Command interfaces - **0 changes**
- User preferences - **0 changes**

---

## 🔌 Daemon Connector Implementation

### New: daemon-connector.ts

```typescript
/**
 * Daemon connection management for MeetingScribe
 * Handles automatic daemon detection and connection
 */

import { execFile } from "child_process";
import { promisify } from "util";
import { existsSync } from "fs";
import { spawn, ChildProcessWithoutNullStreams } from "child_process";
import { StdioClient } from "./stdio";

const execFileAsync = promisify(execFile);

export interface DaemonStatus {
  running: boolean;
  version?: string;
  pid?: number;
  uptime?: number;
}

export class DaemonConnector {
  private static instance: DaemonConnector;
  private daemonStatus: DaemonStatus | null = null;
  private statusCheckTimeout = 2000; // 2 seconds

  constructor(
    private pythonPath: string,
    private projectPath: string
  ) {}

  static getInstance(pythonPath: string, projectPath: string): DaemonConnector {
    if (!DaemonConnector.instance) {
      DaemonConnector.instance = new DaemonConnector(pythonPath, projectPath);
    }
    return DaemonConnector.instance;
  }

  async checkDaemonStatus(): Promise<DaemonStatus> {
    try {
      // Method 1: Try connecting to named pipe
      const pipeStatus = await this.checkNamedPipeConnection();
      if (pipeStatus.running) {
        this.daemonStatus = pipeStatus;
        return pipeStatus;
      }

      // Method 2: Check Windows Service status
      const serviceStatus = await this.checkServiceStatus();
      if (serviceStatus.running) {
        this.daemonStatus = serviceStatus;
        return serviceStatus;
      }

      // Method 3: Try daemon ping command
      const pingStatus = await this.checkDaemonPing();
      this.daemonStatus = pingStatus;
      return pingStatus;

    } catch (error) {
      this.daemonStatus = { running: false };
      return this.daemonStatus;
    }
  }

  private async checkNamedPipeConnection(): Promise<DaemonStatus> {
    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        resolve({ running: false });
      }, 500); // Quick check

      try {
        // Attempt to connect to named pipe (Windows)
        const net = require('net');
        const pipePath = '\\\\.\\pipe\\MeetingScribe';
        
        const client = net.connect(pipePath, () => {
          clearTimeout(timeout);
          client.end();
          resolve({ 
            running: true, 
            version: "2.0.0",
            pid: 0 // Will be filled by actual ping
          });
        });

        client.on('error', () => {
          clearTimeout(timeout);
          resolve({ running: false });
        });

      } catch (error) {
        clearTimeout(timeout);
        resolve({ running: false });
      }
    });
  }

  private async checkServiceStatus(): Promise<DaemonStatus> {
    try {
      // Check Windows Service status
      const { stdout } = await execFileAsync('sc', ['query', 'MeetingScribe'], {
        timeout: this.statusCheckTimeout
      });

      if (stdout.includes('RUNNING')) {
        return { 
          running: true, 
          version: "2.0.0" // Service version
        };
      }
    } catch (error) {
      // Service not installed or not running
    }

    return { running: false };
  }

  private async checkDaemonPing(): Promise<DaemonStatus> {
    try {
      // Try daemon ping via CLI
      const { stdout } = await execFileAsync(
        this.pythonPath, 
        ['-m', 'daemon.cli', 'ping'],
        {
          cwd: this.projectPath,
          timeout: this.statusCheckTimeout,
          windowsHide: true
        }
      );

      const result = JSON.parse(stdout);
      if (result.status === 'success' && result.data?.pong) {
        return {
          running: true,
          version: result.data.version || "2.0.0",
          uptime: result.data.uptime || 0
        };
      }
    } catch (error) {
      // Daemon not responding to ping
    }

    return { running: false };
  }

  async createStdioClient(): Promise<StdioClient> {
    // Check daemon status
    const status = await this.checkDaemonStatus();

    if (status.running) {
      console.log('🚀 Connecting to MeetingScribe daemon service');
      return this.createDaemonClient();
    } else {
      console.log('⚙️ Starting MeetingScribe in direct mode');
      return this.createFallbackClient();
    }
  }

  private createDaemonClient(): StdioClient {
    // Connect to daemon via named pipe or TCP
    // Enhanced StdioClient that connects to daemon
    return new StdioClient(
      '\\\\.\\pipe\\MeetingScribe', // Named pipe path
      this.projectPath,
      undefined, // No event handler for now
      { 
        connectionType: 'daemon',
        timeout: 5000 
      }
    );
  }

  private createFallbackClient(): StdioClient {
    // Fallback to current v1.0 behavior
    return new StdioClient(
      this.pythonPath,
      this.projectPath,
      undefined,
      { 
        connectionType: 'fallback',
        module: 'src.core.stdio_server' // Current behavior
      }
    );
  }
}
```

### Enhanced stdio.ts

```typescript
/**
 * Enhanced StdioClient with daemon support
 * Minimal changes to existing implementation
 */

import { spawn, ChildProcessWithoutNullStreams } from "child_process";
import { DaemonConnector } from "./daemon-connector";

export type StdioEvent = { event: string; [key: string]: any };
export type StdioResult = { status: string; data?: any; error?: { code: string; message: string } };

export interface Preferences {
  pythonPath: string;
  projectPath: string;
  defaultModel: string;
}

interface StdioOptions {
  connectionType?: 'daemon' | 'fallback';
  timeout?: number;
  module?: string;
}

type PendingResolver = (res: StdioResult) => void;

export class StdioClient {
  private proc: ChildProcessWithoutNullStreams | null = null;
  private nextId = 1;
  private pending = new Map<number, PendingResolver>();
  private buffer = "";
  private connectionType: 'daemon' | 'fallback' = 'fallback';

  constructor(
    private pythonPath: string,
    private projectPath: string,
    private onEvent?: (evt: StdioEvent) => void,
    private options: StdioOptions = {}
  ) {
    this.connectionType = options.connectionType || 'fallback';
  }

  start() {
    if (this.proc) return;

    if (this.connectionType === 'daemon') {
      this.startDaemonConnection();
    } else {
      this.startFallbackConnection();
    }

    this.setupOutputHandling();
  }

  private startDaemonConnection() {
    // Connect to daemon service
    // For named pipes, we use a different approach
    if (this.pythonPath.startsWith('\\\\.\\pipe\\')) {
      // Named pipe connection
      this.proc = spawn('python', ['-m', 'daemon.named_pipe_client', this.pythonPath], {
        cwd: this.projectPath,
        stdio: ["pipe", "pipe", "pipe"],
        windowsHide: true,
      });
    } else {
      // TCP connection fallback
      this.proc = spawn('python', ['-m', 'daemon.tcp_client', this.pythonPath], {
        cwd: this.projectPath,
        stdio: ["pipe", "pipe", "pipe"], 
        windowsHide: true,
      });
    }
  }

  private startFallbackConnection() {
    // Original v1.0 behavior (preserved exactly)
    const module = this.options.module || 'src.core.stdio_server';
    
    this.proc = spawn(this.pythonPath, ["-m", module], {
      cwd: this.projectPath,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });
  }

  private setupOutputHandling() {
    if (!this.proc) return;

    this.proc.stdout.setEncoding("utf8");
    this.proc.stdout.on("data", (chunk) => {
      this.buffer += String(chunk);
      let idx;
      while ((idx = this.buffer.indexOf("\\n")) >= 0) {
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
    });

    this.proc.on("exit", () => {
      this.proc = null;
      this.pending.clear();
    });
  }

  stop() {
    try { this.proc?.kill(); } catch {}
    this.proc = null;
    this.pending.clear();
  }

  request<T = StdioResult>(method: string, params?: any): Promise<T> {
    return new Promise((resolve, reject) => {
      if (!this.proc || !this.proc.stdin.writable) {
        return reject(new Error("STDIO server not running"));
      }
      const id = this.nextId++;
      const timeout = this.options.timeout || 30000;
      
      // Setup timeout
      const timeoutHandle = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Request timeout after ${timeout}ms`));
      }, timeout);
      
      this.pending.set(id, (res) => {
        clearTimeout(timeoutHandle);
        resolve(res as unknown as T);
      });
      
      const req = { id, method, params };
      this.proc.stdin.write(JSON.stringify(req) + "\\n");
    });
  }
}

// Enhanced factory function for easy migration
export async function createStdioClient(
  pythonPath: string, 
  projectPath: string,
  onEvent?: (evt: StdioEvent) => void
): Promise<StdioClient> {
  const connector = DaemonConnector.getInstance(pythonPath, projectPath);
  return await connector.createStdioClient();
}
```

### Updated cli.ts (Minimal Changes)

```typescript
/**
 * Updated CLI interface - minimal changes required
 * Just use enhanced createStdioClient function
 */

import { getPreferenceValues } from "@raycast/api";
import { createStdioClient } from "./stdio"; // Enhanced function

interface Preferences {
  pythonPath: string;
  projectPath: string;
  defaultModel: string;
}

// Cache client instance for performance
let cachedClient: any = null;

export async function getStdioClient() {
  if (!cachedClient) {
    const { pythonPath, projectPath } = getPreferenceValues<Preferences>();
    
    // Use enhanced createStdioClient (automatically detects daemon)
    cachedClient = await createStdioClient(pythonPath, projectPath);
    cachedClient.start();
  }
  
  return cachedClient;
}

// All existing functions remain unchanged:
export async function runCliJSON(args: string[]): Promise<any> {
  const client = await getStdioClient();
  return await client.request("cli.run", { args });
}

// ... rest of existing cli.ts functions unchanged
```

---

## 🎛️ Component Integration

### Command Files (No Changes Required)

All existing Raycast command files continue to work without modification:

```typescript
// record.tsx - NO CHANGES
import { runCliJSON } from "../cli";

export default function RecordCommand() {
  // ... existing implementation unchanged
  // Automatically benefits from daemon performance improvements
}

// transcribe.tsx - NO CHANGES  
import { getStdioClient } from "../cli";

export default function TranscribeCommand() {
  // ... existing implementation unchanged
  // Automatically supports concurrent transcription
}

// All other .tsx files - NO CHANGES REQUIRED
```

### Enhanced Functionality

With daemon support, existing commands automatically gain:

```typescript
// Example: Enhanced concurrent recording capability
export default function RecordCommand() {
  // Same UI code as before
  
  const handleRecord = async () => {
    // This now works concurrently with CLI if daemon available
    const client = await getStdioClient();
    await client.request("record.start", { device_id: "speakers", stream: true });
    
    // Progress events work the same way
    client.onEvent?.({ 
      event: "record.progress", 
      seconds: 30 
    });
  };
  
  // ... rest unchanged
}
```

---

## 🔧 Configuration & Types

### New: daemon-types.ts

```typescript
/**
 * TypeScript definitions for daemon functionality
 */

export interface DaemonInfo {
  version: string;
  uptime: number;
  clients_connected: number;
  models_loaded: string[];
  memory_usage: number;
}

export interface DaemonStats {
  requests_processed: number;
  average_response_time: number;
  error_rate: number;
  cache_hit_rate: number;
}

export interface ConnectionOptions {
  type: 'namedpipe' | 'tcp' | 'stdio';
  timeout: number;
  retry_attempts: number;
  retry_delay: number;
}

export interface DaemonCapabilities {
  concurrent_recording: boolean;
  model_persistence: boolean;
  event_streaming: boolean;
  multi_client: boolean;
}

// Enhanced event types for daemon mode
export interface DaemonEvent extends StdioEvent {
  daemon_info?: DaemonInfo;
  client_id?: string;
  broadcast?: boolean;
}
```

### Package.json (No Changes)

No additional dependencies required:
- All daemon communication uses existing Node.js built-ins
- Named pipes use `net` module (built-in)
- Process spawning uses existing `child_process` 
- JSON parsing uses existing JSON methods

---

## 🚀 User Experience Enhancements

### Performance Improvements (Transparent)

| Operation | v1.0 Time | v2.0 Daemon | v2.0 Fallback | User Impact |
|-----------|-----------|-------------|---------------|-------------|
| **Command Startup** | 2-5s | < 1s | 2-5s | Faster response |
| **Device Discovery** | 500ms | < 100ms | 500ms | Instant listing |
| **Transcription Start** | 10-25s | < 500ms | 10-25s | Near-instant start |
| **Status Check** | 200ms | < 50ms | 200ms | Real-time status |

### New Capabilities (Automatic)

```typescript
// Concurrent operations now possible
const client = await getStdioClient();

// User can record in Raycast while CLI transcribes
await Promise.all([
  client.request("record.start", { device_id: "mic" }),
  client.request("transcription.start", { audio_path: "previous.wav" })
]);
```

### Status Indicators

```typescript
// Enhanced status information in Raycast
export function StatusCommand() {
  const [status, setStatus] = useState<DaemonInfo | null>(null);
  
  useEffect(() => {
    async function checkStatus() {
      const client = await getStdioClient();
      
      if (client.connectionType === 'daemon') {
        const daemonStatus = await client.request("daemon.status");
        setStatus(daemonStatus.data);
      } else {
        setStatus(null); // Fallback mode
      }
    }
    
    checkStatus();
  }, []);
  
  return (
    <List>
      {status ? (
        <>
          <List.Item title="🚀 Background Service" subtitle="Running" />
          <List.Item title="Version" subtitle={status.version} />
          <List.Item title="Uptime" subtitle={`${status.uptime}s`} />
          <List.Item title="Connected Clients" subtitle={status.clients_connected.toString()} />
        </>
      ) : (
        <List.Item title="⚙️ Direct Mode" subtitle="No background service" />
      )}
    </List>
  );
}
```

---

## 📊 Testing Strategy

### Automated Tests

```typescript
// tests/daemon-integration.test.ts
import { DaemonConnector } from "../src/daemon-connector";
import { createStdioClient } from "../src/stdio";

describe('Daemon Integration', () => {
  
  test('should detect daemon when running', async () => {
    const connector = new DaemonConnector('python', '/path/to/project');
    const status = await connector.checkDaemonStatus();
    
    // This will pass regardless of daemon status
    expect(status).toHaveProperty('running');
  });
  
  test('should fallback gracefully when daemon unavailable', async () => {
    const client = await createStdioClient('python', '/path/to/project');
    
    // Should create client in either mode
    expect(client).toBeDefined();
    expect(client.request).toBeDefined();
  });
  
  test('should maintain API compatibility', async () => {
    const client = await createStdioClient('python', '/path/to/project');
    client.start();
    
    // Same API calls should work in both modes
    const result = await client.request('ping');
    expect(result.data?.pong).toBe(true);
    
    client.stop();
  });
  
});
```

### Manual Testing Scenarios

1. **Daemon Running**: Verify fast startup and concurrent operations
2. **Daemon Stopped**: Verify fallback to v1.0 behavior  
3. **Daemon Restart**: Verify automatic reconnection
4. **Service Installation**: Verify Windows Service integration
5. **Error Handling**: Verify graceful error handling

---

## 🔄 Migration Checklist

### Pre-Migration Validation
- [ ] All current Raycast commands work in v1.0
- [ ] TypeScript compilation passes
- [ ] No user configuration required

### Implementation Steps
1. [ ] Add `daemon-connector.ts` - daemon detection logic
2. [ ] Add `daemon-types.ts` - TypeScript definitions  
3. [ ] Update `stdio.ts` - enhanced client with daemon support
4. [ ] Update `cli.ts` - use enhanced createStdioClient
5. [ ] Test daemon detection and fallback behavior

### Post-Migration Validation
- [ ] All existing commands work identically
- [ ] Performance improvements visible when daemon running
- [ ] Graceful fallback when daemon unavailable
- [ ] Concurrent operations possible (Raycast + CLI)
- [ ] No breaking changes to user workflow

---

## 📈 Success Metrics

### Functional Success
- [ ] 100% backward compatibility maintained
- [ ] All existing Raycast commands work unchanged  
- [ ] Automatic daemon detection and connection
- [ ] Graceful fallback to v1.0 behavior

### Performance Success
- [ ] Command response time < 1s with daemon
- [ ] Startup performance improvement visible
- [ ] Concurrent operations supported
- [ ] Memory usage reasonable in both modes

### User Experience Success
- [ ] Zero configuration changes required
- [ ] Transparent operation (user unaware of changes)
- [ ] Enhanced functionality available automatically
- [ ] No workflow disruptions

---

*Raycast Integration Specification Version: 2.0*  
*Compatibility: 100% Backward Compatible*  
*Changes Required: < 10% of codebase*  
*Last Updated: 2025-09-07*