/**
 * Hook for accessing available AI models with real-time status updates.
 * Provides model availability tracking via window events.
 *
 * @status active
 * @phase 96
 * @depends react
 * @used_by ChatPanel, ModelSelector, ChatSidebar
 */

import { useEffect, useState } from 'react';

export interface Model {
  id: string;
  name: string;
  type: 'language' | 'vision' | 'embedding';
  available: boolean;
}

const DEFAULT_MODELS: Model[] = [
  { id: 'gpt-4', name: 'GPT-4', type: 'language', available: true },
  { id: 'gpt-4-vision', name: 'GPT-4 Vision', type: 'vision', available: true },
  { id: 'claude-3', name: 'Claude 3 Opus', type: 'language', available: true },
  { id: 'claude-vision', name: 'Claude Vision', type: 'vision', available: true },
  { id: 'local-llm', name: 'Local LLM', type: 'language', available: false },
];

export function useModelRegistry(): Model[] {
  const [models, setModels] = useState<Model[]>(DEFAULT_MODELS);

  useEffect(() => {
    // Listen for model status changes
    const handleModelStatus = (e: any) => {
      const data = e.detail || e;
      setModels((prevModels) =>
        prevModels.map((m) =>
          m.id === data.model_id ? { ...m, available: data.available } : m
        )
      );
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('model-status', handleModelStatus);
      return () => {
        window.removeEventListener('model-status', handleModelStatus);
      };
    }
  }, []);

  return models;
}
