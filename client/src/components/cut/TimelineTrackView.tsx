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
import { useCutEditorStore, interpolateKeyframes, type TimelineClip, type TimelineLane } from '../../store/useCutEditorStore';
import { useTimelineInstanceStore } from '../../store/useTimelineInstanceStore';
import { useSelectionStore } from '../../store/useSelectionStore';
import WaveformCanvas from './WaveformCanvas';
import StereoWaveformCanvas from './StereoWaveformCanvas';
import TimecodeField from './TimecodeField';
import { IconFilmStrip, IconSpeaker, IconCamera, IconLink, IconLock, IconUnlock, IconMute, IconSolo, IconTarget, IconEye, IconEyeOff } from './icons/CutIcons';
import { EFFECT_APPLY_MAP } from './EffectsPanel';
import ThumbnailStrip from './ThumbnailStrip';
import TrackResizeHandle from './TrackResizeHandle';

const LANE_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  video_main: { label: 'V1', color: '#999', icon: <IconFilmStrip size={12} color="#888" /> },
  audio_sync: { label: 'A1', color: '#888', icon: <IconSpeaker size={12} color="#888" /> },
  take_alt_y: { label: 'V2', color: '#888', icon: <IconCamera size={12} color="#888" /> },
  take_alt_z: { label: 'V3', color: '#777', icon: <IconCamera size={12} color="#888" /> },
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
// MARKER_192.3: Increased from 76 to 100 — buttons were overlapping.
// See: RECON_UI_LAYOUT_GROK_2026-03-19.md §5
const LANE_HEADER_WIDTH = 100;
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
  // MARKER_W5.TC: marginLeft removed — ruler now inside flex row with TC header
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

// MARKER_192.3 + MARKER_COMPACT: Lane header — 100px, compact icon layout
const LANE_HEADER: CSSProperties = {
  width: LANE_HEADER_WIDTH,
  flexShrink: 0,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 1,
  padding: '2px 3px',
  borderRight: '1px solid #222',
  background: '#080808',
  userSelect: 'none',
  overflow: 'hidden',
};

const LANE_CONTENT: CSSProperties = {
  flex: 1,
  position: 'relative',
  overflow: 'hidden',
};

// MARKER_W6.TOOL-SM: cursor set dynamically based on activeTool (not hardcoded)
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
  transition: 'border-color 0.1s',
};

// MARKER_C11: Playhead style — active (bright white) vs inactive (dim grey)
function playheadStyle(isActive: boolean): CSSProperties {
  return {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: isActive ? 1 : 1,
    background: isActive ? '#fff' : '#666',
    zIndex: 100,
    pointerEvents: 'none',
  };
}

function playheadHeadStyle(isActive: boolean): CSSProperties {
  const color = isActive ? '#fff' : '#666';
  return {
    position: 'absolute',
    top: -2,
    left: -5,
    width: 0,
    height: 0,
    borderLeft: '5px solid transparent',
    borderRight: '5px solid transparent',
    borderTop: `6px solid ${color}`,
  };
}

// Legacy const refs for backward compat
const PLAYHEAD_STYLE = playheadStyle(true);
const PLAYHEAD_HEAD = playheadHeadStyle(true);

const MARKER_STYLE: CSSProperties = {
  position: 'absolute',
  top: 0,
  width: 2,
  zIndex: 50,
  borderRadius: 1,
  pointerEvents: 'none',
};

const MARKER_COLORS: Record<string, string> = {
  // Editorial markers
  favorite: '#f59e0b',     // amber — positive / keep
  negative: '#ef4444',     // red — anti-favorite / reject
  comment: '#3b82f6',      // blue — annotation (markers exempt from monochrome rule)
  cam: '#a855f7',          // purple — camera note
  insight: '#22c55e',      // green — AI insight
  chat: '#94a3b8',         // slate — chat reference
  // PULSE BPM markers
  bpm_audio: '#22c55e',    // green — audio beats
  bpm_visual: '#4a9eff',   // blue — visual cut points (markers exempt from no-color rule)
  bpm_script: '#ffffff',   // white — script scene transitions
  sync_point: '#f59e0b',   // orange — multi-source sync
};

// MARKER_A3.1: BPM marker kinds — rendered as thin lines, not blocks
const BPM_MARKER_KINDS = new Set(['bpm_audio', 'bpm_visual', 'bpm_script', 'sync_point']);

// MARKER_192.3: 2x2 grid for track buttons — no overlap at 100px width
const TRACK_BUTTON_ROW: CSSProperties = {
  display: 'flex',
  gap: 1,
};

// MARKER_COMPACT: Track buttons — compact for 100px header
const TRACK_BUTTON: CSSProperties = {
  width: 16,
  height: 14,
  borderRadius: 2,
  border: '1px solid #333',
  background: '#111',
  color: '#888',
  fontSize: 7,
  fontWeight: 700,
  lineHeight: '12px',
  padding: 0,
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
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

// MARKER_W5.TRIM: Extended drag modes (FCP7 Ch.44)
type ClipDragMode = 'move' | 'trim_left' | 'trim_right' | 'slip' | 'slide' | 'ripple_left' | 'ripple_right' | 'roll';

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
  // MARKER_W5.TRIM: Additional state for trim tools
  sourceIn?: number;          // slip: tracks source_in offset
  originalSourceIn?: number;  // slip: original source_in for delta calc
  neighborLeft?: { clipId: string; startSec: number; durationSec: number } | null;
  neighborRight?: { clipId: string; startSec: number; durationSec: number } | null;
};

// MARKER_DND: Drop zone state for drag-to-timeline (FCP7 insert/overwrite zones)
type DropZoneState = {
  laneId: string;
  mode: 'insert' | 'overwrite';
  timeSec: number;  // where the drop would land on timeline
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

// MARKER_SHUTTLE_INDICATOR: Visual shuttle speed readout (FCP7 Ch.8)
function ShuttleIndicator() {
  const speed = useCutEditorStore((s) => s.shuttleSpeed);
  if (speed === 0) return null;
  const label = speed > 0 ? `${speed}x` : `${speed}x`;
  const arrow = speed > 0 ? '\u25B6' : '\u25C0';
  return (
    <span style={{
      fontSize: 8, fontWeight: 700, fontFamily: 'monospace',
      color: Math.abs(speed) > 2 ? '#ccc' : '#888',
      marginLeft: 4, whiteSpace: 'nowrap',
    }} data-testid="shuttle-speed-indicator">
      {arrow}{label}
    </span>
  );
}

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
            background: tick.major ? '#666' : '#444',
          }}
        >
          {tick.label ? (
            <span
              data-ruler-label="1"
              style={{
                position: 'absolute',
                bottom: tick.major ? 15 : 9,
                left: 2,
                fontSize: 10,
                fontFamily: '"JetBrains Mono", "SF Mono", monospace',
                color: tick.major ? '#bbb' : '#777',
                whiteSpace: 'nowrap',
                userSelect: 'none',
                pointerEvents: 'none',
                zIndex: 1,
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

// MARKER_C11: Props interface for multi-instance support (Phase 198)
interface TimelineTrackViewProps {
  /** If provided, reads data from useTimelineInstanceStore instead of legacy flat store.
   *  When omitted, falls back to useCutEditorStore (backward-compatible). */
  timelineId?: string;
}

export default function TimelineTrackView({ timelineId: timelineIdProp }: TimelineTrackViewProps = {}) {
  // MARKER_C11: Multi-instance support — resolve instance data
  const instanceStoreTimeline = useTimelineInstanceStore((s) =>
    timelineIdProp ? s.timelines.get(timelineIdProp) : undefined
  );
  const activeTimelineId = useTimelineInstanceStore((s) => s.activeTimelineId);
  const setActiveTimeline = useTimelineInstanceStore((s) => s.setActiveTimeline);
  const isMultiInstance = !!timelineIdProp && !!instanceStoreTimeline;
  const isActive = isMultiInstance ? activeTimelineId === timelineIdProp : true;

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
  const [dropZone, setDropZone] = useState<DropZoneState | null>(null);
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
  const trackHeights = useCutEditorStore((state) => state.trackHeights);
  const setTrackHeightForLane = useCutEditorStore((state) => state.setTrackHeightForLane);
  const currentTime = useCutEditorStore((state) => state.currentTime);
  const duration = useCutEditorStore((state) => state.duration);
  const isPlaying = useCutEditorStore((state) => state.isPlaying);
  const selectedClipId = useSelectionStore((state) => state.selectedClipId);
  const selectedClipIds = useSelectionStore((state) => state.selectedClipIds); // MARKER_W3.7: multi-select highlight
  const hoveredClipId = useCutEditorStore((state) => state.hoveredClipId);
  const sandboxRoot = useCutEditorStore((state) => state.sandboxRoot);
  const projectId = useCutEditorStore((state) => state.projectId);
  const timelineId = useCutEditorStore((state) => state.timelineId);
  const refreshProjectState = useCutEditorStore((state) => state.refreshProjectState);
  const activeMediaPath = useCutEditorStore((state) => state.sourceMediaPath);
  const syncSurface = useCutEditorStore((state) => state.syncSurface);
  // MARKER_DISPLAY-CTRL: display control flags
  const showClipNames = useCutEditorStore((state) => state.showClipNames);
  const showClipBorders = useCutEditorStore((state) => state.showClipBorders);
  const showWaveforms = useCutEditorStore((state) => state.showWaveforms);
  const showThumbnails = useCutEditorStore((state) => state.showThumbnails);
  const showThroughEdits = useCutEditorStore((state) => state.showThroughEdits);
  const showVideoTracks = useCutEditorStore((state) => state.showVideoTracks);
  const showAudioTracks = useCutEditorStore((state) => state.showAudioTracks);
  const markIn = useCutEditorStore((state) => state.markIn);
  const markOut = useCutEditorStore((state) => state.markOut);
  const seek = useCutEditorStore((state) => state.seek);
  const setScrollLeft = useCutEditorStore((state) => state.setScrollLeft);
  const setTrackHeight = useCutEditorStore((state) => state.setTrackHeight);
  const mutedLanes = useCutEditorStore((state) => state.mutedLanes ?? new Set<string>());
  const soloLanes = useCutEditorStore((state) => state.soloLanes ?? new Set<string>());
  const lockedLanes = useCutEditorStore((state) => state.lockedLanes ?? new Set<string>());
  const targetedLanes = useCutEditorStore((state) => state.targetedLanes ?? new Set<string>());
  const laneVolumes = useCutEditorStore((state) => state.laneVolumes);
  const snapEnabled = useCutEditorStore((state) => state.snapEnabled);
  const toggleMute = useCutEditorStore((state) => state.toggleMute);
  const toggleSolo = useCutEditorStore((state) => state.toggleSolo);
  const toggleLock = useCutEditorStore((state) => state.toggleLock);
  const toggleTarget = useCutEditorStore((state) => state.toggleTarget);
  const toggleVisibility = useCutEditorStore((state) => state.toggleVisibility);
  const hiddenLanes = useCutEditorStore((state) => state.hiddenLanes ?? new Set<string>());
  const setLaneVolume = useCutEditorStore((state) => state.setLaneVolume);
  const setSelectedClip = useSelectionStore((state) => state.setSelectedClip);
  // MARKER_W5.TC: Project timecode settings for editable TC field
  const projectFramerate = useCutEditorStore((state) => state.projectFramerate);
  const projectDropFrame = useCutEditorStore((state) => state.dropFrame);
  // MARKER_MULTICAM_TL: Multicam angle lookup for timeline badges
  const multicamAngles = useCutEditorStore((state) => state.multicamAngles);
  const multicamMode = useCutEditorStore((state) => state.multicamMode);
  // MARKER_W3.6: Tool State Machine — cursor changes based on active tool
  const activeTool = useCutEditorStore((state) => state.activeTool);
  // MARKER_W6.TOOL-SM: Cursor maps per context
  // Lane background cursor (when hovering empty space)
  const TOOL_CURSOR: Record<string, string> = {
    selection: 'default', razor: 'crosshair', hand: 'grab', zoom: 'zoom-in',
    slip: 'ew-resize', slide: 'col-resize', ripple: 'w-resize', roll: 'col-resize',
  };
  // Clip body cursor (when hovering over a clip)
  const CLIP_CURSOR: Record<string, string> = {
    selection: 'grab', razor: 'crosshair', hand: 'grab', zoom: 'zoom-in',
    slip: 'ew-resize', slide: 'col-resize', ripple: 'w-resize', roll: 'col-resize',
  };
  const clipCursor = CLIP_CURSOR[activeTool] || 'grab';
  // MARKER_TRIM.CURSOR: Edge cursor reflects active tool (FCP7 Ch.56-60)
  const EDGE_CURSOR: Record<string, string> = {
    selection: 'ew-resize', razor: 'crosshair', hand: 'ew-resize', zoom: 'ew-resize',
    slip: 'ew-resize', slide: 'ew-resize', ripple: 'w-resize', roll: 'col-resize',
  };
  const edgeCursor = EDGE_CURSOR[activeTool] || 'ew-resize';
  // MARKER_DUAL-VIDEO: Timeline clip click → updates activeMedia (legacy) but NOT source monitor
  const setActiveMedia = useCutEditorStore((state) => state.setActiveMedia);
  const setSourceMedia = useCutEditorStore((state) => state.setSourceMedia);
  const setHoveredClip = useCutEditorStore((state) => state.setHoveredClip);

  // ─── MARKER_W6.STORE: Multi-instance read migration (Phase 1) ──────
  // When timelineId prop is provided AND instance exists in the new store,
  // READS come from instance store. WRITES still go to singleton (Phase 2).
  // This enables multiple independent TimelineTrackView instances.
  const inst = instanceStoreTimeline;
  const updateInstance = useTimelineInstanceStore((s) => s.updateTimeline);

  // MARKER_W6.STORE: Override read data from instance store when available
  // Phase 1: redirect reads only — singleton writes untouched
  const effectiveLanes = isMultiInstance && inst ? inst.lanes : lanes;
  const effectiveWaveforms = isMultiInstance && inst ? inst.waveforms : waveforms;
  const effectiveZoom = isMultiInstance && inst ? inst.zoom : zoom;
  const effectiveScrollLeft = isMultiInstance && inst ? inst.scrollX : scrollLeft;
  const effectiveTrackHeight = isMultiInstance && inst ? inst.trackHeight : trackHeight;
  const effectiveCurrentTime = isMultiInstance && inst ? inst.playheadPosition : currentTime;
  const effectiveDuration = isMultiInstance && inst ? inst.duration : duration;
  const effectiveMarkIn = isMultiInstance && inst ? inst.markIn : markIn;
  const effectiveMarkOut = isMultiInstance && inst ? inst.markOut : markOut;
  const effectiveSelectedClipIds = isMultiInstance && inst
    ? new Set(inst.selectedClipIds)
    : selectedClipIds;

  // Click handler: activate this timeline if not active
  const handleTimelineActivate = useCallback(() => {
    if (isMultiInstance && !isActive && timelineIdProp) {
      setActiveTimeline(timelineIdProp);
    }
  }, [isMultiInstance, isActive, timelineIdProp, setActiveTimeline]);
  // ─── END MARKER_W6.STORE ──────────────────────────────────────────

  // MARKER_W6.STORE: Refs sync from effective values (instance when available, else singleton)
  useEffect(() => {
    zoomRef.current = effectiveZoom;
  }, [effectiveZoom]);
  useEffect(() => {
    scrollLeftRef.current = effectiveScrollLeft;
  }, [effectiveScrollLeft]);
  useEffect(() => {
    trackHeightRef.current = effectiveTrackHeight;
  }, [effectiveTrackHeight]);
  useEffect(() => {
    currentTimeRef.current = effectiveCurrentTime;
  }, [effectiveCurrentTime]);
  useEffect(() => {
    markInRef.current = effectiveMarkIn;
  }, [effectiveMarkIn]);
  useEffect(() => {
    markOutRef.current = effectiveMarkOut;
  }, [effectiveMarkOut]);
  useEffect(() => {
    // MARKER_173.18.NLE.BEAT_SNAP: music_sync markers enter the generic snap target pool as beat cues.
    // MARKER_A3.6: Snap to both start_sec AND end_sec of markers
    markerTimesRef.current = markers.flatMap((marker) => {
      const times = [marker.start_sec];
      if (marker.end_sec > marker.start_sec + 0.01) times.push(marker.end_sec);
      return times;
    });
  }, [markers]);
  useEffect(() => {
    snapEnabledRef.current = snapEnabled;
  }, [snapEnabled]);
  useEffect(() => {
    sessionRef.current = { sandboxRoot, projectId, timelineId, refreshProjectState };
  }, [sandboxRoot, projectId, timelineId, refreshProjectState]);

  // MARKER_W6.RULER-FIX: Reactive container width via ResizeObserver
  const [containerWidth, setContainerWidth] = useState(800);
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    setContainerWidth(el.clientWidth);
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const waveformMap = useMemo(() => {
    const map = new Map<string, number[]>();
    for (const item of effectiveWaveforms) {
      if (item.waveform_bins?.length) {
        map.set(item.source_path, item.waveform_bins);
      }
    }
    return map;
  }, [effectiveWaveforms]);

  // MARKER_B31: Stereo waveform lookup (L/R channel data)
  const stereoWaveformMap = useMemo(() => {
    const map = new Map<string, { left: number[]; right: number[] }>();
    for (const item of effectiveWaveforms) {
      if (item.waveform_bins_left?.length && item.waveform_bins_right?.length) {
        map.set(item.source_path, { left: item.waveform_bins_left, right: item.waveform_bins_right });
      }
    }
    return map;
  }, [effectiveWaveforms]);

  // MARKER_DISPLAY-CTRL: Filter lanes based on show video/audio track toggles
  // MARKER_W6.STORE: Use effective lanes for display
  const isVideoLane = (t: string) => t.startsWith('video') || t.startsWith('take_alt');
  const isAudioLane = (t: string) => t.startsWith('audio');
  const filteredLanes = effectiveLanes.filter((lane) => {
    if (!showVideoTracks && isVideoLane(lane.lane_type)) return false;
    if (!showAudioTracks && isAudioLane(lane.lane_type)) return false;
    return true;
  });
  const displayLanes = filteredLanes.length
    ? filteredLanes
    : [
        { lane_id: 'v1_empty', lane_type: 'video_main', clips: [] },
        { lane_id: 'a1_empty', lane_type: 'audio_sync', clips: [] },
      ];

  useEffect(() => {
    displayLanesRef.current = displayLanes;
  }, [displayLanes]);

  // MARKER_FCP7.EDIT2: Compute linked clip IDs — clips sharing scene_id across video + audio lanes
  // FCP7 p.592: "The names of the linked clip items are underlined"
  const linkedClipIds = useMemo(() => {
    const sceneToLaneTypes = new Map<string, Set<string>>();
    const sceneToClipIds = new Map<string, string[]>();
    for (const lane of displayLanes) {
      for (const clip of lane.clips) {
        const key = clip.scene_id || clip.source_path.replace(/\.[^.]+$/, '');
        if (!sceneToLaneTypes.has(key)) sceneToLaneTypes.set(key, new Set());
        sceneToLaneTypes.get(key)!.add(lane.lane_type);
        if (!sceneToClipIds.has(key)) sceneToClipIds.set(key, []);
        sceneToClipIds.get(key)!.push(clip.clip_id);
      }
    }
    const linked = new Set<string>();
    for (const [key, laneTypes] of sceneToLaneTypes) {
      // Linked = appears in at least 2 different lane types (e.g., video + audio)
      if (laneTypes.size >= 2) {
        for (const id of sceneToClipIds.get(key) || []) linked.add(id);
      }
    }
    return linked;
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

  // MARKER_UNDO-FIX-23: Delegates to store applyTimelineOps for consistent error handling + toast
  const applyTimelineOps = useCallback(async (ops: Array<Record<string, unknown>>, opts?: { skipRefresh?: boolean }) => {
    await useCutEditorStore.getState().applyTimelineOps(ops, opts);
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

  // MARKER_W5.TRIM: Helper to find neighboring clips in a lane
  const findNeighbors = useCallback(
    (clipId: string, laneId: string) => {
      const lane = displayLanesRef.current.find((l) => l.lane_id === laneId);
      if (!lane) return { left: null, right: null };
      const sorted = [...lane.clips].sort((a, b) => a.start_sec - b.start_sec);
      const idx = sorted.findIndex((c) => c.clip_id === clipId);
      const left = idx > 0 ? sorted[idx - 1] : null;
      const right = idx < sorted.length - 1 ? sorted[idx + 1] : null;
      return {
        left: left ? { clipId: left.clip_id, startSec: left.start_sec, durationSec: left.duration_sec } : null,
        right: right ? { clipId: right.clip_id, startSec: right.start_sec, durationSec: right.duration_sec } : null,
      };
    },
    [],
  );

  const beginClipInteraction = useCallback(
    (clip: TimelineClip, laneId: string, mode: ClipDragMode, event: MouseEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();

      // MARKER_EDIT1_FIX: Razor split moved to handleClipClick (local-first approach).
      // Previously here: beginClipInteraction fired applyTimelineOps + refreshProjectState
      // on mousedown, causing race with handleClipClick's local split on click.
      if (activeTool === 'razor' && mode === 'move') {
        return; // Let click handler (handleClipClick) do the local-first split
      }

      setSelectedClip(clip.clip_id);
      setActiveMedia(clip.source_path);
      const pointerTime = timeFromTrackClientX(event.clientX);
      const startSec = roundTimeline(clip.start_sec);
      const durationSec = roundTimeline(Math.max(MIN_CLIP_DURATION_SEC, clip.duration_sec));

      // MARKER_W5.TRIM: Determine effective drag mode from activeTool
      // MARKER_TRIM.EDGE: Tool override applies to edges too (FCP7 Ch.56-60)
      // Clicking an edge with ripple tool → ripple trim, not basic trim.
      let effectiveMode = mode;
      if (mode === 'move') {
        switch (activeTool) {
          case 'slip': effectiveMode = 'slip'; break;
          case 'slide': effectiveMode = 'slide'; break;
          case 'ripple': {
            const clipCenter = startSec + durationSec / 2;
            effectiveMode = pointerTime < clipCenter ? 'ripple_left' : 'ripple_right';
            break;
          }
          case 'roll': effectiveMode = 'roll'; break;
          default: break;
        }
      } else if (mode === 'trim_left' || mode === 'trim_right') {
        // Edge interactions: tool overrides basic trim
        switch (activeTool) {
          case 'ripple':
            effectiveMode = mode === 'trim_left' ? 'ripple_left' : 'ripple_right';
            break;
          case 'roll': effectiveMode = 'roll'; break;
          default: break; // selection/razor/hand/zoom → keep basic trim
        }
      }

      const neighbors = findNeighbors(clip.clip_id, laneId);

      setDragState({
        mode: effectiveMode,
        clipId: clip.clip_id,
        sourcePath: clip.source_path,
        laneId,
        originalLaneId: laneId,
        startSec,
        durationSec,
        originalStartSec: startSec,
        originalDurationSec: durationSec,
        grabOffsetSec: clamp(pointerTime - clip.start_sec, 0, clip.duration_sec),
        sourceIn: clip.source_in ?? 0,
        originalSourceIn: clip.source_in ?? 0,
        neighborLeft: neighbors.left,
        neighborRight: neighbors.right,
      });
    },
    [activeTool, applyTimelineOps, findNeighbors, setActiveMedia, setSelectedClip, timeFromTrackClientX]
  );

  const handleWheel = useCallback(
    (event: ReactWheelEvent) => {
      const containerRect = containerRef.current?.getBoundingClientRect();
      const localX = containerRect ? (event.clientX - containerRect.left) : Number.POSITIVE_INFINITY;

      // Shift+Wheel over lane headers → adjust track height
      if (event.shiftKey && localX <= LANE_HEADER_WIDTH) {
        setTrackHeight(trackHeight - event.deltaY * 0.08);
        event.preventDefault();
        return;
      }

      // MARKER_A3.3: Pinch-to-zoom (ctrlKey = trackpad pinch) + Cmd+Wheel zoom
      // Zooms centered on cursor position (not left edge)
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault();
        const zoomRef = useCutEditorStore.getState().zoom;
        const scrollRef = useCutEditorStore.getState().scrollLeft;
        // Cursor time before zoom
        const cursorLocalX = localX - LANE_HEADER_WIDTH;
        const cursorTime = (cursorLocalX + scrollRef) / zoomRef;
        // Apply zoom delta
        const factor = event.deltaY > 0 ? 0.92 : 1.08; // smoother steps
        const newZoom = Math.max(10, Math.min(500, zoomRef * factor));
        // Adjust scroll so cursor stays over same time position
        const newScroll = Math.max(0, cursorTime * newZoom - cursorLocalX);
        useCutEditorStore.getState().setZoom(newZoom);
        useCutEditorStore.getState().setScrollLeft(newScroll);
        return;
      }

      // Horizontal scroll (Shift+Wheel or horizontal trackpad swipe)
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

  // MARKER_DND: Drag-to-Timeline handlers (FCP7 insert/overwrite zones)
  const handleLaneDragOver = useCallback(
    (event: React.DragEvent<HTMLDivElement>, laneId: string, laneEl: HTMLDivElement) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = 'copy';
      const rect = laneEl.getBoundingClientRect();
      const relY = event.clientY - rect.top;
      const laneH = rect.height;
      const mode: 'insert' | 'overwrite' = relY < laneH / 3 ? 'insert' : 'overwrite';
      const timeSec = timeFromTrackClientX(event.clientX);
      setDropZone({ laneId, mode, timeSec });
    },
    [timeFromTrackClientX]
  );

  const handleLaneDragLeave = useCallback(() => {
    setDropZone(null);
  }, []);

  // MARKER_DND_STORE + B50: Drop handler — media paths OR effects
  const handleLaneDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>, laneId: string, laneEl: HTMLDivElement) => {
      event.preventDefault();
      const rect = laneEl.getBoundingClientRect();
      const relY = event.clientY - rect.top;
      const laneH = rect.height;
      const mode: 'insert' | 'overwrite' = relY < laneH / 3 ? 'insert' : 'overwrite';
      const dropTime = timeFromTrackClientX(event.clientX);

      // MARKER_B50: Check for effect drop (application/x-cut-effect from EffectsPanel)
      const effectData = event.dataTransfer.getData('application/x-cut-effect');
      if (effectData) {
        try {
          const { id: effectId } = JSON.parse(effectData) as { id: string; name: string };
          const params = EFFECT_APPLY_MAP[effectId];
          if (params) {
            // Find clip under drop cursor
            const store = useCutEditorStore.getState();
            const lane = store.lanes.find((l) => l.lane_id === laneId);
            const clip = lane?.clips.find(
              (c) => dropTime >= c.start_sec && dropTime <= c.start_sec + c.duration_sec,
            );
            if (clip) {
              store.setClipEffects(clip.clip_id, params);
            }
          }
        } catch { /* malformed effect data */ }
        setDropZone(null);
        return;
      }

      // Read dragged media paths — prefer JSON array, fallback to single path
      let paths: string[] = [];
      const jsonPaths = event.dataTransfer.getData('text/cut-media-paths');
      if (jsonPaths) {
        try { paths = JSON.parse(jsonPaths); } catch { /* malformed JSON */ }
      }
      if (!paths.length) {
        const singlePath = event.dataTransfer.getData('text/cut-media-path')
          || event.dataTransfer.getData('text/plain')
          || '';
        if (singlePath) paths = [singlePath];
      }

      if (paths.length) {
        useCutEditorStore.getState().dropMediaOnTimeline(paths, laneId, dropTime, mode);
      }

      setDropZone(null);
    },
    [timeFromTrackClientX]
  );

  // MARKER_W3.6: Razor tool — click on clip splits at click position
  // MARKER_W3.7: Multi-select — Cmd+click toggle, Shift+click range
  const handleClipClick = useCallback(
    (clipId: string, sourcePath: string, event: MouseEvent) => {
      event.stopPropagation();
      setContextMenu(null);

      // W3.6 + MARKER_QA.W5.3: Razor tool — split clip locally at click position
      if (activeTool === 'razor') {
        const splitTime = timeFromTrackClientX(event.clientX);
        const s = useCutEditorStore.getState();
        const newLanes = s.lanes.map(lane => ({
          ...lane,
          clips: lane.clips.flatMap(c => {
            if (c.clip_id === clipId && splitTime > c.start_sec + 0.01 && splitTime < c.start_sec + c.duration_sec - 0.01) {
              const leftDur = splitTime - c.start_sec;
              return [
                { ...c, clip_id: `${c.clip_id}_L`, duration_sec: leftDur },
                { ...c, clip_id: `${c.clip_id}_R`, start_sec: splitTime, duration_sec: c.duration_sec - leftDur },
              ];
            }
            return [c];
          }),
        }));
        s.setLanes(newLanes);
        // Also notify backend asynchronously (skipRefresh: local state is already updated)
        applyTimelineOps([{ op: 'split_at', clip_id: clipId, split_sec: splitTime }], { skipRefresh: true }).catch(() => {});
        return;
      }

      // W3.7: Multi-select with Cmd+click
      if (event.metaKey || event.ctrlKey) {
        useSelectionStore.getState().toggleClipSelection(clipId);
        return;
      }

      // W3.7: Range select with Shift+click
      if (event.shiftKey) {
        const selState = useSelectionStore.getState();
        const lastSelected = selState.selectedClipId;
        if (lastSelected) {
          // Collect all clips in timeline order
          const editorState = useCutEditorStore.getState();
          const allClips: { clipId: string; time: number }[] = [];
          for (const lane of editorState.lanes) {
            for (const clip of lane.clips) {
              allClips.push({ clipId: clip.clip_id, time: clip.start_sec ?? clip.timeline_in ?? 0 });
            }
          }
          allClips.sort((a, b) => a.time - b.time);
          const idxA = allClips.findIndex((c) => c.clipId === lastSelected);
          const idxB = allClips.findIndex((c) => c.clipId === clipId);
          if (idxA >= 0 && idxB >= 0) {
            const [lo, hi] = idxA < idxB ? [idxA, idxB] : [idxB, idxA];
            const newIds = new Set(selState.selectedClipIds);
            for (let i = lo; i <= hi; i++) newIds.add(allClips[i].clipId);
            useSelectionStore.setState({ selectedClipIds: newIds });
            return;
          }
        }
        // Fallback: just add to selection
        useSelectionStore.getState().toggleClipSelection(clipId);
        return;
      }

      // Default: single select
      setSelectedClip(clipId);
      setActiveMedia(sourcePath);

      // MARKER_TL4: Linked selection — also select synced audio/video on adjacent lane
      // Checks: linked_to field, sync.linked_clip_id, or matching scene_id
      const editorState = useCutEditorStore.getState();
      const selLinked = useSelectionStore.getState().linkedSelection;
      if (selLinked) {
        const ids = new Set([clipId]);
        let clickedClip: TimelineClip | undefined;
        for (const lane of editorState.lanes) {
          const found = lane.clips.find((c) => c.clip_id === clipId);
          if (found) { clickedClip = found; break; }
        }
        if (clickedClip) {
          for (const lane of editorState.lanes) {
            for (const c of lane.clips) {
              if (c.clip_id === clipId) continue;
              // Match by linked_to field (explicit link)
              if ((c as any).linked_to === clipId || (clickedClip as any).linked_to === c.clip_id) { ids.add(c.clip_id); continue; }
              // Match by sync.linked_clip_id (legacy)
              if (c.sync?.linked_clip_id === clipId || clickedClip.sync?.linked_clip_id === c.clip_id) { ids.add(c.clip_id); continue; }
              // Match by scene_id (same scene = linked)
              if (clickedClip.scene_id && c.scene_id === clickedClip.scene_id) { ids.add(c.clip_id); }
            }
          }
        }
        if (ids.size > 1) {
          useSelectionStore.setState({ selectedClipIds: ids });
        }
      }
    },
    [activeTool, applyTimelineOps, setActiveMedia, setSelectedClip, timeFromTrackClientX]
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

      // MARKER_W5.TRIM: Slip — move source content inside clip boundaries
      if (dragState.mode === 'slip') {
        const pointerTime = timeFromTrackClientX(event.clientX);
        setDragState((current) => {
          if (!current) return current;
          const delta = pointerTime - (current.originalStartSec + current.grabOffsetSec);
          const newSourceIn = roundTimeline(Math.max(0, (current.originalSourceIn ?? 0) + delta));
          return { ...current, sourceIn: newSourceIn };
        });
        return;
      }

      // MARKER_W5.TRIM: Slide — move clip between neighbors
      if (dragState.mode === 'slide') {
        const pointerTime = timeFromTrackClientX(event.clientX);
        setDragState((current) => {
          if (!current) return current;
          const rawStart = roundTimeline(Math.max(0, pointerTime - current.grabOffsetSec));
          // Constrain to neighbor boundaries
          const minStart = current.neighborLeft
            ? current.neighborLeft.startSec
            : 0;
          const maxStart = current.neighborRight
            ? current.neighborRight.startSec + current.neighborRight.durationSec - current.durationSec
            : rawStart;
          const clampedStart = clamp(rawStart, minStart, Math.max(minStart, maxStart));
          return { ...current, startSec: clampedStart };
        });
        return;
      }

      // MARKER_W5.TRIM: Ripple — extend/shorten edge, shift everything after
      if (dragState.mode === 'ripple_left' || dragState.mode === 'ripple_right') {
        const pointerTime = timeFromTrackClientX(event.clientX);
        setDragState((current) => {
          if (!current) return current;
          if (current.mode === 'ripple_left') {
            const clipEnd = current.originalStartSec + current.originalDurationSec;
            const nextStart = clamp(pointerTime, 0, clipEnd - MIN_CLIP_DURATION_SEC);
            return {
              ...current,
              startSec: roundTimeline(nextStart),
              durationSec: roundTimeline(Math.max(MIN_CLIP_DURATION_SEC, clipEnd - nextStart)),
            };
          }
          // ripple_right
          const nextEnd = Math.max(current.originalStartSec + MIN_CLIP_DURATION_SEC, pointerTime);
          return {
            ...current,
            durationSec: roundTimeline(Math.max(MIN_CLIP_DURATION_SEC, nextEnd - current.originalStartSec)),
          };
        });
        return;
      }

      // MARKER_W5.TRIM: Roll — move edit point between two clips
      if (dragState.mode === 'roll') {
        const pointerTime = timeFromTrackClientX(event.clientX);
        setDragState((current) => {
          if (!current) return current;
          // Roll adjusts the boundary between this clip and its left neighbor
          // or this clip and its right neighbor based on grab position
          const editingLeftEdge = current.grabOffsetSec < current.originalDurationSec / 2;
          if (editingLeftEdge && current.neighborLeft) {
            // Move left edge: shorten/extend left neighbor's end + this clip's start
            const leftStart = current.neighborLeft.startSec;
            const minBound = leftStart + MIN_CLIP_DURATION_SEC;
            const maxBound = current.originalStartSec + current.originalDurationSec - MIN_CLIP_DURATION_SEC;
            const newEditPoint = clamp(pointerTime, minBound, maxBound);
            return {
              ...current,
              startSec: roundTimeline(newEditPoint),
              durationSec: roundTimeline(current.originalStartSec + current.originalDurationSec - newEditPoint),
            };
          } else if (!editingLeftEdge && current.neighborRight) {
            // Move right edge: extend/shorten this clip's end + right neighbor's start
            const minBound = current.originalStartSec + MIN_CLIP_DURATION_SEC;
            const maxBound = current.neighborRight.startSec + current.neighborRight.durationSec - MIN_CLIP_DURATION_SEC;
            const newEditPoint = clamp(pointerTime, minBound, maxBound);
            return {
              ...current,
              durationSec: roundTimeline(newEditPoint - current.originalStartSec),
            };
          }
          return current;
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
      if (!activeDrag) {
        setDragState(null);
        return;
      }

      // MARKER_TDD-TRIM: Local-first optimistic update — commit drag result to lanes
      // before clearing dragState, so the visual change persists even if backend is unavailable.
      // Handles all drag modes: move, trim, ripple, roll, slip, slide.
      const store = useCutEditorStore.getState();
      const hasMoved = Math.abs(activeDrag.startSec - activeDrag.originalStartSec) > 0.001
        || Math.abs(activeDrag.durationSec - activeDrag.originalDurationSec) > 0.001;

      if (hasMoved || activeDrag.mode === 'slip') {
        const updatedLanes = store.lanes.map((lane) => {
          if (lane.lane_id !== activeDrag.originalLaneId && activeDrag.mode !== 'move') return lane;
          return {
            ...lane,
            clips: lane.clips.map((c) => {
              // Primary clip — always update position/duration
              if (c.clip_id === activeDrag.clipId) {
                const updated = { ...c, start_sec: activeDrag.startSec, duration_sec: activeDrag.durationSec };
                // Slip: update source_in (content scrolled within clip)
                if (activeDrag.mode === 'slip' && activeDrag.sourceIn !== undefined) {
                  updated.source_in = activeDrag.sourceIn;
                }
                return updated;
              }

              // Ripple: shift subsequent clips by delta
              if ((activeDrag.mode === 'ripple_left' || activeDrag.mode === 'ripple_right') && lane.lane_id === activeDrag.originalLaneId) {
                const delta = (activeDrag.startSec + activeDrag.durationSec) - (activeDrag.originalStartSec + activeDrag.originalDurationSec);
                if (Math.abs(delta) > 0.001 && c.start_sec >= activeDrag.originalStartSec + activeDrag.originalDurationSec) {
                  return { ...c, start_sec: Math.max(0, c.start_sec + delta) };
                }
              }

              // Roll: adjust neighbor clip at the edit point
              if (activeDrag.mode === 'roll') {
                if (activeDrag.neighborLeft && c.clip_id === activeDrag.neighborLeft.clipId) {
                  const newLeftDur = activeDrag.startSec - activeDrag.neighborLeft.startSec;
                  if (newLeftDur > 0) return { ...c, duration_sec: newLeftDur };
                }
                if (activeDrag.neighborRight && c.clip_id === activeDrag.neighborRight.clipId) {
                  const newEnd = activeDrag.startSec + activeDrag.durationSec;
                  const rightOrigEnd = activeDrag.neighborRight.startSec + activeDrag.neighborRight.durationSec;
                  const newRightDur = rightOrigEnd - newEnd;
                  if (newRightDur > 0) return { ...c, start_sec: newEnd, duration_sec: newRightDur };
                }
              }

              // Slide: adjust neighbor durations to accommodate moved clip
              if (activeDrag.mode === 'slide') {
                if (activeDrag.neighborLeft && c.clip_id === activeDrag.neighborLeft.clipId) {
                  const newLeftDur = activeDrag.startSec - activeDrag.neighborLeft.startSec;
                  if (newLeftDur > 0) return { ...c, duration_sec: newLeftDur };
                }
                if (activeDrag.neighborRight && c.clip_id === activeDrag.neighborRight.clipId) {
                  const clipEnd = activeDrag.startSec + activeDrag.durationSec;
                  const rightOrigEnd = activeDrag.neighborRight.startSec + activeDrag.neighborRight.durationSec;
                  const newRightDur = rightOrigEnd - clipEnd;
                  if (newRightDur > 0) return { ...c, start_sec: clipEnd, duration_sec: newRightDur };
                }
              }

              // Move to different lane
              if (activeDrag.mode === 'move' && activeDrag.laneId !== activeDrag.originalLaneId) {
                // handled by backend op
              }

              return c;
            }),
          };
        });
        store.setLanes(updatedLanes);
      }
      setDragState(null);

      const ops: Array<Record<string, unknown>> = [];
      if (
        activeDrag.mode === 'move'
        && (activeDrag.laneId !== activeDrag.originalLaneId || Math.abs(activeDrag.startSec - activeDrag.originalStartSec) > 0.001)
      ) {
        // MARKER_A2.4: Multi-clip drag — move all selected clips with same delta
        const multiIds = useSelectionStore.getState().selectedClipIds;
        const delta = activeDrag.startSec - activeDrag.originalStartSec;
        const laneDelta = activeDrag.laneId !== activeDrag.originalLaneId;

        if (multiIds.size > 1 && multiIds.has(activeDrag.clipId) && !laneDelta) {
          // Multi-clip move: apply same time delta to all selected clips
          for (const lane of displayLanesRef.current) {
            for (const clip of lane.clips) {
              if (multiIds.has(clip.clip_id)) {
                ops.push({
                  op: 'move_clip',
                  clip_id: clip.clip_id,
                  lane_id: lane.lane_id,
                  start_sec: roundTimeline(Math.max(0, clip.start_sec + delta)),
                });
              }
            }
          }
        } else {
          // Single clip move (original behavior)
          ops.push({
            op: 'move_clip',
            clip_id: activeDrag.clipId,
            lane_id: activeDrag.laneId,
            start_sec: activeDrag.startSec,
          });
        }
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

      // MARKER_W5.TRIM: Slip — update source_in only
      if (activeDrag.mode === 'slip' && activeDrag.sourceIn !== activeDrag.originalSourceIn) {
        ops.push({
          op: 'slip_clip',
          clip_id: activeDrag.clipId,
          source_in: activeDrag.sourceIn,
        });
      }

      // MARKER_W5.TRIM: Slide — move clip, adjust neighbors
      if (activeDrag.mode === 'slide' && Math.abs(activeDrag.startSec - activeDrag.originalStartSec) > 0.001) {
        const delta = activeDrag.startSec - activeDrag.originalStartSec;
        ops.push({ op: 'move_clip', clip_id: activeDrag.clipId, lane_id: activeDrag.laneId, start_sec: activeDrag.startSec });
        // Adjust left neighbor's duration (extend/shrink right edge)
        if (activeDrag.neighborLeft) {
          ops.push({
            op: 'trim_clip',
            clip_id: activeDrag.neighborLeft.clipId,
            duration_sec: roundTimeline(activeDrag.neighborLeft.durationSec + delta),
          });
        }
        // Adjust right neighbor's start and duration
        if (activeDrag.neighborRight) {
          const clipEnd = activeDrag.startSec + activeDrag.durationSec;
          const rightOrigEnd = activeDrag.neighborRight.startSec + activeDrag.neighborRight.durationSec;
          ops.push({
            op: 'trim_clip',
            clip_id: activeDrag.neighborRight.clipId,
            start_sec: clipEnd,
            duration_sec: roundTimeline(rightOrigEnd - clipEnd),
          });
        }
      }

      // MARKER_W5.TRIM: Ripple — trim edge + shift everything after
      if (
        (activeDrag.mode === 'ripple_left' || activeDrag.mode === 'ripple_right')
        && (
          Math.abs(activeDrag.startSec - activeDrag.originalStartSec) > 0.001
          || Math.abs(activeDrag.durationSec - activeDrag.originalDurationSec) > 0.001
        )
      ) {
        const rippleOp: Record<string, unknown> = {
          op: 'ripple_trim',
          clip_id: activeDrag.clipId,
          start_sec: activeDrag.startSec,
          duration_sec: activeDrag.durationSec,
        };
        ops.push(rippleOp);
      }

      // MARKER_W5.TRIM: Roll — adjust edit point between two clips
      if (activeDrag.mode === 'roll') {
        const editingLeftEdge = activeDrag.grabOffsetSec < activeDrag.originalDurationSec / 2;
        if (editingLeftEdge && activeDrag.neighborLeft) {
          const newLeftDur = roundTimeline(activeDrag.startSec - activeDrag.neighborLeft.startSec);
          if (Math.abs(newLeftDur - activeDrag.neighborLeft.durationSec) > 0.001) {
            ops.push({
              op: 'trim_clip',
              clip_id: activeDrag.neighborLeft.clipId,
              duration_sec: newLeftDur,
            });
            ops.push({
              op: 'trim_clip',
              clip_id: activeDrag.clipId,
              start_sec: activeDrag.startSec,
              duration_sec: activeDrag.durationSec,
            });
          }
        } else if (!editingLeftEdge && activeDrag.neighborRight) {
          const newEnd = activeDrag.startSec + activeDrag.durationSec;
          if (Math.abs(activeDrag.durationSec - activeDrag.originalDurationSec) > 0.001) {
            ops.push({
              op: 'trim_clip',
              clip_id: activeDrag.clipId,
              duration_sec: activeDrag.durationSec,
            });
            ops.push({
              op: 'trim_clip',
              clip_id: activeDrag.neighborRight.clipId,
              start_sec: newEnd,
              duration_sec: roundTimeline(activeDrag.neighborRight.startSec + activeDrag.neighborRight.durationSec - newEnd),
            });
          }
        }
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
    const viewportWidth = Math.max(containerWidth - LANE_HEADER_WIDTH, 0);
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
    <div ref={containerRef} data-testid="cut-timeline-track-view" style={{ ...CONTAINER_STYLE, cursor: TOOL_CURSOR[activeTool] || 'default' }} onWheel={handleWheel} onMouseDown={handleTimelineActivate}>
      {/* MARKER_W5.TC: Ruler row — editable timecode field + time ruler */}
      <div style={{ display: 'flex', flexDirection: 'row', flexShrink: 0, height: RULER_HEIGHT }}>
        {/* Timecode field in lane header area (FCP7 Current Timecode) */}
        <div style={{
          width: LANE_HEADER_WIDTH,
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#080808',
          borderRight: '1px solid #222',
          borderBottom: '1px solid #333',
        }}>
          <TimecodeField
            seconds={currentTime}
            fps={projectFramerate}
            dropFrame={projectDropFrame}
            onSeek={seek}
            testId="cut-timeline-timecode"
          />
          {/* MARKER_SHUTTLE_INDICATOR: Show shuttle speed when JKL active */}
          <ShuttleIndicator />
        </div>
        <div style={{ flex: 1, position: 'relative' }}>
          <TimeRuler
            zoom={zoom}
            scrollLeft={scrollLeft}
            totalWidth={containerWidth - LANE_HEADER_WIDTH}
            rulerRef={rulerRef}
            onSeek={seek}
            onScrubStart={handleRulerScrubStart}
            onDoubleClick={handleRulerDoubleClick}
          />
        </div>
      </div>

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
            borderTop: '8px solid #ccc',
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
            borderTop: '8px solid #888',
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
            borderLeft: '1px dashed rgba(200, 200, 200, 0.8)',
            boxShadow: '0 0 10px rgba(200, 200, 200, 0.2)',
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
          const isHidden = hiddenLanes.has(lane.lane_id);
          const laneDimmed = isHidden || isMuted || (hasSolo && !isSolo);
          const laneH = trackHeights[lane.lane_id] ?? trackHeight;
          return (
            <div key={lane.lane_id} data-testid={`cut-timeline-lane-${lane.lane_id}`} style={{ ...LANE_ROW, height: laneH, opacity: laneDimmed ? 0.3 : 1, position: 'relative' }}>
              <div style={LANE_HEADER}>
                {/* MARKER_COMPACT: Label row — icon + label + eye toggle inline */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%', justifyContent: 'center' }}>
                  <span style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>{config.icon}</span>
                  <span style={{ fontSize: 10, fontWeight: 600, color: config.color, flexShrink: 0 }}>{config.label}</span>
                  <button
                    style={{
                      ...TRACK_BUTTON,
                      width: 14, height: 12,
                      background: isHidden ? '#333' : 'transparent',
                      border: 'none',
                      marginLeft: 'auto',
                    }}
                    title={isHidden ? 'Show track' : 'Hide track'}
                    aria-label={isHidden ? 'Show visibility' : 'Hide visibility'}
                    data-testid={`cut-lane-visibility-${lane.lane_id}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      toggleVisibility(lane.lane_id);
                    }}
                  >
                    {isHidden
                      ? <IconEyeOff size={9} color="#888" />
                      : <IconEye size={9} color="#444" />
                    }
                  </button>
                </div>
                {/* MARKER_COMPACT: 2×2 button grid — [target lock] [solo mute] */}
                <div style={TRACK_BUTTON_ROW}>
                  <button
                    style={{
                      ...TRACK_BUTTON,
                      background: targetedLanes.has(lane.lane_id) ? '#999' : '#111',
                      borderColor: targetedLanes.has(lane.lane_id) ? '#999' : '#333',
                    }}
                    title="Target lane"
                    onClick={(event) => { event.stopPropagation(); toggleTarget(lane.lane_id); }}
                  >
                    <IconTarget size={9} color={targetedLanes.has(lane.lane_id) ? '#111' : '#555'} />
                  </button>
                  <button
                    style={{
                      ...TRACK_BUTTON,
                      background: lockedLanes.has(lane.lane_id) ? '#888' : '#111',
                      borderColor: lockedLanes.has(lane.lane_id) ? '#888' : '#333',
                    }}
                    title="Lock lane"
                    onClick={(event) => { event.stopPropagation(); toggleLock(lane.lane_id); }}
                  >
                    {lockedLanes.has(lane.lane_id)
                      ? <IconLock size={9} color="#111" />
                      : <IconUnlock size={9} color="#555" />
                    }
                  </button>
                  <button
                    style={{
                      ...TRACK_BUTTON,
                      background: soloLanes.has(lane.lane_id) ? '#aaa' : '#111',
                      borderColor: soloLanes.has(lane.lane_id) ? '#aaa' : '#333',
                    }}
                    title="Solo"
                    onClick={(event) => { event.stopPropagation(); toggleSolo(lane.lane_id); }}
                  >
                    <IconSolo size={9} color={soloLanes.has(lane.lane_id) ? '#111' : '#888'} />
                  </button>
                  <button
                    style={{
                      ...TRACK_BUTTON,
                      background: mutedLanes.has(lane.lane_id) ? '#888' : '#111',
                      borderColor: mutedLanes.has(lane.lane_id) ? '#888' : '#333',
                    }}
                    title="Mute"
                    onClick={(event) => { event.stopPropagation(); toggleMute(lane.lane_id); }}
                  >
                    <IconMute size={9} color={mutedLanes.has(lane.lane_id) ? '#111' : '#888'} />
                  </button>
                </div>
              </div>

              <div
                data-testid={`cut-timeline-lane-${lane.lane_id}`}
                style={{ ...LANE_CONTENT, cursor: TOOL_CURSOR[activeTool] || 'default' }}
                onClick={handleTrackClick}
                onDoubleClick={(event) => handleTrackDoubleClick(event, lane.lane_id)}
                onDragOver={(event) => handleLaneDragOver(event, lane.lane_id, event.currentTarget)}
                onDragLeave={handleLaneDragLeave}
                onDrop={(event) => handleLaneDrop(event, lane.lane_id, event.currentTarget)}
              >
                {/* MARKER_QA.DND1: FCP7 Ch.35 p.517 drop zone indicators (insert upper 1/3, overwrite lower 2/3) */}
                <div data-drop-zone="insert" style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '33%', pointerEvents: 'none' }} />
                <div data-drop-zone="overwrite" style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: '67%', pointerEvents: 'none' }} />
                {lane.clips.map((clip, clipIdx) => {
                  if (dragState?.clipId === clip.clip_id) {
                    return null;
                  }
                  const { startSec, durationSec } = clipDisplayTime(clip, dragState);
                  const x = startSec * zoom - scrollLeft;
                  const width = durationSec * zoom;
                  if (x + width < 0 || x > containerWidth) {
                    return null;
                  }

                  // MARKER_TL5: Through edit detection — continuous source media across adjacent clips
                  let isThroughEdit = false;
                  if (showThroughEdits && clipIdx > 0) {
                    const prev = lane.clips[clipIdx - 1];
                    if (prev.source_path === clip.source_path) {
                      const prevEnd = (prev.source_in ?? 0) + prev.duration_sec;
                      const curStart = clip.source_in ?? 0;
                      isThroughEdit = Math.abs(prevEnd - curStart) < 0.05; // within ~1 frame tolerance
                    }
                  }

                  const isSelected = selectedClipId === clip.clip_id || selectedClipIds.has(clip.clip_id);
                  const isHovered = hoveredClipId === clip.clip_id;
                  const waveformBins = waveformMap.get(clip.source_path);
                  const stereoData = stereoWaveformMap.get(clip.source_path);
                  const syncInfo = clip.sync;

                  return (
                    <div
                      key={clip.clip_id}
                      data-clip="1"
                      data-testid={`cut-timeline-clip-${clip.clip_id}`}
                      style={{
                        ...CLIP_STYLE,
                        cursor: clipCursor,
                        left: x,
                        width: Math.max(4, width),
                        background: `${config.color}${isSelected ? '44' : isHovered ? '33' : '22'}`,
                        border: showClipBorders
                          ? `1px solid ${isSelected ? config.color : isHovered ? `${config.color}88` : `${config.color}44`}`
                          : isSelected ? `1px solid ${config.color}` : '1px solid transparent',
                      }}
                      onClick={(event) => handleClipClick(clip.clip_id, clip.source_path, event)}
                      onDoubleClick={() => {
                        // MARKER_DBLCLICK_SOURCE: FCP7 — double-click clip opens in Source Monitor
                        const s = useCutEditorStore.getState();
                        s.setSourceMedia(clip.source_path);
                        s.seekSource(clip.source_in ?? 0);
                        s.setFocusedPanel('source');
                      }}
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
                          cursor: edgeCursor,
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
                          cursor: edgeCursor,
                          zIndex: 3,
                        }}
                        onMouseDown={(event) => beginClipInteraction(clip, lane.lane_id, 'trim_right', event)}
                      />

                      {/* MARKER_TL5: Through edit indicator — triangle at left edge (FCP7 Ch.10 p.152) */}
                      {isThroughEdit && (
                        <div style={{
                          position: 'absolute', left: -1, top: '50%', transform: 'translateY(-50%)',
                          width: 0, height: 0, zIndex: 5, pointerEvents: 'none',
                          borderTop: '4px solid transparent',
                          borderBottom: '4px solid transparent',
                          borderLeft: '5px solid rgba(255,255,255,0.6)',
                        }} title="Through edit — continuous media" />
                      )}

                      {/* MARKER_B57: Video filmstrip thumbnails */}
                      {width > 40 && showThumbnails && (lane.lane_type.startsWith('video') || lane.lane_type.startsWith('take_alt')) && (
                        <div
                          data-clip="1"
                          style={{
                            position: 'absolute',
                            inset: 0,
                            zIndex: 0,
                            overflow: 'hidden',
                            opacity: 0.6,
                          }}
                        >
                          <ThumbnailStrip
                            sourcePath={clip.source_path}
                            duration_sec={clip.duration_sec}
                            width={Math.max(4, width) - 2}
                            height={trackHeight - 2}
                            frameCount={Math.max(1, Math.floor((Math.max(4, width) - 2) / (trackHeight * 16 / 9)))}
                            posterTime={clip.source_in ?? 1.0}
                          />
                        </div>
                      )}

                      {width > 20 && showWaveforms ? (
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
                          {stereoData ? (
                            <StereoWaveformCanvas
                              binsLeft={stereoData.left}
                              binsRight={stereoData.right}
                              width={Math.max(4, width) - 2}
                              height={trackHeight - 8}
                              colorLeft={config.color}
                              colorRight={config.color}
                              cursorRatio={waveformHover?.clipId === clip.clip_id ? waveformHover.ratio : null}
                            />
                          ) : waveformBins ? (
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
                                color: '#999',
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
                                      background: '#999',
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
                                color: '#ccc',
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

                      {width > 40 && showClipNames ? (
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
                            // MARKER_FCP7.EDIT2: Underline linked clip names (FCP7 p.592)
                            textDecoration: linkedClipIds.has(clip.clip_id) ? 'underline' : 'none',
                          }}
                        >
                          {basename(clip.source_path)}
                        </span>
                      ) : null}

                      {/* MARKER_MULTICAM_BADGE: Show angle number on multicam clips */}
                      {multicamMode && width > 20 && (() => {
                        const angleIdx = multicamAngles.findIndex((a) => a.source_path === clip.source_path);
                        if (angleIdx < 0) return null;
                        return (
                          <span style={{
                            position: 'absolute', top: 1, right: 2, zIndex: 4,
                            fontSize: 8, fontWeight: 700, fontFamily: 'monospace',
                            color: '#000', background: '#999', borderRadius: 2,
                            padding: '0 3px', lineHeight: '12px',
                          }}>
                            {angleIdx + 1}
                          </span>
                        );
                      })()}

                      {/* MARKER_TRANSITION: Transition overlay at clip's right edge (FCP7 Ch.47) */}
                      {clip.transition_out && width > 10 ? (() => {
                        const tx = clip.transition_out;
                        const txDurPx = tx.duration_sec * zoom;
                        const txWidth = Math.min(txDurPx, width * 0.5);
                        const txLabel = tx.type === 'cross_dissolve' ? 'XD'
                          : tx.type === 'dip_to_black' ? 'DB'
                          : 'W';
                        // MARKER_TR2: Alignment label (S=start, C=center, E=end)
                        const alignLabel = tx.alignment === 'start' ? 'S' : tx.alignment === 'end' ? 'E' : 'C';
                        // MARKER_TR2: Position based on alignment
                        // end-on-edit: right=0 (ends at cut). center: right=-half. start: right=-full.
                        const alignRight = tx.alignment === 'center' ? -txWidth / 2
                          : tx.alignment === 'start' ? -txWidth
                          : 0;
                        const txGrad = tx.type === 'dip_to_black'
                          ? 'linear-gradient(to right, transparent 20%, rgba(0,0,0,0.6))'
                          : tx.type === 'wipe'
                            ? 'linear-gradient(to right, transparent, rgba(255,255,255,0.12) 50%, transparent)'
                            : 'linear-gradient(to right, transparent, rgba(255,255,255,0.15))';
                        return (
                          <div
                            data-testid={`transition-${clip.clip_id}`}
                            style={{
                              position: 'absolute',
                              right: alignRight,
                              top: 0,
                              bottom: 0,
                              width: txWidth,
                              background: txGrad,
                              borderLeft: '1px dashed rgba(255,255,255,0.3)',
                              zIndex: 4,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                            }}
                            title={`${tx.type.replace(/_/g, ' ')} [${alignLabel}] (${tx.duration_sec.toFixed(1)}s) — click=remove, right-click=type, shift+right-click=alignment`}
                            onClick={(event) => {
                              event.stopPropagation();
                              void useCutEditorStore.getState().applyTimelineOps([{
                                op: 'set_transition', clip_id: clip.clip_id, transition: null,
                              }]);
                            }}
                            onContextMenu={(event) => {
                              event.preventDefault();
                              event.stopPropagation();
                              if (event.shiftKey) {
                                // MARKER_TR2: Shift+right-click = cycle alignment (start→center→end)
                                const aligns: Array<'start' | 'center' | 'end'> = ['start', 'center', 'end'];
                                const curIdx = aligns.indexOf(tx.alignment);
                                const nextAlign = aligns[(curIdx + 1) % aligns.length];
                                void useCutEditorStore.getState().applyTimelineOps([{
                                  op: 'set_transition', clip_id: clip.clip_id,
                                  transition: { type: tx.type, duration_sec: tx.duration_sec, alignment: nextAlign },
                                }]);
                              } else {
                                // Right-click = cycle type (cross_dissolve→dip_to_black→wipe)
                                const types: Array<'cross_dissolve' | 'dip_to_black' | 'wipe'> = ['cross_dissolve', 'dip_to_black', 'wipe'];
                                const curIdx = types.indexOf(tx.type);
                                const nextType = types[(curIdx + 1) % types.length];
                                void useCutEditorStore.getState().applyTimelineOps([{
                                  op: 'set_transition', clip_id: clip.clip_id,
                                  transition: { type: nextType, duration_sec: tx.duration_sec, alignment: tx.alignment },
                                }]);
                              }
                            }}
                          >
                            {/* MARKER_TR1: Drag handle on left edge to resize transition duration */}
                            <div
                              style={{
                                position: 'absolute',
                                left: 0,
                                top: 0,
                                bottom: 0,
                                width: 5,
                                cursor: 'ew-resize',
                                zIndex: 5,
                              }}
                              onMouseDown={(event) => {
                                event.stopPropagation();
                                event.preventDefault();
                                const startX = event.clientX;
                                const startDur = tx.duration_sec;
                                const clipId = clip.clip_id;
                                const txType = tx.type;
                                const txAlign = tx.alignment;
                                const zoomVal = zoom;

                                const onMove = (e: MouseEvent) => {
                                  const deltaPx = startX - e.clientX; // drag left = increase duration
                                  const deltaSec = deltaPx / zoomVal;
                                  const newDur = Math.max(0.04, startDur + deltaSec);
                                  // Local-first visual update
                                  const s = useCutEditorStore.getState();
                                  const updated = s.lanes.map((l) => ({
                                    ...l,
                                    clips: l.clips.map((c) =>
                                      c.clip_id === clipId && c.transition_out
                                        ? { ...c, transition_out: { ...c.transition_out, duration_sec: newDur } }
                                        : c
                                    ),
                                  }));
                                  s.setLanes(updated);
                                };

                                const onUp = (e: MouseEvent) => {
                                  window.removeEventListener('mousemove', onMove);
                                  window.removeEventListener('mouseup', onUp);
                                  const deltaPx = startX - e.clientX;
                                  const deltaSec = deltaPx / zoomVal;
                                  const newDur = Math.max(0.04, startDur + deltaSec);
                                  if (Math.abs(newDur - startDur) > 0.01) {
                                    void useCutEditorStore.getState().applyTimelineOps([{
                                      op: 'set_transition', clip_id: clipId,
                                      transition: { type: txType, duration_sec: newDur, alignment: txAlign },
                                    }]);
                                  }
                                };

                                window.addEventListener('mousemove', onMove);
                                window.addEventListener('mouseup', onUp, { once: true });
                              }}
                            />
                            {/* Diamond icon + type label */}
                            {/* MARKER_TR6: Duplicate frame indicator (FCP7 white dots) */}
                            {(() => {
                              const srcDur = (clip as any).source_duration as number | undefined;
                              const srcIn = clip.source_in ?? 0;
                              if (srcDur && srcDur > 0) {
                                const availableHandle = srcDur - srcIn - clip.duration_sec;
                                if (availableHandle < tx.duration_sec) {
                                  return (
                                    <div style={{
                                      position: 'absolute', bottom: 2, left: 0, right: 0,
                                      display: 'flex', justifyContent: 'center', gap: 2, pointerEvents: 'none',
                                    }}>
                                      {[0,1,2].map((i) => (
                                        <div key={i} style={{ width: 3, height: 3, borderRadius: '50%', background: 'rgba(255,255,255,0.8)' }} />
                                      ))}
                                    </div>
                                  );
                                }
                              }
                              return null;
                            })()}
                            {txWidth > 16 ? (
                              <span style={{
                                fontSize: 8,
                                fontWeight: 700,
                                fontFamily: 'system-ui',
                                color: 'rgba(255,255,255,0.7)',
                                textShadow: '0 1px 3px rgba(0,0,0,0.9)',
                                letterSpacing: 0.5,
                                pointerEvents: 'none',
                              }}>
                                {'◆ '}{txLabel}{txWidth > 30 ? ` ${alignLabel}` : ''}
                              </span>
                            ) : null}
                          </div>
                        );
                      })() : null}

                      {/* MARKER_SPEED: Speed indicator badge */}
                      {clip.speed != null && clip.speed !== 1 && width > 30 ? (
                        <span
                          style={{
                            position: 'absolute',
                            top: 2,
                            right: 4,
                            zIndex: 3,
                            fontSize: 8,
                            fontWeight: 700,
                            fontFamily: 'monospace',
                            padding: '0 3px',
                            borderRadius: 2,
                            background: clip.speed < 0
                              ? 'rgba(239, 68, 68, 0.8)'   // red for reverse
                              : clip.speed < 1
                                ? 'rgba(74, 222, 128, 0.7)' // green for slow-mo
                                : 'rgba(251, 146, 60, 0.7)',// orange for speed-up
                            color: '#fff',
                            textShadow: '0 1px 2px rgba(0,0,0,0.8)',
                            lineHeight: '13px',
                          }}
                          title={`Speed: ${Math.abs(clip.speed * 100).toFixed(0)}%${clip.speed < 0 ? ' (reverse)' : ''}`}
                        >
                          {clip.speed < 0 ? '◀ ' : ''}{Math.abs(clip.speed * 100).toFixed(0)}%
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
                          {syncInfo?.method ? <span style={{ color: '#888', marginLeft: 4 }}>⟲ {syncInfo.method}</span> : null}
                        </span>
                      ) : null}

                      {/* MARKER_A3.1-FIX: Clip-bound markers — ALL markers with media_path matching
                          this clip render INSIDE the clip, positioned relative to source media time.
                          Moves WITH the clip. Shifts on slip (source_in changes).
                          Includes: BPM (audio/visual/script/sync), favorite, negative, comment, cam, insight */}
                      {width > 10 ? markers
                        .filter((m) => m.media_path === clip.source_path)
                        .map((m) => {
                          const isBpm = BPM_MARKER_KINDS.has(m.kind);
                          if (isBpm && zoom < 30) return null; // hide BPM at low zoom
                          const clipSourceIn = clip.source_in ?? 0;
                          const relativeTime = m.start_sec - clipSourceIn;
                          if (relativeTime < -0.01 || relativeTime > durationSec + 0.01) return null;
                          const pxFromClipLeft = relativeTime * zoom;
                          if (pxFromClipLeft < 0 || pxFromClipLeft > width) return null;
                          const mColor = MARKER_COLORS[m.kind] || '#888';
                          if (isBpm) {
                            // BPM: thin 1px line, opacity from score
                            return (
                              <div
                                key={`cm_${m.marker_id}`}
                                style={{
                                  position: 'absolute', left: pxFromClipLeft, width: 1,
                                  top: 1, bottom: 1, background: mColor,
                                  opacity: Math.max(0.15, Math.min(0.8, m.score ?? 0.5)),
                                  pointerEvents: 'none', zIndex: 1,
                                }}
                                title={`${m.kind.replace('bpm_', '')} beat (${(m.score ?? 0).toFixed(2)}) @ src ${m.start_sec.toFixed(2)}s`}
                              />
                            );
                          }
                          // Editorial (favorite/negative/comment/cam/insight): 2px line + flag
                          const mEndRel = m.end_sec - clipSourceIn;
                          const mWidth = Math.max(2, (Math.min(mEndRel, durationSec) - relativeTime) * zoom);
                          return (
                            <div
                              key={`cm_${m.marker_id}`}
                              style={{
                                position: 'absolute', left: pxFromClipLeft,
                                width: mWidth, top: 0, height: 4,
                                background: mColor, opacity: 0.9,
                                borderRadius: '0 0 2px 2px',
                                pointerEvents: 'none', zIndex: 5,
                              }}
                              title={`${m.kind}: ${m.text || ''} @ src ${m.start_sec.toFixed(1)}s`}
                            />
                          );
                        }) : null}

                      {/* MARKER_KF-GRAPH: Keyframe interpolation curves (bezier-aware) */}
                      {clip.keyframes && width > 30 ? (() => {
                        const clipH = trackHeights[lane.lane_id] ?? trackHeight;
                        const graphH = clipH - 8;
                        return Object.entries(clip.keyframes).map(([prop, kfs]) => {
                          if (kfs.length < 2) return null;
                          // Sample the interpolation curve at 2px intervals for smooth bezier rendering
                          const step = Math.max(2, width / 200); // max 200 samples
                          const pts: string[] = [];
                          for (let px = 0; px <= width; px += step) {
                            const t = px / zoom; // time in seconds relative to clip start
                            const val = interpolateKeyframes(kfs, t);
                            const y = graphH - (Math.max(0, Math.min(1, val)) * graphH);
                            pts.push(`${px},${y}`);
                          }
                          return (
                            <svg
                              key={`kfline_${prop}`}
                              style={{ position: 'absolute', left: 0, top: 4, width, height: graphH, pointerEvents: 'none', zIndex: 2 }}
                              viewBox={`0 0 ${width} ${graphH}`}
                              preserveAspectRatio="none"
                            >
                              <polyline
                                points={pts.join(' ')}
                                fill="none"
                                stroke="#999"
                                strokeWidth="1"
                                strokeOpacity="0.6"
                                vectorEffect="non-scaling-stroke"
                              />
                            </svg>
                          );
                        });
                      })() : null}

                      {/* MARKER_KF67: Keyframe diamonds inside clip */}
                      {clip.keyframes && width > 20 ? Object.entries(clip.keyframes).flatMap(([prop, kfs]) =>
                        kfs.map((kf) => {
                          const kfPx = kf.time_sec * zoom;
                          if (kfPx < 0 || kfPx > width) return null;
                          return (
                            <div
                              key={`kf_${prop}_${kf.time_sec}`}
                              className="keyframe"
                              data-testid="keyframe"
                              data-property={prop}
                              data-time={kf.time_sec}
                              style={{
                                position: 'absolute',
                                left: kfPx - 3,
                                bottom: 2,
                                width: 6,
                                height: 6,
                                background: '#999',
                                transform: 'rotate(45deg)',
                                zIndex: 6,
                                pointerEvents: 'none',
                                boxShadow: '0 0 3px rgba(0,0,0,0.8)',
                              }}
                              title={`${prop}: ${kf.value.toFixed(2)} @ ${kf.time_sec.toFixed(2)}s (${kf.easing})`}
                            />
                          );
                        })
                      ) : null}
                    </div>
                  );
                })}

                {/* MARKER_FCP7.EDIT3: Through edit indicators — red triangles at edit points
                    between adjacent clips from the same source (FCP7 p.588) */}
                {lane.clips.map((clip, ci) => {
                  if (ci === 0) return null;
                  const prev = lane.clips[ci - 1];
                  // Through edit: adjacent clips from same source (razor split artifacts)
                  const prevBase = prev.source_path.replace(/\.[^.]+$/, '');
                  const curBase = clip.source_path.replace(/\.[^.]+$/, '');
                  if (prevBase !== curBase) return null;
                  const editX = clip.start_sec * zoom - scrollLeft;
                  if (editX < -8 || editX > containerWidth + 8) return null;
                  return (
                    <div
                      key={`through-edit-${prev.clip_id}-${clip.clip_id}`}
                      data-testid="through-edit"
                      className="through-edit"
                      style={{
                        position: 'absolute',
                        left: editX - 4,
                        top: 0,
                        width: 0,
                        height: 0,
                        borderLeft: '4px solid transparent',
                        borderRight: '4px solid transparent',
                        borderTop: '6px solid #888',
                        zIndex: 10,
                        pointerEvents: 'none',
                      }}
                    />
                  );
                })}

                {/* Timeline-level markers — only markers WITHOUT media_path (sequence markers).
                    Clip-bound markers (with media_path) render inside their clip above. */}
                {markers.filter((m) => !m.media_path).map((marker) => {
                  const markerX = marker.start_sec * zoom - scrollLeft;
                  const markerWidth = Math.max(2, (marker.end_sec - marker.start_sec) * zoom);
                  if (markerX + markerWidth < 0 || markerX > containerWidth) return null;
                  const color = MARKER_COLORS[marker.kind] || '#888';
                  return (
                    <div
                      key={`${lane.lane_id}_${marker.marker_id}`}
                      style={{
                        ...MARKER_STYLE,
                        left: markerX,
                        width: markerWidth,
                        height: laneH - 6,
                        top: 3,
                        background: `${color}33`,
                        borderLeft: `2px solid ${color}`,
                      }}
                      title={`${marker.kind}: ${marker.text || ''} (${marker.start_sec.toFixed(1)}s)`}
                    />
                  );
                })}
                {/* MARKER_DND: Drop zone visual indicator */}
                {dropZone && dropZone.laneId === lane.lane_id ? (
                  <>
                    {/* Zone highlight — upper 1/3 insert (green), lower 2/3 overwrite (blue) */}
                    <div style={{
                      position: 'absolute',
                      left: 0,
                      right: 0,
                      top: 0,
                      height: dropZone.mode === 'insert' ? `${Math.round(laneH / 3)}px` : '100%',
                      background: dropZone.mode === 'insert'
                        ? 'rgba(200, 200, 200, 0.10)'
                        : 'rgba(140, 140, 140, 0.10)',
                      borderTop: dropZone.mode === 'insert' ? '2px solid rgba(200, 200, 200, 0.5)' : undefined,
                      borderBottom: dropZone.mode === 'overwrite' ? '2px solid rgba(140, 140, 140, 0.5)' : undefined,
                      pointerEvents: 'none',
                      zIndex: 50,
                    }} />
                    {/* Drop position indicator line */}
                    <div style={{
                      position: 'absolute',
                      left: dropZone.timeSec * zoom - scrollLeft,
                      top: 0,
                      width: 2,
                      height: '100%',
                      background: dropZone.mode === 'insert' ? '#aaa' : '#888',
                      pointerEvents: 'none',
                      zIndex: 51,
                    }} />
                    {/* Mode label */}
                    <div style={{
                      position: 'absolute',
                      left: dropZone.timeSec * zoom - scrollLeft + 6,
                      top: dropZone.mode === 'insert' ? 2 : laneH / 3 + 2,
                      fontSize: 9,
                      fontWeight: 700,
                      fontFamily: 'monospace',
                      color: dropZone.mode === 'insert' ? '#aaa' : '#888',
                      textShadow: '0 1px 3px rgba(0,0,0,0.9)',
                      pointerEvents: 'none',
                      zIndex: 52,
                    }}>
                      {dropZone.mode === 'insert' ? 'INSERT' : 'OVERWRITE'}
                    </div>
                  </>
                ) : null}
              </div>
              {/* MARKER_TIMELINE-1: Drag-to-resize handle (Gamma's TrackResizeHandle) */}
              <TrackResizeHandle
                laneId={lane.lane_id}
                currentHeight={laneH}
                onResize={setTrackHeightForLane}
              />
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
              style={{ background: '#555', color: '#fff', border: '1px solid #666', borderRadius: 4, padding: '5px 10px', cursor: 'pointer' }}
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

      {/* MARKER_W4.1: Expanded CUT context menu with groups, separators, and shortcut hints */}
      {contextMenu ? (
        <div
          data-testid="cut-clip-context-menu"
          style={{
            position: 'absolute',
            left: contextMenu.x,
            top: contextMenu.y,
            width: 220,
            background: '#0b0b0b',
            border: '1px solid #2a2a2a',
            borderRadius: 6,
            boxShadow: '0 12px 30px rgba(0,0,0,0.45)',
            padding: 4,
            zIndex: 170,
          }}
          onMouseDown={(event) => event.stopPropagation()}
        >
          {(() => {
            const hasSync = syncSurface.some((item) => item.source_path === contextMenu.clip.source_path && item.recommended_method);
            const clipId = contextMenu.clip.clip_id;
            const clipPath = contextMenu.clip.source_path;
            const close = () => setContextMenu(null);

            type MenuItem = { label: string; shortcut?: string; action: () => void; disabled?: boolean } | 'separator';

            const items: MenuItem[] = [
              // ── Selection ──
              { label: 'Open in Source Monitor', shortcut: 'Enter', action: () => { setSourceMedia(clipPath); setSelectedClip(clipId); close(); } },
              // MARKER_A13: Match Frame — find source frame under playhead
              { label: 'Match Frame', shortcut: 'F', action: () => {
                const s = useCutEditorStore.getState();
                const clip = contextMenu.clip;
                const sourceOffset = (clip as any).source_in ?? 0;
                const sourceTime = (s.currentTime - clip.start_sec) + sourceOffset;
                s.setSourceMedia(clip.source_path);
                s.setSourceMarkIn(sourceTime);
                s.setFocusedPanel('source');
                close();
              }},
              'separator',
              // ── Clipboard ──
              { label: 'Cut', shortcut: '\u2318X', action: () => { close(); useCutEditorStore.getState().cutClips(); } },
              { label: 'Copy', shortcut: '\u2318C', action: () => { close(); useCutEditorStore.getState().copyClips(); } },
              { label: 'Paste', shortcut: '\u2318V', action: () => { close(); useCutEditorStore.getState().pasteClips('overwrite'); } },
              'separator',
              // ── Edit operations ──
              // MARKER_UNDO-FIX: Split via backend op for undo support
              { label: 'Split at Playhead', shortcut: '\u2318K', action: () => {
                close();
                const s = useCutEditorStore.getState();
                const t = s.currentTime;
                if (t > contextMenu.clip.start_sec && t < contextMenu.clip.start_sec + contextMenu.clip.duration_sec) {
                  void s.applyTimelineOps([{ op: 'split_at', clip_id: clipId, split_sec: t }]);
                }
              }},
              { label: 'Remove Clip', shortcut: 'Del', action: () => { close(); void removeClip(clipId); } },
              { label: 'Ripple Delete', shortcut: '\u21e7Del', action: () => {
                close();
                // MARKER_A13: Proper ripple delete via backend op
                void applyTimelineOps([{ op: 'ripple_delete', clip_id: clipId }]);
              }},
              'separator',
              // ── Markers ──
              { label: 'Add Marker Here', shortcut: 'M', action: () => {
                close();
                setMarkerDraft({
                  x: contextMenu.x + 16, y: contextMenu.y + 16,
                  timeSec: contextMenu.clip.start_sec, mediaPath: clipPath,
                  kind: 'favorite', text: '',
                });
              }},
              { label: 'Add Negative Marker', shortcut: 'N', action: () => {
                close();
                setMarkerDraft({
                  x: contextMenu.x + 16, y: contextMenu.y + 16,
                  timeSec: contextMenu.clip.start_sec, mediaPath: clipPath,
                  kind: 'comment', text: 'NEG',
                });
              }},
              'separator',
              // ── Sync & NLE ──
              { label: 'Apply Sync', disabled: !hasSync, action: () => { close(); void applySuggestedSync(contextMenu.clip); } },
              { label: 'Enable / Disable Clip', action: () => { close(); /* future: toggle clip enabled state */ } },
              'separator',
              // ── Transitions ──
              // MARKER_UNDO-FIX: Transition via backend op for undo support
              { label: contextMenu.clip.transition_out ? 'Remove Transition' : 'Add Cross Dissolve', shortcut: '\u2318T', action: () => {
                close();
                const s = useCutEditorStore.getState();
                void s.applyTimelineOps([{
                  op: 'set_transition', clip_id: clipId,
                  transition: contextMenu.clip.transition_out
                    ? null  // remove
                    : { type: 'cross_dissolve', duration_sec: 1.0, alignment: 'center' },
                }]);
              }},
              'separator',
              // ── Export ──
              { label: 'Export XML', action: () => { close(); void exportPremiereXml(); } },
            ];

            return items.map((item, idx) => {
              if (item === 'separator') {
                return <div key={`sep-${idx}`} style={{ height: 1, background: '#1e1e1e', margin: '3px 6px' }} />;
              }
              return (
                <button
                  key={item.label}
                  disabled={Boolean(item.disabled)}
                  onClick={item.action}
                  style={{
                    width: '100%',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'transparent',
                    color: item.disabled ? '#444' : '#ccc',
                    border: 'none',
                    borderRadius: 4,
                    padding: '6px 8px',
                    cursor: item.disabled ? 'default' : 'pointer',
                    fontSize: 11,
                    fontFamily: 'system-ui',
                  }}
                >
                  <span>{item.label}</span>
                  {item.shortcut ? (
                    <span style={{ color: '#555', fontSize: 10, marginLeft: 12, flexShrink: 0 }}>{item.shortcut}</span>
                  ) : null}
                </button>
              );
            });
          })()}
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
          {/* MARKER_W5.TRIM: Delta indicator for trim tools */}
          {(dragState.mode === 'slip' || dragState.mode === 'slide' || dragState.mode === 'ripple_left' || dragState.mode === 'ripple_right' || dragState.mode === 'roll') ? (() => {
            const fps = projectFramerate || 25;
            let deltaSec = 0;
            let label = '';
            if (dragState.mode === 'slip') {
              deltaSec = (dragState.sourceIn ?? 0) - (dragState.originalSourceIn ?? 0);
              label = 'SLIP';
            } else if (dragState.mode === 'slide') {
              deltaSec = dragState.startSec - dragState.originalStartSec;
              label = 'SLIDE';
            } else if (dragState.mode === 'ripple_left' || dragState.mode === 'ripple_right') {
              deltaSec = dragState.durationSec - dragState.originalDurationSec;
              label = 'RIPPLE';
            } else if (dragState.mode === 'roll') {
              deltaSec = dragState.startSec - dragState.originalStartSec;
              label = 'ROLL';
            }
            const deltaFrames = Math.round(deltaSec * fps);
            const sign = deltaFrames >= 0 ? '+' : '';
            return (
              <span style={{
                position: 'absolute', top: 2, right: 4, zIndex: 2,
                fontSize: 9, fontWeight: 700, fontFamily: 'monospace',
                color: deltaFrames === 0 ? '#888' : (deltaFrames > 0 ? '#bbb' : '#666'),
                textShadow: '0 1px 2px rgba(0,0,0,0.9)',
              }}>
                {label} {sign}{deltaFrames}f
              </span>
            );
          })() : null}
        </div>
      ) : null}

      {/* MARKER_C11: Playhead — active=bright white, inactive=dim grey */}
      {playheadX > LANE_HEADER_WIDTH - 5 && playheadX < containerWidth + 5 ? (
        <div style={{ ...playheadStyle(isActive), left: playheadX }}>
          <div style={playheadHeadStyle(isActive)} />
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
