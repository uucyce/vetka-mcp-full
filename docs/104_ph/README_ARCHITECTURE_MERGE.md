# Phase 104: Architecture Merge Documentation
**Complete Guide to Legacy Orchestrator + AgentPipeline Integration**

---

## Quick Navigation

### Start Here
1. **[ARCHITECTURE_MERGE_PLAN.md](./ARCHITECTURE_MERGE_PLAN.md)** - Complete analysis and design (30K words)
   - Current state analysis
   - Integration strategy
   - Risk mitigation
   - Success metrics

2. **[MERGE_IMPLEMENTATION_GUIDE.md](./MERGE_IMPLEMENTATION_GUIDE.md)** - Step-by-step code changes (22K words)
   - Exact code snippets
   - Line numbers
   - Testing procedures
   - Troubleshooting

3. **[ARCHITECTURE_DIAGRAMS.md](./ARCHITECTURE_DIAGRAMS.md)** - Visual reference (27K words)
   - Flow diagrams
   - State management
   - Data flow
   - MARKER locations

---

## Executive Summary

**Problem:** Two parallel agent orchestration systems with complementary strengths.

**Solution:** Inject Pipeline's fractal decomposition + research loop INTO Legacy's proven infrastructure.

**Result:** Unified system with:
- ✅ PM → Architect → **[Pipeline Fractal Loop]** → Dev||QA parallel
- ✅ Researcher auto-triggers on unclear subtasks
- ✅ STM (Short-Term Memory) context passing
- ✅ Preserved Elisya state, tool support, approval gates
- ✅ Feature flag for gradual rollout

---

## File Overview

| Document | Purpose | Length | Audience |
|----------|---------|--------|----------|
| **ARCHITECTURE_MERGE_PLAN.md** | Complete analysis + design | 30K | Architects, Leads |
| **MERGE_IMPLEMENTATION_GUIDE.md** | Code changes + testing | 22K | Developers |
| **ARCHITECTURE_DIAGRAMS.md** | Visual reference | 27K | All stakeholders |
| **README_ARCHITECTURE_MERGE.md** | This file - navigation | 3K | All |

**Total documentation:** ~82K words

---

## Key Concepts

### 1. Legacy Orchestrator
**File:** `src/orchestration/orchestrator_with_elisya.py` (2815 lines)

**Strengths:**
- PM → Architect → Dev||QA workflow
- Parallel execution via `asyncio.gather()`
- Full Elisya integration (state, middleware, semantic paths)
- Tool support (camera_focus, semantic search, tree context)
- Approval gate (Phase 55)
- EvalAgent scoring (Phase 34)

**Weaknesses:**
- No Researcher agent
- No fractal task decomposition
- Single-pass execution (no iteration)

### 2. Agent Pipeline
**File:** `src/orchestration/agent_pipeline.py` (768 lines)

**Strengths:**
- Fractal decomposition (Task → Subtasks → Sub-searches)
- Researcher auto-trigger on `needs_research=True`
- STM (Short-Term Memory) context passing
- Confidence-based recursive research
- Code extraction + auto-write

**Weaknesses:**
- No Elisya state (loses context)
- No tool support
- No parallel execution
- No approval gate

### 3. Hybrid Architecture (Phase 104)

**Best of both worlds:**
```
PM → Architect → [PIPELINE LOOP] → Dev||QA
                      ↓
              Fractal + Research
              With Elisya + Tools
```

**Key innovation:** `_run_agent_with_elisya_async()` becomes universal agent invocation method used by BOTH Legacy flow AND Pipeline subtasks.

---

## Implementation Timeline

### Phase 104.1: Preparation (1 hour)
- Add MARKERs to integration points
- Import Pipeline classes

### Phase 104.2: Core Methods (3 hours)
- `_execute_pipeline_loop()` (main integration)
- `_pipeline_architect_plan()` (break down tasks)
- `_pipeline_research()` (researcher loop)
- `_build_subtask_prompt()` (context injection)
- `_extract_code_blocks()` (artifact extraction)
- `_save_pipeline_task()` (storage)
- `_extract_json_robust()` (parsing)

### Phase 104.3: Integration Testing (2 hours)
- Simple task (no research)
- Complex task (with research)
- Parallel Dev/QA after Pipeline
- Artifact staging + approval

### Phase 104.4: Feature Flag (1 hour)
- Add `VETKA_PIPELINE_ENABLED` environment variable
- Test enabled/disabled modes

### Phase 104.5: Cleanup (1 hour)
- Deprecate standalone pipeline
- Update docs
- Archive old orchestrators

**Total: ~8 hours (1 working day)**

---

## Code Changes Summary

### Files Modified
| File | Changes | MARKERs |
|------|---------|---------|
| `orchestrator_with_elisya.py` | +7 methods, +1 hook, +1 flag | `MARKER_104_ARCH_MERGE_1` to `_11` |
| `agent_pipeline.py` | +1 deprecation notice | `MARKER_104_ARCH_MERGE_2` |

### Methods Added
```python
# orchestrator_with_elisya.py
async def _execute_pipeline_loop()        # MARKER_104_ARCH_MERGE_6
async def _pipeline_architect_plan()     # MARKER_104_ARCH_MERGE_3
async def _pipeline_research()           # MARKER_104_ARCH_MERGE_5
def _build_subtask_prompt()              # MARKER_104_ARCH_MERGE_7
def _extract_code_blocks()               # MARKER_104_ARCH_MERGE_8
def _save_pipeline_task()                # MARKER_104_ARCH_MERGE_9
def _extract_json_robust()               # MARKER_104_ARCH_MERGE_10
```

### Integration Hook (Line ~1585)
```python
# MARKER_104_ARCH_MERGE_1
if self.use_pipeline_loop:
    pipeline_output, elisya_state, artifacts = await self._execute_pipeline_loop(...)
    # Use enriched output for Dev/QA
else:
    # Legacy direct flow
```

---

## Testing Strategy

### Test 1: Simple Task (No Research)
```python
feature_request = "Add logging to health_routes.py"
# Expected: 1 subtask, needs_research=False
```

### Test 2: Complex Task (With Research)
```python
feature_request = "Implement voice emotion detection using latest ML models"
# Expected: 3-4 subtasks, 1-2 with needs_research=True, Researcher triggered
```

### Test 3: Parallel Dev/QA After Pipeline
```python
feature_request = "Refactor group chat triggers with fallback routing"
# Expected: Pipeline outputs enriched context → Dev/QA run in parallel
```

### Validation Checklist
- [ ] `data/pipeline_tasks.json` created and populated
- [ ] ElisyaState preserved across subtasks
- [ ] STM injection visible in subtask prompts
- [ ] Artifacts extracted to `result["pipeline_artifacts"]`
- [ ] Dev/QA still run in parallel
- [ ] No regressions with `VETKA_PIPELINE_ENABLED=false`

---

## MARKER Reference

### orchestrator_with_elisya.py
| MARKER | Line | Purpose |
|--------|------|---------|
| `MARKER_104_ARCH_MERGE_1` | ~1585 | Integration hook (if/else) |
| `MARKER_104_ARCH_MERGE_3` | ~2920 | Architect planning method |
| `MARKER_104_ARCH_MERGE_4` | ~115 | Feature flag declaration |
| `MARKER_104_ARCH_MERGE_4B` | ~170 | Flag in __init__ |
| `MARKER_104_ARCH_MERGE_5` | ~2980 | Research loop method |
| `MARKER_104_ARCH_MERGE_6` | ~2820 | Main pipeline loop method |
| `MARKER_104_ARCH_MERGE_7` | ~3040 | Subtask prompt builder |
| `MARKER_104_ARCH_MERGE_8` | ~3080 | Code block extraction |
| `MARKER_104_ARCH_MERGE_9` | ~3120 | Pipeline task storage |
| `MARKER_104_ARCH_MERGE_10` | ~3140 | Robust JSON extraction |
| `MARKER_104_ARCH_MERGE_11` | ~104 | Pipeline imports |

### agent_pipeline.py
| MARKER | Line | Purpose |
|--------|------|---------|
| `MARKER_104_ARCH_MERGE_2` | ~60 | Deprecation notice |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| ElisyaState lost during subtasks | Pass `elisya_state` through entire loop, update after each call |
| STM conflicts with Elisya context | STM is transient (last 5), Elisya is persistent (full conversation) - they complement |
| Tool calls in Researcher | Researcher uses `_run_agent_with_elisya_async()` → gets full tool access |
| Parallel execution after Pipeline | Pipeline outputs merged result → Dev/QA receive single input (no race) |
| Approval gate bypass | Artifacts stored in `result["pipeline_artifacts"]`, approval gate checks before writes |

---

## Success Metrics

### Functional Requirements
✅ Feature flag working (`VETKA_PIPELINE_ENABLED=true`)
✅ Fractal decomposition (3+ subtasks from Architect output)
✅ Researcher auto-trigger (`needs_research=True` → enriched context)
✅ STM injection (subtask prompts include previous results)
✅ ElisyaState preserved (no context loss)
✅ Tool support (camera_focus, semantic search work in Researcher)
✅ Parallel Dev/QA (still runs after Pipeline)
✅ Approval gate (artifacts staged, not auto-written)
✅ No regressions (Legacy mode with flag disabled still works)

### Performance Targets
- Pipeline loop overhead: max 20% of total workflow time
- Context quality: 2x more relevant context (via STM + research)
- Task success rate: +15% for complex/ambiguous tasks

---

## Migration Path

### Phase 104 (Current)
- Hybrid system with feature flag
- Both modes work (Legacy + Pipeline)

### Phase 105 (Future)
- Parallel subtask execution (currently sequential)
- MAX_PARALLEL_PIPELINES semaphore
- Researcher feedback in Chain Context

### Phase 106 (Future)
- AI-powered subtask prioritization
- Dynamic research depth
- Cross-workflow STM

---

## Related Documentation

### Phase 103 Audit
- **[PHASE_103_AUDIT_SUMMARY.md](../103_ph/PHASE_103_AUDIT_SUMMARY.md)** - Found chain context bugs (FIXED)
- **[haiku1_dead_code_report.md](../103_ph/haiku1_dead_code_report.md)** - Dead code cleanup

### Phase 104 Additional
- **[PHASE_104_FREEZE_STATUS.md](./PHASE_104_FREEZE_STATUS.md)** - JARVIS Voice freeze status
- **[PHASE_104_VOICE_AUDIT.md](./PHASE_104_VOICE_AUDIT.md)** - Voice module audit
- **[MCP_LEGACY_WRAPPER.md](./MCP_LEGACY_WRAPPER.md)** - MCP/Legacy integration

---

## Environment Variables

```bash
# Enable Pipeline fractal loop (Phase 104)
export VETKA_PIPELINE_ENABLED=true

# Disable (use Legacy flow only)
export VETKA_PIPELINE_ENABLED=false

# Or add to .env
echo "VETKA_PIPELINE_ENABLED=true" >> .env
```

---

## Quick Start

### For Developers
1. Read [MERGE_IMPLEMENTATION_GUIDE.md](./MERGE_IMPLEMENTATION_GUIDE.md)
2. Follow STEP 1-4 (code changes)
3. Run tests (STEP 6)
4. Review [ARCHITECTURE_DIAGRAMS.md](./ARCHITECTURE_DIAGRAMS.md) for visual reference

### For Architects
1. Read [ARCHITECTURE_MERGE_PLAN.md](./ARCHITECTURE_MERGE_PLAN.md)
2. Review Section 3: Proposed Hybrid Architecture
3. Check Section 7: Risk Mitigation
4. Approve or request changes

### For Project Managers
1. Read this README (you're here!)
2. Review "Implementation Timeline" section
3. Check "Success Metrics" section
4. Allocate 1 working day (8 hours) for implementation

---

## Questions & Support

### Common Questions

**Q: Why not migrate Legacy to Pipeline?**
A: Would lose Elisya state, tool support, approval gate - too risky.

**Q: Why not keep both systems separate?**
A: Confusing for users, duplicate maintenance, context can't transfer.

**Q: Can I disable Pipeline after enabling?**
A: Yes! Set `VETKA_PIPELINE_ENABLED=false` - no breaking changes.

**Q: What if a subtask fails?**
A: Graceful degradation - continue to Dev/QA with partial results.

**Q: How does STM differ from ElisyaState?**
A: STM = transient (last 5 results), ElisyaState = persistent (full conversation).

### Troubleshooting

See [MERGE_IMPLEMENTATION_GUIDE.md](./MERGE_IMPLEMENTATION_GUIDE.md) → Troubleshooting section.

---

## Status

- ✅ **Analysis Complete** (this document)
- ✅ **Design Complete** (ARCHITECTURE_MERGE_PLAN.md)
- ✅ **Implementation Guide Complete** (MERGE_IMPLEMENTATION_GUIDE.md)
- ✅ **Visual Reference Complete** (ARCHITECTURE_DIAGRAMS.md)
- ⏳ **Code Implementation** (PENDING - ready to start)
- ⏳ **Testing** (PENDING - after code)
- ⏳ **Deployment** (PENDING - after testing)

---

**Prepared by:** Claude Opus 4.5
**Date:** 2026-01-31
**Phase:** 104 ARCHITECTURE MERGE
**Total Documentation:** 82,000 words across 4 documents
**MARKERs:** `MARKER_104_ARCH_MERGE_1` through `MARKER_104_ARCH_MERGE_11`
**Next Step:** Begin code implementation (8 hours)
