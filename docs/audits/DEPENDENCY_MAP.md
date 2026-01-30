# VETKA DEPENDENCY MAP
## Phase 42 - Post-Cleanup Architecture

**Generated:** 2026-01-05
**Phase:** 42 (after Flask->FastAPI migration)
**Status:** PRODUCTION READY

---

## Project Structure

```
vetka_live_03/
├── main.py                    # FastAPI entry point (uvicorn)
├── run.sh                     # Startup script
├── quick_start.sh             # Quick start with dependencies
│
├── src/                       # Main source code (185 Python files)
│   ├── api/                   # FastAPI layer
│   │   ├── routes/            # REST endpoints (13 routers, 59 endpoints)
│   │   └── handlers/          # Socket.IO handlers (7 modules, 18 events)
│   │
│   ├── initialization/        # App startup & singletons
│   │   ├── components_init.py # Main initialization
│   │   ├── dependency_check.py# Module availability
│   │   ├── singletons.py      # Singleton accessors
│   │   └── logging_setup.py   # Logging config
│   │
│   ├── elisya/                # AI/LLM layer
│   │   ├── api_aggregator_v3.py  # Main LLM gateway
│   │   ├── api_gateway.py        # API gateway
│   │   ├── model_router_v2.py    # Model routing
│   │   ├── key_manager.py        # API key management
│   │   ├── llm_executor_bridge.py# LLM execution bridge
│   │   ├── middleware.py         # Request middleware
│   │   ├── state.py              # Elisya state
│   │   └── semantic_path.py      # Semantic path gen
│   │
│   ├── orchestration/         # Business logic (22 files)
│   │   ├── orchestrator_with_elisya.py  # Main orchestrator
│   │   ├── agent_orchestrator.py        # Base orchestrator
│   │   ├── agent_orchestrator_parallel.py # Parallel mode
│   │   ├── memory_manager.py            # Memory & storage
│   │   ├── cam_engine.py                # CAM engine
│   │   ├── chain_context.py             # Chain context
│   │   ├── query_dispatcher.py          # Query routing
│   │   ├── response_formatter.py        # Response formatting
│   │   ├── triple_write_manager.py      # Triple write
│   │   ├── feedback_loop_v2.py          # Feedback loop
│   │   └── ...
│   │
│   ├── agents/                # AI agents (26 files)
│   │   ├── hostess_agent.py   # User interaction routing
│   │   ├── eval_agent.py      # Output evaluation
│   │   ├── base_agent.py      # Base agent class
│   │   ├── streaming_agent.py # Streaming support
│   │   ├── tools.py           # Agent tools (49KB!)
│   │   ├── role_prompts.py    # Agent prompts
│   │   ├── arc_solver_agent.py# ARC solver
│   │   ├── learner_factory.py # Learner factory
│   │   ├── learner_initializer.py
│   │   ├── pixtral_learner.py
│   │   ├── qwen_learner.py
│   │   ├── smart_learner.py
│   │   ├── hope_enhancer.py   # HOPE enhancer
│   │   ├── embeddings_projector.py
│   │   ├── student_level_system.py
│   │   └── student_portfolio.py
│   │
│   ├── mcp/                   # Model Context Protocol
│   │   ├── mcp_server.py      # MCP server
│   │   ├── rate_limiter.py
│   │   ├── audit_logger.py
│   │   ├── approval.py
│   │   └── tools/             # MCP tools
│   │
│   ├── memory/                # Memory systems
│   ├── knowledge_graph/       # Knowledge graph
│   ├── tools/                 # Utility tools
│   ├── utils/                 # Utilities
│   ├── visualizer/            # 3D visualization
│   ├── validators/            # Data validators
│   ├── transformers/          # Data transformers
│   ├── workflows/             # LangGraph workflows
│   ├── intake/                # Intake system
│   ├── export/                # Export utilities
│   ├── ocr/                   # OCR processing
│   ├── scanners/              # Code scanners
│   └── monitoring/            # Monitoring
│
├── app/                       # Frontend
│   └── artifact-panel/        # React + Three.js frontend
│
├── data/                      # Data storage
│   ├── changelog/
│   ├── mcp_audit/
│   ├── intakes/
│   └── students/
│
└── tests/                     # Tests
```

---

## Core Dependencies

### Entry Point: main.py
```
main.py (FastAPI)
├── fastapi.FastAPI
├── socketio.AsyncServer (python-socketio)
├── uvicorn (ASGI server)
│
├── src.initialization.initialize_all_components()
│   └── components_init.py
│       ├── MetricsEngine
│       ├── ModelRouter (model_router_v2)
│       ├── APIGateway (api_gateway)
│       ├── LLMExecutorBridge
│       ├── QdrantManager
│       ├── MemoryManager
│       ├── OrchestratorWithElisya
│       ├── HostessAgent
│       ├── EvalAgent
│       ├── FeedbackLoop
│       ├── SmartLearner
│       └── StudentLevelSystem
│
├── src.api.routes.register_all_routers()
│   └── 13 routers registered
│
└── src.api.handlers.register_all_handlers()
    └── 7 handler modules registered
```

### API Layer

#### REST Endpoints (src/api/routes/)
| Router | Prefix | Endpoints | Description |
|--------|--------|-----------|-------------|
| config_routes | /api/config | 5 | Config & health |
| metrics_routes | /api/metrics | 4 | Metrics data |
| files_routes | /api/files | 6 | File operations |
| tree_routes | /api/tree | 8 | Tree navigation |
| eval_routes | /api/eval | 5 | Evaluation |
| semantic_routes | /api/semantic | 7 | Semantic search |
| chat_routes | /api/chat | 6 | Chat operations |
| knowledge_routes | /api/knowledge-graph | 10 | Knowledge graph |
| ocr_routes | /api/ocr | 3 | OCR processing |
| file_ops_routes | /api/file-ops | 2 | File operations |
| triple_write_routes | /api/triple-write | 3 | Triple write |
| workflow_routes | /api/workflow | 3 | Workflows |
| embeddings_routes | /api/embeddings | 3 | Embeddings |

#### Socket.IO Events (src/api/handlers/)
| Handler | Events | Description |
|---------|--------|-------------|
| connection_handlers | connect, disconnect | Connection lifecycle |
| chat_handlers | clear_context, mark_messages_read | Chat management |
| user_message_handler | user_message | Main chat input |
| workflow_handlers | start_workflow, cancel_workflow | Workflow control |
| tree_handlers | select_branch, fork_branch | Tree navigation |
| approval_handlers | approval_response | MCP approval |
| reaction_handlers | quick_action, message_reaction | Quick actions |

---

## Data Flow

```
User Request
    │
    ▼
[FastAPI] /api/chat or Socket.IO 'user_message'
    │
    ▼
[HostessAgent] → Routing Decision
    │
    ├─ Simple Query → quick_answer()
    │                   │
    │                   └─> Response
    │
    └─ Complex Task → [OrchestratorWithElisya]
                          │
                          ├─ PM Agent (planning)
                          ├─ Architect Agent (design)
                          ├─ Dev Agent (implementation)
                          └─ QA Agent (quality)
                               │
                               ▼
                          [EvalAgent] → Score (0-1)
                               │
                               ▼
                          [MemoryManager] → Triple Write
                               │
                               ├─ Qdrant (vectors)
                               ├─ Weaviate (graph)
                               └─ ChangeLog (JSON)
                               │
                               ▼
                          Response + Artifacts
```

---

## Module Dependency Graph

### Core Imports
```
main.py
└── src.initialization
    ├── components_init.py
    │   ├── src.elisya.api_gateway
    │   ├── src.elisya.model_router_v2
    │   ├── src.elisya.llm_executor_bridge
    │   ├── src.orchestration.memory_manager
    │   ├── src.orchestration.orchestrator_with_elisya
    │   ├── src.orchestration.feedback_loop_v2
    │   ├── src.agents.eval_agent
    │   ├── src.agents.learner_factory
    │   └── src.agents.student_level_system
    │
    └── dependency_check.py
        └── (checks module availability)
```

### Orchestrator Dependencies
```
orchestrator_with_elisya.py
├── src.agents
│   ├── hostess_agent.py
│   ├── eval_agent.py
│   ├── streaming_agent.py
│   ├── tools.py
│   └── arc_solver_agent.py
│
├── src.elisya
│   ├── api_aggregator_v3.py → call_model()
│   ├── middleware.py
│   ├── model_router_v2.py
│   ├── key_manager.py
│   ├── state.py
│   └── semantic_path.py
│
├── src.orchestration
│   ├── memory_manager.py
│   ├── progress_tracker.py
│   ├── query_dispatcher.py
│   ├── chain_context.py
│   ├── response_formatter.py
│   └── cam_engine.py
│
└── src.transformers
    └── phase9_to_vetka.py
```

---

## External Dependencies

### Python Packages (requirements.txt)
```
# Web Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-socketio>=5.11.0

# Async HTTP
httpx>=0.26.0
aiohttp>=3.9.0

# Data Validation
pydantic>=2.0.0

# Vector Database
qdrant-client>=1.7.0
weaviate-client>=4.0.0

# AI/ML
ollama>=0.1.0
openai>=1.0.0

# Utilities
python-dotenv
tenacity
rich
```

### External Services
| Service | Purpose | Default Port |
|---------|---------|--------------|
| Ollama | Local LLM inference | 11434 |
| OpenRouter | Fallback LLM API | HTTPS |
| Qdrant | Vector database | 6333 |
| Weaviate | Graph database | 8080 |

---

## Component Status

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| FastAPI App | main.py | ACTIVE | Entry point |
| API Routes | src/api/routes/ | ACTIVE | 13 routers |
| Socket.IO | src/api/handlers/ | ACTIVE | 18 events |
| Orchestrator | orchestrator_with_elisya.py | ACTIVE | Main logic |
| API Gateway | api_aggregator_v3.py | ACTIVE | LLM calls |
| Memory Manager | memory_manager.py | ACTIVE | Triple write |
| Hostess Agent | hostess_agent.py | ACTIVE | Routing |
| Eval Agent | eval_agent.py | ACTIVE | Scoring |
| CAM Engine | cam_engine.py | PARTIAL | Needs integration |
| Learner | learner_*.py | PARTIAL | Debug mode |
| MCP Server | mcp_server.py | ACTIVE | Tool server |

---

## Cleanup History

| Phase | What Removed | Commit | Date |
|-------|--------------|--------|------|
| 41.1 | archive/ (80MB) | - | 2026-01-05 |
| 41.2 | src/server/ (Flask) | cf9d2da | 2026-01-05 |
| 41.3 | Flask imports | f57ea97 | 2026-01-05 |

### Deprecated Files (not removed)
- `src/orchestration/key_management_api.py` - Flask-only, stubbed

---

## Environment Variables

```bash
# Required
OPENROUTER_KEY_1=sk-or-v1-...
OPENROUTER_KEY_2=sk-or-v1-...
OPENROUTER_KEY_3=sk-or-v1-...

# Optional
GEMINI_API_KEY=...
VETKA_PORT=5001
VETKA_HOST=0.0.0.0
VETKA_DEBUG=false

# Ollama
OLLAMA_HOST=http://localhost:11434

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Weaviate
WEAVIATE_HOST=localhost
WEAVIATE_PORT=8080
```

---

## Quick Reference

### Start Server
```bash
./run.sh
# or
python3 main.py
```

### Access Points
- API Docs: http://localhost:5001/docs
- Health Check: http://localhost:5001/api/health
- Frontend: http://localhost:3000 (dev server)

### Key Files
| Purpose | File |
|---------|------|
| Entry point | main.py |
| Initialization | src/initialization/components_init.py |
| Main orchestrator | src/orchestration/orchestrator_with_elisya.py |
| LLM gateway | src/elisya/api_aggregator_v3.py |
| Memory storage | src/orchestration/memory_manager.py |
| Agent tools | src/agents/tools.py |

---

**Last Updated:** 2026-01-05
**Next Phase:** 43 (Observability) or Feature Development
