/**
 * MARKER_TIMELINE_DATA: Centralized timeline data hook.
 * Replaces repeated inline store selectors across 15+ components.
 * Single subscription point — consistent data shape, reduced boilerplate.
 *
 * @phase Alpha-4
 */
import { useMemo } from 'react';
import { useCutEditorStore } from '../store/useCutEditorStore';
import type { TimelineClip, TimelineLane } from '../store/useCutEditorStore';

/** Core timeline state — covers 90% of component needs */
export interface TimelineData {
  lanes: TimelineLane[];
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  selectedClipId: string | null;
  selectedClip: TimelineClip | null;
  zoom: number;
  scrollLeft: number;
}

/**
 * useTimelineData — single hook for timeline state.
 *
 * Usage:
 *   const { lanes, currentTime, selectedClip } = useTimelineData();
 *
 * Replaces:
 *   const lanes = useCutEditorStore((s) => s.lanes);
 *   const currentTime = useCutEditorStore((s) => s.currentTime);
 *   const selectedClipId = useCutEditorStore((s) => s.selectedClipId);
 *   // ... and manual clip lookup
 */
export function useTimelineData(): TimelineData {
  const lanes = useCutEditorStore((s) => s.lanes);
  const currentTime = useCutEditorStore((s) => s.currentTime);
  const duration = useCutEditorStore((s) => s.duration);
  const isPlaying = useCutEditorStore((s) => s.isPlaying);
  const selectedClipId = useCutEditorStore((s) => s.selectedClipId);
  const zoom = useCutEditorStore((s) => s.zoom);
  const scrollLeft = useCutEditorStore((s) => s.scrollLeft);

  // Derived: find selected clip across all lanes
  const selectedClip = useMemo(() => {
    if (!selectedClipId) return null;
    for (const lane of lanes) {
      const clip = lane.clips.find((c) => c.clip_id === selectedClipId);
      if (clip) return clip;
    }
    return null;
  }, [lanes, selectedClipId]);

  return { lanes, currentTime, duration, isPlaying, selectedClipId, selectedClip, zoom, scrollLeft };
}

/**
 * useSelectedClip — lightweight hook for components that only need the selected clip.
 * Avoids subscribing to currentTime/zoom/scrollLeft changes.
 */
export function useSelectedClip(): { clip: TimelineClip | null; clipId: string | null } {
  const lanes = useCutEditorStore((s) => s.lanes);
  const selectedClipId = useCutEditorStore((s) => s.selectedClipId);

  const clip = useMemo(() => {
    if (!selectedClipId) return null;
    for (const lane of lanes) {
      const found = lane.clips.find((c) => c.clip_id === selectedClipId);
      if (found) return found;
    }
    return null;
  }, [lanes, selectedClipId]);

  return { clip, clipId: selectedClipId };
}
