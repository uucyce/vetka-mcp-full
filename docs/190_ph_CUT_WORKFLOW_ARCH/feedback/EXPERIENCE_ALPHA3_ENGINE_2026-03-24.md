# EXPERIENCE REPORT: Alpha Engine Session 2026-03-24
**Agent:** Alpha (Engine Architect) | **Branch:** claude/cut-engine
**Duration:** ~4 hours across multiple sub-sessions
**Commits:** 30+ commits, 6 major features, 15+ bug fixes

## Session Achievements

### Commits by Category
- **P0 fixes:** EFFECT_APPLY_MAP build crash, capture:true hotkeys
- **Undo system:** 100% coverage — all editing ops routed through applyTimelineOps
- **3PT editing:** Local-first insert/overwrite with source fallback
- **JKL shuttle:** Duration clamp fix (compute from lanes when duration=0)
- **Multicam:** Full frontend (store + viewer + 1-9 keys + timeline badges + backend creation)
- **FCP7 compliance:** 82 hotkey actions synced, Hand/Zoom tools, deleteMarker, lanePans
- **Component wiring:** TimelineRuler, TrackResizeHandle, ThumbnailStrip verification
- **Recon:** 23-gap audit vs Architecture v1.0

### Key Pattern: Local-First + skipRefresh
Every editing operation follows:
1. Mutate store immediately (setLanes)
2. Send ops to backend async (applyTimelineOps)
3. Pass `{ skipRefresh: true }` to prevent backend from overwriting local state

This solves the mock-backend race condition that broke all e2e tests.

## 6 Debrief Questions

### 1. Most harmful pattern
Spending time verifying "already implemented" instead of finding what's broken.
Multiple times Commander gave tasks that were already done — I should have pivoted
to finding bugs/gaps immediately instead of confirming working state.

### 2. What worked well
The local-first + skipRefresh architecture. One design decision fixed 3PT, split,
JKL, and the entire undo pipeline. This should be the standard pattern.

### 3. Recurring mistake
Manual git commit instead of action=complete in early sessions. CLAUDE.md explicitly
says "action=complete IS your commit" but I kept doing git add && git commit manually.
Cost: extra steps, missed auto-staging, inconsistent closure flow.

### 4. Off-topic idea
applyTimelineOps is essentially a CRDT-compatible op log. The ops are already
structured (move_clip, trim_clip, split_at, etc.). Adding deterministic replay
and conflict resolution would enable collaborative editing (two editors simultaneously)
without merge conflicts. The backend undo stack already stores all ops.

### 5. What I'd do differently
Start every session with: pull main → vite build → fix errors → THEN features.
The EFFECT_APPLY_MAP crash was P0 but I only found it when forced. First 5 minutes
should always be build verification.

### 6. Anti-pattern in process
task_board responses include full docs_content (38K chars of CUT_TARGET_ARCHITECTURE.md)
on every claim/complete call. This eats context window rapidly. Need a skip_docs flag
for operations where docs are already loaded.

## Recommendations for Next Alpha

1. **Build-first:** `cd client && node_modules/.bin/vite build` before any feature work
2. **Local-first pattern:** Always mutate store first, backend second with skipRefresh
3. **82 hotkeys in sync:** After any hotkey change, run the node audit script
4. **Don't touch panels/:** Create components in `client/src/components/cut/`, let Gamma wrap
5. **EFFECT_APPLY_MAP:** If EffectsPanel changes, the inline map in TimelineTrackView needs updating

## Files Touched (Alpha Ownership)
- `client/src/store/useCutEditorStore.ts` — multicam, lanePans, deleteMarker, undo routing
- `client/src/hooks/useCutHotkeys.ts` — 82 actions synced, H/Z/N keys
- `client/src/components/cut/TimelineTrackView.tsx` — TimelineRuler, TrackResizeHandle, shuttle indicator, multicam badges
- `client/src/components/cut/CutEditorLayoutV2.tsx` — local-first split, 3PT, JKL fix, multicam keys
- `client/src/components/cut/MulticamViewer.tsx` — NEW component
- `client/src/components/cut/ClipInspector.tsx` — source_in, effects summary, monochrome
