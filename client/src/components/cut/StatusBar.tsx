/**
 * MARKER_GAMMA-27: StatusBar — bottom info strip for CUT NLE.
 *
 * 18px strip at the bottom of the editor showing:
 *   [active tool] | [zoom %] | [fps] | [workspace preset] | [save status]
 *
 * Monochrome grey only. FCP7/Premiere reference.
 */
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useDockviewStore } from '../../store/useDockviewStore';

const TOOL_LABELS: Record<string, string> = {
  selection: 'V Selection',
  razor: 'C Razor',
  hand: 'H Hand',
  zoom: 'Z Zoom',
  slip: 'Y Slip',
  slide: 'U Slide',
  ripple: 'B Ripple',
  roll: 'N Roll',
};

const SAVE_LABELS: Record<string, string> = {
  idle: '',
  saving: 'Saving...',
  saved: 'Saved',
  error: 'Save Error',
};

export default function StatusBar() {
  const activeTool = useCutEditorStore((s) => s.activeTool);
  const zoom = useCutEditorStore((s) => s.zoom);
  const fps = useCutEditorStore((s) => s.projectFramerate);
  const saveStatus = useCutEditorStore((s) => s.saveStatus);
  const hasUnsavedChanges = useCutEditorStore((s) => s.hasUnsavedChanges);
  const activePreset = useDockviewStore((s) => s.activePreset);

  const toolLabel = TOOL_LABELS[activeTool] || activeTool;
  // zoom is px/sec (default 60). Display as percentage of default.
  const zoomPct = zoom ? `${Math.round((zoom / 60) * 100)}%` : '100%';
  const fpsLabel = fps ? `${fps} fps` : '';
  const presetLabel = activePreset ? activePreset.charAt(0).toUpperCase() + activePreset.slice(1) : '';
  const saveLabel = SAVE_LABELS[saveStatus] || '';
  const modifiedDot = hasUnsavedChanges ? ' \u00b7' : '';

  return (
    <div
      data-testid="cut-status-bar"
      style={{
        height: 18,
        minHeight: 18,
        maxHeight: 18,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 8px',
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
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <span style={{ color: '#aaa', textTransform: 'uppercase' }}>{toolLabel}</span>
        <Separator />
        <span>Zoom {zoomPct}</span>
        <Separator />
        <span>{fpsLabel}</span>
      </div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <span style={{ textTransform: 'uppercase' }}>{presetLabel}</span>
        {(saveLabel || modifiedDot) && (
          <>
            <Separator />
            <span>{saveLabel}{modifiedDot}</span>
          </>
        )}
      </div>
    </div>
  );
}

function Separator() {
  return <span style={{ color: '#333' }}>|</span>;
}
