/**
 * MARKER_C4.4: Script panel wrapper for dockview.
 * Sets focusedPanel='script' on mouse interaction.
 */
import type { IDockviewPanelProps } from 'dockview-react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import ScriptPanel from '../ScriptPanel';

export default function ScriptPanelDock(props: IDockviewPanelProps) {
  return (
    <div
      style={{ height: '100%', overflow: 'hidden', background: '#0d0d0d' }}
      onMouseDown={() => useCutEditorStore.getState().setFocusedPanel('script')}
    >
      <ScriptPanel scriptText={props.params?.scriptText as string ?? ''} />
    </div>
  );
}
