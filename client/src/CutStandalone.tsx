import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';

import { API_BASE } from './config/api.config';
import { ReactFlowProvider } from '@xyflow/react';
import { DAGView } from './components/mcc/DAGView';
import { NOLAN_PALETTE } from './utils/dagLayout';
import CutEditorLayoutV2 from './components/cut/CutEditorLayoutV2';
import {
  buildCutSceneGraphViewportModel,
  type CutSceneGraphView,
} from './components/cut/sceneGraphViewportAdapter';
import { useCutEditorStore } from './store/useCutEditorStore';
import { useTimelineInstanceStore } from './store/useTimelineInstanceStore';
import { usePanelSyncBridge } from './hooks/usePanelSyncBridge';

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

type MusicCueSummary = {
  track_label?: string;
  cue_point_count?: number;
  phrase_count?: number;
  tempo_bpm?: number | null;
};

type PlayerLabImportPreview = {
  markers: Array<Record<string, unknown>>;
  provisionalEvents: Array<Record<string, unknown>>;
  kindCounts: Record<string, number>;
  fileName: string;
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

function normalizePlayerLabPreview(raw: unknown, fileName: string): PlayerLabImportPreview {
  const payload = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>;
  const markers = Array.isArray(payload.markers) ? (payload.markers as Array<Record<string, unknown>>) : [];
  const provisionalEvents = Array.isArray(payload.provisional_events)
    ? (payload.provisional_events as Array<Record<string, unknown>>)
    : Array.isArray(payload.provisionalEvents)
      ? (payload.provisionalEvents as Array<Record<string, unknown>>)
      : [];
  const kindCounts = markers.reduce<Record<string, number>>((acc, item) => {
    const kind = String(item.kind || 'unknown');
    acc[kind] = (acc[kind] || 0) + 1;
    return acc;
  }, {});
  return {
    markers,
    provisionalEvents,
    kindCounts,
    fileName,
  };
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
  // MARKER_W1.1: Bridge PanelSyncStore → EditorStore (script/DAG clicks → source monitor + playhead)
  usePanelSyncBridge();

  const query = useMemo(parseQuery, []);
  const playerLabInputRef = useRef<HTMLInputElement | null>(null);
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
  const [playerLabPreview, setPlayerLabPreview] = useState<PlayerLabImportPreview | null>(null);

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
        if (node.primaryNodeId && structuralNodeIds.has(node.primaryNodeId)) nodeIdSet.add(node.id);
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
  const scriptText = useMemo(() => {
    return transcriptItems
      .flatMap((item) => item.transcript_normalized_json?.segments || [])
      .map((seg) => seg.text || '')
      .filter(Boolean)
      .join(' ');
  }, [transcriptItems]);
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

  async function handleLoadPlayerLabFile(file: File) {
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as unknown;
      const preview = normalizePlayerLabPreview(parsed, file.name);
      setPlayerLabPreview(preview);
      setStatus(
        `Player Lab preview loaded: ${preview.markers.length} markers, ${preview.provisionalEvents.length} provisional events.`
      );
    } catch (error) {
      setPlayerLabPreview(null);
      setStatus(error instanceof Error ? error.message : 'Failed to parse Player Lab JSON');
    }
  }

  async function handleImportPlayerLab() {
    if (!sandboxRoot || !projectId || !playerLabPreview) return;
    setBusy(true);
    try {
      setStatus(`Importing Player Lab markers from ${playerLabPreview.fileName}...`);
      const payload = await jsonFetch<{
        success: boolean;
        imported_count?: number;
        skipped_duplicates?: number;
        kind_counts?: Record<string, number>;
        error?: { message?: string };
      }>('/cut/markers/import-player-lab', {
        method: 'POST',
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: 'main',
          author: 'cut_shell_player_lab',
          markers: playerLabPreview.markers,
          provisional_events: playerLabPreview.provisionalEvents,
        }),
      });
      if (!payload.success) throw new Error(payload.error?.message || 'Player Lab marker import failed');
      await refreshProjectState(projectId);
      setStatus(
        `Imported Player Lab markers: ${Number(payload.imported_count || 0)} new, ${Number(payload.skipped_duplicates || 0)} duplicates skipped.`
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Player Lab marker import failed');
    } finally {
      setBusy(false);
    }
  }

  return <CutEditorLayoutV2 scriptText={scriptText} />;
}
