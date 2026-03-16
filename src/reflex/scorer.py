"""
REFLEX Scorer — Instant context-aware tool ranking without LLM calls.

MARKER_172.P2.SCORER

Layer 2 of REFLEX (Reactive Execution & Function Linking EXchange).
Pure math scoring on 8 memory signals → ranked tool recommendations in <5ms.

Signals (Phase 187.3 rebalanced — see docs/186_memory/GROK_RESEARCH_ANSWERS.md):
  1. Semantic match      (intent_tags vs task keywords)       weight: 0.22
  2. CAM surprise        (novelty boost from surprise_detector) weight: 0.12  + sparse boost ×1.5
  3. Feedback score      (CORTEX historical success, 0.5 default) weight: 0.18
  4. AURA preference     (user tool_usage_patterns)           weight: 0.07
  5. STM relevance       (working memory recency)             weight: 0.15
  6. Phase match         (fix/build/research alignment)       weight: 0.18
  7. HOPE LOD match      (zoom level → tool granularity)      weight: 0.05  + sparse boost ×1.5
  8. MGC cache heat      (Gen0 hot files → relevant tools)    weight: 0.03

NO LLM calls. NO external API. Pure in-memory scoring.

Part of VETKA OS:
  VETKA > REFLEX > Scorer (this file)

@status: active
@phase: 172.P2
@depends: reflex_registry, llm_model_registry
@used_by: fc_loop (IP-1), agent_pipeline (IP-4), session_init (IP-6)
"""

import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Set

logger = logging.getLogger(__name__)

# MARKER_178.1.6: REFLEX enabled by default (Phase 178)
REFLEX_ENABLED = os.getenv("REFLEX_ENABLED", "true").lower() in ("true", "1", "yes")

# --- MARKER_187.3: Rebalanced weights (Phase 187) ---
# See docs/186_memory/GROK_RESEARCH_ANSWERS.md for rationale.
# Σ = 1.00. Semantic down, phase+stm+feedback up, mgc kept at 0.03 (Opus: don't zero).
_W = {
    "semantic":  float(os.getenv("REFLEX_SEMANTIC_WEIGHT",  "0.22")),
    "cam":       float(os.getenv("REFLEX_CAM_WEIGHT",       "0.12")),
    "feedback":  float(os.getenv("REFLEX_FEEDBACK_WEIGHT",  "0.18")),
    "aura":      float(os.getenv("REFLEX_AURA_WEIGHT",      "0.07")),
    "stm":       float(os.getenv("REFLEX_STM_WEIGHT",       "0.15")),
    "phase":     float(os.getenv("REFLEX_PHASE_WEIGHT",     "0.18")),
    "hope":      float(os.getenv("REFLEX_HOPE_WEIGHT",      "0.05")),
    "mgc":       float(os.getenv("REFLEX_MGC_WEIGHT",       "0.03")),
}

# MARKER_187.3: Sparse signal boost — amplify strong CAM/HOPE signals
_SPARSE_BOOST_THRESHOLD = 0.7
_SPARSE_BOOST_MULTIPLIER = 1.5

# Default feedback score when no history exists (cold start)
_DEFAULT_FEEDBACK_SCORE = 0.5

# Model capability thresholds for tool palette adaptation
_SMALL_MODEL_CONTEXT = 8192      # ≤8k → restricted tool palette
_MEDIUM_MODEL_CONTEXT = 32768    # ≤32k → standard palette
# >32k → full palette


@dataclass
class ReflexContext:
    """
    MARKER_172.P2.CONTEXT

    All signals for REFLEX scoring, collected from VETKA memory stack.
    Constructed via from_subtask() or from_session() factories.
    """

    # Task description (for keyword/semantic matching)
    task_text: str = ""

    # Phase type: "research", "fix", "build"
    phase_type: str = "research"

    # Agent role: "coder", "researcher", "verifier", "architect", "scout"
    agent_role: str = "coder"

    # CAM surprise score (0.0-1.0, from surprise_detector)
    cam_surprise: float = 0.0

    # AURA user preferences: tool_usage_patterns
    # Dict of {tool_id: usage_count} or similar
    user_tool_prefs: Dict[str, float] = field(default_factory=dict)

    # STM items: list of recent content strings from working memory
    stm_items: List[str] = field(default_factory=list)

    # HOPE LOD level: "LOW", "MID", "HIGH" (from viewport zoom)
    hope_level: str = "MID"

    # MGC stats: {gen0_size, hit_rate, ...}
    mgc_stats: Dict[str, Any] = field(default_factory=dict)

    # Feedback scores: {tool_id: float} from CORTEX (Layer 3)
    # Empty dict = cold start, uses _DEFAULT_FEEDBACK_SCORE
    feedback_scores: Dict[str, float] = field(default_factory=dict)

    # Model capability (from LLMModelRegistry)
    model_context_length: int = 128000
    model_output_tps: float = 50.0

    # Extra context for custom scoring
    extra: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_subtask(
        subtask: Any,
        stm_items: Optional[List[str]] = None,
        cam_surprise: float = 0.0,
        user_tool_prefs: Optional[Dict[str, float]] = None,
        feedback_scores: Optional[Dict[str, float]] = None,
        hope_level: str = "MID",
        mgc_stats: Optional[Dict[str, Any]] = None,
        model_context_length: int = 128000,
        model_output_tps: float = 50.0,
    ) -> "ReflexContext":
        """Build ReflexContext from a pipeline Subtask object.

        Args:
            subtask: Subtask dataclass (from agent_pipeline.py)
            stm_items: Recent STM buffer contents
            cam_surprise: CAM surprise score for current context
            user_tool_prefs: AURA tool usage patterns
            feedback_scores: CORTEX per-tool historical scores
            hope_level: Current HOPE LOD level
            mgc_stats: MGC cache statistics
            model_context_length: From LLMModelRegistry.get_profile()
            model_output_tps: Model output speed (tokens/sec)
        """
        description = getattr(subtask, "description", "") or ""
        context = getattr(subtask, "context", None) or {}

        # Extract phase_type from context or default
        phase_type = context.get("phase_type", "research")

        return ReflexContext(
            task_text=description,
            phase_type=phase_type,
            agent_role=context.get("agent_role", "coder"),
            cam_surprise=cam_surprise,
            user_tool_prefs=user_tool_prefs or {},
            stm_items=stm_items or [],
            hope_level=hope_level,
            mgc_stats=mgc_stats or {},
            feedback_scores=feedback_scores or {},
            model_context_length=model_context_length,
            model_output_tps=model_output_tps,
        )

    @staticmethod
    def from_session(
        session_data: Dict[str, Any],
        task_text: str = "",
        phase_type: str = "research",
        feedback_scores: Optional[Dict[str, float]] = None,
        model_context_length: int = 128000,
        model_output_tps: float = 50.0,
    ) -> "ReflexContext":
        """Build ReflexContext from vetka_session_init response.

        Args:
            session_data: Result dict from vetka_session_init
            task_text: Current task (may not be known at session start)
            phase_type: Default phase type
            feedback_scores: CORTEX scores (may not be loaded at session start)
            model_context_length: From LLMModelRegistry
            model_output_tps: Model speed
        """
        # Extract viewport zoom → HOPE level
        viewport = session_data.get("viewport", {})
        zoom = viewport.get("zoom", 0.5)
        if zoom < 0.3:
            hope_level = "LOW"
        elif zoom > 1.0:
            hope_level = "HIGH"
        else:
            hope_level = "MID"

        # Extract user tool preferences from AURA
        user_prefs = session_data.get("user_preferences", {})
        tool_prefs: Dict[str, float] = {}
        if isinstance(user_prefs, dict) and user_prefs.get("has_preferences"):
            # Try to extract tool_usage_patterns from preferences
            comm_style = session_data.get("communication_style", {})
            # tool_usage_patterns would be in a dedicated field
            tool_prefs = user_prefs.get("tool_usage_patterns", {})

        return ReflexContext(
            task_text=task_text,
            phase_type=phase_type,
            agent_role="coder",
            cam_surprise=0.0,  # Not available at session start
            user_tool_prefs=tool_prefs,
            stm_items=[],  # STM empty at session start
            hope_level=hope_level,
            mgc_stats={},
            feedback_scores=feedback_scores or {},
            model_context_length=model_context_length,
            model_output_tps=model_output_tps,
        )


@dataclass
class ScoredTool:
    """A tool with its REFLEX score and reasoning breakdown."""
    tool_id: str
    score: float                          # 0.0 - 1.0
    reason: str                           # Human-readable: "semantic: 0.89, phase: 1.0"
    source_signals: Dict[str, float]      # Per-signal breakdown


class ReflexScorer:
    """
    MARKER_172.P2.SCORER

    REFLEX Layer 2: Pure math scoring engine.
    No LLM calls. No external API. Target: <5ms per recommendation batch.

    Usage:
        scorer = ReflexScorer()
        scored = scorer.recommend(context, tools, top_n=5)
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """Initialize scorer with optional weight overrides.

        Args:
            weights: Override default signal weights. Keys: semantic, cam,
                     feedback, aura, stm, phase, hope, mgc.
        """
        self._weights = dict(_W)
        if weights:
            self._weights.update(weights)

    def recommend(
        self,
        context: ReflexContext,
        available_tools: list,
        top_n: int = 5,
        min_score: float = 0.1,
    ) -> List[ScoredTool]:
        """Rank tools by context relevance. Returns top-N sorted descending.

        Args:
            context: ReflexContext with all memory signals
            available_tools: List of ToolEntry objects from ReflexRegistry
            top_n: Maximum tools to return
            min_score: Minimum score threshold

        Returns:
            List[ScoredTool] sorted by score descending, up to top_n items.
        """
        if not REFLEX_ENABLED:
            return []

        if not available_tools or not context:
            return []

        # Model capability filter
        capability = self._model_capability(context)

        scored: List[ScoredTool] = []
        for tool in available_tools:
            if not getattr(tool, "active", True):
                continue

            # Skip heavy tools for small models
            if capability == "small":
                risk = getattr(tool, "cost", {}).get("risk_level", "read_only")
                if risk in ("execute", "external"):
                    continue

            signals = self.score_signals(tool, context)
            total = self._weighted_sum(signals)

            if total >= min_score:
                reason_parts = [f"{k}: {v:.2f}" for k, v in signals.items() if v > 0]
                scored.append(ScoredTool(
                    tool_id=getattr(tool, "tool_id", str(tool)),
                    score=round(total, 4),
                    reason=", ".join(reason_parts),
                    source_signals=signals,
                ))

        # Sort descending by score
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:top_n]

    def score(self, tool: Any, context: ReflexContext) -> float:
        """Score a single tool against context. Returns 0.0-1.0."""
        if not REFLEX_ENABLED:
            return 0.0
        signals = self.score_signals(tool, context)
        return round(self._weighted_sum(signals), 4)

    def score_signals(self, tool: Any, context: ReflexContext) -> Dict[str, float]:
        """Compute all 8 signal scores for a tool. Each returns 0.0-1.0."""
        return {
            "semantic":  self._semantic_match(tool, context),
            "cam":       self._cam_relevance(tool, context),
            "feedback":  self._feedback_score(tool, context),
            "aura":      self._aura_preference(tool, context),
            "stm":       self._stm_relevance(tool, context),
            "phase":     self._phase_match(tool, context),
            "hope":      self._hope_lod_match(tool, context),
            "mgc":       self._mgc_heat(tool, context),
        }

    def _weighted_sum(self, signals: Dict[str, float]) -> float:
        """Weighted sum of all signals with sparse signal boost. Result is 0.0-1.0.

        MARKER_187.3: CAM and HOPE signals > 0.7 get ×1.5 multiplier
        to reward strong sparse signals that would otherwise be drowned out.
        """
        total = 0.0
        for key, value in signals.items():
            weight = self._weights.get(key, 0.0)
            # Phase 187 sparse boost: amplify strong CAM/HOPE signals
            if key in ("cam", "hope") and value > _SPARSE_BOOST_THRESHOLD:
                value = min(1.0, value * _SPARSE_BOOST_MULTIPLIER)
            total += value * weight
        return min(1.0, max(0.0, total))

    # --- 8 Signal Scorers ---

    def _semantic_match(self, tool: Any, context: ReflexContext) -> float:
        """Signal 1: Keyword/intent overlap between task and tool.

        Uses ToolEntry.matches_keywords() and intent_tags matching.
        Pure string matching, no embeddings (embeddings are for Phase 172.P5 tuning).
        """
        if not context.task_text:
            return 0.0

        tool_id = getattr(tool, "tool_id", "")
        text = context.task_text.lower()

        # Score from ToolEntry.matches_keywords (trigger_patterns.keywords)
        kw_score = 0.0
        if hasattr(tool, "matches_keywords"):
            kw_score = tool.matches_keywords(context.task_text)

        # Score from intent_tags overlap with task words
        intent_tags = getattr(tool, "intent_tags", [])
        if intent_tags:
            task_words = set(text.split())
            tag_set = set(t.lower() for t in intent_tags)
            overlap = task_words & tag_set
            intent_score = len(overlap) / len(tag_set) if tag_set else 0.0
        else:
            intent_score = 0.0

        # Combine: max of keyword match and intent overlap
        return min(1.0, max(kw_score, intent_score))

    def _cam_relevance(self, tool: Any, context: ReflexContext) -> float:
        """Signal 2: CAM surprise boost.

        High surprise (>0.7) = novel context → broaden tool palette (boost all).
        Low surprise (<0.3) = predictable → prefer proven tools.
        Medium = neutral (0.5 baseline).
        """
        surprise = context.cam_surprise
        if surprise >= 0.7:
            return 1.0   # Novel context: all tools get boosted equally
        elif surprise >= 0.3:
            return 0.5   # Normal
        else:
            return 0.3   # Predictable: slight penalty (prefer feedback winners)

    def _feedback_score(self, tool: Any, context: ReflexContext) -> float:
        """Signal 3: Historical success from CORTEX feedback loop.

        Returns the CORTEX aggregated score if available.
        Cold start: _DEFAULT_FEEDBACK_SCORE (0.5).
        """
        tool_id = getattr(tool, "tool_id", "")
        if context.feedback_scores and tool_id in context.feedback_scores:
            return min(1.0, max(0.0, context.feedback_scores[tool_id]))
        return _DEFAULT_FEEDBACK_SCORE

    def _aura_preference(self, tool: Any, context: ReflexContext) -> float:
        """Signal 4: User preference from AURA tool_usage_patterns.

        Frequently used tools score higher. Normalized to 0-1.
        """
        tool_id = getattr(tool, "tool_id", "")
        prefs = context.user_tool_prefs
        if not prefs or tool_id not in prefs:
            return 0.0

        usage = prefs[tool_id]
        # Normalize: usage count → 0-1 scale (sigmoid-like, saturates at ~20 uses)
        if isinstance(usage, (int, float)) and usage > 0:
            return min(1.0, usage / 20.0)
        return 0.0

    def _stm_relevance(self, tool: Any, context: ReflexContext) -> float:
        """Signal 5: Working memory recency.

        If any STM item mentions this tool's domain, boost it.
        """
        if not context.stm_items:
            return 0.0

        tool_id = getattr(tool, "tool_id", "")
        intent_tags = getattr(tool, "intent_tags", [])

        # Check if tool_id or any intent_tag appears in recent STM items
        search_terms = {tool_id.lower()}
        search_terms.update(t.lower() for t in intent_tags)

        stm_text = " ".join(context.stm_items).lower()
        hits = sum(1 for term in search_terms if term and term in stm_text)

        if hits == 0:
            return 0.0
        return min(1.0, hits / max(1, len(search_terms)))

    def _phase_match(self, tool: Any, context: ReflexContext) -> float:
        """Signal 6: Phase type alignment.

        ToolEntry.trigger_patterns.phase_types must include current phase.
        """
        if hasattr(tool, "matches_phase"):
            return 1.0 if tool.matches_phase(context.phase_type) else 0.0

        # Fallback: check trigger_patterns directly
        trigger = getattr(tool, "trigger_patterns", {})
        phases = trigger.get("phase_types", ["*"])
        if "*" in phases:
            return 1.0
        return 1.0 if context.phase_type.lower() in [p.lower() for p in phases] else 0.0

    def _hope_lod_match(self, tool: Any, context: ReflexContext) -> float:
        """Signal 7: Zoom level → tool granularity.

        LOW zoom (overview): prefer search/overview tools
        HIGH zoom (detail): prefer file_op/write tools
        MID: neutral (0.5)
        """
        kind = getattr(tool, "kind", "unknown")
        level = context.hope_level.upper()

        if level == "LOW":
            # Overview mode: prefer search, orchestration
            return 1.0 if kind in ("search", "orchestration", "system") else 0.3
        elif level == "HIGH":
            # Detail mode: prefer file ops, media, write tools
            return 1.0 if kind in ("file_op", "media", "memory") else 0.3
        else:
            return 0.5  # MID = neutral

    def _mgc_heat(self, tool: Any, context: ReflexContext) -> float:
        """Signal 8: MGC cache generation heat.

        High hit_rate + large Gen0 = hot context → file-related tools score higher.
        """
        stats = context.mgc_stats
        if not stats:
            return 0.3  # No data = neutral-low

        hit_rate = stats.get("hit_rate", 0.0)
        gen0_size = stats.get("gen0_size", 0)
        gen0_max = stats.get("gen0_max", 100)

        # Heat: combination of hit rate and Gen0 fullness
        heat = (hit_rate * 0.6) + (min(1.0, gen0_size / max(1, gen0_max)) * 0.4)

        kind = getattr(tool, "kind", "unknown")
        if kind in ("file_op", "search"):
            return heat  # File tools benefit from hot cache
        return heat * 0.5  # Other tools get partial benefit

    # --- Model Capability Adaptation (P2.7) ---

    def _model_capability(self, context: ReflexContext) -> str:
        """Classify model capability for tool palette filtering.

        Uses LLMModelRegistry profile data (context_length, output_tps).
        Does NOT call LLMModelRegistry — reads values from ReflexContext
        (populated by caller from get_llm_registry().get_profile()).

        Returns: "small", "medium", "large"
        """
        ctx_len = context.model_context_length
        if ctx_len <= _SMALL_MODEL_CONTEXT:
            return "small"
        elif ctx_len <= _MEDIUM_MODEL_CONTEXT:
            return "medium"
        return "large"

    # --- Convenience methods ---

    def recommend_for_role(
        self,
        role: str,
        context: ReflexContext,
        registry: Any = None,
        top_n: int = 5,
    ) -> List[ScoredTool]:
        """Recommend tools for a specific agent role.

        Args:
            role: Agent role (e.g., "coder", "Dev", "researcher")
            context: ReflexContext
            registry: ReflexRegistry instance (imports lazily if None)
            top_n: Max tools to return
        """
        if not REFLEX_ENABLED:
            return []

        if registry is None:
            try:
                from src.services.reflex_registry import get_reflex_registry
                registry = get_reflex_registry()
            except ImportError:
                logger.warning("[REFLEX] Cannot import reflex_registry")
                return []

        tools = registry.get_tools_for_role(role)
        context.agent_role = role
        return self.recommend(context, tools, top_n=top_n)

    def recommend_for_session(
        self,
        session_data: Dict[str, Any],
        phase_type: str = "research",
        top_n: int = 10,
    ) -> List[ScoredTool]:
        """Recommend tools for session_init response (IP-6).

        Builds ReflexContext from session data, returns broad recommendations.
        """
        if not REFLEX_ENABLED:
            return []

        context = ReflexContext.from_session(
            session_data, phase_type=phase_type
        )

        try:
            from src.services.reflex_registry import get_reflex_registry
            registry = get_reflex_registry()
            tools = registry.get_all_tools()
        except ImportError:
            logger.warning("[REFLEX] Cannot import reflex_registry")
            return []

        return self.recommend(context, tools, top_n=top_n)


# --- Singleton ---

_scorer_instance: Optional[ReflexScorer] = None


def get_reflex_scorer() -> ReflexScorer:
    """Get or create singleton ReflexScorer."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = ReflexScorer()
    return _scorer_instance


def reset_reflex_scorer() -> None:
    """Reset singleton (for testing)."""
    global _scorer_instance
    _scorer_instance = None
