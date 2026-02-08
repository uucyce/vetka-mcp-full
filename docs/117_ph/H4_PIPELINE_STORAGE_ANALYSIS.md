# HAIKU SCOUT H4: Pipeline Task Storage — Alternatives Analysis

**Status**: Research Complete
**Date**: 2026-02-07
**Phase**: 117 (MCP Sandbox Resilience)
**Priority**: High (Pipeline failures due to read-only file access in MCP sandbox)

---

## Executive Summary

The `data/pipeline_tasks.json` file becomes read-only when called via MCP sandbox, causing pipeline task updates to fail silently. This analysis identifies **4 viable alternatives** to mitigate this issue:

1. **Qdrant Vector Store** (Recommended) - Already used for chat history
2. **Temporary Directory (`/tmp/`)** - Cross-platform fallback
3. **In-Memory Dict** (Session-only) - For non-persistent workflows
4. **Hybrid Pattern** - Combine multiple strategies with intelligent fallback

---

## Section 1: Current Implementation

### H4_UPDATE_TASK_METHOD

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/agent_pipeline.py` (lines 531-535)

```python
def _update_task(self, task: PipelineTask):
    """Update single task in storage"""
    tasks = self._load_tasks()
    tasks[task.task_id] = asdict(task)
    self._save_tasks(tasks)

def _save_tasks(self, tasks: Dict[str, Any]):
    """Save tasks to JSON storage"""
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(json.dumps(tasks, indent=2, default=str))
```

**Problem**:
- Direct file write via `Path.write_text()` with no error handling
- When MCP sandbox denies write access, the exception is not caught
- Tasks are updated in memory but never persisted
- No fallback mechanism exists

---

### H4_PIPELINE_TASK_FIELDS

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/agent_pipeline.py` (lines 76-97)

```python
@dataclass
class PipelineTask:
    """Main task with fractal subtasks"""
    task_id: str                          # Unique identifier
    task: str                             # Task description
    phase_type: str                       # research, fix, build
    status: str = "pending"               # pending, planning, executing, done, failed
    subtasks: List[Subtask] = None        # List of subtasks
    timestamp: float = 0                  # Creation timestamp
    results: Optional[Dict] = None        # Final results dict
    visible_to_user: bool = True          # Show in chat UI
    stream_level: str = "summary"         # full | summary | silent
    highlight_artifacts: bool = True      # Highlight code blocks
```

**Supporting Subtask dataclass** (lines 62-73):

```python
@dataclass
class Subtask:
    """Subtask with optional research trigger"""
    description: str
    needs_research: bool = False
    question: Optional[str] = None
    context: Optional[Dict] = None
    result: Optional[str] = None
    status: str = "pending"               # pending, researching, executing, done, failed
    marker: Optional[str] = None
    visible: bool = True                  # Show progress in UI
    stream_result: bool = True            # Stream completion to chat
```

**Total fields**: 19 (across both dataclasses)
**Serializable**: Yes (all fields are JSON-compatible)
**Storage footprint**: ~186KB current file, grows ~5-10KB per major pipeline

---

## Section 2: Alternative 1 - Qdrant Vector Store

### H4_QDRANT_COLLECTIONS

**Existing Qdrant collections in VETKA**:

From `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_client.py` (lines 85-91):

```python
COLLECTION_NAMES = {
    'tree': 'VetkaTree',              # Hierarchical node storage
    'leaf': 'VetkaLeaf',              # Detailed node information
    'changelog': 'VetkaChangeLog',    # Audit trail entries
    'trash': 'VetkaTrash',            # Deleted items archive
    'chat': 'VetkaGroupChat'          # Chat history (Phase 103.7)
}
```

### Implementation Pattern (Already Proven)

The codebase already uses Qdrant for chat message persistence (lines 732-809):

```python
def upsert_chat_message(
    group_id: str,
    message_id: str,
    sender_id: str,
    content: str,
    role: str = "user",
    agent: str = None,
    model: str = None,
    metadata: Dict = None
) -> bool:
    """Upsert chat message to VetkaGroupChat collection."""
    client = get_qdrant_client()
    # ... embedding generation ...
    point = PointStruct(id=point_id, vector=embedding, payload=payload)
    client.client.upsert(
        collection_name=client.COLLECTION_NAMES['chat'],
        points=points
    )
```

### Advantages

✅ **Already tested** - Used for chat persistence in Phase 103.7
✅ **Non-file-based** - Works in MCP sandbox (no file permissions issues)
✅ **Semantic searchable** - Can search tasks by description
✅ **Batch operations** - Use `QdrantBatchManager` for efficiency
✅ **Persistent** - Survives across sessions
✅ **Audit trail** - Integrate with VetkaChangeLog

### Disadvantages

❌ Requires Qdrant server (but already running for chat)
❌ Slightly more complex retrieval logic
❌ Embedding cost for each task (minor for task descriptions)

### Implementation Sketch

```python
# Add to COLLECTION_NAMES
'tasks': 'VetkaPipelineTasks'

def _upsert_task_to_qdrant(self, task: PipelineTask):
    """Store pipeline task in Qdrant"""
    from src.memory.qdrant_client import get_qdrant_client
    from src.utils.embedding_service import get_embedding
    from qdrant_client.models import PointStruct

    client = get_qdrant_client()
    if not client:
        return False

    # Embed the task description for semantic search
    embedding = get_embedding(task.task[:500])
    point_id = int(hashlib.md5(task.task_id.encode()).hexdigest()[:16], 16)

    payload = {
        'task_id': task.task_id,
        'task': task.task,
        'phase_type': task.phase_type,
        'status': task.status,
        'timestamp': task.timestamp,
        'results': task.results or {},
        'subtasks_count': len(task.subtasks) if task.subtasks else 0,
        'visible_to_user': task.visible_to_user,
    }

    client.client.upsert(
        collection_name='VetkaPipelineTasks',
        points=[PointStruct(id=point_id, vector=embedding, payload=payload)]
    )
    return True
```

---

## Section 3: Alternative 2 - Temporary Directory Fallback

### H4_TMPDIR_USAGE

**Current TMPDIR usage in codebase**:

```bash
File: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_client.py:652
    with open('/tmp/vetka_changelog.jsonl', 'a') as f:
        f.write(json.dumps(asdict(entry)) + '\n')
```

This is the only hardcoded `/tmp/` usage. No existing `os.environ.get('TMPDIR')` pattern.

### Implementation Sketch

```python
import os
import tempfile

def _save_tasks_with_fallback(self, tasks: Dict[str, Any]):
    """Save tasks to JSON with fallback to TMPDIR if data/ is read-only"""
    TASKS_FILE = Path(__file__).parent.parent.parent / "data" / "pipeline_tasks.json"

    try:
        # Try primary location first
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TASKS_FILE.write_text(json.dumps(tasks, indent=2, default=str))
        logger.info("[Pipeline] Tasks saved to primary location")
        return True

    except (PermissionError, OSError) as e:
        logger.warning(f"[Pipeline] Primary write failed: {e}, using TMPDIR fallback")

        try:
            # Fallback to /tmp/ or $TMPDIR
            tmpdir = os.getenv('TMPDIR', '/tmp')
            tmpfile = Path(tmpdir) / f"vetka_pipeline_tasks_{self.chat_id}.json"

            tmpfile.write_text(json.dumps(tasks, indent=2, default=str))
            logger.warning(f"[Pipeline] Tasks saved to temporary location: {tmpfile}")
            return True

        except Exception as e2:
            logger.error(f"[Pipeline] Fallback write also failed: {e2}")
            return False
```

### Advantages

✅ Works cross-platform (`/tmp` or `$TMPDIR`)
✅ No external service dependency
✅ Requires minimal code change
✅ Transparent to calling code

### Disadvantages

❌ Temporary files may be cleaned up by OS
❌ Not persistent across reboots
❌ Per-session isolation (chat_id-scoped)
❌ Lost on `/tmp` cleanup (e.g., weekly maintenance)

### Lifespan

- **macOS**: `/var/folders/...` cleaned every 3 days without access
- **Linux**: `/tmp` typically cleaned on reboot or weekly
- **Windows**: `%TEMP%` similar lifecycle

---

## Section 4: Alternative 3 - In-Memory Dict (Session-only)

### Implementation Sketch

```python
class AgentPipeline:
    # Class-level cache shared across instances in same process
    _tasks_cache: Dict[str, Dict[str, Any]] = {}
    _cache_lock = asyncio.Lock()

    def __init__(self, chat_id: Optional[str] = None, ...):
        self.chat_id = chat_id
        # Instance can still load from disk if available
        self._tasks = self._load_tasks()

    async def _update_task(self, task: PipelineTask):
        """Update task in memory cache with fallback to disk"""
        async with self._cache_lock:
            self._tasks[task.task_id] = asdict(task)
            # Also update class-level cache
            self._tasks_cache[task.task_id] = self._tasks[task.task_id]

        # Try to persist to disk (non-critical if fails)
        try:
            await self._save_tasks_async(self._tasks)
        except Exception as e:
            logger.debug(f"[Pipeline] Async persist failed (non-critical): {e}")

    @classmethod
    def get_cached_task(cls, task_id: str) -> Optional[Dict]:
        """Get task from in-memory cache (fast path)"""
        return cls._tasks_cache.get(task_id)
```

### Advantages

✅ Extremely fast (no I/O)
✅ No external dependencies
✅ Perfect for interactive workflows
✅ Survives MCP sandbox read-only restrictions

### Disadvantages

❌ Lost when process exits
❌ Not shared across pipeline instances
❌ Not queryable by other agents
❌ Only suitable for transient workflows

### Use Case

Best for:
- Interactive development workflows
- Single-session experiments
- Rapid prototyping without persistence requirement

---

## Section 5: Alternative 4 - Hybrid Pattern (Recommended)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Pipeline._update_task()                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
              ┌─────────────────────────────┐
              │  Try Primary (data/...)     │
              └─────────────────────────────┘
                     ↓ (success)
              ✓ Logged and done

                     ↓ (fail: read-only)
              ┌─────────────────────────────┐
              │  Fallback 1: Qdrant         │ ← Preferred
              └─────────────────────────────┘
                     ↓ (success)
              ✓ Logged + analytics

                     ↓ (fail: offline)
              ┌─────────────────────────────┐
              │  Fallback 2: TMPDIR         │ ← Safe
              └─────────────────────────────┘
                     ↓ (success)
              ✓ Logged + session-scoped

                     ↓ (fail: perms)
              ┌─────────────────────────────┐
              │  Fallback 3: In-Memory      │ ← Last resort
              └─────────────────────────────┘
                     ↓ (success)
              ⚠️ Logged + ephemeral warning
```

### Implementation

```python
def _update_task(self, task: PipelineTask):
    """Update task with intelligent fallback strategy"""
    task_dict = asdict(task)
    storage_status = None

    # Try 1: Primary (data/pipeline_tasks.json)
    try:
        self._save_tasks({task.task_id: task_dict})
        logger.info(f"[Pipeline] Task saved (PRIMARY): {task.task_id}")
        storage_status = "primary"
        return
    except (PermissionError, OSError) as e:
        logger.debug(f"[Pipeline] Primary write failed: {type(e).__name__}")

    # Try 2: Qdrant (recommended fallback)
    try:
        self._upsert_task_to_qdrant(task)
        logger.warning(f"[Pipeline] Task saved (QDRANT FALLBACK): {task.task_id}")
        storage_status = "qdrant"
        return
    except Exception as e:
        logger.debug(f"[Pipeline] Qdrant fallback failed: {e}")

    # Try 3: TMPDIR
    try:
        tmpdir = os.getenv('TMPDIR', '/tmp')
        tmpfile = Path(tmpdir) / f"vetka_pipeline_{self.chat_id}.json"
        existing = json.loads(tmpfile.read_text()) if tmpfile.exists() else {}
        existing[task.task_id] = task_dict
        tmpfile.write_text(json.dumps(existing, indent=2, default=str))
        logger.warning(f"[Pipeline] Task saved (TMPDIR FALLBACK): {task.task_id}")
        storage_status = "tmpdir"
        return
    except Exception as e:
        logger.debug(f"[Pipeline] TMPDIR fallback failed: {e}")

    # Try 4: In-memory (last resort)
    if not hasattr(self, '_emergency_cache'):
        self._emergency_cache = {}
    self._emergency_cache[task.task_id] = task_dict
    logger.error(f"[Pipeline] Task saved (EMERGENCY IN-MEMORY): {task.task_id}")
    logger.error("[Pipeline] ⚠️  This task will be LOST when process exits!")
    storage_status = "emergency"

    # Emit status for visibility
    self._emit_progress("@pipeline", f"⚠️ Storage degraded ({storage_status})")
```

### Advantages

✅ **Resilient** - Works in all failure scenarios
✅ **Intelligent** - Uses best available storage
✅ **Observable** - Clear logging at each fallback level
✅ **Graceful degradation** - Never loses data silently
✅ **Qdrant-first** - Leverages existing infrastructure

### Disadvantages

❌ More complex code
❌ Multiple code paths to test

---

## Section 6: Qdrant Collections Needed

### New Collection: VetkaPipelineTasks

```python
COLLECTION_NAMES = {
    'tree': 'VetkaTree',
    'leaf': 'VetkaLeaf',
    'changelog': 'VetkaChangeLog',
    'trash': 'VetkaTrash',
    'chat': 'VetkaGroupChat',
    'tasks': 'VetkaPipelineTasks',  # ← NEW
}

# Initialize with vector size 768 (same as others)
# Payload: {task_id, task, phase_type, status, timestamp, results, subtasks_count}
```

---

## Section 7: Staging.json Pattern (Already Exists!)

### H4_FALLBACK_PATTERN

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/utils/staging_utils.py`

The codebase already has a **proven fallback pattern** for persistent JSON with ELISION compression:

```python
def _save_staging(data: Dict[str, Any], compress_large: bool = True) -> bool:
    """Save staging data to JSON (atomic write) with optional ELISION compression."""
    try:
        STAGING_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp_file = STAGING_FILE.with_suffix('.tmp')
        temp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        temp_file.rename(STAGING_FILE)  # Atomic rename
        return True
    except Exception as e:
        logger.error(f"[Staging] Failed to save: {e}")
        return False
```

**This pattern can be adapted for pipeline tasks!**

---

## Recommendations

### Phase 117 Implementation Plan

#### Priority 1 (Immediate)
1. Add error handling wrapper to `_save_tasks()`:
   - Catch `PermissionError` and `OSError`
   - Log the failure type
   - Return boolean success indicator

#### Priority 2 (Short-term - ~1 week)
2. Implement Qdrant fallback:
   - Create `VetkaPipelineTasks` collection
   - Add `_upsert_task_to_qdrant()` method
   - Integrate with existing `QdrantBatchManager`

#### Priority 3 (Medium-term - ~2 weeks)
3. Implement TMPDIR fallback:
   - Follow existing pattern in `qdrant_client.py`
   - Use `os.getenv('TMPDIR', '/tmp')`
   - Scope by chat_id for isolation

#### Priority 4 (Long-term - nice-to-have)
4. Dashboard visibility:
   - Show storage status (primary/qdrant/tmpdir/emergency)
   - Alert on graceful degradation
   - Recover from TMPDIR to primary on write permission restoration

---

## Testing Strategy

### Test Cases

```python
# Test 1: Normal operation
test_primary_storage()  # Should use data/pipeline_tasks.json

# Test 2: Read-only simulation
test_readonly_fallback()  # Should fallback to Qdrant

# Test 3: Qdrant offline
test_qdrant_offline()  # Should fallback to TMPDIR

# Test 4: All storage unavailable
test_emergency_inmemory()  # Should use emergency cache

# Test 5: Recovery
test_recovery_on_permission_restore()  # Should re-use primary after recovery
```

---

## Files to Modify

1. **Primary**:
   - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/agent_pipeline.py`

2. **Supporting**:
   - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_client.py`
   - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_batch_manager.py`

3. **Optional**:
   - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py` (for observability)

---

## Conclusion

The **Hybrid Fallback Pattern** with Qdrant-first approach is recommended because:

1. ✅ Qdrant already proven for chat persistence
2. ✅ Follows existing VETKA architecture
3. ✅ Provides graceful degradation
4. ✅ Works in MCP sandbox
5. ✅ Observable and debuggable
6. ✅ Recoverable to primary storage

Implementation effort: ~4-6 hours for full solution.

---

## Related Markers

- `MARKER_102.3`: Current task storage implementation
- `MARKER_103.7`: Chat history persistence (reference implementation)
- `MARKER_104_ELISION_PROMPTS`: Compression strategy for large data
- `MARKER_117_2A_FIX_A`: Fixed MCP routing issues (related)

---

**Next Step**: Implement Phase 117.2 - Pipeline Storage Resilience
