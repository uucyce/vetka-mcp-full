# call_model Consolidation Plan

**Date:** 2026-01-31
**Phase:** 103
**Status:** Analysis Complete - Implementation Pending

---

## Executive Summary

VETKA has **3 distinct `call_model` implementations** with overlapping responsibilities:

1. **`api_aggregator_v3.call_model()`** - Legacy Ollama/OpenRouter adapter (547 lines)
2. **`routes.call_model()` (OpenCode Bridge)** - REST API wrapper (18 lines)
3. **`model_client.call_model()`** - Socket.IO streaming client (446 lines)

**Recommendation:** Consolidate to **`provider_registry.call_model_v2()`** as the canonical implementation.

---

## Current State

### 1. `src/elisya/api_aggregator_v3.py::call_model()`

**Location:** Lines 237-434
**Signature:**
```python
async def call_model(
    prompt: str,
    model_name: str = None,
    system_prompt: str = "You are a helpful assistant.",
    tools: Optional[List[Dict]] = None,
    **kwargs,
) -> Any
```

**Responsibilities:**
- Ollama local model calls (via `ollama.chat()`)
- OpenRouter API calls (via `call_openrouter()`)
- Direct API calls (OpenAI/Anthropic/Google via `direct_api_calls`)
- Tool calling support (Phase 27.15)
- Model validation and fallback logic
- Timing and health checks (Phase 32.4)

**Called By:**
- `src/orchestration/orchestrator_with_elisya.py` (imported as `call_model_legacy`)
- `src/api/handlers/streaming_handler.py` (imports `call_model_stream` sibling)
- Legacy code paths (being phased out)

**Status:** 🟡 **ACTIVE (Legacy)** - Still in use but marked for deprecation

**Features:**
- ✅ Async execution
- ✅ Tool calling
- ✅ Streaming support (via `call_model_stream()`)
- ✅ Ollama health checks
- ✅ Model mapping (OpenRouter → Ollama)
- ❌ No provider enum support
- ❌ No API key rotation
- ❌ No explicit provider selection

---

### 2. `src/opencode_bridge/routes.py::call_model()`

**Location:** Lines 395-412
**Signature:**
```python
@router.post("/model/call")
async def call_model(request: Dict[str, Any]):
```

**Responsibilities:**
- FastAPI REST endpoint wrapper
- Delegates to `SharedCallModelTool`
- Input validation
- Error handling

**Called By:**
- External IDE integrations (VS Code, OpenCode Desktop)
- MCP bridge (indirect via REST API)
- Testing scripts

**Status:** 🟢 **ACTIVE (Production)** - Part of Phase 95.6 Bridge Unification

**Features:**
- ✅ REST API interface
- ✅ Schema validation
- ✅ Tool wrapping pattern
- ✅ Error handling
- ❌ Thin wrapper - no actual LLM logic

---

### 3. `src/api/handlers/models/model_client.py::ModelClient.call_model()`

**Location:** Lines 52-109
**Signature:**
```python
async def call_model(
    self,
    model_name: str,
    prompt: str,
    session_id: str,
    node_id: str,
    node_path: str,
    streaming: bool = True,
    max_tokens: int = 999999,
    temperature: float = 0.7,
) -> Dict[str, Any]
```

**Responsibilities:**
- Socket.IO streaming integration
- Ollama local calls (lines 111-208)
- OpenRouter remote calls (lines 209-445)
- API key rotation (Phase 93)
- Stream start/end events
- Token tracking
- Error recovery

**Called By:**
- `src/api/handlers/mention/mention_handler.py` (via DI container)
- `src/api/handlers/user_message_handler.py` (extracted from there)
- Real-time chat handlers

**Status:** 🟢 **ACTIVE (Production)** - Core Socket.IO integration

**Features:**
- ✅ Socket.IO streaming
- ✅ API key rotation
- ✅ Rate limit handling (429 errors)
- ✅ Ollama + OpenRouter support
- ✅ Token usage tracking
- ❌ No tool calling support
- ❌ No direct API provider support (OpenAI/Anthropic/Google)

---

## Canonical Location (Recommendation)

### **Primary:** `src/elisya/provider_registry.py::call_model_v2()`

**Location:** Lines 1053-1189
**Signature:**
```python
async def call_model_v2(
    messages: List[Dict[str, str]],
    model: str,
    provider: Optional[Provider] = None,
    tools: Optional[List[Dict]] = None,
    **kwargs,
) -> Dict[str, Any]
```

**Why This is Canonical:**

1. ✅ **First-class provider support** - Explicit `Provider` enum parameter
2. ✅ **Auto-detect fallback** - If provider not specified, detects from model name
3. ✅ **Tool validation** - Checks `provider_instance.supports_tools`
4. ✅ **Intelligent fallbacks** - XAI → OpenRouter, API key errors → OpenRouter
5. ✅ **Model status tracking** - Updates success/failure states (Phase 93.11)
6. ✅ **HTTP error handling** - 401/402/403/404/429 with automatic fallbacks
7. ✅ **Provider registry pattern** - Unified interface for all providers
8. ✅ **Already used widely** - MCP tools, orchestrator, bridges

**Currently Used By:**
- `src/mcp/tools/llm_call_tool.py::LLMCallTool.execute()` (line 592)
- `src/opencode_bridge/open_router_bridge.py` (line 20)
- `src/orchestration/orchestrator_with_elisya.py` (migrated in Phase 93)
- MCP Bridge tools (vetka_call_model)

**Providers Supported:**
```python
class Provider(Enum):
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    XAI = "xai"
    OLLAMA = "ollama"
```

---

## Migration Plan

### Phase 1: Adapter Layer (SAFE - No Breaking Changes)

**Goal:** Create adapters that wrap `call_model_v2()` with old signatures.

**Tasks:**

1. **Create `api_aggregator_v3` adapter:**
   ```python
   # src/elisya/api_aggregator_v3.py

   async def call_model(
       prompt: str,
       model_name: str = None,
       system_prompt: str = "You are a helpful assistant.",
       tools: Optional[List[Dict]] = None,
       **kwargs,
   ) -> Any:
       """
       DEPRECATED: Use provider_registry.call_model_v2() directly.
       This is a compatibility adapter.
       """
       from src.elisya.provider_registry import call_model_v2

       # Convert prompt to messages format
       messages = [
           {"role": "system", "content": system_prompt},
           {"role": "user", "content": prompt}
       ]

       # Auto-detect provider (call_model_v2 will handle this)
       result = await call_model_v2(messages, model_name, tools=tools, **kwargs)

       # Convert response to legacy format
       return result
   ```

2. **Create `model_client` adapter:**
   ```python
   # src/api/handlers/models/model_client.py

   async def call_model(self, model_name: str, prompt: str, ...) -> Dict[str, Any]:
       """DEPRECATED: Adapter wrapping call_model_v2 with Socket.IO streaming."""
       from src.elisya.provider_registry import call_model_v2

       # Build messages
       messages = [{"role": "user", "content": prompt}]

       # Emit stream_start event
       await self.sio.emit("stream_start", {...}, to=session_id)

       # Call canonical implementation
       result = await call_model_v2(messages, model_name, **kwargs)

       # Emit stream_end event
       await self.sio.emit("stream_end", {...}, to=session_id)

       return result
   ```

3. **Update `routes.py` (already correct):**
   - Routes → `SharedCallModelTool` → `LLMCallTool` → `call_model_v2()` ✅
   - No changes needed, already using canonical path

**Duration:** 1-2 hours
**Risk:** 🟢 **LOW** - Backward compatible, no API changes

---

### Phase 2: Documentation & Deprecation Warnings

**Goal:** Alert developers to use canonical implementation.

**Tasks:**

1. Add deprecation warnings:
   ```python
   import warnings

   warnings.warn(
       "api_aggregator_v3.call_model() is deprecated. "
       "Use provider_registry.call_model_v2() instead.",
       DeprecationWarning,
       stacklevel=2
   )
   ```

2. Update docstrings with migration guide

3. Create `docs/103_ph/CALL_MODEL_MIGRATION_GUIDE.md`

4. Add code comments with `@deprecated` markers

**Duration:** 30 minutes
**Risk:** 🟢 **NONE** - Documentation only

---

### Phase 3: Migrate Callers (Breaking Changes)

**Goal:** Update all call sites to use `call_model_v2()` directly.

**Tasks:**

1. **Update `orchestrator_with_elisya.py`:**
   ```python
   # OLD:
   from src.elisya.api_aggregator_v3 import call_model as call_model_legacy

   # NEW:
   from src.elisya.provider_registry import call_model_v2
   ```

2. **Update `streaming_handler.py`:**
   - Migrate from `call_model_stream()` to `call_model_v2_stream()`

3. **Update `model_client.py` callers:**
   - `mention_handler.py` - use `call_model_v2()` with custom Socket.IO wrapper
   - `user_message_handler.py` - already extracted, verify usage

4. **Grep for all `call_model(` usages:**
   ```bash
   grep -rn "call_model(" src/ --include="*.py" | grep -v "call_model_v2"
   ```

**Duration:** 2-3 hours
**Risk:** 🟡 **MEDIUM** - Requires testing all LLM call paths

---

### Phase 4: Remove Legacy Code

**Goal:** Delete deprecated implementations after migration complete.

**Tasks:**

1. Remove `api_aggregator_v3.call_model()` (lines 237-434)
2. Remove `model_client.py` internal implementations (keep as thin wrapper if Socket.IO events needed)
3. Update imports across codebase
4. Remove dead code markers (Phase 95.1 already started this)

**Duration:** 1 hour
**Risk:** 🟠 **HIGH** - Must verify no hidden dependencies

---

## Risk Assessment

### High Risk Areas

1. **Socket.IO Streaming:**
   - `model_client.py` has custom `stream_start`/`stream_end` events
   - Need to preserve this behavior in migration
   - **Mitigation:** Create `SocketIOModelClient` wrapper around `call_model_v2()`

2. **Ollama Direct Calls:**
   - `api_aggregator_v3.py` uses `ollama.chat()` directly
   - `call_model_v2()` routes through `OllamaProvider` class
   - **Mitigation:** Verify `OllamaProvider` has same feature parity

3. **OpenRouter Key Rotation:**
   - `model_client.py` has manual key rotation (lines 232-327)
   - `call_model_v2()` relies on `unified_key_manager`
   - **Mitigation:** Ensure `unified_key_manager` is initialized before calls

4. **Tool Calling:**
   - `api_aggregator_v3.py` maps OpenRouter models to Ollama for tool support (lines 292-307)
   - Need to verify this logic is preserved
   - **Mitigation:** Add tool support test cases

### Medium Risk Areas

1. **Legacy Import Paths:**
   - Many old files may still import deprecated functions
   - **Mitigation:** Use `@deprecated` decorator with runtime warnings

2. **Response Format Differences:**
   - `call_model()` returns dict/Pydantic objects
   - `call_model_v2()` returns standardized dict
   - **Mitigation:** Document response format changes

3. **Error Handling:**
   - Different implementations have different error messages
   - **Mitigation:** Maintain error message compatibility in adapters

### Low Risk Areas

1. **REST API Routes:**
   - Already use `SharedCallModelTool` → `call_model_v2()`
   - No changes needed ✅

2. **MCP Tools:**
   - Already use `call_model_v2()` directly
   - No changes needed ✅

---

## Testing Strategy

### Unit Tests

1. Test `call_model_v2()` with all providers:
   - `Provider.OPENAI`
   - `Provider.ANTHROPIC`
   - `Provider.GOOGLE`
   - `Provider.XAI`
   - `Provider.OLLAMA`
   - `Provider.OPENROUTER`

2. Test fallback logic:
   - XAI → OpenRouter (403 errors)
   - Direct API → OpenRouter (401/402/404 errors)
   - Model not found → default fallback

3. Test tool calling:
   - With Ollama (supports tools)
   - With OpenRouter (no tool support)
   - With OpenAI/Anthropic (supports tools)

### Integration Tests

1. Test Socket.IO streaming:
   - Verify `stream_start` event emitted
   - Verify `stream_token` events during streaming
   - Verify `stream_end` event with metadata

2. Test MCP bridge:
   - `vetka_call_model` tool execution
   - Context injection (Phase 55.2)
   - Error handling

3. Test REST API:
   - POST `/model/call` endpoint
   - OpenCode bridge integration

### Manual Testing

1. Test Ollama local models:
   - `qwen2.5:7b`
   - `deepseek-llm:7b`
   - `llama3.1:8b`

2. Test OpenRouter models:
   - `anthropic/claude-3-haiku`
   - `mistralai/mistral-7b`

3. Test direct API models:
   - `grok-4` (XAI)
   - `gpt-4o` (OpenAI)
   - `claude-opus-4-5` (Anthropic)
   - `gemini-2.0-flash` (Google)

---

## Success Criteria

- [ ] All 3 `call_model` implementations removed or converted to thin adapters
- [ ] No regressions in Socket.IO streaming
- [ ] No regressions in MCP tool calls
- [ ] No regressions in REST API calls
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Deprecation warnings in place
- [ ] Zero duplicate LLM call logic

---

## Timeline

| Phase | Duration | Blocking Dependencies |
|-------|----------|----------------------|
| Phase 1: Adapter Layer | 1-2 hours | None |
| Phase 2: Documentation | 30 minutes | Phase 1 complete |
| Phase 3: Migrate Callers | 2-3 hours | Phase 1 + 2 complete |
| Phase 4: Remove Legacy | 1 hour | Phase 3 complete + all tests passing |
| **Total** | **4.5-6.5 hours** | Sequential execution required |

---

## Rollback Plan

If migration causes issues:

1. **Revert Phase 4:** Restore deleted code from git
2. **Revert Phase 3:** Restore old imports
3. **Keep Phase 1 & 2:** Adapters remain as compatibility layer

Adapters ensure zero downtime - can run dual implementations during migration.

---

## Open Questions

1. **Q:** Should we preserve `call_model_stream()` separately?
   **A:** Yes, but migrate to `call_model_v2_stream()` (already exists in provider_registry)

2. **Q:** What about `api_aggregator_v3.APIAggregator` class?
   **A:** Deprecated - use `ProviderRegistry` instead (Phase 95.1 already started cleanup)

3. **Q:** Should adapters be permanent or temporary?
   **A:** Temporary (6 months deprecation period, remove in Phase 110+)

---

## Related Documents

- `docs/92_ph/HAIKU_2_KEY_ROUTING_AUDIT.md` - Provider registry audit
- `docs/93_ph/PHASE_93_GIT_COMMIT.md` - Migration to call_model_v2
- `docs/95_ph/PROVIDER_AUDIT_EXECUTIVE_SUMMARY.md` - Provider system consolidation
- `src/elisya/provider_registry.py` - Canonical implementation
- `src/api/handlers/models/model_client.py` - Socket.IO client (to be adapted)

---

**Report Generated:** 2026-01-31
**Author:** Haiku 1 (Audit Agent)
**Status:** Ready for Implementation
