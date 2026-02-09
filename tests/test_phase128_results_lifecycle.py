"""
Phase 128: Results Viewer + Apply + Lifecycle Tests

Tests for:
- MARKER_128.2B: Apply endpoint
- MARKER_128.2C: Apply button in TaskCard
- MARKER_128.3A: Result status endpoint
- MARKER_128.3B/C: TaskCard badges and lifecycle buttons
"""

import os
import pytest


def _read_source(path: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, path), "r") as f:
        return f.read()


class TestPhase128_2_ApplyEndpoint:
    """Tests for MARKER_128.2B: Apply endpoint."""

    def test_marker_128_2b_in_debug_routes(self):
        """MARKER_128.2B should be in debug_routes.py."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "MARKER_128.2B" in source

    def test_apply_endpoint_exists(self):
        """POST /pipeline-results/apply endpoint should exist."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert '@router.post("/pipeline-results/apply")' in source
        assert "async def apply_pipeline_result" in source

    def test_apply_extracts_file_path(self):
        """Apply endpoint should extract file path from code comments."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "// file:" in source or "file:" in source
        assert "files_written" in source

    def test_apply_writes_to_disk(self):
        """Apply endpoint should write files to disk."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "write_text" in source
        assert "mkdir" in source


class TestPhase128_2C_ApplyButton:
    """Tests for MARKER_128.2C: Apply button in TaskCard."""

    def test_marker_128_2c_in_taskcard(self):
        """MARKER_128.2C should be in TaskCard.tsx."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert "MARKER_128.2C" in source

    def test_apply_button_exists(self):
        """Apply button should exist in TaskCard."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert "apply" in source.lower()
        assert "applySubtask" in source

    def test_apply_state_management(self):
        """Apply should have loading and result state."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert "applyingSubtask" in source
        assert "applyResult" in source


class TestPhase128_3A_StatusEndpoint:
    """Tests for MARKER_128.3A: Result status endpoint."""

    def test_marker_128_3a_in_debug_routes(self):
        """MARKER_128.3A should be in debug_routes.py."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert "MARKER_128.3A" in source

    def test_status_endpoint_exists(self):
        """PATCH /pipeline-results/{task_id}/status endpoint should exist."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert '@router.patch("/pipeline-results/{task_id}/status")' in source
        assert "async def update_result_status" in source

    def test_status_values(self):
        """Status endpoint should accept applied/rejected/rework."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert '"applied"' in source
        assert '"rejected"' in source
        assert '"rework"' in source

    def test_rework_resets_status(self):
        """Rework should reset task status to pending."""
        source = _read_source("src/api/routes/debug_routes.py")
        assert 'status="pending"' in source


class TestPhase128_3B_StatusBadge:
    """Tests for MARKER_128.3B: TaskCard status badge."""

    def test_marker_128_3b_in_taskcard(self):
        """MARKER_128.3B should be in TaskCard.tsx."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert "MARKER_128.3B" in source

    def test_result_status_styles(self):
        """Result status styles should be defined."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert "RESULT_STATUS_STYLE" in source
        assert "applied" in source
        assert "rejected" in source
        assert "rework" in source

    def test_taskdata_has_result_fields(self):
        """TaskData interface should have result lifecycle fields."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert "result_status" in source
        assert "result_reviewed_at" in source


class TestPhase128_3C_LifecycleButtons:
    """Tests for MARKER_128.3C: Lifecycle action buttons."""

    def test_marker_128_3c_in_taskcard(self):
        """MARKER_128.3C should be in TaskCard.tsx."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert "MARKER_128.3C" in source

    def test_update_result_status_function(self):
        """updateResultStatus function should exist."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert "updateResultStatus" in source
        assert "PATCH" in source

    def test_lifecycle_buttons_rendered(self):
        """Applied/Rejected/Rework buttons should be rendered."""
        source = _read_source("client/src/components/panels/TaskCard.tsx")
        assert ">applied<" in source.lower() or "'applied'" in source
        assert ">rejected<" in source.lower() or "'rejected'" in source
        assert ">rework<" in source.lower() or "'rework'" in source
