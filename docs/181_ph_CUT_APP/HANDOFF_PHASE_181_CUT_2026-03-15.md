# HANDOFF: Phase 181 CUT — Premiere Layout Integration

**Date:** 2026-03-15
**From:** Opus (Claude Code, worktree modest-meitner)
**To:** Next Opus session (fresh chat)
**Branch:** `main` @ `d8451a73a`
**Push:** GitHub up to date

---

## What Was Done This Session

### 1. Merge Integration (codex/cut → main)
- **290 commits** merged from `codex/cut` into `main`
- **7 conflict files** resolved (Opus layout + Codex window polish)
- Large files (>100MB) cleaned from history via `git filter-repo`
- Force pushed to GitHub successfully

### 2. Conflict Resolution Summary

| File | Resolution |
|------|-----------|
| `usePanelLayoutStore.ts` | Opus: full Premiere layout (leftSplit, DockPosition, DEFAULT_PANELS) |
| `PanelGrid.tsx` | Opus base + Codex rightSplit resize handler |
| `PanelShell.tsx` | Codex: compact 20px header, fullscreen/minimize/detach, all-edge resize |
| `CutEditorLayoutV2.tsx` | Opus Premiere structure + Codex dynamic title-context |
| `DAGProjectPanel.tsx` | Opus: xyflow v12 typing fix |
| `PulseInspector.tsx` | Opus: cleanup unused imports |
| `ScriptPanel.tsx` | Opus: cleanup unused imports |

### 3. Task Board Pipeline Fix (task_board_tools.py)
- Reverted broken auto-commit from `complete` action
- **Agreed protocol:** `vetka_task_board complete` → internally calls `vetka_git_commit` → commit + digest + auto-close
- NOT YET IMPLEMENTED — only the rollback is in place. Next session should implement the unified flow.

### 4. CutStandalone Entry Point
- `CutStandalone.tsx` now imports `CutEditorLayoutV2` (confirmed working)

---

## Current State (Screenshot Analysis)

### What Works
- V2 layout renders: left column (Source Monitor + Project), center (Program Monitor), right (Program Monitor + Inspector), bottom (Timeline)
- Compact title bars (20px) with detach/fullscreen/minimize/close buttons
- Project panel shows "0 clips" with drop zone + Import button
- Timeline with transport bar, V1/A1 tracks, zoom slider, PPro export button
- StorySpace 3D mini overlay in bottom-right corner

### What Needs Fixing (User Feedback)

1. **TWO monitors, each with its OWN purpose** (standard NLE since Steenbeck)
   - **Source Monitor** (LEFT) — shows selected clip / DAG artifact preview
   - **Program Monitor** (RIGHT) — shows timeline playback output
   - Currently: left_top says "Program Monitor" (WRONG), right_top is duplicate Program Monitor (WRONG)
   - Fix: Source Monitor left, Program Monitor right, NO center duplicate

2. **Blue toggle buttons on tracks** — "непонятные ярко синие рычажки"
   - S/M buttons (Solo/Mute) on V1 and A1 tracks are too bright blue
   - Should be subtle/muted like Premiere (gray default, colored only when active)

3. **Import flow** — currently just a path input + Import button
   - Should work like Premiere: File > Import, or drag folders/files from Finder
   - Material should also come from DAG (pipeline output → Project panel)

4. **Layout is 3-column but should be 2-column + bottom**
   - Left: Source Monitor (top) + Project Panel (bottom)
   - Right: Program Monitor (top) + Inspector/Script/DAG tabs (bottom)
   - Bottom: Timeline (full width, ~35%)
   - NO center column — two columns only, like Premiere

---

## Architecture Decisions (Confirmed with User)

1. **IKEA-Premiere:** Free windows, not fixed zones. Any panel can dock/tab/float/fullscreen
2. **Import = left, Export = right** (Steenbeck convention since 1970s)
3. **Columns = metadata fields** inside Project panel, NOT layout structure
4. **Project Window = Excel → DAG**: list view with sortable metadata, toggle to DAG node graph
5. **Timeline ~35% screen height**, pinch-to-zoom for track height
6. **`vetka_task_board complete`** is the single entry/exit point for agents (not `vetka_git_commit` directly)

---

## Files to Know

| File | Purpose |
|------|---------|
| `client/src/CutStandalone.tsx` | Entry point — imports CutEditorLayoutV2 |
| `client/src/components/cut/CutEditorLayoutV2.tsx` | Main layout — panel router |
| `client/src/components/cut/PanelGrid.tsx` | CSS Grid: 5-column with left/right splits |
| `client/src/components/cut/PanelShell.tsx` | Panel wrapper: title bar + buttons |
| `client/src/store/usePanelLayoutStore.ts` | Zustand store: panels, grid sizes, dock positions |
| `client/src/store/useCutEditorStore.ts` | Editor state: zoom, scroll, clips, timeline |
| `client/src/components/cut/ProjectPanel.tsx` | Media bin + import (NEW, ~340 lines) |
| `client/src/components/cut/VideoPreview.tsx` | Video player (Source & Program Monitor) |
| `client/src/components/cut/TimelineTrackView.tsx` | Track lanes with S/M buttons |
| `docs/181_ph_CUT_APP/PREMIERE_LAYOUT_ARCHITECTURE.md` | Architecture doc v3 |

---

## Tasks for Next Session

### P0 — Layout Fixes (do first)

**181.8: Fix layout — 2 columns, Source left, Program right**
- Remove center column from PanelGrid (currently 5-column grid → make 3-column: left | resize | right)
- Left column split: Source Monitor (top) + Project Panel (bottom)
- Right column split: Program Monitor (top) + Inspector/Script/DAG tabs (bottom)
- Bottom: Timeline (full width, ~35%)
- Update `usePanelLayoutStore.ts`: remove 'center' from DockPosition, remove center grid column
- Update `CutEditorLayoutV2.tsx`: remove `renderCenter`, remove `renderRightTop`
- Source Monitor = shows selected clip/DAG artifact. Program Monitor = timeline playback.

**181.9: Fix track S/M buttons — mute blue, use Premiere-style gray**
- `TimelineTrackView.tsx` — find Solo/Mute button styles
- Default: gray/transparent. Solo active = yellow. Mute active = red. Not bright blue.

### P1 — Import Flow

**181.10: DAG → Project Panel pipeline**
- When DAG pipeline completes (bootstrap, media scan), results go into Project panel
- `ProjectPanel.tsx` should subscribe to bootstrap job completion
- Auto-populate bins from `/api/cut/bootstrap-async` results

**181.11: Premiere-style Import dialog**
- File > Import menu item (or Cmd+I)
- Native file picker via Tauri `dialog.open()`
- Drag & drop from Finder into Project panel (already partially works)
- Folder import: recursively scan and classify into bins

### P2 — Polish

**181.12: StorySpace 3D positioning**
- Currently overlaps timeline area (bottom-right)
- Should float inside Program Monitor (center panel) as designed

**181.13: Tab switching in right_bottom**
- Inspector / Script / DAG tabs — clicking should switch via `setActiveTab`
- Tab bar UI not visible yet (need tab header row)

**181.14: Task complete → vetka_git_commit unified flow**
- Implement: `vetka_task_board action=complete` internally calls `vetka_git_commit`
- Task only closes if commit succeeds
- Scoped staging (closure_files, not git add -A)

### P3 — Deferred

- Window management: drag to dock/undock (181.3B)
- Keyboard shortcuts (`, ~ for fullscreen panel, Cmd+I for import)
- Layout persistence per project (save/load from layout_state.json)
- Premiere XML export UI (button exists, needs wiring to `/api/cut/export/premiere-xml`)

---

## Codex Status
- **Budget exhausted** ($30 tier) — not available this session
- Codex completed: C-181.4 (codecs), C-181.5 (window polish), C-181.6 (export), C-181.7 (SRT markers)
- Codex clean-room worktree: `vetka_live_03_cleanmerge_tb_1773526327_2` — can be removed

## Worktrees to Clean
- `modest-meitner` — this session's worktree (changes merged to main)
- `vetka_live_03_cleanmerge_tb_1773526327_2` — Codex clean-room (merged)
- Multiple stale branches identified in recon report (see `docs/177_MCC_local/INTEGRATION_RECON_*.md`)
