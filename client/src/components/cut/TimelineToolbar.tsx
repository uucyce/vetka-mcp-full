/**
 * MARKER_CUT_0.3: TimelineToolbar — minimal toolbar above timeline tracks.
 *
 * Contains ONLY:
 *   - Snap toggle (magnet icon, hotkey S)
 *   - Zoom slider (horizontal, thin)
 *   - Linked selection toggle (link icon)
 *
 * Nothing else. All other controls → hotkeys or menus.
 * Ref: CUT_NLE_UNIVERSAL_ACTION_REGISTRY.md
 */
import { useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

const ROOT: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '2px 12px',
  background: '#0a0a0a',
  borderBottom: '1px solid #1a1a1a',
  height: 26,
  flexShrink: 0,
  userSelect: 'none',
};

const TOGGLE_BTN: CSSProperties = {
  background: 'none',
  border: '1px solid #333',
  color: '#666',
  borderRadius: 3,
  padding: '2px 8px',
  cursor: 'pointer',
  fontSize: 12,
  lineHeight: 1,
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  height: 20,
};

const TOGGLE_ACTIVE: CSSProperties = {
  ...TOGGLE_BTN,
  background: '#1a1a1a',
  color: '#fff',
  border: '1px solid #444',
};

const ZOOM_LABEL: CSSProperties = {
  fontSize: 9,
  color: '#555',
  textTransform: 'uppercase',
  letterSpacing: 1,
};

const ZOOM_SLIDER: CSSProperties = {
  width: 80,
  height: 3,
  appearance: 'none' as const,
  background: '#333',
  borderRadius: 2,
  outline: 'none',
  cursor: 'pointer',
};

export default function TimelineToolbar() {
  const zoom = useCutEditorStore((s) => s.zoom);
  const setZoom = useCutEditorStore((s) => s.setZoom);
  const snapEnabled = useCutEditorStore((s) => s.snapEnabled ?? true);
  const toggleSnap = useCutEditorStore((s) => s.toggleSnap);

  // Linked selection state (local for now — will connect to store later)
  const handleZoomChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setZoom(Number(e.target.value));
    },
    [setZoom],
  );

  return (
    <div style={ROOT}>
      {/* Snap toggle */}
      <button
        style={snapEnabled ? TOGGLE_ACTIVE : TOGGLE_BTN}
        onClick={toggleSnap}
        title="Snap to grid (S)"
      >
        Snap
      </button>

      {/* Zoom slider */}
      <span style={ZOOM_LABEL}>Zoom</span>
      <input
        type="range"
        min={10}
        max={500}
        step={5}
        value={zoom}
        onChange={handleZoomChange}
        style={ZOOM_SLIDER}
        title={`Zoom: ${zoom}px/sec`}
      />

      <div style={{ flex: 1 }} />
    </div>
  );
}
