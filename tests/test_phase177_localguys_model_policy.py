from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_llm_registry_has_exact_safe_defaults_for_localguys_models() -> None:
    from src.elisya.llm_model_registry import LLMModelRegistry

    registry = LLMModelRegistry()
    cases = {
        "qwen3:8b": ("ollama", 32768),
        "qwen2.5:7b": ("ollama", 32768),
        "qwen2.5:3b": ("ollama", 16384),
        "deepseek-r1:8b": ("ollama", 32768),
        "phi4-mini:latest": ("ollama", 16384),
        "qwen2.5vl:3b": ("ollama", 16384),
        "embeddinggemma:300m": ("ollama", 8192),
    }

    for model_id, (provider, context_length) in cases.items():
        profile = await registry.get_profile(model_id)
        assert profile.model_id == model_id
        assert profile.provider == provider
        assert profile.context_length == context_length
        assert profile.source.startswith("hardcoded_defaults")


def test_reflex_decay_has_exact_profiles_for_localguys_models() -> None:
    from src.services.reflex_decay import get_model_profile

    cases = {
        "qwen3:8b": 8,
        "qwen2.5:7b": 8,
        "qwen2.5:3b": 4,
        "deepseek-r1:8b": 6,
        "phi4-mini:latest": 4,
        "qwen2.5vl:3b": 4,
        "embeddinggemma:300m": 1,
    }

    for model_id, max_tools in cases.items():
        profile = get_model_profile(model_id)
        assert profile.model_name == model_id
        assert profile.max_tools == max_tools
