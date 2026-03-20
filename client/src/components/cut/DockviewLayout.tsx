/**
 * MARKER_196.2: DockviewLayout — Premiere-style dockable panel layout for CUT NLE.
 *
 * Replaces PanelGrid.tsx with full drag-to-dock, 5-zone drop targets, tab reordering,
 * floating panels, and workspace preset save/restore.
 *
 * Architecture doc: RECON_PANEL_DOCKING_2026-03-19.md §5
 * Panel registry: 10 panels, timeline = multi-instance, all others = singleton.
 * Panel wrappers: MARKER_C4 — extracted to ./panels/ with focus handling.
 *
 * @phase 196
 */
import { useCallback, useRef, useMemo } from 'react';
import {
  DockviewReact,
  type DockviewApi,
  type DockviewReadyEvent,
} from 'dockview-react';
import 'dockview-react/dist/styles/dockview.css';
import './dockview-cut-theme.css';

import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useDockviewStore } from '../../store/useDockviewStore';
import { useTimelineInstanceStore } from '../../store/useTimelineInstanceStore';

// MARKER_C4: Panel wrappers extracted to panels/ directory
import {
  SourceMonitorPanel,
  ProgramMonitorPanel,
  TimelinePanel,
  ProjectPanelDock,
  ScriptPanelDock,
  GraphPanelDock,
  InspectorPanelDock,
  ClipPanelDock,
  StorySpacePanelDock,
  HistoryPanelDock,
  AutoMontagePanelDock,
  AudioMixerPanelDock,
} from './panels';
import EffectsPanel from './EffectsPanel';

// ─── Component registry ─────────────────────────────────────────────
// Keys = component names used in addPanel({ component: 'xxx' })

const EffectsPanelDock = () => <EffectsPanel />;

const PANEL_COMPONENTS = {
  project: ProjectPanelDock,
  script: ScriptPanelDock,
  graph: GraphPanelDock,
  inspector: InspectorPanelDock,
  clip: ClipPanelDock,
  storyspace: StorySpacePanelDock,
  history: HistoryPanelDock,
  montage: AutoMontagePanelDock,
  effects: EffectsPanelDock,
  mixer: AudioMixerPanelDock,
  source: SourceMonitorPanel,
  program: ProgramMonitorPanel,
  timeline: TimelinePanel,
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
  const { saveLayout, loadLayout, activePreset, setApiRef } = useDockviewStore();

  const onReady = useCallback((event: DockviewReadyEvent) => {
    apiRef.current = event.api;
    // MARKER_C5: Expose API to store for workspace preset switching
    setApiRef(event.api);

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

    // MARKER_C14: Auto-Montage panel (Analysis tab group)
    event.api.addPanel({
      id: 'montage',
      component: 'montage',
      title: 'Montage',
      position: { referencePanel: 'inspector', direction: 'within' },
    });

    // MARKER_B9: Effects panel (Analysis tab group)
    event.api.addPanel({
      id: 'effects',
      component: 'effects',
      title: 'Effects',
      position: { referencePanel: 'inspector', direction: 'within' },
    });

    // MARKER_B13: Audio Mixer panel (Analysis tab group)
    event.api.addPanel({
      id: 'mixer',
      component: 'mixer',
      title: 'Mixer',
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
    // Dockview native tabs now visible — supports multi-instance via drag/split/tab

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
        // MARKER_C12: Detect timeline panels → setActiveTimeline
        const tlId = panel.params?.timelineId as string | undefined;
        if (tlId || panel.id === 'timeline' || panel.id.startsWith('timeline-')) {
          useCutEditorStore.getState().setFocusedPanel('timeline');
          if (tlId) {
            useTimelineInstanceStore.getState().setActiveTimeline(tlId);
          }
        } else {
          const focus = PANEL_FOCUS_MAP[panel.id];
          if (focus) {
            useCutEditorStore.getState().setFocusedPanel(focus);
          }
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
  }, [scriptText, activePreset, loadLayout, saveLayout, setApiRef]);

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
