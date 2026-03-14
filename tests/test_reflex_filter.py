"""
Tests for REFLEX Active Filter Engine — Phase 173.P1

MARKER_173.P1.TESTS

Tests tier-based filtering, always-include preservation,
preference integration, schema format handling, and feature flags.

T1.1  — Gold tier: no filtering
T1.2  — Silver tier: limits to 15
T1.3  — Bronze tier: limits to 8
T1.4  — Always-include set preserved
T1.5  — Empty tools returns empty
T1.6  — Fewer than limit returns all
T1.7  — Pinned tools always included
T1.8  — Banned tools always excluded
T1.9  — Pinned overrides low score
T1.10 — Banned overrides high score
T1.11 — Schema format (OpenAI dict) preserved
T1.12 — FC schemas passthrough (< limit)
T1.13 — resolve_model_tier: dragon presets
T1.14 — resolve_model_tier: unknown defaults silver
T1.15 — get_tool_id: various formats
T1.16 — REFLEX_ACTIVE=False returns unfiltered
T1.17 — REFLEX_ENABLED=False returns unfiltered
T1.18 — Scoring error falls back to position order
T1.19 — Integration: IP-7 function returns original on error
T1.20 — Integration: _is_active checks both flags
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── Mock tools ──────────────────────────────────────────────────

@dataclass
class MockTool:
    tool_id: str
    active: bool = True
    namespace: str = "vetka"
    kind: str = "file_op"


def _make_tools(n: int) -> list:
    """Generate n mock tools."""
    return [MockTool(f"tool_{i}") for i in range(n)]


def _make_schema(name: str) -> dict:
    """Generate an OpenAI-format tool schema."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Mock tool {name}",
            "parameters": {"type": "object", "properties": {}},
        },
    }


# ─── T1.1-T1.6: Tier-based filtering ────────────────────────────

class TestFilterByTier:
    """T1.1-T1.6: filter_tools tier limits."""

    def test_gold_no_filtering(self):
        """Gold tier passes all tools through (no top-N limit)."""
        from src.services.reflex_filter import filter_tools
        tools = _make_tools(50)
        with patch("src.services.reflex_filter.REFLEX_ACTIVE", True), \
             patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = filter_tools(tools, model_tier="gold")
        assert len(result) == 50

    def test_silver_limits_to_15(self):
        """Silver tier returns at most 15 tools."""
        from src.services.reflex_filter import filter_tools
        tools = _make_tools(30)
        with patch("src.services.reflex_filter.REFLEX_ACTIVE", True), \
             patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = filter_tools(tools, model_tier="silver", always_include=set())
        assert len(result) <= 15

    def test_bronze_limits_to_8(self):
        """Bronze tier returns at most 8 tools."""
        from src.services.reflex_filter import filter_tools
        tools = _make_tools(30)
        with patch("src.services.reflex_filter.REFLEX_ACTIVE", True), \
             patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = filter_tools(tools, model_tier="bronze", always_include=set())
        assert len(result) <= 8

    def test_always_include_preserved(self):
        """Always-include tools survive even with strict filtering."""
        from src.services.reflex_filter import filter_tools, DEFAULT_ALWAYS_INCLUDE
        tools = [MockTool(tid) for tid in DEFAULT_ALWAYS_INCLUDE] + _make_tools(30)
        with patch("src.services.reflex_filter.REFLEX_ACTIVE", True), \
             patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = filter_tools(tools, model_tier="bronze", always_include=DEFAULT_ALWAYS_INCLUDE)
        result_ids = {t.tool_id for t in result}
        for tid in DEFAULT_ALWAYS_INCLUDE:
            assert tid in result_ids

    def test_empty_tools(self):
        """Empty input returns empty output."""
        from src.services.reflex_filter import filter_tools
        result = filter_tools([], model_tier="bronze")
        assert result == []

    def test_fewer_than_limit(self):
        """3 tools with silver limit (15) → all 3 returned."""
        from src.services.reflex_filter import filter_tools
        tools = _make_tools(3)
        with patch("src.services.reflex_filter.REFLEX_ACTIVE", True), \
             patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = filter_tools(tools, model_tier="silver", always_include=set())
        assert len(result) == 3


# ─── T1.7-T1.10: Preference integration ─────────────────────────

class TestFilterWithPreferences:
    """T1.7-T1.10: Pin/ban preference effects."""

    def test_pinned_always_included(self):
        """Pinned tool survives even strict bronze filtering."""
        from src.services.reflex_filter import filter_tools
        from src.services.reflex_preferences import ReflexPreferences
        tools = _make_tools(20)
        tools.append(MockTool("pinned_tool"))
        prefs = ReflexPreferences(pinned_tools={"pinned_tool"})
        with patch("src.services.reflex_filter.REFLEX_ACTIVE", True), \
             patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = filter_tools(tools, model_tier="bronze", preferences=prefs, always_include=set())
        result_ids = {t.tool_id for t in result}
        assert "pinned_tool" in result_ids

    def test_banned_always_excluded(self):
        """Banned tool excluded even from gold tier."""
        from src.services.reflex_filter import filter_tools
        from src.services.reflex_preferences import ReflexPreferences
        tools = [MockTool("good_tool"), MockTool("banned_tool")]
        prefs = ReflexPreferences(banned_tools={"banned_tool"})
        with patch("src.services.reflex_filter.REFLEX_ACTIVE", True), \
             patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = filter_tools(tools, model_tier="gold", preferences=prefs)
        result_ids = {t.tool_id for t in result}
        assert "banned_tool" not in result_ids
        assert "good_tool" in result_ids

    def test_banned_overrides_always_include(self):
        """Ban takes precedence over always-include."""
        from src.services.reflex_filter import filter_tools
        from src.services.reflex_preferences import ReflexPreferences
        tools = [MockTool("vetka_read_file"), MockTool("other")]
        prefs = ReflexPreferences(banned_tools={"vetka_read_file"})
        with patch("src.services.reflex_filter.REFLEX_ACTIVE", True), \
             patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = filter_tools(tools, model_tier="silver", preferences=prefs,
                                  always_include={"vetka_read_file"})
        result_ids = {t.tool_id for t in result}
        assert "vetka_read_file" not in result_ids


# ─── T1.11-T1.12: Schema format ─────────────────────────────────

class TestFilterSchemas:
    """T1.11-T1.12: OpenAI tool schema filtering."""

    def test_schema_format_preserved(self):
        """Output schemas are same format as input."""
        from src.services.reflex_filter import filter_tool_schemas
        schemas = [_make_schema(f"tool_{i}") for i in range(20)]
        with patch("src.services.reflex_filter.REFLEX_ACTIVE", True), \
             patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = filter_tool_schemas(schemas, model_tier="silver", always_include=set())
        assert len(result) <= 15
        for s in result:
            assert "function" in s
            assert "name" in s["function"]

    def test_fc_schemas_passthrough(self):
        """Current 5 FC schemas all pass through (under any limit)."""
        from src.services.reflex_filter import filter_tool_schemas
        schemas = [
            _make_schema("vetka_read_file"),
            _make_schema("vetka_search_semantic"),
            _make_schema("vetka_write_file"),
            _make_schema("vetka_git_status"),
            _make_schema("vetka_apply_patch"),
        ]
        with patch("src.services.reflex_filter.REFLEX_ACTIVE", True), \
             patch("src.services.reflex_scorer.REFLEX_ENABLED", True):
            result = filter_tool_schemas(schemas, model_tier="bronze", always_include=set())
        assert len(result) == 5  # All pass: 5 < 8 (bronze limit)


# ─── T1.13-T1.15: Helpers ───────────────────────────────────────

class TestHelpers:
    """T1.13-T1.15: get_tool_id, resolve_model_tier."""

    def test_resolve_dragon_presets(self):
        from src.services.reflex_filter import resolve_model_tier
        assert resolve_model_tier("dragon_bronze") == "bronze"
        assert resolve_model_tier("dragon_silver") == "silver"
        assert resolve_model_tier("dragon_gold") == "gold"
        assert resolve_model_tier("dragon_gold_gpt") == "gold"

    def test_resolve_unknown_defaults_silver(self):
        from src.services.reflex_filter import resolve_model_tier
        assert resolve_model_tier("custom_preset_v2") == "silver"
        assert resolve_model_tier("") == "silver"

    def test_get_tool_id_from_tool_entry(self):
        from src.services.reflex_filter import get_tool_id
        tool = MockTool("my_tool")
        assert get_tool_id(tool) == "my_tool"

    def test_get_tool_id_from_schema(self):
        from src.services.reflex_filter import get_tool_id
        schema = _make_schema("test_func")
        assert get_tool_id(schema) == "test_func"

    def test_get_tool_id_from_string(self):
        from src.services.reflex_filter import get_tool_id
        assert get_tool_id("plain_string") == "plain_string"


# ─── T1.16-T1.17: Feature flags ─────────────────────────────────

class TestFeatureFlags:
    """T1.16-T1.17: REFLEX_ACTIVE and REFLEX_ENABLED checks."""

    def test_reflex_active_false_returns_unfiltered(self):
        from src.services.reflex_filter import filter_tools
        tools = _make_tools(30)
        with patch("src.services.reflex_filter.REFLEX_ACTIVE", False):
            result = filter_tools(tools, model_tier="bronze")
        assert len(result) == 30  # No filtering

    def test_reflex_enabled_false_returns_unfiltered(self):
        from src.services.reflex_filter import filter_tools
        tools = _make_tools(30)
        with patch("src.services.reflex_filter.REFLEX_ACTIVE", True), \
             patch("src.services.reflex_scorer.REFLEX_ENABLED", False):
            result = filter_tools(tools, model_tier="bronze")
        assert len(result) == 30


# ─── T1.18-T1.20: Error handling & Integration ──────────────────

class TestErrorHandling:
    """T1.18-T1.20: Graceful degradation and integration."""

    def test_scoring_error_falls_back(self):
        """If scorer.score() fails, use position order."""
        from src.services.reflex_filter import filter_tools
        tools = _make_tools(20)
        mock_scorer = MagicMock()
        mock_scorer.score.side_effect = RuntimeError("scorer crash")

        with patch("src.services.reflex_filter.REFLEX_ACTIVE", True), \
             patch("src.services.reflex_scorer.REFLEX_ENABLED", True), \
             patch("src.services.reflex_scorer.get_reflex_scorer", return_value=mock_scorer):
            result = filter_tools(tools, context=MagicMock(), model_tier="bronze", always_include=set())
        # Should still return 8 tools (bronze limit), just position-ordered
        assert len(result) == 8

    def test_ip7_returns_original_on_error(self):
        """IP-7 integration function returns original schemas on error."""
        from src.services.reflex_integration import reflex_filter_schemas
        schemas = [_make_schema(f"tool_{i}") for i in range(5)]
        with patch("src.services.reflex_integration._is_active", return_value=True), \
             patch("src.services.reflex_filter.filter_tool_schemas", side_effect=RuntimeError("boom")):
            result = reflex_filter_schemas(schemas)
        assert len(result) == 5  # Original returned on error

    def test_is_active_checks_both_flags(self):
        """_is_active requires both REFLEX_ENABLED and REFLEX_ACTIVE."""
        from src.services.reflex_integration import _is_active
        with patch("src.services.reflex_integration._is_enabled", return_value=True), \
             patch("src.services.reflex_filter.REFLEX_ACTIVE", True):
            assert _is_active() is True

        with patch("src.services.reflex_integration._is_enabled", return_value=False), \
             patch("src.services.reflex_filter.REFLEX_ACTIVE", True):
            assert _is_active() is False

        with patch("src.services.reflex_integration._is_enabled", return_value=True), \
             patch("src.services.reflex_filter.REFLEX_ACTIVE", False):
            assert _is_active() is False
