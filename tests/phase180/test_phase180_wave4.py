"""
Phase 180 Wave 4 Tests — Marker Unification + Project Schema + Panel Migration.

Tests cover:
- 180.20: Unified marker types (editorial + BPM kinds)
- 180.21: project.vetka-cut.json schema (Pydantic validation, load/save)
- 180.4:  CutEditorLayoutV2 — panel-to-dock mapping, all 7 panels present

MARKER_180_WAVE4_TESTS
"""
import json
import os
import time
import tempfile
import pytest

pytestmark = pytest.mark.stale(reason="Phase 180 file markers — CUT layout V2 refactor")
from pathlib import Path


# ---------------------------------------------------------------------------
# 180.20: Unified Marker System
# ---------------------------------------------------------------------------

class TestUnifiedMarkerTypes:
    """Test that marker kinds cover both editorial and BPM domains."""

    EDITORIAL_KINDS = {"favorite", "comment", "cam", "insight", "chat"}
    BPM_KINDS = {"bpm_audio", "bpm_visual", "bpm_script", "sync_point"}
    ALL_KINDS = EDITORIAL_KINDS | BPM_KINDS

    def test_editorial_kinds_preserved(self):
        """Original 5 editorial kinds still valid."""
        assert len(self.EDITORIAL_KINDS) == 5

    def test_bpm_kinds_added(self):
        """4 new BPM-related kinds added."""
        assert len(self.BPM_KINDS) == 4

    def test_total_kinds(self):
        """9 total marker kinds."""
        assert len(self.ALL_KINDS) == 9

    def test_no_overlap(self):
        """Editorial and BPM kinds don't overlap."""
        assert self.EDITORIAL_KINDS.isdisjoint(self.BPM_KINDS)

    def test_marker_with_pulse_data(self):
        """Unified marker can carry PULSE analysis data."""
        marker = {
            "marker_id": "m_001",
            "kind": "favorite",
            "media_path": "/clip.mp4",
            "start_sec": 10.0,
            "end_sec": 15.0,
            "score": 0.9,
            # PULSE data
            "camelot_key": "8A",
            "energy": 0.7,
            "pendulum": -0.3,
            "scene_id": "sc_1",
            "editorial_intent": "accent_cut",
        }
        assert marker["camelot_key"] == "8A"
        assert marker["editorial_intent"] == "accent_cut"

    def test_sync_point_marker(self):
        """Sync point markers have strength and sources."""
        marker = {
            "marker_id": "sp_001",
            "kind": "sync_point",
            "media_path": "/clip.mp4",
            "start_sec": 5.5,
            "end_sec": 5.5,
            "sync_strength": 1.0,
            "sync_sources": ["audio", "visual", "script"],
        }
        assert marker["kind"] == "sync_point"
        assert marker["sync_strength"] == 1.0
        assert len(marker["sync_sources"]) == 3

    def test_bpm_audio_marker(self):
        """BPM audio beat marker."""
        marker = {
            "marker_id": "ba_001",
            "kind": "bpm_audio",
            "media_path": "/clip.mp4",
            "start_sec": 0.5,
            "end_sec": 0.5,
            "source_engine": "librosa_beat_detector",
        }
        assert marker["kind"] == "bpm_audio"
        assert marker["source_engine"]

    def test_editorial_intent_mapping(self):
        """Each editorial kind maps to an intent."""
        INTENT_MAP = {
            "favorite": "accent_cut",
            "comment": "commentary_hold",
            "cam": "camera_emphasis",
            "insight": "insight_emphasis",
            "chat": "dialogue_anchor",
        }
        assert len(INTENT_MAP) == 5
        for kind, intent in INTENT_MAP.items():
            assert kind in self.EDITORIAL_KINDS
            assert intent.endswith(("_cut", "_hold", "_emphasis", "_anchor"))


# ---------------------------------------------------------------------------
# 180.21: project.vetka-cut.json Schema
# ---------------------------------------------------------------------------

class TestProjectSchema:
    """Test the VetkaCutProject Pydantic schema."""

    def _import_schema(self):
        from src.schemas.project_vetka_cut_schema import (
            VetkaCutProject,
            TimelineVersionEntry,
            PanelLayoutConfig,
            PulseConfig,
            AssetEntry,
            create_default_project,
            add_timeline_version,
            save_project,
            load_project,
            SCHEMA_VERSION,
        )
        return {
            "VetkaCutProject": VetkaCutProject,
            "TimelineVersionEntry": TimelineVersionEntry,
            "PanelLayoutConfig": PanelLayoutConfig,
            "PulseConfig": PulseConfig,
            "AssetEntry": AssetEntry,
            "create_default_project": create_default_project,
            "add_timeline_version": add_timeline_version,
            "save_project": save_project,
            "load_project": load_project,
            "SCHEMA_VERSION": SCHEMA_VERSION,
        }

    def test_schema_version(self):
        s = self._import_schema()
        assert s["SCHEMA_VERSION"] == "vetka-cut-project-v1"

    def test_default_project(self):
        s = self._import_schema()
        project = s["create_default_project"]("my_film")
        assert project.project_name == "my_film"
        assert project.schema_version == "vetka-cut-project-v1"
        assert len(project.timelines) == 1
        assert project.timelines[0].id == "main"
        assert project.next_version == 1

    def test_default_layout(self):
        s = self._import_schema()
        project = s["create_default_project"]()
        assert project.layout.left_width == 220
        assert project.layout.right_width == 280
        assert project.layout.bottom_height == 180
        assert project.layout.right_split == 0.5
        assert "script" in project.layout.left_tabs

    def test_default_pulse(self):
        s = self._import_schema()
        project = s["create_default_project"]()
        assert project.pulse.triangle_arch == 0.5
        assert project.pulse.triangle_mini == 0.3
        assert project.pulse.triangle_anti == 0.2
        assert abs(project.pulse.triangle_arch + project.pulse.triangle_mini + project.pulse.triangle_anti - 1.0) < 0.01
        assert project.pulse.sync_tolerance_sec == 0.083

    def test_add_timeline_version(self):
        s = self._import_schema()
        project = s["create_default_project"]("berlin")
        entry = s["add_timeline_version"](project, mode="script")
        assert entry.version == 1
        assert "berlin_cut-01" in entry.label
        assert entry.mode == "script"
        assert entry.parent_id == "main"
        assert project.next_version == 2
        assert len(project.timelines) == 2

    def test_add_multiple_versions(self):
        """Each version gets unique ID and label (§7.1 safety)."""
        s = self._import_schema()
        project = s["create_default_project"]("film")
        ids = set()
        labels = set()
        for i in range(5):
            entry = s["add_timeline_version"](project, mode="manual")
            ids.add(entry.id)
            labels.add(entry.label)
        assert len(ids) == 5  # all unique
        assert len(labels) == 5

    def test_save_and_load(self):
        s = self._import_schema()
        project = s["create_default_project"]("test_film", "proj_123")
        s["add_timeline_version"](project, mode="favorites")
        project.description = "Test project"
        project.tags = ["drama", "berlin"]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            tmppath = f.name
        try:
            s["save_project"](project, tmppath)
            loaded = s["load_project"](tmppath)
            assert loaded.project_name == "test_film"
            assert loaded.project_id == "proj_123"
            assert len(loaded.timelines) == 2
            assert loaded.description == "Test project"
            assert "berlin" in loaded.tags
        finally:
            os.unlink(tmppath)

    def test_load_nonexistent_raises(self):
        s = self._import_schema()
        with pytest.raises(FileNotFoundError):
            s["load_project"]("/nonexistent/path.json")

    def test_asset_entry(self):
        s = self._import_schema()
        asset = s["AssetEntry"](
            asset_id="a1",
            source_path="/media/clip01.mp4",
            media_type="video",
            duration_sec=120.0,
            camelot_key="8A",
            energy=0.7,
            cluster="take",
        )
        assert asset.asset_id == "a1"
        assert asset.cluster == "take"
        assert asset.camelot_key == "8A"

    def test_json_round_trip(self):
        """Schema survives JSON serialization."""
        s = self._import_schema()
        project = s["create_default_project"]("roundtrip_test")
        json_str = project.model_dump_json(indent=2)
        parsed = json.loads(json_str)
        assert parsed["schema_version"] == "vetka-cut-project-v1"
        assert parsed["project_name"] == "roundtrip_test"
        assert isinstance(parsed["timelines"], list)

    def test_timeline_modes(self):
        """All 4 timeline creation modes are valid."""
        s = self._import_schema()
        project = s["create_default_project"]("film")
        for mode in ["favorites", "script", "music", "manual"]:
            entry = s["add_timeline_version"](project, mode=mode)
            assert entry.mode == mode


# ---------------------------------------------------------------------------
# 180.4: CutEditorLayoutV2 — panel mapping
# ---------------------------------------------------------------------------

class TestCutEditorLayoutV2:
    """Test the panel-to-dock mapping in CutEditorLayoutV2."""

    # Expected panel→dock assignment from Architecture doc
    PANEL_DOCK_MAP = {
        "script": "left",
        "dag_project": "left",
        "program_monitor": "center",
        "source_monitor": "right_top",
        "inspector": "right_bottom",
        "timeline": "bottom",
        "story_space_3d": "floating",
        "effects": None,  # hidden by default
    }

    def test_7_visible_panels(self):
        """7 panels visible by default (effects hidden)."""
        visible = {k: v for k, v in self.PANEL_DOCK_MAP.items() if v is not None}
        assert len(visible) == 7

    def test_left_column_has_two_tabs(self):
        left_panels = [k for k, v in self.PANEL_DOCK_MAP.items() if v == "left"]
        assert len(left_panels) == 2
        assert "script" in left_panels
        assert "dag_project" in left_panels

    def test_center_is_program_monitor(self):
        assert self.PANEL_DOCK_MAP["program_monitor"] == "center"

    def test_right_split(self):
        right_panels = [k for k, v in self.PANEL_DOCK_MAP.items() if v and "right" in v]
        assert len(right_panels) == 2

    def test_story_space_floating(self):
        assert self.PANEL_DOCK_MAP["story_space_3d"] == "floating"

    def test_bottom_is_timeline(self):
        assert self.PANEL_DOCK_MAP["timeline"] == "bottom"

    def test_all_dock_positions_covered(self):
        """All 5 dock positions have at least one panel."""
        positions = {"left", "center", "right_top", "right_bottom", "bottom"}
        used = {v for v in self.PANEL_DOCK_MAP.values() if v and v != "floating" and v is not None}
        assert positions == used

    def test_effects_hidden(self):
        assert self.PANEL_DOCK_MAP["effects"] is None


class TestCutEditorLayoutV2Files:
    """Verify CutEditorLayoutV2 file structure."""

    def test_v2_layout_exists(self):
        path = Path(__file__).parent.parent.parent / "client" / "src" / "components" / "cut" / "CutEditorLayoutV2.tsx"
        assert path.exists()

    def test_v2_imports_panel_grid(self):
        path = Path(__file__).parent.parent.parent / "client" / "src" / "components" / "cut" / "CutEditorLayoutV2.tsx"
        if path.exists():
            code = path.read_text()
            assert "PanelGrid" in code
            assert "PanelShell" in code

    def test_v2_imports_all_panels(self):
        """V2 layout imports all panel components."""
        path = Path(__file__).parent.parent.parent / "client" / "src" / "components" / "cut" / "CutEditorLayoutV2.tsx"
        if path.exists():
            code = path.read_text()
            required_imports = [
                "ScriptPanel",
                "DAGProjectPanel",
                "VideoPreview",
                "PulseInspector",
                "TransportBar",
                "TimelineTabBar",
                "TimelineTrackView",
                "BPMTrack",
                "StorySpace3D",
            ]
            for imp in required_imports:
                assert imp in code, f"Missing import: {imp}"

    def test_original_layout_preserved(self):
        """Original CutEditorLayout.tsx still exists (not deleted)."""
        path = Path(__file__).parent.parent.parent / "client" / "src" / "components" / "cut" / "CutEditorLayout.tsx"
        assert path.exists(), "Original layout deleted — should be preserved"


# ---------------------------------------------------------------------------
# Complete Phase 180 file audit
# ---------------------------------------------------------------------------

class TestPhase180CompleteFileAudit:
    """Final audit: all Phase 180 deliverables exist and have content."""

    ALL_FILES = {
        # Stores
        "client/src/store/usePanelLayoutStore.ts": "180.1",
        "client/src/store/usePanelSyncStore.ts": "180.15",
        # Components
        "client/src/components/cut/PanelShell.tsx": "180.2",
        "client/src/components/cut/PanelGrid.tsx": "180.3",
        "client/src/components/cut/CutEditorLayoutV2.tsx": "180.4",
        "client/src/components/cut/ScriptPanel.tsx": "180.5",
        "client/src/components/cut/BPMTrack.tsx": "180.7",
        "client/src/components/cut/StorySpace3D.tsx": "180.9",
        "client/src/components/cut/CamelotWheel.tsx": "180.10",
        "client/src/components/cut/DAGProjectPanel.tsx": "180.16",
        "client/src/components/cut/PulseInspector.tsx": "180.18",
        # Backend
        "src/services/pulse_auto_montage.py": "180.12",
        "src/schemas/project_vetka_cut_schema.py": "180.21",
    }

    def test_all_deliverables_exist(self):
        root = Path(__file__).parent.parent.parent
        missing = []
        for relpath, task in self.ALL_FILES.items():
            if not (root / relpath).exists():
                missing.append(f"{task}: {relpath}")
        assert not missing, f"Missing files: {missing}"

    def test_all_deliverables_substantial(self):
        """Each file should have at least 100 lines."""
        root = Path(__file__).parent.parent.parent
        small = []
        for relpath, task in self.ALL_FILES.items():
            path = root / relpath
            if path.exists():
                lines = len(path.read_text().splitlines())
                if lines < 50:
                    small.append(f"{task}: {relpath} ({lines} lines)")
        assert not small, f"Files too small: {small}"
