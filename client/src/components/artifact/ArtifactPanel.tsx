/**
 * ArtifactPanel - File and content viewer with editing support.
 * Displays files, raw content, and markdown with lazy-loaded viewers.
 *
 * @status active
 * @phase 104.9
 * @depends react, lucide-react, ./utils/fileTypes, ./viewers/*, ./Toolbar
 * @used_by ArtifactWindow, ChatPanel
 *
 * MARKER_104_VISUAL - L2 approval editing with subtle gray styling
 */

import { lazy, Suspense, useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { getViewerType } from './utils/fileTypes';
import { MarkdownViewer } from './viewers/MarkdownViewer';
import { Toolbar } from './Toolbar';
import { Loader2 } from 'lucide-react';
import { closeArtifactMediaWindow, isTauri, openArtifactMediaWindow, openLiveWebWindow, saveTextFileNative } from '../../config/tauri';
import { useStore } from '../../store/useStore';
import { buildViewportContext } from '../../utils/viewport';
import { readFileViaApi } from '../../utils/fileReadClient';
import {
  readDetachedArtifactChatState,
  normalizeDetachedArtifactPath,
  DETACHED_ARTIFACT_CHAT_STATE_KEY,
  writeDetachedArtifactPinRequest,
  type DetachedArtifactChatStateV1,
} from '../../utils/detachedArtifactBridge';
import './ArtifactPanel.css';

// Lazy load heavy viewers
const CodeViewer = lazy(() => import('./viewers/CodeViewer').then(m => ({ default: m.CodeViewer })));
const ImageViewer = lazy(() => import('./viewers/ImageViewer').then(m => ({ default: m.ImageViewer })));
const VideoArtifactPlayer = lazy(() => import('./viewers/VideoArtifactPlayer').then(m => ({ default: m.VideoArtifactPlayer })));
const MEDIA_TIMEUPDATE_THROTTLE_MS = 120;

function ViewerLoading() {
  return (
    <div style={{
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#0a0a0a'
    }}>
      <Loader2 size={32} color="#666" style={{ animation: 'spin 1s linear infinite' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

interface FileInfo {
  path: string;
  name: string;
  extension?: string;
}

interface FileData {
  path: string;
  content: string;
  mimeType: string;
  encoding?: 'utf-8' | 'base64' | 'binary' | string;
  hasChanges: boolean;
  fileSize?: number;
  createdAt?: number;
  modifiedAt?: number;
}

interface MediaPreviewData {
  success: boolean;
  path: string;
  mime_type: string;
  modality: 'audio' | 'video';
  size_bytes: number;
  duration_sec: number;
  waveform_bins: number[];
  waveform_sample_rate: number;
  timeline_segments: Array<{
    start_sec: number;
    end_sec: number;
    duration_sec: number;
    text: string;
    confidence: number;
    chunk_id: string;
    timeline_lane?: 'video_main' | 'audio_sync' | 'take_alt_y' | 'take_alt_z';
    lane_index?: number;
    take_id?: string;
    sync_group_id?: string;
  }>;
  preview?: {
    aspect_ratio?: string | null;
    recommended_zoom?: number;
  };
  playback?: {
    source_url?: string;
    strategy?: string;
    requires_proxy?: boolean;
    sources_scale?: Partial<Record<'full' | 'half' | 'quarter' | 'eighth' | 'sixteenth', string>>;
  };
  preview_assets?: {
    poster_url?: string;
    animated_preview_url_300ms?: string;
  };
  degraded_mode?: boolean;
  degraded_reason?: string;
}

interface SemanticLinkItem {
  relation_type: 'hero' | 'action' | 'location' | 'theme' | string;
  score: number;
  parent_file_path: string;
  start_sec: number;
  end_sec: number;
  text: string;
  timeline_lane?: string;
  take_id?: string;
  sync_group_id?: string;
}

interface RhythmAssistData {
  success: boolean;
  modality: 'audio' | 'video';
  duration_sec: number;
  energy_track: number[];
  rhythm_features: {
    cut_density: {
      per_sec: number;
      per_min: number;
    };
    motion_volatility: number;
    phase_markers: Array<{
      time_sec: number;
      kind: string;
      strength: number;
    }>;
  };
  music_binding: {
    target_bpm: number;
    rhythm_profile: string;
  };
  recommended_shot_sec: number;
  pulse_bridge: {
    available: boolean;
    mode: string;
    degraded_reason?: string;
  };
  recommendations: string[];
  degraded_mode?: boolean;
  degraded_reason?: string;
}

// Phase 48.5.1: Raw content for chat responses
interface RawContent {
  content: string;
  title: string;
  type?: 'text' | 'markdown' | 'code' | 'web';
  sourceUrl?: string;
}

// MARKER_104_VISUAL - Approval levels for artifact editing
type ApprovalLevel = 'L1' | 'L2' | 'L3';

interface Props {
  file?: FileInfo | null;
  rawContent?: RawContent | null;  // Phase 48.5.1: Direct content display
  onClose?: () => void;
  isChatOpen?: boolean;
  // Phase 60.4: Allow editing raw content
  onContentChange?: (content: string) => void;
  // Phase 104.9: Approval level for staged artifacts
  approvalLevel?: ApprovalLevel;
  // Phase 104.9: Artifact ID for approval events
  artifactId?: string;
  // Phase 153: Optional timestamp seek target for media artifacts
  initialSeekSec?: number;
  // Phase 159 R2: Embedded panel vs detached media window mode
  windowMode?: 'embedded' | 'detached';
  // Phase 159 C2: explicit detached window label authority (artifact-main/artifact-media).
  detachedWindowLabel?: string;
  // Phase 159 C3: detached route hint from parent window (file already in VETKA tree or not).
  detachedInitialInVetka?: boolean;
}

export function ArtifactPanel({
  file,
  rawContent,
  onClose,
  isChatOpen = false,
  onContentChange,
  approvalLevel,
  artifactId,
  initialSeekSec,
  windowMode = 'embedded',
  detachedWindowLabel = 'artifact-media',
  detachedInitialInVetka,
}: Props) {
  const setActiveWebContext = useStore((state) => state.setActiveWebContext);
  const nodes = useStore((state) => state.nodes);
  const pinnedFileIds = useStore((state) => state.pinnedFileIds);
  const togglePinFile = useStore((state) => state.togglePinFile);
  const cameraRef = useStore((state) => state.cameraRef);
  const selectedId = useStore((state) => state.selectedId);
  const [fileData, setFileData] = useState<FileData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [webMode, setWebMode] = useState<'live' | 'md'>('live');
  const [openingNativeWeb, setOpeningNativeWeb] = useState(false);
  const [webSaving, setWebSaving] = useState(false);
  const [webMarkdown, setWebMarkdown] = useState<string>('');
  const [webSaveNote, setWebSaveNote] = useState<string>('');
  const [activeSeekSec, setActiveSeekSec] = useState<number | undefined>(initialSeekSec);
  // MARKER_158.P5_1_TIMELINE_ZOOM: Montage-ready zoom for waveform/segment strips.
  const [timelineZoom, setTimelineZoom] = useState<number>(1);
  const [mediaPreview, setMediaPreview] = useState<MediaPreviewData | null>(null);
  const [semanticLinks, setSemanticLinks] = useState<{
    loading: boolean;
    error: string;
    forChunkId: string;
    items: SemanticLinkItem[];
  }>({ loading: false, error: '', forChunkId: '', items: [] });
  const [rhythmAssist, setRhythmAssist] = useState<{
    loading: boolean;
    error: string;
    data: RhythmAssistData | null;
  }>({ loading: false, error: '', data: null });
  const [mediaInfoOpen, setMediaInfoOpen] = useState<boolean>(false);
  const [isMediaFullscreen, setIsMediaFullscreen] = useState<boolean>(false);
  const [isIndexingToVetka, setIsIndexingToVetka] = useState(false);
  const [locallyIndexedPath, setLocallyIndexedPath] = useState<string | null>(null);
  const [isFavorite, setIsFavorite] = useState(false);
  // Phase 48.5.1: Handle raw content mode
  const isRawContentMode = !!rawContent;
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const lastTimeupdateRef = useRef<number>(0);

  // Phase 60.4: Editable raw content state
  const [editableContent, setEditableContent] = useState<string>('');
  const [rawHasChanges, setRawHasChanges] = useState(false);

  // MARKER_104_VISUAL - L2 approval state
  const [currentApprovalLevel, setCurrentApprovalLevel] = useState<ApprovalLevel | undefined>(approvalLevel);
  const [detachedChatState, setDetachedChatState] = useState<DetachedArtifactChatStateV1 | null>(() => (
    windowMode === 'detached' ? readDetachedArtifactChatState() : null
  ));

  const normalizePath = useCallback((p: string) => {
    const raw = String(p || '').trim();
    if (!raw) return '';
    const withoutScheme = raw.replace(/^file:\/\//, '');
    let decoded = withoutScheme;
    try {
      decoded = decodeURIComponent(withoutScheme);
    } catch {
      // keep as-is
    }
    return decoded.replace(/\\/g, '/').replace(/\/+$/, '');
  }, []);

  const detachedCurrentPath = useMemo(() => normalizePath(fileData?.path || file?.path || ''), [fileData?.path, file?.path, normalizePath]);
  const detachedBasename = useMemo(() => {
    const p = detachedCurrentPath || '';
    const parts = p.split('/');
    return parts[parts.length - 1] || '';
  }, [detachedCurrentPath]);
  const isFileMode = !isRawContentMode && Boolean(detachedCurrentPath);

  useEffect(() => {
    if (!detachedCurrentPath) return;
    if (locallyIndexedPath && locallyIndexedPath !== detachedCurrentPath) {
      setLocallyIndexedPath(null);
    }
  }, [detachedCurrentPath, locallyIndexedPath]);

  const isInVetka = useMemo(() => {
    if (locallyIndexedPath && locallyIndexedPath === detachedCurrentPath) return true;
    if (windowMode === 'detached' && typeof detachedInitialInVetka === 'boolean') {
      return detachedInitialInVetka;
    }
    if (!detachedCurrentPath) return false;
    return Object.values(nodes).some((node: any) => {
      const nodePath = normalizePath(String(node?.path || ''));
      return nodePath === detachedCurrentPath || nodePath.endsWith(`/${detachedCurrentPath}`) || detachedCurrentPath.endsWith(`/${nodePath}`);
    });
  }, [windowMode, detachedInitialInVetka, nodes, detachedCurrentPath, normalizePath, locallyIndexedPath]);

  useEffect(() => {
    if (windowMode !== 'detached') return;
    if (!detachedCurrentPath) {
      setIsFavorite(false);
      return;
    }

    const loadFavoriteState = async () => {
      try {
        if (artifactId || (detachedCurrentPath.includes('/data/artifacts/') || detachedCurrentPath.includes('/src/vetka_out/'))) {
          const resp = await fetch('/api/artifacts');
          if (!resp.ok) return;
          const data = await resp.json();
          const list = data.artifacts || [];
          const match = list.find((a: any) => a.id === artifactId || a.file_path === detachedCurrentPath || a.name === detachedBasename);
          setIsFavorite(Boolean(match?.is_favorite));
          return;
        }
        const resp = await fetch('/api/tree/favorites');
        if (!resp.ok) return;
        const data = await resp.json();
        const map = data.favorites || {};
        setIsFavorite(Boolean(map[detachedCurrentPath]));
      } catch {
        // no-op
      }
    };
    void loadFavoriteState();
  }, [windowMode, artifactId, detachedCurrentPath, detachedBasename]);

  const handleAddToVetkaDetached = useCallback(async () => {
    if (windowMode !== 'detached') return;
    if (!detachedCurrentPath || isIndexingToVetka || isInVetka) return;
    setIsIndexingToVetka(true);
    try {
      const response = await fetch('/api/watcher/index-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: detachedCurrentPath }),
      });
      const data = await response.json();
      if (!response.ok || !data?.success) {
        throw new Error(data?.detail || data?.error || `HTTP ${response.status}`);
      }
      setLocallyIndexedPath(detachedCurrentPath);
      window.dispatchEvent(new CustomEvent('vetka-tree-refresh-needed'));
    } catch (err) {
      console.error('[ArtifactPanel] Add to VETKA failed:', err);
    } finally {
      setIsIndexingToVetka(false);
    }
  }, [windowMode, detachedCurrentPath, isIndexingToVetka, isInVetka]);

  const handleToggleFavoriteDetached = useCallback(async () => {
    if (windowMode !== 'detached') return;
    const next = !isFavorite;
    try {
      if (artifactId || (detachedCurrentPath.includes('/data/artifacts/') || detachedCurrentPath.includes('/src/vetka_out/'))) {
        const targetArtifactId = artifactId || detachedBasename || file?.name || 'artifact';
        const response = await fetch(`/api/artifacts/${encodeURIComponent(targetArtifactId)}/favorite`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_favorite: next }),
        });
        if (!response.ok) return;
      } else if (detachedCurrentPath) {
        const response = await fetch('/api/tree/favorite', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: detachedCurrentPath, is_favorite: next }),
        });
        if (!response.ok) return;
      } else {
        return;
      }
      setIsFavorite(next);
      window.dispatchEvent(new CustomEvent('vetka-tree-refresh-needed'));
    } catch (err) {
      console.error('[ArtifactPanel] Favorite toggle failed:', err);
    }
  }, [windowMode, isFavorite, artifactId, detachedCurrentPath, detachedBasename, file?.name]);

  // MARKER_145.VIEWPORT_SAVE_ANCHOR: Recommend nearest viewport node path as default save target.
  const getRecommendedSaveNodePath = useCallback((): string => {
    const selectedPath = selectedId ? nodes[selectedId]?.path : '';
    if (!cameraRef) return selectedPath || '';

    try {
      const viewport = buildViewportContext(nodes, pinnedFileIds, cameraRef);
      const ranked = [...viewport.pinned_nodes, ...viewport.viewport_nodes]
        .filter((n) => n.type === 'file' || n.type === 'folder')
        .sort((a, b) => {
          if (a.is_center !== b.is_center) return a.is_center ? -1 : 1;
          return a.distance_to_camera - b.distance_to_camera;
        });
      return ranked[0]?.path || selectedPath || '';
    } catch {
      return selectedPath || '';
    }
  }, [cameraRef, nodes, pinnedFileIds, selectedId]);

  // MARKER_104_VISUAL - Sync approvalLevel from props
  useEffect(() => {
    setCurrentApprovalLevel(approvalLevel);
  }, [approvalLevel]);

  useEffect(() => {
    setActiveSeekSec(initialSeekSec);
  }, [initialSeekSec]);

  useEffect(() => {
    setIsMediaFullscreen(false);
  }, [fileData?.path, windowMode]);

  useEffect(() => {
    const loadMediaPreview = async () => {
      if (!fileData?.path || !file) {
        setMediaPreview(null);
        return;
      }
      const fileType = getViewerType(file.name);
      const mimeType = fileData.mimeType || '';
      const isMedia = fileType === 'audio' || fileType === 'video' || mimeType.startsWith('audio/') || mimeType.startsWith('video/');
      if (!isMedia) {
        setMediaPreview(null);
        return;
      }
      try {
        const resp = await fetch('/api/artifacts/media/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            path: fileData.path,
            waveform_bins: 120,
            preview_segments_limit: 64,
          }),
        });
        if (!resp.ok) {
          setMediaPreview(null);
          return;
        }
        const data = await resp.json();
        setMediaPreview(data?.success ? data as MediaPreviewData : null);
      } catch {
        setMediaPreview(null);
      }
    };
    loadMediaPreview();
  }, [fileData?.path, file?.name, fileData?.mimeType]);

  useEffect(() => {
    const loadRhythmAssist = async () => {
      if (!fileData?.path || !file) {
        setRhythmAssist({ loading: false, error: '', data: null });
        return;
      }
      const fileType = getViewerType(file.name);
      const mimeType = fileData.mimeType || '';
      const isMedia = fileType === 'audio' || fileType === 'video' || mimeType.startsWith('audio/') || mimeType.startsWith('video/');
      if (!isMedia) {
        setRhythmAssist({ loading: false, error: '', data: null });
        return;
      }
      setRhythmAssist({ loading: true, error: '', data: null });
      try {
        const resp = await fetch('/api/artifacts/media/rhythm-assist', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            path: fileData.path,
            bins: 120,
            segments_limit: 256,
          }),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const payload = await resp.json();
        setRhythmAssist({
          loading: false,
          error: '',
          data: payload?.success ? (payload as RhythmAssistData) : null,
        });
      } catch {
        setRhythmAssist({ loading: false, error: 'rhythm_assist_unavailable', data: null });
      }
    };
    loadRhythmAssist();
  }, [fileData?.path, file?.name, fileData?.mimeType]);

  useEffect(() => {
    const media = videoRef.current || audioRef.current;
    if (!media) return;
    const syncSeek = () => setActiveSeekSec(media.currentTime);
    media.addEventListener('timeupdate', syncSeek);
    return () => media.removeEventListener('timeupdate', syncSeek);
  }, [fileData?.path, fileData?.mimeType]);

  const timelineWidthPct = useMemo(() => Math.max(100, Math.round(timelineZoom * 100)), [timelineZoom]);
  const rhythmOverlay = useMemo(() => {
    const duration = mediaPreview?.duration_sec || 0;
    const rhythmDuration = rhythmAssist.data?.duration_sec || 0;
    const track = Array.isArray(rhythmAssist.data?.energy_track) ? rhythmAssist.data?.energy_track : [];
    const phases = Array.isArray(rhythmAssist.data?.rhythm_features?.phase_markers)
      ? rhythmAssist.data.rhythm_features.phase_markers
      : [];
    if (!duration || !track.length) {
      return { bars: [] as Array<{ leftPct: number; widthPct: number; amp: number }>, markers: [] as Array<{ leftPct: number; kind: string }> };
    }
    const baseDuration = rhythmDuration > 0 ? rhythmDuration : duration;
    const barWidth = 100 / Math.max(1, track.length);
    const bars = track.map((amp, idx) => {
      const leftPct = (idx / Math.max(1, track.length)) * 100;
      const widthPct = Math.max(0.22, barWidth);
      return {
        leftPct: Math.max(0, Math.min(100, leftPct)),
        widthPct: Math.max(0, Math.min(100 - leftPct, widthPct)),
        amp: Math.max(0, Math.min(1, Number(amp) || 0)),
      };
    });
    const markers = phases.slice(0, 128).map((m) => ({
      leftPct: Math.max(0, Math.min(100, ((Number(m.time_sec) || 0) / Math.max(0.001, baseDuration)) * 100)),
      kind: String(m.kind || 'phase'),
    }));
    return { bars, markers };
  }, [mediaPreview?.duration_sec, rhythmAssist.data]);

  const handleSegmentClick = useCallback(async (seg: MediaPreviewData['timeline_segments'][number]) => {
    setActiveSeekSec(seg.start_sec);
    const queryText = String(seg.text || '').trim();
    if (!fileData?.path || !queryText) {
      setSemanticLinks({ loading: false, error: '', forChunkId: String(seg.chunk_id || ''), items: [] });
      return;
    }
    setSemanticLinks({ loading: true, error: '', forChunkId: String(seg.chunk_id || ''), items: [] });
    try {
      const resp = await fetch('/api/artifacts/media/semantic-links', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: fileData.path,
          query_text: queryText,
          start_sec: seg.start_sec,
          end_sec: seg.end_sec,
          limit: 12,
          include_same_file: true,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const payload = await resp.json();
      const items = Array.isArray(payload?.links) ? payload.links as SemanticLinkItem[] : [];
      setSemanticLinks({ loading: false, error: '', forChunkId: String(seg.chunk_id || ''), items });
    } catch {
      setSemanticLinks({ loading: false, error: 'semantic_links_unavailable', forChunkId: String(seg.chunk_id || ''), items: [] });
    }
  }, [fileData?.path]);

  // MARKER_104_VISUAL - Listen for artifact-approval CustomEvent from useSocket.ts
  useEffect(() => {
    const handleApprovalEvent = (event: CustomEvent<{
      artifactId?: string;
      approvalLevel?: ApprovalLevel;
      action?: 'approve' | 'reject' | 'edit';
    }>) => {
      const { artifactId: eventArtifactId, approvalLevel: eventLevel, action } = event.detail;

      // Only respond if this event is for our artifact
      if (artifactId && eventArtifactId && eventArtifactId !== artifactId) {
        return;
      }

      if (eventLevel) {
        setCurrentApprovalLevel(eventLevel);
      }

      // L2 level enables editing mode automatically
      if (eventLevel === 'L2' || action === 'edit') {
        setIsEditing(true);
      }
    };

    window.addEventListener('artifact-approval', handleApprovalEvent as EventListener);
    return () => {
      window.removeEventListener('artifact-approval', handleApprovalEvent as EventListener);
    };
  }, [artifactId]);

  // Phase 60.4: Undo history (max 10 states)
  const MAX_UNDO_HISTORY = 10;
  const undoHistoryRef = useRef<string[]>([]);
  const [canUndo, setCanUndo] = useState(false);

  // Phase 60.4: Sync editable content when rawContent changes
  useEffect(() => {
    if (rawContent?.content) {
      setEditableContent(rawContent.content);
      setRawHasChanges(false);
      // Reset undo history
      undoHistoryRef.current = [rawContent.content];
      setCanUndo(false);
    }
  }, [rawContent?.content]);

  // MARKER_139.S1_4_WEB_LIVE_DEFAULT: Live mode must be default for web artifacts
  useEffect(() => {
    if (rawContent?.type === 'web') {
      setWebMode('live');
      setWebMarkdown('');
      setWebSaveNote('');
      if (rawContent.sourceUrl) {
        setActiveWebContext({
          url: rawContent.sourceUrl,
          title: rawContent.title || 'Web page',
          summary: rawContent.content || '',
          source: 'unified_search',
          web_open: true,
          captured_at: new Date().toISOString(),
        });
      }
    } else {
      const current = useStore.getState().activeWebContext;
      if (current && current.source !== 'native_window' && current.web_open) {
        setActiveWebContext({ ...current, web_open: false });
      }
    }
  }, [rawContent?.type, rawContent?.sourceUrl]);

  // Phase 60.4: Push to undo history
  const pushToUndoHistory = useCallback((content: string) => {
    const history = undoHistoryRef.current;
    // Don't push if same as last
    if (history[history.length - 1] === content) return;

    history.push(content);
    // Keep max 10 states
    if (history.length > MAX_UNDO_HISTORY) {
      history.shift();
    }
    setCanUndo(history.length > 1);
  }, []);

  // Phase 60.4: Undo action
  const handleUndo = useCallback(() => {
    const history = undoHistoryRef.current;
    if (history.length <= 1) return;

    // Remove current state
    history.pop();
    // Get previous state
    const previousState = history[history.length - 1];
    if (previousState !== undefined) {
      setEditableContent(previousState);
      setRawHasChanges(previousState !== rawContent?.content);
    }
    setCanUndo(history.length > 1);
  }, [rawContent?.content]);

  // Load file content
  const loadFile = useCallback(async (path: string) => {
    if (!path) return;

    // MARKER_139.S1_3_WEB_FALLBACK: Never treat http(s) URL as local file path
    if (/^https?:\/\//i.test(path)) {
      setFileData({
        path,
        content: `# External Web URL\n\nSource: ${path}\n\nUse web preview mode to render full page.`,
        mimeType: 'text/markdown',
        hasChanges: false,
      });
      return;
    }

    setIsLoading(true);
    try {
      const data = await readFileViaApi(path);

      setFileData({
        path,
        content: data.content,
        mimeType: data.mimeType || 'text/plain',
        encoding: data.encoding || 'utf-8',
        hasChanges: false,
        fileSize: data.size,
        createdAt: typeof data.createdAt === 'number' ? data.createdAt : undefined,
        modifiedAt: typeof data.modifiedAt === 'number' ? data.modifiedAt : undefined,
      });
    } catch (err) {
      console.error('[ArtifactPanel] Load error:', err);
      // Fallback for demo mode
      setFileData({
        path,
        content: `// Could not load file: ${path}\n// Backend not available`,
        mimeType: 'text/plain',
        encoding: 'utf-8',
        hasChanges: false,
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load file when selection changes
  useEffect(() => {
    if (file?.path) {
      loadFile(file.path);
    } else {
      setFileData(null);
    }
  }, [file?.path, loadFile]);

  useEffect(() => {
    if (activeSeekSec === undefined) return;
    const seekTo = Math.max(0, activeSeekSec);
    const media = videoRef.current || audioRef.current;
    if (!media) return;

    const applySeek = () => {
      try {
        media.currentTime = seekTo;
      } catch {
        // Ignore non-seekable state.
      }
    };

    if (media.readyState >= 1) {
      applySeek();
    } else {
      media.addEventListener('loadedmetadata', applySeek, { once: true });
      return () => media.removeEventListener('loadedmetadata', applySeek);
    }
  }, [activeSeekSec, file?.path, fileData?.mimeType]);

  // Update content
  const updateContent = useCallback((content: string) => {
    setFileData(prev => prev ? { ...prev, content, hasChanges: true } : null);
  }, []);

  // Save file
  const saveFile = useCallback(async () => {
    if (!fileData) return;
    setIsSaving(true);
    try {
      const response = await fetch('/api/files/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: fileData.path, content: fileData.content }),
      });
      if (!response.ok) throw new Error('Save failed');
      setFileData(prev => prev ? { ...prev, hasChanges: false } : null);
    } catch (err) {
      console.error('[ArtifactPanel] Save error:', err);
    } finally {
      setIsSaving(false);
    }
  }, [fileData]);

  // MARKER_136.W3C: Global keyboard shortcut listeners (Ctrl+S, Ctrl+Z)
  useEffect(() => {
    const handleGlobalSave = () => {
      // If editing raw content, save via onContentChange callback
      if (isEditing && rawHasChanges && onContentChange) {
        onContentChange(editableContent);
        setRawHasChanges(false);
      }
      // If editing file, save via saveFile
      else if (fileData?.hasChanges) {
        saveFile();
      }
    };

    const handleGlobalUndo = () => {
      if (isEditing) {
        handleUndo();
      }
    };

    window.addEventListener('vetka-save-file', handleGlobalSave);
    window.addEventListener('vetka-undo', handleGlobalUndo);

    return () => {
      window.removeEventListener('vetka-save-file', handleGlobalSave);
      window.removeEventListener('vetka-undo', handleGlobalUndo);
    };
  }, [isEditing, rawHasChanges, editableContent, onContentChange, fileData, saveFile, handleUndo]);

  // Actions
  const handleCopy = () => navigator.clipboard.writeText(fileData?.content || '');
  const downloadViaBrowser = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    window.setTimeout(() => {
      if (a.parentNode) a.parentNode.removeChild(a);
      URL.revokeObjectURL(url);
    }, 0);
  };

  const handleDownload = async () => {
    if (!fileData) return;
    const filename = fileData.path.split('/').pop() || 'file';
    if (isTauri()) {
      await saveTextFileNative(filename, fileData.content, 'Save artifact');
      return;
    }
    downloadViaBrowser(fileData.content, filename);
  };

  // Phase 48.5.1: Render raw content
  // Phase 60.4: Added editing support
  // MARKER_104_VISUAL - L2 approval editing with subtle gray styling
  const renderRawContent = () => {
    if (!rawContent) return null;

    const contentToShow = isEditing ? editableContent : rawContent.content;

    // MARKER_104_VISUAL - L2 subtle gray styling for approval editing
    const isL2Editing = currentApprovalLevel === 'L2' && isEditing;

    // Phase 60.4: Editing mode - textarea for all types
    // MARKER_104_VISUAL - Enhanced with L2 subtle styling
    if (isEditing) {
      return (
        <div style={{
          height: '100%',
          overflow: 'auto',
          padding: 12,
          // MARKER_104_VISUAL - Subtle background for L2 editing
          background: isL2Editing ? '#1a1a1a' : '#0a0a0a',
          opacity: isL2Editing ? 0.9 : 1,
        }}>
          <textarea
            value={editableContent}
            onChange={(e) => {
              setEditableContent(e.target.value);
              setRawHasChanges(true);
              // MARKER_104_VISUAL - Notify parent of L2 content change
              if (currentApprovalLevel === 'L2' && onContentChange) {
                onContentChange(e.target.value);
              }
            }}
            onBlur={() => {
              // Phase 60.4: Save state to undo history on blur (not every keystroke)
              pushToUndoHistory(editableContent);
            }}
            onKeyDown={(e) => {
              // Phase 60.4: Ctrl+Z / Cmd+Z for undo
              if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
                e.preventDefault();
                handleUndo();
              }
            }}
            style={{
              width: '100%',
              height: '100%',
              minHeight: 300,
              padding: 16,
              // MARKER_104_VISUAL - L2 subtle gray styling (NO bright colors)
              background: isL2Editing ? '#1a1a1a' : '#111',
              border: '1px solid #333',
              borderRadius: isL2Editing ? 4 : 8,
              color: '#e0e0e0',
              fontSize: 14,
              lineHeight: 1.6,
              fontFamily: 'monospace',
              resize: 'none',
              outline: 'none',
              // MARKER_104_VISUAL - Subtle opacity for L2
              opacity: isL2Editing ? 0.9 : 1,
            }}
            placeholder={isL2Editing ? "L2 Edit: Modify staged artifact..." : "Edit content here..."}
          />
          {/* MARKER_104_VISUAL - L2 approval indicator */}
          {isL2Editing && (
            <div style={{
              position: 'absolute',
              top: 4,
              right: 8,
              fontSize: 10,
              color: '#666',
              fontFamily: 'monospace',
            }}>
              L2 EDIT
            </div>
          )}
        </div>
      );
    }

    // View mode
    switch (rawContent.type) {
      case 'web': {
        const markdownFallback = [
          `# ${rawContent.title || 'Web result'}`,
          '',
          rawContent.sourceUrl ? `Source: ${rawContent.sourceUrl}` : '',
          '',
          rawContent.content || '',
        ].join('\n');
        const markdownToShow = webMarkdown || markdownFallback;

        return (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#0a0a0a' }}>
            <div style={{
              padding: '8px 12px',
              borderBottom: '1px solid #222',
              fontSize: 11,
              color: '#999',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <span style={{ color: '#666', textTransform: 'uppercase', letterSpacing: 1 }}>web preview</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <button
                  onClick={() => setWebMode('live')}
                  style={{
                    border: '1px solid #333',
                    background: webMode === 'live' ? '#1f2937' : '#111',
                    color: webMode === 'live' ? '#d1e3ff' : '#999',
                    fontSize: 10,
                    padding: '2px 6px',
                    borderRadius: 4,
                    cursor: 'pointer',
                  }}
                  title="Live web page mode"
                >
                  LIVE
                </button>
                <button
                  onClick={() => setWebMode('md')}
                  style={{
                    border: '1px solid #333',
                    background: webMode === 'md' ? '#1f2937' : '#111',
                    color: webMode === 'md' ? '#d1e3ff' : '#999',
                    fontSize: 10,
                    padding: '2px 6px',
                    borderRadius: 4,
                    cursor: 'pointer',
                  }}
                  title="Markdown fallback mode"
                >
                  MD
                </button>
              </div>
              {rawContent.sourceUrl && (
                <a
                  href={rawContent.sourceUrl}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: '#c7c7c7', textDecoration: 'none', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                  title={rawContent.sourceUrl}
                >
                  {rawContent.sourceUrl}
                </a>
              )}
              {isTauri() && rawContent.sourceUrl && (
                <button
                  onClick={async () => {
                    if (!rawContent.sourceUrl || openingNativeWeb) return;
                    setOpeningNativeWeb(true);
                    try {
                      const opened = await openLiveWebWindow(
                        rawContent.sourceUrl,
                        rawContent.title || 'VETKA Live Web',
                        getRecommendedSaveNodePath(),
                      );
                      if (opened) {
                        setActiveWebContext({
                          url: rawContent.sourceUrl,
                          title: rawContent.title || 'Web page',
                          summary: rawContent.content || '',
                          source: 'native_window',
                          web_open: true,
                          captured_at: new Date().toISOString(),
                        });
                      }
                    } finally {
                      setOpeningNativeWeb(false);
                    }
                  }}
                  style={{
                    marginLeft: 'auto',
                    border: '1px solid #333',
                    background: '#111',
                    color: '#cfcfcf',
                    fontSize: 10,
                    padding: '2px 8px',
                    borderRadius: 4,
                    cursor: openingNativeWeb ? 'wait' : 'pointer',
                    opacity: openingNativeWeb ? 0.7 : 1,
                  }}
                  title="Open in native Tauri live window"
                >
                  {openingNativeWeb ? 'OPENING...' : 'NATIVE WINDOW'}
                </button>
              )}
              {rawContent.sourceUrl && (
                <button
                  onClick={async () => {
                    if (!rawContent.sourceUrl || webSaving) return;
                    setWebSaving(true);
                    setWebSaveNote('');
                    try {
                      const targetNodePath = getRecommendedSaveNodePath();
                      // MARKER_128.9A_WEB_SAVE_UI: Save real webpage extraction into VETKA artifacts
                      const resp = await fetch('/api/artifacts/save-webpage', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          url: rawContent.sourceUrl,
                          title: rawContent.title || '',
                          snippet: rawContent.content || '',
                          output_format: 'md',
                          file_name: rawContent.title || '',
                          target_node_path: targetNodePath,
                        }),
                      });
                      const data = await resp.json();
                      if (!resp.ok || !data?.success) {
                        throw new Error(data?.error || `HTTP ${resp.status}`);
                      }
                      setWebMarkdown(data.markdown || markdownFallback);
                      setWebMode('md');
                      const where = data?.file_path || targetNodePath || 'default artifact dir';
                      setWebSaveNote(`Saved: ${data?.filename || 'artifact'} -> ${where}`);
                      setActiveWebContext({
                        url: rawContent.sourceUrl,
                        title: data?.title || rawContent.title || 'Web page',
                        summary: String(data?.markdown || markdownFallback).slice(0, 3000),
                        source: 'saved_web_artifact',
                        web_open: true,
                        captured_at: new Date().toISOString(),
                      });
                    } catch (e) {
                      console.error('[ArtifactPanel] save-webpage failed:', e);
                      setWebSaveNote('Save failed');
                    } finally {
                      setWebSaving(false);
                    }
                  }}
                  style={{
                    border: '1px solid #333',
                    background: '#111',
                    color: '#cfcfcf',
                    fontSize: 10,
                    padding: '2px 8px',
                    borderRadius: 4,
                    cursor: webSaving ? 'wait' : 'pointer',
                    opacity: webSaving ? 0.7 : 1,
                  }}
                  title="Save extracted web text as markdown artifact"
                >
                  {webSaving ? 'SAVING...' : 'SAVE TO VETKA'}
                </button>
              )}
            </div>
            <div style={{ flex: 1, minHeight: 0 }}>
              {webMode === 'live' && rawContent.sourceUrl ? (
                <iframe
                  title={rawContent.title || 'Web preview'}
                  src={rawContent.sourceUrl}
                  // MARKER_139.S1_4_WEB_LIVE_DEFAULT: Relaxed sandbox for auth/session-heavy websites
                  sandbox="allow-same-origin allow-scripts allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation allow-downloads"
                  referrerPolicy="strict-origin-when-cross-origin"
                  style={{
                    width: '100%',
                    height: '100%',
                    border: 'none',
                    background: '#fff',
                  }}
                />
              ) : webMode === 'md' ? (
                <MarkdownViewer content={markdownToShow} />
              ) : (
                <div style={{ padding: 16, color: '#777', fontSize: 12 }}>
                  Web URL is missing.
                </div>
              )}
            </div>
            {!!webSaveNote && (
              <div style={{ borderTop: '1px solid #222', padding: '6px 12px', fontSize: 11, color: '#bbb' }}>
                {webSaveNote}
              </div>
            )}
            {!!contentToShow && (
              <div style={{ borderTop: '1px solid #222', padding: '8px 12px', fontSize: 11, color: '#888' }}>
                {contentToShow}
              </div>
            )}
          </div>
        );
      }
      case 'markdown':
        return <MarkdownViewer content={contentToShow} />;
      case 'code':
        return (
          <Suspense fallback={<ViewerLoading />}>
            <CodeViewer
              content={contentToShow}
              filename="response.txt"
              readOnly={true}
              onChange={() => {}}
            />
          </Suspense>
        );
      default:
        // Plain text - use pre with styling
        return (
          <div style={{
            height: '100%',
            overflow: 'auto',
            padding: 20,
            background: '#0a0a0a'
          }}>
            <pre style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              color: '#e0e0e0',
              fontSize: 14,
              lineHeight: 1.6,
              margin: 0,
              fontFamily: 'inherit'
            }}>
              {contentToShow}
            </pre>
          </div>
        );
    }
  };

  // Render viewer based on file type
  const renderViewer = () => {
    if (!fileData || !file) return null;
    const { content, path } = fileData;
    const filename = file.name;
    const fileType = getViewerType(filename);
    const fileUrl = `/api/files/raw?path=${encodeURIComponent(path)}`;
    const mimeType = fileData.mimeType || 'application/octet-stream';
    const isBase64 = fileData.encoding === 'base64';
    const streamMedia = fileType === 'audio' || fileType === 'video' || mimeType.startsWith('audio/') || mimeType.startsWith('video/');
    const previewPlaybackSrc = mediaPreview?.playback?.source_url;
    const mediaSrc = streamMedia ? fileUrl : (isBase64 ? `data:${mimeType};base64,${content}` : fileUrl);
    const videoPoster = mediaPreview?.preview_assets?.poster_url;
    const videoQualitySources: Partial<Record<'Auto' | 'Original' | 'Preview', string>> = {
      Auto: fileUrl,
      Original: fileUrl,
    };
    if (previewPlaybackSrc && previewPlaybackSrc !== fileUrl) {
      videoQualitySources.Preview = previewPlaybackSrc;
    }
    const videoQualityScaleSources: Partial<Record<'full' | 'half' | 'quarter' | 'eighth' | 'sixteenth', string>> = {
      full: mediaPreview?.playback?.sources_scale?.full || fileUrl,
      half: mediaPreview?.playback?.sources_scale?.half,
      quarter: mediaPreview?.playback?.sources_scale?.quarter,
      eighth: mediaPreview?.playback?.sources_scale?.eighth,
      sixteenth: mediaPreview?.playback?.sources_scale?.sixteenth,
    };

    if (/^https?:\/\//i.test(path)) {
      return <MarkdownViewer content={content} />;
    }

    switch (fileType) {
      case 'code':
        return (
          <Suspense fallback={<ViewerLoading />}>
            <CodeViewer
              content={content}
              filename={filename}
              readOnly={!isEditing}
              onChange={updateContent}
            />
          </Suspense>
        );
      case 'markdown':
        // Phase 60.4: Support editing for markdown files
        if (isEditing) {
          return (
            <div style={{
              height: '100%',
              overflow: 'auto',
              padding: 12,
              background: '#0a0a0a'
            }}>
              <textarea
                value={content}
                onChange={(e) => updateContent(e.target.value)}
                style={{
                  width: '100%',
                  height: '100%',
                  minHeight: 400,
                  padding: 16,
                  background: '#111',
                  border: '1px solid #333',
                  borderRadius: 8,
                  color: '#e0e0e0',
                  fontSize: 14,
                  lineHeight: 1.6,
                  fontFamily: 'monospace',
                  resize: 'none',
                  outline: 'none',
                }}
                placeholder="Edit markdown here..."
              />
            </div>
          );
        }
        return <MarkdownViewer content={content} />;
      case 'image':
        return (
          <Suspense fallback={<ViewerLoading />}>
            <ImageViewer url={mediaSrc} filename={filename} />
          </Suspense>
        );
      case 'audio':
        return (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
            <audio
              ref={audioRef}
              controls
              onTimeUpdate={() => handleMediaTimeUpdate(audioRef.current)}
              style={{ width: '100%', maxWidth: 720 }}
            >
              <source src={mediaSrc} type={mimeType} />
            </audio>
          </div>
        );
      case 'video':
        return (
          <div style={{ height: '100%', display: 'flex', alignItems: windowMode === 'detached' ? 'stretch' : 'center', justifyContent: windowMode === 'detached' ? 'flex-start' : 'center', padding: windowMode === 'detached' ? 0 : 16 }}>
            <div style={{ width: '100%', maxWidth: windowMode === 'detached' ? 'none' : 1280, height: '100%' }}>
              <Suspense fallback={<ViewerLoading />}>
                <VideoArtifactPlayer
                  key={`${fileData.path}:${mediaSrc}`}
                  src={mediaSrc}
                  mediaPath={fileData.path}
                  poster={videoPoster}
                  mimeType={mimeType}
                  qualitySources={videoQualitySources}
                  qualityScaleSources={videoQualityScaleSources}
                  windowMode={windowMode}
                  windowLabel={windowMode === 'detached' ? detachedWindowLabel : 'main'}
                  controlsOffsetBottom={0}
                  onFullscreenChange={setIsMediaFullscreen}
                />
              </Suspense>
            </div>
          </div>
        );
      case 'pdf':
        return (
          <iframe
            title={filename}
            src={mediaSrc}
            style={{ width: '100%', height: '100%', border: 'none', background: '#111' }}
          />
        );
      default:
        if (mimeType.startsWith('audio/')) {
          return (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
              <audio
                ref={audioRef}
                controls
                onTimeUpdate={() => handleMediaTimeUpdate(audioRef.current)}
                style={{ width: '100%', maxWidth: 720 }}
              >
                <source src={mediaSrc} type={mimeType} />
              </audio>
            </div>
          );
        }
        if (mimeType.startsWith('video/')) {
          return (
            <div style={{ height: '100%', display: 'flex', alignItems: windowMode === 'detached' ? 'stretch' : 'center', justifyContent: windowMode === 'detached' ? 'flex-start' : 'center', padding: windowMode === 'detached' ? 0 : 16 }}>
              <Suspense fallback={<ViewerLoading />}>
                <VideoArtifactPlayer
                  key={`${fileData.path}:${mediaSrc}`}
                  src={mediaSrc}
                  mediaPath={fileData.path}
                  poster={videoPoster}
                  mimeType={mimeType}
                  qualitySources={videoQualitySources}
                  qualityScaleSources={videoQualityScaleSources}
                  windowMode={windowMode}
                  windowLabel={windowMode === 'detached' ? detachedWindowLabel : 'main'}
                  controlsOffsetBottom={0}
                  onFullscreenChange={setIsMediaFullscreen}
                />
              </Suspense>
            </div>
          );
        }
        if (mimeType === 'application/pdf') {
          return (
            <iframe
              title={filename}
              src={mediaSrc}
              style={{ width: '100%', height: '100%', border: 'none', background: '#111' }}
            />
          );
        }
        return (
          <Suspense fallback={<ViewerLoading />}>
            <CodeViewer
              content={content}
              filename={filename}
              readOnly={!isEditing}
              onChange={updateContent}
            />
          </Suspense>
        );
    }
  };

  // Phase 48.5.1: Copy raw content
  // Phase 60.4: Copy current content (edited or original)
  const handleCopyRaw = () => navigator.clipboard.writeText(isEditing ? editableContent : (rawContent?.content || ''));

  const normalizeFsPath = useCallback((p?: string | null): string => {
    return normalizeDetachedArtifactPath(String(p || ''));
  }, []);

  const currentArtifactPath = useMemo(() => (
    normalizeFsPath(fileData?.path || file?.path || '')
  ), [fileData?.path, file?.path, normalizeFsPath]);

  useEffect(() => {
    if (windowMode !== 'detached') {
      setDetachedChatState(null);
      return;
    }

    const syncDetachedChatState = () => {
      setDetachedChatState(readDetachedArtifactChatState());
    };

    syncDetachedChatState();
    window.addEventListener('focus', syncDetachedChatState);
    document.addEventListener('visibilitychange', syncDetachedChatState);
    const onStorage = (event: StorageEvent) => {
      if (event.key === DETACHED_ARTIFACT_CHAT_STATE_KEY) {
        syncDetachedChatState();
      }
    };
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener('focus', syncDetachedChatState);
      document.removeEventListener('visibilitychange', syncDetachedChatState);
      window.removeEventListener('storage', onStorage);
    };
  }, [windowMode]);

  const pinTargetNodeId = useMemo(() => {
    if (!currentArtifactPath) return null;
    const matchId = Object.keys(nodes).find((id) => normalizeFsPath(nodes[id]?.path) === currentArtifactPath);
    return matchId || null;
  }, [currentArtifactPath, nodes, normalizeFsPath]);

  const detachedPinVisible = useMemo(() => (
    windowMode === 'detached' && Boolean(currentArtifactPath && isInVetka)
  ), [currentArtifactPath, isInVetka, windowMode]);

  const detachedPinnedInChat = useMemo(() => {
    if (windowMode !== 'detached' || !currentArtifactPath) return false;
    const pinned = detachedChatState?.pinned_paths || [];
    return pinned.includes(currentArtifactPath);
  }, [currentArtifactPath, detachedChatState?.pinned_paths, windowMode]);

  const detachedPinDisabled = useMemo(() => {
    if (windowMode !== 'detached') return false;
    if (!detachedPinVisible) return true;
    return !detachedChatState?.chat_open;
  }, [detachedChatState?.chat_open, detachedPinVisible, windowMode]);

  const isPinnedInChat = useMemo(() => (
    Boolean(pinTargetNodeId && pinnedFileIds.includes(pinTargetNodeId))
  ), [pinTargetNodeId, pinnedFileIds]);

  const effectivePinVisible = windowMode === 'detached' ? detachedPinVisible : Boolean(pinTargetNodeId);
  const effectiveIsPinnedInChat = windowMode === 'detached' ? detachedPinnedInChat : isPinnedInChat;
  const effectivePinDisabled = windowMode === 'detached'
    ? detachedPinDisabled
    : (!isChatOpen || !pinTargetNodeId);
  const effectivePinTitle = windowMode === 'detached'
    ? (
      !detachedPinVisible
        ? 'File is not indexed in VETKA tree'
        : (!detachedChatState?.chat_open
            ? 'Open chat in VETKA to pin context'
            : (detachedPinnedInChat ? 'Unpin from chat context' : 'Pin to chat context'))
    )
    : (
      !pinTargetNodeId
        ? 'File is not indexed in VETKA tree'
        : (!isChatOpen ? 'Open chat to pin context' : (isPinnedInChat ? 'Unpin from chat context' : 'Pin to chat context'))
    );

  const handlePinToChat = useCallback(() => {
    if (windowMode === 'detached') {
      if (!currentArtifactPath || !isInVetka) return;
      writeDetachedArtifactPinRequest({
        schema_version: 'detached_artifact_pin_request_v1',
        action: 'toggle_pin',
        path: currentArtifactPath,
        requested_at_ms: Date.now(),
        request_id: `detached-pin-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      });
      return;
    }
    if (!isChatOpen || !pinTargetNodeId) return;
    togglePinFile(pinTargetNodeId);
  }, [currentArtifactPath, isChatOpen, isInVetka, pinTargetNodeId, togglePinFile, windowMode]);

  // Phase 60.4: Save edited raw content
  const handleSaveRaw = () => {
    if (onContentChange && rawHasChanges) {
      onContentChange(editableContent);
      setRawHasChanges(false);
      setIsEditing(false);
    }
  };

  // Phase 60.4: Open file in Finder (macOS)
  const handleOpenInFinder = async () => {
    if (!fileData?.path) return;
    try {
      await fetch('/api/files/open-in-finder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: fileData.path }),
      });
    } catch (err) {
      console.error('[ArtifactPanel] Open in Finder error:', err);
    }
  };

  const isMediaArtifact = Boolean(
    fileData && (
      ['audio', 'video'].includes(getViewerType(fileData.path || file?.name || '')) ||
      String(fileData.mimeType || '').startsWith('audio/') ||
      String(fileData.mimeType || '').startsWith('video/')
    )
  );

  const handleOpenDetachedMediaWindow = useCallback(async () => {
    if (!isTauri()) return;
    if (windowMode === 'detached') return;
    if (!fileData?.path || !isMediaArtifact) return;

    const fallbackName = String(file?.name || '').trim() || String(fileData.path || '').replace(/\\/g, '/').split('/').pop() || 'media';
    const extFromPath = String(fileData.path || '').replace(/\\/g, '/').split('.').pop() || '';
    const extension = String(file?.extension || extFromPath || '').replace(/^\./, '');

    const opened = await openArtifactMediaWindow({
      path: fileData.path,
      name: fallbackName,
      extension: extension || undefined,
      artifactId,
      inVetka: isInVetka,
      initialSeekSec: Number.isFinite(activeSeekSec as number) ? activeSeekSec : undefined,
    });

    if (opened && typeof onClose === 'function') {
      onClose();
    }
  }, [activeSeekSec, artifactId, file?.extension, file?.name, fileData?.path, isInVetka, isMediaArtifact, onClose, windowMode]);

  const handleCloseDetachedWindow = useCallback(async () => {
    if (windowMode !== 'detached') {
      onClose?.();
      return;
    }
    if (!isTauri()) {
      window.close();
      return;
    }
    const closed = await closeArtifactMediaWindow(detachedWindowLabel);
    if (!closed) {
      window.close();
    }
  }, [detachedWindowLabel, onClose, windowMode]);

  // Phase 60.4: Save As / Duplicate - download with custom name
  const handleSaveAs = async () => {
    const content = isRawContentMode
      ? (isEditing ? editableContent : rawContent?.content || '')
      : (fileData?.content || '');
    const defaultName = isRawContentMode
      ? 'artifact.md'
      : (fileData?.path.split('/').pop() || 'file.txt');

    const newName = prompt('Save as:', defaultName);
    if (!newName) return;
    if (isTauri()) {
      await saveTextFileNative(newName, content, 'Save artifact as');
      return;
    }
    downloadViaBrowser(content, newName);
  };

  const handleMediaTimeUpdate = useCallback((el: HTMLMediaElement | null) => {
    if (!el) return;
    const now = Date.now();
    if (now - lastTimeupdateRef.current < MEDIA_TIMEUPDATE_THROTTLE_MS) return;
    lastTimeupdateRef.current = now;
    if (Number.isFinite(el.currentTime)) setActiveSeekSec(el.currentTime);
  }, []);

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: '#0a0a0a',
      position: 'relative',
    }}>
      {/* Loading overlay */}
      {isLoading && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(10, 10, 10, 0.8)',
          zIndex: 50,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Loader2 size={32} color="#666" style={{ animation: 'spin 1s linear infinite' }} />
        </div>
      )}

      {/* Phase 48.5.1: Raw content mode */}
      {/* Phase 60.4: Added editing support */}
      {isRawContentMode && rawContent && (
        <>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {renderRawContent()}
          </div>
          <Toolbar
            filename={rawContent.title}
            fileSize={isEditing ? editableContent.length : rawContent.content.length}
            isEditing={isEditing && rawContent.type !== 'web'}
            hasChanges={rawHasChanges}
            isSaving={false}
            canUndo={canUndo}
            onEdit={rawContent.type === 'web' ? undefined : () => setIsEditing(!isEditing)}
            onUndo={rawContent.type === 'web' ? undefined : handleUndo}
            onSave={rawContent.type === 'web' ? undefined : handleSaveRaw}
            onSaveAs={() => { void handleSaveAs(); }}
            onCopy={handleCopyRaw}
            onDownload={() => {
              const content = isEditing ? editableContent : rawContent.content;
              if (isTauri()) {
                void saveTextFileNative('response.txt', content, 'Save artifact response');
                return;
              }
              downloadViaBrowser(content, 'response.txt');
            }}
            onRefresh={undefined}
            onPin={handlePinToChat}
            isPinned={effectiveIsPinnedInChat}
            pinVisible={effectivePinVisible}
            pinDisabled={effectivePinDisabled}
            pinTitle={effectivePinTitle}
            onClose={onClose}
          />
        </>
      )}

      {/* File mode - Empty state */}
      {!isRawContentMode && !file && !isLoading && (
        <div style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#666',
        }}>
          <p>Select a file to view</p>
        </div>
      )}

      {/* File mode - Viewer */}
      {!isRawContentMode && fileData && (
        <>
          {activeSeekSec !== undefined && isMediaArtifact && mediaInfoOpen && (
            <div
              style={{
                padding: '6px 12px',
                borderBottom: '1px solid #232323',
                fontSize: 11,
                color: '#9ca3af',
                background: 'rgba(255, 255, 255, 0.03)',
              }}
            >
              timeline: t={activeSeekSec.toFixed(1)}s
            </div>
          )}
          {mediaPreview && mediaInfoOpen && (
            <div className="artifact-media-preview">
              <div className="artifact-media-preview-header">
                <div className="artifact-media-preview-meta">
                  <span>{mediaPreview.modality.toUpperCase()} preview</span>
                  <span className="artifact-media-preview-badge">{mediaPreview.mime_type}</span>
                  {mediaPreview.degraded_mode && (
                    <span className="artifact-media-preview-badge degraded" title={mediaPreview.degraded_reason || 'degraded'}>
                      degraded
                    </span>
                  )}
                </div>
                <span>{mediaPreview.duration_sec.toFixed(1)}s</span>
              </div>
              <div className="artifact-media-preview-zoom">
                {[1, 2, 4].map((zoom) => (
                  <button
                    key={`zoom-${zoom}`}
                    type="button"
                    onClick={() => setTimelineZoom(zoom)}
                    className={timelineZoom === zoom ? 'active' : ''}
                  >
                    {zoom}x
                  </button>
                ))}
              </div>
              <div className="artifact-media-preview-strip" style={{ fontSize: 11, color: '#9ca3af' }}>
                <div>mime: {mediaPreview.mime_type}</div>
                <div>source: {mediaPreview.playback?.strategy || 'direct'}</div>
                {mediaPreview.degraded_mode && (
                  <div>degraded: {mediaPreview.degraded_reason || 'unknown'}</div>
                )}
              </div>
              {mediaPreview.waveform_bins?.length > 0 && (
                <div className="artifact-media-preview-strip">
                  <div
                    className="artifact-media-waveform"
                    style={{
                      minWidth: `${timelineWidthPct}%`,
                      gridTemplateColumns: `repeat(${mediaPreview.waveform_bins.length}, 1fr)`,
                    }}
                  >
                  {mediaPreview.waveform_bins.map((amp, idx) => (
                    <div
                      key={`wf-${idx}`}
                      className="artifact-media-waveform-bar"
                      style={{ height: `${Math.max(6, Math.round(amp * 100))}%` }}
                    />
                  ))}
                  </div>
                </div>
              )}
              {mediaPreview.timeline_segments?.length > 0 && mediaPreview.duration_sec > 0 && (
                <div className="artifact-media-preview-strip">
                  {(['video_main', 'audio_sync', 'take_alt_y'] as const).map((lane) => {
                    const laneSegments = mediaPreview.timeline_segments.filter((seg) => (seg.timeline_lane || 'video_main') === lane);
                    if (laneSegments.length === 0) return null;
                    return (
                      <div key={`lane-${lane}`} className="artifact-media-lane-row">
                        <div className="artifact-media-lane-label">{lane}</div>
                        <div
                          className="artifact-media-timeline"
                          style={{ minWidth: `${timelineWidthPct}%` }}
                        >
                          {rhythmOverlay.bars.length > 0 && (
                            <div className="artifact-rhythm-overlay-track" aria-hidden="true">
                              {rhythmOverlay.bars.map((bar, idx) => (
                                <div
                                  key={`rob-${lane}-${idx}`}
                                  className="artifact-rhythm-overlay-bar"
                                  style={{
                                    left: `${bar.leftPct}%`,
                                    width: `${bar.widthPct}%`,
                                    opacity: `${0.1 + bar.amp * 0.55}`,
                                  }}
                                />
                              ))}
                              {rhythmOverlay.markers.map((marker, idx) => (
                                <div
                                  key={`rom-${lane}-${idx}`}
                                  className="artifact-rhythm-overlay-marker"
                                  style={{ left: `${marker.leftPct}%` }}
                                  title={marker.kind}
                                />
                              ))}
                            </div>
                          )}
                          {typeof activeSeekSec === 'number' && (
                            <div
                              className="artifact-media-playhead"
                              style={{
                                left: `${Math.max(0, Math.min(100, (activeSeekSec / mediaPreview.duration_sec) * 100))}%`,
                              }}
                            />
                          )}
                          {laneSegments.map((seg, idx) => {
                            const leftPct = Math.max(0, Math.min(100, (seg.start_sec / mediaPreview.duration_sec) * 100));
                            const widthPct = Math.max(
                              0.6,
                              Math.min(100 - leftPct, ((Math.max(seg.end_sec, seg.start_sec) - seg.start_sec) / mediaPreview.duration_sec) * 100)
                            );
                            const isActive = typeof activeSeekSec === 'number' && activeSeekSec >= seg.start_sec && activeSeekSec <= seg.end_sec;
                            return (
                                <button
                                  key={seg.chunk_id || `${lane}-seg-${idx}`}
                                  type="button"
                                  onClick={() => { void handleSegmentClick(seg); }}
                                  title={`${lane} • ${seg.start_sec.toFixed(2)}s — ${seg.end_sec.toFixed(2)}s`}
                                  className={`artifact-media-segment lane-${lane}${isActive ? ' active' : ''}`}
                                  style={{
                                    left: `${leftPct}%`,
                                    width: `${widthPct}%`,
                                }}
                              />
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                  {mediaPreview.timeline_segments.some((seg) => (seg.timeline_lane || 'video_main') === 'take_alt_z') && (
                    <div className="artifact-media-lane-note">take_alt_z detected (experimental)</div>
                  )}
                </div>
              )}
              {mediaPreview.modality === 'video' && mediaPreview.preview_assets?.poster_url && (
                <div className="artifact-media-preview-strip">
                  <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 6 }}>poster</div>
                  <img
                    src={mediaPreview.preview_assets.poster_url}
                    alt="video poster preview"
                    style={{ width: 180, aspectRatio: '16 / 9', objectFit: 'cover', borderRadius: 6, border: '1px solid #2f2f2f' }}
                  />
                </div>
              )}
              {mediaPreview.modality === 'video' && mediaPreview.preview_assets?.animated_preview_url_300ms && (
                <div className="artifact-media-preview-strip">
                  <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 6 }}>dynamic preview 300ms</div>
                  <img
                    src={mediaPreview.preview_assets.animated_preview_url_300ms}
                    alt="video dynamic preview"
                    style={{ width: 180, aspectRatio: '16 / 9', objectFit: 'cover', borderRadius: 6, border: '1px solid #2f2f2f' }}
                  />
                </div>
              )}
              {(semanticLinks.loading || semanticLinks.items.length > 0 || semanticLinks.error) && (
                <div className="artifact-semantic-links">
                  <div className="artifact-semantic-links-title">semantic links</div>
                  {semanticLinks.loading && (
                    <div className="artifact-semantic-links-note">loading...</div>
                  )}
                  {semanticLinks.error && !semanticLinks.loading && (
                    <div className="artifact-semantic-links-note">{semanticLinks.error}</div>
                  )}
                  {!semanticLinks.loading && semanticLinks.items.slice(0, 8).map((link, idx) => (
                    <button
                      key={`sl-${idx}-${link.parent_file_path}-${link.start_sec}`}
                      type="button"
                      className="artifact-semantic-link-item"
                      onClick={() => {
                        const currentPath = String(fileData?.path || '');
                        if (link.parent_file_path === currentPath) {
                          setActiveSeekSec(link.start_sec);
                          return;
                        }
                        const pathParts = String(link.parent_file_path).replace(/\\/g, '/').split('/');
                        const fileName = pathParts[pathParts.length - 1] || 'artifact';
                        window.dispatchEvent(new CustomEvent('vetka-open-artifact', {
                          detail: {
                            filePath: link.parent_file_path,
                            fileName,
                            startSec: link.start_sec,
                          },
                        }));
                      }}
                    >
                      <span className={`artifact-semantic-rel rel-${link.relation_type}`}>{link.relation_type}</span>
                      <span className="artifact-semantic-time">{link.start_sec.toFixed(1)}s</span>
                      <span className="artifact-semantic-text">{link.text || '(empty)'}</span>
                    </button>
                  ))}
                </div>
              )}
              {(rhythmAssist.loading || rhythmAssist.data || rhythmAssist.error) && (
                <div className="artifact-rhythm-assist">
                  <div className="artifact-rhythm-assist-title">rhythm assist (P5.6)</div>
                  {rhythmAssist.loading && (
                    <div className="artifact-rhythm-note">analyzing...</div>
                  )}
                  {rhythmAssist.error && !rhythmAssist.loading && (
                    <div className="artifact-rhythm-note">{rhythmAssist.error}</div>
                  )}
                  {rhythmAssist.data && !rhythmAssist.loading && (
                    <>
                      <div className="artifact-rhythm-metrics">
                        <span>cut/min: {rhythmAssist.data.rhythm_features.cut_density.per_min.toFixed(2)}</span>
                        <span>motion: {rhythmAssist.data.rhythm_features.motion_volatility.toFixed(3)}</span>
                        <span>bpm: {rhythmAssist.data.music_binding.target_bpm}</span>
                        <span>shot: {rhythmAssist.data.recommended_shot_sec.toFixed(2)}s</span>
                      </div>
                      <div className="artifact-rhythm-reco-list">
                        {rhythmAssist.data.recommendations.slice(0, 3).map((r, i) => (
                          <div key={`rr-${i}`} className="artifact-rhythm-reco-item">{r}</div>
                        ))}
                      </div>
                      <div className="artifact-rhythm-phases">
                        {rhythmAssist.data.rhythm_features.phase_markers.slice(0, 12).map((m, i) => (
                          <button
                            key={`pm-${i}`}
                            type="button"
                            className="artifact-rhythm-phase-btn"
                            onClick={() => setActiveSeekSec(m.time_sec)}
                            title={m.kind}
                          >
                            {m.time_sec.toFixed(1)}s
                          </button>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {renderViewer()}
          </div>
        </>
      )}

      {/* File mode - Toolbar */}
      {!isRawContentMode && fileData && !(isMediaArtifact && windowMode === 'detached' && isMediaFullscreen) && (
        <Toolbar
          filename={file?.name || ''}
          filePath={fileData.path}
          fileSize={fileData.fileSize}
          createdAt={fileData.createdAt}
          modifiedAt={fileData.modifiedAt}
          isEditing={isEditing}
          hasChanges={fileData.hasChanges}
          isSaving={isSaving}
          onEdit={isMediaArtifact ? undefined : () => setIsEditing(!isEditing)}
          onSave={isMediaArtifact ? undefined : saveFile}
          onSaveAs={isMediaArtifact ? undefined : () => { void handleSaveAs(); }}
          onCopy={isMediaArtifact ? undefined : handleCopy}
          onInfo={isMediaArtifact ? () => setMediaInfoOpen((v) => !v) : undefined}
          infoActive={isMediaArtifact ? mediaInfoOpen : undefined}
          onDownload={() => { void handleDownload(); }}
          onOpenInFinder={handleOpenInFinder}
          onRefresh={() => file && loadFile(file.path)}
          onDetach={isMediaArtifact && windowMode !== 'detached' ? () => { void handleOpenDetachedMediaWindow(); } : undefined}
          onPin={handlePinToChat}
          isPinned={effectiveIsPinnedInChat}
          pinVisible={effectivePinVisible}
          pinDisabled={effectivePinDisabled}
          pinTitle={effectivePinTitle}
          detachedShowFavorite={windowMode === 'detached' && (isInVetka || !isFileMode)}
          detachedFavoriteActive={isFavorite}
          detachedFavoriteBusy={false}
          onDetachedFavoriteToggle={() => { void handleToggleFavoriteDetached(); }}
          detachedShowVetka={windowMode === 'detached' && isFileMode && !isInVetka}
          detachedVetkaBusy={isIndexingToVetka}
          onDetachedVetkaAdd={() => { void handleAddToVetkaDetached(); }}
          onClose={windowMode === 'detached' ? () => { void handleCloseDetachedWindow(); } : onClose}
          compact={windowMode === 'detached' && isMediaArtifact}
        />
      )}
    </div>
  );
}
