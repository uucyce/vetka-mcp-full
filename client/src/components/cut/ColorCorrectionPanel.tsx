/**
 * MARKER_B16: Color Correction Panel — 3-way color corrector + curves.
 * MARKER_SEC_COLOR: Secondary Color Correction with HSL qualifier (FCP7 Ch.28).
 *
 * Sections:
 * 1. Basic: Exposure, White Balance, Saturation, Hue
 * 2. Lift/Gamma/Gain: Per-channel RGB sliders for shadows/mids/highlights
 * 3. Curves: Preset selector + custom luminance curves
 * 4. Secondary: HSL qualifier + masked hue/sat/exposure correction
 *
 * color_correction persisted via set_prop (applyTimelineOps) — reaches render pipeline.
 * Preview via POST /cut/preview/frame with EffectParam objects.
 * Render via FFmpeg lut3d= with generated .cube LUT (secondary_color EffectParam).
 */
import { useState, useCallback, useEffect, useRef, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useSelectionStore } from '../../store/useSelectionStore';
import { useColorPresetStore } from '../../store/useColorPresetStore';
import { API_BASE } from '../../config/api.config';
import ColorWheel from './ColorWheel';
import CurveEditor, { createDefaultCurveData, curveDataToFFmpegStrings, type CurveData } from './CurveEditor';

// ─── Types ───

interface SecondaryState {
  enabled: boolean;
  // HSL qualifier
  hueCenter: number;   // 0..360 degrees
  hueWidth: number;    // degrees half-width
  satMin: number;      // 0..1
  satMax: number;      // 0..1
  lumaMin: number;     // 0..1
  lumaMax: number;     // 0..1
  softness: number;    // 0..1 feathering
  // Correction
  hueShift: number;    // -180..180
  saturation: number;  // 0..3
  exposure: number;    // -4..4
}

interface ColorState {
  exposure: number;      // stops: -4..+4
  temperature: number;   // K: 2000..12000
  tint: number;          // green-magenta: -100..+100
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
  curveData: CurveData;
  // Secondary color correction (HSL qualifier)
  secondary: SecondaryState;
}

const DEFAULT_SECONDARY: SecondaryState = {
  enabled: false,
  hueCenter: 120, hueWidth: 30,
  satMin: 0, satMax: 1,
  lumaMin: 0, lumaMax: 1,
  softness: 0.15,
  hueShift: 0, saturation: 1.0, exposure: 0,
};

const DEFAULT_COLOR: ColorState = {
  exposure: 0, temperature: 6500, tint: 0, saturation: 1.0, hue: 0, contrast: 1.0,
  liftR: 0, liftG: 0, liftB: 0,
  midR: 0, midG: 0, midB: 0,
  gainR: 0, gainG: 0, gainB: 0,
  curvesPreset: 'none',
  curveData: createDefaultCurveData(),
  secondary: { ...DEFAULT_SECONDARY },
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
  const selectedClipId = useSelectionStore((s) => s.selectedClipId);
  const lanes = useCutEditorStore((s) => s.lanes);

  const selectedClip = lanes
    .flatMap((l) => l.clips || [])
    .find((c) => c.clip_id === selectedClipId);

  const clipColor = (selectedClip as any)?.color_correction as Partial<ColorState> | undefined;
  const [color, setColor] = useState<ColorState>({
    ...DEFAULT_COLOR,
    ...clipColor,
    secondary: { ...DEFAULT_SECONDARY, ...(clipColor?.secondary ?? {}) },
  });

  useEffect(() => {
    const cc = (selectedClip as any)?.color_correction;
    setColor({
      ...DEFAULT_COLOR,
      ...(cc || {}),
      secondary: { ...DEFAULT_SECONDARY, ...(cc?.secondary ?? {}) },
    });
  }, [selectedClipId, selectedClip]);

  const updateField = useCallback((field: keyof ColorState, value: number | string) => {
    setColor((prev) => ({ ...prev, [field]: value }));
  }, []);

  const updateSecondary = useCallback((field: keyof SecondaryState, value: number | boolean) => {
    setColor((prev) => ({ ...prev, secondary: { ...prev.secondary, [field]: value } }));
  }, []);

  const applyColor = useCallback(() => {
    if (!selectedClipId) return;
    const store = useCutEditorStore.getState();
    // Local store update (immediate UI feedback)
    const updatedLanes = store.lanes.map((lane) => ({
      ...lane,
      clips: (lane.clips || []).map((clip) => {
        if (clip.clip_id !== selectedClipId) return clip;
        return { ...clip, color_correction: color };
      }),
    }));
    store.setLanes(updatedLanes);
    // Persist to backend — reaches render pipeline (set_prop is in paste-safe whitelist)
    void store.applyTimelineOps([{
      op: 'set_prop',
      clip_id: selectedClipId,
      key: 'color_correction',
      value: color,
    }]);
  }, [selectedClipId, color]);

  const resetColor = useCallback(() => {
    setColor({ ...DEFAULT_COLOR });
  }, []);

  // ─── Preset bar state ───
  const presets = useColorPresetStore((s) => s.presets);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('');
  const [savingPreset, setSavingPreset] = useState(false);
  const [presetName, setPresetName] = useState('');

  // Load presets on mount
  useEffect(() => {
    useColorPresetStore.getState().loadPresets();
  }, []);

  const handleLoadPreset = useCallback((id: string) => {
    const preset = presets.find((p) => p.id === id);
    if (!preset) return;
    setSelectedPresetId(id);
    setColor({ ...DEFAULT_COLOR, ...preset.color });
  }, [presets]);

  const handleSavePreset = useCallback(() => {
    if (!presetName.trim()) return;
    useColorPresetStore.getState().savePreset(presetName.trim(), color);
    setPresetName('');
    setSavingPreset(false);
  }, [presetName, color]);

  const handleDeletePreset = useCallback(() => {
    const preset = presets.find((p) => p.id === selectedPresetId);
    if (!preset || preset.builtIn) return;
    useColorPresetStore.getState().deletePreset(selectedPresetId);
    setSelectedPresetId('');
  }, [selectedPresetId, presets]);

  const selectedPreset = presets.find((p) => p.id === selectedPresetId);
  const canDelete = !!selectedPreset && !selectedPreset.builtIn;

  // Auto-apply
  useEffect(() => {
    if (!selectedClipId) return;
    const timer = setTimeout(applyColor, 150);
    return () => clearTimeout(timer);
  }, [color, selectedClipId, applyColor]);

  // MARKER_B22: Graded preview thumbnail — fetch from /preview/frame
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [previewTiming, setPreviewTiming] = useState<number | null>(null);
  const previewTimerRef = useRef<number>(0);
  const currentTime = useCutEditorStore((s) => s.currentTime);

  useEffect(() => {
    if (!selectedClip?.source_path) {
      setPreviewSrc(null);
      return;
    }
    if (previewTimerRef.current) clearTimeout(previewTimerRef.current);
    previewTimerRef.current = window.setTimeout(async () => {
      try {
        const effects: Array<{ type: string; params: Record<string, number | string>; enabled: boolean }> = [];
        if (color.exposure !== 0) effects.push({ type: 'exposure', params: { stops: color.exposure }, enabled: true });
        if (color.contrast !== 1) effects.push({ type: 'contrast', params: { value: color.contrast }, enabled: true });
        if (color.saturation !== 1) effects.push({ type: 'saturation', params: { value: color.saturation }, enabled: true });
        if (color.hue !== 0) effects.push({ type: 'hue', params: { degrees: color.hue }, enabled: true });
        if (color.temperature !== 6500 || color.tint !== 0) {
          effects.push({ type: 'white_balance', params: { temperature: color.temperature, tint: color.tint }, enabled: true });
        }
        // MARKER_B52: 3-way color wheels → lift/midtone/gain effects for preview
        if (color.liftR !== 0 || color.liftG !== 0 || color.liftB !== 0) {
          effects.push({ type: 'lift', params: { r: color.liftR, g: color.liftG, b: color.liftB }, enabled: true });
        }
        if (color.midR !== 0 || color.midG !== 0 || color.midB !== 0) {
          effects.push({ type: 'midtone', params: { r: color.midR, g: color.midG, b: color.midB }, enabled: true });
        }
        if (color.gainR !== 0 || color.gainG !== 0 || color.gainB !== 0) {
          effects.push({ type: 'gain', params: { r: color.gainR, g: color.gainG, b: color.gainB }, enabled: true });
        }

        // MARKER_B93: Custom curves → point strings for preview
        if (color.curveData) {
          const cs = curveDataToFFmpegStrings(color.curveData);
          if (cs.master || cs.red || cs.green || cs.blue) {
            effects.push({ type: 'curves', params: { master: cs.master, red: cs.red, green: cs.green, blue: cs.blue }, enabled: true });
          }
        } else if (color.curvesPreset !== 'none') {
          effects.push({ type: 'curves', params: { preset: color.curvesPreset }, enabled: true });
        }

        // MARKER_SEC_COLOR: Secondary color correction (HSL qualifier)
        const sec = color.secondary;
        if (sec.enabled && (sec.hueShift !== 0 || sec.saturation !== 1.0 || sec.exposure !== 0)) {
          effects.push({
            type: 'secondary_color',
            params: {
              hue_center: sec.hueCenter,
              hue_width: sec.hueWidth,
              sat_min: sec.satMin,
              sat_max: sec.satMax,
              luma_min: sec.lumaMin,
              luma_max: sec.lumaMax,
              softness: sec.softness,
              hue_shift: sec.hueShift,
              saturation: sec.saturation,
              exposure: sec.exposure,
            },
            enabled: true,
          });
        }

        const resp = await fetch(`${API_BASE}/cut/preview/frame`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_path: selectedClip.source_path,
            time: currentTime,
            proxy_height: 270,
            effects,
            jpeg_quality: 70,
          }),
        });
        const data = await resp.json();
        if (data.success && data.data) {
          setPreviewSrc(`data:image/jpeg;base64,${data.data}`);
          setPreviewTiming(data.timing_ms);
        }
      } catch {
        // Silent fail — preview is non-critical
      }
    }, 250);

    return () => { if (previewTimerRef.current) clearTimeout(previewTimerRef.current); };
  }, [selectedClip?.source_path, currentTime, color]);

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

      {/* MARKER_CC_PRESETS: Preset bar */}
      <div style={{ ...SECTION, padding: '5px 10px', borderBottom: '1px solid #1a1a1a' }}>
        {!savingPreset ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <select
              style={{
                flex: 1,
                background: '#1a1a1a',
                color: '#ccc',
                border: '1px solid #333',
                borderRadius: 3,
                padding: '3px 6px',
                fontSize: 11,
                fontFamily: 'system-ui',
                cursor: 'pointer',
                minWidth: 0,
              }}
              value={selectedPresetId}
              onChange={(e) => handleLoadPreset(e.target.value)}
            >
              <option value="">— Presets —</option>
              {presets.filter((p) => p.builtIn).length > 0 && (
                <optgroup label="Built-in">
                  {presets.filter((p) => p.builtIn).map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </optgroup>
              )}
              {presets.filter((p) => !p.builtIn).length > 0 && (
                <optgroup label="User">
                  {presets.filter((p) => !p.builtIn).map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </optgroup>
              )}
            </select>
            <button
              style={{
                background: '#222',
                border: '1px solid #333',
                color: '#aaa',
                borderRadius: 3,
                padding: '3px 7px',
                fontSize: 10,
                fontFamily: 'system-ui',
                cursor: 'pointer',
                flexShrink: 0,
              }}
              onClick={() => setSavingPreset(true)}
              title="Save current color as preset"
            >
              Save
            </button>
            {canDelete && (
              <button
                style={{
                  background: '#222',
                  border: '1px solid #333',
                  color: '#888',
                  borderRadius: 3,
                  padding: '3px 7px',
                  fontSize: 10,
                  fontFamily: 'system-ui',
                  cursor: 'pointer',
                  flexShrink: 0,
                }}
                onClick={handleDeletePreset}
                title="Delete selected preset"
              >
                Del
              </button>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <input
              autoFocus
              type="text"
              placeholder="Preset name..."
              value={presetName}
              style={{
                flex: 1,
                background: '#1a1a1a',
                color: '#ccc',
                border: '1px solid #444',
                borderRadius: 3,
                padding: '3px 6px',
                fontSize: 11,
                fontFamily: 'system-ui',
                minWidth: 0,
                outline: 'none',
              }}
              onChange={(e) => setPresetName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSavePreset();
                if (e.key === 'Escape') { setSavingPreset(false); setPresetName(''); }
              }}
            />
            <button
              style={{
                background: '#222',
                border: '1px solid #444',
                color: '#ccc',
                borderRadius: 3,
                padding: '3px 7px',
                fontSize: 10,
                fontFamily: 'system-ui',
                cursor: 'pointer',
                flexShrink: 0,
              }}
              onClick={handleSavePreset}
            >
              OK
            </button>
            <button
              style={{
                background: 'none',
                border: 'none',
                color: '#555',
                cursor: 'pointer',
                fontSize: 10,
                fontFamily: 'system-ui',
                padding: '3px 5px',
                flexShrink: 0,
              }}
              onClick={() => { setSavingPreset(false); setPresetName(''); }}
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* MARKER_B22: Graded preview thumbnail */}
      {previewSrc && (
        <div style={{ ...SECTION, padding: '4px 10px', textAlign: 'center' as const }}>
          <img
            src={previewSrc}
            alt="Graded preview"
            data-testid="cc-graded-preview"
            style={{ width: '100%', maxHeight: 120, objectFit: 'contain' as const, borderRadius: 3, border: '1px solid #222' }}
          />
          {previewTiming !== null && (
            <div style={{ fontSize: 8, color: '#444', marginTop: 2 }}>{previewTiming}ms</div>
          )}
        </div>
      )}

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
          <span style={LABEL}>Tint</span>
          <input type="range" style={SLIDER} min={-100} max={100} step={5} value={color.tint}
            onChange={(e) => updateField('tint', Number(e.target.value))} />
          <span style={VALUE}>{color.tint}</span>
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
            r={color.liftR} g={color.liftG} b={color.liftB}
            size={90}
            onChange={(r, g, b) => setColor((prev) => ({ ...prev, liftR: r, liftG: g, liftB: b }))}
          />
          <ColorWheel
            label="Midtones"
            r={color.midR} g={color.midG} b={color.midB}
            size={90}
            onChange={(r, g, b) => setColor((prev) => ({ ...prev, midR: r, midG: g, midB: b }))}
          />
          <ColorWheel
            label="Highlights"
            r={color.gainR} g={color.gainG} b={color.gainB}
            size={90}
            onChange={(r, g, b) => setColor((prev) => ({ ...prev, gainR: r, gainG: g, gainB: b }))}
          />
        </div>
      </div>

      {/* Curves — MARKER_B93: Interactive curve editor + preset fallback */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}><span>Curves</span></div>
        <CurveEditor
          curves={color.curveData || createDefaultCurveData()}
          onChange={(newCurves) => setColor((prev) => ({ ...prev, curveData: newCurves, curvesPreset: 'none' }))}
          size={Math.min(200, 200)}
        />
        <div style={{ marginTop: 6 }}>
          <select
            style={SELECT}
            value={color.curvesPreset}
            onChange={(e) => {
              const preset = e.target.value;
              updateField('curvesPreset', preset);
              // Reset custom curves when preset selected
              if (preset !== 'none') {
                setColor((prev) => ({ ...prev, curvesPreset: preset, curveData: createDefaultCurveData() }));
              }
            }}
          >
            {CURVE_PRESETS.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* MARKER_SEC_COLOR: Secondary Color Correction — HSL qualifier (FCP7 Ch.28) */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>
          <span>Secondary</span>
          <label style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={color.secondary.enabled}
              onChange={(e) => updateSecondary('enabled', e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            <span style={{ fontSize: 9 }}>Enable</span>
          </label>
        </div>

        {color.secondary.enabled && (
          <>
            {/* Color range indicator */}
            <div style={{ marginBottom: 8 }}>
              <div
                style={{
                  height: 6,
                  borderRadius: 3,
                  background: `linear-gradient(to right, hsl(${color.secondary.hueCenter - color.secondary.hueWidth}deg,70%,45%) 0%, hsl(${color.secondary.hueCenter}deg,85%,55%) 50%, hsl(${color.secondary.hueCenter + color.secondary.hueWidth}deg,70%,45%) 100%)`,
                  opacity: 0.85,
                  border: '1px solid #333',
                }}
              />
            </div>

            {/* Qualifier */}
            <div style={{ ...SECTION_TITLE, fontSize: 9, color: '#444', marginBottom: 6 }}>
              <span>Qualifier</span>
            </div>

            <div style={ROW}>
              <span style={LABEL}>Hue</span>
              <input type="range" style={SLIDER} min={0} max={359} step={1}
                value={color.secondary.hueCenter}
                onChange={(e) => updateSecondary('hueCenter', Number(e.target.value))} />
              <span style={VALUE}>{color.secondary.hueCenter}&deg;</span>
            </div>
            <div style={ROW}>
              <span style={LABEL}>Hue Width</span>
              <input type="range" style={SLIDER} min={1} max={180} step={1}
                value={color.secondary.hueWidth}
                onChange={(e) => updateSecondary('hueWidth', Number(e.target.value))} />
              <span style={VALUE}>&plusmn;{color.secondary.hueWidth}&deg;</span>
            </div>
            <div style={ROW}>
              <span style={LABEL}>Sat Min</span>
              <input type="range" style={SLIDER} min={0} max={1} step={0.01}
                value={color.secondary.satMin}
                onChange={(e) => updateSecondary('satMin', Number(e.target.value))} />
              <span style={VALUE}>{color.secondary.satMin.toFixed(2)}</span>
            </div>
            <div style={ROW}>
              <span style={LABEL}>Sat Max</span>
              <input type="range" style={SLIDER} min={0} max={1} step={0.01}
                value={color.secondary.satMax}
                onChange={(e) => updateSecondary('satMax', Number(e.target.value))} />
              <span style={VALUE}>{color.secondary.satMax.toFixed(2)}</span>
            </div>
            <div style={ROW}>
              <span style={LABEL}>Luma Min</span>
              <input type="range" style={SLIDER} min={0} max={1} step={0.01}
                value={color.secondary.lumaMin}
                onChange={(e) => updateSecondary('lumaMin', Number(e.target.value))} />
              <span style={VALUE}>{color.secondary.lumaMin.toFixed(2)}</span>
            </div>
            <div style={ROW}>
              <span style={LABEL}>Luma Max</span>
              <input type="range" style={SLIDER} min={0} max={1} step={0.01}
                value={color.secondary.lumaMax}
                onChange={(e) => updateSecondary('lumaMax', Number(e.target.value))} />
              <span style={VALUE}>{color.secondary.lumaMax.toFixed(2)}</span>
            </div>
            <div style={ROW}>
              <span style={LABEL}>Softness</span>
              <input type="range" style={SLIDER} min={0} max={1} step={0.01}
                value={color.secondary.softness}
                onChange={(e) => updateSecondary('softness', Number(e.target.value))} />
              <span style={VALUE}>{color.secondary.softness.toFixed(2)}</span>
            </div>

            {/* Correction */}
            <div style={{ ...SECTION_TITLE, fontSize: 9, color: '#444', marginTop: 10, marginBottom: 6 }}>
              <span>Correction</span>
              <button
                style={RESET_BTN}
                onClick={() => setColor((prev) => ({
                  ...prev,
                  secondary: { ...prev.secondary, hueShift: 0, saturation: 1.0, exposure: 0 },
                }))}
              >
                Reset
              </button>
            </div>

            <div style={ROW}>
              <span style={LABEL}>Hue Shift</span>
              <input type="range" style={SLIDER} min={-180} max={180} step={1}
                value={color.secondary.hueShift}
                onChange={(e) => updateSecondary('hueShift', Number(e.target.value))} />
              <span style={VALUE}>{color.secondary.hueShift > 0 ? '+' : ''}{color.secondary.hueShift}&deg;</span>
            </div>
            <div style={ROW}>
              <span style={LABEL}>Saturation</span>
              <input type="range" style={SLIDER} min={0} max={3} step={0.01}
                value={color.secondary.saturation}
                onChange={(e) => updateSecondary('saturation', Number(e.target.value))} />
              <span style={VALUE}>{color.secondary.saturation.toFixed(2)}</span>
            </div>
            <div style={ROW}>
              <span style={LABEL}>Exposure</span>
              <input type="range" style={SLIDER} min={-4} max={4} step={0.1}
                value={color.secondary.exposure}
                onChange={(e) => updateSecondary('exposure', Number(e.target.value))} />
              <span style={VALUE}>{color.secondary.exposure > 0 ? '+' : ''}{color.secondary.exposure.toFixed(1)}</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
