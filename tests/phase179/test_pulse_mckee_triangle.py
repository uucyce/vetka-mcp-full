"""
Tests for PULSE McKee Triangle + StorySpace3D (Phase 179.13).

Tests:
  - TrianglePosition normalization and properties
  - Critic weight interpolation at vertices and interior
  - Chaos index computation
  - Triangle-calibrated energy computation
  - Cinema matrix triangle fields
  - Backward compat: genre → triangle mapping
  - StorySpace point conversion
  - 3 Grok validation films through triangle calibration

MARKER_179.13_TESTS
"""
import pytest
from src.services.pulse_story_space import (
    TrianglePosition,
    StorySpacePoint,
    interpolate_critic_weights,
    chaos_index,
    compute_triangle_energies,
    infer_triangle_from_scores,
    scores_to_story_space,
    genre_to_triangle,
    MCKEE_GENRE_TRIANGLES,
)
from src.services.pulse_cinema_matrix import get_cinema_matrix, PulseCinemaMatrix
from src.services.pulse_conductor import (
    PulseScore,
    NarrativeBPM,
    VisualBPM,
    AudioBPM,
)


# ---------------------------------------------------------------------------
# Triangle Position
# ---------------------------------------------------------------------------

class TestTrianglePosition:
    def test_normalization(self):
        """Triangle coordinates auto-normalize to sum=1.0."""
        t = TrianglePosition(2.0, 1.0, 1.0)  # sum=4
        assert abs(t.arch + t.mini + t.anti - 1.0) < 0.01

    def test_already_normalized(self):
        """Coordinates that already sum to 1.0 stay unchanged."""
        t = TrianglePosition(0.5, 0.3, 0.2)
        assert t.arch == 0.5
        assert t.mini == 0.3
        assert t.anti == 0.2

    def test_mckee_height(self):
        """Height = arch weight (0=bottom, 1=top)."""
        t = TrianglePosition(0.9, 0.05, 0.05)
        assert t.mckee_height == 0.9

    def test_dominant_archplot(self):
        t = TrianglePosition(0.8, 0.1, 0.1)
        assert t.dominant == "archplot"

    def test_dominant_miniplot(self):
        t = TrianglePosition(0.2, 0.6, 0.2)
        assert t.dominant == "miniplot"

    def test_dominant_antiplot(self):
        t = TrianglePosition(0.1, 0.1, 0.8)
        assert t.dominant == "antiplot"

    def test_to_dict(self):
        t = TrianglePosition(0.7, 0.2, 0.1)
        d = t.to_dict()
        assert d == {"arch": 0.7, "mini": 0.2, "anti": 0.1}


# ---------------------------------------------------------------------------
# Critic Weight Interpolation
# ---------------------------------------------------------------------------

class TestCriticInterpolation:
    def test_pure_archplot(self):
        """At archplot vertex, pendulum_balance = 1.0, chaos_tolerance = 0.0."""
        t = TrianglePosition(1.0, 0.0, 0.0)
        w = interpolate_critic_weights(t)
        assert w["pendulum_balance"] == 1.0
        assert w["chaos_tolerance"] == 0.0

    def test_pure_miniplot(self):
        """At miniplot vertex, pendulum_balance = 0.4, counterpoint_penalty = 0.1."""
        t = TrianglePosition(0.0, 1.0, 0.0)
        w = interpolate_critic_weights(t)
        assert w["pendulum_balance"] == 0.4
        assert w["counterpoint_penalty"] == 0.1

    def test_pure_antiplot(self):
        """At antiplot vertex, pendulum_balance = 0.0, chaos_tolerance = 1.0."""
        t = TrianglePosition(0.0, 0.0, 1.0)
        w = interpolate_critic_weights(t)
        assert w["pendulum_balance"] == 0.0
        assert w["chaos_tolerance"] == 1.0

    def test_center_interpolation(self):
        """Center of triangle = average of all vertices."""
        t = TrianglePosition(0.33, 0.34, 0.33)
        w = interpolate_critic_weights(t)
        # Pendulum: 0.33*1.0 + 0.34*0.4 + 0.33*0.0 ≈ 0.466
        assert 0.4 < w["pendulum_balance"] < 0.5

    def test_weights_are_bounded(self):
        """All interpolated weights should be in [0, 1]."""
        for arch in [0.0, 0.33, 0.5, 0.8, 1.0]:
            for mini in [0.0, 0.33, 0.5]:
                anti = max(0.0, 1.0 - arch - mini)
                if anti < 0:
                    continue
                t = TrianglePosition(arch, mini, anti)
                w = interpolate_critic_weights(t)
                for k, v in w.items():
                    assert 0.0 <= v <= 1.0, f"{k}={v} out of bounds for ({arch},{mini},{anti})"


# ---------------------------------------------------------------------------
# Chaos Index
# ---------------------------------------------------------------------------

class TestChaosIndex:
    def _make_score(self, key="1A", pendulum=0.0, energy=0.5, scale="Ionian"):
        return PulseScore(
            scene_id="0",
            scale=scale,
            camelot_key=key,
            pendulum_position=pendulum,
            dramatic_function="", energy_profile="", counterpoint_pair="",
            alignment="sync",
            confidence=0.8,
            narrative_bpm=NarrativeBPM(
                scene_id="0",
                dramatic_function="",
                pendulum_position=pendulum,
                estimated_energy=energy,
            ),
            visual_bpm=None,
            audio_bpm=None,
        )

    def test_smooth_path_low_chaos(self):
        """Adjacent keys, smooth pendulum → low chaos."""
        scores = [
            self._make_score("1A", -0.3, 0.3),
            self._make_score("2A", -0.1, 0.4),
            self._make_score("3A", 0.1, 0.5),
            self._make_score("4A", 0.3, 0.6),
        ]
        c = chaos_index(scores)
        assert c < 0.3, f"Expected low chaos, got {c}"

    def test_erratic_path_high_chaos(self):
        """Wild key jumps, erratic pendulum → high chaos."""
        scores = [
            self._make_score("1A", -0.9, 0.1),
            self._make_score("7A", 0.8, 0.9),
            self._make_score("2A", -0.7, 0.2),
            self._make_score("10A", 0.9, 0.8),
            self._make_score("3A", -0.8, 0.1),
        ]
        c = chaos_index(scores)
        assert c > 0.3, f"Expected high chaos, got {c}"

    def test_too_few_scores(self):
        """Less than 3 scores → 0 chaos."""
        scores = [self._make_score("1A"), self._make_score("2A")]
        assert chaos_index(scores) == 0.0


# ---------------------------------------------------------------------------
# Triangle-Calibrated Energies
# ---------------------------------------------------------------------------

class TestTriangleCalibratedEnergies:
    def _build_scores(self, keys, pendulums, energies):
        scores = []
        for i, (k, p, e) in enumerate(zip(keys, pendulums, energies)):
            scores.append(PulseScore(
                scene_id=str(i),
                scale="Ionian" if p > 0 else "Aeolian",
                camelot_key=k,
                pendulum_position=p,
                dramatic_function="", energy_profile="", counterpoint_pair="",
                alignment="sync" if i % 2 == 0 else "counterpoint",
                confidence=0.8,
                narrative_bpm=NarrativeBPM(
                    scene_id=str(i),
                    dramatic_function="",
                    pendulum_position=p,
                    estimated_energy=e,
                ),
                visual_bpm=VisualBPM(
                    scene_id=str(i),
                    cuts_per_minute=e * 20,
                    motion_intensity=e,
                ),
                audio_bpm=None,
            ))
        return scores

    def test_archplot_full_critics(self):
        """Archplot triangle → critics at full strength."""
        scores = self._build_scores(
            ["1A", "2A", "3A", "4A", "5A"],
            [-0.5, 0.3, -0.7, 0.6, -0.2],
            [0.3, 0.5, 0.7, 0.9, 0.4],
        )
        result = compute_triangle_energies(scores, TrianglePosition(0.9, 0.05, 0.05))
        assert result["dominant_vertex"] == "archplot"
        assert result["mckee_height"] > 0.8
        # Pendulum weight should be close to 1.0
        assert result["weights"]["pendulum_balance"] > 0.8

    def test_antiplot_chaos_tolerated(self):
        """Antiplot triangle → chaos_index reduced, pendulum off."""
        scores = self._build_scores(
            ["1A", "7A", "3A", "10A", "5A"],
            [-0.9, 0.8, -0.7, 0.9, -0.8],
            [0.1, 0.9, 0.2, 0.8, 0.1],
        )
        result = compute_triangle_energies(scores, TrianglePosition(0.1, 0.1, 0.8))
        assert result["dominant_vertex"] == "antiplot"
        # Chaos should be high raw but low calibrated (tolerated)
        assert result["raw"]["chaos_index"] > 0.3
        assert result["calibrated"]["chaos_index"] < result["raw"]["chaos_index"]
        # Pendulum balance should be near 0 (weight ≈ 0)
        assert result["weights"]["pendulum_balance"] < 0.15

    def test_miniplot_counterpoint_tolerated(self):
        """Miniplot → counterpoint penalty very low."""
        scores = self._build_scores(
            ["8A", "8B", "9A", "9B", "8A"],
            [-0.3, 0.2, -0.4, 0.1, -0.2],
            [0.3, 0.4, 0.3, 0.35, 0.3],
        )
        result = compute_triangle_energies(scores, TrianglePosition(0.2, 0.7, 0.1))
        assert result["dominant_vertex"] == "miniplot"
        assert result["weights"]["counterpoint_penalty"] < 0.25

    def test_result_structure(self):
        """Result should have all expected fields."""
        scores = self._build_scores(["1A", "2A", "3A"], [0, 0.5, -0.5], [0.5, 0.5, 0.5])
        result = compute_triangle_energies(scores, TrianglePosition(0.5, 0.3, 0.2))
        assert "triangle_position" in result
        assert "dominant_vertex" in result
        assert "mckee_height" in result
        assert "raw" in result
        assert "calibrated" in result
        assert "weights" in result
        assert "interpretation" in result
        assert "chaos_index" in result["raw"]
        assert "chaos_index" in result["calibrated"]

    def test_infer_triangle_from_scores(self):
        """Triangle position should be inferred from scales in scores."""
        scores = self._build_scores(
            ["1A", "2A", "3A"],
            [0.8, 0.6, 0.9],
            [0.5, 0.7, 0.9],
        )
        # All Ionian (positive pendulums) → archplot dominant
        tri = infer_triangle_from_scores(scores)
        assert tri.arch > 0.5, f"Expected archplot dominant, got {tri.to_dict()}"


# ---------------------------------------------------------------------------
# Cinema Matrix Triangle Fields
# ---------------------------------------------------------------------------

class TestCinemaMatrixTriangle:
    def test_all_scales_have_triangle(self):
        """Every scale in the matrix should have triangle coordinates."""
        matrix = PulseCinemaMatrix()
        for row in matrix.all_scales():
            total = row.triangle_arch + row.triangle_mini + row.triangle_anti
            assert abs(total - 1.0) < 0.01, f"{row.scale}: triangle sum={total}"

    def test_locrian_is_antiplot(self):
        """Locrian (madness/chaos) should be antiplot-dominant."""
        matrix = PulseCinemaMatrix()
        row = matrix.get_by_scale("Locrian")
        assert row.triangle_anti > 0.5

    def test_ionian_is_archplot(self):
        """Ionian (victory/resolution) should be archplot-dominant."""
        matrix = PulseCinemaMatrix()
        row = matrix.get_by_scale("Ionian")
        assert row.triangle_arch > 0.5

    def test_dorian_is_miniplot(self):
        """Dorian (noir/detective) should lean miniplot."""
        matrix = PulseCinemaMatrix()
        row = matrix.get_by_scale("Dorian")
        assert row.triangle_mini >= row.triangle_arch

    def test_japanese_is_miniplot_dominant(self):
        """Japanese (In Sen) should be strongly miniplot."""
        matrix = PulseCinemaMatrix()
        row = matrix.get_by_scale("Japanese")
        assert row is not None
        assert row.triangle_mini >= 0.6

    def test_get_triangle_position(self):
        """get_triangle_position should return (arch, mini, anti) tuple."""
        matrix = PulseCinemaMatrix()
        pos = matrix.get_triangle_position("Ionian")
        assert pos is not None
        assert len(pos) == 3
        assert abs(sum(pos) - 1.0) < 0.01

    def test_scales_by_triangle_region(self):
        """Filter scales by triangle region."""
        matrix = PulseCinemaMatrix()
        antiplot_scales = matrix.scales_by_triangle_region(min_anti=0.5)
        assert len(antiplot_scales) >= 2  # at least Locrian and Chromatic
        for row in antiplot_scales:
            assert row.triangle_anti >= 0.5

    def test_new_scales_exist(self):
        """New scales from CSV should be in the builtin matrix."""
        matrix = PulseCinemaMatrix()
        new_scales = ["Minor Blues", "Major Blues", "Gypsy", "Arabic", "Spanish",
                      "Japanese", "Egyptian", "Phrygian Dominant", "Raga Bhairav", "Melodic Minor"]
        for scale in new_scales:
            row = matrix.get_by_scale(scale)
            assert row is not None, f"Missing scale: {scale}"

    def test_to_dict_includes_triangle(self):
        """Serialized dict should include triangle_position."""
        matrix = PulseCinemaMatrix()
        dicts = matrix.to_dict_list()
        for d in dicts:
            assert "triangle_position" in d
            tri = d["triangle_position"]
            assert "arch" in tri
            assert "mini" in tri
            assert "anti" in tri

    def test_total_scales_count(self):
        """Should have 23 scales (7 modes + 16 extended)."""
        matrix = PulseCinemaMatrix()
        scales = matrix.all_scales()
        assert len(scales) >= 23, f"Expected >= 23 scales, got {len(scales)}"


# ---------------------------------------------------------------------------
# Genre → Triangle Backward Compatibility
# ---------------------------------------------------------------------------

class TestGenreTriangleMapping:
    def test_old_genres_mapped(self):
        """All 7 old genre profiles should have triangle equivalents."""
        old_genres = ["drama", "action", "art_house", "surreal", "horror", "comedy", "documentary"]
        for genre in old_genres:
            tri = genre_to_triangle(genre)
            assert abs(tri.arch + tri.mini + tri.anti - 1.0) < 0.01

    def test_mckee_genres_mapped(self):
        """McKee's additional genres should be available."""
        assert "love_story" in MCKEE_GENRE_TRIANGLES
        assert "crime" in MCKEE_GENRE_TRIANGLES
        assert "disillusionment" in MCKEE_GENRE_TRIANGLES

    def test_unknown_genre_returns_default(self):
        """Unknown genre → default mild archplot."""
        tri = genre_to_triangle("totally_unknown_genre_xyz")
        assert tri.arch == 0.5
        assert tri.mini == 0.3
        assert tri.anti == 0.2


# ---------------------------------------------------------------------------
# Story Space Point Conversion
# ---------------------------------------------------------------------------

class TestStorySpaceConversion:
    def test_scores_to_story_space(self):
        """PulseScores should convert to StorySpacePoints."""
        scores = [
            PulseScore(
                scene_id="0",
                scale="Ionian",
                camelot_key="8B",
                pendulum_position=0.7,
                dramatic_function="Catharsis", energy_profile="peak", counterpoint_pair="Aeolian",
                alignment="sync",
                confidence=0.9,
                narrative_bpm=NarrativeBPM(
                    scene_id="0",
                    dramatic_function="Catharsis",
                    pendulum_position=0.7,
                    estimated_energy=0.8,
                ),
                visual_bpm=None,
                audio_bpm=None,
            ),
        ]
        points = scores_to_story_space(scores)
        assert len(points) == 1
        p = points[0]
        assert p.camelot_key == "8B"
        assert p.camelot_angle == 210.0  # 8B → 210°
        assert p.pendulum == 0.7
        assert p.triangle.arch > 0.5  # Ionian = archplot
        assert p.energy == 0.8

    def test_point_to_dict(self):
        """StorySpacePoint should serialize cleanly."""
        p = StorySpacePoint(
            camelot_key="3A",
            camelot_angle=60.0,
            triangle=TrianglePosition(0.8, 0.1, 0.1),
            pendulum=0.5,
            energy=0.7,
        )
        d = p.to_dict()
        assert d["camelot_key"] == "3A"
        assert d["camelot_angle"] == 60.0
        assert d["mckee_height"] == 0.8
        assert d["pendulum"] == 0.5


# ---------------------------------------------------------------------------
# Grok Film Validation through Triangle
# ---------------------------------------------------------------------------

class TestGrokFilmsTriangle:
    """
    Validate that triangle calibration fixes the issues Grok found:
    - Cabiria: miniplot should tolerate counterpoint
    - Mad Max: archplot-extreme should tolerate sustained energy
    - Mulholland: antiplot should tolerate chaos
    """

    def _ps(self, sid, scale, key, pend, align, conf, text, energy, bpm, kw, vis_cuts, vis_motion):
        """Helper to create PulseScore with all required fields."""
        return PulseScore(
            scene_id=sid, scale=scale, camelot_key=key,
            pendulum_position=pend,
            dramatic_function="", energy_profile="", counterpoint_pair="",
            alignment=align, confidence=conf,
            narrative_bpm=NarrativeBPM(
                scene_id=sid, dramatic_function="",
                pendulum_position=pend, estimated_energy=energy,
            ),
            visual_bpm=VisualBPM(
                scene_id=sid, cuts_per_minute=vis_cuts, motion_intensity=vis_motion,
            ),
            audio_bpm=None,
        )

    def _cabiria_scores(self):
        """Nights of Cabiria — miniplot dominant, counterpoint finale."""
        return [
            self._ps("c0", "Aeolian", "8A", -0.8, "sync", 0.85, "Pushed off cliff", 0.7, 90, ["betrayal"], 6.0, 0.4),
            self._ps("c1", "Dorian", "9A", -0.3, "sync", 0.80, "Night streets", 0.4, 85, ["loneliness"], 4.0, 0.3),
            self._ps("c2", "Ionian", "8B", 0.5, "sync", 0.82, "Meeting Giorgio", 0.5, 95, ["hope"], 5.0, 0.35),
            self._ps("c3", "Aeolian", "8A", -0.7, "sync", 0.85, "Robbery", 0.6, 100, ["betrayal"], 8.0, 0.5),
            self._ps("c4", "Ionian", "8B", 0.6, "counterpoint", 0.88, "Tears and smile", 0.5, 90, ["irony"], 3.0, 0.25),
        ]

    def _mad_max_scores(self):
        """Mad Max: Fury Road — archplot extreme, sustained high energy."""
        return [
            self._ps(f"mm{i}", "Mixolydian", f"{(i%4)+1}B", 0.2+0.1*i, "sync", 0.85,
                     f"Chase {i}", 0.7+0.05*i, 140, ["chase"], 15.0+i, 0.8+0.02*i)
            for i in range(6)
        ]

    def _mulholland_scores(self):
        """Mulholland Drive — antiplot, chaotic transitions."""
        keys = ["1A", "7A", "3B", "10A", "5B", "12A"]
        pends = [-0.9, 0.7, -0.5, 0.8, -0.8, 0.3]
        scales = ["Chromatic", "Locrian", "Whole Tone", "Phrygian", "Chromatic", "Locrian"]
        return [
            self._ps(f"md{i}", scales[i], keys[i], pends[i],
                     "counterpoint" if i % 2 else "sync", 0.75,
                     f"Fragment {i}", 0.3+0.4*(i%2), 100, ["dream"], 3+10*(i%2), 0.2+0.6*(i%2))
            for i in range(6)
        ]

    def test_cabiria_miniplot_calibration(self):
        """Cabiria as miniplot: counterpoint should be tolerated."""
        scores = self._cabiria_scores()
        # Miniplot dominant
        result = compute_triangle_energies(scores, TrianglePosition(0.3, 0.6, 0.1))
        cal = result["calibrated"]

        # Calibrated total should be reasonable (not flagged as "extreme")
        assert cal["total"] < 0.5, f"Cabiria miniplot total too high: {cal['total']}"
        # Counterpoint penalty weight should be very low
        assert result["weights"]["counterpoint_penalty"] < 0.25

    def test_mad_max_archplot_sustained(self):
        """Mad Max as archplot: sustained energy should be acceptable."""
        scores = self._mad_max_scores()
        result = compute_triangle_energies(scores, TrianglePosition(0.85, 0.1, 0.05))

        assert result["dominant_vertex"] == "archplot"
        # Energy contour weight: interpolated 0.85*0.7 + 0.1*0.3 + 0.05*0.2 ≈ 0.635
        assert result["weights"]["energy_contour"] > 0.6
        assert result["weights"]["energy_contour"] < 0.8

    def test_mulholland_antiplot_chaos(self):
        """Mulholland as antiplot: chaos should be tolerated."""
        scores = self._mulholland_scores()
        result = compute_triangle_energies(scores, TrianglePosition(0.1, 0.1, 0.8))

        assert result["dominant_vertex"] == "antiplot"
        # Raw chaos should be high
        assert result["raw"]["chaos_index"] > 0.2
        # Calibrated chaos should be much lower (chaos_tolerance=1.0 → weight=0.0)
        assert result["calibrated"]["chaos_index"] < result["raw"]["chaos_index"]
        # Pendulum balance weight should be ~0
        assert result["weights"]["pendulum_balance"] < 0.15
