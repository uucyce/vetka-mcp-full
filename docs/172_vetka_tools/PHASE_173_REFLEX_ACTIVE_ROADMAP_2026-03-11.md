# Phase 173 — REFLEX Active: Tool Schema Filtering & Ecosystem Streaming

**Author:** Opus (Claude Code)
**Date:** 2026-03-11
**Depends on:** Phase 172 REFLEX (P1-P5 complete)
**Status:** ROADMAP (not started)

---

## Overview

Phase 172 built REFLEX as a **passive observer** — it recommends tools, records feedback,
and streams telemetry, but the model still receives ALL tool schemas every turn.

Phase 173 transforms REFLEX into an **active optimizer** that:
1. **Filters tool_schemas** before sending to LLM (fewer tokens, faster FC)
2. **Streams live** across ALL VETKA ecosystems (MCC, DevPanel, Chat, Jarvis)
3. **Learns from user corrections** (explicit "pin"/"ban" tool actions)
4. **Adapts per-model** (small models get fewer tools, large models get all)

---

## P1 — Active Tool Schema Filtering

**Goal:** Reduce tool_schemas sent to coder LLM based on REFLEX scores.

### P1.1 — Schema Filter Engine (`reflex_filter.py`)
```
Input:  all_tools: List[ToolSchema], context: ReflexContext, model_tier: str
Output: filtered_tools: List[ToolSchema]
```

Rules:
- **Gold models** (Qwen3-235b, GPT-5.2): No filtering, keep all tools
- **Silver models** (Qwen3-coder, Kimi K2.5): Top 15 by REFLEX score + always-include set
- **Bronze models** (Qwen3-coder-flash, Mimo): Top 8 by REFLEX score + always-include set
- **Always-include set:** `vetka_read_file`, `vetka_edit_file`, `vetka_search_semantic` (core ops)
- **User-pinned tools** always included regardless of score
- **User-banned tools** always excluded regardless of score

### P1.2 — Pipeline Injection (IP-7: Schema Filter)
New injection point in `_execute_subtask()` — filter tool_schemas BEFORE building FC message:

```python
# MARKER_173.P1.IP7: Active tool schema filtering
if REFLEX_ENABLED:
    from src.services.reflex_filter import filter_tool_schemas
    tool_schemas = filter_tool_schemas(tool_schemas, reflex_context, model_tier)
```

### P1.3 — Fallback Safety
- If filtered set produces FC failure (no tool called) → retry with FULL set
- Track "filter_fallback" events → if > 30% fallback rate, auto-disable filtering for phase
- Log filtered-vs-full comparison for A/B analysis

### Tests: ~20
- Filter reduces schema count by model tier
- Always-include set preserved
- User pin/ban respected
- Fallback on empty FC result
- Gold model keeps all tools

---

## P2 — User Tool Preferences (Pin/Ban)

**Goal:** Let users explicitly control REFLEX recommendations.

### P2.1 — Preference Store (`reflex_preferences.py`)
```python
class ReflexPreferences:
    pinned_tools: Set[str]    # Always include
    banned_tools: Set[str]    # Always exclude
    custom_weights: Dict[str, float]  # User overrides per-tool
```
- Persisted in `data/reflex/user_preferences.json`
- Exposed via REST: `POST /api/reflex/pin`, `POST /api/reflex/ban`, `GET /api/reflex/preferences`

### P2.2 — Integration with Scorer
- Pinned tools get `score = max(1.0, score)` (always top)
- Banned tools get `score = -1.0` (always excluded)
- Custom weights blend with computed score: `final = 0.7 * computed + 0.3 * user_weight`

### Tests: ~15
- Pin/ban persistence
- Pin overrides low score
- Ban overrides high score
- REST endpoint CRUD

---

## P3 — Ecosystem-Wide Streaming

**Goal:** REFLEX events visible in ALL VETKA UI surfaces.

### P3.1 — WebSocket Event Schema
```json
{
  "event": "reflex:recommendation",
  "data": {
    "pipeline_id": "...",
    "subtask": "step_3",
    "phase": "fix",
    "recommended": [
      {"tool_id": "vetka_edit_file", "score": 0.92, "reason": "file editing task"},
      {"tool_id": "vetka_search_semantic", "score": 0.85, "reason": "bug context"}
    ],
    "filtered_count": 15,
    "total_count": 45,
    "model_tier": "silver"
  }
}
```

Event types:
- `reflex:recommendation` — before FC (what REFLEX suggests)
- `reflex:outcome` — after FC (what model chose vs recommended)
- `reflex:verifier` — after verifier (success/failure → score update)
- `reflex:filter` — schema filtering applied (how many tools removed)
- `reflex:fallback` — filter fallback triggered

### P3.2 — MCC Integration
- RailsActionBar shows live REFLEX match rate badge (green > 0.7, yellow > 0.4, red < 0.4)
- MiniStats adds "REFLEX Accuracy" card
- TaskDrillDown shows per-subtask REFLEX timeline

### P3.3 — DevPanel Integration
- New "REFLEX" tab in DevPanel sidebar
- Live stream of recommendation → outcome pairs
- Match rate graph (Recharts line chart, last 20 subtasks)
- Filter effectiveness: tokens saved per run

### P3.4 — Jarvis Voice Integration
- Jarvis can announce: "REFLEX recommends 5 tools for this fix task, accuracy 78%"
- Voice command: "Pin search tool" → adds to preferences
- Voice command: "Show REFLEX stats" → reads summary

### Tests: ~10
- WebSocket event format validation
- Event flow: recommendation → outcome → verifier
- MCC badge color thresholds

---

## P4 — A/B Testing Framework

**Goal:** Measure whether active filtering improves pipeline quality.

### P4.1 — Experiment Config
```json
{
  "experiment_id": "reflex_active_v1",
  "control": { "filtering": false, "description": "All tools, no filtering" },
  "treatment": { "filtering": true, "description": "REFLEX filtered schemas" },
  "split_ratio": 0.5,
  "metrics": ["success_rate", "tokens_used", "duration_ms", "match_rate"]
}
```

### P4.2 — Metrics Collection
Per-run comparison:
- **Token savings:** `(full_schema_tokens - filtered_schema_tokens) / full_schema_tokens`
- **Quality delta:** `treatment_success_rate - control_success_rate`
- **Speed delta:** `control_duration_ms - treatment_duration_ms`
- **Match rate:** Does filtering improve or degrade tool selection accuracy?

### P4.3 — Dashboard
- `/api/reflex/experiment` endpoint returns A/B results
- Analytics dashboard tab with Recharts comparison charts

### Tests: ~8
- Experiment assignment is stable per pipeline_id
- Metrics collected for both arms
- Split ratio approximately correct over N runs

---

## P5 — CORTEX Score Decay & Model-Specific Tuning

**Goal:** Make REFLEX scores evolve over time and adapt per model.

### P5.1 — Score Decay Refinement
Current: linear decay with `exp(-age_days / 30)`.
Enhanced:
- **Phase-specific half-life:** Research tools decay slower (45 days), fix tools faster (14 days)
- **Success-weighted decay:** High-success tools decay 2x slower
- **Seasonal patterns:** Tools used more at project start vs maintenance phase

### P5.2 — Model-Specific Scoring Profiles
```python
MODEL_PROFILES = {
    "qwen3-coder-flash": {"fc_reliability": 0.7, "max_tools": 8, "prefer_simple": True},
    "qwen3-coder": {"fc_reliability": 0.85, "max_tools": 15, "prefer_simple": False},
    "kimi-k2.5": {"fc_reliability": 0.95, "max_tools": 45, "prefer_simple": False},
}
```
- Small models prefer simpler tool schemas (shorter descriptions)
- FC reliability score adjusts filtering aggressiveness
- Profile auto-updates from verifier feedback data

### Tests: ~12
- Decay rates differ by phase
- Model profile applied correctly
- Auto-update from feedback

---

## P6 — Local Model Behavior Validation

**Goal:** Prove that local Ollama Qwen models do useful tool work with REFLEX, instead of only receiving passive recommendations.

### P6.1 — Direct local tool-use path
- Wire REFLEX recommendations into the direct `vetka_call_model` / `mycelium_call_model` Ollama path.
- Add `select_best_local_qwen_model` to the MCP function-calling allowlist.
- Keep the tool path non-recursive: no nested LLM call inside any helper tool.
- Prefer low-cost read-only helpers for local-model recall (`vetka_search_files`, `vetka_read_file`, `mycelium_task_board`, `select_best_local_qwen_model`).
- Implementation marker: `MARKER_173.P6.DIRECT_LOCAL_TOOL_PATH`

### P6.2 — Search/read behavior test
- Local Qwen receives a coding question about the repo.
- Expected behavior: it uses `vetka_search_files` or `vetka_search_semantic`, then `vetka_read_file`, then answers.
- Pass condition: tool usage is observable and final answer references fetched repo context.

### P6.3 — Task-board ownership test
- Seed a task assigned to local Qwen in task board.
- Expected behavior: model reads or claims the task via task-board tool, updates status, and uses task context instead of hallucinating a plan.
- Pass condition: task-board state changes are recorded and consistent with the run.

### P6.4 — Remembered coding workflow recall
- Seed `remember_reflex_tool` with a coding workflow hint for local-model tasks.
- Expected behavior: on a similar request, REFLEX raises the remembered tool path and the local model actually chooses the matching tool chain.
- Pass condition: remembered overlay changes ranking and the chosen tools match the remembered workflow.

### P6.5 — Read/edit/test chain
- Give local Qwen a small patch task.
- Expected behavior: read file → edit file → run tests or equivalent validation.
- Pass condition: no recursive LLM calls, tool chain is sensible, and target regression tests pass.

### P6.6 — MYCELIUM local patch preset
- Materialize the proven local-model patch loop as a dedicated MYCELIUM workflow preset/contract.
- Encode `expected_sequence`, direct tool surface, and REFLEX preflight rules in the contract instead of leaving them only in prose.
- Pass condition: the preset is discoverable through MCC workflow-contract/operator-method APIs and covered by template + contract tests.
- Implementation marker: `MARKER_173.P6.MYCELIUM_LOCAL_PATCH_PRESET`

### P6.7 — MYCELIUM ownership preset
- Materialize the controlled task-ownership flow as a dedicated MYCELIUM local preset with explicit task-board write opt-in.
- Keep the direct tool surface narrow (`mycelium_task_board`) and prove that the contract advertises task-board writes without opening edit/file writes.
- Pass condition: the preset is discoverable through MCC workflow-contract/operator-method APIs and covered by template + contract tests.
- Implementation marker: `MARKER_173.P6.MYCELIUM_LOCAL_OWNERSHIP_PRESET`

### Tests: ~12
- Local Qwen uses VETKA search/read tools for code context
- Local Qwen claims or updates its task-board task
- Local Qwen follows remembered REFLEX coding workflow
- Local Qwen completes read/edit/test tool chain
- No recursive tool path (`vetka_call_model` inside helper tool) is introduced
- Local-tool allowlist remains read-safe by default

### Marker
- `MARKER_173.P6.LOCAL_QWEN_VALIDATION`
- `MARKER_173.P6.DIRECT_LOCAL_TOOL_PATH`
- `MARKER_173.P6.LIVE_LOCAL_QWEN_BEHAVIOR`
- `MARKER_173.P6.MYCELIUM_LOCAL_PATCH_PRESET`
- `MARKER_173.P6.MYCELIUM_LOCAL_OWNERSHIP_PRESET`

---

## Summary

| Part | Name | Deliverables | Tests |
|------|------|-------------|-------|
| P1 | Active Schema Filtering | `reflex_filter.py`, IP-7, fallback | ~20 |
| P2 | User Preferences (Pin/Ban) | `reflex_preferences.py`, REST API | ~15 |
| P3 | Ecosystem Streaming | WS events, MCC/DevPanel/Jarvis UI | ~10 |
| P4 | A/B Testing Framework | Experiment config, metrics, dashboard | ~8 |
| P5 | Score Decay & Model Tuning | Enhanced decay, model profiles | ~12 |
| P6 | Local Model Behavior Validation | direct Ollama path, live tests, MYCELIUM patch + ownership presets | ~12 |
| **Total** | | | **~73** |

### Execution Order
```
P1 (Schema Filter) → P2 (User Prefs) → P3 (Streaming) → P4 (A/B) → P5 (Tuning)
                                                     ↘
                                                       P6 (Local model validation)
```

P1 is the core — everything else builds on it.
P3 can start in parallel with P2 since streaming doesn't depend on preferences.
P4 and P5 are polish/optimization — can defer to Phase 174 if needed.
P6 starts after the direct Ollama path can see REFLEX recommendations and safe tool allowlists.

### Risk Assessment
- **P1 is safest** — worst case, fallback to full schemas (current behavior)
- **P3 is most work** — touches MCC, DevPanel, Jarvis (3 UI surfaces)
- **P4 is optional** — nice to have but not critical for launch
- **P6 is mandatory before trusting local-model recall** — recommendations alone are not enough; behavior must be observed
- **Feature flag:** `REFLEX_ACTIVE=1` (default: False) — active filtering OFF until validated

---

*MARKER_173.ROADMAP — Phase 173: REFLEX Active*
