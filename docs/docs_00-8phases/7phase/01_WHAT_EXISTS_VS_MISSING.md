# 🏗️ VETKA PHASE 7: WHAT EXISTS vs WHAT'S MISSING

## СЛОЙ 1: USER REQUEST → AUTOGEN

### ✅ ЧТО ЕСТЬ:
- `main.py` → Flask + Socket.IO configured
- POST `/api/workflow/start` endpoint exists
- `workflow_started` Socket.IO event

### ❌ ЧТО НУЖНО:
- [ ] Request parsing into ElisyaState
- [ ] Queue management for concurrent workflows
- [ ] Autogen initialization in request handler

---

## СЛОЙ 2: AUTOGEN GroupChat

### ✅ ЧТО ЕСТЬ:
- 5 агентов написаны: PM, Dev, QA, Architect, EvalAgent
- Каждый = LLM вызов к Ollama
- Agents в `src/agents/`:
  - `pm_agent.py` → VETKAPMAgent
  - `dev_agent.py` → VETKADevAgent
  - `qa_agent.py` → VETKAQAAgent
  - `architect_agent.py` → VETKAArchitectAgent
  - `eval_agent.py` → EvalAgent

### ❌ ЧТО НУЖНО:
- [ ] **СОЗДАТЬ: `src/autogen_integration/`** ← новая директория
- [ ] `agents_config.py` — Autogen AssistantAgent setup
- [ ] `groupchat_wrapper.py` — VetkaGroupChat manager
- [ ] `message_handler.py` — Autogen → Elisyа converter
- [ ] Ollama LLM config для Autogen

---

## СЛОЙ 3: ELISYА STATE (SHARED MEMORY)

### ✅ ЧТО ЕСТЬ:
- `context_manager.py` в `src/elisya_integration/` (LOD, budget)
- `VetkaParallelState` в `src/workflows/langgraph_nodes.py` (TypedDict)

### ❌ ЧТО НУЖНО:
- [ ] **СОЗДАТЬ: `src/elisya/`** ← новая директория
- [ ] `state.py` — **ElisyaState dataclass** (расширить VetkaParallelState):
  ```python
  @dataclass
  class ElisyaState:
      workflow_id: str
      speaker: str  # PM|Dev|QA|Architect|EvalAgent
      semantic_path: str  # projects/python/ml/sklearn
      tint: str  # security|performance|reliability
      lod_level: str  # GLOBAL|TREE|LEAF|FULL
      context: str
      few_shots: List[Dict]
      conversation_history: List[Dict]
      timestamp: float
      retry_count: int = 0
      score: float = 0.0
  ```

- [ ] `middleware.py` — **Elisyа переводчик**:
  - `reframe(state, agent_type)` → добавить history, few-shots, окрасить
  - `update(state, output, speaker)` → append to history, update path

- [ ] `semantic_path.py` — **Path generator**:
  - `generate_semantic_path(history)` → projects/lang/domain/tool

---

## СЛОЙ 4: LANGGRAPH WORKFLOW

### ✅ ЧТО ЕСТЬ:
- `langgraph_nodes.py` — 6 нод реализовано (PM, Architect, Dev, QA, Merge, Ops)
- `agent_orchestrator_parallel.py` — параллельное Dev || QA
- `langgraph_builder.py` — существует (но может быть пустой)

### ❌ ЧТО НУЖНО:
- [ ] **СОЗДАТЬ/ОБНОВИТЬ: `src/workflows/langgraph_with_elisya.py`**:
  - `build_vetka_graph(nodes)` → StateGraph(ElisyaState)
  - Nodes: pm_node, architect_node, dev_qa_parallel, eval_node, merge_node
  - На каждом шаге: reframe() → agent → update() → triple_write()
  - Conditional routing по complexity + score

- [ ] **СОЗДАТЬ: `src/workflows/state_manager.py`**:
  - `create_from_request()` → initial ElisyaState
  - `persist_to_weaviate()` → save state
  - `load_from_weaviate()` → resume workflow

- [ ] **ОБНОВИТЬ: `src/workflows/langgraph_nodes.py`**:
  - Все ноды должны работать с ElisyaState
  - Вместо VetkaParallelState

---

## СЛОЙ 5: MEMORY (Triple Write)

### ✅ ЧТО ЕСТЬ:
- `qdrant_client.py` — `triple_write()` функция готова
- `weaviate_helper.py` — save functions
- `memory_manager.py` — базовый interface

### ❌ ЧТО НУЖНО:
- [ ] **СОЗДАТЬ: `src/memory/triple_write_integration.py`**:
  - `persist_elisya_state(state)` — write to all 3 stores
  - Verify atomicity after write

- [ ] **ОБНОВИТЬ: `src/orchestration/memory_manager.py`**:
  - `save_agent_output()` → call triple_write()
  - `save_workflow_result()` → call triple_write()
  - ChangeLog recording

- [ ] **ОБНОВИТЬ: `src/memory/weaviate_helper.py`**:
  - Add VetkaElisya collection (semantic path + reframe)
  - Add VetkaFewShot collection (examples for retry)

---

## СЛОЙ 6: UI (Socket.IO + 3D Tree)

### ✅ ЧТО ЕСТЬ:
- `main.py` — Socket.IO configured
- `workflow_started`, `workflow_complete` events
- Basic `index.html` in `frontend/templates/`

### ❌ ЧТО НУЖНО:
- [ ] **ОБНОВИТЬ: `main.py`**:
  - emit('agent_spoke', {agent, output, branch})
  - emit('elisya_reframed', {context, lod, few_shots})
  - emit('triple_write_complete', {path, atomicity})

- [ ] **ОБНОВИТЬ: `/frontend/templates/index.html`**:
  - Real-time tree visualization
  - Color by tint (security=red, performance=blue)
  - Update on Socket.IO events

---

## 📂 DIRECTORY STRUCTURE (AFTER ALL CHANGES)

```
vetka_live_03/
├── src/
│   ├── agents/              ✅ (EXISTS)
│   │   ├── pm_agent.py
│   │   ├── dev_agent.py
│   │   ├── qa_agent.py
│   │   ├── architect_agent.py
│   │   └── eval_agent.py
│   │
│   ├── elisya/              ❌ CREATE
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── middleware.py
│   │   ├── semantic_path.py
│   │   └── cache.py (optional)
│   │
│   ├── autogen_integration/ ❌ CREATE
│   │   ├── __init__.py
│   │   ├── agents_config.py
│   │   ├── groupchat_wrapper.py
│   │   └── message_handler.py
│   │
│   ├── elisya_integration/  ✅ (EXISTS - UPDATE)
│   │   ├── context_manager.py
│   │   └── elysia_config.py
│   │
│   ├── orchestration/       ✅ (EXISTS - UPDATE)
│   │   ├── agent_orchestrator_parallel.py
│   │   ├── memory_manager.py
│   │   └── progress_tracker.py
│   │
│   ├── workflows/           ✅ (EXISTS - UPDATE)
│   │   ├── langgraph_nodes.py
│   │   ├── langgraph_with_elisya.py  ❌ CREATE
│   │   ├── state_manager.py          ❌ CREATE
│   │   └── langgraph_builder.py
│   │
│   ├── memory/              ✅ (EXISTS - UPDATE)
│   │   ├── qdrant_client.py
│   │   ├── weaviate_helper.py
│   │   └── triple_write_integration.py  ❌ CREATE
│   │
│   └── integrations/        ✅ (EXISTS)
│
├── main.py                  ✅ (EXISTS - UPDATE)
├── requirements.txt         ✅ (EXISTS - UPDATE)
└── 7phase/
    └── (this directory - documentation)
```

---

## 🔄 DEPENDENCY GRAPH

```
User Request
    ↓
[Autogen GroupChat] 
    ↓ (each message)
[Elisyа Middleware.reframe]
    ↓
[Agent (PM|Dev|QA|Architect)]
    ↓
[Elisyа Middleware.update]
    ↓
[LangGraph Node]
    ↓
[Triple Write (Weaviate+Qdrant+ChangeLog)]
    ↓
[Socket.IO Event to UI]
    ↓
[UI 3D Tree Update]
```

---

## ✅ IMPLEMENTATION CHECKLIST

### PHASE A: Elisyа Foundation
- [ ] Create `src/elisya/` directory
- [ ] Write `state.py` (ElisyaState)
- [ ] Write `middleware.py` (reframe + update)
- [ ] Write `semantic_path.py` (path generator)
- [ ] Write tests: test_elisya_state, test_elisya_middleware

### PHASE B: Autogen Integration
- [ ] Create `src/autogen_integration/` directory
- [ ] Write `agents_config.py` (agent setup)
- [ ] Write `groupchat_wrapper.py` (VetkaGroupChat)
- [ ] Write `message_handler.py` (converter)
- [ ] Write tests: test_autogen_groupchat

### PHASE C: LangGraph + Elisyа
- [ ] Write `langgraph_with_elisya.py` (build graph)
- [ ] Write `state_manager.py` (StateManager)
- [ ] Update `langgraph_nodes.py` (use ElisyaState)
- [ ] Write tests: test_langgraph_with_elisya

### PHASE D: Triple Write
- [ ] Write `triple_write_integration.py`
- [ ] Update `memory_manager.py` (call triple_write)
- [ ] Update `weaviate_helper.py` (collections)
- [ ] Write tests: test_triple_write_atomicity

### PHASE E: UI + Integration
- [ ] Update `main.py` (Socket.IO events)
- [ ] Update `requirements.txt` (add autogen)
- [ ] Update frontend (3D tree visualization)
- [ ] Full workflow tests: test_complete_workflow

---

## 📊 LINE COUNT ESTIMATE

| Component | Lines | Status |
|-----------|-------|--------|
| ElisyaState | 50 | ❌ CREATE |
| elisya_middleware | 150 | ❌ CREATE |
| semantic_path | 80 | ❌ CREATE |
| autogen_agents_config | 100 | ❌ CREATE |
| autogen_groupchat | 200 | ❌ CREATE |
| langgraph_with_elisya | 250 | ❌ CREATE |
| state_manager | 150 | ❌ CREATE |
| triple_write_integration | 100 | ❌ CREATE |
| Tests (5 files) | 300 | ❌ CREATE |
| **TOTAL** | **~1,500** | **❌ CREATE** |

---

## 🚀 NEXT STEPS

1. ✅ Understand architecture (DONE)
2. → Create directory structure
3. → Write Sprint 1 code (Elisyа Foundation)
4. → Test with pytest
5. → Continue Sprints 2-5
6. → All tests GREEN
7. → Merge to main codebase

---

**Last Updated:** 2025-10-28  
**Status:** 🟢 READY FOR IMPLEMENTATION
