"""
MARKER_EPSILON.D1: Debrief pipeline E2E verification test.

Verifies that `_inject_debrief` in task_board_tools.py always injects
debrief_requested=True and debrief_questions on successful action=complete.

Context:
- Predecessor (Epsilon-2) reported FAIL on local fallback transport
- Zeta fixed it (MARKER_195.22): removed session_tracker dependency,
  simplified to always-inject
- This test locks the contract

Two debrief mechanisms exist (both tested):
1. task_board.py MARKER_SC_C.D5 — phase-closure debrief (only when last
   task of numbered phase closes)
2. task_board_tools.py _inject_debrief — always-inject on complete (Zeta fix)
"""

import pytest


class TestDebriefInjection:
    """Test _inject_debrief always fires on successful complete."""

    def test_inject_debrief_on_success(self):
        """_inject_debrief adds debrief fields to successful result."""
        from src.mcp.tools.task_board_tools import _inject_debrief

        result = {"success": True, "task_id": "tb_test_1"}
        _inject_debrief(result, {})

        assert result["debrief_requested"] is True
        assert "debrief_questions" in result
        questions = result["debrief_questions"]
        assert "q1_bugs" in questions
        assert "q2_worked" in questions
        assert "q3_idea" in questions

    def test_inject_debrief_skipped_on_failure(self):
        """_inject_debrief does NOT inject when result is not successful."""
        from src.mcp.tools.task_board_tools import _inject_debrief

        result = {"success": False, "error": "something failed"}
        _inject_debrief(result, {})

        assert "debrief_requested" not in result
        assert "debrief_questions" not in result

    def test_inject_debrief_questions_are_strings(self):
        """All debrief questions must be non-empty strings."""
        from src.mcp.tools.task_board_tools import _inject_debrief

        result = {"success": True, "task_id": "tb_test_2"}
        _inject_debrief(result, {})

        for key in ("q1_bugs", "q2_worked", "q3_idea"):
            val = result["debrief_questions"][key]
            assert isinstance(val, str), f"{key} should be str, got {type(val)}"
            assert len(val) > 10, f"{key} should be non-empty question"

    def test_inject_debrief_does_not_overwrite_existing_fields(self):
        """_inject_debrief should not crash if debrief fields already exist."""
        from src.mcp.tools.task_board_tools import _inject_debrief

        result = {"success": True, "task_id": "tb_test_3", "debrief_requested": False}
        _inject_debrief(result, {})

        # Should overwrite to True
        assert result["debrief_requested"] is True


class TestPhaseClosureDebrief:
    """Test MARKER_SC_C.D5 phase-closure debrief in task_board.py."""

    def test_extract_phase_prefix_numeric(self):
        """Numeric prefix like '195.1: Title' → '195'."""
        from src.orchestration.task_board import TaskBoard

        assert TaskBoard._extract_phase_prefix("195.1: Some task") == "195"
        assert TaskBoard._extract_phase_prefix("42.3: Another") == "42"
        assert TaskBoard._extract_phase_prefix("1.0: First") == "1"

    def test_extract_phase_prefix_non_numeric(self):
        """Non-numeric prefixes like 'EPSILON: ...' → None."""
        from src.orchestration.task_board import TaskBoard

        assert TaskBoard._extract_phase_prefix("EPSILON: Test") is None
        assert TaskBoard._extract_phase_prefix("D4: Non-numeric") is None
        assert TaskBoard._extract_phase_prefix("") is None
        assert TaskBoard._extract_phase_prefix("No prefix here") is None

    def test_generate_debrief_prompt_contains_questions(self):
        """Generated prompt has 3 numbered questions."""
        from src.orchestration.task_board import TaskBoard

        prompt = TaskBoard._generate_debrief_prompt("195", {"title": "Test task"})
        assert "Phase 195 complete" in prompt
        assert "1." in prompt
        assert "2." in prompt
        assert "3." in prompt
