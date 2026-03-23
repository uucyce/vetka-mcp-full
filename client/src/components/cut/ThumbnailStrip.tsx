/**
 * MARKER_B7.3: ThumbnailStrip — video poster frame + filmstrip for Project bin.
 *
 * Fetches poster frame from GET /cut/thumbnail?source_path=...&time_sec=1
 * Optionally renders a filmstrip (multiple evenly-spaced frames across clip duration).
 *
 * Modes:
 *   - poster: single frame (for list/grid view)
 *   - strip: multiple frames side by side (for clip detail/inspector)
 *
 * @phase B7.3
 * @task tb_1774235205_18
 */
import { useState, useEffect, useMemo, type CSSProperties } from 'react';
import { API_BASE } from '../../config/api.config';

// ─── Types ───

interface ThumbnailStripProps {
  /** Path to source media file */
  sourcePath: string;
  /** Total clip duration in seconds */
  duration_sec: number;
  /** Display width in pixels */
  width: number;
  /** Display height in pixels */
  height: number;
  /** Number of frames to show (1 = poster, 5+ = filmstrip) */
  frameCount?: number;
  /** Time offset for poster frame (seconds) */
  posterTime?: number;
  /** Background color */
  bgColor?: string;
  style?: CSSProperties;
}

// ─── Cache ───

const thumbCache = new Map<string, string>(); // url → blob URL

// ─── Component ───

export default function ThumbnailStrip({
  sourcePath,
  duration_sec,
  width,
  height,
  frameCount = 1,
  posterTime = 1.0,
  bgColor = '#111',
  style,
}: ThumbnailStripProps) {
  const frames = useMemo(() => {
    const count = Math.max(1, Math.min(20, frameCount));
    const times: number[] = [];
    if (count === 1) {
      times.push(Math.min(posterTime, duration_sec * 0.9));
    } else {
      for (let i = 0; i < count; i++) {
        times.push((i / (count - 1)) * duration_sec * 0.95 + 0.1);
      }
    }
    return times;
  }, [frameCount, posterTime, duration_sec]);

  const frameWidth = Math.floor(width / frames.length);
  const thumbW = Math.min(320, Math.max(64, frameWidth * 2)); // fetch at 2x for sharpness
  const thumbH = Math.round(thumbW * (height / width));

  return (
    <div
      style={{
        display: 'flex',
        width,
        height,
        background: bgColor,
        overflow: 'hidden',
        flexShrink: 0,
        ...style,
      }}
      data-testid="thumbnail-strip"
    >
      {frames.map((time, i) => (
        <ThumbnailFrame
          key={i}
          sourcePath={sourcePath}
          timeSec={time}
          width={frameWidth}
          height={height}
          fetchWidth={thumbW}
          fetchHeight={thumbH}
        />
      ))}
    </div>
  );
}

// ─── Single frame ───

function ThumbnailFrame({
  sourcePath,
  timeSec,
  width,
  height,
  fetchWidth,
  fetchHeight,
}: {
  sourcePath: string;
  timeSec: number;
  width: number;
  height: number;
  fetchWidth: number;
  fetchHeight: number;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const url = `${API_BASE}/cut/thumbnail?source_path=${encodeURIComponent(sourcePath)}&time_sec=${timeSec.toFixed(2)}&width=${fetchWidth}&height=${fetchHeight}`;

    // Check cache
    const cached = thumbCache.get(url);
    if (cached) {
      setSrc(cached);
      return;
    }

    let cancelled = false;
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        const blobUrl = URL.createObjectURL(blob);
        thumbCache.set(url, blobUrl);
        setSrc(blobUrl);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });

    return () => { cancelled = true; };
  }, [sourcePath, timeSec, fetchWidth, fetchHeight]);

  const frameStyle: CSSProperties = {
    width,
    height,
    flexShrink: 0,
    overflow: 'hidden',
    background: '#0a0a0a',
  };

  if (error || !src) {
    return (
      <div style={{ ...frameStyle, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: '#333', fontSize: 8 }}>{error ? 'x' : ''}</span>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt=""
      style={{
        ...frameStyle,
        objectFit: 'cover',
        display: 'block',
      }}
    />
  );
}

/**
 * Clear thumbnail cache (e.g., on project change).
 */
export function clearThumbnailCache(): void {
  for (const blobUrl of thumbCache.values()) {
    URL.revokeObjectURL(blobUrl);
  }
  thumbCache.clear();
}
