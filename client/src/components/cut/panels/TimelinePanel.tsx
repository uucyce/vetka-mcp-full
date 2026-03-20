/**
 * MARKER_C4.3: Timeline panel wrapper for dockview.
 * MARKER_198: Multi-instance support — active timeline gets full controls,
 * inactive timelines show readonly snapshot with dimmed overlay + click-to-activate.
 */
import type { IDockviewPanelProps } from 'dockview-react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import { useTimelineInstanceStore } from '../../../store/useTimelineInstanceStore';
import TimelineToolbar from '../TimelineToolbar';
import TimelineTrackView from '../TimelineTrackView';
import BPMTrack from '../BPMTrack';

const PANEL_STYLE: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  overflow: 'hidden',
  background: '#0d0d0d',
  position: 'relative',
};

const INACTIVE_OVERLAY: React.CSSProperties = {
  position: 'absolute',
  inset: 0,
  background: 'rgba(0,0,0,0.35)',
  zIndex: 50,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  fontSize: 11,
  color: '#888',
  letterSpacing: '0.5px',
  textTransform: 'uppercase',
};

export default function TimelinePanel(props: IDockviewPanelProps) {
  const zoom = useCutEditorStore((s) => s.zoom);
  const scrollLeft = useCutEditorStore((s) => s.scrollLeft);
  const duration = useCutEditorStore((s) => s.duration);
  const activeTimelineId = useCutEditorStore((s) => s.timelineId);
  const scriptText = (props.params?.scriptText as string) ?? '';

  const panelTimelineId = props.params?.timelineId as string | undefined;
  const isActive = !panelTimelineId || panelTimelineId === activeTimelineId;

  const handleActivate = () => {
    if (panelTimelineId && !isActive) {
      const store = useCutEditorStore.getState();
      store.snapshotTimeline(store.timelineId);
      store.restoreTimeline(panelTimelineId);
      useTimelineInstanceStore.getState().setActiveTimeline(panelTimelineId);
    }
  };

  return (
    <div
      style={PANEL_STYLE}
      onMouseDown={() => useCutEditorStore.getState().setFocusedPanel('timeline')}
    >
      {isActive && <TimelineToolbar />}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <TimelineTrackView timelineId={panelTimelineId} />
      </div>
      {isActive && (
        <BPMTrack
          timelineId={activeTimelineId}
          scriptText={scriptText}
          pxPerSec={zoom}
          scrollLeft={scrollLeft}
          durationSec={duration}
        />
      )}
      {!isActive && (
        <div style={INACTIVE_OVERLAY} onClick={handleActivate}>
          Click to activate
        </div>
      )}
    </div>
  );
}
