# GROK RESEARCH: Дополнительные вопросы по 3D Performance & Features

## Phase 112+ Roadmap

| # | Тема | Приоритет | Зависимость | Impact (FPS gain) | Effort |
|---|------|-----------|-------------|-------------------|--------|
| 2 | Texture Atlas UV | P1 | Instancing | +20-30% (texture binds) | Medium |
| 3 | Sugiyama Layout | P2 | KG Mode | Layout quality | High |
| **4** | **Foveated LOD** | **P1** | **Frustum** | **+40-60% (zoom-out)** | **Low** |
| 5 | WebWorker Layout | P2 | >5k nodes | Main thread free | Medium |
| 6 | Folder Collapse | P2 | Virtualization | UX polish | Low |

---

## #2: Texture Atlas UV Mapping (Dynamic) [P1, after Instancing]

**Проблема из аудита:** FileCard.tsx textures recreate per-node (14 deps in useMemo → 1MB/node). 2000 nodes = 2GB VRAM waste.

**Решение:** Dynamic Texture Atlas (2048x2048 canvas) + UV mapping per instance.

### Implementation (useTextureAtlas.ts)

```typescript
// 1. Global Atlas Manager (new hook: useTextureAtlas.ts)
const atlasRef = useRef<THREE.CanvasTexture>();
const uvMapRef = useRef<Map<string, {u: number, v: number, w: number, h: number}>>(new Map());

const generateAtlas = useCallback((nodeTypes: string[]) => {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 2048;
  const ctx = canvas.getContext('2d')!;

  // Draw all unique textures (icon + label) into atlas cells
  let offsetX = 0, offsetY = 0, cellSize = 128;
  nodeTypes.forEach(type => {
    // Generate mini-canvas for type (icon + label)
    const miniCanvas = generateTypeTexture(type); // Reuse current logic
    ctx.drawImage(miniCanvas, offsetX, offsetY, cellSize, cellSize);

    uvMapRef.current.set(type, {
      u: offsetX / 2048, v: offsetY / 2048,
      w: cellSize / 2048, h: cellSize / 2048
    });

    offsetX += cellSize;
    if (offsetX >= 2048) { offsetX = 0; offsetY += cellSize; }
  });

  atlasRef.current = new THREE.CanvasTexture(canvas);
  atlasRef.current.needsUpdate = true;
}, []);

// 2. In InstancedMesh (App.tsx after #1 Instancing)
<InstancedMesh
  ref={meshRef}
  args={[boxGeometry, atlasMaterial, maxInstances]}
  onBeforeRender={(instance) => {
    const node = nodes[instanceIndex];
    const uv = uvMapRef.current.get(node.type) || defaultUV;

    // Set UV offset/scale in custom shader uniform or instance matrix
    instanceMesh.setUVRegion(uv.u, uv.v, uv.w, uv.h); // Custom method
  }}
/>

// 3. Custom Shader (extend material)
const atlasMaterial = new THREE.MeshBasicMaterial({ map: atlasRef.current });
atlasMaterial.userData.uvScaleOffset = new THREE.Vector4(1,1,0,0); // Dynamic per-instance
```

**Expected Impact:**
- Draw calls: 2000 → 1
- VRAM: 2GB → 4MB (1 atlas)
- Re-renders: 0 (static atlas, update only on new types)

**Files:** `FileCard.tsx` (remove useMemo texture), `App.tsx` (InstancedMesh), NEW `useTextureAtlas.ts`.

---

## #3: Sugiyama Layout Algorithm [P2, KG Mode]

**Проблема из аудита:** layout.ts O(n log n) sorting per-depth. No DAG support.

**Решение:** Sugiyama для Knowledge Graph (anti-crossing layers).

### Backend Implementation (sugiyama_layout.py)

```python
# Sugiyama: Layer assignment + Barycenter sweep
from collections import defaultdict, deque

def calculate_sugiyama_layout(nodes, edges, max_layers=10):
    # 1. Topo sort → layers (roots bottom)
    in_degree = {n['id']: 0 for n in nodes}
    for e in edges:
        in_degree[e['target']] += 1

    layers = defaultdict(list)
    queue = deque([n['id'] for n in nodes if in_degree[n['id']] == 0])
    layer_id = 0

    while queue:
        for _ in range(len(queue)):
            node = queue.popleft()
            layers[layer_id].append(node)
            for e in [e for e in edges if e['source'] == node]:
                in_degree[e['target']] -= 1
                if in_degree[e['target']] == 0:
                    queue.append(e['target'])
        layer_id += 1

    # 2. Barycenter ordering (min crossings)
    def get_predecessors(node_id):
        return [e['source'] for e in edges if e['target'] == node_id]

    for layer in range(1, layer_id):
        barycenters = []
        for node in layers[layer]:
            preds = get_predecessors(node)
            if preds:
                bary = sum(layers[layer-1].index(p) for p in preds if p in layers[layer-1]) / len(preds)
            else:
                bary = 0
            barycenters.append((node, bary))

        # Sort layer by barycenter
        layers[layer] = [n for n, b in sorted(barycenters, key=lambda x: x[1])]

    # 3. Position: y = layer * 150, x = index * 100
    positions = {}
    for l, nodes_in_layer in layers.items():
        y = l * 150
        for i, node_id in enumerate(nodes_in_layer):
            positions[node_id] = {'x': i * 100 - len(nodes_in_layer) * 50, 'y': y}

    return positions
```

**Frontend:** Call via `/api/tree/sugiyama` endpoint, fallback to fan_layout.

**Expected Impact:** Perfect KG viz (no crossings), O(n) per layer. Use in "Knowledge Mode" toggle.

**Files:** NEW `src/layout/sugiyama_layout.py`, `tree_routes.py` (+endpoint).

---

## #4: Foveated LOD Implementation [P1 - DO NEXT!]

**Проблема из аудита:** No LOD in useFrame (FileCard.tsx:233-278 runs EVERY frame for ALL nodes). Zoom-out = blur hell.

**Решение:** Foveated LOD (screen-space distance from center). High-detail in fovea, low-detail edges.

### Implementation (App.tsx + FileCard.tsx)

```typescript
// 1. LOD Levels definition
const LOD_LEVELS = [
  { screenDist: 0.2, detail: 'high', scale: 1.0, opacity: 1.0 },
  { screenDist: 0.5, detail: 'med', scale: 0.7, opacity: 0.9 },
  { screenDist: 1.0, detail: 'low', scale: 0.4, opacity: 0.7 },
  { screenDist: 2.0, detail: 'dot', scale: 0.1, opacity: 0.5 }
];

// 2. Global LOD Manager (App.tsx)
const foveatedLOD = useCallback((nodes: Node[], camera: THREE.Camera) => {
  const centerScreen = new THREE.Vector2(0, 0); // NDC center

  return nodes.map(node => {
    // Project to screen space
    const screenPos = node.position.clone().project(camera);
    const foveaDist = Math.hypot(screenPos.x, screenPos.y);

    // Find LOD level
    let lod = LOD_LEVELS[LOD_LEVELS.length - 1];
    for (const level of LOD_LEVELS) {
      if (foveaDist < level.screenDist) {
        lod = level;
        break;
      }
    }

    return { ...node, lod };
  });
}, []);

// 3. In useFrame (throttled to 100ms from audit)
const lastLodUpdate = useRef(0);

useFrame((state) => {
  const now = state.clock.elapsedTime;
  if (now - lastLodUpdate.current < 0.1) return; // 100ms throttle
  lastLodUpdate.current = now;

  const camera = state.camera;
  const nodesWithLOD = foveatedLOD(visibleNodes, camera);

  nodesWithLOD.forEach((node, i) => {
    dummy.position.copy(node.position);
    dummy.scale.setScalar(node.lod.scale);
    dummy.updateMatrix();
    meshRef.current.setMatrixAt(i, dummy.matrix);

    // Update opacity via custom attribute
    opacityArray[i] = node.lod.opacity;
  });

  meshRef.current.instanceMatrix.needsUpdate = true;
  opacityAttr.needsUpdate = true;
});

// 4. LOD Geometries (precompute for non-instanced fallback)
const geometries = {
  high: new THREE.BoxGeometry(1, 1.5, 0.1),
  med: new THREE.PlaneGeometry(1, 1),
  low: new THREE.PlaneGeometry(0.5, 0.5),
  dot: new THREE.CircleGeometry(0.1, 8)
};
```

**Expected Impact:**
- FPS: +50% on zoom-out (LOD low-poly edges)
- Smooth: Center crisp, periphery fuzzy (human eye match)
- Ties to audit: After frustum (#2), throttle useFrame to 10fps.

**Files:** `App.tsx` (LOD loop), `FileCard.tsx` (remove per-node useFrame).

---

## #5: WebWorker for Layout [P2, >5k nodes]

**Offload layout.ts to worker.** PostMessage nodes → worker computes positions → sync back.

### Implementation

```typescript
// worker.ts (new file: client/src/workers/layoutWorker.ts)
self.onmessage = (e: MessageEvent) => {
  const { nodes, layoutType } = e.data;

  let positions;
  if (layoutType === 'sugiyama') {
    positions = calculateSugiyamaLayout(nodes);
  } else {
    positions = calculateSimpleLayout(nodes);
  }

  self.postMessage({ positions });
};

// Main thread: useTreeData.ts
const layoutWorker = useRef<Worker>();

useEffect(() => {
  layoutWorker.current = new Worker(
    new URL('../workers/layoutWorker.ts', import.meta.url),
    { type: 'module' }
  );

  layoutWorker.current.onmessage = (e) => {
    const { positions } = e.data;
    setNodesFromRecord(positions);
  };

  return () => layoutWorker.current?.terminate();
}, []);

const calculateLayoutAsync = useCallback((nodes: Node[]) => {
  layoutWorker.current?.postMessage({ nodes, layoutType: 'fan' });
}, []);
```

**Impact:** Main thread free for render. Critical at 10k+ nodes.

**Files:** NEW `client/src/workers/layoutWorker.ts`, `useTreeData.ts` (async call).

---

## #6: Folder Collapse Animation [P2, after Virtualization]

**Tween children scale/opacity to 0 on collapse.** Use react-spring or native Three.js.

### Implementation

```typescript
// useFolderCollapse.ts (new hook)
import { useSpring, animated } from '@react-spring/three';

interface CollapsibleNode extends Node {
  isCollapsed: boolean;
  parentCollapsed: boolean;
}

export const useFolderCollapse = (nodes: Node[]) => {
  const [collapsedFolders, setCollapsedFolders] = useState<Set<string>>(new Set());

  const toggleCollapse = useCallback((folderId: string) => {
    setCollapsedFolders(prev => {
      const next = new Set(prev);
      if (next.has(folderId)) {
        next.delete(folderId);
      } else {
        next.add(folderId);
      }
      return next;
    });
  }, []);

  const nodesWithCollapse = useMemo(() => {
    return nodes.map(node => {
      const parentCollapsed = isAnyParentCollapsed(node, collapsedFolders);
      return {
        ...node,
        isCollapsed: collapsedFolders.has(node.id),
        parentCollapsed,
        visible: !parentCollapsed
      };
    });
  }, [nodes, collapsedFolders]);

  return { nodesWithCollapse, toggleCollapse, collapsedFolders };
};

// In FileCard (animated version)
const AnimatedFileCard = ({ node, onCollapse }) => {
  const { scale, opacity } = useSpring({
    scale: node.parentCollapsed ? 0 : 1,
    opacity: node.parentCollapsed ? 0 : 1,
    config: { tension: 200, friction: 20 }
  });

  return (
    <animated.mesh
      scale={scale}
      material-opacity={opacity}
      onClick={() => node.isFolder && onCollapse(node.id)}
    >
      {/* ... */}
    </animated.mesh>
  );
};
```

**Impact:** UX delight, no perf hit (instanced skips collapsed).

**Files:** NEW `useFolderCollapse.ts`, `FileCard.tsx` (animation).

---

## Implementation Order

1. **#1 Instancing** (from INSTANCED_MESH_IMPLEMENTATION.md) → unlock #2 Atlas
2. **#4 Foveated LOD** NOW — test zoom-out on 2000 nodes
3. **#2 Texture Atlas** — after instancing works
4. **#5 WebWorker** — when hitting >5k nodes
5. **#3 Sugiyama** — Knowledge Graph mode
6. **#6 Folder Collapse** — UX polish

## Expected Total Impact

| Metric | Before | After All |
|--------|--------|-----------|
| FPS | ~20 | 60+ |
| Draw calls | 2000+ | <10 |
| VRAM | 2GB | 50MB |
| Main thread | Blocked | Free |

---

## FileCard.tsx Current State (from Opus audit)

### Confirmed Issues

| Issue | Status | Lines | Evidence |
|-------|--------|-------|----------|
| **No React.memo** | ❌ PENDING | 1150-1155 | MARKER_111.21_MEMO comment |
| **useFrame per node** | ⚠️ Throttled | 234-284 | 100ms but runs for ALL nodes |
| **Texture 14 deps** | ⚠️ Heavy | 373-703 | Rebuilds on state change |
| **No InstancedMesh** | ❌ Missing | - | Individual mesh per card |
| **LOD system** | ✅ Works | 269-279 | 10 levels implemented |

### Markers Found in Code

- `MARKER_111.21_USEFRAME` (line 254) - Batch LOD updates PENDING
- `MARKER_111.21_TEXTURE` (line 368) - Split texture layers PENDING
- `MARKER_111.21_MEMO` (line 1150) - React.memo PENDING
- `MARKER_111_DRAG` (line 749) - Folder drag with children
