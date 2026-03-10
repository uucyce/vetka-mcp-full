"""
Tests for REFLEX User Preferences — Phase 173.P2

MARKER_173.P2.TESTS

Tests preference datamodel, store persistence,
pin/ban conflict resolution, and REST endpoints.

T2.1  — Empty preferences defaults
T2.2  — to_dict/from_dict round-trip
T2.3  — is_pinned/is_banned checks
T2.4  — Save and load persistence (tmp_path)
T2.5  — Pin adds, unpin removes
T2.6  — Ban adds, unban removes
T2.7  — Pin removes ban (conflict resolution)
T2.8  — Ban removes pin (conflict resolution)
T2.9  — Custom weight clamped to 0-1
T2.10 — Remove preference clears all
T2.11 — Clear all resets to empty
T2.12 — Load missing file returns empty
T2.13 — Singleton get/reset
T2.14 — REST: GET /api/reflex/preferences
T2.15 — REST: POST /api/reflex/pin
T2.16 — REST: POST /api/reflex/ban
T2.17 — REST: DELETE /api/reflex/preferences/{tool_id}
T2.18 — REST: endpoints disabled when REFLEX off
"""

import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── T2.1-T2.3: Data Model ──────────────────────────────────────

class TestPreferencesDataModel:
    """T2.1-T2.3: ReflexPreferences dataclass."""

    def test_empty_defaults(self):
        from src.services.reflex_preferences import ReflexPreferences
        prefs = ReflexPreferences()
        assert prefs.pinned_tools == set()
        assert prefs.banned_tools == set()
        assert prefs.custom_weights == {}

    def test_to_dict_round_trip(self):
        from src.services.reflex_preferences import ReflexPreferences
        prefs = ReflexPreferences(
            pinned_tools={"tool_a", "tool_b"},
            banned_tools={"tool_c"},
            custom_weights={"tool_d": 0.8, "tool_e": 0.3},
        )
        d = prefs.to_dict()
        restored = ReflexPreferences.from_dict(d)
        assert restored.pinned_tools == {"tool_a", "tool_b"}
        assert restored.banned_tools == {"tool_c"}
        assert restored.custom_weights == {"tool_d": 0.8, "tool_e": 0.3}

    def test_is_pinned(self):
        from src.services.reflex_preferences import ReflexPreferences
        prefs = ReflexPreferences(pinned_tools={"tool_a"})
        assert prefs.is_pinned("tool_a") is True
        assert prefs.is_pinned("tool_b") is False

    def test_is_banned(self):
        from src.services.reflex_preferences import ReflexPreferences
        prefs = ReflexPreferences(banned_tools={"tool_x"})
        assert prefs.is_banned("tool_x") is True
        assert prefs.is_banned("tool_y") is False

    def test_get_custom_weight(self):
        from src.services.reflex_preferences import ReflexPreferences
        prefs = ReflexPreferences(custom_weights={"tool_a": 0.7})
        assert prefs.get_custom_weight("tool_a") == 0.7
        assert prefs.get_custom_weight("tool_b") is None


# ─── T2.4-T2.11: Store ──────────────────────────────────────────

class TestPreferencesStore:
    """T2.4-T2.11: ReflexPreferencesStore persistence and mutators."""

    def test_save_and_load(self, tmp_path):
        from src.services.reflex_preferences import ReflexPreferencesStore, ReflexPreferences
        path = tmp_path / "prefs.json"
        store = ReflexPreferencesStore(path=path)
        prefs = ReflexPreferences(pinned_tools={"tool_a"}, banned_tools={"tool_b"})
        store.save(prefs)

        store2 = ReflexPreferencesStore(path=path)
        loaded = store2.load()
        assert loaded.pinned_tools == {"tool_a"}
        assert loaded.banned_tools == {"tool_b"}

    def test_pin_adds(self, tmp_path):
        from src.services.reflex_preferences import ReflexPreferencesStore
        store = ReflexPreferencesStore(path=tmp_path / "prefs.json")
        store.pin_tool("tool_x")
        assert store.get().is_pinned("tool_x")

    def test_unpin_removes(self, tmp_path):
        from src.services.reflex_preferences import ReflexPreferencesStore
        store = ReflexPreferencesStore(path=tmp_path / "prefs.json")
        store.pin_tool("tool_x")
        store.unpin_tool("tool_x")
        assert not store.get().is_pinned("tool_x")

    def test_ban_adds(self, tmp_path):
        from src.services.reflex_preferences import ReflexPreferencesStore
        store = ReflexPreferencesStore(path=tmp_path / "prefs.json")
        store.ban_tool("tool_y")
        assert store.get().is_banned("tool_y")

    def test_unban_removes(self, tmp_path):
        from src.services.reflex_preferences import ReflexPreferencesStore
        store = ReflexPreferencesStore(path=tmp_path / "prefs.json")
        store.ban_tool("tool_y")
        store.unban_tool("tool_y")
        assert not store.get().is_banned("tool_y")

    def test_pin_removes_ban(self, tmp_path):
        from src.services.reflex_preferences import ReflexPreferencesStore
        store = ReflexPreferencesStore(path=tmp_path / "prefs.json")
        store.ban_tool("tool_z")
        assert store.get().is_banned("tool_z")
        store.pin_tool("tool_z")
        assert store.get().is_pinned("tool_z")
        assert not store.get().is_banned("tool_z")

    def test_ban_removes_pin(self, tmp_path):
        from src.services.reflex_preferences import ReflexPreferencesStore
        store = ReflexPreferencesStore(path=tmp_path / "prefs.json")
        store.pin_tool("tool_z")
        assert store.get().is_pinned("tool_z")
        store.ban_tool("tool_z")
        assert store.get().is_banned("tool_z")
        assert not store.get().is_pinned("tool_z")

    def test_custom_weight_clamped(self, tmp_path):
        from src.services.reflex_preferences import ReflexPreferencesStore
        store = ReflexPreferencesStore(path=tmp_path / "prefs.json")
        store.set_custom_weight("tool_a", 2.5)  # Above 1.0
        assert store.get().custom_weights["tool_a"] == 1.0
        store.set_custom_weight("tool_b", -0.5)  # Below 0.0
        assert store.get().custom_weights["tool_b"] == 0.0

    def test_remove_preference(self, tmp_path):
        from src.services.reflex_preferences import ReflexPreferencesStore
        store = ReflexPreferencesStore(path=tmp_path / "prefs.json")
        store.pin_tool("tool_a")
        store.set_custom_weight("tool_a", 0.9)
        store.remove_preference("tool_a")
        assert not store.get().is_pinned("tool_a")
        assert store.get().get_custom_weight("tool_a") is None

    def test_clear_all(self, tmp_path):
        from src.services.reflex_preferences import ReflexPreferencesStore
        store = ReflexPreferencesStore(path=tmp_path / "prefs.json")
        store.pin_tool("tool_a")
        store.ban_tool("tool_b")
        store.clear_all()
        assert store.get().pinned_tools == set()
        assert store.get().banned_tools == set()

    def test_load_missing_file(self, tmp_path):
        from src.services.reflex_preferences import ReflexPreferencesStore
        store = ReflexPreferencesStore(path=tmp_path / "nonexistent.json")
        prefs = store.load()
        assert prefs.pinned_tools == set()
        assert prefs.banned_tools == set()


# ─── T2.12-T2.13: Singleton ─────────────────────────────────────

class TestPreferencesSingleton:
    """T2.12-T2.13: Singleton get/reset."""

    def test_get_returns_same(self):
        from src.services.reflex_preferences import get_reflex_preferences, reset_reflex_preferences
        reset_reflex_preferences()
        s1 = get_reflex_preferences()
        s2 = get_reflex_preferences()
        assert s1 is s2
        reset_reflex_preferences()

    def test_reset_clears(self):
        from src.services.reflex_preferences import get_reflex_preferences, reset_reflex_preferences
        reset_reflex_preferences()
        s1 = get_reflex_preferences()
        reset_reflex_preferences()
        s2 = get_reflex_preferences()
        assert s1 is not s2
        reset_reflex_preferences()


# ─── T2.14-T2.18: REST Endpoints ────────────────────────────────

class TestPreferencesEndpoints:
    """T2.14-T2.18: REST API for preferences."""

    @pytest.mark.asyncio
    async def test_get_preferences(self):
        from src.api.routes.reflex_routes import reflex_preferences
        from src.services.reflex_preferences import ReflexPreferences

        mock_store = MagicMock()
        mock_store.get.return_value = ReflexPreferences(pinned_tools={"tool_a"})

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_preferences.get_reflex_preferences", return_value=mock_store):
            result = await reflex_preferences()

        assert result["enabled"] is True
        assert "tool_a" in result["preferences"]["pinned_tools"]

    @pytest.mark.asyncio
    async def test_pin_endpoint(self):
        from src.api.routes.reflex_routes import reflex_pin
        from src.services.reflex_preferences import ReflexPreferences

        mock_store = MagicMock()
        mock_store.get.return_value = ReflexPreferences(pinned_tools={"tool_x"})

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_preferences.get_reflex_preferences", return_value=mock_store):
            result = await reflex_pin(tool_id="tool_x")

        mock_store.pin_tool.assert_called_once_with("tool_x")
        assert result["action"] == "pin"

    @pytest.mark.asyncio
    async def test_ban_endpoint(self):
        from src.api.routes.reflex_routes import reflex_ban
        from src.services.reflex_preferences import ReflexPreferences

        mock_store = MagicMock()
        mock_store.get.return_value = ReflexPreferences(banned_tools={"tool_y"})

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_preferences.get_reflex_preferences", return_value=mock_store):
            result = await reflex_ban(tool_id="tool_y")

        mock_store.ban_tool.assert_called_once_with("tool_y")
        assert result["action"] == "ban"

    @pytest.mark.asyncio
    async def test_delete_preference(self):
        from src.api.routes.reflex_routes import reflex_remove_preference
        from src.services.reflex_preferences import ReflexPreferences

        mock_store = MagicMock()
        mock_store.get.return_value = ReflexPreferences()

        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=True), \
             patch("src.services.reflex_preferences.get_reflex_preferences", return_value=mock_store):
            result = await reflex_remove_preference(tool_id="tool_z")

        mock_store.remove_preference.assert_called_once_with("tool_z")
        assert result["action"] == "remove"

    @pytest.mark.asyncio
    async def test_endpoints_disabled(self):
        from src.api.routes.reflex_routes import reflex_preferences
        with patch("src.api.routes.reflex_routes._is_reflex_enabled", return_value=False):
            result = await reflex_preferences()
        assert result["enabled"] is False
