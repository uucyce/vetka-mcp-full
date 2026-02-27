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
import { DAGView, type LODLevel, type DAGViewRef } from './DAGView';
import { ReactFlowProvider } from '@xyflow/react';
// MARKER_155.CLEANUP: Removed deprecated components - using Mini-windows instead
// import { MCCTaskList } from './MCCTaskList';
// import { MCCDetailPanel } from './MCCDetailPanel';
// import { PresetDropdown } from './PresetDropdown';
// import { HeartbeatChip } from './HeartbeatChip';
// import { SandboxDropdown } from './SandboxDropdown';
// import { KeyDropdown } from './KeyDropdown';
// import { CaptainBar } from './CaptainBar';
import { StreamPanel } from './StreamPanel';
import { DAGContextMenu, type ContextMenuTarget } from './DAGContextMenu';
import { NodePicker } from './NodePicker';
import { OnboardingOverlay } from './OnboardingOverlay';
import { OnboardingModal } from './OnboardingModal';
import { MCCBreadcrumb } from './MCCBreadcrumb';
import { FooterActionBar } from './FooterActionBar';
import { MatryoshkaTransition } from './MatryoshkaTransition';
import { TaskEditPopup } from './TaskEditPopup';
import { RedoFeedbackInput } from './RedoFeedbackInput';
// MARKER_154.11A: Mini-windows replace side panels
import { MiniChat } from './MiniChat';
import { MiniTasks } from './MiniTasks';
import { MiniStats } from './MiniStats';
import { MiniBalance } from './MiniBalance';
import { StepIndicator } from './StepIndicator';
import { FirstRunView } from './FirstRunView';
import { PlaygroundBadge } from './PlaygroundBadge';
// MARKER_155.WIZARD.001: Wizard flow for steps 1-3
import { WizardContainer, type WizardStep } from './WizardContainer';
import { ToastContainer } from './ToastContainer';
import { useMCCStore } from '../../store/useMCCStore';
import { useStore } from '../../store/useStore';
import { useOnboarding } from '../../hooks/useOnboarding';
import { useRoadmapDAG } from '../../hooks/useRoadmapDAG';
import { useToast } from '../../hooks/useToast';
import { useCaptain } from '../../hooks/useCaptain';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';
import { NOLAN_PALETTE, createTestDAGData } from '../../utils/dagLayout';
import {
  fetchDagLayoutBiasProfile,
  type DagLayoutBiasProfile,
} from '../../utils/dagLayoutPreferences';
import { useMyceliumSocket } from '../../hooks/useMyceliumSocket';
import { useDAGEditor } from '../../hooks/useDAGEditor';
import type { DAGNode, DAGEdge, DAGStats, DAGNodeType, NodeStatus, EdgeType } from '../../types/dag';
import type { TaskData } from '../panels/TaskCard';

const API_BASE = 'http://localhost:5001/api';

interface PredictedEdgePayload {
  source: string;
  target: string;
  type?: string;
  weight?: number;
  confidence?: number;
  evidence?: string[];
}

interface DagVersionSummary {
  version_id: string;
  name: string;
  created_at: string;
  author: string;
  source: string;
  is_primary: boolean;
  node_count: number;
  edge_count: number;
  decision: string;
  markers: string[];
}

interface DagCompareRow {
  name: string;
  version_id?: string;
  variant_params?: {
    max_nodes?: number;
    min_confidence?: number;
    use_predictive_overlay?: boolean;
    max_predicted_edges?: number;
  };
  scorecard?: {
    score?: number;
    decision?: string;
    node_count?: number;
    edge_count?: number;
    orphan_rate?: number;
    density?: number;
  };
  error?: string;
}

type FocusDisplayMode = 'all' | 'selected_deps' | 'selected_only';
type FocusRestoreSource = 'current' | 'memory' | 'default';
type TaskDrillState = 'collapsed' | 'expanded';
type RoadmapNodeDrillState = 'collapsed' | 'expanded';

function uniqueIds(ids: Array<string | null | undefined>): string[] {
  return Array.from(new Set(ids.filter(Boolean) as string[]));
}

function sameIds(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

function normalizePathKey(value: string | null | undefined): string {
  return String(value || '')
    .trim()
    .replace(/\\/g, '/')
    .replace(/^\.\/+/, '')
    .replace(/\/+/g, '/')
    .toLowerCase();
}

function normalizeTaskOrigin(raw: string | null | undefined): 'architect' | 'chat' | 'manual' | 'system' {
  const v = String(raw || '').trim().toLowerCase();
  if (v.includes('architect')) return 'architect';
  if (v.includes('chat') || v.includes('doctor')) return 'chat';
  if (v.includes('system') || v.includes('auto')) return 'system';
  return 'manual';
}

function resolveTaskAnchorIds(task: TaskData, roadmapNodes: DAGNode[]): string[] {
  const idSet = new Set(roadmapNodes.map((n) => n.id));
  const lookup = new Map<string, string[]>();

  const addLookup = (key: string | null | undefined, nodeId: string) => {
    const normalized = normalizePathKey(key);
    if (!normalized) return;
    const prev = lookup.get(normalized) || [];
    if (!prev.includes(nodeId)) prev.push(nodeId);
    lookup.set(normalized, prev);
  };

  for (const node of roadmapNodes) {
    addLookup(node.id, node.id);
    addLookup(node.projectNodeId, node.id);
    addLookup(node.label, node.id);
    const meta: any = node.metadata || {};
    addLookup(meta.path, node.id);
    addLookup(meta.file_path, node.id);
  }

  const candidates = uniqueIds([
    task.primary_node_id,
    ...(Array.isArray(task.affected_nodes) ? task.affected_nodes : []),
    task.module,
  ]);

  const resolved: string[] = [];
  const append = (nodeId: string) => {
    if (!idSet.has(nodeId)) return;
    if (!resolved.includes(nodeId)) resolved.push(nodeId);
  };

  for (const candidate of candidates) {
    if (idSet.has(candidate)) {
      append(candidate);
      continue;
    }
    const key = normalizePathKey(candidate);
    if (!key) continue;
    const exact = lookup.get(key) || [];
    if (exact.length > 0) {
      exact.forEach(append);
      continue;
    }
    for (const [k, ids] of lookup.entries()) {
      if (k.endsWith(`/${key}`) || key.endsWith(`/${k}`)) {
        ids.forEach(append);
      }
      if (resolved.length >= 3) break;
    }
    if (resolved.length >= 3) break;
  }

  return resolved.slice(0, 3);
}

function inferSuggestedAnchorIds(task: TaskData, roadmapNodes: DAGNode[]): string[] {
  const title = String(task.title || '').toLowerCase();
  const description = String(task.description || '').toLowerCase();
  const stop = new Set(['fix', 'task', 'wire', 'update', 'with', 'from', 'into', 'for', 'and', 'the', 'api']);
  const tokens = Array.from(new Set(`${title} ${description}`
    .split(/[^a-z0-9_./-]+/g)
    .map((t) => t.trim())
    .filter((t) => t.length >= 4 && !stop.has(t))));
  if (tokens.length === 0) return [];

  let best: { id: string; score: number } | null = null;
  for (const node of roadmapNodes) {
    if (node.graphKind === 'project_root') continue;
    const meta: any = node.metadata || {};
    const hay = [
      String(node.id || ''),
      String(node.label || ''),
      String(node.projectNodeId || ''),
      String(meta.path || ''),
      String(meta.file_path || ''),
    ].join(' ').toLowerCase();
    const score = tokens.reduce((s, token) => s + (hay.includes(token) ? 1 : 0), 0);
    if (score <= 0) continue;
    if (!best || score > best.score) best = { id: node.id, score };
  }
  return best ? [best.id] : [];
}

function adaptVersionNode(raw: any): DAGNode {
  if (!raw || typeof raw !== 'object') {
    return {
      id: `invalid_${Math.random().toString(36).slice(2, 8)}`,
      type: 'roadmap_task',
      label: 'invalid',
      status: 'pending',
      layer: 0,
      taskId: 'invalid',
    };
  }
  if (raw.type && raw.status !== undefined) {
    return raw as DAGNode;
  }
  const kind = String(raw.kind || '');
  const graphKind =
    kind === 'root'
      ? 'project_root'
      : kind === 'folder'
        ? 'project_dir'
        : 'project_file';
  return {
    id: String(raw.id || `node_${Math.random().toString(36).slice(2, 8)}`),
    type: 'roadmap_task',
    label: String(raw.label || raw.id || 'node'),
    status: 'pending',
    layer: typeof raw.layer === 'number' ? raw.layer : 0,
    taskId: String(raw.id || 'node'),
    description: String(raw?.metadata?.parent || ''),
    graphKind: graphKind as any,
    projectNodeId: String(raw.id || 'node'),
    metadata: raw.metadata || {},
  };
}

function adaptVersionEdge(raw: any, idx: number): DAGEdge {
  const rawType = String(raw?.type || '').toLowerCase();
  const type: DAGEdge['type'] =
    rawType === 'structural'
      ? 'structural'
      : rawType === 'predicted'
        ? 'predicted'
        : rawType === 'dependency'
        ? 'dependency'
          : 'dependency';
  const rawRelation = String(
    raw?.relationKind || raw?.relation_kind || (type === 'structural' ? 'contains' : 'depends_on'),
  ).toLowerCase();
  const relationKind: NonNullable<DAGEdge['relationKind']> =
    rawRelation === 'contains'
      ? 'contains'
      : rawRelation === 'affects'
        ? 'affects'
        : rawRelation === 'executes'
          ? 'executes'
          : rawRelation === 'passes'
            ? 'passes'
            : rawRelation === 'produces'
              ? 'produces'
              : rawRelation === 'predicted'
                ? 'predicted'
                : 'depends_on';
  return {
    id: String(raw?.id || `v-e-${raw?.source || 's'}-${raw?.target || 't'}-${idx}`),
    source: String(raw?.source || ''),
    target: String(raw?.target || ''),
    type,
    strength: Math.max(0.25, Math.min(1.0, Number(raw?.strength ?? raw?.score ?? raw?.confidence ?? 0.8))),
    relationKind,
  };
}

// MARKER_155A.P1.ADAPTERS: Normalize backend graph payloads to MCC DAG types.
function normalizeNodeType(rawType: string | undefined): DAGNodeType {
  switch (rawType) {
    case 'task':
    case 'roadmap_task':
    case 'agent':
    case 'subtask':
    case 'proposal':
    case 'condition':
    case 'parallel':
    case 'loop':
    case 'transform':
    case 'group':
      return rawType;
    case 'project_task':
    case 'project_root':
    case 'project_dir':
    case 'project_file':
      return 'roadmap_task';
    case 'workflow_agent':
      return 'agent';
    case 'workflow_artifact':
      return 'subtask';
    case 'workflow_message':
      return 'proposal';
    default:
      return 'task';
  }
}

function normalizeEdgeType(rawType: string | undefined): EdgeType {
  switch (rawType) {
    case 'structural':
    case 'dataflow':
    case 'temporal':
    case 'conditional':
    case 'parallel_fork':
    case 'parallel_join':
    case 'feedback':
    case 'dependency':
    case 'predicted':
      return rawType;
    case 'depends_on':
      return 'dependency';
    case 'passes':
    case 'produces':
      return 'dataflow';
    case 'contains':
    case 'affects':
    case 'executes':
      return 'structural';
    default:
      return 'structural';
  }
}

function normalizeStatus(rawStatus: string | undefined): NodeStatus {
  switch (rawStatus) {
    case 'running':
    case 'pending':
    case 'done':
    case 'failed':
      return rawStatus;
    case 'active':
      return 'running';
    case 'completed':
      return 'done';
    case 'error':
      return 'failed';
    default:
      return 'pending';
  }
}

// Convert backend response to frontend types
function mapBackendNode(node: any): DAGNode {
  return {
    id: node.id,
    type: normalizeNodeType(node.type),
    label: node.label || node.id || 'node',
    status: normalizeStatus(node.status),
    layer: typeof node.layer === 'number' ? node.layer : 0,
    taskId: node.task_id || node.taskId || node.id,
    parentId: node.parent_id,
    startedAt: node.started_at,
    completedAt: node.completed_at,
    durationS: node.duration_s,
    tokens: node.tokens,
    model: node.model,
    confidence: node.confidence,
    role: node.role,
    description: node.description,
    // MARKER_155A.P1.GRAPH_SCHEMA: Preserve unified graph identifiers for LOD contract.
    graphKind: node.graph_kind || node.type,
    projectNodeId: node.project_node_id,
    workflowId: node.workflow_id,
    agentNodeId: node.agent_node_id,
    sourceMessageId: node.source_message_id,
    primaryNodeId: node.primary_node_id,
    affectedNodes: Array.isArray(node.affected_nodes) ? node.affected_nodes : undefined,
    integrationTaskOf: Array.isArray(node.integration_task_of) ? node.integration_task_of : undefined,
    taskOrigin: normalizeTaskOrigin(node.task_origin || node.source),
    teamProfile: String(node.team_profile || node.preset || ''),
  };
}

function mapBackendEdge(edge: any): DAGEdge {
  return {
    id: edge.id || `e-${edge.source}-${edge.target}`,
    source: edge.source,
    target: edge.target,
    type: normalizeEdgeType(edge.type),
    strength: typeof edge.strength === 'number' ? edge.strength : 0.8,
    relationKind: edge.relation_kind || edge.type,
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

// MARKER_155.3A: Convert TaskBoard tasks → clean 3-level tree DAG.
// Tree: Module root → phase_type branches (Build/Fix/Research) → task leaves.
// No chunking, no tag grouping. Simple and readable.
function tasksToDAG(
  tasks: TaskData[],
  options?: { moduleId?: string; moduleLabel?: string },
): { nodes: DAGNode[]; edges: DAGEdge[] } {
  const mapStatus = (s: string): NodeStatus => {
    if (s === 'running' || s === 'claimed') return 'running';
    if (s === 'done') return 'done';
    if (s === 'failed' || s === 'cancelled') return 'failed';
    return 'pending';
  };

  const aggregateStatus = (items: TaskData[]): NodeStatus => {
    if (items.some(t => t.status === 'running' || t.status === 'claimed')) return 'running';
    if (items.every(t => t.status === 'done')) return 'done';
    if (items.some(t => t.status === 'failed' || t.status === 'cancelled')) return 'failed';
    return 'pending';
  };

  const PHASE_LABELS: Record<string, string> = {
    build: 'Build', fix: 'Fix', research: 'Research',
  };

  const nodes: DAGNode[] = [];
  const edges: DAGEdge[] = [];

  // --- Root node (module name or "Tasks") ---
  const rootId = '__root__';
  nodes.push({
    id: rootId, type: 'task' as DAGNodeType,
    label: options?.moduleLabel || `Tasks (${tasks.length})`,
    status: aggregateStatus(tasks),
    layer: 0, taskId: rootId,
  });

  // --- Group tasks by phase_type ---
  const groups = new Map<string, TaskData[]>();
  for (const task of tasks) {
    const phase = task.phase_type || 'build';
    if (!groups.has(phase)) groups.set(phase, []);
    groups.get(phase)!.push(task);
  }

  // Sort: largest group first
  const sorted = [...groups.entries()].sort((a, b) => b[1].length - a[1].length);

  for (const [phase, phaseTasks] of sorted) {
    const branchId = `__phase_${phase}__`;
    const branchLabel = PHASE_LABELS[phase] || phase.charAt(0).toUpperCase() + phase.slice(1);

    // Branch node
    nodes.push({
      id: branchId, type: 'task' as DAGNodeType,
      label: `${branchLabel} (${phaseTasks.length})`,
      status: aggregateStatus(phaseTasks),
      layer: 1, taskId: branchId,
    });
    edges.push({
      id: `e-root-${phase}`, source: rootId, target: branchId,
      type: 'structural' as EdgeType, strength: 0.9,
    });

    // Task leaf nodes
    for (const task of phaseTasks) {
      nodes.push({
      id: task.id, type: 'roadmap_task' as DAGNodeType,
        label: task.title, status: mapStatus(task.status),
        layer: 2, taskId: task.id,
        description: task.description, preset: task.preset,
        subtasksDone: task.stats?.subtasks_completed,
        subtasksTotal: task.stats?.subtasks_total,
        // MARKER_155A.P1.CROSSCUT_TASKS: Carry cross-cut metadata in node payload.
        graphKind: 'project_task',
        primaryNodeId: task.primary_node_id || task.module,
        affectedNodes: task.affected_nodes,
        integrationTaskOf: task.integration_task_of,
      });
      edges.push({
        id: `e-${phase}-${task.id}`, source: branchId, target: task.id,
        type: 'structural' as EdgeType, strength: 0.7, relationKind: 'executes',
      });
    }
  }

  // --- Real dependency edges (if any) ---
  const idSet = new Set(tasks.map(t => t.id));
  for (const task of tasks) {
    if (task.dependencies) {
      for (const depId of task.dependencies) {
        if (idSet.has(depId)) {
          edges.push({
            id: `dep-${depId}-${task.id}`, source: depId, target: task.id,
            type: 'dependency' as EdgeType, strength: 0.8, relationKind: 'depends_on',
          });
        }
      }
    }
  }

  return { nodes, edges };
}

function mapTaskNodeStatus(status: string): NodeStatus {
  if (status === 'running' || status === 'claimed') return 'running';
  if (status === 'done') return 'done';
  if (status === 'failed' || status === 'cancelled') return 'failed';
  return 'pending';
}

// MARKER_155A.G21.SINGLE_CANVAS_STATE:
// Overlay tasks directly on top of architecture graph (same canvas, no phase-train view switch).
function overlayTasksOnRoadmap(
  roadmapNodes: DAGNode[],
  roadmapEdges: DAGEdge[],
  tasks: TaskData[],
  focusRoadmapNodeId: string,
  selectedTaskId?: string | null,
): { nodes: DAGNode[]; edges: DAGEdge[] } {
  const baseNodes = [...roadmapNodes];
  const baseEdges = [...roadmapEdges];

  const taskNodes: DAGNode[] = [];
  const taskEdges: DAGEdge[] = [];
  const overlayTaskIds = new Set<string>();

  for (const task of tasks) {
    const id = `task_overlay_${task.id}`;
    const anchors = resolveTaskAnchorIds(task, roadmapNodes);
    const suggestedAnchors = anchors.length === 0 ? inferSuggestedAnchorIds(task, roadmapNodes) : [];
    const effectiveAnchors = anchors.length > 0 ? anchors : suggestedAnchors;
    const anchorState: 'anchored' | 'suggested' | 'unplaced' =
      anchors.length > 0 ? 'anchored' : suggestedAnchors.length > 0 ? 'suggested' : 'unplaced';
    // Keep roadmap clean: show suggested anchors only for explicitly selected task.
    if (anchorState === 'suggested' && (!selectedTaskId || task.id !== selectedTaskId)) continue;
    // Keep fully unplaced tasks out of roadmap graph until operator places them.
    if (anchorState === 'unplaced') continue;
    overlayTaskIds.add(task.id);
    const teamProfile = String(task.team_profile || task.preset || 'dragon_bronze');
    const workflowId = String(task.workflow_id || task.pipeline_task_id || `wf_task_${task.id}`);
    const taskOrigin = normalizeTaskOrigin(task.task_origin || task.source);

    taskNodes.push({
      id,
      type: 'roadmap_task',
      label: task.title,
      status: mapTaskNodeStatus(task.status),
      layer: 3,
      taskId: task.id,
      description: task.description,
      preset: teamProfile,
      subtasksDone: task.stats?.subtasks_completed,
      subtasksTotal: task.stats?.subtasks_total,
      graphKind: 'project_task',
      primaryNodeId: task.primary_node_id || task.module || focusRoadmapNodeId,
      affectedNodes: task.affected_nodes,
      integrationTaskOf: task.integration_task_of,
      workflowId,
      teamProfile,
      taskOrigin,
      anchorNodeIds: effectiveAnchors,
      anchorState,
    });

    const edgeAnchors = effectiveAnchors;

    for (const anchor of edgeAnchors) {
      taskEdges.push({
        id: `overlay-affects-${anchor}-${task.id}`,
        source: anchor,
        target: id,
        type: 'structural',
        relationKind: 'affects',
        strength: anchorState === 'suggested' ? 0.42 : 0.72,
      });
    }
  }

  for (const task of tasks) {
    if (!overlayTaskIds.has(task.id)) continue;
    for (const depId of task.dependencies || []) {
      if (!overlayTaskIds.has(depId)) continue;
      taskEdges.push({
        id: `overlay-dep-${depId}-${task.id}`,
        source: `task_overlay_${depId}`,
        target: `task_overlay_${task.id}`,
        type: 'dependency',
        relationKind: 'depends_on',
        strength: 0.8,
      });
    }
  }

  return { nodes: [...baseNodes, ...taskNodes], edges: [...baseEdges, ...taskEdges] };
}

function overlayWorkflowOnSelectedTask(
  baseNodes: DAGNode[],
  baseEdges: DAGEdge[],
  workflowNodes: DAGNode[],
  workflowEdges: DAGEdge[],
  selectedTaskId: string,
): { nodes: DAGNode[]; edges: DAGEdge[] } {
  if (workflowNodes.length === 0) {
    return { nodes: baseNodes, edges: baseEdges };
  }

  const visibleWorkflowNodes = workflowNodes.filter((n) => n.type !== 'task');
  if (visibleWorkflowNodes.length === 0) {
    return { nodes: baseNodes, edges: baseEdges };
  }

  const idMap = new Map<string, string>();
  visibleWorkflowNodes.forEach((n) => idMap.set(n.id, `wf_${selectedTaskId}_${n.id}`));

  const remappedNodes: DAGNode[] = visibleWorkflowNodes.map((n) => ({
    ...n,
    id: idMap.get(n.id) || n.id,
    taskId: selectedTaskId,
    workflowId: n.workflowId || selectedTaskId,
    graphKind: n.graphKind || 'workflow_agent',
    metadata: {
      ...(n.metadata || {}),
      mini_scale: 0.42,
    },
    // MARKER_155A.P0.WF_MINI_LAYER:
    // Inline workflow is rendered as micro-layer (fractal scale) over architecture.
    width: 54,
    height: 24,
  }));

  const remappedEdges: DAGEdge[] = [];
  for (const e of workflowEdges) {
    const source = idMap.get(e.source);
    const target = idMap.get(e.target);
    if (!source || !target) continue;
    remappedEdges.push({
      ...e,
      id: `wf_${selectedTaskId}_${e.id}`,
      source,
      target,
      type: e.type || 'dataflow',
      relationKind: e.relationKind || 'executes',
      strength: Math.max(0.35, Number(e.strength || 0.65)),
    });
  }

  const hasIncoming = new Set<string>(remappedEdges.map((e) => e.target));
  const entryNodeId = remappedNodes
    .map((n) => n.id)
    .sort((a, b) => a.localeCompare(b))
    .find((id) => !hasIncoming.has(id));
  const overlayTaskNodeId = `task_overlay_${selectedTaskId}`;
  const bridgeEdges: DAGEdge[] = entryNodeId
    ? [{
        id: `wf_bridge_${selectedTaskId}`,
        source: overlayTaskNodeId,
        target: entryNodeId,
        type: 'structural',
        relationKind: 'contains',
        strength: 0.26,
      }]
    : [];

  return {
    nodes: [...baseNodes, ...remappedNodes],
    edges: [...baseEdges, ...remappedEdges, ...bridgeEdges],
  };
}

// MARKER_155A.G23.NODE_DRILL_NEXT_DEPTH:
// Roadmap matryoshka drill for folder/node: reveal only next depth as micro-layer.
function overlayRoadmapNodeChildren(
  baseNodes: DAGNode[],
  baseEdges: DAGEdge[],
  parentNodeId: string,
): { nodes: DAGNode[]; edges: DAGEdge[] } {
  if (!parentNodeId) return { nodes: baseNodes, edges: baseEdges };
  const structural = baseEdges.filter((e) => {
    if (e.relationKind === 'contains') return true;
    if (e.type === 'structural') return true;
    return false;
  });
  if (structural.length === 0) return { nodes: baseNodes, edges: baseEdges };

  const byId = new Map(baseNodes.map((n) => [n.id, n]));
  const validRoadmapNode = (id: string): boolean => {
    if (!id) return false;
    if (id.startsWith('task_overlay_') || id.startsWith('wf_') || id.startsWith('rd_')) return false;
    return byId.has(id);
  };
  const adjacency = new Map<string, Set<string>>();
  const connect = (a: string, b: string) => {
    if (!validRoadmapNode(a) || !validRoadmapNode(b)) return;
    const aa = adjacency.get(a) || new Set<string>();
    aa.add(b);
    adjacency.set(a, aa);
  };
  for (const e of structural) {
    connect(e.source, e.target);
    connect(e.target, e.source);
  }

  const remappedNodes: DAGNode[] = [];
  const remappedEdges: DAGEdge[] = [];
  const seen = new Set<string>();

  // MARKER_155A.G23.NODE_DRILL_BREADTH:
  // Show richer next-depth context (children + limited grandchildren) instead of a single node.
  let depth1 = Array.from(adjacency.get(parentNodeId) || [])
    .filter((id) => validRoadmapNode(id))
    .sort((a, b) => a.localeCompare(b))
    .slice(0, 6);

  // MARKER_155A.G23.NODE_DRILL_PATH_FALLBACK:
  // If graph edges provide too sparse neighborhood, derive child candidates by path hierarchy.
  if (depth1.length < 2) {
    const parent = byId.get(parentNodeId);
    const parentMeta: any = parent?.metadata || {};
    const parentPath = normalizePathKey(
      String(parentMeta.path || parentMeta.file_path || parent?.projectNodeId || parent?.id || '')
    );
    if (parentPath) {
      const segCount = parentPath.split('/').filter(Boolean).length;
      const pathCandidates = baseNodes
        .filter((n) => validRoadmapNode(n.id))
        .filter((n) => {
          const m: any = n.metadata || {};
          const p = normalizePathKey(String(m.path || m.file_path || n.projectNodeId || n.id || ''));
          if (!p || p === parentPath) return false;
          if (!p.startsWith(`${parentPath}/`)) return false;
          const pc = p.split('/').filter(Boolean).length;
          return pc === segCount + 1;
        })
        .map((n) => n.id)
        .sort((a, b) => a.localeCompare(b))
        .slice(0, 8);
      if (pathCandidates.length > depth1.length) depth1 = pathCandidates;
    }
  }
  const depth2Set = new Set<string>();
  for (const c of depth1) {
    const neighbors = Array.from(adjacency.get(c) || [])
      .filter((id) => id !== parentNodeId && validRoadmapNode(id))
      .sort((a, b) => a.localeCompare(b))
      .slice(0, 3);
    neighbors.forEach((id) => depth2Set.add(id));
    if (depth2Set.size >= 8) break;
  }
  const depth2 = Array.from(depth2Set).slice(0, 8);

  const pushNode = (childId: string, depth: number) => {
    if (seen.has(childId)) return;
    const child = byId.get(childId);
    if (!child) return;
    seen.add(childId);
    const rid = `rd_${parentNodeId}_${childId}`;
    remappedNodes.push({
      ...child,
      id: rid,
      metadata: {
        ...(child.metadata || {}),
        rd_parent: parentNodeId,
        rd_depth: depth,
        mini_scale: 0.14,
      },
      width: 44,
      height: 18,
    });
    remappedEdges.push({
      id: `rd_bridge_${parentNodeId}_${childId}`,
      source: parentNodeId,
      target: rid,
      type: 'structural',
      relationKind: 'contains',
      strength: 0.24,
    });
  };

  depth1.forEach((id) => pushNode(id, 1));
  depth2.forEach((id) => pushNode(id, 2));

  if (remappedNodes.length === 0) return { nodes: baseNodes, edges: baseEdges };
  return {
    nodes: [...baseNodes, ...remappedNodes],
    edges: [...baseEdges, ...remappedEdges],
  };
}

function buildInlineWorkflowFromPipeline(taskId: string, subtasks: Array<any>): { nodes: DAGNode[]; edges: DAGEdge[] } {
  const nodes: DAGNode[] = [
    { id: `wf_arch_${taskId}`, type: 'agent', label: '@architect', status: 'done', layer: 1, taskId, role: 'architect', graphKind: 'workflow_agent' },
    { id: `wf_coder_${taskId}`, type: 'agent', label: '@coder', status: 'running', layer: 1, taskId, role: 'coder', graphKind: 'workflow_agent' },
    { id: `wf_verifier_${taskId}`, type: 'agent', label: '@verifier', status: 'pending', layer: 1, taskId, role: 'verifier', graphKind: 'workflow_agent' },
  ];
  const edges: DAGEdge[] = [
    { id: `wf_e_arch_coder_${taskId}`, source: `wf_arch_${taskId}`, target: `wf_coder_${taskId}`, type: 'dataflow', strength: 0.7, relationKind: 'passes' },
    { id: `wf_e_coder_ver_${taskId}`, source: `wf_coder_${taskId}`, target: `wf_verifier_${taskId}`, type: 'temporal', strength: 0.64, relationKind: 'executes' },
  ];
  const max = Math.min(Array.isArray(subtasks) ? subtasks.length : 0, 12);
  for (let i = 0; i < max; i += 1) {
    const st = subtasks[i] || {};
    const sid = `wf_sub_${taskId}_${i}`;
    const raw = String(st.status || 'pending').toLowerCase();
    const status: NodeStatus = raw === 'done' ? 'done' : raw === 'failed' ? 'failed' : raw === 'running' ? 'running' : 'pending';
    nodes.push({
      id: sid,
      type: 'subtask',
      label: String(st.description || `subtask ${i + 1}`).slice(0, 46),
      status,
      layer: 2,
      taskId,
      description: st.result ? String(st.result).slice(0, 220) : undefined,
      graphKind: 'workflow_artifact',
    });
    edges.push({
      id: `wf_e_coder_sub_${taskId}_${i}`,
      source: `wf_coder_${taskId}`,
      target: sid,
      type: 'dataflow',
      strength: 0.62,
      relationKind: 'produces',
    });
    edges.push({
      id: `wf_e_sub_ver_${taskId}_${i}`,
      source: sid,
      target: `wf_verifier_${taskId}`,
      type: 'temporal',
      strength: 0.56,
      relationKind: 'executes',
    });
  }
  return { nodes, edges };
}

function buildInlineWorkflowFromTemplate(taskId: string, template: any): { nodes: DAGNode[]; edges: DAGEdge[] } {
  const rawNodes = Array.isArray(template?.nodes) ? template.nodes : [];
  const rawEdges = Array.isArray(template?.edges) ? template.edges : [];
  if (rawNodes.length === 0) return { nodes: [], edges: [] };

  const asNodeType = (raw: string): DAGNodeType => {
    const t = String(raw || '').toLowerCase();
    if (t === 'agent' || t === 'subtask' || t === 'proposal' || t === 'condition' || t === 'parallel' || t === 'loop' || t === 'transform' || t === 'group') {
      return t as DAGNodeType;
    }
    return 'agent';
  };

  const asEdgeType = (raw: string): EdgeType => {
    const t = String(raw || '').toLowerCase();
    if (t === 'structural' || t === 'dataflow' || t === 'temporal' || t === 'conditional' || t === 'parallel_fork' || t === 'parallel_join' || t === 'feedback') {
      return t as EdgeType;
    }
    return 'structural';
  };

  const nodes: DAGNode[] = rawNodes.map((n: any, idx: number) => {
    const nodeType = asNodeType(String(n?.type || 'agent'));
    const role = String(n?.data?.role || '').toLowerCase();
    const status: NodeStatus = role === 'coder' ? 'running' : 'pending';
    const layer = nodeType === 'agent' ? 1 : (nodeType === 'subtask' ? 2 : 3);
    const nodeId = String(n?.id || `template_node_${idx}`);
    return {
      id: nodeId,
      type: nodeType,
      label: String(n?.label || nodeId).slice(0, 56),
      status,
      layer,
      taskId,
      role: role || undefined,
      description: String(n?.data?.description || '').slice(0, 220) || undefined,
      graphKind: nodeType === 'agent' ? 'workflow_agent' : 'workflow_artifact',
      workflowId: String(template?.id || template?.name || 'bmad_default'),
      metadata: {
        wf_x: Number(n?.position?.x ?? 0),
        wf_y: Number(n?.position?.y ?? 0),
      },
    };
  });

  const nodeIdSet = new Set(nodes.map((n) => n.id));
  const edges: DAGEdge[] = rawEdges
    .map((e: any, idx: number): DAGEdge | null => {
      const source = String(e?.source || '');
      const target = String(e?.target || '');
      if (!source || !target || !nodeIdSet.has(source) || !nodeIdSet.has(target)) return null;
      return {
        id: String(e?.id || `tpl_e_${idx}`),
        source,
        target,
        type: asEdgeType(String(e?.type || 'structural')),
        strength: 0.68,
        relationKind: String(e?.type || 'executes'),
      };
    })
    .filter((e): e is DAGEdge => !!e);

  return { nodes, edges };
}

function selectInlineWorkflowSource(
  selectedTaskId: string,
  dagNodes: DAGNode[],
  dagEdges: DAGEdge[],
  templateNodes: DAGNode[],
  templateEdges: DAGEdge[],
  pipelineNodes: DAGNode[],
  pipelineEdges: DAGEdge[],
): { nodes: DAGNode[]; edges: DAGEdge[]; source: 'dag' | 'template' | 'pipeline' } {
  const hasDetailedDagWorkflow = dagNodes.some((n) => n.type !== 'task');
  if (hasDetailedDagWorkflow) {
    return { nodes: dagNodes, edges: dagEdges, source: 'dag' };
  }
  if (templateNodes.length > 0 && templateEdges.length > 0) {
    return { nodes: templateNodes, edges: templateEdges, source: 'template' };
  }
  if (pipelineNodes.length > 0 && pipelineEdges.length > 0) {
    return { nodes: pipelineNodes, edges: pipelineEdges, source: 'pipeline' };
  }
  const fallback = buildInlineWorkflowFromPipeline(selectedTaskId, []);
  return { nodes: fallback.nodes, edges: fallback.edges, source: 'pipeline' };
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
  const [inlineWorkflowNodes, setInlineWorkflowNodes] = useState<DAGNode[]>([]);
  const [inlineWorkflowEdges, setInlineWorkflowEdges] = useState<DAGEdge[]>([]);
  const [inlineTemplateWorkflowNodes, setInlineTemplateWorkflowNodes] = useState<DAGNode[]>([]);
  const [inlineTemplateWorkflowEdges, setInlineTemplateWorkflowEdges] = useState<DAGEdge[]>([]);
  const [predictedEdges, setPredictedEdges] = useState<DAGEdge[]>([]);
  const [stats, setStats] = useState<DAGStats | null>(null);
  const [loading, setLoading] = useState(true);

  // UI state
  const [taskDrillState, setTaskDrillState] = useState<TaskDrillState>('collapsed');
  const [roadmapNodeDrillState, setRoadmapNodeDrillState] = useState<RoadmapNodeDrillState>('collapsed');
  const [roadmapDrillNodeId, setRoadmapDrillNodeId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [selectedEdge, setSelectedEdge] = useState<{
    id: string; source: string; target: string; type: string;
  } | null>(null);
  const [showStream, setShowStream] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [executeMsg, setExecuteMsg] = useState<string | null>(null);
  const { step: onboardingStep, completed: onboardingCompleted, dismissed: onboardingDismissed, advance: onboardingAdvance, dismiss: onboardingDismiss } = useOnboarding();

  // MARKER_155.WIZARD.027: Wizard flow state — track current step (1-5)
  const [wizardStep, setWizardStep] = useState<WizardStep>(1);
  const [wizardData, setWizardData] = useState<Record<number, any>>({});
  
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

  // MARKER_154.8A: Task editor popup state (Wave 3)
  const [showTaskEdit, setShowTaskEdit] = useState(false);
  // MARKER_154.10A: Redo feedback input state (Wave 3)
  const [showRedoInput, setShowRedoInput] = useState(false);
  const dagViewRef = useRef<DAGViewRef | null>(null);
  const [focusDisplayMode, setFocusDisplayMode] = useState<FocusDisplayMode>('all');
  const [jepaRuntimeUi, setJepaRuntimeUi] = useState<{
    title: string;
    hint: string;
    color: string;
  } | null>(null);
  const focusMemoryRef = useRef<Record<string, string[]>>({});
  const isRestoringFocusRef = useRef(false);

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
  const dagFetchInFlightRef = useRef(false);
  const dagFetchQueuedRef = useRef(false);
  const dagFetchSeqRef = useRef(0);
  const lastPredictiveErrorKeyRef = useRef<string>('');
  const runtimeHealthCacheRef = useRef<{ ok: boolean; detail: string; ts: number } | null>(null);
  const predictiveSkipUntilRef = useRef<number>(0);

  const isActiveWindow = useCallback(() => {
    if (typeof document === 'undefined') return true;
    return document.visibilityState === 'visible';
  }, []);

  // MARKER_143.P3: Fetch DAG data — filtered by selectedTaskId when set
  const fetchDAG = useCallback(async (taskId?: string | null) => {
    const requestSeq = ++dagFetchSeqRef.current;
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

      if (requestSeq !== dagFetchSeqRef.current) return;
      setDagNodes(nodes);
      setDagEdges(edges);
      setStats(mappedStats);
    } catch (err) {
      console.warn('DAG API unavailable:', err);
      if (requestSeq !== dagFetchSeqRef.current) return;
      setDagNodes([]);
      setDagEdges([]);
      setStats({
        totalTasks: 0, runningTasks: 0, completedTasks: 0,
        failedTasks: 0, successRate: 0, totalAgents: 0, totalSubtasks: 0,
      });
    } finally {
      if (requestSeq !== dagFetchSeqRef.current) return;
      setLoading(false);
    }
  }, []);

  // MARKER_153.1C: Initialize MCC — load project config + session state on mount
  const initMCC = useMCCStore(s => s.initMCC);
  const hasProject = useMCCStore(s => s.hasProject);
  const projectConfig = useMCCStore(s => s.projectConfig);
  const navLevel = useMCCStore(s => s.navLevel);
  const navRoadmapNodeId = useMCCStore(s => s.navRoadmapNodeId);
  const drillDown = useMCCStore(s => s.drillDown);
  const goBack = useMCCStore(s => s.goBack);
  const cameraPosition = useMCCStore(s => s.cameraPosition);
  const setCameraPosition = useMCCStore(s => s.setCameraPosition);
  const setFocusedNodeId = useMCCStore(s => s.setFocusedNodeId);
  const focusRestorePolicy = useMCCStore(s => s.focusRestorePolicy);
  const focusRestoreSource = useMCCStore(s => s.focusRestoreSource);
  const setFocusRestorePolicy = useMCCStore(s => s.setFocusRestorePolicy);
  const setFocusRestoreSource = useMCCStore(s => s.setFocusRestoreSource);
  const persistSessionState = useMCCStore(s => s.persistSessionState);
  const layoutPins = useMCCStore(s => s.layoutPins);
  const setLayoutPinsForKey = useMCCStore(s => s.setLayoutPinsForKey);
  const selectedKey = useStore(s => s.selectedKey);
  const loadFavorites = useStore(s => s.loadFavorites);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [mccReady, setMccReady] = useState(false);
  const [cameraLOD, setCameraLOD] = useState<LODLevel>('tasks');
  const dagGraphIdentity = useMemo(
    () => `${navLevel}:${navRoadmapNodeId || 'none'}`,
    [navLevel, navRoadmapNodeId],
  );
  const focusScopeKey = useMemo(() => {
    if (navLevel === 'roadmap') return `roadmap:${navRoadmapNodeId || 'root'}`;
    if (navLevel === 'tasks') return `tasks:${navRoadmapNodeId || 'root'}`;
    if (navLevel === 'workflow') return `workflow:${selectedTaskId || 'none'}:${navRoadmapNodeId || 'root'}`;
    return `${navLevel}:${selectedTaskId || 'none'}:${navRoadmapNodeId || 'root'}`;
  }, [navLevel, navRoadmapNodeId, selectedTaskId]);
  const layoutPreferenceScopeKey = useMemo(() => {
    const graphType = navLevel === 'roadmap' ? 'architecture' : navLevel === 'tasks' ? 'tasks' : 'workflow';
    const scopeRoot = String(projectConfig?.source_path || projectConfig?.sandbox_path || 'default').replace(/\\/g, '/');
    return `dag:${scopeRoot}:${graphType}`;
  }, [projectConfig?.source_path, projectConfig?.sandbox_path, navLevel]);
  const pinnedPositions = useMemo(
    () => layoutPins[dagGraphIdentity] || {},
    [layoutPins, dagGraphIdentity],
  );
  // MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1:
  // Shared layout intent profile from ENGRAM (MCC + VETKA).
  const [layoutBiasProfile, setLayoutBiasProfile] = useState<DagLayoutBiasProfile | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchDagLayoutBiasProfile(layoutPreferenceScopeKey)
      .then((profile) => {
        if (!cancelled) setLayoutBiasProfile(profile);
      })
      .catch(() => {
        if (!cancelled) setLayoutBiasProfile(null);
      });
    return () => {
      cancelled = true;
    };
  }, [layoutPreferenceScopeKey]);

  // MARKER_155.WIZARD.028: Wizard navigation handlers (after initMCC declared)
  const handleWizardComplete = useCallback((step: WizardStep, data: any) => {
    setWizardData(prev => ({ ...prev, [step]: data }));
    
    if (step < 5) {
      setWizardStep((step + 1) as WizardStep);
    }
    
    // When completing step 3 (Keys), initialize the project
    if (step === 3) {
      initMCC();
    }
  }, [initMCC]);

  const handleWizardBack = useCallback(() => {
    if (wizardStep > 1) {
      setWizardStep((wizardStep - 1) as WizardStep);
    }
  }, [wizardStep]);

  // MARKER_153.5B: Roadmap DAG data hook
  const projectScopePath = projectConfig?.source_path || projectConfig?.sandbox_path || '';
  const roadmap = useRoadmapDAG(projectScopePath);
  const [dagVersions, setDagVersions] = useState<DagVersionSummary[]>([]);
  const [activeDagVersionId, setActiveDagVersionId] = useState<string | null>(null);
  const [activeDagVersionPayload, setActiveDagVersionPayload] = useState<any | null>(null);
  const [dagVersionsLoading, setDagVersionsLoading] = useState(false);
  const [dagVersionsError, setDagVersionsError] = useState<string | null>(null);
  const [dagCompareLoading, setDagCompareLoading] = useState(false);
  const [dagCompareError, setDagCompareError] = useState<string | null>(null);
  const [dagCompareBest, setDagCompareBest] = useState<{ name: string; score: number; version_id: string } | null>(null);
  const [dagCompareRows, setDagCompareRows] = useState<DagCompareRow[]>([]);
  const [showDagCompareMatrix, setShowDagCompareMatrix] = useState(false);
  const [selectedDagCompareName, setSelectedDagCompareName] = useState<string | null>(null);
  const [debugMode, setDebugMode] = useState(false);
  // MARKER_153.6C: Toast notifications for pipeline/system events
  const { toasts, addToast, dismissToast } = useToast();

  const fetchDagVersions = useCallback(async () => {
    if (!hasProject) return;
    setDagVersionsLoading(true);
    setDagVersionsError(null);
    try {
      const res = await fetch(`${API_BASE}/mcc/dag-versions/list`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const versions = Array.isArray(data?.versions) ? data.versions as DagVersionSummary[] : [];
      setDagVersions(versions);
      const primaryId = String(data?.primary_version_id || '');
      if (primaryId && !activeDagVersionId) {
        setActiveDagVersionId(primaryId);
      }
    } catch (err) {
      setDagVersionsError(err instanceof Error ? err.message : 'Failed to load DAG versions');
    } finally {
      setDagVersionsLoading(false);
    }
  }, [hasProject, activeDagVersionId]);

  const fetchDagVersionPayload = useCallback(async (versionId: string | null) => {
    if (!versionId) {
      setActiveDagVersionPayload(null);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/mcc/dag-versions/${encodeURIComponent(versionId)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setActiveDagVersionPayload(data?.version || null);
    } catch {
      setActiveDagVersionPayload(null);
    }
  }, []);

  const createDagSnapshot = useCallback(async () => {
    const payload = {
      design_graph: {
        nodes: roadmap.nodes,
        edges: roadmap.edges,
        cross_edges: roadmap.crossEdges,
      },
      verifier: roadmap.verifier,
      predictive_overlay: { stats: { enabled: false, predicted_edges: 0 } },
    };
    const body = {
      name: `Snapshot ${new Date().toLocaleTimeString()}`,
      author: 'architect',
      source: 'manual',
      set_primary: false,
      markers: ['MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.V1'],
      build_meta: {
        builder_profile: 'mcc_manual_snapshot',
        weights: {},
        budget: { max_nodes: roadmap.nodes.length || 0 },
        verifier: roadmap.verifier || {},
        spectral: roadmap.verifier?.spectral || {},
        overlay_stats: { enabled: false, predicted_edges: 0 },
      },
      dag_payload: payload,
    };
    try {
      const res = await fetch(`${API_BASE}/mcc/dag-versions/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const vid = String(data?.version?.version_id || '');
      await fetchDagVersions();
      if (vid) setActiveDagVersionId(vid);
      addToast('success', 'DAG snapshot saved');
    } catch (err) {
      addToast('error', `Failed to save DAG snapshot: ${err instanceof Error ? err.message : 'unknown'}`);
    }
  }, [roadmap.nodes, roadmap.edges, roadmap.crossEdges, roadmap.verifier, fetchDagVersions, addToast]);

  const setPrimaryDagVersion = useCallback(async (versionId: string) => {
    try {
      const res = await fetch(`${API_BASE}/mcc/dag-versions/${encodeURIComponent(versionId)}/set-primary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ set_primary: true }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchDagVersions();
      addToast('info', 'Primary DAG version updated');
    } catch (err) {
      addToast('error', `Failed to set primary DAG version: ${err instanceof Error ? err.message : 'unknown'}`);
    }
  }, [fetchDagVersions, addToast]);

  const runDagAutoCompare = useCallback(async () => {
    if (!hasProject || roadmap.nodes.length === 0) return;
    setDagCompareLoading(true);
    setDagCompareError(null);
    try {
      const maxNodesBase = Math.max(120, Math.min(360, roadmap.nodes.length || 180));
      const variants = [
        {
          name: 'clean_topology',
          max_nodes: Math.max(120, Math.round(maxNodesBase * 0.75)),
          use_predictive_overlay: false,
          min_confidence: 0.78,
        },
        {
          name: 'balanced',
          max_nodes: maxNodesBase,
          use_predictive_overlay: false,
          min_confidence: 0.66,
        },
        {
          name: 'overlay_try',
          max_nodes: Math.min(420, Math.round(maxNodesBase * 1.1)),
          use_predictive_overlay: true,
          max_predicted_edges: 22,
          min_confidence: 0.72,
        },
      ];
      const res = await fetch(`${API_BASE}/mcc/dag-versions/auto-compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_kind: 'scope',
          default_max_nodes: maxNodesBase,
          persist_versions: true,
          set_primary_best: false,
          variants,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const best = data?.best || {};
      const rows = Array.isArray(data?.variants) ? data.variants as DagCompareRow[] : [];
      setDagCompareRows(rows);
      setShowDagCompareMatrix(rows.length > 0);
      setSelectedDagCompareName(rows.length > 0 ? String(rows[0]?.name || null) : null);
      const bestName = String(best?.name || '');
      const bestVersion = String(best?.version_id || '');
      const bestScore = Number(best?.score || 0);
      if (bestName || bestVersion) {
        setDagCompareBest({
          name: bestName || 'best',
          score: Number.isFinite(bestScore) ? bestScore : 0,
          version_id: bestVersion,
        });
      } else {
        setDagCompareBest(null);
      }
      await fetchDagVersions();
      if (bestVersion) {
        setActiveDagVersionId(bestVersion);
      }
      addToast('info', `DAG auto-compare done (${rows.length} variants)`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'unknown';
      setDagCompareError(msg);
      addToast('error', `DAG auto-compare failed: ${msg}`);
    } finally {
      setDagCompareLoading(false);
    }
  }, [hasProject, roadmap.nodes.length, fetchDagVersions, addToast]);

  useEffect(() => {
    if (!mccReady || !hasProject) return;
    fetchDagVersions();
  }, [mccReady, hasProject, fetchDagVersions]);

  useEffect(() => {
    fetchDagVersionPayload(activeDagVersionId);
  }, [activeDagVersionId, fetchDagVersionPayload]);

  const versionRoadmapGraph = useMemo(() => {
    const dagPayload = activeDagVersionPayload?.dag_payload || {};
    const design = dagPayload?.design_graph || {};
    const nodesRaw = Array.isArray(design?.nodes) ? design.nodes : [];
    const edgesRaw = Array.isArray(design?.edges) ? design.edges : [];
    const crossRaw = Array.isArray(design?.cross_edges) ? design.cross_edges : [];
    if (nodesRaw.length === 0 || edgesRaw.length === 0) return null;
    return {
      nodes: nodesRaw.map((n: any) => adaptVersionNode(n)),
      edges: edgesRaw.map((e: any, idx: number) => adaptVersionEdge(e, idx)),
      crossEdges: crossRaw.map((e: any, idx: number) => adaptVersionEdge(e, idx)),
      verifier: dagPayload?.verifier || activeDagVersionPayload?.build_meta?.verifier || null,
    };
  }, [activeDagVersionPayload]);

  const roadmapNodes = versionRoadmapGraph?.nodes || roadmap.nodes;
  const roadmapEdges = versionRoadmapGraph?.edges || roadmap.edges;
  const roadmapCrossEdges = versionRoadmapGraph?.crossEdges || roadmap.crossEdges;
  const roadmapVerifier = versionRoadmapGraph?.verifier || roadmap.verifier;
  const selectedDagCompareRow = useMemo(() => {
    if (!selectedDagCompareName) return null;
    return dagCompareRows.find((r) => r.name === selectedDagCompareName) || null;
  }, [dagCompareRows, selectedDagCompareName]);

  const verifierUi = useMemo(() => {
    if (!roadmapVerifier) return null;
    const decision = String(roadmapVerifier.decision || 'warn').toLowerCase();
    if (decision === 'pass') {
      return {
        title: 'Graph Health: Stable',
        hint: 'Архитектурная топология стабильна. Кликните на ноду, чтобы увидеть связи/риски.',
        color: '#7fe7c4',
      };
    }
    if (decision === 'warn') {
      return {
        title: 'Graph Health: Needs Cleanup',
        hint: 'Есть структурные перегрузки. Рекомендуется branch-focus и уточнение модулей.',
        color: '#f0cf7a',
      };
    }
    return {
      title: 'Graph Health: Unstable',
      hint: 'Обнаружены проблемы структуры. Нужно пересобрать дизайн DAG перед раздачей задач.',
      color: '#ef8d8d',
    };
  }, [roadmapVerifier]);

  // MARKER_153.7C: Architect Captain recommendations
  const captain = useCaptain(mccReady && hasProject);
  const [captainDismissed, setCaptainDismissed] = useState(false);

  useEffect(() => {
    initMCC().then(() => {
      setMccReady(true);
    });
  }, [initMCC]);

  useEffect(() => {
    loadFavorites();
  }, [loadFavorites]);

  useEffect(() => {
    if (!mccReady) return;
    persistSessionState();
  }, [selectedKey, mccReady, persistSessionState]);

  // MARKER_153.5B: Fetch roadmap when MCC is ready and project exists
  useEffect(() => {
    if (mccReady && hasProject) {
      roadmap.fetchRoadmap();
    }
  }, [mccReady, hasProject, projectScopePath]);

  // MARKER_155.P15.UI_BIND:
  // Fetch predictive overlay edges for roadmap-level single-canvas view.
  const fetchPredictiveOverlay = useCallback(async () => {
    if (!mccReady || !hasProject || navLevel !== 'roadmap') {
      setPredictedEdges([]);
      setJepaRuntimeUi(null);
      return;
    }
    const focusNodeIds = selectedNodeIds.length > 0
      ? selectedNodeIds
      : selectedNode
        ? [selectedNode]
        : [];
    if (focusNodeIds.length === 0) {
      setPredictedEdges([]);
      setJepaRuntimeUi(null);
      return;
    }
    try {
      const jepaProvider = cameraLOD === 'architecture' ? 'runtime' : 'auto';
      const jepaStrict = cameraLOD === 'architecture';
      const jepaRuntimeModule =
        (import.meta as any)?.env?.VITE_MCC_JEPA_RUNTIME_MODULE ||
        'src.services.jepa_runtime';
      if (jepaStrict) {
        const now = Date.now();
        if (predictiveSkipUntilRef.current > now) {
          setPredictedEdges([]);
          return;
        }
        const cache = runtimeHealthCacheRef.current;
        const cacheFresh = cache && (now - cache.ts) < 3000;
        let runtimeOk = Boolean(cache?.ok);
        let runtimeDetail = String(cache?.detail || '');
        if (!cacheFresh) {
          const healthUrl = `${API_BASE}/mcc/graph/predict/runtime-health?force=false&runtime_module=${encodeURIComponent(jepaRuntimeModule)}`;
          const healthRes = await fetch(healthUrl);
          const healthData = await healthRes.json().catch(() => ({}));
          runtimeOk = Boolean(healthData?.ok);
          runtimeDetail = String(healthData?.detail || '');
          runtimeHealthCacheRef.current = { ok: runtimeOk, detail: runtimeDetail, ts: now };
        }
        if (!runtimeOk) {
          setJepaRuntimeUi({
            title: 'JEPA Runtime: Unavailable',
            hint: runtimeDetail || 'runtime health failed',
            color: '#ef8d8d',
          });
          setPredictedEdges([]);
          predictiveSkipUntilRef.current = now + 5000;
          return;
        }
      }
      const res = await fetch(`${API_BASE}/mcc/graph/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scope_path: projectScopePath,
          max_nodes: Math.max(120, Math.min(260, roadmapNodes.length || 0)),
          max_predicted_edges: cameraLOD === 'architecture' ? 28 : cameraLOD === 'tasks' ? 20 : 14,
          include_artifacts: false,
          min_confidence: 0.78,
          focus_node_ids: focusNodeIds,
          jepa_provider: jepaProvider,
          jepa_runtime_module: jepaRuntimeModule,
          jepa_strict: jepaStrict,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const detail = String(errData?.detail || `HTTP ${res.status}`);
        const errKey = `${res.status}:${detail}`;
        setJepaRuntimeUi({
          title: 'JEPA Runtime: Unavailable',
          hint: detail,
          color: '#ef8d8d',
        });
        if (lastPredictiveErrorKeyRef.current !== errKey) {
          addToast('error', `JEPA runtime unavailable: ${detail}`);
          lastPredictiveErrorKeyRef.current = errKey;
        }
        predictiveSkipUntilRef.current = Date.now() + 5000;
        setPredictedEdges([]);
        return;
      }
      const data = await res.json();
      const predictorMode = String(data?.stats?.predictor_mode || '');
      const predictorDetail = String(data?.stats?.predictor_detail || '');
      const strictRuntime = Boolean(data?.stats?.strict_runtime);
      const runtimeOk = predictorMode === 'jepa_runtime_module' && predictorDetail.includes('|jepa_http_runtime');
      if (strictRuntime) {
        if (runtimeOk) {
          setJepaRuntimeUi({
            title: 'JEPA Runtime: Live',
            hint: predictorDetail,
            color: '#7fe7c4',
          });
        } else {
          setJepaRuntimeUi({
            title: 'JEPA Runtime: Degraded',
            hint: predictorDetail || 'strict runtime violated',
            color: '#f0cf7a',
          });
        }
      } else {
        setJepaRuntimeUi(null);
      }
      if (jepaStrict && predictorMode === 'deterministic_fallback') {
        const detail = String(data?.stats?.predictor_detail || 'strict runtime violated');
        const errKey = `fallback:${detail}`;
        if (lastPredictiveErrorKeyRef.current !== errKey) {
          addToast('error', `JEPA strict mode fallback blocked: ${detail}`);
          lastPredictiveErrorKeyRef.current = errKey;
        }
        setPredictedEdges([]);
        return;
      }
      lastPredictiveErrorKeyRef.current = '';
      const rawEdges: PredictedEdgePayload[] = Array.isArray(data?.predicted_edges) ? data.predicted_edges : [];
      const mapped: DAGEdge[] = rawEdges.map((edge, idx) => ({
        id: `pred-${edge.source}-${edge.target}-${idx}`,
        source: edge.source,
        target: edge.target,
        type: 'predicted' as const,
        strength: Math.max(0.3, Math.min(1.0, Number(edge.weight ?? edge.confidence ?? 0.65))),
        relationKind: 'predicted' as const,
      })).sort((a, b) => b.strength - a.strength);
      setPredictedEdges(mapped.slice(0, 24));
    } catch (err) {
      console.warn('[MCC] Predictive overlay fetch failed:', err);
      setJepaRuntimeUi({
        title: 'JEPA Runtime: Unavailable',
        hint: err instanceof Error ? err.message : 'fetch failed',
        color: '#ef8d8d',
      });
      setPredictedEdges([]);
    }
  }, [mccReady, hasProject, navLevel, projectScopePath, roadmapNodes.length, selectedNode, selectedNodeIds, cameraLOD, addToast]);

  useEffect(() => {
    fetchPredictiveOverlay();
  }, [fetchPredictiveOverlay]);

  // MARKER_155A.P0.ONBOARDING_REBIND:
  // Legacy modal onboarding is disabled for first-run flow (FirstRunView owns setup UX).
  useEffect(() => {
    if (mccReady && !hasProject && navLevel !== 'first_run') {
      setShowOnboarding(true);
    } else if (navLevel === 'first_run') {
      setShowOnboarding(false);
    }
  }, [mccReady, hasProject, navLevel]);

  // MARKER_143.P3: Refetch DAG when selectedTaskId changes
  useEffect(() => {
    // MARKER_155A.G24.WF_SOURCE_FANOUT:
    // selectedTaskId currently fans out into 3 workflow sources:
    // (1) /api/dag task filter, (2) debug pipeline fallback, (3) workflow template fallback.
    // This is functional but increases divergence risk in inline drill rendering.
    fetchDAG(selectedTaskId);
  }, [selectedTaskId, fetchDAG]);

  // Fallback workflow source for fractal reveal when /api/dag has no detailed task.result.
  useEffect(() => {
    if (!selectedTaskId) {
      setInlineWorkflowNodes([]);
      setInlineWorkflowEdges([]);
      return;
    }
    let cancelled = false;
    fetch(`${API_BASE}/debug/pipeline-results/${encodeURIComponent(selectedTaskId)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data) => {
        if (cancelled) return;
        const subtasks = Array.isArray(data?.subtasks) ? data.subtasks : [];
        const fallback = buildInlineWorkflowFromPipeline(selectedTaskId, subtasks);
        setInlineWorkflowNodes(fallback.nodes);
        setInlineWorkflowEdges(fallback.edges);
      })
      .catch(() => {
        if (cancelled) return;
        // Always keep a default inline workflow skeleton available.
        const fallback = buildInlineWorkflowFromPipeline(selectedTaskId, []);
        setInlineWorkflowNodes(fallback.nodes);
        setInlineWorkflowEdges(fallback.edges);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedTaskId]);

  // Full workflow template fallback (default: bmad_default) when live task.result is absent/partial.
  useEffect(() => {
    if (!selectedTaskId) {
      setInlineTemplateWorkflowNodes([]);
      setInlineTemplateWorkflowEdges([]);
      return;
    }
    const selectedTask = tasks.find((t) => t.id === selectedTaskId);
    const rawWorkflowKey = String(selectedTask?.workflow_id || '').trim();
    // MARKER_155A.G24.WF_TEMPLATE_KEY_POLICY:
    // Auto-normalizing `wf_*` ids to `bmad_default` is convenient, but can hide
    // task-specific workflow intent when workflow_id encodes runtime-only identifiers.
    const workflowKey = rawWorkflowKey || 'bmad_default';

    let cancelled = false;
    const loadTemplate = async () => {
      try {
        const primary = await fetch(`${API_BASE}/mcc/workflows/${encodeURIComponent(workflowKey)}`);
        const fallback = !primary.ok && workflowKey !== 'bmad_default'
          ? await fetch(`${API_BASE}/mcc/workflows/bmad_default`)
          : null;
        const response = primary.ok ? primary : fallback;
        if (!response || !response.ok) throw new Error('template_unavailable');
        const template = await response.json();
        if (cancelled) return;
        const mapped = buildInlineWorkflowFromTemplate(selectedTaskId, template);
        setInlineTemplateWorkflowNodes(mapped.nodes);
        setInlineTemplateWorkflowEdges(mapped.edges);
      } catch {
        if (cancelled) return;
        setInlineTemplateWorkflowNodes([]);
        setInlineTemplateWorkflowEdges([]);
      }
    };

    loadTemplate();
    return () => {
      cancelled = true;
    };
  }, [selectedTaskId, tasks]);

  // P0 drill contract: workflow overlay is controlled by explicit expand/collapse state.
  useEffect(() => {
    if (navLevel !== 'roadmap') {
      setTaskDrillState('collapsed');
      return;
    }
    if (!selectedTaskId) {
      setTaskDrillState('collapsed');
      return;
    }
    // Keep explicit mode: selection alone does not auto-expand workflow.
  }, [navLevel, selectedTaskId]);

  // Listen for real-time updates via CustomEvents
  useEffect(() => {
    const triggerFetch = () => {
      const now = Date.now();
      if (now - lastFetchRef.current < DEBOUNCE_MS) return;
      lastFetchRef.current = now;

      // MARKER_155A.P2.TRIGGER_ONLY_REFRESH:
      // No periodic refresh. Coalesce event storms and refresh only on active window.
      if (!isActiveWindow()) {
        dagFetchQueuedRef.current = true;
        return;
      }
      if (dagFetchInFlightRef.current) {
        dagFetchQueuedRef.current = true;
        return;
      }

      dagFetchInFlightRef.current = true;
      fetchDAG(selectedTaskId)
        .finally(() => {
          dagFetchInFlightRef.current = false;
          if (dagFetchQueuedRef.current && isActiveWindow()) {
            dagFetchQueuedRef.current = false;
            const t = Date.now();
            lastFetchRef.current = t;
            dagFetchInFlightRef.current = true;
            fetchDAG(selectedTaskId).finally(() => {
              dagFetchInFlightRef.current = false;
            });
          }
        });
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
      // MARKER_155A.P2.TRIGGER_ONLY_REFRESH:
      // Stats telemetry is high-frequency; don't trigger DAG refetch from it.
    };

    const handleWindowBecameActive = () => {
      if (dagFetchQueuedRef.current && !dagFetchInFlightRef.current) {
        dagFetchQueuedRef.current = false;
        lastFetchRef.current = Date.now();
        dagFetchInFlightRef.current = true;
        fetchDAG(selectedTaskId).finally(() => {
          dagFetchInFlightRef.current = false;
        });
      }
    };

    window.addEventListener('task-board-updated', handleTaskBoardUpdate as EventListener);
    window.addEventListener('pipeline-activity', handlePipelineActivity as EventListener);
    window.addEventListener('pipeline-stats', handlePipelineStats as EventListener);
    document.addEventListener('visibilitychange', handleWindowBecameActive);
    window.addEventListener('focus', handleWindowBecameActive);

    return () => {
      window.removeEventListener('task-board-updated', handleTaskBoardUpdate as EventListener);
      window.removeEventListener('pipeline-activity', handlePipelineActivity as EventListener);
      window.removeEventListener('pipeline-stats', handlePipelineStats as EventListener);
      document.removeEventListener('visibilitychange', handleWindowBecameActive);
      window.removeEventListener('focus', handleWindowBecameActive);
    };
  }, [fetchDAG, isActiveWindow, pushStreamEvent, selectedTaskId]);

  // MARKER_153.5F: Level-aware effective nodes/edges
  // At roadmap level → show roadmap DAG. At tasks level → show task board DAG.
  // At workflow/running → show workflow DAG.
  const { effectiveNodes, effectiveEdges } = useMemo(() => {
    // MARKER_155A.G21.SINGLE_CANVAS_STATE:
    // Roadmap always renders architecture + full task overlay to keep topology stable.
    if (navLevel === 'roadmap' && roadmapNodes.length > 0 && tasks.length > 0) {
      const fallbackFocusNodeId =
        navRoadmapNodeId ||
        roadmapNodes.find((n) => n.graphKind === 'project_root')?.id ||
        roadmapNodes[0]?.id ||
        '__root__';
      const overlaid = overlayTasksOnRoadmap(roadmapNodes, roadmapEdges, tasks, fallbackFocusNodeId, selectedTaskId);
      return { effectiveNodes: overlaid.nodes, effectiveEdges: overlaid.edges };
    }

    if (navLevel === 'roadmap' && roadmapNodes.length > 0) {
      return { effectiveNodes: roadmapNodes, effectiveEdges: roadmapEdges };
    }
    // MARKER_155.2A: Tasks level → show tasks filtered by module from drill-down
    if (navLevel === 'tasks' && tasks.length > 0) {
      // MARKER_155A.P1.CROSSCUT_TASKS:
      // Allow complex tasks to appear in multiple roadmap branches via affected_nodes[].
      const taskMatchesRoadmapContext = (task: TaskData, roadmapNodeId: string): boolean => {
        const moduleKey = normalizePathKey(task.module);
        const nodeKey = normalizePathKey(roadmapNodeId);
        if (task.primary_node_id === roadmapNodeId) return true;
        if (task.module === roadmapNodeId) return true;
        if (moduleKey && nodeKey && (moduleKey.endsWith(`/${nodeKey}`) || nodeKey.endsWith(`/${moduleKey}`))) return true;
        if (task.tags?.includes(roadmapNodeId)) return true;
        if (task.affected_nodes?.includes(roadmapNodeId)) return true;
        return !task.module && !task.primary_node_id && (!task.affected_nodes || task.affected_nodes.length === 0);
      };

      const filtered = navRoadmapNodeId
        ? tasks.filter(t => taskMatchesRoadmapContext(t, navRoadmapNodeId))
        : tasks;
      const displayTasks = filtered.length > 0 ? filtered : tasks;
      // Find module label from roadmap data for tree root
      const moduleNode = roadmapNodes.find(n => n.id === navRoadmapNodeId);
      const moduleLabel = moduleNode?.label || navRoadmapNodeId;
      const { nodes, edges } = tasksToDAG(displayTasks, {
        moduleId: navRoadmapNodeId,
        moduleLabel,
      });
      return { effectiveNodes: nodes, effectiveEdges: edges };
    }
    // Workflow / running / results levels — use workflow DAG data
    if (dagNodes.length > 0) {
      return { effectiveNodes: dagNodes, effectiveEdges: dagEdges };
    }
    // Fallback: test DAG data when nothing loaded
    const testData = createTestDAGData();
    return { effectiveNodes: testData.nodes, effectiveEdges: testData.edges };
  }, [navLevel, navRoadmapNodeId, roadmapNodes, roadmapEdges, dagNodes, dagEdges, tasks]);

  const effectiveEdgesWithPredicted = useMemo(() => {
    if (navLevel !== 'roadmap') return effectiveEdges;

    // MARKER_155.P1.TOPOLOGY_DEFAULT:
    // Base roadmap view is topology-first, but keep task->task dependency edges stable.
    const topologyEdges = effectiveEdges.filter(e => e.type === 'structural');
    const focusIds = new Set<string>(
      selectedNodeIds.length > 0
        ? selectedNodeIds
        : selectedNode
          ? [selectedNode]
          : []
    );
    if (focusIds.size === 0) return topologyEdges;

    const nodeIds = new Set(effectiveNodes.map(n => n.id));
    const baseIds = new Set(topologyEdges.map(e => e.id));
    const basePairs = new Set(topologyEdges.map(e => `${e.source}->${e.target}`));
    const selectedNeighbors = new Set<string>(focusIds);
    for (const e of topologyEdges) {
      if (focusIds.has(e.source)) selectedNeighbors.add(e.target);
      if (focusIds.has(e.target)) selectedNeighbors.add(e.source);
    }

    // Base dependency edges from current graph are focus-only.
    const baseDependencyOverlay = effectiveEdges
      .filter(e =>
        e.type === 'dependency' &&
        (focusIds.has(e.source) || focusIds.has(e.target)) &&
        !basePairs.has(`${e.source}->${e.target}`) &&
        !baseIds.has(e.id),
      )
      .slice(0, 12);

    const crossOverlay = (roadmapCrossEdges || [])
      .filter(e =>
        nodeIds.has(e.source) &&
        nodeIds.has(e.target) &&
        (focusIds.has(e.source) || focusIds.has(e.target)) &&
        !basePairs.has(`${e.source}->${e.target}`) &&
        !baseIds.has(e.id),
      )
      .sort((a, b) => (b.strength || 0) - (a.strength || 0))
      .slice(0, 10);

    if (predictedEdges.length === 0) {
      if (crossOverlay.length === 0 && baseDependencyOverlay.length === 0) return topologyEdges;
      return [...topologyEdges, ...baseDependencyOverlay, ...crossOverlay];
    }

    const overlay = predictedEdges.filter(e =>
      nodeIds.has(e.source) &&
      nodeIds.has(e.target) &&
      selectedNeighbors.has(e.source) &&
      selectedNeighbors.has(e.target) &&
      (focusIds.has(e.source) || focusIds.has(e.target)) &&
      !basePairs.has(`${e.source}->${e.target}`) &&
      !baseIds.has(e.id),
    ).slice(0, 16);

    if (overlay.length === 0 && crossOverlay.length === 0 && baseDependencyOverlay.length === 0) return topologyEdges;
    return [...topologyEdges, ...baseDependencyOverlay, ...crossOverlay, ...overlay];
  }, [effectiveEdges, effectiveNodes, predictedEdges, navLevel, selectedNode, selectedNodeIds, roadmapCrossEdges]);

  // MARKER_155.G1.TASK_ANCHORING_CONTRACT_V1:
  // Keep MiniTasks selection and roadmap task_overlay node selection synchronized.
  useEffect(() => {
    if (navLevel !== 'roadmap') return;
    if (!selectedTaskId) return;
    const overlayId = `task_overlay_${selectedTaskId}`;
    if (!effectiveNodes.some((n) => n.id === overlayId)) return;
    setSelectedNode((prev) => (prev === overlayId ? prev : overlayId));
    setSelectedNodeIds((prev) => (sameIds(prev, [overlayId]) ? prev : [overlayId]));
    setFocusedNodeId(overlayId);
    setFocusRestoreSource('current');
  }, [effectiveNodes, navLevel, selectedTaskId, setFocusRestoreSource, setFocusedNodeId]);

  const focusIdsForView = useMemo(
    () => new Set<string>(
      selectedNodeIds.length > 0
        ? selectedNodeIds
        : selectedNode
          ? [selectedNode]
          : [],
    ),
    [selectedNode, selectedNodeIds],
  );

  const isInlineWorkflowFocus =
    navLevel === 'roadmap' &&
    taskDrillState === 'expanded' &&
    Boolean(selectedTaskId);

  const graphForView = useMemo(() => {
    let roadmapNodeExpanded = { nodes: effectiveNodes, edges: effectiveEdgesWithPredicted };
    if (
      navLevel === 'roadmap' &&
      roadmapNodeDrillState === 'expanded' &&
      roadmapDrillNodeId &&
      !roadmapDrillNodeId.startsWith('task_overlay_')
    ) {
      roadmapNodeExpanded = overlayRoadmapNodeChildren(
        effectiveNodes,
        effectiveEdgesWithPredicted,
        roadmapDrillNodeId,
      );
    }

    if (isInlineWorkflowFocus && selectedTaskId) {
      // MARKER_155A.G24.WF_SOURCE_ARBITRATION:
      // Explicit source priority:
      // 1) detailed DAG result, 2) workflow template, 3) pipeline fallback.
      const selectedWorkflow = selectInlineWorkflowSource(
        selectedTaskId,
        dagNodes,
        dagEdges,
        inlineTemplateWorkflowNodes,
        inlineTemplateWorkflowEdges,
        inlineWorkflowNodes,
        inlineWorkflowEdges,
      );

      return overlayWorkflowOnSelectedTask(
        roadmapNodeExpanded.nodes,
        roadmapNodeExpanded.edges,
        selectedWorkflow.nodes,
        selectedWorkflow.edges,
        selectedTaskId,
      );
    }

    if (navLevel !== 'roadmap' || focusDisplayMode === 'all' || focusIdsForView.size === 0) {
      return roadmapNodeExpanded;
    }

    // MARKER_155A.P0.WF_STABLE_CONTEXT:
    // Roadmap must keep full architecture context visible while selecting nodes.
    // Selection still drives highlight, but not graph clipping.
    if (navLevel === 'roadmap') {
      return roadmapNodeExpanded;
    }

    const neighborIds = new Set<string>(focusIdsForView);
    for (const e of effectiveEdgesWithPredicted) {
      if (focusIdsForView.has(e.source)) neighborIds.add(e.target);
      if (focusIdsForView.has(e.target)) neighborIds.add(e.source);
    }

    const visibleIds = focusDisplayMode === 'selected_only' ? focusIdsForView : neighborIds;
    const nodes = roadmapNodeExpanded.nodes.filter(n => visibleIds.has(n.id));
    const edges = roadmapNodeExpanded.edges.filter(e => visibleIds.has(e.source) && visibleIds.has(e.target));
    return { nodes, edges };
  }, [
    effectiveEdgesWithPredicted,
    effectiveNodes,
    focusDisplayMode,
    focusIdsForView,
    roadmapDrillNodeId,
    roadmapNodeDrillState,
    isInlineWorkflowFocus,
    navLevel,
    selectedTaskId,
    taskDrillState,
  ]);

  // MARKER_155.P4.FOCUS_ACROSS_ZOOM:
  // Keep multi-focus stable across drill/zoom transitions, drop stale ids only.
  useEffect(() => {
    const liveIds = new Set(effectiveNodes.map(n => n.id));
    setSelectedNodeIds(prev => {
      const filtered = prev.filter(id => liveIds.has(id));
      return sameIds(prev, filtered) ? prev : filtered;
    });
    if (selectedNode && !liveIds.has(selectedNode)) {
      setSelectedNode(null);
    }
  }, [effectiveNodes, selectedNode]);

  // MARKER_155.P4_2.FOCUS_MEMORY:
  // Persist focus context per LOD scope key and restore after drill/zoom transitions.
  useEffect(() => {
    if (navLevel === 'first_run' || isRestoringFocusRef.current) return;
    const ids = selectedNodeIds.length > 0
      ? selectedNodeIds
      : selectedNode
        ? [selectedNode]
        : [];
    const normalized = uniqueIds(ids);
    if (normalized.length === 0) return;
    focusMemoryRef.current[focusScopeKey] = normalized;
  }, [focusScopeKey, navLevel, selectedNode, selectedNodeIds]);

  useEffect(() => {
    if (navLevel === 'first_run') return;
    const liveIds = new Set(effectiveNodes.map(n => n.id));
    if (liveIds.size === 0) return;
    const current = uniqueIds([
      ...selectedNodeIds.filter(id => liveIds.has(id)),
      selectedNode && liveIds.has(selectedNode) ? selectedNode : null,
    ]);
    const saved = uniqueIds((focusMemoryRef.current[focusScopeKey] || []).filter(id => liveIds.has(id)));

    // Explicit user clear (pane click) must remain empty; do not auto-select defaults.
    if (current.length === 0 && saved.length === 0) return;

    const orderedCandidates: Array<{ source: FocusRestoreSource; ids: string[] }> = focusRestorePolicy === 'scope_first'
      ? [
        { source: 'memory', ids: saved },
        { source: 'current', ids: current },
      ]
      : [
        { source: 'current', ids: current },
        { source: 'memory', ids: saved },
      ];
    const picked = orderedCandidates.find(candidate => candidate.ids.length > 0);
    if (!picked) return;

    const nextIds = picked.ids;
    const nextPrimary = nextIds[0] || null;
    if (picked.source === 'current') {
      if (!sameIds(selectedNodeIds, nextIds)) {
        setSelectedNodeIds(nextIds);
      }
      if (selectedNode !== nextPrimary) {
        setSelectedNode(nextPrimary);
        setFocusedNodeId(nextPrimary);
      }
      if (focusRestoreSource !== 'current') {
        setFocusRestoreSource('current');
      }
      return;
    }

    const shouldUpdateIds = !sameIds(selectedNodeIds, nextIds);
    const shouldUpdatePrimary = selectedNode !== nextPrimary;
    const shouldUpdateSource = focusRestoreSource !== picked.source;
    if (!shouldUpdateIds && !shouldUpdatePrimary && !shouldUpdateSource) {
      return;
    }

    isRestoringFocusRef.current = true;
    if (shouldUpdateIds) {
      setSelectedNodeIds(nextIds);
    }
    if (shouldUpdatePrimary) {
      setSelectedNode(nextPrimary);
      setFocusedNodeId(nextPrimary);
    }
    if (shouldUpdateSource) {
      setFocusRestoreSource(picked.source);
    }
    queueMicrotask(() => {
      isRestoringFocusRef.current = false;
    });
  }, [
    focusRestorePolicy,
    focusRestoreSource,
    focusScopeKey,
    navLevel,
    navRoadmapNodeId,
    effectiveNodes,
    selectedNode,
    selectedNodeIds,
    setFocusRestoreSource,
    setFocusedNodeId,
  ]);

  // MARKER_155.1A: Read-only levels (no DAG editing — roadmap + tasks)
  const isReadOnlyLevel = navLevel === 'roadmap' || navLevel === 'tasks';

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
    if (navLevel === 'roadmap' && target.kind !== 'node') {
      setContextMenuTarget(null);
      return;
    }
    setNodePickerPos(null);
    if (target.kind === 'canvas') {
      setContextMenuTarget({ kind: 'canvas', position: target.position });
    } else if (target.kind === 'node' && target.id) {
      setContextMenuTarget({ kind: 'node', nodeId: target.id, position: target.position });
    } else if (target.kind === 'edge' && target.id) {
      setContextMenuTarget({ kind: 'edge', edgeId: target.id, position: target.position });
    }
  }, [navLevel]);

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

  const handleCreateTaskFromNode = useCallback(async (nodeId: string) => {
    if (nodeId.startsWith('task_overlay_')) {
      addToast('info', 'Task node already exists for this anchor');
      return;
    }
    const sourceNode = graphForView.nodes.find((n) => n.id === nodeId);
    if (!sourceNode) {
      addToast('error', `Anchor node not found: ${nodeId}`);
      return;
    }
    const suggestedTitle = `Fix ${sourceNode.label}`;
    const title = window.prompt('Task title', suggestedTitle)?.trim();
    if (!title) return;
    const store = useMCCStore.getState();
    const preset = store.activePreset || 'dragon_silver';
    const phaseType = preset.startsWith('titan') ? 'research' : 'build';
    const tags = [preset.startsWith('titan') ? 'titan' : 'dragon', 'anchored'];
    const metadata = (sourceNode.metadata || {}) as Record<string, any>;
    const moduleHint = String(sourceNode.projectNodeId || metadata.path || metadata.file_path || sourceNode.id || '');
    const taskId = await store.addTask(title, preset, phaseType, tags, undefined, {
      module: moduleHint,
      primary_node_id: sourceNode.id,
      affected_nodes: [sourceNode.id],
      workflow_id: `wf_anchor_${Date.now()}`,
      team_profile: preset,
      task_origin: 'manual',
      source: 'mcc_anchor',
    });
    if (!taskId) {
      addToast('error', 'Failed to create anchored task');
      return;
    }
    store.selectTask(taskId);
    addToast('success', `Task anchored: ${sourceNode.label}`);
  }, [addToast, graphForView.nodes]);

  const handleApproveSuggestedAnchor = useCallback(async (taskOverlayNodeId: string) => {
    if (!taskOverlayNodeId.startsWith('task_overlay_')) return;
    const taskId = taskOverlayNodeId.replace(/^task_overlay_/, '');
    const taskNode = graphForView.nodes.find((n) => n.id === taskOverlayNodeId);
    if (!taskNode) return;
    const suggested = Array.isArray(taskNode.anchorNodeIds) ? taskNode.anchorNodeIds[0] : null;
    if (!suggested) {
      addToast('error', 'No suggested anchor found');
      return;
    }
    const anchorNode = graphForView.nodes.find((n) => n.id === suggested);
    const anchorMeta: any = anchorNode?.metadata || {};
    const moduleHint = String(anchorNode?.projectNodeId || anchorMeta.path || anchorMeta.file_path || suggested);
    try {
      const res = await fetch(`${API_BASE}/debug/task-board/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          primary_node_id: suggested,
          affected_nodes: [suggested],
          module: moduleHint,
          task_origin: 'manual',
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await useMCCStore.getState().fetchTasks();
      addToast('success', 'Suggested anchor approved');
    } catch {
      addToast('error', 'Failed to approve suggested anchor');
    }
  }, [addToast, graphForView.nodes]);

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

  // MARKER_153.5E: Handle node click based on current level
  const handleLevelAwareNodeSelect = useCallback((nodeId: string | null, options?: { additive?: boolean }) => {
    const additive = !!options?.additive;

    if (!nodeId) {
      // Explicit deselect (pane click): clear focus memory for current scope
      // so auto-restore does not immediately reselect old nodes.
      focusMemoryRef.current[focusScopeKey] = [];
      setSelectedNode(null);
      setSelectedNodeIds([]);
      setFocusedNodeId(null);
      setFocusRestoreSource(null);
      return;
    }

    if (additive) {
      setSelectedNode(nodeId);
      setFocusedNodeId(nodeId);
      setSelectedNodeIds(prev => {
        if (prev.includes(nodeId)) {
          const next = prev.filter(id => id !== nodeId);
          return next;
        }
        return [...prev, nodeId];
      });
    } else {
      setSelectedNode(nodeId);
      setSelectedNodeIds([nodeId]);
      setFocusedNodeId(nodeId);
    }
    setFocusRestoreSource('current');

    if (nodeId.startsWith('task_overlay_')) {
      const taskId = nodeId.replace('task_overlay_', '');
      selectTask(taskId);
    }
  }, [focusScopeKey, selectTask, setFocusRestoreSource, setFocusedNodeId]);

  const handleLevelAwareNodeDoubleClick = useCallback((nodeId: string) => {
    if (navLevel === 'roadmap') {
      // Roadmap: workflow drill is explicit on double-click for task overlays.
      if (nodeId.startsWith('task_overlay_')) {
        const taskId = nodeId.replace('task_overlay_', '');
        if (!taskId) return;
        // MARKER_155A.G24.DRILL_TOGGLE_SINGLE_SOURCE:
        // Task drill toggle is intentionally controlled here (single source of truth),
        // avoiding hidden zoom-trigger side effects.
        selectTask(taskId);
        setTaskDrillState((prev) => (selectedTaskId === taskId && prev === 'expanded' ? 'collapsed' : 'expanded'));
        return;
      }
      // MARKER_155A.G23.NODE_DRILL_NEXT_DEPTH:
      // Non-task roadmap node drill (folder/module matryoshka).
      const isSameExpanded = roadmapDrillNodeId === nodeId && roadmapNodeDrillState === 'expanded';
      setRoadmapDrillNodeId(isSameExpanded ? null : nodeId);
      setRoadmapNodeDrillState(isSameExpanded ? 'collapsed' : 'expanded');
      return;
    } else if (navLevel === 'tasks') {
      // MARKER_155.2A: Ignore virtual tree nodes (root + branches), only drill real tasks
      if (nodeId.startsWith('__')) return;
      selectTask(nodeId);
      drillDown('workflow', { taskId: nodeId });
    }
    // Other levels: workflow level uses existing DAG editor behavior
  }, [navLevel, selectTask, drillDown, selectedTaskId, roadmapDrillNodeId, roadmapNodeDrillState]);

  // Handle edge selection
  const handleEdgeSelect = useCallback((edgeId: string | null) => {
    if (!edgeId) {
      setSelectedEdge(null);
      return;
    }
    const edge = effectiveEdgesWithPredicted.find(e => e.id === edgeId);
    if (edge) {
      setSelectedEdge({ id: edge.id, source: edge.source, target: edge.target, type: edge.type });
    }
  }, [effectiveEdgesWithPredicted]);

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
  // MARKER_154.3A: Commented out — WorkflowToolbar removed. Will restore in Wave 4 for MiniChat.
  /*
  const handleGeneratedWorkflow = useCallback(async (workflow: any) => {
    if (!workflow?.nodes?.length) return;
    if (!editMode) toggleEditMode();
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
  */

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

  // MARKER_153.6B: Level-aware keyboard shortcuts via hook (replaces basic Esc/Enter)
  useKeyboardShortcuts({
    // MARKER_155A.P2.DRILL_POLICY: Drill command respects current level in one canvas.
    onDrillNode: selectedNode ? () => handleLevelAwareNodeDoubleClick(selectedNode) : undefined,
    onDrillTask: () => {
      if (selectedNode) handleLevelAwareNodeDoubleClick(selectedNode);
      else if (selectedTaskId && navLevel === 'roadmap') {
        setTaskDrillState((prev) => (prev === 'expanded' ? 'collapsed' : 'expanded'));
      } else if (selectedTaskId) {
        drillDown('workflow', { taskId: selectedTaskId });
      }
    },
    onExecute: handleExecute,
    onToggleEdit: () => toggleEditMode(),
    onExpandStream: () => setShowStream(!showStream),
    // onStop, onApply, onReject — wired when pipeline control is available
  });

  const sendFocusToArchitect = useCallback(() => {
    const focus = selectedNodeIds.length > 0
      ? selectedNodeIds
      : selectedNode
        ? [selectedNode]
        : [];
    if (focus.length === 0) return false;
    const message = `Analyze focused nodes and dependencies: ${focus.join(', ')}\nContext: level=${navLevel}, lod=${cameraLOD}, focus_mode=${focusDisplayMode}, scope=${focusScopeKey}`;
    window.dispatchEvent(new CustomEvent('mcc-chat-prefill', {
      detail: {
        message,
        context: {
          focused_node_ids: focus,
          nav_level: navLevel,
          camera_lod: cameraLOD,
          focus_display_mode: focusDisplayMode,
          focus_scope_key: focusScopeKey,
        },
      },
    }));
    addToast('info', `Architect focus sent (${focus.length} node${focus.length > 1 ? 's' : ''})`);
    return true;
  }, [selectedNode, selectedNodeIds, addToast, navLevel, cameraLOD, focusDisplayMode, focusScopeKey]);

  // MARKER_155.P4.MULTISELECT_ACTION:
  // Shift+Enter sends focused multi-node context to Architect chat as a concrete action.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (!(e.key === 'Enter' && e.shiftKey)) return;
      if (!sendFocusToArchitect()) return;
      e.preventDefault();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [sendFocusToArchitect]);

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
        position: 'relative',
      }}
    >
      <button
        onClick={() => setDebugMode((v) => !v)}
        title={debugMode ? 'Disable debug UI' : 'Enable debug UI'}
        style={{
          position: 'absolute',
          top: 8,
          right: 8,
          zIndex: 40,
          width: 30,
          height: 30,
          border: `1px solid ${debugMode ? '#ffffff' : NOLAN_PALETTE.borderDim}`,
          borderRadius: 4,
          background: '#000000',
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          padding: 0,
        }}
        aria-label="Toggle debug mode"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <rect x="1.5" y="1.5" width="9" height="9" stroke="white" strokeWidth="1" />
          <line x1="3" y1="6" x2="9" y2="6" stroke="white" strokeWidth="1" />
        </svg>
      </button>

      {/* ═══ MARKER_155.CLEANUP: Header removed — using FooterActionBar instead ═══ */}
      
      {/* ═══ MARKER_153.5A: Breadcrumb Bar — navigation path ═══ */}
      {navLevel === 'workflow' || navLevel === 'running' || navLevel === 'results' ? <MCCBreadcrumb /> : null}

      {/* ═══ MARKER_155.FLOW.STEPS: 5-step progress indicator ═══ */}
      {debugMode && (
        <div data-onboarding="step-indicator">
          <StepIndicator />
        </div>
      )}
      {/* MARKER_155A.G21.PLAYGROUND_ENTRY: Always-available playground entry for existing projects. */}
      {debugMode && hasProject && navLevel !== 'first_run' && (
        <div style={{ position: 'absolute', top: 44, right: 14, zIndex: 20 }}>
          <PlaygroundBadge />
        </div>
      )}

      {/* ═══ MARKER_154.3A: WorkflowToolbar REMOVED from layout (Phase 154).
            Actions moved to FooterActionBar + gear popup.
            File kept for reference. ═══ */}

      {/* ═══ MAIN LAYOUT: Single column with floating mini-windows ═══ */}
      {/* MARKER_155.CLEANUP: Removed side panels — using MiniChat, MiniTasks, MiniStats instead */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
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
          {/* MARKER_155.CLEANUP: CaptainBar removed from top — integrated into FooterActionBar notifications */}

          {/* MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.UI_TABS.V1:
              Debug-stage DAG variants (baseline + saved versions). */}
          {debugMode && hasProject && navLevel === 'roadmap' && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 8px',
                borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
                background: 'rgba(255,255,255,0.02)',
                fontSize: 9,
                flexShrink: 0,
                overflowX: 'auto',
              }}
            >
              <button
                onClick={() => setActiveDagVersionId(null)}
                style={{
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 3,
                  background: activeDagVersionId === null ? 'rgba(126, 231, 196, 0.15)' : '#141414',
                  color: activeDagVersionId === null ? '#baf7e4' : '#9ca3ad',
                  padding: '2px 8px',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
                title="Use live baseline DAG"
              >
                baseline
              </button>
              {dagVersions.map(v => (
                <div key={v.version_id} style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <button
                    onClick={() => setActiveDagVersionId(v.version_id)}
                    style={{
                      border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                      borderRadius: 3,
                      background: activeDagVersionId === v.version_id ? 'rgba(142, 203, 255, 0.16)' : '#141414',
                      color: activeDagVersionId === v.version_id ? '#c6e7ff' : '#9ca3ad',
                      padding: '2px 8px',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                    }}
                    title={`${v.name} · nodes=${v.node_count} edges=${v.edge_count} · decision=${v.decision || '-'}`}
                  >
                    {v.name}
                  </button>
                  <button
                    onClick={() => setPrimaryDagVersion(v.version_id)}
                    style={{
                      border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                      borderRadius: 3,
                      background: v.is_primary ? 'rgba(127, 231, 196, 0.16)' : '#111',
                      color: v.is_primary ? '#8cf4d4' : '#67707c',
                      padding: '2px 5px',
                      cursor: 'pointer',
                    }}
                    title="Set as primary DAG version"
                  >
                    ★
                  </button>
                </div>
              ))}
              <button
                onClick={runDagAutoCompare}
                style={{
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 3,
                  background: '#141414',
                  color: '#f0cf7a',
                  padding: '2px 8px',
                  cursor: dagCompareLoading ? 'wait' : 'pointer',
                  whiteSpace: 'nowrap',
                  marginLeft: 2,
                  opacity: dagCompareLoading ? 0.7 : 1,
                }}
                title="Run algorithmic DAG auto-compare (3 presets)"
                disabled={dagCompareLoading}
              >
                {dagCompareLoading ? 'comparing…' : 'auto-compare'}
              </button>
              <button
                onClick={() => setShowDagCompareMatrix(v => !v)}
                style={{
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 3,
                  background: showDagCompareMatrix ? 'rgba(142, 203, 255, 0.16)' : '#141414',
                  color: showDagCompareMatrix ? '#c6e7ff' : '#7a8a9c',
                  padding: '2px 8px',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  marginLeft: 2,
                  opacity: dagCompareRows.length > 0 ? 1 : 0.65,
                }}
                title="Show compare matrix"
                disabled={dagCompareRows.length === 0}
              >
                matrix
              </button>
              <button
                onClick={createDagSnapshot}
                style={{
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 3,
                  background: '#141414',
                  color: '#8ecbff',
                  padding: '2px 8px',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  marginLeft: 2,
                }}
                title="Save current DAG as version"
              >
                + snapshot
              </button>
              {dagVersionsLoading && <span style={{ color: '#666', marginLeft: 4 }}>loading…</span>}
              {dagVersionsError && <span style={{ color: '#aa7373', marginLeft: 4 }}>{dagVersionsError}</span>}
              {dagCompareBest && (
                <span style={{ color: '#7a8a9c', marginLeft: 6, whiteSpace: 'nowrap' }}>
                  best: {dagCompareBest.name} ({dagCompareBest.score.toFixed(1)})
                </span>
              )}
              {dagCompareBest?.version_id && (
                <button
                  onClick={() => setPrimaryDagVersion(dagCompareBest.version_id)}
                  style={{
                    border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                    borderRadius: 3,
                    background: '#111',
                    color: '#8cf4d4',
                    padding: '2px 8px',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    marginLeft: 2,
                  }}
                  title="Set best compare result as primary DAG version"
                >
                  promote best
                </button>
              )}
              {dagCompareError && <span style={{ color: '#aa7373', marginLeft: 4 }}>{dagCompareError}</span>}
              {!dagCompareError && dagCompareRows.length > 0 && (
                <span
                  style={{ color: '#58606c', marginLeft: 4, whiteSpace: 'nowrap' }}
                  title={dagCompareRows
                    .map((r) => `${r.name}:${Number(r?.scorecard?.score || 0).toFixed(1)}${r.error ? ' [err]' : ''}`)
                    .join(' | ')}
                >
                  {dagCompareRows.length} variants
                </span>
              )}
            </div>
          )}
          {debugMode && hasProject && navLevel === 'roadmap' && showDagCompareMatrix && dagCompareRows.length > 0 && (
            <div
              style={{
                borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
                background: 'rgba(8, 10, 12, 0.92)',
                padding: '6px 8px',
                fontSize: 9,
                color: '#95a0ad',
                flexShrink: 0,
              }}
            >
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'minmax(120px,1fr) 56px 58px 48px 48px 52px 52px 120px 56px',
                  gap: 6,
                  padding: '0 2px 4px 2px',
                  borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  color: '#6f7b88',
                  letterSpacing: '0.04em',
                  textTransform: 'uppercase',
                }}
              >
                <span>variant</span>
                <span>score</span>
                <span>decision</span>
                <span>nodes</span>
                <span>edges</span>
                <span>orph</span>
                <span>dens</span>
                <span>version</span>
                <span>action</span>
              </div>
              {dagCompareRows.map((row) => {
                const sc = row.scorecard || {};
                const vid = String(row.version_id || '');
                const score = Number(sc.score || 0);
                const active = Boolean(vid && activeDagVersionId === vid);
                return (
                  <div
                    key={`${row.name}:${vid || 'none'}`}
                    onClick={() => setSelectedDagCompareName(row.name)}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'minmax(120px,1fr) 56px 58px 48px 48px 52px 52px 120px 56px',
                      gap: 6,
                      padding: '3px 2px',
                      borderBottom: '1px dashed rgba(255,255,255,0.06)',
                      alignItems: 'center',
                      background:
                        selectedDagCompareName === row.name
                          ? 'rgba(240, 207, 122, 0.08)'
                          : active
                            ? 'rgba(142, 203, 255, 0.09)'
                            : 'transparent',
                      cursor: 'pointer',
                    }}
                    title={row.error || ''}
                  >
                    <span style={{ color: row.error ? '#aa7373' : '#c5d0dd' }}>{row.name}</span>
                    <span style={{ color: '#9eb9d6' }}>{score.toFixed(1)}</span>
                    <span style={{ color: sc.decision === 'pass' ? '#7fe7c4' : sc.decision === 'warn' ? '#f0cf7a' : '#ef8d8d' }}>
                      {String(sc.decision || '-')}
                    </span>
                    <span>{Number(sc.node_count || 0)}</span>
                    <span>{Number(sc.edge_count || 0)}</span>
                    <span>{Number(sc.orphan_rate || 0).toFixed(2)}</span>
                    <span>{Number(sc.density || 0).toFixed(2)}</span>
                    <button
                      onClick={() => vid && setActiveDagVersionId(vid)}
                      disabled={!vid}
                      style={{
                        border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                        borderRadius: 3,
                        background: vid ? '#121417' : '#101010',
                        color: vid ? (active ? '#c6e7ff' : '#9ca3ad') : '#59616c',
                        padding: '1px 6px',
                        cursor: vid ? 'pointer' : 'default',
                        textAlign: 'left',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {vid ? vid.slice(0, 14) : '-'}
                    </button>
                    <button
                      onClick={() => vid && setPrimaryDagVersion(vid)}
                      disabled={!vid}
                      style={{
                        border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                        borderRadius: 3,
                        background: '#111',
                        color: vid ? '#8cf4d4' : '#59616c',
                        padding: '1px 6px',
                        cursor: vid ? 'pointer' : 'default',
                      }}
                      title="Set version as primary"
                    >
                      ★
                    </button>
                  </div>
                );
              })}
              {selectedDagCompareRow && (
                <div
                  style={{
                    marginTop: 6,
                    padding: '6px 8px',
                    border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                    borderRadius: 4,
                    color: '#8e98a6',
                    background: 'rgba(255,255,255,0.02)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    flexWrap: 'wrap',
                  }}
                >
                  <span style={{ color: '#c5d0dd' }}>
                    {selectedDagCompareRow.name}
                  </span>
                  <span>
                    max_nodes={Number(selectedDagCompareRow.variant_params?.max_nodes || 0)}
                  </span>
                  <span>
                    min_conf={Number(selectedDagCompareRow.variant_params?.min_confidence || 0).toFixed(2)}
                  </span>
                  <span>
                    overlay={selectedDagCompareRow.variant_params?.use_predictive_overlay ? 'on' : 'off'}
                  </span>
                  <span>
                    max_pred={Number(selectedDagCompareRow.variant_params?.max_predicted_edges || 0)}
                  </span>
                  {selectedDagCompareRow.error && (
                    <span style={{ color: '#aa7373' }}>
                      err={selectedDagCompareRow.error}
                    </span>
                  )}
                </div>
              )}
            </div>
          )}

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

          {/* DAG View — level-aware rendering + MARKER_154.5A transition */}
          <div style={{ flex: 1, minHeight: 0, position: 'relative' }} data-onboarding="dag-canvas">
            <ReactFlowProvider>
              <MatryoshkaTransition navLevel={navLevel} inPlace>
                {/* MARKER_154.16A: First Run — show welcome screen instead of DAG */}
                {navLevel === 'first_run' ? (
                  <FirstRunView />
                ) : (loading || roadmap.loading) ? (
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
                    {navLevel === 'roadmap' ? 'Loading Roadmap...' : navLevel === 'tasks' ? 'Loading Tasks...' : 'Loading DAG...'}
                  </div>
                ) : (
                  <DAGView
                    ref={dagViewRef}
                    dagNodes={graphForView.nodes}
                    dagEdges={graphForView.edges}
                    selectedNode={selectedNode}
                    selectedNodeIds={selectedNodeIds}
                    onNodeSelect={handleLevelAwareNodeSelect}
                    onNodeSelectWithMode={(nodeId, opts) => handleLevelAwareNodeSelect(nodeId, { additive: opts.additive })}
                    onEdgeSelect={handleEdgeSelect}
                    initialCamera={cameraPosition}
                    onCameraChange={(camera, lod) => {
                      setCameraPosition(camera);
                      setCameraLOD(lod);
                    }}
                    onLODChange={(lod) => setCameraLOD(lod)}
                    graphIdentity={dagGraphIdentity}
                    layoutMode={navLevel === 'roadmap' ? 'architecture' : navLevel === 'tasks' ? 'tasks' : 'workflow'}
                    layoutBiasProfile={layoutBiasProfile}
                    pinnedPositions={pinnedPositions}
                    onPinnedPositionsChange={(positions) => {
                      setLayoutPinsForKey(dagGraphIdentity, positions);

                      // MARKER_155A.P2_1.PIN_FEEDBACK_LOOP:
                      // Temporarily disabled: real-time profile retrain on drag causes edge jitter
                      // (lines "fly away then back"). Keep only explicit pin persistence.
                    }}
                    // test compatibility marker: navLevel === 'roadmap' ? false : editMode
                    editMode={navLevel === 'roadmap' ? false : (navLevel === 'tasks' ? false : editMode)}
                    onConnect={isReadOnlyLevel ? undefined : dagEditor.handleConnect}
                    onNodesDelete={isReadOnlyLevel ? undefined : (deletedNodes) => deletedNodes.forEach(n => dagEditor.removeNode(n.id))}
                    onEdgesDelete={isReadOnlyLevel ? undefined : (deletedEdges) => deletedEdges.forEach(e => dagEditor.removeEdge(e.id))}
                    onContextMenu={navLevel === 'roadmap' || !isReadOnlyLevel ? handleContextMenu : undefined}
                    contextMenuEnabled={navLevel === 'roadmap' ? true : editMode}
                    onPaneDoubleClick={isReadOnlyLevel
                      ? undefined
                      : handlePaneDoubleClick
                    }
                    onNodeDoubleClick={handleLevelAwareNodeDoubleClick}
                    compact={navLevel === 'tasks'}
                  />
                )}
              </MatryoshkaTransition>
            </ReactFlowProvider>

            {/* MARKER_154.11A: Mini-windows — floating overlays in DAG canvas */}
            {navLevel !== 'first_run' && (
              <>
                <div data-onboarding="mini-chat">
                  <MiniChat />
                </div>
                <MiniTasks />
                <MiniStats />
                <MiniBalance />
              </>
            )}

            {/* MARKER_153.5G + 155.1A: Double-click hint at roadmap and tasks levels */}
            {(navLevel === 'roadmap' || navLevel === 'tasks') && effectiveNodes.length > 0 && selectedNode && (
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
                Press <span style={{ color: NOLAN_PALETTE.textAccent, fontWeight: 600 }}>Enter</span> to drill into {selectedNode?.startsWith('task_overlay_') ? 'workflow' : navLevel === 'roadmap' ? 'module' : 'task'}
              </div>
            )}

            {/* MARKER_155A.P2.LOD_THRESHOLDS: Context hint tied to camera LOD (same canvas, no route switch). */}
            {debugMode && navLevel !== 'first_run' && (
              <div
                style={{
                  position: 'absolute',
                  top: 8,
                  left: 8,
                  background: 'rgba(0,0,0,0.65)',
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 4,
                  padding: '2px 8px',
                  fontSize: 9,
                  color: '#8f9399',
                  textTransform: 'uppercase',
                  letterSpacing: 0.45,
                  pointerEvents: 'none',
                  zIndex: 9,
                }}
              >
                Zoom Context: {cameraLOD}
              </div>
            )}

            {debugMode && navLevel === 'roadmap' && (
              <div
                style={{
                  position: 'absolute',
                  top: 30,
                  left: 8,
                  background: 'rgba(0,0,0,0.65)',
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 4,
                  padding: '2px 8px',
                  fontSize: 9,
                  color: '#8f9399',
                  textTransform: 'uppercase',
                  letterSpacing: 0.45,
                  pointerEvents: 'none',
                  zIndex: 9,
                }}
              >
                Focus View: {focusDisplayMode === 'all' ? 'all' : focusDisplayMode === 'selected_deps' ? 'selected+deps' : 'selected-only'}
              </div>
            )}

            {debugMode && navLevel === 'roadmap' && (
              <div
                style={{
                  position: 'absolute',
                  top: 52,
                  left: 8,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  background: 'rgba(0,0,0,0.65)',
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 4,
                  padding: '2px 6px',
                  zIndex: 9,
                  fontFamily: 'monospace',
                }}
              >
                <button
                  onClick={() => {
                    const next = focusRestorePolicy === 'selection_first' ? 'scope_first' : 'selection_first';
                    setFocusRestorePolicy(next);
                    addToast('info', `Focus restore policy: ${next === 'scope_first' ? 'scope-first' : 'selection-first'}`);
                  }}
                  style={{
                    border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                    borderRadius: 3,
                    background: '#151515',
                    color: '#a3adba',
                    fontSize: 9,
                    letterSpacing: 0.35,
                    cursor: 'pointer',
                    padding: '2px 6px',
                  }}
                  title="Toggle focus restore policy"
                >
                  Restore: {focusRestorePolicy === 'scope_first' ? 'scope-first' : 'selection-first'}
                </button>
                <span style={{ color: '#8f9399', fontSize: 9, letterSpacing: 0.35 }}>
                  Source: {focusRestoreSource || '-'}
                </span>
              </div>
            )}

            {/* MARKER_155.ARCHITECT_BUILD.VERIFIER_UI.V2:
                Practical graph-health badge (user-facing), not raw spectral telemetry. */}
            {debugMode && navLevel === 'roadmap' && roadmapVerifier && verifierUi && (
              <div
                style={{
                  position: 'absolute',
                  top: 8,
                  right: 8,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  background: 'rgba(0,0,0,0.70)',
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 4,
                  padding: '4px 10px',
                  fontSize: 10,
                  color: verifierUi.color,
                  letterSpacing: 0.35,
                  zIndex: 9,
                  pointerEvents: 'auto',
                  fontFamily: 'monospace',
                  cursor: 'help',
                }}
                title={verifierUi.hint}
                onClick={() => {
                  const sp = roadmapVerifier.spectral || ({} as any);
                  addToast(
                    'info',
                    `${verifierUi.title} · λ2=${Number(sp.lambda2 || 0).toFixed(3)} · gap=${Number(sp.eigengap || 0).toFixed(3)} · components=${Number(sp.component_count || 0)}`,
                  );
                }}
              >
                <span>{verifierUi.title}</span>
              </div>
            )}

            {debugMode && navLevel === 'roadmap' && jepaRuntimeUi && (
              <div
                style={{
                  position: 'absolute',
                  top: 36,
                  right: 8,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  background: 'rgba(0,0,0,0.70)',
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 4,
                  padding: '4px 10px',
                  fontSize: 10,
                  color: jepaRuntimeUi.color,
                  letterSpacing: 0.35,
                  zIndex: 9,
                  pointerEvents: 'auto',
                  fontFamily: 'monospace',
                  cursor: 'help',
                }}
                title={jepaRuntimeUi.hint}
                onClick={() => addToast('info', `${jepaRuntimeUi.title} · ${jepaRuntimeUi.hint}`)}
              >
                <span>{jepaRuntimeUi.title}</span>
              </div>
            )}
          </div>

          {/* MARKER_154.3A: FooterActionBar — unified 3-action bar per level.
              Replaces RailsActionBar + CaptainBar + WorkflowToolbar actions. */}
          {debugMode && (
          <FooterActionBar
            onAction={(action) => {
              switch (action) {
                // Roadmap actions
                case 'launch':
                  if (selectedNode) {
                    handleLevelAwareNodeDoubleClick(selectedNode);
                  }
                  else handleExecute();
                  break;
                case 'askArchitect':
                  if (!sendFocusToArchitect()) {
                    // MARKER_154.12A: Fallback — focus MiniChat input for free-form prompt
                    document.querySelector<HTMLInputElement>('.mini-chat-input')?.focus();
                    addToast('info', 'Type in the chat window ↗');
                  }
                  break;
                case 'addTask':
                  // Focus task list quick-add (existing MCCTaskList input)
                  document.querySelector<HTMLInputElement>('[data-testid="quick-add-input"]')?.focus();
                  break;
                // Task actions
                case 'launchTask': {
                  const taskId = useMCCStore.getState().navTaskId || selectedTaskId;
                  if (taskId) useMCCStore.getState().dispatchTask(taskId);
                  break;
                }
                case 'editTask':
                  // MARKER_154.8A: Open TaskEditPopup
                  setShowTaskEdit(true);
                  break;
                // Workflow actions
                case 'execute':
                  handleExecute();
                  break;
                case 'toggleEdit':
                  toggleEditMode();
                  break;
                // Running actions
                case 'pause':
                case 'cancel': {
                  const runningTask = tasks.find(t => t.status === 'running');
                  if (runningTask) useMCCStore.getState().cancelTask(runningTask.id);
                  if (action === 'cancel') goBack();
                  break;
                }
                // Result actions
                case 'apply': {
                  // MARKER_154.10B: Apply code — mark task as done + update result_status
                  const applyTaskId = useMCCStore.getState().navTaskId || selectedTaskId;
                  if (applyTaskId) {
                    fetch(`${API_BASE}/debug/task-board/${applyTaskId}`, {
                      method: 'PATCH',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ status: 'done', result_status: 'applied' }),
                    }).then(() => {
                      addToast('success', 'Result applied ✓');
                      useMCCStore.getState().fetchTasks();
                      goBack();
                    }).catch(() => addToast('error', 'Failed to apply'));
                  }
                  break;
                }
                case 'redo':
                  // MARKER_154.10A: Open RedoFeedbackInput
                  setShowRedoInput(true);
                  break;
                // First Run actions — MARKER_154.16A: FirstRunView handles these directly
                // FooterActionBar still shows at first_run but FirstRunView has own input flow
                case 'selectFolder':
                case 'enterUrl':
                case 'describeText':
                  // No-op: FirstRunView handles project init flow
                  break;
                // Gear actions
                case 'regenerate':
                  roadmap.regenerateRoadmap?.();
                  break;
                case 'openSettings':
                  addToast('info', 'Settings coming in future wave');
                  break;
                case 'openPlayground':
                  addToast('info', 'Playground menu: top-right badge');
                  break;
                case 'openFilter':
                  if (navLevel !== 'roadmap') {
                    addToast('info', 'Focus view filter is available on Architecture level');
                    break;
                  }
                  setFocusDisplayMode((prev) => {
                    const next: FocusDisplayMode = prev === 'all'
                      ? 'selected_deps'
                      : prev === 'selected_deps'
                        ? 'selected_only'
                        : 'all';
                    addToast('info', `Focus view: ${next === 'all' ? 'all' : next === 'selected_deps' ? 'selected + dependencies' : 'selected only'}`);
                    return next;
                  });
                  break;
                case 'saveWorkflow':
                  dagEditor.save(dagEditor.workflowName);
                  break;
                case 'expandStream':
                  setShowStream(!showStream);
                  break;
                case 'showDetails':
                case 'showDiff':
                  addToast('info', 'Details coming in Wave 3');
                  break;
              }
            }}
            disabledActions={
              navLevel === 'roadmap' && !selectedNode ? ['launch'] : []
            }
          />
          )}

          {/* MARKER_154.8A: TaskEditPopup — shown when user clicks Edit on task level */}
          {showTaskEdit && (() => {
            const taskId = useMCCStore.getState().navTaskId || selectedTaskId;
            const task = tasks.find(t => t.id === taskId);
            if (!task) return null;
            return (
              <TaskEditPopup
                taskId={task.id}
                title={task.title}
                description={task.description || ''}
                preset={task.preset || 'dragon_silver'}
                phaseType={task.phase_type || 'build'}
                onSave={(updates) => {
                  fetch(`${API_BASE}/debug/task-board/${task.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updates),
                  }).then(() => useMCCStore.getState().fetchTasks());
                }}
                onDispatch={() => {
                  useMCCStore.getState().dispatchTask(task.id);
                }}
                onClose={() => setShowTaskEdit(false)}
              />
            );
          })()}

          {/* MARKER_154.10A: RedoFeedbackInput — shown when user clicks Redo on result level */}
          {showRedoInput && (() => {
            const taskId = useMCCStore.getState().navTaskId || selectedTaskId;
            const task = tasks.find(t => t.id === taskId);
            if (!task) return null;
            return (
              <RedoFeedbackInput
                taskId={task.id}
                taskTitle={task.title}
                onSubmit={(feedback) => {
                  // PATCH task back to pending with feedback, then re-dispatch
                  fetch(`${API_BASE}/debug/task-board/${task.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      status: 'pending',
                      result_status: 'rework',
                      description: `${task.description || ''}\n\n[REDO FEEDBACK]: ${feedback}`,
                    }),
                  }).then(() => {
                    useMCCStore.getState().fetchTasks();
                    useMCCStore.getState().dispatchTask(task.id);
                    addToast('info', 'Task re-dispatched with feedback');
                  });
                  setShowRedoInput(false);
                }}
                onCancel={() => setShowRedoInput(false)}
              />
            );
          })()}

          {/* Stream Panel — collapsible bottom */}
          {showStream && <StreamPanel maxEvents={8} />}
        </div>
        {/* MARKER_155.CLEANUP: Right panel removed — using floating mini-windows instead */}
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

      {/* ═══ MARKER_144.3 + 155.G1: Context Menu Overlay ═══ */}
      {(editMode || navLevel === 'roadmap') && (
        <DAGContextMenu
          target={contextMenuTarget}
          onClose={() => setContextMenuTarget(null)}
          onAddNode={handleAddNodeFromMenu}
          onCreateTaskHere={navLevel === 'roadmap' ? handleCreateTaskFromNode : undefined}
          onApproveSuggestedAnchor={
            navLevel === 'roadmap'
              && contextMenuTarget?.kind === 'node'
              && contextMenuTarget.nodeId.startsWith('task_overlay_')
              && graphForView.nodes.some(
                (n) => n.id === contextMenuTarget.nodeId && n.anchorState === 'suggested'
              )
              ? handleApproveSuggestedAnchor
              : undefined
          }
          onDeleteNode={navLevel === 'roadmap' ? undefined : dagEditor.removeNode}
          onDuplicateNode={navLevel === 'roadmap' ? undefined : handleDuplicateNode}
          onDeleteEdge={navLevel === 'roadmap' ? undefined : dagEditor.removeEdge}
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

      {debugMode && hasProject && navLevel !== 'first_run' && !onboardingCompleted && !onboardingDismissed && (
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

      {/* MARKER_153.6D: Toast notifications — top-right overlay */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
