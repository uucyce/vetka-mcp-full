"""
PULSE Sprint 2 Tests — REST endpoints, Energy Critics, Counterpoint.

MARKER_179.9_SPRINT2_TESTS
"""
import pytest
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# REST endpoint tests (unit-level, no HTTP server needed — test logic directly)
# ---------------------------------------------------------------------------
from src.services.pulse_cinema_matrix import get_cinema_matrix, CinemaMatrixRow
from src.services.pulse_camelot_engine import (
    CamelotEngine,
    CamelotKey,
    get_camelot_engine,
)
from src.services.pulse_conductor import (
    NarrativeBPM,
    VisualBPM,
    AudioBPM,
    PulseScore,
    FilmPartiture,
    PulseConductor,
    get_pulse_conductor,
)
from src.services.pulse_script_analyzer import (
    PulseScriptAnalyzer,
    get_script_analyzer,
)


# =====================================================================
# 179.5 — REST endpoint logic tests (exercise the same code paths)
# =====================================================================

class TestPulseEndpointLogic:
    """Test the logic behind PULSE REST endpoints without HTTP."""

    def test_matrix_returns_all_scales(self):
        matrix = get_cinema_matrix()
        scales = matrix.to_dict_list()
        assert len(scales) >= 11  # at least 11 built-in + major pentatonic
        for s in scales:
            assert "scale" in s
            assert "pendulum_position" in s

    def test_matrix_by_scale_ionian(self):
        matrix = get_cinema_matrix()
        row = matrix.get_by_scale("Ionian")
        assert row is not None
        assert row.cinema_genre == "Drama / happy end"
        assert row.camelot_region == "B"

    def test_matrix_by_scale_not_found(self):
        matrix = get_cinema_matrix()
        row = matrix.get_by_scale("NonexistentScale")
        assert row is None

    def test_score_scene_script_only(self):
        conductor = get_pulse_conductor()
        analyzer = get_script_analyzer()
        nbpm = analyzer.analyze_single("The hero wins the battle in triumph")
        score = conductor.score_scene("test_1", narrative=nbpm)
        assert score.scene_id == "test_1"
        assert score.confidence > 0
        assert score.scale != ""

    def test_score_scene_all_three_signals(self):
        conductor = get_pulse_conductor()
        narrative = NarrativeBPM(
            scene_id="sc_0",
            dramatic_function="Menace",
            pendulum_position=-0.9,
            estimated_energy=0.6,
            suggested_scale="Phrygian",
            confidence=0.8,
        )
        visual = VisualBPM(
            scene_id="sc_0",
            cuts_per_minute=3.0,
            motion_intensity=0.2,
            confidence=0.7,
        )
        audio = AudioBPM(
            bpm=90.0,
            key="A minor",
            camelot_key="8A",
            confidence=0.9,
        )
        score = conductor.score_scene("sc_0", narrative=narrative, visual=visual, audio=audio)
        assert score.confidence > 0.7  # 3-signal bonus
        assert score.camelot_key == "8A"  # audio provides key
        assert score.alignment in ("sync", "counterpoint", "polyphonic")

    def test_score_film_from_script(self):
        conductor = get_pulse_conductor()
        analyzer = get_script_analyzer()
        script = (
            "INT. DARK ALLEY - NIGHT\n"
            "The detective investigates the mystery clue.\n\n"
            "EXT. BATTLEFIELD - DAY\n"
            "The hero fights an epic battle. Victory is near.\n\n"
            "INT. FUNERAL HOME - NIGHT\n"
            "Tears and grief. A farewell to a lost friend.\n"
        )
        scenes_bpm = analyzer.analyze(script)
        scene_dicts = [
            {"scene_id": s.scene_id, "narrative": s}
            for s in scenes_bpm
        ]
        partiture = conductor.score_film(scene_dicts)
        assert len(partiture.scores) == 3
        # Should oscillate (mystery=-ve, epic=+ve, loss=-ve)
        pendulums = [s.pendulum_position for s in partiture.scores]
        assert any(p < 0 for p in pendulums)
        assert any(p > 0 for p in pendulums)

    def test_camelot_path_analysis(self):
        engine = get_camelot_engine()
        path = engine.plan_path(["8A", "9A", "3B", "8A"])
        assert path.total_distance > 0
        assert path.max_jump > 0
        assert 0.0 <= path.smoothness <= 1.0
        assert len(path.transitions) == 3

    def test_camelot_distance_same_key(self):
        engine = get_camelot_engine()
        assert engine.distance("8A", "8A") == 0
        assert engine.compatibility("8A", "8A") == 1.0

    def test_camelot_neighbors_count(self):
        engine = get_camelot_engine()
        nbrs = engine.neighbors("8A")
        assert len(nbrs) == 3  # ±1 same ring + parallel
        assert "8B" in nbrs  # parallel key

    def test_camelot_suggest_next(self):
        engine = get_camelot_engine()
        suggestions = engine.suggest_next("8A", target_pendulum=0.8)
        assert len(suggestions) > 0
        # First suggestion should have highest score
        scores = [s[1] for s in suggestions]
        assert scores == sorted(scores, reverse=True)

    def test_analyze_script_returns_scenes(self):
        analyzer = get_script_analyzer()
        results = analyzer.analyze("INT. CLUB\nThe detective investigates.\nEXT. PARK\nA hero celebrates victory.")
        assert len(results) >= 1
        for r in results:
            assert r.scene_id.startswith("sc_")
            assert r.dramatic_function != ""


# =====================================================================
# 179.6 — Energy Critics tests
# =====================================================================

class TestEnergyCritics:
    """Test the 5 LeCun-inspired energy critics."""

    def setup_method(self):
        """Import energy critics module."""
        from src.services.pulse_energy_critics import (
            music_scene_sync_energy,
            pendulum_balance_energy,
            camelot_proximity_energy,
            script_visual_match_energy,
            energy_contour_energy,
            compute_all_energies,
        )
        self._music_scene_sync = music_scene_sync_energy
        self._pendulum_balance = pendulum_balance_energy
        self._camelot_proximity = camelot_proximity_energy
        self._script_visual_match = script_visual_match_energy
        self._energy_contour = energy_contour_energy
        self._compute_all = compute_all_energies

    def test_music_scene_sync_perfect_match(self):
        """Scene in minor + music in minor = low energy (good sync)."""
        score = PulseScore(
            scene_id="s1", camelot_key="8A", scale="Aeolian",
            pendulum_position=-0.7, dramatic_function="Loss",
            energy_profile="low_sustained", counterpoint_pair="Ionian",
            confidence=0.8, alignment="sync",
        )
        energy = self._music_scene_sync(score)
        assert 0.0 <= energy <= 1.0
        assert energy < 0.3  # sync = low energy (compatible)

    def test_music_scene_sync_counterpoint(self):
        """Scene in minor + music in major = high energy (tension)."""
        score = PulseScore(
            scene_id="s1", camelot_key="8B", scale="Aeolian",
            pendulum_position=-0.7, dramatic_function="Loss",
            energy_profile="low_sustained", counterpoint_pair="Ionian",
            confidence=0.8, alignment="counterpoint",
        )
        energy = self._music_scene_sync(score)
        assert energy > 0.5  # counterpoint = higher energy

    def test_pendulum_balance_oscillating(self):
        """Properly oscillating pendulum = low energy (balanced)."""
        scores = [
            PulseScore(scene_id=f"s{i}", camelot_key="8A", scale="Aeolian",
                       pendulum_position=p, dramatic_function="", energy_profile="",
                       counterpoint_pair="", confidence=0.8)
            for i, p in enumerate([-0.7, 0.5, -0.3, 0.8, -0.5])
        ]
        energy = self._pendulum_balance(scores)
        assert energy < 0.4  # good oscillation

    def test_pendulum_balance_monotone(self):
        """All same-sign pendulum = high energy (monotonous = bad)."""
        scores = [
            PulseScore(scene_id=f"s{i}", camelot_key="8A", scale="Aeolian",
                       pendulum_position=p, dramatic_function="", energy_profile="",
                       counterpoint_pair="", confidence=0.8)
            for i, p in enumerate([-0.7, -0.5, -0.3, -0.8, -0.6])
        ]
        energy = self._pendulum_balance(scores)
        assert energy > 0.6  # monotonous = high energy (bad)

    def test_camelot_proximity_smooth(self):
        """Adjacent keys = low energy (smooth transitions)."""
        scores = [
            PulseScore(scene_id=f"s{i}", camelot_key=k, scale="",
                       pendulum_position=0.0, dramatic_function="", energy_profile="",
                       counterpoint_pair="", confidence=0.8)
            for i, k in enumerate(["8A", "9A", "8B", "9B"])
        ]
        energy = self._camelot_proximity(scores)
        assert energy < 0.3  # smooth harmonic path

    def test_camelot_proximity_jarring(self):
        """Distant keys = high energy (jarring transitions)."""
        scores = [
            PulseScore(scene_id=f"s{i}", camelot_key=k, scale="",
                       pendulum_position=0.0, dramatic_function="", energy_profile="",
                       counterpoint_pair="", confidence=0.8)
            for i, k in enumerate(["1A", "7B", "3A", "11B"])
        ]
        energy = self._camelot_proximity(scores)
        assert energy > 0.5  # jarring transitions

    def test_script_visual_match_high_energy_match(self):
        """Action scene + high motion = low energy (good match)."""
        narrative = NarrativeBPM(
            scene_id="s1", dramatic_function="Adventure",
            pendulum_position=0.6, estimated_energy=0.85,
            confidence=0.8,
        )
        visual = VisualBPM(
            scene_id="s1", cuts_per_minute=15.0,
            motion_intensity=0.9, confidence=0.7,
        )
        energy = self._script_visual_match(narrative, visual)
        assert energy < 0.4  # good match

    def test_script_visual_match_mismatch(self):
        """Loss scene + high motion = high energy (mismatch)."""
        narrative = NarrativeBPM(
            scene_id="s1", dramatic_function="Loss",
            pendulum_position=-0.7, estimated_energy=0.3,
            confidence=0.8,
        )
        visual = VisualBPM(
            scene_id="s1", cuts_per_minute=20.0,
            motion_intensity=0.95, confidence=0.7,
        )
        energy = self._script_visual_match(narrative, visual)
        assert energy > 0.4  # mismatch

    def test_energy_contour_smooth(self):
        """Gradual energy changes = low contour energy."""
        energies = [0.3, 0.35, 0.4, 0.5, 0.55, 0.6]
        energy = self._energy_contour(energies)
        assert energy < 0.3  # smooth contour

    def test_energy_contour_spiky(self):
        """Wild energy jumps = high contour energy."""
        energies = [0.1, 0.9, 0.2, 0.95, 0.1, 0.85]
        energy = self._energy_contour(energies)
        assert energy > 0.5  # spiky = bad

    def test_compute_all_energies(self):
        """Integration: compute_all_energies returns dict of all 5."""
        scores = [
            PulseScore(
                scene_id="s0", camelot_key="8A", scale="Aeolian",
                pendulum_position=-0.5, dramatic_function="Mystery",
                energy_profile="low_sustained", counterpoint_pair="Ionian",
                confidence=0.8, alignment="sync",
                narrative_bpm=NarrativeBPM(
                    scene_id="s0", dramatic_function="Mystery",
                    pendulum_position=-0.5, estimated_energy=0.4, confidence=0.8,
                ),
                visual_bpm=VisualBPM(
                    scene_id="s0", cuts_per_minute=5.0,
                    motion_intensity=0.3, confidence=0.6,
                ),
            ),
        ]
        result = self._compute_all(scores)
        assert "music_scene_sync" in result
        assert "pendulum_balance" in result
        assert "camelot_proximity" in result
        assert "script_visual_match" in result
        assert "energy_contour" in result
        assert "total" in result
        assert 0.0 <= result["total"] <= 1.0


# =====================================================================
# 179.7 — Counterpoint detector (enhanced)
# =====================================================================

class TestCounterpointDetection:
    """Test counterpoint detection edge cases."""

    def test_nights_of_cabiria_pattern(self):
        """Classic: scene Aeolian (minor) + music in parallel major."""
        conductor = get_pulse_conductor()
        narrative = NarrativeBPM(
            scene_id="cabiria",
            dramatic_function="Loss",
            pendulum_position=-0.7,
            estimated_energy=0.3,
            suggested_scale="Aeolian",
            confidence=0.9,
        )
        audio = AudioBPM(
            bpm=100.0,
            key="C major",
            camelot_key="8B",  # major ring, parallel to 8A
            confidence=0.9,
        )
        score = conductor.score_scene("cabiria", narrative=narrative, audio=audio)
        assert score.alignment == "counterpoint"

    def test_sync_when_modes_match(self):
        """Scene minor + music minor = sync."""
        conductor = get_pulse_conductor()
        narrative = NarrativeBPM(
            scene_id="sync_test",
            dramatic_function="Mystery",
            pendulum_position=-0.4,
            estimated_energy=0.4,
            suggested_scale="Dorian",
            confidence=0.8,
        )
        audio = AudioBPM(
            bpm=110.0,
            key="A minor",
            camelot_key="8A",
            confidence=0.8,
        )
        score = conductor.score_scene("sync_test", narrative=narrative, audio=audio)
        assert score.alignment == "sync"

    def test_no_audio_defaults_sync(self):
        """Without audio signal, default to sync."""
        conductor = get_pulse_conductor()
        narrative = NarrativeBPM(
            scene_id="no_audio",
            dramatic_function="Victory",
            pendulum_position=0.8,
            estimated_energy=0.9,
            suggested_scale="Ionian",
            confidence=0.8,
        )
        score = conductor.score_scene("no_audio", narrative=narrative)
        assert score.alignment == "sync"

    def test_major_scene_minor_music_counterpoint(self):
        """Scene Ionian (major) + music in minor = counterpoint."""
        conductor = get_pulse_conductor()
        narrative = NarrativeBPM(
            scene_id="reverse",
            dramatic_function="Victory",
            pendulum_position=0.8,
            estimated_energy=0.9,
            suggested_scale="Ionian",
            confidence=0.9,
        )
        audio = AudioBPM(
            bpm=120.0,
            key="A minor",
            camelot_key="8A",  # minor
            confidence=0.8,
        )
        score = conductor.score_scene("reverse", narrative=narrative, audio=audio)
        assert score.alignment == "counterpoint"
