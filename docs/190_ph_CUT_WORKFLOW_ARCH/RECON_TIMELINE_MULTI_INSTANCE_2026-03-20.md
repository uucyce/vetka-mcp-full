# RECON: Timeline Multi-Instance via Dockview
**Date:** 2026-03-20
**Author:** Opus (Claude Code)
**Status:** DRAFT — awaiting user approval
**Depends on:** RECON_PANEL_DOCKING_2026-03-19.md (approved)

---

## 1. Problem Statement

Current: TimelinePanelDock is ONE dockview panel containing an internal TimelineTabBar (Main / cut-01 / +). Dockview doesn't know about these "sub-tabs" — can't drag/dock/split individual timelines.

Required: Each timeline version = separate dockview panel. User can:
- Drag timeline-cut-01 next to timeline-cut-00 → side-by-side comparison
- Stack timelines vertically → A/B reference view
- Float a timeline → separate window
- Tab multiple timelines in one group → like Premiere sequence tabs

This replaces both TimelineTabBar AND the hardcoded parallel timeline (MARKER_W5.2).

---

## 2. Current Architecture

### Store (useCutEditorStore)
```
timelineTabs: Array<{ id, label, version, mode, parentId }>
activeTimelineTabIndex: number
timelineId: string               ← active timeline ID
lanes: TimelineLane[]            ← ONE set, global
markers: TimeMarker[]            ← ONE set, global
currentTime: number              ← ONE playhead, global
```

### Components
```
TimelineTabBar.tsx    — renders tabs, calls setActiveTimelineTab(index)
TimelineTrackView.tsx — NO PROPS, reads lanes/markers/timelineId from store
TimelineToolbar.tsx   — snap, zoom, linked selection toggles
BPMTrack.tsx          — needs timelineId, scriptText, zoom, scrollLeft, duration
```

### Data Flow
1. User clicks tab → setActiveTimelineTab(i) → updates timelineId
2. Backend observes timelineId change → fetches lanes/markers for that timeline
3. Store updates lanes/markers → TimelineTrackView re-renders

### Problem
TimelineTrackView reads ONE global `lanes` state. Two instances would both show the same data. No per-timeline isolation.

---

## 3. Solution: Dockview Multi-Instance + Store Adapter

### 3.1 Approach: Active + Readonly Snapshot

**Active timeline** = full interactivity, reads/writes global store (lanes, markers, currentTime).
**Inactive timelines** = readonly snapshots, frozen data, dimmed UI.

When user clicks on an inactive timeline panel, it becomes active:
1. Save current lanes/markers to snapshot cache
2. Load target timeline's data into global store
3. Swap active/inactive styling

This avoids the complexity of parallel stores while enabling visual comparison.

### 3.2 Snapshot Cache

```typescript
// New state in useCutEditorStore:
timelineSnapshots: Map<string, {
  lanes: TimelineLane[];
  markers: TimeMarker[];
  currentTime: number;
  scrollLeft: number;
  zoom: number;
}>

// Actions:
snapshotTimeline(id: string): void     // save current state to cache
restoreTimeline(id: string): void      // load from cache to active state
```

### 3.3 Component Changes

**TimelinePanelDock** (in DockviewLayout.tsx) — receives `params.timelineId`:
```typescript
const TimelinePanelDock = (props: IDockviewPanelProps) => {
  const panelTimelineId = props.params?.timelineId as string;
  const activeTimelineId = useCutEditorStore(s => s.timelineId);
  const isActive = panelTimelineId === activeTimelineId;

  if (isActive) {
    return <TimelineActive />;      // full interactive, reads global store
  }
  return <TimelineSnapshot id={panelTimelineId} />;  // readonly, reads from cache
};
```

**TimelineActive** = current TimelineToolbar + TimelineTrackView + BPMTrack (unchanged).

**TimelineSnapshot** = lightweight readonly view:
- Renders cached lanes/markers (frozen)
- Dimmed opacity (0.7)
- Click anywhere → becomes active (swap)
- No playhead animation, no drag/trim
- Shows label + timestamp

**TimelineTabBar** → DELETED. Dockview tabs replace it entirely.

**TimelineToolbar** → stays inside active timeline panel only.

### 3.4 Dockview Integration

```typescript
// Creating a new timeline:
createVersionedTimeline(projectName, mode) {
  const id = `tl_${label}_${Date.now()}`;
  // ... existing logic ...

  // ADD: create dockview panel
  dockviewApi.addPanel({
    id: `timeline-${id}`,
    component: 'timeline',
    title: label,              // e.g. "project_cut-01"
    params: { timelineId: id },
    position: { referencePanel: `timeline-${currentId}`, direction: 'within' },
    // 'within' = same tab group (default Premiere behavior)
  });
}

// Switching active timeline:
dockviewApi.onDidActivePanelChange(panel => {
  if (panel.id.startsWith('timeline-')) {
    const tlId = panel.params.timelineId;
    snapshotTimeline(currentTimelineId);
    restoreTimeline(tlId);
  }
});
```

### 3.5 Dual View (replaces MARKER_W5.2)

No special code needed. User drags a timeline tab to "below" drop zone → dockview creates split. Both timelines visible:
- Active one: full interactive
- Other: readonly snapshot
- Click to swap

This is strictly better than the hardcoded parallel timeline.

---

## 4. Migration Steps

### Step 1: Add snapshot cache to store
- `timelineSnapshots` Map
- `snapshotTimeline()` and `restoreTimeline()` actions
- Zero UI changes, pure store addition

### Step 2: Refactor TimelinePanelDock
- Accept `params.timelineId`
- Render TimelineActive vs TimelineSnapshot based on active state
- Move TimelineToolbar inside TimelineActive only

### Step 3: Wire dockview ↔ store
- `createVersionedTimeline()` → also calls `dockviewApi.addPanel()`
- `onDidActivePanelChange` → snapshot/restore swap
- Remove timeline from `addPanel()` default layout → create via store
- Pass dockviewApi ref from DockviewLayout to store (or via context)

### Step 4: Delete TimelineTabBar
- Remove component file
- Remove from DockviewLayout / TimelinePanelDock
- Timeline tabs are now dockview native tabs

### Step 5: Delete parallel timeline code
- Remove `parallelTimelineTabIndex` from store
- Remove `swapParallelTimeline()` action
- Remove stacked dual view from old CutEditorLayoutV2 (already gone)
- Dockview split replaces this

---

## 5. What Changes

| Before | After |
|--------|-------|
| 1 dockview panel "Timeline" with internal TabBar | N dockview panels, one per timeline version |
| TimelineTabBar manages tabs | Dockview native tabs |
| Hardcoded parallel timeline (W5.2) | Dockview split (any direction) |
| Single global store | Active store + snapshot cache |
| Can't drag/dock timelines | Full drag/dock/float/split |

## 6. What Stays

- TimelineTrackView.tsx — unchanged (reads global store)
- TimelineToolbar.tsx — unchanged (moved into active panel only)
- BPMTrack.tsx — unchanged
- All store actions (addTimelineTab, etc.) — enhanced, not replaced
- Backend data flow — unchanged

## 7. Risk

| Risk | Mitigation |
|------|-----------|
| Snapshot stale after backend updates | Re-snapshot on data refresh |
| Multiple active timelines confusing | Only ONE active at a time, clear visual distinction |
| DockviewApi access from store | React context or ref forwarding |
| Performance with many snapshot panels | RenderWhenVisible HOC — unmount hidden panels |

---

## Decision Needed

1. Approve Active + Readonly Snapshot approach?
2. Approve 5-step migration?
3. Priority vs other CUT tasks?
