/**
 * Global Zustand store for VETKA 3D visualization state.
 * Manages tree nodes, edges, selections, chat messages, camera, and pinned files.
 *
 * @status active
 * @phase 96
 * @depends zustand, ../types/chat, three
 * @used_by App.tsx, ChatPanel.tsx, FileCard.tsx, TreeVisualization.tsx, most components
 */
import { create } from 'zustand';
import type { ChatMessage, WorkflowStatus } from '../types/chat';
import type { PerspectiveCamera } from 'three';

// Backend node types
export type VetkaNodeType = 'root' | 'branch' | 'leaf';

export interface TreeNode {
  id: string;
  path: string;
  name: string;
  type: 'file' | 'folder' | 'chat' | 'artifact';
  backendType: VetkaNodeType;
  depth: number;
  parentId: string | null;
  position: { x: number; y: number; z: number };
  color: string;
  extension?: string;
  semanticPosition?: {
    x: number;
    y: number;
    z: number;
    knowledgeLevel: number;
  };
  children?: string[];
  isGhost?: boolean;  // Phase 90.11: Deleted from disk but kept in memory
  opacity?: number;   // Phase 90.11: Transparency for ghost files (0.3 for ghosts)
  // MARKER_108_3_CHAT_METADATA: Phase 108.3 - Chat node metadata
  metadata?: {
    chat_id?: string;
    message_count?: number;
    participants?: string[];
    decay_factor?: number;
    last_activity?: string;
    context_type?: string;
  };
}

export interface TreeEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
}

// Chat message from agent
export interface AgentMessage {
  id: string;
  agent: string;
  content: string;
  timestamp: number;
  artifacts?: Array<{
    name: string;
    content: string;
    type: string;
    language?: string;
  }>;
  sourceFiles?: string[];
}

// Camera control command
export interface CameraCommand {
  target: string;
  zoom: 'close' | 'medium' | 'far';
  highlight: boolean;
}

// [PHASE70-M1] useStore.ts: Camera ref field — IMPLEMENTED

interface TreeState {
  nodes: Record<string, TreeNode>;
  edges: TreeEdge[];
  rootPath: string | null;

  selectedId: string | null;
  hoveredId: string | null;
  highlightedId: string | null;  // Legacy single highlight
  // Phase 69: Multi-highlight support
  highlightedIds: Set<string>;
  isLoading: boolean;
  error: string | null;

  isSocketConnected: boolean;
  isDraggingAny: boolean;

  // Legacy agent messages (for backwards compat)
  messages: AgentMessage[];

  // New chat system
  chatMessages: ChatMessage[];
  currentWorkflow: WorkflowStatus | null;
  isTyping: boolean;
  streamingContent: string;
  conversationId: string | null;

  // Camera
  cameraCommand: CameraCommand | null;
  // Phase 70: Camera ref for viewport context
  cameraRef: PerspectiveCamera | null;

  // Phase 61: Pinned files for multi-file context
  pinnedFileIds: string[];

  // FIX_109.4: Current chat ID for unified ID system (solo chats like groups)
  currentChatId: string | null;
  setCurrentChatId: (id: string | null) => void;

  setNodes: (nodes: TreeNode[]) => void;
  setNodesFromRecord: (nodes: Record<string, TreeNode>) => void;
  setEdges: (edges: TreeEdge[]) => void;
  selectNode: (id: string | null) => void;
  hoverNode: (id: string | null) => void;
  highlightNode: (id: string | null) => void;
  // Phase 69: Multi-highlight methods
  highlightNodes: (ids: string[]) => void;
  clearHighlights: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setSocketConnected: (connected: boolean) => void;
  setDraggingAny: (dragging: boolean) => void;
  updateNodePosition: (id: string, position: { x: number; y: number; z: number }) => void;
  addNode: (node: TreeNode) => void;
  removeNode: (id: string) => void;

  // Legacy chat
  addMessage: (message: AgentMessage) => void;
  clearMessages: () => void;

  // New chat system
  addChatMessage: (msg: ChatMessage) => void;
  updateChatMessage: (id: string, updates: Partial<ChatMessage>) => void;
  setWorkflowStatus: (status: WorkflowStatus | null) => void;
  setIsTyping: (typing: boolean) => void;
  appendStreamingContent: (delta: string) => void;
  clearStreamingContent: () => void;
  clearChat: () => void;
  setConversationId: (id: string | null) => void;

  // Camera
  setCameraCommand: (command: CameraCommand | null) => void;
  // Phase 70: Camera ref setter
  setCameraRef: (camera: PerspectiveCamera | null) => void;

  // Phase 61: Pinned files actions
  togglePinFile: (nodeId: string) => void;
  pinSubtree: (rootId: string) => void;
  clearPinnedFiles: () => void;
  // Phase 100.2: Set pinned files from backend (for persistence)
  setPinnedFiles: (ids: string[]) => void;

  // Phase 65: Smart pin based on node type
  pinNodeSmart: (nodeId: string) => void;

  // Phase 65: Grab mode for Blender-style node movement
  grabMode: boolean;
  setGrabMode: (enabled: boolean) => void;
}

export const useStore = create<TreeState>((set) => ({
  nodes: {},
  edges: [],
  rootPath: null,
  selectedId: null,
  hoveredId: null,
  highlightedId: null,
  // Phase 69: Multi-highlight support
  highlightedIds: new Set<string>(),
  isLoading: false,
  error: null,
  isSocketConnected: false,
  isDraggingAny: false,
  messages: [],
  chatMessages: [],
  currentWorkflow: null,
  isTyping: false,
  streamingContent: '',
  conversationId: null,
  cameraCommand: null,
  // Phase 70: Camera ref for viewport context
  cameraRef: null,

  // Phase 61: Pinned files
  pinnedFileIds: [],

  // FIX_109.4: Current chat ID for unified ID system
  currentChatId: null,
  setCurrentChatId: (id) => set({ currentChatId: id }),

  // Phase 65: Grab mode
  grabMode: false,

  setNodes: (nodesList) => set({
    nodes: Object.fromEntries(nodesList.map(n => [n.id, n])),
    rootPath: nodesList.find(n => n.depth === 0)?.path || null
  }),

  setNodesFromRecord: (nodes) => set({
    nodes,
    rootPath: Object.values(nodes).find(n => n.depth === 0)?.path || null
  }),

  setEdges: (edges) => set({ edges }),

  selectNode: (id) => set({ selectedId: id }),

  hoverNode: (id) => set({ hoveredId: id }),

  highlightNode: (id) => set({ highlightedId: id }),

  // Phase 69: Multi-highlight implementation
  highlightNodes: (ids) => set({ highlightedIds: new Set(ids) }),
  clearHighlights: () => set({ highlightedIds: new Set() }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  setSocketConnected: (isSocketConnected) => set({ isSocketConnected }),

  setDraggingAny: (isDraggingAny) => set({ isDraggingAny }),

  updateNodePosition: (id, position) => set((state) => {
    if (!state.nodes[id]) return state;
    return {
      nodes: {
        ...state.nodes,
        [id]: { ...state.nodes[id], position }
      }
    };
  }),

  addNode: (node) => set((state) => ({
    nodes: { ...state.nodes, [node.id]: node }
  })),

  removeNode: (id) => set((state) => {
    const { [id]: _, ...rest } = state.nodes;
    return { nodes: rest };
  }),

  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),

  clearMessages: () => set({ messages: [] }),

  // New chat system
  addChatMessage: (msg) => set((state) => ({
    chatMessages: [...state.chatMessages, msg]
  })),

  updateChatMessage: (id, updates) => set((state) => ({
    chatMessages: state.chatMessages.map((m) =>
      m.id === id ? { ...m, ...updates } : m
    )
  })),

  setWorkflowStatus: (currentWorkflow) => set({ currentWorkflow }),

  setIsTyping: (isTyping) => set({ isTyping }),

  appendStreamingContent: (delta) => set((state) => ({
    streamingContent: state.streamingContent + delta
  })),

  clearStreamingContent: () => set({ streamingContent: '' }),

  clearChat: () => set({ chatMessages: [], currentWorkflow: null, streamingContent: '' }),

  setConversationId: (conversationId) => set({ conversationId }),

  setCameraCommand: (cameraCommand) => set({ cameraCommand }),

  // Phase 70: Camera ref setter
  setCameraRef: (cameraRef) => set({ cameraRef }),

  // Phase 61: Pinned files actions
  togglePinFile: (nodeId) => set((state) => ({
    pinnedFileIds: state.pinnedFileIds.includes(nodeId)
      ? state.pinnedFileIds.filter(id => id !== nodeId)
      : [...state.pinnedFileIds, nodeId]
  })),

  pinSubtree: (rootId) => set((state) => {
    const newPinned = new Set(state.pinnedFileIds);

    // Recursive helper to collect all descendants (files only)
    const addDescendants = (id: string) => {
      const node = state.nodes[id];
      if (!node) return;

      // Pin leaf nodes (files)
      if (node.type === 'file') {
        newPinned.add(id);
      }

      // Find children by parentId
      Object.values(state.nodes)
        .filter(n => n.parentId === id)
        .forEach(child => addDescendants(child.id));
    };

    addDescendants(rootId);
    return { pinnedFileIds: [...newPinned] };
  }),

  clearPinnedFiles: () => set({ pinnedFileIds: [] }),

  // Phase 100.2: Set pinned files from backend (for persistence)
  setPinnedFiles: (ids) => set({ pinnedFileIds: ids }),

  // Phase 65: Smart pin based on node type (file → toggle, folder → subtree)
  pinNodeSmart: (nodeId) => set((state) => {
    const node = state.nodes[nodeId];
    if (!node) return state;

    // If folder → pin entire subtree (all file descendants)
    if (node.type === 'folder') {
      const newPinned = new Set(state.pinnedFileIds);

      const addDescendants = (id: string) => {
        const n = state.nodes[id];
        if (!n) return;
        if (n.type === 'file') {
          newPinned.add(id);
        }
        Object.values(state.nodes)
          .filter(child => child.parentId === id)
          .forEach(child => addDescendants(child.id));
      };

      addDescendants(nodeId);
      return { pinnedFileIds: [...newPinned] };
    }

    // If file → toggle single pin
    return {
      pinnedFileIds: state.pinnedFileIds.includes(nodeId)
        ? state.pinnedFileIds.filter(id => id !== nodeId)
        : [...state.pinnedFileIds, nodeId]
    };
  }),

  // Phase 65: Grab mode toggle
  setGrabMode: (grabMode) => set({ grabMode }),
}));
