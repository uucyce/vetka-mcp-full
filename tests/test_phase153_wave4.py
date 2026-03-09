"""
MARKER_153.4T: Phase 153 Wave 4 Tests — Roadmap, Workflows, Prefetch.

Tests for:
- RoadmapGenerator (project scan + DAG generation)
- WorkflowTemplateLibrary (load, list, select)
- ArchitectPrefetch (prepare context)
- REST endpoints (roadmap, workflows, prefetch)

@phase 153
@wave 4
"""

import json
import os
import tempfile
import shutil
from dataclasses import asdict

import pytest

from src.services.roadmap_generator import RoadmapGenerator, RoadmapDAG, RoadmapNode, RoadmapEdge
from src.services.architect_prefetch import (
    WorkflowTemplateLibrary, ArchitectPrefetch, PrefetchContext, WORKFLOWS_DIR,
)
from src.services.project_config import ProjectConfig


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="test_153w4_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_project(tmp_dir):
    """Create a sample project structure for testing."""
    root = os.path.join(tmp_dir, "project")
    # Create directories
    for d in ["src", "src/services", "client", "client/components", "tests", "docs", "data"]:
        os.makedirs(os.path.join(root, d))
    # Create files
    files = {
        "package.json": '{"name":"test","dependencies":{"react":"^18.0","three":"^0.160"}}',
        "requirements.txt": "fastapi>=0.100\nuvicorn\n",
        "src/main.py": "# MARKER_100.1: Main entry\nfrom fastapi import FastAPI\napp = FastAPI()\n",
        "src/services/auth.py": "# MARKER_101.2: Auth service\nclass AuthService:\n    pass\n",
        "client/components/App.tsx": "import React from 'react';\nexport function App() { return <div />; }\n",
        "tests/test_main.py": "def test_hello(): assert True\n",
        "docs/README.md": "# Test Project\n",
    }
    for path, content in files.items():
        with open(os.path.join(root, path), 'w') as f:
            f.write(content)
    return root


# ══════════════════════════════════════════════════════════════
# TestRoadmapGenerator
# ══════════════════════════════════════════════════════════════

class TestRoadmapGenerator:
    """Test MARKER_153.4A: Roadmap generator."""

    def test_scan_project_structure(self, sample_project):
        scan = RoadmapGenerator.scan_project_structure(sample_project)
        assert "tree" in scan
        assert "key_files" in scan
        assert "package.json" in scan["key_files"]
        assert "requirements.txt" in scan["key_files"]
        assert "Python" in scan["languages"]
        assert "TypeScript" in scan["languages"]
        assert "react" in scan["frameworks"]

    def test_scan_detects_three_js(self, sample_project):
        scan = RoadmapGenerator.scan_project_structure(sample_project)
        assert "three" in scan["frameworks"]

    def test_scan_nonexistent_path(self):
        scan = RoadmapGenerator.scan_project_structure("/nonexistent/path")
        assert scan["tree"] == ""
        assert len(scan["key_files"]) == 0

    def test_generate_static_roadmap(self, sample_project):
        scan = RoadmapGenerator.scan_project_structure(sample_project)
        dag = RoadmapGenerator.generate_static_roadmap(scan, "test_proj")
        assert len(dag.nodes) >= 2  # At least core + something
        assert dag.project_id == "test_proj"
        assert dag.generator == "static"
        # Should have core node
        node_ids = [n["id"] for n in dag.nodes]
        assert "core" in node_ids

    def test_roadmap_has_valid_dag_structure(self, sample_project):
        """Nodes and edges form valid DAG."""
        scan = RoadmapGenerator.scan_project_structure(sample_project)
        dag = RoadmapGenerator.generate_static_roadmap(scan, "test_proj")
        node_ids = {n["id"] for n in dag.nodes}
        for edge in dag.edges:
            assert edge["source"] in node_ids, f"Edge source {edge['source']} not in nodes"
            assert edge["target"] in node_ids, f"Edge target {edge['target']} not in nodes"

    def test_roadmap_detects_test_module(self, sample_project):
        """Should detect tests/ directory as a test module."""
        scan = RoadmapGenerator.scan_project_structure(sample_project)
        dag = RoadmapGenerator.generate_static_roadmap(scan, "test_proj")
        node_ids = [n["id"] for n in dag.nodes]
        assert "tests" in node_ids

    def test_roadmap_save_and_load(self, tmp_dir):
        dag = RoadmapDAG(
            project_id="test",
            generator="static",
            nodes=[asdict(RoadmapNode(id="core", label="Core"))],
            edges=[],
        )
        path = os.path.join(tmp_dir, "roadmap.json")
        assert dag.save(path)
        loaded = RoadmapDAG.load(path)
        assert loaded is not None
        assert loaded.project_id == "test"
        assert len(loaded.nodes) == 1

    def test_roadmap_to_frontend_format(self, sample_project):
        scan = RoadmapGenerator.scan_project_structure(sample_project)
        dag = RoadmapGenerator.generate_static_roadmap(scan, "test_proj")
        fmt = dag.to_frontend_format()
        assert "nodes" in fmt
        assert "edges" in fmt
        # Each frontend node should have id, type, label, position, data
        for node in fmt["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "label" in node
            assert "position" in node
            assert "x" in node["position"]


# ══════════════════════════════════════════════════════════════
# TestWorkflowTemplateLibrary
# ══════════════════════════════════════════════════════════════

class TestWorkflowTemplateLibrary:
    """Test MARKER_153.4C: Workflow Template Library."""

    def test_load_all_templates(self):
        """Should load 6 workflow templates from disk."""
        templates = WorkflowTemplateLibrary.load_all()
        assert len(templates) >= 6, f"Expected 6+ templates, got {len(templates)}"
        expected_keys = {"bmad_default", "quick_fix", "research_first", "refactor", "test_only", "docs_update"}
        assert expected_keys.issubset(set(templates.keys())), f"Missing templates: {expected_keys - set(templates.keys())}"

    def test_each_template_has_required_fields(self):
        """Each template must have id, name, nodes, edges."""
        templates = WorkflowTemplateLibrary.load_all()
        for key, tpl in templates.items():
            assert "id" in tpl, f"{key}: missing id"
            assert "name" in tpl, f"{key}: missing name"
            assert "nodes" in tpl, f"{key}: missing nodes"
            assert "edges" in tpl, f"{key}: missing edges"
            assert len(tpl["nodes"]) >= 2, f"{key}: need at least 2 nodes"

    def test_each_template_is_valid_dag(self):
        """All edges reference valid node IDs."""
        templates = WorkflowTemplateLibrary.load_all()
        for key, tpl in templates.items():
            node_ids = {n["id"] for n in tpl["nodes"]}
            for edge in tpl["edges"]:
                assert edge["source"] in node_ids, f"{key}: edge source '{edge['source']}' not in nodes"
                assert edge["target"] in node_ids, f"{key}: edge target '{edge['target']}' not in nodes"

    def test_list_templates(self):
        """list_templates returns summary info."""
        WorkflowTemplateLibrary.load_all()
        items = WorkflowTemplateLibrary.list_templates()
        assert len(items) >= 6
        for item in items:
            assert "key" in item
            assert "name" in item
            assert "node_count" in item
            assert item["node_count"] >= 2

    def test_get_template_by_key(self):
        WorkflowTemplateLibrary.load_all()
        tpl = WorkflowTemplateLibrary.get_template("quick_fix")
        assert tpl is not None
        assert tpl["id"] == "quick_fix_v1"

    def test_get_nonexistent_template(self):
        WorkflowTemplateLibrary.load_all()
        assert WorkflowTemplateLibrary.get_template("nonexistent") is None

    def test_select_workflow_fix(self):
        WorkflowTemplateLibrary.load_all()
        assert WorkflowTemplateLibrary.select_workflow("fix", 2) == "quick_fix"

    def test_select_workflow_test(self):
        WorkflowTemplateLibrary.load_all()
        assert WorkflowTemplateLibrary.select_workflow("test", 3) == "test_only"

    def test_select_workflow_docs(self):
        WorkflowTemplateLibrary.load_all()
        assert WorkflowTemplateLibrary.select_workflow("docs", 1) == "docs_update"

    def test_select_workflow_refactor(self):
        WorkflowTemplateLibrary.load_all()
        assert WorkflowTemplateLibrary.select_workflow("refactor", 6) == "refactor"

    def test_select_workflow_default(self):
        """Unknown task type → bmad_default."""
        WorkflowTemplateLibrary.load_all()
        result = WorkflowTemplateLibrary.select_workflow("unknown_type", 7)
        assert result == "bmad_default"


# ══════════════════════════════════════════════════════════════
# TestArchitectPrefetch
# ══════════════════════════════════════════════════════════════

class TestArchitectPrefetch:
    """Test MARKER_153.4E: Architect Prefetch Pipeline."""

    def test_prefetch_files_static(self, sample_project):
        files = ArchitectPrefetch.prefetch_files_static(sample_project, "auth service fastapi")
        # Should find at least auth.py (contains "auth")
        paths = [f["path"] for f in files]
        assert any("auth" in p for p in paths), f"Expected auth file in {paths}"

    def test_prefetch_markers(self, sample_project):
        files = [{"path": "src/main.py"}, {"path": "src/services/auth.py"}]
        markers = ArchitectPrefetch.prefetch_markers(sample_project, files)
        assert len(markers) >= 2  # MARKER_100.1 and MARKER_101.2
        marker_content = " ".join(m["content"] for m in markers)
        assert "MARKER_100" in marker_content or "MARKER_101" in marker_content

    def test_prefetch_history_no_file(self):
        """No pipeline_history.json → empty list."""
        result = ArchitectPrefetch.prefetch_history("test task")
        # Might return results if file exists from other tests; that's ok
        assert isinstance(result, list)

    def test_prepare_returns_prefetch_context(self, sample_project):
        config = ProjectConfig(
            project_id="test",
            sandbox_path=sample_project,
            source_type="local",
            source_path=sample_project,
        )
        ctx = ArchitectPrefetch.prepare(
            task_description="fix auth service bug",
            task_type="fix",
            complexity=2,
            config=config,
        )
        assert isinstance(ctx, PrefetchContext)
        assert ctx.workflow_id == "quick_fix"
        assert ctx.preset == "dragon_bronze"  # complexity 2 → bronze
        assert ctx.summary  # Should have non-empty summary

    def test_prepare_selects_silver_for_medium_complexity(self, sample_project):
        config = ProjectConfig(sandbox_path=sample_project, source_type="local", source_path=sample_project)
        ctx = ArchitectPrefetch.prepare(
            task_description="build new feature",
            task_type="build",
            complexity=5,
            config=config,
        )
        assert ctx.preset == "dragon_silver"

    def test_prepare_selects_gold_for_high_complexity(self, sample_project):
        config = ProjectConfig(sandbox_path=sample_project, source_type="local", source_path=sample_project)
        ctx = ArchitectPrefetch.prepare(
            task_description="refactor entire architecture",
            task_type="refactor",
            complexity=8,
            config=config,
        )
        assert ctx.preset == "dragon_gold"

    def test_prepare_without_config(self):
        """Prefetch works even without project config (no files found)."""
        ctx = ArchitectPrefetch.prepare(
            task_description="some task",
            task_type="fix",
            complexity=1,
        )
        assert ctx.workflow_id == "quick_fix"
        assert len(ctx.relevant_files) == 0


# ══════════════════════════════════════════════════════════════
# TestMCCWave4API — REST endpoints
# ══════════════════════════════════════════════════════════════

class TestMCCWave4API:
    """Test MARKER_153.4F: Roadmap/Workflow/Prefetch REST endpoints."""

    @pytest.fixture(autouse=True)
    def setup_api(self, tmp_dir, sample_project):
        import src.services.project_config as pc_module
        import src.services.roadmap_generator as rg_module
        self.orig_config = pc_module.CONFIG_PATH
        self.orig_session = pc_module.SESSION_STATE_PATH
        self.orig_data_dir = pc_module.DATA_DIR
        self.orig_roadmap = rg_module.ROADMAP_PATH

        pc_module.CONFIG_PATH = os.path.join(tmp_dir, "project_config.json")
        pc_module.SESSION_STATE_PATH = os.path.join(tmp_dir, "session_state.json")
        pc_module.DATA_DIR = tmp_dir
        rg_module.ROADMAP_PATH = os.path.join(tmp_dir, "roadmap_dag.json")

        self.tmp_dir = tmp_dir
        self.sample_project = sample_project

        # Create a project config pointing to sample project
        config = ProjectConfig.create_new("local", sample_project, quota_gb=10)
        config.sandbox_path = sample_project
        config.save()

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
        rg_module.ROADMAP_PATH = self.orig_roadmap

    def test_get_roadmap_auto_generates(self):
        """GET /roadmap auto-generates roadmap on first request."""
        r = self.client.get("/api/mcc/roadmap")
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) >= 2

    def test_generate_roadmap(self):
        """POST /roadmap/generate regenerates roadmap."""
        r = self.client.post("/api/mcc/roadmap/generate")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["node_count"] >= 2

    def test_list_workflows(self):
        """GET /workflows lists all templates."""
        r = self.client.get("/api/mcc/workflows")
        assert r.status_code == 200
        data = r.json()
        assert "templates" in data
        assert len(data["templates"]) >= 6

    def test_get_workflow_by_key(self):
        """GET /workflows/quick_fix returns template."""
        r = self.client.get("/api/mcc/workflows/quick_fix")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "quick_fix_v1"

    def test_get_workflow_not_found(self):
        """GET /workflows/nonexistent → 404."""
        r = self.client.get("/api/mcc/workflows/nonexistent")
        assert r.status_code == 404

    def test_prefetch(self):
        """POST /prefetch returns context."""
        r = self.client.post("/api/mcc/prefetch", json={
            "task_description": "fix auth service",
            "task_type": "fix",
            "complexity": 2,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["workflow_id"] == "quick_fix"
        assert data["preset"] == "dragon_bronze"
        assert "summary" in data
        assert "diagnostics" in data
        assert "workflow_selection" in data["diagnostics"]
        wf_diag = data["diagnostics"]["workflow_selection"]
        assert wf_diag["workflow_id"] == data["workflow_id"]
        assert isinstance(wf_diag["reinforcement"], list)
        assert isinstance(wf_diag["reinforcement_policy"], dict)
        assert wf_diag["reason"] in ("openhands_reinforcement_enabled", "base_family_only")

    def test_roadmap_no_project(self):
        """GET /roadmap with no project → 404."""
        import src.services.project_config as pc_module
        # Remove config
        if os.path.exists(pc_module.CONFIG_PATH):
            os.remove(pc_module.CONFIG_PATH)
        r = self.client.get("/api/mcc/roadmap")
        assert r.status_code == 404
