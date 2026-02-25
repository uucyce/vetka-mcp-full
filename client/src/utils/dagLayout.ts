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
  // MARKER_154.6A: Roadmap task node — wider for badge + progress bar
  roadmap_task: { width: 150, height: 55 },
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
// MARKER_155.2B: Layout options for compact mode (tasks level with many nodes)
export interface LayoutOptions {
  compact?: boolean;  // Reduces spacing for large graphs
  mode?: 'architecture' | 'tasks' | 'workflow';
  // MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1:
  // Cross-surface learned layout intent (no raw coordinates).
  layoutBiasProfile?: {
    vertical_separation_bias?: number;
    sibling_spacing_bias?: number;
    branch_compactness_bias?: number;
    confidence?: number;
  } | null;
}

function laplacianSmoothX(
  nodeIds: string[],
  edges: DAGEdge[],
  initialX: Map<string, number>,
  iterations = 36,
): Map<string, number> {
  const neighbors = new Map<string, Set<string>>();
  for (const id of nodeIds) neighbors.set(id, new Set());
  for (const e of edges) {
    if (!neighbors.has(e.source) || !neighbors.has(e.target) || e.source === e.target) continue;
    neighbors.get(e.source)!.add(e.target);
    neighbors.get(e.target)!.add(e.source);
  }

  let cur = new Map(initialX);
  const anchor = new Map(initialX);
  for (let it = 0; it < iterations; it++) {
    const next = new Map(cur);
    for (const id of nodeIds) {
      const ns = Array.from(neighbors.get(id) || []);
      if (ns.length === 0) continue;
      const avg = ns.reduce((s, n) => s + (cur.get(n) ?? 0), 0) / ns.length;
      const self = cur.get(id) ?? 0;
      const anc = anchor.get(id) ?? 0;
      // Fourier/Laplacian objective: minimize Σ(i,j) (x_i - x_j)^2 while preserving anchors.
      const blended = (self * 0.42) + (avg * 0.44) + (anc * 0.14);
      next.set(id, blended);
    }
    cur = next;
  }
  return cur;
}

function applyArchitectureTreeLayout(
  nodes: Node[],
  dagNodes: DAGNode[],
  compact: boolean,
  layoutBiasProfile?: LayoutOptions['layoutBiasProfile'],
): boolean {
  const idSet = new Set(nodes.map(n => n.id));
  if (idSet.size === 0) return false;

  const parentById = new Map<string, string>();
  const childrenById = new Map<string, string[]>();
  for (const id of idSet) childrenById.set(id, []);

  const resolveParentId = (n: DAGNode): string | null => {
    const meta: any = (n as any).metadata || {};
    const parent = String(meta.parent || '').trim();
    if (!parent) return null;
    if (parent.startsWith('branch:')) return idSet.has(parent) ? parent : null;
    const pid = `dir:${parent}`;
    if (idSet.has(pid)) return pid;
    if (parent === '(root)' && idSet.has('dir:(root)')) return 'dir:(root)';
    return null;
  };

  let links = 0;
  for (const n of dagNodes) {
    if (!idSet.has(n.id)) continue;
    const pid = resolveParentId(n);
    if (!pid || pid === n.id) continue;
    parentById.set(n.id, pid);
    const arr = childrenById.get(pid) || [];
    arr.push(n.id);
    childrenById.set(pid, arr);
    links += 1;
  }

  // If no usable parent metadata, caller should use fallback layout.
  if (links < Math.max(2, Math.floor(nodes.length * 0.45))) return false;

  const roots = nodes
    .map(n => n.id)
    .filter(id => !parentById.has(id))
    .sort((a, b) => a.localeCompare(b));
  if (roots.length === 0) return false;

  const childOrderScore = (id: string): [number, number, string] => {
    const raw = dagNodes.find(n => n.id === id);
    const meta: any = raw?.metadata || {};
    const bucket = Number.isFinite(meta.rank_bucket) ? Number(meta.rank_bucket) : 0;
    const cluster = Number.isFinite(meta.cluster_id) ? Number(meta.cluster_id) : -1;
    return [bucket, cluster, id];
  };
  for (const [pid, arr] of childrenById.entries()) {
    arr.sort((a, b) => {
      const sa = childOrderScore(a);
      const sb = childOrderScore(b);
      if (sa[0] !== sb[0]) return sa[0] - sb[0];
      if (sa[1] !== sb[1]) return sa[1] - sb[1];
      return sa[2].localeCompare(sb[2]);
    });
    childrenById.set(pid, arr);
  }

  const leaves = new Map<string, number>();
  const visit = (id: string, seen: Set<string>): number => {
    if (seen.has(id)) return 1;
    seen.add(id);
    const children = childrenById.get(id) || [];
    if (children.length === 0) {
      leaves.set(id, 1);
      return 1;
    }
    let sum = 0;
    for (const c of children) sum += visit(c, seen);
    const val = Math.max(1, sum);
    leaves.set(id, val);
    return val;
  };
  for (const r of roots) visit(r, new Set());

  const xById = new Map<string, number>();
  let cursor = 0;
  const place = (id: string): void => {
    const children = childrenById.get(id) || [];
    if (children.length === 0) {
      xById.set(id, cursor);
      cursor += 1;
      return;
    }
    const start = cursor;
    for (const c of children) place(c);
    const end = cursor - 1;
    xById.set(id, (start + end) / 2);
  };
  for (const r of roots) place(r);

  const layerById = new Map<string, number>();
  for (const d of dagNodes) layerById.set(d.id, typeof d.layer === 'number' ? d.layer : 0);
  const maxLayer = Math.max(...Array.from(layerById.values()));
  const conf = Math.max(0, Math.min(1, Number(layoutBiasProfile?.confidence ?? 0)));
  const vBias = Number(layoutBiasProfile?.vertical_separation_bias ?? 0);
  const sBias = Number(layoutBiasProfile?.sibling_spacing_bias ?? 0);
  const cBias = Number(layoutBiasProfile?.branch_compactness_bias ?? 0);
  // Soft-prior only: explicit pins still override in DAGView.
  const xFactor = 1 + (Math.max(-1, Math.min(1, sBias)) * 0.22 * conf) - (Math.max(-1, Math.min(1, cBias)) * 0.14 * conf);
  const yFactor = 1 + (Math.max(-1, Math.min(1, vBias)) * 0.30 * conf);
  const xStep = (compact ? 95 : 115) * xFactor;
  const yStep = (compact ? 190 : 230) * yFactor;
  const centerX = 0;

  for (const n of nodes) {
    const xv = xById.get(n.id);
    const layer = layerById.get(n.id) ?? 0;
    if (typeof xv === 'number') {
      n.position.x = centerX + xv * xStep;
    }
    n.position.y = (maxLayer - layer) * yStep;
  }

  // Recenter around origin for fitView stability.
  const xs = nodes.map(n => n.position.x);
  const meanX = xs.reduce((s, v) => s + v, 0) / Math.max(1, xs.length);
  for (const n of nodes) n.position.x -= meanX;
  return true;
}

export function layoutSugiyamaBT(
  dagNodes: DAGNode[],
  dagEdges: DAGEdge[],
  options?: LayoutOptions
): { nodes: Node[]; edges: Edge[] } {
  // Create dagre graph
  const g = new dagre.graphlib.Graph();
  // MARKER_155A.G22.VERTICAL_PROFILE:
  // Do not auto-compact by node count; use explicit mode/profile from caller.
  const compact = options?.compact ?? false;
  const mode = options?.mode || 'workflow';
  const profile = (() => {
    if (mode === 'architecture') {
      return {
        ranksep: compact ? 90 : 180,   // more vertical separation
        nodesep: compact ? 24 : 40,    // tighter horizontal spread
        edgesep: compact ? 10 : 18,
        marginx: compact ? 10 : 20,
        marginy: compact ? 14 : 24,
      };
    }
    if (mode === 'tasks') {
      return {
        ranksep: compact ? 70 : 110,
        nodesep: compact ? 18 : 56,
        edgesep: compact ? 8 : 16,
        marginx: compact ? 10 : 24,
        marginy: compact ? 10 : 20,
      };
    }
    return {
      ranksep: compact ? 60 : 120,
      nodesep: compact ? 20 : 80,
      edgesep: compact ? 8 : 20,
      marginx: compact ? 10 : 30,
      marginy: compact ? 10 : 30,
    };
  })();
  g.setGraph({
    rankdir: 'BT',     // Bottom-to-Top: root at bottom (VETKA tree metaphor)
    ranksep: profile.ranksep,
    nodesep: profile.nodesep,
    edgesep: profile.edgesep,
    marginx: profile.marginx,
    marginy: profile.marginy,
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
        // MARKER_154.6A: Pass extra fields for RoadmapTaskNode rendering
        description: node.description,
        // MARKER_155.1A: Extra fields for tasks-level RoadmapTaskNode
        preset: node.preset,
        subtasksDone: node.subtasksDone,
        subtasksTotal: node.subtasksTotal,
      },
    };
  });

  // MARKER_155.INPUT_MATRIX.LAYOUT_VERTICAL_COMPACT.V1:
  // Architecture mode: prioritize vertical hierarchy readability and compress horizontal sprawl.
  const usedTreeLayout = mode === 'architecture' && nodes.length > 0
    ? applyArchitectureTreeLayout(nodes, dagNodes, compact, options?.layoutBiasProfile)
    : false;
  if (mode === 'architecture' && nodes.length > 0 && !usedTreeLayout) {
    const layerById = new Map<string, number>();
    const bucketById = new Map<string, number>();
    const bucketCountByLayer = new Map<number, number>();
    for (const n of dagNodes) {
      layerById.set(n.id, typeof n.layer === 'number' ? n.layer : 0);
      const meta = (n as any).metadata || {};
      const bucket = Number.isFinite(meta.rank_bucket) ? Number(meta.rank_bucket) : 0;
      const bucketCount = Number.isFinite(meta.bucket_count) ? Number(meta.bucket_count) : 1;
      bucketById.set(n.id, Math.max(0, bucket));
      const layer = typeof n.layer === 'number' ? n.layer : 0;
      bucketCountByLayer.set(layer, Math.max(bucketCountByLayer.get(layer) || 1, Math.max(1, bucketCount)));
    }
    const maxLayer = Math.max(...Array.from(layerById.values()));
    const byLayer = new Map<number, Node[]>();
    for (const n of nodes) {
      const layer = layerById.get(n.id) ?? 0;
      const arr = byLayer.get(layer) || [];
      arr.push(n);
      byLayer.set(layer, arr);
    }

    const conf = Math.max(0, Math.min(1, Number(options?.layoutBiasProfile?.confidence ?? 0)));
    const vBias = Math.max(-1, Math.min(1, Number(options?.layoutBiasProfile?.vertical_separation_bias ?? 0)));
    const sBias = Math.max(-1, Math.min(1, Number(options?.layoutBiasProfile?.sibling_spacing_bias ?? 0)));
    const cBias = Math.max(-1, Math.min(1, Number(options?.layoutBiasProfile?.branch_compactness_bias ?? 0)));
    const yStep = (compact ? 220 : 300) * (1 + vBias * 0.24 * conf);
    const rowStep = compact ? 82 : 96;
    const maxCols = compact ? 8 : 10;
    const xStep = (compact ? 92 : 106) * (1 + sBias * 0.18 * conf - cBias * 0.12 * conf);
    const globalCenterX = nodes.reduce((sum, n) => sum + n.position.x, 0) / Math.max(1, nodes.length);
    const initX = new Map<string, number>();
    for (const n of nodes) initX.set(n.id, n.position.x);
    const smoothX = laplacianSmoothX(nodes.map(n => n.id), dagEdges, initX, compact ? 28 : 40);

    for (const [layer, arr] of byLayer.entries()) {
      // Spectral ordering within layer using smoothed Laplacian objective.
      arr.sort((a, b) => (smoothX.get(a.id) ?? a.position.x) - (smoothX.get(b.id) ?? b.position.x));

      const bucketCount = Math.max(1, bucketCountByLayer.get(layer) || 1);
      const byBucket = new Map<number, Node[]>();
      for (const n of arr) {
        const b = Math.max(0, Math.min(bucketCount - 1, bucketById.get(n.id) ?? 0));
        const list = byBucket.get(b) || [];
        list.push(n);
        byBucket.set(b, list);
      }

      const orderedBuckets = Array.from(byBucket.keys()).sort((a, b) => a - b);
      const bucketSpread = xStep * (maxCols + 1);
      const bucketCenter = (orderedBuckets.length - 1) / 2;

      for (const bucket of orderedBuckets) {
        const bucketNodes = byBucket.get(bucket) || [];
        const rows = Math.max(1, Math.ceil(bucketNodes.length / maxCols));
        const bucketOffsetX = (bucket - bucketCenter) * bucketSpread;
        for (let i = 0; i < bucketNodes.length; i++) {
          const n = bucketNodes[i];
          const col = i % maxCols;
          const row = Math.floor(i / maxCols);
          const rowCenter = (maxCols - 1) / 2;
          const packedX = (col - rowCenter) * xStep;
          const smooth = smoothX.get(n.id) ?? n.position.x;
          n.position.x = globalCenterX + bucketOffsetX + packedX + (smooth - globalCenterX) * 0.18;

          const baseY = (maxLayer - layer) * yStep;
          const rowOffset = row * rowStep;
          const chess = ((col + layer + bucket) % 2 === 0) ? 0 : 10;
          n.position.y = baseY + rowOffset + chess - ((rows > 1) ? (rows - 1) * (rowStep / 2.6) : 0);
        }
      }
    }
  }

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
      case 'predicted': return '#6dc8ff';
      default: return NOLAN_PALETTE.edgeStructural;
    }
  };

  // Convert to xyflow edges
  const edges: Edge[] = dagEdges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: 'step',       // MARKER_151.2B: Orthogonal routing — clean right-angle connections (was smoothstep)
    animated: edge.type === 'temporal' || edge.type === 'feedback' || edge.animated,
    style: {
      stroke: getEdgeColor(edge.type),
      strokeWidth: 1 + edge.strength * 2,
      opacity: 0.6 + edge.strength * 0.4,
      strokeDasharray: edge.type === 'feedback' || edge.type === 'predicted' ? '6 4' : undefined,
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

    // Layer 1.5: Coder (executes subtasks)
    {
      id: `agent_${taskId}_coder`,
      type: 'agent',
      label: '@coder',
      status: 'running',
      layer: 1,
      parentId: `task_${taskId}`,
      taskId,
      role: 'coder',
      model: 'qwen3-coder',
      durationS: 12,
    },

    // Layer 2: Subtasks (children of coder)
    {
      id: `sub_${taskId}_0`,
      type: 'subtask',
      label: 'Create cache service',
      status: 'done',
      layer: 2,
      parentId: `agent_${taskId}_coder`,
      taskId,
      tokens: 1240,
    },
    {
      id: `sub_${taskId}_1`,
      type: 'subtask',
      label: 'Add Redis client',
      status: 'running',
      layer: 2,
      parentId: `agent_${taskId}_coder`,
      taskId,
      tokens: 890,
    },
    {
      id: `sub_${taskId}_2`,
      type: 'subtask',
      label: 'Update API endpoints',
      status: 'pending',
      layer: 2,
      parentId: `agent_${taskId}_coder`,
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
    { id: 'e3b', source: `task_${taskId}`, target: `agent_${taskId}_coder`, type: 'structural', strength: 0.9 },

    // Architect → Coder (plan → execute)
    { id: 'e3c', source: `agent_${taskId}_architect`, target: `agent_${taskId}_coder`, type: 'dataflow', strength: 0.9 },

    // Coder → Subtasks
    { id: 'e4', source: `agent_${taskId}_coder`, target: `sub_${taskId}_0`, type: 'dataflow', strength: 0.8 },
    { id: 'e5', source: `agent_${taskId}_coder`, target: `sub_${taskId}_1`, type: 'dataflow', strength: 0.8 },
    { id: 'e6', source: `agent_${taskId}_coder`, target: `sub_${taskId}_2`, type: 'dataflow', strength: 0.6 },

    // Subtask → Verifier
    { id: 'e7', source: `sub_${taskId}_0`, target: `agent_${taskId}_verifier`, type: 'temporal', strength: 0.7 },
    { id: 'e8', source: `sub_${taskId}_1`, target: `agent_${taskId}_verifier`, type: 'temporal', strength: 0.7 },
    { id: 'e9', source: `sub_${taskId}_2`, target: `agent_${taskId}_verifier`, type: 'temporal', strength: 0.5 },

    // Verifier → Proposal
    { id: 'e10', source: `agent_${taskId}_verifier`, target: `prop_${taskId}`, type: 'structural', strength: 0.9 },
  ];

  return { nodes, edges };
}
