/**
 * MARKER_143.P2: Mycelium Command Center — unified three-column workspace.
 * Merges Board + DAG + Stream + Artifacts into ONE view.
 * Layout: Left (tasks) | Center (DAG + stream) | Right (detail panel)
 *
 * Replaces the old two-panel DAG-only layout from Phase 137.
 *
 * @phase 143
 * @status active
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { DAGView } from './DAGView';
import { MCCTaskList } from './MCCTaskList';
import { MCCDetailPanel } from './MCCDetailPanel';
import { PresetDropdown } from './PresetDropdown';
import { StreamPanel } from './StreamPanel';
import { WatcherMicroStatus } from './WatcherMicroStatus';
import { WorkflowToolbar } from './WorkflowToolbar';
import { DAGContextMenu, type ContextMenuTarget } from './DAGContextMenu';
import { useMCCStore } from '../../store/useMCCStore';
import { NOLAN_PALETTE, createTestDAGData } from '../../utils/dagLayout';
import { useMyceliumSocket } from '../../hooks/useMyceliumSocket';
import { useDAGEditor } from '../../hooks/useDAGEditor';
import type { DAGNode, DAGEdge, DAGStats, DAGNodeType, EdgeType } from '../../types/dag';

const API_BASE = 'http://localhost:5001/api';

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

export function MyceliumCommandCenter() {
  // WebSocket connection status
  const { connected } = useMyceliumSocket();

  // MCC store state
  const selectedTaskId = useMCCStore(s => s.selectedTaskId);
  const selectTask = useMCCStore(s => s.selectTask);
  const pushStreamEvent = useMCCStore(s => s.pushStreamEvent);
  const tasks = useMCCStore(s => s.tasks);

  // DAG data state
  const [dagNodes, setDagNodes] = useState<DAGNode[]>([]);
  const [dagEdges, setDagEdges] = useState<DAGEdge[]>([]);
  const [stats, setStats] = useState<DAGStats | null>(null);
  const [loading, setLoading] = useState(true);

  // UI state
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<{
    id: string; source: string; target: string; type: string;
  } | null>(null);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [showStream, setShowStream] = useState(true);

  // MARKER_144.6: Edit mode + context menu
  const editMode = useMCCStore(s => s.editMode);
  const toggleEditMode = useMCCStore(s => s.toggleEditMode);
  const [contextMenuTarget, setContextMenuTarget] = useState<ContextMenuTarget | null>(null);

  // MARKER_144.11: Artifact viewer state — when user clicks artifact from node stream
  const [viewingArtifact, setViewingArtifact] = useState<{
    id: string; name: string; file_path: string; language: string;
  } | null>(null);
  const [artifactContent, setArtifactContent] = useState<string>('');

  const handleViewArtifact = useCallback((artifact: { id: string; name: string; file_path: string; language: string }) => {
    setViewingArtifact(artifact);
    // Fetch artifact content
    fetch(`http://localhost:5001/api/artifacts/${encodeURIComponent(artifact.id)}/content`)
      .then(r => r.json())
      .then(data => {
        setArtifactContent(data.content || data.text || '');
      })
      .catch(() => setArtifactContent('(failed to load artifact content)'));
  }, []);

  // Track last update for debouncing
  const lastFetchRef = useRef<number>(0);
  const DEBOUNCE_MS = 500;

  // MARKER_143.P3: Fetch DAG data — filtered by selectedTaskId when set
  const fetchDAG = useCallback(async (taskId?: string | null) => {
    try {
      const url = taskId
        ? `${API_BASE}/dag?task_id=${encodeURIComponent(taskId)}`
        : `${API_BASE}/dag`;
      const res = await fetch(url);

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      const nodes = (data.nodes || []).map(mapBackendNode);
      const edges = (data.edges || []).map(mapBackendEdge);
      const mappedStats = mapBackendStats(data.stats || {});

      setDagNodes(nodes);
      setDagEdges(edges);
      setStats(mappedStats);
    } catch (err) {
      console.warn('DAG API unavailable:', err);
      setDagNodes([]);
      setDagEdges([]);
      setStats({
        totalTasks: 0, runningTasks: 0, completedTasks: 0,
        failedTasks: 0, successRate: 0, totalAgents: 0, totalSubtasks: 0,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // MARKER_143.P3: Refetch DAG when selectedTaskId changes
  useEffect(() => {
    fetchDAG(selectedTaskId);
  }, [selectedTaskId, fetchDAG]);

  // Listen for real-time updates via CustomEvents
  useEffect(() => {
    const triggerFetch = () => {
      const now = Date.now();
      if (now - lastFetchRef.current < DEBOUNCE_MS) return;
      lastFetchRef.current = now;
      fetchDAG(selectedTaskId);
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

    window.addEventListener('task-board-updated', handleTaskBoardUpdate as EventListener);
    window.addEventListener('pipeline-activity', handlePipelineActivity as EventListener);
    window.addEventListener('pipeline-stats', handlePipelineStats as EventListener);

    return () => {
      window.removeEventListener('task-board-updated', handleTaskBoardUpdate as EventListener);
      window.removeEventListener('pipeline-activity', handlePipelineActivity as EventListener);
      window.removeEventListener('pipeline-stats', handlePipelineStats as EventListener);
    };
  }, [fetchDAG, pushStreamEvent, selectedTaskId]);

  // MARKER_143.P4C: Effective nodes/edges — use test data when API returns empty
  // This ensures selectedNodeData can find clicked nodes even with test DAG.
  const { effectiveNodes, effectiveEdges } = useMemo(() => {
    if (dagNodes.length > 0) {
      return { effectiveNodes: dagNodes, effectiveEdges: dagEdges };
    }
    const testData = createTestDAGData();
    return { effectiveNodes: testData.nodes, effectiveEdges: testData.edges };
  }, [dagNodes, dagEdges]);

  // MARKER_144.2: DAG Editor hook — manages workflow editing state
  // Uses effectiveNodes/effectiveEdges as initial data, provides mutators
  const dagEditor = useDAGEditor(
    effectiveNodes,
    effectiveEdges,
    (updater) => {
      if (typeof updater === 'function') {
        setDagNodes(prev => {
          const effective = prev.length > 0 ? prev : createTestDAGData().nodes;
          return updater(effective);
        });
      } else {
        setDagNodes(updater);
      }
    },
    (updater) => {
      if (typeof updater === 'function') {
        setDagEdges(prev => {
          const effective = prev.length > 0 ? prev : createTestDAGData().edges;
          return updater(effective);
        });
      } else {
        setDagEdges(updater);
      }
    },
  );

  // MARKER_144.3: Context menu handlers
  const handleContextMenu = useCallback((_event: React.MouseEvent, target: { kind: 'canvas' | 'node' | 'edge'; id?: string; position: { x: number; y: number } }) => {
    if (target.kind === 'canvas') {
      setContextMenuTarget({ kind: 'canvas', position: target.position });
    } else if (target.kind === 'node' && target.id) {
      setContextMenuTarget({ kind: 'node', nodeId: target.id, position: target.position });
    } else if (target.kind === 'edge' && target.id) {
      setContextMenuTarget({ kind: 'edge', edgeId: target.id, position: target.position });
    }
  }, []);

  const handleAddNodeFromMenu = useCallback((type: DAGNodeType, position: { x: number; y: number }) => {
    dagEditor.addNode(type, position);
  }, [dagEditor]);

  const handleDuplicateNode = useCallback((nodeId: string) => {
    const node = effectiveNodes.find(n => n.id === nodeId);
    if (node) {
      dagEditor.addNode(node.type, { x: 50, y: 50 }, `${node.label} (copy)`);
    }
  }, [dagEditor, effectiveNodes]);

  // MARKER_144.6: Keyboard shortcuts for edit mode (Ctrl+Z, Ctrl+Shift+Z)
  useEffect(() => {
    if (!editMode) return;
    const handleKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        dagEditor.undo();
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        dagEditor.redo();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [editMode, dagEditor]);

  // Selected node data for detail panel
  const selectedNodeData = useMemo(() => {
    if (!selectedNode) return null;
    return effectiveNodes.find(n => n.id === selectedNode) || null;
  }, [selectedNode, effectiveNodes]);

  // Selected edge data
  const selectedEdgeData = useMemo(() => {
    if (!selectedEdge) return null;
    const e = effectiveEdges.find(e => e.id === selectedEdge.id);
    return e ? { id: e.id, source: e.source, target: e.target, type: e.type } : null;
  }, [selectedEdge, effectiveEdges]);

  // Handle edge selection
  const handleEdgeSelect = useCallback((edgeId: string | null) => {
    if (!edgeId) {
      setSelectedEdge(null);
      return;
    }
    const edge = dagEdges.find(e => e.id === edgeId);
    if (edge) {
      setSelectedEdge({ id: edge.id, source: edge.source, target: edge.target, type: edge.type });
    }
  }, [dagEdges]);

  // Handle node actions
  const handleNodeAction = useCallback(async (action: string) => {
    if (!selectedNode) return;
    try {
      const res = await fetch(`${API_BASE}/dag/node/${selectedNode}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      if (res.ok) fetchDAG(selectedTaskId);
    } catch (err) {
      console.error('[DAG] Action error:', err);
    }
  }, [selectedNode, fetchDAG, selectedTaskId]);

  // MARKER_144.7: Handle generated workflow — load into DAG editor
  const handleGeneratedWorkflow = useCallback(async (workflow: any) => {
    if (!workflow?.nodes?.length) return;
    if (!editMode) toggleEditMode();

    // Save the generated workflow first, then load it via dagEditor.load
    try {
      const res = await fetch(`${API_BASE}/workflows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflow),
      });
      const data = await res.json();
      if (data.success && data.id) {
        await dagEditor.load(data.id);
        pushStreamEvent({
          role: 'architect',
          message: `Generated workflow loaded: ${workflow.name || 'Untitled'} (${workflow.nodes.length} nodes)`,
        });
      }
    } catch (err) {
      console.error('[MCC] Failed to save generated workflow:', err);
    }
  }, [editMode, toggleEditMode, dagEditor, pushStreamEvent]);

  // MARKER_144.7: Handle Architect-proposed DAG changes (from ArchitectChat)
  const handleAcceptArchitectChanges = useCallback((changes: {
    addNodes?: Array<{ type: string; label: string }>;
    removeNodes?: string[];
    addEdges?: Array<{ source: string; target: string; type: string }>;
  }) => {
    if (!editMode) {
      // Auto-enter edit mode when accepting changes
      toggleEditMode();
    }
    // Add proposed nodes
    if (changes.addNodes) {
      const startY = effectiveNodes.length * 120;
      changes.addNodes.forEach((node, i) => {
        dagEditor.addNode(
          (node.type as DAGNodeType) || 'task',
          { x: 200, y: startY + i * 120 },
          node.label,
        );
      });
    }
    // Remove proposed nodes
    if (changes.removeNodes) {
      changes.removeNodes.forEach(id => dagEditor.removeNode(id));
    }
    // Add proposed edges
    if (changes.addEdges) {
      changes.addEdges.forEach(edge => {
        dagEditor.addEdge(edge.source, edge.target, (edge.type || 'structural') as EdgeType);
      });
    }
    pushStreamEvent({
      role: 'architect',
      message: `DAG changes applied: +${changes.addNodes?.length || 0} nodes, +${changes.addEdges?.length || 0} edges`,
    });
  }, [editMode, toggleEditMode, effectiveNodes, dagEditor, pushStreamEvent]);

  // MARKER_143.P3: Get selected task title for breadcrumb
  const selectedTaskTitle = useMemo(() => {
    if (!selectedTaskId) return null;
    const t = tasks.find(t => t.id === selectedTaskId);
    return t?.title || selectedTaskId.slice(0, 12);
  }, [selectedTaskId, tasks]);

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
      {/* ═══ HEADER ═══ */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '5px 10px',
          borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
          flexShrink: 0,
        }}
      >
        {/* Left: title + preset dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              color: NOLAN_PALETTE.textAccent,
              fontSize: 10,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: 2,
            }}
          >
            MCC
          </div>

          <PresetDropdown />

          <span
            style={{
              fontSize: 9,
              color: connected ? NOLAN_PALETTE.statusDone : NOLAN_PALETTE.statusFailed,
              opacity: 0.9,
            }}
          >
            {connected ? '● LIVE' : '○ OFF'}
          </span>
        </div>

        {/* Right: watcher + stats + panel toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <WatcherMicroStatus />

          {stats && (
            <div style={{ display: 'flex', gap: 8, fontSize: 9, color: NOLAN_PALETTE.textNormal }}>
              <span>{stats.totalTasks}t</span>
              <span style={{ color: NOLAN_PALETTE.statusRunning }}>{stats.runningTasks}r</span>
              <span style={{ color: NOLAN_PALETTE.statusDone }}>{stats.completedTasks}d</span>
            </div>
          )}

          {/* Stream toggle */}
          <button
            onClick={() => setShowStream(!showStream)}
            style={{
              background: showStream ? 'rgba(255,255,255,0.06)' : 'transparent',
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 2,
              padding: '2px 6px',
              color: showStream ? NOLAN_PALETTE.text : NOLAN_PALETTE.textDim,
              fontSize: 8,
              cursor: 'pointer',
              fontFamily: 'monospace',
            }}
            title="Toggle live stream"
          >
            stream
          </button>

          {/* Left panel toggle */}
          <button
            onClick={() => setLeftCollapsed(!leftCollapsed)}
            style={{
              background: 'transparent',
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 2,
              padding: '2px 6px',
              color: NOLAN_PALETTE.textNormal,
              fontSize: 8,
              cursor: 'pointer',
              fontFamily: 'monospace',
            }}
            title="Toggle tasks panel [["
          >
            {leftCollapsed ? '▶' : '◀'}
          </button>

          {/* Right panel toggle */}
          <button
            onClick={() => setRightCollapsed(!rightCollapsed)}
            style={{
              background: 'transparent',
              border: `1px solid ${NOLAN_PALETTE.borderDim}`,
              borderRadius: 2,
              padding: '2px 6px',
              color: NOLAN_PALETTE.textNormal,
              fontSize: 8,
              cursor: 'pointer',
              fontFamily: 'monospace',
            }}
            title="Toggle detail panel ]"
          >
            {rightCollapsed ? '◀' : '▶'}
          </button>
        </div>
      </div>

      {/* ═══ MARKER_144.6: Workflow Toolbar — only renders controls when editMode=true ═══ */}
      <WorkflowToolbar
        workflowId={dagEditor.workflowId}
        workflowName={dagEditor.workflowName}
        isDirty={dagEditor.isDirty}
        canUndo={dagEditor.canUndo}
        canRedo={dagEditor.canRedo}
        onNew={dagEditor.newWorkflow}
        onSave={dagEditor.save}
        onLoad={dagEditor.load}
        onListWorkflows={dagEditor.listWorkflows}
        onValidate={dagEditor.validate}
        onUndo={dagEditor.undo}
        onRedo={dagEditor.redo}
        onSetName={dagEditor.setWorkflowName}
        onToggleEdit={toggleEditMode}
        editMode={editMode}
        onGenerate={handleGeneratedWorkflow}
        onImport={handleGeneratedWorkflow}
      />

      {/* ═══ MAIN THREE-COLUMN LAYOUT ═══ */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* LEFT COLUMN: Task List (220px) */}
        {!leftCollapsed && (
          <div
            style={{
              width: 220,
              flexShrink: 0,
              minHeight: 0,
            }}
          >
            <MCCTaskList onAcceptArchitectChanges={handleAcceptArchitectChanges} />
          </div>
        )}

        {/* CENTER COLUMN: DAG + Stream */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            minWidth: 0,
            minHeight: 0,
          }}
        >
          {/* MARKER_143.P3: Task breadcrumb — shows when filtered by task */}
          {selectedTaskId && selectedTaskTitle && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '3px 10px',
                background: 'rgba(255,255,255,0.03)',
                borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
                fontSize: 9,
                flexShrink: 0,
              }}
            >
              <span style={{ color: '#555' }}>Task:</span>
              <span style={{ color: '#ccc', fontWeight: 600 }}>{selectedTaskTitle}</span>
              <button
                onClick={() => selectTask(null)}
                style={{
                  background: 'transparent',
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 2,
                  color: '#888',
                  fontSize: 8,
                  padding: '0px 4px',
                  cursor: 'pointer',
                  fontFamily: 'monospace',
                  marginLeft: 'auto',
                }}
                title="Show all tasks"
              >
                show all
              </button>
            </div>
          )}

          {/* DAG View */}
          <div style={{ flex: 1, minHeight: 0 }}>
            {loading ? (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: NOLAN_PALETTE.textDim,
                  fontSize: 11,
                }}
              >
                Loading DAG...
              </div>
            ) : (
              <DAGView
                dagNodes={effectiveNodes}
                dagEdges={effectiveEdges}
                selectedNode={selectedNode}
                onNodeSelect={setSelectedNode}
                onEdgeSelect={handleEdgeSelect}
                editMode={editMode}
                onConnect={dagEditor.handleConnect}
                onNodesDelete={(deletedNodes) => deletedNodes.forEach(n => dagEditor.removeNode(n.id))}
                onEdgesDelete={(deletedEdges) => deletedEdges.forEach(e => dagEditor.removeEdge(e.id))}
                onContextMenu={handleContextMenu}
              />
            )}
          </div>

          {/* Stream Panel — collapsible bottom */}
          {showStream && <StreamPanel maxEvents={8} />}
        </div>

        {/* RIGHT COLUMN: Detail Panel (240px) */}
        {!rightCollapsed && (
          <div
            style={{
              width: 240,
              flexShrink: 0,
              borderLeft: `1px solid ${NOLAN_PALETTE.borderDim}`,
              minHeight: 0,
            }}
          >
            <MCCDetailPanel
              selectedDagNode={selectedNodeData}
              selectedEdge={selectedEdgeData}
              stats={stats}
              onNodeAction={handleNodeAction}
              editMode={editMode}
              onUpdateNodeData={dagEditor.updateNodeData}
              onViewArtifact={handleViewArtifact}
            />
          </div>
        )}
      </div>

      {/* ═══ MARKER_144.11: Artifact Viewer Overlay ═══ */}
      {viewingArtifact && (
        <div
          style={{
            position: 'absolute',
            top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.8)',
            zIndex: 200,
            display: 'flex',
            flexDirection: 'column',
          }}
          onClick={() => setViewingArtifact(null)}
        >
          <div
            style={{
              margin: '20px auto',
              width: '80%',
              maxWidth: 700,
              maxHeight: '80%',
              background: NOLAN_PALETTE.bg,
              border: `1px solid ${NOLAN_PALETTE.border}`,
              borderRadius: 4,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '8px 12px',
              borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
            }}>
              <div>
                <div style={{ fontSize: 11, color: NOLAN_PALETTE.text, fontWeight: 600 }}>
                  {viewingArtifact.name}
                </div>
                <div style={{ fontSize: 8, color: NOLAN_PALETTE.textDim, marginTop: 2 }}>
                  {viewingArtifact.language} · {viewingArtifact.file_path}
                </div>
              </div>
              <button
                onClick={() => setViewingArtifact(null)}
                style={{
                  background: 'transparent',
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 2,
                  color: NOLAN_PALETTE.textMuted,
                  padding: '2px 8px',
                  fontSize: 9,
                  cursor: 'pointer',
                  fontFamily: 'monospace',
                }}
              >
                close
              </button>
            </div>
            {/* Content */}
            <pre style={{
              flex: 1,
              overflowY: 'auto',
              padding: 12,
              margin: 0,
              fontSize: 10,
              color: '#bbb',
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              lineHeight: 1.5,
            }}>
              {artifactContent || 'Loading...'}
            </pre>
          </div>
        </div>
      )}

      {/* ═══ MARKER_144.3: Context Menu Overlay — only in edit mode ═══ */}
      {editMode && (
        <DAGContextMenu
          target={contextMenuTarget}
          onClose={() => setContextMenuTarget(null)}
          onAddNode={handleAddNodeFromMenu}
          onDeleteNode={dagEditor.removeNode}
          onDuplicateNode={handleDuplicateNode}
          onDeleteEdge={dagEditor.removeEdge}
        />
      )}
    </div>
  );
}
