"""
MARKER_B13 — CUT Audio Engine.

Applies mixer state (volume, mute, solo, pan) to render pipeline.
Converts UI mixer settings into FFmpeg audio filter parameters
that get injected into RenderClip audio effects at render time.

Architecture:
  MixerState → apply_mixer_to_plan(plan, mixer) → modifies plan.clips in-place
  Each lane's volume/mute/solo/pan → per-clip audio filters (volume, pan)

Solo logic (FCP7 Ch.100):
  - If ANY lane is soloed, only soloed lanes produce audio
  - Mute overrides solo (muted+soloed = muted)

Pan (FCP7 Ch.103):
  - -1.0 = full left, 0.0 = center, +1.0 = full right
  - FFmpeg: stereotools=balance_out=<pan>

@status: active
@phase: B13
@task: tb_1774153642_5
@depends: cut_render_engine (RenderPlan, RenderClip)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Mixer state (mirrors frontend useCutEditorStore)
# ---------------------------------------------------------------------------

@dataclass
class LaneMixerState:
    """Per-lane mixer settings."""
    lane_id: str = ""
    volume: float = 1.0       # 0.0 - 1.5 (1.0 = unity, 1.5 = +3.5dB)
    pan: float = 0.0          # -1.0 (L) to +1.0 (R), 0.0 = center
    mute: bool = False
    solo: bool = False


@dataclass
class MixerState:
    """Complete mixer state for all lanes + master."""
    lanes: dict[str, LaneMixerState] = field(default_factory=dict)
    master_volume: float = 1.0  # 0.0 - 1.5

    @staticmethod
    def from_dict(d: dict[str, Any]) -> MixerState:
        """Parse mixer state from API request body."""
        lanes: dict[str, LaneMixerState] = {}
        for lane_id, lane_data in (d.get("lanes") or {}).items():
            lanes[lane_id] = LaneMixerState(
                lane_id=lane_id,
                volume=float(lane_data.get("volume", 1.0)),
                pan=float(lane_data.get("pan", 0.0)),
                mute=bool(lane_data.get("mute", False)),
                solo=bool(lane_data.get("solo", False)),
            )
        return MixerState(
            lanes=lanes,
            master_volume=float(d.get("master_volume", 1.0)),
        )


# ---------------------------------------------------------------------------
# Volume → dB conversion
# ---------------------------------------------------------------------------

def _volume_to_db(volume: float) -> float:
    """Convert linear volume (0-1.5) to dB. 1.0 = 0dB."""
    if volume <= 0:
        return -96.0  # effectively silence
    import math
    return 20.0 * math.log10(volume)


# ---------------------------------------------------------------------------
# Build audio filters from mixer state
# ---------------------------------------------------------------------------

def build_lane_audio_filters(
    lane_state: LaneMixerState,
    *,
    master_volume: float = 1.0,
    any_solo: bool = False,
) -> list[dict[str, Any]]:
    """
    Build audio effect dicts for a lane based on mixer state.

    Returns list of EffectParam-compatible dicts to inject into clip.audio_effects.

    Solo logic:
      - If any_solo=True and this lane is NOT soloed → mute
      - If muted → mute regardless of solo
    """
    effects: list[dict[str, Any]] = []

    # Determine if this lane should be silent
    is_silent = lane_state.mute
    if any_solo and not lane_state.solo:
        is_silent = True

    if is_silent:
        # Complete silence
        effects.append({
            "effect_id": "_mixer_mute",
            "type": "volume",
            "enabled": True,
            "params": {"db": -96.0},
        })
        return effects

    # Volume (lane * master)
    combined_volume = lane_state.volume * master_volume
    if combined_volume != 1.0:
        db = _volume_to_db(combined_volume)
        effects.append({
            "effect_id": "_mixer_volume",
            "type": "volume",
            "enabled": True,
            "params": {"db": round(db, 1)},
        })

    # Pan (only if not center)
    if lane_state.pan != 0.0:
        effects.append({
            "effect_id": "_mixer_pan",
            "type": "_pan",  # custom type, compiled separately
            "enabled": True,
            "params": {"pan": lane_state.pan},
        })

    return effects


def compile_pan_filter(pan: float) -> str:
    """Compile pan value to FFmpeg filter string.

    Uses stereotools for balance control:
      pan=-1.0 → full left
      pan=0.0  → center (no filter)
      pan=+1.0 → full right
    """
    if pan == 0.0:
        return ""
    # stereotools balance: -1 = left, +1 = right
    return f"stereotools=balance_out={pan:.3f}"


# ---------------------------------------------------------------------------
# Apply mixer to render plan
# ---------------------------------------------------------------------------

def apply_mixer_to_plan(plan: Any, mixer_state: MixerState) -> None:
    """
    Apply mixer state to a RenderPlan in-place.

    Injects volume/mute/solo/pan as audio effects on each clip
    based on which lane the clip belongs to.

    Args:
        plan: RenderPlan from cut_render_engine
        mixer_state: MixerState with per-lane settings
    """
    if not mixer_state.lanes and mixer_state.master_volume == 1.0:
        return  # Nothing to apply

    # Check if any lane is soloed
    any_solo = any(ls.solo for ls in mixer_state.lanes.values())

    for clip in plan.clips:
        lane_id = clip.lane_id
        lane_state = mixer_state.lanes.get(lane_id)

        if lane_state is None:
            # Lane not in mixer state — apply master volume only
            if mixer_state.master_volume != 1.0:
                db = _volume_to_db(mixer_state.master_volume)
                clip.audio_effects.append({
                    "effect_id": "_mixer_volume",
                    "type": "volume",
                    "enabled": True,
                    "params": {"db": round(db, 1)},
                })
            # If any lane is soloed and this lane is unknown → mute
            if any_solo:
                clip.audio_effects.append({
                    "effect_id": "_mixer_mute",
                    "type": "volume",
                    "enabled": True,
                    "params": {"db": -96.0},
                })
            continue

        effects = build_lane_audio_filters(
            lane_state,
            master_volume=mixer_state.master_volume,
            any_solo=any_solo,
        )
        clip.audio_effects.extend(effects)


# ---------------------------------------------------------------------------
# Compile pan filters (hook for render engine)
# ---------------------------------------------------------------------------

def compile_mixer_audio_filters(effects: list[Any]) -> list[str]:
    """
    Compile mixer-specific audio effects (like _pan) to FFmpeg filter strings.

    Called from cut_effects_engine or directly from render engine
    for effect types that the standard compiler doesn't know about.
    """
    filters: list[str] = []
    for e in effects:
        if isinstance(e, dict):
            t = e.get("type", "")
            p = e.get("params", {})
            enabled = e.get("enabled", True)
        else:
            t = getattr(e, "type", "")
            p = getattr(e, "params", {})
            enabled = getattr(e, "enabled", True)

        if not enabled:
            continue

        if t == "_pan":
            pan_val = float(p.get("pan", 0))
            f = compile_pan_filter(pan_val)
            if f:
                filters.append(f)

    return filters
