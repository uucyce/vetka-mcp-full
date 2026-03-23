/**
 * MARKER_188.1: ProjectPanel — Premiere-style Project panel (media bin + import).
 *
 * Architecture: Standard NLE layout places the Project panel at bottom-left.
 * This panel manages imported media assets, organized by bins (buckets).
 *
 * Import methods (matching Premiere Pro):
 * 1. Cmd+I hotkey (via 'cut:import-media' custom event from MenuBar/hotkeys)
 * 2. Double-click dropzone to open native file picker
 * 3. Drag & drop files/folders into the panel (future: Tauri native)
 *
 * Terminology follows Premiere Pro conventions:
 * - "Project" panel (not "Source Browser")
 * - "Bin" (folder/category)
 * - "Clip" (media reference)
 * - Import triggers bootstrap-async pipeline on backend
 */
import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react';
import { useCutEditorStore, type ThumbnailItem } from '../../store/useCutEditorStore';
import { API_BASE } from '../../config/api.config';
import DAGProjectPanel from './DAGProjectPanel';

// MARKER_W5.4 + GAMMA-P1.2: View mode type
type ProjectViewMode = 'list' | 'columns' | 'grid' | 'dag';

// ─── Bin (bucket) types ───

type BinKey = 'video' | 'audio' | 'music_track' | 'stills' | 'boards' | 'documents' | 'other';

interface BinDef {
  key: BinKey;
  label: string;
  icon: string;
}

const BIN_ORDER: BinDef[] = [
  { key: 'video',       label: 'Video Clips',  icon: '▶' },
  { key: 'audio',       label: 'Audio',        icon: '♪' },
  { key: 'music_track', label: 'Music',        icon: '♫' },
  { key: 'stills',      label: 'Stills',       icon: '◻' },
  { key: 'boards',      label: 'Boards',       icon: '▦' },
  { key: 'documents',   label: 'Documents',    icon: '≡' },
  { key: 'other',       label: 'Other',        icon: '●' },
];

const MEDIA_ACCEPT = 'video/*,audio/*,image/*,.mov,.mp4,.avi,.mkv,.webm,.m4a,.wav,.mp3,.flac,.aac,.ogg,.jpg,.jpeg,.png,.tiff,.bmp,.webp';

interface ProjectItem extends ThumbnailItem {
  binKey: BinKey;
  binLabel: string;
}

// ─── Styles (§11 compliant: monochrome with subtle accent) ───

const PANEL: CSSProperties = {
  width: '100%',
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  background: '#0D0D0D',
  fontFamily: 'Inter, system-ui, sans-serif',
  overflow: 'hidden',
};

const HEADER: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '6px 10px',
  fontSize: 10,
  color: '#888',
  borderBottom: '1px solid #1A1A1A',
  flexShrink: 0,
};

const IMPORT_AREA: CSSProperties = {
  padding: '8px 10px',
  borderBottom: '1px solid #1A1A1A',
  flexShrink: 0,
};

const DROPZONE: CSSProperties = {
  border: '1px dashed #2f2f2f',
  borderRadius: 4,
  padding: '14px 12px',
  textAlign: 'center',
  fontSize: 10,
  color: '#555',
  cursor: 'pointer',
  transition: 'border-color 0.2s, background 0.2s',
};

const STATUS_LINE: CSSProperties = {
  fontSize: 9,
  color: '#555',
  marginTop: 6,
};

const BIN_LIST: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  overflowX: 'hidden',
};

const BIN_HEADER: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '4px 10px',
  fontSize: 10,
  color: '#666',
  borderBottom: '1px solid #1A1A1A',
  cursor: 'pointer',
  userSelect: 'none',
};

const CLIP_ITEM: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '4px 10px 4px 18px',
  cursor: 'pointer',
  transition: 'background 0.15s',
};

const THUMB: CSSProperties = {
  width: 40,
  height: 28,
  borderRadius: 2,
  background: '#1A1A1A',
  objectFit: 'cover',
  flexShrink: 0,
};

// MARKER_W5.4: Grid view styles
const GRID_CONTAINER: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(80px, 1fr))',
  gap: 4,
  padding: 6,
};

const GRID_ITEM: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: 4,
  borderRadius: 4,
  cursor: 'pointer',
  transition: 'background 0.15s',
};

const GRID_THUMB: CSSProperties = {
  width: '100%',
  aspectRatio: '16/9',
  borderRadius: 3,
  background: '#1A1A1A',
  objectFit: 'cover',
};

const MODE_SWITCH_BTN: CSSProperties = {
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  padding: '1px 5px',
  fontSize: 9,
  fontFamily: 'system-ui',
  borderRadius: 2,
};

// ─── Helpers ───

function basename(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

function labelForPath(path: string): string {
  const parts = path.split(/[\\/]/).filter(Boolean);
  return parts.length > 0 ? parts[parts.length - 1] : 'project';
}

// MARKER_GAMMA-14: Custom drag preview — thumbnail + filename badge
function setDragPreview(
  e: React.DragEvent,
  name: string,
  modality: string | undefined,
  posterUrl: string | undefined,
) {
  const el = document.createElement('div');
  el.style.cssText = 'position:fixed;top:-200px;left:-200px;width:80px;padding:4px;background:#1a1a1a;border:1px solid #555;border-radius:4px;font-size:8px;font-family:system-ui,sans-serif;color:#ccc;text-align:center;pointer-events:none;z-index:99999';
  if (posterUrl) {
    const img = document.createElement('img');
    img.src = posterUrl;
    img.style.cssText = 'width:72px;height:48px;object-fit:cover;border-radius:2px;display:block;margin:0 auto 3px';
    el.appendChild(img);
  } else {
    const icon = document.createElement('div');
    icon.style.cssText = 'width:72px;height:48px;display:flex;align-items:center;justify-content:center;font-size:20px;color:#444;margin:0 auto 3px';
    icon.textContent = modality === 'audio' ? '\u266A' : modality === 'image' ? '\u25FB' : '\u25B6';
    el.appendChild(icon);
  }
  const label = document.createElement('div');
  label.style.cssText = 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:72px;margin:0 auto';
  label.textContent = name;
  el.appendChild(label);
  document.body.appendChild(el);
  e.dataTransfer.setDragImage(el, 40, 30);
  requestAnimationFrame(() => document.body.removeChild(el));
}

// MARKER_W6.IMPORT-FIX: Infer folder path from file list (Tauri native or browser webkitdirectory)
function inferFolderPath(files: FileList | null): string {
  if (!files || files.length === 0) return '';
  const first = files[0] as File & { path?: string; webkitRelativePath?: string };
  // Tauri/Electron: native path available
  if (typeof first.path === 'string' && first.path) {
    return first.path.replace(/[\\/][^\\/]+$/, '');
  }
  // Browser webkitdirectory: webkitRelativePath = "folder/subfolder/file.mp4"
  // We can't get absolute path in browser — return empty for now
  // The uploadAndImport flow handles browser mode
  return '';
}

function classifyItem(item: ThumbnailItem, laneTypesByPath: Map<string, Set<string>>): ProjectItem {
  const lower = item.source_path.toLowerCase();
  const laneTypes = laneTypesByPath.get(item.source_path) ?? new Set();
  const isBoard = lower.includes('/boards/') || lower.includes('\\boards\\');
  const isMusicTrack = (item.modality === 'audio' || laneTypes.has('audio_sync')) && laneTypes.has('audio_sync');

  let binKey: BinKey = 'video';
  let binLabel = 'Video Clips';

  if (isMusicTrack) {
    binKey = 'music_track'; binLabel = 'Music';
  } else if (isBoard) {
    binKey = 'boards'; binLabel = 'Boards';
  } else if (item.modality === 'audio') {
    binKey = 'audio'; binLabel = 'Audio';
  } else if (item.modality === 'image') {
    binKey = 'stills'; binLabel = 'Stills';
  } else if (item.modality === 'document') {
    binKey = 'documents'; binLabel = 'Documents';
  }

  return { ...item, binKey, binLabel };
}

// ─── Component ───

export default function ProjectPanel() {
  // Store selectors
  const storeSandboxRoot = useCutEditorStore((s) => s.sandboxRoot);
  const projectId = useCutEditorStore((s) => s.projectId);
  const refreshProjectState = useCutEditorStore((s) => s.refreshProjectState);
  const setEditorSession = useCutEditorStore((s) => s.setEditorSession);
  const thumbnails = useCutEditorStore((s) => s.thumbnails);
  const lanes = useCutEditorStore((s) => s.lanes);
  const activeMediaPath = useCutEditorStore((s) => s.sourceMediaPath);
  // MARKER_W1.3: Project click → Source Monitor (not program)
  const setActiveMedia = useCutEditorStore((s) => s.setSourceMedia);
  const setSelectedClip = useCutEditorStore((s) => s.setSelectedClip);

  // Local state
  const [importStatus, setImportStatus] = useState('');
  const [importProgress, setImportProgress] = useState<number | null>(null);
  const [importing, setImporting] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [collapsedBins, setCollapsedBins] = useState<Set<string>>(new Set());
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  // MARKER_W5.4: View mode
  const [viewMode, setViewMode] = useState<ProjectViewMode>('list');
  // MARKER_GAMMA-19: Context menu for project items
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; path: string } | null>(null);
  // MARKER_GAMMA-P1.4: Search/filter clips
  const [searchQuery, setSearchQuery] = useState('');
  // MARKER_GAMMA-P1.2: Column sort
  type SortKey = 'name' | 'duration' | 'modality';
  type SortDir = 'asc' | 'desc';
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  // ─── Open file picker ───
  const openFilePicker = useCallback(() => {
    if (importing) return;
    fileInputRef.current?.click();
  }, [importing]);

  // ─── Listen for Cmd+I hotkey (from CutEditorLayoutV2 importMedia handler) ───
  useEffect(() => {
    const handler = () => openFilePicker();
    // MARKER_W6.IMPORT-FIX: Listen for BOTH event names for backward compat
    window.addEventListener('cut:import-media', handler);
    window.addEventListener('cut:trigger-import', handler);
    return () => {
      window.removeEventListener('cut:import-media', handler);
      window.removeEventListener('cut:trigger-import', handler);
    };
  }, [openFilePicker]);

  // ─── Job polling — returns the completed job result ───
  const pollJob = useCallback(async (jobId: string): Promise<Record<string, unknown>> => {
    for (let attempt = 0; attempt < 80; attempt++) {
      const res = await fetch(`${API_BASE}/cut/job/${encodeURIComponent(jobId)}`);
      if (!res.ok) throw new Error(`Job failed: HTTP ${res.status}`);
      const payload = (await res.json()) as {
        job?: {
          state?: string;
          progress?: number;
          result?: Record<string, unknown>;
          error?: { message?: string } | null;
        };
      };
      const state = String(payload.job?.state || '');
      setImportProgress(typeof payload.job?.progress === 'number' ? payload.job.progress : null);
      if (state === 'done') return payload.job?.result || {};
      if (state === 'error') throw new Error(payload.job?.error?.message || 'Import failed');
      await new Promise((r) => setTimeout(r, 250));
    }
    throw new Error('Import timed out');
  }, []);

  // ─── Start import: bootstrap → scene-assembly → refresh ───
  const startImport = useCallback(async (path: string) => {
    const trimmed = path.trim();
    if (!trimmed) {
      setImportStatus('No media path could be determined.');
      return;
    }

    // Auto-derive sandbox if not set
    let sandboxRoot = storeSandboxRoot;
    if (!sandboxRoot) {
      sandboxRoot = `${trimmed}/cut_sandbox`;
      setEditorSession({ sandboxRoot });
    }

    setImporting(true);
    setImportProgress(0);
    setImportStatus(`Scanning ${labelForPath(trimmed)}...`);

    try {
      // Step 1: Bootstrap — scan folder, create project
      const bootstrapRes = await fetch(`${API_BASE}/cut/bootstrap-async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: trimmed,
          sandbox_root: sandboxRoot,
          project_name: projectId || labelForPath(trimmed),
          mode: 'create_or_open',
          use_core_mirror: true,
          create_project_if_missing: true,
        }),
      });
      if (!bootstrapRes.ok) throw new Error(`Bootstrap failed: HTTP ${bootstrapRes.status}`);

      const bootstrapPayload = (await bootstrapRes.json()) as {
        success?: boolean;
        job_id?: string;
        project?: { project_id?: string };
        error?: { message?: string } | null;
      };
      if (!bootstrapPayload.success || !bootstrapPayload.job_id) {
        throw new Error(bootstrapPayload.error?.message || 'Bootstrap did not start');
      }

      const bootstrapResult = await pollJob(bootstrapPayload.job_id);
      setImportProgress(0.4);

      // Extract project_id from bootstrap job result
      const resultProject = bootstrapResult?.project as { project_id?: string } | undefined;
      const pid = resultProject?.project_id || projectId || labelForPath(trimmed);
      setEditorSession({ sourcePath: trimmed, projectId: pid });

      // Step 2: Scene assembly — build timeline lanes + clips from scanned files
      setImportStatus(`Building timeline for ${labelForPath(trimmed)}...`);
      const assemblyRes = await fetch(`${API_BASE}/cut/scene-assembly-async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: pid,
          timeline_id: 'main',
          graph_id: 'main',
        }),
      });
      if (!assemblyRes.ok) throw new Error(`Scene assembly failed: HTTP ${assemblyRes.status}`);

      const assemblyPayload = (await assemblyRes.json()) as {
        success?: boolean;
        job_id?: string;
        error?: { message?: string } | null;
      };
      if (assemblyPayload.success && assemblyPayload.job_id) {
        await pollJob(assemblyPayload.job_id);
      }
      setImportProgress(0.8);

      // MARKER_W6.IMPORT-FIX: Refresh project state → populates thumbnails + lanes in store.
      // Call refreshProjectState from store, but also trigger a direct re-fetch
      // because the closure may have stale projectId.
      await refreshProjectState?.();
      // Fallback: direct fetch to force store hydration with correct pid
      try {
        const stateRes = await fetch(
          `${API_BASE}/cut/project-state?sandbox_root=${encodeURIComponent(sandboxRoot)}&project_id=${encodeURIComponent(pid)}`
        );
        if (stateRes.ok) {
          const statePayload = await stateRes.json();
          if (statePayload.success) {
            const tl = statePayload.timeline_state;
            if (tl?.lanes) {
              useCutEditorStore.getState().setLanes(tl.lanes);
            }
            if (tl?.markers) {
              useCutEditorStore.getState().setMarkers(tl.markers);
            }
            useCutEditorStore.getState().setEditorSession({
              sandboxRoot,
              projectId: pid,
              sourcePath: trimmed,
              timelineId: String(tl?.timeline_id || 'main'),
            });
          }
        }
      } catch { /* non-critical fallback */ }
      setImportStatus(`Imported ${labelForPath(trimmed)}`);
      setImportProgress(1);
    } catch (err) {
      setImportStatus(err instanceof Error ? err.message : 'Import failed');
      setImportProgress(null);
    } finally {
      setImporting(false);
    }
  }, [pollJob, projectId, refreshProjectState, storeSandboxRoot, setEditorSession]);

  // ─── Upload files to backend (browser mode — no native paths) ───
  const uploadAndImport = useCallback(async (files: FileList) => {
    setImporting(true);
    setImportProgress(0);
    setImportStatus(`Uploading ${files.length} files...`);

    try {
      // Upload via multipart form
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }
      // Pass sandbox hint so backend knows where to save
      let sandboxRoot = storeSandboxRoot;
      if (!sandboxRoot) {
        sandboxRoot = `/tmp/cut_sandbox_${Date.now()}`;
        setEditorSession({ sandboxRoot });
      }
      formData.append('sandbox_root', sandboxRoot);
      formData.append('project_name', projectId || 'imported');

      const uploadRes = await fetch(`${API_BASE}/cut/import-files`, {
        method: 'POST',
        body: formData,
      });

      if (!uploadRes.ok) {
        // Fallback: if endpoint doesn't exist yet, tell user
        if (uploadRes.status === 404 || uploadRes.status === 405) {
          setImportStatus('Browser file upload not yet supported. Use Tauri app or paste a folder path in the URL.');
          setImportProgress(null);
          return;
        }
        throw new Error(`Upload failed: HTTP ${uploadRes.status}`);
      }

      const uploadPayload = (await uploadRes.json()) as {
        success?: boolean;
        source_path?: string;
        error?: { message?: string } | null;
      };
      if (!uploadPayload.success || !uploadPayload.source_path) {
        throw new Error(uploadPayload.error?.message || 'Upload failed');
      }

      // Now run the normal import pipeline on the uploaded folder
      void startImport(uploadPayload.source_path);
    } catch (err) {
      setImportStatus(err instanceof Error ? err.message : 'Upload failed');
      setImportProgress(null);
      setImporting(false);
    }
  }, [storeSandboxRoot, projectId, setEditorSession, startImport]);

  // ─── File input handler ───
  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return;

    // Try native path (Tauri/Electron)
    const folderPath = inferFolderPath(files);
    if (folderPath) {
      void startImport(folderPath);
      return;
    }

    // Browser mode: upload files then import
    void uploadAndImport(files);
  }, [startImport, uploadAndImport]);

  // ─── Build clip list from thumbnails + lanes ───
  const laneTypesByPath = new Map<string, Set<string>>();
  for (const lane of lanes) {
    for (const clip of lane.clips) {
      const types = laneTypesByPath.get(clip.source_path) ?? new Set();
      types.add(lane.lane_type);
      laneTypesByPath.set(clip.source_path, types);
    }
  }

  const mediaItems: ThumbnailItem[] = thumbnails.length
    ? thumbnails
    : lanes.flatMap((l) =>
        l.clips.map((c) => ({
          item_id: c.clip_id,
          source_path: c.source_path,
          poster_url: undefined,
          modality: 'video',
          duration_sec: c.duration_sec,
        }))
      );

  const allProjectItems = mediaItems.map((item) => classifyItem(item, laneTypesByPath));

  // MARKER_GAMMA-P1.4: Filter by search query
  const searchLower = searchQuery.toLowerCase();
  const projectItems = searchLower
    ? allProjectItems.filter((item) => basename(item.source_path).toLowerCase().includes(searchLower))
    : allProjectItems;

  // MARKER_GAMMA-P1.2: Sort for column view
  const toggleSort = useCallback((key: SortKey) => {
    if (sortKey === key) setSortDir((d) => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  }, [sortKey]);

  const sortedItems = [...projectItems].sort((a, b) => {
    const dir = sortDir === 'asc' ? 1 : -1;
    if (sortKey === 'name') return dir * basename(a.source_path).localeCompare(basename(b.source_path));
    if (sortKey === 'duration') return dir * ((a.duration_sec ?? 0) - (b.duration_sec ?? 0));
    if (sortKey === 'modality') return dir * (a.modality ?? '').localeCompare(b.modality ?? '');
    return 0;
  });

  const bins = BIN_ORDER
    .map((bin) => ({
      ...bin,
      items: projectItems.filter((it) => it.binKey === bin.key),
    }))
    .filter((b) => b.items.length > 0);

  // ─── Click on clip ───
  const handleClipClick = useCallback((clipSourcePath: string) => {
    setActiveMedia(clipSourcePath);
    for (const lane of lanes) {
      const clip = lane.clips.find((c) => c.source_path === clipSourcePath);
      if (clip) {
        setSelectedClip(clip.clip_id);
        return;
      }
    }
    setSelectedClip(null);
  }, [lanes, setActiveMedia, setSelectedClip]);

  const toggleBin = useCallback((key: string) => {
    setCollapsedBins((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const totalClips = allProjectItems.length;
  const filteredCount = projectItems.length;

  return (
    <div style={PANEL} data-testid="cut-source-browser">
      {/* Header with view mode switcher — MARKER_W5.4 */}
      <div style={HEADER}>
        <span>Project</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {(['list', 'columns', 'grid', 'dag'] as const).map((mode) => (
            <button
              key={mode}
              style={{
                ...MODE_SWITCH_BTN,
                color: viewMode === mode ? '#ccc' : '#555',
                background: viewMode === mode ? '#1a1a1a' : 'none',
              }}
              onClick={() => setViewMode(mode)}
              title={mode === 'list' ? 'List view' : mode === 'columns' ? 'Column view' : mode === 'grid' ? 'Grid view' : 'DAG view'}
            >
              {mode === 'list' ? '≡' : mode === 'columns' ? '▤' : mode === 'grid' ? '⊞' : '◇'}
            </button>
          ))}
          <span style={{ marginLeft: 6, fontSize: 9, color: '#555' }}>
            {searchLower ? `${filteredCount}/${totalClips}` : totalClips}
          </span>
        </div>
      </div>

      {/* MARKER_GAMMA-P1.4: Search/filter bar */}
      <div style={{ padding: '4px 10px', borderBottom: '1px solid #1a1a1a', flexShrink: 0 }}>
        <input
          type="text"
          placeholder="Filter clips..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            width: '100%',
            padding: '3px 6px',
            background: '#111',
            border: '1px solid #333',
            borderRadius: 3,
            color: '#ccc',
            fontSize: 9,
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
      </div>

      {/* Import area */}
      <div style={IMPORT_AREA}>
        {/* Dropzone — double-click opens file picker */}
        <div
          style={{
            ...DROPZONE,
            borderColor: dragging ? '#999' : '#2f2f2f',
            background: dragging ? '#0a0a0a' : 'transparent',
            color: dragging ? '#ccc' : '#555',
          }}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            handleFileSelect(e.dataTransfer.files);
          }}
          onDoubleClick={openFilePicker}
        >
          {importing
            ? `Importing... ${importProgress != null ? `${Math.round(importProgress * 100)}%` : ''}`
            : 'Double-click or press ⌘I to import media'}
        </div>

        {/* MARKER_W6.IMPORT-FIX: Hidden file picker — folder mode for NLE import */}
        <input
          ref={fileInputRef}
          type="file"
          // @ts-expect-error -- webkitdirectory is non-standard but widely supported
          webkitdirectory=""
          directory=""
          multiple
          accept={MEDIA_ACCEPT}
          style={{ display: 'none' }}
          onChange={(e) => {
            handleFileSelect(e.target.files);
            // Reset so re-selecting same files works
            e.target.value = '';
          }}
        />

        {/* Status */}
        {importStatus && (
          <div style={{
            ...STATUS_LINE,
            color: importStatus.toLowerCase().includes('fail') || importStatus.toLowerCase().includes('error')
              ? '#999'
              : '#777',
          }}>
            {importStatus}
          </div>
        )}
      </div>

      {/* Content area — switches by viewMode (MARKER_W5.4 + GAMMA-P1.2) */}
      {viewMode === 'columns' ? (
        /* MARKER_GAMMA-P1.2: Column view — sortable table */
        <div style={{ ...BIN_LIST, fontSize: 9 }}>
          {/* Column headers */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 60px 50px',
            padding: '3px 10px',
            borderBottom: '1px solid #333',
            color: '#777',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            userSelect: 'none',
          }}>
            <span style={{ cursor: 'pointer' }} onClick={() => toggleSort('name')}>
              Name {sortKey === 'name' ? (sortDir === 'asc' ? '\u25B4' : '\u25BE') : ''}
            </span>
            <span style={{ cursor: 'pointer', textAlign: 'right' }} onClick={() => toggleSort('duration')}>
              Duration {sortKey === 'duration' ? (sortDir === 'asc' ? '\u25B4' : '\u25BE') : ''}
            </span>
            <span style={{ cursor: 'pointer', textAlign: 'right' }} onClick={() => toggleSort('modality')}>
              Type {sortKey === 'modality' ? (sortDir === 'asc' ? '\u25B4' : '\u25BE') : ''}
            </span>
          </div>
          {/* Rows */}
          {sortedItems.map((item) => {
            const isActive = item.source_path === activeMediaPath;
            return (
              <div
                key={item.item_id}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData('text/cut-media-path', item.source_path);
                  e.dataTransfer.effectAllowed = 'copy';
                  setDragPreview(e, basename(item.source_path), item.modality, item.poster_url);
                }}
                onContextMenu={(e) => { e.preventDefault(); setCtxMenu({ x: e.clientX, y: e.clientY, path: item.source_path }); }}
                onClick={() => handleClipClick(item.source_path)}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 60px 50px',
                  padding: '3px 10px',
                  borderBottom: '1px solid #111',
                  background: isActive ? '#1a1a1a' : 'transparent',
                  cursor: 'grab',
                  color: isActive ? '#ccc' : '#888',
                }}
                onMouseEnter={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = '#111'; }}
                onMouseLeave={(e) => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {basename(item.source_path)}
                </span>
                <span style={{ textAlign: 'right', color: '#555', fontVariantNumeric: 'tabular-nums' }}>
                  {item.duration_sec ? `${Number(item.duration_sec).toFixed(1)}s` : '—'}
                </span>
                <span style={{ textAlign: 'right', color: '#444' }}>
                  {item.modality ?? '—'}
                </span>
              </div>
            );
          })}
          {totalClips === 0 && (
            <div style={{ padding: 24, color: '#333', textAlign: 'center', fontSize: 11 }}>No clips imported</div>
          )}
        </div>
      ) : viewMode === 'dag' ? (
        /* DAG view — embedded DAGProjectPanel */
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <DAGProjectPanel />
        </div>
      ) : viewMode === 'grid' ? (
        /* Grid view — thumbnail grid */
        <div style={{ ...BIN_LIST }}>
          <div style={GRID_CONTAINER}>
            {projectItems.map((item) => {
              const isActive = item.source_path === activeMediaPath;
              return (
                <div
                  key={item.item_id}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('text/cut-media-path', item.source_path);
                    e.dataTransfer.effectAllowed = 'copy';
                    setDragPreview(e, basename(item.source_path), item.modality, item.poster_url);
                    (e.currentTarget as HTMLElement).style.opacity = '0.5';
                  }}
                  onDragEnd={(e) => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
                  onContextMenu={(e) => { e.preventDefault(); setCtxMenu({ x: e.clientX, y: e.clientY, path: item.source_path }); }}
                  style={{
                    ...GRID_ITEM,
                    background: isActive ? '#1a1a1a' : 'transparent',
                    border: isActive ? '1px solid #999' : '1px solid transparent',
                    cursor: 'grab',
                  }}
                  onClick={() => handleClipClick(item.source_path)}
                >
                  {item.poster_url ? (
                    <img src={item.poster_url} style={GRID_THUMB} alt="" />
                  ) : (
                    <div style={{
                      ...GRID_THUMB,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 18,
                      color: '#333',
                    }}>
                      {item.modality === 'audio' ? '♪' : item.modality === 'image' ? '◻' : '▶'}
                    </div>
                  )}
                  <div style={{
                    fontSize: 8,
                    color: isActive ? '#fff' : '#777',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    width: '100%',
                    textAlign: 'center',
                    marginTop: 2,
                  }}>
                    {basename(item.source_path)}
                  </div>
                </div>
              );
            })}
          </div>
          {totalClips === 0 && (
            <div style={{ padding: 24, color: '#333', textAlign: 'center', fontSize: 11 }}>
              No clips imported
            </div>
          )}
        </div>
      ) : (
        /* List view (default) — bins with clip rows */
        <div style={BIN_LIST}>
          {bins.map((bin) => {
            const isCollapsed = collapsedBins.has(bin.key);
            return (
              <div key={bin.key} data-testid={`cut-source-bucket-${bin.key}`}>
                <div style={BIN_HEADER} onClick={() => toggleBin(bin.key)}>
                  <span>
                    {isCollapsed ? '▸' : '▾'} {bin.icon} {bin.label}
                  </span>
                  <span>{bin.items.length}</span>
                </div>
                {!isCollapsed && bin.items.map((item) => {
                  const isActive = item.source_path === activeMediaPath;
                  return (
                    <div
                      key={item.item_id}
                      data-testid={`cut-source-item-${item.item_id}`}
                      draggable
                      onDragStart={(e) => {
                        e.dataTransfer.setData('text/cut-media-path', item.source_path);
                        e.dataTransfer.effectAllowed = 'copy';
                        setDragPreview(e, basename(item.source_path), item.modality, item.poster_url);
                        (e.currentTarget as HTMLElement).style.opacity = '0.5';
                      }}
                      onDragEnd={(e) => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
                      onContextMenu={(e) => { e.preventDefault(); setCtxMenu({ x: e.clientX, y: e.clientY, path: item.source_path }); }}
                      style={{
                        ...CLIP_ITEM,
                        background: isActive ? '#1a1a1a' : 'transparent',
                        borderLeft: isActive ? '2px solid #999' : '2px solid transparent',
                        cursor: 'grab',
                      }}
                      onClick={() => handleClipClick(item.source_path)}
                    >
                      {item.poster_url ? (
                        <img src={item.poster_url} style={THUMB} alt="" />
                      ) : (
                        <div style={{
                          ...THUMB,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 14,
                          color: '#333',
                        }}>
                          {item.modality === 'audio' ? '♪' : item.modality === 'image' ? '◻' : '▶'}
                        </div>
                      )}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontSize: 11,
                          color: isActive ? '#fff' : '#aaa',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}>
                          {basename(item.source_path)}
                        </div>
                        <div style={{ display: 'flex', gap: 6, fontSize: 9, color: '#555' }}>
                          <span>
                            {item.duration_sec ? `${Number(item.duration_sec).toFixed(1)}s` : '—'}
                          </span>
                          {item.modality && (
                            <span style={{ color: '#444' }}>{item.modality}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}

          {totalClips === 0 && (
            <div style={{ padding: 24, color: '#333', textAlign: 'center', fontSize: 11 }}>
              No clips imported
              <br />
              <span style={{ fontSize: 10, color: '#444' }}>
                press above to import media
              </span>
            </div>
          )}
        </div>
      )}
      {/* MARKER_GAMMA-19: Project item context menu */}
      {ctxMenu && (
        <div
          style={{
            position: 'fixed', top: ctxMenu.y, left: ctxMenu.x,
            background: '#0b0b0b', border: '1px solid #333', borderRadius: 4,
            padding: '3px 0', zIndex: 10000, minWidth: 160,
            fontSize: 11, fontFamily: 'system-ui, -apple-system, sans-serif',
            color: '#ccc', boxShadow: '0 4px 12px rgba(0,0,0,0.6)',
          }}
          onMouseLeave={() => setCtxMenu(null)}
        >
          {[
            { label: 'Open in Source Monitor', action: () => { setActiveMedia(ctxMenu.path); setCtxMenu(null); } },
            { label: 'Add to Timeline', action: () => {
              window.dispatchEvent(new CustomEvent('cut:add-to-timeline', { detail: { path: ctxMenu.path } }));
              setCtxMenu(null);
            }},
            { separator: true },
            { label: 'Reveal in Finder', action: () => { setCtxMenu(null); }, disabled: true },
          ].map((item, i) =>
            'separator' in item ? (
              <div key={i} style={{ height: 1, background: '#222', margin: '3px 0' }} />
            ) : (
              <div
                key={i}
                onClick={item.disabled ? undefined : item.action}
                style={{
                  padding: '4px 12px', cursor: item.disabled ? 'default' : 'pointer',
                  color: item.disabled ? '#444' : '#ccc', whiteSpace: 'nowrap',
                }}
                onMouseEnter={(e) => { if (!item.disabled) (e.currentTarget as HTMLElement).style.background = '#1a1a1a'; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >
                {item.label}
              </div>
            ),
          )}
        </div>
      )}
    </div>
  );
}
