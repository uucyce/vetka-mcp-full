/**
 * MARKER_GAMMA-XFADE: Audio Crossfade Handle — drag-to-apply dissolve on clip edges.
 *
 * Renders a visual crossfade overlay on the right edge of an audio clip when
 * a transition_out is present. Supports:
 *   - Drag left edge to resize crossfade duration
 *   - Right-click to cycle audio curve (equal_power / linear)
 *   - Visual equal-power or linear curve indicator
 *
 * Integration: Alpha imports this into TimelineTrackView clip render loop,
 * positioned inside the clip div as a sibling to the MARKER_TRANSITION overlay.
 *
 * @phase W9
 */
import { useCallback, useRef, useState, type CSSProperties } from 'react';

export type AudioCurve = 'equal_power' | 'linear';

export interface AudioCrossfadeProps {
  /** Crossfade duration in seconds */
  durationSec: number;
  /** Pixels per second (zoom level) */
  zoom: number;
  /** Clip total width in pixels */
  clipWidthPx: number;
  /** Track height in pixels */
  trackHeightPx: number;
  /** Audio curve type */
  curve: AudioCurve;
  /** Alignment relative to edit point */
  alignment: 'center' | 'start' | 'end';
  /** Called when user drags to resize duration */
  onDurationChange: (newDurationSec: number) => void;
  /** Called when user cycles curve type */
  onCurveChange: (newCurve: AudioCurve) => void;
  /** Called when user clicks to remove crossfade */
  onRemove: () => void;
}

const HANDLE_WIDTH = 5;
const MIN_DURATION_PX = 10;

const CONTAINER: CSSProperties = {
  position: 'absolute',
  top: 0,
  bottom: 0,
  right: 0,
  zIndex: 4,
  pointerEvents: 'auto',
};

const OVERLAY: CSSProperties = {
  position: 'absolute',
  top: 0,
  bottom: 0,
  right: 0,
  background: 'rgba(200, 200, 200, 0.12)',
  borderLeft: '1px solid rgba(200, 200, 200, 0.3)',
};

const DRAG_HANDLE: CSSProperties = {
  position: 'absolute',
  left: 0,
  top: 0,
  bottom: 0,
  width: HANDLE_WIDTH,
  cursor: 'ew-resize',
  zIndex: 5,
};

const LABEL: CSSProperties = {
  position: 'absolute',
  bottom: 2,
  right: 4,
  fontSize: 7,
  fontFamily: 'monospace',
  color: '#888',
  pointerEvents: 'none',
  whiteSpace: 'nowrap',
};

/**
 * Render an equal-power or linear curve as an SVG overlay.
 * Equal power: qsin curve (louder at midpoint, FCP7 default)
 * Linear: straight diagonal lines
 */
function CurveVisualization({ width, height, curve }: { width: number; height: number; curve: AudioCurve }) {
  if (width < 8 || height < 8) return null;

  const points = 20;
  const fadeOutPath: string[] = [];
  const fadeInPath: string[] = [];

  for (let i = 0; i <= points; i++) {
    const t = i / points;
    const x = t * width;

    let outVal: number;
    let inVal: number;

    if (curve === 'equal_power') {
      // qsin: cos(t * pi/2) for fade out, sin(t * pi/2) for fade in
      outVal = Math.cos(t * Math.PI / 2);
      inVal = Math.sin(t * Math.PI / 2);
    } else {
      // linear
      outVal = 1 - t;
      inVal = t;
    }

    const outY = (1 - outVal) * (height * 0.6) + height * 0.1;
    const inY = (1 - inVal) * (height * 0.6) + height * 0.1;

    fadeOutPath.push(`${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${outY.toFixed(1)}`);
    fadeInPath.push(`${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${inY.toFixed(1)}`);
  }

  return (
    <svg
      style={{ position: 'absolute', top: 0, left: 0, width, height, pointerEvents: 'none' }}
      viewBox={`0 0 ${width} ${height}`}
    >
      {/* Fade out curve (outgoing clip) */}
      <path d={fadeOutPath.join('')} fill="none" stroke="#aaa" strokeWidth={1} opacity={0.6} />
      {/* Fade in curve (incoming clip) */}
      <path d={fadeInPath.join('')} fill="none" stroke="#777" strokeWidth={1} opacity={0.6} />
    </svg>
  );
}

export default function AudioCrossfadeHandle({
  durationSec,
  zoom,
  clipWidthPx,
  trackHeightPx,
  curve,
  alignment: _alignment,
  onDurationChange,
  onCurveChange,
  onRemove,
}: AudioCrossfadeProps) {
  const [hovered, setHovered] = useState(false);
  const [dragging, setDragging] = useState(false);
  const dragStartRef = useRef<{ startX: number; startDuration: number } | null>(null);

  const widthPx = Math.max(MIN_DURATION_PX, durationSec * zoom);
  // Clamp to clip width
  const clampedWidth = Math.min(widthPx, clipWidthPx * 0.8);

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setDragging(true);
    dragStartRef.current = { startX: e.clientX, startDuration: durationSec };

    const handleMove = (ev: MouseEvent) => {
      if (!dragStartRef.current) return;
      const dx = dragStartRef.current.startX - ev.clientX; // drag left = increase duration
      const deltaSec = dx / zoom;
      const newDuration = Math.max(0.05, dragStartRef.current.startDuration + deltaSec);
      onDurationChange(newDuration);
    };

    const handleUp = () => {
      setDragging(false);
      dragStartRef.current = null;
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
    };

    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
  }, [durationSec, zoom, onDurationChange]);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const nextCurve: AudioCurve = curve === 'equal_power' ? 'linear' : 'equal_power';
    onCurveChange(nextCurve);
  }, [curve, onCurveChange]);

  const handleClick = useCallback((e: React.MouseEvent) => {
    // Alt+click removes crossfade
    if (e.altKey) {
      e.stopPropagation();
      onRemove();
    }
  }, [onRemove]);

  return (
    <div
      data-testid="audio-crossfade-handle"
      style={{ ...CONTAINER, width: clampedWidth }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={handleClick}
      onContextMenu={handleContextMenu}
    >
      {/* Crossfade region overlay */}
      <div style={{
        ...OVERLAY,
        width: clampedWidth,
        background: hovered || dragging
          ? 'rgba(200, 200, 200, 0.18)'
          : 'rgba(200, 200, 200, 0.08)',
      }} />

      {/* Curve visualization */}
      <CurveVisualization width={clampedWidth} height={trackHeightPx} curve={curve} />

      {/* Drag handle on left edge */}
      <div
        data-testid="crossfade-drag-handle"
        style={{
          ...DRAG_HANDLE,
          background: hovered || dragging ? 'rgba(255,255,255,0.3)' : 'transparent',
        }}
        onMouseDown={handleDragStart}
      />

      {/* Duration label on hover */}
      {(hovered || dragging) && (
        <div style={LABEL}>
          {durationSec.toFixed(2)}s {curve === 'equal_power' ? 'EP' : 'LIN'}
        </div>
      )}
    </div>
  );
}
