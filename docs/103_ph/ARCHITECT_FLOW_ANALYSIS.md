# ARCHITECT FLOW ANALYSIS - VETKA Phase 103

**Date:** 2026-01-31
**Scope:** Architect agent behavior, task delegation, Researcher loop
**Files analyzed:**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/agents/vetka_architect.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/agent_pipeline.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/agents/role_prompts.py`

---

## EXECUTIVE SUMMARY

**Architect Agent** существует в 2-х контекстах:
1. **Legacy Orchestrator** (`orchestrator_with_elisya.py`) - работает линейно PM → Architect → Dev/QA parallel
2. **AgentPipeline** (`agent_pipeline.py`) - fractal pipeline с автоматическим Researcher loop

**ГЛАВНЫЙ ВЫВОД:** В Legacy Orchestrator **НЕТ** Researcher loop для Architect. Researcher loop **ЕСТЬ** только в AgentPipeline.

---

## 1. CURRENT FLOW (Legacy Orchestrator)

### 1.1 Workflow Sequence

**File:** `orchestrator_with_elisya.py:1439-1920`

```
PM → Architect → [Dev || QA] → Merge → Ops
```

**Architect position:** Line 1545-1588

```python
# ===== PHASE 2: ARCHITECT =====
elisya_state.speaker = "Architect"
architect_result, elisya_state = await self._run_agent_with_elisya_async(
    "Architect", elisya_state, architect_prompt
)
result["architecture"] = architect_result
```

### 1.2 How Architect Gets Task

**Input sources:**
1. **PM result** (line 1560): `architect_prompt += f"\n\n## PM's Plan:\n{pm_result}"`
2. **Rich context** (if available, line 1553-1558):
   ```python
   architect_prompt = self._generate_rich_agent_prompt(
       agent_type="Architect",
       rich_context=rich_context,  # File preview, metadata
       user_question=feature_request,
       node_path=rich_context.get("node_path")
   )
   ```

**MARKER:** `orchestrator_with_elisya.py:1550-1560`

### 1.3 What Architect Does

**Model:** Dynamic routing via `ModelRouter` (line 1272-1274)
- Default: OpenRouter Claude/Grok fallback
- Override via `self.model_routing[agent_type]`

**Prompt:** `role_prompts.py:237-334` - **ARCHITECT_SYSTEM_PROMPT**

**Key responsibilities:**
- Design system architecture and module structure
- Break down complex tasks into subtasks
- **Coordinate team using @mentions** (Dev, QA, Researcher, PM)
- Define interfaces, patterns, data flow

**Tools available** (line 253-263):
- `read_code_file`, `list_files`, `search_codebase`
- `search_weaviate`, `search_semantic`
- `get_tree_context`, `camera_focus`
- `create_artifact` (for design docs)

**MARKER:** `role_prompts.py:254-263`

### 1.4 Does Architect Return to Researcher?

**NO.** In Legacy Orchestrator:
- Architect runs ONCE (line 1568-1570)
- No loop, no retry, no Researcher callback
- Next step: **Parallel Dev/QA** (line 1589-1720)

**MARKER:** `orchestrator_with_elisya.py:1589` - `# PHASE 3: PARALLEL DEV & QA`

### 1.5 How Tasks are Delegated to Dev/QA

**Delegation mechanism:**
1. Architect completes → architecture saved to `result["architecture"]`
2. Dev/QA prompts **DO NOT include** Architect's output by default
3. Dev gets PM plan + rich context (line 1604-1616)
4. QA gets its own prompt (line 1618-1630)

**CRITICAL GAP:** Dev/QA don't receive Architect's design unless ChainContext passes it.

**MARKER:** `orchestrator_with_elisya.py:1604-1630`

---

## 2. TOOLS AVAILABLE TO ARCHITECT

### 2.1 Agent Class

**File:** `vetka_architect.py:11-23`

```python
class VETKAArchitectAgent(BaseAgent):
    def __init__(self):
        super().__init__("VETKA-Architect")
        self.model = "ollama/deepseek-coder:6.7b"

    def design_solution(self, problem: str) -> str:
        prompt = f"You are Solution Architect. Design architecture for: {problem}\n\nArchitecture:"
        return self.call_llm(prompt)

    def optimize_design(self, design: str) -> str:
        prompt = f"Review and optimize this design:\n{design}\n\nOptimizations:"
        return self.call_llm(prompt)
```

**Status:** ⚠️ **MINIMAL** - только LLM вызовы, NO tools integration

**MARKER:** `vetka_architect.py:11-23`

### 2.2 Tool Injection in Orchestrator

**File:** `orchestrator_with_elisya.py:1221-1400` - `_run_agent_with_elisya_async()`

**Tools injected** (line 2775-2800):
```python
if agent_type in ["PM", "Dev", "QA", "Architect", "Researcher", "Hostess"]:
    # Get CAM tools from registry
    cam_tools = []
    # Standard tools: read_code_file, search_semantic, get_tree_context, camera_focus
```

**Tool types:**
- **CAM tools:** engram_context, engram_subgraph, engram_learning_rate
- **Standard tools:** camera_focus, search_semantic, get_tree_context, read_code_file
- **Phase 17-L tools:** See `role_prompts.py:254-263`

**MARKER:** `orchestrator_with_elisya.py:2788-2796`

---

## 3. RESEARCHER LOOP (AgentPipeline ONLY)

### 3.1 AgentPipeline Architecture

**File:** `agent_pipeline.py:60-768`

**Pipeline flow:**
```
Task → Architect Plan → [Subtask1, Subtask2, ...] → Execute subtasks
         ↓
    Auto-research if needs_research=True
         ↓
    Researcher → Architect (via context injection)
```

### 3.2 Architect Planning Phase

**File:** `agent_pipeline.py:503-563` - `_architect_plan()`

**Model:** `anthropic/claude-sonnet-4` (default, line 520)

**Prompt template** (line 92-114):
```json
{
    "subtasks": [
        {
            "description": "what to do",
            "needs_research": false,
            "question": null,
            "marker": "MARKER_102.X"
        },
        {
            "description": "unclear part",
            "needs_research": true,  // ← Triggers Researcher
            "question": "What is the best approach for X?",
            "marker": "MARKER_102.Y"
        }
    ],
    "execution_order": "sequential" or "parallel",
    "estimated_complexity": "low|medium|high"
}
```

**MARKER:** `agent_pipeline.py:92-114`

### 3.3 Researcher Auto-Trigger

**File:** `agent_pipeline.py:429-473`

**Trigger logic:**
```python
for subtask in pipeline_task.subtasks:
    # Auto-trigger research on needs_research flag
    if subtask.needs_research:
        subtask.status = "researching"

        question = subtask.question or subtask.description
        research = await self._research(question)  # ← Grok/Claude researcher

        # Inject research results into subtask context
        subtask.context.update(research)

        # Recursive: if confidence < 0.7, ask follow-up questions
        if research.get("confidence", 1.0) < 0.7:
            for fq in research.get("further_questions", [])[:2]:
                sub_research = await self._research(fq)
                subtask.context["enriched_context"] += f"\n\nFollow-up ({fq}):\n{sub_research.get('enriched_context', '')}"
```

**MARKER:** `agent_pipeline.py:440-458`

### 3.4 Researcher Model

**File:** `agent_pipeline.py:566-634` - `_research()`

**Model:** `x-ai/grok-4` (default, line 582)

**Response format:**
```json
{
    "insights": ["key finding 1", "key finding 2"],
    "actionable_steps": [
        {"step": "description", "needs_code": true, "marker": "MARKER_102.X"}
    ],
    "enriched_context": "key facts and recommendations for the coder",
    "confidence": 0.9,
    "further_questions": ["optional follow-up if confidence < 0.7"]
}
```

**Semantic injection** (line 596-601):
```python
"inject_context": {
    "semantic_query": question,
    "semantic_limit": 5,
    "include_prefs": True,
    "compress": True
}
```

**MARKER:** `agent_pipeline.py:582-602`

### 3.5 Context Passing (STM)

**File:** `agent_pipeline.py:285-306` - Short-Term Memory

**How it works:**
1. After each subtask completes → `_add_to_stm(marker, result)`
2. Before next subtask → `_get_stm_summary()` injected into context
3. Keeps **last 5 results** for context window management

```python
def _add_to_stm(self, marker: str, result: str):
    self.stm.append({
        "marker": marker,
        "result": result[:500]  # Truncate for efficiency
    })
    if len(self.stm) > self.stm_limit:
        self.stm.pop(0)  # Keep last N

def _get_stm_summary(self) -> str:
    summary_parts = ["Previous results:"]
    for item in self.stm[-3:]:  # Last 3 for brevity
        summary_parts.append(f"- [{item['marker']}]: {item['result'][:200]}...")
    return "\n".join(summary_parts)
```

**Injection point** (line 432-437):
```python
if self.stm:
    stm_summary = self._get_stm_summary()
    if subtask.context is None:
        subtask.context = {}
    subtask.context["previous_results"] = stm_summary
```

**MARKER:** `agent_pipeline.py:285-306`, `agent_pipeline.py:432-437`

---

## 4. PARALLEL DECISION LOGIC

### 4.1 Legacy Orchestrator

**File:** `orchestrator_with_elisya.py:1589-1720`

**Hardcoded parallel:** Dev/QA always run in parallel after Architect

```python
# ===== PHASE 3: PARALLEL DEV & QA =====
async def run_dev():
    return await self._run_agent_with_elisya_async("Dev", elisya_state, dev_prompt)

async def run_qa():
    return await self._run_agent_with_elisya_async("QA", elisya_state, qa_prompt)

# Execute in parallel
results = await asyncio.gather(run_dev(), run_qa(), return_exceptions=True)
```

**MARKER:** `orchestrator_with_elisya.py:1631-1663`

### 4.2 AgentPipeline

**File:** `agent_pipeline.py:112` - `execution_order` field

**Architect decides:**
```json
{
    "execution_order": "sequential" or "parallel",
    "estimated_complexity": "low|medium|high"
}
```

**NOT IMPLEMENTED YET** in execution phase. All subtasks run sequentially (line 429-473).

**MARKER:** `agent_pipeline.py:112`, `agent_pipeline.py:429-473`

---

## 5. GAPS & MARKERS

### GAP 1: Architect → Dev/QA Context Passing
**Location:** `orchestrator_with_elisya.py:1604-1630`
**Issue:** Dev/QA don't receive Architect's architecture by default
**Fix needed:** Inject `result["architecture"]` into Dev/QA prompts

### GAP 2: No Researcher Loop in Legacy Orchestrator
**Location:** `orchestrator_with_elisya.py:1545-1588`
**Issue:** Architect runs once, no research feedback
**Fix needed:** Integrate AgentPipeline's `needs_research` logic

### GAP 3: VETKAArchitectAgent has NO tools
**Location:** `vetka_architect.py:11-23`
**Issue:** Just LLM wrapper, doesn't use CAM/search tools
**Fix needed:** Inherit tool support from BaseAgent or use Orchestrator's tool injection

### GAP 4: Parallel execution not implemented in AgentPipeline
**Location:** `agent_pipeline.py:429-473`
**Issue:** `execution_order` parsed but ignored, all sequential
**Fix needed:** Add `asyncio.gather()` for parallel subtasks

### GAP 5: Architect prompt missing STM context
**Location:** `agent_pipeline.py:503-563`
**Issue:** Architect planning doesn't see previous pipeline results
**Fix needed:** Inject STM summary into Architect prompt

---

## 6. COMPARISON TABLE

| Feature | Legacy Orchestrator | AgentPipeline |
|---------|---------------------|---------------|
| **Architect position** | Phase 2 (after PM) | Planning phase (before subtasks) |
| **Researcher loop** | ❌ NO | ✅ YES (auto-trigger on `needs_research`) |
| **Returns to Architect** | ❌ NO | ⚠️ INDIRECT (via STM context injection) |
| **Parallel execution** | ✅ YES (Dev/QA hardcoded) | ❌ NO (planned but not implemented) |
| **Tools available** | ✅ YES (injected via orchestrator) | ✅ YES (via LLMCallTool) |
| **Context passing** | ElisyaState (mutable) | STM (last 5 results) |
| **Task delegation** | Implicit (next phase) | Explicit (subtasks JSON) |
| **Model** | Dynamic routing | Fixed per agent (Claude/Grok) |

---

## 7. RECOMMENDED ACTIONS

### Priority 1: Architect Context Passing
```python
# In orchestrator_with_elisya.py:1604
dev_prompt += f"\n\n## Architect's Design:\n{result['architecture']}"
qa_prompt += f"\n\n## Architect's Design:\n{result['architecture']}"
```

### Priority 2: Enable Researcher Loop in Orchestrator
```python
# After line 1570 - Architect completes
if "@Researcher" in architect_result:
    # Extract research question
    question = extract_research_question(architect_result)
    research = await self._research_agent(question)
    # Re-run Architect with enriched context
    architect_prompt += f"\n\n## Research Findings:\n{research}"
    architect_result, elisya_state = await self._run_agent_with_elisya_async(
        "Architect", elisya_state, architect_prompt
    )
```

### Priority 3: Unify AgentPipeline and Orchestrator
- Use AgentPipeline's fractal approach as default
- Keep Legacy Orchestrator for backward compatibility
- Feature flag: `VETKA_USE_AGENT_PIPELINE=true`

---

## 8. KEY MARKERS FOR CODE NAVIGATION

| Marker | Location | Description |
|--------|----------|-------------|
| `orchestrator_with_elisya.py:1545-1588` | Architect execution in legacy flow | Main Architect entry point |
| `orchestrator_with_elisya.py:1589-1720` | Dev/QA parallel execution | Where parallel happens |
| `orchestrator_with_elisya.py:2788-2796` | Tool injection logic | CAM tools for all agents |
| `agent_pipeline.py:92-114` | Architect prompt template | JSON schema for subtasks |
| `agent_pipeline.py:440-458` | Researcher auto-trigger | needs_research loop |
| `agent_pipeline.py:285-306` | STM implementation | Context passing between subtasks |
| `role_prompts.py:237-334` | Architect system prompt | Role definition and tools |
| `vetka_architect.py:11-23` | VETKAArchitectAgent class | Minimal agent implementation |

---

## CONCLUSION

**Current State:**
- Architect works in 2 isolated systems (Legacy Orchestrator vs AgentPipeline)
- NO Researcher loop in production orchestrator
- Parallel execution hardcoded for Dev/QA only
- Context passing incomplete (Architect → Dev/QA gap)

**Future State (Phase 104+):**
- Unify both systems under AgentPipeline architecture
- Enable Researcher loop with adaptive confidence threshold
- Implement true parallel execution based on Architect's `execution_order`
- Full STM context passing across all agents

**Next Steps:**
1. Fix context gap (Priority 1)
2. Prototype Researcher loop in orchestrator (Priority 2)
3. Evaluate AgentPipeline for production use (Phase 105)
