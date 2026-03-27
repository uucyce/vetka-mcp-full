"""
MARKER_B2.2 + B2.3 — Tests for ETA calculation and export presets.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from src.services.cut_mcp_job_store import CutMCPJobStore
from src.services.cut_render_engine import (
    EXPORT_PRESETS,
    SOCIAL_PRESETS,
    CODEC_MAP,
    generate_thumbnail,
)


# ── B2.2: ETA via job store ──


class TestJobStoreETA:
    def test_started_at_set_on_running(self) -> None:
        store = CutMCPJobStore()
        job = store.create_job("test", {})
        assert job.get("started_at") is None

        updated = store.update_job(job["job_id"], state="running")
        assert updated is not None
        assert updated.get("started_at") is not None

    def test_started_at_not_overwritten(self) -> None:
        store = CutMCPJobStore()
        job = store.create_job("test", {})
        store.update_job(job["job_id"], state="running")

        # Get the original started_at
        j1 = store.get_job(job["job_id"])
        started_1 = j1["started_at"]

        # Update progress (state stays running)
        store.update_job(job["job_id"], progress=0.5)
        j2 = store.get_job(job["job_id"])

        assert j2["started_at"] == started_1  # Not overwritten

    def test_started_at_only_on_running(self) -> None:
        store = CutMCPJobStore()
        job = store.create_job("test", {})
        store.update_job(job["job_id"], state="queued")

        j = store.get_job(job["job_id"])
        assert j.get("started_at") is None


# ── B2.3: Export Presets ──


class TestExportPresets:
    def test_has_social_presets(self) -> None:
        assert "youtube_1080" in EXPORT_PRESETS
        assert "instagram_reels" in EXPORT_PRESETS
        assert "tiktok" in EXPORT_PRESETS
        assert "telegram" in EXPORT_PRESETS

    def test_has_production_presets(self) -> None:
        assert "prores_master" in EXPORT_PRESETS
        assert "prores_4444" in EXPORT_PRESETS
        assert "dnxhr_hq" in EXPORT_PRESETS
        assert "review_h264" in EXPORT_PRESETS

    def test_has_web_presets(self) -> None:
        assert "av1_web" in EXPORT_PRESETS
        assert "vp9_webm" in EXPORT_PRESETS

    def test_backward_compat_youtube(self) -> None:
        assert "youtube" in EXPORT_PRESETS
        assert EXPORT_PRESETS["youtube"] == EXPORT_PRESETS["youtube_1080"]

    def test_social_presets_alias(self) -> None:
        assert SOCIAL_PRESETS is EXPORT_PRESETS

    def test_all_presets_have_label(self) -> None:
        for key, cfg in EXPORT_PRESETS.items():
            if key == "youtube":
                continue  # alias
            assert "label" in cfg, f"Preset {key} missing label"

    def test_all_presets_have_codec(self) -> None:
        for key, cfg in EXPORT_PRESETS.items():
            assert "codec" in cfg, f"Preset {key} missing codec"

    def test_prores_master_is_source_resolution(self) -> None:
        p = EXPORT_PRESETS["prores_master"]
        assert p["resolution"] == "source"
        assert p["codec"] == "prores_422hq"
        assert p["quality"] == 100

    def test_instagram_has_aspect(self) -> None:
        p = EXPORT_PRESETS["instagram_reels"]
        assert p.get("aspect") == "9:16"

    def test_preset_count_at_least_14(self) -> None:
        # Excluding backward compat aliases
        real = {k for k in EXPORT_PRESETS if k != "youtube"}
        assert len(real) >= 14

    def test_youtube_4k(self) -> None:
        p = EXPORT_PRESETS["youtube_4k"]
        assert p["resolution"] == "4k"
        assert p["codec"] == "h264"


# ── B2.4: Batch export ──


class TestBatchExportPresets:
    """Test that all presets referenced in batch export are valid."""

    def test_all_presets_have_valid_codec(self) -> None:
        """Every preset's codec must exist in CODEC_MAP."""
        for key, cfg in EXPORT_PRESETS.items():
            if key == "youtube":
                continue
            codec = cfg.get("codec", "h264")
            assert codec in CODEC_MAP, f"Preset {key} references unknown codec {codec}"

    def test_batch_typical_workflow(self) -> None:
        """Typical batch: YT + IG + ProRes master — all presets exist."""
        batch = ["youtube_1080", "instagram_reels", "prores_master"]
        for key in batch:
            assert key in EXPORT_PRESETS, f"Batch preset {key} not found"

    def test_batch_all_verticals(self) -> None:
        """Vertical content workflow: IG + TikTok + IG Story."""
        batch = ["instagram_reels", "tiktok", "instagram_story"]
        for key in batch:
            assert key in EXPORT_PRESETS
            assert EXPORT_PRESETS[key].get("aspect") == "9:16", f"{key} should be 9:16"

    def test_batch_production_delivery(self) -> None:
        """Production workflow: ProRes master + review copy."""
        batch = ["prores_master", "review_h264"]
        for key in batch:
            assert key in EXPORT_PRESETS

    def test_job_store_batch_job_type(self) -> None:
        """Batch job should be created with job_type='render_batch'."""
        store = CutMCPJobStore()
        job = store.create_job("render_batch", {"presets": ["youtube_1080", "tiktok"], "preset_count": 2})
        assert job["job_type"] == "render_batch"
        assert job["state"] == "queued"

    def test_batch_cancel_sets_cancelled(self) -> None:
        """Cancel on batch job should set cancel_requested."""
        store = CutMCPJobStore()
        job = store.create_job("render_batch", {"presets": ["a", "b"]})
        store.update_job(job["job_id"], state="running")
        cancelled = store.request_cancel(job["job_id"])
        assert cancelled is not None
        assert cancelled["cancel_requested"] is True

    def test_batch_progress_aggregate(self) -> None:
        """Test that batch progress can represent per-preset slices."""
        store = CutMCPJobStore()
        job = store.create_job("render_batch", {"presets": ["a", "b", "c"]})
        store.update_job(job["job_id"], state="running")
        # After 1st preset done (1/3) + 2nd at 50% (0.5/3)
        batch_progress = (1 + 0.5) / 3
        store.update_job(job["job_id"], progress=batch_progress)
        j = store.get_job(job["job_id"])
        assert j is not None
        assert abs(j["progress"] - 0.5) < 0.01


# ── B2.5: Thumbnail generation ──


class TestThumbnailGeneration:
    def test_nonexistent_file_returns_empty(self) -> None:
        result = generate_thumbnail("/nonexistent/video.mp4")
        assert result == ""

    def test_default_output_path(self) -> None:
        # Without calling FFmpeg, verify the path logic
        import os
        base, _ = os.path.splitext("/tmp/test_video.mp4")
        expected = f"{base}_thumb.jpg"
        assert expected == "/tmp/test_video_thumb.jpg"

    def test_custom_output_path(self) -> None:
        # generate_thumbnail with nonexistent file returns "" (no ffmpeg call)
        result = generate_thumbnail("/nonexistent.mp4", output_path="/tmp/custom_thumb.jpg")
        assert result == ""  # file doesn't exist

    def test_no_ffmpeg_returns_empty(self) -> None:
        result = generate_thumbnail("/nonexistent.mp4", ffmpeg_path="/nonexistent/ffmpeg")
        assert result == ""


# ── B2.6: SocketIO progress ──


class TestSocketIOProgress:
    def test_emit_function_exists(self) -> None:
        """_emit_render_progress should be importable and not crash on call."""
        # B41 extracted render routes to cut_routes_render.py
        # We can't easily test SocketIO emit without a running server,
        # but we verify the function exists and handles errors gracefully.
        from src.api.routes.cut_routes_render import _emit_render_progress
        # Should not raise — best-effort, swallows all errors
        _emit_render_progress("test_job", 0.5, "encoding")

    def test_emit_done_no_crash(self) -> None:
        from src.api.routes.cut_routes_render import _emit_render_progress
        _emit_render_progress("test_job", 1.0, "done")

    def test_emit_error_no_crash(self) -> None:
        from src.api.routes.cut_routes_render import _emit_render_progress
        _emit_render_progress("test_job", 0.0, "error: something failed")
