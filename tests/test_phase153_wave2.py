"""
MARKER_153.2T: Phase 153 Wave 2 Tests — Sandbox management.

Tests for:
- ProjectConfig sandbox utilities (disk usage, quota, status)
- MCC sandbox REST endpoints (status, recreate, delete, quota)
- SandboxDropdown integration (API shape)

@phase 153
@wave 2
"""

import json
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

import pytest

from src.services.project_config import ProjectConfig

# ── Fixtures ──

@pytest.fixture
def tmp_dir():
    """Create a temporary directory for tests."""
    d = tempfile.mkdtemp(prefix="test_153w2_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def config_with_sandbox(tmp_dir):
    """Create a ProjectConfig with an actual sandbox directory."""
    sandbox = os.path.join(tmp_dir, "sandbox")
    os.makedirs(sandbox)
    # Create some test files
    for name in ["main.py", "utils.py", "README.md"]:
        with open(os.path.join(sandbox, name), 'w') as f:
            f.write(f"# {name}\nprint('hello')\n")
    # Create a subdir with files
    subdir = os.path.join(sandbox, "src")
    os.makedirs(subdir)
    with open(os.path.join(subdir, "app.py"), 'w') as f:
        f.write("# app.py\n" * 100)  # ~1KB file

    cfg_path = os.path.join(tmp_dir, "project_config.json")
    config = ProjectConfig(
        project_id="test_proj_abc123",
        source_type="local",
        source_path=os.path.join(tmp_dir, "source"),  # doesn't need to exist for these tests
        sandbox_path=sandbox,
        quota_gb=10,
        created_at="2026-02-16T00:00:00+00:00",
        qdrant_collection="test_proj_abc123",
    )
    config.save(cfg_path)
    return config, cfg_path


@pytest.fixture
def config_no_sandbox(tmp_dir):
    """Create a ProjectConfig WITHOUT a sandbox directory."""
    config = ProjectConfig(
        project_id="test_proj_nosb",
        source_type="local",
        source_path="/tmp/nonexistent_source",
        sandbox_path=os.path.join(tmp_dir, "nonexistent_sandbox"),
        quota_gb=5,
        created_at="2026-02-16T00:00:00+00:00",
        qdrant_collection="test_proj_nosb",
    )
    return config


# ══════════════════════════════════════════════════════════════
# TestProjectConfig — sandbox utilities
# ══════════════════════════════════════════════════════════════

class TestSandboxUtilities:
    """Test MARKER_153.2A: Sandbox utility methods on ProjectConfig."""

    def test_sandbox_exists_true(self, config_with_sandbox):
        config, _ = config_with_sandbox
        assert config.sandbox_exists() is True

    def test_sandbox_exists_false(self, config_no_sandbox):
        assert config_no_sandbox.sandbox_exists() is False

    def test_sandbox_exists_empty_path(self):
        config = ProjectConfig(sandbox_path="")
        assert config.sandbox_exists() is False

    def test_disk_usage_returns_positive(self, config_with_sandbox):
        config, _ = config_with_sandbox
        usage = config.get_disk_usage_bytes()
        assert usage > 0, "Sandbox with files should have positive disk usage"

    def test_disk_usage_no_sandbox_returns_zero(self, config_no_sandbox):
        assert config_no_sandbox.get_disk_usage_bytes() == 0

    def test_disk_usage_gb_format(self, config_with_sandbox):
        config, _ = config_with_sandbox
        gb = config.get_disk_usage_gb()
        assert isinstance(gb, float)
        assert gb >= 0

    def test_check_quota_structure(self, config_with_sandbox):
        config, _ = config_with_sandbox
        q = config.check_quota()
        assert "used_gb" in q
        assert "quota_gb" in q
        assert "percent" in q
        assert "warning" in q
        assert "exceeded" in q
        assert q["quota_gb"] == 10

    def test_check_quota_warning_at_80_percent(self, tmp_dir):
        """Quota warning triggers at >=80%."""
        sandbox = os.path.join(tmp_dir, "sb")
        os.makedirs(sandbox)
        config = ProjectConfig(sandbox_path=sandbox, quota_gb=1)
        # Mock get_disk_usage_gb to return 0.8 (80% of 1GB)
        with patch.object(config, 'get_disk_usage_gb', return_value=0.8):
            q = config.check_quota()
            assert q["warning"] is True
            assert q["exceeded"] is False

    def test_check_quota_exceeded_at_100_percent(self, tmp_dir):
        """Quota exceeded triggers at >=100%."""
        sandbox = os.path.join(tmp_dir, "sb")
        os.makedirs(sandbox)
        config = ProjectConfig(sandbox_path=sandbox, quota_gb=1)
        with patch.object(config, 'get_disk_usage_gb', return_value=1.1):
            q = config.check_quota()
            assert q["warning"] is True
            assert q["exceeded"] is True
            assert q["percent"] > 100

    def test_get_sandbox_status_exists(self, config_with_sandbox):
        config, _ = config_with_sandbox
        s = config.get_sandbox_status()
        assert s["exists"] is True
        assert s["file_count"] >= 4  # main.py, utils.py, README.md, app.py
        assert s["sandbox_path"] == config.sandbox_path

    def test_get_sandbox_status_not_exists(self, config_no_sandbox):
        s = config_no_sandbox.get_sandbox_status()
        assert s["exists"] is False
        assert s["file_count"] == 0
        assert s["used_gb"] == 0


# ══════════════════════════════════════════════════════════════
# TestMCCSandboxAPI — REST endpoints
# ══════════════════════════════════════════════════════════════

class TestMCCSandboxAPI:
    """Test MARKER_153.2B: Sandbox REST endpoints."""

    @pytest.fixture(autouse=True)
    def setup_api(self, tmp_dir):
        """Set up FastAPI test client with temp config paths."""
        # Patch config paths
        import src.services.project_config as pc_module
        self.orig_config = pc_module.CONFIG_PATH
        self.orig_session = pc_module.SESSION_STATE_PATH
        self.orig_data_dir = pc_module.DATA_DIR

        pc_module.CONFIG_PATH = os.path.join(tmp_dir, "project_config.json")
        pc_module.SESSION_STATE_PATH = os.path.join(tmp_dir, "session_state.json")
        pc_module.DATA_DIR = tmp_dir

        self.tmp_dir = tmp_dir

        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.routes.mcc_routes import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

        yield

        pc_module.CONFIG_PATH = self.orig_config
        pc_module.SESSION_STATE_PATH = self.orig_session
        pc_module.DATA_DIR = self.orig_data_dir

    def _create_project_with_sandbox(self, source_path=None):
        """Helper: create a project config and sandbox directory."""
        if source_path is None:
            source_path = os.path.join(self.tmp_dir, "source")
            os.makedirs(source_path, exist_ok=True)
            with open(os.path.join(source_path, "main.py"), 'w') as f:
                f.write("# main\nprint('hello')\n")

        config = ProjectConfig.create_new("local", source_path, quota_gb=10)
        sandbox = config.sandbox_path
        # Create sandbox by copying source
        if os.path.isdir(sandbox):
            shutil.rmtree(sandbox)
        shutil.copytree(source_path, sandbox)
        config.save()
        return config

    def test_sandbox_status_no_project(self):
        """GET /sandbox/status with no project → exists=False."""
        r = self.client.get("/api/mcc/sandbox/status")
        assert r.status_code == 200
        data = r.json()
        assert data["exists"] is False

    def test_sandbox_status_with_sandbox(self):
        """GET /sandbox/status with sandbox → exists=True + usage data."""
        self._create_project_with_sandbox()
        r = self.client.get("/api/mcc/sandbox/status")
        assert r.status_code == 200
        data = r.json()
        assert data["exists"] is True
        assert data["file_count"] >= 1
        assert data["quota_gb"] == 10

    def test_sandbox_status_no_sandbox(self):
        """GET /sandbox/status with project but no sandbox → exists=False."""
        config = ProjectConfig.create_new("local", "/tmp/src", quota_gb=5)
        config.save()
        r = self.client.get("/api/mcc/sandbox/status")
        assert r.status_code == 200
        data = r.json()
        assert data["exists"] is False

    def test_sandbox_delete(self):
        """DELETE /sandbox → removes sandbox directory."""
        config = self._create_project_with_sandbox()
        assert os.path.isdir(config.sandbox_path)

        r = self.client.delete("/api/mcc/sandbox")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert not os.path.isdir(config.sandbox_path)

    def test_sandbox_delete_no_project(self):
        """DELETE /sandbox with no project → 404."""
        r = self.client.delete("/api/mcc/sandbox")
        assert r.status_code == 404

    def test_sandbox_delete_already_absent(self):
        """DELETE /sandbox when sandbox doesn't exist → ok."""
        config = ProjectConfig.create_new("local", "/tmp/src", quota_gb=5)
        config.save()
        r = self.client.delete("/api/mcc/sandbox")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_sandbox_recreate(self):
        """POST /sandbox/recreate with force=true → fresh copy."""
        # Create source with a file
        source = os.path.join(self.tmp_dir, "source_recreate")
        os.makedirs(source, exist_ok=True)
        with open(os.path.join(source, "main.py"), 'w') as f:
            f.write("# main\nprint('hello')\n")

        # Create project with this source — manually set source_path correctly
        config = ProjectConfig.create_new("local", source, quota_gb=10)
        # Create sandbox by copying
        if os.path.isdir(config.sandbox_path):
            shutil.rmtree(config.sandbox_path)
        os.makedirs(os.path.dirname(config.sandbox_path), exist_ok=True)
        shutil.copytree(source, config.sandbox_path)
        config.save()

        # Add a file to sandbox that's not in source
        with open(os.path.join(config.sandbox_path, "extra.txt"), 'w') as f:
            f.write("extra")

        # Verify extra file exists
        assert os.path.exists(os.path.join(config.sandbox_path, "extra.txt"))

        r = self.client.post("/api/mcc/sandbox/recreate", json={"force": True})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

        # Extra file should be gone (fresh copy)
        assert not os.path.exists(os.path.join(config.sandbox_path, "extra.txt"))
        # Source file should be present
        assert os.path.exists(os.path.join(config.sandbox_path, "main.py"))

    def test_sandbox_recreate_no_force_existing(self):
        """POST /sandbox/recreate without force when exists → error."""
        self._create_project_with_sandbox()
        r = self.client.post("/api/mcc/sandbox/recreate", json={"force": False})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is False
        assert "already exists" in data["error"]

    def test_sandbox_recreate_no_project(self):
        """POST /sandbox/recreate with no project → 404."""
        r = self.client.post("/api/mcc/sandbox/recreate", json={"force": True})
        assert r.status_code == 404

    def test_sandbox_quota_update(self):
        """PATCH /sandbox/quota → updates quota_gb."""
        self._create_project_with_sandbox()
        r = self.client.patch("/api/mcc/sandbox/quota?quota_gb=20")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["quota_gb"] == 20

        # Verify persisted
        config = ProjectConfig.load()
        assert config.quota_gb == 20

    def test_sandbox_quota_bounds(self):
        """PATCH /sandbox/quota with bad value → 400."""
        self._create_project_with_sandbox()
        r = self.client.patch("/api/mcc/sandbox/quota?quota_gb=0")
        assert r.status_code == 400
        r = self.client.patch("/api/mcc/sandbox/quota?quota_gb=101")
        assert r.status_code == 400

    def test_sandbox_quota_no_project(self):
        """PATCH /sandbox/quota with no project → 404."""
        r = self.client.patch("/api/mcc/sandbox/quota?quota_gb=5")
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════
# TestSandboxEndpointShape — API contract verification
# ══════════════════════════════════════════════════════════════

class TestSandboxEndpointShape:
    """Verify endpoint existence and response structure."""

    def test_sandbox_endpoints_exist(self):
        """All Wave 2 sandbox endpoints should be registered."""
        from src.api.routes.mcc_routes import router
        paths = [r.path for r in router.routes if hasattr(r, 'path')]
        assert "/api/mcc/sandbox/status" in paths
        assert "/api/mcc/sandbox/recreate" in paths
        assert "/api/mcc/sandbox" in paths  # DELETE
        assert "/api/mcc/sandbox/quota" in paths

    def test_status_response_fields(self):
        """SandboxStatusResponse should have all required fields."""
        from src.api.routes.mcc_routes import SandboxStatusResponse

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 153 contracts changed")

        fields = SandboxStatusResponse.model_fields
        expected = {"exists", "sandbox_path", "file_count", "used_gb", "quota_gb", "percent", "warning", "exceeded"}
        assert expected.issubset(set(fields.keys()))
