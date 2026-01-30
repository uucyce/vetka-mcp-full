# OpenCode Bridge Endpoints Audit
## Phase 95.2 - Endpoints Inventory & MCP Gap Analysis

---

## Summary
- **Total Endpoints:** 4
- **Prefix:** /api/bridge/
- **Status:** Local-only, no authentication
- **Provider:** OpenRouter (via VETKA bridge)
- **Environment Flag:** `OPENCODE_BRIDGE_ENABLED`

---

## Endpoints Inventory

### [OC-EP-001] GET /openrouter/keys
- **Location:** `src/opencode_bridge/routes.py:17-33`
- **Lines:** 17-33 (17 lines)
- **HTTP Method:** GET
- **Function:** `get_openrouter_keys()`
- **Status Code:** 200/503
- **Description:** Get available OpenRouter API keys (masked) for UI selection
- **Request Schema:**
  - No request body
  - Query parameters: None
- **Response Schema:**
  ```json
  {
    "enabled": boolean,
    "provider": "openrouter",
    "keys": [
      {
        "id": "openrouter_0",
        "masked_key": "sk-...",
        "status": "active",
        "provider": "openrouter",
        "alias": "key_0"
      }
    ],
    "total": integer,
    "message": "string (if disabled)",
    "error": "string (if error)"
  }
  ```
- **Service Called:** `OpenRouterBridge.get_available_keys()`
- **Error Handling:** Wrapped in try-catch, returns error dict
- **Enable Condition:** `OPENCODE_BRIDGE_ENABLED == "true"`

---

### [OC-EP-002] POST /openrouter/invoke
- **Location:** `src/opencode_bridge/routes.py:36-61`
- **Lines:** 36-61 (26 lines)
- **HTTP Method:** POST
- **Function:** `invoke_openrouter(request: Dict[str, Any])`
- **Status Code:** 200/503
- **Description:** Invoke OpenRouter model through bridge with automatic key rotation
- **Request Schema:**
  ```json
  {
    "model_id": "string (required, e.g., 'xai/grok-4')",
    "messages": [
      {
        "role": "user|assistant|system",
        "content": "string"
      }
    ],
    "temperature": number (optional, default: 0.7),
    "tools": array (optional),
    "...other_kwargs": "passed through to API"
  }
  ```
- **Response Schema:**
  ```json
  {
    "success": boolean,
    "message": {
      "content": "string",
      "role": "assistant"
    },
    "model": "string",
    "provider": "openrouter",
    "usage": {
      "prompt_tokens": integer,
      "completion_tokens": integer
    },
    "error": "string (if error)"
  }
  ```
- **Service Called:** `OpenRouterBridge.invoke()` → `call_model_v2()`
- **Key Filtering Logic:** Lines 52-56
  - Extracts allowed kwargs excluding `model_id`, `messages`, `request`
  - Passes filtered kwargs to bridge
- **Error Handling:** Wrapped in try-catch, returns success=false dict
- **Enable Condition:** `OPENCODE_BRIDGE_ENABLED == "true"`
- **Critical Note:** `max_tokens` parameter removed (unlimited responses)

---

### [OC-EP-003] GET /openrouter/stats
- **Location:** `src/opencode_bridge/routes.py:64-86`
- **Lines:** 64-86 (23 lines)
- **HTTP Method:** GET
- **Function:** `get_openrouter_stats()`
- **Status Code:** 200/503
- **Description:** Get key rotation statistics for UI monitoring
- **Request Schema:**
  - No request body
  - Query parameters: None
- **Response Schema:**
  ```json
  {
    "enabled": boolean,
    "provider": "openrouter",
    "stats": {
      "total_keys": integer,
      "active_keys": integer,
      "rate_limited_keys": integer,
      "current_key_index": integer,
      "last_rotation": "ISO8601 datetime|null"
    },
    "error": "string (if error)"
  }
  ```
- **Service Called:** `OpenRouterBridge.get_stats()` → `BridgeStats` dataclass
- **Statistics Logic:**
  - Lines 102-106: Counts active vs rate-limited keys
  - Lines 108-109: Retrieves current key index and last rotation time
- **Error Handling:** Wrapped in try-catch, returns error dict
- **Enable Condition:** `OPENCODE_BRIDGE_ENABLED == "true"`

---

### [OC-EP-004] GET /openrouter/health
- **Location:** `src/opencode_bridge/routes.py:89-96`
- **Lines:** 89-96 (8 lines)
- **HTTP Method:** GET
- **Function:** `health_check()`
- **Status Code:** 200
- **Description:** Health check endpoint for monitoring bridge status
- **Request Schema:**
  - No request body
  - Query parameters: None
- **Response Schema:**
  ```json
  {
    "status": "healthy",
    "bridge_enabled": boolean,
    "provider": "openrouter"
  }
  ```
- **Service Called:** None (direct response)
- **Behavior:** No dependency checks, always returns status=healthy
- **Enable Condition:** None (always responds)
- **Use Case:** Docker health checks, load balancer probes

---

## Backend Services & Integration Points

### OpenRouterBridge Class
- **Location:** `src/opencode_bridge/open_router_bridge.py:31-126`
- **Initialization:** Lines 34-38
  - Loads ProviderType.OPENROUTER keys via unified_key_manager
  - Initializes APIKeyService
  - Caches active keys in `self.keys` list
- **Key Methods:**
  - `get_available_keys()` (Lines 51-65): Masks keys, returns list with metadata
  - `invoke()` (Lines 67-95): Async call to `call_model_v2()`, handles errors
  - `get_stats()` (Lines 97-111): Returns BridgeStats with rotation metrics
  - `_get_current_key_index()` (Lines 113-118): Returns first available key index
  - `_get_last_rotation_time()` (Lines 120-125): Returns last used key's timestamp

### MultiModelOrchestrator Class
- **Location:** `src/opencode_bridge/multi_model_orchestrator.py:11-148`
- **Purpose:** Orchestrates multi-model workflows via bridge
- **Key Methods:**
  - `orchestrate()` (Lines 18-39): Command router
    - Handles Russian commands: "Оркестрируй:", "Позвони", "Сделай цепочку:"
  - `_handle_orchestration()` (Lines 41-71): Sequential model chain
  - `_handle_single_call()` (Lines 73-88): Single model invocation
  - `_handle_chain()` (Lines 90-107): Workflow chain execution
  - `_map_model_name()` (Lines 109-123): Friendly name to model ID mapping
  - `call_bridge_model()` (Lines 125-140): Async wrapper around bridge.invoke()

### Dependencies
- **unified_key_manager.py:** Key management & rotation logic
- **provider_registry.py:** Provider enum and call_model_v2() function
- **api_key_service.py:** APIKeyService class for key operations

---

## Gap Analysis: MCP Tools vs OpenCode Bridge Endpoints

| # | MCP Tool | Equivalent OpenCode Endpoint | Status | Priority | Notes |
|---|----------|------------------------------|--------|----------|-------|
| 1 | `vetka_search_semantic` | ❌ MISSING | NOT FOUND | HIGH | Required for semantic search integration |
| 2 | `vetka_read_file` | ❌ MISSING | NOT FOUND | HIGH | No file read capability in bridge |
| 3 | `vetka_edit_file` | ❌ MISSING | NOT FOUND | HIGH | No file edit capability in bridge |
| 4 | `vetka_list_files` | ❌ MISSING | NOT FOUND | MEDIUM | No file system listing endpoint |
| 5 | `vetka_get_tree` | ❌ MISSING | NOT FOUND | MEDIUM | No project tree endpoint |
| 6 | `vetka_get_memory_summary` | ❌ MISSING | NOT FOUND | MEDIUM | No memory/context endpoint |
| 7 | `vetka_get_conversation_context` | ❌ MISSING | NOT FOUND | MEDIUM | No conversation history endpoint |
| 8 | `vetka_get_user_preferences` | ❌ MISSING | NOT FOUND | LOW | No user preferences endpoint |
| 9 | `Model invocation` | ✅ `/openrouter/invoke` | IMPLEMENTED | HIGH | Single provider, OpenRouter only |
| 10 | `Key management` | ✅ `/openrouter/keys` | IMPLEMENTED | HIGH | Read-only key listing |
| 11 | `Stats/Monitoring` | ✅ `/openrouter/stats` | IMPLEMENTED | MEDIUM | Key rotation metrics |
| 12 | `Health monitoring` | ✅ `/openrouter/health` | IMPLEMENTED | LOW | Basic health check |

### Gap Summary
- **High-Priority Gaps:** 3 (search, file operations)
- **Medium-Priority Gaps:** 3 (file system, context, memory)
- **Implemented:** 4 (all OpenRouter-specific)
- **Coverage:** 57% (4/7 essential features)

---

## Endpoint Markers Summary Table

| Marker | Endpoint Path | HTTP Method | Lines | Function | Service |
|--------|---------------|-------------|-------|----------|---------|
| OC-EP-001 | `/openrouter/keys` | GET | 17-33 | `get_openrouter_keys()` | `OpenRouterBridge.get_available_keys()` |
| OC-EP-002 | `/openrouter/invoke` | POST | 36-61 | `invoke_openrouter()` | `OpenRouterBridge.invoke()` |
| OC-EP-003 | `/openrouter/stats` | GET | 64-86 | `get_openrouter_stats()` | `OpenRouterBridge.get_stats()` |
| OC-EP-004 | `/openrouter/health` | GET | 89-96 | `health_check()` | Direct response |

---

## Request/Response Patterns

### Pattern 1: Disabled Bridge Response (All Endpoints)
```json
{
  "enabled": false,
  "message": "Bridge disabled"
}
```
**Trigger:** `OPENCODE_BRIDGE_ENABLED != "true"`

### Pattern 2: Error Response (All Endpoints)
```json
{
  "success": false,
  "error": "error message"
}
```

### Pattern 3: Model Invocation Success
```json
{
  "success": true,
  "message": {
    "content": "response text",
    "role": "assistant"
  },
  "model": "xai/grok-4",
  "provider": "openrouter",
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 280
  }
}
```

---

## Critical Implementation Details

### Key Rotation Logic
- **File:** `src/opencode_bridge/open_router_bridge.py:40-49`
- **Behavior:** Filters active keys from unified_key_manager
- **Transparency:** Keys are masked in responses (e.g., "sk-...")
- **Monitoring:** Available via `/openrouter/stats` endpoint

### Model ID Mapping (Orchestrator)
- **File:** `src/opencode_bridge/multi_model_orchestrator.py:109-123`
- **Supported Models:**
  - Grok (xai/grok-4)
  - Claude Opus (anthropic/claude-opus-4-5)
  - Claude Sonnet (anthropic/claude-3.5-sonnet)
  - DeepSeek (deepseek/deepseek-chat)
  - DeepSeek Coder (deepseek/deepseek-coder)
  - Gemini (google/gemini-flash-1.5)
  - Llama (meta-llama/llama-3.1-8b-instruct)

### Workflow Orchestration Commands
- **File:** `src/opencode_bridge/multi_model_orchestrator.py:18-39`
- **Supported Commands:**
  1. `"Оркестрируй: ModelA → ModelB → ModelC"` - Sequential chain
  2. `"Позвони ModelX с промптом: your_prompt"` - Single model call
  3. `"Сделай цепочку: Research → Design → Code → Test"` - Named chain

---

## Integration Points with VETKA

### Shared Components
| Component | Source | Used By |
|-----------|--------|---------|
| `unified_key_manager` | `src/utils/` | OpenRouterBridge |
| `call_model_v2()` | `src/elisya/provider_registry.py` | OpenRouterBridge.invoke() |
| `ProviderType.OPENROUTER` | `src/utils/unified_key_manager.py` | OpenRouterBridge init |
| `APIKeyService` | `src/orchestration/services/` | OpenRouterBridge init |

---

## Testing Checklist

- [ ] **OC-EP-001** GET /openrouter/keys - returns masked keys when enabled
- [ ] **OC-EP-002** POST /openrouter/invoke - routes to call_model_v2 with correct params
- [ ] **OC-EP-003** GET /openrouter/stats - returns accurate key rotation metrics
- [ ] **OC-EP-004** GET /openrouter/health - always returns healthy status
- [ ] All endpoints respect `OPENCODE_BRIDGE_ENABLED` flag
- [ ] Error handling returns proper JSON response
- [ ] Key masking prevents exposure in responses
- [ ] Model orchestration commands parse correctly
- [ ] Rate limiting keys properly tracked in stats

---

## Next Steps (Phase 95.3+)

1. **Implement Missing MCP Tools as Endpoints**
   - Add `/files/read` endpoint
   - Add `/files/edit` endpoint
   - Add `/search/semantic` endpoint

2. **Add Multi-Provider Support**
   - `/anthropic/invoke` endpoint
   - `/deepseek/invoke` endpoint
   - Provider selection UI

3. **Enhance Error Responses**
   - Add error codes (OC-ERR-001, etc.)
   - Include stack traces in dev mode
   - Add retry guidance

4. **Add Request Logging**
   - Log all invocations (without keys)
   - Track model performance metrics
   - Create audit trail

---

**Audit Date:** 2026-01-26
**Auditor:** Claude Code Agent (Phase 95.2)
**Status:** COMPLETE
