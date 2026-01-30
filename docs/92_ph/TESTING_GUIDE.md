# ScanProgressPanel Testing Guide

**Phase:** 92
**Component:** ScanProgressPanel
**Status:** Ready for Testing

---

## Quick Test (Browser Console)

### 1. Start VETKA
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python main.py
```

### 2. Open Browser Console
Navigate to `http://localhost:5173` and open DevTools Console

### 3. Simulate Progress Events
```javascript
// Test progress event
window.dispatchEvent(new CustomEvent('scan_progress', {
  detail: {
    progress: 45,
    file_path: '/Users/test/project/src/main.py'
  }
}));

// Add more files
window.dispatchEvent(new CustomEvent('scan_progress', {
  detail: {
    progress: 60,
    file_path: '/Users/test/project/src/utils.py'
  }
}));

// Test completion
window.dispatchEvent(new CustomEvent('scan_complete', {
  detail: {
    filesCount: 1234
  }
}));
```

### 4. Expected Behavior
- Panel appears at bottom of chat
- Progress bar fills to 45%, then 60%
- Files appear in list with checkmarks
- After completion, shows "Scan Complete (1234 files)"
- Auto-hides after 3 seconds

---

## Full Integration Test

### Backend Setup

**File:** `/src/scanners/file_watcher.py`

Add progress event emission during scanning:

```python
# In _scan_directory or similar method
async def _scan_directory(self, path: str):
    files = list(Path(path).rglob('*'))
    total = len(files)

    for i, file_path in enumerate(files):
        if file_path.is_file():
            # Index file...
            await self._index_to_qdrant(file_path, wait=False)  # Non-blocking!

            # Emit progress event
            progress = int((i + 1) / total * 100)
            await self._emit_progress(progress, str(file_path))

    # Emit completion
    await self._emit_completion(total)

async def _emit_progress(self, progress: int, file_path: str):
    """Emit scan progress event to frontend"""
    event_data = {
        'progress': progress,
        'file_path': file_path,
        'status': 'scanning'
    }
    # Send via Socket.IO or HTTP endpoint
    # window.dispatchEvent(new CustomEvent('scan_progress', { detail: event_data }))

async def _emit_completion(self, files_count: int):
    """Emit scan completion event to frontend"""
    event_data = {
        'filesCount': files_count
    }
    # window.dispatchEvent(new CustomEvent('scan_complete', { detail: event_data }))
```

### Testing Steps

1. **Start Backend**
```bash
python main.py
```

2. **Open Frontend**
```
http://localhost:5173
```

3. **Open Scanner Tab**
- Click scanner icon in chat header
- Click "Add Folder"

4. **Add Large Folder**
```
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03
```

5. **Verify Panel Behavior**
- [ ] Panel appears at bottom during scan
- [ ] Progress bar animates smoothly
- [ ] Files appear in list as scanned
- [ ] Max 10 files shown (older ones removed)
- [ ] Panel shows "Scanning... X%"

6. **Test Interactions**
- [ ] Click header → panel collapses
- [ ] Click header again → panel expands
- [ ] Click file in list → camera navigates to file in 3D tree
- [ ] File gets highlighted in tree

7. **Test Completion**
- [ ] After scan, shows "Scan Complete (N files)"
- [ ] Progress bar at 100%
- [ ] Panel auto-hides after 3 seconds

---

## Manual Testing Checklist

### Visual Tests
- [ ] Panel appears at correct position (bottom of chat)
- [ ] Progress bar fills smoothly (no jumps)
- [ ] Checkmarks are visible and green (#4a9eff)
- [ ] Text is readable (#888 primary, #666 secondary)
- [ ] Hover states work (file items highlight)
- [ ] Scrollbar appears when >5 files
- [ ] Collapsed state shows only header + progress bar

### Functional Tests
- [ ] Panel hidden when not scanning
- [ ] Panel appears when scan starts
- [ ] Progress updates in real-time
- [ ] File list updates (FIFO, max 10)
- [ ] Collapse/expand toggles correctly
- [ ] File click triggers camera navigation
- [ ] Camera focuses on correct file
- [ ] Node highlights in 3D tree
- [ ] Auto-hide after completion (3s)

### Edge Cases
- [ ] Empty file path → no item added to list
- [ ] Very long file paths → truncated correctly
- [ ] Rapid progress updates → no UI lag
- [ ] Multiple scans in sequence → state resets properly
- [ ] Collapse during scan → progress still updates
- [ ] Click file during scan → navigation works
- [ ] Hover during scan → no visual glitches

### Browser Compatibility
- [ ] Chrome/Edge (primary)
- [ ] Firefox
- [ ] Safari
- [ ] Mobile Safari (if applicable)

### Performance Tests
- [ ] Large folder (1000+ files) → no lag
- [ ] Fast progress updates (100ms) → smooth
- [ ] Panel animations smooth (60fps)
- [ ] Memory usage stable (no leaks)

---

## Debugging Tips

### Component Not Showing
```javascript
// Check if component is mounted
document.querySelector('.scan-progress-panel')

// Check visibility prop
// Should be true when activeTab is 'chat' or 'scanner'
```

### Events Not Working
```javascript
// Test if events are being dispatched
window.addEventListener('scan_progress', (e) => {
  console.log('Progress event:', e.detail);
});

window.addEventListener('scan_complete', (e) => {
  console.log('Complete event:', e.detail);
});
```

### Camera Not Navigating
```javascript
// Check if selectNode and setCameraCommand are called
// Add console.log in onFileClick handler
```

### Progress Bar Not Animating
```css
/* Check if CSS transition is applied */
.scan-progress-fill {
  transition: width 0.3s ease; /* Should be present */
}
```

---

## Expected Console Output

### During Scan
```
[ScanProgressPanel] Progress: 10%
[ScanProgressPanel] File added: /path/to/file1.py
[ScanProgressPanel] Progress: 20%
[ScanProgressPanel] File added: /path/to/file2.tsx
...
```

### On Completion
```
[ScanProgressPanel] Scan complete: 1234 files
[ScanProgressPanel] Auto-hide in 3s
[ScanProgressPanel] Hidden
```

### On File Click
```
[ScanProgressPanel] File clicked: /path/to/file.py
[Camera] Focusing on: /path/to/file.py
[Camera] Zoom: close, Highlight: true
```

---

## Known Issues to Watch For

1. **Z-index conflicts** - Panel should overlay MessageInput
2. **Scroll jump** - Panel appearance shouldn't affect scroll position
3. **Memory leak** - Event listeners should clean up on unmount
4. **Race condition** - Multiple scans starting/stopping quickly
5. **File path encoding** - Special characters in paths

---

## Success Criteria

✅ Panel appears during scan without blocking UI
✅ Progress updates smoothly in real-time
✅ File list shows last 10 files with proper formatting
✅ Click file → camera navigates correctly
✅ Panel auto-hides 3s after completion
✅ No performance degradation during large scans
✅ Collapse/expand works smoothly
✅ All animations smooth (60fps)

---

## Rollback Plan

If issues occur:

1. **Disable component:**
```tsx
// In ChatPanel.tsx, comment out:
{/* <ScanProgressPanel ... /> */}
```

2. **Keep files for debugging:**
- Don't delete ScanProgressPanel.tsx
- Don't delete ScanProgressPanel.css

3. **Check browser console** for errors

4. **Report issues** in Phase 92 documentation

---

## Next Phase Integration

After successful testing:
- [ ] Add backend event emission
- [ ] Implement non-blocking Qdrant upsert
- [ ] Add scan statistics (files/sec)
- [ ] Add error indicators for failed files
- [ ] Consider file type icons

---

**Last Updated:** 2026-01-24
**Tester:** _____________
**Test Date:** _____________
**Result:** ⬜ PASS / ⬜ FAIL
**Notes:**
