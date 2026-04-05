/**
 * MARKER_C4.5: StorySpace3D panel wrapper for dockview.
 * Analysis tab group — no focusedPanel mapping (non-scoped).
 */
import type { IDockviewPanelProps } from 'dockview-react';
import StorySpace3D from '../StorySpace3D';

export default function StorySpacePanelDock(_props: IDockviewPanelProps) {
  return (
    <div style={{ height: '100%', overflow: 'hidden', background: '#0d0d0d' }}>
      <StorySpace3D />
    </div>
  );
}
