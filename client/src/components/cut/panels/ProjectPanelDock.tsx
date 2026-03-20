/**
 * MARKER_C4.4: Project panel wrapper for dockview.
 * Sets focusedPanel='project' on mouse interaction.
 */
import type { IDockviewPanelProps } from 'dockview-react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import ProjectPanel from '../ProjectPanel';

export default function ProjectPanelDock(_props: IDockviewPanelProps) {
  return (
    <div
      style={{ height: '100%', overflow: 'hidden', background: '#0d0d0d' }}
      onMouseDown={() => useCutEditorStore.getState().setFocusedPanel('project')}
    >
      <ProjectPanel />
    </div>
  );
}
