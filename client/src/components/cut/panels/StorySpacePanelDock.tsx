/**
 * MARKER_C4.5 + GAMMA-PW6: StorySpace3D panel wrapper for dockview.
 * Analysis tab group — no focusedPanel mapping (non-scoped).
 * Reads activeTimelineId from store for reactive fetch.
 */
import type { IDockviewPanelProps } from 'dockview-react';
import StorySpace3D from '../StorySpace3D';
import { useCutEditorStore } from '../../../store/useCutEditorStore';

export default function StorySpacePanelDock(_props: IDockviewPanelProps) {
  const timelineId = useCutEditorStore((s) => s.timelineId) || 'main';

  return (
    <div style={{ height: '100%', overflow: 'hidden', background: '#0d0d0d' }}>
      <StorySpace3D timelineId={timelineId} />
    </div>
  );
}
