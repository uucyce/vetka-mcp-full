# REFLEX — Roadmap & Test Checklist
## Phase 172: Implementation Plan

---

## Phase 172.P1 — REFLEX Registry (каталог инструментов)
**Effort:** 1 session | **Risk:** Low | **Assignee:** Dragon Bronze/Silver

### Tasks
- [ ] 172.P1.1 Create `data/reflex/tool_catalog.json` schema
- [ ] 172.P1.2 Create `scripts/generate_reflex_catalog.py` — auto-scan sources:
  - `src/tools/registry.py` (ToolDefinition objects)
  - `src/tools/fc_loop.py` (PIPELINE_CODER_TOOLS)
  - `src/agents/tools.py` (AGENT_TOOL_PERMISSIONS)
  - `src/mcp/vetka_mcp_bridge.py` (MCP tools)
  - `src/mcp/mycelium_mcp_server.py` (Mycelium tools)
  - `src/api/routes/cut_routes.py` (CUT endpoints)
- [ ] 172.P1.3 Create `src/services/reflex_registry.py`:
  - `ReflexRegistry.load()` — from JSON
  - `ReflexRegistry.get_tools_for_role(role)` → respects AGENT_TOOL_PERMISSIONS
  - `ReflexRegistry.get_tools_by_intent(intent_tags)` → fuzzy match
  - `ReflexRegistry.get_tool(tool_id)` → single lookup
- [ ] 172.P1.4 Generate initial catalog: run script, verify all tools captured
- [ ] 172.P1.5 Add `deprecated_aliases` mapping (vetka_task_* → mycelium_task_*)

### Tests (`tests/test_reflex_registry.py`)
- [ ] T1.1 `test_catalog_schema_valid` — JSON schema validation for tool_catalog.json
- [ ] T1.2 `test_all_pipeline_tools_in_catalog` — PIPELINE_CODER_TOOLS ⊂ catalog
- [ ] T1.3 `test_all_mcp_tools_in_catalog` — every registered MCP tool in catalog
- [ ] T1.4 `test_role_permissions_match` — registry roles match AGENT_TOOL_PERMISSIONS
- [ ] T1.5 `test_deprecated_aliases_resolve` — old tool names map to new ones
- [ ] T1.6 `test_intent_tag_search` — fuzzy search returns relevant tools
- [ ] T1.7 `test_catalog_no_duplicates` — unique tool_ids

### Markers
- `MARKER_172.P1.REGISTRY` in `reflex_registry.py`
- `MARKER_172.P1.CATALOG` in `tool_catalog.json`

### Exit Criteria
Catalog covers 100% of tools. Registry loads in <10ms. All T1.x tests pass.

---

## Phase 172.P2 — REFLEX Scorer (мгновенный scoring)
**Effort:** 1-2 sessions | **Risk:** Medium | **Assignee:** Opus + Dragon Silver

### Tasks
- [ ] 172.P2.1 Create `src/services/reflex_scorer.py`:
  - `ReflexContext` dataclass (task_embedding, cam_activations, user_prefs, stm_items, phase_type, hope_level, mgc_stats, feedback_scores)
  - `ReflexScorer.recommend(context, available_tools, top_n=5)` → `List[ScoredTool]`
  - `ReflexScorer.score(tool, context)` → float (0.0-1.0)
- [ ] 172.P2.2 Implement 8 signal scorers:
  - `_semantic_match()` — Qdrant vector similarity (intent_tags vs task)
  - `_cam_relevance()` — surprise score boost
  - `_feedback_score()` — from feedback cortex (Layer 3, 0.5 default initially)
  - `_engram_preference()` — user tool_usage_patterns
  - `_stm_relevance()` — recent working memory items
  - `_phase_match()` — trigger_patterns vs phase_type
  - `_hope_lod_match()` — zoom level → tool granularity
  - `_mgc_heat()` — cache tier → file context relevance
- [ ] 172.P2.3 Add `ReflexContext.from_subtask()` factory — easy construction from pipeline data
- [ ] 172.P2.4 Add `ReflexContext.from_session()` factory — from vetka_session_init payload
- [ ] 172.P2.5 Configurable weights via env vars: `REFLEX_SEMANTIC_WEIGHT=0.30`, etc.
- [ ] 172.P2.6 Feature flag: `REFLEX_ENABLED=false` (off by default, opt-in)

### Tests (`tests/test_reflex_scorer.py`)
- [ ] T2.1 `test_score_returns_float_0_to_1` — bounds check
- [ ] T2.2 `test_recommend_returns_top_n` — correct count, sorted descending
- [ ] T2.3 `test_semantic_match_prefers_relevant_tools` — "search" task → search tools score higher
- [ ] T2.4 `test_phase_match_fix_vs_build` — fix phase → debug tools, build phase → write tools
- [ ] T2.5 `test_cam_surprise_boosts_novel_tools` — high surprise → broader tool set
- [ ] T2.6 `test_engram_preference_respected` — user prefers tool X → X scores higher
- [ ] T2.7 `test_feedback_score_affects_ranking` — tool with high feedback → higher rank
- [ ] T2.8 `test_score_without_feedback_uses_default` — 0.5 default when no history
- [ ] T2.9 `test_weights_configurable` — env var changes affect scores
- [ ] T2.10 `test_scorer_performance_under_5ms` — timing benchmark, no LLM calls
- [ ] T2.11 `test_from_subtask_factory` — ReflexContext created correctly from subtask
- [ ] T2.12 `test_feature_flag_disabled` — REFLEX_ENABLED=false → passthrough, no scoring

### Markers
- `MARKER_172.P2.SCORER` in `reflex_scorer.py`
- `MARKER_172.P2.CONTEXT` in ReflexContext definition

### Exit Criteria
Scorer runs in <5ms. All 12 tests pass. Feature flag works. No LLM calls in scoring path.

---

## Phase 172.P3 — FEEDBACK CORTEX (обучение)
**Effort:** 1 session | **Risk:** Low | **Assignee:** Dragon Silver

### Tasks
- [ ] 172.P3.1 Create `src/services/reflex_feedback.py`:
  - `ReflexFeedback.record(tool_id, result, context, agent_role)` → append to log
  - `ReflexFeedback.record_outcome(subtask_id, tools_used, verifier_passed)` → close feedback loop
  - `ReflexFeedback.get_score(tool_id, task_type)` → aggregated score (0.0-1.0)
  - `ReflexFeedback.get_stats()` → summary statistics
- [ ] 172.P3.2 Create `data/reflex/feedback_log.jsonl` — append-only JSONL
- [ ] 172.P3.3 Implement aggregation:
  - Per (tool_id, phase_type) pair
  - `score = success_rate * 0.40 + usefulness * 0.35 + verifier_pass * 0.25`
  - Decay: `weight *= exp(-0.1 * days_old)`
- [ ] 172.P3.4 Add periodic compaction (aggregate old entries, keep last 1000)
- [ ] 172.P3.5 Wire `result_useful` detection:
  - Coder: content changed after tool call
  - Verifier: found issue using tool results

### Tests (`tests/test_reflex_feedback.py`)
- [ ] T3.1 `test_record_appends_to_log` — JSONL grows by 1 line
- [ ] T3.2 `test_record_outcome_closes_loop` — verifier result linked to tool records
- [ ] T3.3 `test_get_score_aggregates_correctly` — formula matches spec
- [ ] T3.4 `test_decay_reduces_old_entries` — 30-day-old entries weighted less
- [ ] T3.5 `test_compaction_limits_log_size` — after 1000 entries, compact
- [ ] T3.6 `test_empty_log_returns_default` — 0.5 when no history
- [ ] T3.7 `test_stats_returns_summary` — tool counts, success rates

### Markers
- `MARKER_172.P3.FEEDBACK` in `reflex_feedback.py`
- `MARKER_172.P3.LOG` in feedback_log.jsonl creation

### Exit Criteria
Feedback logs correctly. Aggregation formula verified. Decay works. All T3.x pass.

---

## Phase 172.P4 — INJECTION (врезка в систему)
**Effort:** 1-2 sessions | **Risk:** Medium-High | **Assignee:** Opus

### Tasks
- [ ] 172.P4.1 **IP-1: FC Loop pre-execution** (`src/tools/fc_loop.py:493`):
  - Import reflex_scorer
  - Build ReflexContext from subtask + STM + CAM
  - Call `recommend()`, log recommendations
  - Optionally reorder/filter tool_schemas
- [ ] 172.P4.2 **IP-3: FC Loop post-execution** (`src/tools/fc_loop.py:550`):
  - After tool result, call `reflex_feedback.record()`
  - Record: tool_id, success, execution_time, context signals
- [ ] 172.P4.3 **IP-5: Verifier feedback** (`src/orchestration/agent_pipeline.py:954`):
  - After verification, call `reflex_feedback.record_outcome()`
  - Link tools_used to verifier_passed
- [ ] 172.P4.4 **IP-6: Session Init** (`src/mcp/tools/session_init_tool.py`):
  - Add `recommended_tools[]` to session_init response
  - Call `reflex_scorer.recommend_for_session()`
- [ ] 172.P4.5 **IP-4: Pipeline role recommendations** (`agent_pipeline.py`):
  - Before each role execution, query REFLEX
  - Store recommendations in subtask.context["reflex_tools"]
  - Log: which tools REFLEX recommended vs which LLM chose
- [ ] 172.P4.6 **Feature flag guard**: all injection points check `REFLEX_ENABLED`

### Tests (`tests/test_reflex_integration.py`)
- [ ] T4.1 `test_fc_loop_with_reflex_recommends_tools` — mock scorer, verify called
- [ ] T4.2 `test_fc_loop_records_feedback` — mock feedback, verify recorded after execution
- [ ] T4.3 `test_verifier_closes_feedback_loop` — outcome recorded with tools_used
- [ ] T4.4 `test_session_init_includes_recommendations` — recommended_tools in response
- [ ] T4.5 `test_reflex_disabled_no_side_effects` — feature flag off → zero calls to scorer
- [ ] T4.6 `test_full_pipeline_feedback_cycle` — task → score → execute → feedback → next task scored better
- [ ] T4.7 `test_regression_existing_pipeline_unchanged` — with reflex off, all existing tests pass

### Markers
- `MARKER_172.P4.IP1` in fc_loop.py
- `MARKER_172.P4.IP3` in fc_loop.py
- `MARKER_172.P4.IP5` in agent_pipeline.py
- `MARKER_172.P4.IP6` in session_init

### Exit Criteria
All 6 injection points wired. Feature flag works. Existing tests unbroken. Full feedback cycle verified.

---

## Phase 172.P5 — TELEMETRY & TUNING
**Effort:** 1 session | **Risk:** Low | **Assignee:** Codex / Dragon

### Tasks
- [ ] 172.P5.1 Add `GET /api/reflex/stats` endpoint — tool usage, success rates, top tools
- [ ] 172.P5.2 Add `GET /api/reflex/recommendations?task=...` — debug endpoint
- [ ] 172.P5.3 Add REFLEX section to pipeline_stats output
- [ ] 172.P5.4 Log REFLEX recommendations to DevPanel WebSocket (mycelium WS)
- [ ] 172.P5.5 Tune weights based on first 100 feedback entries
- [ ] 172.P5.6 Add observability markers per request: `reflex_on`, `tools_recommended`, `tools_used`

### Tests
- [ ] T5.1 `test_reflex_stats_endpoint` — returns valid JSON
- [ ] T5.2 `test_reflex_debug_recommendations` — returns scored tools
- [ ] T5.3 `test_pipeline_stats_includes_reflex` — reflex section in stats

### Exit Criteria
Stats API works. DevPanel shows recommendations. Observability markers present.

---

## Execution Order & Dependencies

```
172.P1 (Registry)  ──→  172.P2 (Scorer)  ──→  172.P4 (Injection)  ──→  172.P5 (Telemetry)
                              ↑
                    172.P3 (Feedback) ──────┘
```

P1 и P3 можно запускать параллельно. P2 зависит от P1. P4 зависит от P2 + P3. P5 после P4.

---

## Test Summary

| Phase | Tests | File |
|-------|-------|------|
| P1 | 7 tests | `tests/test_reflex_registry.py` |
| P2 | 12 tests | `tests/test_reflex_scorer.py` |
| P3 | 7 tests | `tests/test_reflex_feedback.py` |
| P4 | 7 tests | `tests/test_reflex_integration.py` |
| P5 | 3 tests | in `test_reflex_integration.py` |
| **Total** | **36 tests** | |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Over-recommendation noise | Confidence threshold (default 0.3), top-N limit |
| Performance regression | Scorer <5ms, no LLM calls, async feedback recording |
| Breaking existing pipeline | Feature flag `REFLEX_ENABLED=false` by default |
| Feedback cold start | Default score 0.5 when no history |
| Tool alias drift | Auto-generation script catches deleted/renamed tools |
| Circular imports | REFLEX is a standalone service, imports nothing from pipeline |

---

## Agent Assignments (proposed)

| Phase | Agent | Reason |
|-------|-------|--------|
| **172.P1** | Dragon Bronze | Mechanical: scan code, generate JSON |
| **172.P2** | Opus + Dragon Silver | Architecture: scoring formula, signal integration |
| **172.P3** | Dragon Silver | Straightforward: JSONL logging, aggregation |
| **172.P4** | **Opus** | Critical: injection into pipeline core, regression risk |
| **172.P5** | Codex / Dragon | Telemetry endpoints, observability |
