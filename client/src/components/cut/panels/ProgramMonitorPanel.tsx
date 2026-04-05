/**
 * MARKER_C4.2: Program Monitor panel wrapper for dockview.
 * Renders VideoPreview (feed=program) + MonitorTransport.
 * Sets focusedPanel='program' on mouse interaction.
 */
import type { IDockviewPanelProps } from 'dockview-react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import VideoPreview from '../VideoPreview';
import MonitorTransport from '../MonitorTransport';

const PANEL_STYLE: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  background: '#0d0d0d',
};

export default function ProgramMonitorPanel(_props: IDockviewPanelProps) {
  return (
    <div
      style={PANEL_STYLE}
      data-testid="cut-panel-program"
      onMouseDown={() => useCutEditorStore.getState().setFocusedPanel('program')}
    >
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <VideoPreview feed="program" />
      </div>
      <MonitorTransport feed="program" />
    </div>
  );
}
