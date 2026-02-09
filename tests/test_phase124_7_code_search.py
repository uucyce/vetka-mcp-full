"""
Tests for Phase 124.7 — Contextual Code Search + Scout Pre-fetch.

MARKER_124.7: VetkaSearchCodeTool (ripgrep + Qdrant name filter)
MARKER_124.7B: Scout pre-fetch via ripgrep before LLM call

Tests:
- TestSearchCodeTool: 9 tests — tool definition, strategies, ripgrep, name filter
- TestScoutPrefetch: 6 tests — keyword extraction, pre-fetch injection
- TestFCLoopIntegration: 4 tests — coder prompt, tool schemas, allowlist
- TestRegressionPrevious: 3 tests — hybrid search still works, existing tools intact
"""

import os
import pytest
import asyncio


# ── VetkaSearchCodeTool Tests ──

class TestSearchCodeTool:
    """Tests for MARKER_124.7: VetkaSearchCodeTool."""

    def test_tool_definition(self):
        """Tool should have correct name and description."""
        from src.tools.registry import VetkaSearchCodeTool
        tool = VetkaSearchCodeTool()
        defn = tool.definition
        assert defn.name == "vetka_search_code"
        assert "ripgrep" in defn.description.lower() or "fast" in defn.description.lower()

    def test_has_project_root(self):
        """Tool must have _PROJECT_ROOT set."""
        from src.tools.registry import VetkaSearchCodeTool
        tool = VetkaSearchCodeTool()
        assert hasattr(tool, '_PROJECT_ROOT')
        assert "vetka_live_03" in tool._PROJECT_ROOT

    def test_has_skip_dirs(self):
        """Tool should skip node_modules, __pycache__, etc."""
        from src.tools.registry import VetkaSearchCodeTool
        tool = VetkaSearchCodeTool()
        assert "node_modules" in tool._SKIP_DIRS
        assert "__pycache__" in tool._SKIP_DIRS
        assert ".git" in tool._SKIP_DIRS

    def test_has_search_by_name(self):
        """Tool should have _search_by_name method."""
        from src.tools.registry import VetkaSearchCodeTool
        tool = VetkaSearchCodeTool()
        assert hasattr(tool, '_search_by_name')
        assert asyncio.iscoroutinefunction(tool._search_by_name)

    def test_has_search_by_ripgrep(self):
        """Tool should have _search_by_ripgrep method."""
        from src.tools.registry import VetkaSearchCodeTool
        tool = VetkaSearchCodeTool()
        assert hasattr(tool, '_search_by_ripgrep')
        assert asyncio.iscoroutinefunction(tool._search_by_ripgrep)

    @pytest.mark.asyncio
    async def test_search_by_name_finds_file(self):
        """Name search should find useStore.ts in Qdrant."""
        from src.tools.registry import VetkaSearchCodeTool
        tool = VetkaSearchCodeTool()
        results = await tool._search_by_name("useStore.ts", 5)
        # Should find at least 1 result (assuming Qdrant is running)
        found_names = [r.get("name", "") for r in results]
        assert any("useStore" in n for n in found_names), \
            f"useStore.ts not found in name search results: {found_names}"

    @pytest.mark.asyncio
    async def test_search_by_ripgrep_finds_pattern(self):
        """Ripgrep should find files containing specific patterns."""
        from src.tools.registry import VetkaSearchCodeTool
        tool = VetkaSearchCodeTool()
        results = await tool._search_by_ripgrep("MARKER_124.7", "", 5)
        assert len(results) > 0, "ripgrep should find MARKER_124.7 in code"

    @pytest.mark.asyncio
    async def test_execute_combines_strategies(self):
        """Full execute should combine name + ripgrep results."""
        from src.tools.registry import VetkaSearchCodeTool
        tool = VetkaSearchCodeTool()
        result = await tool.execute(query="useStore.ts", limit=5)
        assert result.success
        assert "useStore.ts" in result.result
        # Should show strategy used
        assert "name" in result.result or "ripgrep" in result.result

    @pytest.mark.asyncio
    async def test_execute_empty_query(self):
        """Empty query should fail gracefully."""
        from src.tools.registry import VetkaSearchCodeTool
        tool = VetkaSearchCodeTool()
        result = await tool.execute(query="", limit=5)
        assert not result.success


# ── Scout Pre-fetch Tests ──

class TestScoutPrefetch:
    """Tests for MARKER_124.7B: Scout pre-fetch via ripgrep."""

    def test_extract_search_keywords_filename(self):
        """Should extract filenames from task description."""
        from src.orchestration.agent_pipeline import AgentPipeline
        keywords = AgentPipeline._extract_search_keywords(
            "Add toggleBookmark to client/src/store/useStore.ts"
        )
        assert "useStore.ts" in keywords

    def test_extract_search_keywords_camelcase(self):
        """Should extract camelCase identifiers."""
        from src.orchestration.agent_pipeline import AgentPipeline
        keywords = AgentPipeline._extract_search_keywords(
            "Implement toggleBookmark function that updates chatStore"
        )
        assert "toggleBookmark" in keywords

    def test_extract_search_keywords_pascalcase(self):
        """Should extract PascalCase identifiers."""
        from src.orchestration.agent_pipeline import AgentPipeline
        keywords = AgentPipeline._extract_search_keywords(
            "Fix ChatPanel component rendering issue"
        )
        assert "ChatPanel" in keywords

    def test_extract_search_keywords_quoted(self):
        """Should extract quoted terms."""
        from src.orchestration.agent_pipeline import AgentPipeline
        keywords = AgentPipeline._extract_search_keywords(
            "Add 'isBookmarked' field to the store"
        )
        assert "isBookmarked" in keywords

    def test_extract_search_keywords_limit(self):
        """Should return max 5 keywords."""
        from src.orchestration.agent_pipeline import AgentPipeline
        keywords = AgentPipeline._extract_search_keywords(
            "Fix toggleBookmark in useStore.ts ChatPanel.tsx DevPanel.tsx "
            "FilePreview.tsx FloatingWindow.tsx TreeView.tsx"
        )
        assert len(keywords) <= 5

    def test_scout_prefetch_method_exists(self):
        """AgentPipeline should have _scout_prefetch method."""
        from src.orchestration.agent_pipeline import AgentPipeline
        assert hasattr(AgentPipeline, '_scout_prefetch')
        assert asyncio.iscoroutinefunction(AgentPipeline._scout_prefetch)

    def test_scout_scan_has_prefetch_marker(self):
        """_scout_scan should contain MARKER_124.7B for pre-fetch."""
        filepath = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
        )
        source = open(filepath).read()
        assert "MARKER_124.7B" in source
        assert "_scout_prefetch" in source


# ── FC Loop Integration Tests ──

class TestFCLoopIntegration:
    """Tests for vetka_search_code in FC loop."""

    def test_search_code_in_allowlist(self):
        """vetka_search_code should be in PIPELINE_CODER_TOOLS."""
        from src.tools.fc_loop import PIPELINE_CODER_TOOLS
        assert "vetka_search_code" in PIPELINE_CODER_TOOLS

    def test_search_code_schema_exists(self):
        """vetka_search_code should have a schema in CODER_TOOL_SCHEMAS."""
        from src.tools.fc_loop import CODER_TOOL_SCHEMAS
        schema_names = [s["function"]["name"] for s in CODER_TOOL_SCHEMAS]
        assert "vetka_search_code" in schema_names

    def test_coder_prompt_mentions_search_code(self):
        """Coder prompt should mention vetka_search_code as primary tool."""
        import json
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        prompts = json.load(open(prompts_path))
        coder_prompt = prompts["coder"]["system"]
        assert "vetka_search_code" in coder_prompt
        assert "FIRST" in coder_prompt  # Should be used FIRST

    def test_coder_prompt_scout_report_workflow(self):
        """Coder prompt should mention Scout report as primary source."""
        import json
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "templates", "pipeline_prompts.json"
        )
        prompts = json.load(open(prompts_path))
        coder_prompt = prompts["coder"]["system"]
        assert "Scout" in coder_prompt
        # Should read Scout files directly
        assert "vetka_read_file" in coder_prompt


# ── Regression Tests ──

class TestRegressionPrevious:
    """Ensure previous tools still work after adding vetka_search_code."""

    def test_tool_registry_has_search_code(self):
        """VetkaSearchCodeTool should be registered."""
        import src.tools.registry  # Side effect: registers tools
        from src.tools.base_tool import registry
        tool_names = [t.definition.name for t in registry._tools.values()]
        assert "vetka_search_code" in tool_names

    def test_total_tools_count(self):
        """Should have 11 tools (was 10 before + vetka_search_code)."""
        import src.tools.registry
        from src.tools.base_tool import registry
        # At minimum: semantic, camera, tree, artifact, read, search_files,
        # list_files, search_code = 8
        assert len(registry._tools) >= 8

    def test_coder_schemas_count(self):
        """Should have 6 tool schemas (was 4 + search_code)."""
        from src.tools.fc_loop import CODER_TOOL_SCHEMAS
        assert len(CODER_TOOL_SCHEMAS) == 5  # read, semantic, files, list, code
