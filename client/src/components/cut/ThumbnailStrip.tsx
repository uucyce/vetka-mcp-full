/**
 * MARKER_B7.3, B95: ThumbnailStrip — video poster frame + filmstrip.
 *
 * Two fetch strategies:
 *   - Individual frames: N × GET /cut/thumbnail (original, for ≤3 frames)
 *   - Sprite sheet: 1 × GET /cut/thumbnail-strip (B95, for 4+ frames)
 *     Returns single horizontal JPEG, rendered via CSS background-position.
 *
 * Modes:
 *   - poster: single frame (for list/grid view)
 *   - strip: multiple frames side by side (for timeline clips)
 *
 * @phase B7.3, B95
 * @task tb_1774235205_18, tb_1774410419_1
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
  /** Force individual frame fetching even for many frames */
  forceIndividual?: boolean;
  style?: CSSProperties;
}

// ─── Cache ───

const thumbCache = new Map<string, string>(); // url → blob URL
const SPRITE_THRESHOLD = 4; // use sprite sheet for 4+ frames

// ─── Component ───

export default function ThumbnailStrip({
  sourcePath,
  duration_sec,
  width,
  height,
  frameCount = 1,
  posterTime = 1.0,
  bgColor = '#111',
  forceIndividual = false,
  style,
}: ThumbnailStripProps) {
  const count = Math.max(1, Math.min(20, frameCount));
  const useSpriteSheet = count >= SPRITE_THRESHOLD && !forceIndividual;

  if (useSpriteSheet) {
    return (
      <SpriteStrip
        sourcePath={sourcePath}
        duration_sec={duration_sec}
        width={width}
        height={height}
        frameCount={count}
        bgColor={bgColor}
        style={style}
      />
    );
  }

  return (
    <IndividualStrip
      sourcePath={sourcePath}
      duration_sec={duration_sec}
      width={width}
      height={height}
      frameCount={count}
      posterTime={posterTime}
      bgColor={bgColor}
      style={style}
    />
  );
}

// ─── Sprite sheet mode (B95): single JPEG, CSS background-position ───

function SpriteStrip({
  sourcePath,
  duration_sec,
  width,
  height,
  frameCount,
  bgColor,
  style,
}: {
  sourcePath: string;
  duration_sec: number;
  width: number;
  height: number;
  frameCount: number;
  bgColor: string;
  style?: CSSProperties;
}) {
  const [spriteUrl, setSpriteUrl] = useState<string | null>(null);
  const [spriteFrameWidth, setSpriteFrameWidth] = useState(0);
  const [error, setError] = useState(false);

  useEffect(() => {
    const url = `${API_BASE}/cut/thumbnail-strip?source_path=${encodeURIComponent(sourcePath)}&duration=${duration_sec}&count=${frameCount}&frame_height=${height}`;

    const cached = thumbCache.get(url);
    if (cached) {
      setSpriteUrl(cached);
      // Estimate frame width from total / count
      setSpriteFrameWidth(Math.floor(width / frameCount));
      return;
    }

    let cancelled = false;
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const fw = parseInt(r.headers.get('X-Frame-Width') || '0', 10);
        if (fw > 0) setSpriteFrameWidth(fw);
        return r.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        const blobUrl = URL.createObjectURL(blob);
        thumbCache.set(url, blobUrl);
        setSpriteUrl(blobUrl);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });

    return () => { cancelled = true; };
  }, [sourcePath, duration_sec, frameCount, height, width]);

  const displayFrameWidth = Math.floor(width / frameCount);

  if (error || !spriteUrl) {
    return (
      <div
        style={{
          width, height, background: bgColor, overflow: 'hidden', flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center', ...style,
        }}
        data-testid="thumbnail-strip"
      >
        <span style={{ color: '#333', fontSize: 8 }}>{error ? 'x' : ''}</span>
      </div>
    );
  }

  // Each frame slot shows a portion of the sprite via background-position
  const fW = spriteFrameWidth || displayFrameWidth;
  return (
    <div
      style={{
        display: 'flex', width, height, background: bgColor,
        overflow: 'hidden', flexShrink: 0, ...style,
      }}
      data-testid="thumbnail-strip"
    >
      {Array.from({ length: frameCount }, (_, i) => (
        <div
          key={i}
          style={{
            width: displayFrameWidth,
            height,
            flexShrink: 0,
            backgroundImage: `url(${spriteUrl})`,
            backgroundPosition: `-${i * fW}px 0`,
            backgroundSize: `${fW * frameCount}px ${height}px`,
            backgroundRepeat: 'no-repeat',
          }}
        />
      ))}
    </div>
  );
}

// ─── Individual frames mode (original B7.3) ───

function IndividualStrip({
  sourcePath,
  duration_sec,
  width,
  height,
  frameCount,
  posterTime,
  bgColor,
  style,
}: {
  sourcePath: string;
  duration_sec: number;
  width: number;
  height: number;
  frameCount: number;
  posterTime: number;
  bgColor: string;
  style?: CSSProperties;
}) {
  const frames = useMemo(() => {
    const times: number[] = [];
    if (frameCount === 1) {
      times.push(Math.min(posterTime, duration_sec * 0.9));
    } else {
      for (let i = 0; i < frameCount; i++) {
        times.push((i / (frameCount - 1)) * duration_sec * 0.95 + 0.1);
      }
    }
    return times;
  }, [frameCount, posterTime, duration_sec]);

  const frameWidth = Math.floor(width / frames.length);
  const thumbW = Math.min(320, Math.max(64, frameWidth * 2));
  const thumbH = Math.round(thumbW * (height / width));

  return (
    <div
      style={{
        display: 'flex', width, height, background: bgColor,
        overflow: 'hidden', flexShrink: 0, ...style,
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
    width, height, flexShrink: 0, overflow: 'hidden', background: '#0a0a0a',
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
      style={{ ...frameStyle, objectFit: 'cover', display: 'block' }}
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
