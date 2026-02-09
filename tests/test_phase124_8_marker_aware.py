"""
Tests for Phase 124.8 — Marker-Aware Search & Reading.

MARKER_124.8A: VetkaSearchCodeTool marker-aware ripgrep (context mode)
MARKER_124.8B: VetkaReadFileTool marker-focused reading (±20 lines)
MARKER_124.8C: Scout pre-fetch marker scanning (_scan_markers_in_files)

Tests:
- TestMarkerAwareRipgrep: 7 tests — marker detection, context parsing, output format
- TestMarkerFocusedRead: 8 tests — marker param, ±20 lines, START/END blocks, not found
- TestScoutMarkerScanning: 6 tests — _scan_markers_in_files, prefetch integration
- TestFCLoopMarkerSchema: 3 tests — schema has marker param, description
- TestRegressionPrevious: 4 tests — existing tools intact, schemas correct
"""

import os
import re
import pytest
import asyncio
import tempfile


# ── MARKER_124.8A: Marker-Aware Ripgrep Tests ──

class TestMarkerAwareRipgrep:
    """Tests for MARKER_124.8A: VetkaSearchCodeTool marker-aware ripgrep."""

    def test_has_parse_marker_context(self):
        """Tool should have _parse_marker_context static method."""
        from src.tools.registry import VetkaSearchCodeTool
        assert hasattr(VetkaSearchCodeTool, '_parse_marker_context')

    def test_parse_marker_context_single_file(self):
        """_parse_marker_context should group output by file."""
        from src.tools.registry import VetkaSearchCodeTool
        # Simulate rg -n -C 5 output
        rg_output = (
            "/project/src/store/useStore.ts:10:  // MARKER_108_3: toggle\n"
            "/project/src/store/useStore.ts-11-  const toggle = () => {\n"
            "/project/src/store/useStore.ts-12-    set({ bookmarked: !get().bookmarked })\n"
            "/project/src/store/useStore.ts-13-  }\n"
        )
        results = VetkaSearchCodeTool._parse_marker_context(rg_output, "MARKER_108_3", 5)
        assert len(results) >= 1
        assert "MARKER_108_3" in results[0].get("match", "")
        assert results[0].get("context", "")

    def test_parse_marker_context_empty_output(self):
        """Empty rg output should return empty list."""
        from src.tools.registry import VetkaSearchCodeTool
        results = VetkaSearchCodeTool._parse_marker_context("", "MARKER_XXX", 5)
        assert results == []

    def test_parse_marker_context_limit(self):
        """Should respect limit parameter."""
        from src.tools.registry import VetkaSearchCodeTool
        # Multiple files in output
        rg_output = ""
        for i in range(10):
            rg_output += f"/project/file{i}.ts:1: // MARKER_TEST_{i}\n"
            rg_output += f"/project/file{i}.ts-2-   code line\n"
            rg_output += "--\n"
        results = VetkaSearchCodeTool._parse_marker_context(rg_output, "MARKER_TEST", 3)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_ripgrep_marker_query_detection(self):
        """Queries starting with MARKER_ should trigger context mode."""
        from src.tools.registry import VetkaSearchCodeTool
        tool = VetkaSearchCodeTool()
        # This should use -C 5 mode instead of -l mode
        result = await tool._search_by_ripgrep("MARKER_124.8A", "", 5)
        # Should return results with context field (since MARKER_124.8A exists in registry.py)
        assert len(result) > 0, "MARKER_124.8A should be found by ripgrep"
        assert any(r.get("context") for r in result), "Marker results should include context"

    @pytest.mark.asyncio
    async def test_ripgrep_normal_query_no_context(self):
        """Non-marker queries should use file-listing mode (no context)."""
        from src.tools.registry import VetkaSearchCodeTool
        tool = VetkaSearchCodeTool()
        result = await tool._search_by_ripgrep("VetkaSearchCodeTool", "", 3)
        # Normal search returns paths without context
        for r in result:
            assert "context" not in r or r.get("context") == ""

    @pytest.mark.asyncio
    async def test_execute_marker_query_includes_context(self):
        """Full execute with MARKER_ query should include context in output."""
        from src.tools.registry import VetkaSearchCodeTool
        tool = VetkaSearchCodeTool()
        result = await tool.execute(query="MARKER_124.8A", limit=3)
        assert result.success
        # Result should contain "---" separator indicating context blocks
        assert "---" in result.result


# ── MARKER_124.8B: Marker-Focused Read Tests ──

class TestMarkerFocusedRead:
    """Tests for MARKER_124.8B: VetkaReadFileTool marker-focused reading."""

    def test_has_marker_param(self):
        """VetkaReadFileTool should accept 'marker' parameter."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        defn = tool.definition
        props = defn.parameters.get("properties", {})
        assert "marker" in props, "Definition should have 'marker' property"

    def test_has_marker_context_lines(self):
        """Tool should have _MARKER_CONTEXT_LINES constant."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        assert hasattr(tool, '_MARKER_CONTEXT_LINES')
        assert tool._MARKER_CONTEXT_LINES == 20

    def test_has_read_marker_focused(self):
        """Tool should have _read_marker_focused method."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        assert hasattr(tool, '_read_marker_focused')
        assert asyncio.iscoroutinefunction(tool._read_marker_focused)

    @pytest.mark.asyncio
    async def test_marker_focused_read_existing_marker(self):
        """Reading with a known marker should return focused content."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        result = await tool.execute(
            file_path="src/tools/registry.py",
            marker="MARKER_124.8B"
        )
        assert result.success
        assert "MARKER_124.8B" in result.result
        assert ">>>" in result.result, "Marker lines should have >>> prefix"
        assert "focused on" in result.result

    @pytest.mark.asyncio
    async def test_marker_focused_read_not_found(self):
        """Reading with non-existent marker should fail gracefully."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        result = await tool.execute(
            file_path="src/tools/registry.py",
            marker="MARKER_NONEXISTENT_999"
        )
        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_marker_focused_read_file_not_found(self):
        """Reading from non-existent file should fail gracefully."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        result = await tool.execute(
            file_path="nonexistent/file.py",
            marker="MARKER_XXX"
        )
        assert not result.success

    @pytest.mark.asyncio
    async def test_marker_focused_read_limited_lines(self):
        """Marker-focused read should return much fewer lines than full read."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()

        # Full read
        full_result = await tool.execute(file_path="src/tools/registry.py")
        # Marker-focused read
        marker_result = await tool.execute(
            file_path="src/tools/registry.py",
            marker="MARKER_124.8B"
        )

        assert full_result.success and marker_result.success
        full_lines = len(full_result.result.splitlines())
        marker_lines = len(marker_result.result.splitlines())
        # Marker read should be much smaller (±20 = ~41 lines + header vs 500+ lines)
        assert marker_lines < full_lines / 3, \
            f"Marker read ({marker_lines} lines) should be much smaller than full ({full_lines})"

    @pytest.mark.asyncio
    async def test_marker_focused_read_line_numbers(self):
        """Marker-focused read should include line numbers."""
        from src.tools.registry import VetkaReadFileTool
        tool = VetkaReadFileTool()
        result = await tool.execute(
            file_path="src/tools/registry.py",
            marker="MARKER_124.8B"
        )
        assert result.success
        # Should have line number patterns like ">>> 464 |" or "   465 |"
        assert re.search(r'\d+\s*\|', result.result), "Should contain line numbers"


# ── MARKER_124.8C: Scout Marker Scanning Tests ──

class TestScoutMarkerScanning:
    """Tests for MARKER_124.8C: Scout pre-fetch marker scanning."""

    def test_scan_markers_method_exists(self):
        """AgentPipeline should have _scan_markers_in_files method."""
        from src.orchestration.agent_pipeline import AgentPipeline
        assert hasattr(AgentPipeline, '_scan_markers_in_files')

    def test_scan_markers_finds_markers_in_registry(self):
        """Should find MARKER_ tags in registry.py."""
        from src.orchestration.agent_pipeline import AgentPipeline
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "tools", "registry.py"
        )
        result = AgentPipeline._scan_markers_in_files([os.path.abspath(filepath)])
        assert result, "Should find markers in registry.py"
        assert "MARKER_124" in result
        assert "registry.py" in result

    def test_scan_markers_empty_list(self):
        """Empty file list should return empty string."""
        from src.orchestration.agent_pipeline import AgentPipeline
        result = AgentPipeline._scan_markers_in_files([])
        assert result == ""

    def test_scan_markers_nonexistent_file(self):
        """Non-existent file should be skipped gracefully."""
        from src.orchestration.agent_pipeline import AgentPipeline
        result = AgentPipeline._scan_markers_in_files(["/nonexistent/file.py"])
        assert result == ""

    def test_scan_markers_max_20(self):
        """Should return max 20 marker lines."""
        from src.orchestration.agent_pipeline import AgentPipeline
        # agent_pipeline.py has 185 markers, but output should be capped at 20
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        result = AgentPipeline._scan_markers_in_files([os.path.abspath(filepath)])
        lines = [l for l in result.splitlines() if l.strip()]
        assert len(lines) <= 20, f"Should cap at 20 markers, got {len(lines)}"

    def test_scan_markers_format(self):
        """Each marker line should have format: name:line — MARKER_XXX — desc."""
        from src.orchestration.agent_pipeline import AgentPipeline
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "tools", "registry.py"
        )
        result = AgentPipeline._scan_markers_in_files([os.path.abspath(filepath)])
        lines = [l for l in result.splitlines() if l.strip()]
        assert len(lines) > 0
        # Each line: "  name:line — MARKER_XXX — desc"
        for line in lines[:3]:
            assert ":" in line, f"Missing colon in: {line}"
            assert "MARKER_" in line, f"Missing MARKER_ in: {line}"
            assert " — " in line, f"Missing separator in: {line}"


# ── FC Loop Schema Tests ──

class TestFCLoopMarkerSchema:
    """Tests for vetka_read_file schema with marker parameter."""

    def test_read_file_schema_has_marker(self):
        """vetka_read_file schema should have 'marker' property."""
        from src.tools.fc_loop import CODER_TOOL_SCHEMAS
        read_schema = None
        for s in CODER_TOOL_SCHEMAS:
            if s["function"]["name"] == "vetka_read_file":
                read_schema = s
                break
        assert read_schema is not None, "vetka_read_file schema not found"
        props = read_schema["function"]["parameters"]["properties"]
        assert "marker" in props, "Schema should have 'marker' property"

    def test_read_file_schema_marker_type(self):
        """marker property should be type string."""
        from src.tools.fc_loop import CODER_TOOL_SCHEMAS
        for s in CODER_TOOL_SCHEMAS:
            if s["function"]["name"] == "vetka_read_file":
                marker = s["function"]["parameters"]["properties"]["marker"]
                assert marker["type"] == "string"
                break

    def test_read_file_schema_marker_not_required(self):
        """marker should not be in required fields."""
        from src.tools.fc_loop import CODER_TOOL_SCHEMAS
        for s in CODER_TOOL_SCHEMAS:
            if s["function"]["name"] == "vetka_read_file":
                required = s["function"]["parameters"].get("required", [])
                assert "marker" not in required, "marker should be optional"
                break


# ── Regression Tests ──

class TestRegressionPrevious:
    """Ensure previous features still work after 124.8 changes."""

    def test_tool_registry_count(self):
        """Should still have at least 8 tools registered."""
        import src.tools.registry
        from src.tools.base_tool import registry
        assert len(registry._tools) >= 8

    def test_search_code_still_registered(self):
        """VetkaSearchCodeTool should still be registered."""
        import src.tools.registry
        from src.tools.base_tool import registry
        tool_names = [t.definition.name for t in registry._tools.values()]
        assert "vetka_search_code" in tool_names

    def test_coder_schemas_count(self):
        """Should still have 5 tool schemas."""
        from src.tools.fc_loop import CODER_TOOL_SCHEMAS
        assert len(CODER_TOOL_SCHEMAS) == 5

    def test_pipeline_coder_tools_unchanged(self):
        """PIPELINE_CODER_TOOLS should still have all 5 tools."""
        from src.tools.fc_loop import PIPELINE_CODER_TOOLS
        assert "vetka_read_file" in PIPELINE_CODER_TOOLS
        assert "vetka_search_semantic" in PIPELINE_CODER_TOOLS
        assert "vetka_search_files" in PIPELINE_CODER_TOOLS
        assert "vetka_search_code" in PIPELINE_CODER_TOOLS
        assert "vetka_list_files" in PIPELINE_CODER_TOOLS
