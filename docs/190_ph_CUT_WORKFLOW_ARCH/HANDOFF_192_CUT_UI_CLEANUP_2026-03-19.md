# HANDOFF: CUT UI Cleanup Session — 2026-03-19

## What was done (4 commits, merged to main)

1. **Remove PULSE dropdown from timeline tab bar** (`15d8d3f2`)
   - `AutoMontageMenu` removed from `TimelineTabBar.tsx`
   - Component preserved for future DAG panel integration

2. **Clean timeline toolbar** (`12320347`)
   - Removed: V/C tool buttons, Export button
   - Kept: Snap toggle (magnet SVG), Linked Selection (new chain SVG icon), Zoom slider, Parallel timeline toggle
   - Principle established: "Toolbar controls STATE, not ACTIONS"

3. **Fix track header layout** (`118876c0`)
   - `LANE_HEADER_WIDTH` 76 → 100px
   - Buttons (Target/Lock/Solo/Mute) now 2x2 grid with flexbox centering

4. **Fix recon doc** (`5928c36f6`)
   - Hotkey table corrected from hardcoded V/C/H/Z to preset-aware (Premiere vs FCP7)

## Critical lessons (READ THESE — mistakes I made)

### 1. ALWAYS attach recon_docs and architecture_docs to tasks
I created 6 CUT tasks with EMPTY recon_docs. User caught it. Rule exists in CLAUDE.md, in memory (`feedback_recon_docs_required.md`), and I still violated it. **Every task needs docs. No exceptions. Check before closing task creation.**

### 2. Do NOT improvise hotkey bindings
I hardcoded V/C as Premiere-only buttons in the toolbar. Meanwhile:
- `useCutHotkeys.ts` already has full PREMIERE_PRESET + FCP7_PRESET (40+ bindings each)
- `CUT_UNIFIED_VISION.md §13.3` describes the preset system
- `docs/185_ph_CUT_POLISH/hotcuts/` has complete research on 3 NLEs
- The user is a 20-year professional editor who uses Cmd+K and B (FCP7), not C (Premiere)

**Before implementing ANY hotkey or UI control: check the Action Registry, check hotcuts/ research, check existing code in useCutHotkeys.ts.**

### 3. Grok research is VALUABLE — save it immediately
User relayed Grok's analysis on 3 topics (PULSE placement, Tools panel, Toolbar). I created `RECON_UI_LAYOUT_GROK_2026-03-19.md` with all findings. This doc is now the source of truth for CUT UI decisions. Always create recon docs from research results.

### 4. Check which port/server shows your changes
Worktree dev server runs on port 3003+, main on 3001/3005. User showed screenshot from port 3005 (main) — my worktree changes weren't visible. Don't confuse "code is written" with "user can see it". Merge first or tell user which port to check.

### 5. Close duplicate tasks
I created new tasks (tb_1773906xxx) for work that already had older tasks (tb_1773894xxx). This left orphan pending tasks on the board. Always `action=list filter_status=pending` and check for duplicates BEFORE creating new tasks.

### 6. NEVER create docs in worktree
Recon docs, handoffs, architecture docs — always write to MAIN repo. Worktree docs are invisible to other agents and user. I wrote the recon doc correctly to main, but this rule needs constant awareness.

## User working style

- **Direct and impatient** — doesn't want explanations of things he already knows
- **Professional editor (20 years)** — knows NLE workflows better than any AI. Don't lecture him about Premiere/FCP/Avid
- **Calls out bullshit immediately** — if something looks wrong on screen, he'll screenshot it and ask "what is this mess"
- **Wants research BEFORE code** — send prompts to Grok, get answers, create recon docs, THEN implement
- **Russian language preferred** for conversation
- **Values honesty** — "I don't know" or "I messed up" is better than excuses
- **NEVER use emoji in UI** — white monochrome SVG/PNG only (memory: `feedback_no_emoji_icons.md`)

## Pending CUT tasks (with docs attached)

### P1 — Critical
| Task ID | Title | Docs |
|---------|-------|------|
| tb_1773908571_7 | **Wire useCutHotkeys into CutEditorLayoutV2** | RECON_192, CUT_UNIFIED_VISION, CUT_HOTKEY_ARCH, ACTION_REGISTRY |
| tb_1773894830_8 | **Dual timeline data isolation (W5.2)** | RECON_UI_LAYOUT, CUT_UNIFIED_VISION, CUT_TARGET_ARCH |

### P3 — Next wave
| Task ID | Title | Docs |
|---------|-------|------|
| tb_1773908578_8 | Hotkey preset selector UI (Premiere/FCP7/Custom) | CUT_UNIFIED_VISION, ACTION_REGISTRY, hotcuts/ |
| tb_1773906176_5 | [RESEARCH] Auto Cut context menu in DAG panel | RECON_UI_LAYOUT, CUT_TARGET_ARCH, CUT_UNIFIED_VISION |
| tb_1773906180_6 | [RESEARCH] Dual timeline stacked view | RECON_UI_LAYOUT, CUT_UNIFIED_VISION, CUT_TARGET_ARCH |

### P4
| Task ID | Title |
|---------|-------|
| Crosspost presets | CUT_UNIFIED_VISION attached |

## Key architecture decisions (from this session)

1. **PULSE is NOT a timeline feature** — it's a DAG-level capability. Timeline is a result surface, not a control surface. PULSE will be renamed "Auto Cut" in UI and live in DAG/Graph panel context menu.

2. **Toolbar = state toggles only** — Snap, Linked Selection, Zoom. No actions (Export, Undo), no tools (V/C). Tools are cursor modes via hotkeys.

3. **BPM/Rhythm tracks stay** — user clarified they're markers area, not to be hidden.

4. **Hotkeys are preset-based** — Premiere/FCP7/Avid/Custom. Code exists (`useCutHotkeys.ts`), just not wired to NLE layout.

## Key files to know

| File | What |
|------|------|
| `client/src/hooks/useCutHotkeys.ts` | Full hotkey system with presets — NOT MOUNTED in NLE |
| `client/src/components/cut/TimelineToolbar.tsx` | Cleaned toolbar (Snap/Linked/Zoom/Parallel) |
| `client/src/components/cut/TimelineTabBar.tsx` | Tab bar — PULSE removed |
| `client/src/components/cut/AutoMontageMenu.tsx` | PULSE component — preserved, needs DAG integration |
| `client/src/components/cut/TimelineTrackView.tsx` | Track headers fixed (100px), has TOOL_CURSOR |
| `docs/190_ph_CUT_WORKFLOW_ARCH/RECON_UI_LAYOUT_GROK_2026-03-19.md` | Source of truth for UI decisions |
| `docs/185_ph_CUT_POLISH/hotcuts/` | NLE hotkey research (Premiere PDF, Avid PDF, FCP7 PDF) |
| `docs/185_ph_CUT_POLISH/CUT_NLE_UNIVERSAL_ACTION_REGISTRY.md` | Master list of all NLE actions with multi-NLE hotkeys |

## Ideas noticed during work

1. **TransportBar is dead weight** — it has Undo/Redo, Export, Scene Detection, Zoom slider that duplicate or conflict with TimelineToolbar. Should be deprecated or merged. RECON_192 §1.2 already flags this.

2. **Store has `activeTool` but no UI feedback** — after removing V/C buttons, the only feedback is cursor change. Could add a tiny floating indicator or status bar text showing current tool.

3. **Cmd+K is the most important hotkey** — split at playhead without switching to razor. Every NLE has this. It's in `useCutHotkeys.ts` but dead because the hook isn't mounted. Fix this FIRST.

4. **Dual timeline needs per-tab lanes** — right now both TimelineTrackViews read same global `lanes` from store. Need `timelineTabs[i].lanes` isolation. This is the hardest remaining task.
