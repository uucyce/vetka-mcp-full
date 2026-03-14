"""
Phase 179 Sprint 5 Tests — Triangle endpoints, SRT bridge, Marker→StorySpace.

MARKER_179.14_TESTS
MARKER_179.15_TESTS
MARKER_179.20_TESTS
"""
import pytest
from src.services.pulse_story_space import (
    TrianglePosition,
    StorySpacePoint,
    compute_triangle_energies,
    chaos_index,
    scores_to_story_space,
    genre_to_triangle,
    interpolate_critic_weights,
    markers_to_story_space_points,
)
from src.services.pulse_conductor import (
    PulseScore,
    NarrativeBPM,
    get_pulse_conductor,
)
from src.services.pulse_srt_bridge import (
    parse_srt,
    parse_vtt,
    parse_subtitles,
    parse_timestamp,
    group_into_scenes,
    srt_to_narrative_bpm,
    srt_to_narrative_bpm_with_timing,
    SubtitleBlock,
)
from src.services.pulse_script_analyzer import get_script_analyzer


# ---------------------------------------------------------------------------
# 179.14 — Triangle + StorySpace3D
# ---------------------------------------------------------------------------

class TestTrianglePosition:
    def test_auto_normalize(self):
        t = TrianglePosition(2.0, 1.0, 1.0)
        assert abs(t.arch + t.mini + t.anti - 1.0) < 0.01

    def test_dominant_archplot(self):
        t = TrianglePosition(0.8, 0.1, 0.1)
        assert t.dominant == "archplot"

    def test_dominant_miniplot(self):
        t = TrianglePosition(0.1, 0.7, 0.2)
        assert t.dominant == "miniplot"

    def test_dominant_antiplot(self):
        t = TrianglePosition(0.1, 0.1, 0.8)
        assert t.dominant == "antiplot"

    def test_mckee_height(self):
        t = TrianglePosition(0.9, 0.05, 0.05)
        assert t.mckee_height == 0.9

    def test_to_dict(self):
        t = TrianglePosition(0.5, 0.3, 0.2)
        d = t.to_dict()
        assert d["arch"] == 0.5
        assert d["mini"] == 0.3
        assert d["anti"] == 0.2


class TestInterpolateCriticWeights:
    def test_pure_archplot(self):
        t = TrianglePosition(1.0, 0.0, 0.0)
        w = interpolate_critic_weights(t)
        assert w["pendulum_balance"] == 1.0
        assert w["chaos_tolerance"] == 0.0

    def test_pure_antiplot(self):
        t = TrianglePosition(0.0, 0.0, 1.0)
        w = interpolate_critic_weights(t)
        assert w["chaos_tolerance"] == 1.0
        assert w["pendulum_balance"] == 0.0

    def test_midpoint_interpolation(self):
        t = TrianglePosition(0.5, 0.5, 0.0)
        w = interpolate_critic_weights(t)
        # Should be between arch and mini values
        assert 0.4 <= w["pendulum_balance"] <= 1.0
        assert w["chaos_tolerance"] == 0.0  # both arch and mini have 0.0

    def test_all_weights_present(self):
        t = TrianglePosition(0.33, 0.34, 0.33)
        w = interpolate_critic_weights(t)
        expected_keys = [
            "pendulum_balance", "pendulum_amplitude_min",
            "camelot_proximity", "energy_contour",
            "music_scene_sync", "script_visual_match",
            "counterpoint_penalty", "chaos_tolerance",
        ]
        for key in expected_keys:
            assert key in w


class TestChaosIndex:
    def _make_scores(self, keys, pendulums, energies):
        scores = []
        for i, (k, p, e) in enumerate(zip(keys, pendulums, energies)):
            scores.append(PulseScore(
                scene_id=f"sc_{i}",
                camelot_key=k,
                scale="Ionian",
                pendulum_position=p,
                dramatic_function="Test",
                energy_profile="neutral",
                counterpoint_pair="Aeolian",
                confidence=0.5,
                narrative_bpm=NarrativeBPM(
                    scene_id=f"sc_{i}",
                    dramatic_function="Test",
                    pendulum_position=p,
                    estimated_energy=e,
                ),
            ))
        return scores

    def test_low_chaos_smooth(self):
        # Smooth transitions → low chaos
        scores = self._make_scores(
            ["8B", "9B", "10B", "11B"],
            [0.5, -0.3, 0.4, -0.2],
            [0.3, 0.4, 0.5, 0.6],
        )
        ci = chaos_index(scores)
        assert ci < 0.5

    def test_high_chaos_wild(self):
        # Wild jumps → high chaos
        scores = self._make_scores(
            ["1A", "7B", "3A", "10B", "5A"],
            [1.0, -1.0, 1.0, -1.0, 1.0],
            [0.9, 0.1, 0.9, 0.1, 0.9],
        )
        ci = chaos_index(scores)
        assert ci > 0.3

    def test_too_few_scenes(self):
        scores = self._make_scores(["8B", "9B"], [0.5, -0.3], [0.3, 0.4])
        assert chaos_index(scores) == 0.0


class TestScoresToStorySpace:
    def test_basic_conversion(self):
        conductor = get_pulse_conductor()
        analyzer = get_script_analyzer()
        scenes = analyzer.analyze("The hero celebrates victory. The villain lurks in shadow.")
        scores = [conductor.score_scene(scene_id=s.scene_id, narrative=s) for s in scenes]
        points = scores_to_story_space(scores)
        assert len(points) == len(scores)
        for p in points:
            d = p.to_dict()
            assert "camelot_key" in d
            assert "triangle" in d
            assert "pendulum" in d


class TestComputeTriangleEnergies:
    def test_returns_structure(self):
        conductor = get_pulse_conductor()
        analyzer = get_script_analyzer()
        scenes = analyzer.analyze(
            "INT. DARK ALLEY - NIGHT\nThe detective investigates the mystery.\n"
            "EXT. STADIUM - DAY\nThe hero wins the championship."
        )
        scores = [conductor.score_scene(scene_id=s.scene_id, narrative=s) for s in scenes]
        result = compute_triangle_energies(scores)
        assert "triangle_position" in result
        assert "calibrated" in result
        assert "raw" in result
        assert "weights" in result
        assert "interpretation" in result

    def test_explicit_triangle(self):
        conductor = get_pulse_conductor()
        analyzer = get_script_analyzer()
        scenes = analyzer.analyze("A hero's victory celebration. Evil threatens the kingdom.")
        scores = [conductor.score_scene(scene_id=s.scene_id, narrative=s) for s in scenes]
        tri = TrianglePosition(0.9, 0.05, 0.05)
        result = compute_triangle_energies(scores, triangle=tri)
        assert result["dominant_vertex"] == "archplot"


class TestGenreToTriangle:
    def test_known_genre(self):
        t = genre_to_triangle("action")
        assert t.arch > 0.7

    def test_unknown_genre_returns_default(self):
        t = genre_to_triangle("nonexistent_genre_xyz")
        assert abs(t.arch - 0.5) < 0.01

    def test_case_insensitive(self):
        t = genre_to_triangle("Art House")
        assert t.mini > t.arch


# ---------------------------------------------------------------------------
# 179.15 — SRT Bridge
# ---------------------------------------------------------------------------

SAMPLE_SRT = """1
00:00:01,000 --> 00:00:04,000
The hero stands at the edge of the world.

2
00:00:04,500 --> 00:00:07,000
A shadow creeps from behind.

3
00:00:07,500 --> 00:00:10,000
He draws his sword with determination.

4
00:00:15,000 --> 00:00:18,000
The villain emerges from the darkness.

5
00:00:18,500 --> 00:00:22,000
A fierce battle begins. Blood and chaos everywhere.
"""

SAMPLE_VTT = """WEBVTT

00:00:01.000 --> 00:00:04.000
The detective investigates the crime scene.

00:00:04.500 --> 00:00:07.000
Clues are scattered everywhere.

00:00:10.000 --> 00:00:13.000
The mystery deepens at night.
"""


class TestParseTimestamp:
    def test_srt_format(self):
        assert parse_timestamp("00:01:30,500") == 90.5

    def test_vtt_format(self):
        assert parse_timestamp("00:01:30.500") == 90.5

    def test_minutes_only(self):
        assert parse_timestamp("01:30.000") == 90.0

    def test_hours(self):
        assert parse_timestamp("01:00:00,000") == 3600.0


class TestParseSrt:
    def test_basic_parse(self):
        blocks = parse_srt(SAMPLE_SRT)
        assert len(blocks) == 5
        assert blocks[0].start_sec == 1.0
        assert blocks[0].end_sec == 4.0
        assert "hero" in blocks[0].text

    def test_sequential_indices(self):
        blocks = parse_srt(SAMPLE_SRT)
        for i, b in enumerate(blocks):
            assert b.index == i + 1

    def test_duration(self):
        blocks = parse_srt(SAMPLE_SRT)
        assert blocks[0].duration_sec == 3.0

    def test_html_stripping(self):
        srt = "1\n00:00:01,000 --> 00:00:04,000\n<b>Bold</b> and <i>italic</i> text.\n"
        blocks = parse_srt(srt)
        assert len(blocks) == 1
        assert "<b>" not in blocks[0].text
        assert "Bold" in blocks[0].text


class TestParseVtt:
    def test_basic_parse(self):
        blocks = parse_vtt(SAMPLE_VTT)
        assert len(blocks) == 3
        assert blocks[0].start_sec == 1.0
        assert "detective" in blocks[0].text


class TestParseSubtitles:
    def test_auto_detect_srt(self):
        blocks = parse_subtitles(SAMPLE_SRT)
        assert len(blocks) == 5

    def test_auto_detect_vtt(self):
        blocks = parse_subtitles(SAMPLE_VTT)
        assert len(blocks) == 3


class TestGroupIntoScenes:
    def test_gap_splits_scenes(self):
        blocks = parse_srt(SAMPLE_SRT)
        # Gap between block 3 (end=10.0) and block 4 (start=15.0) is 5.0 > default 3.0
        scenes = group_into_scenes(blocks, gap_threshold_sec=3.0)
        assert len(scenes) >= 2

    def test_no_gap_single_scene(self):
        blocks = parse_srt(SAMPLE_SRT)
        # Very high threshold → all in one scene
        scenes = group_into_scenes(blocks, gap_threshold_sec=100.0)
        assert len(scenes) == 1

    def test_max_duration_splits(self):
        blocks = parse_srt(SAMPLE_SRT)
        # Very short max duration → forces splits
        scenes = group_into_scenes(blocks, gap_threshold_sec=100.0, max_scene_duration_sec=5.0)
        assert len(scenes) >= 2

    def test_empty_input(self):
        scenes = group_into_scenes([])
        assert len(scenes) == 0

    def test_scene_timing(self):
        blocks = parse_srt(SAMPLE_SRT)
        scenes = group_into_scenes(blocks, gap_threshold_sec=3.0)
        for scene in scenes:
            assert scene.start_sec <= scene.end_sec
            assert scene.duration_sec >= 0
            assert len(scene.combined_text) > 0


class TestSrtToNarrativeBpm:
    def test_returns_narrative_bpms(self):
        results = srt_to_narrative_bpm(SAMPLE_SRT)
        assert len(results) >= 1
        for r in results:
            assert hasattr(r, "scene_id")
            assert hasattr(r, "dramatic_function")
            assert hasattr(r, "pendulum_position")

    def test_with_timing(self):
        results = srt_to_narrative_bpm_with_timing(SAMPLE_SRT)
        assert len(results) >= 1
        for r in results:
            assert "start_sec" in r
            assert "end_sec" in r
            assert "duration_sec" in r
            assert "dramatic_function" in r
            assert "confidence" in r

    def test_empty_content(self):
        results = srt_to_narrative_bpm("")
        assert results == []

    def test_vtt_content(self):
        results = srt_to_narrative_bpm(SAMPLE_VTT)
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# 179.20 — Favorite Marker → StorySpacePoint
# ---------------------------------------------------------------------------

class TestMarkersToStorySpace:
    def _make_scores(self, n=5):
        conductor = get_pulse_conductor()
        analyzer = get_script_analyzer()
        text = "\n".join([
            "INT. BATTLEFIELD - DAY",
            "Epic battle with swords and armies.",
            "EXT. GARDEN - NIGHT",
            "A quiet moment of reflection under the moon.",
            "INT. CASTLE - DAWN",
            "The hero celebrates victory.",
            "EXT. DARK FOREST - NIGHT",
            "Evil threatens from the shadows.",
            "INT. THRONE ROOM - DAY",
            "The kingdom is saved.",
        ])
        scenes = analyzer.analyze(text)
        return [conductor.score_scene(scene_id=s.scene_id, narrative=s) for s in scenes]

    def test_basic_mapping(self):
        scores = self._make_scores()
        markers = [
            {"marker_id": "m1", "start_sec": 0.0, "kind": "favorite", "label": "Fav 1", "score": 1.0},
            {"marker_id": "m2", "start_sec": 30.0, "kind": "favorite", "label": "Fav 2", "score": 1.0},
        ]
        points = markers_to_story_space_points(markers, scores)
        assert len(points) == 2
        for p in points:
            assert "marker_id" in p
            assert "camelot_key" in p
            assert "triangle" in p

    def test_with_timing(self):
        scores = self._make_scores()
        markers = [
            {"marker_id": "m1", "start_sec": 5.0, "kind": "favorite"},
        ]
        timings = [
            {"scene_id": "sc_0", "start_sec": 0.0, "end_sec": 10.0},
            {"scene_id": "sc_1", "start_sec": 10.0, "end_sec": 20.0},
            {"scene_id": "sc_2", "start_sec": 20.0, "end_sec": 30.0},
        ]
        points = markers_to_story_space_points(markers, scores, scene_timings=timings)
        assert len(points) == 1
        assert points[0]["aligned_scene_index"] == 0  # 5.0 is in [0, 10]

    def test_empty_markers(self):
        scores = self._make_scores()
        points = markers_to_story_space_points([], scores)
        assert points == []

    def test_empty_scores(self):
        markers = [{"marker_id": "m1", "start_sec": 0.0, "kind": "favorite"}]
        points = markers_to_story_space_points(markers, [])
        assert points == []

    def test_marker_output_fields(self):
        scores = self._make_scores()
        markers = [
            {"marker_id": "m1", "start_sec": 0.0, "kind": "favorite", "label": "Hero moment", "score": 0.9},
        ]
        points = markers_to_story_space_points(markers, scores)
        p = points[0]
        assert p["marker_id"] == "m1"
        assert p["marker_kind"] == "favorite"
        assert p["marker_label"] == "Hero moment"
        assert p["marker_score"] == 0.9
        assert "camelot_angle" in p
        assert "mckee_height" in p
        assert "energy" in p


class TestStorySpacePointSerialization:
    def test_to_dict_complete(self):
        p = StorySpacePoint(
            camelot_key="8A",
            camelot_angle=210.0,
            triangle=TrianglePosition(0.8, 0.1, 0.1),
            pendulum=-0.5,
            energy=0.7,
            confidence=0.8,
            scene_index=3,
            scene_label="Scene 4",
            scale="Aeolian",
        )
        d = p.to_dict()
        assert d["camelot_key"] == "8A"
        assert d["camelot_angle"] == 210.0
        assert d["mckee_height"] == 0.8
        assert d["pendulum"] == -0.5
        assert d["energy"] == 0.7
        assert d["scene_index"] == 3
        assert d["triangle"]["arch"] == 0.8
