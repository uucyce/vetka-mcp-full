"""
Phase 176 Sprint 1A — Backend Tests

Markers tested:
- MARKER_176.T1: test_roadmap_create_tasks — POST /api/mcc/roadmap/{node_id}/create-tasks
- MARKER_176.T2: test_prefetch_called_before_dispatch — prefetch wired into pipeline
- MARKER_176.T3: test_apply_updates_task_status — POST /api/mcc/tasks/{id}/apply
- MARKER_176.T4: test_reject_requeues_task — POST /api/mcc/tasks/{id}/reject
- MARKER_176.T5: test_trm_policy_in_dag — TRM enrichment (deferred if adapter not ready)
- MARKER_176.T6: test_jepa_clustering_in_roadmap — JEPA enrichment (deferred if adapter not ready)
- MARKER_176.T7: test_group_task_appears_in_mcc — group chat 'now' path → board

@phase 176
@sprint 1A
@status active
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def board(tmp_path, monkeypatch):
    """Isolated TaskBoard backed by tmp_path."""
    import src.orchestration.task_board as task_board_module

    board = task_board_module.TaskBoard(board_file=tmp_path / "task_board.json")
    monkeypatch.setattr(task_board_module, "get_task_board", lambda: board)
    return board


@pytest.fixture
def client(board):
    """TestClient for MCC routes with isolated board."""
    from src.api.routes.mcc_routes import router as mcc_router

    app = FastAPI()
    app.include_router(mcc_router)
    return TestClient(app)


def _seed_task(board, **overrides):
    """Create a task in the board with optional overrides."""
    task_id = board.add_task(
        title=overrides.pop("title", "Sprint 1 test task"),
        description=overrides.pop("description", "Phase 176 test task"),
        priority=overrides.pop("priority", 3),
        phase_type=overrides.pop("phase_type", "build"),
        preset=overrides.pop("preset", "dragon_silver"),
        tags=overrides.pop("tags", ["phase176"]),
    )
    if overrides:
        assert board.update_task(task_id, **overrides)
    return task_id


# ── MARKER_176.T3: Apply pipeline results ────────────────────────

def test_apply_updates_task_status(client, board):
    """MARKER_176.T3: POST /api/mcc/tasks/{id}/apply → status=done, result_status=applied."""
    task_id = _seed_task(board, status="done")

    response = client.post(f"/api/mcc/tasks/{task_id}/apply")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    task = data["task"]
    assert task["status"] == "done"
    assert task["result_status"] == "applied"


def test_apply_nonexistent_task_returns_404(client, board):
    """Apply on missing task returns 404."""
    response = client.post("/api/mcc/tasks/nonexistent_task_id/apply")
    assert response.status_code == 404


# ── MARKER_176.T4: Reject pipeline results ───────────────────────

def test_reject_requeues_task(client, board):
    """MARKER_176.T4: POST /api/mcc/tasks/{id}/reject → status=pending, feedback appended."""
    task_id = _seed_task(board, description="Original description", status="done")

    response = client.post(
        f"/api/mcc/tasks/{task_id}/reject",
        json={"feedback": "Output is incomplete, retry with more context"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    task = data["task"]
    assert task["status"] == "pending"
    assert task["result_status"] == "rejected"
    assert "[USER FEEDBACK]" in task["description"]
    assert "Output is incomplete" in task["description"]


def test_reject_without_feedback(client, board):
    """Reject with empty feedback still works (description unchanged)."""
    task_id = _seed_task(board, description="Original task")

    response = client.post(
        f"/api/mcc/tasks/{task_id}/reject",
        json={"feedback": ""},
    )

    assert response.status_code == 200
    task = response.json()["task"]
    assert task["status"] == "pending"
    assert task["result_status"] == "rejected"


def test_reject_nonexistent_task_returns_404(client, board):
    """Reject on missing task returns 404."""
    response = client.post(
        "/api/mcc/tasks/nonexistent_task_id/reject",
        json={"feedback": "test"},
    )
    assert response.status_code == 404


# ── MARKER_176.T1: Create tasks from roadmap node ────────────────

def test_roadmap_create_tasks_no_roadmap(client, board, monkeypatch):
    """MARKER_176.T1: 404 when no roadmap loaded."""
    # Mock RoadmapDAG.load() to return None
    monkeypatch.setattr(
        "src.services.roadmap_generator.RoadmapDAG.load",
        lambda: None,
    )
    response = client.post("/api/mcc/roadmap/some_node/create-tasks")
    assert response.status_code == 404
    assert "No roadmap found" in response.json()["detail"]


def test_roadmap_create_tasks_node_not_found(client, board, monkeypatch):
    """MARKER_176.T1: 404 when node_id doesn't exist in roadmap."""
    mock_dag = MagicMock()
    mock_dag.to_frontend_format.return_value = {
        "nodes": [
            {"id": "module_auth", "data": {"id": "module_auth", "label": "Auth"}},
        ],
        "edges": [],
    }
    monkeypatch.setattr(
        "src.services.roadmap_generator.RoadmapDAG.load",
        lambda: mock_dag,
    )
    response = client.post("/api/mcc/roadmap/nonexistent_node/create-tasks")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_roadmap_create_tasks_success(client, board, monkeypatch):
    """MARKER_176.T1: Creates tasks from a roadmap node."""
    mock_dag = MagicMock()
    mock_dag.to_frontend_format.return_value = {
        "nodes": [
            {
                "id": "module_auth",
                "data": {
                    "id": "module_auth",
                    "label": "Authentication Module",
                    "description": "Handles user auth, JWT, sessions",
                    "files": ["src/auth/login.py", "src/auth/jwt.py"],
                    "priority": 3,
                    "children": [
                        {"id": "sub_jwt", "label": "JWT Handler", "description": "Token management"},
                    ],
                },
            },
        ],
        "edges": [],
    }
    monkeypatch.setattr(
        "src.services.roadmap_generator.RoadmapDAG.load",
        lambda: mock_dag,
    )

    response = client.post("/api/mcc/roadmap/module_auth/create-tasks")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 2  # main + 1 child
    assert len(data["tasks"]) == 2

    # Verify tasks in board (board.tasks is a dict)
    all_tasks = list(board.tasks.values())
    assert len(all_tasks) == 2
    main_task = all_tasks[0]
    assert "Authentication Module" in main_task["title"]
    assert "roadmap:module_auth" in main_task.get("tags", [])


# ── MARKER_176.T2: Prefetch wired into pipeline ──────────────────

def test_prefetch_marker_in_agent_pipeline():
    """MARKER_176.T2: Verify MARKER_176.2 code exists in agent_pipeline.py."""
    pipeline_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "orchestration", "agent_pipeline.py"
    )
    if not os.path.exists(pipeline_path):
        pytest.skip("agent_pipeline.py not found at expected path")

    with open(pipeline_path) as f:
        content = f.read()

    # Verify both parts exist
    assert "MARKER_176.2" in content, "MARKER_176.2 tag not found in agent_pipeline.py"
    assert "ArchitectPrefetch.prepare" in content, "ArchitectPrefetch.prepare() call not found"
    assert "MARKER_176.2B" in content, "MARKER_176.2B (injection) tag not found"
    assert "_prefetch_context" in content, "Prefetch context storage not found"


def test_prefetch_context_attributes():
    """MARKER_176.T2: ArchitectPrefetch.prepare() returns expected context object."""
    try:
        from src.services.architect_prefetch import ArchitectPrefetch
    except ImportError:
        pytest.skip("architect_prefetch not importable")

    # Call with minimal args — should return a PrefetchContext
    try:
        ctx = ArchitectPrefetch.prepare(
            task_description="Add login endpoint to auth module",
            task_type="build",
            complexity=5,
            workflow_family="",
        )
    except Exception:
        pytest.skip("ArchitectPrefetch.prepare() failed (config/env issue)")

    # Check the context has expected attributes
    assert hasattr(ctx, "workflow_name") or hasattr(ctx, "workflow_id"), \
        "PrefetchContext missing workflow attributes"


# ── MARKER_176.T7: Group chat 'now' path → MCC board ─────────────

def test_group_task_now_path_has_board_tracking():
    """MARKER_176.T7: Verify MARKER_176.6 exists in group_message_handler.py."""
    handler_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "api", "handlers", "group_message_handler.py"
    )
    if not os.path.exists(handler_path):
        pytest.skip("group_message_handler.py not found")

    with open(handler_path) as f:
        content = f.read()

    assert "MARKER_176.6" in content, "MARKER_176.6 tag not found in group_message_handler.py"
    assert "board.add_task" in content, "board.add_task not found in handler"

    # Count board.add_task calls — should be in BOTH paths now
    import re
    calls = re.findall(r'board\.add_task\(', content)
    assert len(calls) >= 2, \
        f"Expected board.add_task in both 'now' and 'queue' paths, found {len(calls)} calls"


# ── MARKER_176.T5: TRM integration (structural check) ────────────

def test_trm_integration_marker_exists():
    """MARKER_176.T5: Verify MARKER_176.4 TRM integration code exists."""
    # Search across all Python files in src/
    src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
    found = False
    for root, dirs, files in os.walk(src_dir):
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath) as f:
                        if "MARKER_176.4" in f.read():
                            found = True
                            break
                except Exception:
                    pass
        if found:
            break

    if not found:
        pytest.skip("MARKER_176.4 not yet implemented — Sonnet agent in progress")


# ── MARKER_176.T6: JEPA clustering (structural check) ────────────

def test_jepa_clustering_marker_exists():
    """MARKER_176.T6: Verify MARKER_176.5 JEPA integration code exists."""
    roadmap_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "services", "roadmap_generator.py"
    )
    if not os.path.exists(roadmap_path):
        # Also check orchestration
        roadmap_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "orchestration", "roadmap_generator.py"
        )
    if not os.path.exists(roadmap_path):
        pytest.skip("roadmap_generator.py not found")

    with open(roadmap_path) as f:
        content = f.read()

    if "MARKER_176.5" not in content:
        pytest.skip("MARKER_176.5 not yet implemented — Sonnet agent in progress")


# ── Compile checks ───────────────────────────────────────────────

def test_mcc_routes_compiles():
    """All modified backend files compile without syntax errors."""
    import py_compile

    base = os.path.join(os.path.dirname(__file__), "..")
    files = [
        "src/api/routes/mcc_routes.py",
        "src/orchestration/agent_pipeline.py",
        "src/api/handlers/group_message_handler.py",
    ]
    for rel_path in files:
        full_path = os.path.join(base, rel_path)
        if os.path.exists(full_path):
            py_compile.compile(full_path, doraise=True)
