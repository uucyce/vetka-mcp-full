from __future__ import annotations

import pytest

from src.services.local_qwen_model_selector import choose_best_local_qwen, get_best_local_qwen_model


def test_choose_best_local_qwen_prefers_newest_strongest_family() -> None:
    selection = choose_best_local_qwen(
        [
            {
                "name": "qwen2.5:7b",
                "details": {"family": "qwen2", "parameter_size": "7.6B", "quantization_level": "Q4_K_M"},
            },
            {
                "name": "qwen3:8b",
                "details": {"family": "qwen3", "parameter_size": "8.2B", "quantization_level": "Q4_K_M"},
            },
            {
                "name": "qwen3.5:latest",
                "details": {"family": "qwen35", "parameter_size": "9.7B", "quantization_level": "Q4_K_M"},
            },
            {
                "name": "qwen2.5vl:3b",
                "details": {"family": "qwen25vl", "parameter_size": "3.8B", "quantization_level": "Q4_K_M"},
            },
        ]
    )

    assert selection["best_model"] == "qwen3.5:latest"
    assert selection["count"] == 4
    assert selection["candidates"][0]["score"] > selection["candidates"][1]["score"]


def test_choose_best_local_qwen_ignores_non_text_qwen_variants() -> None:
    selection = choose_best_local_qwen(
        [
            {"name": "embeddinggemma:300m", "details": {"family": "gemma3", "parameter_size": "307.58M"}},
            {"name": "qwen3-tts:latest", "details": {"family": "qwen3", "parameter_size": "4.0B"}},
        ]
    )

    assert selection["best_model"] == ""
    assert selection["count"] == 0


def test_get_best_local_qwen_model_reads_live_ollama_tags_when_available() -> None:
    try:
        selection = get_best_local_qwen_model()
    except Exception as exc:  # pragma: no cover - local environment dependent
        pytest.skip(f"Ollama tags unavailable: {exc}")

    if selection["count"] == 0:
        pytest.skip("No local Qwen models installed")

    candidate_names = [row["name"] for row in selection["candidates"]]
    assert selection["best_model"] in candidate_names
    assert "qwen" in selection["best_model"].lower()
