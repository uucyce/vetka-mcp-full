"""In-memory generation job registry.

@status: active
@phase: B98
@task: tb_1774432033_1
"""
import time
from threading import Lock
from typing import Any, Dict, List, Optional


class GenerationJobStore:
    """Thread-safe in-memory registry for generation jobs."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def create(self, job_id: str, provider: str, params: dict) -> dict:
        with self._lock:
            job = {
                "job_id": job_id,
                "provider": provider,
                "params": params,
                "status": "queued",
                "progress": 0.0,
                "output_url": None,
                "output_path": None,
                "error": None,
                "cost_usd": 0.0,
                "created_at": time.time(),
                "updated_at": time.time(),
                "provider_job_id": None,
            }
            self._jobs[job_id] = job
            return job.copy()

    def update(self, job_id: str, **kwargs) -> Optional[dict]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            job.update(kwargs)
            job["updated_at"] = time.time()
            return job.copy()

    def get(self, job_id: str) -> Optional[dict]:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.copy() if job else None

    def get_all(self) -> List[dict]:
        with self._lock:
            return [j.copy() for j in self._jobs.values()]

    def get_active(self) -> List[dict]:
        with self._lock:
            return [j.copy() for j in self._jobs.values()
                    if j["status"] in ("queued", "generating", "previewing")]

    def remove(self, job_id: str) -> bool:
        with self._lock:
            return self._jobs.pop(job_id, None) is not None
