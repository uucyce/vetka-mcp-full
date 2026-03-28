# ZETA-[RECON]: Ollama Qwen 3.5 → VETKA MCP Harness Integration
**Task:** `tb_1774515194_1`
**Phase:** 198.8 | **Author:** Zeta | **Date:** 2026-03-26
**Status:** RECON COMPLETE

---

## 1. Current State (R1 — Call Path)

Ollama 0.17.6 is installed locally. `qwen3.5:latest` (6.6 GB) is downloaded. The call chain is **already fully wired**:

```
MCP Client → vetka_call_model
  → LLMCallTool.execute()
    → _detect_provider()         (provider_registry.py:1518)
    → "qwen3.5:latest" → Provider.OLLAMA  (":" in name, no "/")
    → OllamaProvider.call()      (provider_registry.py:806)
      → ollama.chat(model="qwen3.5:latest", messages=..., stream=False)
        → http://localhost:11434/api/chat
```

**Key files in the chain:**

| Step | File | Lines | Role |
|------|------|-------|------|
| MCP dispatch | `src/mcp/vetka_mcp_bridge.py` | 630, 1386 | Tool registration + dispatch |
| Tool execute | `src/mcp/tools/llm_call_tool.py` | 97, 220, 710, 771 | Provider detection + routing |
| Provider registry | `src/elisya/provider_registry.py` | 730-894, 1444, 1556, 2031 | OllamaProvider class, detect_provider, call_model_v2, streaming |
| Model profiles | `src/elisya/llm_model_registry.py` | 152 | qwen3.5:latest profile (ctx=32k, tps=46) |
| Role mapping | `src/services/model_policy.py` | 78, 153 | role_fit=["coder","architect","researcher"] |
| LocalGuys matrix | `src/api/routes/mcc_routes.py` | 494-641 | _LOCALGUYS_MODEL_MATRIX entry |
| Fallback chain | `src/mcp/tools/llm_call_tool_async.py` | 42 | polza → openrouter → ollama (last resort) |

**Streaming alternative:** `_stream_ollama()` (provider_registry.py:2031) uses raw httpx POST to `http://127.0.0.1:11434/api/chat` with `stream=True`.

**Other ollama call sites (not via vetka_call_model):**
- `src/utils/embedding_service.py` — `ollama.embeddings()` for vector search
- `src/voice/jarvis_llm.py` — direct HTTP POST for voice assistant
- `src/api/handlers/jarvis_handler.py` — T9 predictions
- `src/agents/arc_solver_agent.py` — ARC puzzle solving

### R1 Verdict: ✅ FULLY INTEGRATED
Qwen 3.5 can be called today via `vetka_call_model(model="qwen3.5:latest")`. No code changes needed.

---

## 2. MCC Tier/Role Mapping (R2)

### 2.1 Model Registry

`llm_model_registry.py:152` — Qwen 3.5 is registered with:
- Context: 32,768 tokens (medium class)
- Output TPS: 46.0 (balanced latency class)
- Provider: ollama

### 2.2 Model Policy

`model_policy.py:153` — `_derive_role_fit()` maps:
```python
"qwen3.5:latest": ["coder", "architect", "researcher"]
```

### 2.3 LocalGuys Matrix

`mcc_routes.py:494` — `_LOCALGUYS_MODEL_MATRIX` includes qwen3.5:latest as:
- coder, architect, researcher roles
- Mapped to workflows: `g3_localguys`, `ralph_localguys`, `quickfix_localguys`

### 2.4 Gap: Phase 177 Deployment Plan

`PHASE_177_G3_LOCAL_DEPLOYMENT_PLAN.md` lists MVP default as:
- coder → `qwen3:8b` or `qwen2.5:7b`
- verifier → `deepseek-r1:8b`

**Qwen 3.5 is NOT mentioned** in the deployment plan, even though it's already in the code.
It should be promoted to **primary coder** for g3_localguys (higher TPS than qwen3:8b, same context).

### R2 Verdict: ✅ MAPPED, but deployment plan is STALE

---

## 3. REFLEX/CORTEX Compatibility (R3)

### 3.1 How REFLEX scores work

REFLEX scorer (`reflex_scorer.py`) uses 8 signals weighted by tool_id. When vetka_call_model invokes ollama:

- **Tool ID:** `vetka_call_model` — this IS scored by REFLEX
- **Feedback loop:** CORTEX (`reflex_feedback.py`) records `tool_id, success, useful` from post-call results
- **Scorer signals:** semantic, CAM, feedback, ENGRAM, STM, phase, HOPE, MGC — all tool-level, not model-level

**Problem:** REFLEX tracks **tool success**, not **model quality**. If `vetka_call_model` succeeds (HTTP 200), CORTEX records `success=True` regardless of whether Qwen 3.5 gave a good answer.

### 3.2 Guard/Protocol compatibility

| Guard Rule | Compatible? | Notes |
|------------|-------------|-------|
| session_init_first | ✅ | Ollama calls don't bypass session |
| taskboard_before_work | ✅ | Same as any tool call |
| task_before_code | ✅ | Same |
| recon_before_code | ✅ | Same |
| read_before_edit | N/A | Not a file operation |
| roadmap_before_tasks | N/A | Not task creation |

### 3.3 Gap: Model-Level Feedback

Current architecture has NO per-model quality tracking:
- No way to know "qwen3.5 gave bad answer 3x for architect role"
- No automatic model downgrading on repeated failures
- No REFLEX signal for "local model latency exceeded budget"

**Proposed enhancement:**
1. Extend CORTEX `record()` with optional `model_id` field
2. Add scorer signal: `model_success_rate` (decay-weighted per model+role combo)
3. Guard rule: if model fails ≥3 in same role → suggest fallback model

### R3 Verdict: ⚠️ WORKS but no model-level quality tracking

---

## 4. Architecture: "Local Assistant in Harness" (R4)

### 4.1 What exists today

| Component | Status | File |
|-----------|--------|------|
| Ollama API integration | ✅ Working | provider_registry.py |
| Model registry | ✅ qwen3.5 registered | llm_model_registry.py |
| Role mapping | ✅ coder/architect/researcher | model_policy.py |
| MCP tool dispatch | ✅ vetka_call_model | vetka_mcp_bridge.py |
| LocalGuys workflow | ✅ g3_localguys defined | mcc_routes.py |
| MCC pipeline | ✅ mycelium supports localguys | mycelium pipeline |
| Task board | ✅ Works with any agent | task_board.py |
| REFLEX scoring | ✅ Tool-level works | reflex_scorer.py |
| CORTEX feedback | ✅ Tool-level works | reflex_feedback.py |
| Protocol guard | ✅ All rules compatible | protocol_guard.py |

### 4.2 What's missing for "full local assistant experience"

| Gap | Priority | Effort | Description |
|-----|----------|--------|-------------|
| Deployment plan update | HIGH | Low | Phase 177 doc doesn't mention qwen3.5. Update MVP default. |
| Model-level CORTEX tracking | MEDIUM | Medium | Track per-model+role quality, auto-fallback on degradation |
| Local assistant CLI/MCP command | MEDIUM | Low | `@local <task>` heartbeat command that routes to qwen3.5 directly |
| Prompt optimization for qwen3.5 | MEDIUM | Medium | Qwen 3.5 may need different prompting than qwen3:8b — needs eval |
| Context window utilization | LOW | Low | 32k context available but pipeline prompts may not use it |
| Streaming integration | LOW | Low | _stream_ollama exists but MCP tool doesn't expose streaming to client |

### 4.3 Recommended Implementation Order

**Phase A — Immediate (no code changes):**
1. Update `PHASE_177_G3_LOCAL_DEPLOYMENT_PLAN.md` to include qwen3.5:latest as primary coder
2. Test `vetka_call_model(model="qwen3.5:latest")` end-to-end via MCP
3. Run g3_localguys workflow with qwen3.5 as coder on a real task

**Phase B — Short-term (1-2 sessions):**
4. Add model_id to CORTEX feedback recording
5. Add `@local <task>` heartbeat command routing to qwen3.5
6. Eval: qwen3.5 vs qwen3:8b on benchmark tasks (coder role)

**Phase C — Medium-term:**
7. Model-level scorer signal in REFLEX
8. Auto-fallback guard rule
9. Streaming support in MCP tool

---

## 5. Quick Start: Calling Qwen 3.5 Today

### Via MCP tool:
```
vetka_call_model(model="qwen3.5:latest", messages=[{"role":"user","content":"Hello"}])
```

### Via Python (direct):
```python
import ollama
response = ollama.chat(model="qwen3.5:latest", messages=[{"role": "user", "content": "Hello"}])
```

### Via pipeline (g3_localguys):
```
mycelium_pipeline(task="...", preset="g3_localguys")
```

---

## 6. References

- `docs/177_MCC_local/PHASE_177_G3_LOCAL_DEPLOYMENT_PLAN.md` — deployment plan (needs update)
- `docs/177_MCC_local/MODEL_POLICY_MATRIX.md` — deprecated, code is source of truth
- `docs/177_MCC_local/LOCALGUYS_IMPLEMENTATION_BACKLOG.md` — work packages
- `docs/177_MCC_local/MASTER_ROADMAP.md` — phase roadmap
- `src/elisya/provider_registry.py` — OllamaProvider + call_model_v2
- `src/services/model_policy.py` — role mapping
- `src/api/routes/mcc_routes.py` — LocalGuys matrix
