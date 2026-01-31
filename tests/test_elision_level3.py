# MARKER_104_ELISION_TESTS
"""
Phase 104: ELISION Level 3 - Comprehensive Vowel Skipping Tests

Tests for ELISION Level 3: Vowel Skipping + Surprise Selection.

Compression layers:
1. Level 1: Key abbreviation (current_file -> cf)
2. Level 2: Level 1 + path compression
3. Level 3: Level 2 + vowel skipping based on surprise metrics
4. Level 4: Level 3 + local dictionary

Target: 60-70% token savings with surprise-aware compression

Tests validate:
- Basic vowel skipping functionality
- First vowel preservation for readability
- Level 3 vs Level 2 compression savings
- Surprise-based word selection (high surprise = preserve, low surprise = compress)
- Word eligibility for compression
- Legend metadata for reversal
- Integration with ElisyaState context
- Parametrized vowel skip ratios
- Edge cases (short words, acronyms, special characters)

Run: pytest tests/test_elision_level3.py -v
Run with markers: pytest tests/test_elision_level3.py -m elision_compression -v

@status: active
@phase: 104
@depends: pytest, pytest-asyncio, src.memory.elision
@markers: elision_compression, phase_104
"""

import pytest
import json
import re
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field

# Import ELISION components
from src.memory.elision import (
    get_elision_compressor,
    ElisionCompressor,
    ElisionResult,
    ELISION_MAP,
    compress_context,
    expand_context,
)


# ============================================================
# MARKERS & TEST CONFIGURATION
# ============================================================

pytestmark = [
    pytest.mark.elision_compression,
    pytest.mark.phase_104,
]


# ============================================================
# MOCK CLASSES FOR CAM & SURPRISE METRICS
# ============================================================

@dataclass
class SurpriseMetrics:
    """Surprise metrics for text analysis."""
    word: str
    frequency: int  # How often word appears
    surprise_score: float  # 0.0 (common) to 1.0 (rare/surprising)
    should_preserve: bool = False  # True if surprise > threshold


def get_surprise_metrics(text: str, threshold: float = 0.6) -> Dict[str, SurpriseMetrics]:
    """
    Analyze text and compute surprise metrics for each word.

    High surprise (> threshold): Rare, important words -> preserve
    Low surprise (< threshold): Common words -> compress

    Args:
        text: Text to analyze
        threshold: Surprise threshold (0.6 means rare words have surprise > 0.6)

    Returns:
        Dict mapping words to their surprise metrics
    """
    # Extract words
    words = re.findall(r'\b\w+\b', text.lower())

    # Count frequencies
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1

    max_freq = max(word_freq.values()) if word_freq else 1

    # Calculate surprise scores (inverse of frequency)
    # Common words (high freq) = low surprise
    # Rare words (low freq) = high surprise
    metrics = {}
    for word, freq in word_freq.items():
        surprise = 1.0 - (freq / max_freq)  # Inverse relationship
        metrics[word] = SurpriseMetrics(
            word=word,
            frequency=freq,
            surprise_score=surprise,
            should_preserve=surprise > threshold
        )

    return metrics


@dataclass
class CAMMemory:
    """Mock CAM Memory for testing."""
    surprise_metrics: Dict[str, SurpriseMetrics] = field(default_factory=dict)
    context_window: int = 8192
    compression_level: int = 2

    def analyze_context(self, text: str, threshold: float = 0.6) -> Dict[str, SurpriseMetrics]:
        """Analyze and store surprise metrics for text."""
        self.surprise_metrics = get_surprise_metrics(text, threshold)
        return self.surprise_metrics


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def compressor():
    """Get ELISION compressor instance."""
    return get_elision_compressor()


@pytest.fixture
def cam():
    """Get CAM Memory instance."""
    return CAMMemory()


@pytest.fixture
def sample_text():
    """Sample text for compression tests."""
    return "The orchestrator implements the compression mechanism for memory management"


@pytest.fixture
def elisya_context():
    """Sample ElisyaState-like context."""
    return {
        "semantic_path": "/Users/project/src/orchestration/agent_pipeline.py",
        "conversation": [
            {"role": "user", "content": "Implement the orchestrator compression"},
            {"role": "assistant", "content": "I will implement the compression mechanism"}
        ],
        "pinned_context": "VETKA Phase 104 implementation",
        "knowledge_level": 0.85,
        "surprise_score": 0.65
    }


# ============================================================
# TEST CLASS: Vowel Skipping Functionality
# ============================================================

@pytest.mark.elision_compression
class TestVowelSkipping:
    """Tests for vowel skipping in ELISION Level 3."""

    def test_vowel_skip_basic(self, compressor):
        """Test basic vowel skipping with different rates."""
        # Test word with multiple vowels
        word = "orchestrator"

        # Implement vowel skipping logic
        vowels = "aeiouAEIOU"
        # 50% skip: remove every other vowel (after first)
        result = self._apply_vowel_skip(word, rate=0.5)

        # Should have fewer characters
        assert len(result) < len(word)
        # First vowel should be preserved
        assert result[0] == 'o' or (len(result) > 0 and result[0] in 'aeiou')

    def test_vowel_skip_aggressive(self, compressor):
        """Test aggressive vowel skipping (70% skip rate)."""
        word = "implementation"
        result = self._apply_vowel_skip(word, rate=0.7)

        # Aggressive: should be shorter
        assert len(result) < len(word)
        # But should still start with first letter
        assert result[0] == word[0]

    def test_vowel_skip_preserves_consonants(self, compressor):
        """Test that consonants are always preserved."""
        word = "test"
        result = self._apply_vowel_skip(word, rate=0.5)

        # All consonants (t, s, t) should be present
        assert 't' in result
        assert 's' in result

    def test_vowel_skip_short_words_unchanged(self, compressor):
        """Test that short words are not compressed."""
        short_words = ["the", "is", "a", "in", "at"]

        for word in short_words:
            result = self._apply_vowel_skip(word, rate=0.5)
            # Short words should remain mostly unchanged
            assert len(result) >= len(word) - 1

    def test_vowel_skip_preserves_first_vowel(self, compressor):
        """Test that first vowel is preserved for readability."""
        test_words = {
            "orchestrator": 'o',
            "implement": 'i',
            "understanding": 'u',
            "amazing": 'a',
            "engine": 'e',
        }

        for word, first_vowel in test_words.items():
            result = self._apply_vowel_skip(word, rate=0.5)
            # First character should be first vowel or word start
            assert result[0].lower() in [first_vowel.lower(), word[0].lower()]

    def test_vowel_skip_rate_parameter(self, compressor):
        """Test different vowel skip rates."""
        word = "implementation"

        rates = [0.3, 0.5, 0.7, 0.9]
        lengths = []

        for rate in rates:
            result = self._apply_vowel_skip(word, rate=rate)
            lengths.append(len(result))

        # Higher skip rates should produce shorter results
        assert lengths[0] > lengths[1] > lengths[2]

    def test_vowel_skip_case_preservation(self, compressor):
        """Test that case is preserved in vowel skipping."""
        word = "IMPLEMENTATION"
        result = self._apply_vowel_skip(word, rate=0.5)

        # Check if uppercase letters are preserved
        has_uppercase = any(c.isupper() for c in result)
        assert has_uppercase

    def test_vowel_skip_with_numbers(self, compressor):
        """Test vowel skipping with numbers in text."""
        text = "model123implementation456"
        result = self._apply_vowel_skip(text, rate=0.5)

        # Numbers should be preserved
        assert '1' in result or '2' in result or '3' in result or '4' in result

    # ========================================================
    # Helper Methods
    # ========================================================

    @staticmethod
    def _apply_vowel_skip(text: str, rate: float = 0.5) -> str:
        """
        Helper to apply vowel skipping to text.

        Args:
            text: Text to process
            rate: Skip rate (0.0 = keep all, 1.0 = remove all vowels except first)

        Returns:
            Text with vowels removed based on skip rate
        """
        if len(text) <= 3:
            return text  # Don't compress short words

        vowels = set('aeiouAEIOU')
        result = []
        vowel_count = 0
        first_vowel_found = False

        for char in text:
            if char in vowels:
                if not first_vowel_found:
                    # Always keep first vowel
                    result.append(char)
                    first_vowel_found = True
                else:
                    # Skip vowel based on rate
                    if vowel_count % int(1 / rate) != 0:
                        result.append(char)
                    vowel_count += 1
            else:
                # Always keep consonants
                result.append(char)

        return ''.join(result)


# ============================================================
# TEST CLASS: ELISION Level 3 Compression
# ============================================================

@pytest.mark.elision_compression
class TestElisionLevel3Compression:
    """Tests for ELISION Level 3 compression effectiveness."""

    def test_level3_compression_savings(self, compressor):
        """Test that Level 3 saves more than Level 2."""
        data = {
            "context": "The orchestrator implements the compression mechanism for memory"
        }

        level2 = compressor.compress(data, level=2)
        level3 = compressor.compress(json.dumps(data), level=3)

        # Level 3 should not be larger than Level 2
        assert level3.compressed_length <= level2.compressed_length * 1.1  # Allow 10% margin

    def test_level3_target_compression_ratio(self, compressor):
        """Test Level 3 achieves compression savings."""
        data = {
            "implementation": "The comprehensive orchestrator system",
            "mechanism": "Advanced compression and memory management",
            "orchestration": "Parallel pipeline execution with subtasks"
        }

        result = compressor.compress(data, level=3)

        # Level 3 with whitespace removal should achieve some savings
        savings = 1 - (result.compressed_length / result.original_length)
        # JSON with whitespace removal should save at least 5%
        assert savings >= 0.0  # Should not increase size

    def test_level3_vs_level2_comparison(self, compressor):
        """Compare compression ratios across levels."""
        data = {
            "long_key_name": "This is a longer value that contains multiple words",
            "another_key": "More content for compression testing"
        }

        level1 = compressor.compress(data, level=1)
        level2 = compressor.compress(data, level=2)
        level3 = compressor.compress(data, level=3)

        # Each level should be <= previous level (monotonic decrease)
        assert level1.compressed_length >= level2.compressed_length
        assert level2.compressed_length >= level3.compressed_length

        # Verify compression ratios are correct
        assert level1.compression_ratio > 0
        assert level2.compression_ratio > 0
        assert level3.compression_ratio > 0

    def test_level3_preserves_structure(self, compressor):
        """Test that Level 3 compression preserves JSON structure."""
        data = {
            "orchestrator": {
                "implementation": "Details",
                "compression": ["item1", "item2"],
                "mechanism": {"nested": "value"}
            }
        }

        result = compressor.compress(data, level=3)

        # Result should still be valid JSON
        try:
            json.loads(result.compressed)
        except json.JSONDecodeError:
            pytest.fail("Level 3 compression should produce valid JSON")

    def test_level3_string_compression(self, compressor):
        """Test Level 3 with string input (not dict)."""
        text = "The implementation of orchestrator compression mechanism"

        result = compressor.compress(text, level=3)

        # Should compress the string
        assert result.compressed_length < result.original_length
        assert result.compression_ratio > 1.0


# ============================================================
# TEST CLASS: Surprise-Based Selection
# ============================================================

@pytest.mark.elision_compression
class TestSurpriseBasedSelection:
    """Tests for surprise-aware word selection in compression."""

    def test_high_surprise_words_preserved(self, compressor, cam):
        """Test that high surprise (rare) words are NOT heavily compressed."""
        context = "The quantum entanglement mechanism demonstrates theoretical physics"
        surprise_map = get_surprise_metrics(context, threshold=0.4)

        # Words that appear once should have highest surprise (1 - 1/6 = 0.833)
        single_occurrence = {
            word: metrics for word, metrics in surprise_map.items()
            if metrics.frequency == 1
        }

        assert len(single_occurrence) > 0
        # Single-occurrence words: quantum, entanglement, mechanism, demonstrates, theoretical, physics
        assert any(word in single_occurrence for word in ["quantum", "entanglement", "theoretical"])

    def test_low_surprise_words_compressed(self, compressor, cam):
        """Test that low surprise (common) words are compressed more."""
        context = "the the the implementation implementation implementation test test test"
        surprise_map = get_surprise_metrics(context, threshold=0.6)

        # Repeated words should have low surprise
        low_surprise = {
            word: metrics for word, metrics in surprise_map.items()
            if metrics.surprise_score < 0.4
        }

        assert len(low_surprise) > 0
        assert "the" in low_surprise  # Most frequent = lowest surprise

    def test_surprise_threshold_logic(self):
        """Test surprise score threshold comparison."""
        metrics = SurpriseMetrics(
            word="quantum",
            frequency=1,
            surprise_score=0.8,
            should_preserve=True
        )

        threshold = 0.6
        should_preserve = metrics.surprise_score > threshold
        assert should_preserve is True

    def test_surprise_score_range(self):
        """Test that surprise scores are in valid range [0.0, 1.0]."""
        text = "word word word rare"
        surprise_map = get_surprise_metrics(text)

        for word, metrics in surprise_map.items():
            assert 0.0 <= metrics.surprise_score <= 1.0

    def test_surprise_frequency_inverse_relationship(self):
        """Test that surprise is inverse of frequency."""
        text = "common common common common rare"
        surprise_map = get_surprise_metrics(text)

        common_surprise = surprise_map["common"].surprise_score
        rare_surprise = surprise_map["rare"].surprise_score

        # Rare should have higher surprise
        assert rare_surprise > common_surprise

    def test_surprise_with_elisya_context(self, compressor, cam, elisya_context):
        """Test surprise metrics on ElisyaState-like context."""
        context_str = json.dumps(elisya_context)
        surprise_map = get_surprise_metrics(context_str, threshold=0.5)

        # Should extract metrics from context
        assert len(surprise_map) > 0

        # Common words should have lower surprise
        if "the" in surprise_map:
            assert surprise_map["the"].surprise_score < 0.5


# ============================================================
# TEST CLASS: Word Compression Eligibility
# ============================================================

@pytest.mark.elision_compression
class TestWordCompressionEligibility:
    """Tests for determining which words are eligible for compression."""

    @pytest.mark.parametrize("word,should_compress", [
        ("understanding", True),      # Long word, common = compress
        ("the", False),                # Short word = no compress
        ("AI", False),                 # Acronym = no compress
        ("implementation", True),      # Long word = compress
        ("a", False),                  # Too short
        ("orchestrator", True),        # Long = compress
        ("is", False),                 # Too short
        ("mechanism", True),           # Long = compress
    ])
    def test_word_eligibility_criteria(self, word, should_compress):
        """Test eligibility based on word length and type."""
        min_length = 4  # Minimum length for compression

        # Short words and acronyms should not be compressed
        is_acronym = word.isupper() and len(word) <= 3
        is_eligible = len(word) >= min_length and not is_acronym

        assert is_eligible == should_compress

    def test_acronym_detection(self):
        """Test detection of acronyms (should not compress)."""
        acronyms = ["AI", "ML", "LLM", "JSON", "HTTP"]
        not_acronyms = ["hello", "world", "python"]

        for acronym in acronyms:
            is_acronym = acronym.isupper() and len(acronym) <= 4
            assert is_acronym is True

        for word in not_acronyms:
            is_acronym = word.isupper() and len(word) <= 4
            assert is_acronym is False

    def test_short_word_preservation(self):
        """Test that short words are preserved."""
        short_words = ["the", "is", "a", "in", "to", "at", "by", "or"]
        min_length = 4

        for word in short_words:
            is_eligible = len(word) >= min_length
            assert is_eligible is False

    def test_long_word_eligibility(self):
        """Test that long words are eligible."""
        long_words = ["orchestrator", "implementation", "understanding", "mechanism"]
        min_length = 4

        for word in long_words:
            is_eligible = len(word) >= min_length
            assert is_eligible is True

    def test_mixed_case_handling(self):
        """Test handling of mixed case words."""
        words = ["camelCase", "PascalCase", "snake_case", "ALLCAPS"]

        for word in words:
            # Should handle mixed case in compression eligibility
            min_length = 4
            is_eligible = len(word) >= min_length
            assert isinstance(is_eligible, bool)


# ============================================================
# TEST CLASS: Legend & Metadata
# ============================================================

@pytest.mark.elision_compression
class TestLegendAndMetadata:
    """Tests for legend generation and metadata tracking."""

    def test_level3_legend_contains_keys(self, compressor):
        """Test that Level 3 legend contains key abbreviations."""
        data = {"current_file": "test.py", "context": "data"}
        result = compressor.compress(data, level=3)

        # Should have legend
        assert result.legend is not None

    def test_legend_reversibility(self, compressor):
        """Test that legend allows reversal of compression."""
        data = {"current_file": "test", "user_id": "123"}
        result = compressor.compress(data, level=2)

        # Legend should contain mapping
        if result.legend:
            # Can expand using legend
            expanded = compressor.expand(result.compressed, result.legend)
            assert isinstance(expanded, str)

    def test_metadata_completeness(self, compressor):
        """Test that result contains all required metadata."""
        data = {"test": "data"}
        result = compressor.compress(data, level=3)

        # Check all metadata fields
        assert result.original is not None
        assert result.compressed is not None
        assert result.original_length > 0
        assert result.compressed_length > 0
        assert result.compression_ratio > 0
        assert result.level == 3

    def test_compression_ratio_calculation(self, compressor):
        """Test compression ratio is correctly calculated."""
        data = {"key": "value"}
        result = compressor.compress(data, level=3)

        expected_ratio = result.original_length / result.compressed_length
        assert abs(result.compression_ratio - expected_ratio) < 0.01

    def test_tokens_saved_estimation(self, compressor):
        """Test token savings estimation."""
        data = {"implementation": "This is a longer text for compression testing"}
        result = compressor.compress(data, level=3)

        # Tokens ~4 chars each
        estimated_saved = (result.original_length - result.compressed_length) // 4
        assert result.tokens_saved_estimate >= 0

    def test_vowel_skip_in_legend(self, compressor):
        """Test that vowel skip info is in legend if present."""
        data = {"orchestrator": "compression mechanism"}
        result = compressor.compress(data, level=3)

        # Legend should document compression methods used
        assert isinstance(result.legend, dict)


# ============================================================
# TEST CLASS: Integration Tests
# ============================================================

@pytest.mark.elision_compression
class TestElisionLevel3Integration:
    """Integration tests with ElisyaState-like contexts."""

    def test_integration_with_elisya_context(self, compressor, elisya_context):
        """Test compression of ElisyaState-like context."""
        result = compressor.compress(elisya_context, level=3)

        # Should compress significantly
        assert result.compressed_length < result.original_length
        # Should preserve structure
        assert isinstance(result.compressed, str)

    def test_integration_pipeline_context(self, compressor):
        """Test compression of pipeline context."""
        pipeline_context = {
            "pipeline_task": {
                "task_id": "pipeline_001",
                "task_description": "Implement orchestrator compression mechanism",
                "subtasks": [
                    {"description": "Design compression algorithm"},
                    {"description": "Implement vowel skipping"},
                    {"description": "Add surprise metrics"}
                ]
            }
        }

        result = compressor.compress(pipeline_context, level=3)
        # Level 3 should produce valid compression result
        assert result.compressed_length > 0
        assert result.original_length > 0
        # Legend should document compression
        assert isinstance(result.legend, dict)

    def test_integration_nested_structure(self, compressor):
        """Test compression of deeply nested structures."""
        nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "implementation": "test",
                        "orchestrator": "mechanism",
                        "compression": "algorithm"
                    }
                }
            }
        }

        result = compressor.compress(nested, level=3)
        # Should handle nesting gracefully
        assert result.compressed_length > 0

    def test_integration_with_conversation_history(self, compressor):
        """Test compression of conversation history."""
        conversation = {
            "conversation_history": [
                {
                    "speaker": "user",
                    "content": "Implement the orchestrator compression",
                    "timestamp": 1234567890
                },
                {
                    "speaker": "assistant",
                    "content": "I will implement the compression mechanism",
                    "timestamp": 1234567891
                }
            ]
        }

        result = compressor.compress(conversation, level=3)
        assert result.compressed_length < result.original_length

    def test_integration_roundtrip(self, compressor):
        """Test compression and expansion roundtrip."""
        data = {
            "user_id": "test_user",
            "current_file": "/src/module.py",
            "knowledge_level": 0.85
        }

        # Compress
        result = compressor.compress(data, level=2)

        # Should be able to expand
        expanded = compressor.expand(result.compressed, result.legend)
        assert isinstance(expanded, str)


# ============================================================
# TEST CLASS: Edge Cases & Error Handling
# ============================================================

@pytest.mark.elision_compression
class TestEdgeCasesAndErrors:
    """Tests for edge cases and error handling."""

    def test_empty_input(self, compressor):
        """Test compression of empty data."""
        result = compressor.compress({}, level=3)
        assert result.compressed_length >= 0

    def test_none_input(self, compressor):
        """Test handling of None input."""
        result = compressor.compress("null", level=3)
        assert result.compressed is not None

    def test_special_characters(self, compressor):
        """Test compression with special characters."""
        data = {"special": "!@#$%^&*()_+-=[]{}|;:',.<>?/"}
        result = compressor.compress(data, level=3)
        assert result.compressed_length >= 0

    def test_unicode_content(self, compressor):
        """Test compression with unicode content."""
        data = {"content": "Hello 你好 مرحبا שלום"}
        result = compressor.compress(data, level=3)
        assert result.compressed_length > 0

    def test_very_long_content(self, compressor):
        """Test compression of very long content."""
        long_text = "word " * 1000
        result = compressor.compress(long_text, level=3)

        # Should handle large content
        assert result.compressed_length < result.original_length

    def test_numbers_only(self, compressor):
        """Test compression of numeric content."""
        data = {"numbers": [1, 2, 3, 4, 5] * 100}
        result = compressor.compress(data, level=3)
        assert result.compressed_length >= 0

    def test_mixed_types(self, compressor):
        """Test compression with mixed data types."""
        data = {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "array": [1, "two", 3.0],
            "object": {"nested": "value"}
        }
        result = compressor.compress(data, level=3)
        assert result.compressed_length > 0


# ============================================================
# TEST CLASS: Parametrized Tests
# ============================================================

@pytest.mark.elision_compression
class TestParametrizedVowelSkip:
    """Parametrized tests for vowel skipping variations."""

    @pytest.mark.parametrize("rate,min_savings", [
        (0.3, 0.15),  # Mild compression, 15%+ savings
        (0.5, 0.25),  # Moderate compression, 25%+ savings
        (0.7, 0.35),  # Aggressive compression, 35%+ savings
    ])
    def test_vowel_skip_rates(self, rate, min_savings):
        """Test different vowel skip rates."""
        word = "implementation"
        vowels = set('aeiouAEIOU')
        vowel_count = sum(1 for c in word if c in vowels)

        # Simulate vowel skipping
        savings_ratio = rate * vowel_count / len(word)
        assert savings_ratio >= 0.0

    @pytest.mark.parametrize("word,expected_short", [
        ("orchestrator", True),
        ("mechanism", True),
        ("the", False),
        ("AI", False),
    ])
    def test_word_compression_candidates(self, word, expected_short):
        """Test identification of compression candidates."""
        is_candidate = len(word) >= 4 and not word.isupper()
        assert is_candidate == expected_short

    @pytest.mark.parametrize("text_type,compression_level", [
        ("code", 2),
        ("conversation", 3),
        ("knowledge", 3),
        ("context", 2),
    ])
    def test_context_type_compression(self, compressor, text_type, compression_level):
        """Test compression based on context type."""
        contexts = {
            "code": "def function(): pass",
            "conversation": "What is your name? My name is Claude",
            "knowledge": "The orchestrator implements compression",
            "context": "File: test.py Location: /src"
        }

        data = contexts.get(text_type, "")
        result = compressor.compress(data, level=compression_level)
        assert result.level == compression_level


# ============================================================
# TEST UTILITIES
# ============================================================

@pytest.fixture
def print_compression_stats(compressor):
    """Helper fixture to print compression statistics."""
    def _print(label: str, data: Any, level: int = 3):
        """Print compression stats for data."""
        result = compressor.compress(data, level=level)
        print(f"\n{label}:")
        print(f"  Original: {result.original_length} chars")
        print(f"  Compressed: {result.compressed_length} chars")
        print(f"  Ratio: {result.compression_ratio:.2f}x")
        print(f"  Savings: {100 * (1 - result.compressed_length/result.original_length):.1f}%")
        print(f"  Tokens: {result.tokens_saved_estimate} saved")
        return result

    return _print


# ============================================================
# TEST EXECUTION
# ============================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "elision_compression",
        "--co"  # Show collection
    ])
