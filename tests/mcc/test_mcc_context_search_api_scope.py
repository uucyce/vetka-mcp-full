from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import src.api.routes.mcc_routes as routes
    from src.api.routes.mcc_routes import router

    source = tmp_path / "source_project"
    sandbox = tmp_path / "sandbox_project"
    source.mkdir(parents=True, exist_ok=True)
    sandbox.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        routes,
        "_load_active_project_config",
        lambda: SimpleNamespace(
            source_path=str(source),
            sandbox_path=str(sandbox),
            project_id="ctx_search_scope_project",
        ),
    )

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_mcc_scoped_search_uses_sandbox_by_default_and_filters_paths(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.search.file_search_service as fs

    sandbox = (tmp_path / "sandbox_project").resolve()
    inside = sandbox / "src" / "inside.ts"
    outside = (tmp_path / "outside.ts").resolve()

    seen: dict = {}

    def fake_search_files(query: str, limit: int = 20, mode: str = "keyword", scope_roots=None):
        seen["query"] = query
        seen["limit"] = limit
        seen["mode"] = mode
        seen["scope_roots"] = list(scope_roots or [])
        return {
            "success": True,
            "results": [
                {"path": str(inside), "title": "inside.ts", "snippet": "ok", "score": 0.9},
                {"path": str(outside), "title": "outside.ts", "snippet": "leak", "score": 0.8},
            ],
            "count": 2,
        }

    monkeypatch.setattr(fs, "search_files", fake_search_files)

    resp = client.post(
        "/api/mcc/search/file",
        json={"query": "inside", "limit": 20, "mode": "filename"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["scope_root"] == str(sandbox)
    assert seen["scope_roots"] == [str(sandbox)]
    assert data["count"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["path"] == str(inside)


def test_mcc_scoped_search_rejects_scope_outside_active_project(
    client: TestClient,
    tmp_path: Path,
) -> None:
    outside_scope = (tmp_path / "outside_scope").resolve()
    outside_scope.mkdir(parents=True, exist_ok=True)

    resp = client.post(
        "/api/mcc/search/file",
        json={
            "query": "abc",
            "scope_path": str(outside_scope),
        },
    )
    assert resp.status_code == 400
    assert "scope_path must be inside active project scope" in resp.text


def test_mcc_scoped_search_falls_back_to_source_when_sandbox_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.api.routes.mcc_routes as routes
    import src.search.file_search_service as fs
    from src.api.routes.mcc_routes import router

    source = (tmp_path / "source_only_project").resolve()
    source.mkdir(parents=True, exist_ok=True)
    missing_sandbox = (tmp_path / "missing_sandbox").resolve()
    inside = source / "docs" / "plan.md"
    inside.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        routes,
        "_load_active_project_config",
        lambda: SimpleNamespace(
            source_path=str(source),
            sandbox_path=str(missing_sandbox),
            project_id="ctx_search_source_fallback_project",
        ),
    )

    seen: dict = {}

    def fake_search_files(query: str, limit: int = 20, mode: str = "keyword", scope_roots=None):
        seen["scope_roots"] = list(scope_roots or [])
        return {
            "success": True,
            "results": [
                {"path": str(inside), "title": "plan.md", "snippet": "test payload", "score": 0.9},
            ],
            "count": 1,
        }

    monkeypatch.setattr(fs, "search_files", fake_search_files)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post("/api/mcc/search/file", json={"query": "test"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["scope_root"] == str(source)
    assert seen["scope_roots"] == [str(source)]
    assert data["count"] == 1
