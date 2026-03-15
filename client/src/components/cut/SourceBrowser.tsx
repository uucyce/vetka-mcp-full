/**
 * MARKER_181.3: SourceBrowser — media import + asset list for CUT editor.
 *
 * Extracted from CutEditorLayout (V1) for use in CutEditorLayoutV2.
 * Provides:
 *   - Drag-and-drop import zone
 *   - Path input + Import button
 *   - Folder picker (Tauri native or webkitdirectory fallback)
 *   - Bucketed asset list (Video, Boards, Music, Audio, Stills)
 *   - Source sync badges from SyncSurface
 *
 * Reads from useCutEditorStore: sandboxRoot, projectId, thumbnails, lanes, syncSurface.
 * Calls POST /api/cut/bootstrap-async → polls job → refreshProjectState().
 */
import { useCallback, useEffect, useRef, useState, type CSSProperties, type DragEvent } from 'react';
import { API_BASE } from '../../config/api.config';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { usePanelSyncStore } from '../../store/usePanelSyncStore';

// ─── Helpers ───

function basename(path: string): string {
  return path.split('/').pop()?.split('\\').pop() || path;
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function labelForImportPath(sourcePath: string): string {
  if (/^https?:\/\//i.test(sourcePath)) return sourcePath;
  return basename(sourcePath);
}

function inferFolderPath(files: FileList | File[] | null | undefined): string {
  const firstFile = files?.[0] as (File & { path?: string; webkitRelativePath?: string }) | undefined;
  if (!firstFile) return '';
  if (typeof firstFile.path === 'string' && firstFile.path) {
    const relative = String(firstFile.webkitRelativePath || '');
    if (!relative) return firstFile.path.replace(/[\\/][^\\/]+$/, '');
    const segments = relative.split('/').filter(Boolean);
    const depth = Math.max(1, segments.length);
    const absoluteSegments = firstFile.path.split(/[\\/]/).filter(Boolean);
    const prefix = absoluteSegments.slice(0, Math.max(0, absoluteSegments.length - depth));
    return `${firstFile.path.startsWith('/') ? '/' : ''}${prefix.join('/')}`;
  }
  return '';
}

// ─── Types ───

type SourceBucketKey = 'video' | 'boards' | 'music_track' | 'audio' | 'stills';

const SOURCE_BUCKET_ORDER: Array<{ key: SourceBucketKey; label: string }> = [
  { key: 'video', label: 'Video Clips' },
  { key: 'boards', label: 'Boards' },
  { key: 'music_track', label: 'Music Track' },
  { key: 'audio', label: 'Audio Assets' },
  { key: 'stills', label: 'Still Images' },
];

type SourceBrowserItem = {
  item_id: string;
  source_path: string;
  poster_url?: string;
  modality?: string;
  duration_sec?: number;
  bucketKey: SourceBucketKey;
  bucketLabel: string;
  badges: string[];
};

// ─── Styles (§11 compliant: monochrome, minimal accent) ───

const ROOT: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  background: '#0D0D0D',
  overflow: 'hidden',
};

const IMPORT_PANEL: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  padding: 8,
  borderBottom: '1px solid #1a1a1a',
  background: '#080808',
};

const IMPORT_DROPZONE: CSSProperties = {
  padding: '10px 8px',
  borderRadius: 6,
  border: '1px dashed #2f2f2f',
  color: '#8b8b8b',
  fontSize: 10,
  textAlign: 'center',
};

const IMPORT_ROW: CSSProperties = {
  display: 'flex',
  gap: 6,
  alignItems: 'center',
};

const IMPORT_INPUT: CSSProperties = {
  width: '100%',
  background: '#030303',
  border: '1px solid #1f1f1f',
  borderRadius: 4,
  color: '#d1d5db',
  fontSize: 11,
  padding: '6px 8px',
};

const IMPORT_BUTTON: CSSProperties = {
  border: '1px solid #2f2f2f',
  borderRadius: 4,
  background: '#101010',
  color: '#d1d5db',
  fontSize: 10,
  padding: '6px 8px',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
};

const SOURCE_LIST: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: 4,
};

const SOURCE_BUCKET_STYLE: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  marginBottom: 10,
};

const SOURCE_BUCKET_HEADER: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '6px 8px 2px',
  fontSize: 9,
  color: '#6b7280',
  letterSpacing: 0.8,
  textTransform: 'uppercase',
};

const SOURCE_ITEM: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '6px 8px',
  borderRadius: 3,
  cursor: 'pointer',
  fontSize: 11,
  transition: 'background 0.1s',
};

const THUMB_STYLE: CSSProperties = {
  width: 48,
  height: 32,
  borderRadius: 2,
  objectFit: 'cover',
  background: '#111',
  flexShrink: 0,
};

const SOURCE_META_ROW: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: 4,
  marginTop: 2,
};

const SOURCE_BADGE: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '1px 5px',
  borderRadius: 999,
  border: '1px solid #333',
  background: '#1a1a1a',
  color: '#999',
  fontSize: 8,
  lineHeight: '14px',
};

// ─── Component (MARKER_181.3) ───

export default function SourceBrowser() {
  const storeSandboxRoot = useCutEditorStore((s) => s.sandboxRoot);
  const projectId = useCutEditorStore((s) => s.projectId);
  const refreshProjectState = useCutEditorStore((s) => s.refreshProjectState);
  const setEditorSession = useCutEditorStore((s) => s.setEditorSession);
  const thumbnails = useCutEditorStore((s) => s.thumbnails);
  const lanes = useCutEditorStore((s) => s.lanes);
  const syncSurface = useCutEditorStore((s) => s.syncSurface);
  const activeMediaPath = useCutEditorStore((s) => s.activeMediaPath);
  const setActiveMedia = useCutEditorStore((s) => s.setActiveMedia);
  const setSelectedClip = useCutEditorStore((s) => s.setSelectedClip);
  const syncFromDAG = usePanelSyncStore((s) => s.syncFromDAG);

  const [importSourcePath, setImportSourcePath] = useState('');
  const [importStatus, setImportStatus] = useState('');
  const [importProgress, setImportProgress] = useState<number | null>(null);
  const [importing, setImporting] = useState(false);
  const [draggingImport, setDraggingImport] = useState(false);
  const folderInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const input = folderInputRef.current as (HTMLInputElement & { webkitdirectory?: boolean }) | null;
    if (input) input.webkitdirectory = true;
  }, []);

  // ─── Pre-fill from URL source_path if store has it ───
  const urlSourcePath = useCutEditorStore((s) => s.sourcePath);
  useEffect(() => {
    if (urlSourcePath && !importSourcePath) {
      setImportSourcePath(urlSourcePath);
    }
  }, [urlSourcePath]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Poll job helper ───
  const pollJob = useCallback(async (jobId: string) => {
    for (let attempt = 0; attempt < 80; attempt += 1) {
      const response = await fetch(`${API_BASE}/cut/job/${encodeURIComponent(jobId)}`);
      if (!response.ok) throw new Error(`Import job failed: HTTP ${response.status}`);
      const payload = (await response.json()) as {
        job?: { state?: string; progress?: number; error?: { message?: string } | null };
      };
      const state = String(payload.job?.state || '');
      setImportProgress(typeof payload.job?.progress === 'number' ? Number(payload.job.progress) : null);
      if (state === 'done') return;
      if (state === 'error') throw new Error(payload.job?.error?.message || 'Media import failed');
      await new Promise((resolve) => window.setTimeout(resolve, 250));
    }
    throw new Error('Media import timed out');
  }, []);

  // ─── Bootstrap import ───
  const startMediaImport = useCallback(
    async (sourcePath: string) => {
      const trimmedSource = String(sourcePath || '').trim();
      if (!trimmedSource) {
        setImportStatus('Absolute source path is required for bootstrap import.');
        return;
      }
      // MARKER_181.3: Auto-derive sandbox from source path if not configured
      let sandboxRoot = storeSandboxRoot;
      if (!sandboxRoot) {
        sandboxRoot = `${trimmedSource}/cut_sandbox`;
        setEditorSession({ sandboxRoot });
      }
      setImporting(true);
      setImportProgress(0);
      setImportStatus(`Bootstrapping ${labelForImportPath(trimmedSource)}...`);
      try {
        const response = await fetch(`${API_BASE}/cut/bootstrap-async`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_path: trimmedSource,
            sandbox_root: sandboxRoot,
            project_name: projectId || labelForImportPath(trimmedSource),
            mode: 'create_or_open',
            use_core_mirror: true,
            create_project_if_missing: true,
          }),
        });
        if (!response.ok) throw new Error(`Bootstrap failed: HTTP ${response.status}`);
        const payload = (await response.json()) as {
          success?: boolean;
          job_id?: string;
          error?: { message?: string } | null;
        };
        if (!payload.success || !payload.job_id) {
          throw new Error(payload.error?.message || 'Bootstrap job did not start');
        }
        await pollJob(payload.job_id);
        await refreshProjectState?.();
        setImportStatus(`Imported ${labelForImportPath(trimmedSource)} into Source Browser.`);
        setImportProgress(1);
      } catch (error) {
        setImportStatus(error instanceof Error ? error.message : 'Media import failed');
        setImportProgress(null);
      } finally {
        setImporting(false);
      }
    },
    [pollJob, projectId, refreshProjectState, storeSandboxRoot, setEditorSession],
  );

  // ─── Drag and drop ───
  const handleImportDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setDraggingImport(false);
      const path = inferFolderPath(Array.from(event.dataTransfer.files || []));
      if (!path) {
        setImportStatus('Drop provided browser File objects without native path. Paste an absolute path or use desktop folder picker.');
        return;
      }
      setImportSourcePath(path);
      void startMediaImport(path);
    },
    [startMediaImport],
  );

  // ─── Source click → sync panels ───
  const handleSourceClick = useCallback(
    (sourcePath: string, itemId: string) => {
      setActiveMedia(sourcePath);
      setSelectedClip(itemId);
      syncFromDAG(itemId, sourcePath);
    },
    [setActiveMedia, setSelectedClip, syncFromDAG],
  );

  // ─── Build source items from thumbnails/lanes ───
  const mediaItems = thumbnails.length
    ? thumbnails
    : lanes.flatMap((l) =>
        l.clips.map((c) => ({
          item_id: c.clip_id,
          source_path: c.source_path,
          poster_url: undefined as string | undefined,
          modality: 'video' as string,
          duration_sec: c.duration_sec,
        })),
      );

  const laneTypesBySourcePath = new Map<string, Set<string>>();
  for (const lane of lanes) {
    for (const clip of lane.clips) {
      const laneTypes = laneTypesBySourcePath.get(clip.source_path) ?? new Set<string>();
      laneTypes.add(lane.lane_type);
      laneTypesBySourcePath.set(clip.source_path, laneTypes);
    }
  }

  const sourceItems: SourceBrowserItem[] = mediaItems.map((item) => {
    const sourcePathLower = item.source_path.toLowerCase();
    const laneTypes = laneTypesBySourcePath.get(item.source_path) ?? new Set<string>();
    const isBoard = sourcePathLower.includes('/boards/') || sourcePathLower.includes('\\boards\\');
    const isMusicTrack = (item.modality === 'audio' || laneTypes.has('audio_sync')) && laneTypes.has('audio_sync');

    let bucketKey: SourceBucketKey = 'video';
    let bucketLabel = 'Video Clips';
    if (isMusicTrack) {
      bucketKey = 'music_track';
      bucketLabel = 'Music Track';
    } else if (isBoard) {
      bucketKey = 'boards';
      bucketLabel = 'Boards';
    } else if (item.modality === 'audio') {
      bucketKey = 'audio';
      bucketLabel = 'Audio Assets';
    } else if (item.modality === 'image') {
      bucketKey = 'stills';
      bucketLabel = 'Still Images';
    }

    const badges: string[] = [];
    if (isMusicTrack) badges.push('Primary music');
    else if (item.modality === 'audio') badges.push('Audio asset');
    if (laneTypes.has('audio_sync')) badges.push('Audio sync lane');
    if (isBoard) badges.push('Board still');
    else if (item.modality === 'video') badges.push('Camera clip');

    return { ...item, bucketKey, bucketLabel, badges };
  });

  const sourceBuckets = SOURCE_BUCKET_ORDER.map((bucket) => ({
    ...bucket,
    items: sourceItems.filter((item) => item.bucketKey === bucket.key),
  })).filter((bucket) => bucket.items.length > 0);

  return (
    <div style={ROOT}>
      {/* Import panel */}
      <div style={IMPORT_PANEL}>
        <span style={{ float: 'right', color: '#333', fontSize: 9 }}>{sourceItems.length} assets</span>

        <div
          style={{
            ...IMPORT_DROPZONE,
            borderColor: draggingImport ? '#4a9eff' : '#2f2f2f',
            color: draggingImport ? '#bfdbfe' : IMPORT_DROPZONE.color,
            background: draggingImport ? '#081120' : 'transparent',
          }}
          onDragOver={(event) => { event.preventDefault(); setDraggingImport(true); }}
          onDragLeave={() => setDraggingImport(false)}
          onDrop={handleImportDrop}
        >
          Drag media folder here or use path import
        </div>

        <div style={IMPORT_ROW}>
          <input
            data-testid="cut-media-import-path"
            style={IMPORT_INPUT}
            placeholder="/absolute/path/to/media"
            value={importSourcePath}
            onChange={(event) => setImportSourcePath(event.target.value)}
          />
          <button
            type="button"
            data-testid="cut-media-import-trigger"
            style={{ ...IMPORT_BUTTON, opacity: importing ? 0.6 : 1 }}
            disabled={importing || !importSourcePath.trim()}
            onClick={() => void startMediaImport(importSourcePath)}
          >
            Import
          </button>
        </div>

        <div style={IMPORT_ROW}>
          <button
            type="button"
            data-testid="cut-media-folder-picker"
            style={IMPORT_BUTTON}
            disabled={importing}
            onClick={() => folderInputRef.current?.click()}
          >
            Folder Picker
          </button>
          <input
            ref={folderInputRef}
            type="file"
            multiple
            style={{ display: 'none' }}
            onChange={(event) => {
              const path = inferFolderPath(event.target.files);
              if (!path) {
                setImportStatus('Folder picker did not expose a native path. Paste an absolute path instead.');
                return;
              }
              setImportSourcePath(path);
              void startMediaImport(path);
            }}
          />
          <span style={{ fontSize: 9, color: '#555' }}>
            sandbox {storeSandboxRoot ? 'ready' : 'auto'}
          </span>
        </div>

        <div data-testid="cut-media-import-status" style={{ fontSize: 10, color: importStatus ? '#93c5fd' : '#555' }}>
          {importStatus || 'Import media to load assets.'}
          {importProgress != null ? ` ${Math.round(importProgress * 100)}%` : ''}
        </div>
      </div>

      {/* Asset list */}
      <div style={SOURCE_LIST}>
        {sourceBuckets.map((bucket) => (
          <div key={bucket.key} data-testid={`cut-source-bucket-${bucket.key}`} style={SOURCE_BUCKET_STYLE}>
            <div style={SOURCE_BUCKET_HEADER}>
              <span>{bucket.label}</span>
              <span>{bucket.items.length}</span>
            </div>
            {bucket.items.map((item) => {
              const isActive = item.source_path === activeMediaPath;
              const syncItem = syncSurface.find((s) => s.source_path === item.source_path);
              return (
                <div
                  key={item.item_id}
                  data-testid={`cut-source-item-${item.item_id}`}
                  style={{
                    ...SOURCE_ITEM,
                    background: isActive ? '#1a1a2a' : 'transparent',
                    borderLeft: isActive ? '2px solid #4a9eff' : '2px solid transparent',
                  }}
                  onClick={() => handleSourceClick(item.source_path, item.item_id)}
                >
                  {item.poster_url ? (
                    <img src={item.poster_url} style={THUMB_STYLE} alt="" />
                  ) : (
                    <div
                      style={{
                        ...THUMB_STYLE,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 16,
                        color: '#333',
                      }}
                    >
                      {item.modality === 'audio' ? 'A' : 'V'}
                    </div>
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 11,
                        color: isActive ? '#fff' : '#aaa',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {basename(item.source_path)}
                    </div>
                    <div style={SOURCE_META_ROW}>
                      <span style={{ fontSize: 9, color: '#555' }}>
                        {item.duration_sec ? `${Number(item.duration_sec).toFixed(1)}s` : '\u2014'}
                      </span>
                      {item.badges.map((badge) => (
                        <span key={badge} data-testid={`cut-source-item-badge-${item.item_id}-${slugify(badge)}`} style={SOURCE_BADGE}>
                          {badge}
                        </span>
                      ))}
                      {syncItem?.recommended_method ? (
                        <span style={{ ...SOURCE_BADGE, color: '#aaa', borderColor: '#444' }}>
                          Sync {syncItem.recommended_method}
                        </span>
                      ) : null}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ))}

        {!sourceItems.length && (
          <div style={{ padding: 20, color: '#333', textAlign: 'center', fontSize: 11 }}>
            No media loaded
            <br />
            Import a folder to see assets
          </div>
        )}
      </div>
    </div>
  );
}
