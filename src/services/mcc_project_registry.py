"""
MARKER_161.7.MULTIPROJECT.REGISTRY.SERVICE.V1

Lightweight multi-project registry skeleton for MCC.
Keeps backward compatibility with legacy single-project files.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.services.project_config import (
    CONFIG_PATH,
    DATA_DIR,
    SESSION_STATE_PATH,
    ProjectConfig,
    SessionState,
)

REGISTRY_PATH = os.path.join(DATA_DIR, "mcc_projects_registry.json")
SESSIONS_DIR = os.path.join(DATA_DIR, "mcc_sessions")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_registry() -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "updated_at": _utc_now_iso(),
        "active_project_id": "",
        "projects": [],
    }


def _load_registry() -> Dict[str, Any]:
    if not os.path.exists(REGISTRY_PATH):
        return _empty_registry()
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _empty_registry()
        projects = data.get("projects")
        if not isinstance(projects, list):
            data["projects"] = []
        if "active_project_id" not in data:
            data["active_project_id"] = ""
        if "schema_version" not in data:
            data["schema_version"] = 1
        return data
    except Exception:
        return _empty_registry()


def _save_registry(registry: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    registry["updated_at"] = _utc_now_iso()
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def _project_to_record(config: ProjectConfig) -> Dict[str, Any]:
    return {
        "project_id": str(config.project_id),
        "display_name": str(getattr(config, "display_name", "") or ""),
        "source_type": str(config.source_type),
        "source_path": str(config.source_path),
        "sandbox_path": str(config.sandbox_path),
        "quota_gb": int(config.quota_gb),
        "created_at": str(config.created_at),
        "qdrant_collection": str(config.qdrant_collection),
        "last_opened_at": _utc_now_iso(),
    }


def _record_to_project(record: Dict[str, Any]) -> Optional[ProjectConfig]:
    try:
        return ProjectConfig(
            project_id=str(record.get("project_id", "")),
            source_type=str(record.get("source_type", "local")),
            source_path=str(record.get("source_path", "")),
            sandbox_path=str(record.get("sandbox_path", "")),
            quota_gb=int(record.get("quota_gb", 10)),
            created_at=str(record.get("created_at", "")),
            qdrant_collection=str(record.get("qdrant_collection", "")),
            display_name=str(record.get("display_name", "")),
        )
    except Exception:
        return None


def _session_path_for_project(project_id: str) -> str:
    safe = str(project_id or "").strip()
    safe = "".join(ch for ch in safe if ch.isalnum() or ch in ("-", "_", "."))
    if not safe:
        safe = "default_project"
    return os.path.join(SESSIONS_DIR, f"{safe}.session_state.json")


def ensure_registry_bootstrap() -> Dict[str, Any]:
    """
    MARKER_161.7.MULTIPROJECT.REGISTRY.LEGACY_IMPORT.V1
    Bootstrap registry from legacy single-project files when needed.
    """
    registry = _load_registry()
    projects = registry.get("projects") or []
    if isinstance(projects, list) and len(projects) > 0:
        return registry

    legacy = ProjectConfig.load(path=CONFIG_PATH)
    if legacy is None or not legacy.project_id:
        return registry

    record = _project_to_record(legacy)
    registry["projects"] = [record]
    registry["active_project_id"] = str(legacy.project_id)
    _save_registry(registry)

    # Seed per-project session from legacy file if needed.
    try:
        dst = _session_path_for_project(legacy.project_id)
        if os.path.exists(SESSION_STATE_PATH) and not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(SESSION_STATE_PATH, "r", encoding="utf-8") as f:
                payload = json.load(f)
            with open(dst, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return registry


def list_projects() -> Dict[str, Any]:
    registry = ensure_registry_bootstrap()
    rows = registry.get("projects") or []
    summaries: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        display_name = str(row.get("display_name", "")).strip()
        if not display_name:
            sandbox = str(row.get("sandbox_path", "")).replace("\\", "/").rstrip("/")
            source = str(row.get("source_path", "")).replace("\\", "/").rstrip("/")
            display_name = (
                (sandbox.split("/")[-1] if sandbox else "")
                or (source.split("/")[-1] if source else "")
                or str(row.get("project_id", "project"))
            )
        summaries.append(
            {
                "project_id": str(row.get("project_id", "")),
                "display_name": display_name,
                "source_type": str(row.get("source_type", "")),
                "source_path": str(row.get("source_path", "")),
                "sandbox_path": str(row.get("sandbox_path", "")),
                "quota_gb": int(row.get("quota_gb", 10)),
                "created_at": str(row.get("created_at", "")),
                "last_opened_at": str(row.get("last_opened_at", "")),
            }
        )
    return {
        "active_project_id": str(registry.get("active_project_id", "")),
        "projects": summaries,
        "count": len(summaries),
    }


def get_project(project_id: str) -> Optional[ProjectConfig]:
    project_id = str(project_id or "").strip()
    if not project_id:
        return None
    registry = ensure_registry_bootstrap()
    for row in registry.get("projects") or []:
        if str((row or {}).get("project_id", "")) == project_id:
            return _record_to_project(row)
    return None


def get_active_project() -> Optional[ProjectConfig]:
    registry = ensure_registry_bootstrap()
    active_id = str(registry.get("active_project_id", "")).strip()
    if active_id:
        active = get_project(active_id)
        if active is not None:
            return active

    # Fallback to legacy behavior if registry has no active project.
    return ProjectConfig.load(path=CONFIG_PATH)


def upsert_project(config: ProjectConfig, *, set_active: bool = True) -> Dict[str, Any]:
    registry = ensure_registry_bootstrap()
    rows = registry.get("projects") or []
    out: List[Dict[str, Any]] = []
    replaced = False
    for row in rows:
        if str((row or {}).get("project_id", "")) == str(config.project_id):
            out.append(_project_to_record(config))
            replaced = True
        else:
            out.append(dict(row or {}))
    if not replaced:
        out.append(_project_to_record(config))
    registry["projects"] = out
    if set_active:
        registry["active_project_id"] = str(config.project_id)
    _save_registry(registry)
    return {
        "active_project_id": str(registry.get("active_project_id", "")),
        "count": len(out),
    }


def activate_project(project_id: str) -> Dict[str, Any]:
    project_id = str(project_id or "").strip()
    if not project_id:
        raise ValueError("project_id is required")
    registry = ensure_registry_bootstrap()
    rows = registry.get("projects") or []
    found = False
    for row in rows:
        if str((row or {}).get("project_id", "")) == project_id:
            found = True
            row["last_opened_at"] = _utc_now_iso()
            break
    if not found:
        raise ValueError(f"project_id not found: {project_id}")
    registry["active_project_id"] = project_id
    _save_registry(registry)
    return {"active_project_id": project_id, "count": len(rows)}


def remove_project(project_id: str) -> Dict[str, Any]:
    project_id = str(project_id or "").strip()
    if not project_id:
        raise ValueError("project_id is required")
    registry = ensure_registry_bootstrap()
    rows = registry.get("projects") or []
    kept = [dict(r or {}) for r in rows if str((r or {}).get("project_id", "")) != project_id]
    if len(kept) == len(rows):
        raise ValueError(f"project_id not found: {project_id}")
    registry["projects"] = kept
    if str(registry.get("active_project_id", "")) == project_id:
        registry["active_project_id"] = str((kept[0] or {}).get("project_id", "")) if kept else ""
    _save_registry(registry)
    return {"active_project_id": str(registry.get("active_project_id", "")), "count": len(kept)}


def load_session_for_project(project_id: str) -> SessionState:
    path = _session_path_for_project(project_id)
    if os.path.exists(path):
        return SessionState.load(path=path)
    # Fallback for legacy migration period.
    return SessionState.load(path=SESSION_STATE_PATH)


def save_session_for_project(project_id: str, state: SessionState) -> bool:
    path = _session_path_for_project(project_id)
    return state.save(path=path)
