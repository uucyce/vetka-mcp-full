# Phase 134: Tauri DevPanel Window — Cursor Brief
**Date:** 2026-02-10
**Priority:** HIGH — enables floating autonomous monitoring
**Effort:** ~45 min total
**Grok Research:** `docs/132_phTauri Multi-Window/Tauri Multi-Window_GROK.txt`

---

## Context

DevPanel component already exists (`client/src/components/panels/DevPanel.tsx`, 938 lines, 7 tabs).
But it's embedded in the main window. We need it as a **separate always-on-top Tauri window**
so the operator can monitor Dragon/Titan pipelines while working in other apps.

**Tauri v2** is already installed. Plugins: shell, fs, dialog, notification.

---

## C34A: Multi-Window Config (10 min) — P1

**File:** `client/src-tauri/tauri.conf.json`

**What:** Add devpanel window definition.

**Implementation:**
1. Add second window to `windows` array:
```json
{
  "label": "devpanel",
  "title": "VETKA DevPanel",
  "width": 420,
  "height": 650,
  "decorations": true,
  "alwaysOnTop": true,
  "resizable": true,
  "visible": false,
  "url": "/devpanel"
}
```

2. Keep main window unchanged.

**MARKER:** `MARKER_134.C34A`

---

## C34B: Rust Command — open_devpanel (15 min) — P1

**File:** `client/src-tauri/src/main.rs`

**What:** Add Tauri command to open/focus DevPanel window.

**Implementation:**
1. Add command (Tauri v2 API):
```rust
// MARKER_134.C34B: DevPanel window command
#[tauri::command]
async fn open_devpanel(app: tauri::AppHandle) -> Result<(), String> {
    use tauri::Manager;

    if let Some(window) = app.get_webview_window("devpanel") {
        window.show().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
    } else {
        // Window not in config or was closed — recreate
        let _window = tauri::WebviewWindowBuilder::new(
            &app,
            "devpanel",
            tauri::WebviewUrl::App("/devpanel".into()),
        )
        .title("VETKA DevPanel")
        .inner_size(420.0, 650.0)
        .always_on_top(true)
        .build()
        .map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
async fn close_devpanel(app: tauri::AppHandle) -> Result<(), String> {
    use tauri::Manager;
    if let Some(window) = app.get_webview_window("devpanel") {
        window.hide().map_err(|e| e.to_string())?;
    }
    Ok(())
}
```

2. Register in invoke_handler:
```rust
.invoke_handler(tauri::generate_handler![
    // ... existing commands ...
    open_devpanel,
    close_devpanel,
])
```

**MARKER:** `MARKER_134.C34B`

---

## C34C: React Route for DevPanel (15 min) — P1

**File:** `client/src/App.tsx` (or router config)

**What:** Add `/devpanel` route that renders DevPanel in standalone mode.

**Implementation:**
1. Add route in router:
```tsx
// MARKER_134.C34C: Standalone DevPanel route
<Route path="/devpanel" element={<DevPanelStandalone />} />
```

2. Create `DevPanelStandalone.tsx`:
```tsx
// MARKER_134.C34C: Standalone wrapper
import DevPanel from './components/panels/DevPanel';

export default function DevPanelStandalone() {
  return (
    <div className="h-screen w-screen bg-gray-900 overflow-hidden">
      <DevPanel standalone={true} />
    </div>
  );
}
```

3. In existing DevPanel.tsx, accept `standalone` prop:
- If standalone: full height, no collapse button, auto-connect WebSocket
- If embedded (default): current behavior unchanged

**MARKER:** `MARKER_134.C34C`

---

## C34D: Toolbar Toggle Button (5 min) — P2

**File:** Main toolbar/header component

**What:** Add button to open floating DevPanel.

```tsx
import { invoke } from '@tauri-apps/api/core';

<button onClick={() => invoke('open_devpanel')} title="Open DevPanel (floating)">
  🛠️
</button>
```

**MARKER:** `MARKER_134.C34D`

---

## DO NOT TOUCH
- Backend Python code
- docs/ directory
- DevPanel.tsx internal logic (just add `standalone` prop check)
- main.py

## Files to Edit
1. `client/src-tauri/tauri.conf.json` (C34A)
2. `client/src-tauri/src/main.rs` (C34B)
3. `client/src/App.tsx` or router (C34C)
4. New: `client/src/DevPanelStandalone.tsx` (C34C)
5. Toolbar component (C34D)
