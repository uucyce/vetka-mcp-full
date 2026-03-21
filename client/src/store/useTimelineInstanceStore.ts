/**
 * MARKER_C10: Multi-instance timeline store (Phase 198).
 *
 * Parallel to useCutEditorStore — this store manages the Map<string, TimelineInstance>
 * for multi-timeline support. Does NOT replace useCutEditorStore yet; acts as a bridge
 * layer that Stream A can migrate to when ready.
 *
 * Contracts (from RECON_FCP7_MULTI_INSTANCE_TIMELINES.md):
 *   C1: No Set<> in serializable state — string[] and Record<string, boolean> only
 *   C2: Unified marker pool — markers NOT stored per-instance
 *   C3: Close fallback — removeTimeline activates most recently focused
 *   C4: Serialization round-trip — hydrateTimelines(serializeTimelines()) = identity
 *   C5: Active edits — only active timeline gets keyboard edits
 *
 * @phase 198
 */
import { create } from 'zustand';
import type { TimelineLane, WaveformItem, ThumbnailItem } from './useCutEditorStore';

// ─── TimelineInstance ──────────────────────────────────────────────

export interface TimelineInstance {
  id: string;                               // 'tl_cut-00', 'tl_cut-01-v02'
  label: string;                            // 'Cut 00 — Assembly'
  version: number;                          // auto-increment
  mode: 'manual' | 'favorites' | 'script' | 'music';
  parentId?: string;                        // forked from
  createdAt: number;

  // Data (loaded from backend)
  lanes: TimelineLane[];
  waveforms: WaveformItem[];
  thumbnails: ThumbnailItem[];
  duration: number;

  // View state (local, NOT on backend)
  scrollX: number;
  scrollY: number;
  zoom: number;                             // px/sec
  trackHeight: number;

  // Playback state
  playheadPosition: number;
  isPlaying: boolean;
  markIn: number | null;
  markOut: number | null;

  // Selection (C1: NO Set<>, use string[] and Record)
  selectedClipIds: string[];
  hoveredClipId: string | null;

  // Lane state (C1: Record, NOT Set)
  mutedLanes: Record<string, boolean>;
  soloLanes: Record<string, boolean>;
  lockedLanes: Record<string, boolean>;
  targetedLanes: Record<string, boolean>;

  // Focus tracking (C3: for close fallback)
  lastFocusedAt: number;
}

// ─── Create options ────────────────────────────────────────────────

export interface CreateTimelineOpts {
  id?: string;
  label?: string;
  mode?: TimelineInstance['mode'];
  parentId?: string;
  lanes?: TimelineLane[];
  duration?: number;
}

// ─── Default instance factory ──────────────────────────────────────

let nextVersion = 1;

function createInstance(opts: CreateTimelineOpts): TimelineInstance {
  const v = nextVersion++;
  return {
    id: opts.id || `tl_cut-${String(v).padStart(2, '0')}`,
    label: opts.label || `Cut ${String(v).padStart(2, '0')}`,
    version: v,
    mode: opts.mode || 'manual',
    parentId: opts.parentId,
    createdAt: Date.now(),
    lanes: opts.lanes || [],
    waveforms: [],
    thumbnails: [],
    duration: opts.duration || 0,
    scrollX: 0,
    scrollY: 0,
    zoom: 80,
    trackHeight: 60,
    playheadPosition: 0,
    isPlaying: false,
    markIn: null,
    markOut: null,
    selectedClipIds: [],
    hoveredClipId: null,
    mutedLanes: {},
    soloLanes: {},
    lockedLanes: {},
    targetedLanes: {},
    lastFocusedAt: Date.now(),
  };
}

// ─── Store interface ───────────────────────────────────────────────

interface TimelineInstanceStoreState {
  timelines: Map<string, TimelineInstance>;
  activeTimelineId: string;

  // Actions
  createTimeline: (opts?: CreateTimelineOpts) => string;
  removeTimeline: (id: string) => void;
  setActiveTimeline: (id: string) => void;
  getTimeline: (id: string) => TimelineInstance | undefined;
  updateTimeline: (id: string, partial: Partial<TimelineInstance>) => void;

  // MARKER_W6.STORE: Re-snapshot from backend refresh
  onProjectStateRefresh: (data: {
    lanes: TimelineLane[];
    waveforms: WaveformItem[];
    thumbnails: ThumbnailItem[];
    duration: number;
  }) => void;

  // Serialization (C4: round-trip safe)
  serializeTimelines: () => Record<string, TimelineInstance>;
  hydrateTimelines: (data: Record<string, TimelineInstance>) => void;
}

// ─── Store ─────────────────────────────────────────────────────────

export const useTimelineInstanceStore = create<TimelineInstanceStoreState>((set, get) => ({
  timelines: new Map(),
  activeTimelineId: '',

  createTimeline: (opts = {}) => {
    const instance = createInstance(opts);
    set((state) => {
      const next = new Map(state.timelines);
      next.set(instance.id, instance);
      return {
        timelines: next,
        activeTimelineId: state.activeTimelineId || instance.id,
      };
    });
    return instance.id;
  },

  removeTimeline: (id) => {
    set((state) => {
      const next = new Map(state.timelines);
      next.delete(id);

      let newActiveId = state.activeTimelineId;
      if (state.activeTimelineId === id) {
        // C3: Close fallback — find most recently focused remaining
        let best: TimelineInstance | null = null;
        for (const tl of next.values()) {
          if (!best || tl.lastFocusedAt > best.lastFocusedAt) {
            best = tl;
          }
        }
        newActiveId = best?.id || '';
      }

      return { timelines: next, activeTimelineId: newActiveId };
    });
  },

  setActiveTimeline: (id) => {
    set((state) => {
      const tl = state.timelines.get(id);
      if (!tl) return state;

      const next = new Map(state.timelines);
      next.set(id, { ...tl, lastFocusedAt: Date.now() });
      return { timelines: next, activeTimelineId: id };
    });
  },

  getTimeline: (id) => {
    return get().timelines.get(id);
  },

  updateTimeline: (id, partial) => {
    set((state) => {
      const tl = state.timelines.get(id);
      if (!tl) return state;

      const next = new Map(state.timelines);
      next.set(id, { ...tl, ...partial });
      return { timelines: next };
    });
  },

  // MARKER_W6.STORE: Sync data from backend refresh into active instance
  onProjectStateRefresh: (data: {
    lanes: TimelineLane[];
    waveforms: WaveformItem[];
    thumbnails: ThumbnailItem[];
    duration: number;
  }) => {
    const state = get();
    const activeId = state.activeTimelineId;
    if (!activeId) return;
    const tl = state.timelines.get(activeId);
    if (!tl) return;
    const next = new Map(state.timelines);
    next.set(activeId, {
      ...tl,
      lanes: data.lanes,
      waveforms: data.waveforms,
      thumbnails: data.thumbnails,
      duration: data.duration,
    });
    set({ timelines: next });
  },

  // C4: Serialization round-trip
  serializeTimelines: () => {
    const result: Record<string, TimelineInstance> = {};
    for (const [id, tl] of get().timelines) {
      result[id] = { ...tl };
    }
    return result;
  },

  hydrateTimelines: (data) => {
    const map = new Map<string, TimelineInstance>();
    let maxVersion = 0;
    for (const [id, tl] of Object.entries(data)) {
      map.set(id, { ...tl });
      if (tl.version > maxVersion) maxVersion = tl.version;
    }
    nextVersion = maxVersion + 1;

    // Pick active: most recently focused or first
    let activeId = '';
    let bestTime = 0;
    for (const tl of map.values()) {
      if (tl.lastFocusedAt > bestTime) {
        bestTime = tl.lastFocusedAt;
        activeId = tl.id;
      }
    }

    set({ timelines: map, activeTimelineId: activeId });
  },
}));
