"""
PULSE Camelot Engine — harmonic distance, path planning, key transitions.

The Camelot wheel has 12 positions × 2 rings (A=minor, B=major).
Adjacent keys (±1) are harmonically compatible.
Inner↔Outer (same number, A↔B) are parallel keys.

MARKER_179.2_CAMELOT_ENGINE
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class CamelotMode(str, Enum):
    MINOR = "A"  # inner ring
    MAJOR = "B"  # outer ring


@dataclass(frozen=True)
class CamelotKey:
    """A position on the Camelot wheel: number (1-12) + mode (A/B)."""
    number: int  # 1-12
    mode: CamelotMode

    def __str__(self) -> str:
        return f"{self.number}{self.mode.value}"

    @classmethod
    def parse(cls, key_str: str) -> "CamelotKey":
        """Parse '8A', '11B', etc."""
        s = key_str.strip().upper()
        if not s:
            raise ValueError("Empty Camelot key")
        mode_char = s[-1]
        if mode_char not in ("A", "B"):
            raise ValueError(f"Invalid Camelot mode: {mode_char}")
        num_str = s[:-1]
        num = int(num_str)
        if not 1 <= num <= 12:
            raise ValueError(f"Camelot number must be 1-12, got {num}")
        return cls(number=num, mode=CamelotMode(mode_char))

    @property
    def is_minor(self) -> bool:
        return self.mode == CamelotMode.MINOR

    @property
    def is_major(self) -> bool:
        return self.mode == CamelotMode.MAJOR


# ---------------------------------------------------------------------------
# Standard musical key → Camelot mapping
# ---------------------------------------------------------------------------
_KEY_TO_CAMELOT: Dict[str, str] = {
    # Minor keys (A ring)
    "Ab minor": "1A", "Eb minor": "2A", "Bb minor": "3A",
    "F minor": "4A", "C minor": "5A", "G minor": "6A",
    "D minor": "7A", "A minor": "8A", "E minor": "9A",
    "B minor": "10A", "F# minor": "11A", "Db minor": "12A",
    # Major keys (B ring)
    "B major": "1B", "F# major": "2B", "Db major": "3B",
    "Ab major": "4B", "Eb major": "5B", "Bb major": "6B",
    "F major": "7B", "C major": "8B", "G major": "9B",
    "D major": "10B", "A major": "11B", "E major": "12B",
    # Enharmonic aliases
    "G# minor": "1A", "D# minor": "2A", "A# minor": "3A",
    "C# minor": "12A", "Gb major": "2B", "C# major": "3B",
    "G# major": "4B", "D# major": "5B", "A# major": "6B",
}

# Reverse: Camelot → key name
_CAMELOT_TO_KEY: Dict[str, str] = {
    "1A": "Ab minor", "2A": "Eb minor", "3A": "Bb minor",
    "4A": "F minor", "5A": "C minor", "6A": "G minor",
    "7A": "D minor", "8A": "A minor", "9A": "E minor",
    "10A": "B minor", "11A": "F# minor", "12A": "Db minor",
    "1B": "B major", "2B": "F# major", "3B": "Db major",
    "4B": "Ab major", "5B": "Eb major", "6B": "Bb major",
    "7B": "F major", "8B": "C major", "9B": "G major",
    "10B": "D major", "11B": "A major", "12B": "E major",
}


class CamelotEngine:
    """
    Camelot wheel operations: distance, compatibility, path planning.

    Usage:
        engine = CamelotEngine()
        dist = engine.distance("8A", "11B")  # → 3
        compat = engine.compatibility("8A", "8B")  # → 1.0 (parallel)
        path = engine.plan_path(["8A", "9A", "3B", "8A"])  # check smoothness
    """

    def distance(self, key_a: str, key_b: str) -> int:
        """
        Harmonic distance between two Camelot keys.

        Rules:
        - Same key: 0
        - ±1 on wheel (same ring): 1
        - Same number, different ring (parallel): 1
        - Otherwise: minimum steps on the wheel + ring change penalty
        """
        a = CamelotKey.parse(key_a)
        b = CamelotKey.parse(key_b)
        if a == b:
            return 0

        # Circular distance on the 12-position wheel
        num_dist = min(
            abs(a.number - b.number),
            12 - abs(a.number - b.number),
        )

        # Ring change adds 1 step (parallel key transition)
        ring_penalty = 0 if a.mode == b.mode else 1

        # Special case: same number, different ring = parallel = 1
        if num_dist == 0 and ring_penalty == 1:
            return 1

        return num_dist + ring_penalty

    def compatibility(self, key_a: str, key_b: str) -> float:
        """
        Compatibility score 0.0 (worst) to 1.0 (best).

        Distance → Compatibility:
        0 → 1.0 (same key)
        1 → 1.0 (adjacent/parallel — perfect mix)
        2 → 0.8 (acceptable)
        3 → 0.5 (dramatic but possible)
        4 → 0.3 (very dramatic)
        5+ → 0.1 (clash — use for intentional effect)
        """
        d = self.distance(key_a, key_b)
        scores = {0: 1.0, 1: 1.0, 2: 0.8, 3: 0.5, 4: 0.3}
        return scores.get(d, 0.1)

    def transition_quality(self, key_a: str, key_b: str) -> str:
        """
        Human-readable transition quality label.
        """
        d = self.distance(key_a, key_b)
        labels = {
            0: "perfect",
            1: "harmonic",
            2: "acceptable",
            3: "dramatic",
            4: "very_dramatic",
        }
        return labels.get(d, "clash")

    def neighbors(self, key: str) -> List[str]:
        """
        Get all harmonically compatible neighbors (distance ≤ 1).
        Returns 3 keys: ±1 on same ring + parallel key.
        """
        k = CamelotKey.parse(key)
        result = []

        # Same ring, ±1
        for delta in (-1, 1):
            n = ((k.number - 1 + delta) % 12) + 1
            result.append(f"{n}{k.mode.value}")

        # Parallel key (same number, other ring)
        other_mode = CamelotMode.MAJOR if k.is_minor else CamelotMode.MINOR
        result.append(f"{k.number}{other_mode.value}")

        return result

    def plan_path(self, keys: List[str]) -> "CamelotPath":
        """
        Analyze a sequence of Camelot keys (scene transitions).

        Returns path analysis with:
        - total_distance: sum of all transitions
        - max_jump: largest single transition
        - smoothness: 0.0 (all clashes) to 1.0 (all harmonic)
        - transitions: list of (from, to, distance, quality) tuples
        """
        if len(keys) < 2:
            return CamelotPath(
                keys=keys,
                transitions=[],
                total_distance=0,
                max_jump=0,
                smoothness=1.0,
            )

        transitions = []
        total_dist = 0
        max_jump = 0

        for i in range(len(keys) - 1):
            d = self.distance(keys[i], keys[i + 1])
            q = self.transition_quality(keys[i], keys[i + 1])
            transitions.append(CamelotTransition(
                from_key=keys[i],
                to_key=keys[i + 1],
                distance=d,
                quality=q,
            ))
            total_dist += d
            max_jump = max(max_jump, d)

        # Smoothness: average compatibility
        avg_compat = sum(
            self.compatibility(t.from_key, t.to_key)
            for t in transitions
        ) / len(transitions) if transitions else 1.0

        return CamelotPath(
            keys=keys,
            transitions=transitions,
            total_distance=total_dist,
            max_jump=max_jump,
            smoothness=avg_compat,
        )

    def suggest_next(
        self,
        current_key: str,
        target_pendulum: float,
        *,
        prefer_dramatic: bool = False,
    ) -> List[Tuple[str, float]]:
        """
        Suggest next Camelot key based on target pendulum position.

        Args:
            current_key: current scene's Camelot key
            target_pendulum: desired pendulum (-1.0 to +1.0)
            prefer_dramatic: if True, prefer farther keys for dramatic effect

        Returns:
            List of (key, score) sorted by score descending.
        """
        from src.services.pulse_cinema_matrix import get_cinema_matrix

        matrix = get_cinema_matrix()
        candidates = []

        for row in matrix.all_scales():
            if row.camelot_region == "X":
                continue  # skip atonal scales

            # Try all 12 positions for this mode
            mode = row.camelot_region
            for num in range(1, 13):
                key_str = f"{num}{mode}"
                dist = self.distance(current_key, key_str)
                compat = self.compatibility(current_key, key_str)

                # Pendulum fit: how close is this scale's pendulum to target?
                pendulum_fit = 1.0 - abs(row.pendulum_position - target_pendulum) / 2.0

                if prefer_dramatic:
                    # Dramatic: favor bigger jumps
                    drama_bonus = min(dist / 6.0, 1.0) * 0.3
                    score = pendulum_fit * 0.5 + drama_bonus + compat * 0.2
                else:
                    # Smooth: favor harmonic transitions
                    score = pendulum_fit * 0.4 + compat * 0.6

                candidates.append((key_str, round(score, 3)))

        # Deduplicate and sort
        seen = set()
        unique = []
        for key_str, score in sorted(candidates, key=lambda x: -x[1]):
            if key_str not in seen:
                seen.add(key_str)
                unique.append((key_str, score))
        return unique[:10]

    def suggest_transition(
        self, key_a: str, key_b: str,
    ) -> Dict[str, Any]:
        """
        Suggest transition type and duration based on Camelot distance.

        Distance mapping (from task spec):
        - 0-1 (harmonically compatible) → short crossfade (0.5s)
        - 2-3 (moderate)                → medium crossfade (1.0s)
        - 4-5 (dramatic)                → long crossfade (2.0s)
        - 6   (clash)                   → dip-to-black (2.0s)

        Returns dict with type, duration_sec, quality, distance.
        """
        d = self.distance(key_a, key_b)
        quality = self.transition_quality(key_a, key_b)

        if d <= 1:
            return {
                "type": "cross_dissolve",
                "duration_sec": 0.5,
                "quality": quality,
                "distance": d,
            }
        elif d <= 3:
            return {
                "type": "cross_dissolve",
                "duration_sec": 1.0,
                "quality": quality,
                "distance": d,
            }
        elif d <= 5:
            return {
                "type": "cross_dissolve",
                "duration_sec": 2.0,
                "quality": quality,
                "distance": d,
            }
        else:
            # Clash — dip-to-black hides the harmonic collision
            return {
                "type": "dip_to_black",
                "duration_sec": 2.0,
                "quality": quality,
                "distance": d,
            }

    def key_from_musical(self, musical_key: str) -> Optional[str]:
        """Convert musical key name to Camelot code. E.g. 'A minor' → '8A'."""
        return _KEY_TO_CAMELOT.get(musical_key)

    def musical_from_key(self, camelot_key: str) -> Optional[str]:
        """Convert Camelot code to musical key name. E.g. '8A' → 'A minor'."""
        return _CAMELOT_TO_KEY.get(camelot_key.upper())


@dataclass(frozen=True)
class CamelotTransition:
    """A single key transition in a path."""
    from_key: str
    to_key: str
    distance: int
    quality: str  # perfect, harmonic, acceptable, dramatic, very_dramatic, clash


@dataclass(frozen=True)
class CamelotPath:
    """Analysis of a sequence of Camelot key transitions."""
    keys: List[str]
    transitions: List[CamelotTransition]
    total_distance: int
    max_jump: int
    smoothness: float  # 0.0 to 1.0


# Singleton
_engine_instance: Optional[CamelotEngine] = None


def get_camelot_engine() -> CamelotEngine:
    """Get or create singleton Camelot engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = CamelotEngine()
    return _engine_instance
