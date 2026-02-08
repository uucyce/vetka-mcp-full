"""
Phase 119.7: Tavily web search integration for @researcher.

Tests:
- TestWebSearchTool: schema, execute, no-key fallback, result formatting
- TestResearcherWebIntegration: web context injection, fallback, prompt
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.mcp.tools.web_search_tool import WebSearchTool


# --- TestWebSearchTool ---

class TestWebSearchTool:
    """Test WebSearchTool MCP tool."""

    def test_schema_has_required_query(self):
        tool = WebSearchTool()
        assert tool.name == "vetka_web_search"
        assert "query" in tool.schema["properties"]
        assert "query" in tool.schema["required"]

    def test_to_openai_schema(self):
        tool = WebSearchTool()
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "vetka_web_search"

    @patch("src.utils.unified_key_manager.get_key_manager")
    def test_execute_with_mock_tavily(self, mock_km):
        """Execute with mocked Tavily client."""
        mock_km.return_value.get_key_with_rotation.return_value = "tvly-dev-test123456789012"

        mock_response = {
            "results": [
                {
                    "title": "FastAPI Docs",
                    "url": "https://fastapi.tiangolo.com",
                    "content": "FastAPI is a modern web framework...",
                    "score": 0.95
                }
            ],
            "answer": "FastAPI is great."
        }

        with patch("tavily.TavilyClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.search.return_value = mock_response

            tool = WebSearchTool()
            result = tool.execute({"query": "FastAPI WebSockets"})

            assert result["success"] is True
            assert len(result["result"]["results"]) == 1
            assert result["result"]["results"][0]["title"] == "FastAPI Docs"
            assert result["result"]["answer"] == "FastAPI is great."
            mock_instance.search.assert_called_once()

    @patch("src.utils.unified_key_manager.get_key_manager")
    def test_no_key_graceful_fallback(self, mock_km):
        """No Tavily key returns graceful failure."""
        mock_km.return_value.get_key_with_rotation.return_value = None

        tool = WebSearchTool()
        result = tool.execute({"query": "test"})

        assert result["success"] is False
        assert "No Tavily API key" in result["error"]

    def test_empty_query_fails(self):
        tool = WebSearchTool()
        result = tool.execute({"query": ""})
        assert result["success"] is False

    @patch("src.utils.unified_key_manager.get_key_manager")
    def test_content_truncated(self, mock_km):
        """Long content is truncated to 500 chars."""
        mock_km.return_value.get_key_with_rotation.return_value = "tvly-dev-test123456789012"

        long_content = "x" * 1000
        mock_response = {
            "results": [{"title": "T", "url": "http://x", "content": long_content, "score": 0.5}]
        }

        with patch("tavily.TavilyClient") as MockClient:
            MockClient.return_value.search.return_value = mock_response

            tool = WebSearchTool()
            result = tool.execute({"query": "test"})

            assert result["success"] is True
            assert len(result["result"]["results"][0]["content"]) == 500


# --- TestResearcherWebIntegration ---

class TestResearcherWebIntegration:
    """Test that web search integrates into researcher pipeline."""

    def test_researcher_prompt_has_web_sources(self):
        """Researcher prompt JSON format includes web_sources field."""
        prompts_path = PROJECT_ROOT / "data" / "templates" / "pipeline_prompts.json"
        with open(prompts_path) as f:
            prompts = json.load(f)

        researcher_prompt = prompts["researcher"]["system"]
        assert "web_sources" in researcher_prompt
        assert "web search results" in researcher_prompt.lower()

    def test_web_search_in_safe_tools_allowlist(self):
        """vetka_web_search is in SAFE_FUNCTION_CALLING_TOOLS."""
        from src.mcp.tools.llm_call_tool import SAFE_FUNCTION_CALLING_TOOLS
        assert "vetka_web_search" in SAFE_FUNCTION_CALLING_TOOLS
