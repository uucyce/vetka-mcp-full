# HAIKU SCOUT H4: Quick Reference Markers

## Key Findings

### H4_UPDATE_TASK_METHOD
**Location**: `src/orchestration/agent_pipeline.py:531-535`

```python
def _update_task(self, task: PipelineTask):
    """Update single task in storage"""
    tasks = self._load_tasks()
    tasks[task.task_id] = asdict(task)
    self._save_tasks(tasks)
```

**Issue**: No error handling. File write fails silently when read-only in MCP sandbox.

---

### H4_PIPELINE_TASK_FIELDS

**Fields in PipelineTask dataclass** (lines 78-97):
```
task_id: str
task: str
phase_type: str
status: str
subtasks: List[Subtask]
timestamp: float
results: Optional[Dict]
visible_to_user: bool
stream_level: str
highlight_artifacts: bool
```

**Fields in Subtask dataclass** (lines 62-73):
```
description: str
needs_research: bool
question: Optional[str]
context: Optional[Dict]
result: Optional[str]
status: str
marker: Optional[str]
visible: bool
stream_result: bool
```

**Total**: 19 fields (all JSON-serializable)

---

### H4_QDRANT_COLLECTIONS

**Existing Collections** (qdrant_client.py:85-91):

| Key | Collection Name | Purpose |
|-----|-----------------|---------|
| `tree` | VetkaTree | Hierarchical nodes |
| `leaf` | VetkaLeaf | Detail information |
| `changelog` | VetkaChangeLog | Audit trail |
| `trash` | VetkaTrash | Deleted items |
| `chat` | VetkaGroupChat | Chat persistence |

**Proposed New Collection**:
- `tasks` → `VetkaPipelineTasks` (for pipeline task storage)

---

### H4_TMPDIR_USAGE

**Current Usage in Codebase**:
- File: `src/memory/qdrant_client.py:652`
- Pattern: Hardcoded `/tmp/vetka_changelog.jsonl`

**Recommendation**: Use `os.getenv('TMPDIR', '/tmp')` for cross-platform support

**Lifespan**:
- macOS: `/var/folders/...` (3 days without access)
- Linux: `/tmp` (on reboot or weekly)
- Windows: `%TEMP%` (similar)

---

### H4_FALLBACK_PATTERN

**Reference Implementation**: `src/utils/staging_utils.py` (atomic write pattern)

```python
def _save_staging(data: Dict[str, Any]) -> bool:
    try:
        temp_file = STAGING_FILE.with_suffix('.tmp')
        temp_file.write_text(json.dumps(data, indent=2))
        temp_file.rename(STAGING_FILE)  # Atomic
        return True
    except Exception as e:
        logger.error(f"Failed to save: {e}")
        return False
```

**Apply this pattern** to `_save_tasks()` with multi-level fallback:
1. Primary: `data/pipeline_tasks.json`
2. Qdrant: `VetkaPipelineTasks` collection
3. TMPDIR: `$TMPDIR/vetka_pipeline_*.json`
4. Emergency: In-memory dict

---

## Recommended Solution

**Hybrid Fallback Pattern with Qdrant-First**

### Fallback Chain
```
Primary (data/...)
  ↓ fail (read-only) → Qdrant ✓ (recommended)
                        ↓ fail → TMPDIR ✓ (safe)
                                 ↓ fail → In-Memory ⚠️ (ephemeral)
```

### Implementation Effort
- **Phase 117.2 (Immediate)**: Error handling wrapper (~1-2 hours)
- **Phase 117.3 (Short-term)**: Qdrant integration (~2-3 hours)
- **Phase 117.4 (Medium-term)**: TMPDIR fallback (~1 hour)
- **Optional**: Dashboard observability (~1-2 hours)

### Files to Modify
1. `src/orchestration/agent_pipeline.py` (primary)
2. `src/memory/qdrant_client.py` (collection setup)
3. `src/memory/qdrant_batch_manager.py` (batch integration)

---

## Status Codes

- ✅ **PRIMARY**: Using `data/pipeline_tasks.json`
- 🔵 **QDRANT**: Using `VetkaPipelineTasks` collection
- 🟡 **TMPDIR**: Using session-scoped temp file
- ⚠️ **EMERGENCY**: Using in-memory dict (process-ephemeral)

---

## Related Markers in Codebase

- `MARKER_102.3`: Task storage (current implementation)
- `MARKER_103.7`: Chat persistence (reference impl)
- `MARKER_104_ELISION_PROMPTS`: Large data compression
- `MARKER_111.18`: QdrantBatchManager (batch operations)
- `MARKER_117_2A_FIX_A`: MCP routing fixes (related)

---

## Key Insights

1. **File system is unreliable in MCP sandbox** — Current code assumes write access
2. **Qdrant is already proven** — Used for chat (Phase 103.7), can be reused
3. **Staging utils has pattern** — `src/utils/staging_utils.py` shows atomic writes
4. **No in-memory caching exists** — Good opportunity to add resilience
5. **Chat batch manager is mature** — Can be reused for tasks batching

---

**Generated**: 2026-02-07 by HAIKU Scout H4
**For**: Phase 117 - MCP Sandbox Resilience
**Confidence**: High (code inspection + pattern analysis)
