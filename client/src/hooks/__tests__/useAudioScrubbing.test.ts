/**
 * Unit tests for useAudioScrubbing hook.
 *
 * @phase B5.SCRUB
 * @task tb_1774424882_1
 */
import {
  describe,
  it,
  expect,
  beforeEach,
  afterEach,
  vi,
  type Mock,
} from 'vitest';
import { renderHook, act } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Types shared between the store mock and tests
// ---------------------------------------------------------------------------

interface StoreState {
  currentTime: number;
  isPlaying: boolean;
  audioScrubbing: boolean;
  lanes: Lane[];
  laneVolumes: Record<string, number>;
  mutedLanes: Set<string>;
  soloLanes: Set<string>;
  masterVolume: number;
}

interface Clip {
  clip_id: string;
  start_sec: number;
  duration_sec: number;
  source_path: string;
  source_in?: number;
}

interface Lane {
  lane_id: string;
  clips: Clip[];
}

// ---------------------------------------------------------------------------
// Shared mutable state driven by each test
// ---------------------------------------------------------------------------

const subscriberCallbacks: Array<(state: StoreState) => void> = [];
let mockStoreState: StoreState;

function makeDefaultState(): StoreState {
  return {
    currentTime: 0,
    isPlaying: false,
    audioScrubbing: true,
    lanes: [],
    laneVolumes: {},
    mutedLanes: new Set(),
    soloLanes: new Set(),
    masterVolume: 1.0,
  };
}

// ---------------------------------------------------------------------------
// Module mocks — must be at the top level so vitest can hoist them
// ---------------------------------------------------------------------------

vi.mock('../../config/api.config', () => ({
  API_BASE: '/api',
  IS_TAURI: false,
}));

vi.mock('../../store/useCutEditorStore', () => ({
  useCutEditorStore: {
    getState: () => mockStoreState,
    subscribe: (cb: (state: StoreState) => void) => {
      subscriberCallbacks.push(cb);
      return () => {
        const idx = subscriberCallbacks.indexOf(cb);
        if (idx !== -1) subscriberCallbacks.splice(idx, 1);
      };
    },
  },
}));

// ---------------------------------------------------------------------------
// Import hook — static, after mocks are hoisted
// ---------------------------------------------------------------------------

import {
  useAudioScrubbing,
  __resetScrubbingSingletonsForTests,
} from '../useAudioScrubbing';

// ---------------------------------------------------------------------------
// Web Audio API mock classes
// ---------------------------------------------------------------------------

class MockSourceNode {
  buffer: AudioBuffer | null = null;
  onended: (() => void) | null = null;
  start = vi.fn();
  stop = vi.fn();
  connect = vi.fn();
  disconnect = vi.fn();
}

class MockGainNode {
  gain = { value: 1 };
  connect = vi.fn();
  disconnect = vi.fn();
}

// References updated when the mock context creates new nodes
let latestSource: MockSourceNode | undefined;
let latestGain: MockGainNode | undefined;
let latestCtx: MockAudioContext | undefined;

class MockAudioContext {
  state: string = 'running';
  destination = {};
  sampleRate = 44100;
  resume = vi.fn();

  constructor() {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    latestCtx = this;
  }

  createBufferSource() {
    const node = new MockSourceNode();
    latestSource = node;
    return node;
  }

  createGain() {
    const node = new MockGainNode();
    latestGain = node;
    return node;
  }

  async decodeAudioData(_buf: ArrayBuffer): Promise<AudioBuffer> {
    return {
      duration: 2.0,
      length: 88200,
      numberOfChannels: 2,
      sampleRate: 44100,
      getChannelData: vi.fn(),
      copyFromChannel: vi.fn(),
      copyToChannel: vi.fn(),
    } as unknown as AudioBuffer;
  }
}

// ---------------------------------------------------------------------------
// Controllable performance.now
// ---------------------------------------------------------------------------

let nowMs = 0;

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  // Reset store
  mockStoreState = makeDefaultState();
  subscriberCallbacks.length = 0;
  nowMs = 0;

  // Reset hook module-level singletons
  __resetScrubbingSingletonsForTests();

  // Reset tracking pointers
  latestSource = undefined;
  latestGain = undefined;
  latestCtx = undefined;

  // Install AudioContext mock (constructor form — no arrow fn)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).AudioContext = MockAudioContext;

  // Install healthy fetch mock
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(4096)),
  }) as unknown as typeof fetch;

  // Controllable performance.now
  vi.spyOn(performance, 'now').mockImplementation(() => nowMs);
});

afterEach(() => {
  vi.restoreAllMocks();
  subscriberCallbacks.length = 0;
});

// ---------------------------------------------------------------------------
// Helper: simulate a store update and flush the async audio pipeline
// ---------------------------------------------------------------------------

async function scrub(patch: Partial<StoreState>) {
  mockStoreState = { ...mockStoreState, ...patch };
  await act(async () => {
    for (const cb of [...subscriberCallbacks]) {
      cb(mockStoreState);
    }
    // Multiple flushes: fetch → arrayBuffer → decodeAudioData → source.start
    for (let i = 0; i < 6; i++) {
      await new Promise<void>((r) => setTimeout(r, 0));
    }
  });
}

// ---------------------------------------------------------------------------
// Convenience: a store state that has one 30-second clip on a single lane
// ---------------------------------------------------------------------------

function stateWithClip(base: Partial<StoreState> = {}): StoreState {
  return {
    ...makeDefaultState(),
    lanes: [
      {
        lane_id: 'lane1',
        clips: [
          {
            clip_id: 'c1',
            start_sec: 0,
            duration_sec: 30,
            source_path: '/media/clip.wav',
            source_in: 0,
          },
        ],
      },
    ],
    ...base,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useAudioScrubbing', () => {
  // -------------------------------------------------------------------------
  // 1. Does NOT play audio when isPlaying === true
  // -------------------------------------------------------------------------
  it('does NOT fetch audio when isPlaying is true', async () => {
    mockStoreState = stateWithClip();
    nowMs = 1000;
    renderHook(() => useAudioScrubbing());

    await scrub({ isPlaying: true, currentTime: 5.0 });

    expect(globalThis.fetch as Mock).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------------
  // 2. Does NOT play audio when audioScrubbing === false
  // -------------------------------------------------------------------------
  it('does NOT fetch audio when audioScrubbing is false', async () => {
    mockStoreState = stateWithClip();
    nowMs = 1000;
    renderHook(() => useAudioScrubbing());

    await scrub({ audioScrubbing: false, currentTime: 3.0 });

    expect(globalThis.fetch as Mock).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------------
  // 3. DOES fetch when !isPlaying && audioScrubbing && currentTime changes
  // -------------------------------------------------------------------------
  it('fetches audio when scrubbing enabled and time changes while paused', async () => {
    mockStoreState = stateWithClip();
    nowMs = 1000;
    renderHook(() => useAudioScrubbing());

    await scrub({ currentTime: 5.5 });

    expect(globalThis.fetch as Mock).toHaveBeenCalledOnce();
    const url = (globalThis.fetch as Mock).mock.calls[0][0] as string;
    expect(url).toContain('/cut/audio/clip-segment');
    expect(url).toContain('source_path=');
    expect(url).toContain('start_sec=');
  });

  // -------------------------------------------------------------------------
  // 4. Throttling — rapid changes within 60 ms should be collapsed
  // -------------------------------------------------------------------------
  it('throttles rapid scrub calls within 60 ms', async () => {
    mockStoreState = stateWithClip();
    nowMs = 1000;
    renderHook(() => useAudioScrubbing());

    // First scrub — lastScrub starts at 0, delta = 1000 ms → passes
    await scrub({ currentTime: 1.0 });
    expect(globalThis.fetch as Mock).toHaveBeenCalledTimes(1);

    // Rapid follow-up: delta = 40 ms < 60 ms → blocked
    nowMs = 1040;
    await scrub({ currentTime: 1.5 });
    expect(globalThis.fetch as Mock).toHaveBeenCalledTimes(1);

    // After throttle window: delta = 65 ms > 60 ms → passes
    nowMs = 1065;
    await scrub({ currentTime: 2.0 });
    expect(globalThis.fetch as Mock).toHaveBeenCalledTimes(2);
  });

  // -------------------------------------------------------------------------
  // 5. Multiple instances — only first instance subscribes to the store
  // -------------------------------------------------------------------------
  it('only the first mounted instance subscribes to the store', () => {
    mockStoreState = makeDefaultState();

    renderHook(() => useAudioScrubbing());
    renderHook(() => useAudioScrubbing());
    renderHook(() => useAudioScrubbing());

    // Only one store subscriber should be registered
    expect(subscriberCallbacks.length).toBe(1);
  });

  // -------------------------------------------------------------------------
  // 6. Cleanup on unmount — active audio is stopped
  // -------------------------------------------------------------------------
  it('stops active audio source on unmount', async () => {
    mockStoreState = stateWithClip();
    nowMs = 2000;
    const { unmount } = renderHook(() => useAudioScrubbing());

    // Trigger a scrub snippet so the hook creates an AudioBufferSourceNode
    await scrub({ currentTime: 4.0 });

    // The AudioContext must have been created and a source node started
    expect(latestSource).toBeDefined();
    expect(latestSource!.start).toHaveBeenCalled();

    const capturedSource = latestSource!;

    // Unmount — hook cleanup should stop the active source
    unmount();

    expect(capturedSource.stop).toHaveBeenCalled();
  });

  // -------------------------------------------------------------------------
  // 7. Sub-millisecond jitter is silently ignored
  // -------------------------------------------------------------------------
  it('ignores sub-millisecond currentTime jitter (< 0.001 s change)', async () => {
    mockStoreState = stateWithClip({ currentTime: 5.0 });
    nowMs = 3000;
    renderHook(() => useAudioScrubbing());

    // Change is only 0.0004 s — below the 0.001 s jitter threshold
    await scrub({ currentTime: 5.0004 });

    expect(globalThis.fetch as Mock).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------------
  // 8. Non-ok fetch response — graceful no-op, no AudioContext decoding
  // -------------------------------------------------------------------------
  it('handles non-ok fetch response without throwing', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      arrayBuffer: vi.fn(),
    }) as unknown as typeof fetch;

    mockStoreState = stateWithClip();
    nowMs = 4000;
    renderHook(() => useAudioScrubbing());

    await scrub({ currentTime: 7.0 });

    expect(globalThis.fetch as Mock).toHaveBeenCalledOnce();
    // AudioContext may or may not have been created, but decodeAudioData must not run
    if (latestCtx) {
      // If a context was created, verify decoding was skipped
      expect(latestCtx.decodeAudioData).not.toHaveBeenCalled();
    }
    // No source node should have been created
    expect(latestSource).toBeUndefined();
  });
});
