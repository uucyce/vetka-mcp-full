"""
MARKER_B41 — Render sub-router.
Extracted from cut_routes.py: master render, batch render, presets, save.

@status: active
@phase: B41
@task: tb_1774243018_2
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.cut_mcp_job_store import get_cut_mcp_job_store
from src.services.cut_project_store import CutProjectStore

render_router = APIRouter(tags=["CUT-Render"])


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


class CutRenderMasterRequest(BaseModel):
    """Request for master video render."""
    sandbox_root: str = ""
    project_id: str = "project"
    timeline_id: str = "main"
    codec: str = "h264"
    resolution: str = "1080p"
    quality: int = Field(default=80, ge=1, le=100)
    fps: int = Field(default=25, ge=1, le=120)
    preset: str = ""
    range_in: float | None = None
    range_out: float | None = None
    audio_stems: bool = False
    audio_codec: str = "aac"
    bitrate_mode: str = "crf"
    target_bitrate: str = ""
    max_bitrate: str = ""
    mixer: dict[str, Any] | None = None


class CutRenderBatchRequest(BaseModel):
    """MARKER_B2.4 — Batch render: multiple presets in one job."""
    sandbox_root: str = ""
    project_id: str = "project"
    timeline_id: str = "main"
    presets: list[str] = Field(description="List of preset keys from EXPORT_PRESETS")
    mixer: dict[str, Any] | None = None


class CutSaveRequest(BaseModel):
    sandbox_root: str
    project_id: str = ""
    timeline_state: dict[str, Any] | None = None
    scene_graph: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _emit_render_progress(job_id: str, progress: float, message: str = "") -> None:
    """MARKER_B2.6 + B4.2 — Emit render progress via SocketIO with ETA."""
    try:
        import asyncio
        import time as _time
        from src.api.main import sio
        data: dict[str, Any] = {"job_id": job_id, "progress": round(progress, 3), "message": message}
        try:
            store = get_cut_mcp_job_store()
            job = store.get_job(job_id)
            if job:
                started = job.get("started_at") or job.get("created_at")
                if started and progress > 0.01:
                    elapsed = _time.time() - started
                    eta = (elapsed / progress) * (1.0 - progress) if progress < 1.0 else 0
                    data["elapsed_sec"] = round(elapsed, 1)
                    data["eta_sec"] = round(max(0, eta), 1)
        except Exception:
            pass
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(asyncio.ensure_future, sio.emit("render_progress", data))
        except RuntimeError:
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(sio.emit("render_progress", data))
                loop.close()
            except Exception:
                pass
    except Exception:
        pass


def _run_master_render_job(job_id: str, req: CutRenderMasterRequest) -> None:
    """MARKER_B6 + B2.1 — Background thread: delegates to cut_render_engine."""
    from src.services.cut_render_engine import render_timeline, RenderCancelled

    store = get_cut_mcp_job_store()
    try:
        store.update_job(job_id, state="running", progress=0.05)

        project_store = CutProjectStore.get_instance()
        if not project_store:
            store.update_job(job_id, state="error", error={"message": "No project store"})
            return

        timeline = project_store.load_timeline(req.timeline_id)
        if not timeline:
            store.update_job(job_id, state="error", error={"message": f"Timeline '{req.timeline_id}' not found"})
            return

        sandbox = req.sandbox_root or "/tmp/cut_sandbox"
        output_dir = os.path.join(sandbox, "cut_runtime", "renders")

        def on_progress(p: float, msg: str = "") -> None:
            store.update_job(job_id, progress=p)
            _emit_render_progress(job_id, p, msg)

        def cancel_check() -> bool:
            job = store.get_job(job_id)
            return bool(job and job.get("cancel_requested"))

        result = render_timeline(
            timeline, codec=req.codec, resolution=req.resolution, fps=req.fps,
            quality=req.quality, range_in=req.range_in, range_out=req.range_out,
            audio_stems=req.audio_stems, output_dir=output_dir, project_id=req.project_id,
            timeline_id=req.timeline_id, preset=req.preset, on_progress=on_progress,
            mixer=req.mixer, cancel_check=cancel_check, audio_codec=req.audio_codec,
            bitrate_mode=req.bitrate_mode, target_bitrate=req.target_bitrate, max_bitrate=req.max_bitrate,
        )
        store.update_job(job_id, state="done", progress=1.0, result=result)
        _emit_render_progress(job_id, 1.0, "done")

    except RenderCancelled:
        store.update_job(job_id, state="cancelled", progress=1.0, error={"message": "Render cancelled by user"})
        _emit_render_progress(job_id, 1.0, "cancelled")
    except Exception as exc:
        store.update_job(job_id, state="error", error={"message": str(exc)})
        _emit_render_progress(job_id, 0.0, f"error: {exc}")


def _run_batch_render_job(job_id: str, req: CutRenderBatchRequest) -> None:
    """MARKER_B2.4 — Sequential batch render."""
    from src.services.cut_render_engine import render_timeline, RenderCancelled, EXPORT_PRESETS

    store = get_cut_mcp_job_store()
    try:
        store.update_job(job_id, state="running", progress=0.0)

        project_store = CutProjectStore.get_instance()
        if not project_store:
            store.update_job(job_id, state="error", error={"message": "No project store"})
            return

        timeline = project_store.load_timeline(req.timeline_id)
        if not timeline:
            store.update_job(job_id, state="error", error={"message": f"Timeline '{req.timeline_id}' not found"})
            return

        sandbox = req.sandbox_root or "/tmp/cut_sandbox"
        output_dir = os.path.join(sandbox, "cut_runtime", "renders")
        total = len(req.presets)
        results: list[dict[str, Any]] = []
        completed = 0
        cancelled = False

        def cancel_check() -> bool:
            job = store.get_job(job_id)
            return bool(job and job.get("cancel_requested"))

        for i, preset_key in enumerate(req.presets):
            if cancel_check():
                cancelled = True
                break

            preset_cfg = EXPORT_PRESETS.get(preset_key)
            if not preset_cfg:
                results.append({"preset": preset_key, "success": False, "error": f"Unknown preset: {preset_key}"})
                completed += 1
                continue

            def on_progress(p: float, msg: str = "", _i: int = i) -> None:
                batch_progress = (_i + p) / total
                store.update_job(job_id, progress=round(batch_progress, 3))

            on_progress(0.0, f"Starting {preset_key}")
            try:
                result = render_timeline(
                    timeline, codec=preset_cfg.get("codec", "h264"),
                    resolution=preset_cfg.get("resolution", "1080p"),
                    fps=preset_cfg.get("fps", 25), quality=preset_cfg.get("quality", 80),
                    preset=preset_key, output_dir=output_dir, project_id=req.project_id,
                    timeline_id=req.timeline_id, mixer=req.mixer,
                    cancel_check=cancel_check, on_progress=on_progress,
                )
                results.append({"preset": preset_key, "success": True, "label": preset_cfg.get("label", preset_key), **result})
                completed += 1
            except RenderCancelled:
                results.append({"preset": preset_key, "success": False, "error": "cancelled"})
                cancelled = True
                break
            except Exception as exc:
                results.append({"preset": preset_key, "success": False, "error": str(exc)})
                completed += 1

        if cancelled:
            for j in range(len(results), total):
                results.append({"preset": req.presets[j], "success": False, "error": "skipped (batch cancelled)"})
            store.update_job(job_id, state="cancelled", progress=1.0, result={
                "results": results, "completed": completed, "total": total, "cancelled": True,
            })
        else:
            store.update_job(job_id, state="done", progress=1.0, result={
                "results": results, "completed": completed, "total": total, "cancelled": False,
                "success_count": sum(1 for r in results if r.get("success")),
                "failed_count": sum(1 for r in results if not r.get("success")),
            })
    except Exception as exc:
        store.update_job(job_id, state="error", error={"message": str(exc)})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@render_router.post("/render/master")
async def cut_render_master(req: CutRenderMasterRequest) -> dict[str, Any]:
    """MARKER_W6.1 — Master video render. Creates async job."""
    store = get_cut_mcp_job_store()
    job = store.create_job("render_master", {
        "sandbox_root": req.sandbox_root, "project_id": req.project_id,
        "timeline_id": req.timeline_id, "codec": req.codec,
        "resolution": req.resolution, "quality": req.quality, "fps": req.fps, "preset": req.preset,
    })
    thread = threading.Thread(target=_run_master_render_job, args=(str(job["job_id"]), req), daemon=True)
    thread.start()
    return {"success": True, "schema_version": "cut_render_master_v1", "job_id": str(job["job_id"]), "job": job}


@render_router.get("/render/presets")
async def cut_render_presets() -> dict[str, Any]:
    """MARKER_B2.3 — List available export presets."""
    from src.services.cut_render_engine import EXPORT_PRESETS
    presets = []
    for key, cfg in EXPORT_PRESETS.items():
        if key == "youtube":
            continue
        presets.append({
            "key": key, "label": cfg.get("label", key), "codec": cfg.get("codec", "h264"),
            "resolution": cfg.get("resolution", "1080p"), "fps": cfg.get("fps", 25),
            "quality": cfg.get("quality", 80), "aspect": cfg.get("aspect"),
        })
    return {"success": True, "presets": presets, "total": len(presets)}


@render_router.post("/render/batch")
async def cut_render_batch(req: CutRenderBatchRequest) -> dict[str, Any]:
    """MARKER_B2.4 — Batch render: export multiple presets sequentially."""
    if not req.presets:
        return {"success": False, "error": "No presets specified"}

    store = get_cut_mcp_job_store()
    job = store.create_job("render_batch", {
        "sandbox_root": req.sandbox_root, "project_id": req.project_id,
        "timeline_id": req.timeline_id, "presets": req.presets, "preset_count": len(req.presets),
    })
    thread = threading.Thread(target=_run_batch_render_job, args=(str(job["job_id"]), req), daemon=True)
    thread.start()
    return {
        "success": True, "schema_version": "cut_render_batch_v1",
        "job_id": str(job["job_id"]), "job": job, "preset_count": len(req.presets),
    }


@render_router.post("/save")
async def cut_save_project(req: CutSaveRequest) -> dict[str, Any]:
    """MARKER_W4.3: Flush current project state to disk."""
    store = CutProjectStore(req.sandbox_root)
    project = store.load_project()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    saved_at = datetime.now(timezone.utc).isoformat()
    project["updated_at"] = saved_at
    if req.project_id:
        project["project_id"] = req.project_id
    store.save_project(project)

    if req.timeline_state is not None:
        store.save_timeline_state(req.timeline_state)
    if req.scene_graph is not None:
        store.save_scene_graph(req.scene_graph)

    return {"success": True, "saved_at": saved_at, "project_id": str(project.get("project_id", ""))}
