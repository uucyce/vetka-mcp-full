/**
 * MARKER_GAMMA-P3.1: useHotkeyStore — reactive Zustand store for hotkey management.
 *
 * Wraps the existing useCutHotkeys persistence functions (loadPresetName,
 * savePresetName, loadCustomOverrides, saveCustomOverrides) into a reactive
 * store that the HotkeyEditor UI can subscribe to.
 *
 * Features:
 * - Active preset selection (premiere/fcp7/custom)
 * - Custom override map (action → key binding)
 * - Conflict detection (multiple actions bound to same key)
 * - Resolved bindings (preset + overrides merged)
 * - Export/import custom presets as JSON
 */
import { create } from 'zustand';
import {
  type HotkeyPresetName,
  type HotkeyMap,
  type CutHotkeyAction,
  PRESETS,
  loadPresetName,
  savePresetName,
  loadCustomOverrides,
  saveCustomOverrides,
} from '../hooks/useCutHotkeys';

interface HotkeyStoreState {
  /** Active preset name */
  activePreset: HotkeyPresetName;
  /** Custom overrides (action → binding) */
  customOverrides: HotkeyMap;
  /** Set active preset */
  setPreset: (name: HotkeyPresetName) => void;
  /** Set a custom override for an action */
  setOverride: (action: CutHotkeyAction, binding: string) => void;
  /** Remove a custom override (revert to preset default) */
  removeOverride: (action: CutHotkeyAction) => void;
  /** Clear all custom overrides */
  clearOverrides: () => void;
  /** Get resolved binding for an action (custom override > preset default) */
  getBinding: (action: CutHotkeyAction) => string | undefined;
  /** Get all resolved bindings (preset merged with custom overrides) */
  getResolvedMap: () => HotkeyMap;
  /** Find conflicts: actions sharing the same key binding */
  getConflicts: () => Map<string, CutHotkeyAction[]>;
  /** Export current config as JSON string */
  exportConfig: () => string;
  /** Import config from JSON string */
  importConfig: (json: string) => boolean;
}

export const useHotkeyStore = create<HotkeyStoreState>((set, get) => ({
  activePreset: loadPresetName(),
  customOverrides: loadCustomOverrides(),

  setPreset: (name) => {
    set({ activePreset: name });
    savePresetName(name);
  },

  setOverride: (action, binding) => {
    const next = { ...get().customOverrides, [action]: binding };
    set({ customOverrides: next });
    saveCustomOverrides(next);
  },

  removeOverride: (action) => {
    const next = { ...get().customOverrides };
    delete next[action];
    set({ customOverrides: next });
    saveCustomOverrides(next);
  },

  clearOverrides: () => {
    set({ customOverrides: {} });
    saveCustomOverrides({});
  },

  getBinding: (action) => {
    const { activePreset, customOverrides } = get();
    if (customOverrides[action]) return customOverrides[action];
    const preset = activePreset === 'custom' ? {} : (PRESETS[activePreset] ?? {});
    return preset[action];
  },

  getResolvedMap: () => {
    const { activePreset, customOverrides } = get();
    const preset = activePreset === 'custom' ? {} : (PRESETS[activePreset] ?? {});
    return { ...preset, ...customOverrides };
  },

  getConflicts: () => {
    const resolved = get().getResolvedMap();
    const byKey = new Map<string, CutHotkeyAction[]>();
    for (const [action, binding] of Object.entries(resolved)) {
      if (!binding) continue;
      const key = binding.toLowerCase();
      const existing = byKey.get(key) ?? [];
      existing.push(action as CutHotkeyAction);
      byKey.set(key, existing);
    }
    // Only return entries with >1 action (actual conflicts)
    const conflicts = new Map<string, CutHotkeyAction[]>();
    for (const [key, actions] of byKey) {
      if (actions.length > 1) conflicts.set(key, actions);
    }
    return conflicts;
  },

  exportConfig: () => {
    const { activePreset, customOverrides } = get();
    return JSON.stringify({ preset: activePreset, overrides: customOverrides }, null, 2);
  },

  importConfig: (json) => {
    try {
      const data = JSON.parse(json) as { preset?: string; overrides?: HotkeyMap };
      if (data.preset && (data.preset === 'premiere' || data.preset === 'fcp7' || data.preset === 'custom')) {
        set({ activePreset: data.preset as HotkeyPresetName });
        savePresetName(data.preset as HotkeyPresetName);
      }
      if (data.overrides && typeof data.overrides === 'object') {
        set({ customOverrides: data.overrides });
        saveCustomOverrides(data.overrides);
      }
      return true;
    } catch {
      return false;
    }
  },
}));
