/**
 * MARKER_152.10: TaskDAGView — Task-level DAG showing all tasks as nodes.
 * Fetches from /api/analytics/dag/tasks, applies dagre layout, renders ReactFlow.
 * Read-only: single-click selects, double-click drills into workflow DAG.
 *
 * @phase 152
 * @status active
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  MiniMap,
  Controls,
  type Node,
  type Edge,
  ConnectionLineType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { TaskDAGNode } from './nodes/TaskDAGNode';

const API_BASE = 'http://localhost:5001/api';

const nodeTypes = { taskNode: TaskDAGNode };

interface TaskDAGViewProps {
  onTaskSelect: (taskId: string) => void;
  onTaskDrillDown: (taskId: string) => void;
  selectedTaskId?: string | null;
}

// --- Dagre layout ---
function applyDagreLayout(
  nodes: Node[],
  edges: Edge[],
): Node[] {
  if (nodes.length === 0) return nodes;

  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'TB', ranksep: 80, nodesep: 40, marginx: 20, marginy: 20 });

  nodes.forEach(n => g.setNode(n.id, { width: 220, height: 70 }));
  edges.forEach(e => g.setEdge(e.source, e.target));

  dagre.layout(g);

  return nodes.map(n => {
    const pos = g.node(n.id);
    if (!pos) return n;
    return {
      ...n,
      position: { x: pos.x - 110, y: pos.y - 35 },
    };
  });
}

export function TaskDAGView({
  onTaskSelect,
  onTaskDrillDown,
  selectedTaskId,
}: TaskDAGViewProps) {
  const [rawNodes, setRawNodes] = useState<Node[]>([]);
  const [rawEdges, setRawEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch task DAG data
  const fetchDAG = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/analytics/dag/tasks?limit=50`);
      if (!res.ok) {
        setError(`API ${res.status}`);
        return;
      }
      const data = await res.json();
      if (!data.success) {
        setError(data.error || 'API error');
        return;
      }
      setRawNodes(data.nodes || []);
      setRawEdges(
        (data.edges || []).map((e: Edge) => ({
          ...e,
          type: 'smoothstep',
          style: { stroke: NOLAN_PALETTE.edgeStructural, strokeWidth: 1.5 },
        })),
      );
      setError(null);
    } catch (err) {
      setError('fetch failed');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch on mount + event-driven refresh
  useEffect(() => {
    fetchDAG();
    const handler = () => fetchDAG();
    window.addEventListener('task-board-updated', handler);
    return () => window.removeEventListener('task-board-updated', handler);
  }, [fetchDAG]);

  // Inject selectedTaskId into node data + apply dagre layout
  const layoutNodes = useMemo(() => {
    const withSelection = rawNodes.map(n => ({
      ...n,
      data: { ...n.data, selectedTaskId },
    }));
    return applyDagreLayout(withSelection, rawEdges);
  }, [rawNodes, rawEdges, selectedTaskId]);

  // Handle clicks
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onTaskSelect(node.id);
    },
    [onTaskSelect],
  );

  const handleNodeDoubleClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onTaskDrillDown(node.id);
    },
    [onTaskDrillDown],
  );

  // Loading / error / empty states
  if (loading) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100%', color: NOLAN_PALETTE.textDim, fontFamily: 'monospace', fontSize: 10,
      }}>
        Loading task DAG...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100%', color: '#a66', fontFamily: 'monospace', fontSize: 10,
      }}>
        Error: {error}
      </div>
    );
  }

  if (layoutNodes.length === 0) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        height: '100%', color: NOLAN_PALETTE.textDim, fontFamily: 'monospace', fontSize: 10,
        gap: 8,
      }}>
        <span>No tasks yet.</span>
        <span style={{ color: NOLAN_PALETTE.textDimmer, fontSize: 9 }}>
          Use <code style={{ color: NOLAN_PALETTE.textMuted }}>@dragon</code> in chat to create tasks.
        </span>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={layoutNodes}
        edges={rawEdges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onNodeDoubleClick={handleNodeDoubleClick}
        connectionLineType={ConnectionLineType.SmoothStep}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
        panOnDrag={true}
        zoomOnScroll={true}
        style={{ background: '#0a0a0a' }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#1a1a1a"
        />
        <MiniMap
          nodeColor={(n) => (n.data as Record<string, unknown>)?.color as string || '#555'}
          style={{ background: '#111', border: `1px solid ${NOLAN_PALETTE.borderDim}` }}
          maskColor="rgba(0,0,0,0.7)"
        />
        <Controls
          showInteractive={false}
          style={{ background: '#111', border: `1px solid ${NOLAN_PALETTE.borderDim}` }}
        />
      </ReactFlow>

      {/* Pulse animation for running nodes */}
      <style>{`
        @keyframes taskDagPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
      `}</style>
    </div>
  );
}
