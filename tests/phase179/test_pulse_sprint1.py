"""
Phase 179 Sprint 1 tests — PULSE Conductor core modules.

Tests:
- pulse_cinema_matrix.py (179.1)
- pulse_camelot_engine.py (179.2)
- pulse_conductor.py (179.3)
- pulse_script_analyzer.py (179.4)

MARKER_179.T1_SPRINT1_TESTS
"""
import pytest
import sys
import os

# Ensure project root on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ===================================================================
# 179.1 — Cinema Matrix Tests
# ===================================================================


class TestCinemaMatrix:
    """Tests for PulseCinemaMatrix."""

    def test_builtin_loads(self):
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        assert len(m.all_scales()) >= 11  # at least 11 built-in

    def test_get_by_scale_exact(self):
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        row = m.get_by_scale("Phrygian")
        assert row is not None
        assert row.scale == "Phrygian"
        assert row.confidence == 0.94

    def test_get_by_scale_alias(self):
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        # "major" should resolve to Ionian
        row = m.get_by_scale("major")
        assert row is not None
        assert row.scale == "Ionian"

    def test_get_by_scale_minor_alias(self):
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        row = m.get_by_scale("minor")
        assert row is not None
        assert row.scale == "Aeolian"

    def test_get_counterpoint(self):
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        assert m.get_counterpoint("Ionian") == "Aeolian"
        assert m.get_counterpoint("Phrygian") == "Mixolydian"

    def test_get_pendulum(self):
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        assert m.get_pendulum("Locrian") == -1.0
        assert m.get_pendulum("Ionian") == 0.8
        assert m.get_pendulum("Lydian") == 0.8  # corrected by Grok

    def test_grok_corrections_applied(self):
        """Verify Grok 179.0A corrections are in the matrix."""
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        # Lydian: 0.9 → 0.8
        assert m.get_pendulum("Lydian") == 0.8
        # Mixolydian: 0.5 → 0.6
        assert m.get_pendulum("Mixolydian") == 0.6
        # Phrygian: -0.8 → -0.9
        assert m.get_pendulum("Phrygian") == -0.9
        # Harmonic Minor: -0.6 → -0.4
        assert m.get_pendulum("Harmonic Minor") == -0.4
        # Whole Tone: 0.0 → -0.2
        assert m.get_pendulum("Whole Tone") == -0.2

    def test_major_pentatonic_added(self):
        """Grok recommended adding Major Pentatonic."""
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        row = m.get_by_scale("Major Pentatonic")
        assert row is not None
        assert row.pendulum_position == 0.6
        assert row.confidence == 0.87

    def test_get_itten_colors(self):
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        colors = m.get_itten_colors("Ionian")
        assert len(colors) == 7
        assert "Red" in colors

    def test_scales_by_pendulum_range(self):
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        dark = m.scales_by_pendulum_range(-1.0, -0.5)
        assert len(dark) >= 3  # Locrian, Phrygian, Aeolian, Minor Pentatonic, Diminished
        for row in dark:
            assert row.pendulum_position <= -0.5

    def test_scales_by_genre(self):
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        horror = m.scales_by_genre("horror")
        assert len(horror) >= 1
        assert any(r.scale == "Phrygian" for r in horror)

    def test_nearest_by_pendulum(self):
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        # Closest to -1.0 should be Locrian
        row = m.nearest_by_pendulum(-1.0)
        assert row.scale == "Locrian"
        # Closest to 0.8 should be Ionian or Lydian
        row = m.nearest_by_pendulum(0.8)
        assert row.scale in ("Ionian", "Lydian")

    def test_to_dict_list(self):
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        dicts = m.to_dict_list()
        assert len(dicts) >= 11
        assert "scale" in dicts[0]
        assert "pendulum_position" in dicts[0]

    def test_singleton(self):
        from src.services.pulse_cinema_matrix import get_cinema_matrix
        m1 = get_cinema_matrix()
        m2 = get_cinema_matrix()
        assert m1 is m2

    def test_nonexistent_scale(self):
        from src.services.pulse_cinema_matrix import PulseCinemaMatrix
        m = PulseCinemaMatrix()
        assert m.get_by_scale("Nonexistent") is None
        assert m.get_counterpoint("Nonexistent") is None
        assert m.get_pendulum("Nonexistent") is None


# ===================================================================
# 179.2 — Camelot Engine Tests
# ===================================================================


class TestCamelotEngine:
    """Tests for CamelotEngine."""

    def test_distance_same_key(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        assert e.distance("8A", "8A") == 0

    def test_distance_adjacent(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        assert e.distance("8A", "9A") == 1
        assert e.distance("8A", "7A") == 1

    def test_distance_parallel(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        # Same number, different ring = parallel = 1
        assert e.distance("8A", "8B") == 1

    def test_distance_wrap_around(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        # 12A → 1A should be 1 (wrap around)
        assert e.distance("12A", "1A") == 1

    def test_distance_far(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        # 8A → 2A = 6 steps on the circle
        assert e.distance("8A", "2A") == 6

    def test_distance_cross_ring(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        # 8A → 9B = 1 (number) + 1 (ring) = 2
        assert e.distance("8A", "9B") == 2

    def test_compatibility_adjacent(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        assert e.compatibility("8A", "9A") == 1.0  # distance 1

    def test_compatibility_far(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        assert e.compatibility("8A", "2A") <= 0.2  # distance 6

    def test_transition_quality(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        assert e.transition_quality("8A", "8A") == "perfect"
        assert e.transition_quality("8A", "9A") == "harmonic"
        assert e.transition_quality("8A", "10A") == "acceptable"
        assert e.transition_quality("8A", "11A") == "dramatic"

    def test_neighbors(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        nbrs = e.neighbors("8A")
        assert "7A" in nbrs
        assert "9A" in nbrs
        assert "8B" in nbrs
        assert len(nbrs) == 3

    def test_neighbors_wrap(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        nbrs = e.neighbors("1A")
        assert "12A" in nbrs
        assert "2A" in nbrs
        assert "1B" in nbrs

    def test_plan_path_smooth(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        path = e.plan_path(["8A", "9A", "10A", "11A"])
        assert path.total_distance == 3
        assert path.max_jump == 1
        assert path.smoothness == 1.0

    def test_plan_path_dramatic(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        path = e.plan_path(["8A", "2B", "11A"])
        assert path.max_jump >= 3
        assert path.smoothness < 0.8

    def test_plan_path_single(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        path = e.plan_path(["8A"])
        assert path.smoothness == 1.0
        assert path.total_distance == 0

    def test_key_from_musical(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        assert e.key_from_musical("A minor") == "8A"
        assert e.key_from_musical("C major") == "8B"
        assert e.key_from_musical("F# minor") == "11A"

    def test_musical_from_key(self):
        from src.services.pulse_camelot_engine import CamelotEngine
        e = CamelotEngine()
        assert e.musical_from_key("8A") == "A minor"
        assert e.musical_from_key("8B") == "C major"

    def test_camelot_key_parse(self):
        from src.services.pulse_camelot_engine import CamelotKey
        k = CamelotKey.parse("8A")
        assert k.number == 8
        assert k.is_minor
        assert str(k) == "8A"

    def test_camelot_key_parse_invalid(self):
        from src.services.pulse_camelot_engine import CamelotKey
        with pytest.raises(ValueError):
            CamelotKey.parse("13A")
        with pytest.raises(ValueError):
            CamelotKey.parse("8C")

    def test_singleton(self):
        from src.services.pulse_camelot_engine import get_camelot_engine
        e1 = get_camelot_engine()
        e2 = get_camelot_engine()
        assert e1 is e2


# ===================================================================
# 179.3 — PULSE Conductor Tests
# ===================================================================


class TestPulseConductor:
    """Tests for PulseConductor."""

    def test_score_scene_narrative_only(self):
        from src.services.pulse_conductor import PulseConductor, NarrativeBPM
        c = PulseConductor()
        nbpm = NarrativeBPM(
            scene_id="sc_0",
            dramatic_function="Menace",
            pendulum_position=-0.9,
            estimated_energy=0.6,
            keywords=["threat"],
            suggested_scale="Phrygian",
            confidence=0.8,
        )
        score = c.score_scene("sc_0", narrative=nbpm)
        assert score.scale == "Phrygian"
        assert score.pendulum_position == -0.9
        assert score.confidence > 0.0

    def test_score_scene_audio_only(self):
        from src.services.pulse_conductor import PulseConductor, AudioBPM
        c = PulseConductor()
        abpm = AudioBPM(
            bpm=120.0,
            key="A minor",
            camelot_key="8A",
            confidence=0.9,
        )
        score = c.score_scene("sc_1", audio=abpm)
        assert score.camelot_key == "8A"
        assert score.confidence > 0.0

    def test_score_scene_all_three(self):
        from src.services.pulse_conductor import (
            PulseConductor, NarrativeBPM, VisualBPM, AudioBPM,
        )
        c = PulseConductor()
        n = NarrativeBPM(
            scene_id="sc_0", dramatic_function="Victory",
            pendulum_position=0.8, estimated_energy=0.9,
            suggested_scale="Ionian", confidence=0.8,
        )
        v = VisualBPM(
            scene_id="sc_0", cuts_per_minute=15.0,
            motion_intensity=0.7, confidence=0.6,
        )
        a = AudioBPM(
            bpm=130.0, key="C major", camelot_key="8B", confidence=0.9,
        )
        score = c.score_scene("sc_0", narrative=n, visual=v, audio=a)
        assert score.confidence > 0.8  # 3 signals → bonus
        assert score.scale == "Ionian"
        assert score.camelot_key == "8B"

    def test_score_scene_no_signals(self):
        from src.services.pulse_conductor import PulseConductor
        c = PulseConductor()
        score = c.score_scene("sc_empty")
        assert score.confidence == 0.0
        assert score.scale == "Ionian"

    def test_counterpoint_detection(self):
        from src.services.pulse_conductor import PulseConductor, NarrativeBPM, AudioBPM
        c = PulseConductor()
        # Scene in minor (Aeolian), music in major
        n = NarrativeBPM(
            scene_id="sc_0", dramatic_function="Loss",
            pendulum_position=-0.7, estimated_energy=0.3,
            suggested_scale="Aeolian", confidence=0.8,
        )
        a = AudioBPM(
            bpm=100.0, key="C major", camelot_key="8B", confidence=0.9,
        )
        score = c.score_scene("sc_0", narrative=n, audio=a)
        assert score.alignment == "counterpoint"

    def test_sync_detection(self):
        from src.services.pulse_conductor import PulseConductor, NarrativeBPM, AudioBPM
        c = PulseConductor()
        # Both in minor
        n = NarrativeBPM(
            scene_id="sc_0", dramatic_function="Loss",
            pendulum_position=-0.7, estimated_energy=0.3,
            suggested_scale="Aeolian", confidence=0.8,
        )
        a = AudioBPM(
            bpm=80.0, key="A minor", camelot_key="8A", confidence=0.9,
        )
        score = c.score_scene("sc_0", narrative=n, audio=a)
        assert score.alignment == "sync"

    def test_score_film(self):
        from src.services.pulse_conductor import (
            PulseConductor, NarrativeBPM, AudioBPM,
        )
        c = PulseConductor()
        scenes = [
            {
                "scene_id": "sc_0",
                "narrative": NarrativeBPM(
                    scene_id="sc_0", dramatic_function="Mystery",
                    pendulum_position=-0.4, estimated_energy=0.4,
                    suggested_scale="Dorian", confidence=0.7,
                ),
            },
            {
                "scene_id": "sc_1",
                "narrative": NarrativeBPM(
                    scene_id="sc_1", dramatic_function="Victory",
                    pendulum_position=0.8, estimated_energy=0.9,
                    suggested_scale="Ionian", confidence=0.8,
                ),
            },
            {
                "scene_id": "sc_2",
                "narrative": NarrativeBPM(
                    scene_id="sc_2", dramatic_function="Loss",
                    pendulum_position=-0.7, estimated_energy=0.3,
                    suggested_scale="Aeolian", confidence=0.85,
                ),
            },
        ]
        partiture = c.score_film(scenes)
        assert len(partiture.scores) == 3
        assert partiture.tonic_key  # not empty
        assert partiture.camelot_path is not None
        assert partiture.created_at > 0

    def test_score_to_dict(self):
        from src.services.pulse_conductor import PulseConductor, NarrativeBPM
        c = PulseConductor()
        n = NarrativeBPM(
            scene_id="sc_0", dramatic_function="Wonder",
            pendulum_position=0.8, estimated_energy=0.7,
            suggested_scale="Lydian", confidence=0.85,
        )
        score = c.score_scene("sc_0", narrative=n)
        d = score.to_dict()
        assert "camelot_key" in d
        assert "scale" in d
        assert "pendulum_position" in d
        assert "alignment" in d

    def test_partiture_to_dict(self):
        from src.services.pulse_conductor import PulseConductor, NarrativeBPM
        c = PulseConductor()
        scenes = [
            {"scene_id": "sc_0", "narrative": NarrativeBPM(
                scene_id="sc_0", dramatic_function="Epic",
                pendulum_position=0.6, estimated_energy=0.95,
                suggested_scale="Major Pentatonic", confidence=0.9,
            )},
        ]
        p = c.score_film(scenes)
        d = p.to_dict()
        assert "scores" in d
        assert "tonic_key" in d
        assert d["scene_count"] == 1

    def test_confidence_bonus_multiple_signals(self):
        """More signals → higher confidence."""
        from src.services.pulse_conductor import (
            PulseConductor, NarrativeBPM, VisualBPM, AudioBPM,
        )
        c = PulseConductor()
        n = NarrativeBPM(
            scene_id="s", dramatic_function="X",
            pendulum_position=0.0, estimated_energy=0.5,
            confidence=0.7,
        )
        v = VisualBPM(scene_id="s", cuts_per_minute=5.0,
                      motion_intensity=0.5, confidence=0.7)
        a = AudioBPM(bpm=120, key="C major", camelot_key="8B", confidence=0.7)

        s1 = c.score_scene("s", narrative=n)
        s2 = c.score_scene("s", narrative=n, visual=v)
        s3 = c.score_scene("s", narrative=n, visual=v, audio=a)

        assert s3.confidence > s2.confidence > s1.confidence

    def test_singleton(self):
        from src.services.pulse_conductor import get_pulse_conductor
        c1 = get_pulse_conductor()
        c2 = get_pulse_conductor()
        assert c1 is c2


# ===================================================================
# 179.4 — Script Analyzer Tests
# ===================================================================


class TestScriptAnalyzer:
    """Tests for PulseScriptAnalyzer."""

    def test_analyze_single_horror(self):
        from src.services.pulse_script_analyzer import PulseScriptAnalyzer
        a = PulseScriptAnalyzer()
        nbpm = a.analyze_single("Dark ritual in the basement. Evil presence.")
        assert nbpm.pendulum_position < 0
        assert nbpm.suggested_scale == "Phrygian"

    def test_analyze_single_victory(self):
        from src.services.pulse_script_analyzer import PulseScriptAnalyzer
        a = PulseScriptAnalyzer()
        nbpm = a.analyze_single("The hero celebrates victory. Triumph fills the air.")
        assert nbpm.pendulum_position > 0
        assert nbpm.suggested_scale in ("Ionian", "Major Pentatonic")

    def test_analyze_single_neutral(self):
        from src.services.pulse_script_analyzer import PulseScriptAnalyzer
        a = PulseScriptAnalyzer()
        nbpm = a.analyze_single("A man sits at a table.")
        assert nbpm.dramatic_function == "Neutral"
        assert nbpm.confidence < 0.3

    def test_analyze_screenplay_format(self):
        from src.services.pulse_script_analyzer import PulseScriptAnalyzer
        a = PulseScriptAnalyzer()
        script = """INT. DARK ALLEY - NIGHT
The detective walks through shadows. Mystery surrounds him.

EXT. ROOFTOP - DAY
The hero celebrates. Victory! Triumph over evil.

INT. HOSPITAL - NIGHT
She holds his hand. Tears. Farewell.
"""
        results = a.analyze(script)
        assert len(results) == 3
        # First scene: mystery/noir
        assert results[0].pendulum_position < 0
        # Second scene: positive
        assert results[1].pendulum_position > 0
        # Third scene: loss
        assert results[2].pendulum_position < 0

    def test_analyze_russian_text(self):
        from src.services.pulse_script_analyzer import PulseScriptAnalyzer
        a = PulseScriptAnalyzer()
        nbpm = a.analyze_single("Герой побеждает зло. Торжество справедливости.")
        assert nbpm.pendulum_position > 0

    def test_pendulum_monotony_penalty(self):
        """Three consecutive same-sign scenes should get confidence penalty."""
        from src.services.pulse_script_analyzer import PulseScriptAnalyzer
        a = PulseScriptAnalyzer()
        script = """SCENE 1
Chase through the streets. Run! Escape!

SCENE 2
The hero celebrates victory. Triumph!

SCENE 3
Epic battle. Hero wins. Legend!
"""
        results = a.analyze(script)
        assert len(results) >= 3
        # All positive pendulum — last should have reduced confidence
        if all(r.pendulum_position > 0 for r in results[:3]):
            assert results[2].confidence < results[1].confidence

    def test_analyze_empty(self):
        from src.services.pulse_script_analyzer import PulseScriptAnalyzer
        a = PulseScriptAnalyzer()
        results = a.analyze("")
        assert len(results) >= 1  # at least one "neutral" scene

    def test_keywords_extracted(self):
        from src.services.pulse_script_analyzer import PulseScriptAnalyzer
        a = PulseScriptAnalyzer()
        nbpm = a.analyze_single("Horror and blood. Dark ritual. Evil demon.")
        assert len(nbpm.keywords) > 0

    def test_singleton(self):
        from src.services.pulse_script_analyzer import get_script_analyzer
        a1 = get_script_analyzer()
        a2 = get_script_analyzer()
        assert a1 is a2
