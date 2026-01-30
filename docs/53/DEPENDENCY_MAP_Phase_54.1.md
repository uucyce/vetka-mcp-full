# VETKA Dependency Map - Phase 54.1 (Service-Based Architecture)

**Дата**: 2026-01-08
**Версия**: Phase 54.1 (После рефакторинга)
**Статус**: ✅ Актуально

---

## 🏗️ Высокоуровневая Архитектура

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           VETKA APPLICATION                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐     ┌──────────────────────────────────────────┐   │
│  │   Frontend    │────▶│         Flask Backend (app/)             │   │
│  │  (Phase 10)   │     │  - main.py (FastAPI endpoints)           │   │
│  └───────────────┘     │  - Socket.IO events                      │   │
│                        └───────────────┬──────────────────────────┘   │
│                                        │                              │
│                                        ▼                              │
│                        ┌────────────────────────────────────────┐    │
│                        │   OrchestratorWithElisya (1661 lines)  │    │
│                        │   Phase 54.1: Service-Based Facade     │    │
│                        └───────────────┬────────────────────────┘    │
│                                        │                              │
│         ┌──────────────────────────────┼───────────────────────────┐ │
│         │                              │                           │ │
│         ▼                              ▼                           ▼ │
│  ┌─────────────┐              ┌──────────────┐           ┌──────────┤
│  │ 6 Services  │              │  4 Agents    │           │ Memory   │
│  │ (Phase 54.1)│              │  (PM/Dev/    │           │ Systems  │
│  └─────────────┘              │  QA/Arch)    │           └──────────┘
│                               └──────────────┘                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Сервис-Ориентированная Архитектура (Phase 54.1)

### Orchestrator Facade Pattern

```
OrchestratorWithElisya (Facade)
│
├─▶ MemoryService          # Memory operations
│   └─▶ MemoryManager
│       ├─▶ Changelog (JSON)
│       ├─▶ Weaviate
│       └─▶ Qdrant
│
├─▶ ElisyaStateService     # State management
│   ├─▶ ElisyaMiddleware
│   ├─▶ SemanticPathGenerator
│   └─▶ ElisyaState (per workflow)
│
├─▶ APIKeyService          # API key management
│   └─▶ KeyManager
│       ├─▶ config.json
│       └─▶ Environment vars
│
├─▶ RoutingService         # Model routing
│   └─▶ ModelRouter
│       └─▶ TaskType mapping
│
├─▶ CAMIntegration         # CAM Engine
│   └─▶ VETKACAMEngine
│       ├─▶ Pruning
│       └─▶ Merging
│
└─▶ VETKATransformerService # VETKA-JSON
    ├─▶ Phase10Transformer
    └─▶ VetkaValidator
```

---

## 🔄 Dependency Graph (Детальный)

### 1. OrchestratorWithElisya → Services

```python
# orchestrator_with_elisya.py (1661 lines)
from src.orchestration.services import (
    APIKeyService,           # ✅ NEW (Phase 54.1)
    MemoryService,          # ✅ NEW (Phase 54.1)
    CAMIntegration,         # ✅ NEW (Phase 54.1)
    VETKATransformerService,# ✅ NEW (Phase 54.1)
    ElisyaStateService,     # ✅ NEW (Phase 54.1)
    RoutingService          # ✅ NEW (Phase 54.1)
)

# Direct dependencies (non-service)
from src.agents import (
    VETKAPMAgent,
    VETKADevAgent,
    VETKAQAAgent,
    VETKAArchitectAgent
)
from src.orchestration.query_dispatcher import get_dispatcher
from src.agents.arc_solver_agent import create_arc_solver
```

---

### 2. Services → Dependencies

#### 2.1 APIKeyService (165 lines)
```python
# src/orchestration/services/api_key_service.py
import os
from src.elisya.key_manager import KeyManager, ProviderType

Dependencies:
  ├─▶ KeyManager (src/elisya/key_manager.py)
  ├─▶ config.json (API keys storage)
  └─▶ os.environ (environment variables)
```

#### 2.2 MemoryService (126 lines)
```python
# src/orchestration/services/memory_service.py
from src.orchestration.memory_manager import MemoryManager

Dependencies:
  └─▶ MemoryManager (src/orchestration/memory_manager.py)
      ├─▶ Changelog (data/changelog.json)
      ├─▶ Weaviate client
      └─▶ Qdrant client
```

#### 2.3 CAMIntegration (153 lines)
```python
# src/orchestration/services/cam_integration.py
from src.orchestration.cam_engine import VETKACAMEngine

Dependencies:
  └─▶ VETKACAMEngine (src/orchestration/cam_engine.py)
      ├─▶ MemoryManager
      ├─▶ Graph analysis
      └─▶ Pruning/merging algorithms
```

#### 2.4 VETKATransformerService (274 lines)
```python
# src/orchestration/services/vetka_transformer_service.py
from src.transformers.phase9_to_vetka import Phase10Transformer
from src.validators.vetka_validator import VetkaValidator

Dependencies:
  ├─▶ Phase10Transformer (src/transformers/phase9_to_vetka.py)
  ├─▶ VetkaValidator (src/validators/vetka_validator.py)
  ├─▶ config/vetka_schema_v1.3.json
  ├─▶ Socket.IO (for UI emission)
  └─▶ output/ (VETKA-JSON files)
```

#### 2.5 ElisyaStateService (145 lines)
```python
# src/orchestration/services/elisya_state_service.py
from src.elisya.state import ElisyaState
from src.elisya.middleware import ElisyaMiddleware, MiddlewareConfig
from src.elisya.semantic_path import get_path_generator

Dependencies:
  ├─▶ ElisyaState (src/elisya/state.py)
  ├─▶ ElisyaMiddleware (src/elisya/middleware.py)
  ├─▶ SemanticPathGenerator (src/elisya/semantic_path.py)
  └─▶ MemoryManager (for Qdrant integration)
```

#### 2.6 RoutingService (76 lines)
```python
# src/orchestration/services/routing_service.py
from src.elisya.model_router_v2 import ModelRouter, Provider, TaskType

Dependencies:
  └─▶ ModelRouter (src/elisya/model_router_v2.py)
      ├─▶ TaskType mapping
      └─▶ Provider selection logic
```

---

## 🎯 Agents → Tools (Phase 17-L)

```
VETKAPMAgent
├─▶ search_semantic       # Qdrant semantic search
├─▶ get_tree_context      # VETKA tree navigation
└─▶ create_artifact       # Artifact creation

VETKADevAgent
├─▶ search_semantic
├─▶ get_tree_context
├─▶ create_artifact
├─▶ write_file            # File operations
└─▶ edit_file

VETKAQAAgent
├─▶ search_semantic
├─▶ get_tree_context
└─▶ create_artifact

VETKAArchitectAgent
├─▶ search_semantic
├─▶ get_tree_context
└─▶ create_artifact

All Agents (Phase 22)
└─▶ camera_focus          # 3D camera navigation
```

**Tool Registry**: `src/tools/registry.py`

---

## 🧠 Memory Systems (Triple-Write)

```
MemoryManager
│
├─▶ 1. Changelog (JSON)
│   └─▶ data/changelog.json
│       └─▶ Fast local storage
│
├─▶ 2. Weaviate (Vector DB)
│   └─▶ http://localhost:8765
│       ├─▶ Semantic search
│       └─▶ GraphQL queries
│
└─▶ 3. Qdrant (Vector DB)
    └─▶ http://localhost:6333
        ├─▶ Semantic search (Phase 15-3)
        ├─▶ Middleware integration
        └─▶ Few-shot examples
```

**Triple-Write Flow**:
```
Agent Output
    │
    ├─▶ Changelog (JSON)      ✅ Always succeeds
    ├─▶ Weaviate              ⚠️ May fail gracefully
    └─▶ Qdrant                ⚠️ May fail gracefully

Result: Degradation mode if some fail
```

---

## 🔌 Elisya Integration (Phase 54.1 Services)

### ElisyaStateService Flow

```
User Request
    │
    ▼
ElisyaStateService.get_or_create_state()
    │
    ├─▶ Generate semantic path
    │   └─▶ SemanticPathGenerator
    │
    ├─▶ Create ElisyaState
    │   ├─▶ workflow_id
    │   ├─▶ semantic_path
    │   ├─▶ raw_context
    │   └─▶ conversation_history
    │
    ▼
Per Agent:
    │
    ├─▶ ElisyaStateService.reframe_context()
    │   └─▶ ElisyaMiddleware.reframe()
    │       ├─▶ Qdrant semantic search
    │       ├─▶ Few-shot examples
    │       └─▶ LOD truncation
    │
    ├─▶ Agent.process()
    │
    └─▶ ElisyaStateService.update_state()
        └─▶ ElisyaMiddleware.update()
            ├─▶ Add to conversation_history
            └─▶ Update semantic_path
```

---

## 🔑 API Key Management (Phase 54.1)

### APIKeyService Flow

```
APIKeyService
    │
    ├─▶ Load keys from config.json
    │   └─▶ KeyManager.load_from_config()
    │
    ├─▶ Get key for provider
    │   └─▶ KeyManager.get_active_key(provider)
    │       ├─▶ Round-robin rotation
    │       └─▶ Failure tracking
    │
    ├─▶ Inject to environment
    │   └─▶ inject_key_to_env(provider, key)
    │       ├─▶ Save old env vars
    │       └─▶ Set new env vars
    │
    └─▶ Restore environment
        └─▶ restore_env(saved_env)
            └─▶ Restore old env vars
```

**Supported Providers**:
- OpenRouter (10 keys в config.json)
- Gemini (0 keys)
- Ollama (local, no key needed)

---

## 🌳 VETKA Transformation (Phase 54.1)

### VETKATransformerService Flow

```
Workflow Complete
    │
    ▼
VETKATransformerService.transform_and_emit()
    │
    ├─▶ collect_infrastructure_data()
    │   ├─▶ Learning system
    │   ├─▶ Routing decisions
    │   ├─▶ Elisya middleware
    │   └─▶ Storage status
    │
    ├─▶ build_phase9_output()
    │   ├─▶ PM result
    │   ├─▶ Architect result
    │   ├─▶ Dev result
    │   ├─▶ QA result
    │   ├─▶ ARC suggestions
    │   ├─▶ Metrics
    │   └─▶ Infrastructure
    │
    ├─▶ Phase10Transformer.transform()
    │   └─▶ Phase 9 → VETKA-JSON v1.3
    │
    ├─▶ VetkaValidator.validate()
    │   └─▶ Schema validation
    │
    ├─▶ Save to output/vetka_{workflow_id}.json
    │
    └─▶ Socket.IO emit 'vetka_tree_update'
        └─▶ Frontend receives tree
```

---

## 🎨 Model Routing (Phase 54.1)

### RoutingService Decision Tree

```
Task + Agent Type
    │
    ▼
RoutingService.get_routing_for_task()
    │
    ├─▶ Map agent_type → task_type
    │   ├─▶ PM        → REASONING
    │   ├─▶ Architect → REASONING
    │   ├─▶ Dev       → CODE
    │   └─▶ QA        → TESTING
    │
    └─▶ ModelRouter.route(task)
        │
        ├─▶ Check task complexity
        ├─▶ Check provider availability
        └─▶ Return routing decision
            ├─▶ model: "qwen2:7b"
            ├─▶ provider: "ollama"
            └─▶ task_type: "CODE"
```

**Available Models** (8 total):
- Ollama: qwen2:7b, llama3, deepseek, etc.
- OpenRouter: claude-3.5-sonnet, gpt-4, etc.
- Gemini: gemini-pro (if key available)

---

## 🌱 CAM Integration (Phase 54.1)

### CAMIntegration Maintenance Flow

```
Workflow Complete
    │
    ▼
CAMIntegration.maintenance_cycle()
    │
    ├─▶ VETKACAMEngine.prune_low_entropy(threshold=0.2)
    │   └─▶ Analyze node entropy
    │       └─▶ Remove low-value nodes
    │
    └─▶ VETKACAMEngine.merge_similar_subtrees(threshold=0.92)
        └─▶ Find similar subtrees
            └─▶ Merge duplicates
```

**Triggered by**:
- Event: `workflow_completed`
- Manual: API endpoint

---

## 📊 File Dependencies by Module

### Core Orchestration
```
src/orchestration/
├── orchestrator_with_elisya.py (1661 lines) ✅ REFACTORED
│   └─▶ Uses 6 services (Phase 54.1)
│
├── services/                              ✅ NEW (Phase 54.1)
│   ├── __init__.py
│   ├── api_key_service.py       (165 lines)
│   ├── memory_service.py        (126 lines)
│   ├── cam_integration.py       (153 lines)
│   ├── vetka_transformer_service.py (274 lines)
│   ├── elisya_state_service.py  (145 lines)
│   └── routing_service.py       (76 lines)
│
├── memory_manager.py
├── progress_tracker.py
├── query_dispatcher.py
├── chain_context.py
├── response_formatter.py
└── cam_engine.py
```

### Agents
```
src/agents/
├── base_agent.py                # BaseAgent class
├── vetka_pm.py                  # PM Agent
├── vetka_dev.py                 # Dev Agent
├── vetka_qa.py                  # QA Agent
├── vetka_architect.py           # Architect Agent
├── streaming_agent.py
├── arc_solver_agent.py
└── tools/
    ├── __init__.py
    ├── search_semantic_tool.py  # Phase 19
    ├── get_tree_context_tool.py # Phase 19
    ├── create_artifact_tool.py
    └── camera_focus_tool.py     # Phase 22
```

### Elisya
```
src/elisya/
├── state.py                     # ElisyaState
├── middleware.py                # ElisyaMiddleware
├── model_router_v2.py           # ModelRouter
├── key_manager.py               # KeyManager
├── semantic_path.py             # SemanticPathGenerator
└── api_aggregator_v3.py         # LLM calls
```

### Transformers & Validators
```
src/transformers/
└── phase9_to_vetka.py           # Phase10Transformer

src/validators/
└── vetka_validator.py           # VetkaValidator

config/
└── vetka_schema_v1.3.json       # JSON Schema
```

---

## 🔄 Execution Flow (Full Workflow)

### Sequential Mode
```
1. User Request → Flask Backend
2. Backend → OrchestratorWithElisya.execute_full_workflow_streaming()
3. Orchestrator → ElisyaStateService.get_or_create_state()
4. PM Agent:
   ├─▶ ElisyaStateService.reframe_context('PM')
   ├─▶ RoutingService.get_routing_for_task()
   ├─▶ APIKeyService.get_key() + inject_key_to_env()
   ├─▶ Agent.process() with tools
   ├─▶ ElisyaStateService.update_state()
   └─▶ MemoryService.save_agent_output()
5. Architect Agent (same flow)
6. Dev Agent (same flow)
7. QA Agent (same flow)
8. VETKATransformerService.transform_and_emit()
9. CAMIntegration.emit_workflow_complete_event()
10. Response → Frontend
```

### Parallel Mode
```
1-3. Same as sequential
4. PM Agent → output
5. Architect Agent → output
6. Dev & QA Agents (PARALLEL):
   ├─▶ Thread 1: Dev Agent
   └─▶ Thread 2: QA Agent
7-10. Same as sequential
```

---

## 🔌 External Dependencies

### Python Packages (key ones)
```
Flask / FastAPI          # Web framework
Socket.IO                # Real-time communication
Weaviate Client          # Vector DB
Qdrant Client            # Vector DB
Ollama                   # Local LLM
OpenRouter SDK           # Cloud LLM API
Pydantic                 # Data validation
```

### External Services
```
Weaviate    → localhost:8765    # Vector DB
Qdrant      → localhost:6333    # Vector DB
Ollama      → localhost:11434   # Local LLM
OpenRouter  → api.openrouter.ai # Cloud LLM API
```

---

## 📈 Dependency Changes (Phase 54.1)

### Before Refactoring
```
OrchestratorWithElisya (1968 lines)
├─▶ Direct dependency on 15+ modules
├─▶ God Object with 8+ responsibilities
└─▶ Hard to test, maintain, extend
```

### After Refactoring (Phase 54.1)
```
OrchestratorWithElisya (1661 lines)
├─▶ Depends on 6 services (clean interfaces)
├─▶ Single Responsibility (coordination only)
└─▶ Easy to test, maintain, extend

6 New Services (828 lines total)
├─▶ APIKeyService (165 lines)
├─▶ MemoryService (126 lines)
├─▶ CAMIntegration (153 lines)
├─▶ VETKATransformerService (274 lines)
├─▶ ElisyaStateService (145 lines)
└─▶ RoutingService (76 lines)
```

**Benefits**:
- ✅ Reduced orchestrator by 307 lines (-15.6%)
- ✅ Clear separation of concerns
- ✅ Each service independently testable
- ✅ Easier to add new services
- ✅ 100% backwards compatible

---

## 🎯 Service Dependency Matrix

| Service | Depends On |
|---------|------------|
| **APIKeyService** | KeyManager, config.json, os.environ |
| **MemoryService** | MemoryManager, Changelog, Weaviate, Qdrant |
| **CAMIntegration** | VETKACAMEngine, MemoryManager |
| **VETKATransformerService** | Phase10Transformer, VetkaValidator, Socket.IO |
| **ElisyaStateService** | ElisyaState, ElisyaMiddleware, SemanticPathGenerator, MemoryManager |
| **RoutingService** | ModelRouter, TaskType, Provider |

---

## 🧪 Testing Boundaries

### Unit Testing (by service)
```python
# Test APIKeyService independently
def test_api_key_service():
    service = APIKeyService()
    assert service.get_key('ollama') is None

# Test MemoryService independently
def test_memory_service():
    service = MemoryService()
    service.save_agent_output('PM', 'output', 'wf_123', 'planning')

# Test CAMIntegration independently
async def test_cam_integration():
    service = CAMIntegration(memory_manager=mock_memory)
    result = await service.maintenance_cycle()
    assert 'prune_count' in result

# etc. for all 6 services
```

### Integration Testing
```python
# Test orchestrator with all services
def test_orchestrator_initialization():
    orch = OrchestratorWithElisya()
    assert hasattr(orch, 'memory_service')
    assert hasattr(orch, 'elisya_service')
    # ... etc for all 6 services
```

---

## 📝 Configuration Files

```
config.json               # API keys (OpenRouter, Gemini)
vetka_schema_v1.3.json   # VETKA-JSON schema
tree_data.json           # Knowledge graph
data/changelog.json      # Memory changelog
data/chat_history.json   # Per-file chat history (Phase 51.1)
```

---

## 🚀 Future Extensions (Easy with Services)

### Potential New Services
```
src/orchestration/services/
├── eval_agent_service.py      # Extract EvalAgent logic
├── arc_solver_service.py      # Extract ARC Solver logic
├── dispatcher_service.py      # Extract QueryDispatcher logic
├── websocket_service.py       # Extract Socket.IO logic
└── learning_service.py        # Extract learning system logic
```

**Impact**: Minimal changes to orchestrator, just add new service

---

## 🔗 Key Relationships

```
User Request
    ↓
Flask Backend
    ↓
OrchestratorWithElisya (Facade)
    ↓
┌─────────────┬──────────────┬──────────────┬──────────────┐
│             │              │              │              │
▼             ▼              ▼              ▼              ▼
Services     Agents      Elisya         Memory        Tools
(Phase 54.1) (PM/Dev/    (State/        (Triple-      (search_semantic,
             QA/Arch)    Middleware)    Write)        get_tree_context,
                                                      camera_focus, etc.)
```

---

## 📊 Metrics

| Metric | Value |
|--------|-------|
| **Total Python Files** | 196 files |
| **Orchestrator (before)** | 1968 lines |
| **Orchestrator (after)** | 1661 lines |
| **Services Created** | 6 services |
| **Total Service Lines** | 828 lines |
| **Reduction in Orchestrator** | -307 lines (-15.6%) |
| **Refactored Methods** | 16 methods |
| **External Services** | 4 (Weaviate, Qdrant, Ollama, OpenRouter) |
| **Agents** | 4 (PM, Dev, QA, Architect) |
| **Tools** | 5+ (search_semantic, get_tree_context, create_artifact, camera_focus, etc.) |

---

## 🎯 Conclusion

Phase 54.1 успешно трансформировал монолитный `orchestrator_with_elisya.py` в чистую **Service-Based Architecture**:

✅ **6 новых сервисов** с чёткими границами ответственности
✅ **Orchestrator уменьшен** на 307 строк (-15.6%)
✅ **100% backwards compatibility**
✅ **Улучшенная testability** - каждый сервис тестируется отдельно
✅ **Легче поддерживать** - код проще читать и понимать
✅ **Проще расширять** - добавление новых сервисов не затрагивает orchestrator

**Следующие шаги**: Phase 54.2 (Split knowledge_layout.py), Phase 54.3 (Cleanup unused imports)

---

**Автор**: Claude Code
**Дата**: 2026-01-08
**Версия**: Phase 54.1
