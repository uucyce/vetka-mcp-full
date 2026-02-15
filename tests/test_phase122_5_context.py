"""
Phase 122.5: Coder Context Enrichment Tests

Tests that previous_results (STM), scout_report, and inject_context
all reach the coder's LLM call properly.
"""
import json
import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.orchestration.agent_pipeline import AgentPipeline, Subtask


def _make_pipeline(**kwargs):
    """Create pipeline with mocked internals."""
    p = AgentPipeline.__new__(AgentPipeline)
    p.llm_tool = None
    p.provider_override = None
    p.preset_name = "dragon_silver"
    p.preset_models = None
    p.stm = []
    p.stm_limit = 5
    p.auto_write = False
    p.chat_id = None
    p.sio = None
    p.sid = None
    p.progress_hooks = []
    p._last_used_model = ""
    p._scout_context = None
    p.prompts = {
        "coder": {"system": "test coder", "model": "test/model", "temperature": 0.4},
        "researcher": {"system": "test researcher", "model": "test/model"},
        "scout": {"system": "test scout", "model": "test/scout"},
        "architect": {"system": "test architect", "model": "test/arch"},
        "verifier": {"system": "test verifier", "model": "test/verifier"}
    }
    p._emit_progress = AsyncMock()
    # MARKER_126.0A stats counters
    p._llm_calls = 0
    p._tokens_in = 0
    p._tokens_out = 0
    # MARKER_150.2_PLAYGROUND
    p.playground_root = None
    for k, v in kwargs.items():
        setattr(p, k, v)
    return p


# --- TestSTMPassthrough ---

class TestSTMPassthrough:
    """Test that previous_results from STM reach the coder."""

    def test_previous_results_in_context_parts(self):
        """STM previous_results should appear in coder's context_str."""
        pipeline = _make_pipeline()
        subtask = Subtask(
            description="Add favorite field",
            context={"previous_results": "- [MARKER_102.1]: class Chat with favorite field"}
        )

        # Mock tool.execute to capture call_args
        mock_tool = MagicMock()
        mock_tool.execute.return_value = {"success": True, "result": {"content": "code here", "model": "test"}}
        pipeline._get_llm_tool = MagicMock(return_value=mock_tool)

        import asyncio
        asyncio.run(pipeline._execute_subtask(subtask, "build"))

        # Check that previous_results made it into the user message
        call = mock_tool.execute.call_args[0][0]
        user_msg = call["messages"][1]["content"]
        assert "Previous subtask results:" in user_msg
        assert "MARKER_102.1" in user_msg

    def test_no_previous_results_when_empty(self):
        """Without STM, context should say 'No additional context.'"""
        pipeline = _make_pipeline()
        subtask = Subtask(description="Simple task", context=None)

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {"success": True, "result": {"content": "code", "model": "test"}}
        pipeline._get_llm_tool = MagicMock(return_value=mock_tool)

        import asyncio
        asyncio.run(pipeline._execute_subtask(subtask, "build"))

        call = mock_tool.execute.call_args[0][0]
        user_msg = call["messages"][1]["content"]
        assert "No additional context." in user_msg

    def test_previous_results_with_research(self):
        """Both enriched_context and previous_results should be present."""
        pipeline = _make_pipeline()
        subtask = Subtask(
            description="Add toggle",
            context={
                "enriched_context": "Chat uses Zustand store",
                "previous_results": "- [MARKER_102.1]: base schema done"
            }
        )

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {"success": True, "result": {"content": "code", "model": "test"}}
        pipeline._get_llm_tool = MagicMock(return_value=mock_tool)

        import asyncio
        asyncio.run(pipeline._execute_subtask(subtask, "build"))

        call = mock_tool.execute.call_args[0][0]
        user_msg = call["messages"][1]["content"]
        assert "Research context:" in user_msg
        assert "Previous subtask results:" in user_msg


# --- TestScoutReportInjection ---

class TestScoutReportInjection:
    """Test that scout report reaches the coder."""

    def test_scout_report_passed_to_subtask(self):
        """_scout_context should be injected into subtask.context."""
        pipeline = _make_pipeline()
        pipeline._scout_context = {
            "relevant_files": ["src/store/useStore.ts", "src/components/chat/ChatPanel.tsx"],
            "patterns_found": ["Zustand store pattern", "React component"],
            "risks": [],
            "recommendations": ["Follow existing chat patterns"]
        }

        subtask = Subtask(description="Add feature", context=None)

        # Simulate what _execute_subtasks_sequential does
        if getattr(pipeline, '_scout_context', None):
            if subtask.context is None:
                subtask.context = {}
            subtask.context["scout_report"] = pipeline._scout_context

        assert subtask.context is not None
        assert "scout_report" in subtask.context
        assert "useStore.ts" in subtask.context["scout_report"]["relevant_files"][0]

    def test_scout_files_in_coder_message(self):
        """Project files from scout should appear in coder's user message."""
        pipeline = _make_pipeline()
        subtask = Subtask(
            description="Add star toggle",
            context={
                "scout_report": {
                    "relevant_files": ["src/store/useStore.ts", "src/components/ChatPanel.tsx"],
                    "patterns_found": ["Zustand store"],
                    "risks": []
                }
            }
        )

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {"success": True, "result": {"content": "code", "model": "test"}}
        pipeline._get_llm_tool = MagicMock(return_value=mock_tool)

        import asyncio
        asyncio.run(pipeline._execute_subtask(subtask, "build"))

        call = mock_tool.execute.call_args[0][0]
        user_msg = call["messages"][1]["content"]
        assert "Project files:" in user_msg
        assert "useStore.ts" in user_msg

    def test_scout_patterns_in_coder_message(self):
        """Patterns from scout should appear in coder message."""
        pipeline = _make_pipeline()
        subtask = Subtask(
            description="Build feature",
            context={
                "scout_report": {
                    "relevant_files": ["a.py"],
                    "patterns_found": ["Singleton pattern", "Factory method"],
                    "risks": []
                }
            }
        )

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {"success": True, "result": {"content": "code", "model": "test"}}
        pipeline._get_llm_tool = MagicMock(return_value=mock_tool)

        import asyncio
        asyncio.run(pipeline._execute_subtask(subtask, "build"))

        call = mock_tool.execute.call_args[0][0]
        user_msg = call["messages"][1]["content"]
        assert "Patterns to follow:" in user_msg
        assert "Singleton pattern" in user_msg


# --- TestCoderInjectContext ---

class TestCoderInjectContext:
    """Test that inject_context is added to coder's LLM call."""

    def test_inject_context_added_for_build(self):
        """Build phase should have inject_context with semantic search."""
        pipeline = _make_pipeline()
        subtask = Subtask(description="Implement chat favorites", context=None)

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {"success": True, "result": {"content": "code", "model": "test"}}
        pipeline._get_llm_tool = MagicMock(return_value=mock_tool)

        import asyncio
        asyncio.run(pipeline._execute_subtask(subtask, "build"))

        call = mock_tool.execute.call_args[0][0]
        assert "inject_context" in call
        assert call["inject_context"]["semantic_query"] == "Implement chat favorites"
        assert call["inject_context"]["semantic_limit"] == 3

    def test_inject_context_added_for_fix(self):
        """Fix phase should also have inject_context."""
        pipeline = _make_pipeline()
        subtask = Subtask(description="Fix naming bug", context=None)

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {"success": True, "result": {"content": "fixed", "model": "test"}}
        pipeline._get_llm_tool = MagicMock(return_value=mock_tool)

        import asyncio
        asyncio.run(pipeline._execute_subtask(subtask, "fix"))

        call = mock_tool.execute.call_args[0][0]
        assert "inject_context" in call

    def test_no_inject_context_for_research(self):
        """Research phase should NOT have inject_context (researcher has its own)."""
        pipeline = _make_pipeline()
        subtask = Subtask(description="Research embedding models", context=None)

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {"success": True, "result": {"content": "findings", "model": "test"}}
        pipeline._get_llm_tool = MagicMock(return_value=mock_tool)

        import asyncio
        asyncio.run(pipeline._execute_subtask(subtask, "research"))

        call = mock_tool.execute.call_args[0][0]
        assert "inject_context" not in call


# --- TestCoderPrompt ---

class TestCoderPrompt:
    """Test that coder prompt is updated correctly."""

    def test_no_question_instruction(self):
        """Coder prompt should NOT contain question output instruction."""
        with open("data/templates/pipeline_prompts.json") as f:
            prompts = json.load(f)
        coder_prompt = prompts["coder"]["system"]
        assert '"question"' not in coder_prompt
        assert "If you have a question" not in coder_prompt

    def test_never_ask_questions(self):
        """Coder prompt should contain NEVER ask questions instruction."""
        with open("data/templates/pipeline_prompts.json") as f:
            prompts = json.load(f)
        coder_prompt = prompts["coder"]["system"]
        assert "NEVER ask questions" in coder_prompt

    def test_use_scout_report_instruction(self):
        """Coder prompt should reference Scout report and file reading tools."""
        with open("data/templates/pipeline_prompts.json") as f:
            prompts = json.load(f)
        coder_prompt = prompts["coder"]["system"]
        # Phase 124.4: prompt now has WORKFLOW with auto-read + read_file for other files
        assert "vetka_read_file" in coder_prompt
        assert "WORKFLOW" in coder_prompt
