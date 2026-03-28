"""
MARKER_201.NOTIFY — Agent-to-agent notification tests

Tests:
1. send_notification stores in DB and returns success
2. get_notifications returns unread only by default
3. ack_notifications marks specific notifications as read
4. ack_notifications marks all unread when no IDs given
5. file inbox is written on send (when registry available)
6. get_notifications returns empty for unknown role
7. send_notification rejects missing fields
"""

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def _make_board(tmp_path):
    """Create a TaskBoard with tmp storage."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.orchestration.task_board import TaskBoard
    return TaskBoard(board_file=tmp_path / "board.json")


def _patch_registry(worktree_name=None):
    """Mock agent_registry to return a role with given worktree."""
    mock_module = MagicMock()
    if worktree_name:
        mock_role = MagicMock()
        mock_role.worktree = worktree_name
        mock_registry = MagicMock()
        mock_registry.get_by_callsign.return_value = mock_role
    else:
        mock_registry = MagicMock()
        mock_registry.get_by_callsign.return_value = None
    mock_module.get_agent_registry.return_value = mock_registry
    return patch.dict(sys.modules, {"src.services.agent_registry": mock_module})


# ── Test 1: send stores in DB ────────────────────────────────

def test_send_notification_stores_in_db(tmp_path):
    """send_notification should write to SQLite and return success."""
    board = _make_board(tmp_path)

    with _patch_registry():
        result = board.send_notification(
            source_role="Commander",
            target_role="Alpha",
            message="Focus on hotkeys task",
        )

    assert result["success"] is True
    assert "notification_id" in result
    assert result["target_role"] == "Alpha"


# ── Test 2: get_notifications unread only ─────────────────────

def test_get_notifications_unread_only(tmp_path):
    """get_notifications should return only unread by default."""
    board = _make_board(tmp_path)

    with _patch_registry():
        board.send_notification("Commander", "Alpha", "msg 1")
        board.send_notification("Commander", "Alpha", "msg 2")

    notifs = board.get_notifications("Alpha", unread_only=True)
    assert len(notifs) == 2
    assert notifs[0]["message"] == "msg 2"  # newest first
    assert notifs[1]["message"] == "msg 1"


# ── Test 3: ack specific notifications ────────────────────────

def test_ack_specific_notifications(tmp_path):
    """ack_notifications with IDs should mark only those as read."""
    board = _make_board(tmp_path)

    with _patch_registry():
        r1 = board.send_notification("Commander", "Alpha", "msg 1")
        r2 = board.send_notification("Commander", "Alpha", "msg 2")

    # Ack only the first
    board.ack_notifications("Alpha", notification_ids=[r1["notification_id"]])

    unread = board.get_notifications("Alpha", unread_only=True)
    assert len(unread) == 1
    assert unread[0]["message"] == "msg 2"


# ── Test 4: ack all unread ────────────────────────────────────

def test_ack_all_unread(tmp_path):
    """ack_notifications without IDs should mark all unread for role."""
    board = _make_board(tmp_path)

    with _patch_registry():
        board.send_notification("Commander", "Alpha", "msg 1")
        board.send_notification("Commander", "Alpha", "msg 2")

    board.ack_notifications("Alpha")

    unread = board.get_notifications("Alpha", unread_only=True)
    assert len(unread) == 0

    all_notifs = board.get_notifications("Alpha", unread_only=False)
    assert len(all_notifs) == 2


# ── Test 5: file inbox written on send ────────────────────────

def test_inbox_file_written(tmp_path):
    """send_notification should write a JSON line to .inbox file."""
    # Board file at data/ subdirectory so parent.parent = project root
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.orchestration.task_board import TaskBoard
    board = TaskBoard(board_file=data_dir / "board.json")

    # Create fake worktree directory structure at project root level
    worktree_dir = tmp_path / ".claude" / "worktrees" / "cut-engine"
    worktree_dir.mkdir(parents=True)

    mock_module = MagicMock()
    mock_role = MagicMock()
    mock_role.worktree = "cut-engine"
    mock_registry = MagicMock()
    mock_registry.get_by_callsign.return_value = mock_role
    mock_module.get_agent_registry.return_value = mock_registry

    with patch.dict(sys.modules, {"src.services.agent_registry": mock_module}):
        board.send_notification("Commander", "Alpha", "check hotkeys")

    inbox = worktree_dir / ".inbox"
    assert inbox.exists()
    lines = inbox.read_text().strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["from"] == "Commander"
    assert "hotkeys" in entry["message"]


# ── Test 6: get_notifications empty for unknown role ──────────

def test_no_notifications_for_unknown_role(tmp_path):
    """get_notifications for non-existent role returns empty list."""
    board = _make_board(tmp_path)
    notifs = board.get_notifications("NonexistentAgent")
    assert notifs == []


# ── Test 7: cross-role isolation ──────────────────────────────

def test_cross_role_isolation(tmp_path):
    """Notifications for Alpha shouldn't appear for Beta."""
    board = _make_board(tmp_path)

    with _patch_registry():
        board.send_notification("Commander", "Alpha", "for alpha")
        board.send_notification("Commander", "Beta", "for beta")

    alpha_notifs = board.get_notifications("Alpha")
    beta_notifs = board.get_notifications("Beta")

    assert len(alpha_notifs) == 1
    assert alpha_notifs[0]["message"] == "for alpha"
    assert len(beta_notifs) == 1
    assert beta_notifs[0]["message"] == "for beta"
