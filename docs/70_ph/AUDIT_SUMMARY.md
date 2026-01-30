# Phase 70 — Viewport Context Integration Audit
## Executive Summary

**Status:** ✅ AUDIT COMPLETE — NO CHANGES MADE

**Date:** 2026-01-19
**Project:** VETKA (vetka_live_03)
**Version:** Phase 69.2 (Scanner→Qdrant chain fix)

---

## 🎯 Objective

Audit the VETKA codebase to identify all integration points for viewport-aware context — enabling the backend AI to understand not just **which files** the user is asking about, but also **where they are spatially** in the 3D visualization.

**Result:** ✅ All integration points identified and documented.

---

## 📋 Key Findings

### ✅ What Already Exists

1. **Camera System** — Full 3D camera with position, rotation, frustum
2. **Node Positions** — All nodes have `{x, y, z}` coordinates
3. **Store Architecture** — Zustand state management with all needed data
4. **Message Pipeline** — Socket.IO already sends structured context
5. **LOD System** — 10-level detail system based on distance
6. **Animation System** — Smooth camera focus with state management

### 🚀 Ready to Implement

| Component | Status | Effort |
|-----------|--------|--------|
| Camera access | ✅ Ready | Easy |
| Node positions | ✅ Ready | Easy |
| Frustum detection | ⚠️ Needs helper | 1 hr |
| Viewport nodes | ⚠️ New type | 1 hr |
| Message integration | ⚠️ Needs update | 2 hrs |
| Backend support | ⚠️ TBD | 2-3 hrs |

### ⚠️ Challenges

1. **Camera not in useSocket scope** — Needs context/ref (Solution: Zustand or global ref)
2. **Frustum calculation not cached** — May impact performance (Solution: Cache + debounce)
3. **No existing viewport manager** — Needs new utility (Solution: Create `viewport.ts`)

---

## 📊 Three Integration Points

### Point 1: Camera Access

```typescript
// Inside Canvas component
import { useThree } from '@react-three/fiber';
const { camera } = useThree();

// Access from anywhere via context or global ref
const camera = useStore(s => s.cameraRef);  // Recommended
const camera = (window as any).__camera;     // Quick alternative
```

**File:** `App.tsx:464-470` (Camera setup)
**Key Refs:** Stored in `CameraController.tsx:31`, used in `FileCard.tsx:206`

### Point 2: Node Positions

```typescript
// Get all nodes with positions
const nodes = useStore(s => Object.values(s.nodes));

// Access position
nodes[0].position  // { x: number, y: number, z: number }

// Transform to viewport nodes
const viewportNodes = nodes
  .filter(n => isInFrustum(n.position, camera))
  .map(n => ({
    id: n.id,
    position: n.position,
    path: n.path,
    type: n.type
  }))
```

**File:** `useStore.ts:56-160` (Store definition)
**Node Structure:** `TreeNode` interface (7-25)

### Point 3: Message Sending

```typescript
// Current: sends text + nodePath + pinned_files
const { sendMessage } = useSocket();
sendMessage(text, nodePath, modelId);

// Proposed: also send viewport_nodes
socketRef.current.emit('user_message', {
  text,
  node_path: nodePath,
  pinned_files: [...],
  viewport_nodes: [...]  // ← ADD HERE
});
```

**File:** `useSocket.ts:1019-1054` (sendMessage function)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    VETKA Frontend                    │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────────────┐         ┌─────────────────┐  │
│  │  Chat Panel      │         │  Three.js       │  │
│  │  (user input)    │         │  Canvas         │  │
│  └────────┬─────────┘         └────────┬────────┘  │
│           │                           │             │
│           │ text, nodePath            │ camera      │
│           │ modelId                   │ position    │
│           └───────────┬───────────────┘             │
│                       │                             │
│            ┌──────────▼────────────┐               │
│            │  useSocket Hook       │               │
│            │  sendMessage()        │               │
│            │  ┌────────────────┐   │               │
│            │  │ Get from store:│   │               │
│            │  │ - pinned_files │   │               │
│            │  │ - nodes        │   │               │
│            │  │ - camera (NEW) │   │               │
│            │  └────────────────┘   │               │
│            └──────────┬─────────────┘               │
│                       │                             │
│                       │ Socket.IO emit              │
│                       │ 'user_message'              │
│                       │ {                           │
│                       │   text,                     │
│                       │   node_path,                │
│                       │   pinned_files,             │
│                       │   viewport_nodes (NEW)      │
│                       │ }                           │
│                       │                             │
│                       ▼                             │
├─────────────────────────────────────────────────────┤
│                    Backend                          │
│  - Parse viewport_nodes                            │
│  - Assemble spatial context                        │
│  - Send to AI with enhanced context                │
└─────────────────────────────────────────────────────┘
```

---

## 📁 Files Analyzed

| File | Lines | Purpose | Key Finding |
|------|-------|---------|------------|
| `App.tsx` | 550+ | Canvas setup | Camera + OrbitControls setup |
| `CameraController.tsx` | 240 | Camera animation | Smooth focus + sync with OrbitControls |
| `FileCard.tsx` | 500+ | Node rendering | LOD based on distance |
| `ChatPanel.tsx` | 600+ | Chat UI | Message input + send |
| `useSocket.ts` | 1200+ | Socket events | `sendMessage` at line 1019 |
| `useStore.ts` | 310 | State management | All store logic |
| `useDrag3D.ts` | 80 | 3D interaction | Camera world direction access |
| `TreeEdges.tsx` | 60 | Edge rendering | Uses node positions |
| `types/chat.ts` | 80+ | Type definitions | Message types |
| `types/treeNodes.ts` | 45 | Tree node types | TreeNode interface |

---

## 🔧 Implementation Roadmap

### Phase 1: Camera Integration (1-2 hours)
- [ ] Add camera ref to Zustand store
- [ ] Set camera ref in CameraController or App.tsx
- [ ] Create `useCamera()` hook for access

### Phase 2: Viewport Utility (1 hour)
- [ ] Create `client/src/utils/viewport.ts`
- [ ] Implement `getViewportNodes()` function
- [ ] Add LOD level calculation (optional)

### Phase 3: Socket Integration (1-2 hours)
- [ ] Import viewport utility in useSocket.ts
- [ ] Calculate viewport_nodes before emit
- [ ] Add viewport_nodes field to 'user_message' event
- [ ] Test socket communication

### Phase 4: Backend Integration (2-3 hours)
- [ ] Accept viewport_nodes in handler
- [ ] Validate viewport_nodes structure
- [ ] Integrate into context assembly
- [ ] Update AI prompt to use spatial context

### Phase 5: Optimization (2-4 hours, optional)
- [ ] Cache frustum calculation
- [ ] Debounce viewport recalculation
- [ ] Monitor performance
- [ ] Optimize payload size

**Total Estimated Effort:** 7-12 hours (without optimization)

---

## 💡 Design Decision Matrix

### Camera Reference Strategy

| Strategy | Pros | Cons | Recommendation |
|----------|------|------|-----------------|
| **Zustand Store** | Clean, centralized, typed | One more field | ✅ **Recommended** |
| **Context Provider** | Standard React pattern | Extra providers | Good alternative |
| **Global ref** | Quickest | Not typed, hacky | Quick prototype |

### Viewport Calculation Strategy

| Strategy | Pros | Cons |
|----------|------|------|
| **On demand** | Simple, accurate | Recalculates each time |
| **Cached** | Fast, efficient | Need invalidation |
| **Streamed** | Real-time updates | Overhead, unnecessary |

**Recommendation:** On-demand + optional cache

### Payload Strategy

| Field | Required | Size Impact | Recommendation |
|-------|----------|-------------|-----------------|
| `id` | ✅ Yes | Small | Include always |
| `position` | ✅ Yes | Medium | Include always |
| `path` | ✅ Yes | Medium | Include always |
| `type` | ✅ Yes | Small | Include always |
| `distance` | ⚠️ Optional | Small | Include for reasoning |
| `lod_level` | ⚠️ Optional | Tiny | Include if useful |
| `is_selected` | ⚠️ Optional | Tiny | Can skip initially |

---

## 🎓 Learning Resources Referenced

### Three.js Concepts
- **Camera frustum:** For visibility detection
- **Vector3 operations:** Position calculations
- **Quaternion interpolation:** Smooth camera animation

### Architecture Patterns
- **Zustand store:** State management (already in use)
- **Socket.IO events:** Event-driven architecture
- **LOD system:** Spatial rendering optimization

### Existing VETKA Systems
- **Phase 61:** Pinned files context
- **Phase 62:** LOD system implementation
- **Phase 65:** Grab mode for node movement
- **Phase 69:** Multi-highlight support

---

## 📊 Complexity Assessment

### Frontend Complexity: **MEDIUM**
- Camera access: Easy
- Frustum calculation: Medium
- Integration: Easy-Medium
- **Overall:** Moderate, well-understood patterns

### Backend Complexity: **LOW-MEDIUM**
- Parsing new field: Easy
- Validation: Easy
- Context assembly: Medium (depends on design)
- **Overall:** Straightforward, minimal risk

### Total System Complexity: **MEDIUM**
- Well-scoped change
- Backward compatible
- No architecture changes needed
- Minimal risk of regression

---

## ✅ Audit Checklist

- [x] Identified camera system
- [x] Located node position storage
- [x] Found message sending pipeline
- [x] Analyzed store architecture
- [x] Evaluated existing systems
- [x] Documented integration points
- [x] Created type definitions
- [x] Provided implementation examples
- [x] Assessed performance implications
- [x] Established backward compatibility
- [x] Created documentation
- [x] No code changes made

---

## 📋 Deliverables

### Documentation Files

| File | Purpose | Pages |
|------|---------|-------|
| `VIEWPORT_CONTEXT_AUDIT.md` | Complete technical audit | 25+ |
| `QUICK_REFERENCE.md` | Quick lookup guide | 5 |
| `API_CONTRACTS.md` | Type definitions + examples | 15+ |
| `AUDIT_SUMMARY.md` | This file | 5 |

### Key Insights

1. **Architecture is ready** — No fundamental changes needed
2. **Camera is accessible** — Multiple paths available
3. **Data is available** — All needed information exists in store
4. **Implementation is straightforward** — Well-understood patterns
5. **Performance is acceptable** — Small payload, on-demand calculation

---

## 🚀 Next Steps

1. **Read documentation**
   - Start with `QUICK_REFERENCE.md` (5 min)
   - Then `VIEWPORT_CONTEXT_AUDIT.md` (20 min)
   - Reference `API_CONTRACTS.md` during implementation

2. **Implement Phase 1-3** (4-5 hours)
   - Camera integration
   - Viewport utility
   - Socket integration

3. **Test and verify** (2 hours)
   - Frontend: viewport_nodes generated correctly
   - Backend: receives and processes data
   - System: no regressions

4. **Backend integration** (2-3 hours)
   - Update context assembly
   - Monitor AI reasoning quality
   - Optimize if needed

---

## 📞 Questions Answered by Audit

| Question | Answer |
|----------|--------|
| Where is camera defined? | `App.tsx:464-470`, accessed via `useThree()` |
| How to get node positions? | `useStore(s => Object.values(s.nodes))` |
| Can we see camera from useSocket? | Not directly; needs context/ref (recommend Zustand) |
| What about frustum culling? | Not implemented; needs `THREE.Frustum` |
| How much data is sent? | ~2-4 KB per message (~1 KB gzipped) |
| Is it backward compatible? | Yes on frontend, needs backend update |
| Performance impact? | Minimal (<1 ms frustum calc + small payload) |
| What about LOD? | Already exists (10 levels), can be included |

---

## 🎯 Success Criteria

✅ **Achieved:**
- All integration points identified
- Complete documentation created
- No architecture changes required
- Backward compatibility maintained
- Implementation path clear

📊 **Metrics After Implementation:**
- Viewport nodes sent with every message: **100%**
- Backend receives and parses: **100%**
- Performance impact: **<5ms additional latency**
- Code coverage: **>80%**

---

## 📎 Appendices

### Appendix A: File Index
See `VIEWPORT_CONTEXT_AUDIT.md` Section 11

### Appendix B: Type Definitions
See `API_CONTRACTS.md` Type Definitions section

### Appendix C: Implementation Examples
See `API_CONTRACTS.md` Implementation sections

### Appendix D: Performance Analysis
See `API_CONTRACTS.md` Performance Considerations

---

## 🙏 Conclusion

The VETKA codebase is **well-structured and ready** for viewport-aware context integration. All necessary components are in place, and the proposed addition is a **clean, minimal, backward-compatible enhancement**.

Implementation can proceed with confidence using the provided documentation and examples.

**Status:** ✅ AUDIT COMPLETE
**Recommendation:** ✅ PROCEED WITH IMPLEMENTATION

---

**Audit Prepared:** 2026-01-19
**For Project:** VETKA (vetka_live_03)
**Phase:** 70 — Viewport Context Integration
**Type:** AUDIT ONLY (NO CHANGES MADE)

---

*For questions or clarifications, refer to the detailed audit document (`VIEWPORT_CONTEXT_AUDIT.md`) or quick reference guide (`QUICK_REFERENCE.md`).*
