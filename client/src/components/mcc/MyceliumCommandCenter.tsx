/**
 * MARKER_135.1A: Mycelium Command Center — main container.
 * MARKER_135.2C: Connected to real API (Wave 2).
 * MARKER_135.3A: Live updates via WebSocket (Wave 3).
 * DAG View (80%) + Detail Panel (20%).
 * Unified view replacing 7 tabs.
 *
 * @phase 135.3
 * @status active
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { DAGView } from './DAGView';
import { DetailPanel } from './DetailPanel';
import { FilterBar } from './FilterBar';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { useMyceliumSocket } from '../../hooks/useMyceliumSocket';
import type { DAGNode, DAGEdge, DAGFilters, DAGStats } from '../../types/dag';

const API_BASE = 'http://localhost:5001/api';

interface MyceliumCommandCenterProps {
  standalone?: boolean;
}

interface StreamEvent {
  id: string;
  ts: number;
  role: string;
  message: string;
  taskId?: string;
}

// Convert backend response to frontend types
function mapBackendNode(node: any): DAGNode {
  return {
    id: node.id,
    type: node.type,
    label: node.label,
    status: node.status,
    layer: node.layer,
    taskId: node.task_id,
    parentId: node.parent_id,
    startedAt: node.started_at,
    completedAt: node.completed_at,
    durationS: node.duration_s,
    tokens: node.tokens,
    model: node.model,
    confidence: node.confidence,
    role: node.role,
    description: node.description,
  };
}

function mapBackendEdge(edge: any): DAGEdge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: edge.type,
    strength: edge.strength,
  };
}

function mapBackendStats(stats: any): DAGStats {
  return {
    totalTasks: stats.total_tasks || 0,
    runningTasks: stats.running_tasks || 0,
    completedTasks: stats.completed_tasks || 0,
    failedTasks: stats.failed_tasks || 0,
    successRate: stats.success_rate || 0,
    totalAgents: stats.total_agents || 0,
    totalSubtasks: stats.total_subtasks || 0,
  };
}

export function MyceliumCommandCenter({ standalone = false }: MyceliumCommandCenterProps) {
  // WebSocket connection status
  const { connected } = useMyceliumSocket();

  // DAG data state
  const [dagNodes, setDagNodes] = useState<DAGNode[]>([]);
  const [dagEdges, setDagEdges] = useState<DAGEdge[]>([]);
  const [stats, setStats] = useState<DAGStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // UI state
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [filters, setFilters] = useState<DAGFilters>({
    status: 'all',
    timeRange: '1h',
    type: 'all',
  });
  const [panelCollapsed, setPanelCollapsed] = useState(false);
  // MARKER_139.MCC_DAG_STREAM: Live pipeline output stream for DAG tab
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([]);

  // Track last update for debouncing
  const lastFetchRef = useRef<number>(0);
  const DEBOUNCE_MS = 500;
  const MAX_STREAM_EVENTS = 30;

  const pushStreamEvent = useCallback((event: Omit<StreamEvent, 'id' | 'ts'>) => {
    const next: StreamEvent = {
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      ts: Date.now(),
      role: event.role || 'pipeline',
      message: event.message || '',
      taskId: event.taskId,
    };
    setStreamEvents(prev => [next, ...prev].slice(0, MAX_STREAM_EVENTS));
  }, []);

  // Fetch DAG data from API
  const fetchDAG = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filters.status && filters.status !== 'all') {
        params.set('status', filters.status);
      }
      if (filters.timeRange) {
        params.set('time_range', filters.timeRange);
      }

      const res = await fetch(`${API_BASE}/dag?${params.toString()}`);

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();

      // Map backend response to frontend types
      const nodes = (data.nodes || []).map(mapBackendNode);
      const edges = (data.edges || []).map(mapBackendEdge);
      const mappedStats = mapBackendStats(data.stats || {});

      setDagNodes(nodes);
      setDagEdges(edges);
      setStats(mappedStats);
      setError(null);
    } catch (err) {
      // Fallback to test data if API unavailable
      console.warn('DAG API unavailable, using test data:', err);
      setDagNodes([]);
      setDagEdges([]);
      setStats({
        totalTasks: 0,
        runningTasks: 0,
        completedTasks: 0,
        failedTasks: 0,
        successRate: 0,
        totalAgents: 0,
        totalSubtasks: 0,
      });
      setError(null); // Don't show error, just use test data
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Fetch on mount and filter change
  useEffect(() => {
    fetchDAG();
  }, [fetchDAG]);

  // Listen for real-time updates from SocketIO/Mycelium bridge CustomEvents
  // MARKER_135.3A: task-board-updated triggers DAG refresh
  // MARKER_139.MCC_DAG_STREAM: Stream output panel fed by pipeline events
  useEffect(() => {
    const triggerFetch = () => {
      // Debounce rapid updates
      const now = Date.now();
      if (now - lastFetchRef.current < DEBOUNCE_MS) {
        return;
      }
      lastFetchRef.current = now;

      // Re-fetch DAG data
      fetchDAG();
    };

    const handleTaskBoardUpdate = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      const status = detail.status || detail.action || 'updated';
      const taskId = detail.task_id || detail.taskId;
      pushStreamEvent({
        role: 'board',
        message: taskId ? `${status} (${taskId})` : `${status}`,
        taskId,
      });
      triggerFetch();
    };

    const handlePipelineActivity = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      const role = detail.role || detail.agent || 'pipeline';
      const message = detail.message || detail.event || detail.status || 'activity';
      const taskId = detail.task_id || detail.taskId;
      pushStreamEvent({ role: String(role), message: String(message), taskId });
      triggerFetch();
    };

    const handlePipelineStats = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      const running = detail.running ?? detail.running_tasks;
      const done = detail.done ?? detail.completed_tasks;
      if (running !== undefined || done !== undefined) {
        pushStreamEvent({
          role: 'stats',
          message: `running=${running ?? 0} done=${done ?? 0}`,
        });
      }
      triggerFetch();
    };

    // Listen for task board changes (SocketIO and Mycelium WS both dispatch these CustomEvents)
    window.addEventListener('task-board-updated', handleTaskBoardUpdate as EventListener);
    window.addEventListener('pipeline-activity', handlePipelineActivity as EventListener);
    window.addEventListener('pipeline-stats', handlePipelineStats as EventListener);

    return () => {
      window.removeEventListener('task-board-updated', handleTaskBoardUpdate as EventListener);
      window.removeEventListener('pipeline-activity', handlePipelineActivity as EventListener);
      window.removeEventListener('pipeline-stats', handlePipelineStats as EventListener);
    };
  }, [fetchDAG, pushStreamEvent]);

  // Get selected node data
  const selectedNodeData = selectedNode
    ? dagNodes.find(n => n.id === selectedNode) || null
    : null;

  // MARKER_135.4D: Handle node actions (approve, reject, retry)
  const handleNodeAction = useCallback(async (action: string) => {
    if (!selectedNode) return;

    try {
      const res = await fetch(`${API_BASE}/dag/node/${selectedNode}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });

      if (!res.ok) {
        throw new Error(`Action failed: HTTP ${res.status}`);
      }

      const result = await res.json();
      console.log('[DAG] Action result:', result);

      // Refresh DAG after action
      fetchDAG();
    } catch (err) {
      console.error('[DAG] Action error:', err);
    }
  }, [selectedNode, fetchDAG]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: NOLAN_PALETTE.bg,
        fontFamily: 'monospace',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              color: NOLAN_PALETTE.textAccent,
              fontSize: 11,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: 2,
            }}
          >
            Mycelium DAG
          </div>
          {/* MARKER_135.3B: Live connection indicator */}
          <span
            style={{
              fontSize: 10,
              color: connected ? NOLAN_PALETTE.statusDone : NOLAN_PALETTE.statusFailed,
              opacity: 0.9,
            }}
          >
            {connected ? '● LIVE' : '○ OFFLINE'}
          </span>
        </div>

        {/* Stats summary */}
        {stats && (
          <div
            style={{
              display: 'flex',
              gap: 16,
              fontSize: 10,
              color: NOLAN_PALETTE.textNormal,
            }}
          >
            <span>tasks: {stats.totalTasks}</span>
            <span style={{ color: NOLAN_PALETTE.statusRunning }}>
              running: {stats.runningTasks}
            </span>
            <span style={{ color: NOLAN_PALETTE.statusDone }}>
              done: {stats.completedTasks}
            </span>
          </div>
        )}

        {/* Panel toggle */}
        <button
          onClick={() => setPanelCollapsed(!panelCollapsed)}
          style={{
            background: 'transparent',
            border: `1px solid ${NOLAN_PALETTE.borderDim}`,
            borderRadius: 3,
            padding: '4px 8px',
            color: NOLAN_PALETTE.textNormal,
            fontSize: 10,
            cursor: 'pointer',
          }}
        >
          {panelCollapsed ? 'Show Panel' : 'Hide Panel'}
        </button>
      </div>

      {/* Filter bar */}
      <FilterBar filters={filters} onChange={setFilters} />

      {/* MARKER_139.MCC_DAG_STREAM: Live pipeline output stream */}
      <div
        style={{
          borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
          background: '#0d0d0d',
          padding: '6px 10px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: 10,
            marginBottom: 6,
          }}
        >
          <span style={{ color: NOLAN_PALETTE.textDim, letterSpacing: 1, textTransform: 'uppercase' }}>
            live stream
          </span>
          <span style={{ color: NOLAN_PALETTE.textDim }}>
            {streamEvents.length > 0 ? `${streamEvents.length} events` : 'idle'}
          </span>
        </div>
        <div
          style={{
            maxHeight: 72,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 3,
            fontSize: 10,
            fontFamily: 'monospace',
          }}
        >
          {streamEvents.length === 0 ? (
            <span style={{ color: NOLAN_PALETTE.textDim }}>Waiting for pipeline events...</span>
          ) : streamEvents.slice(0, 8).map((event) => (
            <div key={event.id} style={{ display: 'flex', gap: 8 }}>
              <span style={{ color: '#666', minWidth: 54 }}>
                {new Date(event.ts).toLocaleTimeString()}
              </span>
              <span style={{ color: '#888', minWidth: 62, textTransform: 'uppercase' }}>
                {event.role}
              </span>
              <span
                style={{
                  color: '#cfcfcf',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  flex: 1,
                }}
                title={event.message}
              >
                {event.message}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div
        style={{
          display: 'flex',
          flex: 1,
          minHeight: 0,
        }}
      >
        {/* DAG View */}
        <div
          style={{
            flex: panelCollapsed ? 1 : 0.8,
            minWidth: 0,
            transition: 'flex 0.2s ease',
          }}
        >
          {loading ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: NOLAN_PALETTE.textDim,
                fontSize: 12,
              }}
            >
              Loading DAG...
            </div>
          ) : error ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: NOLAN_PALETTE.statusFailed,
                fontSize: 12,
              }}
            >
              Error: {error}
            </div>
          ) : (
            <DAGView
              dagNodes={dagNodes.length > 0 ? dagNodes : undefined}
              dagEdges={dagEdges.length > 0 ? dagEdges : undefined}
              selectedNode={selectedNode}
              onNodeSelect={setSelectedNode}
            />
          )}
        </div>

        {/* Detail Panel */}
        {!panelCollapsed && (
          <div
            style={{
              flex: 0.2,
              minWidth: 200,
              maxWidth: 300,
              borderLeft: `1px solid ${NOLAN_PALETTE.borderDim}`,
            }}
          >
            <DetailPanel
              node={selectedNodeData}
              stats={stats}
              onAction={handleNodeAction}
            />
          </div>
        )}
      </div>
    </div>
  );
}
