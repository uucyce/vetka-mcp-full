# 3D Viewport & Visualization Analysis
## HAIKU Report 10 - VETKA 3D Rendering System

**Date:** 2026-01-24
**Analyzed by:** Claude Haiku 4.5
**Status:** OK - Fully Functional

---

## 1. Visualization Tech Stack

### Core Libraries
| Library | Version | Purpose |
|---------|---------|---------|
| **Three.js** | 0.170.0 | 3D rendering engine |
| **React Three Fiber** | 9.0.0 | React bridge for Three.js |
| **Three/Drei** | 10.0.0 | Utility components (OrbitControls, Line, Html) |
| **React** | 19.0.0 | UI framework |
| **Zustand** | 4.5.2 | State management |

### Canvas Architecture
```
App.tsx (Canvas from @react-three/fiber)
├── OrbitControls (interactive camera)
├── CameraController (animation + focus)
├── GridHelper (background grid)
├── TreeEdges (edge rendering)
└── FileCard (node rendering) x N nodes
```

### Rendering Pipeline
- **Perspective Camera:** FOV 60°, near 0.1, far 10,000
- **Lighting:** Ambient (0.5) + Directional (1.0)
- **Antialias:** Enabled
- **Background:** #0a0a0a (dark gray)

---

## 2. Semantic Zoom Implementation

### Status: FULLY IMPLEMENTED (Google Maps style)

### 10-Level LOD System (FileCard.tsx:9-28)

| LOD | Distance | Visual | Content |
|-----|----------|--------|---------|
| **0** | >2500 | Tiny dot | No detail |
| **1** | 2500-1500 | Small shape | Shape visible |
| **2** | 1500-800 | Shape + name | Name starting |
| **3** | 800-400 | Clear shape + name | Full name visible |
| **4** | 400-150 | Larger card | No preview yet |
| **5** | 150-50 | Mini preview starts | 3-5 lines visible |
| **6** | 50-35 | Mini preview full | Full preview on card |
| **7** | 35-20 | Large preview | Larger preview |
| **8** | 20-10 | Full preview | Complete content |
| **9** | <10 | Ultra close | Full detail + extras |

### Semantic Zoom Features (FileCard.tsx:603-695)

#### Folder Label Visibility Algorithm
```javascript
Importance = 0.50 * depthScore + 0.50 * sizeScore

Where:
  - depthScore = 1/√(depth+1)  // Slower decay for root priority
  - sizeScore = √(childCount) / √(MAX_CHILDREN)

visibilityThreshold = importance * MAX_DISTANCE
  - Root (depth 0): Always visible
  - Folders: Hide if distance > visibilityThreshold
```

#### Dynamic Font Sizing
- Base: 14px
- Importance boost: 0-18px (based on importance score)
- Distance decay: 0-30% reduction at far distances
- Max: 32px

#### Implementation Quality
- Smooth transitions between LOD levels
- Importance weighting (50% depth, 50% size)
- Root folders always visible (depth=0)
- Configurable MAX_DISTANCE: 8000 units (tuned for 1701 nodes)

---

## 3. Lazy Loading Implementation

### Status: PARTIALLY IMPLEMENTED (Content-based, not node-based)

### Preview Content Loading (FileCard.tsx:249-298)

#### Trigger Conditions
```javascript
shouldLoadContent = (lodLevel >= 3 || isHoveredDebounced)
                  && type === 'file'
                  && isPreviewableFile(name)
```

#### Loading Strategy
1. **Cache-First:** Global `previewCache` Map persists across components
2. **LOD-Based:** Only loads when card becomes visible (LOD 3+) OR hovered
3. **Debounced:** 300ms hover delay prevents spam
4. **Size-Limited:** First ~2000 chars only

#### Previewable File Detection
**Supported:**
- Code: py, js, ts, tsx, jsx, json, yaml, yml, sh, bash, css, scss, less, html, xml, sql, java, cpp, c, h, hpp, go, rs, rb, php, swift, kt, scala, vue, svelte

**Excluded (Binary):**
- Images: png, jpg, jpeg, gif, bmp, ico, svg, webp, tiff
- Videos: mp4, avi, mov, mkv, webm, flv
- Audio: mp3, wav, ogg, flac, aac
- Fonts: ttf, otf, woff, woff2, eot
- Archives: zip, tar, gz, rar, 7z
- Documents: pdf, doc, docx, xls, xlsx, ppt, pptx

#### Memory Management
- Preview content cleared on unhover (saves memory)
- Global cache prevents duplicate loads
- Fallback message shown if file unavailable

### Node Lazy Loading

**Status: NOT IMPLEMENTED** - All nodes rendered always
The system renders all nodes in viewport without frustum culling or LOD-based node culling.

---

## 4. Viewport Context & Frustum Culling

### Status: IMPLEMENTED (viewport.ts - Phase 70)

#### Frustum Culling (viewport.ts:110-163)
```javascript
getVisibleNodes(nodesRecord, camera) → ViewportNode[]
- Builds camera frustum from projection matrix
- Tests each node against frustum containment
- Calculates distance to camera (for LOD)
- Determines if in camera center ray (foveated priority)
- Returns sorted by distance (closest first)
```

#### ViewportContext Structure (viewport.ts:46-59)
```typescript
{
  camera_position: { x, y, z }
  camera_target: { x, y, z }
  zoom_level: 0-9 (LOD scale)
  pinned_nodes: ViewportNode[]     // Explicit selection
  viewport_nodes: ViewportNode[]   // Visible nodes
  total_visible: number
  total_pinned: number
}
```

#### LOD Detail Levels (viewport.ts:92-97)
- **Minimal (LOD 0-2):** name + type only
- **Basic (LOD 3-5):** + summary line
- **Detailed (LOD 6-8):** + key exports
- **Full (LOD 9):** complete content if fits

---

## 5. Edge Rendering (TreeEdges.tsx)

### Geometry
- **Type:** Catmull-Rom spline curves (20 segments)
- **Visual:** Curved edges with midpoint elevation
- **Rendering:** @react-three/drei `Line` component

### Color Coding (monochrome style)
| State | Color | Width | Opacity |
|-------|-------|-------|---------|
| Default | #6b7280 (gray) | 1.5 | 0.6 |
| Agent highlighted | #9ca3af (lighter) | 2.5 | 0.8 |
| Selected | #d1d5db (brightest) | 2.0 | 0.75 |

### Edge Source Logic
1. Primary: Uses `storeEdges` array if available
2. Fallback: Computes from `parentId` relationships
3. Visibility: Shows edges for both pinned + viewport nodes

---

## 6. FileCard Rendering (Nodes)

### Billboard Effect
- Cards always face camera (quaternion-based orientation)
- Updated every frame to follow camera rotation

### Canvas-Based Texture Generation
- **Dimensions:** Dynamic based on file type
  - Code files: 256×128 px (horizontal, 16:9)
  - Documents: 128×192 px (vertical, 3:4)
  - Folders: 256×128 px (square-ish)

- **Rendering:** Procedural canvas drawing
  - Dynamic border colors (selection/drag states)
  - File preview text drawn inline (small monospace)
  - Folder icons with alpha transparency
  - Pin indicators (blue border/dot)

### State Tracking (FileCard.tsx:172-182)
- `isDragging` - Blender-style ctrl+drag or grab mode
- `isHovered` - For preview triggering
- `isHoveredDebounced` - 300ms debounced for preview load
- `previewContent` - Cached file content
- `loadingPreview` - Async load state
- `lodLevel` - Updated every 100ms

### Ghost Files (Phase 90.11)
- Semi-transparent nodes for deleted files in Qdrant
- Opacity customizable (default 0.3 for ghosts)

---

## 7. Camera Control System (CameraController.tsx)

### Animation Pipeline
1. **Find node** by path/name/partial match
2. **Calculate target position** (frontal approach, Z+ direction)
3. **Setup animation** with quaternion interpolation
4. **Disable OrbitControls** during animation
5. **Ease-in-out interpolation** over 2.5 seconds
6. **Re-enable OrbitControls** with target sync

### Distance Levels
| Zoom | Distance |
|------|----------|
| close | 20 |
| medium | 30 |
| far | 45 |

### Features
- Smooth quaternion slerp for rotation
- Position lerp with easing curve
- Node highlighting during flight (3s)
- Context switch on completion

---

## 8. Performance Optimizations

### What's Optimized
✅ **Preview Caching** - Global Map prevents redundant loads
✅ **LOD Throttling** - Updates every 100ms, not every frame
✅ **Hover Debouncing** - 300ms delay prevents spam loading
✅ **Content Size Limit** - 2000 char preview truncation
✅ **Frustum Culling** - getVisibleNodes() reduces AI context
✅ **Canvas Textures** - Reusable memoized textures
✅ **Curve Caching** - Edge curves memoized per pair

### What's Not Optimized
❌ **Node Rendering** - All nodes rendered every frame (no LOD culling)
❌ **Instance Rendering** - Individual meshes per node (no THREE.InstancedMesh)
❌ **Texture Atlas** - Separate canvas per card (not atlased)
❌ **Draw Call Reduction** - No batching strategy

---

## 9. Integration Points

### With Store (Zustand)
- `selectedId` - Current selection
- `highlightedId` - Temporary highlight (3s)
- `pinnedFileIds` - Pinned nodes (high priority)
- `nodes` - All nodes data
- `edges` - Edge definitions
- `cameraRef` - Store camera for viewport context
- `cameraCommand` - Animation trigger

### With Chat System
- Selected node = Chat context
- Pinned nodes = Higher context priority
- Camera fly-to on file selection

### With Artifact Viewer
- Selected node shows in artifact window
- File preview accessible from cards

---

## 10. Issues & Recommendations

### Critical Issues
**None found** - System is functional

### Minor Issues
1. **Node Count Rendering:** With 1701 nodes, all-at-once rendering may impact performance at high zoom-out levels
   - *Recommendation:* Implement THREE.InstancedMesh for node rendering

2. **Memory Usage:** Canvas textures created per card (not atlased)
   - *Recommendation:* Use texture atlas or WebGL render-to-texture

3. **Update Frequency:** Camera ref set but not actively used by viewport context builder
   - *Recommendation:* Integrate viewport context into chat/agent pipeline

### Enhancement Opportunities
1. Add occlusion culling for heavily overlapped nodes
2. Implement progressive loading for large file previews
3. Add search-result highlighting in viewport
4. Implement spatial partitioning (octree) for 10k+ node support
5. Cache viewport context in-memory for AI agent queries

---

## 11. Summary

### Status: ✅ OK - Fully Functional

**Strengths:**
- Excellent semantic zoom with importance weighting
- Well-designed LOD system (10 levels)
- Smooth camera animations with quaternion interpolation
- Smart preview loading with caching and debouncing
- Frustum culling ready for AI context
- Clean component architecture (React Three Fiber)

**Current Capacity:**
- Handles 1701 nodes smoothly
- Supports camera focus/zoom animations
- Intelligent folder label visibility
- Hybrid frustum culling + pinned node system

**Ready For:**
- Production use at current scale
- Integration with AI agent viewport context
- Further optimization to 5k-10k node range

---

## File Inventory

| File | Purpose | LOC | Status |
|------|---------|-----|--------|
| FileCard.tsx | Node rendering + LOD | 698 | ✅ ACTIVE |
| TreeEdges.tsx | Edge rendering | 93 | ✅ ACTIVE |
| CameraController.tsx | Camera animation | 254 | ✅ ACTIVE |
| Edge.tsx | Single edge curve | 47 | ✅ ACTIVE |
| viewport.ts | Frustum culling + context | 262 | ✅ ACTIVE |
| App.tsx | Canvas orchestration | 915 | ✅ ACTIVE |
| useStore.ts | State management | Contains camera + pinned | ✅ ACTIVE |

---

## Technical Debt

- Scene.tsx is placeholder (empty)
- Grab mode implementation (Phase 65) works but not fully integrated
- Drag & drop (Phase 54.7) disabled pending Tauri migration
- No node LOD culling (renders all always)
- No texture atlasing strategy

---

**Report Generated:** 2026-01-24
**Next Phase:** Phase 91 - 3D Optimization & Scale Testing
