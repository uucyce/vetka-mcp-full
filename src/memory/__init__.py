"""
VETKA Memory Package.

Memory subsystem including:
- Qdrant vector store integration
- Weaviate graph integration
- Compression (age-based, ELISION)
- User memory (Engram)
- Phase 99: STM Buffer, MGC Cache, MemoryProxy
- Phase 104: CAM Memory (Context Awareness for ELISION)

@status: active
@phase: 104
@depends: -
@used_by: src.initialization, src.orchestration, src.agents
"""

# Phase 99: STM Buffer (Short-Term Memory)
from src.memory.stm_buffer import (
    STMBuffer,
    STMEntry,
    get_stm_buffer,
    reset_stm_buffer,
)

# Phase 99: MGC Cache (Multi-Generational Cache)
from src.memory.mgc_cache import (
    MGCCache,
    MGCEntry,
    get_mgc_cache,
    reset_mgc_cache,
)

# Phase 99: Memory Proxy (Rate Limiting, Circuit Breaker)
from src.memory.memory_proxy import (
    MemoryProxy,
    CircuitBreakerOpen,
    RateLimitExceeded,
    get_memory_proxy,
    get_embedding_proxy,
    get_qdrant_proxy,
    create_embedding_proxy,
    create_qdrant_proxy,
    create_json_proxy,
    reset_all_proxies,
)

# Phase 104: Surprise Detector (Context Awareness Module for ELISION)
# MARKER_119.5: Renamed cam_memory.py -> surprise_detector.py
from src.memory.surprise_detector import (
    CAMMemory,
    get_cam_memory,
    reset_cam_memory,
    get_surprise_metrics,
    compute_block_surprise,
    get_compression_advice,
    STOPWORDS,
)

# Phase 187.8: ENGRAM L1 Cache (Deterministic O(1) Lookup)
from src.memory.engram_cache import (
    EngramCache,
    EngramEntry,
    get_engram_cache,
    reset_engram_cache,
)

__all__ = [
    # STM Buffer
    "STMBuffer",
    "STMEntry",
    "get_stm_buffer",
    "reset_stm_buffer",
    # MGC Cache
    "MGCCache",
    "MGCEntry",
    "get_mgc_cache",
    "reset_mgc_cache",
    # Memory Proxy
    "MemoryProxy",
    "CircuitBreakerOpen",
    "RateLimitExceeded",
    "get_memory_proxy",
    "get_embedding_proxy",
    "get_qdrant_proxy",
    "create_embedding_proxy",
    "create_qdrant_proxy",
    "create_json_proxy",
    "reset_all_proxies",
    # CAM Memory (Phase 104)
    "CAMMemory",
    "get_cam_memory",
    "reset_cam_memory",
    "get_surprise_metrics",
    "compute_block_surprise",
    "get_compression_advice",
    "STOPWORDS",
    # ENGRAM L1 Cache (Phase 187.8)
    "EngramCache",
    "EngramEntry",
    "get_engram_cache",
    "reset_engram_cache",
]
