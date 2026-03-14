# Grok Research: Phase 175 — MYCELIUM.app Standalone Tauri App

> **Date:** 2026-03-09 (received 2026-03-11)
> **Researcher:** Grok 4.1 (via user relay)
> **Status:** Complete

---

## Context

**VETKA** — full 3D knowledge graph Tauri app (React + Three.js + FastAPI backend on :5001).
**MCC (Mycelium Command Center)** — embedded React surface for DAG pipelines, TaskBoard, DevPanel, MiniWindows.

**Goal**: Extract MCC into **standalone MYCELIUM.app** (minimal Tauri binary, ~50MB dmg/app).

---

## Q1: Multi-Target Tauri Workspace

| Approach | Recommendation |
|----------|---------------|
| Single src-tauri/ (env-based) | No — pollutes VETKA build |
| **src-tauri + src-tauri-mcc/ (copy)** | **Yes MVP** — copy+paste minimal cmds |
| Cargo Workspace | Phase 175.3 — after MVP |
| Tauri 2.0 native workspace | Future (alpha 2026) |

**MVP**: `mkdir src-tauri-mcc`, copy trimmed `tauri.conf.json` + `main.rs`.

## Q2: Frontend Build Splitting

| Strategy | Bundle | Recommendation |
|----------|--------|---------------|
| **Vite Multi-Page** | 8MB (no Three) | **Best** |
| Single SPA + Route | 20MB (3D leaks) | OK but wasteful |
| Tree-Shaking env flag | -12MB | Combine with multi-page |

Vite config: `rollupOptions.input = { vetka: 'index.html', mycelium: 'mycelium.html' }`

## Q3: Backend Packaging

| Option | Recommendation |
|--------|---------------|
| **External** (`python main.py`) | **MVP** |
| Tauri Sidecar (PyInstaller) | Phase 175.2 |
| MYCELIUM-only binary | Yes — bundle `mycelium.bin` |

## Q4: MultiTask Board Generalization

```
MYCELIUM.app ─ REST /api/taskboard ─→ Adapter Layer ─→ Backend
Adapters: ClaudeMCPAdapter, CursorAdapter, VSCodeAdapter, OpenCodeAdapter
```

## Priority

1. 175.1: Copy src-tauri-mcc/ + multi-page (4h)
2. 175.2: Sidecar + tree-shake (3h)
3. 175.3: Generic TaskBoard + adapters (6h)
4. 175.4: dmg/app + docs (2h)
