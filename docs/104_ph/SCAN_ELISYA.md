# ELISYA Glossary Scan - Phase 104

## Definition
**ELISYA** = Middleware + Orchestra (coordination of agents in group chat)

Components:
- **ElisyaState**: Shared memory layer for all agents
- **ElisyaMiddleware**: Context reframing + state updates per agent
- **Semantic Path**: Growing context path as conversation evolves
- **ConversationMessage**: Individual agent turns in workflow

---

## ELISYA Core Files (src/elisya/)

| File | Components | Role | Usage |
|------|------------|------|-------|
| `src/elisya/__init__.py:1-50` | ElisyaState, ElisyaMiddleware, SemanticPathGenerator, ModelRouter, KeyManager | **Export Hub** - Central module for all ELISYA imports | Used by orchestrator_with_elisya.py, initialization modules |
| `src/elisya/state.py:1-200` | ElisyaState (dataclass), ConversationMessage, FewShotExample, LODLevel, SemanticTint | **Shared Memory** - Language for agents to communicate | Used by orchestrator_with_elisya.py, elisya_state_service.py |
| `src/elisya/middleware.py:1-300` | ElisyaMiddleware, MiddlewareConfig, ContextAction, LODLevel | **Context Reframing** - Prepare context per agent, update state after execution | Used by orchestrator_with_elisya.py, elisya_state_service.py, langgraph_nodes.py |
| `src/elisya/semantic_path.py` | SemanticPathGenerator, PathComponent | **Path Management** - Grows semantic context path as conversation evolves | Used by orchestrator_with_elisya.py, elisya_state_service.py |
| `src/elisya/model_router_v2.py` | ModelRouter, Provider, TaskType, ModelConfig | **Model Routing** - Intelligent LLM routing per task | Used by orchestrator_with_elisya.py, routing_service.py, model_routes.py |
| `src/elisya/api_aggregator_v3.py` | APIAggregator, call_model | **API Aggregation** - Unified model calling interface | Used by orchestrator_with_elisya.py, various handlers |
| `src/elisya/provider_registry.py` | ProviderRegistry, Provider, call_model_v2 | **Provider Detection** - Multi-provider support (OpenAI, Anthropic, Google, OpenRouter, xAI, Ollama) | Used by orchestrator_with_elisya.py, chat_handler.py, model_routes.py |
| `src/elisya/api_key_detector.py` | APIKeyDetector, ProviderConfig, detect_api_key | **API Key Detection** - Detect and manage API keys per provider | Used by hostess_agent.py, key_handlers.py |
| `src/elisya/key_learner.py` | KeyLearner, get_key_learner | **Key Learning** - Learn and cache API keys from user input | Used by hostess_agent.py, key_handlers.py |
| `src/elisya/key_manager.py` | KeyManager, ProviderType, APIKeyRecord | **Key Management** - Store and retrieve API keys | Used by orchestrator_with_elisya.py |
| `src/elisya/llm_core.py` | LLMCore, LLMExecutor | **LLM Execution** - Core LLM call abstraction | Core dependency for api_aggregator_v3.py |
| `src/elisya/llm_executor_bridge.py` | LLMExecutorBridge | **Bridge** - Interface between ELISYA and LLM execution | Used by initialization modules |
| `src/elisya/direct_api_calls.py` | call_openai_direct, call_anthropic_direct, call_google_direct | **Direct Calls** - Provider-specific API calls | Used by api_aggregator_v3.py |

---

## ELISYA Service Integration (src/orchestration/services/)

| File:Line | Component | Role | Chat Integration |
|-----------|-----------|------|------------------|
| `src/orchestration/services/elisya_state_service.py:1-150` | **ElisyaStateService** | **State Management Hub** - Creates/manages ElisyaState per workflow | ✅ YES - Used by chat_handler.py |
| `src/orchestration/services/elisya_state_service.py:22-30` | class ElisyaStateService | Service initialization with middleware | ✅ Group chat workflows |
| `src/orchestration/services/elisya_state_service.py:36-48` | __init__ middleware setup | Initializes ElisyaMiddleware with Qdrant integration | ✅ Semantic context enrichment |
| `src/orchestration/services/elisya_state_service.py:54-80` | get_or_create_state() | Creates ElisyaState for workflow_id + feature | ✅ Per-group-chat state |
| `src/orchestration/services/elisya_state_service.py:86-110` | update_state() | Updates state after agent execution | ✅ Agent output tracking |
| `src/orchestration/services/elisya_state_service.py:109-120` | reframe_context() | Reframes context for agent_type | ✅ Per-agent context |
| `src/orchestration/services/__init__.py:23` | ElisyaStateService export | Central service export | ✅ Imported by orchestrator_with_elisya |

---

## ELISYA in Main Orchestrator (src/orchestration/orchestrator_with_elisya.py)

| Line | Usage | Role | Chat Integration |
|------|-------|------|------------------|
| **65-66** | `from src.elisya.state import ElisyaState, ConversationMessage` | **State Import** | ✅ Group chat message coordination |
| **66** | `from src.elisya.middleware import ElisyaMiddleware, MiddlewareConfig` | **Middleware Import** | ✅ Context reframing per agent |
| **69** | `from src.elisya.model_router_v2 import ModelRouter, TaskType` | **Model Router Import** | ✅ Agent-specific model selection |
| **75** | `from src.elisya.semantic_path import get_path_generator` | **Path Generator Import** | ✅ Growing conversation context |
| **142-143** | Comments: ElisyaState + ElisyaMiddleware | **Core Architecture Docs** | ✅ Multi-agent coordination |
| **199** | Import ElisyaStateService | **Service Import** | ✅ Delegated state management |
| **208** | `self.elisya_service = ElisyaStateService(memory_manager=...)` | **Service Initialization** | ✅ Phase 54.1 refactor |
| **280-282** | `_get_or_create_state()` method | **State Creation** | ✅ Per-workflow state |
| **290-292** | `_update_state()` method | **State Updates** | ✅ Post-agent execution |
| **1224** | `state: ElisyaState` parameter in method | **Type Signature** | ✅ Agent execution parameter |
| **1235** | `state = self.elisya_service.reframe_context(...)` | **Context Reframing Call** | ✅ Per-agent context prep |
| **1467** | "Initialize ElisyaState" comment | **State Init Point** | ✅ Workflow start |
| **2054** | "Initialize ElisyaState" comment | **State Init Point** | ✅ Parallel execution |
| **2279** | `get_state()` getter method | **State Retrieval** | ✅ Query workflow state |
| **2303** | "Single-agent execution for GroupChat integration" comment | **GroupChat Integration** | ✅ EXPLICIT GROUP CHAT SUPPORT |
| **2313** | Return type: `{'output', 'state': ElisyaState, ...}` | **Return Format** | ✅ State in output |
| **2412, 2427** | `group_id: str = None` parameter | **Group Chat Parameter** | ✅ Optional group chat ID |
| **2510, 2531** | `group_id: str = None` parameter | **Group Chat Parameter** | ✅ Optional group chat ID |

---

## ELISYA in Autogen Extension (src/orchestration/autogen_extension.py)

| Line | Usage | Role | Chat Integration |
|------|-------|------|------------------|
| **18** | `from src.elisya.state import ElisyaState, ConversationMessage` | **State Import for Autogen** | ✅ GroupChat coordination |
| **47** | Comment: "Uses Autogen GroupChat for multi-agent conversation" | **GroupChat Integration** | ✅ EXPLICIT GROUPCHAT |
| **91** | `from autogen import AssistantAgent, GroupChat, GroupChatManager` | **Autogen Import** | ✅ Third-party GroupChat |
| **98** | "Initialize ElisyaState for this workflow" | **ElisyaState Usage** | ✅ Per-workflow state |
| **137** | `groupchat = GroupChat(...)` | **GroupChat Creation** | ✅ Multi-agent conversation |
| **139-147** | GroupChat initialization + manager setup | **GroupChat Configuration** | ✅ Max 4 rounds for agents |
| **165, 172** | Extract messages from groupchat | **GroupChat Message Extraction** | ✅ Collect agent outputs |
| **175** | "Autogen GroupChat completed" | **Completion Tracking** | ✅ Message aggregation |

---

## ELISYA in LangGraph Integration (src/orchestration/langgraph_nodes.py)

| Line | Component | Role | Chat Integration |
|------|-----------|------|------------------|
| **62** | `from src.elisya.middleware import ElisyaMiddleware` | **Middleware Import** | ✅ Node context reframing |
| **291** | "Convert to ElisyaState for backwards compatibility" | **State Conversion** | ✅ VETKAState → ElisyaState |
| **387** | "Convert to ElisyaState" | **State Conversion** | ✅ Format conversion |
| **652** | "Create ElisyaStates for each agent" | **Multi-Agent State Creation** | ✅ Per-agent state init |
| **1104** | Function: `create_elisya_state()` | **State Creator** | ✅ VETKAState → ElisyaState |
| **1108-1110** | Create ElisyaState from VETKAState | **State Bridge** | ✅ Format conversion |

---

## ELISYA in LangGraph State (src/orchestration/langgraph_state.py)

| Line | Usage | Role | Chat Integration |
|------|-------|------|------------------|
| **13** | Comment: "ElisyaState fields (context, semantic_path, LOD)" | **State Field Documentation** | ✅ Field mapping |
| **52** | "Combines ElisyaState + workflow data" | **State Combination** | ✅ Hybrid state model |
| **64** | `group_id: Optional[str]` field | **Group Chat ID Field** | ✅ EXPLICIT GROUP CHAT |
| **143** | `group_id: Optional group chat ID` | **Group Chat Parameter Docs** | ✅ Group identification |
| **231-240** | `convert_to_elisya_format()` function | **Format Converter** | ✅ VETKAState → ElisyaState |

---

## ELISYA in Memory Integration (src/orchestration/memory_manager.py)

| File:Line | Component | Role | Chat Integration |
|-----------|-----------|------|------------------|
| `src/orchestration/memory_manager.py:7` | @calledBy orchestrator_with_elisya.py | Memory backend for ELISYA | ✅ Qdrant vector storage |

---

## ELISYA in Memory & Qdrant (src/memory/)

| File:Line | Usage | Role | Chat Integration |
|-----------|-------|------|------------------|
| `src/memory/qdrant_client.py:9` | Used by orchestrator_with_elisya.py | Qdrant integration | ✅ Vector search for context |
| `src/memory/qdrant_client.py:75` | 'VetkaGroupChat' collection | **Group Chat Collection** | ✅ EXPLICIT GROUP CHAT |
| `src/memory/qdrant_client.py:714-775` | `upsert_message_to_group_chat()` | **Group Chat Storage** | ✅ Persist group messages |
| `src/memory/engram_user_memory.py:9` | Used by orchestrator_with_elisya.py | User memory layer | ✅ Agent context building |
| `src/memory/snapshot.py:397` | `collection="vetka_elisya"` | Collection reference | ✅ Default ELISYA collection |

---

## ELISYA in Provider Registry & Routing

| File:Line | Component | Role | Chat Integration |
|-----------|-----------|------|------------------|
| `src/elisya/provider_registry.py:737` | Comment: Phase 93.6 - "Fix 400 Bad Request in group chat" | **Group Chat Provider Fix** | ✅ Group chat-specific fix |
| `src/orchestration/services/routing_service.py:6` | Phase 54.1 refactor from orchestrator_with_elisya.py | Model routing service | ✅ Agent-specific routing |
| `src/api/handlers/chat_handler.py:62` | `from src.elisya.provider_registry import ProviderRegistry, Provider` | **Provider Detection in Chat** | ✅ Direct model calls |

---

## ELISYA in MCP Integration

| File:Line | Component | Role | Chat Integration |
|-----------|-----------|------|------------------|
| `src/mcp/vetka_mcp_bridge.py:95-125` | `log_to_group_chat()`, `log_mcp_request/response()` | **Log MCP to Group Chat** | ✅ System logging in group |
| `src/mcp/tools/workflow_tools.py:148` | Import OrchestratorWithElisya | Workflow tool orchestration | ✅ Parallel agent execution |
| `src/mcp/tools/llm_call_tool.py:167, 592` | `from src.elisya.provider_registry` | Model provider detection | ✅ Tool-level model routing |

---

## ELISYA in API Handlers

| File:Line | Component | Role | Chat Integration |
|-----------|-----------|------|------------------|
| `src/api/handlers/chat_handler.py:62-77` | `detect_provider()` wrapper | **Provider Detection** | ✅ Chat model selection |
| `src/api/handlers/user_message_handler.py:60-63` | Provider imports from elisya | **Message Routing** | ✅ User message → agent |
| `src/api/handlers/key_handlers.py:64-65` | `from src.elisya.api_key_detector` | **API Key Management** | ✅ Chat key validation |

---

## ELISYA in Agents

| File:Line | Component | Role | Chat Integration |
|-----------|-----------|------|------------------|
| `src/agents/hostess_agent.py:755, 791, 896-897` | `from src.elisya.key_learner` | **Key Learning in Hostess** | ✅ Group chat helper |
| `src/agents/arc_solver_agent.py:1120` | `from src.elisya.api_aggregator_v3 import APIAggregator` | **API Aggregation** | ✅ ARC solving |
| `src/agents/tools.py:14` | Used by orchestrator_with_elisya.py | Tool definitions | ✅ Agent tool registry |
| `src/agents/role_prompts.py:9` | Used by orchestrator_with_elisya.py | Agent role definitions | ✅ Agent personas |

---

## ELISYA Collection References

| File:Line | Collection Name | Purpose | Group Chat Related |
|-----------|-----------------|---------|-------------------|
| `src/knowledge_graph/graph_builder.py:49` | `"vetka_elisya"` | Main ELISYA collection | ✅ Core knowledge storage |
| `src/memory/qdrant_client.py:75` | `'VetkaGroupChat'` | Group chat messages | ✅ EXPLICIT GROUP CHAT |
| `src/memory/qdrant_client.py:322` | `'vetka_elisya'` | Default collection | ✅ Fallback storage |
| `src/memory/snapshot.py:397` | `"vetka_elisya"` | Snapshot storage | ✅ State snapshots |

---

## KEY FINDINGS

### 1. **Core ELISYA Architecture**
- **ElisyaState**: Shared memory language for agent communication
- **ElisyaMiddleware**: Context reframing per agent (LOD, semantic tint, Qdrant enrichment)
- **SemanticPath**: Growing context as conversation evolves
- **ConversationMessage**: Individual agent turns

### 2. **Group Chat Integration**
✅ **EXPLICIT GROUPCHAT SUPPORT** in:
- `orchestrator_with_elisya.py:2303` - "Single-agent execution for GroupChat integration"
- `orchestrator_with_elisya.py:2412, 2427, 2510, 2531` - `group_id` parameters
- `autogen_extension.py:47, 91, 137-147` - Autogen GroupChat usage
- `langgraph_state.py:64` - `group_id: Optional[str]` field
- `qdrant_client.py:75, 714-775` - `VetkaGroupChat` collection
- Memory layer fully supports group chat message persistence

### 3. **Middleware Features (ElisyaMiddleware)**
- **reframe()**: Prepare context for agent
  - Fetch history from semantic_path
  - Truncate by LOD (GLOBAL/TREE/LEAF/FULL)
  - Add few-shots (score > 0.8 threshold)
  - Apply semantic tint filter (Security/Performance/Reliability/Scalability)
  - Fetch similar context from Qdrant (Phase 15-3)
- **update()**: Update state after agent execution
  - Store conversation message
  - Update semantic path
  - Track metrics (timestamp, retry_count, score)

### 4. **Service Delegation (Phase 54.1)**
- **ElisyaStateService**: Centralized state management
- Delegated from `orchestrator_with_elisya.py`
- Methods:
  - `get_or_create_state(workflow_id, feature)`
  - `update_state(state, speaker, output)`
  - `reframe_context(state, agent_type)`
  - `get_state(workflow_id)`

### 5. **Provider Routing**
- **ProviderRegistry**: Multi-provider support
  - OpenAI, Anthropic, Google/Gemini, OpenRouter, xAI, Ollama
- **ModelRouter**: Task-aware routing (PLANNING/CODING/ANALYSIS/EVALUATION)
- Phase 93.6 fix: Group chat-specific provider handling

### 6. **Memory Integration**
- **Qdrant Collections**:
  - `vetka_elisya`: Main collection (default)
  - `VetkaGroupChat`: Group chat messages
- **Semantic Search**: Enriches context with similar past outputs
- **Vector Storage**: Enables semantic path generation

### 7. **Agent Coordination**
- **Conversation History**: All agent turns tracked
- **Few-Shot Learning**: Quality examples (score > 0.8) included in context
- **Parallel Execution**: Dev || QA with synchronized state
- **Autogen Integration**: Python-Autogen GroupChat support

---

## STATISTICS

| Category | Count |
|----------|-------|
| **ELISYA Core Files** | 13 files |
| **ELISYA-dependent Files** | 78 files (grep elisya count) |
| **Middleware References** | 16 files |
| **Orchestra/GroupChat References** | 128 files |
| **ElisyaState Usages** | 12 explicit lines |
| **Group Chat Collections** | 2 (vetka_elisya, VetkaGroupChat) |
| **Qdrant Integrations** | 15+ locations |

---

## SUMMARY

ELISYA is a **complete middleware orchestra for group chat agent coordination**:

1. **State Layer** (ElisyaState): Shared memory where agents read task, interpret, write results
2. **Middleware Layer** (ElisyaMiddleware): Per-agent context reframing with semantic enrichment
3. **Memory Layer** (Qdrant): Vector storage for semantic search + group chat persistence
4. **Service Layer** (ElisyaStateService): Centralized state management (Phase 54.1)
5. **Routing Layer** (ProviderRegistry + ModelRouter): Intelligent model selection per agent
6. **Integration Layer**: Autogen GroupChat, LangGraph, MCP tools, API handlers

**Status**: ACTIVE Phase 96 with Phase 54.1 refactoring complete.

Generated: 2026-01-31
