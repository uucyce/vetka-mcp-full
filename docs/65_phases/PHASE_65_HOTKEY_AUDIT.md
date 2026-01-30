# 🔍 Phase 65: Hotkey Refactoring Audit
**READ-ONLY ANALYSIS REPORT**

---

## 📋 CURRENT HOTKEY MAP

| Action | Key Combo | File | Line | Current Behavior |
|--------|-----------|------|------|------------------|
| **Select node** | Click | FileCard.tsx | 527 | Selects node, fires onClick callback |
| **Pin single file** | Ctrl+Click or Cmd+Click | FileCard.tsx | 501-502 | Toggles `pinnedFileIds` (single file) |
| **Pin entire subtree** | Alt+Click | FileCard.tsx | 507-508 | Calls `pinSubtree(id)` - pins all descendants |
| **Drag node** | Shift+Click + Drag | FileCard.tsx:495-496 + useDrag3D.ts:22 | Multiple | Moves node in 3D space |
| **Rotate camera** | Drag (no modifier) | OrbitControls in App.tsx:421 | 421-436 | Built-in Three.js orbit controls |
| **Pan camera** | Shift+Drag | OrbitControls + useDrag3D.ts | App.tsx:428 | Camera pan disabled when node dragging active |

---

## 🌳 NODE STRUCTURE

### TreeNode Interface
**Location:** `client/src/store/useStore.ts:7-25`

```typescript
export interface TreeNode {
  id: string;
  path: string;
  name: string;
  type: 'file' | 'folder';           // Distinguishes files from folders
  backendType: VetkaNodeType;        // 'root' | 'branch' | 'leaf'
  depth: number;
  parentId: string | null;           // Parent reference
  position: { x: number; y: number; z: number };
  color: string;
  extension?: string;
  semanticPosition?: {
    x: number;
    y: number;
    z: number;
    knowledgeLevel: number;
  };
  children?: string[];               // Child node IDs
}
```

### Parent-Child Relationship Pattern
- **Parent stored as:** `node.parentId` (direct reference)
- **Children identified by:** Looking up all nodes where `node.parentId === targetId`
- **Children collection method:** Recursive walk in `pinSubtree()` at useStore.ts:230-251

### How pinSubtree() Works (Line 230-251)
```typescript
pinSubtree: (rootId) => set((state) => {
  const newPinned = new Set(state.pinnedFileIds);

  // Recursive helper to collect all descendants (files only)
  const addDescendants = (id: string) => {
    const node = state.nodes[id];
    if (!node) return;

    // Pin leaf nodes (files)
    if (node.type === 'file') {
      newPinned.add(id);
    }

    // Find children by parentId
    Object.values(state.nodes)
      .filter(n => n.parentId === id)
      .forEach(child => addDescendants(child.id));
  };

  addDescendants(rootId);
  return { pinnedFileIds: [...newPinned] };
}),
```

**Key Insight:** Only leaf nodes (type='file') get pinned, not folders. Folders act as collection points.

---

## 📁 FILES FOR PHASE 65 REFACTORING

### 1. FileCard.tsx - Click Handler
**Location:** `client/src/components/canvas/FileCard.tsx`

#### Current State (Lines 493-516)
```
Line 493:   const handleClick = useCallback(
Line 495:     if (e.shiftKey) return;        // Block selection if Shift+Click
Line 496:     e.stopPropagation();
Line 498:
Line 501:     if (e.ctrlKey || e.metaKey) {  // Ctrl/Cmd+Click = toggle single pin
Line 502:       togglePinFile(id);
Line 503:       return;
Line 504:     }
Line 506:     // Alt+Click = Pin entire subtree (for folders)
Line 507:     if (e.altKey) {
Line 508:       pinSubtree(id);
Line 509:       return;
Line 510:     }
Line 512:     // Normal click = Select (existing behavior)
Line 513:     onClick?.();
Line 514:   },
```

#### Shift+Click Drag Handler (Lines 435-468)
```
Line 435:   const handlePointerDown = useCallback((e: any) => {
Line 436:     e.stopPropagation();
Line 463:     if (e.shiftKey && e.button === 0) {
Line 464:       setIsDragging(true);
Line 465:       setDraggingAny(true);
Line 466:     }
```

### 2. useDrag3D.ts - 3D Drag Hook
**Location:** `client/src/hooks/useDrag3D.ts:1-74`

#### Key Line (22)
```typescript
if (!e.shiftKey) return;  // Only allow drag if Shift is held
```

This hook is used by FileCard to handle node position updates. Currently checks for Shift+PointerDown.

### 3. useStore.ts - State Management
**Location:** `client/src/store/useStore.ts:80-254`

#### Pin State (Lines 84, 143)
```typescript
pinnedFileIds: string[];  // Line 84 - State declaration
pinnedFileIds: [],        // Line 143 - Initial value
```

#### Pin Actions (Lines 118-120)
```typescript
togglePinFile: (nodeId: string) => void;   // Single file toggle
pinSubtree: (rootId: string) => void;      // Subtree all descendants
clearPinnedFiles: () => void;              // Clear all
```

#### Implementation (Lines 224-253)
- **togglePinFile** (224-228): Adds/removes single node ID
- **pinSubtree** (230-251): Recursively adds all file descendants
- **clearPinnedFiles** (253): Empties the array

### 4. App.tsx - Camera & OrbitControls
**Location:** `client/src/App.tsx:415-549`

#### OrbitControls Configuration (Lines 421-436)
```typescript
<OrbitControls
  ref={(controls) => {
    if (controls) {
      (window as any).__orbitControls = controls;  // Global ref
    }
  }}
  enabled={!isDraggingAny}          // IMPORTANT: Disabled during node drag
  enableDamping
  dampingFactor={0.05}
  enableZoom={true}
  zoomSpeed={1.2}
  minDistance={50}                   // Can get very close
  maxDistance={5000}                 // Can zoom far out
  target={[0, 200, 0]}
/>
```

#### UI Help Text (Line 549)
```
"Click=Select • Drag=Rotate • Shift+Drag=Move"
```

### 5. CameraController.tsx - Camera Animation
**Location:** `client/src/components/canvas/CameraController.tsx:1-160`

**Status:** Handles camera focus animations. NOT directly involved in hotkeys.
Uses `window.__orbitControls` set in App.tsx.

### 6. ChatPanel.tsx - UI Display of Pinned Files
**Location:** `client/src/components/chat/ChatPanel.tsx:42-1073`

#### Pinned Files Display (Lines 1004-1073)
- Shows up to 8 pinned file badges
- Toggle pin via click on badge (line 1057)
- Shows count of additional pinned files

---

## ⚠️ DEPENDENCIES & CONFLICTS

### Camera Controls - CRITICAL DEPENDENCY
**File:** `client/src/App.tsx:421-436`

| Control | Current Use | Modifier | Risk if Changed |
|---------|-------------|----------|-----------------|
| **Drag** | Camera Orbit/Rotate | None | PRIMARY interaction - HIGH |
| **Shift+Drag** | Node Movement (via useDrag3D) | Shift | Custom handling - LOW |
| **OrbitControls.enabled** | Set to `!isDraggingAny` | -- | Disables camera during node drag - CRITICAL |

**Critical Issue:** When `isDraggingAny = true`, OrbitControls is DISABLED. This prevents accidental camera rotation during node movement.

### Existing Pin Logic
**File:** `client/src/store/useStore.ts:224-253`

**Current Actions:**
- `togglePinFile(nodeId)` - add/remove single file
- `pinSubtree(rootId)` - add all file descendants recursively
- `clearPinnedFiles()` - clear all

**Used By:**
- FileCard.tsx:502 - Ctrl/Cmd+Click handler
- FileCard.tsx:508 - Alt+Click handler
- ChatPanel.tsx:1057 - Badge click to unpin

**Risk:** Both actions modify same `pinnedFileIds` array. Any refactor must maintain array consistency.

### Keyboard Event Propagation
**File:** `client/src/components/canvas/FileCard.tsx:493-516`

**Current Flow:**
1. `handleClick` fires on mesh
2. Checks modifier keys in order: Shift → Ctrl → Alt → Normal
3. Each branch calls `e.stopPropagation()` to prevent bubbling
4. Returns early on match

**Risk:** Adding new keyboard handlers must preserve this order to avoid conflicts.

---

## 🎯 IMPLEMENTATION ORDER FOR PHASE 65

### STEP 1: Change Alt → Shift for Single File Pin (SAFEST)
**Target:** Single file pinning behavior change

**File:** `client/src/components/canvas/FileCard.tsx`
- **Line 501:** Change `if (e.ctrlKey || e.metaKey)` → `if (e.shiftKey && !isDraggingAny)`
- **Risk Level:** LOW - isolated change
- **Dependencies:** None

**Note:** This CONFLICTS with Shift+Drag. Need to check if `isDraggingAny` is available to prevent triggering during drag.

### STEP 2: Add Branch Pinning to Single File Pin (OPTIONAL)
**Target:** Make pinning behave intelligently

**File:** `client/src/components/canvas/FileCard.tsx`
- **Line 502:** Add branch detection before `togglePinFile()`
- **Pseudocode:**
  ```typescript
  const node = useStore.getState().nodes[id];
  if (node?.type === 'folder') {
    pinSubtree(id);  // Pin folder's children
  } else {
    togglePinFile(id);  // Pin single file
  }
  ```
- **Risk Level:** MEDIUM - adds logic to existing flow
- **Dependencies:** Need access to node data in click handler

### STEP 3: Ctrl+Drag for Node Move (REQUIRES NEW CODE)
**Target:** Add alternative node move shortcut

**File:** `client/src/hooks/useDrag3D.ts`
- **Line 22:** Change `if (!e.shiftKey) return;` → `if (!(e.shiftKey || (e.ctrlKey && e.button === 0))) return;`
- **Alternative:** Create new hook `useDrag3DWithCtrl()`
- **Risk Level:** MEDIUM - modifies core drag behavior
- **Dependencies:** Hotkey conflicts with pin actions (Ctrl+Click)

**Conflict Analysis:**
- Ctrl+Click triggers pin
- Ctrl+Drag should move
- Need to distinguish: Ctrl+Click (no drag) vs Ctrl+Drag (with movement)
- **Solution:** Check pointer move delta in drag handler

### STEP 4: Add G Key for Grab Mode (NEW FEATURE)
**Target:** Blender-style 'G' to start grab without modifier

**Requires New:**
- Global keyboard listener
- Grab mode state in store
- UI indicator showing grab mode active
- Escape key to cancel

**File:** New hook `useGrabMode.ts` OR integrate into FileCard
- **Risk Level:** MEDIUM-HIGH - new feature, more moving parts
- **Dependencies:** Keyboard event listener, state management

---

## 📊 RISK MATRIX

```
ACTION                           | Risk | Complexity | Dependencies
--------------------------------|------|------------|-------------------
Alt→Shift (single file)         | LOW  | SIMPLE     | None
Add branch detection             | MED  | SIMPLE     | Node access in handler
Ctrl+Drag for move              | MED  | MEDIUM     | Conflict detection
G key for grab                  | HIGH | COMPLEX    | Global state, UI
Shift+Click (current)           | --   | --         | ALREADY WORKS
```

---

## 🔗 TREE STRUCTURE USAGE

### How to Find Children of a Node

**Current Pattern (from pinSubtree):**
```typescript
const node = state.nodes[nodeId];  // Get node
Object.values(state.nodes)         // Get all nodes
  .filter(n => n.parentId === nodeId)  // Find children by parentId
  .forEach(child => {
    // Process child
  });
```

**Alternative (if children array is populated):**
```typescript
const node = state.nodes[nodeId];
const childIds = node.children || [];  // Optional children array
childIds.forEach(childId => {
  // Process child
});
```

**Note:** `node.children` is optional (`children?: string[]`). Current code uses `parentId` lookup, which is reliable.

---

## 🚨 GOTCHAS & WARNINGS

### 1. Shift+Click Conflict
- **Current:** Shift+Click = Drag (via useDrag3D hook)
- **Proposal:** Change to Shift+Click = Pin
- **Problem:** OnClick fires BEFORE onPointerMove
- **Solution:** Check `isDraggingAny` state in handleClick. If false, safe to pin.

### 2. OrbitControls Auto-Disable
- **Current:** `enabled={!isDraggingAny}` (App.tsx:428)
- **Effect:** Camera completely locked when ANY node is dragging
- **Risk:** User can't pan/rotate during node move (feature or bug?)
- **Implication:** Safe for node dragging, but check if this is desired behavior

### 3. Ctrl/Cmd Ambiguity
- **Mac:** Cmd is standard (metaKey)
- **Windows/Linux:** Ctrl is standard (ctrlKey)
- **Current code:** `(e.ctrlKey || e.metaKey)` handles both
- **Good:** Already cross-platform

### 4. pinSubtree Only Pins Files
- **Current behavior:** `if (node.type === 'file') newPinned.add(id)`
- **Implication:** Alt+Click on folder pins only leaf files, not folders
- **Folders:** Act as navigation points, not pinnable units
- **Consider:** Is this intentional? Should folders be pinnable?

### 5. No Keyboard Listener Yet
- **Current:** All hotkeys via mouse modifiers
- **Missing:** Global 'G' key listener, Escape to cancel
- **Requires:** New hook with useEffect + addEventListener
- **Cleanup:** Must remove listener on unmount

---

## 📈 STATE DEPENDENCIES

### Store Dependencies (useStore.ts)
```
togglePinFile → pinnedFileIds (state)
pinSubtree → pinnedFileIds, nodes (state)
clearPinnedFiles → pinnedFileIds (state)
```

### Component Dependencies (FileCard.tsx)
```
FileCard → useStore.togglePinFile
        → useStore.pinSubtree
        → useStore.pinnedFileIds (read-only for display)
```

### UI Dependencies (ChatPanel.tsx)
```
ChatPanel → useStore.pinnedFileIds (display)
         → useStore.togglePinFile (unpin button)
```

### Camera Dependencies (App.tsx)
```
OrbitControls → isDraggingAny (from useStore)
```

---

## 📝 SUMMARY TABLE

| Component | Current State | Changes Needed | Complexity |
|-----------|---------------|-----------------|-----------|
| FileCard.tsx | Alt=Subtree, Ctrl=Single | Change Alt to Shift? | Simple |
| useDrag3D.ts | Shift+Drag moves | Add Ctrl+Drag option? | Medium |
| useStore.ts | togglePinFile, pinSubtree | No changes (works well) | -- |
| App.tsx | OrbitControls config | No changes (no conflicts) | -- |
| CameraController.tsx | Animation system | No changes (not affected) | -- |
| Global keyboard | None | Add G key listener? | Complex |

---

## ✅ NEXT STEPS FOR IMPLEMENTATION

1. **Decide hotkey layout** - Approve Phase 65 plan
2. **Test Shift+Click conflict** - Verify grab doesn't trigger on single shift
3. **Modify FileCard.tsx** - Implement chosen hotkey changes
4. **Update help text** - Line 549 in App.tsx
5. **Test with folders** - Verify folder pin behavior
6. **Document final layout** - Update UI tooltip

---

**Generated:** 2026-01-18
**Status:** 🔒 READ-ONLY AUDIT COMPLETE
**Next Review:** After Phase 65 implementation decision
