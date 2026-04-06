"""
PULSE Conductor — the heart of the system.

Receives three BPM signals (narrative, visual, audio), fuses them
through the cinema matrix, and produces a PulseScore for each scene.

From the manifesto:
  "PULSE is not an audio encoder running parallel to video.
   PULSE is a conductor. It finds music in the script, looks for it
   in video material, and through the Camelot-Itten circle creates
   a unified score for the film."

MARKER_179.3_PULSE_CONDUCTOR
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.services.pulse_cinema_matrix import (
    CinemaMatrixRow,
    PulseCinemaMatrix,
    get_cinema_matrix,
)
from src.services.pulse_camelot_engine import (
    CamelotEngine,
    CamelotPath,
    get_camelot_engine,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class NarrativeBPM:
    """BPM extracted from script/brief analysis."""
    scene_id: str
    dramatic_function: str  # from matrix: Catharsis, Menace, etc.
    pendulum_position: float  # -1.0 .. +1.0
    estimated_energy: float  # 0.0 .. 1.0
    keywords: List[str] = field(default_factory=list)
    suggested_scale: str = ""  # best-match from matrix
    confidence: float = 0.5


@dataclass
class VisualBPM:
    """BPM extracted from video material (V-JEPA2 or FFmpeg)."""
    scene_id: str
    cuts_per_minute: float  # edit density
    motion_intensity: float  # 0.0 .. 1.0 (internal frame movement)
    dominant_colors: List[str] = field(default_factory=list)
    scene_boundaries: List[float] = field(default_factory=list)  # timestamps
    source: str = "histogram"  # "histogram" | "vjepa2" | "ffmpeg"
    confidence: float = 0.5


@dataclass
class AudioBPM:
    """BPM extracted from audio track (librosa / PULSE native)."""
    bpm: float
    key: str  # e.g. "A minor"
    camelot_key: str  # e.g. "8A"
    downbeats: List[float] = field(default_factory=list)  # timestamps
    phrases: List[Dict[str, Any]] = field(default_factory=list)
    energy_curve: List[float] = field(default_factory=list)
    confidence: float = 0.5
    source: str = "librosa"  # "librosa" | "pulse_native" | "pulse_manifest"


@dataclass
class PulseScore:
    """
    The conductor's score for a single scene.
    This is what comes out of PULSE — the unified interpretation.
    """
    scene_id: str
    camelot_key: str  # resolved Camelot position
    scale: str  # from cinema matrix
    pendulum_position: float  # -1.0 .. +1.0
    dramatic_function: str
    energy_profile: str
    counterpoint_pair: str
    confidence: float  # overall confidence
    alignment: str = "sync"  # "sync" | "counterpoint" | "polyphonic"

    # Source signals
    narrative_bpm: Optional[NarrativeBPM] = None
    visual_bpm: Optional[VisualBPM] = None
    audio_bpm: Optional[AudioBPM] = None

    # Derived
    cinema_genre: str = ""
    itten_colors: List[str] = field(default_factory=list)
    music_genres: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for REST API / DAG storage."""
        return {
            "scene_id": self.scene_id,
            "camelot_key": self.camelot_key,
            "scale": self.scale,
            "pendulum_position": self.pendulum_position,
            "dramatic_function": self.dramatic_function,
            "energy_profile": self.energy_profile,
            "counterpoint_pair": self.counterpoint_pair,
            "confidence": round(self.confidence, 3),
            "alignment": self.alignment,
            "cinema_genre": self.cinema_genre,
            "itten_colors": self.itten_colors,
            "music_genres": self.music_genres,
        }


@dataclass
class FilmPartiture:
    """
    The conductor's score for the entire film — orchestral partiture.
    DAG VETKA = this partiture.
    """
    scores: List[PulseScore]
    camelot_path: Optional[CamelotPath] = None
    tonic_key: str = ""  # the "home key" of the film
    overall_pendulum_range: Tuple[float, float] = (-1.0, 1.0)
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scores": [s.to_dict() for s in self.scores],
            "tonic_key": self.tonic_key,
            "pendulum_range": list(self.overall_pendulum_range),
            "path_smoothness": self.camelot_path.smoothness if self.camelot_path else None,
            "path_max_jump": self.camelot_path.max_jump if self.camelot_path else None,
            "scene_count": len(self.scores),
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Signal weights for fusion
# ---------------------------------------------------------------------------

# When all three signals exist
_WEIGHT_NARRATIVE = 0.35
_WEIGHT_VISUAL = 0.30
_WEIGHT_AUDIO = 0.35

# When only two signals exist
_WEIGHT_PAIR = {
    ("narrative", "visual"): (0.55, 0.45),
    ("narrative", "audio"): (0.45, 0.55),
    ("visual", "audio"): (0.40, 0.60),
}


class PulseConductor:
    """
    The conductor of three rhythms.

    Usage:
        conductor = PulseConductor()

        # Score a single scene
        score = conductor.score_scene(
            scene_id="sc_01",
            narrative=NarrativeBPM(...),
            visual=VisualBPM(...),
            audio=AudioBPM(...),
        )

        # Score entire film
        partiture = conductor.score_film(scenes=[...])
    """

    def __init__(
        self,
        matrix: Optional[PulseCinemaMatrix] = None,
        engine: Optional[CamelotEngine] = None,
    ):
        self._matrix = matrix or get_cinema_matrix()
        self._engine = engine or get_camelot_engine()

    def score_scene(
        self,
        scene_id: str,
        narrative: Optional[NarrativeBPM] = None,
        visual: Optional[VisualBPM] = None,
        audio: Optional[AudioBPM] = None,
    ) -> PulseScore:
        """
        Score a single scene by fusing available BPM signals.

        At least one signal must be present.
        """
        if not any([narrative, visual, audio]):
            # No signals — return neutral
            return PulseScore(
                scene_id=scene_id,
                camelot_key="8B",  # C major — neutral
                scale="Ionian",
                pendulum_position=0.0,
                dramatic_function="Unknown",
                energy_profile="neutral",
                counterpoint_pair="Aeolian",
                confidence=0.0,
            )

        # Step 1: Determine pendulum position (weighted fusion)
        pendulum = self._fuse_pendulum(narrative, visual, audio)

        # Step 2: Find best-matching scale from matrix
        row = self._resolve_scale(pendulum, narrative, visual, audio)

        # Step 3: Determine Camelot key
        camelot_key = self._resolve_camelot(row, audio)

        # Step 4: Detect alignment (sync vs counterpoint)
        alignment = self._detect_alignment(row, audio)

        # Step 5: Compute overall confidence
        confidence = self._compute_confidence(narrative, visual, audio)

        return PulseScore(
            scene_id=scene_id,
            camelot_key=camelot_key,
            scale=row.scale,
            pendulum_position=row.pendulum_position,
            dramatic_function=row.dramatic_function,
            energy_profile=row.energy_profile,
            counterpoint_pair=row.counterpoint_pair,
            confidence=confidence,
            alignment=alignment,
            narrative_bpm=narrative,
            visual_bpm=visual,
            audio_bpm=audio,
            cinema_genre=row.cinema_genre,
            itten_colors=row.itten_colors,
            music_genres=row.music_genres,
        )

    def score_film(
        self,
        scenes: List[Dict[str, Any]],
    ) -> FilmPartiture:
        """
        Score an entire film from scene descriptors.

        Each scene dict should have:
        - scene_id: str
        - narrative: Optional[NarrativeBPM]
        - visual: Optional[VisualBPM]
        - audio: Optional[AudioBPM]
        """
        scores = []
        for scene in scenes:
            score = self.score_scene(
                scene_id=scene.get("scene_id", f"sc_{len(scores)}"),
                narrative=scene.get("narrative"),
                visual=scene.get("visual"),
                audio=scene.get("audio"),
            )
            scores.append(score)

        # Analyze the Camelot path
        camelot_keys = [s.camelot_key for s in scores]
        path = self._engine.plan_path(camelot_keys) if len(camelot_keys) >= 2 else None

        # Determine tonic (most frequent key)
        tonic = self._find_tonic(camelot_keys)

        # Pendulum range
        pendulums = [s.pendulum_position for s in scores]
        p_range = (min(pendulums), max(pendulums)) if pendulums else (-1.0, 1.0)

        return FilmPartiture(
            scores=scores,
            camelot_path=path,
            tonic_key=tonic,
            overall_pendulum_range=p_range,
            created_at=time.time(),
        )

    # --- Private: Fusion ---

    def _fuse_pendulum(
        self,
        narrative: Optional[NarrativeBPM],
        visual: Optional[VisualBPM],
        audio: Optional[AudioBPM],
    ) -> float:
        """Fuse available signals into a single pendulum value."""
        signals: List[Tuple[str, float, float]] = []  # (name, pendulum, weight)

        if narrative:
            signals.append(("narrative", narrative.pendulum_position, _WEIGHT_NARRATIVE))

        if visual:
            # Map visual intensity to pendulum:
            # High motion → positive (action/adventure)
            # Low motion → negative (drama/melancholy)
            visual_pendulum = (visual.motion_intensity - 0.5) * 2.0
            # High cut density → more positive (energy)
            if visual.cuts_per_minute > 10:
                visual_pendulum = min(visual_pendulum + 0.2, 1.0)
            signals.append(("visual", visual_pendulum, _WEIGHT_VISUAL))

        if audio:
            # Audio key → pendulum via Camelot ring
            # Minor (A ring) → negative, Major (B ring) → positive
            if audio.camelot_key.endswith("A"):
                audio_pendulum = -0.5
            elif audio.camelot_key.endswith("B"):
                audio_pendulum = 0.5
            else:
                audio_pendulum = 0.0
            signals.append(("audio", audio_pendulum, _WEIGHT_AUDIO))

        if not signals:
            return 0.0

        # Normalize weights if not all three present
        if len(signals) == 1:
            return signals[0][1]

        if len(signals) == 2:
            pair_key = (signals[0][0], signals[1][0])
            weights = _WEIGHT_PAIR.get(pair_key, (0.5, 0.5))
            return signals[0][1] * weights[0] + signals[1][1] * weights[1]

        # All three — standard weighted sum
        total_w = sum(w for _, _, w in signals)
        return sum(p * w for _, p, w in signals) / total_w

    def _resolve_scale(
        self,
        pendulum: float,
        narrative: Optional[NarrativeBPM],
        visual: Optional[VisualBPM],
        audio: Optional[AudioBPM],
    ) -> CinemaMatrixRow:
        """Find the best-matching scale from the cinema matrix."""
        # If narrative explicitly suggests a scale, prefer it
        if narrative and narrative.suggested_scale:
            row = self._matrix.get_by_scale(narrative.suggested_scale)
            if row:
                return row

        # Otherwise find by pendulum proximity
        return self._matrix.nearest_by_pendulum(pendulum)

    def _resolve_camelot(
        self,
        row: CinemaMatrixRow,
        audio: Optional[AudioBPM],
    ) -> str:
        """Determine the Camelot key for this scene."""
        # If audio provides a detected key, use it
        if audio and audio.camelot_key:
            return audio.camelot_key

        # Otherwise derive from scale's camelot_region
        # Default to the "natural" position for the mode
        if row.camelot_region == "A":
            # Minor — pick a typical position (8A = A minor as default)
            return "8A"
        elif row.camelot_region == "B":
            return "8B"  # C major as default
        else:
            return "8B"  # neutral default

    def _detect_alignment(
        self,
        row: CinemaMatrixRow,
        audio: Optional[AudioBPM],
    ) -> str:
        """
        Detect sync vs counterpoint between scene mood and music mood.

        Nights of Cabiria pattern: scene in minor, music in parallel major.
        """
        if not audio or not audio.camelot_key:
            return "sync"  # no music → sync by default

        # Check if music key's ring matches scene's expected mode
        scene_mode = row.camelot_region  # "A" (minor) or "B" (major)
        music_mode = audio.camelot_key[-1] if audio.camelot_key else ""

        if scene_mode == "X":
            return "sync"  # atonal — can't determine

        if scene_mode == music_mode:
            return "sync"  # same mode — reinforcing

        # Different mode — this is counterpoint
        # Check distance: if same number (parallel keys) → conscious counterpoint
        try:
            from src.services.pulse_camelot_engine import CamelotKey
            music_ck = CamelotKey.parse(audio.camelot_key)
            # If the music is in the parallel key (same number, different ring)
            # that's the classic counterpoint (Nights of Cabiria)
            return "counterpoint"
        except (ValueError, ImportError):
            return "sync"

    def _compute_confidence(
        self,
        narrative: Optional[NarrativeBPM],
        visual: Optional[VisualBPM],
        audio: Optional[AudioBPM],
    ) -> float:
        """
        Overall confidence based on available signals and their individual confidence.
        More signals = higher confidence (agreement bonus).
        """
        confidences = []
        if narrative:
            confidences.append(narrative.confidence)
        if visual:
            confidences.append(visual.confidence)
        if audio:
            confidences.append(audio.confidence)

        if not confidences:
            return 0.0

        avg = sum(confidences) / len(confidences)

        # Bonus for having multiple signals (agreement)
        signal_bonus = {1: 0.0, 2: 0.1, 3: 0.15}
        bonus = signal_bonus.get(len(confidences), 0.15)

        return min(avg + bonus, 1.0)

    def _find_tonic(self, keys: List[str]) -> str:
        """Find the tonic (most frequent key) in a sequence."""
        if not keys:
            return "8B"
        freq: Dict[str, int] = {}
        for k in keys:
            freq[k] = freq.get(k, 0) + 1
        return max(freq, key=lambda x: freq[x])


# Singleton
_conductor_instance: Optional[PulseConductor] = None


def get_pulse_conductor() -> PulseConductor:
    """Get or create singleton PULSE conductor."""
    global _conductor_instance
    if _conductor_instance is None:
        _conductor_instance = PulseConductor()
    return _conductor_instance


# MARKER_PLAYER_LAB_SRT: auto-assembly helpers for N-moment / Favorite-moment markers
def filter_clips_by_lab_markers(
    clips: List[Dict],
    markers: List[Dict],
    *,
    include_untagged: bool = True,
) -> List[Dict]:
    """
    Filter clips for rough cut assembly using VETKA Videoplayer Lab markers.

    Rules:
    - Clips whose entire range is covered only by 'negative' markers → excluded.
    - Clips that overlap at least one 'favorite' marker → included (boosted first).
    - Clips with no markers → included if include_untagged=True.

    Args:
        clips: list of clip dicts with keys: media_path, start_sec, end_sec.
        markers: list of TimeMarker dicts with keys: kind, media_path, start_sec, end_sec.
        include_untagged: whether to include clips that have no markers at all.

    Returns:
        Filtered and ordered list: favorite-marked clips first, then untagged.
    """
    from collections import defaultdict

    # Group markers by media_path
    markers_by_path: Dict[str, List[Dict]] = defaultdict(list)
    for m in markers:
        path = str(m.get("media_path") or "")
        if path:
            markers_by_path[path].append(m)

    favorite: List[Dict] = []
    untagged: List[Dict] = []

    for clip in clips:
        path = str(clip.get("media_path") or clip.get("source_path") or "")
        clip_start = float(clip.get("start_sec") or clip.get("source_start_sec") or 0.0)
        clip_end = float(clip.get("end_sec") or clip.get("source_end_sec") or clip_start)

        relevant = [
            m for m in markers_by_path.get(path, [])
            if float(m.get("end_sec") or m.get("start_sec") or 0) > clip_start
            and float(m.get("start_sec") or 0) < clip_end
        ]

        if not relevant:
            if include_untagged:
                untagged.append(clip)
            continue

        has_favorite = any(m.get("kind") == "favorite" for m in relevant)
        all_negative = all(m.get("kind") == "negative" for m in relevant)

        if all_negative:
            continue  # skip N-only clips
        if has_favorite:
            favorite.append(clip)
        else:
            untagged.append(clip)

    return favorite + untagged


def score_clip_by_lab_markers(clip: Dict, markers: List[Dict]) -> float:
    """
    Return a [0, 1] assembly score for a clip based on lab markers.
    favorite → 1.0, negative → 0.0, mixed/untagged → 0.5.
    Uses marker.score as weight when available.
    """
    path = str(clip.get("media_path") or clip.get("source_path") or "")
    clip_start = float(clip.get("start_sec") or clip.get("source_start_sec") or 0.0)
    clip_end = float(clip.get("end_sec") or clip.get("source_end_sec") or clip_start)

    relevant = [
        m for m in markers
        if str(m.get("media_path") or "") == path
        and float(m.get("end_sec") or m.get("start_sec") or 0) > clip_start
        and float(m.get("start_sec") or 0) < clip_end
    ]
    if not relevant:
        return 0.5

    total_weight = 0.0
    weighted_score = 0.0
    for m in relevant:
        w = float(m.get("score") or 0.7)
        s = 1.0 if m.get("kind") == "favorite" else (0.0 if m.get("kind") == "negative" else 0.5)
        weighted_score += s * w
        total_weight += w

    return weighted_score / total_weight if total_weight > 0 else 0.5
