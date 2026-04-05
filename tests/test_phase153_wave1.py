"""
Phase 153 Wave 1: Persistence + Project Config tests.

Tests ProjectConfig, SessionState, and MCC REST API endpoints.

@phase 153
@wave 1
"""

import json
import os
import shutil
import tempfile
import pytest

from src.services.project_config import ProjectConfig, SessionState


# ──────────────────────────────────────────────────────────────
# ProjectConfig tests
# ──────────────────────────────────────────────────────────────

class TestProjectConfig:
    """Tests for ProjectConfig dataclass."""

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.cfg_path = os.path.join(self.tmp_dir, "project_config.json")

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_create_new_local(self):
        """Create config from local path."""
        cfg = ProjectConfig.create_new("local", "/Users/test/my-project")
        assert cfg.source_type == "local"
        assert cfg.source_path == "/Users/test/my-project"
        assert "my-project" in cfg.project_id
        assert "playgrounds" in cfg.sandbox_path
        assert cfg.quota_gb == 10
        assert cfg.created_at != ""

    def test_create_new_git(self):
        """Create config from git URL."""
        cfg = ProjectConfig.create_new("git", "git@github.com:user/awesome-repo.git")
        assert cfg.source_type == "git"
        assert "awesome-repo" in cfg.project_id
        assert cfg.qdrant_collection == cfg.project_id

    def test_save_and_load(self):
        """Save config to JSON, load it back."""
        cfg = ProjectConfig.create_new("local", "/tmp/test")
        assert cfg.save(self.cfg_path)

        loaded = ProjectConfig.load(self.cfg_path)
        assert loaded is not None
        assert loaded.project_id == cfg.project_id
        assert loaded.source_type == cfg.source_type
        assert loaded.source_path == cfg.source_path
        assert loaded.sandbox_path == cfg.sandbox_path
        assert loaded.quota_gb == cfg.quota_gb

    def test_load_nonexistent(self):
        """Load from nonexistent file returns None."""
        result = ProjectConfig.load("/nonexistent/path/config.json")
        assert result is None

    def test_load_corrupt_json(self):
        """Load from corrupt JSON returns None."""
        with open(self.cfg_path, 'w') as f:
            f.write("{broken json")
        result = ProjectConfig.load(self.cfg_path)
        assert result is None

    def test_validate_valid(self):
        """Valid config has no errors."""
        cfg = ProjectConfig.create_new("local", "/tmp/test")
        errors = cfg.validate()
        assert errors == []

    def test_validate_empty_project_id(self):
        """Empty project_id is invalid."""
        cfg = ProjectConfig(project_id="", source_type="local", source_path="/tmp")
        errors = cfg.validate()
        assert any("project_id" in e for e in errors)

    def test_validate_bad_source_type(self):
        """Invalid source_type is caught."""
        cfg = ProjectConfig(project_id="test", source_type="ftp", source_path="/tmp")
        errors = cfg.validate()
        assert any("source_type" in e for e in errors)

    def test_validate_relative_path(self):
        """Relative local path is invalid."""
        cfg = ProjectConfig(project_id="test", source_type="local", source_path="relative/path")
        errors = cfg.validate()
        assert any("absolute" in e for e in errors)

    def test_validate_quota_bounds(self):
        """Quota out of bounds is invalid."""
        cfg = ProjectConfig.create_new("local", "/tmp/test")
        cfg.quota_gb = 0
        errors = cfg.validate()
        assert any("quota" in e for e in errors)

        cfg.quota_gb = 200
        errors = cfg.validate()
        assert any("quota" in e for e in errors)

    def test_unique_project_ids(self):
        """Two configs from same path get different IDs."""
        cfg1 = ProjectConfig.create_new("local", "/tmp/same-project")
        cfg2 = ProjectConfig.create_new("local", "/tmp/same-project")
        assert cfg1.project_id != cfg2.project_id


# ──────────────────────────────────────────────────────────────
# SessionState tests
# ──────────────────────────────────────────────────────────────

class TestSessionState:
    """Tests for SessionState dataclass."""

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.state_path = os.path.join(self.tmp_dir, "session_state.json")

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_default_state(self):
        """Default state is roadmap level."""
        state = SessionState()
        assert state.level == "roadmap"
        assert state.roadmap_node_id == ""
        assert state.task_id == ""
        assert state.history == []

    def test_save_and_load(self):
        """Save and load session state."""
        state = SessionState(
            level="tasks",
            roadmap_node_id="module_auth",
            task_id="tb_abc123",
            history=["roadmap"],
        )
        assert state.save(self.state_path)

        loaded = SessionState.load(self.state_path)
        assert loaded.level == "tasks"
        assert loaded.roadmap_node_id == "module_auth"
        assert loaded.task_id == "tb_abc123"
        assert loaded.history == ["roadmap"]
        assert loaded.last_updated != ""

    def test_load_nonexistent_returns_default(self):
        """Load from nonexistent file returns default state."""
        state = SessionState.load("/nonexistent/path.json")
        assert state.level == "roadmap"

    def test_load_corrupt_returns_default(self):
        """Load from corrupt file returns default state."""
        with open(self.state_path, 'w') as f:
            f.write("not json")
        state = SessionState.load(self.state_path)
        assert state.level == "roadmap"

    def test_navigation_history(self):
        """History tracks navigation path."""
        state = SessionState(
            level="workflow",
            history=["roadmap", "tasks"],
        )
        assert state.save(self.state_path)

        loaded = SessionState.load(self.state_path)
        assert loaded.history == ["roadmap", "tasks"]
        assert loaded.level == "workflow"


# ──────────────────────────────────────────────────────────────
# MCC Routes tests (unit-level, no server)
# ──────────────────────────────────────────────────────────────

class TestMCCRoutes:
    """Test MCC route handler logic."""

    def test_router_has_endpoints(self):
        """MCC router has all expected endpoints."""
        from src.api.routes.mcc_routes import router
        paths = [r.path for r in router.routes]
        assert "/api/mcc/init" in paths
        assert "/api/mcc/state" in paths
        assert "/api/mcc/project/init" in paths
        assert "/api/mcc/project" in paths  # DELETE

    def test_router_registered_in_all_routers(self):
        """MCC router is in the get_all_routers list."""
        from src.api.routes import get_all_routers
        routers = get_all_routers()
        from src.api.routes.mcc_routes import router as mcc_router
        assert mcc_router in routers


# ──────────────────────────────────────────────────────────────
# MCC API Integration tests (with TestClient)
# ──────────────────────────────────────────────────────────────

class TestMCCAPI:
    """Integration tests using FastAPI TestClient."""

    def setup_method(self):
        """Create isolated test environment."""
        self.tmp_dir = tempfile.mkdtemp()
        self.cfg_path = os.path.join(self.tmp_dir, "project_config.json")
        self.state_path = os.path.join(self.tmp_dir, "session_state.json")

        # Monkey-patch paths for testing
        import src.services.project_config as pc_module
        self._orig_config_path = pc_module.CONFIG_PATH
        self._orig_state_path = pc_module.SESSION_STATE_PATH
        pc_module.CONFIG_PATH = self.cfg_path
        pc_module.SESSION_STATE_PATH = self.state_path

        # Create test client
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.routes.mcc_routes import router

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def teardown_method(self):
        """Restore paths."""
        import src.services.project_config as pc_module
        pc_module.CONFIG_PATH = self._orig_config_path
        pc_module.SESSION_STATE_PATH = self._orig_state_path
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_init_no_project(self):
        """GET /init returns has_project=false when no config exists."""
        resp = self.client.get("/api/mcc/init")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_project"] is False
        assert data["project_config"] is None

    def test_init_with_project(self):
        """GET /init returns config after project setup."""
        # Create config manually
        cfg = ProjectConfig.create_new("local", "/tmp/test-project")
        cfg.save(self.cfg_path)

        resp = self.client.get("/api/mcc/init")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_project"] is True
        assert data["project_config"]["source_type"] == "local"
        assert data["session_state"] is not None

    def test_save_and_get_state(self):
        """POST /state saves, GET /state returns."""
        resp = self.client.post("/api/mcc/state", json={
            "level": "tasks",
            "roadmap_node_id": "auth_module",
            "task_id": "tb_123",
            "history": ["roadmap"],
        })
        assert resp.status_code == 200

        resp = self.client.get("/api/mcc/state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["level"] == "tasks"
        assert data["roadmap_node_id"] == "auth_module"
        assert data["task_id"] == "tb_123"
        assert data["history"] == ["roadmap"]

    def test_project_init_local(self):
        """POST /project/init creates config from local path."""
        # Use tmp_dir as "project source"
        source = os.path.join(self.tmp_dir, "fake_project")
        os.makedirs(source)
        with open(os.path.join(source, "README.md"), 'w') as f:
            f.write("# Test")

        resp = self.client.post("/api/mcc/project/init", json={
            "source_type": "local",
            "source_path": source,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["project_id"] != ""
        assert data["sandbox_path"] != ""

        # Config should now exist
        cfg = ProjectConfig.load(self.cfg_path)
        assert cfg is not None
        assert cfg.source_type == "local"

    def test_project_init_nonexistent_path(self):
        """POST /project/init with bad path returns error."""
        resp = self.client.post("/api/mcc/project/init", json={
            "source_type": "local",
            "source_path": "/nonexistent/path/xyz",
        })
        data = resp.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0

    def test_project_init_duplicate_rejected(self):
        """Can't init project twice."""
        # Create first config
        cfg = ProjectConfig.create_new("local", "/tmp/test")
        cfg.save(self.cfg_path)

        resp = self.client.post("/api/mcc/project/init", json={
            "source_type": "local",
            "source_path": "/tmp/something",
        })
        data = resp.json()
        assert data["success"] is False
        assert "already" in data["errors"][0].lower()

    def test_delete_project(self):
        """DELETE /project removes config."""
        cfg = ProjectConfig.create_new("local", "/tmp/test")
        cfg.save(self.cfg_path)
        SessionState().save(self.state_path)

        resp = self.client.delete("/api/mcc/project")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert len(data["deleted"]) == 2

        # Config gone
        assert ProjectConfig.load(self.cfg_path) is None

    def test_state_persists_across_restarts(self):
        """State saved by POST is reloaded by GET (simulates restart)."""
        # Save state
        self.client.post("/api/mcc/state", json={
            "level": "workflow",
            "task_id": "tb_456",
            "history": ["roadmap", "tasks"],
        })

        # Simulate "restart" — create new test client
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.routes.mcc_routes import router

        app2 = FastAPI()
        app2.include_router(router)
        client2 = TestClient(app2)

        # Should restore state from file
        resp = client2.get("/api/mcc/state")
        data = resp.json()
        assert data["level"] == "workflow"
        assert data["task_id"] == "tb_456"
        assert data["history"] == ["roadmap", "tasks"]
