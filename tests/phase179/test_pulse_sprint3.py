"""
PULSE Sprint 3 Tests — Timeline Bridge, Scene Graph enrichment, Partiture.

MARKER_179.S3_SPRINT3_TESTS
"""
import pytest
from typing import Any, Dict, List

from src.services.pulse_timeline_bridge import (
    PulseTimelineBridge,
    ScenePulseData,
    get_pulse_timeline_bridge,
)
from src.services.pulse_conductor import PulseScore


# =====================================================================
# Helpers: build mock scene graph and timeline
# =====================================================================

def _make_scene_graph(num_scenes: int = 3) -> Dict[str, Any]:
    """Create a minimal scene graph with N scene nodes."""
    nodes = []
    edges = []
    for i in range(num_scenes):
        nodes.append({
            "node_id": f"scene_{i}",
            "node_type": "scene",
            "label": f"Scene {i}",
            "metadata": {
                "start_sec": i * 30.0,
                "duration_sec": 30.0,
                "scene_id": f"scene_{i}",
            },
        })
        if i > 0:
            edges.append({
                "edge_id": f"e_{i-1}_{i}",
                "edge_type": "follows",
                "source": f"scene_{i-1}",
                "target": f"scene_{i}",
                "weight": 1.0,
            })
    return {
        "schema_version": "cut_scene_graph_v1",
        "nodes": nodes,
        "edges": edges,
    }


def _make_timeline_state(num_scenes: int = 3) -> Dict[str, Any]:
    """Create minimal timeline state with clips per scene."""
    clips = []
    for i in range(num_scenes):
        # Each scene has 2-4 clips (variable cut density)
        num_clips = 2 + i  # scene 0 = 2 clips, scene 1 = 3, scene 2 = 4
        for j in range(num_clips):
            clips.append({
                "clip_id": f"clip_{i}_{j}",
                "source_path": f"/media/shot_{i}_{j}.mp4",
                "start_sec": i * 30.0 + j * (30.0 / num_clips),
                "duration_sec": 30.0 / num_clips,
                "scene_id": f"scene_{i}",
            })
    return {
        "schema_version": "cut_timeline_state_v1",
        "lanes": [
            {
                "lane_id": "video_main",
                "lane_type": "video_main",
                "clips": clips,
            }
        ],
        "revision": 1,
    }


# =====================================================================
# 179.10 — PulseTimelineBridge tests
# =====================================================================

class TestPulseTimelineBridge:
    """Test the PULSE ↔ Timeline bridge."""

    def test_singleton(self):
        b1 = get_pulse_timeline_bridge()
        b2 = get_pulse_timeline_bridge()
        assert b1 is b2

    def test_enrich_from_script_basic(self):
        """Script analysis attaches pulse_data to scene nodes."""
        bridge = PulseTimelineBridge()
        graph = _make_scene_graph(3)
        script = (
            "INT. DARK ALLEY - NIGHT\n"
            "The detective investigates a mystery.\n\n"
            "EXT. ARENA - DAY\n"
            "Epic battle. The hero fights.\n\n"
            "INT. CHAPEL - NIGHT\n"
            "Grief and loss. Farewell tears.\n"
        )
        enriched = bridge.enrich_from_script(graph, script)
        scene_nodes = [n for n in enriched["nodes"] if n["node_type"] == "scene"]

        for node in scene_nodes:
            pd = node["metadata"].get("pulse_data")
            assert pd is not None, f"No pulse_data on {node['node_id']}"
            assert pd["has_narrative"] is True
            assert pd["camelot_key"] != ""
            assert pd["dramatic_function"] != ""
            assert -1.0 <= pd["pendulum_position"] <= 1.0

    def test_enrich_from_script_pendulum_variety(self):
        """Different scenes should get different pendulum values."""
        bridge = PulseTimelineBridge()
        graph = _make_scene_graph(3)
        script = (
            "SCENE 1\nThe victory celebration. Hero wins.\n\n"
            "SCENE 2\nDeath and grief. Funeral tears.\n\n"
            "SCENE 3\nEpic battle with the monster.\n"
        )
        enriched = bridge.enrich_from_script(graph, script)
        scene_nodes = [n for n in enriched["nodes"] if n["node_type"] == "scene"]
        pendulums = [n["metadata"]["pulse_data"]["pendulum_position"] for n in scene_nodes]

        # Victory (+), Loss (-), Epic (+) — should have both positive and negative
        assert any(p > 0 for p in pendulums), f"No positive pendulums: {pendulums}"
        assert any(p < 0 for p in pendulums), f"No negative pendulums: {pendulums}"

    def test_enrich_from_timeline_visual_signals(self):
        """Timeline clips generate visual BPM signals."""
        bridge = PulseTimelineBridge()
        graph = _make_scene_graph(3)
        timeline = _make_timeline_state(3)

        enriched = bridge.enrich_from_timeline(graph, timeline)
        scene_nodes = [n for n in enriched["nodes"] if n["node_type"] == "scene"]

        # At least some scenes should be enriched with visual data
        enriched_count = sum(
            1 for n in scene_nodes
            if n["metadata"].get("pulse_data", {}).get("has_visual")
        )
        assert enriched_count > 0

    def test_enrich_combined_script_then_timeline(self):
        """Script + timeline enrichment combines signals."""
        bridge = PulseTimelineBridge()
        graph = _make_scene_graph(2)
        script = "SCENE 1\nMystery night investigation.\n\nSCENE 2\nVictory celebration.\n"
        timeline = _make_timeline_state(2)

        # First pass: script
        graph = bridge.enrich_from_script(graph, script)
        # Second pass: timeline
        graph = bridge.enrich_from_timeline(graph, timeline)

        scene_nodes = [n for n in graph["nodes"] if n["node_type"] == "scene"]
        for node in scene_nodes:
            pd = node["metadata"].get("pulse_data", {})
            assert pd.get("has_narrative") is True
            assert pd.get("has_visual") is True

    def test_compute_partiture(self):
        """Full partiture from enriched scene graph."""
        bridge = PulseTimelineBridge()
        graph = _make_scene_graph(4)
        script = (
            "SCENE 1\nVictory triumph celebration.\n\n"
            "SCENE 2\nNight mystery detective shadows.\n\n"
            "SCENE 3\nEpic battle warrior legend.\n\n"
            "SCENE 4\nGrief loss farewell tears.\n"
        )
        graph = bridge.enrich_from_script(graph, script)
        partiture = bridge.compute_partiture(graph)

        assert partiture["scene_count"] == 4
        assert "tonic_key" in partiture
        assert "tonic_musical" in partiture
        assert "energy_critics" in partiture
        assert "camelot_path" in partiture
        assert partiture["camelot_path"]["smoothness"] is not None
        assert len(partiture["scores"]) == 4

    def test_compute_partiture_energy_critics(self):
        """Partiture includes energy critics assessment."""
        bridge = PulseTimelineBridge()
        graph = _make_scene_graph(3)
        script = "SCENE 1\nVictory.\n\nSCENE 2\nLoss grief.\n\nSCENE 3\nEpic battle.\n"
        graph = bridge.enrich_from_script(graph, script)
        partiture = bridge.compute_partiture(graph)

        ec = partiture["energy_critics"]
        assert "total" in ec
        assert "pendulum_balance" in ec
        assert "camelot_proximity" in ec
        assert 0.0 <= ec["total"] <= 1.0

    def test_scene_pulse_summary(self):
        """Compact summary for frontend overlay."""
        bridge = PulseTimelineBridge()
        graph = _make_scene_graph(2)
        script = "SCENE 1\nChase action adventure.\n\nSCENE 2\nMystery night.\n"
        graph = bridge.enrich_from_script(graph, script)

        summary = bridge.get_scene_pulse_summary(graph)
        assert len(summary) == 2
        for s in summary:
            assert "scene_id" in s
            assert "camelot_key" in s
            assert "pendulum_position" in s
            assert "dramatic_function" in s

    def test_empty_scene_graph(self):
        """Handle scene graph with no scene nodes gracefully."""
        bridge = PulseTimelineBridge()
        graph = {"nodes": [], "edges": []}
        result = bridge.enrich_from_script(graph, "Some script text")
        assert result["nodes"] == []

        partiture = bridge.compute_partiture(graph)
        assert partiture["scene_count"] == 0

    def test_more_script_scenes_than_graph_nodes(self):
        """Script has more scenes than graph nodes — extras ignored."""
        bridge = PulseTimelineBridge()
        graph = _make_scene_graph(2)
        script = (
            "SCENE 1\nVictory.\n\n"
            "SCENE 2\nLoss.\n\n"
            "SCENE 3\nEpic.\n\n"
            "SCENE 4\nMystery.\n"
        )
        enriched = bridge.enrich_from_script(graph, script)
        scene_nodes = [n for n in enriched["nodes"] if n["node_type"] == "scene"]
        # Only 2 nodes in graph, so only 2 enriched
        assert len(scene_nodes) == 2
        for n in scene_nodes:
            assert "pulse_data" in n["metadata"]


# =====================================================================
# ScenePulseData tests
# =====================================================================

class TestScenePulseData:
    """Test the ScenePulseData dataclass."""

    def test_to_dict_roundtrip(self):
        pd = ScenePulseData(
            scene_id="sc_0",
            camelot_key="8A",
            scale="Aeolian",
            pendulum_position=-0.7,
            dramatic_function="Loss",
            energy_profile="low_sustained",
            counterpoint_pair="Ionian",
            alignment="sync",
            confidence=0.85,
            itten_colors=["blue", "violet"],
            music_genres=["Drama", "Art-house"],
            has_narrative=True,
            has_visual=False,
            has_audio=False,
        )
        d = pd.to_dict()
        assert d["camelot_key"] == "8A"
        assert d["pendulum_position"] == -0.7
        assert d["has_narrative"] is True
        assert d["has_visual"] is False
        assert d["confidence"] == 0.85

    def test_defaults(self):
        pd = ScenePulseData(scene_id="test")
        d = pd.to_dict()
        assert d["camelot_key"] == ""
        assert d["pendulum_position"] == 0.0
        assert d["confidence"] == 0.0
        assert d["itten_colors"] == []


# =====================================================================
# Visual BPM estimation tests
# =====================================================================

class TestVisualBpmEstimation:
    """Test visual signal estimation from timeline clips."""

    def test_high_cut_density(self):
        """Many short clips → high cuts_per_minute → high motion."""
        bridge = PulseTimelineBridge()
        clips = [
            {"clip_id": f"c{i}", "duration_sec": 2.0, "scene_id": "s0"}
            for i in range(10)
        ]
        visual = bridge._clips_to_visual_bpm("s0", clips)
        assert visual.cuts_per_minute > 10
        assert visual.motion_intensity > 0.5

    def test_low_cut_density(self):
        """One long clip → low cuts_per_minute → lower motion."""
        bridge = PulseTimelineBridge()
        clips = [{"clip_id": "c0", "duration_sec": 60.0, "scene_id": "s0"}]
        visual = bridge._clips_to_visual_bpm("s0", clips)
        assert visual.cuts_per_minute < 5
        assert visual.motion_intensity < 0.5

    def test_empty_clips(self):
        """No clips → default neutral values."""
        bridge = PulseTimelineBridge()
        visual = bridge._clips_to_visual_bpm("s0", [])
        assert visual.cuts_per_minute == 0.0
        assert visual.motion_intensity == 0.5
        assert visual.confidence == 0.3
