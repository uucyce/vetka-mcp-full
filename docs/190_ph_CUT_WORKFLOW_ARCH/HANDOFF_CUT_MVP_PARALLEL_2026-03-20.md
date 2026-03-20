# HANDOFF: CUT MVP Parallel Execution
**Date:** 2026-03-20
**From:** Opus Architect-Commander (session `flamboyant-perlman`)
**To:** 4th Opus (Commander) + 3 Opus agents (Streams A/B/C)
**Commit:** `8a5190770`

---

## Situation

CUT NLE needs to become a working app by tomorrow (client demo). One agent can't cover all gaps. Solution: **4 Opus 4.6 agents working in parallel**.

### Your Role Structure

```
                    OPUS-COMMANDER (You, 4th)
                    ┌─────────┐
                    │ Architect│
                    │ Merger   │
                    │ Reviewer │
                    └────┬────┘
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
     OPUS-A          OPUS-B          OPUS-C
  ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ ENGINE   │   │ MEDIA    │   │ UX       │
  │ Wiring   │   │ Codecs   │   │ Dockview │
  │ Editing  │   │ Effects  │   │ Hotkeys  │
  │ Save     │   │ Render   │   │ Multi-TL │
  └──────────┘   └──────────┘   └──────────┘
  worktree:       worktree:       worktree:
  cut-engine      cut-media       cut-ux
```

### Commander Responsibilities
1. **Assign tasks** — each agent claims from task board before coding
2. **Merge worktrees to main** — only Commander merges (via `merge_request` or manual)
3. **Resolve conflicts** — when streams touch shared files
4. **Review quality** — check agent output before merge
5. **Coordinate merge points** — 4 critical gates (see below)
6. **Close tasks to main** — agents close to `done_worktree`, Commander promotes to `done_main`
7. **Collect feedback** — each agent gives doc feedback at phase end

---

## What Was Done (this session)

1. **Full 4-agent recon** completed:
   - Architecture docs audit (Waves W0-W10 status, 37% hotkey coverage)
   - Frontend code state (28 components, 9220 LOC, 70% NLE features done)
   - Backend API audit (54 endpoints, ALL production-ready, ZERO stubs)
   - Dockview branch status (local only, not on main, 3 tasks awaiting merge)

2. **Critical discovery**: App is stronger than expected:
   - ExportDialog already works (3 tabs, real codecs, async render)
   - ProjectSettings already works (framerate, timecode, audio)
   - HistoryPanel already works (undo/redo visualization)
   - AutoMontageMenu exists (3 PULSE modes)
   - Store has 50+ fields including lane mute/solo/lock/target
   - 35 hotkey actions defined (Premiere + FCP7 presets)

3. **ROADMAP_CUT_MVP_PARALLEL.md** created on main — the master plan

4. **28+ CUT tasks** on task board, organized into 3 streams

5. **6 tasks corrected** after recon (downgraded complexity, updated descriptions)

---

## Key File: The Roadmap

```
docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP_CUT_MVP_PARALLEL.md
```

**Every agent MUST read this file first.** It contains:
- Root document table (10 mandatory docs)
- Current state (what works, what doesn't)
- 3 stream definitions with file ownership
- Task tables with dependencies
- Cross-stream dependency graph
- Merge order (4 phases)
- Agent protocol (DNA)

---

## Task Assignment Plan

### OPUS-A (ENGINE stream) — Start with:
```
1. vetka_task_board action=claim task_id=tb_1773981778_2  → CUT-A1: PanelSyncStore bridge
2. vetka_task_board action=claim task_id=tb_1773981786_4  → CUT-A5: Verify hotkeys mounted
   (A1 and A5 are parallel — can do both)
3. After A1 → CUT-A3: Source/Program feed split
4. After A5 → CUT-A8: Split at playhead (⌘K)
```

### OPUS-B (MEDIA stream) — Start with:
```
1. vetka_task_board action=claim task_id=tb_1773981821_8  → CUT-B1: FFprobe codec detection
2. vetka_task_board action=claim task_id=tb_1773981827_9  → CUT-B3: Sequence settings enhance
   (B1 and B3 are parallel)
3. After B1 → CUT-B5: Master render engine (filter_complex)
```

### OPUS-C (UX stream) — Start with:
```
1. vetka_task_board action=claim task_id=tb_1773981871_15 → CUT-C1: Merge dockview branch
2. After C1 → CUT-C3: CutDockviewLayout
3. Parallel: CUT-C8: DAG Y-axis fix (independent)
```

---

## Critical Merge Points

| Gate | Trigger | What Merges | Why |
|------|---------|-------------|-----|
| **MP1** | A1+A2+A5 done | Stream A store changes → main | Foundation for all panels |
| **MP2** | C3 done | Dockview layout → main | New layout replaces V2 |
| **MP3** | B9+A8 done | Effects + editing → main | Effects need working clips |
| **MP4** | A15+B5+B6 done | Save + Render + Export → main | **MVP gate** |

---

## Pending Merges (do these FIRST)

4 tasks with status `done_worktree` awaiting merge to main:

| Task | Branch | Content |
|------|--------|---------|
| CUT-RESEARCH: Panel docking | `claude/relaxed-rosalind` | Dockview research doc |
| CUT-W3.7: Multi-select clips | `claude/relaxed-rosalind` | Cmd+click, Shift+click |
| CUT-W3.4: JKL reverse playback | `claude/relaxed-rosalind` | rAF backward stepping |
| CUT-ARCH: Roadmap gap update | `claude/flamboyant-perlman` | Corrected gaps after recon |

**Commander action:** Merge `claude/relaxed-rosalind` → main first (prerequisite for C1).

---

## Known Blockers

1. **Git push blocked** — `libtorch_cpu.dylib` (204 MB) in `.depth-venv`. Need `git rm --cached` or `.gitignore` update
2. **Dockview not on remote** — `claude/relaxed-rosalind` is local only, push before agents can see it
3. **MCP runs on main** — `vetka_task_board` auto-commit always targets main. Worktree agents MUST pass `branch=claude/<name>` explicitly

---

## Agent Protocol (DNA)

From the roadmap — every agent inherits this:

1. **session_init** first — always
2. **Read ROADMAP_CUT_MVP_PARALLEL.md** — understand the full picture
3. **Claim task** before any code — `vetka_task_board action=claim`
4. **File ownership** — never edit files owned by another stream
5. **Complete to worktree** — `vetka_task_board action=complete branch=claude/<worktree>`
6. **Tests** — if no test exists, create one. Task closure requires passing test
7. **Self-analysis** — before completing, ask: "Do I understand WHY this code exists in the architecture?"
8. **Feedback** — after completing final task of a phase, write doc feedback: observations, ideas, gaps noticed
9. **No raw git commit** — always through task board

---

## Quick Reference

| What | Where |
|------|-------|
| Roadmap | `docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP_CUT_MVP_PARALLEL.md` |
| Architecture | `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_TARGET_ARCHITECTURE.md` |
| Unified Vision | `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_UNIFIED_VISION.md` |
| Hotkey Arch | `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_HOTKEY_ARCHITECTURE.md` |
| RECON delta | `docs/190_ph_CUT_WORKFLOW_ARCH/RECON_192_ARCH_VS_CODE_2026-03-18.md` |
| Multi-timeline | `docs/198_ph_CUT_MULTI_TIMELINE/` |
| PULSE docs | `docs/besedii_google_drive_docs/PULSE-JEPA/` |
| Hotkey refs | `docs/185_ph_CUT_POLISH/hotcuts/` |
| Main store | `client/src/store/useCutEditorStore.ts` |
| Hotkeys hook | `client/src/hooks/useCutHotkeys.ts` |
| Timeline | `client/src/components/cut/TimelineTrackView.tsx` |
| Backend routes | `src/api/routes/cut_routes.py` |

---

**Status: READY TO EXECUTE. All recon done, all tasks created, roadmap on main. Go.**
