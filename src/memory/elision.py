"""
VETKA Phase 92 - ELISION Compression
Token-efficient JSON context compression

@file elision.py
@status active
@phase 104
@depends json, re, dataclasses, pathlib
@used_by jarvis_prompt_enricher.py, shared_tools.py, llm_call_tool.py, vetka_mcp_bridge.py, tools.py (agents)

ELISION = Efficient Language-Independent Symbolic Inversion of Names

Compression layers:
1. Key abbreviation (current_file -> cf)
2. Path compression (/src/orchestration/ -> s/o/)
3. Vowel skipping with CAM surprise selection (MARKER_104_ELISION_L3)
4. Whitespace removal (JSON separators)
5. Local dictionary (per-subtree)

Target: 60-70% token savings without semantic loss
"""

import json
import re
import threading
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path


# =============================================================================
# ELISION DICTIONARY - Key/Value Abbreviations
# =============================================================================

ELISION_MAP = {
    # Context structure
    "context": "c",
    "user": "u",
    "user_id": "uid",
    "message": "m",
    "timestamp": "t",
    "pinned": "p",
    "viewport": "v",
    "dependencies": "d",
    "semantic": "s",
    "results": "r",

    # File metadata
    "current_file": "cf",
    "file_path": "fp",
    "file_name": "fn",
    "file_type": "ft",
    "extension": "ext",
    "content": "cnt",
    "summary": "sum",

    # Code structure
    "imports": "imp",
    "imported_by": "by",
    "functions": "fns",
    "classes": "cls",
    "variables": "vars",
    "exports": "exp",

    # Metrics
    "knowledge_level": "kl",
    "surprise_score": "ss",
    "confidence": "conf",
    "relevance": "rel",
    "score": "sc",
    "distance": "dist",
    "lod_level": "lod",

    # Node structure
    "children": "ch",
    "parent": "par",
    "depth": "dp",
    "position": "pos",

    # Common values
    "true": "1",
    "false": "0",
    "null": "~",
    "undefined": "~",

    # Types
    "file": "f",
    "folder": "d",  # directory
    "module": "mod",
    "package": "pkg",

    # Pipeline terms (MARKER_118.9_ELISION_PIPELINE)
    "estimated_complexity": "ec",
    "enriched_context": "ectx",
    "subtasks": "sts",
    "needs_research": "nr",
    "execution_order": "eo",
    "pipeline": "pl",
    "mycelium": "myc",
    "architect": "arc",
    "researcher": "res",
    "verifier": "ver",
    "description": "desc",
    "vetka_out": "vo",
    "vetka_staging": "vs",
    "vetka_mycelium_pipeline": "vmp",
    "surprise_detector": "sd",

    # MARKER_198.P0.5: Task board + agent field abbreviations
    "task_id": "tid",
    "assigned_to": "at",
    "priority": "pri",
    "session_id": "sid",
    "reflex_recommendations": "rr",
    "engram_learnings": "el",
    "task_board_summary": "tbs",
    "predecessor_advice": "pa",
    "protocol_status": "ps",
}

# Reverse map for expansion
ELISION_EXPAND = {v: k for k, v in ELISION_MAP.items()}

# Path prefix abbreviations
PATH_PREFIXES = {
    "/src/": "s/",
    "/tests/": "t/",
    "/docs/": "D/",
    "/client/": "C/",
    "/app/": "A/",
    "/orchestration/": "o/",
    "/memory/": "m/",
    "/agents/": "a/",
    "/api/": "api/",
    "/handlers/": "h/",
    "/routes/": "r/",
    "/utils/": "u/",
    "/services/": "srv/",
    "/components/": "cmp/",
}


@dataclass
class ElisionResult:
    """Result of ELISION compression"""
    original: str
    compressed: str
    original_length: int
    compressed_length: int
    compression_ratio: float
    tokens_saved_estimate: int
    level: int  # Compression level used (1-4)
    legend: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compressed": self.compressed,
            "original_length": self.original_length,
            "compressed_length": self.compressed_length,
            "compression_ratio": self.compression_ratio,
            "tokens_saved": self.tokens_saved_estimate,
            "level": self.level,
            "_legend": self.legend if self.legend else None
        }


class ElisionCompressor:
    """
    ELISION Compression Engine

    Compression levels:
    - Level 1: Key abbreviation only (safe, reversible)
    - Level 2: Level 1 + path compression
    - Level 3: Level 2 + vowel skipping with CAM surprise selection (MARKER_104_ELISION_L3)
    - Level 4: Level 3 + whitespace removal
    - Level 5: Level 4 + local dictionary (per-subtree)

    Usage:
        compressor = ElisionCompressor()
        result = compressor.compress(json_data, level=2)
        original = compressor.expand(result.compressed, result.legend)

        # Level 3 with surprise-based vowel skipping:
        result = compressor.compress(json_data, level=3, surprise_map={"word": 0.2})
    """

    def __init__(
        self,
        custom_map: Dict[str, str] = None,
        include_legend: bool = True
    ):
        """
        Initialize ELISION compressor.

        Args:
            custom_map: Additional abbreviations to merge with defaults
            include_legend: Include legend in output for expansion
        """
        self.elision_map = {**ELISION_MAP}
        if custom_map:
            self.elision_map.update(custom_map)

        self.expand_map = {v: k for k, v in self.elision_map.items()}
        self.include_legend = include_legend
        self._local_dict: Dict[str, str] = {}

    def compress(
        self,
        data: Any,
        level: int = 2,
        target_ratio: float = None,
        surprise_map: Optional[Dict[str, float]] = None
    ) -> ElisionResult:
        """
        Compress JSON data using ELISION.

        Args:
            data: Dict, list, or string to compress
            level: Compression level (1-5)
            target_ratio: Optional target compression ratio (0.1-0.9)
            surprise_map: Optional CAM surprise metrics {word: score} for Level 3

        Returns:
            ElisionResult with compressed data and metadata
        """
        # Convert to JSON string if needed
        if isinstance(data, (dict, list)):
            original = json.dumps(data, ensure_ascii=False)
        else:
            original = str(data)

        original_length = len(original)

        # Apply compression levels
        compressed = original
        used_legend = {}

        if level >= 1:
            compressed, legend1 = self._compress_keys(compressed)
            used_legend.update(legend1)

        if level >= 2:
            compressed = self._compress_paths(compressed)

        # MARKER_104_ELISION_L3: Level 3 - Vowel Skipping with Surprise Selection
        if level >= 3:
            compressed, vowel_legend = self._compress_vowels(compressed, surprise_map)
            used_legend.update(vowel_legend)

        if level >= 4:
            compressed = self._compress_whitespace(compressed)

        if level >= 5:
            compressed, legend5 = self._compress_local(compressed)
            used_legend.update(legend5)

        # If target ratio specified, may need more aggressive compression
        if target_ratio and len(compressed) / original_length > target_ratio:
            compressed = self._aggressive_compress(compressed, target_ratio, original_length)

        compressed_length = len(compressed)
        compression_ratio = original_length / compressed_length if compressed_length > 0 else 1.0
        tokens_saved = (original_length - compressed_length) // 4  # ~4 chars per token estimate

        return ElisionResult(
            original=original,
            compressed=compressed,
            original_length=original_length,
            compressed_length=compressed_length,
            compression_ratio=compression_ratio,
            tokens_saved_estimate=tokens_saved,
            level=level,
            legend=used_legend if self.include_legend else {}
        )

    def expand(
        self,
        compressed: str,
        legend: Dict[str, Any] = None
    ) -> str:
        """
        Expand compressed data back to original format.

        Args:
            compressed: ELISION-compressed string
            legend: Custom legend from compression (optional)
                   May include vowel_skip entries (vs_word -> compressed)

        Returns:
            Expanded JSON string
        """
        expanded = compressed

        # Merge provided legend with default expand map
        expand_map = {**self.expand_map}
        if legend:
            # Handle vowel_skip legend entries (vs_* -> original word)
            vowel_expansions = {}
            for k, v in legend.items():
                if k.startswith('vs_') and isinstance(v, str):
                    # vs_orchestrator -> rchstrtr means rchstrtr -> orchestrator
                    original_word = k[3:]  # Remove 'vs_' prefix
                    vowel_expansions[v] = original_word
                elif k == '_vowel_skip':
                    # Metadata entry, skip
                    continue
                elif isinstance(v, str):
                    expand_map[v] = k

            # Apply vowel expansions
            for compressed_word, original in vowel_expansions.items():
                expanded = expanded.replace(compressed_word, original)

        # Expand paths first (longer patterns)
        for short, full in sorted(PATH_PREFIXES.items(), key=lambda x: -len(x[1])):
            expanded = expanded.replace(full.replace("/", ""), short.replace("/", ""))

        # Expand keys (in quotes)
        for short, full in sorted(expand_map.items(), key=lambda x: -len(x[0])):
            # Only expand if it's a JSON key or standalone value
            expanded = re.sub(
                rf'"{re.escape(short)}"(\s*:)',
                f'"{full}"\\1',
                expanded
            )

        return expanded

    def compress_json_context(
        self,
        pinned_files: List[Dict[str, Any]] = None,
        viewport_context: Dict[str, Any] = None,
        dependencies: Dict[str, Any] = None,
        semantic_neighbors: List[Dict[str, Any]] = None,
        level: int = 2
    ) -> ElisionResult:
        """
        Compress VETKA JSON context specifically.

        This is the main entry point for compressing agent context.
        Based on Elisya research: build_compressed_json_context()

        Args:
            pinned_files: List of pinned files [{id, path, name, type}]
            viewport_context: Viewport data {viewport_nodes, zoom_level}
            dependencies: Dependency graph {file_id: {imports, imported_by, kl}}
            semantic_neighbors: Search results [{path, score}]
            level: Compression level (1-4)

        Returns:
            ElisionResult with compressed context
        """
        # Build context structure
        data = {
            "c": {  # context
                "t": "ctx",  # type marker
            }
        }

        # Pinned files
        if pinned_files:
            data["p"] = [
                {
                    "i": f.get("id", ""),
                    "p": self._shorten_path(f.get("path", "")),
                    "n": f.get("name", ""),
                    # Accept both "file" and "leaf" as file type
                    "t": "f" if f.get("type") in ["file", "leaf"] else "d"
                }
                for f in pinned_files[:20]  # Limit to 20
            ]

        # Viewport nodes
        if viewport_context and "viewport_nodes" in viewport_context:
            data["v"] = [
                {
                    "i": n.get("id", ""),
                    "p": self._shorten_path(n.get("path", "")),
                    "d": n.get("distance_to_camera", 0),
                    "l": n.get("lod_level", 0)
                }
                for n in viewport_context["viewport_nodes"][:30]  # Limit to 30
            ]
            data["c"]["z"] = viewport_context.get("zoom_level", "medium")

        # Dependencies
        if dependencies:
            data["d"] = {
                self._shorten_path(k): {
                    "imp": [self._shorten_path(p) for p in v.get("imports", [])[:5]],
                    "by": [self._shorten_path(p) for p in v.get("imported_by", [])[:3]],
                    "kl": round(v.get("knowledge_level", 0), 2)
                }
                for k, v in list(dependencies.items())[:20]  # Limit to 20
            }

        # Semantic neighbors
        if semantic_neighbors:
            data["s"] = [
                {
                    "p": self._shorten_path(n.get("path", "")),
                    "sc": round(n.get("score", 0), 2)
                }
                for n in semantic_neighbors[:10]  # Limit to 10
            ]

        return self.compress(data, level=level)

    def _compress_keys(self, json_str: str) -> Tuple[str, Dict[str, str]]:
        """Level 1: Compress JSON keys using ELISION map"""
        result = json_str
        used = {}

        for full, short in sorted(self.elision_map.items(), key=lambda x: -len(x[0])):
            # Only compress if it appears as a JSON key
            pattern = rf'"{re.escape(full)}"(\s*:)'
            if re.search(pattern, result):
                result = re.sub(pattern, f'"{short}"\\1', result)
                used[full] = short

        return result, used

    def _compress_paths(self, json_str: str) -> str:
        """Level 2: Compress file paths"""
        result = json_str

        for full, short in sorted(PATH_PREFIXES.items(), key=lambda x: -len(x[0])):
            result = result.replace(full, short)

        return result

    # =========================================================================
    # MARKER_104_ELISION_L3: Level 3 - Vowel Skipping with Surprise Selection
    # =========================================================================

    def _vowel_skip(self, word: str, ratio: float = 0.5, connector: str = "") -> str:
        """
        Skip vowels from word for compression. Preserves consonant skeleton.

        Args:
            word: Word to compress
            ratio: Fraction of vowels to remove (0.0-1.0)
            connector: Optional connector to replace vowels with

        Returns:
            Compressed word with vowels removed

        Examples:
            _vowel_skip("orchestrator", 0.7) -> "rchstrtr"
            _vowel_skip("message", 0.5) -> "mssge"
        """
        if len(word) < 4:  # Don't compress short words
            return word

        vowels = 'aeiouAEIOU'
        chars = list(word)
        # Find vowel indices, keeping first character intact
        vowel_indices = [i for i, c in enumerate(chars) if c in vowels and i > 0]

        if not vowel_indices:
            return word

        to_remove = int(len(vowel_indices) * ratio)
        for idx in vowel_indices[:to_remove]:
            chars[idx] = connector

        return "".join(c for c in chars if c != "")

    def _compress_vowels(
        self,
        json_str: str,
        surprise_map: Optional[Dict[str, float]] = None
    ) -> Tuple[str, Dict[str, str]]:
        """
        Level 3: Selective vowel skipping based on CAM surprise metrics.

        Low surprise words (common, predictable) get compressed heavily.
        High surprise words (unique, important) are kept intact.

        Args:
            json_str: JSON string to compress
            surprise_map: Optional {word: surprise_score} from CAM

        Returns:
            Tuple of (compressed_string, legend)
        """
        # Try to get surprise map from CAM if not provided
        if surprise_map is None:
            try:
                from src.memory.surprise_detector import get_surprise_metrics
                surprise_map = get_surprise_metrics(json_str)
            except (ImportError, AttributeError):
                # CAM not available, use empty map (moderate compression)
                surprise_map = {}

        # Track original -> compressed mappings for legend
        vowel_legend = {}
        processed_words = set()

        def selective_skip(text: str) -> str:
            """Apply selective vowel skipping to text."""
            words = text.split()
            result_words = []

            for word in words:
                # Skip if already processed or is a short code/symbol
                if len(word) < 4 or word.startswith('$') or word.startswith('/'):
                    result_words.append(word)
                    continue

                # Get surprise score for word (default 0.5 = medium)
                word_lower = word.lower().strip('",.:;!?()[]{}')
                score = surprise_map.get(word_lower, 0.5)

                if score < 0.3:  # Low surprise: compress heavily (70% vowels)
                    compressed = self._vowel_skip(word, 0.7)
                    if compressed != word and word_lower not in processed_words:
                        vowel_legend[f"vs_{word_lower}"] = compressed
                        processed_words.add(word_lower)
                    result_words.append(compressed)
                elif score > 0.7:  # High surprise: keep full
                    result_words.append(word)
                else:  # Medium surprise: light compression (30% vowels)
                    compressed = self._vowel_skip(word, 0.3)
                    if compressed != word and word_lower not in processed_words:
                        vowel_legend[f"vs_{word_lower}"] = compressed
                        processed_words.add(word_lower)
                    result_words.append(compressed)

            return " ".join(result_words)

        # Apply to string values in JSON (preserve structure)
        try:
            data = json.loads(json_str)
            compressed_data = self._apply_to_values(data, selective_skip)
            result = json.dumps(compressed_data, ensure_ascii=False)
        except json.JSONDecodeError:
            # Not valid JSON, apply directly
            result = selective_skip(json_str)

        # Add vowel_skip metadata to legend
        vowel_legend['_vowel_skip'] = {
            'level': 3,
            'thresholds': {'low': 0.3, 'high': 0.7},
            'ratios': {'low_surprise': 0.7, 'medium_surprise': 0.3, 'high_surprise': 0.0}
        }

        return result, vowel_legend

    def _apply_to_values(self, data: Any, transform_fn) -> Any:
        """
        Recursively apply transform function to string values in data structure.

        Args:
            data: Dict, list, or primitive value
            transform_fn: Function to apply to string values

        Returns:
            Transformed data structure
        """
        if isinstance(data, dict):
            return {k: self._apply_to_values(v, transform_fn) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._apply_to_values(item, transform_fn) for item in data]
        elif isinstance(data, str):
            return transform_fn(data)
        else:
            return data

    def _compress_whitespace(self, json_str: str) -> str:
        """Level 4: Remove unnecessary whitespace"""
        try:
            # Parse and re-dump with minimal separators
            data = json.loads(json_str)
            return json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        except json.JSONDecodeError:
            # If not valid JSON, just remove obvious whitespace
            return re.sub(r'\s+', ' ', json_str).strip()

    def _compress_local(self, json_str: str) -> Tuple[str, Dict[str, str]]:
        """Level 5: Build local dictionary for repeated strings"""
        result = json_str
        local_legend = {}

        # Find repeated strings (3+ occurrences, 5+ chars)
        words = re.findall(r'"([^"]{5,})"', json_str)
        word_counts = {}
        for w in words:
            word_counts[w] = word_counts.get(w, 0) + 1

        # Create short codes for frequent strings
        idx = 0
        for word, count in sorted(word_counts.items(), key=lambda x: -x[1]):
            if count >= 3 and word not in self.elision_map and word not in self.expand_map:
                short = f"${idx}"
                result = result.replace(f'"{word}"', f'"{short}"')
                local_legend[word] = short
                idx += 1
                if idx >= 26:  # Limit local dictionary
                    break

        return result, local_legend

    def compress_level_3(
        self,
        data: Any,
        surprise_map: Optional[Dict[str, float]] = None
    ) -> ElisionResult:
        """
        MARKER_104_ELISION_L3: Level 3 compression with vowel skipping.

        Convenience method for Level 3 compression with CAM surprise selection.
        Applies Level 2 (keys + paths) then adds selective vowel skipping.

        Low surprise words: skip 70% vowels (e.g., "orchestrator" -> "rchstrtr")
        High surprise words: keep full
        Medium surprise: skip 30% vowels

        Target: additional 20% savings (60-70% total compression)

        Args:
            data: Data to compress (dict, list, or string)
            surprise_map: Optional CAM surprise metrics {word: score}
                         If None, attempts to import from surprise_detector

        Returns:
            ElisionResult with compressed data and vowel_skip legend

        Usage:
            compressor = ElisionCompressor()
            result = compressor.compress_level_3(context_data)
            # Or with custom surprise map:
            result = compressor.compress_level_3(data, {"important": 0.9, "common": 0.1})
        """
        return self.compress(data, level=3, surprise_map=surprise_map)

    def _aggressive_compress(
        self,
        text: str,
        target_ratio: float,
        original_length: int
    ) -> str:
        """Additional compression to reach target ratio"""
        current_ratio = len(text) / original_length

        if current_ratio <= target_ratio:
            return text

        # Try removing less important parts
        # 1. Truncate long string values
        def truncate_values(match):
            val = match.group(1)
            if len(val) > 50:
                return f'"{val[:47]}..."'
            return match.group(0)

        text = re.sub(r'"([^"]{50,})"', truncate_values, text)

        return text

    def _shorten_path(self, path: str) -> str:
        """Shorten a file path using prefix compression"""
        if not path:
            return ""

        result = path
        for full, short in PATH_PREFIXES.items():
            result = result.replace(full, short)

        # Also shorten remaining path components
        parts = result.split('/')
        if len(parts) > 3:
            # Keep first char of middle components
            shortened = [parts[0]]
            for p in parts[1:-1]:
                shortened.append(p[0] if p else '')
            shortened.append(parts[-1])
            result = '/'.join(shortened)

        return result


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

# MARKER_118.8_SINGLETON: Thread-safe singleton
_elision_lock = threading.Lock()
_compressor_instance: Optional[ElisionCompressor] = None


def get_elision_compressor() -> ElisionCompressor:
    """Get singleton ElisionCompressor instance (thread-safe)."""
    global _compressor_instance
    if _compressor_instance is None:
        with _elision_lock:
            if _compressor_instance is None:
                _compressor_instance = ElisionCompressor()
    return _compressor_instance


def compress_context(
    context: str,
    level: int = 2,
    target_ratio: float = None
) -> Dict[str, Any]:
    """
    Convenience function to compress context.

    Args:
        context: JSON string or text to compress
        level: Compression level (1-4)
        target_ratio: Optional target ratio

    Returns:
        Dict with compressed data and metadata
    """
    compressor = get_elision_compressor()
    result = compressor.compress(context, level=level, target_ratio=target_ratio)
    return result.to_dict()


def expand_context(compressed: str, legend: Dict[str, str] = None) -> str:
    """
    Convenience function to expand compressed context.

    Args:
        compressed: ELISION-compressed string
        legend: Legend from compression

    Returns:
        Expanded string
    """
    compressor = get_elision_compressor()
    return compressor.expand(compressed, legend)


def compress_level_3(
    data: Any,
    surprise_map: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    MARKER_104_ELISION_L3: Convenience function for Level 3 compression.

    Level 3 = Level 2 + selective vowel skipping based on CAM surprise.
    Target: 60-70% total compression.

    Args:
        data: Data to compress
        surprise_map: Optional CAM surprise metrics {word: score}

    Returns:
        Dict with compressed data and metadata including vowel_skip info
    """
    compressor = get_elision_compressor()
    result = compressor.compress_level_3(data, surprise_map)
    return result.to_dict()


# =============================================================================
# ASYNC WRAPPERS (for tool integration)
# =============================================================================

async def async_compress_context(
    context: str,
    level: int = 2,
    target_ratio: float = None,
    surprise_map: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Async wrapper for compress_context"""
    compressor = get_elision_compressor()
    result = compressor.compress(context, level, target_ratio, surprise_map)
    return result.to_dict()


async def async_compress_level_3(
    data: Any,
    surprise_map: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """MARKER_104_ELISION_L3: Async wrapper for Level 3 compression"""
    return compress_level_3(data, surprise_map)


async def async_expand_context(
    compressed: str,
    legend: Dict[str, str] = None
) -> str:
    """Async wrapper for expand_context"""
    return expand_context(compressed, legend)


