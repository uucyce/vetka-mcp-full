/**
 * Core API utilities for fetching tree data and health checks.
 *
 * @status active
 * @phase 96
 * @depends ./apiConverter, ../config/api.config
 * @used_by ./hooks/useTreeData, ./components/canvas
 */
import { VetkaApiNode, VetkaApiEdge } from './apiConverter';
import { API_BASE } from '../config/api.config';

// Legacy API node format
export interface ApiTreeNode {
  path: string;
  name: string;
  type: 'file' | 'folder';
  depth: number;
  parent_path: string | null;
  position?: { x: number; y: number; z: number };
  children?: string[];
}

// MARKER_108_CHAT_FRONTEND: Phase 108.2 - Chat nodes API types
export interface ChatNodeAPI {
  id: string;  // "chat_{uuid}"
  type: "chat";
  name: string;
  parent_id: string | null;
  metadata: {
    chat_id: string;
    file_path: string;
    last_activity: string;
    message_count: number;
    participants: string[];
    decay_factor: number;
    context_type: string;
  };
  visual_hints: {
    layout_hint: { expected_x: number; expected_y: number; expected_z: number };
    color: string;
    opacity: number;
  };
}

export interface ChatEdgeAPI {
  from: string;
  to: string;
  semantics: "chat";
  metadata: { type: "chat"; color: string; opacity: number };
}

export interface ArtifactNodeAPI {
  id: string;
  type: "artifact";
  name: string;
  parent_id: string | null;
  metadata: {
    artifact_type?: string;
    artifact_id?: string;
    file_path?: string;
    parent_file_path?: string;
    source_artifact_id?: string;
    start_sec?: number;
    end_sec?: number;
    chunk_text?: string;
    status?: string;
    extension?: string;
    [key: string]: any;
  };
  visual_hints: {
    layout_hint: { expected_x: number; expected_y: number; expected_z: number };
    color: string;
    opacity: number;
  };
}

export interface ArtifactEdgeAPI {
  from: string;
  to: string;
  semantics: string;
  metadata?: { type?: string; [key: string]: any };
}

// API response can be either legacy or new VETKA format
export interface ApiTreeResponse {
  success: boolean;
  // Legacy format
  nodes?: ApiTreeNode[];
  edges?: Array<{ source: string; target: string }>;
  // New VETKA format
  tree?: {
    nodes: VetkaApiNode[];
    edges: VetkaApiEdge[];
  };
  // Phase 108.2: Chat nodes
  chat_nodes?: ChatNodeAPI[];
  chat_edges?: ChatEdgeAPI[];
  artifact_nodes?: ArtifactNodeAPI[];
  artifact_edges?: ArtifactEdgeAPI[];
  error?: string;
}

export async function fetchTreeData(): Promise<ApiTreeResponse> {
  try {
    const response = await fetch(`${API_BASE}/tree/data`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    // MARKER_108_CHAT_FRONTEND: Phase 108.2 - Extract chat nodes from response
    // Backend returns {format, mode, source, tree, chat_nodes?, chat_edges?}
    return {
      success: true,
      tree: data.tree,
      chat_nodes: data.chat_nodes,
      chat_edges: data.chat_edges,
      artifact_nodes: data.artifact_nodes,
      artifact_edges: data.artifact_edges,
    };
  } catch (error) {
    console.error('[API] fetchTreeData error:', error);
    return {
      success: false,
      nodes: [],
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
