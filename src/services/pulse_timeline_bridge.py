"""
PULSE ↔ Timeline Bridge — connects PULSE conductor scores to scene graph & timeline.

Enriches scene graph nodes with PULSE metadata (Camelot key, pendulum, energy,
dramatic function). Computes per-scene PULSE scores from timeline state.

Flow:
  Timeline clips → Scene Graph nodes → PULSE analysis → enriched scene graph
  User uploads script → PULSE → NarrativeBPM per scene → attached to scene nodes

MARKER_179.10_PULSE_TIMELINE_BRIDGE
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.services.pulse_conductor import (
    NarrativeBPM,
    VisualBPM,
    AudioBPM,
    PulseScore,
    FilmPartiture,
    PulseConductor,
    get_pulse_conductor,
)
from src.services.pulse_script_analyzer import get_script_analyzer
from src.services.pulse_energy_critics import compute_all_energies
from src.services.pulse_camelot_engine import get_camelot_engine


# ---------------------------------------------------------------------------
# Scene PULSE enrichment
# ---------------------------------------------------------------------------

@dataclass
class ScenePulseData:
    """PULSE data attached to a scene graph node."""
    scene_id: str
    camelot_key: str = ""
    scale: str = ""
    pendulum_position: float = 0.0
    dramatic_function: str = ""
    energy_profile: str = ""
    counterpoint_pair: str = ""
    alignment: str = "sync"
    confidence: float = 0.0
    itten_colors: List[str] = field(default_factory=list)
    music_genres: List[str] = field(default_factory=list)
    # Source signals summary
    has_narrative: bool = False
    has_visual: bool = False
    has_audio: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camelot_key": self.camelot_key,
            "scale": self.scale,
            "pendulum_position": self.pendulum_position,
            "dramatic_function": self.dramatic_function,
            "energy_profile": self.energy_profile,
            "counterpoint_pair": self.counterpoint_pair,
            "alignment": self.alignment,
            "confidence": round(self.confidence, 3),
            "itten_colors": self.itten_colors,
            "music_genres": self.music_genres,
            "has_narrative": self.has_narrative,
            "has_visual": self.has_visual,
            "has_audio": self.has_audio,
        }


class PulseTimelineBridge:
    """
    Bridge between PULSE conductor and CUT timeline/scene graph.

    Usage:
        bridge = PulseTimelineBridge()

        # Enrich scene graph from script
        enriched = bridge.enrich_from_script(scene_graph, script_text)

        # Enrich scene graph from timeline visual signals
        enriched = bridge.enrich_from_timeline(scene_graph, timeline_state)

        # Get full film partiture
        partiture = bridge.compute_partiture(scene_graph)
    """

    def __init__(self):
        self._conductor = get_pulse_conductor()
        self._analyzer = get_script_analyzer()
        self._engine = get_camelot_engine()

    def enrich_from_script(
        self,
        scene_graph: Dict[str, Any],
        script_text: str,
    ) -> Dict[str, Any]:
        """
        Analyze script and attach NarrativeBPM to matching scene graph nodes.

        Matches scenes by index (sc_0 → first scene node, etc.).
        Returns enriched scene_graph with pulse_data in node metadata.
        """
        narrative_scenes = self._analyzer.analyze(script_text)

        # Get scene nodes from graph
        scene_nodes = [
            n for n in scene_graph.get("nodes", [])
            if n.get("node_type") == "scene"
        ]

        # Score each scene with narrative signal
        for i, node in enumerate(scene_nodes):
            if i < len(narrative_scenes):
                nbpm = narrative_scenes[i]
                score = self._conductor.score_scene(
                    scene_id=node.get("node_id", f"sc_{i}"),
                    narrative=nbpm,
                )
                pulse_data = self._score_to_pulse_data(score, has_narrative=True)
            else:
                # No matching script scene — neutral
                pulse_data = ScenePulseData(
                    scene_id=node.get("node_id", f"sc_{i}"),
                    dramatic_function="Neutral",
                    confidence=0.1,
                )

            # Attach to node metadata
            meta = node.get("metadata", {})
            meta["pulse_data"] = pulse_data.to_dict()
            node["metadata"] = meta

        return scene_graph

    def enrich_from_timeline(
        self,
        scene_graph: Dict[str, Any],
        timeline_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract visual signals from timeline clips and enrich scene nodes.

        Estimates motion_intensity from clip duration and cut density.
        """
        scene_nodes = [
            n for n in scene_graph.get("nodes", [])
            if n.get("node_type") == "scene"
        ]

        # Build visual signals from timeline lanes
        lanes = timeline_state.get("lanes", [])
        scene_clips = self._extract_scene_clips(lanes)

        for node in scene_nodes:
            node_id = node.get("node_id", "")
            meta = node.get("metadata", {})

            # Find clips belonging to this scene
            clips = scene_clips.get(node_id, [])
            if not clips:
                # Try matching by scene_id in metadata
                scene_id_from_meta = meta.get("scene_id", "")
                clips = scene_clips.get(scene_id_from_meta, [])

            if clips:
                visual = self._clips_to_visual_bpm(node_id, clips)

                # Check if we already have narrative from script enrichment
                existing_pulse = meta.get("pulse_data", {})
                narrative = None
                if existing_pulse.get("has_narrative"):
                    # Reconstruct narrative from existing data
                    narrative = NarrativeBPM(
                        scene_id=node_id,
                        dramatic_function=existing_pulse.get("dramatic_function", ""),
                        pendulum_position=existing_pulse.get("pendulum_position", 0.0),
                        estimated_energy=0.5,
                        suggested_scale=existing_pulse.get("scale", ""),
                        confidence=existing_pulse.get("confidence", 0.5),
                    )

                score = self._conductor.score_scene(
                    scene_id=node_id,
                    narrative=narrative,
                    visual=visual,
                )
                pulse_data = self._score_to_pulse_data(
                    score,
                    has_narrative=narrative is not None,
                    has_visual=True,
                )
                meta["pulse_data"] = pulse_data.to_dict()
                node["metadata"] = meta

        return scene_graph

    def compute_partiture(
        self,
        scene_graph: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compute full film partiture from enriched scene graph.

        Returns partiture dict + energy critics assessment.
        """
        scene_nodes = [
            n for n in scene_graph.get("nodes", [])
            if n.get("node_type") == "scene"
        ]

        # Build PulseScore list from enriched nodes
        scores = []
        for node in scene_nodes:
            meta = node.get("metadata", {})
            pd = meta.get("pulse_data", {})
            if pd:
                score = PulseScore(
                    scene_id=node.get("node_id", ""),
                    camelot_key=pd.get("camelot_key", "8B"),
                    scale=pd.get("scale", "Ionian"),
                    pendulum_position=pd.get("pendulum_position", 0.0),
                    dramatic_function=pd.get("dramatic_function", ""),
                    energy_profile=pd.get("energy_profile", ""),
                    counterpoint_pair=pd.get("counterpoint_pair", ""),
                    confidence=pd.get("confidence", 0.0),
                    alignment=pd.get("alignment", "sync"),
                    itten_colors=pd.get("itten_colors", []),
                    music_genres=pd.get("music_genres", []),
                )
                scores.append(score)

        # Build partiture
        if len(scores) >= 2:
            camelot_keys = [s.camelot_key for s in scores]
            path = self._engine.plan_path(camelot_keys)
        else:
            path = None

        # Energy critics
        energies = compute_all_energies(scores) if scores else {}

        # Tonic key
        key_freq: Dict[str, int] = {}
        for s in scores:
            key_freq[s.camelot_key] = key_freq.get(s.camelot_key, 0) + 1
        tonic = max(key_freq, key=lambda k: key_freq[k]) if key_freq else "8B"

        pendulums = [s.pendulum_position for s in scores]

        return {
            "schema_version": "pulse_partiture_v1",
            "scene_count": len(scores),
            "tonic_key": tonic,
            "tonic_musical": self._engine.musical_from_key(tonic) or tonic,
            "pendulum_range": [min(pendulums), max(pendulums)] if pendulums else [-1, 1],
            "camelot_path": {
                "smoothness": round(path.smoothness, 3) if path else None,
                "max_jump": path.max_jump if path else None,
                "total_distance": path.total_distance if path else None,
            },
            "energy_critics": energies,
            "scores": [s.to_dict() for s in scores],
        }

    def get_scene_pulse_summary(
        self,
        scene_graph: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Get a compact summary of PULSE data for all scenes.
        Useful for frontend overlay rendering.
        """
        result = []
        for node in scene_graph.get("nodes", []):
            if node.get("node_type") != "scene":
                continue
            meta = node.get("metadata", {})
            pd = meta.get("pulse_data")
            if pd:
                result.append({
                    "scene_id": node.get("node_id"),
                    "label": node.get("label", ""),
                    "start_sec": meta.get("start_sec", 0),
                    "duration_sec": meta.get("duration_sec", 0),
                    **pd,
                })
        return result

    # --- Private ---

    def _score_to_pulse_data(
        self,
        score: PulseScore,
        has_narrative: bool = False,
        has_visual: bool = False,
        has_audio: bool = False,
    ) -> ScenePulseData:
        """Convert PulseScore to ScenePulseData for storage."""
        return ScenePulseData(
            scene_id=score.scene_id,
            camelot_key=score.camelot_key,
            scale=score.scale,
            pendulum_position=score.pendulum_position,
            dramatic_function=score.dramatic_function,
            energy_profile=score.energy_profile,
            counterpoint_pair=score.counterpoint_pair,
            alignment=score.alignment,
            confidence=score.confidence,
            itten_colors=score.itten_colors,
            music_genres=score.music_genres,
            has_narrative=has_narrative,
            has_visual=has_visual,
            has_audio=has_audio,
        )

    def _extract_scene_clips(
        self,
        lanes: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group timeline clips by scene_id.

        Returns: {scene_id: [clip_dict, ...]}
        """
        scene_clips: Dict[str, List[Dict[str, Any]]] = {}
        for lane in lanes:
            for clip in lane.get("clips", []):
                sid = clip.get("scene_id", "")
                if sid:
                    scene_clips.setdefault(sid, []).append(clip)
        return scene_clips

    def _clips_to_visual_bpm(
        self,
        scene_id: str,
        clips: List[Dict[str, Any]],
    ) -> VisualBPM:
        """
        Estimate VisualBPM from timeline clips.

        - cuts_per_minute: number of clips / total duration * 60
        - motion_intensity: estimated from clip count (more clips = more dynamic)
        """
        if not clips:
            return VisualBPM(
                scene_id=scene_id,
                cuts_per_minute=0.0,
                motion_intensity=0.5,
                confidence=0.3,
                source="timeline",
            )

        total_duration = sum(float(c.get("duration_sec", 0)) for c in clips)
        num_clips = len(clips)

        if total_duration > 0:
            cuts_per_minute = (num_clips / total_duration) * 60.0
        else:
            cuts_per_minute = 0.0

        # Estimate motion: more cuts per minute → higher motion
        # 0 cpm → 0.2, 5 cpm → 0.5, 15+ cpm → 0.9
        motion_intensity = min(0.2 + cuts_per_minute * 0.045, 0.95)

        return VisualBPM(
            scene_id=scene_id,
            cuts_per_minute=round(cuts_per_minute, 2),
            motion_intensity=round(motion_intensity, 3),
            confidence=0.5,  # timeline-derived = moderate confidence
            source="timeline",
        )


# Singleton
_bridge_instance: Optional[PulseTimelineBridge] = None


def get_pulse_timeline_bridge() -> PulseTimelineBridge:
    """Get or create singleton bridge."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = PulseTimelineBridge()
    return _bridge_instance
