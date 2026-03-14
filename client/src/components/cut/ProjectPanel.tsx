/**
 * MARKER_181.3: ProjectPanel — Premiere-style Project panel (media bin + import).
 *
 * Architecture: Standard NLE layout places the Project panel at bottom-left.
 * This panel manages imported media assets, organized by bins (buckets).
 *
 * Import methods (matching Premiere Pro):
 * 1. Drag & drop files/folders into the panel
 * 2. Paste an absolute path + click Import
 * 3. Double-click empty area to trigger import
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
  padding: '10px 12px',
  textAlign: 'center',
  fontSize: 10,
  color: '#555',
  cursor: 'pointer',
  transition: 'border-color 0.2s, background 0.2s',
  marginBottom: 6,
};

const INPUT_ROW: CSSProperties = {
  display: 'flex',
  gap: 4,
  alignItems: 'center',
};

const PATH_INPUT: CSSProperties = {
  flex: 1,
  background: '#111',
  border: '1px solid #222',
  borderRadius: 3,
  color: '#ccc',
  fontSize: 10,
  padding: '4px 6px',
  outline: 'none',
  fontFamily: '"JetBrains Mono", monospace',
};

const IMPORT_BTN: CSSProperties = {
  background: '#1A1A1A',
  border: '1px solid #333',
  borderRadius: 3,
  color: '#aaa',
  fontSize: 10,
  padding: '4px 10px',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
};

const STATUS_LINE: CSSProperties = {
  fontSize: 9,
  color: '#555',
  marginTop: 4,
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

// ─── Helpers ───

function basename(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

function labelForPath(path: string): string {
  const parts = path.split(/[\\/]/).filter(Boolean);
  return parts.length > 0 ? parts[parts.length - 1] : 'project';
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
  const sourcePath = useCutEditorStore((s) => s.sourcePath);
  const refreshProjectState = useCutEditorStore((s) => s.refreshProjectState);
  const setEditorSession = useCutEditorStore((s) => s.setEditorSession);
  const thumbnails = useCutEditorStore((s) => s.thumbnails);
  const lanes = useCutEditorStore((s) => s.lanes);
  const activeMediaPath = useCutEditorStore((s) => s.activeMediaPath);
  const setActiveMedia = useCutEditorStore((s) => s.setActiveMedia);
  const setSelectedClip = useCutEditorStore((s) => s.setSelectedClip);

  // Local state
  const [importPath, setImportPath] = useState('');
  const [importStatus, setImportStatus] = useState('');
  const [importProgress, setImportProgress] = useState<number | null>(null);
  const [importing, setImporting] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [collapsedBins, setCollapsedBins] = useState<Set<string>>(new Set());
  const folderInputRef = useRef<HTMLInputElement | null>(null);

  // Pre-fill from URL param / store
  useEffect(() => {
    if (sourcePath && !importPath) {
      setImportPath(sourcePath);
    }
  }, [sourcePath, importPath]);

  // webkitdirectory
  useEffect(() => {
    const input = folderInputRef.current as (HTMLInputElement & { webkitdirectory?: boolean }) | null;
    if (input) input.webkitdirectory = true;
  }, []);

  // ─── Job polling ───
  const pollJob = useCallback(async (jobId: string) => {
    for (let attempt = 0; attempt < 80; attempt++) {
      const res = await fetch(`${API_BASE}/cut/job/${encodeURIComponent(jobId)}`);
      if (!res.ok) throw new Error(`Import job failed: HTTP ${res.status}`);
      const payload = (await res.json()) as {
        job?: { state?: string; progress?: number; error?: { message?: string } | null };
      };
      const state = String(payload.job?.state || '');
      setImportProgress(typeof payload.job?.progress === 'number' ? payload.job.progress : null);
      if (state === 'done') return;
      if (state === 'error') throw new Error(payload.job?.error?.message || 'Import failed');
      await new Promise((r) => setTimeout(r, 250));
    }
    throw new Error('Import timed out');
  }, []);

  // ─── Start import (bootstrap-async) ───
  const startImport = useCallback(async (path: string) => {
    const trimmed = path.trim();
    if (!trimmed) {
      setImportStatus('Enter an absolute path to import.');
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
    setImportStatus(`Importing ${labelForPath(trimmed)}...`);

    try {
      const res = await fetch(`${API_BASE}/cut/bootstrap-async`, {
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
      if (!res.ok) throw new Error(`Import failed: HTTP ${res.status}`);

      const payload = (await res.json()) as {
        success?: boolean;
        job_id?: string;
        error?: { message?: string } | null;
      };
      if (!payload.success || !payload.job_id) {
        throw new Error(payload.error?.message || 'Import job did not start');
      }

      await pollJob(payload.job_id);
      await refreshProjectState?.();
      setImportStatus(`Imported ${labelForPath(trimmed)} — ${thumbnails.length || '?'} clips`);
      setImportProgress(1);
      // Store source path for session
      setEditorSession({ sourcePath: trimmed });
    } catch (err) {
      setImportStatus(err instanceof Error ? err.message : 'Import failed');
      setImportProgress(null);
    } finally {
      setImporting(false);
    }
  }, [pollJob, projectId, refreshProjectState, storeSandboxRoot, setEditorSession, thumbnails.length]);

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

  const projectItems = mediaItems.map((item) => classifyItem(item, laneTypesByPath));

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

  const totalClips = projectItems.length;

  return (
    <div style={PANEL}>
      {/* Header */}
      <div style={HEADER}>
        <span>Project</span>
        <span>{totalClips} clip{totalClips !== 1 ? 's' : ''}</span>
      </div>

      {/* Import area */}
      <div style={IMPORT_AREA}>
        {/* Dropzone */}
        <div
          style={{
            ...DROPZONE,
            borderColor: dragging ? '#4a9eff' : '#2f2f2f',
            background: dragging ? '#081120' : 'transparent',
            color: dragging ? '#bfdbfe' : '#555',
          }}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            // Browser File API doesn't expose native paths reliably
            // User should paste absolute path
            setImportStatus('Drop detected — paste the absolute folder path below.');
          }}
          onDoubleClick={() => folderInputRef.current?.click()}
        >
          Drop media here or double-click to browse
        </div>

        {/* Path input + Import button */}
        <div style={INPUT_ROW}>
          <input
            style={PATH_INPUT}
            placeholder="/path/to/media/folder"
            value={importPath}
            onChange={(e) => setImportPath(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && importPath.trim()) {
                void startImport(importPath);
              }
            }}
          />
          <button
            type="button"
            style={{ ...IMPORT_BTN, opacity: importing ? 0.5 : 1 }}
            disabled={importing || !importPath.trim()}
            onClick={() => void startImport(importPath)}
          >
            Import
          </button>
        </div>

        {/* Hidden folder picker */}
        <input
          ref={folderInputRef}
          type="file"
          multiple
          style={{ display: 'none' }}
          onChange={(e) => {
            const files = e.target.files;
            if (files && files.length > 0) {
              // Try to extract native path (Electron/Tauri only)
              const f = files[0] as File & { path?: string };
              if (f.path) {
                const dir = f.path.replace(/[\\/][^\\/]+$/, '');
                setImportPath(dir);
                void startImport(dir);
              } else {
                setImportStatus('Folder picker does not expose native path in this runtime. Paste an absolute path.');
              }
            }
          }}
        />

        {/* Status */}
        <div style={{
          ...STATUS_LINE,
          color: importStatus.includes('fail') || importStatus.includes('error')
            ? '#f87171'
            : importStatus.includes('Import') ? '#93c5fd' : '#555',
        }}>
          {importStatus || (storeSandboxRoot ? 'Sandbox ready' : 'Import media to create project')}
          {importProgress != null && importProgress < 1 ? ` ${Math.round(importProgress * 100)}%` : ''}
        </div>
      </div>

      {/* Bin list (media clips organized by type) */}
      <div style={BIN_LIST}>
        {bins.map((bin) => {
          const isCollapsed = collapsedBins.has(bin.key);
          return (
            <div key={bin.key}>
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
                    style={{
                      ...CLIP_ITEM,
                      background: isActive ? '#1a1a2a' : 'transparent',
                      borderLeft: isActive ? '2px solid #4a9eff' : '2px solid transparent',
                    }}
                    onClick={() => handleClipClick(item.source_path)}
                  >
                    {/* Thumbnail */}
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

                    {/* Clip info */}
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
              Import a media folder to start editing
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
