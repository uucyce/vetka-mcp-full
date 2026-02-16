/**
 * MARKER_143.P1: Zustand store for MCC (Mycelium Command Center) unified workspace.
 * Replaces DevPanel's local useState for tasks, heartbeat, agents, presets.
 * Shared by MCCTaskList, MCCDetailPanel, PresetDropdown, StreamPanel.
 *
 * @phase 143
 * @status active
 * @depends zustand, TaskCard types
 */
import { create } from 'zustand';
import type { TaskData } from '../components/panels/TaskCard';

const API_BASE = 'http://localhost:5001/api';
const API_DEBUG = `${API_BASE}/debug`;

// ── Types ──

export interface StreamEvent {
  id: string;
  ts: number;
  role: string;
  message: string;
  taskId?: string;
}

export interface HeartbeatSettings {
  enabled: boolean;
  interval: number;
  last_tick: number;
  total_ticks: number;
  tasks_dispatched: number;
}

export interface AgentStatus {
  agent_name: string;
  agent_type: string;
  task_id: string;
  task_title: string;
  status: string;
  elapsed_seconds: number;
}

export interface PresetConfig {
  description: string;
  provider: string;
  roles: Record<string, string>;
}

// ── Store ──

// MARKER_153.1C: Navigation level type for Matryoshka drill-down
export type NavLevel = 'roadmap' | 'tasks' | 'workflow' | 'running' | 'results';

interface MCCState {
  // Task board
  tasks: TaskData[];
  summary: { total: number; by_status: Record<string, number> } | null;
  tasksLoading: boolean;

  // Selection
  selectedTaskId: string | null;

  // Presets
  activePreset: string;
  presets: Record<string, PresetConfig>;

  // Filters
  statusFilter: 'all' | 'pending' | 'running' | 'done';

  // Heartbeat
  heartbeat: HeartbeatSettings | null;

  // Active agents
  activeAgents: AgentStatus[];

  // Stream
  streamEvents: StreamEvent[];

  // MARKER_144.6: Edit mode for DAG workflow editor
  editMode: boolean;

  // MARKER_153.1C: Navigation state (Matryoshka levels)
  navLevel: NavLevel;
  navRoadmapNodeId: string;
  navTaskId: string;
  navHistory: NavLevel[];
  hasProject: boolean;
  projectConfig: Record<string, any> | null;

  // Actions
  fetchTasks: () => Promise<void>;
  addTask: (title: string, preset: string, phaseType: string, tags: string[], selectedKey?: any) => Promise<string | null>;
  dispatchTask: (taskId: string, preset?: string, selectedKey?: any) => Promise<void>;
  dispatchNext: (selectedKey?: any) => Promise<void>;
  selectTask: (taskId: string | null) => void;
  setActivePreset: (preset: string) => void;
  setStatusFilter: (filter: 'all' | 'pending' | 'running' | 'done') => void;
  fetchPresets: () => Promise<void>;
  updateHeartbeat: (updates: Partial<HeartbeatSettings>) => Promise<void>;
  pushStreamEvent: (event: Omit<StreamEvent, 'id' | 'ts'>) => void;
  cancelTask: (taskId: string) => Promise<void>;
  removeTask: (taskId: string) => Promise<void>;
  changePriority: (taskId: string, priority: number) => Promise<void>;
  // MARKER_144.6: Toggle edit mode
  setEditMode: (mode: boolean) => void;
  toggleEditMode: () => void;
  // MARKER_144.10: Execute workflow (convert nodes → tasks → dispatch)
  executeWorkflow: (workflowId: string, preset?: string, dryRun?: boolean) => Promise<{
    success: boolean;
    count?: number;
    tasks_created?: string[];
    tasks_dispatched?: string[];
    planned_tasks?: any[];
    error?: string;
  }>;
  // MARKER_153.1C: Navigation actions
  initMCC: () => Promise<void>;
  drillDown: (level: NavLevel, context?: { roadmapNodeId?: string; taskId?: string }) => void;
  goBack: () => void;
}

const MAX_STREAM_EVENTS = 30;

// MARKER_153.1C: Debounced state persist to server
let _saveTimer: ReturnType<typeof setTimeout> | null = null;
const _persistState = (state: { level: NavLevel; roadmapNodeId: string; taskId: string; history: NavLevel[] }) => {
  if (_saveTimer) clearTimeout(_saveTimer);
  _saveTimer = setTimeout(() => {
    fetch(`${API_BASE}/mcc/state`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        level: state.level,
        roadmap_node_id: state.roadmapNodeId,
        task_id: state.taskId,
        history: state.history,
      }),
    }).catch(() => {}); // Silent fail — state is also in memory
  }, 500);
};

export const useMCCStore = create<MCCState>((set, get) => ({
  // Initial state
  tasks: [],
  summary: null,
  tasksLoading: false,
  selectedTaskId: null,
  activePreset: 'dragon_silver',
  presets: {},
  statusFilter: 'all',
  heartbeat: null,
  activeAgents: [],
  streamEvents: [],
  editMode: true, // MARKER_151.3A: Edit mode ON by default

  // MARKER_153.1C: Navigation initial state
  navLevel: 'roadmap' as NavLevel,
  navRoadmapNodeId: '',
  navTaskId: '',
  navHistory: [] as NavLevel[],
  hasProject: false,
  projectConfig: null,

  // ── Fetch tasks + agents + heartbeat ──
  fetchTasks: async () => {
    set({ tasksLoading: true });
    try {
      const [tasksRes, agentsRes, hbRes] = await Promise.all([
        fetch(`${API_DEBUG}/task-board`).catch(() => null),
        fetch(`${API_DEBUG}/task-board/active-agents`).catch(() => null),
        fetch(`${API_DEBUG}/heartbeat/settings`).catch(() => null),
      ]);

      if (tasksRes?.ok) {
        const data = await tasksRes.json();
        set({ tasks: data.tasks || [], summary: data.summary || null });
      }
      if (agentsRes?.ok) {
        const data = await agentsRes.json();
        set({ activeAgents: data.agents || [] });
      }
      if (hbRes?.ok) {
        const data = await hbRes.json();
        if (data.success) set({ heartbeat: data });
      }
    } catch (err) {
      console.error('[MCC] Fetch failed:', err);
    } finally {
      set({ tasksLoading: false });
    }
  },

  // ── Add task ──
  addTask: async (title, preset, phaseType, tags, selectedKey) => {
    try {
      const res = await fetch(`${API_DEBUG}/task-board/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, preset, phase_type: phaseType, tags }),
      });
      if (res.ok) {
        const data = await res.json();
        get().fetchTasks();
        return data.task_id || null;
      }
    } catch (err) {
      console.error('[MCC] Add task failed:', err);
    }
    return null;
  },

  // ── Dispatch specific task ──
  dispatchTask: async (taskId, preset, selectedKey) => {
    try {
      await fetch(`${API_DEBUG}/task-board/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: taskId,
          selected_key: selectedKey || undefined,
          ...(preset && { preset }),
        }),
      });
      get().fetchTasks();
    } catch (err) {
      console.error('[MCC] Dispatch failed:', err);
    }
  },

  // ── Dispatch next highest-priority ──
  dispatchNext: async (selectedKey) => {
    try {
      await fetch(`${API_DEBUG}/task-board/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_key: selectedKey || undefined }),
      });
      get().fetchTasks();
    } catch (err) {
      console.error('[MCC] Dispatch next failed:', err);
    }
  },

  // ── Select task (left panel click) ──
  selectTask: (taskId) => set({ selectedTaskId: taskId }),

  // ── Preset management ──
  setActivePreset: (preset) => set({ activePreset: preset }),

  fetchPresets: async () => {
    try {
      const res = await fetch(`${API_BASE}/pipeline/presets`);
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          set({ presets: data.presets || {} });
          if (data.default_preset) {
            set({ activePreset: data.default_preset });
          }
        }
      }
    } catch (err) {
      console.error('[MCC] Fetch presets failed:', err);
    }
  },

  // ── Filter ──
  setStatusFilter: (filter) => set({ statusFilter: filter }),

  // ── Heartbeat ──
  updateHeartbeat: async (updates) => {
    try {
      const res = await fetch(`${API_DEBUG}/heartbeat/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          set(state => ({
            heartbeat: state.heartbeat ? {
              ...state.heartbeat,
              enabled: data.enabled ?? updates.enabled ?? state.heartbeat.enabled,
              interval: data.interval ?? updates.interval ?? state.heartbeat.interval,
            } : null,
          }));
        }
      }
    } catch (err) {
      console.error('[MCC] Heartbeat update failed:', err);
    }
  },

  // ── Stream ──
  pushStreamEvent: (event) => {
    const next: StreamEvent = {
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      ts: Date.now(),
      role: event.role || 'pipeline',
      message: event.message || '',
      taskId: event.taskId,
    };
    set(state => ({
      streamEvents: [next, ...state.streamEvents].slice(0, MAX_STREAM_EVENTS),
    }));
  },

  // ── Cancel task ──
  cancelTask: async (taskId) => {
    try {
      await fetch(`${API_DEBUG}/task-board/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId }),
      });
      get().fetchTasks();
    } catch (err) {
      console.error('[MCC] Cancel failed:', err);
    }
  },

  // ── Remove task ──
  removeTask: async (taskId) => {
    try {
      await fetch(`${API_DEBUG}/task-board/${taskId}`, { method: 'DELETE' });
      get().fetchTasks();
    } catch (err) {
      console.error('[MCC] Remove failed:', err);
    }
  },

  // ── MARKER_144.6: Edit mode ──
  setEditMode: (mode) => set({ editMode: mode }),
  toggleEditMode: () => set(state => ({ editMode: !state.editMode })),

  // ── MARKER_144.10: Execute workflow ──
  executeWorkflow: async (workflowId, preset, dryRun = false) => {
    try {
      const activePreset = preset || get().activePreset;
      const res = await fetch(`${API_BASE}/workflows/${encodeURIComponent(workflowId)}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset: activePreset, dry_run: dryRun }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success && !dryRun) {
          // Refresh task list after execution
          get().fetchTasks();
          // Push stream event
          get().pushStreamEvent({
            role: 'workflow',
            message: `Executed "${data.workflow_name}": ${data.count} tasks created, ${data.tasks_dispatched?.length || 0} dispatched`,
          });
        }
        return data;
      }
      const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
      return { success: false, error: err.error || err.detail || `HTTP ${res.status}` };
    } catch (err) {
      console.error('[MCC] Execute workflow failed:', err);
      return { success: false, error: String(err) };
    }
  },

  // ── Change priority ──
  changePriority: async (taskId, priority) => {
    try {
      await fetch(`${API_DEBUG}/task-board/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ priority }),
      });
      get().fetchTasks();
    } catch (err) {
      console.error('[MCC] Priority change failed:', err);
    }
  },

  // ── MARKER_153.1C: Init MCC — load project config + session state ──
  initMCC: async () => {
    try {
      const res = await fetch(`${API_BASE}/mcc/init`);
      if (!res.ok) return;
      const data = await res.json();

      if (data.has_project && data.session_state) {
        set({
          hasProject: true,
          projectConfig: data.project_config,
          navLevel: (data.session_state.level || 'roadmap') as NavLevel,
          navRoadmapNodeId: data.session_state.roadmap_node_id || '',
          navTaskId: data.session_state.task_id || '',
          navHistory: data.session_state.history || [],
        });
      } else {
        set({ hasProject: false, projectConfig: null });
      }
    } catch (err) {
      console.error('[MCC] Init failed:', err);
    }
  },

  // ── MARKER_153.1C: Drill down into next level ──
  drillDown: (level, context) => {
    const prev = get();
    const newState = {
      navLevel: level,
      navRoadmapNodeId: context?.roadmapNodeId ?? prev.navRoadmapNodeId,
      navTaskId: context?.taskId ?? prev.navTaskId,
      navHistory: [...prev.navHistory, prev.navLevel],
    };
    set(newState);
    _persistState({
      level: newState.navLevel,
      roadmapNodeId: newState.navRoadmapNodeId,
      taskId: newState.navTaskId,
      history: newState.navHistory,
    });
  },

  // ── MARKER_153.1C: Go back one level ──
  goBack: () => {
    const prev = get();
    const history = [...prev.navHistory];
    const prevLevel = history.pop() || 'roadmap';
    const newState = {
      navLevel: prevLevel as NavLevel,
      navHistory: history,
    };
    set(newState);
    _persistState({
      level: newState.navLevel,
      roadmapNodeId: prev.navRoadmapNodeId,
      taskId: prev.navTaskId,
      history: newState.navHistory,
    });
  },
}));
