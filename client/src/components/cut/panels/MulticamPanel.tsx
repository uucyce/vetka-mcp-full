/**
 * MARKER_GAMMA-MULTICAM-PANEL: Multicam angle grid panel wrapper for dockview.
 * FCP7 Ch.42: Multiclip viewer shows all camera angles in grid.
 * Maps to focusedPanel 'multicam' for scope isolation.
 */
import type { IDockviewPanelProps } from 'dockview-react';
import MulticamViewer from '../MulticamViewer';

export default function MulticamPanel(_props: IDockviewPanelProps) {
  return (
    <div style={{ height: '100%', overflow: 'hidden', background: '#0a0a0a' }}>
      <MulticamViewer />
    </div>
  );
}
