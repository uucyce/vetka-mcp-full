"""
PULSE Energy Critics — LeCun-inspired scalar compatibility functions.

Five energy critics that evaluate how well montage elements fit together.
Low energy = good compatibility. High energy = tension/conflict.

Genre-aware calibration (MARKER_179.12): critics adjust thresholds
based on film genre context. What's "bad" in drama is intentional in action.
Validated on Nights of Cabiria, Mad Max, Mulholland Drive (Grok 179.0A).

From the manifesto:
  "Energy critics are not judges. They are sensors.
   They don't say 'this is wrong' — they say 'this costs X energy'.
   The editor decides if the cost is worth paying."

MARKER_179.6_ENERGY_CRITICS
MARKER_179.12_GENRE_CALIBRATION
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.services.pulse_conductor import (
    NarrativeBPM,
    VisualBPM,
    AudioBPM,
    PulseScore,
)
from src.services.pulse_camelot_engine import get_camelot_engine


# ---------------------------------------------------------------------------
# 1. Music-Scene Sync Energy
# ---------------------------------------------------------------------------

def music_scene_sync_energy(score: PulseScore) -> float:
    """
    Measures alignment between scene mood and music mood.

    Low energy (0.0) = perfect sync (scene and music reinforce each other)
    High energy (1.0) = maximum contradiction (counterpoint / clash)

    The Nights of Cabiria pattern (conscious counterpoint) will register
    as high energy — this is correct. The editor decides if it's intentional.
    """
    if score.alignment == "sync":
        return 0.1  # minimal energy — everything agrees
    elif score.alignment == "counterpoint":
        return 0.7  # significant energy — conscious contradiction
    elif score.alignment == "polyphonic":
        return 0.5  # moderate — multiple voices
    else:
        return 0.3  # unknown alignment — mild uncertainty


# ---------------------------------------------------------------------------
# 2. Pendulum Balance Energy
# ---------------------------------------------------------------------------

def pendulum_balance_energy(scores: List[PulseScore]) -> float:
    """
    McKee's pendulum: scenes should oscillate between positive and negative.

    Low energy = healthy oscillation (drama is alive)
    High energy = monotonous sequence (same emotional sign throughout)

    Measures:
    - Sign changes: how often pendulum crosses zero
    - Range: does it use the full -1..+1 spectrum
    - Monotony runs: consecutive same-sign stretches
    """
    if len(scores) < 2:
        return 0.0  # single scene — no pendulum to evaluate

    pendulums = [s.pendulum_position for s in scores]

    # Count sign changes
    sign_changes = 0
    for i in range(1, len(pendulums)):
        if pendulums[i] * pendulums[i - 1] < 0:  # different signs
            sign_changes += 1

    max_possible_changes = len(pendulums) - 1
    oscillation_ratio = sign_changes / max_possible_changes if max_possible_changes > 0 else 0

    # Pendulum range utilization
    p_min, p_max = min(pendulums), max(pendulums)
    range_utilization = (p_max - p_min) / 2.0  # max range is 2.0 (-1 to +1)

    # Monotony: longest run of same sign
    max_run = 1
    current_run = 1
    for i in range(1, len(pendulums)):
        if pendulums[i] * pendulums[i - 1] >= 0:  # same sign (or zero)
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1

    monotony_penalty = min(max_run / len(pendulums), 1.0)

    # Energy: inverse of oscillation quality
    # Good oscillation = low energy, monotony = high energy
    energy = 1.0 - (oscillation_ratio * 0.4 + range_utilization * 0.3 + (1 - monotony_penalty) * 0.3)

    return max(0.0, min(1.0, energy))


# ---------------------------------------------------------------------------
# 3. Camelot Proximity Energy
# ---------------------------------------------------------------------------

def camelot_proximity_energy(scores: List[PulseScore]) -> float:
    """
    Measures harmonic smoothness of key transitions across scenes.

    Low energy = smooth harmonic path (adjacent Camelot keys)
    High energy = jarring key jumps (distant keys)

    Uses Camelot wheel distance: 0-1 = harmonic, 2 = okay, 3+ = dramatic.
    """
    if len(scores) < 2:
        return 0.0

    engine = get_camelot_engine()
    keys = [s.camelot_key for s in scores]

    total_distance = 0
    max_distance = 0

    for i in range(len(keys) - 1):
        try:
            d = engine.distance(keys[i], keys[i + 1])
        except ValueError:
            d = 6  # invalid key = maximum tension
        total_distance += d
        max_distance = max(max_distance, d)

    num_transitions = len(keys) - 1
    avg_distance = total_distance / num_transitions

    # Normalize: distance 0-1 → energy 0-0.1, distance 6 → energy 1.0
    energy = min(avg_distance / 6.0, 1.0)

    # Penalty for single very large jump
    spike_penalty = min(max_distance / 6.0, 1.0) * 0.2

    return max(0.0, min(1.0, energy * 0.8 + spike_penalty))


# ---------------------------------------------------------------------------
# 4. Script-Visual Match Energy
# ---------------------------------------------------------------------------

def script_visual_match_energy(
    narrative: NarrativeBPM,
    visual: VisualBPM,
) -> float:
    """
    Measures alignment between script's expected energy and visual energy.

    Low energy = visuals match the script's mood
    High energy = visuals contradict the script

    Compares:
    - Script energy vs visual motion intensity
    - Script energy vs cut density
    """
    # Energy difference between script expectation and visual delivery
    energy_diff = abs(narrative.estimated_energy - visual.motion_intensity)

    # Cut density mapping: high cuts (>15/min) = high energy visuals
    visual_energy_from_cuts = min(visual.cuts_per_minute / 20.0, 1.0)
    cut_diff = abs(narrative.estimated_energy - visual_energy_from_cuts)

    # Weighted combination
    energy = energy_diff * 0.6 + cut_diff * 0.4

    return max(0.0, min(1.0, energy))


# ---------------------------------------------------------------------------
# 5. Energy Contour Energy
# ---------------------------------------------------------------------------

def energy_contour_energy(energy_values: List[float]) -> float:
    """
    Measures how smooth or spiky the overall energy contour is.

    Low energy = gradual changes (smooth arc)
    High energy = wild jumps (chaotic pacing)

    A good film has a controlled energy contour — rising action, climax, denouement.
    Random spikes indicate poor pacing.
    """
    if len(energy_values) < 2:
        return 0.0

    # Calculate deltas between consecutive values
    deltas = [abs(energy_values[i + 1] - energy_values[i]) for i in range(len(energy_values) - 1)]

    avg_delta = sum(deltas) / len(deltas)
    max_delta = max(deltas)

    # Smooth contour: average delta < 0.15, max < 0.3
    # Spiky contour: average delta > 0.4, max > 0.6
    avg_score = min(avg_delta / 0.5, 1.0)
    spike_score = min(max_delta / 0.8, 1.0)

    return max(0.0, min(1.0, avg_score * 0.6 + spike_score * 0.4))


# ---------------------------------------------------------------------------
# Aggregate: compute all 5 energies for a film
# ---------------------------------------------------------------------------

_CRITIC_WEIGHTS = {
    "music_scene_sync": 0.25,
    "pendulum_balance": 0.25,
    "camelot_proximity": 0.20,
    "script_visual_match": 0.15,
    "energy_contour": 0.15,
}


def compute_all_energies(scores: List[PulseScore]) -> Dict[str, float]:
    """
    Compute all 5 energy critics for a film's PulseScore list.

    Returns a dict with individual energies + weighted total.
    Lower total = better overall compatibility.
    """
    result: Dict[str, float] = {}

    # 1. Music-Scene Sync — average across all scenes
    if scores:
        sync_energies = [music_scene_sync_energy(s) for s in scores]
        result["music_scene_sync"] = sum(sync_energies) / len(sync_energies)
    else:
        result["music_scene_sync"] = 0.0

    # 2. Pendulum Balance — whole-film metric
    result["pendulum_balance"] = pendulum_balance_energy(scores)

    # 3. Camelot Proximity — whole-film metric
    result["camelot_proximity"] = camelot_proximity_energy(scores)

    # 4. Script-Visual Match — average across scenes with both signals
    sv_energies = []
    for s in scores:
        if s.narrative_bpm and s.visual_bpm:
            sv_energies.append(script_visual_match_energy(s.narrative_bpm, s.visual_bpm))
    result["script_visual_match"] = (
        sum(sv_energies) / len(sv_energies) if sv_energies else 0.0
    )

    # 5. Energy Contour — from estimated_energy of narrative signals
    energy_values = []
    for s in scores:
        if s.narrative_bpm:
            energy_values.append(s.narrative_bpm.estimated_energy)
        else:
            energy_values.append(0.5)  # neutral fallback
    result["energy_contour"] = energy_contour_energy(energy_values)

    # Weighted total
    total = sum(
        result[name] * weight
        for name, weight in _CRITIC_WEIGHTS.items()
    )
    result["total"] = round(min(total, 1.0), 3)

    # Round individual values
    for k in result:
        result[k] = round(result[k], 3)

    return result


# ---------------------------------------------------------------------------
# MARKER_179.12 — Genre-Aware Calibration
# ---------------------------------------------------------------------------
# Grok validation on 3 films revealed:
#   - Cabiria: counterpoint=0.75 flagged as "bad" but it's Fellini genius
#   - Mad Max: pendulum_balance=0.75 penalizes sustained action
#   - Mulholland Drive: all critics penalize intentional non-linear chaos
#
# Solution: genre profiles adjust raw critic scores via multipliers.
# Multiplier < 1.0 = "this is expected/tolerated for the genre"
# Multiplier > 1.0 = "this is extra problematic for the genre"
# ---------------------------------------------------------------------------

@dataclass
class GenreCalibrationProfile:
    """
    Genre-aware multipliers for energy critic scores.

    Example: action genre has low pendulum_balance multiplier (0.4)
    because sustained same-sign energy is EXPECTED, not a flaw.
    """
    genre: str
    label: str
    # Per-critic multipliers (0.0 = ignore, 1.0 = default, 2.0 = double penalty)
    music_scene_sync: float = 1.0
    pendulum_balance: float = 1.0
    camelot_proximity: float = 1.0
    script_visual_match: float = 1.0
    energy_contour: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "genre": self.genre,
            "label": self.label,
            "multipliers": {
                "music_scene_sync": self.music_scene_sync,
                "pendulum_balance": self.pendulum_balance,
                "camelot_proximity": self.camelot_proximity,
                "script_visual_match": self.script_visual_match,
                "energy_contour": self.energy_contour,
            },
        }


# Built-in genre profiles (validated via Grok on 3 films)
GENRE_PROFILES: Dict[str, GenreCalibrationProfile] = {
    "drama": GenreCalibrationProfile(
        genre="drama",
        label="Drama / Classical Narrative",
        music_scene_sync=1.0,   # counterpoint matters here
        pendulum_balance=1.0,   # McKee oscillation expected
        camelot_proximity=1.0,  # smooth transitions expected
        script_visual_match=1.0,
        energy_contour=1.0,
    ),
    "action": GenreCalibrationProfile(
        genre="action",
        label="Action / Thriller",
        music_scene_sync=0.8,   # sync usually tight
        pendulum_balance=0.4,   # sustained high energy is FINE (Mad Max lesson)
        camelot_proximity=0.7,  # aggressive transitions acceptable
        script_visual_match=0.6, # visuals lead, script follows
        energy_contour=0.3,     # constant high energy is the POINT
    ),
    "art_house": GenreCalibrationProfile(
        genre="art_house",
        label="Art House / Auteur",
        music_scene_sync=0.5,   # counterpoint is INTENTIONAL (Fellini lesson)
        pendulum_balance=0.6,   # less rigid arc expected
        camelot_proximity=0.5,  # wild key changes = artistic choice
        script_visual_match=0.7,
        energy_contour=0.6,     # spiky contour = style
    ),
    "surreal": GenreCalibrationProfile(
        genre="surreal",
        label="Surreal / Non-Linear",
        music_scene_sync=0.4,   # all bets are off
        pendulum_balance=0.3,   # McKee doesn't apply to Lynch
        camelot_proximity=0.3,  # tonal whiplash is the genre
        script_visual_match=0.4, # dream logic ≠ script logic
        energy_contour=0.3,     # chaos IS the contour
    ),
    "horror": GenreCalibrationProfile(
        genre="horror",
        label="Horror / Psychological",
        music_scene_sync=0.7,   # counterpoint used deliberately
        pendulum_balance=0.8,   # sustained dread = ok-ish
        camelot_proximity=0.9,  # jarring transitions are effective
        script_visual_match=1.2, # mismatch often means mistake
        energy_contour=0.8,     # some spikes ok for jumpscares
    ),
    "comedy": GenreCalibrationProfile(
        genre="comedy",
        label="Comedy / Light",
        music_scene_sync=1.2,   # sync very important for timing
        pendulum_balance=1.0,   # need variety
        camelot_proximity=0.8,  # lighter transitions
        script_visual_match=1.1, # visuals should match jokes
        energy_contour=1.0,
    ),
    "documentary": GenreCalibrationProfile(
        genre="documentary",
        label="Documentary / Non-Fiction",
        music_scene_sync=0.9,
        pendulum_balance=0.7,   # can be more monotone
        camelot_proximity=0.6,  # less strict
        script_visual_match=1.2, # should match narration closely
        energy_contour=0.8,
    ),
}


def compute_calibrated_energies(
    scores: List[PulseScore],
    genre: str = "drama",
) -> Dict[str, Any]:
    """
    Compute energy critics with genre-aware calibration.

    Raw scores are multiplied by genre profile multipliers.
    Returns both raw and calibrated values, plus genre context.

    Calibrated total < 0.3 = excellent for this genre
    Calibrated total > 0.6 = problematic even for this genre
    """
    raw = compute_all_energies(scores)
    profile = GENRE_PROFILES.get(genre, GENRE_PROFILES["drama"])

    calibrated: Dict[str, float] = {}
    critic_names = [
        "music_scene_sync", "pendulum_balance", "camelot_proximity",
        "script_visual_match", "energy_contour",
    ]

    for name in critic_names:
        raw_val = raw.get(name, 0.0)
        multiplier = getattr(profile, name, 1.0)
        calibrated[name] = round(min(raw_val * multiplier, 1.0), 3)

    # Calibrated total (re-weighted)
    cal_total = sum(
        calibrated[name] * _CRITIC_WEIGHTS[name]
        for name in critic_names
    )
    calibrated["total"] = round(min(cal_total, 1.0), 3)

    return {
        "genre": genre,
        "genre_label": profile.label,
        "raw": raw,
        "calibrated": calibrated,
        "profile": profile.to_dict(),
        "interpretation": _calibrated_interpretation(calibrated, raw, genre),
    }


def _calibrated_interpretation(
    calibrated: Dict[str, float],
    raw: Dict[str, float],
    genre: str,
) -> Dict[str, Any]:
    """Generate human-readable interpretation of calibrated scores."""
    total = calibrated.get("total", 0.0)

    if total < 0.2:
        verdict = "excellent"
        summary = f"Montage is well-tuned for {genre}"
    elif total < 0.35:
        verdict = "good"
        summary = f"Solid montage with minor tension points"
    elif total < 0.5:
        verdict = "moderate"
        summary = f"Some critics flag tension — may need attention"
    elif total < 0.7:
        verdict = "high_tension"
        summary = f"Significant tension — review flagged critics"
    else:
        verdict = "extreme"
        summary = f"Multiple critics fired — montage may need rework"

    # Find which critics improved most from calibration
    improvements = []
    for name in ["music_scene_sync", "pendulum_balance", "camelot_proximity",
                  "script_visual_match", "energy_contour"]:
        raw_v = raw.get(name, 0.0)
        cal_v = calibrated.get(name, 0.0)
        if raw_v > 0.5 and cal_v < 0.4:
            improvements.append(f"{name}: {raw_v:.2f} → {cal_v:.2f} (genre-tolerated)")

    return {
        "verdict": verdict,
        "summary": summary,
        "raw_total": raw.get("total", 0.0),
        "calibrated_total": total,
        "genre_adjustments": improvements,
    }


def list_genre_profiles() -> List[Dict[str, Any]]:
    """List all available genre calibration profiles."""
    return [p.to_dict() for p in GENRE_PROFILES.values()]
