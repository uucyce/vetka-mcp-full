# VETKA Dependency Map
**Last Updated:** 2026-01-04
**Phase:** 33

---

## Route → Handler → Template/React

### /3d (Main Visualization)
```
GET /3d
  → main.py:vetka_tree_3d()
  → src/visualizer/tree_renderer.py:render()
  → client/src/App.tsx (React)
```

### /api/chat (Chat API)
```
POST /api/chat
  → main.py:chat_api()
  → src/agents/hostess_agent.py:process()
  → src/orchestration/orchestrator_with_elisya.py
```

### /api/workflow/* (Workflow API)
```
POST /api/workflow/run
  → main.py:run_workflow()
  → src/orchestration/orchestrator_with_elisya.py
```

### /api/tree/* (Tree API)
```
GET /api/tree/nodes
  → src/server/routes/tree_routes.py:get_tree_nodes()
  → src/visualizer/tree_renderer.py
```

### /health (Health Check)
```
GET /health
  → src/server/routes/health_routes.py:health_check()
  → Memory Manager, Qdrant, Weaviate status
```

---

## Agent Dependencies

### hostess_agent.py (Entry Point)
- **Imports:** tools.py, role_prompts.py
- **Called by:** main.py (chat_api)
- **Calls:** PM, Dev, QA, Architect agents
- **Status:** ACTIVE

### eval_agent.py (Evaluation) - INTEGRATED Phase 34
- **Imports:** memory_manager.py, ollama
- **Called by:** orchestrator_with_elisya.py (`_evaluate_with_eval_agent`)
- **When:** After MERGE step, before OPS
- **Action:** Quality gate - scores output, logs feedback if score < 0.7
- **Status:** ACTIVE

### cam_engine.py (CAM Metrics) - INTEGRATED Phase 35
- **Imports:** memory_manager.py, numpy
- **Called by:** orchestrator_with_elisya.py
- **When:** After write_file/create_file/edit_file tool execution
- **Methods:** handle_new_artifact(), prune_low_entropy(), merge_similar_subtrees()
- **Status:** ACTIVE

### streaming_agent.py (WebSocket)
- **Imports:** base_agent.py
- **Called by:** orchestrator_with_elisya.py, agent_orchestrator.py
- **Wraps:** All VETKA agents for streaming
- **Status:** ACTIVE

### classifier_agent.py (Task Classification)
- **Imports:** (none from agents)
- **Called by:** src/orchestration/router.py
- **Status:** ACTIVE

---

## Orchestration Flow

```
User Message
    ↓
main.py:chat_api()
    ↓
hostess_agent.py:process()
    ↓
orchestrator_with_elisya.py:run_workflow()
    ↓
┌─────────────────────────────────────┐
│  PM Agent → plan                    │
│  Architect Agent → design           │
│  Dev Agent → implement              │
│    └─ ✅ CAM Engine (on file write) │  ← Phase 35
│  QA Agent → validate                │
│  MERGE → combine results            │
│  ✅ Eval Agent → quality gate       │  ← Phase 34
│  OPS → deployment                   │
└─────────────────────────────────────┘
    ↓
memory_manager.py:triple_write()
    ↓
Response to User
```

---

## Tool Dependencies

### tools.py (Main Tool Registry)
- **Defines:** BaseTool, ToolRegistry, 15+ tools
- **Used by:** All agents via AGENT_TOOL_PERMISSIONS matrix
- **Status:** ACTIVE

### agentic_tools.py (Agentic Loop)
- **Defines:** agentic_loop, tool_executor
- **Used by:** orchestrator_with_elisya.py, main.py
- **Status:** ACTIVE (merge candidate for Phase 36)

---

## Memory Dependencies

### memory_manager.py (Main Memory)
- **Provides:**
  - `triple_write()` - Write to changelog, Weaviate, Qdrant
  - `semantic_search()` - Vector similarity search (NEW!)
  - `search_similar()` - Find similar files
  - `get_similar_context()` - Context retrieval
- **Used by:** All agents, CAM engine, orchestrators

### qdrant_client.py (Vector DB)
- **Provides:** Qdrant connection management
- **Used by:** memory_manager.py
- **Status:** ACTIVE

### weaviate_helper.py (Graph DB)
- **Provides:** Weaviate connection management
- **Used by:** memory_manager.py
- **Status:** ACTIVE (but deprecated in favor of Qdrant)

---

## Learner System Dependencies

```
learner_factory.py (Factory)
    ↓
┌─────────────────────────────────────┐
│  base_learner.py (Abstract)         │
│  smart_learner.py (Main)            │
│  pixtral_learner.py (Pixtral)       │
│  qwen_learner.py (Qwen)             │
└─────────────────────────────────────┘
    ↓
learner_initializer.py (Setup)
```

**Called by:** main.py, components_init.py

---

## Critical Integrations Missing

### 1. Eval Agent Integration
```python
# Should be added to orchestrator_with_elisya.py after QA step:
from src.agents.eval_agent import EvalAgent

async def evaluate_output(self, output: str, task: str) -> float:
    eval_agent = EvalAgent()
    score = await eval_agent.evaluate(output, task)
    return score
```

### 2. CAM Engine Integration
```python
# Should be added to memory_manager.py on file creation:
from src.orchestration.cam_engine import calculate_surprise_metrics

def on_file_created(self, file_path: str, content: str):
    metrics = calculate_surprise_metrics(content)
    self.save_cam_metrics(file_path, metrics)
```

---

## File Count Summary (After Phase 32.9)

| Category | Count |
|----------|-------|
| src/agents/ | 23 |
| src/orchestration/ | 14 |
| src/memory/ | 7 |
| src/server/routes/ | 5 |
| client/src/ | 40+ |
| **Total Python** | ~200 |
| **Total TypeScript** | ~80 |

---

**End of Dependency Map**
