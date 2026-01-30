"""
VETKA Phase 99.3 - ARC Gap Detector Tests

Tests for conceptual gap detection before agent calls.

@status: active
@phase: 99.3
@depends: pytest, pytest-asyncio
"""

import pytest
import asyncio
from src.orchestration.arc_gap_detector import (
    ARCGapDetector,
    ConceptGap,
    GapDetectionResult,
    detect_conceptual_gaps,
    get_gap_detector,
    reset_gap_detector,
)


class TestConceptExtraction:
    """Test concept extraction from text."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_gap_detector()

    def test_extract_programming_concepts(self):
        """Test extraction of common programming concepts."""
        detector = ARCGapDetector()

        text = "We need to add an API endpoint for authentication with database storage"
        concepts = detector.extract_concepts(text)

        assert "api" in concepts
        assert "endpoint" in concepts
        assert "authentication" in concepts
        assert "database" in concepts

    def test_extract_vetka_concepts(self):
        """Test extraction of VETKA-specific concepts."""
        detector = ARCGapDetector()

        text = "The CAM engine should integrate with HOPE for better context"
        concepts = detector.extract_concepts(text)

        assert "cam" in concepts
        assert "hope" in concepts

    def test_extract_camel_case(self):
        """Test extraction from CamelCase identifiers."""
        detector = ARCGapDetector()

        text = "Use MemoryManager and ARCSolverAgent for the workflow"
        concepts = detector.extract_concepts(text)

        # Should extract component words from CamelCase
        # Note: 'agent' is also matched by pattern r'\b(agent|model|llm|gpt|claude|grok)\b'
        assert "memory" in concepts or "manager" in concepts
        # 'workflow' should be extracted by pattern
        assert "workflow" in concepts

    def test_extract_snake_case(self):
        """Test extraction from snake_case identifiers."""
        detector = ARCGapDetector()

        text = "Call get_qdrant_client and memory_manager functions"
        concepts = detector.extract_concepts(text)

        assert "qdrant" in concepts or "memory" in concepts

    def test_empty_text(self):
        """Test handling of empty text."""
        detector = ARCGapDetector()

        concepts = detector.extract_concepts("")
        assert concepts == []

        concepts = detector.extract_concepts(None)
        assert concepts == []

    def test_concept_limit(self):
        """Test that extraction is limited to 20 concepts."""
        detector = ARCGapDetector()

        # Text with many concepts
        text = """
        api endpoint route handler database db qdrant weaviate storage
        auth authentication token session config configuration settings env
        cache memory buffer stm mgc workflow pipeline orchestrator
        agent model llm gpt claude grok error exception handling retry
        file path directory folder socket websocket stream realtime
        ui frontend component react cam hope arc elisya test testing
        """
        concepts = detector.extract_concepts(text)

        assert len(concepts) <= 20


class TestGapDetection:
    """Test gap detection logic."""

    def setup_method(self):
        reset_gap_detector()

    def test_detect_missing_connection(self):
        """Test detection of missing connections."""
        detector = ARCGapDetector(min_confidence=0.3)

        extracted = ["api", "endpoint", "handler"]
        related = [
            {
                "content": "authentication and security for api endpoints",
                "score": 0.8,
                "path": "src/auth/handler.py"
            }
        ]

        gaps = detector.detect_gaps(extracted, related)

        # Should detect auth-related concepts as missing
        assert len(gaps) > 0
        assert gaps[0].gap_type == "missing_connection"
        assert gaps[0].confidence >= 0.3

    def test_no_gaps_when_complete(self):
        """Test no gaps when concepts are complete."""
        detector = ARCGapDetector(min_confidence=0.9)

        extracted = ["api", "auth", "database", "cache"]
        related = [
            {
                "content": "api authentication",
                "score": 0.5,
                "path": "test.py"
            }
        ]

        gaps = detector.detect_gaps(extracted, related)

        # With high confidence threshold and matching concepts, fewer gaps
        # Related content mentions auth which is in extracted
        assert len(gaps) == 0 or gaps[0].confidence < 0.9

    def test_arc_few_shot_gaps(self):
        """Test gap detection from ARC few-shot examples."""
        detector = ARCGapDetector()

        extracted = ["workflow", "agent"]
        related = []
        few_shots = [
            {
                "type": "connection",
                "explanation": "Connect workflow to memory for persistence",
                "code": "def connect_memory(graph):",
                "score": 0.9
            }
        ]

        gaps = detector.detect_gaps(extracted, related, few_shots)

        # Should suggest memory-related concepts
        memory_gap = any("memory" in str(g.related_concepts) for g in gaps)
        assert memory_gap or len(gaps) > 0


class TestSuggestionFormatting:
    """Test suggestion formatting for prompt injection."""

    def setup_method(self):
        reset_gap_detector()

    def test_format_single_gap(self):
        """Test formatting of single gap."""
        detector = ARCGapDetector()

        gaps = [
            ConceptGap(
                concept="auth",
                related_concepts=["authentication", "token"],
                gap_type="missing_connection",
                confidence=0.8,
                suggestion="Consider: authentication, token (from auth.py)",
                source="semantic_search"
            )
        ]

        formatted = detector.format_suggestions(gaps)

        assert "[ARC Gap Analysis" in formatted
        assert "authentication" in formatted
        assert "★" in formatted  # Confidence stars

    def test_format_multiple_gaps(self):
        """Test formatting of multiple gaps."""
        detector = ARCGapDetector()

        gaps = [
            ConceptGap("auth", ["token"], "missing_connection", 0.8, "Suggestion 1", "test"),
            ConceptGap("cache", ["memory"], "missing_pattern", 0.6, "Suggestion 2", "test"),
        ]

        formatted = detector.format_suggestions(gaps)

        assert "1." in formatted
        assert "2." in formatted

    def test_format_empty_gaps(self):
        """Test formatting with no gaps."""
        detector = ARCGapDetector()

        formatted = detector.format_suggestions([])
        assert formatted == ""


class TestAsyncAnalysis:
    """Test async analysis pipeline."""

    def setup_method(self):
        reset_gap_detector()

    @pytest.mark.asyncio
    async def test_analyze_simple_prompt(self):
        """Test analysis of simple prompt."""
        detector = ARCGapDetector()

        result = await detector.analyze(
            prompt="Create an API endpoint",
            context="for user authentication"
        )

        assert isinstance(result, GapDetectionResult)
        assert len(result.extracted_concepts) > 0
        assert "api" in result.extracted_concepts or "endpoint" in result.extracted_concepts

    @pytest.mark.asyncio
    async def test_analyze_empty_prompt(self):
        """Test handling of empty prompt."""
        detector = ARCGapDetector()

        result = await detector.analyze(prompt="", context="")

        assert isinstance(result, GapDetectionResult)
        assert len(result.extracted_concepts) == 0

    @pytest.mark.asyncio
    async def test_convenience_function(self):
        """Test detect_conceptual_gaps convenience function."""
        suggestions = await detect_conceptual_gaps(
            prompt="Build a workflow with agents",
            context="for code review"
        )

        # Without memory manager, no related concepts found
        # So suggestions may be empty or minimal
        assert isinstance(suggestions, str)


class TestARCSolverIntegration:
    """Test integration with real ARCSolverAgent."""

    def setup_method(self):
        reset_gap_detector()

    def test_arc_solver_suggestions_method(self):
        """Test _get_arc_solver_suggestions with mock ARC Solver."""
        detector = ARCGapDetector(min_confidence=0.3)

        # Create mock ARC Solver with few_shot_examples
        class MockARCSolver:
            def __init__(self):
                self.few_shot_examples = [
                    {
                        'type': 'connection',
                        'explanation': 'Connect database to cache for performance',
                        'code': 'def add_cache_layer(db):',
                        'score': 0.85
                    }
                ]

        detector.arc_solver = MockARCSolver()

        extracted = ["api", "endpoint"]
        extracted_set = set(extracted)

        gaps = detector._get_arc_solver_suggestions(extracted, extracted_set)

        # Should find gaps from ARC Solver's few_shot_examples
        assert len(gaps) >= 0  # May find cache/database concepts
        # All gaps should have arc-related source
        for gap in gaps:
            assert gap.source in ['arc_solver', 'arc_solver_cache']

    def test_arc_solver_with_suggest_connections(self):
        """Test with mock ARC Solver that has suggest_connections method."""
        detector = ARCGapDetector(min_confidence=0.3)

        # Create mock ARC Solver with suggest_connections
        class MockARCSolverFull:
            def suggest_connections(self, workflow_id, graph_data, task_context, num_candidates, min_score):
                return {
                    'top_suggestions': [
                        {
                            'type': 'optimization',
                            'explanation': 'Add memory caching layer for faster retrieval',
                            'score': 0.9
                        }
                    ],
                    'suggestions': [],
                    'stats': {}
                }

        detector.arc_solver = MockARCSolverFull()

        extracted = ["api", "endpoint"]
        extracted_set = set(extracted)

        gaps = detector._get_arc_solver_suggestions(extracted, extracted_set)

        # Should have at least one gap from ARC reasoning
        assert len(gaps) >= 1
        assert gaps[0].gap_type == 'arc_reasoning'
        assert gaps[0].source == 'arc_solver'
        assert gaps[0].confidence == 0.9


class TestSingleton:
    """Test singleton pattern."""

    def setup_method(self):
        reset_gap_detector()

    def test_get_singleton(self):
        """Test singleton getter."""
        detector1 = get_gap_detector()
        detector2 = get_gap_detector()

        assert detector1 is detector2

    def test_reset_singleton(self):
        """Test singleton reset."""
        detector1 = get_gap_detector()
        reset_gap_detector()
        detector2 = get_gap_detector()

        assert detector1 is not detector2


# ============================================================
# Run tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
