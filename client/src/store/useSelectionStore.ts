/**
 * MARKER_ARCH_4.1: Dedicated Selection Store — extracted from useCutEditorStore.
 * Manages clip selection state: single/multi-select, linked selection, selection mode.
 * Cross-store dependency: selectAllClips reads lanes from useCutEditorStore.
 */
import { create } from 'zustand';

// --- Types ---

export type SelectionMode = 'normal' | 'range' | 'lasso';

export interface SelectionState {
  selectedClipId: string | null;
  selectedClipIds: Set<string>;
  linkedSelection: boolean;           // MARKER_W3.7: click video → also select synced audio
  selectionMode: SelectionMode;       // MARKER_ARCH_4.1: from spec — normal, range, lasso
}

export interface SelectionActions {
  setSelectedClip: (id: string | null) => void;
  toggleClipSelection: (id: string) => void;   // Cmd+Click toggle
  selectAllClips: () => void;                   // Cmd+A
  clearSelection: () => void;                   // Escape
  toggleLinkedSelection: () => void;
  setSelectionMode: (mode: SelectionMode) => void;
}

// --- Store ---

export const useSelectionStore = create<SelectionState & SelectionActions>()((set) => ({
  // State
  selectedClipId: null,
  selectedClipIds: new Set<string>(),
  linkedSelection: true,
  selectionMode: 'normal',

  // Actions
  setSelectedClip: (id) =>
    set({ selectedClipId: id, selectedClipIds: id ? new Set([id]) : new Set() }),

  toggleClipSelection: (id) =>
    set((state) => {
      const ids = new Set(state.selectedClipIds);
      if (ids.has(id)) { ids.delete(id); } else { ids.add(id); }
      return { selectedClipIds: ids, selectedClipId: ids.size === 1 ? [...ids][0] : state.selectedClipId };
    }),

  selectAllClips: () => {
    // Cross-store: read lanes from useCutEditorStore
    // Lazy import to avoid circular dependency
    const { useCutEditorStore } = require('./useCutEditorStore');
    const lanes = useCutEditorStore.getState().lanes;
    const allIds = new Set<string>();
    for (const lane of lanes) {
      for (const clip of (lane as { clips: Array<{ clip_id: string }> }).clips) {
        allIds.add(clip.clip_id);
      }
    }
    set({ selectedClipIds: allIds });
  },

  clearSelection: () =>
    set({ selectedClipId: null, selectedClipIds: new Set() }),

  toggleLinkedSelection: () =>
    set((state) => ({ linkedSelection: !state.linkedSelection })),

  setSelectionMode: (mode) =>
    set({ selectionMode: mode }),
}));
