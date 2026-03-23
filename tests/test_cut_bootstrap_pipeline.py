"""
MARKER_EPSILON.BOOTSTRAP: Bootstrap pipeline contract tests.

Verifies the project bootstrap flow:
1. Empty state → import folder → media scan
2. Media probe → clip creation on timeline
3. Waveform generation
4. Project state persistence (save/load)
"""

import re
from pathlib import Path

import pytest

CLIENT = Path(__file__).resolve().parent.parent / "client" / "src"
BACKEND = Path(__file__).resolve().parent.parent / "src"
STORE = CLIENT / "store" / "useCutEditorStore.ts"
ROUTES = BACKEND / "api" / "routes"


@pytest.fixture(scope="module")
def store():
    return STORE.read_text()


class TestBootstrapEndpoints:
    """Backend bootstrap endpoints must exist."""

    def test_bootstrap_route_file(self):
        """At least one cut_routes file with bootstrap."""
        found = False
        for f in ROUTES.glob("cut_routes*.py"):
            if "bootstrap" in f.read_text().lower():
                found = True
                break
        assert found, "No bootstrap endpoint found in cut_routes"

    def test_media_probe_endpoint(self):
        """Media probe endpoint for codec/duration detection."""
        found = False
        for f in ROUTES.glob("cut_routes*.py"):
            content = f.read_text()
            if "probe" in content.lower() and ("ffprobe" in content.lower() or "media_info" in content.lower()):
                found = True
                break
        assert found, "No media probe endpoint found"

    def test_waveform_build_endpoint(self):
        """Waveform extraction endpoint."""
        found = False
        for f in ROUTES.glob("cut_routes*.py"):
            if "waveform" in f.read_text().lower():
                found = True
                break
        assert found, "No waveform build endpoint found"


class TestBootstrapStoreFields:
    """Store fields for bootstrap state tracking."""

    def test_sandbox_root(self, store):
        """sandboxRoot tracks project folder path."""
        assert "sandboxRoot" in store

    def test_project_id(self, store):
        assert "projectId" in store

    def test_lanes_field(self, store):
        """lanes[] holds timeline tracks."""
        assert re.search(r"lanes:\s*TimelineLane\[\]|lanes:\s*\[\]", store)

    def test_set_lanes_action(self, store):
        assert "setLanes" in store

    def test_project_framerate(self, store):
        assert "projectFramerate" in store


class TestBootstrapFlow:
    """Bootstrap creates timeline from imported media."""

    def test_import_media_hotkey(self, store):
        """Cmd+I triggers import."""
        layout = (CLIENT / "components" / "cut" / "CutEditorLayoutV2.tsx").read_text()
        assert "importMedia" in layout
        assert "cut:import-media" in layout

    def test_timeline_lane_types(self, store):
        """Store supports video and audio lane types."""
        assert "video_main" in store or "lane_type" in store

    def test_clip_structure(self, store):
        """TimelineClip has essential fields."""
        assert "clip_id" in store
        assert "source_path" in store
        assert "start_sec" in store
        assert "duration_sec" in store


class TestProjectPersistence:
    """Save and load project state."""

    def test_save_status_field(self, store):
        assert "saveStatus" in store

    def test_has_unsaved_changes(self, store):
        assert "hasUnsavedChanges" in store

    def test_last_saved_at(self, store):
        assert "lastSavedAt" in store

    def test_refresh_project_state(self, store):
        """refreshProjectState reloads from backend."""
        assert "refreshProjectState" in store


class TestBootstrapBackend:
    """Backend bootstrap service."""

    def test_project_store_exists(self):
        ps = BACKEND / "services" / "cut_project_store.py"
        assert ps.exists(), "cut_project_store.py should exist"

    def test_bootstrap_service(self):
        """Bootstrap service or route handler."""
        found = False
        for f in list(ROUTES.glob("cut_routes*.py")) + list((BACKEND / "services").glob("cut_*.py")):
            if "bootstrap" in f.read_text().lower():
                found = True
                break
        assert found

    def test_timeline_state_schema(self):
        """cut_timeline_state_v1 schema for persistence."""
        autosave = CLIENT / "hooks" / "useCutAutosave.ts"
        if autosave.exists():
            assert "cut_timeline_state_v1" in autosave.read_text()
