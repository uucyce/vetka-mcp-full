# PHASE 77-90: ENGRAM USER MEMORY INTEGRATION

## SUMMARY

**Engram** = O(1) хеш-таблица для статических паттернов (из DeepSeek архитектуры).

- DeepSeek разгоняет ОДНУ модель (внутренняя память)
- VETKA разгоняет СИСТЕМУ вокруг модели (внешняя память)

### Memory Stack:
```
CAM (Constructivist Agentic Memory)
  ├─ Activation scores + surprise metrics
  ├─ Branching/Pruning/Merging
  └─ src/orchestration/cam_engine.py

ELISYA (Context Reframing Middleware)
  ├─ 4 уровня LOD (GLOBAL/TREE/LEAF/FULL)
  ├─ Semantic tinting (SECURITY/PERFORMANCE/RELIABILITY)
  └─ src/elisya/middleware.py

ELISION (JSON Compression)
  ├─ Path compression: /src/orchestration/ → s/o/
  ├─ Key abbreviation: current_file → cf, dependencies → d
  ├─ 23-43% экономия токенов
  └─ src/api/handlers/message_utils.py

ENGRAM (Query Cache + User Preferences)
  ├─ RAM cache для горячих (usage > 5)
  ├─ Qdrant offload для холодных
  ├─ Temporal decay: 0.05/week
  └─ src/memory/engram_user_memory.py (Phase 76.3)
```

---

## ARCHITECTURE

```
User Query
    ↓
[1] Embed query (768D Gemma embedding)
    ↓
[2] ENGRAM LOOKUP (O(1) in RAM)
    ├─ Match score > 0.8? → Return cached ELISION context
    └─ No match? → Continue to [3]
    ↓
[3] CAM SURPRISE CALCULATION
    ├─ High surprise (>0.7)? → Full Elisya compression
    ├─ Low surprise (<0.3)?  → Use Engram + ELISION only
    └─ Medium (0.3-0.7)?    → Hybrid: CAM activation + ELISION
    ↓
[4] STORE IN ENGRAM
    └─ engram_table.insert(query_emb, compressed_context)
    ↓
[5] SEND TO LLM with Legend header if cold start
```

---

## TASK FOR SONNET

Implement Engram layer between CAM/ELISYA middleware and LLM agent calls.

### File: src/memory/engram_query_cache.py (NEW)

```python
from typing import Optional, Dict, Any
import numpy as np
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CachedContext:
    embedding: np.ndarray
    context: str
    score: float
    usage_count: int
    confidence: float
    created_at: datetime
    last_accessed: datetime

class EngramQueryCache:
    """
    O(1) hash table for static query patterns.
    Hybrid: RAM hot cache + Qdrant cold storage.
    """

    OFFLOAD_THRESHOLD = 5  # usage_count > 5 → RAM
    DECAY_RATE = 0.05  # per week
    MIN_CONFIDENCE = 0.1
    MAX_SIZE = 10000

    def __init__(self, qdrant_client=None):
        self.hot_cache: Dict[str, CachedContext] = {}
        self.qdrant = qdrant_client

    def lookup(self, embedding: np.ndarray, threshold: float = 0.8) -> Optional[CachedContext]:
        """O(1) lookup in RAM cache first, then Qdrant."""
        # 1. Check hot cache (RAM)
        for key, cached in self.hot_cache.items():
            score = self._cosine_sim(embedding, cached.embedding)
            if score > threshold:
                cached.usage_count += 1
                cached.last_accessed = datetime.now()
                return cached

        # 2. Check cold cache (Qdrant)
        if self.qdrant:
            results = self.qdrant.search(embedding, limit=1)
            if results and results[0].score > threshold:
                # Promote to hot if frequently used
                return self._promote_from_cold(results[0])

        return None

    def insert(self, embedding: np.ndarray, context: str) -> None:
        """Store new engram."""
        key = self._hash_embedding(embedding)

        self.hot_cache[key] = CachedContext(
            embedding=embedding,
            context=context,
            score=1.0,
            usage_count=1,
            confidence=1.0,
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )

        # Evict if over capacity
        if len(self.hot_cache) > self.MAX_SIZE:
            self._evict_least_used()

    def decay_confidence(self) -> None:
        """Apply temporal decay to all entries."""
        for cached in self.hot_cache.values():
            cached.confidence -= self.DECAY_RATE
            if cached.confidence < self.MIN_CONFIDENCE:
                self._offload_to_cold(cached)

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def _hash_embedding(self, embedding: np.ndarray) -> str:
        return str(hash(embedding.tobytes()))
```

### File: src/orchestration/cam_engine.py (MODIFY)

Add method:
```python
def calculate_surprise(self, embedding: np.ndarray) -> float:
    """
    Calculate surprise metric for query embedding.
    Returns: 0.0-1.0 (1.0 = максимальная новизна)
    """
    if not self.recent_embeddings:
        return 1.0  # First query is always surprising

    # Average cosine distance from recent queries
    distances = []
    for recent_emb in self.recent_embeddings[-10:]:
        sim = np.dot(embedding, recent_emb) / (
            np.linalg.norm(embedding) * np.linalg.norm(recent_emb)
        )
        distances.append(1.0 - sim)  # Distance = 1 - similarity

    return float(np.mean(distances))
```

### File: src/orchestration/orchestrator_with_elisya.py (MODIFY)

Integration point:
```python
from src.memory.engram_query_cache import EngramQueryCache

class OrchestratorWithElisya:
    def __init__(self):
        self.engram = EngramQueryCache()
        # ... existing init

    async def process_message(self, message: str, context: dict):
        # 1. Embed query
        query_emb = self.embed_query(message)

        # 2. Engram lookup
        cached = self.engram.lookup(query_emb)
        if cached and cached.score > 0.8:
            return {"context": cached.context, "_source": "engram_cache"}

        # 3. CAM surprise check
        surprise = self.cam.calculate_surprise(query_emb)

        # 4. Route based on surprise
        if surprise > 0.7:
            # High novelty - full Elisya
            compressed = await self.elisya.reframe(context)
        elif surprise < 0.3:
            # Low novelty - ELISION only
            compressed = self.elision_compress(context)
        else:
            # Hybrid
            compressed = await self.elisya.reframe(context, lod="TREE")

        # 5. Store in Engram
        self.engram.insert(query_emb, compressed)

        return {"context": compressed, "_source": "cam_driven"}
```

---

## KEY FILE PATHS

```
# MEMORY
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/engram_user_memory.py
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/compression.py
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_client.py

# CAM
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/cam_engine.py

# ELISYA
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/middleware.py
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/state.py

# ELISION
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/message_utils.py

# ORCHESTRATION
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/langgraph_nodes.py
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/memory_manager.py

# DOCS
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/73_ph/ELISYA_INTEGRATION_AUDIT.md
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/80_ph_mcp_agents/PROMPT_FOR_GROK_ELISIUM.md
```

---

## SUCCESS CRITERIA

1. **30%+ cache hit rate** on static patterns
2. **<50ms overhead** for Engram lookup
3. **Seamless fallback** to full CAM+ELISYA
4. **Token savings**: 23-43% ELISION + cache hits

---

## TIMELINE

- Phase 77: EngramQueryCache core (~3-4h)
- Phase 78: CAM surprise integration (~2h)
- Phase 79: Orchestrator integration (~2h)
- Phase 80-89: Testing + optimization
- Phase 90: Production ready

**Total: ~17-25 hours**

---

## RELATED DOCS

- NeurIPS 2025 CAM paper — Constructivist memory operations
- DeepSeek Engram — Hash tables for static n-grams
- PROMPT_FOR_GROK_ELISIUM.md — Compression language
- THE_LEGENDARY_ELISYA_MISHAP.md — История Elisya
