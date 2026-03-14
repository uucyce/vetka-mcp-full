/**
 * MARKER_180.1: Panel Layout Store — Swedish wardrobe architecture.
 * Every panel can be docked, tabbed inside another panel, or floating.
 * Layout persists per project via layout_state.json.
 *
 * Architecture doc: VETKA_CUT_Interface_Architecture_v1.docx §1, §3, §10
 */
import { create } from 'zustand';

// ─── Panel IDs — the 7 core panels from Architecture doc §2 ───
export type PanelId =
  | 'script'
  | 'dag_project'
  | 'program_monitor'
  | 'source_monitor'
  | 'timeline'
  | 'story_space_3d'
  | 'effects'
  | 'inspector'; // inspector lives under source_monitor but is a separate panel

export type PanelMode = 'docked' | 'tab' | 'floating';

// ─── Dock positions in the CSS Grid (§3 default layout) ───
export type DockPosition =
  | 'left'          // 220px column (Script / DAG project)
  | 'center'        // flex column (Program monitor)
  | 'right_top'     // 280px column top (Source monitor)
  | 'right_bottom'  // 280px column bottom (Inspector)
  | 'bottom';       // full-width strip (Timeline)

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

// ─── Default layout from Architecture doc §3 ───
const DEFAULT_PANELS: PanelState[] = [
  {
    id: 'script',
    mode: 'tab',
    visible: true,
    dockPosition: 'left',
    tabParentId: null,
    tabOrder: 0,
    floatGeometry: null,
    isMini: false,
    miniParentId: null,
  },
  {
    id: 'dag_project',
    mode: 'tab',
    visible: true,
    dockPosition: 'left',
    tabParentId: null,
    tabOrder: 1,
    floatGeometry: null,
    isMini: false,
    miniParentId: null,
  },
  {
    id: 'program_monitor',
    mode: 'docked',
    visible: true,
    dockPosition: 'center',
    tabParentId: null,
    tabOrder: 0,
    floatGeometry: null,
    isMini: false,
    miniParentId: null,
  },
  {
    id: 'source_monitor',
    mode: 'docked',
    visible: true,
    dockPosition: 'right_top',
    tabParentId: null,
    tabOrder: 0,
    floatGeometry: null,
    isMini: false,
    miniParentId: null,
  },
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
  {
    id: 'story_space_3d',
    mode: 'floating',
    visible: true,
    dockPosition: null,
    tabParentId: null,
    tabOrder: 0,
    floatGeometry: { x: -128, y: -88, width: 120, height: 80 }, // bottom-right of program monitor (relative)
    isMini: true,
    miniParentId: 'program_monitor',
  },
  {
    id: 'effects',
    mode: 'docked',
    visible: false, // hidden by default, user opens when needed
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
  leftWidth: number;    // default 220px
  rightWidth: number;   // default 280px
  bottomHeight: number; // default 180px
  rightSplit: number;   // 0-1, default 0.5 (50/50 split between source_monitor and inspector)
};

const DEFAULT_GRID: GridSizes = {
  leftWidth: 220,
  rightWidth: 280,
  bottomHeight: 180,
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
  activeTabByDock: { left: 'script' },

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
      activeTabByDock: { left: 'script' },
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
