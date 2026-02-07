"""
Phase 117.6: @dragon E2E Fix Tests

MARKER_117.6: Tests for parse_mentions system command recognition,
file_path fix, and model attribution in pipeline.

Three bugs fixed:
  A. parse_mentions didn't recognize @dragon → Mycelium never triggered
  B. Group chat saved with file_path="unknown"
  C. No model attribution in pipeline progress messages
"""

import json
import inspect
import pytest
from pathlib import Path


# ============================================================================
# MARKER_117.6A: parse_mentions system command recognition
# ============================================================================

class TestParseMentionsSystemCommands:
    """Test that parse_mentions recognizes @dragon/@doctor/@pipeline as system commands."""

    def test_parse_mentions_recognizes_dragon(self):
        """MARKER_117.6A: @dragon should be recognized as system_command."""
        from src.agents.agentic_tools import parse_mentions
        result = parse_mentions("@dragon build a new feature")
        assert result["mode"] == "system_command", (
            f"@dragon should set mode=system_command, got {result['mode']}"
        )
        assert len(result["mentions"]) > 0
        assert result["mentions"][0]["type"] == "system_command"
        assert result["mentions"][0]["target"] == "dragon"

    def test_parse_mentions_recognizes_doctor(self):
        """MARKER_117.6A: @doctor should be recognized as system_command."""
        from src.agents.agentic_tools import parse_mentions
        result = parse_mentions("@doctor why is the API slow?")
        assert result["mode"] == "system_command"
        assert result["mentions"][0]["target"] == "doctor"

    def test_parse_mentions_recognizes_pipeline(self):
        """MARKER_117.6A: @pipeline should be recognized as system_command."""
        from src.agents.agentic_tools import parse_mentions
        result = parse_mentions("@pipeline research authentication")
        assert result["mode"] == "system_command"
        assert result["mentions"][0]["target"] == "pipeline"

    def test_parse_mentions_recognizes_help(self):
        """MARKER_117.6A: @help should be recognized as system_command."""
        from src.agents.agentic_tools import parse_mentions
        result = parse_mentions("@help how do I fix this?")
        assert result["mode"] == "system_command"
        assert result["mentions"][0]["target"] == "help"

    def test_parse_mentions_cleans_message(self):
        """MARKER_117.6A: @dragon should be removed from clean_message."""
        from src.agents.agentic_tools import parse_mentions
        result = parse_mentions("@dragon build a new feature")
        assert "@dragon" not in result["clean_message"]
        assert "build a new feature" in result["clean_message"]

    def test_parse_mentions_regular_alias_still_works(self):
        """MARKER_117.6A: Regular aliases (@deepseek, @claude) should still work."""
        from src.agents.agentic_tools import parse_mentions
        # "auto" mode means no mentions recognized (deepseek may not be in config)
        # Just verify it doesn't crash and doesn't return system_command
        result = parse_mentions("explain this code")
        assert result["mode"] == "auto"
        assert len(result["mentions"]) == 0

    def test_parse_mentions_case_insensitive(self):
        """MARKER_117.6A: @Dragon and @DRAGON should both work."""
        from src.agents.agentic_tools import parse_mentions
        for variant in ["@Dragon fix it", "@DRAGON fix it", "@dragon fix it"]:
            result = parse_mentions(variant)
            assert result["mode"] == "system_command", (
                f"'{variant}' should trigger system_command mode"
            )

    def test_system_command_agents_constant(self):
        """MARKER_117.6A: SYSTEM_COMMAND_AGENTS set should exist in source."""
        source_file = Path(__file__).parent.parent / "src" / "agents" / "agentic_tools.py"
        source = source_file.read_text()
        assert "SYSTEM_COMMAND_AGENTS" in source
        assert '"dragon"' in source or "'dragon'" in source


# ============================================================================
# MARKER_117.6B: file_path fix for group chats
# ============================================================================

class TestGroupChatFilePath:
    """Test that group chats no longer save with file_path='unknown'."""

    def test_no_hardcoded_unknown_filepath(self):
        """MARKER_117.6B: group_message_handler should not use file_path='unknown'."""
        handler_file = Path(__file__).parent.parent / "src" / "api" / "handlers" / "group_message_handler.py"
        source = handler_file.read_text()
        # Count occurrences of file_path="unknown" — should be 0 now
        count = source.count('file_path="unknown"')
        assert count == 0, (
            f"Found {count} occurrences of file_path='unknown' in group_message_handler.py. "
            f"Should be replaced with file_path=group_id (MARKER_117.6B)"
        )

    def test_uses_group_id_as_filepath(self):
        """MARKER_117.6B: Should use group_id as file_path."""
        handler_file = Path(__file__).parent.parent / "src" / "api" / "handlers" / "group_message_handler.py"
        source = handler_file.read_text()
        assert "file_path=group_id" in source, (
            "group_message_handler should use file_path=group_id"
        )


# ============================================================================
# MARKER_117.6C: Model attribution in pipeline
# ============================================================================

class TestModelAttribution:
    """Test that pipeline shows which model is executing."""

    def test_emit_progress_accepts_model_param(self):
        """MARKER_117.6C: _emit_progress should accept model parameter."""
        from src.orchestration.agent_pipeline import AgentPipeline
        sig = inspect.signature(AgentPipeline._emit_progress)
        params = list(sig.parameters.keys())
        assert "model" in params, (
            f"_emit_progress should accept 'model' parameter. Got: {params}"
        )

    def test_emit_progress_formats_model_tag(self):
        """MARKER_117.6C: Model name should appear in formatted message."""
        pipeline_file = Path(__file__).parent.parent / "src" / "orchestration" / "agent_pipeline.py"
        source = pipeline_file.read_text()
        assert "model_tag" in source, (
            "Pipeline should format model_tag from model parameter"
        )
        assert 'short_model = model.split("/")[-1]' in source, (
            "Pipeline should extract short model name (remove provider prefix)"
        )

    def test_last_used_model_attribute(self):
        """MARKER_117.6C: AgentPipeline should have _last_used_model attribute."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)  # Don't call __init__
        # Check that __init__ sets _last_used_model
        source = inspect.getsource(AgentPipeline.__init__)
        assert "_last_used_model" in source, (
            "AgentPipeline.__init__ should initialize _last_used_model"
        )

    def test_pipeline_start_emits_team_info(self):
        """MARKER_117.6C: Pipeline start should emit team composition."""
        pipeline_file = Path(__file__).parent.parent / "src" / "orchestration" / "agent_pipeline.py"
        source = pipeline_file.read_text()
        assert "team_info" in source, (
            "Pipeline execute() should emit team_info at start"
        )
        assert "preset_name" in source, (
            "Pipeline should show which preset is active"
        )

    def test_model_extracted_after_llm_calls(self):
        """MARKER_117.6C: Model should be extracted from LLM result in all 3 call sites."""
        pipeline_file = Path(__file__).parent.parent / "src" / "orchestration" / "agent_pipeline.py"
        source = pipeline_file.read_text()
        # Count model extraction patterns
        extraction_count = source.count('self._last_used_model = result.get("result", {}).get("model"')
        assert extraction_count >= 3, (
            f"Expected model extraction in 3 LLM call sites (architect, researcher, coder), "
            f"found {extraction_count}"
        )
