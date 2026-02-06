# Phase 115 BUG-4: Pinned Files Persistence Implementation

**Date:** 2026-02-06
**Agent:** Sonnet 4.5
**Status:** ✅ Complete

---

## Overview

Implemented persistent storage for global CAM pinned files by replacing the in-memory `_pinned_files` dictionary with a `PinnedFilesService` that persists to `data/pinned_files.json`.

## What Was Done

### 1. Created `PinnedFilesService` Class

**Location:** `/src/api/routes/cam_routes.py` (lines 44-184)

The service provides:
- **Async file I/O** with `asyncio.Lock()` for concurrency
- **Automatic persistence** on every write operation
- **Backward-compatible property** for sync code access
- **Graceful initialization** with both async and sync loading paths

**Key Methods:**
```python
async def load()                    # Load from JSON on startup
async def add_pin(path, reason, ts) # Add pin and persist
async def remove_pin(path)          # Remove pin and persist
async def get_all_pins()            # Get all as list of tuples
async def save()                    # Manual save (public)
def ensure_loaded()                 # Sync fallback for MCP
@property pinned_files -> Dict      # Backward-compatible access
```

### 2. Updated `cam_routes.py`

**Line 258-260:** Replaced dict with service instance
```python
# Phase 115 BUG-4: Pinned files service with JSON persistence
_pinned_service = PinnedFilesService(json_path="data/pinned_files.json")
# Backward-compatible reference for sync code (pinned_files_tool.py)
_pinned_files = _pinned_service.pinned_files
```

**Line 653-655:** Updated write in `pin_file_for_context()`
```python
# Store pinned file with persistence (Phase 115 BUG-4)
await _pinned_service.add_pin(file_path, reason, timestamp)
```

**Line 696-698:** Updated read in `get_pinned_files()`
```python
# Get pinned files from service (Phase 115 BUG-4)
pins = await _pinned_service.get_all_pins()
```

**Line 249-256:** Added startup initialization function
```python
async def initialize_pinned_files_service():
    """Initialize and load pinned files service on app startup."""
    try:
        await _pinned_service.load()
        logger.info("[CAM] Pinned files service initialized")
    except Exception as e:
        logger.error(f"[CAM] Failed to initialize pinned files service: {e}")
```

### 3. Updated `pinned_files_tool.py`

**Line 182-186:** Updated import and ensured service is loaded
```python
# Phase 115 BUG-4: Import service and ensure it's loaded
from src.api.routes.cam_routes import _pinned_service, _pinned_files
# Ensure service is loaded for sync context
_pinned_service.ensure_loaded()
```

**Line 190:** No change needed - still uses `_pinned_files.items()`
```python
# Phase 115 BUG-4: Access via backward-compatible property
for file_path, data in _pinned_files.items():
```

The tool continues to work in sync context by accessing the service's internal dict via the `pinned_files` property.

### 4. Updated `main.py`

**Line 216-220:** Added service initialization in lifespan
```python
# === PHASE 115 BUG-4: Initialize pinned files service ===
try:
    from src.api.routes.cam_routes import initialize_pinned_files_service
    await initialize_pinned_files_service()
    logger.info("[Startup] Pinned files service initialized")
except Exception as e:
    logger.error(f"[Startup] Pinned files service init failed: {e}")
```

---

## JSON File Format

**Location:** `data/pinned_files.json`

**Structure:**
```json
{
  "pins": {
    "/absolute/path/to/file.py": {
      "reason": "Working on authentication",
      "timestamp": "2026-02-06T10:30:00Z"
    }
  },
  "last_updated": "2026-02-06T10:30:00Z"
}
```

---

## Architecture Decisions

### Why Service in `cam_routes.py`?
- Keeps related code together
- Avoids circular imports
- Simple deployment (no new module file)

### Sync vs Async Boundary
The service handles the async/sync boundary elegantly:
- **FastAPI routes** use `await service.add_pin()` (async)
- **MCP tool** uses `_pinned_files.items()` (sync via property)
- **Startup** calls `service.ensure_loaded()` for sync fallback

### Concurrency Strategy
- Uses `asyncio.Lock()` (not `threading.Lock()`)
- Lock protects both in-memory dict AND file writes
- Prevents race conditions in async environment

### Persistence Strategy
- **Write-through cache:** Every add/remove immediately persists
- **No debouncing:** Simplicity over performance (pins are infrequent)
- **Atomic writes:** Uses `run_in_executor` for non-blocking I/O

---

## Testing

**Test Results:** ✅ All Passed

Created and ran two test scripts:

1. **`test_pinned_service.py`** - Core functionality
   - Service initialization
   - Adding pins
   - Getting all pins
   - Persistence verification
   - Sync property access
   - Remove pin
   - Load existing data

2. **`test_pinned_tool_compat.py`** - Backward compatibility
   - Import from `cam_routes`
   - Ensure service loads in sync context
   - Verify dict-like interface
   - Test `.items()` iteration

Both tests passed without errors.

---

## Files Modified

| File | Lines Changed | Type |
|------|---------------|------|
| `src/api/routes/cam_routes.py` | +152 lines | Major (service class + updates) |
| `src/mcp/tools/pinned_files_tool.py` | 3 lines | Minor (import update) |
| `main.py` | 6 lines | Minor (startup init) |
| `docs/115_ph/SONNET_BUG4_IMPLEMENTATION.md` | NEW | Documentation |

**Total:** 161 lines added, 5 lines modified, 0 lines removed

---

## What Was NOT Changed

Per requirements, we did NOT touch:
- ✅ Chat-level pins (`pinned_file_ids` in `chat_history.json`) - Already persisted
- ✅ `chat_history_manager.py` - No changes needed
- ✅ REST endpoint signatures - Same API surface
- ✅ Existing data structures - Backward compatible

---

## Verification Checklist

- [x] All 5 `MARKER_115_BUG4` comments addressed
- [x] Service uses `asyncio.Lock()` for concurrency
- [x] Persists to `data/pinned_files.json`
- [x] On first start: creates empty JSON file
- [x] On load: reads existing pins from JSON
- [x] On write: updates in-memory dict + writes to JSON immediately
- [x] Exposes `_pinned_files` property for backward compatibility
- [x] Startup initialization in `main.py` lifespan
- [x] Sync access works from `pinned_files_tool.py`
- [x] All Python files compile without syntax errors
- [x] Test scripts pass all assertions

---

## Future Improvements (Out of Scope)

1. **Debouncing:** Batch writes if pins become frequent
2. **Migration:** Move to Qdrant for vector-based suggestions
3. **Expiration:** Auto-remove old pins after N days
4. **Per-chat pins:** Unify global and chat-level pin storage

---

## Notes

- The service initializes even if JSON file doesn't exist (creates empty file)
- Thread-safe for async contexts (uses `asyncio.Lock`)
- Sync access is safe because it only reads the internal dict
- File writes are non-blocking via `run_in_executor`
- Service is backward-compatible with existing code

**Status:** Ready for production ✅
