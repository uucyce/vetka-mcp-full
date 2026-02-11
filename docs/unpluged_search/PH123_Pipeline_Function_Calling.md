# Grok Research Prompt: Phase 123 — Pipeline Function Calling & Inter-Agent Communication

**For:** Grok 4.1 (The Last Samurai)
**From:** Opus Commander
**Date:** 2026-02-09
**Priority:** CRITICAL — Pipeline Quality Revolution
**Context:** Phase 122.5 fixed coder context (0% question rate), but coder still produces GENERIC code because it can't READ files

---

## EXECUTIVE SUMMARY

VETKA's Mycelium pipeline has 5 agents: Scout → Architect → Researcher → Coder → Verifier.
Currently agents are "fire-and-forget" — they get a prompt, return JSON, done.

**Problem:** Coder gets file NAMES from Scout but can't READ file contents. So it guesses architecture instead of matching it.

**Goal:** Give pipeline agents function calling (like Elisya orchestrator already does), enable inter-agent communication mid-execution, and allow user intervention between steps.

---

## RESEARCH AREA 1: Coder Function Calling

### 1.1 Current State

**Pipeline agent execution** (`agent_pipeline.py:_execute_subtask`):
```python
call_args = {
    "model": model,
    "messages": [system_prompt, user_prompt],
    "temperature": 0.4,
    "max_tokens": 2000,
}
# Phase 122.5: semantic search injection
if phase_type in ("fix", "build"):
    call_args["inject_context"] = {"semantic_query": subtask.description, "semantic_limit": 3}

result = tool.execute(call_args)  # ONE-SHOT, no tool loop
```

**Elisya orchestrator** (`orchestrator_with_elisya.py:_call_llm_with_tools_loop`):
```python
tool_schemas = get_tools_for_agent(agent_role)
response = await call_model_v2(messages, model, tools=tool_schemas)
for turn in range(max_tool_turns):  # 5 turns max
    tool_calls = extract_tool_calls(response)
    if not tool_calls: break
    results = await executor.execute(tool_calls)
    messages.append(tool_results)
    response = await call_model_v2(messages, model, tools=tool_schemas)  # Next turn
```

**LLM Call Tool** (`llm_call_tool.py`) already supports `tools` parameter:
```python
SAFE_FUNCTION_CALLING_TOOLS = {
    "vetka_read_file", "vetka_search_semantic", "vetka_list_files",
    "vetka_get_tree", "vetka_search_files", "vetka_web_search",
    "vetka_library_docs", ...  # 25+ read-only tools
}
# If tools passed, filters by allowlist, adds to payload
```

### 1.2 Questions for Grok

1. **Which models support function calling reliably?**
   - Dragon team uses: Qwen3-coder (coder), Kimi K2.5 (architect), Grok Fast 4.1 (researcher), GLM-4.7-flash (verifier)
   - Which of these handle OpenAI-style `tools` parameter?
   - Which support `tool_choice: "auto"` vs `tool_choice: "required"`?
   - Fallback for models that DON'T support FC?

2. **How many tool turns is optimal for a coder agent?**
   - Elisya uses 5 turns. Is that enough for coder who needs to read 3-5 files?
   - Risk: infinite loop if coder keeps calling tools but never produces code
   - Should we have a "must produce code by turn N" constraint?

3. **Which tools should coder have access to?**
   - `vetka_read_file` — read project files (ESSENTIAL)
   - `vetka_search_semantic` — Qdrant search for relevant code
   - `vetka_search_files` — ripgrep-style text search
   - `vetka_list_files` — directory listing
   - Should coder have `vetka_web_search`? `vetka_library_docs`?
   - Risk of too many tools: model confusion, token waste

4. **Implementation approach: modify _execute_subtask or create _execute_subtask_with_tools?**
   - Option A: Add tool loop directly to `_execute_subtask` (simpler but mixed responsibilities)
   - Option B: New method `_execute_subtask_with_fc` for agents that need FC (cleaner separation)
   - Option C: Port `_call_llm_with_tools_loop` from orchestrator into pipeline (DRY)

---

## RESEARCH AREA 2: Scout Reports as Artifacts

### 2.1 Current Flow
```
Scout → returns JSON dict → stored as self._scout_context →
  → injected into subtask.context → coder sees file names + patterns
```

### 2.2 Desired Flow
```
Scout → returns JSON dict → stored as self._scout_context →
  → ALSO creates ChatMessage artifact in originating chat →
  → artifact visible in VETKA UI (chat panel) →
  → user can read Scout's findings before pipeline continues →
  → coder sees full Scout report + file contents (via FC)
```

### 2.3 Questions

1. **Artifact format for Scout report?** Markdown? JSON? Collapsible sections?
2. **Should Scout report block pipeline?** Or emit async (user sees it but pipeline continues)?
3. **How to attach artifact to chat?** We have `sio.emit("chat_message", ...)` — add `artifact_type: "scout_report"`?
4. **Should Scout read file contents too?** Currently Scout only gets semantic search snippets. If Scout also reads files, coder might not need FC at all.

---

## RESEARCH AREA 3: Question → Tool Trigger (Adaptive Fallback)

### 3.1 Current Behavior
Phase 122.5 fixed: coder prompt says "NEVER ask questions." But what if coder genuinely needs more info?

### 3.2 Proposed: Adaptive Question Handling
```
Coder produces output →
  IF output contains {"question": "..."} THEN:
    → DON'T fail
    → Extract question
    → Trigger Scout scan with question as task
    → OR trigger vetka_read_file / vetka_search_semantic
    → Inject answer into coder's messages
    → Re-call coder with enriched context
```

### 3.3 Questions

1. **How to detect "question" in coder output?**
   - JSON parse for `{"question": ...}`
   - Regex for `?` at end of output
   - LLM classifier (expensive)

2. **Who answers the question?**
   - Scout (fast, cheap, Haiku model)
   - Researcher (Grok, deeper but slower)
   - Direct tool call (vetka_read_file — cheapest, most reliable)

3. **Loop risk:** Coder asks → Scout answers → Coder asks again → infinite
   - Max question rounds: 2?
   - After max, force coder to produce code with available context

4. **Is this BETTER than giving coder FC?**
   - FC: coder decides what to read (smart but needs FC-capable model)
   - Question trigger: pipeline decides what to read (works with any model)
   - Both? FC first, question trigger as fallback for non-FC models?

---

## RESEARCH AREA 4: Inter-Agent Communication (Tighter Collaboration)

### 4.1 Current Architecture
Agents are isolated. Information flows ONE direction:
```
Scout ──→ Architect ──→ [Researcher] ──→ Coder ──→ Verifier
              │                              ▲
              └──── subtask.context ──────────┘ (via STM)
```

### 4.2 Desired: Bidirectional Communication
```
Scout ◄──► Architect ◄──► Researcher
                ▲               ▲
                │               │
                ▼               ▼
           Coder ◄──► Verifier
                │
                ▼
         ActivityHub (glow events)
```

### 4.3 Questions

1. **Shared memory bus?**
   - Option A: ElisyaState (already exists, key-value store)
   - Option B: STM expansion (currently just list of previous results)
   - Option C: New PipelineState object passed to all agents
   - Which is cleanest?

2. **Agent-to-agent messaging?**
   - When verifier finds an issue, can it message architect directly?
   - Currently: verifier → pipeline → retry coder. Should architect re-plan?
   - Pattern: "escalation channels" vs "broadcast bus"

3. **Real-time progress tracking?**
   - Coder executing subtask 3/5 → user wants to see progress
   - Currently: `_emit_progress()` sends SocketIO events but they're coarse-grained
   - Can we emit per-tool-call progress? (e.g., "Coder reading file X...")

4. **Human-in-the-loop intervention?**
   - User sees coder going wrong direction → wants to intervene
   - Mechanism: SocketIO message from UI → pipeline checks for "pause/redirect" signal
   - Where to check: between subtasks? Between tool turns?
   - User can also inject context: "use Redis, not in-memory cache"

---

## RESEARCH AREA 5: Variative Cycles (User-Controlled Pipeline)

### 5.1 Vision
User should be able to:
1. **Choose models per agent** — "use GPT-5 for coder, keep Kimi for architect"
2. **Choose tools per agent** — "give coder web search" or "disable library docs"
3. **Set constraints** — "max 3 tool calls" or "timeout 60 seconds per subtask"
4. **See decision points** — "architect chose sequential execution — switch to parallel?"
5. **Fork pipeline** — "re-run subtask 2 with different model"

### 5.2 Questions

1. **UI for pipeline control?**
   - Chat-based: `/pipeline config coder.model=gpt-5`
   - Settings panel: drag-and-drop pipeline builder
   - Both?

2. **Preset system expansion?**
   - Current: `dragon_bronze`, `dragon_silver`, `dragon_gold` (fixed teams)
   - New: `custom_team` with per-agent model/tool configuration?
   - Storage: `data/templates/model_presets.json` — extend format?

3. **Runtime model switching?**
   - Subtask 1 coder fails → user says "switch to GPT-5" → subtask 2 uses GPT-5
   - How to implement? SocketIO command → pipeline reads mid-execution?

4. **Pipeline visualization?**
   - Mermaid diagram of current execution flow?
   - 3D visualization in VETKA tree? (nodes = agents, edges = data flow)

---

## RESEARCH AREA 6: Elisya Integration

### 6.1 Current Separation
```
Orchestrator (orchestrator_with_elisya.py):
  - Full tool loop (_call_llm_with_tools_loop, 5 turns)
  - PM → Architect → Dev → QA flow
  - ElisyaState shared memory
  - ElisyaMiddleware context reframing
  - SafeToolExecutor with audit trail

Pipeline (agent_pipeline.py):
  - One-shot LLM calls (no tool loop)
  - Scout → Architect → [Researcher || Scout] → Coder → Verifier
  - STM for inter-subtask memory
  - inject_context for semantic search
  - Verify → retry → escalate loop
```

### 6.2 Questions

1. **Merge or integrate?**
   - Option A: Merge pipeline into orchestrator (one system)
   - Option B: Pipeline calls orchestrator's tool loop for FC-capable agents
   - Option C: Extract `_call_llm_with_tools_loop` into shared utility, both systems use it
   - Which is architecturally cleanest?

2. **ElisyaState for pipeline?**
   - Pipeline already has STM — should it also use ElisyaState?
   - ElisyaState has: `set_variable()`, `get_variable()`, `get_all_variables()`
   - Could replace/supplement STM for richer inter-agent memory

3. **ElisyaMiddleware for pipeline?**
   - Middleware does: context reframing, token budgeting, provider routing
   - Pipeline already handles provider routing via presets
   - Context reframing could help: "reframe task for coder's perspective"

4. **SafeToolExecutor?**
   - Already exists in orchestrator
   - Pipeline would need same executor for FC
   - Shared module? Import from orchestrator?

---

## RESEARCH AREA 7: BMAD Branch Isolation

### 7.1 Already Built (60%)
`src/tools/git_tool.py`:
```python
AGENT_BRANCH_PREFIX = "agent/"
PROTECTED_BRANCHES = ["main", "master", "develop", "production", "staging"]

async def create_agent_branch(base_name, base_branch="main")
async def request_add(files, description, chat_id)  # approval-gated
async def request_commit(message, chat_id)            # approval-gated
async def request_push(branch, chat_id)               # approval-gated
```

### 7.2 NOT wired to pipeline
Pipeline currently writes to `spawn_output/` directory (filesystem) but doesn't create branches.

### 7.3 Questions

1. **When to create branch?** At pipeline start? At first file write?
2. **Branch naming?** `agent/dragon-silver-task-123-chat-star-toggle`?
3. **Auto-merge?** If all subtasks pass verification → auto-merge to main?
4. **Conflict resolution?** If two pipelines run concurrently on same files?
5. **Integration with ActivityHub?** Branch creates → glow on affected files?

---

## FILES TO ANALYZE

**Pipeline Core:**
- `src/orchestration/agent_pipeline.py` (~2100 lines) — Pipeline execution, all 5 agents
- `src/orchestration/orchestrator_with_elisya.py` (~1200 lines) — Elisya orchestrator with FC
- `src/mcp/tools/llm_call_tool.py` (~900 lines) — LLM calling with FC support

**Tool System:**
- `src/tools/safe_tool_executor.py` — Tool execution with audit trail
- `src/tools/git_tool.py` — BMAD branch isolation (60% built)
- `src/mcp/tools/tool_definitions.py` — All tool schemas

**Memory & Context:**
- `src/memory/stm_buffer.py` — Short-term memory between subtasks
- `src/orchestration/elisya_state.py` — Shared state for orchestrator
- `src/orchestration/elisya_middleware.py` — Context reframing

**Config:**
- `data/templates/pipeline_prompts.json` — Agent system prompts
- `data/templates/model_presets.json` — Team tier configurations

**Activity System:**
- `src/services/activity_hub.py` — Glow system (Phase 123.0, from Cursor)
- `src/services/activity_emitter.py` — Event emission

---

## EXPECTED DELIVERABLES

1. **FC Architecture Decision** — Which approach for giving coder function calling?
2. **Model FC Compatibility Matrix** — Which Dragon/Titan models support FC reliably?
3. **Inter-Agent Communication Design** — Shared state vs message bus vs escalation channels
4. **Variative Cycles Spec** — How user controls pipeline at runtime
5. **Elisya Integration Plan** — Merge, import, or extract shared utilities?
6. **BMAD Activation Roadmap** — Steps to wire git_tool into pipeline
7. **Risk Assessment** — Token costs, latency impact, loop risks, model FC reliability

---

## PRIORITIZATION (My Recommendation)

| Priority | Feature | Impact | Effort |
|----------|---------|--------|--------|
| **P0** | Coder FC (vetka_read_file) | Code quality 10x | Small — llm_call_tool already supports it |
| **P1** | Question → Scout trigger | Zero-failure pipeline | Medium — new fallback path |
| **P1** | Scout report artifacts | User visibility | Small — emit to chat |
| **P2** | Inter-agent communication | Collaboration quality | Medium — shared state design |
| **P2** | Variative cycles | User control | Large — UI + backend |
| **P3** | Elisya integration | Architecture cleanup | Large — careful merge |
| **P3** | BMAD activation | Code safety | Medium — wiring existing code |

---

## SUCCESS CRITERIA

After implementation:
- [ ] Coder reads actual file contents via FC → produces architecture-matching code
- [ ] Scout report visible in chat as artifact before coder starts
- [ ] Questions don't stop pipeline — fallback to Scout/tools
- [ ] User can see and intervene in pipeline execution
- [ ] Pipeline uses git branches (BMAD) for safe file operations
- [ ] Elisya's tool loop shared with pipeline (DRY)

---

**End of Research Prompt**

*Opus Commander awaits Grok's architectural analysis.*
*Key question: What's the fastest path to coder FC that works with Dragon team models?*
