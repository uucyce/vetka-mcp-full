/**
 * MARKER_C6.1: Hotkey preset selector — dropdown to switch between Premiere/FCP7/Custom.
 * Reads/writes preset name via useCutHotkeys persistence (localStorage).
 * Compact: 90px dropdown, dark theme, monochrome.
 */
import { useState, useCallback, lazy, Suspense } from 'react';
import {
  type HotkeyPresetName,
  loadPresetName,
  savePresetName,
} from '../../hooks/useCutHotkeys';

const HotkeyEditor = lazy(() => import('./HotkeyEditor'));

const PRESET_LABELS: Record<HotkeyPresetName, string> = {
  premiere: 'Premiere',
  fcp7: 'FCP 7',
  custom: 'Custom',
};

const PRESET_OPTIONS: HotkeyPresetName[] = ['premiere', 'fcp7', 'custom'];

const selectStyle: React.CSSProperties = {
  background: '#1a1a1a',
  color: '#ccc',
  border: '1px solid #333',
  borderRadius: 3,
  padding: '2px 4px',
  fontSize: 10,
  fontFamily: 'monospace',
  cursor: 'pointer',
  outline: 'none',
  height: 20,
};

export default function HotkeyPresetSelector() {
  const [preset, setPreset] = useState<HotkeyPresetName>(loadPresetName);
  const [editorOpen, setEditorOpen] = useState(false);

  const onChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value as HotkeyPresetName;
    setPreset(value);
    savePresetName(value);
    // Force re-mount of hotkey listener by dispatching storage event
    window.dispatchEvent(new StorageEvent('storage', {
      key: 'cut_hotkey_preset',
      newValue: value,
    }));
  }, []);

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ color: '#666', fontSize: 9, fontFamily: 'monospace' }}>Keys:</span>
        <select value={preset} onChange={onChange} style={selectStyle}>
          {PRESET_OPTIONS.map((p) => (
            <option key={p} value={p}>{PRESET_LABELS[p]}</option>
          ))}
        </select>
        <button
          onClick={() => setEditorOpen(true)}
          style={{
            background: 'none',
            border: '1px solid #333',
            borderRadius: 3,
            color: '#888',
            fontSize: 9,
            fontFamily: 'monospace',
            padding: '1px 5px',
            cursor: 'pointer',
            height: 18,
          }}
          title="Edit keyboard shortcuts"
        >
          ...
        </button>
      </div>
      {editorOpen && (
        <Suspense fallback={null}>
          <HotkeyEditor onClose={() => setEditorOpen(false)} />
        </Suspense>
      )}
    </>
  );
}
