"""
MARKER_B70 — PULSE AI sub-router.
Extracted from cut_routes.py for modularity.

Routes: cinema matrix, scene scoring, film scoring, Camelot analysis,
energy critics, story space, auto-montage, BPM markers, SRT analysis.

26 endpoints, ~1300 lines.

@status: active
@phase: B70
@task: tb_1774311967_29
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.cut_project_store import CutProjectStore
from src.services.pulse_cinema_matrix import get_cinema_matrix
from src.services.pulse_camelot_engine import CamelotKey
from src.services.pulse_conductor import PulseConductor
from src.services.pulse_energy_critics import (
    compute_all_energies,
    compute_calibrated_energies,
    list_genre_profiles,
)
from src.services.pulse_timeline_bridge import get_pulse_timeline_bridge
from src.services.pulse_script_analyzer import get_script_analyzer
from src.services.pulse_story_space import (
    TrianglePosition,
    StorySpacePoint,
    compute_triangle_energies,
    chaos_index,
    scores_to_story_space,
    genre_to_triangle,
    interpolate_critic_weights,
    markers_to_story_space_points,
)
from src.services.pulse_srt_bridge import (
    srt_to_narrative_bpm,
    srt_to_narrative_bpm_with_timing,
    parse_subtitles,
)
from src.services.pulse_auto_montage import (
    run_favorites_assembly,
    run_script_assembly,
    run_music_assembly,
)

logger = logging.getLogger("cut.pulse")

pulse_router = APIRouter(tags=["CUT-PULSE"])


class CutPulseScoreSceneRequest(BaseModel):
    """Request to score a single scene via PULSE conductor."""
    scene_id: str = "sc_0"
    # Narrative signal (optional)
    script_text: str | None = None
    dramatic_function: str | None = None
    pendulum_position: float | None = None
    suggested_scale: str | None = None
    # Visual signal (optional)
    cuts_per_minute: float | None = None
    motion_intensity: float | None = None
    # Audio signal (optional)
    audio_bpm: float | None = None
    audio_key: str | None = None
    audio_camelot_key: str | None = None


class CutPulseScoreFilmRequest(BaseModel):
    """Request to score an entire film from script text."""
    script_text: str
    # Optional audio context for the whole film
    audio_bpm: float | None = None
    audio_key: str | None = None
    audio_camelot_key: str | None = None


class CutPulseCamelotPathRequest(BaseModel):
    """Request to analyze a Camelot key path."""
    keys: list[str]  # e.g. ["8A", "9A", "3B", "8A"]


class CutPulseCamelotSuggestRequest(BaseModel):
    """Request to suggest next Camelot key."""
    current_key: str
    target_pendulum: float = 0.0
    prefer_dramatic: bool = False


@pulse_router.get("/pulse/matrix")
async def cut_pulse_matrix() -> dict[str, Any]:
    """
    MARKER_179.5 — Get the full cinema matrix (Scale → Genre → Cinema Scene).
    """
    matrix = get_cinema_matrix()
    return {
        "success": True,
        "schema_version": "pulse_cinema_matrix_v1",
        "scales": matrix.to_dict_list(),
        "total": len(matrix.all_scales()),
    }


@pulse_router.get("/pulse/matrix/{scale_name}")
async def cut_pulse_matrix_by_scale(scale_name: str) -> dict[str, Any]:
    """
    MARKER_179.5 — Get a single row from the cinema matrix by scale name.
    """
    matrix = get_cinema_matrix()
    row = matrix.get_by_scale(scale_name)
    if not row:
        raise HTTPException(404, f"Scale '{scale_name}' not found in cinema matrix")
    return {
        "success": True,
        "scale": row.scale,
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
    }


@pulse_router.post("/pulse/score-scene")
async def cut_pulse_score_scene(req: CutPulseScoreSceneRequest) -> dict[str, Any]:
    """
    MARKER_179.5 — Score a single scene via PULSE conductor.

    Accepts narrative, visual, and/or audio signals.
    If script_text provided, runs script analyzer first.
    """
    conductor = get_pulse_conductor()

    # Build narrative signal
    narrative = None
    if req.script_text:
        analyzer = get_script_analyzer()
        narrative = analyzer.analyze_single(req.script_text, req.scene_id)
    elif req.dramatic_function or req.pendulum_position is not None:
        narrative = NarrativeBPM(
            scene_id=req.scene_id,
            dramatic_function=req.dramatic_function or "Unknown",
            pendulum_position=req.pendulum_position or 0.0,
            estimated_energy=0.5,
            suggested_scale=req.suggested_scale or "",
            confidence=0.7,
        )

    # Build visual signal
    visual = None
    if req.cuts_per_minute is not None or req.motion_intensity is not None:
        visual = VisualBPM(
            scene_id=req.scene_id,
            cuts_per_minute=req.cuts_per_minute or 0.0,
            motion_intensity=req.motion_intensity or 0.5,
            confidence=0.6,
        )

    # Build audio signal
    audio = None
    if req.audio_bpm is not None or req.audio_camelot_key:
        engine = get_camelot_engine()
        camelot = req.audio_camelot_key or ""
        if not camelot and req.audio_key:
            camelot = engine.key_from_musical(req.audio_key) or ""
        audio = AudioBPM(
            bpm=req.audio_bpm or 120.0,
            key=req.audio_key or "",
            camelot_key=camelot,
            confidence=0.8,
        )

    score = conductor.score_scene(req.scene_id, narrative, visual, audio)

    return {
        "success": True,
        "schema_version": "pulse_score_v1",
        "score": score.to_dict(),
    }


@pulse_router.post("/pulse/score-film")
async def cut_pulse_score_film(req: CutPulseScoreFilmRequest) -> dict[str, Any]:
    """
    MARKER_179.5 — Score an entire film from script text.

    Parses script into scenes, runs PULSE conductor on each,
    returns the full partiture with Camelot path analysis.
    """
    analyzer = get_script_analyzer()
    conductor = get_pulse_conductor()

    narrative_bpms = analyzer.analyze(req.script_text)

    # Build audio context if provided
    audio = None
    if req.audio_bpm is not None or req.audio_camelot_key:
        engine = get_camelot_engine()
        camelot = req.audio_camelot_key or ""
        if not camelot and req.audio_key:
            camelot = engine.key_from_musical(req.audio_key) or ""
        audio = AudioBPM(
            bpm=req.audio_bpm or 120.0,
            key=req.audio_key or "",
            camelot_key=camelot,
            confidence=0.8,
        )

    scenes = []
    for nbpm in narrative_bpms:
        scenes.append({
            "scene_id": nbpm.scene_id,
            "narrative": nbpm,
            "audio": audio,  # same audio context for whole film
        })

    partiture = conductor.score_film(scenes)

    return {
        "success": True,
        "schema_version": "pulse_partiture_v1",
        "partiture": partiture.to_dict(),
    }


@pulse_router.post("/pulse/analyze-script")
async def cut_pulse_analyze_script(
    script_text: str = "",
) -> dict[str, Any]:
    """
    MARKER_179.5 — Analyze script text and extract NarrativeBPM for each scene.

    Returns scene breakdown with dramatic functions, pendulum positions,
    and suggested scales.
    """
    if not script_text:
        raise HTTPException(400, "script_text is required")

    analyzer = get_script_analyzer()
    results = analyzer.analyze(script_text)

    return {
        "success": True,
        "schema_version": "pulse_narrative_v1",
        "scenes": [
            {
                "scene_id": r.scene_id,
                "dramatic_function": r.dramatic_function,
                "pendulum_position": r.pendulum_position,
                "estimated_energy": r.estimated_energy,
                "keywords": r.keywords,
                "suggested_scale": r.suggested_scale,
                "confidence": r.confidence,
            }
            for r in results
        ],
        "total_scenes": len(results),
    }


@pulse_router.post("/pulse/camelot/path")
async def cut_pulse_camelot_path(req: CutPulseCamelotPathRequest) -> dict[str, Any]:
    """
    MARKER_179.5 — Analyze a Camelot key path for harmonic smoothness.
    """
    engine = get_camelot_engine()
    try:
        path = engine.plan_path(req.keys)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "success": True,
        "schema_version": "pulse_camelot_path_v1",
        "keys": path.keys,
        "total_distance": path.total_distance,
        "max_jump": path.max_jump,
        "smoothness": round(path.smoothness, 3),
        "transitions": [
            {
                "from": t.from_key,
                "to": t.to_key,
                "distance": t.distance,
                "quality": t.quality,
            }
            for t in path.transitions
        ],
    }


@pulse_router.get("/pulse/camelot/distance")
async def cut_pulse_camelot_distance(key_a: str, key_b: str) -> dict[str, Any]:
    """
    MARKER_179.5 — Get harmonic distance between two Camelot keys.
    """
    engine = get_camelot_engine()
    try:
        d = engine.distance(key_a, key_b)
        c = engine.compatibility(key_a, key_b)
        q = engine.transition_quality(key_a, key_b)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "success": True,
        "key_a": key_a,
        "key_b": key_b,
        "distance": d,
        "compatibility": c,
        "quality": q,
    }


@pulse_router.get("/pulse/camelot/neighbors")
async def cut_pulse_camelot_neighbors(key: str) -> dict[str, Any]:
    """
    MARKER_179.5 — Get harmonically compatible neighbors for a key.
    """
    engine = get_camelot_engine()
    try:
        nbrs = engine.neighbors(key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "success": True,
        "key": key,
        "neighbors": nbrs,
        "musical_key": engine.musical_from_key(key),
    }


@pulse_router.post("/pulse/camelot/suggest-next")
async def cut_pulse_camelot_suggest_next(
    req: CutPulseCamelotSuggestRequest,
) -> dict[str, Any]:
    """
    MARKER_179.5 — Suggest next Camelot key based on target pendulum.
    """
    engine = get_camelot_engine()
    try:
        suggestions = engine.suggest_next(
            req.current_key,
            req.target_pendulum,
            prefer_dramatic=req.prefer_dramatic,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "success": True,
        "current_key": req.current_key,
        "target_pendulum": req.target_pendulum,
        "suggestions": [
            {"key": k, "score": s, "musical_key": engine.musical_from_key(k)}
            for k, s in suggestions
        ],
    }


# ---------------------------------------------------------------------------
# MARKER_179.6_ENERGY_CRITICS_ENDPOINT
# ---------------------------------------------------------------------------


class CutPulseEnergyCriticsRequest(BaseModel):
    """Request to compute energy critics for a film from script text."""
    script_text: str
    # Optional per-scene audio overrides
    audio_bpm: float | None = None
    audio_key: str | None = None
    audio_camelot_key: str | None = None


@pulse_router.post("/pulse/energy-critics")
async def cut_pulse_energy_critics(req: CutPulseEnergyCriticsRequest) -> dict[str, Any]:
    """
    MARKER_179.6 — Compute all 5 energy critics for a film.

    Takes script text, scores each scene via PULSE conductor,
    then runs all energy critics on the resulting PulseScore sequence.

    Returns individual critic energies + weighted total.
    Lower total = better overall montage compatibility.
    """
    if not req.script_text:
        raise HTTPException(400, "script_text is required")

    conductor = get_pulse_conductor()
    analyzer = get_script_analyzer()

    # Analyze script into scenes
    narrative_scenes = analyzer.analyze(req.script_text)

    # Score each scene
    scores = []
    for nbpm in narrative_scenes:
        # Build optional audio signal
        audio = None
        if req.audio_bpm is not None or req.audio_camelot_key:
            engine = get_camelot_engine()
            camelot = req.audio_camelot_key or ""
            if not camelot and req.audio_key:
                camelot = engine.key_from_musical(req.audio_key) or ""
            audio = AudioBPM(
                bpm=req.audio_bpm or 120.0,
                key=req.audio_key or "",
                camelot_key=camelot,
                confidence=0.6,
            )

        score = conductor.score_scene(
            scene_id=nbpm.scene_id,
            narrative=nbpm,
            audio=audio,
        )
        scores.append(score)

    # Compute energy critics
    energies = compute_all_energies(scores)

    return {
        "success": True,
        "schema_version": "pulse_energy_critics_v1",
        "energies": energies,
        "scene_count": len(scores),
        "interpretation": {
            "total_label": _energy_label(energies["total"]),
            "advice": _energy_advice(energies),
        },
    }


def _energy_label(total: float) -> str:
    """Human-readable label for total energy."""
    if total < 0.2:
        return "excellent_harmony"
    elif total < 0.35:
        return "good_balance"
    elif total < 0.5:
        return "moderate_tension"
    elif total < 0.7:
        return "high_tension"
    else:
        return "extreme_conflict"


def _energy_advice(energies: Dict[str, float]) -> list[str]:
    """Generate actionable advice based on individual critic values."""
    advice = []
    if energies.get("pendulum_balance", 0) > 0.6:
        advice.append("Pendulum is monotonous — consider adding scenes with opposite emotional charge")
    if energies.get("camelot_proximity", 0) > 0.5:
        advice.append("Key transitions are jarring — try inserting bridge scenes with adjacent Camelot keys")
    if energies.get("music_scene_sync", 0) > 0.5:
        advice.append("Music-scene alignment shows frequent counterpoint — verify it's intentional")
    if energies.get("script_visual_match", 0) > 0.5:
        advice.append("Visual pacing doesn't match script energy — check cut density and motion intensity")
    if energies.get("energy_contour", 0) > 0.5:
        advice.append("Energy contour is spiky — smooth transitions between high/low energy scenes")
    if not advice:
        advice.append("Montage rhythm looks healthy — energy distribution is balanced")
    return advice


# ---------------------------------------------------------------------------
# MARKER_179.10_PULSE_TIMELINE_BRIDGE
# ---------------------------------------------------------------------------


class CutPulseEnrichScriptRequest(BaseModel):
    """Enrich scene graph from script text."""
    timeline_id: str
    script_text: str


@pulse_router.post("/pulse/enrich-from-script/{timeline_id}")
async def cut_pulse_enrich_from_script(
    timeline_id: str,
    script_text: str = "",
) -> dict[str, Any]:
    """
    MARKER_179.10 — Analyze script and attach PULSE data to scene graph nodes.

    Matches script scenes to scene graph nodes by index.
    Returns enriched scene count and partiture summary.
    """
    if not script_text:
        raise HTTPException(400, "script_text is required")

    store = CutProjectStore.current()
    if not store:
        raise HTTPException(400, "No CUT project loaded")

    scene_graph = store.get_scene_graph(timeline_id)
    if not scene_graph:
        raise HTTPException(404, f"No scene graph for timeline {timeline_id}")

    bridge = get_pulse_timeline_bridge()
    enriched = bridge.enrich_from_script(scene_graph, script_text)

    # Save back
    store.set_scene_graph(timeline_id, enriched)

    # Compute partiture
    partiture = bridge.compute_partiture(enriched)

    return {
        "success": True,
        "schema_version": "pulse_enrich_v1",
        "enriched_scenes": partiture["scene_count"],
        "tonic_key": partiture["tonic_key"],
        "tonic_musical": partiture["tonic_musical"],
        "energy_critics": partiture["energy_critics"],
        "camelot_path": partiture["camelot_path"],
    }


@pulse_router.post("/pulse/enrich-from-timeline/{timeline_id}")
async def cut_pulse_enrich_from_timeline(timeline_id: str) -> dict[str, Any]:
    """
    MARKER_179.10 — Extract visual signals from timeline clips and enrich scene graph.

    Computes cuts_per_minute and motion_intensity from clip data.
    """
    store = CutProjectStore.current()
    if not store:
        raise HTTPException(400, "No CUT project loaded")

    scene_graph = store.get_scene_graph(timeline_id)
    timeline_state = store.get_timeline_state(timeline_id)
    if not scene_graph:
        raise HTTPException(404, f"No scene graph for timeline {timeline_id}")
    if not timeline_state:
        raise HTTPException(404, f"No timeline state for {timeline_id}")

    bridge = get_pulse_timeline_bridge()
    enriched = bridge.enrich_from_timeline(scene_graph, timeline_state)

    store.set_scene_graph(timeline_id, enriched)
    partiture = bridge.compute_partiture(enriched)

    return {
        "success": True,
        "schema_version": "pulse_enrich_v1",
        "enriched_scenes": partiture["scene_count"],
        "energy_critics": partiture["energy_critics"],
    }


@pulse_router.get("/pulse/partiture/{timeline_id}")
async def cut_pulse_partiture(timeline_id: str) -> dict[str, Any]:
    """
    MARKER_179.10 — Get full film partiture from enriched scene graph.

    Returns scores, camelot path, energy critics, tonic key.
    """
    store = CutProjectStore.current()
    if not store:
        raise HTTPException(400, "No CUT project loaded")

    scene_graph = store.get_scene_graph(timeline_id)
    if not scene_graph:
        raise HTTPException(404, f"No scene graph for timeline {timeline_id}")

    bridge = get_pulse_timeline_bridge()
    partiture = bridge.compute_partiture(scene_graph)

    return {
        "success": True,
        **partiture,
    }


@pulse_router.get("/pulse/scene-summary/{timeline_id}")
async def cut_pulse_scene_summary(timeline_id: str) -> dict[str, Any]:
    """
    MARKER_179.10 — Compact PULSE summary for all scenes.

    Returns per-scene camelot_key, pendulum, dramatic_function for frontend overlay.
    """
    store = CutProjectStore.current()
    if not store:
        raise HTTPException(400, "No CUT project loaded")

    scene_graph = store.get_scene_graph(timeline_id)
    if not scene_graph:
        raise HTTPException(404, f"No scene graph for timeline {timeline_id}")

    bridge = get_pulse_timeline_bridge()
    summary = bridge.get_scene_pulse_summary(scene_graph)

    return {
        "success": True,
        "schema_version": "pulse_scene_summary_v1",
        "scenes": summary,
        "total": len(summary),
    }


# ---------------------------------------------------------------------------
# MARKER_179.12_GENRE_CALIBRATION_ENDPOINTS
# ---------------------------------------------------------------------------


@pulse_router.get("/pulse/genre-profiles")
async def cut_pulse_genre_profiles() -> dict[str, Any]:
    """
    MARKER_179.12 — List all available genre calibration profiles.
    """
    return {
        "success": True,
        "profiles": list_genre_profiles(),
        "total": len(list_genre_profiles()),
    }


class CutPulseCalibratedRequest(BaseModel):
    """Request for genre-calibrated energy critics."""
    script_text: str
    genre: str = "drama"
    audio_bpm: float | None = None
    audio_key: str | None = None
    audio_camelot_key: str | None = None


@pulse_router.post("/pulse/energy-critics-calibrated")
async def cut_pulse_energy_critics_calibrated(
    req: CutPulseCalibratedRequest,
) -> dict[str, Any]:
    """
    MARKER_179.12 — Genre-aware energy critics with calibration.

    Same as /pulse/energy-critics but applies genre-specific multipliers.
    High raw scores that are normal for the genre get reduced.

    Validated on: Nights of Cabiria (art_house), Mad Max (action),
    Mulholland Drive (surreal) — Grok 179.0A research.
    """
    if not req.script_text:
        raise HTTPException(400, "script_text is required")

    conductor = get_pulse_conductor()
    analyzer = get_script_analyzer()

    narrative_scenes = analyzer.analyze(req.script_text)
    scores = []
    for nbpm in narrative_scenes:
        audio = None
        if req.audio_bpm is not None or req.audio_camelot_key:
            engine = get_camelot_engine()
            camelot = req.audio_camelot_key or ""
            if not camelot and req.audio_key:
                camelot = engine.key_from_musical(req.audio_key) or ""
            audio = AudioBPM(
                bpm=req.audio_bpm or 120.0,
                key=req.audio_key or "",
                camelot_key=camelot,
                confidence=0.6,
            )
        score = conductor.score_scene(
            scene_id=nbpm.scene_id,
            narrative=nbpm,
            audio=audio,
        )
        scores.append(score)

    result = compute_calibrated_energies(scores, genre=req.genre)

    return {
        "success": True,
        "schema_version": "pulse_energy_critics_calibrated_v1",
        "scene_count": len(scores),
        **result,
    }


# ---------------------------------------------------------------------------
# PULSE Triangle + StorySpace3D endpoints — Phase 179 Sprint 5
# MARKER_179.14_TRIANGLE_STORYSPACE_ENDPOINTS
# ---------------------------------------------------------------------------


class CutPulseTriangleEnergiesRequest(BaseModel):
    """Request for McKee Triangle-calibrated energy critics."""
    script_text: str
    arch: float | None = None
    mini: float | None = None
    anti: float | None = None
    genre: str | None = None


@pulse_router.post("/pulse/triangle-energies")
async def cut_pulse_triangle_energies(
    req: CutPulseTriangleEnergiesRequest,
) -> dict[str, Any]:
    """
    MARKER_179.14 — McKee Triangle-calibrated energy critics.

    Replaces discrete genre calibration with continuous barycentric interpolation.
    If arch/mini/anti provided, uses explicit triangle position.
    If genre provided, maps genre → triangle position.
    If neither, infers from scores' scales.
    """
    analyzer = get_script_analyzer()
    conductor = get_pulse_conductor()

    narrative_scenes = analyzer.analyze(req.script_text)
    scores = []
    for nbpm in narrative_scenes:
        score = conductor.score_scene(scene_id=nbpm.scene_id, narrative=nbpm)
        scores.append(score)

    if not scores:
        return {"success": False, "error": "No scenes detected in script"}

    # Determine triangle position
    triangle = None
    if req.arch is not None and req.mini is not None and req.anti is not None:
        triangle = TrianglePosition(arch=req.arch, mini=req.mini, anti=req.anti)
    elif req.genre:
        triangle = genre_to_triangle(req.genre)
    # else: inferred inside compute_triangle_energies

    result = compute_triangle_energies(scores, triangle=triangle)

    return {
        "success": True,
        "schema_version": "pulse_triangle_energies_v1",
        "scene_count": len(scores),
        **result,
    }


@pulse_router.get("/pulse/triangle-weights")
async def cut_pulse_triangle_weights(
    arch: float = 0.5,
    mini: float = 0.3,
    anti: float = 0.2,
) -> dict[str, Any]:
    """
    MARKER_179.14 — Preview interpolated critic weights for a triangle position.

    Pure computation, no script required. Useful for UI sliders.
    """
    triangle = TrianglePosition(arch=arch, mini=mini, anti=anti)
    weights = interpolate_critic_weights(triangle)

    return {
        "success": True,
        "schema_version": "pulse_triangle_weights_v1",
        "triangle": triangle.to_dict(),
        "dominant": triangle.dominant,
        "mckee_height": round(triangle.mckee_height, 3),
        "weights": weights,
    }


class CutPulseChaosIndexRequest(BaseModel):
    """Request for chaos index computation."""
    script_text: str


@pulse_router.post("/pulse/chaos-index")
async def cut_pulse_chaos_index(
    req: CutPulseChaosIndexRequest,
) -> dict[str, Any]:
    """
    MARKER_179.14 — Compute chaos index (6th energy critic).

    Measures unpredictability of transitions: key jumps, pendulum variance,
    energy direction reversals. High chaos = antiplot territory.
    """
    analyzer = get_script_analyzer()
    conductor = get_pulse_conductor()

    narrative_scenes = analyzer.analyze(req.script_text)
    scores = []
    for nbpm in narrative_scenes:
        score = conductor.score_scene(scene_id=nbpm.scene_id, narrative=nbpm)
        scores.append(score)

    if len(scores) < 3:
        return {
            "success": True,
            "schema_version": "pulse_chaos_index_v1",
            "chaos_index": 0.0,
            "scene_count": len(scores),
            "note": "Need at least 3 scenes to compute chaos index",
        }

    ci = chaos_index(scores)

    return {
        "success": True,
        "schema_version": "pulse_chaos_index_v1",
        "chaos_index": ci,
        "scene_count": len(scores),
        "interpretation": (
            "low_chaos" if ci < 0.3
            else "moderate_chaos" if ci < 0.6
            else "high_chaos"
        ),
    }


class CutPulseStorySpaceRequest(BaseModel):
    """Request for StorySpace3D point generation."""
    script_text: str


@pulse_router.post("/pulse/story-space")
async def cut_pulse_story_space(
    req: CutPulseStorySpaceRequest,
) -> dict[str, Any]:
    """
    MARKER_179.14 — Generate StorySpace3D points for frontend visualization.

    Each scene becomes a point in 3D space:
    - X/Y: Camelot wheel angle (horizontal plane)
    - Z: McKee triangle height (archplot=1, antiplot=0)
    - Color: pendulum position (-1..+1)
    - Size: energy level
    """
    analyzer = get_script_analyzer()
    conductor = get_pulse_conductor()

    narrative_scenes = analyzer.analyze(req.script_text)
    scores = []
    for nbpm in narrative_scenes:
        score = conductor.score_scene(scene_id=nbpm.scene_id, narrative=nbpm)
        scores.append(score)

    if not scores:
        return {"success": False, "error": "No scenes detected in script"}

    points = scores_to_story_space(scores)

    return {
        "success": True,
        "schema_version": "pulse_story_space_v1",
        "scene_count": len(points),
        "points": [p.to_dict() for p in points],
    }


@pulse_router.post("/pulse/story-space/{timeline_id}")
async def cut_pulse_story_space_from_timeline(
    timeline_id: str,
) -> dict[str, Any]:
    """
    MARKER_179.14 — Generate StorySpace3D points from existing timeline scene graph.

    Reads enriched scene graph (must be enriched first via /pulse/enrich-*),
    reconstructs PulseScores, and converts to StorySpacePoints.
    """
    store = CutProjectStore.get_instance()
    scene_graph = store.load_scene_graph(timeline_id)
    if not scene_graph:
        return {"success": False, "error": f"No scene graph for timeline {timeline_id}"}

    # Reconstruct PulseScores from enriched scene graph
    from src.services.pulse_conductor import PulseScore
    scene_nodes = [
        n for n in scene_graph.get("nodes", [])
        if n.get("node_type") == "scene"
    ]

    scores = []
    for node in scene_nodes:
        pd = node.get("metadata", {}).get("pulse_data", {})
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

    if not scores:
        return {"success": False, "error": "No enriched scenes found — run /pulse/enrich-* first"}

    points = scores_to_story_space(scores)

    return {
        "success": True,
        "schema_version": "pulse_story_space_v1",
        "timeline_id": timeline_id,
        "scene_count": len(points),
        "points": [p.to_dict() for p in points],
    }


# ---------------------------------------------------------------------------
# PULSE SRT → NarrativeBPM Bridge — Phase 179 Sprint 5
# MARKER_179.15_SRT_NARRATIVE_BRIDGE
# ---------------------------------------------------------------------------


class CutPulseSrtAnalyzeRequest(BaseModel):
    """Request to analyze SRT/VTT subtitle content."""
    srt_content: str
    gap_threshold_sec: float = 3.0
    max_scene_duration_sec: float = 120.0


@pulse_router.post("/pulse/srt-to-narrative")
async def cut_pulse_srt_to_narrative(
    req: CutPulseSrtAnalyzeRequest,
) -> dict[str, Any]:
    """
    MARKER_179.15 — Parse SRT/VTT subtitles → NarrativeBPM scenes.

    Groups subtitle blocks into scenes by timing gaps, then analyzes
    each scene for dramatic function, pendulum, and energy.
    Returns scenes with timing metadata for timeline alignment.
    """
    results = srt_to_narrative_bpm_with_timing(
        content=req.srt_content,
        gap_threshold_sec=req.gap_threshold_sec,
        max_scene_duration_sec=req.max_scene_duration_sec,
    )

    return {
        "success": True,
        "schema_version": "pulse_srt_narrative_v1",
        "scene_count": len(results),
        "scenes": results,
    }


@pulse_router.post("/pulse/srt-to-story-space")
async def cut_pulse_srt_to_story_space(
    req: CutPulseSrtAnalyzeRequest,
) -> dict[str, Any]:
    """
    MARKER_179.15 — SRT/VTT → full PULSE pipeline → StorySpace3D points.

    End-to-end: parse subtitles → NarrativeBPM → PulseScore → StorySpacePoint[].
    Ready for Three.js visualization.
    """
    conductor = get_pulse_conductor()

    narrative_scenes = srt_to_narrative_bpm(
        content=req.srt_content,
        gap_threshold_sec=req.gap_threshold_sec,
        max_scene_duration_sec=req.max_scene_duration_sec,
    )

    if not narrative_scenes:
        return {"success": False, "error": "No scenes detected in SRT content"}

    scores = []
    for nbpm in narrative_scenes:
        score = conductor.score_scene(scene_id=nbpm.scene_id, narrative=nbpm)
        scores.append(score)

    points = scores_to_story_space(scores)

    # Also compute chaos index for the whole sequence
    ci = chaos_index(scores) if len(scores) >= 3 else 0.0

    return {
        "success": True,
        "schema_version": "pulse_srt_story_space_v1",
        "scene_count": len(points),
        "chaos_index": ci,
        "points": [p.to_dict() for p in points],
    }


# ---------------------------------------------------------------------------
# PULSE Favorite Marker → StorySpacePoint — Phase 179 Sprint 5
# MARKER_179.20_MARKER_STORYSPACE
# ---------------------------------------------------------------------------


class CutPulseMarkerStorySpaceRequest(BaseModel):
    """Request to map markers to StorySpace3D points."""
    script_text: str
    sandbox_root: str
    kind_filter: str = "favorite"


@pulse_router.post("/pulse/markers-to-story-space")
async def cut_pulse_markers_to_story_space(
    req: CutPulseMarkerStorySpaceRequest,
) -> dict[str, Any]:
    """
    MARKER_179.20 — Map favorite markers to StorySpace3D points.

    1. Load marker bundle from project store
    2. Filter by kind (default: favorite)
    3. Score script via PULSE conductor
    4. Align each marker to nearest scene
    5. Return StorySpacePoints with marker metadata
    """
    # Load markers
    store = CutProjectStore(req.sandbox_root)
    marker_bundle = store.load_time_marker_bundle()
    if not marker_bundle:
        return {"success": False, "error": "No marker bundle found"}

    items = marker_bundle.get("items", [])
    filtered = [
        m for m in items
        if m.get("kind") == req.kind_filter
        and m.get("status", "active") != "archived"
    ]

    if not filtered:
        return {
            "success": True,
            "schema_version": "pulse_marker_story_space_v1",
            "marker_count": 0,
            "points": [],
            "note": f"No active '{req.kind_filter}' markers found",
        }

    # Score script
    analyzer = get_script_analyzer()
    conductor = get_pulse_conductor()

    narrative_scenes = analyzer.analyze(req.script_text)
    scores = []
    for nbpm in narrative_scenes:
        score = conductor.score_scene(scene_id=nbpm.scene_id, narrative=nbpm)
        scores.append(score)

    if not scores:
        return {"success": False, "error": "No scenes detected in script"}

    # Map markers to story space
    points = markers_to_story_space_points(filtered, scores)

    return {
        "success": True,
        "schema_version": "pulse_marker_story_space_v1",
        "marker_count": len(points),
        "scene_count": len(scores),
        "points": points,
    }


# ---------------------------------------------------------------------------
# MARKER_180.8 — BPM Markers endpoint
# Returns all 3 BPM sources as timestamped arrays + computed sync points
# Architecture doc §5.1, §5.2
# ---------------------------------------------------------------------------


class CutPulseBPMMarkersRequest(BaseModel):
    """Request for BPM markers — needs timeline context."""

    timeline_id: str = "main"
    sandbox_root: str = ""
    # Optional script text for script BPM calculation
    script_text: str = ""
    # Sync tolerance: how close beats must be to count as sync (seconds)
    sync_tolerance_sec: float = 0.083  # ±2 frames at 24fps


@pulse_router.post("/pulse/bpm-markers")
async def cut_pulse_bpm_markers(
    req: CutPulseBPMMarkersRequest,
) -> dict[str, Any]:
    """
    MARKER_180.8 — BPM markers for timeline track.

    Returns 3 BPM sources + computed sync points (orange dots):
    - audio_beats: from AudioBPM downbeats (green dots)
    - visual_cuts: from VisualBPM scene boundaries (blue dots)
    - script_events: from NarrativeBPM script analysis (white dots)
    - sync_points: where all 3 coincide within tolerance (orange dots)

    Architecture doc: VETKA_CUT_Interface_Architecture_v1.docx §5.1, §5.2
    """
    audio_beats: list[dict[str, Any]] = []
    visual_cuts: list[dict[str, Any]] = []
    script_events: list[dict[str, Any]] = []

    # --- Audio BPM: get from partiture/enriched scene graph ---
    store = CutProjectStore.get_instance()
    scene_graph = store.load_scene_graph(req.timeline_id) if store else None

    if scene_graph:
        scene_nodes = [
            n for n in scene_graph.get("nodes", [])
            if n.get("node_type") == "scene"
        ]
        for node in scene_nodes:
            pulse_data = node.get("metadata", {}).get("pulse_data", {})
            # Audio beats from downbeats
            if pulse_data.get("has_audio"):
                audio_bpm_val = pulse_data.get("audio_bpm", 120)
                start_sec = node.get("metadata", {}).get("start_sec", 0)
                end_sec = node.get("metadata", {}).get("end_sec", start_sec + 10)
                # Generate beat positions from BPM
                if audio_bpm_val > 0:
                    beat_interval = 60.0 / audio_bpm_val
                    t = start_sec
                    while t < end_sec:
                        audio_beats.append({
                            "sec": round(t, 3),
                            "bpm": round(audio_bpm_val, 1),
                            "source": "audio",
                        })
                        t += beat_interval

            # Visual cuts from scene boundaries
            if pulse_data.get("has_visual"):
                start_sec = node.get("metadata", {}).get("start_sec", 0)
                visual_cuts.append({
                    "sec": round(start_sec, 3),
                    "source": "visual",
                })

    # --- Script BPM: from script text analysis ---
    if req.script_text:
        analyzer = get_script_analyzer()
        narrative_scenes = analyzer.analyze(req.script_text)
        # Each scene transition is a script event
        # Script BPM = events per minute (§5.3)
        page_duration_sec = 60.0  # 1 page ≈ 60 seconds
        for i, nbpm in enumerate(narrative_scenes):
            event_sec = i * page_duration_sec / max(len(narrative_scenes), 1) * len(narrative_scenes)
            # Rough time: distribute evenly for now (SRT bridge gives real times)
            event_sec = i * page_duration_sec
            script_events.append({
                "sec": round(event_sec, 3),
                "type": nbpm.dramatic_function,
                "energy": round(nbpm.estimated_energy, 3),
                "scene_id": nbpm.scene_id,
                "source": "script",
            })
    elif scene_graph:
        # Fall back to scene boundaries as script events
        scene_nodes = [
            n for n in scene_graph.get("nodes", [])
            if n.get("node_type") == "scene"
        ]
        for node in scene_nodes:
            start_sec = node.get("metadata", {}).get("start_sec", 0)
            pulse_data = node.get("metadata", {}).get("pulse_data", {})
            script_events.append({
                "sec": round(start_sec, 3),
                "type": pulse_data.get("dramatic_function", "unknown"),
                "energy": round(pulse_data.get("energy", 0.5), 3),
                "scene_id": node.get("node_id", ""),
                "source": "script",
            })

    # --- Compute sync points (orange): where sources coincide ---
    sync_points: list[dict[str, Any]] = []
    tolerance = req.sync_tolerance_sec

    # Collect all timestamps
    audio_times = [b["sec"] for b in audio_beats]
    visual_times = [v["sec"] for v in visual_cuts]
    script_times = [s["sec"] for s in script_events]

    # For each audio beat, check if visual AND script are nearby
    for at in audio_times:
        has_visual = any(abs(vt - at) <= tolerance for vt in visual_times)
        has_script = any(abs(st - at) <= tolerance for st in script_times)
        if has_visual and has_script:
            sync_points.append({
                "sec": round(at, 3),
                "strength": 1.0,
                "sources": ["audio", "visual", "script"],
            })
        elif has_visual or has_script:
            # Partial sync — 2 of 3 sources
            sources = ["audio"]
            if has_visual:
                sources.append("visual")
            if has_script:
                sources.append("script")
            sync_points.append({
                "sec": round(at, 3),
                "strength": 0.67,
                "sources": sources,
            })

    # Also check visual×script pairs that have no audio
    for vt in visual_times:
        has_audio = any(abs(at - vt) <= tolerance for at in audio_times)
        if has_audio:
            continue  # already handled above
        has_script = any(abs(st - vt) <= tolerance for st in script_times)
        if has_script:
            sync_points.append({
                "sec": round(vt, 3),
                "strength": 0.67,
                "sources": ["visual", "script"],
            })

    # Deduplicate sync points within tolerance
    deduped_sync: list[dict[str, Any]] = []
    for sp in sorted(sync_points, key=lambda x: x["sec"]):
        if not deduped_sync or abs(sp["sec"] - deduped_sync[-1]["sec"]) > tolerance:
            deduped_sync.append(sp)
        elif sp["strength"] > deduped_sync[-1]["strength"]:
            deduped_sync[-1] = sp  # keep the stronger one

    return {
        "success": True,
        "schema_version": "pulse_bpm_markers_v1",
        "audio_beats": audio_beats,
        "audio_beat_count": len(audio_beats),
        "visual_cuts": visual_cuts,
        "visual_cut_count": len(visual_cuts),
        "script_events": script_events,
        "script_event_count": len(script_events),
        "sync_points": deduped_sync,
        "sync_point_count": len(deduped_sync),
        "sync_tolerance_sec": tolerance,
    }


# ---------------------------------------------------------------------------
# MARKER_180.13 — PULSE Auto-Montage endpoint
# Architecture doc §7: 3 modes, always new timeline, never overwrite
# ---------------------------------------------------------------------------


class CutPulseAutoMontageRequest(BaseModel):
    """Request for auto-montage."""

    mode: str = "favorites"  # "favorites" | "script" | "music"
    project_name: str = "project"
    version: int = 1
    sandbox_root: str = ""
    timeline_id: str = "main"
    # Mode-specific params
    script_text: str = ""  # for script mode
    order_by: str = "time"  # for favorites mode: "time" | "energy" | "script"
    # Music mode
    music_bpm: float = 120.0
    music_key: str = "8B"
    music_camelot_key: str = "8B"


@pulse_router.post("/pulse/auto-montage")
async def cut_pulse_auto_montage(
    req: CutPulseAutoMontageRequest,
) -> dict[str, Any]:
    """
    MARKER_180.13 — PULSE Auto-Montage: 3 modes, always creates new timeline.

    Modes:
    - favorites: Assembles from favorite markers in marker bundle
    - script: Matches script scenes to available materials
    - music: Matches materials to music track via Camelot/mood

    Architecture doc §7.1 SAFETY: "NEVER overwrite existing work."
    """
    from src.services.pulse_auto_montage import (
        FavoriteMarker,
        MaterialAsset,
        get_auto_montage,
    )
    from src.services.pulse_conductor import AudioBPM

    engine = get_auto_montage()

    if req.mode == "favorites":
        # Load markers from project store
        store = CutProjectStore.get_instance()
        marker_bundle = store.load_time_marker_bundle() if store else None

        markers: list[FavoriteMarker] = []
        if marker_bundle:
            for item in marker_bundle.get("items", []):
                if item.get("kind") == "favorite" and item.get("status", "active") != "archived":
                    markers.append(FavoriteMarker(
                        marker_id=item.get("marker_id", ""),
                        media_path=item.get("media_path", ""),
                        start_sec=item.get("start_sec", 0),
                        end_sec=item.get("end_sec", 0),
                        score=item.get("score", 1.0),
                        text=item.get("text", ""),
                    ))

        result = engine.assemble_favorites(
            markers=markers,
            project_name=req.project_name,
            version=req.version,
            order_by=req.order_by,
        )

    elif req.mode == "script":
        # Gather materials from scene graph
        store = CutProjectStore.get_instance()
        scene_graph = store.load_scene_graph(req.timeline_id) if store else None

        materials: list[MaterialAsset] = []
        if scene_graph:
            for node in scene_graph.get("nodes", []):
                if node.get("node_type") in ("clip", "take", "asset"):
                    meta = node.get("metadata", {})
                    pulse = meta.get("pulse_data", {})
                    materials.append(MaterialAsset(
                        asset_id=node.get("node_id", ""),
                        source_path=meta.get("source_path", ""),
                        duration_sec=meta.get("duration_sec", 30.0),
                        camelot_key=pulse.get("camelot_key", ""),
                        energy=pulse.get("energy", 0.5),
                        pendulum=pulse.get("pendulum_position", 0.0),
                        scene_id=meta.get("scene_id", ""),
                    ))

        result = engine.assemble_from_script(
            script_text=req.script_text,
            materials=materials,
            project_name=req.project_name,
            version=req.version,
        )

    elif req.mode == "music":
        # Build AudioBPM from request
        music = AudioBPM(
            bpm=req.music_bpm,
            key=req.music_key,
            camelot_key=req.music_camelot_key,
        )

        # Gather materials
        store = CutProjectStore.get_instance()
        scene_graph = store.load_scene_graph(req.timeline_id) if store else None

        materials_m: list[MaterialAsset] = []
        if scene_graph:
            for node in scene_graph.get("nodes", []):
                if node.get("node_type") in ("clip", "take", "asset"):
                    meta = node.get("metadata", {})
                    pulse = meta.get("pulse_data", {})
                    materials_m.append(MaterialAsset(
                        asset_id=node.get("node_id", ""),
                        source_path=meta.get("source_path", ""),
                        duration_sec=meta.get("duration_sec", 30.0),
                        camelot_key=pulse.get("camelot_key", ""),
                        energy=pulse.get("energy", 0.5),
                        pendulum=pulse.get("pendulum_position", 0.0),
                    ))

        result = engine.assemble_from_music(
            music_audio=music,
            materials=materials_m,
            project_name=req.project_name,
            version=req.version,
        )

    else:
        return {"success": False, "error": f"Unknown mode: {req.mode}. Use 'favorites', 'script', or 'music'."}

    return {
        "success": True,
        "schema_version": "pulse_auto_montage_v1",
        **result.to_dict(),
    }


# ---------------------------------------------------------------------------
# MARKER_180.17 — DAG Project endpoint
# Returns project asset DAG: nodes by cluster, edges by usage in script
# Architecture doc §2.2, §8
# ---------------------------------------------------------------------------

# Cluster types from Architecture doc §2.2
_DAG_CLUSTER_TYPES = {
    "character", "location", "take", "dub",
    "music", "sfx", "graphics", "other",
}


# ---------------------------------------------------------------------------
# MARKER_AUDIO_ANALYSIS — Per-clip audio analysis endpoint
# Wires cut_audio_analyzer.py (BPM/key/Camelot/energy/onsets) to the API.
# Section 6.10 of VETKA CUT Manual.
# ---------------------------------------------------------------------------

class CutAudioAnalyzeRequest(BaseModel):
    source_path: str = Field(..., description="Absolute path to audio/video file")
    max_duration: float = Field(300.0, description="Max seconds to analyze")
    energy_bins: int = Field(64, description="Energy contour resolution")


@pulse_router.post("/pulse/analyze-clip")
async def cut_pulse_analyze_clip(req: CutAudioAnalyzeRequest) -> dict[str, Any]:
    """
    Analyze a single audio/video clip: BPM, musical key, Camelot key,
    energy contour (64 bins), and onset times.

    Returns AudioAnalysisResult as JSON. If file not found or analysis fails,
    returns partial result with error field.
    """
    from src.services.cut_audio_analyzer import analyze_audio

    if not os.path.isfile(req.source_path):
        raise HTTPException(status_code=404, detail=f"File not found: {req.source_path}")

    try:
        result = analyze_audio(
            req.source_path,
            max_duration=req.max_duration,
            energy_bins=req.energy_bins,
        )
        return {
            "ok": True,
            "schema_version": "audio_analysis_v1",
            **result.to_dict(),
        }
    except Exception as exc:
        logging.getLogger(__name__).warning("analyze_audio failed: %s", exc)
        return {
            "ok": False,
            "error": str(exc),
            "source_path": req.source_path,
            "bpm": 0.0,
            "key": "",
            "camelot_key": "",
            "energy_contour": [],
            "onset_times": [],
            "duration_sec": 0.0,
        }

