/**
 * MARKER_B96: Zustand publish store for the CUT publish pipeline.
 * Manages platform selection, reframe mode, job tracking, and polling.
 *
 * @phase B96
 * @task tb_1774432016_1
 * @depends API_BASE from api.config, zustand
 * @used_by PublishPanel, ExportModal, any component initiating publish flow
 */
import { create } from 'zustand';
import { API_BASE } from '../config/api.config';

// ─── Types ───────────────────────────────────────────────────────────────────

type Platform = 'youtube' | 'instagram' | 'tiktok' | 'x' | 'telegram' | 'file';
type ReframeMode = 'center' | 'none';
type PublishJobStatus = 'pending' | 'encoding' | 'uploading' | 'done' | 'error';

interface PublishJob {
  jobId: string;
  platform: Platform;
  preset: string;
  status: PublishJobStatus;
  progress: number;  // 0–100
  outputPath?: string;
  error?: string;
}

interface PublishState {
  // ── State ──────────────────────────────────────────────────────────────────
  isPublishing: boolean;
  sourcePath: string;
  selectedPlatforms: Platform[];
  reframeMode: ReframeMode;
  jobs: PublishJob[];
  pollIntervalId: number | null;

  // ── Actions ────────────────────────────────────────────────────────────────
  setSourcePath: (path: string) => void;
  togglePlatform: (platform: Platform) => void;
  setReframeMode: (mode: ReframeMode) => void;
  startPublish: () => Promise<void>;
  cancelJob: (jobId: string) => Promise<void>;
  pollStatus: () => Promise<void>;
  startPolling: () => void;
  stopPolling: () => void;
  reset: () => void;
}

// ─── Terminal statuses ────────────────────────────────────────────────────────

const TERMINAL_STATUSES: PublishJobStatus[] = ['done', 'error'];

function allJobsSettled(jobs: PublishJob[]): boolean {
  return jobs.length > 0 && jobs.every((j) => TERMINAL_STATUSES.includes(j.status));
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const usePublishStore = create<PublishState>((set, get) => ({
  // ── Initial state ──────────────────────────────────────────────────────────
  isPublishing: false,
  sourcePath: '',
  selectedPlatforms: [],
  reframeMode: 'center',
  jobs: [],
  pollIntervalId: null,

  // ── Actions ────────────────────────────────────────────────────────────────

  setSourcePath: (path) => set({ sourcePath: path }),

  togglePlatform: (platform) =>
    set((state) => {
      const already = state.selectedPlatforms.includes(platform);
      return {
        selectedPlatforms: already
          ? state.selectedPlatforms.filter((p) => p !== platform)
          : [...state.selectedPlatforms, platform],
      };
    }),

  setReframeMode: (mode) => set({ reframeMode: mode }),

  /**
   * POST /api/cut/publish/prepare
   * Kicks off encoding/upload jobs for every selected platform.
   * Response expected: { jobs: PublishJob[] }
   */
  startPublish: async () => {
    const { sourcePath, selectedPlatforms, reframeMode } = get();
    if (!sourcePath || selectedPlatforms.length === 0) return;

    set({ isPublishing: true, jobs: [] });

    try {
      const res = await fetch(`${API_BASE}/cut/publish/prepare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: sourcePath,
          platforms: selectedPlatforms,
          reframe_mode: reframeMode,
        }),
      });

      if (!res.ok) {
        throw new Error(`Publish prepare failed: ${res.status} ${res.statusText}`);
      }

      const data: { jobs: PublishJob[] } = await res.json();
      set({ jobs: data.jobs });

      // Begin polling immediately after jobs are registered
      get().startPolling();
    } catch (err) {
      console.error('[publishStore] startPublish error:', err);
      set({ isPublishing: false });
    }
  },

  /**
   * POST /api/cut/publish/cancel
   * Requests cancellation of a specific job on the backend.
   */
  cancelJob: async (jobId) => {
    try {
      await fetch(`${API_BASE}/cut/publish/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId }),
      });
      set((state) => ({
        jobs: state.jobs.map((j) =>
          j.jobId === jobId ? { ...j, status: 'error', error: 'Cancelled by user' } : j
        ),
      }));
    } catch (err) {
      console.error('[publishStore] cancelJob error:', err);
    }
  },

  /**
   * GET /api/cut/publish/status?job_ids=id1,id2,...
   * Refreshes progress for all active jobs.
   * Auto-stops polling when all jobs reach a terminal state.
   */
  pollStatus: async () => {
    const { jobs } = get();
    if (jobs.length === 0) return;

    const ids = jobs.map((j) => j.jobId).join(',');
    try {
      const res = await fetch(`${API_BASE}/cut/publish/status?job_ids=${ids}`);
      if (!res.ok) return;

      const data: { jobs: PublishJob[] } = await res.json();

      // Merge updated jobs, preserving any local-only fields
      set((state) => ({
        jobs: state.jobs.map((existing) => {
          const updated = data.jobs.find((j) => j.jobId === existing.jobId);
          return updated ? { ...existing, ...updated } : existing;
        }),
      }));

      // Auto-stop when everything has settled
      const updatedJobs = get().jobs;
      if (allJobsSettled(updatedJobs)) {
        get().stopPolling();
        set({ isPublishing: false });
      }
    } catch (err) {
      console.error('[publishStore] pollStatus error:', err);
    }
  },

  /**
   * Starts a 1 s polling interval.
   * Guards against duplicate intervals.
   */
  startPolling: () => {
    const { pollIntervalId, pollStatus } = get();
    if (pollIntervalId !== null) return; // already running

    const id = window.setInterval(() => {
      pollStatus();
    }, 1000) as unknown as number;

    set({ pollIntervalId: id });
  },

  /**
   * Clears the polling interval.
   */
  stopPolling: () => {
    const { pollIntervalId } = get();
    if (pollIntervalId !== null) {
      clearInterval(pollIntervalId);
      set({ pollIntervalId: null });
    }
  },

  /**
   * Resets the store to its initial state and stops any active polling.
   */
  reset: () => {
    get().stopPolling();
    set({
      isPublishing: false,
      sourcePath: '',
      selectedPlatforms: [],
      reframeMode: 'center',
      jobs: [],
      pollIntervalId: null,
    });
  },
}));
