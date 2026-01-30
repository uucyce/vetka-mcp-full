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
  error?: string;
}

export async function fetchTreeData(): Promise<ApiTreeResponse> {
  try {
    const response = await fetch(`${API_BASE}/tree/data`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    // Backend returns {format, mode, source, tree} - add success flag
    return {
      success: true,
      tree: data.tree,
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
