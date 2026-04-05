"""
MARKER_153.3T: Phase 153 Wave 3 Tests — Onboarding flow.

Tests for:
- First-open detection (init returns has_project=false)
- Project init creates config + sandbox
- After init, subsequent init returns has_project=true
- Full onboarding flow simulation

@phase 153
@wave 3
"""

import json
import os
import tempfile
import shutil

import pytest

from src.services.project_config import ProjectConfig, SessionState


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="test_153w3_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def api_client(tmp_dir):
    """FastAPI test client with patched config paths."""
    import src.services.project_config as pc_module
    import src.services.mcc_project_registry as reg_module
    orig_config = pc_module.CONFIG_PATH
    orig_session = pc_module.SESSION_STATE_PATH
    orig_data = pc_module.DATA_DIR
    orig_reg_path = reg_module.REGISTRY_PATH
    orig_reg_sessions = reg_module.SESSIONS_DIR
    orig_reg_config = reg_module.CONFIG_PATH
    orig_reg_session = reg_module.SESSION_STATE_PATH
    orig_reg_data = reg_module.DATA_DIR

    pc_module.CONFIG_PATH = os.path.join(tmp_dir, "project_config.json")
    pc_module.SESSION_STATE_PATH = os.path.join(tmp_dir, "session_state.json")
    pc_module.DATA_DIR = tmp_dir
    reg_module.REGISTRY_PATH = os.path.join(tmp_dir, "mcc_projects_registry.json")
    reg_module.SESSIONS_DIR = os.path.join(tmp_dir, "mcc_sessions")
    reg_module.CONFIG_PATH = pc_module.CONFIG_PATH
    reg_module.SESSION_STATE_PATH = pc_module.SESSION_STATE_PATH
    reg_module.DATA_DIR = tmp_dir

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.api.routes.mcc_routes import router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    yield client, tmp_dir

    pc_module.CONFIG_PATH = orig_config
    pc_module.SESSION_STATE_PATH = orig_session
    pc_module.DATA_DIR = orig_data
    reg_module.REGISTRY_PATH = orig_reg_path
    reg_module.SESSIONS_DIR = orig_reg_sessions
    reg_module.CONFIG_PATH = orig_reg_config
    reg_module.SESSION_STATE_PATH = orig_reg_session
    reg_module.DATA_DIR = orig_reg_data


class TestOnboardingFlow:
    """Test the full first-open → project setup → ready flow."""

    def test_first_open_no_project(self, api_client):
        """GET /init with no config → has_project=false → triggers onboarding."""
        client, _ = api_client
        r = client.get("/api/mcc/init")
        assert r.status_code == 200
        data = r.json()
        assert data["has_project"] is False
        assert data["project_config"] is None

    def test_project_init_creates_config_and_sandbox(self, api_client):
        """POST /project/init creates config + sandbox from local source."""
        client, tmp_dir = api_client
        # Create source directory
        source = os.path.join(tmp_dir, "my_project")
        os.makedirs(source)
        with open(os.path.join(source, "main.py"), 'w') as f:
            f.write("print('hello')\n")

        r = client.post("/api/mcc/project/init", json={
            "source_type": "local",
            "source_path": source,
            "quota_gb": 5,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["project_id"]
        assert data["sandbox_path"]

        # Verify sandbox was created with the file
        assert os.path.isdir(data["sandbox_path"])
        assert os.path.exists(os.path.join(data["sandbox_path"], "main.py"))

    def test_after_init_has_project_true(self, api_client):
        """After project/init, subsequent init returns has_project=true."""
        client, tmp_dir = api_client
        source = os.path.join(tmp_dir, "proj")
        os.makedirs(source)
        with open(os.path.join(source, "app.py"), 'w') as f:
            f.write("# app\n")

        # Step 1: No project
        r = client.get("/api/mcc/init")
        assert r.json()["has_project"] is False

        # Step 2: Initialize
        r = client.post("/api/mcc/project/init", json={
            "source_type": "local",
            "source_path": source,
        })
        assert r.json()["success"] is True

        # Step 3: Now has project
        r = client.get("/api/mcc/init")
        data = r.json()
        assert data["has_project"] is True
        assert data["project_config"] is not None
        assert data["session_state"] is not None
        assert data["project_config"]["source_type"] == "local"

    def test_full_onboarding_flow(self, api_client):
        """
        Simulate the full onboarding flow:
        1. Check init → no project
        2. Create project
        3. Check sandbox status
        4. Check init → has project
        5. Save navigation state
        6. Verify state persistence
        """
        client, tmp_dir = api_client
        source = os.path.join(tmp_dir, "flow_project")
        os.makedirs(source)
        for name in ["main.py", "utils.py"]:
            with open(os.path.join(source, name), 'w') as f:
                f.write(f"# {name}\n")

        # 1. No project
        r = client.get("/api/mcc/init")
        assert r.json()["has_project"] is False

        # 2. Create project
        r = client.post("/api/mcc/project/init", json={
            "source_type": "local",
            "source_path": source,
            "quota_gb": 10,
        })
        assert r.json()["success"] is True
        project_id = r.json()["project_id"]

        # 3. Check sandbox status
        r = client.get("/api/mcc/sandbox/status")
        data = r.json()
        assert data["exists"] is True
        # file_count is behind VETKA_SANDBOX_COUNT_FILES flag and may be 0 by contract
        assert "file_count" in data

        # 4. Has project now
        r = client.get("/api/mcc/init")
        data = r.json()
        assert data["has_project"] is True
        assert data["project_config"]["project_id"] == project_id

        # 5. Save state (simulating user navigating to roadmap)
        r = client.post("/api/mcc/state", json={
            "level": "roadmap",
            "roadmap_node_id": "",
            "task_id": "",
            "history": [],
        })
        assert r.json()["ok"] is True

        # 6. Verify state persists
        r = client.get("/api/mcc/state")
        data = r.json()
        assert data["level"] == "roadmap"

    def test_onboarding_allows_next_project_init(self, api_client):
        """Second init is allowed in multi-project mode and rotates active project."""
        client, tmp_dir = api_client
        source = os.path.join(tmp_dir, "dup_proj")
        os.makedirs(source)
        with open(os.path.join(source, "x.py"), 'w') as f:
            f.write("#\n")

        # First init
        r = client.post("/api/mcc/project/init", json={
            "source_type": "local",
            "source_path": source,
        })
        assert r.json()["success"] is True

        # Second init → success (new project entry)
        r = client.post("/api/mcc/project/init", json={
            "source_type": "local",
            "source_path": source,
        })
        data = r.json()
        assert data["success"] is True
        assert data["project_id"]

    def test_delete_then_reinit(self, api_client):
        """Delete project → reinit works."""
        client, tmp_dir = api_client
        source = os.path.join(tmp_dir, "reinit_proj")
        os.makedirs(source)
        with open(os.path.join(source, "y.py"), 'w') as f:
            f.write("#\n")

        # Init
        r = client.post("/api/mcc/project/init", json={
            "source_type": "local",
            "source_path": source,
        })
        assert r.json()["success"] is True

        # Delete
        r = client.delete("/api/mcc/project")
        assert r.json()["ok"] is True

        # Re-check: no project
        r = client.get("/api/mcc/init")
        assert r.json()["has_project"] is False

        # Re-init
        r = client.post("/api/mcc/project/init", json={
            "source_type": "local",
            "source_path": source,
        })
        assert r.json()["success"] is True

    def test_session_state_initializes_on_project_init(self, api_client):
        """project/init creates default session state (level=roadmap)."""
        client, tmp_dir = api_client
        source = os.path.join(tmp_dir, "state_proj")
        os.makedirs(source)
        with open(os.path.join(source, "z.py"), 'w') as f:
            f.write("#\n")

        client.post("/api/mcc/project/init", json={
            "source_type": "local",
            "source_path": source,
        })

        r = client.get("/api/mcc/state")
        data = r.json()
        assert data["level"] == "roadmap"
        assert data["roadmap_node_id"] == ""

    def test_invalid_source_path_shows_error(self, api_client):
        """POST /project/init with bad path → error message for UI."""
        client, _ = api_client
        r = client.post("/api/mcc/project/init", json={
            "source_type": "local",
            "source_path": "/nonexistent/path/xyz",
        })
        data = r.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0
        assert any("not found" in e.lower() for e in data["errors"])


class TestOnboardingModalShape:
    """Verify OnboardingModal component contract."""

    def test_onboarding_modal_file_exists(self):
        """OnboardingModal.tsx should exist."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "client", "src", "components", "mcc", "OnboardingModal.tsx"
        )
        assert os.path.exists(path), f"OnboardingModal.tsx not found at {path}"

    def test_onboarding_modal_has_api_call(self):
        """OnboardingModal should call /api/mcc/project/init."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "client", "src", "components", "mcc", "OnboardingModal.tsx"
        )
        content = open(path).read()
        assert "project/init" in content
        assert "source_type" in content
        assert "source_path" in content

    def test_onboarding_modal_has_steps(self):
        """OnboardingModal should have source/scanning/ready steps."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "client", "src", "components", "mcc", "OnboardingModal.tsx"
        )
        content = open(path).read()
        assert "'source'" in content
        assert "'scanning'" in content
        assert "'ready'" in content
