"""
PULSE Story Space 3D — McKee Triangle × Camelot Wheel = Complete Story Space.

The key insight (from Opus): the Camelot wheel and McKee triangle are not
nested — they are ORTHOGONAL.

  Horizontal plane = Camelot wheel (12 keys, BPM). "What we feel now."
  Vertical axis = McKee triangle (arch/mini/anti). "How the story is built."
  Film DAG = trajectory through this 3D space.

Each scene is a point: (camelot_angle, mckee_height, pendulum_color).
Critics don't calibrate externally — they READ the coordinate.
A point high on arch axis → pendulum critic at full strength.
A point low-right on anti axis → pendulum OFF, chaos_index ON.

MARKER_179.13_STORY_SPACE_3D
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.services.pulse_conductor import PulseScore
from src.services.pulse_cinema_matrix import get_cinema_matrix


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class TrianglePosition:
    """
    Position in McKee's Story Triangle.

    Barycentric coordinates: arch + mini + anti = 1.0.
    Each film/scene has a position that determines critic behavior.

    Examples:
      Star Wars:          (0.9, 0.05, 0.05) — pure archplot
      Nights of Cabiria:  (0.3, 0.6, 0.1)   — miniplot-dominant
      Mulholland Drive:   (0.1, 0.1, 0.8)   — antiplot
      Barton Fink:        (0.33, 0.33, 0.34) — center of triangle
    """
    arch: float = 0.5   # Classical Design: symphony, pendulum, camelot path
    mini: float = 0.3   # Minimalism: nocturne, narrow pendulum, counterpoint ok
    anti: float = 0.2   # Anti-structure: atonal, chaos, no pendulum

    def __post_init__(self):
        total = self.arch + self.mini + self.anti
        if total > 0 and abs(total - 1.0) > 0.01:
            # Auto-normalize to sum=1.0
            self.arch /= total
            self.mini /= total
            self.anti /= total

    @property
    def mckee_height(self) -> float:
        """Vertical position: 0.0 = bottom (anti/mini), 1.0 = top (archplot)."""
        return self.arch

    @property
    def dominant(self) -> str:
        """Which vertex is dominant."""
        if self.arch >= self.mini and self.arch >= self.anti:
            return "archplot"
        elif self.mini >= self.anti:
            return "miniplot"
        return "antiplot"

    def to_dict(self) -> Dict[str, float]:
        return {"arch": round(self.arch, 3), "mini": round(self.mini, 3), "anti": round(self.anti, 3)}


@dataclass
class StorySpacePoint:
    """
    A single point in the 3D Story Space.

    Combines Camelot position (horizontal) with McKee position (vertical).
    This is the fundamental unit that critics evaluate.
    """
    # Camelot (horizontal plane)
    camelot_key: str = "1A"           # e.g. "8A", "3B"
    camelot_angle: float = 0.0        # 0-360 degrees on the wheel
    # McKee (vertical axis)
    triangle: TrianglePosition = field(default_factory=TrianglePosition)
    # Pendulum
    pendulum: float = 0.0            # -1.0 (minor) → +1.0 (major)
    # Energy
    energy: float = 0.5              # 0.0 → 1.0
    confidence: float = 0.5          # how confident PULSE is in this score
    # Metadata
    scene_index: int = 0
    scene_label: str = ""
    scale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camelot_key": self.camelot_key,
            "camelot_angle": round(self.camelot_angle, 1),
            "triangle": self.triangle.to_dict(),
            "mckee_height": round(self.triangle.mckee_height, 3),
            "pendulum": round(self.pendulum, 3),
            "energy": round(self.energy, 3),
            "confidence": round(self.confidence, 3),
            "scene_index": self.scene_index,
            "scene_label": self.scene_label,
            "scale": self.scale,
        }


# ---------------------------------------------------------------------------
# Triangle → Critic weights interpolation
# ---------------------------------------------------------------------------

# Vertex profiles: critic weights at each corner of the triangle
# From McKee Triangle Calibration v0.2
_VERTEX_PROFILES = {
    "arch": {
        "pendulum_balance": 1.0,     # full McKee pendulum expected
        "pendulum_amplitude_min": 0.6,  # must swing wide
        "camelot_proximity": 0.8,    # smooth transitions expected
        "energy_contour": 0.7,      # crescendo pattern expected
        "music_scene_sync": 1.0,     # sync matters
        "script_visual_match": 1.0,
        "counterpoint_penalty": 0.5,  # counterpoint unusual but possible
        "chaos_tolerance": 0.0,      # chaos = bad for archplot
    },
    "mini": {
        "pendulum_balance": 0.4,     # narrow oscillation is normal
        "pendulum_amplitude_min": 0.2,  # small swings are fine
        "camelot_proximity": 0.9,    # smooth transitions critical
        "energy_contour": 0.3,      # low energy is the point
        "music_scene_sync": 0.6,     # counterpoint is a feature
        "script_visual_match": 0.7,
        "counterpoint_penalty": 0.1,  # counterpoint is EXPECTED
        "chaos_tolerance": 0.0,      # not chaotic — intimate
    },
    "anti": {
        "pendulum_balance": 0.0,     # linear pendulum not applicable
        "pendulum_amplitude_min": 0.0,  # any swing is valid
        "camelot_proximity": 0.1,    # wild jumps are the point
        "energy_contour": 0.2,      # spiky energy is normal
        "music_scene_sync": 0.3,     # all bets off
        "script_visual_match": 0.3,
        "counterpoint_penalty": 0.0,  # everything is counterpoint
        "chaos_tolerance": 1.0,      # high chaos = GOOD for antiplot
    },
}


def interpolate_critic_weights(triangle: TrianglePosition) -> Dict[str, float]:
    """
    Interpolate critic weights based on triangle position.

    For each critic parameter, the weight is:
      w = arch * arch_weight + mini * mini_weight + anti * anti_weight

    This is the core insight: critics read the coordinate, not an external label.
    """
    result = {}
    for param in _VERTEX_PROFILES["arch"]:
        w = (
            triangle.arch * _VERTEX_PROFILES["arch"][param]
            + triangle.mini * _VERTEX_PROFILES["mini"][param]
            + triangle.anti * _VERTEX_PROFILES["anti"][param]
        )
        result[param] = round(w, 3)
    return result


# ---------------------------------------------------------------------------
# Chaos Index — the 6th energy critic
# ---------------------------------------------------------------------------

def chaos_index(scores: List[PulseScore]) -> float:
    """
    Measures unpredictability of transitions across scenes.

    High chaos = transitions are unpredictable (keys, energy, pendulum all jump).
    Low chaos = transitions are smooth and predictable.

    For archplot: high chaos = BAD (story should have structure).
    For antiplot: high chaos = GOOD (unpredictability IS the form).
    """
    if len(scores) < 3:
        return 0.0

    # 1. Camelot key jump variance
    from src.services.pulse_camelot_engine import get_camelot_engine
    engine = get_camelot_engine()
    key_distances = []
    for i in range(len(scores) - 1):
        try:
            d = engine.distance(scores[i].camelot_key, scores[i + 1].camelot_key)
        except ValueError:
            d = 6
        key_distances.append(d)

    key_variance = _variance(key_distances) if key_distances else 0.0

    # 2. Pendulum jump variance (how erratic the emotional swings are)
    pendulum_jumps = [
        abs(scores[i + 1].pendulum_position - scores[i].pendulum_position)
        for i in range(len(scores) - 1)
    ]
    pendulum_variance = _variance(pendulum_jumps) if pendulum_jumps else 0.0

    # 3. Energy direction changes (how often energy trajectory reverses)
    energies = []
    for s in scores:
        if s.narrative_bpm:
            energies.append(s.narrative_bpm.estimated_energy)
        else:
            energies.append(0.5)

    direction_changes = 0
    if len(energies) >= 3:
        for i in range(1, len(energies) - 1):
            d1 = energies[i] - energies[i - 1]
            d2 = energies[i + 1] - energies[i]
            if d1 * d2 < 0:  # sign change = direction reversal
                direction_changes += 1
        reversal_ratio = direction_changes / (len(energies) - 2)
    else:
        reversal_ratio = 0.0

    # Combine: higher variance + more reversals = higher chaos
    # Normalize to 0-1 range
    key_chaos = min(key_variance / 4.0, 1.0)       # variance > 4 = max chaos
    pend_chaos = min(pendulum_variance / 0.5, 1.0)  # variance > 0.5 = max chaos
    dir_chaos = reversal_ratio                       # already 0-1

    chaos = key_chaos * 0.4 + pend_chaos * 0.3 + dir_chaos * 0.3
    return round(max(0.0, min(1.0, chaos)), 3)


def _variance(values: List[float]) -> float:
    """Simple variance calculation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


# ---------------------------------------------------------------------------
# Triangle-calibrated energy computation
# ---------------------------------------------------------------------------

def compute_triangle_energies(
    scores: List[PulseScore],
    triangle: Optional[TrianglePosition] = None,
) -> Dict[str, Any]:
    """
    Compute energy critics calibrated by McKee Triangle position.

    This replaces the old genre-based calibration with continuous interpolation.
    Critics READ the triangle coordinate — they don't need an external label.

    Args:
        scores: List of PulseScore for the film/sequence
        triangle: Position in McKee's triangle. If None, inferred from scores' scales.

    Returns dict with raw scores, calibrated scores, chaos_index, and interpretation.
    """
    from src.services.pulse_energy_critics import compute_all_energies

    # Infer triangle position from scores' scales if not provided
    if triangle is None:
        triangle = infer_triangle_from_scores(scores)

    # Get raw critic scores (existing 5 critics)
    raw = compute_all_energies(scores)

    # Get interpolated weights for this triangle position
    weights = interpolate_critic_weights(triangle)

    # Compute chaos index (6th critic)
    raw_chaos = chaos_index(scores)

    # Calibrate: multiply raw scores by interpolated weights
    calibrated: Dict[str, float] = {}

    # Standard 5 critics
    critic_mapping = {
        "music_scene_sync": "music_scene_sync",
        "pendulum_balance": "pendulum_balance",
        "camelot_proximity": "camelot_proximity",
        "script_visual_match": "script_visual_match",
        "energy_contour": "energy_contour",
    }

    for critic_name, weight_name in critic_mapping.items():
        raw_val = raw.get(critic_name, 0.0)
        w = weights.get(weight_name, 1.0)
        calibrated[critic_name] = round(min(raw_val * w, 1.0), 3)

    # Chaos index: inverted weight — high chaos_tolerance means chaos is GOOD
    # For antiplot (chaos_tolerance=1.0): raw_chaos 0.8 → calibrated 0.2 (low energy = good)
    # For archplot (chaos_tolerance=0.0): raw_chaos 0.8 → calibrated 0.8 (high energy = bad)
    chaos_weight = 1.0 - weights.get("chaos_tolerance", 0.0)
    calibrated["chaos_index"] = round(raw_chaos * chaos_weight, 3)

    # Weighted total (6 critics now)
    _TRIANGLE_CRITIC_WEIGHTS = {
        "music_scene_sync": 0.20,
        "pendulum_balance": 0.20,
        "camelot_proximity": 0.15,
        "script_visual_match": 0.15,
        "energy_contour": 0.15,
        "chaos_index": 0.15,
    }

    cal_total = sum(
        calibrated.get(name, 0.0) * w
        for name, w in _TRIANGLE_CRITIC_WEIGHTS.items()
    )
    calibrated["total"] = round(min(cal_total, 1.0), 3)

    return {
        "triangle_position": triangle.to_dict(),
        "dominant_vertex": triangle.dominant,
        "mckee_height": round(triangle.mckee_height, 3),
        "raw": {**raw, "chaos_index": raw_chaos},
        "calibrated": calibrated,
        "weights": weights,
        "interpretation": _triangle_interpretation(calibrated, raw, raw_chaos, triangle),
    }


def _triangle_interpretation(
    calibrated: Dict[str, float],
    raw: Dict[str, float],
    raw_chaos: float,
    triangle: TrianglePosition,
) -> Dict[str, Any]:
    """Generate interpretation based on triangle position."""
    total = calibrated.get("total", 0.0)

    if total < 0.15:
        verdict = "excellent"
        summary = f"Montage perfectly tuned for {triangle.dominant}"
    elif total < 0.3:
        verdict = "good"
        summary = "Solid montage with genre-appropriate tensions"
    elif total < 0.45:
        verdict = "moderate"
        summary = "Some critics flag tension — may be intentional"
    elif total < 0.6:
        verdict = "high_tension"
        summary = "Significant tension — review flagged critics"
    else:
        verdict = "extreme"
        summary = "Multiple critics fired — montage may need rework"

    # Genre-specific insights
    insights = []

    if triangle.dominant == "antiplot" and raw_chaos > 0.5:
        insights.append("High chaos is EXPECTED for anti-structure — this is working correctly")
    elif triangle.dominant == "archplot" and raw_chaos > 0.5:
        insights.append("WARNING: High chaos in archplot — story structure may be inconsistent")

    if triangle.dominant == "miniplot" and raw.get("pendulum_balance", 0) > 0.5:
        insights.append("Narrow pendulum is NORMAL for minimalism — not a flaw")

    if triangle.mini > 0.3 and calibrated.get("music_scene_sync", 0) < raw.get("music_scene_sync", 0):
        insights.append("Counterpoint tolerated — miniplot allows conscious contradiction")

    return {
        "verdict": verdict,
        "summary": summary,
        "calibrated_total": total,
        "raw_total": raw.get("total", 0.0),
        "raw_chaos": raw_chaos,
        "insights": insights,
    }


# ---------------------------------------------------------------------------
# Inference: scores → triangle position
# ---------------------------------------------------------------------------

def infer_triangle_from_scores(scores: List[PulseScore]) -> TrianglePosition:
    """
    Infer McKee triangle position from the scales used in PulseScores.

    Uses the cinema matrix: each scale has a triangle position.
    Film's position = weighted average of scene triangle positions.
    """
    matrix = get_cinema_matrix()

    arch_sum = 0.0
    mini_sum = 0.0
    anti_sum = 0.0
    count = 0

    for score in scores:
        row = matrix.get_by_scale(score.scale)
        if row:
            arch_sum += row.triangle_arch
            mini_sum += row.triangle_mini
            anti_sum += row.triangle_anti
            count += 1

    if count == 0:
        return TrianglePosition(0.5, 0.3, 0.2)  # default: mild archplot

    return TrianglePosition(
        arch=arch_sum / count,
        mini=mini_sum / count,
        anti=anti_sum / count,
    )


# ---------------------------------------------------------------------------
# Convenience: convert PulseScores to StorySpacePoints
# ---------------------------------------------------------------------------

# Camelot key → angle on the wheel (30° per position)
_CAMELOT_ANGLES = {
    "1A": 0, "1B": 0,
    "2A": 30, "2B": 30,
    "3A": 60, "3B": 60,
    "4A": 90, "4B": 90,
    "5A": 120, "5B": 120,
    "6A": 150, "6B": 150,
    "7A": 180, "7B": 180,
    "8A": 210, "8B": 210,
    "9A": 240, "9B": 240,
    "10A": 270, "10B": 270,
    "11A": 300, "11B": 300,
    "12A": 330, "12B": 330,
}


def scores_to_story_space(scores: List[PulseScore]) -> List[StorySpacePoint]:
    """Convert a list of PulseScores into StorySpace3D points."""
    matrix = get_cinema_matrix()
    points = []

    for i, score in enumerate(scores):
        row = matrix.get_by_scale(score.scale)
        if row:
            tri = TrianglePosition(row.triangle_arch, row.triangle_mini, row.triangle_anti)
        else:
            tri = TrianglePosition(0.5, 0.3, 0.2)

        angle = _CAMELOT_ANGLES.get(score.camelot_key, 0)

        point = StorySpacePoint(
            camelot_key=score.camelot_key,
            camelot_angle=float(angle),
            triangle=tri,
            pendulum=score.pendulum_position,
            energy=score.narrative_bpm.estimated_energy if score.narrative_bpm else 0.5,
            confidence=score.confidence,
            scene_index=i,
            scene_label=f"Scene {i + 1}",
            scale=score.scale,
        )
        points.append(point)

    return points


# ---------------------------------------------------------------------------
# McKee genre → triangle position mapping (backward compat with 179.12)
# ---------------------------------------------------------------------------

# From McKee "Story" Table: 25 genres → triangle positions
MCKEE_GENRE_TRIANGLES: Dict[str, TrianglePosition] = {
    # Old genre profiles → triangle equivalents
    "drama": TrianglePosition(0.8, 0.15, 0.05),
    "action": TrianglePosition(0.85, 0.05, 0.1),
    "art_house": TrianglePosition(0.2, 0.5, 0.3),
    "surreal": TrianglePosition(0.1, 0.1, 0.8),
    "horror": TrianglePosition(0.6, 0.1, 0.3),
    "comedy": TrianglePosition(0.7, 0.2, 0.1),
    "documentary": TrianglePosition(0.4, 0.4, 0.2),
    # McKee's 25 genres (from calibration doc v0.2)
    "love_story": TrianglePosition(0.8, 0.15, 0.05),
    "crime": TrianglePosition(0.9, 0.05, 0.05),
    "thriller": TrianglePosition(0.7, 0.1, 0.2),
    "social_drama": TrianglePosition(0.3, 0.6, 0.1),
    "education_plot": TrianglePosition(0.6, 0.3, 0.1),
    "redemption_plot": TrianglePosition(0.5, 0.4, 0.1),
    "disillusionment": TrianglePosition(0.3, 0.5, 0.2),
    "fantasy": TrianglePosition(0.9, 0.05, 0.05),
    "non_commercial": TrianglePosition(0.2, 0.4, 0.4),
    "multi_plot": TrianglePosition(0.3, 0.6, 0.1),
    "war": TrianglePosition(0.7, 0.2, 0.1),
    "western": TrianglePosition(0.85, 0.1, 0.05),
    "musical": TrianglePosition(0.7, 0.2, 0.1),
    "period_film": TrianglePosition(0.5, 0.3, 0.2),
    "noir": TrianglePosition(0.5, 0.4, 0.1),
}


def genre_to_triangle(genre: str) -> TrianglePosition:
    """
    Convert a genre string to a triangle position.

    Backward compatible with 179.12 genre profiles.
    New McKee genres also supported.
    """
    key = genre.lower().replace(" ", "_").replace("-", "_")
    return MCKEE_GENRE_TRIANGLES.get(key, TrianglePosition(0.5, 0.3, 0.2))
