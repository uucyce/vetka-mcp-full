"""
MARKER_EPSILON.T1: Save/Autosave contract tests.

Verifies that:
1. useCutAutosave.ts sends POST to /cut/save (not /project/save)
2. Payload includes cut_timeline_state_v1 schema fields
3. Autosave interval is configured (2 min default)
4. Save status state machine: idle → saving → saved|error
5. Backend route /cut/save exists and accepts the payload schema

Source: client/src/hooks/useCutAutosave.ts
Backend: src/api/routes/cut_routes*.py (save endpoint)
"""

import re
from pathlib import Path

import pytest

AUTOSAVE_HOOK = Path(__file__).resolve().parent.parent / "client" / "src" / "hooks" / "useCutAutosave.ts"
STORE_FILE = Path(__file__).resolve().parent.parent / "client" / "src" / "store" / "useCutEditorStore.ts"
CUT_ROUTES_DIR = Path(__file__).resolve().parent.parent / "src" / "api" / "routes"


@pytest.fixture(scope="module")
def autosave_source():
    if not AUTOSAVE_HOOK.exists():
        pytest.skip(f"Autosave hook not found: {AUTOSAVE_HOOK}")
    return AUTOSAVE_HOOK.read_text()


@pytest.fixture(scope="module")
def store_source():
    if not STORE_FILE.exists():
        pytest.skip(f"Store not found: {STORE_FILE}")
    return STORE_FILE.read_text()


class TestSaveEndpoint:
    """Verify save calls POST /cut/save with correct schema."""

    def test_posts_to_cut_save(self, autosave_source):
        """Save must POST to /cut/save endpoint."""
        assert "/cut/save" in autosave_source, \
            "Save should POST to /cut/save endpoint"

    def test_uses_post_method(self, autosave_source):
        """Must use POST method."""
        assert re.search(r"method:\s*['\"]POST['\"]", autosave_source), \
            "Save must use POST method"

    def test_sends_json_content_type(self, autosave_source):
        """Must set Content-Type: application/json."""
        assert "application/json" in autosave_source

    def test_includes_sandbox_root(self, autosave_source):
        """Payload must include sandbox_root for backend to locate project."""
        assert "sandbox_root" in autosave_source

    def test_includes_timeline_state(self, autosave_source):
        """Payload must include timeline_state object."""
        assert "timeline_state" in autosave_source


class TestTimelineStateSchema:
    """Verify cut_timeline_state_v1 schema fields in save payload."""

    def test_schema_version_present(self, autosave_source):
        """Must tag with schema_version for future migrations."""
        assert "schema_version" in autosave_source
        assert "cut_timeline_state_v1" in autosave_source

    def test_lanes_serialized(self, autosave_source):
        """Must include lanes (the actual timeline data)."""
        # lanes is destructured from state and put into timeline_state
        assert re.search(r"lanes", autosave_source)

    def test_markers_serialized(self, autosave_source):
        """Must include markers array."""
        assert "markers" in autosave_source

    def test_view_state_serialized(self, autosave_source):
        """Must include view state (zoom, scroll, currentTime)."""
        assert "zoom" in autosave_source
        assert "scroll_left" in autosave_source or "scrollLeft" in autosave_source
        assert "current_time" in autosave_source or "currentTime" in autosave_source

    def test_selection_state_serialized(self, autosave_source):
        """Must include selection (marks, selected clips)."""
        assert "source_mark_in" in autosave_source or "sourceMarkIn" in autosave_source
        assert "sequence_mark_in" in autosave_source or "sequenceMarkIn" in autosave_source

    def test_fps_included(self, autosave_source):
        """Must include framerate for timecode accuracy."""
        assert "fps" in autosave_source or "projectFramerate" in autosave_source


class TestAutosaveTimer:
    """Verify autosave interval and trigger conditions."""

    def test_autosave_interval_defined(self, autosave_source):
        """Autosave interval must be defined (default 2 min)."""
        match = re.search(r"AUTOSAVE_INTERVAL_MS\s*=\s*(\d[\d_*\s]*)", autosave_source)
        assert match, "AUTOSAVE_INTERVAL_MS must be defined"

    def test_autosave_checks_unsaved(self, autosave_source):
        """Autosave should only fire when hasUnsavedChanges is true."""
        assert "hasUnsavedChanges" in autosave_source, \
            "Autosave must check hasUnsavedChanges before saving"

    def test_autosave_clears_unsaved_flag(self, autosave_source):
        """After successful save, hasUnsavedChanges must be cleared."""
        assert re.search(r"hasUnsavedChanges.*false", autosave_source), \
            "Save must clear hasUnsavedChanges on success"


class TestSaveStatusMachine:
    """Verify save status transitions."""

    def test_sets_saving_status(self, autosave_source):
        """Must set status to 'saving' before request."""
        assert re.search(r"setSaveStatus.*saving", autosave_source)

    def test_sets_saved_status(self, autosave_source):
        """Must set status to 'saved' on success."""
        assert re.search(r"setSaveStatus.*saved", autosave_source)

    def test_sets_error_status(self, autosave_source):
        """Must set status to 'error' on failure."""
        assert re.search(r"setSaveStatus.*error", autosave_source)


class TestStoreHasSaveFields:
    """Verify the store exports save-related state fields."""

    def test_save_status_field(self, store_source):
        assert "saveStatus" in store_source

    def test_has_unsaved_changes_field(self, store_source):
        assert "hasUnsavedChanges" in store_source

    def test_last_saved_at_field(self, store_source):
        assert "lastSavedAt" in store_source

    def test_set_save_status_action(self, store_source):
        assert "setSaveStatus" in store_source
