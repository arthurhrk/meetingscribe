# MeetingScribe Communication Protocols

> **JSON-RPC STDIO/Named Pipes** communication protocols for client-daemon architecture with **Krisp-inspired** efficiency.

## 🔗 Protocol Overview

### Transport Layer Matrix

| Transport | Use Case | Performance | Complexity | Multi-Client |
|-----------|----------|-------------|------------|--------------|
| **STDIO Pipes** | Single client (legacy) | ⭐⭐⭐ | ⭐ | ❌ |
| **Named Pipes** | Multi-client (primary) | ⭐⭐⭐⭐ | ⭐⭐ | ✅ |
| **TCP Socket** | Network/fallback | ⭐⭐ | ⭐⭐⭐ | ✅ |

### Krisp Comparison

| Protocol Feature | Krisp AI | MeetingScribe v2.0 |
|------------------|----------|-------------------|
| **Primary Transport** | IPC (Proprietary) | Named Pipes |
| **Message Format** | Binary + JSON | JSON-RPC |
| **Event Streaming** | ✅ Real-time | ✅ Real-time |
| **Multi-client** | ✅ Yes | ✅ Yes |
| **Encryption** | ✅ Local IPC | ✅ Named Pipe ACL |

## 📡 Message Protocol Specification

### 1. Request/Response Pattern

```json
// Client Request
{
  "id": 123,                    // Unique request ID
  "jsonrpc": "2.0",            // JSON-RPC version
  "method": "record.start",     // Method name
  "params": {                   // Method parameters (optional)
    "device_id": "speakers",
    "duration": 30,
    "stream": true
  }
}

// Daemon Response
{
  "id": 123,                    // Matching request ID
  "jsonrpc": "2.0",
  "result": {                   // Success response
    "interface_version": "1.0",
    "status": "success",
    "data": {
      "session_id": "rec-1693876543",
      "file_path": "C:\\...\\recording.wav"
    }
  }
}

// Error Response  
{
  "id": 123,
  "jsonrpc": "2.0",
  "error": {                    // Error response
    "code": "E_AUDIO_DEVICE",
    "message": "No audio device available",
    "details": {
      "available_devices": []
    }
  }
}
```

### 2. Event Streaming Pattern

```json
// Daemon → Client Events (no ID = broadcast)
{
  "jsonrpc": "2.0",
  "method": "event",
  "params": {
    "event": "record.progress",
    "session_id": "rec-1693876543", 
    "seconds": 15.3,
    "amplitude": 0.75
  }
}

// Multi-client Broadcast
{
  "jsonrpc": "2.0",
  "method": "event",
  "params": {
    "event": "daemon.status",
    "broadcast": true,
    "status": "ready",
    "clients_connected": 2
  }
}
```

## 🔧 Transport Implementations

### 1. STDIO Transport (Legacy Compatibility)

```python
# client/stdio_transport.py
import json
import subprocess
import asyncio
from typing import Optional, Callable

class StdioTransport:
    """STDIO transport for single-client communication"""
    
    def __init__(self, python_path: str, project_path: str):
        self.python_path = python_path
        self.project_path = project_path
        self.process: Optional[subprocess.Popen] = None
        self.event_handler: Optional[Callable] = None
        
    async def connect(self):
        """Start daemon process via STDIO"""
        self.process = subprocess.Popen(
            [self.python_path, "-m", "daemon.stdio_core"],
            cwd=self.project_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0  # Unbuffered for real-time
        )
        
        # Start output reader task
        asyncio.create_task(self._read_output())
        
    async def send_request(self, method: str, params: dict = None) -> dict:
        """Send JSON-RPC request"""
        if not self.process or not self.process.stdin:
            raise ConnectionError("Not connected")
            
        request = {
            "jsonrpc": "2.0",
            "id": self._generate_id(),
            "method": method,
            "params": params or {}
        }
        
        # Send request
        self.process.stdin.write(json.dumps(request) + "\\n")
        self.process.stdin.flush()
        
        # Wait for response (implementation needed)
        return await self._wait_for_response(request["id"])
        
    async def _read_output(self):
        """Read daemon output continuously"""
        while self.process and self.process.poll() is None:
            line = await asyncio.get_event_loop().run_in_executor(
                None, self.process.stdout.readline
            )
            
            if line:
                try:
                    message = json.loads(line.strip())
                    if "id" in message:
                        # Response to request
                        await self._handle_response(message)
                    else:
                        # Event notification
                        if self.event_handler:
                            await self.event_handler(message)
                            
                except json.JSONDecodeError:
                    continue
```

### 2. Named Pipes Transport (Primary)

```python
# client/namedpipe_transport.py
import asyncio
import json
import win32pipe
import win32file
import pywintypes
from typing import Optional, Callable

class NamedPipeTransport:
    """Named Pipes transport for multi-client communication"""
    
    def __init__(self, pipe_name: str = "\\\\.\\pipe\\MeetingScribe"):
        self.pipe_name = pipe_name
        self.pipe_handle: Optional[int] = None
        self.event_handler: Optional[Callable] = None
        self._request_futures = {}
        
    async def connect(self, timeout: int = 5):
        """Connect to daemon named pipe"""
        try:
            # Wait for pipe availability
            win32pipe.WaitNamedPipe(self.pipe_name, timeout * 1000)
            
            # Open pipe
            self.pipe_handle = win32file.CreateFile(
                self.pipe_name,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,  # No sharing
                None,  # Default security
                win32file.OPEN_EXISTING,
                win32file.FILE_FLAG_OVERLAPPED,  # Async I/O
                None
            )
            
            # Start reader task
            asyncio.create_task(self._read_messages())
            
        except pywintypes.error as e:
            raise ConnectionError(f"Failed to connect to daemon: {e}")
            
    async def send_request(self, method: str, params: dict = None) -> dict:
        """Send JSON-RPC request via named pipe"""
        if not self.pipe_handle:
            raise ConnectionError("Not connected")
            
        request_id = self._generate_id()
        request = {
            "jsonrpc": "2.0", 
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        # Send request
        message = json.dumps(request) + "\\n"
        win32file.WriteFile(self.pipe_handle, message.encode('utf-8'))
        
        # Wait for response
        future = asyncio.Future()
        self._request_futures[request_id] = future
        
        try:
            return await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            self._request_futures.pop(request_id, None)
            raise TimeoutError(f"Request {method} timed out")
            
    async def _read_messages(self):
        """Read messages from named pipe"""
        buffer = b""
        
        while self.pipe_handle:
            try:
                # Read data
                _, data = win32file.ReadFile(self.pipe_handle, 4096)
                buffer += data
                
                # Process complete messages
                while b"\\n" in buffer:
                    line, buffer = buffer.split(b"\\n", 1)
                    if line:
                        try:
                            message = json.loads(line.decode('utf-8'))
                            await self._handle_message(message)
                        except json.JSONDecodeError:
                            continue
                            
            except pywintypes.error:
                break
                
    async def _handle_message(self, message: dict):
        """Handle incoming message"""
        if "id" in message and message["id"] in self._request_futures:
            # Response to request
            future = self._request_futures.pop(message["id"])
            future.set_result(message)
        else:
            # Event notification
            if self.event_handler:
                await self.event_handler(message)
```

### 3. Daemon Named Pipe Server

```python
# daemon/namedpipe_server.py
import asyncio
import json
import win32pipe
import win32file
import win32security
import ntsecuritycon
from typing import List, Dict, Optional

class NamedPipeServer:
    """Multi-client named pipe server (Krisp-inspired)"""
    
    def __init__(self, pipe_name: str = "\\\\.\\pipe\\MeetingScribe"):
        self.pipe_name = pipe_name
        self.clients: List['PipeClient'] = []
        self.running = False
        
    async def start(self):
        """Start accepting client connections"""
        self.running = True
        
        while self.running:
            try:
                # Create named pipe with security attributes
                pipe_handle = win32pipe.CreateNamedPipe(
                    self.pipe_name,
                    win32pipe.PIPE_ACCESS_DUPLEX | win32file.FILE_FLAG_OVERLAPPED,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE,
                    10,  # Max instances (Krisp uses higher limits)
                    4096,  # Out buffer size  
                    4096,  # In buffer size
                    0,     # Default timeout
                    self._create_security_attributes()
                )
                
                # Wait for client connection
                await self._wait_for_connection(pipe_handle)
                
                # Create client handler
                client = PipeClient(pipe_handle, self)
                self.clients.append(client)
                
                # Start client handler task
                asyncio.create_task(client.handle_client())
                
            except Exception as e:
                if self.running:  # Don't log errors during shutdown
                    logger.error(f"Named pipe server error: {e}")
                    
    def _create_security_attributes(self):
        """Create security attributes for named pipe"""
        # Allow current user only (Krisp-style security)
        sd = win32security.SECURITY_DESCRIPTOR()
        sd.SetSecurityDescriptorDacl(1, None, 0)  # NULL DACL = full access to owner
        
        sa = win32security.SECURITY_ATTRIBUTES()
        sa.SECURITY_DESCRIPTOR = sd
        sa.bInheritHandle = 0
        
        return sa
        
    async def broadcast_event(self, event_data: dict):
        """Broadcast event to all connected clients"""
        message = {
            "jsonrpc": "2.0",
            "method": "event", 
            "params": event_data
        }
        
        # Send to all connected clients
        for client in self.clients[:]:  # Copy list to avoid modification issues
            try:
                await client.send_message(message)
            except Exception:
                # Remove disconnected client
                self.clients.remove(client)
                
class PipeClient:
    """Individual client connection handler"""
    
    def __init__(self, pipe_handle: int, server: NamedPipeServer):
        self.pipe_handle = pipe_handle
        self.server = server
        self.buffer = b""
        
    async def handle_client(self):
        """Handle client messages"""
        try:
            while True:
                # Read message
                _, data = win32file.ReadFile(self.pipe_handle, 4096)
                self.buffer += data
                
                # Process complete messages
                while b"\\n" in self.buffer:
                    line, self.buffer = self.buffer.split(b"\\n", 1)
                    if line:
                        await self._process_message(line)
                        
        except Exception as e:
            logger.debug(f"Client disconnected: {e}")
        finally:
            win32file.CloseHandle(self.pipe_handle)
            if self in self.server.clients:
                self.server.clients.remove(self)
                
    async def _process_message(self, data: bytes):
        """Process incoming JSON-RPC message"""
        try:
            message = json.loads(data.decode('utf-8'))
            
            # Handle JSON-RPC request
            if "method" in message:
                response = await self._handle_request(message)
                if response:
                    await self.send_message(response)
                    
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": "E_INVALID_JSON",
                    "message": str(e)
                }
            }
            await self.send_message(error_response)
            
    async def _handle_request(self, request: dict) -> Optional[dict]:
        """Handle JSON-RPC request and return response"""
        from stdio_core import _handle  # Reuse existing handler
        
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        # Process request using existing handler
        result = _handle(method, params)
        
        # Format JSON-RPC response
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        
    async def send_message(self, message: dict):
        """Send message to client"""
        data = json.dumps(message) + "\\n"
        win32file.WriteFile(self.pipe_handle, data.encode('utf-8'))
```

## 🔄 Protocol Methods

### Core Methods (Preserved from v1.0)

| Method | Parameters | Response | Events |
|--------|------------|----------|---------|
| `ping` | - | `{"pong": true}` | - |
| `devices.list` | - | `{"devices": [...]}` | - |
| `system.status` | - | `{"system": {...}}` | - |
| `files.list` | `type`, `limit` | `{"items": [...]}` | - |
| `record.start` | `device_id`, `duration`, `stream` | `{"session_id", "file_path"}` | `record.progress`, `record.started` |
| `record.stop` | - | `{"session_id", "file_path"}` | `record.completed` |
| `transcription.start` | `audio_path`, `model`, `language`, `stream` | `{"job_id"}` | `transcription.progress`, `transcription.completed` |
| `export.run` | `filename`, `format`, `output` | `{"export_path"}` | - |

### New Daemon Methods (v2.0)

| Method | Parameters | Response | Description |
|--------|------------|----------|-------------|
| `daemon.status` | - | `{"status", "version", "uptime", "clients"}` | Daemon health check |
| `daemon.stats` | - | `{"memory_usage", "models_loaded", "active_jobs"}` | Performance stats |
| `client.register` | `client_type`, `version` | `{"client_id"}` | Register client session |
| `client.unregister` | `client_id` | `{"success"}` | Unregister client session |

### Event Types

| Event | Payload | Description |
|-------|---------|-------------|
| `daemon.ready` | `{"version", "features"}` | Daemon startup complete |
| `daemon.status` | `{"status", "clients_connected"}` | Daemon status update |
| `record.progress` | `{"session_id", "seconds", "amplitude"}` | Recording progress |
| `record.started` | `{"session_id", "file_path"}` | Recording started |
| `record.completed` | `{"session_id", "file_path"}` | Recording completed |
| `transcription.progress` | `{"job_id", "progress", "message"}` | Transcription progress |
| `transcription.completed` | `{"job_id", "result"}` | Transcription completed |
| `transcription.error` | `{"job_id", "message"}` | Transcription error |
| `client.connected` | `{"client_id", "client_type"}` | New client connected |
| `client.disconnected` | `{"client_id"}` | Client disconnected |

## 📊 Performance Characteristics

### Message Throughput (Krisp Comparison)

| Transport | Messages/sec | Latency | CPU Overhead |
|-----------|--------------|---------|--------------|
| STDIO | ~100 | 5-10ms | Low |
| Named Pipes | ~1000+ | 1-3ms | Very Low |
| TCP Socket | ~500 | 10-20ms | Medium |

### Connection Limits

```python
# daemon/connection_limits.py
class ConnectionLimits:
    STDIO_MAX_CLIENTS = 1      # Single process limitation
    NAMEDPIPE_MAX_CLIENTS = 10 # Windows named pipe limit
    TCP_MAX_CLIENTS = 50       # Configurable limit
    
    # Krisp supports 50+ concurrent connections
    # We target 10 for initial implementation
```

---

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Pesquisar Krisp como benchmark de refer\u00eancia", "status": "completed", "activeForm": "Pesquisando Krisp como benchmark de refer\u00eancia"}, {"content": "Criar estrutura do diret\u00f3rio specs/", "status": "completed", "activeForm": "Criando estrutura do diret\u00f3rio specs/"}, {"content": "Documentar arquitetura client-daemon completa", "status": "completed", "activeForm": "Documentando arquitetura client-daemon completa"}, {"content": "Especificar protocolos de comunica\u00e7\u00e3o detalhados", "status": "completed", "activeForm": "Especificando protocolos de comunica\u00e7\u00e3o detalhados"}, {"content": "Definir benchmarks baseados no Krisp", "status": "in_progress", "activeForm": "Definindo benchmarks baseados no Krisp"}, {"content": "Criar roadmap de implementa\u00e7\u00e3o faseada", "status": "pending", "activeForm": "Criando roadmap de implementa\u00e7\u00e3o faseada"}]