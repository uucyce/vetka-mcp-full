# H3 Report: Drop Zone Architecture Analysis

## MARKER_H3_CURRENT_DROP_SCANPANEL

### ScanPanel Drop Handler (Phase 100.2)

**Current Implementation:**
- **Location**: `/client/src/components/scanner/ScanPanel.tsx` (lines 277-355)
- **Mechanism**: Uses native Tauri `onFilesDropped` event + Browser fallback
- **Handler Flow**:
  1. Subscribes to `onFilesDropped` callback from Tauri config
  2. Receives paths as string array
  3. Processes via `handleDropPaths()` to get FileInfo objects
  4. Separates directories (added to watcher) from files (added to scanned list)
  5. Emits `files_dropped` event via callback

**Browser Fallback (lines 647-666)**:
- Implements `onDragOver`, `onDragLeave`, `onDrop` handlers on ScanPanel div
- Uses HTML5 File System Access API (`getAsFileSystemHandle`)
- Limited in browser - can't get real paths, shows hint to use path input

**Event Details**:
```typescript
interface ScannerEvent {
  type: 'files_dropped' | 'directory_added' | ...;
  path?: string;
  filesCount?: number;
}
```

**State Tracking**:
- `isDragOver`: Visual feedback (line 254)
- `panelRef`: Reference for drag event binding (line 257)

**Key Behavior**:
- Does NOT use `stopPropagation()` on drop events
- Updates scanned files list immediately
- Triggers watcher API call for directories
- Emits custom event for ChatPanel to show Hostess message

---

## MARKER_H3_TAURI_EVENTS

### Native Tauri Drag & Drop (main.rs)

**Architecture** (lines 42-72 in main.rs):
- **Window-level listener**: Registered in `app.setup()` on main window
- **Event Types**:
  - `DragDropEvent::Drop`: Actual drop - emits to frontend
  - `DragDropEvent::Enter`: Drag enters window
  - `DragDropEvent::Over`: Continuous while dragging
  - `DragDropEvent::Leave`: Drag leaves window

**Frontend Emission** (line 58):
```rust
window_handle.emit("files-dropped", &path_strings);
```

**Frontend Reception** (ScanPanel.tsx line 25):
```typescript
import { isTauri, onFilesDropped, handleDropPaths } from '../../config/tauri';
```

**tauri.ts Config** (assumed from usage):
- `onFilesDropped(callback)` - registers listener for "files-dropped" event
- `handleDropPaths(paths)` - converts native paths to FileInfo objects
- `isTauri()` - checks if running in Tauri environment

**Critical Feature**:
- Window-level listener means it fires for ANY drop on the window
- NOT scoped to specific DOM element
- Frontend must determine which zone (Scanner, Chat, Tree) receives the drop

---

## MARKER_H3_APP_STRUCTURE

### App.tsx Global Drop Zone Architecture

**Current State** (Phase 54.7):
- **Status**: Drop handling DISABLED (commented out, lines 28-388)
- **Reason**: "Drag & Drop disabled temporarily - TODO: Re-enable with Tauri migration"

**Commented Architecture** (lines 62-82):
```typescript
// const getDropZone = useCallback((e: DragEvent): DropZone => {
//   const x = e.clientX;  // X-coordinate-based detection
//   const chatPanelWidth = 360;
//
//   if (!isChatOpen) return 'tree';  // Everything goes to tree if chat closed
//
//   if (x < chatPanelWidth) {
//     const y = e.clientY;
//     const scannerHeight = 250;  // Approximate scanner height
//     if (y < scannerHeight) return 'scanner';
//     return 'chat';
//   }
//   return 'tree';
// }, [isChatOpen]);
```

**Drop Zone Types** (line 32):
```typescript
// type DropZone = 'scanner' | 'tree' | 'chat' | null;
```

**Three Target Zones**:
1. **Scanner**: Top-left panel (if chat open) - y < 250
2. **Chat**: Bottom-left panel (if chat open)
3. **Tree**: Right side of screen (the 3D canvas area)

**Layout Dependency**:
- Chat position: Phase 81.1 made chat relocatable (left/right)
- PROBLEM: Current logic assumes chat is LEFT - doesn't handle right-side chat

**Document-level Listeners** (lines 303-388):
- `dragenter`, `dragover`, `dragleave` on document
- Drag counter logic (to detect leaving window vs moving between zones)
- Stale drag detection (500ms failsafe)

---

## MARKER_H3_CHAT_STRUCTURE

### ChatPanel Drop Zone Location

**Panel Structure** (ChatPanel.tsx):
- **Position**: Fixed left (0) or right side (Phase 81.1, line 1268)
- **Width**: Resizable, min 380px (line 1274)
- **Layers**:
  1. Header (8px padding)
  2. Search bar (when chat/group mode)
  3. Pinned context (when files pinned)
  4. **ScanPanel** (when scanner tab active, lines 1899-1921)
  5. Messages container (flex: 1)
  6. Message input (always visible)

**No Current Drop Handling**:
- ChatPanel doesn't have drag/drop handlers
- ScanPanel handles drops when scanner tab is active
- But ScanPanel is INSIDE ChatPanel - it's not window-level

**Problem**:
- Drop events bubble to window level (Tauri)
- ScanPanel only receives drops if:
  - ChatPanel is open AND
  - Scanner tab is active AND
  - Cursor is over ScanPanel area

**Gap**:
- Drops to ChatPanel (chat/group mode) are NOT caught
- Message input has no drop handler
- No way to drop files directly into chat conversation

---

## MARKER_H3_CONFLICT_POINTS

### 1. **Event Propagation Mismatch**
- **Problem**: Tauri emits "files-dropped" at WINDOW level
- **Current Handling**: Only ScanPanel listens (via `onFilesDropped` hook)
- **Conflict**: No way to route drops to other components without window-level coordination

### 2. **Coordinate-based Zone Detection**
- **Current Logic**: Uses `e.clientX / e.clientY` to determine zone
- **Issue**: Chat can be on LEFT or RIGHT (Phase 81.1) - logic doesn't adapt
- **Issue**: Chat width is resizable (Phase 81) - hardcoded 360px is wrong
- **Issue**: ScanPanel height is resizable (lines 559-587) - hardcoded 250px is wrong

### 3. **ScanPanel Inside ChatPanel**
- **Problem**: ScanPanel is rendered INSIDE ChatPanel (line 1899)
- **Current**: Both try to handle drops independently
- **Conflict**:
  - ScanPanel binds `onDragOver/Drop` to its div (lines 686-688)
  - But Tauri emits at window level, not element level
  - ScanPanel's handlers are never triggered (events don't reach div-level in native drop)

### 4. **Chat Tab Visibility**
- **Problem**: ScanPanel only mounts when `activeTab === 'scanner'` (line 1899)
- **Scenario**: User drops file while in 'chat' or 'group' tab
- **Result**: ScanPanel listeners don't exist - drop is unhandled!
- **Solution Needed**: Global drop handler that routes based on active tab

### 5. **Right-side Chat Not Handled**
- **Current Assumption**: Chat is always LEFT (ChatPanel.tsx line 1059)
- **Reality**: Phase 81.1 added right-side chat mode
- **Impact**: Zone detection logic completely wrong for right-side layout

### 6. **stopPropagation Gap**
- **ScanPanel**: Doesn't call `stopPropagation()` on native drop (Tauri event)
- **App.tsx**: Comments suggest handlers would call it to prevent cascade
- **Result**: All drops bubble to all zones simultaneously

### 7. **Resize Handle vs Drop Zone**
- **ScanPanel Resize**: Uses `onMouseDown` on resize handle (line 839)
- **Chat Resize**: Uses `onMouseDown` on resize handle (ChatPanel line 1285)
- **Issue**: If drop happens during/after resize, coordinates are stale

---

## MARKER_H3_HIERARCHY_PROPOSAL

### Recommended Drop Zone Hierarchy

```
WINDOW LEVEL (Tauri emits here)
├── "files-dropped" event -> Global Router
│
└─► ROUTER LOGIC (new component needed)
    ├─► Check activeTab state from store
    ├─► Check chatPosition (left/right) from localStorage
    ├─► Check chatWidth for accurate bounds
    └─► Route to appropriate handler

    ZONE 1: CHAT/SCANNER PANEL (LEFT or RIGHT)
    ├─► IF activeTab === 'scanner'
    │   └─► Route to ScanPanel (existing handler)
    │
    ├─► IF activeTab === 'chat' || activeTab === 'group'
    │   └─► Route to ChatPanel Drop Handler (NEW)
    │       └─► Add file(s) directly to message input as context
    │
    └─► Visual Feedback
        └─► Highlight appropriate zone

    ZONE 2: 3D TREE CANVAS (RIGHT side if chat left, or full if chat closed)
    └─► Route to App.tsx or FileCard (future)
        └─► Add files to tree visualization
```

### Implementation Architecture

#### **1. Global Drop Router (New Component)**

**File**: `client/src/components/DropZoneRouter.tsx`

**Responsibilities**:
- Listen to Tauri "files-dropped" event (singleton)
- Determine current layout:
  - Chat open? Yes → Get position (left/right) + width from localStorage
  - Scanner tab active? Yes/No
  - Active tab? (scanner/chat/group)
- Calculate accurate zone bounds (NOT hardcoded)
- Dispatch custom events to specific zones
- Handle visual feedback (overlay highlighting)

**State Dependencies**:
```typescript
const isChatOpen = store.state.isChatOpen;  // From App.tsx
const chatPosition = localStorage.getItem('vetka_chat_position'); // 'left'|'right'
const chatWidth = localStorage.getItem('vetka_chat_width'); // number
const activeTab = store.state.activeTab; // 'scanner'|'chat'|'group'
```

**Dynamic Zone Calculation**:
```typescript
function calculateZones() {
  const zones = {
    canvas: { x: [0, window.innerWidth], y: [0, window.innerHeight] },
    scanner: null,
    chat: null,
  };

  if (!isChatOpen) {
    // Full window = canvas
    return zones;
  }

  // Chat exists - calculate its bounds
  if (chatPosition === 'left') {
    zones.chat.x = [0, chatWidth];
    zones.canvas.x = [chatWidth, window.innerWidth];
  } else {
    zones.chat.x = [window.innerWidth - chatWidth, window.innerWidth];
    zones.canvas.x = [0, window.innerWidth - chatWidth];
  }

  // Scanner is subset of chat (if active tab is scanner)
  if (activeTab === 'scanner') {
    zones.scanner.y = [0, scanPanelHeight];  // Get from ResizeObserver
    zones.chat.y = [scanPanelHeight, window.innerHeight];
  }

  return zones;
}
```

#### **2. ScanPanel Drop Handler (Existing, Enhance)**

**File**: `client/src/components/scanner/ScanPanel.tsx`

**Current**:
- Receives "files-dropped" from Tauri
- Processes locally

**Enhancement**:
- Listen to custom event: `'scanner-zone-drop'` (from DropZoneRouter)
- Add `stopPropagation()` equivalent (prevent cascade)
- Update visual feedback to use zone event instead of div-level handlers

**New Handler**:
```typescript
useEffect(() => {
  const handleScannerDrop = (e: CustomEvent) => {
    const { paths } = e.detail;
    // Process drops (existing logic)
    processFilePaths(paths);
  };

  window.addEventListener('scanner-zone-drop', handleScannerDrop as EventListener);
  return () => window.removeEventListener('scanner-zone-drop', handleScannerDrop as EventListener);
}, []);
```

#### **3. ChatPanel Drop Handler (NEW)**

**File**: `client/src/components/chat/ChatPanel.tsx`

**Responsibilities**:
- Listen to custom event: `'chat-zone-drop'` (from DropZoneRouter)
- Convert dropped paths to readable file names
- Add to message input as context (similar to pinned files)
- Or auto-insert into message: "Here are the files I dropped: ..."

**Behavior**:
```typescript
const handleChatDrop = (e: CustomEvent) => {
  const { paths } = e.detail;
  // Show files in chat as context/mention
  // Option A: Add to pinned files
  paths.forEach(path => {
    // Find node by path and pin it
  });
  // Option B: Add to input as code snippet
  setInput(prev => prev + `\n\nFiles dropped:\n${paths.join('\n')}`);
};
```

#### **4. Visual Feedback (Global)**

**Enhancement to DropZoneRouter**:
```typescript
function renderDropOverlay() {
  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      pointerEvents: 'none',
      zIndex: 999,
    }}>
      {/* Scanner zone highlight */}
      {zones.scanner && activeTab === 'scanner' && (
        <div style={{
          position: 'absolute',
          ...zones.scanner,
          background: isDragOver ? 'rgba(74, 158, 255, 0.15)' : 'transparent',
          border: isDragOver ? '2px dashed #4a9eff' : '2px dashed transparent',
          transition: 'all 0.15s',
        }} />
      )}

      {/* Chat zone highlight */}
      {zones.chat && (
        <div style={{
          position: 'absolute',
          ...zones.chat,
          background: isDragOver && isOverChat ? 'rgba(100, 200, 100, 0.15)' : 'transparent',
          border: isDragOver && isOverChat ? '2px dashed #64c864' : '2px dashed transparent',
        }} />
      )}

      {/* Canvas zone highlight */}
      <div style={{
        position: 'absolute',
        ...zones.canvas,
        background: isDragOver && isOverCanvas ? 'rgba(200, 100, 100, 0.15)' : 'transparent',
        border: isDragOver && isOverCanvas ? '2px dashed #c86464' : '2px dashed transparent',
      }} />
    </div>
  );
}
```

---

## MARKER_H3_HIERARCHY_PROPOSAL

### Drop Zone Hierarchy (Priority Order)

```
1. SCANNER ZONE (Highest Priority when visible)
   └─ Conditions: ChatPanel open + activeTab === 'scanner'
   └─ Action: Add files to watcher, show in scanned list
   └─ stopPropagation: YES (don't cascade to chat or canvas)

2. CHAT ZONE (Medium Priority when visible)
   └─ Conditions: ChatPanel open + activeTab === 'chat'|'group'
   └─ Action: Add files as context or to pinned files
   └─ stopPropagation: YES (don't cascade to canvas)

3. CANVAS ZONE (Lowest Priority)
   └─ Conditions: Always visible, accepts drops
   └─ Action: (Future) Add files to 3D tree visualization
   └─ stopPropagation: N/A (terminal zone)
```

### Pseudo-code Flow

```typescript
window.addEventListener('files-dropped', (paths: string[]) => {
  // Get current state
  const { isChatOpen, activeTab, selectedNode } = store.getState();
  const chatPos = localStorage.getItem('vetka_chat_position');
  const chatWidth = Number(localStorage.getItem('vetka_chat_width')) || 420;

  // Determine drop zone by position (from Tauri event)
  const zone = determineZone(event.x, event.y, isChatOpen, chatPos, chatWidth);

  // Dispatch to appropriate handler
  switch (zone) {
    case 'scanner':
      if (activeTab === 'scanner' && isChatOpen) {
        window.dispatchEvent(new CustomEvent('scanner-zone-drop', { detail: { paths } }));
        return; // STOP here - don't cascade
      }
      break;

    case 'chat':
      if (isChatOpen && ['chat', 'group'].includes(activeTab)) {
        window.dispatchEvent(new CustomEvent('chat-zone-drop', { detail: { paths } }));
        return; // STOP here - don't cascade
      }
      break;

    case 'canvas':
      window.dispatchEvent(new CustomEvent('canvas-zone-drop', { detail: { paths } }));
      return; // STOP here - terminal zone
  }

  // Fallback: no matching zone (e.g., scanner tab not active but chat closed)
  // Could add to pinned files or tree by default
});
```

### Zone Coordinate Calculation

**Dynamic bounds** (NOT hardcoded):

```typescript
function getZoneBounds() {
  const isChatOpen = store.isChatOpen;
  const chatPos = localStorage.getItem('vetka_chat_position');
  const chatWidth = parseInt(localStorage.getItem('vetka_chat_width') || '420');
  const scannerHeight = getScanPanelHeight(); // Via ResizeObserver
  const w = window.innerWidth;
  const h = window.innerHeight;

  if (!isChatOpen) {
    return {
      canvas: { x1: 0, x2: w, y1: 0, y2: h }
    };
  }

  if (chatPos === 'left') {
    return {
      scanner: { x1: 0, x2: chatWidth, y1: 0, y2: scannerHeight },
      chat: { x1: 0, x2: chatWidth, y1: scannerHeight, y2: h },
      canvas: { x1: chatWidth, x2: w, y1: 0, y2: h }
    };
  } else {
    return {
      canvas: { x1: 0, x2: w - chatWidth, y1: 0, y2: h },
      scanner: { x1: w - chatWidth, x2: w, y1: 0, y2: scannerHeight },
      chat: { x1: w - chatWidth, x2: w, y1: scannerHeight, y2: h }
    };
  }
}
```

---

## Summary

**Current State**:
- Drop handling is DISABLED in App.tsx (Phase 54.7)
- ScanPanel has local Tauri drop listener (Phase 100.2)
- No global coordination between zones
- Hardcoded zone bounds won't work with resizable layout

**Proposed Solution**:
1. Create `DropZoneRouter` component (window-level listener)
2. Calculate zones dynamically (not hardcoded)
3. Route to specific zone handlers via custom events
4. Implement ChatPanel drop handler (NEW)
5. Add `stopPropagation` logic to prevent cascade
6. Add visual feedback overlay for all zones

**Benefits**:
- Works with resizable chat panel
- Works with left/right chat positions
- Clear priority hierarchy (scanner > chat > canvas)
- Easy to add new zones in future
- Visual feedback for user clarity
