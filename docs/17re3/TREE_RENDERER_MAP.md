# tree_renderer.py - File Map

**Total Lines:** 8619
**Total Functions:** ~174 JavaScript functions
**Created:** Phase 17-R Audit

## File Structure Overview

```
tree_renderer.py (8619 lines)
├── Python wrapper (lines 1-75)
│   └── TreeRenderer class - generates HTML template
│
└── HTML Template (lines 76-8619) - EMBEDDED in Python string
    ├── CSS Styles (lines 76-1320)
    │   ├── Layout styles
    │   ├── Chat panel styles
    │   ├── Artifact panel styles
    │   └── Resize handles styles (already well implemented)
    │
    ├── HTML Structure (lines 1320-1360)
    │   ├── #canvas-container
    │   ├── #chat-panel with resize handles
    │   ├── #artifact-panel
    │   └── Control buttons
    │
    └── JavaScript (lines 1360-8619) - THE PROBLEM AREA
        ├── Socket.IO Setup (1363-1380)
        ├── Data Loader (1382-1768)
        │   └── SugiyamaLayout class (1388-1726) - layout calculations
        ├── Constants & Globals (1770-1870)
        ├── Chat State (1852-1865)
        ├── Tree Manager (1866-2005)
        ├── Golden Layout (2006-2038)
        ├── Artifact Panel (2039-2287)
        ├── Artifact Drag (2288-2352)
        ├── Init Function (2353-2900)
        │   └── Mentions system (2446-2780)
        ├── Tree Building (2901-3760)
        │   ├── Utility functions
        │   ├── Branch geometry
        │   ├── Folder labels
        │   ├── LOD system
        │   ├── Camera fitting
        │   ├── Position validation
        │   └── buildTree() main function
        ├── Semantic Edges (3762-3795)
        ├── File Cards (3797-4305)
        ├── Card Drawing (3870-4260)
        ├── Tree Labels (4274-4307)
        ├── Trunk/Spine (4390-4460)
        ├── Node Markers (4461-4700)
        ├── LOD Application (4706-4770)
        ├── Canvas Events (4771-5010)
        ├── Chat History (5011-5375)
        ├── Utilities (5377-5700)
        ├── Chat Resize (5705-5905) - ALREADY FIXED with clamp!
        ├── Search Functions (5906-6100)
        ├── Sorting & Filtering (5396-5700)
        ├── Animation (5600-5700)
        ├── Mode Switching (6100-7400)
        ├── Knowledge Graph (7400-8100)
        ├── Edge Bundling (7430-7600)
        └── Tag Nodes (7700-8619)
```

## Issues Found

### 1. Duplicate Functions
| Function | Line 1 | Line 2 | Action |
|----------|--------|--------|--------|
| `escapeHtml()` | 2243 | 5315 | Remove duplicate at 2243 |

### 2. X/Y Calculations in Frontend (Minor - mostly in layout class)
Most X/Y calculations are in `SugiyamaLayout` class which is a layout engine.
These are acceptable as they're computing layout, not rendering.

Problematic ones:
- Line 3407: `50 + depth * 80` - hardcoded Y calculation
- Line 3603: `Math.cos(theta) * radius` - position calculation
- Line 5505: `20 + normalizedDate * 400` - Y calculation in sort
- Line 6670: `depth * LEVEL_HEIGHT` - hardcoded position

### 3. Resize Handlers
**STATUS: ALREADY FIXED**
- Lines 5708-5883: Full resize implementation with clamp()
- Has all 8 resize handles (4 corners + 4 edges)
- Has viewport bounds protection
- Has global mouseup handler
- Has localStorage persistence
- Has window resize protection

### 4. Position Functions (Multiple but Justified)
These are different purposes, not duplicates:
- `SugiyamaLayout._calculateCoordinates()` - layout algorithm
- `validatePositions()` - validation helper
- `storeOriginalPositions()` - caching for animations
- `restoreTreeView()` - restore from sort

### 5. Comments
- 207 single-line comments (informative, keep)
- No large commented-out code blocks found

## Recommendations

### Quick Wins (Do Now)
1. Remove duplicate `escapeHtml()` at line 2243
2. Add TODO markers for future module splitting

### Medium Term (Future Phases)
1. Extract `SugiyamaLayout` class to separate file
2. Extract chat functionality to `ui/chat_panel.js`
3. Extract artifact panel to `ui/artifact_panel.js`
4. Extract mode switching to `modes/*.js`

### Architecture Notes
The file is large but reasonably organized with section headers.
The main issue is that it's a single Python file containing an entire
JavaScript application as a template string.

## Good Patterns Found
- Section headers with `═══` separators
- Consistent function documentation
- Proper use of clamp() for bounds
- localStorage persistence for UI state
- Global mouseup handlers for drag operations

## Module Structure (Future)

```
src/frontend/
├── renderer/
│   ├── scene.js        # Three.js setup
│   ├── nodes.js        # Node/mesh creation
│   └── edges.js        # Edge rendering
│
├── ui/
│   ├── chat_panel.js   # Chat resize, drag
│   ├── artifact_panel.js
│   └── controls.js     # Buttons, sliders
│
├── modes/
│   ├── directory_mode.js
│   └── knowledge_mode.js
│
├── layout/
│   └── sugiyama.js     # SugiyamaLayout class
│
└── tree_renderer.js    # Coordinator (< 500 lines)
```
