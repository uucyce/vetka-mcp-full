# Phase 175 — MYCELIUM.app Implementation Plan

> **Goal:** Standalone MCC as macOS app (dmg/app)
> **Prerequisite:** Phase 174 complete (REFLEX Live + Agent Chat Streams)
> **Depends on:** Recon report (`RECON_175_UNIFIED.md`), Grok research

---

## Wave 0: Foundation (Codex — parallel)

| Task | Description | Owner | Effort |
|------|-------------|-------|--------|
| 175.0A | 3 missing API endpoints (PATCH task, POST feedback, POST chat/quick) | Codex | 3h |
| 175.0B | MiniBalance store extraction (useStore → useMCCStore) | Codex | 0.5h |
| 175.0C | Tests for new endpoints | Codex | 1h |

Brief: `docs/175_MCC_APP/CODEX_BRIEF_175_MCC_ENDPOINTS.md`

---

## Wave 1: Build Splitting (Opus — 175.1-175.3)

### 175.1 — mycelium.html Entry Point

**File:** `client/mycelium.html` (NEW)

Minimal HTML entry that mounts MCC standalone:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>MYCELIUM</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/mycelium-entry.tsx"></script>
</body>
</html>
```

**File:** `client/src/mycelium-entry.tsx` (NEW)

Dedicated entry point (no App.tsx, no static Tauri import):
```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import MyceliumStandalone from './MyceliumStandalone';
import './styles/voice.css';
import './styles/tokens.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MyceliumStandalone />
  </React.StrictMode>
);
```

### 175.2 — Vite Multi-Page Config

**File:** `client/vite.config.ts` (MODIFY)

Add conditional multi-page input:
```typescript
const isMCC = process.env.VITE_MODE === 'mcc';

build: {
  rollupOptions: {
    input: isMCC
      ? { mycelium: resolve(__dirname, 'mycelium.html') }
      : { vetka: resolve(__dirname, 'index.html') }
  }
}
```

**Scripts** in `package.json`:
```json
{
  "build:mcc": "VITE_MODE=mcc vite build --outDir dist-mcc",
  "dev:mcc": "VITE_MODE=mcc vite --port 3002"
}
```

### 175.3 — Verify Tree-Shaking

Build MCC bundle and verify Three.js/3D code is excluded:
```bash
cd client && npm run build:mcc
du -sh dist-mcc/  # Should be ~8-10MB vs ~25MB full
```

---

## Wave 2: Tauri MCC Project (Opus — 175.4-175.6)

### 175.4 — src-tauri-mcc/ Directory

```
src-tauri-mcc/
├── Cargo.toml
├── build.rs
├── tauri.conf.json
├── capabilities/
│   └── default.json
├── icons/           ← MYCELIUM icon set
└── src/
    └── main.rs
```

### 175.5 — Minimal main.rs

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            check_backend_health,
            get_backend_url,
        ])
        .run(tauri::generate_context!())
        .expect("error while running MYCELIUM");
}

#[tauri::command]
async fn check_backend_health() -> Result<String, String> {
    match reqwest::get("http://localhost:5001/api/health").await {
        Ok(resp) => Ok(format!("Backend: {}", resp.status())),
        Err(e) => Err(e.to_string()),
    }
}

#[tauri::command]
fn get_backend_url() -> String {
    "http://localhost:5001".to_string()
}
```

### 175.6 — tauri.conf.json (MCC)

Single window pointing to `mycelium.html`:
```json
{
  "productName": "MYCELIUM",
  "identifier": "com.vetka.mycelium",
  "build": {
    "beforeBuildCommand": "npm run build:mcc",
    "frontendDist": "../client/dist-mcc"
  },
  "app": {
    "windows": [{
      "label": "main",
      "title": "MYCELIUM Command Center",
      "width": 1200,
      "height": 800,
      "minWidth": 800,
      "minHeight": 600,
      "url": "/mycelium.html"
    }],
    "security": {
      "csp": "default-src 'self'; connect-src 'self' http://localhost:5001 ws://localhost:8082; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
    }
  }
}
```

---

## Wave 3: Packaging + Distribution (175.7-175.8)

### 175.7 — Build Script

**File:** `scripts/build_mycelium.sh` (NEW)

```bash
#!/bin/bash
set -e
echo "🍄 Building MYCELIUM.app..."

# 1. Build frontend
cd client && VITE_MODE=mcc npm run build:mcc && cd ..

# 2. Build Tauri
cd src-tauri-mcc && cargo tauri build && cd ..

echo "✅ MYCELIUM.app ready: src-tauri-mcc/target/release/bundle/dmg/"
```

### 175.8 — Backend Sidecar (deferred to 175.2 phase)

PyInstaller bundle of `run_mycelium.py` for auto-launch.
Deferred until Wave 1+2 are stable.

---

## Wave 4: Generic TaskBoard (Dragon — 175.9-175.11)

### 175.9 — REST TaskBoard API

**File:** `src/api/routes/taskboard_routes.py` (NEW)

Generic REST endpoints with adapter pattern:
- `POST /api/taskboard/create`
- `GET /api/taskboard/list`
- `POST /api/taskboard/dispatch`
- `PATCH /api/taskboard/{id}`

### 175.10 — Adapter Layer

**File:** `src/orchestration/taskboard_adapters.py` (NEW)

```python
class ClaudeMCPAdapter:
    """Bridges REST taskboard to MCP task_board tool."""

class CursorAdapter:
    """Bridges REST taskboard to Cursor SSE protocol."""

class VSCodeAdapter:
    """Bridges REST taskboard to VSCode task runner."""
```

### 175.11 — MultiTask Client Detection

Auto-detect which AI client is connected via User-Agent / handshake:
- Claude Code → ClaudeMCPAdapter
- Cursor → CursorAdapter
- OpenCode → REST (direct)

---

## Success Criteria

1. `npm run dev:mcc` opens MCC in browser at localhost:3002
2. All 5 MiniWindows render and function
3. DAG view shows tasks, pipeline executes
4. `cargo tauri build` in src-tauri-mcc/ produces MYCELIUM.app
5. dmg under 20MB
6. Backend connection via REST (no Tauri IPC needed)
7. WebSocket events stream in real-time

---

## File Inventory

### New Files

| File | Lines | Wave |
|------|-------|------|
| `client/mycelium.html` | ~15 | 1 |
| `client/src/mycelium-entry.tsx` | ~20 | 1 |
| `src-tauri-mcc/Cargo.toml` | ~25 | 2 |
| `src-tauri-mcc/build.rs` | ~5 | 2 |
| `src-tauri-mcc/tauri.conf.json` | ~50 | 2 |
| `src-tauri-mcc/capabilities/default.json` | ~15 | 2 |
| `src-tauri-mcc/src/main.rs` | ~30 | 2 |
| `scripts/build_mycelium.sh` | ~15 | 3 |
| `src/api/routes/taskboard_routes.py` | ~80 | 4 |
| `src/orchestration/taskboard_adapters.py` | ~120 | 4 |

### Modified Files

| File | Change | Wave |
|------|--------|------|
| `client/vite.config.ts` | Multi-page input | 1 |
| `client/package.json` | build:mcc + dev:mcc scripts | 1 |
| `src/api/routes/mcc_routes.py` | 2 endpoints (Codex) | 0 |
| `src/api/routes/chat_routes.py` | 1 endpoint (Codex) | 0 |
| `client/src/store/useMCCStore.ts` | Key management fields (Codex) | 0 |
| `client/src/components/mcc/MiniBalance.tsx` | Store import (Codex) | 0 |
