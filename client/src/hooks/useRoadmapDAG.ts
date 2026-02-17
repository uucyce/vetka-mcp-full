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

import { useState, useCallback } from 'react';
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
// MARKER_154.6A: All roadmap nodes use RoadmapTaskNode for unified rendering
const LAYER_NODE_TYPE: Record<string, string> = {
  core: 'roadmap_task',
  feature: 'roadmap_task',
  enhancement: 'roadmap_task',
  test: 'roadmap_task',
  docs: 'roadmap_task',
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
  // MARKER_154.6A: Roadmap-level DAGNode with extended fields for RoadmapTaskNode
  return {
    id: node.id,
    type: (LAYER_NODE_TYPE[layer] || 'task') as any,
    label: node.label || node.id,
    status: (node.data?.status || LAYER_STATUS_MAP[layer] || 'pending') as any,
    layer: layer,
    taskId: node.data?.taskId || node.id,
    description: node.data?.description || '',
  } as DAGNode;
}

function mapRoadmapEdge(edge: any): DAGEdge {
  return {
    id: edge.id || `e-${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    type: 'dependency',
    strength: 1.0,  // MARKER_154.6A: Roadmap dependency edges at full strength
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
