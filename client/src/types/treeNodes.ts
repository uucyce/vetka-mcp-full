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
