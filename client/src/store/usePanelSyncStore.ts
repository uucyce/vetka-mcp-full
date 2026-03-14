/**
 * MARKER_180.15: Panel Synchronization Store — click anywhere → sync everywhere.
 * Central state that all 7 panels subscribe to.
 * Implements the sync matrix from Architecture doc §9.
 *
 * Sync matrix (what happens when user interacts):
 *   Click script line  → playhead moves, DAG highlights, source shows linked, StorySpace moves
 *   Click DAG node     → source shows asset, inspector shows metadata
 *   Move playhead      → script scrolls, DAG pulses, StorySpace updates, inspector updates
 *   Click StorySpace   → script scrolls, DAG highlights, playhead moves
 *   Play transport     → script auto-scrolls, DAG pulses, StorySpace dot moves
 */
import { create } from 'zustand';

// ─── Scene context for sync ───
export type SyncSceneContext = {
  scene_id: string;
  label?: string;
  start_sec: number;
  end_sec: number;
  camelot_key?: string;
  triangle_pos?: { arch: number; mini: number; anti: number };
  pendulum?: number;
  energy?: number;
  dramatic_function?: string;
};

// ─── Sync source — who triggered the sync ───
export type SyncSource =
  | 'script'
  | 'dag_project'
  | 'timeline'
  | 'program_monitor'
  | 'source_monitor'
  | 'story_space_3d'
  | 'inspector'
  | 'transport'
  | 'external';

// ─── Store interface ───
interface PanelSyncState {
  // ─── Core sync fields ───
  activeSceneId: string | null;
  activeSceneContext: SyncSceneContext | null;
  playheadSec: number;
  selectedAssetId: string | null;
  selectedAssetPath: string | null;
  selectedScriptLine: number | null; // line index in script panel
  lastSyncSource: SyncSource | null;
  syncTimestamp: number; // ms, to debounce rapid updates

  // ─── BPM display (updates continuously during playback) ───
  currentAudioBPM: number | null;
  currentVisualBPM: number | null;
  currentScriptBPM: number | null;

  // ─── Actions — each corresponds to a row in §9 sync matrix ───

  /** Script line clicked → sync playhead, DAG, source, StorySpace */
  syncFromScript: (lineIndex: number, sceneId: string, timeSec: number) => void;

  /** DAG node clicked → sync source monitor, inspector */
  syncFromDAG: (assetId: string, assetPath: string, metadata?: Record<string, unknown>) => void;

  /** Timeline playhead moved → sync script, DAG, StorySpace, inspector */
  syncFromPlayhead: (timeSec: number) => void;

  /** StorySpace dot clicked → sync script, DAG, playhead */
  syncFromStorySpace: (sceneId: string, timeSec: number) => void;

  /** Transport play/pause → continuous sync during playback */
  syncFromTransport: (timeSec: number) => void;

  /** Set active scene with full context (from any PULSE API response) */
  setActiveScene: (scene: SyncSceneContext, source: SyncSource) => void;

  /** Update BPM display values */
  setBPM: (audio: number | null, visual: number | null, script: number | null) => void;

  /** Clear all sync state */
  clearSync: () => void;
}

export const usePanelSyncStore = create<PanelSyncState>((set) => ({
  // Defaults
  activeSceneId: null,
  activeSceneContext: null,
  playheadSec: 0,
  selectedAssetId: null,
  selectedAssetPath: null,
  selectedScriptLine: null,
  lastSyncSource: null,
  syncTimestamp: 0,
  currentAudioBPM: null,
  currentVisualBPM: null,
  currentScriptBPM: null,

  // ─── Script line clicked ───
  syncFromScript: (lineIndex, sceneId, timeSec) =>
    set({
      selectedScriptLine: lineIndex,
      activeSceneId: sceneId,
      playheadSec: timeSec,
      lastSyncSource: 'script',
      syncTimestamp: Date.now(),
    }),

  // ─── DAG node clicked ───
  syncFromDAG: (assetId, assetPath) =>
    set({
      selectedAssetId: assetId,
      selectedAssetPath: assetPath,
      lastSyncSource: 'dag_project',
      syncTimestamp: Date.now(),
    }),

  // ─── Timeline playhead moved ───
  syncFromPlayhead: (timeSec) =>
    set({
      playheadSec: timeSec,
      lastSyncSource: 'timeline',
      syncTimestamp: Date.now(),
    }),

  // ─── StorySpace dot clicked ───
  syncFromStorySpace: (sceneId, timeSec) =>
    set({
      activeSceneId: sceneId,
      playheadSec: timeSec,
      lastSyncSource: 'story_space_3d',
      syncTimestamp: Date.now(),
    }),

  // ─── Transport continuous update ───
  syncFromTransport: (timeSec) =>
    set({
      playheadSec: timeSec,
      lastSyncSource: 'transport',
      syncTimestamp: Date.now(),
    }),

  // ─── Set full scene context ───
  setActiveScene: (scene, source) =>
    set({
      activeSceneId: scene.scene_id,
      activeSceneContext: scene,
      playheadSec: scene.start_sec,
      lastSyncSource: source,
      syncTimestamp: Date.now(),
    }),

  // ─── BPM display ───
  setBPM: (audio, visual, script) =>
    set({
      currentAudioBPM: audio,
      currentVisualBPM: visual,
      currentScriptBPM: script,
    }),

  // ─── Clear ───
  clearSync: () =>
    set({
      activeSceneId: null,
      activeSceneContext: null,
      playheadSec: 0,
      selectedAssetId: null,
      selectedAssetPath: null,
      selectedScriptLine: null,
      lastSyncSource: null,
      syncTimestamp: 0,
      currentAudioBPM: null,
      currentVisualBPM: null,
      currentScriptBPM: null,
    }),
}));
