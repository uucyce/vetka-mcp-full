# Phase 67: Code Changes Summary

## File: `src/api/handlers/message_utils.py`

### Header Update

```diff
-@phase Phase 64.1
+@phase Phase 67 - CAM + Qdrant Integration
-@lastAudit 2026-01-17
+@lastAudit 2026-01-18
```

### New Imports

```diff
 import os
+import logging
-from typing import List, Dict, Any, Optional
+from typing import List, Dict, Any, Optional, Tuple

+logger = logging.getLogger("VETKA_CONTEXT")
```

### New Functions Added

#### `_estimate_tokens()` (line 97)
```python
def _estimate_tokens(text: str) -> int:
    """Estimate token count (~4 chars per token)."""
    return len(text) // 4
```

#### `_smart_truncate()` (line 110)
```python
def _smart_truncate(content: str, max_tokens: int = 1000) -> str:
    """Preserve 60% head + 40% tail."""
    max_chars = max_tokens * 4
    if len(content) <= max_chars:
        return content
    head_chars = int(max_chars * 0.6)
    tail_chars = int(max_chars * 0.4)
    head = content[:head_chars]
    tail = content[-tail_chars:]
    return f"{head}\n\n... [truncated {len(content) - max_chars} chars] ...\n\n{tail}"
```

#### `_get_qdrant_relevance()` (line 140)
```python
def _get_qdrant_relevance(file_path: str, query_embedding: List[float]) -> float:
    """Get semantic relevance from Qdrant (0.0-1.0)."""
    try:
        from src.memory.qdrant_client import get_qdrant_client
        qdrant = get_qdrant_client()
        if not qdrant or not qdrant.health_check():
            return 0.5
        results = qdrant.search_by_vector(query_vector=query_embedding, limit=50, score_threshold=0.3)
        for result in results:
            if file_path in result.get('path', '') or result.get('path', '') in file_path:
                return result.get('score', 0.5)
        return 0.3  # Not found
    except Exception:
        return 0.5
```

#### `_get_cam_activation()` (line 178)
```python
def _get_cam_activation(file_path: str) -> float:
    """Get CAM activation score (0.0-1.0)."""
    try:
        from src.orchestration.cam_engine import VETKACAMEngine
        cam = VETKACAMEngine()
        for node_id, node in cam.nodes.items():
            if file_path in node.path or node.path in file_path:
                return cam.calculate_activation_score(node_id)
        return 0.5
    except Exception:
        return 0.5
```

#### `_rank_pinned_files()` (line 207)
```python
def _rank_pinned_files(
    pinned_files: list,
    user_query: str,
    qdrant_weight: float = 0.7,
    cam_weight: float = 0.3
) -> List[Tuple[Dict, float]]:
    """Rank by: 0.7*qdrant + 0.3*cam."""
    # ... implementation
```

### `build_pinned_context()` Signature Change

```diff
 def build_pinned_context(
-    pinned_files: list, max_files: int = 10
+    pinned_files: list,
+    user_query: str = "",
+    max_files: int = 5,
+    max_tokens_per_file: int = 1000,
+    max_total_tokens: int = 4000
 ) -> str:
```

### New Legacy Function

```python
def build_pinned_context_legacy(pinned_files: list, max_files: int = 10) -> str:
    """Pre-Phase 67 implementation for fallback."""
    # Original simple logic preserved
```

### Exports Update

```diff
 __all__ = [
     'format_history_for_prompt',
     'load_pinned_file_content',
     'build_pinned_context',
+    'build_pinned_context_legacy',
 ]
```

---

## File: `src/api/handlers/user_message_handler.py`

### Call Site 1 (line 259)

```diff
-                    # Phase 61: Build pinned files context
-                    pinned_context = build_pinned_context(pinned_files) if pinned_files else ""
+                    # Phase 67: Build pinned files context with smart selection
+                    pinned_context = build_pinned_context(pinned_files, user_query=text) if pinned_files else ""
```

### Call Site 2 (line 392)

```diff
-                # Phase 61: Build pinned files context
-                pinned_context = build_pinned_context(pinned_files) if pinned_files else ""
+                # Phase 67: Build pinned files context with smart selection
+                pinned_context = build_pinned_context(pinned_files, user_query=text) if pinned_files else ""
```

### Call Site 3 (line 619)

```diff
-                    # Phase 61: Build pinned files context
-                    pinned_context = build_pinned_context(pinned_files) if pinned_files else ""
+                    # Phase 67: Build pinned files context with smart selection
+                    pinned_context = build_pinned_context(pinned_files, user_query=clean_text) if pinned_files else ""
```

### Call Site 4 (line 1295)

```diff
                 # ========================================
                 # PHASE 17-J: BUILD PROMPT WITH CHAIN CONTEXT
-                # Phase 61: Include pinned files context
+                # Phase 67: Include pinned files context with smart selection
                 # ========================================
-                # Phase 61: Build pinned context once
-                agent_pinned_context = build_pinned_context(pinned_files) if pinned_files else ""
+                # Phase 67: Build pinned context with user query for relevance ranking
+                agent_pinned_context = build_pinned_context(pinned_files, user_query=text) if pinned_files else ""
```

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Files modified | 2 |
| New functions | 6 |
| Lines added | ~290 |
| Lines removed | ~16 |
| Call sites updated | 4 |
| Tests passed | 7 unit + 3 integration |
