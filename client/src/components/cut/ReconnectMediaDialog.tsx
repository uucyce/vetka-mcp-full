/**
 * MARKER_B71: Reconnect Offline Media dialog (FCP7 Ch.25).
 *
 * Detects offline clips (source_path doesn't exist on disk), shows list,
 * allows per-file "Locate" (file picker) and batch "Search" (directory scan).
 * Relinks via POST /cut/conform/relink.
 *
 * Triggered:
 *   - Automatically on project open if offline clips detected
 *   - Manually via File > Reconnect Media
 */
import { useState, useCallback, useEffect, type CSSProperties } from 'react';
import { API_BASE } from '../../config/api.config';

// ─── Types ───

interface OfflineMedia {
  source_path: string;
  status: 'online' | 'offline' | 'moved';
  clip_ids: string[];
  file_size: number | null;
  suggestions: string[];
}

interface ConformCheckResult {
  success: boolean;
  media: OfflineMedia[];
  summary: {
    total: number;
    online: number;
    offline: number;
    moved: number;
    auto_relinked: number;
  };
  auto_remap: Record<string, string>;
}

type ReconnectMediaDialogProps = {
  open: boolean;
  onClose: () => void;
  sandboxRoot: string;
  projectId: string;
  onRelinked?: (count: number) => void;
};

// ─── Styles (monochrome, matches SequenceSettingsDialog) ───

const OVERLAY: CSSProperties = {
  position: 'fixed', inset: 0, zIndex: 9999,
  background: 'rgba(0,0,0,0.7)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
};

const DIALOG: CSSProperties = {
  background: '#1a1a1a', border: '1px solid #333', borderRadius: 4,
  padding: 20, width: 520, maxHeight: '80vh', overflow: 'auto',
  fontFamily: 'system-ui, sans-serif', color: '#ccc',
};

const TITLE: CSSProperties = {
  fontSize: 13, fontWeight: 600, color: '#fff', marginBottom: 12,
};

const SUMMARY: CSSProperties = {
  fontSize: 10, color: '#666', marginBottom: 12,
  padding: '6px 8px', background: '#111', borderRadius: 3,
  fontFamily: '"JetBrains Mono", monospace',
};

const LIST: CSSProperties = {
  maxHeight: 300, overflow: 'auto', marginBottom: 12,
};

const ITEM: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 8,
  padding: '6px 8px', borderBottom: '1px solid #222',
  fontSize: 11,
};

const PATH_COL: CSSProperties = {
  flex: 1, minWidth: 0, overflow: 'hidden',
  textOverflow: 'ellipsis', whiteSpace: 'nowrap',
};

const STATUS_OFFLINE: CSSProperties = {
  color: '#888', fontSize: 9, fontWeight: 600,
  padding: '1px 5px', border: '1px solid #444',
  borderRadius: 2, flexShrink: 0,
};

const BTN: CSSProperties = {
  background: '#333', color: '#ccc', border: '1px solid #444',
  borderRadius: 3, padding: '4px 10px', fontSize: 10, cursor: 'pointer',
  flexShrink: 0,
};

const BTN_PRIMARY: CSSProperties = {
  ...BTN, background: '#555', color: '#fff',
};

const BTN_ROW: CSSProperties = {
  display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8,
};

const SUGGESTION: CSSProperties = {
  fontSize: 9, color: '#555', marginTop: 2,
  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
};

// ─── Helpers ───

function basename(path: string): string {
  return path.split('/').pop()?.split('\\').pop() || path;
}

// ─── Component ───

export default function ReconnectMediaDialog({
  open, onClose, sandboxRoot, projectId, onRelinked,
}: ReconnectMediaDialogProps) {
  const [media, setMedia] = useState<OfflineMedia[]>([]);
  const [summary, setSummary] = useState<ConformCheckResult['summary'] | null>(null);
  const [remap, setRemap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [relinking, setRelinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Run conform check on open
  const runCheck = useCallback(async () => {
    if (!sandboxRoot) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/cut/conform/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          search_roots: [sandboxRoot],
          auto_relink_threshold: 0.0,
        }),
      });
      const data: ConformCheckResult = await resp.json();
      if (data.success) {
        setMedia(data.media);
        setSummary(data.summary);
        // Pre-fill remap from suggestions
        const initialRemap: Record<string, string> = { ...data.auto_remap };
        for (const item of data.media) {
          if (item.status === 'offline' && item.suggestions.length > 0 && !initialRemap[item.source_path]) {
            initialRemap[item.source_path] = item.suggestions[0];
          }
        }
        setRemap(initialRemap);
      } else {
        setError('Failed to check media');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setLoading(false);
    }
  }, [sandboxRoot, projectId]);

  useEffect(() => {
    if (open) runCheck();
  }, [open, runCheck]);

  // Locate: file picker for a single offline path
  const handleLocate = useCallback(async (oldPath: string) => {
    try {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'video/*,audio/*,image/*';
      input.onchange = () => {
        const file = input.files?.[0];
        if (file) {
          // Use webkitRelativePath or name — for Electron/Tauri use native path
          // In browser context, we get the file name only; for full path we need the backend
          // For now, store the name and let user confirm
          const newPath = (file as any).path || file.name;
          setRemap((prev) => ({ ...prev, [oldPath]: newPath }));
        }
      };
      input.click();
    } catch {
      // Silent — file picker cancelled
    }
  }, []);

  // Search: trigger directory scan with higher threshold
  const handleSearch = useCallback(async () => {
    if (!sandboxRoot) return;
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/cut/conform/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          search_roots: [sandboxRoot],
          auto_relink_threshold: 0.5,
        }),
      });
      const data: ConformCheckResult = await resp.json();
      if (data.success) {
        setMedia(data.media);
        setSummary(data.summary);
        if (data.auto_remap) {
          setRemap((prev) => ({ ...prev, ...data.auto_remap }));
        }
        // Also pick up new suggestions
        for (const item of data.media) {
          if (item.status === 'offline' && item.suggestions.length > 0) {
            setRemap((prev) => {
              if (!prev[item.source_path]) {
                return { ...prev, [item.source_path]: item.suggestions[0] };
              }
              return prev;
            });
          }
        }
      }
    } catch {
      // Silent
    } finally {
      setLoading(false);
    }
  }, [sandboxRoot, projectId]);

  // Apply relink
  const handleRelink = useCallback(async () => {
    const offlineRemap: Record<string, string> = {};
    for (const [oldPath, newPath] of Object.entries(remap)) {
      if (newPath && newPath !== oldPath) {
        offlineRemap[oldPath] = newPath;
      }
    }
    if (Object.keys(offlineRemap).length === 0) return;

    setRelinking(true);
    try {
      const resp = await fetch(`${API_BASE}/cut/conform/relink`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          remap: offlineRemap,
        }),
      });
      const data = await resp.json();
      if (data.success) {
        onRelinked?.(data.remapped_count || 0);
        // Re-check to update statuses
        await runCheck();
      }
    } catch {
      setError('Relink failed');
    } finally {
      setRelinking(false);
    }
  }, [remap, sandboxRoot, projectId, onRelinked, runCheck]);

  if (!open) return null;

  const offlineMedia = media.filter((m) => m.status === 'offline');
  const remapCount = Object.keys(remap).filter((k) => remap[k] && remap[k] !== k).length;

  return (
    <div style={OVERLAY} onClick={onClose}>
      <div style={DIALOG} onClick={(e) => e.stopPropagation()}>
        <div style={TITLE}>Reconnect Media</div>

        {/* Summary */}
        {summary && (
          <div style={SUMMARY}>
            {summary.total} sources: {summary.online} online, {summary.offline} offline
            {summary.moved > 0 && `, ${summary.moved} moved`}
            {summary.auto_relinked > 0 && ` (${summary.auto_relinked} auto-relinked)`}
          </div>
        )}

        {loading && <div style={{ color: '#555', fontSize: 11, padding: 12 }}>Scanning...</div>}
        {error && <div style={{ color: '#888', fontSize: 11, padding: 8 }}>{error}</div>}

        {/* Offline media list */}
        {offlineMedia.length > 0 ? (
          <div style={LIST}>
            {offlineMedia.map((item) => (
              <div key={item.source_path}>
                <div style={ITEM}>
                  <span style={STATUS_OFFLINE}>OFFLINE</span>
                  <div style={PATH_COL} title={item.source_path}>
                    {basename(item.source_path)}
                    <div style={{ fontSize: 9, color: '#444' }}>{item.source_path}</div>
                    {item.suggestions.length > 0 && !remap[item.source_path] && (
                      <div style={SUGGESTION}>
                        Suggestion: {basename(item.suggestions[0])}
                      </div>
                    )}
                    {remap[item.source_path] && (
                      <div style={{ ...SUGGESTION, color: '#999' }}>
                        &rarr; {remap[item.source_path]}
                      </div>
                    )}
                  </div>
                  <span style={{ color: '#555', fontSize: 9 }}>
                    {item.clip_ids.length} clip{item.clip_ids.length !== 1 ? 's' : ''}
                  </span>
                  {remap[item.source_path] ? (
                    <button
                      style={BTN}
                      onClick={() => setRemap((prev) => {
                        const next = { ...prev };
                        delete next[item.source_path];
                        return next;
                      })}
                    >
                      Clear
                    </button>
                  ) : (
                    <>
                      {item.suggestions.length > 0 && (
                        <button
                          style={BTN}
                          onClick={() => setRemap((prev) => ({
                            ...prev,
                            [item.source_path]: item.suggestions[0],
                          }))}
                        >
                          Accept
                        </button>
                      )}
                      <button style={BTN} onClick={() => handleLocate(item.source_path)}>
                        Locate
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : !loading && summary && (
          <div style={{ color: '#555', fontSize: 11, padding: 12, textAlign: 'center' }}>
            All media online
          </div>
        )}

        {/* Online media collapsed */}
        {media.filter((m) => m.status === 'online').length > 0 && offlineMedia.length > 0 && (
          <div style={{ fontSize: 9, color: '#444', marginBottom: 8 }}>
            {media.filter((m) => m.status === 'online').length} source(s) online
          </div>
        )}

        {/* Action buttons */}
        <div style={BTN_ROW}>
          <button style={BTN} onClick={handleSearch} disabled={loading}>
            Search Directory
          </button>
          <button style={BTN} onClick={runCheck} disabled={loading}>
            Refresh
          </button>
          <button
            style={remapCount > 0 ? BTN_PRIMARY : { ...BTN, opacity: 0.5, cursor: 'default' }}
            onClick={handleRelink}
            disabled={remapCount === 0 || relinking}
          >
            {relinking ? 'Relinking...' : `Relink ${remapCount} file${remapCount !== 1 ? 's' : ''}`}
          </button>
          <button style={BTN} onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
