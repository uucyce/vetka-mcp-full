from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_provider_registry_applies_adaptive_budget_in_call_paths():
    src = _read("src/elisya/provider_registry.py")
    assert 'kwargs["max_tokens"] = await _resolve_adaptive_max_tokens(' in src
    assert src.count('kwargs["max_tokens"] = await _resolve_adaptive_max_tokens(') >= 2


def test_stream_openrouter_uses_dynamic_max_tokens_not_hardcoded():
    src = _read("src/elisya/provider_registry.py")
    assert '"max_tokens": int(kwargs.get("max_tokens", ADAPTIVE_OUTPUT_DEFAULT))' in src
    assert "2048" not in src.split("async def _stream_openrouter", 1)[1][:900]


def test_message_utils_mgc_sync_path_no_async_get_call():
    src = _read("src/api/handlers/message_utils.py")
    assert "gen0 = getattr(cache, \"gen0\", {}) or {}" in src
    assert "cache.get(path)" not in src.split("def _batch_get_mgc_scores", 1)[1].split("def _rank_pinned_files", 1)[0]

