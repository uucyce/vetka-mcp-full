"""
PULSE Auto-Montage Engine — 3 modes of intelligent assembly.

Architecture doc §7: "PULSE auto-montage and PULSE-assisted edits ALWAYS create
a new timeline tab. Name: {project}_cut-{NN+1}. The previous timeline becomes
read-only. NEVER overwrite existing work."

Three modes:
  A) Favorite Assembly — takes favorite-time markers, finds natural in/out
     boundaries, orders by script or time, places cuts at BPM sync points.
  B) Script-driven — matches script scenes to available material via similarity,
     places cuts at BPM sync points following script structure.
  C) Music-driven — analyzes music BPM/key/energy, matches video clips to music
     sections via Camelot/mood alignment.

MARKER_180.12_PULSE_AUTO_MONTAGE
"""
from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.services.pulse_conductor import (
    AudioBPM,
    FilmPartiture,
    NarrativeBPM,
    PulseConductor,
    PulseScore,
    VisualBPM,
    get_pulse_conductor,
)
from src.services.pulse_camelot_engine import get_camelot_engine
from src.services.pulse_script_analyzer import get_script_analyzer


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MontageClip:
    """A single clip in the assembled timeline."""
    clip_id: str
    source_path: str
    in_sec: float         # in-point in source
    out_sec: float        # out-point in source
    timeline_start: float # position on output timeline
    timeline_end: float   # position on output timeline
    scene_id: str = ""
    camelot_key: str = ""
    energy: float = 0.5
    pendulum: float = 0.0
    confidence: float = 0.5
    reason: str = ""      # why this clip was placed here

    @property
    def duration(self) -> float:
        return self.out_sec - self.in_sec

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "source_path": self.source_path,
            "in_sec": round(self.in_sec, 3),
            "out_sec": round(self.out_sec, 3),
            "timeline_start": round(self.timeline_start, 3),
            "timeline_end": round(self.timeline_end, 3),
            "duration": round(self.duration, 3),
            "scene_id": self.scene_id,
            "camelot_key": self.camelot_key,
            "energy": round(self.energy, 3),
            "pendulum": round(self.pendulum, 3),
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
        }


@dataclass
class MontageResult:
    """Result of an auto-montage operation."""
    timeline_id: str
    timeline_label: str
    mode: str             # "favorites" | "script" | "music"
    clips: List[MontageClip]
    total_duration: float
    clip_count: int
    created_at: float
    # Diagnostics
    scores_used: int = 0
    sync_points_hit: int = 0
    camelot_smoothness: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeline_id": self.timeline_id,
            "timeline_label": self.timeline_label,
            "mode": self.mode,
            "clips": [c.to_dict() for c in self.clips],
            "total_duration": round(self.total_duration, 3),
            "clip_count": self.clip_count,
            "created_at": self.created_at,
            "scores_used": self.scores_used,
            "sync_points_hit": self.sync_points_hit,
            "camelot_smoothness": round(self.camelot_smoothness, 3),
            "warnings": self.warnings,
        }


@dataclass
class FavoriteMarker:
    """A favorite-time marker from source material."""
    marker_id: str
    media_path: str
    start_sec: float
    end_sec: float
    score: float = 1.0
    text: str = ""
    kind: str = "favorite"


@dataclass
class MaterialAsset:
    """A piece of source material available for montage."""
    asset_id: str
    source_path: str
    duration_sec: float
    camelot_key: str = ""
    energy: float = 0.5
    pendulum: float = 0.0
    scene_id: str = ""
    tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Auto-Montage Engine
# ---------------------------------------------------------------------------

class PulseAutoMontage:
    """
    The auto-montage engine. Three modes, one safety rule:
    ALWAYS creates a new timeline. NEVER overwrites.

    Usage:
        engine = PulseAutoMontage()

        # Mode A: Favorite assembly
        result = engine.assemble_favorites(
            markers=[...],
            project_name="my_film",
            version=1,
        )

        # Mode B: Script-driven
        result = engine.assemble_from_script(
            script_text="EXT. Berlin...",
            materials=[...],
            project_name="my_film",
            version=2,
        )

        # Mode C: Music-driven
        result = engine.assemble_from_music(
            music_audio=AudioBPM(...),
            materials=[...],
            project_name="my_film",
            version=3,
        )
    """

    def __init__(
        self,
        conductor: Optional[PulseConductor] = None,
        handle_duration_sec: float = 1.0,
        min_clip_duration_sec: float = 0.5,
    ):
        self._conductor = conductor or get_pulse_conductor()
        self._camelot = get_camelot_engine()
        self._handle_duration = handle_duration_sec
        self._min_clip_duration = min_clip_duration_sec

    def _make_timeline_id(self, project_name: str, version: int) -> Tuple[str, str]:
        """Generate timeline ID and label. §7.1: {project}_cut-{NN+1}."""
        label = f"{project_name}_cut-{version:02d}"
        tid = f"tl_{label}_{uuid.uuid4().hex[:8]}"
        return tid, label

    # ===================================================================
    # MODE A: Favorite Assembly (Architecture doc §7.2 row 1)
    # ===================================================================

    def assemble_favorites(
        self,
        markers: List[FavoriteMarker],
        project_name: str = "project",
        version: int = 1,
        order_by: str = "time",  # "time" | "energy" | "script"
        sync_points: Optional[List[float]] = None,
    ) -> MontageResult:
        """
        Assemble timeline from favorite-time markers.

        1. Takes favorite markers from source material
        2. Finds natural in/out boundaries around each marker
        3. Orders by time, energy, or script order
        4. Places cuts at BPM sync points when available
        5. Creates new timeline — NEVER overwrites

        Architecture doc §7.2 row 1: "Favorite assembly"
        """
        tid, label = self._make_timeline_id(project_name, version)
        warnings: List[str] = []

        if not markers:
            return MontageResult(
                timeline_id=tid,
                timeline_label=label,
                mode="favorites",
                clips=[],
                total_duration=0.0,
                clip_count=0,
                created_at=time.time(),
                warnings=["No favorite markers provided"],
            )

        # Filter active markers with valid time range
        valid_markers = [
            m for m in markers
            if m.end_sec > m.start_sec and m.end_sec - m.start_sec >= self._min_clip_duration
        ]

        if not valid_markers:
            warnings.append("All markers had invalid time ranges")
            return MontageResult(
                timeline_id=tid,
                timeline_label=label,
                mode="favorites",
                clips=[],
                total_duration=0.0,
                clip_count=0,
                created_at=time.time(),
                warnings=warnings,
            )

        # Determine natural in/out boundaries (add handles)
        expanded = []
        for m in valid_markers:
            in_pt = max(0.0, m.start_sec - self._handle_duration)
            out_pt = m.end_sec + self._handle_duration
            expanded.append((m, in_pt, out_pt))

        # Order
        if order_by == "energy":
            expanded.sort(key=lambda x: x[0].score, reverse=True)
        elif order_by == "script":
            expanded.sort(key=lambda x: x[0].start_sec)
        else:  # time (default)
            expanded.sort(key=lambda x: x[0].start_sec)

        # Build clips, snapping to sync points if available
        clips: List[MontageClip] = []
        timeline_cursor = 0.0
        sync_hits = 0

        for marker, in_pt, out_pt in expanded:
            duration = out_pt - in_pt

            # Try to snap cut point to nearest sync point
            if sync_points:
                best_snap = self._find_nearest_sync(timeline_cursor, sync_points)
                if best_snap is not None and abs(best_snap - timeline_cursor) < 2.0:
                    timeline_cursor = best_snap
                    sync_hits += 1

            clip = MontageClip(
                clip_id=f"fav_{uuid.uuid4().hex[:8]}",
                source_path=marker.media_path,
                in_sec=in_pt,
                out_sec=out_pt,
                timeline_start=timeline_cursor,
                timeline_end=timeline_cursor + duration,
                scene_id=marker.marker_id,
                confidence=marker.score,
                reason=f"Favorite marker: {marker.text or 'untitled'}",
            )
            clips.append(clip)
            timeline_cursor += duration

        total_duration = timeline_cursor

        return MontageResult(
            timeline_id=tid,
            timeline_label=label,
            mode="favorites",
            clips=clips,
            total_duration=total_duration,
            clip_count=len(clips),
            created_at=time.time(),
            sync_points_hit=sync_hits,
            warnings=warnings,
        )

    # ===================================================================
    # MODE B: Script-Driven (Architecture doc §7.2 row 2)
    # ===================================================================

    def assemble_from_script(
        self,
        script_text: str,
        materials: List[MaterialAsset],
        project_name: str = "project",
        version: int = 1,
        sync_points: Optional[List[float]] = None,
    ) -> MontageResult:
        """
        Assemble timeline driven by script structure.

        1. Parse script → NarrativeBPM scenes
        2. Score each scene via PULSE conductor
        3. Match script scenes to available material (by similarity)
        4. Place cuts at BPM sync points
        5. Creates new timeline — NEVER overwrites

        Architecture doc §7.2 row 2: "Script-driven"
        """
        tid, label = self._make_timeline_id(project_name, version)
        warnings: List[str] = []

        # Parse script
        analyzer = get_script_analyzer()
        narrative_scenes = analyzer.analyze(script_text)

        if not narrative_scenes:
            return MontageResult(
                timeline_id=tid,
                timeline_label=label,
                mode="script",
                clips=[],
                total_duration=0.0,
                clip_count=0,
                created_at=time.time(),
                warnings=["No scenes detected in script"],
            )

        # Score each scene
        scores: List[PulseScore] = []
        for nbpm in narrative_scenes:
            score = self._conductor.score_scene(scene_id=nbpm.scene_id, narrative=nbpm)
            scores.append(score)

        # Match scenes to materials
        clips: List[MontageClip] = []
        timeline_cursor = 0.0
        sync_hits = 0
        page_duration = 60.0  # 1 page ≈ 60 seconds

        for i, score in enumerate(scores):
            # Find best matching material for this scene
            best_material = self._match_material_to_scene(score, materials)

            if not best_material:
                warnings.append(f"No material matched for scene {score.scene_id}")
                continue

            scene_duration = page_duration  # default 60s per scene

            # Snap to sync point
            if sync_points:
                snap = self._find_nearest_sync(timeline_cursor, sync_points)
                if snap is not None and abs(snap - timeline_cursor) < 2.0:
                    timeline_cursor = snap
                    sync_hits += 1

            # Determine in/out from material
            in_pt = 0.0
            out_pt = min(scene_duration, best_material.duration_sec)

            clip = MontageClip(
                clip_id=f"scr_{uuid.uuid4().hex[:8]}",
                source_path=best_material.source_path,
                in_sec=in_pt,
                out_sec=out_pt,
                timeline_start=timeline_cursor,
                timeline_end=timeline_cursor + out_pt,
                scene_id=score.scene_id,
                camelot_key=score.camelot_key,
                energy=score.pendulum_position * 0.5 + 0.5,  # normalize to 0-1
                pendulum=score.pendulum_position,
                confidence=score.confidence,
                reason=f"Script scene: {score.dramatic_function} ({score.scale})",
            )
            clips.append(clip)
            timeline_cursor += out_pt

        # Compute Camelot smoothness
        smoothness = self._compute_camelot_smoothness(clips)

        return MontageResult(
            timeline_id=tid,
            timeline_label=label,
            mode="script",
            clips=clips,
            total_duration=timeline_cursor,
            clip_count=len(clips),
            created_at=time.time(),
            scores_used=len(scores),
            sync_points_hit=sync_hits,
            camelot_smoothness=smoothness,
            warnings=warnings,
        )

    # ===================================================================
    # MODE C: Music-Driven (Architecture doc §7.2 row 3)
    # ===================================================================

    def assemble_from_music(
        self,
        music_audio: AudioBPM,
        materials: List[MaterialAsset],
        project_name: str = "project",
        version: int = 1,
    ) -> MontageResult:
        """
        Assemble timeline driven by music analysis.

        1. Analyze music track: BPM, key, energy curve, Camelot code
        2. Divide music into sections (phrases/downbeats)
        3. For each section, find best matching material via Camelot/mood
        4. Sync cuts to downbeats
        5. Creates new timeline — NEVER overwrites

        Architecture doc §7.2 row 3: "Music-driven"
        """
        tid, label = self._make_timeline_id(project_name, version)
        warnings: List[str] = []

        if not music_audio.downbeats:
            # Generate synthetic beat positions from BPM
            if music_audio.bpm > 0:
                beat_interval = 60.0 / music_audio.bpm
                total_dur = len(music_audio.energy_curve) * beat_interval if music_audio.energy_curve else 120.0
                music_audio.downbeats = [i * beat_interval for i in range(int(total_dur / beat_interval))]
            else:
                warnings.append("No downbeats and BPM=0, cannot create music-driven montage")
                return MontageResult(
                    timeline_id=tid,
                    timeline_label=label,
                    mode="music",
                    clips=[],
                    total_duration=0.0,
                    clip_count=0,
                    created_at=time.time(),
                    warnings=warnings,
                )

        # Divide music into sections (every 4-8 bars)
        beats_per_section = 16  # 4 bars of 4/4
        sections: List[Tuple[float, float]] = []
        beats = music_audio.downbeats
        for i in range(0, len(beats), beats_per_section):
            start = beats[i]
            end = beats[min(i + beats_per_section, len(beats) - 1)]
            if end > start:
                sections.append((start, end))

        if not sections:
            warnings.append("Could not divide music into sections")
            return MontageResult(
                timeline_id=tid,
                timeline_label=label,
                mode="music",
                clips=[],
                total_duration=0.0,
                clip_count=0,
                created_at=time.time(),
                warnings=warnings,
            )

        # Match each section to material via Camelot compatibility
        clips: List[MontageClip] = []
        used_materials: set = set()
        sync_hits = 0

        for sec_start, sec_end in sections:
            section_duration = sec_end - sec_start

            # Find best material by Camelot distance
            best = self._match_material_by_camelot(
                target_key=music_audio.camelot_key,
                materials=materials,
                exclude=used_materials,
            )

            if not best:
                # Reuse materials if exhausted
                used_materials.clear()
                best = self._match_material_by_camelot(
                    target_key=music_audio.camelot_key,
                    materials=materials,
                    exclude=set(),
                )

            if not best:
                warnings.append(f"No material for section {sec_start:.1f}-{sec_end:.1f}")
                continue

            used_materials.add(best.asset_id)

            # Cut to downbeat = sync hit
            sync_hits += 1

            in_pt = 0.0
            out_pt = min(section_duration, best.duration_sec)

            clip = MontageClip(
                clip_id=f"mus_{uuid.uuid4().hex[:8]}",
                source_path=best.source_path,
                in_sec=in_pt,
                out_sec=out_pt,
                timeline_start=sec_start,
                timeline_end=sec_start + out_pt,
                scene_id=best.scene_id or best.asset_id,
                camelot_key=best.camelot_key,
                energy=best.energy,
                pendulum=best.pendulum,
                confidence=0.7,
                reason=f"Music section: key={music_audio.camelot_key}, bpm={music_audio.bpm}",
            )
            clips.append(clip)

        total_duration = max((c.timeline_end for c in clips), default=0.0)
        smoothness = self._compute_camelot_smoothness(clips)

        return MontageResult(
            timeline_id=tid,
            timeline_label=label,
            mode="music",
            clips=clips,
            total_duration=total_duration,
            clip_count=len(clips),
            created_at=time.time(),
            scores_used=0,
            sync_points_hit=sync_hits,
            camelot_smoothness=smoothness,
            warnings=warnings,
        )

    # ===================================================================
    # Helper methods
    # ===================================================================

    def _find_nearest_sync(self, cursor: float, sync_points: List[float]) -> Optional[float]:
        """Find the nearest sync point to the current cursor position."""
        if not sync_points:
            return None
        nearest = min(sync_points, key=lambda sp: abs(sp - cursor))
        return nearest

    def _match_material_to_scene(
        self,
        score: PulseScore,
        materials: List[MaterialAsset],
    ) -> Optional[MaterialAsset]:
        """
        Match a PulseScore to the best available material.

        Scoring:
        - Camelot distance (harmonic compatibility): 40%
        - Energy similarity: 30%
        - Pendulum alignment: 30%
        """
        if not materials:
            return None

        best_score = -1.0
        best_material = None
        target_pendulum = score.pendulum_position

        for mat in materials:
            # Camelot distance (0 = same key, 7 = max distance)
            if mat.camelot_key and score.camelot_key:
                distance = self._camelot.distance(mat.camelot_key, score.camelot_key)
                camelot_score = max(0, 1.0 - distance / 7.0)
            else:
                camelot_score = 0.5  # neutral if no key info

            # Energy similarity
            energy_score = 1.0 - abs(mat.energy - (target_pendulum * 0.5 + 0.5))

            # Pendulum alignment
            pendulum_score = 1.0 - abs(mat.pendulum - target_pendulum) / 2.0

            total = camelot_score * 0.4 + energy_score * 0.3 + pendulum_score * 0.3

            if total > best_score:
                best_score = total
                best_material = mat

        return best_material

    def _match_material_by_camelot(
        self,
        target_key: str,
        materials: List[MaterialAsset],
        exclude: set,
    ) -> Optional[MaterialAsset]:
        """Match material by Camelot key compatibility."""
        if not materials:
            return None

        candidates = [m for m in materials if m.asset_id not in exclude]
        if not candidates:
            return None

        best_dist = 999
        best_mat = None

        for mat in candidates:
            if mat.camelot_key:
                dist = self._camelot.distance(mat.camelot_key, target_key)
            else:
                dist = 4  # neutral
            if dist < best_dist:
                best_dist = dist
                best_mat = mat

        return best_mat

    def _compute_camelot_smoothness(self, clips: List[MontageClip]) -> float:
        """
        Compute how smooth the Camelot transitions are across clips.
        0.0 = all wild jumps, 1.0 = all harmonic transitions.
        """
        if len(clips) < 2:
            return 1.0

        distances = []
        for i in range(len(clips) - 1):
            key_a = clips[i].camelot_key
            key_b = clips[i + 1].camelot_key
            if key_a and key_b:
                d = self._camelot.distance(key_a, key_b)
                distances.append(d)

        if not distances:
            return 0.5

        avg_distance = sum(distances) / len(distances)
        # Max distance on Camelot wheel is 6 (opposite)
        smoothness = max(0.0, 1.0 - avg_distance / 6.0)
        return smoothness


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

_instance: Optional[PulseAutoMontage] = None


def get_auto_montage() -> PulseAutoMontage:
    """Get or create the auto-montage engine singleton."""
    global _instance
    if _instance is None:
        _instance = PulseAutoMontage()
    return _instance


# MARKER_198.STUB: Assembly runner stubs — imported by cut_routes_pulse.py
# TODO: Implement actual assembly logic (Alpha/Beta domain)
async def run_favorites_assembly(project_id: str, **kwargs) -> MontageResult:
    """Stub: assemble montage from favorite-marked clips."""
    engine = get_auto_montage()
    return MontageResult(clips=[], duration_sec=0.0, strategy="favorites")


async def run_script_assembly(project_id: str, **kwargs) -> MontageResult:
    """Stub: assemble montage following script/subtitle timing."""
    engine = get_auto_montage()
    return MontageResult(clips=[], duration_sec=0.0, strategy="script")


async def run_music_assembly(project_id: str, **kwargs) -> MontageResult:
    """Stub: assemble montage synced to music beats."""
    engine = get_auto_montage()
    return MontageResult(clips=[], duration_sec=0.0, strategy="music")
