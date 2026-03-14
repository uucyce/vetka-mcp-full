import { create } from 'zustand';

export type DevPanelTab = 'mcc' | 'stats' | 'architect' | 'balance';
export type TaskSortKey = 'priority' | 'created_at' | 'duration_s' | 'success_rate';
export type StatsPanelMode = 'ops' | 'diagnostics';

interface TaskFilterState {
  source: string;
  statuses: string[];
  preset: string;
  query: string;
  dateFrom: string;
  dateTo: string;
  sortBy: TaskSortKey;
  showCompleted: boolean;
}

interface DevPanelStoreState {
  activeTab: DevPanelTab;
  statsMode: StatsPanelMode;
  taskFilters: TaskFilterState;
  setActiveTab: (tab: DevPanelTab) => void;
  setStatsMode: (mode: StatsPanelMode) => void;
  setTaskFilters: (updates: Partial<TaskFilterState>) => void;
  resetTaskFilters: () => void;
}

const FILTERS_STORAGE_KEY = 'vetka_mcc_task_filters';
const STATS_MODE_STORAGE_KEY = 'vetka_mcc_stats_mode';

const DEFAULT_TASK_FILTERS: TaskFilterState = {
  source: 'all',
  statuses: [],
  preset: 'all',
  query: '',
  dateFrom: '',
  dateTo: '',
  sortBy: 'priority',
  showCompleted: true,
};

function loadFilters(): TaskFilterState {
  try {
    const raw = localStorage.getItem(FILTERS_STORAGE_KEY);
    if (!raw) return DEFAULT_TASK_FILTERS;
    const parsed = JSON.parse(raw);
    return { ...DEFAULT_TASK_FILTERS, ...(parsed || {}) };
  } catch {
    return DEFAULT_TASK_FILTERS;
  }
}

function saveFilters(filters: TaskFilterState) {
  try {
    localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(filters));
  } catch {
    // ignore localStorage failures
  }
}

function loadStatsMode(): StatsPanelMode {
  try {
    const raw = localStorage.getItem(STATS_MODE_STORAGE_KEY);
    if (raw === 'diagnostics' || raw === 'ops') return raw;
    return 'ops';
  } catch {
    return 'ops';
  }
}

function saveStatsMode(mode: StatsPanelMode) {
  try {
    localStorage.setItem(STATS_MODE_STORAGE_KEY, mode);
  } catch {
    // ignore localStorage failures
  }
}

export const useDevPanelStore = create<DevPanelStoreState>((set, get) => ({
  activeTab: 'mcc',
  statsMode: loadStatsMode(),
  taskFilters: loadFilters(),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setStatsMode: (mode) => {
    saveStatsMode(mode);
    set({ statsMode: mode });
  },
  setTaskFilters: (updates) => {
    const next = { ...get().taskFilters, ...updates };
    saveFilters(next);
    set({ taskFilters: next });
  },
  resetTaskFilters: () => {
    saveFilters(DEFAULT_TASK_FILTERS);
    set({ taskFilters: DEFAULT_TASK_FILTERS });
  },
}));
