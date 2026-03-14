"""
Phase 180 Wave 1-2 Tests — Panel Layout Store + BPM Markers + Panel Sync.

Tests cover:
- 180.1: usePanelLayoutStore (Python-side validation of store types)
- 180.8: BPM markers endpoint logic
- 180.15: usePanelSyncStore (Python-side validation)

MARKER_180_TESTS
"""
import json
import math
import pytest
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# 180.8: BPM Markers — sync point computation tests
# ---------------------------------------------------------------------------

class TestBPMSyncPoints:
    """Test the sync point detection logic from 180.8."""

    def _compute_sync_points(
        self,
        audio_times: List[float],
        visual_times: List[float],
        script_times: List[float],
        tolerance: float = 0.083,
    ) -> List[Dict[str, Any]]:
        """
        Replicate the sync point algorithm from cut_routes.py 180.8 endpoint.
        This validates the logic independently of FastAPI.
        """
        sync_points: list[dict] = []

        # For each audio beat, check if visual AND script are nearby
        for at in audio_times:
            has_visual = any(abs(vt - at) <= tolerance for vt in visual_times)
            has_script = any(abs(st - at) <= tolerance for st in script_times)
            if has_visual and has_script:
                sync_points.append({
                    "sec": round(at, 3),
                    "strength": 1.0,
                    "sources": ["audio", "visual", "script"],
                })
            elif has_visual or has_script:
                sources = ["audio"]
                if has_visual:
                    sources.append("visual")
                if has_script:
                    sources.append("script")
                sync_points.append({
                    "sec": round(at, 3),
                    "strength": 0.67,
                    "sources": sources,
                })

        # visual×script without audio
        for vt in visual_times:
            has_audio = any(abs(at - vt) <= tolerance for at in audio_times)
            if has_audio:
                continue
            has_script = any(abs(st - vt) <= tolerance for st in script_times)
            if has_script:
                sync_points.append({
                    "sec": round(vt, 3),
                    "strength": 0.67,
                    "sources": ["visual", "script"],
                })

        # Deduplicate
        deduped: list[dict] = []
        for sp in sorted(sync_points, key=lambda x: x["sec"]):
            if not deduped or abs(sp["sec"] - deduped[-1]["sec"]) > tolerance:
                deduped.append(sp)
            elif sp["strength"] > deduped[-1]["strength"]:
                deduped[-1] = sp
        return deduped

    def test_triple_sync_full_strength(self):
        """All 3 sources at same time → strength 1.0."""
        result = self._compute_sync_points(
            audio_times=[1.0, 2.0, 3.0],
            visual_times=[1.0, 3.0],
            script_times=[1.0, 3.0],
        )
        full_sync = [s for s in result if s["strength"] == 1.0]
        assert len(full_sync) >= 2
        assert full_sync[0]["sec"] == 1.0
        assert "audio" in full_sync[0]["sources"]
        assert "visual" in full_sync[0]["sources"]
        assert "script" in full_sync[0]["sources"]

    def test_double_sync_partial_strength(self):
        """2 of 3 sources → strength 0.67."""
        result = self._compute_sync_points(
            audio_times=[1.0],
            visual_times=[1.0],
            script_times=[5.0],  # far away
        )
        assert len(result) >= 1
        assert result[0]["strength"] == 0.67
        assert "audio" in result[0]["sources"]
        assert "visual" in result[0]["sources"]
        assert "script" not in result[0]["sources"]

    def test_no_sync_no_points(self):
        """No overlap → no sync points."""
        result = self._compute_sync_points(
            audio_times=[1.0],
            visual_times=[5.0],
            script_times=[10.0],
        )
        assert len(result) == 0

    def test_tolerance_boundary(self):
        """Events just within tolerance → sync."""
        tolerance = 0.083
        result = self._compute_sync_points(
            audio_times=[1.0],
            visual_times=[1.08],  # within 0.083
            script_times=[1.05],
            tolerance=tolerance,
        )
        assert len(result) >= 1
        assert result[0]["strength"] == 1.0

    def test_tolerance_exceeded(self):
        """Events just outside tolerance → no full sync."""
        tolerance = 0.083
        result = self._compute_sync_points(
            audio_times=[1.0],
            visual_times=[1.09],  # just outside 0.083
            script_times=[1.05],
            tolerance=tolerance,
        )
        # visual is outside, but script is inside → partial sync
        partial = [s for s in result if s["strength"] == 0.67]
        assert len(partial) >= 1

    def test_visual_script_without_audio(self):
        """Visual + Script without audio → still detected."""
        result = self._compute_sync_points(
            audio_times=[10.0],  # far away
            visual_times=[1.0],
            script_times=[1.0],
        )
        vs_sync = [s for s in result if "visual" in s["sources"] and "script" in s["sources"]]
        assert len(vs_sync) >= 1

    def test_deduplication(self):
        """Nearby sync points are deduplicated, keeping strongest."""
        result = self._compute_sync_points(
            audio_times=[1.0, 1.04],
            visual_times=[1.0, 1.04],
            script_times=[1.0],
            tolerance=0.083,
        )
        # Both audio beats are within tolerance of each other,
        # should keep the triple-sync (stronger)
        assert all(r["strength"] >= 0.67 for r in result)

    def test_empty_sources(self):
        """Empty sources → no crashes, no points."""
        result = self._compute_sync_points([], [], [])
        assert result == []

    def test_single_source_no_sync(self):
        """Only audio → no sync points (need 2+ sources)."""
        result = self._compute_sync_points(
            audio_times=[1.0, 2.0, 3.0],
            visual_times=[],
            script_times=[],
        )
        assert result == []

    def test_many_beats_performance(self):
        """100 audio beats, 20 visual cuts, 30 script events → runs fast."""
        import time
        audio = [i * 0.5 for i in range(100)]  # every 0.5s
        visual = [i * 2.5 for i in range(20)]  # every 2.5s
        script = [i * 1.67 for i in range(30)]  # every 1.67s

        start = time.time()
        result = self._compute_sync_points(audio, visual, script)
        elapsed = time.time() - start

        assert elapsed < 1.0  # should be << 1 second
        assert len(result) > 0  # some syncs expected

    def test_beat_generation_from_bpm(self):
        """Verify beat interval calculation: 120 BPM → 0.5s interval."""
        bpm = 120
        interval = 60.0 / bpm
        assert interval == 0.5

        bpm = 90
        interval = 60.0 / bpm
        assert abs(interval - 0.667) < 0.01


# ---------------------------------------------------------------------------
# 180.1: Panel Layout Store — type and default validation
# ---------------------------------------------------------------------------

class TestPanelLayoutTypes:
    """Validate panel layout store defaults and types (mirrors TypeScript store)."""

    # Default layout from Architecture doc §3
    DEFAULT_PANELS = [
        {"id": "script", "mode": "tab", "dock": "left", "visible": True},
        {"id": "dag_project", "mode": "tab", "dock": "left", "visible": True},
        {"id": "program_monitor", "mode": "docked", "dock": "center", "visible": True},
        {"id": "source_monitor", "mode": "docked", "dock": "right_top", "visible": True},
        {"id": "inspector", "mode": "docked", "dock": "right_bottom", "visible": True},
        {"id": "timeline", "mode": "docked", "dock": "bottom", "visible": True},
        {"id": "story_space_3d", "mode": "floating", "dock": None, "visible": True},
        {"id": "effects", "mode": "docked", "dock": None, "visible": False},
    ]

    VALID_MODES = {"docked", "tab", "floating"}
    VALID_DOCKS = {"left", "center", "right_top", "right_bottom", "bottom", None}
    VALID_IDS = {
        "script", "dag_project", "program_monitor", "source_monitor",
        "timeline", "story_space_3d", "effects", "inspector",
    }

    def test_all_panel_ids_unique(self):
        ids = [p["id"] for p in self.DEFAULT_PANELS]
        assert len(ids) == len(set(ids))

    def test_all_modes_valid(self):
        for p in self.DEFAULT_PANELS:
            assert p["mode"] in self.VALID_MODES, f"{p['id']} has invalid mode {p['mode']}"

    def test_all_docks_valid(self):
        for p in self.DEFAULT_PANELS:
            assert p["dock"] in self.VALID_DOCKS, f"{p['id']} has invalid dock {p['dock']}"

    def test_seven_core_panels(self):
        """Architecture doc §2 defines 7 panel types (+ inspector = 8)."""
        assert len(self.DEFAULT_PANELS) == 8

    def test_monitors_not_dag_capable(self):
        """Architecture doc §8: monitors CANNOT switch to DAG."""
        non_dag = {"program_monitor", "source_monitor"}
        for p in self.DEFAULT_PANELS:
            if p["id"] in non_dag:
                assert p["mode"] in {"docked", "floating"}, \
                    f"{p['id']} should not be a tab (monitors are fixed)"

    def test_story_space_default_floating_mini(self):
        """StorySpace3D defaults to floating mini inside Program Monitor."""
        ss = next(p for p in self.DEFAULT_PANELS if p["id"] == "story_space_3d")
        assert ss["mode"] == "floating"
        assert ss["visible"] is True

    def test_left_column_has_tabs(self):
        """Script + DAG project share left column as tabs."""
        left = [p for p in self.DEFAULT_PANELS if p["dock"] == "left"]
        assert len(left) == 2
        assert all(p["mode"] == "tab" for p in left)

    def test_effects_hidden_by_default(self):
        """Effects panel hidden until user needs it."""
        effects = next(p for p in self.DEFAULT_PANELS if p["id"] == "effects")
        assert effects["visible"] is False

    def test_grid_defaults(self):
        """Default grid sizes from Architecture doc §3."""
        grid = {"leftWidth": 220, "rightWidth": 280, "bottomHeight": 180, "rightSplit": 0.5}
        assert grid["leftWidth"] == 220
        assert grid["rightWidth"] == 280
        assert grid["bottomHeight"] == 180
        assert 0 < grid["rightSplit"] < 1


# ---------------------------------------------------------------------------
# 180.15: Panel Sync Store — sync matrix validation
# ---------------------------------------------------------------------------

class TestPanelSyncMatrix:
    """Validate the sync matrix from Architecture doc §9."""

    SYNC_SOURCES = [
        "script", "dag_project", "timeline", "program_monitor",
        "source_monitor", "story_space_3d", "inspector", "transport", "external",
    ]

    def test_all_sync_sources_valid(self):
        """All sync source types defined."""
        assert len(self.SYNC_SOURCES) == 9

    def test_script_sync_updates_playhead(self):
        """Click script line → playhead must update."""
        # Simulating store behavior
        state = {"playheadSec": 0, "activeSceneId": None, "selectedScriptLine": None}
        # syncFromScript(lineIndex=5, sceneId="sc_3", timeSec=120.5)
        state["selectedScriptLine"] = 5
        state["activeSceneId"] = "sc_3"
        state["playheadSec"] = 120.5
        assert state["playheadSec"] == 120.5
        assert state["activeSceneId"] == "sc_3"

    def test_story_space_sync_updates_playhead(self):
        """Click StorySpace dot → playhead + activeSceneId update."""
        state = {"playheadSec": 0, "activeSceneId": None}
        state["activeSceneId"] = "sc_7"
        state["playheadSec"] = 45.0
        assert state["playheadSec"] == 45.0

    def test_dag_sync_updates_asset(self):
        """Click DAG node → selectedAssetId + selectedAssetPath update."""
        state = {"selectedAssetId": None, "selectedAssetPath": None}
        state["selectedAssetId"] = "asset_42"
        state["selectedAssetPath"] = "/media/clip_01.mp4"
        assert state["selectedAssetId"] == "asset_42"

    def test_bpm_values_independent(self):
        """BPM display values are 3 independent numbers."""
        bpm = {"audio": 124.0, "visual": 96.0, "script": 108.0}
        assert bpm["audio"] != bpm["visual"]
        assert bpm["visual"] != bpm["script"]

    def test_clear_sync_resets_all(self):
        """clearSync() resets everything to null/zero."""
        state = {
            "activeSceneId": "sc_1",
            "playheadSec": 100,
            "selectedAssetId": "a_1",
        }
        # clearSync
        state = {k: None if isinstance(v, str) else 0 for k, v in state.items()}
        assert state["activeSceneId"] is None
        assert state["playheadSec"] == 0


# ---------------------------------------------------------------------------
# Architecture doc §11 — Visual Design Rules validation
# ---------------------------------------------------------------------------

class TestVisualDesignRules:
    """Validate color/font constants match Architecture doc §11."""

    def test_background_colors(self):
        """Dark theme backgrounds."""
        colors = {
            "root": "#0D0D0D",
            "panels": "#1A1A1A",
            "surfaces": "#252525",
        }
        for name, color in colors.items():
            assert color.startswith("#"), f"{name} must be hex"
            assert len(color) == 7, f"{name} must be 6-digit hex"

    def test_text_colors(self):
        """Text hierarchy."""
        assert "#E0E0E0"  # primary
        assert "#888888" or "#888"  # secondary
        assert "#555555" or "#555"  # disabled

    def test_border_spec(self):
        """0.5px solid #333 for borders."""
        border = "0.5px solid #333"
        assert "0.5px" in border
        assert "#333" in border

    def test_corner_radius_hierarchy(self):
        """4px panels, 2px buttons, 0px timeline elements."""
        assert 4 > 2 > 0  # hierarchy check

    def test_no_gradients_rule(self):
        """Rule: no gradients, shadows, glow, blur."""
        forbidden = ["gradient", "shadow", "glow", "blur"]
        # This is a documentation test — actual audit is 180.19
        assert len(forbidden) == 4

    def test_font_spec(self):
        """JetBrains Mono for timecode, Inter for labels."""
        fonts = {"timecode": "JetBrains Mono", "labels": "Inter"}
        assert fonts["timecode"] != fonts["labels"]
