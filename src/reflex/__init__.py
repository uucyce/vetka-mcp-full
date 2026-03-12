"""
REFLEX — Reactive Tool Recommendation Engine

Intelligent tool scoring & recommendation for LLM agent pipelines.
Learns from outcomes, adapts to context, recommends the best tools.

MIT License — Copyright (c) 2026 Danila Gulin / VETKA Project

Quick start:
    from reflex import ReflexScorer, ReflexRegistry, ReflexFeedback

    registry = ReflexRegistry()
    scorer = ReflexScorer(registry)
    feedback = ReflexFeedback()
"""

__version__ = "0.1.0"
__author__ = "Danila Gulin"
__license__ = "MIT"

# Re-export core classes for convenient imports
try:
    from .scorer import ReflexScorer, ReflexContext, REFLEX_ENABLED
    from .registry import ReflexRegistry
    from .feedback import ReflexFeedback, get_reflex_feedback
except ImportError:
    # Standalone usage may have different import paths
    pass

__all__ = [
    "ReflexScorer",
    "ReflexContext",
    "ReflexRegistry",
    "ReflexFeedback",
    "get_reflex_feedback",
    "REFLEX_ENABLED",
    "__version__",
]
