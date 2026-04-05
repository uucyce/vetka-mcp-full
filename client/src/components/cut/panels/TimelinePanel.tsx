/**
 * MARKER_C4.3 + C12.3: Timeline panel wrapper for dockview.
 * MARKER_198: Multi-instance support — active timeline gets full controls,
 * inactive timelines show readonly snapshot with dimmed overlay + click-to-activate.
 *
 * MARKER_GAMMA-C12.3: Enhanced active/inactive visual differentiation.
 * Active: bright border, full toolbar + BPMTrack.
 * Inactive: dimmed overlay with timeline label + click-to-activate.
 */
import type { IDockviewPanelProps } from 'dockview-react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import { useTimelineInstanceStore } from '../../../store/useTimelineInstanceStore';
import TimelineToolbar from '../TimelineToolbar';
import TimelineTrackView from '../TimelineTrackView';
import BPMTrack from '../BPMTrack';

const PANEL_ACTIVE: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  overflow: 'hidden',
  background: '#0d0d0d',
  position: 'relative',
  // MARKER_GAMMA-C12.3: Active timeline gets subtle bright border
  boxShadow: 'inset 0 0 0 1px #333',
};

const PANEL_INACTIVE: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  overflow: 'hidden',
  background: '#080808',
  position: 'relative',
};

const INACTIVE_OVERLAY: React.CSSProperties = {
  position: 'absolute',
  inset: 0,
  background: 'rgba(0,0,0,0.4)',
  zIndex: 50,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  gap: 4,
};

export default function TimelinePanel(props: IDockviewPanelProps) {
  const zoom = useCutEditorStore((s) => s.zoom);
  const scrollLeft = useCutEditorStore((s) => s.scrollLeft);
  const duration = useCutEditorStore((s) => s.duration);
  const activeTimelineId = useCutEditorStore((s) => s.timelineId);
  const scriptText = (props.params?.scriptText as string) ?? '';

  const panelTimelineId = props.params?.timelineId as string | undefined;
  const isActive = !panelTimelineId || panelTimelineId === activeTimelineId;

  // Find label for this timeline
  const timelineTabs = useCutEditorStore((s) => s.timelineTabs);
  const tabLabel = panelTimelineId
    ? timelineTabs.find((t) => t.id === panelTimelineId)?.label || panelTimelineId
    : 'Main Timeline';

  const handleActivate = () => {
    if (panelTimelineId && !isActive) {
      const store = useCutEditorStore.getState();
      // Snapshot current before switching
      store.snapshotTimeline(store.timelineId);
      store.restoreTimeline(panelTimelineId);
      useTimelineInstanceStore.getState().setActiveTimeline(panelTimelineId);
    }
  };

  return (
    <div
      style={isActive ? PANEL_ACTIVE : PANEL_INACTIVE}
      onMouseDown={() => {
        useCutEditorStore.getState().setFocusedPanel('timeline');
        // Auto-activate on mousedown if this is an inactive timeline panel
        if (!isActive && panelTimelineId) handleActivate();
      }}
    >
      {isActive && <TimelineToolbar />}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <TimelineTrackView timelineId={panelTimelineId} />
      </div>
      {/* MARKER_GAMMA-BPM-FIX: Wrapper prevents label overlap at bottom edge */}
      {isActive && (
        <div style={{ flexShrink: 0, minHeight: 40, position: 'relative' }}>
          <BPMTrack
            timelineId={activeTimelineId}
            scriptText={scriptText}
            pxPerSec={zoom}
            scrollLeft={scrollLeft}
            durationSec={duration}
          />
        </div>
      )}
      {/* MARKER_GAMMA-C12.3: Inactive timeline overlay with label */}
      {!isActive && (
        <div style={INACTIVE_OVERLAY} onClick={handleActivate}>
          <span style={{
            fontSize: 10,
            color: '#666',
            fontFamily: 'system-ui, sans-serif',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            {tabLabel}
          </span>
          <span style={{
            fontSize: 9,
            color: '#444',
            fontFamily: 'system-ui, sans-serif',
          }}>
            Click to activate
          </span>
        </div>
      )}
    </div>
  );
}
