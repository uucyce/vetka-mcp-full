import { useCallback, useEffect, useMemo, useState } from 'react';

import { API_BASE } from './config/api.config';
import CutEditorLayoutV2 from './components/cut/CutEditorLayoutV2';
import {
  buildCutSceneGraphViewportModel,
  type CutSceneGraphView,
} from './components/cut/sceneGraphViewportAdapter';
import { useCutEditorStore } from './store/useCutEditorStore';
import { useTimelineInstanceStore } from './store/useTimelineInstanceStore';
import { usePanelSyncBridge } from './hooks/usePanelSyncBridge';
import { useCutSaveSystem } from './hooks/useCutSaveSystem';

type CutProject = {
  project_id: string;
  display_name?: string;
  source_path?: string;
  sandbox_root?: string;
  state?: string;
};

type CutProjectState = {
  success: boolean;
  schema_version?: string;
  project?: CutProject | null;
  bootstrap_state?: Record<string, unknown> | null;
  timeline_state?: Record<string, unknown> | null;
  scene_graph?: Record<string, unknown> | null;
  scene_graph_view?: Record<string, unknown> | null;
  waveform_bundle?: Record<string, unknown> | null;
  transcript_bundle?: Record<string, unknown> | null;
  thumbnail_bundle?: Record<string, unknown> | null;
  audio_sync_result?: Record<string, unknown> | null;
  music_sync_result?: Record<string, unknown> | null;
  music_cue_summary?: Record<string, unknown> | null;
  slice_bundle?: Record<string, unknown> | null;
  timecode_sync_result?: Record<string, unknown> | null;
  sync_surface?: Record<string, unknown> | null;
  time_marker_bundle?: Record<string, unknown> | null;
  recent_jobs?: CutShellJob[] | null;
  active_jobs?: CutShellJob[] | null;
  runtime_ready?: boolean;
  graph_ready?: boolean;
  waveform_ready?: boolean;
  transcript_ready?: boolean;
  thumbnail_ready?: boolean;
  audio_sync_ready?: boolean;
  music_cues_ready?: boolean;
  slice_ready?: boolean;
  timecode_sync_ready?: boolean;
  sync_surface_ready?: boolean;
  meta_sync_ready?: boolean;
  time_markers_ready?: boolean;
  error?: { code?: string; message?: string; recoverable?: boolean } | null;
};

type CutBootstrapResponse = {
  success: boolean;
  project?: CutProject;
  error?: { code?: string; message?: string };
};

type CutJobEnvelope = {
  success: boolean;
  job_id?: string;
  job?: {
    state?: string;
    result?: Record<string, unknown> | null;
    error?: { code?: string; message?: string } | null;
  };
};

type TimelineLane = {
  lane_id: string;
  lane_type: string;
  clips: Array<{
    clip_id: string;
    scene_id?: string;
    start_sec: number;
    duration_sec: number;
    source_path: string;
  }>;
};

type WorkerBundleItem = {
  item_id: string;
  source_path: string;
  degraded_mode?: boolean;
  degraded_reason?: string;
  poster_url?: string;
  animated_preview_url_300ms?: string;
  source_url?: string;
  modality?: string;
  duration_sec?: number;
};

type TranscriptSegment = {
  start?: number;
  end?: number;
  text?: string;
};

type TranscriptBundleItem = {
  item_id: string;
  source_path: string;
  degraded_mode?: boolean;
  degraded_reason?: string;
  transcript_normalized_json?: {
    segments?: TranscriptSegment[];
  };
};

type CutShellJob = {
  job_id: string;
  job_type?: string;
  state?: string;
  progress?: number;
  updated_at?: string;
};

type MusicCueSummary = {
  track_label?: string;
  cue_point_count?: number;
  phrase_count?: number;
  tempo_bpm?: number | null;
};

type SyncSurfaceItem = {
  item_id: string;
  source_path: string;
  reference_path: string;
  recommended_method: 'timecode' | 'waveform' | 'meta_sync' | null;
  recommended_offset_sec: number;
  confidence: number;
};

type CutTimeMarker = {
  marker_id: string;
  kind: string;
  media_path: string;
  start_sec: number;
  end_sec: number;
  text?: string;
  status?: string;
  score?: number;
  cam_payload?: {
    source?: string;
    hint?: string;
    status?: string;
  } | null;
  context_slice?: {
    mode?: string;
    derived_from?: string;
  } | null;
};

function decodeParam(value: string | null): string {
  const raw = String(value || '').trim();
  if (!raw) return '';
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

function parseQuery() {
  const params = new URLSearchParams(window.location.search);
  return {
    sandboxRoot: decodeParam(params.get('sandbox_root')),
    sourcePath: decodeParam(params.get('source_path')),
    projectName: decodeParam(params.get('project_name')),
    projectId: decodeParam(params.get('project_id')),
  };
}

function formatMusicCueStatus(summary?: MusicCueSummary | null): string | null {
  if (!summary) return null;
  const cueCount = Number(summary.cue_point_count || 0);
  const phraseCount = Number(summary.phrase_count || 0);
  const bpm = typeof summary.tempo_bpm === 'number' && summary.tempo_bpm > 0 ? Math.round(summary.tempo_bpm) : null;
  if (cueCount <= 0 && phraseCount <= 0 && !bpm) {
    return null;
  }
  const cueLabel = cueCount === 1 ? 'cue' : 'cues';
  const parts = [`Music cues: ${cueCount} ${cueLabel}`];
  if (bpm) parts.push(`@ ${bpm} BPM`);
  if (phraseCount > 0) parts.push(`phrases ${phraseCount}`);
  return parts.join(' ');
}

// MARKER_W4.3: Paths that mutate project state → mark dirty after success
const DIRTY_PATHS = new Set([
  '/cut/timeline/apply',
  '/cut/timeline/apply-with-markers',
  '/cut/time-markers/apply',
  '/cut/scene-graph/apply',
  '/cut/undo',
  '/cut/redo',
  '/cut/scene-detect-and-apply',
  '/cut/montage/promote-marker',
]);

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const result = (await response.json()) as T;
  // Auto-mark dirty for mutation endpoints
  if (init?.method === 'POST' && DIRTY_PATHS.has(path)) {
    useCutEditorStore.getState().markDirty();
  }
  return result;
}

const CUT_SCENE_GRAPH_PANE_MODE_STORAGE_KEY = 'cut.scene_graph.pane_mode.v1';

function readStoredSceneGraphPaneMode(): 'embedded' | 'peer_pane' {
  try {
    const raw = window.localStorage.getItem(CUT_SCENE_GRAPH_PANE_MODE_STORAGE_KEY);
    return raw === 'peer_pane' ? 'peer_pane' : 'embedded';
  } catch {
    return 'embedded';
  }
}

function persistSceneGraphPaneMode(mode: 'embedded' | 'peer_pane') {
  try {
    window.localStorage.setItem(CUT_SCENE_GRAPH_PANE_MODE_STORAGE_KEY, mode);
  } catch {
    // ignore localStorage failures for CUT shell preview state
  }
}

export default function CutStandalone() {
  // MARKER_QA.STORE_EXPOSURE: Expose store on window for E2E tests and Chrome DevTools.
  // useEffect guarantees this runs after React mount, when all ESM modules are fully
  // resolved — avoids circular dependency issues with top-level module side-effects.
  useEffect(() => {
    (window as unknown as Record<string, unknown>).__CUT_STORE__ = useCutEditorStore;
  }, []);

  // MARKER_W1.1: Bridge PanelSyncStore → EditorStore (script/DAG clicks → source monitor + playhead)
  usePanelSyncBridge();
  // MARKER_W4.3: Save system (Cmd+S, beforeunload guard, recovery check)
  const { checkRecovery, recoverFromSnapshot } = useCutSaveSystem();

  const query = useMemo(parseQuery, []);
  const [sandboxRoot, setSandboxRoot] = useState(query.sandboxRoot);
  const [sourcePath] = useState(query.sourcePath);
  const [projectName] = useState(query.projectName || 'VETKA CUT Demo');
  const [projectId, setProjectId] = useState(query.projectId);
  const [projectState, setProjectState] = useState<CutProjectState | null>(null);
  const [status, setStatus] = useState('Idle');
  const [, setBusy] = useState(false);
  const [selectedThumbnailId, setSelectedThumbnailId] = useState('');
  const [sceneGraphPaneMode] = useState<'embedded' | 'peer_pane'>(() => readStoredSceneGraphPaneMode());
  const timelineLanes = (projectState?.timeline_state?.lanes as TimelineLane[] | undefined) || [];
  const sceneGraphView = (projectState?.scene_graph_view as CutSceneGraphView | undefined) || null;
  const sceneGraphViewport = useMemo(
    () => buildCutSceneGraphViewportModel(sceneGraphView),
    [sceneGraphView]
  );
  const waveformItems = (projectState?.waveform_bundle?.items as WorkerBundleItem[] | undefined) || [];
  const transcriptItems = (projectState?.transcript_bundle?.items as TranscriptBundleItem[] | undefined) || [];
  const scriptText = useMemo(() => {
    return transcriptItems
      .flatMap((item) => item.transcript_normalized_json?.segments || [])
      .map((seg) => seg.text || '')
      .filter(Boolean)
      .join(' ');
  }, [transcriptItems]);
  const thumbnailItems = (projectState?.thumbnail_bundle?.items as WorkerBundleItem[] | undefined) || [];
  const syncSurfaceItems = (projectState?.sync_surface?.items as SyncSurfaceItem[] | undefined) || [];
  const timeMarkers = (projectState?.time_marker_bundle?.items as CutTimeMarker[] | undefined) || [];

  const activeJobs = projectState?.active_jobs || [];
  const refreshProjectState = useCallback(async (currentProjectId?: string, options?: { silent?: boolean }, sandboxRootOverride?: string) => {
    const pid = String(currentProjectId || projectId || '').trim();
    const sr = sandboxRootOverride || sandboxRoot;
    if (!sr || !pid) return;
    if (!options?.silent) {
      setStatus('Hydrating project state...');
    }
    const payload = await jsonFetch<CutProjectState>(
      `/cut/project-state?sandbox_root=${encodeURIComponent(sr)}&project_id=${encodeURIComponent(pid)}`
    );
    setProjectState(payload);
    if (payload.success) {
      setProjectId(String(payload.project?.project_id || pid));
      if (!options?.silent) {
        setStatus(
          formatMusicCueStatus(payload.music_cue_summary as MusicCueSummary | null | undefined) ||
            (payload.runtime_ready ? 'Runtime ready' : 'Project loaded')
        );
      }
    } else {
      setStatus(payload.error?.message || 'Project state error');
    }
  }, [projectId, sandboxRoot]);

  useEffect(() => {
    if (sandboxRoot && projectId) {
      void refreshProjectState(projectId);
    }
  }, []);

  // MARKER_CUT-UX-NOWELCOME: auto-bootstrap Untitled project when no sandbox_root in query
  useEffect(() => {
    if (!query.sandboxRoot) {
      void handleBootstrap();
    }
  }, []);

  useEffect(() => {
    if (!sandboxRoot || !projectId || activeJobs.length === 0) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      void refreshProjectState(projectId, { silent: true });
    }, 1200);
    return () => window.clearInterval(timer);
  }, [sandboxRoot, projectId, activeJobs.length]);

  useEffect(() => {
    persistSceneGraphPaneMode(sceneGraphPaneMode);
  }, [sceneGraphPaneMode]);

  // MARKER_W4.3: Document title with dirty indicator
  const editorIsDirty = useCutEditorStore((s) => s.isDirty);
  const editorIsSaving = useCutEditorStore((s) => s.isSaving);
  useEffect(() => {
    const prefix = editorIsSaving ? '(saving...) ' : editorIsDirty ? '* ' : '';
    document.title = `${prefix}${projectName} — CUT`;
  }, [projectName, editorIsDirty, editorIsSaving]);
  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const api = {
      triggerSceneGraphFocus: (dagNodeId: string | null) => void handleSceneGraphNodeSelect(dagNodeId),
      getStatus: () => status,
    };
    (window as any).__VETKA_CUT_TEST__ = api;
    return () => {
      if ((window as any).__VETKA_CUT_TEST__ === api) {
        delete (window as any).__VETKA_CUT_TEST__;
      }
    };
  }, [handleSceneGraphNodeSelect, status]);


  useEffect(() => {
    if (!thumbnailItems.length) {
      if (selectedThumbnailId) setSelectedThumbnailId('');
      return;
    }
    if (!thumbnailItems.some((item) => item.item_id === selectedThumbnailId)) {
      setSelectedThumbnailId(thumbnailItems[0].item_id);
    }
  }, [thumbnailItems, selectedThumbnailId]);

  // ─── MARKER_170.NLE: Sync projectState → useCutEditorStore ───
  const editorSetLanes = useCutEditorStore((s) => s.setLanes);
  const editorSetWaveforms = useCutEditorStore((s) => s.setWaveforms);
  const editorSetThumbnails = useCutEditorStore((s) => s.setThumbnails);
  const editorSetSyncSurface = useCutEditorStore((s) => s.setSyncSurface);
  const editorSetMarkers = useCutEditorStore((s) => s.setMarkers);
  const editorSetSession = useCutEditorStore((s) => s.setEditorSession);
  const editorSetSceneGraphSurfaceMode = useCutEditorStore((s) => s.setSceneGraphSurfaceMode);
  // MARKER_W6.STORE: Also sync to instance store for multi-timeline
  const instanceRefresh = useTimelineInstanceStore((s) => s.onProjectStateRefresh);

  useEffect(() => {
    editorSetLanes(timelineLanes);
    // MARKER_W6.STORE: Mirror to instance store
    instanceRefresh({
      lanes: timelineLanes,
      waveforms: waveformItems as any,
      thumbnails: thumbnailItems as any,
      duration: timelineLanes.reduce((max, lane) => {
        for (const clip of lane.clips) {
          const end = clip.start_sec + clip.duration_sec;
          if (end > max) max = end;
        }
        return max;
      }, 0),
    });
  }, [timelineLanes, editorSetLanes, instanceRefresh]);
  useEffect(() => {
    editorSetWaveforms(waveformItems as Array<{ item_id: string; source_path: string; waveform_bins?: number[]; degraded_mode?: boolean }>);
  }, [waveformItems, editorSetWaveforms]);
  useEffect(() => {
    editorSetThumbnails(thumbnailItems as Array<{ item_id: string; source_path: string; poster_url?: string; animated_preview_url_300ms?: string; source_url?: string; modality?: string; duration_sec?: number }>);
  }, [thumbnailItems, editorSetThumbnails]);
  useEffect(() => {
    editorSetSyncSurface(syncSurfaceItems);
  }, [syncSurfaceItems, editorSetSyncSurface]);
  useEffect(() => {
    editorSetMarkers(timeMarkers);
  }, [timeMarkers, editorSetMarkers]);
  useEffect(() => {
    editorSetSession({
      // MARKER_170.NLE.SESSION_WIRING: timeline/player actions reuse the shell's CUT session.
      sandboxRoot: sandboxRoot || null,
      projectId: projectId || null,
      sourcePath: sourcePath || null,
      timelineId: String(projectState?.timeline_state?.timeline_id || 'main'),
      refreshProjectState: async () => {
        await refreshProjectState(projectId || undefined, { silent: true });
      },
    });
  }, [sandboxRoot, projectId, sourcePath, projectState?.timeline_state, refreshProjectState, editorSetSession]);
  useEffect(() => {
    editorSetSceneGraphSurfaceMode(sceneGraphPaneMode === 'peer_pane' ? 'nle_ready' : 'shell_only');
  }, [sceneGraphPaneMode, editorSetSceneGraphSurfaceMode]);

  // MARKER_QA.W5.1: Sync debug shell state → editor store for DebugShellPanel
  const editorSetDebugState = useCutEditorStore((s) => s.setDebugProjectState);
  const editorSetDebugStatus = useCutEditorStore((s) => s.setDebugStatus);
  const editorSetDebugHandlers = useCutEditorStore((s) => s.setDebugHandlers);
  useEffect(() => {
    editorSetDebugState(projectState as Record<string, unknown> | null);
  }, [projectState, editorSetDebugState]);
  useEffect(() => {
    editorSetDebugStatus(status);
  }, [status, editorSetDebugStatus]);

  async function handleBootstrap() {
    setBusy(true);
    try {
      setStatus('Bootstrapping CUT project...');
      const payload = await jsonFetch<CutBootstrapResponse>('/cut/bootstrap', {
        method: 'POST',
        body: JSON.stringify({
          source_path: sourcePath,
          sandbox_root: sandboxRoot,
          project_name: projectName,
          mode: 'create_or_open',
          use_core_mirror: true,
          create_project_if_missing: true,
        }),
      });
      if (!payload.success || !payload.project?.project_id) {
        setStatus(payload.error?.message || 'Bootstrap failed');
        return;
      }
      // MARKER_CUT-UX-NOWELCOME: capture backend-assigned sandbox_root for fresh starts
      const effectiveSandboxRoot = payload.project.sandbox_root || sandboxRoot;
      if (effectiveSandboxRoot && effectiveSandboxRoot !== sandboxRoot) {
        setSandboxRoot(effectiveSandboxRoot);
      }
      setProjectId(payload.project.project_id);
      await refreshProjectState(payload.project.project_id, undefined, effectiveSandboxRoot || undefined);

      // MARKER_W4.3: Check for crash recovery after project load
      const recovery = await checkRecovery();
      if (recovery?.recovery_available && recovery.snapshot_dir) {
        const doRecover = window.confirm(
          `Autosave found from ${recovery.autosave_at || 'unknown time'}.\n` +
          `Last explicit save: ${recovery.last_save_at || 'never'}.\n\n` +
          'Recover from autosave?'
        );
        if (doRecover) {
          const ok = await recoverFromSnapshot(recovery.snapshot_dir);
          if (ok) {
            await refreshProjectState(payload.project.project_id);
            setStatus('Recovered from autosave');
          }
        }
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Bootstrap failed');
    } finally {
      setBusy(false);
    }
  }

  async function waitForJob(jobId: string) {
    for (let attempt = 0; attempt < 40; attempt += 1) {
      const payload = await jsonFetch<CutJobEnvelope>(`/cut/job/${encodeURIComponent(jobId)}`);
      const state = String(payload.job?.state || '');
      if (state === 'done') return payload;
      if (state === 'error') {
        throw new Error(payload.job?.error?.message || 'CUT job failed');
      }
      await new Promise((resolve) => window.setTimeout(resolve, 150));
    }
    throw new Error('CUT job timeout');
  }

  async function handleSceneAssembly() {
    if (!sandboxRoot || !projectId) return;
    setBusy(true);
    try {
      setStatus('Running scene assembly...');
      const created = await jsonFetch<CutJobEnvelope>('/cut/scene-assembly-async', {
        method: 'POST',
        body: JSON.stringify({ sandbox_root: sandboxRoot, project_id: projectId, timeline_id: 'main', graph_id: 'main' }),
      });
      if (!created.success || !created.job_id) {
        setStatus('Scene assembly did not start');
        return;
      }
      await waitForJob(created.job_id);
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Scene assembly failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleSelectFirstClip() {
    const firstClipId = timelineLanes[0]?.clips?.[0]?.clip_id;
    if (!firstClipId || !sandboxRoot || !projectId) return;
    setBusy(true);
    try {
      const payload = await jsonFetch<{ success: boolean; timeline_state?: Record<string, unknown>; error?: { message?: string } }>(
        '/cut/timeline/apply',
        {
          method: 'POST',
          body: JSON.stringify({
            sandbox_root: sandboxRoot,
            project_id: projectId,
            timeline_id: 'main',
            author: 'cut_shell',
            ops: [
              { op: 'set_selection', clip_ids: [firstClipId], scene_ids: ['scene_01'] },
              { op: 'set_view', active_lane_id: timelineLanes[0].lane_id, zoom: 1.25 },
            ],
          }),
        }
      );
      if (!payload.success) throw new Error(payload.error?.message || 'Timeline apply failed');
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Timeline apply failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleSceneGraphNodeSelect(dagNodeId: string | null) {
    if (!sceneGraphViewport || !dagNodeId) return;
    const node = sceneGraphViewport.nodeByDagId[dagNodeId];
    if (!node) return;

    const sourcePath = node.selection_refs?.source_paths?.[0] || '';
    const matchingThumbnail = sourcePath
      ? thumbnailItems.find((item) => item.source_path === sourcePath)
      : null;
    if (matchingThumbnail) {
      setSelectedThumbnailId(matchingThumbnail.item_id);
    }

    const clipIds = (node.selection_refs?.clip_ids || []).map(String).filter(Boolean);
    const sceneIds = (node.selection_refs?.scene_ids || []).map(String).filter(Boolean);
    if (!sandboxRoot || !projectId || clipIds.length === 0) {
      setStatus(`Graph focus: ${node.label}`);
      return;
    }

    setBusy(true);
    try {
      setStatus(`Graph focus -> timeline: ${node.label}`);
      const payload = await jsonFetch<{ success: boolean; error?: { message?: string } }>('/cut/timeline/apply', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: 'main',
          author: 'cut_scene_graph_viewport',
          ops: [
            {
              op: 'set_selection',
              clip_ids: clipIds,
              scene_ids: sceneIds,
            },
          ],
        }),
      });
      if (!payload.success) throw new Error(payload.error?.message || 'Graph timeline focus failed');
      await refreshProjectState(projectId, { silent: true });
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Graph timeline focus failed');
    } finally {
      setBusy(false);
    }
  }




  async function handleRunMetaSync() {
    if (!sandboxRoot || !projectId) return;
    setBusy(true);
    try {
      setStatus('Building meta sync analysis...');
      const payload = await jsonFetch<{ success: boolean; job_id?: string; error?: { message?: string } }>(
        '/cut/worker/meta-sync-async',
        {
          method: 'POST',
          body: JSON.stringify({ sandbox_root: sandboxRoot, project_id: projectId }),
        }
      );
      if (!payload.success) throw new Error(payload.error?.message || 'Meta sync failed');
      setStatus(`Meta sync job started: ${payload.job_id}`);
      if (payload.job_id) {
        await waitForJob(payload.job_id);
        await refreshProjectState(projectId);
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Meta sync failed');
    } finally {
      setBusy(false);
    }
  }


  async function handleWaveformBuild() {
    if (!sandboxRoot || !projectId) return;
    setBusy(true);
    try {
      setStatus('Building waveform bundle...');
      const created = await jsonFetch<CutJobEnvelope>('/cut/worker/waveform-build-async', {
        method: 'POST',
        body: JSON.stringify({ sandbox_root: sandboxRoot, project_id: projectId, bins: 48, limit: 12 }),
      });
      if (!created.success || !created.job_id) {
        setStatus('Waveform worker did not start');
        return;
      }
      await waitForJob(created.job_id);
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Waveform build failed');
    } finally {
      setBusy(false);
    }
  }


  async function handleThumbnailBuild() {
    if (!sandboxRoot || !projectId) return;
    setBusy(true);
    try {
      setStatus('Building storyboard thumbnails...');
      const created = await jsonFetch<CutJobEnvelope>('/cut/worker/thumbnail-build-async', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          limit: 12,
          waveform_bins: 48,
          preview_segments_limit: 24,
        }),
      });
      if (!created.success || !created.job_id) {
        setStatus('Thumbnail worker did not start');
        return;
      }
      await waitForJob(created.job_id);
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Thumbnail build failed');
    } finally {
      setBusy(false);
    }
  }

  async function handlePauseSliceBuild() {
    if (!sandboxRoot || !projectId) return;
    setBusy(true);
    try {
      setStatus('Building pause-aware slices...');
      const created = await jsonFetch<CutJobEnvelope>('/cut/worker/pause-slice-async', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          limit: 8,
          sample_bytes: 8192,
          frame_ms: 20,
          silence_threshold: 0.08,
          min_silence_ms: 250,
          keep_silence_ms: 80,
        }),
      });
      if (!created.success || !created.job_id) {
        setStatus('Pause slice worker did not start');
        return;
      }
      await waitForJob(created.job_id);
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Pause slice build failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleAudioSyncBuild() {
    if (!sandboxRoot || !projectId) return;
    setBusy(true);
    try {
      setStatus('Building audio sync offsets...');
      const created = await jsonFetch<CutJobEnvelope>('/cut/worker/audio-sync-async', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          limit: 6,
          sample_bytes: 8192,
          method: 'peaks+correlation',
        }),
      });
      if (!created.success || !created.job_id) {
        setStatus('Audio sync worker did not start');
        return;
      }
      await waitForJob(created.job_id);
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Audio sync build failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleTimecodeSyncBuild() {
    if (!sandboxRoot || !projectId) return;
    setBusy(true);
    try {
      setStatus('Building timecode sync offsets...');
      const created = await jsonFetch<CutJobEnvelope>('/cut/worker/timecode-sync-async', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          limit: 6,
          fps: 25,
        }),
      });
      if (!created.success || !created.job_id) {
        setStatus('Timecode sync worker did not start');
        return;
      }
      await waitForJob(created.job_id);
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Timecode sync build failed');
    } finally {
      setBusy(false);
    }
  }







  // MARKER_QA.W5.1: Expose debug handlers to store for DebugShellPanel
  useEffect(() => {
    editorSetDebugHandlers({
      bootstrap: handleBootstrap,
      sceneAssembly: handleSceneAssembly,
      selectFirstClip: handleSelectFirstClip,
      waveformBuild: handleWaveformBuild,
      audioSyncBuild: handleAudioSyncBuild,
      timecodeSyncBuild: handleTimecodeSyncBuild,
      pauseSliceBuild: handlePauseSliceBuild,
      thumbnailBuild: handleThumbnailBuild,
      metaSync: handleRunMetaSync,
      refreshProjectState: () => refreshProjectState(projectId),
    });
  });

  return <CutEditorLayoutV2 scriptText={scriptText} />;
}
