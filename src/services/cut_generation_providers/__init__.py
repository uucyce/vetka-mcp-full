# @status: active
# @phase: B98
# @task: tb_1774432033_1
# MARKER_B98 — AI generation provider abstraction layer.

from .base_provider import BaseGenerationProvider, GenerationResult
from .runway_provider import RunwayProvider
from .kling_provider import KlingProvider

_REGISTRY = {
    "runway": RunwayProvider,
    "kling": KlingProvider,
}


def get_provider(name: str, **kwargs) -> BaseGenerationProvider:
    """Instantiate a provider by name. Raises KeyError if unknown."""
    cls = _REGISTRY[name]
    return cls(**kwargs)


__all__ = [
    "BaseGenerationProvider",
    "GenerationResult",
    "RunwayProvider",
    "KlingProvider",
    "get_provider",
]
