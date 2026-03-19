# HANDOFF: CUT Tools MVP + Panel Docking Research — 2026-03-19

## What was done

### 1. CUT-TOOLS MVP (committed on worktree `claude/awesome-lumiere`, hash `1fba22ff`)

**4 trim tools implemented:**
- **Selection** (V/A) — arrow, move clips, trim edges
- **Ripple Edit** (B/R) — drag edit point, subsequent clips shift
- **Rolling Edit** (N/Shift+R) — drag edit point, adjacent clip adjusts inversely
- **Razor** (C/B) — click to cut clip

**Removed:** hand tool (useless), zoom tool (useless — slider + hotkeys exist)

**Files changed:**
| File | Change |
|------|--------|
| `useCutEditorStore.ts` | `activeTool: 'selection' \| 'ripple' \| 'rolling' \| 'razor'` |
| `TimelineTabBar.tsx` | Merged tool selector + snap/linked/zoom into tab bar row (killed separate TimelineToolbar row, saved 24px) |
| `TimelineTrackView.tsx` | Custom SVG cursors per tool, ripple/rolling edit logic in mouseUp |
| `useCutHotkeys.ts` | `rippleTool` + `rollingTool` added to Premiere + FCP7 presets |
| `CutEditorLayoutV2.tsx` | Removed TimelineToolbar import/render |

**TimelineToolbar.tsx** still exists (not deleted) but is no longer mounted. Can be deleted later.

### 2. Panel Docking Research (committed on main, hash `087971938`)

**RECON doc:** `docs/190_ph_CUT_WORKFLOW_ARCH/RECON_PANEL_DOCKING_2026-03-19.md`
**Status:** APPROVED

**Decision:** Use **dockview** library for Premiere-style panel docking.
- Zero deps, React 18+, Tauri-compatible
- 5-zone drop targets (top/bottom/left/right/center-tab)
- Floating panels, layout serialization, workspace presets

## Pending CUT tasks (priority order)

### DOCK migration (sequential, each depends on previous)
| Task ID | Title | P | Phase |
|---------|-------|---|-------|
| tb_1773912387_4 | **DOCK-1:** Install dockview + create DockviewLayout wrapper | P1 | build |
| tb_1773912399_5 | **DOCK-2:** Replace PanelGrid with dockview (the big switch) | P1 | build |
| tb_1773912410_6 | **DOCK-3:** Dark theme + panel styling | P2 | build |
| tb_1773912423_7 | **DOCK-4:** Workspace presets (Editing/Color/Audio) | P3 | build |

### Other CUT tasks
| Task ID | Title | P | Notes |
|---------|-------|---|-------|
| tb_1773908571_7 | Wire useCutHotkeys into CutEditorLayoutV2 | P1 | Hotkeys dead — hook exists but not mounted |
| tb_1773894830_8 | Dual timeline data isolation (W5.2) | P2 | Subsumes into DOCK-2 |
| tb_1773908578_8 | Hotkey preset selector UI | P3 | After hotkeys work |
| tb_1773909633_1 | Slip/Slide tools (second wave) | P3 | After MVP tools proven |
| tb_1773874824_27 | Crosspost presets | P4 | Backend ready, frontend only |

### Worktree merge queue
| Task ID | Title | Branch |
|---------|-------|--------|
| tb_1773893336_2 | CUT-W3.7: Multi-select clips | (older worktree) |
| tb_1773893341_3 | CUT-W3.4: JKL reverse playback | (older worktree) |
| tb_1773909650_2 | CUT-TOOLS MVP (this session) | claude/awesome-lumiere |
| tb_1773911196_3 | Panel docking research (this session) | claude/awesome-lumiere |

## Critical lessons from this session

### 1. ALWAYS edit worktree files, not main repo
My first edits went to `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/...` instead of `.../.claude/worktrees/awesome-lumiere/client/...`. Had to copy files and revert main. **Always use full worktree paths.**

### 2. Don't close tasks you didn't verify
I closed 3 research tasks assuming they were done based on similar commit titles. User caught it — the tasks had different IDs and weren't actually completed. **Always verify task content before closing.**

### 3. Tool decisions from a 20-year editor
- Hand tool → useless, mouse does everything with Selection tool
- Zoom tool → useless, slider + hotkeys
- crosshair cursor → wrong for razor, needs blade SVG cursor
- What matters: **Ripple/Rolling edit tools** — the actual trim tools that make a real NLE

### 4. UI space is sacred
Separate toolbar row (24px) was too fat. Merged everything into tab bar. One row = tabs + tools + toggles + zoom.

### 5. Panel docking > dual timeline
The "dual timeline" task was actually about the whole panel docking system. Real problem: all windows should be movable/dockable/tabbable like Premiere. Timeline just happens to be multi-instance.

## Key files

| File | Location | What |
|------|----------|------|
| RECON Panel Docking | `docs/190_ph_CUT_WORKFLOW_ARCH/RECON_PANEL_DOCKING_2026-03-19.md` | Library comparison, migration plan |
| RECON UI Layout | `docs/190_ph_CUT_WORKFLOW_ARCH/RECON_UI_LAYOUT_GROK_2026-03-19.md` | UI decisions (tools, toolbar, PULSE) |
| CUT Unified Vision | `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_UNIFIED_VISION.md` | Master spec for all CUT panels |
| Action Registry | `docs/185_ph_CUT_POLISH/CUT_NLE_UNIVERSAL_ACTION_REGISTRY.md` | 115 NLE actions with multi-preset hotkeys |
| Previous HANDOFF | `docs/190_ph_CUT_WORKFLOW_ARCH/HANDOFF_192_CUT_UI_CLEANUP_2026-03-19.md` | Lessons from UI cleanup session |

## Recommended next action

**Start with DOCK-1** (install dockview + wrapper). This is the foundation for everything else. Hotkey wiring (tb_1773908571_7) can happen in parallel since it doesn't depend on layout system.
