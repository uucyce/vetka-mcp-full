"""
MARKER_177.LOCALGUYS.RUN_REGISTRY.V1

Persistent runtime registry for MCC localguys workflow runs.
Tracks playground binding, current step, and artifact contract state.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_REGISTRY_FILE = PROJECT_ROOT / "data" / "mcc_local_runs.json"
DEFAULT_ARTIFACTS_ROOT = PROJECT_ROOT / "artifacts" / "mcc_local"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_ts(value: str) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


class LocalguysRunRegistry:
    def __init__(
        self,
        registry_file: Path = DEFAULT_REGISTRY_FILE,
        artifacts_root: Path = DEFAULT_ARTIFACTS_ROOT,
    ) -> None:
        self.registry_file = Path(registry_file)
        self.artifacts_root = Path(artifacts_root)
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts_root.mkdir(parents=True, exist_ok=True)

    def _empty(self) -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "updated_at": "",
            "runs": {},
            "task_latest": {},
        }

    def _load(self) -> Dict[str, Any]:
        if not self.registry_file.exists():
            return self._empty()
        try:
            data = json.loads(self.registry_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return self._empty()
            runs = data.get("runs")
            task_latest = data.get("task_latest")
            if not isinstance(runs, dict):
                data["runs"] = {}
            if not isinstance(task_latest, dict):
                data["task_latest"] = {}
            if "schema_version" not in data:
                data["schema_version"] = 1
            if "updated_at" not in data:
                data["updated_at"] = ""
            return data
        except Exception:
            return self._empty()

    def _save(self, data: Dict[str, Any]) -> None:
        data["updated_at"] = _utc_now_iso()
        self.registry_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _sanitize_artifact_name(name: str) -> str:
        clean = "/".join(part for part in str(name or "").split("/") if part not in {"", ".", ".."})
        if not clean or clean.startswith("/"):
            raise ValueError("artifact_name is invalid")
        return clean

    @staticmethod
    def _render_base_path(template: str, *, task_id: str, run_id: str) -> str:
        raw = str(template or "artifacts/mcc_local/{task_id}/").strip() or "artifacts/mcc_local/{task_id}/"
        try:
            rendered = raw.format(task_id=task_id, run_id=run_id)
        except Exception:
            rendered = raw.replace("{task_id}", task_id).replace("{run_id}", run_id)
        return rendered.strip("/")

    def _artifact_layout(self, task_id: str, run_id: str, contract: Dict[str, Any]) -> Dict[str, Any]:
        artifact_contract = contract.get("artifact_contract") or {}
        required = [str(name).strip() for name in list(artifact_contract.get("required") or []) if str(name).strip()]
        base_rel = self._render_base_path(
            str(artifact_contract.get("base_path") or "artifacts/mcc_local/{task_id}/"),
            task_id=task_id,
            run_id=run_id,
        )
        base_rel_path = Path(base_rel)
        if base_rel_path.parts and base_rel_path.parts[0] == "artifacts":
            base_rel_path = Path(*base_rel_path.parts[1:])
        base_dir = self.artifacts_root / base_rel_path
        artifact_root = base_dir / run_id
        artifact_root.mkdir(parents=True, exist_ok=True)
        return {
            "required": required,
            "missing": list(required),
            "artifact_base_rel": str(Path("artifacts") / base_rel_path),
            "artifact_base_abs": str(base_dir),
            "artifact_root_rel": str(Path("artifacts") / base_rel_path / run_id),
            "artifact_root_abs": str(artifact_root),
            "files": {},
        }

    def _refresh_manifest(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        artifact_root = Path(str(manifest.get("artifact_root_abs") or ""))
        required = [str(name).strip() for name in list(manifest.get("required") or []) if str(name).strip()]
        files = manifest.get("files")
        if not isinstance(files, dict):
            files = {}
        out_files: Dict[str, Any] = {}
        missing = []
        ordered_names = list(required)
        for extra_name in list(files.keys()):
            if extra_name not in ordered_names:
                ordered_names.append(extra_name)
        for name in ordered_names:
            safe_name = self._sanitize_artifact_name(name)
            path = artifact_root / safe_name
            exists = path.exists() and path.is_file()
            if name in required and not exists:
                missing.append(name)
            record = files.get(name)
            if not isinstance(record, dict):
                record = {}
            out_files[name] = {
                "name": name,
                "path": str(path),
                "exists": bool(exists),
                "size_bytes": int(path.stat().st_size) if exists else int(record.get("size_bytes") or 0),
                "updated_at": str(record.get("updated_at") or ""),
                "metadata": record.get("metadata") if isinstance(record.get("metadata"), dict) else {},
            }
            if exists:
                out_files[name]["updated_at"] = _utc_now_iso()
        manifest["files"] = out_files
        manifest["missing"] = missing
        return manifest

    def _hydrate_run(self, run: Dict[str, Any]) -> Dict[str, Any]:
        hydrated = dict(run)
        manifest = hydrated.get("artifact_manifest")
        if not isinstance(manifest, dict):
            manifest = {}
        hydrated["artifact_manifest"] = self._refresh_manifest(manifest)
        created_at = _parse_iso_ts(str(hydrated.get("created_at") or ""))
        updated_at = _parse_iso_ts(str(hydrated.get("updated_at") or ""))
        runtime_ms = 0
        if created_at is not None and updated_at is not None:
            runtime_ms = max(0, int((updated_at - created_at).total_seconds() * 1000))
        refreshed_manifest = hydrated["artifact_manifest"]
        required = list(refreshed_manifest.get("required") or [])
        missing = list(refreshed_manifest.get("missing") or [])
        hydrated["metrics"] = {
            "runtime_ms": runtime_ms,
            "required_artifact_count": len(required),
            "artifact_missing_count": len(missing),
            "artifact_present_count": max(0, len(required) - len(missing)),
            "event_count": len(list(hydrated.get("events") or [])),
            "run_status": str(hydrated.get("status") or ""),
            "workflow_family": str(hydrated.get("workflow_family") or ""),
        }
        return hydrated

    def create_run(
        self,
        *,
        task_id: str,
        workflow_family: str,
        contract: Dict[str, Any],
        playground: Dict[str, Any],
        task_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        data = self._load()
        run_id = f"lg_run_{uuid.uuid4().hex[:10]}"
        now = _utc_now_iso()
        manifest = self._artifact_layout(task_id, run_id, contract)
        run = {
            "run_id": run_id,
            "task_id": str(task_id),
            "workflow_family": str(workflow_family),
            "status": "queued",
            "current_step": "recon",
            "active_role": "coder",
            "model_id": "",
            "failure_reason": "",
            "playground_id": str(playground.get("playground_id") or ""),
            "branch_name": str(playground.get("branch_name") or ""),
            "worktree_path": str(playground.get("worktree_path") or ""),
            "artifact_manifest": manifest,
            "contract_version": str(contract.get("version") or "v1"),
            "task_snapshot": dict(task_snapshot or {}),
            "created_at": now,
            "updated_at": now,
            "events": [
                {
                    "ts": now,
                    "event": "created",
                    "status": "queued",
                    "step": "recon",
                    "role": "coder",
                }
            ],
        }
        data["runs"][run_id] = run
        data["task_latest"][str(task_id)] = run_id
        self._save(data)
        return self._hydrate_run(run)

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        run = data.get("runs", {}).get(str(run_id))
        if not isinstance(run, dict):
            return None
        return self._hydrate_run(dict(run))

    def get_latest_for_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        run_id = str(data.get("task_latest", {}).get(str(task_id)) or "")
        if not run_id:
            return None
        run = data.get("runs", {}).get(run_id)
        if not isinstance(run, dict):
            return None
        return self._hydrate_run(dict(run))

    def update_run(self, run_id: str, **updates: Any) -> Optional[Dict[str, Any]]:
        data = self._load()
        run = data.get("runs", {}).get(str(run_id))
        if not isinstance(run, dict):
            return None

        event = {
            "ts": _utc_now_iso(),
            "event": "updated",
            "status": str(updates.get("status") or run.get("status") or ""),
            "step": str(updates.get("current_step") or run.get("current_step") or ""),
            "role": str(updates.get("active_role") or run.get("active_role") or ""),
        }
        if "model_id" in updates:
            event["model_id"] = str(updates.get("model_id") or "")
        if "failure_reason" in updates and updates.get("failure_reason"):
            event["failure_reason"] = str(updates.get("failure_reason") or "")

        for key in ["status", "current_step", "active_role", "model_id", "failure_reason"]:
            if key in updates and updates[key] is not None:
                run[key] = updates[key]
        if isinstance(updates.get("metadata"), dict):
            meta = run.get("metadata")
            if not isinstance(meta, dict):
                meta = {}
            meta.update(updates["metadata"])
            run["metadata"] = meta
        events = run.get("events")
        if not isinstance(events, list):
            events = []
        events.append(event)
        run["events"] = events[-100:]
        run["updated_at"] = _utc_now_iso()
        run["artifact_manifest"] = self._refresh_manifest(run.get("artifact_manifest") or {})
        data["runs"][str(run_id)] = run
        self._save(data)
        return self._hydrate_run(dict(run))

    def write_artifact(
        self,
        run_id: str,
        artifact_name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        data = self._load()
        run = data.get("runs", {}).get(str(run_id))
        if not isinstance(run, dict):
            return None
        manifest = run.get("artifact_manifest") or {}
        manifest = self._refresh_manifest(manifest)
        artifact_root = Path(str(manifest.get("artifact_root_abs") or ""))
        safe_name = self._sanitize_artifact_name(artifact_name)
        path = artifact_root / safe_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content or ""), encoding="utf-8")
        files = manifest.get("files")
        if not isinstance(files, dict):
            files = {}
        files[safe_name] = {
            "name": safe_name,
            "path": str(path),
            "exists": True,
            "size_bytes": path.stat().st_size,
            "updated_at": _utc_now_iso(),
            "metadata": dict(metadata or {}),
        }
        manifest["files"] = files
        manifest = self._refresh_manifest(manifest)
        run["artifact_manifest"] = manifest
        run["updated_at"] = _utc_now_iso()
        data["runs"][str(run_id)] = run
        self._save(data)
        return dict(manifest["files"][safe_name])

    def validate_required_artifacts(self, run_id: str) -> Optional[Dict[str, Any]]:
        data = self._load()
        run = data.get("runs", {}).get(str(run_id))
        if not isinstance(run, dict):
            return None
        manifest = self._refresh_manifest(run.get("artifact_manifest") or {})
        run["artifact_manifest"] = manifest
        run["updated_at"] = _utc_now_iso()
        data["runs"][str(run_id)] = run
        self._save(data)
        return manifest

    def list_runs(
        self,
        *,
        workflow_family: str = "",
        task_id: str = "",
        limit: int = 20,
    ) -> list[Dict[str, Any]]:
        data = self._load()
        rows = []
        for raw in list(data.get("runs", {}).values()):
            if not isinstance(raw, dict):
                continue
            if workflow_family and str(raw.get("workflow_family") or "") != str(workflow_family):
                continue
            if task_id and str(raw.get("task_id") or "") != str(task_id):
                continue
            rows.append(self._hydrate_run(dict(raw)))
        rows.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
        return rows[: max(1, int(limit or 20))]

    def summarize_runs(
        self,
        *,
        workflow_family: str = "",
        task_id: str = "",
        limit: int = 20,
    ) -> Dict[str, Any]:
        rows = self.list_runs(workflow_family=workflow_family, task_id=task_id, limit=limit)
        status_counts: Dict[str, int] = {}
        model_counts: Dict[str, int] = {}
        runtime_total = 0
        missing_total = 0
        required_total = 0
        completed = 0
        for row in rows:
            metrics = dict(row.get("metrics") or {})
            status = str(metrics.get("run_status") or row.get("status") or "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            model_id = str(row.get("model_id") or "").strip()
            if model_id:
                model_counts[model_id] = model_counts.get(model_id, 0) + 1
            runtime_total += int(metrics.get("runtime_ms") or 0)
            missing_total += int(metrics.get("artifact_missing_count") or 0)
            required_total += int(metrics.get("required_artifact_count") or 0)
            if status == "done":
                completed += 1

        count = len(rows)
        success_rate = round((completed / count) * 100.0, 2) if count else 0.0
        return {
            "count": count,
            "workflow_family": str(workflow_family or ""),
            "task_id": str(task_id or ""),
            "status_counts": status_counts,
            "model_counts": model_counts,
            "avg_runtime_ms": int(runtime_total / count) if count else 0,
            "avg_artifact_missing_count": round(missing_total / count, 2) if count else 0.0,
            "avg_required_artifact_count": round(required_total / count, 2) if count else 0.0,
            "success_rate": success_rate,
            "recent_runs": rows,
        }


_registry_singleton: Optional[LocalguysRunRegistry] = None


def get_localguys_run_registry() -> LocalguysRunRegistry:
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = LocalguysRunRegistry()
    return _registry_singleton
