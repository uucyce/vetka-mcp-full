"""
Tests for Agent Gateway API.

@license MIT
"""

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.taskboard import get_task_board

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_board(tmp_path, monkeypatch):
    """Use a fresh temp DB for each test."""
    db_path = str(tmp_path / "test_taskboard.db")
    monkeypatch.setenv("TASKBOARD_DB", db_path)
    # Reset singleton
    import src.taskboard as tb

    tb._board = None
    yield
    tb._board = None


def _register_agent(name="test-agent", agent_type="test"):
    resp = client.post(
        "/api/gateway/agents/register",
        json={
            "name": name,
            "agent_type": agent_type,
        },
    )
    assert resp.status_code == 200
    return resp.json()


def _auth_header(api_key):
    return {"Authorization": f"Bearer {api_key}"}


class TestHealth:
    def test_health(self):
        resp = client.get("/api/gateway/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestRegistration:
    def test_register(self):
        data = _register_agent()
        assert data["success"] is True
        assert "api_key" in data
        assert data["agent"]["name"] == "test-agent"

    def test_register_missing_name(self):
        resp = client.post("/api/gateway/agents/register", json={"agent_type": "test"})
        assert resp.status_code == 400

    def test_register_missing_type(self):
        resp = client.post("/api/gateway/agents/register", json={"name": "x"})
        assert resp.status_code == 400


class TestAuth:
    def test_no_auth(self):
        resp = client.get("/api/gateway/tasks")
        assert resp.status_code == 401

    def test_bad_key(self):
        resp = client.get("/api/gateway/tasks", headers=_auth_header("bad_key"))
        assert resp.status_code == 401

    def test_valid_auth(self):
        reg = _register_agent()
        resp = client.get(
            "/api/gateway/agents/me", headers=_auth_header(reg["api_key"])
        )
        assert resp.status_code == 200


class TestTasks:
    def _create_task(self):
        board = get_task_board()
        tid = board.add_task("Test task", description="A test", priority=1)
        return tid

    def test_list_tasks(self):
        reg = _register_agent()
        self._create_task()
        resp = client.get("/api/gateway/tasks", headers=_auth_header(reg["api_key"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1

    def test_claim_task(self):
        reg = _register_agent()
        tid = self._create_task()
        resp = client.post(
            f"/api/gateway/tasks/{tid}/claim", headers=_auth_header(reg["api_key"])
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_double_claim(self):
        reg1 = _register_agent("agent1")
        reg2 = _register_agent("agent2")
        tid = self._create_task()

        client.post(
            f"/api/gateway/tasks/{tid}/claim", headers=_auth_header(reg1["api_key"])
        )

        resp = client.post(
            f"/api/gateway/tasks/{tid}/claim", headers=_auth_header(reg2["api_key"])
        )
        assert resp.status_code == 400

    def test_complete_task(self):
        reg = _register_agent()
        tid = self._create_task()
        client.post(
            f"/api/gateway/tasks/{tid}/claim", headers=_auth_header(reg["api_key"])
        )

        resp = client.post(
            f"/api/gateway/tasks/{tid}/complete",
            headers=_auth_header(reg["api_key"]),
            json={"commit_hash": "abc1234"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_complete_without_hash(self):
        reg = _register_agent()
        tid = self._create_task()
        client.post(
            f"/api/gateway/tasks/{tid}/claim", headers=_auth_header(reg["api_key"])
        )

        resp = client.post(
            f"/api/gateway/tasks/{tid}/complete",
            headers=_auth_header(reg["api_key"]),
            json={},
        )
        assert resp.status_code == 400


class TestAdmin:
    def test_list_agents(self):
        reg = _register_agent()
        resp = client.get(
            "/api/gateway/admin/agents", headers=_auth_header(reg["api_key"])
        )
        assert resp.status_code == 200

    def test_suspend_nonexistent(self):
        reg = _register_agent()
        resp = client.post(
            "/api/gateway/admin/agents/fake_id/suspend",
            headers=_auth_header(reg["api_key"]),
        )
        assert resp.status_code == 404

    def test_suspend_activate(self):
        # Use admin agent to manage target agent
        admin = _register_agent("admin-agent")
        target = _register_agent("target-agent")
        target_id = target["agent"]["id"]
        admin_headers = _auth_header(admin["api_key"])

        resp = client.post(
            f"/api/gateway/admin/agents/{target_id}/suspend", headers=admin_headers
        )
        assert resp.status_code == 200

        resp = client.post(
            f"/api/gateway/admin/agents/{target_id}/activate", headers=admin_headers
        )
        assert resp.status_code == 200
