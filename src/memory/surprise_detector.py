"""
VETKA Phase 104 - CAM (Context Awareness Module)
Surprise detection for intelligent ELISION compression.

MARKER_104_CAM

Uses embeddings to detect semantic shifts in context.
Like FFmpeg scene detection but for text.

Based on Grok research:
- CAM detects "semantic shifts" like video cut detection
- Surprise score = cosine distance between consecutive context blocks
- Low surprise (<0.3) = compress aggressively (vowel skip)
- High surprise (>0.7) = keep full (preserve semantics)

@file surprise_detector.py
@status active
@phase 104
@depends numpy, typing, collections, re
@used_by elision.py, jarvis_prompt_enricher.py, orchestrator_with_elisya.py

DISTINCTION from src/orchestration/cam_engine.py:
- cam_engine.py: Constructivist Agentic Memory for TREE RESTRUCTURING
- surprise_detector.py: Context Awareness Module for ELISION COMPRESSION
"""

import logging
import math
import re
import threading
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter

# Optional numpy import with fallback
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

logger = logging.getLogger(__name__)

# =============================================================================
# STOPWORDS for frequency analysis
# =============================================================================

STOPWORDS = frozenset({
    # English stopwords (common)
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought',
    'used', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
    'we', 'they', 'what', 'which', 'who', 'whom', 'whose', 'where', 'when',
    'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
    'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there', 'then',
    'if', 'else', 'because', 'about', 'into', 'through', 'during', 'before',
    'after', 'above', 'below', 'between', 'under', 'again', 'further', 'once',

    # Programming keywords (common across languages)
    'def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif', 'for',
    'while', 'try', 'except', 'finally', 'with', 'as', 'pass', 'break',
    'continue', 'lambda', 'yield', 'raise', 'assert', 'del', 'in', 'is',
    'and', 'or', 'not', 'true', 'false', 'none', 'self', 'cls',
    'function', 'const', 'let', 'var', 'async', 'await', 'new', 'this',
    'null', 'undefined', 'void', 'typeof', 'instanceof',

    # Common short words
    'get', 'set', 'add', 'put', 'run', 'end', 'use', 'see', 'say', 'way',
    'its', 'any', 'out', 'up', 'one', 'two', 'my', 'me', 'us', 'our', 'him',
    'her', 'his', 'your', 'their', 'them',
})

# Minimum word length for theme extraction
MIN_WORD_LENGTH = 3


class CAMMemory:
    """
    Context Awareness Module for semantic surprise detection.

    MARKER_104_CAM

    Detects semantic shifts in context blocks, similar to video scene detection.
    Used by ELISION Level 3 to decide compression intensity:
    - Low surprise (<0.3): Compress aggressively (predictable content)
    - Medium surprise (0.3-0.7): Standard compression
    - High surprise (>0.7): Keep full (important semantic content)

    Works without external embeddings by using word frequency analysis.
    Can optionally use OpenAI embeddings for better accuracy.

    Usage:
        cam = CAMMemory()
        surprise = cam.compute_surprise(block1, block2)  # 0.0-1.0
        word_map = cam.get_surprise_map(text)  # {word: surprise_score}
    """

    # Thresholds for ELISION integration
    THRESHOLD_LOW = 0.3    # Below: compress aggressively
    THRESHOLD_HIGH = 0.7   # Above: preserve fully

    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        use_embeddings: bool = False,
        cache_size: int = 100
    ):
        """
        Initialize CAM Memory.

        Args:
            embedding_model: OpenAI embedding model name (if use_embeddings=True)
            use_embeddings: Whether to use external embeddings (default: False)
            cache_size: Size of embedding cache
        """
        self.embedding_model = embedding_model
        self.use_embeddings = use_embeddings
        self._cache: Dict[int, Any] = {}  # hash -> embedding
        self._cache_size = cache_size

        # Statistics
        self._stats = {
            'surprise_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
        }

        logger.debug(
            f"[CAM Memory] Initialized (embeddings={use_embeddings}, "
            f"model={embedding_model})"
        )

    def compute_surprise(self, block1: str, block2: str) -> float:
        """
        Compute surprise score between two text blocks.

        Surprise = semantic distance between consecutive blocks.
        High surprise indicates a "semantic shift" (like video scene cut).

        Args:
            block1: First text block (previous context)
            block2: Second text block (current context)

        Returns:
            Surprise score from 0.0 (identical) to 1.0 (completely different)
        """
        self._stats['surprise_calls'] += 1

        # Handle edge cases
        if not block1 or not block2:
            return 0.5  # Neutral for missing blocks

        if block1 == block2:
            return 0.0  # Identical blocks

        # Try embeddings first if enabled
        if self.use_embeddings and HAS_NUMPY:
            emb_surprise = self._compute_surprise_embeddings(block1, block2)
            if emb_surprise is not None:
                return emb_surprise

        # Fallback to word-based similarity
        return self._compute_surprise_words(block1, block2)

    def _compute_surprise_words(self, block1: str, block2: str) -> float:
        """
        Compute surprise using word overlap (Jaccard distance).

        This is the fallback when embeddings are not available.
        Uses weighted Jaccard with TF consideration.
        """
        # Tokenize and normalize
        words1 = self._tokenize(block1)
        words2 = self._tokenize(block2)

        if not words1 or not words2:
            return 0.5

        # Build word frequency vectors
        freq1 = Counter(words1)
        freq2 = Counter(words2)

        # All unique words
        all_words = set(freq1.keys()) | set(freq2.keys())

        if not all_words:
            return 0.5

        # Weighted Jaccard similarity
        # intersection = sum of min frequencies
        # union = sum of max frequencies
        intersection = 0.0
        union = 0.0

        for word in all_words:
            f1 = freq1.get(word, 0)
            f2 = freq2.get(word, 0)
            intersection += min(f1, f2)
            union += max(f1, f2)

        if union == 0:
            return 0.5

        similarity = intersection / union

        # Surprise = 1 - similarity (distance)
        surprise = 1.0 - similarity

        return max(0.0, min(1.0, surprise))

    def _compute_surprise_embeddings(
        self,
        block1: str,
        block2: str
    ) -> Optional[float]:
        """
        Compute surprise using cosine distance of embeddings.

        Returns None if embeddings cannot be computed.
        """
        emb1 = self._get_embedding(block1)
        emb2 = self._get_embedding(block2)

        if emb1 is None or emb2 is None:
            return None

        # Cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 < 1e-8 or norm2 < 1e-8:
            return 0.5

        similarity = dot_product / (norm1 * norm2)

        # Surprise = 1 - similarity (cosine distance)
        surprise = 1.0 - similarity

        # Normalize to [0, 1] (cosine distance is in [0, 2])
        surprise = surprise / 2.0

        return max(0.0, min(1.0, surprise))

    def _get_embedding(self, text: str) -> Optional[Any]:
        """
        Get embedding for text with caching.

        First tries local embedding service, then OpenAI if configured.
        """
        if not text:
            return None

        # Check cache
        cache_key = hash(text) % 100000
        if cache_key in self._cache:
            self._stats['cache_hits'] += 1
            return self._cache[cache_key]

        self._stats['cache_misses'] += 1

        # Try local embedding service first
        try:
            from src.utils.embedding_service import get_embedding
            embedding = get_embedding(text[:2000])  # Limit text length
            if embedding:
                embedding = np.array(embedding)
                self._cache_embedding(cache_key, embedding)
                return embedding
        except Exception as e:
            logger.debug(f"[CAM Memory] Local embedding failed: {e}")

        # Could add OpenAI fallback here if needed
        return None

    def _cache_embedding(self, key: int, embedding: Any) -> None:
        """Cache embedding with LRU eviction."""
        if len(self._cache) >= self._cache_size:
            # Remove oldest entry (simple FIFO for now)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = embedding

    def get_theme_frequency(
        self,
        context: str,
        top_n: int = 10
    ) -> Dict[str, int]:
        """
        Get top N words by frequency for abbreviation candidates.

        Used by ELISION to identify words that can be abbreviated
        because they appear frequently (reader can infer from context).

        Args:
            context: Text context to analyze
            top_n: Number of top words to return

        Returns:
            Dict mapping word -> frequency (sorted by frequency desc)
        """
        if not context:
            return {}

        # Tokenize and filter
        words = self._tokenize(context)

        # Filter stopwords and short words
        meaningful_words = [
            w for w in words
            if w not in STOPWORDS and len(w) >= MIN_WORD_LENGTH
        ]

        # Count frequencies
        freq = Counter(meaningful_words)

        # Return top N
        top_words = freq.most_common(top_n)

        return dict(top_words)

    def get_surprise_map(
        self,
        text: str,
        block_size: int = 100
    ) -> Dict[str, float]:
        """
        Get surprise score for each word based on context.

        Words with low surprise = frequent/predictable = can compress.
        Words with high surprise = unique/important = keep full.

        This is the main interface for ELISION Level 3 integration.

        Args:
            text: Full text to analyze
            block_size: Size of context blocks for surprise calculation

        Returns:
            Dict mapping word -> surprise score (0.0-1.0)
        """
        if not text:
            return {}

        words = self._tokenize(text)
        if not words:
            return {}

        # Build word frequency across entire text
        total_freq = Counter(words)
        total_words = len(words)

        # Calculate surprise for each unique word
        surprise_map: Dict[str, float] = {}

        for word in set(words):
            if word in STOPWORDS:
                # Stopwords always have low surprise
                surprise_map[word] = 0.1
                continue

            # Base surprise from frequency (rare = high surprise)
            freq = total_freq[word]
            freq_ratio = freq / total_words

            # Inverse frequency -> surprise
            # freq_ratio close to 0 (rare) -> high surprise
            # freq_ratio close to 1 (common) -> low surprise
            freq_surprise = 1.0 - min(1.0, freq_ratio * 10)  # Scale factor

            # Adjust by word properties
            length_factor = min(1.0, len(word) / 15)  # Longer = more specific

            # Combined surprise
            surprise = freq_surprise * 0.7 + length_factor * 0.3

            surprise_map[word] = max(0.0, min(1.0, surprise))

        return surprise_map

    def get_compression_recommendation(
        self,
        text: str
    ) -> Dict[str, Any]:
        """
        Get compression recommendation for ELISION integration.

        Analyzes text and returns:
        - Overall surprise score
        - Recommended compression level
        - Words to preserve (high surprise)
        - Words to compress (low surprise)

        Args:
            text: Text to analyze

        Returns:
            Dict with compression recommendations
        """
        if not text:
            return {
                'overall_surprise': 0.5,
                'compression_level': 2,
                'preserve_words': [],
                'compress_words': [],
            }

        surprise_map = self.get_surprise_map(text)

        if not surprise_map:
            return {
                'overall_surprise': 0.5,
                'compression_level': 2,
                'preserve_words': [],
                'compress_words': [],
            }

        # Calculate overall surprise (weighted average)
        total_surprise = sum(surprise_map.values())
        overall_surprise = total_surprise / len(surprise_map)

        # Recommend compression level
        if overall_surprise < self.THRESHOLD_LOW:
            compression_level = 4  # Aggressive
        elif overall_surprise > self.THRESHOLD_HIGH:
            compression_level = 1  # Conservative
        else:
            compression_level = 2  # Standard

        # Identify words to preserve vs compress
        preserve_words = [
            w for w, s in surprise_map.items()
            if s > self.THRESHOLD_HIGH and w not in STOPWORDS
        ]

        compress_words = [
            w for w, s in surprise_map.items()
            if s < self.THRESHOLD_LOW and len(w) > 4
        ]

        return {
            'overall_surprise': round(overall_surprise, 3),
            'compression_level': compression_level,
            'preserve_words': preserve_words[:20],  # Top 20
            'compress_words': compress_words[:20],  # Top 20
            'word_count': len(surprise_map),
            'high_surprise_ratio': len(preserve_words) / max(len(surprise_map), 1),
            'low_surprise_ratio': len(compress_words) / max(len(surprise_map), 1),
        }

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.

        Normalizes to lowercase, removes punctuation.
        """
        if not text:
            return []

        # Convert to lowercase
        text = text.lower()

        # Replace non-alphanumeric with spaces
        text = re.sub(r'[^a-z0-9_]', ' ', text)

        # Split and filter empty
        words = [w for w in text.split() if w]

        return words

    def get_stats(self) -> Dict[str, Any]:
        """Get CAM Memory statistics."""
        return {
            **self._stats,
            'cache_size': len(self._cache),
            'embeddings_enabled': self.use_embeddings,
        }

    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self._cache.clear()
        self._stats['cache_hits'] = 0
        self._stats['cache_misses'] = 0
        logger.debug("[CAM Memory] Cache cleared")


# =============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# =============================================================================

# MARKER_118.8_SINGLETON: Thread-safe singleton
_cam_lock = threading.Lock()
_cam_memory_instance: Optional[CAMMemory] = None


def get_cam_memory(use_embeddings: bool = False) -> CAMMemory:
    """Get singleton CAM Memory instance (thread-safe)."""
    global _cam_memory_instance
    if _cam_memory_instance is None:
        with _cam_lock:
            if _cam_memory_instance is None:
                _cam_memory_instance = CAMMemory(use_embeddings=use_embeddings)
                logger.info("[CAM Memory] Singleton initialized")
    return _cam_memory_instance


def reset_cam_memory() -> None:
    """Reset singleton for testing purposes."""
    global _cam_memory_instance
    with _cam_lock:
        _cam_memory_instance = None
        logger.info("[CAM Memory] Singleton reset")


def get_surprise_metrics(text: str) -> Dict[str, float]:
    """
    Convenience function for ELISION integration.

    Returns surprise map for each word in text.

    Args:
        text: Text to analyze

    Returns:
        Dict mapping word -> surprise score (0.0-1.0)
    """
    cam = get_cam_memory()
    return cam.get_surprise_map(text)


def compute_block_surprise(block1: str, block2: str) -> float:
    """
    Convenience function to compute surprise between two text blocks.

    Args:
        block1: Previous context block
        block2: Current context block

    Returns:
        Surprise score (0.0-1.0)
    """
    cam = get_cam_memory()
    return cam.compute_surprise(block1, block2)


def get_compression_advice(text: str) -> Dict[str, Any]:
    """
    Get compression advice for ELISION.

    Args:
        text: Text to analyze

    Returns:
        Dict with compression recommendations
    """
    cam = get_cam_memory()
    return cam.get_compression_recommendation(text)


# =============================================================================
# TESTS (run with: python -m src.memory.cam_memory)
# =============================================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("VETKA Phase 104 - CAM Memory Tests")
    print("=" * 60)

    # Test 1: compute_surprise returns 0-1
    print("\n[Test 1] compute_surprise returns value in range [0, 1]")

    cam = CAMMemory()

    # Identical blocks
    s1 = cam.compute_surprise("hello world", "hello world")
    assert 0.0 <= s1 <= 1.0, f"Surprise out of range: {s1}"
    assert s1 == 0.0, f"Identical blocks should have 0 surprise, got {s1}"
    print(f"  - Identical blocks: surprise = {s1} (expected 0.0)")

    # Similar blocks
    s2 = cam.compute_surprise(
        "The quick brown fox jumps over the lazy dog",
        "The quick brown fox leaps over the lazy cat"
    )
    assert 0.0 <= s2 <= 1.0, f"Surprise out of range: {s2}"
    print(f"  - Similar blocks: surprise = {s2:.3f} (expected ~0.2-0.4)")

    # Different blocks
    s3 = cam.compute_surprise(
        "Python is a programming language",
        "The weather today is sunny and warm"
    )
    assert 0.0 <= s3 <= 1.0, f"Surprise out of range: {s3}"
    assert s3 > 0.5, f"Different blocks should have high surprise, got {s3}"
    print(f"  - Different blocks: surprise = {s3:.3f} (expected >0.5)")

    # Empty/None blocks
    s4 = cam.compute_surprise("", "hello")
    assert 0.0 <= s4 <= 1.0, f"Surprise out of range: {s4}"
    print(f"  - Empty block: surprise = {s4:.3f} (expected 0.5)")

    print("  [PASS] All compute_surprise tests passed")

    # Test 2: get_theme_frequency excludes stopwords
    print("\n[Test 2] get_theme_frequency excludes stopwords")

    test_text = """
    The function imports data from the database and processes it.
    The data is then transformed using Python functions.
    Finally, the processed data is exported to JSON format.
    """

    themes = cam.get_theme_frequency(test_text, top_n=10)
    print(f"  - Top themes: {themes}")

    # Check stopwords are excluded
    for stopword in ['the', 'is', 'and', 'from', 'to']:
        assert stopword not in themes, f"Stopword '{stopword}' found in themes"

    # Check meaningful words are included
    assert 'data' in themes, "Expected 'data' in themes"
    assert 'function' in themes or 'functions' in themes, "Expected 'function' in themes"

    print("  [PASS] Stopwords correctly excluded")

    # Test 3: get_surprise_map marks unique words high
    print("\n[Test 3] get_surprise_map marks unique words high")

    test_text = """
    Python Python Python Python Python code code code.
    The xyzzy12345 is a unique identifier that appears only once.
    Python code is great for data processing.
    """

    surprise_map = cam.get_surprise_map(test_text)
    print(f"  - Sample surprise scores:")

    # Frequent word should have low surprise
    if 'python' in surprise_map:
        assert surprise_map['python'] < 0.5, \
            f"Frequent word 'python' should have low surprise: {surprise_map['python']}"
        print(f"    - 'python' (frequent): {surprise_map['python']:.3f}")

    # Unique word should have high surprise
    if 'xyzzy12345' in surprise_map:
        assert surprise_map['xyzzy12345'] > 0.5, \
            f"Unique word 'xyzzy12345' should have high surprise: {surprise_map['xyzzy12345']}"
        print(f"    - 'xyzzy12345' (unique): {surprise_map['xyzzy12345']:.3f}")

    # Stopwords should have low surprise
    if 'the' in surprise_map:
        assert surprise_map['the'] < 0.3, \
            f"Stopword 'the' should have low surprise: {surprise_map['the']}"
        print(f"    - 'the' (stopword): {surprise_map['the']:.3f}")

    print("  [PASS] Surprise map correctly assigns scores")

    # Test 4: get_compression_recommendation
    print("\n[Test 4] get_compression_recommendation")

    # Low surprise text (repetitive)
    low_text = "data data data data data code code code code processing processing"
    low_rec = cam.get_compression_recommendation(low_text)
    print(f"  - Low surprise text: level={low_rec['compression_level']}, "
          f"surprise={low_rec['overall_surprise']:.3f}")

    # High surprise text (diverse)
    high_text = "quantum entanglement cryptocurrency blockchain neural artificial"
    high_rec = cam.get_compression_recommendation(high_text)
    print(f"  - High surprise text: level={high_rec['compression_level']}, "
          f"surprise={high_rec['overall_surprise']:.3f}")

    assert low_rec['compression_level'] >= high_rec['compression_level'], \
        "Low surprise text should recommend higher compression"

    print("  [PASS] Compression recommendations are sensible")

    # Test 5: Convenience functions
    print("\n[Test 5] Convenience functions")

    reset_cam_memory()  # Reset singleton

    metrics = get_surprise_metrics("hello world hello world")
    assert isinstance(metrics, dict), "get_surprise_metrics should return dict"
    print(f"  - get_surprise_metrics: {len(metrics)} words")

    surprise = compute_block_surprise("foo bar", "baz qux")
    assert 0.0 <= surprise <= 1.0, "compute_block_surprise out of range"
    print(f"  - compute_block_surprise: {surprise:.3f}")

    advice = get_compression_advice("test text for compression")
    assert 'compression_level' in advice, "Missing compression_level"
    print(f"  - get_compression_advice: level={advice['compression_level']}")

    print("  [PASS] Convenience functions work correctly")

    # Summary
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)

    # Show stats
    cam_instance = get_cam_memory()
    print(f"\nCAM Memory Stats: {cam_instance.get_stats()}")

    sys.exit(0)
