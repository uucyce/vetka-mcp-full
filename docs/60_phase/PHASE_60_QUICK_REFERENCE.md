# Phase 60: Quick Reference Guide

**For:** Developers implementing LangGraph integration
**Read time:** 3 minutes

---

## 1. File Locations (Copy-Paste Ready)

### Current Implementation
```
Orchestrator Entry:      src/orchestration/orchestrator_with_elisya.py:969
Main Workflow:           src/orchestration/orchestrator_with_elisya.py:1000 (_execute_parallel)
State Definition:        src/elisya/state.py (ElisyaState dataclass)
Agent Definitions:       src/agents/*.py (PM, Dev, QA, Architect)
Memory System:           src/orchestration/memory_manager.py
Eval Agent:              src/agents/eval_agent.py:242 (_evaluate_with_eval_agent)
CAM Integration:         src/orchestration/cam_engine.py
Group Chat Handler:      src/api/handlers/group_message_handler.py:66 (route_through_hostess)
Services:                src/orchestration/services/*.py
```

### Files to Create
```
New LangGraph Graph:     src/orchestration/langgraph_builder.py
Node Implementations:    src/orchestration/langgraph_nodes.py
Checkpointer:            src/orchestration/vetka_saver.py
Learner Agent:           src/agents/learner_agent.py
API Handler:             src/api/handlers/langgraph_handler.py
Tests:                   tests/langgraph/*.py
```

---

## 2. Current Workflow Flow

```
START
  ↓
execute_full_workflow_streaming() [line 969]
  ├─ _execute_parallel() [line 1000]  OR
  └─ _execute_sequential() [line 1523]
      ↓
      [1] PM Agent [line 1058]
          state = reframe(state, 'PM')
          output = call_agent('PM', ...)
          state = update(state, output, 'PM')
      ↓
      [2] Architect Agent [line 1260]
          Same pattern
      ↓
      [3] Dev + QA Parallel [line 1155]
          Both called together, results merged
      ↓
      [4] EvalAgent [line 1267]
          score = evaluate(workflow_output)
          if score >= 0.7: continue
          else: reject
      ↓
      [5] Approval Gate [line 1330]
          Get user approval (if score >= 0.7)
      ↓
      [6] OPS [line 1383]
          Deployment readiness
      ↓
      RETURN result [line 1521 or 1679]
```

---

## 3. Key State Fields (for LangGraph)

```python
from src.elisya.state import ElisyaState

# Primary fields to maintain
state.workflow_id          # Unique identifier
state.speaker              # Current agent ('PM'|'Dev'|'QA'|'Architect')
state.context              # Reframed context for current agent
state.raw_context          # Original unfiltered context
state.semantic_path        # Evolves as conversation progresses
state.conversation_history # List[ConversationMessage] - full history
state.few_shots            # List[FewShotExample] - for learning
state.retry_count          # Incremented on retry
state.score                # EvalAgent score (0-1)
state.execution_state      # Dict - phase-specific data

# For LangGraph checkpointing
state.timestamp            # When state was created
state.lod_level            # LOD filtering level
state.tint                 # Semantic coloring
```

---

## 4. Conversion Template: Node → LangGraph Node

### Before (Current):
```python
# orchestrator_with_elisya.py:1058
pm_result = await self.pm.execute(
    feature_request,
    state.context,
    model=routing['model']
)
result['pm_plan'] = pm_result
state.speaker = 'PM'
```

### After (LangGraph):
```python
# langgraph_nodes.py
async def pm_node(state: ElisyaState) -> ElisyaState:
    """PM Agent as LangGraph node"""

    # 1. Reframe context using middleware
    state = middleware.reframe(state, "PM")

    # 2. Run agent
    output = await orchestrator._run_agent_with_elisya_async(
        agent_type="PM",
        state=state,
        prompt=state.context
    )

    # 3. Update state
    state = middleware.update(state, output, "PM")
    state.pm_plan = output

    return state
```

---

## 5. Conditional Edge Template

### Before (Current):
```python
# orchestrator_with_elisya.py:1328
if eval_score >= 0.7:
    # proceed to approval
else:
    # reject workflow
```

### After (LangGraph):
```python
# langgraph_builder.py
def route_by_score(state: ElisyaState) -> str:
    """Route based on EvalAgent score"""
    if state.score >= 0.7:
        return "approval"
    else:
        return "rejected"

builder.add_conditional_edges(
    "eval",
    route_by_score,
    {
        "approval": "approval_node",
        "rejected": "reject_node"
    }
)
```

---

## 6. Service Wrapper Example

### Using APIKeyService as a node:
```python
async def prepare_keys_node(state: ElisyaState) -> ElisyaState:
    """Prepare API keys before agent execution"""

    routing = get_routing_for_task(state.context, state.speaker)
    api_key = key_service.get_or_rotate_key(routing['provider'])

    # Store in state for node to access
    state.api_key = api_key
    state.model_id = routing['model']

    return state
```

---

## 7. Checkpointer Template (VETKASaver)

```python
# vetka_saver.py
from langgraph.checkpoint.base import BaseCheckpointer
from src.orchestration.memory_manager import MemoryManager

class VETKASaver(BaseCheckpointer):
    """LangGraph Checkpointer using MemoryManager"""

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    def put(self, config, values):
        """Save checkpoint to memory system"""
        checkpoint_id = config['configurable']['thread_id']

        # Triple-write to memory
        self.memory.triple_write({
            'checkpoint_id': checkpoint_id,
            'workflow_id': values.workflow_id,
            'state': values.to_dict(),  # Need to add this method
            'timestamp': datetime.now(),
            'phase': values.speaker
        })

    def get(self, config):
        """Retrieve checkpoint from memory"""
        thread_id = config['configurable']['thread_id']

        # Get from ChangeLog (authoritative)
        checkpoint = self.memory.get_from_changelog(thread_id)

        return checkpoint['state']
```

---

## 8. Testing Checklist

```python
# tests/langgraph/test_nodes.py
def test_pm_node():
    """Test PM node execution"""
    state = ElisyaState(workflow_id="test", speaker="PM")
    result = asyncio.run(pm_node(state))
    assert result.speaker == "PM"
    assert len(result.pm_plan) > 0

def test_state_round_trip():
    """Test state survives checkpoint"""
    saver = VETKASaver(memory_manager)
    state = ElisyaState(...)
    saver.put(config, state)
    restored = saver.get(config)
    assert restored == state

def test_conditional_routing():
    """Test quality gate routing"""
    state = ElisyaState(score=0.8)
    route = route_by_score(state)
    assert route == "approval"

    state.score = 0.5
    route = route_by_score(state)
    assert route == "rejected"

def test_backwards_compatibility():
    """Old orchestrator still works"""
    result = asyncio.run(
        orchestrator.execute_full_workflow_streaming(
            "test feature"
        )
    )
    assert result['status'] == 'complete'
```

---

## 9. Phase 29 Integration (Retry Loop)

Once LangGraph is in place, adding retry becomes simple:

```python
# Phase 29 will add this:

# 1. Create retry node
async def retry_dev_node(state: ElisyaState) -> ElisyaState:
    """Retry Dev execution with EvalAgent feedback"""
    feedback = state.eval_feedback
    improved_prompt = f"{state.context}\n\nFeedback: {feedback}"

    # Re-execute Dev with improved prompt
    output = await orchestrator._run_agent_with_elisya_async(
        "Dev", state, improved_prompt
    )
    state = middleware.update(state, output, "Dev")
    state.retry_count += 1
    return state

# 2. Add conditional edge after eval
builder.add_conditional_edges(
    "eval",
    lambda s: "retry" if s.score < 0.7 and s.retry_count < 3 else "approval",
    {
        "retry": "retry_dev",
        "approval": "approval_node"
    }
)

# 3. Retry node loops back to eval
builder.add_edge("retry_dev", "eval")
```

---

## 10. Environment Setup

```bash
# Verify LangGraph installed
python3 -c "import langgraph; print(langgraph.__version__)"

# Should output: 0.2.45+ (or later)

# Test ElisyaState import
python3 -c "from src.elisya.state import ElisyaState; print('✅ ElisyaState ready')"

# Test MemoryManager
python3 -c "from src.orchestration.memory_manager import MemoryManager; print('✅ MemoryManager ready')"

# Verify all services
python3 -c "from src.orchestration.services import *; print('✅ All services ready')"
```

---

## 11. Debugging Tips

### Print Graph Structure
```python
graph = builder.compile()
print(graph.get_graph().draw_ascii())
```

### Check State at Each Node
```python
async def debug_pm_node(state: ElisyaState) -> ElisyaState:
    print(f"[DEBUG] Input state: {state}")
    result = await pm_node(state)
    print(f"[DEBUG] Output state: {result}")
    return result
```

### Stream Execution
```python
for output in graph.stream(initial_state, config):
    print(f"Output: {output}")
```

---

## 12. Common Pitfalls & Solutions

| Problem | Solution |
|---------|----------|
| **State not persisting** | Add `to_dict()`/`from_dict()` to ElisyaState |
| **Async errors** | All node functions must be `async def` |
| **Agent timeout** | Check AGENT_TIMEOUTS dict (line 90) |
| **Memory not saving** | Verify triple-write all 3 backends |
| **Score not updating** | Ensure EvalAgent runs before conditional |
| **State type errors** | Return ElisyaState, not dict |

---

## 13. Rollout Strategy

```bash
# Phase 60.1: Design (1 week)
# Phase 60.2: Implement (1 week)
# Phase 60.3: Test (1 week)
# Phase 60.4: Feature flag rollout

# Add feature flag to route
if feature_flag('use_langgraph'):
    result = await langgraph_graph.invoke(initial_state)
else:
    result = await orchestrator.execute_full_workflow_streaming(...)

# Gradual rollout:
# - 10% traffic → LangGraph
# - Monitor metrics
# - 50% if no issues
# - 100% when confident
# - Remove old orchestrator (Phase 61)
```

---

## 14. Key Line Numbers to Review

```
orchestrator_with_elisya.py:
  Line 969   - execute_full_workflow_streaming() [START]
  Line 1000  - _execute_parallel() [MAIN LOGIC]
  Line 1025  - ElisyaState creation
  Line 1058  - PM Agent execution
  Line 1155  - Dev + QA parallel
  Line 1260  - Architect Agent
  Line 1267  - EvalAgent integration
  Line 1328  - Quality gate (score >= 0.7)
  Line 1330  - Approval gate
  Line 1383  - OPS phase
  Line 1521  - Return result
  Line 1772  - call_agent() method

middleware.py:
  Line 72    - reframe() method
  Line 160+  - update() method

eval_agent.py:
  Line 35    - __init__
  Line 79    - evaluate() main logic
```

---

**Last Updated:** 2026-01-10
**Document Status:** Ready for Phase 60.1
**Confidence:** 95%
