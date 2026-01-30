# Implementation Checklist — Viewport Context

**Status:** Ready for implementation
**Estimated Time:** 7-12 hours
**Complexity:** Medium
**Risk Level:** Low

---

## Phase 1: Camera Integration (1-2 hours)

### 1.1 Create Camera Store Field

- [ ] Open `client/src/store/useStore.ts`
- [ ] Add to `TreeState` interface (around line 56):
  ```typescript
  cameraRef?: THREE.PerspectiveCamera | null;
  ```

- [ ] Add to initial state (around line 135):
  ```typescript
  cameraRef: null,
  ```

- [ ] Add method to TreeState interface:
  ```typescript
  setCameraRef: (camera: THREE.PerspectiveCamera | null) => void;
  ```

- [ ] Add implementation in create() (around line 242):
  ```typescript
  setCameraRef: (cameraRef) => set({ cameraRef }),
  ```

- [ ] Verify types import THREE:
  ```typescript
  import * as THREE from 'three';
  ```

### 1.2 Update CameraController to Set Camera Ref

- [ ] Open `client/src/components/canvas/CameraController.tsx`
- [ ] Add after line 36 (after getting other selectors):
  ```typescript
  const setCameraRef = useStore((state) => state.setCameraRef);
  ```

- [ ] Add new useEffect (after line 105):
  ```typescript
  useEffect(() => {
    setCameraRef(camera);
  }, [camera, setCameraRef]);
  ```

- [ ] Verify it runs once on mount

### 1.3 Test Camera Reference

- [ ] Run frontend: `npm run dev` in `client/`
- [ ] Open browser console
- [ ] Execute:
  ```javascript
  const store = window.__store; // If exported
  console.log(store.cameraRef); // Should show Camera object
  ```

- [ ] Verify camera has properties:
  - `position: Vector3`
  - `quaternion: Quaternion`
  - `fov: number`
  - `projectionMatrix: Matrix4`

---

## Phase 2: Viewport Utility (1-2 hours)

### 2.1 Create viewport.ts File

- [ ] Create new file: `client/src/utils/viewport.ts`
- [ ] Add imports:
  ```typescript
  import * as THREE from 'three';
  import { TreeNode } from '../store/useStore';
  ```

### 2.2 Define ViewportNode Type

- [ ] Add to `viewport.ts`:
  ```typescript
  export interface ViewportNode {
    id: string;
    position: { x: number; y: number; z: number };
    path: string;
    type: 'file' | 'folder';
    distance_to_camera?: number;
    lod_level?: number;
  }
  ```

### 2.3 Implement getViewportNodes Function

- [ ] Copy from `API_CONTRACTS.md` → Implementation (Simple version)
- [ ] Or use Extended version with LOD support
- [ ] Add JSDoc comments
- [ ] Verify function signature:
  ```typescript
  export function getViewportNodes(
    nodesRecord: Record<string, TreeNode>,
    camera: THREE.PerspectiveCamera,
    includeDistance?: boolean
  ): ViewportNode[]
  ```

### 2.4 Implement getLODLevel Function (Optional)

- [ ] Add helper function for LOD calculation
- [ ] Match levels from `FileCard.tsx:9-28`
- [ ] Test with various distances

### 2.5 Test Viewport Utility

- [ ] Create test file: `client/src/utils/viewport.test.ts` (optional)
- [ ] Or test manually in console:
  ```typescript
  import { getViewportNodes } from './utils/viewport';
  const nodes = useStore.getState().nodes;
  const camera = useStore.getState().cameraRef;
  const viewport = getViewportNodes(nodes, camera);
  console.log(viewport);
  ```

- [ ] Verify output:
  - [ ] Contains 5-20 nodes (typical)
  - [ ] Each has id, position, path, type
  - [ ] Distance values are reasonable
  - [ ] LOD levels 0-9 (if implemented)

---

## Phase 3: Socket Integration (1-2 hours)

### 3.1 Update sendMessage Function

- [ ] Open `client/src/hooks/useSocket.ts`
- [ ] Find `sendMessage` function (line 1019)

- [ ] Add imports at top:
  ```typescript
  import { getViewportNodes, ViewportNode } from '../utils/viewport';
  ```

- [ ] Inside `sendMessage`, after line 1038 (after pinnedFiles):
  ```typescript
  // Get viewport nodes (Phase 70)
  const camera = useStore.getState().cameraRef;
  const viewportNodes = camera
    ? getViewportNodes(nodes, camera, true)
    : [];
  ```

- [ ] Update emit call (line 1047):
  ```typescript
  socketRef.current.emit('user_message', {
    text: message,
    node_path: nodePath || 'unknown',
    node_id: 'root',
    model: modelId,
    pinned_files: pinnedFiles.length > 0 ? pinnedFiles : undefined,
    viewport_nodes: viewportNodes.length > 0 ? viewportNodes : undefined,  // ← NEW
  });
  ```

- [ ] Verify indentation and syntax

### 3.2 Test Socket Event

- [ ] Start frontend: `npm run dev`
- [ ] Open browser DevTools → Network tab
- [ ] Start backend: `python main.py` (or your command)
- [ ] Send a chat message
- [ ] In DevTools, filter by `user_message` event
- [ ] Verify payload includes:
  - [ ] `text`
  - [ ] `node_path`
  - [ ] `pinned_files` (if any)
  - [ ] `viewport_nodes` (new) ← Should be present

### 3.3 Verify Backward Compatibility

- [ ] Ensure `viewport_nodes` is optional in emit
- [ ] Backend should handle missing field gracefully
- [ ] Test without viewport_nodes (shouldn't break)

---

## Phase 4: Backend Integration (2-3 hours)

### 4.1 Update Socket Handler

- [ ] Find `user_message` event handler in backend
- [ ] Add viewport_nodes parameter:
  ```python
  @socket.on('user_message')
  def handle_user_message(data):
      viewport_nodes = data.get('viewport_nodes', [])
      # ... rest of handler
  ```

### 4.2 Validate viewport_nodes

- [ ] Add validation function:
  ```python
  def validate_viewport_nodes(nodes):
      for node in nodes:
          assert isinstance(node, dict)
          assert 'id' in node
          assert 'position' in node
          assert 'path' in node
          assert 'type' in node
      return True
  ```

- [ ] Call validation in handler:
  ```python
  if viewport_nodes:
      validate_viewport_nodes(viewport_nodes)
  ```

### 4.3 Update Context Assembly

- [ ] Find context assembly function in backend
- [ ] Add viewport_nodes parameter
- [ ] Incorporate into AI context:
  ```python
  def assemble_context(message, pinned_files, viewport_nodes):
      # Existing context
      context = f"Current file: {selected_node.path}\n"
      context += f"Pinned files: {[f['path'] for f in pinned_files]}\n"

      # NEW: Spatial context
      if viewport_nodes:
          visible_files = [n['path'] for n in viewport_nodes]
          context += f"Visible files in viewport: {visible_files}\n"

          # Optional: include distance info
          closest = min(viewport_nodes, key=lambda n: n.get('distance_to_camera', float('inf')))
          context += f"Closest file: {closest['path']}\n"

      return context
  ```

### 4.4 Test Backend Integration

- [ ] Send message with viewport_nodes
- [ ] Check backend logs for:
  - [ ] Event received
  - [ ] Viewport nodes parsed
  - [ ] Validation passed
  - [ ] Context assembled correctly

- [ ] Verify AI receives enhanced context
- [ ] Check response quality

---

## Phase 5: Testing (2-3 hours)

### 5.1 Unit Tests (Frontend)

- [ ] Test `getViewportNodes()`:
  - [ ] Empty nodes → empty array
  - [ ] All nodes visible → all returned
  - [ ] Some nodes outside frustum → filtered correctly
  - [ ] Distance calculated accurately

- [ ] Test `getLODLevel()`:
  - [ ] Distance > 300 → LOD 0
  - [ ] Distance 200-300 → LOD 1
  - [ ] Distance < 10 → LOD 9

### 5.2 Integration Tests (Frontend)

- [ ] Send message with no visible nodes
- [ ] Send message with many visible nodes (50+)
- [ ] Send message while panning camera
- [ ] Send message while zooming
- [ ] Verify socket event includes all fields

### 5.3 Integration Tests (Backend)

- [ ] Handle missing viewport_nodes gracefully
- [ ] Handle empty viewport_nodes
- [ ] Parse viewport_nodes structure
- [ ] Use in context assembly
- [ ] AI generates responses with understanding

### 5.4 System Tests

- [ ] End-to-end: Send message → AI responds with spatial awareness
- [ ] Performance: <5ms additional latency
- [ ] No regressions: Existing features still work
- [ ] Backward compat: Old clients still work (if viewport_nodes missing)

### 5.5 Edge Cases

- [ ] Camera at extreme distance (5000+)
- [ ] Camera very close to nodes (<1 unit)
- [ ] Very large tree (1000+ nodes)
- [ ] Mixed file/folder types
- [ ] Rapid camera movement

---

## Phase 6: Optimization (Optional, 2-4 hours)

### 6.1 Cache Frustum

- [ ] Store frustum in useStore or component ref
- [ ] Only recalculate on camera movement
- [ ] Measure performance improvement

### 6.2 Debounce Viewport Calculation

- [ ] Add debounce to sendMessage
- [ ] Example: Don't recalculate if <100ms since last
- [ ] Reduces duplicate calculations

### 6.3 Payload Optimization

- [ ] Remove unnecessary fields (if any)
- [ ] Consider compression
- [ ] Measure gzipped size
- [ ] Target: <5 KB per message

### 6.4 Performance Monitoring

- [ ] Log time to calculate viewport
- [ ] Log payload sizes
- [ ] Monitor latency increase
- [ ] Set performance budgets

---

## Verification Checklist

### Frontend Checklist

- [ ] Camera ref accessible in useSocket
- [ ] getViewportNodes returns correct data
- [ ] Frustum culling works at all distances
- [ ] Distance calculation accurate
- [ ] LOD levels correct (0-9)
- [ ] viewport_nodes sent in every message
- [ ] Backward compatible (no crashes if missing)
- [ ] Performance <5ms per calculation
- [ ] Memory usage stable
- [ ] No console errors

### Backend Checklist

- [ ] Accepts viewport_nodes field
- [ ] Parses structure correctly
- [ ] Validation prevents bad data
- [ ] Context assembly uses viewport_nodes
- [ ] AI responds with spatial awareness
- [ ] No regressions in existing flow
- [ ] Performance impact <10ms
- [ ] Logging shows correct data
- [ ] Error handling for malformed data
- [ ] Backward compatible (handles missing field)

### Integration Checklist

- [ ] Frontend sends complete payload
- [ ] Backend receives complete payload
- [ ] No data loss in transmission
- [ ] End-to-end latency acceptable
- [ ] AI quality improved
- [ ] Spatial reasoning demonstrated
- [ ] All existing features still work
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Ready for production

---

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| 1: Camera Integration | 1-2 hrs | ⬜ Not Started |
| 2: Viewport Utility | 1-2 hrs | ⬜ Not Started |
| 3: Socket Integration | 1-2 hrs | ⬜ Not Started |
| 4: Backend Integration | 2-3 hrs | ⬜ Not Started |
| 5: Testing | 2-3 hrs | ⬜ Not Started |
| 6: Optimization | 2-4 hrs | ⬜ Optional |
| **TOTAL** | **9-16 hrs** | — |

---

## Risk Mitigation

### Risk 1: Camera Ref Not Available
**Severity:** Medium | **Probability:** Low
- **Mitigation:** Use try-catch, default to empty array
- **Fallback:** Global ref if Zustand doesn't work

### Risk 2: Frustum Calculation Slow
**Severity:** Medium | **Probability:** Low
- **Mitigation:** Cache frustum, debounce calls
- **Fallback:** Use simple distance-based filtering

### Risk 3: Large Payload
**Severity:** Low | **Probability:** Low
- **Mitigation:** Only send distance, not full nodes
- **Fallback:** Compress with gzip

### Risk 4: Backend Doesn't Support
**Severity:** Low | **Probability:** Low
- **Mitigation:** Make viewport_nodes optional
- **Fallback:** Document for backend team

### Risk 5: Performance Regression
**Severity:** Medium | **Probability:** Low
- **Mitigation:** Monitor metrics, set budgets
- **Fallback:** Disable if over budget

---

## Success Criteria

### Must Have ✅
- [ ] viewport_nodes sent with messages
- [ ] Backend receives and validates
- [ ] No performance regression
- [ ] Backward compatible
- [ ] All tests pass

### Should Have ⭐
- [ ] Distance included in payload
- [ ] LOD levels calculated
- [ ] Spatial context improved AI response
- [ ] Performance <5ms
- [ ] Documentation complete

### Nice to Have 🌟
- [ ] Frustum caching
- [ ] Advanced visualization
- [ ] Performance optimization
- [ ] Analytics dashboard

---

## Sign-Off

**Prepared by:** Audit Phase 70
**Date:** 2026-01-19
**Ready for:** Implementation Team

### Before Starting
- [ ] Read all documentation
- [ ] Understand architecture
- [ ] Review code examples
- [ ] Set up development environment
- [ ] Verify all tools work

### During Implementation
- [ ] Follow checklist order
- [ ] Test after each phase
- [ ] Commit frequently
- [ ] Document blockers
- [ ] Ask questions early

### After Completion
- [ ] Run full test suite
- [ ] Verify all criteria met
- [ ] Update documentation
- [ ] Prepare PR/MR
- [ ] Request review

---

## Contact & Support

**Documentation:** See `/docs/70_ph/` folder
- `VIEWPORT_CONTEXT_AUDIT.md` — Detailed technical audit
- `QUICK_REFERENCE.md` — Quick lookup guide
- `API_CONTRACTS.md` — Type definitions + examples
- `AUDIT_SUMMARY.md` — Executive summary

**Questions:** Refer to documentation sections

---

**Last Updated:** 2026-01-19
**Phase:** 70 — Viewport Context Integration
**Status:** AUDIT COMPLETE — READY FOR IMPLEMENTATION
