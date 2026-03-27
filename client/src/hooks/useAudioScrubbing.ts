/**
 * MARKER_B5.SCRUB: Audio scrubbing — play short audio snippets during timeline drag/jog.
 *
 * When audioScrubbing is enabled (Shift+S) and the user moves the playhead
 * without playing (ruler drag, JKL jog, arrow keys), this hook plays a brief
 * ~80ms audio snippet at the new position via Web Audio API.
 *
 * Uses the existing GET /cut/audio/clip-segment endpoint (B5.1).
 * Maintains a lightweight LRU cache of decoded AudioBuffers (~2s windows).
 *
 * Design: fully standalone — own AudioContext, own cache, no dependency on
 * useAudioPlayback (which is for continuous multi-track playback).
 *
 * @phase B5.SCRUB
 * @task tb_1774424882_1
 */
import { useEffect, useRef } from 'react';
import { API_BASE } from '../config/api.config';
import { useCutEditorStore } from '../store/useCutEditorStore';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Duration of each scrub audio snippet in seconds. */
const SNIPPET_DURATION_SEC = 0.08;

/** Minimum interval between scrub snippets in ms. */
const THROTTLE_MS = 60;

/** Size of pre-fetched audio window around scrub point (seconds). */
const FETCH_WINDOW_SEC = 2.0;

/** Max cached AudioBuffers for scrub windows. */
const MAX_SCRUB_CACHE = 20;

// ---------------------------------------------------------------------------
// Module-level singletons (shared across all hook instances)
// ---------------------------------------------------------------------------

let scrubCtx: AudioContext | null = null;

function getScrubContext(): AudioContext {
  if (!scrubCtx || scrubCtx.state === 'closed') {
    scrubCtx = new AudioContext({ sampleRate: 44100 });
  }
  if (scrubCtx.state === 'suspended') {
    scrubCtx.resume();
  }
  return scrubCtx;
}

/** LRU cache: key → AudioBuffer for ~2s windows. */
const scrubCache = new Map<string, AudioBuffer>();

function scrubCacheKey(sourcePath: string, windowStart: number): string {
  return `${sourcePath}|${windowStart.toFixed(1)}`;
}

function scrubCacheSet(key: string, buffer: AudioBuffer): void {
  // Evict oldest if over limit
  while (scrubCache.size >= MAX_SCRUB_CACHE) {
    const firstKey = scrubCache.keys().next().value;
    if (!firstKey) break;
    scrubCache.delete(firstKey);
  }
  scrubCache.set(key, buffer);
}

/** Pending fetch dedup. */
const pendingScrubFetches = new Set<string>();

// ---------------------------------------------------------------------------
// Fetch + decode a scrub window
// ---------------------------------------------------------------------------

async function fetchScrubWindow(
  sourcePath: string,
  windowStart: number,
  windowDuration: number,
): Promise<AudioBuffer | null> {
  const key = scrubCacheKey(sourcePath, windowStart);

  const cached = scrubCache.get(key);
  if (cached) return cached;

  if (pendingScrubFetches.has(key)) return null;
  pendingScrubFetches.add(key);

  try {
    const url = `${API_BASE}/cut/audio/clip-segment?source_path=${encodeURIComponent(sourcePath)}&start_sec=${windowStart}&duration_sec=${windowDuration}&sample_rate=44100&channels=2`;
    const resp = await fetch(url);
    if (!resp.ok) return null;

    const arrayBuffer = await resp.arrayBuffer();
    if (arrayBuffer.byteLength < 44) return null; // too small for WAV header

    const ctx = getScrubContext();
    const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
    scrubCacheSet(key, audioBuffer);
    return audioBuffer;
  } catch {
    return null;
  } finally {
    pendingScrubFetches.delete(key);
  }
}

// ---------------------------------------------------------------------------
// Clip info extraction from store lanes
// ---------------------------------------------------------------------------

interface ScrubClipInfo {
  source_path: string;
  /** Start on timeline (seconds). */
  start_sec: number;
  /** Duration on timeline (seconds). */
  duration_sec: number;
  /** Where in the source file this clip starts (seconds). */
  source_in: number;
  /** Effective volume (0–1.5). */
  volume: number;
  /** Whether this clip should be silent. */
  muted: boolean;
}

function getOverlappingClips(timelineSec: number): ScrubClipInfo[] {
  const state = useCutEditorStore.getState();
  const { lanes, laneVolumes, mutedLanes, soloLanes, masterVolume } = state;

  const hasSolo = soloLanes.size > 0;
  const clips: ScrubClipInfo[] = [];

  for (const lane of lanes) {
    // Skip muted lanes; if any lane is soloed, only play soloed lanes
    const isMuted = mutedLanes.has(lane.lane_id) || (hasSolo && !soloLanes.has(lane.lane_id));
    if (isMuted) continue;

    const laneVol = laneVolumes[lane.lane_id] ?? 1.0;

    for (const clip of lane.clips) {
      const clipEnd = clip.start_sec + clip.duration_sec;
      if (timelineSec >= clip.start_sec && timelineSec < clipEnd) {
        clips.push({
          source_path: clip.source_path,
          start_sec: clip.start_sec,
          duration_sec: clip.duration_sec,
          source_in: clip.source_in ?? 0,
          volume: laneVol * masterVolume,
          muted: false,
        });
      }
    }
  }

  return clips;
}

// ---------------------------------------------------------------------------
// Play a single scrub snippet
// ---------------------------------------------------------------------------

let activeScrubSource: AudioBufferSourceNode | null = null;

async function playScrubSnippet(timelineSec: number): Promise<void> {
  // Stop previous snippet
  if (activeScrubSource) {
    try { activeScrubSource.stop(); } catch { /* already stopped */ }
    activeScrubSource = null;
  }

  const clips = getOverlappingClips(timelineSec);
  if (clips.length === 0) return;

  // Play the first (topmost) overlapping clip for scrub preview
  const clip = clips[0];

  // Calculate where in the source file the scrub position falls
  const offsetInClip = timelineSec - clip.start_sec;
  const sourceOffset = clip.source_in + offsetInClip;

  // Determine fetch window: align to FETCH_WINDOW_SEC grid for cache hits
  const windowStart = Math.floor(sourceOffset / FETCH_WINDOW_SEC) * FETCH_WINDOW_SEC;
  const windowDuration = Math.min(FETCH_WINDOW_SEC, 30); // server max = 30s

  const buffer = await fetchScrubWindow(clip.source_path, windowStart, windowDuration);
  if (!buffer) return;

  const ctx = getScrubContext();

  const source = ctx.createBufferSource();
  source.buffer = buffer;

  const gain = ctx.createGain();
  gain.gain.value = clip.volume;

  source.connect(gain);
  gain.connect(ctx.destination);

  // Offset within the fetched window
  const offsetInWindow = sourceOffset - windowStart;
  const safeOffset = Math.max(0, Math.min(offsetInWindow, buffer.duration - 0.01));

  source.start(0, safeOffset, SNIPPET_DURATION_SEC);
  activeScrubSource = source;

  source.onended = () => {
    if (activeScrubSource === source) {
      activeScrubSource = null;
    }
    try { source.disconnect(); gain.disconnect(); } catch { /* ok */ }
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/** Guard: only one active subscription even if multiple VideoPreview instances mount. */
let activeInstances = 0;

/**
 * Enable audio scrubbing for the program monitor.
 * Safe to call from multiple components — only the first instance activates.
 * The hook is fully self-contained — no props needed.
 */
export function useAudioScrubbing(): void {
  const lastScrubRef = useRef(0);

  useEffect(() => {
    activeInstances++;
    // Only first instance subscribes
    if (activeInstances > 1) {
      return () => { activeInstances--; };
    }

    let prevTime = useCutEditorStore.getState().currentTime;

    const unsub = useCutEditorStore.subscribe((state) => {
      const { currentTime, isPlaying, audioScrubbing } = state;

      // Only scrub when not playing and scrubbing is enabled
      if (!audioScrubbing || isPlaying) {
        prevTime = currentTime;
        return;
      }

      // Detect time change (ignore sub-millisecond jitter)
      if (Math.abs(currentTime - prevTime) < 0.001) return;
      prevTime = currentTime;

      // Throttle
      const now = performance.now();
      if (now - lastScrubRef.current < THROTTLE_MS) return;
      lastScrubRef.current = now;

      void playScrubSnippet(currentTime);
    });

    return () => {
      activeInstances--;
      unsub();
      // Stop any active scrub audio on unmount
      if (activeScrubSource) {
        try { activeScrubSource.stop(); } catch { /* ok */ }
        activeScrubSource = null;
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}
