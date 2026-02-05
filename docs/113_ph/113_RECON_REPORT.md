# Phase 113.1 + 113.2: Unified Reconnaissance Report

**Date:** 2026-02-05
**Commander:** Claude Opus 4.6
**Scouts:** 9 Haiku + Grok research + 3 Sonnet verifiers

---

## EXECUTIVE SUMMARY

| Phase | Task | Status | Risk |
|-------|------|--------|------|
| **113.1** | Persistent Spatial Memory | READY | LOW |
| **113.2** | Smooth Drag Physics | READY | LOW-MEDIUM |

**Key finding:** All infrastructure exists. No new dependencies needed.
Zero-dep implementation using existing patterns (useFrame, refs, localStorage).

---

## GROK vs SONNET: Verification Matrix

| Grok Claim | Sonnet Verdict | Score |
|------------|---------------|-------|
| Manual save > persist middleware | CONFIRMED | 10/10 |
| useTreeData loads flat API -> calculateSimpleLayout | PARTIALLY CORRECT (Phase 111 disabled fallback) | 6/10 |
| Extend layout_socket_handler.py for positions | CONFIRMED (perfect insertion point) | 10/10 |
| localStorage 5MB ok for 1700 nodes | CONFIRMED (144KB = 2.8% of limit) | 10/10 |
| 500ms debounce during drag | PARTIALLY CORRECT (save on pointerUp, not during drag) | 7/10 |
| @react-spring/three is WINNER | WRONG (not installed, not needed, arch mismatch) | 2/10 |
| stiffness:400, damping:40 optimal | SPECULATIVE (no codebase basis, use k=0.15/friction=0.9) | 4/10 |
| useDrag from drei | WRONG (drei v10 has no useDrag, custom useDrag3D exists) | 2/10 |
| useChain for cascade children | DISASTER (1700 nodes = perf death) | 1/10 |
| Install zustand@^5.0.0-rc | WRONG (unnecessary, current version works) | 1/10 |

**Grok overall: 5.3/10** — Good on persistence, bad on physics.

---

## ACTUAL ARCHITECTURE (from Sonnets)

### Data Flow (current)
```
Backend fan_layout.py → positions calculated
  ↓
API /tree/data → { tree: { nodes: [...] } }
  ↓
useTreeData.ts:73 → convertApiResponse() → TreeNode[]
  (Phase 111: backend positions PRESERVED, no fallback recalc)
  ↓
useStore.ts:169 → Zustand store, nodes: Record<string, TreeNode>
  TreeNode.position: { x: number, y: number, z: number }
  ↓
App.tsx:119 → position={[node.position.x, node.position.y, node.position.z]}
  FrustumCulledNodes: only visible nodes render (50-80% culled)
  ↓
FileCard.tsx → mesh at position=[x,y,z]
  Drag: handlePointerMove → meshRef.current.position.copy(newPos) [INSTANT]
  Store: moveNodeWithChildren(id, {x,y,z}) or updateNodePosition(id, {x,y,z})
  ↓
  LOST ON RELOAD (no persistence!)
```

### Key Files & Line Numbers

| File | What | Key Lines |
|------|------|-----------|
| `client/src/store/useStore.ts` | Zustand store, 409 lines | L169: create(), L232-293: position functions |
| `client/src/components/canvas/FileCard.tsx` | 3D cards, drag system | L750-776: pointerDown, L778-803: pointerMove, L805-816: pointerUp, L791: **position.copy** (instant snap) |
| `client/src/hooks/useTreeData.ts` | API → store data flow | L73: convertApiResponse, L161: Phase 111 fallback disabled |
| `client/src/App.tsx` | Rendering pipeline | L119: position prop, L49-132: FrustumCulledNodes |
| `client/src/utils/lod.ts` | LOD system (10 levels) | Phase 112.6-112.8: Foveated Spot |
| `src/api/handlers/layout_socket_handler.py` | Backend layout config, 143 lines | L24-31: _layout_config dict, L69-141: socket handlers |
| `client/src/store/roleStore.ts` | ONLY file with Zustand persist | L12: persist middleware example |
| `client/src/hooks/useDrag3D.ts` | Custom drag hook (Phase 96) | 90 lines, Ctrl+drag support |

### Existing Animation Patterns
- **Opacity lerp:** FileCard.tsx:269-286 → `opacityDelta * 0.1` (useFrame, per-frame)
- **Camera lerp:** CameraController.tsx:280 → `lerp(current, target, 0.1)`
- **No spring/velocity/damping code exists** anywhere in client/src/
- **GSAP installed** (package.json) but NOT used for 3D
- **framer-motion installed** but NOT used for 3D

---

## IMPLEMENTATION PLAN

### Phase 113.1: Persistent Spatial Memory

**Approach:** Hybrid — localStorage (immediate) + backend API (debounced)

**Why hybrid:**
- localStorage: instant restore on reload, offline-first, 144KB for 1700 nodes
- Backend: multi-device sync, survives browser clear, Qdrant integration later

**Changes:**

#### 1. useStore.ts — Add persistence actions
- Insert after line 167 (before `create()`)
- Add `PositionMap` type, `STORAGE_KEY`, debounced backend saver
- Add `savePositions()` action: localStorage immediate + fetch debounced
- Add `loadPositions()` action: read localStorage → merge into nodes

#### 2. FileCard.tsx — Hook up save on drag end
- Line 805 (handlePointerUp): add `useStore.getState().savePositions()`

#### 3. useTreeData.ts — Load saved positions after tree load
- After `setNodesFromRecord()`: call `loadPositions()`
- Merge strategy: saved positions override API positions for existing nodes
- New nodes (not in saved layout) keep their API-calculated positions

#### 4. layout_socket_handler.py — Backend endpoint
- Add `save_positions` / `load_positions` socket handlers
- Persist to `data/node_positions.json`

**Merge strategy:**
```
API returns: { node_A: pos1, node_B: pos2, node_C: pos3 }
Saved:       { node_A: pos_saved, node_B: pos_saved }
Result:      { node_A: pos_saved, node_B: pos_saved, node_C: pos3 }
             (saved wins, new nodes keep API position)
```

---

### Phase 113.2: Smooth Drag Physics

**Approach:** Raw useFrame spring math (matches existing lerp patterns, zero deps)

**Why NOT @react-spring:**
- Not installed (16KB new dep)
- Architecture mismatch (VETKA = imperative refs, react-spring = declarative)
- useChain cascade = disaster for 200-child folders
- Raw math matches existing opacity lerp pattern

**Spring constants:**
- `k = 0.15` (spring stiffness per frame)
- `friction = 0.9` (10% velocity decay per frame)
- `settleThreshold = 0.01` (distance) + `0.001` (velocity)

**Changes:**

#### 1. FileCard.tsx — Add spring refs (after line 268)
```typescript
const velocity = useRef(new THREE.Vector3(0, 0, 0));
const targetPosition = useRef(new THREE.Vector3());
const isSettling = useRef(false);
```

#### 2. FileCard.tsx — Modify handlePointerMove (line 791)
```
BEFORE: meshRef.current.position.copy(newPos)  // instant snap
AFTER:  targetPosition.current.copy(newPos)     // set spring target
```

#### 3. FileCard.tsx — Add spring logic to useFrame (after line 286)
- Read targetPosition, calculate delta
- Apply spring force: `delta * 0.15`
- Apply friction: `velocity * 0.9`
- Move mesh: `position += velocity`
- Throttled store sync: every 100ms during drag
- Settle detection: snap when close enough

#### 4. FileCard.tsx — Modify handlePointerUp (line 805)
- Final position sync to store
- Trigger settle animation (node glides to rest)
- Call `savePositions()` (113.1 tie-in)

**Folder strategy:** Spring ONLY on parent, children instant-follow via delta.
- 1 spring calc per folder drag (not 200 springs for children)
- Children move by same delta as parent each frame
- Visually: folder "leads", children "follow" rigidly (natural feel)

---

## RISKS & MITIGATIONS

| Risk | Level | Mitigation |
|------|-------|------------|
| Race condition: API refresh during drag | MEDIUM | Timestamp merge (saved > API if newer) |
| Ghost positions (deleted files) | LOW | Prune orphans on tree load |
| localStorage quota | LOW | try/catch, 144KB << 5MB limit |
| Spring + frustum culling | LOW | Spring runs in useFrame (per-mesh), culled nodes don't animate |
| Folder drag perf (200 children) | LOW | Spring only parent, children instant-follow |
| Multi-tab position conflict | LOW | Last-write-wins (acceptable for now) |

---

## NOT DOING (Grok's bad suggestions)

- ~~Install @react-spring/three~~ (not needed, arch mismatch)
- ~~Install zustand@^5.0.0-rc~~ (current version works)
- ~~useChain for cascade~~ (perf disaster)
- ~~useDrag from drei~~ (doesn't exist, custom hook exists)
- ~~Persist middleware~~ (would serialize entire store 60x/sec)

---

## FILES TO MODIFY

| # | File | Action | Est. Lines |
|---|------|--------|------------|
| 1 | `client/src/store/useStore.ts` | Add savePositions/loadPositions | +50 |
| 2 | `client/src/components/canvas/FileCard.tsx` | Spring refs + useFrame + drag changes | +40 |
| 3 | `client/src/hooks/useTreeData.ts` | Call loadPositions after tree load | +5 |
| 4 | `src/api/handlers/layout_socket_handler.py` | Add position save/load handlers | +40 |

**Total: ~135 lines across 4 files. Zero new dependencies.**

---

*Report compiled from 9 Haiku scouts + Grok research + 3 Sonnet verifiers.*
*Ready for implementation after перекур.*
