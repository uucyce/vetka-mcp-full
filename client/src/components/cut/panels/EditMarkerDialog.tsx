/**
 * MARKER_GAMMA-P1: Edit Marker Dialog — edit marker name, color, and notes.
 *
 * Opens via Enter key when playhead is near a marker.
 * Reads editingMarkerId from store, finds the marker, allows inline edit.
 * Monochrome — no colored UI elements.
 */
import { useState, useEffect, useCallback, useRef, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import { useOverlayEscapeClose } from '../../../hooks/useOverlayEscapeClose';

const OVERLAY: CSSProperties = {
  position: 'fixed', inset: 0, zIndex: 9999,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  background: 'rgba(0,0,0,0.5)',
};

const DIALOG: CSSProperties = {
  background: '#111', border: '1px solid #2a2a2a', borderRadius: 8,
  width: 340, fontFamily: 'system-ui', fontSize: 11, color: '#ccc',
  boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
};

const HEADER: CSSProperties = {
  padding: '12px 14px 8px', borderBottom: '1px solid #1e1e1e',
  fontWeight: 600, fontSize: 13,
};

const BODY: CSSProperties = {
  padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 8,
};

const LABEL: CSSProperties = {
  fontSize: 9, color: '#666', textTransform: 'uppercase', letterSpacing: 0.5,
};

const INPUT: CSSProperties = {
  padding: '5px 8px', background: '#0a0a0a', border: '1px solid #333',
  borderRadius: 4, color: '#ccc', fontSize: 11, fontFamily: 'system-ui',
  outline: 'none',
};

const TEXTAREA: CSSProperties = {
  ...INPUT, minHeight: 48, resize: 'vertical', fontFamily: 'system-ui',
};

const FOOTER: CSSProperties = {
  display: 'flex', justifyContent: 'flex-end', gap: 6,
  padding: '8px 14px', borderTop: '1px solid #1e1e1e',
};

const BTN: CSSProperties = {
  padding: '4px 12px', border: '1px solid #333', borderRadius: 4,
  background: '#1a1a1a', color: '#aaa', fontSize: 10, cursor: 'pointer',
};

const BTN_PRIMARY: CSSProperties = {
  ...BTN, background: '#222', color: '#ccc',
};

export function EditMarkerDialog() {
  const show = useCutEditorStore((s) => s.showEditMarkerDialog);
  const editingMarkerId = useCutEditorStore((s) => s.editingMarkerId);
  const markers = useCutEditorStore((s) => s.markers);
  // MARKER_GAMMA-EDITMARKER-TC: use actual fps + respect timecodeDisplayMode
  const fps = useCutEditorStore((s) => s.projectFramerate ?? 25);
  const timecodeDisplayMode = useCutEditorStore((s) => s.timecodeDisplayMode);

  const marker = markers.find((m) => m.marker_id === editingMarkerId);

  const [name, setName] = useState('');
  const [notes, setNotes] = useState('');
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (show && marker) {
      setName(marker.text || '');
      setNotes(marker.notes || '');
      setTimeout(() => nameRef.current?.focus(), 50);
    }
  }, [show, marker]);

  const close = useCallback(() => {
    useCutEditorStore.getState().setShowEditMarkerDialog(false);
  }, []);

  // MARKER_GAMMA-ESC-HOOK: Escape closes dialog + data-overlay prevents escapeContext from firing
  useOverlayEscapeClose(close);

  const save = useCallback(() => {
    if (!editingMarkerId) return;
    const store = useCutEditorStore.getState();
    const updated = store.markers.map((m) => {
      if (m.marker_id !== editingMarkerId) return m;
      return { ...m, text: name, notes };
    });
    store.setMarkers(updated);
    close();
  }, [editingMarkerId, name, notes, close]);

  if (!show || !marker) return null;

  return (
    <div
      style={OVERLAY}
      data-testid="edit-marker-overlay"
      data-overlay="1"
      role="dialog"
      onClick={(e) => { if (e.target === e.currentTarget) close(); }}
    >
      <div style={DIALOG} data-testid="edit-marker-dialog">
        <div style={HEADER}>Edit Marker</div>
        <div style={BODY}>
          <div>
            <div style={LABEL}>Name</div>
            <input
              ref={nameRef}
              style={INPUT}
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') close(); }}
              data-testid="marker-name-input"
            />
          </div>
          <div>
            <div style={LABEL}>Timecode</div>
            <div style={{ fontSize: 12, fontFamily: 'monospace', color: '#888', padding: '4px 0' }}>
              {fmtTime(marker.start_sec, fps, timecodeDisplayMode)}
            </div>
          </div>
          <div>
            <div style={LABEL}>Notes</div>
            <textarea
              style={TEXTAREA}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Escape') close(); }}
              data-testid="marker-notes-input"
            />
          </div>
        </div>
        <div style={FOOTER}>
          <button style={BTN} onClick={close}>Cancel</button>
          <button style={BTN_PRIMARY} onClick={save} data-testid="marker-save-btn">Save</button>
        </div>
      </div>
    </div>
  );
}

// MARKER_GAMMA-EDITMARKER-TC: fmtTime — respects timecodeDisplayMode + actual fps
function fmtTC(sec: number, fps: number): string {
  const totalFrames = Math.round(sec * fps);
  const f = totalFrames % Math.round(fps);
  const totalSec = Math.floor(totalFrames / Math.round(fps));
  const s = totalSec % 60;
  const m = Math.floor(totalSec / 60) % 60;
  const h = Math.floor(totalSec / 3600);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
}

function fmtTime(sec: number, fps: number, mode: 'timecode' | 'frames' | 'seconds'): string {
  if (mode === 'frames') return `${Math.round(sec * fps)}f`;
  if (mode === 'seconds') return `${sec.toFixed(2)}s`;
  return fmtTC(sec, fps);
}
