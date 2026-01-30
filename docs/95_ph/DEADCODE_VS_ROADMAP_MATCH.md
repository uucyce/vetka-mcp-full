# Dead Code vs Phase 95 Roadmap Match Analysis

**Date:** 2026-01-26
**Purpose:** Сопоставление найденного dead code с планом Phase 95

---

## Executive Summary

| Dead Code Item | Phase 95 Section | Match Level | Action |
|----------------|------------------|-------------|--------|
| JARVIS Enricher | Session Init (Fat Init + ELISION) | **100% MATCH** | Integrate |
| ELISION Viewport | Session Init (compress_with_elision) | **100% MATCH** | Enable |
| Memory Compression | State Management (Qdrant + TTL) | **80% MATCH** | Extend |
| Enhanced Engram L2-5 | User Memory (_get_user_memory) | **90% MATCH** | Complete |
| OpenRouterProvider | Tool Composition (fallback chain) | **70% MATCH** | Fix |

**Verdict:** 95% dead code is actually **INFRASTRUCTURE FOR PHASE 95!**

---

## Detailed Match Analysis

### 1. JARVIS Prompt Enricher → Session Init

**Dead Code (from audit):**
```
[BUG-H2-001] jarvis_prompt_enricher.py:610,626
- enrich_prompt() - NEVER CALLED
- enrich_prompt_for_user() - NEVER CALLED
- Impact: 23-43% token savings lost
```

**Phase 95 Roadmap:**
```python
# From UNIFIED_MCP_STRATEGY.md - Session Init
from src.memory.jarvis_prompt_enricher import compress_with_elision

compressed_project = compress_with_elision(
    project_context,
    target_tokens=300,
    compression_ratio=0.4  # 40% compression
)
```

**Match Analysis:**
| Aspect | Dead Code | Roadmap | Status |
|--------|-----------|---------|--------|
| Function | `enrich_prompt()` | `compress_with_elision()` | **SAME MODULE** |
| Purpose | Compress context | Compress project context | **IDENTICAL** |
| Location | jarvis_prompt_enricher.py | jarvis_prompt_enricher.py | **SAME FILE** |

**Action:**
```python
# In src/mcp/tools/session_tools.py (NEW)
from src.memory.jarvis_prompt_enricher import (
    compress_with_elision,      # ← EXISTS but unused
    enrich_prompt_for_user,     # ← EXISTS but unused
    get_jarvis_enricher         # ← EXISTS but unused
)
```

**Lines to Connect:**
- `jarvis_prompt_enricher.py:610` → `session_tools.py:_get_project_context()`
- `jarvis_prompt_enricher.py:626` → `session_tools.py:_get_user_memory()`

---

### 2. ELISION Viewport Compression → Session Init + Compound Tools

**Dead Code (from audit):**
```
[BUG-H2-002] jarvis_prompt_enricher.py:467
- enrich_prompt_with_viewport() - DEFINED but NOT CALLED
- Impact: 40-60% compression available but unused
```

**Phase 95 Roadmap:**
```python
# From compound_tools.py - VetkaResearchTool
summary = self._create_summary(topic, valid_contents, depth)
# Could use: enrich_prompt_with_viewport() for compression!

# From session_tools.py
compressed_project = compress_with_elision(project_context, ...)
```

**Match Analysis:**
| Aspect | Dead Code | Roadmap | Status |
|--------|-----------|---------|--------|
| Function | `enrich_prompt_with_viewport()` | `compress_with_elision()` | **COMPLEMENTARY** |
| Purpose | Compress 3D viewport | Compress project context | **SAME GOAL** |
| Use Case | UI context → LLM | Session context → Claude Code | **BOTH NEEDED** |

**Action:**
```python
# In compound_tools.py - VetkaResearchTool
from src.memory.jarvis_prompt_enricher import enrich_prompt_with_viewport

def _create_summary(self, topic: str, contents: List, depth: str) -> str:
    # Use ELISION viewport compression for deep summaries
    if depth == "deep":
        return enrich_prompt_with_viewport(
            viewport_context={"files": contents, "topic": topic},
            compression_level=2
        )
```

**Lines to Connect:**
- `jarvis_prompt_enricher.py:467` → `compound_tools.py:VetkaResearchTool._create_summary()`
- `jarvis_prompt_enricher.py:467` → `context_fusion.py:build_context_for_dev()` (existing but unused)

---

### 3. Memory Compression Scheduler → State Management

**Dead Code (from audit):**
```
[BUG-H2-003] compression.py:371
- CompressionScheduler.check_and_compress() - SCHEDULER NOT RUNNING
- Impact: Qdrant grows uncontrolled, 768D embeddings never compressed
```

**Phase 95 Roadmap:**
```python
# From mcp_state_manager.py
class MCPStateManager:
    def __init__(self):
        self.qdrant = get_qdrant_manager()
        self.collection_name = "mcp_agent_state"

    async def save_state(self, agent_id: str, state: Dict, ttl_seconds: int = 3600):
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        # TTL-based expiration
```

**Match Analysis:**
| Aspect | Dead Code | Roadmap | Status |
|--------|-----------|---------|--------|
| Purpose | Age-based compression | TTL-based expiration | **SIMILAR** |
| Storage | Qdrant embeddings | Qdrant state | **SAME BACKEND** |
| Schedule | Background scheduler | On-demand with TTL | **COMPLEMENTARY** |

**Synergy Opportunity:**
```python
# Merge compression.py scheduler with mcp_state_manager.py

class MCPStateManager:
    def __init__(self):
        self.qdrant = get_qdrant_manager()
        # ADD: Memory compression for old states
        from src.memory.compression import get_memory_compressor
        self.compressor = get_memory_compressor()

    async def cleanup_expired_states(self):
        """Periodic cleanup using existing compression infrastructure."""
        # Use compression.py:371 CompressionScheduler logic
        await self.compressor.compress_by_age(
            collection=self.collection_name,
            age_thresholds={
                7: 0.99,    # 7 days: keep 99% quality
                30: 0.90,   # 30 days: 90% quality
                90: 0.80    # 90 days: 80% quality
            }
        )
```

**Lines to Connect:**
- `compression.py:371` → `mcp_state_manager.py:cleanup_expired_states()` (NEW)
- `compression.py:124` (`compress_by_age`) → Background task in `main.py:lifespan`

---

### 4. Enhanced Engram Levels 2-5 → User Memory Integration

**Dead Code (from audit):**
```
[DEAD-H2-001] engram_user_memory.py:526
- enhanced_engram_lookup() - MOCK IMPLEMENTATIONS
- Levels 2-5 only stubs, Level 4/5 not ready
- CAM Integration imported but not used
```

**Phase 95 Roadmap:**
```python
# From session_tools.py
async def _get_user_memory(self) -> Dict:
    """Retrieve user preferences from Engram (if integrated)."""
    try:
        # From HAIKU_1_ENGRAM_STATUS.md - engram.recall(query, limit)
        prefs = self.engram.recall("user_preferences", limit=5)
        recent_work = self.engram.recall("recent_work", limit=3)
```

**Match Analysis:**
| Aspect | Dead Code | Roadmap | Status |
|--------|-----------|---------|--------|
| Function | `enhanced_engram_lookup()` | `engram.recall()` | **SAME INTERFACE** |
| Levels | L2-5 mock | Uses basic recall | **ROADMAP SIMPLER** |
| CAM Integration | Imported but unused | Not mentioned | **OPPORTUNITY** |

**Completion Strategy:**
```python
# In engram_user_memory.py - Complete Level 2 (Semantic)
async def enhanced_engram_lookup(query: str, level: int = 1) -> Dict:
    """
    Multi-level lookup:
    - L1: Static hash (WORKS) ✅
    - L2: Semantic similarity (COMPLETE THIS)
    - L3: CAM context-aware (USE EXISTING CAM)
    - L4: Cross-session (DEFER)
    - L5: Predictive (DEFER)
    """
    if level == 1:
        return await _level1_hash_lookup(query)  # ✅ EXISTS
    elif level == 2:
        # COMPLETE THIS using Qdrant semantic search
        from src.search.hybrid_search import semantic_search
        return await semantic_search(query, collection="engram_preferences")
    elif level == 3:
        # USE EXISTING CAM
        from src.orchestration.cam_engine import get_cam_engine
        cam = get_cam_engine()
        return await cam.contextual_lookup(query)
    # L4, L5 - defer to Phase 96
```

**Lines to Connect:**
- `engram_user_memory.py:526` → `session_tools.py:_get_user_memory()`
- `engram_user_memory.py:548` (CAM import) → Actually USE in Level 3

---

### 5. OpenRouterProvider Empty Class → Compound Tools Fallback

**Dead Code (from audit):**
```
[BUG-H1-001] api_aggregator_v3.py:181-182
- OpenRouterProvider class - EMPTY (pass only)
- No generate() implementation
```

**Phase 95 Roadmap:**
```python
# From compound_tools.py - VetkaFeatureImplementationTool
result = await orchestrator.execute_workflow(
    request=feature_request,
    workflow_type="pm_to_qa",
    return_artifacts=True
)
# Uses orchestrator which needs working providers!
```

**Match Analysis:**
| Aspect | Dead Code | Roadmap | Status |
|--------|-----------|---------|--------|
| Class | `OpenRouterProvider` | Used via orchestrator | **DEPENDENCY** |
| Impact | No fallback if direct API fails | Workflow fails | **CRITICAL** |

**Fix Priority:** HIGH - без рабочего OpenRouterProvider compound tools могут падать!

```python
# In api_aggregator_v3.py:181 - IMPLEMENT instead of pass
class OpenRouterProvider(APIProvider):
    async def generate(self, prompt: str, **kwargs) -> str:
        """Call OpenRouter API."""
        from src.elisya.api_gateway import APIGateway
        gateway = APIGateway()
        return await gateway._call_openrouter(
            model=kwargs.get("model", "openai/gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}]
        )
```

---

## Summary: Dead Code → Phase 95 Integration Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DEAD CODE REVIVAL PLAN                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  JARVIS Enricher ─────────────────────► Session Init               │
│  (jarvis_prompt_enricher.py:610,626)     (session_tools.py)        │
│                                                                     │
│  ELISION Viewport ────────────────────► Compound Tools             │
│  (jarvis_prompt_enricher.py:467)         (compound_tools.py)       │
│                                                                     │
│  Memory Compression ──────────────────► State Manager              │
│  (compression.py:371)                    (mcp_state_manager.py)    │
│                                                                     │
│  Enhanced Engram L2-5 ────────────────► User Memory                │
│  (engram_user_memory.py:526)             (session_tools.py)        │
│                                                                     │
│  OpenRouterProvider ──────────────────► Workflow Execution         │
│  (api_aggregator_v3.py:181)              (workflow_tools.py)       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Order (Phase 95)

| Step | Task | Files | Est. Lines | Priority |
|------|------|-------|------------|----------|
| 1 | Fix OpenRouterProvider | api_aggregator_v3.py:181 | ~15 | CRITICAL |
| 2 | Enable JARVIS in Session Init | session_tools.py (NEW) | ~45 | HIGH |
| 3 | Enable ELISION Viewport | compound_tools.py (NEW) | ~20 | HIGH |
| 4 | Complete Engram L2-3 | engram_user_memory.py:526 | ~30 | MEDIUM |
| 5 | Start Compression Scheduler | main.py + mcp_state_manager.py | ~25 | MEDIUM |

**Total Estimated:** ~135 lines to revive ALL dead code!

---

## Conclusion

**Dead code audit выявил инфраструктуру, которая уже написана для Phase 95!**

Это не мёртвый код - это **НЕДОСТРОЙ**, который roadmap планирует использовать:

1. **JARVIS** - готов, нужно просто вызвать в session_tools
2. **ELISION** - готов, нужно интегрировать в compound_tools
3. **Compression** - готов, нужно запустить scheduler
4. **Engram L2-5** - частично готов, нужно дописать L2-3
5. **OpenRouterProvider** - пустой, нужно реализовать

**Рекомендация:** Начать Phase 95 с **Step 1** (OpenRouterProvider fix) - это критическая зависимость для всех workflow tools.
