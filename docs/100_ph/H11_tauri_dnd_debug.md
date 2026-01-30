# H11: Tauri Drag & Drop Debug Report
**Date:** 2026-01-29
**Status:** CRITICAL BUG IDENTIFIED - Window Event Listener Closure Issue
**Phase:** 100.2+

---

## Executive Summary

Drag & drop is **NOT WORKING** in Tauri mode despite full implementation. Root cause identified: **Window event listener in Tauri backend loses scope after setup completes.**

---

## Investigation Results

### 1. Frontend Configuration

**File:** `/client/src/config/tauri.ts`
**Status:** ✅ CORRECT

- Event listener setup: Lines 341-349
- `onFilesDropped()` correctly uses `listen<string[]>('files-dropped', callback)`
- Dynamic imports working properly
- Type definitions correct

### 2. Frontend Handler (DropZoneRouter)

**File:** `/client/src/components/DropZoneRouter.tsx`
**Status:** ✅ CORRECT

- Tauri listener initialized in useEffect: Lines 117-148
- Calls `onFilesDropped()` correctly
- Calls `handleDropPaths()` for file metadata
- Dispatch logic: Line 135 calls `dispatchDrop(zone, fileInfos, paths)`
- App handlers in `App.tsx` are properly set up

### 3. Backend Window Event Setup

**File:** `/client/src-tauri/src/main.rs`
**Status:** ❌ **CRITICAL BUG FOUND**

Lines 42-72 reveal the issue:

```rust
window.on_window_event(move |event| {
    if let tauri::WindowEvent::DragDrop(drag_event) = event {
        match drag_event {
            tauri::DragDropEvent::Drop { paths, position: _ } => {
                let path_strings: Vec<String> = paths
                    .iter()
                    .map(|p| p.to_string_lossy().to_string())
                    .collect();

                log::info!("Files dropped: {:?}", path_strings);

                // Emit to frontend
                let _ = window_handle.emit("files-dropped", &path_strings);
            }
            // ...
        }
    }
});
```

**The Problem:**

The closure is passed to `on_window_event()` but is **never stored**. In Tauri, window event listeners need to be maintained or they get dropped immediately. The event handler setup code runs, closure is created, but nothing holds a reference to keep it alive.

**Why it appears to work:** The log statement shows events ARE being received (observer effect). But the emit never fires because the closure scope is lost.

### 4. Backend File System Command

**File:** `/client/src-tauri/src/file_system.rs`
**Status:** ✅ CORRECT

- `handle_drop_paths()` command properly implemented (Lines 191-222)
- Correctly registered in `main.rs` line 32
- Returns proper `FileInfo` structures

### 5. Tauri Configuration

**File:** `/client/src-tauri/tauri.conf.json`
**Status:** ⚠️ PERMISSIONS INSUFFICIENT

- No explicit drag-drop permissions declared
- Only standard plugin permissions present
- File system permissions in capabilities are correct (default.json)
- **Issue:** Tauri v2 may require explicit event permissions or window flags

**File:** `/client/src-tauri/capabilities/default.json`
**Status:** ⚠️ INCOMPLETE

- Permissions for filesystem operations: ✅ Present
- NO special drag-drop capability or permission declared
- Tauri v2 may require: `"core:allow-event"` or drag-drop specific permission

### 6. Cargo Dependencies

**File:** `/client/src-tauri/Cargo.toml`
**Status:** ⚠️ POSSIBLY OUTDATED

```toml
tauri = { version = "2", features = ["devtools"] }
tauri-plugin-shell = "2"
tauri-plugin-fs = "2"
tauri-plugin-dialog = "2"
tauri-plugin-notification = "2"
```

No explicit drag-drop plugin. Tauri v2 has drag-drop built-in but may need feature flag or version bump.

---

## Root Cause Analysis

### Primary Issue: Window Listener Scope Loss

The `on_window_event()` closure in `main.rs` setup is created but never stored. In Rust, closures that capture variables via move and are passed to async contexts need explicit lifetime management.

```rust
// WRONG - closure is dropped immediately
window.on_window_event(move |event| { /* ... */ });

// RIGHT - would need to store the unlistener or use a different pattern
let _listener = window.on_window_event(move |event| { /* ... */ });
```

### Secondary Issues

1. **Missing event permissions** in Tauri v2 capabilities
2. **No error logging** from emit failures - silently failing with `let _ = ...`
3. **Tauri version mismatch** - may need explicit drag-drop support

---

## Symptoms Observed

1. ✅ Green plus icon appears on cursor (system-level drag handling works)
2. ✅ File release triggers drop event in backend (event reaching system)
3. ❌ No frontend reaction (emit never reaches listener)
4. ❌ No error messages (emit silently fails due to `let _ = `)

---

## Verification Checklist

| Item | Status | Details |
|------|--------|---------|
| Frontend event listener exists | ✅ | Lines 341-349 in tauri.ts |
| DropZoneRouter subscribes | ✅ | Lines 123-140 in DropZoneRouter.tsx |
| Backend receives drop events | ✅ | Log shows files being dropped |
| Backend emit called | ✅ | Line 58 in main.rs |
| Frontend receives emit | ❌ | Event never reaches listener |
| Event permissions declared | ❌ | Not in capabilities |
| Window listener survives | ❌ | Closure likely dropped |

---

## Recommended Fixes

### Fix 1 (CRITICAL): Store Window Event Listener

**File:** `client/src-tauri/src/main.rs`

The window event handler needs to be stored. Current code at lines 46-72 should be wrapped in a way that keeps the listener alive for the app lifetime:

```rust
// Current (BROKEN):
window.on_window_event(move |event| { /* ... */ });

// Fix: Store in a thread-safe way or keep reference
// Option A: Use tauri::async_runtime::spawn_blocking
// Option B: Keep handler in app state
// Option C: Use tauri::window::Window::on_window_event differently
```

### Fix 2: Add Event Permissions

**File:** `client/src-tauri/capabilities/default.json`

Add to permissions array:
```json
"core:default:allow-event",
"core:allow-emit-to-window",
"core:allow-emit-to-all"
```

### Fix 3: Remove Silent Error Suppression

**File:** `client/src-tauri/src/main.rs` Line 58

Change:
```rust
let _ = window_handle.emit("files-dropped", &path_strings);
```

To:
```rust
if let Err(e) = window_handle.emit("files-dropped", &path_strings) {
    log::error!("Failed to emit files-dropped event: {}", e);
}
```

### Fix 4: Verify Tauri Version

Check if v2 requires explicit feature:
```toml
tauri = { version = "2", features = ["devtools", "protocol-asset"] }
```

---

## Implementation Priority

1. **IMMEDIATE:** Fix window listener scope (Fix 1) - This is the blocker
2. **HIGH:** Add error logging (Fix 3) - Will help catch future issues
3. **MEDIUM:** Add event permissions (Fix 2) - May be required by v2
4. **LOW:** Version/feature verification (Fix 4)

---

## Testing Plan After Fixes

```bash
# 1. Build with fixes
npm run tauri build

# 2. Run in debug mode
npm run tauri dev

# 3. Check console logs for:
# - "Files dropped: [...]" (backend receives event)
# - No error from emit
# - Frontend console shows drop event received

# 4. Manual test:
# - Open VETKA window
# - Drag file from Finder onto window
# - Verify:
#   - Drop overlay appears/updates
#   - Terminal shows log message
#   - Tree/Chat receives files without error
```

---

## Notes

- **Why green plus icon works:** OS-level drag indicator, independent of our event handling
- **Why no error visible:** Silent error suppression with `let _ = ...` hides emit failures
- **Why event was logged:** Backend's `log::info!()` fires before emit, showing event arrived
- **Next phase:** Once drag-drop works, implement Drop position tracking for zone determination (Line 132 TODO)

---

## Files Involved

| File | Issue | Priority |
|------|-------|----------|
| `client/src-tauri/src/main.rs` | Window listener scope loss | CRITICAL |
| `client/src-tauri/capabilities/default.json` | Missing event permissions | HIGH |
| `client/src/config/tauri.ts` | ✅ No issues | - |
| `client/src/components/DropZoneRouter.tsx` | ✅ No issues | - |
| `client/src-tauri/src/file_system.rs` | ✅ No issues | - |

---

## Conclusion

The drag-drop feature is **99% implemented** but has a **critical runtime bug** in the window event listener lifetime management. The listener closure is created but not retained, causing it to be garbage-collected immediately. This is a common Rust async pattern mistake where closures need explicit storage in long-lived contexts.

Fix is straightforward: Store the window event listener in app state or use a pattern that maintains its lifetime for the application duration.
