/**
 * MARKER_192.2: TimelineToolbar — minimal state-only toolbar above timeline.
 *
 * Principle: Toolbar controls STATE, not ACTIONS.
 * See: RECON_UI_LAYOUT_GROK_2026-03-19.md §3
 *
 * Contains ONLY:
 *   - Snap toggle (magnet icon, hotkey S)
 *   - Linked Selection toggle (chain icon)
 *   - Zoom slider (right side)
 *   - Parallel timeline toggle (|| when 2+ tabs)
 *
 * Removed (MARKER_192.2):
 *   - V/C tool buttons → cursor modes via hotkeys only
 *   - Export button → File menu (future task)
 *   - Undo was never here (Cmd+Z)
 */
import { type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import TimelineDisplayControls from './TimelineDisplayControls';

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

const TOGGLE_BTN: CSSProperties = {
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

function ChainIcon({ active }: { active: boolean }) {
  const color = active ? '#ccc' : '#444';
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M6.5 4A2.5 2.5 0 004 6.5v1A2.5 2.5 0 006.5 10h1a.5.5 0 000-1h-1A1.5 1.5 0 015 7.5v-1A1.5 1.5 0 016.5 5h1a.5.5 0 000-1h-1zM8.5 6a.5.5 0 000 1h1A1.5 1.5 0 0111 8.5v1A1.5 1.5 0 019.5 11h-1a.5.5 0 000 1h1a2.5 2.5 0 002.5-2.5v-1A2.5 2.5 0 009.5 6h-1z"
        fill={color}
      />
      <path d="M6 8h4" stroke={color} strokeWidth="1" />
    </svg>
  );
}

const ZOOM_SLIDER: CSSProperties = {
  width: 80,
  height: 3,
  appearance: 'none' as const,
  background: '#222',
  borderRadius: 2,
  outline: 'none',
  cursor: 'pointer',
};

export default function TimelineToolbar() {
  const snapEnabled = useCutEditorStore((s) => s.snapEnabled ?? true);
  const toggleSnap = useCutEditorStore((s) => s.toggleSnap);
  const linkedSelection = useCutEditorStore((s) => s.linkedSelection);
  const toggleLinkedSelection = useCutEditorStore((s) => s.toggleLinkedSelection);
  // Zoom
  const zoom = useCutEditorStore((s) => s.zoom);
  const setZoom = useCutEditorStore((s) => s.setZoom);

  return (
    <div style={ROOT}>
      {/* Snap toggle */}
      <button
        style={{
          ...TOGGLE_BTN,
          background: snapEnabled ? '#1a1a1a' : 'none',
        }}
        onClick={toggleSnap}
        title={`Snap ${snapEnabled ? 'ON' : 'OFF'} (S)`}
      >
        <MagnetIcon active={snapEnabled} />
      </button>

      <div style={{ width: 1, height: 14, background: '#222' }} />

      {/* MARKER_DISPLAY-CTRL: Timeline Display Controls popup */}
      <TimelineDisplayControls />

      <div style={{ width: 1, height: 14, background: '#222' }} />

      {/* Linked Selection toggle */}
      <button
        style={{
          ...TOGGLE_BTN,
          background: linkedSelection ? '#1a1a1a' : 'none',
        }}
        onClick={toggleLinkedSelection}
        title={`Linked Selection ${linkedSelection ? 'ON' : 'OFF'}`}
      >
        <ChainIcon active={linkedSelection} />
      </button>

      {/* MARKER_LAYOUT-2: HotkeyPresetSelector + WorkspacePresets moved to MenuBar
         (Edit > Keyboard Shortcuts, Window > Workspaces) */}

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Zoom slider */}
      <input
        type="range"
        min={10}
        max={300}
        value={zoom}
        onChange={(e) => setZoom(Number(e.target.value))}
        style={ZOOM_SLIDER}
        title={`Zoom: ${zoom}px/s`}
      />
    </div>
  );
}
