"""
MARKER_B9 — CUT Effects Engine.

Per-clip video/audio effects pipeline. Effects are stored as a list of
EffectParams on each clip, compiled to FFmpeg filter strings at render time.

Supported video effects:
  - brightness, contrast, saturation, gamma (via eq filter)
  - hue shift (via hue filter)
  - blur (via boxblur/gblur)
  - sharpen (via unsharp)
  - denoise (via nlmeans)
  - vignette (via vignette)
  - fade in/out (via fade)
  - crop (via crop)
  - flip/mirror (via hflip/vflip)
  - lut (via lut3d)

Supported audio effects:
  - volume (via volume)
  - fade in/out (via afade)
  - eq (via equalizer)
  - compressor (via acompressor)
  - normalize (via loudnorm)

Architecture:
  ClipEffects → list[EffectParam] → compile_video_filters() → FFmpeg filter string
  Effects are composable, order-dependent, and serializable to JSON.

@status: active
@phase: B9
@task: tb_1773981848_12
@depends: cut_render_engine (FilterGraphBuilder)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Effect parameter types
# ---------------------------------------------------------------------------

@dataclass
class EffectParam:
    """A single effect with parameters."""
    effect_id: str = ""        # unique ID per instance
    type: str = ""             # effect type name (brightness, blur, etc.)
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClipEffects:
    """Complete effects stack for one clip."""
    clip_id: str = ""
    video_effects: list[EffectParam] = field(default_factory=list)
    audio_effects: list[EffectParam] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "video_effects": [
                {"effect_id": e.effect_id, "type": e.type, "enabled": e.enabled, "params": e.params}
                for e in self.video_effects
            ],
            "audio_effects": [
                {"effect_id": e.effect_id, "type": e.type, "enabled": e.enabled, "params": e.params}
                for e in self.audio_effects
            ],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> ClipEffects:
        return ClipEffects(
            clip_id=d.get("clip_id", ""),
            video_effects=[
                EffectParam(**e) for e in d.get("video_effects", [])
            ],
            audio_effects=[
                EffectParam(**e) for e in d.get("audio_effects", [])
            ],
        )


# ---------------------------------------------------------------------------
# Effect definitions — metadata for UI + validation
# ---------------------------------------------------------------------------

@dataclass
class EffectDef:
    """Effect type definition with parameter schema."""
    type: str
    label: str
    category: str       # "color", "blur", "transform", "time", "audio"
    params_schema: dict[str, dict[str, Any]]   # param_name → {type, min, max, default, step}
    ffmpeg_video: bool = True   # is it a video filter?
    ffmpeg_audio: bool = False  # is it an audio filter?


EFFECT_DEFS: dict[str, EffectDef] = {
    # === Color correction ===
    "brightness": EffectDef(
        type="brightness", label="Brightness", category="color",
        params_schema={"value": {"type": "float", "min": -1.0, "max": 1.0, "default": 0.0, "step": 0.01}},
    ),
    "contrast": EffectDef(
        type="contrast", label="Contrast", category="color",
        params_schema={"value": {"type": "float", "min": 0.0, "max": 3.0, "default": 1.0, "step": 0.01}},
    ),
    "saturation": EffectDef(
        type="saturation", label="Saturation", category="color",
        params_schema={"value": {"type": "float", "min": 0.0, "max": 3.0, "default": 1.0, "step": 0.01}},
    ),
    "gamma": EffectDef(
        type="gamma", label="Gamma", category="color",
        params_schema={"value": {"type": "float", "min": 0.1, "max": 5.0, "default": 1.0, "step": 0.01}},
    ),
    "hue": EffectDef(
        type="hue", label="Hue Shift", category="color",
        params_schema={"degrees": {"type": "float", "min": -180.0, "max": 180.0, "default": 0.0, "step": 1.0}},
    ),
    "exposure": EffectDef(
        type="exposure", label="Exposure", category="color",
        params_schema={"stops": {"type": "float", "min": -4.0, "max": 4.0, "default": 0.0, "step": 0.1}},
    ),
    "white_balance": EffectDef(
        type="white_balance", label="White Balance", category="color",
        params_schema={
            "temperature": {"type": "float", "min": 2000, "max": 12000, "default": 6500, "step": 100},
        },
    ),

    # === Blur / Sharpen ===
    "blur": EffectDef(
        type="blur", label="Gaussian Blur", category="blur",
        params_schema={"sigma": {"type": "float", "min": 0.0, "max": 30.0, "default": 0.0, "step": 0.5}},
    ),
    "sharpen": EffectDef(
        type="sharpen", label="Sharpen", category="blur",
        params_schema={
            "amount": {"type": "float", "min": 0.0, "max": 10.0, "default": 0.0, "step": 0.1},
            "size": {"type": "int", "min": 3, "max": 13, "default": 5, "step": 2},
        },
    ),
    "denoise": EffectDef(
        type="denoise", label="Denoise", category="blur",
        params_schema={"strength": {"type": "float", "min": 0.0, "max": 20.0, "default": 0.0, "step": 0.5}},
    ),

    # === Transform ===
    "vignette": EffectDef(
        type="vignette", label="Vignette", category="transform",
        params_schema={"angle": {"type": "float", "min": 0.0, "max": 1.5, "default": 0.4, "step": 0.05}},
    ),
    "crop": EffectDef(
        type="crop", label="Crop", category="transform",
        params_schema={
            "x": {"type": "int", "min": 0, "max": 7680, "default": 0},
            "y": {"type": "int", "min": 0, "max": 4320, "default": 0},
            "w": {"type": "int", "min": 1, "max": 7680, "default": 1920},
            "h": {"type": "int", "min": 1, "max": 4320, "default": 1080},
        },
    ),
    "hflip": EffectDef(
        type="hflip", label="Flip Horizontal", category="transform",
        params_schema={},
    ),
    "vflip": EffectDef(
        type="vflip", label="Flip Vertical", category="transform",
        params_schema={},
    ),

    # === MARKER_B16: Color correction ===
    "lift": EffectDef(
        type="lift", label="Lift (Shadows)", category="color",
        params_schema={
            "r": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "g": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "b": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
        },
    ),
    "midtone": EffectDef(
        type="midtone", label="Gamma (Midtones)", category="color",
        params_schema={
            "r": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "g": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "b": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
        },
    ),
    "gain": EffectDef(
        type="gain", label="Gain (Highlights)", category="color",
        params_schema={
            "r": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "g": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "b": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
        },
    ),
    "curves": EffectDef(
        type="curves", label="Curves", category="color",
        params_schema={
            "preset": {"type": "str", "default": "none",
                       "options": ["none", "lighter", "darker", "increase_contrast",
                                   "decrease_contrast", "strong_contrast", "negative",
                                   "vintage", "cross_process"]},
            "master": {"type": "str", "default": ""},   # custom spline: "0/0 0.25/0.2 0.5/0.6 1/1"
            "red": {"type": "str", "default": ""},
            "green": {"type": "str", "default": ""},
            "blue": {"type": "str", "default": ""},
        },
    ),
    "color_balance": EffectDef(
        type="color_balance", label="Color Balance", category="color",
        params_schema={
            "rs": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "gs": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "bs": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "rm": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "gm": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "bm": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "rh": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "gh": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
            "bh": {"type": "float", "min": -1.0, "max": 1.0, "default": 0, "step": 0.01},
        },
    ),

    # === MARKER_B12: Motion controls ===
    "position": EffectDef(
        type="position", label="Position", category="motion",
        params_schema={
            "x": {"type": "float", "min": -7680, "max": 7680, "default": 0, "step": 1},
            "y": {"type": "float", "min": -4320, "max": 4320, "default": 0, "step": 1},
        },
    ),
    "scale": EffectDef(
        type="scale", label="Scale", category="motion",
        params_schema={
            "x": {"type": "float", "min": 0.01, "max": 10.0, "default": 1.0, "step": 0.01},
            "y": {"type": "float", "min": 0.01, "max": 10.0, "default": 1.0, "step": 0.01},
            "uniform": {"type": "bool", "default": True},
        },
    ),
    "rotation": EffectDef(
        type="rotation", label="Rotation", category="motion",
        params_schema={
            "degrees": {"type": "float", "min": -360, "max": 360, "default": 0, "step": 0.5},
        },
    ),
    "anchor": EffectDef(
        type="anchor", label="Anchor Point", category="motion",
        params_schema={
            "x": {"type": "float", "min": 0, "max": 1.0, "default": 0.5, "step": 0.01},
            "y": {"type": "float", "min": 0, "max": 1.0, "default": 0.5, "step": 0.01},
        },
    ),
    "opacity": EffectDef(
        type="opacity", label="Opacity", category="motion",
        params_schema={
            "value": {"type": "float", "min": 0.0, "max": 1.0, "default": 1.0, "step": 0.01},
        },
    ),

    # === MARKER_FCP7-66: Drop Shadow (FCP7 Ch.66 p.1087) ===
    "drop_shadow": EffectDef(
        type="drop_shadow", label="Drop Shadow", category="motion",
        params_schema={
            "offset": {"type": "float", "min": 0, "max": 200, "default": 10, "step": 1},
            "angle": {"type": "float", "min": 0, "max": 360, "default": 135, "step": 1},
            "color": {"type": "str", "default": "black"},  # CSS color name or hex
            "softness": {"type": "float", "min": 0, "max": 100, "default": 5, "step": 1},
            "opacity": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5, "step": 0.01},
        },
    ),
    # === MARKER_FCP7-66: Distort — 4-corner pin perspective (FCP7 Ch.66 p.1089) ===
    "distort": EffectDef(
        type="distort", label="Distort (Corner Pin)", category="motion",
        params_schema={
            # Corner coordinates as fraction of frame (0.0-1.0)
            "tl_x": {"type": "float", "min": -0.5, "max": 1.5, "default": 0.0, "step": 0.01},
            "tl_y": {"type": "float", "min": -0.5, "max": 1.5, "default": 0.0, "step": 0.01},
            "tr_x": {"type": "float", "min": -0.5, "max": 1.5, "default": 1.0, "step": 0.01},
            "tr_y": {"type": "float", "min": -0.5, "max": 1.5, "default": 0.0, "step": 0.01},
            "bl_x": {"type": "float", "min": -0.5, "max": 1.5, "default": 0.0, "step": 0.01},
            "bl_y": {"type": "float", "min": -0.5, "max": 1.5, "default": 1.0, "step": 0.01},
            "br_x": {"type": "float", "min": -0.5, "max": 1.5, "default": 1.0, "step": 0.01},
            "br_y": {"type": "float", "min": -0.5, "max": 1.5, "default": 1.0, "step": 0.01},
        },
    ),
    # === MARKER_FCP7-66: Motion Blur (FCP7 Ch.66 p.1091) ===
    "motion_blur": EffectDef(
        type="motion_blur", label="Motion Blur", category="motion",
        params_schema={
            "amount": {"type": "float", "min": 0, "max": 100, "default": 0, "step": 1},
            "samples": {"type": "int", "min": 1, "max": 32, "default": 4, "step": 1},
        },
    ),

    # === MARKER_B26: Broadcast Safe ===
    "broadcast_safe": EffectDef(
        type="broadcast_safe", label="Broadcast Safe", category="color",
        params_schema={
            "mode": {"type": "str", "default": "clamp",
                     "options": ["clamp", "compress"]},
        },
    ),

    # === Time ===
    "fade_in": EffectDef(
        type="fade_in", label="Fade In", category="time",
        params_schema={"duration": {"type": "float", "min": 0.0, "max": 10.0, "default": 1.0, "step": 0.1}},
    ),
    "fade_out": EffectDef(
        type="fade_out", label="Fade Out", category="time",
        params_schema={"duration": {"type": "float", "min": 0.0, "max": 10.0, "default": 1.0, "step": 0.1}},
    ),

    # === Audio ===
    "volume": EffectDef(
        type="volume", label="Volume", category="audio",
        params_schema={"db": {"type": "float", "min": -60.0, "max": 24.0, "default": 0.0, "step": 0.5}},
        ffmpeg_video=False, ffmpeg_audio=True,
    ),
    "audio_fade_in": EffectDef(
        type="audio_fade_in", label="Audio Fade In", category="audio",
        params_schema={"duration": {"type": "float", "min": 0.0, "max": 10.0, "default": 1.0, "step": 0.1}},
        ffmpeg_video=False, ffmpeg_audio=True,
    ),
    "audio_fade_out": EffectDef(
        type="audio_fade_out", label="Audio Fade Out", category="audio",
        params_schema={"duration": {"type": "float", "min": 0.0, "max": 10.0, "default": 1.0, "step": 0.1}},
        ffmpeg_video=False, ffmpeg_audio=True,
    ),
    "loudnorm": EffectDef(
        type="loudnorm", label="Normalize Loudness", category="audio",
        params_schema={
            "target_lufs": {"type": "float", "min": -30.0, "max": -5.0, "default": -14.0, "step": 0.5},
        },
        ffmpeg_video=False, ffmpeg_audio=True,
    ),
    "compressor": EffectDef(
        type="compressor", label="Compressor", category="audio",
        params_schema={
            "threshold": {"type": "float", "min": 0.001, "max": 1.0, "default": 0.1, "step": 0.01},
            "ratio": {"type": "float", "min": 1.0, "max": 20.0, "default": 4.0, "step": 0.5},
        },
        ffmpeg_video=False, ffmpeg_audio=True,
    ),
    # === MARKER_B14: Audio transitions (FCP7 Ch.47) ===
    "audio_crossfade": EffectDef(
        type="audio_crossfade", label="Audio Cross Fade", category="audio",
        params_schema={
            "duration": {"type": "float", "min": 0.01, "max": 10.0, "default": 0.5, "step": 0.05},
            "curve": {"type": "str", "default": "equal_power",
                      "options": ["equal_power", "linear"]},
        },
        ffmpeg_video=False, ffmpeg_audio=True,
    ),
}


# ---------------------------------------------------------------------------
# FFmpeg filter compilation
# ---------------------------------------------------------------------------

def compile_video_filters(effects: list[EffectParam]) -> list[str]:
    """
    Compile a list of video EffectParams into FFmpeg filter strings.

    Returns a list of filter expressions, e.g.:
    ["eq=brightness=0.1:contrast=1.2:saturation=0.8", "gblur=sigma=2.0", "vignette=PI/4"]

    Brightness/contrast/saturation/gamma are merged into a single eq filter.
    """
    if not effects:
        return []

    filters: list[str] = []

    # Collect eq parameters (merge into one eq filter)
    eq_parts: dict[str, str] = {}

    for e in effects:
        if not e.enabled:
            continue

        t = e.type
        p = e.params

        if t == "brightness":
            val = float(p.get("value", 0))
            if val != 0:
                eq_parts["brightness"] = f"{val:.3f}"

        elif t == "contrast":
            val = float(p.get("value", 1))
            if val != 1.0:
                eq_parts["contrast"] = f"{val:.3f}"

        elif t == "saturation":
            val = float(p.get("value", 1))
            if val != 1.0:
                eq_parts["saturation"] = f"{val:.3f}"

        elif t == "gamma":
            val = float(p.get("value", 1))
            if val != 1.0:
                eq_parts["gamma"] = f"{val:.3f}"

        elif t == "exposure":
            # Exposure in stops → gamma approximation: gamma = 2^(-stops)
            stops = float(p.get("stops", 0))
            if stops != 0:
                gamma_val = 2.0 ** (-stops)
                eq_parts["gamma"] = f"{gamma_val:.3f}"

        elif t == "hue":
            deg = float(p.get("degrees", 0))
            if deg != 0:
                filters.append(f"hue=h={deg:.1f}")

        elif t == "white_balance":
            temp = float(p.get("temperature", 6500))
            if temp != 6500:
                shift = (temp - 6500) / 6500
                rs = -shift * 0.3
                bs = shift * 0.3
                filters.append(f"colorbalance=rs={rs:.3f}:bs={bs:.3f}")

        # MARKER_B16: Lift/Gamma/Gain (3-way color corrector)
        elif t == "lift":
            r, g, b = float(p.get("r", 0)), float(p.get("g", 0)), float(p.get("b", 0))
            if r != 0 or g != 0 or b != 0:
                filters.append(f"colorbalance=rs={r:.3f}:gs={g:.3f}:bs={b:.3f}")

        elif t == "midtone":
            r, g, b = float(p.get("r", 0)), float(p.get("g", 0)), float(p.get("b", 0))
            if r != 0 or g != 0 or b != 0:
                filters.append(f"colorbalance=rm={r:.3f}:gm={g:.3f}:bm={b:.3f}")

        elif t == "gain":
            r, g, b = float(p.get("r", 0)), float(p.get("g", 0)), float(p.get("b", 0))
            if r != 0 or g != 0 or b != 0:
                filters.append(f"colorbalance=rh={r:.3f}:gh={g:.3f}:bh={b:.3f}")

        elif t == "curves":
            preset = str(p.get("preset", "none"))
            master = str(p.get("master", ""))
            red = str(p.get("red", ""))
            green = str(p.get("green", ""))
            blue = str(p.get("blue", ""))
            if preset != "none":
                filters.append(f"curves=preset={preset}")
            elif master or red or green or blue:
                parts_c: list[str] = []
                if master:
                    parts_c.append(f"master='{master}'")
                if red:
                    parts_c.append(f"red='{red}'")
                if green:
                    parts_c.append(f"green='{green}'")
                if blue:
                    parts_c.append(f"blue='{blue}'")
                filters.append(f"curves={':'.join(parts_c)}")

        elif t == "color_balance":
            cb_parts: list[str] = []
            for key in ["rs", "gs", "bs", "rm", "gm", "bm", "rh", "gh", "bh"]:
                val = float(p.get(key, 0))
                if val != 0:
                    cb_parts.append(f"{key}={val:.3f}")
            if cb_parts:
                filters.append(f"colorbalance={':'.join(cb_parts)}")

        elif t == "blur":
            sigma = float(p.get("sigma", 0))
            if sigma > 0:
                filters.append(f"gblur=sigma={sigma:.1f}")

        elif t == "sharpen":
            amount = float(p.get("amount", 0))
            size = int(p.get("size", 5))
            if amount > 0:
                # unsharp=lx:ly:la (luma size x, y, amount)
                filters.append(f"unsharp={size}:{size}:{amount:.1f}")

        elif t == "denoise":
            strength = float(p.get("strength", 0))
            if strength > 0:
                filters.append(f"nlmeans=s={strength:.1f}")

        elif t == "vignette":
            angle = float(p.get("angle", 0.4))
            filters.append(f"vignette=PI/{max(0.1, angle):.2f}")

        elif t == "crop":
            x, y = int(p.get("x", 0)), int(p.get("y", 0))
            w, h = int(p.get("w", 0)), int(p.get("h", 0))
            if w > 0 and h > 0:
                filters.append(f"crop={w}:{h}:{x}:{y}")

        elif t == "broadcast_safe":
            # MARKER_B26: Broadcast Safe — clamp luma 16-235, chroma 16-240
            mode = str(p.get("mode", "clamp"))
            if mode == "compress":
                # Compress full range into legal range (preserves detail)
                filters.append("scale=in_range=full:out_range=tv")
            else:
                # Hard clamp via limiter filter
                filters.append("limiter=min=16:max=235:planes=1")

        elif t == "hflip":
            filters.append("hflip")

        elif t == "vflip":
            filters.append("vflip")

        elif t == "fade_in":
            dur = float(p.get("duration", 1))
            if dur > 0:
                filters.append(f"fade=t=in:st=0:d={dur:.2f}")

        elif t == "fade_out":
            dur = float(p.get("duration", 1))
            if dur > 0:
                # fade out needs clip duration — use large offset, caller should set st
                filters.append(f"fade=t=out:d={dur:.2f}")

        # MARKER_B12: Motion controls → FFmpeg filters
        elif t == "position":
            x, y = float(p.get("x", 0)), float(p.get("y", 0))
            if x != 0 or y != 0:
                # Pad canvas larger, then crop to shift position
                # More reliable: use overlay on black background
                filters.append(f"pad=iw+abs({x:.0f})*2:ih+abs({y:.0f})*2:{max(0, x):.0f}:{max(0, y):.0f}:black")

        elif t == "scale":
            sx = float(p.get("x", 1))
            sy = float(p.get("y", 1))
            uniform = p.get("uniform", True)
            if uniform:
                sy = sx
            if sx != 1.0 or sy != 1.0:
                filters.append(f"scale=iw*{sx:.4f}:ih*{sy:.4f}")

        elif t == "rotation":
            deg = float(p.get("degrees", 0))
            if deg != 0:
                rad = deg * 3.14159265 / 180.0
                filters.append(f"rotate={rad:.6f}:fillcolor=none")

        elif t == "opacity":
            val = float(p.get("value", 1))
            if val < 1.0:
                # Format as alpha via colorchannelmixer
                filters.append(f"colorchannelmixer=aa={val:.3f}")

        # MARKER_FCP7-66: Drop Shadow
        # FFmpeg: drawbox overlay approach — pad canvas, draw shadow, overlay original
        # Simplified: boxblur a shifted copy. For proper shadow, needs 2-pass or overlay.
        # Practical approach: use pad + colorize + overlay in a single filter chain.
        elif t == "drop_shadow":
            offset = float(p.get("offset", 10))
            angle = float(p.get("angle", 135))
            softness = float(p.get("softness", 5))
            opacity = float(p.get("opacity", 0.5))
            if offset > 0 and opacity > 0:
                import math
                rad = angle * math.pi / 180.0
                dx = round(offset * math.cos(rad))
                dy = round(offset * math.sin(rad))
                # Draw a darkened, blurred rectangle offset from the frame
                # Using drawbox with shadow simulation via colorize + boxblur
                color_hex = p.get("color", "black")
                if color_hex == "black":
                    color_hex = "0x000000"
                # Shadow: pad canvas larger, fill offset area, blur, then overlay
                # FFmpeg one-liner: split, colorize shadow copy, blur, shift, overlay
                blur_size = max(1, int(softness))
                filters.append(
                    f"split[shadow][orig];"
                    f"[shadow]colorchannelmixer=rr=0:gg=0:bb=0:aa={opacity:.2f},"
                    f"boxblur={blur_size}:{blur_size},"
                    f"pad=iw+{abs(dx)*2}:ih+{abs(dy)*2}:{max(0,-dx)}:{max(0,-dy)}:color=black@0[shd];"
                    f"[shd][orig]overlay={max(0,dx)}:{max(0,dy)}"
                )

        # MARKER_FCP7-66: Distort — 4-corner perspective via perspective filter
        elif t == "distort":
            tl_x = float(p.get("tl_x", 0)); tl_y = float(p.get("tl_y", 0))
            tr_x = float(p.get("tr_x", 1)); tr_y = float(p.get("tr_y", 0))
            bl_x = float(p.get("bl_x", 0)); bl_y = float(p.get("bl_y", 1))
            br_x = float(p.get("br_x", 1)); br_y = float(p.get("br_y", 1))
            # Check if non-identity
            is_identity = (tl_x == 0 and tl_y == 0 and tr_x == 1 and tr_y == 0
                          and bl_x == 0 and bl_y == 1 and br_x == 1 and br_y == 1)
            if not is_identity:
                # FFmpeg perspective filter: x0:y0:x1:y1:x2:y2:x3:y3
                # Coords are absolute pixels — we use expressions with iw/ih
                filters.append(
                    f"perspective="
                    f"x0={tl_x:.4f}*iw:y0={tl_y:.4f}*ih:"
                    f"x1={tr_x:.4f}*iw:y1={tr_y:.4f}*ih:"
                    f"x2={bl_x:.4f}*iw:y2={bl_y:.4f}*ih:"
                    f"x3={br_x:.4f}*iw:y3={br_y:.4f}*ih:"
                    f"interpolation=linear"
                )

        # MARKER_FCP7-66: Motion Blur — directional blur via avgblur/boxblur
        elif t == "motion_blur":
            amount = float(p.get("amount", 0))
            samples = int(p.get("samples", 4))
            if amount > 0:
                # Use avgblur for motion blur approximation
                # Higher samples = smoother but slower
                radius = max(1, int(amount * samples / 10))
                filters.append(f"avgblur=sizeX={radius}:sizeY=0:planes=7")

    # Build merged eq filter
    if eq_parts:
        eq_str = ":".join(f"{k}={v}" for k, v in eq_parts.items())
        filters.insert(0, f"eq={eq_str}")

    return filters


def compile_audio_filters(effects: list[EffectParam]) -> list[str]:
    """Compile audio EffectParams into FFmpeg audio filter strings."""
    if not effects:
        return []

    filters: list[str] = []

    for e in effects:
        if not e.enabled:
            continue

        t = e.type
        p = e.params

        if t == "volume":
            db = float(p.get("db", 0))
            if db != 0:
                filters.append(f"volume={db:.1f}dB")

        elif t == "audio_fade_in":
            dur = float(p.get("duration", 1))
            if dur > 0:
                filters.append(f"afade=t=in:st=0:d={dur:.2f}")

        elif t == "audio_fade_out":
            dur = float(p.get("duration", 1))
            if dur > 0:
                filters.append(f"afade=t=out:d={dur:.2f}")

        elif t == "loudnorm":
            lufs = float(p.get("target_lufs", -14))
            filters.append(f"loudnorm=I={lufs:.1f}:LRA=11:TP=-1.5")

        elif t == "compressor":
            threshold = float(p.get("threshold", 0.1))
            ratio = float(p.get("ratio", 4))
            filters.append(f"acompressor=threshold={threshold:.3f}:ratio={ratio:.1f}")

        # MARKER_B13: Mixer pan (injected by cut_audio_engine)
        elif t == "_pan":
            pan_val = float(p.get("pan", 0))
            if pan_val != 0:
                filters.append(f"stereotools=balance_out={pan_val:.3f}")

    return filters


# ---------------------------------------------------------------------------
# CSS filter preview (for real-time in browser)
# ---------------------------------------------------------------------------

def compile_css_filters(effects: list[EffectParam]) -> str:
    """
    Compile video effects to CSS filter string for real-time preview.

    Only a subset of effects can be previewed via CSS:
    brightness, contrast, saturation, blur, hue.
    """
    parts: list[str] = []

    for e in effects:
        if not e.enabled:
            continue

        t = e.type
        p = e.params

        if t == "brightness":
            val = float(p.get("value", 0))
            # CSS brightness(1.0) = normal, FFmpeg brightness 0 = normal
            parts.append(f"brightness({1.0 + val:.3f})")

        elif t == "contrast":
            val = float(p.get("value", 1))
            parts.append(f"contrast({val:.3f})")

        elif t == "saturation":
            val = float(p.get("value", 1))
            parts.append(f"saturate({val:.3f})")

        elif t == "blur":
            sigma = float(p.get("sigma", 0))
            if sigma > 0:
                parts.append(f"blur({sigma:.1f}px)")

        elif t == "hue":
            deg = float(p.get("degrees", 0))
            if deg != 0:
                parts.append(f"hue-rotate({deg:.0f}deg)")

        # MARKER_B12: Motion → CSS transform
        elif t == "opacity":
            val = float(p.get("value", 1))
            if val < 1.0:
                parts.append(f"opacity({val:.3f})")

        # MARKER_FCP7-66: CSS drop-shadow
        elif t == "drop_shadow":
            offset = float(p.get("offset", 10))
            angle = float(p.get("angle", 135))
            softness = float(p.get("softness", 5))
            opacity = float(p.get("opacity", 0.5))
            if offset > 0 and opacity > 0:
                import math
                dx = round(offset * math.cos(angle * math.pi / 180))
                dy = round(offset * math.sin(angle * math.pi / 180))
                parts.append(f"drop-shadow({dx}px {dy}px {softness:.0f}px rgba(0,0,0,{opacity:.2f}))")

    # Collect CSS transforms separately
    transforms: list[str] = []
    for e in effects:
        if not e.enabled:
            continue
        t, p = e.type, e.params
        if t == "position":
            x, y = float(p.get("x", 0)), float(p.get("y", 0))
            if x != 0 or y != 0:
                transforms.append(f"translate({x:.0f}px, {y:.0f}px)")
        elif t == "scale":
            sx = float(p.get("x", 1))
            sy = float(p.get("y", 1))
            if p.get("uniform", True):
                sy = sx
            if sx != 1.0 or sy != 1.0:
                transforms.append(f"scale({sx:.3f}, {sy:.3f})")
        elif t == "rotation":
            deg = float(p.get("degrees", 0))
            if deg != 0:
                transforms.append(f"rotate({deg:.1f}deg)")

    result = " ".join(parts) if parts else ""
    # CSS transforms go as a separate property — return combined
    if transforms:
        transform_str = " ".join(transforms)
        if result:
            return f"{result}; transform: {transform_str}"
        return f"transform: {transform_str}"
    return result if result else "none"


# ---------------------------------------------------------------------------
# Utility: list available effects for UI
# ---------------------------------------------------------------------------

def list_effects(category: str | None = None) -> list[dict[str, Any]]:
    """Return effect definitions for UI rendering."""
    result = []
    for eid, edef in EFFECT_DEFS.items():
        if category and edef.category != category:
            continue
        result.append({
            "type": edef.type,
            "label": edef.label,
            "category": edef.category,
            "params": edef.params_schema,
            "is_video": edef.ffmpeg_video,
            "is_audio": edef.ffmpeg_audio,
        })
    return result
