/**
 * MARKER_135.1A: DAG View — main visualization component.
 * MARKER_137.2A: Edge highlighting on node select (VETKA-style).
 * Uses xyflow for interactive graph with Sugiyama BT layout.
 * Root at bottom, proposals at top — VETKA spatial metaphor.
 *
 * @phase 137
 * @status active
 */

import { useCallback, useEffect, useMemo, useRef } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  ConnectionLineType,
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
import { layoutSugiyamaBT, createTestDAGData, NOLAN_PALETTE } from '../../utils/dagLayout';
import type { DAGNode, DAGEdge, NodeStatus } from '../../types/dag';

// MARKER_135.4F: Track node positions for incremental layout
type PositionMap = Record<string, { x: number; y: number }>;

// Register custom node types (use Record for xyflow v12 compatibility)
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
} as const;

interface DAGViewProps {
  dagNodes?: DAGNode[];
  dagEdges?: DAGEdge[];
  selectedNode?: string | null;
  onNodeSelect?: (nodeId: string | null) => void;
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
}

export function DAGView({
  dagNodes,
  dagEdges,
  selectedNode,
  onNodeSelect,
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
}: DAGViewProps) {
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

  // Apply Sugiyama BT layout with incremental position preservation
  const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(() => {
    const result = layoutSugiyamaBT(inputNodes, inputEdges);

    // Preserve positions of existing nodes (incremental layout)
    const prevPositions = prevPositionsRef.current;
    const updatedNodes = result.nodes.map(node => {
      const prevPos = prevPositions[node.id];
      if (prevPos) {
        // Keep existing position for smooth updates
        return { ...node, position: prevPos };
      }
      return node;
    });

    // Update position map for next render
    const newPositions: PositionMap = {};
    updatedNodes.forEach(n => {
      newPositions[n.id] = n.position;
    });
    prevPositionsRef.current = newPositions;

    return { nodes: updatedNodes, edges: result.edges };
  }, [inputNodes, inputEdges]);

  // xyflow state
  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

  // Keep a ref to the base edges (before highlighting) for reset
  const baseEdgesRef = useRef<Edge[]>(layoutedEdges);

  // Update nodes/edges when layout changes
  useEffect(() => {
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
    baseEdgesRef.current = layoutedEdges;
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges]);

  // MARKER_137.2B: Apply edge highlighting when selectedNode changes
  useEffect(() => {
    if (!selectedNode) {
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
    connectedNodeIds.add(selectedNode);

    baseEdgesRef.current.forEach(e => {
      if (e.source === selectedNode || e.target === selectedNode) {
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
  }, [selectedNode, setEdges, setNodes]);

  // Track user drag changes
  const handleNodesChange = useCallback((changes: any) => {
    onNodesChange(changes);

    // Update position map when user drags nodes
    changes.forEach((change: any) => {
      if (change.type === 'position' && change.position) {
        prevPositionsRef.current[change.id] = change.position;
      }
    });
  }, [onNodesChange]);

  // Handle node click
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      // Toggle: click same node again → deselect
      if (node.id === selectedNode) {
        onNodeSelect?.(null);
      } else {
        onNodeSelect?.(node.id);
      }
    },
    [onNodeSelect, selectedNode]
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
    onNodeSelect?.(null);
    onEdgeSelect?.(null);
    if (editMode && event.detail === 2) {
      onPaneDoubleClick?.({ x: event.clientX, y: event.clientY });
    }
  }, [editMode, onNodeSelect, onEdgeSelect, onPaneDoubleClick]);

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
        edges={edges}
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
        connectionLineType={ConnectionLineType.Step}
        defaultEdgeOptions={{ type: 'step' }}
        connectionLineStyle={{ stroke: '#4ecdc4', strokeWidth: 2 }}
        // MARKER_144.2: Edit mode handlers (no-op when editMode=false)
        onConnect={editMode ? onConnect : undefined}
        onNodesDelete={editMode ? onNodesDelete : undefined}
        onEdgesDelete={editMode ? onEdgesDelete : undefined}
        deleteKeyCode={editMode ? 'Delete' : null}
        // MARKER_144.3: Context menu handlers (no-op when editMode=false)
        onNodeContextMenu={editMode ? handleNodeContextMenu : undefined}
        onEdgeContextMenu={editMode ? handleEdgeContextMenu : undefined}
        onPaneContextMenu={editMode ? handlePaneContextMenu : undefined}
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
      `}</style>
    </div>
  );
}
