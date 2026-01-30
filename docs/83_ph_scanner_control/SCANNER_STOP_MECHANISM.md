# Phase 83: Scanner Stop Mechanism and Targeted Scanning

## Overview

Phase 83 addresses critical issues with the VETKA scanner:
1. `/api/scanner/rescan` was ignoring the `path` parameter and scanning everything
2. No way to stop a running scan (Ctrl+C didn't work)
3. Scans taking hours with no ability to interrupt

## Changes Made

### 1. QdrantIncrementalUpdater (`src/scanners/qdrant_updater.py`)

Added stop flag mechanism to enable graceful scan interruption:

```python
# New attributes
self._stop_requested: bool = False

# New methods
def request_stop(self) -> None:
    """Request the updater to stop processing."""
    self._stop_requested = True

def reset_stop(self) -> None:
    """Reset the stop flag before starting a new scan."""
    self._stop_requested = False

def is_stop_requested(self) -> bool:
    """Check if stop has been requested."""
    return self._stop_requested
```

The `batch_update()` method now checks `_stop_requested` at multiple points:
- Before filtering files for changes
- Before starting the batch update
- During the embedding loop

The `get_stats()` method now includes `stop_requested` in its output.

### 2. Fixed `/api/scanner/rescan` Endpoint (`src/api/routes/semantic_routes.py`)

The endpoint now properly handles the `path` parameter:

- **Before:** Ignored `path` parameter, always scanned from `Path.cwd()`
- **After:** Uses `path` parameter for targeted scanning when provided

Key changes:
- Properly resolves and expands the path (`expanduser().resolve()`)
- Validates that path is a directory
- Resets stop flag before starting new scan
- Checks stop flag in the main scan loop
- Returns `stopped: true` if scan was interrupted
- Emits `scan_stopped` socket event if interrupted

### 3. New Endpoints

#### `POST /api/scanner/stop`
Stops a running scan gracefully.

**Response:**
```json
{
    "success": true,
    "status": "stop_requested",
    "message": "Stop signal sent - scan will halt at next checkpoint",
    "current_stats": {
        "updated_count": 150,
        "skipped_count": 45,
        "deleted_count": 0,
        "error_count": 2,
        "collection": "vetka_elisya",
        "stop_requested": true
    }
}
```

#### `GET /api/scanner/status`
Gets current scanner status.

**Response:**
```json
{
    "success": true,
    "stop_requested": false,
    "stats": {
        "updated_count": 0,
        "skipped_count": 0,
        "deleted_count": 0,
        "error_count": 0,
        "collection": "vetka_elisya",
        "stop_requested": false
    }
}
```

## Usage Examples

### Targeted Scan (specific directory only)
```bash
curl -X POST "http://localhost:8000/api/scanner/rescan?path=/Users/me/project/src"
```

### Full Project Scan (no path = current working directory)
```bash
curl -X POST "http://localhost:8000/api/scanner/rescan"
```

### Stop Running Scan
```bash
curl -X POST "http://localhost:8000/api/scanner/stop"
```

### Check Scanner Status
```bash
curl "http://localhost:8000/api/scanner/status"
```

## Socket Events

| Event | Description |
|-------|-------------|
| `scan_started` | Emitted when scan begins |
| `scan_progress` | Emitted every 10 files with progress info |
| `scan_complete` | Emitted when scan finishes normally |
| `scan_stopped` | Emitted when scan is stopped via API |
| `scan_stop_requested` | Emitted when stop endpoint is called |

## Implementation Notes

1. **Stop Flag is Cooperative:** The scan loop checks the flag at each file iteration. A stop request will take effect after the current file finishes processing.

2. **Reset Before New Scan:** The stop flag is automatically reset when starting a new scan via `/api/scanner/rescan`.

3. **Singleton Pattern:** The `QdrantIncrementalUpdater` uses a singleton pattern, so the stop flag persists across calls and can be set from any endpoint.

4. **No Thread Safety Issues:** The stop flag is a simple boolean read/write which is atomic in Python due to the GIL.

## Files Modified

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/qdrant_updater.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/semantic_routes.py`

## Date

2026-01-21
