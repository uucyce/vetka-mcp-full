/**
 * MARKER_GAMMA-FIND: Find dialog — search clips on timeline (FCP7 Edit > Find ⌘F).
 *
 * Filters all clips across all lanes by source_path basename or clip_id.
 * Results: timecode + lane_id + filename.
 * Click row → seek playhead to clip start_sec.
 * Monochrome FCP7 style.
 */
import { useState, useMemo, useRef, useEffect, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import { useOverlayEscapeClose } from '../../../hooks/useOverlayEscapeClose';

// ─── Styles ───

const OVERLAY: CSSProperties = {
  position: 'fixed', inset: 0, zIndex: 9999,
  display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
  background: 'rgba(0,0,0,0.5)',
  paddingTop: 80,
};

const DIALOG: CSSProperties = {
  background: '#111', border: '1px solid #2a2a2a', borderRadius: 6,
  width: 420, fontFamily: 'system-ui', fontSize: 11, color: '#ccc',
  boxShadow: '0 16px 48px rgba(0,0,0,0.6)',
  display: 'flex', flexDirection: 'column',
};

const SEARCH_ROW: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 8,
  padding: '10px 12px', borderBottom: '1px solid #1e1e1e',
};

const SEARCH_INPUT: CSSProperties = {
  flex: 1, background: '#0a0a0a', border: '1px solid #333', borderRadius: 4,
  color: '#ccc', fontSize: 12, padding: '6px 10px', outline: 'none',
  fontFamily: 'system-ui',
};

const RESULTS: CSSProperties = {
  maxHeight: 280, overflowY: 'auto',
};

const RESULT_ROW: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 8,
  padding: '5px 12px', borderBottom: '1px solid #111',
  cursor: 'pointer',
};

const TC: CSSProperties = {
  fontFamily: 'monospace', fontSize: 9, color: '#666', flexShrink: 0, width: 72,
};

const LANE_BADGE: CSSProperties = {
  fontSize: 8, padding: '1px 5px', borderRadius: 2,
  border: '1px solid #2a2a2a', color: '#555', flexShrink: 0,
};

const FILENAME: CSSProperties = {
  flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
  fontSize: 11,
};

const FOOTER: CSSProperties = {
  padding: '6px 12px', borderTop: '1px solid #1a1a1a',
  fontSize: 9, color: '#444', display: 'flex', justifyContent: 'space-between',
};

// ─── Helper ───

function fmtTC(sec: number, fps: number): string {
  const total = Math.round(sec * fps);
  const f = total % fps;
  const s = Math.floor(total / fps) % 60;
  const m = Math.floor(total / fps / 60) % 60;
  const h = Math.floor(total / fps / 3600);
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}:${String(f).padStart(2,'0')}`;
}

function basename(path: string): string {
  return path.split('/').pop()?.split('\\').pop() || path;
}

// ─── Component ───

export function FindDialog() {
  const show = useCutEditorStore((s) => s.showFindDialog);
  const lanes = useCutEditorStore((s) => s.lanes);
  const fps = useCutEditorStore((s) => s.projectFramerate) || 25;
  const seek = useCutEditorStore((s) => s.seek);

  const [query, setQuery] = useState('');
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const close = useCallback(() => {
    useCutEditorStore.getState().setShowFindDialog(false);
  }, []);

  // MARKER_GAMMA-ESC-HOOK: Escape closes overlay + data-overlay prevents escapeContext from firing
  useOverlayEscapeClose(close);

  // Auto-focus input when opened
  useEffect(() => {
    if (show) {
      setQuery('');
      setActiveIdx(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [show]);

  // Build flat clip list with lane info
  const allClips = useMemo(() => {
    const list: { clipId: string; laneId: string; startSec: number; name: string }[] = [];
    for (const lane of lanes) {
      for (const clip of lane.clips) {
        list.push({
          clipId: clip.clip_id,
          laneId: lane.lane_id,
          startSec: clip.start_sec,
          name: basename(clip.source_path || clip.clip_id),
        });
      }
    }
    list.sort((a, b) => a.startSec - b.startSec);
    return list;
  }, [lanes]);

  const results = useMemo(() => {
    if (!query.trim()) return allClips;
    const q = query.toLowerCase();
    return allClips.filter((c) =>
      c.name.toLowerCase().includes(q) || c.clipId.toLowerCase().includes(q) || c.laneId.toLowerCase().includes(q)
    );
  }, [allClips, query]);

  const handleKey = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && results[activeIdx]) {
      seek(results[activeIdx].startSec);
      close();
    }
  }, [results, activeIdx, seek, close]);

  if (!show) return null;

  return (
    <div
      style={OVERLAY}
      data-overlay="1"
      data-testid="find-dialog-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) close(); }}
    >
      <div style={DIALOG} data-testid="find-dialog">
        <div style={SEARCH_ROW}>
          <input
            ref={inputRef}
            style={SEARCH_INPUT}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActiveIdx(0); }}
            onKeyDown={handleKey}
            placeholder="Search clips by name or track..."
            data-testid="find-dialog-input"
          />
        </div>

        <div style={RESULTS}>
          {results.length === 0 ? (
            <div style={{ padding: '16px 12px', color: '#444', fontSize: 10, textAlign: 'center' }}>
              {query ? 'No clips match.' : 'No clips on timeline.'}
            </div>
          ) : (
            results.map((clip, idx) => (
              <div
                key={`${clip.laneId}-${clip.clipId}`}
                style={{
                  ...RESULT_ROW,
                  background: idx === activeIdx ? '#1a1a1a' : 'transparent',
                }}
                data-testid={`find-result-${idx}`}
                onClick={() => { seek(clip.startSec); close(); }}
                onMouseEnter={() => setActiveIdx(idx)}
              >
                <span style={TC}>{fmtTC(clip.startSec, fps)}</span>
                <span style={LANE_BADGE}>{clip.laneId}</span>
                <span style={FILENAME} title={clip.name}>{clip.name}</span>
              </div>
            ))
          )}
        </div>

        <div style={FOOTER}>
          <span>{results.length} clip{results.length !== 1 ? 's' : ''}</span>
          <span>↑↓ navigate · Enter seek · Esc close</span>
        </div>
      </div>
    </div>
  );
}
