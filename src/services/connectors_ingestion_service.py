"""
Connectors Ingestion Queue Service (Phase 147.3)

Creates queue jobs for Mycelium/web ingestion after connector scans.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConnectorsIngestionQueueService:
    def __init__(self, queue_file: str = "data/connectors_ingestion_queue.json") -> None:
        self.queue_file = queue_file
        self._lock = Lock()
        self._jobs: List[Dict] = []
        self._load()

    def _load(self) -> None:
        os.makedirs(os.path.dirname(self.queue_file), exist_ok=True)
        if not os.path.exists(self.queue_file):
            self._persist()
            return
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            jobs = raw.get("jobs", [])
            self._jobs = jobs if isinstance(jobs, list) else []
        except Exception:
            self._jobs = []
            self._persist()

    def _persist(self) -> None:
        payload = {
            "jobs": self._jobs[-400:],
            "updated_at": _utc_now_iso(),
        }
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def enqueue(self, provider_id: str, source: str, metadata: Optional[Dict] = None) -> Dict:
        job = {
            "job_id": f"conn-{uuid4().hex[:12]}",
            "provider_id": provider_id,
            "source": source,
            "status": "queued",
            "created_at": _utc_now_iso(),
            "metadata": metadata or {},
        }
        with self._lock:
            self._jobs.append(job)
            self._persist()
        return job

    def list(self, limit: int = 50) -> List[Dict]:
        with self._lock:
            items = list(self._jobs[-max(1, limit):])
        return list(reversed(items))


_svc: Optional[ConnectorsIngestionQueueService] = None


def get_connectors_ingestion_queue_service() -> ConnectorsIngestionQueueService:
    global _svc
    if _svc is None:
        _svc = ConnectorsIngestionQueueService()
    return _svc

