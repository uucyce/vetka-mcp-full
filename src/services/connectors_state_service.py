"""
Connector State Service (Phase 147.4)

Dynamic connector metadata + static registry merge.
State file stores mutable runtime fields only.
Registry file defines provider capabilities/policies.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DEFAULT_CONNECTORS_REGISTRY: List[Dict] = [
    {
        "id": "google_drive",
        "display_name": "Google Drive",
        "source": "cloud",
        "provider_class": "google",
        "auth_method": "oauth",
        "auth_flow": "authorization_code",
        "capabilities": {"read": True, "write": False, "offline_access": True, "webhooks": True},
        "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
        "scopes_minimal": ["https://www.googleapis.com/auth/drive.readonly"],
        "scopes_full": [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive.metadata.readonly",
            "https://www.googleapis.com/auth/drive.file",
        ],
        "default_scopes": ["https://www.googleapis.com/auth/drive.readonly"],
        "redirect_uri": "",
        "compliance_notes": "Google restricted scopes may require OAuth verification and CASA assessment.",
        "requires_verification": True,
        "rate_limit_model": "per_user",
        "rate_limit_policy": "per_user_1000_per_100s",
        "token_policy": "mandatory_secure_storage",
    },
    {
        "id": "gmail",
        "display_name": "Gmail",
        "source": "cloud",
        "provider_class": "google",
        "auth_method": "oauth",
        "auth_flow": "authorization_code",
        "capabilities": {"read": True, "write": False, "offline_access": True, "webhooks": True},
        "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
        "scopes_minimal": ["https://www.googleapis.com/auth/gmail.readonly"],
        "scopes_full": [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ],
        "default_scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
        "redirect_uri": "",
        "compliance_notes": "Gmail restricted scopes may require OAuth verification and CASA assessment.",
        "requires_verification": True,
        "rate_limit_model": "per_user",
        "rate_limit_policy": "per_user_250_per_min",
        "token_policy": "mandatory_secure_storage",
    },
    {
        "id": "dropbox",
        "display_name": "Dropbox",
        "source": "cloud",
        "provider_class": "dropbox",
        "auth_method": "oauth",
        "auth_flow": "authorization_code",
        "capabilities": {"read": True, "write": False, "offline_access": True, "webhooks": True},
        "scopes": ["files.content.read"],
        "scopes_minimal": ["files.content.read"],
        "scopes_full": ["files.content.read", "files.content.write"],
        "default_scopes": ["files.content.read"],
        "redirect_uri": "",
        "compliance_notes": "Use token_access_type=offline for refresh tokens.",
        "requires_verification": False,
        "rate_limit_model": "per_app",
        "rate_limit_policy": "per_app_1000_per_15min",
        "token_policy": "mandatory_secure_storage",
    },
    {
        "id": "github",
        "display_name": "GitHub",
        "source": "social",
        "provider_class": "github",
        "auth_method": "oauth",
        "auth_flow": "authorization_code",
        "capabilities": {"read": True, "write": False, "offline_access": True, "webhooks": True},
        "scopes": ["read:user", "repo"],
        "scopes_minimal": ["read:user"],
        "scopes_full": ["read:user", "repo"],
        "default_scopes": ["read:user"],
        "redirect_uri": "",
        "compliance_notes": "For repository ingest prefer fine-grained tokens with read-only permissions.",
        "requires_verification": False,
        "rate_limit_model": "per_user",
        "rate_limit_policy": "per_user_5000_per_hour",
        "token_policy": "mandatory_secure_storage",
    },
    {
        "id": "x",
        "display_name": "X",
        "source": "social",
        "provider_class": "x",
        "auth_method": "oauth",
        "auth_flow": "authorization_code",
        "capabilities": {"read": True, "write": False, "offline_access": True, "webhooks": True},
        "scopes": ["tweet.read", "users.read"],
        "scopes_minimal": ["tweet.read", "users.read"],
        "scopes_full": ["tweet.read", "users.read", "offline.access"],
        "default_scopes": ["tweet.read", "users.read"],
        "redirect_uri": "",
        "compliance_notes": "X API access depends on plan limits.",
        "requires_verification": False,
        "rate_limit_model": "per_user",
        "rate_limit_policy": "per_user_450_per_15min",
        "token_policy": "mandatory_secure_storage",
    },
    {
        "id": "linkedin",
        "display_name": "LinkedIn",
        "source": "social",
        "provider_class": "linkedin",
        "auth_method": "oauth",
        "auth_flow": "authorization_code",
        "capabilities": {"read": True, "write": False, "offline_access": True, "webhooks": False},
        "scopes": ["openid", "profile", "email"],
        "scopes_minimal": ["openid", "profile", "email"],
        "scopes_full": ["openid", "profile", "email"],
        "default_scopes": ["openid", "profile", "email"],
        "redirect_uri": "",
        "compliance_notes": "Advanced feed/message access requires partner approval.",
        "requires_verification": True,
        "rate_limit_model": "per_app",
        "rate_limit_policy": "very_strict_per_app",
        "token_policy": "mandatory_secure_storage",
    },
    {
        "id": "telegram",
        "display_name": "Telegram",
        "source": "social",
        "provider_class": "telegram",
        "auth_method": "api_key",
        "auth_flow": "bot_token",
        "capabilities": {"read": True, "write": True, "offline_access": False, "webhooks": True},
        "scopes": [],
        "scopes_minimal": [],
        "scopes_full": [],
        "default_scopes": [],
        "redirect_uri": "",
        "compliance_notes": "Bot API token via BotFather.",
        "requires_verification": False,
        "rate_limit_model": "per_bot",
        "rate_limit_policy": "per_bot_30_per_sec",
        "token_policy": "server_side_vault_allowed",
    },
]


@dataclass
class ConnectorState:
    id: str
    source: str  # cloud | social
    display_name: str
    connected: bool = False
    account_label: Optional[str] = None
    last_sync_at: Optional[str] = None
    last_scan_count: int = 0
    last_scan_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConnectorsStateService:
    def __init__(
        self,
        state_file: str = "data/connectors_state.json",
        registry_file: str = "data/connectors_registry.json",
    ) -> None:
        self.state_file = state_file
        self.registry_file = registry_file
        self._lock = Lock()
        self._states: Dict[str, ConnectorState] = {}
        self._registry: Dict[str, Dict] = {}
        self._load_registry()
        self._load()

    def _load_registry(self) -> None:
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
        if not os.path.exists(self.registry_file):
            payload = {"providers": DEFAULT_CONNECTORS_REGISTRY, "updated_at": _utc_now_iso()}
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)

        loaded: Dict[str, Dict] = {}
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            providers_raw = raw.get("providers", [])
            if isinstance(providers_raw, dict):
                providers_iter = providers_raw.values()
            else:
                providers_iter = providers_raw
            for item in providers_iter:
                cid = str(item.get("id", "")).strip()
                if not cid:
                    continue
                loaded[cid] = item
        except Exception:
            loaded = {item["id"]: item for item in DEFAULT_CONNECTORS_REGISTRY}

        # Ensure defaults exist if registry file is partial.
        for default in DEFAULT_CONNECTORS_REGISTRY:
            if default["id"] not in loaded:
                loaded[default["id"]] = default

        self._registry = loaded

    def _default_state_for(self, provider_id: str) -> ConnectorState:
        reg = self._registry.get(provider_id, {})
        return ConnectorState(
            id=provider_id,
            source=str(reg.get("source", "cloud")),
            display_name=str(reg.get("display_name", provider_id)),
        )

    def _load(self) -> None:
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        if not os.path.exists(self.state_file):
            self._states = {pid: self._default_state_for(pid) for pid in self._registry.keys()}
            self._persist()
            return

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            items = raw.get("providers", [])
            loaded: Dict[str, ConnectorState] = {}
            for item in items:
                cid = str(item.get("id", "")).strip()
                if not cid:
                    continue
                loaded[cid] = ConnectorState(
                    id=cid,
                    source=str(item.get("source", "")).strip() or str(self._registry.get(cid, {}).get("source", "cloud")),
                    display_name=str(item.get("display_name", "")).strip() or str(self._registry.get(cid, {}).get("display_name", cid)),
                    connected=bool(item.get("connected", False)),
                    account_label=item.get("account_label"),
                    last_sync_at=item.get("last_sync_at"),
                    last_scan_count=int(item.get("last_scan_count", 0) or 0),
                    last_scan_at=item.get("last_scan_at"),
                    updated_at=item.get("updated_at"),
                )
            for provider_id in self._registry.keys():
                if provider_id not in loaded:
                    loaded[provider_id] = self._default_state_for(provider_id)
            self._states = loaded
        except Exception:
            self._states = {pid: self._default_state_for(pid) for pid in self._registry.keys()}
            self._persist()

    def _persist(self) -> None:
        payload = {
            "providers": [asdict(self._states[k]) for k in sorted(self._states.keys())],
            "updated_at": _utc_now_iso(),
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _merge_with_registry(self, state: ConnectorState) -> Dict:
        reg = self._registry.get(state.id, {})
        merged = asdict(state)
        merged["display_name"] = str(reg.get("display_name", merged.get("display_name", state.id)))
        merged["source"] = str(reg.get("source", merged.get("source", "cloud")))
        merged["auth_method"] = str(reg.get("auth_method", "oauth"))
        merged["provider_class"] = reg.get("provider_class")
        merged["auth_flow"] = reg.get("auth_flow")
        merged["capabilities"] = reg.get("capabilities", {
            "read": True,
            "write": False,
            "offline_access": True,
            "webhooks": False,
        })
        merged["scopes"] = reg.get("scopes")
        merged["scopes_minimal"] = reg.get("scopes_minimal")
        merged["scopes_full"] = reg.get("scopes_full")
        merged["default_scopes"] = reg.get("default_scopes")
        merged["redirect_uri"] = reg.get("redirect_uri")
        merged["compliance_notes"] = reg.get("compliance_notes")
        merged["requires_verification"] = bool(reg.get("requires_verification", False))
        merged["rate_limit_model"] = reg.get("rate_limit_model")
        merged["rate_limit_policy"] = reg.get("rate_limit_policy")
        merged["token_policy"] = reg.get("token_policy")
        merged["expires_in"] = reg.get("expires_in")
        return merged

    def list(self, source: Optional[str] = None) -> List[Dict]:
        with self._lock:
            items = [self._merge_with_registry(v) for v in self._states.values()]
        if source:
            source = source.strip().lower()
            items = [i for i in items if i.get("source") == source]
        return sorted(items, key=lambda x: (x.get("source", ""), x.get("display_name", "")))

    def get_registry(self, source: Optional[str] = None) -> List[Dict]:
        items = list(self._registry.values())
        if source:
            source = source.strip().lower()
            items = [i for i in items if str(i.get("source", "")).lower() == source]
        return sorted(items, key=lambda x: (x.get("source", ""), x.get("display_name", "")))

    def connect(self, provider_id: str, account_label: Optional[str]) -> Dict:
        with self._lock:
            state = self._states.get(provider_id)
            if not state:
                raise KeyError(provider_id)
            state.connected = True
            state.account_label = (account_label or state.display_name).strip()[:120]
            state.updated_at = _utc_now_iso()
            self._persist()
            return self._merge_with_registry(state)

    def disconnect(self, provider_id: str) -> Dict:
        with self._lock:
            state = self._states.get(provider_id)
            if not state:
                raise KeyError(provider_id)
            state.connected = False
            state.account_label = None
            state.updated_at = _utc_now_iso()
            self._persist()
            return self._merge_with_registry(state)

    def mark_scan(self, provider_id: str, scanned_count: int) -> Dict:
        with self._lock:
            state = self._states.get(provider_id)
            if not state:
                raise KeyError(provider_id)
            state.last_scan_count = max(0, int(scanned_count))
            state.last_scan_at = _utc_now_iso()
            state.last_sync_at = state.last_scan_at
            state.updated_at = state.last_scan_at
            self._persist()
            return self._merge_with_registry(state)


_service: Optional[ConnectorsStateService] = None


def get_connectors_state_service() -> ConnectorsStateService:
    global _service
    if _service is None:
        _service = ConnectorsStateService()
    return _service
