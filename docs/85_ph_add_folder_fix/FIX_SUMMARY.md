# Phase 85: Add Folder Scan Bug Fix

## Problem
When adding a folder via the "Add Folder" button in ScannerPanel, the `filesCount` was not being passed to the `directory_added` event, causing ChatPanel to display a generic message instead of showing the actual file count.

## Root Cause
In `handleAddFolder` callback (line 452-465), the API response was consumed but the result was never stored:

```javascript
// BEFORE (broken)
if (response.ok) {
  await response.json();  // result ignored!
  onEvent?.({ type: 'directory_added', path: fullPath.trim() }); // no filesCount!
}
```

## Fix Applied
File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/scanner/ScannerPanel.tsx`

Lines 452-469:
```javascript
// AFTER (fixed)
if (response.ok) {
  const result = await response.json();
  onEvent?.({
    type: 'directory_added',
    path: fullPath.trim(),
    filesCount: result.indexed_count || result.files_count || 0
  });
}
```

## How It Works
1. Backend `/watcher/add` returns `{ indexed_count: N }` after scanning
2. Frontend now captures this result
3. Event includes `filesCount` for ChatPanel to display
4. ChatPanel already handles `filesCount` correctly (lines 882-890)

## ChatPanel Message Logic
- `filesCount > 1000`: "Wow! X files... This is a serious project!"
- `filesCount > 100`: "Great! X files from..."
- `filesCount > 0`: "X files from... Drop more folders!"
- `filesCount == 0`: "... added! Files will be indexed."

## Verified
- Fix applied to correct location
- Fallback chain: `indexed_count || files_count || 0`
- ChatPanel handler confirmed at lines 861-911

## Date
2026-01-21
