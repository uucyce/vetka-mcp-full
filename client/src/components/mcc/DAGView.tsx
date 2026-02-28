/**
 * MARKER_135.1A: DAG View — main visualization component.
 * MARKER_137.2A: Edge highlighting on node select (VETKA-style).
 * Uses xyflow for interactive graph with Sugiyama BT layout.
 * Root at bottom, proposals at top — VETKA spatial metaphor.
 *
 * @phase 137
 * @status active
 */

import { useCallback, useEffect, useMemo, useRef, useImperativeHandle, forwardRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ConnectionLineType,
  MarkerType,
  type Node,
  type Edge,
  type Connection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { TaskNode } from './nodes/TaskNode';
import { AgentNode } from './nodes/AgentNode';
import { SubtaskNode } from './nodes/SubtaskNode';
import { ProposalNode } from './nodes/ProposalNode';
// MARKER_144.4: Phase 144 workflow editor node types
import { ConditionNode } from './nodes/ConditionNode';
import { ParallelNode } from './nodes/ParallelNode';
import { LoopNode } from './nodes/LoopNode';
import { TransformNode } from './nodes/TransformNode';
import { GroupNode } from './nodes/GroupNode';
// MARKER_154.6A: Roadmap-specific node type
import { RoadmapTaskNode } from './nodes/RoadmapTaskNode';
import { layoutSugiyamaBT, createTestDAGData, NOLAN_PALETTE } from '../../utils/dagLayout';
import type { DAGNode, DAGEdge, NodeStatus } from '../../types/dag';

// MARKER_135.4F: Track node positions for incremental layout
type PositionMap = Record<string, { x: number; y: number }>;

// MARKER_155.1: Zoom levels for Matryoshka drill-down
export const ZOOM_LEVELS = {
  0: { min: 0.5, max: 1.0, label: 'Architecture' },
  1: { min: 1.0, max: 2.0, label: 'Tasks' },
  2: { min: 2.0, max: 3.0, label: 'Workflow' },
} as const;

// MARKER_155A.P2.LOD_THRESHOLDS: Canonical zoom->LOD mapping for unified single-canvas behavior.
export type LODLevel = 'architecture' | 'tasks' | 'workflow';
const LOD_THRESHOLDS = {
  architectureMax: 0.95,
  tasksMax: 1.8,
} as const;

// MARKER_155A.G26.WF_CANONICAL_LAYOUT:
// Deterministic inline workflow layout used in roadmap drill context.
// Goal: stable matryoshka shape (no random "clump") across repeated expands.
function layoutInlineWorkflowCanonical(
  nodes: DAGNode[],
  edges: DAGEdge[],
): { nodes: DAGNode[]; edges: DAGEdge[] } {
  if (nodes.length === 0) return { nodes, edges };
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const indegree = new Map<string, number>();
  const depth = new Map<string, number>();
  nodes.forEach((n) => {
    indegree.set(n.id, 0);
    depth.set(n.id, 0);
  });
  for (const e of edges) {
    if (!byId.has(e.source) || !byId.has(e.target) || e.source === e.target) continue;
    indegree.set(e.target, (indegree.get(e.target) || 0) + 1);
  }

  const roleDepth = (n: DAGNode): number => {
    const role = String((n as any)?.role || '').toLowerCase();
    if (role === 'architect') return 0;
    if (role === 'coder') return 1;
    if (role === 'verifier') return 2;
    if (role === 'scout' || role === 'researcher') return 1;
    if (n.type === 'proposal') return 3;
    if (n.type === 'subtask') return 2;
    return 1;
  };
  const roleOrder = (n: DAGNode): number => {
    const role = String((n as any)?.role || '').toLowerCase();
    if (role === 'architect') return 0;
    if (role === 'scout') return 1;
    if (role === 'researcher') return 2;
    if (role === 'coder') return 3;
    if (role === 'verifier') return 4;
    if (n.type === 'condition') return 5;
    if (n.type === 'parallel') return 6;
    if (n.type === 'loop') return 7;
    if (n.type === 'transform') return 8;
    if (n.type === 'group') return 9;
    if (n.type === 'subtask') return 10;
    if (n.type === 'proposal') return 11;
    return 20;
  };

  // Kahn traversal for acyclic core, then semantic fallback for cyclic leftovers.
  const q: string[] = nodes
    .filter((n) => (indegree.get(n.id) || 0) === 0)
    .map((n) => n.id)
    .sort((a, b) => a.localeCompare(b));
  while (q.length > 0) {
    const id = q.shift()!;
    const d = depth.get(id) || 0;
    for (const e of edges) {
      if (e.source !== id || !byId.has(e.target)) continue;
      depth.set(e.target, Math.max(depth.get(e.target) || 0, d + 1));
      indegree.set(e.target, (indegree.get(e.target) || 0) - 1);
      if ((indegree.get(e.target) || 0) === 0) q.push(e.target);
    }
    q.sort((a, b) => a.localeCompare(b));
  }

  for (const n of nodes) {
    if ((indegree.get(n.id) || 0) > 0) {
      depth.set(n.id, Math.max(depth.get(n.id) || 0, roleDepth(n)));
    } else {
      depth.set(n.id, Math.max(depth.get(n.id) || 0, roleDepth(n)));
    }
  }

  const byDepth = new Map<number, DAGNode[]>();
  for (const n of nodes) {
    const d = Math.max(0, depth.get(n.id) || 0);
    const arr = byDepth.get(d) || [];
    arr.push(n);
    byDepth.set(d, arr);
  }
  const levels = Array.from(byDepth.keys()).sort((a, b) => a - b);
  // MARKER_155A.G26.WF_CANONICAL_PACKING:
  // Split overcrowded rows into deterministic micro-levels to avoid horizontal-strip collapse.
  const packedRows: DAGNode[][] = [];
  const maxPerRow = 3;
  for (const lvl of levels) {
    const row = (byDepth.get(lvl) || []).sort((a, b) => {
      const ra = roleOrder(a);
      const rb = roleOrder(b);
      if (ra !== rb) return ra - rb;
      return String(a.label || a.id).localeCompare(String(b.label || b.id));
    });
    for (let i = 0; i < row.length; i += maxPerRow) {
      packedRows.push(row.slice(i, i + maxPerRow));
    }
  }
  const xGap = 102;
  const yGap = 86;
  const outNodes: DAGNode[] = [];
  const totalRows = packedRows.length;
  for (let lvl = 0; lvl < packedRows.length; lvl += 1) {
    const row = packedRows[lvl] || [];
    const rowW = Math.max(0, row.length - 1) * xGap;
    const startX = -rowW / 2;
    row.forEach((n, idx) => {
      outNodes.push({
        ...n,
        metadata: {
          ...(n.metadata || {}),
          wf_stage: lvl,
        },
        // local canonical coords (later embedded as micro layer around anchor)
        position: {
          x: startX + idx * xGap,
          // MARKER_155A.G27.WF_BOTTOM_UP_ORIENTATION:
          // Workflow in roadmap unfolds bottom-up: start near task (bottom), results above.
          y: (totalRows - 1 - lvl) * yGap,
        } as any,
      } as any);
    });
  }
  return { nodes: outNodes, edges };
}

function getLODLevel(zoom: number): LODLevel {
  if (zoom <= LOD_THRESHOLDS.architectureMax) return 'architecture';
  if (zoom <= LOD_THRESHOLDS.tasksMax) return 'tasks';
  return 'workflow';
}

export interface CameraPosition {
  x: number;
  y: number;
  zoom: number;
}

export interface DAGViewRef {
  zoomToNode: (nodeId: string, level: number) => void;
  zoomOut: () => void;
  getCameraPosition: () => CameraPosition | null;
  fitView: () => void;
}

// MARKER_144.4: Extended with Phase 144 workflow editor node types
const nodeTypes = {
  task: TaskNode,
  agent: AgentNode,
  subtask: SubtaskNode,
  proposal: ProposalNode,
  condition: ConditionNode,
  parallel: ParallelNode,
  loop: LoopNode,
  transform: TransformNode,
  group: GroupNode,
  // MARKER_154.6A: Roadmap-level enhanced task node
  roadmap_task: RoadmapTaskNode,
} as const;

interface DAGViewProps {
  dagNodes?: DAGNode[];
  dagEdges?: DAGEdge[];
  selectedNode?: string | null;
  selectedNodeIds?: string[];
  onNodeSelect?: (nodeId: string | null) => void;
  onNodeSelectWithMode?: (nodeId: string | null, options: { additive: boolean }) => void;
  onEdgeSelect?: (edgeId: string | null) => void;
  width?: number | string;
  height?: number | string;
  // MARKER_144.2: Edit mode props (additive — all optional)
  editMode?: boolean;
  onConnect?: (connection: Connection) => void;
  onNodesDelete?: (nodes: Node[]) => void;
  onEdgesDelete?: (edges: Edge[]) => void;
  // MARKER_144.3: Context menu callback
  onContextMenu?: (event: React.MouseEvent, target: { kind: 'canvas' | 'node' | 'edge'; id?: string; position: { x: number; y: number } }) => void;
  contextMenuEnabled?: boolean;
  // MARKER_151.3B: ComfyUI-style node picker trigger
  onPaneDoubleClick?: (position: { x: number; y: number }) => void;
  // MARKER_153.5D: Node double-click for Matryoshka drill-down
  onNodeDoubleClick?: (nodeId: string) => void;
  // MARKER_155.2B: Compact layout for large task trees
  compact?: boolean;
  // MARKER_155A.P2.CAMERA_STATE: Persist camera for smooth back navigation.
  initialCamera?: CameraPosition | null;
  onCameraChange?: (camera: CameraPosition, lod: LODLevel) => void;
  onLODChange?: (lod: LODLevel) => void;
  // MARKER_155A.G21.LAYOUT_RESET_POLICY: Unique identity for layout cache reset.
  graphIdentity?: string;
  // MARKER_155A.G22.VERTICAL_PROFILE: Layout profile per navigation context.
  layoutMode?: 'architecture' | 'tasks' | 'workflow';
  layoutBiasProfile?: {
    vertical_separation_bias?: number;
    sibling_spacing_bias?: number;
    branch_compactness_bias?: number;
    confidence?: number;
  } | null;
  // MARKER_155A.P2.PIN_LAYOUT: Persisted manual positions keyed by graph context.
  pinnedPositions?: PositionMap;
  onPinnedPositionsChange?: (positions: PositionMap) => void;
}

export const DAGView = forwardRef<DAGViewRef, DAGViewProps>(function DAGView({
  dagNodes,
  dagEdges,
  selectedNode,
  selectedNodeIds = [],
  onNodeSelect,
  onNodeSelectWithMode,
  onEdgeSelect,
  width = '100%',
  height = '100%',
  // MARKER_144.2: Edit mode props (default: read-only, no regression)
  editMode = false,
  onConnect,
  onNodesDelete,
  onEdgesDelete,
  // MARKER_144.3: Context menu
  onContextMenu,
  contextMenuEnabled,
  onPaneDoubleClick,
  // MARKER_153.5D: Node double-click drill-down
  onNodeDoubleClick,
  // MARKER_155.2B: Compact layout for large task trees
  compact,
  initialCamera,
  onCameraChange,
  onLODChange,
  graphIdentity,
  layoutMode = 'workflow',
  layoutBiasProfile = null,
  pinnedPositions,
  onPinnedPositionsChange,
}, ref) {
  // If no data provided, use test data
  const { nodes: inputNodes, edges: inputEdges } = useMemo(() => {
    if (dagNodes && dagEdges) {
      return { nodes: dagNodes, edges: dagEdges };
    }
    // Use hardcoded test data for development
    return createTestDAGData();
  }, [dagNodes, dagEdges]);

  // MARKER_135.4F: Track previous positions for incremental layout
  const prevPositionsRef = useRef<PositionMap>({});
  const pinnedPositionsRef = useRef<PositionMap>(pinnedPositions || {});
  const persistPinsTimerRef = useRef<number | null>(null);
  const graphIdentityRef = useRef<string | undefined>(graphIdentity);
  const isInlineOverlayNodeId = useCallback(
    (id: string): boolean => id.startsWith('wf_') || id.startsWith('rd_'),
    [],
  );

  useEffect(() => {
    // MARKER_155A.G27.PIN_SANITIZE_INLINE:
    // Never restore persisted pins for temporary inline overlays (wf_/rd_).
    const incoming = pinnedPositions || {};
    const sanitized: PositionMap = {};
    for (const [id, pos] of Object.entries(incoming)) {
      if (isInlineOverlayNodeId(id)) continue;
      sanitized[id] = pos;
    }
    pinnedPositionsRef.current = sanitized;
  }, [pinnedPositions, isInlineOverlayNodeId]);

  // MARKER_155A.P2.FRACTAL_RENDER: LOD-aware visual density tuning in one canvas.
  const [cameraLOD, setCameraLOD] = useState<LODLevel>('tasks');

  // Apply Sugiyama BT layout with incremental position preservation
  const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(() => {
    // MARKER_155A.G21.LAYOUT_RESET_POLICY:
    // Drop stale cached coordinates when graph domain changes (architecture/tasks/workflow).
    if (graphIdentityRef.current !== graphIdentity) {
      prevPositionsRef.current = {};
      graphIdentityRef.current = graphIdentity;
    }
    const result = layoutSugiyamaBT(inputNodes, inputEdges, {
      compact,
      mode: layoutMode,
      layoutBiasProfile,
    });

    // Preserve positions of existing nodes (incremental layout) for non-architecture modes.
    const prevPositions = prevPositionsRef.current;
    const hasWorkflowInline = inputNodes.some((n) => n.id.startsWith('wf_'));
    const hasRoadmapDrillInline = inputNodes.some((n) => n.id.startsWith('rd_'));
    // MARKER_155A.G23.NO_SINK_ACCUMULATION:
    // In architecture mode, avoid incremental reuse when inline overlays are active.
    // Otherwise local push offsets accumulate and drag anchor branches "underground".
    // MARKER_155A.G24.INCREMENTAL_LAYOUT_ARBITRATION:
    // Keep architecture stable when no inline overlays are active.
    // Disable full incremental reuse while inline layers are present to avoid sink drift.
    const keepIncremental =
      layoutMode !== 'architecture' || (!hasWorkflowInline && !hasRoadmapDrillInline);
    // MARKER_155A.G25.INCREMENTAL_STRESS_TUNE:
    // Under inline drill, keep non-inline architecture nodes pinned to previous positions.
    // This reduces jump/flicker during rapid toggle stress while letting inline nodes re-layout.
    const reuseArchitectureBaseWhileInline =
      layoutMode === 'architecture' && (hasWorkflowInline || hasRoadmapDrillInline);
    let updatedNodes = result.nodes.map(node => {
      const prevPos = prevPositions[node.id];
      if (!prevPos) return node;
      if (keepIncremental) {
        // Keep existing position for smooth updates
        return { ...node, position: prevPos };
      }
      if (reuseArchitectureBaseWhileInline && !isInlineOverlayNodeId(node.id)) {
        return { ...node, position: prevPos };
      }
      return node;
    });

    // MARKER_155A.P2.PIN_LAYOUT:
    // Persisted user drag positions have highest priority over auto layout.
    const pinMap = pinnedPositionsRef.current || {};
      if (Object.keys(pinMap).length > 0) {
        updatedNodes = updatedNodes.map(node => {
          if (isInlineOverlayNodeId(node.id)) return node;
          const pinned = pinMap[node.id];
          if (!pinned) return node;
        return {
          ...node,
          position: pinned,
        };
      });
    }

    // MARKER_155.G1.TASK_ANCHORING_CONTRACT_V1:
    // Deterministic post-layout placement for roadmap task overlays:
    // anchored tasks near code anchors, unplaced tasks in right rail.
    if (layoutMode === 'architecture') {
      const taskOverlayNodes = updatedNodes.filter(
        (n) => n.type === 'roadmap_task' && n.id.startsWith('task_overlay_')
      );
      if (taskOverlayNodes.length > 0) {
        const nodeById = new Map(updatedNodes.map((n) => [n.id, n]));
        const baseNodes = updatedNodes.filter((n) => !(n.type === 'roadmap_task' && n.id.startsWith('task_overlay_')));
        const bounds = baseNodes.reduce(
          (acc, n) => {
            const w = Number(n.width || 140);
            acc.maxX = Math.max(acc.maxX, n.position.x + w);
            acc.minY = Math.min(acc.minY, n.position.y);
            return acc;
          },
          { maxX: Number.NEGATIVE_INFINITY, minY: Number.POSITIVE_INFINITY }
        );

        const getCenter = (n: Node): { x: number; y: number } => ({
          x: n.position.x + Number(n.width || 140) / 2,
          y: n.position.y + Number(n.height || 48) / 2,
        });

        const anchoredGroups = new Map<string, Node[]>();
        const unplacedNodes: Node[] = [];

        for (const taskNode of taskOverlayNodes) {
          if (pinMap[taskNode.id]) continue;
          const data: any = taskNode.data || {};
          const anchorIds: string[] = Array.isArray(data.anchorNodeIds)
            ? (data.anchorNodeIds as unknown[]).filter((id): id is string => typeof id === 'string' && !!nodeById.get(id))
            : [];
          const anchors = anchorIds
            .map((id: string) => nodeById.get(id))
            .filter((n): n is Node => !!n && !(n.type === 'roadmap_task' && n.id.startsWith('task_overlay_')));
          if (anchors.length === 0) {
            unplacedNodes.push(taskNode);
            continue;
          }
          const key = anchorIds.slice().sort().join('|');
          const list = anchoredGroups.get(key) || [];
          list.push(taskNode);
          anchoredGroups.set(key, list);
        }

        for (const [key, group] of anchoredGroups.entries()) {
          const anchorIds = key.split('|').filter(Boolean);
          const anchors = anchorIds
            .map((id) => nodeById.get(id))
            .filter((n): n is Node => !!n);
          if (anchors.length === 0) continue;
          const centers = anchors.map(getCenter);
          const centerX = centers.reduce((s, c) => s + c.x, 0) / centers.length;
          const centerY = centers.reduce((s, c) => s + c.y, 0) / centers.length;
          const sorted = [...group].sort((a, b) => a.id.localeCompare(b.id));
          sorted.forEach((taskNode, idx) => {
            const offset = (idx - (sorted.length - 1) / 2) * 84;
            taskNode.position = {
              x: centerX + 120,
              y: centerY + offset,
            };
          });
        }

        const railX = Number.isFinite(bounds.maxX) ? bounds.maxX + 180 : 980;
        const railStartY = Number.isFinite(bounds.minY) ? Math.max(120, bounds.minY + 140) : 140;
        unplacedNodes
          .sort((a, b) => String((a.data as any)?.label || '').localeCompare(String((b.data as any)?.label || '')))
          .forEach((taskNode, idx) => {
            taskNode.position = {
              x: railX,
              y: railStartY + idx * 88,
            };
          });
      }

      // Keep inline workflow fragments as a local mini-DAG above selected task (not detached strips).
      const wfNodes = updatedNodes.filter((n) => n.id.startsWith('wf_'));
      if (wfNodes.length > 0) {
        const nodeById = new Map(updatedNodes.map((n) => [n.id, n]));
        const pushBBoxes: Array<{ x: number; y: number; w: number; h: number }> = [];
        const wfByTask = new Map<string, Node[]>();
        for (const n of wfNodes) {
          if (pinMap[n.id]) continue;
          const taskId = String((n.data as any)?.taskId || '').trim();
          if (!taskId) continue;
          const arr = wfByTask.get(taskId) || [];
          arr.push(n);
          wfByTask.set(taskId, arr);
        }

        for (const [taskId, group] of wfByTask.entries()) {
          const overlay = nodeById.get(`task_overlay_${taskId}`);
          if (!overlay) continue;
          const overlayCenterX = overlay.position.x + Number(overlay.width || 150) / 2;
          const overlayY = overlay.position.y;
          const groupIds = new Set(group.map((n) => n.id));
          const srcById = new Map(inputNodes.map((n) => [n.id, n]));
          const localDagNodes: DAGNode[] = group
            .map((n) => srcById.get(n.id))
            .filter((n): n is DAGNode => !!n);
          const localDagEdges: DAGEdge[] = inputEdges.filter(
            (e) => groupIds.has(e.source) && groupIds.has(e.target)
          );
          if (localDagNodes.length === 0) continue;
          const localHasIncoming = new Set(localDagEdges.map((e) => e.target));
          const architectFirst = localDagNodes
            .find((n) => String((n as any)?.role || '').toLowerCase() === 'architect')?.id;
          const localEntryId =
            architectFirst ||
            localDagNodes
              .map((n) => n.id)
              .sort((a, b) => a.localeCompare(b))
              .find((id) => !localHasIncoming.has(id)) || localDagNodes[0].id;

          // MARKER_155A.G23.WF_LAYER_PHYSICS_V1:
          // Build canonical workflow shape via isolated sublayout (same DAG engine), then embed as micro-layer.
          const localLayout = layoutInlineWorkflowCanonical(localDagNodes, localDagEdges);
          const localById = new Map(localLayout.nodes.map((n) => [n.id, n]));
          const xs = localLayout.nodes.map((n: any) => Number((n.position as any)?.x || 0));
          const ys = localLayout.nodes.map((n: any) => Number((n.position as any)?.y || 0));
          const minX = Math.min(...xs);
          const maxX = Math.max(...xs);
          const minY = Math.min(...ys);
          const maxY = Math.max(...ys);
          const spanX = Math.max(1, maxX - minX);
          const spanY = Math.max(1, maxY - minY);

          // MARKER_155A.G26.WF_MICRO_ENVELOPE:
          // MARKER_155A.G27.RESERVED_WORKFLOW_FRAME:
          // Inline workflow always lives inside fixed reserved frame (invisible "table") near selected task.
          const RESERVED_WF_FRAME_W = 176;
          const RESERVED_WF_FRAME_H = 126;
          const targetW = RESERVED_WF_FRAME_W;
          const targetH = RESERVED_WF_FRAME_H;
          const scale = Math.min(targetW / spanX, targetH / spanY);
          const entryLocal = localById.get(localEntryId);
          const entryScaledX =
            entryLocal && Number.isFinite(Number((entryLocal.position as any)?.x))
              ? ((Number((entryLocal.position as any)?.x) - minX) * scale)
              : targetW / 2;
          // MARKER_155A.G26.WF_ANCHOR_ROOT_LOCK:
          // Lock inline workflow entry/root horizontally to selected task center.
          const anchorX = overlayCenterX - entryScaledX;
          const topYTry = overlayY - targetH - 22;
          const topY = topYTry < 24 ? (overlayY + Number(overlay.height || 60) + 18) : topYTry;

          for (const n of group) {
            const p = localById.get(n.id);
            if (!p) continue;
            n.position = {
              x: anchorX + (p.position.x - minX) * scale,
              // bottom->top invariant: keep workflow above task anchor in roadmap view.
              y: topY + (p.position.y - minY) * scale,
            };
          }

          pushBBoxes.push({
            x: anchorX - 20,
            y: topY - 14,
            w: targetW + 40,
            h: targetH + 28,
          });
        }

        // MARKER_155A.G23.LOCAL_PUSH_V1:
        // Push only nearby conflicting architecture branches; never global relayout.
        // MARKER_155A.G24.LOCAL_REPEL_VECTOR:
        // Resolve collisions with bounded local repel vector (x/y), not one-way downward shift.
        if (pushBBoxes.length > 0) {
          const blockers = updatedNodes.filter((n) =>
            !n.id.startsWith('wf_') &&
            !n.id.startsWith('rd_') &&
            !n.id.startsWith('task_overlay_')
          );
          const overlaps = (
            a: { x: number; y: number; w: number; h: number },
            b: { x: number; y: number; w: number; h: number },
          ) => !(a.x + a.w < b.x || b.x + b.w < a.x || a.y + a.h < b.y || b.y + b.h < a.y);
          const maxShiftX = 160;
          const maxShiftY = 180;
          for (const n of blockers) {
            const box = {
              x: n.position.x,
              y: n.position.y,
              w: Number(n.width || 150),
              h: Number(n.height || 54),
            };
            let shiftX = 0;
            let shiftY = 0;
            for (const wfBox of pushBBoxes) {
              if (!overlaps(box, wfBox)) continue;
              const overlapX =
                Math.min(box.x + box.w, wfBox.x + wfBox.w) - Math.max(box.x, wfBox.x);
              const overlapY =
                Math.min(box.y + box.h, wfBox.y + wfBox.h) - Math.max(box.y, wfBox.y);
              if (overlapX <= 0 || overlapY <= 0) continue;
              const nodeCx = box.x + box.w / 2;
              const nodeCy = box.y + box.h / 2;
              const wfCx = wfBox.x + wfBox.w / 2;
              const wfCy = wfBox.y + wfBox.h / 2;
              if (overlapX < overlapY) {
                const dirX = nodeCx < wfCx ? -1 : 1;
                shiftX += dirX * Math.round(overlapX + 12);
              } else {
                const dirY = nodeCy < wfCy ? -1 : 1;
                shiftY += dirY * Math.round(overlapY + 12);
              }
            }
            if (shiftX !== 0 || shiftY !== 0) {
              const boundedX = Math.max(-maxShiftX, Math.min(maxShiftX, shiftX));
              const boundedY = Math.max(-maxShiftY, Math.min(maxShiftY, shiftY));
              n.position = {
                x: n.position.x + boundedX,
                y: n.position.y + boundedY,
              };
            }
          }
        }
      }

      // MARKER_155A.G23.NODE_DRILL_NEXT_DEPTH:
      // Place roadmap node-drill micro layer above selected parent (bottom->top invariant).
      const rdNodes = updatedNodes.filter((n) => n.id.startsWith('rd_'));
      if (rdNodes.length > 0) {
        const nodeById = new Map(updatedNodes.map((n) => [n.id, n]));
        const rdByParent = new Map<string, Node[]>();
        for (const n of rdNodes) {
          if (pinMap[n.id]) continue;
          const parentId = String((n.data as any)?.rd_parent || '');
          if (!parentId) continue;
          const arr = rdByParent.get(parentId) || [];
          arr.push(n);
          rdByParent.set(parentId, arr);
        }

        for (const [parentId, group] of rdByParent.entries()) {
          const parent = nodeById.get(parentId);
          if (!parent) continue;
          const centerX = parent.position.x + Number(parent.width || 160) / 2;
          const parentTopY = parent.position.y;
          const xGap = 62;
          const yGap = 42;
          const byDepth = new Map<number, Node[]>();
          for (const n of group) {
            const d = Math.max(1, Number((n.data as any)?.rd_depth || 1));
            const row = byDepth.get(d) || [];
            row.push(n);
            byDepth.set(d, row);
          }
          const depthKeys = Array.from(byDepth.keys()).sort((a, b) => a - b);
          for (const d of depthKeys) {
            const row = (byDepth.get(d) || []).sort((a, b) => a.id.localeCompare(b.id));
            const rowWidth = Math.max(0, row.length - 1) * xGap;
            const rowStartX = centerX - rowWidth / 2;
            const rowY = parentTopY - 54 - (d - 1) * yGap;
            row.forEach((n, idx) => {
              n.position = {
                x: rowStartX + idx * xGap,
                y: rowY,
              };
            });
          }
        }
      }
    }

    // Update position map for next render
    const newPositions: PositionMap = {};
    updatedNodes.forEach((n) => {
      newPositions[n.id] = n.position;
    });
    if (layoutMode === 'architecture' && (hasWorkflowInline || hasRoadmapDrillInline)) {
      // Keep only non-inline architecture anchors in cache while inline overlays are active.
      const retained: PositionMap = {};
      for (const [id, pos] of Object.entries(newPositions)) {
        if (isInlineOverlayNodeId(id)) continue;
        retained[id] = pos;
      }
      prevPositionsRef.current = retained;
    } else {
      prevPositionsRef.current = newPositions;
    }

    return { nodes: updatedNodes, edges: result.edges };
  }, [inputNodes, inputEdges, compact, graphIdentity, layoutMode, layoutBiasProfile, isInlineOverlayNodeId]);

  const hasInlineWorkflow = useMemo(
    () => layoutedNodes.some((n) => n.id.startsWith('wf_')),
    [layoutedNodes],
  );

  // xyflow state
  const fractalNodes = useMemo(() => {
    if (cameraLOD === 'workflow') return layoutedNodes;

    return layoutedNodes.map(node => {
      // Keep architecture/task roots visually dominant when zoomed out.
      const isWorkflowEntity = node.type === 'agent' || node.type === 'subtask' || node.type === 'proposal';
      if (hasInlineWorkflow) {
        return {
          ...node,
          style: {
            ...node.style,
            opacity: 1,
          },
        };
      }
      const shouldDim = cameraLOD === 'architecture' ? isWorkflowEntity : node.type === 'proposal';
      if (!shouldDim) return node;
      return {
        ...node,
        style: {
          ...node.style,
          opacity: cameraLOD === 'architecture' ? 0.28 : 0.5,
        },
      };
    });
  }, [layoutedNodes, cameraLOD, hasInlineWorkflow]);

  const [nodes, setNodes, onNodesChange] = useNodesState(fractalNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

  // MARKER_155A.G21.VECTOR_EDGE_STYLE:
  // Render all loaded edges as direct vectors regardless of upstream edge type.
  const vectorEdgesForRender = useMemo(
    () =>
      edges.map((edge): Edge => {
        const isMicroInline =
          String(edge.id || '').startsWith('wf_') ||
          String(edge.id || '').startsWith('rd_') ||
          String((edge as any).className || '').includes('wf-inline-edge') ||
          String((edge as any).className || '').includes('wf-bridge-edge');
        return {
          ...edge,
          // MARKER_155A.G27.GLOBAL_HANDLE_FLOW:
          // Global geometry contract: output from top, input to bottom.
          sourceHandle: edge.sourceHandle || 'source-top',
          targetHandle: edge.targetHandle || 'target-bottom',
          type: 'straight',
          markerEnd: edge.markerEnd || { type: MarkerType.ArrowClosed, color: '#7d8590' },
          style: {
            ...(edge.style || {}),
            strokeWidth: isMicroInline ? 0.7 : Number((edge.style as any)?.strokeWidth || 1),
            opacity: isMicroInline ? 0.78 : Number((edge.style as any)?.opacity || 1),
          },
        };
      }),
    [edges],
  );

  // MARKER_155.2: ReactFlow instance for zoom control
  const reactFlow = useReactFlow();
  const nodesRef = useRef(nodes);
  const didApplyInitialCameraRef = useRef(false);
  const clickTimerRef = useRef<number | null>(null);

  // Keep nodes ref updated for imperative handle
  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);

  const emitViewport = useCallback(() => {
    const viewport = reactFlow.getViewport();
    const camera = { x: viewport.x, y: viewport.y, zoom: viewport.zoom };
    const lod = getLODLevel(viewport.zoom);
    setCameraLOD(lod);
    onLODChange?.(lod);
    onCameraChange?.(camera, lod);
  }, [reactFlow, onCameraChange, onLODChange]);

  // MARKER_155A.P2.CAMERA_STATE: Restore persisted viewport once after mount.
  useEffect(() => {
    if (didApplyInitialCameraRef.current) return;
    if (!initialCamera) return;
    didApplyInitialCameraRef.current = true;
    reactFlow.setViewport(initialCamera, { duration: 250 });
    const lod = getLODLevel(initialCamera.zoom);
    setCameraLOD(lod);
    onLODChange?.(lod);
  }, [initialCamera, reactFlow, onLODChange]);

  // MARKER_155.3: Expose zoom functions via ref
  useImperativeHandle(ref, () => ({
    zoomToNode: (nodeId: string, level: number) => {
      const targetNode = nodesRef.current.find(n => n.id === nodeId);
      if (!targetNode) {
        console.warn('[DAGView] Node not found for zoom:', nodeId);
        return;
      }
      const zoomConfig = ZOOM_LEVELS[level as keyof typeof ZOOM_LEVELS];
      const targetZoom = zoomConfig?.min || 1.5;
      const nodeWidth = Number((targetNode as any).measured?.width ?? targetNode.width ?? 0);
      const nodeHeight = Number((targetNode as any).measured?.height ?? targetNode.height ?? 0);
      const centerX = targetNode.position.x + (nodeWidth > 0 ? nodeWidth / 2 : 0);
      const centerY = targetNode.position.y + (nodeHeight > 0 ? nodeHeight / 2 : 0);
      
      reactFlow.setCenter(centerX, centerY, {
        zoom: targetZoom,
        duration: 800,
      });
      // Track viewport state after animated move.
      window.setTimeout(() => emitViewport(), 850);
    },
    zoomOut: () => {
      reactFlow.fitView({ duration: 800, padding: 0.2 });
      window.setTimeout(() => emitViewport(), 850);
    },
    getCameraPosition: (): CameraPosition | null => {
      const viewport = reactFlow.getViewport();
      return { x: viewport.x, y: viewport.y, zoom: viewport.zoom };
    },
    fitView: () => {
      reactFlow.fitView({ padding: 0.2, duration: 400 });
      window.setTimeout(() => emitViewport(), 450);
    },
  }), [reactFlow, emitViewport]);

  // Keep a ref to the base edges (before highlighting) for reset
  const baseEdgesRef = useRef<Edge[]>(layoutedEdges);

  // Update nodes/edges when layout changes
  useEffect(() => {
    setNodes(fractalNodes);
    setEdges(layoutedEdges);
    baseEdgesRef.current = layoutedEdges;
  }, [fractalNodes, layoutedEdges, setNodes, setEdges]);

  // MARKER_137.2B: Apply edge highlighting when selected node set changes.
  useEffect(() => {
    const focusIds = new Set<string>(
      selectedNodeIds.length > 0
        ? selectedNodeIds
        : selectedNode
          ? [selectedNode]
          : []
    );

    if (focusIds.size === 0) {
      // Reset all edges and nodes to default
      setEdges(baseEdgesRef.current);
      setNodes(nds => nds.map(n => ({
        ...n,
        style: { ...n.style, opacity: 1 },
      })));
      return;
    }

    // Find connected edges
    const connectedEdgeIds = new Set<string>();
    const connectedNodeIds = new Set<string>();
    for (const id of focusIds) connectedNodeIds.add(id);

    baseEdgesRef.current.forEach(e => {
      if (focusIds.has(e.source) || focusIds.has(e.target)) {
        connectedEdgeIds.add(e.id);
        connectedNodeIds.add(e.source);
        connectedNodeIds.add(e.target);
      }
    });

    if (hasInlineWorkflow) {
      // MARKER_155A.G24.HIGHLIGHT_INLINE_CONTEXT:
      // Keep full-context opacity for nodes while preserving edge emphasis for selection.
      setEdges(baseEdgesRef.current.map(e => {
        const isConnected = connectedEdgeIds.has(e.id);
        return {
          ...e,
          style: {
            ...e.style,
            stroke: isConnected ? '#fff' : (e.style?.stroke || NOLAN_PALETTE.edgeStructural),
            strokeWidth: isConnected ? 2.2 : 1,
            opacity: isConnected ? 1.0 : 0.56,
          },
          animated: isConnected ? true : false,
          zIndex: isConnected ? 10 : 0,
        };
      }));
      setNodes(nds => nds.map(n => ({
        ...n,
        style: {
          ...n.style,
          opacity: 1,
        },
      })));
      return;
    }

    // Update edges: brighten connected, dim others
    setEdges(baseEdgesRef.current.map(e => {
      const isConnected = connectedEdgeIds.has(e.id);
      return {
        ...e,
        style: {
          ...e.style,
          stroke: isConnected ? '#fff' : (e.style?.stroke || NOLAN_PALETTE.edgeStructural),
          strokeWidth: isConnected ? 2.5 : 1,
          opacity: isConnected ? 1.0 : 0.08,
        },
        animated: isConnected ? true : false,
        zIndex: isConnected ? 10 : 0,
      };
    }));

    // Update nodes: dim unconnected
    setNodes(nds => nds.map(n => ({
      ...n,
      style: {
        ...n.style,
        opacity: connectedNodeIds.has(n.id) ? 1.0 : 0.25,
      },
    })));
  }, [selectedNode, selectedNodeIds, layoutedEdges, setEdges, setNodes, hasInlineWorkflow]);

  // Track user drag changes
  const handleNodesChange = useCallback((changes: any) => {
    onNodesChange(changes);

    // Update position map when user drags nodes
    let changed = false;
    const nextPins: PositionMap = { ...pinnedPositionsRef.current };
    changes.forEach((change: any) => {
      if (change.type === 'position' && change.position) {
        prevPositionsRef.current[change.id] = change.position;
        if (isInlineOverlayNodeId(change.id)) return;
        nextPins[change.id] = change.position;
        changed = true;
      }
    });
    if (changed) {
      pinnedPositionsRef.current = nextPins;
      if (persistPinsTimerRef.current !== null) {
        window.clearTimeout(persistPinsTimerRef.current);
      }
      persistPinsTimerRef.current = window.setTimeout(() => {
        onPinnedPositionsChange?.(nextPins);
      }, 120);
    }
  }, [onNodesChange, onPinnedPositionsChange, isInlineOverlayNodeId]);

  useEffect(() => {
    return () => {
      if (clickTimerRef.current !== null) {
        window.clearTimeout(clickTimerRef.current);
      }
      if (persistPinsTimerRef.current !== null) {
        window.clearTimeout(persistPinsTimerRef.current);
      }
    };
  }, []);

  // Handle node click
  const onNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      if (event.detail > 1) return;
      if (clickTimerRef.current !== null) {
        window.clearTimeout(clickTimerRef.current);
      }
      clickTimerRef.current = window.setTimeout(() => {
        clickTimerRef.current = null;
        const additive = !!event.shiftKey;
        // MARKER_155A.G24.CLICK_DBLCLICK_DEBOUNCE:
        // 220ms debounce separates single vs double click. Keep aligned with UX contract docs.
        if (onNodeSelectWithMode) {
          onNodeSelectWithMode(node.id, { additive });
          return;
        }
        // Toggle: click same node again → deselect
        if (node.id === selectedNode) {
          onNodeSelect?.(null);
        } else {
          onNodeSelect?.(node.id);
        }
      }, 220);
    },
    [onNodeSelect, onNodeSelectWithMode, selectedNode]
  );

  // MARKER_153.5D: Handle node double-click — Matryoshka drill-down
  const handleNodeDoubleClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (clickTimerRef.current !== null) {
        window.clearTimeout(clickTimerRef.current);
        clickTimerRef.current = null;
      }
      onNodeDoubleClick?.(node.id);
    },
    [onNodeDoubleClick]
  );

  // Handle edge click
  const onEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      onEdgeSelect?.(edge.id);
    },
    [onEdgeSelect]
  );

  // Handle pane click (deselect)
  const onPaneClick = useCallback((event: React.MouseEvent) => {
    // Immediate visual reset, then propagate selection clear upstream.
    setEdges(baseEdgesRef.current);
    setNodes(nds => nds.map(n => ({
      ...n,
      style: { ...n.style, opacity: 1 },
    })));
    onNodeSelectWithMode?.(null, { additive: false });
    onNodeSelect?.(null);
    onEdgeSelect?.(null);
    if (editMode && event.detail === 2) {
      onPaneDoubleClick?.({ x: event.clientX, y: event.clientY });
    }
  }, [editMode, onNodeSelect, onNodeSelectWithMode, onEdgeSelect, onPaneDoubleClick, setEdges, setNodes]);

  // MARKER_155.G1.TASK_ANCHORING_CONTRACT_V1:
  // Allow controlled context menu in read-only roadmap mode for task anchoring.
  const canOpenContextMenu = Boolean(onContextMenu) && (contextMenuEnabled ?? editMode);

  const handleNodeContextMenu = useCallback(
    (event: React.MouseEvent, node: Node) => {
      if (!canOpenContextMenu || !onContextMenu) return;
      event.preventDefault();
      onContextMenu(event, { kind: 'node', id: node.id, position: { x: event.clientX, y: event.clientY } });
    },
    [canOpenContextMenu, onContextMenu]
  );

  const handleEdgeContextMenu = useCallback(
    (event: React.MouseEvent, edge: Edge) => {
      if (!canOpenContextMenu || !onContextMenu) return;
      event.preventDefault();
      onContextMenu(event, { kind: 'edge', id: edge.id, position: { x: event.clientX, y: event.clientY } });
    },
    [canOpenContextMenu, onContextMenu]
  );

  const handlePaneContextMenu = useCallback(
    (event: MouseEvent | React.MouseEvent) => {
      if (!canOpenContextMenu || !onContextMenu) return;
      event.preventDefault();
      onContextMenu(event as React.MouseEvent, { kind: 'canvas', position: { x: event.clientX, y: event.clientY } });
    },
    [canOpenContextMenu, onContextMenu]
  );

  // MARKER_137.2C: Get node color for minimap (actually used now)
  const getNodeColor = useCallback((node: Node): string => {
    const status = node.data?.status as NodeStatus;
    switch (status) {
      case 'running': return NOLAN_PALETTE.statusRunning;
      case 'done': return NOLAN_PALETTE.statusDone;
      case 'failed': return NOLAN_PALETTE.statusFailed;
      default: return NOLAN_PALETTE.statusPending;
    }
  }, []);

  return (
    <div
      style={{
        width,
        height,
        background: NOLAN_PALETTE.bg,
        borderRadius: 4,
        overflow: 'hidden',
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={vectorEdgesForRender}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onNodeDoubleClick={onNodeDoubleClick ? handleNodeDoubleClick : undefined}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView={false}
        minZoom={0.2}
        maxZoom={3}
        zoomOnDoubleClick={false}
        nodesDraggable={true}
        nodesConnectable={editMode}
        elementsSelectable={true}
        proOptions={{ hideAttribution: true }}
        // MARKER_151.2C: Orthogonal edge routing for new connections
        // MARKER_155A.G21.VECTOR_EDGE_STYLE: Directional vectors input->output by default.
        connectionLineType={ConnectionLineType.Straight}
        defaultEdgeOptions={{
          type: 'straight',
          markerEnd: { type: MarkerType.ArrowClosed, color: '#7d8590' },
        }}
        connectionLineStyle={{ stroke: '#7d8590', strokeWidth: 1.8 }}
        // MARKER_144.2: Edit mode handlers (no-op when editMode=false)
        onConnect={editMode ? onConnect : undefined}
        onNodesDelete={editMode ? onNodesDelete : undefined}
        onEdgesDelete={editMode ? onEdgesDelete : undefined}
        deleteKeyCode={editMode ? 'Delete' : null}
        // MARKER_144.3: Context menu handlers (no-op when editMode=false)
        onNodeContextMenu={canOpenContextMenu ? handleNodeContextMenu : undefined}
        onEdgeContextMenu={canOpenContextMenu ? handleEdgeContextMenu : undefined}
        onPaneContextMenu={canOpenContextMenu ? handlePaneContextMenu : undefined}
        onMoveEnd={emitViewport}
      >
        <Background color="#111" gap={32} size={1} />
        <Controls
          position="bottom-left"
          style={{
            background: NOLAN_PALETTE.bgDim,
            border: `1px solid ${NOLAN_PALETTE.border}`,
            borderRadius: 4,
          }}
        />
        {/* MARKER_137.2C: MiniMap now uses actual status colors */}
        <MiniMap
          position="bottom-right"
          nodeColor={getNodeColor}
          maskColor="rgba(0,0,0,0.85)"
          style={{
            background: '#0a0a0a',
            border: `1px solid ${NOLAN_PALETTE.border}`,
            borderRadius: 4,
          }}
        />
      </ReactFlow>

      {/* CSS animations for running nodes + fade-in */}
      {/* MARKER_135.4E: Fade-in animation for new nodes */}
      <style>{`
        @keyframes nodePulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }

        @keyframes nodeFadeIn {
          from {
            opacity: 0;
            transform: scale(0.9) translateY(10px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }

        .react-flow__node {
          animation: none;
          transition: transform 420ms cubic-bezier(0.22, 0.61, 0.36, 1), opacity 0.22s linear;
        }

        .react-flow__node.dragging {
          transition: none !important;
        }

        .react-flow__node.selected {
          z-index: 10 !important;
        }

        .react-flow__edge.animated path {
          stroke-dasharray: 5;
          animation: edgeFlow 1s linear infinite;
        }

        @keyframes edgeFlow {
          to { stroke-dashoffset: -10; }
        }

        .react-flow__edge {
          animation: none;
          transition: opacity 0.12s linear;
        }

        .react-flow__edge path {
          transition: stroke 0.2s ease, stroke-width 0.2s ease, opacity 0.2s ease;
        }

        .react-flow__edge.wf-inline-edge path,
        .react-flow__edge.wf-bridge-edge path {
          stroke-width: 0.7px !important;
          opacity: 0.78 !important;
        }

        /* Controls button styling for dark theme */
        .react-flow__controls button {
          background: ${NOLAN_PALETTE.bgDim} !important;
          border-color: ${NOLAN_PALETTE.border} !important;
          color: ${NOLAN_PALETTE.textMuted} !important;
          fill: ${NOLAN_PALETTE.textMuted} !important;
        }
        .react-flow__controls button:hover {
          background: ${NOLAN_PALETTE.bgLight} !important;
        }
        .react-flow__controls button svg {
          fill: ${NOLAN_PALETTE.textMuted} !important;
        }

        /* MARKER_151.4A: Always-visible handles + clearer drag affordance */
        .react-flow__handle {
          opacity: 1 !important;
          width: 9px !important;
          height: 9px !important;
          border: 1px solid #101010 !important;
          background: #6a6a6a !important;
        }

        .react-flow__handle-connecting {
          background: #ff6b6b !important;
        }

        .react-flow__handle-valid {
          background: #4ecdc4 !important;
        }

        /* MARKER_155A.G27.MICRO_HANDLE_DOWNSCALE:
           Inline wf/rd overlays use tiny handles to avoid visual clutter in reserved workflow frame. */
        .react-flow__node[data-id^="wf_"] .react-flow__handle,
        .react-flow__node[data-id^="rd_"] .react-flow__handle {
          width: 4px !important;
          height: 4px !important;
          border-width: 1px !important;
        }

        /* MARKER_154.6A: Show double-click hint on roadmap node hover */
        .react-flow__node:hover .roadmap-node-hint {
          opacity: 1 !important;
        }

        /* MARKER_155A.DANGER.STUB.HINT_WORKFLOW_PREVIEW:
           Placeholder for tiny workflow previews on architecture LOD, guarded by perf budget. */
      `}</style>
    </div>
  );
});
