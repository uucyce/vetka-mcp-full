# ========================================
# MARKER: Phase 72.4 + 72.5 Dependency Calculator Tests
# Date: 2026-01-19
# File: tests/scanners/test_dependency_calculator.py
# Purpose: Test Kimi K2 Enhanced formula and Qdrant integration
# Phase 72.5: Sigmoid center 0.35, semantic gating, temporal floor
# ========================================
"""
Tests for DependencyCalculator (Phase 72.4 + 72.5).

Test categories:
1. Scoring formula validation
2. Temporal decay calculation (with floor)
3. Sigmoid normalization (center = 0.35)
4. Semantic gating (threshold = 0.5)
5. Edge cases (missing timestamps, extreme values)
6. Batch processing
7. Qdrant integration (mock)
8. Real-world scenarios
"""

import math
import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from unittest.mock import Mock, MagicMock

from src.scanners.dependency_calculator import (
    DependencyCalculator,
    ScoringConfig,
    ScoringInput,
    ScoringResult,
    FileMetadata,
    QdrantSemanticProvider,
    calculate_dependency_score,
    combine_import_and_semantic,
    DEFAULT_CONFIG,
)
from src.scanners.dependency import Dependency, DependencyType


class TestScoringConfig:
    """Test ScoringConfig validation (Phase 72.5 Enhanced)."""

    def test_default_config_valid(self):
        """Default config has weights summing to 1.0."""
        config = ScoringConfig()
        total = config.w_import + config.w_semantic + config.w_reference + config.w_rrf
        assert abs(total - 1.0) < 0.001

    def test_custom_config_valid(self):
        """Custom config with valid weights."""
        config = ScoringConfig(
            w_import=0.5,
            w_semantic=0.3,
            w_reference=0.15,
            w_rrf=0.05
        )
        assert config.w_import == 0.5

    def test_invalid_weights_raises_error(self):
        """Invalid weights should raise ValueError."""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            ScoringConfig(
                w_import=0.5,
                w_semantic=0.5,
                w_reference=0.5,
                w_rrf=0.5
            )

    def test_negative_weight_raises_error(self):
        """Negative weights should raise ValueError."""
        with pytest.raises(ValueError, match="must be >= 0"):
            ScoringConfig(
                w_import=-0.1,
                w_semantic=0.6,
                w_reference=0.4,
                w_rrf=0.1
            )

    def test_invalid_sigmoid_center_raises_error(self):
        """Sigmoid center outside [0, 1] should raise ValueError."""
        with pytest.raises(ValueError, match="sigmoid_center must be in"):
            ScoringConfig(sigmoid_center=-0.5)

        with pytest.raises(ValueError, match="sigmoid_center must be in"):
            ScoringConfig(sigmoid_center=1.5)

    def test_invalid_temporal_floor_raises_error(self):
        """Temporal floor outside [0, 1] should raise ValueError."""
        with pytest.raises(ValueError, match="temporal_floor must be in"):
            ScoringConfig(temporal_floor=-0.1)

        with pytest.raises(ValueError, match="temporal_floor must be in"):
            ScoringConfig(temporal_floor=1.5)

    def test_invalid_tau_days_raises_error(self):
        """tau_days <= 0 should raise ValueError."""
        with pytest.raises(ValueError, match="tau_days must be > 0"):
            ScoringConfig(tau_days=0)

        with pytest.raises(ValueError, match="tau_days must be > 0"):
            ScoringConfig(tau_days=-10)

    def test_invalid_sigmoid_steepness_raises_error(self):
        """sigmoid_steepness <= 0 should raise ValueError."""
        with pytest.raises(ValueError, match="sigmoid_steepness must be > 0"):
            ScoringConfig(sigmoid_steepness=0)

    def test_invalid_semantic_gate_threshold_raises_error(self):
        """semantic_gate_threshold outside [0, 1] should raise ValueError."""
        with pytest.raises(ValueError, match="semantic_gate_threshold must be in"):
            ScoringConfig(semantic_gate_threshold=1.5)


class TestFileMetadata:
    """Test FileMetadata dataclass."""

    def test_minimal_metadata(self):
        """Create metadata with only path."""
        meta = FileMetadata(path="/src/main.py")
        assert meta.path == "/src/main.py"
        assert meta.created_at is None
        assert meta.rrf_score == 0.5

    def test_full_metadata(self):
        """Create metadata with all fields."""
        now = datetime.now()
        meta = FileMetadata(
            path="/src/utils.py",
            created_at=now,
            modified_at=now,
            rrf_score=0.8,
            has_references=True
        )
        assert meta.created_at == now
        assert meta.rrf_score == 0.8


class TestTemporalDecay:
    """Test temporal decay calculation E(ΔT) with Phase 72.5 floor."""

    @pytest.fixture
    def calculator(self) -> DependencyCalculator:
        return DependencyCalculator()

    def test_same_day_high_decay(self, calculator: DependencyCalculator):
        """Same day = high decay factor (~1.0)."""
        now = datetime.now()
        decay = calculator._calculate_temporal_decay(now, now)
        # Phase 72.5: floor=0.2, so decay = 0.2 + 0.8*1.0 = 1.0
        assert decay > 0.95  # Very close to 1.0

    def test_one_day_decay(self, calculator: DependencyCalculator):
        """1 day delta = ~0.97 decay (with floor)."""
        source = datetime.now()
        target = source + timedelta(days=1)
        decay = calculator._calculate_temporal_decay(source, target)
        # Phase 72.5: E(ΔT) = 0.2 + 0.8 * e^(-1/30)
        raw = math.exp(-1 / 30)  # ≈ 0.967
        expected = 0.2 + 0.8 * raw  # ≈ 0.97
        assert abs(decay - expected) < 0.01

    def test_30_days_decay(self, calculator: DependencyCalculator):
        """30 days = ~0.49 decay (with floor)."""
        source = datetime.now()
        target = source + timedelta(days=30)
        decay = calculator._calculate_temporal_decay(source, target)
        # Phase 72.5: E(ΔT) = 0.2 + 0.8 * e^(-1) ≈ 0.2 + 0.8*0.368 = 0.49
        raw = math.exp(-1)  # ≈ 0.368
        expected = 0.2 + 0.8 * raw  # ≈ 0.49
        assert abs(decay - expected) < 0.02

    def test_90_days_decay(self, calculator: DependencyCalculator):
        """90 days = ~0.24 decay (with floor, not 0.05)."""
        source = datetime.now()
        target = source + timedelta(days=90)
        decay = calculator._calculate_temporal_decay(source, target)
        # Phase 72.5: E(ΔT) = 0.2 + 0.8 * e^(-3) ≈ 0.2 + 0.8*0.05 = 0.24
        raw = math.exp(-3)  # ≈ 0.05
        expected = 0.2 + 0.8 * raw  # ≈ 0.24
        assert abs(decay - expected) < 0.02

    def test_very_old_file_has_floor(self, calculator: DependencyCalculator):
        """Very old files (365 days) still have 20% floor."""
        source = datetime.now()
        target = source + timedelta(days=365)
        decay = calculator._calculate_temporal_decay(source, target)
        # Phase 72.5: floor guarantees minimum 0.2
        assert decay >= 0.2

    def test_causality_violation_zero(self, calculator: DependencyCalculator):
        """Source after target = 0 decay (causality violation)."""
        target = datetime.now()
        source = target + timedelta(days=1)  # Source created AFTER target
        decay = calculator._calculate_temporal_decay(source, target)
        assert decay == 0.0

    def test_missing_timestamps_neutral(self, calculator: DependencyCalculator):
        """Missing timestamps = neutral decay (0.5)."""
        decay = calculator._calculate_temporal_decay(None, None)
        assert decay == 0.5

        decay = calculator._calculate_temporal_decay(datetime.now(), None)
        assert decay == 0.5


class TestSigmoid:
    """Test sigmoid normalization (Phase 72.5: center = 0.35)."""

    @pytest.fixture
    def calculator(self) -> DependencyCalculator:
        return DependencyCalculator()

    def test_sigmoid_center(self, calculator: DependencyCalculator):
        """Sigmoid at center (0.35) = 0.5."""
        # Phase 72.5: center shifted from 0.5 to 0.35
        result = calculator._sigmoid(0.35)
        assert abs(result - 0.5) < 0.01

    def test_sigmoid_at_old_center(self, calculator: DependencyCalculator):
        """Sigmoid at 0.5 (old center) is now > 0.5."""
        # Phase 72.5: 0.5 is above new center, so output > 0.5
        result = calculator._sigmoid(0.5)
        assert result > 0.7  # Should be ~0.86

    def test_sigmoid_low(self, calculator: DependencyCalculator):
        """Sigmoid at 0 is very low."""
        result = calculator._sigmoid(0.0)
        # Phase 72.5: with center=0.35, σ(0) = 1/(1+e^(-12*(0-0.35))) ≈ 0.015
        assert result < 0.03

    def test_sigmoid_high(self, calculator: DependencyCalculator):
        """Sigmoid at 1 is high (~0.9999)."""
        result = calculator._sigmoid(1.0)
        assert result > 0.99

    def test_sigmoid_range(self, calculator: DependencyCalculator):
        """Sigmoid always returns 0-1."""
        for x in [-10, -1, 0, 0.35, 0.5, 1, 10]:
            result = calculator._sigmoid(x)
            assert 0.0 <= result <= 1.0

    def test_sigmoid_import_only_threshold(self, calculator: DependencyCalculator):
        """Pure import (0.4 raw) now exceeds significance threshold."""
        # Phase 72.5 key fix: pure import should pass threshold 0.6
        # Raw score for I=1.0, others=0 with RRF=0.5:
        # 0.4*1.0 + 0.07*0.5 = 0.435
        raw = 0.435
        result = calculator._sigmoid(raw)
        # With center=0.35: σ(0.435) ≈ 0.74 > 0.6 ✓
        assert result > 0.6


class TestDependencyCalculator:
    """Test core DependencyCalculator (Phase 72.5 Enhanced)."""

    @pytest.fixture
    def calculator(self) -> DependencyCalculator:
        return DependencyCalculator()

    @pytest.fixture
    def now(self) -> datetime:
        return datetime.now()

    def test_explicit_import_high_score(self, calculator: DependencyCalculator, now: datetime):
        """Explicit import should give high score (Phase 72.5 key fix)."""
        input_data = ScoringInput(
            source_file=FileMetadata(path="/src/utils.py", created_at=now),
            target_file=FileMetadata(path="/src/main.py", created_at=now),
            import_confidence=1.0,  # Explicit import
            semantic_score=0.0
        )
        result = calculator.calculate(input_data)

        # Phase 72.5: Pure import should now exceed threshold 0.6
        # Raw = 0.4*1.0 + 0.07*0.5 = 0.435
        # With center=0.35: sigmoid(0.435) ≈ 0.74 > 0.6 ✓
        assert result.final_score > 0.6  # Was 0.2 before Phase 72.5
        assert result.is_significant is True
        assert result.components['I'] == 1.0

    def test_semantic_only_medium_score(self, calculator: DependencyCalculator, now: datetime):
        """Semantic similarity only = medium score (Phase 72.5: with gating)."""
        input_data = ScoringInput(
            source_file=FileMetadata(path="/docs/spec.md", created_at=now),
            target_file=FileMetadata(
                path="/src/impl.py",
                created_at=now + timedelta(days=2)
            ),
            import_confidence=0.0,
            semantic_score=0.8  # Above gate threshold 0.5
        )
        result = calculator.calculate(input_data)

        # Phase 72.5: S_gated = (0.8 - 0.5) / 0.5 = 0.6
        # E ≈ 0.2 + 0.8*0.94 ≈ 0.95 (2 days with floor)
        # Raw = 0.33 * 0.6 * 0.95 + 0.07*0.5 ≈ 0.188 + 0.035 = 0.22
        # With center=0.35: sigmoid(0.22) ≈ 0.20
        assert 0.0 < result.final_score < 0.6
        assert result.components['S_raw'] == 0.8
        assert abs(result.components['S_gated'] - 0.6) < 0.001  # Float tolerance

    def test_combined_high_score(self, calculator: DependencyCalculator, now: datetime):
        """Import + semantic + reference = high score."""
        input_data = ScoringInput(
            source_file=FileMetadata(path="/src/utils.py", created_at=now),
            target_file=FileMetadata(path="/src/main.py", created_at=now),
            import_confidence=0.9,
            semantic_score=0.7,  # Above gate threshold
            has_explicit_reference=True
        )
        result = calculator.calculate(input_data)

        # Phase 72.5: S_gated = (0.7 - 0.5) / 0.5 = 0.4
        # I=0.9, S_gated=0.4, E≈1.0, R=1.0, RRF=0.5
        # Raw = 0.4*0.9 + 0.33*0.4*1.0 + 0.2*1.0 + 0.07*0.5
        #     = 0.36 + 0.132 + 0.2 + 0.035 = 0.727
        # With center=0.35: sigmoid(0.727) ≈ 0.99
        assert result.final_score > 0.8
        assert result.is_significant is True

    def test_causality_violation_no_import(self, calculator: DependencyCalculator, now: datetime):
        """Source after target without import = zero score."""
        input_data = ScoringInput(
            source_file=FileMetadata(
                path="/src/new_utils.py",
                created_at=now + timedelta(days=5)  # Created AFTER target
            ),
            target_file=FileMetadata(path="/src/main.py", created_at=now),
            import_confidence=0.0,
            semantic_score=0.8
        )
        result = calculator.calculate(input_data)

        assert result.final_score == 0.0
        assert result.is_significant is False
        assert result.components.get('reason') == 'temporal_violation'

    def test_import_overrides_causality(self, calculator: DependencyCalculator, now: datetime):
        """Explicit import overrides causality (circular deps)."""
        input_data = ScoringInput(
            source_file=FileMetadata(
                path="/src/circular_a.py",
                created_at=now + timedelta(days=1)  # Created after
            ),
            target_file=FileMetadata(path="/src/circular_b.py", created_at=now),
            import_confidence=1.0,  # Explicit import exists
            semantic_score=0.5  # At gate threshold - should be 0
        )
        result = calculator.calculate(input_data)

        # Import should still contribute even with temporal violation
        assert result.final_score > 0.0
        assert result.components['I'] == 1.0

    def test_low_semantic_filtered(self, calculator: DependencyCalculator, now: datetime):
        """Low semantic score (< 0.3) is filtered out."""
        input_data = ScoringInput(
            source_file=FileMetadata(path="/docs/readme.md", created_at=now),
            target_file=FileMetadata(path="/src/main.py", created_at=now),
            import_confidence=0.0,
            semantic_score=0.2  # Below min_semantic_score threshold
        )
        result = calculator.calculate(input_data)

        # Semantic should be zeroed out
        assert result.components['S_gated'] == 0.0


class TestSemanticGating:
    """Test Phase 72.5 semantic gating: S' = max(0, (S - 0.5) / 0.5)."""

    @pytest.fixture
    def calculator(self) -> DependencyCalculator:
        return DependencyCalculator()

    @pytest.fixture
    def now(self) -> datetime:
        return datetime.now()

    def test_semantic_below_gate_zero(self, calculator: DependencyCalculator, now: datetime):
        """Semantic < 0.5 → gated to 0."""
        input_data = ScoringInput(
            source_file=FileMetadata(path="/a.py", created_at=now),
            target_file=FileMetadata(path="/b.py", created_at=now),
            import_confidence=0.0,
            semantic_score=0.4  # Below 0.5 gate
        )
        result = calculator.calculate(input_data)
        assert result.components['S_gated'] == 0.0

    def test_semantic_at_gate_zero(self, calculator: DependencyCalculator, now: datetime):
        """Semantic == 0.5 → gated to 0 (boundary)."""
        input_data = ScoringInput(
            source_file=FileMetadata(path="/a.py", created_at=now),
            target_file=FileMetadata(path="/b.py", created_at=now),
            import_confidence=0.0,
            semantic_score=0.5  # At gate threshold
        )
        result = calculator.calculate(input_data)
        assert result.components['S_gated'] == 0.0

    def test_semantic_above_gate_normalized(self, calculator: DependencyCalculator, now: datetime):
        """Semantic > 0.5 → normalized to (S-0.5)/0.5."""
        input_data = ScoringInput(
            source_file=FileMetadata(path="/a.py", created_at=now),
            target_file=FileMetadata(path="/b.py", created_at=now),
            import_confidence=0.0,
            semantic_score=0.75  # Above gate
        )
        result = calculator.calculate(input_data)
        # S_gated = (0.75 - 0.5) / 0.5 = 0.5
        assert abs(result.components['S_gated'] - 0.5) < 0.01

    def test_semantic_max_normalized(self, calculator: DependencyCalculator, now: datetime):
        """Semantic == 1.0 → gated to 1.0."""
        input_data = ScoringInput(
            source_file=FileMetadata(path="/a.py", created_at=now),
            target_file=FileMetadata(path="/b.py", created_at=now),
            import_confidence=0.0,
            semantic_score=1.0  # Max
        )
        result = calculator.calculate(input_data)
        # S_gated = (1.0 - 0.5) / 0.5 = 1.0
        assert abs(result.components['S_gated'] - 1.0) < 0.01

    def test_gating_filters_noise(self, calculator: DependencyCalculator, now: datetime):
        """Gating should filter out weak semantic matches as noise."""
        # Weak semantic match without import should not be significant
        input_data = ScoringInput(
            source_file=FileMetadata(path="/random.py", created_at=now),
            target_file=FileMetadata(path="/main.py", created_at=now),
            import_confidence=0.0,
            semantic_score=0.49  # Just below gate
        )
        result = calculator.calculate(input_data)

        # Should not be significant (only RRF contributes)
        assert result.is_significant is False

    def test_float_precision_at_boundary(self, calculator: DependencyCalculator, now: datetime):
        """Test float precision near gate threshold boundary."""
        # Test just above threshold (should give small but non-zero S_gated)
        input_data = ScoringInput(
            source_file=FileMetadata(path="/a.py", created_at=now),
            target_file=FileMetadata(path="/b.py", created_at=now),
            import_confidence=0.0,
            semantic_score=0.50001  # Just above 0.5
        )
        result = calculator.calculate(input_data)
        # S_gated = (0.50001 - 0.5) / 0.5 = 0.00002
        assert result.components['S_gated'] > 0.0
        assert result.components['S_gated'] < 0.001

    def test_float_precision_just_below_boundary(self, calculator: DependencyCalculator, now: datetime):
        """Test float precision just below gate threshold."""
        input_data = ScoringInput(
            source_file=FileMetadata(path="/a.py", created_at=now),
            target_file=FileMetadata(path="/b.py", created_at=now),
            import_confidence=0.0,
            semantic_score=0.49999  # Just below 0.5
        )
        result = calculator.calculate(input_data)
        # Below threshold → should be exactly 0
        assert result.components['S_gated'] == 0.0
        assert result.is_significant is False


class TestBatchProcessing:
    """Test batch score calculation."""

    def test_calculate_batch(self):
        """Test batch processing of multiple inputs."""
        calculator = DependencyCalculator()
        now = datetime.now()

        inputs = [
            ScoringInput(
                source_file=FileMetadata(path=f"/src/file{i}.py", created_at=now),
                target_file=FileMetadata(path="/src/main.py", created_at=now),
                import_confidence=i * 0.2,
                semantic_score=0.5
            )
            for i in range(5)
        ]

        results = calculator.calculate_batch(inputs)

        assert len(results) == 5
        # Higher import confidence = higher score
        scores = [r.final_score for r in results]
        assert scores == sorted(scores)  # Increasing order

    def test_find_dependencies(self):
        """Test finding significant dependencies."""
        calculator = DependencyCalculator()
        now = datetime.now()

        target = FileMetadata(path="/src/main.py", created_at=now)
        sources = [
            FileMetadata(path="/src/utils.py", created_at=now),
            FileMetadata(path="/src/config.py", created_at=now),
            FileMetadata(path="/src/helper.py", created_at=now),
        ]

        import_scores = {
            "/src/utils.py": 1.0,   # Imported
            "/src/config.py": 0.5,  # Partially resolved
            "/src/helper.py": 0.0,  # Not imported
        }
        semantic_scores = {
            "/src/utils.py": 0.8,
            "/src/config.py": 0.6,
            "/src/helper.py": 0.3,
        }

        results = calculator.find_dependencies(
            target_file=target,
            candidate_sources=sources,
            import_scores=import_scores,
            semantic_scores=semantic_scores
        )

        # Should return only significant ones, sorted by score
        assert all(r.is_significant for r in results)
        if len(results) > 1:
            assert results[0].final_score >= results[1].final_score


class TestQdrantSemanticProvider:
    """Test Qdrant integration with mock."""

    def test_search_similar_with_mock(self):
        """Test semantic search with mocked Qdrant."""
        # Mock Qdrant client
        mock_client = Mock()
        mock_client.search_by_vector.return_value = [
            {'path': '/src/utils.py', 'score': 0.9},
            {'path': '/src/helper.py', 'score': 0.7},
            {'path': '/src/config.py', 'score': 0.5},
        ]

        # Mock embedding function
        mock_embedding = Mock(return_value=[0.1] * 768)

        provider = QdrantSemanticProvider(
            qdrant_client=mock_client,
            embedding_func=mock_embedding
        )

        results = provider.search_similar('/src/main.py', limit=5)

        assert len(results) == 3
        assert results[0] == ('/src/utils.py', 0.9)
        mock_embedding.assert_called_once_with('/src/main.py')

    def test_search_caching(self):
        """Test that results are cached."""
        mock_client = Mock()
        mock_client.search_by_vector.return_value = [
            {'path': '/src/utils.py', 'score': 0.9},
        ]
        mock_embedding = Mock(return_value=[0.1] * 768)

        provider = QdrantSemanticProvider(
            qdrant_client=mock_client,
            embedding_func=mock_embedding
        )

        # First call
        results1 = provider.search_similar('/src/main.py')
        # Second call (should use cache)
        results2 = provider.search_similar('/src/main.py')

        assert results1 == results2
        # Embedding should only be called once
        assert mock_embedding.call_count == 1

    def test_search_no_client(self):
        """Test graceful handling when client is None."""
        provider = QdrantSemanticProvider(qdrant_client=None)
        results = provider.search_similar('/src/main.py')
        assert results == []

    def test_clear_cache(self):
        """Test cache clearing."""
        provider = QdrantSemanticProvider(qdrant_client=Mock())
        provider._cache['key'] = [('path', 0.5)]
        provider.clear_cache()
        assert provider._cache == {}


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_calculate_dependency_score(self):
        """Test single score calculation."""
        now = datetime.now()
        score = calculate_dependency_score(
            source_path="/src/utils.py",
            target_path="/src/main.py",
            import_confidence=0.9,
            semantic_score=0.7,
            source_created=now,
            target_created=now
        )

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # High import confidence should yield good score

    def test_combine_import_and_semantic(self):
        """Test enhancing imports with semantic scores."""
        dependencies = [
            Dependency(
                target="/src/main.py",
                source="/src/utils.py",
                dependency_type=DependencyType.IMPORT,
                confidence=0.9,
                line_number=5,
                context="from utils import helper"
            ),
            Dependency(
                target="/src/main.py",
                source="/src/config.py",
                dependency_type=DependencyType.IMPORT,
                confidence=0.5,
                line_number=10,
                context="import config"
            ),
        ]

        semantic_scores = {
            "/src/utils.py": 0.8,
            "/src/config.py": 0.3,
        }

        enhanced = combine_import_and_semantic(dependencies, semantic_scores)

        assert len(enhanced) == 2
        # Both should have updated metadata
        for dep in enhanced:
            assert 'original_confidence' in dep.metadata
            assert 'semantic_score' in dep.metadata
            assert 'scoring_components' in dep.metadata


class TestScoringResultToDependency:
    """Test conversion to Dependency."""

    def test_to_dependency(self):
        """Test ScoringResult.to_dependency()."""
        result = ScoringResult(
            source_path="/src/utils.py",
            target_path="/src/main.py",
            raw_score=0.7,
            final_score=0.85,
            is_significant=True,
            components={'I': 0.9, 'S': 0.8}
        )

        dep = result.to_dependency()

        assert dep.source == "/src/utils.py"
        assert dep.target == "/src/main.py"
        assert dep.dependency_type == DependencyType.TEMPORAL_SEMANTIC
        assert dep.confidence == 0.85
        assert 'raw_score' in dep.metadata


class TestEdgeCases:
    """Test edge cases."""

    def test_zero_all_inputs(self):
        """All zero inputs = low score."""
        calculator = DependencyCalculator()
        input_data = ScoringInput(
            source_file=FileMetadata(path="/a.py"),
            target_file=FileMetadata(path="/b.py"),
            import_confidence=0.0,
            semantic_score=0.0
        )
        result = calculator.calculate(input_data)

        # Only RRF contributes (default 0.5)
        # 0.07 * 0.5 = 0.035 → sigmoid ≈ 0.004
        assert result.final_score < 0.1

    def test_max_all_inputs(self):
        """All max inputs = high score."""
        calculator = DependencyCalculator()
        now = datetime.now()
        input_data = ScoringInput(
            source_file=FileMetadata(
                path="/a.py",
                created_at=now,
                rrf_score=1.0
            ),
            target_file=FileMetadata(path="/b.py", created_at=now),
            import_confidence=1.0,
            semantic_score=1.0,
            has_explicit_reference=True
        )
        result = calculator.calculate(input_data)

        # Raw = 0.4 + 0.33*1.0 + 0.2 + 0.07 = 1.0
        assert result.final_score > 0.99

    def test_self_reference_filtered(self):
        """Self-reference should be filtered in find_dependencies."""
        calculator = DependencyCalculator()
        now = datetime.now()

        target = FileMetadata(path="/src/main.py", created_at=now)
        sources = [
            FileMetadata(path="/src/main.py", created_at=now),  # Self
            FileMetadata(path="/src/utils.py", created_at=now),
        ]

        results = calculator.find_dependencies(
            target_file=target,
            candidate_sources=sources,
            import_scores={"/src/main.py": 1.0, "/src/utils.py": 0.5}
        )

        # Self-reference should be excluded
        paths = [r.source_path for r in results]
        assert "/src/main.py" not in paths


class TestRealWorldScenarios:
    """Test real-world scenarios (Phase 72.5 Enhanced)."""

    def test_spec_to_implementation(self):
        """Spec document → implementation code (Phase 72.5)."""
        calculator = DependencyCalculator()

        # Spec created Jan 1, impl created Jan 3
        spec_created = datetime(2026, 1, 1)
        impl_created = datetime(2026, 1, 3)

        input_data = ScoringInput(
            source_file=FileMetadata(
                path="/docs/api_spec.md",
                created_at=spec_created,
                rrf_score=0.7  # Important document
            ),
            target_file=FileMetadata(
                path="/src/api/handlers.py",
                created_at=impl_created
            ),
            import_confidence=0.0,  # Markdown can't be imported
            semantic_score=0.8,     # High semantic similarity
            has_explicit_reference=True  # Code links to spec
        )

        result = calculator.calculate(input_data)

        # Phase 72.5:
        # S_gated = (0.8 - 0.5) / 0.5 = 0.6
        # E(2 days) = 0.2 + 0.8*e^(-2/30) ≈ 0.2 + 0.8*0.94 = 0.95
        # Raw = 0.33*0.6*0.95 + 0.2*1.0 + 0.07*0.7 = 0.188 + 0.2 + 0.049 = 0.437
        # With center=0.35: sigmoid(0.437) ≈ 0.74
        assert result.final_score > 0.6
        assert result.is_significant is True
        assert result.components['E_delta_t'] > 0.9

    def test_refactored_code(self):
        """Old file → refactored new file (Phase 72.5: temporal floor)."""
        calculator = DependencyCalculator()

        old_created = datetime(2025, 6, 1)  # 6 months ago
        new_created = datetime(2026, 1, 1)

        input_data = ScoringInput(
            source_file=FileMetadata(
                path="/src/old_utils.py",
                created_at=old_created
            ),
            target_file=FileMetadata(
                path="/src/utils.py",
                created_at=new_created
            ),
            import_confidence=0.0,  # Renamed, not imported
            semantic_score=0.9,     # Very similar content
        )

        result = calculator.calculate(input_data)

        # Phase 72.5: 214 days, but with floor = 0.2
        # E(214) = 0.2 + 0.8*e^(-214/30) ≈ 0.2 + 0.8*0.0008 = 0.2006
        # OLD formula would give 0.0008, now minimum is 0.2
        assert result.components['E_delta_t'] >= 0.2

        # S_gated = (0.9 - 0.5) / 0.5 = 0.8
        # Raw = 0.33*0.8*0.2 + 0.07*0.5 = 0.053 + 0.035 = 0.088
        # With center=0.35: sigmoid(0.088) ≈ 0.04
        # Still low, but not zero due to floor
        assert result.final_score > 0.0

    def test_utility_library(self):
        """Shared utility → multiple consumers (Phase 72.5)."""
        calculator = DependencyCalculator()
        now = datetime.now()

        # Utility file
        utils = FileMetadata(
            path="/src/utils.py",
            created_at=now - timedelta(days=10),
            rrf_score=0.9  # High importance (many imports)
        )

        # Consumer files
        consumers = [
            FileMetadata(path="/src/api.py", created_at=now),
            FileMetadata(path="/src/cli.py", created_at=now),
            FileMetadata(path="/src/worker.py", created_at=now),
        ]

        results = []
        for consumer in consumers:
            input_data = ScoringInput(
                source_file=utils,
                target_file=consumer,
                import_confidence=1.0,  # All import utils
                semantic_score=0.5  # At gate threshold → S_gated = 0
            )
            results.append(calculator.calculate(input_data))

        # All should be significant (due to import)
        assert all(r.is_significant for r in results)
        # All should have similar scores (same import pattern)
        scores = [r.final_score for r in results]
        assert max(scores) - min(scores) < 0.1

    def test_pure_import_now_significant(self):
        """Phase 72.5 key fix: pure import without semantic is now significant."""
        calculator = DependencyCalculator()
        now = datetime.now()

        input_data = ScoringInput(
            source_file=FileMetadata(path="/lib/utils.py", created_at=now),
            target_file=FileMetadata(path="/src/main.py", created_at=now),
            import_confidence=1.0,  # Pure import
            semantic_score=0.0,     # No semantic match (e.g., utility lib)
        )

        result = calculator.calculate(input_data)

        # Phase 72.5 key fix: should now be significant
        # Raw = 0.4*1.0 + 0.07*0.5 = 0.435
        # With center=0.35: sigmoid(0.435) ≈ 0.74 > 0.6
        assert result.final_score > 0.6
        assert result.is_significant is True
