"""
MARKER_153.5T: Phase 153 Wave 5 Tests — Navigation Rendering, Breadcrumb, Level-Aware DAG.

Tests for:
- MCCBreadcrumb component shape (imports, props)
- useRoadmapDAG hook shape (imports, exports)
- Level-aware navigation (drillDown, goBack, keyboard)
- Roadmap DAG endpoint integration (auto-fetch at roadmap level)
- DAGView onNodeDoubleClick prop
- WorkflowToolbar conditional rendering per level

@phase 153
@wave 5
"""

import os
import re
import json
import tempfile
import shutil
from pathlib import Path

import pytest


# ══════════════════════════════════════════════════════════════
# Locate frontend files
# ══════════════════════════════════════════════════════════════

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_SRC = os.path.join(ROOT, "client", "src")


def _read(relpath: str) -> str:
    """Read a frontend file relative to project root."""
    full = os.path.join(ROOT, relpath)
    if not os.path.exists(full):
        return ""
    with open(full, "r") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════
# TestMCCBreadcrumb — Component Shape
# ══════════════════════════════════════════════════════════════

class TestMCCBreadcrumb:
    """Test MARKER_153.5A: Breadcrumb component."""

    def test_file_exists(self):
        path = os.path.join(CLIENT_SRC, "components", "mcc", "MCCBreadcrumb.tsx")
        assert os.path.exists(path), "MCCBreadcrumb.tsx must exist"

    def test_imports_useMCCStore(self):
        code = _read("client/src/components/mcc/MCCBreadcrumb.tsx")
        assert "useMCCStore" in code

    def test_imports_NavLevel_type(self):
        code = _read("client/src/components/mcc/MCCBreadcrumb.tsx")
        assert "NavLevel" in code

    def test_exports_MCCBreadcrumb(self):
        code = _read("client/src/components/mcc/MCCBreadcrumb.tsx")
        assert "export function MCCBreadcrumb" in code

    def test_has_level_labels_for_all_levels(self):
        code = _read("client/src/components/mcc/MCCBreadcrumb.tsx")
        for level in ["roadmap", "tasks", "workflow", "running", "results"]:
            assert level in code, f"Missing label for level: {level}"

    def test_goBack_wired(self):
        code = _read("client/src/components/mcc/MCCBreadcrumb.tsx")
        assert "goBack" in code, "Breadcrumb must call goBack"

    def test_esc_hint_shown(self):
        code = _read("client/src/components/mcc/MCCBreadcrumb.tsx")
        assert "Esc" in code, "Should show Esc keyboard hint"

    def test_separator_character(self):
        code = _read("client/src/components/mcc/MCCBreadcrumb.tsx")
        assert "›" in code, "Should use › as separator"


# ══════════════════════════════════════════════════════════════
# TestUseRoadmapDAG — Hook Shape
# ══════════════════════════════════════════════════════════════

class TestUseRoadmapDAG:
    """Test MARKER_153.5B: Roadmap DAG data hook."""

    def test_file_exists(self):
        path = os.path.join(CLIENT_SRC, "hooks", "useRoadmapDAG.ts")
        assert os.path.exists(path), "useRoadmapDAG.ts must exist"

    def test_exports_hook(self):
        code = _read("client/src/hooks/useRoadmapDAG.ts")
        assert "export function useRoadmapDAG" in code

    def test_fetches_from_mcc_roadmap(self):
        code = _read("client/src/hooks/useRoadmapDAG.ts")
        assert "/mcc/roadmap" in code, "Hook must fetch from /api/mcc/roadmap"

    def test_returns_nodes_and_edges(self):
        code = _read("client/src/hooks/useRoadmapDAG.ts")
        assert "DAGNode" in code
        assert "DAGEdge" in code

    def test_has_fetchRoadmap_method(self):
        code = _read("client/src/hooks/useRoadmapDAG.ts")
        assert "fetchRoadmap" in code

    def test_has_regenerateRoadmap_method(self):
        code = _read("client/src/hooks/useRoadmapDAG.ts")
        assert "regenerateRoadmap" in code

    def test_handles_404_gracefully(self):
        code = _read("client/src/hooks/useRoadmapDAG.ts")
        assert "404" in code, "Should handle 404 (no project) gracefully"

    def test_maps_roadmap_layer_to_node_type(self):
        code = _read("client/src/hooks/useRoadmapDAG.ts")
        assert "LAYER_NODE_TYPE" in code, "Should map roadmap layers to DAG node types"


# ══════════════════════════════════════════════════════════════
# TestMCCIntegration — Level-Aware Rendering
# ══════════════════════════════════════════════════════════════

class TestMCCIntegration:
    """Test MARKER_153.5: Level-aware rendering in MCC."""

    def test_mcc_imports_breadcrumb(self):
        code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        assert "MCCBreadcrumb" in code

    def test_mcc_imports_useRoadmapDAG(self):
        code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        assert "useRoadmapDAG" in code

    def test_mcc_renders_breadcrumb(self):
        code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        assert "<MCCBreadcrumb" in code

    def test_mcc_has_navLevel_state(self):
        code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        assert "navLevel" in code

    def test_mcc_has_drillDown_action(self):
        code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        assert "drillDown" in code

    def test_mcc_has_goBack_action(self):
        code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        assert "goBack" in code

    def test_mcc_fetches_roadmap_on_ready(self):
        code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        assert "roadmap.fetchRoadmap" in code, "Should fetch roadmap when mccReady"

    def test_mcc_level_aware_effective_nodes(self):
        """At roadmap level, should use roadmap nodes instead of workflow DAG."""
        code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        assert "roadmap.nodes" in code
        assert "roadmap.edges" in code

    def test_mcc_keyboard_escape_goback(self):
        """Esc key should trigger goBack (via useKeyboardShortcuts hook)."""
        mcc = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        # MCC delegates to useKeyboardShortcuts hook
        assert "useKeyboardShortcuts" in mcc
        # Hook handles Escape globally
        hook = _read("client/src/hooks/useKeyboardShortcuts.ts")
        assert "'Escape'" in hook or '"Escape"' in hook

    def test_mcc_keyboard_enter_drill(self):
        """Enter key at roadmap level should drill down (via useKeyboardShortcuts hook)."""
        mcc = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        assert "onDrillNode:" in mcc
        # Hook handles Enter per level
        hook = _read("client/src/hooks/useKeyboardShortcuts.ts")
        assert "Enter" in hook

    def test_mcc_workflow_toolbar_conditional(self):
        """WorkflowToolbar should NOT show at roadmap level."""
        code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        # Check that toolbar is wrapped in a conditional
        assert "navLevel === 'workflow'" in code or "navLevel === 'tasks'" in code

    def test_mcc_roadmap_edit_disabled(self):
        """At roadmap level, editMode should be false for DAGView."""
        code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        assert "navLevel === 'roadmap' ? false : editMode" in code

    def test_mcc_passes_node_double_click(self):
        """DAGView should receive onNodeDoubleClick prop."""
        code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
        assert "onNodeDoubleClick" in code


# ══════════════════════════════════════════════════════════════
# TestDAGViewExtension — Node Double-Click
# ══════════════════════════════════════════════════════════════

class TestDAGViewExtension:
    """Test MARKER_153.5D: DAGView onNodeDoubleClick extension."""

    def test_dagview_has_double_click_prop(self):
        code = _read("client/src/components/mcc/DAGView.tsx")
        assert "onNodeDoubleClick" in code

    def test_dagview_props_interface(self):
        code = _read("client/src/components/mcc/DAGView.tsx")
        # Should have the prop in the interface
        assert "onNodeDoubleClick?: (nodeId: string) => void" in code

    def test_dagview_handles_double_click(self):
        code = _read("client/src/components/mcc/DAGView.tsx")
        assert "handleNodeDoubleClick" in code

    def test_dagview_wires_to_reactflow(self):
        code = _read("client/src/components/mcc/DAGView.tsx")
        assert "onNodeDoubleClick={" in code


# ══════════════════════════════════════════════════════════════
# TestNavigationAPI — Backend endpoints used by navigation
# ══════════════════════════════════════════════════════════════

class TestNavigationAPI:
    """Test that backend endpoints needed by navigation exist and work."""

    @pytest.fixture(autouse=True)
    def setup_api(self, tmp_path):
        import src.services.project_config as pc_module
        import src.services.roadmap_generator as rg_module

        self.orig_config = pc_module.CONFIG_PATH
        self.orig_session = pc_module.SESSION_STATE_PATH
        self.orig_data_dir = pc_module.DATA_DIR
        self.orig_roadmap = rg_module.ROADMAP_PATH

        pc_module.CONFIG_PATH = str(tmp_path / "project_config.json")
        pc_module.SESSION_STATE_PATH = str(tmp_path / "session_state.json")
        pc_module.DATA_DIR = str(tmp_path)
        rg_module.ROADMAP_PATH = str(tmp_path / "roadmap_dag.json")

        self.tmp_path = tmp_path

        # Create sample project
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "src").mkdir()
        (project_dir / "tests").mkdir()
        (project_dir / "src" / "main.py").write_text("# MARKER_100.1\nfrom fastapi import FastAPI\n")
        (project_dir / "package.json").write_text('{"name":"test","dependencies":{"react":"^18"}}')
        self.project_dir = project_dir

        # Save config
        from src.services.project_config import ProjectConfig
        config = ProjectConfig.create_new("local", str(project_dir), quota_gb=10)
        config.sandbox_path = str(project_dir)
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

    def test_roadmap_returns_nodes_and_edges(self):
        """GET /roadmap should return nodes and edges arrays."""
        r = self.client.get("/api/mcc/roadmap")
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_roadmap_nodes_have_frontend_format(self):
        """Each roadmap node should have id, type, label, position, data."""
        r = self.client.get("/api/mcc/roadmap")
        data = r.json()
        for node in data["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "label" in node
            assert "position" in node
            assert "x" in node["position"]

    def test_state_save_and_load_navigation(self):
        """Save nav state → load it back."""
        # Save state at tasks level
        r = self.client.post("/api/mcc/state", json={
            "level": "tasks",
            "roadmap_node_id": "frontend",
            "task_id": "",
            "history": ["roadmap"],
        })
        assert r.status_code == 200

        # Load state back
        r = self.client.get("/api/mcc/state")
        assert r.status_code == 200
        data = r.json()
        assert data["level"] == "tasks"
        assert data["roadmap_node_id"] == "frontend"
        assert data["history"] == ["roadmap"]

    def test_init_returns_navigation_state(self):
        """GET /init should include saved navigation state."""
        # Save some navigation state first
        self.client.post("/api/mcc/state", json={
            "level": "workflow",
            "roadmap_node_id": "core",
            "task_id": "tb_123",
            "history": ["roadmap", "tasks"],
        })

        # Init should return it
        r = self.client.get("/api/mcc/init")
        assert r.status_code == 200
        data = r.json()
        assert data["has_project"] is True
        assert data["session_state"]["level"] == "workflow"
        assert data["session_state"]["roadmap_node_id"] == "core"
        assert data["session_state"]["task_id"] == "tb_123"
        assert data["session_state"]["history"] == ["roadmap", "tasks"]

    def test_workflows_list_available(self):
        """GET /workflows should return template list for workflow selection."""
        r = self.client.get("/api/mcc/workflows")
        assert r.status_code == 200
        data = r.json()
        assert "templates" in data
        assert len(data["templates"]) >= 6

    def test_prefetch_for_drill_down(self):
        """POST /prefetch can be used when drilling into a task."""
        r = self.client.post("/api/mcc/prefetch", json={
            "task_description": "implement frontend navigation",
            "task_type": "build",
            "complexity": 4,
        })
        assert r.status_code == 200
        data = r.json()
        assert "workflow_id" in data
        assert "preset" in data
        assert "summary" in data
        assert "diagnostics" in data
        assert "workflow_selection" in data["diagnostics"]


# ══════════════════════════════════════════════════════════════
# TestUSMCCStoreNavigation — Zustand store navigation actions
# ══════════════════════════════════════════════════════════════

class TestUSMCCStoreNavigation:
    """Test that useMCCStore has correct navigation shape."""

    def test_store_has_navLevel(self):
        code = _read("client/src/store/useMCCStore.ts")
        assert "navLevel:" in code or "navLevel :" in code

    def test_store_has_drillDown(self):
        code = _read("client/src/store/useMCCStore.ts")
        assert "drillDown:" in code

    def test_store_has_goBack(self):
        code = _read("client/src/store/useMCCStore.ts")
        assert "goBack:" in code

    def test_store_persists_state(self):
        code = _read("client/src/store/useMCCStore.ts")
        assert "_persistState" in code

    def test_store_drillDown_pushes_history(self):
        code = _read("client/src/store/useMCCStore.ts")
        # drillDown should push current level onto history
        assert "navHistory" in code
        assert "prev.navLevel" in code

    def test_store_goBack_pops_history(self):
        code = _read("client/src/store/useMCCStore.ts")
        assert "history.pop()" in code
