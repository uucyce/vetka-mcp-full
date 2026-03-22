"""
MARKER_B2.2 + B2.3 — Tests for ETA calculation and export presets.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from src.services.cut_mcp_job_store import CutMCPJobStore
from src.services.cut_render_engine import EXPORT_PRESETS, SOCIAL_PRESETS, CODEC_MAP


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
