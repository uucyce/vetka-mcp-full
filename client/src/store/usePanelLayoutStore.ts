/**
 * MARKER_181.3: Panel Layout Store — IKEA-Premiere architecture.
 * Free windows: dock, tab, float, mini, minimize. No fixed zones.
 * Layout persists per project via layout_state.json.
 *
 * Architecture doc: PREMIERE_LAYOUT_ARCHITECTURE.md §4
 * Default: Source Monitor (left_top), Project (left_bottom),
 *          Program Monitor (right_top), Inspector+Script+DAG tabs (right_bottom),
 *          Timeline (bottom ~35%), StorySpace 3D (mini in Program Monitor)
 */
import { create } from 'zustand';

// ─── Panel IDs — core panels (Premiere-style naming) ───
export type PanelId =
  | 'script'
  | 'dag_project'
  | 'project'           // MARKER_181.3: Project panel (media bin + import)
  | 'program_monitor'
  | 'source_monitor'
  | 'timeline'
  | 'story_space_3d'
  | 'effects'
  | 'inspector';

export type PanelMode = 'docked' | 'tab' | 'floating';

// ─── Dock positions (IKEA-Premiere: left/right split + bottom) ───
export type DockPosition =
  | 'left'          // unsplit left (backwards compat)
  | 'left_top'      // Source Monitor (default)
  | 'left_bottom'   // Project panel (default)
  | 'center'        // backwards compat
  | 'right_top'     // Program Monitor (default)
  | 'right_bottom'  // Inspector + Script/DAG tabs (default)
  | 'bottom';       // Timeline (full-width)

// ─── Floating panel geometry ───
export type FloatGeometry = {
  x: number;
  y: number;
  width: number;
  height: number;
};

// ─── Panel state ───
export type PanelState = {
  id: PanelId;
  mode: PanelMode;
  visible: boolean;
  // Docked mode
  dockPosition: DockPosition | null;
  // Tab mode — which panel hosts this as a tab
  tabParentId: PanelId | null;
  tabOrder: number;
  // Floating mode
  floatGeometry: FloatGeometry | null;
  // Mini-panel mode (e.g., StorySpace3D inside Program Monitor)
  isMini: boolean;
  miniParentId: PanelId | null;
};

// ─── Default layout: IKEA-Premiere (MARKER_181.3) ───
// Source Monitor (left_top) | Program Monitor (right_top)
// Project Panel (left_bottom) | Inspector + Script/DAG tabs (right_bottom)
// Timeline (bottom, ~35% height)
const DEFAULT_PANELS: PanelState[] = [
  // Left top: Source Monitor — raw clip preview
  {
    id: 'source_monitor',
    mode: 'docked',
    visible: true,
    dockPosition: 'left_top',
    tabParentId: null,
    tabOrder: 0,
    floatGeometry: null,
    isMini: false,
    miniParentId: null,
  },
  // Left bottom: Project panel — media bin + import
  {
    id: 'project',
    mode: 'docked',
    visible: true,
    dockPosition: 'left_bottom',
    tabParentId: null,
    tabOrder: 0,
    floatGeometry: null,
    isMini: false,
    miniParentId: null,
  },
  // Right top: Program Monitor — timeline playback
  {
    id: 'program_monitor',
    mode: 'docked',
    visible: true,
    dockPosition: 'right_top',
    tabParentId: null,
    tabOrder: 0,
    floatGeometry: null,
    isMini: false,
    miniParentId: null,
  },
  // Right bottom: Inspector (with Script and DAG as tabs)
  {
    id: 'inspector',
    mode: 'docked',
    visible: true,
    dockPosition: 'right_bottom',
    tabParentId: null,
    tabOrder: 0,
    floatGeometry: null,
    isMini: false,
    miniParentId: null,
  },
  {
    id: 'script',
    mode: 'tab',
    visible: true,
    dockPosition: 'right_bottom',
    tabParentId: null,
    tabOrder: 1,
    floatGeometry: null,
    isMini: false,
    miniParentId: null,
  },
  {
    id: 'dag_project',
    mode: 'tab',
    visible: true,
    dockPosition: 'right_bottom',
    tabParentId: null,
    tabOrder: 2,
    floatGeometry: null,
    isMini: false,
    miniParentId: null,
  },
  // Bottom: Timeline (full width, ~35% screen height)
  {
    id: 'timeline',
    mode: 'docked',
    visible: true,
    dockPosition: 'bottom',
    tabParentId: null,
    tabOrder: 0,
    floatGeometry: null,
    isMini: false,
    miniParentId: null,
  },
  // Floating mini: StorySpace 3D inside Program Monitor corner
  {
    id: 'story_space_3d',
    mode: 'floating',
    visible: true,
    dockPosition: null,
    tabParentId: null,
    tabOrder: 0,
    floatGeometry: { x: -128, y: -88, width: 120, height: 80 },
    isMini: true,
    miniParentId: 'program_monitor',
  },
  // Hidden: Effects panel (user opens when needed)
  {
    id: 'effects',
    mode: 'docked',
    visible: false,
    dockPosition: null,
    tabParentId: null,
    tabOrder: 0,
    floatGeometry: null,
    isMini: false,
    miniParentId: null,
  },
];

// ─── Grid column/row sizes (resizable) ───
export type GridSizes = {
  leftWidth: number;    // default 260px
  rightWidth: number;   // default 280px
  bottomHeight: number; // default 35vh (~35% screen height per arch doc §2.6)
  leftSplit: number;    // 0-1, default 0.5 (Source Monitor top / Project bottom)
  rightSplit: number;   // 0-1, default 0.5 (Program Monitor top / Inspector+tabs bottom)
};

const DEFAULT_GRID: GridSizes = {
  leftWidth: 260,
  rightWidth: 280,
  bottomHeight: 280,    // ~35% of 800px viewport
  leftSplit: 0.5,
  rightSplit: 0.5,
};

// ─── Store interface ───
interface PanelLayoutState {
  panels: PanelState[];
  grid: GridSizes;
  activeTabByDock: Record<string, PanelId>; // which tab is active per dock position

  // ─── Panel actions ───
  detach: (id: PanelId) => void;                           // docked/tab → floating
  dock: (id: PanelId, position: DockPosition) => void;     // floating → docked
  tabify: (id: PanelId, targetDock: DockPosition) => void; // → tab inside dock position
  togglePanel: (id: PanelId) => void;                       // show/hide
  setActiveTab: (dockPosition: string, panelId: PanelId) => void;

  // ─── Floating actions ───
  moveFloating: (id: PanelId, x: number, y: number) => void;
  resizeFloating: (id: PanelId, width: number, height: number) => void;
  toggleMini: (id: PanelId) => void; // mini ↔ full floating

  // ─── Grid resize ───
  setGridSize: (key: keyof GridSizes, value: number) => void;

  // ─── Persistence ───
  saveLayout: () => SerializedLayout;
  loadLayout: (layout: SerializedLayout) => void;
  resetLayout: () => void;

  // ─── Queries ───
  getPanelsByDock: (position: DockPosition) => PanelState[];
  getPanel: (id: PanelId) => PanelState | undefined;
  getFloatingPanels: () => PanelState[];
  getMiniPanels: (parentId: PanelId) => PanelState[];
}

export type SerializedLayout = {
  panels: PanelState[];
  grid: GridSizes;
  activeTabByDock: Record<string, PanelId>;
};

export const usePanelLayoutStore = create<PanelLayoutState>((set, get) => ({
  panels: [...DEFAULT_PANELS],
  grid: { ...DEFAULT_GRID },
  activeTabByDock: { right_bottom: 'inspector' },

  // ─── Detach: move panel to floating mode ───
  detach: (id) =>
    set((state) => ({
      panels: state.panels.map((p) =>
        p.id === id
          ? {
              ...p,
              mode: 'floating' as PanelMode,
              dockPosition: null,
              tabParentId: null,
              isMini: false,
              miniParentId: null,
              floatGeometry: p.floatGeometry ?? { x: 100, y: 100, width: 400, height: 300 },
            }
          : p
      ),
    })),

  // ─── Dock: move floating panel to a grid position ───
  dock: (id, position) =>
    set((state) => ({
      panels: state.panels.map((p) =>
        p.id === id
          ? {
              ...p,
              mode: 'docked' as PanelMode,
              dockPosition: position,
              tabParentId: null,
              floatGeometry: null,
              isMini: false,
              miniParentId: null,
            }
          : p
      ),
    })),

  // ─── Tabify: add as tab in a dock position ───
  tabify: (id, targetDock) =>
    set((state) => {
      const existingTabs = state.panels.filter(
        (p) => (p.mode === 'tab' || p.mode === 'docked') && p.dockPosition === targetDock
      );
      return {
        panels: state.panels.map((p) =>
          p.id === id
            ? {
                ...p,
                mode: 'tab' as PanelMode,
                dockPosition: targetDock,
                tabParentId: null,
                tabOrder: existingTabs.length,
                floatGeometry: null,
                isMini: false,
                miniParentId: null,
              }
            : p
        ),
      };
    }),

  // ─── Toggle visibility ───
  togglePanel: (id) =>
    set((state) => ({
      panels: state.panels.map((p) =>
        p.id === id ? { ...p, visible: !p.visible } : p
      ),
    })),

  // ─── Set active tab in a dock position ───
  setActiveTab: (dockPosition, panelId) =>
    set((state) => ({
      activeTabByDock: { ...state.activeTabByDock, [dockPosition]: panelId },
    })),

  // ─── Move floating panel ───
  moveFloating: (id, x, y) =>
    set((state) => ({
      panels: state.panels.map((p) =>
        p.id === id && p.floatGeometry
          ? { ...p, floatGeometry: { ...p.floatGeometry, x, y } }
          : p
      ),
    })),

  // ─── Resize floating panel ───
  resizeFloating: (id, width, height) =>
    set((state) => ({
      panels: state.panels.map((p) =>
        p.id === id && p.floatGeometry
          ? { ...p, floatGeometry: { ...p.floatGeometry, width, height } }
          : p
      ),
    })),

  // ─── Toggle mini ↔ full floating ───
  toggleMini: (id) =>
    set((state) => ({
      panels: state.panels.map((p) => {
        if (p.id !== id) return p;
        if (p.isMini) {
          // Expand: mini → full floating
          return {
            ...p,
            isMini: false,
            miniParentId: null,
            floatGeometry: { x: 100, y: 100, width: 480, height: 360 },
          };
        }
        // Collapse: full → mini (back to program monitor)
        return {
          ...p,
          isMini: true,
          miniParentId: 'program_monitor',
          floatGeometry: { x: -128, y: -88, width: 120, height: 80 },
        };
      }),
    })),

  // ─── Grid resize ───
  setGridSize: (key, value) =>
    set((state) => ({
      grid: { ...state.grid, [key]: value },
    })),

  // ─── Persistence ───
  saveLayout: () => {
    const { panels, grid, activeTabByDock } = get();
    return { panels, grid, activeTabByDock };
  },

  loadLayout: (layout) =>
    set({
      panels: layout.panels,
      grid: layout.grid,
      activeTabByDock: layout.activeTabByDock,
    }),

  resetLayout: () =>
    set({
      panels: [...DEFAULT_PANELS],
      grid: { ...DEFAULT_GRID },
      activeTabByDock: { right_bottom: 'inspector' },
    }),

  // ─── Queries ───
  getPanelsByDock: (position) =>
    get().panels.filter(
      (p) => p.dockPosition === position && p.visible && (p.mode === 'docked' || p.mode === 'tab')
    ),

  getPanel: (id) => get().panels.find((p) => p.id === id),

  getFloatingPanels: () =>
    get().panels.filter((p) => p.mode === 'floating' && p.visible && !p.isMini),

  getMiniPanels: (parentId) =>
    get().panels.filter((p) => p.isMini && p.miniParentId === parentId && p.visible),
}));
