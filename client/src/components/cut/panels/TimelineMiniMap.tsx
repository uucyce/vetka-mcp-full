/**
 * MARKER_GAMMA-MN1: Mini timeline navigator — overview bar with zoom viewport indicator.
 *
 * Thin horizontal bar (20px) showing:
 *   - Full sequence duration as background
 *   - Clip blocks as simplified rectangles (per lane)
 *   - Current viewport as draggable bright rectangle
 *   - Playhead position as white vertical line
 *   - Click anywhere to jump viewport, drag to pan
 *
 * Reads from useCutEditorStore: zoom, scrollLeft, duration, currentTime, lanes.
 * Premiere Pro style mini-map / overview bar.
 */
import { useCallback, useRef, type CSSProperties, type MouseEvent } from 'react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';

const BAR_HEIGHT = 20;

const CONTAINER: CSSProperties = {
  height: BAR_HEIGHT,
  minHeight: BAR_HEIGHT,
  background: '#080808',
  borderTop: '1px solid #222',
  position: 'relative',
  cursor: 'pointer',
  userSelect: 'none',
  overflow: 'hidden',
};

export default function TimelineMiniMap() {
  const zoom = useCutEditorStore((s) => s.zoom);
  const scrollLeft = useCutEditorStore((s) => s.scrollLeft);
  const duration = useCutEditorStore((s) => s.duration);
  const currentTime = useCutEditorStore((s) => s.currentTime);
  const lanes = useCutEditorStore((s) => s.lanes);
  const setScrollLeft = useCutEditorStore((s) => s.setScrollLeft);
  const seek = useCutEditorStore((s) => s.seek);

  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  // Total content width in pixels and viewport width
  const totalPx = duration > 0 ? duration * zoom : 1;
  // Assume viewport is ~800px wide (approximation; actual comes from container)
  const viewportPx = containerRef.current?.clientWidth || 800;

  // Scale factor: minimap width → total content
  const barWidth = containerRef.current?.clientWidth || 1;
  const scale = barWidth / Math.max(totalPx, 1);

  // Viewport rectangle position and width in minimap coordinates
  const vpLeft = scrollLeft * scale;
  const vpWidth = Math.max(4, viewportPx * scale);

  // Playhead position in minimap
  const playheadX = currentTime * zoom * scale;

  const handleMouseAction = useCallback((clientX: number) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect || duration <= 0) return;
    const x = clientX - rect.left;
    const ratio = x / rect.width;
    const targetTime = ratio * duration;

    if (dragging.current) {
      // Pan viewport: set scrollLeft so viewport centers on click position
      const newScroll = targetTime * zoom - viewportPx / 2;
      setScrollLeft(Math.max(0, newScroll));
    } else {
      // Click: seek + center viewport
      seek(Math.max(0, Math.min(duration, targetTime)));
      const newScroll = targetTime * zoom - viewportPx / 2;
      setScrollLeft(Math.max(0, newScroll));
    }
  }, [duration, zoom, viewportPx, setScrollLeft, seek]);

  const onMouseDown = useCallback((e: MouseEvent) => {
    dragging.current = true;
    handleMouseAction(e.clientX);

    const onMove = (ev: globalThis.MouseEvent) => handleMouseAction(ev.clientX);
    const onUp = () => {
      dragging.current = false;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, [handleMouseAction]);

  return (
    <div
      ref={containerRef}
      style={CONTAINER}
      onMouseDown={onMouseDown}
      data-testid="timeline-minimap"
    >
      {/* Clip blocks — simplified rectangles */}
      {duration > 0 && lanes.map((lane, laneIdx) => {
        const laneY = (laneIdx / Math.max(lanes.length, 1)) * (BAR_HEIGHT - 2);
        const laneH = Math.max(2, (BAR_HEIGHT - 2) / Math.max(lanes.length, 1) - 1);
        return lane.clips.map((clip) => {
          const x = (clip.start_sec / duration) * barWidth;
          const w = Math.max(1, (clip.duration_sec / duration) * barWidth);
          return (
            <div
              key={clip.clip_id}
              style={{
                position: 'absolute',
                left: x,
                top: laneY + 1,
                width: w,
                height: laneH,
                background: lane.lane_id.startsWith('audio') ? '#333' : '#444',
                borderRadius: 1,
                pointerEvents: 'none',
              }}
            />
          );
        });
      })}

      {/* Viewport rectangle */}
      <div
        style={{
          position: 'absolute',
          left: vpLeft,
          top: 0,
          width: vpWidth,
          height: BAR_HEIGHT,
          border: '1px solid #666',
          background: 'rgba(255,255,255,0.04)',
          borderRadius: 2,
          pointerEvents: 'none',
        }}
      />

      {/* Playhead */}
      {duration > 0 && (
        <div
          style={{
            position: 'absolute',
            left: playheadX,
            top: 0,
            width: 1,
            height: BAR_HEIGHT,
            background: '#fff',
            pointerEvents: 'none',
            zIndex: 1,
          }}
        />
      )}
    </div>
  );
}
