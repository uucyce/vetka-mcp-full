# ROADMAP: CORTEX Tool Freshness (Phase 195)

## Overview

5 tasks, sequential dependency chain. Total complexity: medium.
Each task is self-contained with clear acceptance criteria.

## Task Breakdown

### T1: SourceWatch — Tool-to-File Mapping + Change Detection
**Phase:** 195.2
**Type:** build
**Complexity:** medium
**Priority:** 1

**Description:**
Create `src/services/tool_source_watch.py` with:
1. Auto-discover tool→source file mapping by scanning `src/mcp/tools/*.py` for `@tool(name="...")` decorators
2. Store mapping in `data/reflex/tool_source_map.json`
3. Support manual overrides via `data/reflex/tool_source_overrides.json`
4. `check_freshness(tool_id) -> Optional[FreshnessEvent]` — compare git commit hash vs stored
5. `scan_all() -> List[FreshnessEvent]` — batch scan for session_init

**Allowed paths:**
- `src/services/tool_source_watch.py`
- `data/reflex/tool_source_map.json`
- `data/reflex/tool_source_overrides.json`
- `data/reflex/tool_freshness.json`
- `tests/test_tool_source_watch.py`

**Acceptance criteria:**
- [ ] Auto-discovers >=80% of tools from tool_catalog.json
- [ ] Git commit hash comparison works (no false positives on checkout)
- [ ] FreshnessEvent contains: tool_id, old_commit, new_commit, epoch, source_files
- [ ] tool_freshness.json persists between sessions
- [ ] scan_all() completes in <500ms for 15 source files

**Architecture docs:** `docs/195_CORTEX_FRESHNESS/ARCHITECTURE_195_TOOL_FRESHNESS.md`

---

### T2: Epoch-Based Feedback Decay
**Phase:** 195.3
**Type:** build
**Complexity:** low
**Priority:** 1
**Depends on:** T1

**Description:**
Modify `reflex_feedback.py :: _aggregate_entries()` to apply epoch-based discount:
1. Load tool_freshness.json for epoch data
2. For each feedback entry, determine its epoch by comparing timestamp vs epoch history
3. If entry.epoch < current_epoch → multiply weight by `0.1 ^ epochs_behind`
4. Pre-update failures contribute 10% (1 epoch) or 1% (2 epochs)

**Allowed paths:**
- `src/services/reflex_feedback.py`
- `tests/test_reflex_feedback.py` (add epoch discount tests)

**Acceptance criteria:**
- [ ] Pre-update failures discounted by 10× per epoch gap
- [ ] Post-update entries unaffected (weight = 1.0)
- [ ] Tool with 0% success pre-update shows ~50% (cold start) after epoch bump
- [ ] Existing tests still pass
- [ ] No performance regression in aggregation (<10ms for 500 entries)

**Architecture docs:** `docs/195_CORTEX_FRESHNESS/ARCHITECTURE_195_TOOL_FRESHNESS.md`

---

### T3: CAM Curiosity Boost for Fresh Tools
**Phase:** 195.4
**Type:** build
**Complexity:** low
**Priority:** 2
**Depends on:** T1

**Description:**
Modify `reflex_scorer.py :: _cam_signal()` to add freshness boost:
1. Check tool_freshness_log for recently updated tools
2. Add +0.3 CAM boost decaying linearly over 48 hours
3. Combined with sparse boost (×1.5 when > 0.7), this raises fresh tools in ranking

**Allowed paths:**
- `src/services/reflex_scorer.py`
- `tests/test_reflex_scorer.py` (add freshness boost tests)

**Acceptance criteria:**
- [ ] Recently updated tool gets +0.3 CAM boost at t=0
- [ ] Boost decays to 0 at t=48h
- [ ] Sparse boost applies correctly (>0.7 → ×1.5)
- [ ] Tools NOT recently updated are unaffected
- [ ] Existing scorer tests pass

**Architecture docs:** `docs/195_CORTEX_FRESHNESS/ARCHITECTURE_195_TOOL_FRESHNESS.md`

---

### T4: Guard Warning Clearance
**Phase:** 195.5
**Type:** build
**Complexity:** low
**Priority:** 2
**Depends on:** T1

**Description:**
Modify `reflex_guard.py :: _check_cortex_failures()` to suppress cortex_failure warnings
for tools updated within the last 48 hours.

**Allowed paths:**
- `src/services/reflex_guard.py`
- `tests/test_reflex_guard.py` (add freshness suppression tests)

**Acceptance criteria:**
- [ ] Tool with 0% success rate but updated <48h ago → no cortex_failure warning
- [ ] Tool with 0% success rate and NOT recently updated → warning persists
- [ ] After 48h without improvement → warning re-appears
- [ ] Existing guard tests pass

**Architecture docs:** `docs/195_CORTEX_FRESHNESS/ARCHITECTURE_195_TOOL_FRESHNESS.md`

---

### T5: session_init Integration + Watchdog Trigger
**Phase:** 195.6
**Type:** build
**Complexity:** low
**Priority:** 1
**Depends on:** T1, T2, T3, T4

**Description:**
Wire SourceWatch into session_init so freshness scan runs automatically:
1. Call `source_watch.scan_all()` during session_init
2. If any tools freshened: log events, update tool_freshness.json
3. Add `freshness_events` section to session_init response (list of recently updated tools)
4. Add freshness summary to `reflex_report` in session_init

**Allowed paths:**
- `src/mcp/tools/session_tools.py`
- `tests/test_session_tools.py`

**Acceptance criteria:**
- [ ] session_init triggers SourceWatch scan automatically
- [ ] Freshness events appear in session_init response
- [ ] Updated tools listed in reflex_report section
- [ ] No regression in session_init latency (budget: +300ms max)
- [ ] Zero manual intervention required

**Architecture docs:** `docs/195_CORTEX_FRESHNESS/ARCHITECTURE_195_TOOL_FRESHNESS.md`

---

## Dependency Graph

```
T1 (SourceWatch)
├── T2 (Epoch Decay) ──┐
├── T3 (CAM Boost)  ───┤
├── T4 (Guard Clear) ──┤
└───────────────────────┴── T5 (session_init integration)
```

## Execution Strategy

- **T1** is the foundation — must be done first
- **T2, T3, T4** are independent of each other — can be parallelized
- **T5** is the final integration — depends on all others
- Total: 5 tasks, critical path = 3 steps (T1 → T2|T3|T4 → T5)
