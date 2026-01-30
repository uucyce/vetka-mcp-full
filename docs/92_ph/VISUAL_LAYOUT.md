# ScanProgressPanel Visual Layout

## ChatPanel Structure (Before)

```
┌─────────────────────────────────────────┐
│ Header (tabs, buttons)                  │
├─────────────────────────────────────────┤
│ Search Bar (UnifiedSearchBar)           │
├─────────────────────────────────────────┤
│                                         │
│                                         │
│ Messages (MessageList)                  │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│ MessageInput                            │
└─────────────────────────────────────────┘
```

## ChatPanel Structure (After - Phase 92)

```
┌─────────────────────────────────────────┐
│ Header (tabs, buttons)                  │
├─────────────────────────────────────────┤
│ Search Bar (UnifiedSearchBar)           │
├─────────────────────────────────────────┤
│                                         │
│                                         │
│ Messages (MessageList)                  │
│                                         │
│                                         │
├─────────────────────────────────────────┤ ← NEW
│ ▼ Scanning... 45% [Settings]           │ ← ScanProgressPanel
│ ━━━━━━━━━━━░░░░░░░░░░░░░░░░░░░░░       │ ← (absolute position)
│   Recently scanned:                     │
│   ✓ file1.py                            │ ← (clickable)
│   ✓ file2.tsx                           │ ← (max 10 files)
├─────────────────────────────────────────┤
│ MessageInput                            │
└─────────────────────────────────────────┘
```

## ScanProgressPanel States

### Expanded (Default)
```
┌─────────────────────────────────────────┐
│ ▼ Scanning... 67%                  [▼]  │ ← Header (clickable)
│ ━━━━━━━━━━━━━━━━━░░░░░░░░░░░░░░░░░     │ ← Progress bar
│   Recently scanned:                     │ ← Label
│   ✓ src/components/Panel.tsx            │ ← File 1
│   ✓ src/utils/helper.ts                 │ ← File 2
│   ✓ public/assets/logo.svg              │ ← File 3
│   ... (up to 10)                        │
└─────────────────────────────────────────┘
    └─ max-height: 220px
```

### Collapsed
```
┌─────────────────────────────────────────┐
│ ▲ Scanning... 67%                  [▲]  │ ← Header only
│ ━━━━━━━━━━━━━━━━━░░░░░░░░░░░░░░░░░     │ ← Progress bar
└─────────────────────────────────────────┘
    └─ max-height: 42px
```

### Complete (auto-hide after 3s)
```
┌─────────────────────────────────────────┐
│ ▼ Scan Complete (1234 files)       [▼]  │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │ ← 100% filled
│   Recently scanned:                     │
│   ✓ last_file.py                        │
│   ✓ another_file.tsx                    │
└─────────────────────────────────────────┘
    └─ Fades out after 3 seconds
```

## Interaction Flow

### 1. User Adds Folder to Scanner
```
User: Clicks "Add Folder" in ScannerPanel
   ↓
Backend: Starts scanning, emits events
   ↓
ScanProgressPanel: Shows at bottom
```

### 2. During Scan
```
Backend: scan_progress { progress: 45, file_path: "/path/file.py" }
   ↓
ScanProgressPanel:
  - Updates progress bar to 45%
  - Adds "file.py" to list with checkmark
  - Keeps last 10 files (FIFO)
```

### 3. Click File in List
```
User: Clicks "✓ file.py"
   ↓
onFileClick(path) → selectNode(path)
   ↓
setCameraCommand({ target: path, zoom: 'close', highlight: true })
   ↓
Camera: Flies to file in 3D tree, highlights it
```

### 4. Completion
```
Backend: scan_complete { filesCount: 1234 }
   ↓
ScanProgressPanel:
  - Shows "Scan Complete (1234 files)"
  - Progress bar at 100%
  - Auto-hide after 3 seconds
```

## CSS Classes

```css
.scan-progress-panel           /* Container */
  .expanded / .collapsed       /* State modifier */

  .scan-progress-header        /* Header row */
    .scan-progress-title       /* Left text */
    .collapse-btn              /* Right button */

  .scan-progress-bar           /* Progress container */
    .scan-progress-fill        /* Blue fill */

  .scanned-files-container     /* Files section */
    .scanned-files-label       /* "Recently scanned:" */
    .scanned-files-list        /* UL */
      .scanned-file-item       /* LI (clickable) */
        .check-icon            /* ✓ */
        .file-name             /* Filename */
```

## Z-Index Layers

```
MessageInput           z-index: auto
ScanProgressPanel      z-index: 100  ← Overlays input area
FloatingWindow         z-index: 1000
```

## Positioning

```css
position: absolute;
bottom: 0;              /* Above MessageInput */
left: 0;
right: 0;
background: rgba(0, 0, 0, 0.85);
backdrop-filter: blur(10px);
```

## Color Scheme (Dark Theme)

```
Background:     rgba(0, 0, 0, 0.85)
Border:         rgba(255, 255, 255, 0.1)
Progress Bar:   #4a9eff (blue gradient)
Checkmarks:     #4a9eff
Text Primary:   #888
Text Secondary: #666
Hover:          rgba(255, 255, 255, 0.08)
```
