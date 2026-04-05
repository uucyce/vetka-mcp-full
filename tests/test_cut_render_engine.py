"""
MARKER_B5 — Tests for cut_render_engine.py.

Tests RenderPlan construction, FilterGraphBuilder output,
FFmpeg command generation (concat vs filter_complex), and
transition/speed handling.

@task: tb_1773981833_10
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from src.services.cut_render_engine import (
    CODEC_MAP,
    FilterGraphBuilder,
    RenderClip,
    RenderPlan,
    Transition,
    _build_atempo_chain,
    _map_transition_type,
    build_ffmpeg_command,
    build_render_plan,
    render_timeline,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_timeline(clips: list[dict], lane_type: str = "video_main") -> dict:
    """Build minimal timeline dict."""
    return {
        "lanes": [
            {
                "lane_id": "V1",
                "lane_type": lane_type,
                "clips": clips,
            }
        ]
    }


def _make_clip(path: str, start: float, dur: float, **kw) -> dict:
    return {"source_path": path, "start_sec": start, "duration_sec": dur, "clip_id": f"c_{start}", **kw}


CLIP_A = "/tmp/test_a.mp4"
CLIP_B = "/tmp/test_b.mp4"
CLIP_C = "/tmp/test_c.mp4"


@pytest.fixture(autouse=True)
def _create_fake_clips(tmp_path):
    """Create fake clip files so os.path.isfile passes."""
    for name in [CLIP_A, CLIP_B, CLIP_C]:
        os.makedirs(os.path.dirname(name), exist_ok=True)
        if not os.path.exists(name):
            open(name, "w").close()
    yield
    for name in [CLIP_A, CLIP_B, CLIP_C]:
        try:
            os.remove(name)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# build_render_plan
# ---------------------------------------------------------------------------

class TestBuildRenderPlan:
    def test_basic_plan(self):
        tl = _make_timeline([
            _make_clip(CLIP_A, 0, 5),
            _make_clip(CLIP_B, 5, 5),
        ])
        plan = build_render_plan(tl, output_dir="/tmp/test_renders")
        assert len(plan.clips) == 2
        assert plan.clips[0].source_path == CLIP_A
        assert plan.clips[1].source_path == CLIP_B
        assert plan.transitions == []  # no overlap

    def test_overlap_creates_transition(self):
        tl = _make_timeline([
            _make_clip(CLIP_A, 0, 5),
            _make_clip(CLIP_B, 4, 5),  # 1s overlap with A
        ])
        plan = build_render_plan(tl, output_dir="/tmp/test_renders")
        assert len(plan.transitions) == 1
        t = plan.transitions[0]
        assert t.type == "crossfade"
        assert abs(t.duration_sec - 1.0) < 0.1
        assert t.between == (0, 1)

    def test_social_preset_overrides(self):
        tl = _make_timeline([_make_clip(CLIP_A, 0, 5)])
        plan = build_render_plan(tl, preset="youtube", output_dir="/tmp/test_renders")
        assert plan.codec == "h264"
        assert plan.fps == 30
        assert plan.quality == 85

    def test_clips_sorted_by_start(self):
        tl = _make_timeline([
            _make_clip(CLIP_B, 5, 3),
            _make_clip(CLIP_A, 0, 5),
        ])
        plan = build_render_plan(tl, output_dir="/tmp/test_renders")
        assert plan.clips[0].source_path == CLIP_A
        assert plan.clips[1].source_path == CLIP_B

    def test_resolution_from_preset(self):
        tl = _make_timeline([_make_clip(CLIP_A, 0, 5)])
        plan = build_render_plan(tl, resolution="4k", output_dir="/tmp/test_renders")
        assert plan.width == 3840
        assert plan.height == 2160

    def test_speed_preserved(self):
        tl = _make_timeline([_make_clip(CLIP_A, 0, 5, speed=2.0)])
        plan = build_render_plan(tl, output_dir="/tmp/test_renders")
        assert plan.clips[0].speed == 2.0

    def test_source_trim_preserved(self):
        tl = _make_timeline([_make_clip(CLIP_A, 0, 3, source_in=2.0, source_out=5.0)])
        plan = build_render_plan(tl, output_dir="/tmp/test_renders")
        assert plan.clips[0].source_in == 2.0
        assert plan.clips[0].source_out == 5.0


# ---------------------------------------------------------------------------
# FilterGraphBuilder
# ---------------------------------------------------------------------------

class TestFilterGraphBuilder:
    def test_single_clip(self):
        plan = RenderPlan(
            clips=[RenderClip(source_path=CLIP_A, duration_sec=5)],
            width=1920, height=1080, fps=25,
        )
        builder = FilterGraphBuilder(plan)
        input_args, fg = builder.build()
        assert "-i" in input_args
        assert CLIP_A in input_args
        assert "[outv]" in fg
        assert "[outa]" in fg

    def test_two_clips_no_transition(self):
        plan = RenderPlan(
            clips=[
                RenderClip(source_path=CLIP_A, start_sec=0, duration_sec=5),
                RenderClip(source_path=CLIP_B, start_sec=5, duration_sec=5),
            ],
            width=1920, height=1080, fps=25,
        )
        builder = FilterGraphBuilder(plan)
        input_args, fg = builder.build()
        assert input_args.count("-i") == 2
        assert "concat" in fg

    def test_crossfade_transition(self):
        plan = RenderPlan(
            clips=[
                RenderClip(source_path=CLIP_A, start_sec=0, duration_sec=5),
                RenderClip(source_path=CLIP_B, start_sec=4, duration_sec=5),
            ],
            transitions=[Transition(type="crossfade", duration_sec=1.0, between=(0, 1))],
            width=1920, height=1080, fps=25,
        )
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "xfade" in fg
        assert "transition=fade" in fg
        assert "acrossfade" in fg

    def test_dip_to_black_transition(self):
        plan = RenderPlan(
            clips=[
                RenderClip(source_path=CLIP_A, start_sec=0, duration_sec=5),
                RenderClip(source_path=CLIP_B, start_sec=4, duration_sec=5),
            ],
            transitions=[Transition(type="dip_to_black", duration_sec=1.0, between=(0, 1))],
            width=1920, height=1080, fps=25,
        )
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "transition=fadeblack" in fg

    def test_speed_filter(self):
        plan = RenderPlan(
            clips=[RenderClip(source_path=CLIP_A, duration_sec=5, speed=2.0)],
            width=1920, height=1080, fps=25,
        )
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "setpts=0.5000*PTS" in fg
        assert "atempo=" in fg

    def test_trim_filter(self):
        plan = RenderPlan(
            clips=[RenderClip(source_path=CLIP_A, duration_sec=3, source_in=2.0, source_out=5.0)],
            width=1920, height=1080, fps=25,
        )
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "trim=start=2.0:end=5.0" in fg
        assert "atrim=start=2.0:end=5.0" in fg

    def test_three_clips_two_transitions(self):
        plan = RenderPlan(
            clips=[
                RenderClip(source_path=CLIP_A, start_sec=0, duration_sec=5),
                RenderClip(source_path=CLIP_B, start_sec=4, duration_sec=5),
                RenderClip(source_path=CLIP_C, start_sec=8, duration_sec=5),
            ],
            transitions=[
                Transition(type="crossfade", duration_sec=1.0, between=(0, 1)),
                Transition(type="dissolve", duration_sec=1.0, between=(1, 2)),
            ],
            width=1920, height=1080, fps=25,
        )
        builder = FilterGraphBuilder(plan)
        input_args, fg = builder.build()
        assert input_args.count("-i") == 3
        assert fg.count("xfade") == 2
        assert fg.count("acrossfade") == 2

    def test_scale_in_output(self):
        plan = RenderPlan(
            clips=[RenderClip(source_path=CLIP_A, duration_sec=5)],
            width=3840, height=2160, fps=30,
        )
        builder = FilterGraphBuilder(plan)
        _, fg = builder.build()
        assert "scale=3840:2160" in fg
        assert "fps=30" in fg


# ---------------------------------------------------------------------------
# build_ffmpeg_command
# ---------------------------------------------------------------------------

class TestBuildFfmpegCommand:
    def test_simple_uses_concat(self):
        plan = RenderPlan(
            clips=[
                RenderClip(source_path=CLIP_A, start_sec=0, duration_sec=5),
                RenderClip(source_path=CLIP_B, start_sec=5, duration_sec=5),
            ],
            codec="h264", resolution="1080p", fps=25, quality=80,
            output_path="/tmp/out.mp4",
        )
        cmd = build_ffmpeg_command(plan)
        assert "-f" in cmd
        assert "concat" in cmd
        assert "-filter_complex" not in cmd
        # Cleanup
        concat_path = getattr(plan, "_concat_path", None)
        if concat_path and os.path.exists(concat_path):
            os.remove(concat_path)

    def test_transitions_use_filter_complex(self):
        plan = RenderPlan(
            clips=[
                RenderClip(source_path=CLIP_A, start_sec=0, duration_sec=5),
                RenderClip(source_path=CLIP_B, start_sec=4, duration_sec=5),
            ],
            transitions=[Transition(type="crossfade", duration_sec=1.0, between=(0, 1))],
            codec="h264", resolution="1080p", fps=25, quality=80,
            output_path="/tmp/out.mp4",
        )
        cmd = build_ffmpeg_command(plan)
        assert "-filter_complex" in cmd
        assert "-map" in cmd
        assert "[outv]" in cmd[cmd.index("-map") + 1]

    def test_speed_uses_filter_complex(self):
        plan = RenderPlan(
            clips=[RenderClip(source_path=CLIP_A, duration_sec=5, speed=0.5)],
            codec="h264", output_path="/tmp/out.mp4",
            width=1920, height=1080, fps=25,
        )
        cmd = build_ffmpeg_command(plan)
        assert "-filter_complex" in cmd

    def test_codec_params(self):
        plan = RenderPlan(
            clips=[RenderClip(source_path=CLIP_A, duration_sec=5)],
            codec="prores_422", output_path="/tmp/out.mov",
            width=1920, height=1080, fps=25,
        )
        cmd = build_ffmpeg_command(plan)
        assert "prores_ks" in cmd
        assert "-profile:v" in cmd

    def test_crf_quality(self):
        plan = RenderPlan(
            clips=[
                RenderClip(source_path=CLIP_A, start_sec=0, duration_sec=5),
            ],
            codec="h264", quality=100, output_path="/tmp/out.mp4",
            resolution="1080p", fps=25,
        )
        cmd = build_ffmpeg_command(plan)
        crf_idx = cmd.index("-crf")
        assert cmd[crf_idx + 1] == "0"  # quality 100 → CRF 0

    def test_range_trim(self):
        plan = RenderPlan(
            clips=[
                RenderClip(source_path=CLIP_A, start_sec=0, duration_sec=10),
            ],
            codec="h264", output_path="/tmp/out.mp4",
            range_in=2.0, range_out=8.0,
            resolution="1080p", fps=25,
        )
        cmd = build_ffmpeg_command(plan)
        assert "-ss" in cmd
        assert "-t" in cmd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestAtemoChain:
    def test_normal_speed(self):
        chain = _build_atempo_chain(1.5)
        assert chain == ["atempo=1.5000"]

    def test_double_speed(self):
        chain = _build_atempo_chain(2.0)
        assert chain == ["atempo=2.0000"]

    def test_slow_speed(self):
        chain = _build_atempo_chain(0.25)
        assert len(chain) == 2  # 0.5 * 0.5
        assert chain[0] == "atempo=0.5"

    def test_very_fast(self):
        chain = _build_atempo_chain(4.0)
        assert chain == ["atempo=4.0000"]

    def test_zero_speed(self):
        chain = _build_atempo_chain(0)
        assert chain == ["anull"]


class TestTransitionMapping:
    def test_crossfade(self):
        assert _map_transition_type("crossfade") == "fade"

    def test_dip_to_black(self):
        assert _map_transition_type("dip_to_black") == "fadeblack"

    def test_dissolve(self):
        assert _map_transition_type("dissolve") == "dissolve"

    def test_unknown(self):
        assert _map_transition_type("unknown") == "fade"


# ---------------------------------------------------------------------------
# render_timeline (integration)
# ---------------------------------------------------------------------------

class TestRenderTimeline:
    def test_no_ffmpeg(self):
        tl = _make_timeline([_make_clip(CLIP_A, 0, 5)])
        with patch("src.services.cut_render_engine.shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="FFmpeg not found"):
                render_timeline(tl)

    def test_no_clips(self):
        tl = _make_timeline([], lane_type="audio_sync")  # no video lanes
        with patch("src.services.cut_render_engine.shutil.which", return_value="/usr/bin/ffmpeg"):
            with pytest.raises(RuntimeError, match="No video clips"):
                render_timeline(tl, output_dir="/tmp/test_renders")

    def test_successful_render(self, tmp_path):
        tl = _make_timeline([
            _make_clip(CLIP_A, 0, 5),
            _make_clip(CLIP_B, 4, 5),  # 1s crossfade
        ])
        output_dir = str(tmp_path / "renders")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = ""

        progress_calls = []

        def on_progress(p, msg):
            progress_calls.append((p, msg))

        with patch("src.services.cut_render_engine.shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("src.services.cut_render_engine.subprocess.run", return_value=mock_proc):
                # Create fake output file
                os.makedirs(output_dir, exist_ok=True)
                result = render_timeline(
                    tl,
                    output_dir=output_dir,
                    on_progress=on_progress,
                )

        assert result["clips_count"] == 2
        assert result["transitions_count"] == 1
        assert result["used_filter_complex"] is True
        assert result["codec"] == "h264"
        assert len(progress_calls) >= 3  # at least 0.05, 0.1, 0.3, 1.0

    def test_ffmpeg_failure(self, tmp_path):
        tl = _make_timeline([_make_clip(CLIP_A, 0, 5)])
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "Some FFmpeg error"

        with patch("src.services.cut_render_engine.shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("src.services.cut_render_engine.subprocess.run", return_value=mock_proc):
                with pytest.raises(RuntimeError, match="FFmpeg failed"):
                    render_timeline(tl, output_dir=str(tmp_path))
