/**
 * MARKER_C4.5: ClipInspector panel wrapper for dockview.
 * Analysis tab group — no focusedPanel mapping (non-scoped).
 */
import type { IDockviewPanelProps } from 'dockview-react';
import ClipInspector from '../ClipInspector';

export default function ClipPanelDock(_props: IDockviewPanelProps) {
  return (
    <div style={{ height: '100%', overflow: 'auto', background: '#0d0d0d' }}>
      <ClipInspector />
    </div>
  );
}
