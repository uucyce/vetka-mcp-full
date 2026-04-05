/**
 * MARKER_B15: Waveform overlay for timeline clips.
 *
 * Auto-fetches waveform peaks from backend when not available in store.
 * Renders WaveformCanvas inside clip rect. Caches peaks per source_path.
 * Works for both video clips (audio track) and audio-only clips.
 *
 * Usage: <WaveformOverlay sourcePath={clip.source_path} width={px} height={px} color="#4a9eff" />
 */
import { useState, useEffect, useRef, type CSSProperties } from 'react';
import { API_BASE } from '../../config/api.config';
import WaveformCanvas from './WaveformCanvas';

// In-memory cache: source_path → peaks array (shared across all instances)
const peaksCache = new Map<string, number[]>();
const pendingFetches = new Set<string>();

interface WaveformOverlayProps {
  sourcePath: string;
  width: number;
  height: number;
  color?: string;
  /** Pre-loaded peaks from store (skip fetch if available) */
  cachedPeaks?: number[];
  /** Cursor position 0-1 for seek preview */
  cursorRatio?: number | null;
  /** Number of bins to request from backend */
  bins?: number;
  style?: CSSProperties;
}

export default function WaveformOverlay({
  sourcePath,
  width,
  height,
  color = '#888',
  cachedPeaks,
  cursorRatio = null,
  bins = 128,
  style,
}: WaveformOverlayProps) {
  const [peaks, setPeaks] = useState<number[] | null>(
    cachedPeaks ?? peaksCache.get(sourcePath) ?? null
  );
  const [error, setError] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // Sync with cached peaks from store
  useEffect(() => {
    if (cachedPeaks?.length) {
      setPeaks(cachedPeaks);
      peaksCache.set(sourcePath, cachedPeaks);
    }
  }, [cachedPeaks, sourcePath]);

  // Auto-fetch if no peaks available
  useEffect(() => {
    if (peaks?.length || error) return;
    if (peaksCache.has(sourcePath)) {
      setPeaks(peaksCache.get(sourcePath)!);
      return;
    }
    if (pendingFetches.has(sourcePath)) return;

    pendingFetches.add(sourcePath);

    const fetchPeaks = async () => {
      try {
        const url = `${API_BASE}/cut/waveform-peaks?source_path=${encodeURIComponent(sourcePath)}&bins=${bins}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.success && data.peaks?.length) {
          peaksCache.set(sourcePath, data.peaks);
          if (mountedRef.current) {
            setPeaks(data.peaks);
          }
        } else {
          if (mountedRef.current) setError(true);
        }
      } catch {
        if (mountedRef.current) setError(true);
      } finally {
        pendingFetches.delete(sourcePath);
      }
    };

    fetchPeaks();
  }, [sourcePath, peaks, error, bins]);

  if (!peaks?.length || width <= 4 || height <= 4) {
    return null;
  }

  return (
    <WaveformCanvas
      bins={peaks}
      width={width}
      height={height}
      color={color}
      cursorRatio={cursorRatio}
      style={style}
    />
  );
}

/**
 * Clear the peaks cache (e.g., when project changes).
 */
export function clearWaveformCache() {
  peaksCache.clear();
}
