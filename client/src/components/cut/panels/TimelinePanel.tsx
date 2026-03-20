/**
 * MARKER_C4.3: Timeline panel wrapper for dockview.
 * Renders TimelineToolbar + TimelineTabBar + TimelineTrackView + BPMTrack.
 * Sets focusedPanel='timeline' on mouse interaction.
 */
import type { IDockviewPanelProps } from 'dockview-react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import TimelineToolbar from '../TimelineToolbar';
import TimelineTabBar from '../TimelineTabBar';
import TimelineTrackView from '../TimelineTrackView';
import BPMTrack from '../BPMTrack';

const PANEL_STYLE: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  overflow: 'hidden',
  background: '#0d0d0d',
};

export default function TimelinePanel(props: IDockviewPanelProps) {
  const zoom = useCutEditorStore((s) => s.zoom);
  const scrollLeft = useCutEditorStore((s) => s.scrollLeft);
  const duration = useCutEditorStore((s) => s.duration);
  const timelineId = useCutEditorStore((s) => s.timelineId);
  const scriptText = (props.params?.scriptText as string) ?? '';

  return (
    <div
      style={PANEL_STYLE}
      onMouseDown={() => useCutEditorStore.getState().setFocusedPanel('timeline')}
    >
      <TimelineToolbar />
      <TimelineTabBar />
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <TimelineTrackView />
      </div>
      <BPMTrack
        timelineId={timelineId}
        scriptText={scriptText}
        pxPerSec={zoom}
        scrollLeft={scrollLeft}
        durationSec={duration}
      />
    </div>
  );
}
