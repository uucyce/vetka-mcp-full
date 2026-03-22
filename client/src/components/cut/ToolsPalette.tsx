/**
 * MARKER_GAMMA-23: Tools Palette — Premiere Pro style vertical column.
 *
 * Single-column strip of tool icons with shortcut letters.
 * Narrow (~36px), dockable/floating. Can be dismissed — editors use hotkeys.
 * Window → Tools to reopen.
 *
 * Premiere layout: vertical column left of timeline.
 * Each tool = one row: icon centered, shortcut letter overlay.
 * Monochrome only.
 */
import { type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

type ToolDef = {
  id: string;
  icon: string;
  shortcut: string;
  title: string;
};

// Premiere Pro order: Selection, Track Select, Ripple Edit, Rolling Edit,
// Rate Stretch, Razor, Slip, Slide, Pen, Hand, Zoom, Type
// We map to our available tools:
const ALL_TOOLS: ToolDef[] = [
  { id: 'selection', icon: '\u2B06', shortcut: 'A', title: 'Arrow Tool' },
  { id: 'razor',     icon: '\u2702', shortcut: 'B', title: 'Blade Tool' },
  { id: 'ripple',    icon: '\u21C4', shortcut: 'R', title: 'Ripple Edit' },
  { id: 'roll',      icon: '\u21CB', shortcut: 'N', title: 'Rolling Edit' },
  { id: 'slip',      icon: '\u2194', shortcut: 'S', title: 'Slip Tool' },
  { id: 'slide',     icon: '\u21D4', shortcut: 'U', title: 'Slide Tool' },
  { id: 'hand',      icon: '\u270B', shortcut: 'H', title: 'Hand Tool' },
  { id: 'zoom',      icon: '\u2315', shortcut: 'Z', title: 'Zoom Tool' },
];

const PANEL: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: 1,
  padding: '4px 2px',
  height: '100%',
  overflow: 'auto',
  background: '#0d0d0d',
  width: 36,
  minWidth: 36,
};

const TOOL_BTN = (active: boolean): CSSProperties => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  position: 'relative',
  width: 28,
  height: 28,
  border: 'none',
  borderRadius: 3,
  background: active ? '#222' : 'transparent',
  color: active ? '#fff' : '#888',
  cursor: 'pointer',
  fontSize: 15,
  padding: 0,
  outline: active ? '1px solid #555' : 'none',
});

const SHORTCUT_BADGE: CSSProperties = {
  position: 'absolute',
  bottom: 1,
  right: 2,
  fontSize: 7,
  fontFamily: 'monospace',
  color: '#555',
  lineHeight: 1,
};

const DIVIDER: CSSProperties = {
  width: 20,
  height: 1,
  background: '#222',
  margin: '3px 0',
  flexShrink: 0,
};

const SNAP_BTN = (active: boolean): CSSProperties => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 28,
  height: 20,
  border: 'none',
  borderRadius: 3,
  background: active ? '#222' : 'transparent',
  color: active ? '#ccc' : '#555',
  cursor: 'pointer',
  fontSize: 8,
  fontFamily: 'monospace',
  fontWeight: 600,
  outline: active ? '1px solid #555' : 'none',
});

export default function ToolsPalette() {
  const activeTool = useCutEditorStore((s) => s.activeTool);
  const setActiveTool = useCutEditorStore((s) => s.setActiveTool);
  const snapEnabled = useCutEditorStore((s) => s.snapEnabled ?? true);
  const toggleSnap = useCutEditorStore((s) => s.toggleSnap);

  return (
    <div style={PANEL} data-testid="tools-palette">
      {ALL_TOOLS.map((t, i) => (
        <div key={t.id}>
          <button
            style={TOOL_BTN(activeTool === t.id)}
            onClick={() => setActiveTool(t.id as any)}
            title={`${t.title} (${t.shortcut})`}
          >
            {t.icon}
            <span style={SHORTCUT_BADGE as any}>{t.shortcut}</span>
          </button>
          {/* Divider after primary tools (Arrow, Blade) and before Hand/Zoom */}
          {(i === 1 || i === 5) && <div style={DIVIDER} />}
        </div>
      ))}
      <div style={DIVIDER} />
      {/* Snap toggle */}
      <button
        style={SNAP_BTN(snapEnabled)}
        onClick={toggleSnap}
        title={`Snap ${snapEnabled ? 'ON' : 'OFF'} (S)`}
      >
        {snapEnabled ? 'S' : 's'}
      </button>
    </div>
  );
}
