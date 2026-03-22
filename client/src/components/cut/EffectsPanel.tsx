/**
 * MARKER_W10.6 + GAMMA-18: EffectsPanel — per-clip video effects controls.
 *
 * Categorized effects panel with collapsible groups:
 *   - Color: brightness, contrast, saturation, gamma
 *   - Blur/Sharpen: blur, sharpen, denoise
 *   - Transform: vignette, crop (T/B/L/R), flip H/V
 *   - Time: fade in, fade out
 *   - Opacity: opacity
 *
 * Core 5 effects (brightness, contrast, saturation, blur, opacity) persist
 * to store via ClipEffects type. Extended effects use local state until
 * Alpha extends ClipEffects type. Backend EFFECT_DEFS supports all 32.
 */
import { useState, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore, DEFAULT_CLIP_EFFECTS, type ClipEffects } from '../../store/useCutEditorStore';

const PANEL: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
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
  height: 20,
};

const LABEL: CSSProperties = {
  width: 60,
  flexShrink: 0,
  color: '#888',
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
};

const EMPTY: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  color: '#555',
  fontSize: 10,
};

const TOGGLE_BTN = (active: boolean): CSSProperties => ({
  padding: '2px 8px',
  border: `1px solid ${active ? '#888' : '#333'}`,
  borderRadius: 3,
  background: active ? '#222' : '#111',
  color: active ? '#ccc' : '#555',
  fontSize: 9,
  cursor: 'pointer',
});

// ─── Effect definitions by category ───────────────────────────────

type SliderDef = {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  fmt: (v: number) => string;
  storeKey?: keyof ClipEffects; // if present, persists to store
};

type ToggleDef = {
  key: string;
  label: string;
};

type CategoryDef = {
  name: string;
  sliders?: SliderDef[];
  toggles?: ToggleDef[];
};

const pctFmt = (v: number) => `${v > 0 ? '+' : ''}${(v * 100).toFixed(0)}%`;
const pxFmt = (v: number) => v === 0 ? 'off' : `${v.toFixed(1)}px`;
const secFmt = (v: number) => v === 0 ? 'off' : `${v.toFixed(1)}s`;

const CATEGORIES: CategoryDef[] = [
  {
    name: 'Color',
    sliders: [
      { key: 'brightness', label: 'Bright', min: -1, max: 1, step: 0.01, fmt: pctFmt, storeKey: 'brightness' },
      { key: 'contrast', label: 'Contrast', min: -1, max: 1, step: 0.01, fmt: pctFmt, storeKey: 'contrast' },
      { key: 'saturation', label: 'Satur.', min: 0, max: 2, step: 0.01, fmt: (v) => `${(v * 100).toFixed(0)}%`, storeKey: 'saturation' },
      { key: 'gamma', label: 'Gamma', min: 0.2, max: 3, step: 0.05, fmt: (v) => v.toFixed(2) },
    ],
  },
  {
    name: 'Blur / Sharpen',
    sliders: [
      { key: 'blur', label: 'Blur', min: 0, max: 20, step: 0.5, fmt: pxFmt, storeKey: 'blur' },
      { key: 'sharpen', label: 'Sharpen', min: 0, max: 5, step: 0.1, fmt: (v) => v === 0 ? 'off' : v.toFixed(1) },
      { key: 'denoise', label: 'Denoise', min: 0, max: 10, step: 0.5, fmt: (v) => v === 0 ? 'off' : v.toFixed(1) },
    ],
  },
  {
    name: 'Transform',
    sliders: [
      { key: 'vignette', label: 'Vignette', min: 0, max: 1, step: 0.05, fmt: (v) => v === 0 ? 'off' : `${(v * 100).toFixed(0)}%` },
      { key: 'crop_top', label: 'Crop T', min: 0, max: 0.5, step: 0.01, fmt: (v) => v === 0 ? '0' : `${(v * 100).toFixed(0)}%` },
      { key: 'crop_bottom', label: 'Crop B', min: 0, max: 0.5, step: 0.01, fmt: (v) => v === 0 ? '0' : `${(v * 100).toFixed(0)}%` },
      { key: 'crop_left', label: 'Crop L', min: 0, max: 0.5, step: 0.01, fmt: (v) => v === 0 ? '0' : `${(v * 100).toFixed(0)}%` },
      { key: 'crop_right', label: 'Crop R', min: 0, max: 0.5, step: 0.01, fmt: (v) => v === 0 ? '0' : `${(v * 100).toFixed(0)}%` },
    ],
    toggles: [
      { key: 'hflip', label: 'Flip H' },
      { key: 'vflip', label: 'Flip V' },
    ],
  },
  {
    name: 'Time',
    sliders: [
      { key: 'fade_in', label: 'Fade In', min: 0, max: 5, step: 0.1, fmt: secFmt },
      { key: 'fade_out', label: 'Fade Out', min: 0, max: 5, step: 0.1, fmt: secFmt },
    ],
  },
  {
    name: 'Opacity',
    sliders: [
      { key: 'opacity', label: 'Opacity', min: 0, max: 1, step: 0.01, fmt: (v) => `${(v * 100).toFixed(0)}%`, storeKey: 'opacity' },
    ],
  },
];

// Default values for extended effects (not in store)
const EXT_DEFAULTS: Record<string, number> = {
  gamma: 1, sharpen: 0, denoise: 0, vignette: 0,
  crop_top: 0, crop_bottom: 0, crop_left: 0, crop_right: 0,
  hflip: 0, vflip: 0, fade_in: 0, fade_out: 0,
};

// ─── Category header ──────────────────────────────────────────────

function CategoryHeader({ name, open, onToggle }: { name: string; open: boolean; onToggle: () => void }) {
  return (
    <div
      onClick={onToggle}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        padding: '4px 0',
        cursor: 'pointer',
        borderBottom: '1px solid #1a1a1a',
        marginTop: 4,
      }}
    >
      <span style={{ fontSize: 8, color: '#555' }}>{open ? '\u25BE' : '\u25B8'}</span>
      <span style={{ fontSize: 9, fontWeight: 600, color: '#999', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
        {name}
      </span>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────

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

  const storeEffects = selectedClip?.effects ?? DEFAULT_CLIP_EFFECTS;

  // Extended effects — local state per clip (until Alpha extends ClipEffects type)
  const [extEffects, setExtEffects] = useState<Record<string, number>>({ ...EXT_DEFAULTS });
  const [collapsedCats, setCollapsedCats] = useState<Set<string>>(new Set());

  const getValue = useCallback((key: string, storeKey?: keyof ClipEffects): number => {
    if (storeKey) return storeEffects[storeKey];
    return extEffects[key] ?? EXT_DEFAULTS[key] ?? 0;
  }, [storeEffects, extEffects]);

  const handleChange = useCallback((key: string, value: number, storeKey?: keyof ClipEffects) => {
    if (storeKey && selectedClipId) {
      setClipEffects(selectedClipId, { [storeKey]: value });
    } else {
      setExtEffects((prev) => ({ ...prev, [key]: value }));
    }
  }, [selectedClipId, setClipEffects]);

  const handleToggle = useCallback((key: string) => {
    setExtEffects((prev) => ({ ...prev, [key]: prev[key] ? 0 : 1 }));
  }, []);

  const handleReset = useCallback(() => {
    if (selectedClipId) resetClipEffects(selectedClipId);
    setExtEffects({ ...EXT_DEFAULTS });
  }, [selectedClipId, resetClipEffects]);

  const toggleCategory = useCallback((name: string) => {
    setCollapsedCats((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }, []);

  if (!selectedClip) {
    return <div style={EMPTY}>Select a clip to adjust effects</div>;
  }

  const hasStoreChanges = (Object.keys(DEFAULT_CLIP_EFFECTS) as (keyof ClipEffects)[]).some(
    (k) => storeEffects[k] !== DEFAULT_CLIP_EFFECTS[k],
  );
  const hasExtChanges = Object.keys(EXT_DEFAULTS).some((k) => extEffects[k] !== EXT_DEFAULTS[k]);

  return (
    <div style={PANEL} data-testid="effects-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
        <span style={{ fontSize: 10, fontWeight: 600, color: '#aaa', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Effects
        </span>
        {(hasStoreChanges || hasExtChanges) && (
          <button style={RESET_BTN} onClick={handleReset} title="Reset all effects to default">
            Reset
          </button>
        )}
      </div>

      <div style={{ fontSize: 9, color: '#555', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {selectedClip.source_path.split('/').pop()}
      </div>

      {CATEGORIES.map((cat) => {
        const isOpen = !collapsedCats.has(cat.name);
        return (
          <div key={cat.name}>
            <CategoryHeader name={cat.name} open={isOpen} onToggle={() => toggleCategory(cat.name)} />
            {isOpen && (
              <>
                {cat.sliders?.map((s) => (
                  <div key={s.key} style={ROW}>
                    <span style={LABEL}>{s.label}</span>
                    <input
                      type="range"
                      min={s.min}
                      max={s.max}
                      step={s.step}
                      value={getValue(s.key, s.storeKey)}
                      onChange={(e) => handleChange(s.key, parseFloat(e.target.value), s.storeKey)}
                      style={SLIDER}
                    />
                    <span style={VALUE}>{s.fmt(getValue(s.key, s.storeKey))}</span>
                  </div>
                ))}
                {cat.toggles && (
                  <div style={{ display: 'flex', gap: 4, padding: '4px 0' }}>
                    {cat.toggles.map((t) => (
                      <button
                        key={t.key}
                        style={TOGGLE_BTN(!!extEffects[t.key])}
                        onClick={() => handleToggle(t.key)}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
