# Phase 111.10.3 - FULL AUDIT REPORT
**Date:** 2026-02-04
**Agents:** 4x Haiku Exploration Agents

---

## EXECUTIVE SUMMARY

| Area | Coverage | Status |
|------|----------|--------|
| API Layer (user_message_handler) | 100% | ✅ READY |
| Model Directory UI | 95% | ✅ READY |
| Reply Routing | 90% | ✅ FIXED in 111.10.2 |
| Group Chat Routing | 0% | ❌ NOT IMPLEMENTED |
| MCP/Pipeline Routing | 0% | ❌ NOT IMPLEMENTED |
| Agent Delegation | 0% | ❌ NOT IMPLEMENTED |

**Total model_source coverage: ~42%**

---

## AGENT 1: MODEL_SOURCE MARKERS AUDIT

### Files with Phase 111 markers:

| File | Status | Notes |
|------|--------|-------|
| `user_message_handler.py` | ✅ | source passed to detect_provider |
| `call_model_v2.py` | ✅ | source parameter implemented |
| `provider_registry.py` | ✅ | detect_provider with source |
| `ChatPanel.tsx` | ✅ | selectedModelSource state |
| `useSocket.ts` | ✅ | model_source in emit |
| `MessageBubble.tsx` | ✅ | source in onReply |
| `chat.ts` types | ✅ | model_source in metadata |

### Missing model_source:

| File | Function | Priority |
|------|----------|----------|
| `group_handler.py` | `handle_group_message()` | 🔴 HIGH |
| `MentionPopup.tsx` | model selection | 🟠 MEDIUM |
| `orchestrator_with_elisya.py` | line 1174 | 🔴 HIGH |

---

## AGENT 2: GROUP CHAT ROUTING AUDIT

### Finding: NO model_source in group chat

**File:** `src/api/handlers/group_handler.py`

```python
# Line ~180 - NO model_source extracted
requested_model = data.get("model") or role_config.model

# Line ~220 - NO source passed to detect_provider
provider = ProviderRegistry.detect_provider(requested_model)
# MISSING: source=model_source
```

**Impact:**
- When user sends message to group with specific model source
- Source is NOT extracted from request
- Source is NOT passed to detect_provider
- Fallback to name-based detection only
- Poe/Polza models route incorrectly

### Recommendation:
```python
# Add after line 180:
model_source = data.get("model_source")

# Fix line 220:
provider = ProviderRegistry.detect_provider(requested_model, source=model_source)
```

---

## AGENT 3: TAVILY/NANOGPT PROVIDER ANALYSIS

### Tavily
- **Status:** ✅ CORRECT (0 models)
- **Reason:** Search tool, not LLM provider
- **Files:** `perplexity_fetcher.py` uses tavily_search_v2
- **Action:** None needed

### NanoGPT
- **Status:** ⚠️ MISSING MODEL FETCHER
- **Problem:** No `nanogpt_fetcher.py` exists
- **Impact:** Models with source="nanogpt" won't appear in Model Directory
- **Action:** Create `src/elisya/fetchers/nanogpt_fetcher.py`

---

## AGENT 4: MYCELIUM/MCP AGENT ROUTING AUDIT

### Critical Finding: Pipeline loses model_source completely

**Flow Analysis:**
```
API Request (model_source=X)
  ↓
chat_routes.py ✅ (extracts source)
  ↓
user_message_handler.py ✅ (passes source)
  ↓
call_model_v2_stream ✅ (uses source)

MCP Pipeline Request
  ↓
vetka_mcp_bridge.py ❌ (NO source in schema)
  ↓
spawn_pipeline() ❌ (NO source param)
  ↓
AgentPipeline ❌ (NO source stored)
  ↓
LLMCallTool ❌ (NO source support)
  ↓
SOURCE LOST → name detection fallback
```

### Files Requiring Fix:

| File | Function | Line | Fix |
|------|----------|------|-----|
| `orchestrator_with_elisya.py` | `_run_agent_with_elisya_async` | 1174 | Add `source=source` |
| `agent_pipeline.py` | `spawn_pipeline()` | 1242 | Add `model_source` param |
| `agent_pipeline.py` | `_research()` | 1105 | Pass source to tool |
| `agent_pipeline.py` | `_execute_subtask()` | 1190 | Pass source to tool |
| `llm_call_tool.py` | Tool schema | - | Add `model_source` field |
| `vetka_mcp_bridge.py` | `vetka_spawn_pipeline` | 1635 | Add `model_source` to schema |
| `base_agent.py` | `call_llm()` | 87-200 | Add source support |

---

## PHASE 111.11 RECOMMENDATIONS

### Priority 1 (CRITICAL):
1. Fix `orchestrator_with_elisya.py:1174` - missing source in 2nd call
2. Add model_source to `LLMCallTool` schema and execute
3. Fix `group_handler.py` - extract and pass model_source

### Priority 2 (HIGH):
4. Add model_source to `spawn_pipeline()` signature
5. Propagate source through AgentPipeline methods
6. Update MCP tool `vetka_spawn_pipeline` schema

### Priority 3 (MEDIUM):
7. Create `nanogpt_fetcher.py` for Model Directory
8. Add source to `base_agent.py` call_llm()
9. Update MentionPopup for source selection

---

## VERIFICATION CHECKLIST

After Phase 111.11 implementation:

- [ ] Model Directory → Poe model → message routes to Poe
- [ ] Reply on Poe message → routes to Poe
- [ ] Group chat with Poe model → routes to Poe
- [ ] Pipeline spawned with source → all sub-calls use correct source
- [ ] MCP tool call_model with source → correct routing
- [ ] NanoGPT models appear in Model Directory

---

## FILES MODIFIED IN PHASE 111.10.2

- `client/src/components/chat/ChatPanel.tsx` - ReplyTarget.source
- `client/src/components/chat/MessageBubble.tsx` - onReply source
- `client/src/hooks/useSocket.ts` - metadata.model_source
- `client/src/types/chat.ts` - metadata.model_source type
- `src/api/handlers/user_message_handler.py` - DEBUG logs, stream_start
- `src/elisya/provider_registry.py` - direct provider routing
- `src/mcp/tools/doctor_tool.py` - Polza URL fix

---

*Report generated by Haiku Exploration Agents*
*Phase 111.10.3 Audit Complete*
