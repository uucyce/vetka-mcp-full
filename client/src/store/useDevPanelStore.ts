import { create } from 'zustand';

export type DevPanelTab = 'mcc' | 'stats' | 'architect' | 'balance';

interface DevPanelStoreState {
  activeTab: DevPanelTab;
  setActiveTab: (tab: DevPanelTab) => void;
}

export const useDevPanelStore = create<DevPanelStoreState>((set) => ({
  activeTab: 'mcc',
  setActiveTab: (tab) => set({ activeTab: tab }),
}));
