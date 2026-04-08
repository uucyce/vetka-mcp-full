"""
REFLEX Emotions — Post-scoring emotion modulator for tool ranking.

MARKER_195.2.1

Layer of REFLEX (Reactive Execution & Function Linking EXchange).
Three emotional dimensions modulate base tool scores AFTER scoring:

  final_score = base_score * emotion_modifier(curiosity, trust, caution)

Dimensions:
  1. CURIOSITY  — exploration drive, boosts novel/fresh tools    [0,1]
  2. TRUST      — reliability confidence, asymmetric EMA         [0,1]
  3. CAUTION    — risk awareness, penalises dangerous operations  [0,1]

Combined modifier clamped to [0.3, 1.5].

Pure logic — no imports from session_tools, fc_loop, or scorer.

Part of VETKA OS:
  VETKA > REFLEX > Emotions (this file)

@status: active
@phase: 195.2.1
@depends: engram_cache (optional, for persistence)
@used_by: reflex_scorer (post-scoring), reflex_feedback (outcome), reflex_integration
"""

import json
import logging
import math
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature flag: emotions enabled by default
# ---------------------------------------------------------------------------
REFLEX_EMOTIONS_ENABLED = os.getenv("REFLEX_EMOTIONS_ENABLED", "true").lower() in ("true", "1", "yes")

# ---------------------------------------------------------------------------
# Paths (JSON file persistence as primary, ENGRAM as secondary)
# ---------------------------------------------------------------------------
_DATA_DIR = Path(os.getenv(
    "REFLEX_EMOTIONS_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "reflex", "emotions"),
))
_STATE_FILE = _DATA_DIR / "emotion_states.json"

# ---------------------------------------------------------------------------
# Cold-start defaults
# ---------------------------------------------------------------------------
_COLD_CURIOSITY = 0.6
_COLD_TRUST = 0.5
_COLD_CAUTION = 0.3

# Trust EMA rates (asymmetric)
_TRUST_GAIN = 0.15
_TRUST_LOSS = 0.35
_TRUST_GUARD_CAP = 0.3

# Risk levels by permission category
_SIDE_EFFECT_RISK: Dict[str, float] = {
    "WRITE": 0.7,
    "EXECUTE": 0.7,
    "ADMIN": 0.9,
    "EXTERNAL": 0.8,
}

# ENGRAM persistence key prefix and category
_ENGRAM_KEY_PREFIX = "emo"
_ENGRAM_CATEGORY = "emotion_state"

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EmotionState:
    """Per-tool emotional state, persisted across sessions.

    MARKER_195.2.STATE
    """
    tool_id: str
    curiosity: float = _COLD_CURIOSITY
    trust: float = _COLD_TRUST
    caution: float = _COLD_CAUTION
    mood_label: str = "neutral"      # computed: curious/confident/cautious/neutral
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_updated: float = field(default_factory=time.time)


@dataclass
class EmotionContext:
    """Context provided at scoring time — describes the current invocation.

    MARKER_195.2.CONTEXT
    MARKER_198.P1.1: Added protocol_violation_count to wire Protocol Guard into Caution.
    """
    agent_id: str = ""
    phase_type: str = ""
    project_id: str = ""
    tool_permission: str = "READ"
    is_foreign_file: bool = False
    has_recon: bool = True
    guard_warnings: List[str] = field(default_factory=list)
    freshness_score: float = 0.0
    tool_freshness: Dict[str, float] = field(default_factory=dict)
    tool_usage_history: Dict[str, List[dict]] = field(default_factory=dict)
    tool_metadata: Dict[str, dict] = field(default_factory=dict)
    file_ownership: Dict[str, str] = field(default_factory=dict)
    current_task_recon_docs: List[str] = field(default_factory=list)
    # MARKER_198.P1.1: Protocol Guard violation count — boosts caution proportionally.
    # 0 = no violations; each violation adds +0.1 caution (capped at 0.9).
    protocol_violation_count: int = 0


# ---------------------------------------------------------------------------
# Pure computation functions
# ---------------------------------------------------------------------------


def compute_curiosity(usage_count: int, freshness_score: float) -> float:
    """Curiosity = novelty sigmoid + freshness boost, clamped [0, 1].

    novelty = 1 / (1 + exp(0.5 * (usage_count - 5)))
    freshness_boost = freshness_score * 0.4

    MARKER_198.P1.2: Tool Freshness -> Curiosity contract.
    freshness_score is supplied by reflex_integration.reflex_session() IP-6,
    which calls ToolSourceWatch.scan_all() on every session_init and then
    derives a per-tool score capped at 0.75 with linear 48 h decay:
      freshness_score = min(0.75, 1.0 - hours_since_update / 48)
    This ensures freshness_boost peaks at 0.75 * 0.4 = 0.30 at t=0 and
    reaches 0.0 at t=48 h, giving recently-updated tools a +0.30 Curiosity
    boost that decays naturally over the freshness window.
    """
    try:
        novelty = 1.0 / (1.0 + math.exp(0.5 * (usage_count - 5)))
        freshness_boost = float(freshness_score) * 0.4
        return max(0.0, min(1.0, novelty + freshness_boost))
    except Exception:
        logger.debug("compute_curiosity failed, returning cold start", exc_info=True)
        return _COLD_CURIOSITY


def compute_trust(current_trust: float, success: bool, guard_warnings: List[str]) -> float:
    """Asymmetric EMA trust update.

    +0.15 on success, -0.35 on failure.
    Guard warnings cap trust at 0.3.
    """
    try:
        if success:
            new_trust = current_trust + _TRUST_GAIN * (1.0 - current_trust)
        else:
            new_trust = current_trust - _TRUST_LOSS * current_trust

        new_trust = max(0.0, min(1.0, new_trust))

        if guard_warnings:
            new_trust = min(new_trust, _TRUST_GUARD_CAP)

        return new_trust
    except Exception:
        logger.debug("compute_trust failed, returning cold start", exc_info=True)
        return _COLD_TRUST


def compute_caution(
    tool_permission: str,
    is_foreign_file: bool,
    has_recon: bool,
    guard_warnings: List[str],
    protocol_violation_count: int = 0,
) -> float:
    """Caution = max of all risk signals.

    READ-only tools get caution <= 0.1.

    MARKER_198.P1.1: Protocol Guard violation count boosts caution proportionally.
    Each violation adds +0.1 (capped at 0.9), scaled up from any existing guard risk.
    """
    try:
        perm = tool_permission.upper() if tool_permission else "READ"

        risks: List[float] = []

        # Side-effect risk by permission
        side_risk = _SIDE_EFFECT_RISK.get(perm, 0.0)
        if side_risk > 0.0:
            risks.append(side_risk)

        # Ownership risk
        if is_foreign_file:
            risks.append(0.8)

        # Protocol risk — no recon done
        if not has_recon:
            risks.append(0.5)

        # Guard risk (binary: any warnings → 0.9 base)
        if guard_warnings:
            risks.append(0.9)

        # MARKER_198.P1.1: Protocol violation count risk — scales with violation count.
        # Each violation adds 0.1, minimum floor 0.4 when violations exist, max 0.9.
        if protocol_violation_count > 0:
            violation_risk = min(0.9, 0.4 + protocol_violation_count * 0.1)
            risks.append(violation_risk)

        if not risks:
            # READ-only with no risk flags -> minimal caution
            return 0.1 if perm == "READ" else 0.0

        return max(risks)
    except Exception:
        logger.debug("compute_caution failed, returning cold start", exc_info=True)
        return _COLD_CAUTION


def compute_emotion_modifier(curiosity: float, trust: float, caution: float) -> float:
    """Combined post-scoring modifier, clamped to [0.3, 1.5].

    modifier = (0.5 + trust * 0.5) * (1.0 + curiosity * 0.3) * (1.0 - caution * 0.4)
    """
    try:
        trust_factor = 0.5 + float(trust) * 0.5
        curiosity_factor = 1.0 + float(curiosity) * 0.3
        caution_factor = 1.0 - float(caution) * 0.4
        modifier = trust_factor * curiosity_factor * caution_factor
        return max(0.3, min(1.5, modifier))
    except Exception:
        logger.debug("compute_emotion_modifier failed, returning 1.0", exc_info=True)
        return 1.0


def get_mood_label(curiosity: float, trust: float, caution: float) -> str:
    """Derive mood label from dominant emotion.

    - curious: curiosity > 0.7 and curiosity is dominant
    - confident: trust > 0.7 and trust is dominant
    - cautious: caution > 0.6 and caution is dominant
    - neutral: otherwise
    """
    if curiosity > 0.7 and curiosity >= trust and curiosity >= caution:
        return "curious"
    if trust > 0.7 and trust >= curiosity and trust >= caution:
        return "confident"
    if caution > 0.6 and caution >= curiosity and caution >= trust:
        return "cautious"
    return "neutral"


# ---------------------------------------------------------------------------
# EmotionEngine
# ---------------------------------------------------------------------------


class EmotionEngine:
    """Manages per-tool emotional states with JSON + ENGRAM persistence.

    MARKER_195.2.1: Core emotion modulator for REFLEX.

    Persistence hierarchy:
      1. In-memory dict (fastest)
      2. JSON file (data/reflex/emotions/emotion_states.json)
      3. ENGRAM L1 cache (per agent+tool pair, optional)
    """

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else _DATA_DIR
        self._state_file = self._data_dir / "emotion_states.json"
        self._states: Dict[str, EmotionState] = {}
        self._lock = threading.Lock()
        self._load()

    # -- persistence ---------------------------------------------------------

    def _load(self) -> None:
        """Load emotion states from disk (JSON)."""
        try:
            if self._state_file.exists():
                raw = json.loads(self._state_file.read_text(encoding="utf-8"))
                for tool_id, blob in raw.items():
                    self._states[tool_id] = EmotionState(
                        tool_id=tool_id,
                        curiosity=blob.get("curiosity", _COLD_CURIOSITY),
                        trust=blob.get("trust", _COLD_TRUST),
                        caution=blob.get("caution", _COLD_CAUTION),
                        mood_label=blob.get("mood_label", "neutral"),
                        usage_count=blob.get("usage_count", 0),
                        success_count=blob.get("success_count", 0),
                        failure_count=blob.get("failure_count", 0),
                        last_updated=blob.get("last_updated", time.time()),
                    )
                logger.debug("Loaded %d emotion states from %s", len(self._states), self._state_file)
        except Exception:
            logger.warning("Failed to load emotion states, starting fresh", exc_info=True)
            self._states = {}

    def _save(self) -> None:
        """Persist emotion states to disk (JSON)."""
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            payload: Dict[str, dict] = {}
            for tool_id, state in self._states.items():
                payload[tool_id] = asdict(state)
            self._state_file.write_text(
                json.dumps(payload, indent=2, default=str),
                encoding="utf-8",
            )
            logger.debug("Saved %d emotion states to %s", len(payload), self._state_file)
        except Exception:
            logger.warning("Failed to save emotion states", exc_info=True)

    def _save_to_engram(self, agent_id: str, tool_id: str, state: EmotionState) -> None:
        """Persist emotion state to ENGRAM L1 cache (secondary persistence)."""
        try:
            from src.memory.engram_cache import get_engram_cache
            cache = get_engram_cache()
            key = f"{_ENGRAM_KEY_PREFIX}::{agent_id or 'default'}::{tool_id}::emotion"
            value = json.dumps({
                "curiosity": state.curiosity,
                "trust": state.trust,
                "caution": state.caution,
                "mood_label": state.mood_label,
                "usage_count": state.usage_count,
                "success_count": state.success_count,
                "failure_count": state.failure_count,
            })
            cache.put(key, value, category=_ENGRAM_CATEGORY)
        except Exception as e:
            logger.debug("[EMOTIONS] ENGRAM save failed (non-fatal): %s", e)

    def _load_from_engram(self, agent_id: str, tool_id: str) -> Optional[EmotionState]:
        """Load emotion state from ENGRAM L1 cache."""
        try:
            from src.memory.engram_cache import get_engram_cache
            cache = get_engram_cache()
            all_entries = cache.get_all()
            key = f"{_ENGRAM_KEY_PREFIX}::{agent_id or 'default'}::{tool_id}::emotion"
            entry = all_entries.get(key)
            if entry:
                data = json.loads(entry.get("value", "{}"))
                return EmotionState(
                    tool_id=tool_id,
                    curiosity=data.get("curiosity", _COLD_CURIOSITY),
                    trust=data.get("trust", _COLD_TRUST),
                    caution=data.get("caution", _COLD_CAUTION),
                    mood_label=data.get("mood_label", "neutral"),
                    usage_count=data.get("usage_count", 0),
                    success_count=data.get("success_count", 0),
                    failure_count=data.get("failure_count", 0),
                )
        except Exception as e:
            logger.debug("[EMOTIONS] ENGRAM load failed (non-fatal): %s", e)
        return None

    # -- public API ----------------------------------------------------------

    def get_emotion_state(self, tool_id: str) -> EmotionState:
        """Return current EmotionState for a tool (cold-start if unknown)."""
        with self._lock:
            if tool_id not in self._states:
                self._states[tool_id] = EmotionState(tool_id=tool_id)
            return self._states[tool_id]

    def compute_emotions(self, tool_id: str, context: Optional[EmotionContext] = None) -> EmotionState:
        """Full emotion computation: curiosity, trust, caution, mood_label.

        Returns EmotionState with all dimensions computed from context.
        """
        if not REFLEX_EMOTIONS_ENABLED:
            return EmotionState(tool_id=tool_id)

        try:
            ctx = context or EmotionContext()
            state = self.get_emotion_state(tool_id)

            curiosity = compute_curiosity(state.usage_count, ctx.freshness_score)
            trust = state.trust
            # MARKER_198.P1.1: Pass protocol_violation_count into caution computation
            caution = compute_caution(
                ctx.tool_permission,
                ctx.is_foreign_file,
                ctx.has_recon,
                ctx.guard_warnings,
                ctx.protocol_violation_count,
            )

            # Guard warning or protocol violations cap trust
            if ctx.guard_warnings or ctx.protocol_violation_count > 0:
                trust = min(trust, _TRUST_GUARD_CAP)

            state.curiosity = curiosity
            state.trust = trust
            state.caution = caution
            state.mood_label = get_mood_label(curiosity, trust, caution)

            return state
        except Exception:
            logger.debug("compute_emotions failed for %s, returning defaults", tool_id, exc_info=True)
            return EmotionState(tool_id=tool_id)

    def compute_modifier(self, tool_id: str, context: Optional[EmotionContext] = None) -> float:
        """Compute the combined emotion modifier for a tool.

        Returns a float in [0.3, 1.5] that multiplies the base score.
        When REFLEX_EMOTIONS_ENABLED=false, returns 1.0 (no modulation).
        """
        if not REFLEX_EMOTIONS_ENABLED:
            return 1.0

        try:
            state = self.get_emotion_state(tool_id)
            ctx = context or EmotionContext()

            curiosity = compute_curiosity(state.usage_count, ctx.freshness_score)
            trust = state.trust
            # MARKER_198.P1.1: Pass protocol_violation_count into caution computation
            caution = compute_caution(
                ctx.tool_permission,
                ctx.is_foreign_file,
                ctx.has_recon,
                ctx.guard_warnings,
                ctx.protocol_violation_count,
            )

            # Update state snapshot (not persisted until record_outcome)
            state.curiosity = curiosity
            state.caution = caution
            state.mood_label = get_mood_label(curiosity, trust, caution)

            return compute_emotion_modifier(curiosity, trust, caution)
        except Exception:
            logger.debug("compute_modifier failed for %s, returning 1.0", tool_id, exc_info=True)
            return 1.0

    def record_outcome(self, tool_id: str, success: bool, context: Optional[EmotionContext] = None) -> EmotionState:
        """Record a tool invocation outcome and update emotional state.

        Persists to disk (JSON + ENGRAM) after every call.
        When REFLEX_EMOTIONS_ENABLED=false, still returns current state but skips update.
        """
        if not REFLEX_EMOTIONS_ENABLED:
            return self.get_emotion_state(tool_id)

        try:
            ctx = context or EmotionContext()

            with self._lock:
                if tool_id not in self._states:
                    self._states[tool_id] = EmotionState(tool_id=tool_id)

                state = self._states[tool_id]

                # Update counters
                state.usage_count += 1
                if success:
                    state.success_count += 1
                else:
                    state.failure_count += 1

                # Recompute emotions
                # MARKER_198.P1.1: Pass protocol_violation_count into caution computation
                state.curiosity = compute_curiosity(state.usage_count, ctx.freshness_score)
                state.trust = compute_trust(state.trust, success, ctx.guard_warnings)
                state.caution = compute_caution(
                    ctx.tool_permission,
                    ctx.is_foreign_file,
                    ctx.has_recon,
                    ctx.guard_warnings,
                    ctx.protocol_violation_count,
                )
                state.mood_label = get_mood_label(state.curiosity, state.trust, state.caution)
                state.last_updated = time.time()

                self._save()

            # ENGRAM persistence (outside lock, non-fatal)
            self._save_to_engram(ctx.agent_id, tool_id, state)

            return state
        except Exception:
            logger.warning("record_outcome failed for %s", tool_id, exc_info=True)
            return self.get_emotion_state(tool_id)

    def get_modifier_breakdown(self, tool_id: str, context: Optional[EmotionContext] = None) -> Dict[str, Any]:
        """Return a breakdown dict for debugging / UI display.

        When REFLEX_EMOTIONS_ENABLED=false, returns neutral breakdown with modifier=1.0.
        """
        if not REFLEX_EMOTIONS_ENABLED:
            return {
                "tool_id": tool_id,
                "curiosity": _COLD_CURIOSITY,
                "trust": _COLD_TRUST,
                "caution": _COLD_CAUTION,
                "modifier": 1.0,
                "mood_label": "neutral",
                "usage_count": 0,
                "success_count": 0,
                "failure_count": 0,
            }

        try:
            state = self.get_emotion_state(tool_id)
            ctx = context or EmotionContext()

            curiosity = compute_curiosity(state.usage_count, ctx.freshness_score)
            trust = state.trust
            # MARKER_198.P1.1: Pass protocol_violation_count into caution computation
            caution = compute_caution(
                ctx.tool_permission,
                ctx.is_foreign_file,
                ctx.has_recon,
                ctx.guard_warnings,
                ctx.protocol_violation_count,
            )
            modifier = compute_emotion_modifier(curiosity, trust, caution)
            mood = get_mood_label(curiosity, trust, caution)

            return {
                "tool_id": tool_id,
                "curiosity": round(curiosity, 4),
                "trust": round(trust, 4),
                "caution": round(caution, 4),
                "modifier": round(modifier, 4),
                "mood_label": mood,
                "usage_count": state.usage_count,
                "success_count": state.success_count,
                "failure_count": state.failure_count,
            }
        except Exception:
            logger.debug("get_modifier_breakdown failed for %s", tool_id, exc_info=True)
            return {
                "tool_id": tool_id,
                "curiosity": _COLD_CURIOSITY,
                "trust": _COLD_TRUST,
                "caution": _COLD_CAUTION,
                "modifier": 1.0,
                "mood_label": "neutral",
                "usage_count": 0,
                "success_count": 0,
                "failure_count": 0,
            }

    def get_state_from_engram(self, agent_id: str, tool_id: str) -> Optional[EmotionState]:
        """Load emotion state from ENGRAM (for cross-session recovery)."""
        return self._load_from_engram(agent_id, tool_id)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_instance: Optional[EmotionEngine] = None
_instance_lock = threading.Lock()


def get_reflex_emotions(data_dir: Optional[str] = None) -> EmotionEngine:
    """Return the singleton EmotionEngine instance."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = EmotionEngine(data_dir=data_dir)
    return _instance


def reset_reflex_emotions() -> None:
    """Reset the singleton (useful for tests)."""
    global _instance
    with _instance_lock:
        _instance = None
