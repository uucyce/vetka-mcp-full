"""
VETKA Context Fusion — Bridge between 3D Viewport and Code Context

This module bridges two context sources:
1. VETKA context (3D viewport, pinned files, spatial awareness)
2. Code context (Elysia tool results, file operations)

The context_fusion() function creates a unified context string for LLM,
prioritizing spatial (VETKA) context while including code context when needed.

Architecture:
    ┌─────────────────────────────────────────────────────┐
    │              context_fusion() [75.3]                 │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
    │  │  viewport   │  │   pinned    │  │     CAM     │  │
    │  │   context   │  │    files    │  │  activations│  │
    │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  │
    │         └────────────────┼────────────────┘         │
    │                          ▼                          │
    │              Unified Context (≤2000 tokens)         │
    └─────────────────────────────────────────────────────┘

Token Budget:
- Spatial context: 300 tokens
- Pinned files summary: 400 tokens
- CAM hints: 100 tokens
- Code context: 1200 tokens (lazy, only if needed)
- Total: ≤2000 tokens

@status: active
@phase: 98
@depends: src.orchestration.cam_engine, src.agents.hope_enhancer
@used_by: src.orchestration.langgraph_nodes, src.agents.hostess_agent

FIX_98.1: Added HOPE (Hierarchical Optimized Processing) integration.
HOPE provides frequency-based context layers (LOW/MID/HIGH) for matryoshka-style
context enrichment, enabling richer semantic context at multiple granularities.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("VETKA_FUSION")

# ═══════════════════════════════════════════════════════════════════
# [PHASE75.3-1] Configuration
# ═══════════════════════════════════════════════════════════════════

# Token budgets (configurable via env)
FUSION_MAX_TOKENS = int(os.getenv("VETKA_FUSION_MAX_TOKENS", "2000"))
FUSION_SPATIAL_TOKENS = int(os.getenv("VETKA_FUSION_SPATIAL_TOKENS", "300"))
FUSION_PINNED_TOKENS = int(os.getenv("VETKA_FUSION_PINNED_TOKENS", "400"))
FUSION_CAM_TOKENS = int(os.getenv("VETKA_FUSION_CAM_TOKENS", "100"))
FUSION_HOPE_TOKENS = int(os.getenv("VETKA_FUSION_HOPE_TOKENS", "300"))  # FIX_98.1
FUSION_CODE_TOKENS = int(os.getenv("VETKA_FUSION_CODE_TOKENS", "1200"))

# Include code context only when query matches these patterns
CODE_CONTEXT_KEYWORDS = [
    "read",
    "write",
    "edit",
    "code",
    "file",
    "test",
    "commit",
    "function",
    "class",
    "import",
    "bug",
    "fix",
    "implement",
    "прочитай",
    "напиши",
    "исправь",
    "код",
    "файл",
    "тест",
]


# ═══════════════════════════════════════════════════════════════════
# [PHASE75.3-2] Main Fusion Function
# ═══════════════════════════════════════════════════════════════════


def context_fusion(
    viewport_context: Optional[Dict[str, Any]] = None,
    pinned_files: Optional[List[Dict[str, Any]]] = None,
    code_context: Optional[Dict[str, Any]] = None,
    cam_activations: Optional[Dict[str, float]] = None,
    hope_context: Optional[Dict[str, str]] = None,  # FIX_98.1: HOPE layers
    user_query: str = "",
    max_tokens: int = FUSION_MAX_TOKENS,
    include_code: Optional[bool] = None,
) -> str:
    """
    Fuse 3D viewport context and code context for LLM.

    This is the heart of Phase 75's hybrid architecture.
    Creates a unified context string that gives LLM spatial awareness
    while providing code context only when needed.

    Priority Order:
    1. Spatial context (viewport position, zoom level, camera target)
    2. Pinned files (user's explicit selection - highest priority)
    3. CAM activation hints (JARVIS-style suggestions)
    4. Code context (lazy - only if query is code-related)

    Args:
        viewport_context: Dict from frontend with:
            - camera_position: {x, y, z}
            - camera_target: {x, y, z} or file path
            - zoom_level: 0-10 scale
            - total_visible: number of visible nodes
            - total_pinned: number of pinned nodes
        pinned_files: List of {id, path, name, type} dicts
        code_context: Dict with:
            - summary: brief description of code state
            - last_operation: last Elysia tool used
            - files_modified: list of modified files
        cam_activations: Dict mapping tool_name -> activation_score
        user_query: User's query (for code context detection)
        max_tokens: Maximum tokens for output (default 2000)
        include_code: Force include/exclude code context (None = auto-detect)

    Returns:
        Unified context string formatted for LLM, or empty string if no context

    Example Output:
        ## SPATIAL CONTEXT
        User viewing at zoom ~5 (medium). Camera focused on: src/orchestration/
        Visible: 23 files, Pinned: 3 files

        ## PINNED FILES (User Selection)
        1. cam_engine.py (Python, 881 lines)
        2. langgraph_nodes.py (Python, 906 lines)
        3. middleware.py (Python, 288 lines)

        ## CAM SUGGESTION
        CAM suggests: search_files (activation: 0.85)

        ## CODE CONTEXT
        Last operation: read_file(cam_engine.py)
        Modified: [none]
    """
    sections = []
    total_tokens = 0

    # ───────────────────────────────────────────────────────────────
    # Section 1: Spatial Context (highest priority)
    # ───────────────────────────────────────────────────────────────
    spatial_section = _build_spatial_section(viewport_context)
    if spatial_section:
        spatial_tokens = _estimate_tokens(spatial_section)
        if total_tokens + spatial_tokens <= max_tokens:
            sections.append(spatial_section)
            total_tokens += spatial_tokens

    # ───────────────────────────────────────────────────────────────
    # Section 2: Pinned Files (user's explicit selection)
    # ───────────────────────────────────────────────────────────────
    pinned_section = _build_pinned_section(pinned_files)
    if pinned_section:
        pinned_tokens = _estimate_tokens(pinned_section)
        if total_tokens + pinned_tokens <= max_tokens:
            sections.append(pinned_section)
            total_tokens += pinned_tokens

    # ───────────────────────────────────────────────────────────────
    # Section 3: CAM Activation Hints (JARVIS-style)
    # ───────────────────────────────────────────────────────────────
    cam_section = _build_cam_section(cam_activations)
    if cam_section:
        cam_tokens = _estimate_tokens(cam_section)
        if total_tokens + cam_tokens <= max_tokens:
            sections.append(cam_section)
            total_tokens += cam_tokens

    # ───────────────────────────────────────────────────────────────
    # Section 4: HOPE Context (FIX_98.1: Hierarchical Processing)
    # ───────────────────────────────────────────────────────────────
    hope_section = _build_hope_section(hope_context)
    if hope_section:
        hope_tokens = _estimate_tokens(hope_section)
        if total_tokens + hope_tokens <= max_tokens:
            sections.append(hope_section)
            total_tokens += hope_tokens

    # ───────────────────────────────────────────────────────────────
    # Section 5: Code Context (lazy - only if needed)
    # ───────────────────────────────────────────────────────────────
    should_include_code = include_code
    if should_include_code is None:
        # Auto-detect based on user query
        should_include_code = _is_code_related_query(user_query)

    if should_include_code and code_context:
        remaining_tokens = max_tokens - total_tokens
        code_section = _build_code_section(code_context, max_tokens=remaining_tokens)
        if code_section:
            sections.append(code_section)
            total_tokens += _estimate_tokens(code_section)

    # ───────────────────────────────────────────────────────────────
    # Assemble final context
    # ───────────────────────────────────────────────────────────────
    if not sections:
        return ""

    result = "\n\n".join(sections)

    logger.info(
        f"[Fusion] Built context: {total_tokens} tokens, "
        f"{len(sections)} sections, code={should_include_code}"
    )

    return result


# ═══════════════════════════════════════════════════════════════════
# [PHASE75.3-3] Section Builders
# ═══════════════════════════════════════════════════════════════════


def _build_spatial_section(viewport_context: Optional[Dict[str, Any]]) -> str:
    """Build spatial context section from viewport data."""
    if not viewport_context:
        return ""

    parts = ["## SPATIAL CONTEXT"]

    # Zoom level description
    zoom = viewport_context.get("zoom_level", 0)
    zoom_desc = _zoom_to_description(zoom)

    # Camera target
    camera_target = viewport_context.get("camera_target", {})
    if isinstance(camera_target, dict):
        # 3D coordinates
        target_str = f"({camera_target.get('x', 0):.0f}, {camera_target.get('y', 0):.0f}, {camera_target.get('z', 0):.0f})"
    elif isinstance(camera_target, str):
        # File/folder path
        target_str = camera_target
    else:
        target_str = "unknown"

    parts.append(
        f"User viewing at zoom ~{zoom} ({zoom_desc}). Camera focused on: {target_str}"
    )

    # Stats
    total_visible = viewport_context.get("total_visible", 0)
    total_pinned = viewport_context.get("total_pinned", 0)
    parts.append(f"Visible: {total_visible} files, Pinned: {total_pinned} files")

    # Folder focus (if available)
    folder_focus = viewport_context.get("folder_focus", "")
    if folder_focus:
        parts.append(f"Folder focus: {folder_focus}")

    return "\n".join(parts)


def _build_pinned_section(pinned_files: Optional[List[Dict[str, Any]]]) -> str:
    """Build pinned files section."""
    if not pinned_files:
        return ""

    parts = ["## PINNED FILES (User Selection)"]

    # Limit to top 5 pinned files
    for i, pf in enumerate(pinned_files[:5], 1):
        name = pf.get("name", "unknown")
        file_type = pf.get("type", "file")
        path = pf.get("path", "")

        # Infer language from extension
        ext = name.split(".")[-1] if "." in name else ""
        lang_map = {
            "py": "Python",
            "ts": "TypeScript",
            "tsx": "React/TSX",
            "js": "JavaScript",
            "jsx": "React/JSX",
            "md": "Markdown",
            "json": "JSON",
            "yaml": "YAML",
            "yml": "YAML",
        }
        lang = lang_map.get(ext.lower(), ext.upper() if ext else "File")

        parts.append(f"{i}. {name} ({lang})")

    if len(pinned_files) > 5:
        parts.append(f"   ... and {len(pinned_files) - 5} more pinned")

    return "\n".join(parts)


def _build_cam_section(cam_activations: Optional[Dict[str, float]]) -> str:
    """Build CAM activation hints section."""
    if not cam_activations:
        return ""

    # Find top suggestion
    top_tools = sorted(cam_activations.items(), key=lambda x: x[1], reverse=True)

    if not top_tools or top_tools[0][1] < 0.5:
        return ""  # No strong suggestion

    parts = ["## CAM SUGGESTION"]

    top_tool, score = top_tools[0]
    parts.append(f"CAM suggests: {top_tool} (activation: {score:.2f})")

    # Add secondary suggestions if strong enough
    if len(top_tools) > 1 and top_tools[1][1] >= 0.6:
        second_tool, second_score = top_tools[1]
        parts.append(f"Alternative: {second_tool} ({second_score:.2f})")

    return "\n".join(parts)


def _build_hope_section(hope_context: Optional[Dict[str, str]]) -> str:
    """
    Build HOPE (Hierarchical Optimized Processing) context section.

    FIX_98.1: Integrates frequency-based context layers for matryoshka-style
    context enrichment. HOPE provides LOW/MID/HIGH granularity levels.

    Args:
        hope_context: Dict with keys:
            - summary: LOW layer (global overview, ~200 words)
            - detailed: MID layer (detailed context, ~400 words)
            - specific: HIGH layer (specific details, ~600 words)
            - full: Original content (for reference)

    Returns:
        Formatted HOPE section string
    """
    if not hope_context:
        return ""

    parts = ["## HOPE CONTEXT (Hierarchical Layers)"]

    # LOW layer - always include if available (brief overview)
    summary = hope_context.get('summary', '')
    if summary:
        # Truncate to budget
        max_chars = FUSION_HOPE_TOKENS * 3  # ~3 chars per token
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."
        parts.append(f"**Overview:** {summary}")

    # MID layer - include if space permits and available
    detailed = hope_context.get('detailed', '')
    if detailed and len(detailed) > len(summary):
        # Only add if it provides more context than summary
        mid_preview = detailed[:200] + "..." if len(detailed) > 200 else detailed
        parts.append(f"**Detail hint:** {mid_preview}")

    # HIGH layer - skip in context_fusion (too verbose), used in jarvis enricher

    if len(parts) == 1:  # Only header, no content
        return ""

    return "\n".join(parts)


def _build_code_section(
    code_context: Dict[str, Any], max_tokens: int = FUSION_CODE_TOKENS
) -> str:
    """Build code context section."""
    if not code_context:
        return ""

    parts = ["## CODE CONTEXT"]

    # Summary
    summary = code_context.get("summary", "")
    if summary:
        # Truncate if too long
        max_summary_chars = max_tokens * 3  # ~3 chars per token
        if len(summary) > max_summary_chars:
            summary = summary[:max_summary_chars] + "..."
        parts.append(summary)

    # Last operation
    last_op = code_context.get("last_operation", "")
    if last_op:
        parts.append(f"Last operation: {last_op}")

    # Files modified
    modified = code_context.get("files_modified", [])
    if modified:
        if len(modified) <= 3:
            parts.append(f"Modified: {', '.join(modified)}")
        else:
            parts.append(
                f"Modified: {', '.join(modified[:3])} (+{len(modified) - 3} more)"
            )
    else:
        parts.append("Modified: [none]")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════
# [PHASE75.3-4] Utility Functions
# ═══════════════════════════════════════════════════════════════════


# FIX_97.1: Consolidated to src/utils/token_utils.py
from src.utils.token_utils import estimate_tokens as _estimate_tokens


def _zoom_to_description(zoom: float) -> str:
    """Convert zoom level to human description."""
    if zoom <= 2:
        return "overview"
    elif zoom <= 5:
        return "medium"
    elif zoom <= 8:
        return "close-up"
    else:
        return "ultra-close"


def _is_code_related_query(query: str) -> bool:
    """Check if query is code-related (should include code context)."""
    if not query:
        return False

    query_lower = query.lower()
    return any(kw in query_lower for kw in CODE_CONTEXT_KEYWORDS)


# ═══════════════════════════════════════════════════════════════════
# [PHASE75.3-5] Integration Helpers
# ═══════════════════════════════════════════════════════════════════


def get_cam_activations_for_fusion(context: Dict[str, Any]) -> Dict[str, float]:
    """
    Get CAM activations formatted for context_fusion.

    Bridges CAMToolMemory (Phase 75.1) with context_fusion.

    Args:
        context: Context dict with folder_path, file_extension, etc.

    Returns:
        Dict mapping tool_name -> activation_score
    """
    try:
        from src.orchestration.cam_engine import get_cam_tool_memory

        tool_memory = get_cam_tool_memory()
        suggestions = tool_memory.suggest_tool(context, top_n=3)

        return {tool: score for tool, score in suggestions}

    except Exception as e:
        logger.warning(f"[Fusion] Failed to get CAM activations: {e}")
        return {}


def build_context_for_hostess(
    viewport_context: Optional[Dict[str, Any]] = None,
    pinned_files: Optional[List[Dict[str, Any]]] = None,
    user_query: str = "",
) -> str:
    """
    Build context for Hostess node (routing decisions).

    Includes CAM activations automatically.

    Args:
        viewport_context: Viewport data from frontend
        pinned_files: Pinned files list
        user_query: User's query

    Returns:
        Fused context string
    """
    # Extract context for CAM
    cam_context = {}
    if viewport_context:
        cam_context["viewport_zoom"] = viewport_context.get("zoom_level", 0)
        cam_context["folder_path"] = viewport_context.get("folder_focus", "")

    if pinned_files and len(pinned_files) > 0:
        first_pinned = pinned_files[0]
        ext = first_pinned.get("name", "").split(".")[-1]
        cam_context["file_extension"] = ext

    # Get CAM activations
    cam_activations = get_cam_activations_for_fusion(cam_context)

    return context_fusion(
        viewport_context=viewport_context,
        pinned_files=pinned_files,
        cam_activations=cam_activations,
        user_query=user_query,
        include_code=False,  # Hostess doesn't need code context
        max_tokens=999999,  # Unlimited responses
    )


def build_context_for_dev(
    viewport_context: Optional[Dict[str, Any]] = None,
    pinned_files: Optional[List[Dict[str, Any]]] = None,
    code_context: Optional[Dict[str, Any]] = None,
    user_query: str = "",
) -> str:
    """
    Build context for Dev node (code implementation).

    Always includes code context.

    Args:
        viewport_context: Viewport data from frontend
        pinned_files: Pinned files list
        code_context: Code operation context
        user_query: User's query

    Returns:
        Fused context string
    """
    # Extract context for CAM
    cam_context = {}
    if viewport_context:
        cam_context["viewport_zoom"] = viewport_context.get("zoom_level", 0)
        cam_context["folder_path"] = viewport_context.get("folder_focus", "")

    if pinned_files and len(pinned_files) > 0:
        first_pinned = pinned_files[0]
        ext = first_pinned.get("name", "").split(".")[-1]
        cam_context["file_extension"] = ext

    # Get CAM activations
    cam_activations = get_cam_activations_for_fusion(cam_context)

    return context_fusion(
        viewport_context=viewport_context,
        pinned_files=pinned_files,
        code_context=code_context,
        cam_activations=cam_activations,
        user_query=user_query,
        include_code=True,  # Dev always needs code context
        max_tokens=FUSION_MAX_TOKENS,
    )


# ═══════════════════════════════════════════════════════════════════
# [PHASE75.3-6] Stats and Debugging
# ═══════════════════════════════════════════════════════════════════


def get_fusion_stats() -> Dict[str, Any]:
    """Get context fusion configuration stats."""
    return {
        "max_tokens": FUSION_MAX_TOKENS,
        "spatial_budget": FUSION_SPATIAL_TOKENS,
        "pinned_budget": FUSION_PINNED_TOKENS,
        "cam_budget": FUSION_CAM_TOKENS,
        "hope_budget": FUSION_HOPE_TOKENS,  # FIX_98.1
        "code_budget": FUSION_CODE_TOKENS,
        "code_keywords": CODE_CONTEXT_KEYWORDS,
    }


# ═══════════════════════════════════════════════════════════════════
# Module Exports
# ═══════════════════════════════════════════════════════════════════

__all__ = [
    # Main function
    "context_fusion",
    # Integration helpers
    "build_context_for_hostess",
    "build_context_for_dev",
    "get_cam_activations_for_fusion",
    # Utilities
    "get_fusion_stats",
    # Configuration
    "FUSION_MAX_TOKENS",
    "FUSION_SPATIAL_TOKENS",
    "FUSION_PINNED_TOKENS",
    "FUSION_CAM_TOKENS",
    "FUSION_HOPE_TOKENS",  # FIX_98.1
    "FUSION_CODE_TOKENS",
]
