import { create } from 'zustand';

export interface HeartbeatState {
  enabled: boolean;
  interval: number; // in seconds
  last_tick: number | null; // timestamp in seconds
  tasks_dispatched: number;
  tasks_failed: number;
}

interface HeartbeatStore {
  heartbeat: HeartbeatState | null;
  updateHeartbeat: (updates: Partial<HeartbeatState>) => void;
  resetHeartbeat: () => void;
}

export const useHeartbeatStore = create<HeartbeatStore>((set) => ({
  heartbeat: null,
  
  updateHeartbeat: (updates) => set((state) => {
    if (!state.heartbeat) return state;
    return {
      heartbeat: {
        ...state.heartbeat,
        ...updates
      }
    };
  }),
  
  resetHeartbeat: () => set({
    heartbeat: {
      enabled: false,
      interval: 300, // 5 minutes default
      last_tick: null,
      tasks_dispatched: 0,
      tasks_failed: 0
    }
  })
}));