from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_import_workflow_stamps_bank_metadata(monkeypatch) -> None:
    import src.api.routes.workflow_template_routes as routes
    from src.api.routes.workflow_template_routes import router

    class _FakeStore:
        def validate(self, workflow):
            class _Validation:
                def to_dict(self):
                    return {"valid": True, "errors": [], "warnings": []}

            return _Validation()

        def save(self, workflow):
            self.saved_workflow = workflow
            return "wf_imported"

    fake_store = _FakeStore()
    monkeypatch.setattr(routes, "get_store", lambda: fake_store)
    monkeypatch.setattr(
        "src.services.converters.n8n_converter.detect_n8n_format",
        lambda data: True,
    )
    monkeypatch.setattr(
        "src.services.converters.n8n_converter.n8n_to_vetka",
        lambda data: {
            "id": "wf_temp",
            "name": "Imported n8n",
            "nodes": [],
            "edges": [],
            "metadata": {"imported_from": "n8n"},
        },
    )

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post(
        "/api/workflows/import",
        json={"data": {"nodes": [], "connections": {}}, "format": "n8n", "save": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["format_detected"] == "n8n"
    assert data["workflow"]["metadata"]["workflow_bank"] == "n8n"
    assert data["workflow"]["metadata"]["import_format"] == "n8n"
