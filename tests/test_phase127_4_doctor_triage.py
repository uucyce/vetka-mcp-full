"""
Phase 127.4: Doctor Triage Flow Tests

Tests for MARKER_127.4A/B/C:
- Doctor shows analysis in chat before dispatch
- Improved prompt with examples, estimated_subtasks, key_files
- Quick-action buttons (1d, 2d, h)
"""

import os
import json
import pytest

# Helper to read source files
def _read_source(path: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, path), "r") as f:
        return f.read()


class TestPhase127_4A_DoctorChatFeedback:
    """Tests for MARKER_127.4A: Doctor shows analysis in chat."""

    def test_marker_127_4a_in_group_handler(self):
        """MARKER_127.4A should be in group_message_handler.py."""
        source = _read_source("src/api/handlers/group_message_handler.py")
        assert "MARKER_127.4A" in source

    def test_doctor_emits_analyzing_message(self):
        """Doctor should emit 'Analyzing task...' message first."""
        source = _read_source("src/api/handlers/group_message_handler.py")
        assert "Analyzing task..." in source

    def test_doctor_shows_abstraction_result(self):
        """Doctor should show abstraction level in chat."""
        source = _read_source("src/api/handlers/group_message_handler.py")
        assert "Abstraction:" in source
        assert "Reformulated:" in source

    def test_doctor_shows_suggested_team(self):
        """Doctor should show suggested team in chat."""
        source = _read_source("src/api/handlers/group_message_handler.py")
        assert "Suggested:" in source
        assert "suggested_team" in source


class TestPhase127_4B_DoctorPrompt:
    """Tests for MARKER_127.4B: Improved doctor prompt."""

    def test_doctor_prompt_has_examples(self):
        """Doctor prompt should have concrete/moderate/abstract examples."""
        prompts_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data/templates/pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            prompts = json.load(f)

        doctor_prompt = prompts.get("doctor", {}).get("system", "")
        assert "CONCRETE task" in doctor_prompt
        assert "MODERATE task" in doctor_prompt
        assert "ABSTRACT task" in doctor_prompt

    def test_doctor_prompt_has_estimated_subtasks(self):
        """Doctor prompt should output estimated_subtasks."""
        prompts_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data/templates/pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            prompts = json.load(f)

        doctor_prompt = prompts.get("doctor", {}).get("system", "")
        assert "estimated_subtasks" in doctor_prompt

    def test_doctor_prompt_has_key_files(self):
        """Doctor prompt should output key_files."""
        prompts_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data/templates/pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            prompts = json.load(f)

        doctor_prompt = prompts.get("doctor", {}).get("system", "")
        assert "key_files" in doctor_prompt


class TestPhase127_4C_QuickActions:
    """Tests for MARKER_127.4C: Quick-action buttons."""

    def test_marker_127_4c_in_group_handler(self):
        """MARKER_127.4C should be in group_message_handler.py."""
        source = _read_source("src/api/handlers/group_message_handler.py")
        assert "MARKER_127.4C" in source

    def test_quick_action_handler_exists(self):
        """_handle_doctor_quick_action function should exist."""
        source = _read_source("src/api/handlers/group_message_handler.py")
        assert "async def _handle_doctor_quick_action" in source

    def test_quick_actions_1d_2d_h(self):
        """Quick actions 1d, 2d, h should be handled."""
        source = _read_source("src/api/handlers/group_message_handler.py")
        assert 'action == "1d"' in source
        assert 'action == "2d"' in source
        assert 'action == "h"' in source

    def test_quick_action_routing(self):
        """Quick-action routing should be wired in message handler."""
        source = _read_source("src/api/handlers/group_message_handler.py")
        assert '_handle_doctor_quick_action(group_id, content)' in source
        assert '"1d", "2d", "h"' in source

    def test_pending_tasks_storage(self):
        """_DOCTOR_PENDING_TASKS dict should exist for quick-action state."""
        source = _read_source("src/api/handlers/group_message_handler.py")
        assert "_DOCTOR_PENDING_TASKS" in source


class TestPhase127_4_Integration:
    """Integration tests for doctor triage flow."""

    def test_doctor_triage_function_exists(self):
        """_doctor_triage function should exist with updated markers."""
        source = _read_source("src/api/handlers/group_message_handler.py")
        assert "async def _doctor_triage" in source
        assert "MARKER_127.4A" in source

    def test_abstract_task_goes_to_hold(self):
        """Abstract tasks should be set to hold status."""
        source = _read_source("src/api/handlers/group_message_handler.py")
        assert 'status="hold"' in source
        assert "needs-approve" in source

    def test_reformulated_task_shown(self):
        """Reformulated task should be shown in chat."""
        source = _read_source("src/api/handlers/group_message_handler.py")
        assert "reformulated" in source
        assert "Reformulated:" in source
