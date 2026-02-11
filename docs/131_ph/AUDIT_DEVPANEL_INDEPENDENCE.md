# Audit Report: DevPanel Window Independence

**Date:** 2026-02-10
**Phase:** 131
**Status:** AUDIT_COMPLETE
**Auditor:** Claude Opus

## Executive Summary

DevPanel currently lives inside the VETKA Tauri application as a React component. This creates a dependency: if VETKA isn't running, DevPanel is inaccessible. This audit explores options to make DevPanel an independent window/application for continuous Mycelium monitoring.

---

## Current Architecture Analysis

### MARKER_AUDIT_A1: Component Location

```
client/src/
├── App.tsx                    # DevPanel mounted here (line 520-522)
├── components/panels/
│   ├── DevPanel.tsx          # Main component (870+ lines)
│   ├── TaskCard.tsx          # Task display
│   ├── PipelineStats.tsx     # Statistics
│   ├── BalancesPanel.tsx     # API key usage
│   ├── ActivityLog.tsx       # Real-time logs
│   ├── WatcherStats.tsx      # File watcher
│   ├── ArtifactViewer.tsx    # Approval UI
│   ├── AgentStatusBar.tsx    # Active agents
│   └── LeagueTester.tsx      # Pipeline test
└── hooks/
    └── useMyceliumSocket.ts  # WebSocket connection
```

### MARKER_AUDIT_A2: Backend Connections

DevPanel connects to **two** backend services:

| Service | Endpoint | Protocol | Purpose |
|---------|----------|----------|---------|
| VETKA MCP | `http://localhost:5001/api/*` | REST | Task board, heartbeat, approvals |
| Mycelium WS | `ws://localhost:8082` | WebSocket | Pipeline events in real-time |

**Key finding:** Both connections are **direct** — no dependency on VETKA frontend routing.

### MARKER_AUDIT_A3: Store Dependencies

DevPanel uses minimal Zustand store state:

```typescript
// From DevPanel.tsx lines 113-114
const selectedKey = useStore((s) => s.selectedKey);      // API key selection
const clearSelectedKey = useStore((s) => s.clearSelectedKey);

// From lines 806-838
useStore.getState().persistPositions     // 3D position toggle
useStore.getState().setPersistPositions
useStore.getState().resetLayout
```

**Critical:** These are **convenience features**, not core functionality. DevPanel can work without them.

### MARKER_AUDIT_A4: Event System

DevPanel listens to CustomEvents dispatched by `useMyceliumSocket.ts`:

```typescript
window.dispatchEvent(new CustomEvent('pipeline-activity', { detail: data }));
window.dispatchEvent(new CustomEvent('task-board-updated', { detail: data }));
window.dispatchEvent(new CustomEvent('pipeline-stats', { detail: data }));
```

**Note:** These are `window` events — work in any window context.

---

## Independence Options

### Option A: Tauri Multi-Window (Recommended)

**Complexity:** Medium
**Independence:** Partial (still requires Tauri runtime)

Add second window in `tauri.conf.json`:

```json
{
  "app": {
    "windows": [
      { "label": "main", "title": "VETKA - 3D Knowledge Graph", ... },
      {
        "label": "devpanel",
        "title": "VETKA DevPanel",
        "width": 800,
        "height": 700,
        "url": "/devpanel.html",
        "visible": false,
        "alwaysOnTop": false
      }
    ]
  }
}
```

**Pros:**
- Native window with independent lifecycle
- Can open DevPanel without full VETKA
- Shared Tauri plugins (fs, notifications)

**Cons:**
- Still requires Tauri app to be running
- Need separate entry point (`devpanel.html` + `DevPanelApp.tsx`)
- Build complexity increases

### Option B: Vite Multi-Entry Build

**Complexity:** Low-Medium
**Independence:** High (web-based)

Create separate entry point:

```
client/
├── src/
│   ├── main.tsx           # VETKA main entry
│   └── devpanel-main.tsx  # DevPanel standalone entry
└── vite.config.ts         # Multi-entry build
```

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        devpanel: resolve(__dirname, 'devpanel.html'),
      }
    }
  }
});
```

**Pros:**
- Run DevPanel in browser at `http://localhost:3001/devpanel.html`
- Full independence from Tauri
- Simple to implement

**Cons:**
- No native features (notifications, always-on-top)
- Separate browser window needed

### Option C: Standalone Electron App

**Complexity:** High
**Independence:** Full

Create separate `devpanel-electron/` project:

```
devpanel-electron/
├── main.js          # Electron main process
├── package.json
└── src/
    └── (copy DevPanel components)
```

**Pros:**
- Full independence
- Native window management
- Can run without VETKA at all

**Cons:**
- Code duplication
- Separate maintenance
- Electron overhead

### Option D: Web-Only (Simple Browser Tab)

**Complexity:** Low
**Independence:** Full

Just add a route `/devpanel` to existing Vite dev server:

```typescript
// App.tsx or router
<Route path="/devpanel" element={<DevPanelStandalone />} />
```

Open in browser: `http://localhost:3001/devpanel`

**Pros:**
- Zero additional setup
- Works now
- Bookmark in browser

**Cons:**
- No native window features
- Must keep browser tab open

---

## Recommendation

### Phase 1: Web-Only (Immediate)
Add `/devpanel` route. Open in browser for monitoring when VETKA is closed.
**Effort:** 1 hour

### Phase 2: Vite Multi-Entry (Short-term)
Create `devpanel.html` entry for clean standalone build.
**Effort:** 2-3 hours

### Phase 3: Tauri Multi-Window (Future)
When we need native features (notifications, always-on-top for monitoring).
**Effort:** 1 day

---

## Implementation Checklist

### For Option D (Web-Only):

- [ ] Create `DevPanelStandalone.tsx` wrapper
- [ ] Add route in App.tsx or create router
- [ ] Remove store dependencies (or provide local fallbacks)
- [ ] Test at `http://localhost:3001/devpanel`

### For Option B (Vite Multi-Entry):

- [ ] Create `devpanel.html` in `client/`
- [ ] Create `devpanel-main.tsx` entry point
- [ ] Update `vite.config.ts` for multi-entry
- [ ] Create `DevPanelApp.tsx` standalone wrapper
- [ ] Build and test

### Store State Fallbacks Needed:

```typescript
// devpanel-main.tsx
// Provide minimal store or fallback values
const selectedKey = null;  // No key selection in standalone
const persistPositions = false;  // Irrelevant without 3D tree
```

---

## Files Modified (None Yet)

This is an audit only. Implementation requires separate phase.

---

## Related Files Reference

| File | Role | Lines |
|------|------|-------|
| `client/src/App.tsx` | DevPanel mount | 520-522 |
| `client/src/components/panels/DevPanel.tsx` | Main component | 870+ |
| `client/src/hooks/useMyceliumSocket.ts` | WS connection | 154 |
| `client/src/store/useStore.ts` | Store deps | 179, 187-189 |
| `client/src-tauri/tauri.conf.json` | Window config | 14-27 |
| `client/src-tauri/src/main.rs` | Tauri setup | 83 |

---

## Conclusion

DevPanel is **architecturally ready** for independence. The only blockers are:
1. Mounted inside App.tsx (easy to separate)
2. Minor store dependencies (easy to mock)
3. No separate entry point (easy to add)

**Recommended path:** Start with Option D (web route), evolve to Option B (multi-entry) when needed.
