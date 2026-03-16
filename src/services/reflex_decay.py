"""
REFLEX Score Decay & Model-Specific Tuning.

MARKER_173.P5.DECAY

Phase-specific half-life decay, success-weighted decay modifiers,
and model-specific scoring profiles for adaptive tool selection.

Replaces single DECAY_LAMBDA with intelligent adaptive decay:
  - Research tools decay slowly (half-life 45 days)
  - Fix tools decay fast (half-life 14 days)
  - Build tools decay at moderate rate (half-life 30 days)
  - Successful tools decay 2x slower (retain proven winners)
  - Failing tools decay 2x faster (forget bad choices quickly)

Model profiles define per-model FC reliability and tool limits,
used by filter engine and scorer for adaptive behavior.

Part of VETKA OS:
  VETKA > REFLEX > Decay & Tuning (this file)

@status: active
@phase: 173.P5
@depends: reflex_feedback (supplies entries), reflex_filter (reads profiles)
@used_by: reflex_feedback._aggregate_entries, reflex_routes
"""

import logging
import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─── Phase-Specific Half-Lives (days) ────────────────────────────

PHASE_HALF_LIFE: Dict[str, float] = {
    "research": 45.0,  # Research tools stay relevant longer (exploration)
    "fix": 14.0,  # Fix tools decay fast (context-specific patches)
    "build": 30.0,  # Build tools — moderate retention
    "*": 30.0,  # Default fallback
}


# ─── Decay Configuration ────────────────────────────────────────


@dataclass
class DecayConfig:
    """MARKER_173.P5.CONFIG — Tunable decay parameters.

    Attributes:
        phase_half_lives: Mapping of phase_type → half-life in days.
        success_boost_threshold: Success rate above which decay is slowed.
        success_boost_multiplier: Half-life multiplier for successful tools.
        failure_threshold: Success rate below which decay is accelerated.
        failure_multiplier: Half-life multiplier for failing tools.
        min_half_life: Floor to prevent ultra-fast decay.
        max_half_life: Ceiling to prevent tools from never decaying.
    """

    phase_half_lives: Dict[str, float] = field(
        default_factory=lambda: dict(PHASE_HALF_LIFE)
    )
    success_boost_threshold: float = 0.8
    success_boost_multiplier: float = 2.0
    failure_threshold: float = 0.3
    failure_multiplier: float = 0.5
    min_half_life: float = 7.0  # 1 week minimum
    max_half_life: float = 90.0  # 3 months maximum

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DecayConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─── Model Profiles ─────────────────────────────────────────────


@dataclass
class ModelProfile:
    """MARKER_173.P5.PROFILE — Per-model FC characteristics.

    Attributes:
        model_name: Model identifier (matches preset model names).
        fc_reliability: How reliably the model follows FC instructions (0-1).
        max_tools: Maximum tools this model handles well in a single FC call.
        prefer_simple: Whether model performs better with simpler tool schemas.
        score_boost: Global score adjustment applied to all tools for this model.
    """

    model_name: str = ""
    fc_reliability: float = 0.8
    max_tools: int = 15
    prefer_simple: bool = False
    score_boost: float = 0.0  # Global adjustment (-0.2 to +0.2)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelProfile":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─── Known Model Profiles ───────────────────────────────────────

MODEL_PROFILES: Dict[str, ModelProfile] = {
    # Bronze tier
    "qwen3-30b": ModelProfile(
        model_name="qwen3-30b",
        fc_reliability=0.75,
        max_tools=12,
        prefer_simple=True,
    ),
    "qwen3-coder-flash": ModelProfile(
        model_name="qwen3-coder-flash",
        fc_reliability=0.70,
        max_tools=8,
        prefer_simple=True,
    ),
    "mimo-v2-flash": ModelProfile(
        model_name="mimo-v2-flash",
        fc_reliability=0.60,
        max_tools=5,
        prefer_simple=True,
    ),
    # Silver tier
    "kimi-k2.5": ModelProfile(
        model_name="kimi-k2.5",
        fc_reliability=0.90,
        max_tools=30,
        prefer_simple=False,
    ),
    "qwen3-coder": ModelProfile(
        model_name="qwen3-coder",
        fc_reliability=0.85,
        max_tools=15,
        prefer_simple=False,
    ),
    "qwen3.5:latest": ModelProfile(
        model_name="qwen3.5:latest",
        fc_reliability=0.86,
        max_tools=10,
        prefer_simple=True,
    ),
    "qwen3:8b": ModelProfile(
        model_name="qwen3:8b",
        fc_reliability=0.82,
        max_tools=8,
        prefer_simple=True,
    ),
    "qwen2.5:7b": ModelProfile(
        model_name="qwen2.5:7b",
        fc_reliability=0.80,
        max_tools=8,
        prefer_simple=True,
    ),
    "qwen2.5:3b": ModelProfile(
        model_name="qwen2.5:3b",
        fc_reliability=0.68,
        max_tools=4,
        prefer_simple=True,
    ),
    "glm-4.7-flash": ModelProfile(
        model_name="glm-4.7-flash",
        fc_reliability=0.75,
        max_tools=10,
        prefer_simple=True,
    ),
    # Gold tier
    "qwen3-235b": ModelProfile(
        model_name="qwen3-235b",
        fc_reliability=0.95,
        max_tools=45,
        prefer_simple=False,
    ),
    # Research (all tiers)
    "grok-fast-4.1": ModelProfile(
        model_name="grok-fast-4.1",
        fc_reliability=0.90,
        max_tools=20,
        prefer_simple=False,
    ),
    # GPT option
    "gpt-5.2": ModelProfile(
        model_name="gpt-5.2",
        fc_reliability=0.95,
        max_tools=45,
        prefer_simple=False,
    ),
    "deepseek-r1:8b": ModelProfile(
        model_name="deepseek-r1:8b",
        fc_reliability=0.74,
        max_tools=6,
        prefer_simple=True,
    ),
    "phi4-mini:latest": ModelProfile(
        model_name="phi4-mini:latest",
        fc_reliability=0.78,
        max_tools=4,
        prefer_simple=True,
    ),
    "qwen2.5vl:3b": ModelProfile(
        model_name="qwen2.5vl:3b",
        fc_reliability=0.72,
        max_tools=4,
        prefer_simple=True,
    ),
    "embeddinggemma:300m": ModelProfile(
        model_name="embeddinggemma:300m",
        fc_reliability=1.0,
        max_tools=1,
        prefer_simple=True,
    ),
    # MARKER_177.A2.1: New localguys models (2026-03)
    "gemma3:4b": ModelProfile(
        model_name="gemma3:4b",
        fc_reliability=0.72,
        max_tools=5,
        prefer_simple=True,
    ),
    "gemma3:12b": ModelProfile(
        model_name="gemma3:12b",
        fc_reliability=0.81,
        max_tools=9,
        prefer_simple=True,
    ),
    "mistral-nemo": ModelProfile(
        model_name="mistral-nemo",
        fc_reliability=0.84,
        max_tools=12,
        prefer_simple=False,
    ),
}

DEFAULT_PROFILE = ModelProfile(
    model_name="default",
    fc_reliability=0.80,
    max_tools=15,
    prefer_simple=False,
)


# ─── Decay Engine ────────────────────────────────────────────────


class ReflexDecayEngine:
    """MARKER_173.P5.ENGINE — Computes adaptive decay weights.

    Replaces fixed exp(-DECAY_LAMBDA * age_days) with:
    1. Phase-specific half-life → λ = ln(2) / half_life
    2. Success-weighted multiplier → high-success tools decay slower
    3. Clamped half-life bounds → prevent extreme decay rates

    Usage:
        engine = ReflexDecayEngine()
        weight = engine.compute_weight(age_days=10, phase_type="fix", success_rate=0.9)
    """

    def __init__(self, config: Optional[DecayConfig] = None):
        self._config = config or DecayConfig()

    @property
    def config(self) -> DecayConfig:
        return self._config

    def get_half_life(
        self,
        phase_type: str = "*",
        success_rate: Optional[float] = None,
    ) -> float:
        """Get effective half-life for a phase + success combination.

        Args:
            phase_type: Pipeline phase (research, fix, build, *)
            success_rate: Optional historical success rate (0-1)

        Returns:
            Effective half-life in days (clamped to min/max bounds).
        """
        # Base half-life from phase
        base_hl = self._config.phase_half_lives.get(
            phase_type,
            self._config.phase_half_lives.get("*", 30.0),
        )

        # Success-weighted adjustment
        if success_rate is not None:
            if success_rate >= self._config.success_boost_threshold:
                base_hl *= self._config.success_boost_multiplier
            elif success_rate <= self._config.failure_threshold:
                base_hl *= self._config.failure_multiplier

        # Clamp
        return max(self._config.min_half_life, min(self._config.max_half_life, base_hl))

    def compute_weight(
        self,
        age_days: float,
        phase_type: str = "*",
        success_rate: Optional[float] = None,
    ) -> float:
        """Compute decay weight for a feedback entry.

        Args:
            age_days: Age of the feedback entry in days.
            phase_type: Pipeline phase for this entry.
            success_rate: Historical success rate for the tool (optional).

        Returns:
            Weight in (0, 1] — 1.0 for brand new, approaches 0 over time.
        """
        if age_days <= 0:
            return 1.0

        half_life = self.get_half_life(phase_type, success_rate)
        decay_lambda = math.log(2) / half_life
        return math.exp(-decay_lambda * age_days)

    @staticmethod
    def half_life_to_lambda(half_life_days: float) -> float:
        """Convert half-life (days) to exponential decay lambda.

        λ = ln(2) / half_life
        weight(t) = exp(-λ * t) → weight(half_life) = 0.5
        """
        if half_life_days <= 0:
            return 1.0  # Instant decay
        return math.log(2) / half_life_days


# ─── Model Profile Lookup ───────────────────────────────────────


def get_model_profile(model_name: str) -> ModelProfile:
    """Get scoring profile for a specific model.

    Supports fuzzy matching: "qwen3-coder" matches "qwen3-coder".
    Falls back to DEFAULT_PROFILE for unknown models.

    Args:
        model_name: Model name or identifier.

    Returns:
        ModelProfile with FC characteristics.
    """
    if not model_name:
        return DEFAULT_PROFILE

    name_lower = model_name.lower().strip()

    # Exact match
    if name_lower in MODEL_PROFILES:
        return MODEL_PROFILES[name_lower]

    # Fuzzy match: check if model_name contains or is contained by a known key
    for key, profile in MODEL_PROFILES.items():
        if key in name_lower or name_lower in key:
            return profile

    return DEFAULT_PROFILE


def get_all_model_profiles() -> Dict[str, Dict[str, Any]]:
    """Get all known model profiles as dicts (for REST API).

    Returns:
        Dict of {model_name: profile_dict}
    """
    return {name: p.to_dict() for name, p in MODEL_PROFILES.items()}


# ─── Convenience: Decay Summary ─────────────────────────────────


def get_decay_summary() -> Dict[str, Any]:
    """Get human-readable summary of decay configuration.

    Returns:
        Dict with phase half-lives, lambdas, and profile info.
    """
    engine = ReflexDecayEngine()
    config = engine.config

    phases = {}
    for phase, hl in config.phase_half_lives.items():
        lam = engine.half_life_to_lambda(hl)
        # Example: weight at 7/14/30/60 days
        phases[phase] = {
            "half_life_days": hl,
            "decay_lambda": round(lam, 6),
            "weight_at_7d": round(math.exp(-lam * 7), 4),
            "weight_at_14d": round(math.exp(-lam * 14), 4),
            "weight_at_30d": round(math.exp(-lam * 30), 4),
            "weight_at_60d": round(math.exp(-lam * 60), 4),
        }

    # Success-weighted examples
    success_examples = {}
    for phase in ["research", "fix", "build"]:
        base_hl = engine.get_half_life(phase)
        boosted_hl = engine.get_half_life(phase, success_rate=0.9)
        penalized_hl = engine.get_half_life(phase, success_rate=0.2)
        success_examples[phase] = {
            "base_half_life": base_hl,
            "success_boosted_half_life": boosted_hl,
            "failure_penalized_half_life": penalized_hl,
        }

    return {
        "phases": phases,
        "success_weighted_examples": success_examples,
        "config": config.to_dict(),
        "model_profiles_count": len(MODEL_PROFILES),
    }
