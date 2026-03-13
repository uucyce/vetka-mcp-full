"""
PULSE Cinema Matrix — Scale → Genre → Cinema Scene → Drama mapping.

Loads the validated matrix (Grok 179.0A, confidence 0.85) and provides
query API for the PULSE conductor.

MARKER_179.1_CINEMA_MATRIX
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class CinemaMatrixRow:
    """Single row in the cinema matrix."""

    scale: str
    intervals: List[int]
    note_count: int
    cinema_genre: str
    cinema_scene_types: str
    dramatic_function: str
    pendulum_position: float  # -1.0 (minor) .. +1.0 (major)
    counterpoint_pair: str
    energy_profile: str
    itten_colors: List[str]
    music_genres: List[str]
    confidence: float  # Grok validation confidence 0-1
    camelot_region: str  # e.g. "8A" (minor) or "8B" (major)


# ---------------------------------------------------------------------------
# Built-in matrix — validated by Grok on 10 films (mean confidence 0.85)
# Corrections applied from 179.0A recon
# ---------------------------------------------------------------------------

_BUILTIN_MATRIX: List[Dict] = [
    {
        "scale": "Ionian",
        "intervals": [0, 2, 4, 5, 7, 9, 11],
        "cinema_genre": "Drama / happy end",
        "cinema_scene_types": "Victory, reunion, finale, celebration",
        "dramatic_function": "Catharsis, Resolution",
        "pendulum_position": 0.8,
        "counterpoint_pair": "Aeolian",
        "energy_profile": "building → peak → sustained",
        "itten_colors": ["Red", "Orange", "Yellow", "Yellow-Green", "Blue-Green", "Blue-Violet", "Red-Violet"],
        "music_genres": ["Pop", "Rock", "Classical", "Folk"],
        "confidence": 0.92,
        "camelot_region": "B",  # major
    },
    {
        "scale": "Lydian",
        "intervals": [0, 2, 4, 6, 7, 9, 11],
        "cinema_genre": "Fantasy / wonder",
        "cinema_scene_types": "Miracle, flight, dream, revelation",
        "dramatic_function": "Wonder, Aspiration",
        "pendulum_position": 0.8,  # corrected from 0.9 by Grok
        "counterpoint_pair": "Locrian",
        "energy_profile": "float → lift → sustained glow",
        "itten_colors": ["Red", "Orange", "Yellow", "Green", "Blue-Green", "Blue-Violet", "Red-Violet"],
        "music_genres": ["Jazz", "Film Scores", "Progressive Rock"],
        "confidence": 0.85,
        "camelot_region": "B",
    },
    {
        "scale": "Mixolydian",
        "intervals": [0, 2, 4, 5, 7, 9, 10],
        "cinema_genre": "Adventure / drive",
        "cinema_scene_types": "Chase, road, journey, heist",
        "dramatic_function": "Adventure, Drive",
        "pendulum_position": 0.6,  # corrected from 0.5 by Grok
        "counterpoint_pair": "Phrygian",
        "energy_profile": "high → higher → peak → repeat",
        "itten_colors": ["Red", "Orange", "Yellow", "Yellow-Green", "Blue-Green", "Blue-Violet", "Violet"],
        "music_genres": ["Blues", "Rock", "Country", "Funk"],
        "confidence": 0.88,
        "camelot_region": "B",
    },
    {
        "scale": "Dorian",
        "intervals": [0, 2, 3, 5, 7, 9, 10],
        "cinema_genre": "Noir / detective",
        "cinema_scene_types": "Night city, detective, cool tension, mystery",
        "dramatic_function": "Mystery, Cool tension",
        "pendulum_position": -0.4,
        "counterpoint_pair": "Lydian",
        "energy_profile": "low simmer → pulse → simmer",
        "itten_colors": ["Red", "Orange", "Yellow-Orange", "Yellow-Green", "Blue-Green", "Blue-Violet", "Violet"],
        "music_genres": ["Jazz", "Rock", "Blues", "Funk"],
        "confidence": 0.79,
        "camelot_region": "A",  # minor
    },
    {
        "scale": "Aeolian",
        "intervals": [0, 2, 3, 5, 7, 8, 10],
        "cinema_genre": "Melodrama / loss",
        "cinema_scene_types": "Loss, farewell, loneliness, grief",
        "dramatic_function": "Grief, Melancholy",
        "pendulum_position": -0.7,
        "counterpoint_pair": "Ionian",
        "energy_profile": "sustained low → dip → fade",
        "itten_colors": ["Red", "Orange", "Yellow-Orange", "Yellow-Green", "Blue-Green", "Blue", "Violet"],
        "music_genres": ["Rock", "Metal", "Classical", "Pop Ballads"],
        "confidence": 0.91,
        "camelot_region": "A",
    },
    {
        "scale": "Phrygian",
        "intervals": [0, 1, 3, 5, 7, 8, 10],
        "cinema_genre": "Horror / ritual",
        "cinema_scene_types": "Threat, ritual, ancient evil, menace",
        "dramatic_function": "Menace, Ritual",
        "pendulum_position": -0.9,  # corrected from -0.8 by Grok
        "counterpoint_pair": "Mixolydian",
        "energy_profile": "drone → spike → drone → spike",
        "itten_colors": ["Red", "Red-Orange", "Yellow-Orange", "Yellow-Green", "Blue-Green", "Blue", "Violet"],
        "music_genres": ["Metal", "Flamenco", "Middle Eastern"],
        "confidence": 0.94,
        "camelot_region": "A",
    },
    {
        "scale": "Locrian",
        "intervals": [0, 1, 3, 5, 6, 8, 10],
        "cinema_genre": "Madness / collapse",
        "cinema_scene_types": "Insanity, chaos, disintegration, breakdown",
        "dramatic_function": "Disintegration, Madness",
        "pendulum_position": -1.0,
        "counterpoint_pair": "Lydian",
        "energy_profile": "unstable → collapse → void",
        "itten_colors": ["Red", "Red-Orange", "Yellow-Orange", "Yellow-Green", "Green", "Blue", "Violet"],
        "music_genres": ["Metal", "Avant-Garde", "Experimental"],
        "confidence": 0.89,
        "camelot_region": "A",
    },
    {
        "scale": "Harmonic Minor",
        "intervals": [0, 2, 3, 5, 7, 8, 11],
        "cinema_genre": "Thriller / passion",
        "cinema_scene_types": "Fatal attraction, obsession, destiny, tension build",
        "dramatic_function": "Fatal attraction, Destiny, Obsession",
        "pendulum_position": -0.4,  # corrected from -0.6 by Grok
        "counterpoint_pair": "Harmonic Major",
        "energy_profile": "tension build → exotic leap → sustain",
        "itten_colors": ["Red", "Orange", "Yellow-Orange", "Yellow-Green", "Blue-Green", "Blue", "Red-Violet"],
        "music_genres": ["Metal", "Classical", "Flamenco", "Middle Eastern"],
        "confidence": 0.76,
        "camelot_region": "A",
    },
    {
        "scale": "Chromatic",
        "intervals": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
        "cinema_genre": "Avant-garde / panic",
        "cinema_scene_types": "Horror buildup, panic, escalation, Scriabin/Eno",
        "dramatic_function": "Escalation, Static tension",
        "pendulum_position": 0.0,
        "counterpoint_pair": "Major Pentatonic",
        "energy_profile": "static pressure → crescendo",
        "itten_colors": ["Red", "Red-Orange", "Orange", "Yellow-Orange", "Yellow", "Yellow-Green",
                         "Green", "Blue-Green", "Blue", "Blue-Violet", "Violet", "Red-Violet"],
        "music_genres": ["Avant-Garde", "Experimental", "Atonal"],
        "confidence": 0.82,
        "camelot_region": "X",  # atonal — no Camelot mapping
    },
    {
        "scale": "Whole Tone",
        "intervals": [0, 2, 4, 6, 8, 10],
        "cinema_genre": "Dream / surreal",
        "cinema_scene_types": "Dream, hallucination, underwater, uncanny",
        "dramatic_function": "Unreality, Uncanny dream",
        "pendulum_position": -0.2,  # corrected from 0.0 by Grok — often eerie
        "counterpoint_pair": "Diminished",
        "energy_profile": "float → blur → float (no gravity)",
        "itten_colors": ["Red", "Orange", "Yellow", "Green", "Blue", "Violet"],
        "music_genres": ["Jazz", "Impressionism", "Film Scores"],
        "confidence": 0.71,
        "camelot_region": "X",  # symmetric — ambiguous Camelot
    },
    {
        "scale": "Diminished",
        "intervals": [0, 2, 3, 5, 6, 8, 9, 11],
        "cinema_genre": "Clockwork thriller",
        "cinema_scene_types": "Mechanical, inevitable, ticking bomb, symmetric evil",
        "dramatic_function": "Inevitability, Mechanical tension",
        "pendulum_position": -0.5,
        "counterpoint_pair": "Whole Tone",
        "energy_profile": "tick → tick → tick → BOOM",
        "itten_colors": ["Red", "Orange", "Yellow-Orange", "Yellow-Green", "Green", "Blue", "Blue-Violet", "Red-Violet"],
        "music_genres": ["Jazz", "Metal", "Horror Scores"],
        "confidence": 0.80,
        "camelot_region": "A",
    },
    # --- Added by Grok 179.0A recommendation ---
    {
        "scale": "Major Pentatonic",
        "intervals": [0, 2, 4, 7, 9],
        "cinema_genre": "Epic / adventure",
        "cinema_scene_types": "Hero journey, boss fight, epic landscape, triumph",
        "dramatic_function": "Heroism, Epic resolution",
        "pendulum_position": 0.6,
        "counterpoint_pair": "Minor Pentatonic",
        "energy_profile": "rise → peak → sustained glory",
        "itten_colors": ["Red", "Orange", "Yellow", "Blue-Green", "Blue-Violet"],
        "music_genres": ["Rock", "Blues", "Country", "Folk"],
        "confidence": 0.87,
        "camelot_region": "B",
    },
    {
        "scale": "Minor Pentatonic",
        "intervals": [0, 3, 5, 7, 10],
        "cinema_genre": "Gritty / street",
        "cinema_scene_types": "Street fight, underground, raw emotion, hip-hop montage",
        "dramatic_function": "Raw struggle, Street truth",
        "pendulum_position": -0.5,
        "counterpoint_pair": "Major Pentatonic",
        "energy_profile": "grind → pulse → grind",
        "itten_colors": ["Red", "Yellow-Orange", "Yellow-Green", "Blue-Green", "Violet"],
        "music_genres": ["Blues", "Rock", "Metal", "Hip-Hop"],
        "confidence": 0.83,
        "camelot_region": "A",
    },
]


class PulseCinemaMatrix:
    """
    Loads and queries the Scale → Cinema Scene matrix.

    Usage:
        matrix = PulseCinemaMatrix()
        row = matrix.get_by_scale("Phrygian")
        counter = matrix.get_counterpoint("Phrygian")  # → "Mixolydian"
        pendulum = matrix.get_pendulum("Phrygian")      # → -0.9
    """

    def __init__(self, csv_path: Optional[str] = None):
        self._rows: Dict[str, CinemaMatrixRow] = {}
        if csv_path and os.path.isfile(csv_path):
            self._load_csv(csv_path)
        else:
            self._load_builtin()

    # --- Public API ---

    def get_by_scale(self, scale: str) -> Optional[CinemaMatrixRow]:
        """Get matrix row by scale name (case-insensitive, partial match)."""
        key = self._normalize(scale)
        if key in self._rows:
            return self._rows[key]
        # Partial match: "minor" → "aeolian"
        for k, row in self._rows.items():
            if key in k or key in row.scale.lower():
                return row
        return None

    def get_counterpoint(self, scale: str) -> Optional[str]:
        """Get the counterpoint pair scale name."""
        row = self.get_by_scale(scale)
        return row.counterpoint_pair if row else None

    def get_pendulum(self, scale: str) -> Optional[float]:
        """Get pendulum position -1.0 (deepest minor) to +1.0 (brightest major)."""
        row = self.get_by_scale(scale)
        return row.pendulum_position if row else None

    def get_itten_colors(self, scale: str) -> List[str]:
        """Get Itten color wheel colors for the scale."""
        row = self.get_by_scale(scale)
        return row.itten_colors if row else []

    def get_energy_profile(self, scale: str) -> Optional[str]:
        """Get energy profile string."""
        row = self.get_by_scale(scale)
        return row.energy_profile if row else None

    def get_dramatic_function(self, scale: str) -> Optional[str]:
        """Get dramatic function for the scale."""
        row = self.get_by_scale(scale)
        return row.dramatic_function if row else None

    def scales_by_pendulum_range(
        self, min_p: float, max_p: float
    ) -> List[CinemaMatrixRow]:
        """Get all scales within a pendulum range."""
        return [
            row for row in self._rows.values()
            if min_p <= row.pendulum_position <= max_p
        ]

    def scales_by_genre(self, genre_keyword: str) -> List[CinemaMatrixRow]:
        """Find scales matching a cinema genre keyword."""
        kw = genre_keyword.lower()
        return [
            row for row in self._rows.values()
            if kw in row.cinema_genre.lower() or kw in row.cinema_scene_types.lower()
        ]

    def nearest_by_pendulum(self, target: float) -> CinemaMatrixRow:
        """Find the scale with pendulum closest to target value."""
        return min(
            self._rows.values(),
            key=lambda r: abs(r.pendulum_position - target),
        )

    def all_scales(self) -> List[CinemaMatrixRow]:
        """Return all matrix rows."""
        return list(self._rows.values())

    def to_dict_list(self) -> List[Dict]:
        """Serialize to list of dicts for REST API."""
        result = []
        for row in self._rows.values():
            result.append({
                "scale": row.scale,
                "intervals": row.intervals,
                "note_count": row.note_count,
                "cinema_genre": row.cinema_genre,
                "cinema_scene_types": row.cinema_scene_types,
                "dramatic_function": row.dramatic_function,
                "pendulum_position": row.pendulum_position,
                "counterpoint_pair": row.counterpoint_pair,
                "energy_profile": row.energy_profile,
                "itten_colors": row.itten_colors,
                "music_genres": row.music_genres,
                "confidence": row.confidence,
                "camelot_region": row.camelot_region,
            })
        return result

    # --- Private ---

    def _normalize(self, name: str) -> str:
        """Normalize scale name for lookup."""
        n = name.lower().strip()
        # Aliases
        aliases = {
            "major": "ionian",
            "natural minor": "aeolian",
            "minor": "aeolian",
        }
        return aliases.get(n, n)

    def _load_builtin(self) -> None:
        """Load the built-in validated matrix."""
        for entry in _BUILTIN_MATRIX:
            row = CinemaMatrixRow(
                scale=entry["scale"],
                intervals=entry["intervals"],
                note_count=len(entry["intervals"]),
                cinema_genre=entry["cinema_genre"],
                cinema_scene_types=entry["cinema_scene_types"],
                dramatic_function=entry["dramatic_function"],
                pendulum_position=entry["pendulum_position"],
                counterpoint_pair=entry["counterpoint_pair"],
                energy_profile=entry["energy_profile"],
                itten_colors=entry["itten_colors"],
                music_genres=entry["music_genres"],
                confidence=entry["confidence"],
                camelot_region=entry["camelot_region"],
            )
            self._rows[self._normalize(row.scale)] = row

    def _load_csv(self, path: str) -> None:
        """Load matrix from CSV file (extended format)."""
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                intervals_str = raw.get("intervals", "")
                intervals = [int(x.strip()) for x in intervals_str.split(",") if x.strip()] if intervals_str else []
                itten_str = raw.get("itten_colors", "")
                itten = [c.strip() for c in itten_str.split(",") if c.strip()] if itten_str else []
                genres_str = raw.get("music_genres", "")
                genres = [g.strip() for g in genres_str.split(",") if g.strip()] if genres_str else []

                row = CinemaMatrixRow(
                    scale=raw.get("scale", "Unknown"),
                    intervals=intervals,
                    note_count=len(intervals),
                    cinema_genre=raw.get("cinema_genre", ""),
                    cinema_scene_types=raw.get("cinema_scene_types", ""),
                    dramatic_function=raw.get("dramatic_function", ""),
                    pendulum_position=float(raw.get("pendulum_position", 0.0)),
                    counterpoint_pair=raw.get("counterpoint_pair", ""),
                    energy_profile=raw.get("energy_profile", ""),
                    itten_colors=itten,
                    music_genres=genres,
                    confidence=float(raw.get("confidence", 0.5)),
                    camelot_region=raw.get("camelot_region", "X"),
                )
                self._rows[self._normalize(row.scale)] = row


# Singleton
_matrix_instance: Optional[PulseCinemaMatrix] = None


def get_cinema_matrix() -> PulseCinemaMatrix:
    """Get or create singleton cinema matrix."""
    global _matrix_instance
    if _matrix_instance is None:
        _matrix_instance = PulseCinemaMatrix()
    return _matrix_instance
