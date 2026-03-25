/**
 * MARKER_170.NLE.STORE: Shared Zustand store for CUT NLE editor.
 * Bridge between Timeline, VideoPreview, Transport, and Waveform components.
 * Both Opus (timeline) and Codex (player/transport) streams write/read from this.
 */
import { create } from 'zustand';
import { API_BASE } from '../config/api.config';
import { usePanelSyncStore } from './usePanelSyncStore';

// MARKER_KF67: Keyframe system (FCP7 Ch.67)
export type Keyframe = {
  time_sec: number;     // time relative to clip start (0 = clip beginning)
  value: number;        // parameter value at this keypoint
  easing: 'linear' | 'ease_in' | 'ease_out' | 'bezier';
};

// MARKER_KF-BEZIER: Keyframe interpolation with easing curves
// Exported for use in timeline rendering and effect application
export function interpolateKeyframes(keyframes: Keyframe[], timeSec: number): number {
  if (keyframes.length === 0) return 0;
  if (keyframes.length === 1) return keyframes[0].value;

  // Before first keyframe → hold first value
  if (timeSec <= keyframes[0].time_sec) return keyframes[0].value;
  // After last keyframe → hold last value
  if (timeSec >= keyframes[keyframes.length - 1].time_sec) return keyframes[keyframes.length - 1].value;

  // Find surrounding keyframes
  let i = 0;
  while (i < keyframes.length - 1 && keyframes[i + 1].time_sec <= timeSec) i++;
  const kfA = keyframes[i];
  const kfB = keyframes[i + 1];
  const dt = kfB.time_sec - kfA.time_sec;
  if (dt <= 0) return kfA.value;
  const t = (timeSec - kfA.time_sec) / dt; // 0..1 normalized

  // Apply easing (use outgoing easing from kfA)
  let eased: number;
  switch (kfA.easing) {
    case 'ease_in':    eased = t * t; break;
    case 'ease_out':   eased = 1 - (1 - t) * (1 - t); break;
    case 'bezier':     eased = t * t * (3 - 2 * t); break; // smooth step (cubic hermite)
    default:           eased = t; // linear
  }

  return kfA.value + (kfB.value - kfA.value) * eased;
}

// MARKER_W10.6: Per-clip video effects (maps to FFmpeg filter_complex)
export type ClipEffects = {
  brightness: number;   // -1..1, default 0
  contrast: number;     // -1..1, default 0
  saturation: number;   // 0..2, default 1
  blur: number;         // 0..20, default 0 (px radius)
  opacity: number;      // 0..1, default 1
};

export const DEFAULT_CLIP_EFFECTS: ClipEffects = {
  brightness: 0,
  contrast: 0,
  saturation: 1,
  blur: 0,
  opacity: 1,
};

// MARKER_TRANSITION: Transition between clips (FCP7 Ch.47)
export type ClipTransition = {
  type: 'cross_dissolve' | 'dip_to_black' | 'wipe';
  duration_sec: number;    // typically 1.0s (30 frames at 30fps)
  alignment: 'center' | 'start' | 'end';  // relative to edit point
};

export type TimelineClip = {
  clip_id: string;
  scene_id?: string;
  start_sec: number;
  duration_sec: number;
  source_path: string;
  // MARKER_W5.TRIM: source_in tracks where in the source media this clip starts.
  // Required for slip editing — changes source_in without moving clip on timeline.
  source_in?: number;
  // MARKER_SPEED: Clip speed (1.0 = normal, 0.5 = half speed, 2.0 = double, -1 = reverse)
  speed?: number;
  // MARKER_TRANSITION: Outgoing transition (rendered at clip's right edge)
  transition_out?: ClipTransition;
  effects?: ClipEffects;
  // MARKER_KF67: Per-property keyframes (opacity, volume, brightness, etc.)
  keyframes?: Record<string, Keyframe[]>;
  sync?: {
    method?: string;
    offset_sec?: number;
    confidence?: number;
    reference_path?: string;
  };
};

export type TimelineLane = {
  lane_id: string;
  lane_type: string;
  clips: TimelineClip[];
};

export type WaveformItem = {
  item_id: string;
  source_path: string;
  waveform_bins?: number[];
  // MARKER_B31: Stereo waveform data (L/R channel peaks)
  waveform_bins_left?: number[];
  waveform_bins_right?: number[];
  degraded_mode?: boolean;
};

export type ThumbnailItem = {
  item_id: string;
  source_path: string;
  poster_url?: string;
  animated_preview_url_300ms?: string;
  source_url?: string;
  modality?: string;
  duration_sec?: number;
};

export type SyncSurfaceItem = {
  item_id: string;
  source_path: string;
  reference_path: string;
  recommended_method: 'timecode' | 'waveform' | 'meta_sync' | null;
  recommended_offset_sec: number;
  confidence: number;
};

/**
 * MARKER_180.20: Unified TimeMarker — combines editorial + PULSE data.
 *
 * Architecture doc §5.1: "Markers carry both editorial intent (favorite/comment/cam)
 * AND PULSE analysis (camelot_key, energy, pendulum). This unifies the marker
 * system so BPMTrack, Timeline, ScriptPanel, and StorySpace all read one type."
 *
 * Kind types: favorite | comment | cam | insight | chat | bpm_audio | bpm_visual | bpm_script | sync_point
 */
export type MarkerKind =
  | 'favorite' | 'comment' | 'cam' | 'insight' | 'chat'
  | 'bpm_audio' | 'bpm_visual' | 'bpm_script' | 'sync_point';

export type TimeMarker = {
  marker_id: string;
  kind: MarkerKind | string;        // unified kind (editorial + BPM)
  media_path: string;
  start_sec: number;
  end_sec: number;
  text?: string;
  status?: string;                   // 'active' | 'archived'
  score?: number;                    // confidence/priority 0-1
  // MARKER_180.20: PULSE data (optional, filled by analysis)
  camelot_key?: string;              // e.g. "8A"
  energy?: number;                   // 0-1
  pendulum?: number;                 // -1..+1
  scene_id?: string;                 // linked scene
  editorial_intent?: string;         // accent_cut, commentary_hold, etc.
  sync_strength?: number;            // for sync_point kind: 0.67 or 1.0
  sync_sources?: string[];           // for sync_point: ['audio','visual','script']
  source_engine?: string;            // what generated this marker
};

interface CutEditorState {
  // === Playback ===
  currentTime: number;
  isPlaying: boolean;
  playbackRate: number;
  shuttleSpeed: number;  // MARKER_W3.4: JKL progressive shuttle (-8,-4,-2,-1,0,1,2,4,8)
  duration: number;
  // MARKER_B3.2: Keyframe Record Mode (FCP7 automation)
  isRecordMode: boolean;  // true = fader/pan changes auto-write keyframes
  markIn: number | null;      // legacy — mirrors sourceMarkIn for backward compat
  markOut: number | null;     // legacy — mirrors sourceMarkOut for backward compat

  // === MARKER_DUAL-VIDEO: Independent Source Monitor playback state ===
  // Source monitor has its own video element and playback, decoupled from timeline
  sourceCurrentTime: number;
  sourceIsPlaying: boolean;
  sourceDuration: number;

  // === MARKER_W1.4: Separate Source marks and Sequence marks ===
  sourceMarkIn: number | null;     // IN/OUT for raw clip in Source Monitor
  sourceMarkOut: number | null;
  sequenceMarkIn: number | null;   // IN/OUT for timeline position in Program Monitor
  sequenceMarkOut: number | null;

  // === Timeline View ===
  zoom: number; // pixels per second (20 = zoomed out, 200 = zoomed in)
  scrollLeft: number; // horizontal scroll in pixels
  trackHeight: number; // global default height per lane in pixels
  trackHeights: Record<string, number>; // per-lane custom heights (overrides trackHeight)
  trackHeightPreset: 0 | 1 | 2; // 0=S(28), 1=M(56), 2=L(112) — cycled by Shift-T
  mutedLanes: Set<string>;
  soloLanes: Set<string>;
  lockedLanes: Set<string>;      // MARKER_W2.1: locked lanes (no edits allowed)
  targetedLanes: Set<string>;    // MARKER_W2.1: targeted lanes (insert/overwrite destination)
  hiddenLanes: Set<string>;      // MARKER_FIX-TIMELINE-2: hidden lanes (not rendered in playback/export)
  laneVolumes: Record<string, number>;
  lanePans: Record<string, number>;    // MARKER_RECON_21: -1 (full left) to +1 (full right), 0 = center
  snapEnabled: boolean;

  // === Selection ===
  selectedClipId: string | null;
  selectedClipIds: Set<string>;       // MARKER_W3.7: multi-select
  linkedSelection: boolean;           // MARKER_W3.7: click video → also select synced audio
  activeMediaPath: string | null;     // legacy — kept for backward compat, mirrors sourceMediaPath
  hoveredClipId: string | null;

  // === MARKER_W1.2: Panel Focus (Premiere-style panel-scoped hotkeys) ===
  focusedPanel: 'source' | 'program' | 'timeline' | 'project' | 'script' | 'dag' | 'effects' | null;

  // === MARKER_W3.6: Tool State Machine ===
  // MARKER_W5.TRIM: Extended tool state machine (FCP7 Ch.44)
  activeTool: 'selection' | 'razor' | 'hand' | 'zoom' | 'slip' | 'slide' | 'ripple' | 'roll';

  // === MARKER_W1.3: Source/Program feed split ===
  sourceMediaPath: string | null;     // raw clip from DAG/Project click → Source Monitor
  programMediaPath: string | null;    // timeline playback → Program Monitor

  // === MARKER_PW2: Panel Sync Bridge — scene selection from Script/DAG panels ===
  selectedSceneId: string | null;     // active scene for PulseInspector/ClipInspector reactivity

  // === Data (set from CutStandalone projectState) ===
  lanes: TimelineLane[];
  waveforms: WaveformItem[];
  thumbnails: ThumbnailItem[];
  syncSurface: SyncSurfaceItem[];
  markers: TimeMarker[];

  // === MARKER_MULTICAM: Multicam state ===
  multicamId: string | null;            // active multicam clip ID
  multicamAngles: Array<{ source_path: string; label: string; offset_sec: number }>;
  multicamActiveAngle: number;          // currently displayed angle index
  multicamMode: boolean;                // true = multicam viewer active

  // === MARKER_W4.5: Project Settings ===
  projectFramerate: number;             // 23.976 | 24 | 25 | 29.97 | 30 | 50 | 59.94 | 60
  timecodeFormat: 'smpte' | 'milliseconds';  // HH:MM:SS:FF or HH:MM:SS.mmm
  dropFrame: boolean;                   // only for 29.97/59.94
  startTimecode: string;                // e.g. "01:00:00:00"
  audioSampleRate: 48000 | 44100 | 96000;
  audioBitDepth: 16 | 24 | 32;
  showProjectSettings: boolean;         // dialog visibility
  // === MARKER_B3: Sequence Settings — resolution, color space, proxy mode ===
  sequenceResolution: '4K' | '1080p' | '720p' | 'custom';
  sequenceWidth: number;                // custom resolution width
  sequenceHeight: number;               // custom resolution height
  sequenceColorSpace: 'Rec.709' | 'Rec.2020' | 'DCI-P3';
  proxyMode: 'full' | 'proxy' | 'auto';

  // === MARKER_198: Timeline snapshot cache (multi-instance) ===
  timelineSnapshots: Map<string, {
    lanes: TimelineLane[];
    markers: TimeMarker[];
    currentTime: number;
    scrollLeft: number;
    zoom: number;
  }>;

  // === Session / backend wiring ===
  sandboxRoot: string | null;
  projectId: string | null;
  sourcePath: string | null;
  timelineId: string;
  refreshProjectState: (() => Promise<void>) | null;

  // === Multi-timeline tabs (MARKER_170.12 + MARKER_180.14 versioning) ===
  timelineTabs: Array<{
    id: string;
    label: string;
    version?: number;        // MARKER_180.14: auto-increment version
    createdAt?: number;      // ms timestamp
    parentId?: string;       // which timeline this was derived from
    mode?: string;           // 'favorites' | 'script' | 'music' | 'manual'
  }>;
  activeTimelineTabIndex: number;
  /** MARKER_180.14: global version counter for {project}_cut-{NN} naming */
  nextTimelineVersion: number;

  // === MARKER_W5.2: Parallel Timelines (stacked dual view) ===
  parallelTimelineTabIndex: number | null;  // index of the reference (non-active) timeline tab, null = single view

  // === Auto-Montage (MARKER_W5.1) ===
  montageRunning: boolean;
  montageMode: 'favorites' | 'script' | 'music' | null;
  montageProgress: string | null;  // status text: "Analyzing..." / "Building timeline..."
  montageError: string | null;

  // === MARKER_W6.1: Export/Render dialog ===
  showExportDialog: boolean;
  showSpeedControl: boolean;        // MARKER_B11: Speed/Duration dialog
  // === MARKER_TRIM_WINDOW: Trim Edit Window overlay (FCP7 Ch.45-46) ===
  trimEditActive: boolean;          // is overlay open
  trimEditClipId: string | null;    // outgoing clip at edit point
  trimEditPoint: number;            // time of edit point (seconds)
  setTrimEditActive: (active: boolean, clipId?: string | null, editPoint?: number) => void;
  showMatchSequencePopup: boolean;  // MARKER_GAMMA-MATCH: Match Sequence Settings on first clip drop
  pendingMatchClipPath: string | null; // First clip path for probe
  renderProgress: number | null;    // 0-1, null = not rendering
  renderStatus: string | null;      // "Encoding...", "Muxing audio...", etc
  renderError: string | null;

  // === MARKER_W4.3: Save status ===
  saveStatus: 'idle' | 'saving' | 'saved' | 'error';
  lastSavedAt: string | null;     // ISO timestamp from backend
  saveError: string | null;
  hasUnsavedChanges: boolean;

  // === MARKER_W5.2: Monitor display settings ===
  monitorZoom: number;              // 0 = Fit, or 50/75/100/150/200
  showTitleSafe: boolean;           // 4:3 title safe zone overlay
  showActionSafe: boolean;          // 4:3 action safe zone overlay
  showMonitorOverlays: boolean;     // timecode + clip name on monitor

  // === MARKER_CLIPBOARD: Clipboard for Cut/Copy/Paste ===
  clipboard: TimelineClip[];  // copied/cut clips

  // === Media status ===
  mediaError: string | null;
  mediaLoading: boolean;

  // === MARKER_DISPLAY-CTRL: Timeline Display Controls (FCP7 Ch.9 §141-148) ===
  showClipNames: boolean;
  showClipBorders: boolean;
  showWaveforms: boolean;
  showThumbnails: boolean;           // MARKER_B57: filmstrip thumbnails on video clips
  showThroughEdits: boolean;
  showClipLabels: boolean;
  showRubberBand: boolean;
  clipLabelMode: 'name' | 'color' | 'filename';
  timecodeDisplayMode: 'timecode' | 'frames' | 'seconds';
  showVideoTracks: boolean;
  showAudioTracks: boolean;

  // === Layout mode ===
  viewMode: 'nle' | 'debug'; // toggle between NLE and legacy debug view
  sceneGraphSurfaceMode: 'shell_only' | 'nle_ready';

  // === Debug shell state (MARKER_QA.W5.1) ===
  debugProjectState: Record<string, unknown> | null;
  debugStatus: string;
  debugHandlers: Record<string, (() => void | Promise<void>)> | null;
  setDebugProjectState: (state: Record<string, unknown> | null) => void;
  setDebugStatus: (status: string) => void;
  setDebugHandlers: (handlers: Record<string, (() => void | Promise<void>)>) => void;

  // === Actions ===
  play: () => void;
  pause: () => void;
  togglePlay: () => void;
  seek: (time: number) => void;
  setDuration: (d: number) => void;
  // MARKER_DUAL-VIDEO: Source monitor independent playback
  playSource: () => void;
  pauseSource: () => void;
  togglePlaySource: () => void;
  seekSource: (time: number) => void;
  setSourceDuration: (d: number) => void;
  setMarkIn: (t: number | null) => void;
  setMarkOut: (t: number | null) => void;
  // MARKER_W1.4: Separate marks
  setSourceMarkIn: (t: number | null) => void;
  setSourceMarkOut: (t: number | null) => void;
  setSequenceMarkIn: (t: number | null) => void;
  setSequenceMarkOut: (t: number | null) => void;
  setPlaybackRate: (rate: number) => void;
  setShuttleSpeed: (speed: number) => void;  // MARKER_W3.4
  setZoom: (z: number) => void;
  setTrackHeight: (h: number) => void;
  setTrackHeightForLane: (laneId: string, h: number) => void;
  cycleTrackHeights: () => void; // Shift-T: S→M→L→S
  setScrollLeft: (s: number) => void;
  toggleMute: (laneId: string) => void;
  toggleSolo: (laneId: string) => void;
  toggleLock: (laneId: string) => void;      // MARKER_W2.1
  toggleTarget: (laneId: string) => void;    // MARKER_W2.1
  toggleVisibility: (laneId: string) => void; // MARKER_FIX-TIMELINE-2: eye icon
  setLaneVolume: (laneId: string, volume: number) => void;
  setLanePan: (laneId: string, pan: number) => void;  // MARKER_RECON_21
  toggleSnap: () => void;
  setSelectedClip: (id: string | null) => void;
  // MARKER_W3.7: Multi-select
  toggleClipSelection: (id: string) => void;   // Cmd+Click toggle
  selectAllClips: () => void;                   // Cmd+A
  clearSelection: () => void;                   // Escape
  toggleLinkedSelection: () => void;            // linked selection toggle
  // MARKER_CLIPBOARD: Clipboard actions
  copyClips: () => void;                         // Copy selected clips to clipboard
  cutClips: () => void;                          // Cut selected clips (copy + remove)
  pasteClips: (mode: 'overwrite' | 'insert') => void;  // Paste at playhead
  pasteAttributes: () => void;                   // Paste effects from clipboard to selected
  // MARKER_SEQ-MENU: Sequence editing operations
  liftClip: () => void;                          // Remove selected clips, leave gap
  extractClip: () => void;                       // Remove selected clips, close gap (ripple)
  closeGap: () => void;                          // Find and remove gaps in targeted lanes
  extendEdit: () => void;                        // Extend nearest edit to playhead
  // MARKER_TD4: Numeric trim — trim selected clip's nearest edge by N frames
  numericTrimSelected: (frames: number) => void;
  // MARKER_TD2: Asymmetric trim — adjust two adjacent clips independently
  asymmetricTrim: (leftClipId: string, leftDeltaFrames: number, rightClipId: string, rightDeltaFrames: number) => void;
  // MARKER_SPLIT-EDIT: L-cut / J-cut (FCP7 Ch.41)
  splitEditLCut: () => void;                     // Video ends at playhead, audio continues
  splitEditJCut: () => void;                     // Audio starts at playhead, video starts later
  // MARKER_TRANSITION: Default transition (FCP7 Ch.47 ⌘T)
  addDefaultTransition: () => void;              // Add cross dissolve at nearest edit point
  setActiveMedia: (path: string | null) => void;
  // MARKER_W1.3: Source/Program routing
  setSourceMedia: (path: string | null) => void;
  setProgramMedia: (path: string | null) => void;
  setHoveredClip: (id: string | null) => void;
  setMediaError: (err: string | null) => void;
  setMediaLoading: (loading: boolean) => void;
  setViewMode: (mode: 'nle' | 'debug') => void;
  setSceneGraphSurfaceMode: (mode: 'shell_only' | 'nle_ready') => void;
  // MARKER_W1.2: Panel Focus
  setFocusedPanel: (panel: 'source' | 'program' | 'timeline' | 'project' | 'script' | 'dag' | 'effects' | null) => void;
  // MARKER_W3.6: Tool State Machine
  setActiveTool: (tool: 'selection' | 'razor' | 'hand' | 'zoom' | 'slip' | 'slide' | 'ripple' | 'roll') => void;
  // MARKER_W4.5: Project Settings
  setProjectFramerate: (fps: number) => void;
  setTimecodeFormat: (fmt: 'smpte' | 'milliseconds') => void;
  setDropFrame: (on: boolean) => void;
  setStartTimecode: (tc: string) => void;
  setAudioSampleRate: (rate: 48000 | 44100 | 96000) => void;
  setAudioBitDepth: (bits: 16 | 24 | 32) => void;
  setShowProjectSettings: (show: boolean) => void;
  // MARKER_B3: Sequence Settings
  setSequenceResolution: (res: '4K' | '1080p' | '720p' | 'custom') => void;
  setSequenceWidth: (w: number) => void;
  setSequenceHeight: (h: number) => void;
  setSequenceColorSpace: (cs: 'Rec.709' | 'Rec.2020' | 'DCI-P3') => void;
  setProxyMode: (mode: 'full' | 'proxy' | 'auto') => void;
  // MARKER_W6.1: Export/Render
  setShowExportDialog: (show: boolean) => void;
  setShowSpeedControl: (show: boolean) => void;  // MARKER_B11
  setShowMatchSequencePopup: (show: boolean, clipPath?: string) => void;
  setRenderProgress: (p: number | null) => void;
  setRenderStatus: (s: string | null) => void;
  setRenderError: (e: string | null) => void;
  // MARKER_W5.1: Auto-Montage
  setMontageRunning: (running: boolean) => void;
  setMontageMode: (mode: 'favorites' | 'script' | 'music' | null) => void;
  setMontageProgress: (text: string | null) => void;
  setMontageError: (err: string | null) => void;

  // MARKER_W5.2: Monitor display setters
  setMonitorZoom: (zoom: number) => void;
  toggleTitleSafe: () => void;
  toggleActionSafe: () => void;
  toggleMonitorOverlays: () => void;

  // MARKER_W4.3: Save actions
  setSaveStatus: (status: 'idle' | 'saving' | 'saved' | 'error') => void;
  setLastSavedAt: (ts: string | null) => void;
  setSaveError: (err: string | null) => void;
  markUnsavedChanges: () => void;

  // MARKER_W2.2: Source patching — resolve insert/overwrite destinations
  getInsertTargets: () => { videoLaneId: string | null; audioLaneId: string | null };

  // MARKER_DISPLAY-CTRL: Timeline Display Controls toggles
  toggleShowClipNames: () => void;
  toggleShowClipBorders: () => void;
  toggleShowWaveforms: () => void;
  toggleShowThroughEdits: () => void;
  toggleShowClipLabels: () => void;
  toggleShowRubberBand: () => void;
  setClipLabelMode: (mode: 'name' | 'color' | 'filename') => void;
  setTimecodeDisplayMode: (mode: 'timecode' | 'frames' | 'seconds') => void;
  toggleShowVideoTracks: () => void;
  toggleShowAudioTracks: () => void;

  // MARKER_W10.6: Per-clip effects
  setClipEffects: (clipId: string, effects: Partial<ClipEffects>) => void;
  resetClipEffects: (clipId: string) => void;

  // MARKER_KF67: Keyframe actions (FCP7 Ch.67)
  addKeyframe: (clipId: string, property: string, timeSec: number, value: number) => void;
  removeKeyframe: (clipId: string, property: string, timeSec: number) => void;
  getKeyframeTimes: () => number[];  // all keyframe times on timeline (for navigation)
  // MARKER_B3.2: Record mode actions
  toggleRecordMode: () => void;      // Cmd+Shift+K — toggle record mode
  recordPropertyChange: (clipId: string, property: string, value: number) => void;  // auto-keyframe if recording

  // Data setters (called by CutStandalone when projectState updates)
  setLanes: (lanes: TimelineLane[]) => void;
  setWaveforms: (items: WaveformItem[]) => void;
  setThumbnails: (items: ThumbnailItem[]) => void;
  setSyncSurface: (items: SyncSurfaceItem[]) => void;
  setMarkers: (items: TimeMarker[]) => void;
  // MARKER_FCP7_CH38: Marker CRUD
  deleteMarker: (markerId: string) => void;
  updateMarker: (markerId: string, updates: Partial<TimeMarker>) => void;

  // MARKER_MULTICAM: Multicam actions
  setMulticam: (id: string, angles: Array<{ source_path: string; label: string; offset_sec: number }>) => void;
  clearMulticam: () => void;
  setMulticamActiveAngle: (index: number) => void;
  toggleMulticamMode: () => void;
  multicamSwitchAngle: (angleIndex: number) => void;
  createMulticamClip: (sourcePaths: string[], syncMethod?: 'waveform' | 'timecode' | 'marker') => Promise<void>;

  setEditorSession: (session: {
    sandboxRoot?: string | null;
    projectId?: string | null;
    sourcePath?: string | null;
    timelineId?: string;
    refreshProjectState?: (() => Promise<void>) | null;
  }) => void;

  // MARKER_DND_STORE: Drop media from ProjectPanel onto timeline
  dropMediaOnTimeline: (paths: string[], laneId: string, dropTimeSec: number, mode: 'insert' | 'overwrite') => void;

  // MARKER_UNDO-FIX: Shared applyTimelineOps — routes edits through backend undo stack
  applyTimelineOps: (ops: Array<Record<string, unknown>>, opts?: { skipRefresh?: boolean }) => Promise<void>;

  // Multi-timeline tab actions (MARKER_170.12 + MARKER_180.14)
  addTimelineTab: (id: string, label: string) => void;
  removeTimelineTab: (index: number) => void;
  setActiveTimelineTab: (index: number) => void;
  renameTimelineTab: (index: number, label: string) => void;
  /** MARKER_180.14: Create versioned timeline — ALWAYS new, NEVER overwrite (§7.1) */
  createVersionedTimeline: (projectName: string, mode?: string) => string;
  // MARKER_W5.2: Parallel Timelines
  setParallelTimeline: (tabIndex: number | null) => void;
  swapParallelTimeline: () => void;  // swap active ↔ parallel

  // MARKER_198: Snapshot cache for multi-instance timeline swap
  snapshotTimeline: (id: string) => void;
  restoreTimeline: (id: string) => void;

  // MARKER_A4.5: PULSE Auto-Montage — call backend, create new timeline tab with result
  runAutoMontage: (mode: 'favorites' | 'script' | 'music') => Promise<void>;
  // MARKER_A4.8: PULSE Analysis — enrich all scenes with Camelot/McKee/energy metadata
  runPulseAnalysis: () => Promise<void>;
  // PULSE analysis results stored here
  pulseScores: Record<string, { camelot_key?: string; energy?: number; pendulum?: number; dramatic_function?: string }>;
  montageInProgress: boolean;
  pulseAnalysisInProgress: boolean;
}

export const useCutEditorStore = create<CutEditorState>((set, get) => ({
  // Playback defaults
  currentTime: 0,
  isPlaying: false,
  // MARKER_DUAL-VIDEO: Source monitor defaults
  sourceCurrentTime: 0,
  sourceIsPlaying: false,
  sourceDuration: 0,
  playbackRate: 1,
  shuttleSpeed: 0,
  duration: 0,
  isRecordMode: false,  // MARKER_B3.2
  markIn: null,
  markOut: null,

  // MARKER_W1.4: Separate marks
  sourceMarkIn: null,
  sourceMarkOut: null,
  sequenceMarkIn: null,
  sequenceMarkOut: null,

  // Timeline defaults
  zoom: 60, // 60px per second — good starting point
  scrollLeft: 0,
  trackHeight: 56,
  trackHeights: {},
  trackHeightPreset: 1 as 0 | 1 | 2,
  mutedLanes: new Set<string>(),
  soloLanes: new Set<string>(),
  lockedLanes: new Set<string>(),
  targetedLanes: new Set<string>(),
  hiddenLanes: new Set<string>(),
  laneVolumes: {},
  lanePans: {},
  snapEnabled: true,

  // Selection
  selectedClipId: null,
  selectedClipIds: new Set<string>(),
  linkedSelection: true,
  activeMediaPath: null,
  hoveredClipId: null,

  // MARKER_W1.3: Source/Program feed split
  sourceMediaPath: null,
  programMediaPath: null,

  // MARKER_PW2: Panel Sync Bridge
  selectedSceneId: null,

  // MARKER_W1.2: Panel Focus
  // MARKER_GAMMA-29: Default to 'timeline' so hotkeys work on load (was null → silent failures)
  focusedPanel: 'timeline',
  activeTool: 'selection',

  // MARKER_W4.5: Project Settings defaults
  projectFramerate: 25,
  timecodeFormat: 'smpte',
  dropFrame: false,
  startTimecode: '00:00:00:00',
  audioSampleRate: 48000,
  audioBitDepth: 24,
  showProjectSettings: false,
  // MARKER_B3: Sequence Settings defaults
  sequenceResolution: '1080p',
  sequenceWidth: 1920,
  sequenceHeight: 1080,
  sequenceColorSpace: 'Rec.709',
  proxyMode: 'auto',

  // Data
  lanes: [],
  waveforms: [],
  thumbnails: [],
  syncSurface: [],
  markers: [],

  // MARKER_MULTICAM: Multicam defaults
  multicamId: null,
  multicamAngles: [],
  multicamActiveAngle: 0,
  multicamMode: false,

  // MARKER_198: Timeline snapshot cache
  timelineSnapshots: new Map(),

  // Session defaults
  sandboxRoot: null,
  projectId: null,
  sourcePath: null,
  timelineId: 'main',
  refreshProjectState: null,

  // Multi-timeline defaults
  timelineTabs: [{ id: 'main', label: 'Main', version: 0, createdAt: Date.now(), mode: 'manual' }],
  activeTimelineTabIndex: 0,
  nextTimelineVersion: 1,
  parallelTimelineTabIndex: null,

  // MARKER_W6.1: Export/Render
  showExportDialog: false,
  showSpeedControl: false,          // MARKER_B11
  // MARKER_TRIM_WINDOW: Trim Edit Window defaults
  trimEditActive: false,
  trimEditClipId: null,
  trimEditPoint: 0,
  showMatchSequencePopup: false,    // MARKER_GAMMA-MATCH
  pendingMatchClipPath: null,
  renderProgress: null,
  renderStatus: null,
  renderError: null,

  // MARKER_W5.1: Auto-Montage
  montageRunning: false,
  montageMode: null,
  montageProgress: null,
  montageError: null,

  // MARKER_W4.3: Save status
  saveStatus: 'idle',
  lastSavedAt: null,
  saveError: null,
  hasUnsavedChanges: false,

  // MARKER_CLIPBOARD: Clipboard default
  clipboard: [],

  // MARKER_W5.2: Monitor display defaults
  monitorZoom: 0,          // 0 = Fit
  showTitleSafe: false,
  showActionSafe: false,
  showMonitorOverlays: false,

  // MARKER_DISPLAY-CTRL: Timeline Display Controls defaults (FCP7 Ch.9 §141-148)
  showClipNames: true,
  showClipBorders: true,
  showWaveforms: true,
  showThumbnails: true,  // MARKER_B57: video filmstrip on by default
  showThroughEdits: false,
  showClipLabels: false,
  showRubberBand: false,
  clipLabelMode: 'name' as 'name' | 'color' | 'filename',
  timecodeDisplayMode: 'timecode' as 'timecode' | 'frames' | 'seconds',
  showVideoTracks: true,
  showAudioTracks: true,

  // Media status
  mediaError: null,
  mediaLoading: false,

  // Layout
  viewMode: 'nle',
  debugProjectState: null,
  debugStatus: 'Idle',
  debugHandlers: null,
  sceneGraphSurfaceMode: 'shell_only',

  // Actions
  play: () => set({ isPlaying: true }),
  pause: () => set({ isPlaying: false, isRecordMode: false }),  // MARKER_B3.2: exit record on pause
  togglePlay: () => set((s) => {
    const next = !s.isPlaying;
    // MARKER_B3.2: exit record mode when stopping playback
    return next ? { isPlaying: true } : { isPlaying: false, isRecordMode: false };
  }),
  seek: (time) => set((state) => ({ currentTime: Math.min(state.duration || Infinity, Math.max(0, time)) })),
  setDuration: (d) => set({ duration: d }),
  // MARKER_DUAL-VIDEO: Source monitor independent playback actions
  playSource: () => set({ sourceIsPlaying: true }),
  pauseSource: () => set({ sourceIsPlaying: false }),
  togglePlaySource: () => set((s) => ({ sourceIsPlaying: !s.sourceIsPlaying })),
  seekSource: (time) => set({ sourceCurrentTime: Math.max(0, time) }),
  setSourceDuration: (d) => set({ sourceDuration: d }),
  setMarkIn: (t) => set({ markIn: t, sourceMarkIn: t }),
  setMarkOut: (t) => set({ markOut: t, sourceMarkOut: t }),
  // MARKER_W1.4: Separate marks
  setSourceMarkIn: (t) => set({ sourceMarkIn: t, markIn: t }),
  setSourceMarkOut: (t) => set({ sourceMarkOut: t, markOut: t }),
  // MARKER_MRK-FIX: Sync legacy markIn/markOut when setting sequence marks
  // Tests and some components read markIn/markOut — keep them in sync
  setSequenceMarkIn: (t) => set({ sequenceMarkIn: t, markIn: t }),
  setSequenceMarkOut: (t) => set({ sequenceMarkOut: t, markOut: t }),
  setPlaybackRate: (rate) => set({ playbackRate: Math.max(0.25, Math.min(4, rate)) }),
  setShuttleSpeed: (speed) => set({ shuttleSpeed: speed }),
  setZoom: (z) => set({ zoom: Math.max(10, Math.min(300, z)) }),
  setTrackHeight: (h) => set({ trackHeight: Math.max(28, Math.min(180, h)) }),
  setTrackHeightForLane: (laneId, h) =>
    set((state) => ({
      trackHeights: { ...state.trackHeights, [laneId]: Math.max(28, Math.min(180, h)) },
    })),
  cycleTrackHeights: () =>
    set((state) => {
      const PRESETS: [number, 0 | 1 | 2][] = [[28, 0], [56, 1], [112, 2]];
      const next = ((state.trackHeightPreset + 1) % 3) as 0 | 1 | 2;
      return { trackHeight: PRESETS[next][0], trackHeightPreset: next, trackHeights: {} };
    }),
  setScrollLeft: (s) => set({ scrollLeft: Math.max(0, s) }),
  toggleMute: (laneId) =>
    set((state) => {
      const mutedLanes = new Set(state.mutedLanes);
      if (mutedLanes.has(laneId)) mutedLanes.delete(laneId);
      else mutedLanes.add(laneId);
      return { mutedLanes };
    }),
  toggleSolo: (laneId) =>
    set((state) => {
      const soloLanes = new Set(state.soloLanes);
      if (soloLanes.has(laneId)) soloLanes.delete(laneId);
      else soloLanes.add(laneId);
      return { soloLanes };
    }),
  // MARKER_W2.1: Lock and Target toggles
  toggleLock: (laneId) =>
    set((state) => {
      const lockedLanes = new Set(state.lockedLanes);
      if (lockedLanes.has(laneId)) lockedLanes.delete(laneId);
      else lockedLanes.add(laneId);
      return { lockedLanes };
    }),
  toggleTarget: (laneId) =>
    set((state) => {
      const targetedLanes = new Set(state.targetedLanes);
      if (targetedLanes.has(laneId)) targetedLanes.delete(laneId);
      else targetedLanes.add(laneId);
      return { targetedLanes };
    }),
  // MARKER_FIX-TIMELINE-2: Track visibility toggle (eye icon)
  toggleVisibility: (laneId) =>
    set((state) => {
      const hiddenLanes = new Set(state.hiddenLanes);
      if (hiddenLanes.has(laneId)) hiddenLanes.delete(laneId);
      else hiddenLanes.add(laneId);
      return { hiddenLanes };
    }),
  setLaneVolume: (laneId, volume) =>
    set((state) => ({
      laneVolumes: {
        ...state.laneVolumes,
        [laneId]: Math.max(0, Math.min(1.5, volume)),
      },
    })),
  // MARKER_RECON_21: Persist pan to store (was local useState in AudioMixer)
  setLanePan: (laneId, pan) =>
    set((state) => ({
      lanePans: {
        ...state.lanePans,
        [laneId]: Math.max(-1, Math.min(1, pan)),
      },
    })),
  toggleSnap: () => set((state) => ({ snapEnabled: !state.snapEnabled })),
  setSelectedClip: (id) => set({ selectedClipId: id, selectedClipIds: id ? new Set([id]) : new Set() }),
  // MARKER_W3.7: Multi-select actions
  toggleClipSelection: (id) =>
    set((state) => {
      const ids = new Set(state.selectedClipIds);
      if (ids.has(id)) { ids.delete(id); } else { ids.add(id); }
      return { selectedClipIds: ids, selectedClipId: ids.size === 1 ? [...ids][0] : state.selectedClipId };
    }),
  selectAllClips: () =>
    set((state) => {
      const allIds = new Set<string>();
      for (const lane of state.lanes) {
        for (const clip of lane.clips) { allIds.add(clip.clip_id); }
      }
      return { selectedClipIds: allIds };
    }),
  clearSelection: () => set({ selectedClipId: null, selectedClipIds: new Set() }),
  toggleLinkedSelection: () => set((state) => ({ linkedSelection: !state.linkedSelection })),

  // MARKER_CLIPBOARD: Clipboard implementations
  copyClips: () => {
    const { lanes, selectedClipIds } = get();
    if (selectedClipIds.size === 0) return;
    const clips: TimelineClip[] = [];
    for (const lane of lanes) {
      for (const clip of lane.clips) {
        if (selectedClipIds.has(clip.clip_id)) clips.push({ ...clip });
      }
    }
    set({ clipboard: clips });
  },
  // MARKER_UNDO_CUT: Cut clips — copy to clipboard + remove via applyTimelineOps for undo support
  cutClips: () => {
    const { lanes, selectedClipIds } = get();
    if (selectedClipIds.size === 0) return;
    const clips: TimelineClip[] = [];
    for (const lane of lanes) {
      for (const clip of lane.clips) {
        if (selectedClipIds.has(clip.clip_id)) clips.push({ ...clip });
      }
    }
    set({ clipboard: clips, selectedClipId: null, selectedClipIds: new Set() });
    // Route removal through backend undo stack
    const ops = clips.map((c) => ({ op: 'remove_clip', clip_id: c.clip_id }));
    void get().applyTimelineOps(ops);
  },
  // MARKER_UNDO_PASTE: Paste clips via applyTimelineOps for undo support
  pasteClips: (mode) => {
    const { clipboard, currentTime, getInsertTargets } = get();
    if (clipboard.length === 0) return;
    const targets = getInsertTargets();
    const targetLaneId = targets.videoLaneId;
    if (!targetLaneId) return;
    const minStart = Math.min(...clipboard.map((c) => c.start_sec));
    const opType = mode === 'insert' ? 'insert_at' : 'overwrite_at';
    const ops = clipboard.map((c) => ({
      op: opType,
      lane_id: targetLaneId,
      start_sec: currentTime + (c.start_sec - minStart),
      duration_sec: c.duration_sec,
      source_path: c.source_path,
    }));
    void get().applyTimelineOps(ops);
    const maxEnd = Math.max(...clipboard.map((c) => c.start_sec + c.duration_sec));
    get().seek(currentTime + (maxEnd - minStart));
  },
  // MARKER_UNDO_PASTE_ATTR: Route through applyTimelineOps
  pasteAttributes: () => {
    const { clipboard, selectedClipIds } = get();
    if (clipboard.length === 0 || selectedClipIds.size === 0) return;
    const sourceEffects = clipboard[0].effects;
    if (!sourceEffects) return;
    const ops = [...selectedClipIds].map((id) => ({
      op: 'set_effects', clip_id: id, effects: sourceEffects,
    }));
    void get().applyTimelineOps(ops);
  },

  // MARKER_SEQ-MENU + MARKER_UNDO_LIFT: Sequence editing operations — routed through applyTimelineOps
  liftClip: () => {
    // Lift: remove selected clips, leave gap (like Delete but respects In/Out range)
    const { lanes, selectedClipIds, sequenceMarkIn, sequenceMarkOut } = get();
    const ops: Array<Record<string, unknown>> = [];
    if (selectedClipIds.size > 0) {
      for (const id of selectedClipIds) ops.push({ op: 'remove_clip', clip_id: id });
      set({ selectedClipId: null, selectedClipIds: new Set() });
    } else if (sequenceMarkIn != null && sequenceMarkOut != null) {
      // Lift range: remove clips in range, trim partials
      for (const lane of lanes) {
        for (const c of lane.clips) {
          const cEnd = c.start_sec + c.duration_sec;
          if (c.start_sec >= sequenceMarkIn && cEnd <= sequenceMarkOut) {
            ops.push({ op: 'remove_clip', clip_id: c.clip_id });
          } else if (!(cEnd <= sequenceMarkIn || c.start_sec >= sequenceMarkOut)) {
            // Partial overlap — trim to fit
            if (c.start_sec < sequenceMarkIn) {
              ops.push({ op: 'trim_clip', clip_id: c.clip_id, duration_sec: sequenceMarkIn - c.start_sec });
            }
          }
        }
      }
    }
    if (ops.length) void get().applyTimelineOps(ops);
  },
  // MARKER_UNDO_EXTRACT: Extract clips — remove + ripple via applyTimelineOps
  extractClip: () => {
    const { lanes, selectedClipIds, sequenceMarkIn, sequenceMarkOut } = get();
    const ops: Array<Record<string, unknown>> = [];
    if (selectedClipIds.size > 0) {
      for (const id of selectedClipIds) ops.push({ op: 'ripple_delete', clip_id: id });
      set({ selectedClipId: null, selectedClipIds: new Set() });
    } else if (sequenceMarkIn != null && sequenceMarkOut != null) {
      for (const lane of lanes) {
        for (const c of lane.clips) {
          const cEnd = c.start_sec + c.duration_sec;
          if (c.start_sec >= sequenceMarkIn && cEnd <= sequenceMarkOut) {
            ops.push({ op: 'ripple_delete', clip_id: c.clip_id });
          }
        }
      }
    }
    if (ops.length) void get().applyTimelineOps(ops);
  },
  // MARKER_UNDO_CLOSEGAP: Close gap via applyTimelineOps for undo support
  closeGap: () => {
    const { lanes, targetedLanes } = get();
    const ops: Array<Record<string, unknown>> = [];
    for (const lane of lanes) {
      if (targetedLanes.size > 0 && !targetedLanes.has(lane.lane_id)) continue;
      const sorted = [...lane.clips].sort((a, b) => a.start_sec - b.start_sec);
      let cursor = 0;
      for (const clip of sorted) {
        const newStart = Math.max(cursor, 0);
        if (newStart < clip.start_sec) {
          ops.push({ op: 'move_clip', clip_id: clip.clip_id, lane_id: lane.lane_id, start_sec: newStart });
        }
        cursor = (newStart < clip.start_sec ? newStart : clip.start_sec) + clip.duration_sec;
      }
    }
    if (ops.length) void get().applyTimelineOps(ops);
  },
  // MARKER_TD3: Extend Edit (E key) — extend nearest clip edge to playhead
  // FCP7 Ch.19 p.285: finds closest edit point, extends it to playhead
  // MARKER_UNDO-FIX: Routes through applyTimelineOps for undo support
  extendEdit: () => {
    const { lanes, currentTime, lockedLanes } = get();
    let bestDist = Infinity;
    let bestClipId = '';
    let bestEdge: 'start' | 'end' = 'end';
    let bestClipStart = 0;
    let bestClipDur = 0;

    lanes.forEach((lane) => {
      if (lockedLanes.has(lane.lane_id)) return;
      lane.clips.forEach((clip) => {
        const endSec = clip.start_sec + clip.duration_sec;
        const dEnd = Math.abs(endSec - currentTime);
        const dStart = Math.abs(clip.start_sec - currentTime);
        if (dEnd < bestDist) {
          bestDist = dEnd; bestClipId = clip.clip_id; bestEdge = 'end';
          bestClipStart = clip.start_sec; bestClipDur = clip.duration_sec;
        }
        if (dStart < bestDist) {
          bestDist = dStart; bestClipId = clip.clip_id; bestEdge = 'start';
          bestClipStart = clip.start_sec; bestClipDur = clip.duration_sec;
        }
      });
    });

    if (!bestClipId) return;

    if (bestEdge === 'end') {
      const newDur = Math.max(0.01, currentTime - bestClipStart);
      void get().applyTimelineOps([{ op: 'trim_clip', clip_id: bestClipId, duration_sec: newDur }]);
    } else {
      const oldEnd = bestClipStart + bestClipDur;
      const newDur = Math.max(0.01, oldEnd - currentTime);
      void get().applyTimelineOps([{ op: 'trim_clip', clip_id: bestClipId, start_sec: currentTime, duration_sec: newDur }]);
    }
  },

  // MARKER_TD4: Numeric trim — trim selected clip's out point by N frames
  // Positive frames = extend, negative = shorten. Uses trim_clip op.
  // FCP7 Ch.20: type number while trim tool active → trim by exact frame count
  numericTrimSelected: (frames: number) => {
    const { selectedClipId, lanes, projectFramerate } = get();
    if (!selectedClipId) return;
    const deltaSec = frames / (projectFramerate || 25);
    for (const lane of lanes) {
      const clip = lane.clips.find((c) => c.clip_id === selectedClipId);
      if (clip) {
        const newDur = Math.max(0.01, clip.duration_sec + deltaSec);
        void get().applyTimelineOps([{ op: 'trim_clip', clip_id: selectedClipId, duration_sec: newDur }]);
        return;
      }
    }
  },

  // MARKER_TD2: Asymmetric trim — adjust two adjacent clips independently
  // FCP7 Ch.21: different L/R trim values. Left clip out-point changes by leftDeltaFrames,
  // right clip in-point changes by rightDeltaFrames. Does NOT preserve total duration.
  asymmetricTrim: (leftClipId, leftDeltaFrames, rightClipId, rightDeltaFrames) => {
    const { projectFramerate, lanes } = get();
    const fps = projectFramerate || 25;
    const ops: Array<Record<string, unknown>> = [];

    for (const lane of lanes) {
      const leftClip = lane.clips.find((c) => c.clip_id === leftClipId);
      if (leftClip && leftDeltaFrames !== 0) {
        const newDur = Math.max(0.01, leftClip.duration_sec + leftDeltaFrames / fps);
        ops.push({ op: 'trim_clip', clip_id: leftClipId, duration_sec: newDur });
      }
      const rightClip = lane.clips.find((c) => c.clip_id === rightClipId);
      if (rightClip && rightDeltaFrames !== 0) {
        const delta = rightDeltaFrames / fps;
        const newStart = Math.max(0, rightClip.start_sec + delta);
        const newDur = Math.max(0.01, rightClip.duration_sec - delta);
        ops.push({ op: 'trim_clip', clip_id: rightClipId, start_sec: newStart, duration_sec: newDur });
      }
    }

    if (ops.length) {
      void get().applyTimelineOps(ops);
    }
  },

  // MARKER_SPLIT-EDIT: L-cut / J-cut (FCP7 Ch.41)
  // L-cut: video ends at playhead, audio continues past. Creates dialogue overlap.
  // J-cut: audio starts at playhead position, video starts later. Audio leads video.
  // Both find clip under playhead, then trim only video lanes (L-cut) or only audio lanes (J-cut).
  // MARKER_UNDO_SPLIT_EDIT: L-cut/J-cut via applyTimelineOps
  splitEditLCut: () => {
    const { lanes, currentTime, lockedLanes } = get();
    const ops: Array<Record<string, unknown>> = [];
    for (const lane of lanes) {
      if (lockedLanes.has(lane.lane_id)) continue;
      const isVideo = lane.lane_type.startsWith('video') || lane.lane_type.startsWith('take_alt');
      if (!isVideo) continue;
      for (const c of lane.clips) {
        if (c.start_sec < currentTime && c.start_sec + c.duration_sec > currentTime) {
          ops.push({ op: 'trim_clip', clip_id: c.clip_id, duration_sec: currentTime - c.start_sec });
        }
      }
    }
    if (ops.length) void get().applyTimelineOps(ops);
  },
  splitEditJCut: () => {
    const { lanes, currentTime, lockedLanes } = get();
    const ops: Array<Record<string, unknown>> = [];
    for (const lane of lanes) {
      if (lockedLanes.has(lane.lane_id)) continue;
      const isVideo = lane.lane_type.startsWith('video') || lane.lane_type.startsWith('take_alt');
      if (!isVideo) continue;
      for (const c of lane.clips) {
        const cEnd = c.start_sec + c.duration_sec;
        if (c.start_sec < currentTime && cEnd > currentTime) {
          ops.push({ op: 'trim_clip', clip_id: c.clip_id, start_sec: currentTime, duration_sec: cEnd - currentTime });
        }
      }
    }
    if (ops.length) void get().applyTimelineOps(ops);
  },

  // MARKER_TRANSITION: Add default cross dissolve at nearest edit point to playhead
  // MARKER_UNDO-FIX: Routes through applyTimelineOps for undo support
  // FCP7 Ch.24: default transition = 30 frames (1s at 30fps, 1.2s at 25fps)
  addDefaultTransition: () => {
    const { lanes, currentTime, lockedLanes, projectFramerate } = get();
    const defaultFrames = 30;
    const defaultDuration = defaultFrames / (projectFramerate || 25);
    let bestDist = Infinity;
    let bestClipId = '';

    // Find nearest clip end (outgoing edit point) to playhead
    lanes.forEach((lane) => {
      if (lockedLanes.has(lane.lane_id)) return;
      lane.clips.forEach((clip) => {
        const clipEnd = clip.start_sec + clip.duration_sec;
        const dist = Math.abs(clipEnd - currentTime);
        if (dist < bestDist) {
          bestDist = dist;
          bestClipId = clip.clip_id;
        }
      });
    });

    if (!bestClipId || bestDist > 2.0) return;

    void get().applyTimelineOps([{
      op: 'set_transition',
      clip_id: bestClipId,
      transition: { type: 'cross_dissolve', duration_sec: defaultDuration, alignment: 'center' },
    }]);
  },

  // MARKER_DUAL-VIDEO: setActiveMedia is legacy — sets activeMediaPath only, does NOT bleed into source
  setActiveMedia: (path) => set({ activeMediaPath: path, mediaError: null, mediaLoading: !!path }),
  // MARKER_W1.3: Source/Program routing — fully decoupled
  setSourceMedia: (path) => set({ sourceMediaPath: path }),
  setProgramMedia: (path) => set({ programMediaPath: path }),
  setMediaError: (err) => set({ mediaError: err, mediaLoading: false }),
  setMediaLoading: (loading) => set({ mediaLoading: loading }),
  setHoveredClip: (id) => set({ hoveredClipId: id }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setDebugProjectState: (state) => set({ debugProjectState: state }),
  setDebugStatus: (status) => set({ debugStatus: status }),
  setDebugHandlers: (handlers) => set({ debugHandlers: handlers }),
  setSceneGraphSurfaceMode: (mode) => set({ sceneGraphSurfaceMode: mode }),
  // MARKER_W1.2: Panel Focus
  setFocusedPanel: (panel) => set({ focusedPanel: panel }),
  // MARKER_W3.6: Tool State Machine
  setActiveTool: (tool) => set({ activeTool: tool }),
  // MARKER_W4.5: Project Settings setters
  setProjectFramerate: (fps) => set({ projectFramerate: fps }),
  setTimecodeFormat: (fmt) => set({ timecodeFormat: fmt }),
  setDropFrame: (on) => set({ dropFrame: on }),
  setStartTimecode: (tc) => set({ startTimecode: tc }),
  setAudioSampleRate: (rate) => set({ audioSampleRate: rate }),
  setAudioBitDepth: (bits) => set({ audioBitDepth: bits }),
  setShowProjectSettings: (show) => set({ showProjectSettings: show }),
  // MARKER_B3: Sequence Settings setters
  setSequenceResolution: (res) => {
    const dims: Record<string, [number, number]> = {
      '4K': [3840, 2160], '1080p': [1920, 1080], '720p': [1280, 720],
    };
    const [w, h] = dims[res] ?? [get().sequenceWidth, get().sequenceHeight];
    set({ sequenceResolution: res, sequenceWidth: w, sequenceHeight: h });
  },
  setSequenceWidth: (w) => set({ sequenceWidth: w, sequenceResolution: 'custom' }),
  setSequenceHeight: (h) => set({ sequenceHeight: h, sequenceResolution: 'custom' }),
  setSequenceColorSpace: (cs) => set({ sequenceColorSpace: cs }),
  setProxyMode: (mode) => set({ proxyMode: mode }),
  // MARKER_W6.1: Export/Render
  setShowExportDialog: (show) => set({ showExportDialog: show }),
  setShowSpeedControl: (show) => set({ showSpeedControl: show }),  // MARKER_B11
  // MARKER_TRIM_WINDOW: Trim Edit Window action
  setTrimEditActive: (active, clipId, editPoint) => set({ trimEditActive: active, trimEditClipId: clipId ?? null, trimEditPoint: editPoint ?? 0 }),
  setShowMatchSequencePopup: (show: boolean, clipPath?: string) => set({
    showMatchSequencePopup: show,
    pendingMatchClipPath: clipPath ?? null,
  }),
  setRenderProgress: (p) => set({ renderProgress: p }),
  setRenderStatus: (s) => set({ renderStatus: s }),
  setRenderError: (e) => set({ renderError: e }),
  // MARKER_W5.1: Auto-Montage
  setMontageRunning: (running) => set({ montageRunning: running }),
  setMontageMode: (mode) => set({ montageMode: mode }),
  setMontageProgress: (text) => set({ montageProgress: text }),
  setMontageError: (err) => set({ montageError: err }),

  // MARKER_W5.2: Monitor display actions
  setMonitorZoom: (zoom) => set({ monitorZoom: zoom }),
  toggleTitleSafe: () => set((s) => ({ showTitleSafe: !s.showTitleSafe })),
  toggleActionSafe: () => set((s) => ({ showActionSafe: !s.showActionSafe })),
  toggleMonitorOverlays: () => set((s) => ({ showMonitorOverlays: !s.showMonitorOverlays })),

  // MARKER_W4.3: Save actions
  setSaveStatus: (status) => set({ saveStatus: status }),
  setLastSavedAt: (ts) => set({ lastSavedAt: ts }),
  setSaveError: (err) => set({ saveError: err }),
  markUnsavedChanges: () => set({ hasUnsavedChanges: true, saveStatus: 'idle' }),

  // MARKER_DISPLAY-CTRL: Timeline Display Controls toggles
  toggleShowClipNames: () => set((s) => ({ showClipNames: !s.showClipNames })),
  toggleShowClipBorders: () => set((s) => ({ showClipBorders: !s.showClipBorders })),
  toggleShowWaveforms: () => set((s) => ({ showWaveforms: !s.showWaveforms })),
  toggleShowThumbnails: () => set((s) => ({ showThumbnails: !s.showThumbnails })),
  toggleShowThroughEdits: () => set((s) => ({ showThroughEdits: !s.showThroughEdits })),
  toggleShowClipLabels: () => set((s) => ({ showClipLabels: !s.showClipLabels })),
  toggleShowRubberBand: () => set((s) => ({ showRubberBand: !s.showRubberBand })),
  setClipLabelMode: (mode) => set({ clipLabelMode: mode }),
  setTimecodeDisplayMode: (mode) => set({ timecodeDisplayMode: mode }),
  toggleShowVideoTracks: () => set((s) => ({ showVideoTracks: !s.showVideoTracks })),
  toggleShowAudioTracks: () => set((s) => ({ showAudioTracks: !s.showAudioTracks })),

  // MARKER_W10.6: Per-clip effects
  // MARKER_UNDO_EFFECTS: Effects + keyframes via applyTimelineOps
  // Optimistic local update + backend undo stack
  setClipEffects: (clipId, effects) => {
    // Local optimistic: merge partial effects onto clip
    set((s) => ({
      lanes: s.lanes.map((lane) => ({
        ...lane,
        clips: lane.clips.map((c) =>
          c.clip_id === clipId
            ? { ...c, effects: { ...(c.effects || DEFAULT_CLIP_EFFECTS), ...effects } }
            : c
        ),
      })),
    }));
    void get().applyTimelineOps([{ op: 'set_effects', clip_id: clipId, effects }]);
  },
  resetClipEffects: (clipId) => {
    // Local optimistic: reset effects to undefined (neutral)
    set((s) => ({
      lanes: s.lanes.map((lane) => ({
        ...lane,
        clips: lane.clips.map((c) =>
          c.clip_id === clipId ? { ...c, effects: undefined } : c
        ),
      })),
    }));
    void get().applyTimelineOps([{ op: 'reset_effects', clip_id: clipId }]);
  },

  // MARKER_UNDO_KF: Keyframe actions via applyTimelineOps
  addKeyframe: (clipId, property, timeSec, value) => {
    void get().applyTimelineOps([{
      op: 'add_keyframe', clip_id: clipId, property, time_sec: timeSec, value,
    }]);
  },
  removeKeyframe: (clipId, property, timeSec) => {
    void get().applyTimelineOps([{
      op: 'remove_keyframe', clip_id: clipId, property, time_sec: timeSec,
    }]);
  },
  getKeyframeTimes: () => {
    const { lanes, lockedLanes } = get();
    const times = new Set<number>();
    for (const lane of lanes) {
      if (lockedLanes.has(lane.lane_id)) continue;
      for (const clip of lane.clips) {
        if (!clip.keyframes) continue;
        for (const kfs of Object.values(clip.keyframes)) {
          for (const kf of kfs) {
            times.add(clip.start_sec + kf.time_sec);
          }
        }
      }
    }
    return [...times].sort((a, b) => a - b);
  },

  // MARKER_B3.2: Record Mode — state machine
  toggleRecordMode: () => set((s) => ({ isRecordMode: !s.isRecordMode })),
  recordPropertyChange: (clipId, property, value) => {
    const { isRecordMode, isPlaying, currentTime, lanes } = get();
    if (!isRecordMode || !isPlaying) return;
    // Find clip and compute relative time within clip
    for (const lane of lanes) {
      const clip = lane.clips.find((c) => c.clip_id === clipId);
      if (clip) {
        const relTime = currentTime - clip.start_sec;
        if (relTime >= 0 && relTime <= clip.duration_sec) {
          get().addKeyframe(clipId, property, relTime, value);
        }
        break;
      }
    }
  },

  // MARKER_W2.2: Resolve insert/overwrite destination lanes
  // Lane types: video_main, take_alt_y, take_alt_z = video; audio_sync = audio
  getInsertTargets: () => {
    const state = get();
    const { lanes, targetedLanes } = state;
    const isVideo = (t: string) => t.startsWith('video') || t.startsWith('take_alt');
    const isAudio = (t: string) => t.startsWith('audio');
    let videoLaneId: string | null = null;
    let audioLaneId: string | null = null;
    for (const lane of lanes) {
      if (!targetedLanes.has(lane.lane_id)) continue;
      if (!videoLaneId && isVideo(lane.lane_type)) videoLaneId = lane.lane_id;
      if (!audioLaneId && isAudio(lane.lane_type)) audioLaneId = lane.lane_id;
    }
    // Fallback: first V and first A lane if none targeted
    if (!videoLaneId) videoLaneId = lanes.find((l) => isVideo(l.lane_type))?.lane_id ?? null;
    if (!audioLaneId) audioLaneId = lanes.find((l) => isAudio(l.lane_type))?.lane_id ?? null;
    return { videoLaneId, audioLaneId };
  },

  // Data setters
  setLanes: (lanes) => {
    // MARKER_W2.2: Auto-target first V + first A lane if no targets set
    const state = get();
    const isVideo = (t: string) => t.startsWith('video') || t.startsWith('take_alt');
    const isAudio = (t: string) => t.startsWith('audio');
    if (state.targetedLanes.size === 0 && lanes.length > 0) {
      const autoTargets = new Set<string>();
      const firstV = lanes.find((l) => isVideo(l.lane_type));
      const firstA = lanes.find((l) => isAudio(l.lane_type));
      if (firstV) autoTargets.add(firstV.lane_id);
      if (firstA) autoTargets.add(firstA.lane_id);
      set({ lanes, targetedLanes: autoTargets });
    } else {
      set({ lanes });
    }
  },
  setWaveforms: (items) => set({ waveforms: items }),
  setThumbnails: (items) => set({ thumbnails: items }),
  setSyncSurface: (items) => set({ syncSurface: items }),
  setMarkers: (items) => set({ markers: items }),
  // MARKER_FCP7_CH38: Delete + update marker
  deleteMarker: (markerId) => set((s) => ({ markers: s.markers.filter((m) => m.marker_id !== markerId) })),
  updateMarker: (markerId, updates) => set((s) => ({
    markers: s.markers.map((m) => m.marker_id === markerId ? { ...m, ...updates } : m),
  })),

  // MARKER_MULTICAM: Multicam action implementations
  setMulticam: (id, angles) => set({ multicamId: id, multicamAngles: angles, multicamActiveAngle: 0, multicamMode: true }),
  clearMulticam: () => set({ multicamId: null, multicamAngles: [], multicamActiveAngle: 0, multicamMode: false }),
  setMulticamActiveAngle: (index) => set({ multicamActiveAngle: index }),
  toggleMulticamMode: () => set((s) => ({ multicamMode: !s.multicamMode })),
  multicamSwitchAngle: (angleIndex) => {
    const { multicamId, multicamAngles, currentTime } = get();
    if (!multicamId || angleIndex >= multicamAngles.length) return;
    set({ multicamActiveAngle: angleIndex });
    const angle = multicamAngles[angleIndex];
    void get().applyTimelineOps([{
      op: 'overwrite_at',
      lane_id: 'V1',
      start_sec: currentTime,
      duration_sec: 5,
      source_path: angle.source_path,
      source_in: currentTime + angle.offset_sec,
    }]);
  },

  // MARKER_MULTICAM_CREATE: Create multicam clip via backend POST /cut/multicam/create
  createMulticamClip: async (sourcePaths, syncMethod = 'waveform') => {
    try {
      const response = await fetch(`${API_BASE}/cut/multicam/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_paths: sourcePaths,
          sync_method: syncMethod,
          reference_index: 0,
          fps: get().projectFramerate || 25,
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!data.success || !data.multicam_id) throw new Error(data.error || 'create failed');
      // Load multicam into store
      const angles = (data.angles || []).map((a: any, i: number) => ({
        source_path: a.source_path || sourcePaths[i] || '',
        label: a.label || `Angle ${i + 1}`,
        offset_sec: a.offset_sec || 0,
      }));
      get().setMulticam(data.multicam_id, angles);
    } catch (err) {
      console.error('[MULTICAM] Create failed:', err);
      window.dispatchEvent(new CustomEvent('pipeline-activity', {
        detail: { status: 'error', message: `Multicam create failed: ${err}` },
      }));
    }
  },

  setEditorSession: (session) =>
    set((state) => ({
      sandboxRoot: session.sandboxRoot ?? state.sandboxRoot,
      projectId: session.projectId ?? state.projectId,
      sourcePath: session.sourcePath ?? state.sourcePath,
      timelineId: session.timelineId ?? state.timelineId,
      refreshProjectState:
        session.refreshProjectState === undefined ? state.refreshProjectState : session.refreshProjectState,
    })),

  // MARKER_DND_STORE: Drop media from ProjectPanel onto timeline
  // Consumes text/cut-media-paths JSON array, creates clips sequentially at drop position
  dropMediaOnTimeline: (paths, laneId, dropTimeSec, mode) => {
    if (!paths.length) return;
    // MARKER_GAMMA-MATCH: Detect first clip drop on empty timeline → offer to match sequence settings
    const state = get();
    const totalClips = state.lanes.reduce((n, l) => n + l.clips.length, 0);
    if (totalClips === 0 && !localStorage.getItem('cut_suppress_match_popup')) {
      state.setShowMatchSequencePopup(true, paths[0]);
    }
    const DEFAULT_CLIP_DURATION = 5; // seconds — placeholder until probe gives real duration
    const op = mode === 'insert' ? 'insert_at' : 'overwrite_at';
    const ops: Array<Record<string, unknown>> = [];
    let cursor = dropTimeSec;
    for (const sourcePath of paths) {
      ops.push({
        op,
        lane_id: laneId,
        start_sec: cursor,
        duration_sec: DEFAULT_CLIP_DURATION,
        source_path: sourcePath,
      });
      cursor += DEFAULT_CLIP_DURATION;
    }
    void get().applyTimelineOps(ops);
    // Select first dropped clip conceptually — seek to drop position
    get().seek(dropTimeSec);
  },

  // MARKER_UNDO-FIX: Shared applyTimelineOps — all editing ops route through backend undo stack
  applyTimelineOps: async (ops, opts) => {
    const { sandboxRoot, projectId, timelineId, refreshProjectState } = get();
    if (!sandboxRoot || !projectId) {
      // MARKER_UNDO-FIX-23: Quiet drop — no toast for no-session.
      // Before project bootstrap, many auto-triggers call applyTimelineOps.
      // Showing an error toast for each is noisy and confusing.
      // Only log to console for debugging.
      console.warn('[CUT] applyTimelineOps: no project session — op dropped', ops);
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/cut/timeline/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: timelineId || 'main',
          author: 'cut_nle_ui',
          ops,
        }),
      });
      if (!response.ok) {
        throw new Error(`Timeline op failed: HTTP ${response.status}`);
      }
      const payload = (await response.json()) as { success?: boolean; error?: { message?: string } };
      if (!payload.success) {
        throw new Error(payload.error?.message || 'Timeline op failed');
      }
      if (!opts?.skipRefresh) {
        await refreshProjectState?.();
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Timeline op failed';
      console.error('[CUT] applyTimelineOps error:', msg, ops);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('pipeline-activity', {
          detail: { status: 'error', message: msg },
        }));
      }
    }
  },

  // MARKER_170.12: Multi-timeline tab management
  addTimelineTab: (id, label) =>
    set((state) => ({
      timelineTabs: [...state.timelineTabs, { id, label }],
      activeTimelineTabIndex: state.timelineTabs.length, // switch to new tab
      timelineId: id,
    })),
  removeTimelineTab: (index) =>
    set((state) => {
      if (state.timelineTabs.length <= 1) return state; // keep at least one
      const tabs = state.timelineTabs.filter((_, i) => i !== index);
      const newIndex = Math.min(state.activeTimelineTabIndex, tabs.length - 1);
      return { timelineTabs: tabs, activeTimelineTabIndex: newIndex, timelineId: tabs[newIndex].id };
    }),
  setActiveTimelineTab: (index) =>
    set((state) => {
      if (index < 0 || index >= state.timelineTabs.length) return state;
      return { activeTimelineTabIndex: index, timelineId: state.timelineTabs[index].id };
    }),
  renameTimelineTab: (index, label) =>
    set((state) => {
      const tabs = [...state.timelineTabs];
      if (tabs[index]) tabs[index] = { ...tabs[index], label };
      return { timelineTabs: tabs };
    }),

  // MARKER_W5.2: Parallel Timelines
  setParallelTimeline: (tabIndex) => set({ parallelTimelineTabIndex: tabIndex }),
  swapParallelTimeline: () =>
    set((state) => {
      if (state.parallelTimelineTabIndex === null) return state;
      const oldActive = state.activeTimelineTabIndex;
      const newActive = state.parallelTimelineTabIndex;
      if (newActive < 0 || newActive >= state.timelineTabs.length) return state;
      return {
        activeTimelineTabIndex: newActive,
        timelineId: state.timelineTabs[newActive].id,
        parallelTimelineTabIndex: oldActive,
      };
    }),

  // MARKER_198: Snapshot cache — save/restore active timeline data on swap
  snapshotTimeline: (id) =>
    set((state) => {
      const snapshots = new Map(state.timelineSnapshots);
      snapshots.set(id, {
        lanes: state.lanes,
        markers: state.markers,
        currentTime: state.currentTime,
        scrollLeft: state.scrollLeft,
        zoom: state.zoom,
      });
      return { timelineSnapshots: snapshots };
    }),
  restoreTimeline: (id) =>
    set((state) => {
      const snap = state.timelineSnapshots.get(id);
      if (!snap) return { timelineId: id };
      return {
        timelineId: id,
        lanes: snap.lanes,
        markers: snap.markers,
        currentTime: snap.currentTime,
        scrollLeft: snap.scrollLeft,
        zoom: snap.zoom,
      };
    }),

  // MARKER_180.14: Create versioned timeline — ALWAYS new, NEVER overwrite (§7.1)
  createVersionedTimeline: (projectName, mode = 'manual') => {
    let newId = '';
    set((state) => {
      const version = state.nextTimelineVersion;
      const versionStr = version.toString().padStart(2, '0');
      const label = `${projectName}_cut-${versionStr}`;
      newId = `tl_${label}_${Date.now()}`;
      const currentTabId = state.timelineTabs[state.activeTimelineTabIndex]?.id;
      const newTab = {
        id: newId,
        label,
        version,
        createdAt: Date.now(),
        parentId: currentTabId,
        mode,
      };
      return {
        timelineTabs: [...state.timelineTabs, newTab],
        activeTimelineTabIndex: state.timelineTabs.length,
        timelineId: newId,
        nextTimelineVersion: version + 1,
      };
    });
    return newId;
  },

  // MARKER_A4.5: PULSE Auto-Montage — 3 modes (favorites/script/music)
  pulseScores: {},
  montageInProgress: false,
  pulseAnalysisInProgress: false,

  runAutoMontage: async (mode) => {
    const { sandboxRoot, projectId, timelineId, montageInProgress } = get();
    if (montageInProgress) return;
    if (!sandboxRoot || !projectId) {
      console.warn('[PULSE] runAutoMontage: no project session');
      return;
    }
    set({ montageInProgress: true });
    try {
      const resp = await fetch(`${API_BASE}/api/cut/pulse/auto-montage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: timelineId,
          mode,
        }),
      });
      const data = await resp.json();
      if (!data.success) {
        console.error('[PULSE] auto-montage failed:', data.error || data);
        return;
      }
      // Create new timeline tab with montage result
      const label = data.timeline_label || `montage_${mode}`;
      const newId = get().createVersionedTimeline(label, `pulse_${mode}`);
      // Place montage clips on timeline
      if (data.clips?.length) {
        const lanes = get().lanes.map((l) => ({ ...l, clips: [] as typeof l.clips }));
        const videoLane = lanes.find((l) => l.lane_type.startsWith('video')) || lanes[0];
        const audioLane = lanes.find((l) => l.lane_type.startsWith('audio'));
        if (videoLane) {
          videoLane.clips = data.clips.map((c: Record<string, unknown>, i: number) => ({
            clip_id: `montage_${i}`,
            source_path: c.source_path as string,
            source_in: (c.in_point as number) ?? 0,
            start_sec: (c.timeline_position as number) ?? 0,
            duration_sec: ((c.out_point as number) ?? 0) - ((c.in_point as number) ?? 0),
            effects: {},
          }));
          if (audioLane) {
            audioLane.clips = videoLane.clips.map((c) => ({ ...c, clip_id: `${c.clip_id}_a` }));
          }
        }
        set({ lanes, timelineId: newId });
      }
      console.log(`[PULSE] Auto-montage complete: ${data.clips?.length ?? 0} clips, mode=${mode}`);
    } catch (err) {
      console.error('[PULSE] auto-montage error:', err);
    } finally {
      set({ montageInProgress: false });
    }
  },

  // MARKER_A4.8: PULSE Analysis — enrich scenes with Camelot/McKee/energy
  runPulseAnalysis: async () => {
    const { sandboxRoot, projectId, pulseAnalysisInProgress } = get();
    if (pulseAnalysisInProgress) return;
    if (!sandboxRoot || !projectId) {
      console.warn('[PULSE] runPulseAnalysis: no project session');
      return;
    }
    set({ pulseAnalysisInProgress: true });
    try {
      const resp = await fetch(`${API_BASE}/api/cut/pulse/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sandbox_root: sandboxRoot, project_id: projectId }),
      });
      const data = await resp.json();
      if (data.success && data.scores) {
        const scores: Record<string, { camelot_key?: string; energy?: number; pendulum?: number; dramatic_function?: string }> = {};
        for (const score of data.scores) {
          scores[score.scene_id || score.id] = {
            camelot_key: score.camelot_key,
            energy: score.energy,
            pendulum: score.pendulum_position ?? score.pendulum,
            dramatic_function: score.dramatic_function,
          };
        }
        set({ pulseScores: scores });
        console.log(`[PULSE] Analysis complete: ${Object.keys(scores).length} scenes scored`);
      }
    } catch (err) {
      console.error('[PULSE] analysis error:', err);
    } finally {
      set({ pulseAnalysisInProgress: false });
    }
  },
}));

// MARKER_PW2: Panel Sync Bridge — propagate Script/DAG clicks to editor store
// Script click → activeSceneId updates → selectedSceneId → PulseInspector/ClipInspector reactive
// DAG click → selectedAssetPath updates → setSourceMedia → Source Monitor loads clip
usePanelSyncStore.subscribe((state, prev) => {
  // When selectedAssetPath changes → load in Source Monitor
  if (state.selectedAssetPath && state.selectedAssetPath !== prev.selectedAssetPath) {
    useCutEditorStore.getState().setSourceMedia(state.selectedAssetPath);
  }
  // When activeSceneId changes → store it for PulseInspector/ClipInspector
  if (state.activeSceneId && state.activeSceneId !== prev.activeSceneId) {
    useCutEditorStore.setState({ selectedSceneId: state.activeSceneId });
  }
});

// MARKER_PW8: Timeline ID sync — keep CutEditorStore.timelineId in sync with TimelineInstanceStore
// DAG, StorySpace, Inspector can read useCutEditorStore(s => s.timelineId) instead of hardcoding 'main'
import { useTimelineInstanceStore } from './useTimelineInstanceStore';
useTimelineInstanceStore.subscribe((state, prev) => {
  if (state.activeTimelineId && state.activeTimelineId !== prev.activeTimelineId) {
    const current = useCutEditorStore.getState().timelineId;
    if (current !== state.activeTimelineId) {
      useCutEditorStore.setState({ timelineId: state.activeTimelineId });
    }
  }
});

// MARKER_QA.STORE_EXPOSURE: Expose store on window for E2E test access
if (typeof window !== 'undefined') {
  (window as unknown as Record<string, unknown>).__CUT_STORE__ = useCutEditorStore;
}

