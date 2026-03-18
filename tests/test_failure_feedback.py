"""Tests for failure feedback loops (Phase 187.12).

MARKER_187.12: Pipeline failure → STM boost + CORTEX record + ENGRAM warnings.
"""

import time
import pytest
from unittest.mock import patch, MagicMock

from src.memory.failure_feedback import (
    record_failure_feedback,
    record_recovery_feedback,
    _feed_stm,
    _feed_cortex,
    _check_engram_warnings,
    _recent_failures,
    _COOLDOWN_SECONDS,
)


@pytest.fixture(autouse=True)
def clear_cooldown():
    """Clear anti-spam cooldown between tests."""
    _recent_failures.clear()
    yield
    _recent_failures.clear()


class TestSTMFeed:
    def test_critical_failure_high_weight(self):
        result = _feed_stm("task1", "timeout error", "critical", "gold", None)
        assert result["status"] == "ok"
        assert result["weight"] == 2.0
        assert result["surprise"] == 0.9

    def test_minor_failure_low_weight(self):
        result = _feed_stm("task2", "lint warning", "minor", "bronze", None)
        assert result["status"] == "ok"
        assert result["weight"] == 1.2
        assert result["surprise"] == 0.4

    def test_with_subtask_context(self):
        result = _feed_stm("task3", "parse error", "major", "silver", "editing scorer.py")
        assert result["status"] == "ok"


class TestCORTEXFeed:
    def test_records_failed_tools(self):
        result = _feed_cortex(["vetka_edit_file", "vetka_search_files"], "fix", "task1")
        assert result["recorded"] == 2

    def test_empty_tools_records_nothing(self):
        result = _feed_cortex([], "build", "task1")
        assert result["recorded"] == 0


class TestENGRAMWarnings:
    def test_no_warnings_for_unknown_tools(self):
        result = _check_engram_warnings(["unknown_tool"])
        assert result["warnings"] == 0


class TestAntiSpam:
    def test_first_call_passes(self):
        result = record_failure_feedback("task1", "error1")
        assert "skipped" not in result

    def test_duplicate_call_within_cooldown_skipped(self):
        record_failure_feedback("task1", "error1", attempt=1)
        result = record_failure_feedback("task1", "error1", attempt=1)
        assert result.get("skipped") is True

    def test_different_attempt_passes(self):
        record_failure_feedback("task1", "error1", attempt=1)
        result = record_failure_feedback("task1", "error2", attempt=2)
        assert "skipped" not in result

    def test_different_task_passes(self):
        record_failure_feedback("task1", "error1")
        result = record_failure_feedback("task2", "error2")
        assert "skipped" not in result


class TestRecoveryFeedback:
    def test_recovery_returns_result(self):
        result = record_recovery_feedback("task1", "fixed the bug")
        assert "task_id" in result


class TestFullPipeline:
    def test_full_failure_feedback(self):
        """End-to-end: record failure, verify all subsystems touched."""
        result = record_failure_feedback(
            task_id="tb_test_123",
            error_summary="Verifier rejected: missing type annotations",
            failed_tools=["vetka_edit_file"],
            tier_used="silver",
            phase_type="fix",
            attempt=1,
            severity="major",
        )
        assert result["task_id"] == "tb_test_123"
        assert result["stm"]["status"] == "ok"
        assert result["stm"]["weight"] == 1.5
        assert result["cortex"]["recorded"] == 1
        assert "warnings" in result["engram"]
