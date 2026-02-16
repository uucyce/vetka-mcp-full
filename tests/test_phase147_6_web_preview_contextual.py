import pytest

from src.api.routes import unified_search_routes as usr
from src.search.contextual_retrieval import contextual_rerank


def test_web_preview_sanitize_removes_active_content():
    raw = """
    <html>
      <head><script>alert(1)</script><style>body{display:none}</style></head>
      <body onload="evil()">
        <form action="/x"><input></form>
        <iframe src="https://x.com"></iframe>
        <a href="javascript:alert(2)">x</a>
        <div>safe text</div>
      </body>
    </html>
    """
    cleaned = usr._sanitize_html(raw)
    assert "<script" not in cleaned.lower()
    assert "<style" not in cleaned.lower()
    assert "<iframe" not in cleaned.lower()
    assert "<form" not in cleaned.lower()
    assert "onload=" not in cleaned.lower()
    assert "javascript:" not in cleaned.lower()
    assert "safe text" in cleaned


def test_web_preview_detects_probably_js_app():
    raw = """
    <html><body><div id="__next"></div>
    <script src="/a.js"></script><script src="/b.js"></script><script src="/c.js"></script>
    </body></html>
    """
    safe = "<html><body><div id='__next'></div></body></html>"
    assert usr._is_probably_js_app(raw, safe) is True


def test_contextual_rerank_boosts_focus_branch_for_file_like_rows():
    rows = [
        {"source": "file", "title": "src/other/file.py", "snippet": "misc", "score": 0.8, "url": "file://src/other/file.py"},
        {"source": "file", "title": "src/focus/main.py", "snippet": "focus token", "score": 0.6, "url": "file://src/focus/main.py"},
    ]
    viewport_context = {
        "pinned_nodes": [
            {"type": "file", "path": "src/focus/main.py", "name": "main.py", "is_center": True},
        ],
        "viewport_nodes": [],
    }
    reranked = contextual_rerank(rows, viewport_context=viewport_context)
    assert reranked[0]["title"] == "src/focus/main.py"
    assert reranked[0].get("context_boost", 0) > 0


@pytest.mark.parametrize(
    "hostname,expected",
    [
        ("localhost", True),
        ("127.0.0.1", True),
        ("10.1.2.3", True),
        ("example.com", False),
    ],
)
def test_private_host_guard(hostname: str, expected: bool):
    assert usr._is_private_or_local_host(hostname) is expected

