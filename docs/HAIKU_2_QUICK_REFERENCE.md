# Group Chat Flow - Quick Reference

## Entry to Response Flow

```
Socket.IO Event          File                              Line
─────────────────────────────────────────────────────────────────
group_message       →    group_message_handler.py          529
                        (handle_group_message)

Parse message       →    group_message_handler.py          541-550
                        (@mentions, role parsing)

Select agents       →    group_chat_manager.py             166
                        (select_responding_agents)

Role→AgentType map  →    group_message_handler.py          721-737
                        (MARKER_94.6)

Call agent          →    orchestrator_with_elisya.py       2242
                        (call_agent)

Run with Elisya     →    orchestrator_with_elisya.py       1215
                        (_run_agent_with_elisya_async)

Detect provider     →    orchestrator_with_elisya.py       1244
                        (ProviderRegistry.detect_provider)

Call LLM            →    orchestrator_with_elisya.py       1023
                        (call_model_v2)

Response            ←    group_message_handler.py          842-860
                        (emit group_stream_end)
```

---

## Role Routing

### By Role Name
| Role | AgentType | Default Model | Provider | Fallback |
|------|-----------|---------------|---------|----|
| PM | PM | model_routing["PM"]["model"] | Detected | OpenRouter |
| Dev | Dev | model_routing["Dev"]["model"] | Detected | OpenRouter |
| QA | QA | model_routing["QA"]["model"] | Detected | OpenRouter |
| Architect | Architect | model_routing["Architect"]["model"] | Detected | OpenRouter |
| Worker (default) | Dev | " | Detected | OpenRouter |
| Admin (default) | PM | " | Detected | OpenRouter |

### By Keyword
```python
PM keywords:      ['plan', 'task', 'scope', 'timeline', 'requirements', 'analyze', 'strategy']
Architect kw:     ['architecture', 'design', 'system', 'pattern', 'structure', 'module']
Dev keywords:     ['code', 'implement', 'function', 'class', 'write', 'debug', 'fix', 'api']
QA keywords:      ['test', 'bug', 'review', 'verify', 'validate', 'coverage', 'quality']
```

---

## Provider Detection Chain

```
model_id (e.g., "openai/gpt-4")
    ↓
ProviderRegistry.detect_provider(model_id)
    ├─ "openai/*" → Provider.OPENAI
    ├─ "anthropic/*" → Provider.ANTHROPIC
    ├─ "gpt-*" → Provider.OPENAI
    ├─ "claude-*" → Provider.ANTHROPIC
    ├─ "ollama/*" → Provider.OLLAMA
    ├─ "x-ai/*" or "grok-*" → Provider.XAI
    ├─ "openrouter/*" → Provider.OPENROUTER
    └─ default → Provider.OPENROUTER
    ↓
Inject API key via APIKeyService
    ↓
call_model_v2(model, provider, tools)
```

---

## Fallback Triggers

| Trigger | Condition | Action | Model Conversion |
|---------|-----------|--------|-------------------|
| **XAI Exhaustion** | XaiKeysExhausted exception | Fallback to OpenRouter | `"grok-2" → "x-ai/grok-2"` |
| **Rate Limit** | "429" in error message | Fallback to OpenRouter | Model stays as-is |
| **Not Found** | "404" in error message | Fallback to OpenRouter | Model stays as-is |
| **Quota** | "quota" in error message | Fallback to OpenRouter | Model stays as-is |

**Location:** `orchestrator_with_elisya.py:1020-1050` (MARKER_90.1.4.2)

---

## Tool Support by Provider

| Provider | Tools Supported | Notes |
|----------|-----------------|-------|
| OpenAI | ✅ YES | Via tool_schemas |
| Anthropic | ✅ YES | Via tool_schemas |
| Google/Gemini | ✅ YES | Via tool_schemas |
| Ollama | ⚠️ DEPENDS | Local models vary |
| X.AI (Grok) | ✅ YES | When using X.AI API directly |
| OpenRouter | ❌ NO | Disabled in fallback (Line 1036) |

**Critical:** When fallback to OpenRouter occurs: `tools=None` (Line 1036)

---

## Agent System Prompts

**Location:** `orchestrator_with_elisya.py:884-941`

```python
PM_PROMPT = """
You are the Project Manager analyzing {node_path}.
Focus on: requirements, timeline, risk assessment, resource allocation.
"""

Dev_PROMPT = """
You are the Developer implementing solutions for {node_path}.
Focus on: technical implementation, code quality, architecture alignment.
"""

QA_PROMPT = """
You are the QA Engineer ensuring quality for {node_path}.
Focus on: testing strategy, quality metrics, edge cases, regression.
"""

Architect_PROMPT = """
You are the Architect designing for {node_path}.
Focus on: system design, scalability, maintainability, patterns.
"""
```

Plus role-specific imports from `src/agents/role_prompts.py` (Line 1285)

---

## Parallel Execution (Dev + QA)

**Location:** `orchestrator_with_elisya.py:1539-1615`

```python
# Both Dev and QA run simultaneously
async def run_dev():
    return await _run_agent_with_elisya_async("Dev", state, dev_prompt)

async def run_qa():
    return await _run_agent_with_elisya_async("QA", state, qa_prompt)

dev_result, qa_result = await asyncio.gather(run_dev(), run_qa())
```

**Each parallel call:**
- Gets own model_id from routing
- Detects own provider independently
- Has own fallback logic
- Gets own tool schemas (if supported)
- Runs simultaneously with asyncio.gather()

---

## Phase 80.28: Smart Reply Decay

**Enables:** Conversation continuation without @mentions

```python
# In Group object (group_chat_manager.py:89-91)
last_responder_id: Optional[str] = None  # e.g., "@dev"
last_responder_decay: int = 0             # Increments on user messages

# Selection logic (group_chat_manager.py:280-289)
if sender_id == 'user' and group.last_responder_id and group.last_responder_decay < 1:
    # Route to last responder for conversation continuity
    return [last_responder]

# Reset on agent response (group_message_handler.py:862-870)
if group_object and result.get("status") == "done":
    group_object.last_responder_id = agent_id
    group_object.last_responder_decay = 0  # Reset
```

---

## Key Markers & Phases

| Marker | Phase | File | Purpose |
|--------|-------|------|---------|
| MARKER_94.5_GROUP_ENTRY | 94.5 | group_message_handler.py:541 | Group chat entry point |
| MARKER_94.6_ROLE_ROUTING | 94.6 | group_message_handler.py:719 | Role-based agent routing |
| MARKER_94.6_AGENT_SELECTION | 94.6 | group_chat_manager.py:198 | Agent selection logic |
| MARKER_90.1.4.1 | 90.1.4.1 | orchestrator_with_elisya.py:1234 | Provider detection standardization |
| MARKER_90.1.4.2 | 90.1.4.2 | orchestrator_with_elisya.py:1020 | XAI fallback handling |
| Phase 80.28 | 80.28 | group_chat_manager.py:172 | Smart reply with decay |
| Phase 80.13 | 80.13 | group_message_handler.py:72 | MCP agent @mention routing |
| Phase 57.8 | 57.8 | group_message_handler.py:222 | Hostess as group router |

---

## Testing Checklist

- [ ] Test PM role with OpenAI fallback to OpenRouter
- [ ] Test Dev role with Ollama → OpenRouter fallback on error
- [ ] Test QA role with Anthropic → OpenRouter fallback
- [ ] Test Architect with multiple models in group
- [ ] Verify tools=None when OpenRouter fallback occurs
- [ ] Test @mentions routing to specific agent
- [ ] Test SMART keyword-based selection (plan→PM, code→Dev, test→QA)
- [ ] Test /solo, /team, /round commands
- [ ] Test smart reply decay with user followups
- [ ] Verify Phase 80.28 last_responder tracking
- [ ] Test parallel Dev+QA execution
- [ ] Verify error handling and fallback logging

---

## OpenRouter Integration Status

✅ **FULLY INTEGRATED**

- Per-role provider detection: YES
- Per-role API key management: YES
- Fallback on XAI exhaustion: YES
- Fallback on rate limits: YES
- Fallback on 404 errors: YES
- Tool support: YES (primary), NO (fallback)
- Parallel execution support: YES
- Phase 80.28 smart reply: YES
- MCP @mention routing: YES

⚠️ **Known Limitation:** Tools disabled in OpenRouter fallback scenario
