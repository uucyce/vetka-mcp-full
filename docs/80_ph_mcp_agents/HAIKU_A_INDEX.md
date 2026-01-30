# HAIKU A: User Message Handler Refactoring - Complete Analysis

**Generated:** 2026-01-22
**Status:** Code Audit Complete | Ready for Implementation
**Target File:** `/src/api/handlers/user_message_handler.py` (1694 lines)

## Quick Navigation

### For 5-Minute Review
Read: **HAIKU_A_QUICK_REFERENCE.md** (254 lines)
- 10-marker TL;DR table
- Target architecture diagram
- Before/after code examples
- Implementation timeline

### For 30-Minute Deep Dive
Read: **PHASE1_HAIKU_A_REFACTOR_MARKERS.md** (1051 lines)
- Complete technical blueprint
- 10 refactoring sections with exact line numbers
- 8 DI interface specifications
- Dependency injection patterns
- Testing strategy
- Migration path (week by week)

## What Was Delivered

### 1. Comprehensive Code Analysis
- Analyzed 1694-line "God Object" file
- Identified 10 distinct responsibilities
- Located 4 major code blocks requiring extraction
- Found 120+ lines of duplicated context code
- Identified 120+ lines of imports in function scope

### 2. Audit Consolidation
Unified insights from 3 major LLM audits:
- **Grok:** God object anti-pattern, recommended module splits
- **Gemini:** Proposed architecture with incremental approach
- **Claude:** Layered structure with clear module boundaries

Result: **United refactoring blueprint** with 10 specific markers

### 3. Architecture Design
```
Current (1 file):
  user_message_handler.py (1694 lines, God Object)

Target (8+ focused modules):
  ├── user_message_handler.py (200 lines, orchestrator)
  ├── models/model_client.py (250 lines)
  ├── agents/agent_orchestrator.py (250 lines)
  ├── agents/hostess_router.py (200 lines)
  ├── handlers/response_managers.py (200 lines)
  ├── context/context_builders.py (150 lines)
  ├── handlers/mention_handler.py (150 lines)
  ├── handlers/session_manager.py (80 lines)
  └── interfaces/ (8 files, 300 lines total)
```

### 4. Dependency Injection Framework
- 8 new abstract interfaces
- DIContainer class with lazy initialization
- Service registration patterns
- Mock container for testing
- Backwards-compatible migration path

## 10 Refactoring Markers Explained

| # | Marker | Lines | Issue | Solution | Priority |
|---|--------|-------|-------|----------|----------|
| 1 | [REFACTOR-001] | 39-160 | Nested function scope | UserMessageHandler class | P0 |
| 2 | [REFACTOR-002] | 49-128 | 80+ imports in function | DIContainer registration | P0 |
| 3 | [REFACTOR-003] | 43-46 | Global mutable state | SessionStateManager singleton | P1 |
| 4 | [REFACTOR-004] | 142-220 | Mixed validation concerns | Separate validation module | P1 |
| 5 | [REFACTOR-005] | 227-601 | MASSIVE model call block (374 lines!) | ModelClient interface | P0 |
| 6 | [REFACTOR-006] | 603-891 | @mention handling duplication | MentionHandler service | P1 |
| 7 | [REFACTOR-007] | 254-291, 399-436, 638-675 | Context code repeated 3x | ContextBuilder (DRY) | P1 |
| 8 | [REFACTOR-008] | 912-1315 | Complex routing logic (403 lines) | HostessRouter service | P1 |
| 9 | [REFACTOR-009] | 1317-1505 | Agent loop mixed concerns | AgentOrchestrator service | P0 |
| 10 | [REFACTOR-010] | 1515-1665 | Summary + response emission | ResponseManager service | P1 |

**Legend:**
- P0 = Critical (big impact, high complexity)
- P1 = Important (medium impact, depends on P0)

## DI Pattern Overview

### Current State
```python
def register_user_message_handler(sio, app=None):
    # 120+ lines of nested imports
    from src.agents.agentic_tools import parse_mentions
    from src.api.handlers.handler_utils import sync_get_rich_context
    # ... etc

    @sio.on('user_message')
    async def handle_user_message(sid, data):
        # 1600+ lines of tightly-coupled logic
        pass
```

### Target State
```python
class UserMessageHandler:
    def __init__(self, container: DIContainer):
        self.mention_parser = container.get('mention_parser')
        self.model_client = container.get('model_client')
        self.agent_executor = container.get('agent_executor')
        # All dependencies injected, no concrete imports!

    async def handle_user_message(self, sid: str, data: dict):
        # Clean orchestration using injected services
        pass
```

## 8 Abstract Interfaces

| Interface | Purpose | Location |
|-----------|---------|----------|
| `IMessageHandler` | Main contract for message handling | `interfaces/message_handler.py` |
| `IMentionParser` | Parse @mention directives | `interfaces/message_parser.py` |
| `IContextProvider` | Build LLM context | `interfaces/context_provider.py` |
| `IModelClient` | Call Ollama/OpenRouter models | `interfaces/model_client_interface.py` |
| `IAgentExecutor` | Execute agent chains | `interfaces/agent_executor.py` |
| `IHostessRouter` | Route via Hostess agent | `interfaces/router.py` |
| `IResponseEmitter` | Emit responses to client | `interfaces/response_manager.py` |
| `ISummaryGenerator` | Generate multi-agent summaries | `interfaces/response_manager.py` |

## 5-Week Implementation Timeline

### Week 1: Foundation
**Create interfaces (7-10 files)**
- All abstract base classes
- DIContainer class
- Unit tests for interfaces
- Risk: LOW | Value: HIGH

### Week 2-3: Core Services
**Extract most isolated services**
1. [REFACTOR-007] ContextBuilder - Consolidate DRY code
2. [REFACTOR-005] ModelClient - Ollama + OpenRouter
3. [REFACTOR-003] SessionStateManager - Replace globals

### Week 4: Orchestration
**Extract routing and workflow logic**
1. [REFACTOR-008] HostessRouter - Routing decisions
2. [REFACTOR-009] AgentOrchestrator - Agent chain execution
3. [REFACTOR-006] MentionHandler - @mention processing

### Week 5: Integration
**Main handler refactor + testing**
1. [REFACTOR-001] UserMessageHandler class
2. [REFACTOR-010] ResponseManager integration
3. Full regression testing & deployment

## Key Metrics

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Main file size | 1694 lines | 200 lines | -88% |
| Number of modules | 1 | 8+ | Better organization |
| Import coupling | 120+ nested | 0 | Fully decoupled |
| Test coverage | ~20% | >80% | +300% |
| Cyclomatic complexity | Very high | Low | Maintainable |
| Lines per responsibility | 1694:8 = 212 | 150-300 | Single concern |

## Existing Patterns to Leverage

### In Codebase Already
1. `/src/dependencies.py` - FastAPI Depends() pattern
2. `/src/initialization/components_init.py` - Singleton globals with thread locks
3. Availability flags pattern (HOSTESS_AVAILABLE, etc.)

### Recommendation
**Adopt components_init.py pattern** for consistency with existing DI infrastructure.

## Testing Strategy

### Unit Tests (One per service)
```
tests/api/handlers/
├── test_mention_parser.py
├── test_context_builder.py
├── test_model_client.py
├── test_hostess_router.py
├── test_agent_orchestrator.py
├── test_response_manager.py
├── test_session_manager.py
└── test_di_container.py
```

### Integration Test
```
tests/api/handlers/
└── test_user_message_handler_integration.py
```

### Mock Pattern
```python
@pytest.fixture
def mock_container():
    container = DIContainer()
    container.register_singleton('socketio', AsyncMock())
    container.register_singleton('model_client', AsyncMock())
    # ... etc
    return container
```

## Deployment Strategy

### Phase 1: Backwards Compatible
- New classes coexist with old function
- Feature flags control routing
- No breaking changes to API

### Phase 2: Incremental Migration
- Services extracted one-by-one
- Each PR tested independently
- Regression tests run after each extraction

### Phase 3: Cutover
- Old nested function removed
- New class becomes default
- Performance verified

### Phase 4: Cleanup
- Remove old handler_utils imports
- Update documentation
- Celebrate!

## Critical Decisions Made

### 1. Interface-First Design
- Define contracts before implementation
- Low-risk, high-value first step
- Enables parallel work

### 2. Service Extraction Order
- Start with most isolated (ContextBuilder)
- Build on existing patterns
- Test after each extraction

### 3. DI Container Implementation
- Use `components_init.py` pattern
- Thread-safe singletons
- Lazy initialization

### 4. Backwards Compatibility
- Keep old function during migration
- Use feature flags
- No production downtime

## Potential Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Circular imports | Medium | Use interfaces to break cycles |
| Test maintenance | Low | Mock container pattern |
| Performance | Low | Singletons + lazy init |
| Backwards compat | Medium | Phased migration with flags |
| Deployment | Low | Only handler changed, no API changes |

## Success Criteria (Completion Checklist)

### Phase 1: Analysis (COMPLETE)
- [x] Identify all 10 refactoring sections
- [x] Provide exact line numbers
- [x] Design DI patterns
- [x] Document migration path

### Phase 2: Interfaces (TODO)
- [ ] Create 8 interface files
- [ ] Create DIContainer class
- [ ] Add interface unit tests

### Phase 3: Service Extraction (TODO)
- [ ] Extract 3 core services (Weeks 2-3)
- [ ] Extract 3 orchestration services (Week 4)
- [ ] 100% coverage on new tests

### Phase 4: Main Handler Refactor (TODO)
- [ ] Create UserMessageHandler class
- [ ] Integrate all services
- [ ] Full regression testing

### Phase 5: Deployment (TODO)
- [ ] Performance benchmarking
- [ ] Staging verification
- [ ] Production deployment

## FAQ

**Q: Will this break existing functionality?**
A: No. Migration is phased with feature flags. Old code continues to work during transition.

**Q: How many developers needed?**
A: 1-2 developers. Can be parallelized after interfaces are ready.

**Q: What's the risk level?**
A: LOW. Interfaces are created first (low risk), services extracted incrementally with tests.

**Q: Can we do this incrementally?**
A: YES. Each service extracted = new PR, new tests, new deployment. No big bang.

**Q: Which section should we start with?**
A: [REFACTOR-007] ContextBuilder - most isolated, easiest win.

## Files in This Analysis

| File | Lines | Purpose |
|------|-------|---------|
| HAIKU_A_QUICK_REFERENCE.md | 254 | 10-minute overview + TL;DR tables |
| PHASE1_HAIKU_A_REFACTOR_MARKERS.md | 1051 | Complete technical blueprint |
| HAIKU_A_INDEX.md | This file | Navigation + summary |

## Next Steps

1. **Review** HAIKU_A_QUICK_REFERENCE.md (5 minutes)
2. **Read** PHASE1_HAIKU_A_REFACTOR_MARKERS.md (30 minutes)
3. **Discuss** with team & get approval
4. **Week 1**: Create interface layer (7-10 files)
5. **Week 2**: Create first PR for context builder extraction
6. **Week 3-5**: Iterative service extraction & main handler refactor

## Questions?

Refer to the specific sections:
- **"How do I start?"** → HAIKU_A_QUICK_REFERENCE.md "Implementation Priority"
- **"What are the markers?"** → PHASE1_HAIKU_A_REFACTOR_MARKERS.md "Part 2"
- **"What's the DI pattern?"** → PHASE1_HAIKU_A_REFACTOR_MARKERS.md "Part 3"
- **"How do I test?"** → PHASE1_HAIKU_A_REFACTOR_MARKERS.md "Part 6"
- **"What if X happens?"** → HAIKU_A_INDEX.md "Potential Risks"

---

**Generated by:** Haiku Agent A (Code Analysis & Refactoring)
**Analysis Date:** 2026-01-22
**Repository:** https://github.com/danilagoleen/vetka
**Branch:** main
**Status:** READY FOR IMPLEMENTATION
