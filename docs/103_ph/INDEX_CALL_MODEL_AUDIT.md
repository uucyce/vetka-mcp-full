# call_model Consolidation Audit - Index

**Phase:** 103
**Created:** 2026-01-31
**Status:** Analysis Complete

---

## Document Overview

This audit identifies **3 duplicate `call_model` implementations** in VETKA and provides a consolidation plan to reduce code duplication by **86.3%** (~863 lines).

---

## Documents in This Audit

### 1. Consolidation Plan (Primary Document)

**File:** `/docs/103_ph/call_model_consolidation_plan.md`

**Contents:**
- Executive Summary
- Current State Analysis (3 implementations)
- Canonical Location Recommendation
- 4-Phase Migration Plan
- Risk Assessment (High/Medium/Low)
- Testing Strategy
- Success Criteria
- Timeline (4.5-6.5 hours total)
- Rollback Plan

**Key Finding:**
> Consolidate to `provider_registry.call_model_v2()` as canonical implementation

---

### 2. Flow Diagrams

**File:** `/docs/103_ph/call_model_flow_diagram.txt`

**Contents:**
- Current State Flow Diagram (3 implementations)
- Proposed State Flow Diagram (1 canonical + thin adapters)
- Call Graph Analysis
- Migration Impact Matrix
- Duplicate Code Metrics
- Risk Matrix
- Feature Parity Check
- Consolidation Benefits
- Timeline Gantt Chart

**Key Metrics:**
- Before: ~1000 lines of LLM call logic
- After: ~137 lines (86.3% reduction)
- Feature completeness: 49% → 92%

---

### 3. Quick Reference Guide

**File:** `/docs/103_ph/call_model_quick_reference.md`

**Contents:**
- TL;DR - What to use
- Signature comparison (old vs new)
- Migration examples (4 scenarios)
- Response format comparison
- Provider auto-detection
- Error handling
- Tool support matrix
- Streaming support
- Common mistakes (4 examples)
- Migration checklist
- Testing examples
- FAQ

**Target Audience:** Developers migrating code

---

### 4. This Index

**File:** `/docs/103_ph/INDEX_CALL_MODEL_AUDIT.md`

**Purpose:** Central navigation for all audit documents

---

## Quick Links

| Document | Purpose | Audience |
|----------|---------|----------|
| Consolidation Plan | Full technical analysis | Tech Lead, Architects |
| Flow Diagrams | Visual understanding | All Developers |
| Quick Reference | Migration guide | Active Developers |
| Index (this) | Navigation | Everyone |

---

## Key Findings Summary

### Current Implementations (3)

1. **`api_aggregator_v3.call_model()`**
   - Location: `src/elisya/api_aggregator_v3.py:237-434`
   - Lines: 547 (including helpers)
   - Status: 🟡 Legacy (deprecated)
   - Features: Ollama, OpenRouter, Direct APIs, Tool calling
   - Missing: Provider enum, Key rotation, Model status tracking

2. **`model_client.call_model()`**
   - Location: `src/api/handlers/models/model_client.py:52-109, 111-445`
   - Lines: 446
   - Status: 🟢 Active (Socket.IO integration)
   - Features: Socket.IO streaming, Key rotation, Ollama, OpenRouter
   - Missing: Direct APIs, Tool calling

3. **`routes.call_model()`** (OpenCode Bridge)
   - Location: `src/opencode_bridge/routes.py:395-412`
   - Lines: 18 (thin wrapper)
   - Status: 🟢 Active (REST API)
   - Features: Already delegates to canonical path ✅
   - Missing: N/A (wrapper only)

### Canonical Implementation

**`provider_registry.call_model_v2()`**
- Location: `src/elisya/provider_registry.py:1053-1189`
- Lines: 137
- Status: 🟢 Production Ready
- Features: All 6 providers, Tool validation, Intelligent fallbacks, Model status tracking, HTTP error handling
- Missing: Socket.IO events (can be added as wrapper)

---

## Migration Phases

| Phase | Task | Duration | Risk | Status |
|-------|------|----------|------|--------|
| 1 | Adapter Layer | 1-2 hours | 🟢 Low | Not Started |
| 2 | Documentation | 30 min | 🟢 None | Not Started |
| 3 | Migrate Callers | 2-3 hours | 🟡 Medium | Not Started |
| 4 | Remove Legacy | 1 hour | 🟠 High | Not Started |
| **Total** | | **4.5-6.5 hrs** | | |

---

## Impact Analysis

### Files Requiring Changes

| File | Impact Level | Lines Affected | Migration Time |
|------|--------------|----------------|----------------|
| `api_aggregator_v3.py` | HIGH | 547 lines | 1-2 hours |
| `model_client.py` | MEDIUM | 446 lines | 2-3 hours |
| `routes.py` | NONE | 0 (already correct) | 0 hours ✅ |
| `orchestrator_with_elisya.py` | LOW | 1 import | 15 minutes |
| `streaming_handler.py` | LOW | 1 import | 30 minutes |

**Total Files:** 5
**Total Lines Modified:** ~994 lines
**Total Time:** 4.5-6.5 hours

---

## Benefits

### Code Quality
- ✅ 86.3% reduction in duplicate LLM call logic (863 lines eliminated)
- ✅ Single source of truth for provider selection
- ✅ Consistent error handling across entire codebase
- ✅ Easier to maintain and debug

### Features
- ✅ All callers get XAI/Grok support
- ✅ All callers get intelligent fallbacks
- ✅ All callers get model status tracking
- ✅ All callers get consistent tool validation

### Performance
- ✅ Unified key rotation (no race conditions)
- ✅ Consistent caching strategy
- ✅ Single monitoring point

### Developer Experience
- ✅ One API to learn (instead of 3)
- ✅ Predictable behavior across codebase
- ✅ Easier to add new providers (add to registry once)

### Testing
- ✅ Test one implementation thoroughly
- ✅ No need to test 3 separate call paths
- ✅ Integration tests cover all callers

---

## Risk Mitigation

### High Risk: Socket.IO Streaming
**Risk:** Breaking real-time chat streaming
**Mitigation:** Create `SocketIOModelClient` wrapper that:
- Wraps `call_model_v2()`
- Emits `stream_start` event
- Handles streaming tokens
- Emits `stream_end` event with metadata

### High Risk: Ollama Direct Calls
**Risk:** Different behavior between `ollama.chat()` and `OllamaProvider`
**Mitigation:**
- Verify `OllamaProvider` uses same `ollama.chat()` call
- Test all Ollama models (qwen2.5:7b, deepseek-llm:7b, llama3.1:8b)
- Compare response formats

### High Risk: OpenRouter Key Rotation
**Risk:** Breaking key rotation logic during migration
**Mitigation:**
- Ensure `unified_key_manager` is initialized before migration
- Test 429 rate limit handling
- Test key exhaustion scenarios

---

## Testing Plan

### Unit Tests
- [ ] `call_model_v2()` with all 6 providers
- [ ] Fallback logic (XAI→OpenRouter, API errors→OpenRouter)
- [ ] Tool calling (Ollama, OpenAI, Anthropic)
- [ ] Error handling (401, 402, 403, 404, 429)

### Integration Tests
- [ ] Socket.IO streaming (stream_start, stream_token, stream_end)
- [ ] MCP bridge (`vetka_call_model` tool)
- [ ] REST API (`POST /model/call`)

### Manual Tests
- [ ] Ollama models (qwen2.5:7b, deepseek-llm:7b, llama3.1:8b)
- [ ] OpenRouter models (anthropic/claude-3-haiku, mistralai/mistral-7b)
- [ ] Direct API models (grok-4, gpt-4o, claude-opus-4-5, gemini-2.0-flash)

---

## Success Criteria

- [ ] All 3 `call_model` implementations removed or converted to thin adapters
- [ ] No regressions in Socket.IO streaming
- [ ] No regressions in MCP tool calls
- [ ] No regressions in REST API calls
- [ ] All tests passing (unit + integration + manual)
- [ ] Documentation updated
- [ ] Deprecation warnings in place
- [ ] Zero duplicate LLM call logic

---

## Rollback Plan

If migration causes issues:

1. **Phase 4 Rollback:** Restore deleted code from git
2. **Phase 3 Rollback:** Restore old imports
3. **Keep Phase 1 & 2:** Adapters remain as compatibility layer

**Zero Downtime:** Adapters ensure old code continues working during migration.

---

## Timeline

```
Week 1:
  Day 1-2: ███░░ Phase 1 - Adapter Layer (1-2 hours)
  Day 2:   █░░░░ Phase 2 - Documentation (30 min)
  Day 3-4: ███░░ Phase 3 - Migrate Callers (2-3 hours)
  Day 5:   ████░ Testing & Validation

Week 2:
  Day 1:   █░░░░ Phase 4 - Remove Legacy (1 hour)
  Day 2+:  ░░░░░ Monitoring & Rollback if needed
```

---

## Related Documents

### Previous Audits
- `docs/92_ph/HAIKU_2_KEY_ROUTING_AUDIT.md` - Provider registry audit
- `docs/93_ph/PHASE_93_GIT_COMMIT.md` - Migration to call_model_v2
- `docs/95_ph/PROVIDER_AUDIT_EXECUTIVE_SUMMARY.md` - Provider system consolidation

### Implementation Guides
- `docs/QUICK_PROVIDER_REFERENCE.md` - Provider usage examples
- `docs/95_ph/MCP_TOOLS_MARKERS.md` - MCP tool documentation
- `docs/95_ph/PHASE_95.6_BRIDGE_UNIFICATION_COMPLETE.md` - Bridge architecture

### Source Code
- `src/elisya/provider_registry.py` - Canonical implementation
- `src/elisya/api_aggregator_v3.py` - Legacy implementation #1
- `src/api/handlers/models/model_client.py` - Legacy implementation #2
- `src/opencode_bridge/routes.py` - REST API wrapper (already correct)

---

## Next Steps

1. Review this audit with tech lead
2. Get approval for migration timeline
3. Schedule Phase 1 (Adapter Layer) - 1-2 hours
4. Begin migration following 4-phase plan
5. Monitor for issues during rollout

---

## Appendix: Code Statistics

### Before Consolidation
```
Total call_model implementations: 3
Total lines of LLM call logic: ~1000 lines
Lines per implementation:
  ├─ api_aggregator_v3: 547 lines
  ├─ model_client: 446 lines
  └─ routes.py: 18 lines (wrapper)

Provider coverage:
  ├─ api_aggregator_v3: Ollama, OpenRouter, Direct APIs (3/6 providers)
  ├─ model_client: Ollama, OpenRouter (2/6 providers)
  └─ call_model_v2: All 6 providers ✅

Feature completeness:
  ├─ api_aggregator_v3: 49% (9/18 features)
  ├─ model_client: 38% (7/18 features)
  └─ call_model_v2: 92% (16.5/18 features)
```

### After Consolidation
```
Total call_model implementations: 1 canonical + thin adapters
Total lines of LLM call logic: ~137 lines (call_model_v2)
Duplicate logic eliminated: ~863 lines (86.3% reduction)

Provider coverage:
  └─ call_model_v2: All 6 providers ✅

Feature completeness:
  └─ call_model_v2: 92% (16.5/18 features)
      Missing only Socket.IO events (can be added as wrapper)
```

---

**Audit Completed:** 2026-01-31
**Auditor:** Haiku 1 (Audit Agent)
**Status:** Ready for Implementation
**Recommendation:** APPROVE - High benefit, manageable risk
