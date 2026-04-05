/**
 * MARKER_C4.4: DAG Graph panel wrapper for dockview.
 * Sets focusedPanel='dag' on mouse interaction.
 */
import type { IDockviewPanelProps } from 'dockview-react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import DAGProjectPanel from '../DAGProjectPanel';

export default function GraphPanelDock(_props: IDockviewPanelProps) {
  return (
    <div
      style={{ height: '100%', overflow: 'hidden', background: '#0d0d0d' }}
      onMouseDown={() => useCutEditorStore.getState().setFocusedPanel('dag')}
    >
      <DAGProjectPanel />
    </div>
  );
}
