# Phase 17-M: Artifact Panel - Drag & Resize Fix

**Status:** COMPLETE
**Commits:** `45a58b9`, `36f93ec`, `45847fc`
**Date:** 2025-12-27

## Summary

Fixed critical bugs in the Artifact Panel and unified its drag/resize behavior with the Chat Panel for consistent UX.

## Issues Fixed

### 1. Artifact Panel Won't Reopen After Closing
**Problem:** After closing the artifact panel once, clicking another file would not reopen it - required hard page refresh.

**Root Cause:** `closeArtifactPanel()` set three inline styles:
```javascript
panel.style.display = 'none';
panel.style.opacity = '0';
panel.style.pointerEvents = 'none';
```

But `loadFileToArtifact()` only reset one:
```javascript
panel.style.display = 'flex';  // Missing opacity and pointerEvents reset!
```

**Fix:** Added missing resets in `loadFileToArtifact()`:
```javascript
panel.style.display = 'flex';
panel.style.opacity = '1';        // ADDED
panel.style.pointerEvents = 'auto'; // ADDED
```

### 2. JavaScript Regex Syntax Error
**Problem:** `SyntaxError: Invalid regular expression: missing /`

**Root Cause:** Python triple-quoted strings interpret `/pattern/g` regex literals differently.

**Fix:** Replaced all regex literals with `new RegExp()` constructor:
```javascript
// Before (breaks in Python template)
content.replace(/&/g, '&amp;')

// After (works correctly)
content.replace(new RegExp('&', 'g'), '&amp;')
```

### 3. JavaScript Newline Syntax Error
**Problem:** `SyntaxError: Invalid or unexpected token` at line 2261

**Root Cause:** Python interprets `'\n'` as actual newline character, outputting broken JavaScript.

**Fix:** Escaped backslashes for literal output:
```javascript
// Before (Python outputs actual newline)
content.split('\n')

// After (Python outputs \n as text)
content.split('\\n')
```

### 4. Heavy/Sluggish Drag Physics
**Problem:** Artifact panel felt "heavy" when dragging, unlike the smooth chat panel.

**Root Cause:** Original code used `transform: translate(x, y)` which doesn't integrate well with fixed positioning.

**Fix:** Rewrote to use `left/top` positioning matching the chat panel pattern.

## New Features

### VETKAArtifactPanel Controller
Created a unified controller object matching `VETKAChatPanel` architecture:

```javascript
const VETKAArtifactPanel = {
    panel: null,
    isResizing: false,
    isDragging: false,
    config: { minWidth: 300, minHeight: 200, margin: 50 },

    init()              // Initialize on DOM ready
    initResizeHandlers() // Attach to all 8 handles
    initDragHandler()   // Attach to header
    doDrag(e)           // Smooth left/top positioning
    doResize(e)         // Handle all 8 directions
    saveState()         // Persist to localStorage
    loadState()         // Restore from localStorage
    reset()             // Emergency recovery
};
```

### 8 Resize Handles
Added same resize handles as chat panel:

```html
<div class="resize-handle resize-handle-nw"></div>
<div class="resize-handle resize-handle-ne"></div>
<div class="resize-handle resize-handle-sw"></div>
<div class="resize-handle resize-handle-se"></div>
<div class="resize-edge-left"></div>
<div class="resize-edge-right"></div>
<div class="resize-edge-top"></div>
<div class="resize-edge-bottom"></div>
```

### Visual Improvements
- `backdrop-filter: blur(10px)` for modern glass effect
- Semi-transparent background `rgba(26, 26, 26, 0.95)`
- Changed from `right: 420px` to `left: 20px` positioning
- Consistent `z-index: 200` matching chat panel

### Persistence
Panel state saved to localStorage:
- `vetkaArtifactPanelLeft`
- `vetkaArtifactPanelTop`
- `vetkaArtifactPanelWidth`
- `vetkaArtifactPanelHeight`

## Files Modified

### src/visualizer/tree_renderer.py
| Section | Lines | Changes |
|---------|-------|---------|
| CSS | 289-328 | Updated positioning, added blur, transparency |
| HTML | 1606-1645 | Added 8 resize handles |
| JS loadFileToArtifact | 2255-2262 | Fixed opacity/pointerEvents reset |
| JS VETKAArtifactPanel | 2766-3011 | New controller with drag/resize |

## Commits

1. **`45a58b9`** - Fix: Replace regex literals with new RegExp() for Python compatibility
2. **`36f93ec`** - Fix: Escape newline chars in JS strings for Python template
3. **`45847fc`** - Phase 17-M: Fix artifact panel reopen + unified drag/resize

## Testing Checklist

- [x] Click file → artifact opens
- [x] Close artifact → click another file → reopens correctly
- [x] Drag by header → smooth, responsive movement
- [x] Resize from corners (NW, NE, SW, SE) → works
- [x] Resize from edges (left, right, top, bottom) → works
- [x] Edit mode → save → changes persist
- [x] Refresh page → panel position/size restored
- [x] Python syntax validation passes

## Architecture Notes

### Why Inline JavaScript (not external file)?
The `frontend/static/` directory is in `.gitignore`, so external JS files don't get deployed. All artifact panel code must be inline in `tree_renderer.py`.

### Pattern Consistency
Both panels now follow identical architecture:
```
VETKAChatPanel     → frontend/static/js/ui/chat_panel.js
VETKAArtifactPanel → inline in tree_renderer.py
```

Same methods, same localStorage keys pattern, same clamp logic.

## Console Debug Commands

```javascript
// Reset artifact panel to defaults
window.resetArtifactPanel()

// Check current state
console.log(VETKAArtifactPanel.panel.style.cssText)

// Force reopen
VETKAArtifactPanel.panel.classList.remove('hidden')
VETKAArtifactPanel.panel.style.display = 'flex'
VETKAArtifactPanel.panel.style.opacity = '1'
```
