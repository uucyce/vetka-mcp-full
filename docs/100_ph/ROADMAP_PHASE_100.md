# VETKA Phase 100: Tauri Migration Roadmap

**Status:** PLANNED
**Target:** Q1 2026
**Theme:** "Desktop Native Experience"

---

## Overview

Phase 100 marks VETKA's transition from web-based React to native desktop via Tauri.
This enables:
- Native file system access (no more API proxying)
- System tray integration
- Local LLM execution (Ollama native)
- Offline-first architecture
- Native notifications & heartbeats

---

## Pre-Migration Checklist (from Phase 99)

- [x] STM Buffer integration (FIX_99.1)
- [x] MGC Cache implementation (FIX_99.2)
- [x] MemoryProxy with circuit breaker (FIX_99.2)
- [x] ARC Gap Detection MCP tools (FIX_99.3)
- [x] Dead code cleanup (FIX_99.4)
- [x] All 137+ tests passing
- [x] Git clean, pushed to GitHub

---

## Phase 100.1: Tauri Foundation

### Tasks
- [ ] Initialize Tauri project in `client/src-tauri/`
- [ ] Configure Rust backend with proper permissions
- [ ] Port Vite config for Tauri build
- [ ] Replace electron-like APIs with Tauri equivalents
- [ ] Test basic window + webview

### Files to Create
```
client/
  src-tauri/
    Cargo.toml
    tauri.conf.json
    src/
      main.rs
      commands.rs      # Rust <-> JS bridge
      file_system.rs   # Native FS access
```

---

## Phase 100.2: Native File System

### Tasks
- [ ] Implement Rust file watcher (notify crate)
- [ ] Replace Python file_watcher.py with native
- [ ] Direct file read/write without HTTP
- [ ] Native drag & drop support

### Migration Map
| Current (Python) | Target (Rust) |
|------------------|---------------|
| file_watcher.py | src-tauri/src/file_system.rs |
| local_scanner.py | Native Rust scanner |
| WebSocket file events | Tauri events |

---

## Phase 100.3: JARVIS Proactive Mode (Heartbeats)

### Tasks
- [ ] Implement heartbeat loop in Rust backend
- [ ] Check open tasks every 5-10 minutes
- [ ] Native system notifications
- [ ] Tray icon with status indicator
- [ ] "Continue task?" prompt via toast

### Architecture
```
HeartbeatService (Rust)
    |
    +-> Check Qdrant for open tasks
    +-> Check CAM for stale contexts
    +-> Emit notification via Tauri
    +-> Update tray icon badge
```

### Example Code Sketch
```rust
// src-tauri/src/heartbeat.rs
use std::time::Duration;
use tokio::time::interval;

pub async fn heartbeat_loop(app: tauri::AppHandle) {
    let mut ticker = interval(Duration::from_secs(300)); // 5 min

    loop {
        ticker.tick().await;

        if let Ok(tasks) = check_open_tasks().await {
            if !tasks.is_empty() {
                app.emit_all("heartbeat", HeartbeatPayload {
                    message: format!("{} open tasks", tasks.len()),
                    tasks: tasks,
                }).unwrap();
            }
        }
    }
}
```

---

## Phase 100.4: Local LLM Integration

### Tasks
- [ ] Native Ollama process management
- [ ] GPU detection and allocation
- [ ] Model download progress in UI
- [ ] Fallback to API when local unavailable

### Models Priority
1. Qwen2.5-7B (primary local)
2. Pixtral-12B (vision tasks)
3. Claude API (fallback)

---

## Phase 100.5: Offline-First Architecture

### Tasks
- [ ] SQLite for local state (replace some Qdrant queries)
- [ ] Sync queue for Qdrant when online
- [ ] Local embeddings (all-MiniLM via ONNX)
- [ ] Graceful degradation UI

---

## Phase 100.6: Polish & Release

### Tasks
- [ ] App signing (macOS notarization)
- [ ] Auto-updater via Tauri
- [ ] Installer for macOS/Windows/Linux
- [ ] Documentation update
- [ ] Beta release to testers

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| App startup time | ~3s (dev server) | <1s |
| File watch latency | ~100ms (WebSocket) | <10ms (native) |
| Memory footprint | ~500MB | ~200MB |
| Offline capability | None | Full local mode |

---

## Dependencies

### Rust Crates
- `tauri` - Core framework
- `notify` - File system watcher
- `tokio` - Async runtime
- `serde` - Serialization
- `rusqlite` - Local database
- `ort` - ONNX runtime for embeddings

### Keep from Current Stack
- React + Three.js (frontend unchanged)
- Qdrant (vector storage)
- Python MCP server (via stdio)

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 100.1 Foundation | 2-3 days | None |
| 100.2 File System | 2-3 days | 100.1 |
| 100.3 Heartbeats | 1-2 days | 100.1 |
| 100.4 Local LLM | 3-4 days | 100.2 |
| 100.5 Offline | 2-3 days | 100.4 |
| 100.6 Polish | 2-3 days | All |

**Total: ~2-3 weeks**

---

## Notes

- Heartbeats idea inspired by Moltbot's proactive mode
- Self-written skills feature deliberately skipped (too risky)
- Eternal disk persistence already covered by Qdrant snapshots
- Focus on native experience, not feature creep

---

*Created: 2026-01-28*
*Author: Claude Opus 4.5 + Данила*
