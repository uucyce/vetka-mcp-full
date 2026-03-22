"""
MARKER_ZETA.D4: Tests for Task Board role/domain extensions.

Tests:
1. role and domain fields accepted on task add
2. role and domain fields accepted on task update
3. Backward compatibility — tasks without role/domain work as before
4. Domain validation on claim (warn mode)
5. Ownership validation on complete (warn mode)
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.orchestration.task_board import TaskBoard


@pytest.fixture
def board(tmp_path):
    """Fresh task board with temp storage."""
    json_path = tmp_path / "task_board.json"
    json_path.write_text('{"tasks": {}, "settings": {}}')
    return TaskBoard(board_file=json_path)


# ── Field Acceptance Tests ──────────────────────────────────


class TestRoleDomainFields:
    def test_add_task_with_role_and_domain(self, board):
        task_id = board.add_task(
            title="Test task",
            role="Alpha",
            domain="engine",
        )
        task = board.get_task(task_id)
        assert task["role"] == "Alpha"
        assert task["domain"] == "engine"

    def test_add_task_without_role_domain(self, board):
        """Backward compat: tasks without role/domain get empty strings."""
        task_id = board.add_task(title="Legacy task")
        task = board.get_task(task_id)
        assert task["role"] == ""
        assert task["domain"] == ""

    def test_update_task_role_and_domain(self, board):
        task_id = board.add_task(title="Update test")
        board.update_task(task_id, role="Beta", domain="media")
        task = board.get_task(task_id)
        assert task["role"] == "Beta"
        assert task["domain"] == "media"

    def test_update_role_preserves_other_fields(self, board):
        task_id = board.add_task(title="Preserve test", priority=1, phase_type="fix")
        board.update_task(task_id, role="Gamma")
        task = board.get_task(task_id)
        assert task["role"] == "Gamma"
        assert task["priority"] == 1
        assert task["phase_type"] == "fix"


# ── Backward Compatibility Tests ────────────────────────────


class TestBackwardCompat:
    def test_claim_works_without_role_domain(self, board):
        task_id = board.add_task(title="No role task")
        result = board.claim_task(task_id, "opus", "claude_code")
        assert result["success"] is True

    def test_complete_works_without_role_domain(self, board):
        task_id = board.add_task(
            title="No role complete",
            agent_type="claude_code",
            execution_mode="manual",
        )
        board.claim_task(task_id, "opus", "claude_code")
        result = board.complete_task(task_id, commit_hash="abc123", branch="main")
        assert result["success"] is True

    def test_existing_tasks_without_role_field_still_work(self, board):
        """Simulate legacy task missing role/domain entirely."""
        task_id = board.add_task(title="Legacy task")
        task = board.get_task(task_id)
        # Manually remove role/domain to simulate legacy data
        task.pop("role", None)
        task.pop("domain", None)
        board.tasks[task_id] = task
        # Claim should still work
        result = board.claim_task(task_id, "opus", "claude_code")
        assert result["success"] is True


# ── Domain Validation on Claim (Warn Mode) ──────────────────


class TestDomainValidationOnClaim:
    def test_claim_with_matching_domain_no_warning(self, board):
        """When agent's domain matches task domain, no warning."""
        task_id = board.add_task(title="Engine task", domain="engine")

        # Mock registry to return Alpha (engine domain)
        mock_role = MagicMock()
        mock_role.callsign = "Alpha"
        mock_role.domain = "engine"

        mock_registry = MagicMock()
        mock_registry.get_by_branch.return_value = mock_role
        mock_registry.validate_domain_match.return_value = (True, "matches")

        with patch("src.services.agent_registry.get_agent_registry", return_value=mock_registry):
            result = board.claim_task(task_id, "opus", "claude_code")

        assert result["success"] is True
        assert "domain_warning" not in result

    def test_claim_with_mismatching_domain_returns_warning(self, board):
        """When agent's domain doesn't match task domain, return warning."""
        task_id = board.add_task(title="QA task", domain="qa")

        mock_role = MagicMock()
        mock_role.callsign = "Alpha"
        mock_role.domain = "engine"

        mock_registry = MagicMock()
        mock_registry.get_by_branch.return_value = mock_role
        mock_registry.validate_domain_match.return_value = (
            False,
            "Domain mismatch: Alpha owns 'engine' but task domain is 'qa'",
        )

        with patch("src.services.agent_registry.get_agent_registry", return_value=mock_registry):
            result = board.claim_task(task_id, "opus", "claude_code")

        # Claim still succeeds (warn mode, not blocking)
        assert result["success"] is True
        assert "domain_warning" in result
        assert "mismatch" in result["domain_warning"].lower()

    def test_claim_without_registry_still_succeeds(self, board):
        """If AgentRegistry import fails, claim still works."""
        task_id = board.add_task(title="No registry", domain="engine")

        with patch(
            "src.services.agent_registry.get_agent_registry",
            side_effect=ImportError("no registry"),
        ):
            result = board.claim_task(task_id, "opus", "claude_code")

        assert result["success"] is True


# ── Ownership Validation on Complete (Warn Mode) ────────────


class TestOwnershipValidationOnComplete:
    def test_complete_with_valid_paths_no_warnings(self, board):
        task_id = board.add_task(
            title="Valid paths",
            role="Alpha",
            domain="engine",
            allowed_paths=["client/src/store/useTimelineInstanceStore.ts"],
            agent_type="claude_code",
            execution_mode="manual",
        )
        board.claim_task(task_id, "opus", "claude_code")

        mock_result = MagicMock()
        mock_result.is_blocked = False

        mock_registry = MagicMock()
        mock_registry.validate_file_ownership.return_value = mock_result

        with patch("src.services.agent_registry.get_agent_registry", return_value=mock_registry):
            result = board.complete_task(task_id, commit_hash="abc123", branch="main")

        assert result["success"] is True
        assert "ownership_warnings" not in result

    def test_complete_with_blocked_paths_returns_warnings(self, board):
        task_id = board.add_task(
            title="Blocked paths",
            role="Alpha",
            domain="engine",
            allowed_paths=["client/src/components/cut/MenuBar.tsx"],
            agent_type="claude_code",
            execution_mode="manual",
        )
        board.claim_task(task_id, "opus", "claude_code")

        mock_result = MagicMock()
        mock_result.is_blocked = True

        mock_registry = MagicMock()
        mock_registry.validate_file_ownership.return_value = mock_result

        with patch("src.services.agent_registry.get_agent_registry", return_value=mock_registry):
            result = board.complete_task(task_id, commit_hash="abc123", branch="main")

        # Complete still succeeds (warn mode)
        assert result["success"] is True
        assert "ownership_warnings" in result
        assert len(result["ownership_warnings"]) > 0

    def test_complete_without_registry_still_succeeds(self, board):
        task_id = board.add_task(
            title="No registry complete",
            role="Alpha",
            allowed_paths=["some/file.ts"],
            agent_type="claude_code",
            execution_mode="manual",
        )
        board.claim_task(task_id, "opus", "claude_code")

        with patch(
            "src.services.agent_registry.get_agent_registry",
            side_effect=ImportError("no registry"),
        ):
            result = board.complete_task(task_id, commit_hash="abc123", branch="main")

        assert result["success"] is True
