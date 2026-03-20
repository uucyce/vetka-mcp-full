"""
MARKER_B9 — Tests for cut_effects_engine.py.

Tests effect compilation to FFmpeg filters, CSS preview filters,
ClipEffects serialization, and render engine integration.

@task: tb_1773981848_12
"""
from __future__ import annotations

import pytest

from src.services.cut_effects_engine import (
    ClipEffects,
    EffectParam,
    compile_audio_filters,
    compile_css_filters,
    compile_video_filters,
    list_effects,
    EFFECT_DEFS,
)


# ---------------------------------------------------------------------------
# compile_video_filters
# ---------------------------------------------------------------------------

class TestCompileVideoFilters:
    def test_empty(self):
        assert compile_video_filters([]) == []

    def test_brightness(self):
        effects = [EffectParam(type="brightness", params={"value": 0.2})]
        result = compile_video_filters(effects)
        assert len(result) == 1
        assert "eq=" in result[0]
        assert "brightness=0.200" in result[0]

    def test_contrast(self):
        effects = [EffectParam(type="contrast", params={"value": 1.5})]
        result = compile_video_filters(effects)
        assert "contrast=1.500" in result[0]

    def test_saturation(self):
        effects = [EffectParam(type="saturation", params={"value": 0.5})]
        result = compile_video_filters(effects)
        assert "saturation=0.500" in result[0]

    def test_eq_merged(self):
        """brightness + contrast + saturation → single eq filter."""
        effects = [
            EffectParam(type="brightness", params={"value": 0.1}),
            EffectParam(type="contrast", params={"value": 1.3}),
            EffectParam(type="saturation", params={"value": 0.8}),
        ]
        result = compile_video_filters(effects)
        assert len(result) == 1  # merged into one eq
        assert "eq=" in result[0]
        assert "brightness=" in result[0]
        assert "contrast=" in result[0]
        assert "saturation=" in result[0]

    def test_gamma(self):
        effects = [EffectParam(type="gamma", params={"value": 2.0})]
        result = compile_video_filters(effects)
        assert "gamma=2.000" in result[0]

    def test_hue(self):
        effects = [EffectParam(type="hue", params={"degrees": 45})]
        result = compile_video_filters(effects)
        assert "hue=h=45.0" in result[0]

    def test_blur(self):
        effects = [EffectParam(type="blur", params={"sigma": 3.0})]
        result = compile_video_filters(effects)
        assert "gblur=sigma=3.0" in result[0]

    def test_sharpen(self):
        effects = [EffectParam(type="sharpen", params={"amount": 2.0, "size": 5})]
        result = compile_video_filters(effects)
        assert "unsharp=5:5:2.0" in result[0]

    def test_denoise(self):
        effects = [EffectParam(type="denoise", params={"strength": 5.0})]
        result = compile_video_filters(effects)
        assert "nlmeans=s=5.0" in result[0]

    def test_vignette(self):
        effects = [EffectParam(type="vignette", params={"angle": 0.4})]
        result = compile_video_filters(effects)
        assert "vignette=" in result[0]

    def test_crop(self):
        effects = [EffectParam(type="crop", params={"x": 100, "y": 50, "w": 1920, "h": 1080})]
        result = compile_video_filters(effects)
        assert "crop=1920:1080:100:50" in result[0]

    def test_hflip(self):
        effects = [EffectParam(type="hflip")]
        result = compile_video_filters(effects)
        assert result == ["hflip"]

    def test_vflip(self):
        effects = [EffectParam(type="vflip")]
        result = compile_video_filters(effects)
        assert result == ["vflip"]

    def test_fade_in(self):
        effects = [EffectParam(type="fade_in", params={"duration": 2.0})]
        result = compile_video_filters(effects)
        assert "fade=t=in:st=0:d=2.00" in result[0]

    def test_fade_out(self):
        effects = [EffectParam(type="fade_out", params={"duration": 1.5})]
        result = compile_video_filters(effects)
        assert "fade=t=out:d=1.50" in result[0]

    def test_disabled_effect_skipped(self):
        effects = [EffectParam(type="brightness", params={"value": 0.5}, enabled=False)]
        assert compile_video_filters(effects) == []

    def test_default_values_skipped(self):
        """brightness=0, contrast=1, saturation=1 → no filters (identity)."""
        effects = [
            EffectParam(type="brightness", params={"value": 0}),
            EffectParam(type="contrast", params={"value": 1.0}),
            EffectParam(type="saturation", params={"value": 1.0}),
        ]
        assert compile_video_filters(effects) == []

    def test_exposure_to_gamma(self):
        effects = [EffectParam(type="exposure", params={"stops": -1.0})]
        result = compile_video_filters(effects)
        assert "gamma=" in result[0]

    def test_white_balance(self):
        effects = [EffectParam(type="white_balance", params={"temperature": 3500})]
        result = compile_video_filters(effects)
        assert "colorbalance=" in result[0]

    def test_complex_chain(self):
        """Multiple effects → eq first, then others in order."""
        effects = [
            EffectParam(type="brightness", params={"value": 0.1}),
            EffectParam(type="blur", params={"sigma": 2.0}),
            EffectParam(type="hflip"),
        ]
        result = compile_video_filters(effects)
        assert len(result) == 3
        assert result[0].startswith("eq=")  # eq always first
        assert "gblur" in result[1]
        assert result[2] == "hflip"


# ---------------------------------------------------------------------------
# compile_audio_filters
# ---------------------------------------------------------------------------

class TestCompileAudioFilters:
    def test_empty(self):
        assert compile_audio_filters([]) == []

    def test_volume(self):
        effects = [EffectParam(type="volume", params={"db": -6.0})]
        result = compile_audio_filters(effects)
        assert "volume=-6.0dB" in result[0]

    def test_audio_fade_in(self):
        effects = [EffectParam(type="audio_fade_in", params={"duration": 2.0})]
        result = compile_audio_filters(effects)
        assert "afade=t=in:st=0:d=2.00" in result[0]

    def test_loudnorm(self):
        effects = [EffectParam(type="loudnorm", params={"target_lufs": -14.0})]
        result = compile_audio_filters(effects)
        assert "loudnorm=I=-14.0" in result[0]

    def test_compressor(self):
        effects = [EffectParam(type="compressor", params={"threshold": 0.1, "ratio": 4.0})]
        result = compile_audio_filters(effects)
        assert "acompressor=" in result[0]
        assert "ratio=4.0" in result[0]

    def test_disabled_skipped(self):
        effects = [EffectParam(type="volume", params={"db": -6}, enabled=False)]
        assert compile_audio_filters(effects) == []


# ---------------------------------------------------------------------------
# compile_css_filters
# ---------------------------------------------------------------------------

class TestCompileCSSFilters:
    def test_empty(self):
        assert compile_css_filters([]) == "none"

    def test_brightness(self):
        effects = [EffectParam(type="brightness", params={"value": 0.2})]
        assert "brightness(1.200)" in compile_css_filters(effects)

    def test_contrast(self):
        effects = [EffectParam(type="contrast", params={"value": 1.5})]
        assert "contrast(1.500)" in compile_css_filters(effects)

    def test_saturation(self):
        effects = [EffectParam(type="saturation", params={"value": 0.5})]
        assert "saturate(0.500)" in compile_css_filters(effects)

    def test_blur(self):
        effects = [EffectParam(type="blur", params={"sigma": 3.0})]
        assert "blur(3.0px)" in compile_css_filters(effects)

    def test_hue(self):
        effects = [EffectParam(type="hue", params={"degrees": 90})]
        assert "hue-rotate(90deg)" in compile_css_filters(effects)

    def test_multiple(self):
        effects = [
            EffectParam(type="brightness", params={"value": 0.1}),
            EffectParam(type="blur", params={"sigma": 2.0}),
        ]
        css = compile_css_filters(effects)
        assert "brightness(" in css
        assert "blur(" in css


# ---------------------------------------------------------------------------
# MARKER_B12: Motion controls
# ---------------------------------------------------------------------------

class TestMotionFilters:
    def test_position(self):
        effects = [EffectParam(type="position", params={"x": 100, "y": -50})]
        result = compile_video_filters(effects)
        assert len(result) == 1
        assert "pad=" in result[0]

    def test_scale(self):
        effects = [EffectParam(type="scale", params={"x": 1.5, "y": 1.5, "uniform": True})]
        result = compile_video_filters(effects)
        assert "scale=" in result[0]
        assert "1.5000" in result[0]

    def test_rotation(self):
        effects = [EffectParam(type="rotation", params={"degrees": 45})]
        result = compile_video_filters(effects)
        assert "rotate=" in result[0]

    def test_opacity(self):
        effects = [EffectParam(type="opacity", params={"value": 0.5})]
        result = compile_video_filters(effects)
        assert "colorchannelmixer=aa=0.500" in result[0]

    def test_opacity_full_no_filter(self):
        effects = [EffectParam(type="opacity", params={"value": 1.0})]
        assert compile_video_filters(effects) == []

    def test_scale_identity_no_filter(self):
        effects = [EffectParam(type="scale", params={"x": 1.0, "y": 1.0})]
        assert compile_video_filters(effects) == []

    def test_position_zero_no_filter(self):
        effects = [EffectParam(type="position", params={"x": 0, "y": 0})]
        assert compile_video_filters(effects) == []

    def test_rotation_zero_no_filter(self):
        effects = [EffectParam(type="rotation", params={"degrees": 0})]
        assert compile_video_filters(effects) == []


class TestMotionCSSPreview:
    def test_position_css(self):
        effects = [EffectParam(type="position", params={"x": 50, "y": -20})]
        css = compile_css_filters(effects)
        assert "translate(50px, -20px)" in css

    def test_scale_css(self):
        effects = [EffectParam(type="scale", params={"x": 2.0, "y": 2.0, "uniform": True})]
        css = compile_css_filters(effects)
        assert "scale(2.000" in css

    def test_rotation_css(self):
        effects = [EffectParam(type="rotation", params={"degrees": 90})]
        css = compile_css_filters(effects)
        assert "rotate(90.0deg)" in css

    def test_opacity_css(self):
        effects = [EffectParam(type="opacity", params={"value": 0.7})]
        css = compile_css_filters(effects)
        assert "opacity(0.700)" in css

    def test_combined_motion_css(self):
        effects = [
            EffectParam(type="position", params={"x": 10, "y": 20}),
            EffectParam(type="scale", params={"x": 1.5, "uniform": True}),
            EffectParam(type="rotation", params={"degrees": 30}),
        ]
        css = compile_css_filters(effects)
        assert "translate(" in css
        assert "scale(" in css
        assert "rotate(" in css


# ---------------------------------------------------------------------------
# ClipEffects serialization
# ---------------------------------------------------------------------------

class TestClipEffects:
    def test_to_dict(self):
        ce = ClipEffects(
            clip_id="c1",
            video_effects=[EffectParam(effect_id="e1", type="brightness", params={"value": 0.2})],
            audio_effects=[EffectParam(effect_id="e2", type="volume", params={"db": -3})],
        )
        d = ce.to_dict()
        assert d["clip_id"] == "c1"
        assert len(d["video_effects"]) == 1
        assert d["video_effects"][0]["type"] == "brightness"
        assert len(d["audio_effects"]) == 1

    def test_from_dict(self):
        d = {
            "clip_id": "c2",
            "video_effects": [{"effect_id": "e1", "type": "blur", "enabled": True, "params": {"sigma": 5}}],
            "audio_effects": [],
        }
        ce = ClipEffects.from_dict(d)
        assert ce.clip_id == "c2"
        assert len(ce.video_effects) == 1
        assert ce.video_effects[0].type == "blur"

    def test_roundtrip(self):
        ce = ClipEffects(
            clip_id="c3",
            video_effects=[
                EffectParam(effect_id="e1", type="saturation", params={"value": 1.5}),
                EffectParam(effect_id="e2", type="hflip"),
            ],
        )
        d = ce.to_dict()
        ce2 = ClipEffects.from_dict(d)
        assert ce2.clip_id == ce.clip_id
        assert len(ce2.video_effects) == 2
        assert ce2.video_effects[1].type == "hflip"


# ---------------------------------------------------------------------------
# list_effects
# ---------------------------------------------------------------------------

class TestListEffects:
    def test_all_effects(self):
        all_fx = list_effects()
        assert len(all_fx) >= 15

    def test_filter_by_category(self):
        color = list_effects(category="color")
        assert all(e["category"] == "color" for e in color)
        assert len(color) >= 5

    def test_audio_category(self):
        audio = list_effects(category="audio")
        assert all(e["is_audio"] for e in audio)

    def test_effect_has_params(self):
        all_fx = list_effects()
        for fx in all_fx:
            assert "type" in fx
            assert "label" in fx
            assert "params" in fx


# ---------------------------------------------------------------------------
# Render engine integration
# ---------------------------------------------------------------------------

class TestRenderEngineEffects:
    def test_effects_trigger_filter_complex(self):
        from src.services.cut_render_engine import RenderClip, RenderPlan, build_ffmpeg_command
        import os
        clip_path = "/tmp/test_a.mp4"
        os.makedirs(os.path.dirname(clip_path), exist_ok=True)
        if not os.path.exists(clip_path):
            open(clip_path, "w").close()

        plan = RenderPlan(
            clips=[RenderClip(
                source_path=clip_path,
                duration_sec=5,
                video_effects=[EffectParam(type="brightness", params={"value": 0.2})],
            )],
            codec="h264", output_path="/tmp/out.mp4",
            width=1920, height=1080, fps=25,
        )
        cmd = build_ffmpeg_command(plan)
        assert "-filter_complex" in cmd

        # Clean up
        try:
            os.remove(clip_path)
        except OSError:
            pass

    def test_effects_in_filter_graph(self):
        from src.services.cut_render_engine import RenderClip, RenderPlan, FilterGraphBuilder
        plan = RenderPlan(
            clips=[RenderClip(
                source_path="/tmp/test.mp4",
                duration_sec=5,
                video_effects=[
                    EffectParam(type="brightness", params={"value": 0.3}),
                    EffectParam(type="blur", params={"sigma": 2.0}),
                ],
                audio_effects=[
                    EffectParam(type="volume", params={"db": -3}),
                ],
            )],
            width=1920, height=1080, fps=25,
        )
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "eq=brightness=" in fg
        assert "gblur=" in fg
        assert "volume=-3.0dB" in fg
