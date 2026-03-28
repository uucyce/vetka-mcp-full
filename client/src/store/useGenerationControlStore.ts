/**
 * MARKER_GEN-STORE: Generation Control Store — Zustand state machine.
 *
 * Mirrors FCP7 Deck Control (Ch.50-51) state machine pattern.
 * State transitions:
 *   DISCONNECTED → CONNECTING → IDLE → CONFIGURING → QUEUED → GENERATING
 *   → PREVIEWING → ACCEPTED → IMPORTING → IDLE
 *   GENERATING → CANCELLED → IDLE
 *   PREVIEWING → REJECTED → CONFIGURING (prompt preserved)
 *
 * @phase GENERATION_CONTROL
 * @task tb_1774432024_1
 */
import { create } from 'zustand';

// ─── State machine ───

export type GenMachineState =
  | 'DISCONNECTED'
  | 'CONNECTING'
  | 'IDLE'
  | 'CONFIGURING'
  | 'QUEUED'
  | 'GENERATING'
  | 'PREVIEWING'
  | 'ACCEPTED'
  | 'IMPORTING'
  | 'CANCELLED'
  | 'REJECTED';

// ─── Store shape ───

export interface GenerationControlState {
  // State machine
  machineState: GenMachineState;

  // Provider
  activeProviderId: string | null;

  // Job
  jobId: string | null;
  prompt: string;
  params: Record<string, string | number>;
  progress: number; // 0-1
  progressEta: string | null;
  previewUrl: string | null;

  // Cost tracking
  estimatedCostUsd: number | null;
  actualCostUsd: number | null;
  sessionSpendUsd: number;

  // Reference frame (Cmd+F capture from source monitor)
  referenceFrameDataUrl: string | null;

  // Actions — state machine transitions
  connectProvider: (providerId: string) => void;
  connectionSuccess: () => void;
  connectionFailed: () => void;
  disconnect: () => void;

  startConfiguring: () => void;
  setPrompt: (prompt: string) => void;
  setParam: (key: string, value: string | number) => void;
  setEstimatedCost: (usd: number | null) => void;

  submitJob: () => void;
  jobQueued: (jobId: string) => void;
  jobStarted: () => void;
  setProgress: (progress: number, eta?: string) => void;
  setPreviewUrl: (url: string) => void;
  cancelJob: () => void;

  acceptPreview: () => void;
  importComplete: () => void;
  rejectPreview: () => void;

  // Reference frame
  setReferenceFrame: (dataUrl: string | null) => void;

  // Internal / QA helpers
  forceState: (state: GenMachineState) => void;
  addSpend: (usd: number) => void;
}

// ─── Guard: allowed transitions ───

const ALLOWED: Partial<Record<GenMachineState, GenMachineState[]>> = {
  DISCONNECTED: ['CONNECTING'],
  CONNECTING:   ['IDLE', 'DISCONNECTED'],
  IDLE:         ['CONFIGURING', 'DISCONNECTED'],
  CONFIGURING:  ['QUEUED', 'IDLE'],
  QUEUED:       ['GENERATING', 'CANCELLED'],
  GENERATING:   ['PREVIEWING', 'CANCELLED'],
  PREVIEWING:   ['ACCEPTED', 'REJECTED'],
  ACCEPTED:     ['IMPORTING'],
  IMPORTING:    ['IDLE'],
  CANCELLED:    ['IDLE'],
  REJECTED:     ['CONFIGURING'],
};

function canTransition(from: GenMachineState, to: GenMachineState): boolean {
  return ALLOWED[from]?.includes(to) ?? false;
}

function transition(
  get: () => GenerationControlState,
  set: (partial: Partial<GenerationControlState>) => void,
  to: GenMachineState,
  extra?: Partial<GenerationControlState>,
) {
  const { machineState } = get();
  if (!canTransition(machineState, to)) {
    console.warn(`[GEN-STORE] Invalid transition ${machineState} → ${to}`);
    return;
  }
  set({ machineState: to, ...extra });
}

// ─── Store ───

export const useGenerationControlStore = create<GenerationControlState>((set, get) => ({
  // Initial state
  machineState: 'DISCONNECTED',
  activeProviderId: null,
  jobId: null,
  prompt: '',
  params: {},
  progress: 0,
  progressEta: null,
  previewUrl: null,
  estimatedCostUsd: null,
  actualCostUsd: null,
  sessionSpendUsd: 0,
  referenceFrameDataUrl: null,

  // ─── State machine transitions ───

  connectProvider: (providerId) => {
    transition(get, set, 'CONNECTING', { activeProviderId: providerId });
  },

  connectionSuccess: () => {
    transition(get, set, 'IDLE');
  },

  connectionFailed: () => {
    transition(get, set, 'DISCONNECTED');
  },

  disconnect: () => {
    set({
      machineState: 'DISCONNECTED',
      activeProviderId: null,
      jobId: null,
      progress: 0,
      progressEta: null,
      previewUrl: null,
      estimatedCostUsd: null,
      actualCostUsd: null,
    });
  },

  startConfiguring: () => {
    transition(get, set, 'CONFIGURING');
  },

  setPrompt: (prompt) => {
    set({ prompt });
    const { machineState } = get();
    if (machineState === 'IDLE') {
      transition(get, set, 'CONFIGURING');
    }
  },

  setParam: (key, value) => {
    set((s) => ({ params: { ...s.params, [key]: value } }));
  },

  setEstimatedCost: (usd) => {
    set({ estimatedCostUsd: usd });
  },

  submitJob: () => {
    transition(get, set, 'QUEUED');
  },

  jobQueued: (jobId) => {
    set({ jobId });
  },

  jobStarted: () => {
    transition(get, set, 'GENERATING', { progress: 0, progressEta: null });
  },

  setProgress: (progress, eta) => {
    set({ progress, progressEta: eta ?? null });
  },

  setPreviewUrl: (url) => {
    transition(get, set, 'PREVIEWING', { previewUrl: url, progress: 1 });
  },

  cancelJob: () => {
    const { machineState } = get();
    if (machineState === 'QUEUED' || machineState === 'GENERATING') {
      transition(get, set, 'CANCELLED', { progress: 0, progressEta: null });
    }
  },

  acceptPreview: () => {
    transition(get, set, 'ACCEPTED');
    // Auto-advance to IMPORTING
    setTimeout(() => {
      transition(get, set, 'IMPORTING');
    }, 50);
  },

  importComplete: () => {
    const { actualCostUsd } = get();
    set((s) => ({
      machineState: 'IDLE',
      jobId: null,
      progress: 0,
      previewUrl: null,
      estimatedCostUsd: null,
      actualCostUsd: null,
      sessionSpendUsd: s.sessionSpendUsd + (actualCostUsd ?? 0),
    }));
  },

  rejectPreview: () => {
    transition(get, set, 'REJECTED', { previewUrl: null });
    setTimeout(() => {
      transition(get, set, 'CONFIGURING');
    }, 50);
  },

  // ─── Reference frame ───

  setReferenceFrame: (dataUrl) => {
    set({ referenceFrameDataUrl: dataUrl });
  },

  // ─── Helpers ───

  forceState: (state) => {
    set({ machineState: state });
  },

  addSpend: (usd) => {
    set((s) => ({ sessionSpendUsd: s.sessionSpendUsd + usd, actualCostUsd: usd }));
  },
}));
