/**
 * Chat-as-Tree node type definitions for chat and artifact nodes.
 * Extends base TreeNode with chat conversations and generated artifacts.
 *
 * @status active
 * @phase 96
 * @depends none
 * @used_by ./store/useStore, ./components/canvas/FileCard
 */

/**
 * Chat node: Represents a conversation branching from a source file
 */
export interface ChatNode {
  id: string;
  type: 'chat' | 'group';
  parentId: string; // Source file node ID
  name: string; // "Chat: filename + topic"
  participants: string[]; // Agent IDs: ["@architect", "@qa"]
  messageCount: number;
  lastActivity: Date;
  artifacts: string[]; // Child artifact node IDs
  status: 'active' | 'archived' | 'live';
  preview?: string; // Last message preview
  userId?: string; // For multi-user
  decay_factor?: number; // 1.0 = new, 0.1 = old
}

/**
 * Artifact node: Represents a generated artifact streaming from chat
 */
export interface ArtifactNode {
  id: string;
  type: 'artifact';
  parentId: string; // Parent chat node ID
  name: string; // "refactored.py"
  artifactType: 'code' | 'document' | 'image' | 'data';
  status: 'streaming' | 'done' | 'error';
  progress?: number; // 0-100 during streaming
  preview?: string; // Content preview
  messageId?: string; // Link to chat message that created it
  createdAt: Date;
}

/**
 * Union type for all tree nodes
 * Extend existing TreeNode as needed
 */
export type TreeNodeType = 'file' | 'folder' | 'chat' | 'group' | 'artifact';

/**
 * MARKER_CHAT_NODE_TYPES: Chat and artifact integration into 3D tree
 *
 * Node hierarchy for 3D visualization:
 * File (TreeNode)
 *   ├── Chat (ChatNode) ← parentId references file node id
 *   │   ├── Artifact (ArtifactNode) ← parentId references chat node id
 *   │   └── Message (virtual) ← indexed in Qdrant, not rendered as node
 *   └── Another Chat
 *
 * Folder (TreeNode)
 *   ├── Subfolder
 *   └── Files
 *
 * Positioning strategy:
 * - File position: from layout engine (knowledge_layout.py Sugiyama)
 * - Chat position: slightly offset from parent file (e.g., +5 in X axis)
 * - Artifact position: below chat node (e.g., -10 in Y axis)
 * - Edge colors:
 *   - File→File: '#6b7280' (gray)
 *   - File→Chat: '#4a9eff' (blue)
 *   - Chat→Artifact: '#4a9eff' (blue, slightly brighter)
 *
 * Rendering:
 * - Use FileCard component for all node types (type='chat'|'artifact')
 * - Chat nodes: show participant list in preview
 * - Artifact nodes: show artifact type and status badges
 *
 * Data flow:
 * 1. Backend: API /api/tree/data returns tree nodes + chat nodes
 * 2. Frontend: useTreeData hook fetches and converts to TreeNode[]
 * 3. Store: useStore.setNodes adds to nodes Record<id, TreeNode>
 * 4. Rendering: FileCard renders each node, TreeEdges connects them
 * 5. Interaction: Chat opens in ChatPanel, artifacts in ArtifactPanel
 */
