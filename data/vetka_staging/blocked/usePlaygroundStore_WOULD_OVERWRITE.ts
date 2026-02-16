// file: client/src/store/usePlaygroundStore.ts

/**
 * usePlaygroundStore - Zustand store for playground state.
 * Manages playground data fetching and state for the debug playground feature.
 *
 * @status active
 * @phase build
 * @depends zustand
 * @used_by PlaygroundPanel
 */

import { create } from 'zustand';

// Define types for playground data
export interface Playground {
  id: string;
  name: string;
  createdAt: string;
  isActive: boolean;
}

interface PlaygroundState {
  // State
  count: number;
  playgrounds: Playground[];
  review_ready: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchPlaygroundData: () => Promise<void>;
  setReviewReady: (ready: boolean) => void;
  clearError: () => void;
}

export const usePlaygroundStore = create<PlaygroundState>((set) => ({
  // Initial state
  count: 0,
  playgrounds: [],
  review_ready: false,
  isLoading: false,
  error: null,

  // Async action to fetch playground data
  fetchPlaygroundData: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch('/api/debug/playground');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      
      set({
        count: data.count || 0,
        playgrounds: data.playgrounds || [],
        review_ready: data.review_ready || false,
        isLoading: false,
        error: null
      });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch playground data'
      });
    }
  },

  // Action to set review_ready flag
  setReviewReady: (ready: boolean) => set({ review_ready: ready }),

  // Action to clear error
  clearError: () => set({ error: null })
}));