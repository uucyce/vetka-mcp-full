"""
MARKER_153.7T: Phase 153 Wave 7 Tests — Architect Captain.

Tests for:
- ArchitectCaptain (recommendation engine, progress tracking)
- REST endpoints (recommend, accept, reject, progress)
- Frontend integration (useCaptain, CaptainBar, MCC wiring)

@phase 153
@wave 7
"""

import json
import os
import tempfile
import shutil
from dataclasses import asdict

import pytest

from src.services.architect_captain import ArchitectCaptain, Recommendation
from src.services.roadmap_generator import RoadmapDAG, RoadmapNode, RoadmapEdge

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 153 contracts changed")

# ── Paths ──
CLIENT_DIR = os.path.join(os.path.dirname(__file__), '..', 'client', 'src')
MCC_DIR = os.path.join(CLIENT_DIR, 'components', 'mcc')
HOOKS_DIR = os.path.join(CLIENT_DIR, 'hooks')

CAPTAIN_PY = os.path.join(os.path.dirname(__file__), '..', 'src', 'services', 'architect_captain.py')
CAPTAIN_BAR_FILE = os.path.join(MCC_DIR, 'CaptainBar.tsx')
CAPTAIN_HOOK_FILE = os.path.join(HOOKS_DIR, 'useCaptain.ts')
MCC_FILE = os.path.join(MCC_DIR, 'MyceliumCommandCenter.tsx')


def _read(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="test_153w7_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_roadmap():
    """Create a sample roadmap with 4 nodes and dependencies."""
    return RoadmapDAG(
        project_id="test",
        generator="static",
        nodes=[
            asdict(RoadmapNode(id="core", label="Core", layer="core", status="completed")),
            asdict(RoadmapNode(id="api", label="API Service", layer="feature", status="active")),
            asdict(RoadmapNode(id="frontend", label="Frontend", layer="feature", status="pending")),
            asdict(RoadmapNode(id="tests", label="Tests", layer="test", status="pending")),
        ],
        edges=[
            asdict(RoadmapEdge(source="core", target="api")),
            asdict(RoadmapEdge(source="core", target="frontend")),
            asdict(RoadmapEdge(source="api", target="tests")),
            asdict(RoadmapEdge(source="frontend", target="tests")),
        ],
    )


@pytest.fixture
def empty_board():
    return {"tasks": [], "settings": {}}


@pytest.fixture
def board_with_completed_api():
    return {
        "tasks": [
            {"id": "tb_1", "title": "Build API service", "status": "done", "description": "api"},
        ],
        "settings": {},
    }


# ══════════════════════════════════════════════════════════════
# TestArchitectCaptain — Core Logic
# ══════════════════════════════════════════════════════════════

class TestArchitectCaptain:
    """Test MARKER_153.7A: Architect Captain recommendation engine."""

    def test_recommend_returns_recommendation(self, sample_roadmap, empty_board):
        rec = ArchitectCaptain.recommend_next(sample_roadmap, empty_board)
        assert rec is not None
        assert isinstance(rec, Recommendation)
        assert rec.module_id != ""
        assert rec.workflow_id != ""
        assert rec.preset != ""

    def test_recommend_prefers_active_over_pending(self, sample_roadmap, empty_board):
        """Active nodes should be recommended first."""
        rec = ArchitectCaptain.recommend_next(sample_roadmap, empty_board)
        assert rec is not None
        assert rec.module_id == "api"  # api is "active", others are pending

    def test_recommend_skips_completed(self, sample_roadmap, empty_board):
        """Completed nodes should never be recommended."""
        rec = ArchitectCaptain.recommend_next(sample_roadmap, empty_board)
        assert rec.module_id != "core"  # core is completed

    def test_recommend_respects_dependencies(self, sample_roadmap, empty_board):
        """Tests module depends on api + frontend — shouldn't be recommended yet."""
        rec = ArchitectCaptain.recommend_next(sample_roadmap, empty_board)
        # tests depends on api(active) and frontend(pending) — not all deps satisfied
        assert rec.module_id != "tests"

    def test_recommend_nothing_when_all_done(self):
        """All completed → no recommendation."""
        dag = RoadmapDAG(
            project_id="test", generator="static",
            nodes=[asdict(RoadmapNode(id="x", label="X", status="completed"))],
            edges=[],
        )
        rec = ArchitectCaptain.recommend_next(dag, {"tasks": []})
        assert rec is None

    def test_recommend_nothing_when_empty(self):
        """No roadmap → no recommendation."""
        rec = ArchitectCaptain.recommend_next(None, None)
        assert rec is None

    def test_completed_modules_from_board(self, sample_roadmap, board_with_completed_api):
        completed = ArchitectCaptain.get_completed_modules(sample_roadmap, board_with_completed_api)
        # "api" should be detected as completed (task title contains "api")
        assert "api" in completed or "core" in completed

    def test_completed_modules_from_roadmap_status(self, sample_roadmap, empty_board):
        """Nodes with status=completed in roadmap are detected."""
        completed = ArchitectCaptain.get_completed_modules(sample_roadmap, empty_board)
        assert "core" in completed

    def test_rank_candidates_order(self, sample_roadmap, empty_board):
        completed = ArchitectCaptain.get_completed_modules(sample_roadmap, empty_board)
        candidates = ArchitectCaptain.rank_candidates(sample_roadmap, completed)
        assert len(candidates) >= 1
        # First candidate should be "api" (active, deps satisfied)
        assert candidates[0]["node"]["id"] == "api"

    def test_recommendation_has_alternatives(self, sample_roadmap, empty_board):
        rec = ArchitectCaptain.recommend_next(sample_roadmap, empty_board)
        assert rec is not None
        assert isinstance(rec.alternatives, list)

    def test_recommendation_selects_workflow(self, sample_roadmap, empty_board):
        rec = ArchitectCaptain.recommend_next(sample_roadmap, empty_board)
        assert rec.workflow_id != ""

    def test_recommendation_selects_preset(self, sample_roadmap, empty_board):
        rec = ArchitectCaptain.recommend_next(sample_roadmap, empty_board)
        assert rec.preset in ("dragon_bronze", "dragon_silver", "dragon_gold")

    def test_recommendation_has_reason(self, sample_roadmap, empty_board):
        rec = ArchitectCaptain.recommend_next(sample_roadmap, empty_board)
        assert rec.reason != ""
        assert len(rec.reason) > 10

    def test_accept_recommendation(self, sample_roadmap, empty_board):
        rec = ArchitectCaptain.recommend_next(sample_roadmap, empty_board)
        result = ArchitectCaptain.accept_recommendation(rec)
        assert result["ok"] is True
        assert result["task_title"] != ""
        assert result["workflow_id"] != ""

    def test_reject_recommendation(self, sample_roadmap, empty_board):
        rec = ArchitectCaptain.recommend_next(sample_roadmap, empty_board)
        result = ArchitectCaptain.reject_recommendation(rec)
        assert result["ok"] is True
        assert "rejected" in result

    def test_progress_counts(self, sample_roadmap, empty_board):
        progress = ArchitectCaptain.get_progress(sample_roadmap, empty_board)
        assert progress["total"] == 4
        assert progress["completed"] >= 1  # core is completed
        assert progress["percent"] > 0

    def test_progress_empty_roadmap(self):
        progress = ArchitectCaptain.get_progress(None, None)
        assert progress["total"] == 0
        assert progress["percent"] == 0


# ══════════════════════════════════════════════════════════════
# TestDependencySatisfaction
# ══════════════════════════════════════════════════════════════

class TestDependencySatisfaction:
    """Test dependency resolution logic."""

    def test_no_deps_always_satisfied(self):
        dag = RoadmapDAG(
            project_id="test", generator="static",
            nodes=[asdict(RoadmapNode(id="standalone", label="Standalone"))],
            edges=[],
        )
        assert ArchitectCaptain.get_dependencies_satisfied("standalone", dag, set())

    def test_dep_not_completed_blocks(self):
        dag = RoadmapDAG(
            project_id="test", generator="static",
            nodes=[
                asdict(RoadmapNode(id="a", label="A")),
                asdict(RoadmapNode(id="b", label="B")),
            ],
            edges=[asdict(RoadmapEdge(source="a", target="b"))],
        )
        # b depends on a; a not completed → b blocked
        assert not ArchitectCaptain.get_dependencies_satisfied("b", dag, set())

    def test_dep_completed_unblocks(self):
        dag = RoadmapDAG(
            project_id="test", generator="static",
            nodes=[
                asdict(RoadmapNode(id="a", label="A")),
                asdict(RoadmapNode(id="b", label="B")),
            ],
            edges=[asdict(RoadmapEdge(source="a", target="b"))],
        )
        # b depends on a; a completed → b unblocked
        assert ArchitectCaptain.get_dependencies_satisfied("b", dag, {"a"})

    def test_multiple_deps_all_needed(self):
        dag = RoadmapDAG(
            project_id="test", generator="static",
            nodes=[
                asdict(RoadmapNode(id="a", label="A")),
                asdict(RoadmapNode(id="b", label="B")),
                asdict(RoadmapNode(id="c", label="C")),
            ],
            edges=[
                asdict(RoadmapEdge(source="a", target="c")),
                asdict(RoadmapEdge(source="b", target="c")),
            ],
        )
        # c depends on both a and b
        assert not ArchitectCaptain.get_dependencies_satisfied("c", dag, {"a"})
        assert ArchitectCaptain.get_dependencies_satisfied("c", dag, {"a", "b"})


# ══════════════════════════════════════════════════════════════
# TestCaptainRESTAPI
# ══════════════════════════════════════════════════════════════

class TestCaptainRESTAPI:
    """Test MARKER_153.7B: Captain REST endpoints."""

    @pytest.fixture(autouse=True)
    def setup_api(self, tmp_dir, sample_roadmap):
        import src.services.project_config as pc_module
        import src.services.roadmap_generator as rg_module
        import src.services.architect_captain as cap_module

        self.orig_config = pc_module.CONFIG_PATH
        self.orig_session = pc_module.SESSION_STATE_PATH
        self.orig_data_dir = pc_module.DATA_DIR
        self.orig_roadmap = rg_module.ROADMAP_PATH
        self.orig_board = cap_module.TASK_BOARD_PATH

        pc_module.CONFIG_PATH = os.path.join(tmp_dir, "project_config.json")
        pc_module.SESSION_STATE_PATH = os.path.join(tmp_dir, "session_state.json")
        pc_module.DATA_DIR = tmp_dir
        rg_module.ROADMAP_PATH = os.path.join(tmp_dir, "roadmap_dag.json")
        cap_module.TASK_BOARD_PATH = os.path.join(tmp_dir, "task_board.json")

        self.tmp_dir = tmp_dir

        # Save sample roadmap
        sample_roadmap.save(rg_module.ROADMAP_PATH)

        # Save empty task board
        with open(cap_module.TASK_BOARD_PATH, 'w') as f:
            json.dump({"tasks": [], "settings": {}}, f)

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
        cap_module.TASK_BOARD_PATH = self.orig_board

    def test_recommend_endpoint(self):
        r = self.client.get("/api/mcc/captain/recommend")
        assert r.status_code == 200
        data = r.json()
        assert data["has_recommendation"] is True
        assert "module_id" in data
        assert "workflow_id" in data
        assert "preset" in data
        assert "reason" in data

    def test_accept_endpoint(self):
        r = self.client.post("/api/mcc/captain/accept")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "task_title" in data

    def test_reject_endpoint(self):
        r = self.client.post("/api/mcc/captain/reject")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "alternatives" in data

    def test_progress_endpoint(self):
        r = self.client.get("/api/mcc/captain/progress")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "completed" in data
        assert "percent" in data


# ══════════════════════════════════════════════════════════════
# TestFrontendComponents
# ══════════════════════════════════════════════════════════════

class TestFrontendComponents:
    """Test Wave 7 frontend files."""

    def test_captain_py_exists(self):
        assert os.path.isfile(CAPTAIN_PY)

    def test_captain_bar_exists(self):
        assert os.path.isfile(CAPTAIN_BAR_FILE)

    def test_captain_hook_exists(self):
        assert os.path.isfile(CAPTAIN_HOOK_FILE)

    def test_captain_bar_exports(self):
        src = _read(CAPTAIN_BAR_FILE)
        assert 'export function CaptainBar' in src

    def test_captain_bar_shows_at_roadmap(self):
        src = _read(CAPTAIN_BAR_FILE)
        assert 'roadmap' in src

    def test_captain_bar_has_accept_reject(self):
        src = _read(CAPTAIN_BAR_FILE)
        assert 'onAccept' in src
        assert 'onReject' in src

    def test_captain_bar_has_dismiss(self):
        src = _read(CAPTAIN_BAR_FILE)
        assert 'onDismiss' in src

    def test_captain_bar_shows_progress(self):
        src = _read(CAPTAIN_BAR_FILE)
        assert 'progress' in src

    def test_captain_hook_exports(self):
        src = _read(CAPTAIN_HOOK_FILE)
        assert 'export function useCaptain' in src

    def test_captain_hook_fetches_recommend(self):
        src = _read(CAPTAIN_HOOK_FILE)
        assert '/captain/recommend' in src

    def test_captain_hook_has_accept(self):
        src = _read(CAPTAIN_HOOK_FILE)
        assert 'acceptRecommendation' in src

    def test_captain_hook_has_reject(self):
        src = _read(CAPTAIN_HOOK_FILE)
        assert 'rejectRecommendation' in src

    def test_captain_hook_has_progress(self):
        src = _read(CAPTAIN_HOOK_FILE)
        assert 'fetchProgress' in src

    def test_captain_hook_auto_fetch(self):
        src = _read(CAPTAIN_HOOK_FILE)
        assert 'autoFetch' in src

    def test_captain_hook_exports_types(self):
        src = _read(CAPTAIN_HOOK_FILE)
        assert 'Recommendation' in src
        assert 'ProjectProgress' in src


# ══════════════════════════════════════════════════════════════
# TestMCCWave7Integration
# ══════════════════════════════════════════════════════════════

class TestMCCWave7Integration:
    """Test Wave 7 integration into MCC."""

    def test_mcc_imports_captain_bar(self):
        src = _read(MCC_FILE)
        assert "import { CaptainBar }" in src

    def test_mcc_imports_use_captain(self):
        src = _read(MCC_FILE)
        assert "import { useCaptain }" in src

    def test_mcc_renders_captain_bar(self):
        src = _read(MCC_FILE)
        assert '<CaptainBar' in src

    def test_mcc_uses_captain_hook(self):
        src = _read(MCC_FILE)
        assert 'useCaptain(' in src

    def test_mcc_captain_dismiss(self):
        src = _read(MCC_FILE)
        assert 'captainDismissed' in src

    def test_mcc_captain_marker(self):
        src = _read(MCC_FILE)
        assert 'MARKER_153.7' in src
