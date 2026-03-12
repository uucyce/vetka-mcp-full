import os
from unittest.mock import MagicMock, patch

from src.api.handlers.unified_search import get_search_capabilities


def _provider_name(provider) -> str:
    return str(getattr(provider, "value", provider)).lower()


def test_web_capabilities_uses_key_manager_when_env_missing(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)

    with patch("src.utils.unified_key_manager.get_key_manager") as mock_get_key_manager:
        km = MagicMock()
        mock_get_key_manager.return_value = km

        def _count(provider):
            return 1 if _provider_name(provider) == "tavily" else 0

        km.get_provider_keys_count.side_effect = _count

        payload = get_search_capabilities("web")

    assert payload["success"] is True
    assert payload["provider_health"]["tavily"]["available"] is True
    assert payload["provider_health"]["serper"]["available"] is False


def test_web_capabilities_env_short_circuit(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-dev-env-test")

    with patch("src.utils.unified_key_manager.get_key_manager", side_effect=RuntimeError("km unavailable")):
        payload = get_search_capabilities("web")

    assert payload["provider_health"]["tavily"]["available"] is True
