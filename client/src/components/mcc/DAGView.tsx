/**
 * MARKER_135.1A: DAG View — main visualization component.
 * Uses xyflow for interactive graph with Sugiyama BT layout.
 * Root at bottom, proposals at top — VETKA spatial metaphor.
 *
 * @phase 135.1
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
  type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { TaskNode } from './nodes/TaskNode';
import { AgentNode } from './nodes/AgentNode';
import { SubtaskNode } from './nodes/SubtaskNode';
import { ProposalNode } from './nodes/ProposalNode';
import { layoutSugiyamaBT, createTestDAGData, NOLAN_PALETTE } from '../../utils/dagLayout';
import type { DAGNode, DAGEdge, NodeStatus } from '../../types/dag';

// MARKER_135.4F: Track node positions for incremental layout
type PositionMap = Record<string, { x: number; y: number }>;

// Register custom node types (use Record for xyflow v12 compatibility)
const nodeTypes = {
  task: TaskNode,
  agent: AgentNode,
  subtask: SubtaskNode,
  proposal: ProposalNode,
} as const;

interface DAGViewProps {
  dagNodes?: DAGNode[];
  dagEdges?: DAGEdge[];
  selectedNode?: string | null;
  onNodeSelect?: (nodeId: string | null) => void;
  width?: number | string;
  height?: number | string;
}

export function DAGView({
  dagNodes,
  dagEdges,
  selectedNode,
  onNodeSelect,
  width = '100%',
  height = '100%',
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

  // Update nodes/edges when layout changes
  useEffect(() => {
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges]);

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
      onNodeSelect?.(node.id);
    },
    [onNodeSelect]
  );

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    onNodeSelect?.(null);
  }, [onNodeSelect]);

  // Get node color for minimap
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
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={3}
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={true}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#222" gap={24} />
        <Controls
          position="bottom-left"
          style={{
            background: NOLAN_PALETTE.bgDim,
            border: `1px solid ${NOLAN_PALETTE.border}`,
            borderRadius: 4,
          }}
        />
        <MiniMap
          position="bottom-right"
          nodeColor={getNodeColor}
          maskColor="rgba(10,10,10,0.85)"
          style={{
            background: NOLAN_PALETTE.bgDim,
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
        }
      `}</style>
    </div>
  );
}
