# Phase 17.5: Mode Toggle (Replaces Blend Slider)

**Date:** December 25, 2025
**Status:** IMPLEMENTED
**Previous Phase:** 17.4 - Angular Fan Distribution (COMPLETE)

---

## Problem Statement

Phase 17.1-17.4 used a 0-100% blend slider to transition between Directory and Knowledge modes. This caused:

1. **Coordinate system mixing** - Interpolation between two layouts created chaos
2. **Lost positions** - directoryPositions got overwritten during blending
3. **Complex stem logic** - Stems had to interpolate between folder and tag connections
4. **Confusing UX** - Users didn't understand what intermediate values meant

---

## Solution: Binary Mode Toggle

Replace the slider with two simple buttons:

```
┌─────────────────┐
│ 📁 Directory    │  ← Active (highlighted)
├─────────────────┤
│ 🧠 Knowledge    │
└─────────────────┘
```

### Key Principle: No Interpolation

- **Directory Mode**: Files under folders, stems to folders
- **Knowledge Mode**: Files in fan layout, stems to tags/chains
- **Instant switch** - No blending between modes

---

## Implementation

### HTML Changes

**Before (Slider):**
```html
<div id="semantic-blend-panel">
    <input type="range" id="semantic-blend-slider" min="0" max="100" value="0">
    <span id="semantic-blend-value">0%</span>
</div>
```

**After (Buttons):**
```html
<div id="mode-toggle-panel">
    <button id="mode-directory-btn" class="mode-btn active" onclick="switchToDirectoryMode()">
        📁 Directory
    </button>
    <button id="mode-knowledge-btn" class="mode-btn" onclick="switchToKnowledgeMode()">
        🧠 Knowledge
    </button>
</div>
```

### CSS Changes

```css
#mode-toggle-panel {
    position: fixed;
    left: 20px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    flex-direction: column;
    gap: 8px;
    z-index: 150;
    background: rgba(22, 22, 22, 0.95);
    padding: 12px;
    border-radius: 12px;
}
#mode-toggle-panel .mode-btn.active {
    background: linear-gradient(135deg, #8B4513, #9A4A8B);
    color: #fff;
}
```

### JavaScript Changes

**New State Variable:**
```javascript
let currentMode = 'directory';  // 'directory' or 'knowledge'
```

**New Functions:**

```javascript
function switchToDirectoryMode() {
    if (currentMode === 'directory') return;
    currentMode = 'directory';

    // 1. Restore file positions from directoryPositions
    // 2. Hide all tags
    // 3. Show folders
    // 4. Restore stems to folders
    // 5. Hide prerequisite edges
}

async function switchToKnowledgeMode() {
    if (currentMode === 'knowledge') return;

    // 1. Load KG data if needed
    // 2. Move files to knowledge positions
    // 3. Show tags
    // 4. Hide folders
    // 5. Rebind stems to tags/chains
}
```

---

## Removed Code

| Removed | Reason |
|---------|--------|
| `yBlendValue` variable | Replaced by `currentMode` |
| `updateKnowledgeBlend(value)` | Replaced by mode switch functions |
| Slider interpolation logic | No longer needed |
| lerp() calls | No blending between modes |
| Old slider CSS | New button CSS |

---

## API Changes

None - backend unchanged. Mode affects only frontend visualization.

---

## User Experience

### Before (Confusing)
- Slider 0-100%
- Intermediate states unclear
- Files move erratically during drag
- Reset sometimes failed

### After (Clear)
- Two buttons: Directory / Knowledge
- Click once to switch
- Instant, predictable transition
- Reset always works (switches to Directory)

---

## Files Modified

| File | Changes |
|------|---------|
| `src/visualizer/tree_renderer.py` | HTML, CSS, JS for mode toggle |

---

## Testing Checklist

```
[ ] Page loads in Directory Mode (Directory button highlighted)
[ ] Click Knowledge → instant switch to fan layout
[ ] Click Directory → instant switch back
[ ] Tags visible only in Knowledge Mode
[ ] Folders visible only in Directory Mode
[ ] Stems connect to correct parents in each mode
[ ] Reset View works (switches to Directory)
[ ] Export uses currentMode for mode parameter
```

---

*Implemented: December 25, 2025*
*Author: Claude Opus 4.5*
