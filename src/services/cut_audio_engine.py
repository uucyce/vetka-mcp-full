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


# ---------------------------------------------------------------------------
# MARKER_B17: LUFS Loudness Analysis (EBU R128)
# ---------------------------------------------------------------------------

# Broadcast loudness standards
LOUDNESS_STANDARDS: dict[str, dict[str, float]] = {
    "ebu_r128": {"target_lufs": -23.0, "tolerance": 1.0, "max_true_peak": -1.0, "label": "EBU R128 (Europe)"},
    "atsc_a85": {"target_lufs": -24.0, "tolerance": 2.0, "max_true_peak": -2.0, "label": "ATSC A/85 (US)"},
    "arib_tr_b32": {"target_lufs": -24.0, "tolerance": 2.0, "max_true_peak": -1.0, "label": "ARIB TR-B32 (Japan)"},
    "youtube": {"target_lufs": -14.0, "tolerance": 1.0, "max_true_peak": -1.0, "label": "YouTube"},
    "spotify": {"target_lufs": -14.0, "tolerance": 1.0, "max_true_peak": -1.0, "label": "Spotify"},
    "apple_music": {"target_lufs": -16.0, "tolerance": 1.0, "max_true_peak": -1.0, "label": "Apple Music"},
    "podcast": {"target_lufs": -16.0, "tolerance": 2.0, "max_true_peak": -1.0, "label": "Podcast (general)"},
}


@dataclass
class LoudnessResult:
    """Result of LUFS loudness analysis."""
    source_path: str = ""
    success: bool = False
    error: str = ""
    # EBU R128 measurements
    integrated_lufs: float = -70.0   # integrated loudness (whole file)
    true_peak_dbtp: float = -70.0    # true peak in dBTP
    lra: float = 0.0                 # loudness range (LU)
    threshold: float = -70.0        # measurement gate threshold
    # Compliance
    standard: str = ""
    compliant: bool = False
    deviation_lu: float = 0.0       # how far from target

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "success": self.success,
            "error": self.error,
            "integrated_lufs": self.integrated_lufs,
            "true_peak_dbtp": self.true_peak_dbtp,
            "lra": self.lra,
            "threshold": self.threshold,
            "standard": self.standard,
            "compliant": self.compliant,
            "deviation_lu": self.deviation_lu,
        }


def analyze_loudness(
    source_path: str,
    *,
    standard: str = "ebu_r128",
    timeout: float = 120.0,
) -> LoudnessResult:
    """
    Analyze audio loudness using FFmpeg ebur128 filter.

    FFmpeg command: ffmpeg -i file -af ebur128=peak=true -f null -
    Parses stderr for integrated loudness, true peak, LRA.

    Args:
        source_path: Path to media file.
        standard: Loudness standard key (ebu_r128, atsc_a85, youtube, etc.)
        timeout: FFmpeg subprocess timeout.

    Returns:
        LoudnessResult with measurements and compliance check.
    """
    import os
    import re
    import shutil
    import subprocess

    result = LoudnessResult(source_path=source_path, standard=standard)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        result.error = "ffmpeg_not_found"
        return result

    if not os.path.isfile(source_path):
        result.error = "file_not_found"
        return result

    # Run FFmpeg with ebur128 filter (measurement only, no output file)
    cmd = [
        ffmpeg,
        "-i", source_path,
        "-af", "ebur128=peak=true",
        "-f", "null", "-",
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        result.error = "ffmpeg_timeout"
        return result
    except OSError as exc:
        result.error = f"ffmpeg_error: {exc}"
        return result

    # ebur128 output is on stderr (FFmpeg convention)
    stderr = proc.stderr or ""

    # Parse summary block (appears at end of stderr):
    #   Summary:
    #     Integrated loudness:
    #       I:         -23.0 LUFS
    #       Threshold:  -33.0 LUFS
    #     Loudness range:
    #       LRA:         7.0 LU
    #     True peak:
    #       Peak:        -1.5 dBFS

    # Integrated loudness
    m = re.search(r"I:\s+(-?\d+\.?\d*)\s+LUFS", stderr)
    if m:
        result.integrated_lufs = float(m.group(1))
        result.success = True

    # Threshold
    m = re.search(r"Threshold:\s+(-?\d+\.?\d*)\s+LUFS", stderr)
    if m:
        result.threshold = float(m.group(1))

    # LRA
    m = re.search(r"LRA:\s+(-?\d+\.?\d*)\s+LU", stderr)
    if m:
        result.lra = float(m.group(1))

    # True peak
    m = re.search(r"Peak:\s+(-?\d+\.?\d*)\s+dBFS", stderr)
    if m:
        result.true_peak_dbtp = float(m.group(1))

    if not result.success:
        result.error = "parse_failed"
        return result

    # Compliance check
    std = LOUDNESS_STANDARDS.get(standard)
    if std:
        target = std["target_lufs"]
        tolerance = std["tolerance"]
        max_peak = std["max_true_peak"]
        result.deviation_lu = round(result.integrated_lufs - target, 1)
        lufs_ok = abs(result.deviation_lu) <= tolerance
        peak_ok = result.true_peak_dbtp <= max_peak
        result.compliant = lufs_ok and peak_ok

    return result


# ---------------------------------------------------------------------------
# MARKER_B_P2_HOTKEYS: Audio level adjustment (Alt+Up / Alt+Down)
# ---------------------------------------------------------------------------

# Range limits for lane volume in dB
_MIN_DB: float = -96.0   # silence floor
_MAX_DB: float = 12.0    # +12 dB hard ceiling


def db_to_linear(db: float) -> float:
    """Convert dB value to linear scale. -96 dB → 0, 0 dB → 1.0."""
    if db <= _MIN_DB:
        return 0.0
    import math
    return 10.0 ** (db / 20.0)


def linear_to_db(linear: float) -> float:
    """Convert linear volume to dB. 0 → -96, 1.0 → 0, 1.5 → ~3.5 dB."""
    if linear <= 0.0:
        return _MIN_DB
    import math
    return 20.0 * math.log10(linear)


def clamp_db(db: float) -> float:
    """Clamp dB value to valid range [_MIN_DB, _MAX_DB]."""
    return max(_MIN_DB, min(_MAX_DB, db))


def adjust_lane_volume_db(current_linear: float, delta_db: float) -> float:
    """
    Adjust a lane's linear volume by delta_db (e.g. ±1 dB per key step).

    Converts current linear → dB → adjusts by delta → clamps → back to linear.

    Args:
        current_linear: Current volume in linear scale (0..1.5 range from store).
        delta_db: Signed dB step (positive = louder, negative = quieter).

    Returns:
        New volume in linear scale (0..1.5), clamped to valid range.
    """
    current_db = linear_to_db(current_linear)
    new_db = clamp_db(current_db + delta_db)
    return db_to_linear(new_db)


# ---------------------------------------------------------------------------
# MARKER_B_P2_HOTKEYS: Audio scrubbing state (Shift+S toggle)
# In-memory flag — persisted per project session.
# ---------------------------------------------------------------------------

# Global scrubbing registry: project_id → bool
# Lightweight in-memory state (not persisted to disk — resets on server restart).
_audio_scrubbing_state: dict[str, bool] = {}


def get_audio_scrubbing(project_id: str) -> bool:
    """Get audio scrubbing state for a project. Default: True (enabled)."""
    return _audio_scrubbing_state.get(project_id, True)


def set_audio_scrubbing(project_id: str, enabled: bool) -> None:
    """Set audio scrubbing state for a project."""
    _audio_scrubbing_state[project_id] = enabled


def toggle_audio_scrubbing(project_id: str) -> bool:
    """Toggle audio scrubbing state. Returns new state."""
    new_state = not get_audio_scrubbing(project_id)
    set_audio_scrubbing(project_id, new_state)
    return new_state
