# OPUS 4.6 QUICK START: Phase 170.8 Music-Sync Markers
**Time:** 2h 50m from 2026-03-13 02:55 UTC
**Deadline:** 05:42 UTC
**Status:** Contract-first implementation

---

## ⚡ 30-Second Brief

You're wiring two existing workers (`energy_pause_v1` + `audio_sync_v1`) into a marker bundle that Scene Graph renders. Three tasks:

1. **Backend contract** (30 min) — schema + endpoint stub
2. **Backend impl** (60 min) — merge slices + sync → TimeMarkerBundle
3. **Frontend UI** (60 min) — marker nodes + badges
4. **Validation** (20 min) — E2E pass on Berlin fixture

---

## 🎯 Three Tasks (Copy-Paste Flow)

### TASK 1: Backend Contract (30 min)

**Files to touch:**
```
src/schemas/cut_schemas.py         ← Add TimeMarkerBundle + SyncStatus classes
src/api/routes/cut_routes.py       ← Add /api/cut/timeline/apply-with-markers endpoint
```

**What to copy into schemas:**
```python
# TimeMarker class
class TimeMarker(BaseModel):
    id: str
    label: str
    start_ms: float
    end_ms: float
    source: Literal["transcript_pause", "energy_pause", "hybrid"]
    confidence: float  # 0.0-1.0
    tags: List[str] = ["music"]

# SyncStatus class
class SyncStatus(BaseModel):
    method: Literal["peaks_correlation", "peak_only"]
    offset_ms: float
    confidence: float
    notes: Optional[str] = None

# TimeMarkerBundle (main contract)
class TimeMarkerBundle(BaseModel):
    markers: List[TimeMarker]
    sync_status: SyncStatus
    slice_method: Literal["transcript_only", "energy_only", "hybrid_merge"]
    source_track_id: str
```

**What to add to cut_routes.py:**
```python
@router.post("/api/cut/timeline/apply-with-markers")
async def apply_timeline_with_markers(req: ApplyTimelineWithMarkersRequest):
    """
    MARKER_170.8.MUSIC_SYNC_INTEGRATION
    Wire energy_pause_v1 + audio_sync_v1 → TimeMarkerBundle → store
    """
    # existing timeline apply logic...
    return {
        "timeline_applied": True,
        "marker_bundle": TimeMarkerBundle(...),
        "applied_at": datetime.utcnow().isoformat()
    }
```

**Test file:** Create `tests/phase170/test_cut_music_marker_bundle_creation.py`
```python
pytest tests/phase170/test_cut_music_marker_bundle_creation.py -v
# Expect: PASSED (or skip if markers schema not fully wired)
```

---

### TASK 2: Backend Service (60 min)

**New file:**
```
src/services/cut/marker_bundle_service.py
```

**Core function:**
```python
async def create_marker_bundle_from_slices(
    project_id: str,
    track_id: str,
    slice_windows: List[SliceWindow],     # from energy_pause_v1
    sync_result: AudioSyncResult,         # from audio_sync_v1
    slice_method: str = "hybrid_merge"
) -> TimeMarkerBundle:
    """
    1. Merge overlapping windows (hybrid_merge)
    2. Apply sync offset to all markers
    3. Label them (transcript beats or numeric)
    4. Return TimeMarkerBundle
    """
    # See HANDOFF doc for full implementation sketch
```

**Integration in cut_routes.py:**
```python
# Inside apply_timeline_with_markers handler:
if req.slice_config.method != "none":
    marker_bundle = await marker_bundle_service.create_marker_bundle_from_slices(
        project_id=req.project_id,
        track_id=selected_track.id,
        slice_windows=slice_result.windows,
        sync_result=sync_result,
        slice_method=req.slice_config.method
    )
    await project_state_service.update_markers(req.project_id, marker_bundle)
```

**Run test:**
```bash
pytest tests/phase170/test_cut_music_marker_bundle_creation.py -xvs
# Should PASS with 3+ markers created from Berlin fixture
```

---

### TASK 3: Frontend Marker Nodes (60 min)

**New files:**
```
client/src/components/cut/nodes/MarkerNode.tsx
```

**Modify:**
```
client/src/components/cut/SceneGraph.tsx           (add marker node type to DAG)
client/src/components/cut/CutEditorLayout.tsx      (add music badge)
```

**MarkerNode.tsx snippet:**
```typescript
const MarkerNode = ({ data }) => {
  const sourceColor = {
    transcript_pause: '#8b5cf6',
    energy_pause: '#ec4899',
    hybrid: '#f59e0b'
  }[data.source];

  return (
    <div
      data-testid="marker-node"
      data-marker-id={data.markerId}
      data-marker-label={data.label}
      style={{
        background: sourceColor,
        opacity: data.confidence,
        padding: '8px 6px',
        borderRadius: '4px',
        color: 'white',
        fontSize: '11px'
      }}
    >
      {data.label}
    </div>
  );
};
```

**Add to SceneGraph.tsx DAG nodes:**
```typescript
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
```

**Add badge to CutEditorLayout.tsx:**
```typescript
{markerBundle && (
  <div className="marker-badge">
    🎵 {markerBundle.markers.length} markers (Sync {(markerBundle.sync_status.confidence * 100).toFixed(0)}%)
  </div>
)}
```

---

### TASK 4: E2E Validation (20 min)

**New test file:** `client/e2e/cut_berlin_music_markers_smoke.spec.cjs`

```javascript
const { test, expect } = require('@playwright/test');

test('Berlin fixture: music track → visible markers', async ({ page }) => {
  await page.goto('http://localhost:3211/?fixture=berlin_fixture_v1');
  await page.waitForSelector('[data-testid="scene-graph"]');

  // Navigate to music track
  await page.click('[data-testid="music-track-item"]');

  // Trigger marker generation
  await page.click('[data-testid="apply-timeline-btn"]');
  await page.waitForTimeout(500);

  // Verify markers exist
  const markerCount = await page.locator('[data-testid="marker-node"]').count();
  expect(markerCount).toBeGreaterThan(0);

  // Verify first marker has label
  const firstLabel = await page
    .locator('[data-testid="marker-node"]')
    .first()
    .getAttribute('data-marker-label');
  expect(firstLabel).toBeTruthy();
});
```

**Run:**
```bash
npx playwright test e2e/cut_berlin_music_markers_smoke.spec.cjs
# Expect: 1 passed
```

---

## 🎬 Full Execution Timeline

| Time | Task | Command |
|------|------|---------|
| 00:00–00:30 | Backend contract | vim src/schemas/cut_schemas.py && vim src/api/routes/cut_routes.py |
| 00:30–01:30 | Backend service | vim src/services/cut/marker_bundle_service.py && pytest tests/phase170/test_cut_music_marker_bundle_creation.py -xvs |
| 01:30–02:30 | Frontend nodes | vim client/src/components/cut/nodes/MarkerNode.tsx && vim client/src/components/cut/SceneGraph.tsx |
| 02:30–02:50 | E2E + badge | vim client/e2e/cut_berlin_music_markers_smoke.spec.cjs && npx playwright test |
| 02:50–05:42 | Validation | pytest tests/phase170/ && git commit |

---

## ✅ Validation Checklist

- [ ] Schema compiles: `python -c "from src.schemas.cut_schemas import TimeMarkerBundle"`
- [ ] Endpoint created: `grep -n "apply-with-markers" src/api/routes/cut_routes.py`
- [ ] Service passes tests: `pytest tests/phase170/test_cut_music_marker_bundle_creation.py -q`
- [ ] MarkerNode renders: `grep -n "data-testid=\"marker-node\"" client/src/components/cut/nodes/MarkerNode.tsx`
- [ ] E2E passing: `npx playwright test e2e/cut_berlin_music_markers_smoke.spec.cjs --reporter=list`
- [ ] Commit ready: `git status` shows clean or staged only

---

## 🔑 Key Contract Points

**Worker Inputs (Already Implemented):**
- `energy_pause_v1()` → `SliceWindow[]{start, end, source, confidence}`
- `audio_sync_v1()` → `AudioSyncResult{method, offset_ms, confidence, notes}`

**Your Responsibility:**
- Merge slice windows (handle overlaps via hybrid_merge)
- Apply sync offset to marker times
- Create TimeMarkerBundle with labeled markers
- Return via new endpoint

**Frontend Responsibility (Opus team):**
- Render MarkerNode in DAG (colored by source)
- Show badge with marker count + sync confidence
- E2E smoke test on Berlin fixture

---

## 🚨 If You Get Stuck

1. **Schema errors?** Check existing `cut_audio_sync_result_v1` in `src/schemas/cut_schemas.py` for BaseModel pattern
2. **Worker API?** See `test_cut_audio_sync_worker_api.py` for how to call `audio_sync_v1`
3. **Markers not visible?** Check DAG nodes list includes marker nodes (log before push to nodes array)
4. **Berlin fixture not loading?** Verify port 3211 in sandbox config; see `PHASE_170_CUT_BERLIN_BOOTSTRAP_HANDOFF_2026-03-13.md`

---

## 📝 Markers for This Sprint

- `MARKER_170.8.MUSIC_SYNC_INTEGRATION` — scope marker
- `MARKER_170.8.MARKER_BUNDLE_CONTRACT` — schema done
- `MARKER_170.8.SCENE_GRAPH_MARKERS` — UI rendering done
- `MARKER_170.8.BERLIN_ACCEPTANCE_PASSING` — final gate

---

**Go! 🚀 You have 2h 50m. Contract-first, then implement, then validate.**
