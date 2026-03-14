from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4


class MediaMCPJobStore:
    """
    In-memory local job store for media-MCP async orchestration.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def create_job(self, job_type: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        job_id = str(uuid4())
        job = {
            "schema_version": "media_mcp_job_v1",
            "job_id": job_id,
            "type": str(job_type),
            "state": "queued",
            "progress": 0.0,
            "retry_count": 0,
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

    def update_job(
        self,
        job_id: str,
        *,
        state: str | None = None,
        progress: float | None = None,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(str(job_id))
            if not job:
                return None
            if state is not None:
                job["state"] = str(state)
            if progress is not None:
                job["progress"] = max(0.0, min(1.0, float(progress)))
            if result is not None:
                job["result"] = dict(result)
            if error is not None:
                job["error"] = dict(error)
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
            return deepcopy(job)


_STORE = MediaMCPJobStore()


def get_media_mcp_job_store() -> MediaMCPJobStore:
    return _STORE

