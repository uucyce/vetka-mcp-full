# H6: 3D Assets Report - VETKA Phase 100 Tauri Migration

## Summary

**No pre-made 3D model files**. All 3D visualization is code-based with procedural geometry.

## 3D Model Files

| Format | Count | Notes |
|--------|-------|-------|
| .gltf | 0 | None found |
| .glb | 0 | None found |
| .obj | 0 | None found |
| .fbx | 0 | None found |

## Textures

- No dedicated texture files
- Canvas-based textures generated dynamically in FileCard.tsx
- Environment presets from @react-three/drei

## Shaders

- No custom shader files (.glsl, .vert, .frag)
- All materials use built-in Three.js materials

## Three.js Components

| Component | Path | Purpose |
|-----------|------|---------|
| FileCard | `canvas/FileCard.tsx` | 3D mesh cards, LOD, canvas textures |
| Edge | `canvas/Edge.tsx` | Curved lines (CatmullRomCurve3) |
| TreeEdges | `canvas/TreeEdges.tsx` | All graph edges |
| CameraController | `canvas/CameraController.tsx` | Smooth camera animation |
| ThreeDViewer | `artifact-panel/.../ThreeDViewer.tsx` | GLTF model viewer |
| Scene | `canvas/Scene.tsx` | Placeholder group |

## R3F/Three.js APIs Used

### React-Three-Fiber
- `Canvas` - Main renderer
- `useFrame` - Per-frame updates
- `useThree` - Camera, raycaster access
- `ThreeEvent` - Pointer events

### @react-three/drei
- `OrbitControls` - Camera control
- `Html` - 2D overlays in 3D
- `Line` - 3D line rendering
- `useGLTF` - GLTF loading
- `Environment` - Preset lighting ("city")
- `Center` - Auto-center models

### Three.js Core
- `THREE.Mesh` - Geometry containers
- `THREE.Vector3` - Positions
- `THREE.Matrix4` - Transforms
- `THREE.Quaternion` - Rotations
- `THREE.CanvasTexture` - Dynamic textures
- `THREE.CatmullRomCurve3` - Smooth curves
- `THREE.Raycaster` - Mouse picking
- `THREE.Frustum` - Viewport culling

## Canvas Configuration (App.tsx)

```javascript
Canvas:
  size: 100vw × 100vh
  camera: [0, 500, 1000], FOV 60°, far 10000
  antialiasing: enabled
  background: #0a0a0a

Lighting:
  ambientLight: 0.5
  directionalLight: [10, 10, 5]

Grid:
  size: 2000 × 100
  color: dark
```

## LOD System (FileCard.tsx)

| Level | Distance | Detail |
|-------|----------|--------|
| 0 | >300 units | Tiny dot |
| 5 | 50-70 units | Mini preview |
| 9 | <10 units | Ultra detail |

## Viewport Context (viewport.ts)

- Frustum culling for visible nodes
- Foveated rendering (center priority)
- Pinned vs viewport separation
- LOD-based detail levels

## Drag System (useDrag3D.ts)

- Ctrl/Cmd+Drag for movement
- Raycaster plane intersection
- Pointer capture
- Blender-style grab mode (G key)

## Package Versions

```json
{
  "three": "^0.170.0",
  "@types/three": "^0.170.0",
  "@react-three/fiber": "^9.0.0",
  "@react-three/drei": "^10.0.0"
}
```

## Supported 3D File Types

ThreeDViewer supports: `.gltf`, `.glb`, `.obj`, `.fbx`, `.stl`, `.3ds`, `.dae`

## Markers

[3D_MODEL] None (procedural only)
[3D_TEXTURE] Canvas-based: FileCard.tsx:436
[3D_SHADER] None (built-in materials)
[3D_COMPONENT] 6 components
[3D_HOOK] useDrag3D.ts
[3D_UTILITY] viewport.ts

## Tauri Migration Notes

| File | Impact |
|------|--------|
| FileCard.tsx | Dynamic canvas texture needs no change |
| CameraController.tsx | useFrame works in Tauri WebView |
| useDrag3D.ts | Pointer events work in Tauri |
| ThreeDViewer.tsx | useGLTF needs file:// or blob: URLs |
| viewport.ts | Frustum culling unchanged |

---
Generated: 2026-01-29 | Agent: H6 Haiku | Phase 100
