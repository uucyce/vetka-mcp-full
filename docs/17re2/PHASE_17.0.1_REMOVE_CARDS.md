# PHASE 17.0.1: Card Overlay Audit - NO CLEANUP NEEDED

**Date:** 2025-12-24
**Status:** AUDIT PASSED - Architecture is already clean

---

## Executive Summary

A thorough audit was performed to identify duplicate card overlays. **No duplicates exist.** The codebase has a clean architecture where:

1. File sprites ARE the primary visualization (no separate overlays)
2. Edges connect via file.id (not card.id)
3. Content preview is in a proper Artifact Panel (not 3D overlay)

---

## Architecture Analysis

### File Visualization System

```
┌─────────────────────────────────────────────────────────┐
│                    Three.js Scene                       │
│                                                         │
│  ┌─────────────┐         ┌─────────────┐               │
│  │ File Sprite │ ←edge→  │ File Sprite │               │
│  │ (canvas     │         │ (canvas     │               │
│  │  texture)   │         │  texture)   │               │
│  └─────────────┘         └─────────────┘               │
│         ↑                       ↑                       │
│    nodeObjects.get(file.id)                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          ↓ click
┌─────────────────────────────────────────────────────────┐
│                   Artifact Panel                        │
│              (Separate DOM element)                     │
│  Shows file content when clicked                        │
└─────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Type | Purpose | Location |
|-----------|------|---------|----------|
| `createVisibleFileCard()` | Function | Creates THREE.Sprite with CanvasTexture | Line 3046 |
| `fileCards[]` | Array | Tracks all file sprites | Line 2026 |
| `nodeObjects` | Map | Maps file.id → {mesh, data} | Lines 2839, 5996 |
| Edge Creation | Function | Uses `nodeObjects.get(edge.from/to)` | Line 2974 |
| Artifact Panel | DOM | Shows content on click | Line 1581-1610 |

---

## Verification Results

### 1. Card Creation Code
```javascript
// Line 3046-3116: createVisibleFileCard()
const sprite = new THREE.Sprite(material);  // Line 3093
sprite.userData = { type: 'file', nodeId: node.id, ... };
return sprite;  // Returns SPRITE, not overlay
```

### 2. Edge Source Check
```javascript
// Line 2974-2975: Edge lookup
const fromInfo = nodeObjects.get(edge.from);  // Uses file.id
const toInfo = nodeObjects.get(edge.to);      // Uses file.id
```

**Result:** Edges connect file→file, not card→card

### 3. Overlay Search
```bash
grep -n "overlay" src/visualizer/tree_renderer.py
```
**Results:**
- Line 637, 650, 803: `.modal-overlay` (CSS for VETKA creation modal)
- Line 1545: Comment about artifact panel
- Line 3101: Comment about opacity

**No 3D overlay system exists!**

### 4. DOM Element Creation
```bash
grep -n "document.createElement" src/visualizer/tree_renderer.py
```
**Results:**
- Line 1691: `escapeHtml()` helper (creates temp div for escaping)
- Line 4499: Same pattern

**No overlay divs created for file content!**

---

## What Was Found (All Correct)

| Element | Status | Notes |
|---------|--------|-------|
| File Sprites | Correct | THREE.Sprite with CanvasTexture |
| Content Preview | Correct | Part of sprite's canvas drawing |
| Edge Connections | Correct | file.id → file.id lookup |
| Artifact Panel | Correct | Separate DOM panel for detailed view |
| Modal Overlay | Correct | Only for VETKA creation dialog |

---

## Conclusion

**NO CLEANUP NEEDED**

The visualization architecture is already optimized:

1. **File sprites = primary visualization** (no overlays)
2. **Edges = file.id connections** (not card-based)
3. **Content preview = canvas texture** (not DOM overlay)
4. **Detailed view = Artifact Panel** (proper separation)

The request was based on a misunderstanding of the architecture. The "cards" mentioned ARE the file sprites - there's no separate card layer to remove.

---

## Recommendation

Proceed directly to Phase 17.1 (CAM) - the visualization layer is clean and properly structured.

---

*Audited: 2025-12-24*
*Author: Claude Opus 4.5*
