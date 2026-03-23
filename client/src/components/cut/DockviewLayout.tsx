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
import { useCallback, useRef, useMemo, useEffect, useState } from 'react';
import {
  DockviewReact,
  type DockviewApi,
  type DockviewReadyEvent,
} from 'dockview-react';
// MARKER_GAMMA-37: dockview CSS via JS import (Vite resolves node_modules).
// Our theme CSS loads second → wins by source order. GAMMA-35 nuclear overrides.
import 'dockview-react/dist/styles/dockview.css';
import './dockview-cut-theme.css';

import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useDockviewStore } from '../../store/useDockviewStore';
import { useTimelineInstanceStore } from '../../store/useTimelineInstanceStore';
import { showHotkeyToast } from './utils/hotkeyToast';
import {
  resolveMap,
  loadPresetName,
  loadCustomOverrides,
  ALL_ACTIONS,
  ACTION_SCOPE,
  type FocusPanelId,
} from '../../hooks/useCutHotkeys';

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
  MarkerListPanel,
} from './panels';
import EffectsPanel from './EffectsPanel';
import VideoScopes from './VideoScopes';
import ColorCorrectionPanel from './ColorCorrectionPanel';
import LutBrowserPanel from './LutBrowserPanel';
import SpeedControl from './SpeedControl';
import TransitionsPanel from './TransitionsPanel';
import ToolsPalette from './ToolsPalette';
// MARKER_GAMMA-25: WorkspacePresets removed — switching via Window menu only
import StatusBar from './StatusBar';
import DropZoneOverlay from './DropZoneOverlay';
import TimelineMiniMap from './panels/TimelineMiniMap';
import { PRESET_BUILDERS, buildEditingLayout } from './presetBuilders';

// ─── Component registry ─────────────────────────────────────────────
// Keys = component names used in addPanel({ component: 'xxx' })

const EffectsPanelDock = () => <EffectsPanel />;
const VideoScopesPanelDock = () => <VideoScopes />;
const ColorCorrectorPanelDock = () => <ColorCorrectionPanel />;
const LutBrowserPanelDock = () => <LutBrowserPanel />;
const SpeedControlPanelDock = () => <div data-testid="speed-control-panel"><SpeedControl /></div>;
const TransitionsPanelDock = () => <TransitionsPanel />;
const ToolsPaletteDock = () => <ToolsPalette />;

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
  speed: SpeedControlPanelDock,
  transitions: TransitionsPanelDock,
  tools: ToolsPaletteDock,
  markers: MarkerListPanel,
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

// MARKER_GAMMA-28: Preset builders extracted to presetBuilders.ts (shared with MenuBar)

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

    // MARKER_FOCUS: Wire panel focus to store + visual indicator
    // MARKER_GAMMA-29: Wired BEFORE layout restore so it fires on all paths
    event.api.onDidActivePanelChange((panel) => {
      if (panel) {
        // MARKER_C12: Detect timeline panels → setActiveTimeline + snapshot swap
        const tlId = panel.params?.timelineId as string | undefined;
        if (tlId || panel.id === 'timeline' || panel.id.startsWith('timeline-')) {
          useCutEditorStore.getState().setFocusedPanel('timeline');
          // MARKER_GAMMA-8-FIX: Persist focus on every panel change (not just workspace switch)
          useDockviewStore.getState().saveFocusForPreset(
            useDockviewStore.getState().activePreset, 'timeline'
          );
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
            // MARKER_GAMMA-8-FIX: Persist focus on every panel change
            useDockviewStore.getState().saveFocusForPreset(
              useDockviewStore.getState().activePreset, panel.id
            );
          }
        }

        // MARKER_FOCUS: Visual focus indicator — set data-focused on active group
        try {
          const container = document.querySelector('.dockview-theme-dark');
          if (container) {
            container.querySelectorAll('.dv-groupview[data-focused]').forEach((el: Element) => el.removeAttribute('data-focused'));
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
        const panels = (json as any)?.panels?.data;
        if (Array.isArray(panels)) {
          const ids = panels.map((p: any) => p?.id).filter(Boolean);
          const uniqueIds = new Set(ids);
          if (ids.length !== uniqueIds.size) {
            console.warn('[CUT DockviewLayout] Refusing to save layout with duplicate panels');
            return;
          }
        }
        saveLayout(activePreset, json);
      }
    });

    // ─── Layout restore / build ───
    let layoutRestored = false;

    // MARKER_W6.DEDUP: Try restoring saved layout with duplicate panel guard
    const saved = loadLayout(activePreset);
    if (saved) {
      try {
        const panels = (saved as any)?.panels?.data;
        if (Array.isArray(panels)) {
          const ids = panels.map((p: any) => p?.id).filter(Boolean);
          const uniqueIds = new Set(ids);
          if (ids.length !== uniqueIds.size) {
            console.warn('[CUT DockviewLayout] Corrupt saved layout: duplicate panel IDs found, resetting');
            try { localStorage.removeItem('cut_dockview_' + activePreset); } catch { /* ok */ }
          } else {
            event.api.fromJSON(saved);
            layoutRestored = true;
          }
        } else {
          event.api.fromJSON(saved);
          layoutRestored = true;
        }
      } catch {
        console.warn('[CUT DockviewLayout] Failed to restore layout, using default');
      }
    }

    if (!layoutRestored) {
      // MARKER_C5: Build preset-specific default layout
      const builder = PRESET_BUILDERS[activePreset] || buildEditingLayout;
      builder(event.api, scriptText);

      requestAnimationFrame(() => {
        try { saveLayout(activePreset, event.api.toJSON()); } catch { /* ok */ }
      });
    }

    // MARKER_GAMMA-29 + GAMMA-8-FIX: Restore persisted focus from localStorage on load.
    // Falls back to active panel detection, then timeline default.
    requestAnimationFrame(() => {
      const savedFocus = useDockviewStore.getState().getFocusForPreset(activePreset);
      if (savedFocus) {
        // Try to activate the saved panel in dockview
        try {
          const savedPanel = event.api.getPanel(savedFocus);
          if (savedPanel) {
            savedPanel.api.setActive();
            const focus = PANEL_FOCUS_MAP[savedFocus];
            if (focus) useCutEditorStore.getState().setFocusedPanel(focus);
            return;
          }
        } catch { /* panel not found — fall through */ }
      }

      // Fallback: detect from dockview active panel
      const active = event.api.activePanel;
      if (active) {
        const tlId = active.params?.timelineId as string | undefined;
        if (tlId || active.id === 'timeline' || active.id.startsWith('timeline-')) {
          useCutEditorStore.getState().setFocusedPanel('timeline');
        } else {
          const focus = PANEL_FOCUS_MAP[active.id];
          if (focus) {
            useCutEditorStore.getState().setFocusedPanel(focus);
          }
        }
      } else {
        // Fallback: default to timeline if no active panel detected
        useCutEditorStore.getState().setFocusedPanel('timeline');
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

  // MARKER_GAMMA-R5.1: Hotkey visual feedback — show action name toast on shortcut activation
  useEffect(() => {
    // Build a lookup: action name → human label
    const actionLabels = new Map(ALL_ACTIONS.map((a) => [a.action, a.label]));

    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if ((e.target as HTMLElement)?.isContentEditable) return;

      const resolved = resolveMap(loadPresetName(), loadCustomOverrides());
      const focusedPanel = useCutEditorStore.getState().focusedPanel ?? 'timeline';

      for (const [action, parsed] of resolved) {
        const wantCmd = parsed.cmd;
        const wantCtrl = parsed.ctrl;
        const hasMetaOrCtrl = e.metaKey || e.ctrlKey;
        if (wantCmd && !hasMetaOrCtrl) continue;
        if (!wantCmd && !wantCtrl && hasMetaOrCtrl) continue;
        if (wantCtrl && !e.ctrlKey) continue;
        if (parsed.shift !== e.shiftKey) continue;
        if (parsed.alt !== e.altKey) continue;

        // Normalize key
        let eventKey = e.key.toLowerCase();
        if (e.code === 'Space') eventKey = 'space';
        else if (e.key.startsWith('Arrow')) eventKey = e.key.toLowerCase();

        if (eventKey !== parsed.key) continue;

        // Check scope
        const scope = ACTION_SCOPE[action];
        if (scope !== 'global' && !scope.includes(focusedPanel as FocusPanelId)) continue;

        const label = actionLabels.get(action);
        if (label) showHotkeyToast(label);
        return;
      }
    };

    // Use capture phase so toast fires even if handler stops propagation
    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, []);

  // MARKER_GAMMA-34: MutationObserver (GAMMA-26) removed — dead code.
  // Dockview-core JS never sets inline border-color/outline-color (verified in source).
  // CSS @layer (GAMMA-32) + ::after kill (GAMMA-FIX) + var overrides (GAMMA-31)
  // handle all colored borders at the CSS level. No JS mutation watching needed.

  // Memoize components object to prevent re-renders
  const components = useMemo(() => PANEL_COMPONENTS, []);

  // MARKER_GAMMA-15: Panel tab context menu
  const [tabMenu, setTabMenu] = useState<{ x: number; y: number; panelId: string } | null>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      // Find closest .dv-tab ancestor
      const tab = (e.target as HTMLElement).closest?.('.dv-tab') as HTMLElement | null;
      if (!tab) { setTabMenu(null); return; }
      // Dockview stores panel ID as data attribute or we read from API
      const api = apiRef.current;
      if (!api) return;
      e.preventDefault();
      // Find panel ID: walk dockview panels, match by active tab text
      const tabText = tab.textContent?.trim().toUpperCase() || '';
      let panelId = '';
      for (const p of api.panels) {
        if (p.title?.toUpperCase() === tabText || p.id.toUpperCase() === tabText) {
          panelId = p.id;
          break;
        }
      }
      if (!panelId) return;
      setTabMenu({ x: e.clientX, y: e.clientY, panelId });
    };
    const dismiss = () => setTabMenu(null);
    document.addEventListener('contextmenu', handler);
    document.addEventListener('click', dismiss);
    return () => {
      document.removeEventListener('contextmenu', handler);
      document.removeEventListener('click', dismiss);
    };
  }, []);

  const handleTabMenuAction = useCallback((action: string) => {
    const api = apiRef.current;
    if (!api || !tabMenu) return;
    const panel = api.getPanel(tabMenu.panelId);
    if (!panel) { setTabMenu(null); return; }
    switch (action) {
      case 'close':
        api.removePanel(panel);
        break;
      case 'close-others': {
        const group = panel.group;
        if (group) {
          const others = api.panels.filter((p) => p.group === group && p.id !== tabMenu.panelId);
          others.forEach((p) => { try { api.removePanel(p); } catch { /* ok */ } });
        }
        break;
      }
      case 'close-all': {
        const group = panel.group;
        if (group) {
          const all = api.panels.filter((p) => p.group === group);
          all.forEach((p) => { try { api.removePanel(p); } catch { /* ok */ } });
        }
        break;
      }
      case 'float':
        // MARKER_GAMMA-R9: Float panel into a floating group
        try {
          (api as any).addFloatingGroup?.(panel, {
            x: tabMenu.x, y: tabMenu.y, width: 400, height: 300,
          });
        } catch { /* floating API may not be available */ }
        break;
      case 'maximize':
        toggleMaximize();
        break;
    }
    setTabMenu(null);
  }, [tabMenu, toggleMaximize]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%' }}>
      {/* MARKER_GAMMA-25: WorkspacePresets removed from top bar (FCP7: Window menu only) */}
      <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
        <DockviewReact
          className="dockview-theme-dark"
          components={components}
          onReady={onReady}
        />
        {/* MARKER_GAMMA-R4.3: Drop zone overlay for media drag */}
        <DropZoneOverlay />
        {/* MARKER_GAMMA-15: Tab context menu */}
        {tabMenu && (
          <div
            style={{
              position: 'fixed',
              top: tabMenu.y,
              left: tabMenu.x,
              background: '#0b0b0b',
              border: '1px solid #333',
              borderRadius: 4,
              padding: '3px 0',
              zIndex: 10000,
              minWidth: 140,
              fontSize: 11,
              fontFamily: 'system-ui, -apple-system, sans-serif',
              color: '#ccc',
              boxShadow: '0 4px 12px rgba(0,0,0,0.6)',
            }}
          >
            {[
              { label: 'Close Panel', action: 'close' },
              { label: 'Close Others in Group', action: 'close-others' },
              { label: 'Close All in Group', action: 'close-all' },
              { separator: true },
              { label: 'Float Panel', action: 'float' },
              { label: 'Maximize / Restore', action: 'maximize' },
            ].map((item, i) =>
              'separator' in item ? (
                <div key={i} style={{ height: 1, background: '#222', margin: '3px 0' }} />
              ) : (
                <div
                  key={i}
                  onClick={() => handleTabMenuAction(item.action)}
                  style={{
                    padding: '4px 12px',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = '#1a1a1a'; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  {item.label}
                </div>
              ),
            )}
          </div>
        )}
      </div>
      {/* MARKER_GAMMA-MN1: Mini timeline navigator — overview bar */}
      <TimelineMiniMap />
      {/* MARKER_GAMMA-27: StatusBar — bottom info strip */}
      <StatusBar />
    </div>
  );
}
