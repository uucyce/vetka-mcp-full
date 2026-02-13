import asyncio
from pathlib import Path

from starlette.requests import Request

from src.api.routes import connectors_routes as cr
from src.services.connectors_state_service import ConnectorsStateService


class _FakeStore:
    def __init__(self):
        self.saved = {}

    def has_token(self, provider_id: str) -> bool:
        return provider_id in self.saved

    def encryption_enabled(self) -> bool:
        return True

    def set_oauth_tokens(self, provider_id: str, access_token: str, refresh_token=None, expires_in=None, scope=None, token_type="oauth_access"):
        self.saved[provider_id] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "scope": scope,
            "token_type": token_type,
        }

    def set_token(self, provider_id: str, token: str, token_type: str = "oauth_access"):
        self.saved[provider_id] = {"access_token": token, "token_type": token_type}

    def clear_token(self, provider_id: str):
        self.saved.pop(provider_id, None)


class _FakeStateService:
    def connect(self, provider_id: str, account_label):
        return {
            "id": provider_id,
            "source": "cloud",
            "display_name": provider_id,
            "connected": True,
            "account_label": account_label or provider_id,
            "capabilities": {"read": True, "write": False, "offline_access": True, "webhooks": False},
            "status": "connected",
        }


def _request(path: str = "/api/connectors/google_drive/oauth/start") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "headers": [],
        "server": ("testserver", 80),
        "client": ("testclient", 1234),
        "query_string": b"",
    }
    return Request(scope)


def test_state_service_loads_registry_map_format(tmp_path: Path):
    registry_file = tmp_path / "registry.json"
    state_file = tmp_path / "state.json"

    registry_file.write_text(
        """
{
  "providers": {
    "google_drive": {
      "id": "google_drive",
      "display_name": "Google Drive",
      "source": "cloud",
      "auth_method": "oauth"
    }
  }
}
""".strip(),
        encoding="utf-8",
    )

    service = ConnectorsStateService(state_file=str(state_file), registry_file=str(registry_file))
    providers = service.list(source="cloud")
    assert any(p["id"] == "google_drive" for p in providers)


def test_oauth_start_returns_real_handoff_payload(monkeypatch):
    monkeypatch.setattr(cr, "_provider_index", lambda: {
        "google_drive": {
            "id": "google_drive",
            "auth_method": "oauth",
            "provider_class": "google",
            "default_scopes": ["scope.read"],
            "source": "cloud",
            "display_name": "Google Drive",
        }
    })
    monkeypatch.setattr(cr, "_resolve_oauth_client_credentials", lambda provider, provider_id: ("cid", "secret"))
    monkeypatch.setattr(cr, "_build_oauth_authorize_url", lambda **kwargs: "https://accounts.example/auth")

    response = asyncio.run(
        cr.oauth_start("google_drive", cr.OAuthStartRequest(), _request())
    )

    assert response["success"] is True
    assert "dev_auto_complete" not in response
    assert response["auth_url"] == "https://accounts.example/auth"
    assert response["expires_in"] == cr.OAUTH_PENDING_TTL_SECONDS


def test_oauth_complete_uses_provider_from_pending_state(monkeypatch):
    fake_store = _FakeStore()
    fake_state = _FakeStateService()

    monkeypatch.setattr(cr, "get_connectors_secure_store", lambda: fake_store)
    monkeypatch.setattr(cr, "get_connectors_state_service", lambda: fake_state)
    monkeypatch.setattr(cr, "_provider_index", lambda: {
        "google_drive": {
            "id": "google_drive",
            "auth_method": "oauth",
            "provider_class": "google",
            "source": "cloud",
            "display_name": "Google Drive",
            "capabilities": {"read": True, "write": False, "offline_access": True, "webhooks": False},
        }
    })
    monkeypatch.setattr(cr, "_exchange_code_for_tokens", lambda **kwargs: {
        "access_token": "acc-1",
        "refresh_token": "ref-1",
        "expires_in": 3600,
        "scope": "scope.read",
    })

    cr._oauth_pending.clear()
    cr._oauth_pending["st_test"] = {
        "provider_id": "google_drive",
        "redirect_uri": "vetka://oauth/callback",
        "scopes": ["scope.read"],
        "created_at": 0,
        "expires_at": 9999999999,
    }

    response = asyncio.run(
        cr.oauth_complete(
            cr.OAuthCompleteRequest(
                oauth_state="st_test",
                auth_code="code-123",
            )
        )
    )

    assert response["success"] is True
    assert response["provider"]["id"] == "google_drive"
    assert fake_store.saved["google_drive"]["access_token"] == "acc-1"
