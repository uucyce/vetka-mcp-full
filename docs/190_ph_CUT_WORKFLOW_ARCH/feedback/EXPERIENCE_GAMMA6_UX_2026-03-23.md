# Gamma-6 UX/Panel Architect — Experience Report
**Date:** 2026-03-23
**Agent:** OPUS-GAMMA-6 (claude/cut-ux)
**Commits:** 26 total
**Scope:** Full UX domain — dockview CSS, Effects Browser, Project Panel, Keyboard Shortcuts, monochrome enforcement

---

## 1. DELIVERY (26 commits)

### CSS Architecture (8 commits)
| Task | Impact |
|------|--------|
| GAMMA-26 | MutationObserver for dockview inline styles |
| GAMMA-31 | --dv-paneview-active-outline-color override |
| GAMMA-32 | @layer migration (44→0 double-class, 23→4 !important) |
| GAMMA-34 | Remove dead MutationObserver (-65 lines) |
| GAMMA-35 | Nuclear border override (all paths covered) |
| GAMMA-37 | HOTFIX — delete broken dockview-layers.css |
| GAMMA-P1 | Hardcoded hex + !important for tab backgrounds |
| GAMMA-FIX | Colored tab underlines (::after/::before kill) |

### Features (12 commits)
| Task | Impact |
|------|--------|
| GAMMA-27 | StatusBar (zoom%, fps) |
| GAMMA-28 | Workspace switch without reload + presetBuilders.ts |
| GAMMA-29 | focusedPanel default fix (hotkeys on load) |
| GAMMA-30 | StatusBar cleanup (zoom+fps only) |
| GAMMA-33 | Panel visibility fix (Transitions/Speed foreground) |
| GAMMA-36 | Effects Browser (30 effects, 4 categories, search, drag) |
| P1.1 | Project Panel bins (create/rename/delete/drag) |
| P1.2 | Project Panel column view (sortable) |
| P1.4 | Project Panel search/filter |
| P2.1a | Effects Browser double-click apply |
| P2.3 | Effects Browser favorites (localStorage) |
| P2.5 | Effects Browser recently used |

### Keyboard Shortcuts (3 commits)
| Task | Impact |
|------|--------|
| P3.1 | useHotkeyStore (Zustand reactive store) |
| P3.4 | Preset switcher (Premiere/FCP7/Custom) |
| P3.5 | Conflict resolution (Unbind Other) |
| P3.6 | Export/import JSON |

### Monochrome Enforcement (3 commits)
| Task | Impact |
|------|--------|
| GAMMA-FIX | MonitorTransport SVG icons + kill #3b82f6 |
| P4.1 | AudioMixer, LutBrowser, VideoScopes color sweep |
| P4.1b | AutoMontagePanel, SpeedControl final sweep |

---

## 2. ARCHITECTURAL INSIGHTS

### @layer was the wrong approach for Vite
CSS `@import url() layer()` is correct per spec but Vite's CSS plugin can't resolve bare module specifiers in `@import`. The approach was reverted (GAMMA-37). Source order + `!important` on critical values is the pragmatic solution. @layer remains aspirational — needs PostCSS plugin.

### Double-class selectors were never needed
After hardcoding hex values with `!important` on tab elements, all dockview CSS battles ended. The double-class `.dockview-theme-dark.dockview-theme-dark` pattern from Gamma-4/5 was over-engineering. Simple `!important` with hardcoded values is more resilient than CSS variable cascade.

### MutationObserver was built on a false premise
Dockview-core JS never sets inline border-color. The `rgb(0,12,24)` color came from CSS cascade, not JS injection. 65 lines of observer code were dead weight. Lesson: read the library source before building workarounds.

### Effects Browser needs the "apply" loop to be useful
A browsable list of effects without the ability to apply them is a stub. Double-click-to-apply (P2.1a) was the minimal viable interaction that turned the list into a tool. Drag-to-timeline is better UX but requires Alpha coordination — double-click is Gamma-solo.

### Project Panel already had good bones
The existing bins/grid/list/DAG views were solid. Adding search, column view, and user bins built on the foundation rather than replacing it. 4 features in ~200 lines total.

---

## 3. REMAINING GAMMA WORK

| Priority | Task | Status |
|----------|------|--------|
| P2 | P2.2: Drag transition → edit point | Delegated to Alpha (tb_1774236328_20) |
| P3 | P3.2: Visual keyboard layout | Deferred (high complexity, cosmetic) |
| P4 | Marker colors in ClipInspector/TranscriptOverlay | Allowed per monochrome exception |
| P4 | CamelotWheel colors | Music theory data viz — exception |
| P4 | TimelineTrackView #3b82f6 comment marker | Alpha domain |

---

## 4. FILES TOUCHED (26 commits)

```
NEW:
  StatusBar.tsx                    — zoom% + fps bottom strip
  presetBuilders.ts                — shared workspace layout builders
  useHotkeyStore.ts                — Zustand store for hotkey management
  dockview-layers.css              — @layer experiment (created + deleted)

MAJOR CHANGES:
  EffectsPanel.tsx                 — Effects Browser: 30 effects, favorites, apply, recent
  ProjectPanel.tsx                 — search, column view, user bins
  DockviewLayout.tsx               — MutationObserver, focusedPanel fix, StatusBar mount
  dockview-cut-theme.css           — @layer, nuclear overrides, tab bg fix
  HotkeyEditor.tsx                 — preset switcher, conflict resolution, export/import
  MonitorTransport.tsx             — SVG icons, kill blue

MODIFICATIONS:
  MenuBar.tsx                      — presetBuilders import, switchWorkspace fix
  TimelineToolbar.tsx              — linked selection data-testid
  AudioMixer.tsx                   — mute/solo color fix
  LutBrowserPanel.tsx              — error text color fix
  VideoScopes.tsx                  — broadcast safe + scope color fixes
  AutoMontagePanel.tsx             — active/error/success color fix
  SpeedControl.tsx                 — speed indicator color fix
  ClipInspector.tsx                — waveform/comment marker color fix
  useCutEditorStore.ts             — focusedPanel default

DELETED:
  dockview-layers.css              — broken @import layer()
```

---

## 5. COLOR VIOLATIONS KILLED (cumulative)

| File | Count | Colors Eliminated |
|------|-------|-------------------|
| MonitorTransport | 4 | #3b82f6 (×4) |
| dockview-cut-theme.css | 2 | dodgerblue, navy rgb(16,25,64) |
| ClipInspector | 2 | #3b82f6 (×2) |
| AudioMixer | 4 | #e44, #eab308 (×2 each) |
| LutBrowserPanel | 1 | #ef4444 |
| VideoScopes | 5 | #ef4444, #f59e0b, #22c55e, #553300, #664400 |
| AutoMontagePanel | 8 | #1a2a1a, #4a9, #7ecf7e (×2), #e88, #1a1111, #111a11, #2a3a2a |
| SpeedControl | 2 | #4ade80, #facc15 |
| HotkeyEditor | 3 | #1a2a1a, #7ecf7e, #e88 |
| ProjectPanel | 2 | #93c5fd, #f87171 |
| **Total** | **33** | |

---

*"Gray is not the absence of color. Gray is the discipline that lets the content speak." — Gamma-5*
*"Every panel must be functional, not a stub." — Commander*
