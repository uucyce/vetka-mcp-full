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
  /** MARKER_C12: Add a timeline panel to dockview (multi-instance) */
  addTimelinePanel: (timelineId: string, label: string) => void;
  /** MARKER_PANEL-TOGGLE: Toggle panel — if open, focus it. If closed, re-add it. */
  togglePanel: (id: string, component: string, title: string) => void;
  /** MARKER_GAMMA-3: Toggle maximize active panel group (backtick key, FCP7/Premiere style) */
  toggleMaximize: () => void;
  /** MARKER_GAMMA-12: Save/restore focused panel per workspace preset */
  focusPerPreset: Record<WorkspacePresetName, string | null>;
  saveFocusForPreset: (preset: WorkspacePresetName, panelId: string | null) => void;
  getFocusForPreset: (preset: WorkspacePresetName) => string | null;
}

const LS_PREFIX = 'cut_dockview_';
const LS_ACTIVE = 'cut_dockview_active';

export const useDockviewStore = create<DockviewStoreState>((set, get) => ({
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

  // MARKER_PANEL-TOGGLE: Toggle panel — if exists, focus. If closed, re-add.
  togglePanel: (id, component, title) => {
    const api = get().apiRef;
    if (!api) return;
    try {
      const existing = api.getPanel(id);
      if (existing) {
        // Panel exists — focus it
        existing.api.setActive();
        return;
      }
    } catch { /* panel not found */ }
    // Panel was closed — re-add it (attached to inspector group or as new group)
    try {
      const refPanel = api.getPanel('inspector') || api.getPanel('project');
      api.addPanel({
        id,
        component,
        title,
        position: refPanel
          ? { referencePanel: refPanel.id, direction: 'within' }
          : { direction: 'right' },
      });
    } catch { /* addPanel failed */ }
  },

  // MARKER_GAMMA-3: Toggle maximize active panel group (backtick key)
  toggleMaximize: () => {
    const api = get().apiRef;
    if (!api) return;
    try {
      if (api.hasMaximizedGroup()) {
        api.exitMaximizedGroup();
      } else {
        const active = api.activePanel;
        if (active) {
          api.maximizeGroup(active);
        }
      }
    } catch { /* maximize API not available in this dockview version */ }
  },

  // MARKER_C12: Add timeline panel to dockview
  addTimelinePanel: (timelineId, label) => {
    const api = get().apiRef;
    if (!api) return;
    const panelId = `timeline-${timelineId}`;
    // Check if panel already exists
    try {
      if (api.getPanel(panelId)) return;
    } catch { /* panel not found — ok to create */ }
    // Find existing timeline group to add as tab, or create below
    const existingTimeline = api.getPanel('timeline');
    api.addPanel({
      id: panelId,
      component: 'timeline',
      title: label,
      params: { timelineId },
      position: existingTimeline
        ? { referencePanel: existingTimeline.id, direction: 'within' }
        : { direction: 'below' },
    });
  },

  // MARKER_GAMMA-12: Focus persistence per workspace preset
  focusPerPreset: { editing: 'timeline', color: 'program', audio: 'timeline', custom: null },
  saveFocusForPreset: (preset, panelId) => {
    set((s) => ({
      focusPerPreset: { ...s.focusPerPreset, [preset]: panelId },
    }));
  },
  getFocusForPreset: (preset) => get().focusPerPreset[preset],
}));
