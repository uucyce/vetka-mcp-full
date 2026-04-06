# Alpha Session 7 — Engine Import P0 Debug
**Date:** 2026-04-06
**Agent:** Alpha (Opus 4.6, 1M context)
**Branch:** claude/cut-engine + main hotfixes
**Duration:** ~2 hours intensive debug
**Outcome:** Import pipeline NOT fixed. Paused for Gemma local model integration.

---

## Q1: What bugs did you find?

### Layer 1 — Frontend: Tauri dialog (FIXED, commits e82ec2cb + 751218e)
- `openFileDialog` in tauri.ts had no Rust-side `pick_files_native` fallback — invoke command was dead code
- Filter order put "Video" first instead of "All Media" — macOS UTI confusion greyed out files
- `startImport` derived sandbox as `${filePath}/cut_sandbox` — broke for file paths
- **Fix:** Added Rust `pick_files_native` command, reordered filters, fixed sandbox derivation
- **Status:** Dialog now opens correctly and files are selectable

### Layer 2 — Frontend: Store hydration (FIXED, commit c4cb3b26)
- `refreshProjectState()` closure captures `projectId=null` and `sandboxRoot=null` from CutStandalone — silently no-ops on first import
- Fallback fetch in `startImport` calls `setLanes()` but **never calls `setThumbnails()`** — ProjectPanel shows "No clips imported"
- CutStandalone reactive chain (projectState → useEffect → setLanes/setThumbnails) not triggered by direct store mutations
- **Fix:** Added thumbnail hydration from `project-state` response + fallback synthesis from lane clips

### Layer 3 — Backend: Missing imports (FIXED, commit a5a22b00e)
- `_run_cut_bootstrap_job` was moved to `cut_routes_bootstrap.py` (MARKER_B65) but import in `cut_routes_workers.py` was never updated
- `_bootstrap_error` also missing from imports
- Every POST to `/api/cut/bootstrap-async` returned **500 Internal Server Error**
- The backend was completely dead for bootstrap — no import could ever succeed
- **Fix:** Added missing imports to cut_routes_workers.py

### Layer 4 — Circular import (UNSOLVED)
- `cut_routes.py` imports from `cut_routes_workers.py` which imports back from `cut_routes.py`
- At direct import time: `ImportError: cannot import name from partially initialized module`
- At server startup via main.py: may or may not resolve depending on import order
- After adding the missing imports, the circular dependency may have worsened
- **Status:** UNSOLVED — likely the remaining blocker

### Merge regressions found and fixed on main:
- `threePointInsert` undefined crash — `useThreePointEdit()` not destructured (commit 6efafd2a)
- WelcomeScreen gate regression — removed per MARKER_CUT-UX-NOWELCOME (commit d9513fdb)
- 17 duplicate keys in `hotkeyHandlers` useMemo (task created, not fixed)
- `performInsert`/`performOverwrite`/`smoothZoomTo` missing from useMemo deps (task created)
- `SpeedControlModal` Rules of Hooks violation (task created)
- `ProjectPanel` `startImport` forward-reference stale closure (task created)

---

## Q2: What unexpectedly worked?

- **Parallel Sonnet subagent recon** — 4 agents independently traced frontend pipeline, backend endpoints, store refresh, and server routing. All converged on the same diagnosis within 2 minutes. This pattern should be standard for P0 debug.
- **`git show branch:file`** is the only reliable way to verify committed state. Working tree grep lies — the auto-commit `allowed_paths` guard silently excludes files outside the list.
- **Rust `pick_files_native` from `tauri_plugin_dialog::DialogExt`** — works identically to JS bridge but bypasses it entirely. Clean fallback pattern.

---

## Q3: What idea came to mind?

- CutStandalone's reactive chain (projectState → useEffect → setLanes/setThumbnails) is an unnecessary middleman. Direct store mutations bypass it. Should refactor to store-only data flow.
- Pre-merge autotest should run `autoBootstrap.test.ts` to catch NOWELCOME regressions immediately.
- `cut_routes_workers.py` circular import with `cut_routes.py` needs architectural fix — extract shared Pydantic models to `cut_routes_models.py`.
- Drag-and-drop from Finder as third import path — Tauri `onDrop` event gives native file paths directly, no dialog needed.

---

## Q4: What tools/approaches failed?

- **Mock-based testing** (Haiku agents' 3 prior attempts): 15 vitest tests all passed but the real app was broken. Mocks test the interface contract, not the actual runtime behavior.
- **Grep on working tree** to verify committed state: led to false negative on Delta's QA (I dismissed their correct finding because my grep showed the line in working tree, but it wasn't committed).
- **Single-layer debugging**: the bug manifested as "files don't appear" but the root cause was 4 layers deep. Each layer fix revealed the next layer was broken too.
- **Incremental frontend fixes without backend verification**: I spent most of the session fixing frontend code while the backend was returning 500 on every call. Should have curled the API endpoint first.

---

## Q5: What anti-patterns should future agents avoid?

1. **Never trust mock tests for integration bugs.** If the complaint is "it doesn't work in the real app", you must trace the actual runtime path, not write more mocks.
2. **Always curl the backend first** when debugging import/save/load — if the API returns 500, no amount of frontend fixes will help.
3. **Always verify with `git show`, not `grep`** — auto-commit allowed_paths silently drops files.
4. **Check imports after function relocation** — when moving Python functions between modules, the import in the caller module must be updated. This is the #1 cause of 500s after refactoring.
5. **Circular imports are landmines** — `cut_routes.py` ↔ `cut_routes_workers.py` is a ticking bomb. Any new import added to either side can break the other.

---

## Q6: Root cause analysis — Why so many regressions?

### 1. Merge without QA gate on main
The snapshot merge strategy (20 commits at once) from worktree branches brought back removed code (WelcomeScreen, bare `useThreePointEdit()`) because conflict resolution picked the wrong version. **No autotest ran on main after merge.**

### 2. Agent domain isolation prevents integration testing
Alpha owns engine, Gamma owns UX, Beta owns media — but import spans ALL domains (Tauri dialog → ProjectPanel → Zustand store → CutStandalone → backend routes). No single agent sees the full pipeline. **Cross-domain bugs fall through the cracks.**

### 3. Backend Python refactoring without import verification
`_run_cut_bootstrap_job` was moved to `cut_routes_bootstrap.py` in a prior session. The move was committed, but the import in `cut_routes_workers.py` was not updated. **No test verifies that the endpoint actually runs** — only that the route is registered.

### 4. Frontend architecture: CutStandalone middleman
CutStandalone acts as a middleman between the backend and Zustand store. It subscribes to `projectState` (React state) and syncs to the store via useEffect. But `ProjectPanel.startImport` writes directly to the store, bypassing CutStandalone. This creates TWO data paths that can diverge. **The architecture should use store-only flow.**

### 5. Stale closures in Zustand store
`refreshProjectState` is stored in Zustand but captures React local state from CutStandalone. When the store is updated by ProjectPanel, the closure still sees the old values. **Zustand slots should not hold closures over React state.**

### 6. Recommended fixes for the pipeline
- **Post-merge CI:** Run vitest + pytest + curl smoke test on main after every merge
- **Integration test for import:** One test that calls `/api/cut/bootstrap-async` with a real folder, polls the job, checks `project-state` returns clips — no mocks
- **Extract shared models:** Move Pydantic request models to `cut_routes_models.py` to break circular import
- **Eliminate CutStandalone middleman:** All data flows through Zustand store only. No React-state-based closures stored in Zustand.
- **Agent recon before code:** When a P0 comes in, ALWAYS curl the API first. Frontend debug is useless if backend is dead.

---

## Tasks created this session

| Task ID | Title | Priority | Status |
|---|---|---|---|
| tb_1775439405 | Import P0: Rust pick_files_native + filter fix + sandbox path | P1 | done_worktree |
| tb_1775440102 | QA-FIX: register pick_files_native in main.rs | P1 | done_worktree |
| tb_1775441858 | threePointInsert crash — destructure useThreePointEdit | P1 | need_qa |
| tb_1775443171 | WelcomeScreen regression — remove gate | P1 | done_worktree |
| tb_1775443817 | Import pipeline: setThumbnails hydration | P1 | done_worktree |
| tb_1775441870 | 17 duplicate keys in hotkeyHandlers | P2 | pending |
| tb_1775441871 | Missing useMemo deps (stale closures) | P2 | pending |
| tb_1775443824 | refreshProjectState stale closure architecture | P2 | pending |
| tb_1775443830 | scene-assembly failure silently skipped | P2 | pending |
| tb_1775441966 | SpeedControlModal Rules of Hooks | P3 | pending |
| tb_1775441970 | ProjectPanel startImport ordering | P3 | pending |

---

## Commits on main this session

| Hash | Description |
|---|---|
| 6efafd2a | threePointInsert crash fix |
| d9513fdb | WelcomeScreen regression removal |
| c4cb3b26 | Import pipeline thumbnail hydration |
| a5a22b00e | Backend missing imports (_run_cut_bootstrap_job) |

## Commits on claude/cut-engine

| Hash | Description |
|---|---|
| e82ec2cb | Rust pick_files_native + filter reorder + sandbox path |
| 751218e02 | Register pick_files_native in main.rs generate_handler |
