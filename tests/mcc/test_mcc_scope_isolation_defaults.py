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

    source = tmp_path / "source_scope"
    sandbox = tmp_path / "sandbox_scope"
    source.mkdir(parents=True, exist_ok=True)
    sandbox.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        routes,
        "_load_active_project_config",
        lambda: SimpleNamespace(
            source_path=str(source),
            sandbox_path=str(sandbox),
            project_id="scope_isolation_project",
        ),
    )

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_build_design_defaults_to_sandbox_scope(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import src.services.mcc_architect_builder as builder

    seen: dict = {}

    def fake_build(scope_root: str, *args, **kwargs):
        seen["scope_root"] = str(scope_root)
        return {"design_graph": {"nodes": [], "edges": []}}

    monkeypatch.setattr(builder, "build_design_dag", fake_build)

    resp = client.post("/api/mcc/graph/build-design", json={"max_nodes": 100})
    assert resp.status_code == 200
    assert "sandbox_scope" in str(seen.get("scope_root", ""))


def test_auto_compare_defaults_to_sandbox_scope(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import src.services.mcc_dag_compare as compare_module

    seen: dict = {}

    def fake_compare(**kwargs):
        seen["scope_root"] = str(kwargs.get("scope_root", ""))
        return {
            "success": True,
            "count": 1,
            "variants": [],
            "best": {"name": "baseline"},
            "markers": [],
        }

    monkeypatch.setattr(compare_module, "run_dag_auto_compare", fake_compare)

    resp = client.post(
        "/api/mcc/dag-versions/auto-compare",
        json={
            "source_kind": "scope",
            "variants": [{"name": "baseline"}],
            "persist_versions": False,
        },
    )
    assert resp.status_code == 200
    assert "sandbox_scope" in str(seen.get("scope_root", ""))

