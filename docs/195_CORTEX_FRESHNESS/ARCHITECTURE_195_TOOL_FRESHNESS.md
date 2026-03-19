# ARCHITECTURE: CORTEX Tool Freshness Signal (Phase 195.1)

## Problem Statement

When a VETKA tool's source code is fixed/updated, its historical failure data in CORTEX
continues to drag down its REFLEX score. Example: `vetka_read_file` has 0% success over 59 calls.
Even after the bug is fixed, the tool remains penalized until entries naturally decay (~7 days half-life).

**Result:** Agents avoid recently-fixed tools for days, defeating the purpose of the fix.

## Design Goals

1. **Auto-detect** when a tool's source file changes (zero manual intervention)
2. **Discount** pre-update failure history for that tool
3. **Curiosity boost** — encourage re-trying updated tools via CAM novelty signal
4. **No new REFLEX signal** — extend existing infrastructure (Feedback + MGC)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   TOOL FRESHNESS WATCHDOG                │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐   ┌─────────────┐ │
│  │  SourceWatch  │───→│ FreshnessLog │──→│ FeedbackReset│ │
│  │ (git mtime)   │    │ (version     │   │ (epoch-based │ │
│  │               │    │  epochs)     │   │  decay)      │ │
│  └──────────────┘    └──────────────┘   └─────────────┘ │
│         │                                      │         │
│         ▼                                      ▼         │
│  ┌──────────────┐                     ┌──────────────┐   │
│  │ CAM Novelty   │                     │ REFLEX Guard │   │
│  │ (surprise     │                     │ (clear stale │   │
│  │  injection)   │                     │  warnings)   │   │
│  └──────────────┘                     └──────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Component Design

### C1: SourceWatch — Tool-to-File Mapping + Change Detection

**File:** `src/services/tool_source_watch.py`

**Concept:** Map each MCP tool to its source file(s), track mtimes, detect changes.

```python
# Tool → source file mapping (auto-discovered + manual overrides)
TOOL_SOURCE_MAP: Dict[str, List[str]] = {
    "vetka_read_file":     ["src/mcp/tools/file_tools.py"],
    "vetka_edit_file":     ["src/mcp/tools/file_tools.py"],
    "vetka_search_files":  ["src/mcp/tools/search_tools.py"],
    "vetka_task_board":    ["src/orchestration/task_board.py"],
    "vetka_session_init":  ["src/mcp/tools/session_tools.py"],
    # ... auto-populated from tool_catalog.json + MCP tool registry
}
```

**Auto-discovery strategy:**
1. Parse `tool_catalog.json` — extract `tool_id` and `namespace`
2. Scan `src/mcp/tools/*.py` — match `@tool(name="...")` decorators to tool_ids
3. Store discovered mapping in `data/reflex/tool_source_map.json`
4. Manual overrides via `data/reflex/tool_source_overrides.json`

**Change detection:**
- On each `session_init` (or heartbeat tick): compare current `os.path.getmtime()` vs stored mtime
- If mtime changed → tool is "freshened"
- Git-aware: use `git log -1 --format=%H -- <file>` to get last commit hash (more reliable than mtime)

### C2: FreshnessLog — Version Epochs

**File:** `data/reflex/tool_freshness.json`

```json
{
  "vetka_read_file": {
    "source_files": ["src/mcp/tools/file_tools.py"],
    "current_epoch": 3,
    "last_commit": "b8f74a9e4",
    "last_mtime": 1773891106.0,
    "updated_at": "2026-03-19T07:00:00Z",
    "history": [
      {"epoch": 1, "commit": "abc123", "ts": "2026-03-12T00:00:00Z"},
      {"epoch": 2, "commit": "def456", "ts": "2026-03-15T00:00:00Z"},
      {"epoch": 3, "commit": "b8f74a9", "ts": "2026-03-19T07:00:00Z"}
    ]
  }
}
```

**Epoch semantics:**
- Each source file change increments the tool's `current_epoch`
- Feedback entries recorded BEFORE this epoch are "pre-update" → discounted
- No need to modify `feedback_log.jsonl` schema — epoch comparison happens at aggregation time

### C3: FeedbackReset — Epoch-Based Decay Multiplier

**Integration point:** `reflex_feedback.py :: _aggregate_entries()`

```python
def _aggregate_entries(self, tool_id, entries, decay_engine=None):
    # Get tool's current epoch and epoch history
    freshness = tool_freshness_log.get(tool_id)

    for entry in entries:
        age_days = (now - entry.timestamp).total_seconds() / 86400

        # Standard decay
        weight = decay_engine.compute_weight(...) if decay_engine else exp(-0.1 * age_days)

        # NEW: Epoch-based discount
        if freshness and entry_epoch < freshness.current_epoch:
            # Pre-update entry: apply steep discount
            epochs_behind = freshness.current_epoch - entry_epoch
            epoch_discount = 0.1 ** epochs_behind  # 10% per epoch
            weight *= epoch_discount

        total_weight += weight
        # ... rest of aggregation
```

**Effect:** Pre-update failures contribute only 10% (1 epoch ago) or 1% (2 epochs ago) to the score.
Post-update calls quickly dominate the aggregate, allowing rapid recovery.

**How entry_epoch is determined:**
- Compare `entry.timestamp` vs `freshness.history[].ts`
- Entry belongs to the epoch active at the time it was recorded

### C4: CAM Novelty Injection — Curiosity Boost

**Integration point:** `reflex_scorer.py :: _cam_signal()`

When a tool is freshened (epoch just incremented):

```python
def _cam_signal(self, tool, context):
    base_surprise = context.cam_surprise  # existing

    # NEW: Tool freshness boost
    freshness = tool_freshness_log.get(tool.tool_id)
    if freshness and freshness.is_recently_updated(hours=48):
        # Inject curiosity: recently-updated tools get CAM boost
        freshness_boost = 0.3  # Significant but not overwhelming
        # Decay the boost over 48 hours
        hours_since = freshness.hours_since_update()
        boost = freshness_boost * max(0, 1.0 - hours_since / 48.0)
        base_surprise = min(1.0, base_surprise + boost)

    # Existing sparse boost
    if base_surprise > 0.7:
        return min(1.0, base_surprise * 1.5)
    return base_surprise
```

**Effect:** For 48 hours after update, tool gets up to +0.3 CAM boost (equivalent to +0.036 final score).
Combined with epoch discount on old failures, the tool quickly rises in recommendations.

### C5: Guard Warning Clearance

**Integration point:** `reflex_guard.py :: _check_cortex_failures()`

```python
def _check_cortex_failures(self, tool_id, context):
    # Existing check...
    stats = self._cortex_cache.get(tool_id)

    # NEW: Skip warning if tool was recently updated
    freshness = tool_freshness_log.get(tool_id)
    if freshness and freshness.is_recently_updated(hours=48):
        return None  # Suppress cortex_failure warning for fresh tools

    # Existing logic continues...
```

## Decision: NOT a 9th Signal

**Rationale:**
- Adding a 9th signal requires rebalancing all 8 existing weights (risk of regression)
- Tool freshness is **orthogonal to context** — it modifies how we interpret EXISTING signals
- Epoch-based decay in Feedback (signal #3) + CAM boost (signal #2) + Guard clearance achieves the same goal
- Simpler: 3 small changes vs 1 new subsystem + weight recalibration

## Decision: Git Commit Hash over OS mtime

**Rationale:**
- `mtime` changes on checkout, rebase, touch — false positives
- `git log -1 --format=%H -- file.py` is deterministic and reflects actual code changes
- Also captures WHO changed the file (for attribution)
- Slightly slower (~50ms per file) but only runs on session_init (once per conversation)

## Data Flow

```
1. Agent starts conversation
2. session_init → SourceWatch scans tool source files
3. For each tool: git log → compare commit hash vs stored
4. If changed:
   a. Increment epoch in tool_freshness.json
   b. Clear cortex_failure warning (Guard)
   c. Set freshness_boost timer (48h)
5. During tool selection:
   a. _aggregate_entries() discounts pre-epoch failures (Feedback signal)
   b. _cam_signal() adds curiosity boost (CAM signal)
6. Agent tries updated tool → new feedback entry recorded at current epoch
7. After 48h: curiosity boost fades, tool judged on NEW performance only
```

## Performance Budget

| Operation | Cost | When |
|-----------|------|------|
| Git mtime scan (15 files) | ~200ms | session_init only |
| Epoch lookup per tool | O(1) dict access | Each scoring call |
| Epoch discount computation | O(n) per entry | Feedback aggregation |
| Freshness boost check | O(1) | Each CAM signal |

**Total overhead per session_init:** <300ms (acceptable, runs once)

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/services/tool_source_watch.py` | CREATE | C1: Tool→file mapping + change detection |
| `data/reflex/tool_freshness.json` | CREATE | C2: Version epoch storage |
| `data/reflex/tool_source_map.json` | CREATE | Auto-discovered tool→file mapping |
| `src/services/reflex_feedback.py` | MODIFY | C3: Epoch-based decay in `_aggregate_entries()` |
| `src/services/reflex_scorer.py` | MODIFY | C4: Freshness boost in `_cam_signal()` |
| `src/services/reflex_guard.py` | MODIFY | C5: Suppress warnings for fresh tools |
| `src/mcp/tools/session_tools.py` | MODIFY | Trigger SourceWatch on init |
| `tests/test_tool_freshness.py` | CREATE | Unit + integration tests |

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| False positive: file touched but tool not actually fixed | Git hash check (only real commits count) |
| Over-boosting: bad tool gets undeserved second chance | Boost only lasts 48h; if tool fails again, penalty resumes |
| Epoch overflow on frequently-changed files | Cap at 100 epochs, compact history |
| Performance: scanning too many files | Only scan tools in tool_catalog.json (95 tools, ~15 unique source files) |

## Markers

- **MARKER_195.1.WATCH** — SourceWatch auto-discovery
- **MARKER_195.1.EPOCH** — FreshnessLog epoch tracking
- **MARKER_195.1.DECAY** — Epoch discount in feedback aggregation
- **MARKER_195.1.BOOST** — CAM novelty injection
- **MARKER_195.1.GUARD** — Warning clearance for fresh tools
