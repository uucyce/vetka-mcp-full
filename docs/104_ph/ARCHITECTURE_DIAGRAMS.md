# Phase 104: Architecture Diagrams
**Visual Reference for Legacy + Pipeline Merge**

---

## 1. BEFORE vs AFTER

### BEFORE (Phase 103)

```
┌────────────────────────────────────────────────────────────┐
│                  Legacy Orchestrator                        │
│         (orchestrator_with_elisya.py)                      │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
         ┌──────────────────────────────────────┐
         │  PM → Architect → Dev||QA → Eval     │
         └──────────────────────────────────────┘
                  ✅ Parallel Dev/QA
                  ✅ Elisya state
                  ✅ Tool support
                  ❌ NO Researcher
                  ❌ NO fractal decomposition


┌────────────────────────────────────────────────────────────┐
│                   Agent Pipeline                            │
│             (agent_pipeline.py)                            │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
      ┌───────────────────────────────────────────┐
      │  Architect → Subtasks → Researcher loop   │
      └───────────────────────────────────────────┘
                  ✅ Fractal decomposition
                  ✅ Researcher auto-trigger
                  ✅ STM context passing
                  ❌ NO Elisya state
                  ❌ NO tool support
                  ❌ NO parallel execution
```

### AFTER (Phase 104)

```
┌────────────────────────────────────────────────────────────┐
│              UNIFIED HYBRID ORCHESTRATOR                    │
│         (orchestrator_with_elisya.py + Pipeline)           │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
    ┌────────────────────────────────────────────────┐
    │  PM → Architect → [PIPELINE LOOP] → Dev||QA   │
    │                       ↓                         │
    │              Fractal + Research                 │
    └────────────────────────────────────────────────┘
                  ✅ ALL Legacy features
                  ✅ ALL Pipeline features
                  ✅ Unified ElisyaState
                  ✅ Feature flag control
```

---

## 2. DETAILED EXECUTION FLOW

### Phase 104 Hybrid Workflow

```
USER REQUEST
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: PM AGENT                                           │
│   Input: User request                                       │
│   Output: High-level plan                                   │
│   Method: _run_agent_with_elisya_async("PM", ...)          │
└─────────────────────────────────────────────────────────────┘
     │ ElisyaState + PM plan
     ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: ARCHITECT AGENT                                    │
│   Input: PM plan                                            │
│   Output: Architecture design                               │
│   Method: _run_agent_with_elisya_async("Architect", ...)   │
└─────────────────────────────────────────────────────────────┘
     │ ElisyaState + Architecture
     ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: PIPELINE FRACTAL LOOP                              │
│ (NEW - controlled by VETKA_PIPELINE_ENABLED)                │
│                                                              │
│  ┌────────────────────────────────────────────────┐         │
│  │ Step 1: Architect Planning                     │         │
│  │   _pipeline_architect_plan()                   │         │
│  │   ├─ Break architecture into subtasks          │         │
│  │   ├─ Mark unclear parts needs_research=True    │         │
│  │   └─ Output: [Subtask1, Subtask2, Subtask3]   │         │
│  └────────────────────────────────────────────────┘         │
│              │                                               │
│              ▼                                               │
│  ┌────────────────────────────────────────────────┐         │
│  │ Step 2: Execute Subtasks (SEQUENTIAL)         │         │
│  │                                                │         │
│  │  FOR EACH subtask:                             │         │
│  │                                                │         │
│  │  ┌──────────────────────────────────────┐     │         │
│  │  │ 2a. Inject STM Context               │     │         │
│  │  │   "Previous results: [...]"          │     │         │
│  │  └──────────────────────────────────────┘     │         │
│  │              │                                 │         │
│  │              ▼                                 │         │
│  │  ┌──────────────────────────────────────┐     │         │
│  │  │ 2b. IF needs_research == True:       │     │         │
│  │  │   _pipeline_research(question)       │     │         │
│  │  │   ├─ Call via Elisya                 │     │         │
│  │  │   ├─ Get enriched context            │     │         │
│  │  │   └─ IF confidence < 0.7:            │     │         │
│  │  │       └─ Recursive research (max 2)  │     │         │
│  │  └──────────────────────────────────────┘     │         │
│  │              │                                 │         │
│  │              ▼                                 │         │
│  │  ┌──────────────────────────────────────┐     │         │
│  │  │ 2c. Execute Subtask                  │     │         │
│  │  │   _run_agent_with_elisya_async()     │     │         │
│  │  │   ├─ Agent: Dev (build) or Architect │     │         │
│  │  │   ├─ Prompt: description + context   │     │         │
│  │  │   └─ Output: code/analysis           │     │         │
│  │  └──────────────────────────────────────┘     │         │
│  │              │                                 │         │
│  │              ▼                                 │         │
│  │  ┌──────────────────────────────────────┐     │         │
│  │  │ 2d. Extract Artifacts                │     │         │
│  │  │   IF phase == "build":               │     │         │
│  │  │     _extract_code_blocks()           │     │         │
│  │  │     └─ Extract ```code``` blocks     │     │         │
│  │  └──────────────────────────────────────┘     │         │
│  │              │                                 │         │
│  │              ▼                                 │         │
│  │  ┌──────────────────────────────────────┐     │         │
│  │  │ 2e. Update STM                       │     │         │
│  │  │   stm.append({marker, result})       │     │         │
│  │  │   Keep last 5 results                │     │         │
│  │  └──────────────────────────────────────┘     │         │
│  │                                                │         │
│  │  NEXT SUBTASK →                                │         │
│  └────────────────────────────────────────────────┘         │
│              │                                               │
│              ▼                                               │
│  ┌────────────────────────────────────────────────┐         │
│  │ Step 3: Compile Results                        │         │
│  │   merged_output = join(all subtask results)    │         │
│  │   artifacts = [code blocks from all subtasks]  │         │
│  └────────────────────────────────────────────────┘         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
     │ ElisyaState + Enriched context + Artifacts
     ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: MERGE PIPELINE RESULTS                             │
│   Use pipeline output as input for Dev/QA                   │
│   Store artifacts for approval gate                         │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 5: DEV || QA PARALLEL EXECUTION                       │
│   asyncio.gather(                                           │
│     run_dev_async(),  # Uses pipeline output                │
│     run_qa_async()    # Uses pipeline output                │
│   )                                                          │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 6-8: EVAL → APPROVE → OPS                             │
│   (Existing Legacy flow unchanged)                          │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
  RESULT
```

---

## 3. AGENT INVOCATION COMPARISON

### Legacy Method (Before)

```python
# Direct agent call - no decomposition, no research
async def _execute_parallel(self, feature_request, workflow_id):
    # PM
    pm_result, state = await self._run_agent_with_elisya_async(
        "PM", elisya_state, feature_request
    )

    # Architect
    architect_result, state = await self._run_agent_with_elisya_async(
        "Architect", elisya_state, pm_result
    )

    # Dev & QA (parallel)
    dev, qa = await asyncio.gather(
        self._run_agent_with_elisya_async("Dev", state, pm_result),
        self._run_agent_with_elisya_async("QA", state, feature_request)
    )
```

**Problem:** Architect output → Dev input (single pass, no breakdown)

### Pipeline Method (Before)

```python
# Fractal decomposition - but no Elisya state
async def execute(self, task, phase_type):
    # Architect breaks down
    plan = await self._architect_plan(task, phase_type)
    # Uses LLMCallTool (NOT Elisya)

    # Execute subtasks
    for subtask in plan["subtasks"]:
        if subtask.needs_research:
            research = await self._research(subtask.question)
            # Uses LLMCallTool (NOT Elisya)

        result = await self._execute_subtask(subtask)
        # Uses LLMCallTool (NOT Elisya)
```

**Problem:** No Elisya state → loses context, no tools

### Hybrid Method (Phase 104)

```python
# Best of both worlds
async def _execute_pipeline_loop(self, architect_output, elisya_state, ...):
    # 1. Break down (via Elisya)
    plan = await self._pipeline_architect_plan(architect_output, ..., elisya_state)
    # Uses _run_agent_with_elisya_async → Elisya + tools

    # 2. Execute subtasks (via Elisya + STM)
    for subtask in plan["subtasks"]:
        # 2a. Research if needed (via Elisya)
        if subtask.needs_research:
            research = await self._pipeline_research(question, elisya_state)
            # Uses _run_agent_with_elisya_async → Elisya + tools

        # 2b. Execute (via Elisya + injected context)
        result, elisya_state = await self._run_agent_with_elisya_async(
            "Dev", elisya_state, subtask_prompt
        )
        # Full Elisya features + STM context
```

**Result:** Fractal decomposition + research loop + Elisya state + tools

---

## 4. STATE MANAGEMENT

### ElisyaState Flow

```
USER REQUEST
     │
     ▼
┌─────────────────┐
│  ElisyaState    │
│  context: ""    │  <─── Created at workflow start
│  messages: []   │
└─────────────────┘
     │
     ▼ PM agent
┌─────────────────┐
│  ElisyaState    │
│  context: "PM"  │  <─── Updated after PM
│  messages: [PM] │
└─────────────────┘
     │
     ▼ Architect agent
┌─────────────────┐
│  ElisyaState    │
│  context: "Arc" │  <─── Updated after Architect
│  messages: [..]│
└─────────────────┘
     │
     ▼ PIPELINE LOOP
     │
     ├─ Subtask 1 (via Elisya)
     │   └─ ElisyaState updated
     │
     ├─ Research (if needed, via Elisya)
     │   └─ ElisyaState updated
     │
     ├─ Subtask 2 (via Elisya)
     │   └─ ElisyaState updated
     │
     └─ Subtask 3 (via Elisya)
         └─ ElisyaState updated
     │
     ▼ Dev||QA agents
┌─────────────────┐
│  ElisyaState    │
│  context: "Full"│  <─── All context preserved
│  messages: [...]│
└─────────────────┘
```

### STM (Short-Term Memory) Flow

```
PIPELINE LOOP STARTS
     │
     stm = []  <─── Empty at start
     │
     ▼
Subtask 1: "Create config.py"
     │ result: "# config.py\nSETTINGS = {...}"
     ▼
stm = [{
    "marker": "MARKER_104.1",
    "result": "# config.py\nSETTINGS = {...}"
}]
     │
     ▼
Subtask 2: "Create utils.py"
     │ INJECT: "Previous results: [MARKER_104.1]: # config.py..."
     │ result: "# utils.py\nfrom config import SETTINGS"
     ▼
stm = [
    {"marker": "MARKER_104.1", "result": "# config.py..."},
    {"marker": "MARKER_104.2", "result": "# utils.py..."}
]
     │
     ▼
Subtask 3: "Create main.py"
     │ INJECT: "Previous results:
     │          [MARKER_104.1]: # config.py...
     │          [MARKER_104.2]: # utils.py..."
     │ result: "# main.py\nfrom utils import *"
     ▼
stm = [
    {"marker": "MARKER_104.1", "result": "..."},
    {"marker": "MARKER_104.2", "result": "..."},
    {"marker": "MARKER_104.3", "result": "..."}
]
     │
     ▼ (Keep only last 5)
stm[-3:] used for next subtask context
```

**Key:** STM allows later subtasks to reference earlier code without re-calling LLM.

---

## 5. RESEARCHER AUTO-TRIGGER

### Without Research (Simple Task)

```
Subtask: "Add logging to health_routes.py"
    ├─ needs_research: False
    ├─ context: {}
    └─ Execute directly
        └─ Output: "import logging\nlogger.info(...)"
```

### With Research (Complex Task)

```
Subtask: "Implement voice emotion detection"
    ├─ needs_research: True
    ├─ question: "What ML models are best for voice emotion?"
    │
    ▼ RESEARCHER TRIGGERED
    │
    ├─ _pipeline_research("What ML models...")
    │   ├─ Call LLM with research prompt
    │   ├─ Inject semantic search results
    │   └─ Return:
    │       {
    │         "insights": ["SER models like..."],
    │         "enriched_context": "Use librosa + LSTM...",
    │         "confidence": 0.85,
    │         "actionable_steps": [...]
    │       }
    │
    ▼ confidence >= 0.7 → PROCEED
    │
    ├─ context updated with research
    └─ Execute subtask with enriched context
        └─ Output: "import librosa\nmodel = LSTM(...)"
```

### With Recursive Research (Low Confidence)

```
Subtask: "Optimize VETKA memory architecture"
    ├─ needs_research: True
    ├─ question: "Best memory architecture for AI agents?"
    │
    ▼ RESEARCHER TRIGGERED
    │
    ├─ _pipeline_research(...)
    │   └─ Return: {confidence: 0.6}  <─── LOW!
    │
    ▼ confidence < 0.7 → RECURSE
    │
    ├─ further_questions: [
    │     "What are VETKA's current memory bottlenecks?",
    │     "How does Qdrant compare to Weaviate for agent memory?"
    │   ]
    │
    ├─ _pipeline_research("What are VETKA's bottlenecks?")
    │   └─ enriched_context += "Current bottleneck: Qdrant sync..."
    │
    ├─ _pipeline_research("Qdrant vs Weaviate...")
    │   └─ enriched_context += "Qdrant better for..."
    │
    ▼ NOW confidence high enough
    │
    └─ Execute subtask with 3x enriched context
        └─ Output: "Optimize Qdrant by batching upserts..."
```

**Maximum recursion depth:** 2 (prevents infinite loops)

---

## 6. ARTIFACT EXTRACTION FLOW

### Code Block Detection

```
LLM Response:
"Here's the implementation:

```python
# src/voice/emotion.py
import librosa

def detect_emotion(audio_path):
    # Load audio
    y, sr = librosa.load(audio_path)
    # Extract features...
```

This uses librosa for feature extraction."

     ▼ _extract_code_blocks()
     │
     ├─ Regex: ```(?P<lang>\w+)?\s*\n(?P<code>.*?)\n```
     │
     └─ Extract:
         {
           "code": "# src/voice/emotion.py\nimport librosa...",
           "language": "python",
           "marker": "MARKER_104.3",
           "filepath": "src/voice/emotion.py",  <─── Extracted from code
           "size": 245
         }

     ▼ Stored in result["pipeline_artifacts"]
     │
     ▼ Approval Gate (Phase 55)
     │
User reviews artifact → Approve/Reject
     │
     ▼ If approved: Write to disk
```

---

## 7. FEATURE FLAG CONTROL

### Disabled (Legacy Mode)

```bash
export VETKA_PIPELINE_ENABLED=false
```

```
PM → Architect → Dev||QA → Eval
     ↑
   Direct flow (no Pipeline loop)
```

**Use when:**
- Simple tasks
- No research needed
- Testing Legacy changes
- Debugging approval gate

### Enabled (Hybrid Mode)

```bash
export VETKA_PIPELINE_ENABLED=true
```

```
PM → Architect → [PIPELINE LOOP] → Dev||QA → Eval
                      ↑
                Fractal + Research
```

**Use when:**
- Complex/ambiguous tasks
- Research needed
- Multi-step implementation
- Learning new domains

---

## 8. DATA FLOW DIAGRAM

```
┌─────────────┐
│ User Input  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│           orchestrator_with_elisya.py        │
│                                              │
│  ┌────────────────────────────────────┐     │
│  │ PM Agent                           │     │
│  │  Input: user_request               │     │
│  │  Output: pm_plan                   │     │
│  └────────┬───────────────────────────┘     │
│           │                                  │
│           ▼                                  │
│  ┌────────────────────────────────────┐     │
│  │ Architect Agent                    │     │
│  │  Input: pm_plan                    │     │
│  │  Output: architecture              │     │
│  └────────┬───────────────────────────┘     │
│           │                                  │
│           ▼                                  │
│  ┌────────────────────────────────────┐     │
│  │ IF VETKA_PIPELINE_ENABLED:         │     │
│  │                                    │     │
│  │  ┌──────────────────────────┐     │     │
│  │  │ Pipeline Loop            │     │     │
│  │  │  (agent_pipeline.py)     │     │     │
│  │  │                          │     │     │
│  │  │  ┌────────────────┐     │     │     │
│  │  │  │ Break down     │     │     │     │
│  │  │  │ architecture   │     │     │     │
│  │  │  └───────┬────────┘     │     │     │
│  │  │          │               │     │     │
│  │  │          ▼               │     │     │
│  │  │  ┌────────────────┐     │     │     │
│  │  │  │ For subtask:   │     │     │     │
│  │  │  │  - Research?   │     │     │     │
│  │  │  │  - Execute     │     │     │     │
│  │  │  │  - Extract     │     │     │     │
│  │  │  │  - Update STM  │     │     │     │
│  │  │  └───────┬────────┘     │     │     │
│  │  │          │               │     │     │
│  │  │  [Loop]  │               │     │     │
│  │  │          │               │     │     │
│  │  │          ▼               │     │     │
│  │  │  ┌────────────────┐     │     │     │
│  │  │  │ Merge results  │     │     │     │
│  │  │  └───────┬────────┘     │     │     │
│  │  │          │               │     │     │
│  │  └──────────┼───────────────┘     │     │
│  │             │                     │     │
│  │             ▼                     │     │
│  │    enriched_context +            │     │
│  │    artifacts                     │     │
│  │                                  │     │
│  └────────┬─────────────────────────┘     │
│           │                                │
│           ▼                                │
│  ┌────────────────────────────────────┐   │
│  │ Dev || QA Parallel                 │   │
│  │  Input: pipeline_output OR arch    │   │
│  │  Output: dev_result, qa_result     │   │
│  └────────┬───────────────────────────┘   │
│           │                                │
└───────────┼────────────────────────────────┘
            │
            ▼
    ┌───────────────┐
    │ Eval → Approve│
    │ → Ops → Done  │
    └───────────────┘
```

---

## 9. MARKER LOCATIONS

### orchestrator_with_elisya.py

```
Line 115:  MARKER_104_ARCH_MERGE_4 (Feature flag)
Line 170:  MARKER_104_ARCH_MERGE_4B (Flag in __init__)
Line 104:  MARKER_104_ARCH_MERGE_11 (Imports)
Line 1585: MARKER_104_ARCH_MERGE_1 (Integration hook)
Line 2820: MARKER_104_ARCH_MERGE_6 (_execute_pipeline_loop)
Line 2920: MARKER_104_ARCH_MERGE_3 (_pipeline_architect_plan)
Line 2980: MARKER_104_ARCH_MERGE_5 (_pipeline_research)
Line 3040: MARKER_104_ARCH_MERGE_7 (_build_subtask_prompt)
Line 3080: MARKER_104_ARCH_MERGE_8 (_extract_code_blocks)
Line 3120: MARKER_104_ARCH_MERGE_9 (_save_pipeline_task)
Line 3140: MARKER_104_ARCH_MERGE_10 (_extract_json_robust)
```

### agent_pipeline.py

```
Line 60: MARKER_104_ARCH_MERGE_2 (Deprecation notice)
```

---

**Created by:** Claude Opus 4.5
**Phase:** 104 ARCHITECTURE MERGE
**Status:** VISUAL REFERENCE COMPLETE
