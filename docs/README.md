# MeetingScribe Documentation

## 📋 Documentation Structure

### Version 1.x (Current Implementation)
**Location**: [`v1-current/`](./v1-current/)
- **Runtime Interface** - JSON-RPC STDIO communication protocols
- **Architecture Evolution** - Incremental enhancement approach  
- **API Completion Analysis** - HTTP adapter specifications
- **Core Completion Analysis** - Component completion status

### Version 2.0 (Client-Daemon Architecture)
**Location**: [`v2-client-daemon/`](./v2-client-daemon/)
- **Complete architectural redesign** with Windows Service daemon
- **Krisp AI-inspired** performance benchmarks and implementation
- **Zero breaking changes** migration strategy
- **Multi-client support** (Raycast + CLI concurrent)

### Other Documentation
**Location**: [`architecture/`](./architecture/)
- Current state analysis and architectural documentation

---

## 🎯 Quick Navigation

### For Current v1.x Implementation
- [Runtime Interface Spec](./v1-current/runtime-interface.md) - JSON-RPC commands and responses
- [Architecture Evolution](./v1-current/architecture-evolution.md) - Incremental enhancement strategy

### For v2.0 Client-Daemon Migration  
- [v2.0 Overview](./v2-client-daemon/README.md) - Project goals and architecture vision
- [Migration Phases](./v2-client-daemon/migration-phases.md) - 5-phase implementation roadmap
- [Performance Benchmarks](./v2-client-daemon/performance-benchmarks.md) - Krisp AI-based targets

---

## 📊 Version Comparison

| Aspect | v1.x Current | v2.0 Client-Daemon |
|--------|-------------|-------------------|
| **Architecture** | CLI + STDIO Server | Windows Service + Clients |
| **Startup Time** | 15-30s | < 3s |
| **Multi-client** | Single process | Concurrent clients |
| **Model Loading** | Per-execution | Persistent daemon |
| **Deployment** | Manual execution | Professional service |

---

*Last Updated: 2025-09-07*