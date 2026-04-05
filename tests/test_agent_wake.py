"""MARKER_200.AGENT_WAKE: Tests for notification inbox system.

Tests:
1. notify → creates record in SQLite
2. get_notifications → returns unread
3. ack_notifications → marks as read
4. verify verdict=pass → auto-notifies owner + Commander
5. complete_task → auto-notifies Commander
6. session_init integration → notifications appear in context
"""

import os
import sys
import sqlite3
import tempfile
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def board():
    """Create a TaskBoard with a temporary SQLite database."""
    from src.orchestration.task_board import TaskBoard

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        b = TaskBoard.__new__(TaskBoard)
        b.db = sqlite3.connect(db_path, check_same_thread=False)
        b.db.row_factory = sqlite3.Row
        b.db.execute("PRAGMA journal_mode=WAL")
        b.tasks = {}
        b.settings = {}
        b._file_path = db_path
        b._ensure_schema()
        b._run_migrations()
        yield b
    finally:
        b.db.close()
        os.unlink(db_path)


class TestNotificationCRUD:
    """Test basic notify → read → ack lifecycle."""

    def test_notify_creates_record(self, board):
        result = board.notify("Alpha", "Fix the bug", ntype="task_needs_fix", source_role="Delta")
        assert result["success"] is True
        assert result["notification_id"].startswith("notif_")

    def test_get_notifications_unread(self, board):
        board.notify("Alpha", "Message 1", source_role="Delta")
        board.notify("Alpha", "Message 2", source_role="Zeta")
        board.notify("Beta", "Not for Alpha", source_role="Delta")

        notifs = board.get_notifications("Alpha", unread_only=True)
        assert len(notifs) == 2
        assert all(n["target_role"] == "Alpha" for n in notifs)
        assert all(n["read_at"] is None for n in notifs)

    def test_ack_all_unread(self, board):
        board.notify("Alpha", "Msg 1", source_role="Delta")
        board.notify("Alpha", "Msg 2", source_role="Zeta")

        result = board.ack_notifications("Alpha")
        assert result["success"] is True
        assert result["acked"] == 2

        # After ack, no unread
        notifs = board.get_notifications("Alpha", unread_only=True)
        assert len(notifs) == 0

        # But all still visible with unread_only=False
        notifs = board.get_notifications("Alpha", unread_only=False)
        assert len(notifs) == 2

    def test_ack_specific_ids(self, board):
        r1 = board.notify("Alpha", "Msg 1", source_role="Delta")
        r2 = board.notify("Alpha", "Msg 2", source_role="Zeta")

        board.ack_notifications("Alpha", notification_ids=[r1["notification_id"]])

        notifs = board.get_notifications("Alpha", unread_only=True)
        assert len(notifs) == 1
        assert notifs[0]["id"] == r2["notification_id"]

    def test_role_isolation(self, board):
        """Cannot ack another role's notifications."""
        board.notify("Alpha", "Secret", source_role="Delta")
        result = board.ack_notifications("Beta")  # Wrong role
        assert result["acked"] == 0

        # Alpha's notification still unread
        notifs = board.get_notifications("Alpha", unread_only=True)
        assert len(notifs) == 1


class TestAutoNotify:
    """Test that status transitions auto-create notifications."""

    def _add_task(self, board, task_id="tb_test_1", role="Alpha", status="need_qa"):
        task = {
            "id": task_id,
            "title": "Test task for wake",
            "description": "",
            "priority": 2,
            "status": status,
            "phase_type": "fix",
            "complexity": "low",
            "project_id": "CUT",
            "assigned_to": role,
            "agent_type": "claude_code",
            "assigned_at": "",
            "created_by": "test",
            "created_at": "2026-03-27T12:00:00",
            "started_at": "",
            "completed_at": "",
            "closed_at": "",
            "commit_hash": "",
            "commit_message": "",
            "extra": "{}",
            "updated_at": "",
            "role": role,
            "status_history": [],
            "verification_agent": "",
        }
        board.tasks[task_id] = task
        board._save_task(task)
        return task

    def test_verify_pass_notifies_owner_and_commander(self, board):
        self._add_task(board, status="need_qa", role="Alpha")
        board.verify_task("tb_test_1", "pass", notes="LGTM", verified_by="Delta")

        # Alpha should get "task verified"
        alpha_notifs = board.get_notifications("Alpha", unread_only=True)
        assert len(alpha_notifs) >= 1
        assert any("verified" in n["message"].lower() for n in alpha_notifs)

        # Commander should get "ready to merge"
        cmd_notifs = board.get_notifications("Commander", unread_only=True)
        assert len(cmd_notifs) >= 1
        assert any("merge" in n["message"].lower() or "verified" in n["message"].lower() for n in cmd_notifs)

    def test_verify_fail_notifies_owner(self, board):
        self._add_task(board, status="need_qa", role="Gamma")
        board.verify_task("tb_test_1", "fail", notes="Monochrome violation", verified_by="Delta")

        gamma_notifs = board.get_notifications("Gamma", unread_only=True)
        assert len(gamma_notifs) >= 1
        assert any("fix" in n["message"].lower() for n in gamma_notifs)

    def test_notify_with_task_id(self, board):
        board.notify("Commander", "Merge ready", ntype="ready_to_merge", task_id="tb_123")
        notifs = board.get_notifications("Commander")
        assert notifs[0]["task_id"] == "tb_123"


class TestSynapseWakeJSONL:
    """MARKER_209: Verify _synapse_wake writes JSONL audit log."""

    def test_wake_debounce_logs_jsonl(self, board, tmp_path):
        """Debounce path should write a JSONL record with outcome='debounce'."""
        import json as _json

        log_file = tmp_path / "synapse_wake_audit.jsonl"
        ts_file = tmp_path / "synapse_wake_TestRole.ts"

        # Simulate a recent wake (touch timestamp file)
        ts_file.touch()

        # Patch class attrs and Path to use tmp_path
        original_log = board._WAKE_LOG
        original_cooldown = board._WAKE_COOLDOWN_SECS
        board._WAKE_LOG = log_file
        board._WAKE_COOLDOWN_SECS = 9999  # ensure debounce triggers

        try:
            # Monkey-patch Path so /tmp/synapse_wake_TestRole.ts resolves to tmp_path
            import unittest.mock as mock
            with mock.patch("src.orchestration.task_board.Path") as MockPath:
                MockPath.return_value = ts_file
                # Make f-string Path(f"/tmp/...") return our ts_file
                MockPath.side_effect = lambda p: ts_file if "synapse_wake_" in str(p) else Path(p)
                board._synapse_wake("TestRole", "hello")
        finally:
            board._WAKE_LOG = original_log
            board._WAKE_COOLDOWN_SECS = original_cooldown

        assert log_file.exists(), "JSONL audit log should be created"
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        record = _json.loads(lines[0])
        assert record["role"] == "TestRole"
        assert record["outcome"] == "debounce"
        assert record["message"] == "hello"
        assert "ts" in record

    def test_wake_tmux_logs_jsonl(self, board, tmp_path):
        """tmux path should write a JSONL record with outcome='tmux'."""
        import json as _json
        import unittest.mock as mock

        log_file = tmp_path / "synapse_wake_audit.jsonl"
        ts_file = tmp_path / "synapse_wake_Agent.ts"

        original_log = board._WAKE_LOG
        board._WAKE_LOG = log_file

        try:
            with mock.patch("src.orchestration.task_board.Path") as MockPath:
                MockPath.side_effect = lambda p: ts_file if "synapse_wake_" in str(p) else Path(p)
                with mock.patch("subprocess.run") as mock_run:
                    # tmux has-session succeeds, send-keys succeeds
                    mock_run.return_value = mock.Mock(returncode=0)
                    board._synapse_wake("Agent", "wake up")
        finally:
            board._WAKE_LOG = original_log

        assert log_file.exists()
        record = _json.loads(log_file.read_text().strip())
        assert record["outcome"] == "tmux"
        assert record["role"] == "Agent"


class TestMigration:
    """Test that migration 2 creates notifications table."""

    def test_notifications_table_exists(self, board):
        row = board.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='notifications'"
        ).fetchone()
        assert row is not None

    def test_schema_version_is_2(self, board):
        version = board._get_schema_version()
        assert version >= 2
