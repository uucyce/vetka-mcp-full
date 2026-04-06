"""
REFLEX Scorer — Instant context-aware tool ranking without LLM calls.

MARKER_172.P2.SCORER

Layer 2 of REFLEX (Reactive Execution & Function Linking EXchange).
Pure math scoring on 8 memory signals → ranked tool recommendations in <5ms.

Signals (Phase 187.3 rebalanced — see docs/186_memory/GROK_RESEARCH_ANSWERS.md):
  1. Semantic match      (intent_tags vs task keywords)       weight: 0.14  [was 0.22, -0.08 for Signal 9]
  2. CAM surprise        (novelty boost from surprise_detector) weight: 0.12  + sparse boost ×1.5
  3. Feedback score      (CORTEX historical success, 0.5 default) weight: 0.18
  4. ENGRAM preference   (user tool_usage_patterns)           weight: 0.07
  5. STM relevance       (working memory recency)             weight: 0.15
  6. Phase match         (fix/build/research alignment)       weight: 0.18
  7. HOPE LOD match      (zoom level → tool granularity)      weight: 0.05  + sparse boost ×1.5
  8. MGC cache heat      (Gen0 hot files → relevant tools)    weight: 0.03
  9. Weaviate similarity (embedding match via elysia_tools)   weight: 0.08  fallback → 0.0 (MARKER_198.P3.2)

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
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# MARKER_178.1.6: REFLEX enabled by default (Phase 178)
REFLEX_ENABLED = os.getenv("REFLEX_ENABLED", "true").lower() in ("true", "1", "yes")

# --- MARKER_187.3: Rebalanced weights (Phase 187) ---
# See docs/186_memory/GROK_RESEARCH_ANSWERS.md for rationale.
# Σ = 1.00. Semantic down, phase+stm+feedback up, mgc kept at 0.03 (Opus: don't zero).
_W = {
    "semantic":  float(os.getenv("REFLEX_SEMANTIC_WEIGHT",  "0.14")),  # was 0.22, -0.08 for Signal 9
    "cam":       float(os.getenv("REFLEX_CAM_WEIGHT",       "0.12")),
    "feedback":  float(os.getenv("REFLEX_FEEDBACK_WEIGHT",  "0.18")),
    "engram":    float(os.getenv("REFLEX_ENGRAM_WEIGHT",    "0.07")),
    "stm":       float(os.getenv("REFLEX_STM_WEIGHT",       "0.15")),
    "phase":     float(os.getenv("REFLEX_PHASE_WEIGHT",     "0.18")),
    "hope":      float(os.getenv("REFLEX_HOPE_WEIGHT",      "0.05")),
    "mgc":       float(os.getenv("REFLEX_MGC_WEIGHT",       "0.03")),
    # MARKER_198.P3.2: Signal 9 — Weaviate embedding similarity (stub: returns 0.0 until collection populated)
    "weaviate":  float(os.getenv("REFLEX_WEAVIATE_WEIGHT",  "0.08")),
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


def _infer_context_from_git() -> tuple:
    """MARKER_186.3: Scan recent git changes to build task_text.

    Returns (task_text, mgc_stats) where task_text is a synthetic description
    built from recently changed file extensions and directories.
    mgc_stats is always empty — real MGC stats come from get_mgc_cache().get_stats()
    (MARKER_200.MGC_REAL).
    """
    import subprocess

    task_keywords: list = []

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~5", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        )
        if result.returncode != 0:
            return "", {}

        files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        if not files:
            return "", {}

        # Count file types for keyword inference
        ext_counts: Dict[str, int] = {}
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

        # Build synthetic task_text from file extensions
        ext_to_keywords = {
            ".tsx": ["component", "ui", "layout", "react", "visual"],
            ".ts": ["typescript", "logic", "ui"],
            ".css": ["style", "css", "visual", "layout"],
            ".py": ["python", "backend", "api", "test"],
            ".json": ["config", "data"],
            ".sh": ["script", "automation"],
            ".spec.cjs": ["test", "e2e", "playwright", "smoke"],
            ".spec.ts": ["test", "e2e", "playwright"],
        }

        for ext, count in ext_counts.items():
            kws = ext_to_keywords.get(ext, [])
            task_keywords.extend(kws)

        # Add directory-based hints
        dir_keywords = {
            "client/e2e": ["test", "e2e", "playwright"],
            "client/src": ["ui", "component", "frontend"],
            "src/api": ["api", "backend", "route"],
            "src/orchestration": ["pipeline", "orchestration"],
            "src/services": ["service", "backend"],
        }
        for f in files:
            for dir_prefix, kws in dir_keywords.items():
                if f.startswith(dir_prefix):
                    task_keywords.extend(kws)
                    break

        # Deduplicate
        task_keywords = list(dict.fromkeys(task_keywords))

    except Exception:
        pass

    # MARKER_200.MGC_REAL: No fake mgc_stats from git diff.
    # Real MGC stats are read from get_mgc_cache().get_stats() in from_session().
    return " ".join(task_keywords), {}


def _agent_type_to_role(agent_type: str) -> str:
    """MARKER_186.3: Map agent_type to agent_role for tool filtering."""
    mapping = {
        "claude_code": "all",      # Opus/Claude Code = full access
        "cursor": "coder",         # Cursor = frontend coder
        "codex": "coder",          # Codex = isolated coder
        "dragon": "coder",         # Dragon pipeline = coder
        "dragon_bronze": "coder",
        "dragon_silver": "coder",
        "dragon_gold": "coder",
    }
    return mapping.get(agent_type, "coder")


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

    # ENGRAM user preferences: tool_usage_patterns
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

    # MARKER_198.P3.2: Signal 9 — Weaviate embedding similarity scores {tool_id: float}
    # Populated by query_tool_similarity() from elysia_tools.py.
    # Empty dict (default) → Signal 9 contributes 0.0 for all tools (zero regression).
    weaviate_scores: Dict[str, float] = field(default_factory=dict)

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
            user_tool_prefs: ENGRAM tool usage patterns
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
        agent_type: str = "",
        stm_items: Optional[List[str]] = None,
    ) -> "ReflexContext":
        """Build ReflexContext from vetka_session_init response.

        MARKER_186.3: Enhanced with agent_type and auto-generated task_text
        from recent git changes when task_text is empty.

        Args:
            session_data: Result dict from vetka_session_init
            task_text: Current task (may not be known at session start)
            phase_type: Default phase type
            feedback_scores: CORTEX scores (may not be loaded at session start)
            model_context_length: From LLMModelRegistry
            model_output_tps: Model speed
            agent_type: Agent type: "claude_code", "cursor", "dragon", etc.
        """
        # MARKER_198.P0.3: HOPE LOD from task complexity + model tier (NOT viewport zoom)
        # LOW = compressed overview (for Haiku or high-complexity cross-domain tasks)
        # MID = balanced (default, for Sonnet or medium tasks)
        # HIGH = full detail (for Opus or low-complexity single-file tasks)
        _task_complexity = session_data.get("task_board_summary", {}).get("top_pending", [{}])
        _complexity_hint = "medium"  # default
        if _task_complexity and isinstance(_task_complexity[0], dict):
            _complexity_hint = _task_complexity[0].get("complexity", "medium")

        # Model tier override
        _agent_type = agent_type or "claude_code"
        if "haiku" in _agent_type.lower():
            hope_level = "LOW"  # Haiku always gets compressed context
        elif "opus" in _agent_type.lower():
            hope_level = "HIGH" if _complexity_hint == "low" else "MID"
        else:  # sonnet, default
            if _complexity_hint == "high":
                hope_level = "LOW"
            elif _complexity_hint == "low":
                hope_level = "HIGH"
            else:
                hope_level = "MID"

        # Extract user tool preferences from ENGRAM
        user_prefs = session_data.get("user_preferences", {})
        tool_prefs: Dict[str, float] = {}
        if isinstance(user_prefs, dict) and user_prefs.get("has_preferences"):
            tool_prefs = user_prefs.get("tool_usage_patterns", {})

        # MARKER_186.3: Auto-generate task_text from recent git changes
        # when no explicit task is given. This gives semantic match signal
        # something to work with instead of returning flat 0.0 for all tools.
        mgc_stats: Dict[str, Any] = {}
        if not task_text:
            task_text, mgc_stats = _infer_context_from_git()

        # MARKER_186.3: Map agent_type to agent_role for role-based filtering
        agent_role = _agent_type_to_role(agent_type)

        # MARKER_200.CAM_COSINE: Compute CAM surprise from embedding cosine distance.
        # Replaces word-overlap Jaccard (Phase 198) with real semantic distance.
        # Uses mcc_jepa_adapter fallback chain: HTTP → Ollama → deterministic hash.
        # Falls back to Jaccard if embedding fails.
        cam_surprise = 0.0
        try:
            import json as _json_cam
            from pathlib import Path as _Path

            def _cam_project_root() -> "_Path":
                """Worktree-safe project root (same pattern as experience_report.py)."""
                candidate = _Path(__file__).resolve().parent.parent.parent
                parts = candidate.parts
                try:
                    wt_idx = parts.index(".claude")
                    main_root = _Path(*parts[:wt_idx])
                    if main_root.exists():
                        return main_root
                except ValueError:
                    pass
                return candidate

            _cam_path = _cam_project_root() / "data" / "cam_last_task.json"

            # Determine current task text from session data
            _current_task_text = task_text.strip()
            if not _current_task_text:
                _tbs = session_data.get("task_board_summary", {})
                _top = _tbs.get("top_pending", [])
                if _top and isinstance(_top[0], dict):
                    _current_task_text = _top[0].get("title", "")

            if _cam_path.exists() and _current_task_text:
                _prev = _json_cam.loads(_cam_path.read_text())
                _prev_embedding = _prev.get("embedding")
                _prev_text = _prev.get("task_text", "")

                if _prev_embedding and isinstance(_prev_embedding, list):
                    # Cosine distance path: embed current, compare to stored embedding
                    try:
                        from src.services.mcc_jepa_adapter import embed_texts_for_overlay
                        _result = embed_texts_for_overlay(
                            [_current_task_text], target_dim=128
                        )
                        if _result and _result.vectors and len(_result.vectors) > 0:
                            _curr_emb = _result.vectors[0]
                            _prev_emb = _prev_embedding
                            # Cosine similarity: dot(a,b) / (|a| * |b|)
                            _dot = sum(a * b for a, b in zip(_curr_emb, _prev_emb))
                            _norm_a = sum(a * a for a in _curr_emb) ** 0.5
                            _norm_b = sum(b * b for b in _prev_emb) ** 0.5
                            if _norm_a > 0 and _norm_b > 0:
                                _cosine_sim = _dot / (_norm_a * _norm_b)
                                cam_surprise = round(
                                    max(0.0, min(1.0, 1.0 - _cosine_sim)), 4
                                )
                    except Exception:
                        pass  # Fall through to Jaccard below

                # Jaccard fallback if embedding failed or no stored embedding
                if cam_surprise == 0.0 and _prev_text and _prev_text != _current_task_text:
                    _prev_words = set(_prev_text.lower().split())
                    _curr_words = set(_current_task_text.lower().split())
                    _total = len(_prev_words | _curr_words)
                    if _total > 0:
                        _overlap = len(_prev_words & _curr_words)
                        cam_surprise = round(1.0 - _overlap / _total, 4)

            # Persist current task text + embedding for next session
            if _current_task_text:
                _cam_data: Dict[str, Any] = {"task_text": _current_task_text}
                try:
                    from src.services.mcc_jepa_adapter import embed_texts_for_overlay
                    _save_result = embed_texts_for_overlay(
                        [_current_task_text], target_dim=128
                    )
                    if _save_result and _save_result.vectors and len(_save_result.vectors) > 0:
                        _cam_data["embedding"] = _save_result.vectors[0]
                except Exception:
                    pass  # Save text-only if embedding fails
                _cam_path.parent.mkdir(parents=True, exist_ok=True)
                _cam_path.write_text(_json_cam.dumps(_cam_data))
        except Exception:
            pass  # CAM surprise is best-effort — never blocks session init

        # MARKER_200.MGC_REAL: Read actual MGC cache stats instead of git-diff heuristic
        if not mgc_stats:
            try:
                from src.memory.mgc_cache import get_mgc_cache
                _mgc = get_mgc_cache()
                _mgc_s = _mgc.get_stats() if hasattr(_mgc, 'get_stats') else {}
                if _mgc_s:
                    mgc_stats = _mgc_s
            except Exception:
                pass  # MGC stats are best-effort

        return ReflexContext(
            task_text=task_text,
            phase_type=phase_type,
            agent_role=agent_role,
            cam_surprise=cam_surprise,
            user_tool_prefs=tool_prefs,
            stm_items=stm_items or [],  # MARKER_198.P0.1: populated from disk if available
            hope_level=hope_level,
            mgc_stats=mgc_stats,
            feedback_scores=feedback_scores or {},
            model_context_length=model_context_length,
            model_output_tps=model_output_tps,
            extra={"agent_type": agent_type} if agent_type else {},
        )


@dataclass
class ScoredTool:
    """A tool with its REFLEX score and reasoning breakdown."""
    tool_id: str
    score: float                          # 0.0 - 1.0
    reason: str                           # Human-readable: "semantic: 0.89, phase: 1.0"
    source_signals: Dict[str, float]      # Per-signal breakdown
    overlay: Dict[str, Any] = field(default_factory=dict)


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
                     feedback, engram, stm, phase, hope, mgc.
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

        # MARKER_195.2.3: Load emotion engine for post-scoring modulation (IP-E1)
        emotion_engine = None
        try:
            from src.services.reflex_emotions import get_reflex_emotions, EmotionContext as EmoCtx
            emotion_engine = get_reflex_emotions()
        except Exception:
            pass  # Emotion errors never break scoring

        scored: List[ScoredTool] = []
        for tool in self._eligible_tools(context, available_tools):
            signals = self.score_signals(tool, context)
            total = self._weighted_sum(signals)

            if total >= min_score:
                reason_parts = [f"{k}: {v:.2f}" for k, v in signals.items() if v > 0]
                overlay = self.overlay_effect(tool, context)
                if overlay["applied"] and overlay["score_delta"] > 0:
                    reason_parts.append(f"overlay:+{overlay['score_delta']:.2f}")

                # MARKER_195.2.3 IP-E1: Apply emotion modifier after weighted sum
                emotion_overlay: Dict[str, Any] = {}
                if emotion_engine is not None:
                    try:
                        tool_id = getattr(tool, "tool_id", str(tool))
                        emo_ctx = EmoCtx(
                            agent_id=context.extra.get("agent_type", ""),
                            phase_type=context.phase_type,
                            tool_permission=getattr(tool, "permission", "READ"),
                        )
                        breakdown = emotion_engine.get_modifier_breakdown(tool_id, emo_ctx)
                        emo_modifier = breakdown.get("modifier", 1.0)
                        total = max(0.0, min(1.0, total * emo_modifier))
                        emotion_overlay = {
                            "curiosity": breakdown.get("curiosity", 0),
                            "trust": breakdown.get("trust", 0),
                            "caution": breakdown.get("caution", 0),
                            "modifier": round(emo_modifier, 4),
                        }
                        reason_parts.append(f"emo:×{emo_modifier:.2f}")
                    except Exception:
                        pass  # Emotion errors never break scoring

                final_overlay = overlay
                if emotion_overlay:
                    final_overlay = {**overlay, "emotions": emotion_overlay}

                scored.append(ScoredTool(
                    tool_id=getattr(tool, "tool_id", str(tool)),
                    score=round(total, 4),
                    reason=", ".join(reason_parts),
                    source_signals=signals,
                    overlay=final_overlay,
                ))

        # Sort descending by score
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:top_n]

    def score(self, tool: Any, context: ReflexContext) -> float:
        """Score a single tool against context. Returns 0.0-1.0.

        MARKER_199.EMOTION_SCORE: Emotion modifier is applied here (same as recommend()).
        final_score = base_score * emotion_modifier(curiosity, trust, caution)
        Modifier is clamped to [0.3, 1.5]; result is clamped to [0.0, 1.0].
        Emotion errors are swallowed — they must never break scoring.

        Previous: MARKER_195.2.3 (initial wiring, single-signal only).
        Now: full EmotionContext with agent_id, phase_type, permission (parity with recommend()).
        """
        if not REFLEX_ENABLED:
            return 0.0
        signals = self.score_signals(tool, context)
        total = self._weighted_sum(signals)

        # MARKER_199.EMOTION_SCORE: Apply emotion modifier to single-tool scoring.
        # Builds EmotionContext identical to recommend() so both paths are consistent.
        try:
            from src.services.reflex_emotions import get_reflex_emotions, EmotionContext as EmoCtx
            emotion_engine = get_reflex_emotions()
            tool_id = getattr(tool, "tool_id", str(tool))
            emo_ctx = EmoCtx(
                agent_id=context.extra.get("agent_type", ""),
                phase_type=context.phase_type,
                tool_permission=getattr(tool, "permission", "READ"),
                is_foreign_file=context.extra.get("is_foreign_file", False),
                has_recon=context.extra.get("has_recon", True),
                guard_warnings=context.extra.get("guard_warnings", []),
                freshness_score=context.extra.get("freshness_score", 0.0),
                protocol_violation_count=context.extra.get("protocol_violation_count", 0),
            )
            breakdown = emotion_engine.get_modifier_breakdown(tool_id, emo_ctx)
            emo_modifier = breakdown.get("modifier", 1.0)
            total = max(0.0, min(1.0, total * emo_modifier))
        except Exception:
            pass  # Emotion errors never break scoring

        return round(total, 4)

    def score_signals(self, tool: Any, context: ReflexContext) -> Dict[str, float]:
        """Compute all 9 signal scores for a tool. Each returns 0.0-1.0."""
        return {
            "semantic":  self._semantic_match(tool, context),
            "cam":       self._cam_relevance(tool, context),
            "feedback":  self._feedback_score(tool, context),
            "engram":    self._engram_preference(tool, context),
            "stm":       self._stm_relevance(tool, context),
            "phase":     self._phase_match(tool, context),
            "hope":      self._hope_lod_match(tool, context),
            "mgc":       self._mgc_heat(tool, context),
            # MARKER_198.P3.2: Signal 9 — Weaviate embedding similarity (0.0 until collection populated)
            "weaviate":  self._weaviate_similarity(tool, context),
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

    def overlay_effect(self, tool: Any, context: ReflexContext) -> Dict[str, Any]:
        """MARKER_177.REFLEX.TOOL_MEMORY.OVERLAY_EFFECT — Explain overlay impact on ranking."""
        hints = dict(getattr(tool, "overlay_hints", {}) or {})
        if not hints.get("overlay_applied"):
            return {
                "applied": False,
                "score_delta": 0.0,
                "signal_deltas": {},
                "added_intent_tags": [],
                "added_keywords": [],
            }

        base_intent_tags = list(hints.get("base_intent_tags", []) or [])
        base_keywords = list(hints.get("base_keywords", []) or [])
        current_semantic = self._semantic_match(tool, context)
        current_stm = self._stm_relevance(tool, context)
        base_semantic = self._semantic_match_values(context.task_text, base_intent_tags, base_keywords)
        base_stm = self._stm_relevance_values(
            getattr(tool, "tool_id", ""),
            base_intent_tags,
            context.stm_items,
        )

        semantic_delta = round(current_semantic - base_semantic, 4)
        stm_delta = round(current_stm - base_stm, 4)
        score_delta = round(
            (semantic_delta * self._weights.get("semantic", 0.0))
            + (stm_delta * self._weights.get("stm", 0.0)),
            4,
        )

        return {
            "applied": True,
            "origin": str(hints.get("origin", "")),
            "catalog_source": str(hints.get("catalog_source", "")),
            "path": str(hints.get("path", "")),
            "trigger_hint": str(hints.get("trigger_hint", "")),
            "aliases": list(hints.get("aliases", []) or []),
            "added_intent_tags": list(hints.get("added_intent_tags", []) or []),
            "added_keywords": list(hints.get("added_keywords", []) or []),
            "signal_deltas": {
                "semantic": semantic_delta,
                "stm": stm_delta,
            },
            "score_delta": score_delta,
        }

    def score_without_overlay(self, tool: Any, context: ReflexContext) -> float:
        """Return the tool score using canonical catalog metadata only."""
        if not REFLEX_ENABLED:
            return 0.0
        current_total = self._weighted_sum(self.score_signals(tool, context))
        overlay = self.overlay_effect(tool, context)
        return round(min(1.0, max(0.0, current_total - overlay["score_delta"])), 4)

    def overlay_rank_changes(
        self,
        context: ReflexContext,
        available_tools: List[Any],
        min_score: float = 0.1,
    ) -> Dict[str, Dict[str, Any]]:
        """Compare current ranks with canonical-only ranks for overlay-aware tools."""
        if not REFLEX_ENABLED:
            return {}

        ranked_current: List[tuple[str, float]] = []
        ranked_baseline: List[tuple[str, float]] = []
        diagnostics: Dict[str, Dict[str, Any]] = {}

        for tool in self._eligible_tools(context, available_tools):
            tool_id = getattr(tool, "tool_id", str(tool))
            current_score = round(self._weighted_sum(self.score_signals(tool, context)), 4)
            baseline_score = self.score_without_overlay(tool, context)
            overlay = self.overlay_effect(tool, context)
            diagnostics[tool_id] = {
                "current_score": current_score,
                "baseline_score": baseline_score,
                "score_delta": overlay["score_delta"],
                "applied": overlay["applied"],
            }
            if current_score >= min_score:
                ranked_current.append((tool_id, current_score))
            if baseline_score >= min_score:
                ranked_baseline.append((tool_id, baseline_score))

        ranked_current.sort(key=lambda item: item[1], reverse=True)
        ranked_baseline.sort(key=lambda item: item[1], reverse=True)
        current_ranks = {tool_id: index + 1 for index, (tool_id, _) in enumerate(ranked_current)}
        baseline_ranks = {tool_id: index + 1 for index, (tool_id, _) in enumerate(ranked_baseline)}

        for tool_id, row in diagnostics.items():
            current_rank = current_ranks.get(tool_id)
            baseline_rank = baseline_ranks.get(tool_id)
            rank_delta = 0
            if current_rank is not None and baseline_rank is not None:
                rank_delta = baseline_rank - current_rank
            row["current_rank"] = current_rank
            row["baseline_rank"] = baseline_rank
            row["rank_delta"] = rank_delta
            row["order_changed"] = bool(row["applied"] and rank_delta != 0)

        return diagnostics

    def _eligible_tools(self, context: ReflexContext, available_tools: List[Any]) -> List[Any]:
        capability = self._model_capability(context)
        eligible: List[Any] = []
        for tool in available_tools:
            if not getattr(tool, "active", True):
                continue
            if capability == "small":
                risk = getattr(tool, "cost", {}).get("risk_level", "read_only")
                if risk in ("execute", "external"):
                    continue
            eligible.append(tool)
        return eligible

    # --- 8 Signal Scorers ---

    def _semantic_match(self, tool: Any, context: ReflexContext) -> float:
        """Signal 1: Keyword/intent overlap between task and tool.

        Uses ToolEntry.matches_keywords() and intent_tags matching.
        Pure string matching, no embeddings (embeddings are for Phase 172.P5 tuning).
        """
        if not context.task_text:
            return 0.0

        trigger_patterns = getattr(tool, "trigger_patterns", {}) or {}
        return self._semantic_match_values(
            context.task_text,
            getattr(tool, "intent_tags", []),
            trigger_patterns.get("keywords", []),
        )

    def _cam_relevance(self, tool: Any, context: ReflexContext) -> float:
        """Signal 2: CAM surprise boost.

        High surprise (>0.7) = novel context → broaden tool palette (boost all).
        Low surprise (<0.3) = predictable → prefer proven tools.
        Medium = neutral (0.5 baseline).

        MARKER_195.4.BOOST: Tool freshness curiosity boost.
        Recently-updated tools (within 48h) get +0.3 CAM boost decaying linearly,
        encouraging agents to re-try tools after source code changes.
        """
        surprise = context.cam_surprise

        # MARKER_195.4.BOOST: Freshness curiosity boost for updated tools
        tool_id = getattr(tool, "tool_id", "")
        if tool_id:
            try:
                from src.services.tool_source_watch import get_tool_source_watch
                freshness = get_tool_source_watch().get(tool_id)
                if freshness and freshness.is_recently_updated(hours=48):
                    hours_since = freshness.hours_since_update()
                    boost = 0.3 * max(0.0, 1.0 - hours_since / 48.0)
                    surprise = min(1.0, surprise + boost)
            except ImportError:
                pass

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

    def _engram_preference(self, tool: Any, context: ReflexContext) -> float:
        """Signal 4: User preference from ENGRAM tool_usage_patterns.

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
        return self._stm_relevance_values(
            getattr(tool, "tool_id", ""),
            getattr(tool, "intent_tags", []),
            context.stm_items,
        )

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

    def _semantic_match_values(
        self,
        task_text: str,
        intent_tags: List[str],
        keywords: List[str],
    ) -> float:
        if not task_text:
            return 0.0
        text = task_text.lower()
        keyword_values = [str(value).strip() for value in (keywords or []) if str(value).strip()]
        kw_score = 0.0
        if keyword_values:
            hits = sum(1 for kw in keyword_values if kw.lower() in text)
            kw_score = hits / len(keyword_values)

        intent_values = [str(value).strip() for value in (intent_tags or []) if str(value).strip()]
        if intent_values:
            task_words = set(text.split())
            tag_set = set(value.lower() for value in intent_values)
            overlap = task_words & tag_set
            intent_score = len(overlap) / len(tag_set) if tag_set else 0.0
        else:
            intent_score = 0.0

        return min(1.0, max(kw_score, intent_score))

    def _stm_relevance_values(
        self,
        tool_id: str,
        intent_tags: List[str],
        stm_items: List[str],
    ) -> float:
        if not stm_items:
            return 0.0
        search_terms = {str(tool_id or "").lower()}
        search_terms.update(str(tag).lower() for tag in (intent_tags or []) if str(tag).strip())
        stm_text = " ".join(stm_items).lower()
        hits = sum(1 for term in search_terms if term and term in stm_text)
        if hits == 0:
            return 0.0
        return min(1.0, hits / max(1, len(search_terms)))

    # --- Signal 9: Weaviate embedding similarity ---

    def _weaviate_similarity(self, tool: Any, context: ReflexContext) -> float:
        """MARKER_198.P3.2: Signal 9 — Weaviate embedding similarity.

        Looks up tool_id in context.weaviate_scores (pre-fetched via
        elysia_tools.query_tool_similarity() at context build time).

        Returns 0.0 when:
          - context.weaviate_scores is empty (Weaviate unavailable or not populated)
          - tool_id not in top-K results from collection query
        Zero regression: existing behavior unchanged when weaviate_scores = {}.

        To activate: populate weaviate_scores in ReflexContext.from_subtask() /
        from_session() by calling query_tool_similarity(task_description).
        See: src/orchestration/elysia_tools.py — query_tool_similarity() stub.
        """
        if not context.weaviate_scores:
            return 0.0
        tool_id = getattr(tool, "tool_id", None) or str(tool)
        score = context.weaviate_scores.get(tool_id, 0.0)
        return float(min(1.0, max(0.0, score)))

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
        agent_type: str = "",
        current_task: Optional[Dict[str, Any]] = None,
        stm_items: Optional[List[str]] = None,
    ) -> List[ScoredTool]:
        """Recommend tools for session_init response (IP-6).

        MARKER_186.3: Enhanced with agent_type and auto-context from git.
        MARKER_191.3: Enhanced with current_task for task-aware semantic matching.
        MARKER_198.P0.1: Enhanced with stm_items from disk-persisted STM buffer.
        Builds ReflexContext from session data, returns broad recommendations.
        """
        if not REFLEX_ENABLED:
            return []

        # Load feedback scores for better scoring
        feedback_scores: Dict[str, float] = {}
        try:
            from src.services.reflex_feedback import get_reflex_feedback
            feedback_scores = get_reflex_feedback().get_scores_bulk(phase_type)
        except Exception:
            pass

        # MARKER_191.3: Extract task_text from current task for semantic matching
        task_text = ""
        if current_task:
            title = current_task.get("title", "")
            desc = current_task.get("description", "")
            task_text = f"{title} {desc}".strip()

        context = ReflexContext.from_session(
            session_data,
            task_text=task_text,
            phase_type=phase_type,
            feedback_scores=feedback_scores,
            agent_type=agent_type,
            stm_items=stm_items,  # MARKER_198.P0.1: pass disk-loaded STM items
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
