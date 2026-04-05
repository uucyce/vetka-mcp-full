/**
 * MARKER_GAMMA-RULER: Standalone TimelineRuler — FCP7-style time ruler.
 *
 * Drop-in replacement for the inline TimeRuler function inside TimelineTrackView.
 * Alpha imports this and replaces the internal version.
 *
 * Improvements over internal TimeRuler:
 * 1. SMPTE timecode format (HH:MM:SS:FF) at high zoom, MM:SS at low zoom
 * 2. Zoom-adaptive subdivisions (10s→5s→1s→frames as zoom increases)
 * 3. Frame-level ticks at high zoom (zoom > 200)
 * 4. Sub-second marks (0.5s, 0.25s) at medium zoom
 * 5. Monochrome palette (no color)
 *
 * Props match the internal TimeRuler interface for easy replacement.
 */
import { type MouseEvent, type RefObject, type CSSProperties, useCallback, memo } from 'react';

const RULER_HEIGHT = 28;

const RULER_STYLE: CSSProperties = {
  height: RULER_HEIGHT,
  background: '#111',
  borderBottom: '1px solid #333',
  position: 'relative',
  overflow: 'hidden',
  flexShrink: 0,
  cursor: 'pointer',
  userSelect: 'none',
};

// ─── Timecode formatting ───

function formatFrames(seconds: number, fps: number): string {
  return String(Math.round(seconds * fps));
}

function formatSeconds(seconds: number): string {
  return seconds % 1 === 0 ? `${seconds}s` : `${seconds.toFixed(1)}s`;
}

function formatSMPTE(seconds: number, fps: number): string {
  const totalFrames = Math.round(seconds * fps);
  const f = totalFrames % Math.round(fps);
  const totalSec = Math.floor(totalFrames / Math.round(fps));
  const s = totalSec % 60;
  const m = Math.floor(totalSec / 60) % 60;
  const h = Math.floor(totalSec / 3600);
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
  }
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
}

function formatMMSS(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

// ─── Zoom-adaptive tick intervals ───

interface TickLevel {
  interval: number;   // seconds between ticks
  height: number;     // tick height in px
  label: boolean;     // show timecode label
  color: string;      // tick color
}

function getTickLevels(zoom: number, fps: number): TickLevel[] {
  // zoom = pixels per second
  // At low zoom (< 20 px/s) → only 10s and 5s marks
  // At medium zoom (20-80) → 1s marks appear
  // At high zoom (80-200) → sub-second marks
  // At very high zoom (> 200) → frame-level ticks

  const levels: TickLevel[] = [];

  // Major ticks: always visible
  if (zoom < 10) {
    levels.push({ interval: 30, height: 14, label: true, color: '#bbb' });
    levels.push({ interval: 10, height: 10, label: false, color: '#555' });
  } else if (zoom < 20) {
    levels.push({ interval: 10, height: 14, label: true, color: '#bbb' });
    levels.push({ interval: 5, height: 10, label: false, color: '#555' });
  } else if (zoom < 40) {
    levels.push({ interval: 10, height: 14, label: true, color: '#bbb' });
    levels.push({ interval: 5, height: 10, label: true, color: '#888' });
    levels.push({ interval: 1, height: 6, label: false, color: '#444' });
  } else if (zoom < 80) {
    levels.push({ interval: 10, height: 14, label: true, color: '#bbb' });
    levels.push({ interval: 5, height: 12, label: true, color: '#999' });
    levels.push({ interval: 1, height: 8, label: true, color: '#777' });
  } else if (zoom < 200) {
    levels.push({ interval: 10, height: 14, label: true, color: '#bbb' });
    levels.push({ interval: 1, height: 10, label: true, color: '#999' });
    levels.push({ interval: 0.5, height: 6, label: false, color: '#444' });
  } else {
    // Frame-level: show SMPTE
    levels.push({ interval: 1, height: 14, label: true, color: '#bbb' });
    levels.push({ interval: 0.5, height: 10, label: false, color: '#666' });
    if (fps > 0) {
      levels.push({ interval: 1 / fps, height: 4, label: false, color: '#333' });
    }
  }

  return levels;
}

// ─── Tick generation ───

interface Tick {
  x: number;
  height: number;
  color: string;
  label: string;
}

function generateTicks(
  zoom: number,
  scrollLeft: number,
  totalWidth: number,
  fps: number,
  timecodeDisplayMode: 'timecode' | 'frames' | 'seconds' = 'timecode',
): Tick[] {
  const levels = getTickLevels(zoom, fps);
  const ticks: Tick[] = [];
  const usedPositions = new Set<number>(); // prevent overlapping ticks

  const startTime = Math.max(0, scrollLeft / zoom - 1);
  const endTime = (scrollLeft + totalWidth) / zoom + 1;
  const showSMPTE = zoom >= 200;

  for (const level of levels) {
    const startTick = Math.floor(startTime / level.interval) * level.interval;
    for (let time = startTick; time <= endTime; time += level.interval) {
      if (time < 0) continue;
      const x = Math.round(time * zoom - scrollLeft);
      if (x < -30 || x > totalWidth + 30) continue;

      // Skip if a higher-priority tick already at this position
      const posKey = Math.round(x);
      if (usedPositions.has(posKey)) continue;
      usedPositions.add(posKey);

      let label = '';
      if (level.label) {
        if (timecodeDisplayMode === 'frames') {
          label = formatFrames(time, fps);
        } else if (timecodeDisplayMode === 'seconds') {
          label = formatSeconds(time);
        } else {
          // 'timecode' — SMPTE at high zoom, MM:SS at low zoom
          label = showSMPTE ? formatSMPTE(time, fps) : formatMMSS(time);
        }
      }

      ticks.push({ x, height: level.height, color: level.color, label });
    }
  }

  return ticks;
}

// ─── Component ───

export interface TimelineRulerProps {
  zoom: number;
  scrollLeft: number;
  totalWidth: number;
  fps?: number;
  timecodeDisplayMode?: 'timecode' | 'frames' | 'seconds';
  rulerRef?: RefObject<HTMLDivElement | null>;
  onSeek?: (timeSec: number) => void;
  onScrubStart?: (event: MouseEvent<HTMLDivElement>) => void;
  onDoubleClick?: (event: MouseEvent<HTMLDivElement>) => void;
}

function TimelineRulerInner({
  zoom,
  scrollLeft,
  totalWidth,
  fps = 25,
  timecodeDisplayMode = 'timecode',
  rulerRef,
  onSeek,
  onScrubStart,
  onDoubleClick,
}: TimelineRulerProps) {
  const handleClick = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      if (!onSeek) return;
      const rect = event.currentTarget.getBoundingClientRect();
      const x = event.clientX - rect.left + scrollLeft;
      onSeek(x / zoom);
    },
    [onSeek, scrollLeft, zoom],
  );

  const ticks = generateTicks(zoom, scrollLeft, totalWidth, fps, timecodeDisplayMode);

  return (
    <div
      ref={rulerRef}
      data-testid="cut-timeline-ruler"
      style={RULER_STYLE}
      onClick={handleClick}
      onMouseDown={onScrubStart}
      onDoubleClick={onDoubleClick}
    >
      {ticks.map((tick, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: tick.x,
            bottom: 0,
            width: 1,
            height: tick.height,
            background: tick.color,
          }}
        >
          {tick.label ? (
            <span
              data-ruler-label="1"
              style={{
                position: 'absolute',
                bottom: tick.height + 1,
                left: 2,
                fontSize: 10,
                fontFamily: '"JetBrains Mono", "SF Mono", monospace',
                color: tick.color,
                whiteSpace: 'nowrap',
                pointerEvents: 'none',
                zIndex: 1,
              }}
            >
              {tick.label}
            </span>
          ) : null}
        </div>
      ))}
    </div>
  );
}

const TimelineRuler = memo(TimelineRulerInner);
export default TimelineRuler;

/**
 * Re-export RULER_HEIGHT for layout calculations in TimelineTrackView.
 */
export { RULER_HEIGHT };
