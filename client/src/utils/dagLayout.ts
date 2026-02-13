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
// MARKER_144.4: Extended with workflow editor node dimensions
const NODE_DIMENSIONS: Record<DAGNodeType, { width: number; height: number }> = {
  task: { width: 160, height: 60 },
  agent: { width: 120, height: 50 },
  subtask: { width: 140, height: 45 },
  proposal: { width: 140, height: 55 },
  // Phase 144 additions
  condition: { width: 100, height: 100 },   // Diamond shape
  parallel: { width: 160, height: 50 },     // Wide rectangle
  loop: { width: 120, height: 60 },         // Rounded with cycle icon
  transform: { width: 130, height: 50 },    // Trapezoid shape
  group: { width: 240, height: 160 },       // Large container
};

// MARKER_135.5A: Pure VETKA grayscale — like 3D tree on the right
// NO COLORS AT ALL — only black, white, gray
export const NOLAN_PALETTE = {
  // Backgrounds — pure black
  bg: '#000',           // Main background — pure black
  bgLight: '#0a0a0a',   // Cards — almost black
  bgDim: '#050505',     // Panels — darker

  // Borders — gray lines
  border: '#333',       // Default border
  borderDim: '#222',    // Dim border
  borderLight: '#555',  // Active/hover border

  // Text hierarchy — white to gray
  text: '#fff',         // Primary text — white
  textMuted: '#888',    // Secondary text
  textNormal: '#888',   // Alias
  textDim: '#555',      // Tertiary text
  textDimmer: '#333',   // Disabled/placeholder
  textAccent: '#fff',   // Headers — white

  // Status — PURE GRAYSCALE (no colors!)
  statusPending: '#333',      // Dark gray
  statusRunning: '#fff',      // White — active
  statusDone: '#888',         // Medium gray — completed
  statusFailed: '#555',       // Dim gray — failed

  // Status backgrounds — subtle grays
  statusPendingBg: '#0a0a0a',
  statusRunningBg: '#111',
  statusDoneBg: '#0a0a0a',
  statusFailedBg: '#0a0a0a',

  // Confidence — grayscale
  confHigh: '#fff',
  confMid: '#888',
  confLow: '#555',

  // Edges — gray lines like VETKA tree branches
  edgeStructural: '#444',
  edgeDataflow: '#555',
  edgeTemporal: '#333',

  // MARKER_144.4: Workflow editor edge colors
  edgeConditional: '#666',      // Slightly brighter for condition branches
  edgeParallelFork: '#555',
  edgeParallelJoin: '#555',
  edgeFeedback: '#444',         // Dashed loop-back
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

  // MARKER_144.4: Edge color mapping for all edge types
  const getEdgeColor = (edgeType: string): string => {
    switch (edgeType) {
      case 'structural': return NOLAN_PALETTE.edgeStructural;
      case 'dataflow': return NOLAN_PALETTE.edgeDataflow;
      case 'temporal': return NOLAN_PALETTE.edgeTemporal;
      case 'conditional': return NOLAN_PALETTE.edgeConditional;
      case 'parallel_fork': return NOLAN_PALETTE.edgeParallelFork;
      case 'parallel_join': return NOLAN_PALETTE.edgeParallelJoin;
      case 'feedback': return NOLAN_PALETTE.edgeFeedback;
      default: return NOLAN_PALETTE.edgeStructural;
    }
  };

  // Convert to xyflow edges
  const edges: Edge[] = dagEdges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    animated: edge.type === 'temporal' || edge.type === 'feedback' || edge.animated,
    style: {
      stroke: getEdgeColor(edge.type),
      strokeWidth: 1 + edge.strength * 2,
      opacity: 0.6 + edge.strength * 0.4,
      strokeDasharray: edge.type === 'feedback' ? '5 3' : undefined,
    },
    label: (edge as any).label || undefined,
    labelStyle: { fill: NOLAN_PALETTE.textDim, fontSize: 9, fontFamily: 'monospace' },
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
