/**
 * MARKER_C5 + GAMMA-WS1: Visual workspace preset picker.
 *
 * Compact icon strip with layout pictograms. Each button shows:
 *   - SVG icon representing the layout structure
 *   - Label below
 *   - Active state: brighter border + filled background
 *   - Shortcut hint on hover
 *
 * Clicking a preset: save current → load target → update store.
 * Double-click Custom: save current as Custom.
 */
import { useDockviewStore, type WorkspacePresetName } from '../../store/useDockviewStore';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { PRESET_BUILDERS } from './presetBuilders';

interface PresetDef {
  name: WorkspacePresetName;
  label: string;
  shortcut: string;
  // SVG path for layout pictogram (12x10 viewBox)
  icon: string;
}

const PRESETS: PresetDef[] = [
  {
    name: 'editing',
    label: 'Edit',
    shortcut: '⌥⇧1',
    // Two columns top + timeline bottom
    icon: 'M0 0h5v6H0zM6 0h6v6H6zM0 7h12v3H0z',
  },
  {
    name: 'color',
    label: 'Color',
    shortcut: '⌥⇧2',
    // Three columns: scopes left, viewer center, controls right
    icon: 'M0 0h3v10H0zM4 0h5v6H4zM4 7h5v3H4zM10 0h2v10h-2z',
  },
  {
    name: 'audio',
    label: 'Audio',
    shortcut: '⌥⇧3',
    // Mixer columns + timeline
    icon: 'M0 0h2v7H0zM3 0h2v7H3zM6 0h2v7H6zM9 0h3v7H9zM0 8h12v2H0z',
  },
  {
    name: 'custom',
    label: 'Custom',
    shortcut: '⌥⇧4',
    // Grid pattern
    icon: 'M0 0h5v4H0zM6 0h6v4H6zM0 5h4v5H0zM5 5h3v5H5zM9 5h3v5H9z',
  },
];

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
      // MARKER_GAMMA-R2: No saved layout — build via API instead of reload
      setActivePreset(name);
      try {
        apiRef.clear();
        const builder = PRESET_BUILDERS[name] || PRESET_BUILDERS.editing;
        builder(apiRef, '');
        requestAnimationFrame(() => {
          try { saveLayout(name, apiRef.toJSON()); } catch { /* ok */ }
        });
      } catch { /* builder failed */ }
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
    <div style={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      {PRESETS.map(({ name, label, shortcut, icon }) => {
        const isActive = activePreset === name;
        return (
          <button
            key={name}
            onClick={() => handleSwitch(name)}
            onDoubleClick={name === 'custom' ? handleSaveCustom : undefined}
            title={`${label} (${shortcut})${name === 'custom' ? ' — double-click to save' : ''}`}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 1,
              padding: '2px 5px',
              background: isActive ? '#1a1a1a' : 'transparent',
              border: '1px solid',
              borderColor: isActive ? '#555' : 'transparent',
              borderRadius: 3,
              cursor: 'pointer',
              transition: 'background 0.1s, border-color 0.1s',
              minWidth: 32,
            }}
          >
            <svg
              width={18}
              height={14}
              viewBox="0 0 12 10"
              style={{ display: 'block' }}
            >
              <path
                d={icon}
                fill={isActive ? '#888' : '#444'}
                fillRule="evenodd"
              />
            </svg>
            <span
              style={{
                fontSize: 7,
                fontFamily: 'system-ui, -apple-system, sans-serif',
                color: isActive ? '#ccc' : '#555',
                lineHeight: 1,
                letterSpacing: '0.3px',
              }}
            >
              {label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
