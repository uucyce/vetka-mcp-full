/**
 * MARKER_C7: HotkeyEditor — full key rebinding UI for CUT NLE.
 *
 * Features:
 *   - Searchable table of all 38+ actions with current binding
 *   - Click-to-rebind with key capture overlay
 *   - Conflict detection (warns if key already assigned)
 *   - Reset single binding or all custom overrides
 *   - Groups: Playback, Marking, Editing, Tools, Markers, Navigation, View, Project
 *
 * Uses: useCutHotkeys persistence (localStorage).
 * Mount: as modal overlay or dockview panel.
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import {
  type CutHotkeyAction,
  type HotkeyPresetName,
  type HotkeyMap,
  PREMIERE_PRESET,
  FCP7_PRESET,
  PRESETS,
  loadPresetName,
  savePresetName,
  loadCustomOverrides,
  saveCustomOverrides,
} from '../../hooks/useCutHotkeys';

// ─── Action registry with groups ───────────────────────────────────

interface ActionDef {
  action: CutHotkeyAction;
  label: string;
  group: string;
}

const ALL_ACTIONS: ActionDef[] = [
  // Playback
  { action: 'playPause', label: 'Play / Pause', group: 'Playback' },
  { action: 'stop', label: 'Stop', group: 'Playback' },
  { action: 'shuttleBack', label: 'Shuttle Back (J)', group: 'Playback' },
  { action: 'shuttleForward', label: 'Shuttle Forward (L)', group: 'Playback' },
  { action: 'frameStepBack', label: 'Frame Step Back', group: 'Playback' },
  { action: 'frameStepForward', label: 'Frame Step Forward', group: 'Playback' },
  { action: 'fiveFrameStepBack', label: '5-Frame Step Back', group: 'Playback' },
  { action: 'fiveFrameStepForward', label: '5-Frame Step Forward', group: 'Playback' },
  { action: 'goToStart', label: 'Go to Start', group: 'Playback' },
  { action: 'goToEnd', label: 'Go to End', group: 'Playback' },
  { action: 'cyclePlaybackRate', label: 'Cycle Playback Rate', group: 'Playback' },
  // Marking
  { action: 'markIn', label: 'Mark In', group: 'Marking' },
  { action: 'markOut', label: 'Mark Out', group: 'Marking' },
  { action: 'clearIn', label: 'Clear In', group: 'Marking' },
  { action: 'clearOut', label: 'Clear Out', group: 'Marking' },
  { action: 'clearInOut', label: 'Clear In/Out', group: 'Marking' },
  { action: 'goToIn', label: 'Go to In Point', group: 'Marking' },
  { action: 'goToOut', label: 'Go to Out Point', group: 'Marking' },
  // Editing
  { action: 'undo', label: 'Undo', group: 'Editing' },
  { action: 'redo', label: 'Redo', group: 'Editing' },
  { action: 'deleteClip', label: 'Delete Clip', group: 'Editing' },
  { action: 'splitClip', label: 'Split at Playhead', group: 'Editing' },
  { action: 'rippleDelete', label: 'Ripple Delete', group: 'Editing' },
  { action: 'selectAll', label: 'Select All', group: 'Editing' },
  { action: 'copy', label: 'Copy', group: 'Editing' },
  { action: 'paste', label: 'Paste', group: 'Editing' },
  { action: 'nudgeLeft', label: 'Nudge Left', group: 'Editing' },
  { action: 'nudgeRight', label: 'Nudge Right', group: 'Editing' },
  // Tools
  { action: 'razorTool', label: 'Razor Tool', group: 'Tools' },
  { action: 'selectTool', label: 'Selection Tool', group: 'Tools' },
  { action: 'insertEdit', label: 'Insert Edit', group: 'Tools' },
  { action: 'overwriteEdit', label: 'Overwrite Edit', group: 'Tools' },
  // Markers
  { action: 'addMarker', label: 'Add Marker', group: 'Markers' },
  { action: 'addComment', label: 'Add Comment Marker', group: 'Markers' },
  // Navigation
  { action: 'prevEditPoint', label: 'Previous Edit Point', group: 'Navigation' },
  { action: 'nextEditPoint', label: 'Next Edit Point', group: 'Navigation' },
  // View
  { action: 'zoomIn', label: 'Zoom In', group: 'View' },
  { action: 'zoomOut', label: 'Zoom Out', group: 'View' },
  { action: 'zoomToFit', label: 'Zoom to Fit', group: 'View' },
  // Project
  { action: 'importMedia', label: 'Import Media', group: 'Project' },
  { action: 'sceneDetect', label: 'Scene Detect', group: 'Project' },
  { action: 'toggleViewMode', label: 'Toggle View Mode', group: 'Project' },
  { action: 'escapeContext', label: 'Escape / Cancel', group: 'Project' },
];

const GROUPS = [...new Set(ALL_ACTIONS.map((a) => a.group))];

// ─── Key event → binding string ────────────────────────────────────

function eventToBinding(e: KeyboardEvent): string {
  const parts: string[] = [];
  if (e.metaKey) parts.push('Cmd');
  if (e.ctrlKey) parts.push('Ctrl');
  if (e.altKey) parts.push('Alt');
  if (e.shiftKey) parts.push('Shift');

  const key = e.key;
  // Skip modifier-only presses
  if (['Meta', 'Control', 'Alt', 'Shift'].includes(key)) return '';

  if (e.code === 'Space') parts.push('Space');
  else if (key === 'ArrowLeft') parts.push('ArrowLeft');
  else if (key === 'ArrowRight') parts.push('ArrowRight');
  else if (key === 'ArrowUp') parts.push('ArrowUp');
  else if (key === 'ArrowDown') parts.push('ArrowDown');
  else if (key === 'Delete') parts.push('Delete');
  else if (key === 'Backspace') parts.push('Backspace');
  else if (key === 'Home') parts.push('Home');
  else if (key === 'End') parts.push('End');
  else if (key === 'Enter') parts.push('Enter');
  else if (key === 'Escape') parts.push('Escape');
  else if (key === 'Tab') parts.push('Tab');
  else if (/^F\d+$/i.test(key)) parts.push(key);
  else parts.push(key.length === 1 ? key.toLowerCase() : key);

  return parts.join('+');
}

// ─── Styles ────────────────────────────────────────────────────────

const OVERLAY: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.85)',
  zIndex: 9999,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexDirection: 'column',
};

const PANEL: React.CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: 6,
  width: 520,
  maxHeight: '80vh',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
};

const HEADER: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '8px 12px',
  borderBottom: '1px solid #222',
  background: '#0a0a0a',
};

const ROW: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  padding: '3px 12px',
  borderBottom: '1px solid #1a1a1a',
  fontSize: 10,
  fontFamily: 'system-ui, sans-serif',
  cursor: 'pointer',
};

const BINDING_BADGE: React.CSSProperties = {
  background: '#1a1a1a',
  border: '1px solid #333',
  borderRadius: 3,
  padding: '1px 6px',
  fontSize: 10,
  fontFamily: 'monospace',
  color: '#ccc',
  minWidth: 40,
  textAlign: 'center',
};

const GROUP_HEADER: React.CSSProperties = {
  padding: '6px 12px 2px',
  fontSize: 8,
  fontFamily: 'monospace',
  color: '#555',
  textTransform: 'uppercase',
  letterSpacing: 0.5,
  background: '#0a0a0a',
};

// ─── Component ─────────────────────────────────────────────────────

interface HotkeyEditorProps {
  onClose: () => void;
}

export default function HotkeyEditor({ onClose }: HotkeyEditorProps) {
  const [presetName, setPresetName] = useState<HotkeyPresetName>(loadPresetName);
  const [customOverrides, setCustomOverrides] = useState<HotkeyMap>(loadCustomOverrides);
  const [search, setSearch] = useState('');
  const [capturing, setCapturing] = useState<CutHotkeyAction | null>(null);
  const [conflict, setConflict] = useState<{ action: CutHotkeyAction; binding: string } | null>(null);
  const captureRef = useRef<HTMLDivElement>(null);

  // Get effective binding for an action
  const getBinding = useCallback((action: CutHotkeyAction): string => {
    if (customOverrides[action]) return customOverrides[action]!;
    const preset = presetName === 'custom' ? PREMIERE_PRESET : (PRESETS[presetName] || PREMIERE_PRESET);
    return preset[action] || '';
  }, [presetName, customOverrides]);

  // Check for conflicts
  const findConflict = useCallback((binding: string, excludeAction: CutHotkeyAction): CutHotkeyAction | null => {
    for (const def of ALL_ACTIONS) {
      if (def.action === excludeAction) continue;
      if (getBinding(def.action) === binding) return def.action;
    }
    return null;
  }, [getBinding]);

  // Key capture handler
  useEffect(() => {
    if (!capturing) return;

    const onKeyDown = (e: KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (e.key === 'Escape') {
        setCapturing(null);
        setConflict(null);
        return;
      }

      const binding = eventToBinding(e);
      if (!binding) return; // modifier-only press

      // Check conflict
      const conflictAction = findConflict(binding, capturing);
      if (conflictAction) {
        setConflict({ action: conflictAction, binding });
        // Still apply — user can see the conflict warning
      } else {
        setConflict(null);
      }

      // Save override
      const next = { ...customOverrides, [capturing]: binding };
      setCustomOverrides(next);
      saveCustomOverrides(next);

      // If not already on custom preset, switch
      if (presetName !== 'custom') {
        setPresetName('custom');
        savePresetName('custom');
        window.dispatchEvent(new StorageEvent('storage', {
          key: 'cut_hotkey_preset',
          newValue: 'custom',
        }));
      }

      // Notify hotkey system
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'cut_hotkey_custom',
        newValue: JSON.stringify(next),
      }));

      setCapturing(null);
    };

    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, [capturing, customOverrides, presetName, findConflict]);

  // Reset single binding
  const resetBinding = useCallback((action: CutHotkeyAction) => {
    const next = { ...customOverrides };
    delete next[action];
    setCustomOverrides(next);
    saveCustomOverrides(next);
    window.dispatchEvent(new StorageEvent('storage', {
      key: 'cut_hotkey_custom',
      newValue: JSON.stringify(next),
    }));
  }, [customOverrides]);

  // Reset all
  const resetAll = useCallback(() => {
    setCustomOverrides({});
    saveCustomOverrides({});
    window.dispatchEvent(new StorageEvent('storage', {
      key: 'cut_hotkey_custom',
      newValue: '{}',
    }));
  }, []);

  // Filter actions by search
  const searchLower = search.toLowerCase();
  const filtered = search
    ? ALL_ACTIONS.filter((a) =>
        a.label.toLowerCase().includes(searchLower) ||
        a.action.toLowerCase().includes(searchLower) ||
        getBinding(a.action).toLowerCase().includes(searchLower)
      )
    : ALL_ACTIONS;

  // Group filtered actions
  const grouped = GROUPS.map((g) => ({
    group: g,
    actions: filtered.filter((a) => a.group === g),
  })).filter((g) => g.actions.length > 0);

  return (
    <div style={OVERLAY} onClick={onClose}>
      <div style={PANEL} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={HEADER}>
          <span style={{ color: '#ccc', fontSize: 12, fontWeight: 600 }}>Keyboard Shortcuts</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              onClick={resetAll}
              style={{
                background: 'none',
                border: '1px solid #333',
                borderRadius: 3,
                color: '#888',
                fontSize: 9,
                padding: '2px 8px',
                cursor: 'pointer',
                fontFamily: 'monospace',
              }}
            >
              Reset All
            </button>
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: '#555',
                fontSize: 14,
                cursor: 'pointer',
                padding: '0 4px',
              }}
            >
              x
            </button>
          </div>
        </div>

        {/* MARKER_GAMMA-P3.4: Preset selector */}
        <div style={{ padding: '4px 12px', borderBottom: '1px solid #222', display: 'flex', gap: 4, alignItems: 'center' }}>
          <span style={{ fontSize: 8, color: '#555', marginRight: 4 }}>PRESET:</span>
          {(['premiere', 'fcp7', 'custom'] as const).map((p) => (
            <button
              key={p}
              onClick={() => { setPresetName(p); savePresetName(p); window.dispatchEvent(new StorageEvent('storage', { key: 'cut_hotkey_preset', newValue: p })); }}
              style={{
                background: presetName === p ? '#222' : 'none',
                border: '1px solid ' + (presetName === p ? '#555' : '#333'),
                borderRadius: 3,
                color: presetName === p ? '#ccc' : '#666',
                fontSize: 8,
                padding: '2px 8px',
                cursor: 'pointer',
                textTransform: 'uppercase',
              }}
            >
              {p === 'premiere' ? 'Premiere' : p === 'fcp7' ? 'FCP7' : 'Custom'}
            </button>
          ))}
        </div>

        {/* Search */}
        <div style={{ padding: '6px 12px', borderBottom: '1px solid #222' }}>
          <input
            type="text"
            placeholder="Search actions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%',
              background: '#0a0a0a',
              border: '1px solid #333',
              borderRadius: 3,
              color: '#ccc',
              fontSize: 10,
              fontFamily: 'monospace',
              padding: '4px 8px',
              outline: 'none',
            }}
          />
        </div>

        {/* Action list */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {grouped.map(({ group, actions }) => (
            <div key={group}>
              <div style={GROUP_HEADER}>{group}</div>
              {actions.map((def) => {
                const binding = getBinding(def.action);
                const isCustom = !!customOverrides[def.action];
                const isCapturing = capturing === def.action;

                return (
                  <div
                    key={def.action}
                    style={{
                      ...ROW,
                      background: isCapturing ? '#222' : undefined,
                    }}
                    onClick={() => {
                      setCapturing(def.action);
                      setConflict(null);
                    }}
                  >
                    <span style={{ flex: 1, color: '#ccc' }}>{def.label}</span>
                    {isCapturing ? (
                      <span style={{ ...BINDING_BADGE, borderColor: '#999', color: '#999' }}>
                        Press key...
                      </span>
                    ) : (
                      <span style={{
                        ...BINDING_BADGE,
                        color: isCustom ? '#fff' : '#ccc',
                      }}>
                        {binding || '—'}
                      </span>
                    )}
                    {isCustom && !isCapturing && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          resetBinding(def.action);
                        }}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#555',
                          fontSize: 9,
                          cursor: 'pointer',
                          marginLeft: 4,
                          padding: '0 2px',
                        }}
                        title="Reset to preset default"
                      >
                        x
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* Conflict warning */}
        {conflict && (
          <div style={{
            padding: '4px 12px',
            background: '#1a1a1a',
            borderTop: '1px solid #333',
            fontSize: 9,
            color: '#999',
            fontFamily: 'monospace',
          }}>
            Conflict: "{conflict.binding}" already assigned to{' '}
            {ALL_ACTIONS.find((a) => a.action === conflict.action)?.label || conflict.action}
          </div>
        )}

        {/* Footer: current preset */}
        <div style={{
          padding: '4px 12px',
          borderTop: '1px solid #222',
          background: '#0a0a0a',
          fontSize: 8,
          color: '#555',
          fontFamily: 'monospace',
          display: 'flex',
          justifyContent: 'space-between',
        }}>
          <span>Preset: {presetName}</span>
          <span>{ALL_ACTIONS.length} actions</span>
        </div>
      </div>
    </div>
  );
}
