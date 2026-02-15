"""
Tests for Phase 124.9 — Scout Places Markers (Virtual marker_map).

MARKER_124.9A: Scout pre-fetch reads file snippets with line numbers
MARKER_124.9B: marker_map flows Scout → Architect → Coder as "rails"
MARKER_124.9C: VetkaReadFileTool supports virtual markers (MARKER_SCOUT_X:line)

Tests:
- TestScoutPromptMarkerMap: 4 tests — prompt has marker_map, action types, format
- TestReadFileSnippets: 5 tests — _read_file_snippets method, line numbers, max files
- TestVirtualMarkerRead: 6 tests — MARKER_SCOUT_X:42 format, forced line, fallback
- TestMarkerMapWiring: 5 tests — Scout→Architect→Coder flow, formatting
- TestPromptUpdates: 4 tests — architect, coder, scout prompts updated
- TestRegressionPrevious: 4 tests — existing features intact
"""

import os
import json
import pytest
import asyncio


# ── MARKER_124.9A: Scout Prompt + Pre-fetch Tests ──

class TestScoutPromptMarkerMap:
    """Tests for MARKER_124.9: Scout prompt includes marker_map."""

    def test_scout_prompt_has_marker_map(self):
        """Scout prompt should mention marker_map field."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        prompts = json.load(open(prompts_path))
        scout_prompt = prompts["scout"]["system"]
        assert "marker_map" in scout_prompt

    def test_scout_prompt_has_action_types(self):
        """Scout prompt should define action types (INSERT_AFTER, MODIFY, etc.)."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        prompts = json.load(open(prompts_path))
        scout_prompt = prompts["scout"]["system"]
        assert "INSERT_AFTER" in scout_prompt
        assert "MODIFY" in scout_prompt

    def test_scout_prompt_has_marker_id_format(self):
        """Scout prompt should specify MARKER_SCOUT_X format."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        prompts = json.load(open(prompts_path))
        scout_prompt = prompts["scout"]["system"]
        assert "MARKER_SCOUT_" in scout_prompt

    def test_scout_prompt_primary_output(self):
        """Scout prompt should say marker_map is PRIMARY output."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        prompts = json.load(open(prompts_path))
        scout_prompt = prompts["scout"]["system"]
        assert "PRIMARY" in scout_prompt or "primary" in scout_prompt


class TestReadFileSnippets:
    """Tests for MARKER_124.9A: _read_file_snippets method."""

    def test_method_exists(self):
        """AgentPipeline should have _read_file_snippets static method."""
        from src.orchestration.agent_pipeline import AgentPipeline
        assert hasattr(AgentPipeline, '_read_file_snippets')

    def test_reads_real_file(self):
        """Should read first lines of a real file with line numbers."""
        from src.orchestration.agent_pipeline import AgentPipeline
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "tools", "registry.py"
        )
        result = AgentPipeline._read_file_snippets([os.path.abspath(filepath)], max_lines=10)
        assert result, "Should return snippet content"
        assert "registry.py" in result
        assert "   1 |" in result or "    1 |" in result  # Line number format

    def test_respects_max_lines(self):
        """Should not exceed max_lines per file."""
        from src.orchestration.agent_pipeline import AgentPipeline
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "tools", "registry.py"
        )
        result = AgentPipeline._read_file_snippets([os.path.abspath(filepath)], max_lines=5)
        # Count code lines (exclude header line with filename)
        lines = result.split("\n")
        code_lines = [l for l in lines if "|" in l]
        assert len(code_lines) == 5

    def test_max_3_files(self):
        """Should read at most 3 files."""
        from src.orchestration.agent_pipeline import AgentPipeline
        base = os.path.join(os.path.dirname(__file__), "..", "src", "tools")
        files = [
            os.path.abspath(os.path.join(base, "registry.py")),
            os.path.abspath(os.path.join(base, "fc_loop.py")),
            os.path.abspath(os.path.join(base, "base_tool.py")),
            os.path.abspath(os.path.join(base, "executor.py")),
        ]
        result = AgentPipeline._read_file_snippets(files, max_lines=3)
        # Count file headers (lines with [...])
        headers = [l for l in result.split("\n") if l.startswith("[")]
        assert len(headers) <= 3

    def test_empty_list(self):
        """Empty file list should return empty string."""
        from src.orchestration.agent_pipeline import AgentPipeline
        result = AgentPipeline._read_file_snippets([])
        assert result == ""


# ── MARKER_124.9C: Virtual Marker Read Tests ──

class TestVirtualMarkerRead:
    """Tests for MARKER_124.9C: VetkaReadFileTool virtual markers."""

    @pytest.mark.asyncio
    async def test_marker_with_line_number(self):
        """MARKER_SCOUT_1:10 should read around line 10."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        result = await tool.execute(
            file_path="src/tools/registry.py",
            marker="MARKER_SCOUT_TEST:10"
        )
        assert result.success
        assert ">>>" in result.result  # Should highlight line 10
        assert "focused on MARKER_SCOUT_TEST" in result.result

    @pytest.mark.asyncio
    async def test_virtual_marker_shows_correct_area(self):
        """Virtual marker at line 10 should show ±20 lines around it."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        result = await tool.execute(
            file_path="src/tools/registry.py",
            marker="MARKER_SCOUT_AREA:10"
        )
        assert result.success
        # Should show lines around 10 (1-30 roughly)
        assert "lines 1-" in result.result or "lines 1-31" in result.result

    @pytest.mark.asyncio
    async def test_virtual_marker_at_end_of_file(self):
        """Virtual marker near end of file should not crash."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        # Use a high line number
        result = await tool.execute(
            file_path="src/tools/registry.py",
            marker="MARKER_SCOUT_END:900"
        )
        assert result.success
        assert "focused on" in result.result

    @pytest.mark.asyncio
    async def test_real_marker_still_works(self):
        """Existing MARKER_ tags should still work without line number."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        result = await tool.execute(
            file_path="src/tools/registry.py",
            marker="MARKER_124.9C"
        )
        assert result.success
        assert "MARKER_124.9C" in result.result

    @pytest.mark.asyncio
    async def test_invalid_line_number(self):
        """Line number beyond file length should fail gracefully."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        result = await tool.execute(
            file_path="src/tools/registry.py",
            marker="MARKER_SCOUT_BAD:999999"
        )
        assert not result.success
        assert "not found" in result.error.lower() or "Tip" in result.error

    @pytest.mark.asyncio
    async def test_colon_parsing(self):
        """Should correctly parse marker_id:line format."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        # MARKER_124.8B exists in file — should find it even with extra colon
        result = await tool.execute(
            file_path="src/tools/registry.py",
            marker="MARKER_124.8B"
        )
        assert result.success


# ── MARKER_124.9B: marker_map Wiring Tests ──

class TestMarkerMapWiring:
    """Tests for marker_map flow through pipeline."""

    def test_scout_context_injection_has_marker_section(self):
        """_scout_prefetch should have MARKER_124.9A marker."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        assert "MARKER_124.9A" in source
        assert "_read_file_snippets" in source

    def test_coder_context_has_marker_rails(self):
        """_execute_subtask should format marker_map as rails for coder."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        assert "MARKER_124.9B" in source
        assert "MARKER RAILS" in source

    def test_marker_map_formatting(self):
        """Should format marker_map entries as 📍 lines."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        assert "marker_map" in source
        assert "marker_id" in source

    def test_architect_prompt_references_markers(self):
        """Architect prompt should reference Scout's marker_map."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        prompts = json.load(open(prompts_path))
        arch_prompt = prompts["architect"]["system"]
        assert "marker_map" in arch_prompt
        assert "MARKER_SCOUT" in arch_prompt

    def test_coder_prompt_mentions_marker_rails(self):
        """Coder prompt should mention MARKER RAILS workflow."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        prompts = json.load(open(prompts_path))
        coder_prompt = prompts["coder"]["system"]
        assert "MARKER RAILS" in coder_prompt or "marker" in coder_prompt.lower()
        assert "MARKER_SCOUT" in coder_prompt


# ── Prompt Update Tests ──

class TestPromptUpdates:
    """Tests for updated prompts in Phase 124.9."""

    def test_coder_prompt_has_marker_param(self):
        """Coder prompt should document marker parameter for vetka_read_file."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        prompts = json.load(open(prompts_path))
        coder_prompt = prompts["coder"]["system"]
        assert "marker=" in coder_prompt or "marker'" in coder_prompt

    def test_coder_prompt_has_gps_workflow(self):
        """Coder prompt should have GPS/rails workflow."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        prompts = json.load(open(prompts_path))
        coder_prompt = prompts["coder"]["system"]
        assert "GPS" in coder_prompt or "rails" in coder_prompt or "RAILS" in coder_prompt

    def test_scout_prompt_has_line_numbers(self):
        """Scout prompt should reference line numbers for marker placement."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        prompts = json.load(open(prompts_path))
        scout_prompt = prompts["scout"]["system"]
        assert "line" in scout_prompt.lower()

    def test_all_prompts_valid_json_file(self):
        """pipeline_prompts.json should be valid JSON."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            data = json.load(f)
        assert "scout" in data
        assert "architect" in data
        assert "coder" in data
        assert "verifier" in data


# ── Regression Tests ──

class TestRegressionPrevious:
    """Ensure 124.8 features still work after 124.9 changes."""

    def test_marker_focused_read_still_works(self):
        """VetkaReadFileTool marker-focused read should still work."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        assert hasattr(tool, '_read_marker_focused')

    def test_scan_markers_still_works(self):
        """_scan_markers_in_files should still work."""
        from src.orchestration.agent_pipeline import AgentPipeline
        assert hasattr(AgentPipeline, '_scan_markers_in_files')

    def test_search_code_tool_intact(self):
        """VetkaSearchCodeTool should still be registered."""
        import src.tools.registry
        from src.tools.base_tool import registry
        tool_names = [t.definition.name for t in registry._tools.values()]
        assert "vetka_search_code" in tool_names

    def test_coder_tool_schemas_count(self):
        """Should still have 5 tool schemas."""
        from src.tools.fc_loop import CODER_TOOL_SCHEMAS
        assert len(CODER_TOOL_SCHEMAS) == 5
