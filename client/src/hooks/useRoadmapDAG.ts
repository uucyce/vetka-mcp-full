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
import { API_BASE } from '../config/api.config';

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
  crossEdges: DAGEdge[];
  verifier: {
    decision: 'pass' | 'warn' | 'fail';
    acyclic?: boolean;
    monotonic_layers?: boolean;
    spectral?: {
      lambda2?: number;
      eigengap?: number;
      component_count?: number;
      status?: 'ok' | 'warn' | 'fail';
    };
  } | null;
  loading: boolean;
  error: string | null;
}

interface VetkaApiNodeLite {
  id: string;
  type: 'root' | 'branch' | 'leaf' | string;
  name?: string;
  parent_id?: string | null;
  metadata?: {
    path?: string;
    depth?: number;
  };
}

interface VetkaApiEdgeLite {
  from: string;
  to: string;
}

interface CondensedL2Node {
  id: string;
  kind?: string;
  label?: string;
  layer?: number;
  members?: string[];
  scc_size?: number;
  metadata?: {
    parent?: string;
    cluster_id?: number;
    rank_bucket?: number;
    bucket_count?: number;
    layer_index?: number;
    is_branch?: boolean;
    [key: string]: any;
  };
}

interface CondensedL2Edge {
  source: string;
  target: string;
  type?: string;
}

function withVirtualArchitectureRoot(
  nodes: CondensedL2Node[],
  edges: CondensedL2Edge[],
  scopePath?: string,
): { nodes: CondensedL2Node[]; edges: CondensedL2Edge[] } {
  if (nodes.length === 0) return { nodes, edges };

  const nodeIds = new Set(nodes.map(n => n.id));
  const indeg = new Map<string, number>();
  for (const id of nodeIds) indeg.set(id, 0);
  for (const e of edges) {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) continue;
    indeg.set(e.target, (indeg.get(e.target) || 0) + 1);
  }

  const roots = Array.from(nodeIds).filter(id => (indeg.get(id) || 0) === 0);
  if (roots.length <= 1) return { nodes, edges };

  const scopeLabel = (() => {
    const normalized = String(scopePath || '').replace(/\\/g, '/').replace(/\/+$/, '');
    const last = normalized.split('/').pop();
    return last || 'Architecture';
  })();

  const rootId = '__arch_root__';
  const outNodes: CondensedL2Node[] = [
    {
      id: rootId,
      kind: 'root',
      label: `${scopeLabel} (root)`,
      layer: -1,
      members: [],
      scc_size: 1,
      metadata: {},
    },
    ...nodes,
  ];

  const nodeById = new Map(nodes.map(n => [n.id, n] as const));
  const seen = new Set(edges.map(e => `${e.source}->${e.target}`));
  const extraEdges: CondensedL2Edge[] = [];

  const topBucket = (id: string): string => {
    const node = nodeById.get(id);
    const parent = String(node?.metadata?.parent || '').replace(/\\/g, '/').replace(/^\/+/, '');
    const first = parent.split('/').find(Boolean);
    return first || 'other';
  };

  // Avoid one giant star root -> many nodes by introducing intermediate hubs.
  const hubs = new Map<string, string>();
  const hubCountByBucket = new Map<string, number>();
  const MAX_BUCKETS = 8;
  const sortedRoots = [...roots].sort((a, b) => a.localeCompare(b));
  const bucketFreq = new Map<string, number>();
  for (const id of sortedRoots) {
    const bucket = topBucket(id);
    bucketFreq.set(bucket, (bucketFreq.get(bucket) || 0) + 1);
  }
  const topBuckets = [...bucketFreq.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, MAX_BUCKETS)
    .map(([name]) => name);
  const topBucketSet = new Set(topBuckets);

  for (const id of sortedRoots) {
    const rawBucket = topBucket(id);
    const bucket = topBucketSet.has(rawBucket) ? rawBucket : 'other';
    let hubId = hubs.get(bucket);
    if (!hubId) {
      hubId = `__arch_hub__${bucket}`;
      hubs.set(bucket, hubId);
      hubCountByBucket.set(bucket, 0);
      outNodes.push({
        id: hubId,
        kind: 'root',
        label: `${bucket}`,
        layer: 0,
        members: [],
        scc_size: 1,
        metadata: {},
      });
      const rootHubKey = `${rootId}->${hubId}`;
      if (!seen.has(rootHubKey)) {
        extraEdges.push({ source: rootId, target: hubId, type: 'structural' });
        seen.add(rootHubKey);
      }
    }

    // Spread huge buckets into micro-hubs every 10 roots.
    const count = hubCountByBucket.get(bucket) || 0;
    const subHubIndex = Math.floor(count / 10);
    let attachHub = hubId;
    if (subHubIndex > 0) {
      attachHub = `${hubId}__${subHubIndex}`;
      if (!nodeById.has(attachHub) && !outNodes.find(n => n.id === attachHub)) {
        outNodes.push({
          id: attachHub,
          kind: 'root',
          label: `${bucket}-${subHubIndex + 1}`,
          layer: 1,
          members: [],
          scc_size: 1,
          metadata: {},
        });
        const hKey = `${hubId}->${attachHub}`;
        if (!seen.has(hKey)) {
          extraEdges.push({ source: hubId, target: attachHub, type: 'structural' });
          seen.add(hKey);
        }
      }
    }

    const key = `${attachHub}->${id}`;
    if (!seen.has(key)) {
      extraEdges.push({ source: attachHub, target: id, type: 'structural' });
      seen.add(key);
    }
    hubCountByBucket.set(bucket, count + 1);
  }

  return { nodes: outNodes, edges: [...edges, ...extraEdges] };
}

function thinCondensedEdges(
  nodes: CondensedL2Node[],
  edges: CondensedL2Edge[],
): CondensedL2Edge[] {
  const layerById = new Map<string, number>();
  for (const n of nodes) {
    layerById.set(n.id, typeof n.layer === 'number' ? n.layer : 0);
  }

  // Prefer local progression edges and limit degree for readability,
  // but keep enough constraints so layout doesn't collapse into one horizontal rail.
  const sorted = [...edges].sort((a, b) => {
    const aDelta = Math.abs((layerById.get(a.target) || 0) - (layerById.get(a.source) || 0));
    const bDelta = Math.abs((layerById.get(b.target) || 0) - (layerById.get(b.source) || 0));
    return aDelta - bDelta;
  });

  const outCount = new Map<string, number>();
  const inCount = new Map<string, number>();
  const kept: CondensedL2Edge[] = [];
  const seen = new Set<string>();

  for (const e of sorted) {
    const key = `${e.source}->${e.target}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const src = e.source;
    const tgt = e.target;
    const srcLayer = layerById.get(src) ?? 0;
    const tgtLayer = layerById.get(tgt) ?? 0;
    const delta = Math.abs(tgtLayer - srcLayer);

    // Hard filter: skip very long jumps in architecture view.
    if (delta > 3) continue;

    const out = outCount.get(src) || 0;
    const inc = inCount.get(tgt) || 0;

    // Keep graph sparse and readable.
    if (out >= 3) continue;
    if (inc >= 4) continue;

    kept.push(e);
    outCount.set(src, out + 1);
    inCount.set(tgt, inc + 1);
  }

  // Connectivity repair: make sure most nodes have at least one incoming
  // edge (except true roots) to avoid rank-degenerate "single line" layouts.
  const keptSet = new Set(kept.map(e => `${e.source}->${e.target}`));
  const indeg = new Map<string, number>();
  const byTarget = new Map<string, CondensedL2Edge[]>();
  const nodeIds = new Set(nodes.map(n => n.id));

  for (const id of nodeIds) indeg.set(id, 0);
  for (const e of edges) {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) continue;
    const arr = byTarget.get(e.target) || [];
    arr.push(e);
    byTarget.set(e.target, arr);
  }
  for (const e of kept) indeg.set(e.target, (indeg.get(e.target) || 0) + 1);

  for (const id of nodeIds) {
    if ((indeg.get(id) || 0) > 0) continue;
    const candidates = (byTarget.get(id) || []).sort((a, b) => {
      const aDelta = Math.abs((layerById.get(a.target) || 0) - (layerById.get(a.source) || 0));
      const bDelta = Math.abs((layerById.get(b.target) || 0) - (layerById.get(b.source) || 0));
      return aDelta - bDelta;
    });
    const first = candidates.find(c => !keptSet.has(`${c.source}->${c.target}`));
    if (!first) continue;
    kept.push(first);
    keptSet.add(`${first.source}->${first.target}`);
  }

  // Final prune to avoid spaghetti: near-tree first, then small extra budget.
  const minLayer = Math.min(...nodes.map(n => (typeof n.layer === 'number' ? n.layer : 0)));
  const roots = new Set(nodes.filter(n => (typeof n.layer === 'number' ? n.layer : 0) === minLayer).map(n => n.id));

  const priority = (e: CondensedL2Edge): number => {
    const srcLayer = layerById.get(e.source) ?? 0;
    const tgtLayer = layerById.get(e.target) ?? 0;
    const delta = Math.abs(tgtLayer - srcLayer);
    // lower is better
    return delta * 10 + (roots.has(e.source) ? -1 : 0);
  };

  const sortedKept = [...kept].sort((a, b) => priority(a) - priority(b));
  const finalEdges: CondensedL2Edge[] = [];
  const finalIn = new Map<string, number>();
  const finalOut = new Map<string, number>();
  const edgeBudget = Math.min(220, Math.max(80, Math.floor(nodes.length * 1.2)));

  // Pass 1: one incoming per node (except roots) to preserve hierarchy.
  for (const e of sortedKept) {
    if (finalEdges.length >= edgeBudget) break;
    const srcLayer = layerById.get(e.source) ?? 0;
    const tgtLayer = layerById.get(e.target) ?? 0;
    const delta = Math.abs(tgtLayer - srcLayer);
    if (delta === 0) continue;
    if (!roots.has(e.target) && (finalIn.get(e.target) || 0) >= 1) continue;
    if ((finalOut.get(e.source) || 0) >= 2) continue;
    finalEdges.push(e);
    finalIn.set(e.target, (finalIn.get(e.target) || 0) + 1);
    finalOut.set(e.source, (finalOut.get(e.source) || 0) + 1);
  }

  // Pass 2: small extras for readability/context.
  for (const e of sortedKept) {
    if (finalEdges.length >= edgeBudget) break;
    const key = `${e.source}->${e.target}`;
    if (finalEdges.some(x => `${x.source}->${x.target}` === key)) continue;
    const srcLayer = layerById.get(e.source) ?? 0;
    const tgtLayer = layerById.get(e.target) ?? 0;
    const delta = Math.abs(tgtLayer - srcLayer);
    if (delta === 0 || delta > 2) continue;
    if ((finalIn.get(e.target) || 0) >= 2) continue;
    if ((finalOut.get(e.source) || 0) >= 3) continue;
    finalEdges.push(e);
    finalIn.set(e.target, (finalIn.get(e.target) || 0) + 1);
    finalOut.set(e.source, (finalOut.get(e.source) || 0) + 1);
  }

  return finalEdges;
}

function mapCondensedL2Node(node: CondensedL2Node): DAGNode {
  if (node.kind === 'root') {
    return {
      id: node.id,
      type: 'roadmap_task',
      label: node.label || 'Architecture Root',
      status: 'running' as any,
      layer: -1,
      taskId: node.id,
      description: '',
      graphKind: 'project_root' as any,
      projectNodeId: node.id,
      metadata: node.metadata || {},
    };
  }
  const status = node.scc_size && node.scc_size > 1 ? 'running' : 'pending';
  const kind = String(node.kind || '');
  const graphKind =
    kind === 'folder'
      ? 'project_dir'
      : (kind === 'scc' ? 'project_dir' : 'project_file');
  return {
    id: node.id,
    type: 'roadmap_task',
    label: node.label || node.id,
    status: status as any,
    layer: typeof node.layer === 'number' ? node.layer : 0,
    taskId: node.id,
    description: node.metadata?.parent || (node.members?.[0] || ''),
    graphKind: graphKind as any,
    projectNodeId: node.id,
    metadata: node.metadata || {},
  };
}

function mapCondensedL2Edge(edge: CondensedL2Edge, index: number): DAGEdge {
  const rawType = String(edge.type || '').toLowerCase();
  const mappedType: DAGEdge['type'] =
    rawType === 'structural'
      ? 'structural'
      : rawType === 'predicted'
      ? 'predicted'
      : 'dependency';
  return {
    id: `l2-${edge.source}-${edge.target}-${index}`,
    source: edge.source,
    target: edge.target,
    type: mappedType,
    strength: 0.85,
    relationKind: mappedType === 'structural' ? 'contains' : 'depends_on',
  };
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
    // MARKER_155A.P1.GRAPH_SCHEMA: Keep unified kind metadata for single-contract rendering.
    graphKind: node.data?.graph_kind || 'project_task',
    projectNodeId: node.data?.project_node_id || node.id,
  } as DAGNode;
}

function mapRoadmapEdge(edge: any): DAGEdge {
  return {
    id: edge.id || `e-${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    type: 'dependency',
    strength: 1.0,  // MARKER_154.6A: Roadmap dependency edges at full strength
    relationKind: edge.relation_kind || 'depends_on',
  };
}

function readableName(pathOrName: string): string {
  const normalized = String(pathOrName || '').replace(/\\/g, '/');
  const trimmed = normalized.endsWith('/') ? normalized.slice(0, -1) : normalized;
  const last = trimmed.split('/').pop() || trimmed;
  return last || 'node';
}

// MARKER_155A.G22.VETKA_TREE_ARCH:
// Build architecture DAG from /api/tree/data (fan-layout source), compacted into rooted branches.
function normalizePath(path: string | undefined): string {
  return String(path || '').replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase();
}

function mapTreeToArchitectureDAG(
  rawNodes: VetkaApiNodeLite[],
  rawEdges: VetkaApiEdgeLite[],
  scopePath?: string,
): {
  nodes: DAGNode[];
  edges: DAGEdge[];
} {
  const byId = new Map<string, VetkaApiNodeLite>();
  const children = new Map<string, string[]>();
  const parent = new Map<string, string>();

  for (const n of rawNodes) {
    byId.set(n.id, n);
    if (!children.has(n.id)) children.set(n.id, []);
  }
  for (const e of rawEdges) {
    if (!children.has(e.from)) children.set(e.from, []);
    children.get(e.from)!.push(e.to);
    parent.set(e.to, e.from);
  }
  for (const n of rawNodes) {
    if (n.parent_id && byId.has(n.parent_id)) {
      if (!children.has(n.parent_id)) children.set(n.parent_id, []);
      if (!children.get(n.parent_id)!.includes(n.id)) children.get(n.parent_id)!.push(n.id);
      if (!parent.has(n.id)) parent.set(n.id, n.parent_id);
    }
  }

  const roots = rawNodes.filter(n => n.type === 'root' || !parent.has(n.id));
  const normalizedScope = normalizePath(scopePath);
  const withPath = rawNodes.filter(n => Boolean(n.metadata?.path));

  let projectRoot: VetkaApiNodeLite | undefined;
  if (normalizedScope) {
    // 1) Exact path node.
    projectRoot = withPath.find(n => normalizePath(n.metadata?.path) === normalizedScope);
    // 2) Deepest ancestor node of scope.
    if (!projectRoot) {
      projectRoot = withPath
        .filter(n => {
          const p = normalizePath(n.metadata?.path);
          return normalizedScope.startsWith(`${p}/`) || normalizedScope === p;
        })
        .sort((a, b) => (b.metadata?.depth || 0) - (a.metadata?.depth || 0))[0];
    }
    // 3) First descendant under scope if ancestor not available.
    if (!projectRoot) {
      projectRoot = withPath
        .filter(n => normalizePath(n.metadata?.path).startsWith(`${normalizedScope}/`))
        .sort((a, b) => (a.metadata?.depth || 0) - (b.metadata?.depth || 0))[0];
    }
  }
  if (!projectRoot) projectRoot = roots[0];
  if (!projectRoot) return { nodes: [], edges: [] };

  const countLeaves = (nodeId: string): number => {
    const kids = children.get(nodeId) || [];
    if (kids.length === 0) return 1;
    let total = 0;
    for (const k of kids) total += countLeaves(k);
    return total;
  };

  const directChildren = children.get(projectRoot.id) || [];
  const branchRoots = directChildren.filter(id => {
    const n = byId.get(id);
    return n && n.type !== 'leaf';
  });
  const leafChildren = directChildren.filter(id => {
    const n = byId.get(id);
    return n && n.type === 'leaf';
  });

  const nodes: DAGNode[] = [];
  const edges: DAGEdge[] = [];
  const createdNodeIds = new Set<string>();

  const mkNode = (id: string, layer: number, fallbackLabel: string): DAGNode => {
    const n = byId.get(id);
    const nodeName = n?.name || readableName(n?.metadata?.path || fallbackLabel);
    const leafCount = countLeaves(id);
    const graphKind = n?.type === 'leaf' ? 'project_file' : 'project_dir';
    return {
      id,
      type: 'roadmap_task',
      label: `${nodeName} (${leafCount})`,
      status: 'pending',
      layer,
      taskId: id,
      description: n?.metadata?.path || nodeName,
      graphKind,
      projectNodeId: id,
    };
  };

  // Layer 0: major branches under project root (src/output/etc)
  for (const branchId of branchRoots) {
    const node = mkNode(branchId, 0, branchId);
    nodes.push(node);
    createdNodeIds.add(node.id);
  }
  // If branch count is low, include some direct files to avoid oversimplified 3-node view.
  if (branchRoots.length < 3 && leafChildren.length <= 10) {
    for (const leafId of leafChildren.slice(0, 12)) {
      const node = mkNode(leafId, 0, leafId);
      if (!createdNodeIds.has(node.id)) {
        nodes.push(node);
        createdNodeIds.add(node.id);
      }
      edges.push({
        id: `tree-${projectRoot.id}-${leafId}`,
        source: projectRoot.id,
        target: leafId,
        type: 'structural',
        strength: 0.6,
        relationKind: 'contains',
      });
    }
  }

  // Layer 1-2: sub-branches, limited for readability.
  for (const branchId of branchRoots) {
    const level1 = (children.get(branchId) || [])
      .map(id => byId.get(id))
      .filter((n): n is VetkaApiNodeLite => Boolean(n))
      .filter(n => n.type !== 'leaf')
      .sort((a, b) => countLeaves(b.id) - countLeaves(a.id))
      .slice(0, 18);

    // MARKER_155A.G22.KNOWLEDGE_TIER_HIERARCHY:
    // For wide branches, insert semantic tier hubs to increase vertical structure.
    const useTierHubs = level1.length > 8;
    const tierLabel = (leafCount: number) => {
      if (leafCount >= 200) return 'Core';
      if (leafCount >= 80) return 'Active';
      if (leafCount >= 20) return 'Context';
      return 'Leaf';
    };
    const tierNodeId = (branch: string, tier: string) => `tier_${branch}_${tier.toLowerCase()}`;
    const tierCounts = new Map<string, number>();
    for (const child of level1) {
      const tier = tierLabel(countLeaves(child.id));
      tierCounts.set(tier, (tierCounts.get(tier) || 0) + 1);
    }

    if (useTierHubs) {
      for (const [tier, count] of tierCounts.entries()) {
        const id = tierNodeId(branchId, tier);
        if (createdNodeIds.has(id)) continue;
        nodes.push({
          id,
          type: 'roadmap_task',
          label: `${tier} (${count})`,
          status: 'pending',
          layer: 1,
          taskId: id,
          description: `Knowledge tier ${tier} for ${readableName(branchId)}`,
          graphKind: 'project_dir',
          projectNodeId: id,
        });
        createdNodeIds.add(id);
        edges.push({
          id: `tier-${branchId}-${id}`,
          source: branchId,
          target: id,
          type: 'structural',
          strength: 0.95,
          relationKind: 'contains',
        });
      }
    }

    for (const child of level1) {
      const childNode = mkNode(child.id, useTierHubs ? 2 : 1, child.id);
      if (!createdNodeIds.has(childNode.id)) {
        nodes.push(childNode);
        createdNodeIds.add(childNode.id);
      }

      const parentForChild = useTierHubs
        ? tierNodeId(branchId, tierLabel(countLeaves(child.id)))
        : branchId;

      edges.push({
        id: `tree-${parentForChild}-${child.id}`,
        source: parentForChild,
        target: child.id,
        type: 'structural',
        strength: 0.9,
        relationKind: 'contains',
      });

      const level2 = (children.get(child.id) || [])
        .map(id => byId.get(id))
        .filter((n): n is VetkaApiNodeLite => Boolean(n))
        .filter(n => n.type !== 'leaf')
        .sort((a, b) => countLeaves(b.id) - countLeaves(a.id))
        .slice(0, 12);

      for (const grand of level2) {
        const grandNode = mkNode(grand.id, useTierHubs ? 3 : 2, grand.id);
        if (!createdNodeIds.has(grandNode.id)) {
          nodes.push(grandNode);
          createdNodeIds.add(grandNode.id);
        }
        edges.push({
          id: `tree-${child.id}-${grand.id}`,
          source: child.id,
          target: grand.id,
          type: 'structural',
          strength: 0.8,
          relationKind: 'contains',
        });
      }
    }
  }

  // If branches are disconnected after filtering, connect them through virtual project root.
  const hasAnyEdge = edges.length > 0;
  if (!hasAnyEdge && branchRoots.length > 1) {
    const rootId = `virt_root_${projectRoot.id}`;
    nodes.push({
      id: rootId,
      type: 'roadmap_task',
      label: readableName(projectRoot.name || projectRoot.metadata?.path || 'project'),
      status: 'pending',
      layer: -1,
      taskId: rootId,
      graphKind: 'project_root',
      projectNodeId: projectRoot.id,
    });
    for (const branchId of branchRoots) {
      edges.push({
        id: `virt-${rootId}-${branchId}`,
        source: rootId,
        target: branchId,
        type: 'structural',
        strength: 1,
        relationKind: 'contains',
      });
    }
  }

  return { nodes, edges };
}

export function useRoadmapDAG(scopePath?: string): RoadmapData & {
  fetchRoadmap: () => Promise<void>;
  regenerateRoadmap: () => Promise<void>;
} {
  const [nodes, setNodes] = useState<DAGNode[]>([]);
  const [edges, setEdges] = useState<DAGEdge[]>([]);
  const [crossEdges, setCrossEdges] = useState<DAGEdge[]>([]);
  const [verifier, setVerifier] = useState<RoadmapData['verifier']>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRoadmap = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // MARKER_155.ARCHITECT_BUILD.UI_BIND.V1:
      // Preferred source: architect build endpoint returns design_graph + verifier contract.
      const buildRes = await fetch(`${API_BASE}/mcc/graph/build-design`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scope_path: scopePath || '',
          max_nodes: 220,
          include_artifacts: false,
          use_predictive_overlay: false,
          problem_statement: 'Build readable architecture DAG for collaborative agent context.',
          target_outcome: 'Single-canvas acyclic project DAG for task placement and drill.',
        }),
      });
      if (buildRes.ok) {
        const buildData = await buildRes.json();
        const designNodes: CondensedL2Node[] = buildData?.design_graph?.nodes || [];
        const designEdgesRaw: CondensedL2Edge[] = buildData?.design_graph?.edges || [];
        const crossEdgesRaw: CondensedL2Edge[] =
          buildData?.design_graph?.cross_edges ||
          buildData?.runtime_graph?.l1?.cross_edges ||
          [];
        if (designNodes.length > 0) {
          setNodes(designNodes.map(mapCondensedL2Node));
          setEdges(designEdgesRaw.map(mapCondensedL2Edge));
          setCrossEdges(crossEdgesRaw.map((e, i) => ({
            ...mapCondensedL2Edge(e, i),
            id: `build-cross-${e.source}-${e.target}-${i}`,
            strength: Math.max(0.35, Math.min(0.95, Number((e as any).score ?? (e as any).confidence ?? 0.55))),
            type: 'temporal',
          })));
          setVerifier(buildData?.verifier || null);
          return;
        }
      }

      // MARKER_155.P15.UI_BIND:
      // Prefer SCC-condensed L2 architecture graph for MCC roadmap canvas.
      const qs = new URLSearchParams();
      if (scopePath) qs.set('scope_path', scopePath);
      qs.set('max_nodes', '220');
      qs.set('refresh', '1');
      const condensedRes = await fetch(`${API_BASE}/mcc/graph/condensed?${qs.toString()}`);
      if (condensedRes.ok) {
        const condensed = await condensedRes.json();
        const l2OverviewNodes: CondensedL2Node[] = condensed?.l2_overview?.nodes || [];
        const l2OverviewEdgesRaw: CondensedL2Edge[] = condensed?.l2_overview?.edges || [];
        const l2Nodes: CondensedL2Node[] = condensed?.l2?.nodes || [];
        const l2EdgesRaw: CondensedL2Edge[] = condensed?.l2?.edges || [];
        const crossEdgesRaw: CondensedL2Edge[] = condensed?.l1?.cross_edges || [];
        if (l2OverviewNodes.length > 0 || l2Nodes.length > 0) {
          const sourceNodes = l2OverviewNodes.length > 0 ? l2OverviewNodes : l2Nodes;
          const sourceEdges = l2OverviewEdgesRaw.length > 0 ? l2OverviewEdgesRaw : l2EdgesRaw;
          // MARKER_155.INPUT_MATRIX.BACKBONE_DAG.V1:
          // Backend now returns algorithmic backbone L2; avoid client-side re-wiring
          // that can reintroduce horizontal rails/spaghetti.
          const useRawL2 = true;
          if (useRawL2) {
            setNodes(sourceNodes.map(mapCondensedL2Node));
            setEdges(sourceEdges.map(mapCondensedL2Edge));
            setCrossEdges(crossEdgesRaw.map((e, i) => ({
              ...mapCondensedL2Edge(e, i),
              id: `l1-cross-${e.source}-${e.target}-${i}`,
              strength: Math.max(0.35, Math.min(0.95, Number((e as any).score ?? (e as any).confidence ?? 0.55))),
              type: 'temporal',
            })));
            setVerifier(null);
          } else {
            // Legacy fallback path.
            const l2Edges = thinCondensedEdges(l2Nodes, l2EdgesRaw);
            const rooted = withVirtualArchitectureRoot(l2Nodes, l2Edges, scopePath);
            setNodes(rooted.nodes.map(mapCondensedL2Node));
            setEdges(rooted.edges.map(mapCondensedL2Edge));
            setCrossEdges(crossEdgesRaw.map((e, i) => ({
              ...mapCondensedL2Edge(e, i),
              id: `l1-cross-${e.source}-${e.target}-${i}`,
              strength: Math.max(0.35, Math.min(0.95, Number((e as any).score ?? (e as any).confidence ?? 0.55))),
              type: 'temporal',
            })));
            setVerifier(null);
          }
          return;
        }
      }

      // MARKER_155A.G22.VETKA_TREE_ARCH: Prefer canonical VETKA tree/fan source for architecture LOD.
      const treeRes = await fetch(`${API_BASE}/tree/data`);
      if (treeRes.ok) {
        const treeData = await treeRes.json();
        const treeNodes: VetkaApiNodeLite[] = treeData?.tree?.nodes || [];
        const treeEdges: VetkaApiEdgeLite[] = treeData?.tree?.edges || [];
        if (treeNodes.length > 0) {
          const mapped = mapTreeToArchitectureDAG(treeNodes, treeEdges, scopePath);
          if (mapped.nodes.length > 0) {
            setNodes(mapped.nodes);
            setEdges(mapped.edges);
            setCrossEdges([]);
            setVerifier(null);
            return;
          }
        }
      }

      // Fallback to older MCC roadmap endpoint.
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
      setCrossEdges([]);
      setVerifier(null);
    } catch (err) {
      console.warn('[Roadmap] Fetch failed:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setNodes([]);
      setEdges([]);
      setCrossEdges([]);
      setVerifier(null);
    } finally {
      setLoading(false);
    }
  }, [scopePath]);

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

  return { nodes, edges, crossEdges, verifier, loading, error, fetchRoadmap, regenerateRoadmap };
}
