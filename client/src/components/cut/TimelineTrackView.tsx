/**
 * MARKER_170.NLE.TIMELINE: Horizontal timeline track view — the core NLE visual.
 * Renders lanes as horizontal tracks with positioned clip blocks.
 * Includes time ruler, playhead, waveform overlays, drag/drop, trim handles, and markers.
 */
import {
  useRef,
  useState,
  useEffect,
  useCallback,
  useMemo,
  type CSSProperties,
  type MouseEvent,
  type RefObject,
  type WheelEvent as ReactWheelEvent,
} from 'react';

import { API_BASE } from '../../config/api.config';
import { useCutEditorStore, type TimelineClip, type TimelineLane } from '../../store/useCutEditorStore';
import WaveformCanvas from './WaveformCanvas';
import { IconFilmStrip, IconSpeaker, IconCamera, IconLink } from './icons/CutIcons';

const LANE_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  video_main: { label: 'V1', color: '#4a9eff', icon: <IconFilmStrip size={12} color="#888" /> },
  audio_sync: { label: 'A1', color: '#22c55e', icon: <IconSpeaker size={12} color="#888" /> },
  take_alt_y: { label: 'V2', color: '#a855f7', icon: <IconCamera size={12} color="#888" /> },
  take_alt_z: { label: 'V3', color: '#f59e0b', icon: <IconCamera size={12} color="#888" /> },
  aux: { label: 'AUX', color: '#888', icon: <IconLink size={12} color="#888" /> },
};

const CONTAINER_STYLE: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  background: '#0a0a0a',
  overflow: 'hidden',
  position: 'relative',
  fontFamily: 'system-ui',
  fontSize: 11,
};

const RULER_HEIGHT = 28;
const LANE_HEADER_WIDTH = 76;
const TRIM_HANDLE_WIDTH = 7;
const MIN_CLIP_DURATION_SEC = 0.15;
const PLAYHEAD_FOLLOW_PADDING = 120;
const SNAP_THRESHOLD_PX = 5;

const RULER_STYLE: CSSProperties = {
  height: RULER_HEIGHT,
  background: '#111',
  borderBottom: '1px solid #333',
  position: 'relative',
  overflow: 'hidden',
  flexShrink: 0,
  marginLeft: LANE_HEADER_WIDTH,
  cursor: 'pointer',
};

const TRACKS_CONTAINER: CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  overflowY: 'auto',
  overflowX: 'hidden',
  position: 'relative',
};

const LANE_ROW: CSSProperties = {
  display: 'flex',
  flexDirection: 'row',
  borderBottom: '1px solid #1a1a1a',
  position: 'relative',
  flexShrink: 0,
};

const LANE_HEADER: CSSProperties = {
  width: LANE_HEADER_WIDTH,
  flexShrink: 0,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 4,
  padding: '4px 2px',
  borderRight: '1px solid #222',
  background: '#080808',
  userSelect: 'none',
};

const LANE_CONTENT: CSSProperties = {
  flex: 1,
  position: 'relative',
  overflow: 'hidden',
};

const CLIP_STYLE: CSSProperties = {
  position: 'absolute',
  top: 3,
  bottom: 3,
  borderRadius: 3,
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  padding: '0 6px',
  overflow: 'hidden',
  cursor: 'grab',
  transition: 'border-color 0.1s',
};

const PLAYHEAD_STYLE: CSSProperties = {
  position: 'absolute',
  top: 0,
  bottom: 0,
  width: 1,
  background: '#fff',
  zIndex: 100,
  pointerEvents: 'none',
};

const PLAYHEAD_HEAD: CSSProperties = {
  position: 'absolute',
  top: -2,
  left: -5,
  width: 0,
  height: 0,
  borderLeft: '5px solid transparent',
  borderRight: '5px solid transparent',
  borderTop: '6px solid #fff',
};

const MARKER_STYLE: CSSProperties = {
  position: 'absolute',
  top: 0,
  width: 2,
  zIndex: 50,
  borderRadius: 1,
  pointerEvents: 'none',
};

const MARKER_COLORS: Record<string, string> = {
  favorite: '#f59e0b',
  comment: '#3b82f6',
  cam: '#a855f7',
  insight: '#22c55e',
};

const TRACK_BUTTON_ROW: CSSProperties = {
  display: 'flex',
  gap: 3,
};

const TRACK_BUTTON: CSSProperties = {
  width: 18,
  height: 16,
  borderRadius: 3,
  border: '1px solid #333',
  background: '#111',
  color: '#888',
  fontSize: 9,
  fontWeight: 700,
  lineHeight: '14px',
  padding: 0,
  cursor: 'pointer',
};

const TRACK_SLIDER: CSSProperties = {
  width: 44,
  height: 16,
  appearance: 'none' as const,
  background: '#333',
  borderRadius: 2,
  outline: 'none',
  cursor: 'pointer',
  transform: 'rotate(-90deg)',
  transformOrigin: 'center',
};

const TRACK_SLIDER_WRAP: CSSProperties = {
  width: 18,
  height: 52,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

type ClipDragMode = 'move' | 'trim_left' | 'trim_right';

type ClipDragState = {
  mode: ClipDragMode;
  clipId: string;
  sourcePath: string;
  laneId: string;
  originalLaneId: string;
  startSec: number;
  durationSec: number;
  originalStartSec: number;
  originalDurationSec: number;
  grabOffsetSec: number;
};

type MarkerKind = 'favorite' | 'comment' | 'cam' | 'insight';

type MarkerDraftState = {
  x: number;
  y: number;
  timeSec: number;
  mediaPath: string;
  kind: MarkerKind;
  text: string;
};

type ClipContextMenuState = {
  x: number;
  y: number;
  clip: TimelineClip;
};

type SnapIndicatorState = {
  timeSec: number;
  laneId: string;
};

type WaveformHoverState = {
  clipId: string;
  ratio: number;
  timeSec: number;
};

function basename(path: string): string {
  return path.split('/').pop()?.split('\\').pop() || path;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function roundTimeline(value: number): number {
  return Math.round(value * 1000) / 1000;
}

function clipDisplayTime(clip: TimelineClip, dragState: ClipDragState | null): { startSec: number; durationSec: number } {
  if (!dragState || dragState.clipId !== clip.clip_id) {
    return { startSec: clip.start_sec, durationSec: clip.duration_sec };
  }
  return { startSec: dragState.startSec, durationSec: dragState.durationSec };
}

function clampMenu(value: number, max: number): number {
  return Math.max(8, Math.min(value, Math.max(8, max - 8)));
}

function rulerTickIntervalForZoom(zoom: number): number {
  if (zoom < 20) return 10;
  if (zoom < 40) return 5;
  if (zoom < 100) return 2;
  if (zoom >= 200) return 0.5;
  return 1;
}

function uniqueSnapCandidates(values: number[]): number[] {
  return [...new Set(values.filter((value) => Number.isFinite(value) && value >= 0).map((value) => roundTimeline(value)))];
}

function findClosestSnapCandidate(timeSec: number, candidates: number[], thresholdSec: number): { candidate: number; distance: number } | null {
  let best: { candidate: number; distance: number } | null = null;
  for (const candidate of candidates) {
    const distance = Math.abs(timeSec - candidate);
    if (distance <= thresholdSec && (!best || distance < best.distance)) {
      best = { candidate, distance };
    }
  }
  return best;
}

function collectSnapCandidates(args: {
  lanes: TimelineLane[];
  laneId: string;
  clipId: string;
  zoom: number;
  referenceSec: number;
  playheadSec?: number;
  markInSec?: number | null;
  markOutSec?: number | null;
  markerTimes?: number[];
}): number[] {
  const candidates: number[] = [];

  for (const lane of args.lanes) {
    for (const clip of lane.clips || []) {
      if (clip.clip_id === args.clipId) continue;
      candidates.push(clip.start_sec, clip.start_sec + clip.duration_sec);
    }
  }

  if (args.playheadSec != null) candidates.push(args.playheadSec);
  if (args.markInSec != null) candidates.push(args.markInSec);
  if (args.markOutSec != null) candidates.push(args.markOutSec);
  if (args.markerTimes?.length) candidates.push(...args.markerTimes);

  const tickInterval = rulerTickIntervalForZoom(args.zoom);
  const baseTick = Math.round(Math.max(0, args.referenceSec) / tickInterval) * tickInterval;
  for (const offset of [-1, 0, 1]) {
    candidates.push(baseTick + offset * tickInterval);
  }

  return uniqueSnapCandidates(candidates);
}

function findSnapTarget(args: {
  lanes: TimelineLane[];
  laneId: string;
  clipId: string;
  startSec: number;
  durationSec: number;
  zoom: number;
  playheadSec?: number;
  markInSec?: number | null;
  markOutSec?: number | null;
  markerTimes?: number[];
}): { snappedStartSec: number; indicator: SnapIndicatorState | null } {
  const thresholdSec = SNAP_THRESHOLD_PX / Math.max(args.zoom, 1);
  const candidates = collectSnapCandidates({
    lanes: args.lanes,
    laneId: args.laneId,
    clipId: args.clipId,
    zoom: args.zoom,
    referenceSec: args.startSec + args.durationSec / 2,
    playheadSec: args.playheadSec,
    markInSec: args.markInSec,
    markOutSec: args.markOutSec,
    markerTimes: args.markerTimes,
  });
  const proposedEnd = args.startSec + args.durationSec;
  const startMatch = findClosestSnapCandidate(args.startSec, candidates, thresholdSec);
  const endMatch = findClosestSnapCandidate(proposedEnd, candidates, thresholdSec);

  let best: { candidate: number; snappedStartSec: number; distance: number } | null = null;
  if (startMatch) {
    best = { candidate: startMatch.candidate, snappedStartSec: startMatch.candidate, distance: startMatch.distance };
  }
  if (endMatch && (!best || endMatch.distance < best.distance)) {
    best = { candidate: endMatch.candidate, snappedStartSec: endMatch.candidate - args.durationSec, distance: endMatch.distance };
  }

  if (!best) {
    return { snappedStartSec: args.startSec, indicator: null };
  }

  return {
    snappedStartSec: roundTimeline(Math.max(0, best.snappedStartSec)),
    indicator: { timeSec: roundTimeline(best.candidate), laneId: args.laneId },
  };
}

function TimeRuler({
  zoom,
  scrollLeft,
  totalWidth,
  rulerRef,
  onSeek,
  onScrubStart,
  onDoubleClick,
}: {
  zoom: number;
  scrollLeft: number;
  totalWidth: number;
  rulerRef: RefObject<HTMLDivElement | null>;
  onSeek: (time: number) => void;
  onScrubStart: (event: MouseEvent<HTMLDivElement>) => void;
  onDoubleClick: (event: MouseEvent<HTMLDivElement>) => void;
}) {
  const handleClick = (event: MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left + scrollLeft;
    onSeek(x / zoom);
  };

  const tickInterval = rulerTickIntervalForZoom(zoom);

  const ticks: { x: number; label: string; major: boolean }[] = [];
  const startTime = Math.floor(scrollLeft / zoom / tickInterval) * tickInterval;
  const endTime = (scrollLeft + totalWidth) / zoom + tickInterval;

  for (let time = startTime; time <= endTime; time += tickInterval) {
    if (time < 0) continue;
    const x = time * zoom - scrollLeft;
    if (x < -20 || x > totalWidth + 20) continue;
    const major = tickInterval >= 1 ? time % (tickInterval * 5) === 0 : time % 5 === 0;
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    const label =
      major || tickInterval >= 2 ? `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}` : '';
    ticks.push({ x, label, major });
  }

  return (
    <div
      ref={rulerRef}
      data-testid="cut-timeline-ruler"
      style={RULER_STYLE}
      onClick={handleClick}
      onMouseDown={onScrubStart}
      onDoubleClick={onDoubleClick}
    >
      {ticks.map((tick, index) => (
        <div
          key={index}
          style={{
            position: 'absolute',
            left: tick.x,
            bottom: 0,
            width: 1,
            height: tick.major ? 14 : 8,
            background: tick.major ? '#555' : '#333',
          }}
        >
          {tick.label ? (
            <span
              style={{
                position: 'absolute',
                bottom: tick.major ? 15 : 9,
                left: 2,
                fontSize: 9,
                color: tick.major ? '#888' : '#555',
                whiteSpace: 'nowrap',
                userSelect: 'none',
              }}
            >
              {tick.label}
            </span>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export default function TimelineTrackView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const rulerRef = useRef<HTMLDivElement>(null);
  const zoomRef = useRef(60);
  const scrollLeftRef = useRef(0);
  const displayLanesRef = useRef<TimelineLane[]>([]);
  const trackHeightRef = useRef(56);
  const currentTimeRef = useRef(0);
  const markInRef = useRef<number | null>(null);
  const markOutRef = useRef<number | null>(null);
  const markerTimesRef = useRef<number[]>([]);
  const snapEnabledRef = useRef(true);
  const sessionRef = useRef<{
    sandboxRoot: string | null;
    projectId: string | null;
    timelineId: string;
    refreshProjectState: (() => Promise<void>) | null;
  }>({
    sandboxRoot: null,
    projectId: null,
    timelineId: 'main',
    refreshProjectState: null,
  });

  const [dragState, setDragState] = useState<ClipDragState | null>(null);
  const [scrubActive, setScrubActive] = useState(false);
  const [markerDraft, setMarkerDraft] = useState<MarkerDraftState | null>(null);
  const [contextMenu, setContextMenu] = useState<ClipContextMenuState | null>(null);
  const [snapIndicator, setSnapIndicator] = useState<SnapIndicatorState | null>(null);
  const [waveformHover, setWaveformHover] = useState<WaveformHoverState | null>(null);

  const lanes = useCutEditorStore((state) => state.lanes);
  const waveforms = useCutEditorStore((state) => state.waveforms);
  const markers = useCutEditorStore((state) => state.markers);
  const zoom = useCutEditorStore((state) => state.zoom);
  const scrollLeft = useCutEditorStore((state) => state.scrollLeft);
  const trackHeight = useCutEditorStore((state) => state.trackHeight);
  const currentTime = useCutEditorStore((state) => state.currentTime);
  const isPlaying = useCutEditorStore((state) => state.isPlaying);
  const selectedClipId = useCutEditorStore((state) => state.selectedClipId);
  const hoveredClipId = useCutEditorStore((state) => state.hoveredClipId);
  const sandboxRoot = useCutEditorStore((state) => state.sandboxRoot);
  const projectId = useCutEditorStore((state) => state.projectId);
  const timelineId = useCutEditorStore((state) => state.timelineId);
  const refreshProjectState = useCutEditorStore((state) => state.refreshProjectState);
  const activeMediaPath = useCutEditorStore((state) => state.sourceMediaPath);
  const syncSurface = useCutEditorStore((state) => state.syncSurface);
  const markIn = useCutEditorStore((state) => state.markIn);
  const markOut = useCutEditorStore((state) => state.markOut);
  const seek = useCutEditorStore((state) => state.seek);
  const setScrollLeft = useCutEditorStore((state) => state.setScrollLeft);
  const setTrackHeight = useCutEditorStore((state) => state.setTrackHeight);
  const mutedLanes = useCutEditorStore((state) => state.mutedLanes);
  const soloLanes = useCutEditorStore((state) => state.soloLanes);
  const laneVolumes = useCutEditorStore((state) => state.laneVolumes);
  const snapEnabled = useCutEditorStore((state) => state.snapEnabled);
  const toggleMute = useCutEditorStore((state) => state.toggleMute);
  const toggleSolo = useCutEditorStore((state) => state.toggleSolo);
  const setLaneVolume = useCutEditorStore((state) => state.setLaneVolume);
  const setSelectedClip = useCutEditorStore((state) => state.setSelectedClip);
  // MARKER_W1.3: Timeline clip click → Source Monitor
  const setActiveMedia = useCutEditorStore((state) => state.setSourceMedia);
  const setHoveredClip = useCutEditorStore((state) => state.setHoveredClip);

  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);
  useEffect(() => {
    scrollLeftRef.current = scrollLeft;
  }, [scrollLeft]);
  useEffect(() => {
    trackHeightRef.current = trackHeight;
  }, [trackHeight]);
  useEffect(() => {
    currentTimeRef.current = currentTime;
  }, [currentTime]);
  useEffect(() => {
    markInRef.current = markIn;
  }, [markIn]);
  useEffect(() => {
    markOutRef.current = markOut;
  }, [markOut]);
  useEffect(() => {
    // MARKER_173.18.NLE.BEAT_SNAP: music_sync markers enter the generic snap target pool as beat cues.
    markerTimesRef.current = markers.map((marker) => marker.start_sec);
  }, [markers]);
  useEffect(() => {
    snapEnabledRef.current = snapEnabled;
  }, [snapEnabled]);
  useEffect(() => {
    sessionRef.current = { sandboxRoot, projectId, timelineId, refreshProjectState };
  }, [sandboxRoot, projectId, timelineId, refreshProjectState]);

  const containerWidth = containerRef.current?.clientWidth || 800;

  const waveformMap = useMemo(() => {
    const map = new Map<string, number[]>();
    for (const item of waveforms) {
      if (item.waveform_bins?.length) {
        map.set(item.source_path, item.waveform_bins);
      }
    }
    return map;
  }, [waveforms]);

  const displayLanes = lanes.length
    ? lanes
    : [
        { lane_id: 'v1_empty', lane_type: 'video_main', clips: [] },
        { lane_id: 'a1_empty', lane_type: 'audio_sync', clips: [] },
      ];

  useEffect(() => {
    displayLanesRef.current = displayLanes;
  }, [displayLanes]);

  const clipOverlayTop = useMemo(() => {
    if (!dragState) return null;
    const laneIndex = displayLanes.findIndex((lane) => lane.lane_id === dragState.laneId);
    if (laneIndex < 0) return null;
    return RULER_HEIGHT + laneIndex * trackHeight + 3;
  }, [displayLanes, dragState, trackHeight]);

  const playheadX = currentTime * zoom - scrollLeft + LANE_HEADER_WIDTH;

  const timeFromTrackClientX = useCallback((clientX: number) => {
    const contentRect = contentRef.current?.getBoundingClientRect();
    if (!contentRect) return 0;
    const x = clientX - contentRect.left + scrollLeftRef.current;
    return Math.max(0, x / zoomRef.current);
  }, []);

  const timeFromRulerClientX = useCallback((clientX: number) => {
    const rulerRect = rulerRef.current?.getBoundingClientRect();
    if (!rulerRect) return 0;
    const x = clientX - rulerRect.left + scrollLeftRef.current;
    return Math.max(0, x / zoomRef.current);
  }, []);

  const laneIdFromClientY = useCallback((clientY: number) => {
    const contentRect = contentRef.current?.getBoundingClientRect();
    if (!contentRect || displayLanesRef.current.length === 0) {
      return displayLanesRef.current[0]?.lane_id || 'video_main';
    }
    const scrollTop = contentRef.current?.scrollTop || 0;
    const y = clientY - contentRect.top + scrollTop;
    const laneIndex = clamp(Math.floor(y / Math.max(trackHeightRef.current, 1)), 0, displayLanesRef.current.length - 1);
    return displayLanesRef.current[laneIndex]?.lane_id || displayLanesRef.current[0]?.lane_id || 'video_main';
  }, []);

  const applyTimelineOps = useCallback(async (ops: Array<Record<string, unknown>>) => {
    const session = sessionRef.current;
    if (!session.sandboxRoot || !session.projectId) {
      return;
    }

    const response = await fetch(`${API_BASE}/cut/timeline/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sandbox_root: session.sandboxRoot,
        project_id: session.projectId,
        timeline_id: session.timelineId || 'main',
        author: 'cut_nle_ui',
        ops,
      }),
    });
    if (!response.ok) {
      throw new Error(`timeline apply failed: HTTP ${response.status}`);
    }
    const payload = (await response.json()) as { success?: boolean; error?: { message?: string } };
    if (!payload.success) {
      throw new Error(payload.error?.message || 'timeline apply failed');
    }
    await session.refreshProjectState?.();
  }, []);

  const resolveMarkerMediaPath = useCallback(
    (timeSec: number, laneId?: string) => {
      if (laneId) {
        const lane = displayLanesRef.current.find((entry) => entry.lane_id === laneId);
        const clip = lane?.clips.find(
          (item) => timeSec >= item.start_sec && timeSec <= item.start_sec + item.duration_sec
        );
        if (clip?.source_path) {
          return clip.source_path;
        }
      }
      for (const lane of displayLanesRef.current) {
        const clip = lane.clips.find(
          (item) => timeSec >= item.start_sec && timeSec <= item.start_sec + item.duration_sec
        );
        if (clip?.source_path) {
          return clip.source_path;
        }
      }
      return activeMediaPath || null;
    },
    [activeMediaPath]
  );

  const createMarker = useCallback(
    async (draft: { timeSec: number; mediaPath: string; kind: MarkerKind; text: string }) => {
      const session = sessionRef.current;
      if (!session.sandboxRoot || !session.projectId || !draft.mediaPath) {
        return;
      }
      const response = await fetch(`${API_BASE}/cut/time-markers/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: session.sandboxRoot,
          project_id: session.projectId,
          timeline_id: session.timelineId || 'main',
          author: 'cut_nle_ui',
          op: 'create',
          media_path: draft.mediaPath,
          kind: draft.kind,
          start_sec: roundTimeline(draft.timeSec),
          end_sec: roundTimeline(draft.timeSec + 1),
          anchor_sec: roundTimeline(draft.timeSec),
          score: draft.kind === 'favorite' ? 1.0 : draft.kind === 'comment' ? 0.7 : draft.kind === 'cam' ? 0.85 : 0.9,
          text: draft.text,
          source_engine: 'cut_nle_ui',
        }),
      });
      if (!response.ok) {
        throw new Error(`marker create failed: HTTP ${response.status}`);
      }
      const payload = (await response.json()) as { success?: boolean; error?: { message?: string } };
      if (!payload.success) {
        throw new Error(payload.error?.message || 'marker create failed');
      }
      await session.refreshProjectState?.();
    },
    []
  );

  const exportPremiereXml = useCallback(async () => {
    const session = sessionRef.current;
    if (!session.sandboxRoot) {
      return;
    }
    const response = await fetch(`${API_BASE}/cut/export/premiere-xml`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sandbox_root: session.sandboxRoot,
        project_id: session.projectId || '',
        fps: 25,
      }),
    });
    if (!response.ok) {
      throw new Error(`export xml failed: HTTP ${response.status}`);
    }
    const payload = (await response.json()) as { success?: boolean; error?: { message?: string } };
    if (!payload.success) {
      throw new Error(payload.error?.message || 'export xml failed');
    }
  }, []);

  const openMarkerDraft = useCallback(
    (clientX: number, clientY: number, timeSec: number, laneId?: string) => {
      const mediaPath = resolveMarkerMediaPath(timeSec, laneId);
      if (!mediaPath || !containerRef.current) {
        return;
      }
      const rect = containerRef.current.getBoundingClientRect();
      setContextMenu(null);
      setMarkerDraft({
        x: clampMenu(clientX - rect.left, rect.width - 220),
        y: clampMenu(clientY - rect.top, rect.height - 112),
        timeSec: roundTimeline(timeSec),
        mediaPath,
        kind: 'favorite',
        text: '',
      });
    },
    [resolveMarkerMediaPath]
  );

  const applySuggestedSync = useCallback(
    async (clip: TimelineClip) => {
      const match = syncSurface.find((item) => item.source_path === clip.source_path);
      if (!match?.recommended_method) {
        return;
      }
      await applyTimelineOps([
        {
          op: 'apply_sync_offset',
          clip_id: clip.clip_id,
          method: match.recommended_method,
          offset_sec: match.recommended_offset_sec,
          reference_path: match.reference_path,
          confidence: match.confidence,
          source: 'context_menu',
        },
      ]);
    },
    [applyTimelineOps, syncSurface]
  );

  const removeClip = useCallback(
    async (clipId: string) => {
      await applyTimelineOps([{ op: 'remove_clip', clip_id: clipId }]);
    },
    [applyTimelineOps]
  );

  const beginClipInteraction = useCallback(
    (clip: TimelineClip, laneId: string, mode: ClipDragMode, event: MouseEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setSelectedClip(clip.clip_id);
      setActiveMedia(clip.source_path);
      const pointerTime = timeFromTrackClientX(event.clientX);
      const startSec = roundTimeline(clip.start_sec);
      const durationSec = roundTimeline(Math.max(MIN_CLIP_DURATION_SEC, clip.duration_sec));
      setDragState({
        mode,
        clipId: clip.clip_id,
        sourcePath: clip.source_path,
        laneId,
        originalLaneId: laneId,
        startSec,
        durationSec,
        originalStartSec: startSec,
        originalDurationSec: durationSec,
        grabOffsetSec: clamp(pointerTime - clip.start_sec, 0, clip.duration_sec),
      });
    },
    [setActiveMedia, setSelectedClip, timeFromTrackClientX]
  );

  const handleWheel = useCallback(
    (event: ReactWheelEvent) => {
      const containerRect = containerRef.current?.getBoundingClientRect();
      const localX = containerRect ? (event.clientX - containerRect.left) : Number.POSITIVE_INFINITY;
      if (event.shiftKey && localX <= LANE_HEADER_WIDTH) {
        setTrackHeight(trackHeight - event.deltaY * 0.08);
        event.preventDefault();
        return;
      }
      if (event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) {
        setScrollLeft(Math.max(0, scrollLeft + (event.deltaX || event.deltaY)));
        event.preventDefault();
      }
    },
    [scrollLeft, setScrollLeft, setTrackHeight, trackHeight]
  );

  const handleTrackClick = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      if ((event.target as HTMLElement).dataset.clip) return;
      seek(timeFromTrackClientX(event.clientX));
      setContextMenu(null);
    },
    [seek, timeFromTrackClientX]
  );

  const handleTrackDoubleClick = useCallback(
    (event: MouseEvent<HTMLDivElement>, laneId: string) => {
      if ((event.target as HTMLElement).dataset.clip) {
        return;
      }
      const timeSec = timeFromTrackClientX(event.clientX);
      seek(timeSec);
      openMarkerDraft(event.clientX, event.clientY, timeSec, laneId);
    },
    [openMarkerDraft, seek, timeFromTrackClientX]
  );

  const handleClipClick = useCallback(
    (clipId: string, sourcePath: string, event: MouseEvent) => {
      event.stopPropagation();
      setSelectedClip(clipId);
      setActiveMedia(sourcePath);
      setContextMenu(null);
    },
    [setActiveMedia, setSelectedClip]
  );

  const handleWaveformHover = useCallback((clip: TimelineClip, event: MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = rect.width > 0 ? clamp((event.clientX - rect.left) / rect.width, 0, 1) : 0;
    setWaveformHover({
      clipId: clip.clip_id,
      ratio,
      timeSec: roundTimeline(clip.start_sec + clip.duration_sec * ratio),
    });
  }, []);

  const handleWaveformSeek = useCallback(
    (clip: TimelineClip, event: MouseEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      const rect = event.currentTarget.getBoundingClientRect();
      const ratio = rect.width > 0 ? clamp((event.clientX - rect.left) / rect.width, 0, 1) : 0;
      const targetTime = clip.start_sec + clip.duration_sec * ratio;
      setSelectedClip(clip.clip_id);
      setActiveMedia(clip.source_path);
      setWaveformHover({
        clipId: clip.clip_id,
        ratio,
        timeSec: roundTimeline(targetTime),
      });
      seek(targetTime);
      setContextMenu(null);
    },
    [seek, setActiveMedia, setSelectedClip]
  );

  const handleClipContextMenu = useCallback(
    (clip: TimelineClip, event: MouseEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      if (!containerRef.current) {
        return;
      }
      const rect = containerRef.current.getBoundingClientRect();
      setSelectedClip(clip.clip_id);
      setActiveMedia(clip.source_path);
      setMarkerDraft(null);
      setContextMenu({
        x: clampMenu(event.clientX - rect.left, rect.width - 180),
        y: clampMenu(event.clientY - rect.top, rect.height - 180),
        clip,
      });
    },
    [setActiveMedia, setSelectedClip]
  );

  const handleRulerScrubStart = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      event.preventDefault();
      seek(timeFromRulerClientX(event.clientX));
      setMarkerDraft(null);
      setContextMenu(null);
      setScrubActive(true);
    },
    [seek, timeFromRulerClientX]
  );

  const handleRulerDoubleClick = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      const timeSec = timeFromRulerClientX(event.clientX);
      seek(timeSec);
      openMarkerDraft(event.clientX, event.clientY, timeSec);
    },
    [openMarkerDraft, seek, timeFromRulerClientX]
  );

  useEffect(() => {
    if (!markerDraft && !contextMenu) {
      return undefined;
    }
    const close = () => {
      setMarkerDraft(null);
      setContextMenu(null);
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        close();
      }
    };
    window.addEventListener('mousedown', close);
    window.addEventListener('keydown', handleKey);
    return () => {
      window.removeEventListener('mousedown', close);
      window.removeEventListener('keydown', handleKey);
    };
  }, [contextMenu, markerDraft]);

  useEffect(() => {
    if (!dragState && !scrubActive) {
      return undefined;
    }

    const handleMouseMove = (event: globalThis.MouseEvent) => {
      if (scrubActive) {
        seek(timeFromRulerClientX(event.clientX));
      }
      if (!dragState) {
        return;
      }

      if (dragState.mode === 'move') {
        const pointerTime = timeFromTrackClientX(event.clientX);
        const nextLaneId = laneIdFromClientY(event.clientY);
        setDragState((current) => {
          if (!current) return current;
          const rawStartSec = roundTimeline(Math.max(0, pointerTime - current.grabOffsetSec));
          if (!snapEnabledRef.current || event.altKey) {
            setSnapIndicator(null);
            return {
              ...current,
              laneId: nextLaneId,
              startSec: rawStartSec,
            };
          }
          // MARKER_170.NLE.SNAP_GRID: snap move/trim gestures to clip edges, playhead, marks, markers, and ruler ticks.
          const snapped = findSnapTarget({
            lanes: displayLanesRef.current,
            laneId: nextLaneId,
            clipId: current.clipId,
            startSec: rawStartSec,
            durationSec: current.durationSec,
            zoom: zoomRef.current,
            playheadSec: currentTimeRef.current,
            markInSec: markInRef.current,
            markOutSec: markOutRef.current,
            markerTimes: markerTimesRef.current,
          });
          setSnapIndicator(snapped.indicator);
          return {
            ...current,
            laneId: nextLaneId,
            startSec: snapped.snappedStartSec,
          };
        });
        return;
      }

      const pointerTime = timeFromTrackClientX(event.clientX);
      setDragState((current) => {
        if (!current) return current;
        if (current.mode === 'trim_left') {
          const clipEnd = current.originalStartSec + current.originalDurationSec;
          const nextStart = clamp(pointerTime, 0, clipEnd - MIN_CLIP_DURATION_SEC);
          if (!snapEnabledRef.current || event.altKey) {
            setSnapIndicator(null);
            return {
              ...current,
              startSec: nextStart,
              durationSec: roundTimeline(Math.max(MIN_CLIP_DURATION_SEC, clipEnd - nextStart)),
            };
          }
          const snapped = findSnapTarget({
            lanes: displayLanesRef.current,
            laneId: current.laneId,
            clipId: current.clipId,
            startSec: nextStart,
            durationSec: Math.max(MIN_CLIP_DURATION_SEC, clipEnd - nextStart),
            zoom: zoomRef.current,
            playheadSec: currentTimeRef.current,
            markInSec: markInRef.current,
            markOutSec: markOutRef.current,
            markerTimes: markerTimesRef.current,
          });
          setSnapIndicator(snapped.indicator);
          return {
            ...current,
            startSec: snapped.snappedStartSec,
            durationSec: roundTimeline(Math.max(MIN_CLIP_DURATION_SEC, clipEnd - snapped.snappedStartSec)),
          };
        }
        const nextEnd = Math.max(current.originalStartSec + MIN_CLIP_DURATION_SEC, pointerTime);
        if (!snapEnabledRef.current || event.altKey) {
          setSnapIndicator(null);
          return {
            ...current,
            durationSec: roundTimeline(Math.max(MIN_CLIP_DURATION_SEC, nextEnd - current.originalStartSec)),
          };
        }
        const thresholdSec = SNAP_THRESHOLD_PX / Math.max(zoomRef.current, 1);
        const candidates = collectSnapCandidates({
          lanes: displayLanesRef.current,
          laneId: current.laneId,
          clipId: current.clipId,
          zoom: zoomRef.current,
          referenceSec: nextEnd,
          playheadSec: currentTimeRef.current,
          markInSec: markInRef.current,
          markOutSec: markOutRef.current,
          markerTimes: markerTimesRef.current,
        });
        const snapMatch = findClosestSnapCandidate(nextEnd, candidates, thresholdSec);
        const snappedEnd = snapMatch?.candidate ?? nextEnd;
        setSnapIndicator(snapMatch ? { timeSec: roundTimeline(snapMatch.candidate), laneId: current.laneId } : null);
        return {
          ...current,
          durationSec: roundTimeline(Math.max(MIN_CLIP_DURATION_SEC, snappedEnd - current.originalStartSec)),
        };
      });
    };

    const handleMouseUp = () => {
      const activeDrag = dragState;
      setScrubActive(false);
      setSnapIndicator(null);
      setDragState(null);
      if (!activeDrag) {
        return;
      }

      const ops: Array<Record<string, unknown>> = [];
      if (
        activeDrag.mode === 'move'
        && (activeDrag.laneId !== activeDrag.originalLaneId || Math.abs(activeDrag.startSec - activeDrag.originalStartSec) > 0.001)
      ) {
        ops.push({
          op: 'move_clip',
          clip_id: activeDrag.clipId,
          lane_id: activeDrag.laneId,
          start_sec: activeDrag.startSec,
        });
      }

      if (
        (activeDrag.mode === 'trim_left' || activeDrag.mode === 'trim_right')
        && (
          Math.abs(activeDrag.startSec - activeDrag.originalStartSec) > 0.001
          || Math.abs(activeDrag.durationSec - activeDrag.originalDurationSec) > 0.001
        )
      ) {
        const trimOp: Record<string, unknown> = {
          op: 'trim_clip',
          clip_id: activeDrag.clipId,
          duration_sec: activeDrag.durationSec,
        };
        if (activeDrag.mode === 'trim_left') {
          trimOp.start_sec = activeDrag.startSec;
        }
        ops.push(trimOp);
      }

      if (ops.length) {
        void applyTimelineOps(ops);
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp, { once: true });
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [applyTimelineOps, dragState, laneIdFromClientY, scrubActive, seek, timeFromRulerClientX, timeFromTrackClientX]);

  useEffect(() => {
    if (!isPlaying || dragState || scrubActive) {
      return;
    }
    const viewportWidth = Math.max((containerRef.current?.clientWidth || 0) - LANE_HEADER_WIDTH, 0);
    if (!viewportWidth) {
      return;
    }
    const playheadWithinViewport = currentTime * zoom - scrollLeft;
    const rightThreshold = Math.max(80, viewportWidth - PLAYHEAD_FOLLOW_PADDING);
    if (playheadWithinViewport > rightThreshold) {
      // MARKER_170.NLE.AUTOSCROLL: keep the playhead inside the visible timeline while playback runs.
      setScrollLeft(Math.max(0, currentTime * zoom - rightThreshold));
    }
  }, [currentTime, dragState, isPlaying, scrubActive, scrollLeft, setScrollLeft, zoom]);

  return (
    <div ref={containerRef} data-testid="cut-timeline-track-view" style={CONTAINER_STYLE} onWheel={handleWheel}>
      <TimeRuler
        zoom={zoom}
        scrollLeft={scrollLeft}
        totalWidth={containerWidth - LANE_HEADER_WIDTH}
        rulerRef={rulerRef}
        onSeek={seek}
        onScrubStart={handleRulerScrubStart}
        onDoubleClick={handleRulerDoubleClick}
      />

      {markIn != null && markOut != null && markOut > markIn ? (
        <div
          style={{
            position: 'absolute',
            left: LANE_HEADER_WIDTH + markIn * zoom - scrollLeft,
            top: 0,
            width: Math.max(2, (markOut - markIn) * zoom),
            height: RULER_HEIGHT,
            background: 'linear-gradient(90deg, rgba(34, 197, 94, 0.2), rgba(239, 68, 68, 0.2))',
            pointerEvents: 'none',
            zIndex: 20,
          }}
        />
      ) : null}
      {markIn != null ? (
        <div
          style={{
            position: 'absolute',
            left: LANE_HEADER_WIDTH + markIn * zoom - scrollLeft - 5,
            top: 0,
            width: 0,
            height: 0,
            borderLeft: '5px solid transparent',
            borderRight: '5px solid transparent',
            borderTop: '8px solid #22c55e',
            zIndex: 21,
            pointerEvents: 'none',
          }}
        />
      ) : null}
      {markOut != null ? (
        <div
          style={{
            position: 'absolute',
            left: LANE_HEADER_WIDTH + markOut * zoom - scrollLeft - 5,
            top: 0,
            width: 0,
            height: 0,
            borderLeft: '5px solid transparent',
            borderRight: '5px solid transparent',
            borderTop: '8px solid #ef4444',
            zIndex: 21,
            pointerEvents: 'none',
          }}
        />
      ) : null}
      {markers.map((marker) => {
        const markerX = marker.start_sec * zoom - scrollLeft + LANE_HEADER_WIDTH;
        if (markerX < LANE_HEADER_WIDTH - 6 || markerX > containerWidth + 6) {
          return null;
        }
        const color = MARKER_COLORS[marker.kind] || '#888';
        return (
          <div
            key={`ruler_${marker.marker_id}`}
            style={{
              position: 'absolute',
              left: markerX,
              top: 0,
              width: 10,
              height: RULER_HEIGHT,
              zIndex: 22,
              pointerEvents: 'none',
            }}
            title={`${marker.kind}: ${marker.text || ''}`}
          >
            <div
              style={{
                width: 0,
                height: 0,
                borderLeft: '5px solid transparent',
                borderRight: '5px solid transparent',
                borderTop: `8px solid ${color}`,
              }}
            />
          </div>
        );
      })}

      {snapIndicator ? (
        <div
          style={{
            position: 'absolute',
            left: LANE_HEADER_WIDTH + snapIndicator.timeSec * zoom - scrollLeft,
            top: RULER_HEIGHT,
            bottom: 0,
            width: 1,
            borderLeft: '1px dashed rgba(250, 204, 21, 0.95)',
            boxShadow: '0 0 10px rgba(250, 204, 21, 0.35)',
            zIndex: 130,
            pointerEvents: 'none',
          }}
        />
      ) : null}

      <div ref={contentRef} style={TRACKS_CONTAINER}>
        {displayLanes.map((lane) => {
          const config = LANE_CONFIG[lane.lane_type] || LANE_CONFIG.aux;
          const isMuted = mutedLanes.has(lane.lane_id);
          const hasSolo = soloLanes.size > 0;
          const isSolo = soloLanes.has(lane.lane_id);
          const laneDimmed = isMuted || (hasSolo && !isSolo);
          return (
            <div key={lane.lane_id} style={{ ...LANE_ROW, height: trackHeight, opacity: laneDimmed ? 0.3 : 1 }}>
              <div style={LANE_HEADER}>
                <span style={{ display: 'flex', alignItems: 'center' }}>{config.icon}</span>
                <span style={{ fontSize: 11, fontWeight: 600, color: config.color }}>{config.label}</span>
                {/* MARKER_170.NLE.TRACK_SOLO_MUTE: per-lane solo/mute controls live in the header. */}
                <div style={TRACK_BUTTON_ROW}>
                  <button
                    style={{
                      ...TRACK_BUTTON,
                      color: soloLanes.has(lane.lane_id) ? '#111' : '#888',
                      background: soloLanes.has(lane.lane_id) ? '#facc15' : '#111',
                      borderColor: soloLanes.has(lane.lane_id) ? '#facc15' : '#333',
                    }}
                    title="Solo lane"
                    onClick={(event) => {
                      event.stopPropagation();
                      toggleSolo(lane.lane_id);
                    }}
                  >
                    S
                  </button>
                  <button
                    style={{
                      ...TRACK_BUTTON,
                      color: mutedLanes.has(lane.lane_id) ? '#111' : '#888',
                      background: mutedLanes.has(lane.lane_id) ? '#ef4444' : '#111',
                      borderColor: mutedLanes.has(lane.lane_id) ? '#ef4444' : '#333',
                    }}
                    title="Mute lane"
                    onClick={(event) => {
                      event.stopPropagation();
                      toggleMute(lane.lane_id);
                    }}
                  >
                    M
                  </button>
                </div>
                {/* Volume slider removed (CUT-0.4 cleanup) — volume via context menu or hotkeys */}
              </div>

              <div
                data-testid={`cut-timeline-lane-${lane.lane_id}`}
                style={LANE_CONTENT}
                onClick={handleTrackClick}
                onDoubleClick={(event) => handleTrackDoubleClick(event, lane.lane_id)}
              >
                {lane.clips.map((clip) => {
                  if (dragState?.clipId === clip.clip_id) {
                    return null;
                  }
                  const { startSec, durationSec } = clipDisplayTime(clip, dragState);
                  const x = startSec * zoom - scrollLeft;
                  const width = durationSec * zoom;
                  if (x + width < 0 || x > containerWidth) {
                    return null;
                  }

                  const isSelected = selectedClipId === clip.clip_id;
                  const isHovered = hoveredClipId === clip.clip_id;
                  const waveformBins = waveformMap.get(clip.source_path);
                  const syncInfo = clip.sync;

                  return (
                    <div
                      key={clip.clip_id}
                      data-clip="1"
                      data-testid={`cut-timeline-clip-${clip.clip_id}`}
                      style={{
                        ...CLIP_STYLE,
                        left: x,
                        width: Math.max(4, width),
                        background: `${config.color}${isSelected ? '44' : isHovered ? '33' : '22'}`,
                        border: `1px solid ${isSelected ? config.color : isHovered ? `${config.color}88` : `${config.color}44`}`,
                      }}
                      onClick={(event) => handleClipClick(clip.clip_id, clip.source_path, event)}
                      onMouseDown={(event) => beginClipInteraction(clip, lane.lane_id, 'move', event)}
                      onMouseEnter={() => setHoveredClip(clip.clip_id)}
                      onMouseLeave={() => setHoveredClip(null)}
                      onContextMenu={(event) => handleClipContextMenu(clip, event)}
                    >
                      <div
                        data-clip="1"
                        style={{
                          position: 'absolute',
                          left: 0,
                          top: 0,
                          bottom: 0,
                          width: TRIM_HANDLE_WIDTH,
                          cursor: 'ew-resize',
                          zIndex: 3,
                        }}
                        onMouseDown={(event) => beginClipInteraction(clip, lane.lane_id, 'trim_left', event)}
                      />
                      <div
                        data-clip="1"
                        style={{
                          position: 'absolute',
                          right: 0,
                          top: 0,
                          bottom: 0,
                          width: TRIM_HANDLE_WIDTH,
                          cursor: 'ew-resize',
                          zIndex: 3,
                        }}
                        onMouseDown={(event) => beginClipInteraction(clip, lane.lane_id, 'trim_right', event)}
                      />

                      {width > 20 ? (
                        <div
                          data-clip="1"
                          style={{
                            position: 'absolute',
                            inset: 0,
                            opacity: waveformBins ? 0.5 : 0.85,
                            zIndex: 1,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                          onMouseDown={(event) => event.stopPropagation()}
                          onMouseMove={(event) => handleWaveformHover(clip, event)}
                          onMouseLeave={() =>
                            setWaveformHover((current) => (current?.clipId === clip.clip_id ? null : current))
                          }
                          onClick={(event) => handleWaveformSeek(clip, event)}
                          title={waveformBins ? 'Click waveform to seek inside clip' : 'No waveform bins yet'}
                        >
                          {waveformBins ? (
                            <WaveformCanvas
                              bins={waveformBins}
                              width={Math.max(4, width) - 2}
                              height={trackHeight - 8}
                              color={config.color}
                              cursorRatio={waveformHover?.clipId === clip.clip_id ? waveformHover.ratio : null}
                            />
                          ) : (
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 6,
                                color: '#9ca3af',
                                textTransform: 'uppercase',
                                letterSpacing: 0.4,
                                textShadow: '0 1px 2px rgba(0,0,0,0.65)',
                                userSelect: 'none',
                              }}
                            >
                              <span
                                aria-hidden="true"
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'flex-end',
                                  gap: 1,
                                  height: 10,
                                }}
                              >
                                {[4, 7, 5].map((barHeight, index) => (
                                  <span
                                    key={index}
                                    style={{
                                      width: 2,
                                      height: barHeight,
                                      borderRadius: 1,
                                      background: '#9ca3af',
                                      opacity: 0.8 - index * 0.15,
                                    }}
                                  />
                                ))}
                              </span>
                              <span style={{ fontSize: 10 }}>≈ no waveform</span>
                            </div>
                          )}
                          {waveformHover?.clipId === clip.clip_id ? (
                            <div
                              style={{
                                position: 'absolute',
                                top: 4,
                                left: clamp((waveformHover.ratio * Math.max(4, width)) - 18, 4, Math.max(4, width - 44)),
                                padding: '1px 4px',
                                borderRadius: 3,
                                background: 'rgba(0, 0, 0, 0.72)',
                                color: '#d1d5db',
                                fontSize: 9,
                                lineHeight: 1.2,
                                pointerEvents: 'none',
                              }}
                            >
                              {waveformHover.timeSec.toFixed(2)}s
                            </div>
                          ) : null}
                        </div>
                      ) : null}

                      {width > 40 ? (
                        <span
                          style={{
                            position: 'relative',
                            zIndex: 2,
                            fontSize: 10,
                            fontWeight: 500,
                            color: '#fff',
                            textOverflow: 'ellipsis',
                            overflow: 'hidden',
                            whiteSpace: 'nowrap',
                            textShadow: '0 1px 3px rgba(0,0,0,0.8)',
                          }}
                        >
                          {basename(clip.source_path)}
                        </span>
                      ) : null}

                      {width > 60 ? (
                        <span
                          style={{
                            position: 'relative',
                            zIndex: 2,
                            fontSize: 9,
                            color: '#999',
                            textShadow: '0 1px 2px rgba(0,0,0,0.6)',
                          }}
                        >
                          {durationSec.toFixed(1)}s
                          {syncInfo?.method ? <span style={{ color: '#22c55e', marginLeft: 4 }}>⟲ {syncInfo.method}</span> : null}
                        </span>
                      ) : null}
                    </div>
                  );
                })}

                {markers.map((marker) => {
                  const markerX = marker.start_sec * zoom - scrollLeft;
                  const markerWidth = Math.max(2, (marker.end_sec - marker.start_sec) * zoom);
                  if (markerX + markerWidth < 0 || markerX > containerWidth) {
                    return null;
                  }
                  const color = MARKER_COLORS[marker.kind] || '#888';
                  return (
                    <div
                      key={`${lane.lane_id}_${marker.marker_id}`}
                      style={{
                        ...MARKER_STYLE,
                        left: markerX,
                        width: markerWidth,
                        height: trackHeight - 6,
                        top: 3,
                        background: `${color}33`,
                        borderLeft: `2px solid ${color}`,
                      }}
                      title={`${marker.kind}: ${marker.text || ''} (${marker.start_sec.toFixed(1)}s)`}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {markerDraft ? (
        <div
          data-testid="cut-marker-draft"
          style={{
            position: 'absolute',
            left: markerDraft.x,
            top: markerDraft.y,
            width: 220,
            padding: 10,
            background: '#0b0b0b',
            border: '1px solid #2a2a2a',
            borderRadius: 6,
            boxShadow: '0 12px 30px rgba(0,0,0,0.45)',
            zIndex: 160,
          }}
          onMouseDown={(event) => event.stopPropagation()}
        >
          <div style={{ fontSize: 10, color: '#777', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Marker @ {markerDraft.timeSec.toFixed(2)}s
          </div>
          <select
            value={markerDraft.kind}
            onChange={(event) => setMarkerDraft((current) => (current ? { ...current, kind: event.target.value as MarkerKind } : current))}
            style={{ width: '100%', marginBottom: 8, background: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, padding: '6px 8px' }}
          >
            <option value="favorite">favorite</option>
            <option value="comment">comment</option>
            <option value="cam">cam</option>
            <option value="insight">insight</option>
          </select>
          <input
            value={markerDraft.text}
            placeholder="marker text"
            onChange={(event) => setMarkerDraft((current) => (current ? { ...current, text: event.target.value } : current))}
            style={{ width: '100%', marginBottom: 8, background: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, padding: '6px 8px' }}
          />
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button
              style={{ background: 'transparent', color: '#777', border: '1px solid #333', borderRadius: 4, padding: '5px 8px', cursor: 'pointer' }}
              onClick={() => setMarkerDraft(null)}
            >
              Cancel
            </button>
            <button
              data-testid="cut-marker-draft-create"
              style={{ background: '#1d4ed8', color: '#fff', border: '1px solid #2563eb', borderRadius: 4, padding: '5px 10px', cursor: 'pointer' }}
              onClick={() => {
                if (!markerDraft) return;
                const draft = markerDraft;
                setMarkerDraft(null);
                void createMarker({
                  timeSec: draft.timeSec,
                  mediaPath: draft.mediaPath,
                  kind: draft.kind,
                  text: draft.text,
                });
              }}
            >
              Create Marker
            </button>
          </div>
        </div>
      ) : null}

      {contextMenu ? (
        <div
          data-testid="cut-clip-context-menu"
          style={{
            position: 'absolute',
            left: contextMenu.x,
            top: contextMenu.y,
            width: 180,
            background: '#0b0b0b',
            border: '1px solid #2a2a2a',
            borderRadius: 6,
            boxShadow: '0 12px 30px rgba(0,0,0,0.45)',
            padding: 6,
            zIndex: 170,
          }}
          onMouseDown={(event) => event.stopPropagation()}
        >
          {[
            {
              label: 'Set as Active',
              action: () => {
                setActiveMedia(contextMenu.clip.source_path);
                setSelectedClip(contextMenu.clip.clip_id);
                setContextMenu(null);
              },
            },
            {
              label: 'Add Marker Here',
              action: () => {
                setContextMenu(null);
                setMarkerDraft({
                  x: contextMenu.x + 16,
                  y: contextMenu.y + 16,
                  timeSec: contextMenu.clip.start_sec,
                  mediaPath: contextMenu.clip.source_path,
                  kind: 'favorite',
                  text: '',
                });
              },
            },
            {
              label: 'Apply Sync',
              disabled: !syncSurface.some((item) => item.source_path === contextMenu.clip.source_path && item.recommended_method),
              action: () => {
                const clip = contextMenu.clip;
                setContextMenu(null);
                void applySuggestedSync(clip);
              },
            },
            {
              label: 'Remove Clip',
              action: () => {
                const clipId = contextMenu.clip.clip_id;
                setContextMenu(null);
                void removeClip(clipId);
              },
            },
            {
              label: 'Export XML',
              action: () => {
                setContextMenu(null);
                void exportPremiereXml();
              },
            },
          ].map((item) => (
            <button
              key={item.label}
              disabled={Boolean(item.disabled)}
              onClick={item.action}
              style={{
                width: '100%',
                textAlign: 'left',
                background: 'transparent',
                color: item.disabled ? '#555' : '#ccc',
                border: 'none',
                borderRadius: 4,
                padding: '7px 8px',
                cursor: item.disabled ? 'default' : 'pointer',
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}

      {dragState && clipOverlayTop !== null ? (
        <div
          style={{
            ...CLIP_STYLE,
            left: dragState.startSec * zoom - scrollLeft + LANE_HEADER_WIDTH,
            top: clipOverlayTop,
            width: Math.max(4, dragState.durationSec * zoom),
            height: trackHeight - 6,
            bottom: 'auto',
            background: 'rgba(37, 99, 235, 0.28)',
            border: '1px dashed rgba(96, 165, 250, 0.95)',
            pointerEvents: 'none',
            zIndex: 120,
            cursor: dragState.mode === 'move' ? 'grabbing' : 'ew-resize',
          }}
        >
          <span style={{ position: 'relative', zIndex: 1, color: '#fff', textShadow: '0 1px 3px rgba(0,0,0,0.8)' }}>
            {basename(dragState.sourcePath)}
          </span>
        </div>
      ) : null}

      {playheadX > LANE_HEADER_WIDTH - 5 && playheadX < containerWidth + 5 ? (
        <div style={{ ...PLAYHEAD_STYLE, left: playheadX }}>
          <div style={PLAYHEAD_HEAD} />
        </div>
      ) : null}

      {!lanes.length ? (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#333',
            fontSize: 13,
            textAlign: 'center',
            userSelect: 'none',
            pointerEvents: 'none',
          }}
        >
          Bootstrap a project to see timeline
        </div>
      ) : null}
    </div>
  );
}
