"""
PULSE Cinema Matrix — Scale → Genre → Cinema Scene → Drama mapping.

Loads the validated matrix (Grok 179.0A, confidence 0.85) and provides
query API for the PULSE conductor.

v2.0 (179.13): Added McKee Triangle coordinates, ISI, BPM range,
polygon notes, cinema_genre_mckee, and 10 new world/ethnic scales.
The Camelot wheel (horizontal) × McKee triangle (vertical) = StorySpace3D.

MARKER_179.1_CINEMA_MATRIX
MARKER_179.13_MCKEE_TRIANGLE
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
    # --- McKee Triangle coordinates (179.13) ---
    triangle_arch: float = 0.5   # Archplot weight (0.0-1.0)
    triangle_mini: float = 0.3   # Miniplot weight (0.0-1.0)
    triangle_anti: float = 0.2   # Antiplot weight (0.0-1.0)
    cinema_genre_mckee: str = ""  # McKee genre mapping (Love Story, Crime, etc.)
    isi: float = 0.0             # Interval Spread Index
    bpm_range: str = ""          # e.g. "90-130"
    polygon_notes: str = ""      # Geometric description of scale polygon


# ---------------------------------------------------------------------------
# Built-in matrix — validated by Grok on 10 films (mean confidence 0.85)
# Corrections applied from 179.0A recon
# ---------------------------------------------------------------------------

_BUILTIN_MATRIX: List[Dict] = [
    # ===================================================================
    # Core 7 modes + extended scales — v2.0 with McKee Triangle coords
    # Source: pulse_cinema_matrix.csv (Opus + Grok, validated on 10 films)
    # Triangle coords from McKee "Story" mapping (179.13)
    # ===================================================================
    {
        "scale": "Ionian",
        "intervals": [0, 2, 4, 5, 7, 9, 11],
        "cinema_genre": "Drama / happy end",
        "cinema_scene_types": "Victory, reunion, finale, wedding",
        "dramatic_function": "Catharsis / Resolution",
        "pendulum_position": 0.8,
        "counterpoint_pair": "Aeolian",
        "energy_profile": "peak → release",
        "itten_colors": ["Red", "Orange", "Yellow", "Green", "Blue", "Violet"],
        "music_genres": ["Pop", "Rock", "Classical", "Folk"],
        "confidence": 0.92,
        "camelot_region": "B",
        "triangle_arch": 0.8, "triangle_mini": 0.15, "triangle_anti": 0.05,
        "cinema_genre_mckee": "Love Story, Education Plot, Redemption",
        "isi": 0.58, "bpm_range": "90-130",
        "polygon_notes": "Balanced heptagon — stable and resolved",
    },
    {
        "scale": "Dorian",
        "intervals": [0, 2, 3, 5, 7, 9, 10],
        "cinema_genre": "Noir / detective",
        "cinema_scene_types": "Night city, noir, detective office, jazz club",
        "dramatic_function": "Mystery / Cool tension",
        "pendulum_position": -0.4,
        "counterpoint_pair": "Mixolydian",
        "energy_profile": "low → building",
        "itten_colors": ["Red", "Orange", "Yellow-Orange", "Green", "Blue-Violet", "Violet"],
        "music_genres": ["Jazz", "Rock", "Blues", "Funk"],
        "confidence": 0.79,
        "camelot_region": "A",
        "triangle_arch": 0.4, "triangle_mini": 0.5, "triangle_anti": 0.1,
        "cinema_genre_mckee": "Crime Story, Social Drama",
        "isi": 0.58, "bpm_range": "90-120",
        "polygon_notes": "Minor-flavored asymmetric heptagon",
    },
    {
        "scale": "Phrygian",
        "intervals": [0, 1, 3, 5, 7, 8, 10],
        "cinema_genre": "Horror / ritual",
        "cinema_scene_types": "Threat, ritual, ancient evil, dungeon",
        "dramatic_function": "Menace / Ritual",
        "pendulum_position": -0.8,
        "counterpoint_pair": "Lydian",
        "energy_profile": "building → peak",
        "itten_colors": ["Red", "Red-Orange", "Yellow-Orange", "Green", "Blue", "Violet"],
        "music_genres": ["Metal", "Flamenco", "Middle Eastern"],
        "confidence": 0.94,
        "camelot_region": "A",
        "triangle_arch": 0.5, "triangle_mini": 0.1, "triangle_anti": 0.4,
        "cinema_genre_mckee": "Horror, Thriller",
        "isi": 0.58, "bpm_range": "110-160",
        "polygon_notes": "Dark tension heptagon — flat 2 creates dread",
    },
    {
        "scale": "Lydian",
        "intervals": [0, 2, 4, 6, 7, 9, 11],
        "cinema_genre": "Fantasy / wonder",
        "cinema_scene_types": "Wonder, flight, dream, fantasy world",
        "dramatic_function": "Wonder / Aspiration",
        "pendulum_position": 0.9,
        "counterpoint_pair": "Locrian",
        "energy_profile": "low → floating",
        "itten_colors": ["Red", "Orange", "Yellow", "Green", "Blue-Green", "Blue-Violet", "Red-Violet"],
        "music_genres": ["Jazz", "Film Scores", "Progressive Rock"],
        "confidence": 0.85,
        "camelot_region": "B",
        "triangle_arch": 0.7, "triangle_mini": 0.2, "triangle_anti": 0.1,
        "cinema_genre_mckee": "Fantasy, Sci-Fi, Coming of Age",
        "isi": 0.58, "bpm_range": "80-120",
        "polygon_notes": "Bright uplift heptagon — raised 4th = magic",
    },
    {
        "scale": "Mixolydian",
        "intervals": [0, 2, 4, 5, 7, 9, 10],
        "cinema_genre": "Adventure / drive",
        "cinema_scene_types": "Chase, road, journey, cowboy sunset",
        "dramatic_function": "Adventure / Drive",
        "pendulum_position": 0.5,
        "counterpoint_pair": "Phrygian",
        "energy_profile": "building → sustained",
        "itten_colors": ["Red", "Orange", "Yellow", "Yellow-Green", "Blue-Green", "Blue-Violet", "Violet"],
        "music_genres": ["Blues", "Rock", "Country", "Funk"],
        "confidence": 0.88,
        "camelot_region": "B",
        "triangle_arch": 0.85, "triangle_mini": 0.1, "triangle_anti": 0.05,
        "cinema_genre_mckee": "Action Adventure, Western",
        "isi": 0.58, "bpm_range": "100-140",
        "polygon_notes": "Bluesy flat 7 heptagon — forward momentum",
    },
    {
        "scale": "Aeolian",
        "intervals": [0, 2, 3, 5, 7, 8, 10],
        "cinema_genre": "Melodrama / loss",
        "cinema_scene_types": "Loss, farewell, loneliness, funeral",
        "dramatic_function": "Grief / Melancholy",
        "pendulum_position": -0.7,
        "counterpoint_pair": "Ionian",
        "energy_profile": "low → sustained low",
        "itten_colors": ["Red", "Orange", "Yellow-Orange", "Yellow-Green", "Blue-Green", "Blue", "Violet"],
        "music_genres": ["Rock", "Metal", "Classical", "Pop Ballads"],
        "confidence": 0.91,
        "camelot_region": "A",
        "triangle_arch": 0.4, "triangle_mini": 0.5, "triangle_anti": 0.1,
        "cinema_genre_mckee": "Social Drama, Disillusionment Plot, War",
        "isi": 0.58, "bpm_range": "70-100",
        "polygon_notes": "Melancholic heptagon — natural sadness",
    },
    {
        "scale": "Locrian",
        "intervals": [0, 1, 3, 5, 6, 8, 10],
        "cinema_genre": "Madness / collapse",
        "cinema_scene_types": "Madness, chaos, collapse, asylum",
        "dramatic_function": "Disintegration / Madness",
        "pendulum_position": -1.0,
        "counterpoint_pair": "Lydian",
        "energy_profile": "erratic spikes",
        "itten_colors": ["Red", "Red-Orange", "Yellow-Orange", "Yellow-Green", "Green", "Blue", "Violet"],
        "music_genres": ["Metal", "Avant-Garde", "Experimental"],
        "confidence": 0.89,
        "camelot_region": "A",
        "triangle_arch": 0.1, "triangle_mini": 0.1, "triangle_anti": 0.8,
        "cinema_genre_mckee": "Anti-Structure, Avant-Garde",
        "isi": 0.58, "bpm_range": "120-180",
        "polygon_notes": "Unstable heptagon — dim5 = nothing holds",
    },
    {
        "scale": "Harmonic Minor",
        "intervals": [0, 2, 3, 5, 7, 8, 11],
        "cinema_genre": "Thriller / passion",
        "cinema_scene_types": "Fatal passion, flamenco, destiny, betrayal",
        "dramatic_function": "Fatal attraction / Destiny",
        "pendulum_position": -0.6,
        "counterpoint_pair": "Harmonic Major",
        "energy_profile": "building → explosive peak",
        "itten_colors": ["Red", "Orange", "Yellow-Orange", "Yellow-Green", "Blue-Green", "Blue", "Red-Violet"],
        "music_genres": ["Metal", "Classical", "Flamenco", "Middle Eastern"],
        "confidence": 0.76,
        "camelot_region": "A",
        "triangle_arch": 0.6, "triangle_mini": 0.3, "triangle_anti": 0.1,
        "cinema_genre_mckee": "Thriller, Crime, Love Story (tragic)",
        "isi": 1.14, "bpm_range": "100-140",
        "polygon_notes": "Exotic leap heptagon — 3H interval = surprise",
    },
    {
        "scale": "Melodic Minor",
        "intervals": [0, 2, 3, 5, 7, 9, 11],
        "cinema_genre": "Jazz / inner growth",
        "cinema_scene_types": "Jazz club confession, fusion scene, inner growth",
        "dramatic_function": "Subtle transformation",
        "pendulum_position": -0.3,
        "counterpoint_pair": "Melodic Major",
        "energy_profile": "low → gentle arc",
        "itten_colors": ["Red", "Orange", "Yellow-Orange", "Yellow-Green", "Blue-Green", "Blue-Violet", "Red-Violet"],
        "music_genres": ["Jazz", "Fusion", "Film Scores"],
        "confidence": 0.78,
        "camelot_region": "A",
        "triangle_arch": 0.3, "triangle_mini": 0.6, "triangle_anti": 0.1,
        "cinema_genre_mckee": "Education Plot, Redemption Plot",
        "isi": 0.58, "bpm_range": "80-110",
        "polygon_notes": "Ascending flow heptagon — gradual change",
    },
    {
        "scale": "Major Pentatonic",
        "intervals": [0, 2, 4, 7, 9],
        "cinema_genre": "Epic / adventure",
        "cinema_scene_types": "Childhood, simplicity, folk village, first love",
        "dramatic_function": "Innocence / Nostalgia",
        "pendulum_position": 0.6,
        "counterpoint_pair": "Minor Pentatonic",
        "energy_profile": "low → gentle peak",
        "itten_colors": ["Red", "Orange", "Yellow", "Blue-Green", "Blue-Violet"],
        "music_genres": ["Rock", "Blues", "Country", "Folk"],
        "confidence": 0.87,
        "camelot_region": "B",
        "triangle_arch": 0.85, "triangle_mini": 0.1, "triangle_anti": 0.05,
        "cinema_genre_mckee": "Comedy, Coming of Age, Fantasy",
        "isi": 0.42, "bpm_range": "80-120",
        "polygon_notes": "Simple pentagon — universal story shape",
    },
    {
        "scale": "Minor Pentatonic",
        "intervals": [0, 3, 5, 7, 10],
        "cinema_genre": "Gritty / street",
        "cinema_scene_types": "Blues bar, poverty, endurance, prison",
        "dramatic_function": "Endurance / Grit",
        "pendulum_position": -0.5,
        "counterpoint_pair": "Major Pentatonic",
        "energy_profile": "sustained mid",
        "itten_colors": ["Red", "Yellow-Orange", "Yellow-Green", "Blue-Green", "Violet"],
        "music_genres": ["Blues", "Rock", "Metal", "Hip-Hop"],
        "confidence": 0.83,
        "camelot_region": "A",
        "triangle_arch": 0.6, "triangle_mini": 0.3, "triangle_anti": 0.1,
        "cinema_genre_mckee": "Social Drama, Crime, War",
        "isi": 0.67, "bpm_range": "80-110",
        "polygon_notes": "Bluesy pentagon — stubbornness",
    },
    # --- Blues & extended scales (179.13) ---
    {
        "scale": "Minor Blues",
        "intervals": [0, 3, 5, 6, 7, 10],
        "cinema_genre": "Noir / defeat",
        "cinema_scene_types": "Smoking in rain, gambling loss, betrayal aftermath",
        "dramatic_function": "Defeat / Resignation",
        "pendulum_position": -0.6,
        "counterpoint_pair": "Major Blues",
        "energy_profile": "low → sustained",
        "itten_colors": ["Red", "Yellow-Orange", "Yellow-Green", "Green", "Blue-Green", "Violet"],
        "music_genres": ["Blues", "Jazz", "Soul"],
        "confidence": 0.80,
        "camelot_region": "A",
        "triangle_arch": 0.4, "triangle_mini": 0.5, "triangle_anti": 0.1,
        "cinema_genre_mckee": "Disillusionment, Noir",
        "isi": 1.0, "bpm_range": "70-100",
        "polygon_notes": "Gritty hexagon — acceptance of loss",
    },
    {
        "scale": "Major Blues",
        "intervals": [0, 2, 3, 4, 7, 9],
        "cinema_genre": "Comedy / heist",
        "cinema_scene_types": "Lucky break, cabaret, swing dance, heist fun",
        "dramatic_function": "Comic relief / Joy",
        "pendulum_position": 0.4,
        "counterpoint_pair": "Minor Blues",
        "energy_profile": "mid → bouncy peaks",
        "itten_colors": ["Red", "Orange", "Yellow-Orange", "Yellow", "Blue-Green", "Blue-Violet"],
        "music_genres": ["Blues", "Jazz", "Swing", "Soul"],
        "confidence": 0.80,
        "camelot_region": "B",
        "triangle_arch": 0.7, "triangle_mini": 0.2, "triangle_anti": 0.1,
        "cinema_genre_mckee": "Comedy, Caper, Musical",
        "isi": 0.71, "bpm_range": "110-140",
        "polygon_notes": "Upbeat hexagon — playful energy",
    },
    {
        "scale": "Chromatic",
        "intervals": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
        "cinema_genre": "Avant-garde / panic",
        "cinema_scene_types": "Escalating horror, panic attack, paranoia",
        "dramatic_function": "Escalation / Stasis tension",
        "pendulum_position": 0.0,
        "counterpoint_pair": "Whole Tone",
        "energy_profile": "sustained → spike",
        "itten_colors": ["Red", "Red-Orange", "Orange", "Yellow-Orange", "Yellow", "Yellow-Green",
                         "Green", "Blue-Green", "Blue", "Blue-Violet", "Violet", "Red-Violet"],
        "music_genres": ["Avant-Garde", "Experimental", "Atonal"],
        "confidence": 0.82,
        "camelot_region": "X",
        "triangle_arch": 0.1, "triangle_mini": 0.1, "triangle_anti": 0.8,
        "cinema_genre_mckee": "Horror, Anti-Structure, Psychological Thriller",
        "isi": 0.0, "bpm_range": "varies",
        "polygon_notes": "Perfect dodecagon (circle) — no form = pure dread (Scriabin/Eno)",
    },
    {
        "scale": "Whole Tone",
        "intervals": [0, 2, 4, 6, 8, 10],
        "cinema_genre": "Dream / surreal",
        "cinema_scene_types": "Dream sequence, hallucination, underwater, limbo",
        "dramatic_function": "Unreality / Dream",
        "pendulum_position": 0.0,
        "counterpoint_pair": "Chromatic",
        "energy_profile": "floating sustained",
        "itten_colors": ["Red", "Orange", "Yellow", "Green", "Blue", "Violet"],
        "music_genres": ["Jazz", "Impressionism", "Film Scores"],
        "confidence": 0.71,
        "camelot_region": "X",
        "triangle_arch": 0.1, "triangle_mini": 0.4, "triangle_anti": 0.5,
        "cinema_genre_mckee": "Fantasy (surreal), Art Film, Non-Commercial",
        "isi": 0.0, "bpm_range": "60-90",
        "polygon_notes": "Perfect hexagon — no gravity (Debussy)",
    },
    {
        "scale": "Diminished",
        "intervals": [0, 2, 3, 5, 6, 8, 9, 11],
        "cinema_genre": "Clockwork thriller",
        "cinema_scene_types": "Ticking clock, villain pursuit, mechanical trap",
        "dramatic_function": "Ticking clock / Pursuit",
        "pendulum_position": -0.3,
        "counterpoint_pair": "Augmented",
        "energy_profile": "building → relentless",
        "itten_colors": ["Red", "Orange", "Yellow-Orange", "Yellow-Green", "Green", "Blue", "Blue-Violet", "Red-Violet"],
        "music_genres": ["Jazz", "Metal", "Horror Scores"],
        "confidence": 0.80,
        "camelot_region": "A",
        "triangle_arch": 0.5, "triangle_mini": 0.1, "triangle_anti": 0.4,
        "cinema_genre_mckee": "Thriller, Horror Score",
        "isi": 0.58, "bpm_range": "120-160",
        "polygon_notes": "Symmetric octagon — mechanical inevitability",
    },
    # --- World / Ethnic scales (179.13) ---
    {
        "scale": "Gypsy",
        "intervals": [0, 2, 3, 6, 7, 8, 11],
        "cinema_genre": "Carnival / freedom",
        "cinema_scene_types": "Carnival, gypsy camp, wild freedom, dark feast",
        "dramatic_function": "Wild freedom",
        "pendulum_position": -0.2,
        "counterpoint_pair": "Hungarian Minor",
        "energy_profile": "peaks and valleys",
        "itten_colors": ["Red", "Orange", "Yellow-Orange", "Green", "Blue-Green", "Blue", "Red-Violet"],
        "music_genres": ["Romani", "Folk", "Film Scores"],
        "confidence": 0.75,
        "camelot_region": "A",
        "triangle_arch": 0.4, "triangle_mini": 0.3, "triangle_anti": 0.3,
        "cinema_genre_mckee": "Period Film, Musical, Social Drama",
        "isi": 1.14, "bpm_range": "100-140",
        "polygon_notes": "Irregular heptagon with holes — unpredictable passion",
    },
    {
        "scale": "Arabic",
        "intervals": [0, 2, 4, 5, 6, 8, 10],
        "cinema_genre": "Intrigue / desert",
        "cinema_scene_types": "Desert, palace, conspiracy, bazaar",
        "dramatic_function": "Intrigue / Vastness",
        "pendulum_position": -0.4,
        "counterpoint_pair": "Spanish",
        "energy_profile": "sustained → building",
        "itten_colors": ["Red", "Orange", "Yellow", "Yellow-Green", "Green", "Blue", "Violet"],
        "music_genres": ["Arabic", "Middle Eastern", "Film Scores"],
        "confidence": 0.75,
        "camelot_region": "A",
        "triangle_arch": 0.5, "triangle_mini": 0.3, "triangle_anti": 0.2,
        "cinema_genre_mckee": "Political Thriller, Historical, War",
        "isi": 0.58, "bpm_range": "80-120",
        "polygon_notes": "Neutral modal heptagon — ancient power",
    },
    {
        "scale": "Spanish",
        "intervals": [0, 1, 3, 4, 5, 7, 8, 10],
        "cinema_genre": "Passion / confrontation",
        "cinema_scene_types": "Flamenco stage, Latin passion, bullfight",
        "dramatic_function": "Passionate confrontation",
        "pendulum_position": -0.3,
        "counterpoint_pair": "Arabic",
        "energy_profile": "explosive peaks",
        "itten_colors": ["Red", "Red-Orange", "Yellow-Orange", "Yellow", "Yellow-Green", "Blue-Green", "Blue", "Violet"],
        "music_genres": ["Flamenco", "Latin", "Film Scores"],
        "confidence": 0.75,
        "camelot_region": "A",
        "triangle_arch": 0.6, "triangle_mini": 0.2, "triangle_anti": 0.2,
        "cinema_genre_mckee": "Period Drama, Musical, Crime",
        "isi": 0.58, "bpm_range": "110-150",
        "polygon_notes": "Passionate octagon — 8 notes = dense emotion",
    },
    {
        "scale": "Japanese (In Sen)",
        "intervals": [0, 1, 5, 7, 10],
        "cinema_genre": "Zen / meditation",
        "cinema_scene_types": "Temple, meditation, samurai preparation, zen garden",
        "dramatic_function": "Stillness / Honor",
        "pendulum_position": -0.3,
        "counterpoint_pair": "Ryuku",
        "energy_profile": "very low sustained",
        "itten_colors": ["Red", "Red-Orange", "Yellow-Green", "Blue-Green", "Blue"],
        "music_genres": ["Japanese Traditional", "Ambient", "Film Scores"],
        "confidence": 0.72,
        "camelot_region": "A",
        "triangle_arch": 0.2, "triangle_mini": 0.7, "triangle_anti": 0.1,
        "cinema_genre_mckee": "Art Film, Period Drama, Non-Commercial",
        "isi": 1.71, "bpm_range": "50-80",
        "polygon_notes": "Sparse pentagon with wide gaps — silence between notes",
    },
    {
        "scale": "Egyptian",
        "intervals": [0, 2, 5, 7, 10],
        "cinema_genre": "Ancient / mystery",
        "cinema_scene_types": "Ancient tomb, pharaoh court, desert crossing",
        "dramatic_function": "Ancient mystery",
        "pendulum_position": -0.4,
        "counterpoint_pair": "Pelog",
        "energy_profile": "low → building slow",
        "itten_colors": ["Red", "Orange", "Yellow-Green", "Blue-Green", "Violet"],
        "music_genres": ["World", "Film Scores", "Ambient"],
        "confidence": 0.72,
        "camelot_region": "A",
        "triangle_arch": 0.5, "triangle_mini": 0.3, "triangle_anti": 0.2,
        "cinema_genre_mckee": "Historical, Adventure, Horror",
        "isi": 0.67, "bpm_range": "70-100",
        "polygon_notes": "Ancient pentagon — sparse and dry",
    },
    {
        "scale": "Phrygian Dominant",
        "intervals": [0, 1, 4, 5, 7, 8, 10],
        "cinema_genre": "Exotic danger",
        "cinema_scene_types": "Eastern marketplace, exotic danger, ambush",
        "dramatic_function": "Exotic danger",
        "pendulum_position": -0.5,
        "counterpoint_pair": "Double Harmonic",
        "energy_profile": "building → sharp peak",
        "itten_colors": ["Red", "Red-Orange", "Yellow", "Yellow-Green", "Blue-Green", "Blue", "Violet"],
        "music_genres": ["Middle Eastern", "Metal", "Flamenco"],
        "confidence": 0.75,
        "camelot_region": "A",
        "triangle_arch": 0.6, "triangle_mini": 0.1, "triangle_anti": 0.3,
        "cinema_genre_mckee": "Action, Thriller (exotic setting)",
        "isi": 1.14, "bpm_range": "110-150",
        "polygon_notes": "Dominant heptagon with augmented 2nd — surprise and threat",
    },
    {
        "scale": "Raga Bhairav",
        "intervals": [0, 1, 4, 5, 7, 8, 11],
        "cinema_genre": "Sacred / mystical",
        "cinema_scene_types": "Mystical ritual, spiritual journey, temple dawn",
        "dramatic_function": "Sacred / Mystical",
        "pendulum_position": -0.4,
        "counterpoint_pair": "Raga Gamanasrama",
        "energy_profile": "very low → transcendent",
        "itten_colors": ["Red", "Red-Orange", "Yellow", "Yellow-Green", "Blue-Green", "Blue", "Red-Violet"],
        "music_genres": ["Indian Classical", "World", "Ambient"],
        "confidence": 0.70,
        "camelot_region": "A",
        "triangle_arch": 0.2, "triangle_mini": 0.6, "triangle_anti": 0.2,
        "cinema_genre_mckee": "Art Film, Spiritual Drama, World Cinema",
        "isi": 1.14, "bpm_range": "50-90",
        "polygon_notes": "Mystic heptagon — two clusters create tension between earth and sky",
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

    def get_triangle_position(self, scale: str) -> Optional[Tuple[float, float, float]]:
        """Get McKee triangle coordinates (arch, mini, anti) for a scale."""
        row = self.get_by_scale(scale)
        if not row:
            return None
        return (row.triangle_arch, row.triangle_mini, row.triangle_anti)

    def scales_by_triangle_region(
        self, min_arch: float = 0.0, min_mini: float = 0.0, min_anti: float = 0.0,
    ) -> List[CinemaMatrixRow]:
        """Get scales where triangle weight exceeds threshold."""
        return [
            row for row in self._rows.values()
            if row.triangle_arch >= min_arch
            and row.triangle_mini >= min_mini
            and row.triangle_anti >= min_anti
        ]

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
                "triangle_position": {
                    "arch": row.triangle_arch,
                    "mini": row.triangle_mini,
                    "anti": row.triangle_anti,
                },
                "cinema_genre_mckee": row.cinema_genre_mckee,
                "isi": row.isi,
                "bpm_range": row.bpm_range,
                "polygon_notes": row.polygon_notes,
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
                triangle_arch=entry.get("triangle_arch", 0.5),
                triangle_mini=entry.get("triangle_mini", 0.3),
                triangle_anti=entry.get("triangle_anti", 0.2),
                cinema_genre_mckee=entry.get("cinema_genre_mckee", ""),
                isi=entry.get("isi", 0.0),
                bpm_range=entry.get("bpm_range", ""),
                polygon_notes=entry.get("polygon_notes", ""),
            )
            self._rows[self._normalize(row.scale)] = row

    def _load_csv(self, path: str) -> None:
        """Load matrix from CSV file (extended v2 format with McKee triangle)."""
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                intervals_str = raw.get("intervals", "")
                intervals = [int(x.strip()) for x in intervals_str.split(",") if x.strip()] if intervals_str else []
                itten_str = raw.get("itten_colors", raw.get("color_mood_itten", ""))
                itten = [c.strip() for c in itten_str.split(",") if c.strip()] if itten_str else []
                genres_str = raw.get("music_genres", "")
                genres = [g.strip() for g in genres_str.split(",") if g.strip()] if genres_str else []

                # Scale name: handle CSV column "scale_name" or "scale"
                scale_name = raw.get("scale_name", raw.get("scale", "Unknown"))
                # Strip parenthetical aliases like "Ionian (Major)" → "Ionian"
                if "(" in scale_name:
                    scale_name = scale_name.split("(")[0].strip()

                row = CinemaMatrixRow(
                    scale=scale_name,
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
                    triangle_arch=float(raw.get("triangle_arch", 0.5)),
                    triangle_mini=float(raw.get("triangle_mini", 0.3)),
                    triangle_anti=float(raw.get("triangle_anti", 0.2)),
                    cinema_genre_mckee=raw.get("cinema_genre_mcKee", raw.get("cinema_genre_mckee", "")),
                    isi=float(raw.get("ISI", raw.get("isi", 0.0))),
                    bpm_range=raw.get("bpm_range", ""),
                    polygon_notes=raw.get("polygon_notes", ""),
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
