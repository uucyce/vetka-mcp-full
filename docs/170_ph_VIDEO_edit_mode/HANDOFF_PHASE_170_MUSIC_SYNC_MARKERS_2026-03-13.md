# HANDOFF: Phase 170 Music-Sync → Markers Integration
**For:** Opus 4.6 Command + Team
**From:** Opus (Architect) — Phase 170 CUT video editing
**Date:** 2026-03-13 02:52 UTC
**Deadline:** 2026-03-13 05:42 UTC (2h 50m)
**Branch:** `codex/cut` (commit: acf6881b5)
**Sandbox:** `codex54_cut_fixture_sandbox` @ port 3211

---

## 🎯 Mission: Wire Music-Sync Workers → TimeMarker Bundle → Scene Graph

### What We Just Closed (Non-Blocking)
- ✅ Node-click stabilization (248) — Scene Graph focus handler + `/api/cut/timeline/apply` round-trip **PROVEN**
- ✅ Test hooks in place: `data-testid="dag-node-label"` + `window.__VETKA_CUT_TEST__.triggerSceneGraphFocus()`
- ✅ Smoke spec passing: `cut_scene_graph_node_click_smoke.spec.cjs`
- ⏱️ Pure DOM click actionability inside DAG canvas remains separate non-blocking UI-surface issue

### What You Own (Phase 170.8)
Connect the three layers:
1. **Energy pause worker** (`energy_pause_v1`) + **Audio sync worker** (`audio_sync_v1`) outputs
2. **TimeMarkerBundle** contract creation from slices + sync results
3. **Scene Graph marker nodes** visual rendering + badges

---

## 📦 SCOPE: Music-Sync Worker Integration

### Task 1: Backend Contract — Slice + Sync → TimeMarkerBundle
**File:** `src/api/routes/cut_routes.py` (or new `cut_marker_routes.py`)
**Status:** Contract-first
**Complexity:** Medium

#### What exists:
```
✓ cut_audio_sync_result_v1 (frozen schema)
✓ cut_slice_window_v1 (from energy_pause_v1 + transcript_pause_window_v1)
✗ cut_time_marker_bundle_v1 (MISSING — you create)
```

#### New Contract to Add
```json
{
  "cut_time_marker_bundle_v1": {
    "type": "object",
    "required": ["markers", "sync_status", "slice_method"],
    "properties": {
      "markers": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["id", "label", "start_ms", "end_ms", "source"],
          "properties": {
            "id": {"type": "string", "description": "unique marker id"},
            "label": {"type": "string", "description": "human-readable label (e.g., 'Beat 1', 'Verse')"},
            "start_ms": {"type": "number", "description": "marker window start in milliseconds"},
            "end_ms": {"type": "number", "description": "marker window end in milliseconds"},
            "source": {
              "type": "string",
              "enum": ["transcript_pause", "energy_pause", "hybrid"],
              "description": "which slicing method produced this window"
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "e.g., ['music', 'primary_track']"}
          }
        }
      },
      "sync_status": {
        "type": "object",
        "required": ["method", "offset_ms", "confidence"],
        "properties": {
          "method": {"type": "string", "enum": ["peaks_correlation", "peak_only"], "description": "which audio sync method was used"},
          "offset_ms": {"type": "number", "description": "detected sync offset in milliseconds"},
          "confidence": {"type": "number", "minimum": 0, "maximum": 1},
          "notes": {"type": "string", "description": "degradation reason if confidence < 0.7"}
        }
      },
      "slice_method": {
        "type": "string",
        "enum": ["transcript_only", "energy_only", "hybrid_merge"],
        "description": "which slicing strategy was applied"
      },
      "source_track_id": {"type": "string", "description": "reference to the music track being synced"}
    }
  }
}
```

#### Endpoint to Add
```
POST /api/cut/timeline/apply-with-markers
Request:
{
  "project_id": "...",
  "selected_shot_id": "...",
  "timeline_state": {...},
  "slice_config": {
    "method": "hybrid_merge",  // transcript_only | energy_only | hybrid_merge
    "use_sync": true,
    "sync_method": "peaks_correlation"
  }
}

Response:
{
  "timeline_applied": true,
  "marker_bundle": {...cut_time_marker_bundle_v1...},
  "applied_at": "2026-03-13T05:15:00Z"
}
```

**Test to create:** `tests/phase170/test_cut_music_marker_bundle_creation.py`
- Input: Berlin fixture + slice_config
- Expected: TimeMarkerBundle with 3-5 markers for music track
- Assert: `markers[0].source` ∈ {transcript_pause, energy_pause, hybrid}
- Assert: `sync_status.confidence > 0.7`

---

### Task 2: Wire Slice + Sync → Marker Creation (Backend Implementation)
**File:** `src/services/cut/` (new `marker_bundle_service.py`)
**Status:** 1-2 hour implementation
**Complexity:** Medium

#### Implementation sketch:
```python
# marker_bundle_service.py
async def create_marker_bundle_from_slices(
    project_id: str,
    track_id: str,
    slice_windows: List[SliceWindow],  # from energy_pause_v1
    sync_result: AudioSyncResult,      # from audio_sync_v1
    slice_method: str = "hybrid_merge"
) -> TimeMarkerBundle:
    """
    Merge transcript + energy slices into editorial markers.
    Apply sync offset to marker windows.
    Return labeled TimeMarkerBundle ready for Scene Graph.
    """
    # 1. Deduplicate + merge overlapping windows
    merged_windows = hybrid_merge_slices(slice_windows)

    # 2. Apply sync offset to all marker times
    offset_windows = [
        {
            "start": w["start"] + sync_result.offset_ms,
            "end": w["end"] + sync_result.offset_ms,
            "source": w["source"],
            "confidence": w.get("confidence", 0.9)
        }
        for w in merged_windows
    ]

    # 3. Create labeled markers (use transcript beats, or fallback to numeric labels)
    markers = [
        TimeMarker(
            id=f"{track_id}_marker_{i}",
            label=w.get("label", f"Slice {i+1}"),
            start_ms=int(w["start"]),
            end_ms=int(w["end"]),
            source=w["source"],
            confidence=w["confidence"],
            tags=["music", "primary_track"]
        )
        for i, w in enumerate(offset_windows)
    ]

    # 4. Assemble bundle
    return TimeMarkerBundle(
        markers=markers,
        sync_status=SyncStatus(
            method=sync_result.method,
            offset_ms=sync_result.offset_ms,
            confidence=sync_result.confidence,
            notes=sync_result.degradation_reason
        ),
        slice_method=slice_method,
        source_track_id=track_id
    )
```

**Integration point in `cut_routes.py`:**
```python
@router.post("/api/cut/timeline/apply-with-markers")
async def apply_timeline_with_markers(req: ApplyTimelineWithMarkersRequest):
    # ... existing timeline apply logic ...

    # NEW: Create marker bundle
    if req.slice_config.method != "none":
        marker_bundle = await marker_bundle_service.create_marker_bundle_from_slices(
            project_id=req.project_id,
            track_id=selected_track.id,
            slice_windows=slice_result.windows,      # from energy_pause_v1
            sync_result=sync_result,                  # from audio_sync_v1
            slice_method=req.slice_config.method
        )
    else:
        marker_bundle = None

    # Store in project state
    if marker_bundle:
        await project_state_service.update_markers(
            req.project_id,
            marker_bundle
        )

    return {
        "timeline_applied": True,
        "marker_bundle": marker_bundle,
        "applied_at": datetime.utcnow().isoformat()
    }
```

**Test:** `test_cut_music_marker_bundle_creation.py`
- Mock energy_pause_v1 output (3 windows)
- Mock audio_sync_v1 output (offset: +150ms)
- Call `create_marker_bundle_from_slices()`
- Assert: 3 markers with offset applied, sync_status populated

---

### Task 3: Frontend — Scene Graph Marker Nodes + Badges
**Files:**
- `client/src/components/cut/SceneGraph.tsx` (add marker node type)
- `client/src/components/cut/nodes/MarkerNode.tsx` (new marker node renderer)
- `client/src/components/cut/CutEditorLayout.tsx` (conditionally show music badges)

**Status:** 1-1.5 hour UI implementation
**Complexity:** Medium (contract + xyflow node)

#### What to add:

**1. Marker Node Type**
```typescript
// In SceneGraph.tsx useRoadmapDAG hook
const MarkerNodeType: NodeProps<{
  markerId: string;
  label: string;
  start_ms: number;
  end_ms: number;
  source: 'transcript_pause' | 'energy_pause' | 'hybrid';
  confidence: number;
}> = ({ data }) => (
  <MarkerNode {...data} />
);

// In DAG nodes: include marker nodes from timeline
useEffect(() => {
  if (markers) {
    const markerNodes = markers.map((m, i) => ({
      id: `marker_${m.id}`,
      type: 'marker',
      position: { x: calculateMarkerX(m.start_ms), y: 250 },
      data: {
        markerId: m.id,
        label: m.label,
        start_ms: m.start_ms,
        end_ms: m.end_ms,
        source: m.source,
        confidence: m.confidence
      }
    }));
    nodes.push(...markerNodes);
  }
}, [markers]);
```

**2. MarkerNode Renderer** (`MarkerNode.tsx`)
```typescript
import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

const MarkerNode = memo(({ data }: NodeProps) => {
  const width = Math.max(60, (data.end_ms - data.start_ms) / 100); // scale to canvas
  const sourceColor = {
    transcript_pause: '#8b5cf6',    // purple
    energy_pause: '#ec4899',         // pink
    hybrid: '#f59e0b'                // amber
  }[data.source];

  return (
    <div
      style={{
        width: `${width}px`,
        padding: '8px 6px',
        borderRadius: '4px',
        background: sourceColor,
        border: `2px solid ${sourceColor}`,
        opacity: data.confidence,
        fontSize: '11px',
        fontWeight: 600,
        color: 'white',
        textAlign: 'center',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      }}
      data-testid="marker-node"
      data-marker-id={data.markerId}
      data-marker-label={data.label}
    >
      {data.label}
    </div>
  );
});

export default MarkerNode;
```

**3. Music Badge in CutEditorLayout**
```typescript
// In CutEditorLayout.tsx
{markerBundle && (
  <div className="marker-badge">
    🎵 {markerBundle.markers.length} markers
    <span className="sync-confidence">
      Sync {(markerBundle.sync_status.confidence * 100).toFixed(0)}%
    </span>
  </div>
)}
```

**Test (E2E):** `client/e2e/cut_berlin_music_markers_smoke.spec.cjs`
```javascript
test('Berlin fixture: music track → visible markers', async ({ page }) => {
  await page.goto('http://localhost:3211/?fixture=berlin_fixture_v1');
  await page.waitForSelector('[data-testid="scene-graph"]');

  // Click music track in source browser
  await page.click('[data-testid="music-track-item"]');

  // Trigger marker creation
  await page.click('[data-testid="apply-timeline-btn"]');

  // Wait for markers to render
  const markerNodes = await page.locator('[data-testid="marker-node"]').count();
  expect(markerNodes).toBeGreaterThan(0);

  // Verify marker labels
  const firstMarkerLabel = await page
    .locator('[data-testid="marker-node"]')
    .first()
    .getAttribute('data-marker-label');
  expect(firstMarkerLabel).toBeTruthy();
});
```

---

## 📋 CHECKLIST (Time-Boxed)

### 0:00–0:30 — Backend Contract + Routes
- [ ] Create `cut_time_marker_bundle_v1` schema in `src/schemas/cut_schemas.py`
- [ ] Add `POST /api/cut/timeline/apply-with-markers` endpoint stub
- [ ] Add response model `TimeMarkerBundle` class

### 0:30–1:30 — Backend Implementation
- [ ] Create `src/services/cut/marker_bundle_service.py` with `create_marker_bundle_from_slices()`
- [ ] Integrate into `cut_routes.py` apply handler
- [ ] Write & pass `test_cut_music_marker_bundle_creation.py`

### 1:30–2:30 — Frontend Marker Nodes
- [ ] Add `MarkerNodeType` to `SceneGraph.tsx`
- [ ] Create `MarkerNode.tsx` component
- [ ] Wire into DAG nodes rendering

### 2:30–2:50 — E2E + Polish
- [ ] Write `cut_berlin_music_markers_smoke.spec.cjs`
- [ ] Add music badge to `CutEditorLayout.tsx`
- [ ] Run: `npx playwright test e2e/cut_berlin_music_markers_smoke.spec.cjs`

### 2:50–05:42 — Validation
- [ ] Run full test suite: `pytest -xvs tests/phase170/`
- [ ] Verify commit: `git add . && git commit -m "phase170.8: Music-sync → markers integration"`
- [ ] Update PHASE_170_CHECKPOINT.md with results

---

## 🔗 CONTRACTS & TEST HOOKS

### Existing Workers (Ready to Use)
- **`energy_pause_v1` worker:** `src/services/cut/pause_slice_worker.py`
  - Returns: `SliceWindow[]` with start/end/source/confidence
  - Test: `test_cut_audio_slice_sync_bakeoff.py` ✓

- **`audio_sync_v1` worker:** `src/services/cut/audio_sync_worker.py`
  - Returns: `AudioSyncResult` with method/offset_ms/confidence
  - Test: `test_cut_audio_sync_worker_api.py` ✓

### Berlin Fixture (Live Acceptance)
- **Location:** `client/e2e/fixtures/cut_berlin_fixture_state.json`
- **Track:** `"Punch" (Primary Music)`
- **Fixture sandbox:** port 3211 (`codex54_cut_fixture_sandbox`)
- **Current state:** Source browser hydration proves ✓, markers NOT yet visible

### Test Hook for Round-Trip
```typescript
window.__VETKA_CUT_TEST__ = {
  async triggerSceneGraphFocus(markerId: string) {
    // Already implemented in CutStandalone:666
    // Can reuse for marker testing
  }
};
```

---

## 📍 File Locations (Copy-Paste Ready)

**Backend routes:**
```
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/cut_routes.py
```

**Service folder:**
```
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/cut/
```

**Frontend components:**
```
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/cut/
```

**Test suites:**
```
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/phase170/
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/e2e/
```

---

## ⚡ CRITICAL NOTES

1. **Contract-first:** Write schema + test cases before implementation
2. **Reuse existing workers:** Don't rewrite `audio_sync_v1` or `energy_pause_v1` — just call them
3. **Berlin fixture acceptance:** Once markers render in sandbox, you're done
4. **Non-blocking:** Pure DOM click in DAG canvas (from 248) doesn't block this lane
5. **Time box:** 2h 50m deadline — prioritize backend contract (Task 1) if time runs short

---

## 🎬 Success Criteria

- ✅ `POST /api/cut/timeline/apply-with-markers` returns valid `TimeMarkerBundle`
- ✅ Backend test: `test_cut_music_marker_bundle_creation.py` passing
- ✅ Frontend: Marker nodes render in Scene Graph on Berlin fixture (sandbox port 3211)
- ✅ E2E: `cut_berlin_music_markers_smoke.spec.cjs` passing
- ✅ Music badge shows in CutEditorLayout when markers present
- ✅ Commit pushed to `codex/cut` with message: `phase170.8: Music-sync → markers integration`

---

## 📞 Support

**Blockers?** Check these files for reference:
- `PHASE_170_CUT_BERLIN_BOOTSTRAP_HANDOFF_2026-03-13.md` — fixture setup
- `PHASE_170_P170_7_SLICE_SYNC_METHOD_BAKEOFF_IMPLEMENTATION_2026-03-11.md` — sync strategy
- `tests/phase170/test_cut_audio_*.py` — worker API examples

**Markers for this phase:**
- `MARKER_170.8.MUSIC_SYNC_INTEGRATION` — main scope
- `MARKER_170.8.MARKER_BUNDLE_CONTRACT` — schema milestone
- `MARKER_170.8.SCENE_GRAPH_MARKERS` — UI milestone

Good luck! 🚀
