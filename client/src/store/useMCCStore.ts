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

// MARKER_155A.P2.PIN_LAYOUT: Persist manual node positions per graph context.
export interface NodePinPosition {
  x: number;
  y: number;
}

export type LayoutPinsMap = Record<string, Record<string, NodePinPosition>>;
export type FocusRestorePolicy = 'scope_first' | 'selection_first';
export type FocusRestoreSource = 'current' | 'memory' | 'default' | null;

const LAYOUT_PINS_STORAGE_KEY = 'mcc_layout_pins_v1';
const FOCUS_RESTORE_POLICY_STORAGE_KEY = 'mcc_focus_restore_policy_v1';

function loadLayoutPins(): LayoutPinsMap {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(LAYOUT_PINS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function saveLayoutPins(pins: LayoutPinsMap): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(LAYOUT_PINS_STORAGE_KEY, JSON.stringify(pins));
  } catch {
    // ignore persistence errors
  }
}

function loadFocusRestorePolicy(): FocusRestorePolicy {
  if (typeof window === 'undefined') return 'selection_first';
  try {
    const raw = window.localStorage.getItem(FOCUS_RESTORE_POLICY_STORAGE_KEY);
    if (raw === 'scope_first' || raw === 'selection_first') return raw;
    return 'selection_first';
  } catch {
    return 'selection_first';
  }
}

function saveFocusRestorePolicy(policy: FocusRestorePolicy): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(FOCUS_RESTORE_POLICY_STORAGE_KEY, policy);
  } catch {
    // ignore persistence errors
  }
}

// ── Store ──

// MARKER_153.1C: Navigation level type for Matryoshka drill-down
// MARKER_154.1B: Added 'first_run' level for Phase 154 Matryoshka simplification
export type NavLevel = 'first_run' | 'roadmap' | 'tasks' | 'workflow' | 'running' | 'results';

// ── MARKER_154.1B: Level Configuration (single source of truth) ──
export interface ActionDef {
  label: string;
  icon: string;
  action: string;
  shortcut?: string;
  primary?: boolean;
}

export interface LevelConfig {
  label: string;
  icon: string;
  actions: ActionDef[];
}

export const LEVEL_CONFIG: Record<NavLevel, LevelConfig> = {
  first_run: {
    label: 'Welcome',
    icon: '🚀',
    actions: [
      { label: 'Folder', icon: '📁', action: 'selectFolder', shortcut: '1', primary: true },
      { label: 'URL', icon: '🔗', action: 'enterUrl', shortcut: '2' },
      { label: 'Text', icon: '📝', action: 'describeText', shortcut: '3' },
    ],
  },
  roadmap: {
    label: 'Roadmap',
    icon: '🗺',
    actions: [
      { label: 'Launch', icon: '▶', action: 'launch', shortcut: '1', primary: true },
      { label: 'Ask', icon: '💬', action: 'askArchitect', shortcut: '2' },
      { label: 'Add', icon: '+', action: 'addTask', shortcut: '3' },
    ],
  },
  tasks: {
    label: 'Tasks',
    icon: '📋',
    actions: [
      { label: 'Launch', icon: '▶', action: 'launchTask', shortcut: '1', primary: true },
      { label: 'Edit', icon: '✏', action: 'editTask', shortcut: '2' },
      { label: 'Back', icon: '←', action: 'goBack', shortcut: 'Esc' },
    ],
  },
  workflow: {
    label: 'Workflow',
    icon: '⚙',
    actions: [
      { label: 'Execute', icon: '▶', action: 'execute', shortcut: '1', primary: true },
      { label: 'Edit', icon: '✏', action: 'toggleEdit', shortcut: '2' },
      { label: 'Back', icon: '←', action: 'goBack', shortcut: 'Esc' },
    ],
  },
  running: {
    label: 'Running',
    icon: '▶',
    actions: [
      { label: 'Pause', icon: '⏸', action: 'pause', shortcut: '1', primary: true },
      { label: 'Cancel', icon: '⏹', action: 'cancel', shortcut: '2' },
      { label: 'Back', icon: '←', action: 'goBack', shortcut: 'Esc' },
    ],
  },
  results: {
    label: 'Results',
    icon: '📊',
    actions: [
      { label: 'Accept', icon: '✓', action: 'apply', shortcut: '1', primary: true },
      { label: 'Redo', icon: '↻', action: 'redo', shortcut: '2' },
      { label: 'Back', icon: '←', action: 'goBack', shortcut: 'Esc' },
    ],
  },
};

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

  // MARKER_155.4: Camera position for zoom-based navigation
  cameraPosition: { x: number; y: number; zoom: number } | null;
  focusedNodeId: string | null;
  focusRestorePolicy: FocusRestorePolicy;
  focusRestoreSource: FocusRestoreSource;
  // MARKER_155A.P2.PIN_LAYOUT: Manual layout persistence buckets.
  layoutPins: LayoutPinsMap;

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
  // MARKER_154.1B: Direct level jump (no history push — used by breadcrumb clicks)
  goToLevel: (level: NavLevel) => void;
  // MARKER_155.4: Camera position actions
  setCameraPosition: (pos: { x: number; y: number; zoom: number } | null) => void;
  setFocusedNodeId: (nodeId: string | null) => void;
  setFocusRestorePolicy: (policy: FocusRestorePolicy) => void;
  setFocusRestoreSource: (source: FocusRestoreSource) => void;
  // MARKER_155A.P2.PIN_LAYOUT: Layout pin actions.
  setLayoutPinsForKey: (key: string, positions: Record<string, NodePinPosition>) => void;
  clearLayoutPinsForKey: (key: string) => void;
  // MARKER_155A.G21.SINGLE_CANVAS_STATE: Focus roadmap branch without level switch.
  setRoadmapFocus: (roadmapNodeId: string | null) => void;
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

  // MARKER_155A.P0.FLOW_GATE: Safe bootstrap level to avoid premature drill UI
  navLevel: 'first_run' as NavLevel,
  navRoadmapNodeId: '',
  navTaskId: '',
  navHistory: [] as NavLevel[],
  hasProject: false,
  projectConfig: null,

  // MARKER_155.4: Camera position initial state
  cameraPosition: null,
  focusedNodeId: null,
  focusRestorePolicy: loadFocusRestorePolicy(),
  focusRestoreSource: null,
  layoutPins: loadLayoutPins(),

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
  // MARKER_154.1B: first_run level when no project configured
  initMCC: async () => {
    try {
      const res = await fetch(`${API_BASE}/mcc/init`);
      if (!res.ok) {
        // No backend → first_run
        set({ hasProject: false, projectConfig: null, navLevel: 'first_run', navHistory: [] });
        return;
      }
      const data = await res.json();

      if (data.has_project && data.session_state) {
        // MARKER_155A.P0.FLOW_GATE:
        // Do not restore deep drill levels on startup. Users should enter from roadmap
        // after project init to keep context predictable.
        set({
          hasProject: true,
          projectConfig: data.project_config,
          navLevel: 'roadmap',
          navRoadmapNodeId: '',
          navTaskId: '',
          navHistory: [],
        });
      } else {
        // MARKER_154.1B: No project → first_run level
        set({ hasProject: false, projectConfig: null, navLevel: 'first_run', navHistory: [] });
      }
    } catch (err) {
      console.error('[MCC] Init failed:', err);
      set({ hasProject: false, projectConfig: null, navLevel: 'first_run', navHistory: [] });
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

  // ── MARKER_154.1B: Direct level jump — resets history up to target ──
  goToLevel: (level) => {
    const prev = get();
    // Find if the target level exists in history — trim history up to it
    const histIdx = prev.navHistory.indexOf(level);
    const newHistory = histIdx >= 0
      ? prev.navHistory.slice(0, histIdx)
      : []; // Jump to arbitrary level = reset history
    const newState = {
      navLevel: level,
      navHistory: newHistory,
    };
    set(newState);
    _persistState({
      level: newState.navLevel,
      roadmapNodeId: prev.navRoadmapNodeId,
      taskId: prev.navTaskId,
      history: newState.navHistory,
    });
  },

  // MARKER_155.4: Camera position actions
  setCameraPosition: (pos) => set({ cameraPosition: pos }),
  setFocusedNodeId: (nodeId) => set({ focusedNodeId: nodeId }),
  setFocusRestorePolicy: (policy) => {
    saveFocusRestorePolicy(policy);
    set({ focusRestorePolicy: policy });
  },
  setFocusRestoreSource: (source) => set({ focusRestoreSource: source }),
  setLayoutPinsForKey: (key, positions) => set((state) => {
    const next = {
      ...state.layoutPins,
      [key]: positions,
    };
    saveLayoutPins(next);
    return { layoutPins: next };
  }),
  clearLayoutPinsForKey: (key) => set((state) => {
    if (!state.layoutPins[key]) return state;
    const next = { ...state.layoutPins };
    delete next[key];
    saveLayoutPins(next);
    return { layoutPins: next };
  }),
  setRoadmapFocus: (roadmapNodeId) => set({ navRoadmapNodeId: roadmapNodeId || '' }),
}));
