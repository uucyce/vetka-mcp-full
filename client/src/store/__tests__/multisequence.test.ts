/**
 * MARKER_MULTISEQUENCE-SWITCH — Tests for setActiveTimelineTab snapshot+restore+refresh cycle.
 *
 * Tests cover:
 *   - snapshot of outgoing timeline on switch
 *   - restoreTimeline called for incoming tab
 *   - refreshProjectState called when no cached snapshot exists
 *   - no redundant refresh when snapshot cache hit
 *   - no-op when switching to same tab
 *   - out-of-range index ignored
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useCutEditorStore } from '../useCutEditorStore';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function resetStore() {
  // Reset to initial state before each test
  useCutEditorStore.setState({
    timelineTabs: [
      { id: 'tl_main', label: 'Main', version: 0, createdAt: 0, mode: 'manual' },
      { id: 'tl_cut01', label: 'Cut-01', version: 1, createdAt: 1, mode: 'manual' },
      { id: 'tl_cut02', label: 'Cut-02', version: 2, createdAt: 2, mode: 'manual' },
    ],
    activeTimelineTabIndex: 0,
    timelineId: 'tl_main',
    timelineSnapshots: new Map(),
    lanes: [{ lane_id: 'V1', clips: [{ clip_id: 'c1', start_sec: 0, duration_sec: 5 }] }] as any,
    markers: [],
    currentTime: 3.0,
    scrollLeft: 100,
    zoom: 1.5,
    refreshProjectState: null,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('setActiveTimelineTab', () => {
  beforeEach(resetStore);

  it('switches activeTimelineTabIndex', () => {
    useCutEditorStore.getState().setActiveTimelineTab(1);
    expect(useCutEditorStore.getState().activeTimelineTabIndex).toBe(1);
  });

  it('updates timelineId to the new tab', () => {
    useCutEditorStore.getState().setActiveTimelineTab(1);
    expect(useCutEditorStore.getState().timelineId).toBe('tl_cut01');
  });

  it('snapshots outgoing timeline before switching', () => {
    useCutEditorStore.getState().setActiveTimelineTab(1);
    const snaps = useCutEditorStore.getState().timelineSnapshots;
    expect(snaps.has('tl_main')).toBe(true);
  });

  it('snapshot contains outgoing lanes', () => {
    useCutEditorStore.getState().setActiveTimelineTab(1);
    const snap = useCutEditorStore.getState().timelineSnapshots.get('tl_main');
    expect(snap?.lanes).toBeDefined();
    expect(snap?.lanes[0]?.lane_id).toBe('V1');
  });

  it('snapshot contains outgoing currentTime', () => {
    useCutEditorStore.getState().setActiveTimelineTab(1);
    const snap = useCutEditorStore.getState().timelineSnapshots.get('tl_main');
    expect(snap?.currentTime).toBe(3.0);
  });

  it('calls refreshProjectState when no snapshot for incoming tab', () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    useCutEditorStore.setState({ refreshProjectState: refresh });

    useCutEditorStore.getState().setActiveTimelineTab(1);

    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it('does NOT call refreshProjectState when snapshot exists for incoming tab', () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    useCutEditorStore.setState({ refreshProjectState: refresh });

    // Pre-populate snapshot for tl_cut01
    const snaps = new Map();
    snaps.set('tl_cut01', { lanes: [], markers: [], currentTime: 0, scrollLeft: 0, zoom: 1 });
    useCutEditorStore.setState({ timelineSnapshots: snaps });

    useCutEditorStore.getState().setActiveTimelineTab(1);

    expect(refresh).not.toHaveBeenCalled();
  });

  it('restores lanes from snapshot when switching back', () => {
    // Switch to tab 1, then back to tab 0
    useCutEditorStore.getState().setActiveTimelineTab(1);
    // Switch back — tab 0 was snapshotted
    useCutEditorStore.getState().setActiveTimelineTab(0);
    // Lanes should be restored from snapshot
    const state = useCutEditorStore.getState();
    expect(state.lanes[0]?.lane_id).toBe('V1');
  });

  it('no-op when switching to same index', () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    useCutEditorStore.setState({ refreshProjectState: refresh });

    useCutEditorStore.getState().setActiveTimelineTab(0); // already at 0

    expect(refresh).not.toHaveBeenCalled();
    expect(useCutEditorStore.getState().activeTimelineTabIndex).toBe(0);
  });

  it('ignores negative index', () => {
    useCutEditorStore.getState().setActiveTimelineTab(-1);
    expect(useCutEditorStore.getState().activeTimelineTabIndex).toBe(0);
  });

  it('ignores out-of-range index', () => {
    useCutEditorStore.getState().setActiveTimelineTab(99);
    expect(useCutEditorStore.getState().activeTimelineTabIndex).toBe(0);
  });

  it('switches to last tab correctly', () => {
    useCutEditorStore.getState().setActiveTimelineTab(2);
    expect(useCutEditorStore.getState().timelineId).toBe('tl_cut02');
  });

  it('refreshProjectState not called when null', () => {
    // Should not throw
    useCutEditorStore.setState({ refreshProjectState: null });
    expect(() => useCutEditorStore.getState().setActiveTimelineTab(1)).not.toThrow();
  });
});
