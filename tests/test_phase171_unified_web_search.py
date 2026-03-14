from unittest.mock import patch

from src.api.handlers.unified_search import run_unified_search


def test_run_unified_search_web_returns_results():
    payload = {
        "success": True,
        "result": {
            "results": [
                {
                    "title": "3D modeling",
                    "url": "https://example.com/3d",
                    "content": "3D modeling overview",
                    "score": 0.98,
                }
            ]
        },
    }

    with patch("src.mcp.tools.web_search_tool.WebSearchTool.execute", return_value=payload):
        result = run_unified_search("3d", limit=5, sources=["web"], mode="keyword")

    assert result["success"] is True
    assert result["count"] == 1
    assert result["results"][0]["source"] == "web"
    assert result["results"][0]["title"] == "3D modeling"
    assert result["source_errors"] == {}


def test_run_unified_search_web_surfaces_provider_error():
    payload = {
        "success": False,
        "error": "No Tavily API key configured",
        "result": None,
    }

    with patch("src.mcp.tools.web_search_tool.WebSearchTool.execute", return_value=payload):
        result = run_unified_search("3d", limit=5, sources=["web"], mode="keyword")

    assert result["success"] is True
    assert result["count"] == 0
    assert result["by_source"]["web"] == []
    assert result["source_errors"]["web"] == "No Tavily API key configured"


def test_run_unified_search_web_requests_at_most_ten_provider_rows():
    payload = {
        "success": True,
        "result": {
            "results": [
                {
                    "title": f"Result {i}",
                    "url": f"https://example.com/{i}",
                    "content": f"Snippet {i}",
                    "score": 1.0 - (i * 0.01),
                }
                for i in range(15)
            ]
        },
    }

    with patch("src.mcp.tools.web_search_tool.WebSearchTool.execute", return_value=payload) as execute_mock:
        result = run_unified_search("3d", limit=50, sources=["web"], mode="keyword")

    execute_mock.assert_called_once()
    call_args = execute_mock.call_args.args[0]
    assert call_args["query"] == "3d"
    assert call_args["max_results"] == 10
    assert result["success"] is True
    # Aggregator trusts tool output; the clamp currently lives in WebSearchTool request contract.
    assert result["count"] == 15
    assert len(result["results"]) == 15
