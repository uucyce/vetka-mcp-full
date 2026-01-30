# Phase 92: Scanning UI Audit Report

**Date:** 2026-01-24
**Auditors:** Haiku Agent + Grok Research
**Status:** Ready for Implementation

---

## Summary

Kimi K2 identified that blocking Ollama/Qdrant calls freeze FastAPI during scanning.
This audit maps existing UI patterns for adding **non-blocking scan progress** to ChatPanel.

---

## Key Files

| Component | File | Lines |
|-----------|------|-------|
| Chat Panel | `/client/src/components/chat/ChatPanel.tsx` | 2,032 |
| Scanner Panel | `/client/src/components/scanner/ScannerPanel.tsx` | 670 |
| Search Bar | `/client/src/components/search/UnifiedSearchBar.tsx` | 1,182 |
| Camera Controller | `/client/src/components/canvas/CameraController.tsx` | 150+ |
| Socket Hook | `/client/src/hooks/useSocket.ts` | 80 |

---

## MARKER-92-SCAN: Scanning Progress

### Existing Pattern (ScannerPanel.tsx:160-221)

```typescript
// State
const [isScanning, setIsScanning] = useState(false);
const [progress, setProgress] = useState(0);

// Window event listeners
useEffect(() => {
  const handleScanProgress = (event: CustomEvent<{ progress: number }>) => {
    setProgress(event.detail.progress);
    setIsScanning(true);
  };

  const handleScanComplete = (event: CustomEvent<{ filesCount?: number }>) => {
    setIsScanning(false);
    setProgress(0);
  };

  window.addEventListener('scan_progress', handleScanProgress as EventListener);
  window.addEventListener('scan_complete', handleScanComplete as EventListener);

  return () => { /* cleanup */ };
}, []);
```

### Progress Bar CSS (ScannerPanel.css:249-262)

```css
.progress-bar {
  height: 3px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: rgba(255, 255, 255, 0.6);
  transition: width 0.3s ease;
}
```

---

## MARKER-92-CAMERA: Camera Navigation Pattern

### Existing Pattern (UnifiedSearchBar.tsx:746-757)

```typescript
const handleSearchSelect = useCallback((result: SearchResult) => {
  if (result.path) {
    selectNode(result.path);
    setCameraCommand({
      target: result.path,
      zoom: 'close',
      highlight: true
    });
  }
}, [selectNode, setCameraCommand]);
```

### CameraCommand Interface

```typescript
interface CameraCommand {
  target: string;        // File path to focus on
  zoom: 'close' | 'medium' | 'far';
  highlight?: boolean;
}
```

---

## Socket Events (useSocket.ts)

```typescript
interface ServerToClientEvents {
  scan_progress: (data: { progress: number; status: string }) => void;
  scan_complete: (data: { nodes_count: number }) => void;
  directory_scanned: (data: { path: string; files_count: number }) => void;
  camera_control: (data: { action: string; target: string }) => void;
}
```

---

## Grok's UX Recommendation

**Hybrid Approach:**
1. **Linear progress bar** - Overall % at bottom of chat
2. **File list with checkmarks** - Real-time scanned files
3. **Click-to-navigate** - Camera flies to file in 3D

**Why not animated tree?** Too heavy for progress indicator.

---

## Implementation Plan

### 1. Add ScanProgressPanel Component

```typescript
// /client/src/components/chat/ScanProgressPanel.tsx
interface ScanProgressPanelProps {
  onFileClick: (path: string) => void;
}

const ScanProgressPanel: React.FC<ScanProgressPanelProps> = ({ onFileClick }) => {
  const [isScanning, setIsScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [scannedFiles, setScannedFiles] = useState<string[]>([]);

  // Listen to window events (same pattern as ScannerPanel)

  return (
    <div className="scan-progress-panel">
      {isScanning && (
        <>
          <div className="progress-header">
            <span>Scanning... {progress}%</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <ul className="scanned-files-list">
            {scannedFiles.slice(-10).map((file, i) => (
              <li key={i} onClick={() => onFileClick(file)}>
                <CheckIcon /> {file.split('/').pop()}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
};
```

### 2. Integrate in ChatPanel

```typescript
// ChatPanel.tsx - at bottom of chat area
<ScanProgressPanel
  onFileClick={(path) => {
    selectNode(path);
    setCameraCommand({ target: path, zoom: 'close', highlight: true });
  }}
/>
```

### 3. Backend: Non-blocking Scan (Kimi K2 fix)

```python
# file_watcher.py - Change wait=True to wait=False
await collection.upsert(points, wait=False)  # Non-blocking

# Or use BackgroundTasks
from fastapi import BackgroundTasks
bg_tasks.add_task(self._index_to_qdrant, file_path)
```

---

## CSS Additions

```css
.scan-progress-panel {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.8);
  border-top: 1px solid #333;
  max-height: 200px;
  overflow: hidden;
}

.scanned-files-list {
  max-height: 150px;
  overflow-y: auto;
  padding: 8px;
}

.scanned-files-list li {
  cursor: pointer;
  padding: 4px 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.scanned-files-list li:hover {
  background: rgba(255, 255, 255, 0.1);
}
```

---

## Testing

```bash
# Start VETKA
python main.py

# Add large folder to trigger scan
curl -X POST http://localhost:5001/api/watcher/add \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/large/folder"}'

# Verify UI doesn't freeze
curl http://localhost:5001/api/health  # Should respond instantly
```

---

## Next Steps

1. [ ] Create `ScanProgressPanel.tsx` component
2. [ ] Add to ChatPanel at bottom
3. [ ] Wire up camera navigation on file click
4. [ ] Apply Kimi K2's backend fix (wait=False)
5. [ ] Test with large folder scan
