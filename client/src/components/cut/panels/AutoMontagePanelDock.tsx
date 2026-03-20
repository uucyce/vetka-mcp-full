/**
 * MARKER_C14: Auto-Montage panel wrapper for dockview.
 * Analysis tab group — no focusedPanel mapping (non-scoped).
 */
import type { IDockviewPanelProps } from 'dockview-react';
import AutoMontagePanel from '../AutoMontagePanel';

export default function AutoMontagePanelDock(_props: IDockviewPanelProps) {
  return (
    <div style={{ height: '100%', overflow: 'auto', background: '#0d0d0d' }}>
      <AutoMontagePanel />
    </div>
  );
}
