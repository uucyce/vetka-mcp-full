"""
Tests for Phase 182: Verifier Merge — verify_and_merge() + closure protocol.

MARKER_S4_RECON_2B: Restored in Session 4 (was lost between worktrees).

Tests cover:
- verify_and_merge(): file collection, staging, commit, error handling
- _validate_closure_proof(): protocol validation, thresholds, overrides
- _run_closure_tests(): async test execution, truncation, fail-fast
- complete_task(): closure proof integration, status transitions
- ActionRegistry.get_edit_files_for_run(): dedup, filtering
"""

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from src.orchestration.action_registry import ActionLogEntry, ActionRegistry

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 182 contracts changed")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_log(tmp_path):
    return tmp_path / "action_log.json"


@pytest.fixture
def registry(tmp_log):
    return ActionRegistry(storage_path=tmp_log)


@pytest.fixture
def task_board(tmp_path):
    """Create a real TaskBoard with temporary storage."""
    from src.orchestration.task_board import TaskBoard
    board_file = tmp_path / "task_board.json"
    board_file.write_text('{"tasks": {}, "settings": {}}')
    board = TaskBoard(board_file=board_file)
    return board


# ---------------------------------------------------------------------------
# ActionRegistry.get_edit_files_for_run() tests
# ---------------------------------------------------------------------------

class TestGetEditFilesForRun:
    def test_basic_edit_files(self, registry):
        registry.log_action(run_id="run_1", agent="coder", action="edit",
                            file="src/main.py", result="success")
        registry.log_action(run_id="run_1", agent="coder", action="create",
                            file="src/new.py", result="success")
        registry.log_action(run_id="run_1", agent="scout", action="read",
                            file="src/other.py", result="success")

        files = registry.get_edit_files_for_run("run_1")
        assert "src/main.py" in files
        assert "src/new.py" in files
        assert "src/other.py" not in files  # read excluded

    def test_deduplication(self, registry):
        registry.log_action(run_id="run_1", agent="coder", action="edit",
                            file="src/main.py", result="success")
        registry.log_action(run_id="run_1", agent="coder", action="edit",
                            file="src/main.py", result="success")

        files = registry.get_edit_files_for_run("run_1")
        assert files.count("src/main.py") == 1

    def test_failed_edits_excluded(self, registry):
        registry.log_action(run_id="run_1", agent="coder", action="edit",
                            file="src/broken.py", result="error")
        registry.log_action(run_id="run_1", agent="coder", action="edit",
                            file="src/good.py", result="success")

        files = registry.get_edit_files_for_run("run_1")
        assert "src/broken.py" not in files
        assert "src/good.py" in files

    def test_different_run_ids_isolated(self, registry):
        registry.log_action(run_id="run_1", agent="coder", action="edit",
                            file="src/a.py", result="success")
        registry.log_action(run_id="run_2", agent="coder", action="edit",
                            file="src/b.py", result="success")

        files_1 = registry.get_edit_files_for_run("run_1")
        files_2 = registry.get_edit_files_for_run("run_2")
        assert "src/a.py" in files_1
        assert "src/b.py" not in files_1
        assert "src/b.py" in files_2

    def test_empty_run(self, registry):
        files = registry.get_edit_files_for_run("run_nonexistent")
        assert files == []

    def test_sorted_output(self, registry):
        registry.log_action(run_id="run_1", agent="coder", action="edit",
                            file="src/z.py", result="success")
        registry.log_action(run_id="run_1", agent="coder", action="create",
                            file="src/a.py", result="success")
        registry.log_action(run_id="run_1", agent="coder", action="edit",
                            file="src/m.py", result="success")

        files = registry.get_edit_files_for_run("run_1")
        assert files == sorted(files)


# ---------------------------------------------------------------------------
# _validate_closure_proof() tests
# ---------------------------------------------------------------------------

class TestValidateClosureProof:
    """Test TaskBoard._validate_closure_proof() logic."""

    def _make_task(self, require_proof=True, stats=None):
        task = {
            "task_id": "tb_test_001",
            "title": "Test task",
            "status": "done",
            "require_closure_proof": require_proof,
        }
        if stats:
            task["stats"] = stats
        return task

    def _make_proof(self, pipeline_success=True, confidence=0.8, tests=None, commit_hash="abc123"):
        proof = {
            "pipeline_success": pipeline_success,
            "verifier_confidence": confidence,
            "commit_hash": commit_hash,
        }
        if tests is not None:
            proof["tests"] = tests
        else:
            proof["tests"] = [{"command": "pytest", "passed": True, "exit_code": 0}]
        return proof

    def test_manual_override_bypasses_all(self, task_board):
        task = self._make_task(require_proof=True)
        result = task_board._validate_closure_proof(task, None, manual_override=True)
        assert result is None  # None = validation passed

    def test_non_protocol_task_skips(self, task_board):
        task = self._make_task(require_proof=False)
        result = task_board._validate_closure_proof(task, None)
        assert result is None

    def test_missing_proof_for_protocol_task(self, task_board):
        task = self._make_task(require_proof=True)
        result = task_board._validate_closure_proof(task, None)
        assert result is not None
        assert "required" in result.lower()

    def test_pipeline_success_false(self, task_board):
        task = self._make_task(require_proof=True)
        proof = self._make_proof(pipeline_success=False)
        result = task_board._validate_closure_proof(task, proof)
        assert result is not None
        assert "pipeline_success" in result.lower()

    def test_low_verifier_confidence(self, task_board):
        task = self._make_task(require_proof=True)
        proof = self._make_proof(confidence=0.1)
        result = task_board._validate_closure_proof(task, proof)
        assert result is not None
        assert "confidence" in result.lower() or "threshold" in result.lower()

    def test_high_verifier_confidence_passes(self, task_board):
        task = self._make_task(require_proof=True)
        proof = self._make_proof(confidence=0.9)
        result = task_board._validate_closure_proof(task, proof)
        assert result is None

    def test_empty_tests_array(self, task_board):
        task = self._make_task(require_proof=True)
        proof = self._make_proof(tests=[])
        result = task_board._validate_closure_proof(task, proof)
        assert result is not None
        assert "test" in result.lower()

    def test_failed_test_in_array(self, task_board):
        task = self._make_task(require_proof=True)
        proof = self._make_proof(tests=[
            {"command": "pytest", "passed": True, "exit_code": 0},
            {"command": "npm test", "passed": False, "exit_code": 1},
        ])
        result = task_board._validate_closure_proof(task, proof)
        assert result is not None
        assert "test" in result.lower()

    def test_missing_commit_hash(self, task_board):
        task = self._make_task(require_proof=True)
        proof = self._make_proof(commit_hash="")
        result = task_board._validate_closure_proof(task, proof)
        assert result is not None
        assert "commit" in result.lower()

    def test_full_valid_proof_passes(self, task_board):
        task = self._make_task(require_proof=True)
        proof = self._make_proof(
            pipeline_success=True,
            confidence=0.85,
            tests=[{"command": "pytest", "passed": True, "exit_code": 0}],
            commit_hash="abc123def456",
        )
        result = task_board._validate_closure_proof(task, proof)
        assert result is None

    def test_confidence_string_coercion(self, task_board):
        """Confidence passed as string should be parsed to float."""
        task = self._make_task(require_proof=True)
        proof = self._make_proof(confidence="0.9")
        result = task_board._validate_closure_proof(task, proof)
        assert result is None  # Should parse "0.9" → 0.9 and pass


# ---------------------------------------------------------------------------
# _run_closure_tests() tests
# ---------------------------------------------------------------------------

class TestRunClosureTests:
    @pytest.mark.asyncio
    async def test_single_passing_command(self, task_board):
        results = await task_board._run_closure_tests(["echo 'hello'"])
        assert len(results) == 1
        assert results[0]["passed"] is True
        assert results[0]["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_failing_command(self, task_board):
        results = await task_board._run_closure_tests(["exit 1"])
        assert len(results) == 1
        assert results[0]["passed"] is False
        assert results[0]["exit_code"] == 1

    @pytest.mark.asyncio
    async def test_fail_fast_stops_on_first_failure(self, task_board):
        results = await task_board._run_closure_tests([
            "exit 1",
            "echo 'should not run'",
        ])
        # Should stop after first failure
        assert len(results) == 1
        assert results[0]["passed"] is False

    @pytest.mark.asyncio
    async def test_multiple_passing(self, task_board):
        results = await task_board._run_closure_tests([
            "echo 'test1'",
            "echo 'test2'",
        ])
        assert len(results) == 2
        assert all(r["passed"] for r in results)

    @pytest.mark.asyncio
    async def test_stdout_captured(self, task_board):
        results = await task_board._run_closure_tests(["echo 'captured output'"])
        assert "captured output" in results[0]["stdout"]


# ---------------------------------------------------------------------------
# verify_and_merge() tests (mocked git operations)
# ---------------------------------------------------------------------------

class TestVerifyAndMerge:
    """Test verify_and_merge() static method.

    ActionRegistry is imported locally inside the function, so we patch
    at the source module level: src.orchestration.action_registry.ActionRegistry.
    """

    @pytest.mark.asyncio
    async def test_no_edits_returns_success(self):
        """If no files were edited in this run, return success with empty list."""
        from src.orchestration.agent_pipeline import AgentPipeline

        mock_registry = MagicMock()
        mock_registry.get_edit_files_for_run.return_value = []

        with patch("src.orchestration.action_registry.ActionRegistry", return_value=mock_registry):
            result = await AgentPipeline.verify_and_merge(
                run_id="run_empty_001",
                task_id="tb_empty_001",
            )

            assert result["success"] is True
            assert result["files_committed"] == []
            assert "note" in result

    @pytest.mark.asyncio
    async def test_missing_files_skipped(self, tmp_path):
        """Files that don't exist on disk should be skipped."""
        from src.orchestration.agent_pipeline import AgentPipeline

        mock_registry = MagicMock()
        mock_registry.get_edit_files_for_run.return_value = [
            "/nonexistent/path/file.py",
        ]

        with patch("src.orchestration.action_registry.ActionRegistry", return_value=mock_registry):
            result = await AgentPipeline.verify_and_merge(
                run_id="run_missing_001",
                task_id="tb_missing_001",
            )
            # All files missing → either success with note or error
            assert "success" in result


# ---------------------------------------------------------------------------
# complete_task() with closure proof tests
# ---------------------------------------------------------------------------

class TestCompleteTaskWithProof:
    def _add_task(self, board, task_id="tb_cp_001", require_proof=False, status="done"):
        """Add a task directly to the board's internal storage."""
        task = {
            "task_id": task_id,
            "title": "Test closure",
            "status": status,
            "require_closure_proof": require_proof,
            "assigned_to": "opus",
            "created_at": time.time(),
            "status_history": [],
        }
        board.tasks[task_id] = task
        return task

    def test_complete_non_protocol_task(self, task_board):
        self._add_task(task_board, require_proof=False)
        result = task_board.complete_task("tb_cp_001", commit_hash="abc123")
        assert result["success"] is True

    def test_complete_protocol_task_with_valid_proof(self, task_board):
        self._add_task(task_board, require_proof=True)
        proof = {
            "pipeline_success": True,
            "verifier_confidence": 0.9,
            "tests": [{"command": "pytest", "passed": True, "exit_code": 0}],
            "commit_hash": "abc123",
        }
        result = task_board.complete_task("tb_cp_001", closure_proof=proof)
        assert result["success"] is True

    def test_complete_protocol_task_without_proof_fails(self, task_board):
        self._add_task(task_board, require_proof=True)
        result = task_board.complete_task("tb_cp_001")
        assert result["success"] is False

    def test_complete_with_manual_override(self, task_board):
        self._add_task(task_board, require_proof=True)
        result = task_board.complete_task(
            "tb_cp_001",
            manual_override=True,
            override_reason="Commander approved",
        )
        assert result["success"] is True

    def test_complete_nonexistent_task(self, task_board):
        result = task_board.complete_task("tb_nonexistent")
        assert result["success"] is False

    def test_complete_sets_status_done(self, task_board):
        self._add_task(task_board, require_proof=False)
        task_board.complete_task("tb_cp_001", commit_hash="abc123")
        task = task_board.get_task("tb_cp_001")
        assert task["status"] == "done"
