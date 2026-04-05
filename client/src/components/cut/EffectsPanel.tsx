/**
 * MARKER_W10.6: EffectsPanel — per-clip video effects controls.
 *
 * Shows when a clip is selected. Sliders for:
 *   brightness (-1..1), contrast (-1..1), saturation (0..2),
 *   blur (0..20px), opacity (0..1)
 *
 * Values stored in TimelineClip.effects, rendered via backend filter_complex.
 * Reset button restores defaults.
 */
import { useCallback, type CSSProperties } from 'react';
import { useCutEditorStore, DEFAULT_CLIP_EFFECTS, type ClipEffects } from '../../store/useCutEditorStore';

const PANEL: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  padding: 8,
  height: '100%',
  overflow: 'auto',
  fontFamily: 'system-ui, -apple-system, sans-serif',
  fontSize: 10,
  color: '#ccc',
  background: '#0a0a0a',
};

const ROW: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
};

const LABEL: CSSProperties = {
  width: 64,
  flexShrink: 0,
  color: '#888',
  textTransform: 'uppercase',
  letterSpacing: '0.3px',
  fontSize: 9,
};

const SLIDER: CSSProperties = {
  flex: 1,
  height: 3,
  appearance: 'none',
  background: '#333',
  borderRadius: 2,
  outline: 'none',
  cursor: 'pointer',
};

const VALUE: CSSProperties = {
  width: 36,
  textAlign: 'right',
  color: '#aaa',
  fontSize: 9,
  fontVariantNumeric: 'tabular-nums',
};

const RESET_BTN: CSSProperties = {
  padding: '3px 8px',
  border: '1px solid #333',
  borderRadius: 3,
  background: '#111',
  color: '#888',
  fontSize: 9,
  cursor: 'pointer',
  textTransform: 'uppercase',
  letterSpacing: '0.3px',
};

const EMPTY: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  color: '#555',
  fontSize: 10,
};

type SliderDef = {
  key: keyof ClipEffects;
  label: string;
  min: number;
  max: number;
  step: number;
  fmt: (v: number) => string;
};

const SLIDERS: SliderDef[] = [
  { key: 'brightness', label: 'Brightness', min: -1, max: 1, step: 0.01, fmt: (v) => `${v > 0 ? '+' : ''}${(v * 100).toFixed(0)}%` },
  { key: 'contrast', label: 'Contrast', min: -1, max: 1, step: 0.01, fmt: (v) => `${v > 0 ? '+' : ''}${(v * 100).toFixed(0)}%` },
  { key: 'saturation', label: 'Saturation', min: 0, max: 2, step: 0.01, fmt: (v) => `${(v * 100).toFixed(0)}%` },
  { key: 'blur', label: 'Blur', min: 0, max: 20, step: 0.5, fmt: (v) => v === 0 ? 'off' : `${v.toFixed(1)}px` },
  { key: 'opacity', label: 'Opacity', min: 0, max: 1, step: 0.01, fmt: (v) => `${(v * 100).toFixed(0)}%` },
];

export default function EffectsPanel() {
  const selectedClipId = useCutEditorStore((s) => s.selectedClipId);
  const lanes = useCutEditorStore((s) => s.lanes);
  const setClipEffects = useCutEditorStore((s) => s.setClipEffects);
  const resetClipEffects = useCutEditorStore((s) => s.resetClipEffects);

  // Find selected clip
  let selectedClip = null;
  if (selectedClipId) {
    for (const lane of lanes) {
      const found = lane.clips.find((c) => c.clip_id === selectedClipId);
      if (found) { selectedClip = found; break; }
    }
  }

  const effects = selectedClip?.effects ?? DEFAULT_CLIP_EFFECTS;

  const handleChange = useCallback((key: keyof ClipEffects, value: number) => {
    if (selectedClipId) setClipEffects(selectedClipId, { [key]: value });
  }, [selectedClipId, setClipEffects]);

  const handleReset = useCallback(() => {
    if (selectedClipId) resetClipEffects(selectedClipId);
  }, [selectedClipId, resetClipEffects]);

  if (!selectedClip) {
    return <div style={EMPTY}>Select a clip to adjust effects</div>;
  }

  const hasChanges = SLIDERS.some((s) => effects[s.key] !== DEFAULT_CLIP_EFFECTS[s.key]);

  return (
    <div style={PANEL}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontSize: 10, fontWeight: 600, color: '#aaa', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Video Effects
        </span>
        {hasChanges && (
          <button style={RESET_BTN} onClick={handleReset} title="Reset all effects to default">
            Reset
          </button>
        )}
      </div>

      <div style={{ fontSize: 9, color: '#555', marginBottom: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {selectedClip.source_path.split('/').pop()}
      </div>

      {SLIDERS.map((s) => (
        <div key={s.key} style={ROW}>
          <span style={LABEL}>{s.label}</span>
          <input
            type="range"
            min={s.min}
            max={s.max}
            step={s.step}
            value={effects[s.key]}
            onChange={(e) => handleChange(s.key, parseFloat(e.target.value))}
            style={SLIDER}
          />
          <span style={VALUE}>{s.fmt(effects[s.key])}</span>
        </div>
      ))}
    </div>
  );
}
