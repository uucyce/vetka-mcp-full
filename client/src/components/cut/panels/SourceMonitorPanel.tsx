/**
 * MARKER_C4.2: Source Monitor panel wrapper for dockview.
 * Renders VideoPreview (feed=source) + MonitorTransport.
 * Sets focusedPanel='source' on mouse interaction.
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

export default function SourceMonitorPanel(_props: IDockviewPanelProps) {
  return (
    <div
      style={PANEL_STYLE}
      data-testid="cut-panel-source"
      onMouseDown={() => useCutEditorStore.getState().setFocusedPanel('source')}
    >
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <VideoPreview feed="source" />
      </div>
      <MonitorTransport feed="source" />
    </div>
  );
}
