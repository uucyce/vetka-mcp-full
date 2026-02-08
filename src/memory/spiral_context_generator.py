"""
Phase 108.7: Spiral Context Generator - MGC + ELISION + HOPE Integration

Based on Grok's research: "Оптимизация Контекста в Vetka"
Implements Pi-spiral progressive disclosure for LLM context.

@file spiral_context_generator.py
@status active
@phase 108.7
@depends elision.py, engram_user_memory.py, hope_enhancer.py
@used_by orchestrator_with_elisya.py, vetka_mcp_bridge.py, session_tools.py

MARKER_108_7_SPIRAL_CONTEXT: Spiral context generation
- LOD by zoom level (Pi-spiral: radius = Pi * depth)
- MGC generations (Gen0: RAM hot, Gen1: Qdrant mid, Gen2: summarized)
- ELISION compression (40-60% token savings)
- HOPE frequency layers (LOW/MID/HIGH)

Token Budget:
- zoom < 0.3 (overview): ~500 tokens (LOW layer only)
- zoom 0.3-1.0 (mid): ~1000 tokens (LOW + MID)
- zoom > 1.0 (close-up): ~2000 tokens (all layers)

Target: 80% token savings vs raw file lists, 0 noise
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import math

from src.memory.mgc_cache import get_mgc_cache

logger = logging.getLogger(__name__)


# =============================================================================
# MARKER_108_7_SPIRAL_CONTEXT: Constants & Enums
# =============================================================================

class SpiralLayer(Enum):
    """Frequency layers for spiral disclosure (HOPE-aligned)."""
    LOW = "low"       # Overview: stats, top vectors (~200 words)
    MID = "mid"       # Relations: dependencies, clusters (~400 words)
    HIGH = "high"     # Details: code snippets, full context (~600 words)


class MGCGeneration(Enum):
    """Multi-Generational Cache levels."""
    GEN0 = 0  # RAM hot: pinned files, active context
    GEN1 = 1  # Qdrant mid: summaries, embeddings
    GEN2 = 2  # Archive: compressed historical data


# Pi-spiral parameters
PI = math.pi
SPIRAL_ITERATIONS = 3  # Pi/10 → Pi/1 → Pi*3


@dataclass
class SpiralConfig:
    """Configuration for spiral context generation."""
    max_tokens: int = 2000
    zoom_threshold_low: float = 0.3
    zoom_threshold_mid: float = 1.0
    top_pinned_count: int = 4
    top_visible_count: int = 10
    enable_elision: bool = True
    enable_hope: bool = True
    enable_mgc: bool = True


@dataclass
class SpiralContext:
    """Generated spiral context result."""
    layer: SpiralLayer
    gen0: Dict[str, Any]  # Hot context (pinned, query)
    gen1: Dict[str, Any]  # Mid context (stats, structure)
    gen2: Optional[Dict[str, Any]] = None  # Archive (if HIGH layer)
    tokens_estimate: int = 0
    compression_ratio: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# MARKER_119.1: MGCGraphCache removed — using canonical MGCCache singleton
# See src/memory/mgc_cache.py for the unified implementation
# =============================================================================

class SpiralContextGenerator:
    """
    Generates progressive spiral context for LLM.

    Based on Grok's research:
    - Pi-spiral depth (radius = Pi * iteration)
    - LOD filtering by zoom
    - MGC + ELISION + HOPE integration
    """

    def __init__(self, config: Optional[SpiralConfig] = None):
        self.config = config or SpiralConfig()
        self.mgc_cache = get_mgc_cache()  # MARKER_119.1: canonical singleton
        self._elision_enabled = self.config.enable_elision
        self._hope_enabled = self.config.enable_hope

    def generate(
        self,
        zoom: float,
        user_query: str,
        pinned_paths: List[str],
        visible_stats: Dict[str, Any],
        viewport_data: Optional[Dict[str, Any]] = None
    ) -> SpiralContext:
        """
        Generate spiral context based on zoom level and query.

        Args:
            zoom: Current viewport zoom (0 = far, >1 = close)
            user_query: User's query for semantic filtering
            pinned_paths: List of pinned file paths
            visible_stats: Viewport statistics (count, distances)
            viewport_data: Full viewport data if available

        Returns:
            SpiralContext with appropriate detail level
        """
        # Determine spiral layer based on zoom
        layer = self._get_layer_for_zoom(zoom)

        # Build Gen0 (hot context)
        gen0 = self._build_gen0(pinned_paths, user_query)

        # Build Gen1 (stats/structure)
        gen1 = self._build_gen1(visible_stats, viewport_data)

        # Build Gen2 only for HIGH layer
        gen2 = None
        if layer == SpiralLayer.HIGH:
            gen2 = self._build_gen2(pinned_paths, viewport_data)

        # Apply ELISION compression
        if self._elision_enabled:
            gen0, gen1, gen2, ratio = self._apply_elision(gen0, gen1, gen2)
        else:
            ratio = 1.0

        # Estimate tokens
        tokens = self._estimate_tokens(gen0, gen1, gen2, layer)

        # Ensure within budget
        if tokens > self.config.max_tokens:
            gen0, gen1, gen2, tokens = self._prune_to_budget(
                gen0, gen1, gen2, self.config.max_tokens
            )

        return SpiralContext(
            layer=layer,
            gen0=gen0,
            gen1=gen1,
            gen2=gen2,
            tokens_estimate=tokens,
            compression_ratio=ratio,
            metadata={
                "zoom": zoom,
                "query": user_query[:50],
                "pinned_count": len(pinned_paths),
                "layer_name": layer.value
            }
        )

    def _get_layer_for_zoom(self, zoom: float) -> SpiralLayer:
        """Map zoom level to spiral layer (Pi-spiral)."""
        if zoom < self.config.zoom_threshold_low:
            return SpiralLayer.LOW
        elif zoom < self.config.zoom_threshold_mid:
            return SpiralLayer.MID
        else:
            return SpiralLayer.HIGH

    def _build_gen0(self, pinned_paths: List[str], user_query: str) -> Dict[str, Any]:
        """Build Gen0 hot context (pinned + query vector)."""
        # Top pinned files with relevance
        top_pinned = []
        for i, path in enumerate(pinned_paths[:self.config.top_pinned_count]):
            filename = os.path.basename(path)
            # Simulate relevance score (in production: cosine similarity)
            relevance = round(0.9 - (i * 0.1), 2)
            top_pinned.append(f"★{filename} (rel={relevance})")

        gen0 = {
            "type": "pinned_summary",
            "count": len(pinned_paths),
            "top_files": top_pinned,
            "query_key": user_query[:100],  # Truncated query
            "hyperlink": "[→ pins] vetka_get_pinned_files"
        }

        # Cache in MGC
        cache_key = f"gen0_{hash(user_query)}"
        self.mgc_cache.set_sync(cache_key, gen0)  # MARKER_119.1

        return gen0

    def _build_gen1(
        self,
        visible_stats: Dict[str, Any],
        viewport_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build Gen1 mid context (stats + structure)."""
        gen1 = {
            "stats": {
                "visible_count": visible_stats.get("count", 0),
                "zoom": visible_stats.get("zoom", 0),
                "focus": visible_stats.get("focus_path", "/")
            },
            "hyperlink": "[→ viewport] vetka_get_viewport_detail"
        }

        # Add structure summary if viewport data available
        if viewport_data:
            # Extract top-3 folders
            folders = viewport_data.get("visible_folders", [])[:3]
            gen1["structure"] = {
                "top_folders": folders,
                "depth": viewport_data.get("max_depth", 0)
            }

        return gen1

    def _build_gen2(
        self,
        pinned_paths: List[str],
        viewport_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build Gen2 detailed context (for HIGH layer only)."""
        gen2 = {
            "pinned_details": [],
            "relations": []
        }

        # Add file details for pinned
        for path in pinned_paths[:self.config.top_pinned_count]:
            filename = os.path.basename(path)
            gen2["pinned_details"].append({
                "name": filename,
                "path": path,
                "hyperlink": f"[→ file] vetka_read_file?path={path}"
            })

        # Add relations if available
        if viewport_data and "relations" in viewport_data:
            gen2["relations"] = viewport_data["relations"][:5]

        return gen2

    def _apply_elision(
        self,
        gen0: Dict[str, Any],
        gen1: Dict[str, Any],
        gen2: Optional[Dict[str, Any]]
    ) -> Tuple[Dict, Dict, Optional[Dict], float]:
        """Apply ELISION compression to all generations."""
        try:
            from src.memory.elision import compress_context

            original_size = len(json.dumps(gen0)) + len(json.dumps(gen1))
            if gen2:
                original_size += len(json.dumps(gen2))

            # Compress each generation
            gen0_str = compress_context(gen0)
            gen1_str = compress_context(gen1)
            gen2_str = compress_context(gen2) if gen2 else None

            # Parse back (ELISION returns compressed JSON string)
            gen0 = json.loads(gen0_str) if isinstance(gen0_str, str) else gen0_str
            gen1 = json.loads(gen1_str) if isinstance(gen1_str, str) else gen1_str
            if gen2_str:
                gen2 = json.loads(gen2_str) if isinstance(gen2_str, str) else gen2_str

            compressed_size = len(json.dumps(gen0)) + len(json.dumps(gen1))
            if gen2:
                compressed_size += len(json.dumps(gen2))

            ratio = original_size / compressed_size if compressed_size > 0 else 1.0

            return gen0, gen1, gen2, ratio

        except Exception as e:
            logger.warning(f"[Spiral] ELISION compression failed: {e}")
            return gen0, gen1, gen2, 1.0

    def _estimate_tokens(
        self,
        gen0: Dict[str, Any],
        gen1: Dict[str, Any],
        gen2: Optional[Dict[str, Any]],
        layer: SpiralLayer
    ) -> int:
        """Estimate token count (rough: 4 chars ≈ 1 token)."""
        total_chars = len(json.dumps(gen0)) + len(json.dumps(gen1))
        if gen2:
            total_chars += len(json.dumps(gen2))

        # Layer multipliers (LOW uses less)
        multipliers = {
            SpiralLayer.LOW: 0.5,
            SpiralLayer.MID: 0.75,
            SpiralLayer.HIGH: 1.0
        }

        base_tokens = total_chars // 4
        return int(base_tokens * multipliers.get(layer, 1.0))

    def _prune_to_budget(
        self,
        gen0: Dict[str, Any],
        gen1: Dict[str, Any],
        gen2: Optional[Dict[str, Any]],
        max_tokens: int
    ) -> Tuple[Dict, Dict, Optional[Dict], int]:
        """Prune context to fit within token budget."""
        # Priority: Gen0 > Gen1 > Gen2

        # First, drop Gen2 if over budget
        tokens = self._estimate_tokens(gen0, gen1, gen2, SpiralLayer.HIGH)
        if tokens > max_tokens and gen2:
            gen2 = None
            tokens = self._estimate_tokens(gen0, gen1, None, SpiralLayer.MID)

        # Then truncate Gen1
        if tokens > max_tokens:
            gen1 = {"stats": gen1.get("stats", {})}
            tokens = self._estimate_tokens(gen0, gen1, None, SpiralLayer.LOW)

        # Finally truncate Gen0
        if tokens > max_tokens:
            gen0["top_files"] = gen0.get("top_files", [])[:2]
            tokens = self._estimate_tokens(gen0, gen1, None, SpiralLayer.LOW)

        return gen0, gen1, gen2, tokens

    def to_json(self, context: SpiralContext) -> str:
        """Convert SpiralContext to JSON string for prompt injection."""
        output = {
            "spiral_layer": context.layer.value,
            "gen0": context.gen0,
            "gen1": context.gen1,
            "tokens": context.tokens_estimate,
            "compression": f"{context.compression_ratio:.1f}x"
        }

        if context.gen2:
            output["gen2"] = context.gen2

        return json.dumps(output, separators=(',', ':'))


# =============================================================================
# MARKER_108_7_SPIRAL_CONTEXT: Convenience Functions
# =============================================================================

def generate_spiral_context(
    zoom: float,
    user_query: str,
    pinned_paths: List[str],
    visible_stats: Dict[str, Any],
    max_tokens: int = 2000
) -> Dict[str, Any]:
    """
    Convenience function for spiral context generation.

    Returns JSON-ready dict for prompt injection.
    """
    config = SpiralConfig(max_tokens=max_tokens)
    generator = SpiralContextGenerator(config)

    context = generator.generate(
        zoom=zoom,
        user_query=user_query,
        pinned_paths=pinned_paths,
        visible_stats=visible_stats
    )

    return {
        "spiral_layer": context.layer.value,
        "gen0": context.gen0,
        "gen1": context.gen1,
        "gen2": context.gen2,
        "tokens_estimate": context.tokens_estimate,
        "compression_ratio": context.compression_ratio
    }


def get_context_for_zoom(zoom: float) -> str:
    """Get appropriate context layer name for zoom level."""
    if zoom < 0.3:
        return "overview"
    elif zoom < 1.0:
        return "mid-range"
    else:
        return "close-up"
