# H4: Implementation Roadmap — Pipeline Storage Resilience

## Timeline Overview

```
Phase 117.2        Phase 117.3        Phase 117.4        Phase 117.5+
(Immediate)        (Week 1)           (Week 2)           (Ongoing)
────────────       ────────────       ────────────       ────────────
Error Handler      Qdrant Fallback    TMPDIR Fallback    Dashboard
1-2 hours          2-3 hours          1 hour             1-2 hours
```

---

## Phase 117.2: Error Handler Wrapper (Immediate)

### Objective
Add basic error handling to `_save_tasks()` so failures are visible, not silent.

### Code Changes

**File**: `src/orchestration/agent_pipeline.py`

```python
def _save_tasks(self, tasks: Dict[str, Any]) -> bool:
    """Save tasks to JSON storage with error handling"""
    try:
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TASKS_FILE.write_text(json.dumps(tasks, indent=2, default=str))
        logger.info(f"[Pipeline] Tasks persisted ({len(tasks)} tasks)")
        return True
    except (PermissionError, OSError) as e:
        logger.error(f"[Pipeline] Primary storage failed: {type(e).__name__} - {e}")
        return False
    except Exception as e:
        logger.error(f"[Pipeline] Unexpected error: {e}")
        return False

def _update_task(self, task: PipelineTask):
    """Update task with error awareness"""
    tasks = self._load_tasks()
    tasks[task.task_id] = asdict(task)
    success = self._save_tasks(tasks)

    if not success:
        logger.warning(f"[Pipeline] Task {task.task_id} not persisted - fallback needed!")
        self._emit_progress("@pipeline", f"⚠️ Storage unavailable for {task.task_id}")
```

### Testing
```bash
# Test normal operation
pytest tests/test_pipeline_storage.py::test_primary_storage

# Test read-only simulation
chmod 444 data/pipeline_tasks.json
pytest tests/test_pipeline_storage.py::test_readonly_error
chmod 644 data/pipeline_tasks.json
```

### Metrics to Track
- ✅ Primary write successes
- ❌ Primary write failures (type)
- ⏱️ Write latency

---

## Phase 117.3: Qdrant Fallback (Week 1)

### Objective
Implement Qdrant as primary fallback for resilience.

### Step 1: Initialize Collection

**File**: `src/memory/qdrant_client.py`

```python
COLLECTION_NAMES = {
    'tree': 'VetkaTree',
    'leaf': 'VetkaLeaf',
    'changelog': 'VetkaChangeLog',
    'trash': 'VetkaTrash',
    'chat': 'VetkaGroupChat',
    'tasks': 'VetkaPipelineTasks',  # ← NEW
}

def _initialize_collections(self):
    """Create collections if they don't exist"""
    # ... existing code ...
    for col_name in self.COLLECTION_NAMES.values():
        if col_name not in existing:
            self.client.recreate_collection(
                collection_name=col_name,
                vectors_config=VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"✅ Created collection: {col_name}")
```

### Step 2: Add Task Upsert Method

**File**: `src/orchestration/agent_pipeline.py`

```python
def _upsert_task_to_qdrant(self, task: PipelineTask) -> bool:
    """Store pipeline task in Qdrant as fallback"""
    try:
        from src.memory.qdrant_client import get_qdrant_client
        from src.utils.embedding_service import get_embedding
        from qdrant_client.models import PointStruct
        import hashlib

        client = get_qdrant_client()
        if not client or not client.client:
            logger.warning("[Pipeline] Qdrant not available for fallback")
            return False

        # Embed task description for semantic search
        embedding = get_embedding(task.task[:500])
        if not embedding:
            logger.warning("[Pipeline] Failed to generate embedding for task")
            return False

        # Deterministic point ID
        point_id = int(hashlib.md5(task.task_id.encode()).hexdigest()[:16], 16)

        payload = {
            'task_id': task.task_id,
            'task': task.task,
            'phase_type': task.phase_type,
            'status': task.status,
            'timestamp': task.timestamp,
            'subtasks_count': len(task.subtasks) if task.subtasks else 0,
            'visible_to_user': task.visible_to_user,
        }

        point = PointStruct(id=point_id, vector=embedding, payload=payload)
        client.client.upsert(
            collection_name=client.COLLECTION_NAMES['tasks'],
            points=[point]
        )

        logger.info(f"[Pipeline] Task upserted to Qdrant: {task.task_id}")
        return True

    except Exception as e:
        logger.warning(f"[Pipeline] Qdrant upsert failed: {e}")
        return False
```

### Step 3: Update Fallback Chain

**File**: `src/orchestration/agent_pipeline.py`

```python
def _update_task(self, task: PipelineTask):
    """Update task with Qdrant fallback"""
    tasks = self._load_tasks()
    tasks[task.task_id] = asdict(task)

    # Try primary
    if self._save_tasks(tasks):
        return  # Success!

    # Fallback to Qdrant
    if self._upsert_task_to_qdrant(task):
        logger.warning(f"[Pipeline] Task saved to QDRANT (primary unavailable)")
        self._emit_progress("@pipeline", "⚠️ Using Qdrant fallback for task storage")
        return

    # More fallbacks coming...
    logger.error(f"[Pipeline] CRITICAL: Cannot save task {task.task_id}")
```

### Testing
```python
# Test Qdrant fallback
pytest tests/test_pipeline_storage.py::test_qdrant_fallback

# Verify retrievability
def test_qdrant_retrieve():
    client = get_qdrant_client()
    results = client.client.scroll(
        collection_name='VetkaPipelineTasks',
        limit=10,
        with_payload=True
    )
    assert len(results[0]) > 0
```

### Metrics
- ✅ Qdrant write successes
- ❌ Qdrant write failures (type)
- 📊 Tasks in Qdrant vs. filesystem

---

## Phase 117.4: TMPDIR Fallback (Week 2)

### Objective
Implement ephemeral fallback for offline Qdrant.

### Code Changes

**File**: `src/orchestration/agent_pipeline.py`

```python
import os
from pathlib import Path

def _save_to_tmpdir(self, task: PipelineTask) -> bool:
    """Save task to TMPDIR as fallback"""
    try:
        tmpdir = os.getenv('TMPDIR', '/tmp')
        tmpfile = Path(tmpdir) / f"vetka_pipeline_{self.chat_id}.json"

        # Load existing or create new
        existing = {}
        if tmpfile.exists():
            try:
                existing = json.loads(tmpfile.read_text())
            except json.JSONDecodeError:
                logger.warning("[Pipeline] Corrupted TMPDIR backup, starting fresh")

        # Update with new task
        existing[task.task_id] = asdict(task)

        # Atomic write
        tmpfile.write_text(json.dumps(existing, indent=2, default=str))
        logger.warning(f"[Pipeline] Task saved to TMPDIR: {tmpfile}")

        return True

    except Exception as e:
        logger.error(f"[Pipeline] TMPDIR fallback failed: {e}")
        return False

def _update_task(self, task: PipelineTask):
    """Update task with full fallback chain"""
    tasks = self._load_tasks()
    tasks[task.task_id] = asdict(task)

    # Try 1: Primary
    if self._save_tasks(tasks):
        return

    # Try 2: Qdrant
    if self._upsert_task_to_qdrant(task):
        return

    # Try 3: TMPDIR
    if self._save_to_tmpdir(task):
        self._emit_progress("@pipeline", "⚠️ Using TMPDIR fallback (ephemeral)")
        return

    # Try 4: In-memory
    self._save_to_emergency_cache(task)
```

### Testing
```python
# Test TMPDIR fallback (simulate Qdrant offline)
def test_tmpdir_fallback(tmp_path, monkeypatch):
    # Disable Qdrant
    monkeypatch.setenv('QDRANT_OFFLINE', '1')

    # Create pipeline and task
    pipeline = AgentPipeline()
    task = PipelineTask(task_id="test_1", task="test", phase_type="research")

    # Update should use TMPDIR
    pipeline._update_task(task)

    # Verify in TMPDIR
    tmpdir = Path(os.getenv('TMPDIR', '/tmp'))
    tmpfile = tmpdir / f"vetka_pipeline_{pipeline.chat_id}.json"
    assert tmpfile.exists()

    data = json.loads(tmpfile.read_text())
    assert "test_1" in data
```

### Lifespan Management
```python
# Log TMPDIR status
logger.warning(f"[Pipeline] TMPDIR fallback: {tmpfile}")
logger.warning("[Pipeline] ℹ️  Data is ephemeral - will be lost on:")
logger.warning("[Pipeline]   - macOS: 3 days without access")
logger.warning("[Pipeline]   - Linux: reboot or weekly maintenance")
logger.warning("[Pipeline]   - Windows: similar lifecycle")
logger.warning("[Pipeline]   Recovery: Task will re-persist when primary becomes available")
```

---

## Phase 117.5: Emergency In-Memory Cache (Optional)

### Code
```python
def _save_to_emergency_cache(self, task: PipelineTask):
    """Last-resort in-memory storage"""
    if not hasattr(self, '_emergency_cache'):
        self._emergency_cache = {}

    self._emergency_cache[task.task_id] = asdict(task)

    logger.critical(f"[Pipeline] EMERGENCY: Task {task.task_id} saved to in-memory only!")
    logger.critical("[Pipeline] ❌ THIS TASK WILL BE LOST WHEN PROCESS EXITS!")

    # Alert with urgent message
    self._emit_progress(
        "@pipeline",
        "🚨 CRITICAL: All persistent storage unavailable! Data will be lost on exit."
    )
```

---

## Phase 117.6: Dashboard Integration (Optional)

### Status Display

```javascript
// UI displays storage status per task:
PRIMARY   ✅ (data/pipeline_tasks.json)
QDRANT    🔵 (VetkaPipelineTasks)
TMPDIR    🟡 ($TMPDIR/vetka_pipeline_*.json)
EMERGENCY ⚠️  (process in-memory only)
```

### Metrics Endpoint

```python
@router.get("/api/debug/pipeline/storage-status")
def get_storage_status():
    return {
        "primary_available": check_primary_write(),
        "qdrant_available": check_qdrant_connection(),
        "tmpdir_available": check_tmpdir_write(),
        "tasks_in_primary": len(load_from_primary()),
        "tasks_in_qdrant": count_qdrant_tasks(),
        "tasks_in_tmpdir": count_tmpdir_tasks(),
        "emergency_cache_size": len(pipeline._emergency_cache) if hasattr(pipeline, '_emergency_cache') else 0,
        "current_fallback_level": get_current_fallback_level(),
    }
```

---

## Testing Matrix

| Scenario | Primary | Qdrant | TMPDIR | In-Memory | Expected |
|----------|---------|--------|--------|-----------|----------|
| Normal operation | ✅ | N/A | N/A | N/A | Use PRIMARY |
| Primary read-only | ❌ | ✅ | N/A | N/A | Use QDRANT |
| Primary + Qdrant down | ❌ | ❌ | ✅ | N/A | Use TMPDIR |
| All except memory | ❌ | ❌ | ❌ | ✅ | Use EMERGENCY |
| Recovery | ✅ | ✅ | ✅ | ✅ | Migrate to PRIMARY |

---

## Deployment Checklist

### Phase 117.2
- [ ] Add error handling to `_save_tasks()`
- [ ] Add logger statements
- [ ] Unit tests for error paths
- [ ] Deploy to staging

### Phase 117.3
- [ ] Create `VetkaPipelineTasks` collection
- [ ] Implement `_upsert_task_to_qdrant()`
- [ ] Integrate into `_update_task()`
- [ ] Integration tests with Qdrant
- [ ] Deploy to staging → production

### Phase 117.4
- [ ] Implement `_save_to_tmpdir()`
- [ ] Add TMPDIR lifespan warnings
- [ ] Test on macOS, Linux, Windows
- [ ] Deploy

### Phase 117.5 (Optional)
- [ ] Implement emergency cache
- [ ] Add critical alerts
- [ ] Test recovery flows
- [ ] Document for troubleshooting

### Phase 117.6 (Optional)
- [ ] Dashboard status display
- [ ] Metrics endpoint
- [ ] Alert thresholds
- [ ] Observability dashboard

---

## Success Criteria

✅ **Phase 117.2**: Pipeline tasks never silently lost to write failures
✅ **Phase 117.3**: MCP sandbox doesn't break pipelines (Qdrant fallback)
✅ **Phase 117.4**: Works offline with ephemeral storage
✅ **Phase 117.5**: Last-resort protection against total failure
✅ **Phase 117.6**: Visibility into storage health

---

## Rollback Strategy

If fallback causes issues:

1. **Disable Qdrant fallback**: Set env var `PIPELINE_SKIP_QDRANT=1`
2. **Disable TMPDIR fallback**: Set env var `PIPELINE_SKIP_TMPDIR=1`
3. **Emergency mode**: Only use primary (may lose data if primary fails)

---

## Estimated Effort

| Phase | Task | Duration | Priority |
|-------|------|----------|----------|
| 117.2 | Error handler | 1-2h | ✅ CRITICAL |
| 117.3 | Qdrant fallback | 2-3h | ✅ HIGH |
| 117.4 | TMPDIR fallback | 1h | ✅ HIGH |
| 117.5 | In-memory cache | 1h | 🟡 MEDIUM |
| 117.6 | Dashboard | 1-2h | 🟡 MEDIUM |
| Testing | Full suite | 2h | ✅ CRITICAL |
| Docs | Runbooks | 1h | 🟡 MEDIUM |

**Total**: ~12-15 hours for full solution, ~5-6 hours for MVP (117.2-117.4)

---

**Generated**: 2026-02-07
**For**: Phase 117 - Pipeline Storage Resilience
