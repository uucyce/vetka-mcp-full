# ========================================
# MARKER: Phase 72.4 + 72.5 Dependency Scoring
# Date: 2026-01-19
# File: src/scanners/dependency_calculator.py
# Purpose: Calculate combined dependency scores
# Formula: Kimi K2 Enhanced (6-AI consensus)
# Integrates: PythonScanner (72.3), Qdrant semantic search
# Phase 72.5: Sigmoid center 0.35, semantic gating, temporal floor
# ========================================
"""
Dependency Scoring Calculator for VETKA Phase 72.4 + 72.5

Combines multiple signals into unified dependency score:
- I (Import): Explicit code imports (confidence from PythonScanner)
- S' (Semantic gated): Vector similarity with threshold gating
- E(ΔT): Temporal decay with floor (20% memory)
- R (Reference): Direct references (links, paths)
- RRF: Reciprocal Rank Fusion for source importance

Formula (Kimi K2 Enhanced - 6-AI consensus):
    DEP(A→B) = σ( w₁·I + w₂·S'·E(ΔT) + w₃·R + w₄·RRF )

    Phase 72.5 enhancements:
        σ(x) = 1/(1+e^(-12(x-0.35)))  # Sigmoid center shifted to 0.35
        S' = max(0, (S - 0.5) / 0.5)  # Semantic gating (threshold 0.5)
        E(ΔT) = 0.2 + 0.8·e^(-ΔT/τ)  # Temporal floor (20% memory)

    where:
        ΔT = max(0, created(B) - created(A)) / 86400  # Days
        τ = 30 days                  # Decay constant
        w = [0.4, 0.33, 0.2, 0.07]   # Weights (sum = 1.0)
        threshold = 0.6              # Minimum for significant link

Score interpretation:
    0.8-1.0: Strong dependency (explicit import)
    0.6-0.8: Significant link (semantic + temporal)
    0.4-0.6: Weak link (semantic only)
    0.0-0.4: No meaningful dependency

@status: active
@phase: 96
@depends: math, dataclasses, datetime, dependency
@used_by: embedding_pipeline, tree_renderer
"""

import math
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

from .dependency import Dependency, DependencyType

logger = logging.getLogger(__name__)


# ========================================
# Configuration (Phase 72.5 Enhanced)
# ========================================

@dataclass
class ScoringConfig:
    """
    Configuration for dependency scoring.

    Weights must sum to 1.0 for proper normalization.
    Adjust based on content type and use case.

    Phase 72.5 enhancements (6-AI consensus):
    - sigmoid_center: 0.5 → 0.35 (boost pure imports)
    - semantic_gate_threshold: 0.5 (filter weak similarity)
    - temporal_floor: 0.2 (20% memory for old files)
    """
    # Weights for scoring formula
    w_import: float = 0.40      # w₁: Import weight (explicit deps)
    w_semantic: float = 0.33    # w₂: Semantic similarity weight
    w_reference: float = 0.20   # w₃: Reference weight (links, paths)
    w_rrf: float = 0.07         # w₄: RRF weight (source importance)

    # Temporal decay (Phase 72.5: added floor)
    tau_days: float = 30.0      # τ: Decay constant in days
    max_delta_days: float = 365.0  # Max time delta to consider
    temporal_floor: float = 0.2    # Phase 72.5: 20% minimum (memory)

    # Sigmoid parameters (Phase 72.5: shifted center)
    sigmoid_steepness: float = 12.0  # Steepness of sigmoid curve
    sigmoid_center: float = 0.35     # Phase 72.5: shifted from 0.5 to boost imports

    # Semantic gating (Phase 72.5: threshold normalization)
    semantic_gate_threshold: float = 0.5  # Phase 72.5: S' = max(0, (S-0.5)/0.5)
    min_semantic_score: float = 0.3   # Legacy: ignore below this (pre-gate)

    # Thresholds
    significance_threshold: float = 0.6  # Minimum for meaningful link

    def __post_init__(self):
        """Validate configuration parameters."""
        # Validate weights sum to 1.0 (tight tolerance)
        total = self.w_import + self.w_semantic + self.w_reference + self.w_rrf
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"Weights must sum to 1.0, got {total:.4f}. "
                f"Weights: I={self.w_import}, S={self.w_semantic}, "
                f"R={self.w_reference}, RRF={self.w_rrf}"
            )

        # Validate all weights are non-negative
        for name, value in [
            ('w_import', self.w_import),
            ('w_semantic', self.w_semantic),
            ('w_reference', self.w_reference),
            ('w_rrf', self.w_rrf),
        ]:
            if value < 0:
                raise ValueError(f"{name} must be >= 0, got {value}")

        # Validate sigmoid parameters
        if not 0 <= self.sigmoid_center <= 1:
            raise ValueError(
                f"sigmoid_center must be in [0, 1], got {self.sigmoid_center}"
            )
        if self.sigmoid_steepness <= 0:
            raise ValueError(
                f"sigmoid_steepness must be > 0, got {self.sigmoid_steepness}"
            )

        # Validate temporal parameters
        if not 0 <= self.temporal_floor <= 1:
            raise ValueError(
                f"temporal_floor must be in [0, 1], got {self.temporal_floor}"
            )
        if self.tau_days <= 0:
            raise ValueError(f"tau_days must be > 0, got {self.tau_days}")

        # Validate semantic gating
        if not 0 <= self.semantic_gate_threshold <= 1:
            raise ValueError(
                f"semantic_gate_threshold must be in [0, 1], got {self.semantic_gate_threshold}"
            )


# Default configuration
DEFAULT_CONFIG = ScoringConfig()


# ========================================
# Data Structures
# ========================================

@dataclass
class FileMetadata:
    """
    Metadata for a file in dependency calculation.

    Attributes:
        path: Absolute file path
        created_at: File creation timestamp
        modified_at: Last modification timestamp
        rrf_score: Reciprocal Rank Fusion score (0-1)
        has_references: Whether file contains explicit references
    """
    path: str
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    rrf_score: float = 0.5
    has_references: bool = False


@dataclass
class ScoringInput:
    """
    Input for dependency score calculation.

    Represents a potential A→B dependency link.

    Attributes:
        source_file: File A (the dependency provider)
        target_file: File B (the file that depends on A)
        import_confidence: Confidence from import resolution (0-1)
        semantic_score: Cosine similarity from Qdrant (0-1)
        has_explicit_reference: Whether B explicitly references A
    """
    source_file: FileMetadata
    target_file: FileMetadata
    import_confidence: float = 0.0
    semantic_score: float = 0.0
    has_explicit_reference: bool = False


@dataclass
class ScoringResult:
    """
    Result of dependency score calculation.

    Attributes:
        source_path: Path of source file
        target_path: Path of target file
        raw_score: Score before sigmoid normalization
        final_score: Final normalized score (0-1)
        is_significant: Whether score exceeds threshold
        components: Individual score components for debugging
    """
    source_path: str
    target_path: str
    raw_score: float
    final_score: float
    is_significant: bool
    components: Dict[str, float] = field(default_factory=dict)

    def to_dependency(self) -> Dependency:
        """
        Convert to Dependency object.

        Uses TEMPORAL_SEMANTIC type for combined scoring.
        """
        return Dependency(
            target=self.target_path,
            source=self.source_path,
            dependency_type=DependencyType.TEMPORAL_SEMANTIC,
            confidence=self.final_score,
            metadata={
                'raw_score': self.raw_score,
                'components': self.components,
                'is_significant': self.is_significant,
            }
        )


# ========================================
# Qdrant Interface (Protocol for DI)
# ========================================

class SemanticSearchProvider(Protocol):
    """
    Protocol for semantic search provider.

    Allows dependency injection of Qdrant or mock for testing.
    """

    def search_similar(
        self,
        query_path: str,
        limit: int = 10,
        score_threshold: float = 0.3
    ) -> List[Tuple[str, float]]:
        """
        Find semantically similar files.

        Args:
            query_path: Path of file to find similar files for
            limit: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of (file_path, similarity_score) tuples
        """
        ...


# ========================================
# Core Calculator
# ========================================

class DependencyCalculator:
    """
    Calculate combined dependency scores using Kimi K2 formula.

    Combines:
    - Import analysis (from PythonScanner)
    - Semantic similarity (from Qdrant)
    - Temporal relationships (file timestamps)
    - Explicit references
    - Source importance (RRF)

    Usage:
        >>> calculator = DependencyCalculator()
        >>> result = calculator.calculate(ScoringInput(
        ...     source_file=FileMetadata(path="/src/utils.py", created_at=...),
        ...     target_file=FileMetadata(path="/src/main.py", created_at=...),
        ...     import_confidence=0.9,
        ...     semantic_score=0.7
        ... ))
        >>> print(f"Score: {result.final_score:.2f}")
    """

    def __init__(
        self,
        config: Optional[ScoringConfig] = None,
        semantic_provider: Optional[SemanticSearchProvider] = None
    ):
        """
        Initialize calculator.

        Args:
            config: Scoring configuration (uses defaults if None)
            semantic_provider: Provider for semantic search (optional)
        """
        self.config = config or DEFAULT_CONFIG
        self.semantic_provider = semantic_provider

    def calculate(self, input_data: ScoringInput) -> ScoringResult:
        """
        Calculate dependency score for A→B link.

        Args:
            input_data: Input data with file metadata and scores

        Returns:
            ScoringResult with final score and components

        Phase 72.5 enhancements:
        - Semantic gating: S' = max(0, (S - 0.5) / 0.5)
        - Temporal floor: E(ΔT) = 0.2 + 0.8·e^(-ΔT/τ)
        - Sigmoid center shifted to 0.35
        """
        # Extract components
        I = input_data.import_confidence
        S_raw = input_data.semantic_score
        R = 1.0 if input_data.has_explicit_reference else 0.0
        RRF = input_data.source_file.rrf_score

        # Phase 72.5: Semantic gating - S' = max(0, (S - threshold) / (1 - threshold))
        # This normalizes 0.5-1.0 → 0.0-1.0, anything below 0.5 → 0.0
        gate_threshold = self.config.semantic_gate_threshold
        if S_raw >= gate_threshold:
            S_gated = (S_raw - gate_threshold) / (1.0 - gate_threshold)
        else:
            S_gated = 0.0

        # Calculate temporal decay (Phase 72.5: includes floor)
        E_delta_t = self._calculate_temporal_decay(
            input_data.source_file.created_at,
            input_data.target_file.created_at
        )

        # Check causality constraint: A must be created before B
        # E_delta_t == 0.0 only when _calculate_temporal_decay detects violation
        # (source created AFTER target = impossible dependency)
        if E_delta_t == 0.0 and I == 0.0:
            # No import and wrong temporal order = no dependency
            return ScoringResult(
                source_path=input_data.source_file.path,
                target_path=input_data.target_file.path,
                raw_score=0.0,
                final_score=0.0,
                is_significant=False,
                components={
                    'I': I, 'S_raw': S_raw, 'S_gated': S_gated,
                    'E_delta_t': E_delta_t, 'R': R, 'RRF': RRF,
                    'reason': 'temporal_violation'
                }
            )

        # Note: Legacy min_semantic_score filter removed in Phase 72.5
        # Semantic gating (threshold 0.5) handles noise filtering more effectively

        # Calculate weighted sum (using gated semantic)
        raw_score = (
            self.config.w_import * I +
            self.config.w_semantic * S_gated * E_delta_t +
            self.config.w_reference * R +
            self.config.w_rrf * RRF
        )

        # Apply sigmoid normalization (Phase 72.5: center = 0.35)
        final_score = self._sigmoid(raw_score)

        # Determine significance
        is_significant = final_score >= self.config.significance_threshold

        return ScoringResult(
            source_path=input_data.source_file.path,
            target_path=input_data.target_file.path,
            raw_score=raw_score,
            final_score=final_score,
            is_significant=is_significant,
            components={
                'I': I,
                'S_raw': S_raw,
                'S_gated': S_gated,
                'E_delta_t': E_delta_t,
                'S_weighted': S_gated * E_delta_t,
                'R': R,
                'RRF': RRF,
            }
        )

    def calculate_batch(
        self,
        inputs: List[ScoringInput]
    ) -> List[ScoringResult]:
        """
        Calculate scores for multiple input pairs.

        Args:
            inputs: List of scoring inputs

        Returns:
            List of scoring results in same order
        """
        return [self.calculate(input_data) for input_data in inputs]

    def find_dependencies(
        self,
        target_file: FileMetadata,
        candidate_sources: List[FileMetadata],
        import_scores: Optional[Dict[str, float]] = None,
        semantic_scores: Optional[Dict[str, float]] = None,
        reference_paths: Optional[List[str]] = None
    ) -> List[ScoringResult]:
        """
        Find all significant dependencies for a target file.

        Args:
            target_file: File to find dependencies for
            candidate_sources: List of potential source files
            import_scores: Dict of path → import confidence
            semantic_scores: Dict of path → semantic similarity
            reference_paths: Paths explicitly referenced in target

        Returns:
            List of significant dependencies, sorted by score
        """
        import_scores = import_scores or {}
        semantic_scores = semantic_scores or {}
        reference_paths = set(reference_paths or [])

        results = []

        for source in candidate_sources:
            # Skip self-reference
            if source.path == target_file.path:
                continue

            input_data = ScoringInput(
                source_file=source,
                target_file=target_file,
                import_confidence=import_scores.get(source.path, 0.0),
                semantic_score=semantic_scores.get(source.path, 0.0),
                has_explicit_reference=source.path in reference_paths
            )

            result = self.calculate(input_data)
            if result.is_significant:
                results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.final_score, reverse=True)

        return results

    def _calculate_temporal_decay(
        self,
        source_created: Optional[datetime],
        target_created: Optional[datetime]
    ) -> float:
        """
        Calculate temporal decay factor E(ΔT).

        Phase 72.5 formula:
            E(ΔT) = floor + (1 - floor) · e^(-ΔT/τ)

        where floor = 0.2 (20% memory for old files)

        If source was created AFTER target, returns 0 (causality violation).
        """
        # If timestamps missing, assume neutral decay
        if source_created is None or target_created is None:
            return 0.5  # Neutral: neither boost nor penalty

        # Calculate delta in days
        delta_seconds = (target_created - source_created).total_seconds()
        delta_days = delta_seconds / 86400.0

        # Causality check: source must exist before target
        if delta_days < 0:
            # Source created after target = impossible dependency
            return 0.0

        # Cap at max delta
        if delta_days > self.config.max_delta_days:
            delta_days = self.config.max_delta_days

        # Phase 72.5: Exponential decay with floor
        # E(ΔT) = floor + (1 - floor) · e^(-ΔT/τ)
        floor = self.config.temporal_floor
        raw_decay = math.exp(-delta_days / self.config.tau_days)
        decay = floor + (1.0 - floor) * raw_decay

        return decay

    def _sigmoid(self, x: float) -> float:
        """
        Apply sigmoid normalization.

        σ(x) = 1 / (1 + e^(-k(x-c)))

        where k = steepness, c = center
        """
        k = self.config.sigmoid_steepness
        c = self.config.sigmoid_center

        try:
            return 1.0 / (1.0 + math.exp(-k * (x - c)))
        except OverflowError:
            # Handle extreme values
            return 0.0 if x < c else 1.0


# ========================================
# Qdrant Integration Helper
# ========================================

class QdrantSemanticProvider:
    """
    Semantic search provider using Qdrant.

    Wraps QdrantVetkaClient for use with DependencyCalculator.
    """

    def __init__(self, qdrant_client: Any, embedding_func: Optional[Callable] = None):
        """
        Initialize provider.

        Args:
            qdrant_client: QdrantVetkaClient instance
            embedding_func: Function to generate embeddings from file path
        """
        self.client = qdrant_client
        self.embedding_func = embedding_func
        self._cache: Dict[str, List[Tuple[str, float]]] = {}

    def search_similar(
        self,
        query_path: str,
        limit: int = 10,
        score_threshold: float = 0.3
    ) -> List[Tuple[str, float]]:
        """
        Find semantically similar files using Qdrant.

        Args:
            query_path: Path of file to find similar files for
            limit: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of (file_path, similarity_score) tuples
        """
        # Check cache
        cache_key = f"{query_path}:{limit}:{score_threshold}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self.client is None:
            return []

        # Get embedding for query file
        if self.embedding_func is None:
            return []

        try:
            query_vector = self.embedding_func(query_path)
            if query_vector is None:
                return []

            # Search Qdrant
            results = self.client.search_by_vector(
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )

            # Convert to (path, score) tuples
            similar = [
                (r.get('path', ''), r.get('score', 0.0))
                for r in results
                if r.get('path')
            ]

            # Cache results
            self._cache[cache_key] = similar

            return similar

        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            return []

    def clear_cache(self):
        """Clear the similarity cache."""
        self._cache.clear()


# ========================================
# Convenience Functions
# ========================================

def calculate_dependency_score(
    source_path: str,
    target_path: str,
    import_confidence: float = 0.0,
    semantic_score: float = 0.0,
    source_created: Optional[datetime] = None,
    target_created: Optional[datetime] = None,
    has_reference: bool = False,
    config: Optional[ScoringConfig] = None
) -> float:
    """
    Convenience function to calculate a single dependency score.

    Args:
        source_path: Path of source file (dependency provider)
        target_path: Path of target file (depends on source)
        import_confidence: Import resolution confidence (0-1)
        semantic_score: Semantic similarity (0-1)
        source_created: Source file creation time
        target_created: Target file creation time
        has_reference: Whether target explicitly references source
        config: Scoring configuration

    Returns:
        Final dependency score (0-1)
    """
    calculator = DependencyCalculator(config=config)

    input_data = ScoringInput(
        source_file=FileMetadata(
            path=source_path,
            created_at=source_created
        ),
        target_file=FileMetadata(
            path=target_path,
            created_at=target_created
        ),
        import_confidence=import_confidence,
        semantic_score=semantic_score,
        has_explicit_reference=has_reference
    )

    result = calculator.calculate(input_data)
    return result.final_score


def combine_import_and_semantic(
    dependencies: List[Dependency],
    semantic_scores: Dict[str, float],
    file_timestamps: Optional[Dict[str, datetime]] = None,
    config: Optional[ScoringConfig] = None
) -> List[Dependency]:
    """
    Enhance import dependencies with semantic scores.

    Takes dependencies from PythonScanner and enhances them
    with semantic similarity from Qdrant.

    Args:
        dependencies: List of import dependencies
        semantic_scores: Dict of source_path → semantic score
        file_timestamps: Dict of path → creation time
        config: Scoring configuration

    Returns:
        List of dependencies with updated confidence scores
    """
    calculator = DependencyCalculator(config=config)
    file_timestamps = file_timestamps or {}
    enhanced = []

    for dep in dependencies:
        source_created = file_timestamps.get(dep.source)
        target_created = file_timestamps.get(dep.target)

        input_data = ScoringInput(
            source_file=FileMetadata(
                path=dep.source,
                created_at=source_created
            ),
            target_file=FileMetadata(
                path=dep.target,
                created_at=target_created
            ),
            import_confidence=dep.confidence,
            semantic_score=semantic_scores.get(dep.source, 0.0),
            has_explicit_reference=False
        )

        result = calculator.calculate(input_data)

        # Create enhanced dependency
        enhanced_dep = Dependency(
            target=dep.target,
            source=dep.source,
            dependency_type=dep.dependency_type,
            confidence=result.final_score,
            line_number=dep.line_number,
            context=dep.context,
            metadata={
                **dep.metadata,
                'original_confidence': dep.confidence,
                'semantic_score': semantic_scores.get(dep.source, 0.0),
                'scoring_components': result.components,
            }
        )
        enhanced.append(enhanced_dep)

    return enhanced
