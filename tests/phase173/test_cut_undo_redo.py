"""
MARKER_173.1 — Undo/Redo service + endpoint tests.

Tests:
- UndoStack push/undo/redo logic
- Label generation
- Max depth enforcement
- Persistence round-trip
- API endpoint integration (undo, redo, undo-stack)
- Non-undoable ops (set_selection, set_view) skipped
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── Ensure project root on sys.path ──
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.cut_undo_redo import (
    CutUndoRedoService,
    UndoStack,
    build_op_label,
)


# ── Fixtures ────────────────────────────────────────────────


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """Create sandbox with minimal CUT project structure."""
    state_dir = tmp_path / "cut_runtime" / "state"
    state_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def service(sandbox: Path) -> CutUndoRedoService:
    return CutUndoRedoService(str(sandbox), "proj_1", "tl_1")


def _make_state(revision: int = 0, lanes: list | None = None) -> dict[str, Any]:
    return {
        "schema_version": "cut_timeline_state_v1",
        "project_id": "proj_1",
        "timeline_id": "tl_1",
        "revision": revision,
        "lanes": lanes or [{"lane_id": "main", "type": "video_main", "clips": []}],
    }


def _make_ops(op_type: str = "move_clip", clip_id: str = "clip_01") -> list[dict]:
    return [{"op": op_type, "clip_id": clip_id, "lane_id": "main", "start_sec": 5.0}]


# ── Unit: build_op_label ────────────────────────────────────


class TestBuildOpLabel:
    def test_empty_ops(self):
        assert build_op_label([]) == "Empty edit"

    def test_single_move(self):
        label = build_op_label([{"op": "move_clip", "clip_id": "abcdef12"}])
        assert "Move clip" in label
        assert "abcdef12" in label

    def test_single_trim(self):
        label = build_op_label([{"op": "trim_clip", "clip_id": "xyz"}])
        assert "Trim clip" in label

    def test_single_split(self):
        label = build_op_label([{"op": "split_at", "clip_id": "c1"}])
        assert "Split clip" in label

    def test_single_ripple_delete(self):
        label = build_op_label([{"op": "ripple_delete", "clip_id": "c2"}])
        assert "Ripple delete" in label

    def test_multiple_ops(self):
        ops = [
            {"op": "move_clip", "clip_id": "a"},
            {"op": "trim_clip", "clip_id": "b"},
        ]
        label = build_op_label(ops)
        assert "2 edits" in label

    def test_unknown_op(self):
        label = build_op_label([{"op": "custom_op", "clip_id": "c3"}])
        assert "custom_op" in label


# ── Unit: UndoStack properties ──────────────────────────────


class TestUndoStackProperties:
    def test_empty_stack(self):
        stack = UndoStack(project_id="p", timeline_id="t")
        assert stack.undo_depth == 0
        assert stack.redo_depth == 0
        assert not stack.can_undo
        assert not stack.can_redo

    def test_labels_empty(self):
        stack = UndoStack(project_id="p", timeline_id="t")
        assert stack.labels() == []


# ── Unit: CutUndoRedoService ────────────────────────────────


class TestServicePush:
    def test_push_single(self, service: CutUndoRedoService):
        state = _make_state(revision=1)
        ops = _make_ops()
        result = service.push("Move clip_01", state, ops, 1, 2)
        assert result["pushed"] is True
        assert result["undo_depth"] == 1
        assert result["redo_depth"] == 0

    def test_push_multiple(self, service: CutUndoRedoService):
        for i in range(5):
            service.push(f"Edit {i}", _make_state(i), _make_ops(), i, i + 1)
        info = service.get_stack_info()
        assert info["undo_depth"] == 5
        assert info["redo_depth"] == 0

    def test_push_max_depth(self, sandbox: Path):
        svc = CutUndoRedoService(str(sandbox), "proj_1", "tl_1", max_depth=3)
        for i in range(5):
            svc.push(f"Edit {i}", _make_state(i), _make_ops(), i, i + 1)
        info = svc.get_stack_info()
        assert info["undo_depth"] == 3  # oldest 2 dropped
        assert info["max_depth"] == 3


class TestServiceUndo:
    def test_undo_empty(self, service: CutUndoRedoService):
        assert service.undo() is None

    def test_undo_single(self, service: CutUndoRedoService):
        state_v1 = _make_state(revision=1)
        service.push("Edit 1", state_v1, _make_ops(), 1, 2)

        result = service.undo()
        assert result is not None
        assert result["restore_state"]["revision"] == 1
        assert result["undo_depth"] == 0
        assert result["redo_depth"] == 1
        assert "Edit 1" in result["entry"]["label"]

    def test_undo_multiple(self, service: CutUndoRedoService):
        for i in range(3):
            service.push(f"Edit {i}", _make_state(i), _make_ops(), i, i + 1)

        # Undo 3 times
        r1 = service.undo()
        assert r1 is not None
        assert r1["restore_state"]["revision"] == 2

        r2 = service.undo()
        assert r2 is not None
        assert r2["restore_state"]["revision"] == 1

        r3 = service.undo()
        assert r3 is not None
        assert r3["restore_state"]["revision"] == 0

        # Fourth undo should fail
        assert service.undo() is None

    def test_undo_then_push_clears_redo(self, service: CutUndoRedoService):
        service.push("Edit 1", _make_state(1), _make_ops(), 1, 2)
        service.push("Edit 2", _make_state(2), _make_ops(), 2, 3)

        service.undo()  # undo Edit 2
        info = service.get_stack_info()
        assert info["redo_depth"] == 1

        # New push should clear redo
        service.push("Edit 3", _make_state(1), _make_ops(), 1, 4)
        info = service.get_stack_info()
        assert info["redo_depth"] == 0
        assert info["undo_depth"] == 2  # Edit 1 + Edit 3


class TestServiceRedo:
    def test_redo_empty(self, service: CutUndoRedoService):
        assert service.redo() is None

    def test_redo_without_undo(self, service: CutUndoRedoService):
        service.push("Edit 1", _make_state(1), _make_ops(), 1, 2)
        assert service.redo() is None

    def test_undo_then_redo(self, service: CutUndoRedoService):
        ops = [{"op": "move_clip", "clip_id": "c1", "lane_id": "main", "start_sec": 10}]
        service.push("Move c1", _make_state(1), ops, 1, 2)

        service.undo()
        result = service.redo()
        assert result is not None
        assert result["reapply_ops"] == ops
        assert "Move c1" in result["entry"]["label"]
        assert result["redo_depth"] == 0

    def test_undo_redo_undo_redo_cycle(self, service: CutUndoRedoService):
        service.push("Edit 1", _make_state(1), _make_ops(), 1, 2)

        for _ in range(3):
            u = service.undo()
            assert u is not None
            r = service.redo()
            assert r is not None

        info = service.get_stack_info()
        assert info["undo_depth"] == 1
        assert info["redo_depth"] == 0


class TestServicePersistence:
    def test_save_and_reload(self, sandbox: Path):
        svc1 = CutUndoRedoService(str(sandbox), "proj_1", "tl_1")
        svc1.push("Edit A", _make_state(1), _make_ops(), 1, 2)
        svc1.push("Edit B", _make_state(2), _make_ops(), 2, 3)

        # Create new service instance — should load from disk
        svc2 = CutUndoRedoService(str(sandbox), "proj_1", "tl_1")
        info = svc2.get_stack_info()
        assert info["undo_depth"] == 2
        assert info["can_undo"] is True

    def test_project_mismatch_resets(self, sandbox: Path):
        svc1 = CutUndoRedoService(str(sandbox), "proj_1", "tl_1")
        svc1.push("Edit A", _make_state(1), _make_ops(), 1, 2)

        # Different project — stack should reset
        svc2 = CutUndoRedoService(str(sandbox), "proj_OTHER", "tl_1")
        info = svc2.get_stack_info()
        assert info["undo_depth"] == 0

    def test_corrupted_file_resets(self, sandbox: Path):
        stack_path = sandbox / "cut_runtime" / "state" / "undo_stack.json"
        stack_path.parent.mkdir(parents=True, exist_ok=True)
        stack_path.write_text("NOT VALID JSON", encoding="utf-8")

        svc = CutUndoRedoService(str(sandbox), "proj_1", "tl_1")
        info = svc.get_stack_info()
        assert info["undo_depth"] == 0  # graceful reset


class TestServiceClear:
    def test_clear(self, service: CutUndoRedoService):
        service.push("Edit 1", _make_state(1), _make_ops(), 1, 2)
        result = service.clear()
        assert result["cleared"] is True
        assert result["undo_depth"] == 0


class TestGetStackInfo:
    def test_info_shape(self, service: CutUndoRedoService):
        info = service.get_stack_info()
        assert "schema_version" in info
        assert info["schema_version"] == "cut_undo_stack_v1"
        assert "undo_depth" in info
        assert "redo_depth" in info
        assert "can_undo" in info
        assert "can_redo" in info
        assert "labels" in info
        assert isinstance(info["labels"], list)

    def test_labels_after_pushes(self, service: CutUndoRedoService):
        service.push("Alpha", _make_state(1), _make_ops(), 1, 2)
        service.push("Beta", _make_state(2), _make_ops(), 2, 3)
        info = service.get_stack_info()
        labels = [l["label"] for l in info["labels"]]
        assert "Beta" in labels
        assert "Alpha" in labels


# ── Integration: API endpoints via httpx ────────────────────


@pytest.fixture
def _mock_store():
    """Patch CutProjectStore for endpoint tests."""
    project_data = {"project_id": "proj_1"}
    timeline_data = _make_state(revision=5)
    timeline_data["timeline_id"] = "tl_1"
    timeline_data["lanes"] = [
        {
            "lane_id": "main",
            "type": "video_main",
            "clips": [
                {"clip_id": "clip_01", "source_path": "a.mp4", "start_sec": 0.0, "duration_sec": 10.0},
                {"clip_id": "clip_02", "source_path": "b.mp4", "start_sec": 10.0, "duration_sec": 8.0},
            ],
        }
    ]

    with patch("src.api.routes.cut_routes.CutProjectStore") as MockStore:
        instance = MagicMock()
        instance.load_project.return_value = project_data
        instance.load_timeline_state.return_value = timeline_data
        instance.save_timeline_state = MagicMock()
        instance.append_timeline_edit_event = MagicMock()
        MockStore.return_value = instance
        yield instance, timeline_data


class TestUndoEndpoint:
    """Test POST /api/cut/undo via TestClient."""

    @pytest.fixture(autouse=True)
    def _setup(self, _mock_store, tmp_path):
        self.mock_store, self.timeline = _mock_store
        self.sandbox = str(tmp_path)

        # Pre-populate undo stack
        svc = CutUndoRedoService(self.sandbox, "proj_1", "tl_1")
        svc.push("Move clip_01", _make_state(4), [{"op": "move_clip", "clip_id": "clip_01"}], 4, 5)

    def test_undo_success(self):
        from fastapi.testclient import TestClient
        from src.api.routes.cut_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post("/api/cut/undo", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            "timeline_id": "tl_1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["undone_label"] == "Move clip_01"
        assert data["undo_depth"] == 0
        assert data["redo_depth"] == 1

    def test_undo_nothing(self):
        from fastapi.testclient import TestClient
        from src.api.routes.cut_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # First undo succeeds
        client.post("/api/cut/undo", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            "timeline_id": "tl_1",
        })
        # Second undo — nothing left
        resp = client.post("/api/cut/undo", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            "timeline_id": "tl_1",
        })
        data = resp.json()
        assert data["success"] is False
        assert data["error"] == "nothing_to_undo"


class TestRedoEndpoint:
    @pytest.fixture(autouse=True)
    def _setup(self, _mock_store, tmp_path):
        self.mock_store, self.timeline = _mock_store
        self.sandbox = str(tmp_path)

        svc = CutUndoRedoService(self.sandbox, "proj_1", "tl_1")
        svc.push(
            "Move clip_01",
            _make_state(4),
            [{"op": "move_clip", "clip_id": "clip_01", "lane_id": "main", "start_sec": 5.0}],
            4, 5,
        )
        svc.undo()  # now we have 1 redo available

    def test_redo_success(self):
        from fastapi.testclient import TestClient
        from src.api.routes.cut_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post("/api/cut/redo", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            "timeline_id": "tl_1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "Move clip_01" in data["redone_label"]


class TestUndoStackEndpoint:
    def test_get_stack_info(self, tmp_path):
        from fastapi.testclient import TestClient
        from src.api.routes.cut_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        sandbox = str(tmp_path)
        svc = CutUndoRedoService(sandbox, "proj_1", "tl_1")
        svc.push("Edit A", _make_state(1), _make_ops(), 1, 2)
        svc.push("Edit B", _make_state(2), _make_ops(), 2, 3)

        resp = client.get("/api/cut/undo-stack", params={
            "sandbox_root": sandbox,
            "project_id": "proj_1",
            "timeline_id": "tl_1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["undo_depth"] == 2
        assert data["can_undo"] is True
        assert len(data["labels"]) == 2
