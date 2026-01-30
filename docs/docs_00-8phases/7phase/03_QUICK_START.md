#!/bin/bash

# 🚀 VETKA PHASE 7 — QUICK START GUIDE

## 📍 YOU ARE HERE
Location: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/7phase/`

## 📚 DOCUMENTATION STRUCTURE

```
7phase/
├── 00_ARCHITECTURE_COMPLETE.md    ← Start here: Full 6-layer architecture
├── 01_WHAT_EXISTS_VS_MISSING.md   ← What's ready vs what to create
├── 02_SPRINT_ROADMAP.md           ← Detailed 5-sprint plan
├── 03_QUICK_START.sh              ← This file
└── README.md                       ← Summary (you're reading it)
```

---

## 🎯 3-MINUTE SUMMARY

**VETKA** is a 6-layer distributed AI development system where:

1. **User** sends feature request
2. **Autogen GroupChat** spawns 5 agents (PM, Dev, QA, Architect, EvalAgent)
3. **Elisyа** (not a database) = shared language layer where all agents read/write
4. **LangGraph** orchestrates flow with Elisyа middleware at each step
5. **Triple Write** saves atomically to Weaviate + Qdrant + ChangeLog
6. **Socket.IO UI** shows 3D VetkaTree in real-time

**Key Innovation:** Agents don't know each other—they know Elisyа. It reframes context, filters by LOD, adds few-shots, and generates semantic paths.

---

## ✅ WHAT'S READY (Phase 6-7 exists)

- Agent code (PM, Dev, QA, Architect, EvalAgent)
- LangGraph nodes
- Qdrant client with triple_write()
- Context manager (LOD, budget, relevance)
- Parallel Dev || QA execution
- Ollama + Weaviate

## ❌ WHAT'S MISSING (Need to create in container)

- **ElisyaState** dataclass (extended state with speaker, semantic_path, tint, conversation)
- **elisya_middleware.py** (reframe + update functions)
- **Autogen integration** (GroupChat setup, agents config)
- **langgraph_with_elisya.py** (StateGraph using ElisyaState)
- **Triple write wiring** (actual persist calls)
- **UI events** (Socket.IO real-time updates)

---

## 📦 IMPLEMENTATION PLAN

### Phase 1: Container Development (16 hours)

```bash
# 5 sprints, each with code + tests
Sprint 1: Elisyа Foundation (2-3h)
  - ElisyaState
  - elisya_middleware
  - semantic_path_generator
  - 3 unit tests → GREEN

Sprint 2: Autogen Integration (3-4h)
  - agents_config
  - groupchat_wrapper
  - message_handler
  - 3 unit tests → GREEN

Sprint 3: LangGraph + Elisyа (4-5h)
  - langgraph_with_elisya
  - state_manager
  - updated langgraph_nodes
  - 2 unit tests → GREEN

Sprint 4: Triple Write (2-3h)
  - triple_write_integration
  - memory_manager updates
  - 2 unit tests → GREEN

Sprint 5: Integration Tests (3-4h)
  - Full workflow test
  - Performance benchmarks
  - 1 integration test → GREEN

# ALL TESTS PASS
pytest tests/ -v → ✅ 100% GREEN
```

### Phase 2: Mac Integration (2 hours)

```bash
# Copy from container to Mac project
mkdir -p src/elisya/
mkdir -p src/autogen_integration/

# (files copied)

# Update main files
# - main.py (Socket.IO events)
# - requirements.txt (add autogen)

# Test on Mac
python main.py
# Check: http://localhost:5001 + Socket.IO connection
```

---

## 🧪 SUCCESS CRITERIA

### Must be GREEN:
✅ Elisyа middleware: reframe() adds few-shots  
✅ Autogen GroupChat: agents communicate  
✅ LangGraph: state flows through all nodes  
✅ Dev || QA: parallel execution verified  
✅ Triple Write: all 3 stores written atomically  
✅ Full workflow: < 160s from request to output  
✅ EvalAgent: score > 0.7  
✅ Semantic paths: projects/python/ml/sklearn format  

---

## 📂 FILE LOCATIONS (After implementation)

```
vetka_live_03/
├── src/
│   ├── elisya/                  ← NEW (Sprint 1)
│   │   ├── state.py
│   │   ├── middleware.py
│   │   └── semantic_path.py
│   │
│   ├── autogen_integration/     ← NEW (Sprint 2)
│   │   ├── agents_config.py
│   │   ├── groupchat_wrapper.py
│   │   └── message_handler.py
│   │
│   ├── workflows/               ← UPDATED (Sprint 3)
│   │   ├── langgraph_with_elisya.py
│   │   ├── state_manager.py
│   │   └── langgraph_nodes.py (updated)
│   │
│   └── memory/                  ← UPDATED (Sprint 4)
│       └── triple_write_integration.py
│
├── main.py                      ← UPDATED (Sprint 5)
└── 7phase/                      ← This folder (docs)
```

---

## 🚀 GET STARTED NOW

### Step 1: Read Documentation
1. Read this file (3 min)
2. Read `00_ARCHITECTURE_COMPLETE.md` (10 min)
3. Read `01_WHAT_EXISTS_VS_MISSING.md` (10 min)
4. Read `02_SPRINT_ROADMAP.md` (20 min)

### Step 2: Start Sprint 1 in Container
```bash
cd /home/claude/vetka_implementation

# Create Sprint 1 directory
mkdir -p phase_a_elisya

# Start writing:
# 1. elisya_state.py (50 lines)
# 2. elisya_middleware.py (150 lines)
# 3. semantic_path_generator.py (80 lines)

# Test:
pytest tests/phase_a/ -v → expect 3 PASS
```

### Step 3: After Each Sprint
- Write code
- Write tests
- Run pytest
- Ensure GREEN
- Move to next sprint

### Step 4: All Sprints Complete
- All tests GREEN
- Copy to Mac
- Update main.py + requirements.txt
- Run on Mac
- Demo complete

---

## 💡 KEY CONCEPTS TO REMEMBER

### Elisyа = Language, Not Database
- Not a file, not a database, not a service
- It's a **shared perception layer** that all agents read/write
- Every agent reads ElisyaState (context filtered for them)
- Every agent writes output → middleware updates ElisyaState

### Semantic Path = Dynamic Branch
- `projects/python/ml/sklearn` generated on-the-fly
- Not pre-planned, not hierarchical directories
- Grows as agents talk

### Triple Write = Append-Only Memory
- Weaviate = semantic concepts
- Qdrant = hierarchical tree
- ChangeLog = immutable truth
- If one falls, others recover from ChangeLog

### Dev || QA = True Parallel
- Dev writes code, QA writes tests
- Same input (pm_plan)
- Both run at same time
- Merge results after both complete

---

## 📊 METRICS

| Metric | Target | Status |
|--------|--------|--------|
| Elisyа reframe time | < 100ms | TBD |
| Triple write latency | < 500ms | TBD |
| Full workflow time | < 160s | TBD |
| EvalAgent score | > 0.7 | TBD |
| Autogen convergence | < 5 msgs | TBD |
| Tests passing | 100% | TBD |

---

## ⚠️ IMPORTANT REMINDERS

✅ All code written in container FIRST  
✅ Pytest runs in container  
✅ Only merge to Mac after all tests GREEN  
✅ Use Filesystem tool for Mac files (not bash)  
✅ ElisyaState = central truth during execution  
✅ Middleware = the magic (reframe + update)  

---

## 🎬 NEXT IMMEDIATE STEP

**👉 Read `00_ARCHITECTURE_COMPLETE.md` to understand all 6 layers**

Then:
→ Read `01_WHAT_EXISTS_VS_MISSING.md`  
→ Read `02_SPRINT_ROADMAP.md`  
→ Start writing Sprint 1 code in container  
→ Test with pytest  
→ Move forward  

---

## 📞 QUICK REFERENCE

- **Architecture Doc:** `00_ARCHITECTURE_COMPLETE.md`
- **Missing Components:** `01_WHAT_EXISTS_VS_MISSING.md`
- **Sprint Details:** `02_SPRINT_ROADMAP.md`
- **Project Root:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/`
- **Container Work:** `/home/claude/vetka_implementation/`
- **Requirements:** Autogen, LangGraph, Qdrant, Weaviate, Ollama

---

**Status:** 🟢 READY TO BEGIN  
**Timeline:** ~18 hours total (16h container + 2h Mac)  
**Outcome:** Full Elisyа + Autogen + LangGraph integrated system  

Let's build! 🚀
