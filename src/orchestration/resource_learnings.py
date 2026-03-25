"""
Resource Learnings Store — Phase 183.2

Stores and retrieves lessons learned from pipeline executions.
After each Verifier merge, extracts 2-3 lessons and embeds them in Qdrant
collection `VetkaResourceLearnings`. Architect queries these before planning.

Flow:
    Verifier merge → extract_lessons() → embed → Qdrant
    Architect plan → search_learnings(task_description) → inject into context

MARKER_198.P0.4: ENGRAM L2→L1 auto-promotion implemented.
When a learning is matched >=3 times, it auto-promotes to ENGRAM L1 via
engram_cache.put(). Match counts are persisted in
data/reflex/learning_match_counts.json using PROJECT_ROOT absolute path
(worktree-safe — never relative paths).

@status: active
@phase: 183.2 / 198.P0.4
@depends: src/memory/qdrant_client.py, src/utils/embedding_service.py,
          src/memory/engram_cache.py
"""

import json
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("VETKA_LEARNINGS")

# Qdrant collection for learnings
COLLECTION_NAME = "VetkaResourceLearnings"
VECTOR_SIZE = 768

# MARKER_198.P0.4: Use PROJECT_ROOT absolute path — worktree-safe (never relative)
_PROJECT_ROOT = Path(__file__).parent.parent.parent

# Local fallback file when Qdrant is unavailable
_FALLBACK_FILE = _PROJECT_ROOT / "data" / "resource_learnings.json"

# MARKER_198.P0.4: Counter file for L2→L1 auto-promotion threshold tracking
_MATCH_COUNTS_FILE = _PROJECT_ROOT / "data" / "reflex" / "learning_match_counts.json"

# MARKER_198.P0.4: Number of L2 matches required to trigger ENGRAM L1 promotion
_PROMOTION_THRESHOLD = 3


def _load_match_counts() -> Dict[str, int]:
    """Load learning match counts from disk. Returns empty dict on any error.

    MARKER_198.P0.4: Persisted in data/reflex/learning_match_counts.json.
    """
    try:
        if _MATCH_COUNTS_FILE.exists():
            return json.loads(_MATCH_COUNTS_FILE.read_text())
    except Exception as e:
        logger.warning(f"[Learnings] Could not load match counts: {e}")
    return {}


def _save_match_counts(counts: Dict[str, int]) -> None:
    """Persist learning match counts to disk.

    MARKER_198.P0.4: Creates parent dirs if absent (first-run safe).
    """
    try:
        _MATCH_COUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _MATCH_COUNTS_FILE.write_text(json.dumps(counts, indent=2))
    except Exception as e:
        logger.warning(f"[Learnings] Could not save match counts: {e}")


def _derive_engram_key(result: Any) -> str:
    """Derive a stable ENGRAM key from a Qdrant result payload.

    MARKER_198.P0.4: Key format follows Phase 186 Grok spec:
    agent::file::action::phase_type

    Falls back to compound of task_id + point id when rich metadata absent.
    """
    payload = result.payload if hasattr(result, "payload") else {}
    task_id = payload.get("task_id") or "unknown"
    files = payload.get("files") or []
    filename = Path(files[0]).name if files else "unknown"
    category = payload.get("category") or "pattern"
    # Map learning category to action concept
    action_map = {
        "pitfall": "danger",
        "optimization": "optimize",
        "pattern": "pattern",
        "architecture": "arch",
    }
    action = action_map.get(category, category)
    # agent wildcard: these learnings are cross-agent
    return f"*::{filename}::{action}::{task_id}"


def _promote_to_engram_l1(result: Any, match_count: int) -> None:
    """Auto-promote a Qdrant learning result to ENGRAM L1 cache.

    MARKER_198.P0.4: Called when match_count >= _PROMOTION_THRESHOLD.
    Category mapping: 'pitfall' → 'danger', everything else → 'architecture'.
    """
    try:
        from src.memory.engram_cache import get_engram_cache
        payload = result.payload if hasattr(result, "payload") else {}
        lesson_text = payload.get("text", "")
        if not lesson_text:
            return

        raw_category = payload.get("category", "pattern")
        # MARKER_198.P0.4: pitfalls become danger (permanent TTL); others architecture
        engram_category = "danger" if raw_category == "pitfall" else "architecture"

        # Derive stable key
        key = payload.get("key") or _derive_engram_key(result)
        source_id = str(getattr(result, "id", None) or "")

        engram = get_engram_cache()
        is_new = engram.put(
            key=key,
            value=lesson_text,
            category=engram_category,
            source_learning_id=source_id or None,
            match_count=match_count,
        )
        if is_new:
            logger.info(
                f"[Learnings] ENGRAM L1 promoted (new): key={key!r} "
                f"category={engram_category} match_count={match_count}"
            )
        else:
            logger.debug(
                f"[Learnings] ENGRAM L1 updated: key={key!r} match_count={match_count}"
            )
    except Exception as e:
        logger.warning(f"[Learnings] ENGRAM L1 promotion failed: {e}")


class ResourceLearningStore:
    """Stores and retrieves pipeline lessons in Qdrant.

    Each learning is a short text (1-3 sentences) with metadata:
    - run_id, task_id, session_id: provenance
    - category: "pattern" | "pitfall" | "optimization" | "architecture"
    - files: list of affected files
    - timestamp
    """

    def __init__(self):
        self._qdrant = None
        self._embedding = None
        self._initialized = False

    def _ensure_init(self) -> bool:
        """Lazy init Qdrant client + embedding service."""
        if self._initialized:
            return self._qdrant is not None

        self._initialized = True
        try:
            from src.memory.qdrant_client import get_qdrant_client
            self._qdrant = get_qdrant_client()
            if not self._qdrant or not self._qdrant.health_check():
                logger.warning("[Learnings] Qdrant not available, using fallback")
                self._qdrant = None
                return False

            # Ensure collection exists
            try:
                from qdrant_client.models import Distance, VectorParams
                self._qdrant.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
                logger.info(f"[Learnings] Created collection {COLLECTION_NAME}")
            except Exception:
                pass  # Already exists

            from src.utils.embedding_service import get_embedding_service
            self._embedding = get_embedding_service()
            return True

        except Exception as e:
            logger.warning(f"[Learnings] Init failed: {e}")
            self._qdrant = None
            return False

    def store_learning_sync(
        self,
        text: str,
        category: str = "pattern",
        run_id: Optional[str] = None,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        files: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """MARKER_198.P1.7: Synchronous store — for use from sync code paths (MCP complete).

        Uses sync get_embedding() instead of async. Same Qdrant upsert + fallback logic.
        """
        point_id = str(uuid.uuid4())

        payload = {
            "text": text,
            "category": category,
            "run_id": run_id,
            "task_id": task_id,
            "session_id": session_id,
            "files": files or [],
            "timestamp": time.time(),
            "timestamp_iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            **(metadata or {}),
        }

        if not self._ensure_init():
            return self._store_fallback(point_id, payload)

        try:
            from src.utils.embedding_service import get_embedding
            vector = get_embedding(text)
            if not vector:
                logger.warning("[Learnings] Empty embedding (sync), using fallback")
                return self._store_fallback(point_id, payload)

            from qdrant_client.models import PointStruct
            self._qdrant.client.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )],
            )
            logger.info(f"[Learnings] Stored (sync): {text[:60]}... (id={point_id})")
            return point_id

        except Exception as e:
            logger.warning(f"[Learnings] Qdrant store failed (sync): {e}")
            return self._store_fallback(point_id, payload)

    async def store_learning(
        self,
        text: str,
        category: str = "pattern",
        run_id: Optional[str] = None,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        files: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store a single learning in Qdrant.

        Args:
            text: The lesson learned (1-3 sentences)
            category: "pattern" | "pitfall" | "optimization" | "architecture"
            run_id: Pipeline run ID
            task_id: TaskBoard task ID
            session_id: Heartbeat session ID
            files: List of affected file paths
            metadata: Additional metadata

        Returns:
            Point ID if stored, None if failed
        """
        point_id = str(uuid.uuid4())

        payload = {
            "text": text,
            "category": category,
            "run_id": run_id,
            "task_id": task_id,
            "session_id": session_id,
            "files": files or [],
            "timestamp": time.time(),
            "timestamp_iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            **(metadata or {}),
        }

        if not self._ensure_init():
            # Fallback to local JSON
            return self._store_fallback(point_id, payload)

        try:
            from src.utils.embedding_service import get_embedding_async
            vector = await get_embedding_async(text)
            if not vector:
                logger.warning("[Learnings] Empty embedding, using fallback")
                return self._store_fallback(point_id, payload)

            from qdrant_client.models import PointStruct
            self._qdrant.client.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )],
            )
            logger.info(f"[Learnings] Stored: {text[:60]}... (id={point_id})")
            return point_id

        except Exception as e:
            logger.warning(f"[Learnings] Qdrant store failed: {e}")
            return self._store_fallback(point_id, payload)

    async def search_learnings(
        self,
        query: str,
        limit: int = 5,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic search for relevant learnings.

        Args:
            query: Task description or search query
            limit: Max results to return
            category: Optional filter by category

        Returns:
            List of {text, category, score, run_id, task_id, files, timestamp}
        """
        if not self._ensure_init():
            return self._search_fallback(query, limit)

        try:
            from src.utils.embedding_service import get_embedding_async
            vector = await get_embedding_async(query)
            if not vector:
                return self._search_fallback(query, limit)

            query_filter = None
            if category:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                query_filter = Filter(must=[
                    FieldCondition(key="category", match=MatchValue(value=category))
                ])

            results = self._qdrant.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=vector,
                limit=limit,
                query_filter=query_filter,
            )

            return [
                {
                    "text": r.payload.get("text", ""),
                    "category": r.payload.get("category", ""),
                    "score": round(r.score, 3),
                    "run_id": r.payload.get("run_id"),
                    "task_id": r.payload.get("task_id"),
                    "files": r.payload.get("files", []),
                    "timestamp": r.payload.get("timestamp_iso", ""),
                }
                for r in results
                if r.score > 0.3  # minimum relevance threshold
            ]

        except Exception as e:
            logger.warning(f"[Learnings] Search failed: {e}")
            return self._search_fallback(query, limit)

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        if not self._ensure_init():
            return {"source": "fallback", "count": len(self._read_fallback())}

        try:
            info = self._qdrant.client.get_collection(COLLECTION_NAME)
            return {
                "source": "qdrant",
                "collection": COLLECTION_NAME,
                "count": info.points_count,
                "vector_size": VECTOR_SIZE,
            }
        except Exception:
            return {"source": "fallback", "count": len(self._read_fallback())}

    # ── Fallback: local JSON ─────────────────────────────────────────

    def _store_fallback(self, point_id: str, payload: Dict) -> str:
        """Store learning in local JSON file when Qdrant is unavailable."""
        entries = self._read_fallback()
        entries.append({"id": point_id, **payload})
        # Keep last 500 entries
        entries = entries[-500:]
        try:
            _FALLBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
            _FALLBACK_FILE.write_text(json.dumps(entries, indent=2, default=str))
        except Exception as e:
            logger.error(f"[Learnings] Fallback store failed: {e}")
        return point_id

    def _read_fallback(self) -> List[Dict]:
        """Read learnings from fallback JSON."""
        try:
            if _FALLBACK_FILE.exists():
                return json.loads(_FALLBACK_FILE.read_text())
        except Exception:
            pass
        return []

    def _search_fallback(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Simple keyword search on fallback JSON (no embeddings)."""
        entries = self._read_fallback()
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for entry in entries:
            text = entry.get("text", "").lower()
            # Simple word overlap score
            text_words = set(text.split())
            overlap = len(query_words & text_words)
            if overlap > 0:
                score = overlap / max(len(query_words), 1)
                scored.append({
                    "text": entry.get("text", ""),
                    "category": entry.get("category", ""),
                    "score": round(score, 3),
                    "run_id": entry.get("run_id"),
                    "task_id": entry.get("task_id"),
                    "files": entry.get("files", []),
                    "timestamp": entry.get("timestamp_iso", ""),
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]


# ── Convenience functions ───────────────────────────────────────────

_store_instance: Optional[ResourceLearningStore] = None


def get_learning_store() -> ResourceLearningStore:
    """Get singleton instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = ResourceLearningStore()
    return _store_instance


async def extract_and_store_learnings(
    run_id: str,
    task_id: str,
    session_id: Optional[str] = None,
    verifier_results: Optional[List[Dict]] = None,
    files_committed: Optional[List[str]] = None,
    task_title: str = "",
    task_description: str = "",
) -> List[str]:
    """Extract lessons from a completed pipeline run and store in Qdrant.

    Called after verify_and_merge() succeeds.

    Synthesizes 1-3 learnings from:
    - Verifier feedback (issues found, retries needed)
    - Files modified (patterns about which files change together)
    - Task metadata (what worked, what didn't)

    Returns:
        List of stored point IDs
    """
    store = get_learning_store()
    stored_ids = []

    # Learning 1: Files that change together (co-change pattern)
    if files_committed and len(files_committed) >= 2:
        # Extract file extensions/directories for pattern
        dirs = set()
        for f in files_committed[:10]:
            parts = Path(f).parts
            if len(parts) >= 2:
                dirs.add(parts[-2] if parts[-2] != "src" else "/".join(parts[-3:-1]))

        if dirs:
            text = (
                f"Files that change together for '{task_title[:50]}': "
                f"{', '.join(f[:60] for f in files_committed[:5])}. "
                f"Directories involved: {', '.join(dirs)}."
            )
            pid = await store.store_learning(
                text=text,
                category="pattern",
                run_id=run_id,
                task_id=task_id,
                session_id=session_id,
                files=files_committed[:10],
            )
            if pid:
                stored_ids.append(pid)

    # Learning 2: Verifier issues (pitfalls to avoid)
    if verifier_results:
        issues = []
        retries = 0
        for vr in verifier_results:
            if isinstance(vr, dict):
                issues.extend(vr.get("issues", []))
                if vr.get("retry_count", 0) > 0:
                    retries += vr["retry_count"]

        if issues:
            unique_issues = list(set(str(i)[:80] for i in issues[:5]))
            text = (
                f"Pitfalls for '{task_title[:40]}': "
                f"{'; '.join(unique_issues)}. "
                f"Required {retries} retries to resolve."
            )
            pid = await store.store_learning(
                text=text,
                category="pitfall",
                run_id=run_id,
                task_id=task_id,
                session_id=session_id,
                files=files_committed[:5] if files_committed else [],
                metadata={"retry_count": retries},
            )
            if pid:
                stored_ids.append(pid)

    # Learning 3: Task completion pattern (what kind of task, how it was solved)
    if task_title and files_committed:
        text = (
            f"Task '{task_title[:60]}' completed successfully, "
            f"modifying {len(files_committed)} files. "
            f"Approach: {task_description[:100] if task_description else 'standard pipeline'}."
        )
        pid = await store.store_learning(
            text=text,
            category="optimization",
            run_id=run_id,
            task_id=task_id,
            session_id=session_id,
            files=files_committed[:5],
        )
        if pid:
            stored_ids.append(pid)

    logger.info(f"[Learnings] Extracted {len(stored_ids)} learnings for run {run_id}")
    return stored_ids


async def get_learnings_for_architect(task_description: str, limit: int = 3) -> str:
    """Search past learnings and format for architect injection.

    MARKER_198.P0.4: After fetching results from Qdrant / fallback, increments
    per-learning match counts (persisted in data/reflex/learning_match_counts.json).
    When a learning's match_count reaches _PROMOTION_THRESHOLD (3), it is
    auto-promoted to ENGRAM L1 via _promote_to_engram_l1().

    Returns formatted string for architect user_content, or empty string.
    """
    store = get_learning_store()

    # MARKER_198.P0.4: Fetch raw Qdrant results when possible so we can use
    # the original result objects for key derivation and promotion.
    # Fall back to search_learnings() dicts when Qdrant is unavailable.
    raw_results = None
    if store._ensure_init() and store._qdrant is not None:
        try:
            from src.utils.embedding_service import get_embedding_async
            vector = await get_embedding_async(task_description)
            if vector:
                raw_results = store._qdrant.client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=vector,
                    limit=limit,
                )
                raw_results = [r for r in raw_results if r.score > 0.3]
        except Exception as e:
            logger.warning(f"[Learnings] Raw search for promotion tracking failed: {e}")
            raw_results = None

    # Fallback: use dict-based search (no Qdrant objects available)
    if raw_results is None:
        results = await store.search_learnings(task_description, limit=limit)
        if not results:
            return ""
        lines = ["[Past Learnings]"]
        for r in results:
            lines.append(f"- [{r['category']}] {r['text'][:120]} (score: {r['score']})")
        return "\n".join(lines)

    if not raw_results:
        return ""

    # MARKER_198.P0.4: Track match counts and auto-promote at threshold
    counts = _load_match_counts()
    promoted_keys: List[str] = []

    for result in raw_results:
        payload = result.payload if hasattr(result, "payload") else {}
        # Use explicit key field when present, else derive a stable key
        learning_key = payload.get("key") or _derive_engram_key(result)

        counts[learning_key] = counts.get(learning_key, 0) + 1

        if counts[learning_key] >= _PROMOTION_THRESHOLD:
            _promote_to_engram_l1(result, counts[learning_key])
            promoted_keys.append(learning_key)

    _save_match_counts(counts)

    if promoted_keys:
        logger.info(
            f"[Learnings] {len(promoted_keys)} learning(s) promoted to ENGRAM L1: "
            f"{promoted_keys}"
        )

    # Format output for architect injection
    lines = ["[Past Learnings]"]
    for result in raw_results:
        payload = result.payload if hasattr(result, "payload") else {}
        category = payload.get("category", "")
        text = payload.get("text", "")
        score = round(result.score, 3)
        lines.append(f"- [{category}] {text[:120]} (score: {score})")

    return "\n".join(lines)
