# Gamma-10 UX/Panel Architect — Experience Report
**Date:** 2026-03-25
**Agent:** OPUS-GAMMA-10 (claude/cut-ux)
**Session:** 11 commits, 12 tasks processed
**Duration:** Single session ~2.5 hours

---

## Q1: What's broken?

**TaskBoard `action=complete` has `logger` not defined bug.** Auto-commit succeeds but task status update fails with `name 'logger' is not defined`. Happened 3 times during session. Workaround: check `git log -1` to verify commit, then `action=update status=done_worktree` manually. Created task for Zeta.

**MenuBar Add Marker/Add Comment Marker use `document.dispatchEvent(KeyboardEvent)` — fragile.** Depends on panel focus state. Should call store action directly. Needs `addMarker(type, time)` store action from Alpha. Reported in debrief Q1.

**HistoryPanel labels type mismatch.** Backend returns `[{index, label, timestamp}]` but frontend expected `string[]`. Rendered `[object Object]`. Fixed with union type + typeof guard.

**37 `disabled: true` items remain in MenuBar.** Most are Alpha-blocked (need store actions for splitClip, rippleDelete, etc.). 5 have TODO comments. Not bugs but FCP7 compliance gaps.

**Circular symlink in `client/node_modules`** — points to itself. Breaks `npx vite build` in all worktrees. Fixed locally with `rm + npm install`, created Zeta task.

---

## Q2: What unexpectedly worked?

**Sonnet Explore agents — 90% of work at 10% of context.** Used 8+ Sonnet agents this session. Each: read files, grep patterns, return structured reports. Opus never reads large files directly. **Pattern: Opus thinks, Sonnet reads.**

**Verify-before-code saved 50% effort.** ExportDialog SocketIO task (tb_1774410674_1) was already fully implemented — socket.io import, render_progress listener, progress bar + ETA + cancel. Closed without code changes. Gamma-9 pattern confirmed: grep before claim.

**`storeKey` on slider definitions — 1-line wiring.** Extended effects (12 sliders) needed only adding `storeKey: 'gamma'` etc. to CATEGORIES config. The `handleChange`/`getValue` infrastructure was already built to support it by Gamma-6. Zero architecture changes.

**withTestId HOC auto-wraps new panels.** Adding `multicam` to `PANEL_COMPONENTS` automatically gave it `data-testid='cut-panel-multicam'`. Cross-cutting concern solved at registry level.

**Debrief Q1/Q2/Q3 system works.** Every `action=complete` asked 3 targeted questions. Answers flowed into ENGRAM L1 (per Zeta screenshot: 27 learnings from 6 agents). Real bugs surfaced (MenuBar dispatchEvent), useful patterns captured (verify-before-code), ideas recorded (auto-generate EFFECT_APPLY_MAP). The system makes experience reports automatic rather than manual.

---

## Q3: Ideas I didn't have time to implement

**1. Shared CUT timeline socket singleton.**
`getCutTimelineSocket()` — single WebSocket for all CUT panels needing real-time timeline state. HistoryPanel, StatusBar live updates, future timeline sync indicators. Prevents N socket connections per panel mount.

**2. Auto-generate EFFECT_APPLY_MAP from CATEGORIES.**
Iterate sliders with `storeKey`, use `default + delta` as preset value. Would prevent EFFECT_APPLY_MAP and CATEGORIES from diverging. ~20 lines, pre-commit hook viable.

**3. CSS scope linter pre-commit hook.**
Reject any `[data-testid=]` selector in `dockview-cut-theme.css` without `.dockview-theme-dark` prefix. Prevents CSS isolation regression from GAMMA-CSS1.

**4. Keyframe graph editor canvas.**
Mini canvas below each slider showing value curves over clip duration. Click to add control points. FCP7 Keyframe Editor reference (Ch.57). ~200 lines canvas code.

**5. Store field `@owner` JSDoc annotations.**
`useCutEditorStore.ts` = 1400+ lines shared between Alpha/Gamma/Beta. Add `/** @owner Alpha */` on each field. Lint rule: agent can't change field with other agent's `@owner`. Prevents cross-domain store corruption.

---

## Q4: What tools worked well?

1. **Sonnet Explore subagents** — delegated all file reading, grep sweeps, FCP7 compliance audits. 8+ agents, zero context wasted on large file reads. Best ROI tool.

2. **`task_board action=complete` with `closure_files`** — scoped auto-commit. Never ran `git add`/`git commit` manually (except when logger bug hit). Pipeline works.

3. **`npx vite build` from `client/`** — 5-6 seconds, catches every import/type error. Ran after every change. 11/11 commits verified.

4. **Debrief Q1/Q2/Q3 at task closure** — forced structured reflection. Surfaced bugs I would have forgotten, patterns worth standardizing, and ideas for future sessions. Zeta collects these into ENGRAM L1 automatically — learnings persist across sessions.

5. **FCP7 Compliance Matrix as work generator** — scanned for PARTIAL/MISSING items in Gamma's domain, found 11 actionable gaps. Prioritized by test-impact. Systematic approach beats random bug hunting.

---

## Q5: What NOT to repeat

1. **Don't run `npx vite build` from repo root.** "Cannot resolve entry module index.html" — must `cd client` first. Lost 30 seconds twice.

2. **Don't claim without checking `git log -1`.** TaskBoard `action=complete` has a logger bug — commit succeeds but status doesn't update. Always verify commit hash before manual status update.

3. **Don't create Alpha tasks when task already exists.** I created `tb_1774410685_1` (Alpha: extend ClipEffects) then Commander's task `tb_1774410637_1` said I should do it myself. Duplicated effort. Check board before delegating.

4. **Don't fix monochrome "violations" that are intentional.** DAGProjectPanel #5DCAA5 was deliberately exempted by Gamma-MONO2 as Camelot viz color. Delta's task overrode this, but the discussion should happen before code. Color semantics need clear documentation.

5. **Don't forget `useRef` import.** Added WebSocket ref to HistoryPanel but initially missed importing `useRef`. Vite build caught it in 5 seconds, but avoidable.

---

## Q6: Unexpected ideas

**1. "Effect Chain" panel — visual effect stack per clip.**
Current: flat list of effect values in sliders. Proposed: vertical chain like Resolve's Node Editor but simpler — each effect is a box, drag to reorder, toggle on/off. FFmpeg filter_complex already operates as a chain. UI would mirror the render pipeline. No other web-based NLE does this.

**2. Workspace preset auto-save on quit.**
Dockview supports `api.toJSON()` serialize. On `beforeunload` → save current layout as "custom" preset in localStorage. On next load → restore. Premiere Pro does this. ~30 lines.

**3. Panel focus breadcrumb in StatusBar.**
Show `Timeline > V1 > Clip "interview_03"` in StatusBar when navigating. Helps editor know which context they're in. Read from `focusedPanel` + `selectedClipId` + `selectedTrackId`.

**4. "Conforming panel" — timeline diff between two cuts.**
Gamma-9 also proposed this. Two timelines stacked, matching clips grey, differences highlighted. Git diff for video. No NLE does this. DAG-native feature — CUT has multiple timeline projections already.

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Commits | 11 |
| Tasks claimed | 12 |
| Tasks completed (code) | 9 |
| Tasks verified (already done) | 2 (ExportDialog SocketIO, workspace presets audit) |
| New files created | 1 (MulticamPanel.tsx) |
| Files modified | 9 (DockviewLayout, presetBuilders, panels/index, StatusBar, HistoryPanel, EffectsPanel, MenuBar, DAGProjectPanel, Panel) |
| Files deleted | 1 (WorkspacePresets.tsx) |
| ClipEffects fields added | 12 (5→17 total) |
| Disabled MenuBar items enabled | 4 (⌘T video/audio transition, Solo, About CUT) |
| Monochrome fixes | 3 (#5DCAA5→#999, #94a3b8→#888, #3b82f6→#555) |
| Dead code removed | 3 items (SpeedControl lazy, unused type imports, WorkspacePresets.tsx) |
| Build verifications | 11 (one per commit, all GREEN) |
| Sonnet subagents used | 8+ |
| Tasks created for other agents | 5 (Alpha ClipEffects, Delta fixme tests, Zeta symlink, Zeta logger, Alpha mark handlers) |
| Debrief Q1/Q2/Q3 answers given | 9 (one per completed task → ENGRAM L1 pipeline) |

---

## Debrief System Assessment

The Q1/Q2/Q3 system at task closure is a significant improvement over Gamma-9's manual experience report:

- **Q1 (bugs)** caught the MenuBar `dispatchEvent` pattern that I would have filed and forgotten. Now it's in ENGRAM L1 for any future agent touching MenuBar.
- **Q2 (worked)** captured the `storeKey` wiring pattern, verify-before-code discipline, and Sonnet delegation strategy. These are now retrievable patterns.
- **Q3 (ideas)** generated 9 architecture ideas across the session — auto-EFFECT_APPLY_MAP, CSS linter, shared socket singleton, keyframe editor. These survive session boundaries.

The pipeline (debrief → Resource Learnings → ENGRAM L1 → CORTEX) means I don't need to remember everything — the system remembers for Gamma-11.

**One concern:** The Q1/Q2/Q3 format works best when the task is substantial. For trivial tasks (1-line monochrome fix), the 3 questions feel heavy. Consider: skip debrief for tasks under `complexity: low` with < 3 files changed.

---

*"Opus thinks, Sonnet reads. 50% of tasks are already done. The other 50% are FCP7 compliance gaps."*
