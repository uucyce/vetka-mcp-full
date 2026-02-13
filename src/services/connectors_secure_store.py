"""
Connectors Secure Store (Phase 147.3)

Stores connector tokens/secrets outside regular connector metadata.
Encryption is enabled when cryptography+ENCRYPTION_KEY are available.
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Optional, Any

try:
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover
    Fernet = None  # type: ignore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConnectorsSecureStore:
    def __init__(self, store_file: str = "data/connectors_tokens.json") -> None:
        self.store_file = store_file
        self._lock = Lock()
        self._entries: Dict[str, Dict] = {}
        self._fernet = self._init_fernet()
        self._load()

    def _init_fernet(self):
        if Fernet is None:
            return None
        key = os.getenv("ENCRYPTION_KEY", "").strip()
        if not key:
            return None
        try:
            # Accept raw key or plain string converted to urlsafe base64 32 bytes.
            if len(key) != 44:
                padded = (key.encode("utf-8") + b"0" * 32)[:32]
                key = base64.urlsafe_b64encode(padded).decode("utf-8")
            return Fernet(key.encode("utf-8"))
        except Exception:
            return None

    def _load(self) -> None:
        os.makedirs(os.path.dirname(self.store_file), exist_ok=True)
        if not os.path.exists(self.store_file):
            self._persist()
            return
        try:
            with open(self.store_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            entries = raw.get("tokens", {})
            if isinstance(entries, dict):
                self._entries = entries
        except Exception:
            self._entries = {}
            self._persist()

    def _persist(self) -> None:
        payload = {
            "tokens": self._entries,
            "encryption_enabled": bool(self._fernet),
            "updated_at": _utc_now_iso(),
        }
        with open(self.store_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _encode(self, token: str) -> str:
        if self._fernet:
            return self._fernet.encrypt(token.encode("utf-8")).decode("utf-8")
        return base64.b64encode(token.encode("utf-8")).decode("utf-8")

    def _decode(self, payload: str) -> str:
        if self._fernet:
            return self._fernet.decrypt(payload.encode("utf-8")).decode("utf-8")
        return base64.b64decode(payload.encode("utf-8")).decode("utf-8")

    def set_token(self, provider_id: str, token: str, token_type: str = "oauth_access") -> None:
        with self._lock:
            self._entries[provider_id] = {
                "token_enc": self._encode(token),
                "token_type": token_type,
                "updated_at": _utc_now_iso(),
            }
            self._persist()

    def set_oauth_tokens(
        self,
        provider_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        scope: Optional[str] = None,
        token_type: str = "oauth_access",
    ) -> None:
        with self._lock:
            entry: Dict[str, Any] = {
                "token_enc": self._encode(access_token),
                "token_type": token_type,
                "updated_at": _utc_now_iso(),
            }
            if refresh_token:
                entry["refresh_token_enc"] = self._encode(refresh_token)
            if expires_in is not None:
                entry["expires_in"] = int(expires_in)
            if scope:
                entry["scope"] = scope
            self._entries[provider_id] = entry
            self._persist()

    def set_oauth_client_credentials(self, provider_id: str, client_id: str, client_secret: str) -> None:
        with self._lock:
            entry: Dict[str, Any] = dict(self._entries.get(provider_id, {}))
            entry["oauth_client_id_enc"] = self._encode(client_id)
            entry["oauth_client_secret_enc"] = self._encode(client_secret)
            entry["oauth_credentials_updated_at"] = _utc_now_iso()
            entry["updated_at"] = _utc_now_iso()
            self._entries[provider_id] = entry
            self._persist()

    def get_oauth_client_credentials(self, provider_id: str) -> Optional[Dict[str, str]]:
        with self._lock:
            item = self._entries.get(provider_id)
        if not item:
            return None
        cid_enc = item.get("oauth_client_id_enc")
        sec_enc = item.get("oauth_client_secret_enc")
        if not cid_enc or not sec_enc:
            return None
        try:
            return {
                "client_id": self._decode(str(cid_enc)),
                "client_secret": self._decode(str(sec_enc)),
            }
        except Exception:
            return None

    def clear_token(self, provider_id: str) -> None:
        with self._lock:
            if provider_id in self._entries:
                del self._entries[provider_id]
                self._persist()

    def has_token(self, provider_id: str) -> bool:
        with self._lock:
            entry = self._entries.get(provider_id)
            return bool(entry and entry.get("token_enc"))

    def get_token(self, provider_id: str) -> Optional[str]:
        with self._lock:
            item = self._entries.get(provider_id)
        if not item:
            return None
        try:
            return self._decode(str(item.get("token_enc", "")))
        except Exception:
            return None

    def get_oauth_bundle(self, provider_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self._entries.get(provider_id)
        if not item:
            return None
        try:
            bundle: Dict[str, Any] = {
                "access_token": self._decode(str(item.get("token_enc", ""))),
                "token_type": item.get("token_type"),
                "updated_at": item.get("updated_at"),
                "expires_in": item.get("expires_in"),
                "scope": item.get("scope"),
            }
            refresh_enc = item.get("refresh_token_enc")
            if refresh_enc:
                bundle["refresh_token"] = self._decode(str(refresh_enc))
            return bundle
        except Exception:
            return None

    def encryption_enabled(self) -> bool:
        return bool(self._fernet)


_store: Optional[ConnectorsSecureStore] = None


def get_connectors_secure_store() -> ConnectorsSecureStore:
    global _store
    if _store is None:
        _store = ConnectorsSecureStore()
    return _store
