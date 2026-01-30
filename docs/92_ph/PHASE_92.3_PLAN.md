# Phase 92.3: Scan Progress Panel Fix Plan

**Date:** 2026-01-25
**Status:** ✅ APPROVED - IMPLEMENTING

---

## Haiku Audit Results

### Search Panel (`UnifiedSearchBar.tsx`)
- 300ms hover preview via `setTimeout` + `useRef`
- Preview shows: type, size, date, path, content snippet
- Click → `onSelectResult` → camera navigation
- Dark theme: #0f0f0f, #1a1a1a, inline CSS
- All SVG icons inline

### Chat Panel Structure
**ScanProgressPanel uses `position: absolute; bottom: 0`** - overlay, NOT blocking flex layout

**Render order (top → bottom):**
1. Header (tabs)
2. SearchBar
3. Chat name
4. Pinned files
5. ScannerPanel (scanner tab only, maxHeight 40%)
6. MessageList (flex: 1)
7. ScanProgressPanel (absolute bottom, z-index: 100)
8. MessageInput (always last)

### Two Different Panels:
- **ScannerPanel** (`scanner/ScannerPanel.tsx`) - "Add Folder" + "Clear All Scans"
- **ScanProgressPanel** (`chat/ScanProgressPanel.tsx`) - Progress overlay with files

---

## User Requirements (Approved)

1. ✅ Delete bottom overlay panel (ScanProgressPanel) - блокирует взгляд
2. ✅ Keep old panel, add features from new (resize, camera click)
3. ✅ Progress bar 10px (not 4px), VETKA blue
4. ✅ Counter рядом: `45/156 files`
5. ✅ "Clear All Scans" → маленькая иконка корзины 🗑
6. ✅ Add 300ms hover preview like search panel
7. ✅ Scan drawer should be AT TOP (after search, before messages)
8. ✅ Chat input must stay at bottom unchanged

---

## Implementation Plan

### Step 1: Move ScanProgressPanel to TOP
**File:** `ChatPanel.tsx`

Move from line 1991 (before MessageInput) to after ScannerPanel (line ~1893)

```tsx
{/* Phase 92.3: Scan Progress at TOP, not bottom */}
{(activeTab === 'chat' || activeTab === 'scanner') && (
  <ScanProgressPanel
    onFileClick={(path) => {
      selectNode(path);
      setCameraCommand({ target: path, zoom: 'close', highlight: true });
    }}
    position="top"  // New prop
  />
)}
```

### Step 2: Update ScanProgressPanel CSS
**File:** `ScanProgressPanel.css`

Change from `position: absolute; bottom: 0` to:
```css
.scan-progress-panel {
  position: relative;  /* In document flow */
  /* Remove bottom: 0 */
  flex-shrink: 0;
  max-height: 300px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);  /* Border on bottom, not top */
}
```

### Step 3: Update Progress Bar to 10px
**File:** `ScanProgressPanel.css`

```css
.scan-progress-bar {
  height: 10px;  /* Increased from 3px */
  border-radius: 5px;
  margin: 8px 12px;
}
```

### Step 4: Shrink "Clear All Scans" in ScannerPanel
**File:** `ScannerPanel.tsx` (lines 585-615)

Replace wide button with small icon:
```tsx
<button
  onClick={handleClearAll}
  title="Clear All Scans"
  style={{
    width: '32px',
    height: '32px',
    padding: '6px',
    background: '#2a2020',
    border: '1px solid #442a2a',
    borderRadius: '6px',
    color: '#cc6666',
    cursor: 'pointer',
  }}
>
  <TrashIcon /> {/* 16x16 SVG */}
</button>
```

### Step 5: Add 300ms Hover Preview
**File:** `ScanProgressPanel.tsx`

Add same pattern as UnifiedSearchBar:
```tsx
const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
const [hoveredFile, setHoveredFile] = useState<ScannedFile | null>(null);
const [previewPosition, setPreviewPosition] = useState({ x: 0, y: 0 });

const handleMouseEnter = (file: ScannedFile, e: React.MouseEvent) => {
  const rect = e.currentTarget.getBoundingClientRect();
  hoverTimerRef.current = setTimeout(() => {
    setHoveredFile(file);
    setPreviewPosition({ x: rect.right + 8, y: rect.top });
  }, 300);
};

const handleMouseLeave = () => {
  if (hoverTimerRef.current) {
    clearTimeout(hoverTimerRef.current);
    hoverTimerRef.current = null;
  }
  setHoveredFile(null);
};
```

### Step 6: Verify MessageInput Unchanged
Check that MessageInput still renders at bottom with no overlays.

---

## Files to Modify

| File | Changes |
|------|---------|
| `ChatPanel.tsx` | Move ScanProgressPanel render location to TOP |
| `ScanProgressPanel.tsx` | Add position prop, 300ms hover preview |
| `ScanProgressPanel.css` | position: relative, 10px progress bar |
| `ScannerPanel.tsx` | Shrink "Clear All Scans" to icon |

---

## Visual Design (Final)

```
┌─────────────────────────────────────────────────────┐
│ [Chat] [Scanner] [Group]                     [−][×] │
├─────────────────────────────────────────────────────┤
│ 🔍 Search...                                        │
├─────────────────────────────────────────────────────┤
│ Scanning... 45/156 files                       [🗑] │
│ ██████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ✓ src/api/routes.py              (hover → preview) │
│ ✓ src/api/handlers.py                              │
│ ✓ src/memory/engram.py                             │
│ ✓ src/agents/tools.py                              │
│                                       [▼ collapse] │
├─────────────────────────────────────────────────────┤
│                                                     │
│           Messages Area (flex: 1)                   │
│                                                     │
├─────────────────────────────────────────────────────┤
│ [Message input...                          ] [Send] │
└─────────────────────────────────────────────────────┘
```

---

## Status: IMPLEMENTING NOW
