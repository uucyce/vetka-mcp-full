/**
 * MARKER_B5.2: useAudioPlayback — Web Audio API hook for timeline audio playback.
 *
 * Fetches clip audio from GET /cut/audio/clip-segment, decodes to AudioBuffer,
 * plays via AudioBufferSourceNode synced to video playhead.
 *
 * Audio graph per clip:
 *   AudioBufferSourceNode → GainNode (clip volume) → StereoPannerNode (pan) → destination
 *
 * Features:
 *   - Play/pause/seek synced to store isPlaying + currentTime
 *   - Per-clip volume from laneVolumes (future: keyframe automation)
 *   - Multiple simultaneous clips (layered audio tracks)
 *   - LRU buffer cache to avoid re-fetching
 *   - Lazy AudioContext creation (first user interaction)
 *
 * Alpha wires this into CutEditorLayoutV2 or VideoPreview.
 *
 * @phase B5.2
 * @task tb_1774231583_13
 */
import { useRef, useCallback, useEffect } from 'react';
import { API_BASE } from '../config/api.config';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AudioClipInfo {
  /** Unique clip identifier */
  clip_id: string;
  /** Path to source media file */
  source_path: string;
  /** Start time on timeline (seconds) */
  start_sec: number;
  /** Duration on timeline (seconds) */
  duration_sec: number;
  /** Source in-point (where in the source file this clip starts) */
  source_in: number;
  /** Volume 0.0 - 1.5 */
  volume: number;
  /** Pan -1.0 (L) to +1.0 (R) */
  pan: number;
  /** Whether this clip is muted */
  muted: boolean;
}

interface ActiveSource {
  sourceNode: AudioBufferSourceNode;
  gainNode: GainNode;
  panNode: StereoPannerNode;
  clipId: string;
  startedAt: number; // AudioContext.currentTime when started
  offset: number;    // offset into buffer when started
}

// ---------------------------------------------------------------------------
// Buffer cache (module-level singleton)
// ---------------------------------------------------------------------------

const MAX_CACHE_ENTRIES = 32;
const bufferCache = new Map<string, AudioBuffer>();

function cacheKey(sourcePath: string, sourceIn: number, duration: number): string {
  return `${sourcePath}|${sourceIn.toFixed(2)}|${duration.toFixed(2)}`;
}

function cacheSet(key: string, buffer: AudioBuffer): void {
  if (bufferCache.size >= MAX_CACHE_ENTRIES) {
    // Evict oldest entry
    const firstKey = bufferCache.keys().next().value;
    if (firstKey) bufferCache.delete(firstKey);
  }
  bufferCache.set(key, buffer);
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAudioPlayback() {
  const ctxRef = useRef<AudioContext | null>(null);
  const activeSourcesRef = useRef<ActiveSource[]>([]);
  const pendingFetchesRef = useRef<Set<string>>(new Set());

  // Lazy AudioContext creation
  const getContext = useCallback((): AudioContext => {
    if (!ctxRef.current) {
      ctxRef.current = new AudioContext({ sampleRate: 44100 });
    }
    // Resume if suspended (browser autoplay policy)
    if (ctxRef.current.state === 'suspended') {
      ctxRef.current.resume();
    }
    return ctxRef.current;
  }, []);

  // Fetch + decode audio buffer for a clip
  const loadClipAudio = useCallback(async (
    sourcePath: string,
    sourceIn: number,
    duration: number,
  ): Promise<AudioBuffer | null> => {
    const key = cacheKey(sourcePath, sourceIn, duration);

    // Check cache
    const cached = bufferCache.get(key);
    if (cached) return cached;

    // Deduplicate in-flight fetches
    if (pendingFetchesRef.current.has(key)) return null;
    pendingFetchesRef.current.add(key);

    try {
      const url = `${API_BASE}/cut/audio/clip-segment?source_path=${encodeURIComponent(sourcePath)}&start_sec=${sourceIn}&duration_sec=${Math.min(30, duration)}&sample_rate=44100&channels=2`;
      const response = await fetch(url);
      if (!response.ok) return null;

      const arrayBuffer = await response.arrayBuffer();
      if (arrayBuffer.byteLength < 44) return null;

      const ctx = getContext();
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
      cacheSet(key, audioBuffer);
      return audioBuffer;
    } catch {
      return null;
    } finally {
      pendingFetchesRef.current.delete(key);
    }
  }, [getContext]);

  // Stop all active sources
  const stopAll = useCallback(() => {
    for (const active of activeSourcesRef.current) {
      try {
        active.sourceNode.stop();
        active.sourceNode.disconnect();
        active.gainNode.disconnect();
        active.panNode.disconnect();
      } catch {
        // Already stopped
      }
    }
    activeSourcesRef.current = [];
  }, []);

  // Play a single clip at a given offset within the clip
  const playClip = useCallback(async (clip: AudioClipInfo, offsetInClip: number = 0): Promise<void> => {
    if (clip.muted) return;

    const buffer = await loadClipAudio(clip.source_path, clip.source_in, clip.duration_sec);
    if (!buffer) return;

    const ctx = getContext();

    // Audio graph: source → gain → pan → destination
    const sourceNode = ctx.createBufferSource();
    sourceNode.buffer = buffer;

    const gainNode = ctx.createGain();
    gainNode.gain.value = clip.volume;

    const panNode = ctx.createStereoPanner();
    panNode.pan.value = clip.pan;

    sourceNode.connect(gainNode);
    gainNode.connect(panNode);
    panNode.connect(ctx.destination);

    // Clamp offset to buffer duration
    const safeOffset = Math.max(0, Math.min(offsetInClip, buffer.duration - 0.01));
    const remainingDuration = buffer.duration - safeOffset;

    sourceNode.start(0, safeOffset, remainingDuration);

    const active: ActiveSource = {
      sourceNode,
      gainNode,
      panNode,
      clipId: clip.clip_id,
      startedAt: ctx.currentTime,
      offset: safeOffset,
    };
    activeSourcesRef.current.push(active);

    // Auto-cleanup when source ends
    sourceNode.onended = () => {
      activeSourcesRef.current = activeSourcesRef.current.filter((a) => a !== active);
      try {
        sourceNode.disconnect();
        gainNode.disconnect();
        panNode.disconnect();
      } catch { /* already disconnected */ }
    };
  }, [getContext, loadClipAudio]);

  // Play all clips that overlap with a given timeline time
  const playAt = useCallback(async (clips: AudioClipInfo[], timelineSec: number): Promise<void> => {
    stopAll();

    // Find clips that overlap with current time
    const overlapping = clips.filter((clip) =>
      !clip.muted &&
      timelineSec >= clip.start_sec &&
      timelineSec < clip.start_sec + clip.duration_sec,
    );

    // Play each overlapping clip at the right offset
    await Promise.all(
      overlapping.map((clip) => {
        const offsetInClip = timelineSec - clip.start_sec;
        return playClip(clip, offsetInClip);
      }),
    );
  }, [stopAll, playClip]);

  // Update volume for an active clip (e.g., during fader drag)
  const setClipVolume = useCallback((clipId: string, volume: number) => {
    for (const active of activeSourcesRef.current) {
      if (active.clipId === clipId) {
        active.gainNode.gain.setValueAtTime(volume, getContext().currentTime);
      }
    }
  }, [getContext]);

  // Update pan for an active clip
  const setClipPan = useCallback((clipId: string, pan: number) => {
    for (const active of activeSourcesRef.current) {
      if (active.clipId === clipId) {
        active.panNode.pan.setValueAtTime(pan, getContext().currentTime);
      }
    }
  }, [getContext]);

  // Pre-fetch audio for upcoming clips
  const prefetch = useCallback((clips: AudioClipInfo[]) => {
    for (const clip of clips) {
      loadClipAudio(clip.source_path, clip.source_in, clip.duration_sec);
    }
  }, [loadClipAudio]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopAll();
      if (ctxRef.current) {
        ctxRef.current.close();
        ctxRef.current = null;
      }
    };
  }, [stopAll]);

  return {
    /** Play all clips overlapping timeline position */
    playAt,
    /** Stop all audio playback */
    stopAll,
    /** Update volume for a playing clip */
    setClipVolume,
    /** Update pan for a playing clip */
    setClipPan,
    /** Pre-fetch audio buffers for clips */
    prefetch,
    /** Load a single clip's audio buffer */
    loadClipAudio,
    /** Get or create AudioContext */
    getContext,
    /** Clear buffer cache */
    clearCache: () => bufferCache.clear(),
  };
}

/**
 * Clear the global audio buffer cache (e.g., on project change).
 */
export function clearAudioBufferCache(): void {
  bufferCache.clear();
}
