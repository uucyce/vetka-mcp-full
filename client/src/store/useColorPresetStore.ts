/**
 * MARKER_CC_PRESETS: Color Correction Preset Store
 * Manages save/load of named color correction presets (built-in + user-created).
 * Persists user presets to localStorage.
 */
import { create } from 'zustand';

// ─── Types ───

export interface ColorCorrection {
  exposure: number;
  temperature: number;
  saturation: number;
  hue: number;
  contrast: number;
  liftR: number; liftG: number; liftB: number;
  midR: number; midG: number; midB: number;
  gainR: number; gainG: number; gainB: number;
  curvesPreset: string;
}

export interface ColorPreset {
  id: string;
  name: string;
  builtIn: boolean;
  color: ColorCorrection;
  createdAt: number;
}

// ─── Built-in Presets ───

const RESET_COLOR: ColorCorrection = {
  exposure: 0, temperature: 6500, saturation: 1.0, hue: 0, contrast: 1.0,
  liftR: 0, liftG: 0, liftB: 0,
  midR: 0, midG: 0, midB: 0,
  gainR: 0, gainG: 0, gainB: 0,
  curvesPreset: 'none',
};

export const BUILTIN_PRESETS: ColorPreset[] = [
  {
    id: 'builtin_reset',
    name: 'Reset',
    builtIn: true,
    color: { ...RESET_COLOR },
    createdAt: 0,
  },
  {
    id: 'builtin_warm',
    name: 'Warm',
    builtIn: true,
    color: { ...RESET_COLOR, temperature: 8000, saturation: 1.1 },
    createdAt: 0,
  },
  {
    id: 'builtin_cool',
    name: 'Cool',
    builtIn: true,
    color: { ...RESET_COLOR, temperature: 4500, saturation: 0.95 },
    createdAt: 0,
  },
  {
    id: 'builtin_highcontrast',
    name: 'High Contrast',
    builtIn: true,
    color: { ...RESET_COLOR, contrast: 1.6, curvesPreset: 'increase_contrast' },
    createdAt: 0,
  },
  {
    id: 'builtin_vintage',
    name: 'Vintage Film',
    builtIn: true,
    color: { ...RESET_COLOR, saturation: 0.7, temperature: 7200, midG: 0.05, curvesPreset: 'vintage' },
    createdAt: 0,
  },
  {
    id: 'builtin_teal_orange',
    name: 'Cinematic Teal & Orange',
    builtIn: true,
    color: { ...RESET_COLOR, liftR: -0.08, liftG: -0.02, liftB: 0.12, gainR: 0.15, gainG: 0.05, gainB: -0.08, saturation: 1.15, contrast: 1.15 },
    createdAt: 0,
  },
  {
    id: 'builtin_film_log',
    name: 'Film Log Look',
    builtIn: true,
    color: { ...RESET_COLOR, contrast: 0.7, saturation: 0.85, liftR: 0.04, liftG: 0.04, liftB: 0.04, curvesPreset: 'lighter' },
    createdAt: 0,
  },
  {
    id: 'builtin_slog_normalize',
    name: 'S-Log Normalize',
    builtIn: true,
    color: { ...RESET_COLOR, exposure: 1.2, contrast: 1.4, saturation: 1.2 },
    createdAt: 0,
  },
];

const STORAGE_KEY = 'vetka_color_presets';

// ─── Store ───

interface ColorPresetState {
  presets: ColorPreset[];
  loadPresets: () => void;
  savePreset: (name: string, color: ColorCorrection) => ColorPreset;
  deletePreset: (id: string) => void;
}

export const useColorPresetStore = create<ColorPresetState>()((set, get) => ({
  presets: [...BUILTIN_PRESETS],

  loadPresets: () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const userPresets: ColorPreset[] = raw ? JSON.parse(raw) : [];
      set({ presets: [...BUILTIN_PRESETS, ...userPresets] });
    } catch {
      set({ presets: [...BUILTIN_PRESETS] });
    }
  },

  savePreset: (name, color) => {
    const preset: ColorPreset = {
      id: `user_${Date.now()}`,
      name: name.trim() || 'Untitled',
      builtIn: false,
      color: { ...color },
      createdAt: Date.now(),
    };
    const current = get().presets.filter((p) => !p.builtIn);
    const updated = [...current, preset];
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    } catch {
      // storage full — ignore
    }
    set({ presets: [...BUILTIN_PRESETS, ...updated] });
    return preset;
  },

  deletePreset: (id) => {
    const current = get().presets.filter((p) => !p.builtIn && p.id !== id);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
    } catch {
      // ignore
    }
    set({ presets: [...BUILTIN_PRESETS, ...current] });
  },
}));
