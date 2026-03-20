/**
 * MARKER_C4.5: PulseInspector panel wrapper for dockview.
 * Analysis tab group — no focusedPanel mapping (non-scoped).
 */
import type { IDockviewPanelProps } from 'dockview-react';
import PulseInspector from '../PulseInspector';

export default function InspectorPanelDock(_props: IDockviewPanelProps) {
  return (
    <div style={{ height: '100%', overflow: 'auto', background: '#0d0d0d' }}>
      <PulseInspector />
    </div>
  );
}
