# PHASE 170 CUT Video Editing — Checkpoint 2026-03-13

**Phase Status:** 170 (CUT Video Editing Mode)
**Current Date:** 2026-03-13
**Branch:** `codex/cut` (commit: acf6881b5)
**Digest Phase:** 171 (will update after Opus 4.6 completes 170.8)

---

## 📊 Wave Summary

### ✅ COMPLETED WAVES

| Wave | Focus | Status | Tests | Markers |
|------|-------|--------|-------|---------|
| 1–4 | Bootstrap + scene graph architecture | ✅ DONE | 12 passing | MARKER_170.1–170.4 |
| 5–6 | DAG viewport + cross-highlighting | ✅ DONE | 6 passing | MARKER_170.5–170.6 |
| 7 | Node-click stabilization (248) | ✅ DONE | 4 passing | MARKER_170.7–170.NODE_CLICK |

### 🔄 IN PROGRESS WAVES

| Wave | Focus | Owner | ETA | Markers |
|------|-------|-------|-----|---------|
| **170.8** | Music-sync → markers integration | **Opus 4.6** | 05:42 UTC | MARKER_170.8.* |

### ⏳ PENDING WAVES

| Wave | Focus | Estimate | Blocker | Notes |
|------|-------|----------|---------|-------|
| 170.9 | Pure DOM click actionability in DAG | TBD | Non-critical | UI-surface fix, separate from focus pipeline |
| 170.10 | Scene Graph performance optimization | TBD | User feedback | LOD clustering for large graphs |
| 170.11 | Project state → persistent marker storage | TBD | 170.8 complete | Store markers in project.json |

---

## 🎯 What 170.8 Unlocks

After Opus 4.6 completes music-sync integration (by 05:42 UTC):

1. ✅ **Music track markers visible in Scene Graph** — colored by sync method
2. ✅ **TimeMarkerBundle contract frozen** — ready for future workers
3. ✅ **Berlin fixture acceptance proof** — marker rendering on live fixture
4. ✅ **Hybrid merge rules tested** — transcript + energy slices merged correctly

**Blocks:** 170.11 (persistent storage) and any future music-automation layers

---

## 📁 Core Deliverables by Wave

### Wave 1–4: Bootstrap + Architecture (DONE)
Files created:
- `src/api/routes/cut_routes.py` (19 endpoints, 20 JSON schemas)
- `src/services/cut/` worker suite (audio_sync, pause_slice, thumbnail, transcript, waveform, etc.)
- `client/src/components/cut/CutStandalone.tsx` (main container)
- `client/src/components/cut/SceneGraph.tsx` (DAG visualization)
- Tests: `tests/phase170/test_cut_bootstrap_*.py` (12 passing)

### Wave 5–6: Viewport + Cross-Highlighting (DONE)
Files:
- `client/src/components/cut/SceneGraphViewport.tsx`
- Cross-highlighting via `_onNodeHover`, `_onEdgeHover`
- Tests: `test_cut_scene_graph_apply_api.py`, `test_cut_scene_assembly_async_api.py` (6 passing)

### Wave 7: Node-Click Stabilization (DONE)
Files:
- Test hooks: `data-testid="dag-node-label"` in TaskNode + RoadmapTaskNode
- Smoke spec: `client/e2e/cut_scene_graph_node_click_smoke.spec.cjs` (1 passing)
- Test hook: `window.__VETKA_CUT_TEST__.triggerSceneGraphFocus()` in CutStandalone:666
- Tests: `test_cut_standalone_shell_contract.py` (4 passing, 1 warning)

### Wave 170.8: Music-Sync → Markers (IN PROGRESS)
Files to create:
- `src/services/cut/marker_bundle_service.py` — merge slices + sync → TimeMarkerBundle
- `client/src/components/cut/nodes/MarkerNode.tsx` — marker node renderer
- `tests/phase170/test_cut_music_marker_bundle_creation.py` — backend contract test
- `client/e2e/cut_berlin_music_markers_smoke.spec.cjs` — E2E acceptance test
- Schemas: `TimeMarkerBundle`, `TimeMarker`, `SyncStatus` in `src/schemas/cut_schemas.py`

---

## 🧪 Test Coverage by Domain

### Backend (pytest)
```
tests/phase170/
├── test_cut_bootstrap_api.py                     ✓ passing
├── test_cut_bootstrap_async_api.py               ✓ passing
├── test_cut_contract_schemas.py                  ✓ passing
├── test_cut_audio_slice_sync_bakeoff.py          ✓ passing (reference evals)
├── test_cut_audio_sync_worker_api.py             ✓ passing
├── test_cut_pause_slice_worker_api.py            ✓ passing
├── test_cut_scene_graph_apply_api.py             ✓ passing
├── test_cut_scene_assembly_async_api.py          ✓ passing
├── test_cut_standalone_shell_contract.py         ✓ passing (4/5, 1 warning)
├── test_cut_timeline_apply_api.py                ✓ passing
├── test_cut_project_state_api.py                 ✓ passing
├── test_cut_thumbnail_worker_api.py              ✓ passing
├── test_cut_time_marker_api.py                   ✓ passing
├── test_cut_transcript_worker_api.py             ✓ passing
├── test_cut_waveform_worker_api.py               ✓ passing
├── test_cut_timecode_sync_worker_api.py          ✓ passing
├── test_cut_job_control_api.py                   ✓ passing
├── test_cut_project_store.py                     ✓ passing
└── test_cut_music_marker_bundle_creation.py      (NEW — 170.8)
```

### Frontend (Playwright E2E)
```
client/e2e/
├── cut_scene_graph_node_click_smoke.spec.cjs     ✓ passing (1)
├── cut_berlin_fixture_smoke.spec.cjs             ✓ passing (fixture hydration)
├── cut_berlin_music_acceptance.spec.cjs          ✓ passing (music track visibility)
└── cut_berlin_music_markers_smoke.spec.cjs       (NEW — 170.8)
```

---

## 🌲 Current Architecture

### Backend Stack
```
FastAPI + SocketIO (port 5001)
├─ /api/cut/bootstrap         → load fixture + project state
├─ /api/cut/timeline/apply    → apply edits to timeline
├─ /api/cut/timeline/apply-with-markers  ← NEW (170.8)
├─ Workers:
│  ├─ audio_sync_v1           (peaks + correlation, offset detection)
│  ├─ energy_pause_v1         (pydub silence detection)
│  ├─ transcript_pause_v1     (pause windows from transcript)
│  ├─ thumbnail_worker        (frame extraction)
│  ├─ transcript_worker       (speech-to-text)
│  └─ waveform_worker         (audio analysis)
└─ Project state store        (JSON-based, reloadable)
```

### Frontend Stack
```
React + Three.js + ReactFlow
├─ CutStandalone (main container)
├─ SceneGraph (DAG visualization via xyflow)
│  ├─ Nodes: Video, Audio, Music, Timeline, Marker ← NEW (170.8)
│  └─ Edges: sync, dependency, crosshighlight
├─ SceneGraphViewport (canvas rendering)
├─ SourceBrowser (media asset selector)
├─ Inspector (node details)
└─ Timeline (linear editing view)
```

---

## 📊 Berlin Fixture (Live Acceptance)

**Location:** `client/e2e/fixtures/cut_berlin_fixture_state.json`
**Sandbox:** `codex54_cut_fixture_sandbox` @ port 3211
**Assets:**
- Video clips: 3x (various durations)
- Music track: "Punch" (Primary Music) — 2:15 duration
- Transcripts: English speech
- Hydration state: Persists across reloads

**Current coverage:**
- ✓ Fixture loads without errors
- ✓ Source browser hydrates media buckets (Video Clips, Music Track, Audio Assets)
- ✓ Music track appears with Primary Music + Audio sync lane badges
- ✓ Music track persists after reload
- ⏳ **Markers not yet visible** ← 170.8 will fix this

---

## 🚀 Path to Phase 171

**Gate:** Opus 4.6 completes 170.8 by 05:42 UTC

**After 170.8 passes:**
1. Merge `codex/cut` → `main` (or create PR for Opus review)
2. Update digest: Phase 170 → COMPLETE, Phase 171 → active
3. Lock 170 wave docs: mark as archive
4. Start 171: either pure DOM click fix OR new CUT features

**Next features queued:**
- Project state persistence (save/load markers)
- Rhythm-aware editing (beat-snapping markers)
- Multi-track sync (A/B camera alignment)

---

## 📋 Outstanding Issues (Non-Blocking)

| Issue | Severity | Blocker | Notes |
|-------|----------|---------|-------|
| Pure DOM click in DAG canvas (Playwright actionability) | Low | No | Separate from focus pipeline — 248 proved handler works via test hook |
| App packaging (TypeScript failures) | Medium | No | Outside CUT scope |
| Qdrant persistence (vector search fallback) | Low | No | Phase 152+ scope |

---

## ✅ Success Criteria for 170.8

- [ ] TimeMarkerBundle schema defined and compiles
- [ ] `/api/cut/timeline/apply-with-markers` endpoint returns valid bundle
- [ ] `test_cut_music_marker_bundle_creation.py` passing (4/4)
- [ ] MarkerNode renders in Scene Graph (colored by source: transcript/energy/hybrid)
- [ ] Music badge shows in CutEditorLayout (marker count + sync confidence %)
- [ ] `cut_berlin_music_markers_smoke.spec.cjs` passing (Berlin fixture acceptance)
- [ ] Full test suite `pytest tests/phase170/ -q` shows no new failures
- [ ] Commit: `phase170.8: Music-sync → markers integration`

---

## 📌 Handoff Documents

Created for Opus 4.6:
1. **`HANDOFF_PHASE_170_MUSIC_SYNC_MARKERS_2026-03-13.md`** — detailed scope + contracts + implementation
2. **`OPUS_QUICK_START_PHASE_170_8_2026-03-13.md`** — 4-task execution timeline (30m + 60m + 60m + 20m)
3. **`PHASE_170_CHECKPOINT_2026-03-13.md`** — this file, for record-keeping

---

## 🎯 Metrics & Observations

**Code volume by domain:**
- Backend routes + schemas: ~800 lines
- Worker services: ~1200 lines
- Frontend components: ~900 lines
- Tests: ~2400 lines (18 test modules)
- **Total Phase 170 code:** ~5300 lines

**Test density:** ~0.45 lines of test per line of code (good coverage)

**Architecture decision:** Contract-first pattern accelerated 170.7–170.8 transition (minimal rework)

---

## 🔮 Future Roadmap (Post 170.8)

**170.9:** Pure DOM click actionability fix (requires specialized Playwright debugging)
**170.10:** Scene Graph performance for large DAGs (LOD clustering, viewport culling)
**170.11:** Persistent marker storage in project.json (linked to project state service)
**170.12:** Rhythm-aware editing (beat detection, snap-to-grid for markers)
**170.13:** Multi-track sync (align multiple cameras using audio correlation)

---

## 🏁 Final Notes

**For Opus 4.6:** You own 170.8 completely. Contract-first pattern is established; follow the quick-start doc and you'll have 30+ min buffer before 05:42 deadline.

**For future phases:** Phase 170 is now the reference implementation for CUT-mode video editing. Use this architecture for:
- Other NLE integrations (DaVinci Resolve, Vegas Pro)
- Real-time collaboration layers (multiple users editing same timeline)
- A/B testing UI patterns (viewport layouts, node interactions)

---

**Phase 170 CUT: Building the future of AI-assisted video editing. 🎬🤖**
