/**
 * MARKER_GAMMA-27/30 + SB1: StatusBar — bottom info strip for CUT NLE.
 *
 * Shows: zoom % | fps | tracks | duration | selection | mark in/out (when set).
 * Monochrome grey only. FCP7 reference.
 */
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useDockviewStore } from '../../store/useDockviewStore';

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

// Format duration as M:SS or H:MM:SS
function fmtDur(sec: number): string {
  if (sec <= 0) return '0:00';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

const SEP = { color: '#333' } as const;

export default function StatusBar() {
  const zoom = useCutEditorStore((s) => s.zoom);
  const fps = useCutEditorStore((s) => s.projectFramerate);
  const markIn = useCutEditorStore((s) => s.sequenceMarkIn);
  const markOut = useCutEditorStore((s) => s.sequenceMarkOut);
  const lanes = useCutEditorStore((s) => s.lanes);
  const duration = useCutEditorStore((s) => s.duration);
  const selectedClipId = useCutEditorStore((s) => s.selectedClipId);
  const activePreset = useDockviewStore((s) => s.activePreset);

  // zoom is px/sec (default 60). Display as percentage of default.
  const zoomPct = zoom ? `${Math.round((zoom / 60) * 100)}%` : '100%';
  const fpsLabel = fps ? `${fps} fps` : '';
  const fpsVal = fps || 24;
  const hasMarks = markIn != null || markOut != null;

  // MARKER_GAMMA-SB1: Track count + total clip count
  const trackCount = lanes.length;
  const clipCount = lanes.reduce((sum, lane) => sum + lane.clips.length, 0);

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
      {/* Left section: zoom + fps + workspace */}
      <span>Zoom {zoomPct}</span>
      <span style={SEP}>|</span>
      <span>{fpsLabel}</span>
      <span style={SEP}>|</span>
      <span style={{ textTransform: 'capitalize' }}>{activePreset}</span>

      {/* Center section: tracks + clips + duration */}
      {trackCount > 0 && (
        <>
          <span style={SEP}>|</span>
          <span>{trackCount} {trackCount === 1 ? 'track' : 'tracks'}, {clipCount} {clipCount === 1 ? 'clip' : 'clips'}</span>
        </>
      )}
      {duration > 0 && (
        <>
          <span style={SEP}>|</span>
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>{fmtDur(duration)}</span>
        </>
      )}

      {/* Selection indicator */}
      {selectedClipId && (
        <>
          <span style={SEP}>|</span>
          <span style={{ color: '#aaa' }}>1 selected</span>
        </>
      )}

      {/* MARKER_GAMMA-MRK4: Mark in/out display */}
      {hasMarks && (
        <>
          <span style={SEP}>|</span>
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
