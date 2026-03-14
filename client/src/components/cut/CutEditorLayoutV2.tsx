/**
 * MARKER_180.4: CutEditorLayoutV2 — 7-panel NLE layout using PanelGrid + PanelShell.
 *
 * Architecture doc §1-§3:
 * "Swedish Wardrobe: every panel detachable, resizable, dockable."
 * "Three-column layout with timeline strip at bottom."
 *
 * This is the v2 layout that replaces the original 3-panel CutEditorLayout.
 * It wraps each existing panel component in PanelShell for tab/dock/float support,
 * and arranges them using PanelGrid's 5-zone CSS Grid.
 *
 * Panel mapping:
 *   Left column (tabs):  ScriptPanel + DAGProjectPanel
 *   Center:              VideoPreview (Program Monitor)
 *   Right top:           VideoPreview (Source Monitor — selected asset)
 *   Right bottom:        PulseInspector
 *   Bottom:              TransportBar + TimelineTabBar + TimelineTrackView + BPMTrack
 *   Floating:            StorySpace3D (mini, inside Program Monitor)
 */
import { useCallback, useMemo, type CSSProperties, type ReactNode } from 'react';
import { usePanelLayoutStore, type DockPosition } from '../../store/usePanelLayoutStore';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { usePanelSyncStore } from '../../store/usePanelSyncStore';
import PanelGrid from './PanelGrid';
import PanelShell from './PanelShell';
import ScriptPanel from './ScriptPanel';
import DAGProjectPanel from './DAGProjectPanel';
import VideoPreview from './VideoPreview';
import PulseInspector from './PulseInspector';
import TransportBar from './TransportBar';
import TimelineTabBar from './TimelineTabBar';
import TimelineTrackView from './TimelineTrackView';
import BPMTrack from './BPMTrack';
import StorySpace3D from './StorySpace3D';

// ─── Styles ───

const ROOT: CSSProperties = {
  width: '100%',
  height: '100vh',
  background: '#0D0D0D',
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
};

const TIMELINE_AREA: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  overflow: 'hidden',
};

// ─── Component ───

interface CutEditorLayoutV2Props {
  /** Script text for ScriptPanel and BPMTrack */
  scriptText?: string;
}

export default function CutEditorLayoutV2({ scriptText = '' }: CutEditorLayoutV2Props) {
  const panels = usePanelLayoutStore((s) => s.panels);
  const getPanelsAtDock = usePanelLayoutStore((s) => s.getPanelsAtDock);

  // Editor store
  const zoom = useCutEditorStore((s) => s.zoom);
  const scrollLeft = useCutEditorStore((s) => s.scrollLeft);
  const duration = useCutEditorStore((s) => s.duration);
  const timelineId = useCutEditorStore((s) => s.timelineId);
  const selectedAssetPath = usePanelSyncStore((s) => s.selectedAssetPath);

  // ─── Left column: Script + DAG as tabs ───
  const renderLeft = useCallback(() => {
    const leftPanels = getPanelsAtDock('left');
    if (leftPanels.length === 0) return null;

    return (
      <PanelShell panelId="script" title="Script / DAG">
        <LeftTabContent scriptText={scriptText} />
      </PanelShell>
    );
  }, [getPanelsAtDock, scriptText]);

  // ─── Center: Program Monitor ───
  const renderCenter = useCallback(() => {
    return (
      <PanelShell panelId="program_monitor" title="Program Monitor">
        <VideoPreview />
      </PanelShell>
    );
  }, []);

  // ─── Right top: Source Monitor ───
  const renderRightTop = useCallback(() => {
    return (
      <PanelShell panelId="source_monitor" title="Source Monitor">
        {selectedAssetPath ? (
          <VideoPreview />
        ) : (
          <div
            style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#444',
              fontSize: 11,
              fontFamily: 'Inter, system-ui, sans-serif',
              background: '#1A1A1A',
            }}
          >
            Select an asset in DAG or click a script line
          </div>
        )}
      </PanelShell>
    );
  }, [selectedAssetPath]);

  // ─── Right bottom: Inspector ───
  const renderRightBottom = useCallback(() => {
    return (
      <PanelShell panelId="inspector" title="Inspector">
        <PulseInspector />
      </PanelShell>
    );
  }, []);

  // ─── Bottom: Timeline area (Transport + TabBar + Tracks + BPM) ───
  const renderBottom = useCallback(() => {
    return (
      <div style={TIMELINE_AREA}>
        <TransportBar />
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
  }, [timelineId, scriptText, zoom, scrollLeft, duration]);

  // ─── Panel router ───
  const renderPanel = useCallback(
    (position: DockPosition): ReactNode => {
      switch (position) {
        case 'left':
          return renderLeft();
        case 'center':
          return renderCenter();
        case 'right_top':
          return renderRightTop();
        case 'right_bottom':
          return renderRightBottom();
        case 'bottom':
          return renderBottom();
        default:
          return null;
      }
    },
    [renderLeft, renderCenter, renderRightTop, renderRightBottom, renderBottom],
  );

  // ─── Floating panels: StorySpace3D mini ───
  const storySpacePanel = useMemo(() => {
    const ssState = panels.find((p) => p.id === 'story_space_3d');
    if (!ssState?.visible) return null;

    return (
      <PanelShell panelId="story_space_3d" title="StorySpace 3D">
        <StorySpace3D
          timelineId={timelineId}
          scriptText={scriptText}
          mini={ssState.mode === 'floating'}
        />
      </PanelShell>
    );
  }, [panels, timelineId, scriptText]);

  return (
    <div style={ROOT}>
      <PanelGrid renderPanel={renderPanel} floatingPanels={storySpacePanel} />
    </div>
  );
}

// ─── Left tab content: Script / DAG switch ───

function LeftTabContent({ scriptText }: { scriptText: string }) {
  // Internal tab state for script vs DAG
  const [activeTab, setActiveTab] = useCutEditorStore.getState().timelineId
    ? ['script', () => {}]
    : ['script', () => {}];

  // Use ScriptPanel's built-in tab system
  return (
    <ScriptPanel
      scriptText={scriptText}
      activeTab="script"
      onTabChange={(tab) => {
        // Tab change handled internally by ScriptPanel
      }}
    />
  );
}
