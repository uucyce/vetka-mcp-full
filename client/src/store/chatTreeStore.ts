/**
 * useChatTreeStore - Zustand store for chat and artifact nodes.
 * Manages CRUD operations for chat sessions and their artifacts.
 *
 * @status active
 * @phase 96
 * @depends zustand, immer, ChatNode/ArtifactNode types
 * @used_by ChatPanel, Canvas3D
 */

import { create } from 'zustand';
import { produce } from 'immer';
import { ChatNode, ArtifactNode } from '../types/treeNodes';

interface ChatTreeState {
  // State
  chatNodes: Record<string, ChatNode>;
  artifactNodes: Record<string, ArtifactNode>;

  // Chat node actions
  addChatNode: (parentFileId: string, data: Partial<ChatNode>) => string;
  updateChatNode: (id: string, updates: Partial<ChatNode>) => void;
  archiveChatNode: (id: string) => void;
  deleteChatNode: (id: string) => void;

  // Artifact node actions
  addArtifactNode: (parentChatId: string, data: Partial<ArtifactNode>) => string;
  updateArtifactNode: (id: string, updates: Partial<ArtifactNode>) => void;
  deleteArtifactNode: (id: string) => void;

  // Queries
  getChatsByParent: (parentId: string) => ChatNode[];
  getArtifactsByChat: (chatId: string) => ArtifactNode[];
  getChatById: (id: string) => ChatNode | undefined;
  getArtifactById: (id: string) => ArtifactNode | undefined;

  // Batch operations
  clearChatNodes: () => void;
  clearArtifactNodes: () => void;
}

export const useChatTreeStore = create<ChatTreeState>((set, get) => ({
  chatNodes: {},
  artifactNodes: {},

  addChatNode: (parentFileId, data) => {
    // Use provided id or generate new one
    const id = data.id || (() => {
      // ✅ Browser compatibility: fallback for older browsers/Safari
      const uuid =
        typeof crypto !== 'undefined' && crypto.randomUUID
          ? crypto.randomUUID()
          : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
      return `chat-${uuid}`;
    })();

    // Skip if node already exists (prevent duplicates from socket events)
    const existing = get().chatNodes[id];
    if (existing) {
      // console.log('[ChatTreeStore] Node already exists, skipping:', id);
      return id;
    }

    set(
      produce((state) => {
        state.chatNodes[id] = {
          id,
          type: 'chat',
          parentId: parentFileId,
          name: data.name || `Chat ${new Date().toLocaleTimeString()}`,
          participants: data.participants || [],
          messageCount: 0,
          lastActivity: new Date(),
          artifacts: [],
          status: 'active',
          decay_factor: 1.0,
          ...data,
        };
      })
    );
    return id;
  },

  updateChatNode: (id, updates) => {
    set(
      produce((state) => {
        if (state.chatNodes[id]) {
          state.chatNodes[id] = {
            ...state.chatNodes[id],
            ...updates,
            lastActivity: new Date(),
          };
        }
      })
    );
  },

  archiveChatNode: (id) => {
    set(
      produce((state) => {
        if (state.chatNodes[id]) {
          state.chatNodes[id].status = 'archived';
        }
      })
    );
  },

  deleteChatNode: (id) => {
    set(
      produce((state) => {
        const chatNode = state.chatNodes[id];
        if (chatNode) {
          // Delete associated artifacts
          chatNode.artifacts.forEach((artifactId: string) => {
            delete state.artifactNodes[artifactId];
          });
          // Delete chat
          delete state.chatNodes[id];
        }
      })
    );
  },

  addArtifactNode: (parentChatId, data) => {
    // Use provided id or generate new one
    const id = data.id || (() => {
      // ✅ Browser compatibility: fallback for older browsers/Safari
      const uuid =
        typeof crypto !== 'undefined' && crypto.randomUUID
          ? crypto.randomUUID()
          : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
      return `artifact-${uuid}`;
    })();

    // Skip if node already exists (prevent duplicates from socket events)
    const existing = get().artifactNodes[id];
    if (existing) {
      // console.log('[ChatTreeStore] Artifact already exists, skipping:', id);
      return id;
    }

    set(
      produce((state) => {
        state.artifactNodes[id] = {
          id,
          type: 'artifact',
          parentId: parentChatId,
          name: data.name || 'Artifact',
          artifactType: data.artifactType || 'code',
          status: 'streaming',
          progress: 0,
          createdAt: new Date(),
          ...data,
        };

        // Add to parent chat (if not already present)
        if (state.chatNodes[parentChatId]) {
          const artifacts = state.chatNodes[parentChatId].artifacts;
          if (!artifacts.includes(id)) {
            artifacts.push(id);
          }
        }
      })
    );
    return id;
  },

  updateArtifactNode: (id, updates) => {
    set(
      produce((state) => {
        if (state.artifactNodes[id]) {
          state.artifactNodes[id] = {
            ...state.artifactNodes[id],
            ...updates,
          };
        }
      })
    );
  },

  deleteArtifactNode: (id) => {
    set(
      produce((state) => {
        const artifactNode = state.artifactNodes[id];
        if (artifactNode) {
          // Remove from parent chat
          const parentChat = state.chatNodes[artifactNode.parentId];
          if (parentChat) {
            parentChat.artifacts = parentChat.artifacts.filter((a: string) => a !== id);
          }
          // Delete artifact
          delete state.artifactNodes[id];
        }
      })
    );
  },

  getChatsByParent: (parentId) => {
    const state = get();
    return Object.values(state.chatNodes).filter((chat) => chat.parentId === parentId);
  },

  getArtifactsByChat: (chatId) => {
    const state = get();
    return Object.values(state.artifactNodes).filter((artifact) => artifact.parentId === chatId);
  },

  getChatById: (id) => {
    const state = get();
    return state.chatNodes[id];
  },

  getArtifactById: (id) => {
    const state = get();
    return state.artifactNodes[id];
  },

  clearChatNodes: () => {
    set(
      produce((state) => {
        state.chatNodes = {};
      })
    );
  },

  clearArtifactNodes: () => {
    set(
      produce((state) => {
        state.artifactNodes = {};
      })
    );
  },
}));
