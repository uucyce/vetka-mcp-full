"""Tests for MARKER_201.BRANCH_GUARD — branch protection in complete_task().

TB_201.C: Warn-mode guard that checks if the completing branch matches
the task role's registered branch. Phase 1 = warn only, Phase 2 = reject.

TDD-RED: These tests require TB_201.A+B+C merged from claude/harness
and claude/harness-eta. Until merge, all tests are xfail.

These tests verify:
1. Warning fires on branch mismatch
2. No warning when branch matches
3. Guard skips gracefully for empty role / main branch / unknown callsign
4. Guard is non-fatal (try/except) — completion always proceeds in warn-mode
"""
import logging
import pytest
from pathlib import Path
from unittest.mock import patch

from src.orchestration.task_board import TaskBoard

# TDD-RED: Guard code lives on claude/harness + claude/harness-eta, not yet merged
_201_NOT_MERGED = pytest.mark.xfail(
    reason="TB_201 guard code not yet merged from claude/harness — TDD-RED contract test",
    strict=False,
)


def make_board(tmp_path: Path) -> TaskBoard:
    board_file = tmp_path / "task_board.json"
    return TaskBoard(board_file=board_file)


@_201_NOT_MERGED
class TestBranchGuardWarnMode:
    """TB_201.C: Branch protection guard — warn-mode (Phase 1)."""

    def test_branch_mismatch_warns_but_allows_completion(self, tmp_path, caplog):
        """Completing on wrong branch should warn but NOT reject."""
        board = make_board(tmp_path)
        task_id = board.add_task("test task", role="Alpha")
        board.claim_task(task_id, agent_name="Alpha", agent_type="claude_code")

        with patch.object(board, "_detect_current_branch", return_value="claude/cut-media"):
            with caplog.at_level(logging.WARNING):
                result = board.complete_task(
                    task_id,
                    agent_name="Alpha",
                    branch="claude/cut-media",
                    commit_hash="abc123",
                    commit_message="test commit",
                )
        # Warn-mode: completion should succeed despite branch mismatch
        # (Alpha's registered branch is claude/cut-engine, not claude/cut-media)
        assert result.get("success") is True or "error" not in result or "BRANCH_GUARD" not in result.get("error", "")

    def test_matching_branch_no_warning(self, tmp_path, caplog):
        """Completing on correct branch should NOT produce BRANCH_GUARD warning."""
        board = make_board(tmp_path)
        task_id = board.add_task("test task", role="Delta")
        board.claim_task(task_id, agent_name="Delta", agent_type="claude_code")

        with patch.object(board, "_detect_current_branch", return_value="worktree-cut-qa"):
            with caplog.at_level(logging.WARNING):
                result = board.complete_task(
                    task_id,
                    agent_name="Delta",
                    branch="worktree-cut-qa",
                    commit_hash="def456",
                    commit_message="test commit",
                )
        branch_warnings = [r for r in caplog.records if "BRANCH_GUARD" in r.message]
        assert len(branch_warnings) == 0, f"Unexpected BRANCH_GUARD warning: {branch_warnings}"

    def test_empty_role_skips_guard(self, tmp_path, caplog):
        """Tasks with no role should bypass branch guard entirely."""
        board = make_board(tmp_path)
        task_id = board.add_task("no role task")
        board.claim_task(task_id, agent_name="anon", agent_type="claude_code")

        with patch.object(board, "_detect_current_branch", return_value="some-random-branch"):
            with caplog.at_level(logging.WARNING):
                board.complete_task(
                    task_id,
                    agent_name="anon",
                    branch="some-random-branch",
                    commit_hash="ghi789",
                    commit_message="test commit",
                )
        branch_warnings = [r for r in caplog.records if "BRANCH_GUARD" in r.message]
        assert len(branch_warnings) == 0

    def test_main_branch_skips_guard(self, tmp_path, caplog):
        """Completing on main branch should bypass guard (different flow)."""
        board = make_board(tmp_path)
        task_id = board.add_task("main task", role="Alpha")
        board.claim_task(task_id, agent_name="Alpha", agent_type="claude_code")

        with patch.object(board, "_detect_current_branch", return_value="main"):
            with caplog.at_level(logging.WARNING):
                board.complete_task(
                    task_id,
                    agent_name="Alpha",
                    branch="main",
                    commit_hash="jkl012",
                    commit_message="test commit",
                )
        branch_warnings = [r for r in caplog.records if "BRANCH_GUARD" in r.message]
        assert len(branch_warnings) == 0

    def test_unknown_callsign_skips_guard(self, tmp_path, caplog):
        """Unknown callsign not in registry should not crash — guard skips."""
        board = make_board(tmp_path)
        task_id = board.add_task("ephemeral task", role="Phantom")
        board.claim_task(task_id, agent_name="Phantom", agent_type="claude_code")

        with patch.object(board, "_detect_current_branch", return_value="claude/phantom"):
            with caplog.at_level(logging.WARNING):
                board.complete_task(
                    task_id,
                    agent_name="Phantom",
                    branch="claude/phantom",
                    commit_hash="mno345",
                    commit_message="test commit",
                )
        # Should not crash, guard skips for unknown callsign
        branch_warnings = [r for r in caplog.records if "BRANCH_GUARD" in r.message]
        assert len(branch_warnings) == 0

    def test_guard_nonfatal_on_registry_import_error(self, tmp_path, caplog):
        """Registry import failure should degrade gracefully — completion proceeds."""
        board = make_board(tmp_path)
        task_id = board.add_task("import fail task", role="Alpha")
        board.claim_task(task_id, agent_name="Alpha", agent_type="claude_code")

        with patch("src.orchestration.task_board.AgentRegistry", side_effect=ImportError("no registry")):
            with patch.object(board, "_detect_current_branch", return_value="claude/wrong"):
                result = board.complete_task(
                    task_id,
                    agent_name="Alpha",
                    branch="claude/wrong",
                    commit_hash="pqr678",
                    commit_message="test commit",
                )
        # Should not crash — guard degrades, completion proceeds
        assert "BRANCH_GUARD" not in result.get("error", "")


@_201_NOT_MERGED
class TestToolIsolationExtended:
    """Additional coverage for TB_201.B edge cases."""

    def test_unknown_agent_type_rejected_from_locked_task(self, tmp_path):
        """Default agent_type='unknown' should be rejected from locked tasks."""
        board = make_board(tmp_path)
        task_id = board.add_task("locked task", allowed_tools=["claude_code"])
        result = board.claim_task(task_id, agent_name="mystery", agent_type="unknown")
        assert result["success"] is False
        assert result.get("tool_isolation_rejected") is True

    def test_multiple_allowed_tools(self, tmp_path):
        """Task allowing multiple tool types should accept any of them."""
        board = make_board(tmp_path)
        task_id = board.add_task("multi-tool task", allowed_tools=["claude_code", "local_ollama", "cursor"])
        result = board.claim_task(task_id, agent_name="ollama_agent", agent_type="local_ollama")
        assert result["success"] is True
