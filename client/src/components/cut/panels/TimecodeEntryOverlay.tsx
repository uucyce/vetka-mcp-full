/**
 * MARKER_GAMMA-P1: Timecode Entry Overlay — jump to timecode via F2.
 *
 * FCP7 Ch.15: Timecode entry allows direct numeric input to navigate.
 * Type timecode (HH:MM:SS:FF) and press Enter to jump playhead.
 * Monochrome — no colored UI elements.
 */
import { useState, useEffect, useRef, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';

const OVERLAY: CSSProperties = {
  position: 'fixed', inset: 0, zIndex: 9999,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  background: 'rgba(0,0,0,0.4)',
};

const DIALOG: CSSProperties = {
  background: '#111', border: '1px solid #2a2a2a', borderRadius: 8,
  width: 280, fontFamily: 'system-ui', fontSize: 11, color: '#ccc',
  boxShadow: '0 12px 40px rgba(0,0,0,0.5)', padding: '14px',
};

const LABEL: CSSProperties = {
  fontSize: 9, color: '#666', textTransform: 'uppercase',
  letterSpacing: 0.5, marginBottom: 6,
};

const INPUT: CSSProperties = {
  width: '100%', padding: '8px 10px', background: '#0a0a0a',
  border: '1px solid #333', borderRadius: 4, color: '#ccc',
  fontSize: 18, fontFamily: 'monospace', textAlign: 'center',
  outline: 'none', letterSpacing: 2, boxSizing: 'border-box',
};

const HINT: CSSProperties = {
  fontSize: 9, color: '#444', textAlign: 'center', marginTop: 8,
};

export function TimecodeEntryOverlay() {
  const show = useCutEditorStore((s) => s.showTimecodeEntry);
  const currentTime = useCutEditorStore((s) => s.currentTime);

  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (show) {
      setValue(formatTimecode(currentTime));
      setTimeout(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      }, 50);
    }
  }, [show, currentTime]);

  const close = useCallback(() => {
    useCutEditorStore.getState().setShowTimecodeEntry(false);
  }, []);

  const submit = useCallback(() => {
    const seconds = parseTimecode(value);
    if (seconds !== null && seconds >= 0) {
      useCutEditorStore.getState().seek(seconds);
    }
    close();
  }, [value, close]);

  if (!show) return null;

  return (
    <div
      style={OVERLAY}
      data-testid="timecode-entry-overlay"
      role="dialog"
      onClick={(e) => { if (e.target === e.currentTarget) close(); }}
    >
      <div style={DIALOG} data-testid="timecode-entry-dialog">
        <div style={LABEL}>Go to Timecode</div>
        <input
          ref={inputRef}
          style={INPUT}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') submit();
            if (e.key === 'Escape') close();
          }}
          placeholder="00:00:00:00"
          data-testid="timecode-input"
        />
        <div style={HINT}>Enter to jump, Esc to cancel</div>
      </div>
    </div>
  );
}

function formatTimecode(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  const f = Math.floor((sec % 1) * 30);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
}

function parseTimecode(tc: string): number | null {
  // Accept HH:MM:SS:FF or HH:MM:SS or MM:SS or raw seconds
  const parts = tc.trim().split(/[:;]/);
  if (parts.length === 4) {
    const [h, m, s, f] = parts.map(Number);
    if ([h, m, s, f].some(isNaN)) return null;
    return h * 3600 + m * 60 + s + f / 30;
  }
  if (parts.length === 3) {
    const [h, m, s] = parts.map(Number);
    if ([h, m, s].some(isNaN)) return null;
    return h * 3600 + m * 60 + s;
  }
  if (parts.length === 2) {
    const [m, s] = parts.map(Number);
    if ([m, s].some(isNaN)) return null;
    return m * 60 + s;
  }
  const n = Number(tc);
  return isNaN(n) ? null : n;
}
