# Phase 104: Architecture Merge Plan
**Legacy Orchestrator + AgentPipeline Integration**

**Date:** 2026-01-31
**Status:** ANALYSIS COMPLETE
**Priority:** P0 - Foundation for Phase 105+

---

## Executive Summary

**Problem:** Two parallel agent orchestration systems with complementary strengths:
- **Legacy (`orchestrator_with_elisya.py`):** PM → Architect → Dev||QA parallel, NO Researcher loop
- **Pipeline (`agent_pipeline.py`):** Architect → Researcher loop, STM, but parallel NOT implemented

**Solution:** Hybrid architecture - inject Pipeline's fractal decomposition + research loop INTO Legacy's proven parallel execution framework.

**Impact:** Unified system with:
- PM → Architect → **[Pipeline Fractal Loop]** → Dev||QA parallel
- Researcher auto-triggers on unclear subtasks
- STM (Short-Term Memory) context passing between subtasks
- Preserved Elisya state, tool support, approval gates

---

## 1. CURRENT STATE ANALYSIS

### 1.1 Legacy Orchestrator (2815 lines)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`

#### Agent Invocation Method
```python
# Line 1221-1370: _run_agent_with_elisya_async()
async def _run_agent_with_elisya_async(
    self,
    agent_type: str,
    state: ElisyaState,
    prompt: str,
    **kwargs
) -> tuple:
    """
    ASYNC Run LLM call with Elisya middleware and Tool support.
    Phase 19: Includes response formatting with source citations.
    """
    # 1. Reframe context via Elisya middleware
    state = self.elisya_service.reframe_context(state, agent_type)

    # 2. Get routing (ModelRouter or manual override)
    routing = self._get_routing_for_task(...)

    # 3. Inject API key to environment
    api_key = self._inject_api_key(routing)

    # 4. Execute LLM with tool loop
    llm_response = await self._call_llm_with_tools_loop(
        prompt=prompt,
        agent_type=agent_type,
        model=model_name,
        system_prompt=system_prompt,
        provider=provider_enum
    )

    # 5. Format response with source citations
    output = ResponseFormatter.add_source_citations(output, sources)

    # 6. Update ElisyaState
    state = self._update_state(state, agent_type, output)

    return output, state
```

#### Workflow Structure (Line 1439-1789)
```python
async def _execute_parallel(self, feature_request: str, workflow_id: str):
    # PHASE 1: PM → Planning
    pm_result, elisya_state = await self._run_agent_with_elisya_async(
        "PM", elisya_state, pm_prompt
    )
    chain.add_step(agent="PM", input_msg=pm_prompt, output=pm_result)

    # PHASE 2: ARCHITECT → Design
    # MARKER_103_CHAIN1: Architect NOT added to chain (BUG)
    architect_result, elisya_state = await self._run_agent_with_elisya_async(
        "Architect", elisya_state, architect_prompt
    )

    # PHASE 3: DEV || QA → Parallel Execution (asyncio.gather)
    dev_qa_results = await asyncio.gather(
        run_dev_async(),  # Calls _run_agent_with_elisya_async
        run_qa_async()
    )

    # PHASE 4: MERGE → Combine results
    # PHASE 5: EVAL → EvalAgent scoring
    # PHASE 6: APPROVAL → User approval gate
    # PHASE 7: OPS → Deployment
```

#### Strengths
✅ **Parallel execution:** Dev||QA via `asyncio.gather()` (Phase 103 fix)
✅ **Elisya integration:** Full state management, middleware, semantic paths
✅ **Tool support:** camera_focus, search_semantic, get_tree_context
✅ **Response formatting:** Source citations (Phase 19)
✅ **Chain context:** PM → Architect → Dev → QA (Phase 17-K)
✅ **Approval gate:** User review before file writes (Phase 55)
✅ **EvalAgent:** Quality scoring (Phase 34)
✅ **Key rotation:** Auto-retry on 401/429 errors

#### Weaknesses
❌ **No Researcher agent:** Can't handle unclear requirements
❌ **No fractal decomposition:** Single-level task breakdown
❌ **No STM:** Context lost between PM → Architect → Dev
❌ **Hardcoded flow:** PM → Architect → Dev||QA (inflexible)

---

### 1.2 Agent Pipeline (768 lines)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/agent_pipeline.py`

#### Agent Invocation Method
```python
# Line 504-562: _architect_plan()
async def _architect_plan(self, task: str, phase_type: str) -> Dict[str, Any]:
    """Architect breaks down task into subtasks with needs_research flags."""
    tool = self._get_llm_tool()  # LLMCallTool from MCP

    # LLMCallTool.execute is SYNCHRONOUS
    result = tool.execute({
        "model": "anthropic/claude-sonnet-4",
        "messages": [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": f"Phase type: {phase_type}\n\nTask: {task}"}
        ],
        "temperature": 0.3,
        "max_tokens": 2000
    })

    # Extract JSON plan
    plan = self._extract_json(result["result"]["content"])
    return plan

# Line 566-634: _research()
async def _research(self, question: str) -> Dict[str, Any]:
    """Grok researcher - deep dive on unclear subtasks."""
    result = tool.execute({
        "model": "x-ai/grok-4",
        "messages": [
            {"role": "system", "content": researcher_prompt},
            {"role": "user", "content": f"Research: {question}"}
        ],
        "inject_context": {
            "semantic_query": question,
            "semantic_limit": 5
        }
    })

    research = self._extract_json(result["result"]["content"])
    # Returns: insights, actionable_steps, enriched_context, confidence
    return research

# Line 638-720: _execute_subtask()
async def _execute_subtask(self, subtask: Subtask, phase_type: str) -> str:
    """Execute subtask with context from research."""
    # Inject research context into prompt
    context_str = subtask.context.get("enriched_context", "")

    result = tool.execute({
        "model": "anthropic/claude-sonnet-4",
        "messages": [
            {"role": "system", "content": coder_prompt},
            {"role": "user", "content": f"""
                Subtask: {subtask.description}
                Marker: {subtask.marker}
                {context_str}
                Execute this subtask.
            """}
        ]
    })

    # Phase 103.4: Extract code blocks and write files
    if phase_type == "build" and self.auto_write:
        files_created = self._extract_and_write_files(content, subtask)

    return content
```

#### Workflow Structure (Line 386-500)
```python
async def execute(self, task: str, phase_type: str = "research"):
    """Fractal pipeline: Task → Subtasks → Sub-searches."""

    # PHASE 1: Architect breaks down task
    plan = await self._architect_plan(task, phase_type)
    pipeline_task.subtasks = [Subtask(**st) for st in plan["subtasks"]]

    # PHASE 2: Execute each subtask (SEQUENTIAL)
    self.stm = []  # Reset STM
    for i, subtask in enumerate(pipeline_task.subtasks):
        # Inject STM from previous subtasks
        if self.stm:
            subtask.context["previous_results"] = self._get_stm_summary()

        # Auto-trigger research if needs_research=True
        if subtask.needs_research:
            question = subtask.question or subtask.description
            research = await self._research(question)
            subtask.context.update(research)

            # Recursive research if confidence < 0.7
            if research["confidence"] < 0.7:
                for follow_up in research["further_questions"][:2]:
                    sub_research = await self._research(follow_up)
                    subtask.context["enriched_context"] += sub_research["enriched_context"]

        # Execute subtask with enriched context
        result = await self._execute_subtask(subtask, phase_type)
        subtask.result = result

        # Add to STM for next subtask
        self._add_to_stm(subtask.marker, result)

    # PHASE 3: Compile results
    return asdict(pipeline_task)
```

#### Strengths
✅ **Fractal decomposition:** Architect → Subtasks → Recursive Research
✅ **Researcher loop:** Auto-triggered on `needs_research=True`
✅ **STM (Short-Term Memory):** Last 5 subtask results passed to next step
✅ **Confidence-based recursion:** Follow-up research if confidence < 0.7
✅ **Code extraction:** Auto-write files from code blocks (Phase 103.4)
✅ **Progress streaming:** Emits to group chat via HTTP POST
✅ **MARKERs:** All code annotated with MARKER_102.X

#### Weaknesses
❌ **No Elisya state:** Lost context between subtasks
❌ **No tool support:** camera_focus, semantic search unavailable
❌ **No parallel execution:** Subtasks run SEQUENTIAL (flag exists but not used)
❌ **No approval gate:** Auto-writes without user review
❌ **LLMCallTool only:** Can't use Elisya middleware or ModelRouter
❌ **Synchronous LLM calls:** `tool.execute()` is sync, wrapped in async

---

## 2. INTEGRATION POINTS

### 2.1 Shared Imports

Both systems import from:
```python
# Common agent classes
from src.agents import VETKAPMAgent, VETKADevAgent, VETKAQAAgent, VETKAArchitectAgent

# Common utilities
from src.orchestration.progress_tracker import ProgressTracker
from src.orchestration.memory_manager import MemoryManager
```

### 2.2 Common Agent Interface

**BaseAgent** (Line 35-150 in `base_agent.py`):
```python
class BaseAgent:
    def __init__(self, role: str, token_budget: Optional[int] = None):
        self.role = role
        self.name = role
        self.model = "ollama/llama3.2:1b"

    def call_llm(self, prompt: str, context: str = "", max_tokens: Optional[int] = None) -> str:
        """Call LLM using best available provider."""
        provider_info = self._get_best_provider()
        # Routes to OpenRouter/Gemini/Ollama
        return response
```

**Problem:** Pipeline bypasses `BaseAgent.call_llm()` and uses `LLMCallTool.execute()` instead.

### 2.3 State Management Conflict

| Component | Legacy | Pipeline |
|-----------|--------|----------|
| **State object** | `ElisyaState` (conversation history) | `PipelineTask` (subtasks list) |
| **Memory** | `ElisyaState.context` (reframed per agent) | `AgentPipeline.stm` (last 5 results) |
| **Tools** | Via `_call_llm_with_tools_loop()` | Not available |
| **Routing** | `ModelRouter` + `APIKeyService` | Hardcoded model names |
| **Approval** | Phase 55 approval gate | Auto-write (skippable) |

---

## 3. PROPOSED HYBRID ARCHITECTURE

### 3.1 Design Principle

**INJECT Pipeline INTO Legacy, not replace.**

```
Legacy Workflow (BEFORE):
PM → Architect → Dev||QA → Eval → Approve → Ops

Hybrid Workflow (AFTER):
PM → Architect → [PIPELINE LOOP] → Merge → Dev||QA → Eval → Approve → Ops
                      ↑
                Fractal decomposition
                Researcher auto-trigger
                STM context passing
```

### 3.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   Legacy Orchestrator                        │
│  (orchestrator_with_elisya.py)                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PHASE 1: PM (Planning)                                     │
│    ├─ _run_agent_with_elisya_async("PM", ...)              │
│    └─ Output: High-level plan                               │
│                                                              │
│  PHASE 2: Architect (Design)                                │
│    ├─ _run_agent_with_elisya_async("Architect", ...)       │
│    └─ Output: Architecture design                           │
│                                                              │
│  ┌─────────────────────────────────────────────┐            │
│  │ PHASE 3: PIPELINE FRACTAL LOOP (NEW)       │            │
│  │ (agent_pipeline.py integrated)              │            │
│  ├─────────────────────────────────────────────┤            │
│  │                                              │            │
│  │  Step 1: Break down Architect output        │            │
│  │    └─ _architect_plan() → Subtasks          │            │
│  │                                              │            │
│  │  Step 2: For each subtask (SEQUENTIAL):     │            │
│  │    ├─ Inject STM from previous subtask      │            │
│  │    ├─ IF needs_research:                    │            │
│  │    │   └─ _research() → Enriched context    │            │
│  │    ├─ _execute_subtask_with_elisya()        │            │
│  │    │   └─ Uses _run_agent_with_elisya_async │            │
│  │    └─ Add result to STM                     │            │
│  │                                              │            │
│  │  Step 3: Compile results                    │            │
│  │    └─ Merged output for Dev/QA              │            │
│  │                                              │            │
│  └─────────────────────────────────────────────┘            │
│                                                              │
│  PHASE 4: Merge Pipeline Results                            │
│    └─ Combine enriched context + code artifacts            │
│                                                              │
│  PHASE 5: Dev||QA (Parallel Execution)                     │
│    ├─ asyncio.gather(run_dev_async, run_qa_async)         │
│    └─ Uses Pipeline output as input                        │
│                                                              │
│  PHASE 6: Eval → Approve → Ops                             │
│    └─ Existing Legacy flow                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Key Integration Point

**NEW METHOD:** `_execute_pipeline_loop()`

Insert between Architect and Dev/QA in `orchestrator_with_elisya.py`:

```python
# MARKER_104_ARCH_MERGE_1: Pipeline integration hook
async def _execute_pipeline_loop(
    self,
    architect_output: str,
    elisya_state: ElisyaState,
    workflow_id: str,
    phase_type: str = "build"
) -> tuple[str, ElisyaState, List[Dict]]:
    """
    Execute Pipeline fractal loop with Elisya state preservation.

    Replaces AgentPipeline.execute() but uses Legacy's agent invocation.

    Args:
        architect_output: Architect's design to break down
        elisya_state: Current ElisyaState (preserved across subtasks)
        workflow_id: Workflow ID for tracking
        phase_type: "research" | "fix" | "build"

    Returns:
        (merged_output, updated_elisya_state, artifacts_list)
    """
    # 1. Initialize Pipeline-style task storage
    task_id = f"pipeline_{workflow_id}"
    pipeline_task = PipelineTask(
        task_id=task_id,
        task=architect_output,
        phase_type=phase_type,
        status="planning"
    )

    # 2. Break down into subtasks (reuse Pipeline's _architect_plan logic)
    plan = await self._pipeline_architect_plan(architect_output, phase_type)
    pipeline_task.subtasks = [Subtask(**st) for st in plan["subtasks"]]

    # 3. Execute subtasks with STM + Elisya state
    stm = []  # Short-term memory
    artifacts = []

    for i, subtask in enumerate(pipeline_task.subtasks):
        # 3.1 Inject STM context
        if stm:
            stm_summary = "\n".join([f"[{s['marker']}]: {s['result'][:200]}..." for s in stm[-3:]])
            subtask.context["previous_results"] = stm_summary

        # 3.2 Auto-trigger research if needed
        if subtask.needs_research:
            research = await self._pipeline_research(
                subtask.question or subtask.description,
                elisya_state
            )
            subtask.context.update(research)

        # 3.3 Execute subtask using Legacy's Elisya-enabled agent call
        # THIS IS THE KEY: Replace LLMCallTool with _run_agent_with_elisya_async
        subtask_prompt = self._build_subtask_prompt(subtask, phase_type)

        # Use "Dev" agent for build phase, "Architect" for research phase
        agent_type = "Dev" if phase_type in ["fix", "build"] else "Architect"

        subtask_result, elisya_state = await self._run_agent_with_elisya_async(
            agent_type,
            elisya_state,
            subtask_prompt
        )

        subtask.result = subtask_result
        subtask.status = "done"

        # 3.4 Extract artifacts (Phase 103.4 logic)
        if phase_type == "build" and "```" in subtask_result:
            extracted = self._extract_code_blocks(subtask_result, subtask.marker)
            artifacts.extend(extracted)

        # 3.5 Add to STM
        stm.append({"marker": subtask.marker, "result": subtask_result})
        if len(stm) > 5:
            stm.pop(0)

    # 4. Compile merged output
    merged_output = "\n\n".join([
        f"## {st.marker}: {st.description}\n{st.result}"
        for st in pipeline_task.subtasks if st.result
    ])

    pipeline_task.status = "done"
    self._save_pipeline_task(pipeline_task)

    return merged_output, elisya_state, artifacts
```

---

## 4. IMPLEMENTATION ROADMAP

### Phase 104.1: Preparation (1 hour)

**Files to modify:**
1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`
   - Add `MARKER_104_ARCH_MERGE_1` comment at line ~1580 (after Architect, before Dev/QA)
   - Import `PipelineTask`, `Subtask` from `agent_pipeline.py`

2. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/agent_pipeline.py`
   - Mark methods as `@staticmethod` where possible for reuse
   - Add `MARKER_104_ARCH_MERGE_2` to extraction methods

**Code snippet (orchestrator_with_elisya.py, line ~1580):**
```python
# MARKER_104_ARCH_MERGE_1: Pipeline integration point
# After Architect completes, before Dev/QA parallel execution
# INSERT _execute_pipeline_loop() call here

# EXISTING CODE:
architect_result, elisya_state = await self._run_agent_with_elisya_async(
    "Architect", elisya_state, architect_prompt
)

# NEW CODE (insert after above):
if self.use_pipeline_loop:  # Feature flag
    print("\n🔀 PIPELINE FRACTAL LOOP: Breaking down architecture...")
    pipeline_output, elisya_state, artifacts = await self._execute_pipeline_loop(
        architect_output=architect_result,
        elisya_state=elisya_state,
        workflow_id=workflow_id,
        phase_type="build"
    )
    # Store artifacts for approval gate
    result["pipeline_artifacts"] = artifacts
else:
    pipeline_output = architect_result  # Passthrough if disabled
```

### Phase 104.2: Core Methods (3 hours)

**Add to `orchestrator_with_elisya.py`:**

1. `_execute_pipeline_loop()` (60 lines) - Main integration method
2. `_pipeline_architect_plan()` (40 lines) - Reuse Pipeline's breakdown logic but call via Elisya
3. `_pipeline_research()` (50 lines) - Researcher loop with Elisya state
4. `_build_subtask_prompt()` (30 lines) - Format subtask + context into prompt
5. `_extract_code_blocks()` (40 lines) - Extract artifacts (reuse Pipeline's logic)
6. `_save_pipeline_task()` (20 lines) - Store to `data/pipeline_tasks.json`

**Example: _pipeline_architect_plan()**
```python
# MARKER_104_ARCH_MERGE_3: Pipeline-style planning with Elisya
async def _pipeline_architect_plan(
    self,
    task: str,
    phase_type: str,
    elisya_state: ElisyaState
) -> Dict[str, Any]:
    """
    Break down task into subtasks using Architect agent + Elisya.
    Replaces AgentPipeline._architect_plan() but uses Elisya routing.
    """
    # Build planning prompt
    system_prompt = """You are a task architect for VETKA project.
Break down the task into clear subtasks.
For any unclear part, mark it with needs_research=true and add a question.

Respond in STRICT JSON format:
{
    "subtasks": [
        {"description": "...", "needs_research": false, "marker": "MARKER_104.X"},
        {"description": "...", "needs_research": true, "question": "...", "marker": "MARKER_104.Y"}
    ],
    "execution_order": "sequential",
    "estimated_complexity": "low|medium|high"
}"""

    user_prompt = f"Phase type: {phase_type}\n\nTask to break down:\n{task}"

    # Call via Elisya (gets tool support, routing, key management)
    elisya_state.speaker = "Architect"
    plan_output, elisya_state = await self._run_agent_with_elisya_async(
        "Architect",
        elisya_state,
        user_prompt,
        system_prompt_override=system_prompt
    )

    # Extract JSON
    try:
        plan = self._extract_json_robust(plan_output)
        if "subtasks" not in plan:
            raise ValueError("No subtasks in plan")
        return plan
    except Exception as e:
        logger.warning(f"[Pipeline] Plan parse failed: {e}")
        # Fallback: single subtask
        return {
            "subtasks": [{"description": task, "needs_research": True, "marker": "MARKER_104.1"}],
            "execution_order": "sequential",
            "estimated_complexity": "medium"
        }
```

### Phase 104.3: Integration Testing (2 hours)

**Test cases:**

1. **Simple task (no research needed):**
   ```
   Input: "Add logging to health_routes.py"
   Expected: 1 subtask, needs_research=False, direct execution
   ```

2. **Complex task (requires research):**
   ```
   Input: "Implement voice emotion detection using latest ML models"
   Expected: 3-4 subtasks, 1-2 with needs_research=True, Researcher auto-triggers
   ```

3. **Parallel Dev/QA after Pipeline:**
   ```
   Input: "Refactor group chat triggers with fallback routing"
   Expected: Pipeline outputs enriched context → Dev/QA run in parallel with full context
   ```

**Validation:**
- Check `data/pipeline_tasks.json` for stored subtasks
- Verify ElisyaState preserved across subtasks
- Confirm STM injection in subtask prompts
- Ensure artifacts extracted and staged for approval

### Phase 104.4: Feature Flag (1 hour)

**Add to `orchestrator_with_elisya.py` init:**
```python
# MARKER_104_ARCH_MERGE_4: Feature flag for Pipeline loop
FEATURE_FLAG_PIPELINE_LOOP = os.environ.get("VETKA_PIPELINE_ENABLED", "false").lower() == "true"

class OrchestratorWithElisya:
    def __init__(self, ...):
        # ...
        self.use_pipeline_loop = FEATURE_FLAG_PIPELINE_LOOP

        if is_first_init:
            print(f"[Phase 104] FEATURE_FLAG_PIPELINE_LOOP = {self.use_pipeline_loop}")
```

**Environment variable:**
```bash
# Enable Pipeline loop (Phase 104+)
export VETKA_PIPELINE_ENABLED=true

# Disable (use Legacy flow only)
export VETKA_PIPELINE_ENABLED=false
```

### Phase 104.5: Cleanup (1 hour)

1. **Deprecate standalone pipeline usage:**
   - Mark `AgentPipeline.execute()` with `@deprecated` annotation
   - Update MCP tools to use `orchestrator.execute_full_workflow_streaming()` instead

2. **Update documentation:**
   - `docs/104_ph/ARCHITECTURE_MERGE_PLAN.md` (this doc)
   - `docs/104_ph/PIPELINE_MIGRATION_GUIDE.md` (user-facing)
   - Add markers to all modified files

3. **Archive old orchestrators:**
   - Move `agent_orchestrator.py` to `backup/phase_104/`
   - Move `agent_orchestrator_parallel.py` to `backup/phase_104/`
   - Keep only `orchestrator_with_elisya.py` as canonical

---

## 5. CODE CHANGES CHECKLIST

### 5.1 Files to Modify

| File | Lines to Change | Markers |
|------|----------------|---------|
| `orchestrator_with_elisya.py` | ~1580-1590 (insert hook) | `MARKER_104_ARCH_MERGE_1` |
| `orchestrator_with_elisya.py` | ~2800+ (add 6 new methods) | `MARKER_104_ARCH_MERGE_3-8` |
| `agent_pipeline.py` | Line 60 (add deprecation warning) | `MARKER_104_ARCH_MERGE_2` |
| `orchestrator_with_elisya.py` | Line 115 (add feature flag) | `MARKER_104_ARCH_MERGE_4` |

### 5.2 Methods to Add

```python
# MARKER_104_ARCH_MERGE_3
async def _pipeline_architect_plan(...) -> Dict[str, Any]

# MARKER_104_ARCH_MERGE_5
async def _pipeline_research(...) -> Dict[str, Any]

# MARKER_104_ARCH_MERGE_6
async def _execute_pipeline_loop(...) -> tuple

# MARKER_104_ARCH_MERGE_7
def _build_subtask_prompt(...) -> str

# MARKER_104_ARCH_MERGE_8
def _extract_code_blocks(...) -> List[Dict]

# MARKER_104_ARCH_MERGE_9
def _save_pipeline_task(...) -> None

# MARKER_104_ARCH_MERGE_10
def _extract_json_robust(...) -> Dict  # Reuse Pipeline's extraction
```

### 5.3 Imports to Add

```python
# MARKER_104_ARCH_MERGE_11: Add to orchestrator_with_elisya.py imports
from src.orchestration.agent_pipeline import (
    PipelineTask,
    Subtask,
    TASKS_FILE  # data/pipeline_tasks.json path
)
from dataclasses import asdict
import re  # For JSON extraction
```

---

## 6. MIGRATION STRATEGY

### Option A: Pipeline Inside Legacy (RECOMMENDED)

**Pros:**
- Preserves all Legacy features (Elisya, tools, approval)
- Adds Pipeline's fractal decomposition as enhancement
- No breaking changes to existing workflows
- Feature flag allows gradual rollout

**Cons:**
- orchestrator_with_elisya.py grows to ~3200 lines
- Need to maintain two orchestration modes

**Decision:** This is the chosen approach (as described above)

### Option B: Migrate Legacy to Pipeline

**Pros:**
- Clean slate, simpler codebase
- Pipeline is only 768 lines vs Legacy's 2815

**Cons:**
- Would lose Elisya state management (critical for context)
- Would lose tool support (camera_focus, semantic search)
- Would lose approval gate (Phase 55)
- High risk of regression

**Decision:** Rejected - too risky

### Option C: Parallel Systems

**Pros:**
- No integration work needed
- Each system optimized for its use case

**Cons:**
- Confusing for users (which to use?)
- Duplicate maintenance burden
- Context can't transfer between systems

**Decision:** Rejected - creates technical debt

---

## 7. RISK MITIGATION

### Risk 1: ElisyaState Lost During Subtasks
**Mitigation:** Pass `elisya_state` through entire Pipeline loop, update after each subtask

### Risk 2: STM Conflicts with Elisya Context
**Mitigation:** STM is transient (last 5 results), Elisya is persistent (full conversation). They complement.

### Risk 3: Tool Calls in Researcher Agent
**Mitigation:** Researcher uses same `_run_agent_with_elisya_async()` → gets full tool access

### Risk 4: Parallel Execution After Pipeline
**Mitigation:** Pipeline outputs merged result → Dev/QA receive it as single input (no race condition)

### Risk 5: Approval Gate Bypass
**Mitigation:** Pipeline artifacts stored, approval gate checks `result["pipeline_artifacts"]` before writes

---

## 8. SUCCESS METRICS

### Phase 104 Complete When:

✅ **Feature flag working:** `VETKA_PIPELINE_ENABLED=true` activates Pipeline loop
✅ **Fractal decomposition:** Architect output broken into 3+ subtasks
✅ **Researcher auto-trigger:** `needs_research=True` subtasks get enriched context
✅ **STM injection:** Subtask prompts include previous results
✅ **ElisyaState preserved:** No context loss across subtasks
✅ **Tool support:** camera_focus, semantic search work in Researcher
✅ **Parallel Dev/QA:** Still runs after Pipeline completes
✅ **Approval gate:** Pipeline artifacts staged, not auto-written
✅ **No regressions:** Legacy flow (VETKA_PIPELINE_ENABLED=false) still works

### Performance Targets:

- **Overhead:** Pipeline loop adds max 20% to total workflow time
- **Context quality:** Subtasks have 2x more relevant context (via STM + research)
- **Task success rate:** +15% for complex/ambiguous tasks

---

## 9. ALTERNATIVE CONSIDERED: Reverse Integration

**Pipeline as orchestrator, call Legacy for individual agents:**

```python
# In agent_pipeline.py
async def _execute_subtask(self, subtask, phase_type):
    # Instead of LLMCallTool, use Legacy's agent invocation
    from orchestrator_with_elisya import OrchestratorWithElisya

    orchestrator = OrchestratorWithElisya()
    result, state = await orchestrator._run_agent_with_elisya_async(
        agent_type="Dev",
        state=self.elisya_state,
        prompt=subtask.description
    )
    return result
```

**Why rejected:**
- Pipeline doesn't have PM → Architect flow (only Architect → Subtasks)
- No approval gate, EvalAgent, or Ops phase
- Would require rebuilding all Legacy features in Pipeline
- Higher risk of breaking existing workflows

---

## 10. NEXT STEPS

### Immediate (Phase 104):
1. Add MARKERs to integration points (30 min)
2. Implement `_execute_pipeline_loop()` (3 hours)
3. Add feature flag (1 hour)
4. Test with simple/complex tasks (2 hours)
5. Update docs (1 hour)

**Total: ~8 hours (1 working day)**

### Phase 105 (Future):
- Implement parallel subtask execution (currently sequential)
- Add MAX_PARALLEL_PIPELINES semaphore (prevent overload)
- Integrate Researcher feedback into Chain Context
- Add Pipeline metrics to VETKA-JSON output

### Phase 106 (Future):
- AI-powered subtask prioritization (reorder based on dependencies)
- Dynamic research depth (adjust recursion based on task complexity)
- Cross-workflow STM (remember patterns across different tasks)

---

## 11. SUMMARY

**Problem:** Two complementary orchestration systems operating in parallel
**Solution:** Inject Pipeline's fractal loop INTO Legacy's proven infrastructure
**Result:** Unified system with best of both worlds

**Key Innovation:** `_run_agent_with_elisya_async()` becomes the universal agent invocation method, used by both Legacy flow AND Pipeline subtasks.

**Migration Path:** Feature flag → Gradual rollout → Deprecate standalone Pipeline → Single source of truth

**Timeline:** Phase 104.1-104.5 = 8 hours
**Risk Level:** Medium (mitigated by feature flag + extensive testing)
**Impact:** High (enables complex task automation with research loop)

---

**Prepared by:** Claude Opus 4.5
**Phase:** 104 ARCHITECTURE MERGE
**Status:** READY FOR IMPLEMENTATION
**Markers:** `MARKER_104_ARCH_MERGE_1` through `MARKER_104_ARCH_MERGE_11`
