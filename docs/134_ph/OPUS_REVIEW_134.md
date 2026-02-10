# Opus Review: Phase 134 Architecture
**Date:** 2026-02-10
**Verdict:** ✅ APPROVED with 4 MANDATORY corrections below

---

## ✅ APPROVED — Cursor, GO IMPLEMENT

Architecture is solid. Playground isolation is the right approach.
Apply these corrections during implementation:

---

## 🔴 CORRECTION 1: No Router — Use pathname check, not react-router

App has NO react-router-dom. It's pure single-page useState-driven.
**DO NOT install react-router.**

Instead, in `client/src/main.tsx`, check pathname:

```tsx
// main.tsx — MARKER_134.FIX_ROUTER
import App from './App'
import MyceliumStandalone from './MyceliumStandalone'

const pathname = window.location.pathname

function Root() {
  if (pathname === '/mycelium') {
    return <MyceliumStandalone />
  }
  return <App />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>
)
```

This way Tauri opens `/mycelium` in second window → renders MyceliumStandalone.
Main window opens `/` → renders App as before.
**No router needed. Zero breaking changes.**

---

## 🔴 CORRECTION 2: Install missing dependencies FIRST

Before starting any chart work:

```bash
cd client
npm install recharts react-window @types/react-window
```

Add to C34E task (before charts).

---

## 🔴 CORRECTION 3: Create components/dev/ directory

```bash
mkdir -p client/src/components/dev/charts
```

Already implied in architecture but not called out as explicit step.

---

## 🔴 CORRECTION 4: Execution order — C33E FIRST, then MCC

Current heartbeat burns tokens every 60 seconds because settings don't persist.
**C33E (heartbeat persist to disk)** must be done BEFORE MCC work.

Revised order:
```
Hour 1: C33E (heartbeat persist) ← STOPS TOKEN BURN
Hour 2: C33F (stale task cleanup)
Hour 3: C33G (UX fixes — toggles right-aligned)
Hour 4: C34A-D (Tauri multi-window foundation)
Day 2+: C34E onwards (MCC core)
```

C33E brief is in: `docs/133_ph/CURSOR_BRIEF_133B_DEVPANEL_FIXES.md`

---

## Additional Notes for Cursor

### useMyceliumSocket already exists
- Path: `client/src/hooks/useMyceliumSocket.ts`
- Returns: `{ connected: boolean }`
- Dispatches: `pipeline-activity`, `task-board-updated`, `pipeline-stats`, `pipeline-complete`, `pipeline-failed`
- **Reuse it, don't recreate**

### Existing panels to lazy-load
- `client/src/components/panels/DevPanel.tsx` (938 lines)
- `client/src/components/panels/PipelineStats.tsx` (~270 lines)
- `client/src/components/panels/ActivityLog.tsx` (~630 lines)
- `client/src/components/artifact/ArtifactViewer.tsx` (~390 lines)
- All are functional and production-ready

### State management
- App uses **Zustand** (useStore.ts)
- Socket.io client available
- React 19.0.0, Vite, TypeScript 5.4

---

## Summary

| Item | Status |
|------|--------|
| Architecture | ✅ Approved |
| 8 tabs design | ✅ Good |
| Playground isolation | ✅ Excellent idea |
| Router approach | 🔴 Fix: pathname check in main.tsx |
| Dependencies | 🔴 Fix: install recharts, react-window |
| Directory structure | 🔴 Fix: create components/dev/ |
| Execution order | 🔴 Fix: C33E first, then MCC |

**Cursor: read this file + `CURSOR_BRIEF_133B_DEVPANEL_FIXES.md`, then proceed.**
