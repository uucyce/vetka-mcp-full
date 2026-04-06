/**
 * MARKER_GAMMA-MKL1: Marker List panel — sortable table with seek-on-click.
 *
 * FCP7 Ch.52 reference: scrollable table of all timeline markers.
 * Columns: timecode, type (color dot), text.
 * Click row → seek playhead to marker time.
 * Sort by time (default) or type. Filter by kind dropdown.
 *
 * Reads markers from useCutEditorStore. Marker colors match timeline rendering.
 */
import { useState, useCallback, useMemo, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';

// Marker colors — matches TimelineTrackView MARKER_COLORS (exception to monochrome rule)
const MARKER_COLORS: Record<string, string> = {
  favorite: '#f59e0b',
  negative: '#ef4444',
  comment: '#3b82f6',
  cam: '#a855f7',
  insight: '#22c55e',
  chat: '#94a3b8',
  bpm_audio: '#22c55e',
  bpm_visual: '#4a9eff',
  bpm_script: '#ffffff',
  sync_point: '#f59e0b',
};

const KIND_LABELS: Record<string, string> = {
  favorite: 'Favorite',
  comment: 'Comment',
  cam: 'Camera',
  insight: 'Insight',
  chat: 'Chat',
  bpm_audio: 'BPM Audio',
  bpm_visual: 'BPM Visual',
  bpm_script: 'BPM Script',
  sync_point: 'Sync Point',
};

function fmtTC(sec: number, fps: number): string {
  const totalFrames = Math.round(sec * fps);
  const f = totalFrames % fps;
  const totalSec = Math.floor(totalFrames / fps);
  const s = totalSec % 60;
  const m = Math.floor(totalSec / 60) % 60;
  const h = Math.floor(totalSec / 3600);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
}

// MARKER_GAMMA-MARKER-TC-MODE: respect timecodeDisplayMode (same pattern as StatusBar)
function fmtTime(sec: number, fps: number, mode: 'timecode' | 'frames' | 'seconds'): string {
  if (mode === 'frames') return `${Math.round(sec * fps)}f`;
  if (mode === 'seconds') return `${sec.toFixed(2)}s`;
  return fmtTC(sec, fps);
}

const PANEL: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  background: '#0a0a0a',
  fontFamily: 'system-ui, -apple-system, sans-serif',
  fontSize: 10,
  color: '#ccc',
  overflow: 'hidden',
};

const TOOLBAR: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  padding: '4px 8px',
  borderBottom: '1px solid #1a1a1a',
  flexShrink: 0,
};

const TH: CSSProperties = {
  padding: '3px 6px',
  fontSize: 8,
  color: '#555',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  cursor: 'pointer',
  userSelect: 'none',
  borderBottom: '1px solid #222',
  background: '#0a0a0a',
  textAlign: 'left',
};

const TD: CSSProperties = {
  padding: '3px 6px',
  fontSize: 10,
  borderBottom: '1px solid #111',
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
};

type SortKey = 'time' | 'kind';

export default function MarkerListPanel() {
  const markers = useCutEditorStore((s) => s.markers);
  const fps = useCutEditorStore((s) => s.projectFramerate) || 24;
  const seek = useCutEditorStore((s) => s.seek);
  const currentTime = useCutEditorStore((s) => s.currentTime);
  // MARKER_GAMMA-MARKER-TC-MODE: respect user's display mode preference
  const timecodeDisplayMode = useCutEditorStore((s) => s.timecodeDisplayMode);

  const [sortKey, setSortKey] = useState<SortKey>('time');
  const [sortAsc, setSortAsc] = useState(true);
  const [filterKind, setFilterKind] = useState<string>('all');

  const toggleSort = useCallback((key: SortKey) => {
    if (sortKey === key) setSortAsc((a) => !a);
    else { setSortKey(key); setSortAsc(true); }
  }, [sortKey]);

  const sorted = useMemo(() => {
    let list = [...markers];
    if (filterKind !== 'all') list = list.filter((m) => m.kind === filterKind);
    const dir = sortAsc ? 1 : -1;
    if (sortKey === 'time') list.sort((a, b) => dir * (a.start_sec - b.start_sec));
    else list.sort((a, b) => dir * (a.kind ?? '').localeCompare(b.kind ?? ''));
    return list;
  }, [markers, sortKey, sortAsc, filterKind]);

  // Unique kinds for filter dropdown
  const kinds = useMemo(() => {
    const set = new Set(markers.map((m) => m.kind));
    return [...set].sort();
  }, [markers]);

  // Find nearest marker to playhead
  const nearestId = useMemo(() => {
    if (markers.length === 0) return null;
    let best = markers[0];
    for (const m of markers) {
      if (Math.abs(m.start_sec - currentTime) < Math.abs(best.start_sec - currentTime)) best = m;
    }
    return Math.abs(best.start_sec - currentTime) < 0.5 ? best.marker_id : null;
  }, [markers, currentTime]);

  if (markers.length === 0) {
    return (
      <div style={PANEL} data-testid="marker-list-panel">
        <div style={{ ...TOOLBAR, justifyContent: 'center', color: '#555', padding: 24 }}>
          No markers. Press M to add a marker.
        </div>
      </div>
    );
  }

  return (
    <div style={PANEL} data-testid="marker-list-panel">
      {/* Toolbar: filter + count */}
      <div style={TOOLBAR}>
        <select
          data-testid="marker-list-filter-kind"
          value={filterKind}
          onChange={(e) => setFilterKind(e.target.value)}
          style={{
            background: '#111', border: '1px solid #333', borderRadius: 3,
            color: '#ccc', fontSize: 9, padding: '2px 4px', outline: 'none',
          }}
        >
          <option value="all">All ({markers.length})</option>
          {kinds.map((k) => (
            <option key={k} value={k}>{KIND_LABELS[k] || k} ({markers.filter((m) => m.kind === k).length})</option>
          ))}
        </select>
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 8, color: '#555' }}>
          {sorted.length} marker{sorted.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ ...TH, width: 16 }} />
              <th style={{ ...TH, width: 80 }} data-testid="marker-list-sort-time" onClick={() => toggleSort('time')}>
                Time {sortKey === 'time' ? (sortAsc ? '\u25B4' : '\u25BE') : ''}
              </th>
              <th style={{ ...TH, width: 60 }} data-testid="marker-list-sort-kind" onClick={() => toggleSort('kind')}>
                Type {sortKey === 'kind' ? (sortAsc ? '\u25B4' : '\u25BE') : ''}
              </th>
              <th style={TH}>Text</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((m) => {
              const isNear = m.marker_id === nearestId;
              return (
                <tr
                  key={m.marker_id}
                  data-testid={`marker-list-row-${m.marker_id}`}
                  onClick={() => seek(m.start_sec)}
                  onDoubleClick={() => useCutEditorStore.getState().setShowEditMarkerDialog(true, m.marker_id)}
                  style={{
                    cursor: 'pointer',
                    background: isNear ? '#1a1a1a' : 'transparent',
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = '#151515'; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = isNear ? '#1a1a1a' : 'transparent'; }}
                >
                  <td style={{ ...TD, textAlign: 'center' }}>
                    <div style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: MARKER_COLORS[m.kind] || '#888',
                      display: 'inline-block',
                    }} />
                  </td>
                  <td style={{ ...TD, fontVariantNumeric: 'tabular-nums', fontFamily: 'monospace', fontSize: 9 }}>
                    {fmtTime(m.start_sec, fps, timecodeDisplayMode)}
                  </td>
                  <td style={{ ...TD, color: '#888', fontSize: 9 }}>
                    {KIND_LABELS[m.kind] || m.kind}
                  </td>
                  <td style={{ ...TD, maxWidth: 120 }}>
                    {m.text || '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
