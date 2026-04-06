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
import { useSelectionStore } from '../../store/useSelectionStore';
import { API_BASE } from '../../config/api.config';
import { isTauri, openFileDialog, openFolderDialog } from '../../config/tauri';
import DAGProjectPanel from './DAGProjectPanel';
import { setDragPreview } from './utils/dragPreview';

// MARKER_W5.4 + GAMMA-P1.2: View mode type
type ProjectViewMode = 'list' | 'columns' | 'grid' | 'dag';

// ─── Bin (bucket) types ───

type BinKey = 'video' | 'audio' | 'music_track' | 'stills' | 'boards' | 'documents' | 'other' | string;

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

// MARKER_GAMMA-14: setDragPreview extracted to ./utils/dragPreview.ts (Gamma-8 refactor)

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
  const setSelectedClip = useSelectionStore((s) => s.setSelectedClip);

  // Local state
  const [importStatus, setImportStatus] = useState('');
  const [importProgress, setImportProgress] = useState<number | null>(null);
  const [importing, setImporting] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [collapsedBins, setCollapsedBins] = useState<Set<string>>(new Set());
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);
  // MARKER_W5.4: View mode
  const [viewMode, setViewMode] = useState<ProjectViewMode>('list');
  // MARKER_GAMMA-19: Context menu for project items
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; path: string } | null>(null);
  // MARKER_GAMMA-P1.4: Search/filter clips
  const [searchQuery, setSearchQuery] = useState('');
  // MARKER_GAMMA-MB1: Thumbnail size slider for grid view (48-160px)
  const [thumbSize, setThumbSize] = useState(80);
  // MARKER_GAMMA-P1.1: User-created bins
  type UserBin = { id: string; name: string };
  const [userBins, setUserBins] = useState<UserBin[]>(() => {
    try { const raw = localStorage.getItem('cut_user_bins'); return raw ? JSON.parse(raw) : []; } catch { return []; }
  });
  const [clipBinMap, setClipBinMap] = useState<Record<string, string>>(() => {
    try { const raw = localStorage.getItem('cut_clip_bins'); return raw ? JSON.parse(raw) : {}; } catch { return {}; }
  });
  const [renamingBin, setRenamingBin] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  // MARKER_GAMMA-R4.2: Multi-select state
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  // MARKER_GAMMA-R4.5: Shift+click range select anchor
  const lastClickedPathRef = useRef<string | null>(null);

  const saveUserBins = useCallback((bins: UserBin[]) => {
    setUserBins(bins);
    try { localStorage.setItem('cut_user_bins', JSON.stringify(bins)); } catch { /* ok */ }
  }, []);
  const saveClipBinMap = useCallback((map: Record<string, string>) => {
    setClipBinMap(map);
    try { localStorage.setItem('cut_clip_bins', JSON.stringify(map)); } catch { /* ok */ }
  }, []);

  const createBin = useCallback(() => {
    const id = `bin_${Date.now()}`;
    const name = `Bin ${userBins.length + 1}`;
    saveUserBins([...userBins, { id, name }]);
    setRenamingBin(id);
    setRenameValue(name);
  }, [userBins, saveUserBins]);

  const renameBin = useCallback((id: string, name: string) => {
    saveUserBins(userBins.map((b) => b.id === id ? { ...b, name } : b));
    setRenamingBin(null);
  }, [userBins, saveUserBins]);

  const deleteBin = useCallback((id: string) => {
    saveUserBins(userBins.filter((b) => b.id !== id));
    const next = { ...clipBinMap };
    for (const key of Object.keys(next)) { if (next[key] === id) delete next[key]; }
    saveClipBinMap(next);
  }, [userBins, clipBinMap, saveUserBins, saveClipBinMap]);

  const assignClipToBin = useCallback((clipPath: string, binId: string) => {
    saveClipBinMap({ ...clipBinMap, [clipPath]: binId });
  }, [clipBinMap, saveClipBinMap]);
  // MARKER_GAMMA-P1.2: Column sort
  type SortKey = 'name' | 'duration' | 'modality';
  type SortDir = 'asc' | 'desc';
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  // ─── Open file picker (MARKER_IMPORT-DIALOG-FIX) ───
  // In Tauri: use native openFileDialog with proper media filters (directory=false).
  // In browser: fall back to HTML <input type="file"> (no webkitdirectory).
  // MARKER_IMPORT-P0-FIX: openFilePicker with robust path handling + debug logging
  const openFilePicker = useCallback(async () => {
    if (importing) return;
    if (isTauri()) {
      console.log('[CUT Import] Opening native file dialog via Tauri...');
      const result = await openFileDialog({ title: 'Import Media Files', multiple: true });
      console.log('[CUT Import] Dialog result:', result);
      if (!result) {
        console.log('[CUT Import] Dialog cancelled or returned null');
        return;
      }
      const paths = Array.isArray(result) ? result : [result];
      if (paths.length > 0) {
        // Derive common parent folder for backend bootstrap scan
        const firstDir = paths[0].replace(/[\\/][^\\/]+$/, '');
        console.log(`[CUT Import] Selected ${paths.length} file(s), importing from: ${firstDir}`);
        void startImport(firstDir);
      }
    } else {
      fileInputRef.current?.click();
    }
  }, [importing, startImport]);

  // ─── Open folder picker (import folder as bin) ───
  const openFolderPicker = useCallback(async () => {
    if (importing) return;
    if (isTauri()) {
      const folder = await openFolderDialog('Import Media Folder');
      if (folder) void startImport(folder);
    } else {
      folderInputRef.current?.click();
    }
  }, [importing, startImport]);

  // ─── Listen for Cmd+I hotkey (from CutEditorLayoutV2 importMedia handler) ───
  useEffect(() => {
    const fileHandler = () => { void openFilePicker(); };
    const folderHandler = () => { void openFolderPicker(); };
    // MARKER_IMPORT-DIALOG-FIX: file import = default Cmd+I, folder import = separate event
    window.addEventListener('cut:import-media', fileHandler);
    window.addEventListener('cut:trigger-import', fileHandler);
    window.addEventListener('cut:import-folder', folderHandler);
    return () => {
      window.removeEventListener('cut:import-media', fileHandler);
      window.removeEventListener('cut:trigger-import', fileHandler);
      window.removeEventListener('cut:import-folder', folderHandler);
    };
  }, [openFilePicker, openFolderPicker]);

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
    // MARKER_IMPORT-P0-FIX: If source_path is a file, derive sandbox from its parent dir
    let sandboxRoot = storeSandboxRoot;
    if (!sandboxRoot) {
      const hasExt = /\.[a-zA-Z0-9]{2,5}$/.test(trimmed);
      const baseDir = hasExt ? trimmed.replace(/[\\/][^\\/]+$/, '') : trimmed;
      sandboxRoot = `${baseDir}/cut_sandbox`;
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
  // MARKER_GAMMA-R4.2 + R4.5: Multi-select with Cmd/Ctrl+click, Shift+click range
  const handleClipClick = useCallback((clipSourcePath: string, e?: React.MouseEvent) => {
    if (e && e.shiftKey && lastClickedPathRef.current) {
      // MARKER_GAMMA-R4.5: Shift+click range select
      // Build flat ordered list of all visible items for range calculation
      const allPaths = sortedItems.map((it) => it.source_path);
      const anchorIdx = allPaths.indexOf(lastClickedPathRef.current);
      const targetIdx = allPaths.indexOf(clipSourcePath);
      if (anchorIdx !== -1 && targetIdx !== -1) {
        const lo = Math.min(anchorIdx, targetIdx);
        const hi = Math.max(anchorIdx, targetIdx);
        const rangePaths = allPaths.slice(lo, hi + 1);
        setSelectedPaths((prev) => {
          const next = new Set(prev);
          for (const p of rangePaths) next.add(p);
          return next;
        });
      } else {
        setSelectedPaths(new Set([clipSourcePath]));
      }
      // Don't update lastClickedPathRef — anchor stays for extending range
    } else if (e && (e.metaKey || e.ctrlKey)) {
      // Toggle in multi-selection
      setSelectedPaths((prev) => {
        const next = new Set(prev);
        if (next.has(clipSourcePath)) next.delete(clipSourcePath);
        else next.add(clipSourcePath);
        return next;
      });
      lastClickedPathRef.current = clipSourcePath;
    } else {
      // Single select — clear multi-selection
      setSelectedPaths(new Set([clipSourcePath]));
      lastClickedPathRef.current = clipSourcePath;
    }
    setActiveMedia(clipSourcePath);
    for (const lane of lanes) {
      const clip = lane.clips.find((c) => c.source_path === clipSourcePath);
      if (clip) {
        setSelectedClip(clip.clip_id);
        return;
      }
    }
    setSelectedClip(null);
  }, [lanes, setActiveMedia, setSelectedClip, sortedItems]);

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
      {/* Header with view mode switcher — MARKER_W5.4 + GAMMA-P1.1 New Bin */}
      <div style={HEADER}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span>Project</span>
          <button
            onClick={createBin}
            style={{ ...MODE_SWITCH_BTN, color: '#555', fontSize: 10 }}
            title="New Bin (⌘B)"
          >+</button>
        </div>
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

      {/* MARKER_GAMMA-MB1: Thumbnail size slider (grid mode only) */}
      {viewMode === 'grid' && (
        <div style={{ padding: '2px 10px', borderBottom: '1px solid #1a1a1a', display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          <span style={{ fontSize: 8, color: '#555' }}>Size</span>
          <input
            type="range"
            min={48}
            max={160}
            step={8}
            value={thumbSize}
            onChange={(e) => setThumbSize(parseInt(e.target.value))}
            style={{ flex: 1, height: 3, appearance: 'none', background: '#333', borderRadius: 2, outline: 'none', cursor: 'pointer' }}
          />
          <span style={{ fontSize: 8, color: '#555', fontVariantNumeric: 'tabular-nums', width: 24, textAlign: 'right' }}>{thumbSize}</span>
        </div>
      )}

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

        {/* MARKER_IMPORT-DIALOG-FIX: Hidden file picker — individual media files (NO webkitdirectory) */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={MEDIA_ACCEPT}
          style={{ display: 'none' }}
          onChange={(e) => {
            handleFileSelect(e.target.files);
            e.target.value = '';
          }}
        />
        {/* MARKER_IMPORT-DIALOG-FIX: Hidden folder picker — folder import as bin */}
        <input
          ref={folderInputRef}
          type="file"
          // @ts-expect-error -- webkitdirectory is non-standard but widely supported
          webkitdirectory=""
          directory=""
          multiple
          style={{ display: 'none' }}
          onChange={(e) => {
            handleFileSelect(e.target.files);
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
                  const isMulti = selectedPaths.has(item.source_path) && selectedPaths.size > 1;
                  const paths = isMulti ? [...selectedPaths] : [item.source_path];
                  e.dataTransfer.setData('text/cut-media-path', paths[0]);
                  e.dataTransfer.setData('text/cut-media-paths', JSON.stringify(paths));
                  e.dataTransfer.effectAllowed = 'copy';
                  setDragPreview(e, basename(item.source_path), item.modality, item.poster_url, item.duration_sec, paths.length);
                }}
                onContextMenu={(e) => { e.preventDefault(); setCtxMenu({ x: e.clientX, y: e.clientY, path: item.source_path }); }}
                onClick={(e) => handleClipClick(item.source_path, e)}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 60px 50px',
                  padding: '3px 10px',
                  borderBottom: '1px solid #111',
                  background: (isActive || selectedPaths.has(item.source_path)) ? '#1a1a1a' : 'transparent',
                  cursor: 'grab',
                  color: (isActive || selectedPaths.has(item.source_path)) ? '#ccc' : '#888',
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
          <div style={{ ...GRID_CONTAINER, gridTemplateColumns: `repeat(auto-fill, minmax(${thumbSize}px, 1fr))` }}>
            {projectItems.map((item) => {
              const isActive = item.source_path === activeMediaPath;
              return (
                <div
                  key={item.item_id}
                  draggable
                  onDragStart={(e) => {
                    const isMulti = selectedPaths.has(item.source_path) && selectedPaths.size > 1;
                    const paths = isMulti ? [...selectedPaths] : [item.source_path];
                    e.dataTransfer.setData('text/cut-media-path', paths[0]);
                    e.dataTransfer.setData('text/cut-media-paths', JSON.stringify(paths));
                    e.dataTransfer.effectAllowed = 'copy';
                    setDragPreview(e, basename(item.source_path), item.modality, item.poster_url, item.duration_sec, paths.length);
                    (e.currentTarget as HTMLElement).style.opacity = '0.5';
                  }}
                  onDragEnd={(e) => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
                  onContextMenu={(e) => { e.preventDefault(); setCtxMenu({ x: e.clientX, y: e.clientY, path: item.source_path }); }}
                  style={{
                    ...GRID_ITEM,
                    background: (isActive || selectedPaths.has(item.source_path)) ? '#1a1a1a' : 'transparent',
                    border: (isActive || selectedPaths.has(item.source_path)) ? '1px solid #999' : '1px solid transparent',
                    cursor: 'grab',
                  }}
                  onClick={(e) => handleClipClick(item.source_path, e)}
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
        /* List view (default) — user bins + auto bins with clip rows */
        <div style={BIN_LIST}>
          {/* MARKER_GAMMA-P1.1: User-created bins */}
          {userBins.map((ubin) => {
            const isCollapsed = collapsedBins.has(ubin.id);
            const ubinItems = projectItems.filter((it) => clipBinMap[it.source_path] === ubin.id);
            return (
              <div key={ubin.id} data-testid={`cut-user-bin-${ubin.id}`}>
                <div
                  style={BIN_HEADER}
                  onClick={() => toggleBin(ubin.id)}
                  onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }}
                  onDrop={(e) => {
                    e.preventDefault();
                    const path = e.dataTransfer.getData('text/cut-media-path');
                    if (path) assignClipToBin(path, ubin.id);
                  }}
                  onContextMenu={(e) => {
                    e.preventDefault();
                    if (confirm(`Delete bin "${ubin.name}"?`)) deleteBin(ubin.id);
                  }}
                >
                  <span>
                    {isCollapsed ? '▸' : '▾'}{' '}
                    {renamingBin === ubin.id ? (
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={() => renameBin(ubin.id, renameValue)}
                        onKeyDown={(e) => { if (e.key === 'Enter') renameBin(ubin.id, renameValue); if (e.key === 'Escape') setRenamingBin(null); }}
                        onClick={(e) => e.stopPropagation()}
                        style={{ background: '#111', border: '1px solid #555', borderRadius: 2, color: '#ccc', fontSize: 10, width: 100, padding: '0 3px', outline: 'none' }}
                      />
                    ) : (
                      <span onDoubleClick={(e) => { e.stopPropagation(); setRenamingBin(ubin.id); setRenameValue(ubin.name); }}>
                        {ubin.name}
                      </span>
                    )}
                  </span>
                  <span>{ubinItems.length}</span>
                </div>
                {!isCollapsed && ubinItems.map((item) => {
                  const isActive = item.source_path === activeMediaPath;
                  return (
                    <div
                      key={item.item_id}
                      draggable
                      onDragStart={(e) => {
                        const isMulti = selectedPaths.has(item.source_path) && selectedPaths.size > 1;
                        const paths = isMulti ? [...selectedPaths] : [item.source_path];
                        e.dataTransfer.setData('text/cut-media-path', paths[0]);
                        e.dataTransfer.setData('text/cut-media-paths', JSON.stringify(paths));
                        e.dataTransfer.effectAllowed = 'copyMove';
                        setDragPreview(e, basename(item.source_path), item.modality, item.poster_url, item.duration_sec, paths.length);
                      }}
                      style={{
                        ...CLIP_ITEM,
                        background: (isActive || selectedPaths.has(item.source_path)) ? '#1a1a1a' : 'transparent',
                        borderLeft: (isActive || selectedPaths.has(item.source_path)) ? '2px solid #999' : '2px solid transparent',
                        cursor: 'grab',
                      }}
                      onClick={(e) => handleClipClick(item.source_path, e)}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 11, color: isActive ? '#fff' : '#aaa', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {basename(item.source_path)}
                        </div>
                        <div style={{ fontSize: 9, color: '#555' }}>
                          {item.duration_sec ? `${Number(item.duration_sec).toFixed(1)}s` : '—'}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
          {/* Auto-classified bins */}
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
                        const isMulti = selectedPaths.has(item.source_path) && selectedPaths.size > 1;
                        const paths = isMulti ? [...selectedPaths] : [item.source_path];
                        e.dataTransfer.setData('text/cut-media-path', paths[0]);
                        e.dataTransfer.setData('text/cut-media-paths', JSON.stringify(paths));
                        e.dataTransfer.effectAllowed = 'copy';
                        setDragPreview(e, basename(item.source_path), item.modality, item.poster_url, item.duration_sec, paths.length);
                        (e.currentTarget as HTMLElement).style.opacity = '0.5';
                      }}
                      onDragEnd={(e) => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
                      onContextMenu={(e) => { e.preventDefault(); setCtxMenu({ x: e.clientX, y: e.clientY, path: item.source_path }); }}
                      style={{
                        ...CLIP_ITEM,
                        background: (isActive || selectedPaths.has(item.source_path)) ? '#1a1a1a' : 'transparent',
                        borderLeft: (isActive || selectedPaths.has(item.source_path)) ? '2px solid #999' : '2px solid transparent',
                        cursor: 'grab',
                      }}
                      onClick={(e) => handleClipClick(item.source_path, e)}
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
            { label: 'Reveal in Finder', action: () => {
              fetch(`${API_BASE}/files/open-in-finder`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: ctxMenu.path }),
              }).catch(() => {});
              setCtxMenu(null);
            }},
          ].map((item: { label?: string; action?: () => void; separator?: boolean; disabled?: boolean }, i) =>
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
