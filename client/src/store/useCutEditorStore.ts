/**
 * MARKER_170.NLE.STORE: Shared Zustand store for CUT NLE editor.
 * Bridge between Timeline, VideoPreview, Transport, and Waveform components.
 * Both Opus (timeline) and Codex (player/transport) streams write/read from this.
 */
import { create } from 'zustand';

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

export type TimelineClip = {
  clip_id: string;
  scene_id?: string;
  start_sec: number;
  duration_sec: number;
  source_path: string;
  effects?: ClipEffects;
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
  markIn: number | null;      // legacy — mirrors sourceMarkIn for backward compat
  markOut: number | null;     // legacy — mirrors sourceMarkOut for backward compat

  // === MARKER_W1.4: Separate Source marks and Sequence marks ===
  sourceMarkIn: number | null;     // IN/OUT for raw clip in Source Monitor
  sourceMarkOut: number | null;
  sequenceMarkIn: number | null;   // IN/OUT for timeline position in Program Monitor
  sequenceMarkOut: number | null;

  // === Timeline View ===
  zoom: number; // pixels per second (20 = zoomed out, 200 = zoomed in)
  scrollLeft: number; // horizontal scroll in pixels
  trackHeight: number; // height per lane in pixels
  mutedLanes: Set<string>;
  soloLanes: Set<string>;
  lockedLanes: Set<string>;      // MARKER_W2.1: locked lanes (no edits allowed)
  targetedLanes: Set<string>;    // MARKER_W2.1: targeted lanes (insert/overwrite destination)
  laneVolumes: Record<string, number>;
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
  activeTool: 'selection' | 'razor' | 'hand' | 'zoom';

  // === MARKER_W1.3: Source/Program feed split ===
  sourceMediaPath: string | null;     // raw clip from DAG/Project click → Source Monitor
  programMediaPath: string | null;    // timeline playback → Program Monitor

  // === Data (set from CutStandalone projectState) ===
  lanes: TimelineLane[];
  waveforms: WaveformItem[];
  thumbnails: ThumbnailItem[];
  syncSurface: SyncSurfaceItem[];
  markers: TimeMarker[];

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
  renderProgress: number | null;    // 0-1, null = not rendering
  renderStatus: string | null;      // "Encoding...", "Muxing audio...", etc
  renderError: string | null;

  // === MARKER_W4.3: Save status ===
  saveStatus: 'idle' | 'saving' | 'saved' | 'error';
  lastSavedAt: string | null;     // ISO timestamp from backend
  saveError: string | null;
  hasUnsavedChanges: boolean;

  // === Media status ===
  mediaError: string | null;
  mediaLoading: boolean;

  // === Layout mode ===
  viewMode: 'nle' | 'debug'; // toggle between NLE and legacy debug view
  sceneGraphSurfaceMode: 'shell_only' | 'nle_ready';

  // === Actions ===
  play: () => void;
  pause: () => void;
  togglePlay: () => void;
  seek: (time: number) => void;
  setDuration: (d: number) => void;
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
  setScrollLeft: (s: number) => void;
  toggleMute: (laneId: string) => void;
  toggleSolo: (laneId: string) => void;
  toggleLock: (laneId: string) => void;      // MARKER_W2.1
  toggleTarget: (laneId: string) => void;    // MARKER_W2.1
  setLaneVolume: (laneId: string, volume: number) => void;
  toggleSnap: () => void;
  setSelectedClip: (id: string | null) => void;
  // MARKER_W3.7: Multi-select
  toggleClipSelection: (id: string) => void;   // Cmd+Click toggle
  selectAllClips: () => void;                   // Cmd+A
  clearSelection: () => void;                   // Escape
  toggleLinkedSelection: () => void;            // linked selection toggle
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
  setActiveTool: (tool: 'selection' | 'razor' | 'hand' | 'zoom') => void;
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
  setRenderProgress: (p: number | null) => void;
  setRenderStatus: (s: string | null) => void;
  setRenderError: (e: string | null) => void;
  // MARKER_W5.1: Auto-Montage
  setMontageRunning: (running: boolean) => void;
  setMontageMode: (mode: 'favorites' | 'script' | 'music' | null) => void;
  setMontageProgress: (text: string | null) => void;
  setMontageError: (err: string | null) => void;

  // MARKER_W4.3: Save actions
  setSaveStatus: (status: 'idle' | 'saving' | 'saved' | 'error') => void;
  setLastSavedAt: (ts: string | null) => void;
  setSaveError: (err: string | null) => void;
  markUnsavedChanges: () => void;

  // MARKER_W2.2: Source patching — resolve insert/overwrite destinations
  getInsertTargets: () => { videoLaneId: string | null; audioLaneId: string | null };

  // MARKER_W10.6: Per-clip effects
  setClipEffects: (clipId: string, effects: Partial<ClipEffects>) => void;
  resetClipEffects: (clipId: string) => void;

  // Data setters (called by CutStandalone when projectState updates)
  setLanes: (lanes: TimelineLane[]) => void;
  setWaveforms: (items: WaveformItem[]) => void;
  setThumbnails: (items: ThumbnailItem[]) => void;
  setSyncSurface: (items: SyncSurfaceItem[]) => void;
  setMarkers: (items: TimeMarker[]) => void;
  setEditorSession: (session: {
    sandboxRoot?: string | null;
    projectId?: string | null;
    sourcePath?: string | null;
    timelineId?: string;
    refreshProjectState?: (() => Promise<void>) | null;
  }) => void;

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
}

export const useCutEditorStore = create<CutEditorState>((set, get) => ({
  // Playback defaults
  currentTime: 0,
  isPlaying: false,
  playbackRate: 1,
  shuttleSpeed: 0,
  duration: 0,
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
  mutedLanes: new Set<string>(),
  soloLanes: new Set<string>(),
  lockedLanes: new Set<string>(),
  targetedLanes: new Set<string>(),
  laneVolumes: {},
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

  // MARKER_W1.2: Panel Focus
  focusedPanel: null,
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

  // Media status
  mediaError: null,
  mediaLoading: false,

  // Layout
  viewMode: 'nle',
  sceneGraphSurfaceMode: 'shell_only',

  // Actions
  play: () => set({ isPlaying: true }),
  pause: () => set({ isPlaying: false }),
  togglePlay: () => set((s) => ({ isPlaying: !s.isPlaying })),
  seek: (time) => set({ currentTime: Math.max(0, time) }),
  setDuration: (d) => set({ duration: d }),
  setMarkIn: (t) => set({ markIn: t, sourceMarkIn: t }),
  setMarkOut: (t) => set({ markOut: t, sourceMarkOut: t }),
  // MARKER_W1.4: Separate marks
  setSourceMarkIn: (t) => set({ sourceMarkIn: t, markIn: t }),
  setSourceMarkOut: (t) => set({ sourceMarkOut: t, markOut: t }),
  setSequenceMarkIn: (t) => set({ sequenceMarkIn: t }),
  setSequenceMarkOut: (t) => set({ sequenceMarkOut: t }),
  setPlaybackRate: (rate) => set({ playbackRate: Math.max(0.25, Math.min(4, rate)) }),
  setShuttleSpeed: (speed) => set({ shuttleSpeed: speed }),
  setZoom: (z) => set({ zoom: Math.max(10, Math.min(300, z)) }),
  setTrackHeight: (h) => set({ trackHeight: Math.max(32, Math.min(180, h)) }),
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
  setLaneVolume: (laneId, volume) =>
    set((state) => ({
      laneVolumes: {
        ...state.laneVolumes,
        [laneId]: Math.max(0, Math.min(1.5, volume)),
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
  setActiveMedia: (path) => set({ activeMediaPath: path, sourceMediaPath: path, mediaError: null, mediaLoading: !!path }),
  // MARKER_W1.3: Source/Program routing
  setSourceMedia: (path) => set({ sourceMediaPath: path, activeMediaPath: path, mediaError: null, mediaLoading: !!path }),
  setProgramMedia: (path) => set({ programMediaPath: path }),
  setMediaError: (err) => set({ mediaError: err, mediaLoading: false }),
  setMediaLoading: (loading) => set({ mediaLoading: loading }),
  setHoveredClip: (id) => set({ hoveredClipId: id }),
  setViewMode: (mode) => set({ viewMode: mode }),
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
  setRenderProgress: (p) => set({ renderProgress: p }),
  setRenderStatus: (s) => set({ renderStatus: s }),
  setRenderError: (e) => set({ renderError: e }),
  // MARKER_W5.1: Auto-Montage
  setMontageRunning: (running) => set({ montageRunning: running }),
  setMontageMode: (mode) => set({ montageMode: mode }),
  setMontageProgress: (text) => set({ montageProgress: text }),
  setMontageError: (err) => set({ montageError: err }),

  // MARKER_W4.3: Save actions
  setSaveStatus: (status) => set({ saveStatus: status }),
  setLastSavedAt: (ts) => set({ lastSavedAt: ts }),
  setSaveError: (err) => set({ saveError: err }),
  markUnsavedChanges: () => set({ hasUnsavedChanges: true, saveStatus: 'idle' }),

  // MARKER_W10.6: Per-clip effects
  setClipEffects: (clipId, effects) =>
    set((state) => ({
      lanes: state.lanes.map((lane) => ({
        ...lane,
        clips: lane.clips.map((c) =>
          c.clip_id === clipId
            ? { ...c, effects: { ...(c.effects ?? DEFAULT_CLIP_EFFECTS), ...effects } }
            : c,
        ),
      })),
    })),
  resetClipEffects: (clipId) =>
    set((state) => ({
      lanes: state.lanes.map((lane) => ({
        ...lane,
        clips: lane.clips.map((c) =>
          c.clip_id === clipId ? { ...c, effects: undefined } : c,
        ),
      })),
    })),

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
  setEditorSession: (session) =>
    set((state) => ({
      sandboxRoot: session.sandboxRoot ?? state.sandboxRoot,
      projectId: session.projectId ?? state.projectId,
      sourcePath: session.sourcePath ?? state.sourcePath,
      timelineId: session.timelineId ?? state.timelineId,
      refreshProjectState:
        session.refreshProjectState === undefined ? state.refreshProjectState : session.refreshProjectState,
    })),

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
}));

