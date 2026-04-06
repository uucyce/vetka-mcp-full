"""
src/services/model_policy.py
MARKER_177.MCC.POLICY.UNIFIED

Единая система политик для всех localguys-моделей.
Мержит:
- reflex_decay (fc_reliability, max_tools, prefer_simple)
- LLMModelRegistry (context_length, output_tps, provider)
- производные: tool_budget_class, role_fit, context_class, latency_class

Теперь везде (mcc_routes, reflex, MATRIX) используется один источник правды.

@status: in_progress
@phase: 177
@depends: reflex_decay, llm_model_registry
@used_by: mcc_routes, agent_pipeline
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular dependencies
_reflex_profile_cache: Dict[str, Any] = {}
_llm_registry_cache: Optional[Any] = None


def _get_reflex_profile(model_id: str) -> Any:
    """Get reflex_decay profile for model."""
    if model_id in _reflex_profile_cache:
        return _reflex_profile_cache[model_id]

    try:
        from src.services.reflex_decay import get_model_profile

        profile = get_model_profile(model_id)
        _reflex_profile_cache[model_id] = profile
        return profile
    except Exception as e:
        logger.warning(f"Failed to get reflex profile for {model_id}: {e}")
        return None


def _get_llm_registry() -> Any:
    """Get LLMModelRegistry singleton."""
    global _llm_registry_cache
    if _llm_registry_cache is not None:
        return _llm_registry_cache

    try:
        from src.elisya.llm_model_registry import get_llm_registry

        _llm_registry_cache = get_llm_registry()
        return _llm_registry_cache
    except Exception as e:
        logger.warning(f"Failed to get LLM registry: {e}")
        return None


@dataclass
class ModelPolicy:
    """Unified model policy combining all sources."""

    model_id: str

    # Из reflex_decay (или fallback)
    fc_reliability: float = 0.80
    max_tools: int = 8
    prefer_simple: bool = True

    # Из LLMModelRegistry (или fallback)
    context_length: int = 8192
    output_tps: float = 0.0
    input_tps: float = 0.0
    ttft_ms: float = 0.0
    provider: str = "ollama"

    # Производные (вычисляются в __post_init__)
    tool_budget_class: str = field(init=False)
    role_fit: List[str] = field(init=False, default_factory=list)
    context_class: str = field(init=False)
    latency_class: str = field(init=False)

    def __post_init__(self):
        self._load_reflex_data()
        self._load_llm_data()
        self._derive_classes()

    def _load_reflex_data(self):
        """Загружаем данные из reflex_decay."""
        profile = _get_reflex_profile(self.model_id)
        if profile:
            self.fc_reliability = getattr(
                profile, "fc_reliability", self.fc_reliability
            )
            self.max_tools = getattr(profile, "max_tools", self.max_tools)
            self.prefer_simple = getattr(profile, "prefer_simple", self.prefer_simple)

    def _load_llm_data(self):
        """Загружаем данные из LLMModelRegistry."""
        registry = _get_llm_registry()
        if registry is None:
            return

        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in async context - create a task
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, registry.get_profile(self.model_id)
                    )
                    profile = future.result(timeout=5)
            else:
                profile = asyncio.run(registry.get_profile(self.model_id))

            if profile:
                self.context_length = getattr(
                    profile, "context_length", self.context_length
                )
                self.output_tps = getattr(
                    profile, "output_tokens_per_second", self.output_tps
                )
                self.input_tps = getattr(
                    profile, "input_tokens_per_second", self.input_tps
                )
                self.ttft_ms = getattr(profile, "ttft_ms", self.ttft_ms)
                self.provider = getattr(profile, "provider", self.provider)
        except Exception as e:
            logger.debug(f"Could not load LLM profile for {self.model_id}: {e}")

    def _derive_classes(self):
        """Вычисляем производные классы."""
        self.tool_budget_class = self._derive_budget_class()
        self.role_fit = self._derive_role_fit()
        self.context_class = self._derive_context_class()
        self.latency_class = self._derive_latency_class()

    def _derive_budget_class(self) -> str:
        """Авто-определение tool_budget на основе fc_reliability."""
        if self.fc_reliability >= 0.85:
            return "medium"
        if self.fc_reliability >= 0.75:
            return "low-medium"
        return "low"

    def _derive_role_fit(self) -> List[str]:
        """Определение роли на основе model_id."""
        mapping = {
            "qwen3:8b": ["coder", "architect", "researcher"],
            "qwen2.5:7b": ["coder", "architect", "researcher"],
            "qwen2.5:3b": ["coder", "support", "researcher"],
            "deepseek-r1:8b": ["verifier", "architect"],
            "phi4-mini:latest": ["router", "verifier", "scout", "approval"],
            "qwen2.5vl:3b": ["scout"],
            "embeddinggemma:300m": ["retrieval"],
            "gemma3:4b": ["support", "general"],
            "gemma3:12b": ["generalist", "coder"],
            "mistral-nemo": ["general", "docs", "research"],
            "qwen3.5:latest": ["coder", "architect", "researcher"],
        }
        return mapping.get(self.model_id.lower(), ["general"])

    def _derive_context_class(self) -> str:
        """Определение context_class на основе context_length."""
        if self.context_length <= 8192:
            return "small"
        if self.context_length <= 32768:
            return "medium"
        return "large"

    def _derive_latency_class(self) -> str:
        """Определение latency_class на основе output_tps."""
        if self.output_tps > 80 or self.model_id in ("phi4-mini:latest", "qwen2.5:3b"):
            return "fast"
        if self.output_tps > 40:
            return "balanced"
        return "slow"

    def to_dict(self) -> Dict[str, Any]:
        """Экспорт в словарь для API."""
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "fc_reliability": round(self.fc_reliability, 3),
            "max_tools": self.max_tools,
            "prefer_simple": self.prefer_simple,
            "tool_budget_class": self.tool_budget_class,
            "role_fit": self.role_fit,
            "context_class": self.context_class,
            "latency_class": self.latency_class,
            "context_length": self.context_length,
            "output_tps": round(self.output_tps, 1),
            "input_tps": round(self.input_tps, 1),
            "ttft_ms": round(self.ttft_ms, 1),
        }


# Каталог известных localguys моделей
LOCALGUYS_CATALOG = [
    "qwen3:8b",
    "qwen2.5:7b",
    "qwen2.5:3b",
    "deepseek-r1:8b",
    "phi4-mini:latest",
    "qwen2.5vl:3b",
    "embeddinggemma:300m",
    "qwen3.5:latest",
    "gemma3:4b",
    "gemma3:12b",
    "mistral-nemo",
]


def get_unified_policy(model_id: str) -> ModelPolicy:
    """Единая точка входа для получения политики модели."""
    return ModelPolicy(model_id)


def get_all_policies() -> List[Dict[str, Any]]:
    """Получить все политики для каталога моделей."""
    return [get_unified_policy(m).to_dict() for m in LOCALGUYS_CATALOG]
