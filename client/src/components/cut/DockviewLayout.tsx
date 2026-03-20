/**
 * MARKER_196.2: DockviewLayout — Premiere-style dockable panel layout for CUT NLE.
 *
 * Replaces PanelGrid.tsx with full drag-to-dock, 5-zone drop targets, tab reordering,
 * floating panels, and workspace preset save/restore.
 *
 * Architecture doc: RECON_PANEL_DOCKING_2026-03-19.md §5
 * Panel registry: 10 panels, timeline = multi-instance, all others = singleton.
 *
 * @phase 196
 */
import { useCallback, useRef, useMemo } from 'react';
import {
  DockviewReact,
  type DockviewApi,
  type DockviewReadyEvent,
  type IDockviewPanelProps,
} from 'dockview-react';
import 'dockview-react/dist/styles/dockview.css';
import './dockview-cut-theme.css';

import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useDockviewStore } from '../../store/useDockviewStore';

// Panel content components
import VideoPreview from './VideoPreview';
import ProjectPanel from './ProjectPanel';
import ScriptPanel from './ScriptPanel';
import DAGProjectPanel from './DAGProjectPanel';
import MonitorTransport from './MonitorTransport';
import PulseInspector from './PulseInspector';
import ClipInspector from './ClipInspector';
import StorySpace3D from './StorySpace3D';
import HistoryPanel from './HistoryPanel';
import TimelineToolbar from './TimelineToolbar';
import TimelineTabBar from './TimelineTabBar';
import TimelineTrackView from './TimelineTrackView';
import BPMTrack from './BPMTrack';

// ─── Panel wrapper components ───────────────────────────────────────
// Each wraps an existing CUT panel into a dockview-compatible component.
// dockview provides its own title bar, so we render content only.

const ProjectPanelDock = (_props: IDockviewPanelProps) => <ProjectPanel />;

const ScriptPanelDock = (props: IDockviewPanelProps) => (
  <ScriptPanel scriptText={props.params?.scriptText as string ?? ''} />
);

const GraphPanelDock = (_props: IDockviewPanelProps) => <DAGProjectPanel />;

const InspectorPanelDock = (_props: IDockviewPanelProps) => <PulseInspector />;

const ClipPanelDock = (_props: IDockviewPanelProps) => <ClipInspector />;

const StorySpacePanelDock = (_props: IDockviewPanelProps) => <StorySpace3D />;

const HistoryPanelDock = (_props: IDockviewPanelProps) => <HistoryPanel />;

const SourceMonitorDock = (_props: IDockviewPanelProps) => (
  <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
    <div style={{ flex: 1, overflow: 'hidden' }}>
      <VideoPreview feed="source" />
    </div>
    <MonitorTransport feed="source" />
  </div>
);

const ProgramMonitorDock = (_props: IDockviewPanelProps) => (
  <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
    <div style={{ flex: 1, overflow: 'hidden' }}>
      <VideoPreview feed="program" />
    </div>
    <MonitorTransport feed="program" />
  </div>
);

const TimelinePanelDock = (props: IDockviewPanelProps) => {
  const zoom = useCutEditorStore((s) => s.zoom);
  const scrollLeft = useCutEditorStore((s) => s.scrollLeft);
  const duration = useCutEditorStore((s) => s.duration);
  const timelineId = useCutEditorStore((s) => s.timelineId);
  const scriptText = (props.params?.scriptText as string) ?? '';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', overflow: 'hidden' }}>
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
};

// ─── Component registry ─────────────────────────────────────────────
// Keys = component names used in addPanel({ component: 'xxx' })

const PANEL_COMPONENTS = {
  project: ProjectPanelDock,
  script: ScriptPanelDock,
  graph: GraphPanelDock,
  inspector: InspectorPanelDock,
  clip: ClipPanelDock,
  storyspace: StorySpacePanelDock,
  history: HistoryPanelDock,
  source: SourceMonitorDock,
  program: ProgramMonitorDock,
  timeline: TimelinePanelDock,
};

// ─── Panel ID → focusedPanel mapping ────────────────────────────────

const PANEL_FOCUS_MAP: Record<string, 'source' | 'program' | 'timeline' | 'project' | 'script' | 'dag'> = {
  project: 'project',
  script: 'script',
  graph: 'dag',
  source: 'source',
  program: 'program',
  timeline: 'timeline',
};

// ─── Main component ─────────────────────────────────────────────────

interface DockviewLayoutProps {
  scriptText?: string;
}

export default function DockviewLayout({ scriptText = '' }: DockviewLayoutProps) {
  const apiRef = useRef<DockviewApi | null>(null);
  const { saveLayout, loadLayout, activePreset } = useDockviewStore();

  const onReady = useCallback((event: DockviewReadyEvent) => {
    apiRef.current = event.api;

    // Try restoring saved layout
    const saved = loadLayout(activePreset);
    if (saved) {
      try {
        event.api.fromJSON(saved);
        return;
      } catch {
        // Corrupt layout — fall through to default
      }
    }

    // ─── Default layout (matches CutEditorLayoutV2 positions) ───

    // Left column: Project (with Script and Graph as tabs)
    event.api.addPanel({
      id: 'project',
      component: 'project',
      title: 'Project',
    });

    event.api.addPanel({
      id: 'script',
      component: 'script',
      title: 'Script',
      params: { scriptText },
      position: { referencePanel: 'project', direction: 'within' },
    });

    event.api.addPanel({
      id: 'graph',
      component: 'graph',
      title: 'Graph',
      position: { referencePanel: 'project', direction: 'within' },
    });

    // Source Monitor (center)
    event.api.addPanel({
      id: 'source',
      component: 'source',
      title: 'SOURCE',
      position: { referencePanel: 'project', direction: 'right' },
    });

    // Program Monitor (right)
    event.api.addPanel({
      id: 'program',
      component: 'program',
      title: 'PROGRAM',
      position: { referencePanel: 'source', direction: 'right' },
    });

    // Analysis tabs (below Project)
    event.api.addPanel({
      id: 'inspector',
      component: 'inspector',
      title: 'Inspector',
      position: { referencePanel: 'project', direction: 'below' },
    });

    event.api.addPanel({
      id: 'clip',
      component: 'clip',
      title: 'Clip',
      position: { referencePanel: 'inspector', direction: 'within' },
    });

    event.api.addPanel({
      id: 'storyspace',
      component: 'storyspace',
      title: 'StorySpace',
      position: { referencePanel: 'inspector', direction: 'within' },
    });

    event.api.addPanel({
      id: 'history',
      component: 'history',
      title: 'History',
      position: { referencePanel: 'inspector', direction: 'within' },
    });

    // Timeline (full-width bottom)
    event.api.addPanel({
      id: 'timeline',
      component: 'timeline',
      title: 'Timeline',
      params: { scriptText },
      position: { direction: 'below' },
    });

    // Set approximate sizes to match current layout proportions
    // Left column ~260px, right monitor area fills rest
    const projectPanel = event.api.getPanel('project');
    const sourcePanel = event.api.getPanel('source');
    const timelinePanel = event.api.getPanel('timeline');

    if (projectPanel) {
      try { projectPanel.api.setSize({ width: 260 }); } catch { /* ok */ }
    }
    if (sourcePanel && event.api.getPanel('program')) {
      // Source and program share center-right equally
    }
    if (timelinePanel) {
      try { timelinePanel.api.setSize({ height: 300 }); } catch { /* ok */ }
    }

    // Wire panel focus to store
    event.api.onDidActivePanelChange((panel) => {
      if (panel) {
        const focus = PANEL_FOCUS_MAP[panel.id];
        if (focus) {
          useCutEditorStore.getState().setFocusedPanel(focus);
        }
      }
    });

    // Auto-save layout on changes
    event.api.onDidLayoutChange(() => {
      if (apiRef.current) {
        const json = apiRef.current.toJSON();
        saveLayout(activePreset, json);
      }
    });
  }, [scriptText, activePreset, loadLayout, saveLayout]);

  // Memoize components object to prevent re-renders
  const components = useMemo(() => PANEL_COMPONENTS, []);

  return (
    <DockviewReact
      className="dockview-theme-dark"
      components={components}
      onReady={onReady}
    />
  );
}
