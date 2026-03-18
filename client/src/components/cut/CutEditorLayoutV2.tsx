/**
 * MARKER_181.3: CutEditorLayoutV2 — IKEA-Premiere NLE layout.
 *
 * Architecture doc: PREMIERE_LAYOUT_ARCHITECTURE.md §4
 * "Free windows, not fixed zones." Default arrangement:
 *
 *   Left:          Tabbed panel (Project | Script | DAG)
 *   Center:        Source Monitor (raw clip preview + MonitorTransport)
 *   Right:         Program Monitor (full column + MonitorTransport)
 *   Bottom:        Timeline (TimelineToolbar + TabBar + Tracks + BPM)
 */
import { useCallback, useState, useMemo, type CSSProperties, type ReactNode } from 'react';
import { usePanelLayoutStore, type DockPosition } from '../../store/usePanelLayoutStore';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import PanelGrid from './PanelGrid';
import PanelShell from './PanelShell';
import VideoPreview from './VideoPreview';
import ProjectPanel from './ProjectPanel';
import ScriptPanel from './ScriptPanel';
import DAGProjectPanel from './DAGProjectPanel';
import MonitorTransport from './MonitorTransport';
import TimelineToolbar from './TimelineToolbar';
import TimelineTabBar from './TimelineTabBar';
import TimelineTrackView from './TimelineTrackView';
import BPMTrack from './BPMTrack';

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
  void panels; // keep for future panel visibility checks

  // Editor store
  const zoom = useCutEditorStore((s) => s.zoom);
  const scrollLeft = useCutEditorStore((s) => s.scrollLeft);
  const duration = useCutEditorStore((s) => s.duration);
  const timelineId = useCutEditorStore((s) => s.timelineId);
  const activeMediaPath = useCutEditorStore((s) => s.activeMediaPath);
  const thumbnails = useCutEditorStore((s) => s.thumbnails);
  const projectId = useCutEditorStore((s) => s.projectId);

  // ─── Left column: tabbed panel (Project | Script | DAG) ───
  const [leftTab, setLeftTab] = useState<'project' | 'script' | 'dag'>('project');

  const renderLeftTop = useCallback(() => {
    return (
      <PanelShell panelId="project" title="Project">
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {/* Tab bar */}
          <div style={{
            display: 'flex',
            height: 24,
            background: '#0a0a0a',
            borderBottom: '1px solid #1a1a1a',
            flexShrink: 0,
          }}>
            {(['project', 'script', 'dag'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setLeftTab(tab)}
                style={{
                  background: leftTab === tab ? '#1a1a1a' : 'none',
                  color: leftTab === tab ? '#ccc' : '#555',
                  border: 'none',
                  borderBottom: leftTab === tab ? '2px solid #4a9eff' : '2px solid transparent',
                  padding: '0 12px',
                  fontSize: 10,
                  cursor: 'pointer',
                  fontFamily: 'system-ui',
                }}
              >
                {tab === 'project' ? 'Project' : tab === 'script' ? 'Script' : 'DAG'}
              </button>
            ))}
          </div>
          {/* Tab content */}
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {leftTab === 'project' && <ProjectPanel />}
            {leftTab === 'script' && <ScriptPanel scriptText={scriptText} />}
            {leftTab === 'dag' && <DAGProjectPanel />}
          </div>
        </div>
      </PanelShell>
    );
  }, [leftTab, scriptText, projectId, thumbnails.length]);

  const renderLeftBottom = useCallback(() => null, []);

  // ─── Center: Source Monitor — raw clip preview (large area) ───
  // Phase 3 (CUT-3.2) will add feed="source" prop to VideoPreview
  const renderCenter = useCallback(() => {
    const clipName = activeMediaPath ? activeMediaPath.split('/').pop() : 'NO CLIP';
    return (
      <PanelShell panelId="source_monitor" title={`Source: ${clipName}`}>
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <VideoPreview />
          </div>
          <MonitorTransport feed="source" />
        </div>
      </PanelShell>
    );
  }, [activeMediaPath]);

  // ─── Right top: Program Monitor (ONLY ONE — timeline playback) ───
  // StorySpace removed — was blocking Program Monitor. Will be a separate panel/tab.
  const renderRightTop = useCallback(() => {
    return (
      <PanelShell panelId="program_monitor" title="Program Monitor">
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <VideoPreview />
          </div>
          <MonitorTransport feed="program" />
        </div>
      </PanelShell>
    );
  }, []);

  // ─── Right bottom: empty (Inspector moved to Source Monitor tabs, Phase 3) ───
  const renderRightBottom = useCallback(() => null, []);

  // ─── Bottom: Timeline area ───
  const renderBottom = useCallback(() => {
    return (
      <PanelShell panelId="timeline" title={`Timeline: ${timelineId} (${thumbnails.length} clips)`}>
        <div style={TIMELINE_AREA}>
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

  return (
    <div style={ROOT}>
      <PanelGrid renderPanel={renderPanel} />
    </div>
  );
}

// Inspector/Script/DAG tabs removed from layout (CUT-0.4 cleanup).
// Inspector will be a tab inside Source Monitor area (Phase 3).
// DAG Project moved to left_bottom.
