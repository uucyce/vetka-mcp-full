"""
Chat Artifact Registry

MARKER_CHAT_HUB_4A:
Persistent mapping between chat messages and produced artifacts.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


REGISTRY_FILE = Path("data/chat_artifacts.json")


class ChatArtifactRegistry:
    """Registry for chat->artifact links with lightweight dedup."""

    def __init__(self, registry_file: Path = REGISTRY_FILE):
        self.registry_file = registry_file
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Any]:
        if not self.registry_file.exists():
            return {"by_chat": {}, "updated_at": ""}
        try:
            data = json.loads(self.registry_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"by_chat": {}, "updated_at": ""}
            by_chat = data.get("by_chat", {})
            if not isinstance(by_chat, dict):
                by_chat = {}
            return {"by_chat": by_chat, "updated_at": data.get("updated_at", "")}
        except Exception:
            return {"by_chat": {}, "updated_at": ""}

    def _save(self, data: Dict[str, Any]) -> None:
        data["updated_at"] = datetime.now().isoformat()
        self.registry_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def link(
        self,
        chat_id: str,
        message_id: Optional[str],
        artifact: Dict[str, Any],
    ) -> bool:
        """Upsert link. Returns True when registry changed."""
        chat_key = str(chat_id or "").strip()
        if not chat_key:
            return False

        artifact_id = str(artifact.get("artifact_id") or artifact.get("id") or "").strip()
        file_path = str(artifact.get("file_path") or "").strip()
        if not artifact_id and not file_path:
            return False

        data = self._load()
        by_chat = data.setdefault("by_chat", {})
        entries = by_chat.setdefault(chat_key, [])
        if not isinstance(entries, list):
            entries = []
            by_chat[chat_key] = entries

        message_key = str(message_id or "").strip() or None
        dedup_key = (
            artifact_id,
            file_path,
            message_key,
        )

        for entry in entries:
            existing_key = (
                str(entry.get("artifact_id", "")).strip(),
                str(entry.get("file_path", "")).strip(),
                (str(entry.get("message_id", "")).strip() or None),
            )
            if existing_key == dedup_key:
                return False

        now_iso = datetime.now().isoformat()
        entries.append(
            {
                "chat_id": chat_key,
                "message_id": message_key,
                "artifact_id": artifact_id or None,
                "file_path": file_path or None,
                "name": artifact.get("name"),
                "source_agent": artifact.get("source_agent"),
                "source_role": artifact.get("source_role"),
                "status": artifact.get("status"),
                "linked_at": now_iso,
            }
        )

        # Keep most recent links only
        if len(entries) > 3000:
            by_chat[chat_key] = entries[-3000:]

        self._save(data)
        return True

    def get_by_chat(self, chat_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        chat_key = str(chat_id or "").strip()
        if not chat_key:
            return []
        data = self._load()
        by_chat = data.get("by_chat", {})
        if not isinstance(by_chat, dict):
            return []
        entries = by_chat.get(chat_key, [])
        if not isinstance(entries, list):
            return []
        return list(entries[-max(1, min(limit, 5000)):])[::-1]


_registry_singleton: Optional[ChatArtifactRegistry] = None


def get_chat_artifact_registry() -> ChatArtifactRegistry:
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = ChatArtifactRegistry()
    return _registry_singleton

