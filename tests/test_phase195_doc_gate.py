# MARKER_195.3: Tests for phase_type-aware DOC_GATE
# research/test tasks auto-exempt, build/fix require docs or force_no_docs
from unittest.mock import patch
from pathlib import Path
from src.orchestration.task_board import TaskBoard
from src.mcp.tools.task_board_tools import handle_task_board
import tempfile


class TestDocGatePhaseTypeAware:
    """MARKER_195.3: DOC_GATE should auto-exempt research and test tasks."""

    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.board = TaskBoard(board_file=Path(self.tmp.name))

    @patch("src.orchestration.task_board.get_task_board")
    def test_research_task_without_docs_passes(self, mock_get_board):
        """phase_type=research auto-exempt — no docs needed, no force_no_docs needed."""
        mock_get_board.return_value = self.board
        result = handle_task_board({
            "action": "add",
            "title": "Research: investigate new auth patterns",
            "phase_type": "research",
            "priority": 3,
        })
        assert result["success"] is True, f"Research task rejected: {result.get('error')}"
        assert "task_id" in result

    @patch("src.orchestration.task_board.get_task_board")
    def test_test_task_without_docs_passes(self, mock_get_board):
        """phase_type=test auto-exempt — tests validate, they don't need design docs."""
        mock_get_board.return_value = self.board
        result = handle_task_board({
            "action": "add",
            "title": "Test: add coverage for auth module",
            "phase_type": "test",
            "priority": 3,
        })
        assert result["success"] is True, f"Test task rejected: {result.get('error')}"
        assert "task_id" in result

    @patch("src.orchestration.task_board.get_task_board")
    def test_build_task_without_docs_rejected(self, mock_get_board):
        """phase_type=build without docs → REJECT (must attach docs or force_no_docs)."""
        mock_get_board.return_value = self.board
        result = handle_task_board({
            "action": "add",
            "title": "Build: new auth middleware",
            "phase_type": "build",
            "priority": 2,
        })
        assert result["success"] is False
        assert "DOC_GATE" in result["error"]
        assert result.get("doc_gate") is True

    @patch("src.orchestration.task_board.get_task_board")
    def test_fix_task_without_docs_rejected(self, mock_get_board):
        """phase_type=fix without docs → REJECT."""
        mock_get_board.return_value = self.board
        result = handle_task_board({
            "action": "add",
            "title": "Fix: auth token expiry bug",
            "phase_type": "fix",
            "priority": 1,
        })
        assert result["success"] is False
        assert "DOC_GATE" in result["error"]

    @patch("src.orchestration.task_board.get_task_board")
    def test_build_task_with_force_no_docs_strict_mode(self, mock_get_board):
        """phase_type=build + force_no_docs=true → STRICT: rejected when suggested_docs >= 2."""
        mock_get_board.return_value = self.board
        result = handle_task_board({
            "action": "add",
            "title": "Build: emergency hotfix no docs",
            "phase_type": "build",
            "priority": 1,
            "force_no_docs": True,
        })
        # force_no_docs is now strict — only bypasses when <2 suggested docs found
        # In a real repo with docs, this should be rejected
        if result.get("strict_mode"):
            assert result["success"] is False
            assert "DOC_GATE STRICT" in result["error"]
        else:
            # No docs found → force_no_docs still works
            assert result["success"] is True
            assert "task_id" in result

    @patch("src.orchestration.task_board.get_task_board")
    def test_no_phase_type_without_docs_rejected(self, mock_get_board):
        """No phase_type + no docs → REJECT (default strict behavior)."""
        mock_get_board.return_value = self.board
        result = handle_task_board({
            "action": "add",
            "title": "Some task without phase_type",
            "priority": 3,
        })
        assert result["success"] is False
        assert "DOC_GATE" in result["error"]

    @patch("src.orchestration.task_board.get_task_board")
    def test_research_task_with_docs_also_passes(self, mock_get_board):
        """Research task WITH docs still works (docs are optional, not forbidden)."""
        mock_get_board.return_value = self.board
        result = handle_task_board({
            "action": "add",
            "title": "Research: extend auth recon",
            "phase_type": "research",
            "priority": 3,
            "recon_docs": ["docs/some_existing_recon.md"],
        })
        assert result["success"] is True
        assert "task_id" in result

    @patch("src.orchestration.task_board.get_task_board")
    def test_hint_mentions_auto_exempt(self, mock_get_board):
        """REJECT hint should mention that research/test are auto-exempt."""
        mock_get_board.return_value = self.board
        result = handle_task_board({
            "action": "add",
            "title": "Build: something without docs",
            "phase_type": "build",
            "priority": 3,
        })
        assert result["success"] is False
        assert "auto-exempt" in result.get("hint", "")
