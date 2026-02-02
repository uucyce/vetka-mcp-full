# 📊 AUDIT REPORT: VETKA Solo/Group Chat Architecture

**Date:** 2026-02-02
**Auditor:** Claude Opus 4.5 (via MCP)
**Phase:** 106+ (Post Multi-Agent MCP)
**Status:** ANALYSIS COMPLETE - MARKERS READY

---

## 🔍 ТЕКУЩАЯ АРХИТЕКТУРА

### **Solo Chat** (`src/api/handlers/user_message_handler.py`)

```
┌─────────────────────────────────────────────────────────────┐
│                    SOLO CHAT FLOW                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Путь 1: Direct Model Call (requested_model != None)       │
│  ├── Lines 264-664                                          │
│  ├── call_model_v2() напрямую                              │
│  └── ✅ ПРАВИЛЬНО для solo - обходит orchestrator          │
│                                                             │
│  Путь 2: @mention Direct Model                              │
│  ├── Lines 680-1002                                         │
│  ├── call_model_v2() напрямую                              │
│  └── ✅ ПРАВИЛЬНО - direct model bypass                    │
│                                                             │
│  Путь 3: Agent Chain (PM→Dev→QA)                           │
│  ├── Lines 1555-1700                                        │
│  ├── agent_instance.call_llm() напрямую ← ⚠️ ПРОБЛЕМА!    │
│  └── Line 1634: lambda: agent_instance.call_llm(...)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Group Chat** (`src/api/handlers/group_message_handler.py`)

```
┌─────────────────────────────────────────────────────────────┐
│                   GROUP CHAT FLOW                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Путь: All Messages → orchestrator.call_agent()            │
│  ├── Line 851                                               │
│  ├── orchestrator.call_agent(agent_type, model_id, prompt) │
│  └── ✅ ПРАВИЛЬНО! Получает:                               │
│      • CAM metrics                                          │
│      • Semantic context                                     │
│      • Proper key rotation                                  │
│      • Elisya tools integration                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## ❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### **ISSUE_1: Solo Chat Agent Chain НЕ использует orchestrator**

**Файл:** `src/api/handlers/user_message_handler.py`
**Строки:** 1632-1637

```python
# ТЕКУЩИЙ КОД (ПРОБЛЕМНЫЙ):
loop = asyncio.get_event_loop()
response_text = await loop.run_in_executor(
    None,
    lambda: agent_instance.call_llm(  # ← ПРЯМОЙ ВЫЗОВ!
        prompt=full_prompt, max_tokens=max_tokens
    ),
)
```

**Что теряется:**
- ❌ CAM metrics не записываются
- ❌ Semantic context не добавляется
- ❌ Key rotation не работает
- ❌ Tools = None (function calling disabled)
- ❌ Elisya integration bypassed

**Grok's Original Marker:** `❌ Solo chat: agent.call_llm() напрямую (line 1634)`
**Verdict:** Grok был ПРАВ! Solo agent chain должен использовать orchestrator.

---

### **ISSUE_2: OpenRouter Fallback - tools=None**

**Файл:** `src/api/handlers/user_message_handler.py`
**Строки:** 576-592

```python
# XAI Keys Exhausted → OpenRouter Fallback
async for token in call_model_v2_stream(
    messages=[{"role": "user", "content": model_prompt}],
    model=requested_model,
    provider=Provider.OPENROUTER,
    temperature=0.7,
    # ← tools НЕ ПЕРЕДАЮТСЯ! BUG!
):
```

**Проблема:** При fallback на OpenRouter теряются tools.

---

### **ISSUE_3: Chat History - Model Attribution**

**Файл:** `src/chat/chat_history_manager.py`

Сообщения сохраняются с `agent` field, но:
- ❌ Нет `model_name` в сохранённых сообщениях
- ❌ Нет `model_provider` для disambiguation
- ❌ Grok может путать свои ответы с ChatGPT при replay

**Пример текущего формата:**
```json
{
  "role": "assistant",
  "content": "...",
  "agent": "Dev"  // ← Какая модель? Grok? GPT? Claude?
}
```

**Нужный формат:**
```json
{
  "role": "assistant",
  "content": "...",
  "agent": "Dev",
  "model": "x-ai/grok-3",
  "provider": "xai"
}
```

---

## ✅ ЧТО РАБОТАЕТ ПРАВИЛЬНО

| Component | Status | Notes |
|-----------|--------|-------|
| Group Chat `orchestrator.call_agent()` | ✅ | Line 851 |
| Solo Direct Model Calls | ✅ | Correctly bypasses orchestrator |
| Phase 106 MCP Markers | ✅ | Ready in SUPER_PROMPT_v3.md |
| Provider Registry Semaphores | ✅ | Already in provider_registry.py:35-44 |
| MCP Session Init | ✅ | Fire-and-forget in both handlers |
| Chat History Persistence | ✅ | JSONL + Qdrant sync works |

---

## 📋 МАРКЕРЫ ДЛЯ SONNETS

### MARKER_SOLO_ORCHESTRATOR: Solo Agent Chain → orchestrator

**Файл:** `src/api/handlers/user_message_handler.py`
**Строки:** 1628-1650 (замена блока)

```python
# MARKER_SOLO_ORCHESTRATOR_START
# Phase 106+: Solo agent chain now uses orchestrator for CAM/tools/keys
from src.initialization.components_init import get_orchestrator

if use_streaming:
    # Streaming path unchanged
    response_text, token_count = await stream_response(...)
else:
    # FIX: Use orchestrator instead of direct call_llm
    orchestrator = get_orchestrator()
    if orchestrator:
        try:
            result = await asyncio.wait_for(
                orchestrator.call_agent(
                    agent_type=agent_name,
                    model_id=get_agent_model_name(agent_instance) if agent_instance else "qwen2.5vl:3b",
                    prompt=full_prompt,
                    context={
                        "file_path": node_path,
                        "node_id": request_node_id,
                        "is_solo_chain": True,
                    },
                ),
                timeout=120.0,
            )
            if result.get("status") == "done":
                response_text = result.get("output", "")
            else:
                response_text = f"[{agent_name}] Error: {result.get('error', 'Unknown')}"
        except asyncio.TimeoutError:
            response_text = f"[{agent_name}] Timeout after 120s"
    else:
        # Fallback to direct call if orchestrator unavailable
        loop = asyncio.get_event_loop()
        response_text = await loop.run_in_executor(
            None,
            lambda: agent_instance.call_llm(prompt=full_prompt, max_tokens=max_tokens),
        )
# MARKER_SOLO_ORCHESTRATOR_END
```

---

### MARKER_FALLBACK_TOOLS: OpenRouter Fallback with Tools

**Файл:** `src/api/handlers/user_message_handler.py`
**Строки:** 571-593 (добавить tools parameter)

```python
# MARKER_FALLBACK_TOOLS_START
except XaiKeysExhausted:
    print(f"[MODEL_DIRECTORY] XAI keys exhausted, falling back to OpenRouter")
    full_response = "⚠️ XAI API keys exhausted. Trying OpenRouter fallback..."
    try:
        # FIX: Pass tools if they were originally requested
        fallback_tools = data.get("tools")  # Preserve original tools
        async for token in call_model_v2_stream(
            messages=[{"role": "user", "content": model_prompt}],
            model=requested_model,
            provider=Provider.OPENROUTER,
            temperature=0.7,
            tools=fallback_tools,  # ← FIX: Pass tools!
        ):
            if token:
                full_response += token
                tokens_output += 1
                await sio.emit("stream_token", {"id": msg_id, "token": token}, to=sid)
    except Exception as fallback_err:
        full_response = f"Error: All providers failed - {str(fallback_err)[:100]}"
# MARKER_FALLBACK_TOOLS_END
```

---

### MARKER_CHAT_HISTORY_ATTRIBUTION: Model Attribution in Chat History

**Файл:** `src/api/handlers/user_message_handler.py`
**Везде где вызывается `save_chat_message()`** (множественные места)

```python
# MARKER_CHAT_HISTORY_ATTRIBUTION
# Example at line 423:
save_chat_message(
    node_path,
    {
        "role": "assistant",
        "agent": requested_model,
        "text": full_response,
        "node_id": node_id,
        "model": requested_model,           # ← ADD
        "provider": str(detected_provider), # ← ADD
    },
    pinned_files=pinned_files,
)
```

**Также обновить `chat_history_manager.py`** для поддержки новых полей.

---

## 🔄 GROK RESEARCH REFERENCE

Из `PHASE_106_SUPER_PROMPT_v3.md` и истории Грока:

| Phase | Feature | Status |
|-------|---------|--------|
| 99.2 | Chat history persistence | ✅ Implemented |
| 103.2 | CreateArtifactTool revival | ✅ Implemented |
| 104.5 | Team chat artifacts | ✅ Implemented |
| 106a | HTTP Multi-Transport | 🟡 Markers ready |
| 106b | MCPActor Class | 🟡 Markers ready |
| 106c | Client Pool Manager | 🟡 Markers ready |
| 106d | Provider Semaphores | ✅ In code |
| 106e | Socket.IO MCP Namespace | 🟡 Markers ready |
| 106f | MCP Server Updates | 🟡 Markers ready |
| 106g | OpenCode/Cursor/Doctor | ✅ Markers documented |

**Grok's Key Insight:**
> "Solo должен использовать orchestrator.call_agent()"

**Verdict:** Grok был ПРАВ для agent chain, но НЕ для direct model calls.

---

## 📊 SUMMARY TABLE

| Issue | Severity | Fix Complexity | Marker |
|-------|----------|----------------|--------|
| Solo Agent Chain → orchestrator | 🔴 HIGH | Medium | MARKER_SOLO_ORCHESTRATOR |
| OpenRouter Fallback tools=None | 🟡 MEDIUM | Low | MARKER_FALLBACK_TOOLS |
| Chat History Model Attribution | 🟡 MEDIUM | Medium | MARKER_CHAT_HISTORY_ATTRIBUTION |
| Chat Naming (semantic key) | 🟢 LOW | Low | Separate issue |
| Chat grouping by time | 🟢 LOW | Low | Separate issue |

---

## 🚀 NEXT STEPS

1. **Sonnets Group:** Применить MARKER_SOLO_ORCHESTRATOR
2. **Sonnets Group:** Применить MARKER_FALLBACK_TOOLS
3. **Sonnets Group:** Применить MARKER_CHAT_HISTORY_ATTRIBUTION
4. **Haiku Group:** Проверить все маркеры на полноту
5. **Test:** Verify solo chat now uses orchestrator
6. **Test:** Verify OpenRouter fallback preserves tools

---

**Author:** Claude Opus 4.5
**Reviewed by:** Pending Grok verification
**Implementation:** Sonnets team
