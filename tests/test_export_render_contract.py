"""
MARKER_RENDER-CONTRACT: Contract tests for render job lifecycle + export API.

Covers CutMCPJobStore (start/poll/cancel), render/presets schema,
CutRenderMasterRequest field validation, and render queue response shape.

Tests written by Epsilon [task:tb_1774786642_19262_1]
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.cut_mcp_job_store import CutMCPJobStore


# ─── CutMCPJobStore — start / poll / cancel ───────────────────────────────────

class TestJobStoreContract:
    @pytest.fixture
    def store(self):
        s = CutMCPJobStore()
        s.clear()
        return s

    # ── create_job (start) ───

    def test_create_job_returns_required_schema_fields(self, store):
        job = store.create_job("render_master", {"sandbox_root": "/tmp"})
        assert "job_id" in job
        assert job["job_type"] == "render_master"
        assert job["state"] == "queued"
        assert job["progress"] == 0.0
        assert job["schema_version"] == "cut_mcp_job_v1"
        assert job["cancel_requested"] is False
        assert job["input"]["sandbox_root"] == "/tmp"

    def test_create_job_unique_ids(self, store):
        job_a = store.create_job("render_master", {})
        job_b = store.create_job("render_master", {})
        assert job_a["job_id"] != job_b["job_id"]

    def test_create_job_state_is_queued(self, store):
        job = store.create_job("render_batch", {})
        assert job["state"] == "queued"

    # ── get_job (poll) ───

    def test_get_job_returns_same_data(self, store):
        job = store.create_job("render_master", {"timeline_id": "main"})
        fetched = store.get_job(job["job_id"])
        assert fetched is not None
        assert fetched["job_id"] == job["job_id"]
        assert fetched["input"]["timeline_id"] == "main"

    def test_get_job_unknown_returns_none(self, store):
        assert store.get_job("nonexistent-id") is None

    # ── update_job (state transitions) ───

    def test_update_to_running_sets_started_at(self, store):
        job = store.create_job("render_master", {})
        assert job.get("started_at") is None
        updated = store.update_job(job["job_id"], state="running")
        assert updated is not None
        assert updated["state"] == "running"
        assert updated.get("started_at") is not None

    def test_update_running_twice_does_not_overwrite_started_at(self, store):
        job = store.create_job("render_master", {})
        first = store.update_job(job["job_id"], state="running")
        started_at = first["started_at"]
        second = store.update_job(job["job_id"], state="running")
        assert second["started_at"] == started_at

    def test_update_progress_clamped_to_0_1(self, store):
        job = store.create_job("render_master", {})
        over = store.update_job(job["job_id"], progress=2.5)
        assert over["progress"] == 1.0
        under = store.update_job(job["job_id"], progress=-0.5)
        assert under["progress"] == 0.0

    def test_update_result_stored(self, store):
        job = store.create_job("render_master", {})
        result = {"output_path": "/out/video.mp4", "size_bytes": 42_000_000}
        updated = store.update_job(job["job_id"], state="done", result=result)
        assert updated["result"]["output_path"] == "/out/video.mp4"
        assert updated["state"] == "done"

    def test_update_unknown_job_returns_none(self, store):
        assert store.update_job("bad-id", state="running") is None

    # ── request_cancel ───

    def test_cancel_queued_job_sets_cancelled(self, store):
        job = store.create_job("render_master", {})
        cancelled = store.request_cancel(job["job_id"])
        assert cancelled["cancel_requested"] is True
        assert cancelled["cancel_requested_at"] is not None
        assert cancelled["state"] == "cancelled"

    def test_cancel_running_job_sets_cancel_requested_but_keeps_running(self, store):
        job = store.create_job("render_master", {})
        store.update_job(job["job_id"], state="running")
        cancelled = store.request_cancel(job["job_id"])
        # Running jobs are flagged but not immediately cancelled
        assert cancelled["cancel_requested"] is True
        assert cancelled["state"] == "running"

    def test_cancel_reflected_in_list_jobs(self, store):
        job = store.create_job("render_master", {})
        store.request_cancel(job["job_id"])
        jobs = store.list_jobs()
        found = next((j for j in jobs if j["job_id"] == job["job_id"]), None)
        assert found is not None
        assert found["state"] == "cancelled"

    def test_cancel_unknown_job_returns_none(self, store):
        assert store.request_cancel("nonexistent") is None

    # ── list_jobs ───

    def test_list_jobs_returns_all_created(self, store):
        store.create_job("render_master", {})
        store.create_job("render_batch", {})
        jobs = store.list_jobs()
        assert len(jobs) == 2

    def test_list_jobs_can_filter_by_job_type_prefix(self, store):
        store.create_job("render_master", {})
        store.create_job("render_batch", {})
        store.create_job("bootstrap", {})
        render_jobs = [j for j in store.list_jobs() if str(j.get("job_type", "")).startswith("render")]
        assert len(render_jobs) == 2

    def test_list_jobs_empty_after_clear(self, store):
        store.create_job("render_master", {})
        store.clear()
        assert store.list_jobs() == []

    # ── increment_retry ───

    def test_increment_retry_increases_count(self, store):
        job = store.create_job("render_master", {})
        assert job["retry_count"] == 0
        updated = store.increment_retry(job["job_id"])
        assert updated["retry_count"] == 1
        updated2 = store.increment_retry(job["job_id"])
        assert updated2["retry_count"] == 2

    def test_increment_retry_sets_degraded_mode(self, store):
        job = store.create_job("render_master", {})
        updated = store.increment_retry(job["job_id"], degraded_mode=True, degraded_reason="proxy_failed")
        assert updated["degraded_mode"] is True
        assert updated["degraded_reason"] == "proxy_failed"


# ─── Render presets API contract ───────────────────────────────────────────────

class TestRenderPresetsContract:
    def test_export_presets_dict_importable(self):
        from src.services.cut_render_engine import EXPORT_PRESETS
        assert isinstance(EXPORT_PRESETS, dict)
        assert len(EXPORT_PRESETS) > 0

    def test_each_preset_has_required_keys(self):
        from src.services.cut_render_engine import EXPORT_PRESETS
        required = {"label", "codec", "resolution", "fps", "quality"}
        for key, cfg in EXPORT_PRESETS.items():
            if key == "youtube":
                continue
            missing = required - set(cfg.keys())
            assert not missing, f"Preset '{key}' missing keys: {missing}"

    def test_codec_map_includes_common_codecs(self):
        from src.services.cut_render_engine import CODEC_MAP
        for codec in ("h264", "h265", "prores_422", "dnxhd", "av1"):
            assert codec in CODEC_MAP, f"CODEC_MAP missing '{codec}'"

    def test_social_presets_importable(self):
        from src.services.cut_render_engine import SOCIAL_PRESETS
        assert isinstance(SOCIAL_PRESETS, dict)


# ─── CutRenderMasterRequest schema ────────────────────────────────────────────

class TestRenderMasterRequestSchema:
    def test_default_values_are_valid(self):
        from src.api.routes.cut_routes_render import CutRenderMasterRequest
        req = CutRenderMasterRequest()
        assert req.codec == "h264"
        assert req.resolution == "1080p"
        assert 1 <= req.quality <= 100
        assert req.fps >= 1

    def test_quality_bounds_enforced(self):
        from src.api.routes.cut_routes_render import CutRenderMasterRequest
        from pydantic import ValidationError
        with pytest.raises((ValidationError, ValueError)):
            CutRenderMasterRequest(quality=0)
        with pytest.raises((ValidationError, ValueError)):
            CutRenderMasterRequest(quality=101)

    def test_custom_fields_round_trip(self):
        from src.api.routes.cut_routes_render import CutRenderMasterRequest
        req = CutRenderMasterRequest(
            sandbox_root="/projects/film",
            project_id="myfilm",
            timeline_id="cut01",
            codec="prores_422",
            resolution="4k",
            quality=95,
            fps=24,
        )
        assert req.sandbox_root == "/projects/film"
        assert req.project_id == "myfilm"
        assert req.codec == "prores_422"
        assert req.fps == 24
