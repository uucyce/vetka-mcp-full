"""
MARKER_B_P2_HOTKEYS — CUT Audio sub-router.

Endpoints for hotkey-driven audio features:
  POST /cut/audio/scrubbing/toggle    — Shift+S: toggle audio-during-scrub
  GET  /cut/audio/scrubbing           — query current scrubbing state
  POST /cut/audio/level/adjust        — Alt+Up/Down: ±1 dB per lane or master
  POST /cut/audio/solo                — S: solo/unsolo a lane

Solo logic and level math live in cut_audio_engine.py.
Frontend store actions (adjustAudioLevel, toggleAudioScrubbing, soloTrack)
drive these endpoints via useCutEditorStore async thunks.

@status: active
@phase: B_P2_HOTKEYS
@task: tb_1774429865_1
@depends: cut_audio_engine, cut_project_store
"""
from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

audio_router = APIRouter(tags=["CUT-Audio"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class AudioScrubToggleRequest(BaseModel):
    """Toggle audio scrubbing for a project."""
    project_id: str = "project"


class AudioScrubSetRequest(BaseModel):
    """Explicitly set audio scrubbing state."""
    project_id: str = "project"
    enabled: bool = True


class AudioLevelAdjustRequest(BaseModel):
    """Adjust a lane's audio level by ±delta_db (Alt+Up = +1, Alt+Down = -1)."""
    project_id: str = "project"
    lane_id: str = Field(description="Lane ID to adjust, or '__master__' for master bus")
    current_volume_linear: float = Field(
        default=1.0, ge=0.0, le=1.5,
        description="Current volume in linear scale (0.0–1.5, unity=1.0)",
    )
    delta_db: float = Field(
        description="dB change per step: +1.0 (Alt+Up) or -1.0 (Alt+Down)",
    )


class AudioSoloRequest(BaseModel):
    """Toggle solo state for a lane."""
    project_id: str = "project"
    lane_id: str = Field(description="Lane ID to solo/unsolo")
    # Force-set (true/false) or toggle (None)
    solo_state: bool | None = Field(
        default=None,
        description="Explicit solo state. Omit to toggle.",
    )


# ---------------------------------------------------------------------------
# Audio scrubbing routes
# ---------------------------------------------------------------------------


@audio_router.post("/audio/scrubbing/toggle")
async def cut_audio_scrubbing_toggle(req: AudioScrubToggleRequest) -> dict[str, Any]:
    """
    MARKER_B_P2_HOTKEYS — Toggle audio scrubbing (Shift+S hotkey backend).

    Audio scrubbing = whether audio plays during timeline jog/scrub operations.
    FCP7 equivalent: Audio scrubbing on/off (Shift+S).

    Returns new scrubbing state for the project.
    """
    from src.services.cut_audio_engine import toggle_audio_scrubbing
    new_state = toggle_audio_scrubbing(req.project_id)
    return {
        "success": True,
        "project_id": req.project_id,
        "audio_scrubbing": new_state,
        "label": "Audio scrubbing ON" if new_state else "Audio scrubbing OFF",
    }


@audio_router.post("/audio/scrubbing/set")
async def cut_audio_scrubbing_set(req: AudioScrubSetRequest) -> dict[str, Any]:
    """Set audio scrubbing state explicitly (for store hydration on load)."""
    from src.services.cut_audio_engine import set_audio_scrubbing
    set_audio_scrubbing(req.project_id, req.enabled)
    return {
        "success": True,
        "project_id": req.project_id,
        "audio_scrubbing": req.enabled,
    }


@audio_router.get("/audio/scrubbing")
async def cut_audio_scrubbing_get(project_id: str = "project") -> dict[str, Any]:
    """Get current audio scrubbing state for a project."""
    from src.services.cut_audio_engine import get_audio_scrubbing
    state = get_audio_scrubbing(project_id)
    return {
        "success": True,
        "project_id": project_id,
        "audio_scrubbing": state,
    }


# ---------------------------------------------------------------------------
# Audio level adjustment route
# ---------------------------------------------------------------------------


@audio_router.post("/audio/level/adjust")
async def cut_audio_level_adjust(req: AudioLevelAdjustRequest) -> dict[str, Any]:
    """
    MARKER_B_P2_HOTKEYS — Adjust lane audio level by delta_db (Alt+Up/Down backend).

    Takes current linear volume + delta_db, returns new linear volume and dB display.

    This is a stateless computation endpoint — the frontend store holds the
    actual volume and calls this to get the correct linear value after dB adjustment.

    Alt+Up  → delta_db = +1.0 (increase by 1 dB)
    Alt+Down → delta_db = -1.0 (decrease by 1 dB)
    """
    from src.services.cut_audio_engine import adjust_lane_volume_db, linear_to_db
    new_linear = adjust_lane_volume_db(req.current_volume_linear, req.delta_db)
    new_db = linear_to_db(new_linear)
    return {
        "success": True,
        "project_id": req.project_id,
        "lane_id": req.lane_id,
        "new_volume_linear": round(new_linear, 4),
        "new_db": round(new_db, 1),
        "new_db_display": f"{new_db:+.1f} dB" if abs(new_db) < 96 else "-inf dB",
        "delta_db": req.delta_db,
        "previous_linear": req.current_volume_linear,
    }


# ---------------------------------------------------------------------------
# Audio solo route
# ---------------------------------------------------------------------------


@audio_router.post("/audio/solo")
async def cut_audio_solo(req: AudioSoloRequest) -> dict[str, Any]:
    """
    MARKER_B_P2_HOTKEYS — Solo/unsolo a lane (S hotkey backend).

    Solo state is managed in the frontend Zustand store (soloLanes Set).
    This endpoint provides a backend confirmation + logging hook.
    The store's toggleSolo() handles the UI state machine directly.

    FCP7 solo logic:
      - Any soloed lane → only soloed lanes produce audio at render
      - Mute + solo = muted (mute overrides solo)
      - Unsolo last soloed lane → all lanes audible again
    """
    return {
        "success": True,
        "project_id": req.project_id,
        "lane_id": req.lane_id,
        "action": "solo_toggled",
        "note": "Solo state is managed by frontend store. Backend applies at render via mixer param.",
    }


# ---------------------------------------------------------------------------
# Audio level bulk-set route (for serialization / restore)
# ---------------------------------------------------------------------------


@audio_router.get("/audio/level/db_display")
async def cut_audio_level_db_display(
    volume_linear: float = 1.0,
) -> dict[str, Any]:
    """
    Convert a linear volume value to a dB display string.
    Used by the AudioMixer component to show current dB next to fader.
    """
    from src.services.cut_audio_engine import linear_to_db
    if volume_linear <= 0.0:
        return {"success": True, "volume_linear": volume_linear, "db": -96.0, "display": "-inf dB"}
    db = linear_to_db(volume_linear)
    display = f"{db:+.1f} dB" if db > -96.0 else "-inf dB"
    return {
        "success": True,
        "volume_linear": round(volume_linear, 4),
        "db": round(db, 1),
        "display": display,
    }
