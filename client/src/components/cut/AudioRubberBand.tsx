/**
 * MARKER_B30: Audio Rubber Band — volume automation overlay for timeline clips.
 *
 * FCP7 Reference: Ch.52-55 "Audio Editing in the Timeline"
 * Renders a draggable volume line + keyframe points on audio clips.
 *
 * Features:
 *   - Horizontal line at clip volume level (0% bottom → 150% top)
 *   - Keyframe dots with interpolated path between them
 *   - Drag line up/down = change clip volume
 *   - Callbacks for keyframe add/drag (wiring by Alpha in TimelineTrackView)
 *
 * Color: monochrome #999 line per feedback_monochrome_ui rule.
 * Pending design review task for FCP7 color fidelity + Itten harmony.
 *
 * @phase B30
 * @task tb_1774167622_25
 */
import { useRef, useCallback, useMemo, type CSSProperties } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type RubberBandKeyframe = {
  /** Time relative to clip start, in seconds */
  time_sec: number;
  /** Volume value: 0.0 = silence, 1.0 = unity, 1.5 = +3.5dB */
  value: number;
};

export interface AudioRubberBandProps {
  /** Clip width in pixels */
  width: number;
  /** Clip height in pixels */
  height: number;
  /** Clip duration in seconds */
  duration_sec: number;
  /** Base clip volume (0.0 - 1.5), used when no keyframes */
  volume: number;
  /** Volume keyframes (sorted by time_sec) */
  keyframes?: RubberBandKeyframe[];
  /** Called when user drags the volume line (no keyframes mode) */
  onVolumeChange?: (newVolume: number) => void;
  /** Called when user Option+clicks to add a keyframe */
  onKeyframeAdd?: (time_sec: number, value: number) => void;
  /** Called when user drags a keyframe dot */
  onKeyframeDrag?: (index: number, time_sec: number, value: number) => void;
  /** Line color — monochrome default, overridable after design review */
  lineColor?: string;
  /** Keyframe dot color */
  dotColor?: string;
  /** Whether the clip is selected (brighter line) */
  selected?: boolean;
  /** Whether rubber band editing is enabled */
  enabled?: boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Maximum volume for rubber band (1.5 = +3.5dB) */
const MAX_VOLUME = 1.5;
/** Keyframe dot radius */
const DOT_RADIUS = 3;
/** Hit area for line drag (px from line center) */
const LINE_HIT_AREA = 6;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Convert volume (0-1.5) to Y position (bottom=0, top=max_vol) */
function volumeToY(vol: number, height: number): number {
  const clamped = Math.max(0, Math.min(MAX_VOLUME, vol));
  // 0 = bottom, MAX_VOLUME = top (with 2px padding)
  const pad = 2;
  return height - pad - (clamped / MAX_VOLUME) * (height - 2 * pad);
}

/** Convert Y position to volume */
function yToVolume(y: number, height: number): number {
  const pad = 2;
  const vol = ((height - pad - y) / (height - 2 * pad)) * MAX_VOLUME;
  return Math.max(0, Math.min(MAX_VOLUME, Math.round(vol * 100) / 100));
}

/** Convert time to X position */
function timeToX(time_sec: number, duration_sec: number, width: number): number {
  if (duration_sec <= 0) return 0;
  return (time_sec / duration_sec) * width;
}

/** Convert X position to time */
function xToTime(x: number, duration_sec: number, width: number): number {
  if (width <= 0) return 0;
  return Math.max(0, Math.min(duration_sec, (x / width) * duration_sec));
}

/** Interpolate volume at a given time from sorted keyframes */
function interpolateVolume(
  time_sec: number,
  keyframes: RubberBandKeyframe[],
  defaultVolume: number,
): number {
  if (!keyframes.length) return defaultVolume;
  if (time_sec <= keyframes[0].time_sec) return keyframes[0].value;
  if (time_sec >= keyframes[keyframes.length - 1].time_sec) return keyframes[keyframes.length - 1].value;

  for (let i = 0; i < keyframes.length - 1; i++) {
    const a = keyframes[i];
    const b = keyframes[i + 1];
    if (time_sec >= a.time_sec && time_sec <= b.time_sec) {
      const t = (time_sec - a.time_sec) / (b.time_sec - a.time_sec);
      return a.value + t * (b.value - a.value);
    }
  }
  return defaultVolume;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AudioRubberBand({
  width,
  height,
  duration_sec,
  volume,
  keyframes = [],
  onVolumeChange,
  onKeyframeAdd,
  onKeyframeDrag,
  lineColor = '#999',
  dotColor = '#ccc',
  selected = false,
  enabled = true,
}: AudioRubberBandProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const dragStateRef = useRef<{
    type: 'line' | 'keyframe';
    startY: number;
    startVolume: number;
    kfIndex: number;
  } | null>(null);

  // Build SVG path for the volume line
  const { pathD, dots } = useMemo(() => {
    if (width <= 0 || height <= 0) return { pathD: '', dots: [] };

    const sortedKf = [...keyframes].sort((a, b) => a.time_sec - b.time_sec);

    if (sortedKf.length === 0) {
      // Flat line at clip volume
      const y = volumeToY(volume, height);
      return {
        pathD: `M 0 ${y} L ${width} ${y}`,
        dots: [] as { x: number; y: number; index: number }[],
      };
    }

    // Build path through keyframes
    const points: { x: number; y: number }[] = [];

    // Extend to left edge
    const firstKf = sortedKf[0];
    if (firstKf.time_sec > 0) {
      points.push({ x: 0, y: volumeToY(firstKf.value, height) });
    }

    // Keyframe points
    for (const kf of sortedKf) {
      points.push({
        x: timeToX(kf.time_sec, duration_sec, width),
        y: volumeToY(kf.value, height),
      });
    }

    // Extend to right edge
    const lastKf = sortedKf[sortedKf.length - 1];
    if (lastKf.time_sec < duration_sec) {
      points.push({ x: width, y: volumeToY(lastKf.value, height) });
    }

    const pathParts = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`);

    const kfDots = sortedKf.map((kf, i) => ({
      x: timeToX(kf.time_sec, duration_sec, width),
      y: volumeToY(kf.value, height),
      index: i,
    }));

    return { pathD: pathParts.join(' '), dots: kfDots };
  }, [width, height, duration_sec, volume, keyframes]);

  // --- Drag handlers ---

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!enabled || !containerRef.current) return;
      e.stopPropagation();
      e.preventDefault();

      const rect = containerRef.current.getBoundingClientRect();
      const localY = e.clientY - rect.top;
      const localX = e.clientX - rect.left;

      // Check if clicking a keyframe dot
      const sortedKf = [...keyframes].sort((a, b) => a.time_sec - b.time_sec);
      for (let i = 0; i < sortedKf.length; i++) {
        const dx = timeToX(sortedKf[i].time_sec, duration_sec, width) - localX;
        const dy = volumeToY(sortedKf[i].value, height) - localY;
        if (Math.sqrt(dx * dx + dy * dy) <= DOT_RADIUS + 3) {
          dragStateRef.current = {
            type: 'keyframe',
            startY: e.clientY,
            startVolume: sortedKf[i].value,
            kfIndex: i,
          };
          return;
        }
      }

      // Option+click = add keyframe
      if (e.altKey && onKeyframeAdd) {
        const time = xToTime(localX, duration_sec, width);
        const vol = keyframes.length > 0
          ? interpolateVolume(time, sortedKf, volume)
          : volume;
        onKeyframeAdd(time, vol);
        return;
      }

      // Drag the line (no keyframes mode or general drag)
      if (keyframes.length === 0 && onVolumeChange) {
        const lineY = volumeToY(volume, height);
        if (Math.abs(localY - lineY) <= LINE_HIT_AREA) {
          dragStateRef.current = {
            type: 'line',
            startY: e.clientY,
            startVolume: volume,
            kfIndex: -1,
          };
        }
      }
    },
    [enabled, keyframes, duration_sec, width, height, volume, onKeyframeAdd, onVolumeChange],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragStateRef.current || !containerRef.current) return;
      e.stopPropagation();

      const deltaY = e.clientY - dragStateRef.current.startY;
      // Moving mouse up = volume increase (negative deltaY)
      const volDelta = -(deltaY / (height - 4)) * MAX_VOLUME;
      const newVol = Math.max(0, Math.min(MAX_VOLUME, dragStateRef.current.startVolume + volDelta));

      if (dragStateRef.current.type === 'line' && onVolumeChange) {
        onVolumeChange(Math.round(newVol * 100) / 100);
      } else if (dragStateRef.current.type === 'keyframe' && onKeyframeDrag) {
        const rect = containerRef.current.getBoundingClientRect();
        const localX = e.clientX - rect.left;
        const time = xToTime(localX, duration_sec, width);
        onKeyframeDrag(dragStateRef.current.kfIndex, time, Math.round(newVol * 100) / 100);
      }
    },
    [height, duration_sec, width, onVolumeChange, onKeyframeDrag],
  );

  const handleMouseUp = useCallback(() => {
    dragStateRef.current = null;
  }, []);

  if (width <= 4 || height <= 4 || duration_sec <= 0) return null;

  const effectiveColor = selected ? '#bbb' : lineColor;
  const effectiveDotColor = selected ? '#ddd' : dotColor;

  // Volume label (dB)
  const volDb = volume <= 0 ? '-inf' : `${(20 * Math.log10(volume)).toFixed(1)}dB`;

  const containerStyle: CSSProperties = {
    position: 'absolute',
    inset: 0,
    pointerEvents: enabled ? 'auto' : 'none',
    cursor: enabled ? 'ns-resize' : 'default',
    zIndex: 5,
  };

  return (
    <div
      ref={containerRef}
      style={containerStyle}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      data-testid="audio-rubber-band"
    >
      <svg
        width={width}
        height={height}
        style={{ position: 'absolute', top: 0, left: 0, overflow: 'visible' }}
      >
        {/* Unity line (0dB reference) — subtle dashed */}
        <line
          x1={0}
          y1={volumeToY(1.0, height)}
          x2={width}
          y2={volumeToY(1.0, height)}
          stroke="#444"
          strokeWidth={0.5}
          strokeDasharray="4 4"
        />
        {/* Volume line / keyframe path */}
        {pathD && (
          <path
            d={pathD}
            fill="none"
            stroke={effectiveColor}
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
        {/* Keyframe dots */}
        {dots.map((dot) => (
          <circle
            key={dot.index}
            cx={dot.x}
            cy={dot.y}
            r={DOT_RADIUS}
            fill={effectiveDotColor}
            stroke="#000"
            strokeWidth={0.5}
            style={{ cursor: 'grab' }}
          />
        ))}
      </svg>
      {/* Volume label — top right, only when selected */}
      {selected && (
        <span
          style={{
            position: 'absolute',
            top: 2,
            right: 4,
            fontSize: 8,
            color: '#777',
            pointerEvents: 'none',
            fontFamily: 'system-ui',
          }}
        >
          {volDb}
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Exports for testing
// ---------------------------------------------------------------------------

export { volumeToY, yToVolume, timeToX, xToTime, interpolateVolume, MAX_VOLUME };
