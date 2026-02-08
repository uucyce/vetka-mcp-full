/**
 * API response converters for VETKA backend data.
 * Transforms VetkaApiNode/Edge to frontend TreeNode/TreeEdge format.
 * Supports both new API format and legacy format for backwards compatibility.
 *
 * @status active
 * @phase 96
 * @depends ../store/useStore
 * @used_by useTreeData.ts, socket handlers, API fetch functions
 */
import { TreeNode, TreeEdge, VetkaNodeType } from '../store/useStore';
import { ChatNode } from '../types/treeNodes';
import type { ChatNodeAPI, ChatEdgeAPI } from './api';

// Backend API types
export interface VetkaApiNode {
  id: string;
  type: VetkaNodeType;
  name: string;
  parent_id?: string;
  metadata: {
    path: string;
    extension?: string;
    depth: number;
    is_ghost?: boolean;  // Phase 90.11: Deleted from disk
  };
  visual_hints: {
    layout_hint: { expected_x: number; expected_y: number; expected_z: number };
    color: string;
    opacity?: number;  // Phase 90.11: Transparency for ghost files
  };
  semantic_position?: {
    x: number;
    y: number;
    z: number;
    knowledge_level: number;
  };
}

export interface VetkaApiEdge {
  from: string;
  to: string;
  semantics: string;
}

export interface VetkaApiResponse {
  tree: {
    nodes: VetkaApiNode[];
    edges: VetkaApiEdge[];
  };
}

// Default colors for fallback
const DEFAULT_COLORS: Record<VetkaNodeType, string> = {
  root: '#6366f1',
  branch: '#374151',
  leaf: '#1f2937',
};

export function convertApiNode(apiNode: VetkaApiNode): TreeNode {
  const backendType = apiNode.type;

  // Phase 27.9 FIX: Handle nodes without metadata (e.g., root node)
  const metadata = apiNode.metadata || { path: apiNode.id, depth: 0 };
  const visualHints = apiNode.visual_hints || {
    layout_hint: { expected_x: 0, expected_y: 0, expected_z: 0 },
    color: DEFAULT_COLORS[backendType]
  };
  const layoutHint = visualHints.layout_hint || { expected_x: 0, expected_y: 0, expected_z: 0 };

  // Phase 90.11: Ghost files (deleted from disk)
  const isGhost = metadata.is_ghost ?? false;
  const opacity = visualHints.opacity ?? (isGhost ? 0.3 : 1.0);

  return {
    id: apiNode.id,
    path: metadata.path || apiNode.id,
    name: apiNode.name,
    type: backendType === 'leaf' ? 'file' : 'folder',
    backendType,
    depth: metadata.depth ?? 0,
    parentId: apiNode.parent_id || null,
    position: {
      x: layoutHint.expected_x ?? 0,
      y: layoutHint.expected_y ?? 0,
      z: layoutHint.expected_z ?? 0,
    },
    color: visualHints.color || DEFAULT_COLORS[backendType],
    extension: metadata.extension,
    semanticPosition: apiNode.semantic_position
      ? {
          x: apiNode.semantic_position.x,
          y: apiNode.semantic_position.y,
          z: apiNode.semantic_position.z,
          knowledgeLevel: apiNode.semantic_position.knowledge_level,
        }
      : undefined,
    isGhost,  // Phase 90.11
    opacity,  // Phase 90.11
  };
}

export function convertApiEdge(apiEdge: VetkaApiEdge, index: number): TreeEdge {
  return {
    id: `edge_${index}`,
    source: apiEdge.from,
    target: apiEdge.to,
    type: apiEdge.semantics,
  };
}

export function convertApiResponse(response: VetkaApiResponse): {
  nodes: Record<string, TreeNode>;
  edges: TreeEdge[];
} {
  const nodes: Record<string, TreeNode> = {};

  for (const apiNode of response.tree.nodes) {
    const node = convertApiNode(apiNode);
    // MARKER_119.2K: Phase 119.2 - Pass through heatScore from API
    node.heatScore = (apiNode as any).heatScore ?? 0;
    nodes[node.id] = node;
  }

  const edges = response.tree.edges.map((e, i) => convertApiEdge(e, i));

  // MARKER_119.2L: Phase 119.2 - Build children arrays from edges
  // This is critical for labelScoring which uses children.length
  for (const edge of edges) {
    const parentNode = nodes[edge.source];
    if (parentNode) {
      if (!parentNode.children) {
        parentNode.children = [];
      }
      parentNode.children.push(edge.target);
    }
  }

  // Debug log
  const nodesWithChildren = Object.values(nodes).filter(n => (n.children?.length ?? 0) > 0);
  console.log(`[apiConverter] Phase 119.2: Built children for ${nodesWithChildren.length} nodes`);

  return { nodes, edges };
}

// Convert legacy format (for backwards compatibility with existing API)
export interface LegacyApiNode {
  path: string;
  name: string;
  type: 'file' | 'folder';
  depth: number;
  parent_path?: string | null;
  position?: { x: number; y: number; z: number };
  children?: string[];
}

export interface LegacyApiEdge {
  source: string;
  target: string;
}

export function convertLegacyNode(legacyNode: LegacyApiNode): TreeNode {
  const backendType: VetkaNodeType =
    legacyNode.depth === 0 ? 'root' :
    legacyNode.type === 'folder' ? 'branch' : 'leaf';

  return {
    id: legacyNode.path,
    path: legacyNode.path,
    name: legacyNode.name,
    type: legacyNode.type,
    backendType,
    depth: legacyNode.depth,
    parentId: legacyNode.parent_path || null,
    position: legacyNode.position || { x: 0, y: 0, z: 0 },
    color: DEFAULT_COLORS[backendType],
    children: legacyNode.children,
  };
}

export function convertLegacyEdge(legacyEdge: LegacyApiEdge, index: number): TreeEdge {
  return {
    id: `edge_${index}`,
    source: legacyEdge.source,
    target: legacyEdge.target,
    type: 'parent-child',
  };
}

// MARKER_108_CHAT_FRONTEND: Phase 108.2 - Chat node converters

/**
 * Convert ChatNodeAPI from backend to frontend ChatNode type
 * Integrates chat nodes into the tree visualization
 */
export function convertChatNode(apiChatNode: ChatNodeAPI): ChatNode {
  return {
    id: apiChatNode.id,
    type: 'chat',
    parentId: apiChatNode.parent_id || '',
    name: apiChatNode.name,
    participants: apiChatNode.metadata.participants,
    messageCount: apiChatNode.metadata.message_count,
    lastActivity: new Date(apiChatNode.metadata.last_activity),
    artifacts: [],
    status: 'active',
    decay_factor: apiChatNode.metadata.decay_factor,
    // Store chat_id for backend correlation
    userId: apiChatNode.metadata.chat_id,
  };
}

/**
 * Convert ChatEdgeAPI from backend to TreeEdge format
 */
export function convertChatEdge(apiChatEdge: ChatEdgeAPI, index: number): TreeEdge {
  return {
    id: `chat_edge_${index}`,
    source: apiChatEdge.from,
    target: apiChatEdge.to,
    type: 'chat',
  };
}

/**
 * Convert ChatNode to TreeNode for unified 3D rendering
 * This allows chat nodes to render alongside file/folder nodes
 */
export function chatNodeToTreeNode(chatNode: ChatNode, position: { x: number; y: number; z: number }): TreeNode {
  return {
    id: chatNode.id,
    path: chatNode.id, // Chat nodes don't have file paths
    name: chatNode.name,
    type: 'chat', // MARKER_108_3_CHAT_TYPE: Phase 108.3 - Render as 'chat' type for FileCard
    backendType: 'leaf',
    depth: 0, // Will be calculated from parent
    parentId: chatNode.parentId,
    position,
    color: '#4a9eff', // Blue for chat nodes
    opacity: chatNode.decay_factor,
    // MARKER_108_3_CHAT_METADATA: Phase 108.3 - Include chat metadata for click handling
    metadata: {
      chat_id: chatNode.userId, // userId stores the backend chat_id
      message_count: chatNode.messageCount,
      participants: chatNode.participants,
      decay_factor: chatNode.decay_factor,
      last_activity: chatNode.lastActivity.toISOString(),
      context_type: 'chat',
    },
  };
}
