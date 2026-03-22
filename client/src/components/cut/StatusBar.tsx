/**
 * MARKER_GAMMA-27/30: StatusBar — bottom info strip for CUT NLE.
 *
 * Shows ONLY: zoom % | fps. Nothing else.
 * Monochrome grey only. FCP7 reference.
 */
import { useCutEditorStore } from '../../store/useCutEditorStore';

export default function StatusBar() {
  const zoom = useCutEditorStore((s) => s.zoom);
  const fps = useCutEditorStore((s) => s.projectFramerate);

  // zoom is px/sec (default 60). Display as percentage of default.
  const zoomPct = zoom ? `${Math.round((zoom / 60) * 100)}%` : '100%';
  const fpsLabel = fps ? `${fps} fps` : '';

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
    </div>
  );
}
