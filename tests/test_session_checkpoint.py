"""
MARKER_200.CHECKPOINT + MARKER_200.DECISIONS: Tests for SessionTracker disk
persistence and decision capture to ENGRAM.
"""

import json
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.services.session_tracker import (
    SessionActionTracker,
    SessionActions,
    _CHECKPOINT_DIR,
)


@pytest.fixture
def tracker():
    """Fresh tracker instance (not the global singleton)."""
    return SessionActionTracker()


@pytest.fixture
def tmp_checkpoint_dir(tmp_path):
    """Redirect checkpoint writes to a temp dir."""
    with patch("src.services.session_tracker._CHECKPOINT_DIR", tmp_path):
        yield tmp_path


class TestSaveCheckpoint:
    """save_checkpoint writes structured JSON to disk."""

    def test_saves_file(self, tracker, tmp_checkpoint_dir):
        sid = "test-session-1"
        tracker.record_action(sid, "vetka_session_init", {})
        session = tracker.get_session(sid)
        session.role_callsign = "Alpha"
        session.role_domain = "engine"
        session.role_branch = "claude/cut-engine"
        session.claimed_task_id = "tb_123"
        session.task_claimed = True
        session.files_edited.add("src/foo.py")
        session.files_read.add("src/bar.py")

        path = tracker.save_checkpoint(
            sid,
            task_title="Fix something",
            completion_contract=["Tests pass", "No console errors"],
        )

        assert path is not None
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["format"] == "hermes_7s_v1"
        assert data["goal"]["claimed_task_id"] == "tb_123"
        assert data["goal"]["task_title"] == "Fix something"
        assert data["constraints"]["role"] == "Alpha"
        assert data["constraints"]["domain"] == "engine"
        assert data["progress"]["files_edited"] == 1
        assert data["progress"]["files_read"] == 1
        assert "src/foo.py" in data["files"]["edited"]
        assert data["next_steps"] == ["Tests pass", "No console errors"]
        assert data["protocol"]["session_init"] is True
        assert data["protocol"]["task_claimed"] is True

    def test_no_session_returns_none(self, tracker, tmp_checkpoint_dir):
        path = tracker.save_checkpoint("nonexistent")
        assert path is None

    def test_decisions_included(self, tracker, tmp_checkpoint_dir):
        sid = "test-decisions"
        tracker.record_action(sid, "vetka_session_init", {})
        session = tracker.get_session(sid)
        session.role_callsign = "Zeta"

        path = tracker.save_checkpoint(
            sid,
            decisions=["Use JEPA not HERMES", "Skip ELYSIA integration"],
        )

        data = json.loads(path.read_text())
        assert len(data["decisions"]) == 2
        assert "JEPA" in data["decisions"][0]

    def test_filename_uses_callsign(self, tracker, tmp_checkpoint_dir):
        sid = "test-name"
        session = tracker.get_session(sid)
        session.role_callsign = "Beta"

        path = tracker.save_checkpoint(sid)
        assert path.name == "session_checkpoint_beta.json"


class TestLoadCheckpoint:
    """load_checkpoint reads and validates checkpoint from disk."""

    def test_loads_existing(self, tracker, tmp_checkpoint_dir):
        sid = "test-load"
        session = tracker.get_session(sid)
        session.role_callsign = "Alpha"
        session.claimed_task_id = "tb_456"
        tracker.save_checkpoint(sid, task_title="Build something")

        with patch("src.services.session_tracker._CHECKPOINT_DIR", tmp_checkpoint_dir):
            loaded = SessionActionTracker.load_checkpoint("Alpha")

        assert loaded is not None
        assert loaded["goal"]["claimed_task_id"] == "tb_456"

    def test_returns_none_if_missing(self, tmp_checkpoint_dir):
        with patch("src.services.session_tracker._CHECKPOINT_DIR", tmp_checkpoint_dir):
            loaded = SessionActionTracker.load_checkpoint("Nonexistent")
        assert loaded is None

    def test_expires_old_checkpoints(self, tracker, tmp_checkpoint_dir):
        sid = "test-expire"
        session = tracker.get_session(sid)
        session.role_callsign = "Gamma"
        tracker.save_checkpoint(sid)

        # Manually set checkpoint_at to 3 hours ago
        path = tmp_checkpoint_dir / "session_checkpoint_gamma.json"
        data = json.loads(path.read_text())
        old_time = time.strftime(
            "%Y-%m-%dT%H:%M:%S+0000",
            time.gmtime(time.time() - 10800),  # 3 hours ago
        )
        data["checkpoint_at"] = old_time
        path.write_text(json.dumps(data))

        with patch("src.services.session_tracker._CHECKPOINT_DIR", tmp_checkpoint_dir):
            loaded = SessionActionTracker.load_checkpoint("Gamma")
        assert loaded is None  # Expired


class TestDecisionCapture:
    """MARKER_200.DECISIONS: decisions at action=complete route to ENGRAM L1."""

    def test_decisions_routed_to_engram(self):
        """_inject_debrief routes decisions to ENGRAM with architecture category."""
        from src.mcp.tools.task_board_tools import _inject_debrief

        mock_engram = MagicMock()
        mock_engram.put.return_value = True

        result = {"success": True, "task_id": "tb_test_123"}
        arguments = {
            "task_id": "tb_test_123",
            "role": "Alpha",
            "domain": "engine",
            "decisions": [
                "Use JEPA Context Packing instead of HERMES LLM",
                "Skip ELYSIA — dormant, not worth wiring",
            ],
        }

        with patch("src.memory.engram_cache.get_engram_cache", return_value=mock_engram), \
             patch("src.services.session_tracker.get_session_tracker") as mock_tracker:
            mock_tracker.return_value.get_role.return_value = {
                "callsign": "Alpha",
                "domain": "engine",
            }
            _inject_debrief(result, arguments)

        # ENGRAM.put called twice (one per decision)
        assert mock_engram.put.call_count == 2
        # Check first decision
        first_call = mock_engram.put.call_args_list[0]
        assert first_call.kwargs["key"].startswith("Alpha::decision::engine::tb_test_123")
        assert "JEPA" in first_call.kwargs["value"]
        assert first_call.kwargs["category"] == "architecture"
        assert first_call.kwargs["match_count"] == 0
        # Result reports capture count
        assert result["decisions_captured"] == 2

    def test_empty_decisions_ignored(self):
        """No ENGRAM writes when decisions is empty."""
        from src.mcp.tools.task_board_tools import _inject_debrief

        result = {"success": True}
        arguments = {"decisions": []}
        _inject_debrief(result, arguments)
        assert "decisions_captured" not in result

    def test_no_decisions_field_is_fine(self):
        """_inject_debrief works without decisions field."""
        from src.mcp.tools.task_board_tools import _inject_debrief

        result = {"success": True}
        arguments = {}
        _inject_debrief(result, arguments)
        assert result["debrief_requested"] is True
        assert "decisions_captured" not in result
