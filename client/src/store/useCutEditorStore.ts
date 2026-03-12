/**
 * MARKER_170.NLE.STORE: Shared Zustand store for CUT NLE editor.
 * Bridge between Timeline, VideoPreview, Transport, and Waveform components.
 * Both Opus (timeline) and Codex (player/transport) streams write/read from this.
 */
import { create } from 'zustand';

export type TimelineClip = {
  clip_id: string;
  scene_id?: string;
  start_sec: number;
  duration_sec: number;
  source_path: string;
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

export type TimeMarker = {
  marker_id: string;
  kind: string;
  media_path: string;
  start_sec: number;
  end_sec: number;
  text?: string;
  status?: string;
  score?: number;
};

interface CutEditorState {
  // === Playback ===
  currentTime: number;
  isPlaying: boolean;
  playbackRate: number;
  duration: number;
  markIn: number | null;
  markOut: number | null;

  // === Timeline View ===
  zoom: number; // pixels per second (20 = zoomed out, 200 = zoomed in)
  scrollLeft: number; // horizontal scroll in pixels
  trackHeight: number; // height per lane in pixels
  mutedLanes: Set<string>;
  soloLanes: Set<string>;
  laneVolumes: Record<string, number>;
  snapEnabled: boolean;

  // === Selection ===
  selectedClipId: string | null;
  activeMediaPath: string | null;
  hoveredClipId: string | null;

  // === Data (set from CutStandalone projectState) ===
  lanes: TimelineLane[];
  waveforms: WaveformItem[];
  thumbnails: ThumbnailItem[];
  syncSurface: SyncSurfaceItem[];
  markers: TimeMarker[];

  // === Session / backend wiring ===
  sandboxRoot: string | null;
  projectId: string | null;
  timelineId: string;
  refreshProjectState: (() => Promise<void>) | null;

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
  setPlaybackRate: (rate: number) => void;
  setZoom: (z: number) => void;
  setScrollLeft: (s: number) => void;
  toggleMute: (laneId: string) => void;
  toggleSolo: (laneId: string) => void;
  setLaneVolume: (laneId: string, volume: number) => void;
  toggleSnap: () => void;
  setSelectedClip: (id: string | null) => void;
  setActiveMedia: (path: string | null) => void;
  setHoveredClip: (id: string | null) => void;
  setMediaError: (err: string | null) => void;
  setMediaLoading: (loading: boolean) => void;
  setViewMode: (mode: 'nle' | 'debug') => void;
  setSceneGraphSurfaceMode: (mode: 'shell_only' | 'nle_ready') => void;

  // Data setters (called by CutStandalone when projectState updates)
  setLanes: (lanes: TimelineLane[]) => void;
  setWaveforms: (items: WaveformItem[]) => void;
  setThumbnails: (items: ThumbnailItem[]) => void;
  setSyncSurface: (items: SyncSurfaceItem[]) => void;
  setMarkers: (items: TimeMarker[]) => void;
  setEditorSession: (session: {
    sandboxRoot?: string | null;
    projectId?: string | null;
    timelineId?: string;
    refreshProjectState?: (() => Promise<void>) | null;
  }) => void;
}

export const useCutEditorStore = create<CutEditorState>((set) => ({
  // Playback defaults
  currentTime: 0,
  isPlaying: false,
  playbackRate: 1,
  duration: 0,
  markIn: null,
  markOut: null,

  // Timeline defaults
  zoom: 60, // 60px per second — good starting point
  scrollLeft: 0,
  trackHeight: 56,
  mutedLanes: new Set<string>(),
  soloLanes: new Set<string>(),
  laneVolumes: {},
  snapEnabled: true,

  // Selection
  selectedClipId: null,
  activeMediaPath: null,
  hoveredClipId: null,

  // Data
  lanes: [],
  waveforms: [],
  thumbnails: [],
  syncSurface: [],
  markers: [],

  // Session defaults
  sandboxRoot: null,
  projectId: null,
  timelineId: 'main',
  refreshProjectState: null,

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
  setMarkIn: (t) => set({ markIn: t }),
  setMarkOut: (t) => set({ markOut: t }),
  setPlaybackRate: (rate) => set({ playbackRate: Math.max(0.25, Math.min(4, rate)) }),
  setZoom: (z) => set({ zoom: Math.max(10, Math.min(300, z)) }),
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
  setLaneVolume: (laneId, volume) =>
    set((state) => ({
      laneVolumes: {
        ...state.laneVolumes,
        [laneId]: Math.max(0, Math.min(1.5, volume)),
      },
    })),
  toggleSnap: () => set((state) => ({ snapEnabled: !state.snapEnabled })),
  setSelectedClip: (id) => set({ selectedClipId: id }),
  setActiveMedia: (path) => set({ activeMediaPath: path, mediaError: null, mediaLoading: !!path }),
  setMediaError: (err) => set({ mediaError: err, mediaLoading: false }),
  setMediaLoading: (loading) => set({ mediaLoading: loading }),
  setHoveredClip: (id) => set({ hoveredClipId: id }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setSceneGraphSurfaceMode: (mode) => set({ sceneGraphSurfaceMode: mode }),

  // Data setters
  setLanes: (lanes) => set({ lanes }),
  setWaveforms: (items) => set({ waveforms: items }),
  setThumbnails: (items) => set({ thumbnails: items }),
  setSyncSurface: (items) => set({ syncSurface: items }),
  setMarkers: (items) => set({ markers: items }),
  setEditorSession: (session) =>
    set((state) => ({
      sandboxRoot: session.sandboxRoot ?? state.sandboxRoot,
      projectId: session.projectId ?? state.projectId,
      timelineId: session.timelineId ?? state.timelineId,
      refreshProjectState:
        session.refreshProjectState === undefined ? state.refreshProjectState : session.refreshProjectState,
    })),
}));
