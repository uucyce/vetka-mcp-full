# PHASE 1 - HAIKU A: User Message Handler Refactoring Blueprint

**Status:** Code Audit Complete | Ready for Incremental Implementation
**File:** `/src/api/handlers/user_message_handler.py` (1694 lines)
**Last Updated:** 2026-01-22
**Phase:** Phase 80-90 (Incremental Refactoring)

## Executive Summary

The `user_message_handler.py` is a **God Object** exhibiting clear signs of SRP violation (1694 lines). This blueprint consolidates insights from three major LLM audits (Grok, Gemini, Claude) and proposes an incremental refactoring strategy using **Dependency Injection**, **Layered Architecture**, and **Interface-based Design**.

**Current State:**
- ✗ Single 1694-line handler managing 8+ distinct responsibilities
- ✗ Tight coupling to imports and concrete implementations
- ✗ Difficult to test individual concerns
- ✗ Hard to maintain and extend with new features

**Target State:**
- ✓ 7-10 focused modules, each < 300 lines
- ✓ Dependency injection for all external dependencies
- ✓ Clear interfaces between modules
- ✓ Testable and independently deployable

---

## Part 1: Architecture Overview

### Unified Module Structure

```
src/api/handlers/
├── user_message_handler.py          [REFACTORED: Main orchestrator, ~200 lines]
├── handlers/
│   ├── event_handlers.py            [NEW: Socket event emission, ~150 lines]
│   ├── message_parsers.py           [NEW: Parse mentions & directives, ~150 lines]
│   └── model_handlers.py            [NEW: Handle model routing, ~300 lines]
├── agents/
│   ├── agent_orchestrator.py        [NEW: Agent chain orchestration, ~250 lines]
│   ├── hostess_router.py            [NEW: Hostess routing logic, ~200 lines]
│   └── response_managers.py        [NEW: Response emission & formatting, ~200 lines]
├── context/
│   ├── context_builders.py          [NEW: Build context for agents, ~200 lines]
│   └── history_manager.py           [NEW: Chat history integration, ~150 lines]
├── models/
│   ├── model_client.py              [NEW: Direct model API calls, ~250 lines]
│   └── streaming_adapter.py         [NEW: Streaming support, ~150 lines]
└── interfaces/
    ├── message_handler.py           [NEW: Abstract message handler, ~50 lines]
    ├── model_client_interface.py    [NEW: Model client contract, ~40 lines]
    └── context_provider.py          [NEW: Context provider contract, ~40 lines]
```

### Dependency Injection Pattern

```
┌─────────────────────────────────────────────────┐
│  Message Handler (Entry Point)                   │
│  - Receives: DIContainer with all dependencies  │
│  - No imports of concrete classes               │
└──────────────┬──────────────────────────────────┘
               │
      ┌────────▼─────────┬──────────┬─────────┐
      │                  │          │         │
┌─────▼──────┐   ┌──────▼──┐  ┌───▼───┐  ┌──▼────┐
│ Message    │   │ Context │  │Agent  │  │Model  │
│ Parser     │   │Provider │  │Router │  │Client │
└────────────┘   └─────────┘  └───────┘  └───────┘
```

---

## Part 2: Refactoring Sections with Markers

### [REFACTOR-001] Main Handler Structure (Lines 39-160)

**Current Location:** `user_message_handler.py:39-160`
**Issue:** God object function definition with nested imports

**Action Items:**
1. Extract main handler logic into `MessageHandler` class with DI
2. Move phase comments into module docstring
3. Replace nested function with async method receiving `DIContainer`

**DI Pattern:**
```python
# BEFORE (lines 39-46)
def register_user_message_handler(sio, app=None):
    pending_api_keys = {}
    # 120+ nested imports follow

# AFTER
class UserMessageHandler:
    def __init__(self, container: DIContainer):
        self.sio = container.get('socketio')
        self.agents_service = container.get('agents_service')
        self.context_builder = container.get('context_builder')
        # ... other injected services

    async def handle_user_message(self, sid: str, data: dict) -> None:
        # Main orchestration logic
```

**Marker:** `[REFACTOR-001]` Insert before line 39
**Impact:** Eliminates nested function scope, enables testing

---

### [REFACTOR-002] Import Organization (Lines 49-128)

**Current Location:** `user_message_handler.py:49-128`
**Issue:** 80+ lines of imports inside function scope

**Extracted to Modules:**
- `message_parsers.py` → Lines 54, 57, 127-128 (parse_mentions, Message)
- `context_builders.py` → Lines 64-72 (handler_utils, context builders)
- `streaming_adapter.py` → Lines 92 (stream_response)
- `agent_orchestrator.py` → Lines 105-116 (workflow helpers)
- `models/model_client.py` → Lines 95-102 (chat_handler)

**DI-Pattern-001: Dependency Container Initialization**

```python
# In src/api/handlers/interfaces/dependency_container.py
class DIContainer:
    """Dependency Injection Container for message handler."""

    def __init__(self):
        self._services = {}

    def register(self, name: str, factory: Callable):
        self._services[name] = factory

    def get(self, name: str):
        if name not in self._services:
            raise ValueError(f"Service {name} not registered")
        return self._services[name]()

    def register_singleton(self, name: str, instance: Any):
        self._services[name] = lambda: instance
```

**Marker:** `[REFACTOR-002]` Insert before line 49
**Impact:** -80 lines of imports, +100 lines of interface definitions

---

### [REFACTOR-003] Session State Management (Lines 43-46)

**Current Location:** `user_message_handler.py:43-46`
**Issue:** Global `pending_api_keys` mutable state

**Extracted to:** `SessionStateManager` class in `handlers/session_manager.py`

```python
# NEW: src/api/handlers/handlers/session_manager.py
class SessionStateManager:
    """Manages per-session state (pending keys, context, etc)."""

    def __init__(self):
        self._session_state = {}  # {sid: {...}}

    def set_pending_key(self, sid: str, key: str, timestamp: float):
        if sid not in self._session_state:
            self._session_state[sid] = {}
        self._session_state[sid]['pending_key'] = key
        self._session_state[sid]['timestamp'] = timestamp

    def get_pending_key(self, sid: str) -> Optional[dict]:
        return self._session_state.get(sid, {}).get('pending_key')

    def clear_session(self, sid: str):
        if sid in self._session_state:
            del self._session_state[sid]
```

**Marker:** `[REFACTOR-003]` Replace lines 43-46
**Impact:** Singleton pattern, thread-safe state management

---

### [REFACTOR-004] Core Handler Entry Point (Lines 142-220)

**Current Location:** `user_message_handler.py:142-220`
**Issue:** Mixed concerns (validation, parsing, logging, state management)

**Split Into:**
- `handlers/validation.py` → Message validation (lines 166-219)
- `message_parsers.py` → Parse mentions & node context (lines 203-213)
- `handlers/event_handlers.py` → Logging & status emission (lines 156-193)

**DI-Pattern-002: Message Handler Interface**

```python
# NEW: src/api/handlers/interfaces/message_handler.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IMessageHandler(ABC):
    """Contract for message handling."""

    @abstractmethod
    async def handle_user_message(self, sid: str, data: Dict[str, Any]) -> None:
        """Handle incoming user message."""
        pass

    @abstractmethod
    async def validate_message(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate message structure. Returns (valid, error_msg)."""
        pass

    @abstractmethod
    async def parse_and_route(self, text: str) -> Dict[str, Any]:
        """Parse message for mentions/directives and determine route."""
        pass
```

**Marker:** `[REFACTOR-004]` Insert before line 142
**Impact:** Clear separation of concerns, testable validation

---

### [REFACTOR-005] Direct Model Call Path (Lines 227-601)

**Current Location:** `user_message_handler.py:227-601` (374 lines!)
**Issue:** MASSIVE single-shot code block for Ollama + OpenRouter handling

**Split Into:** `models/model_client.py` (~250 lines)

**DI-Pattern-003: Model Client Interface**

```python
# NEW: src/api/handlers/interfaces/model_client_interface.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ModelResponse:
    """Standard model response format."""
    content: str
    tokens_output: int
    tokens_input: int
    model: str
    agent: str
    metadata: Dict[str, Any]

class IModelClient(ABC):
    """Contract for model calls."""

    @abstractmethod
    async def call_model(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> ModelResponse:
        """Call a model and return response."""
        pass

    @abstractmethod
    async def stream_model(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 2000,
        on_token: Optional[callable] = None
    ) -> ModelResponse:
        """Stream model response token by token."""
        pass

    @abstractmethod
    def is_local_model(self, model: str) -> bool:
        """Check if model is local (Ollama)."""
        pass
```

**Breakdown:**

| Section | Lines | Content | New Module |
|---------|-------|---------|-----------|
| Model routing detection | 227-245 | Emit routing status | `event_handlers.py` |
| Ollama local call | 246-370 | Call local Ollama model | `models/model_client.py:OllamaModelClient` |
| OpenRouter streaming | 372-601 | Call remote model + streaming | `models/model_client.py:OpenRouterModelClient` |

**Key Refactorings:**

- Lines 246-370: Extract `OllamaModelClient.call_model()`
- Lines 372-601: Extract `OpenRouterModelClient.call_model()` + `stream_model()`
- Lines 378-387: Extract key rotation logic → `KeyRotationService`
- Lines 442-526: Extract streaming logic → `StreamingAdapter`

**Marker:** `[REFACTOR-005]` Lines 227-601 → Models Subsystem
**Impact:** -350 lines from main handler, +250 in focused modules

---

### [REFACTOR-006] @Mention Direct Call Path (Lines 603-891)

**Current Location:** `user_message_handler.py:603-891` (288 lines)
**Issue:** Duplicate of direct model call handling with @mention-specific logic

**Extracted to:** `message_parsers.py` + `handlers/mention_handler.py`

**Key Sections:**
- Lines 606-612: Parse mentions → `message_parsers.py:parse_mentions()`
- Lines 613-632: Routing decision → `handlers/mention_handler.py:MentionRouter`
- Lines 637-821: Model call → Reuse `IModelClient` from [REFACTOR-005]
- Lines 824-868: Response emission → `event_handlers.py`

**DI-Pattern-004: Message Parser Interface**

```python
# NEW: src/api/handlers/interfaces/message_parser.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any

class IMentionParser(ABC):
    """Contract for parsing message content."""

    @abstractmethod
    def parse_mentions(self, text: str) -> Dict[str, Any]:
        """Parse @mention directives. Returns: {
            'mentions': [...],
            'clean_message': str,
            'mode': 'single'|'agents'|'multi',
            'models': [...],
            'agents': [...]
        }"""
        pass

class IMessageRouter(ABC):
    """Contract for routing parsed messages."""

    @abstractmethod
    async def route_mention(
        self,
        mentions: Dict[str, Any],
        text: str,
        context: Dict[str, Any]
    ) -> str:  # 'direct_model'|'agent_chain'|'hostess'
        pass
```

**Marker:** `[REFACTOR-006]` Lines 603-891 → Mention Handler Subsystem
**Impact:** Eliminates code duplication, ~250 lines consolidated

---

### [REFACTOR-007] Chat History & Context Loading (Lines 254-291, 399-436, 638-675)

**Current Location:** Scattered across direct model call sections
**Issue:** Context building code repeated 3+ times

**Extracted to:** `context/context_builders.py` (~150 lines)

**DI-Pattern-005: Context Provider Interface**

```python
# NEW: src/api/handlers/interfaces/context_provider.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class IContextProvider(ABC):
    """Contract for building context for LLM prompts."""

    @abstractmethod
    async def build_model_context(
        self,
        node_path: str,
        user_query: str,
        pinned_files: List[str],
        viewport_context: Optional[Dict] = None
    ) -> str:
        """Build complete prompt context."""
        pass

    @abstractmethod
    async def get_chat_history(
        self,
        node_path: str,
        max_messages: int = 10
    ) -> str:
        """Load formatted chat history."""
        pass

    @abstractmethod
    async def get_file_context(
        self,
        node_path: str
    ) -> str:
        """Get rich file context."""
        pass

    @abstractmethod
    async def get_pinned_context(
        self,
        pinned_files: List[str],
        user_query: str
    ) -> str:
        """Build pinned files context with smart selection."""
        pass
```

**Consolidation Points:**

| Lines (Ollama) | Lines (OpenRouter) | Lines (@mention) | New Location |
|---|---|---|---|
| 254-260 | 399-405 | 638-644 | `context_builders.py:load_chat_history()` |
| 262-267 | 407-412 | 646-651 | `context_builders.py:build_file_context()` |
| 269-278 | 414-423 | 653-662 | `context_builders.py:build_pinned_context()` |
| 288-291 | 433-436 | 672-675 | `context_builders.py:build_model_prompt()` |

**Marker:** `[REFACTOR-007]` Lines 254-291 (and dups) → Context Builder
**Impact:** DRY principle, -120 lines duplicated code

---

### [REFACTOR-008] Hostess Routing & Decision Logic (Lines 912-1315)

**Current Location:** `user_message_handler.py:912-1315` (403 lines)
**Issue:** Complex conditional logic for Hostess decision routing

**Extracted to:** `agents/hostess_router.py` (~200 lines)

**Key Sections:**
- Lines 915-998: Get Hostess decision → `HostessRouterService.get_decision()`
- Lines 1000-1112: Hostess actions handling → `HostessActionHandler`
- Lines 1179-1228: Route to agents based on @mention/Hostess → `RoutingStrategyFactory`
- Lines 1233-1290: API key flow (ask_provider, learn_key) → `KeyFlowHandler`

**DI-Pattern-006: Router Service Interface**

```python
# NEW: src/api/handlers/interfaces/router.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class HostessDecision:
    """Result from Hostess routing."""
    action: str  # 'quick_answer'|'clarify'|'agent_call'|'chain_call'|'search'|'camera_focus'|'ask_provider'|etc
    agent: Optional[str]  # For agent_call
    result: str  # Hostess's response/decision text
    confidence: float
    options: Optional[List[str]]  # For clarify action

class IHostessRouter(ABC):
    """Contract for Hostess routing."""

    @abstractmethod
    async def get_decision(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> HostessDecision:
        """Get Hostess routing decision."""
        pass

    @abstractmethod
    async def handle_action(
        self,
        decision: HostessDecision,
        sid: str
    ) -> bool:
        """Handle Hostess action. Returns True if handled (no agent needed)."""
        pass

class IAgentRouterStrategy(ABC):
    """Strategy for determining which agents to call."""

    @abstractmethod
    def get_agents_to_call(
        self,
        mentions: Dict[str, Any],
        hostess_decision: Optional[HostessDecision]
    ) -> tuple[List[str], bool]:  # (agents_list, single_mode)
        pass
```

**Breakdown:**

| Lines | Content | New Module | Class |
|-------|---------|-----------|-------|
| 915-998 | Hostess decision | `agents/hostess_router.py` | `HostessRouterService` |
| 1000-1112 | Action handlers | `agents/hostess_router.py` | `HostessActionHandler` |
| 1179-1228 | Routing strategy | `agents/agent_orchestrator.py` | `AgentRoutingStrategy` |
| 1233-1290 | API key flow | `agents/hostess_router.py` | `ApiKeyFlowHandler` |

**Marker:** `[REFACTOR-008]` Lines 912-1315 → Hostess Router Subsystem
**Impact:** Cleaner routing logic, testable decision flow

---

### [REFACTOR-009] Agent Chain Orchestration (Lines 1317-1505)

**Current Location:** `user_message_handler.py:1317-1505` (188 lines)
**Issue:** Agent loop with mixed concerns (prompt building, LLM calls, artifact extraction)

**Extracted to:** `agents/agent_orchestrator.py` (~250 lines)

**Key Sections:**
- Lines 1323-1369: Prompt building → `PromptBuilder` interface
- Lines 1370-1391: Agent LLM calls → `AgentExecutor`
- Lines 1409-1424: Artifact extraction → `ArtifactExtractor` (already exists, integrate)
- Lines 1445-1505: Response emission → `ResponseEmitter`

**DI-Pattern-007: Agent Executor Interface**

```python
# NEW: src/api/handlers/interfaces/agent_executor.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class AgentExecutionRequest:
    """Request to execute an agent."""
    agent_name: str  # 'PM'|'Dev'|'QA'
    prompt: str
    max_tokens: int
    file_context: str
    previous_outputs: Dict[str, str]  # {agent_name: response}
    use_streaming: bool

class AgentExecutionResult:
    """Result from agent execution."""
    agent_name: str
    response_text: str
    artifacts: List[Dict[str, Any]]
    qa_score: Optional[float]
    tokens_generated: int

class IAgentExecutor(ABC):
    """Contract for agent execution."""

    @abstractmethod
    async def execute(
        self,
        request: AgentExecutionRequest
    ) -> AgentExecutionResult:
        """Execute single agent and return result."""
        pass

class IPromptBuilder(ABC):
    """Contract for building agent prompts."""

    @abstractmethod
    def build_prompt(
        self,
        agent_name: str,
        user_message: str,
        file_context: str,
        previous_outputs: Dict[str, str],
        pinned_context: str
    ) -> str:
        """Build complete prompt for agent."""
        pass
```

**Breakdown:**

| Lines | Content | New Module | Class |
|-------|---------|-----------|-------|
| 1323-1369 | Prompt building | `agents/agent_orchestrator.py` | `PromptBuilder` |
| 1370-1404 | Agent execution | `agents/agent_orchestrator.py` | `AgentExecutor` |
| 1409-1424 | Artifact extraction | `handlers/response_managers.py` | `ArtifactExtractor` (delegate) |
| 1445-1505 | Response emission | `handlers/response_managers.py` | `ResponseEmitter` |

**Marker:** `[REFACTOR-009]` Lines 1317-1505 → Agent Orchestrator
**Impact:** Separated agent loop from main handler

---

### [REFACTOR-010] Summary Generation & Response Emission (Lines 1515-1665)

**Current Location:** `user_message_handler.py:1515-1665` (150 lines)
**Issue:** Summary generation mixed with response emission

**Extracted to:** `handlers/response_managers.py` (~200 lines)

**Key Sections:**
- Lines 1520-1530: Simple summary → `SummaryGenerator.simple_summary()`
- Lines 1532-1595: LLM-based summary → `SummaryGenerator.llm_summary()`
- Lines 1597-1627: Summary emission → `ResponseEmitter.emit_summary()`
- Lines 1618-1626: Quick actions → `ResponseEmitter.emit_quick_actions()`
- Lines 1653-1664: Single-mode actions → `ResponseEmitter.emit_single_mode_actions()`

**DI-Pattern-008: Response Manager Interface**

```python
# NEW: src/api/handlers/interfaces/response_manager.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class IResponseEmitter(ABC):
    """Contract for emitting responses to client."""

    @abstractmethod
    async def emit_agent_response(
        self,
        sid: str,
        agent: str,
        response_text: str,
        model: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Emit single agent response."""
        pass

    @abstractmethod
    async def emit_summary(
        self,
        sid: str,
        summary_text: str,
        agent_count: int
    ) -> None:
        """Emit multi-agent summary."""
        pass

    @abstractmethod
    async def emit_quick_actions(
        self,
        sid: str,
        agent: str,
        mode: str  # 'single'|'multi'
    ) -> None:
        """Emit action buttons to client."""
        pass

class ISummaryGenerator(ABC):
    """Contract for generating summaries."""

    @abstractmethod
    def simple_summary(self, responses: List[Dict]) -> str:
        """Generate simple text summary."""
        pass

    @abstractmethod
    async def llm_summary(
        self,
        responses: List[Dict],
        agent_executor
    ) -> str:
        """Generate LLM-based summary."""
        pass
```

**Breakdown:**

| Lines | Content | New Module | Class |
|-------|---------|-----------|-------|
| 1520-1595 | Summary generation | `handlers/response_managers.py` | `SummaryGenerator` |
| 1597-1665 | Response emission | `handlers/response_managers.py` | `ResponseEmitter` |

**Marker:** `[REFACTOR-010]` Lines 1515-1665 → Response Manager
**Impact:** Cleaner response handling, reusable for other handlers

---

## Part 3: DI Pattern Implementation Roadmap

### Phase 1: Create Interface Layer (Week 1)

```bash
src/api/handlers/interfaces/
├── __init__.py
├── dependency_container.py    [REFACTOR-002]
├── message_handler.py         [REFACTOR-004]
├── message_parser.py          [REFACTOR-006]
├── context_provider.py        [REFACTOR-007]
├── model_client_interface.py  [REFACTOR-005]
├── agent_executor.py          [REFACTOR-009]
├── response_manager.py        [REFACTOR-010]
├── router.py                  [REFACTOR-008]
└── session_manager.py         [REFACTOR-003]
```

**Implementation Order:**
1. Create all interface files (abstract base classes)
2. Update existing handler_utils.py to use interfaces
3. Create DIContainer class
4. Add unit tests for each interface

### Phase 2: Extract Services (Week 2-3)

**Week 2: Core Services**
- [REFACTOR-003] SessionStateManager
- [REFACTOR-007] ContextBuilders
- [REFACTOR-005] ModelClient (Ollama + OpenRouter)

**Week 3: Routing & Orchestration**
- [REFACTOR-006] MentionParser & MentionHandler
- [REFACTOR-008] HostessRouter
- [REFACTOR-009] AgentOrchestrator

### Phase 3: Main Handler Refactor (Week 4)

- [REFACTOR-001] Create UserMessageHandler class with DI
- [REFACTOR-010] ResponseManager integration
- Update tests to use DIContainer
- Remove old function signature

### Phase 4: Integration & Migration (Week 5)

- Update socket.io registration
- Migrate all existing handlers to new patterns
- Run full test suite
- Performance benchmarking

---

## Part 4: Specific Code Markers

### Current Handler Structure

```python
# MARKER: [PHASE-80-ENTRY]
def register_user_message_handler(sio, app=None):
    """Lines 39-40 - ENTRY POINT"""

    # MARKER: [REFACTOR-003]
    pending_api_keys = {}  # Line 46 - REPLACE with SessionStateManager

    # MARKER: [REFACTOR-002]
    # Lines 49-128: EXTRACT all imports to DIContainer registration
    from src.agents.agentic_tools import parse_mentions  # Line 54
    from src.chat.chat_registry import ChatRegistry, Message  # Line 57
    from src.api.handlers.handler_utils import (...)  # Lines 63-72
    from .message_utils import (...)  # Lines 83-89
    from .streaming_handler import stream_response  # Line 92
    from .chat_handler import (...)  # Lines 95-102
    from .workflow_handler import (...)  # Lines 105-116

    # MARKER: [REFACTOR-004]
    @sio.on('user_message')
    async def handle_user_message(sid, data):  # Lines 142-160 - VALIDATION
        # Line 156-160: Debug logging
        # Line 165-167: Parse input data
        # Line 171-178: Node path normalization
        # Line 181-186: Extract model/pinned/viewport
        # Line 203-213: Chat manager & context setup
        # Line 217-219: Empty message check

        # MARKER: [REFACTOR-005]
        if requested_model:  # Line 227 - DIRECT MODEL ROUTE
            # Lines 227-245: Routing status
            # Lines 246-370: Ollama handling
            # Lines 372-601: OpenRouter handling
            # EXTRACT TO: models/model_client.py

        # MARKER: [REFACTOR-006]
        parsed_mentions = parse_mentions(text)  # Line 606
        if parsed_mentions['mentions']:  # Line 609
            # Lines 613-632: Routing decision
            # Lines 637-821: Direct model call (DUPLICATE OF [REFACTOR-005])
            # Lines 824-868: Response emission

        # MARKER: [REFACTOR-007]
        # Lines 254-291: Context loading (Ollama path)
        chat_history = get_chat_history_manager()  # Line 255
        rich_context = sync_get_rich_context(node_path)  # Line 263
        pinned_context = build_pinned_context(...)  # Line 270
        model_prompt = build_model_prompt(...)  # Line 291
        # CONSOLIDATE: Repeated at lines 399-436 and 638-675

        # MARKER: [REFACTOR-008]
        if HOSTESS_AVAILABLE:  # Line 917
            hostess = get_hostess()  # Line 919
            hostess_decision = hostess.process(text, context=rich_context)  # Line 997
            # Lines 1000-1112: Handle Hostess actions
            # EXTRACT TO: agents/hostess_router.py

        # MARKER: [REFACTOR-009]
        for agent_name in agents_to_call:  # Line 1323
            # Lines 1323-1369: Prompt building
            # Lines 1370-1391: Agent execution
            # Lines 1409-1424: Artifact extraction
            # EXTRACT TO: agents/agent_orchestrator.py

        # MARKER: [REFACTOR-010]
        if not single_mode and len(responses) > 1:  # Line 1518
            # Lines 1520-1595: Summary generation
            # Lines 1597-1627: Summary emission
            # EXTRACT TO: handlers/response_managers.py
```

### Line-by-Line Refactoring Checklist

| Marker | Lines | Action | Priority | Status |
|--------|-------|--------|----------|--------|
| [REFACTOR-001] | 39-160 | Create UserMessageHandler class | P0 | Pending |
| [REFACTOR-002] | 49-128 | Extract imports to DIContainer | P0 | Pending |
| [REFACTOR-003] | 43-46 | Extract SessionStateManager | P1 | Pending |
| [REFACTOR-004] | 142-220 | Validation & parsing | P1 | Pending |
| [REFACTOR-005] | 227-601 | Model client extraction | P0 | Pending |
| [REFACTOR-006] | 603-891 | Mention handler | P1 | Pending |
| [REFACTOR-007] | 254-291,399-436,638-675 | DRY context builders | P1 | Pending |
| [REFACTOR-008] | 912-1315 | Hostess router extraction | P1 | Pending |
| [REFACTOR-009] | 1317-1505 | Agent orchestrator | P0 | Pending |
| [REFACTOR-010] | 1515-1665 | Response manager | P1 | Pending |

---

## Part 5: Dependency Injection Container Setup

### Registration Pattern

```python
# NEW: src/api/handlers/di_container.py

from src.api.handlers.interfaces.dependency_container import DIContainer
from src.api.handlers.interfaces.message_parser import IMentionParser
from src.api.handlers.interfaces.context_provider import IContextProvider
from src.api.handlers.interfaces.model_client_interface import IModelClient
from src.api.handlers.interfaces.agent_executor import IAgentExecutor
from src.api.handlers.interfaces.response_manager import IResponseEmitter, ISummaryGenerator
from src.api.handlers.interfaces.router import IHostessRouter, IAgentRouterStrategy

def create_message_handler_container(sio) -> DIContainer:
    """Create DI container for user message handler."""
    container = DIContainer()

    # Register socketio
    container.register_singleton('socketio', sio)

    # Register services
    container.register(
        'mention_parser',
        lambda: MentionParser()  # Implements IMentionParser
    )

    container.register(
        'context_builder',
        lambda: ContextBuilder()  # Implements IContextProvider
    )

    container.register(
        'model_client',
        lambda: ModelClientFactory.create()  # Implements IModelClient
    )

    container.register(
        'agent_executor',
        lambda: AgentExecutor(container.get('model_client'))
    )

    container.register(
        'hostess_router',
        lambda: HostessRouter()  # Implements IHostessRouter
    )

    container.register(
        'response_emitter',
        lambda: ResponseEmitter(sio)  # Implements IResponseEmitter
    )

    container.register(
        'summary_generator',
        lambda: SummaryGenerator()  # Implements ISummaryGenerator
    )

    container.register(
        'session_manager',
        lambda: SessionStateManager()  # Singleton for session state
    )

    return container


# Usage in main handler
class UserMessageHandler:
    def __init__(self, container: DIContainer):
        self.sio = container.get('socketio')
        self.mention_parser = container.get('mention_parser')
        self.context_builder = container.get('context_builder')
        self.model_client = container.get('model_client')
        self.agent_executor = container.get('agent_executor')
        self.hostess_router = container.get('hostess_router')
        self.response_emitter = container.get('response_emitter')
        self.summary_generator = container.get('summary_generator')
        self.session_manager = container.get('session_manager')

    async def handle_user_message(self, sid: str, data: dict):
        """Main orchestration using injected dependencies."""
        # No concrete imports needed here!
        pass
```

---

## Part 6: Testing Strategy

### Unit Test Files

```bash
tests/api/handlers/
├── test_mention_parser.py        # [REFACTOR-006]
├── test_context_builder.py       # [REFACTOR-007]
├── test_model_client.py          # [REFACTOR-005]
├── test_hostess_router.py        # [REFACTOR-008]
├── test_agent_orchestrator.py    # [REFACTOR-009]
├── test_response_manager.py      # [REFACTOR-010]
├── test_session_manager.py       # [REFACTOR-003]
├── test_di_container.py          # [REFACTOR-002]
└── test_user_message_handler_integration.py  # [REFACTOR-001]
```

### Mock Container Pattern

```python
# tests/api/handlers/conftest.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.api.handlers.di_container import DIContainer

@pytest.fixture
def mock_container():
    """Create mock DI container for testing."""
    container = DIContainer()

    container.register_singleton('socketio', AsyncMock())
    container.register_singleton('mention_parser', MagicMock())
    container.register_singleton('context_builder', AsyncMock())
    container.register_singleton('model_client', AsyncMock())
    container.register_singleton('agent_executor', AsyncMock())
    container.register_singleton('hostess_router', AsyncMock())
    container.register_singleton('response_emitter', AsyncMock())
    container.register_singleton('summary_generator', MagicMock())
    container.register_singleton('session_manager', MagicMock())

    return container
```

---

## Part 7: Migration Path (Incremental)

### Step 1: Add Interfaces (No Breaking Changes)
- Create interfaces alongside existing code
- Existing code continues to work
- Risk: Low

### Step 2: Extract First Service
- Pick [REFACTOR-007] (ContextBuilder) as it's most isolated
- Implement `IContextProvider`
- Create `ContextBuilder` class
- Add unit tests
- Update user_message_handler to use it optionally

### Step 3: Extract Model Client
- Implement [REFACTOR-005]
- Create `ModelClient` with Ollama + OpenRouter support
- Update direct model call path to use it
- Verify streaming still works

### Step 4: Extract Remaining Services
- [REFACTOR-003] SessionStateManager
- [REFACTOR-006] MentionParser
- [REFACTOR-008] HostessRouter
- [REFACTOR-009] AgentOrchestrator
- [REFACTOR-010] ResponseManager

### Step 5: Main Handler Refactor
- [REFACTOR-001] Create UserMessageHandler class
- [REFACTOR-002] Use DIContainer
- Remove old nested function
- Full regression testing

### Step 6: Cleanup
- Remove old imports from handler_utils
- Update documentation
- Performance benchmarking

---

## Part 8: Existing DI Patterns in Codebase

### Current Patterns Found

**File:** `/src/dependencies.py`
- FastAPI `Depends()` pattern for HTTP routes
- Request object introspection for app.state
- Optional vs required components pattern

**File:** `/src/initialization/components_init.py`
- Module-level singleton globals
- Thread locks for thread-safe initialization
- Graceful degradation (availability flags)

### Recommended Adoption

```python
# DO: Use pattern from components_init.py for service registration
class DIContainer:
    _services = {}
    _locks = {}

    @classmethod
    def register_singleton(cls, name: str, factory: Callable):
        """Register singleton service."""
        if name not in cls._locks:
            cls._locks[name] = threading.Lock()

        with cls._locks[name]:
            if name not in cls._services:
                cls._services[name] = factory()

    @classmethod
    def get(cls, name: str) -> Optional[Any]:
        """Get service, with lazy initialization."""
        if name not in cls._services:
            return None
        return cls._services[name]
```

---

## Part 9: Lines Summary Table

| Refactor Section | Lines | New Module(s) | Est. New Lines | Est. Reduction |
|---|---|---|---|---|
| [REFACTOR-001] Main Handler | 39-160 | - | +50 refactor | -80 nested scope |
| [REFACTOR-002] Imports | 49-128 | interfaces/ | +100 interfaces | -80 imports |
| [REFACTOR-003] Session State | 43-46 | handlers/session_manager.py | +80 class | -4 globals |
| [REFACTOR-004] Validation | 142-220 | handlers/validation.py | +50 | -50 |
| [REFACTOR-005] Model Client | 227-601 | models/model_client.py | +250 class | -350 |
| [REFACTOR-006] @Mention | 603-891 | handlers/mention_handler.py | +150 | -250 |
| [REFACTOR-007] Context | 254-291, 399-436, 638-675 | context/context_builders.py | +150 | -120 dups |
| [REFACTOR-008] Hostess | 912-1315 | agents/hostess_router.py | +200 | -300 |
| [REFACTOR-009] Agents | 1317-1505 | agents/agent_orchestrator.py | +250 | -180 |
| [REFACTOR-010] Response | 1515-1665 | handlers/response_managers.py | +200 | -150 |
| **TOTAL** | **1694** | **8 modules** | **~1400** | **~1100 net** |

**Result:** 1694-line file → 7 focused modules (150-300 lines each) + interfaces

---

## Part 10: Next Steps for Haiku A

1. **Review this document** with team for feedback
2. **Create interfaces layer** first (low risk)
3. **Pick [REFACTOR-007]** as first extraction target (most isolated)
4. **Create PR with interface+first service** for review
5. **Iterate on remaining services** one per PR
6. **Final refactor of main handler** after all services extracted

---

**Report Generated:** 2026-01-22
**Audit Consolidation:** Grok + Gemini + Claude LLM Analysis
**Implementation Status:** Code Markers Ready
**Next Phase:** Phase 81 (Service Extraction)
