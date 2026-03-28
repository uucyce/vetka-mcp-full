# RECON: MCC Integration Status — Audit 2026-03-26

**Author:** Delta (opencode)
**Scope:** All MCC/localguys/model-integration pending tasks
**Method:** Source code verification + test execution + git log analysis

---

## Executive Summary

Audited 7 MCC-related pending tasks. Found **2 already implemented** (closed), **1 partially done**, **4 need real work**.

| # | Task | Verdict | Action |
|---|------|---------|--------|
| 1 | tb_1773376273_1 — Runtime guard enforcement | ✅ DONE | CLOSED |
| 2 | tb_1773698671_10 — BG-004 artifact contract | ✅ DONE | CLOSED |
| 3 | tb_1773703998_16 — A1.2 get_profile_sync | ❌ NOT DONE | Needs impl |
| 4 | tb_1773702691_14 — MODEL_POLICY_MATRIX sync | ⚠️ PARTIAL | Needs auto-gen |
| 5 | tb_1774424683_1 — Cross-role ENGRAM search | ❌ NOT DONE | Needs impl |
| 6 | tb_1773375069_2 — MCP-only TB writes | ❌ NOT DONE | Needs impl |
| 7 | tb_1774424860_1 — QA Fleet orchestrator | ❌ NOT DONE | Needs impl |

---

## Detailed Findings

### 1. Runtime Guard Enforcement — ALREADY DONE ✅

**Task:** `tb_1773376273_1` — Enforce MCC localguys runtime guard at run-update boundary

**What exists:**
- `_prepare_localguys_runtime_metadata()` validates used_tools, write_attempts, turn_budget at PATCH boundary (`mcc_routes.py:3056-3100`)
- `_build_localguys_runtime_guard()` exposes guard state in all responses (`mcc_routes.py:3027-3053`)
- All 14 tests pass (`test_mcc_localguys_run_contract.py`)

**Why it failed 6 times:** quickfix_localguys tier agents saw existing code, produced empty diff, got rejected.

---

### 2. Artifact Contract (BG-004) — ALREADY DONE ✅

**Task:** `tb_1773698671_10` — Implement artifact contract for localguys runs

**What exists:**
- `artifact_contract` in workflow contract response (`mcc_routes.py:891`)
- PUT artifact endpoint (`mcc_routes.py:3263-3289`)
- Required-artifact validation on done transition (`mcc_routes.py:3241-3253`)
- Registry: `write_artifact()`, `validate_required_artifacts()`, `_refresh_manifest()`
- 12+ test assertions pass

**Why stale:** Feature was built into larger localguys pass without dedicated commit. Doc `LOCALGUYS_IMPLEMENTATION_BACKLOG.md` never updated.

---

### 3. A1.2: get_profile_sync — NOT DONE ❌

**Task:** `tb_1773703998_16` — Add get_profile_sync to LLMModelRegistry

**Current state:**
- `LLMModelRegistry.get_profile()` exists but is `async` only (`llm_model_registry.py:476`)
- `model_policy.py:101-121` uses hacky `asyncio.run` + `ThreadPoolExecutor` workaround
- Zero `.py` files contain `get_profile_sync`

**What to do:**
- Add `get_profile_sync(model_id)` method to `LLMModelRegistry` that does sync dict lookup on `self._profiles` (already sync data) + falls back to `_get_safe_default()`
- Replace `asyncio.run` workaround in `model_policy.py`

**Files:**
- `src/elisya/llm_model_registry.py` — add method
- `src/services/model_policy.py` — replace workaround

---

### 4. MODEL_POLICY_MATRIX Sync — PARTIAL ⚠️

**Task:** `tb_1773702691_14` — Sync MODEL_POLICY_MATRIX.md with reflex_decay.py

**Current state:**
- `MODEL_POLICY_MATRIX.md` marked DEPRECATED, points to `model_policy.py`
- `model_policy.py` exists as unified source of truth (merges reflex_decay + LLMModelRegistry)
- `reflex_decay.py` has 24 models with fc_reliability, max_tools, prefer_simple
- Drift recon doc exists: `RECON_MODEL_POLICY_MATRIX_DRIFT.md`

**What's missing:**
- No auto-gen script to regenerate human-readable doc from code
- 10 drift items still undocumented in human-readable form: max_tools per model, prefer_simple flags, PHASE_HALF_LIFE (45/14/30 days), DecayConfig thresholds

**Recommended:** Close as "strategically resolved" (code is source of truth). Optional follow-up: auto-gen script.

---

### 5. Cross-role ENGRAM Search — NOT DONE ❌

**Task:** `tb_1774424683_1` — 198.P2.9: Delta's bug report about Alpha's code should reach Alpha at session_init

**Current state:**
- ENGRAM keys already encode agent callsign: `Delta::debrief::bug::*`
- session_init loads ALL entries by category (no role filter)
- No wildcard key search method in engram_cache.py
- No `cross_role_warnings` field in session context

**What to do:**
- Add `search_by_key_pattern()` to `engram_cache.py`
- In `session_tools.py` (~line 500), after existing ENGRAM block, add cross-role search: `*::debrief::bug::*` filtered by current role's `owned_paths`
- Inject as `cross_role_warnings[]` in session context

**Files:**
- `src/memory/engram_cache.py` — add wildcard search
- `src/mcp/tools/session_tools.py` — add cross-role injection

---

### 6. MCP-only TaskBoard Writes — NOT DONE ❌

**Task:** `tb_1773375069_2` — Enforce MCP-only writes + surface agent ownership in MCC

**Current state:**
- REST API debug endpoints (`debug_routes.py`) expose unguarded write access
- `sanitize_tool_schemas()` in `llm_call_reflex.py` restricts MCP tool-call path only
- `ownership_scope` / `owner_agent` fields exist in task schema but mostly empty
- `validate_file_ownership()` exists in `agent_registry.py:185`

**What to do:**
- Add `Depends()` guard or middleware on debug_routes.py write endpoints
- Populate `owner_agent` consistently from task claims
- Surface ownership info in MCC run responses

---

### 7. QA Fleet Orchestrator — NOT DONE ❌

**Task:** `tb_1774424860_1` — Auto-audit done_worktree tasks with parallel Sonnet agents

**Current state:**
- QA gate workflow exists: `done_worktree → verify → verified/needs_fix`
- Manual: Commander dispatches Delta agent for QA review
- `ScoutAuditor` exists but for Mycelium artifacts, not TaskBoard QA
- No automated scan of done_worktree tasks

**What to do:**
- Build auto-scanner that periodically checks `done_worktree` queue
- Dispatch parallel Sonnet agents for automated review
- Feed results back through QA gate (verify/needs_fix)

---

## Ollama Qwen 3.5 — 24/7 Free Assistant

**Status:** qwen3.5:latest is INSTALLED (6.6 GB) and Ollama is RUNNING on localhost:11434

**Current config in reflex_decay.py:**
```python
"qwen3.5:latest": ModelProfile(
    model_name="qwen3.5:latest",
    fc_reliability=0.86,  # decent
    max_tools=10,         # moderate tool budget
    prefer_simple=True,   # prefers simpler prompts
)
```

**Integration path (already exists):**
- `vetka_call_model` MCP tool supports `model: "qwen3.5:latest"` with `model_source: "ollama"`
- Dragon team presets already use local Ollama models (qwen3:8b, deepseek-r1:8b, etc.)
- Heartbeat system + Mycelium pipeline can run 24/7 via local models

**For 24/7 operation:**
1. Use heartbeat + localguys with `workflow_family: "quickfix_localguys"` or `"research_localguys"`
2. Set model policy to prefer `qwen3.5:latest` (fc_reliability=0.86, 10 tools)
3. Ollama runs locally — no API costs, no rate limits
4. Guard via MCC runtime guard (already implemented)

**Limitation:** qwen3.5 has `prefer_simple=True` — best for straightforward tasks. For complex multi-file work, Silver/Gold tiers with Kimi/Qwen-coder still recommended.

---

## Recommended Priority

1. **Quick wins (close stale tasks):** MODEL_POLICY_MATRIX sync → close as resolved
2. **Real work (high value):** A1.2 get_profile_sync, Cross-role ENGRAM
3. **Architecture (medium):** MCP-only TB writes, QA Fleet orchestrator
