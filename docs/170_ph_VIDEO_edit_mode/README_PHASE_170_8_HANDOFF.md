# Phase 170.8: Music-Sync → Markers Handoff
**For:** Opus 4.6 Command + Team
**Deadline:** 2026-03-13 05:42 UTC
**Status:** ✅ Handoff Documents Ready

---

## 📑 Quick Access Index

### 🎯 START HERE
**→ [`OPUS_QUICK_START_PHASE_170_8_2026-03-13.md`](./OPUS_QUICK_START_PHASE_170_8_2026-03-13.md)** (299 lines)
- 30-second mission brief
- 4-task execution timeline (copy-paste ready)
- Validation checklist

### 📘 FULL SCOPE
**→ [`HANDOFF_PHASE_170_MUSIC_SYNC_MARKERS_2026-03-13.md`](./HANDOFF_PHASE_170_MUSIC_SYNC_MARKERS_2026-03-13.md)** (466 lines)
- Complete mission statement
- Task contracts + implementation sketches
- Berlin fixture acceptance gate
- Support references

### 📊 CONTEXT & ROADMAP
**→ [`PHASE_170_CHECKPOINT_2026-03-13.md`](./PHASE_170_CHECKPOINT_2026-03-13.md)** (256 lines)
- Waves 170.1–170.7 summary
- Test coverage breakdown (18 modules)
- Architecture + Berlin fixture status
- Path to Phase 171

---

## ⚡ Mission at a Glance

**Wire music-sync workers → marker bundle → Scene Graph visualization**

### Three Layers
```
Layer 1: energy_pause_v1 + audio_sync_v1 (workers exist ✓)
    ↓
Layer 2: TimeMarkerBundle contract + /api/cut/timeline/apply-with-markers (YOU build)
    ↓
Layer 3: MarkerNode rendering + badges in UI (YOU build)
```

### Time Budget: 2h 50m
```
00:00–00:30  Backend contract      (schema + endpoint stub)
00:30–01:30  Backend impl          (create_marker_bundle_from_slices)
01:30–02:30  Frontend markers      (MarkerNode.tsx + DAG wiring)
02:30–02:50  E2E + badge          (Berlin fixture acceptance)
02:50–05:42  Validation           (git commit + full test suite)
             ✅ Buffer: 30–50 min
```

---

## 📋 Pre-Flight Checklist

- [ ] Read `OPUS_QUICK_START_PHASE_170_8_2026-03-13.md` (5 min)
- [ ] Verify branch: `git branch -v` → `codex/cut`
- [ ] Check fixture: access `http://localhost:3211` (should load Berlin fixture)
- [ ] Verify workers: `grep -n "energy_pause_v1\|audio_sync_v1" src/services/cut/*.py`

---

## 🎯 Success Criteria

All of these must pass by 05:42 UTC:

1. ✓ TimeMarkerBundle schema defined (BaseModel in src/schemas/cut_schemas.py)
2. ✓ `/api/cut/timeline/apply-with-markers` endpoint returns valid bundle
3. ✓ `test_cut_music_marker_bundle_creation.py` passing (4/4)
4. ✓ MarkerNode renders in Scene Graph (colored: purple/pink/amber by source)
5. ✓ Music badge shows in CutEditorLayout (e.g., "🎵 3 markers (Sync 95%)")
6. ✓ `cut_berlin_music_markers_smoke.spec.cjs` passing (E2E on Berlin fixture)
7. ✓ Full test suite: `pytest tests/phase170/ -q` (no new failures)
8. ✓ Git commit: `phase170.8: Music-sync → markers integration`

---

## 🔧 Key Files

### Backend (Build These)
| File | Lines | Purpose |
|------|-------|---------|
| `src/schemas/cut_schemas.py` | +20 | Add TimeMarker, SyncStatus, TimeMarkerBundle |
| `src/api/routes/cut_routes.py` | +30 | Add /api/cut/timeline/apply-with-markers endpoint |
| `src/services/cut/marker_bundle_service.py` | 100 | NEW — create_marker_bundle_from_slices() |
| `tests/phase170/test_cut_music_marker_bundle_creation.py` | 80 | NEW — contract tests |

### Frontend (Build These)
| File | Lines | Purpose |
|------|-------|---------|
| `client/src/components/cut/nodes/MarkerNode.tsx` | 60 | NEW — marker node component |
| `client/src/components/cut/SceneGraph.tsx` | +20 | Wire marker nodes into DAG |
| `client/src/components/cut/CutEditorLayout.tsx` | +10 | Add music badge display |
| `client/e2e/cut_berlin_music_markers_smoke.spec.cjs` | 50 | NEW — E2E acceptance test |

### Existing (Don't Modify)
```
✓ src/services/cut/audio_sync_worker.py      (ready to call)
✓ src/services/cut/pause_slice_worker.py     (ready to call)
✓ client/e2e/fixtures/cut_berlin_fixture_state.json
✓ client/src/components/cut/CutStandalone.tsx (test hooks already in place)
```

---

## 🚨 Common Blockers & Solutions

| Blocker | Solution |
|---------|----------|
| "Where do I call energy_pause_v1?" | See HANDOFF doc, Task 2 — integration sketch shows exact place |
| "How to structure TimeMarkerBundle?" | Copy the schema from HANDOFF doc Task 1, paste into schemas |
| "MarkerNode not rendering?" | Check DAG nodes array includes marker nodes (add log before push) |
| "Berlin fixture not loading?" | Verify port 3211 sandbox config; see PHASE_170_CUT_BERLIN_BOOTSTRAP_HANDOFF_2026-03-13.md |
| "Test failing?" | Run with `-xvs` for verbose output: `pytest tests/phase170/test_cut_music_marker_bundle_creation.py -xvs` |

---

## 📞 Support References

**If you need deeper context:**
- Wave strategy: `PHASE_170_P170_7_SLICE_SYNC_METHOD_BAKEOFF_IMPLEMENTATION_2026-03-11.md`
- Worker APIs: `tests/phase170/test_cut_audio_sync_worker_api.py` (shows how to call workers)
- Berlin fixture: `PHASE_170_CUT_BERLIN_BOOTSTRAP_HANDOFF_2026-03-13.md`
- Node-click (previous wave): `PHASE_170_CUT_SCENE_GRAPH_NODE_CLICK_STABILIZATION_2026-03-13.md`

---

## 📊 Handoff Completeness

| Component | Status | Coverage |
|-----------|--------|----------|
| Worker APIs (energy_pause, audio_sync) | ✅ Ready | 100% — no changes needed |
| Schema contracts | 📝 TODO | TimeMarkerBundle (new) |
| Backend routes | 📝 TODO | /api/cut/timeline/apply-with-markers (new) |
| Service integration | 📝 TODO | marker_bundle_service.py (new) |
| Frontend components | 📝 TODO | MarkerNode.tsx (new) |
| Backend tests | 📝 TODO | test_cut_music_marker_bundle_creation.py (new) |
| E2E tests | 📝 TODO | cut_berlin_music_markers_smoke.spec.cjs (new) |
| **Total scope** | **~500 lines** | **4 new files, ~300 lines modification** |

---

## ✨ What 170.7 Achieved

✅ Scene Graph node-click stabilization complete
- Focus handler proven (test hook round-trip works)
- Smoke spec: 1/1 passing
- Pure DOM click actionability (non-blocking separate issue)

---

## 🚀 Begin Here

1. **Open:** `OPUS_QUICK_START_PHASE_170_8_2026-03-13.md`
2. **Follow:** 4-task timeline with copy-paste code
3. **Validate:** Checklist at end of each task
4. **Submit:** Commit with message from Quick Start doc

**You have 2h 50m. Contract-first pattern = faster implementation. Good luck! 🎯**

---

**Generated:** 2026-03-13 03:36 UTC
**For:** Opus 4.6 Command + Team
**Branch:** `codex/cut`
**Deadline:** 05:42 UTC
