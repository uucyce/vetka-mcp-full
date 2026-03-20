/**
 * MARKER_196.2: Dockview layout persistence store.
 *
 * Saves/restores workspace presets via localStorage.
 * Workspace = serialized dockview layout JSON.
 */
import { create } from 'zustand';
import type { SerializedDockview } from 'dockview-react';

export type WorkspacePresetName = 'editing' | 'color' | 'audio' | 'custom';

interface DockviewStoreState {
  /** Active workspace preset name */
  activePreset: WorkspacePresetName;
  /** Set active preset */
  setActivePreset: (name: WorkspacePresetName) => void;
  /** Save layout JSON to localStorage */
  saveLayout: (name: WorkspacePresetName, layout: SerializedDockview) => void;
  /** Load layout JSON from localStorage */
  loadLayout: (name: WorkspacePresetName) => SerializedDockview | null;
  /** List saved preset names */
  getSavedPresets: () => WorkspacePresetName[];
  /** MARKER_C5: Dockview API ref for workspace preset switching */
  apiRef: import('dockview-react').DockviewApi | null;
  setApiRef: (api: import('dockview-react').DockviewApi) => void;
}

const LS_PREFIX = 'cut_dockview_';
const LS_ACTIVE = 'cut_dockview_active';

export const useDockviewStore = create<DockviewStoreState>((set) => ({
  activePreset: (() => {
    try {
      const v = localStorage.getItem(LS_ACTIVE);
      if (v === 'editing' || v === 'color' || v === 'audio' || v === 'custom') return v;
    } catch { /* SSR */ }
    return 'editing';
  })(),

  setActivePreset: (name) => {
    set({ activePreset: name });
    try { localStorage.setItem(LS_ACTIVE, name); } catch { /* noop */ }
  },

  saveLayout: (name, layout) => {
    try {
      localStorage.setItem(LS_PREFIX + name, JSON.stringify(layout));
    } catch { /* noop */ }
  },

  loadLayout: (name) => {
    try {
      const raw = localStorage.getItem(LS_PREFIX + name);
      if (raw) return JSON.parse(raw) as SerializedDockview;
    } catch { /* corrupt */ }
    return null;
  },

  getSavedPresets: () => {
    const presets: WorkspacePresetName[] = [];
    for (const name of ['editing', 'color', 'audio', 'custom'] as const) {
      try {
        if (localStorage.getItem(LS_PREFIX + name)) presets.push(name);
      } catch { /* noop */ }
    }
    return presets;
  },

  // MARKER_C5: API ref for workspace preset switching
  apiRef: null,
  setApiRef: (api) => set({ apiRef: api }),
}));
