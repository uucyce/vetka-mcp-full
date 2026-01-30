# HAIKU 3: Детальный Call Graph для VETKA

**Date:** 2026-01-25
**Purpose:** Точные пути вызовов для каждого сценария

---

## 🔴 SOLO CHAT: Сценарий 1 - Model Override

```
CLIENT SIDE:
  socket.emit('user_message', {
    text: "Help me",
    model: "qwen2:7b",  // ← Explicit model
    node_path: "/path/to/file.py"
  })

SERVER SIDE (user_message_handler.py):
  handle_user_message(sid, data)  [line 150]
    │
    ├─ requested_model = data.get("model")  [line 189]
    │  requested_model = "qwen2:7b"
    │
    └─→ if requested_model:  [line 237]
         │
         ├─ is_local_ollama = is_local_ollama_model(requested_model)  [line 241]
         │  └─→ detect_provider(model_name)  [chat_handler.py:49]
         │      └─→ ProviderRegistry.detect_provider(model_name)  [provider_registry.py:64]
         │          └─→ Returns: Provider.OLLAMA
         │  └─ is_local_ollama = True
         │
         └─→ if is_local_ollama:  [line 261]
             │
             ├─ Build model_prompt via build_model_prompt()  [line 326]
             │  [chat_handler.py:110]
             │
             ├─ Emit "stream_start" socket event  [line 339]
             │
             ├─ DIRECT CALL:
             │  ollama.chat(
             │    model="qwen2:7b",
             │    messages=[{"role": "user", "content": prompt}],
             │    stream=False
             │  )  [line 356]
             │  ❌ NO orchestrator involved
             │  ❌ NO provider_registry involved
             │  ❌ NO Elisya involved
             │  ✅ Direct to Ollama via import ollama
             │
             ├─ Extract response text  [line 364-369]
             │
             ├─ Emit "stream_end" socket event  [line 378]
             │
             ├─ Save to chat_history via save_chat_message()  [line 395]
             │
             └─ return (early exit)  [line 421]

RESPONSE FLOW:
  stream_start → stream_end → chat_response → agent_message

KEY LINES:
  - 189: requested_model assignment
  - 237: if requested_model branch
  - 241: model detection
  - 356: DIRECT ollama.chat() call
  - 362-391: Response handling + emit
```

---

## 🔵 SOLO CHAT: Сценарий 2 - OpenRouter Model Override

```
CLIENT:
  socket.emit('user_message', {
    text: "Help me",
    model: "anthropic/claude-3-haiku",  // ← OpenRouter model
    node_path: "/path/to/file.py"
  })

SERVER (user_message_handler.py):
  handle_user_message(sid, data)  [line 150]
    │
    ├─ requested_model = "anthropic/claude-3-haiku"
    │
    └─→ if requested_model:  [line 237]
         │
         ├─ is_local_ollama = is_local_ollama_model(requested_model)
         │  └─→ Model contains "/", so NOT ollama
         │  └─ is_local_ollama = False
         │
         ├─ Continue to OpenRouter section  [line 439]
         │
         ├─ Get OpenRouter API key via UnifiedKeyManager  [line 449-456]
         │  km = get_key_manager()
         │  api_key = km.get_openrouter_key()
         │
         ├─ Build model_prompt  [line 529]
         │
         ├─ Emit "stream_start"  [line 557]
         │
         ├─ TRY STREAMING:  [line 553-646]
         │  async with httpx.AsyncClient() as client:
         │    async with client.stream(
         │      "POST",
         │      "https://openrouter.ai/api/v1/chat/completions",
         │      headers={"Authorization": f"Bearer {api_key}", ...},
         │      json={
         │        "model": "anthropic/claude-3-haiku",
         │        "messages": [{"role": "user", "content": prompt}],
         │        "stream": True
         │      }
         │    ) as response:
         │      │
         │      ├─ if response.status_code == 429:  [line 582]
         │      │  full_response = "Model is rate limited"
         │      │
         │      ├─ elif response.status_code != 200:  [line 588]
         │      │  └─→ Check for auth errors (401, 402)  [line 601]
         │      │      └─→ Rotate key via km.rotate_to_next()  [line 608]
         │      │      └─→ Retry with new key
         │      │
         │      └─ else status_code == 200:  [line 623]
         │         async for line in response.aiter_lines():  [line 624]
         │           Extract tokens from SSE stream
         │           Emit "stream_token" per token  [line 640]
         │           Accumulate full_response
         │
         ├─ FALLBACK if streaming fails:  [line 655-686]
         │  Use non-streaming POST to same endpoint
         │  Receive full response at once
         │
         ├─ Emit "stream_end" with full_message  [line 693]
         │
         ├─ Save to chat_history  [line 710]
         │
         └─ return (early exit)  [line 738]

KEY LINES:
  - 439-754: OpenRouter section
  - 449-456: Key management
  - 553-646: Streaming attempt
  - 655-686: Non-streaming fallback
  - 601-616: Key rotation on 401/402
  - 608-612: Rotate and retry

IMPORTANT NOTES:
  ❌ Does NOT use provider_registry
  ❌ Does NOT use orchestrator
  ❌ Direct httpx call to OpenRouter API
  ❌ Manual key rotation (not unified with orchestrator)
  ✅ Streaming support via httpx
```

---

## 🟣 SOLO CHAT: Сценарий 3 - @Mention Model

```
USER TEXT: "@ollama:qwen2:7b Can you help?"

CLIENT:
  socket.emit('user_message', {
    text: "@ollama:qwen2:7b Can you help?",
    node_path: "/path/to/file.py"
  })

SERVER (user_message_handler.py):
  handle_user_message(sid, data)  [line 150]
    │
    ├─ text = "@ollama:qwen2:7b Can you help?"
    ├─ requested_model = None (no model override)  [line 189]
    │
    ├─ if requested_model: FALSE  [line 237]
    │
    ├─ Parse @mentions  [line 759]
    │  parsed_mentions = parse_mentions(text)
    │  └─→ Detects "@ollama:qwen2:7b"
    │      models = ["qwen2:7b"]
    │      mode = "single"
    │
    ├─ if parsed_mentions["mode"] == "single" and models:  [line 771]
    │  model_to_use = "qwen2:7b"
    │  is_ollama = True
    │
    └─→ try:  [line 798]
         │
         ├─ Build model_prompt  [line 858]
         │
         ├─ if is_ollama:  [line 876]
         │  │
         │  ├─ Check for tool support  [line 879]
         │  │
         │  ├─ DIRECT CALL:
         │  │  loop.run_in_executor(
         │  │    None,
         │  │    lambda: ollama.chat(
         │  │      model="qwen2:7b",
         │  │      messages=messages_with_tools,
         │  │      tools=model_tools if supported,
         │  │      stream=False
         │  │    )
         │  │  )  [line 901-906]
         │  │  ❌ Direct ollama.chat()
         │  │  ❌ No provider_registry
         │  │  ❌ No orchestrator
         │  │
         │  └─ Handle tool calls if present  [line 909-953]
         │     If tool calls, execute via SafeToolExecutor
         │
         └─ Emit agent_message + chat_response  [line 1048-1074]

KEY DIFFERENCES FROM SCENARIO 1:
  - Uses parse_mentions() instead of data.get("model")
  - Can handle tool calls from Ollama
  - Allows both ollama: and openrouter models via @mention
  - Still DIRECT API call, NO orchestrator

KEY LINES:
  - 759: parse_mentions()
  - 771: Single model detection
  - 876-877: Model routing logic
  - 901-906: DIRECT ollama.chat()
```

---

## 🟢 SOLO CHAT: Сценарий 4 - Agent Chain (DEFAULT)

```
CLIENT:
  socket.emit('user_message', {
    text: "Help me with this code",
    node_path: "/path/to/file.py"
    // NO model override, NO @mention
  })

SERVER (user_message_handler.py):
  handle_user_message(sid, data)  [line 150]
    │
    ├─ requested_model = None  [line 189]
    ├─ parsed_mentions = {} (no @mentions)  [line 759]
    │
    ├─ HOSTESS ROUTING (if available)  [line 1159]
    │  └─→ get_hostess()
    │      └─→ hostess.call_llm(prompt)
    │          └─→ Returns routing decision
    │
    ├─ Get agents  [line 1452]
    │  agents = get_agents()
    │  └─→ Returns {"PM": {...}, "Dev": {...}, "QA": {...}}
    │      Each has: instance, system_prompt, model_id
    │
    ├─ Determine agents_to_call based on Hostess decision  [line 1491-1677]
    │  agents_to_call = ["PM", "Dev", "QA"]  (default)
    │
    └─→ for agent_name in agents_to_call:  [line 1685]
         │
         ├─ agent_instance = agents[agent_name]["instance"]
         │  └─→ Type: VETKAPMAgent, VETKADevAgent, VETKAQAAgent
         │
         ├─ Build full_prompt  [line 1712-1735]
         │  └─→ build_full_prompt(
         │        agent_type="PM",
         │        user_message=text,
         │        file_context=context_for_llm,
         │        previous_outputs={},  // Chain context from earlier agents
         │        pinned_context=""
         │      )
         │
         ├─ CALL AGENT:  [line 1761-1767]
         │  loop.run_in_executor(
         │    None,
         │    lambda: agent_instance.call_llm(
         │      prompt=full_prompt,
         │      max_tokens=999999
         │    )
         │  )
         │
         │  ⚠️ This enters agent.call_llm() internals:
         │     Location: src/agents/base_agent.py
         │     Behavior: DEPENDS ON AGENT IMPLEMENTATION
         │     May use:
         │     - agent.model_id (e.g., "qwen2:7b")
         │     - provider_registry or api_aggregator internally
         │     - NOT visible from user_message_handler
         │
         ├─ Handle response (dict or string)  [line 1770-1779]
         │
         ├─ Store for chain context  [line 1786]
         │  previous_outputs["PM"] = response_text
         │
         ├─ Extract artifacts if Dev  [line 1791-1799]
         │
         ├─ Extract QA score if QA  [line 1804-1810]
         │
         └─ Append to responses[]  [line 1820-1829]

        NEXT ITERATION (Dev agent):
        ├─ previous_outputs = {"PM": "<pm output>"}
        ├─ Build prompt WITH previous_outputs context
        ├─ agent.call_llm() sees Dev system prompt + PM output
        └─ Dev responds based on PM analysis

        FINAL ITERATION (QA agent):
        ├─ previous_outputs = {"PM": "...", "Dev": "..."}
        ├─ Build prompt with both previous outputs
        ├─ QA responds based on both PM and Dev
        └─ Full chain complete

    ├─ Emit ALL responses to client  [line 1835-1911]
    │  for each resp in responses:
    │    emit("agent_message", {...})
    │    emit("chat_response", {...})
    │
    └─ Generate summary (multi-agent only)  [line 1928-2090]
       if not single_mode and len(responses) > 1:
         Build summary_prompt from responses
         Call Dev agent again to summarize
         Emit summary to client

KEY OBSERVATIONS:
  ✅ CHAIN CONTEXT: Previous agent outputs passed to next agent
  ❌ NOT using orchestrator
  ❌ NOT visible path to provider
  ⚠️ Agent internals hidden (black box)
  ⚠️ No Elisya context fusion
  ⚠️ No XAI fallback (would be in orchestrator)

KEY LINES:
  - 1452: get_agents()
  - 1685-1829: Agent loop
  - 1712-1718: build_full_prompt() with chain context
  - 1764: AGENT.CALL_LLM() call
  - 1786: Store previous output
  - 1835-1911: Emit all responses
  - 1928+: Summary generation
```

---

## 🟠 GROUP CHAT: Standard Flow

```
CLIENT:
  socket.emit('group_message', {
    group_id: "group-uuid",
    sender_id: "user",
    content: "Build a calculator app",
    pinned_files: []
  })

SERVER (group_message_handler.py):
  handle_group_message(sid, data)  [line 530]
    │
    ├─ group_id = data.get("group_id")
    ├─ sender_id = "user"
    ├─ content = "Build a calculator app"
    │
    ├─ Get orchestrator  [line 635]
    │  orchestrator = get_orchestrator()
    │  └─→ Type: OrchestratorWithElisya
    │
    ├─ Get group info  [line 560]
    │  manager = get_group_chat_manager()
    │  group = manager.get_group(group_id)
    │  └─→ Returns: {"name": "Team", "participants": {...}}
    │
    ├─ Store user message  [line 571-577]
    │  manager.send_message(
    │    group_id=group_id,
    │    sender_id="user",
    │    content=content,
    │    message_type="chat"
    │  )
    │
    ├─ Broadcast user message to group room  [line 584-586]
    │  sio.emit("group_message", user_message, room=f"group_{group_id}")
    │
    ├─ Check for MCP @mentions  [line 595-612]
    │  mentions = extract_mentions(content)
    │  if mentions:
    │    notify_mcp_agents(sio, group_id, mentions)
    │
    ├─ Select responding agents  [line 663-669]
    │  participants_to_respond = await manager.select_responding_agents(
    │    content=content,
    │    participants=group["participants"],
    │    sender_id="user"
    │  )
    │  └─→ Returns: [
    │        {"agent_id": "@Architect", "model_id": "claude-3-opus", "role": "Architect"},
    │        {"agent_id": "@Dev", "model_id": "qwen2:7b", "role": "Dev"}
    │      ]
    │
    └─→ while processed_idx < len(participants_to_respond):  [line 698-947]
         │
         ├─ participant = participants_to_respond[processed_idx]
         ├─ agent_id = "@Architect"
         ├─ model_id = "claude-3-opus"
         │
         ├─ Map role to agent type  [line 713-730]
         │  agent_type_map = {
         │    "Architect": "Architect",
         │    "Dev": "Dev",
         │    "QA": "QA"
         │  }
         │  agent_type = "Architect"
         │
         ├─ Build role-specific prompt  [line 758-783]
         │  system_prompt = get_agent_prompt("Architect")
         │  context_parts = [
         │    "## ROLE\n{system_prompt}\n",
         │    "## GROUP: Team\n",
         │    "## PREVIOUS AGENT OUTPUTS\n[PM]: ...\n",  // Chain context
         │    "## RECENT CONVERSATION\n...\n",
         │    "## CURRENT REQUEST\nBuild a calculator app"
         │  ]
         │  prompt = "\n".join(context_parts)
         │
         ├─ Emit stream start  [line 745-754]
         │  sio.emit("group_stream_start", {
         │    "id": msg_id,
         │    "group_id": group_id,
         │    "agent_id": "@Architect",
         │    "model": "claude-3-opus"
         │  }, room=f"group_{group_id}")
         │
         ├─ CALL ORCHESTRATOR:  [line 792-805]
         │  result = await asyncio.wait_for(
         │    orchestrator.call_agent(
         │      agent_type="Architect",
         │      model_id="claude-3-opus",
         │      prompt=prompt,
         │      context={
         │        "group_id": group_id,
         │        "group_name": "Team",
         │        "agent_id": "@Architect",
         │        "display_name": "Architect"
         │      }
         │    ),
         │    timeout=120.0
         │  )
         │
         │  ✅ ENTERS ORCHESTRATOR:
         │  Location: src/orchestration/orchestrator_with_elisya.py
         │
         │  Inside orchestrator.call_agent():
         │  a) Build ElisyaState from context
         │  b) Apply ElisyaMiddleware for reframing
         │  c) Call provider_registry.call_model_v2() [line 45]
         │     └─→ Clean provider dispatch
         │         ├─ OpenAI models → OpenAIProvider
         │         ├─ Anthropic models → AnthropicProvider
         │         ├─ Google models → GoogleProvider
         │         ├─ Ollama models → OllamaProvider
         │         ├─ OpenRouter models → OpenRouterProvider
         │         └─ XAI models → XaiProvider
         │  d) Handle XAI fallback if needed:
         │     if XaiKeysExhausted raised [provider_registry.py:27]:
         │       └─→ Fallback to OpenRouter [Phase 80.39]
         │  e) Return {status: "done", output: response_text}
         │
         ├─ Extract response  [line 815-818]
         │  response_text = result.get("output", "")
         │
         ├─ Store agent response  [line 826-832]
         │  manager.send_message(
         │    group_id=group_id,
         │    sender_id="@Architect",
         │    content=response_text,
         │    message_type="response",
         │    metadata={"in_reply_to": user_message.id}
         │  )
         │
         ├─ Emit stream end  [line 835-845]
         │  sio.emit("group_stream_end", {
         │    "id": msg_id,
         │    "group_id": group_id,
         │    "agent_id": "@Architect",
         │    "full_message": response_text,
         │    "metadata": {"model": "claude-3-opus", "agent_type": "Architect"}
         │  }, room=f"group_{group_id}")
         │
         ├─ Track last responder (for smart reply)  [line 855-863]
         │  group_object.last_responder_id = "@Architect"
         │  group_object.last_responder_decay = 0
         │
         ├─ Check for @mentions in agent response  [line 891-947]
         │  agent_mentions = extract_mentions(response_text)
         │  if agent_mentions and agent not in previous_outputs:
         │    └─→ ADD to participants_to_respond
         │        processed_idx doesn't increment for this agent
         │        While loop will process newly added agent
         │
         └─ previous_outputs["Architect"] = response_text  [line 823]
              ↓ Next iteration gets this context

        NEXT PARTICIPANT (e.g., @Dev):
        ├─ prompt includes previous_outputs["Architect"]
        ├─ orchestrator.call_agent() called again
        ├─ Dev responds with Architect context
        └─ Cycle continues

FINAL STEPS:
  ├─ All agents responded
  ├─ (Phase 57.8.2: Hostess summary DISABLED - too slow)
  └─ Group message handling complete

KEY ORCHESTRATOR FEATURES:
  ✅ XAI fallback to OpenRouter (Phase 80.37-80.40)
  ✅ Elisya context fusion
  ✅ CAM metrics collection
  ✅ Semantic search integration
  ✅ Proper key rotation via APIKeyService
  ✅ 120s timeout protection
  ✅ Chain context support
  ✅ Dynamic agent selection via @mentions

KEY LINES:
  - 635: orchestrator = get_orchestrator()
  - 663: select_responding_agents()
  - 793: orchestrator.call_agent() MAIN CALL
  - 815-818: Extract response
  - 826-832: Store agent response
  - 891-947: @mention detection for chaining
```

---

## 🟡 ORCHESTRATOR INTERNALS (orchestrator_with_elisya.py)

```
orchestrator.call_agent(
  agent_type="Architect",
  model_id="claude-3-opus",
  prompt=prompt,
  context={"group_id": "...", "display_name": "Architect"}
)

ENTRY: call_agent() method [orchestrator_with_elisya.py]
  ├─ Build ElisyaState  [varies by orchestrator version]
  │  state = ElisyaState(
  │    conversation_history=[],
  │    context=context,
  │    memory={...}
  │  )
  │
  ├─ Apply ElisyaMiddleware  [MiddlewareConfig]
  │  middleware = ElisyaMiddleware(config)
  │  reframed_prompt = middleware.reframe(prompt, state)
  │
  ├─ Call provider_registry.call_model_v2()  [line 45]
  │  result = await call_model_v2(
  │    prompt=reframed_prompt,
  │    model_id="claude-3-opus",
  │    temperature=0.7,
  │    max_tokens=999999,
  │    provider=ProviderRegistry.detect_provider("claude-3-opus")
  │  )
  │
  ├─ Inside call_model_v2():
  │  ├─ Detect provider from model name  [provider_registry.py:856]
  │  │  "claude-3-opus" → Provider.ANTHROPIC
  │  │  "gpt-4" → Provider.OPENAI
  │  │  "qwen2:7b" → Provider.OLLAMA
  │  │
  │  ├─ Get provider instance from registry  [line 863+]
  │  │  provider = ProviderRegistry.get_provider(Provider.ANTHROPIC)
  │  │  └─→ Returns AnthropicProvider(config)
  │  │
  │  ├─ Call provider.call()  [line 866+]
  │  │  response = await provider.call(
  │  │    messages=[{"role": "user", "content": reframed_prompt}],
  │  │    model="claude-3-opus",
  │  │    tools=None,
  │  │    **kwargs
  │  │  )
  │  │
  │  │  Inside AnthropicProvider.call():
  │  │  ├─ Get API key from config or APIKeyService
  │  │  ├─ Build Anthropic API request
  │  │  ├─ Call api.messages.create()
  │  │  └─ Return standardized response {message, model, provider, usage}
  │  │
  │  └─ Return response
  │
  ├─ Handle exceptions:
  │  try:
  │    result = await call_model_v2(...)
  │  except XaiKeysExhausted:  [Phase 80.39]
  │    # All xai keys got 403, fallback to OpenRouter
  │    result = await call_model_v2(
  │      model_id="openrouter/..." + model_name,
  │      provider=Provider.OPENROUTER  [Phase 80.40]
  │    )
  │
  ├─ Save to memory  [if enabled]
  │  state.conversation_history.append(ConversationMessage(...))
  │
  ├─ Collect CAM metrics  [orchestration/cam_engine.py]
  │  cam_engine.record_call(
  │    agent_type="Architect",
  │    model_id="claude-3-opus",
  │    tokens_input=len(prompt.split()),
  │    tokens_output=len(response.split()),
  │    latency=time.time() - start_time
  │  )
  │
  └─ Return {status: "done", output: response_text}

PROVIDER ARCHITECTURE [provider_registry.py:54-94]:
  BaseProvider (abstract):
    ├─ supports_tools: bool
    ├─ name: str
    └─ call(messages, model, tools=None, **kwargs) → Dict

  OpenAIProvider(BaseProvider):
    └─ call() → HTTP call to api.openai.com

  AnthropicProvider(BaseProvider):
    └─ call() → HTTP call to api.anthropic.com

  GoogleProvider(BaseProvider):
    └─ call() → HTTP call to generativelanguage.googleapis.com

  OllamaProvider(BaseProvider):
    └─ call() → Local call to ollama.chat()

  OpenRouterProvider(BaseProvider):
    └─ call() → HTTP call to openrouter.ai/api/v1/chat/completions

  XaiProvider(BaseProvider):
    └─ call() → HTTP call to api.x.ai
        └─ Exception: XaiKeysExhausted (403 on all keys)
```

---

## 📊 SUMMARY TABLE

| Scenario | Handler | LLM Path | Provider | Elisya | XAI Fallback | Key Rotation |
|----------|---------|----------|----------|--------|--------------|--------------|
| Solo - Model Override | user_message.py | ollama.chat() direct | None | ❌ | ❌ | ❌ |
| Solo - OpenRouter | user_message.py | httpx.post() direct | None | ❌ | ❌ | ✅ Manual |
| Solo - @Mention | user_message.py | ollama/requests direct | None | ❌ | ❌ | ✅ Manual |
| Solo - Agent Chain | user_message.py | agent.call_llm() | Depends on agent | ❌ | ❌ | ❌ |
| Group Chat | group_message.py | orchestrator.call_agent() | provider_registry | ✅ | ✅ | ✅ Auto |

---

**Note:** This document captures exact line numbers and execution paths as of 2026-01-25. Code changes may affect line numbers but flows should remain similar.
