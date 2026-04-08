"""
Tests for MARKER_210.MCP_GUARD — vetka_git_commit claimed-task guardrail.

Covers:
1. Commit blocked when VETKA_AGENT_ROLE set but no claimed task
2. Commit allowed when claimed task exists
3. Guard skipped when VETKA_AGENT_ROLE not set (non-vetka context)
4. Emergency bypass via VETKA_COMMIT_GUARDRAIL_BYPASS=1
5. Guard fail-open when task_board import fails (non-critical)
6. Pending task suggestions appear in error message
"""
import os
import unittest
from unittest.mock import MagicMock, patch


def _make_tool():
    """Import GitCommitTool without triggering subprocess calls."""
    from src.mcp.tools.git_tool import GitCommitTool
    return GitCommitTool()


class TestMCPCommitGuardrail(unittest.TestCase):

    def _base_args(self, dry_run=False):
        return {"message": "test: commit message", "dry_run": dry_run, "cwd": "/tmp"}

    # ── 1. Blocked: role set, no claimed task ─────────────────────────────
    def test_blocked_when_no_claimed_task(self):
        tool = _make_tool()
        mock_board = MagicMock()
        mock_board.list_tasks.return_value = {"tasks": [
            {"id": "tb_001", "title": "Fix something important"},
            {"id": "tb_002", "title": "Add feature X"},
        ]}

        with patch.dict(os.environ, {"VETKA_AGENT_ROLE": "Eta"}, clear=False):
            with patch.dict("sys.modules", {
                "src.orchestration.task_board": MagicMock(
                    check_claimed_task_for_hook=lambda r: None,
                    get_task_board=lambda: mock_board,
                )
            }):
                result = tool.execute(self._base_args())

        self.assertFalse(result["success"])
        self.assertTrue(result.get("guardrail"))
        self.assertIn("no claimed task", result["error"])
        self.assertIn("Eta", result["error"])

    # ── 2. Allowed: role set, claimed task exists ─────────────────────────
    def test_allowed_when_claimed_task_exists(self):
        tool = _make_tool()
        mock_task = {"id": "tb_123", "title": "Fix the bug", "status": "claimed"}

        import subprocess
        with patch.dict(os.environ, {"VETKA_AGENT_ROLE": "Eta"}, clear=False):
            with patch.dict("sys.modules", {
                "src.orchestration.task_board": MagicMock(
                    check_claimed_task_for_hook=lambda r: mock_task,
                    get_task_board=MagicMock(),
                )
            }):
                # Mock all subprocess calls so we don't actually git commit
                with patch("subprocess.run") as mock_run:
                    # git add
                    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                    result = tool.execute(self._base_args())

        # Guard passed — result depends on subprocess mocks (commit may fail), but NOT guardrail block
        self.assertFalse(result.get("guardrail", False))

    # ── 3. Skipped: no VETKA_AGENT_ROLE ──────────────────────────────────
    def test_guard_skipped_when_no_role(self):
        tool = _make_tool()
        env = {k: v for k, v in os.environ.items() if k != "VETKA_AGENT_ROLE"}

        with patch.dict(os.environ, env, clear=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="abc1234\n", stderr="")
                result = tool.execute(self._base_args())

        # Guard not triggered — no guardrail key
        self.assertFalse(result.get("guardrail", False))

    # ── 4. Bypass: VETKA_COMMIT_GUARDRAIL_BYPASS=1 ───────────────────────
    def test_bypass_env_var_skips_guard(self):
        tool = _make_tool()

        with patch.dict(os.environ, {
            "VETKA_AGENT_ROLE": "Eta",
            "VETKA_COMMIT_GUARDRAIL_BYPASS": "1",
        }, clear=False):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="abc1234\n", stderr="")
                result = tool.execute(self._base_args())

        self.assertFalse(result.get("guardrail", False))

    # ── 5. Fail-open: ImportError → guard skipped ────────────────────────
    def test_guard_fail_open_on_import_error(self):
        tool = _make_tool()

        with patch.dict(os.environ, {"VETKA_AGENT_ROLE": "Eta"}, clear=False):
            # Remove task_board from sys.modules so import inside execute raises ImportError
            with patch.dict("sys.modules", {"src.orchestration.task_board": None}):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="abc1234\n", stderr="")
                    result = tool.execute(self._base_args())

        # Guard failed open — commit proceeds
        self.assertFalse(result.get("guardrail", False))

    # ── 6. Error message includes pending task suggestions ────────────────
    def test_error_includes_pending_suggestions(self):
        tool = _make_tool()
        mock_board = MagicMock()
        mock_board.list_tasks.return_value = {"tasks": [
            {"id": "tb_001", "title": "Critical P1 fix"},
            {"id": "tb_002", "title": "Feature Y implementation"},
        ]}

        with patch.dict(os.environ, {"VETKA_AGENT_ROLE": "Eta"}, clear=False):
            with patch.dict("sys.modules", {
                "src.orchestration.task_board": MagicMock(
                    check_claimed_task_for_hook=lambda r: None,
                    get_task_board=lambda: mock_board,
                )
            }):
                result = tool.execute(self._base_args())

        self.assertFalse(result["success"])
        self.assertIn("tb_001", result["error"])

    # ── 7. dry_run bypasses guard entirely ───────────────────────────────
    def test_dry_run_bypasses_guard(self):
        tool = _make_tool()

        with patch.dict(os.environ, {"VETKA_AGENT_ROLE": "Eta"}, clear=False):
            result = tool.execute(self._base_args(dry_run=True))

        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["status"], "dry_run")


if __name__ == "__main__":
    unittest.main()
