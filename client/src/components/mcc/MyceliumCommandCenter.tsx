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
import { HeartbeatChip } from './HeartbeatChip';
import { SandboxDropdown } from './SandboxDropdown';
import { KeyDropdown } from './KeyDropdown';
import { WorkflowToolbar } from './WorkflowToolbar';
import { DAGContextMenu, type ContextMenuTarget } from './DAGContextMenu';
import { NodePicker } from './NodePicker';
import { OnboardingOverlay } from './OnboardingOverlay';
import { OnboardingModal } from './OnboardingModal';
import { MCCBreadcrumb } from './MCCBreadcrumb';
import { useMCCStore } from '../../store/useMCCStore';
import { useOnboarding } from '../../hooks/useOnboarding';
import { useLimitedTooltip } from '../../hooks/useLimitedTooltip';
import { useRoadmapDAG } from '../../hooks/useRoadmapDAG';
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
  const summary = useMCCStore(s => s.summary);
  const executeWorkflow = useMCCStore(s => s.executeWorkflow);

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
  const [executing, setExecuting] = useState(false);
  const [executeMsg, setExecuteMsg] = useState<string | null>(null);
  const { step: onboardingStep, completed: onboardingCompleted, dismissed: onboardingDismissed, advance: onboardingAdvance, dismiss: onboardingDismiss } = useOnboarding();

  // MARKER_144.6: Edit mode + context menu
  const editMode = useMCCStore(s => s.editMode);
  const toggleEditMode = useMCCStore(s => s.toggleEditMode);
  const [contextMenuTarget, setContextMenuTarget] = useState<ContextMenuTarget | null>(null);
  const [nodePickerPos, setNodePickerPos] = useState<{ x: number; y: number } | null>(null);

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

  // MARKER_153.1C: Initialize MCC — load project config + session state on mount
  const initMCC = useMCCStore(s => s.initMCC);
  const hasProject = useMCCStore(s => s.hasProject);
  const navLevel = useMCCStore(s => s.navLevel);
  const drillDown = useMCCStore(s => s.drillDown);
  const goBack = useMCCStore(s => s.goBack);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [mccReady, setMccReady] = useState(false);

  // MARKER_153.5B: Roadmap DAG data hook
  const roadmap = useRoadmapDAG();

  useEffect(() => {
    initMCC().then(() => {
      setMccReady(true);
    });
  }, [initMCC]);

  // MARKER_153.5B: Fetch roadmap when MCC is ready and project exists
  useEffect(() => {
    if (mccReady && hasProject) {
      roadmap.fetchRoadmap();
    }
  }, [mccReady, hasProject]);

  // MARKER_153.3B: Show onboarding modal when no project configured
  useEffect(() => {
    if (mccReady && !hasProject) {
      setShowOnboarding(true);
    }
  }, [mccReady, hasProject]);

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

  // MARKER_153.5F: Level-aware effective nodes/edges
  // At roadmap level → show roadmap DAG. At workflow/running → show workflow DAG.
  const { effectiveNodes, effectiveEdges } = useMemo(() => {
    if (navLevel === 'roadmap' && roadmap.nodes.length > 0) {
      return { effectiveNodes: roadmap.nodes, effectiveEdges: roadmap.edges };
    }
    // Workflow / tasks / running / results levels — use workflow DAG data
    if (dagNodes.length > 0) {
      return { effectiveNodes: dagNodes, effectiveEdges: dagEdges };
    }
    // Fallback: test DAG data when nothing loaded
    const testData = createTestDAGData();
    return { effectiveNodes: testData.nodes, effectiveEdges: testData.edges };
  }, [navLevel, roadmap.nodes, roadmap.edges, dagNodes, dagEdges]);

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
    setNodePickerPos(null);
    if (target.kind === 'canvas') {
      setContextMenuTarget({ kind: 'canvas', position: target.position });
    } else if (target.kind === 'node' && target.id) {
      setContextMenuTarget({ kind: 'node', nodeId: target.id, position: target.position });
    } else if (target.kind === 'edge' && target.id) {
      setContextMenuTarget({ kind: 'edge', edgeId: target.id, position: target.position });
    }
  }, []);

  const handlePaneDoubleClick = useCallback((position: { x: number; y: number }) => {
    if (!editMode) return;
    setContextMenuTarget(null);
    setNodePickerPos(position);
  }, [editMode]);

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

  // MARKER_153.5C: Global keyboard shortcuts — Esc=goBack, Enter=drillDown
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      // Skip when typing in inputs
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (e.key === 'Escape') {
        e.preventDefault();
        goBack();
      }
      if (e.key === 'Enter' && navLevel === 'roadmap' && selectedNode) {
        e.preventDefault();
        handleRoadmapNodeDrill(selectedNode);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [goBack, navLevel, selectedNode]);

  // MARKER_153.5D: Handle roadmap node click → drill into tasks level
  const handleRoadmapNodeDrill = useCallback((nodeId: string) => {
    drillDown('tasks', { roadmapNodeId: nodeId });
  }, [drillDown]);

  // MARKER_153.5E: Handle node click based on current level
  const handleLevelAwareNodeSelect = useCallback((nodeId: string | null) => {
    setSelectedNode(nodeId);
  }, []);

  const handleLevelAwareNodeDoubleClick = useCallback((nodeId: string) => {
    if (navLevel === 'roadmap') {
      handleRoadmapNodeDrill(nodeId);
    }
    // Other levels: workflow level uses existing DAG editor behavior
  }, [navLevel, handleRoadmapNodeDrill]);

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

  // MARKER_151.7B: Stream panel auto-visibility follows running tasks.
  const runningCount = summary?.by_status?.running ?? stats?.runningTasks ?? 0;
  useEffect(() => {
    setShowStream(runningCount > 0);
  }, [runningCount]);

  // MARKER_151.5C: Header execute action (save first, then execute workflow).
  const handleExecute = useCallback(async () => {
    setExecuteMsg(null);
    const currentWorkflowId = dagEditor.workflowId;
    if (!currentWorkflowId && !dagEditor.isDirty) {
      setExecuteMsg('save workflow first');
      return;
    }

    setExecuting(true);
    try {
      // MARKER_151.18A: Auto-create sandbox on first execute when none exists.
      try {
        const listRes = await fetch('http://localhost:5001/api/debug/playground');
        if (listRes.ok) {
          const listData = await listRes.json();
          const playgrounds = Array.isArray(listData.playgrounds) ? listData.playgrounds : [];
          if (playgrounds.length === 0) {
            await fetch('http://localhost:5001/api/debug/playground/create', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                task: `vetka-workspace-${Date.now()}`,
                preset: 'dragon_silver',
                auto_write: true,
              }),
            });
            setExecuteMsg('created sandbox');
          }
        }
      } catch {
        // Non-blocking: execute can proceed even if sandbox bootstrap failed.
      }

      const wfId = dagEditor.isDirty
        ? await dagEditor.save(dagEditor.workflowName)
        : currentWorkflowId;

      if (!wfId) {
        setExecuteMsg('save failed');
        return;
      }

      const result = await executeWorkflow(wfId);
      if (result.success) {
        setExecuteMsg(`ok: ${result.count || 0} tasks`);
      } else {
        setExecuteMsg(`fail: ${result.error || 'unknown'}`);
      }
    } catch {
      setExecuteMsg('execute error');
    } finally {
      setExecuting(false);
    }
  }, [dagEditor, executeWorkflow]);

  const ttTeam = useLimitedTooltip('mcc_team', 'Select AI team preset (Dragon Bronze/Silver/Gold)');
  const ttSandbox = useLimitedTooltip('mcc_sandbox', 'Choose working directory for agent file writes');
  const ttHeartbeat = useLimitedTooltip('mcc_heartbeat', 'Set automatic task polling interval');
  const ttKey = useLimitedTooltip('mcc_key', 'Select API key and view remaining balance');
  const ttStats = useLimitedTooltip('mcc_stats', 'pending / running / done tasks');
  const ttExecute = useLimitedTooltip('mcc_execute', 'Run current workflow or dispatch next task');

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
      {/* ═══ HEADER / MARKER_151.5_UNIFIED_BAR ═══ */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '6px 10px',
          borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            color: NOLAN_PALETTE.textAccent,
            fontSize: 10,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: 2,
          }}
        >
          MCC
        </div>

        <div data-onboarding="team-dropdown" onMouseEnter={ttTeam.onMouseEnter} title={ttTeam.title}>
          <PresetDropdown />
        </div>
        <div data-onboarding="sandbox-dropdown" onMouseEnter={ttSandbox.onMouseEnter} title={ttSandbox.title}>
          <SandboxDropdown />
        </div>
        <div onMouseEnter={ttHeartbeat.onMouseEnter} title={ttHeartbeat.title}>
          <HeartbeatChip />
        </div>
        <div data-onboarding="key-dropdown" onMouseEnter={ttKey.onMouseEnter} title={ttKey.title}>
          <KeyDropdown />
        </div>

        <div style={{ flex: 1 }} />

        <span
          style={{
            fontSize: 9,
            color: connected ? NOLAN_PALETTE.statusDone : NOLAN_PALETTE.statusFailed,
            opacity: 0.9,
          }}
        >
          {connected ? '● LIVE' : '○ OFF'}
        </span>

        <div
          style={{ display: 'flex', gap: 7, fontSize: 9, color: NOLAN_PALETTE.textNormal }}
          onMouseEnter={ttStats.onMouseEnter}
          title={ttStats.title}
        >
          <span>{summary?.by_status?.pending ?? stats?.totalTasks ?? 0}t</span>
          <span style={{ color: NOLAN_PALETTE.statusRunning }}>{runningCount}r</span>
          <span style={{ color: NOLAN_PALETTE.statusDone }}>{summary?.by_status?.done ?? stats?.completedTasks ?? 0}d</span>
        </div>

        {/* MARKER_152.W3B3: Execute disabled when nothing to execute */}
        {(() => {
          const canExecute = effectiveNodes.length > 0 || tasks.some(t => t.status === 'pending');
          const isDisabled = executing || !canExecute;
          return (
            <button
              onClick={!isDisabled ? handleExecute : undefined}
              data-onboarding="execute-button"
              style={{
                background: canExecute ? 'rgba(78,205,196,0.15)' : 'rgba(255,255,255,0.03)',
                border: canExecute ? '1px solid #4ecdc4' : `1px solid ${NOLAN_PALETTE.borderDim}`,
                borderRadius: 3,
                padding: '3px 9px',
                color: !canExecute ? '#555' : executing ? '#7aa7a5' : '#c6ffff',
                fontSize: 10,
                cursor: isDisabled ? (executing ? 'wait' : 'not-allowed') : 'pointer',
                fontFamily: 'monospace',
                fontWeight: 600,
                opacity: isDisabled ? 0.5 : 1,
              }}
              onMouseEnter={ttExecute.onMouseEnter}
              title={!canExecute ? 'Load or create a workflow first' : ttExecute.title}
            >
              {executing ? '...' : '▶ Execute'}
            </button>
          );
        })()}

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

        {executeMsg && (
          <span
            style={{
              fontSize: 8,
              color: executeMsg.startsWith('ok:') ? NOLAN_PALETTE.statusDone : NOLAN_PALETTE.statusFailed,
              marginLeft: 2,
            }}
            title={executeMsg}
          >
            {executeMsg}
          </span>
        )}
      </div>

      {/* ═══ MARKER_153.5A: Breadcrumb Bar — navigation path ═══ */}
      <MCCBreadcrumb />

      {/* ═══ MARKER_144.6: Workflow Toolbar — only at workflow/running levels ═══ */}
      {(navLevel === 'workflow' || navLevel === 'running' || navLevel === 'results' ||
        navLevel === 'tasks') && (
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
        nodeCount={effectiveNodes.length}
      />
      )}

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
            <MCCTaskList />
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

          {/* DAG View — level-aware rendering */}
          <div style={{ flex: 1, minHeight: 0 }}>
            {(loading || roadmap.loading) ? (
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
                {navLevel === 'roadmap' ? 'Loading Roadmap...' : 'Loading DAG...'}
              </div>
            ) : (
              <DAGView
                dagNodes={effectiveNodes}
                dagEdges={effectiveEdges}
                selectedNode={selectedNode}
                onNodeSelect={handleLevelAwareNodeSelect}
                onEdgeSelect={handleEdgeSelect}
                editMode={navLevel === 'roadmap' ? false : editMode}
                onConnect={navLevel === 'roadmap' ? undefined : dagEditor.handleConnect}
                onNodesDelete={navLevel === 'roadmap' ? undefined : (deletedNodes) => deletedNodes.forEach(n => dagEditor.removeNode(n.id))}
                onEdgesDelete={navLevel === 'roadmap' ? undefined : (deletedEdges) => deletedEdges.forEach(e => dagEditor.removeEdge(e.id))}
                onContextMenu={navLevel === 'roadmap' ? undefined : handleContextMenu}
                onPaneDoubleClick={navLevel === 'roadmap'
                  ? undefined
                  : handlePaneDoubleClick
                }
                onNodeDoubleClick={handleLevelAwareNodeDoubleClick}
              />
            )}

            {/* MARKER_153.5G: Double-click hint at roadmap level */}
            {navLevel === 'roadmap' && effectiveNodes.length > 0 && selectedNode && (
              <div
                style={{
                  position: 'absolute',
                  bottom: showStream ? 110 : 10,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  background: 'rgba(0,0,0,0.85)',
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 4,
                  padding: '4px 12px',
                  fontSize: 9,
                  color: '#aaa',
                  fontFamily: 'monospace',
                  zIndex: 10,
                  pointerEvents: 'none',
                }}
              >
                Press <span style={{ color: NOLAN_PALETTE.textAccent, fontWeight: 600 }}>Enter</span> or double-click to drill into module
              </div>
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

      {editMode && (
        <NodePicker
          position={nodePickerPos}
          onClose={() => setNodePickerPos(null)}
          onSelect={(type, position) => {
            dagEditor.addNode(type, position);
            setNodePickerPos(null);
          }}
        />
      )}

      {!onboardingCompleted && !onboardingDismissed && (
        <OnboardingOverlay
          step={onboardingStep}
          onAdvance={onboardingAdvance}
          onDismiss={onboardingDismiss}
        />
      )}

      {/* MARKER_153.3B: Project setup wizard — shows when no project configured */}
      {showOnboarding && (
        <OnboardingModal onComplete={() => setShowOnboarding(false)} />
      )}
    </div>
  );
}
