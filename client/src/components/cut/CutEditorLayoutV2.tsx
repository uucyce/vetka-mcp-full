/**
 * MARKER_181.3: CutEditorLayoutV2 — IKEA-Premiere NLE layout.
 *
 * Architecture doc: PREMIERE_LAYOUT_ARCHITECTURE.md §4
 * "Free windows, not fixed zones." Default arrangement:
 *
 *   Left top:      Source Monitor (raw clip preview)
 *   Left bottom:   Project Panel (media bin + import)
 *   Center:        Program Monitor (timeline playback)
 *   Right top:     Program Monitor (duplicate — or empty for now)
 *   Right bottom:  Inspector + Script + DAG (tab group)
 *   Bottom:        Timeline (Transport + TabBar + Tracks + BPM)
 *   Floating:      StorySpace3D (mini, inside Program Monitor)
 */
import { useCallback, useMemo, type CSSProperties, type ReactNode } from 'react';
import { usePanelLayoutStore, type DockPosition } from '../../store/usePanelLayoutStore';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import PanelGrid from './PanelGrid';
import PanelShell from './PanelShell';
import ScriptPanel from './ScriptPanel';
import VideoPreview from './VideoPreview';
import PulseInspector from './PulseInspector';
import ProjectPanel from './ProjectPanel';
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
  const activeTabByDock = usePanelLayoutStore((s) => s.activeTabByDock);

  // Editor store
  const zoom = useCutEditorStore((s) => s.zoom);
  const scrollLeft = useCutEditorStore((s) => s.scrollLeft);
  const duration = useCutEditorStore((s) => s.duration);
  const timelineId = useCutEditorStore((s) => s.timelineId);
  const activeMediaPath = useCutEditorStore((s) => s.activeMediaPath);
  const thumbnails = useCutEditorStore((s) => s.thumbnails);
  const projectId = useCutEditorStore((s) => s.projectId);

  // ─── Left top: Source Monitor — raw clip preview ───
  const renderLeftTop = useCallback(() => {
    const clipName = activeMediaPath ? activeMediaPath.split('/').pop() : 'No clip';
    return (
      <PanelShell panelId="source_monitor" title={`Source: ${clipName}`}>
        <VideoPreview />
      </PanelShell>
    );
  }, [activeMediaPath]);

  // ─── Left bottom: Project Panel — media bin + import ───
  const renderLeftBottom = useCallback(() => {
    return (
      <PanelShell panelId="project" title={`Project: ${projectId || 'cut'} (${thumbnails.length} clips)`}>
        <ProjectPanel />
      </PanelShell>
    );
  }, [projectId, thumbnails.length]);

  // ─── Center: Program Monitor — timeline playback ───
  const renderCenter = useCallback(() => {
    return (
      <PanelShell panelId="program_monitor" title="Program Monitor">
        <VideoPreview />
      </PanelShell>
    );
  }, []);

  // ─── Right top: Program Monitor (secondary) ───
  const renderRightTop = useCallback(() => {
    return (
      <PanelShell panelId="program_monitor" title="Program Monitor">
        <VideoPreview />
      </PanelShell>
    );
  }, []);

  // ─── Right bottom: Inspector + Script + DAG tab group (MARKER_181.13) ───
  const setActiveTab = usePanelLayoutStore((s) => s.setActiveTab);
  const activeRightBottomTab = activeTabByDock['right_bottom'] || 'inspector';
  const handleTabChange = useCallback(
    (tab: string) => setActiveTab('right_bottom', tab as import('../../store/usePanelLayoutStore').PanelId),
    [setActiveTab],
  );
  const renderRightBottom = useCallback(() => {
    return (
      <PanelShell panelId="inspector" title="Inspector">
        <RightBottomTabbedPanel
          activeTab={activeRightBottomTab}
          scriptText={scriptText}
          onTabChange={handleTabChange}
        />
      </PanelShell>
    );
  }, [activeRightBottomTab, scriptText, handleTabChange]);

  // ─── Bottom: Timeline area ───
  const renderBottom = useCallback(() => {
    return (
      <PanelShell panelId="timeline" title={`Timeline: ${timelineId} (${thumbnails.length} clips)`}>
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
      </PanelShell>
    );
  }, [timelineId, scriptText, zoom, scrollLeft, duration, thumbnails.length]);

  // ─── Panel router ───
  const renderPanel = useCallback(
    (position: DockPosition): ReactNode => {
      switch (position) {
        case 'left_top':
          return renderLeftTop();
        case 'left_bottom':
          return renderLeftBottom();
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
    [renderLeftTop, renderLeftBottom, renderCenter, renderRightTop, renderRightBottom, renderBottom],
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
          mini={ssState.isMini}
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

// ─── MARKER_181.13: Right bottom tab bar + content ───

const TAB_BAR_STYLE: CSSProperties = {
  display: 'flex',
  alignItems: 'stretch',
  height: 26,
  background: '#0a0a0a',
  borderBottom: '1px solid #1a1a1a',
  flexShrink: 0,
  userSelect: 'none',
};

const TAB_ITEM_BASE: CSSProperties = {
  padding: '0 12px',
  fontSize: 11,
  fontFamily: 'system-ui',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  borderRight: '1px solid #1a1a1a',
  transition: 'background 0.1s, color 0.1s',
};

const RIGHT_BOTTOM_TABS: { id: 'inspector' | 'script' | 'dag_project'; label: string }[] = [
  { id: 'inspector', label: 'Inspector' },
  { id: 'script', label: 'Script' },
  { id: 'dag_project', label: 'DAG' },
];

function RightBottomTabbedPanel({ activeTab, scriptText, onTabChange }: {
  activeTab: string;
  scriptText: string;
  onTabChange: (tab: string) => void;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Tab bar */}
      <div style={TAB_BAR_STYLE}>
        {RIGHT_BOTTOM_TABS.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <div
              key={tab.id}
              data-testid={`cut-tab-${tab.id}`}
              onClick={() => onTabChange(tab.id)}
              style={{
                ...TAB_ITEM_BASE,
                background: isActive ? '#1a1a1a' : 'transparent',
                color: isActive ? '#fff' : '#666',
                borderBottom: isActive ? '2px solid #3b82f6' : '2px solid transparent',
                fontWeight: isActive ? 600 : 400,
              }}
            >
              {tab.label}
            </div>
          );
        })}
      </div>
      {/* Tab content */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <RightBottomTabContent activeTab={activeTab} scriptText={scriptText} />
      </div>
    </div>
  );
}

function RightBottomTabContent({ activeTab, scriptText }: { activeTab: string; scriptText: string }) {
  switch (activeTab) {
    case 'script':
      return (
        <ScriptPanel
          scriptText={scriptText}
          activeTab="script"
          onTabChange={() => {}}
        />
      );
    case 'dag_project':
      return <div style={{ color: '#666', padding: 12, fontSize: 11 }}>DAG View (coming soon)</div>;
    case 'inspector':
    default:
      return <PulseInspector />;
  }
}
