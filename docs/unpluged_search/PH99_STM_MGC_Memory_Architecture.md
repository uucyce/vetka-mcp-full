# Phase 99: Unified Memory Architecture

**Date:** 2026-01-28
**Pre-Tauri Migration Phase**
**Based on:** Grok MGC Research + Grok STM Research

---

## Executive Summary

Phase 99 consolidates two major memory subsystems into VETKA's cognitive architecture:

1. **MGC (Multi-Generational Consistency)** — PostgreSQL-inspired hierarchical cache
2. **STM (Short-Term Memory)** — Dynamic buffer for recent interactions

Together they form a **three-tier memory system** with automatic promotion/demotion.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    VETKA Memory Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    STM Buffer (5-10 items)               │   │
│  │  • Recent interactions with decay                        │   │
│  │  • Surprise events from CAM                              │   │
│  │  • Quick context for HOPE                                │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                         │ overflow/important                    │
│                         ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 MGC Gen 0 (RAM) — Hot                    │   │
│  │  • 100 items max, LRU eviction                          │   │
│  │  • Access count tracking                                 │   │
│  │  • Sub-millisecond access                                │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                         │ eviction (access_count < threshold)   │
│                         ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               MGC Gen 1 (Qdrant) — Warm                  │   │
│  │  • Vector embeddings                                     │   │
│  │  • Semantic search                                       │   │
│  │  • 10ms access latency                                   │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                         │ cold storage                          │
│                         ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               MGC Gen 2 (JSON) — Cold                    │   │
│  │  • Persistent fallback                                   │   │
│  │  • Full archive                                          │   │
│  │  • Disk-based                                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    MemoryProxy                           │   │
│  │  • Rate limiting                                         │   │
│  │  • Connection pooling                                    │   │
│  │  • Request deduplication                                 │   │
│  │  • Vicious cycle prevention                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component 1: STM Buffer

### Purpose
Fast-access buffer for the most recent 5-10 interactions with automatic decay.

### Location
`src/memory/stm_buffer.py` (NEW)

### Schema
```python
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class STMEntry:
    content: str
    timestamp: datetime
    source: str  # 'user', 'agent', 'system', 'cam_surprise'
    weight: float = 1.0  # decays over time
    surprise_score: float = 0.0  # FIX: CAM integration (Grok review)
    metadata: Optional[Dict[str, Any]] = None

class STMBuffer:
    def __init__(self, max_size: int = 10, decay_rate: float = 0.1):
        self._buffer: deque[STMEntry] = deque(maxlen=max_size)
        self.decay_rate = decay_rate

    def add(self, entry: STMEntry) -> None:
        """Add entry, apply decay to existing items"""
        self._apply_decay()
        self._buffer.append(entry)

    def add_from_cam(self, content: str, surprise_score: float) -> None:
        """Add CAM surprise event with boosted weight (Grok review)"""
        entry = STMEntry(
            content=content,
            timestamp=datetime.now(),
            source='cam_surprise',
            weight=1.0 + surprise_score,  # Surprise boosts initial weight
            surprise_score=surprise_score
        )
        self.add(entry)

    def get_context(self, max_items: int = 5) -> List[STMEntry]:
        """Get recent items sorted by weight (empty list if buffer empty)"""
        if not self._buffer:
            return []
        return sorted(self._buffer, key=lambda x: x.weight, reverse=True)[:max_items]

    def _apply_decay(self) -> None:
        """Reduce weights of older items"""
        for entry in self._buffer:
            age_seconds = (datetime.now() - entry.timestamp).total_seconds()
            entry.weight *= (1 - self.decay_rate * (age_seconds / 60))
```

### Integration Points

| File | Line | Integration |
|------|------|-------------|
| `src/orchestration/workflow.py` | State schema | Add `stm_buffer: STMBuffer` |
| `src/orchestration/langgraph_nodes.py` | ~493 | Update STM after HOPE |
| `src/agents/cam_agent.py` | surprise events | Add to STM |
| `src/agents/hope_enhancer.py` | analyze() | Use STM for quick context |
| `client/src/store/useStore.ts` | state | Mirror STM for 3D viz |

---

## Component 2: MGC Hierarchical Cache

### Purpose
PostgreSQL-inspired multi-generational cache with automatic promotion/demotion.

### Location
`src/memory/mgc_cache.py` (NEW)

### Schema
```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

@dataclass
class MGCEntry:
    key: str
    value: Any
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    generation: int = 0  # 0=RAM, 1=Qdrant, 2=JSON

class MGCCache:
    def __init__(
        self,
        gen0_max: int = 100,
        promotion_threshold: int = 3,
        qdrant_client=None
    ):
        self.gen0: Dict[str, MGCEntry] = {}  # RAM cache
        self.gen0_max = gen0_max
        self.promotion_threshold = promotion_threshold
        self.qdrant = qdrant_client

    async def get(self, key: str) -> Optional[Any]:
        """Get from fastest available generation"""
        # Gen 0: RAM (hot)
        if key in self.gen0:
            entry = self.gen0[key]
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            return entry.value

        # Gen 1: Qdrant (warm)
        if self.qdrant:
            result = await self._get_from_qdrant(key)
            if result:
                # Promote to Gen 0 if accessed often
                await self._maybe_promote(key, result)
                return result

        # Gen 2: JSON (cold)
        return await self._get_from_json(key)

    async def set(self, key: str, value: Any) -> None:
        """Set in Gen 0, handle eviction"""
        if len(self.gen0) >= self.gen0_max:
            await self._evict_lru()

        self.gen0[key] = MGCEntry(key=key, value=value)

    async def _evict_lru(self) -> None:
        """Evict least recently used to Gen 1"""
        if not self.gen0:
            return

        lru_key = min(self.gen0, key=lambda k: self.gen0[k].last_accessed)
        entry = self.gen0.pop(lru_key)

        # Demote to Gen 1 (Qdrant) if valuable
        if entry.access_count >= self.promotion_threshold:
            await self._store_in_qdrant(entry)
        else:
            # Demote to Gen 2 (JSON)
            await self._store_in_json(entry)
```

### Generation Flow
```
New Entry → Gen 0 (RAM)
                │
                ├── access_count >= threshold → stays in Gen 0
                │
                └── LRU eviction → Gen 1 (Qdrant)
                                        │
                                        └── cold/stale → Gen 2 (JSON)
```

---

## Component 3: MemoryProxy

### Purpose
PgBouncer-like proxy to prevent vicious cycles (overload → retries → more overload).

### Location
`src/memory/memory_proxy.py` (NEW)

### Schema
```python
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

class MemoryProxy:
    """
    PgBouncer-like proxy for memory operations.

    Prevents vicious cycles:
    - Rate limiting: max N requests per second
    - Connection pooling: semaphore limits concurrent ops
    - Deduplication: same request within window returns cached
    - Circuit breaker: backs off on repeated failures
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        rate_limit: int = 100,  # requests per second
        dedup_window: float = 0.5,  # seconds
        circuit_breaker_threshold: int = 5  # failures before tripping
    ):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limit = rate_limit
        self.dedup_window = dedup_window
        self.circuit_breaker_threshold = circuit_breaker_threshold

        self._recent_requests: Dict[str, datetime] = {}
        self._cached_results: Dict[str, Any] = {}
        self._request_count = 0
        self._last_reset = datetime.now()
        self._failure_count = 0
        self._circuit_open = False
        self._circuit_open_until: Optional[datetime] = None

    async def execute(self, key: str, func: Callable, *args, **kwargs) -> Any:
        """Execute with rate limiting, deduplication, and circuit breaker"""
        # Circuit breaker check
        if self._circuit_open:
            if datetime.now() < self._circuit_open_until:
                raise RuntimeError("Circuit breaker open - backing off")
            self._circuit_open = False
            self._failure_count = 0

        # Deduplication check
        if self._is_duplicate(key):
            return self._cached_results.get(key)

        # Rate limiting
        await self._check_rate_limit()

        # Connection pooling via semaphore
        async with self.semaphore:
            try:
                result = await func(*args, **kwargs)
                self._cache_result(key, result)
                self._failure_count = 0  # Reset on success
                return result
            except Exception as e:
                self._failure_count += 1
                if self._failure_count >= self.circuit_breaker_threshold:
                    self._trip_circuit_breaker()
                raise

    def _is_duplicate(self, key: str) -> bool:
        """Check if same request within dedup window"""
        last_time = self._recent_requests.get(key)
        if last_time and (datetime.now() - last_time).total_seconds() < self.dedup_window:
            return True
        self._recent_requests[key] = datetime.now()
        return False

    def _cache_result(self, key: str, result: Any) -> None:
        """Cache result for deduplication"""
        self._cached_results[key] = result
        # Cleanup old entries (keep last 100)
        if len(self._cached_results) > 100:
            oldest = min(self._recent_requests, key=self._recent_requests.get)
            self._cached_results.pop(oldest, None)
            self._recent_requests.pop(oldest, None)

    async def _check_rate_limit(self) -> None:
        """Enforce rate limiting"""
        now = datetime.now()
        if (now - self._last_reset).total_seconds() >= 1.0:
            self._request_count = 0
            self._last_reset = now

        self._request_count += 1
        if self._request_count > self.rate_limit:
            wait_time = 1.0 - (now - self._last_reset).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

    def _trip_circuit_breaker(self) -> None:
        """Open circuit breaker for exponential backoff"""
        self._circuit_open = True
        backoff = min(30, 2 ** self._failure_count)  # Max 30 seconds
        self._circuit_open_until = datetime.now() + timedelta(seconds=backoff)
```

### Vicious Cycle Prevention
```
Normal Flow:
  Request → MemoryProxy → MGC Cache → Response

Overload Detection:
  High latency detected → reduce rate_limit
  Queue depth > threshold → reject new requests
  Retry storm detected → exponential backoff

Recovery:
  Latency normalizes → gradually increase rate_limit
  Queue drains → accept new requests
```

---

## Concrete Integration Points (Grok Review)

### STM → LangGraph
```python
# src/orchestration/langgraph_nodes.py:493 (after HOPE analysis)
async def run_hope_node(state: WorkflowState) -> WorkflowState:
    # ... existing HOPE code ...

    # FIX_99.1: Add to STM after HOPE
    if state.get('stm_buffer'):
        state['stm_buffer'].add(STMEntry(
            content=state.get('hope_summary', '')[:500],
            timestamp=datetime.now(),
            source='hope'
        ))

    return state
```

### CAM → STM
```python
# src/agents/cam_agent.py (on surprise event)
def on_surprise_detected(self, content: str, score: float):
    if self.stm_buffer and score > 0.3:  # threshold
        self.stm_buffer.add_from_cam(content, score)
```

### STM → HOPE (quick context)
```python
# src/agents/hope_enhancer.py
def analyze(self, content: str, ..., stm_context: List[STMEntry] = None):
    if stm_context:
        recent = "\n".join(e.content for e in stm_context[:3])
        content = f"Recent context:\n{recent}\n\n{content}"
```

### Frontend STM Mirror
```typescript
// client/src/store/useStore.ts
interface STMState {
  stmBuffer: Array<{
    content: string;
    timestamp: string;
    source: string;
    weight: number;
  }>;
  addToSTM: (entry: STMEntry) => void;
}
```

---

## Integration Plan

### Phase 99.1: STM Buffer
1. Create `src/memory/stm_buffer.py`
2. Add to LangGraph state schema
3. Update langgraph_nodes.py HOPE node
4. Connect CAM surprise events
5. Frontend mirror in useStore.ts

### Phase 99.2: MGC Cache
1. Create `src/memory/mgc_cache.py`
2. Replace direct Qdrant calls in:
   - `src/memory/qdrant_client.py`
   - `src/scanners/embedding_pipeline.py`
   - `src/orchestration/cam_engine.py`
3. Add JSON fallback (Gen 2)
4. Implement promotion/demotion logic

### Phase 99.3: MemoryProxy
1. Create `src/memory/memory_proxy.py`
2. Wrap all memory operations
3. Add circuit breaker pattern
4. Implement exponential backoff

### Phase 99.4: Frontend Integration
1. Add STM visualization component
2. Show MGC generation indicators
3. Memory health dashboard

---

## Test Cases

### STM Tests
```python
def test_stm_decay():
    """Older items should have lower weights"""

def test_stm_overflow():
    """Oldest items evicted when full"""

def test_stm_surprise_priority():
    """Surprise events get higher initial weight"""
```

### MGC Tests
```python
def test_mgc_promotion():
    """Frequently accessed items stay in Gen 0"""

def test_mgc_eviction():
    """LRU items demoted to Gen 1"""

def test_mgc_fallback():
    """Gen 2 JSON serves when Qdrant unavailable"""
```

### MemoryProxy Tests
```python
def test_deduplication():
    """Same request within window returns cached result"""

def test_rate_limiting():
    """Requests throttled when limit exceeded"""

def test_vicious_cycle_prevention():
    """Overload triggers protective measures"""
```

---

## Migration Notes

### Before Tauri
- Implement core classes (STM, MGC, MemoryProxy)
- Add markers to all new files
- Integration tests passing
- No breaking changes to existing API

### After Tauri
- Rust bindings for performance-critical paths
- Native memory management
- Cross-process memory sharing

---

## Files to Create

| File | Purpose | Priority |
|------|---------|----------|
| `src/memory/stm_buffer.py` | Short-term memory | HIGH |
| `src/memory/mgc_cache.py` | Multi-generational cache | HIGH |
| `src/memory/memory_proxy.py` | Rate limiting/pooling | MEDIUM |
| `tests/test_stm_buffer.py` | STM tests | HIGH |
| `tests/test_mgc_cache.py` | MGC tests | HIGH |
| `client/src/components/memory/STMVisualization.tsx` | Frontend | LOW |

---

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `src/orchestration/workflow.py` | Add stm_buffer to state | HIGH |
| `src/orchestration/langgraph_nodes.py` | STM update after HOPE | HIGH |
| `src/agents/cam_agent.py` | Surprise → STM | HIGH |
| `src/agents/hope_enhancer.py` | Use STM context | MEDIUM |
| `src/memory/qdrant_client.py` | Route through MGC | MEDIUM |
| `client/src/store/useStore.ts` | Mirror STM | MEDIUM |

---

## Success Criteria

- [ ] STM buffer with decay working
- [ ] MGC 3-tier cache operational
- [ ] MemoryProxy preventing vicious cycles
- [ ] All tests passing
- [ ] No performance regression
- [ ] Frontend visualization (optional pre-Tauri)

---

**Report Generated:** 2026-01-28
**Based On:** Grok MGC Research + Grok STM Research
**Ready For:** Phase 99 Implementation
