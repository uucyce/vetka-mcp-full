"""
Phase 193.3 — REFLEX Feedback Guard test suite (10 tests).

Tests the FeedbackGuard layer that blocks/warns dangerous tool calls
based on ENGRAM L1 danger entries, CORTEX failure history, and static rules.

MARKER_193.3
@task tb_1773887692_3
"""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

from src.memory.engram_cache import EngramCache, EngramEntry

# ── Imports from new modules (Agent A / Agent B build in parallel) ──
from src.services.reflex_guard import (
    FeedbackGuard,
    DangerRule,
    GuardContext,
    GuardResult,
    get_feedback_guard,
)


# ════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════

@pytest.fixture
def tmp_cache(tmp_path):
    """Fresh EngramCache writing to tmp dir."""
    cache_path = tmp_path / "engram_cache.json"
    cache = EngramCache(cache_path=cache_path)
    return cache


@pytest.fixture
def tmp_rules_file(tmp_path):
    """Static rules JSON file with one user-defined rule."""
    rules = [
        {
            "tool_pattern": "preview_start",
            "context_pattern": "CUT",
            "reason": "Never use preview for CUT — causes hang",
            "source": "user_feedback",
            "severity": "block",
        }
    ]
    rules_path = tmp_path / "reflex_guard_rules.json"
    rules_path.write_text(json.dumps(rules, indent=2))
    return rules_path


@pytest.fixture
def guard_with_rules(tmp_cache, tmp_rules_file):
    """FeedbackGuard initialized with tmp cache + static rules file."""
    with patch("src.services.reflex_guard.CACHE_PATH", tmp_cache._path), \
         patch("src.services.reflex_guard.RULES_PATH", tmp_rules_file):
        guard = FeedbackGuard()
    return guard


@pytest.fixture
def danger_rule_block():
    """A blocking DangerRule for preview_start in CUT context."""
    return DangerRule(
        tool_pattern="preview_start",
        context_pattern="CUT",
        reason="Never use preview for CUT",
        source="engram_l1",
        severity="block",
        created_at=time.time(),
    )


@pytest.fixture
def danger_rule_warn():
    """A warning DangerRule for search_files (low success)."""
    return DangerRule(
        tool_pattern="search_files",
        context_pattern="*",
        reason="search_files success rate 15% (3+ calls)",
        source="cortex_failure",
        severity="warn",
        created_at=time.time(),
    )


@pytest.fixture
def guard_context_cut():
    """GuardContext for CUT phase."""
    return GuardContext(agent_type="claude_code", phase_type="CUT", project_id="vetka")


@pytest.fixture
def guard_context_pulse():
    """GuardContext for PULSE phase."""
    return GuardContext(agent_type="claude_code", phase_type="PULSE", project_id="vetka")


# ════════════════════════════════════════════════════════════════
# W1 — 10 Core Tests
# ════════════════════════════════════════════════════════════════

class TestReflexGuardW1:
    """Wave 1: Core Feedback Guard tests (10 tests)."""

    # ── 1. Guard blocks danger tool ──
    def test_guard_blocks_danger_tool(self, guard_context_cut, danger_rule_block):
        """Tool with danger ENGRAM entry is blocked."""
        guard = FeedbackGuard.__new__(FeedbackGuard)
        guard._danger_rules = [danger_rule_block]
        guard._failure_thresholds = {}

        result = guard.check_tool("preview_start", guard_context_cut)

        assert isinstance(result, GuardResult)
        assert result.allowed is False
        assert "preview" in result.blocked_reason.lower() or "CUT" in result.blocked_reason
        print("✅ test_guard_blocks_danger_tool")

    # ── 2. Guard warns low-success tool ──
    def test_guard_warns_low_success_tool(self, guard_context_cut, danger_rule_warn):
        """Tool with <20% success rate gets warning but is allowed."""
        guard = FeedbackGuard.__new__(FeedbackGuard)
        guard._danger_rules = [danger_rule_warn]
        guard._failure_thresholds = {}

        result = guard.check_tool("search_files", guard_context_cut)

        assert result.allowed is True
        assert len(result.warnings) > 0
        assert any("success rate" in w.lower() or "15%" in w for w in result.warnings)
        print("✅ test_guard_warns_low_success_tool")

    # ── 3. Guard allows safe tool ──
    def test_guard_allows_safe_tool(self, guard_context_cut, danger_rule_block):
        """Normal tool with no matching danger rule passes through."""
        guard = FeedbackGuard.__new__(FeedbackGuard)
        guard._danger_rules = [danger_rule_block]
        guard._failure_thresholds = {}

        result = guard.check_tool("vetka_read_file", guard_context_cut)

        assert result.allowed is True
        assert len(result.warnings) == 0
        assert result.blocked_reason == ""
        print("✅ test_guard_allows_safe_tool")

    # ── 4. Filter recommendations removes blocked ──
    def test_filter_recommendations_removes_blocked(
        self, guard_context_cut, danger_rule_block
    ):
        """Blocked tools are removed/marked in filtered recommendation list."""
        guard = FeedbackGuard.__new__(FeedbackGuard)
        guard._danger_rules = [danger_rule_block]
        guard._failure_thresholds = {}

        recs = [
            {"tool_id": "preview_start", "score": 0.87, "reason": "semantic match"},
            {"tool_id": "vetka_read_file", "score": 0.72, "reason": "recent use"},
        ]

        filtered = guard.filter_recommendations(recs, guard_context_cut)

        # Blocked tool should be marked blocked or removed
        tool_ids = [r["tool_id"] for r in filtered if not r.get("blocked")]
        assert "preview_start" not in tool_ids
        # Safe tool remains
        assert any(r["tool_id"] == "vetka_read_file" for r in filtered)
        print("✅ test_filter_recommendations_removes_blocked")

    # ── 5. Filter recommendations adds warnings ──
    def test_filter_recommendations_adds_warnings(
        self, guard_context_cut, danger_rule_warn
    ):
        """Warned tools get a 'warning' field in recommendations."""
        guard = FeedbackGuard.__new__(FeedbackGuard)
        guard._danger_rules = [danger_rule_warn]
        guard._failure_thresholds = {}

        recs = [
            {"tool_id": "search_files", "score": 0.65, "reason": "match"},
            {"tool_id": "vetka_read_file", "score": 0.72, "reason": "recent"},
        ]

        filtered = guard.filter_recommendations(recs, guard_context_cut)

        search_rec = next(r for r in filtered if r["tool_id"] == "search_files")
        assert "warning" in search_rec
        assert search_rec["warning"]  # non-empty

        safe_rec = next(r for r in filtered if r["tool_id"] == "vetka_read_file")
        assert not safe_rec.get("warning")
        print("✅ test_filter_recommendations_adds_warnings")

    # ── 6. Danger rule glob matching ──
    def test_danger_rule_glob_matching(self, guard_context_cut):
        """Glob pattern 'preview_*' matches 'preview_start' and 'preview_stop'."""
        glob_rule = DangerRule(
            tool_pattern="preview_*",
            context_pattern="CUT",
            reason="All preview tools blocked for CUT",
            source="user_feedback",
            severity="block",
            created_at=time.time(),
        )
        guard = FeedbackGuard.__new__(FeedbackGuard)
        guard._danger_rules = [glob_rule]
        guard._failure_thresholds = {}

        # preview_start should match
        r1 = guard.check_tool("preview_start", guard_context_cut)
        assert r1.allowed is False

        # preview_stop should match
        r2 = guard.check_tool("preview_stop", guard_context_cut)
        assert r2.allowed is False

        # vetka_preview should NOT match (prefix mismatch)
        r3 = guard.check_tool("vetka_preview", guard_context_cut)
        assert r3.allowed is True
        print("✅ test_danger_rule_glob_matching")

    # ── 7. Static rules loaded from JSON ──
    def test_static_rules_loaded(self, tmp_rules_file):
        """Rules from static JSON file are loaded into guard."""
        with patch("src.services.reflex_guard.RULES_PATH", tmp_rules_file), \
             patch("src.services.reflex_guard.get_engram_cache") as mock_cache:
            mock_cache.return_value = MagicMock(get_all=MagicMock(return_value={}))
            guard = FeedbackGuard()

        # Should have at least the one rule from the JSON file
        static_rules = [r for r in guard._danger_rules if r.source == "user_feedback"]
        assert len(static_rules) >= 1
        assert static_rules[0].tool_pattern == "preview_start"
        assert static_rules[0].context_pattern == "CUT"
        assert static_rules[0].severity == "block"
        print("✅ test_static_rules_loaded")

    # ── 8. Context pattern matching ──
    def test_context_pattern_matching(
        self, danger_rule_block, guard_context_cut, guard_context_pulse
    ):
        """Rule for 'CUT' context doesn't block the same tool in 'PULSE'."""
        guard = FeedbackGuard.__new__(FeedbackGuard)
        guard._danger_rules = [danger_rule_block]
        guard._failure_thresholds = {}

        # CUT context → blocked
        r_cut = guard.check_tool("preview_start", guard_context_cut)
        assert r_cut.allowed is False

        # PULSE context → allowed (rule is CUT-specific)
        r_pulse = guard.check_tool("preview_start", guard_context_pulse)
        assert r_pulse.allowed is True
        print("✅ test_context_pattern_matching")

    # ── 9. ENGRAM danger collector ──
    def test_engram_danger_collector(self, tmp_cache):
        """get_danger_entries() returns only danger-category entries."""
        # Put a mix of categories
        tmp_cache.put("k1::f::a::p", "danger tool advice", category="danger")
        tmp_cache.put("k2::f::a::p", "pattern advice", category="pattern")
        tmp_cache.put("k3::f::a::p", "another danger", category="danger")
        tmp_cache.put("k4::f::a::p", "default advice", category="default")

        danger_entries = tmp_cache.get_danger_entries()

        assert len(danger_entries) == 2
        assert all(e.category == "danger" for e in danger_entries)
        keys = {e.key for e in danger_entries}
        assert "k1::f::a::p" in keys
        assert "k3::f::a::p" in keys
        print("✅ test_engram_danger_collector")

    # ── 10. Session init includes warnings ──
    def test_session_init_includes_warnings(self):
        """Mocked session_init response contains reflex_warnings and blocked_tools."""
        mock_guard = MagicMock()
        mock_guard.get_active_dangers.return_value = [
            DangerRule(
                tool_pattern="preview_start",
                context_pattern="CUT",
                reason="Failed 5/5 times for CUT",
                source="cortex_failure",
                severity="block",
                created_at=time.time(),
            )
        ]
        mock_guard.filter_recommendations.return_value = [
            {
                "tool_id": "vetka_read_file",
                "score": 0.72,
                "reason": "recent use",
            },
            {
                "tool_id": "preview_start",
                "score": 0.87,
                "reason": "semantic match",
                "blocked": True,
                "warning": "Failed 5/5 times for CUT",
            },
        ]

        with patch("src.services.reflex_guard.get_feedback_guard", return_value=mock_guard):
            guard = get_feedback_guard()
            dangers = guard.get_active_dangers(agent_type="claude_code", phase_type="CUT")
            recs = guard.filter_recommendations([], GuardContext(
                agent_type="claude_code", phase_type="CUT", project_id="vetka"
            ))

        # Verify blocked_tools derivable from guard output
        blocked = [r for r in recs if r.get("blocked")]
        assert len(blocked) == 1
        assert blocked[0]["tool_id"] == "preview_start"
        assert "5/5" in blocked[0]["warning"]

        # Verify dangers list
        assert len(dangers) == 1
        assert dangers[0].tool_pattern == "preview_start"
        assert dangers[0].source == "cortex_failure"
        print("✅ test_session_init_includes_warnings")
