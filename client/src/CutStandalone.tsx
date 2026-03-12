import { useCallback, useEffect, useMemo, useState, type CSSProperties } from 'react';

import { API_BASE } from './config/api.config';
import { ReactFlowProvider } from '@xyflow/react';
import { DAGView } from './components/mcc/DAGView';
import { NOLAN_PALETTE } from './utils/dagLayout';
import CutEditorLayout from './components/cut/CutEditorLayout';
import {
  buildCutSceneGraphViewportModel,
  type CutSceneGraphView,
} from './components/cut/sceneGraphViewportAdapter';
import { useCutEditorStore } from './store/useCutEditorStore';

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

type SceneGraphNode = {
  node_id: string;
  node_type: string;
  label: string;
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

type SliceWindow = {
  start_sec: number;
  end_sec: number;
  duration_sec?: number;
  confidence?: number;
  method?: string;
};

type SliceBundleItem = {
  item_id: string;
  source_path: string;
  method: string;
  windows: SliceWindow[];
  degraded_mode?: boolean;
  degraded_reason?: string;
};

type AudioSyncResultItem = {
  item_id: string;
  reference_path: string;
  source_path: string;
  detected_offset_sec: number;
  confidence: number;
  method: string;
  degraded_mode?: boolean;
  degraded_reason?: string;
};

type TimecodeSyncResultItem = {
  item_id: string;
  reference_path: string;
  source_path: string;
  reference_timecode: string;
  source_timecode: string;
  fps: number;
  detected_offset_sec: number;
  confidence: number;
  method: string;
  degraded_mode?: boolean;
  degraded_reason?: string;
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

function derivePreviewMarkerWindow(item: WorkerBundleItem): { startSec: number; endSec: number; anchorSec: number } {
  const durationSec = Math.max(0, Number(item.duration_sec) || 0);
  if (durationSec <= 0) {
    return { startSec: 0, endSec: 1, anchorSec: 0.5 };
  }
  const windowSize = Math.min(3, Math.max(0.75, durationSec * 0.12));
  const anchorSec = Math.min(durationSec, Math.max(0, durationSec * 0.5));
  const halfWindow = windowSize / 2;
  const startSec = Math.max(0, anchorSec - halfWindow);
  const endSec = Math.min(durationSec, Math.max(startSec + 0.25, anchorSec + halfWindow));
  return {
    startSec: Number(startSec.toFixed(2)),
    endSec: Number(endSec.toFixed(2)),
    anchorSec: Number(anchorSec.toFixed(2)),
  };
}

function deriveTranscriptMarkerWindow(
  item: WorkerBundleItem,
  transcriptItem?: TranscriptBundleItem
): { startSec: number; endSec: number; anchorSec: number; mode: string } {
  const previewWindow = derivePreviewMarkerWindow(item);
  const segments = (transcriptItem?.transcript_normalized_json?.segments || [])
    .map((segment) => ({
      start: Number(segment.start ?? 0),
      end: Number(segment.end ?? 0),
      text: String(segment.text || ''),
    }))
    .filter((segment) => Number.isFinite(segment.start) && Number.isFinite(segment.end) && segment.end > segment.start);
  if (!segments.length) {
    return { ...previewWindow, mode: 'preview_window_v1' };
  }

  const anchorSec = previewWindow.anchorSec;
  let index = segments.findIndex((segment) => segment.start <= anchorSec && anchorSec <= segment.end);
  if (index < 0) {
    index = segments.reduce((bestIndex, segment, currentIndex) => {
      const bestMid = (segments[bestIndex].start + segments[bestIndex].end) / 2;
      const currentMid = (segment.start + segment.end) / 2;
      return Math.abs(currentMid - anchorSec) < Math.abs(bestMid - anchorSec) ? currentIndex : bestIndex;
    }, 0);
  }

  let startSec = segments[index].start;
  let endSec = segments[index].end;
  let left = index - 1;
  let right = index + 1;
  while (left >= 0) {
    const gap = startSec - segments[left].end;
    if (gap > 0.35 || endSec - segments[left].start > 6.0) break;
    startSec = segments[left].start;
    left -= 1;
  }
  while (right < segments.length) {
    const gap = segments[right].start - endSec;
    if (gap > 0.35 || segments[right].end - startSec > 6.0) break;
    endSec = segments[right].end;
    right += 1;
  }

  return {
    startSec: Number(startSec.toFixed(2)),
    endSec: Number(endSec.toFixed(2)),
    anchorSec: Number(anchorSec.toFixed(2)),
    mode: 'transcript_pause_window_v1',
  };
}

function deriveSliceMarkerWindow(
  item: WorkerBundleItem,
  sliceItem?: SliceBundleItem | null
): { startSec: number; endSec: number; anchorSec: number; mode: string } {
  const windows = (sliceItem?.windows || []).filter((window) => Number(window.end_sec) > Number(window.start_sec));
  if (!windows.length) {
    return { ...derivePreviewMarkerWindow(item), mode: 'preview_window_v1' };
  }
  const bestWindow = windows.reduce((best, current) => {
    const bestDuration = Number(best.end_sec) - Number(best.start_sec);
    const currentDuration = Number(current.end_sec) - Number(current.start_sec);
    return currentDuration > bestDuration ? current : best;
  });
  const startSec = Number(Number(bestWindow.start_sec).toFixed(2));
  const endSec = Number(Number(bestWindow.end_sec).toFixed(2));
  return {
    startSec,
    endSec,
    anchorSec: Number(((startSec + endSec) / 2).toFixed(2)),
    mode: String(bestWindow.method || sliceItem?.method || 'energy_pause_v1'),
  };
}

function deriveBestMarkerWindow(
  item: WorkerBundleItem,
  transcriptItem?: TranscriptBundleItem,
  sliceItem?: SliceBundleItem | null
): { startSec: number; endSec: number; anchorSec: number; mode: string } {
  if (sliceItem?.windows?.length) {
    return deriveSliceMarkerWindow(item, sliceItem);
  }
  return deriveTranscriptMarkerWindow(item, transcriptItem);
}

function findTimelineClipBySourcePath(lanes: TimelineLane[], sourcePath: string) {
  for (const lane of lanes) {
    for (const clip of lane.clips) {
      if (clip.source_path === sourcePath) {
        return { lane, clip };
      }
    }
  }
  return null;
}

function findAudioSyncMatch(items: AudioSyncResultItem[], sourcePath: string) {
  return items.find((item) => item.source_path === sourcePath || item.reference_path === sourcePath) || null;
}

function findTimecodeSyncMatch(items: TimecodeSyncResultItem[], sourcePath: string) {
  return items.find((item) => item.source_path === sourcePath || item.reference_path === sourcePath) || null;
}

function findSyncSurfaceMatch(items: SyncSurfaceItem[], sourcePath: string) {
  return items.find((item) => item.source_path === sourcePath || item.reference_path === sourcePath) || null;
}

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
  return (await response.json()) as T;
}

const shellStyle: Record<string, CSSProperties> = {
  root: {
    width: '100vw',
    height: '100vh',
    display: 'grid',
    gridTemplateColumns: '280px minmax(0, 1fr) 320px',
    background: NOLAN_PALETTE.bg,
    color: NOLAN_PALETTE.text,
    fontFamily: 'monospace',
  },
  panel: {
    borderRight: `1px solid ${NOLAN_PALETTE.borderDim}`,
    padding: 16,
    overflow: 'auto',
    background: NOLAN_PALETTE.bgDim,
  },
  panelRight: {
    borderLeft: `1px solid ${NOLAN_PALETTE.borderDim}`,
    padding: 16,
    overflow: 'auto',
    background: NOLAN_PALETTE.bgDim,
  },
  title: { fontSize: 18, fontWeight: 600, marginBottom: 12, color: NOLAN_PALETTE.textAccent, letterSpacing: 0.4 },
  label: { fontSize: 11, color: NOLAN_PALETTE.textMuted, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.4 },
  input: {
    width: '100%',
    background: NOLAN_PALETTE.bgLight,
    color: NOLAN_PALETTE.text,
    border: `1px solid ${NOLAN_PALETTE.border}`,
    borderRadius: 6,
    padding: '10px 12px',
    marginBottom: 10,
  },
  button: {
    width: '100%',
    background: NOLAN_PALETTE.bgLight,
    color: NOLAN_PALETTE.text,
    border: `1px solid ${NOLAN_PALETTE.borderLight}`,
    borderRadius: 6,
    padding: '10px 12px',
    cursor: 'pointer',
    marginBottom: 8,
    fontWeight: 600,
  },
  secondaryButton: {
    width: '100%',
    background: NOLAN_PALETTE.bgLight,
    color: NOLAN_PALETTE.textMuted,
    border: `1px solid ${NOLAN_PALETTE.borderDim}`,
    borderRadius: 6,
    padding: '10px 12px',
    cursor: 'pointer',
    marginBottom: 8,
  },
  smallButton: {
    background: NOLAN_PALETTE.bgLight,
    color: NOLAN_PALETTE.textMuted,
    border: `1px solid ${NOLAN_PALETTE.borderDim}`,
    borderRadius: 4,
    padding: '6px 10px',
    cursor: 'pointer',
    fontSize: 11,
  },
  card: {
    background: NOLAN_PALETTE.bgLight,
    border: `1px solid ${NOLAN_PALETTE.border}`,
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
  },
  code: {
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
    fontSize: 12,
    color: NOLAN_PALETTE.textMuted,
    wordBreak: 'break-all',
  },
  clip: {
    padding: '8px 10px',
    borderRadius: 6,
    background: NOLAN_PALETTE.bg,
    border: `1px solid ${NOLAN_PALETTE.borderDim}`,
    marginBottom: 8,
  },
  muted: { color: NOLAN_PALETTE.textMuted, fontSize: 12 },
  statusOk: { color: NOLAN_PALETTE.text },
  statusWarn: { color: NOLAN_PALETTE.textMuted },
  sectionTitle: { fontSize: 11, fontWeight: 600, marginBottom: 10, color: NOLAN_PALETTE.textAccent, textTransform: 'uppercase', letterSpacing: 0.45 },
};

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
  const query = useMemo(parseQuery, []);
  const [sandboxRoot, setSandboxRoot] = useState(query.sandboxRoot);
  const [sourcePath, setSourcePath] = useState(query.sourcePath);
  const [projectName, setProjectName] = useState(query.projectName || 'VETKA CUT Demo');
  const [projectId, setProjectId] = useState(query.projectId);
  const [projectState, setProjectState] = useState<CutProjectState | null>(null);
  const [status, setStatus] = useState('Idle');
  const [busy, setBusy] = useState(false);
  const [selectedThumbnailId, setSelectedThumbnailId] = useState('');
  const [sceneGraphPaneMode, setSceneGraphPaneMode] = useState<'embedded' | 'peer_pane'>(() => readStoredSceneGraphPaneMode());
  const [showNleSceneGraphDetails, setShowNleSceneGraphDetails] = useState(true);
  const [sceneGraphEdgeFilter, setSceneGraphEdgeFilter] = useState<'all' | 'structural' | 'overlay'>('all');
  const [showActiveMarkersOnly, setShowActiveMarkersOnly] = useState(true);
  const [showGlobalActiveMarkersOnly, setShowGlobalActiveMarkersOnly] = useState(true);
  const [selectedMarkerId, setSelectedMarkerId] = useState('');

  const timelineLanes = (projectState?.timeline_state?.lanes as TimelineLane[] | undefined) || [];
  const selectedClipIds = ((projectState?.timeline_state?.selection as { clip_ids?: string[] } | undefined)?.clip_ids || []).map(String);
  const sceneGraphNodes = (projectState?.scene_graph?.nodes as SceneGraphNode[] | undefined) || [];
  const sceneGraphView = (projectState?.scene_graph_view as CutSceneGraphView | undefined) || null;
  const sceneGraphViewport = useMemo(
    () => buildCutSceneGraphViewportModel(sceneGraphView),
    [sceneGraphView]
  );
  const filteredSceneGraphViewport = useMemo(() => {
    if (!sceneGraphViewport) return null;
    if (sceneGraphEdgeFilter === 'all') return sceneGraphViewport;

    const structuralEdgeIds = new Set(sceneGraphViewport.structuralEdgeIds);
    const overlayEdgeIds = new Set((sceneGraphView?.overlay_edges || []).map((edge) => String((edge as { edge_id?: string }).edge_id || '')));
    const keepEdge = (edge: { id: string }) =>
      sceneGraphEdgeFilter === 'structural' ? structuralEdgeIds.has(edge.id) : overlayEdgeIds.has(edge.id);

    const dagEdges = sceneGraphViewport.dagEdges.filter(keepEdge);
    const structuralNodeIds = new Set(sceneGraphViewport.structuralNodeIds);
    const nodeIdSet = new Set<string>(sceneGraphViewport.rootIds);
    dagEdges.forEach((edge) => {
      nodeIdSet.add(edge.source);
      nodeIdSet.add(edge.target);
    });
    if (sceneGraphEdgeFilter === 'structural') {
      sceneGraphViewport.dagNodes.forEach((node) => {
        if (structuralNodeIds.has(node.primaryNodeId)) nodeIdSet.add(node.id);
      });
    }
    if (sceneGraphViewport.primaryNodeId) {
      const primaryDagId = `cut_graph:${sceneGraphViewport.primaryNodeId}`;
      nodeIdSet.add(primaryDagId);
    }
    sceneGraphViewport.focusNodeIds.forEach((nodeId) => nodeIdSet.add(`cut_graph:${nodeId}`));

    const dagNodes = sceneGraphViewport.dagNodes.filter((node) => nodeIdSet.has(node.id));
    return {
      ...sceneGraphViewport,
      dagNodes,
      dagEdges,
      rootIds: sceneGraphViewport.rootIds.filter((id) => nodeIdSet.has(id)),
      overlayEdgeCount: sceneGraphEdgeFilter === 'overlay' ? dagEdges.length : sceneGraphViewport.overlayEdgeCount,
      structuralNodeIds: sceneGraphEdgeFilter === 'overlay' ? [] : sceneGraphViewport.structuralNodeIds,
    };
  }, [sceneGraphEdgeFilter, sceneGraphView?.overlay_edges, sceneGraphViewport]);
  const waveformItems = (projectState?.waveform_bundle?.items as WorkerBundleItem[] | undefined) || [];
  const transcriptItems = (projectState?.transcript_bundle?.items as TranscriptBundleItem[] | undefined) || [];
  const thumbnailItems = (projectState?.thumbnail_bundle?.items as WorkerBundleItem[] | undefined) || [];
  const audioSyncItems = (projectState?.audio_sync_result?.items as AudioSyncResultItem[] | undefined) || [];
  const sliceItems = (projectState?.slice_bundle?.items as SliceBundleItem[] | undefined) || [];
  const timecodeSyncItems = (projectState?.timecode_sync_result?.items as TimecodeSyncResultItem[] | undefined) || [];
  const syncSurfaceItems = (projectState?.sync_surface?.items as SyncSurfaceItem[] | undefined) || [];
  const timeMarkers = (projectState?.time_marker_bundle?.items as CutTimeMarker[] | undefined) || [];
  const recentJobs = projectState?.recent_jobs || [];
  const activeJobs = projectState?.active_jobs || [];
  const fallbackQuestions = (projectState?.bootstrap_state?.last_stats as Record<string, unknown> | undefined) || null;
  const selectedThumbnail =
    thumbnailItems.find((item) => item.item_id === selectedThumbnailId) || thumbnailItems[0] || null;
  const selectedTimelineMatch = selectedThumbnail ? findTimelineClipBySourcePath(timelineLanes, selectedThumbnail.source_path) : null;
  const selectedTranscriptItem =
    selectedThumbnail ? transcriptItems.find((item) => item.source_path === selectedThumbnail.source_path) : undefined;
  const selectedSliceItem = selectedThumbnail ? sliceItems.find((item) => item.source_path === selectedThumbnail.source_path) : undefined;
  const selectedAudioSyncItem = selectedThumbnail ? findAudioSyncMatch(audioSyncItems, selectedThumbnail.source_path) : null;
  const selectedTimecodeSyncItem = selectedThumbnail ? findTimecodeSyncMatch(timecodeSyncItems, selectedThumbnail.source_path) : null;
  const selectedSyncSurfaceItem = selectedThumbnail ? findSyncSurfaceMatch(syncSurfaceItems, selectedThumbnail.source_path) : null;
  const selectedShotMarkers = timeMarkers
    .filter((marker) => (selectedThumbnail ? marker.media_path === selectedThumbnail.source_path : false))
    .filter((marker) => (showActiveMarkersOnly ? String(marker.status || 'active') === 'active' : true));
  const globalVisibleMarkers = timeMarkers.filter((marker) =>
    showGlobalActiveMarkersOnly ? String(marker.status || 'active') === 'active' : true
  );
  const globalMarkerGroups = {
    favorite: globalVisibleMarkers.filter((marker) => marker.kind === 'favorite'),
    comment: globalVisibleMarkers.filter((marker) => marker.kind === 'comment'),
    cam: globalVisibleMarkers.filter((marker) => marker.kind === 'cam'),
    other: globalVisibleMarkers.filter((marker) => !['favorite', 'comment', 'cam'].includes(marker.kind)),
  };
  const selectedShotMarkerGroups = {
    favorite: selectedShotMarkers.filter((marker) => marker.kind === 'favorite'),
    comment: selectedShotMarkers.filter((marker) => marker.kind === 'comment'),
    cam: selectedShotMarkers.filter((marker) => marker.kind === 'cam'),
    other: selectedShotMarkers.filter((marker) => !['favorite', 'comment', 'cam'].includes(marker.kind)),
  };
  const selectedShotCamMarkers = selectedShotMarkers.filter((marker) => marker.kind === 'cam');
  const selectedStoryboardGraphDagNodeIds = useMemo(() => {
    if (!sceneGraphViewport || !selectedThumbnail?.source_path) return [];
    return sceneGraphViewport.dagIdsBySourcePath[selectedThumbnail.source_path] || [];
  }, [sceneGraphViewport, selectedThumbnail]);
  const selectedTimelineGraphDagNodeIds = useMemo(() => {
    if (!sceneGraphViewport || selectedClipIds.length === 0) return [];
    return Array.from(
      new Set(selectedClipIds.flatMap((clipId) => sceneGraphViewport.dagIdsByClipId[clipId] || []))
    );
  }, [sceneGraphViewport, selectedClipIds]);
  const selectedSceneGraphDagNodeIds = useMemo(
    () =>
      Array.from(
        new Set([
          ...(sceneGraphViewport?.focusNodeIds || []).map((id) => `cut_graph:${id}`),
          ...selectedStoryboardGraphDagNodeIds,
          ...selectedTimelineGraphDagNodeIds,
        ])
      ),
    [sceneGraphViewport, selectedStoryboardGraphDagNodeIds, selectedTimelineGraphDagNodeIds]
  );
  const selectedShotGraphCards = useMemo(() => {
    if (!sceneGraphViewport) return [];
    return selectedSceneGraphDagNodeIds
      .map((dagId) => sceneGraphViewport.nodeByDagId[dagId]?.node_id || '')
      .filter(Boolean)
      .map((nodeId) => sceneGraphViewport.cardByNodeId[nodeId])
      .filter(Boolean);
  }, [sceneGraphViewport, selectedSceneGraphDagNodeIds]);
  const selectedShotPrimaryGraphCard = useMemo(() => {
    if (!sceneGraphViewport) return null;
    if (selectedShotGraphCards.length === 0) return null;
    return (
      selectedShotGraphCards.find((card) => card.nodeId === sceneGraphViewport.primaryNodeId) ||
      selectedShotGraphCards[0] ||
      null
    );
  }, [sceneGraphViewport, selectedShotGraphCards]);

  const selectedShotGraphSyncBadges = useMemo(
    () => Array.from(new Set(selectedShotGraphCards.map((card) => card.syncBadge).filter(Boolean))),
    [selectedShotGraphCards]
  );
  const selectedShotGraphBuckets = useMemo(
    () => Array.from(new Set(selectedShotGraphCards.map((card) => card.visualBucket).filter(Boolean))),
    [selectedShotGraphCards]
  );
  const selectedShotInspectorNodes = useMemo(() => {
    if (!sceneGraphViewport) return [];
    const nodeIds = new Set(selectedShotGraphCards.map((card) => card.nodeId));
    return sceneGraphViewport.inspectorNodes.filter((node) => nodeIds.has(node.node_id));
  }, [sceneGraphViewport, selectedShotGraphCards]);
  const selectedShotGraphFocusSource = useMemo(() => {
    if (selectedTimelineGraphDagNodeIds.length) return 'timeline + storyboard crosslinks';
    if (selectedStoryboardGraphDagNodeIds.length) return 'storyboard crosslinks';
    if (sceneGraphViewport?.focusNodeIds.length) return 'scene graph anchor only';
    return 'none';
  }, [sceneGraphViewport, selectedStoryboardGraphDagNodeIds, selectedTimelineGraphDagNodeIds]);
  const selectedShotGraphMarkerCount = useMemo(
    () => selectedShotGraphCards.reduce((sum, card) => sum + Number(card.markerCount || 0), 0),
    [selectedShotGraphCards]
  );


  const refreshProjectState = useCallback(async (currentProjectId?: string, options?: { silent?: boolean }) => {
    const pid = String(currentProjectId || projectId || '').trim();
    if (!sandboxRoot || !pid) return;
    if (!options?.silent) {
      setStatus('Hydrating project state...');
    }
    const payload = await jsonFetch<CutProjectState>(
      `/cut/project-state?sandbox_root=${encodeURIComponent(sandboxRoot)}&project_id=${encodeURIComponent(pid)}`
    );
    setProjectState(payload);
    if (payload.success) {
      setProjectId(String(payload.project?.project_id || pid));
      if (!options?.silent) {
        setStatus(payload.runtime_ready ? 'Runtime ready' : 'Project loaded');
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

  useEffect(() => {
    editorSetLanes(timelineLanes);
  }, [timelineLanes, editorSetLanes]);
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
      timelineId: String(projectState?.timeline_state?.timeline_id || 'main'),
      refreshProjectState: async () => {
        await refreshProjectState(projectId || undefined, { silent: true });
      },
    });
  }, [sandboxRoot, projectId, projectState?.timeline_state, refreshProjectState, editorSetSession]);
  useEffect(() => {
    editorSetSceneGraphSurfaceMode(sceneGraphPaneMode === 'peer_pane' ? 'nle_ready' : 'shell_only');
  }, [sceneGraphPaneMode, editorSetSceneGraphSurfaceMode]);

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
      setProjectId(payload.project.project_id);
      await refreshProjectState(payload.project.project_id);
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

  async function handleSyncSelectedShotToTimeline() {
    if (!sandboxRoot || !projectId || !selectedTimelineMatch) return;
    setBusy(true);
    try {
      setStatus('Syncing selected shot to timeline...');
      const payload = await jsonFetch<{ success: boolean; error?: { message?: string } }>('/cut/timeline/apply', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: 'main',
          author: 'cut_shell',
          ops: [
            {
              op: 'set_selection',
              clip_ids: [selectedTimelineMatch.clip.clip_id],
              scene_ids: selectedTimelineMatch.clip.scene_id ? [selectedTimelineMatch.clip.scene_id] : [],
            },
            {
              op: 'set_view',
              active_lane_id: selectedTimelineMatch.lane.lane_id,
            },
          ],
        }),
      });
      if (!payload.success) throw new Error(payload.error?.message || 'Timeline sync failed');
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Timeline sync failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleApplySelectedSyncOffset() {
    if (!sandboxRoot || !projectId || !selectedTimelineMatch || !selectedSyncSurfaceItem || !selectedSyncSurfaceItem.recommended_method) {
      return;
    }
    setBusy(true);
    try {
      setStatus('Applying sync offset to timeline...');
      const payload = await jsonFetch<{ success: boolean; error?: { message?: string } }>('/cut/timeline/apply', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: 'main',
          author: 'cut_shell',
          ops: [
            {
              op: 'apply_sync_offset',
              clip_id: selectedTimelineMatch.clip.clip_id,
              offset_sec: Number(selectedSyncSurfaceItem.recommended_offset_sec || 0),
              method: String(selectedSyncSurfaceItem.recommended_method),
              confidence: Number(selectedSyncSurfaceItem.confidence || 0),
              reference_path: selectedSyncSurfaceItem.reference_path,
              source: 'sync_surface',
              group_id: `sync_${selectedTimelineMatch.clip.clip_id}`,
            },
          ],
        }),
      });
      if (!payload.success) throw new Error(payload.error?.message || 'Timeline sync apply failed');
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Timeline sync apply failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleApplyAllSyncOffsets() {
    if (!sandboxRoot || !projectId) return;
    const actionable = syncSurfaceItems.filter(
      (item) => item.recommended_method && item.recommended_offset_sec !== 0
    );
    if (actionable.length === 0) {
      setStatus('No actionable sync recommendations.');
      return;
    }
    setBusy(true);
    try {
      setStatus(`Applying ${actionable.length} sync offset(s)...`);
      const ops = actionable
        .map((item) => {
          const match = findTimelineClipBySourcePath(timelineLanes, item.source_path);
          if (!match) return null;
          return {
            op: 'apply_sync_offset',
            clip_id: match.clip.clip_id,
            offset_sec: Number(item.recommended_offset_sec || 0),
            method: String(item.recommended_method),
            confidence: Number(item.confidence || 0),
            reference_path: item.reference_path,
            source: 'sync_surface',
            group_id: `sync_${match.clip.clip_id}`,
          };
        })
        .filter(Boolean);
      if (ops.length === 0) {
        setStatus('No clips matched sync surface items in timeline.');
        setBusy(false);
        return;
      }
      const payload = await jsonFetch<{ success: boolean; error?: { message?: string } }>('/cut/timeline/apply', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: 'main',
          author: 'cut_shell',
          ops,
        }),
      });
      if (!payload.success) throw new Error(payload.error?.message || 'Batch sync apply failed');
      await refreshProjectState(projectId);
      setStatus(`Applied ${ops.length} sync offset(s).`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Batch sync apply failed');
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

  async function handleFocusMarkerInTimeline(marker: CutTimeMarker) {
    if (!sandboxRoot || !projectId || !selectedTimelineMatch) return;
    setBusy(true);
    try {
      setStatus('Focusing marker in timeline...');
      const payload = await jsonFetch<{ success: boolean; error?: { message?: string } }>('/cut/timeline/apply', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: 'main',
          author: 'cut_shell',
          ops: [
            {
              op: 'set_selection',
              clip_ids: [selectedTimelineMatch.clip.clip_id],
              scene_ids: selectedTimelineMatch.clip.scene_id ? [selectedTimelineMatch.clip.scene_id] : [],
            },
            {
              op: 'set_view',
              active_lane_id: selectedTimelineMatch.lane.lane_id,
              scroll_sec: Number(marker.start_sec || 0),
              zoom: 1.5,
            },
          ],
        }),
      });
      if (!payload.success) throw new Error(payload.error?.message || 'Timeline marker focus failed');
      setSelectedMarkerId(marker.marker_id);
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Timeline marker focus failed');
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

  async function handleTranscriptNormalize() {
    if (!sandboxRoot || !projectId) return;
    setBusy(true);
    try {
      setStatus('Normalizing transcripts...');
      const created = await jsonFetch<CutJobEnvelope>('/cut/worker/transcript-normalize-async', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          limit: 6,
          segments_limit: 128,
          max_transcribe_sec: 180,
        }),
      });
      if (!created.success || !created.job_id) {
        setStatus('Transcript worker did not start');
        return;
      }
      await waitForJob(created.job_id);
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Transcript normalize failed');
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

  async function handleCancelJob(jobId: string) {
    if (!jobId) return;
    setBusy(true);
    try {
      setStatus(`Cancelling job ${jobId.slice(0, 8)}...`);
      await jsonFetch<{ success: boolean; job?: { state?: string } }>('/cut/job/' + encodeURIComponent(jobId) + '/cancel', {
        method: 'POST',
      });
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Cancel failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateTimeMarker(item: WorkerBundleItem, kind: 'favorite' | 'comment' | 'cam') {
    if (!sandboxRoot || !projectId || !item.source_path) return;
    const text =
      kind === 'comment'
        ? window.prompt('Comment marker text', 'CUT note') || ''
        : kind === 'cam'
          ? window.prompt('CAM marker hint', 'context signal') || ''
        : '';
    const transcriptItem = transcriptItems.find((entry) => entry.source_path === item.source_path);
    const sliceItem = sliceItems.find((entry) => entry.source_path === item.source_path);
    const markerWindow = deriveBestMarkerWindow(item, transcriptItem, sliceItem);
    setBusy(true);
    try {
      setStatus(
        kind === 'favorite'
          ? 'Creating favorite moment...'
          : kind === 'comment'
            ? 'Creating comment marker...'
            : 'Creating CAM marker...'
      );
      const payload = await jsonFetch<{ success: boolean; error?: { message?: string } }>('/cut/time-markers/apply', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: 'main',
          author: 'cut_shell',
          op: 'create',
          media_path: item.source_path,
          kind,
          start_sec: markerWindow.startSec,
          end_sec: markerWindow.endSec,
          anchor_sec: markerWindow.anchorSec,
          score: kind === 'favorite' ? 1.0 : kind === 'comment' ? 0.7 : 0.85,
          text,
          context_slice: {
            mode: markerWindow.mode,
            derived_from:
              markerWindow.mode === 'energy_pause_v1'
                ? 'slice_bundle'
                : markerWindow.mode === 'transcript_pause_window_v1'
                  ? 'transcript_bundle'
                  : 'thumbnail_bundle',
            duration_sec: Number(item.duration_sec) || 0,
            poster_url: item.poster_url || '',
            animated_preview_url_300ms: item.animated_preview_url_300ms || '',
          },
          cam_payload:
            kind === 'cam'
              ? {
                  source: 'cut_shell',
                  hint: text || 'context signal',
                  status: 'placeholder',
                }
              : null,
          source_engine: 'cut_shell',
        }),
      });
      if (!payload.success) throw new Error(payload.error?.message || 'Time marker apply failed');
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Time marker apply failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleArchiveTimeMarker(markerId: string) {
    if (!sandboxRoot || !projectId || !markerId) return;
    setBusy(true);
    try {
      setStatus('Archiving marker...');
      const payload = await jsonFetch<{ success: boolean; error?: { message?: string } }>('/cut/time-markers/apply', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: 'main',
          author: 'cut_shell',
          op: 'archive',
          marker_id: markerId,
        }),
      });
      if (!payload.success) throw new Error(payload.error?.message || 'Time marker archive failed');
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Time marker archive failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleAddDirectorNote() {
    const sceneNode = sceneGraphNodes.find((node) => node.node_type === 'scene');
    if (!sceneNode || !sandboxRoot || !projectId) return;
    setBusy(true);
    try {
      const payload = await jsonFetch<{ success: boolean; error?: { message?: string } }>('/cut/scene-graph/apply', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          graph_id: 'main',
          author: 'cut_shell',
          ops: [
            {
              op: 'add_note',
              label: 'Director note',
              text: 'CUT shell note',
              target_node_id: sceneNode.node_id,
            },
          ],
        }),
      });
      if (!payload.success) throw new Error(payload.error?.message || 'Scene graph apply failed');
      await refreshProjectState(projectId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Scene graph apply failed');
    } finally {
      setBusy(false);
    }
  }

  // ─── MARKER_170.NLE: NLE layout wraps the debug shell ───
  const nleSceneGraphSurface = !sceneGraphViewport || sceneGraphViewport.cards.length === 0 ? (
    <div style={shellStyle.muted}>No graph nodes available. Open a CUT project and run scene assembly.</div>
  ) : (
    <>
      <div style={shellStyle.sectionTitle}>Viewport Priority</div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <button
          style={shellStyle.smallButton}
          onClick={() => setShowNleSceneGraphDetails((value) => !value)}
        >
          {showNleSceneGraphDetails ? 'Hide Details' : 'Show Details'}
        </button>
        <button style={shellStyle.smallButton} onClick={() => setSceneGraphEdgeFilter('all')}>
          All Edges
        </button>
        <button style={shellStyle.smallButton} onClick={() => setSceneGraphEdgeFilter('structural')}>
          Structural Only
        </button>
        <button style={shellStyle.smallButton} onClick={() => setSceneGraphEdgeFilter('overlay')}>
          Overlay Only
        </button>
      </div>
      <div style={shellStyle.muted}>Shared DAG viewport mounted inside NLE pane.</div>
      <div style={shellStyle.muted}>edge filter: {sceneGraphEdgeFilter}</div>
      <div style={shellStyle.muted}>
        edge legend: nodes {(filteredSceneGraphViewport?.dagNodes || sceneGraphViewport.dagNodes).length} · edges {(filteredSceneGraphViewport?.dagEdges || sceneGraphViewport.dagEdges).length} · structural {sceneGraphViewport.structuralEdgeIds.length} · overlay {sceneGraphViewport.overlayEdgeCount}
      </div>
      <div style={shellStyle.muted}>roots {filteredSceneGraphViewport?.rootIds.length || 0} · structural {filteredSceneGraphViewport?.structuralNodeIds.length || 0} · overlays {filteredSceneGraphViewport?.overlayEdgeCount || 0}</div>
      <div style={{ height: 240, border: `1px solid ${NOLAN_PALETTE.borderDim}`, borderRadius: 8, overflow: 'hidden' }}>
        <ReactFlowProvider>
          <DAGView
            dagNodes={filteredSceneGraphViewport?.dagNodes || sceneGraphViewport.dagNodes}
            dagEdges={filteredSceneGraphViewport?.dagEdges || sceneGraphViewport.dagEdges}
            selectedNodeIds={selectedSceneGraphDagNodeIds}
            onNodeSelect={handleSceneGraphNodeSelect}
            graphIdentity={`cut_scene_graph_nle:${sceneGraphViewport.graphId}`}
            layoutMode="workflow"
            compact
            width="100%"
            height="100%"
          />
        </ReactFlowProvider>
      </div>
      <div style={shellStyle.muted}>NLE pane now reuses the shared DAG viewport bridge.</div>
      {showNleSceneGraphDetails ? (
        <>
          <div style={shellStyle.sectionTitle}>Selection Summary</div>
          <div style={shellStyle.muted}>clip-linked graph nodes: {selectedShotGraphCards.length}</div>
          <div style={shellStyle.muted}>
            active graph node: {selectedShotPrimaryGraphCard ? `${selectedShotPrimaryGraphCard.label} · ${selectedShotPrimaryGraphCard.nodeType}` : 'none'}
          </div>
          <div style={shellStyle.muted}>
            pane inspector link: {selectedShotInspectorNodes.length ? selectedShotInspectorNodes.map((node) => node.label).join(' · ') : 'no linked inspector node'}
          </div>
          <div style={shellStyle.muted}>focus source: {selectedShotGraphFocusSource}</div>
          <div style={shellStyle.muted}>graph buckets: {selectedShotGraphBuckets.length ? selectedShotGraphBuckets.join(', ') : 'none'}</div>
          <div style={shellStyle.sectionTitle}>Media Card</div>
          <div style={{ ...shellStyle.clip, marginBottom: 0, padding: '8px 10px' }}>
        <div>Compact Graph Card</div>
        {selectedShotPrimaryGraphCard?.posterUrl ? (
          <img
            src={selectedShotPrimaryGraphCard.posterUrl}
            alt={selectedShotPrimaryGraphCard.label}
            style={{ width: '100%', height: 88, objectFit: 'cover', borderRadius: 6, marginBottom: 8 }}
          />
        ) : (
          <div
            style={{
              height: 88,
              borderRadius: 6,
              marginBottom: 8,
              background: NOLAN_PALETTE.bgDim,
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: NOLAN_PALETTE.textMuted,
              fontSize: 11,
            }}
          >
            no poster preview
          </div>
        )}
        <div style={shellStyle.muted}>
          {selectedShotPrimaryGraphCard
            ? `${selectedShotPrimaryGraphCard.label} · ${selectedShotPrimaryGraphCard.nodeType}`
            : 'no primary graph card'}
        </div>
        <div style={shellStyle.muted}>
          {selectedShotPrimaryGraphCard?.displayMode || 'display unknown'} · {selectedShotPrimaryGraphCard?.modality || 'n/a'}
          {typeof selectedShotPrimaryGraphCard?.durationSec === 'number' ? ` · ${selectedShotPrimaryGraphCard.durationSec.toFixed(1)}s` : ''}
        </div>
        <div style={shellStyle.muted}>markers {selectedShotPrimaryGraphCard?.markerCount || 0}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span
            style={{
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 999,
              border: `1px solid ${selectedShotPrimaryGraphCard?.syncBadge ? '#22c55e88' : NOLAN_PALETTE.borderDim}` ,
              color: selectedShotPrimaryGraphCard?.syncBadge ? '#22c55e' : NOLAN_PALETTE.textMuted,
              background: selectedShotPrimaryGraphCard?.syncBadge ? '#22c55e22' : 'transparent',
            }}
          >
            {selectedShotPrimaryGraphCard?.syncBadge ? `sync ${selectedShotPrimaryGraphCard.syncBadge}` : 'no sync badge'}
          </span>
          <span style={shellStyle.muted}>
            {selectedShotPrimaryGraphCard?.visualBucket ? `bucket ${selectedShotPrimaryGraphCard.visualBucket}` : 'no bucket'}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
          {selectedShotInspectorNodes.length ? (
            selectedShotInspectorNodes.map((node) => (
              <span
                key={`inspector-chip-${node.node_id}`}
                style={{
                  fontSize: 10,
                  padding: '2px 6px',
                  borderRadius: 999,
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  color: NOLAN_PALETTE.textMuted,
                  background: NOLAN_PALETTE.bgDim,
                }}
              >
                inspector {node.label}
              </span>
            ))
          ) : (
            <span style={shellStyle.muted}>no inspector chips</span>
          )}
        </div>
          </div>
        </>
      ) : (
        <div style={shellStyle.muted}>secondary summaries collapsed</div>
      )}
      <div style={shellStyle.sectionTitle}>Actions</div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button style={shellStyle.smallButton} onClick={() => void handleSyncSelectedShotToTimeline()} disabled={busy || !projectId || !selectedTimelineMatch}>
          Focus Timeline From Graph
        </button>
        <button style={shellStyle.smallButton} onClick={() => selectedThumbnail && setSelectedThumbnailId(selectedThumbnail.item_id)} disabled={busy || !selectedThumbnail}>
          Focus Selected Shot
        </button>
      </div>
    </>
  );

  const debugShell = (
    <div style={shellStyle.root}>
      <aside style={shellStyle.panel}>
        <div style={shellStyle.title}>VETKA CUT</div>
        <div style={shellStyle.label}>Sandbox Root</div>
        <input style={shellStyle.input} value={sandboxRoot} onChange={(e) => setSandboxRoot(e.target.value)} />
        <div style={shellStyle.label}>Source Path</div>
        <input style={shellStyle.input} value={sourcePath} onChange={(e) => setSourcePath(e.target.value)} />
        <div style={shellStyle.label}>Project Name</div>
        <input style={shellStyle.input} value={projectName} onChange={(e) => setProjectName(e.target.value)} />
        <button style={shellStyle.button} onClick={handleBootstrap} disabled={busy || !sandboxRoot || !sourcePath}>
          Open CUT Project
        </button>
        <button style={shellStyle.secondaryButton} onClick={() => void refreshProjectState()} disabled={busy || !sandboxRoot || !projectId}>
          Refresh Project State
        </button>
        <button
          style={shellStyle.secondaryButton}
          onClick={handleSceneAssembly}
          disabled={busy || !sandboxRoot || !projectId || Boolean(projectState?.runtime_ready)}
        >
          Start Scene Assembly
        </button>
        <div style={shellStyle.card}>
          <div style={shellStyle.sectionTitle}>Status</div>
          <div style={projectState?.success ? shellStyle.statusOk : shellStyle.statusWarn}>{status}</div>
          {projectId ? <div style={shellStyle.code}>{projectId}</div> : null}
        </div>
        <div style={shellStyle.card}>
          <div style={shellStyle.sectionTitle}>Shell Actions</div>
          <button style={shellStyle.secondaryButton} onClick={handleSelectFirstClip} disabled={busy || !projectState?.runtime_ready}>
            Select First Clip
          </button>
          <button style={shellStyle.secondaryButton} onClick={handleAddDirectorNote} disabled={busy || !projectState?.graph_ready}>
            Add Director Note
          </button>
          <button style={shellStyle.secondaryButton} onClick={handleWaveformBuild} disabled={busy || !projectId}>
            Build Waveforms
          </button>
          <button style={shellStyle.secondaryButton} onClick={handleTranscriptNormalize} disabled={busy || !projectId}>
            Normalize Transcripts
          </button>
          <button style={shellStyle.secondaryButton} onClick={handleThumbnailBuild} disabled={busy || !projectId}>
            Build Thumbnails
          </button>
          <button style={shellStyle.secondaryButton} onClick={handleTimecodeSyncBuild} disabled={busy || !projectId}>
            Build Timecode Sync
          </button>
          <button style={shellStyle.secondaryButton} onClick={handleAudioSyncBuild} disabled={busy || !projectId}>
            Build Audio Sync
          </button>
          <button style={shellStyle.secondaryButton} onClick={handlePauseSliceBuild} disabled={busy || !projectId}>
            Build Pause Slices
          </button>
          <button style={shellStyle.secondaryButton} onClick={handleRunMetaSync} disabled={busy || !projectId}>
            Build Meta Sync
          </button>
          <button
            style={{ ...shellStyle.secondaryButton, background: syncSurfaceItems.some((item) => item.recommended_method && item.recommended_offset_sec !== 0) ? '#166534' : undefined }}
            onClick={handleApplyAllSyncOffsets}
            disabled={busy || !projectId || !syncSurfaceItems.some((item) => item.recommended_method && item.recommended_offset_sec !== 0)}
          >
            Apply All Syncs ({syncSurfaceItems.filter((item) => item.recommended_method && item.recommended_offset_sec !== 0).length})
          </button>
        </div>
      </aside>

      <main
        style={{
          padding: 16,
          overflow: 'auto',
          display: 'grid',
          gap: 16,
          gridTemplateColumns: sceneGraphPaneMode === 'peer_pane' ? 'minmax(0, 1.4fr) minmax(420px, 0.9fr)' : 'minmax(0, 1fr)',
          alignItems: 'start',
        }}
      >
        <div style={{ display: 'grid', gap: 16 }}>
        <div style={{ ...shellStyle.card, minHeight: 220, opacity: sceneGraphPaneMode === 'peer_pane' ? 0.9 : 1 }}>
          <div style={shellStyle.sectionTitle}>Timeline Surface</div>
          {!projectState?.runtime_ready ? (
            <div style={shellStyle.muted}>Timeline not ready. Run scene assembly.</div>
          ) : timelineLanes.length === 0 ? (
            <div style={shellStyle.muted}>No lanes available.</div>
          ) : (
            timelineLanes.map((lane) => (
              <div key={lane.lane_id} style={{ marginBottom: 14 }}>
                <div style={{ ...shellStyle.muted, marginBottom: 8 }}>
                  {lane.lane_id} / {lane.lane_type}
                </div>
                {lane.clips.map((clip) => (
                  <div
                    key={clip.clip_id}
                    style={{
                      ...shellStyle.clip,
                      border:
                        selectedClipIds.includes(clip.clip_id)
                          ? `1px solid ${NOLAN_PALETTE.textAccent}`
                          : `1px solid ${NOLAN_PALETTE.borderDim}`,
                    }}
                  >
                    <div>{clip.clip_id}</div>
                    <div style={shellStyle.muted}>{clip.source_path.split('/').pop()}</div>
                    <div style={shellStyle.muted}>
                      start {clip.start_sec}s · duration {clip.duration_sec}s
                    </div>
                    {selectedClipIds.includes(clip.clip_id) ? <div style={shellStyle.muted}>timeline selected</div> : null}
                  </div>
                ))}
              </div>
            ))
          )}
        </div>

        </div>

        <div
          style={{
            ...shellStyle.card,
            border: sceneGraphPaneMode === 'peer_pane' ? `1px solid ${NOLAN_PALETTE.textAccent}` : `1px solid ${NOLAN_PALETTE.borderDim}`,
            position: sceneGraphPaneMode === 'peer_pane' ? 'sticky' : 'static',
            top: sceneGraphPaneMode === 'peer_pane' ? 16 : undefined,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 10 }}>
            <div style={shellStyle.sectionTitle}>Scene Graph Surface</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                style={shellStyle.smallButton}
                onClick={() => setSceneGraphPaneMode('embedded')}
                disabled={busy || sceneGraphPaneMode === 'embedded'}
              >
                Embed In Flow
              </button>
              <button
                style={shellStyle.smallButton}
                onClick={() => setSceneGraphPaneMode('peer_pane')}
                disabled={busy || sceneGraphPaneMode === 'peer_pane'}
              >
                Promote To Peer Pane
              </button>
            </div>
          </div>
          {!projectState?.graph_ready ? (
            <div style={shellStyle.muted}>Scene graph not ready. Open a CUT project and run scene assembly.</div>
          ) : !sceneGraphViewport || sceneGraphViewport.cards.length === 0 ? (
            <div style={shellStyle.muted}>No graph nodes available. Open a CUT project and run scene assembly.</div>
          ) : (
            <>
              <div style={shellStyle.muted}>
                viewport roots: {sceneGraphViewport.rootIds.length} · structural nodes: {sceneGraphViewport.structuralNodeIds.length} · overlays:{' '}
                {sceneGraphViewport.overlayEdgeCount}
              </div>
              <div
                style={{
                  height: sceneGraphPaneMode === 'peer_pane' ? 480 : 320,
                  marginTop: 12,
                  marginBottom: 12,
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 8,
                  overflow: 'hidden',
                }}
              >
                <ReactFlowProvider>
                  <DAGView
                    dagNodes={sceneGraphViewport.dagNodes}
                    dagEdges={sceneGraphViewport.dagEdges}
                    selectedNodeIds={selectedSceneGraphDagNodeIds}
                    onNodeSelect={handleSceneGraphNodeSelect}
                    graphIdentity={`cut_scene_graph:${sceneGraphViewport.graphId}`}
                    layoutMode="workflow"
                    compact
                    width="100%"
                    height="100%"
                  />
                </ReactFlowProvider>
              </div>
              <div style={shellStyle.muted}>
                Scene Graph DAG viewport is explicit. Cards and inspector remain visible beside graph navigation.
              </div>
              <div style={shellStyle.muted}>
                Graph focus follows storyboard + timeline context through source-path and clip crosslinks.
              </div>
              <div style={shellStyle.muted}>
                pane mode: {sceneGraphPaneMode === 'peer_pane' ? 'peer product surface preview' : 'embedded debug-shell flow'}
              </div>
              <div style={shellStyle.muted}>
                layout slot: {sceneGraphPaneMode === 'peer_pane' ? 'right peer pane beside timeline/storyboard stack' : 'inline shell flow card'}
              </div>
              <div style={shellStyle.muted}>
                persistence: pane mode restores on CUT reload via localStorage preference
              </div>
              {sceneGraphViewport.cards.map((node) => (
                <div
                  key={node.nodeId}
                  style={{
                    ...shellStyle.clip,
                    border: node.isPrimary
                      ? `1px solid ${NOLAN_PALETTE.textAccent}`
                      : selectedSceneGraphDagNodeIds.includes(`cut_graph:${node.nodeId}`)
                        ? `1px solid ${NOLAN_PALETTE.borderLight}`
                        : node.isFocused
                          ? `1px solid ${NOLAN_PALETTE.borderLight}`
                          : `1px solid ${NOLAN_PALETTE.borderDim}`,
                  }}
                >
                  <div>{node.label}</div>
                  <div style={shellStyle.muted}>
                    {node.nodeId} · {node.nodeType} · {node.displayMode}
                  </div>
                  <div style={shellStyle.muted}>{node.summary}</div>
                  <div style={shellStyle.muted}>
                    modality: {node.modality || 'n/a'} · markers: {node.markerCount}
                    {typeof node.durationSec === 'number' ? ` · ${node.durationSec.toFixed(1)}s` : ''}
                  </div>
                  <div style={shellStyle.muted}>
                    bucket: {node.visualBucket}
                    {node.syncBadge ? ` · sync ${node.syncBadge}` : ''}
                  </div>
                  {node.posterUrl ? (
                    <div style={shellStyle.muted}>preview: poster attached</div>
                  ) : null}
                </div>
              ))}
              {sceneGraphViewport.inspectorNodes.length ? (
                <div style={{ marginTop: 8 }}>
                  <div style={shellStyle.sectionTitle}>Scene Graph Inspector</div>
                  {sceneGraphViewport.inspectorNodes.map((node) => {
                    const selectedShotLinked = selectedShotGraphCards.some((card) => card.nodeId === node.node_id);
                    return (
                      <div
                        key={node.node_id}
                        style={{
                          ...shellStyle.clip,
                          border: selectedShotLinked
                            ? `1px solid ${NOLAN_PALETTE.textAccent}`
                            : `1px solid ${NOLAN_PALETTE.borderDim}`,
                        }}
                      >
                        <div>{node.label}</div>
                        <div style={shellStyle.muted}>{node.summary}</div>
                        <div style={shellStyle.muted}>
                          clips {node.related_clip_ids.length} · sources {node.related_source_paths.length}
                        </div>
                        <div style={shellStyle.muted}>
                          {selectedShotLinked ? 'selected-shot linked inspector node' : 'graph-focused inspector node'}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : null}
              <div style={shellStyle.muted}>
                first-class viewport adapter ready: dag nodes {sceneGraphViewport.dagNodes.length} · dag edges {sceneGraphViewport.dagEdges.length}
              </div>
            </>
          )}
        </div>

        <div style={shellStyle.card}>
          <div style={shellStyle.sectionTitle}>Worker Outputs</div>
          <div style={shellStyle.muted}>waveforms: {waveformItems.length}</div>
          <div style={shellStyle.muted}>transcripts: {transcriptItems.length}</div>
          <div style={shellStyle.muted}>thumbnails: {thumbnailItems.length}</div>
          <div style={shellStyle.muted}>timecode_sync: {timecodeSyncItems.length}</div>
          <div style={shellStyle.muted}>audio_sync: {audioSyncItems.length}</div>
          <div style={shellStyle.muted}>pause_slices: {sliceItems.length}</div>
          <div style={shellStyle.muted}>time_markers: {timeMarkers.length}</div>
          {waveformItems.slice(0, 3).map((item) => (
            <div key={item.item_id} style={shellStyle.clip}>
              <div>WF · {item.source_path.split('/').pop()}</div>
              <div style={shellStyle.muted}>{item.degraded_mode ? item.degraded_reason || 'degraded' : 'ready'}</div>
            </div>
          ))}
          {transcriptItems.slice(0, 3).map((item) => (
            <div key={item.item_id} style={shellStyle.clip}>
              <div>TX · {item.source_path.split('/').pop()}</div>
              <div style={shellStyle.muted}>{item.degraded_mode ? item.degraded_reason || 'degraded' : 'ready'}</div>
            </div>
          ))}
          {audioSyncItems.slice(0, 3).map((item) => (
            <div key={item.item_id} style={shellStyle.clip}>
              <div>SYNC · {item.source_path.split('/').pop()}</div>
              <div style={shellStyle.muted}>
                offset {Number(item.detected_offset_sec || 0).toFixed(3)}s · conf {Number(item.confidence || 0).toFixed(2)}
              </div>
              <div style={shellStyle.muted}>{item.method}</div>
            </div>
          ))}
          {timecodeSyncItems.slice(0, 3).map((item) => (
            <div key={item.item_id} style={shellStyle.clip}>
              <div>TC · {item.source_path.split('/').pop()}</div>
              <div style={shellStyle.muted}>
                {item.reference_timecode} {'→'} {item.source_timecode}
              </div>
              <div style={shellStyle.muted}>
                offset {Number(item.detected_offset_sec || 0).toFixed(3)}s · fps {item.fps}
              </div>
            </div>
          ))}
          {!waveformItems.length && !transcriptItems.length && !thumbnailItems.length ? (
            <div style={shellStyle.muted}>No worker bundles available.</div>
          ) : null}
        </div>

        <div style={{ ...shellStyle.card, opacity: sceneGraphPaneMode === 'peer_pane' ? 0.9 : 1 }}>
          <div style={shellStyle.sectionTitle}>Storyboard Strip</div>
          {!thumbnailItems.length ? (
            <div style={shellStyle.muted}>No thumbnails yet. Run thumbnail build.</div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 12 }}>
              {thumbnailItems.slice(0, 8).map((item) => (
                <div
                  key={item.item_id}
                  style={{
                    ...shellStyle.clip,
                    marginBottom: 0,
                    border:
                      selectedThumbnail?.item_id === item.item_id
                        ? `1px solid ${NOLAN_PALETTE.textAccent}`
                        : `1px solid ${NOLAN_PALETTE.borderDim}`,
                  }}
                >
                  {item.poster_url ? (
                    <img
                      src={item.poster_url}
                      alt={item.source_path.split('/').pop() || item.item_id}
                      style={{ width: '100%', height: 90, objectFit: 'cover', borderRadius: 6, marginBottom: 8 }}
                    />
                  ) : (
                    <div style={{ height: 90, borderRadius: 6, marginBottom: 8, background: NOLAN_PALETTE.bgDim, border: `1px solid ${NOLAN_PALETTE.borderDim}` }} />
                  )}
                  <div>{item.source_path.split('/').pop()}</div>
                  <div style={shellStyle.muted}>{item.modality || 'media'}</div>
                  {(() => {
                    const syncMatch = findSyncSurfaceMatch(syncSurfaceItems, item.source_path);
                    if (!syncMatch || !syncMatch.recommended_method) return null;
                    const methodColors: Record<string, string> = { timecode: '#22c55e', waveform: '#3b82f6', meta_sync: '#a855f7' };
                    const color = methodColors[syncMatch.recommended_method] || NOLAN_PALETTE.textMuted;
                    return (
                      <div style={{ fontSize: 11, marginTop: 4, padding: '2px 6px', borderRadius: 4, background: `${color}22`, border: `1px solid ${color}55`, color }}>
                        Sync Badge {syncMatch.recommended_method} {Number(syncMatch.recommended_offset_sec).toFixed(3)}s ({(syncMatch.confidence * 100).toFixed(0)}%)
                      </div>
                    );
                  })()}
                  <div style={shellStyle.muted}>
                    marker window {deriveBestMarkerWindow(item, transcriptItems.find((entry) => entry.source_path === item.source_path), sliceItems.find((entry) => entry.source_path === item.source_path)).startSec}s - {deriveBestMarkerWindow(item, transcriptItems.find((entry) => entry.source_path === item.source_path), sliceItems.find((entry) => entry.source_path === item.source_path)).endSec}s
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <button style={shellStyle.smallButton} onClick={() => setSelectedThumbnailId(item.item_id)} disabled={busy}>
                      Select Shot
                    </button>
                    <button
                      style={shellStyle.smallButton}
                      onClick={() => void handleCreateTimeMarker(item, 'favorite')}
                      disabled={busy || !projectId}
                    >
                      Favorite Moment
                    </button>
                    <button
                      style={shellStyle.smallButton}
                      onClick={() => void handleCreateTimeMarker(item, 'comment')}
                      disabled={busy || !projectId}
                    >
                      Comment Marker
                    </button>
                    <button
                      style={shellStyle.smallButton}
                      onClick={() => void handleCreateTimeMarker(item, 'cam')}
                      disabled={busy || !projectId}
                    >
                      CAM Marker
                    </button>
                    <a
                      href={item.source_url || '#'}
                      style={{ ...shellStyle.smallButton, textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open Preview
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      <aside style={shellStyle.panelRight}>
        <div style={shellStyle.card}>
          <div style={shellStyle.sectionTitle}>Selected Shot</div>
          {!selectedThumbnail ? (
            <div style={shellStyle.muted}>No storyboard item selected.</div>
          ) : (
            <>
              <div>{selectedThumbnail.source_path.split('/').pop()}</div>
              <div style={shellStyle.muted}>{selectedThumbnail.modality || 'media'}</div>
              <div style={shellStyle.muted}>duration: {Number(selectedThumbnail.duration_sec || 0).toFixed(2)}s</div>
              <div style={shellStyle.muted}>
                marker window {deriveBestMarkerWindow(selectedThumbnail, selectedTranscriptItem, selectedSliceItem).startSec}s - {deriveBestMarkerWindow(selectedThumbnail, selectedTranscriptItem, selectedSliceItem).endSec}s
              </div>
              <div style={shellStyle.muted}>slice source: {selectedSliceItem ? 'pause_slice_worker' : selectedTranscriptItem ? 'transcript_heuristic' : 'preview_fallback'}</div>
              <div style={shellStyle.muted}>
                timeline link: {selectedTimelineMatch ? selectedTimelineMatch.clip.clip_id : 'not in timeline yet'}
              </div>
              <div style={shellStyle.muted}>graph-linked nodes: {selectedShotGraphCards.length}</div>
              <div style={shellStyle.muted}>
                graph primary:{' '}
                {selectedShotPrimaryGraphCard
                  ? `${selectedShotPrimaryGraphCard.label} · ${selectedShotPrimaryGraphCard.nodeType}`
                  : 'no linked graph node'}
              </div>
              <div style={shellStyle.muted}>
                graph render mode:{' '}
                {selectedShotPrimaryGraphCard
                  ? `${selectedShotPrimaryGraphCard.displayMode || 'display unknown'} · ${selectedShotPrimaryGraphCard.modality || 'n/a'}`
                  : 'no linked graph render hints'}
              </div>
              <div style={shellStyle.muted}>
                graph summary: {selectedShotPrimaryGraphCard?.summary || 'no graph summary'}
              </div>
              <div style={shellStyle.muted}>
                graph focus source:{' '}
                {selectedTimelineGraphDagNodeIds.length
                  ? 'timeline + storyboard crosslinks'
                  : selectedStoryboardGraphDagNodeIds.length
                    ? 'storyboard crosslinks'
                    : sceneGraphViewport?.focusNodeIds.length
                      ? 'scene graph anchor only'
                      : 'none'}
              </div>
              <div style={shellStyle.muted}>graph marker budget: {selectedShotGraphMarkerCount}</div>
              <div style={shellStyle.muted}>
                graph sync badges: {selectedShotGraphSyncBadges.length ? selectedShotGraphSyncBadges.join(', ') : 'none'}
              </div>
              <div style={shellStyle.muted}>
                graph buckets: {selectedShotGraphBuckets.length ? selectedShotGraphBuckets.join(', ') : 'none'}
              </div>
              <div style={shellStyle.muted}>
                graph inspector link: {selectedShotInspectorNodes.length ? selectedShotInspectorNodes.map((node) => node.label).join(' · ') : 'no inspector node linked'}
              </div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                {selectedShotGraphSyncBadges.length ? (
                  selectedShotGraphSyncBadges.map((badge) => (
                    <span
                      key={`selected-shot-sync-${badge}`}
                      style={{
                        fontSize: 10,
                        padding: '2px 6px',
                        borderRadius: 999,
                        border: '1px solid #22c55e88',
                        color: '#22c55e',
                        background: '#22c55e22',
                      }}
                    >
                      graph sync {badge}
                    </span>
                  ))
                ) : (
                  <span style={shellStyle.muted}>no graph sync chips</span>
                )}
                {selectedShotGraphBuckets.map((bucket) => (
                  <span
                    key={`selected-shot-bucket-${bucket}`}
                    style={{
                      fontSize: 10,
                      padding: '2px 6px',
                      borderRadius: 999,
                      border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                      color: NOLAN_PALETTE.textMuted,
                      background: NOLAN_PALETTE.bgDim,
                    }}
                  >
                    graph bucket {bucket}
                  </span>
                ))}
              </div>
              <div style={{ ...shellStyle.clip, marginTop: 8, padding: '8px 10px' }}>
                <div style={shellStyle.muted}>Primary Graph Mini Card</div>
                {selectedShotPrimaryGraphCard?.posterUrl ? (
                  <img
                    src={selectedShotPrimaryGraphCard.posterUrl}
                    alt={`${selectedShotPrimaryGraphCard.label} mini`}
                    style={{ width: '100%', height: 64, objectFit: 'cover', borderRadius: 6, marginTop: 6, marginBottom: 6 }}
                  />
                ) : (
                  <div style={shellStyle.muted}>no graph poster reuse</div>
                )}
                <div style={shellStyle.muted}>
                  {selectedShotPrimaryGraphCard
                    ? `${selectedShotPrimaryGraphCard.label} · ${selectedShotPrimaryGraphCard.nodeType}`
                    : 'no graph mini card'}
                </div>
                <div style={shellStyle.muted}>
                  {selectedShotPrimaryGraphCard?.summary || 'no mini summary'}
                </div>
              </div>
              <div style={shellStyle.muted}>
                sync hint:{' '}
                {selectedAudioSyncItem
                  ? `${Number(selectedAudioSyncItem.detected_offset_sec || 0).toFixed(3)}s via ${selectedAudioSyncItem.method}`
                  : 'no sync result yet'}
              </div>
              <div style={shellStyle.muted}>
                timecode hint:{' '}
                {selectedTimecodeSyncItem
                  ? `${selectedTimecodeSyncItem.reference_timecode} -> ${selectedTimecodeSyncItem.source_timecode}`
                  : 'no timecode sync yet'}
              </div>
              <div style={shellStyle.muted}>
                recommended sync:{' '}
                {selectedSyncSurfaceItem?.recommended_method
                  ? `${selectedSyncSurfaceItem.recommended_method} ${Number(selectedSyncSurfaceItem.recommended_offset_sec || 0).toFixed(3)}s`
                  : 'none'}
              </div>
              <div style={shellStyle.muted}>markers for shot: {selectedShotMarkers.length}</div>
              <div style={shellStyle.muted}>
                favorite: {selectedShotMarkerGroups.favorite.length} · comment: {selectedShotMarkerGroups.comment.length} · cam:{' '}
                {selectedShotMarkerGroups.cam.length}
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 8, marginBottom: 8 }}>
                <button
                  style={shellStyle.smallButton}
                  onClick={() => void handleSyncSelectedShotToTimeline()}
                  disabled={busy || !projectId || !selectedTimelineMatch}
                >
                  Sync Timeline Selection
                </button>
                <button
                  style={shellStyle.smallButton}
                  onClick={() => void handleApplySelectedSyncOffset()}
                  disabled={busy || !projectId || !selectedTimelineMatch || !selectedSyncSurfaceItem?.recommended_method}
                >
                  Apply Sync Offset
                </button>
                <button
                  style={shellStyle.smallButton}
                  onClick={() => void handleCreateTimeMarker(selectedThumbnail, 'favorite')}
                  disabled={busy || !projectId}
                >
                  Favorite Selected
                </button>
                <button
                  style={shellStyle.smallButton}
                  onClick={() => void handleCreateTimeMarker(selectedThumbnail, 'comment')}
                  disabled={busy || !projectId}
                >
                  Comment Selected
                </button>
                <button
                  style={shellStyle.smallButton}
                  onClick={() => void handleCreateTimeMarker(selectedThumbnail, 'cam')}
                  disabled={busy || !projectId}
                >
                  CAM Selected
                </button>
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <button
                  style={shellStyle.smallButton}
                  onClick={() => setShowActiveMarkersOnly((value) => !value)}
                  disabled={busy}
                >
                  {showActiveMarkersOnly ? 'Show All Markers' : 'Show Active Only'}
                </button>
              </div>
              <div style={shellStyle.card}>
                <div style={shellStyle.sectionTitle}>CAM Ready</div>
                <div style={shellStyle.muted}>cam markers: {selectedShotCamMarkers.length}</div>
                <div style={shellStyle.muted}>
                  status: {selectedShotCamMarkers.length ? 'context-linked markers detected' : 'waiting for CAM payloads'}
                </div>
                <div style={shellStyle.muted}>next: attach `cam_payload` and contextual hints for this shot</div>
                {selectedShotCamMarkers.slice(0, 3).map((marker) => (
                  <div key={`cam-ready-${marker.marker_id}`} style={shellStyle.clip}>
                    <div>
                      {marker.start_sec}s - {marker.end_sec}s
                    </div>
                    <div style={shellStyle.muted}>
                      source: {marker.cam_payload?.source || 'unknown'} · status: {marker.cam_payload?.status || 'none'}
                    </div>
                    <div style={shellStyle.muted}>{marker.cam_payload?.hint || marker.text || 'no cam hint yet'}</div>
                  </div>
                ))}
              </div>
              {(
                [
                  ['Favorite Markers', selectedShotMarkerGroups.favorite],
                  ['Comment Markers', selectedShotMarkerGroups.comment],
                  ['CAM Markers', selectedShotMarkerGroups.cam],
                  ['Other Markers', selectedShotMarkerGroups.other],
                ] as Array<[string, CutTimeMarker[]]>
              ).map(([title, markers]) =>
                markers.length ? (
                  <div key={title} style={{ marginBottom: 8 }}>
                    <div style={{ ...shellStyle.muted, marginBottom: 6 }}>{title}</div>
                    {markers.slice(0, 6).map((marker) => (
                      <div
                        key={`selected-shot-marker-${marker.marker_id}`}
                        style={{
                          ...shellStyle.clip,
                          border:
                            selectedMarkerId === marker.marker_id
                              ? `1px solid ${NOLAN_PALETTE.textAccent}`
                              : `1px solid ${NOLAN_PALETTE.borderDim}`,
                        }}
                      >
                        <div>
                          {marker.kind} · {marker.start_sec}s - {marker.end_sec}s
                        </div>
                        <div style={shellStyle.muted}>
                          {marker.status || 'active'} · score {Number(marker.score || 0).toFixed(2)}
                        </div>
                        <div style={shellStyle.muted}>
                          slice: {marker.context_slice?.mode || 'unknown'} · source: {marker.context_slice?.derived_from || 'n/a'}
                        </div>
                        {marker.text ? <div style={shellStyle.muted}>{marker.text}</div> : null}
                        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                          <button
                            style={shellStyle.smallButton}
                            onClick={() => void handleFocusMarkerInTimeline(marker)}
                            disabled={busy || !projectId || !selectedTimelineMatch}
                          >
                            Focus Marker In Timeline
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null
              )}
              {!selectedShotMarkers.length ? <div style={shellStyle.muted}>No markers for selected shot.</div> : null}
              <div style={shellStyle.code}>{selectedThumbnail.source_path}</div>
            </>
          )}
        </div>
        <div style={shellStyle.sectionTitle}>Project Overview</div>
        <div style={shellStyle.card}>
          <div style={shellStyle.label}>Project</div>
          <div>{projectState?.project?.display_name || 'No project loaded'}</div>
          <div style={shellStyle.code}>{projectState?.project?.source_path || ''}</div>
        </div>
        <div style={shellStyle.card}>
          <div style={shellStyle.sectionTitle}>Runtime Flags</div>
          <div style={shellStyle.muted}>runtime_ready: {String(Boolean(projectState?.runtime_ready))}</div>
          <div style={shellStyle.muted}>graph_ready: {String(Boolean(projectState?.graph_ready))}</div>
          <div style={shellStyle.muted}>waveform_ready: {String(Boolean(projectState?.waveform_ready))}</div>
          <div style={shellStyle.muted}>transcript_ready: {String(Boolean(projectState?.transcript_ready))}</div>
          <div style={shellStyle.muted}>thumbnail_ready: {String(Boolean(projectState?.thumbnail_ready))}</div>
          <div style={shellStyle.muted}>audio_sync_ready: {String(Boolean(projectState?.audio_sync_ready))}</div>
          <div style={shellStyle.muted}>slice_ready: {String(Boolean(projectState?.slice_ready))}</div>
          <div style={shellStyle.muted}>timecode_sync_ready: {String(Boolean(projectState?.timecode_sync_ready))}</div>
          <div style={shellStyle.muted}>sync_surface_ready: {String(Boolean(projectState?.sync_surface_ready))}</div>
          <div style={shellStyle.muted}>meta_sync_ready: {String(Boolean(projectState?.meta_sync_ready))}</div>
          <div style={shellStyle.muted}>time_markers_ready: {String(Boolean(projectState?.time_markers_ready))}</div>
        </div>
        <div style={shellStyle.card}>
          <div style={shellStyle.sectionTitle}>Sync Hints</div>
          <div style={shellStyle.muted}>sync_surface items: {syncSurfaceItems.length}</div>
          <div style={shellStyle.muted}>timecode_sync results: {timecodeSyncItems.length}</div>
          <div style={shellStyle.muted}>audio_sync results: {audioSyncItems.length}</div>
          {!audioSyncItems.length && !timecodeSyncItems.length ? (
            <div style={shellStyle.muted}>No sync offsets yet.</div>
          ) : (
            <>
              {timecodeSyncItems.slice(0, 6).map((item) => (
                <div key={item.item_id} style={shellStyle.clip}>
                  <div>{item.source_path.split('/').pop()}</div>
                  <div style={shellStyle.muted}>ref: {item.reference_path.split('/').pop()}</div>
                  <div style={shellStyle.muted}>
                    {item.reference_timecode} {'→'} {item.source_timecode} · {Number(item.detected_offset_sec || 0).toFixed(3)}s
                  </div>
                  <div style={shellStyle.muted}>{item.method}</div>
                </div>
              ))}
              {syncSurfaceItems.slice(0, 6).map((item) => (
                <div key={item.item_id} style={shellStyle.clip}>
                  <div>{item.source_path.split('/').pop()}</div>
                  <div style={shellStyle.muted}>recommended: {item.recommended_method || 'none'}</div>
                  <div style={shellStyle.muted}>
                    offset {Number(item.recommended_offset_sec || 0).toFixed(3)}s · conf {Number(item.confidence || 0).toFixed(2)}
                  </div>
                </div>
              ))}
              {audioSyncItems.slice(0, 6).map((item) => (
              <div key={item.item_id} style={shellStyle.clip}>
                <div>{item.source_path.split('/').pop()}</div>
                <div style={shellStyle.muted}>
                  ref: {item.reference_path.split('/').pop()}
                </div>
                <div style={shellStyle.muted}>
                  offset {Number(item.detected_offset_sec || 0).toFixed(3)}s · conf {Number(item.confidence || 0).toFixed(2)}
                </div>
                <div style={shellStyle.muted}>{item.method}</div>
              </div>
              ))}
            </>
          )}
        </div>
        <div style={shellStyle.card}>
          <div style={shellStyle.sectionTitle}>Cognitive Markers</div>
          <div style={shellStyle.muted}>markers: {timeMarkers.length}</div>
          <div style={shellStyle.muted}>
            favorite: {globalMarkerGroups.favorite.length} · comment: {globalMarkerGroups.comment.length} · cam:{' '}
            {globalMarkerGroups.cam.length}
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 8, marginBottom: 8 }}>
            <button
              style={shellStyle.smallButton}
              onClick={() => setShowGlobalActiveMarkersOnly((value) => !value)}
              disabled={busy}
            >
              {showGlobalActiveMarkersOnly ? 'Show All Global Markers' : 'Show Active Global Only'}
            </button>
          </div>
          {(
            [
              ['Favorite Markers', globalMarkerGroups.favorite],
              ['Comment Markers', globalMarkerGroups.comment],
              ['CAM Markers', globalMarkerGroups.cam],
              ['Other Markers', globalMarkerGroups.other],
            ] as Array<[string, CutTimeMarker[]]>
          ).map(([title, markers]) =>
            markers.length ? (
              <div key={`global-${title}`} style={{ marginBottom: 8 }}>
                <div style={{ ...shellStyle.muted, marginBottom: 6 }}>{title}</div>
                {markers.slice(0, 6).map((marker) => (
                  <div key={marker.marker_id} style={shellStyle.clip}>
                    <div>
                      {marker.kind} · {marker.media_path.split('/').pop()}
                    </div>
                    <div style={shellStyle.muted}>
                      {marker.start_sec}s - {marker.end_sec}s · {marker.status || 'active'}
                    </div>
                    <div style={shellStyle.muted}>
                      slice: {marker.context_slice?.mode || 'unknown'} · source: {marker.context_slice?.derived_from || 'n/a'}
                    </div>
                    {marker.text ? <div style={shellStyle.muted}>{marker.text}</div> : null}
                    <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                      <button
                        style={shellStyle.smallButton}
                        onClick={() => void handleArchiveTimeMarker(marker.marker_id)}
                        disabled={busy || !projectId || marker.status === 'archived'}
                      >
                        Archive Marker
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : null
          )}
          {!globalVisibleMarkers.length ? <div style={shellStyle.muted}>No visible cognitive markers.</div> : null}
        </div>
        <div style={shellStyle.card}>
          <div style={shellStyle.sectionTitle}>Worker Queue</div>
          <div style={shellStyle.muted}>active_jobs: {activeJobs.length}</div>
          <div style={shellStyle.muted}>recent_jobs: {recentJobs.length}</div>
          {activeJobs.slice(0, 4).map((job) => (
            <div key={`active-${job.job_id}`} style={shellStyle.clip}>
              <div>{job.job_type || 'job'}</div>
              <div style={shellStyle.muted}>
                {job.state || 'unknown'} · {Math.round((Number(job.progress) || 0) * 100)}%
              </div>
              <button style={shellStyle.smallButton} onClick={() => void handleCancelJob(job.job_id)} disabled={busy}>
                Cancel Job
              </button>
            </div>
          ))}
          {recentJobs.slice(0, 4).map((job) => (
            <div key={job.job_id} style={shellStyle.clip}>
              <div>{job.job_type || 'job'}</div>
              <div style={shellStyle.muted}>
                {job.state || 'unknown'} · {Math.round((Number(job.progress) || 0) * 100)}%
              </div>
            </div>
          ))}
          {!recentJobs.length ? <div style={shellStyle.muted}>No worker jobs yet.</div> : null}
        </div>
        <div style={shellStyle.card}>
          <div style={shellStyle.sectionTitle}>Inspector / Questions</div>
          <div style={shellStyle.muted}>Bootstrap stats</div>
          <pre style={{ ...shellStyle.code, whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(fallbackQuestions, null, 2)}
          </pre>
        </div>
      </aside>
    </div>
  );

  return (
    <CutEditorLayout
      sceneGraphSurface={nleSceneGraphSurface}
      debugView={debugShell}
      statusText={status}
    />
  );
}
