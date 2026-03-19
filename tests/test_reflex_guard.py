"""
Tests for REFLEX Guard — Phase 193.1 + Phase 195.5 (freshness clearance).

MARKER_195.5.TEST
"""

import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.services.reflex_guard import (
    FeedbackGuard,
    DangerRule,
    GuardContext,
    GuardResult,
    _FAILURE_MIN_CALLS,
    _FAILURE_MAX_SUCCESS_RATE,
)


@pytest.fixture
def guard():
    """Create a FeedbackGuard with mocked CORTEX cache."""
    g = FeedbackGuard()
    # Pre-populate CORTEX cache so we don't hit real feedback log
    g._cortex_cache = {
        "vetka_read_file": {"count": 59, "success_rate": 0.0},
        "vetka_edit_file": {"count": 30, "success_rate": 0.05},
        "vetka_search": {"count": 20, "success_rate": 0.8},
    }
    g._cortex_cache_ts = time.time()  # Fresh cache
    return g


class TestCheckCortexFailures:
    """Test _check_cortex_failures with and without freshness."""

    def test_warns_on_low_success_rate(self, guard):
        """Tool with 0% success over 59 calls → warning."""
        ctx = GuardContext()
        rule = guard._check_cortex_failures("vetka_read_file", ctx)
        assert rule is not None
        assert rule.severity == "warn"
        assert rule.source == "cortex_failure"
        assert "0%" in rule.reason

    def test_no_warn_on_good_tool(self, guard):
        """Tool with 80% success → no warning."""
        ctx = GuardContext()
        rule = guard._check_cortex_failures("vetka_search", ctx)
        assert rule is None

    def test_no_warn_on_unknown_tool(self, guard):
        """Tool not in CORTEX cache → no warning."""
        ctx = GuardContext()
        rule = guard._check_cortex_failures("unknown_tool", ctx)
        assert rule is None


class TestFreshnessClearance:
    """T4: MARKER_195.5 — Suppress warnings for recently-updated tools."""

    def teardown_method(self):
        import src.services.tool_source_watch as tsw_mod
        tsw_mod._watch_instance = None

    def test_fresh_tool_no_warning(self, guard):
        """Tool with 0% success but updated <48h ago → no warning."""
        from src.services.tool_source_watch import ToolFreshnessEntry
        import src.services.tool_source_watch as tsw_mod

        freshness = ToolFreshnessEntry(
            source_files=["src/mcp/tools/read_file_tool.py"],
            current_epoch=1,
            updated_at=datetime.now(timezone.utc).isoformat(),
            history=[
                {"epoch": 0, "commit": "old", "ts": "2026-03-01T00:00:00+00:00"},
                {"epoch": 1, "commit": "new", "ts": datetime.now(timezone.utc).isoformat()},
            ],
        )

        mock_watch = MagicMock()
        mock_watch.get.return_value = freshness
        tsw_mod._watch_instance = mock_watch

        ctx = GuardContext()
        rule = guard._check_cortex_failures("vetka_read_file", ctx)
        assert rule is None, "Fresh tool should not get cortex_failure warning"

    def test_stale_tool_still_warned(self, guard):
        """Tool with 0% success and NOT recently updated → warning persists."""
        from src.services.tool_source_watch import ToolFreshnessEntry
        import src.services.tool_source_watch as tsw_mod

        old_time = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        freshness = ToolFreshnessEntry(
            source_files=["src/mcp/tools/read_file_tool.py"],
            current_epoch=1,
            updated_at=old_time,
            history=[
                {"epoch": 0, "commit": "old", "ts": "2026-03-01T00:00:00+00:00"},
                {"epoch": 1, "commit": "new", "ts": old_time},
            ],
        )

        mock_watch = MagicMock()
        mock_watch.get.return_value = freshness
        tsw_mod._watch_instance = mock_watch

        ctx = GuardContext()
        rule = guard._check_cortex_failures("vetka_read_file", ctx)
        assert rule is not None, "Stale tool should still get warning"
        assert rule.source == "cortex_failure"

    def test_epoch_zero_not_fresh(self, guard):
        """Tool at epoch 0 (initial discovery) should NOT be considered fresh."""
        from src.services.tool_source_watch import ToolFreshnessEntry
        import src.services.tool_source_watch as tsw_mod

        freshness = ToolFreshnessEntry(
            source_files=["src/mcp/tools/read_file_tool.py"],
            current_epoch=0,
            updated_at=datetime.now(timezone.utc).isoformat(),
            history=[
                {"epoch": 0, "commit": "init", "ts": datetime.now(timezone.utc).isoformat()},
            ],
        )

        mock_watch = MagicMock()
        mock_watch.get.return_value = freshness
        tsw_mod._watch_instance = mock_watch

        ctx = GuardContext()
        rule = guard._check_cortex_failures("vetka_read_file", ctx)
        assert rule is not None, "Epoch 0 should not suppress warnings"

    def test_no_freshness_data_no_change(self, guard):
        """Without freshness data, warning behavior unchanged."""
        import src.services.tool_source_watch as tsw_mod

        mock_watch = MagicMock()
        mock_watch.get.return_value = None
        tsw_mod._watch_instance = mock_watch

        ctx = GuardContext()
        rule = guard._check_cortex_failures("vetka_read_file", ctx)
        assert rule is not None, "No freshness data → warning should persist"


class TestDangerRuleMatching:
    """Basic DangerRule matching tests."""

    def test_exact_match(self):
        rule = DangerRule(
            tool_pattern="vetka_read_file",
            context_pattern="*",
            reason="test",
            source="test",
        )
        assert rule.matches_tool("vetka_read_file")
        assert not rule.matches_tool("vetka_edit_file")

    def test_glob_match(self):
        rule = DangerRule(
            tool_pattern="vetka_*",
            context_pattern="*",
            reason="test",
            source="test",
        )
        assert rule.matches_tool("vetka_read_file")
        assert rule.matches_tool("vetka_edit_file")
        assert not rule.matches_tool("mycelium_task_board")
