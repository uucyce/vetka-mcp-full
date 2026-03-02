"""
Voice Assignment Registry (S2)

MARKER_156.VOICE.S2_REGISTRY

Persistent model identity -> voice assignment registry.
Identity key format: "{provider}:{model_id}".
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from src.voice.qwen_voice_catalog import QWEN_LEGACY_ALIASES, QWEN_VOICE_POOL, normalize_qwen_voice_id

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_REGISTRY_PATH = _PROJECT_ROOT / "data" / "agent_voice_assignments.json"
_DEFAULT_ROLE_MAP_PATH = _PROJECT_ROOT / "data" / "agent_role_voice_map.json"

_DEFAULT_VOICE_POOL = QWEN_VOICE_POOL
_LEGACY_VOICE_ALIASES = QWEN_LEGACY_ALIASES

_DEFAULT_PERSONA_POOL = [
    "analytical",
    "calm",
    "confident",
    "warm",
    "focused",
    "energetic",
    "strict",
    "reflective",
]

_DEFAULT_ROLE_VOICE_MAP = {
    "pm": "ryan",
    "dev": "eric",
    "qa": "aiden",
    "architect": "uncle_fu",
    "hostess": "vivian",
    "researcher": "serena",
    "jarvis": "dylan",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VoiceAssignmentRegistry:
    """
    Process-safe-in-instance assignment registry with JSON persistence.
    Atomicity is guaranteed per process via asyncio.Lock + atomic file replace.
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = path or _DEFAULT_REGISTRY_PATH
        self._lock = asyncio.Lock()
        self._loaded = False
        self._state: Dict[str, Any] = {
            "version": "1.0",
            "updated_at": _utc_now_iso(),
            "last_free_voice_id": None,
            "assignments": {},
        }

    def _identity_key(self, provider: str, model_id: str) -> str:
        provider_norm = (provider or "unknown").strip().lower() or "unknown"
        model_norm = (model_id or "unknown").strip() or "unknown"
        return f"{provider_norm}:{model_norm}"

    def _group_role_key(self, group_id: str, role: str) -> str:
        group_norm = (group_id or "unknown_group").strip() or "unknown_group"
        role_norm = self._normalize_role(role)
        return f"group:{group_norm}:role:{role_norm}"

    def _normalize_role(self, role: str) -> str:
        cleaned = re.sub(r"[^a-z0-9_]+", "", (role or "").strip().lower().replace("@", ""))
        return cleaned or "unknown"

    def _normalize_voice_id(self, voice_id: str) -> str:
        return normalize_qwen_voice_id(voice_id, default=_DEFAULT_VOICE_POOL[0])

    def _migrate_assignment_voices_locked(self) -> bool:
        changed = False
        assignments = self._state.get("assignments", {})
        if not isinstance(assignments, dict):
            return False

        for record in assignments.values():
            if not isinstance(record, dict):
                continue
            current_voice = str(record.get("voice_id", "")).strip()
            normalized = self._normalize_voice_id(current_voice)
            if normalized and normalized != current_voice:
                record["voice_id"] = normalized
                record["updated_at"] = _utc_now_iso()
                changed = True

        return changed

    def _load_role_voice_map(self) -> Dict[str, str]:
        try:
            if _DEFAULT_ROLE_MAP_PATH.exists():
                payload = json.loads(_DEFAULT_ROLE_MAP_PATH.read_text(encoding="utf-8"))
                role_map = payload.get("roles", payload) if isinstance(payload, dict) else {}
                out: Dict[str, str] = {}
                if isinstance(role_map, dict):
                    for raw_role, raw_voice in role_map.items():
                        role = self._normalize_role(str(raw_role))
                        voice = self._normalize_voice_id(str(raw_voice))
                        if role and voice:
                            out[role] = voice
                if out:
                    return out
        except Exception as exc:
            logger.warning("[VoiceAssignmentRegistry] role voice map load failed: %s", exc)
        return dict(_DEFAULT_ROLE_VOICE_MAP)

    def _pick_voice_id(self, identity_key: str, assignments: Dict[str, Any]) -> str:
        used = {
            str(v.get("voice_id")).strip()
            for v in assignments.values()
            if isinstance(v, dict) and v.get("voice_id")
        }
        available = [v for v in _DEFAULT_VOICE_POOL if v not in used]
        self._state["last_free_voice_id"] = available[0] if available else None
        pool = available if available else _DEFAULT_VOICE_POOL
        return pool[hash(identity_key) % len(pool)]

    def _pick_persona_tag(self, identity_key: str) -> str:
        salt_key = f"{identity_key}::persona"
        return _DEFAULT_PERSONA_POOL[hash(salt_key) % len(_DEFAULT_PERSONA_POOL)]

    async def _ensure_loaded_locked(self) -> None:
        if self._loaded:
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)

        if not self._path.exists():
            await self._save_locked()
            self._loaded = True
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("voice assignment registry is not an object")
            if not isinstance(data.get("assignments"), dict):
                data["assignments"] = {}
            self._state = data
            if "last_free_voice_id" not in self._state:
                self._state["last_free_voice_id"] = None
            if self._migrate_assignment_voices_locked():
                await self._save_locked()
        except Exception as exc:
            logger.warning(
                "[VoiceAssignmentRegistry] Failed to load %s, resetting: %s",
                self._path,
                exc,
            )
            self._state = {
                "version": "1.0",
                "updated_at": _utc_now_iso(),
                "last_free_voice_id": None,
                "assignments": {},
            }
            await self._save_locked()

        self._loaded = True

    async def _save_locked(self) -> None:
        self._state["updated_at"] = _utc_now_iso()
        payload = json.dumps(self._state, indent=2, ensure_ascii=False)
        temp_path = self._path.with_suffix(".tmp")
        temp_path.write_text(payload, encoding="utf-8")
        temp_path.replace(self._path)

    async def get_or_assign(
        self,
        *,
        provider: str,
        model_id: str,
        tts_provider: str = "qwen3",
    ) -> Dict[str, Any]:
        """
        Atomic first assignment:
        - if key exists -> return existing
        - else allocate voice_id + persona_tag, persist, return
        """
        async with self._lock:
            await self._ensure_loaded_locked()

            assignments = self._state["assignments"]
            identity_key = self._identity_key(provider, model_id)
            existing = assignments.get(identity_key)
            if isinstance(existing, dict):
                existing["last_used_at"] = _utc_now_iso()
                existing["usage_count"] = int(existing.get("usage_count", 0) or 0) + 1
                existing["status"] = existing.get("status") or "active"
                existing["assigned_at"] = existing.get("assigned_at") or existing.get("created_at") or _utc_now_iso()
                existing["updated_at"] = _utc_now_iso()
                await self._save_locked()
                return dict(existing)

            record = {
                "model_identity_key": identity_key,
                "provider": (provider or "unknown").strip().lower() or "unknown",
                "model_id": (model_id or "unknown").strip() or "unknown",
                "voice_id": self._pick_voice_id(identity_key, assignments),
                "tts_provider": tts_provider,
                "persona_tag": self._pick_persona_tag(identity_key),
                "assigned_at": _utc_now_iso(),
                "last_used_at": _utc_now_iso(),
                "usage_count": 1,
                "status": "active",
                "created_at": _utc_now_iso(),
                "updated_at": _utc_now_iso(),
            }
            assignments[identity_key] = record
            await self._save_locked()
            return dict(record)

    async def get_or_assign_group_role(
        self,
        *,
        group_id: str,
        role: str,
        provider: str,
        model_id: str,
        tts_provider: str = "qwen3",
    ) -> Dict[str, Any]:
        """
        MARKER_156.VOICE.S6_ROLE_LOCK:
        Stable voice assignment by group+role (team chat), independent from model overlap.
        """
        async with self._lock:
            await self._ensure_loaded_locked()
            assignments = self._state["assignments"]
            identity_key = self._group_role_key(group_id, role)
            existing = assignments.get(identity_key)
            if isinstance(existing, dict):
                existing["last_used_at"] = _utc_now_iso()
                existing["usage_count"] = int(existing.get("usage_count", 0) or 0) + 1
                existing["status"] = existing.get("status") or "active"
                existing["assigned_at"] = existing.get("assigned_at") or existing.get("created_at") or _utc_now_iso()
                existing["updated_at"] = _utc_now_iso()
                await self._save_locked()
                return dict(existing)

            role_norm = self._normalize_role(role)
            role_voice_map = self._load_role_voice_map()
            preferred_voice = role_voice_map.get(role_norm)
            if preferred_voice:
                voice_id = self._normalize_voice_id(preferred_voice)
            else:
                voice_id = self._pick_voice_id(identity_key, assignments)

            record = {
                "model_identity_key": identity_key,
                "provider": (provider or "unknown").strip().lower() or "unknown",
                "model_id": (model_id or "unknown").strip() or "unknown",
                "group_id": (group_id or "").strip(),
                "role": role_norm,
                "voice_id": voice_id,
                "tts_provider": tts_provider,
                "persona_tag": self._pick_persona_tag(identity_key),
                "assigned_at": _utc_now_iso(),
                "last_used_at": _utc_now_iso(),
                "usage_count": 1,
                "status": "active",
                "created_at": _utc_now_iso(),
                "updated_at": _utc_now_iso(),
            }
            assignments[identity_key] = record
            await self._save_locked()
            return dict(record)


_registry = VoiceAssignmentRegistry()


def get_voice_assignment_registry() -> VoiceAssignmentRegistry:
    return _registry
