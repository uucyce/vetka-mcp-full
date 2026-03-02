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
import { API_BASE } from '../config/api.config';

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
  // MARKER_119.2G: Phase 119.2 - Heat score for label visibility
  heatScore?: number; // 0.0-1.0, higher = more active directory
  // MARKER_108_3_CHAT_METADATA: Phase 108.3 - Chat node metadata
  metadata?: {
    chat_id?: string;
    message_count?: number;
    participants?: string[];
    decay_factor?: number;
    last_activity?: string;
    context_type?: string;
    is_favorite?: boolean;
    path?: string;
    artifact_id?: string;
    [key: string]: any;
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

// MARKER_140.WEB_CTX_STATE: Active web context for chat/model prompt injection
export interface ActiveWebContext {
  url: string;
  title?: string;
  summary?: string;
  source?: 'unified_search' | 'native_window' | 'saved_web_artifact' | 'manual';
  web_open?: boolean;
  captured_at?: string;
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
  // MARKER_140.WEB_CTX_STATE: Optional live web context (does not replace viewport context)
  activeWebContext: ActiveWebContext | null;

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
  moveNodeWithChildren: (id: string, position: { x: number; y: number; z: number }) => void;
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
  // MARKER_140.WEB_CTX_STATE: Mutators for live web context
  setActiveWebContext: (ctx: ActiveWebContext | null) => void;
  clearActiveWebContext: () => void;

  // Phase 65: Smart pin based on node type
  pinNodeSmart: (nodeId: string) => void;

  // Phase 65: Grab mode for Blender-style node movement
  grabMode: boolean;
  setGrabMode: (enabled: boolean) => void;

  // Phase 113.1: Persistent Spatial Memory
  savePositions: () => void;
  loadPositions: () => void;

  // Phase 113.4: Label Championship — score-based label selection
  selectedLabelIds: string[];
  setSelectedLabels: (labelIds: string[]) => void;
  // Phase 153: Toggle media chunk nodes/edges visibility in tree viewport
  showMediaChunks: boolean;
  setShowMediaChunks: (enabled: boolean) => void;

  // Phase 113.4: Persist positions toggle (DevPanel control)
  persistPositions: boolean;
  setPersistPositions: (enabled: boolean) => void;
  resetLayout: () => void;

  // MARKER_123.2B: Phase 123 - Activity heat score for glow effect
  setNodeHeatScore: (nodeId: string, intensity: number) => void;

  // MARKER_126.9B: Selected API key for pipeline dispatch
  selectedKey: { provider: string; key_masked: string } | null;
  setSelectedKey: (key: { provider: string; key_masked: string } | null) => void;
  clearSelectedKey: () => void;

  // MARKER_152.FIX3: Starred keys & models (persisted to data/favorites.json)
  favoriteKeys: string[];       // ["polza:pza_****9PUM"]
  favoriteModels: string[];     // ["x-ai/grok-4.1-fast"]
  setFavoriteKeys: (keys: string[]) => void;
  setFavoriteModels: (models: string[]) => void;
  toggleFavoriteKey: (key: string) => void;
  toggleFavoriteModel: (modelId: string) => void;
  loadFavorites: () => Promise<void>;
}

// Phase 113.1: Persistent Spatial Memory
const POSITIONS_STORAGE_KEY = 'vetka_node_positions';
let _positionSaveTimer: ReturnType<typeof setTimeout> | null = null;

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

function inferLayoutBiasFromPositionMap(positionMap: Record<string, { x: number; y: number; z: number }>) {
  const points = Object.values(positionMap);
  if (points.length < 3) return null;
  const xs = points.map(p => p.x);
  const ys = points.map(p => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spreadX = Math.max(1, maxX - minX);
  const spreadY = Math.max(1, maxY - minY);
  const ratio = spreadY / spreadX;
  const compactness = points.length / (spreadX * spreadY);
  return {
    vertical_separation_bias: clamp((ratio - 0.75) * 1.2, -1, 1),
    sibling_spacing_bias: clamp((spreadX / Math.max(1, points.length * 50)) - 1, -1, 1),
    branch_compactness_bias: clamp((compactness * 120000) - 0.5, -1, 1),
    focus_overlay_preference: 'focus_only',
    pin_persistence_preference: 'pin_first',
    confidence: clamp(0.55 + Math.log10(points.length + 1) * 0.2, 0.55, 0.95),
    sample_count: 1,
    updated_at: new Date().toISOString(),
  };
}

export const useStore = create<TreeState>((set, get) => ({
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
  activeWebContext: null,

  // FIX_109.4: Current chat ID for unified ID system
  currentChatId: null,
  setCurrentChatId: (id) => set({ currentChatId: id }),

  // Phase 65: Grab mode
  grabMode: false,

  // Phase 113.4: Label Championship
  selectedLabelIds: [],
  showMediaChunks: true,
  setShowMediaChunks: (enabled) => set({ showMediaChunks: enabled }),
  persistPositions: false,  // OFF by default (Phase 113.3 lesson: persistence = risky without toggle)

  // MARKER_126.9B: Selected API key for pipeline dispatch
  selectedKey: null,
  setSelectedKey: (key) => set({ selectedKey: key }),
  clearSelectedKey: () => set({ selectedKey: null }),

  // MARKER_152.FIX3: Starred keys & models
  favoriteKeys: [],
  favoriteModels: [],
  setFavoriteKeys: (keys) => set({ favoriteKeys: keys }),
  setFavoriteModels: (models) => set({ favoriteModels: models }),
  toggleFavoriteKey: (key) => {
    const current = get().favoriteKeys;
    const next = current.includes(key)
      ? current.filter(k => k !== key)
      : [...current, key];
    set({ favoriteKeys: next });
    // Persist to backend
    fetch('/api/favorites', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keys: next, models: get().favoriteModels }),
    }).catch(() => {});
  },
  toggleFavoriteModel: (modelId) => {
    const current = get().favoriteModels;
    const next = current.includes(modelId)
      ? current.filter(m => m !== modelId)
      : [...current, modelId];
    set({ favoriteModels: next });
    fetch('/api/favorites', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keys: get().favoriteKeys, models: next }),
    }).catch(() => {});
  },
  loadFavorites: async () => {
    try {
      const res = await fetch('/api/favorites');
      if (res.ok) {
        const data = await res.json();
        set({ favoriteKeys: data.keys || [], favoriteModels: data.models || [] });
      }
    } catch {}
  },

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

  // MARKER_111_DRAG: Move node with all children (branch follows)
  moveNodeWithChildren: (id, newPosition) => set((state) => {
    const node = state.nodes[id];
    if (!node) return state;

    // Calculate delta from old position to new position
    const delta = {
      x: newPosition.x - node.position.x,
      y: newPosition.y - node.position.y,
      z: newPosition.z - node.position.z,
    };

    // Find all descendants recursively
    const findDescendants = (nodeId: string): string[] => {
      const descendants: string[] = [];
      Object.values(state.nodes).forEach((n) => {
        if (n.parentId === nodeId) {
          descendants.push(n.id);
          descendants.push(...findDescendants(n.id));
        }
      });
      return descendants;
    };

    const descendantIds = findDescendants(id);
    const updatedNodes = { ...state.nodes };

    // Update the dragged node
    updatedNodes[id] = {
      ...node,
      position: newPosition,
    };

    // Update all descendants with delta
    descendantIds.forEach((childId) => {
      const child = updatedNodes[childId];
      if (child) {
        updatedNodes[childId] = {
          ...child,
          position: {
            x: child.position.x + delta.x,
            y: child.position.y + delta.y,
            z: child.position.z + delta.z,
          },
        };
      }
    });

    console.log(`[DRAG] Moved ${id} + ${descendantIds.length} children by delta (${delta.x.toFixed(1)}, ${delta.y.toFixed(1)}, ${delta.z.toFixed(1)})`);

    return { nodes: updatedNodes };
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
  setActiveWebContext: (activeWebContext) => set({ activeWebContext }),
  clearActiveWebContext: () => set({ activeWebContext: null }),

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

  // Phase 113.4: Label Championship
  setSelectedLabels: (labelIds) => set({ selectedLabelIds: labelIds }),
  setPersistPositions: (enabled) => set({ persistPositions: enabled }),
  resetLayout: () => {
    localStorage.removeItem(POSITIONS_STORAGE_KEY);
    // Re-fetch from API will reset positions on next load
    console.log('[Layout] Phase 113.4: Positions cache cleared. Reload to apply API defaults.');
  },

  // MARKER_123.2B: Phase 123 - Activity heat score for glow effect
  setNodeHeatScore: (nodeId: string, intensity: number) => set((state) => {
    // Find the node - could be by path or by id
    const possibleIds = [nodeId, nodeId.split('/').pop()];
    let foundId: string | null = null;

    for (const id of possibleIds) {
      if (id && state.nodes[id]) {
        foundId = id;
        break;
      }
    }

    // Also try matching by path
    if (!foundId) {
      for (const [id, node] of Object.entries(state.nodes)) {
        if (node.path === nodeId || node.path.endsWith(nodeId)) {
          foundId = id;
          break;
        }
      }
    }

    if (!foundId) return state;

    return {
      nodes: {
        ...state.nodes,
        [foundId]: {
          ...state.nodes[foundId],
          heatScore: Math.max(0, Math.min(1, intensity)),
        },
      },
    };
  }),

  // Phase 113.1: Persistent Spatial Memory
  savePositions: () => {
    const { nodes, rootPath } = get();
    const entries = Object.values(nodes);
    if (entries.length === 0) return;

    const positionMap: Record<string, { x: number; y: number; z: number }> = {};
    for (const node of entries) {
      positionMap[node.id] = node.position;
    }

    const payload = { positions: positionMap, ts: Date.now() };

    // Immediate: localStorage (offline-first)
    try {
      localStorage.setItem(POSITIONS_STORAGE_KEY, JSON.stringify(payload));
    } catch (e) {
      console.error('[Layout] localStorage save failed:', e);
    }

    // Debounced: backend via socket (500ms)
    if (_positionSaveTimer) clearTimeout(_positionSaveTimer);
    _positionSaveTimer = setTimeout(() => {
      try {
        // Use socket if available, fallback to fetch
        const socketEl = document.querySelector('[data-vetka-socket]') as any;
        if (socketEl?.socket?.emit) {
          socketEl.socket.emit('save_positions', payload);
        } else {
          fetch('/api/layout/positions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          }).catch(() => {});
        }
      } catch (e) {
        console.error('[Layout] Backend save failed:', e);
      }
    }, 500);

    // MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1:
    // Update shared ENGRAM DAG layout intent profile (no raw coordinates).
    try {
      const profile = inferLayoutBiasFromPositionMap(positionMap);
      if (profile) {
        const scopeRoot = String(rootPath || 'default').replace(/\\/g, '/');
        const scopeKey = `dag:${scopeRoot}:architecture`;
        fetch(`${API_BASE}/mcc/layout/preferences`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: 'danila',
            scope_key: scopeKey,
            profile,
          }),
        }).catch(() => {});
      }
    } catch {}

    console.log(`[Layout] Saved ${entries.length} positions`);
  },

  loadPositions: () => {
    try {
      const saved = localStorage.getItem(POSITIONS_STORAGE_KEY);
      if (!saved) return;

      const { positions, ts } = JSON.parse(saved) as {
        positions: Record<string, { x: number; y: number; z: number }>;
        ts: number;
      };

      if (!positions || typeof positions !== 'object') return;

      // Only apply if saved data is less than 7 days old
      const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
      if (Date.now() - ts > MAX_AGE_MS) {
        console.log('[Layout] Saved positions expired, ignoring');
        localStorage.removeItem(POSITIONS_STORAGE_KEY);
        return;
      }

      set((state) => {
        const updatedNodes = { ...state.nodes };
        let applied = 0;

        for (const [id, pos] of Object.entries(positions)) {
          if (updatedNodes[id]) {
            updatedNodes[id] = { ...updatedNodes[id], position: pos };
            applied++;
          }
          // New nodes not in saved positions keep their API-calculated positions
        }

        console.log(`[Layout] Restored ${applied} positions from localStorage (${Object.keys(positions).length} saved, ${Object.keys(updatedNodes).length} total nodes)`);
        return { nodes: updatedNodes };
      });
    } catch (e) {
      console.error('[Layout] Load positions failed:', e);
    }
  },
}));
