# Phase 104: Merge Implementation Guide
**Quick Reference for Code Changes**

---

## STEP 1: Add Feature Flag (5 min)

**File:** `src/orchestration/orchestrator_with_elisya.py`
**Location:** After line 117 (after FEATURE_FLAG_LANGGRAPH)

```python
# MARKER_104_ARCH_MERGE_4: Feature flag for Pipeline fractal loop
FEATURE_FLAG_PIPELINE_LOOP = (
    os.environ.get("VETKA_PIPELINE_ENABLED", "false").lower() == "true"
)

# Log feature flag status on module load
print(f"[Phase 104] FEATURE_FLAG_PIPELINE_LOOP = {FEATURE_FLAG_PIPELINE_LOOP}")
```

**In `__init__` (line ~170):**
```python
# Execution mode
self.use_parallel = use_parallel
# MARKER_104_ARCH_MERGE_4B: Add Pipeline loop flag
self.use_pipeline_loop = FEATURE_FLAG_PIPELINE_LOOP
```

---

## STEP 2: Add Imports (5 min)

**File:** `src/orchestration/orchestrator_with_elisya.py`
**Location:** After line 104 (after json import)

```python
# MARKER_104_ARCH_MERGE_11: Pipeline integration imports
from src.orchestration.agent_pipeline import (
    PipelineTask,
    Subtask,
    TASKS_FILE
)
from dataclasses import asdict
import re  # For robust JSON extraction
```

---

## STEP 3: Add Integration Hook (10 min)

**File:** `src/orchestration/orchestrator_with_elisya.py`
**Location:** Line ~1585 (after Architect completes, before PHASE 3: PARALLEL DEV & QA)

**FIND THIS BLOCK:**
```python
# ===== PHASE 2: ARCHITECT =====
print("\n2️⃣  ARCHITECT with Elisya...")
# ... Architect execution ...
print(f"   ✅ Architect completed in {result['metrics']['phases']['architect']:.1f}s")

# Phase 55.1: MCP state hook
try:
    mcp_bridge = get_mcp_state_bridge()
    await mcp_bridge.save_agent_state(workflow_id, "Architect", architect_result, elisya_state)
except Exception as e:
    print(f"   ⚠️ MCP Architect state save failed: {e}")

# ===== PHASE 3: PARALLEL DEV & QA =====  <-- INSERT BEFORE THIS LINE
```

**INSERT THIS CODE:**
```python
# MARKER_104_ARCH_MERGE_1: Pipeline fractal loop integration
if self.use_pipeline_loop:
    print("\n🔀 PIPELINE FRACTAL LOOP: Breaking down architecture into subtasks...")
    self._emit_status(workflow_id, "pipeline", "running")
    phase_start = time.time()

    try:
        pipeline_output, elisya_state, artifacts = await self._execute_pipeline_loop(
            architect_output=architect_result,
            elisya_state=elisya_state,
            workflow_id=workflow_id,
            phase_type="build"
        )

        # Store artifacts for approval gate
        result["pipeline_artifacts"] = artifacts
        result["pipeline_enriched_context"] = pipeline_output

        # Use pipeline output as input for Dev/QA
        dev_prompt = pipeline_output if pipeline_output else dev_prompt
        qa_prompt = pipeline_output if pipeline_output else qa_prompt

        result["metrics"]["phases"]["pipeline_loop"] = time.time() - phase_start
        self._emit_status(workflow_id, "pipeline", "done")
        print(f"   ✅ Pipeline completed in {result['metrics']['phases']['pipeline_loop']:.1f}s")
        print(f"   📦 Artifacts: {len(artifacts)} extracted, {len(pipeline_output)} chars context")

    except Exception as e:
        logger.error(f"[Pipeline] Loop failed: {e}")
        result["metrics"]["phases"]["pipeline_loop"] = time.time() - phase_start
        result["pipeline_error"] = str(e)
        self._emit_status(workflow_id, "pipeline", "error", error=str(e))
        # Continue to Dev/QA with Architect output (graceful degradation)
else:
    print("\n⏭️  PIPELINE LOOP: Disabled (using direct Architect → Dev/QA flow)")
```

---

## STEP 4: Add Core Methods (90 min)

**File:** `src/orchestration/orchestrator_with_elisya.py`
**Location:** End of file (after line ~2815, before final class closure)

### Method 1: Main Pipeline Loop

**NOTE:** Parallel subtask execution is ALREADY implemented in agent_pipeline.py!
- See `_execute_subtasks_parallel()` at lines 629-687
- Semaphore control: MAX_PARALLEL_PIPELINES=5 (lines 32-47)
- Markers: MARKER_104_PARALLEL_1 through MARKER_104_PARALLEL_5
- REUSE this code instead of re-implementing!

**For detailed parallel execution design and constraints, see:** [PARALLEL_EXECUTION_PLAN.md](./PARALLEL_EXECUTION_PLAN.md)

```python
# MARKER_104_ARCH_MERGE_6: Pipeline fractal loop execution
async def _execute_pipeline_loop(
    self,
    architect_output: str,
    elisya_state: ElisyaState,
    workflow_id: str,
    phase_type: str = "build"
) -> tuple:
    """
    Execute Pipeline-style fractal task decomposition with Elisya integration.

    Replaces standalone AgentPipeline.execute() but uses Legacy's
    _run_agent_with_elisya_async() for all LLM calls.

    Args:
        architect_output: Architect's design to break down into subtasks
        elisya_state: Current ElisyaState (preserved across subtasks)
        workflow_id: Workflow ID for tracking
        phase_type: "research" | "fix" | "build"

    Returns:
        (merged_output, updated_elisya_state, artifacts_list)
    """
    # 1. Initialize Pipeline task
    task_id = f"pipeline_{workflow_id}"
    pipeline_task = PipelineTask(
        task_id=task_id,
        task=architect_output,
        phase_type=phase_type,
        status="planning",
        timestamp=time.time()
    )

    logger.info(f"[Pipeline] Starting fractal loop for: {architect_output[:50]}...")

    # 2. Break down into subtasks
    plan = await self._pipeline_architect_plan(architect_output, phase_type, elisya_state)
    pipeline_task.subtasks = [
        Subtask(**st) if isinstance(st, dict) else st
        for st in plan.get("subtasks", [])
    ]
    total_subtasks = len(pipeline_task.subtasks)
    logger.info(f"[Pipeline] Plan: {total_subtasks} subtasks, {plan.get('execution_order')}")

    # 3. Execute subtasks with STM + Elisya
    stm = []  # Short-term memory (last N results)
    artifacts = []

    for i, subtask in enumerate(pipeline_task.subtasks):
        logger.info(f"[Pipeline] Subtask {i+1}/{total_subtasks}: {subtask.description[:40]}...")

        # 3.1 Inject STM from previous subtasks
        if stm:
            stm_summary = "\n".join([
                f"- [{s['marker']}]: {s['result'][:200]}..."
                for s in stm[-3:]  # Last 3 for context
            ])
            if subtask.context is None:
                subtask.context = {}
            subtask.context["previous_results"] = stm_summary
            logger.debug(f"[Pipeline] Injected STM: {len(stm)} previous results")

        # 3.2 Auto-trigger research if needed
        if subtask.needs_research:
            subtask.status = "researching"
            logger.info(f"[Pipeline] Researching: {subtask.description[:30]}...")

            question = subtask.question or subtask.description
            research = await self._pipeline_research(question, elisya_state)

            if subtask.context is None:
                subtask.context = {}
            subtask.context.update(research)

            # Recursive research if confidence < 0.7
            if research.get("confidence", 1.0) < 0.7:
                logger.info(f"[Pipeline] Low confidence ({research['confidence']:.2f}), recursing...")
                for fq in research.get("further_questions", [])[:2]:
                    sub_research = await self._pipeline_research(fq, elisya_state)
                    enriched = subtask.context.get("enriched_context", "")
                    subtask.context["enriched_context"] = enriched + f"\n\nFollow-up:\n{sub_research.get('enriched_context', '')}"

        # 3.3 Execute subtask using Elisya
        subtask.status = "executing"
        subtask_prompt = self._build_subtask_prompt(subtask, phase_type)

        # Use Dev for build, Architect for research
        agent_type = "Dev" if phase_type in ["fix", "build"] else "Architect"

        elisya_state.speaker = agent_type
        subtask_result, elisya_state = await self._run_agent_with_elisya_async(
            agent_type,
            elisya_state,
            subtask_prompt
        )

        subtask.result = subtask_result
        subtask.status = "done"
        logger.info(f"[Pipeline] Subtask {i+1} done: {len(subtask_result)} chars")

        # 3.4 Extract code artifacts (Phase 103.4 logic)
        if phase_type == "build" and "```" in subtask_result:
            extracted = self._extract_code_blocks(subtask_result, subtask.marker or f"step_{i+1}")
            artifacts.extend(extracted)
            logger.info(f"[Pipeline] Extracted {len(extracted)} artifacts")

        # 3.5 Add to STM
        stm.append({
            "marker": subtask.marker or f"step_{i+1}",
            "result": subtask_result[:500]  # Truncate for efficiency
        })
        if len(stm) > 5:
            stm.pop(0)

    # 4. Compile merged output
    merged_output = "\n\n".join([
        f"## {st.marker or f'Step {i+1}'}: {st.description}\n{st.result}"
        for i, st in enumerate(pipeline_task.subtasks) if st.result
    ])

    pipeline_task.status = "done"
    pipeline_task.results = {
        "subtasks_completed": len([s for s in pipeline_task.subtasks if s.status == "done"]),
        "subtasks_total": total_subtasks,
        "artifacts_count": len(artifacts)
    }

    # 5. Save to pipeline_tasks.json
    self._save_pipeline_task(pipeline_task)

    logger.info(f"[Pipeline] Complete: {len(merged_output)} chars, {len(artifacts)} artifacts")
    return merged_output, elisya_state, artifacts
```

### Method 2: Architect Planning

```python
# MARKER_104_ARCH_MERGE_3: Pipeline architect planning with Elisya
async def _pipeline_architect_plan(
    self,
    task: str,
    phase_type: str,
    elisya_state: ElisyaState
) -> Dict[str, Any]:
    """
    Break down task into subtasks using Architect agent via Elisya.

    Replaces AgentPipeline._architect_plan() but uses _run_agent_with_elisya_async.

    Returns:
        {
            "subtasks": [{"description": str, "needs_research": bool, "marker": str}],
            "execution_order": "sequential"|"parallel",
            "estimated_complexity": "low"|"medium"|"high"
        }
    """
    system_prompt = """You are a task architect for VETKA project.
Break down the task into clear subtasks.
For any unclear part, mark it with needs_research=true and add a question.

Respond in STRICT JSON format:
{
    "subtasks": [
        {
            "description": "what to do",
            "needs_research": false,
            "question": null,
            "marker": "MARKER_104.X"
        },
        {
            "description": "unclear part",
            "needs_research": true,
            "question": "What is the best approach for X?",
            "marker": "MARKER_104.Y"
        }
    ],
    "execution_order": "sequential",
    "estimated_complexity": "low|medium|high"
}"""

    user_prompt = f"Phase type: {phase_type}\n\nTask to break down:\n{task}"

    # Call via Elisya (gets routing, tools, key management)
    elisya_state.speaker = "Architect"

    # Temporarily override system prompt for JSON response
    original_role = self.architect.role if hasattr(self, 'architect') else None
    try:
        plan_output, elisya_state = await self._run_agent_with_elisya_async(
            "Architect",
            elisya_state,
            user_prompt
        )

        # Extract JSON with robust parsing
        plan = self._extract_json_robust(plan_output)

        # Validate required fields
        if "subtasks" not in plan or not plan["subtasks"]:
            raise ValueError("No subtasks in plan")

        logger.info(f"[Pipeline] Architect plan: {len(plan['subtasks'])} subtasks")
        return plan

    except Exception as e:
        logger.warning(f"[Pipeline] Plan parse failed: {e}, using fallback")
        # Fallback: single subtask with research
        return {
            "subtasks": [
                {
                    "description": task,
                    "needs_research": True,
                    "question": f"How to implement: {task[:100]}?",
                    "marker": "MARKER_104.1"
                }
            ],
            "execution_order": "sequential",
            "estimated_complexity": "medium"
        }
```

### Method 3: Research Loop

```python
# MARKER_104_ARCH_MERGE_5: Pipeline researcher with Elisya
async def _pipeline_research(
    self,
    question: str,
    elisya_state: ElisyaState
) -> Dict[str, Any]:
    """
    Deep research on unclear subtask using Researcher agent via Elisya.

    Uses Grok or configured model for research-heavy tasks.

    Returns:
        {
            "insights": [str],
            "actionable_steps": [{"step": str, "needs_code": bool}],
            "enriched_context": str,
            "confidence": float,
            "further_questions": [str]  # If confidence < 0.7
        }
    """
    system_prompt = """You are a deep researcher for VETKA project.
Research the question thoroughly. Provide actionable insights.

Respond in STRICT JSON format:
{
    "insights": ["key finding 1", "key finding 2"],
    "actionable_steps": [
        {"step": "description", "needs_code": true, "marker": "MARKER_104.X"}
    ],
    "enriched_context": "key facts and recommendations for the coder",
    "confidence": 0.9,
    "further_questions": ["optional follow-up if confidence < 0.7"]
}"""

    user_prompt = f"Research this for VETKA project:\n\n{question}"

    # Use Architect agent with research-focused routing
    # (Could also use dedicated Researcher agent if available)
    elisya_state.speaker = "Architect"  # Or "Researcher" if exists

    try:
        research_output, elisya_state = await self._run_agent_with_elisya_async(
            "Architect",  # Use Architect for now
            elisya_state,
            user_prompt
        )

        # Extract JSON
        research = self._extract_json_robust(research_output)

        # Set defaults for missing fields
        if "insights" not in research:
            research["insights"] = ["See enriched_context"]
        if "enriched_context" not in research:
            research["enriched_context"] = research_output[:500]
        if "confidence" not in research:
            research["confidence"] = 0.7

        logger.info(f"[Pipeline] Research confidence: {research.get('confidence', 'N/A')}")
        return research

    except Exception as e:
        logger.warning(f"[Pipeline] Research parse failed: {e}, using fallback")
        # Fallback: raw text as context
        return {
            "insights": ["Research data available in enriched_context"],
            "actionable_steps": [],
            "enriched_context": research_output[:500] if 'research_output' in locals() else question,
            "confidence": 0.6,
            "further_questions": []
        }
```

### Method 4: Subtask Prompt Builder

```python
# MARKER_104_ARCH_MERGE_7: Build subtask prompt with context
def _build_subtask_prompt(self, subtask: Subtask, phase_type: str) -> str:
    """
    Build prompt for subtask execution with injected context.

    Includes:
    - Subtask description
    - Research context (if available)
    - Previous subtask results (STM)
    - Phase-specific guidance
    """
    parts = [f"# Subtask: {subtask.description}"]

    # Add marker
    if subtask.marker:
        parts.append(f"Marker: {subtask.marker}")

    # Add research context
    if subtask.context:
        if subtask.context.get("enriched_context"):
            parts.append(f"\n## Research Context:\n{subtask.context['enriched_context']}")

        if subtask.context.get("actionable_steps"):
            steps = "\n".join([
                f"- {s.get('step', s)}"
                for s in subtask.context["actionable_steps"]
            ])
            parts.append(f"\n## Actionable Steps:\n{steps}")

        if subtask.context.get("previous_results"):
            parts.append(f"\n## Previous Subtask Results:\n{subtask.context['previous_results']}")

    # Add phase guidance
    if phase_type == "build":
        parts.append("\n## Instructions:\nImplement this subtask. Provide code with clear markers.")
    elif phase_type == "fix":
        parts.append("\n## Instructions:\nFix the issue described. Include before/after code.")
    else:  # research
        parts.append("\n## Instructions:\nProvide analysis and recommendations.")

    return "\n".join(parts)
```

### Method 5: Code Extraction

```python
# MARKER_104_ARCH_MERGE_8: Extract code blocks from LLM response
def _extract_code_blocks(self, content: str, marker: str) -> List[Dict]:
    """
    Extract code blocks from LLM response for artifact staging.

    Returns list of artifacts:
    [
        {
            "code": str,
            "language": str,
            "marker": str,
            "filepath": str (optional)
        }
    ]
    """
    import re

    artifacts = []

    # Pattern: ```[lang]\ncode\n```
    pattern = r'```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```'
    matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)

    for i, match in enumerate(matches):
        lang = match.group('lang') or 'text'
        code = match.group('code').strip()

        if not code:
            continue

        # Try to extract filepath from description
        filepath = None
        filepath_match = re.search(
            r'(src/[^\s]+?\.(?:py|js|ts|tsx|md|json))',
            content,
            re.IGNORECASE
        )
        if filepath_match:
            filepath = filepath_match.group(1)

        artifacts.append({
            "code": code,
            "language": lang,
            "marker": f"{marker}_{i+1}" if i > 0 else marker,
            "filepath": filepath,
            "size": len(code)
        })

    logger.info(f"[Pipeline] Extracted {len(artifacts)} code blocks")
    return artifacts
```

### Method 6: Task Storage

```python
# MARKER_104_ARCH_MERGE_9: Save pipeline task to JSON
def _save_pipeline_task(self, task: PipelineTask):
    """Save pipeline task to data/pipeline_tasks.json."""
    try:
        # Load existing tasks
        if TASKS_FILE.exists():
            tasks = json.loads(TASKS_FILE.read_text())
        else:
            tasks = {}

        # Update task
        tasks[task.task_id] = asdict(task)

        # Save back
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TASKS_FILE.write_text(json.dumps(tasks, indent=2, default=str))

        logger.debug(f"[Pipeline] Saved task {task.task_id} to {TASKS_FILE}")

    except Exception as e:
        logger.warning(f"[Pipeline] Task save failed: {e}")
```

### Method 7: Robust JSON Extraction

```python
# MARKER_104_ARCH_MERGE_10: Robust JSON extraction from LLM
def _extract_json_robust(self, text: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM response with multiple fallback strategies.

    Handles:
    - Raw JSON
    - Markdown code blocks (```json)
    - JSON embedded in prose
    """
    import re

    if not text or not text.strip():
        return {}

    text = text.strip()

    # Try 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try 2: ```json ... ```
    json_block = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_block:
        try:
            return json.loads(json_block.group(1))
        except json.JSONDecodeError:
            pass

    # Try 3: ``` ... ```
    code_block = re.search(r'```\s*([\s\S]*?)\s*```', text)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    # Try 4: Find JSON object {...}
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Try 5: From first {
    first_brace = text.find('{')
    if first_brace != -1:
        try:
            return json.loads(text[first_brace:])
        except json.JSONDecodeError:
            pass

    logger.warning(f"[Pipeline] JSON extraction failed: {text[:100]}...")
    raise json.JSONDecodeError("No valid JSON found", text, 0)
```

---

## STEP 5: Enable Feature Flag (1 min)

**Terminal:**
```bash
# Enable Pipeline loop
export VETKA_PIPELINE_ENABLED=true

# Or add to .env
echo "VETKA_PIPELINE_ENABLED=true" >> .env
```

---

## STEP 6: Test (30 min)

### Test 1: Simple Task
```python
# In Python console or test file
from src.orchestration.orchestrator_with_elisya import OrchestratorWithElisya
import asyncio

orchestrator = OrchestratorWithElisya(use_parallel=True)

result = asyncio.run(
    orchestrator.execute_full_workflow_streaming(
        feature_request="Add logging to health_routes.py",
        workflow_id="test_simple"
    )
)

print(result.get("pipeline_artifacts"))  # Should be empty (no code needed)
print(result.get("pipeline_enriched_context")[:200])  # Should have context
```

### Test 2: Complex Task (with Research)
```python
result = asyncio.run(
    orchestrator.execute_full_workflow_streaming(
        feature_request="Implement voice emotion detection using latest ML models",
        workflow_id="test_complex"
    )
)

print(result.get("pipeline_artifacts"))  # Should have code blocks
print(len(result.get("pipeline_enriched_context", "")))  # Should be 1000+ chars
```

### Test 3: Verify Pipeline Task Storage
```bash
cat data/pipeline_tasks.json | jq '.["pipeline_test_simple"]'
cat data/pipeline_tasks.json | jq '.["pipeline_test_complex"].subtasks | length'
```

---

## TROUBLESHOOTING

### Issue: "PipelineTask not found"
**Fix:** Check import at top of file:
```python
from src.orchestration.agent_pipeline import PipelineTask, Subtask, TASKS_FILE
```

### Issue: "JSON extraction failed"
**Fix:** LLM not returning valid JSON. Check `_extract_json_robust()` logs and adjust prompts.

### Issue: "ElisyaState lost"
**Fix:** Ensure `elisya_state` is returned and reassigned after each call:
```python
result, elisya_state = await self._run_agent_with_elisya_async(...)
# NOT: result = await self._run_agent_with_elisya_async(...)
```

### Issue: "Pipeline loop too slow"
**Fix:** Reduce STM limit (line 3 in `_execute_pipeline_loop`):
```python
stm[-3:]  # Last 3 instead of 5
```

---

## VERIFICATION CHECKLIST

After implementation, verify:

- [ ] `VETKA_PIPELINE_ENABLED=true` in environment
- [ ] No errors on server startup
- [ ] Feature flag logged: `[Phase 104] FEATURE_FLAG_PIPELINE_LOOP = True`
- [ ] Simple task: 1 subtask, no research
- [ ] Complex task: 3+ subtasks, researcher triggered
- [ ] `data/pipeline_tasks.json` created and populated
- [ ] Artifacts extracted to `pipeline_artifacts` field
- [ ] Dev/QA still run in parallel after Pipeline
- [ ] ElisyaState preserved (check `result["elisya_path"]`)
- [ ] No regressions with `VETKA_PIPELINE_ENABLED=false`

---

**Estimated Time:** 2 hours (code) + 30 min (testing) = 2.5 hours total
**MARKERs:** `MARKER_104_ARCH_MERGE_1` through `MARKER_104_ARCH_MERGE_11`
