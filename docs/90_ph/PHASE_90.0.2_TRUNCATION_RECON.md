# PHASE 90.0.2: ChatGPT Output Truncation Reconnaissance Report

# MARKER_90.0.2_START: Truncation Investigation

## Summary
Investigation of potential hardcoded output limits causing ChatGPT response truncation. Found **multiple truncation points** across the codebase, but **no backend-level response truncation for ChatGPT specifically**.

---

## CRITICAL FINDINGS

### Suspected Culprit: NONE FOUND AT RESPONSE LEVEL
No hardcoded truncation of model responses before emitting to frontend. The OpenAI provider returns raw responses without slicing.

---

## TRUNCATION POINTS IDENTIFIED

### 1. **Context Preparation Layer** (Input truncation, not output)
These are NOT causing ChatGPT output truncation, but ARE limiting context sent to models:

#### Message Utils (`src/api/handlers/message_utils.py`)
- **Line 154**: History message truncation `content[:500]` - limits individual history items to 500 chars
  ```python
  if len(content) > 500:
      content = content[:500] + "... [truncated]"
  ```
  - **Impact**: Only affects historical message display, not current response

- **Lines 191, 236-239**: Pinned file truncation (max 3000 chars per file)
  ```python
  if len(content) > max_chars:
      content = content[:max_chars] + "\n... [truncated]"
  ```
  - **Impact**: Only affects pinned file context sent to model

- **Line 1162**: JSON context truncation (max 2000 tokens)
  ```python
  context_data = _truncate_json_context(context_data, max_tokens)
  ```
  - **Impact**: Only affects dependency context structure

---

#### Handler Utils (`src/api/handlers/handler_utils.py`)
- **Line 165**: File content truncation (max 8000 chars)
  ```python
  max_chars = 8000
  if len(content) > max_chars:
      content = content[:max_chars] + "\n... [truncated]"
  ```
  - **Impact**: Only affects context for generic handlers

---

#### Orchestrator (`src/orchestration/orchestrator_with_elisya.py`)
- **Lines 709, 715**: Preview truncation (max 2000 chars)
  ```python
  'preview': content[:2000],
  'total_context_chars': len(content[:2000]),
  ```
  - **Impact**: Only affects preview metadata, not response

- **Line 761**: History truncation (max 500 chars)
  ```python
  content = content[:500] + "... [truncated]"
  ```
  - **Impact**: Only affects conversation history formatting

---

### 2. **Response Formatting Layer** (Where issue might be)
These operate on model responses:

#### Response Formatter (`src/orchestration/response_formatter.py`)
- **Line 171**: Code block truncation (max 3000 chars)
  ```python
  return cls.format_code_block(content[:3000], "")
  ```
  - **Impact**: Could truncate code responses to 3000 chars
  - **Provider**: Potentially affects all models
  - **CONCERN**: This happens AFTER model call, before emission

#### Elysia Tools (`src/orchestration/elysia_tools.py`)
- **Line 163**: Large file truncation (100KB limit)
  ```python
  content = content[:100_000] + "\n\n... [truncated at 100KB]"
  ```
  - **Impact**: Only affects file reading tools, not model response

---

### 3. **Provider-Specific Max Tokens** (Limits, not truncation)
These are **input limits**, not output truncation:

#### Provider Registry (`src/elisya/provider_registry.py`)
- **Line 229** (Anthropic provider):
  ```python
  "max_tokens": kwargs.get("max_tokens", 4096),
  ```
  - **Impact**: Output limit set at API call time (request-level, not response truncation)

#### LangGraph Nodes (`src/orchestration/langgraph_nodes.py`)
- **Line 507**: Context limit for analysis
  ```python
  content=content_to_analyze[:4000],
  ```
  - **Impact**: Limits input context, not model response

---

### 4. **Memory/Storage Limits** (Not response truncation)
- **triple_write_manager.py:226**: Weaviate storage (5000 chars) - for database, not API response
- **memory_manager.py:329**: Memory entry limit (5000 chars) - for internal storage
- **kg_extractor.py:371**: Knowledge graph content (3000 chars) - for indexing

---

## Architecture Analysis

### Response Flow for ChatGPT:
```
OpenAI API Call (provider_registry.py:104-171)
  ↓
Raw response returned (no truncation)
  ↓
Response Manager (response_manager.py)
  ├─ Format response text
  ├─ Emit to Socket.IO ← NO TRUNCATION HERE
  ↓
Frontend receives full response
```

### Potential Truncation Points in Response Flow:

| Location | Code | Behavior | ChatGPT Impact |
|----------|------|----------|-----------------|
| `response_formatter.py:171` | `content[:3000]` | Truncates code blocks | ⚠️ POSSIBLE |
| `provider_registry.py:229` | `max_tokens: 4096` | Request-level limit | Set by client, not truncation |
| Socket.IO emit | No slicing found | Returns full response | ✓ CLEAN |
| Message utils | Context building | Input truncation only | Not output truncation |

---

## VERDICT: Likely Culprits

### 1. **MOST LIKELY: `response_formatter.py:171`**
```python
return cls.format_code_block(content[:3000], "")
```
- This truncates **formatted responses** to 3000 chars
- Location: Happens AFTER model returns, BEFORE client receives
- Severity: **HIGH** - directly affects output
- Provider: Any model whose response goes through this formatter
- **FIX**: Check if this is being applied to ChatGPT responses

### 2. **POSSIBLE: Max tokens set too low**
- If `max_tokens=4096` is being set globally, model has less room
- But this is a REQUEST limit, not response truncation
- OpenAI would return partial token streams, not truncation at our level

### 3. **UNLIKELY but check:**
- Socket.IO emit logic in response_manager.py
- Frontend message display limits
- Client-side truncation (unlikely to be "backend issue")

---

## Key Evidence

### ✓ NO BACKEND TRUNCATION IN:
- OpenAI provider (`src/elisya/provider_registry.py:104-171`) - returns raw response
- Socket.IO handlers - no `[:N]` slicing on response content
- Chat routes (`src/api/routes/chat_routes.py`) - no truncation found

### ⚠️ TRUNCATION FOUND IN:
- Response formatter (potential culprit)
- Context builders (input only, not output)
- Handler utilities (input only)

---

## Recommendations for Phase 90.0.2+

1. **Audit `response_formatter.py:171`** - Check if code block formatting is being applied to ChatGPT responses
2. **Check `max_tokens` defaults** - Verify they're not too restrictive
3. **Trace response flow** - Add logging to see where truncation occurs:
   - After model returns
   - Before Socket.IO emit
   - At formatter stage
4. **Add response length monitoring** - Log response sizes at each stage

---

# MARKER_90.0.2_END

