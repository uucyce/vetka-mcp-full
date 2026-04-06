"""
MARKER_IMPORT-SAVE-FIX: Tests for CutProjectPaths.autosave_timeline_state_path
and CutProjectStore.save_autosave_timeline_state + load.

Bug: CutProjectPaths was missing autosave_timeline_state_path, causing
/api/cut/save (autosave=True) and /api/cut/autosave/check to crash with AttributeError.

[task:tb_1775436833_84818_1]
"""
import json
import os
import tempfile

import pytest

from src.services.cut_project_store import CutProjectPaths, CutProjectStore


class TestCutProjectPathsAutosave:
    """Verify autosave_timeline_state_path property exists and returns correct path."""

    def test_autosave_timeline_state_path_exists(self):
        paths = CutProjectPaths("/tmp/test_sandbox")
        assert hasattr(paths, "autosave_timeline_state_path")

    def test_autosave_timeline_state_path_value(self):
        paths = CutProjectPaths("/tmp/test_sandbox")
        expected = os.path.join("/tmp/test_sandbox", ".autosave", "timeline_state.json")
        assert paths.autosave_timeline_state_path == expected

    def test_autosave_dir_is_parent_of_autosave_timeline(self):
        paths = CutProjectPaths("/tmp/test_sandbox")
        assert paths.autosave_timeline_state_path.startswith(paths.autosave_dir)

    def test_autosave_path_distinct_from_main_timeline(self):
        paths = CutProjectPaths("/tmp/test_sandbox")
        assert paths.autosave_timeline_state_path != paths.timeline_state_path


class TestCutProjectStoreAutosave:
    """Verify save/load autosave timeline state methods."""

    @pytest.fixture
    def sandbox(self, tmp_path):
        sandbox_root = str(tmp_path / "cut_sandbox")
        os.makedirs(sandbox_root)
        # Create config dir with a minimal project file so store works
        config_dir = os.path.join(sandbox_root, "config")
        os.makedirs(config_dir, exist_ok=True)
        project = {"schema_version": "cut_project_v1", "project_id": "test"}
        with open(os.path.join(config_dir, "cut_project.json"), "w") as f:
            json.dump(project, f)
        return sandbox_root

    def test_save_autosave_timeline_state_method_exists(self, sandbox):
        store = CutProjectStore(sandbox)
        assert hasattr(store, "save_autosave_timeline_state")
        assert callable(store.save_autosave_timeline_state)

    def test_load_autosave_timeline_state_method_exists(self, sandbox):
        store = CutProjectStore(sandbox)
        assert hasattr(store, "load_autosave_timeline_state")
        assert callable(store.load_autosave_timeline_state)

    def test_save_creates_autosave_dir(self, sandbox):
        store = CutProjectStore(sandbox)
        autosave_dir = store.paths.autosave_dir
        assert not os.path.exists(autosave_dir)
        store.save_autosave_timeline_state({"schema_version": "cut_timeline_state_v1", "lanes": []})
        assert os.path.isdir(autosave_dir)

    def test_save_writes_json_file(self, sandbox):
        store = CutProjectStore(sandbox)
        state = {"schema_version": "cut_timeline_state_v1", "lanes": [], "markers": []}
        store.save_autosave_timeline_state(state)
        path = store.paths.autosave_timeline_state_path
        assert os.path.isfile(path)
        with open(path) as f:
            saved = json.load(f)
        assert saved["lanes"] == []
        assert saved["markers"] == []

    def test_load_returns_none_when_no_autosave(self, sandbox):
        store = CutProjectStore(sandbox)
        result = store.load_autosave_timeline_state()
        assert result is None

    def test_load_returns_saved_state(self, sandbox):
        store = CutProjectStore(sandbox)
        state = {"schema_version": "cut_timeline_state_v1", "lanes": [{"id": "V1"}], "test_key": "test_val"}
        store.save_autosave_timeline_state(state)
        loaded = store.load_autosave_timeline_state()
        assert loaded is not None
        assert loaded["test_key"] == "test_val"
        assert loaded["lanes"] == [{"id": "V1"}]

    def test_save_autosave_does_not_affect_main_timeline(self, sandbox):
        store = CutProjectStore(sandbox)
        # Save to autosave
        store.save_autosave_timeline_state({"schema_version": "cut_timeline_state_v1", "autosave": True})
        # Main timeline should not exist
        assert not os.path.exists(store.paths.timeline_state_path)

    def test_autosave_overwrite(self, sandbox):
        store = CutProjectStore(sandbox)
        store.save_autosave_timeline_state({"schema_version": "cut_timeline_state_v1", "version": 1})
        store.save_autosave_timeline_state({"schema_version": "cut_timeline_state_v1", "version": 2})
        loaded = store.load_autosave_timeline_state()
        assert loaded is not None
        assert loaded["version"] == 2
