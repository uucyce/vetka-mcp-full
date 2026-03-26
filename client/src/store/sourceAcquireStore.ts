/**
 * MARKER_SOURCE_ACQUIRE: Source Acquire store — 4-tab ingest panel state.
 * Replaces FCP7 Log & Capture (Ch.14-15).
 * Tabs: YouTube fetch, AI local, AI remote, enhanced local import.
 */
import { create } from 'zustand';

// ─── Types ──────────────────────────────────────────────────────────

export type AcquireTab = 'youtube' | 'ai-local' | 'ai-remote' | 'import';

export type AcquireJobStatus =
  | 'idle'
  | 'configuring'
  | 'fetching'
  | 'generating'
  | 'previewing'
  | 'accepted'
  | 'importing_to_dag'
  | 'rejected'
  | 'failed'
  | 'cancelled';

export type RemoteProvider = 'runway' | 'sora' | 'kling';
export type VideoQuality = 'best' | '1080p' | '720p' | '480p' | 'audio-only';

export interface YouTubeSegment {
  id: string;
  inTime: number;
  outTime: number;
  label: string;
}

export interface AcquireJob {
  id: string;
  type: AcquireTab;
  status: AcquireJobStatus;
  label: string;
  progress: number; // 0–1
  outputFilePath: string | null;
  outputPreviewUrl: string | null;
  dagNodeId: string | null;
  error: string | null;
  createdAt: number;
}

// ─── Store interface ────────────────────────────────────────────────

interface SourceAcquireState {
  // Tab routing
  activeTab: AcquireTab;
  setActiveTab: (tab: AcquireTab) => void;

  // YouTube tab state
  youtubeUrl: string;
  setYoutubeUrl: (url: string) => void;
  youtubeQuality: VideoQuality;
  setYoutubeQuality: (q: VideoQuality) => void;
  youtubeSegments: YouTubeSegment[];
  addYoutubeSegment: (seg: YouTubeSegment) => void;
  removeYoutubeSegment: (id: string) => void;
  clearYoutubeSegments: () => void;

  // AI local tab state
  aiLocalPrompt: string;
  setAiLocalPrompt: (p: string) => void;

  // AI remote tab state
  aiRemotePrompt: string;
  setAiRemotePrompt: (p: string) => void;
  aiRemoteProvider: RemoteProvider;
  setAiRemoteProvider: (p: RemoteProvider) => void;

  // Acquire queue (shared across all tabs)
  jobs: AcquireJob[];
  addJob: (job: AcquireJob) => void;
  updateJob: (id: string, patch: Partial<AcquireJob>) => void;
  removeJob: (id: string) => void;
  clearCompletedJobs: () => void;

  // Import tab — drag-and-drop file list
  importFiles: string[];
  setImportFiles: (files: string[]) => void;
  addImportFiles: (files: string[]) => void;
  clearImportFiles: () => void;
}

// ─── Store ──────────────────────────────────────────────────────────

export const useSourceAcquireStore = create<SourceAcquireState>((set) => ({
  // Tab routing
  activeTab: 'import',
  setActiveTab: (tab) => set({ activeTab: tab }),

  // YouTube
  youtubeUrl: '',
  setYoutubeUrl: (url) => set({ youtubeUrl: url }),
  youtubeQuality: 'best',
  setYoutubeQuality: (q) => set({ youtubeQuality: q }),
  youtubeSegments: [],
  addYoutubeSegment: (seg) =>
    set((s) => ({ youtubeSegments: [...s.youtubeSegments, seg] })),
  removeYoutubeSegment: (id) =>
    set((s) => ({ youtubeSegments: s.youtubeSegments.filter((seg) => seg.id !== id) })),
  clearYoutubeSegments: () => set({ youtubeSegments: [] }),

  // AI local
  aiLocalPrompt: '',
  setAiLocalPrompt: (p) => set({ aiLocalPrompt: p }),

  // AI remote
  aiRemotePrompt: '',
  setAiRemotePrompt: (p) => set({ aiRemotePrompt: p }),
  aiRemoteProvider: 'runway',
  setAiRemoteProvider: (p) => set({ aiRemoteProvider: p }),

  // Queue
  jobs: [],
  addJob: (job) => set((s) => ({ jobs: [...s.jobs, job] })),
  updateJob: (id, patch) =>
    set((s) => ({
      jobs: s.jobs.map((j) => (j.id === id ? { ...j, ...patch } : j)),
    })),
  removeJob: (id) => set((s) => ({ jobs: s.jobs.filter((j) => j.id !== id) })),
  clearCompletedJobs: () =>
    set((s) => ({
      jobs: s.jobs.filter((j) => j.status !== 'accepted' && j.status !== 'failed' && j.status !== 'cancelled'),
    })),

  // Import files
  importFiles: [],
  setImportFiles: (files) => set({ importFiles: files }),
  addImportFiles: (files) => set((s) => ({ importFiles: [...s.importFiles, ...files] })),
  clearImportFiles: () => set({ importFiles: [] }),
}));
