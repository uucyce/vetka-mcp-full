/**
 * MARKER_CUT_0.3: TimelineToolbar — minimal toolbar above timeline tracks.
 *
 * Contains ONLY:
 *   - Snap toggle (magnet SVG icon, hotkey S)
 *
 * Zoom = hotkeys +/- or mouse wheel. No slider.
 * Track height = mouse drag on track header or Shift+scroll.
 * Ref: CUT_NLE_UNIVERSAL_ACTION_REGISTRY.md
 */
import { type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

const ROOT: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  padding: '2px 12px',
  background: '#0a0a0a',
  borderBottom: '1px solid #1a1a1a',
  height: 24,
  flexShrink: 0,
  userSelect: 'none',
};

const SNAP_BTN: CSSProperties = {
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  padding: '2px 4px',
  display: 'flex',
  alignItems: 'center',
  borderRadius: 3,
};

function MagnetIcon({ active }: { active: boolean }) {
  const color = active ? '#ccc' : '#444';
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M4 2v2h2V2H4zm6 0v2h2V2h-2zM4 4v4a4 4 0 008 0V4h-2v4a2 2 0 01-4 0V4H4z"
        fill={color}
      />
    </svg>
  );
}

// MARKER_W3.6: Tool indicator style
const TOOL_BTN: CSSProperties = {
  background: 'none',
  border: '1px solid transparent',
  cursor: 'pointer',
  padding: '1px 6px',
  fontSize: 10,
  fontFamily: 'system-ui',
  color: '#555',
  borderRadius: 3,
};

export default function TimelineToolbar() {
  const snapEnabled = useCutEditorStore((s) => s.snapEnabled ?? true);
  const toggleSnap = useCutEditorStore((s) => s.toggleSnap);
  const activeTool = useCutEditorStore((s) => s.activeTool);
  const setActiveTool = useCutEditorStore((s) => s.setActiveTool);

  return (
    <div style={ROOT}>
      <button
        style={{
          ...SNAP_BTN,
          background: snapEnabled ? '#1a1a1a' : 'none',
        }}
        onClick={toggleSnap}
        title={`Snap ${snapEnabled ? 'ON' : 'OFF'} (S)`}
      >
        <MagnetIcon active={snapEnabled} />
      </button>
      {/* MARKER_W3.6: Tool selector — V=Selection, C=Razor */}
      <div style={{ width: 1, height: 14, background: '#222', margin: '0 4px' }} />
      {(['selection', 'razor'] as const).map((tool) => (
        <button
          key={tool}
          style={{
            ...TOOL_BTN,
            color: activeTool === tool ? '#ccc' : '#555',
            background: activeTool === tool ? '#1a1a1a' : 'none',
            borderColor: activeTool === tool ? '#333' : 'transparent',
          }}
          onClick={() => setActiveTool(tool)}
          title={tool === 'selection' ? 'Selection Tool (V)' : 'Razor Tool (C)'}
        >
          {tool === 'selection' ? 'V' : 'C'}
        </button>
      ))}
    </div>
  );
}
