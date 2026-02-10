/**
 * MARKER_135.1B: Sugiyama layout with Bottom-to-Top direction.
 * Uses dagre for automatic layered layout.
 * Root at bottom, proposals/results at top — like VETKA 3D tree.
 *
 * @phase 135.1
 * @status active
 */

import dagre from 'dagre';
import type { Node, Edge } from '@xyflow/react';
import type { DAGNode, DAGEdge, NodeStatus, DAGNodeType } from '../types/dag';

// Node dimensions by type
const NODE_DIMENSIONS: Record<DAGNodeType, { width: number; height: number }> = {
  task: { width: 160, height: 60 },
  agent: { width: 120, height: 50 },
  subtask: { width: 140, height: 45 },
  proposal: { width: 140, height: 55 },
};

// Nolan monochrome palette
export const NOLAN_PALETTE = {
  // Backgrounds
  bg: '#0a0a0a',
  bgNode: '#111111',
  bgPanel: '#0d0d0d',

  // Borders & Lines
  borderDim: '#333333',
  borderNormal: '#555555',
  borderBright: '#888888',
  borderAccent: '#e0e0e0',

  // Text
  textDim: '#555555',
  textNormal: '#888888',
  textBright: '#cccccc',
  textAccent: '#e0e0e0',

  // Status (subtle, not saturated)
  statusPending: '#444444',
  statusRunning: '#e0e0e0',
  statusDone: '#6a8a6a',
  statusFailed: '#8a6a6a',

  // Confidence (for proposals)
  confHigh: '#6a8a6a',
  confMid: '#8a8a6a',
  confLow: '#8a6a6a',

  // Edges
  edgeStructural: '#4a5a4a',
  edgeDataflow: '#5a6a7a',
  edgeTemporal: '#6a5a4a',
};

/**
 * Get border color based on node status.
 */
export function getStatusBorderColor(status: NodeStatus): string {
  switch (status) {
    case 'running': return NOLAN_PALETTE.statusRunning;
    case 'done': return NOLAN_PALETTE.statusDone;
    case 'failed': return NOLAN_PALETTE.statusFailed;
    default: return NOLAN_PALETTE.statusPending;
  }
}

/**
 * Get confidence glow color for proposals.
 */
export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.85) return NOLAN_PALETTE.confHigh;
  if (confidence >= 0.5) return NOLAN_PALETTE.confMid;
  return NOLAN_PALETTE.confLow;
}

/**
 * Apply Sugiyama BT layout using dagre.
 * Returns positioned xyflow nodes and edges.
 */
export function layoutSugiyamaBT(
  dagNodes: DAGNode[],
  dagEdges: DAGEdge[]
): { nodes: Node[]; edges: Edge[] } {
  // Create dagre graph
  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: 'BT',     // Bottom-to-Top: root at bottom
    ranksep: 80,       // Vertical spacing between layers
    nodesep: 50,       // Horizontal spacing between nodes
    marginx: 20,
    marginy: 20,
  });
  g.setDefaultEdgeLabel(() => ({}));

  // Add nodes to dagre
  for (const node of dagNodes) {
    const dims = NODE_DIMENSIONS[node.type] || NODE_DIMENSIONS.subtask;
    g.setNode(node.id, { width: dims.width, height: dims.height });
  }

  // Add edges to dagre
  for (const edge of dagEdges) {
    g.setEdge(edge.source, edge.target);
  }

  // Run layout
  dagre.layout(g);

  // Convert to xyflow nodes
  const nodes: Node[] = dagNodes.map((node) => {
    const dagreNode = g.node(node.id);
    const dims = NODE_DIMENSIONS[node.type] || NODE_DIMENSIONS.subtask;

    return {
      id: node.id,
      type: node.type,          // Custom node type
      position: {
        x: dagreNode.x - dims.width / 2,
        y: dagreNode.y - dims.height / 2,
      },
      data: {
        label: node.label,
        status: node.status,
        role: node.role,
        confidence: node.confidence,
        tokens: node.tokens,
        durationS: node.durationS,
        model: node.model,
        taskId: node.taskId,
        layer: node.layer,
      },
    };
  });

  // Convert to xyflow edges
  const edges: Edge[] = dagEdges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    animated: edge.type === 'temporal' || edge.animated,
    style: {
      stroke: edge.type === 'structural'
        ? NOLAN_PALETTE.edgeStructural
        : edge.type === 'dataflow'
          ? NOLAN_PALETTE.edgeDataflow
          : NOLAN_PALETTE.edgeTemporal,
      strokeWidth: 1 + edge.strength * 2,
      opacity: 0.6 + edge.strength * 0.4,
    },
  }));

  return { nodes, edges };
}

/**
 * Create hardcoded test data for development.
 */
export function createTestDAGData(): { nodes: DAGNode[]; edges: DAGEdge[] } {
  const taskId = 'test_task_001';

  const nodes: DAGNode[] = [
    // Layer 0: Root task
    {
      id: `task_${taskId}`,
      type: 'task',
      label: 'Add caching to API',
      status: 'running',
      layer: 0,
      taskId,
    },

    // Layer 1: Agents
    {
      id: `agent_${taskId}_scout`,
      type: 'agent',
      label: '@scout',
      status: 'done',
      layer: 1,
      parentId: `task_${taskId}`,
      taskId,
      role: 'scout',
      durationS: 3,
    },
    {
      id: `agent_${taskId}_architect`,
      type: 'agent',
      label: '@architect',
      status: 'done',
      layer: 1,
      parentId: `task_${taskId}`,
      taskId,
      role: 'architect',
      model: 'kimi-k2.5',
      durationS: 8,
    },
    {
      id: `agent_${taskId}_researcher`,
      type: 'agent',
      label: '@researcher',
      status: 'done',
      layer: 1,
      parentId: `task_${taskId}`,
      taskId,
      role: 'researcher',
      model: 'grok-fast-4.1',
      durationS: 5,
    },

    // Layer 2: Subtasks
    {
      id: `sub_${taskId}_0`,
      type: 'subtask',
      label: 'Create cache service',
      status: 'done',
      layer: 2,
      parentId: `agent_${taskId}_architect`,
      taskId,
      tokens: 1240,
    },
    {
      id: `sub_${taskId}_1`,
      type: 'subtask',
      label: 'Add Redis client',
      status: 'running',
      layer: 2,
      parentId: `agent_${taskId}_architect`,
      taskId,
      tokens: 890,
    },
    {
      id: `sub_${taskId}_2`,
      type: 'subtask',
      label: 'Update API endpoints',
      status: 'pending',
      layer: 2,
      parentId: `agent_${taskId}_architect`,
      taskId,
    },

    // Layer 3: Verifier
    {
      id: `agent_${taskId}_verifier`,
      type: 'agent',
      label: '@verifier',
      status: 'pending',
      layer: 3,
      parentId: `sub_${taskId}_0`,
      taskId,
      role: 'verifier',
    },

    // Layer 4: Proposal
    {
      id: `prop_${taskId}`,
      type: 'proposal',
      label: 'Proposal: Cache',
      status: 'pending',
      layer: 4,
      parentId: `agent_${taskId}_verifier`,
      taskId,
      confidence: 0.72,
    },
  ];

  const edges: DAGEdge[] = [
    // Task → Agents
    { id: 'e1', source: `task_${taskId}`, target: `agent_${taskId}_scout`, type: 'structural', strength: 0.8 },
    { id: 'e2', source: `task_${taskId}`, target: `agent_${taskId}_architect`, type: 'structural', strength: 0.9 },
    { id: 'e3', source: `task_${taskId}`, target: `agent_${taskId}_researcher`, type: 'structural', strength: 0.7 },

    // Agents → Subtasks
    { id: 'e4', source: `agent_${taskId}_architect`, target: `sub_${taskId}_0`, type: 'dataflow', strength: 0.8 },
    { id: 'e5', source: `agent_${taskId}_architect`, target: `sub_${taskId}_1`, type: 'dataflow', strength: 0.8 },
    { id: 'e6', source: `agent_${taskId}_architect`, target: `sub_${taskId}_2`, type: 'dataflow', strength: 0.6 },

    // Subtask → Verifier
    { id: 'e7', source: `sub_${taskId}_0`, target: `agent_${taskId}_verifier`, type: 'temporal', strength: 0.7 },
    { id: 'e8', source: `sub_${taskId}_1`, target: `agent_${taskId}_verifier`, type: 'temporal', strength: 0.7 },
    { id: 'e9', source: `sub_${taskId}_2`, target: `agent_${taskId}_verifier`, type: 'temporal', strength: 0.5 },

    // Verifier → Proposal
    { id: 'e10', source: `agent_${taskId}_verifier`, target: `prop_${taskId}`, type: 'structural', strength: 0.9 },
  ];

  return { nodes, edges };
}
