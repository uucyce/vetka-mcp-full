from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4


class CutMCPJobStore:
    """
    MARKER_170.MCP.JOB_STORE_V1

    In-memory local job store for CUT bootstrap and follow-up MCP orchestration.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def create_job(self, job_type: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        job_id = str(uuid4())
        job = {
            "schema_version": "cut_mcp_job_v1",
            "job_id": job_id,
            "job_type": str(job_type),
            "state": "queued",
            "progress": 0.0,
            "retry_count": 0,
            "route_mode": "background",
            "cancel_requested": False,
            "cancel_requested_at": None,
            "degraded_mode": False,
            "degraded_reason": "",
            "input": dict(input_payload or {}),
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            self._jobs[job_id] = job
        return deepcopy(job)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(str(job_id))
            return deepcopy(job) if job else None

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [deepcopy(job) for job in self._jobs.values()]

    def update_job(
        self,
        job_id: str,
        *,
        state: str | None = None,
        progress: float | None = None,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        retry_count: int | None = None,
        route_mode: str | None = None,
        degraded_mode: bool | None = None,
        degraded_reason: str | None = None,
    ) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(str(job_id))
            if not job:
                return None
            if state is not None:
                job["state"] = str(state)
                # MARKER_B2.2: Record start time for ETA calculation
                if state == "running" and not job.get("started_at"):
                    job["started_at"] = datetime.now(timezone.utc).isoformat()
            if progress is not None:
                job["progress"] = max(0.0, min(1.0, float(progress)))
            if result is not None:
                job["result"] = dict(result)
            if error is not None:
                job["error"] = dict(error)
            if retry_count is not None:
                job["retry_count"] = max(0, int(retry_count))
            if route_mode is not None:
                job["route_mode"] = str(route_mode)
            if degraded_mode is not None:
                job["degraded_mode"] = bool(degraded_mode)
            if degraded_reason is not None:
                job["degraded_reason"] = str(degraded_reason)
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
            return deepcopy(job)

    def request_cancel(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(str(job_id))
            if not job:
                return None
            now = datetime.now(timezone.utc).isoformat()
            job["cancel_requested"] = True
            job["cancel_requested_at"] = now
            if str(job.get("state") or "") == "queued":
                job["state"] = "cancelled"
                job["progress"] = 1.0
            job["updated_at"] = now
            return deepcopy(job)

    def increment_retry(
        self,
        job_id: str,
        *,
        degraded_mode: bool = False,
        degraded_reason: str = "",
    ) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(str(job_id))
            if not job:
                return None
            job["retry_count"] = int(job.get("retry_count") or 0) + 1
            job["degraded_mode"] = bool(degraded_mode)
            job["degraded_reason"] = str(degraded_reason or "")
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
            return deepcopy(job)

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()


_STORE = CutMCPJobStore()


def get_cut_mcp_job_store() -> CutMCPJobStore:
    return _STORE
