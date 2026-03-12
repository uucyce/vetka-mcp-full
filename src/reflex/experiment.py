"""
REFLEX A/B Testing — Experiment Framework.

MARKER_173.P4.EXPERIMENT

Measures whether active REFLEX filtering improves pipeline quality.
Stable assignment per pipeline_id (deterministic hash), metrics
collection per arm, and aggregation for comparison.

Experiment arms:
  control   — All tools, no filtering (REFLEX_ACTIVE bypassed)
  treatment — REFLEX filtered schemas (active filtering)

Metrics per pipeline run:
  - success_rate: verifier pass/total
  - tokens_used: total prompt+completion tokens (from pipeline stats)
  - duration_ms: pipeline wall-clock time
  - match_rate: REFLEX recommendation accuracy
  - schemas_filtered: number of schemas removed by filter
  - fallback_count: number of filter fallbacks triggered

Part of VETKA OS:
  VETKA > REFLEX > Experiment (this file)

@status: active
@phase: 173.P4
@depends: reflex_filter, reflex_streaming
@used_by: agent_pipeline.py, reflex_routes.py
"""

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Feature flag ─────────────────────────────────────────────────

REFLEX_EXPERIMENT = os.environ.get("REFLEX_EXPERIMENT", "0") == "1"

# ─── Data dir ─────────────────────────────────────────────────────

try:
    from src.services.reflex_feedback import REFLEX_DATA_DIR
except ImportError:
    REFLEX_DATA_DIR = Path("data/reflex")


# ─── Experiment Config ────────────────────────────────────────────

@dataclass
class ExperimentConfig:
    """MARKER_173.P4.CONFIG — A/B experiment definition."""
    experiment_id: str = "reflex_active_v1"
    control_description: str = "All tools, no filtering"
    treatment_description: str = "REFLEX filtered schemas"
    split_ratio: float = 0.5   # 0.5 = 50/50 split
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExperimentConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─── Run Metrics ──────────────────────────────────────────────────

@dataclass
class ExperimentMetrics:
    """MARKER_173.P4.METRICS — Per-run metrics for one pipeline execution."""
    pipeline_id: str = ""
    arm: str = ""                   # "control" or "treatment"
    experiment_id: str = ""
    timestamp: float = field(default_factory=time.time)
    # Quality metrics
    success_rate: float = 0.0       # verifier pass / total subtasks
    match_rate: float = 0.0         # REFLEX recommendation accuracy
    # Efficiency metrics
    duration_ms: float = 0.0        # pipeline wall-clock time
    tokens_used: int = 0            # total tokens (prompt + completion)
    schemas_filtered: int = 0       # schemas removed by filter
    tokens_saved_estimate: int = 0  # tokens saved by filtering
    # Reliability metrics
    fallback_count: int = 0         # filter fallbacks triggered
    subtask_count: int = 0          # total subtasks executed

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExperimentMetrics":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─── Assignment ───────────────────────────────────────────────────

def assign_arm(pipeline_id: str, config: Optional[ExperimentConfig] = None) -> str:
    """MARKER_173.P4.ASSIGN — Deterministic arm assignment from pipeline_id.

    Uses SHA-256 hash to ensure stable assignment:
    same pipeline_id always gets same arm.

    Args:
        pipeline_id: Unique pipeline/task identifier
        config: Experiment config (uses default if None)

    Returns:
        "control" or "treatment"
    """
    if not config:
        config = ExperimentConfig()

    if not pipeline_id:
        return "control"  # Default for unknown

    # Deterministic hash
    h = hashlib.sha256(f"{config.experiment_id}:{pipeline_id}".encode()).hexdigest()
    # Convert first 8 hex chars to float in [0, 1)
    hash_value = int(h[:8], 16) / 0xFFFFFFFF

    return "treatment" if hash_value < config.split_ratio else "control"


# ─── Experiment Store ─────────────────────────────────────────────

class ReflexExperimentStore:
    """MARKER_173.P4.STORE — Persists experiment results to disk.

    Stores:
    - config: experiment configuration
    - metrics: list of per-run metrics (appended)

    File: data/reflex/experiment_results.json
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = path or (REFLEX_DATA_DIR / "experiment_results.json")
        self._lock = threading.Lock()
        self._config = ExperimentConfig()
        self._metrics: List[ExperimentMetrics] = []
        self._load()

    def _load(self):
        """Load from disk."""
        try:
            if self._path.exists():
                with open(self._path, "r") as f:
                    data = json.load(f)
                if "config" in data:
                    self._config = ExperimentConfig.from_dict(data["config"])
                if "metrics" in data:
                    self._metrics = [ExperimentMetrics.from_dict(m) for m in data["metrics"]]
        except Exception as e:
            logger.debug("[REFLEX Experiment] Load error (non-fatal): %s", e)

    def _save(self):
        """Persist to disk."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w") as f:
                json.dump({
                    "config": self._config.to_dict(),
                    "metrics": [m.to_dict() for m in self._metrics[-500:]],  # Keep last 500
                }, f, indent=2)
        except Exception as e:
            logger.debug("[REFLEX Experiment] Save error (non-fatal): %s", e)

    def get_config(self) -> ExperimentConfig:
        with self._lock:
            return self._config

    def set_config(self, config: ExperimentConfig):
        with self._lock:
            self._config = config
            self._save()

    def record_metrics(self, metrics: ExperimentMetrics):
        """Append pipeline run metrics."""
        with self._lock:
            self._metrics.append(metrics)
            self._save()

    def get_all_metrics(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [m.to_dict() for m in self._metrics]

    def get_arm_metrics(self, arm: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [m.to_dict() for m in self._metrics if m.arm == arm]

    def get_comparison(self) -> Dict[str, Any]:
        """MARKER_173.P4.COMPARE — Aggregate comparison between arms.

        Returns:
            Dict with per-arm averages and deltas.
        """
        with self._lock:
            control = [m for m in self._metrics if m.arm == "control"]
            treatment = [m for m in self._metrics if m.arm == "treatment"]

        def _avg(metrics: List[ExperimentMetrics], field: str) -> float:
            vals = [getattr(m, field, 0) for m in metrics]
            return sum(vals) / len(vals) if vals else 0.0

        ctrl_stats = {
            "count": len(control),
            "avg_success_rate": round(_avg(control, "success_rate"), 3),
            "avg_match_rate": round(_avg(control, "match_rate"), 3),
            "avg_duration_ms": round(_avg(control, "duration_ms"), 1),
            "avg_tokens_used": round(_avg(control, "tokens_used")),
            "total_tokens_saved": sum(m.tokens_saved_estimate for m in control),
        }
        treat_stats = {
            "count": len(treatment),
            "avg_success_rate": round(_avg(treatment, "success_rate"), 3),
            "avg_match_rate": round(_avg(treatment, "match_rate"), 3),
            "avg_duration_ms": round(_avg(treatment, "duration_ms"), 1),
            "avg_tokens_used": round(_avg(treatment, "tokens_used")),
            "total_tokens_saved": sum(m.tokens_saved_estimate for m in treatment),
        }

        # Compute deltas (treatment - control)
        deltas = {}
        if ctrl_stats["count"] > 0 and treat_stats["count"] > 0:
            deltas = {
                "success_rate_delta": round(treat_stats["avg_success_rate"] - ctrl_stats["avg_success_rate"], 3),
                "match_rate_delta": round(treat_stats["avg_match_rate"] - ctrl_stats["avg_match_rate"], 3),
                "duration_ms_delta": round(treat_stats["avg_duration_ms"] - ctrl_stats["avg_duration_ms"], 1),
                "tokens_used_delta": round(treat_stats["avg_tokens_used"] - ctrl_stats["avg_tokens_used"]),
            }

        return {
            "experiment_id": self._config.experiment_id,
            "total_runs": len(self._metrics),
            "control": ctrl_stats,
            "treatment": treat_stats,
            "deltas": deltas,
        }

    def clear(self):
        """Clear all metrics (for testing/reset)."""
        with self._lock:
            self._metrics.clear()
            self._save()


# ─── Singleton ────────────────────────────────────────────────────

_global_store: Optional[ReflexExperimentStore] = None
_global_lock = threading.Lock()


def get_reflex_experiment() -> ReflexExperimentStore:
    """Public accessor for the global experiment store."""
    global _global_store
    if _global_store is None:
        with _global_lock:
            if _global_store is None:
                _global_store = ReflexExperimentStore()
    return _global_store


def reset_reflex_experiment():
    """Reset global store (for testing)."""
    global _global_store
    with _global_lock:
        _global_store = None


def is_experiment_active() -> bool:
    """Check if A/B experiment is enabled."""
    return REFLEX_EXPERIMENT and get_reflex_experiment().get_config().enabled
