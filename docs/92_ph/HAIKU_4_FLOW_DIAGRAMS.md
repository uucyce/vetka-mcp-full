# ДИАГРАММЫ ПОТОКОВ: Solo vs Group Chat

## 1. SOLO CHAT FLOW

```
User Message (Socket.IO: "message")
         ↓
user_message_handler.py:register_user_message_handler()
         ↓
@sio.on("message")
handle_user_message(sid, data)
         ↓
Extract: text, requested_model, node_path, etc.
         ↓
build_context_from_file() [LINE ~300]
         ↓
build_model_prompt() [LINE 326]  ← chat_handler.py:110-157
    • Adds context
    • Adds pinned files
    • Adds history
    • Adds viewport
    • ← Returns SINGLE PROMPT STRING
         ↓
[PROVIDER DETECTION] [LINE ~300-420]
         ├─→ is_ollama_model? ──→ Ollama Path
         │        ↓
         │   ollama.chat() [LINE 355]
         │   messages=[{"role": "user", "content": model_prompt}]
         │   stream=False
         │        ↓
         │   Parse response.message.content
         │        ↓
         │   emit("stream_end") ← Full response
         │
         └─→ is_openrouter_model? ──→ OpenRouter Path
                ↓
          httpx.AsyncClient [LINE 553]
          POST to openrouter.ai/api/v1/chat/completions [LINE 577]
          payload={
              "model": requested_model,
              "messages": [{"role": "user", "content": model_prompt}],
              "stream": True
          }
                ↓
          [STREAMING LOOP]
          For each server-sent-event:
              • Parse JSON
              • Extract chunk
              • emit("stream_token") ← INCREMENTAL
                ↓
          When stream ends:
          emit("stream_end") ← Full response
         ↓
Save to chat_history (LINE 395, 520)
         ↓
emit("message_sent") to CAM
         ↓
Response shown to user
```

**КЛЮЧЕВЫЕ ХАРАКТЕРИСТИКИ SOLO:**
- ✅ **БЫСТРО:** Прямые вызовы провайдеров
- ✅ **STREAMING:** Встроено в логику (OpenRouter)
- ❌ **БЕЗ РОЛЕЙ:** Все модели = "helpful assistant"
- ❌ **БЕЗ ELISYA:** Нет shared state
- ❌ **HARDCODED:** Provider detection в коде
- ❌ **НЕСОВМЕСТИМО:** Другой message format чем group

---

## 2. GROUP CHAT FLOW

```
User Message (Socket.IO: "group_message")
         ↓
group_message_handler.py:register_group_message_handler()
         ↓
@sio.on("group_message")
handle_group_message(sid, data)
         ↓
Extract: group_id, content, sender_id, pinned_files
         ↓
get_orchestrator() [LINE 635]
    ← Получить OrchestratorWithElisya instance
         ↓
select_responding_agents() [LINE 663]
    ← Выбрать какие агенты отвечают (PM, Dev, QA, etc.)
         ↓
FOR EACH participant IN participants_to_respond:
    ↓
    # Get system prompt for role
    system_prompt = get_agent_prompt(agent_type) [LINE 758]
                ↓ (e.g., role_prompts.py:15-74 for PM)

    # Build context with role
    context_parts = [
        f"## ROLE\n{system_prompt}\n",
        f"## GROUP: {group_name}\n",
        "## PREVIOUS AGENT OUTPUTS\n..." (if any),
        "## RECENT CONVERSATION\n...",
        f"## CURRENT REQUEST\n{content}"
    ]  [LINE 762-782]
    prompt = "\n".join(context_parts)
            ↓
    # Handle model overrides
    if "gpt" in model_id: model_id = f"openrouter/{model_id}" [LINE 707]
            ↓
    # CALL ORCHESTRATOR [LINE 793-804]
    result = await orchestrator.call_agent(
        agent_type=agent_type,              # "Dev", "QA", "PM", "Architect"
        model_id=model_id,                  # "openrouter/gpt-4", "ollama/qwen2:7b"
        prompt=prompt,                      # Full context + request
        context={
            "group_id": group_id,
            "group_name": group["name"],
            "agent_id": agent_id,
            "display_name": display_name,
        }
    )  [LINE 793]
            ↓
    ORCHESTRATOR.CALL_AGENT() [orchestrator_with_elisya.py:2242-2331]
            ↓
    # Create ElisyaState
    workflow_id = str(uuid.uuid4())
    state = self._get_or_create_state(workflow_id, prompt) [LINE 2285]
            ↓
    # Store context in state
    if context:
        state.raw_context = format_context(context) [LINE 2287-2296]
            ↓
    # Override model if specified
    if model_id and model_id != "auto":
        self.model_routing[agent_type] = {
            "provider": "manual",
            "model": model_id
        } [LINE 2300-2305]
            ↓
    # Run agent with Elisya
    if hasattr(self, "_run_agent_with_elisya_async"):
        output, updated_state = await self._run_agent_with_elisya_async(
            agent_type, state, prompt
        ) [LINE 2310]
            ↓
    INTERNAL: _run_agent_with_elisya_async() [SOMEWHERE IN ORCHESTRATOR]
            ├─→ Get system_prompt from role_prompts
            ├─→ Build messages with explicit role:
            │    messages = [
            │        {"role": "system", "content": system_prompt},
            │        {"role": "user", "content": prompt}
            │    ]
            ├─→ Call call_model_v2() [provider_registry.py:856]
            │        ↓
            │    async def call_model_v2(messages, model, provider=None, ...)
            │        ↓
            │    # Detect provider if not specified
            │    if provider is None:
            │        provider = ProviderRegistry.detect_provider(model) [LINE 885]
            │        ↓
            │    # Get provider instance
            │    provider_instance = registry.get(provider) [LINE 888]
            │        ↓
            │    # Call provider
            │    result = await provider_instance.call(
            │        messages, model, tools, **kwargs
            │    ) [LINE 901]
            │        ↓
            │    Return result with streaming support
            │
            └─→ Return output to call_agent()
            ↓
    Return {"output": output, "state": state, "status": "done"}
            ↓
    response_text = result.get("output", "") [LINE 816]

    # Store agent response
    agent_message = await manager.send_message(
        group_id=group_id,
        sender_id=agent_id,
        content=response_text
    ) [LINE 826]
            ↓
    # Emit streaming end
    await sio.emit("group_stream_end", {...}) [LINE 835]
            ↓
    # Store in previous outputs for chain context
    previous_outputs[display_name] = response_text[:500] [LINE 823]
            ↓
    # Check for @mentions in response for next agents
    agent_mentions = re.findall(r"@(\w+)", response_text) [LINE 892]
    if agent_mentions:
        # Add mentioned agents to responders queue
        participants_to_respond.append(...) [LINE 944]

    [END OF FOR LOOP - PROCESS NEXT AGENT]
    ↓
Save all responses to chat_history
         ↓
Response shown to all group participants
```

**КЛЮЧЕВЫЕ ХАРАКТЕРИСТИКИ GROUP:**
- ✅ **РОЛИ:** PM, Dev, QA, Architect с разными system prompts
- ✅ **ELISYA:** ElisyaState для context fusion
- ✅ **PROVIDER REGISTRY:** Единая система выбора провайдера
- ✅ **CHAIN CONTEXT:** Агенты видят output предыдущих агентов
- ✅ **@MENTIONS:** Динамическое добавление агентов в очередь
- ✅ **SMART REPLY:** Отслеживание последнего responder
- ❌ **МЕДЛЕННЕЕ:** Overhead от orchestration
- ❌ **ТОЛЬКО GROUP:** Не используется в solo chat

---

## 3. СРАВНЕНИЕ ОБОИХ ПОТОКОВ

### Message Building

**SOLO:**
```
User Input "What is 2+2?"
    ↓
build_model_prompt(
    text="What is 2+2?",
    context_for_model="<file content>",
    pinned_context="<pinned files>",
    ...
)
    ↓
Returns:
"""You are a helpful AI assistant. Analyze the following context...

<file content>

## CURRENT USER QUESTION
What is 2+2?
"""
    ↓
messages = [{"role": "user", "content": ↑THIS ENTIRE STRING↑}]
```

**GROUP:**
```
User Input "What is 2+2?"
    ↓
get_agent_prompt("Dev")
    ↓
Returns:
"""You are Dev (Developer) in the VETKA AI team.
## YOUR ROLE
- Write WORKING, COMPLETE code
...
"""
    ↓
Build context_parts:
- "## ROLE\n" + system_prompt
- "## GROUP: Project Team\n"
- "## CURRENT REQUEST\nWhat is 2+2?"
    ↓
prompt = "\n".join(context_parts)
    ↓
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": prompt}
]
```

### Provider Detection

**SOLO:**
```
if is_ollama_model(requested_model):
    # Direct ollama.chat()
elif is_openrouter_model(requested_model):
    # Direct httpx to openrouter.ai
```

**GROUP:**
```
if "gpt" in model_id:
    model_id = f"openrouter/{model_id}"

orchestrator.call_agent(
    model_id=model_id,
    ...
)
    ↓
Inside orchestrator:
self.model_routing[agent_type] = {"provider": "manual", "model": model_id}
    ↓
Later in _run_agent_with_elisya_async():
provider = ProviderRegistry.detect_provider(model_id)
provider_instance = registry.get(provider)
await provider_instance.call(...)
```

---

## 4. CALL STACK REFERENCE

### SOLO CALL STACK
```
Socket.IO Event ("message")
    ↓
user_message_handler.py:handle_user_message()
    ↓
chat_handler.py:build_model_prompt()
    ↓
[DIRECT PROVIDER CALL]
    ├─ ollama.chat() [ollama library]
    └─ httpx.AsyncClient.stream() [httpx library]
```

### GROUP CALL STACK
```
Socket.IO Event ("group_message")
    ↓
group_message_handler.py:handle_group_message()
    ↓
orchestrator.call_agent()
    ↓
orchestrator._run_agent_with_elisya_async()
    ↓
provider_registry.py:call_model_v2()
    ↓
provider_instance.call()  [OpenAI, Anthropic, Ollama, etc.]
    ↓
[ACTUAL API CALL]
```

---

## 5. MESSAGE FORMAT EXAMPLES

### SOLO - What the Model Actually Receives

```
Role: user
Content:
"""
You are a helpful AI assistant. Analyze the following context and answer the user's question.

## FILE CONTEXT
[content of /src/main.py - full file]

## PINNED FILES
<content of pinned files>

## 3D VIEWPORT CONTEXT
[viewport summary if provided]

## CHAT HISTORY
[recent chat history]

## CURRENT USER QUESTION
What is 2+2?

---

Provide a helpful, specific answer:
"""
```

### GROUP - What the Model Actually Receives

```
System Role:
"""
You are Dev (Developer) in the VETKA AI team.

## YOUR ROLE
- Write WORKING, COMPLETE code
- Create artifacts (files, functions, classes)
- Follow tasks from PM or Architect (if provided)
...
"""

User Message:
"""
## ROLE
[same system prompt again - because built into prompt]

## GROUP: Project Team

## PREVIOUS AGENT OUTPUTS
[PM]: Here's the plan...
[QA]: I tested it...

## RECENT CONVERSATION
[user]: Build a calculator
[PM]: I'll coordinate this

## CURRENT REQUEST
Build a calculator
"""
```

**OBSERVATION:** Group chat DUPLICATES system prompt (once as system role, once in prompt string)!

---

## 6. STREAMING COMPARISON

### SOLO STREAMING (OpenRouter)
```
Message 1: {"object":"chat.completion.chunk","choices":[{"delta":{"content":"Hello"}}]}
    ↓ extract chunk
    ↓ emit("stream_token", {"content": "Hello"})
    ↓ Wait for next event

Message 2: {"object":"chat.completion.chunk","choices":[{"delta":{"content":" world"}}]}
    ↓ emit("stream_token", {"content": " world"})

Message 3: {"object":"chat.completion.chunk","choices":[{"delta":{"content":"!"}}]}
    ↓ emit("stream_token", {"content": "!"})

[stream]
    ↓ Final emit("stream_end", {"full_message": "Hello world!"})
```

### GROUP STREAMING (Through Orchestrator)
```
orchestrator.call_agent()
    ↓
_run_agent_with_elisya_async()
    ↓
call_model_v2()
    ↓
provider_instance.call()
    ↓ [Streaming happens here, but wrapped]
    ↓ [Single result returned]

emit("group_stream_end", {"full_message": "..."})
    ↓ No incremental tokens (buffered until done)
```

**DIFFERENCE:** Solo streams tokens incrementally, Group buffers until completion

---

## 7. ERROR HANDLING DIFFERENCES

### SOLO ERROR HANDLING

**Ollama Error:**
```
try:
    ollama_response = await loop.run_in_executor(None, ollama_call)
except Exception as e:
    emit("stream_end", {"error": str(e)})
```

**OpenRouter Error:**
```
if response.status_code == 429:
    # Rate limit
    full_response = "⚠️ Model is rate limited..."
elif response.status_code == 400:
    # Streaming not supported, fallback
    use_streaming = False
else:
    # Other error
    error_text = await response.aread()
```

### GROUP ERROR HANDLING

```
try:
    result = await asyncio.wait_for(
        orchestrator.call_agent(...),
        timeout=120.0
    )
except asyncio.TimeoutError:
    result = {"status": "error", "error": "Timeout after 120 seconds"}
except Exception as e:
    # Captured inside orchestrator
    return {"output": "", "error": str(e), "status": "error"}
```

---

## 8. EXECUTION TIMELINE EXAMPLE

### SOLO TIMELINE
```
User: "What is 2+2?"
t=0ms:    Socket.IO event received
t=10ms:   Context built
t=20ms:   Prompt built (550 chars)
t=30ms:   HTTP request to openrouter.ai sent
t=200ms:  First token arrives ("2")
t=250ms:  Second token arrives ("+")
t=300ms:  Third token arrives ("2")
t=350ms:  Fourth token arrives ("=")
t=400ms:  Fifth token arrives ("4")
t=450ms:  Stream ends
t=460ms:  Response saved
t=470ms:  Total: ~470ms
```

### GROUP TIMELINE (PM + Dev)
```
User: "Build a calculator"
t=0ms:      Socket.IO event received
t=50ms:     PM selected as primary responder
t=100ms:    PM system prompt loaded
t=150ms:    PM context built
t=200ms:    PM message sent to orchestrator
t=300ms:    PM receives response from LLM (~100ms for LLM)
t=400ms:    PM response stored
t=450ms:    Dev selected from PM @mention
t=500ms:    Dev system prompt loaded
t=550ms:    Dev context built (includes PM output)
t=600ms:    Dev message sent to orchestrator
t=700ms:    Dev receives response from LLM (~100ms for LLM)
t=800ms:    Dev response stored
t=850ms:    Total: ~850ms (2x agents sequential)
```

---

## 9. WHERE TO MAKE CHANGES FOR UNIFICATION

### OPTION A: Make SOLO use GROUP system (RECOMMENDED)

```
# Step 1: user_message_handler.py line ~350
INSTEAD OF:
    if is_ollama_model:
        ollama.chat(...)
    elif is_openrouter_model:
        httpx.post(...)

DO THIS:
    result = await orchestrator.call_agent(
        agent_type="Assistant",  # Default role for solo
        model_id=requested_model,
        prompt=text,  # Just the user input
        context={"file": node_path}
    )

# Step 2: Make chat_handler.py:build_model_prompt() return both
INSTEAD OF:
    return f"You are helpful...{context}...{text}"

DO THIS:
    system_prompt = "You are a helpful assistant"
    user_message = f"{context}\n\n{text}"
    return (system_prompt, user_message)

# Step 3: Orchestrator already does the right thing
# Just needs to handle "Assistant" agent type
```

### OPTION B: Keep SOLO independent, but unify message format

```
# Still use direct calls, but build messages correctly
# user_message_handler.py line ~350

system_prompt = "You are a helpful AI assistant..."
user_message = f"{context}\n\nQuestion: {text}"

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_message}
]

# Then pass to ollama or openrouter
if is_ollama_model:
    ollama.chat(
        model=requested_model,
        messages=messages  # ← Now matches group format!
    )
```

---

## CONCLUSION

**IDEAL STATE:**
```
ALL model calls
    ↓
orchestrator.call_agent(agent_type, model_id, prompt)
    ↓
provider_registry.call_model_v2(messages, model, provider)
    ↓
provider_instance.call(messages, model)
    ↓
ACTUAL API
```

**CURRENT STATE:**
```
SOLO calls                      GROUP calls
    ↓                               ↓
Direct ollama/openrouter      orchestrator.call_agent()
    ↓                               ↓
ACTUAL API                    provider_registry
                                  ↓
                              ACTUAL API
```

**Need to converge these into ONE system!**
