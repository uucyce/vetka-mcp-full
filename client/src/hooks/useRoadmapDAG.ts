/**
 * MARKER_153.5B: useRoadmapDAG — hook for fetching and managing roadmap DAG data.
 *
 * Fetches from GET /api/mcc/roadmap and converts to DAGNode/DAGEdge format.
 * Returns roadmap nodes ready for DAGView rendering.
 *
 * @phase 153
 * @wave 5
 * @status active
 */

import { useState, useCallback, useEffect } from 'react';
import type { DAGNode, DAGEdge } from '../types/dag';

const API_BASE = 'http://localhost:5001/api';

// Layer → visual style mapping
const LAYER_STATUS_MAP: Record<string, string> = {
  core: 'active',
  feature: 'pending',
  enhancement: 'pending',
  test: 'pending',
  docs: 'completed',
};

// Layer → node type mapping for xyflow rendering
const LAYER_NODE_TYPE: Record<string, string> = {
  core: 'task',
  feature: 'agent',
  enhancement: 'subtask',
  test: 'subtask',
  docs: 'proposal',
};

interface RoadmapData {
  nodes: DAGNode[];
  edges: DAGEdge[];
  loading: boolean;
  error: string | null;
}

/**
 * Convert roadmap API response to DAGNode/DAGEdge format.
 */
function mapRoadmapNode(node: any, index: number): DAGNode {
  const layer = node.data?.layer || 'core';
  return {
    id: node.id,
    type: (LAYER_NODE_TYPE[layer] || 'task') as any,
    label: node.label || node.id,
    status: (node.data?.status || LAYER_STATUS_MAP[layer] || 'pending') as any,
    layer: layer,
    description: node.data?.description || '',
    // Use positions from API or generate grid layout
    // The API returns {x, y} positions that are sequential
  };
}

function mapRoadmapEdge(edge: any): DAGEdge {
  return {
    id: edge.id || `e-${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    type: 'dependency',
  };
}

export function useRoadmapDAG(): RoadmapData & {
  fetchRoadmap: () => Promise<void>;
  regenerateRoadmap: () => Promise<void>;
} {
  const [nodes, setNodes] = useState<DAGNode[]>([]);
  const [edges, setEdges] = useState<DAGEdge[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRoadmap = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/mcc/roadmap`);
      if (res.status === 404) {
        // No project configured — not an error
        setNodes([]);
        setEdges([]);
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      const mappedNodes = (data.nodes || []).map(mapRoadmapNode);
      const mappedEdges = (data.edges || []).map(mapRoadmapEdge);

      setNodes(mappedNodes);
      setEdges(mappedEdges);
    } catch (err) {
      console.warn('[Roadmap] Fetch failed:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setNodes([]);
      setEdges([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const regenerateRoadmap = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/mcc/roadmap/generate`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // Refetch after generation
      await fetchRoadmap();
    } catch (err) {
      console.warn('[Roadmap] Regenerate failed:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [fetchRoadmap]);

  return { nodes, edges, loading, error, fetchRoadmap, regenerateRoadmap };
}
