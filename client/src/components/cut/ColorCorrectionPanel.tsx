/**
 * MARKER_B16: Color Correction Panel — 3-way color corrector + curves.
 *
 * Sections:
 * 1. Basic: Exposure, White Balance, Saturation, Hue
 * 2. Lift/Gamma/Gain: Per-channel RGB sliders for shadows/mids/highlights
 * 3. Curves: Preset selector + custom luminance curves (future: per-channel)
 *
 * Stores color effects in clip.effects.video_effects via effects engine.
 * Preview via CSS filters (brightness/contrast/saturate/hue-rotate).
 * Render via FFmpeg eq/colorbalance/curves filters.
 */
import { useState, useCallback, useEffect, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import ColorWheel from './ColorWheel';

// ─── Types ───

interface ColorState {
  exposure: number;      // stops: -4..+4
  temperature: number;   // K: 2000..12000
  saturation: number;    // 0..3
  hue: number;           // degrees: -180..180
  contrast: number;      // 0..3
  // Lift (shadows)
  liftR: number; liftG: number; liftB: number;
  // Midtone (gamma)
  midR: number; midG: number; midB: number;
  // Gain (highlights)
  gainR: number; gainG: number; gainB: number;
  // Curves
  curvesPreset: string;
}

const DEFAULT_COLOR: ColorState = {
  exposure: 0, temperature: 6500, saturation: 1.0, hue: 0, contrast: 1.0,
  liftR: 0, liftG: 0, liftB: 0,
  midR: 0, midG: 0, midB: 0,
  gainR: 0, gainG: 0, gainB: 0,
  curvesPreset: 'none',
};

const CURVE_PRESETS = [
  { id: 'none', label: 'None' },
  { id: 'lighter', label: 'Lighter' },
  { id: 'darker', label: 'Darker' },
  { id: 'increase_contrast', label: 'High Contrast' },
  { id: 'decrease_contrast', label: 'Low Contrast' },
  { id: 'strong_contrast', label: 'Strong Contrast' },
  { id: 'negative', label: 'Negative' },
  { id: 'vintage', label: 'Vintage' },
  { id: 'cross_process', label: 'Cross Process' },
];

// ─── Styles ───

const PANEL: CSSProperties = {
  height: '100%',
  overflow: 'auto',
  background: '#0d0d0d',
  fontFamily: 'system-ui',
  fontSize: 11,
  color: '#ccc',
};

const SECTION: CSSProperties = {
  padding: '8px 10px',
  borderBottom: '1px solid #1a1a1a',
};

const SECTION_TITLE: CSSProperties = {
  fontSize: 10,
  color: '#555',
  textTransform: 'uppercase' as const,
  letterSpacing: 1,
  marginBottom: 8,
  display: 'flex',
  justifyContent: 'space-between',
};

const ROW: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  marginBottom: 5,
  gap: 6,
};

const LABEL: CSSProperties = {
  color: '#666',
  fontSize: 10,
  width: 65,
  flexShrink: 0,
};

const SLIDER: CSSProperties = { flex: 1, minWidth: 0 };

const VALUE: CSSProperties = {
  color: '#ccc',
  fontFamily: '"JetBrains Mono", monospace',
  fontSize: 10,
  width: 42,
  textAlign: 'right' as const,
};

const SELECT: CSSProperties = {
  background: '#1a1a1a',
  color: '#ccc',
  border: '1px solid #333',
  borderRadius: 4,
  padding: '4px 8px',
  fontSize: 11,
  fontFamily: 'system-ui',
  cursor: 'pointer',
  width: '100%',
};

const RESET_BTN: CSSProperties = {
  background: 'none',
  border: 'none',
  color: '#555',
  cursor: 'pointer',
  fontSize: 9,
  fontFamily: 'system-ui',
};

// ─── Component ───

export default function ColorCorrectionPanel() {
  const selectedClipId = useCutEditorStore((s) => s.selectedClipId);
  const lanes = useCutEditorStore((s) => s.lanes);

  const selectedClip = lanes
    .flatMap((l) => l.clips || [])
    .find((c) => c.clip_id === selectedClipId);

  const clipColor = (selectedClip as any)?.color_correction as Partial<ColorState> | undefined;
  const [color, setColor] = useState<ColorState>({ ...DEFAULT_COLOR, ...clipColor });

  useEffect(() => {
    const cc = (selectedClip as any)?.color_correction;
    setColor({ ...DEFAULT_COLOR, ...(cc || {}) });
  }, [selectedClipId, selectedClip]);

  const updateField = useCallback((field: keyof ColorState, value: number | string) => {
    setColor((prev) => ({ ...prev, [field]: value }));
  }, []);

  const applyColor = useCallback(() => {
    if (!selectedClipId) return;
    const store = useCutEditorStore.getState();
    const updatedLanes = store.lanes.map((lane) => ({
      ...lane,
      clips: (lane.clips || []).map((clip) => {
        if (clip.clip_id !== selectedClipId) return clip;
        return { ...clip, color_correction: color };
      }),
    }));
    store.setLanes(updatedLanes);
  }, [selectedClipId, color]);

  const resetColor = useCallback(() => {
    setColor({ ...DEFAULT_COLOR });
  }, []);

  // Auto-apply
  useEffect(() => {
    if (!selectedClipId) return;
    const timer = setTimeout(applyColor, 150);
    return () => clearTimeout(timer);
  }, [color, selectedClipId, applyColor]);

  if (!selectedClipId || !selectedClip) {
    return (
      <div style={PANEL}>
        <div style={{ ...SECTION, background: '#0d0d0d' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#fff' }}>Color</div>
        </div>
        <div style={{ ...SECTION, color: '#444', textAlign: 'center', padding: 24 }}>
          Select a clip on the timeline
        </div>
      </div>
    );
  }

  const isModified = JSON.stringify(color) !== JSON.stringify(DEFAULT_COLOR);

  return (
    <div style={PANEL}>
      {/* Header */}
      <div style={{ ...SECTION, background: '#0d0d0d' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#fff' }}>Color Correction</div>
          {isModified && <button style={RESET_BTN} onClick={resetColor}>Reset All</button>}
        </div>
      </div>

      {/* Basic */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}><span>Basic</span></div>

        <div style={ROW}>
          <span style={LABEL}>Exposure</span>
          <input type="range" style={SLIDER} min={-4} max={4} step={0.1} value={color.exposure}
            onChange={(e) => updateField('exposure', Number(e.target.value))} />
          <span style={VALUE}>{color.exposure > 0 ? '+' : ''}{color.exposure.toFixed(1)}</span>
        </div>

        <div style={ROW}>
          <span style={LABEL}>Temp (K)</span>
          <input type="range" style={SLIDER} min={2000} max={12000} step={100} value={color.temperature}
            onChange={(e) => updateField('temperature', Number(e.target.value))} />
          <span style={VALUE}>{color.temperature}</span>
        </div>

        <div style={ROW}>
          <span style={LABEL}>Contrast</span>
          <input type="range" style={SLIDER} min={0} max={3} step={0.01} value={color.contrast}
            onChange={(e) => updateField('contrast', Number(e.target.value))} />
          <span style={VALUE}>{color.contrast.toFixed(2)}</span>
        </div>

        <div style={ROW}>
          <span style={LABEL}>Saturation</span>
          <input type="range" style={SLIDER} min={0} max={3} step={0.01} value={color.saturation}
            onChange={(e) => updateField('saturation', Number(e.target.value))} />
          <span style={VALUE}>{color.saturation.toFixed(2)}</span>
        </div>

        <div style={ROW}>
          <span style={LABEL}>Hue</span>
          <input type="range" style={SLIDER} min={-180} max={180} step={1} value={color.hue}
            onChange={(e) => updateField('hue', Number(e.target.value))} />
          <span style={VALUE}>{color.hue}&deg;</span>
        </div>
      </div>

      {/* MARKER_CC3WAY: 3-Way Color Wheels (FCP7 Ch.79) */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}><span>3-Way Color Corrector</span></div>
        <div style={{ display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: 8 }}>
          <ColorWheel
            label="Shadows"
            r={color.liftR}
            g={color.liftG}
            b={color.liftB}
            size={90}
            onChange={(r, g, b) => {
              setColor((prev) => ({ ...prev, liftR: r, liftG: g, liftB: b }));
            }}
          />
          <ColorWheel
            label="Midtones"
            r={color.midR}
            g={color.midG}
            b={color.midB}
            size={90}
            onChange={(r, g, b) => {
              setColor((prev) => ({ ...prev, midR: r, midG: g, midB: b }));
            }}
          />
          <ColorWheel
            label="Highlights"
            r={color.gainR}
            g={color.gainG}
            b={color.gainB}
            size={90}
            onChange={(r, g, b) => {
              setColor((prev) => ({ ...prev, gainR: r, gainG: g, gainB: b }));
            }}
          />
        </div>
      </div>

      {/* Curves */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}><span>Curves</span></div>
        <select
          style={SELECT}
          value={color.curvesPreset}
          onChange={(e) => updateField('curvesPreset', e.target.value)}
        >
          {CURVE_PRESETS.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
