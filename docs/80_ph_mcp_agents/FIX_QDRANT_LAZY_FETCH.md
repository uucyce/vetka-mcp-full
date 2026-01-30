# Phase 80.17: Fix Qdrant Client Singleton Bug

**Date:** 2026-01-22
**Status:** FIXED
**Files Modified:**
- `src/scanners/file_watcher.py`
- `src/initialization/components_init.py`

## Problem

The `VetkaFileWatcher` singleton was caching `qdrant_client=None` at initialization time and never updating it. This caused new files to NOT be indexed in Qdrant (only socket events were emitted).

### Root Cause

```python
# file_watcher.py __init__
self.qdrant_client = qdrant_client  # Cached at creation time

# During file change event
if self.qdrant_client:  # Always None if init was before Qdrant connect
    handle_watcher_event(...)
```

The watcher singleton was often created BEFORE Qdrant finished connecting (async background connection). Once created with `qdrant_client=None`, it never got updated even after Qdrant became available.

## Solution: Lazy Fetch Pattern (Variant 2)

Instead of caching the client at init time, fetch it lazily at each event time from `components_init`.

### Changes Made

#### 1. Added `get_qdrant_manager()` to `components_init.py`

```python
def get_qdrant_manager():
    """
    Get Qdrant manager instance (Phase 80.17).

    Used by file_watcher for lazy fetch of qdrant_client
    to fix the singleton caching bug where watcher was
    initialized before Qdrant connected.

    Returns:
        QdrantAutoRetry instance or None if not available
    """
    return qdrant_manager
```

#### 2. Added `_get_qdrant_client()` method to `VetkaFileWatcher`

```python
def _get_qdrant_client(self) -> Optional[Any]:
    """
    Phase 80.17: Lazy fetch Qdrant client.

    The watcher singleton may be created BEFORE Qdrant connects.
    This method fetches the client at event time, not at init time.
    """
    # First check instance variable (may have been set via get_watcher update)
    if self.qdrant_client is not None:
        return self.qdrant_client

    # Phase 80.17: Lazy fetch from components_init
    try:
        from src.initialization.components_init import get_qdrant_manager
        manager = get_qdrant_manager()
        if manager and hasattr(manager, 'client') and manager.client:
            # Cache for future calls
            self.qdrant_client = manager.client
            print("[Watcher] Phase 80.17: Lazy fetched qdrant_client from components_init")
            return manager.client
    except ImportError as e:
        print(f"[Watcher] Phase 80.17: Cannot import components_init: {e}")
    except Exception as e:
        print(f"[Watcher] Phase 80.17: Error fetching qdrant_client: {e}")

    return None
```

#### 3. Updated `_on_file_change()` to use lazy fetch

```python
# Phase 80.17: Lazy fetch qdrant_client (fixes singleton cache bug)
qdrant_client = self._get_qdrant_client()
if qdrant_client:
    try:
        handle_watcher_event(event, qdrant_client=qdrant_client)
        print(f"[Watcher] Indexed to Qdrant: {path}")
    except Exception as e:
        print(f"[Watcher] Error updating Qdrant index: {e}")
else:
    print(f"[Watcher] WARNING: qdrant_client not available (lazy fetch failed)")
```

## Why This Solution

### Considered Alternatives

1. **Variant 1: Getter function** - Pass a callable that returns the client. More complex, requires API changes.

2. **Variant 2: Lazy fetch (CHOSEN)** - Fetch from `components_init` at event time. Simple, reliable, no API changes.

3. **Variant 3: Update method in `get_watcher()`** - Already partially implemented (lines 571-574), but only works if `get_watcher()` is called again with a client.

### Why Variant 2 is Best

- **Simple**: No changes to `get_watcher()` API
- **Reliable**: Works even if `get_watcher()` is never called again after init
- **Efficient**: Caches the client after first successful fetch
- **Backward compatible**: Falls back to instance variable if set

## Testing

After this fix:
1. Start VETKA server
2. Wait for "Qdrant is now connected!" message
3. Create/modify a file in a watched directory
4. Check logs for: `[Watcher] Phase 80.17: Lazy fetched qdrant_client from components_init`
5. Verify: `[Watcher] Indexed to Qdrant: <path>`

## Logging

New log messages added:
- `[Watcher] Phase 80.17: Lazy fetched qdrant_client from components_init` - Success
- `[Watcher] Phase 80.17: Cannot import components_init: <error>` - Import failed
- `[Watcher] Phase 80.17: Error fetching qdrant_client: <error>` - Other error
- `[Watcher] WARNING: qdrant_client not available (lazy fetch failed)` - Client still unavailable
