# HAIKU_BUG4_MARKERS - Phase 115 Bug Fix Planning

## Task: Pinned Files Persistence

**Objective:** Place `MARKER_115_BUG4` comments at all locations that need to be changed for implementing `PinnedFilesService` with JSON persistence.

**DO NOT IMPLEMENT** — only mark locations for future implementation.

---

## Files Modified

### 1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/cam_routes.py`

#### Line 103: Dictionary Definition
**MARKER ADDED:**
```python
# Phase 99.3: Pinned files for JARVIS-like context suggestions
# MARKER_115_BUG4: Replace with PinnedFilesService(json_path="data/pinned_files.json")
_pinned_files: Dict[str, dict] = {}  # file_path -> {reason, timestamp}
```

**Action needed in fix:**
- Replace the module-level `_pinned_files` dict with a `PinnedFilesService` instance
- Service should initialize from `data/pinned_files.json` on startup
- Use `asyncio.Lock()` for thread-safe concurrent access

---

#### Line 583: WRITE - pin_file_for_context() endpoint
**MARKER ADDED:**
```python
        # Store pinned file
        # MARKER_115_BUG4: WRITE - Replace _pinned_files[file_path] = {...} with await service.add_pin(file_path, reason)
        _pinned_files[file_path] = {
            "reason": reason,
            "timestamp": timestamp
        }
```

**Action needed in fix:**
- Replace dict assignment with async method call: `await service.add_pin(file_path, reason, timestamp)`
- Make endpoint async if not already
- Service method should handle persistence to JSON file

---

#### Line 631: READ - get_pinned_files() endpoint
**MARKER ADDED:**
```python
        # Format pinned files
        # MARKER_115_BUG4: READ - Replace _pinned_files.items() with await service.get_all_pins()
        pinned_list = [
            {
                "file_path": file_path,
                "reason": data.get("reason", ""),
                "timestamp": data.get("timestamp", "")
            }
            for file_path, data in _pinned_files.items()
        ]
```

**Action needed in fix:**
- Replace `_pinned_files.items()` with `await service.get_all_pins()`
- Service method should return list of tuples `(file_path, data_dict)` or similar structure

---

### 2. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/pinned_files_tool.py`

#### Line 182: IMPORT - _get_pinned_from_cam() method
**MARKER ADDED:**
```python
        try:
            # Try to import from cam_routes (requires FastAPI to be available)
            try:
                # MARKER_115_BUG4: IMPORT - Update to use PinnedFilesService instead of _pinned_files dict
                from src.api.routes.cam_routes import _pinned_files
            except ImportError as e:
                logger.debug(f"[PinnedFilesTool] CAM routes not available: {e}")
                return []
```

**Action needed in fix:**
- Change import from `_pinned_files` dict to `PinnedFilesService` instance (or getter function)
- Alternative: Import a function that returns the service singleton

---

#### Line 189: READ - _get_pinned_from_cam() method
**MARKER ADDED:**
```python
            pinned_list = []

            # MARKER_115_BUG4: READ - Replace _pinned_files.items() with await service.get_all_pins()
            for file_path, data in _pinned_files.items():
```

**Action needed in fix:**
- Replace `_pinned_files.items()` with `await service.get_all_pins()`
- Ensure async/await properly chains up through `_get_pinned_from_cam()`

---

## Summary of Changes Required

### Files to Create
1. **`src/services/pinned_files_service.py`** (NEW)
   - Class: `PinnedFilesService`
   - Methods:
     - `__init__(json_path: str)` — initialize with file path
     - `async load()` — load from JSON on startup
     - `async add_pin(file_path: str, reason: str, timestamp: str)` — add pin and persist
     - `async get_all_pins()` -> List[Tuple[str, dict]]` — return all pins
     - `async remove_pin(file_path: str)` — remove pin and persist
     - `async save()` — write current state to JSON file
   - **Concurrency:** Use `asyncio.Lock()` for thread-safe access
   - **Format:** Store as JSON in `data/pinned_files.json`

### Files to Modify (with markers placed)
1. **`src/api/routes/cam_routes.py`** — 3 markers placed
   - Replace `_pinned_files` dict with service instance
   - Update both endpoints to use service methods
   - Add service initialization on module load

2. **`src/mcp/tools/pinned_files_tool.py`** — 2 markers placed
   - Update import to use service
   - Update `_get_pinned_from_cam()` to call service methods

### Marker Summary

| File | Line | Type | Description |
|------|------|------|-------------|
| cam_routes.py | 103 | DEFINITION | Replace dict with service initialization |
| cam_routes.py | 583 | WRITE | Replace assignment with `await service.add_pin()` |
| cam_routes.py | 631 | READ | Replace `.items()` with `await service.get_all_pins()` |
| pinned_files_tool.py | 182 | IMPORT | Update import to PinnedFilesService |
| pinned_files_tool.py | 189 | READ | Replace `.items()` with `await service.get_all_pins()` |

---

## Implementation Notes

### Persistence Strategy
- **Format:** JSON file at `data/pinned_files.json`
- **Schema:**
  ```json
  {
    "pins": {
      "/path/to/file.py": {
        "reason": "Working on authentication",
        "timestamp": "2026-02-06T10:30:00Z"
      },
      ...
    },
    "last_updated": "2026-02-06T10:30:00Z"
  }
  ```

### Concurrency
- Use `asyncio.Lock()` (NOT `threading.Lock()`)
- Serialize access to both in-memory dict and JSON file writes
- Lock acquired during both reads and writes to prevent race conditions

### Startup/Shutdown
- On app startup: Call `await service.load()` to restore pins from disk
- On shutdown: Ensure any pending writes are flushed (consider debouncing)

### What NOT to Touch
- **Chat-level pins** (`pinned_file_ids` in `chat_history.json`) — Already persisted, leave as-is
- `chat_history_manager.py` — No changes needed
- REST endpoints remain the same, just internally use the service

---

## Verification Checklist

Before marking complete:
- [ ] All 5 `MARKER_115_BUG4` comments placed correctly
- [ ] No code logic changed (comments only)
- [ ] Markers provide clear guidance on what to replace
- [ ] No other files that directly access `_pinned_files` missed

---

## Related Tasks

- **BUG-3** (Context DAG caching) — Independent, uses REST API
- **BUG-5+** (Memory service improvements) — Can wait, independent

**Status:** ✅ Markers placed, ready for implementation phase.
