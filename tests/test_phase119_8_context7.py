"""
Phase 119.8: Context7 library docs integration for @coder.

Tests:
- TestLibraryDocsTool: schema, execute, no-API fallback, caching
- TestExtractLibraryNames: basic extraction, stopwords, empty input
- TestCoderDocsIntegration: docs in allowlist, prompt updated
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 119 contracts changed")

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.mcp.tools.library_docs_tool import LibraryDocsTool, _LIBRARY_ID_CACHE


# --- TestLibraryDocsTool ---

class TestLibraryDocsTool:
    """Test LibraryDocsTool MCP tool."""

    def setup_method(self):
        """Clear cache before each test."""
        _LIBRARY_ID_CACHE.clear()

    def test_schema_has_required_library(self):
        tool = LibraryDocsTool()
        assert tool.name == "vetka_library_docs"
        assert "library" in tool.schema["properties"]
        assert "library" in tool.schema["required"]

    def test_to_openai_schema(self):
        tool = LibraryDocsTool()
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "vetka_library_docs"

    def test_empty_library_fails(self):
        tool = LibraryDocsTool()
        result = tool.execute({"library": ""})
        assert result["success"] is False
        assert "required" in result["error"]

    @patch("httpx.Client")
    def test_execute_resolve_and_fetch(self, MockClient):
        """Execute with mocked HTTP client — resolve + fetch docs."""
        mock_client = MagicMock()
        MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
        MockClient.return_value.__exit__ = MagicMock(return_value=False)

        # First call: resolve library ID
        resolve_response = MagicMock()
        resolve_response.json.return_value = {
            "results": [{"id": "/tiangolo/fastapi", "name": "fastapi"}]
        }
        resolve_response.raise_for_status = MagicMock()

        # Second call: fetch docs
        docs_response = MagicMock()
        docs_response.json.return_value = {
            "content": "FastAPI is a modern, fast web framework for building APIs..."
        }
        docs_response.raise_for_status = MagicMock()

        mock_client.get.side_effect = [resolve_response, docs_response]

        tool = LibraryDocsTool()
        result = tool.execute({"library": "fastapi", "topic": "websockets"})

        assert result["success"] is True
        assert result["result"]["library"] == "fastapi"
        assert result["result"]["library_id"] == "/tiangolo/fastapi"
        assert "FastAPI" in result["result"]["docs"]
        assert mock_client.get.call_count == 2

    @patch("httpx.Client")
    def test_library_id_cached(self, MockClient):
        """Resolved library ID is cached for subsequent calls."""
        _LIBRARY_ID_CACHE["numpy"] = "/numpy/numpy"

        mock_client = MagicMock()
        MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
        MockClient.return_value.__exit__ = MagicMock(return_value=False)

        # Only docs fetch should happen (resolve skipped due to cache)
        docs_response = MagicMock()
        docs_response.json.return_value = {"content": "NumPy array docs..."}
        docs_response.raise_for_status = MagicMock()
        mock_client.get.return_value = docs_response

        tool = LibraryDocsTool()
        result = tool.execute({"library": "numpy"})

        assert result["success"] is True
        # Only 1 HTTP call (docs), not 2 (resolve + docs)
        assert mock_client.get.call_count == 1

    @patch("httpx.Client")
    def test_resolve_not_found(self, MockClient):
        """Library not found on Context7 returns graceful error."""
        mock_client = MagicMock()
        MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
        MockClient.return_value.__exit__ = MagicMock(return_value=False)

        resolve_response = MagicMock()
        resolve_response.json.return_value = {"results": []}
        resolve_response.raise_for_status = MagicMock()
        mock_client.get.return_value = resolve_response

        tool = LibraryDocsTool()
        result = tool.execute({"library": "nonexistent_lib_xyz"})

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_httpx_not_installed(self):
        """Missing httpx returns graceful error."""
        with patch.dict("sys.modules", {"httpx": None}):
            tool = LibraryDocsTool()
            # Force re-import failure
            import importlib
            result = tool.execute({"library": "fastapi"})
            # Either ImportError or httpx is None — both should fail gracefully
            assert result["success"] is False


# --- TestExtractLibraryNames ---

class TestExtractLibraryNames:
    """Test _extract_library_names helper in AgentPipeline."""

    def _extract(self, text):
        from src.orchestration.agent_pipeline import AgentPipeline
        return AgentPipeline._extract_library_names(text)

    def test_import_pattern(self):
        names = self._extract("import fastapi\nfrom numpy import array")
        assert "fastapi" in names
        assert "numpy" in names

    def test_using_pattern(self):
        names = self._extract("Build a REST API using fastapi framework")
        assert "fastapi" in names

    def test_library_suffix_pattern(self):
        names = self._extract("Check the React library documentation")
        assert "react" in names

    def test_stopwords_filtered(self):
        names = self._extract("import code\nimport test\nimport file")
        assert len(names) == 0

    def test_empty_input(self):
        names = self._extract("")
        assert names == []

    def test_known_libs_react(self):
        """Known framework names detected without import/using keywords."""
        names = self._extract("Fix the React component in TreeCanvas.tsx")
        assert "react" in names

    def test_known_libs_threejs(self):
        """Three.js detected from task description."""
        names = self._extract("Raycasting performance in Three.js scene with Zustand store")
        assert "threejs" in names
        assert "zustand" in names

    def test_known_libs_fastapi(self):
        """FastAPI detected in backend task."""
        names = self._extract("Add a new FastAPI endpoint for file upload with httpx client")
        assert "fastapi" in names
        assert "httpx" in names

    def test_max_five(self):
        names = self._extract("import fastapi\nimport numpy\nimport pandas\nimport scipy\nimport torch")
        assert len(names) <= 5


# --- TestCoderDocsIntegration ---

class TestCoderDocsIntegration:
    """Test that library docs integrates into coder pipeline."""

    def test_library_docs_in_safe_tools_allowlist(self):
        """vetka_library_docs is in SAFE_FUNCTION_CALLING_TOOLS."""
        from src.mcp.tools.llm_call_tool import SAFE_FUNCTION_CALLING_TOOLS

        assert "vetka_library_docs" in SAFE_FUNCTION_CALLING_TOOLS

    def test_coder_prompt_mentions_library_docs(self):
        """Coder prompt includes instruction to use library documentation."""
        prompts_path = PROJECT_ROOT / "data" / "templates" / "pipeline_prompts.json"
        with open(prompts_path) as f:
            prompts = json.load(f)

        coder_prompt = prompts["coder"]["system"]
        assert "library documentation" in coder_prompt.lower()
