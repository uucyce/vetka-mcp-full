/**
 * MARKER_C4.5: History panel wrapper for dockview.
 * Analysis tab group — no focusedPanel mapping (non-scoped).
 */
import type { IDockviewPanelProps } from 'dockview-react';
import HistoryPanel from '../HistoryPanel';

export default function HistoryPanelDock(_props: IDockviewPanelProps) {
  return (
    <div style={{ height: '100%', overflow: 'auto', background: '#0d0d0d' }}>
      <HistoryPanel />
    </div>
  );
}
