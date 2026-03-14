"""
PULSE Genre-Aware Calibration Tests — validated via Grok on 3 films.

Tests that genre calibration correctly adjusts energy critics:
- Nights of Cabiria (art_house): counterpoint is tolerated
- Mad Max: Fury Road (action): sustained energy is tolerated
- Mulholland Drive (surreal): chaos is tolerated

MARKER_179.12_GENRE_CALIBRATION_TESTS
"""
import pytest
from typing import Dict, List

from src.services.pulse_energy_critics import (
    compute_all_energies,
    compute_calibrated_energies,
    list_genre_profiles,
    GENRE_PROFILES,
    GenreCalibrationProfile,
    music_scene_sync_energy,
    pendulum_balance_energy,
    camelot_proximity_energy,
    energy_contour_energy,
)
from src.services.pulse_conductor import (
    PulseScore,
    NarrativeBPM,
    VisualBPM,
    AudioBPM,
    PulseConductor,
    get_pulse_conductor,
)
from src.services.pulse_script_analyzer import get_script_analyzer


# =====================================================================
# Genre Profile Tests
# =====================================================================

class TestGenreProfiles:
    """Test genre calibration profile infrastructure."""

    def test_all_profiles_exist(self):
        assert len(GENRE_PROFILES) >= 7
        for genre in ["drama", "action", "art_house", "surreal", "horror", "comedy", "documentary"]:
            assert genre in GENRE_PROFILES

    def test_profile_multipliers_in_range(self):
        for name, profile in GENRE_PROFILES.items():
            for field in ["music_scene_sync", "pendulum_balance", "camelot_proximity",
                          "script_visual_match", "energy_contour"]:
                val = getattr(profile, field)
                assert 0.0 <= val <= 2.0, f"{name}.{field} = {val} out of range"

    def test_drama_is_neutral(self):
        """Drama profile should be all 1.0 (baseline)."""
        p = GENRE_PROFILES["drama"]
        assert p.music_scene_sync == 1.0
        assert p.pendulum_balance == 1.0
        assert p.energy_contour == 1.0

    def test_action_tolerates_monotony(self):
        """Action genre should tolerate sustained energy (low pendulum_balance multiplier)."""
        p = GENRE_PROFILES["action"]
        assert p.pendulum_balance < 0.5  # Mad Max lesson
        assert p.energy_contour < 0.5    # constant energy is fine

    def test_art_house_tolerates_counterpoint(self):
        """Art house should tolerate counterpoint (low music_scene_sync multiplier)."""
        p = GENRE_PROFILES["art_house"]
        assert p.music_scene_sync < 0.7  # Fellini lesson

    def test_surreal_tolerates_everything(self):
        """Surreal genre should have low multipliers across the board."""
        p = GENRE_PROFILES["surreal"]
        avg_multiplier = (
            p.music_scene_sync + p.pendulum_balance + p.camelot_proximity +
            p.script_visual_match + p.energy_contour
        ) / 5.0
        assert avg_multiplier < 0.5  # Lynch lesson: chaos is the genre

    def test_list_genre_profiles(self):
        profiles = list_genre_profiles()
        assert len(profiles) >= 7
        for p in profiles:
            assert "genre" in p
            assert "label" in p
            assert "multipliers" in p

    def test_profile_to_dict(self):
        p = GENRE_PROFILES["action"]
        d = p.to_dict()
        assert d["genre"] == "action"
        assert "multipliers" in d
        assert d["multipliers"]["pendulum_balance"] < 0.5


# =====================================================================
# Calibrated Energy Tests
# =====================================================================

class TestCalibratedEnergies:
    """Test compute_calibrated_energies with genre context."""

    def _build_monotone_action_scores(self) -> List[PulseScore]:
        """Build Mad Max-style scores: all positive, high energy."""
        return [
            PulseScore(
                scene_id=f"s{i}", camelot_key=k, scale="Mixolydian",
                pendulum_position=p, dramatic_function="Adventure",
                energy_profile="high_sustained", counterpoint_pair="Dorian",
                confidence=0.8, alignment="sync",
            )
            for i, (k, p) in enumerate([
                ("11B", 0.2), ("10B", 0.5), ("12B", -0.2),
                ("9B", 0.8), ("2B", -0.4), ("8A", 1.0),
            ])
        ]

    def _build_counterpoint_scores(self) -> List[PulseScore]:
        """Build Cabiria-style scores: counterpoint alignment."""
        return [
            PulseScore(
                scene_id=f"s{i}", camelot_key=k, scale="Aeolian",
                pendulum_position=p, dramatic_function=func,
                energy_profile="low_sustained", counterpoint_pair="Ionian",
                confidence=0.8, alignment=align,
            )
            for i, (k, p, func, align) in enumerate([
                ("4A", -0.9, "Loss", "counterpoint"),
                ("9A", -0.6, "Loss", "counterpoint"),
                ("8B", 0.4, "Wonder", "sync"),
                ("3A", -0.8, "Menace", "counterpoint"),
                ("1A", -1.0, "Loss", "counterpoint"),
                ("7B", 0.7, "Victory", "sync"),
            ])
        ]

    def _build_surreal_scores(self) -> List[PulseScore]:
        """Build Lynch-style scores: wild pendulum, jarring keys."""
        return [
            PulseScore(
                scene_id=f"s{i}", camelot_key=k, scale=sc,
                pendulum_position=p, dramatic_function=func,
                energy_profile="variable", counterpoint_pair="Whole Tone",
                confidence=0.7, alignment=align,
            )
            for i, (k, p, sc, func, align) in enumerate([
                ("6A", -0.3, "Dorian", "Mystery", "sync"),
                ("1B", 0.8, "Ionian", "Wonder", "counterpoint"),
                ("11A", -0.7, "Phrygian", "Menace", "counterpoint"),
                ("4B", -0.9, "Aeolian", "Loss", "sync"),
                ("7A", 0.1, "Dorian", "Mystery", "sync"),
                ("3B", -1.0, "Locrian", "Madness", "counterpoint"),
                ("9A", -0.5, "Aeolian", "Loss", "sync"),
            ])
        ]

    def test_drama_no_calibration_change(self):
        """Drama genre should not change raw scores (multipliers are 1.0)."""
        scores = self._build_monotone_action_scores()
        result = compute_calibrated_energies(scores, genre="drama")
        assert result["genre"] == "drama"
        # For drama, calibrated should equal raw
        for name in ["music_scene_sync", "pendulum_balance", "camelot_proximity",
                      "script_visual_match", "energy_contour"]:
            assert abs(result["calibrated"][name] - result["raw"][name]) < 0.01

    def test_action_reduces_pendulum_penalty(self):
        """Action genre should significantly reduce pendulum balance penalty."""
        scores = self._build_monotone_action_scores()

        raw = compute_all_energies(scores)
        result = compute_calibrated_energies(scores, genre="action")

        # Raw pendulum balance is non-zero (some monotony in positive energy)
        assert raw["pendulum_balance"] > 0.0, f"Expected non-zero raw pendulum: {raw}"
        # Calibrated should be lower (action multiplier < 0.5)
        assert result["calibrated"]["pendulum_balance"] < raw["pendulum_balance"]
        # Action calibrated total should be lower than raw
        assert result["calibrated"]["total"] < result["raw"]["total"]

    def test_art_house_reduces_counterpoint_penalty(self):
        """Art house genre should reduce music_scene_sync penalty."""
        scores = self._build_counterpoint_scores()

        raw = compute_all_energies(scores)
        result = compute_calibrated_energies(scores, genre="art_house")

        # Raw should flag high counterpoint
        assert raw["music_scene_sync"] > 0.3
        # Calibrated should be lower
        assert result["calibrated"]["music_scene_sync"] < raw["music_scene_sync"]

    def test_surreal_reduces_all_penalties(self):
        """Surreal genre should reduce penalties across the board."""
        scores = self._build_surreal_scores()

        raw = compute_all_energies(scores)
        result = compute_calibrated_energies(scores, genre="surreal")

        # Raw total should be high (everything clashes in Lynch)
        # Calibrated should be significantly lower
        assert result["calibrated"]["total"] < result["raw"]["total"]
        # Check specific reductions
        for name in ["pendulum_balance", "camelot_proximity", "energy_contour"]:
            assert result["calibrated"][name] <= result["raw"][name]

    def test_calibrated_includes_interpretation(self):
        """Result should include human-readable interpretation."""
        scores = self._build_counterpoint_scores()
        result = compute_calibrated_energies(scores, genre="art_house")

        assert "interpretation" in result
        interp = result["interpretation"]
        assert "verdict" in interp
        assert "summary" in interp
        assert "raw_total" in interp
        assert "calibrated_total" in interp
        assert "genre_adjustments" in interp

    def test_calibrated_includes_profile(self):
        """Result should include the profile used."""
        scores = self._build_monotone_action_scores()
        result = compute_calibrated_energies(scores, genre="action")
        assert result["profile"]["genre"] == "action"
        assert "multipliers" in result["profile"]

    def test_unknown_genre_falls_back_to_drama(self):
        """Unknown genre should fall back to drama (neutral) profile."""
        scores = self._build_monotone_action_scores()
        result = compute_calibrated_energies(scores, genre="nonexistent_genre")
        # Should behave like drama
        for name in ["music_scene_sync", "pendulum_balance"]:
            assert abs(result["calibrated"][name] - result["raw"][name]) < 0.01

    def test_calibrated_values_capped_at_1(self):
        """Calibrated values should never exceed 1.0."""
        scores = self._build_counterpoint_scores()
        # Horror has some multipliers > 1.0
        result = compute_calibrated_energies(scores, genre="horror")
        for name in ["music_scene_sync", "pendulum_balance", "camelot_proximity",
                      "script_visual_match", "energy_contour", "total"]:
            assert result["calibrated"][name] <= 1.0


# =====================================================================
# Grok Validation: Specific Film Tests
# =====================================================================

class TestGrokValidation:
    """Tests based on Grok's exact analysis of 3 films."""

    def test_cabiria_counterpoint_detected(self):
        """Nights of Cabiria: 4 of 6 scenes have counterpoint alignment."""
        scores = [
            PulseScore(scene_id="sc_0", camelot_key="4A", scale="Aeolian",
                       pendulum_position=-0.9, dramatic_function="Loss",
                       energy_profile="high", counterpoint_pair="Ionian",
                       confidence=0.8, alignment="counterpoint"),
            PulseScore(scene_id="sc_1", camelot_key="9A", scale="Aeolian",
                       pendulum_position=-0.6, dramatic_function="Loss",
                       energy_profile="medium", counterpoint_pair="Ionian",
                       confidence=0.7, alignment="counterpoint"),
            PulseScore(scene_id="sc_2", camelot_key="8B", scale="Ionian",
                       pendulum_position=0.4, dramatic_function="Wonder",
                       energy_profile="medium", counterpoint_pair="Aeolian",
                       confidence=0.7, alignment="sync"),
            PulseScore(scene_id="sc_3", camelot_key="3A", scale="Phrygian",
                       pendulum_position=-0.8, dramatic_function="Menace",
                       energy_profile="high", counterpoint_pair="Lydian",
                       confidence=0.8, alignment="counterpoint"),
            PulseScore(scene_id="sc_4", camelot_key="1A", scale="Aeolian",
                       pendulum_position=-1.0, dramatic_function="Loss",
                       energy_profile="low", counterpoint_pair="Ionian",
                       confidence=0.9, alignment="counterpoint"),
            PulseScore(scene_id="sc_5", camelot_key="7B", scale="Ionian",
                       pendulum_position=0.7, dramatic_function="Victory",
                       energy_profile="high", counterpoint_pair="Aeolian",
                       confidence=0.8, alignment="sync"),
        ]
        raw = compute_all_energies(scores)
        cal = compute_calibrated_energies(scores, genre="art_house")

        # Raw music_scene_sync should be high (lots of counterpoint)
        assert raw["music_scene_sync"] > 0.4
        # Art house calibrated should be lower
        assert cal["calibrated"]["music_scene_sync"] < raw["music_scene_sync"]

    def test_mad_max_energy_contour_tolerated(self):
        """Mad Max: constant high energy should be tolerated in action genre."""
        scores = [
            PulseScore(scene_id=f"s{i}", camelot_key=k, scale="Mixolydian",
                       pendulum_position=p, dramatic_function="Adventure",
                       energy_profile="high_sustained", counterpoint_pair="Dorian",
                       confidence=0.8, alignment="sync",
                       narrative_bpm=NarrativeBPM(
                           scene_id=f"s{i}", dramatic_function="Adventure",
                           pendulum_position=p, estimated_energy=e, confidence=0.8,
                       ))
            for i, (k, p, e) in enumerate([
                ("11B", 0.2, 1.0), ("10B", 0.5, 0.95), ("12B", -0.2, 1.0),
                ("9B", 0.8, 1.0), ("2B", -0.4, 0.98), ("8A", 1.0, 0.9),
            ])
        ]
        raw = compute_all_energies(scores)
        cal = compute_calibrated_energies(scores, genre="action")

        # Energy contour should be high raw (constant high energy = spiky? No, flat high)
        # But action should tolerate it
        assert cal["calibrated"]["energy_contour"] <= raw["energy_contour"]
        assert cal["calibrated"]["pendulum_balance"] < raw["pendulum_balance"]

    def test_mulholland_chaos_tolerated_in_surreal(self):
        """Mulholland Drive: wild jumps tolerated in surreal genre."""
        scores = [
            PulseScore(scene_id=f"s{i}", camelot_key=k, scale=sc,
                       pendulum_position=p, dramatic_function=func,
                       energy_profile="variable", counterpoint_pair="",
                       confidence=0.7, alignment=align)
            for i, (k, p, sc, func, align) in enumerate([
                ("6A", -0.3, "Dorian", "Mystery", "sync"),
                ("1B", 0.8, "Ionian", "Wonder", "counterpoint"),
                ("11A", -0.7, "Phrygian", "Menace", "counterpoint"),
                ("4B", -0.9, "Aeolian", "Loss", "sync"),
                ("7A", 0.1, "Dorian", "Mystery", "sync"),
                ("3B", -1.0, "Locrian", "Madness", "counterpoint"),
                ("9A", -0.5, "Aeolian", "Loss", "sync"),
            ])
        ]
        raw = compute_all_energies(scores)
        cal = compute_calibrated_energies(scores, genre="surreal")

        # Raw should be high (chaos)
        assert raw["camelot_proximity"] > 0.3
        # Surreal calibrated should be much lower
        assert cal["calibrated"]["total"] < raw["total"]
        # Camelot proximity reduced by surreal multiplier (0.3)
        assert cal["calibrated"]["camelot_proximity"] < raw["camelot_proximity"]
