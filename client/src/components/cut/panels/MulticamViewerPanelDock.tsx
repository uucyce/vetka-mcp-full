/**
 * MARKER_MULTICAM_DOCK: Multicam Viewer panel wrapper for dockview.
 * Thin wrapper — no focusedPanel mapping (non-scoped panel).
 */
import type { IDockviewPanelProps } from 'dockview-react';
import MulticamViewer from '../MulticamViewer';

export default function MulticamViewerPanelDock(_props: IDockviewPanelProps) {
  return (
    <div style={{ height: '100%', overflow: 'hidden', background: '#0a0a0a' }}>
      <MulticamViewer />
    </div>
  );
}
