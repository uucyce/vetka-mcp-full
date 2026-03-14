"""
VETKA Phase 76.3 + 92 - JARVIS Prompt Enricher with ELISION
Model-agnostic prompt enrichment with user preferences and context compression

@file jarvis_prompt_enricher.py
@status active
@phase 98
@depends json, logging, datetime, dataclasses, engram_user_memory.py, elision.py, hope_enhancer.py
@used_by session_tools.py, orchestrator (via API handlers)

FIX_98.2: Added HOPE (Hierarchical Optimized Processing) integration.
New enrich_with_hope() method provides frequency-based context layers.

Model-Agnostic Architecture (from Grok #2):
- Single template works for DeepSeek/Claude/Qwen/any model
- Adapt format per model (DeepSeek uses [INST], Claude native)
- Include preferences as structured JSON
- 23-43% token savings via selective inclusion

Phase 92 ELISION Integration:
- Automatic context compression before LLM calls
- 40-60% additional token savings on JSON context
- Configurable compression levels (1-4)
- Preserves semantic meaning while reducing tokens

The magic: VETKA = Eternal Memory
- User preferences survive model changes
- Switch models → keep personalization
- DeepSeek/Claude/Qwen → instant "your assistant"
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

from .engram_user_memory import EngramUserMemory, get_engram_user_memory
from .elision import get_elision_compressor, ElisionCompressor, ElisionResult

logger = logging.getLogger(__name__)


@dataclass
class ElisionConfig:
    """Configuration for ELISION compression in enricher"""
    enabled: bool = True
    level: int = 2  # Default: keys + paths compression
    target_ratio: Optional[float] = None  # Optional target compression ratio
    compress_context: bool = True  # Compress user context JSON
    compress_viewport: bool = True  # Compress viewport data
    include_legend: bool = False  # Include expansion legend in output


class JARVISPromptEnricher:
    """
    Model-Agnostic Prompt Enrichment (from Grok #2).

    Works with ANY model:
    - DeepSeek-LLM-7B → [INST]...[/INST]
    - Claude API → Native format
    - Qwen2-7B → Native format
    - Ollama models → Native format
    - Future models → Adaptable

    Adds user preferences to prompt → instant personalization.

    Usage:
        enricher = JARVISPromptEnricher()
        enriched = enricher.enrich_prompt(
            base_prompt="Fix the bug in CAM engine",
            user_id="danila",
            model="deepseek"
        )
    """

    # Model format adapters
    MODEL_FORMATS = {
        "deepseek": ("[INST]", "[/INST]"),
        "deepseek-coder": ("[INST]", "[/INST]"),
        "llama": ("[INST]", "[/INST]"),
        "llama3": (
            "<|begin_of_text|><|start_header_id|>user<|end_header_id|>",
            "<|eot_id|>",
        ),
        "mistral": ("[INST]", "[/INST]"),
        "claude": ("", ""),  # Native format
        "gpt": ("", ""),  # Native format
        "qwen": ("", ""),  # Native format
        "gemma": ("", ""),  # Native format
    }

    # Minimum confidence to include preference
    MIN_CONFIDENCE = 0.5

    def __init__(
        self,
        engram_memory: Optional[EngramUserMemory] = None,
        elision_config: Optional[ElisionConfig] = None
    ):
        """
        Initialize JARVIS Prompt Enricher with ELISION support.

        Args:
            engram_memory: EngramUserMemory instance (uses singleton if None)
            elision_config: ELISION compression configuration
        """
        self.memory = engram_memory or get_engram_user_memory()
        self.elision_config = elision_config or ElisionConfig()
        self._elision_compressor: Optional[ElisionCompressor] = None

        # Stats tracking
        self._compression_stats = {
            "total_compressions": 0,
            "total_tokens_saved": 0,
            "avg_compression_ratio": 0.0
        }

    def enrich_prompt(
        self,
        base_prompt: str,
        user_id: str,
        model: str = "default",
        include_categories: Optional[List[str]] = None,
        # max_tokens removed - unlimited responses
    ) -> str:
        """
        Enrich prompt with user preferences.

        Template works for all models (adapts format only).

        Args:
            base_prompt: Original prompt text
            user_id: User identifier for preferences lookup
            model: Model name for format adaptation
            include_categories: Specific categories to include (all if None)
            max_tokens: Maximum tokens for preferences section

        Returns:
            Enriched prompt with user preferences

        Example:
            enriched = enricher.enrich_prompt(
                "Fix the bug in CAM engine",
                user_id="danila",
                model="deepseek"
            )
        """
        # Get user context
        user_context = self._get_user_context(user_id, include_categories)

        # Skip if no meaningful preferences
        if not user_context or len(user_context) <= 1:  # Only user_id
            return base_prompt

        # Build enriched prompt
        enriched = self._build_enriched_prompt(base_prompt, user_id, user_context)

        # Adapt to model format
        return self._adapt_to_model(model, enriched)

    def _get_user_context(
        self, user_id: str, include_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get relevant user preferences for prompt.

        Token savings: Only include non-default preferences with confidence > threshold.

        Args:
            user_id: User identifier
            include_categories: Specific categories to include

        Returns:
            Dict with user context for prompt
        """
        prefs = {"user_id": user_id}

        # Default categories to check
        categories = include_categories or [
            "communication_style",
            "project_highlights",
            "temporal_patterns",
        ]

        # Communication style (most important for response formatting)
        if "communication_style" in categories:
            formality = self.memory.get_preference(
                user_id, "communication_style", "formality"
            )
            detail_level = self.memory.get_preference(
                user_id, "communication_style", "detail_level"
            )
            prefers_russian = self.memory.get_preference(
                user_id, "communication_style", "prefers_russian"
            )

            # Only include if explicitly set (not default)
            style = {}
            if formality is not None and formality != 0.5:
                style["formality"] = formality
            if detail_level is not None and detail_level != 0.5:
                style["detail_level"] = detail_level
            if prefers_russian is not None:
                style["prefers_russian"] = prefers_russian

            if style:
                prefs["communication_style"] = style

        # Viewport focus (for code-related tasks)
        if "viewport_patterns" in categories:
            focus_areas = self.memory.get_preference(
                user_id, "viewport_patterns", "focus_areas"
            )
            if focus_areas:
                prefs["current_focus"] = focus_areas[:3]  # Top 3

        # Project highlights
        if "project_highlights" in categories:
            current_project = self.memory.get_preference(
                user_id, "project_highlights", "current_project"
            )
            priorities = self.memory.get_preference(
                user_id, "project_highlights", "priorities"
            )

            if current_project and current_project != "vetka":  # Skip default
                prefs["current_project"] = current_project
            if priorities:
                prefs["priorities"] = priorities[:3]

        # Temporal patterns (for context)
        if "temporal_patterns" in categories:
            time_patterns = self.memory.get_preference(
                user_id, "temporal_patterns", "time_of_day"
            )
            if time_patterns:
                # Get current period's typical action
                hour = datetime.now().hour
                if 5 <= hour < 12:
                    period = "morning"
                elif 12 <= hour < 18:
                    period = "afternoon"
                else:
                    period = "evening"

                if period in time_patterns:
                    prefs["typical_activity"] = time_patterns[period]

        return prefs

    def _build_enriched_prompt(
        self, base_prompt: str, user_id: str, user_context: Dict[str, Any]
    ) -> str:
        """
        Build enriched prompt with preferences section.

        Args:
            base_prompt: Original prompt
            user_id: User identifier
            user_context: Extracted preferences

        Returns:
            Enriched prompt string
        """
        # Build system section with preferences
        comm_style = user_context.get("communication_style", {})
        formality = comm_style.get("formality", 0.5)
        detail = comm_style.get("detail_level", 0.5)
        prefers_russian = comm_style.get("prefers_russian", False)

        # Formality description
        if formality < 0.3:
            formality_desc = "casual, friendly"
        elif formality > 0.7:
            formality_desc = "formal, professional"
        else:
            formality_desc = "balanced"

        # Detail description
        if detail < 0.3:
            detail_desc = "concise, brief"
        elif detail > 0.7:
            detail_desc = "detailed, thorough"
        else:
            detail_desc = "moderate detail"

        # Language
        language = "Russian preferred" if prefers_russian else "English"

        # Build context section
        context_parts = []

        if user_context.get("current_focus"):
            context_parts.append(
                f"- Current focus areas: {', '.join(user_context['current_focus'])}"
            )

        if user_context.get("priorities"):
            context_parts.append(
                f"- Priorities: {', '.join(user_context['priorities'])}"
            )

        if user_context.get("typical_activity"):
            context_parts.append(
                f"- Typical activity now: {user_context['typical_activity']}"
            )

        context_section = "\n".join(context_parts) if context_parts else ""

        # Build enriched prompt
        enriched = f"""<system>
You are VETKA - personal AI assistant for {user_id}.

Response Style:
- Tone: {formality_desc}
- Detail: {detail_desc}
- Language: {language}
"""

        if context_section:
            enriched += f"""
User Context:
{context_section}
"""

        enriched += f"""
Adapt your response to match user preferences.
</system>

{base_prompt}
"""

        return enriched

    def _adapt_to_model(self, model: str, enriched: str) -> str:
        """
        Adapt prompt format per model.

        Args:
            model: Model name/identifier
            enriched: Enriched prompt

        Returns:
            Model-formatted prompt
        """
        model_lower = model.lower()

        # Find matching format
        for model_prefix, (start_tag, end_tag) in self.MODEL_FORMATS.items():
            if model_prefix in model_lower:
                if start_tag or end_tag:
                    return f"{start_tag}\n{enriched}\n{end_tag}"
                return enriched

        # Default: no wrapping
        return enriched

    def enrich_for_agent(
        self, base_prompt: str, user_id: str, agent_type: str, model: str = "default"
    ) -> str:
        """
        Enrich prompt for specific VETKA agent.

        Different agents need different preference subsets:
        - Dev: focus areas, technical depth
        - PM: communication style, priorities
        - QA: detail level
        - Architect: project highlights

        Args:
            base_prompt: Original prompt
            user_id: User identifier
            agent_type: Agent type (Dev, PM, QA, Architect)
            model: Model name

        Returns:
            Agent-specific enriched prompt
        """
        # Map agent type to relevant categories
        agent_categories = {
            "Dev": ["viewport_patterns", "project_highlights"],
            "PM": ["communication_style", "project_highlights", "temporal_patterns"],
            "QA": ["communication_style"],
            "Architect": ["project_highlights", "communication_style"],
            "Hostess": ["communication_style", "temporal_patterns"],
        }

        categories = agent_categories.get(agent_type, ["communication_style"])

        return self.enrich_prompt(
            base_prompt=base_prompt,
            user_id=user_id,
            model=model,
            include_categories=categories,
        )

    def get_token_estimate(self, user_id: str) -> Dict[str, Any]:
        """
        Estimate tokens added by preferences.

        Useful for budget management.

        Returns:
            Dict with token estimates per category
        """
        user_context = self._get_user_context(user_id)

        # Rough token estimate (1 token ≈ 4 chars)
        json_str = json.dumps(user_context, ensure_ascii=False)
        estimated_tokens = len(json_str) // 4

        return {
            "user_id": user_id,
            "categories_included": list(user_context.keys()),
            "estimated_tokens": estimated_tokens,
            "context_preview": json_str[:200],
        }

    # ============ PHASE 92: ELISION INTEGRATION ============

    @property
    def elision_compressor(self) -> ElisionCompressor:
        """Lazy-load ELISION compressor"""
        if self._elision_compressor is None:
            self._elision_compressor = get_elision_compressor()
        return self._elision_compressor

    def compress_context(
        self,
        context: Dict[str, Any],
        level: Optional[int] = None
    ) -> str:
        """
        Compress context using ELISION.

        Args:
            context: Dictionary to compress
            level: Override compression level (uses config if None)

        Returns:
            Compressed JSON string
        """
        if not self.elision_config.enabled:
            return json.dumps(context, ensure_ascii=False)

        compression_level = level or self.elision_config.level
        result = self.elision_compressor.compress(
            context,
            level=compression_level,
            target_ratio=self.elision_config.target_ratio
        )

        # Track stats
        self._compression_stats["total_compressions"] += 1
        self._compression_stats["total_tokens_saved"] += result.tokens_saved_estimate
        n = self._compression_stats["total_compressions"]
        old_avg = self._compression_stats["avg_compression_ratio"]
        self._compression_stats["avg_compression_ratio"] = (
            (old_avg * (n - 1) + result.compression_ratio) / n
        )

        logger.debug(
            f"[ELISION] Compressed {result.original_length} -> {result.compressed_length} "
            f"({result.compression_ratio:.2f}x, ~{result.tokens_saved_estimate} tokens saved)"
        )

        return result.compressed

    def enrich_prompt_with_viewport(
        self,
        base_prompt: str,
        user_id: str,
        viewport_context: Optional[Dict[str, Any]] = None,
        pinned_files: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[Dict[str, Any]] = None,
        semantic_neighbors: Optional[List[Dict[str, Any]]] = None,
        model: str = "default",
        compress: bool = True
    ) -> str:
        """
        Enrich prompt with 3D viewport context and ELISION compression.

        This is the main entry point for VETKA 3D integration.
        Combines user preferences with spatial context, then compresses.

        Args:
            base_prompt: Original prompt
            user_id: User identifier
            viewport_context: 3D viewport data {viewport_nodes, zoom_level}
            pinned_files: List of pinned files
            dependencies: File dependency graph
            semantic_neighbors: Semantic search results
            model: Model name for format adaptation
            compress: Whether to use ELISION compression

        Returns:
            Enriched and optionally compressed prompt
        """
        # Get user preferences first
        user_context = self._get_user_context(user_id)

        # Build VETKA context section
        vetka_context = {}

        if viewport_context and self.elision_config.compress_viewport:
            vetka_context["viewport"] = viewport_context

        if pinned_files:
            vetka_context["pinned"] = pinned_files[:20]  # Limit

        if dependencies:
            vetka_context["deps"] = {
                k: v for k, v in list(dependencies.items())[:15]
            }

        if semantic_neighbors:
            vetka_context["semantic"] = semantic_neighbors[:10]

        # Compress VETKA context if enabled
        if compress and self.elision_config.enabled and vetka_context:
            compressed_context = self.compress_context(vetka_context)
            context_section = f"\n<vetka-context compressed=\"elision-L{self.elision_config.level}\">\n{compressed_context}\n</vetka-context>\n"
        elif vetka_context:
            context_section = f"\n<vetka-context>\n{json.dumps(vetka_context, indent=2)}\n</vetka-context>\n"
        else:
            context_section = ""

        # Build enriched prompt
        enriched = self._build_enriched_prompt(base_prompt, user_id, user_context)

        # Insert VETKA context before the base prompt
        if context_section:
            # Find where base_prompt starts in enriched
            if "</system>" in enriched:
                enriched = enriched.replace(
                    "</system>",
                    f"</system>\n{context_section}"
                )
            else:
                enriched = f"{context_section}\n{enriched}"

        # Adapt to model format
        return self._adapt_to_model(model, enriched)

    def get_compression_stats(self) -> Dict[str, Any]:
        """
        Get ELISION compression statistics.

        Returns:
            Dict with compression stats
        """
        return {
            **self._compression_stats,
            "elision_enabled": self.elision_config.enabled,
            "compression_level": self.elision_config.level,
        }

    # ============ FIX_98.2: HOPE INTEGRATION ============

    def enrich_with_hope(
        self,
        base_prompt: str,
        user_id: str,
        content_for_analysis: str,
        model: str = "default",
        hope_layers: Optional[List[str]] = None,
        compress: bool = True
    ) -> str:
        """
        Enrich prompt with HOPE (Hierarchical Optimized Processing) context.

        HOPE provides frequency-based context layers for matryoshka-style
        context enrichment:
        - LOW: Global overview (~200 words) - always included
        - MID: Detailed context (~400 words) - included if space permits
        - HIGH: Specific details (~600 words) - used for deep analysis

        Args:
            base_prompt: Original prompt
            user_id: User identifier for preferences
            content_for_analysis: Content to analyze with HOPE
            model: Model name for format adaptation
            hope_layers: Which layers to include ['low', 'mid', 'high'] (default: ['low', 'mid'])
            compress: Whether to use ELISION compression on HOPE context

        Returns:
            Enriched prompt with HOPE context layers

        Example:
            enriched = enricher.enrich_with_hope(
                "Analyze this code",
                user_id="danila",
                content_for_analysis=code_content,
                model="claude"
            )
        """
        from src.agents.hope_enhancer import HOPEEnhancer, FrequencyLayer

        # Default layers
        if hope_layers is None:
            hope_layers = ['low', 'mid']

        # Get HOPE analysis
        try:
            enhancer = HOPEEnhancer(use_api_fallback=False)  # Local analysis only

            # Map string layers to enum
            layer_map = {
                'low': FrequencyLayer.LOW,
                'mid': FrequencyLayer.MID,
                'high': FrequencyLayer.HIGH
            }
            enum_layers = [layer_map[l] for l in hope_layers if l in layer_map]

            # Analyze content
            hope_result = enhancer.analyze(
                content_for_analysis,
                layers=enum_layers,
                complexity="MEDIUM"
            )

            # Build HOPE context section
            hope_context = {}
            if 'low' in hope_layers and 'low' in hope_result:
                hope_context['overview'] = hope_result['low']
            if 'mid' in hope_layers and 'mid' in hope_result:
                hope_context['detailed'] = hope_result['mid']
            if 'high' in hope_layers and 'high' in hope_result:
                hope_context['specific'] = hope_result['high']

            if not hope_context:
                # Fallback if analysis failed
                logger.warning("[HOPE] Analysis returned no results, using raw content")
                return self.enrich_prompt(base_prompt, user_id, model)

            # Compress if enabled
            if compress and self.elision_config.enabled:
                hope_section = self.compress_context(hope_context)
                hope_tag = f'\n<hope-context compressed="elision-L{self.elision_config.level}" layers="{",".join(hope_layers)}">\n{hope_section}\n</hope-context>\n'
            else:
                hope_section = json.dumps(hope_context, ensure_ascii=False, indent=2)
                hope_tag = f'\n<hope-context layers="{",".join(hope_layers)}">\n{hope_section}\n</hope-context>\n'

            # Get user preferences
            user_context = self._get_user_context(user_id)

            # Build enriched prompt
            enriched = self._build_enriched_prompt(base_prompt, user_id, user_context)

            # Insert HOPE context
            if "</system>" in enriched:
                enriched = enriched.replace(
                    "</system>",
                    f"</system>\n{hope_tag}"
                )
            else:
                enriched = f"{hope_tag}\n{enriched}"

            logger.info(
                f"[HOPE] Enriched prompt with {len(hope_layers)} layers "
                f"({len(hope_section)} chars)"
            )

            return self._adapt_to_model(model, enriched)

        except ImportError as e:
            logger.warning(f"[HOPE] HOPEEnhancer not available: {e}")
            return self.enrich_prompt(base_prompt, user_id, model)
        except Exception as e:
            logger.error(f"[HOPE] Analysis failed: {e}")
            return self.enrich_prompt(base_prompt, user_id, model)


# ============ FACTORY FUNCTION ============

_enricher_instance: Optional[JARVISPromptEnricher] = None


def get_jarvis_enricher(
    engram_memory: Optional[EngramUserMemory] = None,
    elision_config: Optional[ElisionConfig] = None,
) -> JARVISPromptEnricher:
    """
    Factory function - returns singleton JARVISPromptEnricher.

    Args:
        engram_memory: EngramUserMemory instance
        elision_config: ELISION compression configuration

    Returns:
        JARVISPromptEnricher singleton instance
    """
    global _enricher_instance

    if _enricher_instance is None:
        _enricher_instance = JARVISPromptEnricher(engram_memory, elision_config)

    return _enricher_instance


def configure_elision(
    enabled: bool = True,
    level: int = 2,
    target_ratio: Optional[float] = None
) -> ElisionConfig:
    """
    Create ELISION configuration.

    Args:
        enabled: Enable/disable compression
        level: Compression level (1-4)
        target_ratio: Optional target compression ratio

    Returns:
        ElisionConfig instance
    """
    return ElisionConfig(
        enabled=enabled,
        level=level,
        target_ratio=target_ratio
    )


# ============ CONVENIENCE FUNCTIONS ============


def enrich_prompt_for_user(prompt: str, user_id: str, model: str = "default") -> str:
    """
    Quick function to enrich prompt with user preferences.

    Args:
        prompt: Base prompt
        user_id: User identifier
        model: Model name

    Returns:
        Enriched prompt
    """
    enricher = get_jarvis_enricher()
    return enricher.enrich_prompt(prompt, user_id, model)


def enrich_with_viewport(
    prompt: str,
    user_id: str,
    viewport_context: Optional[Dict[str, Any]] = None,
    pinned_files: Optional[List[Dict[str, Any]]] = None,
    model: str = "default",
    compress: bool = True
) -> str:
    """
    Quick function to enrich prompt with viewport context and ELISION.

    Args:
        prompt: Base prompt
        user_id: User identifier
        viewport_context: 3D viewport data
        pinned_files: Pinned files list
        model: Model name
        compress: Use ELISION compression

    Returns:
        Enriched and compressed prompt
    """
    enricher = get_jarvis_enricher()
    return enricher.enrich_prompt_with_viewport(
        base_prompt=prompt,
        user_id=user_id,
        viewport_context=viewport_context,
        pinned_files=pinned_files,
        model=model,
        compress=compress
    )


def enrich_with_hope(
    prompt: str,
    user_id: str,
    content_for_analysis: str,
    model: str = "default",
    hope_layers: Optional[List[str]] = None,
    compress: bool = True
) -> str:
    """
    Quick function to enrich prompt with HOPE context layers.

    FIX_98.2: HOPE (Hierarchical Optimized Processing) integration.

    Args:
        prompt: Base prompt
        user_id: User identifier
        content_for_analysis: Content to analyze with HOPE
        model: Model name
        hope_layers: Which layers to include ['low', 'mid', 'high']
        compress: Use ELISION compression

    Returns:
        Enriched prompt with HOPE context

    Example:
        enriched = enrich_with_hope(
            "Explain this code",
            user_id="danila",
            content_for_analysis=file_content
        )
    """
    enricher = get_jarvis_enricher()
    return enricher.enrich_with_hope(
        base_prompt=prompt,
        user_id=user_id,
        content_for_analysis=content_for_analysis,
        model=model,
        hope_layers=hope_layers,
        compress=compress
    )
