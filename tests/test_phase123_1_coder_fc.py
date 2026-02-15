"""
Phase 123.1: Coder Function Calling Tests

Tests for the shared async FC loop utility (fc_loop.py) and its integration
with the pipeline coder in agent_pipeline.py.

17 tests across 5 classes:
- TestFCLoopCore (5): Core FC loop behavior
- TestExtractToolCalls (3): Tool call extraction from responses
- TestCoderFCIntegration (4): Pipeline integration
- TestCoderToolSchemas (3): Tool schema validation
- TestCoderPrompt (2): Prompt enhancement validation
"""

import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Test Fixtures & Helpers
# ============================================================================

def make_llm_response(content: str, tool_calls=None):
    """Create a mock call_model_v2 response dict."""
    msg = {"content": content, "role": "assistant"}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {
        "message": msg,
        "model": "test-model",
        "provider": "test-provider",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50}
    }


def make_tool_call(name: str, args: dict, call_id: str = "call_0"):
    """Create a tool call dict in OpenAI format."""
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": args
        }
    }


def make_tool_result(success=True, result="file content here", error=None):
    """Create a mock ToolResult."""
    @dataclass
    class MockToolResult:
        success: bool
        result: any
        error: str = None
        execution_time_ms: float = 10.0
    return MockToolResult(success=success, result=result, error=error)


@pytest.fixture
def patch_fc_providers():
    """Patch fc_loop module-level call_model_v2 and SafeToolExecutor for testing."""
    import src.tools.fc_loop as fc_mod

    mock_call = AsyncMock()
    mock_executor_cls = MagicMock()
    mock_executor = MagicMock()
    mock_executor.execute = AsyncMock()
    mock_executor_cls.return_value = mock_executor

    # Save originals
    orig_ensure = fc_mod._ensure_provider_imports
    orig_call = fc_mod.call_model_v2
    orig_executor = fc_mod.SafeToolExecutor

    # Patch
    fc_mod._ensure_provider_imports = lambda: None
    fc_mod.call_model_v2 = mock_call
    fc_mod.SafeToolExecutor = mock_executor_cls

    yield mock_call, mock_executor

    # Restore
    fc_mod._ensure_provider_imports = orig_ensure
    fc_mod.call_model_v2 = orig_call
    fc_mod.SafeToolExecutor = orig_executor


# ============================================================================
# TestFCLoopCore — Core FC loop behavior
# ============================================================================

class TestFCLoopCore:
    """Test execute_fc_loop core functionality."""

    @pytest.mark.asyncio
    async def test_fc_loop_no_tool_calls(self, patch_fc_providers):
        """LLM responds immediately without tools → returns content directly."""
        from src.tools.fc_loop import execute_fc_loop
        mock_call, mock_executor = patch_fc_providers

        mock_response = make_llm_response("Here is the code:\n```python\nprint('hello')\n```")
        mock_call.return_value = mock_response

        result = await execute_fc_loop(
            model="test-model",
            messages=[{"role": "user", "content": "write code"}],
            tool_schemas=[{"type": "function", "function": {"name": "vetka_read_file"}}],
            max_turns=3,
        )

        assert result["content"] == "Here is the code:\n```python\nprint('hello')\n```"
        assert result["tool_executions"] == []
        assert result["turns_used"] == 0
        assert mock_call.call_count == 1  # Only initial call, no loop

    @pytest.mark.asyncio
    async def test_fc_loop_one_tool_turn(self, patch_fc_providers):
        """LLM calls vetka_read_file, gets result, then produces code."""
        from src.tools.fc_loop import execute_fc_loop
        mock_call, mock_executor = patch_fc_providers

        # Turn 1: LLM requests tool call
        tool_call = make_tool_call("vetka_read_file", {"file_path": "src/App.tsx"}, "call_1")
        response_with_tools = make_llm_response("", tool_calls=[tool_call])

        # Turn 2: LLM produces final code
        final_response = make_llm_response("```tsx\nexport const App = () => <div>Hello</div>\n```")

        mock_call.side_effect = [response_with_tools, final_response]
        mock_executor.execute.return_value = make_tool_result(
            success=True, result="export const App = () => <div/>;"
        )

        result = await execute_fc_loop(
            model="test-model",
            messages=[{"role": "user", "content": "implement App component"}],
            tool_schemas=[{"type": "function", "function": {"name": "vetka_read_file"}}],
        )

        assert "App" in result["content"]
        assert len(result["tool_executions"]) == 1
        assert result["tool_executions"][0]["name"] == "vetka_read_file"
        assert result["tool_executions"][0]["args"] == {"file_path": "src/App.tsx"}
        assert result["turns_used"] == 1
        assert mock_call.call_count == 2  # Initial + after tool result

    @pytest.mark.asyncio
    async def test_fc_loop_max_turns_limit(self, patch_fc_providers):
        """LLM keeps calling tools until max_turns → last turn has no tools (forces text)."""
        from src.tools.fc_loop import execute_fc_loop
        mock_call, mock_executor = patch_fc_providers

        tool_call = make_tool_call("vetka_read_file", {"file_path": "file.py"}, "call_x")
        response_with_tools = make_llm_response("", tool_calls=[tool_call])
        final_response = make_llm_response("final code output")

        # 3 turns: tool call → tool call → tool call → forced final (no tools param)
        mock_call.side_effect = [
            response_with_tools,  # Initial
            response_with_tools,  # Turn 1
            response_with_tools,  # Turn 2 (max_turns-1)
            final_response,       # Turn 3 (last, no tools)
        ]
        mock_executor.execute.return_value = make_tool_result(success=True, result="content")

        result = await execute_fc_loop(
            model="test-model",
            messages=[{"role": "user", "content": "task"}],
            tool_schemas=[{"type": "function", "function": {"name": "vetka_read_file"}}],
            max_turns=3,
        )

        assert result["content"] == "final code output"
        # On last turn, tools=None should be passed
        last_call_kwargs = mock_call.call_args_list[-1]
        assert last_call_kwargs.kwargs.get("tools") is None

    @pytest.mark.asyncio
    async def test_fc_loop_tool_execution_error(self, patch_fc_providers):
        """Tool fails → error result sent to LLM, loop continues."""
        from src.tools.fc_loop import execute_fc_loop
        mock_call, mock_executor = patch_fc_providers

        tool_call = make_tool_call("vetka_read_file", {"file_path": "missing.py"}, "call_err")
        response_with_tools = make_llm_response("", tool_calls=[tool_call])
        final_response = make_llm_response("code without the file")

        mock_call.side_effect = [response_with_tools, final_response]
        mock_executor.execute.return_value = make_tool_result(
            success=False, result=None, error="File not found"
        )

        result = await execute_fc_loop(
            model="test-model",
            messages=[{"role": "user", "content": "task"}],
            tool_schemas=[{"type": "function", "function": {"name": "vetka_read_file"}}],
        )

        assert result["content"] == "code without the file"
        assert len(result["tool_executions"]) == 1
        assert result["tool_executions"][0]["result"]["success"] is False

    @pytest.mark.asyncio
    async def test_fc_loop_progress_callback(self, patch_fc_providers):
        """Verifies progress_callback called for each tool execution."""
        from src.tools.fc_loop import execute_fc_loop
        mock_call, mock_executor = patch_fc_providers

        tool_call = make_tool_call("vetka_read_file", {"file_path": "src/store.ts"}, "call_p")
        response_with_tools = make_llm_response("", tool_calls=[tool_call])
        final_response = make_llm_response("code")

        mock_call.side_effect = [response_with_tools, final_response]
        mock_executor.execute.return_value = make_tool_result()

        progress_calls = []
        async def mock_progress(agent, msg):
            progress_calls.append((agent, msg))

        await execute_fc_loop(
            model="test-model",
            messages=[{"role": "user", "content": "task"}],
            tool_schemas=[{"type": "function", "function": {"name": "vetka_read_file"}}],
            progress_callback=mock_progress,
        )

        assert len(progress_calls) >= 1
        assert progress_calls[0][0] == "@coder"
        assert "src/store.ts" in progress_calls[0][1]


# ============================================================================
# TestExtractToolCalls — Tool call extraction
# ============================================================================

class TestExtractToolCalls:
    """Test extract_tool_calls helper for different response formats."""

    def test_extract_from_dict_response(self):
        """Standard dict format from OpenRouter/call_model_v2."""
        from src.tools.fc_loop import extract_tool_calls

        response = {
            "message": {
                "content": "",
                "role": "assistant",
                "tool_calls": [
                    {"id": "call_1", "function": {"name": "vetka_read_file", "arguments": {"file_path": "x.py"}}}
                ]
            }
        }
        result = extract_tool_calls(response)
        assert result is not None
        assert len(result) == 1
        assert result[0]["function"]["name"] == "vetka_read_file"

    def test_extract_from_pydantic_response(self):
        """Pydantic format from Ollama."""
        from src.tools.fc_loop import extract_tool_calls

        # Simulate Pydantic-like object
        class MockFunction:
            name = "vetka_search_semantic"
            arguments = {"query": "store"}

        class MockToolCall:
            id = "call_1"
            function = MockFunction()

        class MockMessage:
            tool_calls = [MockToolCall()]
            content = ""

        class MockResponse:
            message = MockMessage()

        result = extract_tool_calls(MockResponse())
        assert result is not None
        assert len(result) == 1

    def test_extract_none_when_no_calls(self):
        """No tool_calls → returns None."""
        from src.tools.fc_loop import extract_tool_calls

        response = {"message": {"content": "just text", "role": "assistant"}}
        assert extract_tool_calls(response) is None

        response2 = {"message": {"content": "text", "tool_calls": []}}
        assert extract_tool_calls(response2) is None

        response3 = {"message": {"content": "text", "tool_calls": None}}
        assert extract_tool_calls(response3) is None


# ============================================================================
# TestCoderFCIntegration — Pipeline integration
# ============================================================================

class TestCoderFCIntegration:
    """Test FC integration in agent_pipeline._execute_subtask."""

    def _make_pipeline(self, prompts=None):
        """Create a minimal AgentPipeline for testing."""
        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)
        pipeline.prompts = prompts or {
            "coder": {
                "system": "You are a coder with tools.",
                "temperature": 0.4,
                "model": "test-model",
            },
            "researcher": {
                "system": "You are a researcher.",
                "temperature": 0.3,
                "model": "test-researcher",
            }
        }
        pipeline.provider_override = None
        pipeline.chat_id = "test-chat"
        pipeline.auto_write = False
        pipeline.llm_tool = MagicMock()
        pipeline._last_used_model = ""
        pipeline._emit_progress = AsyncMock()
        # MARKER_126.0A stats counters
        pipeline._llm_calls = 0
        pipeline._tokens_in = 0
        pipeline._tokens_out = 0
        # MARKER_151.11A per-agent stats
        pipeline._agent_stats = {}
        # MARKER_150.2_PLAYGROUND: playground_root for FC loop base_path
        pipeline.playground_root = None
        return pipeline

    def _make_subtask(self, description="implement feature"):
        """Create a mock Subtask."""
        from src.orchestration.agent_pipeline import Subtask
        return Subtask(
            description=description,
            needs_research=False,
            marker="MARKER_TEST",
            context={}
        )

    @pytest.mark.asyncio
    async def test_coder_uses_fc_for_build(self):
        """phase_type='build' triggers FC loop when available."""
        pipeline = self._make_pipeline()
        subtask = self._make_subtask()

        fc_result = {
            "content": "```python\nprint('hello')\n```",
            "tool_executions": [{"name": "vetka_read_file", "args": {"file_path": "x.py"}, "result": {"success": True}}],
            "turns_used": 1,
            "model": "test-model"
        }

        with patch("src.orchestration.agent_pipeline.FC_LOOP_AVAILABLE", True), \
             patch("src.orchestration.agent_pipeline.execute_fc_loop", new_callable=AsyncMock) as mock_fc, \
             patch("src.orchestration.agent_pipeline.get_coder_tool_schemas") as mock_schemas:
            mock_fc.return_value = fc_result
            mock_schemas.return_value = [{"type": "function", "function": {"name": "vetka_read_file"}}]

            result = await pipeline._execute_subtask(subtask, "build")

        assert "print('hello')" in result
        mock_fc.assert_called_once()
        # Verify FC was called with correct params
        fc_kwargs = mock_fc.call_args
        assert fc_kwargs.kwargs["max_turns"] == 4  # MAX_FC_TURNS_CODER (124.5B: 3→4)

    @pytest.mark.asyncio
    async def test_coder_uses_fc_for_fix(self):
        """phase_type='fix' also triggers FC loop."""
        pipeline = self._make_pipeline()
        subtask = self._make_subtask("fix the bug")

        fc_result = {
            "content": "fixed code here",
            "tool_executions": [],
            "turns_used": 0,
            "model": "test-model"
        }

        with patch("src.orchestration.agent_pipeline.FC_LOOP_AVAILABLE", True), \
             patch("src.orchestration.agent_pipeline.execute_fc_loop", new_callable=AsyncMock) as mock_fc, \
             patch("src.orchestration.agent_pipeline.get_coder_tool_schemas") as mock_schemas:
            mock_fc.return_value = fc_result
            mock_schemas.return_value = [{"type": "function", "function": {"name": "vetka_read_file"}}]

            result = await pipeline._execute_subtask(subtask, "fix")

        assert "fixed code here" in result
        mock_fc.assert_called_once()

    @pytest.mark.asyncio
    async def test_coder_falls_back_on_fc_error(self):
        """FC raises exception → falls back to one-shot LLMCallTool."""
        pipeline = self._make_pipeline()
        subtask = self._make_subtask()

        # One-shot succeeds
        pipeline.llm_tool.execute.return_value = {
            "success": True,
            "result": {"content": "one-shot code", "model": "test-model"}
        }

        with patch("src.orchestration.agent_pipeline.FC_LOOP_AVAILABLE", True), \
             patch("src.orchestration.agent_pipeline.execute_fc_loop", new_callable=AsyncMock) as mock_fc, \
             patch("src.orchestration.agent_pipeline.get_coder_tool_schemas") as mock_schemas:
            mock_fc.side_effect = Exception("FC connection error")
            mock_schemas.return_value = [{"type": "function", "function": {"name": "vetka_read_file"}}]

            result = await pipeline._execute_subtask(subtask, "build")

        assert "one-shot code" in result
        # Verify fallback to tool.execute was used
        pipeline.llm_tool.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_coder_no_fc_for_research(self):
        """phase_type='research' uses one-shot, not FC."""
        pipeline = self._make_pipeline()
        subtask = self._make_subtask("research the topic")

        pipeline.llm_tool.execute.return_value = {
            "success": True,
            "result": {"content": "research findings", "model": "test-model"}
        }

        with patch("src.orchestration.agent_pipeline.FC_LOOP_AVAILABLE", True), \
             patch("src.orchestration.agent_pipeline.execute_fc_loop", new_callable=AsyncMock) as mock_fc:

            result = await pipeline._execute_subtask(subtask, "research")

        assert "research findings" in result
        mock_fc.assert_not_called()  # FC should NOT be used for research


# ============================================================================
# TestCoderToolSchemas — Tool schema validation
# ============================================================================

class TestCoderToolSchemas:
    """Test get_coder_tool_schemas and CODER_TOOL_SCHEMAS."""

    def test_get_coder_tool_schemas_returns_list(self):
        """Returns non-empty list of tool schemas."""
        from src.tools.fc_loop import get_coder_tool_schemas
        schemas = get_coder_tool_schemas()
        assert isinstance(schemas, list)
        assert len(schemas) == 5  # 5 coder tools (added vetka_search_code in 124.7)

    def test_schemas_are_read_only(self):
        """No write tools (vetka_edit_file, vetka_git_commit) in schemas."""
        from src.tools.fc_loop import get_coder_tool_schemas, PIPELINE_CODER_TOOLS
        schemas = get_coder_tool_schemas()
        tool_names = [s["function"]["name"] for s in schemas]

        write_tools = ["vetka_edit_file", "vetka_git_commit", "vetka_call_model",
                       "write_code_file", "execute_code"]
        for wt in write_tools:
            assert wt not in tool_names, f"Write tool '{wt}' should not be in coder tools"
            assert wt not in PIPELINE_CODER_TOOLS

    def test_schemas_openai_format(self):
        """Each schema has correct OpenAI function calling format."""
        from src.tools.fc_loop import get_coder_tool_schemas
        schemas = get_coder_tool_schemas()
        for schema in schemas:
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]
            assert schema["function"]["parameters"]["type"] == "object"


# ============================================================================
# TestCoderPrompt — Prompt enhancement validation
# ============================================================================

class TestCoderPrompt:
    """Test coder system prompt mentions tools and workflow."""

    def test_prompt_mentions_tools(self):
        """Coder system prompt includes tool names."""
        prompts_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "templates", "pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            prompts = json.load(f)

        coder_prompt = prompts["coder"]["system"]
        assert "vetka_read_file" in coder_prompt
        assert "vetka_search_semantic" in coder_prompt
        assert "vetka_search_code" in coder_prompt  # 124.7: primary search tool
        assert "vetka_list_files" in coder_prompt

    def test_prompt_mentions_workflow(self):
        """Coder prompt instructs to read files BEFORE writing code."""
        prompts_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "templates", "pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            prompts = json.load(f)

        coder_prompt = prompts["coder"]["system"]
        assert "read" in coder_prompt.lower()
        # Phase 124.4: prompt uses "WORKFLOW" section with auto-read awareness
        assert "WORKFLOW" in coder_prompt
        assert "NEVER ask questions" in coder_prompt


# =============================================================================
# MARKER_124.1_TESTS: Tests for Phase 124.1 fixes
# =============================================================================

class TestCleanTextToolCalls:
    """Phase 124.1: Test text tool_call cleanup from final response."""

    def test_clean_removes_text_tool_calls(self):
        """Text-format <tool_call> tags are removed from content."""
        from src.tools.fc_loop import _clean_text_tool_calls

        content = """Here is the code:
```typescript
const foo = "bar";
```
<tool_call>
<function=vetka_list_files>
<parameter=path>
src
</parameter>
</function>
</tool_call>"""

        cleaned = _clean_text_tool_calls(content)
        assert "<tool_call>" not in cleaned
        assert "const foo" in cleaned

    def test_clean_preserves_content_without_tool_calls(self):
        """Content without tool_call tags is unchanged."""
        from src.tools.fc_loop import _clean_text_tool_calls

        content = "```typescript\nconst x = 1;\n```"
        assert _clean_text_tool_calls(content) == content

    def test_clean_returns_original_if_all_tool_calls(self):
        """If entire content is tool_calls, return original (not empty)."""
        from src.tools.fc_loop import _clean_text_tool_calls

        content = """<tool_call>
<function=vetka_read_file>
<parameter=file_path>src/App.tsx</parameter>
</function>
</tool_call>"""

        cleaned = _clean_text_tool_calls(content)
        # Should return original since cleaning would produce empty string
        assert cleaned == content

    def test_clean_handles_empty_string(self):
        """Empty string returns empty string."""
        from src.tools.fc_loop import _clean_text_tool_calls
        assert _clean_text_tool_calls("") == ""
        assert _clean_text_tool_calls(None) is None

    def test_clean_handles_multiple_tool_calls(self):
        """Multiple text tool_calls are all removed."""
        from src.tools.fc_loop import _clean_text_tool_calls

        content = """Some code here
<tool_call>
<function=vetka_read_file>
<parameter=file_path>a.ts</parameter>
</function>
</tool_call>
More code
<tool_call>
<function=vetka_list_files>
<parameter=path>src</parameter>
</function>
</tool_call>
Final code"""

        cleaned = _clean_text_tool_calls(content)
        assert "<tool_call>" not in cleaned
        assert "Some code here" in cleaned
        assert "More code" in cleaned
        assert "Final code" in cleaned
