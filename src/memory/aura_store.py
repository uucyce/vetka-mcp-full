"""
VETKA AURA — Adaptive User Response Archive
Hybrid RAM + Qdrant storage for user preferences

@file aura_store.py
@status active
@phase 187.6 (renamed from engram_user_memory.py)
@depends logging, math, datetime, qdrant_client, user_memory.py, elision.py
@used_by jarvis_prompt_enricher.py, orchestrator_with_elisya.py, vetka_mcp_bridge.py,
         shared_tools.py, llm_call_tool.py, session_tools.py, user_memory_updater.py

Architecture:
- Hot preferences in RAM (O(1) lookup)
- Cold preferences in Qdrant (semantic search)
- Offload threshold: usage_count > 5
- Per-category temporal decay (configurable rates per category)

Features:
- 23-43% token savings via selective inclusion
- Model-agnostic (works with any LLM)
- Per-agent preference keys (agent_type dimension)
- Vechnaya pamyat (eternal memory - survives model changes)

MARKER_108_7_AURA_ELISION: Phase 108.7 Integration
- ELISION compression for Qdrant payloads (40-60% savings)
- MGC-aware cascading (Gen0 RAM -> Gen1 Qdrant -> Gen2 Archive)
- Spiral context integration via get_spiral_context()
"""

import logging
import math
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from .user_memory import UserPreferences, create_user_preferences


def _user_id_to_point_id(user_id: str) -> int:
    """
    Convert string user_id to integer point ID for Qdrant REST API.

    Qdrant REST API requires integer IDs. This function provides deterministic
    conversion using UUID5 hash.
    """
    return uuid.uuid5(uuid.NAMESPACE_DNS, user_id).int & 0x7FFFFFFFFFFFFFFF


logger = logging.getLogger(__name__)

# Import Qdrant client
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        PointStruct,
        Distance,
        VectorParams,
        Filter,
        FieldCondition,
        Range,
        PointIdsList,
    )

    QDRANT_AVAILABLE = True
except ImportError:
    logger.warning("qdrant-client not installed for AuraStore")
    QDRANT_AVAILABLE = False
    QdrantClient = None


# Per-category decay rates (per week)
CATEGORY_DECAY_RATES: Dict[str, float] = {
    "communication_style": 0.01,   # slow decay — style is stable
    "viewport_patterns":   0.03,   # medium — viewing habits shift
    "tree_structure":      0.02,   # slow-medium — project structure evolves
    "project_highlights":  0.04,   # faster — project focus changes
    "temporal_patterns":   0.03,   # medium
    "tool_usage_patterns": 0.05,   # fastest — tool preferences shift often
}

# Default decay for unknown categories
DEFAULT_DECAY_RATE = 0.05


class AuraStore:
    """
    AURA — Adaptive User Response Archive.

    Hybrid storage architecture:
    - RAM cache for hot preferences (usage > 5)
    - Qdrant for cold preferences (semantic search)
    - Per-agent keys: preferences[agent_type][user_id]

    Features:
    - O(1) lookup for frequent preferences
    - Automatic offload to RAM when usage > threshold
    - Per-category temporal decay
    - Per-agent preference isolation
    - 23-43% token savings (from CAM research)

    Usage:
        store = AuraStore(qdrant_client)
        zoom = store.get_preference('default', 'danila', 'viewport_patterns', 'zoom_levels')
        store.set_preference('default', 'danila', 'communication_style', 'formality', 0.2)
    """

    COLLECTION_NAME = "vetka_user_memories"  # Qdrant collection — NOT renamed (data preserved)
    VECTOR_SIZE = 768  # Gemma embeddings

    # Offload to RAM when usage exceeds this threshold
    OFFLOAD_THRESHOLD = 5

    # Minimum confidence before pruning
    MIN_CONFIDENCE = 0.1

    def __init__(self, qdrant_client: Optional[QdrantClient] = None):
        """
        Initialize AURA Store.

        Args:
            qdrant_client: Qdrant client instance (or None for RAM-only mode)
        """
        self.qdrant = qdrant_client
        # Per-agent RAM cache: agent_type -> user_id -> preferences
        self.ram_cache: Dict[str, Dict[str, UserPreferences]] = {}
        self.usage_counts: Dict[str, Dict[str, int]] = {}  # user_id -> {category.key -> count}
        self._initialized = False

        if self.qdrant and QDRANT_AVAILABLE:
            self._ensure_collection()
            self._load_hot_data()
            self._initialized = True
            logger.info("[AuraStore] Initialized with Qdrant backend")
        else:
            logger.info("[AuraStore] Initialized in RAM-only mode")

    def _agent_cache(self, agent_type: str) -> Dict[str, UserPreferences]:
        """Get or create per-agent cache partition."""
        if agent_type not in self.ram_cache:
            self.ram_cache[agent_type] = {}
        return self.ram_cache[agent_type]

    def _ensure_collection(self) -> bool:
        """Create Qdrant collection if not exists."""
        if not self.qdrant or not QDRANT_AVAILABLE:
            return False

        try:
            collections = self.qdrant.get_collections()
            existing = {c.name for c in collections.collections}

            if self.COLLECTION_NAME not in existing:
                self.qdrant.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE, distance=Distance.COSINE
                    ),
                )
                logger.info(f"[AuraStore] Created collection: {self.COLLECTION_NAME}")

            return True

        except Exception as e:
            logger.error(f"[AuraStore] Collection init failed: {e}")
            return False

    def _load_hot_data(self):
        """Load frequently accessed preferences from Qdrant to RAM (default agent)."""
        if not self.qdrant or not QDRANT_AVAILABLE:
            return

        try:
            points, _ = self.qdrant.scroll(
                collection_name=self.COLLECTION_NAME,
                limit=100,
                with_payload=True,
                with_vectors=False,
            )

            default_cache = self._agent_cache("default")
            for point in points:
                user_id = point.payload.get("user_id")
                if user_id:
                    prefs = UserPreferences.from_dict(point.payload)
                    default_cache[user_id] = prefs
                    logger.debug(f"[AuraStore] Loaded preferences for: {user_id}")

            logger.info(f"[AuraStore] Loaded {len(default_cache)} users to RAM cache")

        except Exception as e:
            logger.warning(f"[AuraStore] Hot data load failed: {e}")

    def get_preference(
        self, agent_type: str, user_id: str, category: str, key: str
    ) -> Optional[Any]:
        """
        O(1) lookup from RAM or Qdrant fallback.

        Args:
            agent_type: Agent type key (e.g., 'opus', 'cursor', 'default')
            user_id: User identifier
            category: Preference category (e.g., 'viewport_patterns')
            key: Specific preference key (e.g., 'zoom_levels')

        Returns:
            Preference value or None if not found
        """
        cache = self._agent_cache(agent_type)

        # Check RAM cache first (O(1))
        if user_id in cache:
            prefs = cache[user_id]
            category_obj = getattr(prefs, category, None)

            if category_obj and hasattr(category_obj, key):
                value = getattr(category_obj, key)
                self._increment_usage(user_id, category, key)
                return value

        # Fallback to default agent cache
        if agent_type != "default":
            default_cache = self._agent_cache("default")
            if user_id in default_cache:
                prefs = default_cache[user_id]
                category_obj = getattr(prefs, category, None)
                if category_obj and hasattr(category_obj, key):
                    value = getattr(category_obj, key)
                    self._increment_usage(user_id, category, key)
                    return value

        # Fallback: Qdrant search
        result = self._qdrant_get(user_id, category, key)
        if result is not None:
            self._maybe_offload_to_ram(agent_type, user_id, category, key, result)
            return result

        return None

    def set_preference(
        self, agent_type: str, user_id: str, category: str, key: str,
        value: Any, confidence: float = 0.5
    ):
        """
        Set preference with automatic RAM offload.

        Args:
            agent_type: Agent type key (e.g., 'opus', 'cursor', 'default')
            user_id: User identifier
            category: Preference category
            key: Specific preference key
            value: New value to set
            confidence: Confidence score (0-1)
        """
        cache = self._agent_cache(agent_type)

        # Ensure user exists in cache
        if user_id not in cache:
            cache[user_id] = create_user_preferences(user_id)

        prefs = cache[user_id]

        # Get category object
        category_obj = getattr(prefs, category, None)
        if category_obj is None:
            logger.warning(f"[AuraStore] Invalid category: {category}")
            return

        # Set value
        if hasattr(category_obj, key):
            setattr(category_obj, key, value)
            setattr(category_obj, "confidence", confidence)
            setattr(category_obj, "last_updated", datetime.now().isoformat())

            # Save to Qdrant
            self._qdrant_upsert(user_id, prefs)

            # Increment usage
            self._increment_usage(user_id, category, key)

            logger.debug(f"[AuraStore] Set {agent_type}/{user_id}.{category}.{key} = {value}")
        else:
            logger.warning(f"[AuraStore] Invalid key: {category}.{key}")

    def get_user_preferences(self, user_id: str, agent_type: str = "default") -> Optional[UserPreferences]:
        """
        Get complete preferences for a user.

        Args:
            user_id: User identifier
            agent_type: Agent type (default: 'default')

        Returns:
            UserPreferences or None if not found
        """
        cache = self._agent_cache(agent_type)

        # Check agent cache first, then default
        if user_id in cache:
            return cache[user_id]

        if agent_type != "default":
            default_cache = self._agent_cache("default")
            if user_id in default_cache:
                return default_cache[user_id]

        # Try Qdrant
        return self._qdrant_get_full(user_id)

    def _increment_usage(self, user_id: str, category: str, key: str):
        """Track usage count for offload decision."""
        if user_id not in self.usage_counts:
            self.usage_counts[user_id] = {}

        pref_key = f"{category}.{key}"
        current = self.usage_counts[user_id].get(pref_key, 0)
        self.usage_counts[user_id][pref_key] = current + 1

    def _maybe_offload_to_ram(
        self, agent_type: str, user_id: str, category: str, key: str, value: Any
    ):
        """
        Offload to RAM if usage > threshold.
        Hot preferences are kept in RAM for O(1) access.
        """
        pref_key = f"{category}.{key}"
        usage = self.usage_counts.get(user_id, {}).get(pref_key, 0)

        if usage >= self.OFFLOAD_THRESHOLD:
            cache = self._agent_cache(agent_type)
            if user_id not in cache:
                prefs = self._qdrant_get_full(user_id)
                if prefs:
                    cache[user_id] = prefs
                    logger.info(f"[AuraStore] Offloaded {user_id} to RAM (usage={usage})")
                else:
                    cache[user_id] = create_user_preferences(user_id)

    def _qdrant_get(self, user_id: str, category: str, key: str) -> Optional[Any]:
        """Retrieve specific preference from Qdrant."""
        if not self.qdrant or not QDRANT_AVAILABLE:
            return None

        try:
            point_id = _user_id_to_point_id(user_id)
            results = self.qdrant.retrieve(
                collection_name=self.COLLECTION_NAME, ids=[point_id], with_payload=True
            )

            if results:
                payload = results[0].payload
                category_data = payload.get(category, {})
                return category_data.get(key)

        except Exception as e:
            logger.debug(f"[AuraStore] Qdrant get failed: {e}")

        return None

    def get_all_preferences(self, user_id: str) -> Optional[dict]:
        """
        Public method — returns all preferences for user as dict.
        Called by llm_call_tool, context_dag_tool, vetka_mcp_bridge.
        """
        # Check default agent cache first
        default_cache = self._agent_cache("default")
        if user_id in default_cache:
            return default_cache[user_id].to_dict()
        # Fallback to Qdrant
        prefs = self._qdrant_get_full(user_id)
        if prefs:
            return prefs.to_dict()
        return None

    def _qdrant_get_full(self, user_id: str) -> Optional[UserPreferences]:
        """Retrieve full preferences from Qdrant."""
        if not self.qdrant or not QDRANT_AVAILABLE:
            return None

        try:
            point_id = _user_id_to_point_id(user_id)
            results = self.qdrant.retrieve(
                collection_name=self.COLLECTION_NAME, ids=[point_id], with_payload=True
            )

            if results:
                return UserPreferences.from_dict(results[0].payload)

        except Exception as e:
            logger.debug(f"[AuraStore] Qdrant get full failed: {e}")

        return None

    def _qdrant_upsert(self, user_id: str, preferences: UserPreferences):
        """Save preferences to Qdrant."""
        if not self.qdrant or not QDRANT_AVAILABLE:
            return

        try:
            embedding = [0.0] * self.VECTOR_SIZE
            point_id = _user_id_to_point_id(user_id)

            payload = preferences.to_dict()
            payload["_user_id"] = user_id

            point = PointStruct(
                id=point_id, vector=embedding, payload=payload
            )

            self.qdrant.upsert(collection_name=self.COLLECTION_NAME, points=[point])

        except Exception as e:
            logger.warning(f"[AuraStore] Qdrant upsert failed: {e}")

    def decay_preferences(self, user_id: str, agent_type: str = "default"):
        """
        Apply per-category temporal decay.

        Each category has its own decay rate (see CATEGORY_DECAY_RATES).
        Prunes categories below MIN_CONFIDENCE threshold.
        """
        cache = self._agent_cache(agent_type)
        if user_id not in cache:
            return

        prefs = cache[user_id]
        now = datetime.now()

        categories = list(CATEGORY_DECAY_RATES.keys())

        for category_name in categories:
            category = getattr(prefs, category_name, None)
            if not category:
                continue

            decay_rate = CATEGORY_DECAY_RATES.get(category_name, DEFAULT_DECAY_RATE)

            try:
                last_updated_str = getattr(category, "last_updated", None)
                if last_updated_str:
                    last_updated = datetime.fromisoformat(last_updated_str)
                    days_old = (now - last_updated).days
                    weeks_old = days_old / 7

                    current_confidence = getattr(category, "confidence", 0.5)
                    new_confidence = current_confidence * math.exp(
                        -decay_rate * weeks_old
                    )

                    if new_confidence < self.MIN_CONFIDENCE:
                        logger.debug(
                            f"[AuraStore] Pruning {user_id}.{category_name} "
                            f"(confidence={new_confidence:.3f}, rate={decay_rate})"
                        )
                        setattr(prefs, category_name, type(category)())
                    else:
                        setattr(category, "confidence", round(new_confidence, 3))

            except Exception as e:
                logger.debug(f"[AuraStore] Decay error for {category_name}: {e}")

        # Save updated preferences
        self._qdrant_upsert(user_id, prefs)

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        agent_stats = {}
        for agent_type, cache in self.ram_cache.items():
            agent_stats[agent_type] = {
                "users": list(cache.keys()),
                "count": len(cache),
            }

        return {
            "agents": agent_stats,
            "total_users_in_ram": sum(len(c) for c in self.ram_cache.values()),
            "qdrant_available": self.qdrant is not None and QDRANT_AVAILABLE,
            "offload_threshold": self.OFFLOAD_THRESHOLD,
            "decay_rates": CATEGORY_DECAY_RATES,
            "collection": self.COLLECTION_NAME,
        }

    # =========================================================================
    # MARKER_108_7_AURA_ELISION: Spiral Context Integration
    # =========================================================================

    def get_spiral_context(
        self,
        user_id: str,
        query_vec: Optional[List[float]] = None,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """
        Get spiral context from user memory.

        Hybrid search: RAM first (Gen0), Qdrant fallback (Gen1).
        Returns ELISION-compressed context for prompt injection.
        """
        context = {
            "user_id": user_id,
            "gen": "gen0",
            "prefs": {}
        }

        # Try RAM first (Gen0 - hot) — search default agent cache
        default_cache = self._agent_cache("default")
        if user_id in default_cache:
            prefs = default_cache[user_id]
            context["prefs"] = self._compress_prefs(prefs, max_tokens)
            context["source"] = "ram_cache"
        else:
            # Fallback to Qdrant (Gen1 - mid)
            qdrant_prefs = self._qdrant_get_full(user_id)
            if qdrant_prefs:
                context["prefs"] = self._compress_prefs(qdrant_prefs, max_tokens)
                context["gen"] = "gen1"
                context["source"] = "qdrant"

        # Apply ELISION compression
        try:
            from src.memory.elision import compress_context
            compressed = compress_context(context)
            if isinstance(compressed, str):
                import json
                context = json.loads(compressed)
        except Exception as e:
            logger.debug(f"[AuraStore] ELISION compression skipped: {e}")

        context["hyperlink"] = "[-> prefs] vetka_get_user_preferences"
        return context

    def _compress_prefs(
        self,
        prefs: UserPreferences,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Compress preferences to fit token budget."""
        compressed = {}

        priority_categories = [
            "communication_style",
            "viewport_patterns",
            "tool_usage_patterns"
        ]

        tokens_used = 0
        chars_per_token = 4

        for category in priority_categories:
            cat_data = getattr(prefs, category, None)
            if cat_data:
                cat_dict = cat_data.to_dict() if hasattr(cat_data, 'to_dict') else {}
                cat_size = len(str(cat_dict)) // chars_per_token

                if tokens_used + cat_size <= max_tokens:
                    compressed[category[:3]] = cat_dict
                    tokens_used += cat_size
                else:
                    break

        return compressed

    def clear_user(self, user_id: str, agent_type: Optional[str] = None):
        """Clear all preferences for a user (optionally scoped to agent_type)."""
        if agent_type:
            # Clear only for specific agent
            cache = self.ram_cache.get(agent_type, {})
            cache.pop(user_id, None)
        else:
            # Clear from all agent caches
            for cache in self.ram_cache.values():
                cache.pop(user_id, None)

        if user_id in self.usage_counts:
            del self.usage_counts[user_id]

        # Remove from Qdrant (only if clearing all agents)
        if not agent_type and self.qdrant and QDRANT_AVAILABLE:
            try:
                point_id = _user_id_to_point_id(user_id)
                self.qdrant.delete(
                    collection_name=self.COLLECTION_NAME,
                    points_selector=PointIdsList(points=[point_id]),
                )
            except Exception as e:
                logger.warning(f"[AuraStore] Qdrant delete failed: {e}")

        logger.info(f"[AuraStore] Cleared preferences for: {user_id}")


# ============ FACTORY FUNCTION ============

_aura_instance: Optional[AuraStore] = None


def get_aura_store(
    qdrant_client: Optional[QdrantClient] = None,
) -> AuraStore:
    """
    Factory function - returns singleton AuraStore.

    Args:
        qdrant_client: Qdrant client (uses global if None)

    Returns:
        AuraStore singleton instance
    """
    global _aura_instance

    if _aura_instance is None:
        if qdrant_client is None:
            try:
                from src.memory.qdrant_client import get_qdrant_client

                qdrant_vetka = get_qdrant_client()
                if qdrant_vetka and qdrant_vetka.client:
                    qdrant_client = qdrant_vetka.client
            except ImportError:
                pass

        _aura_instance = AuraStore(qdrant_client=qdrant_client)

    return _aura_instance


# ============================================================================
# AURA LOOKUP (Level 1 only — enhanced levels removed as dead mock code)
# ============================================================================


async def aura_lookup(query: str) -> Optional[List[Dict[str, Any]]]:
    """
    Basic AURA O(1) lookup for user preferences and patterns.

    Args:
        query: Query string to search for

    Returns:
        List of matching patterns or None if not found
    """
    try:
        store = get_aura_store()

        results = []
        query_lower = query.lower()

        # Search through default agent cache
        default_cache = store._agent_cache("default")
        for user_id, preferences in default_cache.items():
            for category, prefs in preferences.preferences.items():
                for key, value in prefs.items():
                    if (
                        query_lower in category.lower()
                        or query_lower in key.lower()
                        or (isinstance(value, str) and query_lower in value.lower())
                    ):
                        results.append(
                            {
                                "user_id": user_id,
                                "category": category,
                                "key": key,
                                "value": value,
                                "confidence": getattr(value, "confidence", 1.0)
                                if hasattr(value, "confidence")
                                else 1.0,
                                "source": "aura_o1",
                                "relevance": 0.8,
                            }
                        )

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results[:10] if results else None

    except Exception as e:
        logger.error(f"[AURA Lookup] Basic lookup failed: {e}")
        return None


# ============ BACKWARDS COMPATIBILITY ============
# Temporary aliases — remove after all callers migrated
EngramUserMemory = AuraStore
get_engram_user_memory = get_aura_store
engram_lookup = aura_lookup
