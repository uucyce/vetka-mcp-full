# Phase 76 Integration Markers - Learning System

## 🎯 Quick Reference

| Component | Status | File | Lines | Marker |
|-----------|--------|------|-------|--------|
| EvalAgent | ✅ Active | langgraph_nodes.py | 580-700 | [M-02] |
| LearnerAgent | ✅ Active | langgraph_nodes.py | 706-808 | [M-04] |
| HOPE | ⚠️ Ready | hope_enhancer.py | 37-150 | [M-09] |
| ARC | ✅ Ready | orchestrator.py | 1468-1505 | [M-08] |

---

## 📍 MARKER LOCATIONS

### [M-01] EvalAgent Initialization
**File**: `src/orchestration/langgraph_nodes.py`
**Line**: 110-122
**Type**: Property definition
```python
@property
def eval_agent(self) -> EvalAgent:
    if self._eval_agent is None:
        self._eval_agent = EvalAgent()
    return self._eval_agent
```

### [M-02] eval_node() Implementation
**File**: `src/orchestration/langgraph_nodes.py`
**Lines**: 580-700
**Action**: Full eval pipeline - reads Dev+QA output, scores, routes
**Trigger**: After dev_qa_parallel_node
**Output**: eval_score, eval_feedback, next=(approval|learner)

### [M-03] EVAL_THRESHOLD Constant
**File**: `src/orchestration/langgraph_nodes.py`
**Line**: 79
**Value**: 0.75
**Usage**: Score threshold for pass/fail decision

### [M-04] learner_node() Implementation
**File**: `src/orchestration/langgraph_nodes.py`
**Lines**: 706-808
**Action**: Analyze failure, generate enhanced_prompt, store lessons
**Trigger**: When score < 0.75 AND retry_count < max_retries
**Output**: enhanced_prompt (→ dev context), lessons_learned, retry_count++

### [M-05] Learner Entry Point
**File**: `src/orchestration/langgraph_nodes.py`
**Line**: 744
```python
failure_analysis = self.learner.analyze_failure(
    task=state["raw_context"],
    dev_output=dev_output,
    eval_feedback=eval_feedback,
    retry_attempt=state["retry_count"]
)
```

### [M-06] ARC Import
**File**: `src/orchestration/orchestrator_with_elisya.py`
**Line**: 72
```python
from src.agents.arc_solver_agent import ARCSolverAgent
```

### [M-07] ARC Initialization
**File**: `src/orchestration/orchestrator_with_elisya.py`
**Lines**: 207-217
```python
self.arc_solver = ARCSolverAgent(
    model_name="deepseek-chat",
    semantic_index=self.semantic_index,
    logger=logger
)
```

### [M-08] ARC Execution
**File**: `src/orchestration/orchestrator_with_elisya.py`
**Lines**: 1468-1505
**When**: POST-workflow (after approval_node)
**Input**: Workflow result, graph data, task context
**Output**: Creative suggestions for future similar tasks

### [M-09] HOPE Integration Point
**File**: `src/agents/hope_enhancer.py`
**Lines**: 37-150
**Proposed**: Insert BETWEEN pm_node AND dev_qa_parallel_node
**Usage**:
```python
hope = HOPEEnhancer()
analysis = hope.analyze(
    content=pm_output,
    complexity=state['lod_level'],
    cache_key=workflow_id
)
```

### [M-10] HOPE in LangGraph
**Proposal**: New node `hope_enhancement_node`
**Insert after**: pm_node
**Insert before**: dev_qa_parallel_node
**Flow**: PM output → HOPE analysis → Dev+QA context

### [M-11] retry_count Field
**File**: `src/orchestration/langgraph_state.py`
**Line**: 67
**Type**: int (0-based)
**Usage**: Tracks retry attempts

### [M-12] max_retries Field
**File**: `src/orchestration/langgraph_state.py`
**Line**: 68
**Type**: int (default: 3)
**Usage**: Max retry limit before forced approval

### [M-13] Retry Decision Logic
**File**: `src/orchestration/langgraph_nodes.py`
**Lines**: 659-671
```
if score >= 0.75:
    next = "approval"
elif retry_count < max_retries:
    next = "learner"
else:
    next = "approval" (with warning)
```

### [M-14] retry_count Increment
**File**: `src/orchestration/langgraph_nodes.py`
**Line**: 782
```python
state["retry_count"] = state.get("retry_count", 0) + 1
```

### [M-15] enhanced_prompt Usage
**File**: `src/orchestration/langgraph_nodes.py`
**Lines**: 486-498
**On retry**: enhanced_prompt from LearnerAgent injected into combined_context
```python
if state["retry_count"] > 0:
    combined_context += f"""
### ⚠️ RETRY #{retry_count}
{enhanced_prompt}  ← From LearnerAgent
"""
```

### [M-16] Lessons Learned Storage
**File**: `src/orchestration/langgraph_nodes.py`
**Lines**: 871-883 (approval_node)
**Artifact type**: "lesson_learned"
**Fields**: workflow_id, task, failure_reason, suggestion, retry_attempt, final_score

### [M-17] Eval Conditional Edges
**File**: `src/orchestration/langgraph_builder.py`
**Lines**: 149-156
**Type**: LangGraph conditional_edge
**Router**: _route_from_eval()

### [M-18] Route Decision Function
**File**: `src/orchestration/langgraph_builder.py`
**Lines**: 207-228
```python
def _route_from_eval(state: VETKAState) -> str:
    if state['eval_score'] >= EVAL_THRESHOLD:
        return "approval"
    elif state['retry_count'] < state['max_retries']:
        return "learner"
    return "approval"
```

### [M-19] Learner Loop Back
**File**: `src/orchestration/langgraph_builder.py`
**Line**: 159
**Edge**: learner → dev_qa_parallel (retry loop)

### [M-20] Workflow Counter
**Proposal**: Track for LoRA fine-tuning every 50 workflows
**Location**: TBD (orchestrator.execute_with_langgraph)
**Purpose**: Trigger LoRA training checkpoint

### [M-21] Replay Buffer
**Proposal**: Store high-value lessons for training
**Location**: TBD (memory_service or new)
**Pattern**: 80/20 (80% recent failures, 20% hard examples)

### [M-22] Learning History Storage
**Location**: TBD (qdrant or new collection)
**Data**: lessons_learned artifacts + workflow metadata
**Query**: Retrieve similar patterns for new tasks

### [M-23] EVAL_THRESHOLD
**File**: `src/orchestration/langgraph_nodes.py`
**Line**: 79
**Value**: 0.75 (from Grok research)
**Critical**: Do NOT change without research

### [M-24] MAX_RETRIES
**File**: `src/orchestration/langgraph_state.py`
**Line**: 68
**Default**: 3
**Configurable**: Via create_initial_state() parameter

---

## 🔄 Data Flow

```
Dev+QA Output
    ↓ [M-02]
EvalAgent (score)
    ├─ score ≥ 0.75 → Approval [M-17]
    └─ score < 0.75 → [M-13] Check retry_count
                      ├─ retry < max → LearnerAgent [M-04]
                      │   ├─ analyze_failure [M-05]
                      │   ├─ generate enhanced_prompt
                      │   ├─ store lessons [M-16]
                      │   ├─ increment retry [M-14]
                      │   └─ loop to dev_qa [M-19]
                      │       ↓ [M-15]
                      │   (retry with enhanced_prompt)
                      └─ retry ≥ max → Approval (with warning)
```

---

## ⚠️ NOT YET INTEGRATED

| Component | Status | Notes |
|-----------|--------|-------|
| LoRA Fine-tuning | ❌ 0% | Needs workflow counter [M-20] |
| Replay Buffer | ❌ 0% | Need storage decision [M-21] |
| Learning History | ⚠️ 50% | Lessons stored, but not queried |
| HOPE in LangGraph | ⚠️ 20% | Module ready, needs [M-10] node |
| Agent Teams | ❌ 0% | Separate research needed |

---

## 🚀 Phase 76 Roadmap

### Phase 76.1: Markers & Analysis (DONE ✓)
- [x] All markers identified
- [x] Integration points located
- [x] Data flow documented

### Phase 76.2: HOPE Integration (5h)
- [ ] Create hope_enhancement_node [M-10]
- [ ] Insert between pm_node and dev_qa_parallel_node
- [ ] Test hope analysis output

### Phase 76.3: Learning System Validation (3h)
- [ ] Verify eval_node logic [M-02]
- [ ] Verify learner_node logic [M-04]
- [ ] Test retry loop [M-19]
- [ ] Test enhanced_prompt injection [M-15]

### Phase 76.4: Counter System (5h)
- [ ] Implement workflow counter [M-20]
- [ ] Create Replay Buffer [M-21]
- [ ] Implement learning history queries [M-22]

### Phase 76.5: LoRA Integration (10h)
- [ ] Connect counter to LoRA training
- [ ] Fine-tune on high-value lessons
- [ ] A/B test fine-tuned vs base models

---

**Status**: ✅ **READY FOR PHASE 76 IMPLEMENTATION**
**Markers**: 24 identified + line numbers
**Files to modify**: 5 (langgraph_nodes.py, langgraph_builder.py, state, orchestrator, hope)
**Effort**: ~23 hours total (Phase 76.1-76.5)

---

**Created**: 2026-01-20
**For**: Claude Code Opus 4.5
**Prepared by**: Claude Code Haiku 4.5
