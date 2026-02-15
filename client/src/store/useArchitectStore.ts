import { create } from 'zustand';

export interface ArchitectMessage {
  id: string;
  role: 'user' | 'architect';
  content: string;
  timestamp: number;
  subtasks?: string[];
}

interface ArchitectStoreState {
  messages: ArchitectMessage[];
  selectedModel: string;
  isGenerating: boolean;
  setSelectedModel: (model: string) => void;
  setIsGenerating: (value: boolean) => void;
  addMessage: (message: ArchitectMessage) => void;
  clearMessages: () => void;
}

export const useArchitectStore = create<ArchitectStoreState>((set) => ({
  messages: [],
  selectedModel: 'kimi-k2.5',
  isGenerating: false,
  setSelectedModel: (model) => set({ selectedModel: model }),
  setIsGenerating: (value) => set({ isGenerating: value }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  clearMessages: () => set({ messages: [] }),
}));
