# 🌳 VETKA PHASE 7 — COMPLETE BLUEPRINT

## Executive Summary

VETKA Phase 7 is a complete rewrite of the orchestration layer to support **Elisyа (Shared Language Layer) + Autogen (Multi-Agent Communication) + LangGraph (Deterministic Workflow)**.

### Vision
> **"Agents don't execute tasks. They think together in Elisyа, a language where memory is immutable, context is filtered for each, and the tree grows by understanding, not by command."**

---

## 📊 System Architecture (6 Layers)

### Layer 1: User Request
- **Input:** Feature description + complexity level
- **Output:** ElisyaState initialized
- **Technology:** Flask POST → `/api/workflow/start`

### Layer 2: Autogen GroupChat
- **Agents:** PM, Dev, QA, Architect, EvalAgent
- **Communication:** Free-form (agents decide who speaks next)
- **Technology:** `pyautogen.GroupChat`

### Layer 3: Elisyа State (CORE)
- **What it is:** Shared memory layer (NOT a database)
- **State contents:** context, speaker, semantic_path, tint, lod_level, few_shots, conversation_history
- **How it works:** Every agent reads reframed context, writes output → middleware updates state
- **Technology:** `ElisyaState` dataclass + `ElisyaMiddleware`

### Layer 4: Elisyа Middleware
- **Reframe:** Fetch history from Weaviate, truncate by LOD, add few-shots (score > 0.8), add semantic tint
- **Update:** Append to conversation_history, generate/update semantic_path, return updated state
- **Technology:** `elisya_middleware.py`

### Layer 5: LangGraph Workflow
- **Orchestration:** StateGraph(ElisyaState) with nodes (PM, Architect, Dev||QA, Eval, Merge)
- **Conditional routing:** By complexity, by score
- **Retry logic:** If score < 0.7 → back to Elisyа + rephrase
- **Technology:** `langgraph.StateGraph`

### Layer 6: Triple Write Memory
- **Weaviate:** Semantic concepts (VetkaElisya collection)
- **Qdrant:** Hierarchical tree (VetkaTree, VetkaLeaf)
- **ChangeLog:** Immutable audit trail
- **Atomicity:** If one store fails → logged in ChangeLog, others recover
- **Technology:** `qdrant_client.triple_write()` + Weaviate

### Layer 7: UI (Socket.IO 3D Tree)
- **Real-time events:** agent_spoke, elisya_reframed, triple_write_complete
- **Visualization:** 3D VetkaTree branches, colored by tint
- **Technology:** Socket.IO + 3D.js (Phase 7.5)

---

## 🎯 Key Concepts

### Elisyа = Language
**NOT a database, NOT a service, NOT a node in the graph.**

It's a **shared perceptual medium** where agents think together:
- **Read:** Each agent reads context filtered FOR THEM (by LOD, task type, relevance)
- **Write:** Each agent writes output, which updates shared state
- **Transform:** Middleware reframes at each step (adds history, few-shots, context filtering)

**Analogy:** Like natural language in human conversations:
- Two people don't exchange JSON directly
- They speak in language, which carries context, adapts to listener, evolves conversation

### Semantic Path = Living Branch
**Format:** `projects/LANG/DOMAIN/TOOL`  
**Examples:**
- `projects/python/ml/sklearn`
- `projects/typescript/backend/express`
- `projects/rust/system/tokio`

**How it's generated:**
1. PM creates initial context
2. Elisyа middleware calls LLM: "Based on conversation, generate path"
3. Path created dynamically (not pre-planned)
4. Gets stored in ElisyaState
5. All future writes use this path

### Triple Write = Memory Never Breaks
```
After each agent output:
  1. Write to Weaviate (semantic search)
  2. Write to Qdrant (hierarchical tree)
  3. Write to ChangeLog (immutable truth)

Atomicity check:
  If ANY store fails → log in ChangeLog, continue
  ChangeLog = source of truth
  Others recover on restart
```

### Dev || QA = True Parallelism
```
PM Output:
  "Create auth with JWT"
         ↓
  Elisyа reframes for Dev: "...add security few-shots"
  Elisyа reframes for QA: "...add test coverage few-shots"
         ↓
  Dev writes code ← [PARALLEL] → QA writes tests
         ↓
  Both complete, merge results
  EvalAgent scores combined output
```

---

## 📦 What Needs to be Built

### Phase A: Elisyа Foundation (Sprint 1, 2-3h)
**Files to create:**
- `src/elisya/state.py` — ElisyaState dataclass (50 lines)
- `src/elisya/middleware.py` — reframe() + update() (150 lines)
- `src/elisya/semantic_path.py` — path generator (80 lines)

**Tests:**
- test_elisya_state_creation
- test_reframe_adds_few_shots
- test_update_generates_path

### Phase B: Autogen Integration (Sprint 2, 3-4h)
**Files to create:**
- `src/autogen_integration/agents_config.py` — agent setup (100 lines)
- `src/autogen_integration/groupchat_wrapper.py` — GroupChat wrapper (200 lines)
- `src/autogen_integration/message_handler.py` — message converter (100 lines)

**Tests:**
- test_autogen_agents_created
- test_groupchat_runs
- test_messages_flow

### Phase C: LangGraph + Elisyа (Sprint 3, 4-5h)
**Files to create:**
- `src/workflows/langgraph_with_elisya.py` — StateGraph with ElisyaState (250 lines)
- `src/workflows/state_manager.py` — StateManager (150 lines)
- **Update:** `src/workflows/langgraph_nodes.py` — use ElisyaState

**Tests:**
- test_graph_compiles
- test_state_flows_through_nodes
- test_parallel_execution_timing

### Phase D: Triple Write (Sprint 4, 2-3h)
**Files to create:**
- `src/memory/triple_write_integration.py` — persist_elisya_state() (100 lines)
- **Update:** `src/orchestration/memory_manager.py` — call triple_write

**Tests:**
- test_triple_write_all_stores
- test_changelog_records_writes
- test_atomicity_verified

### Phase E: Integration + UI (Sprint 5, 3-4h)
**Files to update:**
- `main.py` — Socket.IO events for real-time updates
- `requirements.txt` — add autogen dependency
- **Optional:** `/frontend/` — 3D tree visualization

**Tests:**
- test_complete_workflow
- test_performance_benchmarks

---

## ✅ Implementation Checklist

### Before Sprint 1:
- [ ] Read all 3 architecture docs (00, 01, 02)
- [ ] Understand Elisyа as language layer
- [ ] Understand semantic path generation
- [ ] Understand triple write atomicity

### Sprint 1: Elisyа Foundation
- [ ] Create `src/elisya/` directory
- [ ] Write ElisyaState (state.py)
- [ ] Write ElisyaMiddleware (middleware.py)
- [ ] Write SemanticPathGenerator (semantic_path.py)
- [ ] Write 3 unit tests
- [ ] All tests GREEN ✅

### Sprint 2: Autogen Integration
- [ ] Create `src/autogen_integration/` directory
- [ ] Write agents_config.py
- [ ] Write groupchat_wrapper.py
- [ ] Write message_handler.py
- [ ] Write 3 unit tests
- [ ] All tests GREEN ✅

### Sprint 3: LangGraph + Elisyа
- [ ] Write langgraph_with_elisya.py
- [ ] Write state_manager.py
- [ ] Update langgraph_nodes.py
- [ ] Write 2 unit tests
- [ ] All tests GREEN ✅

### Sprint 4: Triple Write
- [ ] Write triple_write_integration.py
- [ ] Update memory_manager.py
- [ ] Write 2 unit tests
- [ ] All tests GREEN ✅

### Sprint 5: Integration Tests
- [ ] Write full workflow test
- [ ] Write performance benchmarks
- [ ] Update main.py (Socket.IO events)
- [ ] Update requirements.txt
- [ ] All tests GREEN ✅

### Merge to Mac
- [ ] Copy all files to Mac project
- [ ] Run `python main.py`
- [ ] Verify Socket.IO connection
- [ ] Test full workflow on Mac

---

## 🧪 Success Criteria (ALL must be ✅)

### Elisyа Layer:
- ✅ ElisyaState creates, serializes, validates
- ✅ Middleware reframe() adds few-shots
- ✅ Middleware update() generates semantic_path
- ✅ Paths have format projects/*/*/

### Autogen Layer:
- ✅ GroupChat initializes without errors
- ✅ Agents communicate (PM → Dev → QA)
- ✅ Each message updates ElisyaState
- ✅ Retry triggered when score < 0.7

### LangGraph Layer:
- ✅ StateGraph compiles
- ✅ State flows through all 5 nodes
- ✅ Elisyа middleware applied at each node
- ✅ Dev || QA executed in parallel (timestamps verify)

### Memory Layer:
- ✅ All 3 stores written after each agent
- ✅ ChangeLog records every write
- ✅ Atomicity flag = true
- ✅ One store failure → continue with log

### Full Workflow:
- ✅ User request → output in < 160s
- ✅ EvalAgent score > 0.7
- ✅ Semantic paths generated (projects/...)
- ✅ Conversation history complete and coherent
- ✅ Socket.IO events flowing (if on Mac)

---

## 📊 Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Elisyа middleware time | < 100ms | TBD |
| Triple write latency | < 500ms | TBD |
| Full workflow time | < 160s | TBD |
| EvalAgent score | > 0.7 | TBD |
| Autogen convergence | < 5 messages | TBD |
| Tests passing | 100% | TBD |
| Code coverage | > 80% | TBD |

---

## 🚀 Timeline

| Phase | Duration | Output |
|-------|----------|--------|
| **Container Development** | ~16 hours | 5 sprints, all tests GREEN |
| Sprint 1 (Elisyа) | 2-3h | ~280 lines + 3 tests |
| Sprint 2 (Autogen) | 3-4h | ~400 lines + 3 tests |
| Sprint 3 (LangGraph) | 4-5h | ~400 lines + 2 tests |
| Sprint 4 (Triple Write) | 2-3h | ~100 lines + 2 tests |
| Sprint 5 (Integration) | 3-4h | ~100 lines + 1 test |
| **Mac Integration** | ~2 hours | Copy, update, verify |
| **Total** | ~18 hours | Complete system |

---

## 📂 Final Directory Structure

```
vetka_live_03/
├── src/
│   ├── agents/                          ✅ EXISTS
│   │   ├── pm_agent.py
│   │   ├── dev_agent.py
│   │   ├── qa_agent.py
│   │   ├── architect_agent.py
│   │   └── eval_agent.py
│   │
│   ├── elisya/                          ❌ CREATE (Sprint 1)
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── middleware.py
│   │   └── semantic_path.py
│   │
│   ├── autogen_integration/             ❌ CREATE (Sprint 2)
│   │   ├── __init__.py
│   │   ├── agents_config.py
│   │   ├── groupchat_wrapper.py
│   │   └── message_handler.py
│   │
│   ├── workflows/                       ✅ EXISTS (UPDATED Sprint 3)
│   │   ├── langgraph_nodes.py           (updated to use ElisyaState)
│   │   ├── langgraph_with_elisya.py     (❌ CREATE)
│   │   └── state_manager.py             (❌ CREATE)
│   │
│   ├── memory/                          ✅ EXISTS (UPDATED Sprint 4)
│   │   ├── qdrant_client.py
│   │   ├── weaviate_helper.py
│   │   └── triple_write_integration.py  (❌ CREATE)
│   │
│   └── orchestration/                   ✅ EXISTS
│       └── memory_manager.py            (UPDATED: call triple_write)
│
├── main.py                              ✅ EXISTS (UPDATED Sprint 5)
├── requirements.txt                     ✅ EXISTS (UPDATED: +autogen)
└── 7phase/
    ├── 00_ARCHITECTURE_COMPLETE.md
    ├── 01_WHAT_EXISTS_VS_MISSING.md
    ├── 02_SPRINT_ROADMAP.md
    ├── 03_QUICK_START.md
    └── README.md (this file)
```

---

## 🎬 Getting Started

### Step 1: Read Documentation (1 hour)
```
00_ARCHITECTURE_COMPLETE.md    → Full system overview
01_WHAT_EXISTS_VS_MISSING.md   → What to build
02_SPRINT_ROADMAP.md           → Detailed code specs
03_QUICK_START.md              → Quick reference
```

### Step 2: Container Development (16 hours)
```
Sprint 1 → Sprint 2 → Sprint 3 → Sprint 4 → Sprint 5
All tests GREEN
```

### Step 3: Mac Integration (2 hours)
```
Copy files → Update main.py → Run → Test
```

---

## 💡 Remember

1. **Elisyа is a language, not a database**
2. **Agents don't execute—they think together**
3. **Semantic paths grow dynamically**
4. **Memory never breaks—it appends**
5. **Dev || QA are truly parallel**
6. **Triple write ensures atomicity**

---

## ✨ Vision Complete

You now have the **complete blueprint** for VETKA Phase 7:
- ✅ 6-layer architecture documented
- ✅ What exists vs what's missing identified
- ✅ 5-sprint implementation roadmap detailed
- ✅ Success criteria defined
- ✅ Timeline estimated

**Next step: Start Sprint 1! 🚀**

---

**Document:** VETKA Phase 7 Complete Blueprint  
**Created:** 2025-10-28  
**Status:** 🟢 READY FOR IMPLEMENTATION  
**Architecture:** COMPLETE  
**Vision:** CLEAR  

Let's build the future of AI development! 🌳✨
