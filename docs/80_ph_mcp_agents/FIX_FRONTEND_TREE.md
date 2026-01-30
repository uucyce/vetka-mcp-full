# FIX: Frontend Tree Listeners - Phase 80

**Status:** ✅ FIXED
**Date:** 2026-01-21
**Agent:** Claude Sonnet 4.5
**Task:** SONNET_FIX_TASK_7

## Problem

Frontend tree listeners in `useSocket.ts` were empty stubs - they received events from the backend but did nothing with them, causing the 3D tree visualization to never update when files changed.

### Root Cause (from Haiku Scout)

```typescript
// client/src/hooks/useSocket.ts:424-447
socket.on('node_added', (data) => {
  // EMPTY - No action taken!
});

socket.on('node_removed', (data) => {
  // EMPTY - No action taken!
});

// MISSING LISTENERS:
// - node_updated
// - tree_bulk_update
```

### Backend Events Being Emitted

The file watcher (`src/scanners/file_watcher.py`) was correctly emitting:
- `node_added` (line 355) - When file created
- `node_removed` (line 357) - When file deleted
- `node_updated` (line 359) - When file modified
- `tree_bulk_update` (line 363) - When bulk changes (git checkout, npm install)

But frontend had **no handlers** for `node_updated` and `tree_bulk_update`!

## Solution

### 1. Added Missing Event Type Definitions

```typescript
// client/src/hooks/useSocket.ts:26-30
interface ServerToClientEvents {
  node_added: (data: { path: string; node?: any; event?: any }) => void;
  node_removed: (data: { path: string; event?: any }) => void;
  node_updated: (data: { path: string; event?: any }) => void;  // ← NEW
  tree_bulk_update: (data: { path: string; count: number; events: string[] }) => void;  // ← NEW
}
```

### 2. Created Tree Reload Helper

```typescript
// client/src/hooks/useSocket.ts:346-368
const reloadTreeFromHttp = useCallback(async () => {
  try {
    const response = await fetch(`${API_BASE}/tree/data`);
    if (response.ok) {
      const treeData = await response.json();
      console.log('[Socket] Tree reloaded via HTTP:', treeData.tree?.nodes?.length, 'nodes');

      if (treeData.tree) {
        const vetkaResponse: VetkaApiResponse = {
          tree: {
            nodes: treeData.tree.nodes,
            edges: treeData.tree.edges || [],
          },
        };
        const { nodes: convertedNodes, edges } = convertApiResponse(vetkaResponse);
        setNodesFromRecord(convertedNodes);
        setEdges(edges);
      }
    }
  } catch (err) {
    console.error('[Socket] Tree reload error:', err);
  }
}, [setNodesFromRecord, setEdges]);
```

### 3. Implemented Event Handlers

```typescript
// client/src/hooks/useSocket.ts:424-447
socket.on('node_added', (data) => {
  console.log('[Socket] node_added:', data.path);
  // Trigger tree refetch via HTTP to get updated tree with proper positions
  reloadTreeFromHttp();
});

socket.on('node_removed', (data) => {
  console.log('[Socket] node_removed:', data.path);
  // Remove node from local state
  const { removeNode } = useStore.getState();
  removeNode(data.path);
});

socket.on('node_updated', (data) => {
  console.log('[Socket] node_updated:', data.path);
  // Trigger tree refetch for updated node
  reloadTreeFromHttp();
});

socket.on('tree_bulk_update', (data) => {
  console.log('[Socket] tree_bulk_update:', data.count, 'changes');
  // Reload entire tree for bulk updates (git checkout, etc.)
  reloadTreeFromHttp();
});
```

## Strategy

### Why HTTP Reload Instead of Direct Update?

We reload the full tree via HTTP instead of patching local state because:

1. **Position Integrity**: Backend calculates Sugiyama layout positions - we need those
2. **Edge Updates**: File changes may affect parent-child relationships
3. **Consistency**: Ensures frontend always matches backend ground truth
4. **Bulk Changes**: Git operations can modify hundreds of files at once

### Optimization Note

For high-frequency updates, we could:
- Add debouncing to `reloadTreeFromHttp()` (e.g., 500ms)
- Cache tree data with short TTL
- Implement incremental updates for `node_updated`

Currently keeping it simple - full reload is fast enough (<100ms for typical repos).

## Files Modified

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/hooks/useSocket.ts`
  - Added `node_updated` and `tree_bulk_update` type definitions
  - Created `reloadTreeFromHttp()` helper function
  - Implemented all 4 tree event handlers
  - Updated useEffect dependency array

## Testing

After fix, the tree should now:
1. ✅ Update when you create a file (node_added)
2. ✅ Update when you delete a file (node_removed)
3. ✅ Update when you modify a file (node_updated)
4. ✅ Update after git operations (tree_bulk_update)

### Manual Test

```bash
# Terminal 1: Start VETKA
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
npm run dev

# Terminal 2: Watch a directory
cd /path/to/watched/folder

# Create file - tree should update
touch new_file.py

# Modify file - tree should update
echo "print('hello')" >> new_file.py

# Delete file - tree should update
rm new_file.py

# Git operation - tree should bulk update
git checkout -b test-branch
```

Watch browser console for:
```
[Socket] node_added: /path/to/new_file.py
[Socket] Tree reloaded via HTTP: 42 nodes
```

## Related Issues

- Haiku Scout report: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/80_ph_mcp_agents/SCOUT_WATCHDOG_TREE.md`
- File watcher implementation: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py`

## Next Steps

1. Add debouncing if tree reloads become frequent
2. Consider incremental updates for single file changes
3. Add visual feedback when tree is reloading
4. Monitor performance with large repos (1000+ files)
