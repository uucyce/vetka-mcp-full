from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_debug_routes_expose_media_window_snapshot_endpoints():
    debug_routes = _read("src/api/routes/debug_routes.py")

    assert '@router.post("/media-window-snapshot")' in debug_routes
    assert '@router.get("/media-window-snapshot")' in debug_routes
    assert 'category="media_window"' in debug_routes
    assert "_media_window_snapshots" in debug_routes


def test_browser_agent_bridge_exposes_detached_media_snapshot_reader():
    bridge = _read("client/src/utils/browserAgentBridge.ts")

    assert "getDetachedMediaSnapshot" in bridge
    assert "DetachedMediaSnapshotResult" in bridge
    assert "media-window-snapshot" in bridge
    assert "Latest media geometry" in bridge


def test_mcp_bridge_registers_media_window_debug_tool():
    bridge = _read("src/mcp/vetka_mcp_bridge.py")

    assert 'name="vetka_get_media_window_debug"' in bridge
    assert '"/api/debug/media-window-snapshot"' in bridge
    assert "Detached Media Window Debug" in bridge


def test_media_window_debug_tool_is_safe_for_function_calling():
    sync_tool = _read("src/mcp/tools/llm_call_tool.py")
    async_tool = _read("src/mcp/tools/llm_call_tool_async.py")

    assert '"vetka_get_media_window_debug"' in sync_tool
    assert '"vetka_get_media_window_debug"' in async_tool
