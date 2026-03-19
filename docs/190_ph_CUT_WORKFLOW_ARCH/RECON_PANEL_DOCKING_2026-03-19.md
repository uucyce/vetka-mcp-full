# RECON: Panel Docking System — Premiere-Style Drag/Drop/Split/Tab
**Date:** 2026-03-19
**Task:** tb_1773911196_3
**Status:** APPROVED by user (2026-03-19)

---

## 1. What Premiere Does

Every panel window has **5 drop zones**: top, bottom, left, right, center (creates tab).
- Drag panel header → rearrange, dock elsewhere
- Pull divider → split into two areas
- Timeline can exist in **multiple instances**
- Other panels (Project, Inspector) = **singletons**
- Workspace presets: "Editing", "Color", "Audio" — save/restore full layout

---

## 2. What We Have Now

| Component | What it does | Gap |
|-----------|-------------|-----|
| **PanelGrid.tsx** | CSS Grid 5-col/3-row + 4 resize handles | No drag-to-dock, no drop zones |
| **usePanelLayoutStore.ts** | Zustand: dock/tab/float modes, grid sizes | `detach()` works, but no visual drop targets |
| **PanelShell.tsx** | Window wrapper: title bar drag, 8-dir resize, floating | No 5-zone drop overlay |
| **CutEditorLayoutV2.tsx** | Assembles all panels into grid | Hardcoded positions, not dynamic |

**Bottom line:** We have resize + float + tabs, but **NO drag-to-dock with visual drop zones**. Layout is static CSS grid, not a dynamic docking tree.

---

## 3. Library Comparison

| | **dockview** | **FlexLayout** | **rc-dock** | react-mosaic |
|---|---|---|---|---|
| Stars | 3,100 | 1,260 | 800 | 3,700 |
| Last update | Mar 2026 | Jan 2026 | 2025 (alpha) | 2023 (stale) |
| 5-zone drop targets | YES | YES | YES | NO (tiling only) |
| Drag headers | YES | YES | YES | Partial |
| Save/restore layout | YES (first-class) | YES (JSON) | YES | YES |
| Floating panels | YES | YES | YES | NO |
| Bundle size | 656 kB | 522 kB | 498 kB | 404 kB |
| TypeScript | YES | YES | YES | YES |
| React 18+ | YES | YES | YES | YES |
| Zero deps | YES | No | No | No |
| Notable users | IDE-style apps | Trading platforms | Ticlo | Palantir |

**Eliminated:**
- **golden-layout** — abandoned (last update 2022), React wrapper fragile
- **allotment** — split panes only, no tabs/docking
- **lumino** — not React-native (Jupyter widget toolkit)

---

## 4. Recommendation: dockview

**Why dockview over FlexLayout:**
1. **Most active** — releases in Mar 2026, responsive maintainer
2. **Zero dependencies** — no supply chain risk
3. **Best docs** — dockview.dev with live examples for every feature
4. **Floating panels** — native support (detach monitor → separate float)
5. **Layout serialization** — `toJSON()`/`fromJSON()` for workspace presets
6. **Multi-framework** — React/Vue/Angular/vanilla, future-proof

**FlexLayout** is the fallback if dockview doesn't fit — mature, React-only, battle-tested in finance.

---

## 5. Migration Plan

### Phase 1: Install + Wrapper (1 session)
- `npm install dockview`
- Create `DockviewLayout.tsx` wrapper component
- Map existing panels to dockview panel registry
- Timeline = multi-instance capable, others = singleton

### Phase 2: Replace PanelGrid (1-2 sessions)
- Replace CutEditorLayoutV2's hardcoded grid with dockview
- Each panel becomes a `DockviewPanel` with our existing content
- PanelShell.tsx title bar → dockview handles this natively
- Preserve all existing panel content components unchanged

### Phase 3: Drop Zones + Drag (automatic from dockview)
- 5-zone drop targets come free with dockview
- Tab reordering comes free
- Panel header drag-to-dock comes free

### Phase 4: Workspace Presets
- Default: current layout as "Editing" preset
- Add presets: "Color" (larger Program Monitor), "Audio" (waveforms prominent)
- `dockview.toJSON()` → save to localStorage or backend
- `dockview.fromJSON()` → restore on load

### Panel Registry

| Panel ID | Component | Multi-instance? | Default Position |
|----------|-----------|----------------|-----------------|
| project | ProjectPanel | NO | left-top tab |
| script | ScriptPanel | NO | left-top tab |
| graph | DAGProjectPanel | NO | left-top tab |
| inspector | PulseInspector | NO | left-bottom tab |
| clip | ClipInspector | NO | left-bottom tab |
| storyspace | StorySpace3D | NO | left-bottom tab |
| history | HistoryPanel | NO | left-bottom tab |
| source | VideoPreview(source) | NO | center-left |
| program | VideoPreview(program) | NO | center-right |
| timeline | TimelineTrackView | YES | bottom (full width) |

---

## 6. What We Keep

- All panel **content components** stay unchanged
- `useCutEditorStore` — untouched
- `usePanelSyncStore` — untouched
- Hotkey system — untouched
- Panel focus system (`focusedPanel`) — wire to dockview's `onDidActivePanelChange`

**What we delete:**
- `PanelGrid.tsx` — replaced by dockview
- PanelShell.tsx title bar/resize logic — dockview handles this
- `usePanelLayoutStore.ts` grid sizes — dockview manages layout tree

---

## 7. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| dockview styling doesn't match dark theme | CSS custom properties, dockview supports full theming |
| Performance with video elements in panels | dockview uses DOM recycling, same as current approach |
| Breaking existing panel content | Content components are pure React — just re-parent into dockview panels |
| Learning curve | dockview docs are excellent, live playground available |

---

## Decision Needed

1. **Approve dockview** as the docking library?
2. **Approve migration plan** (4 phases)?
3. **Priority** — do this before or after hotkey wiring?
