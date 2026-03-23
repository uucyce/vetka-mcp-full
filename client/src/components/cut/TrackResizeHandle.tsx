/**
 * MARKER_GAMMA-RESIZE: Standalone TrackResizeHandle for timeline track height.
 *
 * Renders a horizontal drag handle at the bottom edge of a track header/lane.
 * Alpha integrates this into TimelineTrackView per-lane rendering.
 *
 * Features:
 * - Drag to resize track height (mousedown → mousemove → mouseup)
 * - Visual feedback: transparent → #333 on hover → #555 while dragging
 * - Min/max height clamping
 * - Calls onResize(laneId, newHeight) on drag end
 * - Double-click resets to default height
 *
 * CSS: styled via [data-testid="track-resize-handle"] in dockview-cut-theme.css
 */
import { useCallback, useRef, useState, type CSSProperties, memo } from 'react';

const HANDLE_HEIGHT = 4;
const DEFAULT_TRACK_HEIGHT = 80;
const MIN_TRACK_HEIGHT = 32;
const MAX_TRACK_HEIGHT = 300;

const HANDLE_STYLE: CSSProperties = {
  width: '100%',
  height: HANDLE_HEIGHT,
  position: 'absolute',
  bottom: 0,
  left: 0,
  zIndex: 5,
};

export interface TrackResizeHandleProps {
  laneId: string;
  currentHeight: number;
  onResize: (laneId: string, newHeight: number) => void;
  onResizeStart?: (laneId: string) => void;
  onResizeEnd?: (laneId: string) => void;
}

function TrackResizeHandleInner({
  laneId,
  currentHeight,
  onResize,
  onResizeStart,
  onResizeEnd,
}: TrackResizeHandleProps) {
  const [dragging, setDragging] = useState(false);
  const startYRef = useRef(0);
  const startHeightRef = useRef(currentHeight);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragging(true);
      startYRef.current = e.clientY;
      startHeightRef.current = currentHeight;
      onResizeStart?.(laneId);

      const handleMouseMove = (ev: MouseEvent) => {
        const delta = ev.clientY - startYRef.current;
        const newHeight = Math.max(
          MIN_TRACK_HEIGHT,
          Math.min(MAX_TRACK_HEIGHT, startHeightRef.current + delta),
        );
        onResize(laneId, newHeight);
      };

      const handleMouseUp = () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        setDragging(false);
        onResizeEnd?.(laneId);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [laneId, currentHeight, onResize, onResizeStart, onResizeEnd],
  );

  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      onResize(laneId, DEFAULT_TRACK_HEIGHT);
    },
    [laneId, onResize],
  );

  return (
    <div
      data-testid="track-resize-handle"
      data-dragging={dragging ? 'true' : 'false'}
      style={HANDLE_STYLE}
      onMouseDown={handleMouseDown}
      onDoubleClick={handleDoubleClick}
    />
  );
}

const TrackResizeHandle = memo(TrackResizeHandleInner);
export default TrackResizeHandle;

/**
 * Re-export constants for integration.
 */
export { HANDLE_HEIGHT, DEFAULT_TRACK_HEIGHT, MIN_TRACK_HEIGHT, MAX_TRACK_HEIGHT };
