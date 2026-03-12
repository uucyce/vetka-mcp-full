"""
MARKER_177.MCC.BENCHMARK_STORE.V1

Shared benchmark store for adjacent MCC runtimes such as LiteRT.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_STORE_FILE = PROJECT_ROOT / "data" / "mcc_benchmark_records.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MCCBenchmarkStore:
    def __init__(self, store_file: Path = DEFAULT_STORE_FILE) -> None:
        self.store_file = Path(store_file)
        self.store_file.parent.mkdir(parents=True, exist_ok=True)

    def _empty(self) -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "updated_at": "",
            "records": {},
        }

    def _load(self) -> Dict[str, Any]:
        if not self.store_file.exists():
            return self._empty()
        try:
            data = json.loads(self.store_file.read_text(encoding="utf-8"))
        except Exception:
            return self._empty()
        if not isinstance(data, dict):
            return self._empty()
        if not isinstance(data.get("records"), dict):
            data["records"] = {}
        data.setdefault("schema_version", 1)
        data.setdefault("updated_at", "")
        return data

    def _save(self, data: Dict[str, Any]) -> None:
        data["updated_at"] = _utc_now_iso()
        self.store_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_record(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load()
        record = dict(payload or {})
        record_id = str(record.get("record_id") or f"bench_{uuid.uuid4().hex[:10]}")
        record["record_id"] = record_id
        record["runtime_name"] = str(record.get("runtime_name") or "benchmark").strip() or "benchmark"
        record["workflow_family"] = str(record.get("workflow_family") or "").strip()
        record["run_status"] = str(record.get("run_status") or "measured").strip() or "measured"
        record["task_id"] = str(record.get("task_id") or "").strip()
        record["runtime_ms"] = int(record.get("runtime_ms") or 0)
        record["cold_start_ms"] = int(record.get("cold_start_ms") or 0)
        record["artifact_missing_count"] = int(record.get("artifact_missing_count") or 0)
        record["required_artifact_count"] = int(record.get("required_artifact_count") or 0)
        record["artifact_present_count"] = int(record.get("artifact_present_count") or 0)
        record["success_rate"] = float(record.get("success_rate") or 0.0)
        record["created_at"] = str(record.get("created_at") or _utc_now_iso())
        record["updated_at"] = _utc_now_iso()
        data["records"][record_id] = record
        self._save(data)
        return dict(record)

    def list_records(
        self,
        *,
        runtime_name: str = "",
        workflow_family: str = "",
        task_id: str = "",
        limit: int = 20,
    ) -> list[Dict[str, Any]]:
        data = self._load()
        rows = []
        for raw in list(data.get("records", {}).values()):
            if not isinstance(raw, dict):
                continue
            if runtime_name and str(raw.get("runtime_name") or "") != str(runtime_name):
                continue
            if workflow_family and str(raw.get("workflow_family") or "") != str(workflow_family):
                continue
            if task_id and str(raw.get("task_id") or "") != str(task_id):
                continue
            rows.append(dict(raw))
        rows.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
        return rows[: max(1, int(limit or 20))]


_benchmark_store_singleton: Optional[MCCBenchmarkStore] = None


def get_mcc_benchmark_store() -> MCCBenchmarkStore:
    global _benchmark_store_singleton
    if _benchmark_store_singleton is None:
        _benchmark_store_singleton = MCCBenchmarkStore()
    return _benchmark_store_singleton
