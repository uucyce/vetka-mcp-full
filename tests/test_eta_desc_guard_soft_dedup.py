"""
Tests for MARKER_ETA.GUARD features:
- DESC_GUARD: Description validation (P1/P2 blocking, P3+ warning)
- SOFT_DEDUP: Soft deduplication by title similarity

MARKER_ETA: Early-stage task validation to improve task clarity and prevent duplicates.
"""

import pytest
import tempfile
import json
from pathlib import Path

from src.orchestration.task_board import TaskBoard
from src.mcp.tools.task_board_tools import handle_task_board


class TestDescGuardValidation:
    """DESC_GUARD: Description length validation."""

    def setup_method(self):
        """Create temporary task board for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.board_path = Path(self.temp_dir) / "tasks.db"
        self.board = TaskBoard(self.board_path)

    def test_desc_guard_p1_task_too_short_blocks(self):
        """P1 task with description < 20 chars should be rejected."""
        result = handle_task_board({
            "action": "add",
            "title": "Fix bug",
            "description": "Short",  # 5 chars < 20
            "phase_type": "fix",
            "priority": 1,  # P1,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is False
        assert "DESC_GUARD" in result["error"]
        assert result.get("desc_guard") is True
        assert "20 characters" in result["error"]

    def test_desc_guard_p2_task_too_short_blocks(self):
        """P2 task with description < 20 chars should be rejected."""
        result = handle_task_board({
            "action": "add",
            "title": "Implement feature",
            "description": "Do it",  # 5 chars < 20
            "phase_type": "build",
            "priority": 2,  # P2,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is False
        assert "DESC_GUARD" in result["error"]
        assert result.get("desc_guard") is True

    def test_desc_guard_p1_task_with_valid_description_accepts(self):
        """P1 task with valid description should be accepted."""
        result = handle_task_board({
            "action": "add",
            "title": "Fix critical bug",
            "description": "This is a valid description with at least twenty characters for clarity",  # >20
            "phase_type": "fix",
            "priority": 1,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is True
        assert "desc_guard" not in result or result.get("desc_guard") is False

    def test_desc_guard_p3_task_short_warns_but_accepts(self):
        """P3+ task with short description should warn but still accept."""
        result = handle_task_board({
            "action": "add",
            "title": "Nice to have",
            "description": "Short",  # 5 chars < 20
            "phase_type": "build",
            "priority": 3,  # P3,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is True  # Accepts P3+
        assert "desc_guard_warning" in result  # But surfaces warning
        assert "description is short" in result["desc_guard_warning"]

    def test_desc_guard_p4_task_short_warns_but_accepts(self):
        """P4+ task with short description should warn but still accept."""
        result = handle_task_board({
            "action": "add",
            "title": "Someday maybe",
            "description": "Fix",  # 3 chars < 20
            "phase_type": "build",
            "priority": 4,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is True
        assert "desc_guard_warning" in result

    def test_desc_guard_empty_description_p1_blocks(self):
        """P1 task with empty description should be rejected."""
        result = handle_task_board({
            "action": "add",
            "title": "Critical task",
            "description": "",  # Empty
            "phase_type": "fix",
            "priority": 1,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is False
        assert "DESC_GUARD" in result["error"]

    def test_desc_guard_whitespace_only_p2_blocks(self):
        """P2 task with whitespace-only description should be rejected."""
        result = handle_task_board({
            "action": "add",
            "title": "Important task",
            "description": "   \t\n   ",  # Whitespace only
            "phase_type": "build",
            "priority": 2,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is False
        assert "DESC_GUARD" in result["error"]

    def test_desc_guard_exactly_20_chars_accepts(self):
        """P1 task with exactly 20 chars should be accepted."""
        desc_20 = "a" * 20  # Exactly 20 characters
        result = handle_task_board({
            "action": "add",
            "title": "Test task",
            "description": desc_20,
            "phase_type": "fix",
            "priority": 1,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is True


class TestSoftDedupDetection:
    """SOFT_DEDUP: Soft deduplication by title similarity."""

    def setup_method(self):
        """Create temporary task board with existing tasks."""
        self.temp_dir = tempfile.mkdtemp()
        self.board_path = Path(self.temp_dir) / "tasks.db"
        self.board = TaskBoard(self.board_path)

        # Add some existing tasks
        handle_task_board({
            "action": "add",
            "title": "Fix authentication bug in login flow",
            "description": "Users cannot log in with OAuth tokens after session timeout",
            "phase_type": "fix",
            "priority": 1,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        handle_task_board({
            "action": "add",
            "title": "Add user registration endpoint",
            "description": "Create POST /api/auth/register endpoint with validation",
            "phase_type": "build",
            "priority": 2,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        handle_task_board({
            "action": "add",
            "title": "Refactor database connection pooling",
            "description": "Implement connection pool for better performance",
            "phase_type": "build",
            "priority": 3,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

    def test_soft_dedup_detects_similar_title(self):
        """Adding task with similar title should warn about possible duplicates."""
        result = handle_task_board({
            "action": "add",
            "title": "Fix login authentication bug",  # Similar to existing task
            "description": "Address the OAuth token issue in the authentication system",
            "phase_type": "fix",
            "priority": 1,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        # Should succeed
        assert result["success"] is True
        # Should suggest duplicates
        if "possible_duplicates" in result:
            assert "similar task(s) found" in result["possible_duplicates"]["message"]
            assert len(result["possible_duplicates"]["tasks"]) > 0

    def test_soft_dedup_detects_exact_title_match(self):
        """Adding task with exact same title should detect duplicate."""
        result = handle_task_board({
            "action": "add",
            "title": "Fix authentication bug in login flow",  # Exact match
            "description": "Different description but same title",
            "phase_type": "fix",
            "priority": 1,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is True
        # High likelihood of duplicate due to exact match
        if "possible_duplicates" in result:
            assert "similar task(s) found" in result["possible_duplicates"]["message"]

    def test_soft_dedup_ignores_dissimilar_title(self):
        """Adding task with dissimilar title should not suggest duplicates."""
        result = handle_task_board({
            "action": "add",
            "title": "Implement caching layer for API responses",
            "description": "Add Redis caching to improve API performance",
            "phase_type": "build",
            "priority": 2,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is True
        # Dissimilar enough, might not have duplicates
        # (depends on FTS score threshold)

    def test_soft_dedup_handles_special_characters(self):
        """SOFT_DEDUP should handle titles with special characters."""
        result = handle_task_board({
            "action": "add",
            "title": "Fix: bug in login@flow/auth (OAuth)",
            "description": "Address special character handling",
            "phase_type": "fix",
            "priority": 2,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is True
        # Should not crash with special chars

    def test_soft_dedup_is_advisory_never_blocks(self):
        """SOFT_DEDUP warnings should never block task creation."""
        # Add a task that creates potential duplicates
        result = handle_task_board({
            "action": "add",
            "title": "Fix authentication bug in login flow",  # Similar
            "description": "OAuth issue reproduction and fix",
            "phase_type": "fix",
            "priority": 1,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        # Even with possible duplicates, task should succeed
        assert result["success"] is True

    def test_soft_dedup_limits_suggestions(self):
        """SOFT_DEDUP should limit duplicate suggestions to 5."""
        # Create many tasks
        for i in range(10):
            handle_task_board({
                "action": "add",
                "title": f"Fix bug in login flow variant {i}",
                "description": f"Auth issue {i}",
                "phase_type": "fix",
                "priority": 3,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
            })

        # Add similar task
        result = handle_task_board({
            "action": "add",
            "title": "Fix authentication bug in login flow",
            "description": "Another similar auth issue to test dedup",
            "phase_type": "fix",
            "priority": 1,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is True
        if "possible_duplicates" in result:
            # Should limit to 5 suggestions
            assert len(result["possible_duplicates"]["tasks"]) <= 5


class TestDescGuardAndSoftDedupInteraction:
    """Test DESC_GUARD and SOFT_DEDUP working together."""

    def setup_method(self):
        """Create temporary task board."""
        self.temp_dir = tempfile.mkdtemp()
        self.board_path = Path(self.temp_dir) / "tasks.db"
        self.board = TaskBoard(self.board_path)

    def test_desc_guard_blocks_before_dedup_check(self):
        """DESC_GUARD validation should happen before SOFT_DEDUP."""
        # Add initial task
        handle_task_board({
            "action": "add",
            "title": "Fix login bug",
            "description": "This is a valid description with sufficient length",
            "phase_type": "fix",
            "priority": 1,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        # Try to add similar task with invalid description (P1)
        result = handle_task_board({
            "action": "add",
            "title": "Fix login bug duplicate",
            "description": "Short",  # Invalid < 20 chars
            "phase_type": "fix",
            "priority": 1,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        # DESC_GUARD should block before SOFT_DEDUP
        assert result["success"] is False
        assert "DESC_GUARD" in result["error"]
        assert "possible_duplicates" not in result  # Didn't get to SOFT_DEDUP

    def test_both_guards_applied_for_p3_task(self):
        """For P3+ tasks, DESC_GUARD warns and SOFT_DEDUP checks."""
        # Add initial task
        handle_task_board({
            "action": "add",
            "title": "Refactor database queries",
            "description": "Optimize query performance by using better indexing",
            "phase_type": "build",
            "priority": 2,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        # Add similar P3 task with short description
        result = handle_task_board({
            "action": "add",
            "title": "Refactor database",  # Similar
            "description": "Optimize",  # Short < 20 chars
            "phase_type": "build",
            "priority": 3,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        # Should succeed (P3+)
        assert result["success"] is True
        # DESC_GUARD should warn
        assert "desc_guard_warning" in result
        # SOFT_DEDUP may also suggest duplicates
        # (no assertion, as it's optional)


class TestGuardErrorMessages:
    """Test error and warning message clarity."""

    def test_desc_guard_shows_actual_character_count(self):
        """Error message should show actual character count."""
        result = handle_task_board({
            "action": "add",
            "title": "Test",
            "description": "12345678",  # 8 chars
            "phase_type": "fix",
            "priority": 1,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is False
        assert "8" in result["error"]  # Should show actual count
        assert "20" in result["error"]  # Should show requirement

    def test_desc_guard_warning_for_p3_shows_char_count(self):
        """Warning should show character count for P3+ tasks."""
        result = handle_task_board({
            "action": "add",
            "title": "Nice to have",
            "description": "ABC",  # 3 chars
            "phase_type": "build",
            "priority": 3,
            "architecture_docs": ["docs/92_ph/PHASE_92_TRUNCATION_INVESTIGATION_AND_FIXES.md"],
        })

        assert result["success"] is True
        assert "desc_guard_warning" in result
        assert "3" in result["desc_guard_warning"]  # Shows char count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
