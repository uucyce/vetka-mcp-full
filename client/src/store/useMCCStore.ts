/**
 * MARKER_143.P1: Zustand store for MCC (Mycelium Command Center) unified workspace.
 * Replaces DevPanel's local useState for tasks, heartbeat, agents, presets.
 * Shared by active MCC surfaces (MyceliumCommandCenter + mini windows + stream/actions).
 *
 * @phase 143
 * @status active
 * @depends zustand, TaskCard types
 */
import { create } from 'zustand';
import type { TaskData } from '../components/panels/TaskCard';
import { useStore } from './useStore';
import { API_BASE } from '../config/api.config';

const API_DEBUG = `${API_BASE}/debug`;

// ── Types ──

export interface StreamEvent {
  id: string;
  ts: number;
  role: string;
  message: string;
  taskId?: string;
  // MARKER_174.B: Structured metadata for rich rendering (REFLEX pills, agent chat)
  metadata?: {
    type?: string;
    event?: string;
    tools?: Array<{ id: string; score?: number }>;
    tools_used?: string[];
    feedback_count?: number;
    passed?: boolean;
    original_count?: number;
    filtered_count?: number;
    phase?: string;
    tier?: string;
    subtask?: string;
    [key: string]: any;
  };
}

export interface HeartbeatSettings {
  enabled: boolean;
  interval: number;
  last_tick: number;
  total_ticks: number;
  tasks_dispatched: number;
  monitor_all?: boolean;
  profile_mode?: 'global' | 'project' | 'workflow' | 'task' | string;
  project_id?: string;
  workflow_family?: string;
  task_id?: string;
  localguys_enabled?: boolean;
  localguys_idle_sec?: number;
  localguys_action?: 'auto' | 'nudge' | 'resume_task' | string;
  effective_profile?: {
    mode?: 'global' | 'project' | 'workflow' | 'task' | string;
    project_id?: string;
    workflow_family?: string;
    task_id?: string;
    key?: string;
  };
}

export interface AgentStatus {
  agent_name: string;
  agent_type: string;
  task_id: string;
  task_title: string;
  status: string;
  elapsed_seconds: number;
}

export interface TaskCreateOptions {
  module?: string;
  primary_node_id?: string;
  affected_nodes?: string[];
  workflow_id?: string;
  team_profile?: string;
  task_origin?: 'architect' | 'chat' | 'manual' | 'system' | string;
  source?: string;
}

export interface AttachedTaskCreateOptions {
  title?: string;
  description?: string;
  preset?: string;
  phase_type?: string;
  priority?: number;
  node_id: string;
  node_label?: string;
  node_path?: string;
  node_graph_kind?: string;
  roadmap_node_id?: string;
  project_id?: string;
  project_lane?: string;
  tags?: string[];
  affected_node_ids?: string[];
  architecture_docs?: string[];
  closure_files?: string[];
}

export interface PresetConfig {
  description: string;
  provider: string;
  roles: Record<string, string>;
}

export interface MCCProjectTab {
  project_id: string;
  display_name?: string;
  project_kind?: string;
  tab_visibility?: string;
  source_type: string;
  execution_mode?: string;
  source_path: string;
  sandbox_path: string;
  workspace_path?: string;
  context_scope_path?: string;
  quota_gb?: number;
  created_at?: string;
  last_opened_at?: string;
}

// MARKER_155A.P2.PIN_LAYOUT: Persist manual node positions per graph context.
export interface NodePinPosition {
  x: number;
  y: number;
}

export type LayoutPinsMap = Record<string, Record<string, NodePinPosition>>;
export type FocusRestorePolicy = 'scope_first' | 'selection_first';
export type FocusRestoreSource = 'current' | 'memory' | 'default' | null;
export interface MCCSelectedKey {
  provider: string;
  key_masked: string;
}
export interface MCCTaskFilters {
  status: string;
  phase: string;
  preset: string;
  search: string;
}

const LAYOUT_PINS_STORAGE_KEY = 'mcc_layout_pins_v1';
const FOCUS_RESTORE_POLICY_STORAGE_KEY = 'mcc_focus_restore_policy_v1';
const MYCO_HELPER_MODE_STORAGE_KEY = 'mcc_myco_helper_mode_v1';
const MCC_SELECTED_KEY_STORAGE_KEY = 'mcc_selected_key';
const MCC_FAVORITE_KEYS_STORAGE_KEY = 'mcc_favorite_keys';
const MCC_TASK_FILTERS_STORAGE_KEY = 'mcc_task_filters';
const MCC_WINDOW_SESSION_STORAGE_KEY = 'mcc_window_session_id_v1';
export const MCC_PROJECT_REGISTRY_SYNC_KEY = 'mcc_project_registry_sync_v1';

const DEFAULT_TASK_FILTERS: MCCTaskFilters = {
  status: 'all',
  phase: 'all',
  preset: 'all',
  search: '',
};

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

function loadMycoHelperMode(): MycoHelperMode {
  if (typeof window === 'undefined') return 'off';
  try {
    const raw = window.localStorage.getItem(MYCO_HELPER_MODE_STORAGE_KEY);
    if (raw === 'off' || raw === 'passive' || raw === 'active') return raw;
    return 'off';
  } catch {
    return 'off';
  }
}

function saveMycoHelperMode(mode: MycoHelperMode): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(MYCO_HELPER_MODE_STORAGE_KEY, mode);
  } catch {
    // ignore persistence errors
  }
}

function loadSelectedKey(): MCCSelectedKey | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(MCC_SELECTED_KEY_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (
      parsed
      && typeof parsed === 'object'
      && typeof parsed.provider === 'string'
      && typeof parsed.key_masked === 'string'
    ) {
      return { provider: parsed.provider, key_masked: parsed.key_masked };
    }
    return null;
  } catch {
    return null;
  }
}

function saveSelectedKey(key: MCCSelectedKey | null): void {
  if (typeof window === 'undefined') return;
  try {
    if (!key) {
      window.localStorage.removeItem(MCC_SELECTED_KEY_STORAGE_KEY);
      return;
    }
    window.localStorage.setItem(MCC_SELECTED_KEY_STORAGE_KEY, JSON.stringify(key));
  } catch {
    // ignore persistence errors
  }
}

function loadFavoriteKeys(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(MCC_FAVORITE_KEYS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((item) => typeof item === 'string') : [];
  } catch {
    return [];
  }
}

function saveFavoriteKeys(keys: string[]): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(MCC_FAVORITE_KEYS_STORAGE_KEY, JSON.stringify(keys));
  } catch {
    // ignore persistence errors
  }
}

function loadTaskFilters(): MCCTaskFilters {
  if (typeof window === 'undefined') return DEFAULT_TASK_FILTERS;
  try {
    const raw = window.localStorage.getItem(MCC_TASK_FILTERS_STORAGE_KEY);
    if (!raw) return DEFAULT_TASK_FILTERS;
    const parsed = JSON.parse(raw);
    return {
      ...DEFAULT_TASK_FILTERS,
      ...(parsed && typeof parsed === 'object' ? parsed : {}),
    };
  } catch {
    return DEFAULT_TASK_FILTERS;
  }
}

function saveTaskFilters(filters: MCCTaskFilters): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(MCC_TASK_FILTERS_STORAGE_KEY, JSON.stringify(filters));
  } catch {
    // ignore persistence errors
  }
}

function broadcastProjectRegistrySync(projectId: string, windowSessionId: string, reason: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(
      MCC_PROJECT_REGISTRY_SYNC_KEY,
      JSON.stringify({
        project_id: String(projectId || ''),
        window_session_id: String(windowSessionId || ''),
        reason: String(reason || 'refresh'),
        ts: Date.now(),
      }),
    );
  } catch {
    // ignore storage sync errors
  }
}

function createWindowSessionId(): string {
  const randomPart = Math.random().toString(36).slice(2, 10);
  return `mccwin_${Date.now().toString(36)}_${randomPart}`;
}

function loadWindowSessionId(): string {
  if (typeof window === 'undefined') return 'mccwin_server';
  try {
    const existing = window.sessionStorage.getItem(MCC_WINDOW_SESSION_STORAGE_KEY);
    if (existing) return existing;
    const next = createWindowSessionId();
    window.sessionStorage.setItem(MCC_WINDOW_SESSION_STORAGE_KEY, next);
    return next;
  } catch {
    return createWindowSessionId();
  }
}

// ── Store ──

// MARKER_153.1C: Navigation level type for Matryoshka drill-down
// MARKER_154.1B: Added 'first_run' level for Phase 154 Matryoshka simplification
export type NavLevel = 'first_run' | 'roadmap' | 'tasks' | 'workflow' | 'running' | 'results';
export type WorkflowSourceMode = 'runtime' | 'design' | 'predict';
export type MycoHelperMode = 'off' | 'passive' | 'active';

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
    // MARKER_155A.G24.ACTION_SEMANTICS_REVIEW:
    // Legacy labels kept for backward compatibility with FooterActionBar wiring.
    // Roadmap plan tracks semantic rename/context-gating alignment.
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
      // MARKER_176.1F: Create roadmap-derived tasks from the current roadmap focus.
      { label: 'Create Tasks', icon: '📋', action: 'createTasksFromRoadmap', shortcut: '2' },
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
      { label: 'Apply', icon: '✓', action: 'apply', shortcut: '1', primary: true },
      // MARKER_176.3F: Reject opens feedback/requeue flow for result review.
      { label: 'Reject', icon: '✕', action: 'reject', shortcut: '2' },
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

  // MARKER_175.0D: Standalone MCC key management
  selectedKey: MCCSelectedKey | null;
  favoriteKeys: string[];

  // Filters
  statusFilter: 'all' | 'pending' | 'running' | 'done';
  taskFilters: MCCTaskFilters;

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
  // MARKER_161.7.MULTIPROJECT.UI.ACTIVE_PROJECT_STATE.V1:
  // Current store is single-project; future tab-shell extends this into activeProjectId + projectTabs[].
  activeProjectId: string;
  windowSessionId: string;
  projectTabs: MCCProjectTab[];
  projectTabsLoading: boolean;
  projectTabsUpdatedAt: string;
  projectTabsHiddenCount: number;
  // MARKER_189.6A: Toggle to show tasks from all projects vs active only
  showAllProjectsTasks: boolean;

  // MARKER_155.4: Camera position for zoom-based navigation
  cameraPosition: { x: number; y: number; zoom: number } | null;
  workflowSourceMode: WorkflowSourceMode;
  helperMode: MycoHelperMode;
  focusedNodeId: string | null;
  focusRestorePolicy: FocusRestorePolicy;
  focusRestoreSource: FocusRestoreSource;
  // MARKER_155A.P2.PIN_LAYOUT: Manual layout persistence buckets.
  layoutPins: LayoutPinsMap;

  // Actions
  fetchTasks: () => Promise<void>;
  addTask: (title: string, preset: string, phaseType: string, tags: string[], selectedKey?: any, options?: TaskCreateOptions) => Promise<string | null>;
  addAttachedTask: (options: AttachedTaskCreateOptions) => Promise<string | null>;
  attachTaskToNode: (taskId: string, options: AttachedTaskCreateOptions) => Promise<boolean>;
  dispatchTask: (taskId: string, preset?: string, selectedKey?: any) => Promise<void>;
  dispatchNext: (selectedKey?: any) => Promise<void>;
  selectTask: (taskId: string | null) => void;
  setActivePreset: (preset: string) => void;
  setSelectedKey: (key: MCCSelectedKey | null) => void;
  toggleFavoriteKey: (key: string) => void;
  setStatusFilter: (filter: 'all' | 'pending' | 'running' | 'done') => void;
  setTaskFilter: (key: keyof MCCTaskFilters, value: string) => void;
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
  initMCC: (projectIdOverride?: string) => Promise<void>;
  refreshProjectTabs: () => Promise<void>;
  activateProjectTab: (projectId: string) => Promise<boolean>;
  announceProjectRegistryChanged: (projectId?: string, reason?: string) => void;
  drillDown: (level: NavLevel, context?: { roadmapNodeId?: string; taskId?: string }) => void;
  goBack: () => void;
  // MARKER_154.1B: Direct level jump (no history push — used by breadcrumb clicks)
  goToLevel: (level: NavLevel) => void;
  // MARKER_155.4: Camera position actions
  setCameraPosition: (pos: { x: number; y: number; zoom: number } | null) => void;
  setWorkflowSourceMode: (mode: WorkflowSourceMode) => void;
  setHelperMode: (mode: MycoHelperMode) => void;
  setFocusedNodeId: (nodeId: string | null) => void;
  setFocusRestorePolicy: (policy: FocusRestorePolicy) => void;
  setFocusRestoreSource: (source: FocusRestoreSource) => void;
  // MARKER_155A.P2.PIN_LAYOUT: Layout pin actions.
  setLayoutPinsForKey: (key: string, positions: Record<string, NodePinPosition>) => void;
  clearLayoutPinsForKey: (key: string) => void;
  // MARKER_155A.G21.SINGLE_CANVAS_STATE: Focus roadmap branch without level switch.
  setRoadmapFocus: (roadmapNodeId: string | null) => void;
  // MARKER_156.MCC_KEY_PERSIST.001: Persist full MCC session state on demand.
  persistSessionState: () => void;
}

const MAX_STREAM_EVENTS = 30;
const INITIAL_SELECTED_KEY = loadSelectedKey();
const INITIAL_FAVORITE_KEYS = loadFavoriteKeys();
const INITIAL_TASK_FILTERS = loadTaskFilters();
const INITIAL_WINDOW_SESSION_ID = loadWindowSessionId();

if (INITIAL_SELECTED_KEY) {
  useStore.getState().setSelectedKey(INITIAL_SELECTED_KEY);
}
if (INITIAL_FAVORITE_KEYS.length > 0) {
  useStore.getState().setFavoriteKeys(INITIAL_FAVORITE_KEYS);
}

// MARKER_153.1C: Debounced state persist to server
let _saveTimer: ReturnType<typeof setTimeout> | null = null;
const _persistState = (state: { level: NavLevel; roadmapNodeId: string; taskId: string; history: NavLevel[] }) => {
  if (_saveTimer) clearTimeout(_saveTimer);
  _saveTimer = setTimeout(() => {
    const store = useMCCStore.getState();
    const selectedKey = store.selectedKey;
    const activeProjectId = String(store.activeProjectId || '');
    if (!activeProjectId) return;
    fetch(`${API_BASE}/mcc/state`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: activeProjectId,
        window_session_id: String(store.windowSessionId || ''),
        level: state.level,
        roadmap_node_id: state.roadmapNodeId,
        task_id: state.taskId,
        selected_key: selectedKey || undefined,
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
  selectedKey: INITIAL_SELECTED_KEY,
  favoriteKeys: INITIAL_FAVORITE_KEYS,
  statusFilter: 'all',
  taskFilters: INITIAL_TASK_FILTERS,
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
  activeProjectId: '',
  windowSessionId: INITIAL_WINDOW_SESSION_ID,
  projectTabs: [],
  projectTabsLoading: false,
  projectTabsUpdatedAt: '',
  projectTabsHiddenCount: 0,
  showAllProjectsTasks: false,

  // MARKER_155.4: Camera position initial state
  cameraPosition: null,
  workflowSourceMode: 'design',
  // MARKER_162.MYCO.MODE_TOGGLE.V1: persisted helper guide mode.
  helperMode: loadMycoHelperMode(),
  focusedNodeId: null,
  focusRestorePolicy: loadFocusRestorePolicy(),
  focusRestoreSource: null,
  layoutPins: loadLayoutPins(),

  // ── Fetch tasks + agents + heartbeat ──
  fetchTasks: async () => {
    set({ tasksLoading: true });
    try {
      const activeProjectId = String(get().activeProjectId || '');
      // MARKER_189.6A: showAllProjectsTasks bypasses project filter
      const taskQs = (activeProjectId && !get().showAllProjectsTasks) ? `?project_id=${encodeURIComponent(activeProjectId)}` : '';
      const [tasksRes, agentsRes, hbRes] = await Promise.all([
        fetch(`${API_DEBUG}/task-board${taskQs}`).catch(() => null),
        fetch(`${API_DEBUG}/task-board/active-agents${taskQs}`).catch(() => null),
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
  addTask: async (title, preset, phaseType, tags, selectedKey, options) => {
    try {
      const activeProjectId = String(get().activeProjectId || '');
      const roadmapNodeId = String(get().navRoadmapNodeId || '');
      const nodeId = String(options?.primary_node_id || roadmapNodeId || activeProjectId || '').trim();
      const nodePath = String(options?.module || '').trim();
      const res = await fetch(`${API_BASE}/mcc/tasks/create-attached`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          preset,
          phase_type: phaseType,
          tags,
          node_id: nodeId,
          node_label: title,
          node_path: nodePath,
          roadmap_node_id: roadmapNodeId,
          project_id: activeProjectId,
          project_lane: roadmapNodeId || activeProjectId || nodePath || nodeId,
          affected_node_ids: options?.affected_nodes,
        }),
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

  addAttachedTask: async (options) => {
    try {
      const activeProjectId = String(get().activeProjectId || '');
      const roadmapNodeId = String(get().navRoadmapNodeId || '');
      const res = await fetch(`${API_BASE}/mcc/tasks/create-attached`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: activeProjectId,
          roadmap_node_id: roadmapNodeId || options.roadmap_node_id,
          project_lane: options.project_lane || roadmapNodeId || activeProjectId,
          ...options,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        get().fetchTasks();
        return data.task_id || data.task?.id || null;
      }
    } catch (err) {
      console.error('[MCC] Add attached task failed:', err);
    }
    return null;
  },

  attachTaskToNode: async (taskId, options) => {
    try {
      const activeProjectId = String(get().activeProjectId || '');
      const roadmapNodeId = String(get().navRoadmapNodeId || '');
      const res = await fetch(`${API_BASE}/mcc/tasks/${encodeURIComponent(taskId)}/attach-node`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: activeProjectId,
          roadmap_node_id: roadmapNodeId || options.roadmap_node_id,
          project_lane: options.project_lane || roadmapNodeId || activeProjectId,
          ...options,
        }),
      });
      if (res.ok) {
        await get().fetchTasks();
        return true;
      }
    } catch (err) {
      console.error('[MCC] Attach task to node failed:', err);
    }
    return false;
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
  setSelectedKey: (key) => {
    saveSelectedKey(key);
    if (key) {
      useStore.getState().setSelectedKey(key);
    } else {
      useStore.getState().clearSelectedKey();
    }
    set({ selectedKey: key });
  },
  toggleFavoriteKey: (key) => {
    const current = get().favoriteKeys;
    const next = current.includes(key)
      ? current.filter((item) => item !== key)
      : [...current, key];
    saveFavoriteKeys(next);
    useStore.getState().setFavoriteKeys(next);
    set({ favoriteKeys: next });
  },

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
  setTaskFilter: (key, value) => {
    const next = { ...get().taskFilters, [key]: value };
    saveTaskFilters(next);
    set({ taskFilters: next });
  },

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
              ...data,
            } : data,
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
      metadata: event.metadata,  // MARKER_174.B: Preserve structured metadata
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
  initMCC: async (projectIdOverride?: string) => {
    // MARKER_161.7.MULTIPROJECT.UI.INIT_ROUTE.V1:
    // Future init will hydrate tab list + active project context before DAG fetch.
    try {
      const projectId = String(projectIdOverride || '').trim();
      const initUrl = projectId
        ? `${API_BASE}/mcc/init?project_id=${encodeURIComponent(projectId)}&window_session_id=${encodeURIComponent(get().windowSessionId)}`
        : `${API_BASE}/mcc/init?window_session_id=${encodeURIComponent(get().windowSessionId)}`;
      const res = await fetch(initUrl);
      if (!res.ok) {
        // No backend → first_run
        set({
          hasProject: false,
          projectConfig: null,
          activeProjectId: '',
          projectTabs: [],
          projectTabsUpdatedAt: '',
          projectTabsHiddenCount: 0,
          navLevel: 'first_run',
          navHistory: [],
        });
        return;
      }
      const data = await res.json();
      const tabs = Array.isArray(data.projects) ? data.projects : [];
      const activeProjectId = String(data.active_project_id || projectId || '');
      const windowSessionId = String(data.window_session_id || get().windowSessionId || INITIAL_WINDOW_SESSION_ID);

      if (data.has_project && data.session_state) {
        const ss = data.session_state || {};
        const savedSelectedKey = (
          ss.selected_key
          && typeof ss.selected_key.provider === 'string'
          && typeof ss.selected_key.key_masked === 'string'
        ) ? { provider: ss.selected_key.provider, key_masked: ss.selected_key.key_masked } : null;
        saveSelectedKey(savedSelectedKey);
        if (savedSelectedKey) {
          useStore.getState().setSelectedKey(savedSelectedKey);
        } else {
          useStore.getState().clearSelectedKey();
        }
        // MARKER_155A.P0.FLOW_GATE:
        // Do not restore deep drill levels on startup. Users should enter from roadmap
        // after project init to keep context predictable.
        set({
          hasProject: true,
          projectConfig: data.project_config,
          activeProjectId: activeProjectId || String(data?.project_config?.project_id || ''),
          windowSessionId,
          projectTabs: tabs,
          projectTabsUpdatedAt: String(data.updated_at || ''),
          projectTabsHiddenCount: Number(data.hidden_count || 0),
          selectedKey: savedSelectedKey,
          navLevel: 'roadmap',
          navRoadmapNodeId: '',
          navTaskId: '',
          navHistory: [],
        });
      } else {
        // MARKER_154.1B: No project → first_run level
        set({
          hasProject: false,
          projectConfig: null,
          activeProjectId: activeProjectId,
          windowSessionId,
          projectTabs: tabs,
          projectTabsUpdatedAt: String(data.updated_at || ''),
          projectTabsHiddenCount: Number(data.hidden_count || 0),
          navLevel: 'first_run',
          navHistory: [],
        });
      }
    } catch (err) {
      console.error('[MCC] Init failed:', err);
      set({
        hasProject: false,
        projectConfig: null,
        activeProjectId: '',
        windowSessionId: get().windowSessionId || INITIAL_WINDOW_SESSION_ID,
        projectTabs: [],
        projectTabsUpdatedAt: '',
        projectTabsHiddenCount: 0,
        navLevel: 'first_run',
        navHistory: [],
      });
    }
  },

  refreshProjectTabs: async () => {
    set({ projectTabsLoading: true });
    try {
      const res = await fetch(`${API_BASE}/mcc/projects/list`);
      if (!res.ok) return;
      const data = await res.json();
      const tabs = Array.isArray(data?.projects) ? data.projects : [];
      const active = String(data?.active_project_id || '');
      const current = String(get().activeProjectId || '');
      const hasCurrent = !!current && tabs.some((tab: MCCProjectTab) => String(tab?.project_id || '') === current);
      set({
        projectTabs: tabs,
        projectTabsUpdatedAt: String(data?.updated_at || ''),
        projectTabsHiddenCount: Number(data?.hidden_count || 0),
        activeProjectId: hasCurrent ? current : (active || current),
      });
    } catch (err) {
      console.error('[MCC] refreshProjectTabs failed:', err);
    } finally {
      set({ projectTabsLoading: false });
    }
  },

  activateProjectTab: async (projectId) => {
    const pid = String(projectId || '').trim();
    if (!pid) return false;
    try {
      const res = await fetch(`${API_BASE}/mcc/projects/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: pid }),
      });
      if (!res.ok) return false;
      set({ activeProjectId: pid });
      await get().initMCC(pid);
      get().announceProjectRegistryChanged(pid, 'activate');
      return true;
    } catch (err) {
      console.error('[MCC] activateProjectTab failed:', err);
      return false;
    }
  },

  announceProjectRegistryChanged: (projectId, reason = 'refresh') => {
    const store = get();
    broadcastProjectRegistrySync(
      String(projectId || store.activeProjectId || ''),
      String(store.windowSessionId || ''),
      String(reason || 'refresh'),
    );
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
  setWorkflowSourceMode: (mode) => set({ workflowSourceMode: mode }),
  setHelperMode: (mode) => {
    saveMycoHelperMode(mode);
    set({ helperMode: mode });
  },
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
  persistSessionState: () => {
    const s = get();
    _persistState({
      level: s.navLevel,
      roadmapNodeId: s.navRoadmapNodeId,
      taskId: s.navTaskId,
      history: s.navHistory,
    });
  },
}));
