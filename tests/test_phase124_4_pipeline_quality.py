"""
Phase 124.4 — Pipeline Quality Fixes
Tests for: VetkaSearchFilesTool REST API, FC recovery on empty content,
updated coder prompt, _build_tool_context_summary.

@phase: 124.4
@created: 2026-02-09
"""
import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ── Test VetkaSearchFilesTool REST API (MARKER_124.4A) ──

class TestSearchFilesToolRESTAPI:
    """VetkaSearchFilesTool should use REST API, not direct Qdrant."""

    def _get_class_source(self, class_name):
        """Read source of a specific class from registry.py."""
        import os
        filepath = os.path.join(os.path.dirname(__file__), "..", "src", "tools", "registry.py")
        source = open(filepath).read()
        start = source.find(f"class {class_name}")
        end = source.find("\nclass ", start + 1)
        if end == -1:
            end = len(source)
        return source[start:end]

    def test_no_memory_manager_dependency(self):
        """Tool should NOT import or use get_memory_manager."""
        class_source = self._get_class_source("VetkaSearchFilesTool")
        assert "get_memory_manager" not in class_source, \
            "VetkaSearchFilesTool should not use get_memory_manager (direct Qdrant is broken)"

    def test_no_semantic_tagger_dependency(self):
        """Tool should NOT import SemanticTagger."""
        class_source = self._get_class_source("VetkaSearchFilesTool")
        assert "SemanticTagger" not in class_source, \
            "VetkaSearchFilesTool should not use SemanticTagger (broken direct Qdrant)"

    def test_delegates_to_semantic(self):
        """Tool should delegate to VetkaSearchSemanticTool (hybrid search)."""
        class_source = self._get_class_source("VetkaSearchFilesTool")
        assert "VetkaSearchSemanticTool" in class_source, "Should delegate to VetkaSearchSemanticTool"

    def test_definition_unchanged(self):
        """Tool definition should still be vetka_search_files."""
        from src.tools.registry import VetkaSearchFilesTool
        tool = VetkaSearchFilesTool()
        assert tool.definition.name == "vetka_search_files"
        assert "query" in tool.definition.parameters["properties"]

    @pytest.mark.asyncio
    async def test_query_too_short(self):
        """Should reject queries shorter than 2 chars."""
        from src.tools.registry import VetkaSearchFilesTool
        tool = VetkaSearchFilesTool()
        result = await tool.execute(query="a")
        assert not result.success
        assert "too short" in result.error

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Should reject empty query."""
        from src.tools.registry import VetkaSearchFilesTool
        tool = VetkaSearchFilesTool()
        result = await tool.execute(query="")
        assert not result.success


# ── Test FC Recovery on Empty Content (MARKER_124.4B) ──

class TestBuildToolContextSummary:
    """Tests for _build_tool_context_summary helper."""

    def test_empty_executions(self):
        """Should return default message for empty list."""
        from src.tools.fc_loop import _build_tool_context_summary
        result = _build_tool_context_summary([])
        assert "No relevant context" in result

    def test_read_file_success(self):
        """Should include file content from successful reads."""
        from src.tools.fc_loop import _build_tool_context_summary
        execs = [
            {
                "name": "vetka_read_file",
                "args": {"file_path": "src/store.ts"},
                "result": {"success": True, "result": "export const useStore = create(...)"}
            }
        ]
        result = _build_tool_context_summary(execs)
        assert "src/store.ts" in result
        assert "useStore" in result

    def test_search_results(self):
        """Should include search result summaries."""
        from src.tools.fc_loop import _build_tool_context_summary
        execs = [
            {
                "name": "vetka_search_semantic",
                "args": {"query": "store"},
                "result": {"success": True, "result": "Found 5 files: src/store.ts, src/hooks.ts"}
            }
        ]
        result = _build_tool_context_summary(execs)
        assert "Search results" in result
        assert "store.ts" in result

    def test_truncates_long_content(self):
        """Should truncate file content over 3000 chars."""
        from src.tools.fc_loop import _build_tool_context_summary
        long_content = "x" * 5000
        execs = [
            {
                "name": "vetka_read_file",
                "args": {"file_path": "big.py"},
                "result": {"success": True, "result": long_content}
            }
        ]
        result = _build_tool_context_summary(execs)
        assert "truncated" in result
        assert len(result) < 4000  # Should be truncated

    def test_skips_failed_reads(self):
        """Should skip failed tool executions."""
        from src.tools.fc_loop import _build_tool_context_summary
        execs = [
            {
                "name": "vetka_read_file",
                "args": {"file_path": "missing.py"},
                "result": {"success": False, "result": None, "error": "Not found"}
            }
        ]
        result = _build_tool_context_summary(execs)
        assert "No relevant context" in result

    def test_mixed_tool_types(self):
        """Should handle mix of search and read results."""
        from src.tools.fc_loop import _build_tool_context_summary
        execs = [
            {
                "name": "vetka_search_semantic",
                "args": {"query": "store"},
                "result": {"success": True, "result": "Found files"}
            },
            {
                "name": "vetka_read_file",
                "args": {"file_path": "src/store.ts"},
                "result": {"success": True, "result": "const store = {}"}
            },
            {
                "name": "vetka_list_files",  # Not included in summary
                "args": {"path": "src/"},
                "result": {"success": True, "result": ["file1.ts"]}
            }
        ]
        result = _build_tool_context_summary(execs)
        assert "Search results" in result
        assert "src/store.ts" in result
        # list_files should be skipped
        assert "file1.ts" not in result


class TestFCRecoveryCall:
    """Test that FC loop makes recovery call when content is empty after cleanup."""

    def test_recovery_marker_exists(self):
        """MARKER_124.4B should exist in fc_loop.py."""
        import src.tools.fc_loop as fc_mod
        source = open(fc_mod.__file__).read()
        assert "MARKER_124.4B" in source, "Recovery code marker should exist"

    def test_recovery_function_exists(self):
        """_build_tool_context_summary should be importable."""
        from src.tools.fc_loop import _build_tool_context_summary
        assert callable(_build_tool_context_summary)

    def test_recovery_only_on_empty_with_tools(self):
        """Recovery should NOT trigger if content is non-empty."""
        import src.tools.fc_loop as fc_mod
        source = open(fc_mod.__file__).read()
        # Check the condition: "not content.strip() and all_tool_executions"
        assert "not content.strip() and all_tool_executions" in source, \
            "Recovery should only trigger when content is empty AND tools were used"


# ── Test Updated Coder Prompt ──

class TestCoderPromptUpdate:
    """Verify coder prompt mentions auto-read and code output format."""

    def test_prompt_mentions_auto_read(self):
        """Coder prompt should tell coder about auto-read feature."""
        with open("data/templates/pipeline_prompts.json") as f:
            prompts = json.load(f)
        coder_system = prompts["coder"]["system"]
        assert "auto-read" in coder_system.lower() or "Auto-reads" in coder_system, \
            "Coder should know about auto-read feature"

    def test_prompt_requires_code_blocks(self):
        """Coder prompt should require ``` code blocks in output."""
        with open("data/templates/pipeline_prompts.json") as f:
            prompts = json.load(f)
        coder_system = prompts["coder"]["system"]
        assert "```" in coder_system, "Should require code blocks in output"

    def test_prompt_forbids_tool_call_text(self):
        """Coder prompt should say NOT to output <tool_call> tags."""
        with open("data/templates/pipeline_prompts.json") as f:
            prompts = json.load(f)
        coder_system = prompts["coder"]["system"]
        assert "tool_call" in coder_system, "Should warn against text tool_call output"

    def test_prompt_minimum_code_length(self):
        """Prompt should specify minimum code output length."""
        with open("data/templates/pipeline_prompts.json") as f:
            prompts = json.load(f)
        coder_system = prompts["coder"]["system"]
        assert "10 lines" in coder_system or "AT LEAST" in coder_system, \
            "Should specify minimum code output"

    def test_prompt_has_search_workflow(self):
        """Prompt should describe search → auto-read → write workflow."""
        with open("data/templates/pipeline_prompts.json") as f:
            prompts = json.load(f)
        coder_system = prompts["coder"]["system"]
        assert "search_semantic" in coder_system or "vetka_search" in coder_system
        assert "vetka_read_file" in coder_system


# ── Regression: Previous fixes still work ──

class TestRegressionPreviousFixes:
    """Ensure 124.3E fixes still work after 124.4 changes."""

    def test_extract_file_paths_absolute(self):
        """_extract_file_paths should handle absolute paths."""
        from src.tools.fc_loop import _extract_file_paths
        text = "  /Users/dan/VETKA_Project/vetka_live_03/src/store.py (score: 0.8)"
        paths = _extract_file_paths(text)
        assert any("store.py" in p for p in paths)

    def test_normalize_path(self):
        """_normalize_path should strip project root."""
        from src.tools.fc_loop import _normalize_path
        result = _normalize_path("/Users/dan/Documents/VETKA_Project/vetka_live_03/src/main.py")
        assert result == "src/main.py"

    def test_is_useful_file(self):
        """_is_useful_file should filter __init__.py and test files."""
        from src.tools.fc_loop import _is_useful_file
        assert not _is_useful_file("src/__init__.py")
        assert not _is_useful_file("tests/test_main.py")
        assert _is_useful_file("src/store.ts")

    def test_clean_text_tool_calls(self):
        """_clean_text_tool_calls should strip XML tool calls (Qwen format)."""
        from src.tools.fc_loop import _clean_text_tool_calls
        # Qwen format: <tool_call><function=name>{"args":"val"}</function></tool_call>
        content = '<tool_call>\n<function=vetka_read_file>{"file_path":"src/store.ts"}</function>\n</tool_call>\nsome code here'
        result = _clean_text_tool_calls(content)
        assert "<tool_call>" not in result
        assert "some code here" in result


# ── Phase 124.5 Tests: Hybrid Search + Max Turns ──

class TestHybridSearch:
    """Tests for MARKER_124.5A: hybrid search (semantic + code-only)."""

    def test_semantic_tool_has_code_extensions(self):
        """VetkaSearchSemanticTool should define code extensions."""
        from src.tools.registry import VetkaSearchSemanticTool
        tool = VetkaSearchSemanticTool()
        assert hasattr(tool, '_CODE_EXTENSIONS')
        assert ".ts" in tool._CODE_EXTENSIONS
        assert ".tsx" in tool._CODE_EXTENSIONS
        assert ".py" in tool._CODE_EXTENSIONS

    def test_semantic_tool_has_skip_names(self):
        """Should skip __init__.py."""
        from src.tools.registry import VetkaSearchSemanticTool
        tool = VetkaSearchSemanticTool()
        assert "__init__.py" in tool._SKIP_NAMES

    def test_search_code_only_method_exists(self):
        """_search_code_only helper should exist."""
        from src.tools.registry import VetkaSearchSemanticTool
        tool = VetkaSearchSemanticTool()
        assert hasattr(tool, '_search_code_only')
        assert asyncio.iscoroutinefunction(tool._search_code_only)

    def test_get_query_embedding_method_exists(self):
        """_get_query_embedding helper should exist."""
        from src.tools.registry import VetkaSearchSemanticTool
        assert hasattr(VetkaSearchSemanticTool, '_get_query_embedding')

    def test_hybrid_search_marker_in_code(self):
        """MARKER_124.5A should exist in registry.py."""
        import os
        filepath = os.path.join(os.path.dirname(__file__), "..", "src", "tools", "registry.py")
        source = open(filepath).read()
        assert "MARKER_124.5A" in source

    def test_search_files_delegates(self):
        """VetkaSearchFilesTool should delegate to VetkaSearchSemanticTool."""
        import os
        filepath = os.path.join(os.path.dirname(__file__), "..", "src", "tools", "registry.py")
        source = open(filepath).read()
        start = source.find("class VetkaSearchFilesTool")
        end = source.find("\nclass ", start + 1)
        class_source = source[start:end]
        assert "VetkaSearchSemanticTool" in class_source


class TestMaxTurnsUpdate:
    """Test MARKER_124.5B: max_turns increased from 3 to 4."""

    def test_max_fc_turns_is_4(self):
        """MAX_FC_TURNS_CODER should be 4 (was 3)."""
        from src.tools.fc_loop import MAX_FC_TURNS_CODER
        assert MAX_FC_TURNS_CODER == 4, f"Expected 4, got {MAX_FC_TURNS_CODER}"

    def test_max_fc_turns_default_unchanged(self):
        """MAX_FC_TURNS_DEFAULT should still be 5."""
        from src.tools.fc_loop import MAX_FC_TURNS_DEFAULT
        assert MAX_FC_TURNS_DEFAULT == 5


# ── Phase 124.6 Tests: Improved Search Filters ──

class TestImprovedSearchFilters:
    """Tests for MARKER_124.6A: refined Qdrant search filters."""

    def test_frontend_extensions_defined(self):
        """Should have separate frontend extensions list."""
        from src.tools.registry import VetkaSearchSemanticTool
        tool = VetkaSearchSemanticTool()
        assert hasattr(tool, '_FRONTEND_EXTENSIONS')
        assert ".ts" in tool._FRONTEND_EXTENSIONS
        assert ".tsx" in tool._FRONTEND_EXTENSIONS
        assert ".py" not in tool._FRONTEND_EXTENSIONS

    def test_skip_path_parts_defined(self):
        """Should skip node_modules, __pycache__, etc."""
        from src.tools.registry import VetkaSearchSemanticTool
        tool = VetkaSearchSemanticTool()
        assert hasattr(tool, '_SKIP_PATH_PARTS')
        assert "node_modules" in tool._SKIP_PATH_PARTS
        assert "__pycache__" in tool._SKIP_PATH_PARTS

    def test_skip_names_extended(self):
        """Should skip __init__.py, index.ts, index.js."""
        from src.tools.registry import VetkaSearchSemanticTool
        tool = VetkaSearchSemanticTool()
        assert "__init__.py" in tool._SKIP_NAMES
        assert "index.ts" in tool._SKIP_NAMES
        assert "index.js" in tool._SKIP_NAMES

    def test_two_pass_search_marker_in_code(self):
        """MARKER_124.6A should exist in registry.py."""
        import os
        filepath = os.path.join(os.path.dirname(__file__), "..", "src", "tools", "registry.py")
        source = open(filepath).read()
        assert "MARKER_124.6A" in source

    @pytest.mark.asyncio
    async def test_code_only_filters_node_modules(self):
        """Code-only search should not return node_modules paths."""
        from src.tools.registry import VetkaSearchSemanticTool
        tool = VetkaSearchSemanticTool()
        results = await tool._search_code_only("main", 20)
        for r in results:
            assert "node_modules" not in r.get("path", ""), \
                f"node_modules should be filtered: {r['path']}"

    @pytest.mark.asyncio
    async def test_code_only_filters_init_py(self):
        """Code-only search should not return __init__.py files."""
        from src.tools.registry import VetkaSearchSemanticTool
        tool = VetkaSearchSemanticTool()
        results = await tool._search_code_only("import", 20)
        for r in results:
            assert r.get("name") != "__init__.py", \
                f"__init__.py should be filtered: {r['path']}"

    @pytest.mark.asyncio
    async def test_hybrid_search_no_init_files(self):
        """Full hybrid search should not return __init__.py."""
        from src.tools.registry import VetkaSearchSemanticTool
        tool = VetkaSearchSemanticTool()
        result = await tool.execute(query="store management", limit=10)
        assert result.success
        assert "__init__.py" not in result.result
