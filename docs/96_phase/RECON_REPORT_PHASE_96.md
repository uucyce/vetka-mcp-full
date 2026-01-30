# VETKA Phase 96 - Reconnaissance Report

**Date:** 2026-01-27
**Agent:** Claude Opus 4.5 + Haiku Swarm
**Status:** System Health Check Complete

---

## System Health Status

```
VETKA Health Status
===================
Status: healthy
Version: 2.0.0
Phase: 39.8

Components:
  ✅ metrics_engine
  ✅ model_router
  ❌ api_gateway (removed in Phase 95)
  ✅ qdrant
  ✅ feedback_loop
  ✅ smart_learner
  ✅ hope_enhancer
  ✅ embeddings_projector
  ✅ student_system
  ✅ learner
  ✅ elisya
```

---

## 1. TRIPLE WRITE ARCHITECTURE

### What It Does
Triple Write — система синхронизации данных, которая **одновременно записывает в три хранилища**:

```
Операция индексирования
       ↓
TripleWriteManager.write_file()
       ↓
    +--+--+
    |  |  |
    ↓  ↓  ↓
  Qdrant  Weaviate  ChangeLog
  (vector) (graph)  (audit)
```

### Key Files
| File | Purpose |
|------|---------|
| `src/orchestration/triple_write_manager.py` | Main manager with retry logic |
| `src/api/routes/triple_write_routes.py` | REST API endpoints |
| `src/orchestration/memory_manager.py` | Alternative triple_write() for logs |

### API Endpoints
```
GET  /api/triple-write/stats
GET  /api/triple-write/check-coherence?depth=basic|full
POST /api/triple-write/cleanup
POST /api/triple-write/reindex
```

### CRITICAL ISSUES

| Marker | Location | Problem | Severity |
|--------|----------|---------|----------|
| `MARKER_COHERENCE_ROOT_001` | qdrant_updater.py:53 | File watcher writes ONLY to Qdrant, bypasses TripleWrite | **CRITICAL** |
| `MARKER_COHERENCE_BYPASS_001-005` | watcher_routes.py | 5 places bypass TripleWrite | **CRITICAL** |
| `MARKER_TW_010_RACE_CONDITION` | triple_write_manager.py:74 | Race condition in changelog | HIGH |
| `MARKER_TW_013_NO_WRITE_LOCK` | triple_write_manager.py:77 | Needs lock for concurrent writes | HIGH |

### Data Coherence Problem
```
Expected state:
  Qdrant count = 1000
  Weaviate count = 1000
  ChangeLog entries = 1000

Actual state (after normal usage):
  Qdrant count = 5000    ← ALL writes go here
  Weaviate count = 1000  ← Not updated
  ChangeLog entries = 1000 ← Empty

  DIFFERENCE: +4000 files only in Qdrant!
```

---

## 2. DEPENDENCY INJECTION SYSTEM

### Architecture (3 Levels)

**Level 1: `dependencies.py` (FastAPI DI)**
- Required deps: `memory_manager`, `orchestrator`, `eval_agent`
- Optional deps: `model_router`, `qdrant_manager`, `smart_learner`, etc.

**Level 2: `di_container.py` (Handler Container)**
- Created to split the 1694-line `user_message_handler`
- Chain: `ContextBuilder` → `ModelClient` → `MentionHandler` → `HostessRouter`

**Level 3: `components_init.py` (Initialization)**
- Singletons for all components
- Lazy initialization via getter functions

### Key Files
| File | Purpose |
|------|---------|
| `src/dependencies.py` | FastAPI Depends() definitions |
| `src/api/handlers/di_container.py` | Handler DI container |
| `src/initialization/components_init.py` | Component initialization |
| `src/initialization/dependency_check.py` | Module availability checks |

### Potential Issues
```python
# components_init.py:344-351
promotion_engine = student_promotion_engine_factory(
    level_system=student_level_system,
    smart_learner=smart_learner if SMART_LEARNER_AVAILABLE else None,
    eval_agent=None,  # ⚠️ HARD-CODED NONE
    memory_manager=None  # ⚠️ HARD-CODED NONE
)
```

### Status
| Aspect | Rating | Comment |
|--------|--------|---------|
| Organization | ✅ Good | 3-level architecture |
| Circular deps | ✅ Safe | Linear initialization |
| Graceful degradation | ✅ Excellent | Availability flags |
| Singleton management | ⚠️ OK | Global vars + locks |

---

## 3. ORCHESTRATION LAYER

### Orchestrator Hierarchy

```
1. OrchestratorWithElisya (PRIMARY - 2500+ lines)
   ↓ if fails
2. AgentOrchestrator (parallel mode)
   ↓ if fails
3. AgentOrchestrator (sequential mode)
```

### Main Entry Point
```python
# /src/initialization/components_init.py:487
def get_orchestrator():
    # Returns singleton OrchestratorWithElisya
```

### Workflow Structure (LangGraph Mode)
```
START
  ↓
HOSTESS (context + history)
  ↓
ARCHITECT (solution design)
  ↓
PM (planning)
  ↓
DEV + QA (parallel)
  ↓
EVAL (quality score >= 0.75?)
  ├─ YES → APPROVAL → END
  └─ NO → LEARNER (retry<3) → back to DEV+QA
```

### Key Files (30 files, ~15.3K lines)
```
src/orchestration/
├── orchestrator_with_elisya.py     [MAIN - 2500+ lines]
├── agent_orchestrator.py           [Sequential fallback]
├── agent_orchestrator_parallel.py  [Parallel with semaphore]
├── langgraph_builder.py            [Declarative workflow]
├── langgraph_nodes.py              [Node implementations]
├── services/
│   ├── memory_service.py
│   ├── elisya_state_service.py
│   ├── routing_service.py
│   ├── api_key_service.py
│   └── mcp_state_bridge.py
├── query_dispatcher.py             [Task classification]
├── triple_write_manager.py         [Reliability]
└── [+ 20 more files]
```

### Execution Modes
1. **LangGraph Mode** (Phase 60) - Recommended, declarative
2. **Legacy Mode** - Sequential PM → Architect → Dev → QA

---

## 4. GIT STATUS SUMMARY

```
Branch: main
Last commit: 93370ed Update Phase 96 TODO
Clean: ❌ No

Modified: 65 files
Untracked: 240 files (mostly docs and test files)
```

### Key Modified Files
- `src/orchestration/triple_write_manager.py`
- `src/orchestration/orchestrator_with_elisya.py`
- `src/api/handlers/user_message_handler.py`
- `src/dependencies.py`
- `src/initialization/components_init.py`

---

## 5. ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                        VETKA CORE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   FastAPI   │───▶│  Handlers   │───▶│ Orchestrator│     │
│  │   Routes    │    │(DI Container)│    │ (Elisya)   │     │
│  └─────────────┘    └─────────────┘    └──────┬──────┘     │
│                                               │             │
│         ┌────────────────────────────────────┼─────┐       │
│         ▼                    ▼               ▼     │       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  LangGraph  │    │   Agents    │    │   Memory    │     │
│  │  Workflow   │    │ PM/Dev/QA   │    │  Manager    │     │
│  └─────────────┘    └─────────────┘    └──────┬──────┘     │
│                                               │             │
│  ┌────────────────────────────────────────────┼─────┐      │
│  │              TRIPLE WRITE LAYER            │     │      │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐  │     │      │
│  │  │ Qdrant  │   │Weaviate │   │ChangeLog│  │     │      │
│  │  │ (Vector)│   │ (Graph) │   │ (Audit) │  │     │      │
│  │  └─────────┘   └─────────┘   └─────────┘  │     │      │
│  └───────────────────────────────────────────┘     │      │
│                                                     │      │
│  ⚠️ BYPASS PATHS (File Watcher, Browser Scan)──────┘      │
│     Write directly to Qdrant, skip Weaviate/ChangeLog     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. RECOMMENDATIONS FOR PHASE 96

### Priority 1: Fix Triple Write Coherence
- [ ] Route all file operations through TripleWriteManager
- [ ] Fix MARKER_COHERENCE_BYPASS_001-005
- [ ] Add real-time coherence monitoring

### Priority 2: Clean Up DI
- [ ] Remove hard-coded `None` values in components_init.py
- [ ] Document dependency graph

### Priority 3: Stabilize Orchestration
- [ ] Ensure LangGraph mode is default
- [ ] Add health checks for all workflow nodes

### Priority 4: Git Cleanup
- [ ] Commit or stash 65 modified files
- [ ] Organize 240 untracked files

---

## Files Created This Session
- `docs/96_phase/RECON_REPORT_PHASE_96.md` (this file)

---

*Generated by Claude Opus 4.5 with Haiku Swarm reconnaissance*
