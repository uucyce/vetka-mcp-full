from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_workflow_myco_hint_contract(monkeypatch) -> None:
    import src.api.routes.mcc_routes as routes
    from src.api.routes.mcc_routes import router

    monkeypatch.setattr(
        "src.services.myco_memory_bridge.retrieve_myco_hidden_context",
        lambda **kwargs: {
            "query": "ralph_loop coder active task",
            "items": [{"source_path": "docs/162_ph_MCC_MYCO_HELPER/MYCO_RAG_CORE_V1.md", "score": 0.8, "snippet": "Use Context before Tasks"}],
            "method": "lexical_fallback",
            "aliases_used": [],
            "marker": "MARKER_162.P3.P4.MYCO.RETRIEVAL_BRIDGE.V1",
        },
    )

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post(
        "/api/mcc/workflow/myco-hint",
        json={
            "workflow_bank": "core",
            "workflow_id": "ralph_loop",
            "workflow_family": "ralph_loop",
            "role": "coder",
            "task_label": "Fix tests",
            "scope": "task",
            "focus": {"navLevel": "workflow", "graphKind": "project_task"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "MYCO:" in data["hint"]
    assert data["ordered_tools"][:3] == ["context", "tasks", "stats"]
    assert data["tool_priority"]["role_required"] == ["context", "tasks", "artifacts"]
    assert data["diagnostics"]["retrieval_method"] == "lexical_fallback"
    assert data["diagnostics"]["retrieval_count"] == 1
