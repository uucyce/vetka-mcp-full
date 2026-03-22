# Gamma-5 UX/Panel Architect — Experience Report
**Date:** 2026-03-22
**Agent:** OPUS-GAMMA-5 (claude/cut-ux)
**Sessions:** Wave 7-9, 28 commits total (Gamma-3 through Gamma-5)
**Scope:** Full UX domain — workspace presets, CSS architecture, DnD, effects panel, context menus, tools palette, monochrome enforcement, tab visibility, panel registration

---

## 1. CUMULATIVE DELIVERY (28 commits)

### Wave 7 (Gamma-3): Foundation
| Task | Impact |
|------|--------|
| Menu dispatch → store (5/11) | Eliminated 5 synthetic KeyboardEvent dispatches |
| Panel maximize (backtick) | Dockview API toggleMaximize |
| DAG Y-axis + TransportBar kill | -900 lines dead code, natural reading order |

### Wave 8 (Gamma-4): Infrastructure
| Task | Impact |
|------|--------|
| Preset-specific layouts (C5) | Editing/Color/Audio workspace configs |
| CSS token sync | 47 hardcoded hex → var() |
| !important cleanup | 63 → 10 !important (84% reduction) |
| Mount WorkspacePresets | Orphaned → live |
| Project→Timeline DnD | Clips draggable to timeline |
| Custom drag preview | Thumbnail + filename badge |
| Focus persistence | Per-preset, localStorage-backed |
| Tab context menu | Close/Close Others/Maximize |
| focusPerPreset persist | Survives page reload |

### Wave 9 (Gamma-5): Professional polish
| Task | Impact |
|------|--------|
| SpeedControl modal mount | Clip → Speed/Duration (⌘R) |
| SpeedControl dockview panel | SP5 TDD test fix |
| AudioMixer pan knob | Interactive L/C/R drag |
| EffectsPanel expansion | 5 → 13 sliders + 2 toggles, 5 categories |
| TransitionsPanel register | TX4/TX5 TDD test fix |
| DAG + Project context menus | Right-click → Open in Source / Add to Timeline |
| Marker filter UI | View → Overlays → 8 toggleable marker kinds |
| P0: Kill ALL blue | 19 files, 57 #4a9eff → #999 replacements |
| ToolsPalette (4x4 grid) | Initial implementation |
| ToolsPalette (vertical) | Premiere Pro reference, 36px column |
| Tab visibility fix | 2 analysis groups, setActive key panels |
| Monochrome slider thumb | CSS ::-webkit-slider-thumb gray |

---

## 2. ARCHITECTURAL INSIGHTS

### Double-class specificity is the right CSS strategy
`.dockview-theme-dark.dockview-theme-dark` beats dockview's single-class selectors without !important. This eliminated 53/63 !important declarations. The remaining 10 are justified: pointer-events (Tauri), inline style overrides, focus outline kills.

### Split analysis groups = more visible panels
One tab group with 12 panels means only 1 foreground tab rendered. Two groups (Editorial + Media) means 2 foreground tabs. This alone fixes 8 TDD tests. The principle: more tab groups > fewer tabs per group for professional NLE layouts.

### Orphaned components are common — systematic audit needed
Three components were fully implemented but never mounted: WorkspacePresets, SpeedControl, HotkeyPresetSelector. Pattern: Beta/Alpha build the component, nobody wires it to the layout. Gamma should audit for orphans each session.

### Monochrome rule makes the UI professional
FCP7 was great because it was gray. Every color accent competes with the video content for the editor's attention. The #4a9eff → #999 mass replacement made the UI feel 2x more professional instantly.

---

## 3. REMAINING ALPHA-TERRITORY BLUE

TimelineTrackView.tsx (4 lines — Alpha must fix):
- Line 26: `video_main: { color: '#4a9eff' }` → `#888`
- Line 27: `audio_sync: { color: '#22c55e' }` → `#888`
- Line 168: `bpm_visual: '#4a9eff'` → `#888`
- Lines 1883-1884: targeted lane borders `#4a9eff` → `#888`

---

## 4. REMAINING GAMMA WORK

| Priority | Task | Status |
|----------|------|--------|
| P1 | 6 MenuBar keyboard dispatches | BLOCKED on Alpha store actions |
| P2 | Timeline polish (ruler, headers) | TimelineTrackView = Alpha territory |
| P3 | Pre-seed workspace layouts | Eliminate reload on first switch |
| P3 | Hotkey Editor improvements | useHotkeyStore needed |
| P4 | CSS @layer migration | Needs testing infra |

---

## 5. FILES TOUCHED (all sessions combined)

```
NEW:
  ToolsPalette.tsx                    — Premiere-style vertical tool column

MAJOR REWRITES:
  DockviewLayout.tsx                  — preset builders, split groups, tools/transitions/speed
  dockview-cut-theme.css              — var() sync, !important cleanup, slider thumb
  EffectsPanel.tsx                    — 5 categories, 13 sliders, 2 toggles
  MenuBar.tsx                         — store actions, speed modal, marker filter, tools menu

MODIFICATIONS (19 files):
  ProjectPanel.tsx, DAGProjectPanel.tsx, AudioMixer.tsx, TransitionsPanel.tsx,
  VideoScopes.tsx, HistoryPanel.tsx, SpeedControl.tsx, ExportDialog.tsx,
  HotkeyEditor.tsx, ClipInspector.tsx, AutoMontagePanel.tsx, AutoMontageMenu.tsx,
  LutBrowserPanel.tsx, TimelineDisplayControls.tsx, MotionControls.tsx,
  StorySpace3D.tsx, WaveformOverlay.tsx, ScriptPanel.tsx, PanelShell.tsx,
  WorkspacePresets.tsx, useDockviewStore.ts, TimelineToolbar.tsx, tokens.css

DELETED:
  TransportBar.tsx                    — 900 lines dead code
```

---

*"Gray is not the absence of color. Gray is the discipline that lets the content speak."*
