/**
 * MARKER_GAMMA-27/30: StatusBar — bottom info strip for CUT NLE.
 *
 * Shows: zoom % | fps | mark in/out (when set).
 * Monochrome grey only. FCP7 reference.
 */
import { useCutEditorStore } from '../../store/useCutEditorStore';

// MARKER_GAMMA-MRK4: Format seconds as HH:MM:SS:FF timecode
function fmtTC(sec: number, fps: number): string {
  const totalFrames = Math.round(sec * fps);
  const f = totalFrames % fps;
  const totalSec = Math.floor(totalFrames / fps);
  const s = totalSec % 60;
  const m = Math.floor(totalSec / 60) % 60;
  const h = Math.floor(totalSec / 3600);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
}

export default function StatusBar() {
  const zoom = useCutEditorStore((s) => s.zoom);
  const fps = useCutEditorStore((s) => s.projectFramerate);
  const markIn = useCutEditorStore((s) => s.sequenceMarkIn);
  const markOut = useCutEditorStore((s) => s.sequenceMarkOut);

  // zoom is px/sec (default 60). Display as percentage of default.
  const zoomPct = zoom ? `${Math.round((zoom / 60) * 100)}%` : '100%';
  const fpsLabel = fps ? `${fps} fps` : '';
  const fpsVal = fps || 24;
  const hasMarks = markIn != null || markOut != null;

  return (
    <div
      data-testid="cut-status-bar"
      style={{
        height: 18,
        minHeight: 18,
        maxHeight: 18,
        display: 'flex',
        alignItems: 'center',
        padding: '0 8px',
        gap: 12,
        background: '#0a0a0a',
        borderTop: '1px solid #222',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontSize: 9,
        color: '#888',
        letterSpacing: '0.3px',
        userSelect: 'none',
        flexShrink: 0,
      }}
    >
      <span>Zoom {zoomPct}</span>
      <span style={{ color: '#333' }}>|</span>
      <span>{fpsLabel}</span>
      {/* MARKER_GAMMA-MRK4: Mark in/out display */}
      {hasMarks && (
        <>
          <span style={{ color: '#333' }}>|</span>
          <span data-testid="mark-in-out" style={{ fontVariantNumeric: 'tabular-nums' }}>
            IN {markIn != null ? fmtTC(markIn, fpsVal) : '—'}
            {' '}
            OUT {markOut != null ? fmtTC(markOut, fpsVal) : '—'}
          </span>
        </>
      )}
    </div>
  );
}
