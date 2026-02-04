"""
VETKA Message Utilities - Pure Functions

@file message_utils.py
@status ACTIVE
@phase Phase 73.6 - JSON Context Builder with ELISION Compression + Legend
@extracted_from user_message_handler.py
@lastAudit 2026-01-20

@calledBy:
  - src.api.handlers.user_message_handler (format_history_for_prompt, build_pinned_context)
  - src.api.handlers.__init__ (re-export)

Pure utility functions for message handling:
- Chat history formatting
- Pinned file context building (with Qdrant semantic search + CAM activation)
- JSON context building for AI agents (Phase 73)
- Message parsing

Phase 67: Added smart context assembly using:
- Qdrant vector search for semantic relevance
- CAM activation scores for importance weighting
- Token-based truncation (not char-based)
- Fallback to legacy logic if services unavailable

Phase 67.2: Performance optimizations:
- Singleton CAM Engine (no new instance per call)
- Batch Qdrant queries (1 query instead of N)
- LRU cache for relevance scores
- Configurable weights via env variables
- Optional debug mode

Phase 73.0: JSON Context Builder
- build_json_context() for structured AI agent context
- Semantic neighbors from Qdrant
- Dependency scoring via DependencyCalculator
- Viewport summary extraction

Phase 73.5: ELISION Compression + Cache (Etymology: ELYSIUM + ELISION = "Elisya")
- Path compression: '/src/orchestration/cam_engine.py' → 's/o/cam_engine.py'
- Key abbreviation: 'current_file' → 'cf', 'dependencies' → 'd'
- Minified JSON output when compressed=True
- LRU cache for JSON context (configurable size)
- PythonScanner integration for import_confidence
- imported_by reverse index

Phase 73.6: Legend Header (_l)
- Optional _legend header with key mappings for cold start/debug
- Auto-detection of cold start (first message of session)
- Configurable via VETKA_JSON_CONTEXT_LEGEND_MODE (auto|always|never)
"""

import os
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Set

logger = logging.getLogger("VETKA_CONTEXT")

# ═══════════════════════════════════════════════════════════════════
# Phase 67.2: Configurable weights via environment variables
# ═══════════════════════════════════════════════════════════════════

# MARKER_109_7_UNIFIED_WEIGHTING: Extended weights for multi-source scoring
# Phase 67 original: qdrant=0.7, cam=0.3
# Phase 109.7: Add engram, viewport, hope, mgc (Grok research)
QDRANT_WEIGHT = float(os.getenv("VETKA_QDRANT_WEIGHT", "0.40"))
CAM_WEIGHT = float(os.getenv("VETKA_CAM_WEIGHT", "0.20"))
ENGRAM_WEIGHT = float(os.getenv("VETKA_ENGRAM_WEIGHT", "0.15"))
VIEWPORT_WEIGHT = float(os.getenv("VETKA_VIEWPORT_WEIGHT", "0.15"))
HOPE_WEIGHT = float(os.getenv("VETKA_HOPE_WEIGHT", "0.05"))
MGC_WEIGHT = float(os.getenv("VETKA_MGC_WEIGHT", "0.05"))

# Dynamic context budget per model family
MODEL_CONTEXT_BUDGETS = {
    'gpt-4': 8000, 'gpt-4o': 8000,
    'claude': 8000, 'sonnet': 8000, 'opus': 8000,
    'grok': 4000,
    'glm': 4000,
    'qwen': 2000,
    'llama': 2000,
    'haiku': 4000,
    'gemini': 8000,
    'default': 4000
}

def get_context_budget_for_model(model_name: str) -> int:
    """Get token budget based on model family."""
    model_lower = model_name.lower() if model_name else ""
    for key, budget in MODEL_CONTEXT_BUDGETS.items():
        if key in model_lower:
            return budget
    return MODEL_CONTEXT_BUDGETS['default']

MAX_CONTEXT_TOKENS = int(os.getenv("VETKA_MAX_CONTEXT_TOKENS", "4000"))
MAX_TOKENS_PER_FILE = int(os.getenv("VETKA_MAX_TOKENS_PER_FILE", "1000"))
VETKA_DEBUG_CONTEXT = os.getenv("VETKA_DEBUG_CONTEXT", "false").lower() == "true"
# Phase 69: Configurable max pinned files limit
VETKA_MAX_PINNED_FILES = int(os.getenv("VETKA_MAX_PINNED_FILES", "10"))
# Artifact Panel: Unlimited tokens for full file display
ARTIFACT_MAX_TOKENS_PER_FILE = int(
    os.getenv("VETKA_ARTIFACT_MAX_TOKENS_PER_FILE", "999999")
)

# ═══════════════════════════════════════════════════════════════════
# [PHASE73-1] Phase 73: JSON Context Builder Configuration
# ═══════════════════════════════════════════════════════════════════
VETKA_JSON_CONTEXT_MAX_TOKENS = int(
    os.getenv("VETKA_JSON_CONTEXT_MAX_TOKENS", "2000")
)
VETKA_JSON_CONTEXT_INCLUDE_DEPS = (
    os.getenv("VETKA_JSON_CONTEXT_INCLUDE_DEPS", "true").lower() == "true"
)
VETKA_JSON_CONTEXT_INCLUDE_SEMANTIC = (
    os.getenv("VETKA_JSON_CONTEXT_INCLUDE_SEMANTIC", "true").lower() == "true"
)
VETKA_JSON_CONTEXT_DEBUG = (
    os.getenv("VETKA_JSON_CONTEXT_DEBUG", "false").lower() == "true"
)

# [PHASE73.5-1] Phase 73.5: ELISION Compression + Cache Configuration
VETKA_JSON_CONTEXT_COMPRESSED = (
    os.getenv("VETKA_JSON_CONTEXT_COMPRESSED", "true").lower() == "true"
)
VETKA_JSON_CONTEXT_CACHE_SIZE = int(os.getenv("VETKA_JSON_CONTEXT_CACHE_SIZE", "100"))
VETKA_JSON_CONTEXT_INCLUDE_IMPORTS = (
    os.getenv("VETKA_JSON_CONTEXT_INCLUDE_IMPORTS", "true").lower() == "true"
)

# [PHASE73.6-1] Phase 73.6: Legend Header Configuration
# auto = send on cold start only, always = always send, never = never send
VETKA_JSON_CONTEXT_LEGEND_MODE = os.getenv(
    "VETKA_JSON_CONTEXT_LEGEND_MODE", "auto"
).lower()

# [PHASE73.6-2] Phase 73.6: Legend map (abbreviated key → full key)
ELISION_LEGEND_MAP = {
    "cf": "current_file",
    "sn": "semantic_neighbors",
    "d": "dependencies",
    "imp": "imports",
    "by": "imported_by",
    "v": "viewport",
    "vf": "visible_files",
    "pc": "pinned_count",
    "zl": "zoom_level",
    "ff": "folder_focus",
    "s": "summary",
    "td": "total_dependencies",
    "tsn": "total_semantic_neighbors",
    "sl": "strongest_link",
    "p": "path",
    "n": "name",
    "sc": "score",
    "t": "type",
}

# Phase 73.6: Cold start tracking (per-session)
# Phase 73.6.2: Changed to per-model tracking - each model gets legend on first call
_json_context_session_id: Optional[str] = None
_json_context_models_seen: Set[str] = set()  # Models that have seen legend this session

# Phase 73.5: JSON context LRU cache
_json_context_cache: Dict[str, str] = {}
_json_context_cache_hits = 0
_json_context_cache_misses = 0

# Phase 67.2: LRU cache for relevance scores
_relevance_cache: Dict[str, List[Tuple[Dict, float]]] = {}
_cache_max_size = 100
_cache_hits = 0
_cache_misses = 0


def format_history_for_prompt(messages: list, max_messages: int = 10) -> str:
    """
    Phase 51.1: Format chat history for LLM prompt.

    Args:
        messages: List of message dicts from ChatHistoryManager
        max_messages: Maximum number of recent messages to include

    Returns:
        Formatted history string for prompt, or empty string if no history
    """
    if not messages:
        return ""

    # Take last N messages
    recent = messages[-max_messages:] if len(messages) > max_messages else messages

    formatted = "## CONVERSATION HISTORY\n"
    formatted += "(Previous messages in this conversation)\n\n"

    for msg in recent:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "") or msg.get("text", "")

        # Truncate very long messages
        if len(content) > 500:
            content = content[:500] + "... [truncated]"

        # Include agent name if assistant
        if role == "ASSISTANT":
            agent = msg.get("agent", "Assistant")
            formatted += f"**{agent}**: {content}\n\n"
        else:
            formatted += f"**USER**: {content}\n\n"

    formatted += "---\n\n"
    return formatted


def load_pinned_file_content(
    file_path: str, max_chars: int = 999999
) -> Optional[str]:  # Unlimited for full context
    """
    Phase 61: Load file content from path for pinned files context.

    Args:
        file_path: Path to file
        max_chars: Maximum characters to include (truncate if larger)

    Returns:
        File content string, or None if not accessible
    """
    # Try different base paths
    possible_paths = [
        file_path,
        os.path.join(os.getcwd(), file_path),
        os.path.join(os.getcwd(), "data", file_path),
    ]

    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if len(content) > max_chars:
                        content = content[:max_chars] + "\n... [truncated]"
                    return content
            except Exception as e:
                print(f"[PHASE_61] Failed to read {path}: {e}")

    return None


# FIX_97.1: Consolidated to src/utils/token_utils.py
from src.utils.token_utils import estimate_tokens as _estimate_tokens


def _smart_truncate(content: str, max_tokens: int = 1000) -> str:
    """
    Smart truncation that preserves beginning and end of file.

    More useful than simple char truncation because:
    - Beginning often has imports, class definitions
    - End often has exports, main logic

    Args:
        content: File content
        max_tokens: Maximum tokens to include

    Returns:
        Truncated content
    """
    max_chars = max_tokens * 4  # Rough token-to-char conversion

    if len(content) <= max_chars:
        return content

    # Keep 60% from beginning, 40% from end
    head_chars = int(max_chars * 0.6)
    tail_chars = int(max_chars * 0.4)

    head = content[:head_chars]
    tail = content[-tail_chars:]

    return f"{head}\n\n... [truncated {len(content) - max_chars} chars] ...\n\n{tail}"


def _batch_get_qdrant_relevance(
    file_paths: List[str], query_embedding: List[float]
) -> Dict[str, float]:
    """
    Phase 67.2: Batch Qdrant query for all files at once.

    Single query instead of N queries - major performance improvement.

    Args:
        file_paths: List of file paths to score
        query_embedding: User query embedding vector

    Returns:
        Dict mapping path -> relevance score (0.0-1.0)
    """
    default_scores = {path: 0.5 for path in file_paths}

    if not query_embedding:
        return default_scores

    try:
        from src.memory.qdrant_client import get_qdrant_client

        qdrant = get_qdrant_client()
        if not qdrant or not qdrant.health_check():
            return default_scores

        # Single search, get more results to cover all pinned files
        results = qdrant.search_by_vector(
            query_vector=query_embedding, limit=100, score_threshold=0.2
        )

        # Build path → score map
        scores = {}
        for path in file_paths:
            scores[path] = 0.3  # Default: not found in index
            for result in results:
                result_path = result.get("path", "")
                if path in result_path or result_path in path:
                    scores[path] = result.get("score", 0.5)
                    break

        return scores

    except Exception as e:
        logger.debug(f"[CONTEXT] Batch Qdrant failed: {e}")
        return default_scores


def _get_cam_activation(file_path: str) -> float:
    """
    Get CAM activation score for a file.

    Phase 67.2: Uses singleton CAM engine instead of creating new instance.

    Args:
        file_path: Path to file

    Returns:
        Activation score (0.0-1.0), or 0.5 as default
    """
    try:
        from src.orchestration.cam_engine import get_cam_engine

        # Phase 67.2: Use singleton instead of creating new instance
        cam = get_cam_engine()
        if not cam:
            return 0.5

        # Look for node by path
        for node_id, node in cam.nodes.items():
            if file_path in node.path or node.path in file_path:
                return cam.calculate_activation_score(node_id)

        return 0.5  # Default if not in CAM tree

    except Exception as e:
        logger.debug(f"[CONTEXT] CAM activation failed: {e}")
        return 0.5


def _batch_get_cam_activations(file_paths: List[str]) -> Dict[str, float]:
    """
    Phase 67.2: Get CAM activation scores for multiple files.

    Args:
        file_paths: List of file paths

    Returns:
        Dict mapping path -> activation score
    """
    scores = {}
    try:
        from src.orchestration.cam_engine import get_cam_engine

        cam = get_cam_engine()
        if not cam:
            return {path: 0.5 for path in file_paths}

        for path in file_paths:
            found = False
            for node_id, node in cam.nodes.items():
                if path in node.path or node.path in path:
                    scores[path] = cam.calculate_activation_score(node_id)
                    found = True
                    break
            if not found:
                scores[path] = 0.5

        return scores

    except Exception as e:
        logger.debug(f"[CONTEXT] Batch CAM failed: {e}")
        return {path: 0.5 for path in file_paths}


def _make_cache_key(user_query: str, file_paths: List[str]) -> str:
    """
    Phase 67.2: Create cache key from query and file paths.

    Args:
        user_query: User's query
        file_paths: List of file paths

    Returns:
        MD5 hash as cache key
    """
    content = user_query + "|" + "|".join(sorted(file_paths))
    return hashlib.md5(content.encode()).hexdigest()


# =============================================================================
# MARKER_109_7_UNIFIED_WEIGHTING: Additional scoring functions
# =============================================================================

def _batch_get_engram_scores(file_paths: List[str], user_id: str = "default") -> Dict[str, float]:
    """
    Phase 109.7: Get Engram preference affinity scores for files.

    Uses user's historical preferences to boost relevant files.
    """
    scores = {}
    try:
        from src.memory.engram_user_memory import get_engram_user_memory

        engram = get_engram_user_memory()
        if not engram:
            return {path: 0.5 for path in file_paths}

        prefs = engram.get_user_preferences(user_id)
        if not prefs:
            return {path: 0.5 for path in file_paths}

        # Score files based on user's code preferences
        code_prefs = getattr(prefs, 'code_preferences', {}) or {}
        preferred_patterns = code_prefs.get('preferred_patterns', [])

        for path in file_paths:
            score = 0.5  # Default
            # Boost if matches user's preferred file types
            if any(pattern in path for pattern in preferred_patterns):
                score = 0.8
            # Boost if recently viewed (viewport_patterns)
            viewport_prefs = getattr(prefs, 'viewport_patterns', {}) or {}
            if path in viewport_prefs.get('recent_files', []):
                score = min(1.0, score + 0.2)
            scores[path] = score

        return scores
    except Exception as e:
        logger.debug(f"[UNIFIED] Engram scoring failed: {e}")
        return {path: 0.5 for path in file_paths}


def _batch_get_viewport_scores(file_paths: List[str], viewport_context: Optional[Dict] = None) -> Dict[str, float]:
    """
    Phase 109.7: Get viewport proximity scores for files.

    Files closer to camera get higher scores.
    Formula: score = 1 / (1 + distance/100)
    """
    scores = {}

    if not viewport_context:
        return {path: 0.5 for path in file_paths}

    try:
        # Extract visible nodes with distances
        viewport_nodes = viewport_context.get('viewport_nodes', [])
        pinned_nodes = viewport_context.get('pinned_nodes', [])

        # Build distance map
        distance_map = {}
        for node in viewport_nodes + pinned_nodes:
            node_path = node.get('path', node.get('name', ''))
            dist = node.get('distance_to_camera', node.get('d', 500))
            if node_path:
                distance_map[node_path] = dist

        # Score each file
        for path in file_paths:
            if path in distance_map:
                dist = distance_map[path]
                # Inverse distance: closer = higher score
                scores[path] = 1.0 / (1.0 + dist / 100.0)
            else:
                # Not visible - check if pinned (higher priority)
                is_pinned = any(n.get('is_pinned', False) for n in pinned_nodes
                               if path in n.get('path', ''))
                scores[path] = 0.7 if is_pinned else 0.3

        return scores
    except Exception as e:
        logger.debug(f"[UNIFIED] Viewport scoring failed: {e}")
        return {path: 0.5 for path in file_paths}


def _batch_get_hope_scores(file_paths: List[str], zoom_level: float = 1.0) -> Dict[str, float]:
    """
    Phase 109.7: Get HOPE frequency layer scores.

    Adapts scoring based on zoom level (LOD):
    - LOW (zoom < 0.5): Boost overview/summary files
    - MID (0.5 <= zoom < 2): Balanced
    - HIGH (zoom >= 2): Boost implementation details
    """
    scores = {}

    try:
        # Determine current layer based on zoom
        if zoom_level < 0.5:
            layer = "LOW"
            # Boost: README, docs, __init__.py, index files
            boost_patterns = ['readme', '__init__', 'index', 'main', 'summary']
        elif zoom_level < 2.0:
            layer = "MID"
            boost_patterns = ['handler', 'service', 'route', 'api', 'controller']
        else:
            layer = "HIGH"
            # Boost: specific implementations, utils, helpers
            boost_patterns = ['util', 'helper', 'tool', 'impl', '_test', 'spec']

        for path in file_paths:
            path_lower = path.lower()
            if any(pattern in path_lower for pattern in boost_patterns):
                scores[path] = 0.9
            else:
                scores[path] = 0.5

        logger.debug(f"[UNIFIED] HOPE layer={layer}, zoom={zoom_level}")
        return scores
    except Exception as e:
        logger.debug(f"[UNIFIED] HOPE scoring failed: {e}")
        return {path: 0.5 for path in file_paths}


def _batch_get_mgc_scores(file_paths: List[str]) -> Dict[str, float]:
    """
    Phase 109.7: Get MGC (Multi-Generational Cache) hit scores.

    Files in hot cache (Gen0) get boost.
    """
    scores = {}

    try:
        from src.memory.spiral_context_generator import SpiralContextGenerator

        generator = SpiralContextGenerator()
        cache = generator.mgc_cache

        for path in file_paths:
            # Check if in any cache generation
            cached = cache.get(path)
            if cached:
                gen = cached.get('generation', 2)
                # Gen0 = 1.0, Gen1 = 0.7, Gen2 = 0.4
                scores[path] = 1.0 - (gen * 0.3)
            else:
                scores[path] = 0.3  # Not cached

        return scores
    except Exception as e:
        logger.debug(f"[UNIFIED] MGC scoring failed: {e}")
        return {path: 0.5 for path in file_paths}


def _rank_pinned_files(
    pinned_files: list,
    user_query: str,
    viewport_context: Optional[Dict] = None,
    user_id: str = "default",
    zoom_level: float = 1.0,
) -> List[Tuple[Dict, float]]:
    """
    MARKER_109_7_UNIFIED_WEIGHTING: Rank pinned files using multi-source scoring.

    Phase 67.2 → Phase 109.7: Extended from 2 sources to 6 sources.

    Unified formula:
    relevance = qdrant*0.40 + cam*0.20 + engram*0.15 + viewport*0.15 + hope*0.05 + mgc*0.05

    Args:
        pinned_files: List of {id, path, name, type} dicts
        user_query: User's question/message
        viewport_context: Optional viewport data with distances
        user_id: User ID for Engram preferences
        zoom_level: Current zoom for HOPE layer selection

    Returns:
        List of (file_dict, relevance_score) tuples, sorted by score descending
    """
    global _cache_hits, _cache_misses

    if not user_query:
        # No query - return files as-is with neutral scores
        return [(pf, 0.5) for pf in pinned_files]

    # Filter out folders and collect paths
    file_candidates = [pf for pf in pinned_files if pf.get("type", "file") != "folder"]

    if not file_candidates:
        return []

    file_paths = [pf.get("path", pf.get("name", "unknown")) for pf in file_candidates]

    # Phase 67.2: Check cache first
    cache_key = _make_cache_key(user_query, file_paths)
    if cache_key in _relevance_cache:
        _cache_hits += 1
        logger.debug(
            f"[UNIFIED] Cache hit (hits={_cache_hits}, misses={_cache_misses})"
        )
        return _relevance_cache[cache_key]

    _cache_misses += 1

    # Get query embedding once
    query_embedding = None
    try:
        from src.utils.embedding_service import get_embedding

        query_embedding = get_embedding(user_query)
    except Exception as e:
        logger.debug(f"[UNIFIED] Embedding failed: {e}")

    # MARKER_109_7: Batch queries for ALL 6 sources
    qdrant_scores = _batch_get_qdrant_relevance(file_paths, query_embedding)
    cam_scores = _batch_get_cam_activations(file_paths)
    engram_scores = _batch_get_engram_scores(file_paths, user_id)
    viewport_scores = _batch_get_viewport_scores(file_paths, viewport_context)
    hope_scores = _batch_get_hope_scores(file_paths, zoom_level)
    mgc_scores = _batch_get_mgc_scores(file_paths)

    # Calculate unified relevance
    ranked = []
    for pf in file_candidates:
        file_path = pf.get("path", pf.get("name", "unknown"))

        # Get all scores with defaults
        scores = {
            'qdrant': qdrant_scores.get(file_path, 0.5),
            'cam': cam_scores.get(file_path, 0.5),
            'engram': engram_scores.get(file_path, 0.5),
            'viewport': viewport_scores.get(file_path, 0.5),
            'hope': hope_scores.get(file_path, 0.5),
            'mgc': mgc_scores.get(file_path, 0.5),
        }

        # MARKER_109_7_UNIFIED_FORMULA: Weighted sum
        relevance = (
            scores['qdrant'] * QDRANT_WEIGHT +
            scores['cam'] * CAM_WEIGHT +
            scores['engram'] * ENGRAM_WEIGHT +
            scores['viewport'] * VIEWPORT_WEIGHT +
            scores['hope'] * HOPE_WEIGHT +
            scores['mgc'] * MGC_WEIGHT
        )

        # Clamp to [0, 1]
        relevance = min(1.0, max(0.0, relevance))

        ranked.append((pf, relevance))

    # Sort by relevance descending
    ranked.sort(key=lambda x: x[1], reverse=True)

    # Log top-5 for debugging
    if VETKA_DEBUG_CONTEXT and ranked:
        top5_info = ", ".join(f"{pf.get('name', '?')}={score:.2f}" for pf, score in ranked[:5])
        logger.info(f"[UNIFIED] Top-5: {top5_info}")

    # Phase 67.2: Store in cache (with size limit)
    if len(_relevance_cache) >= _cache_max_size:
        # Remove oldest entry (FIFO)
        oldest_key = next(iter(_relevance_cache))
        del _relevance_cache[oldest_key]

    _relevance_cache[cache_key] = ranked

    return ranked


def clear_relevance_cache():
    """Phase 67.2: Clear the relevance cache (for testing)."""
    global _relevance_cache, _cache_hits, _cache_misses
    _relevance_cache.clear()
    _cache_hits = 0
    _cache_misses = 0
    logger.info("[CONTEXT] Relevance cache cleared")


def get_cache_stats() -> Dict[str, int]:
    """Phase 67.2: Get cache statistics."""
    return {
        "size": len(_relevance_cache),
        "max_size": _cache_max_size,
        "hits": _cache_hits,
        "misses": _cache_misses,
        "hit_rate": f"{_cache_hits / (_cache_hits + _cache_misses) * 100:.1f}%"
        if (_cache_hits + _cache_misses) > 0
        else "N/A",
    }


def build_pinned_context(
    pinned_files: list,
    user_query: str = "",
    max_files: int = VETKA_MAX_PINNED_FILES,  # Phase 69: from env var
    max_tokens_per_file: int = MAX_TOKENS_PER_FILE,
    max_total_tokens: int = MAX_CONTEXT_TOKENS,
    is_artifact_panel: bool = False,  # NEW: Flag for artifact panel unlimited tokens
    viewport_context: Optional[Dict] = None,  # MARKER_109_7: For unified weighting
    user_id: str = "default",  # MARKER_109_7: For Engram preferences
    zoom_level: float = 1.0,  # MARKER_109_7: For HOPE layer selection
    model_name: str = "",  # MARKER_109_7: For dynamic token budget
) -> str:
    """
    Phase 67 → Phase 109.7: Build smart context with unified weighting.

    MARKER_109_7_UNIFIED_WEIGHTING: Extended scoring from 2 to 6 sources.

    Uses multi-source scoring:
    1. Qdrant semantic similarity (40%)
    2. CAM activation/surprise (20%)
    3. Engram user preferences (15%)
    4. Viewport proximity (15%)
    5. HOPE frequency layer (5%)
    6. MGC cache hits (5%)

    Args:
        pinned_files: List of {id, path, name, type} dicts
        user_query: User's question (for relevance ranking)
        max_files: Maximum number of files to include (default 5)
        max_tokens_per_file: Token limit per file (default from env)
        max_total_tokens: Total token budget for context (default from env)
        is_artifact_panel: If True, use unlimited tokens for full file display
        viewport_context: Viewport data with file distances (Phase 109.7)
        user_id: User ID for Engram preferences (Phase 109.7)
        zoom_level: Current zoom for HOPE layer (Phase 109.7)
        model_name: Model name for dynamic token budget (Phase 109.7)

    Returns:
        XML-formatted context string
    """
    if not pinned_files:
        return ""

    # Filter out folders first
    file_candidates = [pf for pf in pinned_files if pf.get("type", "file") != "folder"]

    if not file_candidates:
        return ""

    # MARKER_109_7: Dynamic token budget based on model
    if model_name:
        effective_max_tokens = get_context_budget_for_model(model_name)
        if effective_max_tokens != max_total_tokens:
            logger.debug(f"[UNIFIED] Token budget adjusted: {max_total_tokens} → {effective_max_tokens} for {model_name}")
            max_total_tokens = effective_max_tokens

    # Try smart ranking, fall back to original order
    use_smart_selection = False
    try:
        if user_query:
            # MARKER_109_7: Pass all context for unified weighting
            ranked_files = _rank_pinned_files(
                file_candidates,
                user_query,
                viewport_context=viewport_context,
                user_id=user_id,
                zoom_level=zoom_level
            )
            use_smart_selection = True
            avg_relevance = (
                sum(r[1] for r in ranked_files) / len(ranked_files)
                if ranked_files
                else 0
            )
            logger.info(
                f"[CONTEXT] Using smart selection: {len(ranked_files)} files, {avg_relevance:.2f} avg relevance"
            )
        else:
            # No query - use original order with neutral scores
            ranked_files = [(pf, 0.5) for pf in file_candidates]
    except Exception as e:
        logger.warning(f"[CONTEXT] Smart ranking failed, using fallback: {e}")
        ranked_files = [(pf, 0.5) for pf in file_candidates]

    # Select top files within token budget
    context_parts = []
    total_tokens = 0
    files_included = 0

    # Use artifact panel unlimited tokens if flag is set
    if is_artifact_panel:
        max_tokens_per_file = ARTIFACT_MAX_TOKENS_PER_FILE
        max_total_tokens = 999999  # Practically unlimited

    for pf, relevance in ranked_files[:max_files]:
        file_path = pf.get("path", pf.get("name", "unknown"))
        file_name = pf.get("name", "unknown")

        content = load_pinned_file_content(file_path, max_chars=max_tokens_per_file * 4)

        if content:
            # Smart truncate if needed
            content = _smart_truncate(content, max_tokens=max_tokens_per_file)
            content_tokens = _estimate_tokens(content)

            # Check total budget
            if total_tokens + content_tokens > max_total_tokens:
                # Truncate to fit remaining budget
                remaining_tokens = max_total_tokens - total_tokens
                if remaining_tokens < 200:  # Too little space left
                    break
                content = _smart_truncate(content, max_tokens=remaining_tokens)
                content_tokens = _estimate_tokens(content)

            relevance_tag = (
                f' relevance="{relevance:.2f}"' if use_smart_selection else ""
            )
            context_parts.append(
                f'<pinned_file path="{file_path}" name="{file_name}"{relevance_tag}>\n{content}\n</pinned_file>'
            )
            total_tokens += content_tokens
            files_included += 1
        else:
            context_parts.append(
                f'<pinned_file path="{file_path}" name="{file_name}">\n[File not accessible]\n</pinned_file>'
            )

    if not context_parts:
        return ""

    selection_note = ""
    if use_smart_selection:
        selection_note = f"\n(Files ranked by semantic relevance to user query. Showing top {files_included} of {len(file_candidates)}.)"

    # Phase 67.2: Optional debug mode
    debug_section = ""
    if VETKA_DEBUG_CONTEXT and use_smart_selection:
        cache_stats = get_cache_stats()
        debug_section = f"""
<context_debug>
Query: {user_query[:100]}{"..." if len(user_query) > 100 else ""}
Ranking:
{chr(10).join(f"  {i + 1}. {pf.get('name')} - relevance={score:.3f}" for i, (pf, score) in enumerate(ranked_files[:max_files]))}
Weights: qdrant={QDRANT_WEIGHT}, cam={CAM_WEIGHT}
Cache: {cache_stats["hit_rate"]} hit rate ({cache_stats["hits"]} hits, {cache_stats["misses"]} misses)
</context_debug>
"""

    # MARKER_109_5_CONTEXT_META: Add meta-info so agents understand HOW context was built
    context_meta = f"""<context_meta>
  selection: {"qdrant_semantic + cam_activation" if use_smart_selection else "original_order"}
  total_pinned: {len(file_candidates)}
  included: {files_included}
  tokens: ~{total_tokens}
  compression: elision
  weights: qdrant={QDRANT_WEIGHT}, cam={CAM_WEIGHT}
</context_meta>
"""

    return f"""
{context_meta}<pinned_context>
User has pinned {len(file_candidates)} file(s). Included {files_included} most relevant file(s) for context (~{total_tokens} tokens).{selection_note}

{chr(10).join(context_parts)}
</pinned_context>
{debug_section}
"""


def build_pinned_context_legacy(pinned_files: list, max_files: int = 10) -> str:
    """
    Legacy implementation of build_pinned_context (pre-Phase 67).

    Kept for backwards compatibility and fallback.
    Uses simple file reading with char-based truncation.

    Args:
        pinned_files: List of {id, path, name, type} dicts
        max_files: Maximum number of files to include

    Returns:
        XML-formatted context string
    """
    if not pinned_files:
        return ""

    context_parts = []
    for pf in pinned_files[:max_files]:
        file_path = pf.get("path", pf.get("name", "unknown"))
        file_name = pf.get("name", "unknown")
        file_type = pf.get("type", "file")

        # Skip folders
        if file_type == "folder":
            continue

        content = load_pinned_file_content(file_path)
        if content:
            context_parts.append(
                f'<pinned_file path="{file_path}" name="{file_name}">\n{content}\n</pinned_file>'
            )
        else:
            context_parts.append(
                f'<pinned_file path="{file_path}" name="{file_name}">\n[File not accessible]\n</pinned_file>'
            )

    if not context_parts:
        return ""

    return f"""
<pinned_context>
User has pinned {len(context_parts)} file(s) for additional context.
These files should be considered when answering the user's question.

{chr(10).join(context_parts)}
</pinned_context>

"""


# ═══════════════════════════════════════════════════════════════════
# [PHASE73.5-2] Phase 73.5: ELISION Compression Functions
# Etymology: ELYSIUM (highlights) + ELISION (sound compression)
# The accidental typo "Elisya" from Phase 44 perfectly describes this!
# ═══════════════════════════════════════════════════════════════════


def _shorten_path(path: str) -> str:
    """
    Phase 73.5: ELISION path compression.

    Shortens paths by abbreviating folder names to first letter.
    Example: '/src/orchestration/cam_engine.py' → 's/o/cam_engine.py'

    Args:
        path: Full file path

    Returns:
        Shortened path (40-60% token savings on paths)
    """
    if not path:
        return path

    # Remove leading slash for processing
    clean_path = path.lstrip("/")
    parts = clean_path.split("/")

    if len(parts) <= 2:
        return path  # Already short enough

    # Keep last part (filename), abbreviate folders
    abbreviated = [p[0] if p else "" for p in parts[:-1]]
    abbreviated.append(parts[-1])  # Full filename

    return "/" + "/".join(abbreviated)


def _compress_json_context(context_data: Dict, compressed: bool = True) -> Dict:
    """
    Phase 73.5: ELISION JSON compression.

    Shortens JSON keys and paths for token efficiency.

    Key mappings:
        current_file → cf
        dependencies → d
        semantic_neighbors → sn
        viewport → v
        summary → s
        imports → imp
        imported_by → by
        visible_files → vf
        pinned_count → pc
        zoom_level → zl
        folder_focus → ff
        total_dependencies → td
        total_semantic_neighbors → tsn
        strongest_link → sl

    Args:
        context_data: Full JSON context dict
        compressed: Whether to apply compression

    Returns:
        Compressed dict (or original if compressed=False)
    """
    if not compressed:
        return context_data

    # Key mappings for compression
    key_map = {
        "current_file": "cf",
        "dependencies": "d",
        "semantic_neighbors": "sn",
        "viewport": "v",
        "summary": "s",
        "imports": "imp",
        "imported_by": "by",
        "visible_files": "vf",
        "pinned_count": "pc",
        "zoom_level": "zl",
        "folder_focus": "ff",
        "total_dependencies": "td",
        "total_semantic_neighbors": "tsn",
        "strongest_link": "sl",
    }

    def compress_dict(d: Dict) -> Dict:
        """Recursively compress dict keys and shorten paths."""
        if not isinstance(d, dict):
            return d

        result = {}
        for key, value in d.items():
            # Compress key
            new_key = key_map.get(key, key)

            # Handle nested structures
            if isinstance(value, dict):
                result[new_key] = compress_dict(value)
            elif isinstance(value, list):
                result[new_key] = [
                    compress_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif key == "path" and isinstance(value, str):
                # Shorten paths
                result[new_key] = _shorten_path(value)
            else:
                result[new_key] = value

        return result

    return compress_dict(context_data)


def _make_json_context_cache_key(
    current_file_path: str, viewport_hash: str = ""
) -> str:
    """
    Phase 73.5: Create cache key for JSON context.

    Args:
        current_file_path: Path of current file
        viewport_hash: Optional hash of viewport state

    Returns:
        MD5 hash as cache key
    """
    content = f"{current_file_path}|{viewport_hash}"
    return hashlib.md5(content.encode()).hexdigest()


def _get_cached_json_context(cache_key: str) -> Optional[str]:
    """
    Phase 73.5: Get JSON context from cache.

    Args:
        cache_key: Cache key from _make_json_context_cache_key()

    Returns:
        Cached JSON string, or None if not found
    """
    global _json_context_cache_hits, _json_context_cache_misses

    if cache_key in _json_context_cache:
        _json_context_cache_hits += 1
        logger.debug(f"[PHASE73.5] Cache hit for {cache_key[:8]}...")
        return _json_context_cache[cache_key]

    _json_context_cache_misses += 1
    return None


def _set_cached_json_context(cache_key: str, json_str: str) -> None:
    """
    Phase 73.5: Store JSON context in cache with LRU eviction.

    Args:
        cache_key: Cache key
        json_str: JSON string to cache
    """
    global _json_context_cache

    # LRU eviction: remove oldest if cache is full
    if len(_json_context_cache) >= VETKA_JSON_CONTEXT_CACHE_SIZE:
        oldest_key = next(iter(_json_context_cache))
        del _json_context_cache[oldest_key]

    _json_context_cache[cache_key] = json_str


def clear_json_context_cache() -> None:
    """Phase 73.5: Clear the JSON context cache (for testing)."""
    global _json_context_cache, _json_context_cache_hits, _json_context_cache_misses
    _json_context_cache.clear()
    _json_context_cache_hits = 0
    _json_context_cache_misses = 0
    logger.info("[PHASE73.5] JSON context cache cleared")


def get_json_context_cache_stats() -> Dict[str, int]:
    """Phase 73.5: Get JSON context cache statistics."""
    total = _json_context_cache_hits + _json_context_cache_misses
    return {
        "size": len(_json_context_cache),
        "max_size": VETKA_JSON_CONTEXT_CACHE_SIZE,
        "hits": _json_context_cache_hits,
        "misses": _json_context_cache_misses,
        "hit_rate": f"{_json_context_cache_hits / total * 100:.1f}%"
        if total > 0
        else "N/A",
    }


# ═══════════════════════════════════════════════════════════════════
# [PHASE73.6-3] Phase 73.6: Legend Header Functions
# ═══════════════════════════════════════════════════════════════════


def _is_cold_start(
    session_id: Optional[str] = None, model_name: Optional[str] = None
) -> bool:
    """
    Phase 73.6: Detect if this is the first message of session (cold start).
    Phase 73.6.2: Changed to per-model tracking - each model gets legend on first call.

    Uses session_id to track per-session state. If session_id changes,
    resets models seen set. Each model gets _legend on its first call.

    Args:
        session_id: Optional session identifier (e.g., socket.io sid)
        model_name: Optional model name for per-model tracking

    Returns:
        True if legend should be included, False otherwise
    """
    global _json_context_session_id, _json_context_models_seen

    # New session detected - reset models seen
    if session_id and session_id != _json_context_session_id:
        _json_context_session_id = session_id
        _json_context_models_seen = set()
        logger.debug(
            f"[PHASE73.6.2] New session {session_id[:8]}..., reset models_seen"
        )

    # If no model specified, check if ANY model has been seen
    if not model_name:
        # First call of session (no models seen yet)
        return len(_json_context_models_seen) == 0

    # Per-model cold start: has this model seen the legend?
    return model_name not in _json_context_models_seen


def _mark_model_seen(model_name: Optional[str] = None) -> None:
    """
    Phase 73.6.2: Mark model as having seen the legend.

    Args:
        model_name: Model name to mark as seen (if None, marks generic "unknown")
    """
    global _json_context_models_seen
    model_key = model_name or "unknown"
    _json_context_models_seen.add(model_key)
    logger.debug(f"[PHASE73.6.2] Marked model '{model_key}' as seen legend")


def _should_include_legend(
    include_legend: Optional[bool],
    session_id: Optional[str] = None,
    model_name: Optional[str] = None,
) -> bool:
    """
    Phase 73.6: Determine if legend should be included in output.
    Phase 73.6.2: Added per-model tracking.

    Args:
        include_legend: Explicit setting (None = use auto mode)
        session_id: Session identifier for cold start detection
        model_name: Model name for per-model cold start tracking

    Returns:
        True if legend should be included
    """
    # Explicit setting takes precedence
    if include_legend is True:
        return True
    if include_legend is False:
        return False

    # Auto mode based on LEGEND_MODE config
    if VETKA_JSON_CONTEXT_LEGEND_MODE == "always":
        return True
    if VETKA_JSON_CONTEXT_LEGEND_MODE == "never":
        return False

    # Default: "auto" - include on cold start only (per-model)
    return _is_cold_start(session_id, model_name)


def reset_json_context_session() -> None:
    """
    Phase 73.6: Reset session state (for testing or manual reset).
    Phase 73.6.2: Updated for per-model tracking.

    Clears session_id and models_seen set, causing next call to be cold start.
    """
    global _json_context_session_id, _json_context_models_seen
    _json_context_session_id = None
    _json_context_models_seen = set()
    logger.debug("[PHASE73.6.2] Session state reset (all models cleared)")


def get_legend_map() -> Dict[str, str]:
    """Phase 73.6: Get the ELISION legend map for external use."""
    return ELISION_LEGEND_MAP.copy()


# ═══════════════════════════════════════════════════════════════════
# [PHASE73-2] Phase 73: JSON Context Builder for AI Agents
# [PHASE73.5-6] Phase 73.5: Enhanced with compression, cache, PythonScanner
# [PHASE73.6-4] Phase 73.6: Added legend header support
# [PHASE73.6.2] Phase 73.6.2: Per-model cold start tracking
# ═══════════════════════════════════════════════════════════════════


def build_json_context(
    pinned_files: list = None,
    viewport_context: dict = None,
    max_tokens: int = VETKA_JSON_CONTEXT_MAX_TOKENS,
    include_dependencies: bool = VETKA_JSON_CONTEXT_INCLUDE_DEPS,
    include_semantic_neighbors: bool = VETKA_JSON_CONTEXT_INCLUDE_SEMANTIC,
    compressed: bool = VETKA_JSON_CONTEXT_COMPRESSED,
    use_cache: bool = True,
    include_legend: Optional[bool] = None,
    session_id: Optional[str] = None,
    model_name: Optional[str] = None,
) -> str:
    """
    Phase 73: Build structured JSON context for AI agents.
    Phase 73.5: Enhanced with ELISION compression and LRU cache.
    Phase 73.6: Added legend header for cold start/debug.
    Phase 73.6.2: Added per-model cold start tracking.

    Assembles dependency graph and semantic neighbors into a compact JSON
    format that AI can use to understand file relationships.

    ELISION compression (Phase 73.5):
    - Paths shortened: '/src/orchestration/cam.py' → 's/o/cam.py'
    - Keys abbreviated: 'current_file' → 'cf', 'dependencies' → 'd'
    - JSON minified when compressed=True

    Legend header (Phase 73.6):
    - When include_legend=True or on cold start (auto mode), adds "_legend" key
    - Contains mapping of abbreviated keys to full names
    - Helps AI understand compressed format on first message

    Per-model tracking (Phase 73.6.2):
    - Each model gets _legend on its first call in the session
    - Allows different models to receive legend independently

    Args:
        pinned_files: List of {id, path, name, type} dicts from UI
        viewport_context: Dict from frontend with camera_position, pinned_nodes, etc.
        max_tokens: Maximum tokens for JSON output (default 2000)
        include_dependencies: Whether to include dependency scoring
        include_semantic_neighbors: Whether to include Qdrant semantic search
        compressed: Whether to apply ELISION compression (default from env)
        use_cache: Whether to use LRU cache (default True)
        include_legend: Include legend header (None=auto, True=always, False=never)
        session_id: Session ID for cold start detection (optional)
        model_name: Model name for per-model cold start tracking (optional)

    Returns:
        JSON string wrapped in section header, or empty string if no context

    Example output (compressed=False):
        ## DEPENDENCY CONTEXT
        ```json
        {
          "current_file": {"path": "/src/main.py", "name": "main.py"},
          "dependencies": {"imports": [...], "imported_by": [...]},
          "semantic_neighbors": [...],
          "viewport": {"visible_files": 12, "zoom_level": "medium"}
        }
        ```

    Example output (compressed=True, with legend):
        ## DEPENDENCY CONTEXT
        ```json
        {"_l":{"cf":"current_file","sn":"semantic_neighbors",...},"cf":{"p":"s/main.py"},...}
        ```

    Example output (compressed=True, no legend):
        ## DEPENDENCY CONTEXT
        ```json
        {"cf":{"p":"s/main.py","n":"main.py"},"d":{"imp":[],"by":[]},"sn":[],"v":{"vf":12,"zl":"medium"}}
        ```
    """
    import json

    # === Determine current_file from available context ===
    current_file_path = ""
    current_file_name = ""
    current_file_type = "file"

    # Priority 1: First pinned file
    if pinned_files and len(pinned_files) > 0:
        first_pinned = pinned_files[0]
        current_file_path = first_pinned.get("path", first_pinned.get("name", ""))
        current_file_name = first_pinned.get("name", "")
        current_file_type = first_pinned.get("type", "file")

    # Priority 2: Selected node from viewport_context
    elif viewport_context and viewport_context.get("selected_node"):
        selected = viewport_context["selected_node"]
        current_file_path = selected.get("path", selected.get("name", ""))
        current_file_name = selected.get("name", "")
        current_file_type = selected.get("type", "file")

    # Priority 3: First pinned node from viewport
    elif viewport_context and viewport_context.get("pinned_nodes"):
        pinned = viewport_context["pinned_nodes"]
        if pinned:
            first_node = pinned[0]
            current_file_path = first_node.get("path", first_node.get("name", ""))
            current_file_name = first_node.get("name", "")
            current_file_type = first_node.get("type", "file")

    # No context available
    if not current_file_path:
        logger.debug("[PHASE73] No current_file available, skipping JSON context")
        return ""

    # === [PHASE73.5-3] Check cache first ===
    viewport_hash = ""
    if viewport_context:
        viewport_hash = str(viewport_context.get("zoom_level", 0)) + str(
            viewport_context.get("total_visible", 0)
        )

    cache_key = _make_json_context_cache_key(current_file_path, viewport_hash)

    if use_cache:
        cached = _get_cached_json_context(cache_key)
        if cached:
            logger.debug(f"[PHASE73.5] Cache hit for {current_file_name}")
            return cached

    # === Build JSON structure ===
    context_data = {
        "current_file": {
            "path": current_file_path,
            "name": current_file_name or current_file_path.split("/")[-1],
            "type": current_file_type,
        },
        "dependencies": {"imports": [], "imported_by": []},
        "semantic_neighbors": [],
        "viewport": {},
        "summary": {},
    }

    # === Fetch semantic neighbors from Qdrant ===
    semantic_results = []
    if include_semantic_neighbors:
        semantic_results = _fetch_semantic_neighbors(current_file_path, limit=10)
        context_data["semantic_neighbors"] = [
            {
                "path": r.get("path", ""),
                "name": r.get("name", ""),
                "score": round(r.get("score", 0), 3),
                "type": r.get("type", "file"),
            }
            for r in semantic_results
        ]

    # === Calculate dependency scores ===
    if include_dependencies and semantic_results:
        deps = _calculate_dependencies_for_context(current_file_path, semantic_results)
        context_data["dependencies"] = deps

    # === Add viewport summary ===
    if viewport_context:
        zoom = viewport_context.get("zoom_level", 0)
        context_data["viewport"] = {
            "visible_files": viewport_context.get("total_visible", 0),
            "pinned_count": viewport_context.get("total_pinned", 0),
            "zoom_level": "overview"
            if zoom <= 2
            else "medium"
            if zoom <= 5
            else "close-up",
            "folder_focus": _extract_folder_focus(viewport_context),
        }

    # === Build summary ===
    all_deps = context_data["dependencies"].get("imports", []) + context_data[
        "dependencies"
    ].get("imported_by", [])
    strongest = max(all_deps, key=lambda x: x.get("score", 0), default=None)

    context_data["summary"] = {
        "total_dependencies": len(all_deps),
        "total_semantic_neighbors": len(context_data["semantic_neighbors"]),
        "strongest_link": {
            "path": strongest.get("path", ""),
            "score": strongest.get("score", 0),
        }
        if strongest
        else None,
    }

    # === [PHASE73.5-4] Apply ELISION compression ===
    if compressed:
        context_data = _compress_json_context(context_data, compressed=True)

    # === [PHASE73.6-5] Add legend header if needed ===
    # [PHASE73.6.2] Now uses per-model tracking
    add_legend = compressed and _should_include_legend(
        include_legend, session_id, model_name
    )
    if add_legend:
        # Insert "_legend" at the beginning of the dict (full name for clarity, used only on cold start)
        context_data = {"_legend": ELISION_LEGEND_MAP, **context_data}
        logger.debug(
            f"[PHASE73.6.2] Added legend header for model '{model_name or 'unknown'}'"
        )

    # === Serialize and check token budget ===
    # Phase 73.5: Use minified JSON when compressed
    if compressed:
        json_str = json.dumps(context_data, separators=(",", ":"), ensure_ascii=False)
    else:
        json_str = json.dumps(context_data, indent=2, ensure_ascii=False)

    estimated_tokens = _estimate_tokens(json_str)

    if estimated_tokens > max_tokens:
        # Truncate: remove semantic_neighbors first, then dependencies
        context_data = _truncate_json_context(context_data, max_tokens)
        if compressed:
            json_str = json.dumps(
                context_data, separators=(",", ":"), ensure_ascii=False
            )
        else:
            json_str = json.dumps(context_data, indent=2, ensure_ascii=False)

    # === Debug output ===
    if VETKA_JSON_CONTEXT_DEBUG:
        logger.info(
            f"[PHASE73.6] JSON context: {_estimate_tokens(json_str)} tokens, "
            f"{len(all_deps)} deps, {len(semantic_results)} semantic, "
            f"compressed={compressed}, legend={add_legend}"
        )

    logger.info(
        f"[PHASE73.6] Built JSON context for {current_file_name}: "
        f"{_estimate_tokens(json_str)} tokens (compressed={compressed}, legend={add_legend})"
    )

    # === [PHASE73.6.2] Mark model as having seen legend ===
    if add_legend:
        _mark_model_seen(model_name)

    # === Build final result ===
    result = f"""## DEPENDENCY CONTEXT
```json
{json_str}
```

"""

    # === [PHASE73.5-5] Store in cache ===
    if use_cache:
        _set_cached_json_context(cache_key, result)
        logger.debug(f"[PHASE73.5] Cached context for {current_file_name}")

    return result


def _fetch_semantic_neighbors(
    file_path: str, limit: int = 10, score_threshold: float = 0.5
) -> List[Dict]:
    """
    Phase 73: Fetch semantically similar files from Qdrant.

    Uses existing get_qdrant_client() singleton and search_by_vector().

    Args:
        file_path: Path of file to find neighbors for
        limit: Maximum neighbors to return
        score_threshold: Minimum similarity score

    Returns:
        List of {path, name, score, type} dicts
    """
    try:
        from src.memory.qdrant_client import get_qdrant_client
        from src.utils.embedding_service import get_embedding

        qdrant = get_qdrant_client()
        if not qdrant or not qdrant.health_check():
            logger.debug("[PHASE73] Qdrant unavailable for semantic search")
            return []

        # Get embedding for current file
        # Note: get_embedding expects text, so we use file path as proxy
        # In future, could load file content for better embedding
        query_embedding = get_embedding(file_path)
        if not query_embedding:
            logger.debug("[PHASE73] Could not generate embedding for file")
            return []

        # Single batch query to Qdrant
        results = qdrant.search_by_vector(
            query_vector=query_embedding,
            limit=limit + 1,  # +1 to exclude self
            score_threshold=score_threshold,
            file_types_only=True,
        )

        # Filter out self-reference
        neighbors = [r for r in results if r.get("path", "") != file_path][:limit]

        return neighbors

    except ImportError as e:
        logger.debug(f"[PHASE73] Import error in semantic search: {e}")
        return []
    except Exception as e:
        logger.warning(f"[PHASE73] Semantic search failed: {e}")
        return []


def _get_import_confidence(source_path: str, target_path: str) -> float:
    """
    Phase 73.5: Get import confidence using PythonScanner.

    Checks if source_path imports target_path by parsing AST.

    Args:
        source_path: File that may contain import
        target_path: File that may be imported

    Returns:
        Confidence 0.0-1.0 (0.95 for explicit import, 0.0 if not found)
    """
    if not VETKA_JSON_CONTEXT_INCLUDE_IMPORTS:
        return 0.0

    # Only for Python files
    if not source_path.endswith(".py") or not target_path.endswith(".py"):
        return 0.0

    try:
        from pathlib import Path

        # Try to read source file
        source_file = Path(source_path)
        if not source_file.exists():
            return 0.0

        content = source_file.read_text(encoding="utf-8", errors="ignore")

        # Quick check: is target filename mentioned?
        target_name = Path(target_path).stem  # e.g., "utils" from "utils.py"
        if target_name not in content:
            return 0.0

        # Use PythonScanner for precise AST analysis
        from src.scanners.python_scanner import PythonScanner

        scanner = PythonScanner(
            project_root=Path.cwd(),
            scanned_files=[source_path, target_path],
            include_external=False,
        )

        # Extract imports
        imports = scanner.extract_imports_only(content, source_path)

        # Check if target is imported
        for imp in imports:
            # Check module name contains target
            if target_name in imp.module:
                # Higher confidence for explicit imports
                if imp.is_conditional:
                    return 0.7  # TYPE_CHECKING imports
                if imp.is_dynamic:
                    return 0.6  # Dynamic imports
                return 0.95  # Direct import

        return 0.0

    except Exception as e:
        logger.debug(f"[PHASE73.5] Import confidence check failed: {e}")
        return 0.0


def _calculate_dependencies_for_context(
    current_file_path: str, semantic_results: List[Dict]
) -> Dict[str, List[Dict]]:
    """
    Phase 73: Calculate dependency scores using DependencyCalculator.
    Phase 73.5: Enhanced with PythonScanner import_confidence.

    Args:
        current_file_path: Path of current file
        semantic_results: Results from Qdrant semantic search

    Returns:
        Dict with 'imports' and 'imported_by' lists
    """
    deps = {"imports": [], "imported_by": []}

    try:
        from src.scanners.dependency_calculator import (
            DependencyCalculator,
            FileMetadata,
            ScoringInput,
        )
        from datetime import datetime

        calculator = DependencyCalculator()

        # Build FileMetadata for current file
        target_file = FileMetadata(
            path=current_file_path,
            created_at=None,  # Could fetch from Qdrant payload
            rrf_score=0.5,
        )

        # Score each semantic neighbor as potential dependency
        for result in semantic_results:
            source_path = result.get("path", "")
            if not source_path:
                continue

            # Get timestamps from Qdrant result if available
            created_time = result.get("created_time", 0)
            source_created = (
                datetime.fromtimestamp(created_time) if created_time else None
            )

            source_file = FileMetadata(
                path=source_path, created_at=source_created, rrf_score=0.5
            )

            # [PHASE73.5-7] Get import confidence using PythonScanner
            import_confidence = _get_import_confidence(current_file_path, source_path)

            # Create scoring input with import confidence
            input_data = ScoringInput(
                source_file=source_file,
                target_file=target_file,
                import_confidence=import_confidence,
                semantic_score=result.get("score", 0.0),
                has_explicit_reference=import_confidence > 0.5,
            )

            scoring_result = calculator.calculate(input_data)

            if scoring_result.is_significant:
                dep_type = "import" if import_confidence > 0.5 else "semantic"
                deps["imports"].append(
                    {
                        "path": source_path,
                        "name": result.get("name", source_path.split("/")[-1]),
                        "score": round(scoring_result.final_score, 3),
                        "type": dep_type,
                        "import_conf": round(import_confidence, 2)
                        if import_confidence > 0
                        else None,
                    }
                )

            # [PHASE73.5-8] Check reverse: does source import target (imported_by)?
            if VETKA_JSON_CONTEXT_INCLUDE_IMPORTS:
                reverse_confidence = _get_import_confidence(
                    source_path, current_file_path
                )
                if reverse_confidence > 0.5:
                    deps["imported_by"].append(
                        {
                            "path": source_path,
                            "name": result.get("name", source_path.split("/")[-1]),
                            "confidence": round(reverse_confidence, 2),
                        }
                    )

        # Sort by score descending
        deps["imports"].sort(key=lambda x: x.get("score", 0), reverse=True)
        deps["imported_by"].sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return deps

    except ImportError as e:
        logger.debug(f"[PHASE73.5] DependencyCalculator import error: {e}")
        return deps
    except Exception as e:
        logger.warning(f"[PHASE73.5] Dependency calculation failed: {e}")
        return deps


def _extract_folder_focus(viewport_context: Dict) -> str:
    """
    Phase 73: Extract dominant folder from viewport context.

    Looks at visible and pinned nodes to determine which folder
    the user is focused on.

    Args:
        viewport_context: Dict with viewport_nodes, pinned_nodes

    Returns:
        Folder path string, or empty if undetermined
    """
    if not viewport_context:
        return ""

    # Collect all visible paths
    paths = []

    for node in viewport_context.get("pinned_nodes", []):
        path = node.get("path", "")
        if path:
            paths.append(path)

    for node in viewport_context.get("viewport_nodes", [])[:10]:
        path = node.get("path", "")
        if path:
            paths.append(path)

    if not paths:
        return ""

    # Find common prefix (folder)
    if len(paths) == 1:
        # Single file - return its parent folder
        parts = paths[0].rsplit("/", 1)
        return parts[0] if len(parts) > 1 else ""

    # Multiple paths - find common ancestor
    common = paths[0].split("/")
    for path in paths[1:]:
        parts = path.split("/")
        new_common = []
        for i, (a, b) in enumerate(zip(common, parts)):
            if a == b:
                new_common.append(a)
            else:
                break
        common = new_common

    return "/".join(common) if common else ""


def _truncate_json_context(context_data: Dict, max_tokens: int) -> Dict:
    """
    Phase 73: Truncate JSON context to fit token budget.

    Strategy: Remove items in order of least importance:
    1. Reduce semantic_neighbors
    2. Reduce dependencies
    3. Simplify viewport

    Args:
        context_data: Full JSON context dict
        max_tokens: Target token budget

    Returns:
        Truncated context dict
    """
    import json

    # First pass: reduce semantic neighbors
    while len(context_data.get("semantic_neighbors", [])) > 3:
        context_data["semantic_neighbors"] = context_data["semantic_neighbors"][:-1]
        json_str = json.dumps(context_data, ensure_ascii=False)
        if _estimate_tokens(json_str) <= max_tokens:
            return context_data

    # Second pass: reduce dependencies
    imports = context_data.get("dependencies", {}).get("imports", [])
    while len(imports) > 3:
        imports = imports[:-1]
        context_data["dependencies"]["imports"] = imports
        json_str = json.dumps(context_data, ensure_ascii=False)
        if _estimate_tokens(json_str) <= max_tokens:
            return context_data

    # Third pass: remove semantic neighbors entirely
    if context_data.get("semantic_neighbors"):
        context_data["semantic_neighbors"] = []
        context_data["summary"]["total_semantic_neighbors"] = 0
        json_str = json.dumps(context_data, ensure_ascii=False)
        if _estimate_tokens(json_str) <= max_tokens:
            return context_data

    # Final: minimal context
    return {
        "current_file": context_data.get("current_file", {}),
        "summary": {"truncated": True, "reason": "token_limit"},
    }


# ═══════════════════════════════════════════════════════════════════
# [PHASE71-M2] Phase 71: Viewport Context Summary for LLM
# ═══════════════════════════════════════════════════════════════════


def build_viewport_summary(
    viewport_context: Optional[Dict[str, Any]],
    max_visible_files: int = 15,
    max_pinned_files: int = 5,
) -> str:
    """
    Phase 71: Create text summary from viewport_context for LLM.

    Google Maps model:
    - Pinned nodes: full paths + type (highest priority)
    - Viewport nodes: closest N by distance (implicit context)
    - Stats: zoom level, camera position, total counts

    Args:
        viewport_context: Dict from frontend with camera_position, pinned_nodes, viewport_nodes
        max_visible_files: Maximum visible files to include in summary
        max_pinned_files: Maximum pinned files to include

    Returns:
        Formatted text summary for LLM prompt, or empty string if no context
    """
    if not viewport_context:
        return ""

    parts = []

    # === Camera position context (Google Maps zoom model) ===
    zoom = viewport_context.get("zoom_level", 0)
    cam_pos = viewport_context.get("camera_position", {})
    cam_target = viewport_context.get("camera_target", {})

    zoom_description = (
        "overview"
        if zoom <= 2
        else "medium"
        if zoom <= 5
        else "close-up"
        if zoom <= 8
        else "ultra-close"
    )
    parts.append(f"[Spatial Context] User viewing at zoom ~{zoom} ({zoom_description})")

    # === Pinned nodes (explicit selection - highest priority) ===
    pinned = viewport_context.get("pinned_nodes", [])
    if pinned:
        pinned_limited = pinned[:max_pinned_files]
        pinned_info = []
        for node in pinned_limited:
            name = node.get("name", "unknown")
            node_type = node.get("type", "file")
            distance = node.get("distance_to_camera", 0)
            lod = node.get("lod_level", 0)
            pinned_info.append(f"{name} ({node_type}, LOD={lod})")

        parts.append(f"[Pinned Files - User Selection] {', '.join(pinned_info)}")
        if len(pinned) > max_pinned_files:
            parts.append(f"  (+{len(pinned) - max_pinned_files} more pinned)")

    # === Viewport nodes (implicit - closest first, foveated priority) ===
    visible = viewport_context.get("viewport_nodes", [])
    if visible:
        # Already sorted by distance from frontend, but let's ensure
        sorted_visible = sorted(visible, key=lambda x: x.get("distance_to_camera", 999))

        # Prioritize center nodes (foveated)
        center_nodes = [n for n in sorted_visible if n.get("is_center", False)]
        other_nodes = [n for n in sorted_visible if not n.get("is_center", False)]

        # Take center first, then closest others
        selected = (
            center_nodes[:5]
            + other_nodes[: max_visible_files - min(5, len(center_nodes))]
        )
        selected = selected[:max_visible_files]

        visible_info = []
        for node in selected:
            name = node.get("name", "unknown")
            distance = node.get("distance_to_camera", 0)
            is_center = "★" if node.get("is_center", False) else ""
            visible_info.append(f"{is_center}{name} (d={distance:.0f})")

        parts.append(f"[Visible Files - In Viewport] {', '.join(visible_info)}")
        if len(visible) > max_visible_files:
            parts.append(
                f"  (+{len(visible) - max_visible_files} more visible in scene)"
            )

    # === Stats summary ===
    total_visible = viewport_context.get("total_visible", 0)
    total_pinned = viewport_context.get("total_pinned", 0)
    parts.append(
        f"[Stats] {total_pinned} pinned, {total_visible} visible in 3D viewport"
    )

    # Log for debugging
    logger.info(
        f"[VIEWPORT] Summary built: {total_pinned} pinned, {total_visible} visible, zoom ~{zoom}"
    )

    # MARKER_109_5_VIEWPORT_META: Add meta-info about viewport context assembly
    viewport_meta = f"""<viewport_meta>
  zoom: {zoom} ({zoom_description})
  lod_model: google_maps_foveated
  pinned_shown: {min(len(pinned), max_pinned_files) if pinned else 0}/{len(pinned) if pinned else 0}
  visible_shown: {min(len(visible), max_visible_files) if visible else 0}/{len(visible) if visible else 0}
  priority: center_first + distance_sorted
</viewport_meta>
"""

    return viewport_meta + "\n".join(parts) + "\n\n"


# Export all utilities
__all__ = [
    "format_history_for_prompt",
    "load_pinned_file_content",
    "build_pinned_context",
    "build_pinned_context_legacy",
    # Phase 67.2: Cache utilities
    "clear_relevance_cache",
    "get_cache_stats",
    # Phase 67.2: Config exports
    "QDRANT_WEIGHT",
    "CAM_WEIGHT",
    "MAX_CONTEXT_TOKENS",
    "MAX_TOKENS_PER_FILE",
    # Artifact Panel: Unlimited tokens
    "ARTIFACT_MAX_TOKENS_PER_FILE",
    # Phase 69: Max pinned files
    "VETKA_MAX_PINNED_FILES",
    # Phase 71: Viewport summary
    "build_viewport_summary",
    # [PHASE73-3] Phase 73: JSON Context Builder
    "build_json_context",
    "VETKA_JSON_CONTEXT_MAX_TOKENS",
    "VETKA_JSON_CONTEXT_INCLUDE_DEPS",
    "VETKA_JSON_CONTEXT_INCLUDE_SEMANTIC",
    # [PHASE73.5-9] Phase 73.5: ELISION compression + cache
    "VETKA_JSON_CONTEXT_COMPRESSED",
    "VETKA_JSON_CONTEXT_CACHE_SIZE",
    "VETKA_JSON_CONTEXT_INCLUDE_IMPORTS",
    "clear_json_context_cache",
    "get_json_context_cache_stats",
    # [PHASE73.6-7] Phase 73.6: Legend header
    "VETKA_JSON_CONTEXT_LEGEND_MODE",
    "ELISION_LEGEND_MAP",
    "reset_json_context_session",
    "get_legend_map",
    # [PHASE73.6.2] Per-model tracking (exported for testing)
    "_is_cold_start",
    "_mark_model_seen",
    "_should_include_legend",
]
