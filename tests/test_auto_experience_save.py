"""
MARKER_ZETA.E2: Tests for auto_experience_save.py (session end hook).

Tests:
1. Session with tasks → report saved
2. Session with no work → report NOT saved
3. Unknown branch → saves with callsign empty
4. CORTEX feedback aggregation correct
5. Script exits 0 even on error
6. Dry-run mode prints JSON, no file writes
"""

import json
import time

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.tools.auto_experience_save import (
    auto_save,
    _has_meaningful_work,
    _get_cortex_summary,
    main,
)
from src.services.session_tracker import SessionActionTracker, reset_session_tracker
from src.services.experience_report import reset_experience_store


@pytest.fixture(autouse=True)
def clean_singletons():
    reset_session_tracker()
    reset_experience_store()
    yield
    reset_session_tracker()
    reset_experience_store()


def _populate_session(tracker, sid="test-session"):
    """Create a session with meaningful work."""
    tracker.record_action(sid, "vetka_session_init", {})
    tracker.record_action(sid, "vetka_task_board", {"action": "list"})
    tracker.record_action(sid, "vetka_task_board", {"action": "claim", "task_id": "tb_001"})
    tracker.record_action(sid, "Edit", {"file_path": "src/foo.py"})
    tracker.record_action(sid, "Edit", {"file_path": "src/bar.py"})
    tracker.record_action(sid, "Grep", {"pattern": "test"})
    tracker.record_action(sid, "vetka_task_board", {"action": "complete", "task_id": "tb_001"})


# ── Meaningful Work Detection ───────────────────────────────


class TestMeaningfulWork:
    def test_empty_session_not_meaningful(self):
        assert _has_meaningful_work({"empty": True}) is False

    def test_zero_everything_not_meaningful(self):
        assert _has_meaningful_work({
            "empty": False, "tasks_completed": 0, "edit_count": 0, "search_count": 0
        }) is False

    def test_tasks_completed_is_meaningful(self):
        assert _has_meaningful_work({
            "empty": False, "tasks_completed": 1, "edit_count": 0, "search_count": 0
        }) is True

    def test_edits_is_meaningful(self):
        assert _has_meaningful_work({
            "empty": False, "tasks_completed": 0, "edit_count": 3, "search_count": 0
        }) is True

    def test_searches_is_meaningful(self):
        assert _has_meaningful_work({
            "empty": False, "tasks_completed": 0, "edit_count": 0, "search_count": 5
        }) is True


# ── CORTEX Feedback Aggregation ─────────────────────────────


class TestCortexSummary:
    def test_no_feedback_file(self, tmp_path):
        with patch("src.tools.auto_experience_save._FEEDBACK_LOG", tmp_path / "nonexistent.jsonl"):
            result = _get_cortex_summary()
        assert result["total_calls"] == 0

    def test_feedback_aggregation(self, tmp_path):
        log_file = tmp_path / "feedback.jsonl"
        entries = [
            {"tool_id": "Read", "success": True, "timestamp": time.time()},
            {"tool_id": "Read", "success": True, "timestamp": time.time()},
            {"tool_id": "Read", "success": False, "timestamp": time.time()},
            {"tool_id": "Edit", "success": True, "timestamp": time.time()},
            {"tool_id": "vetka_read_file", "success": False, "timestamp": time.time()},
            {"tool_id": "vetka_read_file", "success": False, "timestamp": time.time()},
        ]
        log_file.write_text("\n".join(json.dumps(e) for e in entries))

        with patch("src.tools.auto_experience_save._FEEDBACK_LOG", log_file):
            result = _get_cortex_summary()

        assert result["total_calls"] == 6
        assert result["success_rate"] == 0.5  # 3/6

        # Top tools sorted by call count
        top = result["top_tools"]
        assert top[0]["tool"] == "Read"
        assert top[0]["calls"] == 3

        # Failed tools (success < 0.5 and >= 2 calls)
        failed = result["failed_tools"]
        assert any(f["tool"] == "vetka_read_file" for f in failed)

    def test_timestamp_filtering(self, tmp_path):
        log_file = tmp_path / "feedback.jsonl"
        old_time = time.time() - 7200  # 2 hours ago
        new_time = time.time()
        entries = [
            {"tool_id": "OldTool", "success": True, "timestamp": old_time},
            {"tool_id": "NewTool", "success": True, "timestamp": new_time},
        ]
        log_file.write_text("\n".join(json.dumps(e) for e in entries))

        with patch("src.tools.auto_experience_save._FEEDBACK_LOG", log_file):
            result = _get_cortex_summary(since_timestamp=new_time - 10)

        # Should only include NewTool
        assert result["total_calls"] == 1
        assert result["top_tools"][0]["tool"] == "NewTool"


# ── Auto Save Integration ──────────────────────────────────


class TestAutoSave:
    def test_session_with_work_saves_report(self, tmp_path):
        from src.services.session_tracker import get_session_tracker
        tracker = get_session_tracker()
        _populate_session(tracker)

        with patch("src.tools.auto_experience_save._detect_branch", return_value="main"), \
             patch("src.services.experience_report._REPORTS_DIR", tmp_path):
            from src.services.experience_report import get_experience_store, reset_experience_store
            reset_experience_store()
            store = get_experience_store(tmp_path)

            path = auto_save()

        assert path is not None
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["session_id"].startswith("auto-")
        assert "src/foo.py" in data["files_touched"] or "src/bar.py" in data["files_touched"]

    def test_session_no_work_skips(self):
        # Empty session tracker — no work
        with patch("src.tools.auto_experience_save._detect_branch", return_value="main"):
            path = auto_save()
        assert path is None

    def test_unknown_branch_saves_with_empty_callsign(self, tmp_path):
        from src.services.session_tracker import get_session_tracker
        tracker = get_session_tracker()
        _populate_session(tracker)

        with patch("src.tools.auto_experience_save._detect_branch", return_value="some/unknown-branch"), \
             patch("src.tools.auto_experience_save._get_role", return_value=None), \
             patch("src.services.experience_report._REPORTS_DIR", tmp_path):
            from src.services.experience_report import reset_experience_store
            reset_experience_store()
            from src.services.experience_report import get_experience_store
            get_experience_store(tmp_path)

            path = auto_save()

        assert path is not None
        data = json.loads(path.read_text())
        assert data["agent_callsign"] == ""
        assert data["domain"] == ""
        assert data["branch"] == "some/unknown-branch"

    def test_dry_run_no_file(self, tmp_path, capsys):
        from src.services.session_tracker import get_session_tracker
        tracker = get_session_tracker()
        _populate_session(tracker)

        with patch("src.tools.auto_experience_save._detect_branch", return_value="main"):
            path = auto_save(dry_run=True)

        assert path is None
        captured = capsys.readouterr()
        assert "session_id" in captured.out  # JSON printed to stdout

    def test_role_detected_from_branch(self, tmp_path):
        from src.services.session_tracker import get_session_tracker
        tracker = get_session_tracker()
        _populate_session(tracker)

        mock_role = MagicMock()
        mock_role.callsign = "Alpha"
        mock_role.domain = "engine"
        mock_role.worktree = "cut-engine"

        with patch("src.tools.auto_experience_save._detect_branch", return_value="claude/cut-engine"), \
             patch("src.tools.auto_experience_save._get_role", return_value=mock_role), \
             patch("src.services.experience_report._REPORTS_DIR", tmp_path):
            from src.services.experience_report import reset_experience_store
            reset_experience_store()
            from src.services.experience_report import get_experience_store
            get_experience_store(tmp_path)

            path = auto_save()

        assert path is not None
        data = json.loads(path.read_text())
        assert data["agent_callsign"] == "Alpha"
        assert data["domain"] == "engine"
        assert "cut-engine" in data["session_id"]


# ── Main Entry Point ────────────────────────────────────────


class TestMain:
    def test_main_exits_0_on_success(self):
        with patch("src.tools.auto_experience_save.auto_save", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_main_exits_0_on_error(self):
        with patch("src.tools.auto_experience_save.auto_save", side_effect=RuntimeError("boom")):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
