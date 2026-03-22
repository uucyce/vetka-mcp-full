/**
 * MARKER_C5: Workspace preset switcher — Editing / Color / Audio / Custom.
 *
 * Compact button bar. Clicking a preset:
 *   1. Saves current layout to current preset name
 *   2. Loads target preset layout via dockview API
 *   3. Updates activePreset in store
 *
 * Requires: dockview API ref exposed via useDockviewStore.apiRef.
 */
import { useDockviewStore, type WorkspacePresetName } from '../../store/useDockviewStore';
import { useCutEditorStore } from '../../store/useCutEditorStore';

const PRESETS: { name: WorkspacePresetName; label: string }[] = [
  { name: 'editing', label: 'Edit' },
  { name: 'color', label: 'Color' },
  { name: 'audio', label: 'Audio' },
  { name: 'custom', label: 'Custom' },
];

const btnBase: React.CSSProperties = {
  background: 'none',
  border: '1px solid #333',
  borderRadius: 3,
  fontSize: 9,
  fontFamily: 'monospace',
  padding: '1px 6px',
  cursor: 'pointer',
  height: 18,
  transition: 'background 0.1s, color 0.1s',
};

export default function WorkspacePresets() {
  const activePreset = useDockviewStore((s) => s.activePreset);
  const setActivePreset = useDockviewStore((s) => s.setActivePreset);
  const loadLayout = useDockviewStore((s) => s.loadLayout);
  const saveLayout = useDockviewStore((s) => s.saveLayout);
  const apiRef = useDockviewStore((s) => s.apiRef);

  const saveFocusForPreset = useDockviewStore((s) => s.saveFocusForPreset);
  const getFocusForPreset = useDockviewStore((s) => s.getFocusForPreset);

  const handleSwitch = (name: WorkspacePresetName) => {
    if (name === activePreset) return;

    // MARKER_GAMMA-12: Save current focus before switching
    const currentFocus = useCutEditorStore.getState().focusedPanel;
    saveFocusForPreset(activePreset, currentFocus);

    // Save current layout before switching
    if (apiRef) {
      try {
        const currentJson = apiRef.toJSON();
        saveLayout(activePreset, currentJson);
      } catch { /* ok */ }
    }

    // Load target preset
    const saved = loadLayout(name);
    if (saved && apiRef) {
      try {
        apiRef.fromJSON(saved);
      } catch {
        return;
      }
      setActivePreset(name);
      // MARKER_GAMMA-12: Restore focus for target preset
      const targetFocus = getFocusForPreset(name);
      if (targetFocus) {
        useCutEditorStore.getState().setFocusedPanel(targetFocus as any);
      }
    } else {
      // MARKER_C5: No saved layout — reload to build preset-specific default
      setActivePreset(name);
      window.location.reload();
    }
  };

  const handleSaveCustom = () => {
    if (!apiRef) return;
    try {
      const json = apiRef.toJSON();
      saveLayout('custom', json);
      setActivePreset('custom');
    } catch { /* ok */ }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      <span style={{ color: '#555', fontSize: 8, fontFamily: 'monospace', marginRight: 2 }}>WS:</span>
      {PRESETS.map(({ name, label }) => (
        <button
          key={name}
          onClick={() => handleSwitch(name)}
          onDoubleClick={name === 'custom' ? handleSaveCustom : undefined}
          style={{
            ...btnBase,
            background: activePreset === name ? '#1a1a1a' : 'none',
            color: activePreset === name ? '#ccc' : '#555',
            borderColor: activePreset === name ? '#555' : '#333',
          }}
          title={name === 'custom' ? 'Double-click to save current layout as Custom' : `Switch to ${label} workspace`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
