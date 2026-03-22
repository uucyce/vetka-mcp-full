# HANDOFF: Commander pedantic-bell → Next Commander
**Date:** 2026-03-22
**Session duration:** ~2.5 hours
**Agents:** Alpha + Beta + Gamma + Delta-1 + Delta-2 (5 Opus 4.6 parallel)
**Main HEAD:** d386013f5

---

## FIRST: Read These Before Anything Else

1. `COMMANDER_ROLE_PROMPT.md` — your role, merge ritual, all lessons (v2.0, updated this session)
2. `feedback/FEEDBACK_WAVE5_6_ALL_AGENTS_2026-03-22.md` — consolidated agent insights + priority matrix
3. This file — current state + what's broken + what to do next

---

## What Was Accomplished (Wave 5-6)

### Alpha (Engine) — 12 tasks, 141 tests
- Three-Point Editing (I/O/,) with FCP7-correct mark precedence
- JKL shuttle with rAF loop (reverse/variable speed)
- Match Frame (F key)
- Store Migration Phase 1 (effective* selectors — backward-compatible reads)
- Tool state machine (6 tools, dynamic cursors, toolbar indicator)
- Import media fix (3 bugs: event mismatch, file picker mode, stale projectId)
- Dedicated Tauri CUT config (VETKA CUT, ai.vetka.cut)
- Desktop build verified (APP/DMG)

### Beta (Media) — 13 tasks, 79 tests, 9 new modules
- Color Pipeline v2 COMPLETE:
  - Video Scopes (waveform/parade/vectorscope/histogram) — pure numpy, ~42ms all four
  - 3-Way Color Wheels (ColorWheel.tsx component)
  - LUT Browser (import/preview/delete .cube files)
  - Scope-Preview sync (pre/post grade toggle)
  - Camera Log auto-detect (10 profiles, 3-tier detection)
  - Broadcast Safe (YCbCr clamp, zebra mask, indicator)
- Dockview CSS wildcard fix (nuclear `*` broke Tauri production drag/resize)

### Gamma (UX) — 11 commits
- All 8 menus built out (File/Edit/Mark/Clip/Sequence/View/Window/Help)
- Panel focus scoping (ACTION_SCOPE map, 55+ actions scoped)
- Timecode entry navigation (click-to-edit, SMPTE format, Drop Frame)
- L-cut/J-cut (⌥E/⌥⇧E)
- Speed indicators (green/orange/red on clips)
- Compact track headers (16x14, 1 row of 4 buttons)
- Panel toggle (togglePanel with addPanel fallback)
- Ruler label visibility fix

### Delta-2 (QA) — FCP7 recon + 40 TDD specs
- FCP7 Bible audit Ch.41-115 (40 GAPs identified)
- 26 smoke tests (7 pass, 14 fail, 5 skip)
- 40 TDD specs (RED by design — test-first)
- `__CUT_STORE__` ESM circular dep fix

### Delta-1 (QA) — 41+ tests passing
- Debug shell tests
- Scene graph + export tests
- TransportBar mount in dockview (W5.2)

---

## What's BROKEN (P0 — fix before anything else)

### 1. Duplicate TransportBar (VISIBLE TO USER)
**Task:** `tb_1774137356_10`
**Symptom:** Second transport bar appears at bottom of CUT layout.
**Root causes found:**
- Delta-1 stashed code on main that adds `<TransportBar />` standalone in CutEditorLayoutV2.tsx OUTSIDE dockview. Stash ref: `Delta-1 W5.2 uncommitted (includes TransportBar dupe bug)`. **DO NOT `git stash pop` this.**
- Alpha's dockview dedup guard (MARKER_W6.DEDUP) helps with corrupt localStorage but doesn't fix the standalone mount issue.
- TransportBar.tsx itself is DEAD CODE (0 imports). MonitorTransport (inside Source/Program panels) is the real transport.
**Fix:** Delete TransportBar.tsx. Ensure CutEditorLayoutV2 does NOT mount any transport component. All transport UI lives inside dockview panels only.

### 2. Source = Program Video Feed (NOT VISIBLE BUT CRITICAL)
**Symptom:** Both Source and Program monitors show the same video element. VideoPreview ignores `feed` prop.
**Impact:** Three-Point Edit works but IN/OUT marks go to wrong monitor. Import preview duplicates onto timeline.
**Fix:** Separate video elements for Source (clip preview) and Program (sequence playback). Separate IN/OUT state per monitor.

### 3. Input/Output Logic Confused
**Symptom:** Import media + output controls appear in Source AND duplicate on timeline.
**Correct FCP7 behavior:** Source = preview source clip with source IN/OUT. Program/Timeline = preview sequence with program IN/OUT. Never duplicate.

---

## Task Board State

### Claimed (in progress):
- `tb_1774130920_3` — Delta-1 W5.2 TransportBar mount (COMPLETED but task not promoted)

### Pending (ready for dispatch):
| ID | Title | Priority | Domain |
|----|-------|----------|--------|
| tb_1774137356_10 | TransportBar dupe + Input/Output logic | P0 | Alpha or Gamma |
| tb_1774130923_4 | FCP7 razor split, ⌘K, linked selection | P2 | Alpha |
| tb_1773996025_9 | Audio Mixer | P3 | Beta |
| tb_1773996031_10 | Motion attributes (Drop Shadow, Distort) | P3 | Beta |
| tb_1773996076_15 | Keyframe navigation + timeline graph | P3 | Alpha |
| tb_1773874824_27 | Crosspost presets (YT/IG/TT) | P4 | Beta |

### Recommended next wave (P0-P1 for "usable NLE"):
1. **Alpha:** tb_1774137356_10 (TransportBar dupe + Source/Program separation)
2. **Beta:** WebSocket scopes for live playback (currently HTTP, jerky ~2x/sec)
3. **Gamma:** Kill TransportBar.tsx dead code + CSS isolation for timeline content
4. **Delta:** Continue smoke test analysis, promote passing tests to CI

---

## Stash Warning

There is a git stash on main:
```
Delta-1 W5.2 uncommitted (includes TransportBar dupe bug)
```
Contains: TransportBar standalone mount in CutEditorLayoutV2, DebugStatusText in TransportBar, SceneGraphStatus in GraphPanelDock.

**DO NOT blindly `git stash pop`.** The TransportBar mount is the bug. SceneGraphStatus and DebugStatusText may be useful but need review. Dispatch an agent to cherry-pick only the good parts.

---

## Worktree Status

| Worktree | Branch | Status |
|----------|--------|--------|
| cut-engine | claude/cut-engine | at main (merged) |
| cut-media | claude/cut-media | at main (merged) |
| cut-ux | claude/cut-ux | at main (merged) |
| cut-qa | worktree-cut-qa | Delta-1 may still be working |

Old worktrees (from previous sessions): awesome-lumiere, flamboyant-perlman, inspiring-cohen, peaceful-stonebraker, pensive-jennings, relaxed-rosalind. Can be pruned if disk space needed.

---

## Strategic Context

**User's words:** "мне реально надо монтировать видео, надо немного деньжат заработать"

CUT needs to be a WORKING NLE for paid video editing. The checkpoint:
- Import → Edit (cut, trim, 3-point) → Export as MP4
- Works as desktop APP/DMG (Tauri build verified)
- FCP7 keyboard shortcuts feel right
- DAG/PULSE/Script Spine = AFTER this checkpoint

The ship sails with fair wind. P0-P1 fixes get us to the island. Don't turn toward the open ocean (P3 features) until we've resupplied.

---

## Commander-to-Commander Advice

1. Your first merge will feel scary. Follow the checklist in COMMANDER_ROLE_PROMPT.md §6 step by step.
2. Agents WILL leave uncommitted files on main. Always `git status` first.
3. User will send screenshots — that's your only eyes. Read them carefully. Look for visual bugs the agent doesn't mention.
4. When agents finish a wave, ask for experience reports BEFORE rotating. The insights are irreplaceable.
5. cut_routes.py will conflict on every Beta merge. Don't panic, just combine both sides.
6. Two Deltas = two different terminal tabs. Ask user which is which and WRITE IT DOWN.
7. Don't code. Don't code. Don't code. Even when you see a one-line fix. Delegate.

---

*Fair winds and following seas, Captain.*
