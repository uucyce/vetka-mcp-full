/**
 * MARKER_W10.6 + GAMMA-18 + GAMMA-36: EffectsPanel
 *
 * Two modes:
 * 1. No clip selected → Effects Browser (FCP7 Ch.13): browsable list of
 *    available effects organized by category. Drag effect onto timeline clip
 *    to apply. Search/filter at top.
 * 2. Clip selected → Effect sliders (per-clip adjustment).
 *
 * Categories: Video Filters, Audio Filters, Transitions, Generators.
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

  // MARKER_GAMMA-36: Effects Browser mode (no clip selected)
  if (!selectedClip) {
    return <EffectsBrowser />;
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

// ═══ MARKER_GAMMA-36: Effects Browser ════════════════════════════════

type BrowserEffect = {
  id: string;
  name: string;
  description: string;
};

type BrowserCategory = {
  name: string;
  effects: BrowserEffect[];
};

const BROWSER_CATEGORIES: BrowserCategory[] = [
  {
    name: 'Video Filters',
    effects: [
      { id: 'brightness', name: 'Brightness & Contrast', description: 'Adjust brightness and contrast levels' },
      { id: 'color_balance', name: 'Color Balance', description: 'Shift color balance between shadows, midtones, highlights' },
      { id: 'saturation', name: 'Hue/Saturation', description: 'Adjust hue, saturation, and lightness' },
      { id: 'gamma', name: 'Gamma Correction', description: 'Adjust gamma curve for exposure control' },
      { id: 'blur', name: 'Gaussian Blur', description: 'Apply gaussian blur to soften image' },
      { id: 'sharpen', name: 'Unsharp Mask', description: 'Sharpen edges using unsharp mask algorithm' },
      { id: 'denoise', name: 'Noise Reduction', description: 'Reduce video noise and grain' },
      { id: 'vignette', name: 'Vignette', description: 'Darken edges of frame for cinematic look' },
      { id: 'chroma_key', name: 'Chroma Key', description: 'Green/blue screen keying for compositing' },
      { id: 'lut_apply', name: 'LUT Apply', description: 'Apply Look-Up Table for color grading' },
    ],
  },
  {
    name: 'Audio Filters',
    effects: [
      { id: 'eq', name: 'Equalizer', description: '10-band parametric equalizer' },
      { id: 'compressor', name: 'Compressor', description: 'Dynamic range compression' },
      { id: 'limiter', name: 'Limiter', description: 'Peak limiting to prevent clipping' },
      { id: 'noise_gate', name: 'Noise Gate', description: 'Remove background noise below threshold' },
      { id: 'reverb', name: 'Reverb', description: 'Add room ambience and space' },
      { id: 'delay', name: 'Delay', description: 'Echo and delay effects' },
      { id: 'pitch_shift', name: 'Pitch Shift', description: 'Change audio pitch without affecting speed' },
      { id: 'normalize', name: 'Normalize', description: 'Normalize audio levels to target loudness' },
    ],
  },
  {
    name: 'Transitions',
    effects: [
      { id: 'cross_dissolve', name: 'Cross Dissolve', description: 'Standard dissolve between two clips' },
      { id: 'dip_to_black', name: 'Dip to Black', description: 'Fade through black between clips' },
      { id: 'dip_to_white', name: 'Dip to White', description: 'Fade through white between clips' },
      { id: 'wipe_left', name: 'Wipe Left', description: 'Linear wipe from right to left' },
      { id: 'wipe_down', name: 'Wipe Down', description: 'Linear wipe from top to bottom' },
      { id: 'push_left', name: 'Push Left', description: 'New clip pushes old clip off screen' },
      { id: 'slide_left', name: 'Slide Left', description: 'New clip slides over old clip' },
    ],
  },
  {
    name: 'Generators',
    effects: [
      { id: 'color_matte', name: 'Color Matte', description: 'Solid color background generator' },
      { id: 'bars_and_tone', name: 'Bars and Tone', description: 'SMPTE color bars with 1kHz tone' },
      { id: 'slug', name: 'Slug', description: 'Black video placeholder' },
      { id: 'title', name: 'Text Generator', description: 'Simple title/text overlay generator' },
      { id: 'countdown', name: 'Countdown Leader', description: 'Countdown leader for program start' },
    ],
  },
];

// MARKER_GAMMA-P2.3: Favorites persistence
const LS_FAVORITES = 'cut_effect_favorites';
function loadFavorites(): Set<string> {
  try {
    const raw = localStorage.getItem(LS_FAVORITES);
    if (raw) return new Set(JSON.parse(raw));
  } catch { /* corrupt */ }
  return new Set();
}
function saveFavorites(favs: Set<string>) {
  try { localStorage.setItem(LS_FAVORITES, JSON.stringify([...favs])); } catch { /* ok */ }
}

function EffectsBrowser() {
  const [search, setSearch] = useState('');
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [favorites, setFavorites] = useState<Set<string>>(loadFavorites);

  const toggleFavorite = useCallback((id: string) => {
    setFavorites((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      saveFavorites(next);
      return next;
    });
  }, []);

  const toggleCat = useCallback((name: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  }, []);

  const searchLower = search.toLowerCase();

  // Build favorites category from starred effects
  const allEffects = BROWSER_CATEGORIES.flatMap((c) => c.effects);
  const favEffects = allEffects.filter((e) => favorites.has(e.id));
  const favCategory: BrowserCategory | null = favEffects.length > 0
    ? { name: 'Favorites', effects: favEffects }
    : null;

  const categories = favCategory
    ? [favCategory, ...BROWSER_CATEGORIES]
    : BROWSER_CATEGORIES;

  const handleDragStart = useCallback((e: React.DragEvent, effect: BrowserEffect) => {
    e.dataTransfer.setData('application/x-cut-effect', JSON.stringify({ id: effect.id, name: effect.name }));
    e.dataTransfer.effectAllowed = 'copy';
  }, []);

  return (
    <div style={PANEL} data-testid="effects-browser">
      <div style={{ fontSize: 10, fontWeight: 600, color: '#aaa', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 }}>
        Effects
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="Search effects..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{
          width: '100%',
          padding: '3px 6px',
          background: '#111',
          border: '1px solid #333',
          borderRadius: 3,
          color: '#ccc',
          fontSize: 9,
          outline: 'none',
          marginBottom: 6,
          boxSizing: 'border-box',
        }}
      />

      {/* Category list (with Favorites at top if any starred) */}
      {categories.map((cat) => {
        const filtered = searchLower
          ? cat.effects.filter((e) => e.name.toLowerCase().includes(searchLower) || e.description.toLowerCase().includes(searchLower))
          : cat.effects;
        if (searchLower && filtered.length === 0) return null;
        const isOpen = !collapsed.has(cat.name) || !!searchLower;
        const isFavCat = cat.name === 'Favorites';

        return (
          <div key={cat.name}>
            <div
              onClick={() => toggleCat(cat.name)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                padding: '4px 0',
                cursor: 'pointer',
                borderBottom: isFavCat ? '1px solid #333' : '1px solid #1a1a1a',
                marginTop: 2,
              }}
            >
              <span style={{ fontSize: 8, color: '#555' }}>{isOpen ? '\u25BE' : '\u25B8'}</span>
              <span style={{ fontSize: 9, fontWeight: 600, color: isFavCat ? '#ccc' : '#999', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                {cat.name}
              </span>
              <span style={{ fontSize: 8, color: '#444', marginLeft: 'auto' }}>{filtered.length}</span>
            </div>
            {isOpen && filtered.map((effect) => (
              <div
                key={`${cat.name}-${effect.id}`}
                draggable
                onDragStart={(e) => handleDragStart(e, effect)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '3px 4px 3px 16px',
                  cursor: 'grab',
                  borderBottom: '1px solid #111',
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = '#1a1a1a'; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                title={effect.description}
              >
                {/* MARKER_GAMMA-P2.3: Star toggle */}
                <span
                  onClick={(e) => { e.stopPropagation(); toggleFavorite(effect.id); }}
                  style={{ cursor: 'pointer', fontSize: 10, color: favorites.has(effect.id) ? '#ccc' : '#333', flexShrink: 0 }}
                  title={favorites.has(effect.id) ? 'Remove from Favorites' : 'Add to Favorites'}
                >
                  {favorites.has(effect.id) ? '\u2605' : '\u2606'}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: 9, color: '#ccc', display: 'block' }}>{effect.name}</span>
                  <span style={{ fontSize: 8, color: '#555', marginTop: 1, display: 'block' }}>{effect.description}</span>
                </div>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
