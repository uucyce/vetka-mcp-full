# CODEX BRIEFING -- Day 1

| Field          | Value                                         |
|----------------|-----------------------------------------------|
| Phase          | 145                                           |
| Date           | 2026-02-14                                    |
| Agent          | CODEX (Claude Code worktree)                  |
| Branch         | Use git worktree `cranky-borg` or create new  |
| Time budget    | 9.5 hours total                               |
| Priority order | BUG-1 > BUG-8 > BUG-2 > BUG-3 > BUG-9       |

---

## Priority Order Summary

| Bug   | Priority | Est. Time | Description                        |
|-------|----------|-----------|------------------------------------|
| BUG-1 | CRITICAL | 3.0 hrs   | Scanner duplicate indexing in Qdrant |
| BUG-8 | HIGH     | 2.0 hrs   | Web Shell navigation race condition  |
| BUG-2 | HIGH     | 2.0 hrs   | Heartbeat hardcoded GROUP_ID         |
| BUG-3 | HIGH     | 1.0 hr    | FC Loop silent degradation           |
| BUG-9 | MEDIUM   | 1.5 hrs   | Web Shell save path empty fallback   |

---

## BUG-1: Scanner Duplicates (CRITICAL)

### Impact

Users scanning directories see the same file indexed 2x or more in Qdrant.
This inflates Qdrant storage, corrupts semantic search rankings (duplicate
results), and makes the 3D tree show ghost nodes. Every project scan compounds
the problem -- large projects can accumulate thousands of duplicate points.

### Root Cause Analysis

Three independent sources of duplication interact:

**1. No path normalization before point ID generation.**

File: `src/scanners/qdrant_updater.py`, line 223-235.

```python
def _get_point_id(self, file_path: str) -> int:
    return uuid.uuid5(uuid.NAMESPACE_DNS, file_path).int & 0x7FFFFFFFFFFFFFFF
```

The `file_path` argument is used raw. If the same physical file is referenced as
`~/Documents/project/foo.py` vs `/Users/danila/Documents/project/foo.py`, these
produce different UUID5 hashes and therefore different point IDs. Two Qdrant
points are created for the same file.

The inconsistency is introduced by callers:
- `watcher_routes.py` line 98 calls `os.path.expanduser(path)` on the directory
  but individual file paths inside `scan_directory()` inherit whatever form
  `os.walk()` returns.
- `embedding_pipeline.py` line 301 uses `file_data.get('path', '')` as-is from
  the scanner, which may or may not be normalized.
- `watcher_routes.py` line 637 (`index-file` endpoint) calls
  `os.path.expanduser(file_path)` but never `os.path.abspath()`.

**2. Double scanning on `/api/watcher/add`.**

File: `src/api/routes/watcher_routes.py`, lines 147-156.

```python
already_watching = path in watcher.watched_dirs
success = watcher.add_directory(path, recursive=recursive)
should_scan = success or already_watching
```

When a directory is already watched, `already_watching=True` and
`should_scan=True`, so the full `scan_directory()` runs again. Meanwhile the
watcher's file observer is also running and will emit `created`/`modified`
events for the same files -- both paths call `update_file()` concurrently.

**3. No "already indexed" guard before Qdrant upsert.**

File: `src/scanners/qdrant_updater.py`, lines 406-427.

The `update_file()` method does check `_file_changed()` (line 343), which
queries Qdrant by point ID. But because point IDs differ for un-normalized
paths (issue 1), the lookup misses the existing entry and proceeds to upsert a
new point.

File: `src/scanners/embedding_pipeline.py`, lines 474-499.

`_save_to_qdrant()` generates its own `point_id` from `doc_id`, which is an
MD5 of `path:content_hash`. If the path string is different (normalization
issue), this too produces a different point ID.

### Files to Modify

| File | Purpose |
|------|---------|
| `src/scanners/qdrant_updater.py` | Normalize paths in `_get_point_id()` and `update_file()` |
| `src/api/routes/watcher_routes.py` | Guard against redundant full scans |
| `src/scanners/embedding_pipeline.py` | Add indexed-paths cache, normalize in `_generate_id()` |

### Step-by-Step Fix Instructions

**Step 1: Normalize paths in `_get_point_id()` (qdrant_updater.py:223-235)**

Replace the current implementation:

```python
def _get_point_id(self, file_path: str) -> int:
    # MARKER_145.BUG1A: Normalize path before ID generation to prevent duplicates.
    # ~/project and /Users/x/project must produce the same point ID.
    normalized = os.path.abspath(os.path.expanduser(file_path))
    return uuid.uuid5(uuid.NAMESPACE_DNS, normalized).int & 0x7FFFFFFFFFFFFFFF
```

Add `import os` at the top of the file (it is not currently imported; only
`pathlib.Path` is used). Note: `os` is already available via stdlib.

**Step 2: Normalize in `update_file()` (qdrant_updater.py:320-336)**

At the top of `update_file()`, normalize the incoming path before any
operations:

```python
def update_file(self, file_path: Path) -> bool:
    # MARKER_145.BUG1B: Normalize early to ensure consistent hashing and lookups.
    file_path = Path(os.path.abspath(os.path.expanduser(str(file_path))))
    ...
```

This ensures that `_file_changed()`, `_get_point_id()`, and the metadata
`'path'` field all use the same canonical path.

**Step 3: Guard against redundant scans (watcher_routes.py:147-156)**

Change the scan logic so that re-adding an already-watched directory does NOT
trigger a full re-scan (the watcher observer is already handling incremental
updates):

```python
already_watching = path in watcher.watched_dirs
success = watcher.add_directory(path, recursive=recursive)
# MARKER_145.BUG1C: Only full-scan on first add. Rescan is redundant because
# the watcher observer is already emitting events for this directory.
should_scan = success and not already_watching
```

If the user explicitly wants a rescan, they can use `/api/watcher/remove` then
`/api/watcher/add`, or a separate `/api/watcher/rescan` endpoint could be added
later.

**Step 4: Add indexed_paths cache to EmbeddingPipeline (embedding_pipeline.py)**

Add a class-level `Set` to track paths already indexed within a single pipeline
run, preventing double-processing:

```python
class EmbeddingPipeline:
    ...
    def __init__(self, ...):
        ...
        # MARKER_145.BUG1D: In-memory set to skip already-indexed paths within a run.
        self._indexed_paths: set = set()
```

In `_process_single()` (line 297), add a guard at the top:

```python
def _process_single(self, file_data: Dict[str, Any]) -> EmbeddingResult:
    path = file_data.get('path', '')
    # MARKER_145.BUG1D: Normalize and skip if already indexed in this run.
    normalized_path = os.path.abspath(os.path.expanduser(path)) if path else ''
    if normalized_path in self._indexed_paths:
        return EmbeddingResult(
            doc_id=self._generate_id(file_data),
            path=path, name=file_data.get('name', ''),
            embedding=[], metadata={},
            success=True, error=None
        )
    ...
    # After successful save:
    if success and normalized_path:
        self._indexed_paths.add(normalized_path)
```

**Step 5: Normalize path in `_generate_id()` (embedding_pipeline.py:507-511)**

```python
def _generate_id(self, file_data: Dict[str, Any]) -> str:
    path = file_data.get('path', '')
    # MARKER_145.BUG1E: Normalize path for consistent ID generation.
    normalized = os.path.abspath(os.path.expanduser(path)) if path else ''
    content_hash = file_data.get('content_hash', '')
    return hashlib.md5(f"{normalized}:{content_hash}".encode()).hexdigest()
```

Add `import os` at the top of embedding_pipeline.py.

### Testing Criteria

1. **Unit test -- path normalization:** Call `_get_point_id("~/project/foo.py")`
   and `_get_point_id("/Users/danilagulin/project/foo.py")` -- both must return
   the same integer.
2. **Unit test -- no double upsert:** Mock Qdrant client, call `update_file()`
   twice with the same file (different path forms). Assert `upsert` called
   exactly once.
3. **Integration test -- watcher add idempotent:** POST `/api/watcher/add`
   twice for the same directory. Assert second call does NOT trigger
   `scan_directory()`.
4. **Integration test -- Qdrant count:** After scanning a directory with 10
   files, assert exactly 10 points in Qdrant (not 20).
5. **Regression test:** Verify `soft_delete()` still works with normalized
   paths.

---

## BUG-8: Web Shell Navigation Race (HIGH)

### Impact

When a user clicks multiple search results quickly in VETKA, the Web Shell
opens and fires multiple `loadPreview()` calls concurrently. Because async
fetches can resolve out of order, an older (slower) page load can overwrite a
newer (faster) one. The user sees stale content that does not match the URL bar.

### Root Cause Analysis

**Frontend: `WebShellStandalone.tsx`**

File: `client/src/WebShellStandalone.tsx`, lines 194-235.

The current `loadPreview()` already has a monotonic `loadRequestRef` counter
(line 195) and an `AbortController` (lines 196-201). However, there is a
remaining race window:

1. The `AbortController` is created per call but `loadAbortRef` is shared.
   If `loadPreview(A)` starts, then `loadPreview(B)` starts and aborts A's
   controller, then A's `finally` block runs and sets
   `loadAbortRef.current = null` (line 232), potentially nullifying B's
   controller reference.

2. The Tauri event listener at lines 130-166 calls `loadPreview(nextUrl)` via
   `void loadPreview(nextUrl)` (fire-and-forget). Multiple rapid events from
   Tauri can pile up without waiting for the previous load to abort cleanly.

**Backend: `commands.rs`**

File: `client/src-tauri/src/commands.rs`, lines 96-162.

The `open_research_browser` command either creates a new window or reuses an
existing one. When reusing (line 134), it calls `existing.eval(&nav_js)` AND
`existing.emit("vetka:web-shell:navigate", payload)`. The `eval` triggers a
full page reload via `window.location.replace()`, which destroys any in-flight
React state. Meanwhile the `emit` arrives as a Tauri event to the React
listener (line 136 in TSX). These two signals can race against each other.

### Files to Modify

| File | Purpose |
|------|---------|
| `client/src/WebShellStandalone.tsx` | Fix loadPreview race with proper abort sequencing |
| `client/src-tauri/src/commands.rs` | Remove redundant navigation signal when reusing window |

### Step-by-Step Fix Instructions

**Step 1: Fix abort lifecycle in `loadPreview` (WebShellStandalone.tsx:194-235)**

The `finally` block must only clear `loadAbortRef` if it is still the current
controller (not a newer one):

```typescript
const loadPreview = async (url: string) => {
  const reqId = ++loadRequestRef.current;
  // MARKER_145.BUG8A: Abort any in-flight request before creating new controller.
  if (loadAbortRef.current) {
    loadAbortRef.current.abort();
  }
  const controller = new AbortController();
  loadAbortRef.current = controller;
  setIsLoading(true);
  try {
    const resp = await fetch('/api/search/web-preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, timeout_s: 14 }),
      signal: controller.signal,
    });
    const data = await resp.json();
    if (!resp.ok || !data?.success || !data?.html) {
      throw new Error(data?.error || `HTTP ${resp.status}`);
    }
    // MARKER_145.BUG8B: Stale response guard -- only apply if still the latest request.
    if (reqId !== loadRequestRef.current) return;

    const resolvedUrl = String(data.url || url);
    setPreviewHtml(String(data.html || ''));
    setCurrentUrl(resolvedUrl);
    setAddressValue(resolvedUrl);
    findRangesRef.current = [];
    findIndexRef.current = -1;
    findNeedRebuildRef.current = true;
    setStatus(`Loaded: ${data.title || resolvedUrl}`);
  } catch (e) {
    if ((e as Error)?.name === 'AbortError') return;
    if (reqId !== loadRequestRef.current) return;
    setPreviewHtml('');
    setStatus(`Load failed: ${(e as Error).message}`);
  } finally {
    // MARKER_145.BUG8C: Only clear loading state if this is still the active request.
    // Prevents a stale finally block from clobbering a newer request's controller.
    if (reqId === loadRequestRef.current) {
      setIsLoading(false);
      if (loadAbortRef.current === controller) {
        loadAbortRef.current = null;
      }
    }
  }
};
```

The key change is in `finally`: instead of unconditionally setting
`loadAbortRef.current = null`, it checks `loadAbortRef.current === controller`
first.

**Step 2: Remove redundant navigation in `open_research_browser` (commands.rs:134-148)**

When an existing window is found, the current code does BOTH `eval(nav_js)`
(full page reload) AND `emit("vetka:web-shell:navigate", payload)` (React
event). This creates a race: the page reload destroys React state, and the
event handler may fire before or after the reload completes.

Fix: Use only the Tauri event, not the full-page `eval`:

```rust
if let Some(existing) = app.get_webview_window(&label) {
    // MARKER_145.BUG8D: Only emit navigate event, do NOT eval window.location.replace().
    // The React listener handles URL changes internally via loadPreview().
    // eval() causes a full page reload that destroys React state and races with the event.
    let _ = existing.set_title(&window_title);
    let payload = WebShellNavigatePayload {
        url: parsed.as_str().to_string(),
        title: window_title,
        save_path: save_path.clone(),
        save_paths: save_paths.clone(),
    };
    let _ = existing.emit("vetka:web-shell:navigate", payload);
    existing.show().map_err(|e| e.to_string())?;
    existing.set_focus().map_err(|e| e.to_string())?;
    return Ok(true);
}
```

This removes the `eval(&nav_js)` call entirely. The React event listener
(TSX line 136) already handles navigation via `loadPreview(nextUrl)`.

### Testing Criteria

1. **Manual test -- rapid clicks:** Open VETKA, search for something, click
   3 results in quick succession. The Web Shell must show the LAST clicked
   result, not an earlier one.
2. **Unit test -- abort sequencing:** Call `loadPreview('a')`, immediately call
   `loadPreview('b')`. Assert only the second fetch completes, the first is
   aborted.
3. **Unit test -- stale finally guard:** Verify that `loadAbortRef.current` is
   NOT set to null by a stale finally block when a newer request is active.
4. **Manual test -- Tauri reuse:** Open a web result, then open another. The
   existing window should navigate to the new URL without a full page reload
   flash.

---

## BUG-2: Heartbeat Hardcoded GROUP_ID (HIGH)

### Impact

The heartbeat engine only monitors one hardcoded group chat
(`5e2198c2-8b1a-45df-807f-5c73c5496aa8`). If a user creates a new group chat
and sends `@dragon build X` there, the heartbeat ignores it. The `monitor_all`
flag (line 401) exists as a workaround but it polls ALL groups and ALL solo
chats, which is wasteful and can dispatch tasks from chats that should not be
monitored.

### Root Cause Analysis

File: `src/orchestration/mycelium_heartbeat.py`, line 37.

```python
HEARTBEAT_GROUP_ID = "5e2198c2-8b1a-45df-807f-5c73c5496aa8"
```

This constant is used as the default for `heartbeat_tick()` (line 384) and for
`_emit_heartbeat_status()` (line 276). The `heartbeat_config.json` at
`data/heartbeat_config.json` stores `enabled`, `interval`, and `monitor_all`
but has no concept of per-group configuration.

### Files to Modify

| File | Purpose |
|------|---------|
| `src/orchestration/mycelium_heartbeat.py` | Load group config from YAML, iterate groups |
| `data/config/heartbeat_config.yaml` | New config file (create) |
| `data/heartbeat_config.json` | Keep for backward compat, add `groups` field |

### Step-by-Step Fix Instructions

**Step 1: Create YAML config file.**

Create `data/config/heartbeat_config.yaml`:

```yaml
# MARKER_145.BUG2A: Heartbeat group configuration.
# Each group has id, name, enabled flag, and optional interval override.
groups:
  - id: "5e2198c2-8b1a-45df-807f-5c73c5496aa8"
    name: "MCP Dev"
    enabled: true
    interval_seconds: 30

  # Add more groups here:
  # - id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  #   name: "Frontend Team"
  #   enabled: true
  #   interval_seconds: 60

defaults:
  interval_seconds: 30
  max_concurrent_dispatches: 2
```

**Step 2: Add config loader to `mycelium_heartbeat.py`.**

Add a function near the top (after the imports, around line 42):

```python
# MARKER_145.BUG2B: Load heartbeat group config from YAML (preferred) or JSON fallback.
_CONFIG_YAML = Path(__file__).parent.parent.parent / "data" / "config" / "heartbeat_config.yaml"
_CONFIG_JSON = Path(__file__).parent.parent.parent / "data" / "heartbeat_config.json"

def _load_heartbeat_groups() -> List[Dict[str, Any]]:
    """Load monitored group configurations.

    Priority: YAML config > JSON config > hardcoded fallback.
    Returns list of group dicts with keys: id, name, enabled, interval_seconds.
    """
    # Try YAML first
    if _CONFIG_YAML.exists():
        try:
            import yaml
            data = yaml.safe_load(_CONFIG_YAML.read_text())
            groups = data.get("groups", [])
            if groups:
                logger.info(f"[Heartbeat] Loaded {len(groups)} groups from YAML config")
                return groups
        except Exception as e:
            logger.warning(f"[Heartbeat] Failed to load YAML config: {e}")

    # Fallback to JSON
    if _CONFIG_JSON.exists():
        try:
            data = json.loads(_CONFIG_JSON.read_text())
            groups = data.get("groups", [])
            if groups:
                logger.info(f"[Heartbeat] Loaded {len(groups)} groups from JSON config")
                return groups
        except Exception:
            pass

    # Hardcoded fallback (backward compat)
    logger.info("[Heartbeat] Using hardcoded default group")
    return [{"id": HEARTBEAT_GROUP_ID, "name": "MCP Dev (default)", "enabled": True, "interval_seconds": 30}]
```

**Step 3: Update `heartbeat_tick()` to iterate configured groups.**

Replace the function signature default and the single-group fetch block
(lines 383-464). The `group_id` parameter becomes optional and is only used
as an explicit override:

```python
async def heartbeat_tick(
    group_id: Optional[str] = None,
    dry_run: bool = False,
    monitor_all: bool = False,
) -> Dict[str, Any]:
    # MARKER_145.BUG2C: Use configured groups instead of hardcoded default.
    if group_id:
        # Explicit override -- monitor only this group (legacy behavior).
        target_groups = [{"id": group_id, "name": "override", "enabled": True}]
    elif monitor_all:
        # Dynamic discovery (existing behavior, unchanged).
        ...
    else:
        # Default: use configured groups.
        target_groups = [g for g in _load_heartbeat_groups() if g.get("enabled", True)]
        if not target_groups:
            target_groups = [{"id": HEARTBEAT_GROUP_ID, "name": "fallback", "enabled": True}]

    all_messages = []
    for group_cfg in target_groups:
        gid = group_cfg["id"]
        cursor = chat_cursors.get(f"group:{gid}")
        msgs = _fetch_new_messages(gid, since_id=cursor)
        if msgs:
            for m in msgs:
                m["_source_chat_id"] = gid
                m["_source_chat_type"] = "group"
            all_messages.extend(msgs)
            chat_cursors[f"group:{gid}"] = msgs[-1].get("id", cursor)

    messages = all_messages
    ...
```

**Step 4: Update `_emit_heartbeat_status()` to accept group_id dynamically.**

The function already takes `group_id` as a parameter (line 276), so no change
is needed to its signature. However, callers in `heartbeat_tick()` that
currently use the module-level `group_id` variable must pass the correct
per-group ID when iterating.

### Testing Criteria

1. **Unit test -- config loading:** Create a temp YAML with 2 groups (one
   enabled, one disabled). Assert `_load_heartbeat_groups()` returns only the
   enabled one.
2. **Unit test -- fallback:** Delete both YAML and JSON configs. Assert the
   hardcoded default is returned.
3. **Integration test -- multi-group tick:** Mock `_fetch_new_messages` for 2
   group IDs. Run `heartbeat_tick()`. Assert messages from both groups are
   parsed.
4. **Regression test:** Call `heartbeat_tick(group_id="specific-id")`.
   Assert only that group is monitored (override behavior preserved).

---

## BUG-3: FC Loop Silent Degradation (HIGH)

### Impact

If `src/tools/fc_loop.py` fails to import (syntax error, missing dependency,
circular import), the coder silently falls back to one-shot mode. One-shot mode
produces significantly worse code (no file reading, no search, generic output).
There is no log entry at ERROR level, no chat notification to the user, and no
health check visibility. The operator has no idea the pipeline is running
degraded.

### Root Cause Analysis

File: `src/orchestration/agent_pipeline.py`, lines 40-45.

```python
try:
    from src.tools.fc_loop import execute_fc_loop, get_coder_tool_schemas, MAX_FC_TURNS_CODER
    FC_LOOP_AVAILABLE = True
except ImportError:
    FC_LOOP_AVAILABLE = False
    logger.debug("[Pipeline] FC loop not available, coder will use one-shot mode")
```

The log level is `debug` (line 45), which is not visible in normal operation.
The variable `FC_LOOP_AVAILABLE` is checked at line 3068 to decide whether to
use FC. If `False`, the coder silently gets no tools.

### Files to Modify

| File | Purpose |
|------|---------|
| `src/orchestration/agent_pipeline.py` | Raise import severity, emit warning |

### Step-by-Step Fix Instructions

**Step 1: Escalate log level and add explicit error details (agent_pipeline.py:40-45).**

```python
# MARKER_145.BUG3A: FC loop is a required dependency. If unavailable, log ERROR
# and emit a visible warning so operators know the pipeline is degraded.
try:
    from src.tools.fc_loop import execute_fc_loop, get_coder_tool_schemas, MAX_FC_TURNS_CODER
    FC_LOOP_AVAILABLE = True
except ImportError as _fc_import_err:
    FC_LOOP_AVAILABLE = False
    logger.error(
        f"[Pipeline] CRITICAL: FC loop import FAILED -- coder will use degraded one-shot mode. "
        f"Error: {_fc_import_err}. Fix: ensure src/tools/fc_loop.py is importable."
    )
```

**Step 2: Emit warning to chat when pipeline starts with FC unavailable.**

In the `AgentPipeline.execute()` method, after the initial progress emission,
add a degradation warning if FC is unavailable. Find the `execute()` method
(search for `async def execute`) and add after the first `_emit_progress` call:

```python
# MARKER_145.BUG3B: Warn operators in chat when FC loop is unavailable.
if not FC_LOOP_AVAILABLE:
    await self._emit_progress(
        "@system",
        "WARNING: Coder Function Calling is UNAVAILABLE. "
        "Code quality will be degraded (no file reading, no search). "
        "Check logs for fc_loop import error."
    )
```

**Step 3: Add FC status to pipeline health endpoint.**

If a health check endpoint exists (e.g., `/api/health` or
`/api/debug/health`), add `fc_loop_available: bool` to its response. Search
for the health route and add:

```python
"fc_loop_available": FC_LOOP_AVAILABLE,
```

If no convenient health endpoint exists, add the flag to the pipeline stats
returned by `pipeline.get_stats()` or to the heartbeat status.

### Testing Criteria

1. **Unit test -- import failure logging:** Temporarily make `fc_loop.py`
   un-importable (e.g., rename it). Start the pipeline module. Assert that an
   ERROR-level log message is emitted containing "FC loop import FAILED".
2. **Unit test -- chat warning:** With `FC_LOOP_AVAILABLE = False`, call
   `pipeline.execute()`. Assert that `_emit_progress` is called with a message
   containing "WARNING" and "Function Calling".
3. **Regression test:** With `FC_LOOP_AVAILABLE = True`, confirm no warning
   message is emitted.

---

## BUG-9: Web Shell Save Path Empty (MEDIUM)

### Impact

When a user opens the Web Shell and clicks "Save to VETKA", the save path
dropdown can be completely empty if no viewport context is available (no
nodes loaded, camera not initialized, or running in browser mode without
Tauri). The user sees an empty text field with no suggestions for where to
save, and if they submit with an empty path, the backend may save to an
arbitrary or broken location.

### Root Cause Analysis

**Frontend dependency on viewport state.**

File: `client/src/config/tauri.ts`, lines 214-294 (inside `openLiveWebWindow`).

The save path suggestions are derived from:
1. `state.selectedId` -- currently selected node (can be null)
2. `state.pinnedFileIds` -- pinned files (can be empty array)
3. `state.cameraRef` -- camera reference (null until 3D scene loads)
4. Fallback: `state.nodes` sorted by depth (empty if no scan done)

If ALL of these are empty (fresh session, no directory scanned, no 3D scene),
`savePaths` remains `[]` and `inferredSavePath` remains `""`. The Web Shell
opens with no save path suggestions at all.

**No backend fallback resolver.**

The save flow is purely client-side. There is no backend endpoint that can
recommend save paths based on server-side knowledge (scanned directories,
recent artifacts, project root). The frontend has no fallback when its own
state is empty.

### Files to Modify

| File | Purpose |
|------|---------|
| `src/api/routes/artifact_routes.py` (or new file) | Create `POST /api/tree/recommend-save-paths` |
| `client/src/WebShellStandalone.tsx` | Call backend fallback when suggestions are empty |
| `client/src/config/tauri.ts` | Call backend fallback in `openLiveWebWindow()` |

### Step-by-Step Fix Instructions

**Step 1: Create backend endpoint `POST /api/tree/recommend-save-paths`.**

Add to `src/api/routes/artifact_routes.py` (or a new `tree_utils_routes.py`):

```python
# MARKER_145.BUG9A: Backend fallback for save path recommendations.
# Returns ranked list of directory paths suitable for saving web content.
@router.post("/recommend-save-paths")
async def recommend_save_paths(request: Request):
    """Return recommended save paths based on server-side state.

    Sources (in priority order):
    1. Currently watched directories (from file watcher)
    2. Recent artifact save locations
    3. Project root from scan history
    4. Hardcoded fallback: ~/Documents/VETKA_Saved/
    """
    paths = []

    # Source 1: Watched directories
    try:
        from src.scanners.file_watcher import get_watcher
        watcher = get_watcher()
        for wd in watcher.watched_dirs:
            paths.append(wd)
    except Exception:
        pass

    # Source 2: Recent artifact locations
    try:
        artifacts_dir = Path(__file__).parent.parent.parent.parent / "data" / "artifacts"
        if artifacts_dir.exists():
            for sub in sorted(artifacts_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if sub.is_dir():
                    paths.append(str(sub))
                    if len(paths) >= 12:
                        break
    except Exception:
        pass

    # Source 3: Hardcoded fallback
    fallback = os.path.expanduser("~/Documents/VETKA_Saved")
    if fallback not in paths:
        paths.append(fallback)

    # Deduplicate and limit
    seen = set()
    unique = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    unique = unique[:24]

    return {"paths": unique, "default": unique[0] if unique else fallback}
```

**Step 2: Call backend fallback in WebShellStandalone.tsx.**

In `WebShellStandalone.tsx`, add a `useEffect` that calls the backend endpoint
when `savePathSuggestions` is empty:

```typescript
// MARKER_145.BUG9B: Fetch save path suggestions from backend when client state is empty.
useEffect(() => {
  if (savePathSuggestions.length > 0) return;
  let cancelled = false;
  void (async () => {
    try {
      const resp = await fetch('/api/tree/recommend-save-paths', { method: 'POST' });
      const data = await resp.json();
      if (cancelled) return;
      const backendPaths: string[] = data?.paths || [];
      if (backendPaths.length > 0) {
        setSavePathSuggestions(backendPaths);
        if (!savePath.trim()) {
          setSavePath(data?.default || backendPaths[0]);
        }
      }
    } catch {
      // non-fatal
    }
  })();
  return () => { cancelled = true; };
}, [savePathSuggestions.length]);
```

Place this after the existing `useEffect` blocks (after line 179).

**Step 3: Add backend fallback in `openLiveWebWindow()` (tauri.ts:214-294).**

At the end of the `try` block that gathers viewport paths (around line 291),
add a backend call if `savePaths` is still empty:

```typescript
// MARKER_145.BUG9C: Backend fallback for save paths when viewport state is empty.
if (savePaths.length === 0) {
  try {
    const resp = await fetch('/api/tree/recommend-save-paths', { method: 'POST' });
    const data = await resp.json();
    const backendPaths: string[] = (data?.paths || []).map((p: string) => String(p).trim()).filter(Boolean);
    if (backendPaths.length > 0) {
      savePaths = backendPaths.slice(0, 24);
      inferredSavePath = inferredSavePath || data?.default || backendPaths[0];
    }
  } catch {
    // non-fatal
  }
}
```

Insert this code just before the `savePaths = savePaths.slice(0, 24);` line
(approximately line 291).

### Testing Criteria

1. **API test:** Call `POST /api/tree/recommend-save-paths` with no body.
   Assert response has `paths` array (non-empty if any directory was ever
   scanned) and `default` string.
2. **Frontend test -- empty state:** Load WebShellStandalone with no viewport
   state (fresh session). Assert that `savePathSuggestions` gets populated from
   the backend within 2 seconds.
3. **Frontend test -- non-empty state:** Load with viewport paths already
   available. Assert no backend call is made (the `useEffect` guard checks
   `savePathSuggestions.length > 0`).
4. **Integration test -- save flow:** In the save modal, verify the path field
   has at least one suggestion and is not blank.

---

## General Notes for Codex

1. **Commit convention:** Use `vetka_git_commit` MCP tool. Message format:
   `MARKER_145.BUG{N}: <description>`. Example:
   `MARKER_145.BUG1: normalize paths in qdrant_updater to prevent scanner duplicates`.

2. **Tests location:** Place all new tests in `tests/test_phase145_bug_fixes.py`
   (one file, multiple test classes -- one per bug).

3. **Do not modify:** `src/orchestration/agent_pipeline.py` beyond the FC loop
   import block (lines 40-45) and the execute() method warning. Other agents
   may be modifying this file concurrently.

4. **Run tests before commit:** `python -m pytest tests/test_phase145_bug_fixes.py -v`

5. **If blocked:** Update the task on the board with status `hold` and describe
   the blocker. Do not wait -- move to the next bug.
