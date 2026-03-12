/**
 * MARKER_154.14A: MiniStats — compact statistics overlay in DAG canvas.
 *
 * Compact: 4 key numbers (runs, success%, avg duration, total cost).
 * Expanded: full stats dashboard.
 * Position: top-right.
 * Data: GET /api/analytics/summary
 *
 * @phase 154
 * @wave 4
 * @status active
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { MiniWindow } from './MiniWindow';
import { NOLAN_PALETTE } from '../../utils/dagLayout';
import { useDevPanelStore } from '../../store/useDevPanelStore';
import { useMCCDiagnostics } from '../../hooks/useMCCDiagnostics';
import { useMCCStore } from '../../store/useMCCStore';
// MARKER_176.15: Centralized MCC API config import.
import { ANALYTICS_API, MCC_API } from '../../config/api.config';
import type { MiniContextPayload } from './MiniContext';
import { resolveMiniStatsCompactRoleAsset, resolveRoleMotionAsset, resolveRolePreviewAsset, resolveWorkflowLeadRole, type MycoRolePreviewRole } from './mycoRolePreview';


interface SummaryData {
  total_pipelines: number;
  success_rate: number;
  avg_duration_s: number;
  total_cost_usd: number;
  total_llm_calls: number;
  total_tokens: number;
  // Optional per-team breakdown
  by_preset?: Record<string, {
    count: number;
    success_rate: number;
    avg_duration_s: number;
  }>;
}

// MARKER_154.14A_FIX: Normalize API response to match SummaryData interface
function normalizeSummary(raw: any): SummaryData {
  // API may wrap in { success, data } or return flat
  const d = raw?.data || raw;
  return {
    total_pipelines: d.total_pipelines ?? d.total_runs ?? 0,
    success_rate: d.success_rate ?? 0,
    avg_duration_s: d.avg_duration_s ?? 0,
    total_cost_usd: d.total_cost_usd ?? d.total_cost_estimate ?? 0,
    total_llm_calls: d.total_llm_calls ?? 0,
    total_tokens: d.total_tokens ?? 0,
    by_preset: d.by_preset ?? d.tasks_by_preset ? Object.fromEntries(
      Object.entries(d.tasks_by_preset || {}).map(([k, v]: [string, any]) => [
        k,
        typeof v === 'number'
          ? { count: v, success_rate: 0, avg_duration_s: 0 }
          : { count: v?.count ?? 0, success_rate: v?.success_rate ?? 0, avg_duration_s: v?.avg_duration_s ?? 0 },
      ])
    ) : undefined,
  };
}

// MARKER_155.STATS.UI: Agent metrics data
interface AgentSummary {
  agent_type: string;
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  avg_duration: number;
  avg_quality: number;
  total_tokens: number;
  total_cost: number;
  recent_remarks: string[];
}

interface AgentsData {
  period: string;
  agents: Record<string, AgentSummary>;
}

const NEUTRAL_FAIL = '#90978f';
const NEUTRAL_WARN = '#c1b27c';

interface MiniStatsProps {
  context?: MiniContextPayload;
}

interface PrefetchWorkflowSelectionDiagnostics {
  workflow_id?: string;
  workflow_name?: string;
  reinforcement?: string[];
  reinforcement_policy?: Record<string, any>;
  reason?: string;
}

interface TaskWorkflowBinding {
  workflow_bank: string;
  workflow_id: string;
  workflow_family: string;
  team_profile: string;
  selection_origin: string;
}

interface WorkflowMycoHintData {
  hint: string;
  ordered_tools: string[];
  tool_priority: Record<string, string[]>;
  diagnostics: {
    workflow_family: string;
    workflow_bank: string;
    role: string;
    retrieval_method: string;
    retrieval_count: number;
  };
}

interface LocalguysRunData {
  run_id: string;
  task_id: string;
  workflow_family: string;
  status: string;
  current_step: string;
  active_role: string;
  model_id: string;
  failure_reason: string;
  playground_id: string;
  branch_name: string;
  worktree_path: string;
  artifact_manifest?: {
    required?: string[];
    missing?: string[];
    files?: Record<string, {
      name: string;
      exists: boolean;
      size_bytes?: number;
      updated_at?: string;
    }>;
  };
  metrics?: {
    runtime_ms?: number;
    required_artifact_count?: number;
    artifact_missing_count?: number;
    artifact_present_count?: number;
    event_count?: number;
    run_status?: string;
    workflow_family?: string;
  };
}

interface LocalguysBenchmarkSummaryData {
  count: number;
  workflow_family: string;
  status_counts?: Record<string, number>;
  model_counts?: Record<string, number>;
  runtime_counts?: Record<string, number>;
  avg_runtime_ms?: number;
  avg_artifact_missing_count?: number;
  avg_required_artifact_count?: number;
  success_rate?: number;
  recent_runs?: Array<{
    runtime_name?: string;
    run_status?: string;
    accelerator?: string;
    device_profile?: string;
    notes?: string;
    updated_at?: string;
    created_at?: string;
  }>;
}

function summarizeRuntimeCounts(summary?: LocalguysBenchmarkSummaryData | null): string {
  const counts = summary?.runtime_counts;
  if (!counts) return 'runtime:localguys';
  const rows = Object.entries(counts)
    .filter(([, value]) => Number(value || 0) > 0)
    .sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0))
    .map(([key, value]) => `${key}:${value}`);
  return rows.length ? `runtime:${rows.join('/')}` : 'runtime:localguys';
}

function summarizeLatestLitert(summary?: LocalguysBenchmarkSummaryData | null): string | null {
  const row = (summary?.recent_runs || []).find((item) => String(item?.runtime_name || '').trim() === 'litert');
  if (!row) return null;
  const status = String(row.run_status || 'unknown').trim() || 'unknown';
  const accelerator = String(row.accelerator || '').trim();
  const device = String(row.device_profile || '').trim();
  const notes = String(row.notes || '').trim();
  const parts = ['litert', status];
  if (accelerator) parts.push(accelerator);
  if (device) parts.push(device);
  if (notes) parts.push(notes);
  return parts.join(' · ');
}

function resolveContextSubtitle(context?: MiniContextPayload): string {
  if (!context || context.scope === 'project') return 'scope: project';
  if (context.nodeKind === 'task') return `scope: task (${context.label})`;
  if (context.nodeKind === 'agent') return `scope: agent (${context.role || context.label})`;
  if (context.nodeKind === 'file' || context.nodeKind === 'directory') return `scope: ${context.nodeKind} (${context.label})`;
  return `scope: node (${context.label})`;
}

function resolveAgentLane(role?: string): string | null {
  const r = String(role || '').toLowerCase().trim();
  if (r === 'verifier') return 'lane: checks (pass/fail)';
  if (r === 'eval') return 'lane: scoring (quality)';
  return null;
}

function usePrefetchReinforcement(context?: MiniContextPayload) {
  const [diag, setDiag] = useState<PrefetchWorkflowSelectionDiagnostics | null>(null);
  const [loading, setLoading] = useState(false);
  const requestKey = useMemo(() => {
    const scope = context?.scope || 'project';
    const kind = context?.nodeKind || 'project';
    const label = String(context?.label || '').trim();
    const role = String(context?.role || '').trim();
    return `${scope}:${kind}:${role}:${label}`;
  }, [context?.scope, context?.nodeKind, context?.label, context?.role]);

  useEffect(() => {
    let cancelled = false;
    const taskDescription =
      String(context?.label || '').trim() ||
      (context?.scope === 'project' ? 'project architect planning' : 'context planning');
    const taskType = context?.nodeKind === 'agent'
      ? 'build'
      : context?.nodeKind === 'task'
        ? 'test'
        : 'build';
    const complexity = context?.scope === 'project' ? 7 : 5;

    setLoading(true);
    fetch(`${MCC_API}/prefetch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_description: taskDescription,
        task_type: taskType,
        complexity,
      }),
    })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (cancelled || !data) return;
        const wf = data?.diagnostics?.workflow_selection;
        setDiag(wf && typeof wf === 'object' ? wf : null);
      })
      .catch(() => {
        if (cancelled) return;
        setDiag(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [requestKey]);

  return { diag, loading };
}

function useTaskWorkflowBinding(context: MiniContextPayload | undefined, tasks: any[]) {
  const [binding, setBinding] = useState<TaskWorkflowBinding | null>(null);
  const [revision, setRevision] = useState(0);
  const taskId = String(context?.taskId || '').trim();
  const nodeId = String(context?.nodeId || '').trim();

  const fallbackTask = useMemo(() => {
    if (!context || !taskId) return null;
    return tasks.find((t) => t.id === taskId || `task_overlay_${t.id}` === nodeId) || null;
  }, [context, nodeId, taskId, tasks]);

  useEffect(() => {
    if (!taskId) {
      setBinding(null);
      return;
    }
    let cancelled = false;

    const fallbackBinding = fallbackTask ? {
      workflow_bank: String(fallbackTask.workflow_bank || 'core').trim() || 'core',
      workflow_id: String(fallbackTask.workflow_id || fallbackTask.pipeline_task_id || '').trim(),
      workflow_family: String(fallbackTask.workflow_family || fallbackTask.workflow_id || '').trim(),
      team_profile: String(fallbackTask.team_profile || fallbackTask.preset || '').trim(),
      selection_origin: String(fallbackTask.workflow_selection_origin || '').trim(),
    } : null;

    fetch(`${MCC_API}/tasks/${encodeURIComponent(taskId)}/workflow-binding`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (cancelled) return;
        const row = data?.binding;
        if (!row || typeof row !== 'object') {
          setBinding(fallbackBinding);
          return;
        }
        setBinding({
          workflow_bank: String(row.workflow_bank || 'core').trim() || 'core',
          workflow_id: String(row.workflow_id || '').trim(),
          workflow_family: String(row.workflow_family || row.workflow_id || '').trim(),
          team_profile: String(row.team_profile || '').trim(),
          selection_origin: String(row.selection_origin || '').trim(),
        });
      })
      .catch(() => {
        if (cancelled) return;
        setBinding(fallbackBinding);
      });

    return () => {
      cancelled = true;
    };
  }, [fallbackTask, revision, taskId]);

  const refresh = useCallback(() => {
    setRevision((n) => n + 1);
  }, []);

  return { binding, refresh };
}

function useWorkflowCatalog() {
  const [catalog, setCatalog] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${MCC_API}/workflow-catalog`);
      if (!res.ok) return;
      const json = await res.json();
      setCatalog(json);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { catalog, loading, refresh };
}

function useLocalguysRun(
  context: MiniContextPayload | undefined,
  binding: TaskWorkflowBinding | null,
) {
  const [run, setRun] = useState<LocalguysRunData | null>(null);
  const [loading, setLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  const [starting, setStarting] = useState(false);
  const taskId = String(context?.taskId || '').trim();
  const workflowFamily = String(binding?.workflow_family || '').trim();
  const enabled = taskId.length > 0 && workflowFamily.endsWith('_localguys');

  useEffect(() => {
    if (!enabled) {
      setRun(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetch(`${MCC_API}/tasks/${encodeURIComponent(taskId)}/localguys-run`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (cancelled) return;
        const row = data?.run;
        setRun(row && typeof row === 'object' ? row as LocalguysRunData : null);
      })
      .catch(() => {
        if (cancelled) return;
        setRun(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [enabled, revision, taskId]);

  const refresh = useCallback(() => {
    setRevision((n) => n + 1);
  }, []);

  const startRun = useCallback(async () => {
    if (!enabled || starting) return false;
    setStarting(true);
    try {
      const res = await fetch(`${MCC_API}/tasks/${encodeURIComponent(taskId)}/localguys-run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) return false;
      const json = await res.json();
      const row = json?.run;
      setRun(row && typeof row === 'object' ? row as LocalguysRunData : null);
      setRevision((n) => n + 1);
      return true;
    } catch {
      return false;
    } finally {
      setStarting(false);
    }
  }, [enabled, starting, taskId]);

  return { enabled, run, loading, starting, refresh, startRun };
}

function useLocalguysBenchmarkSummary(
  context: MiniContextPayload | undefined,
  binding: TaskWorkflowBinding | null,
) {
  const [summary, setSummary] = useState<LocalguysBenchmarkSummaryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  const taskId = String(context?.taskId || '').trim();
  const workflowFamily = String(binding?.workflow_family || '').trim();
  const enabled = taskId.length > 0 && workflowFamily.endsWith('_localguys');

  useEffect(() => {
    if (!enabled) {
      setSummary(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetch(`${MCC_API}/localguys/benchmark-summary?workflow_family=${encodeURIComponent(workflowFamily)}&limit=20`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (cancelled) return;
        const row = data?.summary;
        setSummary(row && typeof row === 'object' ? row as LocalguysBenchmarkSummaryData : null);
      })
      .catch(() => {
        if (cancelled) return;
        setSummary(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [enabled, revision, taskId, workflowFamily]);

  const refresh = useCallback(() => {
    setRevision((n) => n + 1);
  }, []);

  return { enabled, summary, loading, refresh };
}


function useWorkflowMycoHint(context: MiniContextPayload | undefined, binding: TaskWorkflowBinding | null) {
  const [data, setData] = useState<WorkflowMycoHintData | null>(null);
  const [loading, setLoading] = useState(false);

  const requestKey = useMemo(() => {
    return [
      String(context?.taskId || ''),
      String(context?.label || ''),
      String(context?.role || ''),
      String(binding?.workflow_bank || ''),
      String(binding?.workflow_id || ''),
      String(binding?.workflow_family || ''),
    ].join('::');
  }, [binding?.workflow_bank, binding?.workflow_family, binding?.workflow_id, context?.label, context?.role, context?.taskId]);

  useEffect(() => {
    if (!context?.taskId || !binding?.workflow_id) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetch(`${MCC_API}/workflow/myco-hint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workflow_bank: binding.workflow_bank,
        workflow_id: binding.workflow_id,
        workflow_family: binding.workflow_family,
        role: context.role || '',
        task_label: context.label || context.taskId || 'active task',
        scope: context.scope || 'task',
        focus: context || {},
      }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((json) => {
        if (cancelled || !json?.success) return;
        setData({
          hint: String(json.hint || '').trim(),
          ordered_tools: Array.isArray(json.ordered_tools) ? json.ordered_tools.map((v: any) => String(v)) : [],
          tool_priority: json.tool_priority || {},
          diagnostics: {
            workflow_family: String(json?.diagnostics?.workflow_family || ''),
            workflow_bank: String(json?.diagnostics?.workflow_bank || ''),
            role: String(json?.diagnostics?.role || ''),
            retrieval_method: String(json?.diagnostics?.retrieval_method || 'none'),
            retrieval_count: Number(json?.diagnostics?.retrieval_count || 0),
          },
        });
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [binding?.workflow_id, context, requestKey]);

  return { data, loading };
}

function useSummaryData() {
  const [data, setData] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const lastFetchRef = useRef(0);

  const fetch_ = useCallback(async () => {
    const now = Date.now();
    if (now - lastFetchRef.current < 1000) return;
    lastFetchRef.current = now;
    try {
      const res = await fetch(`${ANALYTICS_API}/summary`);
      if (!res.ok) return;
      const json = await res.json();
      // MARKER_154.14A_FIX: Normalize response (API wraps in {success, data})
      setData(normalizeSummary(json));
    } catch {
      // API may not be available
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch_();
    const onVisibility = () => {
      if (!document.hidden) fetch_();
    };
    window.addEventListener('pipeline-stats', fetch_ as EventListener);
    window.addEventListener('task-board-updated', fetch_ as EventListener);
    window.addEventListener('focus', fetch_);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('pipeline-stats', fetch_ as EventListener);
      window.removeEventListener('task-board-updated', fetch_ as EventListener);
      window.removeEventListener('focus', fetch_);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [fetch_]);

  return { data, loading, refresh: fetch_ };
}

// MARKER_155.STATS.UI: Hook for agent metrics
function useAgentsData() {
  const [data, setData] = useState<AgentsData | null>(null);
  const [loading, setLoading] = useState(true);
  const lastFetchRef = useRef(0);

  const fetch_ = useCallback(async () => {
    const now = Date.now();
    if (now - lastFetchRef.current < 1500) return;
    lastFetchRef.current = now;
    try {
      const res = await fetch(`${ANALYTICS_API}/agents/summary?period=7d`);
      if (!res.ok) return;
      const json = await res.json();
      if (json.success) {
        setData(json);
      }
    } catch {
      // API may not be available
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch_();
    const onVisibility = () => {
      if (!document.hidden) fetch_();
    };
    window.addEventListener('pipeline-stats', fetch_ as EventListener);
    window.addEventListener('task-board-updated', fetch_ as EventListener);
    window.addEventListener('focus', fetch_);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('pipeline-stats', fetch_ as EventListener);
      window.removeEventListener('task-board-updated', fetch_ as EventListener);
      window.removeEventListener('focus', fetch_);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [fetch_]);

  return { data, loading, refresh: fetch_ };
}

// Single stat box
function StatBox({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div style={{ textAlign: 'center', flex: 1 }}>
      <div style={{
        color: NOLAN_PALETTE.text,
        fontSize: 14,
        fontWeight: 700,
        lineHeight: 1,
      }}>
        {value}
        {unit && <span style={{ fontSize: 8, color: '#555', marginLeft: 1 }}>{unit}</span>}
      </div>
      <div style={{
        color: '#555',
        fontSize: 7,
        textTransform: 'uppercase',
        letterSpacing: 0.5,
        marginTop: 2,
      }}>
        {label}
      </div>
    </div>
  );
}

// Compact: 4 stat boxes
function StatsCompact({ context }: MiniStatsProps) {
  const { data, loading } = useSummaryData();
  const setStatsMode = useDevPanelStore(s => s.setStatsMode);
  const diagnostics = useMCCDiagnostics();
  const prefetchDiag = usePrefetchReinforcement(context);
  const tasks = useMCCStore(s => s.tasks);
  const streamEvents = useMCCStore(s => s.streamEvents);
  const scopeSubtitle = useMemo(() => resolveContextSubtitle(context), [context]);
  const { binding: taskWorkflowBinding } = useTaskWorkflowBinding(context, tasks);
  const workflowMycoHint = useWorkflowMycoHint(context, taskWorkflowBinding);
  const [triggerRoleAsset, setTriggerRoleAsset] = useState<string | null>(null);
  const triggerRoleTimerRef = useRef<number | null>(null);
  const compactRoleAsset = useMemo(() => {
    // MARKER_168.MYCO.RUNTIME.MINI_STATS_COMPACT_ROLE_PREVIEW.V1:
    // Compact Stats previews the relevant role for the selected task/workflow surface.
    return triggerRoleAsset || resolveMiniStatsCompactRoleAsset(context);
  }, [context, triggerRoleAsset]);
  const selectedTask = useMemo(() => {
    if (!context?.taskId) return null;
    return tasks.find((t) => t.id === context.taskId || `task_overlay_${t.id}` === context.nodeId) || null;
  }, [context?.nodeId, context?.taskId, tasks]);
  const localguys = useLocalguysRun(context, taskWorkflowBinding);
  const localguysBenchmark = useLocalguysBenchmarkSummary(context, taskWorkflowBinding);

  const taskWorkflowSummary = useMemo(() => {
    if (!context?.taskId) return null;
    const workflowId = String(taskWorkflowBinding?.workflow_id || selectedTask?.workflow_id || '').trim();
    const workflowFamily = String(taskWorkflowBinding?.workflow_family || workflowId || '').trim();
    const workflowBank = String(taskWorkflowBinding?.workflow_bank || 'core').trim() || 'core';
    const selectionOrigin = String(taskWorkflowBinding?.selection_origin || '').trim() || 'heuristic';
    const teamProfile = String(taskWorkflowBinding?.team_profile || selectedTask?.team_profile || selectedTask?.preset || '').trim();
    const teamStats = teamProfile ? data?.by_preset?.[teamProfile] : null;
    return {
      workflowId,
      workflowFamily,
      workflowBank,
      selectionOrigin,
      teamProfile,
      teamRuns: teamStats?.count ?? 0,
      teamSuccess: teamStats?.success_rate ?? 0,
      bindingState: workflowId ? 'bound' : 'pending',
      overrideState: selectionOrigin === 'user-selected' ? 'user' : 'heuristic',
    };
  }, [context?.taskId, data?.by_preset, selectedTask, taskWorkflowBinding]);

  useEffect(() => {
    if (!context?.taskId) {
      setTriggerRoleAsset(null);
      return;
    }
    const clearTriggerTimer = () => {
      if (triggerRoleTimerRef.current !== null) {
        window.clearTimeout(triggerRoleTimerRef.current);
        triggerRoleTimerRef.current = null;
      }
    };
    const pulseRole = (role: string | null | undefined, seed: string) => {
      const normalized = String(role || '').trim().toLowerCase();
      if (!normalized) return;
      const resolvedRole: MycoRolePreviewRole | null =
        normalized === 'eval'
          ? 'verifier'
          : (normalized === 'architect' || normalized === 'coder' || normalized === 'researcher' || normalized === 'scout' || normalized === 'verifier'
              ? normalized
              : null);
      if (!resolvedRole) return;
      const asset = resolveRoleMotionAsset(
        resolvedRole,
        `${seed}:${context?.taskId || ''}:${context?.nodeId || ''}:${context?.label || ''}`,
      );
      if (!asset) return;
      setTriggerRoleAsset(asset);
      clearTriggerTimer();
      triggerRoleTimerRef.current = window.setTimeout(() => {
        setTriggerRoleAsset(null);
        triggerRoleTimerRef.current = null;
      }, 3200);
    };

    const onWorkflowSelected = (event: Event) => {
      // MARKER_168.MYCO.RUNTIME.MINI_STATS_WORKFLOW_SELECTED_TRANSITION.V1:
      // Compact Stats briefly pulses the workflow lead role after explicit task workflow choice.
      const detail = (event as CustomEvent).detail || {};
      if (String(detail.taskId || '') !== String(context?.taskId || '')) return;
      pulseRole(detail.role || 'architect', `workflow_selected:${String(detail.workflowId || '')}`);
    };

    const onTaskBoardUpdated = (event: Event) => {
      // MARKER_168.MYCO.RUNTIME.MINI_STATS_TASK_BOARD_TRANSITION.V1:
      // Task-board lifecycle events may transiently foreground coder/verifier role previews
      // for the currently selected task only.
      const detail = (event as CustomEvent).detail || {};
      const eventTaskId = String(detail.task_id || detail.taskId || '');
      if (eventTaskId && eventTaskId !== String(context?.taskId || '')) return;
      const action = String(detail.action || detail.type || '').toLowerCase();
      if (action === 'task_claimed' || action === 'task_started' || action === 'running') {
        pulseRole(detail.agent_type || detail.role || 'coder', `task_started:${action}`);
      } else if (action === 'task_completed') {
        pulseRole(detail.agent_type || detail.role || 'verifier', `task_completed:${action}`);
      } else if (action === 'task_failed' || action === 'pipeline_failed') {
        pulseRole(detail.agent_type || detail.role || 'verifier', `task_failed:${action}`);
      }
    };

    window.addEventListener('mcc-workflow-selected', onWorkflowSelected as EventListener);
    window.addEventListener('task-board-updated', onTaskBoardUpdated as EventListener);
    return () => {
      window.removeEventListener('mcc-workflow-selected', onWorkflowSelected as EventListener);
      window.removeEventListener('task-board-updated', onTaskBoardUpdated as EventListener);
      clearTriggerTimer();
    };
  }, [context?.label, context?.nodeId, context?.taskId]);

  const openWorkflowPanel = useCallback(() => {
    setStatsMode('ops');
    window.dispatchEvent(new CustomEvent('mcc-miniwindow-open', {
      detail: { windowId: 'stats', expanded: true },
    }));
  }, [setStatsMode]);

  const contextualLine = useMemo(() => {
    if (!context || context.scope === 'project') {
      return null;
    }
    if (context.taskId) {
      const task = tasks.find((t) => t.id === context.taskId || `task_overlay_${t.id}` === context.nodeId);
      const events = streamEvents.filter((e) => e.taskId === (context.taskId || task?.id));
      return `task: ${task?.status || context.status || '-'} · events: ${events.length}`;
    }
    if (context.role) {
      const role = String(context.role).toLowerCase();
      const roleAliases = role === 'eval' ? ['eval', 'verifier'] : [role];
      const events = streamEvents.filter((e) => roleAliases.includes(String(e.role || '').toLowerCase()));
      const lane = resolveAgentLane(role);
      return lane
        ? `role: ${role} · events: ${events.length} · ${lane}`
        : `role: ${role} · events: ${events.length}`;
    }
    if (context.path) {
      const linkedTasks = tasks.filter((t) => String(t.module || '').includes(context.path || ''));
      return `linked tasks: ${linkedTasks.length}`;
    }
    return `node: ${context.nodeId || '-'}`;
  }, [context, tasks, streamEvents]);

  if (loading || !data) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <span style={{ color: '#444', fontSize: 9 }}>
          {loading ? 'Loading...' : 'No stats yet'}
        </span>
      </div>
    );
  }

  const formatDuration = (s: number) => {
    if (s < 60) return `${Math.round(s)}s`;
    return `${Math.round(s / 60)}m`;
  };

  const rate = data.success_rate ?? 0;
  const successColor = rate >= 70 ? '#8a8' : rate >= 50 ? NEUTRAL_WARN : NEUTRAL_FAIL;
  const cost = data.total_cost_usd ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'center', gap: 8 }}>
      <div style={{ color: '#7f8893', fontSize: 8, textTransform: 'uppercase', letterSpacing: 0.35 }}>
        {scopeSubtitle}
      </div>
      {taskWorkflowSummary ? (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 5,
            padding: '6px 0',
            borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
            borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 8,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
              {compactRoleAsset ? (
                <img
                  src={compactRoleAsset}
                  alt="Workflow role preview"
                  style={{ width: 22, height: 28, objectFit: 'contain', flexShrink: 0 }}
                />
              ) : null}
              <button
                onClick={openWorkflowPanel}
                style={{
                  border: '1px solid #2e2e2e',
                  borderRadius: 4,
                  background: '#151515',
                  color: NOLAN_PALETTE.text,
                  fontSize: 9,
                  padding: '2px 8px',
                  cursor: 'pointer',
                  fontFamily: 'monospace',
                  letterSpacing: 0.35,
                }}
                title="Open workflow selection in Stats panel"
              >
                WORKFLOW
              </button>
            </div>
            <span style={{ fontSize: 8, color: '#a2abb5', textTransform: 'uppercase' }}>
              {taskWorkflowSummary.workflowBank}
            </span>
          </div>
          <div style={{ color: NOLAN_PALETTE.text, fontSize: 8, lineHeight: 1.35 }}>
            {/* MARKER_167.STATS_WORKFLOW.UI_COMPACT_CONTEXT.V1 */}
            {taskWorkflowSummary.workflowFamily || taskWorkflowSummary.workflowId || 'choose workflow for task'}
          </div>
          <div style={{ color: '#8e98a4', fontSize: 8, lineHeight: 1.35 }}>
            {/* MARKER_167.STATS_WORKFLOW.UI_COMPACT_TEAM_STATS.V1 */}
            team:{taskWorkflowSummary.teamProfile || '-'} · runs:{taskWorkflowSummary.teamRuns} · ok:{Math.round(taskWorkflowSummary.teamSuccess)}% · via:{taskWorkflowSummary.selectionOrigin}
          </div>
          <div style={{ color: '#6f7883', fontSize: 8, lineHeight: 1.35 }}>
            {/* MARKER_167.STATS_WORKFLOW.MYCO_HINTS.V1 */}
            {workflowMycoHint.loading
              ? 'MYCO: loading workflow hint...'
              : (workflowMycoHint.data?.hint || 'MYCO: choose workflow, then review Context -> Tasks -> Stats')}
          </div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {[
              `bind:${taskWorkflowSummary.bindingState}`,
              `bank:${taskWorkflowSummary.workflowBank}`,
              `via:${taskWorkflowSummary.overrideState}`,
              `myco:${workflowMycoHint.data?.diagnostics?.retrieval_method || 'none'}`,
            ].map((chip) => (
              <span
                key={chip}
                style={{
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 999,
                  padding: '1px 6px',
                  color: '#95a0ad',
                  fontSize: 7,
                  lineHeight: 1.6,
                }}
              >
                {/* MARKER_167.STATS_WORKFLOW.BADGES.V1 */}
                {chip}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {localguys.enabled ? (
        <div
          style={{
            border: `1px solid ${NOLAN_PALETTE.borderDim}`,
            borderRadius: 6,
            padding: '6px 8px',
            background: 'rgba(10,10,10,0.78)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
            <div style={{ color: '#c5ced8', fontSize: 8 }}>
              localguys: {localguys.run ? `${localguys.run.status} · ${localguys.run.current_step}` : (localguys.loading ? 'loading' : 'idle')}
            </div>
            {!localguys.run ? (
              <button
                onClick={() => { void localguys.startRun(); }}
                disabled={localguys.starting}
                style={{
                  border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                  borderRadius: 4,
                  background: 'transparent',
                  color: NOLAN_PALETTE.textMuted,
                  fontSize: 8,
                  padding: '2px 6px',
                  cursor: localguys.starting ? 'default' : 'pointer',
                  opacity: localguys.starting ? 0.6 : 1,
                  fontFamily: 'monospace',
                }}
              >
                {localguys.starting ? 'starting…' : 'start'}
              </button>
            ) : null}
          </div>
          {localguys.run ? (
            <div style={{ color: '#7f8893', fontSize: 8, marginTop: 4 }}>
              pg:{localguys.run.playground_id || '-'} · missing:{localguys.run.metrics?.artifact_missing_count ?? localguys.run.artifact_manifest?.missing?.length ?? 0} · rt:{localguys.run.metrics?.runtime_ms ?? 0}ms
            </div>
          ) : null}
          {localguysBenchmark.summary ? (
            <>
              <div style={{ color: '#6f7882', fontSize: 8, marginTop: 2 }}>
                bench:{localguysBenchmark.summary.count || 0} · ok:{Math.round(Number(localguysBenchmark.summary.success_rate || 0))}% · avg:{localguysBenchmark.summary.avg_runtime_ms || 0}ms · {summarizeRuntimeCounts(localguysBenchmark.summary)}
              </div>
              {summarizeLatestLitert(localguysBenchmark.summary) ? (
                <div style={{ color: '#66707a', fontSize: 8, marginTop: 2 }}>
                  {summarizeLatestLitert(localguysBenchmark.summary)}
                </div>
              ) : null}
            </>
          ) : null}
        </div>
      ) : null}

      {!taskWorkflowSummary ? (
        <>
          <div style={{ display: 'flex', gap: 4 }}>
            <StatBox label="Runs" value={data.total_pipelines ?? 0} />
            <StatBox
              label="Success"
              value={
                <span style={{ color: successColor }}>{Math.round(rate)}%</span> as any
              }
            />
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <StatBox label="Avg Time" value={formatDuration(data.avg_duration_s ?? 0)} />
            <StatBox label="Cost" value={`$${cost.toFixed(2)}`} />
          </div>
        </>
      ) : null}

      {contextualLine ? (
        <div style={{ color: '#8e98a4', fontSize: 8, paddingTop: 2 }}>
          {contextualLine}
        </div>
      ) : null}

      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginTop: 2,
        paddingTop: 6,
        borderTop: `1px solid ${NOLAN_PALETTE.borderDim}`,
      }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <span style={{ fontSize: 8, color: '#9aa4af' }}>
            wf:{context?.workflowSourceMode || 'runtime'}
          </span>
          <span style={{
            fontSize: 8,
            color: diagnostics.buildDesign?.verifier?.decision === 'pass' ? '#67e6bf' : diagnostics.buildDesign?.verifier?.decision === 'warn' ? '#f7d070' : NEUTRAL_FAIL,
          }}>
            graph:{String(diagnostics.buildDesign?.verifier?.decision || '-')}
          </span>
          <span style={{
            fontSize: 8,
            color: diagnostics.runtimeHealth?.ok ? '#67e6bf' : NEUTRAL_FAIL,
          }}>
            rt:{diagnostics.runtimeHealth?.ok ? 'ok' : 'down'}
          </span>
          <span style={{ fontSize: 8, color: '#8e98a4' }}>
            retry:dashed
          </span>
          <span style={{ fontSize: 8, color: '#8e98a4' }} title="OpenHands reinforcement from prefetch diagnostics">
            rh:{
              prefetchDiag.loading
                ? '...'
                : ((prefetchDiag.diag?.reinforcement || []).length > 0
                  ? (prefetchDiag.diag?.reinforcement || []).slice(0, 2).join('+')
                  : 'off')
            }
          </span>
          {workflowMycoHint.data ? (
            <span style={{ fontSize: 8, color: '#8e98a4' }} title="MYCO workflow hint diagnostics">
              myco:{workflowMycoHint.data.diagnostics.retrieval_method || 'none'}/{workflowMycoHint.data.diagnostics.retrieval_count}
            </span>
          ) : null}
        </div>
        <button
          onClick={() => {
            setStatsMode('diagnostics');
          }}
          style={{
            border: '1px solid #2e2e2e',
            borderRadius: 3,
            background: '#151515',
            color: '#9aa2ad',
            fontSize: 8,
            padding: '1px 6px',
            cursor: 'pointer',
            fontFamily: 'monospace',
          }}
          title="Open diagnostics"
        >
          diag ↗
        </button>
      </div>
    </div>
  );
}

// Agent icon mapping
const AGENT_ICONS: Record<string, string> = {
  scout: '[S]',
  researcher: '[R]',
  architect: '[A]',
  coder: '[C]',
  verifier: '[V]',
};

function asRolePreview(agentType: string): MycoRolePreviewRole | null {
  const role = String(agentType || '').trim().toLowerCase();
  if (role === 'architect' || role === 'coder' || role === 'researcher' || role === 'scout' || role === 'verifier') {
    return role;
  }
  return null;
}

function resolveAgentStatsAvatar(agentType: string, seed: string): string | null {
  const role = asRolePreview(agentType);
  if (!role) return null;
  return resolveRoleMotionAsset(role, seed) || resolveRolePreviewAsset(role, seed);
}

// Agent Performance Section
function AgentPerformanceSection() {
  const { data, loading } = useAgentsData();

  if (loading) {
    return (
      <div style={{ color: '#444', fontSize: 11, padding: '12px 0' }}>
        Loading agent metrics...
      </div>
    );
  }

  if (!data || !data.agents) {
    return (
      <div style={{ color: '#444', fontSize: 11, padding: '12px 0' }}>
        No agent data available
      </div>
    );
  }

  const agents = Object.entries(data.agents);
  
  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ 
        color: NOLAN_PALETTE.textMuted, 
        fontSize: 9, 
        marginBottom: 12, 
        textTransform: 'uppercase',
        borderBottom: `1px solid ${NOLAN_PALETTE.border}`,
        paddingBottom: 8,
      }}>
        Agent Performance ({data.period})
      </div>
      
      {agents.map(([agentType, stats]) => {
        const successRate = stats.total_runs > 0 
          ? Math.round((stats.successful_runs / stats.total_runs) * 100) 
          : 0;
        // MARKER_177.LOCALGUYS.AGENT_AVATAR_STATS.V1:
        // Team role rows should use the prepared animated/static role assets instead of
        // plain glyphs when a canonical MCC role is available.
        const avatarSrc = resolveAgentStatsAvatar(agentType, `stats:${agentType}`) || resolveMiniStatsCompactRoleAsset({
          scope: 'node',
          navLevel: 'workflow',
          focusScopeKey: `stats:${agentType}`,
          workflowSourceMode: 'runtime',
          selectedNodeIds: [],
          nodeId: `stats:${agentType}`,
          nodeKind: 'agent',
          label: agentType,
          role: agentType,
        });
        
        return (
          <div
            key={agentType}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 0',
              borderBottom: `1px solid ${NOLAN_PALETTE.borderDim}`,
            }}
          >
            {avatarSrc ? (
              <img
                src={avatarSrc}
                alt={`${agentType} avatar`}
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: 999,
                  objectFit: 'cover',
                  flexShrink: 0,
                }}
              />
            ) : (
              <span style={{ fontSize: 12, width: 20 }}>
                {AGENT_ICONS[agentType] || '🤖'}
              </span>
            )}
            <span style={{ 
              color: NOLAN_PALETTE.text, 
              fontSize: 10, 
              width: 80,
              textTransform: 'capitalize',
            }}>
              {agentType}
            </span>
            <span style={{ color: '#666', fontSize: 9, width: 50 }}>
              {stats.total_runs} runs
            </span>
            <span style={{
              color: successRate >= 70 ? '#8a8' : successRate >= 50 ? NEUTRAL_WARN : NEUTRAL_FAIL,
              fontSize: 9,
              width: 40,
            }}>
              {successRate}%
            </span>
            <span style={{ color: '#666', fontSize: 9, width: 60 }}>
              ~{Math.round(stats.avg_duration)}s
            </span>
            <span style={{ color: '#666', fontSize: 9 }}>
              ${stats.total_cost.toFixed(2)}
            </span>
          </div>
        );
      })}
      
      {/* Recent Remarks */}
      {agents.some(([_, s]) => s.recent_remarks.length > 0) && (
        <div style={{ marginTop: 12 }}>
          <div style={{ 
            color: NOLAN_PALETTE.textMuted, 
            fontSize: 8, 
            marginBottom: 8,
          }}>
            Recent Architect Remarks
          </div>
          {agents.flatMap(([agentType, stats]) => 
            stats.recent_remarks.map((remark, idx) => (
              <div
                key={`${agentType}-${idx}`}
                style={{
                  padding: '4px 8px',
                  marginBottom: 4,
                  background: NOLAN_PALETTE.bg,
                  borderRadius: 4,
                  fontSize: 8,
                  color: '#888',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {(() => {
                  const avatarSrc = resolveAgentStatsAvatar(agentType, `remarks:${agentType}`);
                  if (!avatarSrc) {
                    return <span style={{ color: NOLAN_PALETTE.textAccent }}>{AGENT_ICONS[agentType]}</span>;
                  }
                  return (
                    <img
                      src={avatarSrc}
                      alt={`${agentType} avatar`}
                      style={{ width: 21, height: 21, borderRadius: 999, objectFit: 'cover', flexShrink: 0 }}
                    />
                  );
                })()}
                <span>{remark}</span>
              </div>
            ))
          ).slice(0, 3)}
        </div>
      )}
    </div>
  );
}

// Expanded: detailed stats
function StatsExpanded({ context }: MiniStatsProps) {
  const { data, loading, refresh } = useSummaryData();
  const diagnostics = useMCCDiagnostics();
  const scopeSubtitle = useMemo(() => resolveContextSubtitle(context), [context]);
  const tasks = useMCCStore(s => s.tasks);
  const { binding: taskWorkflowBinding, refresh: refreshBinding } = useTaskWorkflowBinding(context, tasks);
  const localguys = useLocalguysRun(context, taskWorkflowBinding);
  const localguysBenchmark = useLocalguysBenchmarkSummary(context, taskWorkflowBinding);
  const { catalog, loading: catalogLoading, refresh: refreshCatalog } = useWorkflowCatalog();
  const workflowMycoHint = useWorkflowMycoHint(context, taskWorkflowBinding);
  const [selectedBank, setSelectedBank] = useState('core');
  const [savingWorkflowId, setSavingWorkflowId] = useState('');

  const selectedTask = useMemo(() => {
    if (!context?.taskId) return null;
    return tasks.find((t) => t.id === context.taskId || `task_overlay_${t.id}` === context.nodeId) || null;
  }, [context?.nodeId, context?.taskId, tasks]);

  useEffect(() => {
    if (!taskWorkflowBinding?.workflow_bank) return;
    setSelectedBank(taskWorkflowBinding.workflow_bank);
  }, [taskWorkflowBinding?.workflow_bank]);

  const workflowRows = useMemo(() => {
    const rows = Array.isArray(catalog?.workflows) ? catalog.workflows : [];
    return rows.filter((row: any) => String(row?.bank || '') === selectedBank);
  }, [catalog?.workflows, selectedBank]);

  const handleSelectWorkflow = useCallback(async (row: any) => {
    if (!context?.taskId) return;
    const workflowId = String(row?.id || '').trim();
    if (!workflowId) return;
    setSavingWorkflowId(workflowId);
    try {
      await fetch(`${MCC_API}/tasks/${encodeURIComponent(context.taskId)}/workflow-binding`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_bank: String(row?.bank || 'core'),
          workflow_id: workflowId,
          workflow_family: String(row?.family || workflowId),
          team_profile: String(taskWorkflowBinding?.team_profile || selectedTask?.team_profile || selectedTask?.preset || 'dragon_silver'),
          selection_origin: 'user-selected',
        }),
      });
      window.dispatchEvent(new CustomEvent('mcc-workflow-selected', {
        detail: {
          taskId: context.taskId,
          workflowId,
          workflowBank: String(row?.bank || 'core'),
          workflowFamily: String(row?.family || workflowId),
          role: resolveWorkflowLeadRole({
            id: workflowId,
            title: String(row?.title || ''),
            description: String(row?.description || ''),
            compatibility_tags: Array.isArray(row?.compatibility_tags) ? row.compatibility_tags : [],
          }),
        },
      }));
      refreshBinding();
    } catch {
      // ignore
    } finally {
      setSavingWorkflowId('');
    }
  }, [context?.taskId, refreshBinding, selectedTask?.preset, selectedTask?.team_profile, taskWorkflowBinding?.team_profile]);

  if (loading || !data) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <span style={{ color: '#444', fontSize: 11 }}>
          {loading ? 'Loading stats...' : 'No analytics data available'}
        </span>
      </div>
    );
  }

  const presets = data.by_preset ? Object.entries(data.by_preset) : [];

  return (
    <div style={{ padding: '12px 16px', fontFamily: 'monospace' }}>
      <div style={{ color: '#7f8893', fontSize: 9, textTransform: 'uppercase', letterSpacing: 0.35, marginBottom: 10 }}>
        {scopeSubtitle}
      </div>
      {context?.taskId ? (
        <>
          <div
            style={{
              marginBottom: 16,
              padding: '10px 12px',
              border: `1px solid ${NOLAN_PALETTE.border}`,
              borderRadius: 6,
              background: 'rgba(10,10,10,0.85)',
            }}
          >
            <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 9, textTransform: 'uppercase', marginBottom: 8 }}>
              Current Task
            </div>
            <div style={{ color: NOLAN_PALETTE.text, fontSize: 12, fontWeight: 700, marginBottom: 6 }}>
              {selectedTask?.title || context.label}
            </div>
            <div style={{ color: '#9aa4af', fontSize: 9, lineHeight: 1.5 }}>
              {/* MARKER_167.STATS_WORKFLOW.UI_EXPANDED_SELECTOR.V1 */}
              active workflow: {taskWorkflowBinding?.workflow_family || taskWorkflowBinding?.workflow_id || '-'} · bank:{taskWorkflowBinding?.workflow_bank || '-'} · team:{taskWorkflowBinding?.team_profile || selectedTask?.preset || '-'} · via:{taskWorkflowBinding?.selection_origin || '-'}
            </div>
          </div>

          {localguys.enabled ? (
            <div
              style={{
                marginBottom: 16,
                padding: '10px 12px',
                border: `1px solid ${NOLAN_PALETTE.border}`,
                borderRadius: 6,
                background: 'rgba(10,10,10,0.85)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 9, textTransform: 'uppercase' }}>
                  Localguys Runtime
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button
                    onClick={() => { localguys.refresh(); localguysBenchmark.refresh(); }}
                    style={{
                      border: `1px solid ${NOLAN_PALETTE.border}`,
                      borderRadius: 4,
                      background: 'transparent',
                      color: NOLAN_PALETTE.textMuted,
                      fontSize: 9,
                      padding: '3px 8px',
                      cursor: 'pointer',
                      fontFamily: 'monospace',
                    }}
                  >
                    refresh
                  </button>
                  {!localguys.run ? (
                    <button
                      onClick={() => { void localguys.startRun(); }}
                      disabled={localguys.starting}
                      style={{
                        border: `1px solid ${NOLAN_PALETTE.textAccent}`,
                        borderRadius: 4,
                        background: 'transparent',
                        color: NOLAN_PALETTE.text,
                        fontSize: 9,
                        padding: '3px 8px',
                        cursor: localguys.starting ? 'default' : 'pointer',
                        opacity: localguys.starting ? 0.6 : 1,
                        fontFamily: 'monospace',
                      }}
                    >
                      {localguys.starting ? 'starting…' : 'start run'}
                    </button>
                  ) : null}
                </div>
              </div>

              {localguys.loading && !localguys.run ? (
                <div style={{ color: '#666', fontSize: 10 }}>Loading localguys runtime...</div>
              ) : !localguys.run ? (
                <div style={{ color: '#666', fontSize: 10 }}>No localguys run yet for this task.</div>
              ) : (
                <>
                  <div style={{ color: NOLAN_PALETTE.text, fontSize: 11, marginBottom: 6 }}>
                    {localguys.run.status} · {localguys.run.current_step} · role:{localguys.run.active_role || '-'}
                  </div>
                  <div style={{ color: '#9aa4af', fontSize: 9, lineHeight: 1.6, marginBottom: 8 }}>
                    run:{localguys.run.run_id} · pg:{localguys.run.playground_id || '-'} · branch:{localguys.run.branch_name || '-'}
                    {localguys.run.model_id ? ` · model:${localguys.run.model_id}` : ''}
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
                    <span style={{ color: '#9aa4af', fontSize: 9 }}>
                      runtime: {localguys.run.metrics?.runtime_ms ?? 0}ms
                    </span>
                    <span style={{ color: '#9aa4af', fontSize: 9 }}>
                      artifacts: {localguys.run.metrics?.artifact_present_count ?? 0}/{localguys.run.metrics?.required_artifact_count ?? localguys.run.artifact_manifest?.required?.length ?? 0}
                    </span>
                    <span style={{ color: '#9aa4af', fontSize: 9 }}>
                      events: {localguys.run.metrics?.event_count ?? 0}
                    </span>
                  </div>
                  {localguysBenchmark.summary ? (
                    <>
                      <div style={{ color: '#9aa4af', fontSize: 9, lineHeight: 1.6, marginBottom: 4 }}>
                        benchmark: runs:{localguysBenchmark.summary.count || 0} · ok:{Math.round(Number(localguysBenchmark.summary.success_rate || 0))}% · avg rt:{localguysBenchmark.summary.avg_runtime_ms || 0}ms · avg missing:{localguysBenchmark.summary.avg_artifact_missing_count ?? 0}
                      </div>
                      <div style={{ color: '#8a949f', fontSize: 9, lineHeight: 1.6, marginBottom: 8 }}>
                        {summarizeRuntimeCounts(localguysBenchmark.summary)}
                        {summarizeLatestLitert(localguysBenchmark.summary) ? ` · ${summarizeLatestLitert(localguysBenchmark.summary)}` : ''}
                      </div>
                    </>
                  ) : localguysBenchmark.loading ? (
                    <div style={{ color: '#7f8893', fontSize: 9, marginBottom: 8 }}>
                      benchmark: loading...
                    </div>
                  ) : null}
                  {localguys.run.failure_reason ? (
                    <div style={{ color: NEUTRAL_WARN, fontSize: 9, marginBottom: 8 }}>
                      fail: {localguys.run.failure_reason}
                    </div>
                  ) : null}
                  <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 9, textTransform: 'uppercase', marginBottom: 6 }}>
                    Artifact Contract
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                    {(localguys.run.artifact_manifest?.required || []).map((name) => {
                      const exists = Boolean(localguys.run?.artifact_manifest?.files?.[name]?.exists);
                      return (
                        <span
                          key={name}
                          style={{
                            border: `1px solid ${exists ? '#42563e' : NOLAN_PALETTE.border}`,
                            borderRadius: 999,
                            padding: '2px 7px',
                            fontSize: 8,
                            color: exists ? '#9fd08f' : '#7f8893',
                            background: exists ? 'rgba(56,86,46,0.22)' : 'transparent',
                          }}
                        >
                          {exists ? 'ok' : 'missing'}:{name}
                        </span>
                      );
                    })}
                  </div>
                  <div style={{ color: '#9aa4af', fontSize: 9 }}>
                    missing required: {localguys.run.metrics?.artifact_missing_count ?? localguys.run.artifact_manifest?.missing?.length ?? 0}
                  </div>
                </>
              )}
            </div>
          ) : null}

          <div
            style={{
              marginBottom: 20,
              padding: '10px 12px',
              border: `1px solid ${NOLAN_PALETTE.border}`,
              borderRadius: 6,
              background: NOLAN_PALETTE.bg,
            }}
          >
            <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 9, textTransform: 'uppercase', marginBottom: 10 }}>
              Workflow Banks
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
              {(Array.isArray(catalog?.banks) ? catalog.banks : []).map((bank: any) => {
                const key = String(bank?.key || '');
                const active = key === selectedBank;
                return (
                  <button
                    key={key}
                    onClick={() => setSelectedBank(key)}
                    style={{
                      border: `1px solid ${active ? NOLAN_PALETTE.textAccent : NOLAN_PALETTE.border}`,
                      borderRadius: 4,
                      background: active ? '#131313' : 'transparent',
                      color: active ? NOLAN_PALETTE.text : NOLAN_PALETTE.textMuted,
                      fontSize: 9,
                      padding: '3px 8px',
                      cursor: 'pointer',
                      fontFamily: 'monospace',
                    }}
                  >
                    {/* MARKER_167.STATS_WORKFLOW.UI_BANK_TABS.V1 */}
                    {String(bank?.label || key)} {Number(bank?.count || 0)}
                  </button>
                );
              })}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {catalogLoading ? (
                <div style={{ color: '#666', fontSize: 10 }}>Loading workflow catalog...</div>
              ) : workflowRows.length === 0 ? (
                <div style={{ color: '#666', fontSize: 10 }}>No workflows in this bank yet.</div>
              ) : workflowRows.map((row: any) => {
                const workflowId = String(row?.id || '');
                const selected = workflowId && workflowId === String(taskWorkflowBinding?.workflow_id || '');
                return (
                  <div
                    key={`${row.bank}:${workflowId}`}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: 12,
                      padding: '8px 10px',
                      border: `1px solid ${selected ? NOLAN_PALETTE.textAccent : NOLAN_PALETTE.borderDim}`,
                      borderRadius: 6,
                      background: selected ? 'rgba(255,255,255,0.03)' : 'transparent',
                    }}
                  >
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ color: NOLAN_PALETTE.text, fontSize: 11, fontWeight: 700 }}>
                        {String(row?.title || workflowId)}
                      </div>
                      <div style={{ color: '#8e98a4', fontSize: 9, marginTop: 2 }}>
                        {String(row?.family || '-')} · {String(row?.source || '-')}
                      </div>
                      <div style={{ color: '#6f7883', fontSize: 9, marginTop: 2 }}>
                        {String(row?.description || '').trim() || 'No description'}
                      </div>
                    </div>
                    <button
                      onClick={() => handleSelectWorkflow(row)}
                      disabled={savingWorkflowId === workflowId}
                      style={{
                        border: '1px solid #2e2e2e',
                        borderRadius: 4,
                        background: '#151515',
                        color: selected ? NOLAN_PALETTE.textAccent : NOLAN_PALETTE.text,
                        fontSize: 9,
                        padding: '4px 10px',
                        cursor: 'pointer',
                        fontFamily: 'monospace',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {/* MARKER_167.STATS_WORKFLOW.UI_SELECT_ACTION.V1 */}
                      {selected ? 'Selected' : savingWorkflowId === workflowId ? 'Saving...' : 'Select for task'}
                    </button>
                  </div>
                );
              })}
            </div>
            <button
              onClick={() => {
                refreshCatalog();
                refreshBinding();
              }}
              style={{
                marginTop: 10,
                padding: '4px 10px',
                background: 'transparent',
                border: `1px solid ${NOLAN_PALETTE.border}`,
                borderRadius: 4,
                color: NOLAN_PALETTE.textMuted,
                fontSize: 9,
                cursor: 'pointer',
                fontFamily: 'monospace',
              }}
            >
              Refresh workflow banks
            </button>
          </div>

          <div
            style={{
              marginBottom: 20,
              padding: '10px 12px',
              border: `1px solid ${NOLAN_PALETTE.border}`,
              borderRadius: 6,
              background: NOLAN_PALETTE.bg,
            }}
          >
            <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 9, textTransform: 'uppercase', marginBottom: 8 }}>
              MYCO Workflow Guidance
            </div>
            <div style={{ color: NOLAN_PALETTE.text, fontSize: 10, lineHeight: 1.5, marginBottom: 8 }}>
              {workflowMycoHint.loading
                ? 'Loading MYCO workflow hint...'
                : (workflowMycoHint.data?.hint || 'No workflow hint available yet.')}
            </div>
            {workflowMycoHint.data ? (
              <>
                <div style={{ color: '#8e98a4', fontSize: 9, marginBottom: 6 }}>
                  {/* MARKER_167.STATS_WORKFLOW.MYCO_TOOL_PRIORITY.V1 */}
                  tools: {workflowMycoHint.data.ordered_tools.join(' > ') || '-'}
                </div>
                <div style={{ color: '#6f7883', fontSize: 9 }}>
                  retrieval: {workflowMycoHint.data.diagnostics.retrieval_method} · hits:{workflowMycoHint.data.diagnostics.retrieval_count}
                </div>
              </>
            ) : null}
          </div>

          <div
            style={{
              marginBottom: 20,
              padding: '10px 12px',
              border: `1px solid ${NOLAN_PALETTE.border}`,
              borderRadius: 6,
              background: NOLAN_PALETTE.bg,
            }}
          >
            <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 9, textTransform: 'uppercase', marginBottom: 8 }}>
              Workflow Diagnostics
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
              {[
                `workflow:${taskWorkflowBinding?.workflow_family || taskWorkflowBinding?.workflow_id || 'pending'}`,
                `bank:${taskWorkflowBinding?.workflow_bank || 'core'}`,
                `origin:${taskWorkflowBinding?.selection_origin || 'heuristic'}`,
                `binding:${taskWorkflowBinding?.workflow_id ? 'explicit' : 'missing'}`,
                `override:${(taskWorkflowBinding?.selection_origin || 'heuristic') === 'user-selected' ? 'user' : 'heuristic'}`,
              ].map((chip) => (
                <span
                  key={chip}
                  style={{
                    border: `1px solid ${NOLAN_PALETTE.borderDim}`,
                    borderRadius: 999,
                    padding: '2px 8px',
                    color: '#95a0ad',
                    fontSize: 8,
                    lineHeight: 1.5,
                  }}
                >
                  {/* MARKER_167.STATS_WORKFLOW.DIAGNOSTICS.V1 */}
                  {chip}
                </span>
              ))}
            </div>
            <div style={{ color: '#6f7883', fontSize: 9 }}>
              graph:{String(diagnostics.buildDesign?.verifier?.decision || '-')} · runtime:{diagnostics.runtimeHealth?.ok ? 'ok' : 'down'}
            </div>
          </div>
        </>
      ) : null}

      {/* Summary row */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        <StatBox label="Total Runs" value={data.total_pipelines ?? 0} />
        <StatBox label="Success Rate" value={`${Math.round(data.success_rate ?? 0)}%`} />
        <StatBox label="Avg Duration" value={`${Math.round(data.avg_duration_s ?? 0)}s`} />
        <StatBox label="Total Cost" value={`$${(data.total_cost_usd ?? 0).toFixed(2)}`} />
      </div>

      {/* Token stats */}
      <div style={{
        display: 'flex',
        gap: 16,
        marginBottom: 20,
        padding: '8px 12px',
        background: NOLAN_PALETTE.bg,
        borderRadius: 6,
      }}>
        <StatBox label="LLM Calls" value={data.total_llm_calls} />
        <StatBox label="Tokens" value={
          data.total_tokens > 1000000 ? `${(data.total_tokens / 1000000).toFixed(1)}M` :
          data.total_tokens > 1000 ? `${(data.total_tokens / 1000).toFixed(0)}K` :
          data.total_tokens
        } />
      </div>

      {/* Per-team breakdown */}
      {presets.length > 0 && (
        <>
          <div style={{ color: NOLAN_PALETTE.textMuted, fontSize: 9, marginBottom: 8, textTransform: 'uppercase' }}>
            Team Breakdown
          </div>
          {presets.map(([preset, stats]) => (
            <div
              key={preset}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '6px 0',
                borderBottom: `1px solid ${NOLAN_PALETTE.border}`,
              }}
            >
              <span style={{ color: NOLAN_PALETTE.textAccent, fontSize: 10, width: 100 }}>
                {preset}
              </span>
              <span style={{ color: NOLAN_PALETTE.text, fontSize: 10 }}>
                {stats.count} runs
              </span>
              <span style={{
                color: stats.success_rate >= 70 ? '#8a8' : NEUTRAL_FAIL,
                fontSize: 10,
              }}>
                {Math.round(stats.success_rate)}%
              </span>
              <span style={{ color: '#555', fontSize: 10 }}>
                ~{Math.round(stats.avg_duration_s)}s
              </span>
            </div>
          ))}
        </>
      )}

      {/* MARKER_155.STATS.UI: Agent Performance Section */}
      <AgentPerformanceSection />

      {/* Refresh button */}
      <button
        onClick={refresh}
        style={{
          marginTop: 16,
          padding: '4px 12px',
          background: NOLAN_PALETTE.bg,
          border: `1px solid ${NOLAN_PALETTE.border}`,
          borderRadius: 4,
          color: NOLAN_PALETTE.textMuted,
          fontSize: 9,
          cursor: 'pointer',
          fontFamily: 'monospace',
        }}
      >
        ↻ Refresh
      </button>
    </div>
  );
}

export function MiniStats({ context }: MiniStatsProps) {
  return (
    <MiniWindow
      windowId="stats" // MARKER_155.DRAGGABLE.012: Unique ID for position persistence
      title="Stats"
      icon="||"
      position="top-right"
      compactWidth={200}
      compactHeight={176}
      compactContent={<StatsCompact context={context} />}
      expandedContent={<StatsExpanded context={context} />}
    />
  );
}
