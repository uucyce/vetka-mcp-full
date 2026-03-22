/**
 * MARKER_GAMMA-21: Tools Palette — floating/dockable tool selection window.
 *
 * FCP7 style: compact palette with Arrow (A), Blade (B), Zoom (Z), Hand (H)
 * + trim tools (Slip/Slide/Ripple/Roll) + Snap toggle.
 * Can be closed — editors use hotkeys. Window → Tools to reopen.
 * Monochrome only — no color per tool.
 */
import { type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

type ToolDef = {
  id: string;
  label: string;
  icon: string;
  shortcut: string;
};

const TOOLS: ToolDef[] = [
  { id: 'selection', label: 'Arrow', icon: '\u2191', shortcut: 'A' },
  { id: 'razor',     label: 'Blade', icon: '\u2702', shortcut: 'B' },
  { id: 'hand',      label: 'Hand',  icon: '\u270B', shortcut: 'H' },
  { id: 'zoom',      label: 'Zoom',  icon: '\u2315', shortcut: 'Z' },
];

const TRIM_TOOLS: ToolDef[] = [
  { id: 'slip',   label: 'Slip',   icon: '\u2194', shortcut: 'S' },
  { id: 'slide',  label: 'Slide',  icon: '\u21D4', shortcut: 'U' },
  { id: 'ripple', label: 'Ripple', icon: '\u21C4', shortcut: 'R' },
  { id: 'roll',   label: 'Roll',   icon: '\u21CB', shortcut: 'N' },
];

const PANEL: CSSProperties = {
  height: '100%',
  overflow: 'auto',
  background: '#0d0d0d',
  fontFamily: 'system-ui, -apple-system, sans-serif',
  fontSize: 10,
  color: '#ccc',
  padding: 6,
};

const SECTION_LABEL: CSSProperties = {
  fontSize: 8,
  color: '#555',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  marginBottom: 4,
  marginTop: 8,
};

const GRID: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(4, 1fr)',
  gap: 3,
};

const TOOL_BTN = (active: boolean): CSSProperties => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 1,
  padding: '6px 2px',
  border: `1px solid ${active ? '#888' : '#222'}`,
  borderRadius: 3,
  background: active ? '#1a1a1a' : '#0a0a0a',
  color: active ? '#fff' : '#888',
  cursor: 'pointer',
  fontSize: 16,
  lineHeight: 1,
});

const SHORTCUT: CSSProperties = {
  fontSize: 7,
  color: '#555',
  fontFamily: 'monospace',
};

const SNAP_BTN = (active: boolean): CSSProperties => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 4,
  width: '100%',
  padding: '5px 0',
  border: `1px solid ${active ? '#888' : '#222'}`,
  borderRadius: 3,
  background: active ? '#1a1a1a' : '#0a0a0a',
  color: active ? '#ccc' : '#666',
  cursor: 'pointer',
  fontSize: 10,
  marginTop: 8,
});

export default function ToolsPalette() {
  const activeTool = useCutEditorStore((s) => s.activeTool);
  const setActiveTool = useCutEditorStore((s) => s.setActiveTool);
  const snapEnabled = useCutEditorStore((s) => s.snapEnabled ?? true);
  const toggleSnap = useCutEditorStore((s) => s.toggleSnap);

  return (
    <div style={PANEL} data-testid="tools-palette">
      {/* Primary tools */}
      <div style={{ fontSize: 8, color: '#555', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 }}>
        Tools
      </div>
      <div style={GRID}>
        {TOOLS.map((t) => (
          <button
            key={t.id}
            style={TOOL_BTN(activeTool === t.id)}
            onClick={() => setActiveTool(t.id as any)}
            title={`${t.label} (${t.shortcut})`}
          >
            <span>{t.icon}</span>
            <span style={SHORTCUT}>{t.shortcut}</span>
          </button>
        ))}
      </div>

      {/* Trim tools */}
      <div style={SECTION_LABEL}>Trim</div>
      <div style={GRID}>
        {TRIM_TOOLS.map((t) => (
          <button
            key={t.id}
            style={TOOL_BTN(activeTool === t.id)}
            onClick={() => setActiveTool(t.id as any)}
            title={`${t.label} (${t.shortcut})`}
          >
            <span>{t.icon}</span>
            <span style={SHORTCUT}>{t.shortcut}</span>
          </button>
        ))}
      </div>

      {/* Snap toggle */}
      <button
        style={SNAP_BTN(snapEnabled)}
        onClick={toggleSnap}
        title={`Snap ${snapEnabled ? 'ON' : 'OFF'} (S)`}
      >
        Snap {snapEnabled ? 'ON' : 'OFF'}
      </button>
    </div>
  );
}
