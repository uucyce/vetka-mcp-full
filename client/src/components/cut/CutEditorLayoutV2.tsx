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
import { useCutHotkeys, type CutHotkeyHandlers } from '../../hooks/useCutHotkeys';
import PanelGrid from './PanelGrid';
import PanelShell from './PanelShell';
import VideoPreview from './VideoPreview';
import ProjectPanel from './ProjectPanel';
import ScriptPanel from './ScriptPanel';
import DAGProjectPanel from './DAGProjectPanel';
import MonitorTransport from './MonitorTransport';
import PulseInspector from './PulseInspector';
import ClipInspector from './ClipInspector';
import StorySpace3D from './StorySpace3D';
import TimelineToolbar from './TimelineToolbar';
import TimelineTabBar from './TimelineTabBar';
import TimelineTrackView from './TimelineTrackView';
import BPMTrack from './BPMTrack';
import HistoryPanel from './HistoryPanel';
import ProjectSettings from './ProjectSettings';
import ExportDialog from './ExportDialog';

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
  const thumbnails = useCutEditorStore((s) => s.thumbnails);
  const projectId = useCutEditorStore((s) => s.projectId);
  // MARKER_W5.2: Parallel timeline state
  const parallelTimelineTabIndex = useCutEditorStore((s) => s.parallelTimelineTabIndex);
  const timelineTabs = useCutEditorStore((s) => s.timelineTabs);
  const swapParallelTimeline = useCutEditorStore((s) => s.swapParallelTimeline);

  // ─── MARKER_196.1: Hotkey handlers ───
  const hotkeyHandlers = useMemo<CutHotkeyHandlers>(() => ({
    // Playback
    playPause: () => useCutEditorStore.getState().togglePlay(),
    stop: () => { useCutEditorStore.getState().pause(); useCutEditorStore.getState().setShuttleSpeed(0); },
    shuttleBack: () => {
      const s = useCutEditorStore.getState();
      const cur = s.shuttleSpeed;
      const next = cur > 0 ? 0 : Math.max(cur - 1, -4);
      s.setShuttleSpeed(next);
    },
    shuttleForward: () => {
      const s = useCutEditorStore.getState();
      const cur = s.shuttleSpeed;
      const next = cur < 0 ? 0 : Math.min(cur + 1, 4);
      s.setShuttleSpeed(next);
    },
    frameStepBack: () => {
      const s = useCutEditorStore.getState();
      s.pause();
      s.seek(Math.max(0, s.currentTime - 1 / s.projectFramerate));
    },
    frameStepForward: () => {
      const s = useCutEditorStore.getState();
      s.pause();
      s.seek(Math.min(s.duration, s.currentTime + 1 / s.projectFramerate));
    },
    fiveFrameStepBack: () => {
      const s = useCutEditorStore.getState();
      s.pause();
      s.seek(Math.max(0, s.currentTime - 5 / s.projectFramerate));
    },
    fiveFrameStepForward: () => {
      const s = useCutEditorStore.getState();
      s.pause();
      s.seek(Math.min(s.duration, s.currentTime + 5 / s.projectFramerate));
    },
    goToStart: () => useCutEditorStore.getState().seek(0),
    goToEnd: () => { const s = useCutEditorStore.getState(); s.seek(s.duration); },

    // Marking — context-aware: source panel → source marks, else → sequence marks
    markIn: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.setSourceMarkIn(s.currentTime);
      else s.setSequenceMarkIn(s.currentTime);
    },
    markOut: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.setSourceMarkOut(s.currentTime);
      else s.setSequenceMarkOut(s.currentTime);
    },
    clearIn: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.setSourceMarkIn(null);
      else s.setSequenceMarkIn(null);
    },
    clearOut: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') s.setSourceMarkOut(null);
      else s.setSequenceMarkOut(null);
    },
    clearInOut: () => {
      const s = useCutEditorStore.getState();
      if (s.focusedPanel === 'source') { s.setSourceMarkIn(null); s.setSourceMarkOut(null); }
      else { s.setSequenceMarkIn(null); s.setSequenceMarkOut(null); }
    },
    goToIn: () => {
      const s = useCutEditorStore.getState();
      const mark = s.focusedPanel === 'source' ? s.sourceMarkIn : s.sequenceMarkIn;
      if (mark !== null) s.seek(mark);
    },
    goToOut: () => {
      const s = useCutEditorStore.getState();
      const mark = s.focusedPanel === 'source' ? s.sourceMarkOut : s.sequenceMarkOut;
      if (mark !== null) s.seek(mark);
    },

    // Editing
    selectAll: () => useCutEditorStore.getState().selectAllClips(),
    deleteClip: () => {
      const s = useCutEditorStore.getState();
      if (s.selectedClipId) {
        const newLanes = s.lanes.map((lane) => ({
          ...lane,
          clips: lane.clips.filter((c) => c.clip_id !== s.selectedClipId),
        }));
        s.setLanes(newLanes);
        s.setSelectedClip(null);
      }
    },
    splitClip: () => {
      const s = useCutEditorStore.getState();
      const t = s.currentTime;
      const newLanes = s.lanes.map((lane) => ({
        ...lane,
        clips: lane.clips.flatMap((c) => {
          if (t > c.start_sec && t < c.start_sec + c.duration_sec) {
            const leftDur = t - c.start_sec;
            const rightDur = c.duration_sec - leftDur;
            return [
              { ...c, duration_sec: leftDur },
              { ...c, clip_id: c.clip_id + '_split', start_sec: t, duration_sec: rightDur },
            ];
          }
          return [c];
        }),
      }));
      s.setLanes(newLanes);
    },

    // Tools
    razorTool: () => useCutEditorStore.getState().setActiveTool('razor'),
    selectTool: () => useCutEditorStore.getState().setActiveTool('selection'),

    // View
    zoomIn: () => { const s = useCutEditorStore.getState(); s.setZoom(Math.min(s.zoom * 1.25, 500)); },
    zoomOut: () => { const s = useCutEditorStore.getState(); s.setZoom(Math.max(s.zoom / 1.25, 10)); },
    zoomToFit: () => {
      const s = useCutEditorStore.getState();
      if (s.duration > 0) {
        // Approximate visible width (will be refined when we have actual container width)
        s.setZoom(Math.max(10, Math.min(500, (window.innerWidth - 560) / s.duration)));
        s.setScrollLeft(0);
      }
    },

    // Project
    toggleViewMode: () => {
      const s = useCutEditorStore.getState();
      s.setViewMode(s.viewMode === 'nle' ? 'debug' : 'nle');
    },
    escapeContext: () => {
      const s = useCutEditorStore.getState();
      s.clearSelection();
      s.setActiveTool('selection');
      s.setShuttleSpeed(0);
    },
  }), []);

  useCutHotkeys({ handlers: hotkeyHandlers });

  // ─── Left column: Navigation tabs (Project | Script | DAG) ───
  const [leftTab, setLeftTab] = useState<'project' | 'script' | 'dag'>('project');

  // ─── Left column bottom: Analysis tabs (Inspector | Clip | StorySpace | History) ───
  // MARKER_W0.5: Restore Analysis tab group in left_bottom
  const [analysisTab, setAnalysisTab] = useState<'inspector' | 'clip' | 'story' | 'history'>('inspector');

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

  // MARKER_W0.5: Analysis tab group — Inspector, Clip, StorySpace, History
  const renderLeftBottom = useCallback(() => {
    const tabs = [
      { id: 'inspector' as const, label: 'Inspector' },
      { id: 'clip' as const, label: 'Clip' },
      { id: 'story' as const, label: 'StorySpace' },
      { id: 'history' as const, label: 'History' },
    ];
    return (
      <PanelShell panelId="inspector" title="Analysis">
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {/* Tab bar */}
          <div style={{
            display: 'flex',
            height: 24,
            background: '#0a0a0a',
            borderBottom: '1px solid #1a1a1a',
            flexShrink: 0,
          }}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setAnalysisTab(tab.id)}
                style={{
                  background: analysisTab === tab.id ? '#1a1a1a' : 'none',
                  color: analysisTab === tab.id ? '#ccc' : '#555',
                  border: 'none',
                  borderBottom: analysisTab === tab.id ? '2px solid #4a9eff' : '2px solid transparent',
                  padding: '0 10px',
                  fontSize: 10,
                  cursor: 'pointer',
                  fontFamily: 'system-ui',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
          {/* Tab content */}
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {analysisTab === 'inspector' && <PulseInspector />}
            {analysisTab === 'clip' && <ClipInspector />}
            {analysisTab === 'story' && <StorySpace3D />}
            {analysisTab === 'history' && <HistoryPanel />}
          </div>
        </div>
      </PanelShell>
    );
  }, [analysisTab]);

  // ─── Center: Source Monitor — raw clip preview (large area) ───
  // MARKER_W1.3: feed="source" routes to sourceMediaPath
  const sourceMediaPath = useCutEditorStore((s) => s.sourceMediaPath);
  const renderCenter = useCallback(() => {
    const clipName = sourceMediaPath ? sourceMediaPath.split('/').pop() : 'NO CLIP';
    return (
      <PanelShell panelId="source_monitor" title={`SOURCE: ${clipName}`}>
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <VideoPreview feed="source" />
          </div>
          <MonitorTransport feed="source" />
        </div>
      </PanelShell>
    );
  }, [sourceMediaPath]);

  // ─── Right top: Program Monitor (ONLY ONE — timeline playback) ───
  // MARKER_W1.3: feed="program" routes to programMediaPath
  const renderRightTop = useCallback(() => {
    return (
      <PanelShell panelId="program_monitor" title="PROGRAM">
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <VideoPreview feed="program" />
          </div>
          <MonitorTransport feed="program" />
        </div>
      </PanelShell>
    );
  }, []);

  // ─── Right bottom: empty (Inspector moved to Source Monitor tabs, Phase 3) ───
  const renderRightBottom = useCallback(() => null, []);

  // ─── Bottom: Timeline area ───
  // MARKER_W5.2: Parallel timeline — when parallelTimelineTabIndex is set, render stacked dual view
  const parallelTab = parallelTimelineTabIndex !== null ? timelineTabs[parallelTimelineTabIndex] : null;

  const renderBottom = useCallback(() => {
    const isParallel = parallelTab !== null;

    return (
      <PanelShell panelId="timeline" title={timelineId}>
        <div style={TIMELINE_AREA}>
          <TimelineToolbar />
          <TimelineTabBar />
          {isParallel ? (
            /* MARKER_W5.2: Stacked dual view */
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {/* Active timeline (top) */}
              <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
                <TimelineTrackView />
              </div>
              {/* Divider with swap button */}
              <div style={{
                height: 20,
                background: '#111',
                borderTop: '1px solid #333',
                borderBottom: '1px solid #333',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                flexShrink: 0,
                fontSize: 9,
                fontFamily: 'system-ui',
                color: '#666',
                cursor: 'pointer',
                userSelect: 'none',
              }}
              onClick={swapParallelTimeline}
              title="Click to swap active timeline"
              >
                <span style={{ color: '#4a9eff' }}>{timelineId.replace(/^tl_/, '').split('_').slice(0, -1).join('_') || timelineId}</span>
                <span style={{ color: '#555' }}>&#8645;</span>
                <span style={{ color: '#888' }}>{parallelTab?.label || 'Reference'}</span>
              </div>
              {/* Reference timeline (bottom) — dimmed, click to swap */}
              <div
                style={{
                  flex: 1,
                  overflow: 'hidden',
                  position: 'relative',
                  opacity: 0.5,
                  cursor: 'pointer',
                }}
                onClick={swapParallelTimeline}
                title="Click to make this the active timeline"
              >
                <TimelineTrackView />
              </div>
            </div>
          ) : (
            /* Single timeline view */
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <TimelineTrackView />
            </div>
          )}
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
  }, [timelineId, scriptText, zoom, scrollLeft, duration, thumbnails.length, parallelTab, swapParallelTimeline]);

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
      <ProjectSettings />
      <ExportDialog />
    </div>
  );
}

// MARKER_W0.5: Analysis tabs (Inspector, Clip, StorySpace, History) restored in left_bottom.
// Navigation tabs (Project, Script, DAG) in left_top.
