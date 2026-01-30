# Search Click-to-Navigate Pattern Audit
## Phase 92 - Click Handler & Camera Focus Pattern

**Author:** Haiku Audit Agent
**Date:** 2026-01-25
**Phase:** 92
**Status:** Complete Audit

---

## Executive Summary

The UnifiedSearchBar component implements a complete click-to-navigate pattern with camera focus. When a user clicks on a search result, the system:

1. Calls `onSelectResult` callback with SearchResult data
2. Inside ChatPanel's `handleSearchSelect`:
   - Calls `selectNode(result.path)` to select the node in store
   - Calls `setCameraCommand()` to trigger camera animation
3. CameraController listens for camera commands and executes smooth 3D animation
4. After animation completes, the node is highlighted and chat context is switched

This pattern **must be replicated in ScanProgressPanel** for file clicks.

---

## 1. UnifiedSearchBar Click Handler Implementation

### Source File
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/search/UnifiedSearchBar.tsx`

### Result Item Click Handler (Lines 1007-1022)

```typescript
<div
  key={result.id}
  style={{
    ...styles.resultItem,
    ...(isSelected ? styles.resultItemSelected : {}),
    background: isSelected ? '#252525' : 'transparent',
  }}
  onClick={(e) => handleSelect(result, index, e)}
  onMouseEnter={(e) => {
    if (!isSelected) e.currentTarget.style.background = '#1f1f1f';
    handleMouseEnter(result, e);
  }}
  onMouseLeave={(e) => {
    if (!isSelected) e.currentTarget.style.background = 'transparent';
    handleMouseLeave();
  }}
>
```

### handleSelect Function (Lines 331-359)

```typescript
const handleSelect = useCallback((result: SearchResult, index: number, e: React.MouseEvent) => {
  if (e.shiftKey && lastSelectedIndex !== null) {
    // Range select
    const start = Math.min(lastSelectedIndex, index);
    const end = Math.max(lastSelectedIndex, index);
    const newSelected = new Set(selectedIds);
    for (let i = start; i <= end; i++) {
      newSelected.add(sortedResults[i].id);
    }
    setSelectedIds(newSelected);
  } else if (e.ctrlKey || e.metaKey) {
    // Toggle single selection
    const newSelected = new Set(selectedIds);
    if (newSelected.has(result.id)) {
      newSelected.delete(result.id);
    } else {
      newSelected.add(result.id);
    }
    setSelectedIds(newSelected);
    setLastSelectedIndex(index);
  } else {
    // Normal click - select only this one and trigger navigation
    setSelectedIds(new Set([result.id]));
    setLastSelectedIndex(index);
    // Phase 68.3: Show selected file path
    setSelectedFilePath(result.path);
    onSelectResult?.(result);  // <-- CALLBACK TO PARENT
  }
}, [lastSelectedIndex, selectedIds, sortedResults, onSelectResult]);
```

**Key Points:**
- Multi-select support with Shift+Click and Ctrl/Cmd+Click
- Normal single click calls `onSelectResult?(result)` callback
- Passes full `SearchResult` object with all metadata

---

## 2. CSS Hover & Selection Styles

### Result Item Styles (Lines 488-541)

```typescript
const styles = {
  resultItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: compact ? '6px 10px' : '8px 12px',
    cursor: 'pointer',
    borderBottom: '1px solid #222',
    transition: 'background 0.15s',
  },
  resultItemSelected: {
    background: '#252525',
  },
  // ...
};
```

### Dynamic Hover Effect (Lines 1015-1022)

```typescript
onMouseEnter={(e) => {
  if (!isSelected) e.currentTarget.style.background = '#1f1f1f';
  handleMouseEnter(result, e);  // Also triggers 300ms hover preview
}}
onMouseLeave={(e) => {
  if (!isSelected) e.currentTarget.style.background = 'transparent';
  handleMouseLeave();
}}
```

**CSS Classes Applied:**
- `.resultItem` - Base styles with `cursor: pointer`
- Dynamic inline `background` changes:
  - Normal: `transparent`
  - Hover: `#1f1f1f` (slightly lighter)
  - Selected: `#252525` (brighter)
- All transitions use `transition: 'background 0.15s'` (15ms smooth)

---

## 3. Camera Navigation Integration

### ChatPanel Handler (Lines 747-758)

**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`

```typescript
const handleSearchSelect = useCallback((result: SearchResult) => {
  // Select node in 3D tree
  if (result.path) {
    selectNode(result.path);  // <-- Select in store
    // Focus camera on selected file
    setCameraCommand({
      target: result.path,
      zoom: 'close',
      highlight: true
    });
  }
}, [selectNode, setCameraCommand]);
```

**Passed to UnifiedSearchBar as:**
```typescript
<UnifiedSearchBar
  onSelectResult={handleSearchSelect}
  // ... other props
/>
```

### Camera Command Structure

The camera command object contains:
- `target: string` - File path to navigate to (matches node.path)
- `zoom: 'close' | 'medium' | 'far'` - Camera distance
- `highlight: boolean` - Whether to highlight the node briefly

**Usage in Search:** `zoom: 'close'` and `highlight: true`

---

## 4. CameraController Processing

### Source File
**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/CameraController.tsx`

### Camera Command Handler (Lines 123-197)

```typescript
useEffect(() => {
  if (!cameraCommand) return;

  // Find node by path or name
  const nodeEntry = findNode(cameraCommand.target);

  if (!nodeEntry) {
    // Node not found - clear command
    setCameraCommand(null);
    return;
  }

  const [nodeId, node] = nodeEntry;

  // Highlight the node immediately
  if (cameraCommand.highlight) {
    highlightNode(nodeId);
    setTimeout(() => highlightNode(null), 3000);  // 3s highlight duration
  }

  // Target node position
  const nodePos = new THREE.Vector3(
    node.position.x,
    node.position.y,
    node.position.z
  );

  // Final distance based on zoom (Phase 52.6.3: increased for comfortable view)
  const finalDistance = cameraCommand.zoom === 'close' ? 20
                      : cameraCommand.zoom === 'medium' ? 30 : 45;

  // Phase 52.6.2: Simple frontal positioning (ALWAYS approach from Z+ direction)
  const targetPos = new THREE.Vector3(
    nodePos.x,
    nodePos.y + 3,  // Slightly above
    nodePos.z + finalDistance  // In front on Z axis
  );

  // Calculate target camera orientation (looking at node)
  const tempCamera = camera.clone();
  tempCamera.position.copy(targetPos);
  tempCamera.lookAt(nodePos);

  // Phase 52.6.3: Disable OrbitControls during animation
  const controls = window.__orbitControls;
  if (controls) {
    controls.enabled = false;
    controls.minDistance = 10;
  }

  // Setup smooth animation with quaternion interpolation
  animationRef.current = {
    active: true,
    startPos: camera.position.clone(),
    targetPos,
    startQuaternion: camera.quaternion.clone(),
    targetQuaternion: tempCamera.quaternion.clone(),
    lookAt: nodePos.clone(),
    progress: 0,
    nodeId
  };

  // Clear command after setup
  setCameraCommand(null);
}, [cameraCommand, nodes, selectNode, highlightNode, setCameraCommand]);
```

### Animation Loop (Lines 200-251)

```typescript
useFrame((_, delta) => {
  if (!animationRef.current?.active) return;

  const anim = animationRef.current;

  // Progress speed (2.5s total animation)
  anim.progress = Math.min(anim.progress + delta * 0.4, 1);

  const t = anim.progress;

  // Ease-in-out interpolation (smoother curve)
  const eased = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

  // Interpolate position
  const currentPos = new THREE.Vector3().lerpVectors(
    anim.startPos,
    anim.targetPos,
    eased
  );

  // Interpolate rotation (quaternion slerp for smooth rotation)
  const currentQuat = new THREE.Quaternion().slerpQuaternions(
    anim.startQuaternion,
    anim.targetQuaternion,
    eased
  );

  // Update camera
  camera.position.copy(currentPos);
  camera.quaternion.copy(currentQuat);

  // Animation complete
  if (anim.progress >= 1.0) {
    // Re-enable OrbitControls and sync target
    const controls = window.__orbitControls;
    if (controls) {
      controls.target.copy(anim.lookAt);
      controls.enabled = true;
      controls.update();
    }

    // Switch chat context
    selectNode(anim.nodeId);

    // Stop animation
    animationRef.current = null;
  }
});
```

**Animation Characteristics:**
- **Duration:** 2.5 seconds (delta * 0.4 interpolation)
- **Easing:** Ease-in-out cubic for smooth acceleration/deceleration
- **Approach:** Always from Z+ direction (frontal view)
- **Distance:** 20 units for "close" zoom (search results use this)
- **Post-Animation:** Highlight removed after 3 seconds, chat context switched

---

## 5. Node Finding Algorithm

### CameraController findNode (Lines 54-81)

```typescript
const findNode = (target: string): [string, typeof nodes[string]] | null => {
  // 1. Exact path match
  let entry = Object.entries(nodes).find(([_, n]) => n.path === target);
  if (entry) {
    return entry as [string, typeof nodes[string]];
  }

  // 2. Filename match (main.py → /full/path/main.py)
  entry = Object.entries(nodes).find(([_, n]) =>
    n.path?.endsWith('/' + target) || n.name === target
  );
  if (entry) {
    return entry as [string, typeof nodes[string]];
  }

  // 3. Partial path match (docs/file.md → /full/path/docs/file.md)
  entry = Object.entries(nodes).find(([_, n]) =>
    n.path?.includes(target)
  );
  if (entry) {
    return entry as [string, typeof nodes[string]];
  }

  return null;
};
```

**Matching Priority:**
1. Exact path match (fastest, most reliable)
2. Filename match (e.g., just "main.py")
3. Partial path match (e.g., "docs/file.md")

---

## 6. Hover Preview Panel Pattern

### Hover State Management (Lines 266-268, 393-409)

```typescript
// Hover preview state
const [hoveredResult, setHoveredResult] = useState<SearchResult | null>(null);
const [previewPosition, setPreviewPosition] = useState<{ x: number; y: number } | null>(null);

// Hover preview handlers
const handleMouseEnter = useCallback((result: SearchResult, e: React.MouseEvent) => {
  const rect = e.currentTarget.getBoundingClientRect();
  hoverTimerRef.current = setTimeout(() => {
    setHoveredResult(result);
    setPreviewPosition({ x: rect.right + 8, y: rect.top });
  }, 300);  // 300ms delay before showing preview
}, []);

const handleMouseLeave = useCallback(() => {
  if (hoverTimerRef.current) {
    clearTimeout(hoverTimerRef.current);
    hoverTimerRef.current = null;
  }
  setHoveredResult(null);
  setPreviewPosition(null);
}, []);
```

### Preview Rendering (Lines 1127-1165)

```typescript
{hoveredResult && previewPosition && (
  <div
    style={{
      ...styles.preview,
      left: Math.min(previewPosition.x, window.innerWidth - 420),
      top: Math.min(previewPosition.y, window.innerHeight - 320),
    }}
  >
    <div style={styles.previewTitle}>{hoveredResult.name}</div>

    {/* Metadata row */}
    <div style={{
      display: 'flex',
      gap: 12,
      fontSize: 10,
      color: '#666',
      marginBottom: 8,
      paddingBottom: 8,
      borderBottom: '1px solid #333',
    }}>
      <span>Type: <b style={{ color: '#888' }}>{hoveredResult.type}</b></span>
      <span>Ext: <b style={{ color: '#888' }}>.{hoveredResult.name.split('.').pop() || '?'}</b></span>
      <span>Score: <b style={{ color: '#888' }}>{Math.round(hoveredResult.relevance * 100)}%</b></span>
      {hoveredResult.modified_time ? (
        <span>Modified: <b style={{ color: '#888' }}>{new Date(hoveredResult.modified_time * 1000).toLocaleDateString('ru-RU')}</b></span>
      ) : null}
    </div>

    {/* Path */}
    <div style={{ fontSize: 10, color: '#555', marginBottom: 8, wordBreak: 'break-all' }}>
      {hoveredResult.path}
    </div>

    {/* Preview content */}
    <div style={styles.previewContent}>
      {hoveredResult.preview || 'No preview available'}
    </div>
  </div>
)}
```

### Preview Styles (Lines 584-610)

```typescript
preview: {
  position: 'fixed' as const,
  background: '#1a1a1a',
  border: '1px solid #333',
  borderRadius: '6px',
  padding: '12px',
  maxWidth: '400px',
  maxHeight: '300px',
  overflow: 'auto',
  zIndex: 2000,
  boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
},
previewTitle: {
  color: '#fff',
  fontSize: '13px',
  fontWeight: 500,
  marginBottom: '8px',
  borderBottom: '1px solid #333',
  paddingBottom: '8px',
},
previewContent: {
  color: '#888',
  fontSize: '12px',
  fontFamily: 'monospace',
  whiteSpace: 'pre-wrap' as const,
  wordBreak: 'break-all' as const,
},
```

**Preview Behavior:**
- Shows after 300ms hover
- Fixed position, adjusted to stay in viewport
- Contains: title, metadata (type, ext, score, modified), path, preview content
- High z-index (2000) to float above other content

---

## 7. ScanProgressPanel - Current vs Required

### Current Implementation

**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ScanProgressPanel.tsx`

**Current Click Handler (Lines 122-124):**
```typescript
const handleFileClick = useCallback((path: string) => {
  onFileClick(path);
}, [onFileClick]);
```

**Current Usage (Line 175):**
```typescript
<li
  key={`${file.path}-${file.timestamp}`}
  className="scanned-file-item"
  onClick={() => handleFileClick(file.path)}
  title={file.path}
>
```

**Problem:** Only calls `onFileClick(path)` - does NOT trigger camera navigation!

### Current CSS

**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ScanProgressPanel.css`

```css
.scanned-file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.scanned-file-item:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.1);
}
```

**Good:** Already has proper hover styling and cursor

### Required Changes

To replicate UnifiedSearchBar pattern:

1. **Update props interface** to accept camera navigation callbacks
2. **Replace simple onFileClick** with camera trigger logic
3. **Add selectNode call** before camera animation
4. **Maintain consistent styling** (already good)

---

## 8. Implementation Checklist for ScanProgressPanel

### Code Changes Required

```typescript
// 1. Add props for camera navigation
interface ScanProgressPanelProps {
  onFileClick: (path: string) => void;
  selectNode?: (path: string) => void;  // NEW
  setCameraCommand?: (cmd: { target: string; zoom: 'close' | 'medium' | 'far'; highlight: boolean }) => void;  // NEW
  isVisible?: boolean;
}

// 2. Update component signature
export const ScanProgressPanel: React.FC<ScanProgressPanelProps> = ({
  onFileClick,
  selectNode,  // NEW
  setCameraCommand,  // NEW
  isVisible = true
}) => {
  // ...

  // 3. Update click handler to match UnifiedSearchBar pattern
  const handleFileClick = useCallback((path: string) => {
    if (selectNode && setCameraCommand) {
      selectNode(path);  // Select in store
      setCameraCommand({
        target: path,
        zoom: 'close',  // Same as UnifiedSearchBar
        highlight: true  // Same as UnifiedSearchBar
      });
    } else {
      // Fallback if props not provided
      onFileClick(path);
    }
  }, [selectNode, setCameraCommand, onFileClick]);
};
```

### Caller Changes (ChatPanel)

```typescript
<ScanProgressPanel
  onFileClick={handleSearchSelect}  // Existing
  selectNode={selectNode}  // NEW - pass from store
  setCameraCommand={setCameraCommand}  // NEW - pass from store
  isVisible={isVisible}
/>
```

**or even simpler - pass entire SearchResult-like object:**

```typescript
const handleScanFileClick = useCallback((path: string) => {
  // Replicate the search pattern exactly
  if (path) {
    selectNode(path);
    setCameraCommand({
      target: path,
      zoom: 'close',
      highlight: true
    });
  }
}, [selectNode, setCameraCommand]);

<ScanProgressPanel
  onFileClick={handleScanFileClick}
  isVisible={isVisible}
/>
```

---

## 9. Design Patterns Identified

### Pattern: Click-to-Navigate-with-Camera

1. **Callback Pattern**
   - Component calls `onSelectResult(result)` or `onFileClick(path)`
   - Parent component implements the navigation logic
   - Decoupling: component doesn't need camera knowledge

2. **Store-Based State Management**
   - `selectNode(path)` - updates selected node ID in Zustand store
   - `setCameraCommand(command)` - triggers camera animation
   - CameraController listens for changes and executes animation

3. **Three-Step Process**
   ```
   Click → selectNode + setCameraCommand → CameraController animation → selectNode (context switch)
   ```
   - Step 1: User interaction (handled by component)
   - Step 2: Store update (handled by parent/hooks)
   - Step 3: Animation (handled by CameraController)
   - Step 3b: Context finalization (selectNode called after animation)

4. **CSS Styling Pattern**
   - Base styles for normal state
   - `transition: background 0.15s` for smooth hover
   - Inline style overrides for selected/hover states
   - No CSS class toggling needed for single-item selections

5. **Hover Preview Pattern** (SearchBar specific)
   - 300ms delay before showing
   - Fixed positioning with viewport edge detection
   - Rich metadata display
   - High z-index (2000) for proper layering

---

## 10. Code Snippet Summary Table

| Component | Function | Key Code |
|-----------|----------|----------|
| **UnifiedSearchBar** | Click handler | `onClick={(e) => handleSelect(result, index, e)}` |
| **UnifiedSearchBar** | Callback | `onSelectResult?.(result)` |
| **UnifiedSearchBar** | CSS hover | `transition: 'background 0.15s'` |
| **ChatPanel** | Navigation | `selectNode(result.path); setCameraCommand(...)` |
| **CameraController** | Animation | `useFrame` loop with quaternion slerp |
| **CameraController** | Find node | `findNode(target)` with 3-level fallback |
| **ScanProgressPanel** | Current | `onClick={() => handleFileClick(file.path)}` |
| **ScanProgressPanel** | CSS | `.scanned-file-item:hover` with background change |

---

## 11. References

- **UnifiedSearchBar:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/search/UnifiedSearchBar.tsx` (lines 331-359, 1007-1022)
- **ChatPanel:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx` (lines 747-758)
- **CameraController:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/CameraController.tsx` (lines 54-251)
- **ScanProgressPanel:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ScanProgressPanel.tsx` (lines 122-124)
- **ScanProgressPanel CSS:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ScanProgressPanel.css`

---

## Key Takeaway for Implementation

**The UnifiedSearchBar pattern is the canonical click-to-navigate pattern in VETKA. ScanProgressPanel should replicate it exactly:**

```typescript
// When user clicks a file in ScanProgressPanel:
selectNode(filePath);
setCameraCommand({
  target: filePath,
  zoom: 'close',
  highlight: true
});
```

This is the same three-step flow as UnifiedSearchBar, just without the multi-select complexity and preview panel.
