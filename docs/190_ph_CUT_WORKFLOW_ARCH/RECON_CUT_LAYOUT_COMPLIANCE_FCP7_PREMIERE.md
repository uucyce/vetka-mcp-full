# RECON: CUT NLE — Layout Compliance Audit vs FCP7/Premiere
**Date:** 2026-03-20
**Author:** OPUS-D (QA/Test Architect)
**Task:** tb_1773990332_34
**Type:** Research + E2E test design
**References:** FCP7 User Manual (Ch.4, Ch.10), Premiere Pro Default Shortcuts, FCP7 Shortcuts (Noble Desktop)

---

## 0. Executive Summary

CUT NLE deviates from industry NLE standards in **3 critical areas**:
1. **No Menu Bar** — both FCP7 and Premiere have full menu bars. CUT has zero.
2. **HotkeyPresetSelector in Timeline Toolbar** — should be in Edit menu (Premiere) or Tools menu (FCP7).
3. **WorkspacePresets in Timeline Toolbar** — acceptable as quick-access, but should ALSO be accessible from Window menu.

Panel layout geometry is **mostly correct** — matches Premiere's default "Editing" workspace. Minor adjustments needed.

---

## 1. Reference: Industry Standard Layouts

### 1.1 FCP7 Default Layout (from User Manual p.54, p.158)

```
┌──────────────── MENU BAR ─────────────────────────┐
│ File  Edit  View  Mark  Modify  Sequence  Effects  │
│ Tools  Window                                      │
├────────────┬──────────────┬───────────────────────┤
│            │              │                        │
│  BROWSER   │   VIEWER     │   CANVAS               │
│  (⌘4)     │   (⌘1)      │   (⌘2)                │
│  project   │   source     │   program/sequence     │
│  bins,     │   clip       │   edited result        │
│  clips     │   preview    │                        │
│            │              │                        │
├────────────┴──────────────┴───────────────────────┤
│                                                    │
│  TIMELINE (⌘3)                                    │
│  [Sequence 1] [Sequence 2] ...                     │
│  V1: ▓▓▓▓│▓▓▓▓▓│▓▓▓│▓▓▓▓▓│                       │
│  A1: ░░░░│░░░░░│░░░│░░░░░│                        │
│                                                    │
│  Tool palette (floating)  Audio meters (floating)  │
└────────────────────────────────────────────────────┘
```

**FCP7 Panel Focus Shortcuts:**
- ⌘1 = Viewer (Source)
- ⌘2 = Canvas (Program)
- ⌘3 = Timeline
- ⌘4 = Browser (Project)
- ⌥4 = Audio Meters

**FCP7 Menu Structure:**
| Menu | Key Items |
|------|-----------|
| **File** | New Project (⌥⌘N), New Sequence (⌘N), Open, Close, Save (⌘S), Save As (⌥⌘S), Import (⌘I), Export |
| **Edit** | Undo (⌘Z), Redo (⌘⇧Z), Cut/Copy/Paste, Find (⌘F), Select All (⌘A) |
| **View** | Text Size, Browser/Timeline display options |
| **Mark** | Mark In (I), Mark Out (O), Mark Clip (X), Go to In/Out (⇧I/⇧O), Clear In/Out, Add Marker (M) |
| **Modify** | Speed, Duration, levels, audio channels |
| **Sequence** | Render, Add Edit (⌘K), Trim, Transitions, Snap (N), Zoom |
| **Effects** | Video/Audio effects and transitions |
| **Tools** | **Keyboard Layout > Customize (⌥H)** |
| **Window** | **Arrange > [Standard/Audio Mixing/Color Correction/Two Up]**, show/hide panels |

**Key insight:** Keyboard customization in FCP7 is buried in `Tools > Keyboard Layout > Customize` — NOT in any toolbar.

### 1.2 Premiere Pro Default Layout

```
┌──────────────── MENU BAR ─────────────────────────┐
│ File  Edit  Clip  Sequence  Markers  Graphics      │
│ Window  Help                                       │
├──────────┬─────────────┬──────────────────────────┤
│          │             │                           │
│ PROJECT  │  SOURCE     │  PROGRAM                  │
│ (⇧1)    │  MONITOR    │  MONITOR                  │
│ Media bin │  (⇧2)      │  (⇧4)                   │
│ + Effects │             │                          │
│          │             │                           │
├──────────┴─────────────┴──────────────────────────┤
│                                                    │
│  TIMELINE (⇧3)                                    │
│  [Sequence 1] [Sequence 2] ...                     │
│  V1: ▓▓▓▓│▓▓▓▓▓│                                  │
│  A1: ░░░░│░░░░░│                                  │
│                                                    │
└────────────────────────────────────────────────────┘
```

**Premiere Menu Structure:**
| Menu | Key Items |
|------|-----------|
| **File** | New Project (⌥⌘N), New Sequence (⌘N), Open (⌘O), Save (⌘S), Import (⌘I), Export Media (⌘M) |
| **Edit** | Undo (⌘Z), Redo (⌘⇧Z), Cut/Copy/Paste, Select All (⌘A), **Keyboard Shortcuts (⌘⌥K)** |
| **Clip** | Subclip, Audio Gain (G), Speed/Duration (⌘R), Insert (,), Overwrite (.), Link (⌘L), Group (⌘G) |
| **Sequence** | Render (Enter), Match Frame (F), Add Edit (⌘K), Trim (⌘T), Transitions (⌘D), Snap (S), Zoom |
| **Markers** | Mark In/Out, Go to In/Out, Clear, Add Marker (M), Navigate markers |
| **Graphics** | Text (⌘T), shapes, arrange layers |
| **Window** | **Workspaces** (⌥⇧1-0), Show/hide panels (⇧1-9) |

**Key insight:** In Premiere, keyboard shortcuts are in `Edit > Keyboard Shortcuts (⌘⌥K)` — the standard location for preferences/settings. Workspace switching is in `Window > Workspaces`.

### 1.3 CUT Current Layout

```
┌───────────── NO MENU BAR ─────────────────────────┐
│ (nothing)                                          │
├──────────┬─────────────┬──────────────────────────┤
│          │             │                           │
│ LEFT COL │   SOURCE    │   PROGRAM                 │
│ Project  │   MONITOR   │   MONITOR                 │
│ Script   │             │                           │
│ Graph    │             │                           │
│ ──────── │             │                           │
│ Inspector│             │                           │
│ Clip     │             │                           │
│ Story3D  │             │                           │
│ History  │             │                           │
├──────────┴─────────────┴──────────────────────────┤
│ Timeline Toolbar:                                  │
│ [Snap] [Link] │ Keys: [Premiere ▾] [...] │         │
│               │ WS: [Edit|Color|Audio|Custom]      │
│                                    [───Zoom───]    │
├────────────────────────────────────────────────────┤
│  TIMELINE (full width)                             │
│  V1: ▓▓▓▓│▓▓▓▓▓│                                  │
│  A1: ░░░░│░░░░░│                                  │
│  BPM Track                                         │
└────────────────────────────────────────────────────┘
```

---

## 2. Compliance Matrix

### 2.1 Layout Geometry

| Element | Premiere | FCP7 | CUT | Status |
|---------|----------|------|-----|--------|
| Menu Bar (top of app) | File/Edit/Clip/Sequence/Markers/Graphics/Window | File/Edit/View/Mark/Modify/Sequence/Effects/Tools/Window | **MISSING** | FAIL |
| Project/Browser (left) | Left column | Left column | Left column | PASS |
| Source Monitor (center-top) | Center | Center-left | Center | PASS |
| Program Monitor (right-top) | Right | Center-right | Right | PASS |
| Timeline (bottom, full-width) | Bottom | Bottom | Bottom | PASS |
| Audio Meters | Program Monitor embedded | Floating window | Embedded in monitors | PASS (modern) |
| Tool Palette | Bottom-left of timeline | Floating | **MISSING** (hotkeys only) | ACCEPTABLE |
| Effects Browser | Left column tab | Browser tab | **MISSING** | KNOWN GAP |

### 2.2 Menu Bar Items

| Menu | Premiere | FCP7 | CUT | Status |
|------|----------|------|-----|--------|
| **File** | New/Open/Save/Import/Export | New/Open/Save/Import/Export | **NO MENU** (⌘S via hotkey, ⌘I via hotkey) | FAIL |
| **Edit** | Undo/Redo/Cut/Copy/Paste/**Keyboard Shortcuts** | Undo/Redo/Cut/Copy/Paste/Find | **NO MENU** | FAIL |
| **View** | Text Size, Zoom, Show panels | Browser/Timeline display | **NO MENU** | FAIL |
| **Clip/Mark** | Subclip, Speed, IN/OUT, Markers | Mark In/Out, Markers, Clear | **NO MENU** | FAIL |
| **Sequence** | Render, Add Edit, Snap, Zoom | Render, Add Edit, Transitions | **NO MENU** | FAIL |
| **Window** | **Workspaces**, Panel visibility | **Arrange**, Panel visibility | **NO MENU** (WorkspacePresets in toolbar) | FAIL |

### 2.3 Keyboard Shortcuts Access

| Feature | Premiere | FCP7 | CUT | Status |
|---------|----------|------|-----|--------|
| Open shortcut editor | Edit > Keyboard Shortcuts (⌘⌥K) | Tools > Keyboard Layout > Customize (⌥H) | "..." button in TimelineToolbar | **WRONG LOCATION** |
| Preset selector | Inside Keyboard Shortcuts dialog | N/A (single layout per file) | `<select>` in TimelineToolbar | **WRONG LOCATION** |
| Where it should be | Menu bar (Edit or Preferences) | Menu bar (Tools) | Should be in Edit menu or standalone modal trigger (⌘⌥K) | — |

### 2.4 Workspace Management

| Feature | Premiere | FCP7 | CUT | Status |
|---------|----------|------|-----|--------|
| Switch workspace | Window > Workspaces (⌥⇧1-0) | Window > Arrange | Buttons in TimelineToolbar | PARTIAL (works, wrong location) |
| Save workspace | Window > Workspaces > Save | Window > Arrange > Save Window Layout | Double-click "Custom" button | PARTIAL (works, non-standard) |
| Reset workspace | Window > Workspaces > Reset (⌥⇧0) | Window > Arrange > Standard (Ctrl-U) | Not exposed | MISSING |

### 2.5 Panel Focus Shortcuts

| Panel | Premiere (macOS) | FCP7 | CUT | Status |
|-------|-----------------|------|-----|--------|
| Project/Browser | ⇧1 | ⌘4 | **MISSING** | FAIL |
| Source Monitor/Viewer | ⇧2 | ⌘1 | **MISSING** | FAIL |
| Timeline | ⇧3 | ⌘3 | **MISSING** | FAIL |
| Program Monitor/Canvas | ⇧4 | ⌘2 | **MISSING** | FAIL |
| Effects/Inspector | ⇧5 | ⌘5 | **MISSING** | FAIL |
| Audio Mixer | ⇧6 | — | **MISSING** | FAIL |

---

## 3. Violations — Severity Rating

### V1: No Menu Bar [CRITICAL]

**Problem:** CUT has no menu bar at all. Both Premiere and FCP7 (and every professional NLE — DaVinci Resolve, Avid Media Composer, FCPX) have a menu bar.

**Impact:**
- Editors expect File > Save, File > Import, File > Export — muscle memory
- Edit > Undo, Edit > Keyboard Shortcuts — standard location
- Discoverability: new users can't find features
- Accessibility: screen readers rely on menu bar

**Fix scope:** Create `MenuBar.tsx` component. Mount above `DockviewLayout` in `CutEditorLayoutV2.tsx`.

**Menu structure for CUT (merged FCP7 + Premiere + CUT-specific):**

```
File    Edit    View    Mark    Clip    Sequence    Window    Help

File:
  New Project         ⌘N        (future)
  Open Project        ⌘O        (future)
  Save                ⌘S        → existing autosave
  Save As...          ⌘⇧S       (future)
  ──────────
  Import Media...     ⌘I        → existing bootstrap
  ──────────
  Export Media...     ⌘M        → existing ExportDialog
  Export > Premiere XML
  Export > FCPXML
  Export > EDL
  Export > OTIO
  ──────────
  Project Settings... ⌘;        → existing ProjectSettings modal

Edit:
  Undo                ⌘Z        → existing
  Redo                ⌘⇧Z       → existing
  ──────────
  Cut                 ⌘X        (future)
  Copy                ⌘C        (future)
  Paste               ⌘V        (future)
  ──────────
  Select All          ⌘A        → existing
  Deselect All        ⌘⇧A       (future)
  ──────────
  Keyboard Shortcuts  ⌘⌥K      → HotkeyEditor modal ← MOVE HERE

View:
  Zoom In             =          → existing
  Zoom Out            -          → existing
  Zoom to Fit         \          (future)
  ──────────
  Toggle NLE/Debug    ⌘\         → existing

Mark:
  Mark In             I          → existing
  Mark Out            O          → existing
  ──────────
  Go to In            ⇧I        → existing
  Go to Out           ⇧O        → existing
  ──────────
  Clear In            ⌥I        → existing
  Clear Out           ⌥O        → existing
  Clear In and Out    ⌥X        → existing
  ──────────
  Add Marker          M          → existing
  Go to Next Marker   ⇧M
  Go to Prev Marker   ⌘⇧M

Clip:
  Speed/Duration...   ⌘R        (future — Stream B)
  Insert              ,          → existing
  Overwrite           .          → existing
  ──────────
  Link/Unlink         ⌘L        (future)
  Group               ⌘G        (future)

Sequence:
  Add Edit            ⌘K        → existing split
  Add Edit All Tracks ⌘⇧K      (future)
  ──────────
  Ripple Delete       ⌥Delete   → existing
  ──────────
  Apply Video Trans.  ⌘D        (future — Stream B)
  ──────────
  Snap in Timeline    S          → existing
  ──────────
  Scene Detection     ⌘D        → existing

Window:
  Workspaces >
    Editing           ⌥⇧1       → existing preset
    Color             ⌥⇧2       → existing preset
    Audio             ⌥⇧3       → existing preset
    Custom            ⌥⇧4       → existing preset
    ──────────
    Save Workspace...
    Reset Workspace   ⌥⇧0
  ──────────
  Project Panel       ⇧1
  Source Monitor      ⇧2
  Timeline            ⇧3
  Program Monitor     ⇧4
  Inspector           ⇧5
  ──────────
  History
  Audio Mixer         (future)
  Effects             (future)

Help:
  Keyboard Shortcuts Reference
  About CUT
```

### V2: HotkeyPresetSelector in Timeline Toolbar [HIGH]

**Problem:** `HotkeyPresetSelector` (Premiere/FCP7/Custom dropdown + "..." editor button) is rendered inside `TimelineToolbar.tsx`. This is wrong:
- Premiere: keyboard shortcuts are in `Edit > Keyboard Shortcuts`
- FCP7: keyboard shortcuts are in `Tools > Keyboard Layout > Customize`
- No NLE puts a preset selector in the timeline toolbar

**Current location:**
```
TimelineToolbar.tsx → [Snap] [Link] | Keys:[Premiere ▾][...] | [WS:Edit|Color|Audio|Custom] | [Zoom]
```

**Target location:**
- Remove from `TimelineToolbar.tsx`
- Add `Edit > Keyboard Shortcuts (⌘⌥K)` to Menu Bar
- Trigger: opens `HotkeyEditor` modal (already exists)
- Preset selector moves INSIDE the `HotkeyEditor` modal (already has it as header)

### V3: WorkspacePresets Position [MEDIUM]

**Problem:** Workspace buttons in toolbar is acceptable as quick-access (DaVinci Resolve does this too with workspace tabs at the bottom). But it should ALSO be accessible from `Window > Workspaces`.

**Current:** Only in toolbar.
**Target:** Keep in toolbar (for quick access) AND add to `Window > Workspaces` submenu.

---

## 4. Panel Position Verification

### 4.1 DockviewLayout Default Positions (from code analysis)

```javascript
// DockviewLayout.tsx — default layout order:
1. project    → base panel (left column, top)
2. script     → within project (tabbed)
3. graph      → within project (tabbed)
4. inspector  → below project (analysis group)
5. clip       → within inspector (tabbed)
6. storyspace → within inspector (tabbed)
7. history    → within inspector (tabbed)
8. source     → right of project (center)
9. program    → right of source (right)
10. timeline  → below all (full width, 300px height)
```

### 4.2 Compliance Check

| Zone | Premiere Default | FCP7 Standard | CUT Default | Match? |
|------|-----------------|---------------|-------------|--------|
| **Top-Left** | Project + Media Browser | Browser | Project + Script + Graph (tabbed) | PASS (CUT has more tabs, acceptable) |
| **Bottom-Left** | Effect Controls, Effects | (same window as Browser) | Inspector + Clip + Story3D + History (tabbed) | PASS (analysis tabs = good) |
| **Center-Top** | Source Monitor | Viewer | Source Monitor | PASS |
| **Right-Top** | Program Monitor | Canvas | Program Monitor | PASS |
| **Bottom (full width)** | Timeline | Timeline | Timeline + Toolbar + BPM | PASS |
| **Left column width** | ~25% of screen | ~25% | 260px (~18% at 1440p) | NARROW — should be ~300-350px |

### 4.3 Panel Naming

| CUT Panel Name | Premiere Equivalent | FCP7 Equivalent | Match? |
|---------------|--------------------|--------------------|--------|
| Project Panel | Project Panel | Browser | PASS (Premiere naming) |
| Source Monitor | Source Monitor | Viewer | PASS |
| Program Monitor | Program Monitor | Canvas | PASS |
| Timeline | Timeline | Timeline | PASS |
| Script Panel | — (no equivalent) | — | N/A (CUT-specific) |
| Graph/DAG | — (no equivalent) | — | N/A (CUT-specific) |
| Inspector | Effect Controls | — | PASS (Premiere naming) |
| Clip Inspector | — | — | N/A (CUT-specific) |
| History | History | — | PASS (Premiere naming) |

---

## 5. Timeline Toolbar Audit

### 5.1 Current Contents

```
TimelineToolbar.tsx (24px height):
[Snap toggle] [Linked Selection] | [Keys: Premiere ▾] [...] | [WS: Edit|Color|Audio|Custom] | ←spacer→ [Zoom slider]
```

### 5.2 What Should Be in Timeline Toolbar (industry standard)

**Premiere Timeline Panel Toolbar:**
- Snap toggle (S)
- Linked Selection toggle
- Track targeting buttons (V1, V2, A1, A2...)
- Insert/Overwrite buttons
- Zoom slider

**FCP7 Timeline:**
- Snapping toggle
- Linking toggle
- Track visibility controls
- Zoom slider

### 5.3 What Should NOT Be in Timeline Toolbar

| Item | Current | Should Be | Action |
|------|---------|-----------|--------|
| HotkeyPresetSelector | In toolbar | Edit > Keyboard Shortcuts (⌘⌥K) | **REMOVE from toolbar** |
| WorkspacePresets | In toolbar | Keep in toolbar + add to Window menu | **KEEP + DUPLICATE** |
| Snap toggle | In toolbar | In toolbar | Keep |
| Linked Selection | In toolbar | In toolbar | Keep |
| Zoom slider | In toolbar | In toolbar | Keep |

---

## 6. Fix Tasks

### FIX-1: Create Menu Bar Component [CRITICAL]

**Title:** CUT-LAYOUT-1: Add MenuBar component (File/Edit/View/Mark/Clip/Sequence/Window)
**Stream:** Gamma (UX)
**Priority:** 1-CRITICAL
**Complexity:** high

**Scope:**
1. Create `client/src/components/cut/MenuBar.tsx`
2. Mount in `CutEditorLayoutV2.tsx` above `DockviewLayout`
3. Implement menus: File, Edit, View, Mark, Clip, Sequence, Window, Help
4. Wire existing actions: Save (⌘S), Import (⌘I), Export (⌘M), Undo/Redo, Split (⌘K), Snap (S)
5. Add `Edit > Keyboard Shortcuts (⌘⌥K)` — opens HotkeyEditor modal
6. Add `Window > Workspaces > [Editing/Color/Audio/Custom]`
7. Add `Window > [Project ⇧1/Source ⇧2/Timeline ⇧3/Program ⇧4/Inspector ⇧5]`
8. Dark theme matching dockview-cut-theme.css (bg: #0a0a0a, text: #ccc)
9. Height: 22-26px (standard macOS electron menu bar height)

**Acceptance criteria:**
- Menu bar renders above dockview
- All menus open on click, close on outside click or Esc
- Keyboard shortcut labels shown next to each action
- Disabled items grayed out (e.g., Save As when no project)
- `⌘⌥K` opens HotkeyEditor from anywhere

**Allowed paths:**
```
client/src/components/cut/MenuBar.tsx              ← NEW
client/src/components/cut/CutEditorLayoutV2.tsx    ← mount MenuBar
```

### FIX-2: Remove HotkeyPresetSelector from Timeline Toolbar [HIGH]

**Title:** CUT-LAYOUT-2: Move HotkeyPresetSelector from toolbar to Edit menu
**Stream:** Gamma (UX)
**Priority:** 2-HIGH
**Complexity:** low
**Depends on:** FIX-1 (Menu Bar must exist first)

**Scope:**
1. Remove `<HotkeyPresetSelector />` from `TimelineToolbar.tsx`
2. Remove separator before it
3. `Edit > Keyboard Shortcuts (⌘⌥K)` in MenuBar opens HotkeyEditor modal
4. HotkeyEditor modal already has preset selector in its header — no change needed there
5. Register `⌘⌥K` global hotkey in `CutEditorLayoutV2.tsx`

**Acceptance criteria:**
- No preset selector visible in TimelineToolbar
- `⌘⌥K` opens HotkeyEditor modal
- Preset switching works inside HotkeyEditor

**Allowed paths:**
```
client/src/components/cut/TimelineToolbar.tsx      ← remove HotkeyPresetSelector
client/src/components/cut/CutEditorLayoutV2.tsx    ← add ⌘⌥K handler
client/src/components/cut/MenuBar.tsx              ← Edit > Keyboard Shortcuts
```

### FIX-3: Add Panel Focus Shortcuts [HIGH]

**Title:** CUT-LAYOUT-3: Implement panel focus shortcuts (⇧1-5)
**Stream:** Alpha (Engine)
**Priority:** 2-HIGH
**Complexity:** low

**Scope:**
1. In `CutEditorLayoutV2.tsx` hotkey handlers, add:
   - `⇧1` → `setFocusedPanel('project')` + activate dockview panel
   - `⇧2` → `setFocusedPanel('source')` + activate dockview panel
   - `⇧3` → `setFocusedPanel('timeline')` + activate dockview panel
   - `⇧4` → `setFocusedPanel('program')` + activate dockview panel
   - `⇧5` → `setFocusedPanel('inspector')` + activate dockview panel
2. Add to HotkeyEditor action list
3. Add to MenuBar: `Window > [Panel names with shortcuts]`

**Acceptance criteria:**
- ⇧1 focuses Project panel (visible highlight border)
- ⇧2 focuses Source Monitor
- ⇧3 focuses Timeline
- ⇧4 focuses Program Monitor
- ⇧5 focuses Inspector
- Focused panel has #4A9EFF border

**Allowed paths:**
```
client/src/components/cut/CutEditorLayoutV2.tsx    ← hotkey handlers
client/src/hooks/useCutHotkeys.ts                  ← add focus actions
```

### FIX-4: Widen Left Column Default [LOW]

**Title:** CUT-LAYOUT-4: Increase left column default width 260px → 320px
**Stream:** Gamma (UX)
**Priority:** 3-MEDIUM
**Complexity:** low

**Scope:**
1. In `DockviewLayout.tsx`, change left column initial size from 260px to 320px
2. This matches ~22% screen width at 1440p (Premiere uses ~25%)

**Allowed paths:**
```
client/src/components/cut/DockviewLayout.tsx       ← size change
```

---

## 7. E2E Test Specifications (for QA-agent)

These tests should be run once FIX-1 through FIX-3 are implemented.

### T1: Menu Bar Presence

```
Test: Menu bar exists above dockview
Steps:
  1. navigate_page → http://localhost:3009/cut
  2. wait_for → page loaded
  3. evaluate_script → document.querySelector('[data-testid="cut-menu-bar"]') !== null
  4. take_screenshot → "menu_bar_presence.png"
Assert:
  - Menu bar element exists
  - Menu bar is first child of root container
  - Menu items visible: File, Edit, View, Mark, Clip, Sequence, Window, Help
```

### T2: Menu Bar Structure

```
Test: Each menu opens and shows correct items
Steps:
  For each menu in [File, Edit, View, Mark, Clip, Sequence, Window, Help]:
    1. click → menu label
    2. take_snapshot → verify dropdown rendered
    3. evaluate_script → count menu items
    4. take_screenshot → "{menu}_open.png"
    5. press_key → Escape (close menu)
Assert:
  - File menu contains: Save, Import, Export
  - Edit menu contains: Undo, Redo, Keyboard Shortcuts
  - Window menu contains: Workspaces submenu, panel list with ⇧1-5
```

### T3: Keyboard Shortcuts Dialog Access

```
Test: ⌘⌥K opens HotkeyEditor from anywhere
Steps:
  1. navigate_page → http://localhost:3009/cut
  2. press_key → Cmd+Alt+K
  3. wait_for → HotkeyEditor modal visible
  4. evaluate_script → document.querySelector('[data-testid="cut-hotkey-editor"]') !== null
  5. take_screenshot → "hotkey_editor_from_shortcut.png"
Assert:
  - HotkeyEditor modal opens
  - Preset selector visible inside modal (not in toolbar)
```

### T4: HotkeyPresetSelector NOT in Toolbar

```
Test: Timeline toolbar does NOT contain hotkey preset selector
Steps:
  1. navigate_page → http://localhost:3009/cut
  2. evaluate_script →
     const toolbar = document.querySelector('[data-testid="cut-timeline-toolbar"]');
     const selects = toolbar ? toolbar.querySelectorAll('select') : [];
     return selects.length;
Assert:
  - No <select> elements in timeline toolbar (zoom is an <input type="range">)
  - Or: any <select> is NOT a preset selector
```

### T5: Panel Focus Shortcuts

```
Test: ⇧1-5 switch panel focus
Steps:
  1. navigate_page → http://localhost:3009/cut
  2. For each [⇧1=project, ⇧2=source, ⇧3=timeline, ⇧4=program, ⇧5=inspector]:
     a. press_key → Shift+{N}
     b. evaluate_script → window.__CUT_STORE__.getState().focusedPanel
     c. take_screenshot → "focus_shift_{N}.png"
Assert:
  - ⇧1 → focusedPanel === 'project'
  - ⇧2 → focusedPanel === 'source'
  - ⇧3 → focusedPanel === 'timeline'
  - ⇧4 → focusedPanel === 'program'
  - Focused panel has visible highlight border
```

### T6: Panel Geometry

```
Test: Panels are in correct positions
Steps:
  1. navigate_page → http://localhost:3009/cut
  2. wait_for → timeline loaded
  3. evaluate_script →
     const panels = {};
     ['project','source','program','timeline'].forEach(id => {
       const el = document.querySelector(`[data-testid="cut-panel-${id}"]`);
       if (el) {
         const r = el.getBoundingClientRect();
         panels[id] = { left: r.left, top: r.top, width: r.width, height: r.height };
       }
     });
     return panels;
  4. take_screenshot → "panel_geometry.png"
Assert:
  - project.left < source.left < program.left (left-to-right order)
  - timeline.top > source.top (timeline below monitors)
  - timeline.width ≈ window.innerWidth (full width)
  - source.top ≈ program.top (same row)
```

### T7: Workspace Switching

```
Test: Workspace presets switch layout correctly
Steps:
  1. navigate_page → http://localhost:3009/cut
  2. take_screenshot → "workspace_editing.png" (default)
  3. click → "Color" workspace button (or Window > Workspaces > Color)
  4. wait_for → layout change
  5. take_screenshot → "workspace_color.png"
  6. click → "Editing" workspace button
  7. take_screenshot → "workspace_back_to_editing.png"
Assert:
  - Layout changes between presets
  - Switching back restores original layout
  - Panel positions match expected preset configuration
```

---

## 8. Summary of Deliverables

| # | Item | Type | Priority | Owner |
|---|------|------|----------|-------|
| FIX-1 | MenuBar component | Build task | 1-CRITICAL | Gamma |
| FIX-2 | Remove HotkeyPresetSelector from toolbar | Build task | 2-HIGH | Gamma |
| FIX-3 | Panel focus shortcuts (⇧1-5) | Build task | 2-HIGH | Alpha |
| FIX-4 | Widen left column 260→320px | Build task | 3-MEDIUM | Gamma |
| T1-T7 | E2E layout compliance tests | Test specs | After FIX-1-3 | QA-agent |

---

*End of RECON. This document establishes the NLE layout standard that CUT must meet.*
