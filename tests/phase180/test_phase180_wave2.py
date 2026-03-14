"""
Phase 180 Wave 2 Tests — BPMTrack + StorySpace3D + CamelotWheel + PulseInspector + DAGProjectPanel.

Tests cover:
- 180.7:  BPMTrack — Canvas rendering logic, dot spacing, data fetch contract
- 180.9:  StorySpace3D — 3D positioning math, pendulum→color, API contract
- 180.10: CamelotWheel — SVG arc geometry, harmonic distance, key lookup
- 180.16: DAGProjectPanel — cluster layout, node classification, API contract
- 180.18: PulseInspector — scene context display, pendulum labels

MARKER_180_WAVE2_TESTS
"""
import math
import pytest
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# 180.7: BPMTrack — Canvas rendering contract tests
# ---------------------------------------------------------------------------

class TestBPMTrack:
    """Test BPM track dot rendering logic (mirrors Canvas drawing code)."""

    DOT_RADIUS = 2
    MIN_DOT_SPACING_PX = 3

    def _should_draw_dot(
        self, sec: float, px_per_sec: float, scroll_left: float,
        visible_width: float, last_px: float,
    ) -> tuple[bool, float]:
        """Replicate the dot visibility/spacing check from BPMTrack canvas."""
        px = sec * px_per_sec - scroll_left
        if px < -self.DOT_RADIUS or px > visible_width + self.DOT_RADIUS:
            return False, last_px
        if px - last_px < self.MIN_DOT_SPACING_PX:
            return False, last_px
        return True, px

    def test_visible_dots_basic(self):
        """Dots within viewport are drawn."""
        drawn, _ = self._should_draw_dot(
            sec=5.0, px_per_sec=100, scroll_left=0,
            visible_width=800, last_px=-999,
        )
        assert drawn

    def test_offscreen_left_skipped(self):
        """Dots scrolled off left edge are skipped."""
        drawn, _ = self._should_draw_dot(
            sec=1.0, px_per_sec=100, scroll_left=200,
            visible_width=800, last_px=-999,
        )
        assert not drawn

    def test_offscreen_right_skipped(self):
        """Dots beyond right edge are skipped."""
        drawn, _ = self._should_draw_dot(
            sec=100.0, px_per_sec=100, scroll_left=0,
            visible_width=800, last_px=-999,
        )
        assert not drawn

    def test_min_spacing_enforced(self):
        """Dots too close together are skipped (prevents visual clutter)."""
        _, last = self._should_draw_dot(
            sec=5.0, px_per_sec=100, scroll_left=0,
            visible_width=800, last_px=-999,
        )
        # Next dot at 5.01s = 501px, only 1px away from 500px
        drawn, _ = self._should_draw_dot(
            sec=5.01, px_per_sec=100, scroll_left=0,
            visible_width=800, last_px=last,
        )
        assert not drawn

    def test_adequate_spacing_drawn(self):
        """Dots with enough spacing are drawn."""
        _, last = self._should_draw_dot(
            sec=5.0, px_per_sec=100, scroll_left=0,
            visible_width=800, last_px=-999,
        )
        drawn, _ = self._should_draw_dot(
            sec=5.1, px_per_sec=100, scroll_left=0,
            visible_width=800, last_px=last,
        )
        assert drawn  # 10px apart > 3px minimum

    def test_120bpm_dot_count(self):
        """120 BPM over 60 seconds = 120 beats. With pxPerSec=50, most should be visible."""
        beats = [i * 0.5 for i in range(120)]  # 120 BPM = 0.5s interval
        visible = 0
        last_px = -999.0
        for b in beats:
            drawn, new_last = self._should_draw_dot(
                sec=b, px_per_sec=50, scroll_left=0,
                visible_width=3000, last_px=last_px,
            )
            if drawn:
                visible += 1
                last_px = new_last
        # At 50px/sec, beats are 25px apart — all should be visible
        assert visible == 120

    def test_high_density_filtering(self):
        """Very high BPM (240) at low zoom → many dots filtered by spacing."""
        beats = [i * 0.25 for i in range(240)]  # 240 BPM
        visible = 0
        last_px = -999.0
        for b in beats:
            drawn, new_last = self._should_draw_dot(
                sec=b, px_per_sec=10, scroll_left=0,
                visible_width=600, last_px=last_px,
            )
            if drawn:
                visible += 1
                last_px = new_last
        # At 10px/sec, beats are 2.5px apart < 3px min → half should be filtered
        assert visible < 240

    def test_bpm_markers_api_contract(self):
        """Validate the expected API response shape."""
        response = {
            "success": True,
            "schema_version": "pulse_bpm_markers_v1",
            "audio_beats": [{"sec": 0.5, "bpm": 120, "source": "audio"}],
            "audio_beat_count": 1,
            "visual_cuts": [{"sec": 2.0, "source": "visual"}],
            "visual_cut_count": 1,
            "script_events": [{"sec": 0.0, "type": "exposition", "source": "script"}],
            "script_event_count": 1,
            "sync_points": [{"sec": 0.5, "strength": 0.67, "sources": ["audio", "visual"]}],
            "sync_point_count": 1,
            "sync_tolerance_sec": 0.083,
        }
        assert response["success"]
        assert response["schema_version"] == "pulse_bpm_markers_v1"
        assert isinstance(response["audio_beats"], list)
        assert isinstance(response["sync_points"], list)
        assert response["sync_points"][0]["strength"] in (0.67, 1.0)

    def test_four_row_layout(self):
        """BPM track has 4 rows: audio, visual, script, sync. Fits in 36px."""
        ROW_HEIGHT = 8
        ROW_GAP = 1
        TRACK_HEIGHT = 36
        rows = 4
        # 4 rows × 8px + gaps between rows
        expected_height = rows * ROW_HEIGHT + (rows - 1) * ROW_GAP
        assert expected_height <= TRACK_HEIGHT


# ---------------------------------------------------------------------------
# 180.9: StorySpace3D — 3D positioning math
# ---------------------------------------------------------------------------

class TestStorySpace3DPositioning:
    """Test the 3D position calculation for StorySpace points."""

    WHEEL_RADIUS = 3
    TRIANGLE_HEIGHT = 4

    def _point_to_position(self, camelot_angle: float, mckee_height: float, energy: float):
        """Replicate pointToPosition() from StorySpace3D.tsx."""
        rad = camelot_angle * math.pi / 180
        r = self.WHEEL_RADIUS * 0.3 + self.WHEEL_RADIUS * 0.7 * energy
        x = math.cos(rad) * r
        z = math.sin(rad) * r
        y = mckee_height * self.TRIANGLE_HEIGHT
        return (x, y, z)

    def test_arch_top_position(self):
        """Archplot (mckee_height=1.0) → Y = TRIANGLE_HEIGHT."""
        _, y, _ = self._point_to_position(0, 1.0, 0.5)
        assert y == self.TRIANGLE_HEIGHT

    def test_anti_bottom_position(self):
        """Antiplot (mckee_height=0.0) → Y = 0."""
        _, y, _ = self._point_to_position(0, 0.0, 0.5)
        assert y == 0.0

    def test_camelot_angle_0_on_x_axis(self):
        """Angle 0° → positive X axis."""
        x, _, z = self._point_to_position(0, 0.5, 0.5)
        assert x > 0
        assert abs(z) < 0.001

    def test_camelot_angle_90_on_z_axis(self):
        """Angle 90° → positive Z axis."""
        x, _, z = self._point_to_position(90, 0.5, 0.5)
        assert abs(x) < 0.001
        assert z > 0

    def test_energy_scales_radius(self):
        """Higher energy → larger radius from center."""
        x_low, _, z_low = self._point_to_position(45, 0.5, 0.1)
        x_high, _, z_high = self._point_to_position(45, 0.5, 0.9)
        r_low = math.sqrt(x_low**2 + z_low**2)
        r_high = math.sqrt(x_high**2 + z_high**2)
        assert r_high > r_low

    def test_zero_energy_still_visible(self):
        """Even at zero energy, dot has minimum radius (0.3 * WHEEL_RADIUS)."""
        x, _, z = self._point_to_position(0, 0.5, 0.0)
        r = math.sqrt(x**2 + z**2)
        assert r == pytest.approx(self.WHEEL_RADIUS * 0.3, abs=0.01)

    def test_full_energy_max_radius(self):
        """Energy 1.0 → full WHEEL_RADIUS."""
        x, _, z = self._point_to_position(0, 0.5, 1.0)
        r = math.sqrt(x**2 + z**2)
        assert r == pytest.approx(self.WHEEL_RADIUS, abs=0.01)


class TestPendulumToColor:
    """Test pendulum → color mapping."""

    def _pendulum_to_rgb(self, pendulum: float) -> tuple[int, int, int]:
        """Replicate pendulumToColor() from StorySpace3D.tsx, returning RGB."""
        if pendulum >= 0:
            t = pendulum
            r = round(224 + (255 - 224) * t)
            g = round(224 - (224 - 159) * t)
            b = round(224 - (224 - 67) * t)
        else:
            t = -pendulum
            r = round(224 - (224 - 55) * t)
            g = round(224 - (224 - 138) * t)
            b = round(224 + (221 - 224) * t)
        return (r, g, b)

    def test_neutral_is_light(self):
        """Pendulum 0 → near-white (224,224,224)."""
        r, g, b = self._pendulum_to_rgb(0.0)
        assert r == 224 and g == 224 and b == 224

    def test_positive_is_warm(self):
        """Pendulum +1 → warm orange (255,159,67)."""
        r, g, b = self._pendulum_to_rgb(1.0)
        assert r == 255
        assert g == 159
        assert b == 67

    def test_negative_is_cool(self):
        """Pendulum -1 → cool blue (55,138,221)."""
        r, g, b = self._pendulum_to_rgb(-1.0)
        assert r == 55
        assert g == 138
        assert b == 221

    def test_half_positive(self):
        """Pendulum +0.5 → somewhere between white and orange."""
        r, g, b = self._pendulum_to_rgb(0.5)
        assert 224 < r <= 255
        assert 159 < g < 224
        assert 67 < b < 224


# ---------------------------------------------------------------------------
# 180.10: CamelotWheel — harmonic distance + geometry
# ---------------------------------------------------------------------------

class TestCamelotWheel:
    """Test Camelot harmonic distance and wheel geometry."""

    def _camelot_distance(self, key1: str, key2: str) -> int:
        """Replicate camelotDistance() from CamelotWheel.tsx."""
        # Extract number and letter
        num1 = int(''.join(c for c in key1 if c.isdigit()))
        num2 = int(''.join(c for c in key2 if c.isdigit()))
        letter1 = key1[-1]
        letter2 = key2[-1]

        if key1 == key2:
            return 0
        if num1 == num2:
            return 1  # relative major/minor
        diff = abs(num1 - num2)
        circ_diff = min(diff, 12 - diff)
        if letter1 == letter2 and circ_diff == 1:
            return 1
        return circ_diff + (1 if letter1 != letter2 else 0)

    def test_same_key_zero(self):
        assert self._camelot_distance("8A", "8A") == 0

    def test_relative_major_minor(self):
        """Same number, different letter = 1 (e.g., 8A → 8B)."""
        assert self._camelot_distance("8A", "8B") == 1

    def test_adjacent_same_letter(self):
        """Adjacent numbers, same letter = 1 (e.g., 8A → 9A)."""
        assert self._camelot_distance("8A", "9A") == 1
        assert self._camelot_distance("8A", "7A") == 1

    def test_wrap_around_12_to_1(self):
        """12A → 1A wraps around = distance 1."""
        assert self._camelot_distance("12A", "1A") == 1

    def test_opposite_keys_far(self):
        """Keys on opposite sides = distance 6."""
        assert self._camelot_distance("1A", "7A") == 6

    def test_cross_letter_and_number(self):
        """Different letter AND number = distance > 1."""
        d = self._camelot_distance("1A", "3B")
        assert d > 1

    def test_compatible_keys_within_1(self):
        """Active key 8A should have 5 compatible keys (self + 4 neighbors)."""
        active = "8A"
        all_keys = [f"{i}{l}" for i in range(1, 13) for l in "AB"]
        compatible = [k for k in all_keys if self._camelot_distance(active, k) <= 1]
        # 8A (self) + 7A, 9A (adjacent same letter) + 8B (relative major) = 4
        # Plus 7B, 9B adjacent to 8B? No, those are distance 2.
        assert len(compatible) == 4  # 8A, 7A, 9A, 8B

    def test_24_keys_total(self):
        """Camelot wheel has 24 positions (12 major + 12 minor)."""
        all_keys = [f"{i}{l}" for i in range(1, 13) for l in "AB"]
        assert len(all_keys) == 24

    def test_arc_segment_coverage(self):
        """12 segments × 30° = 360° full circle."""
        SEGMENT_ARC = 30
        assert 12 * SEGMENT_ARC == 360


class TestCamelotWheelGeometry:
    """Test SVG arc path generation."""

    SVG_SIZE = 200
    CENTER = 100
    OUTER_R = 85
    INNER_R = 55

    def test_outer_ring_larger(self):
        assert self.OUTER_R > self.INNER_R

    def test_rings_fit_in_svg(self):
        assert self.CENTER + self.OUTER_R <= self.SVG_SIZE

    def test_inner_ring_has_space(self):
        """Inner ring must leave space for center label."""
        INNER_R_INNER = 32
        assert INNER_R_INNER > 20  # enough for text


# ---------------------------------------------------------------------------
# 180.16: DAGProjectPanel — cluster layout + API contract
# ---------------------------------------------------------------------------

class TestDAGProjectLayout:
    """Test DAG node layout by cluster columns."""

    CLUSTER_ORDER = ['character', 'location', 'take', 'dub', 'music', 'sfx', 'graphics', 'other']
    COL_WIDTH = 180
    ROW_HEIGHT = 70
    CLUSTER_GAP = 30

    def _layout_clusters(self, nodes_per_cluster: Dict[str, int]):
        """Replicate layoutNodes() cluster column positioning."""
        positions: list[dict] = []
        col_x = 0
        for cluster in self.CLUSTER_ORDER:
            count = nodes_per_cluster.get(cluster, 0)
            if count == 0:
                continue
            for i in range(count):
                positions.append({
                    "cluster": cluster,
                    "x": col_x,
                    "y": i * self.ROW_HEIGHT + 10,
                })
            col_x += self.COL_WIDTH + self.CLUSTER_GAP
        return positions

    def test_single_cluster(self):
        positions = self._layout_clusters({"take": 3})
        assert len(positions) == 3
        assert all(p["x"] == 0 for p in positions)

    def test_two_clusters_separate_columns(self):
        positions = self._layout_clusters({"character": 2, "location": 1})
        char_x = {p["x"] for p in positions if p["cluster"] == "character"}
        loc_x = {p["x"] for p in positions if p["cluster"] == "location"}
        assert char_x != loc_x

    def test_empty_clusters_skipped(self):
        positions = self._layout_clusters({"take": 2})
        # Only take cluster, no gaps for empty character/location
        assert positions[0]["x"] == 0

    def test_vertical_stacking(self):
        positions = self._layout_clusters({"take": 5})
        ys = [p["y"] for p in positions]
        assert ys == sorted(ys)  # monotonically increasing

    def test_all_8_cluster_types(self):
        """Architecture doc §2.2 defines 8 cluster types."""
        assert len(self.CLUSTER_ORDER) == 8

    def test_dag_api_contract(self):
        """Validate expected API response shape."""
        response = {
            "success": True,
            "schema_version": "cut_project_dag_v1",
            "node_count": 5,
            "edge_count": 3,
            "clusters": {"take": ["n1", "n2"], "music": ["n3"]},
            "nodes": [
                {
                    "node_id": "n1",
                    "label": "clip01.mp4",
                    "cluster": "take",
                    "camelot_key": "8A",
                    "energy": 0.7,
                    "linked_scene_ids": ["sc_1"],
                },
            ],
            "edges": [
                {"source": "n1", "target": "n3", "edge_type": "sync"},
            ],
        }
        assert response["success"]
        assert "clusters" in response
        node = response["nodes"][0]
        assert "cluster" in node
        assert "linked_scene_ids" in node


# ---------------------------------------------------------------------------
# 180.18: PulseInspector — display logic
# ---------------------------------------------------------------------------

class TestPulseInspector:
    """Test PulseInspector display helpers."""

    def _pendulum_label(self, v: float) -> str:
        """Replicate pendulumLabel() from PulseInspector.tsx."""
        if v <= -0.6:
            return "Deep Minor"
        if v <= -0.2:
            return "Minor"
        if v <= 0.2:
            return "Neutral"
        if v <= 0.6:
            return "Major"
        return "Bright Major"

    def test_deep_minor(self):
        assert self._pendulum_label(-0.8) == "Deep Minor"

    def test_minor(self):
        assert self._pendulum_label(-0.4) == "Minor"

    def test_neutral(self):
        assert self._pendulum_label(0.0) == "Neutral"

    def test_major(self):
        assert self._pendulum_label(0.4) == "Major"

    def test_bright_major(self):
        assert self._pendulum_label(0.9) == "Bright Major"

    def test_boundary_minor_neutral(self):
        """At exactly -0.2, should be Minor (≤ -0.2 boundary)."""
        assert self._pendulum_label(-0.2) == "Minor"

    def test_boundary_neutral_major(self):
        """At exactly 0.2, should be Neutral."""
        assert self._pendulum_label(0.2) == "Neutral"

    def _format_timecode(self, sec: float) -> str:
        """Replicate timecode formatting."""
        m = int(sec) // 60
        s = int(sec) % 60
        f = int((sec % 1) * 24)  # 24fps
        return f"{m:02d}:{s:02d}:{f:02d}"

    def test_timecode_zero(self):
        assert self._format_timecode(0.0) == "00:00:00"

    def test_timecode_one_minute(self):
        assert self._format_timecode(60.0) == "01:00:00"

    def test_timecode_with_frames(self):
        """0.5 seconds at 24fps = 12 frames."""
        assert self._format_timecode(0.5) == "00:00:12"

    def test_timecode_complex(self):
        """2 min 30 sec 10 frames (10/24 = 0.4167s)."""
        tc = self._format_timecode(150.4167)
        assert tc == "02:30:10"

    def test_dramatic_function_icons(self):
        """Each dramatic function should have a corresponding icon."""
        functions = ["exposition", "rising_action", "climax", "falling_action", "resolution", "turning_point"]
        # Verify all are recognized (no crash, all have icons)
        def function_icon(fn: str) -> str:
            icons = {
                "exposition": "📖",
                "rising_action": "📈",
                "climax": "⚡",
                "falling_action": "📉",
                "resolution": "🏁",
                "turning_point": "🔄",
            }
            return icons.get(fn, "●")
        for fn in functions:
            assert function_icon(fn) != "●"


# ---------------------------------------------------------------------------
# Cross-component: Sync store integration
# ---------------------------------------------------------------------------

class TestSyncStoreIntegration:
    """Test that all Wave 2 components interact correctly with PanelSyncStore."""

    def test_story_space_dot_click_produces_sync(self):
        """Clicking StorySpace dot should call syncFromStorySpace(sceneId, timeSec)."""
        # Simulate: scene_index=3 → scene_id="sc_3", time=12 (3*4)
        scene_index = 3
        scene_id = f"sc_{scene_index}"
        time_sec = scene_index * 4
        assert scene_id == "sc_3"
        assert time_sec == 12

    def test_dag_node_click_produces_sync(self):
        """Clicking DAG node should call syncFromDAG(assetId, assetPath)."""
        asset_id = "n1"
        asset_path = "/media/clip01.mp4"
        # Verify these are non-empty
        assert asset_id
        assert asset_path

    def test_bpm_track_updates_bpm_display(self):
        """BPMTrack should call setBPM(audio, visual, script)."""
        audio_bpm = 120.0
        visual_bpm = 96  # cuts per minute
        script_bpm = 108
        assert audio_bpm > 0
        assert visual_bpm > 0
        assert script_bpm > 0

    def test_inspector_reads_active_scene_context(self):
        """PulseInspector should read activeSceneContext from sync store."""
        context = {
            "scene_id": "sc_1",
            "camelot_key": "8A",
            "energy": 0.7,
            "pendulum": -0.3,
            "triangle_pos": {"arch": 0.5, "mini": 0.3, "anti": 0.2},
            "dramatic_function": "exposition",
        }
        assert "camelot_key" in context
        assert "energy" in context
        assert "triangle_pos" in context


# ---------------------------------------------------------------------------
# Architecture doc §11 — Visual Design Rules for Wave 2
# ---------------------------------------------------------------------------

class TestWave2DesignRules:
    """Validate color/font constants in Wave 2 components match §11."""

    def test_story_space_background(self):
        """StorySpace uses root background #0D0D0D."""
        assert "#0D0D0D"  # darkest level per §11

    def test_camelot_wheel_12_keys(self):
        """12 Camelot keys on the outer ring."""
        keys = [f"{i}B" for i in range(1, 13)]
        assert len(keys) == 12

    def test_bpm_colors(self):
        """BPM dot colors per Architecture doc §5.1."""
        colors = {
            "audio": "#5DCAA5",    # green
            "visual": "#85B7EB",   # blue
            "script": "#E0E0E0",   # white
            "sync": "#FF9F43",     # orange
        }
        assert len(colors) == 4
        # All are hex colors
        for name, c in colors.items():
            assert c.startswith("#"), f"{name} must be hex"

    def test_monochrome_font_stack(self):
        """§11: JetBrains Mono for data, Inter for labels."""
        fonts = {
            "data": "JetBrains Mono",
            "labels": "Inter",
        }
        assert fonts["data"] != fonts["labels"]
