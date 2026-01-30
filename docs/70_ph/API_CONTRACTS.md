# API Contracts — Viewport Context Integration

## Current API Contract

### Backend Event: `user_message`

**File:** `client/src/hooks/useSocket.ts:1047-1053`

```typescript
socketRef.current.emit('user_message', {
  text: string;
  node_path: string;
  node_id: string;
  model?: string;
  pinned_files?: Array<{
    id: string;
    path: string;
    name: string;
    type: 'file' | 'folder';
  }>;
});
```

**Current Payload Example:**
```json
{
  "text": "Explain this file",
  "node_path": "/root/src/components/App.tsx",
  "node_id": "root",
  "model": "claude",
  "pinned_files": [
    {
      "id": "file-123",
      "path": "/root/src/components/App.tsx",
      "name": "App.tsx",
      "type": "file"
    }
  ]
}
```

---

## Proposed Extended Contract

### With Viewport Context

```typescript
socketRef.current.emit('user_message', {
  text: string;
  node_path: string;
  node_id: string;
  model?: string;
  pinned_files?: PinnedFile[];
  viewport_nodes?: ViewportNode[];  // ← NEW
});
```

### New Type: ViewportNode

```typescript
interface ViewportNode {
  id: string;                            // Node ID
  position: { x: number; y: number; z: number };  // 3D position
  path: string;                          // File path
  type: 'file' | 'folder';              // Node type
  distance_to_camera?: number;           // Optional: distance metric
  lod_level?: number;                    // Optional: current LOD level
  is_selected?: boolean;                 // Optional: if currently selected
}
```

### Extended Payload Example

```json
{
  "text": "Explain the architecture",
  "node_path": "/root/src/components/App.tsx",
  "node_id": "root",
  "model": "claude",
  "pinned_files": [
    {
      "id": "file-123",
      "path": "/root/src/components/App.tsx",
      "name": "App.tsx",
      "type": "file"
    }
  ],
  "viewport_nodes": [
    {
      "id": "file-1",
      "position": { "x": 125.4, "y": 340.2, "z": 89.7 },
      "path": "/root/src/App.tsx",
      "type": "file",
      "distance_to_camera": 45.2,
      "lod_level": 5,
      "is_selected": true
    },
    {
      "id": "file-2",
      "position": { "x": 200.1, "y": 280.5, "z": 120.3 },
      "path": "/root/src/main.tsx",
      "type": "file",
      "distance_to_camera": 62.1,
      "lod_level": 4,
      "is_selected": false
    }
  ]
}
```

---

## Type Definitions

### Current TreeNode (Store)

```typescript
// From useStore.ts:7-25
export interface TreeNode {
  id: string;
  path: string;
  name: string;
  type: 'file' | 'folder';
  backendType: VetkaNodeType;
  depth: number;
  parentId: string | null;
  position: { x: number; y: number; z: number };
  color: string;
  extension?: string;
  children?: string[];
  semanticPosition?: {
    x: number;
    y: number;
    z: number;
    knowledgeLevel: number;
  };
}
```

### Proposed ViewportNode (Minimal)

```typescript
export interface ViewportNode {
  id: string;
  position: { x: number; y: number; z: number };
  path: string;
  type: 'file' | 'folder';
}
```

### Proposed ViewportNode (Extended)

```typescript
export interface ViewportNodeExtended extends ViewportNode {
  distance_to_camera?: number;
  lod_level?: number;
  is_selected?: boolean;
  name?: string;
  depth?: number;
}
```

---

## Implementation: sendMessage Update

### Current Implementation

**File:** `useSocket.ts:1019-1054`

```typescript
const sendMessage = useCallback((message: string, nodePath?: string, modelId?: string) => {
  if (!socketRef.current?.connected) return;

  const pinnedFileIds = useStore.getState().pinnedFileIds;
  const nodes = useStore.getState().nodes;

  const pinnedFiles = pinnedFileIds
    .map(id => nodes[id])
    .filter(Boolean)
    .map(node => ({
      id: node.id,
      path: node.path,
      name: node.name,
      type: node.type,
    }));

  socketRef.current.emit('user_message', {
    text: message,
    node_path: nodePath || 'unknown',
    node_id: 'root',
    model: modelId,
    pinned_files: pinnedFiles.length > 0 ? pinnedFiles : undefined,
  });
}, []);
```

### Proposed Implementation

```typescript
const sendMessage = useCallback((message: string, nodePath?: string, modelId?: string) => {
  if (!socketRef.current?.connected) return;

  const pinnedFileIds = useStore.getState().pinnedFileIds;
  const nodesRecord = useStore.getState().nodes;

  // 1. Transform pinned files (unchanged)
  const pinnedFiles = pinnedFileIds
    .map(id => nodesRecord[id])
    .filter(Boolean)
    .map(node => ({
      id: node.id,
      path: node.path,
      name: node.name,
      type: node.type,
    }));

  // 2. NEW: Get viewport nodes (requires camera access)
  const viewportNodes = getViewportNodes(nodesRecord, camera);

  // 3. Emit with new field
  socketRef.current.emit('user_message', {
    text: message,
    node_path: nodePath || 'unknown',
    node_id: 'root',
    model: modelId,
    pinned_files: pinnedFiles.length > 0 ? pinnedFiles : undefined,
    viewport_nodes: viewportNodes.length > 0 ? viewportNodes : undefined,  // ← NEW
  });
}, []);
```

---

## Helper Function: getViewportNodes

### Location
Create new file: `client/src/utils/viewport.ts`

### Implementation (Simple)

```typescript
import * as THREE from 'three';
import { TreeNode } from '../store/useStore';

export interface ViewportNode {
  id: string;
  position: { x: number; y: number; z: number };
  path: string;
  type: 'file' | 'folder';
  distance_to_camera?: number;
}

/**
 * Get all nodes visible in camera frustum
 */
export function getViewportNodes(
  nodesRecord: Record<string, TreeNode>,
  camera: THREE.PerspectiveCamera,
  includeDistance: boolean = true
): ViewportNode[] {
  const nodes = Object.values(nodesRecord);

  // Build frustum
  const frustum = new THREE.Frustum();
  frustum.setFromProjectionMatrix(
    new THREE.Matrix4().multiplyMatrices(
      camera.projectionMatrix,
      camera.matrixWorldInverse
    )
  );

  // Filter visible nodes
  return nodes
    .filter(node => {
      const point = new THREE.Vector3(
        node.position.x,
        node.position.y,
        node.position.z
      );
      return frustum.containsPoint(point);
    })
    .map(node => ({
      id: node.id,
      position: node.position,
      path: node.path,
      type: node.type,
      distance_to_camera: includeDistance
        ? camera.position.distanceTo(
            new THREE.Vector3(
              node.position.x,
              node.position.y,
              node.position.z
            )
          )
        : undefined,
    }));
}
```

### Implementation (With LOD)

```typescript
/**
 * Get viewport nodes with LOD level
 */
export function getViewportNodesWithLOD(
  nodesRecord: Record<string, TreeNode>,
  camera: THREE.PerspectiveCamera
): ViewportNode[] {
  const nodes = Object.values(nodesRecord);

  const frustum = new THREE.Frustum();
  frustum.setFromProjectionMatrix(
    new THREE.Matrix4().multiplyMatrices(
      camera.projectionMatrix,
      camera.matrixWorldInverse
    )
  );

  return nodes
    .filter(node => {
      const point = new THREE.Vector3(
        node.position.x,
        node.position.y,
        node.position.z
      );
      return frustum.containsPoint(point);
    })
    .map(node => {
      const dist = camera.position.distanceTo(
        new THREE.Vector3(
          node.position.x,
          node.position.y,
          node.position.z
        )
      );

      return {
        id: node.id,
        position: node.position,
        path: node.path,
        type: node.type,
        distance_to_camera: dist,
        lod_level: getLODLevel(dist),  // 0-9
      };
    });
}

/**
 * Calculate LOD level based on distance
 * Matches FileCard.tsx LOD system
 */
function getLODLevel(distance: number): number {
  if (distance > 300) return 0;
  if (distance > 200) return 1;
  if (distance > 150) return 2;
  if (distance > 100) return 3;
  if (distance > 70) return 4;
  if (distance > 50) return 5;
  if (distance > 35) return 6;
  if (distance > 20) return 7;
  if (distance > 10) return 8;
  return 9;
}
```

---

## Challenge: Getting Camera in useSocket

### Problem
`useSocket` is a hook called at app level, but `useThree()` only works inside `<Canvas>`.

### Solution Options

#### Option 1: Camera Context
```typescript
// Create CameraContext provider in App.tsx
export const CameraContext = createContext<THREE.PerspectiveCamera | null>(null);

function CameraProvider({ children }) {
  const { camera } = useThree();
  return (
    <CameraContext.Provider value={camera}>
      {children}
    </CameraContext.Provider>
  );
}

// Wrap Canvas children
<Canvas>
  <CameraProvider>
    {/* children that use useSocket */}
  </CameraProvider>
</Canvas>

// Then in useSocket:
const camera = useContext(CameraContext);
```

#### Option 2: Global Reference (Quick)
```typescript
// App.tsx - Store camera like we do with OrbitControls
const { camera } = useThree();
(window as any).__camera = camera;

// useSocket.ts
const camera = (window as any).__camera;
```

#### Option 3: Zustand Store (Clean)
```typescript
// Add to useStore
interface TreeState {
  // ...
  cameraRef?: THREE.PerspectiveCamera | null;
  setCameraRef: (camera: THREE.PerspectiveCamera) => void;
}

// App.tsx - CameraController or direct
const { camera } = useThree();
const setCameraRef = useStore((s) => s.setCameraRef);
useEffect(() => setCameraRef(camera), [camera, setCameraRef]);

// useSocket.ts
const camera = useStore((s) => s.cameraRef);
```

**Recommended:** Option 3 (cleanest, consistent with architecture)

---

## Backend Integration

### Expected Changes

1. **Handler for `user_message`:**
   ```python
   @socket.on('user_message')
   def handle_user_message(data):
       text = data.get('text')
       node_path = data.get('node_path')
       model = data.get('model')
       pinned_files = data.get('pinned_files', [])
       viewport_nodes = data.get('viewport_nodes', [])  # NEW

       # Use viewport_nodes for context assembly
   ```

2. **Context Assembly:**
   ```python
   def assemble_context(user_message, pinned_files, viewport_nodes):
       # Existing: pinned_files provide multi-file context
       # New: viewport_nodes provide spatial awareness
       # Result: AI understands not just files, but their spatial relationships
   ```

3. **Validation:**
   ```python
   # Validate viewport_nodes structure
   for node in viewport_nodes:
       assert 'id' in node
       assert 'position' in node
       assert 'path' in node
       assert 'type' in node
   ```

---

## Testing Checklist

### Frontend Tests

- [ ] Camera context accessible in useSocket
- [ ] getViewportNodes returns correct array
- [ ] Frustum culling works correctly
- [ ] Distance calculation accurate
- [ ] LOD levels assigned correctly
- [ ] viewport_nodes included in emit
- [ ] Backward compatible (viewport_nodes optional)

### Backend Tests

- [ ] Accept viewport_nodes field
- [ ] Parse viewport_nodes array
- [ ] Handle empty viewport_nodes
- [ ] Use viewport_nodes in context
- [ ] No regressions in existing flow

### Integration Tests

- [ ] Send message with pinned + viewport
- [ ] Backend receives both correctly
- [ ] Context assembly uses viewport
- [ ] Response quality improved

---

## Backward Compatibility

### Frontend
✅ **Fully backward compatible**
- `viewport_nodes` field optional in emit
- Existing pinned_files still works
- No breaking changes to types

### Backend
⚠️ **Requires update**
- Must accept optional `viewport_nodes` field
- Should not fail if missing
- Can implement gradually

**Migration Path:**
1. Add viewport_nodes support (optional)
2. Log when received/not received
3. Gradually enable context assembly
4. Monitor performance
5. Make required (if beneficial)

---

## Performance Considerations

### Frustum Calculation
- **Cost:** ~1ms per frame (10 nodes)
- **Optimization:** Cache frustum, update only on camera change
- **Frequency:** Can send with every message (likely 1-2 per second)

### Viewport Nodes Size
- **Typical:** 5-20 nodes visible at once
- **Worst case:** 100+ (extreme zoom out)
- **Payload:** ~2-4 KB per message (gzip: <1 KB)

### Recommendation
- Calculate on demand (in sendMessage)
- No continuous updates needed
- Include distance for AI reasoning
- LOD level optional (can add later)

---

## File Changes Summary

| File | Change | Lines |
|------|--------|-------|
| `useSocket.ts` | Add viewport_nodes to emit | +10 |
| `viewport.ts` | NEW utility functions | +60 |
| `useStore.ts` | Add camera ref field | +3 |
| `App.tsx` | Set camera ref in store | +3 |
| `types/chat.ts` | Define ViewportNode type | +10 |

**Total: ~5 files, ~86 lines added**

---

## References

- **Camera frustum:** https://threejs.org/docs/#api/en/math/Frustum
- **Vector3 distance:** https://threejs.org/docs/#api/en/math/Vector3.distanceTo
- **LOD patterns:** Google Maps, Cesium.js
- **Spatial context:** Context-aware AI systems

---

**Phase 70 — Viewport Context API Contracts**
**Status:** READY FOR IMPLEMENTATION
