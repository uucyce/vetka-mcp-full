# Viewport Context Integration — Quick Reference

## 🚀 TL;DR

Three key integration points for viewport-aware context:

```
Camera Access: useThree().camera
Node Positions: useStore(s => s.nodes)
Message Send: useSocket().sendMessage(text, nodePath, modelId)
```

---

## 1️⃣ Get Camera

```typescript
import { useThree } from '@react-three/fiber';

export function MyComponent() {
  const { camera } = useThree();

  // ✅ Use camera
  const position = camera.position;  // Vector3
  const direction = camera.getWorldDirection(new THREE.Vector3());
}
```

**Location:** Must be used inside `<Canvas>` children
**File:** `App.tsx:464-518`

---

## 2️⃣ Get All Nodes with Positions

```typescript
import { useStore } from '../store/useStore';

export function MyComponent() {
  // Get all nodes
  const nodes = useStore(s => Object.values(s.nodes));

  // Access positions
  nodes.forEach(node => {
    console.log(`${node.name}: x=${node.position.x}, y=${node.position.y}, z=${node.position.z}`);
  });
}
```

**Structure:** `{ x: number, y: number, z: number }`
**Store:** `client/src/store/useStore.ts`

---

## 3️⃣ Get Visible Nodes (Frustum)

```typescript
import { useThree } from '@react-three/fiber';
import { useStore } from '../store/useStore';
import * as THREE from 'three';

function getVisibleNodes() {
  const { camera } = useThree();
  const nodes = useStore(s => Object.values(s.nodes));

  // Create frustum
  const frustum = new THREE.Frustum();
  frustum.setFromProjectionMatrix(
    new THREE.Matrix4().multiplyMatrices(
      camera.projectionMatrix,
      camera.matrixWorldInverse
    )
  );

  // Filter visible nodes
  return nodes.filter(node => {
    const point = new THREE.Vector3(
      node.position.x,
      node.position.y,
      node.position.z
    );
    return frustum.containsPoint(point);
  });
}
```

---

## 4️⃣ Get Distance to Camera

```typescript
const dist = camera.position.distanceTo(
  new THREE.Vector3(node.position.x, node.position.y, node.position.z)
);
```

**Already used in:** `FileCard.tsx:206`

---

## 5️⃣ Send Message with Context

```typescript
import { useSocket } from '../hooks/useSocket';
import { useStore } from '../store/useStore';

export function ChatPanel() {
  const { sendMessage } = useSocket();
  const selectedNode = useStore(s => s.selectedId ? s.nodes[s.selectedId] : null);

  const handleSend = (text: string) => {
    sendMessage(
      text,
      selectedNode?.path,
      modelId
    );
  };
}
```

**Current params:** `text`, `nodePath`, `modelId`
**Backend also receives:** `pinned_files` (Phase 61)
**Location:** `useSocket.ts:1019-1054`

---

## 6️⃣ Pinned Files

```typescript
const pinnedFileIds = useStore(s => s.pinnedFileIds);
const nodes = useStore(s => s.nodes);

const pinnedNodes = pinnedFileIds
  .map(id => nodes[id])
  .filter(Boolean);
```

**Methods:**
- `togglePinFile(nodeId)`
- `pinSubtree(rootId)`
- `pinNodeSmart(nodeId)` ← Recommended
- `clearPinnedFiles()`

---

## 7️⃣ Focus Camera on Node

```typescript
import { useStore } from '../store/useStore';

const setCameraCommand = useStore(s => s.setCameraCommand);

setCameraCommand({
  target: 'main.py',          // filename or path
  zoom: 'medium',             // 'close' | 'medium' | 'far'
  highlight: true
});

// Camera animates automatically
// OrbitControls synced
// Chat context switched
```

**Location:** `CameraController.tsx:107-182`

---

## 8️⃣ OrbitControls Reference

```typescript
const controls = (window as any).__orbitControls;

if (controls) {
  console.log('Position:', controls.object.position);
  console.log('Target:', controls.target);
  console.log('Distance:', controls.getDistance());

  // Disable/enable
  controls.enabled = false;
}
```

**Set in:** `App.tsx:482`

---

## 📊 Data Flow

```
User types in ChatPanel
    ↓
sendMessage(text, nodePath, modelId)
    ↓
Backend receives event with:
  - text
  - node_path
  - model
  - pinned_files
  - (NEW) viewport_nodes ← ADD HERE
    ↓
Backend uses context for AI
```

---

## 🎯 To Add viewport_nodes

**File:** `client/src/hooks/useSocket.ts`
**Function:** `sendMessage` (line 1019)
**After line:** 1038 (after pinnedFiles)
**Before emit:** line 1047

```typescript
// Add here:
const viewport_nodes = getViewportNodes(nodes, camera);

// Then in emit:
socketRef.current.emit('user_message', {
  text: message,
  node_path: nodePath || 'unknown',
  node_id: 'root',
  model: modelId,
  pinned_files: pinnedFiles.length > 0 ? pinnedFiles : undefined,
  viewport_nodes: viewport_nodes.length > 0 ? viewport_nodes : undefined,  // ← NEW
});
```

---

## 🏗️ Architecture Summary

```
Store (Zustand)
├── nodes: Record<string, TreeNode>
│   └── position: {x, y, z}
├── pinnedFileIds: string[]
├── selectedId: string | null
└── cameraCommand: CameraCommand | null

Canvas (@react-three/fiber)
├── Camera (PerspectiveCamera)
│   ├── position: Vector3
│   ├── fov: 60°
│   └── frustum: Frustum
├── OrbitControls
│   └── stored in window.__orbitControls
└── FileCards
    ├── LOD based on distance
    └── position from store

Socket Events
└── user_message
    ├── text
    ├── node_path
    ├── model
    ├── pinned_files (Phase 61)
    └── viewport_nodes (Phase 70 ← NEW)
```

---

## 📍 File Locations

| What | Where |
|------|-------|
| Camera setup | `App.tsx:464-470` |
| Canvas render loop | `App.tsx:503-517` |
| Camera animation | `CameraController.tsx` |
| Message sending | `useSocket.ts:1019-1054` |
| Store definition | `useStore.ts:56-310` |
| Node types | `types/chat.ts`, `types/treeNodes.ts` |

---

## ✅ Checklist

- [ ] Understand camera access via useThree()
- [ ] Know where nodes are stored (useStore)
- [ ] Understand sendMessage flow
- [ ] Know how pinned files work
- [ ] Understand camera focus mechanism
- [ ] Know OrbitControls integration
- [ ] Ready to add viewport_nodes

---

**Phase 70 — Viewport Context Audit**
**Status:** AUDIT COMPLETE - READY FOR IMPLEMENTATION
