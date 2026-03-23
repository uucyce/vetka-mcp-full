/**
 * MARKER_B8.2: Render Indicator — colored bar above timeline ruler.
 *
 * FCP7 Ch.48: Shows render status of timeline segments:
 *   - Green: rendered (effects pre-computed, smooth playback)
 *   - Red: needs render (heavy effects, will stutter on playback)
 *   - Grey: no effects (plays direct from source, no render needed)
 *
 * Monochrome exception: red/green are functional status indicators
 * (like broadcast ILLEGAL/SAFE in scopes).
 *
 * Alpha wires into TimelineTrackView above the time ruler.
 *
 * @phase B8.2
 * @task tb_1774233785_17
 */
import { useMemo, type CSSProperties } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type RenderSegmentStatus = 'rendered' | 'needs_render' | 'no_effects';

export interface RenderSegment {
  /** Start time in seconds */
  start_sec: number;
  /** End time in seconds */
  end_sec: number;
  /** Render status */
  status: RenderSegmentStatus;
}

export interface RenderIndicatorProps {
  /** Timeline segments with render status */
  segments: RenderSegment[];
  /** Total timeline duration (seconds) */
  duration_sec: number;
  /** Visible width in pixels */
  width: number;
  /** Scroll offset in seconds */
  scrollOffset?: number;
  /** Zoom: pixels per second */
  pixelsPerSec?: number;
  /** Bar height in pixels */
  height?: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUS_COLORS: Record<RenderSegmentStatus, string> = {
  rendered: '#2a5a2a',     // dark green
  needs_render: '#5a2a2a', // dark red
  no_effects: '#1a1a1a',   // background grey (invisible)
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function RenderIndicator({
  segments,
  duration_sec,
  width,
  scrollOffset = 0,
  pixelsPerSec = 50,
  height = 3,
}: RenderIndicatorProps) {
  const bars = useMemo(() => {
    if (!segments.length || duration_sec <= 0 || width <= 0) return [];

    return segments
      .filter((seg) => seg.status !== 'no_effects') // skip invisible segments
      .map((seg, i) => {
        const x = (seg.start_sec - scrollOffset) * pixelsPerSec;
        const w = (seg.end_sec - seg.start_sec) * pixelsPerSec;

        // Skip if completely off-screen
        if (x + w < 0 || x > width) return null;

        return {
          key: i,
          x: Math.max(0, x),
          width: Math.min(w, width - Math.max(0, x)),
          color: STATUS_COLORS[seg.status],
        };
      })
      .filter(Boolean);
  }, [segments, duration_sec, width, scrollOffset, pixelsPerSec]);

  const containerStyle: CSSProperties = {
    position: 'relative',
    width,
    height,
    background: '#0a0a0a',
    flexShrink: 0,
    overflow: 'hidden',
  };

  return (
    <div style={containerStyle} data-testid="render-indicator">
      {bars.map((bar) =>
        bar ? (
          <div
            key={bar.key}
            style={{
              position: 'absolute',
              left: bar.x,
              top: 0,
              width: bar.width,
              height,
              background: bar.color,
            }}
          />
        ) : null,
      )}
    </div>
  );
}
