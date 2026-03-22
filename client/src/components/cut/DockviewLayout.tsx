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
import { useCallback, useRef, useMemo, useEffect } from 'react';
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
import VideoScopes from './VideoScopes';
import ColorCorrectionPanel from './ColorCorrectionPanel';
import LutBrowserPanel from './LutBrowserPanel';

// ─── Component registry ─────────────────────────────────────────────
// Keys = component names used in addPanel({ component: 'xxx' })

const EffectsPanelDock = () => <EffectsPanel />;
const VideoScopesPanelDock = () => <VideoScopes />;
const ColorCorrectorPanelDock = () => <ColorCorrectionPanel />;
const LutBrowserPanelDock = () => <LutBrowserPanel />;

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
  scopes: VideoScopesPanelDock,
  colorcorrector: ColorCorrectorPanelDock,
  lutbrowser: LutBrowserPanelDock,
  source: SourceMonitorPanel,
  program: ProgramMonitorPanel,
  timeline: TimelinePanel,
};

// ─── Panel ID → focusedPanel mapping ────────────────────────────────

const PANEL_FOCUS_MAP: Record<string, 'source' | 'program' | 'timeline' | 'project' | 'script' | 'dag' | 'effects'> = {
  project: 'project',
  script: 'script',
  graph: 'dag',
  source: 'source',
  program: 'program',
  timeline: 'timeline',
  effects: 'effects',
};

// ─── Main component ─────────────────────────────────────────────────

interface DockviewLayoutProps {
  scriptText?: string;
}

export default function DockviewLayout({ scriptText = '' }: DockviewLayoutProps) {
  const apiRef = useRef<DockviewApi | null>(null);
  const { saveLayout, loadLayout, activePreset, setApiRef, toggleMaximize } = useDockviewStore();

  // MARKER_W6.DEDUP: One-time cleanup of corrupt saved layouts on mount
  useEffect(() => {
    for (const preset of ['editing', 'color', 'audio', 'custom'] as const) {
      try {
        const raw = localStorage.getItem('cut_dockview_' + preset);
        if (!raw) continue;
        const json = JSON.parse(raw);
        const panels = json?.panels?.data;
        if (!Array.isArray(panels)) continue;
        const ids = panels.map((p: any) => p?.id).filter(Boolean);
        if (ids.length !== new Set(ids).size) {
          console.warn(`[CUT] Removing corrupt layout "${preset}" (duplicate panels)`);
          localStorage.removeItem('cut_dockview_' + preset);
        }
      } catch { /* ignore parse errors */ }
    }
  }, []);

  const onReady = useCallback((event: DockviewReadyEvent) => {
    apiRef.current = event.api;
    // MARKER_C5: Expose API to store for workspace preset switching
    setApiRef(event.api);

    // MARKER_W6.DEDUP: Try restoring saved layout with duplicate panel guard
    const saved = loadLayout(activePreset);
    if (saved) {
      try {
        // Validate: check for duplicate panel IDs in saved layout
        const panels = (saved as any)?.panels?.data;
        if (Array.isArray(panels)) {
          const ids = panels.map((p: any) => p?.id).filter(Boolean);
          const uniqueIds = new Set(ids);
          if (ids.length !== uniqueIds.size) {
            // Corrupt layout with duplicate panels — skip restore
            console.warn('[CUT DockviewLayout] Corrupt saved layout: duplicate panel IDs found, resetting');
            try { localStorage.removeItem('cut_dockview_' + activePreset); } catch { /* ok */ }
          } else {
            event.api.fromJSON(saved);
            return;
          }
        } else {
          event.api.fromJSON(saved);
          return;
        }
      } catch {
        // Corrupt layout — fall through to default
        console.warn('[CUT DockviewLayout] Failed to restore layout, using default');
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

    // MARKER_B19: Video Scopes panel (Analysis tab group)
    event.api.addPanel({
      id: 'scopes',
      component: 'scopes',
      title: 'Scopes',
      position: { referencePanel: 'inspector', direction: 'within' },
    });

    // MARKER_CC3WAY: Color Corrector 3-Way panel (Analysis tab group)
    event.api.addPanel({
      id: 'colorcorrector',
      component: 'colorcorrector',
      title: 'Color',
      position: { referencePanel: 'inspector', direction: 'within' },
    });

    // MARKER_B23: LUT Browser panel (Analysis tab group)
    event.api.addPanel({
      id: 'lutbrowser',
      component: 'lutbrowser',
      title: 'LUTs',
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
      // MARKER_LAYOUT-4: Widen left column 260→320px (~22% at 1440p, matches Premiere)
      try { projectPanel.api.setSize({ width: 320 }); } catch { /* ok */ }
    }
    if (sourcePanel && event.api.getPanel('program')) {
      // Source and program share center-right equally
    }
    if (timelinePanel) {
      try { timelinePanel.api.setSize({ height: 300 }); } catch { /* ok */ }
    }

    // MARKER_FOCUS: Wire panel focus to store + visual indicator
    event.api.onDidActivePanelChange((panel) => {
      if (panel) {
        // MARKER_C12: Detect timeline panels → setActiveTimeline + snapshot swap
        const tlId = panel.params?.timelineId as string | undefined;
        if (tlId || panel.id === 'timeline' || panel.id.startsWith('timeline-')) {
          useCutEditorStore.getState().setFocusedPanel('timeline');
          if (tlId) {
            const editorStore = useCutEditorStore.getState();
            if (editorStore.timelineId && editorStore.timelineId !== tlId) {
              editorStore.snapshotTimeline(editorStore.timelineId);
            }
            editorStore.restoreTimeline(tlId);
            useTimelineInstanceStore.getState().setActiveTimeline(tlId);
          }
        } else {
          const focus = PANEL_FOCUS_MAP[panel.id];
          if (focus) {
            useCutEditorStore.getState().setFocusedPanel(focus);
          }
        }

        // MARKER_FOCUS: Visual focus indicator — set data-focused on active group
        try {
          const container = document.querySelector('.dockview-theme-dark');
          if (container) {
            container.querySelectorAll('.dv-groupview[data-focused]').forEach((el: Element) => el.removeAttribute('data-focused'));
            // Navigate from panel's group to DOM element
            const group = panel.group;
            if (group) {
              const groupEl = (group as unknown as { element?: HTMLElement }).element;
              if (groupEl) groupEl.setAttribute('data-focused', 'true');
            }
          }
        } catch { /* visual indicator is non-critical */ }
      }
    });

    // MARKER_W6.DEDUP: Auto-save layout on changes (with dedup guard)
    event.api.onDidLayoutChange(() => {
      if (apiRef.current) {
        const json = apiRef.current.toJSON();
        // Validate before saving: no duplicate panel IDs
        const panels = (json as any)?.panels?.data;
        if (Array.isArray(panels)) {
          const ids = panels.map((p: any) => p?.id).filter(Boolean);
          const uniqueIds = new Set(ids);
          if (ids.length !== uniqueIds.size) {
            console.warn('[CUT DockviewLayout] Refusing to save layout with duplicate panels');
            return; // Don't save corrupt state
          }
        }
        saveLayout(activePreset, json);
      }
    });
  }, [scriptText, activePreset, loadLayout, saveLayout, setApiRef]);

  // MARKER_GAMMA-3: Backtick key → toggle maximize active panel (Premiere/FCP7 style)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '`' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        // Don't intercept if user is typing in an input/textarea
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable) return;
        e.preventDefault();
        toggleMaximize();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [toggleMaximize]);

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
