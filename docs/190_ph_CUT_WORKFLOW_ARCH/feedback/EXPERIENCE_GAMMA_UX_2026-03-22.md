# Gamma UX/Panel Architect — Experience Report
**Date:** 2026-03-22
**Agent:** OPUS-GAMMA (claude/cut-ux)
**Session:** Wave 5-6, 11 commits + 3 verified-done (no code needed)
**Scope:** Panel focus scoping, menus (all 8), clipboard ops, DnD zones, track icons, speed indicators, transitions, L-cut/J-cut, ruler fix, panel toggle

---

## 1. WHAT WORKED

### ACTION_SCOPE map — the single best architectural decision
Defining a `Record<CutHotkeyAction, 'global' | FocusPanelId[]>` in useCutHotkeys.ts was the cleanest way to scope 50+ hotkeys. The scope check is 4 lines in the keydown handler — reads `focusedPanel` from store, checks the map, skips if not matching. Zero refactoring of existing handlers needed. Every new action just adds one line to the map.

### Store actions as the single entry point
Every menu item calls `store.getState().action()` directly — no synthetic keyboard events, no DOM hacks. This made Cut/Copy/Paste, Lift/Extract, CloseGap, ExtendEdit, L-cut/J-cut all trivially testable and debuggable. The pattern: define interface → add default → implement action → wire to menu + hotkey. Takes ~5 minutes per action.

### Compact track headers
Reducing button size from 20x16 to 16x14 and rearranging from 2 rows of 2 to 1 row of 4 (target + lock + solo + mute) with eye icon inline with label saved ~30px vertical space. Track headers now fit even in S height (28px). Net: -15 lines of code.

### togglePanel() in useDockviewStore
Simple but critical: `getPanel(id)` → if exists, `setActive()`, if not, `addPanel()`. Solved the "closed panels can't reopen" bug in one function. Window menu went from 9 items to 16.

---

## 2. WHAT DIDN'T WORK

### MenuBar keyboard dispatch pattern (legacy)
Several menu items from other agents used `document.dispatchEvent(new KeyboardEvent(...))` to trigger actions. This is fragile — doesn't go through the hotkey system's scope check, doesn't work when focus is wrong, and creates invisible dependencies. I replaced Lift/Extract/CloseGap/ExtendEdit with direct store calls but left some legacy dispatches (Add Edit, Ripple Delete, Scene Detection) since those handlers live in CutEditorLayoutV2 and I didn't want to duplicate logic.

**Recommendation:** All menu actions should call store methods directly. Keyboard dispatch should only be for actual user keyboard input.

### Ruler label visibility
The ruler tick labels (`#888` text on `#111` background) became invisible after dockview CSS changes. Root cause unclear — I bumped colors to `#999/#666`, added explicit `fontFamily: monospace` and `zIndex: 1`. This was a band-aid. The real issue is that dockview's CSS uses `!important` on many properties, and any parent container inheriting those rules can cascade into child components.

### Reset Workspace only cleared one preset
The "Reset Workspace" menu action only removed `cut_dockview_editing` from localStorage, leaving color/audio/custom presets intact. Corrupted saved layouts (likely from panel registration changes) caused duplicate panels to appear. Fixed by clearing all 5 keys.

---

## 3. UX INSIGHTS

### Editors think in muscle memory, not menus
Panel focus scoping is not a feature — it's a prerequisite. Without it, JKL shuttle controls ALL monitors simultaneously, Delete works when the wrong panel is focused, and I/O marks go to the wrong track. The #1 feedback from Wave 3-4 was correct: "Without this, CUT feels wrong to any editor."

### Menus are documentation
Even disabled menu items with correct shortcut labels (`⌘T`, `⌘U`, `F11`) tell users "this feature exists". A menu with 4 items feels like a toy; a menu with 20 items feels like a professional tool. The Sequence menu went from 4 to 20 items — most are stubs, but the UX impression changed fundamentally.

### L-cut/J-cut is the signature of professional editing
The fact that video and audio are separate lanes makes L-cut/J-cut natural in our architecture. FCP7 requires Link/Unlink toggle to achieve this. We just trim video lanes and leave audio untouched — simpler and more intuitive. This is one of those "CUT advantage over FCP7" moments.

### Speed indicators create trust
When a clip shows "50%" in green or "200%" in orange, the editor knows exactly what's happening without clicking. Small visual cues (speed badge, transition gradient, drop zone color) compound into a feeling of control.

---

## 4. DOCKVIEW LESSONS

### CSS cascade is the #1 enemy
Dockview uses inline styles with `rgb(0, 12, 24)` (their brand blue) that override CSS variables. Our theme file has 30+ `!important` overrides. Any new dockview version can break the theme. We had to add `[style*="border-color: rgb(0, 12, 24)"]` selectors to catch inline blue.

**Lesson:** Pin dockview version. Test theme after any upgrade. Never use `*` wildcard selectors (broke drag/resize in Tauri production build — MARKER_DOCK-FIX-3).

### Panel registration must match saved layouts
When you add a new panel to `PANEL_COMPONENTS` and the user has a saved layout that doesn't include it, the panel never appears. When you remove a panel from `PANEL_COMPONENTS` and the saved layout references it, dockview throws. Always handle `try/catch` around `fromJSON()` and fall through to default layout.

### `onDidActivePanelChange` is the only reliable focus hook
Mouse events on panel wrappers work for click-to-focus, but dockview tab clicks don't fire those. `event.api.onDidActivePanelChange` catches everything — including keyboard tab navigation, programmatic `setActive()`, and tab close → next tab focus.

### `panel.group.element` is how you get DOM access
Dockview doesn't expose `api.element`. To set `data-focused` attribute for CSS, you need: `panel.group` → cast to `{ element?: HTMLElement }` → `groupEl.setAttribute(...)`. This is undocumented and may break.

---

## 5. DUPLICATE TRANSPORT INVESTIGATION

### MonitorTransport render locations (verified):
1. `SourceMonitorPanel.tsx` line 27: `<MonitorTransport feed="source" />`
2. `ProgramMonitorPanel.tsx` line 27: `<MonitorTransport feed="program" />`

**That's it.** Two instances, one per monitor. No transport in TimelinePanel, DebugShellPanel, CutEditorLayoutV2, or anywhere else.

### TransportBar.tsx (legacy):
Exists as a file (163 lines) but is **not imported anywhere**. Zero imports in the entire `client/src/` tree. It's dead code from pre-dockview era.

### Most likely cause of "duplicate transport":
**Corrupted saved dockview layout.** If the user had a saved layout from a prior session where panels were duplicated (e.g., two Source Monitor panels), `fromJSON()` would faithfully restore both — each with its own MonitorTransport. Fix: Window → Workspaces → Reset Workspace (Alt+Shift+0), which now clears all 5 localStorage keys.

### Why I didn't see it:
No access to the running browser. Code analysis shows exactly 2 MonitorTransport instances. If a third appears, it's from dockview layout restoration, not code duplication.

---

## 6. RECOMMENDATIONS FOR SUCCESSOR (Gamma-3)

### Bridge effect is next
Gamma-1 said it, I'll say it again: `addTimelinePanel()` → `createTimeline()` in instance store → backend fetch → `updateTimeline()`. Without this, multi-instance timelines show mirrored data. The snapshot/restore mechanism works for swapping, but a true second timeline panel needs its own data pipeline.

### Kill TransportBar.tsx
It's dead code. 163 lines, zero imports. Remove it. ProjectPanel.tsx references it in a comment — update that too.

### Convert remaining keyboard dispatch to store actions
Menu items that still use `document.dispatchEvent(new KeyboardEvent(...))`:
- Add Edit (⌘K) → should be `store.getState().splitAtPlayhead()`
- Ripple Delete (⌥⌫) → already has `rippleDelete` handler but menu dispatches keyboard
- Scene Detection (⌘D) → should be `store.getState().runSceneDetection()`

### CSS isolation for timeline content
Timeline ruler labels, clip names, and transport controls should never inherit dockview styles. Consider a CSS isolation boundary (e.g., `all: initial` on the timeline container, or a shadow DOM boundary — though React doesn't love that).

### Test workflow, not features
Delta's advice is gold: "open clip → set IN/OUT → press , → clip appears at correct position" is worth more than 50 unit tests on individual functions. Build Playwright specs around editing workflows.

---

## 7. PANEL FOCUS STATUS

### What's implemented:
| Component | Status |
|-----------|--------|
| `focusedPanel` in store | `'source' \| 'program' \| 'timeline' \| 'project' \| 'script' \| 'dag' \| 'effects' \| null` |
| `ACTION_SCOPE` map | 55+ actions scoped (timeline-only, monitor, global) |
| Scope guard in keydown | Reads `focusedPanel`, checks scope, skips if mismatch |
| DockviewLayout bridge | `onDidActivePanelChange` → `setFocusedPanel()` |
| Visual indicator | `data-focused` attr + CSS `outline: 1px solid #555` |
| Panel focus shortcuts | ⌘1-5 (focus source/program/timeline/project/effects) |
| Match Frame (F) | Finds clip under playhead → Source Monitor |
| Toggle Source/Program (Q) | Switches focus between monitors |

### What's NOT implemented:
- Focus ring color per panel type (all use #555 — could use panel-specific accent)
- Panel maximize (backtick key) — toggle panel fullscreen in dockview
- Focus persistence across workspace switches (focus resets on preset change)
- Focus indication in menu (Window menu doesn't show which panel is focused)

### Scope rules summary:
| Scope | Actions |
|-------|---------|
| Timeline only | Delete, Split, Razor, Trim tools (slip/slide/ripple/roll), Nudge, Edit points, L-cut/J-cut, Extend Edit, Lift/Extract, Close Gap, Transitions |
| Source + Program + Timeline | Play/Pause, JKL, Frame step, Mark I/O, Markers, Play In-to-Out |
| Global | Undo/Redo, Copy/Cut/Paste, Zoom, Import, Save, Panel focus shortcuts, View toggle, Escape |

---

*"The interface is not the product. The editor's confidence is the product. Every pixel either builds trust or erodes it."*
