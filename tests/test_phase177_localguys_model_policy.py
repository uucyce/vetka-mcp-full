from __future__ import annotations


def test_llm_registry_safe_defaults_cover_localguys_models() -> None:
    from src.elisya.llm_model_registry import _SAFE_DEFAULTS

    cases = {
        "qwen3.5:latest": ("ollama", 32768),
        "qwen3:8b": ("ollama", 32768),
        "qwen2.5:7b": ("ollama", 32768),
        "qwen2.5:3b": ("ollama", 16384),
        "deepseek-r1:8b": ("ollama", 32768),
        "phi4-mini:latest": ("ollama", 16384),
        "qwen2.5vl:3b": ("ollama", 16384),
        "embeddinggemma:300m": ("ollama", 8192),
    }

    for model_id, (provider, context_length) in cases.items():
        defaults = _SAFE_DEFAULTS[model_id]
        assert defaults["provider"] == provider
        assert defaults["context_length"] == context_length


def test_reflex_decay_has_exact_profiles_for_localguys_models() -> None:
    from src.services.reflex_decay import get_model_profile

    cases = {
        "qwen3.5:latest": 10,
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
