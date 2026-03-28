/**
 * MARKER_B23: LUT Browser Panel — import, browse, preview, apply LUTs.
 *
 * Features:
 *   - List imported .cube LUT files from project storage
 *   - Click to preview (before/after thumbnails)
 *   - Double-click to apply to selected clip
 *   - Import button (file path input)
 *   - Delete button per LUT
 *
 * Wires to: GET /cut/color/lut/list, POST /cut/color/lut/import,
 *           POST /cut/color/lut/preview, POST /cut/color/lut/delete
 *
 * @phase B23
 * @task tb_1774129488_3
 */
import { useState, useEffect, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useSelectionStore } from '../../store/useSelectionStore';
import { API_BASE } from '../../config/api.config';

interface LutEntry {
  name: string;
  filename: string;
  path: string;
}

interface LutPreview {
  before: string | null;
  after: string | null;
  lutName: string;
}

const PANEL: CSSProperties = {
  display: 'flex', flexDirection: 'column', height: '100%',
  background: '#0d0d0d', fontFamily: 'system-ui', fontSize: 11, color: '#ccc', overflow: 'hidden',
};

const HEADER: CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  padding: '6px 10px', borderBottom: '1px solid #1a1a1a', flexShrink: 0,
};

const LUT_LIST: CSSProperties = {
  flex: 1, overflowY: 'auto', padding: '4px 0',
};

const LUT_ITEM: CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  padding: '4px 10px', cursor: 'pointer', borderBottom: '1px solid #111',
};

const LUT_ITEM_SELECTED: CSSProperties = {
  ...LUT_ITEM, background: '#1a1a1a',
};

const BTN: CSSProperties = {
  padding: '3px 8px', border: '1px solid #333', borderRadius: 3,
  background: '#111', color: '#aaa', fontSize: 9, cursor: 'pointer',
};

const BTN_DANGER: CSSProperties = {
  ...BTN, borderColor: '#444', color: '#888',
};

const PREVIEW_AREA: CSSProperties = {
  display: 'flex', gap: 4, padding: '6px 10px',
  borderTop: '1px solid #1a1a1a', flexShrink: 0,
};

const PREVIEW_IMG: CSSProperties = {
  flex: 1, maxHeight: 80, objectFit: 'contain' as const,
  borderRadius: 3, border: '1px solid #222',
};

const EMPTY: CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  flex: 1, color: '#444', fontSize: 10,
};

const IMPORT_ROW: CSSProperties = {
  display: 'flex', gap: 4, padding: '6px 10px',
  borderTop: '1px solid #1a1a1a', flexShrink: 0,
};

const INPUT: CSSProperties = {
  flex: 1, padding: '3px 6px', background: '#111', border: '1px solid #333',
  borderRadius: 3, color: '#ccc', fontSize: 10, fontFamily: 'system-ui',
};

export default function LutBrowserPanel() {
  const [luts, setLuts] = useState<LutEntry[]>([]);
  const [selectedLut, setSelectedLut] = useState<string | null>(null);
  const [preview, setPreview] = useState<LutPreview | null>(null);
  const [importPath, setImportPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sandboxRoot = useCutEditorStore((s) => s.sandboxRoot);
  const projectId = useCutEditorStore((s) => s.projectId);
  const selectedClipId = useSelectionStore((s) => s.selectedClipId);
  const currentTime = useCutEditorStore((s) => s.currentTime);
  const lanes = useCutEditorStore((s) => s.lanes);

  const selectedClip = lanes.flatMap((l) => l.clips || []).find((c) => c.clip_id === selectedClipId);

  // Fetch LUT list
  const fetchLuts = useCallback(async () => {
    if (!sandboxRoot || !projectId) return;
    try {
      const res = await fetch(
        `${API_BASE}/cut/color/lut/list?sandbox_root=${encodeURIComponent(sandboxRoot)}&project_id=${encodeURIComponent(projectId)}`
      );
      const data = await res.json();
      if (data.success) setLuts(data.luts || []);
    } catch {
      // silent
    }
  }, [sandboxRoot, projectId]);

  useEffect(() => { fetchLuts(); }, [fetchLuts]);

  // Preview selected LUT
  const previewLut = useCallback(async (lut: LutEntry) => {
    if (!selectedClip?.source_path) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/cut/color/lut/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: selectedClip.source_path,
          lut_path: lut.path,
          time: currentTime,
          proxy_height: 180,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setPreview({
          before: data.before ? `data:image/jpeg;base64,${data.before}` : null,
          after: data.after ? `data:image/jpeg;base64,${data.after}` : null,
          lutName: lut.name,
        });
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [selectedClip?.source_path, currentTime]);

  // Select + preview
  const handleSelect = useCallback((lut: LutEntry) => {
    setSelectedLut(lut.filename);
    previewLut(lut);
  }, [previewLut]);

  // Apply LUT to clip
  const handleApply = useCallback((lut: LutEntry) => {
    if (!selectedClipId) return;
    const store = useCutEditorStore.getState();
    const updatedLanes = store.lanes.map((lane) => ({
      ...lane,
      clips: (lane.clips || []).map((clip) => {
        if (clip.clip_id !== selectedClipId) return clip;
        const cc = (clip as any).color_correction || {};
        return { ...clip, color_correction: { ...cc, lutPath: lut.path, lutName: lut.name } };
      }),
    }));
    store.setLanes(updatedLanes);
  }, [selectedClipId]);

  // Import LUT
  const handleImport = useCallback(async () => {
    if (!sandboxRoot || !projectId || !importPath.trim()) return;
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/cut/color/lut/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sandbox_root: sandboxRoot, project_id: projectId, source_path: importPath.trim() }),
      });
      const data = await res.json();
      if (data.success) {
        setImportPath('');
        fetchLuts();
      } else {
        setError(data.error || 'import_failed');
      }
    } catch (e: any) {
      setError(e.message);
    }
  }, [sandboxRoot, projectId, importPath, fetchLuts]);

  // Delete LUT
  const handleDelete = useCallback(async (filename: string) => {
    if (!sandboxRoot || !projectId) return;
    try {
      await fetch(`${API_BASE}/cut/color/lut/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sandbox_root: sandboxRoot, project_id: projectId, lut_filename: filename }),
      });
      if (selectedLut === filename) {
        setSelectedLut(null);
        setPreview(null);
      }
      fetchLuts();
    } catch {
      // silent
    }
  }, [sandboxRoot, projectId, selectedLut, fetchLuts]);

  return (
    <div style={PANEL} data-testid="cut-lut-browser">
      <div style={HEADER}>
        <span style={{ fontSize: 12, fontWeight: 600, color: '#fff' }}>LUT Browser</span>
        <button style={BTN} onClick={fetchLuts} title="Refresh">Refresh</button>
      </div>

      {luts.length === 0 ? (
        <div style={EMPTY}>No LUTs imported. Use the import field below.</div>
      ) : (
        <div style={LUT_LIST}>
          {luts.map((lut) => (
            <div
              key={lut.filename}
              style={selectedLut === lut.filename ? LUT_ITEM_SELECTED : LUT_ITEM}
              onClick={() => handleSelect(lut)}
              onDoubleClick={() => handleApply(lut)}
              data-testid={`lut-item-${lut.name}`}
              title="Click to preview, double-click to apply"
            >
              <div>
                <div style={{ fontWeight: 500 }}>{lut.name}</div>
                <div style={{ fontSize: 9, color: '#555' }}>{lut.filename}</div>
              </div>
              <div style={{ display: 'flex', gap: 4 }}>
                <button
                  style={BTN}
                  onClick={(e) => { e.stopPropagation(); handleApply(lut); }}
                  title="Apply to selected clip"
                >
                  Apply
                </button>
                <button
                  style={BTN_DANGER}
                  onClick={(e) => { e.stopPropagation(); handleDelete(lut.filename); }}
                  title="Delete LUT"
                >
                  Del
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Before/After preview */}
      {preview && (
        <div style={PREVIEW_AREA}>
          {preview.before && (
            <div style={{ flex: 1, textAlign: 'center' as const }}>
              <div style={{ fontSize: 8, color: '#555', marginBottom: 2 }}>Before</div>
              <img src={preview.before} alt="Before" style={PREVIEW_IMG} />
            </div>
          )}
          {preview.after && (
            <div style={{ flex: 1, textAlign: 'center' as const }}>
              <div style={{ fontSize: 8, color: '#999', marginBottom: 2 }}>{preview.lutName}</div>
              <img src={preview.after} alt="After" style={PREVIEW_IMG} />
            </div>
          )}
        </div>
      )}

      {loading && <div style={{ padding: '4px 10px', fontSize: 9, color: '#555' }}>Loading preview...</div>}

      {/* Import row */}
      <div style={IMPORT_ROW}>
        <input
          style={INPUT}
          value={importPath}
          onChange={(e) => setImportPath(e.target.value)}
          placeholder="/path/to/lut.cube"
          onKeyDown={(e) => e.key === 'Enter' && handleImport()}
          data-testid="lut-import-input"
        />
        <button style={BTN} onClick={handleImport} data-testid="lut-import-btn">Import</button>
      </div>

      {error && <div style={{ padding: '2px 10px', fontSize: 9, color: '#999' }}>{error}</div>}
    </div>
  );
}
