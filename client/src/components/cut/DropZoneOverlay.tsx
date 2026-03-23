/**
 * MARKER_GAMMA-R4.3: Timeline drop zone overlay.
 *
 * Shows visual feedback when dragging media from Project Panel over the layout:
 * - Dashed border overlay appears on dragover when cut media data is present
 * - Mode badge shows Insert/Overwrite (Alt toggles)
 * - Purely visual — actual drop handling is in TimelineTrackView (Alpha domain)
 */
import { useState, useCallback, useEffect, useRef, type CSSProperties } from 'react';

const OVERLAY: CSSProperties = {
  position: 'absolute',
  inset: 0,
  border: '2px dashed #666',
  borderRadius: 4,
  background: 'rgba(255,255,255,0.02)',
  pointerEvents: 'none',
  zIndex: 9998,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'opacity 0.15s ease-out',
};

const BADGE: CSSProperties = {
  padding: '4px 12px',
  background: 'rgba(30,30,30,0.92)',
  border: '1px solid #555',
  borderRadius: 4,
  fontSize: 11,
  fontFamily: 'system-ui, -apple-system, sans-serif',
  color: '#ccc',
  letterSpacing: '0.5px',
  pointerEvents: 'none',
};

function hasCutMedia(e: DragEvent): boolean {
  return e.dataTransfer?.types?.includes('text/cut-media-path') ?? false;
}

export default function DropZoneOverlay() {
  const [visible, setVisible] = useState(false);
  const [altHeld, setAltHeld] = useState(false);
  const dragCountRef = useRef(0);

  const onDragEnter = useCallback((e: DragEvent) => {
    if (!hasCutMedia(e)) return;
    dragCountRef.current++;
    setVisible(true);
  }, []);

  const onDragLeave = useCallback(() => {
    dragCountRef.current--;
    if (dragCountRef.current <= 0) {
      dragCountRef.current = 0;
      setVisible(false);
    }
  }, []);

  const onDrop = useCallback(() => {
    dragCountRef.current = 0;
    setVisible(false);
  }, []);

  const onDragOver = useCallback((e: DragEvent) => {
    if (!hasCutMedia(e)) return;
    setAltHeld(e.altKey);
  }, []);

  useEffect(() => {
    const el = document.querySelector('.dockview-theme-dark');
    if (!el) return;
    el.addEventListener('dragenter', onDragEnter as EventListener);
    el.addEventListener('dragleave', onDragLeave as EventListener);
    el.addEventListener('drop', onDrop as EventListener);
    el.addEventListener('dragover', onDragOver as EventListener);
    return () => {
      el.removeEventListener('dragenter', onDragEnter as EventListener);
      el.removeEventListener('dragleave', onDragLeave as EventListener);
      el.removeEventListener('drop', onDrop as EventListener);
      el.removeEventListener('dragover', onDragOver as EventListener);
    };
  }, [onDragEnter, onDragLeave, onDrop, onDragOver]);

  // Track Alt key globally while dragging
  useEffect(() => {
    if (!visible) return;
    const onKey = (e: KeyboardEvent) => setAltHeld(e.altKey);
    window.addEventListener('keydown', onKey);
    window.addEventListener('keyup', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('keyup', onKey);
    };
  }, [visible]);

  if (!visible) return null;

  return (
    <div style={{ ...OVERLAY, opacity: 1 }} data-testid="drop-zone-overlay">
      <div style={BADGE}>
        {altHeld ? 'INSERT' : 'OVERWRITE'}
        <span style={{ color: '#666', marginLeft: 8, fontSize: 9 }}>
          {altHeld ? '(Alt held)' : '(hold Alt for Insert)'}
        </span>
      </div>
    </div>
  );
}
