import type { DAGEdge, DAGNode } from '../../types/dag';

export type CutSceneGraphViewNode = {
  node_id: string;
  node_type: string;
  visual_bucket: string;
  label: string;
  parent_id: string | null;
  rank_hint: number | null;
  selection_refs: {
    clip_ids: string[];
    scene_ids: string[];
    source_paths: string[];
  };
  render_hints: {
    display_mode: string;
    poster_url: string | null;
    modality: string | null;
    duration_sec: number | null;
    marker_count: number;
    sync_badge: string | null;
  };
  metadata: Record<string, unknown>;
};

export type CutSceneGraphViewInspectorNode = {
  node_id: string;
  node_type: string;
  label: string;
  summary: string;
  related_clip_ids: string[];
  related_source_paths: string[];
};

export type CutSceneGraphView = {
  schema_version?: string;
  graph_id: string;
  nodes: CutSceneGraphViewNode[];
  edges: Array<Record<string, unknown>>;
  focus: {
    selected_clip_ids: string[];
    selected_scene_ids: string[];
    focused_node_ids: string[];
    anchor_node_id: string | null;
  };
  layout_hints: {
    structural_edge_types: string[];
    intelligence_edge_types: string[];
    primary_rank_edge_types: string[];
  };
  crosslinks: {
    by_clip_id: Record<string, string[]>;
    by_scene_id: Record<string, string[]>;
    by_source_path: Record<string, string[]>;
  };
  structural_subgraph: {
    node_ids: string[];
    edge_ids: string[];
  };
  overlay_edges: Array<Record<string, unknown>>;
  dag_projection: {
    nodes: DAGNode[];
    edges: DAGEdge[];
    root_ids: string[];
  };
  inspector: {
    primary_node_id: string | null;
    focused_nodes: CutSceneGraphViewInspectorNode[];
  };
};

export type CutSceneGraphViewportCard = {
  nodeId: string;
  nodeType: string;
  label: string;
  visualBucket: string;
  isFocused: boolean;
  isPrimary: boolean;
  summary: string;
  displayMode: string;
  posterUrl: string | null;
  modality: string | null;
  durationSec: number | null;
  markerCount: number;
  syncBadge: string | null;
};

export type CutSceneGraphViewportModel = {
  graphId: string;
  dagNodes: DAGNode[];
  dagEdges: DAGEdge[];
  rootIds: string[];
  focusNodeIds: string[];
  primaryNodeId: string | null;
  structuralNodeIds: string[];
  structuralEdgeIds: string[];
  overlayEdgeCount: number;
  cards: CutSceneGraphViewportCard[];
  inspectorNodes: CutSceneGraphViewInspectorNode[];
  nodeByDagId: Record<string, CutSceneGraphViewNode>;
  cardByNodeId: Record<string, CutSceneGraphViewportCard>;
  dagIdsByClipId: Record<string, string[]>;
  dagIdsBySceneId: Record<string, string[]>;
  dagIdsBySourcePath: Record<string, string[]>;
};

function toDagId(nodeId: string): string {
  return `cut_graph:${nodeId}`;
}

function summarizeNode(
  node: CutSceneGraphViewNode,
  inspectorNode?: CutSceneGraphViewInspectorNode | null,
): string {
  if (inspectorNode?.summary) return inspectorNode.summary;
  const summary = String(node.metadata?.summary || '').trim();
  if (summary) return summary;
  const markerCount = Number(node.render_hints?.marker_count || 0);
  const durationSec = node.render_hints?.duration_sec;
  if (typeof durationSec === 'number') {
    return `${markerCount} markers · ${durationSec.toFixed(1)}s`;
  }
  return `${markerCount} markers`;
}

export function buildCutSceneGraphViewportModel(
  view: CutSceneGraphView | null | undefined,
): CutSceneGraphViewportModel | null {
  if (!view || !Array.isArray(view.nodes) || !view.dag_projection) return null;

  const inspectorById = new Map(
    (view.inspector?.focused_nodes || []).map((node) => [node.node_id, node] as const),
  );
  const focusNodeIds = view.focus?.focused_node_ids || [];
  const primaryNodeId = view.inspector?.primary_node_id || view.focus?.anchor_node_id || null;

  const cards = view.nodes.map((node) => {
    const inspectorNode = inspectorById.get(node.node_id) || null;
    return {
      nodeId: node.node_id,
      nodeType: node.node_type,
      label: node.label,
      visualBucket: node.visual_bucket,
      isFocused: focusNodeIds.includes(node.node_id),
      isPrimary: primaryNodeId === node.node_id,
      summary: summarizeNode(node, inspectorNode),
      displayMode: node.render_hints.display_mode,
      posterUrl: node.render_hints.poster_url,
      modality: node.render_hints.modality,
      durationSec: node.render_hints.duration_sec,
      markerCount: Number(node.render_hints.marker_count || 0),
      syncBadge: node.render_hints.sync_badge,
    };
  });

  const toDagIds = (values: Record<string, string[]> | undefined) =>
    Object.fromEntries(
      Object.entries(values || {}).map(([key, nodeIds]) => [key, nodeIds.map((nodeId) => toDagId(String(nodeId)))])
    );

  return {
    graphId: String(view.graph_id || 'main'),
    dagNodes: view.dag_projection.nodes || [],
    dagEdges: view.dag_projection.edges || [],
    rootIds: view.dag_projection.root_ids || [],
    focusNodeIds,
    primaryNodeId,
    structuralNodeIds: view.structural_subgraph?.node_ids || [],
    structuralEdgeIds: view.structural_subgraph?.edge_ids || [],
    overlayEdgeCount: Array.isArray(view.overlay_edges) ? view.overlay_edges.length : 0,
    cards,
    inspectorNodes: view.inspector?.focused_nodes || [],
    nodeByDagId: Object.fromEntries(view.nodes.map((node) => [toDagId(node.node_id), node])),
    cardByNodeId: Object.fromEntries(cards.map((card) => [card.nodeId, card])),
    dagIdsByClipId: toDagIds(view.crosslinks?.by_clip_id),
    dagIdsBySceneId: toDagIds(view.crosslinks?.by_scene_id),
    dagIdsBySourcePath: toDagIds(view.crosslinks?.by_source_path),
  };
}
