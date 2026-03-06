from pathlib import Path


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase159_detached_actions_endpoints_and_cam_sync_contract():
    panel = _read("client/src/components/artifact/ArtifactPanel.tsx")
    artifact_routes = _read("src/api/routes/artifact_routes.py")
    tree_routes = _read("src/api/routes/tree_routes.py")
    watcher_routes = _read("src/api/routes/watcher_routes.py")

    assert "fetch('/api/watcher/index-file'" in panel
    assert "fetch('/api/tree/favorite'" in panel
    assert "fetch('/api/tree/favorites'" in panel
    assert "/api/artifacts/${encodeURIComponent(targetArtifactId)}/favorite" in panel

    assert '@router.post("/index-file")' in watcher_routes
    assert '@router.put("/{artifact_id}/favorite")' in artifact_routes
    assert '@router.put("/favorite")' in tree_routes
    assert "@router.get(\"/favorites\")" in tree_routes

    # CAM/Engram hooks remain present for favorites.
    assert "MARKER_137.6F: Optional CAM memory sync for favorited artifacts." in artifact_routes
    assert "MARKER_137.6F: Optional CAM sync for favorited nodes." in tree_routes
