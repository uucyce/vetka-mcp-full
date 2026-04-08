#!/usr/bin/env python3
"""
VETKA Phase 8.0 - HOPEEnhancer
Hierarchical Optimized Processing for Enhanced understanding

HOPE = Hierarchical frequency decomposition:
- Low frequency: Global structure, main themes
- Mid frequency: Details, relationships
- High frequency: Fine-grained specifics, edge cases

IMPLEMENTATION NOTE:
HOPE-VL model is not available in Ollama, but the HOPE pattern
(hierarchical frequency decomposition) works with any capable model.
We use Llama3.1-8B as the primary model for HOPE pattern implementation.

REAL MODELS:
- Primary: llama3.1:8b (Ollama) - HOPE pattern implementation
- Fallback: deepseek-llm:7b (Ollama) - reasoning fallback
- API: claude-3.5-sonnet / gemini-2.0 via OpenRouter

@status: active
@phase: 99
@depends: ollama, logging, src.memory.stm_buffer
@used_by: orchestrator, embeddings_projector, langgraph_nodes
"""

import logging
import ollama
from typing import Dict, Any, Optional, List
from enum import Enum, auto

logger = logging.getLogger(__name__)


class FrequencyLayer(Enum):
    """HOPE frequency layers"""
    LOW = auto()     # Global overview
    MID = auto()     # Detailed analysis
    HIGH = auto()    # Fine-grained specifics


class HOPEEnhancer:
    """
    Hierarchical analysis with frequency-based decomposition.

    Phase 8.0: Processes content at multiple levels of abstraction:
    - LOW: High-level summary, main concepts (matryoshka outer)
    - MID: Detailed analysis, relationships (matryoshka middle)
    - HIGH: Specifics, edge cases, implementation details (matryoshka inner)

    Includes API fallback when local models fail.
    """

    LAYER_PROMPTS = {
        FrequencyLayer.LOW: """GLOBAL ANALYSIS (Low Frequency - Big Picture)
Analyze the following content at a HIGH LEVEL:
- What are the main themes/concepts?
- What is the overall structure?
- Key takeaways (max 3-5 points)

Content:
{content}

Provide a concise GLOBAL overview (max 200 words):""",

        FrequencyLayer.MID: """DETAILED ANALYSIS (Mid Frequency - Relationships)
Analyze the following content in DETAIL:
- How do different parts relate to each other?
- What are the important connections?
- What patterns emerge?

Content:
{content}

Previous global context:
{low_context}

Provide DETAILED analysis with relationships (max 400 words):""",

        FrequencyLayer.HIGH: """FINE-GRAINED ANALYSIS (High Frequency - Specifics)
Analyze the following content at the FINEST level:
- What are the specific implementation details?
- What edge cases exist?
- What nuances are important?

Content:
{content}

Previous context:
Global: {low_context}
Detailed: {mid_context}

Provide SPECIFIC, fine-grained analysis (max 600 words):""",
    }

    def __init__(
        self,
        local_model: str = "llama3.1:8b",
        fast_model: str = "deepseek-llm:7b",
        api_client: Optional[Any] = None,
        api_model: str = "anthropic/claude-3.5-sonnet",  # via OpenRouter
        use_api_fallback: bool = True,
    ):
        """
        Initialize HOPEEnhancer.

        Args:
            local_model: Primary local model for HOPE pattern (default: llama3.1:8b)
            fast_model: Faster local model for fallback (default: deepseek-llm:7b)
            api_client: Optional API client (anthropic/openai)
            api_model: API model for fallback (via OpenRouter)
            use_api_fallback: Whether to fall back to API on local failure
        """
        self.local_model = local_model
        self.fast_model = fast_model
        self.api_client = api_client
        self.api_model = api_model
        self.use_api_fallback = use_api_fallback
        self._analysis_cache = {}

    def analyze(
        self,
        content: str,
        layers: Optional[List[FrequencyLayer]] = None,
        complexity: str = "MEDIUM",
        cache_key: Optional[str] = None,
        stm_context: Optional[List[Any]] = None,  # FIX_99.1: STM Buffer integration
    ) -> Dict[str, Any]:
        """
        Perform hierarchical analysis on content.

        Args:
            content: Content to analyze
            layers: Which layers to analyze (default: all)
            complexity: MICRO/SMALL/MEDIUM/LARGE/EPIC
            cache_key: Optional key for caching results
            stm_context: FIX_99.1 - Optional STM entries for quick context enrichment

        Returns:
            {
                'low': 'Global overview...',
                'mid': 'Detailed analysis...',
                'high': 'Fine-grained specifics...',
                'combined': 'Full hierarchical analysis...',
                'metadata': {...}
            }
        """
        # FIX_99.1: Prepend STM context if available
        if stm_context:
            try:
                recent_context = "\n".join(
                    e.content if hasattr(e, 'content') else str(e)
                    for e in stm_context[:3]  # Top 3 by weight
                )
                if recent_context:
                    content = f"Recent context:\n{recent_context}\n\n{content}"
                    logger.debug(f"HOPE enriched with STM context ({len(stm_context)} entries)")
            except Exception as e:
                logger.warning(f"HOPE STM context enrichment failed: {e}")

        # Check cache
        if cache_key and cache_key in self._analysis_cache:
            logger.debug(f"HOPE cache hit: {cache_key}")
            return self._analysis_cache[cache_key]

        # Default to all layers for MEDIUM+ complexity
        if layers is None:
            if complexity in ['MICRO', 'SMALL']:
                layers = [FrequencyLayer.LOW]
            elif complexity == 'MEDIUM':
                layers = [FrequencyLayer.LOW, FrequencyLayer.MID]
            else:
                layers = list(FrequencyLayer)

        result = {
            'low': None,
            'mid': None,
            'high': None,
            'combined': '',
            'metadata': {
                'layers_analyzed': [l.name for l in layers],
                'complexity': complexity,
                'model_used': None,
                'fallback_used': False,
            }
        }

        # Process each layer
        low_context = ""
        mid_context = ""

        for layer in layers:
            prompt = self.LAYER_PROMPTS[layer].format(
                content=content[:4000],  # Truncate for context window
                low_context=low_context,
                mid_context=mid_context,
            )

            # Try local model first
            response = self._call_local(prompt)

            if response is None and self.use_api_fallback:
                # Fallback to API
                response = self._call_api(prompt)
                result['metadata']['fallback_used'] = True

            if response:
                if layer == FrequencyLayer.LOW:
                    result['low'] = response
                    low_context = response
                elif layer == FrequencyLayer.MID:
                    result['mid'] = response
                    mid_context = response
                elif layer == FrequencyLayer.HIGH:
                    result['high'] = response

        # Combine results
        result['combined'] = self._combine_layers(result)

        # Cache if key provided
        if cache_key:
            self._analysis_cache[cache_key] = result

        return result

    def _call_local(self, prompt: str) -> Optional[str]:
        """Call local Ollama model."""
        try:
            response = ollama.generate(
                model=self.local_model,
                prompt=prompt,
                stream=False,
                options={
                    "temperature": 0.3,
                    "num_predict": 1000,
                }
            )
            result = response.get("response", "")
            if result:
                logger.debug(f"HOPE local model success: {self.local_model}")
                return result
            return None
        except Exception as e:
            logger.warning(f"HOPE local model failed: {e}")
            return None

    def _call_api(self, prompt: str) -> Optional[str]:
        """Call API model as fallback."""
        if not self.api_client:
            logger.warning("HOPE: No API client configured for fallback")
            return None

        try:
            # Try Anthropic client
            if hasattr(self.api_client, 'messages'):
                response = self.api_client.messages.create(
                    model=self.api_model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

            # Try OpenAI-compatible client
            if hasattr(self.api_client, 'chat'):
                response = self.api_client.chat.completions.create(
                    model=self.api_model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content

            logger.warning("HOPE: Unknown API client type")
            return None

        except Exception as e:
            logger.error(f"HOPE API fallback failed: {e}")
            return None

    def _combine_layers(self, result: Dict[str, Any]) -> str:
        """Combine layer results into unified output."""
        parts = []

        if result.get('low'):
            parts.append("## Global Overview\n" + result['low'])

        if result.get('mid'):
            parts.append("\n## Detailed Analysis\n" + result['mid'])

        if result.get('high'):
            parts.append("\n## Specifics & Details\n" + result['high'])

        return "\n".join(parts) if parts else "No analysis available"

    def quick_analyze(self, content: str) -> str:
        """Quick single-layer analysis (LOW only)."""
        result = self.analyze(content, layers=[FrequencyLayer.LOW], complexity="SMALL")
        return result.get('low', 'Analysis unavailable')

    def deep_analyze(self, content: str) -> Dict[str, Any]:
        """Deep three-layer analysis."""
        return self.analyze(content, layers=list(FrequencyLayer), complexity="EPIC")

    def get_embedding_context(self, content: str) -> Dict[str, str]:
        """
        Get context for matryoshka embeddings.

        Returns contexts at different granularities for multi-level embedding.
        """
        result = self.analyze(content, layers=list(FrequencyLayer), complexity="MEDIUM")

        return {
            'full': content,
            'summary': result.get('low', content[:500]),
            'detailed': result.get('mid', content[:1000]),
            'specific': result.get('high', content),
        }

    def clear_cache(self):
        """Clear analysis cache."""
        self._analysis_cache.clear()
        logger.info("HOPE cache cleared")


def hope_enhancer_factory(
    api_client: Optional[Any] = None,
    use_api_fallback: bool = True
) -> HOPEEnhancer:
    """Factory for creating HOPEEnhancer instance."""
    return HOPEEnhancer(
        api_client=api_client,
        use_api_fallback=use_api_fallback
    )


# Convenience functions
def quick_hope_analysis(content: str) -> str:
    """Quick HOPE analysis (single layer)."""
    enhancer = HOPEEnhancer(use_api_fallback=False)
    return enhancer.quick_analyze(content)


def full_hope_analysis(content: str) -> Dict[str, Any]:
    """Full HOPE analysis (all layers)."""
    enhancer = HOPEEnhancer(use_api_fallback=True)
    return enhancer.deep_analyze(content)
