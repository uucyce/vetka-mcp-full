╔══════════════════════════════════════════════════════════════════════════════╗
║           🚀 VETKA PHASE 7 — COMPLETE ARCHITECTURE BLUEPRINT                 ║
║                    Elisyа + Autogen + LangGraph Integration                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

# 📊 СИСТЕМА: 6 СЛОЁВ АРХИТЕКТУРЫ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ СЛОЙ 1: USER REQUEST                                                        │
│ Flask POST → /api/workflow/start → workflow_id + feature + complexity      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ СЛОЙ 2: AUTOGEN GroupChat                                                   │
│ AgentManager spawns: PM | Dev | QA | Architect | EvalAgent                 │
│ Agents speak, not execute sequentially                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ СЛОЙ 3: ELISYА STATE (SHARED MEMORY - THE HEART)                           │
│ ❌ Agents НЕ говорят друг другу напрямую                                    │
│ ✅ Все говорят на ЯЗЫКЕ ELISYА (ElisyaState)                              │
│                                                                              │
│ ElisyaState содержит:                                                       │
│   • context: основной текст (переосмысленный)                              │
│   • speaker: кто сейчас говорит (PM|Dev|QA|Architect|EvalAgent)          │
│   • semantic_path: projects/python/ml/sklearn (динамически создаётся)      │
│   • tint: семантическая окраска (security|performance|reliability)         │
│   • lod_level: уровень детали (GLOBAL|TREE|LEAF|FULL)                     │
│   • few_shots: примеры для retry                                            │
│   • conversation_history: весь диалог                                       │
│   • timestamp, retry_count, score                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ СЛОЙ 4: ELISYА MIDDLEWARE (Переводчик)                                    │
│                                                                              │
│ reframe(state, agent_type) → для КАЖДОГО агента:                           │
│   1. Fetch history из Weaviate (same semantic_path)                        │
│   2. Truncate по LOD (ContextManager)                                       │
│   3. Add few-shots (score > 0.8 для этого agent_type)                      │
│   4. Add semantic_tint                                                      │
│   5. Возвращает переосмысленный контекст                                   │
│                                                                              │
│ update(state, output, speaker) → после каждого агента:                     │
│   1. Append to conversation_history                                         │
│   2. Generate/update semantic_path (LLM call)                              │
│   3. Return updated state                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ СЛОЙ 5: LANGGRAPH WORKFLOW (Оркестрация)                                   │
│                                                                              │
│ StateGraph(ElisyaState) с нодами:                                          │
│   • pm_node: reframe() → PM agent → update() → triple write                │
│   • architect_node: reframe() → Architect → update() → triple write        │
│   • dev_qa_parallel: [Dev || QA] в параллели → update() → triple write   │
│   • eval_node: reframe() → EvalAgent → score → retry if < 0.7             │
│   • merge_node: объединить результаты                                      │
│                                                                              │
│ Conditional routing:                                                        │
│   - Complexity → simple or parallel workflow                                │
│   - Score < 0.7 → back to Elisyа + rephrase → retry                       │
│   - Score > 0.7 → save as few-shot → continue                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ СЛОЙ 6: TRIPLE WRITE (Atomicity)                                           │
│                                                                              │
│ После каждого agent output:                                                │
│   1. Write to Weaviate (semantic concepts) → VetkaElisya                   │
│   2. Write to Qdrant (hierarchical tree) → VetkaTree + VetkaLeaf           │
│   3. Write to ChangeLog (audit trail) → immutable source of truth         │
│                                                                              │
│ Atomicity verification:                                                     │
│   - Если одна БД упала → log in ChangeLog, continue                        │
│   - ChangeLog = истина, остальные восстанавливаются из неё                │
│   - Память растёт, не ломается                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ СЛОЙ 7: UI (Socket.IO 3D VetkaTree)                                        │
│                                                                              │
│ Real-time events:                                                           │
│   • agent_spoke: {'agent': 'PM', 'output': '...', 'branch': 'projects/...'} │
│   • elisya_reframed: {'context': '...', 'lod': 'TREE', 'few_shots': [...]} │
│   • triple_write_complete: {'path': 'projects/...', 'atomicity': true}     │
│                                                                              │
│ Visualization:                                                              │
│   • 3D-zoom по VetkaTree branches                                          │
│   • Color by tint: security=red, performance=blue                          │
│   • Update on every write                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 🎯 ЧТО ЕСТЬ vs ЧТО НУЖНО

## ✅ ГОТОВО (Phase 6-7 код существует):
- `main.py` — Flask + Socket.IO
- `agent_orchestrator_parallel.py` — параллельное Dev || QA
- `langgraph_nodes.py` — 6 нод (PM, Architect, Dev, QA, Merge, Ops)
- `qdrant_client.py` — triple_write функция
- `context_manager.py` — LOD, budget, relevance
- `eval_agent.py` — scoring, retry logic
- `Ollama` — локальные LLM
- `Weaviate` — semantic search

## ❌ НУЖНО СОЗДАТЬ (в контейнере, потом на Mac):

### Группа A: ELISYА STATE & MIDDLEWARE
- `src/elisya/state.py` — ElisyaState dataclass (расширенный)
- `src/elisya/middleware.py` — reframe() + update() functions
- `src/elisya/semantic_path.py` — generate_semantic_path()
- `src/elisya/__init__.py`

### Группа B: AUTOGEN INTEGRATION
- `src/autogen_integration/agents_config.py` — agents setup
- `src/autogen_integration/groupchat_wrapper.py` — VetkaGroupChat
- `src/autogen_integration/message_handler.py` — Autogen2Elisya converter
- `src/autogen_integration/__init__.py`

### Группа C: LANGGRAPH + ELISYА
- `src/workflows/langgraph_with_elisya.py` — построить StateGraph
- `src/workflows/state_manager.py` — StateManager (create, persist, load)
- Обновить `src/workflows/langgraph_nodes.py` — использовать ElisyaState

### Группа D: TRIPLE WRITE INTEGRATION
- `src/memory/triple_write_integration.py` — persist_elisya_state()
- Обновить `src/orchestration/memory_manager.py` — вызывать triple_write

### Группа E: API & UI
- Обновить `main.py` — добавить Socket.IO events + API endpoints
- `/frontend/3d_tree_viz.html` — 3D visualization (опционально Phase 7.5)

---

# 📦 WORKFLOW: Request → Output

```
1️⃣  User Request
    POST /api/workflow/start
    {"feature": "Create ML model", "complexity": "LARGE"}
                              ↓
2️⃣  Create ElisyaState
    StateManager.create_from_request()
                              ↓
3️⃣  Autogen GroupChat STARTS
    PM: "I'll plan this"
    (agents speak freely, not in fixed order)
                              ↓
4️⃣  Each agent output → Elisyа Middleware
    speaker_output → elisya_middleware.reframe()
                  → agent uses reframed context
                  → agent produces output
                  → elisya_middleware.update()
                              ↓
5️⃣  Update → Triple Write
    state → qdrant.triple_write(
        path="projects/python/ml/sklearn",
        content=output,
        vector=embed(output)
    )
    → Weaviate + Qdrant + ChangeLog
                              ↓
6️⃣  Socket.IO Event to UI
    emit('agent_spoke', {agent, output, branch})
    UI updates 3D tree in real-time
                              ↓
7️⃣  Dev || QA PARALLEL
    Both write to Elisyа State
    Both → Triple Write
                              ↓
8️⃣  EvalAgent Scores
    score = evaluate(conversation_history)
    If score < 0.7:
      → Elisyа adds few-shots + rephrase
      → Autogen retry with new prompt
    If score > 0.7:
      → Save as few-shot
      → Continue
                              ↓
9️⃣  LangGraph Merge
    Combine Dev + QA outputs
    Finalize state
                              ↓
🔟 Complete
    emit('workflow_complete', final_state)
    UI shows final tree with all branches
```

---

# 🧪 SUCCESS CRITERIA

## Elisyа Middleware:
- ✅ reframe() добавляет few-shots из Weaviate
- ✅ update() генерирует semantic_path
- ✅ semantic_path имеет формат projects/*/*/* 
- ✅ Работает для всех agent types

## Autogen Integration:
- ✅ GroupChat spawns без ошибок
- ✅ Агенты говорят в любом порядке
- ✅ Elisyа state обновляется после каждого сообщения
- ✅ Retry logic срабатывает при score < 0.7

## LangGraph + Elisyа:
- ✅ StateGraph компилируется
- ✅ State течёт через все ноды
- ✅ Elisyа middleware применяется на каждом шаге
- ✅ Dev || QA работают параллельно (проверено по timestamps)

## Triple Write:
- ✅ Все 3 базы пишут после каждого agent output
- ✅ ChangeLog записывает все операции
- ✅ Atomicity flag = true
- ✅ При падении одной БД → ChangeLog + continue

## Full Workflow:
- ✅ User request → final output в < 160s
- ✅ EvalAgent score > 0.7
- ✅ Semantic paths генерируются (projects/python/...)
- ✅ Conversation history полная
- ✅ Socket.IO events приходят в real-time

---

# 📊 SPRINT ROADMAP

| Sprint | Component | Time | Files | Lines |
|--------|-----------|------|-------|-------|
| 1 | Elisyа Foundation | 2-3h | 3 | 280 |
| 2 | Autogen Integration | 3-4h | 3 | 400 |
| 3 | LangGraph + Elisyа | 4-5h | 2 | 400 |
| 4 | Triple Write | 2-3h | 1 | 100 |
| 5 | Full Tests + Benchmarks | 3-4h | 1 | 100 |
| **TOTAL** | **Complete System** | **~16h** | **10+** | **~1,500** |

---

# 🚀 NEXT: START SPRINT 1

All planning complete. Ready to write code in container, test with pytest, then merge to Mac.

---

**Created:** 2025-10-28  
**Status:** 🟢 READY FOR IMPLEMENTATION  
**Architecture:** Complete  
**Blueprint:** Verified  
