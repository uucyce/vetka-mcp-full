"""
MARKER_175B: Workflow Family Selection — backend tests.

Tests:
- PATCH /api/mcc/tasks/{id} with workflow_family field
- ArchitectPrefetch.prepare() respects user-selected workflow_family
- WorkflowTemplateLibrary list/family operations
- Real-task descriptions from Phase 154/155 roadmaps for heuristic validation

@phase 175
@status active
"""

import json
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def board(tmp_path, monkeypatch):
    import src.orchestration.task_board as task_board_module

    board = task_board_module.TaskBoard(board_file=tmp_path / "task_board.json")
    monkeypatch.setattr(task_board_module, "get_task_board", lambda: board)
    return board


@pytest.fixture
def client(board):
    from src.api.routes.mcc_routes import router as mcc_router

    app = FastAPI()
    app.include_router(mcc_router)
    return TestClient(app)


def _seed_task(board, **overrides):
    task_id = board.add_task(
        title=overrides.pop("title", "Test workflow task"),
        description=overrides.pop("description", "Implement workflow selection"),
        priority=overrides.pop("priority", 3),
        phase_type=overrides.pop("phase_type", "build"),
        preset=overrides.pop("preset", "dragon_silver"),
        tags=overrides.pop("tags", ["phase175b"]),
    )
    if overrides:
        assert board.update_task(task_id, **overrides)
    return task_id


# --- T1: PATCH with workflow_family succeeds ---

def test_patch_task_with_workflow_family(client, board):
    """PATCH /api/mcc/tasks/{id} accepts workflow_family field."""
    task_id = _seed_task(board)

    response = client.patch(
        f"/api/mcc/tasks/{task_id}",
        json={"workflow_family": "ralph_loop"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    task = data["task"]
    assert task["workflow_family"] == "ralph_loop"


def test_patch_task_workflow_family_with_other_fields(client, board):
    """PATCH with workflow_family alongside other fields."""
    task_id = _seed_task(board)

    response = client.patch(
        f"/api/mcc/tasks/{task_id}",
        json={
            "description": "Updated with workflow",
            "preset": "dragon_gold",
            "workflow_family": "g3_critic_coder",
        },
    )

    assert response.status_code == 200
    task = response.json()["task"]
    assert task["workflow_family"] == "g3_critic_coder"
    assert task["preset"] == "dragon_gold"
    assert task["description"] == "Updated with workflow"


# --- T2: Invalid fields still rejected ---

def test_patch_task_rejects_invalid_field_with_workflow(client, board):
    """PATCH with only unknown fields still returns 400."""
    task_id = _seed_task(board)

    response = client.patch(
        f"/api/mcc/tasks/{task_id}",
        json={"unknown_field": "nope"},
    )

    assert response.status_code == 400


# --- T3: architect_prefetch uses task.workflow_family when set ---

def test_prefetch_uses_explicit_workflow_family(tmp_path, monkeypatch):
    """ArchitectPrefetch.prepare() uses workflow_family when it's a valid template key."""
    from src.services.architect_prefetch import ArchitectPrefetch, WorkflowTemplateLibrary

    # Ensure templates are loaded
    WorkflowTemplateLibrary.load_all()

    ctx = ArchitectPrefetch.prepare(
        task_description="Implement dark mode toggle",
        task_type="build",
        complexity=5,
        workflow_family="ralph_loop",
    )

    assert ctx.workflow_id == "ralph_loop"
    assert "ralph" in ctx.workflow_name.lower() or ctx.workflow_name == "ralph_loop"
    # No reinforcement when user explicitly selects
    assert ctx.workflow_reinforcement == []


# --- T4: Fallback to heuristic when workflow_family is empty ---

def test_prefetch_falls_back_to_heuristic_when_empty(tmp_path, monkeypatch):
    """ArchitectPrefetch.prepare() uses heuristic when workflow_family is empty."""
    from src.services.architect_prefetch import ArchitectPrefetch, WorkflowTemplateLibrary

    WorkflowTemplateLibrary.load_all()

    ctx = ArchitectPrefetch.prepare(
        task_description="Fix authentication bug in login form",
        task_type="fix",
        complexity=2,
        workflow_family="",
    )

    # Heuristic should pick quick_fix for fix + low complexity
    assert ctx.workflow_id == "quick_fix"


# --- T5: Fallback to heuristic when workflow_family is invalid ---

def test_prefetch_falls_back_when_invalid_template(tmp_path, monkeypatch):
    """ArchitectPrefetch.prepare() falls back when workflow_family is invalid key."""
    from src.services.architect_prefetch import ArchitectPrefetch, WorkflowTemplateLibrary

    WorkflowTemplateLibrary.load_all()

    ctx = ArchitectPrefetch.prepare(
        task_description="Build user dashboard",
        task_type="build",
        complexity=5,
        workflow_family="nonexistent_workflow_xyz",
    )

    # Should fall back to heuristic (not crash)
    assert ctx.workflow_id != "nonexistent_workflow_xyz"
    assert ctx.workflow_id != ""


# --- T6: list_templates returns all templates ---

def test_list_templates_returns_all(tmp_path):
    """WorkflowTemplateLibrary.list_templates() returns all available templates."""
    from src.services.architect_prefetch import WorkflowTemplateLibrary

    WorkflowTemplateLibrary._loaded = False
    templates = WorkflowTemplateLibrary.list_templates()

    assert len(templates) >= 8  # At least 8 non-stub templates
    keys = [t["key"] for t in templates]
    assert "bmad_default" in keys
    assert "ralph_loop" in keys
    assert "g3_critic_coder" in keys
    assert "quick_fix" in keys
    assert "research_first" in keys


# --- T7: list_families groups correctly ---

def test_list_families_groups_templates():
    """WorkflowTemplateLibrary.list_families() groups templates by family."""
    from src.services.architect_prefetch import WorkflowTemplateLibrary

    WorkflowTemplateLibrary._loaded = False
    families = WorkflowTemplateLibrary.list_families()

    assert len(families) > 0
    for fam in families:
        assert "family" in fam
        assert "templates" in fam
        assert isinstance(fam["templates"], list)
        assert len(fam["templates"]) > 0


# --- Real-task tests: descriptions from Phase 154/155 roadmaps ---

def test_real_task_reflex_toggle_selects_quick_fix():
    """Real task: 'Add showReflexInsight toggle' → quick_fix (fix, complexity 2)."""
    from src.services.architect_prefetch import WorkflowTemplateLibrary

    WorkflowTemplateLibrary._loaded = False
    WorkflowTemplateLibrary.load_all()

    result = WorkflowTemplateLibrary.select_workflow(
        task_type="fix",
        complexity=2,
        task_description="Add showReflexInsight toggle to useStore.ts",
    )

    assert result == "quick_fix"


def test_real_task_playwright_tests_selects_test_only():
    """Real task: 'Playwright E2E tests for Phase 154' → test_only."""
    from src.services.architect_prefetch import WorkflowTemplateLibrary

    WorkflowTemplateLibrary._loaded = False
    WorkflowTemplateLibrary.load_all()

    result = WorkflowTemplateLibrary.select_workflow(
        task_type="test",
        complexity=4,
        task_description="Implement Playwright E2E tests for Phase 154 Matryoshka navigation",
    )

    assert result == "test_only"


def test_real_task_qdrant_persistence_selects_research():
    """Real task: 'Qdrant fallback persistence' → research_first (build + learn)."""
    from src.services.architect_prefetch import WorkflowTemplateLibrary

    WorkflowTemplateLibrary._loaded = False
    WorkflowTemplateLibrary.load_all()

    result = WorkflowTemplateLibrary.select_workflow(
        task_type="build",
        complexity=6,
        task_description="Add Qdrant fallback persistence for MiniWindow positions with learn strategy",
    )

    # 'build' task_type + 'learn' in description → research_first
    assert result == "research_first"


def test_real_task_refactor_captainbar():
    """Real task: 'Refactor CaptainBar' → refactor."""
    from src.services.architect_prefetch import WorkflowTemplateLibrary

    WorkflowTemplateLibrary._loaded = False
    WorkflowTemplateLibrary.load_all()

    result = WorkflowTemplateLibrary.select_workflow(
        task_type="refactor",
        complexity=3,
        task_description="Refactor CaptainBar conditional rendering to use level config",
    )

    assert result == "refactor"


# --- End-to-end: explicit workflow_family bypasses all heuristics ---

def test_explicit_workflow_overrides_heuristic_for_any_task():
    """When user selects g3_critic_coder, it should be used regardless of task_type."""
    from src.services.architect_prefetch import ArchitectPrefetch, WorkflowTemplateLibrary

    WorkflowTemplateLibrary._loaded = False
    WorkflowTemplateLibrary.load_all()

    # Even though task_type=fix + complexity=1 would normally select quick_fix,
    # explicit workflow_family should override
    ctx = ArchitectPrefetch.prepare(
        task_description="Fix typo in readme",
        task_type="fix",
        complexity=1,
        workflow_family="g3_critic_coder",
    )

    assert ctx.workflow_id == "g3_critic_coder"
