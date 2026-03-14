"""
REFLEX User Preferences — Pin / Ban / Custom Weights.

MARKER_173.P2.PREFS

Persistent user preferences for REFLEX tool selection:
- Pinned tools: always included in recommendations
- Banned tools: always excluded from recommendations
- Custom weights: per-tool score overrides (0.0-1.0)

Persisted to data/reflex/user_preferences.json.
Thread-safe writes via threading.Lock.

Part of VETKA OS:
  VETKA > REFLEX > Preferences (this file)

@status: active
@phase: 173.P2
@depends: reflex_feedback (REFLEX_DATA_DIR)
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

# Reuse the same data directory as feedback
REFLEX_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "reflex"
PREFERENCES_PATH = REFLEX_DATA_DIR / "user_preferences.json"


# ─── Data Model ──────────────────────────────────────────────────

@dataclass
class ReflexPreferences:
    """MARKER_173.P2.MODEL — User preferences for tool selection."""

    pinned_tools: Set[str] = field(default_factory=set)
    banned_tools: Set[str] = field(default_factory=set)
    custom_weights: Dict[str, float] = field(default_factory=dict)

    def is_pinned(self, tool_id: str) -> bool:
        return tool_id in self.pinned_tools

    def is_banned(self, tool_id: str) -> bool:
        return tool_id in self.banned_tools

    def get_custom_weight(self, tool_id: str) -> Optional[float]:
        return self.custom_weights.get(tool_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pinned_tools": sorted(self.pinned_tools),
            "banned_tools": sorted(self.banned_tools),
            "custom_weights": dict(self.custom_weights),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ReflexPreferences":
        return ReflexPreferences(
            pinned_tools=set(d.get("pinned_tools", [])),
            banned_tools=set(d.get("banned_tools", [])),
            custom_weights={
                k: max(0.0, min(1.0, float(v)))
                for k, v in d.get("custom_weights", {}).items()
            },
        )


# ─── Preferences Store ──────────────────────────────────────────

class ReflexPreferencesStore:
    """MARKER_173.P2.STORE — Thread-safe persistent preferences store."""

    def __init__(self, path: Optional[Path] = None):
        self._path = path or PREFERENCES_PATH
        self._lock = threading.Lock()
        self._prefs: Optional[ReflexPreferences] = None

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> ReflexPreferences:
        """Load preferences from disk. Returns empty prefs if file missing."""
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._prefs = ReflexPreferences.from_dict(data)
            else:
                self._prefs = ReflexPreferences()
        except Exception as e:
            logger.warning("[REFLEX Prefs] Load error: %s — using defaults", e)
            self._prefs = ReflexPreferences()
        return self._prefs

    def save(self, prefs: Optional[ReflexPreferences] = None) -> None:
        """Persist preferences to disk. Creates directories if needed."""
        if prefs is not None:
            self._prefs = prefs
        if self._prefs is None:
            return

        with self._lock:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                data = self._prefs.to_dict()
                data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                with open(self._path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error("[REFLEX Prefs] Save error: %s", e)

    def get(self) -> ReflexPreferences:
        """Get current preferences (lazy load)."""
        if self._prefs is None:
            self.load()
        return self._prefs  # type: ignore

    # ─── Convenience mutators ────────────────────────────────────

    def pin_tool(self, tool_id: str) -> None:
        """Pin a tool. Removes it from banned if present."""
        prefs = self.get()
        prefs.banned_tools.discard(tool_id)  # No conflict
        prefs.pinned_tools.add(tool_id)
        self.save()

    def unpin_tool(self, tool_id: str) -> None:
        """Remove pin from a tool."""
        prefs = self.get()
        prefs.pinned_tools.discard(tool_id)
        self.save()

    def ban_tool(self, tool_id: str) -> None:
        """Ban a tool. Removes it from pinned if present."""
        prefs = self.get()
        prefs.pinned_tools.discard(tool_id)  # No conflict
        prefs.banned_tools.add(tool_id)
        self.save()

    def unban_tool(self, tool_id: str) -> None:
        """Remove ban from a tool."""
        prefs = self.get()
        prefs.banned_tools.discard(tool_id)
        self.save()

    def set_custom_weight(self, tool_id: str, weight: float) -> None:
        """Set custom weight for a tool (clamped to 0.0-1.0)."""
        prefs = self.get()
        prefs.custom_weights[tool_id] = max(0.0, min(1.0, weight))
        self.save()

    def remove_custom_weight(self, tool_id: str) -> None:
        """Remove custom weight for a tool."""
        prefs = self.get()
        prefs.custom_weights.pop(tool_id, None)
        self.save()

    def remove_preference(self, tool_id: str) -> None:
        """Remove ALL preferences (pin, ban, weight) for a tool."""
        prefs = self.get()
        prefs.pinned_tools.discard(tool_id)
        prefs.banned_tools.discard(tool_id)
        prefs.custom_weights.pop(tool_id, None)
        self.save()

    def clear_all(self) -> None:
        """Reset all preferences to empty."""
        self._prefs = ReflexPreferences()
        self.save()


# ─── Singleton ───────────────────────────────────────────────────

_store_instance: Optional[ReflexPreferencesStore] = None


def get_reflex_preferences() -> ReflexPreferencesStore:
    """Get the singleton preferences store."""
    global _store_instance
    if _store_instance is None:
        _store_instance = ReflexPreferencesStore()
    return _store_instance


def reset_reflex_preferences() -> None:
    """Reset the singleton (for tests)."""
    global _store_instance
    _store_instance = None
