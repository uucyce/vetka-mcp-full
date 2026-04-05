"""
REFLEX Emotions — Post-scoring emotion modulator for tool ranking.

MARKER_195.2.1

Layer of REFLEX (Reactive Execution & Function Linking EXchange).
Three emotional dimensions modulate base tool scores AFTER scoring:

  final_score = base_score × emotion_modifier(curiosity, trust, caution)

Dimensions:
  1. CURIOSITY  — exploration drive, boosts novel/fresh tools    [0,1] → ×1.0–1.3
  2. TRUST      — reliability confidence, asymmetric EMA         [0,1] → ×0.5–1.0
  3. CAUTION    — risk awareness, penalises dangerous operations  [0,1] → ×0.6–1.0

Combined modifier clamped to [0.3, 1.5].

Pure logic — no imports from session_tools, fc_loop, or scorer.

Part of VETKA OS:
  VETKA > REFLEX > Emotions (this file)

@status: active
@phase: 195.2.1
@depends: (none — standalone)
@used_by: reflex_scorer (post-scoring), reflex_integration
"""

import json
import logging
import math
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
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
_COLD_CAUTION = 0.0

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

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EmotionState:
    """Per-tool emotional state, persisted across sessions."""
    tool_id: str
    curiosity: float = _COLD_CURIOSITY
    trust: float = _COLD_TRUST
    caution: float = _COLD_CAUTION
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_updated: float = field(default_factory=time.time)


@dataclass
class EmotionContext:
    """Context provided at scoring time — describes the current invocation."""
    agent_id: str = ""
    phase_type: str = ""
    tool_permission: str = "READ"
    is_foreign_file: bool = False
    has_recon: bool = True
    guard_warnings: List[str] = field(default_factory=list)
    freshness_score: float = 0.0


# ---------------------------------------------------------------------------
# Pure computation functions
# ---------------------------------------------------------------------------


def compute_curiosity(usage_count: int, freshness_score: float) -> float:
    """Curiosity = novelty sigmoid + freshness boost, clamped [0, 1].

    novelty = 1 / (1 + exp(0.5 * (usage_count - 5)))
    freshness_boost = freshness_score * 0.4
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
) -> float:
    """Caution = max of all risk signals.

    READ-only tools get caution <= 0.1.
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

        # Guard risk
        if guard_warnings:
            risks.append(0.9)

        if not risks:
            # READ-only with no risk flags → minimal caution
            return 0.1 if perm == "READ" else 0.0

        return max(risks)
    except Exception:
        logger.debug("compute_caution failed, returning cold start", exc_info=True)
        return _COLD_CAUTION


def compute_emotion_modifier(curiosity: float, trust: float, caution: float) -> float:
    """Combined post-scoring modifier, clamped to [0.3, 1.5].

    modifier = (0.5 + trust * 0.5) × (1.0 + curiosity * 0.3) × (1.0 - caution * 0.4)
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


# ---------------------------------------------------------------------------
# EmotionEngine
# ---------------------------------------------------------------------------


class EmotionEngine:
    """Manages per-tool emotional states with JSON persistence.

    MARKER_195.2.1: Core emotion modulator for REFLEX.
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

    # -- public API ----------------------------------------------------------

    def get_emotion_state(self, tool_id: str) -> EmotionState:
        """Return current EmotionState for a tool (cold-start if unknown)."""
        with self._lock:
            if tool_id not in self._states:
                self._states[tool_id] = EmotionState(tool_id=tool_id)
            return self._states[tool_id]

    def compute_modifier(self, tool_id: str, context: Optional[EmotionContext] = None) -> float:
        """Compute the combined emotion modifier for a tool.

        Returns a float in [0.3, 1.5] that multiplies the base score.
        """
        try:
            state = self.get_emotion_state(tool_id)
            ctx = context or EmotionContext()

            curiosity = compute_curiosity(state.usage_count, ctx.freshness_score)
            trust = state.trust
            caution = compute_caution(
                ctx.tool_permission,
                ctx.is_foreign_file,
                ctx.has_recon,
                ctx.guard_warnings,
            )

            # Update state snapshot (not persisted until record_outcome)
            state.curiosity = curiosity
            state.caution = caution

            return compute_emotion_modifier(curiosity, trust, caution)
        except Exception:
            logger.debug("compute_modifier failed for %s, returning 1.0", tool_id, exc_info=True)
            return 1.0

    def record_outcome(self, tool_id: str, success: bool, context: Optional[EmotionContext] = None) -> EmotionState:
        """Record a tool invocation outcome and update emotional state.

        Persists to disk after every call.
        """
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
                state.curiosity = compute_curiosity(state.usage_count, ctx.freshness_score)
                state.trust = compute_trust(state.trust, success, ctx.guard_warnings)
                state.caution = compute_caution(
                    ctx.tool_permission,
                    ctx.is_foreign_file,
                    ctx.has_recon,
                    ctx.guard_warnings,
                )
                state.last_updated = time.time()

                self._save()
                return state
        except Exception:
            logger.warning("record_outcome failed for %s", tool_id, exc_info=True)
            return self.get_emotion_state(tool_id)

    def get_modifier_breakdown(self, tool_id: str, context: Optional[EmotionContext] = None) -> Dict[str, float]:
        """Return a breakdown dict for debugging / UI display."""
        try:
            state = self.get_emotion_state(tool_id)
            ctx = context or EmotionContext()

            curiosity = compute_curiosity(state.usage_count, ctx.freshness_score)
            trust = state.trust
            caution = compute_caution(
                ctx.tool_permission,
                ctx.is_foreign_file,
                ctx.has_recon,
                ctx.guard_warnings,
            )
            modifier = compute_emotion_modifier(curiosity, trust, caution)

            return {
                "tool_id": tool_id,
                "curiosity": round(curiosity, 4),
                "trust": round(trust, 4),
                "caution": round(caution, 4),
                "modifier": round(modifier, 4),
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
                "usage_count": 0,
                "success_count": 0,
                "failure_count": 0,
            }


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
