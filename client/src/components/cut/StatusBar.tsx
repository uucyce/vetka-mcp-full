/**
 * MARKER_GAMMA-27/30 + SB1 + SB2: StatusBar — bottom info strip for CUT NLE.
 *
 * Shows: sequence name | timecode | zoom % | fps | tracks | duration | selection | mark in/out.
 * Monochrome grey only. FCP7 reference.
 */
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useSelectionStore } from '../../store/useSelectionStore';
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
  const currentTime = useCutEditorStore((s) => s.currentTime);
  const markIn = useCutEditorStore((s) => s.sequenceMarkIn);
  const markOut = useCutEditorStore((s) => s.sequenceMarkOut);
  const lanes = useCutEditorStore((s) => s.lanes);
  const duration = useCutEditorStore((s) => s.duration);
  const selectedClipId = useSelectionStore((s) => s.selectedClipId);
  const activePreset = useDockviewStore((s) => s.activePreset);
  const renderProgress = useCutEditorStore((s) => s.renderProgress);
  // MARKER_GAMMA-SB2: Sequence name from timelineId
  const timelineId = useCutEditorStore((s) => s.timelineId);
  const timelineTabs = useCutEditorStore((s) => s.timelineTabs);

  const zoomPct = zoom ? `${Math.round((zoom / 60) * 100)}%` : '100%';
  const fpsLabel = fps ? `${fps} fps` : '';
  const fpsVal = fps || 24;
  const hasMarks = markIn != null || markOut != null;
  const trackCount = lanes.length;
  const clipCount = lanes.reduce((sum, lane) => sum + lane.clips.length, 0);

  // Sequence name
  const seqName = timelineTabs.find((t) => t.id === timelineId)?.label || timelineId || 'Main';

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
      {/* MARKER_GAMMA-SB2: Sequence name */}
      <span style={{ color: '#aaa', fontWeight: 600 }}>{seqName}</span>

      {/* MARKER_GAMMA-SB2: Current playhead timecode */}
      <span style={{ fontVariantNumeric: 'tabular-nums', fontFamily: 'monospace', color: '#999', fontSize: 10 }}>
        {fmtTC(currentTime, fpsVal)}
      </span>

      <span style={SEP}>|</span>
      <span>Zoom {zoomPct}</span>
      <span style={SEP}>|</span>
      <span>{fpsLabel}</span>
      <span style={SEP}>|</span>
      <span style={{ textTransform: 'capitalize' }}>{activePreset}</span>

      {renderProgress != null && (
        <>
          <span style={SEP}>|</span>
          <span data-testid="render-progress" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            Render {Math.round(renderProgress * 100)}%
            <span style={{
              display: 'inline-block',
              width: 40,
              height: 4,
              background: '#222',
              borderRadius: 2,
              overflow: 'hidden',
            }}>
              <span style={{
                display: 'block',
                width: `${renderProgress * 100}%`,
                height: '100%',
                background: '#999',
                borderRadius: 2,
              }} />
            </span>
          </span>
        </>
      )}

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

      {selectedClipId && (
        <>
          <span style={SEP}>|</span>
          <span style={{ color: '#aaa' }}>1 selected</span>
        </>
      )}

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
