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

  useEffect(() => {
    pinnedPositionsRef.current = pinnedPositions || {};
  }, [pinnedPositions]);

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
    const keepIncremental = layoutMode !== 'architecture';
    let updatedNodes = result.nodes.map(node => {
      if (!keepIncremental) return node;
      const prevPos = prevPositions[node.id];
      if (prevPos) {
        // Keep existing position for smooth updates
        return { ...node, position: prevPos };
      }
      return node;
    });

    // MARKER_155A.P2.PIN_LAYOUT:
    // Persisted user drag positions have highest priority over auto layout.
    const pinMap = pinnedPositionsRef.current || {};
    if (Object.keys(pinMap).length > 0) {
      updatedNodes = updatedNodes.map(node => {
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
    }

    // Update position map for next render
    const newPositions: PositionMap = {};
    updatedNodes.forEach(n => {
      newPositions[n.id] = n.position;
    });
    prevPositionsRef.current = newPositions;

    return { nodes: updatedNodes, edges: result.edges };
  }, [inputNodes, inputEdges, compact, graphIdentity, layoutMode, layoutBiasProfile]);

  // xyflow state
  const fractalNodes = useMemo(() => {
    if (cameraLOD === 'workflow') return layoutedNodes;

    return layoutedNodes.map(node => {
      // Keep architecture/task roots visually dominant when zoomed out.
      const isWorkflowEntity = node.type === 'agent' || node.type === 'subtask' || node.type === 'proposal';
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
  }, [layoutedNodes, cameraLOD]);

  const [nodes, setNodes, onNodesChange] = useNodesState(fractalNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

  // MARKER_155A.G21.VECTOR_EDGE_STYLE:
  // Render all loaded edges as direct vectors regardless of upstream edge type.
  const vectorEdgesForRender = useMemo(
    () =>
      edges.map((edge): Edge => ({
        ...edge,
        type: 'straight',
        markerEnd: edge.markerEnd || { type: MarkerType.ArrowClosed, color: '#7d8590' },
      })),
    [edges],
  );

  // MARKER_155.2: ReactFlow instance for zoom control
  const reactFlow = useReactFlow();
  const nodesRef = useRef(nodes);
  const didApplyInitialCameraRef = useRef(false);

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
      
      reactFlow.setCenter(targetNode.position.x, targetNode.position.y, {
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
  }, [selectedNode, selectedNodeIds, layoutedEdges, setEdges, setNodes]);

  // Track user drag changes
  const handleNodesChange = useCallback((changes: any) => {
    onNodesChange(changes);

    // Update position map when user drags nodes
    let changed = false;
    const nextPins: PositionMap = { ...pinnedPositionsRef.current };
    changes.forEach((change: any) => {
      if (change.type === 'position' && change.position) {
        prevPositionsRef.current[change.id] = change.position;
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
  }, [onNodesChange, onPinnedPositionsChange]);

  useEffect(() => {
    return () => {
      if (persistPinsTimerRef.current !== null) {
        window.clearTimeout(persistPinsTimerRef.current);
      }
    };
  }, []);

  // Handle node click
  const onNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      const additive = !!event.shiftKey;
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
    },
    [onNodeSelect, onNodeSelectWithMode, selectedNode]
  );

  // MARKER_153.5D: Handle node double-click — Matryoshka drill-down
  const handleNodeDoubleClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
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

  // MARKER_144.3: Right-click handlers for context menu (only in edit mode)
  const handleNodeContextMenu = useCallback(
    (event: React.MouseEvent, node: Node) => {
      if (!editMode || !onContextMenu) return;
      event.preventDefault();
      onContextMenu(event, { kind: 'node', id: node.id, position: { x: event.clientX, y: event.clientY } });
    },
    [editMode, onContextMenu]
  );

  const handleEdgeContextMenu = useCallback(
    (event: React.MouseEvent, edge: Edge) => {
      if (!editMode || !onContextMenu) return;
      event.preventDefault();
      onContextMenu(event, { kind: 'edge', id: edge.id, position: { x: event.clientX, y: event.clientY } });
    },
    [editMode, onContextMenu]
  );

  const handlePaneContextMenu = useCallback(
    (event: MouseEvent | React.MouseEvent) => {
      if (!editMode || !onContextMenu) return;
      event.preventDefault();
      onContextMenu(event as React.MouseEvent, { kind: 'canvas', position: { x: event.clientX, y: event.clientY } });
    },
    [editMode, onContextMenu]
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
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={3}
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
        onNodeContextMenu={editMode ? handleNodeContextMenu : undefined}
        onEdgeContextMenu={editMode ? handleEdgeContextMenu : undefined}
        onPaneContextMenu={editMode ? handlePaneContextMenu : undefined}
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
          animation: nodeFadeIn 0.3s ease-out;
          transition: opacity 0.2s ease;
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
          animation: nodeFadeIn 0.4s ease-out;
          transition: opacity 0.2s ease;
        }

        .react-flow__edge path {
          transition: stroke 0.2s ease, stroke-width 0.2s ease, opacity 0.2s ease;
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
