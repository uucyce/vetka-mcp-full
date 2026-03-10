"""
Tests for REFLEX A/B Testing — Phase 173.P4

MARKER_173.P4.TESTS

Tests experiment config, deterministic assignment, metrics
collection, comparison aggregation, persistence, and REST.

T4.1  — ExperimentConfig defaults
T4.2  — ExperimentConfig round-trip
T4.3  — assign_arm deterministic
T4.4  — assign_arm stable across calls
T4.5  — assign_arm split ratio ~50/50
T4.6  — assign_arm empty pipeline_id
T4.7  — ExperimentMetrics round-trip
T4.8  — Store record and get_all
T4.9  — Store get_arm_metrics filter
T4.10 — Store get_comparison aggregation
T4.11 — Store comparison deltas
T4.12 — Store persistence (tmp_path)
T4.13 — Store clear resets
T4.14 — Singleton get/reset
T4.15 — REST: GET /api/reflex/experiment
T4.16 — REST: GET /api/reflex/experiment/metrics
T4.17 — Pipeline _get_reflex_experiment_arm
T4.18 — is_experiment_active checks flag + config
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── T4.1-T4.2: Config ───────────────────────────────────────────

class TestExperimentConfig:
    """T4.1-T4.2: ExperimentConfig dataclass."""

    def test_defaults(self):
        from src.services.reflex_experiment import ExperimentConfig
        cfg = ExperimentConfig()
        assert cfg.experiment_id == "reflex_active_v1"
        assert cfg.split_ratio == 0.5
        assert cfg.enabled is True

    def test_round_trip(self):
        from src.services.reflex_experiment import ExperimentConfig
        cfg = ExperimentConfig(experiment_id="test_v2", split_ratio=0.3, enabled=False)
        d = cfg.to_dict()
        restored = ExperimentConfig.from_dict(d)
        assert restored.experiment_id == "test_v2"
        assert restored.split_ratio == 0.3
        assert restored.enabled is False


# ─── T4.3-T4.6: Assignment ───────────────────────────────────────

class TestAssignment:
    """T4.3-T4.6: Deterministic arm assignment."""

    def test_deterministic(self):
        from src.services.reflex_experiment import assign_arm
        arm1 = assign_arm("task_abc")
        arm2 = assign_arm("task_abc")
        assert arm1 == arm2  # Same input → same output

    def test_stable_across_calls(self):
        from src.services.reflex_experiment import assign_arm, ExperimentConfig
        cfg = ExperimentConfig()
        arms = [assign_arm("task_xyz", cfg) for _ in range(100)]
        assert len(set(arms)) == 1  # All same

    def test_split_ratio_approximate(self):
        from src.services.reflex_experiment import assign_arm, ExperimentConfig
        cfg = ExperimentConfig(split_ratio=0.5)
        arms = [assign_arm(f"task_{i}", cfg) for i in range(1000)]
        treatment_count = arms.count("treatment")
        control_count = arms.count("control")
        # Should be roughly 50/50 (±10%)
        assert 350 <= treatment_count <= 650, f"treatment={treatment_count}, control={control_count}"
        assert treatment_count + control_count == 1000

    def test_empty_pipeline_id(self):
        from src.services.reflex_experiment import assign_arm
        assert assign_arm("") == "control"
        assert assign_arm("", None) == "control"

    def test_different_ids_different_arms(self):
        """Different pipeline IDs should produce a mix of arms."""
        from src.services.reflex_experiment import assign_arm
        arms = set()
        for i in range(100):
            arms.add(assign_arm(f"unique_task_{i}"))
        # Should have both arms represented
        assert "control" in arms
        assert "treatment" in arms


# ─── T4.7: Metrics ────────────────────────────────────────────────

class TestMetrics:
    """T4.7: ExperimentMetrics round-trip."""

    def test_round_trip(self):
        from src.services.reflex_experiment import ExperimentMetrics
        m = ExperimentMetrics(
            pipeline_id="pipe_1",
            arm="treatment",
            success_rate=0.85,
            match_rate=0.7,
            duration_ms=5000,
            tokens_used=12000,
            schemas_filtered=3,
        )
        d = m.to_dict()
        restored = ExperimentMetrics.from_dict(d)
        assert restored.pipeline_id == "pipe_1"
        assert restored.arm == "treatment"
        assert restored.success_rate == 0.85
        assert restored.tokens_used == 12000


# ─── T4.8-T4.13: Store ───────────────────────────────────────────

class TestExperimentStore:
    """T4.8-T4.13: ReflexExperimentStore operations."""

    def test_record_and_get_all(self, tmp_path):
        from src.services.reflex_experiment import ReflexExperimentStore, ExperimentMetrics
        store = ReflexExperimentStore(path=tmp_path / "exp.json")
        store.record_metrics(ExperimentMetrics(pipeline_id="p1", arm="control", success_rate=0.8))
        store.record_metrics(ExperimentMetrics(pipeline_id="p2", arm="treatment", success_rate=0.9))
        all_m = store.get_all_metrics()
        assert len(all_m) == 2

    def test_get_arm_metrics(self, tmp_path):
        from src.services.reflex_experiment import ReflexExperimentStore, ExperimentMetrics
        store = ReflexExperimentStore(path=tmp_path / "exp.json")
        store.record_metrics(ExperimentMetrics(pipeline_id="p1", arm="control"))
        store.record_metrics(ExperimentMetrics(pipeline_id="p2", arm="treatment"))
        store.record_metrics(ExperimentMetrics(pipeline_id="p3", arm="control"))
        ctrl = store.get_arm_metrics("control")
        treat = store.get_arm_metrics("treatment")
        assert len(ctrl) == 2
        assert len(treat) == 1

    def test_comparison_aggregation(self, tmp_path):
        from src.services.reflex_experiment import ReflexExperimentStore, ExperimentMetrics
        store = ReflexExperimentStore(path=tmp_path / "exp.json")
        store.record_metrics(ExperimentMetrics(arm="control", success_rate=0.7, duration_ms=3000))
        store.record_metrics(ExperimentMetrics(arm="control", success_rate=0.9, duration_ms=5000))
        store.record_metrics(ExperimentMetrics(arm="treatment", success_rate=0.85, duration_ms=2000))
        store.record_metrics(ExperimentMetrics(arm="treatment", success_rate=0.95, duration_ms=4000))
        comp = store.get_comparison()
        assert comp["control"]["count"] == 2
        assert comp["treatment"]["count"] == 2
        assert comp["control"]["avg_success_rate"] == 0.8  # (0.7+0.9)/2
        assert comp["treatment"]["avg_success_rate"] == 0.9  # (0.85+0.95)/2

    def test_comparison_deltas(self, tmp_path):
        from src.services.reflex_experiment import ReflexExperimentStore, ExperimentMetrics
        store = ReflexExperimentStore(path=tmp_path / "exp.json")
        store.record_metrics(ExperimentMetrics(arm="control", success_rate=0.8, tokens_used=10000))
        store.record_metrics(ExperimentMetrics(arm="treatment", success_rate=0.9, tokens_used=8000))
        comp = store.get_comparison()
        assert comp["deltas"]["success_rate_delta"] == pytest.approx(0.1, abs=0.001)
        assert comp["deltas"]["tokens_used_delta"] == -2000

    def test_persistence(self, tmp_path):
        from src.services.reflex_experiment import ReflexExperimentStore, ExperimentMetrics
        path = tmp_path / "exp.json"
        store1 = ReflexExperimentStore(path=path)
        store1.record_metrics(ExperimentMetrics(pipeline_id="p1", arm="control", success_rate=0.75))
        # Load in new store instance
        store2 = ReflexExperimentStore(path=path)
        all_m = store2.get_all_metrics()
        assert len(all_m) == 1
        assert all_m[0]["pipeline_id"] == "p1"

    def test_clear(self, tmp_path):
        from src.services.reflex_experiment import ReflexExperimentStore, ExperimentMetrics
        store = ReflexExperimentStore(path=tmp_path / "exp.json")
        store.record_metrics(ExperimentMetrics(arm="control"))
        store.record_metrics(ExperimentMetrics(arm="treatment"))
        store.clear()
        assert len(store.get_all_metrics()) == 0


# ─── T4.14: Singleton ────────────────────────────────────────────

class TestSingleton:
    """T4.14: Global store singleton."""

    def test_get_returns_same(self):
        from src.services.reflex_experiment import get_reflex_experiment, reset_reflex_experiment
        reset_reflex_experiment()
        s1 = get_reflex_experiment()
        s2 = get_reflex_experiment()
        assert s1 is s2
        reset_reflex_experiment()

    def test_reset_clears(self):
        from src.services.reflex_experiment import get_reflex_experiment, reset_reflex_experiment
        reset_reflex_experiment()
        s1 = get_reflex_experiment()
        reset_reflex_experiment()
        s2 = get_reflex_experiment()
        assert s1 is not s2
        reset_reflex_experiment()


# ─── T4.15-T4.16: REST Endpoints ─────────────────────────────────

class TestExperimentEndpoints:
    """T4.15-T4.16: REST API for experiment."""

    @pytest.mark.asyncio
    async def test_get_experiment(self):
        from src.api.routes.reflex_routes import reflex_experiment
        from src.services.reflex_experiment import ReflexExperimentStore, ExperimentMetrics

        mock_store = ReflexExperimentStore.__new__(ReflexExperimentStore)
        mock_store._config = MagicMock()
        mock_store._config.to_dict.return_value = {"experiment_id": "test", "split_ratio": 0.5}
        mock_store._config.enabled = True
        mock_store._metrics = []
        mock_store._lock = __import__("threading").Lock()

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_experiment.get_reflex_experiment", return_value=mock_store), \
             patch("src.services.reflex_experiment.REFLEX_EXPERIMENT", True):
            result = await reflex_experiment()

        assert result["enabled"] is True
        assert result["experiment_active"] is True
        assert "comparison" in result

    @pytest.mark.asyncio
    async def test_get_experiment_metrics(self):
        from src.api.routes.reflex_routes import reflex_experiment_metrics
        from src.services.reflex_experiment import ReflexExperimentStore, ExperimentMetrics

        mock_store = MagicMock()
        mock_store.get_all_metrics.return_value = [
            {"pipeline_id": "p1", "arm": "control"},
            {"pipeline_id": "p2", "arm": "treatment"},
        ]

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_experiment.get_reflex_experiment", return_value=mock_store):
            result = await reflex_experiment_metrics(arm="")

        assert result["enabled"] is True
        assert result["count"] == 2


# ─── T4.17: Pipeline integration ─────────────────────────────────

class TestPipelineExperiment:
    """T4.17: Pipeline _get_reflex_experiment_arm."""

    def test_arm_not_in_experiment(self):
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline._reflex_experiment_arm = None
        with patch("src.services.reflex_experiment.is_experiment_active", return_value=False):
            arm = pipeline._get_reflex_experiment_arm()
        assert arm == ""

    def test_arm_in_experiment(self):
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline._reflex_experiment_arm = None
        pipeline._board_task_id = "task_test_123"
        with patch("src.services.reflex_experiment.is_experiment_active", return_value=True), \
             patch("src.services.reflex_experiment.assign_arm", return_value="treatment"):
            arm = pipeline._get_reflex_experiment_arm()
        assert arm == "treatment"


# ─── T4.18: Feature flag ─────────────────────────────────────────

class TestFeatureFlag:
    """T4.18: is_experiment_active checks flag + config."""

    def test_flag_off(self):
        from src.services.reflex_experiment import is_experiment_active
        with patch("src.services.reflex_experiment.REFLEX_EXPERIMENT", False):
            assert is_experiment_active() is False

    def test_flag_on_config_disabled(self):
        from src.services.reflex_experiment import is_experiment_active, ExperimentConfig
        mock_store = MagicMock()
        mock_store.get_config.return_value = ExperimentConfig(enabled=False)
        with patch("src.services.reflex_experiment.REFLEX_EXPERIMENT", True), \
             patch("src.services.reflex_experiment.get_reflex_experiment", return_value=mock_store):
            assert is_experiment_active() is False

    def test_flag_on_config_enabled(self):
        from src.services.reflex_experiment import is_experiment_active, ExperimentConfig
        mock_store = MagicMock()
        mock_store.get_config.return_value = ExperimentConfig(enabled=True)
        with patch("src.services.reflex_experiment.REFLEX_EXPERIMENT", True), \
             patch("src.services.reflex_experiment.get_reflex_experiment", return_value=mock_store):
            assert is_experiment_active() is True
