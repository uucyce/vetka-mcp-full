# HAIKU A: Quick Reference Guide

**Full Document:** `PHASE1_HAIKU_A_REFACTOR_MARKERS.md` (1051 lines)

## TL;DR - 10 Key Refactoring Markers

| Marker | Lines | Issue | Solution | Priority |
|--------|-------|-------|----------|----------|
| [REFACTOR-001] | 39-160 | Nested function scope | Create UserMessageHandler class | P0 |
| [REFACTOR-002] | 49-128 | 80 imports inside function | Extract to DIContainer | P0 |
| [REFACTOR-003] | 43-46 | Global mutable state | SessionStateManager singleton | P1 |
| [REFACTOR-004] | 142-220 | Mixed concerns | Separate validation & parsing | P1 |
| [REFACTOR-005] | 227-601 | MASSIVE model call block (374 lines) | Extract ModelClient interface | P0 |
| [REFACTOR-006] | 603-891 | Code duplication with @mentions | Extract MentionHandler | P1 |
| [REFACTOR-007] | 254-291, 399-436, 638-675 | Context code repeated 3x | DRY with ContextBuilder | P1 |
| [REFACTOR-008] | 912-1315 | Complex routing logic (403 lines) | Extract HostessRouter | P1 |
| [REFACTOR-009] | 1317-1505 | Agent loop mixed concerns | Extract AgentOrchestrator | P0 |
| [REFACTOR-010] | 1515-1665 | Summary + response emission | Extract ResponseManager | P1 |

## Target Architecture

```
Current:  1694 lines → user_message_handler.py (GOD OBJECT)

After:    ~1400 lines distributed across:
          ├── user_message_handler.py (200 lines, clean orchestrator)
          ├── models/model_client.py (250 lines)
          ├── agents/agent_orchestrator.py (250 lines)
          ├── agents/hostess_router.py (200 lines)
          ├── handlers/response_managers.py (200 lines)
          ├── context/context_builders.py (150 lines)
          ├── handlers/mention_handler.py (150 lines)
          ├── handlers/session_manager.py (80 lines)
          └── interfaces/ (8 files, ~300 lines total)
```

## DI Pattern (Dependency Injection)

### Before
```python
def register_user_message_handler(sio, app=None):
    # 120+ nested imports
    from src.agents.agentic_tools import parse_mentions
    from src.api.handlers.handler_utils import sync_get_rich_context
    from .streaming_handler import stream_response
    # ... 120 more lines of imports

    @sio.on('user_message')
    async def handle_user_message(sid, data):
        # 1600+ lines of logic
```

### After
```python
class UserMessageHandler:
    def __init__(self, container: DIContainer):
        # All dependencies injected!
        self.mention_parser = container.get('mention_parser')
        self.context_builder = container.get('context_builder')
        self.model_client = container.get('model_client')
        self.agent_executor = container.get('agent_executor')
        self.hostess_router = container.get('hostess_router')

    async def handle_user_message(self, sid: str, data: dict):
        # Clean orchestration, no concrete imports
        pass

# Registration
container = create_message_handler_container(sio)
handler = UserMessageHandler(container)
sio.on('user_message')(handler.handle_user_message)
```

## Interface-Based Design (8 New Interfaces)

| Interface | Location | Purpose |
|-----------|----------|---------|
| `IMessageHandler` | interfaces/message_handler.py | Main contract for message handling |
| `IMentionParser` | interfaces/message_parser.py | Parse @mention directives |
| `IContextProvider` | interfaces/context_provider.py | Build LLM context |
| `IModelClient` | interfaces/model_client_interface.py | Call Ollama/OpenRouter |
| `IAgentExecutor` | interfaces/agent_executor.py | Execute agent chains |
| `IHostessRouter` | interfaces/router.py | Route via Hostess |
| `IResponseEmitter` | interfaces/response_manager.py | Emit responses to client |
| `ISummaryGenerator` | interfaces/response_manager.py | Generate summaries |

## Implementation Priority

### Week 1: Foundation (Create Interfaces)
```bash
✓ Create 8 interface files in src/api/handlers/interfaces/
✓ Create DIContainer class
✓ Add unit tests for interfaces
```

### Week 2-3: Core Services (Extract First 3)
```bash
[REFACTOR-007] ContextBuilder - Consolidate DRY context code
[REFACTOR-005] ModelClient - Gigantic 374-line block
[REFACTOR-003] SessionStateManager - Replace global state
```

### Week 4: Routing & Orchestration (Extract Next 3)
```bash
[REFACTOR-008] HostessRouter - 403 lines of routing logic
[REFACTOR-009] AgentOrchestrator - 188 lines of agent loop
[REFACTOR-006] MentionHandler - Eliminate duplication
```

### Week 5: Integration (Main Refactor)
```bash
[REFACTOR-001] UserMessageHandler class - Main orchestrator
[REFACTOR-010] ResponseManager - Response emission
Full integration testing & deployment
```

## Key Metrics

| Metric | Current | Target | Change |
|--------|---------|--------|--------|
| Main file size | 1694 lines | 200 lines | -88% |
| Number of modules | 1 | 8+ | Better org |
| Import coupling | 120+ lines | 0 in handler | Decoupled |
| Test coverage | ~20% | >80% | Improved |
| Cycle complexity | Very high | Low | Better |

## Existing DI Patterns in Codebase

Already using in VETKA:
- `/src/dependencies.py` - FastAPI Depends() pattern
- `/src/initialization/components_init.py` - Singleton globals with locks
- Thread-safe initialization flags

Recommendation: **Adopt components_init.py pattern** for consistency

## Files Modified/Created

### Modified
- `/src/api/handlers/user_message_handler.py` (refactored)

### New Directories
- `/src/api/handlers/interfaces/` (8 files)
- `/src/api/handlers/models/` (2 files)
- `/src/api/handlers/agents/` (3 files)
- `/src/api/handlers/context/` (2 files)

### New Test Files
- `/tests/api/handlers/test_*.py` (8 test files)

## Code Markers in Source

Search for these markers in user_message_handler.py:

```
Line 39:   [REFACTOR-001] Main handler entry point
Line 43:   [REFACTOR-003] Global pending_api_keys
Line 49:   [REFACTOR-002] Import block start
Line 142:  [REFACTOR-004] Main @sio.on() decorator
Line 227:  [REFACTOR-005] Direct model routing (374 lines!)
Line 254:  [REFACTOR-007] First context building block
Line 399:  [REFACTOR-007] Duplicate context code
Line 603:  [REFACTOR-006] @mention parsing start
Line 638:  [REFACTOR-007] Third context building block
Line 912:  [REFACTOR-008] Hostess decision logic
Line 1317: [REFACTOR-009] Agent chain loop
Line 1515: [REFACTOR-010] Summary generation
```

## Testing Strategy

### Unit Tests (One per service)
```bash
tests/api/handlers/
├── test_mention_parser.py       - Parse @mentions
├── test_context_builder.py      - Build context
├── test_model_client.py         - Call models
├── test_hostess_router.py       - Route via Hostess
├── test_agent_orchestrator.py   - Execute agents
├── test_response_manager.py     - Emit responses
├── test_session_manager.py      - Session state
└── test_di_container.py         - DI registration
```

### Integration Tests
```bash
tests/api/handlers/
└── test_user_message_handler_integration.py
```

### Mock Pattern
```python
@pytest.fixture
def mock_container():
    """Inject mocks for testing."""
    container = DIContainer()
    container.register_singleton('socketio', AsyncMock())
    container.register_singleton('model_client', AsyncMock())
    # ... rest of mocks
    return container
```

## Potential Issues & Solutions

| Issue | Risk | Solution |
|-------|------|----------|
| Circular imports | Medium | Use interfaces to break cycles |
| Test complexity | Low | Mock container pattern handles it |
| Performance | Low | Lazy init + singletons = same perf |
| Backwards compat | Medium | Phased migration with feature flags |
| DevOps deployment | Low | Only handler changed, APIs same |

## Success Criteria

- [x] All 10 refactoring sections identified
- [x] Specific line numbers provided
- [x] DI patterns designed
- [x] Migration path documented
- [ ] Interfaces implemented (Week 1)
- [ ] First service extracted (Week 2)
- [ ] All services extracted (Week 3)
- [ ] Main handler refactored (Week 4)
- [ ] Tests pass (Week 5)
- [ ] Performance verified
- [ ] Deployed to staging

## Questions & Answers

**Q: Won't this increase code lines?**
A: No. We're moving 1694 lines to 8 modules, but consolidating duplication (120 lines of repeated context code). Net ~1400 lines (same amount, better organized).

**Q: Will this break production?**
A: No. Old `register_user_message_handler()` still works while new classes are being created. Migration is phased with feature flags.

**Q: How long will this take?**
A: ~5 weeks with 1-2 devs. Can be parallelized after interfaces are ready.

**Q: Which markers should I start with?**
A: Start with [REFACTOR-007] (context builders) - most isolated, easiest win.

## References

- Full document: `PHASE1_HAIKU_A_REFACTOR_MARKERS.md`
- Repository: `https://github.com/danilagoleen/vetka`
- Current branch: `main`
- Last update: 2026-01-22

---

**Next Steps:**
1. Review this document with team
2. Read full PHASE1_HAIKU_A_REFACTOR_MARKERS.md
3. Start Week 1: Create interfaces
4. Create PR for code review
5. Begin incremental extraction
