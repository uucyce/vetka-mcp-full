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
PROJECTS_DIR = os.path.join(DATA_DIR, "mcc_projects")


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
    workspace_path = str(config.resolved_workspace_path() or "").strip()
    context_scope_path = str(config.resolved_context_scope_path() or "").strip()
    project_kind = str(getattr(config, "project_kind", "user") or "user").strip().lower() or "user"
    return {
        "project_id": str(config.project_id),
        "display_name": str(getattr(config, "display_name", "") or ""),
        "project_kind": project_kind,
        "tab_visibility": "visible" if project_kind == "user" else "hidden",
        "source_type": str(config.source_type),
        "execution_mode": str(getattr(config, "execution_mode", "playground") or "playground"),
        "source_path": str(config.source_path),
        "sandbox_path": str(config.sandbox_path),
        "workspace_path": workspace_path,
        "context_scope_path": context_scope_path,
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
            execution_mode=str(record.get("execution_mode", "playground") or "playground"),
            sandbox_path=str(record.get("sandbox_path", "")),
            quota_gb=int(record.get("quota_gb", 10)),
            created_at=str(record.get("created_at", "")),
            qdrant_collection=str(record.get("qdrant_collection", "")),
            display_name=str(record.get("display_name", "")),
            project_kind=str(record.get("project_kind", "user") or "user"),
        )
    except Exception:
        return None


def _safe_session_segment(value: str, fallback: str) -> str:
    safe = str(value or "").strip()
    safe = "".join(ch for ch in safe if ch.isalnum() or ch in ("-", "_", "."))
    return safe or fallback


def _project_dir(project_id: str) -> str:
    project_safe = _safe_session_segment(project_id, "default_project")
    return os.path.join(PROJECTS_DIR, project_safe)


def _project_config_path(project_id: str) -> str:
    return os.path.join(_project_dir(project_id), "project_config.json")


def _save_project_snapshot(config: ProjectConfig) -> None:
    config.save(path=_project_config_path(config.project_id))


def _load_snapshot_records() -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not os.path.isdir(PROJECTS_DIR):
        return records
    try:
        for name in sorted(os.listdir(PROJECTS_DIR)):
            cfg_path = os.path.join(PROJECTS_DIR, name, "project_config.json")
            cfg = ProjectConfig.load(path=cfg_path)
            if cfg is None or not str(cfg.project_id or "").strip():
                continue
            records.append(_project_to_record(cfg))
    except Exception:
        return records
    return records


def _merge_record_maps(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for group in groups:
        for row in group or []:
            if not isinstance(row, dict):
                continue
            project_id = str(row.get("project_id", "")).strip()
            if not project_id:
                continue
            base = dict(merged.get(project_id) or {})
            base.update(dict(row))
            if not str(base.get("display_name", "")).strip():
                sandbox = str(base.get("sandbox_path", "")).replace("\\", "/").rstrip("/")
                source = str(base.get("workspace_path") or base.get("source_path") or "").replace("\\", "/").rstrip("/")
                base["display_name"] = (
                    (sandbox.split("/")[-1] if sandbox else "")
                    or (source.split("/")[-1] if source else "")
                    or project_id
                )
            merged[project_id] = base
    return list(merged.values())


def _session_path_for_project(project_id: str, window_session_id: str = "") -> str:
    project_safe = _safe_session_segment(project_id, "default_project")
    window_safe = _safe_session_segment(window_session_id, "")
    suffix = f".{window_safe}" if window_safe else ""
    return os.path.join(SESSIONS_DIR, f"{project_safe}{suffix}.session_state.json")


def ensure_registry_bootstrap() -> Dict[str, Any]:
    """
    MARKER_161.7.MULTIPROJECT.REGISTRY.LEGACY_IMPORT.V1
    Bootstrap registry from legacy single-project files when needed.
    """
    registry = _load_registry()
    changed = False
    projects = registry.get("projects") or []

    legacy = ProjectConfig.load(path=CONFIG_PATH)
    snapshot_records = _load_snapshot_records()

    if legacy is not None and legacy.project_id:
        snapshot_records = _merge_record_maps(snapshot_records, [_project_to_record(legacy)])
        if not str(registry.get("active_project_id", "")).strip():
            registry["active_project_id"] = str(legacy.project_id)
            changed = True
        try:
            _save_project_snapshot(legacy)
        except Exception:
            pass

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

    merged_projects = _merge_record_maps(snapshot_records, list(projects or []))
    if merged_projects != list(projects or []):
        registry["projects"] = merged_projects
        changed = True

    if changed:
        _save_registry(registry)

    return registry


def list_projects(*, include_hidden: bool = False, always_include_project_id: str = "") -> Dict[str, Any]:
    registry = ensure_registry_bootstrap()
    rows = registry.get("projects") or []
    summaries: List[Dict[str, Any]] = []
    active_id = str(registry.get("active_project_id", ""))
    always_include = str(always_include_project_id or "").strip()
    hidden_count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        project_id = str(row.get("project_id", "")).strip()
        project_kind = str(row.get("project_kind", "user") or "user").strip().lower() or "user"
        tab_visibility = str(row.get("tab_visibility", "visible") or "visible").strip().lower() or "visible"
        is_hidden = tab_visibility != "visible" or project_kind != "user"
        if is_hidden and project_id != always_include and not include_hidden:
            hidden_count += 1
            continue
        display_name = str(row.get("display_name", "")).strip()
        if not display_name:
            sandbox = str(row.get("sandbox_path", "")).replace("\\", "/").rstrip("/")
            source = str(row.get("workspace_path") or row.get("source_path") or "").replace("\\", "/").rstrip("/")
            display_name = (
                (sandbox.split("/")[-1] if sandbox else "")
                or (source.split("/")[-1] if source else "")
                or str(row.get("project_id", "project"))
            )
        summaries.append(
            {
                "project_id": project_id,
                "display_name": display_name,
                "project_kind": project_kind,
                "tab_visibility": tab_visibility,
                "source_type": str(row.get("source_type", "")),
                "execution_mode": str(row.get("execution_mode", "playground") or "playground"),
                "source_path": str(row.get("source_path", "")),
                "sandbox_path": str(row.get("sandbox_path", "")),
                "workspace_path": str(row.get("workspace_path", "")),
                "context_scope_path": str(row.get("context_scope_path", "")),
                "quota_gb": int(row.get("quota_gb", 10)),
                "created_at": str(row.get("created_at", "")),
                "last_opened_at": str(row.get("last_opened_at", "")),
            }
        )
    summaries.sort(
        key=lambda row: (
            str(row.get("project_id", "")) == active_id,
            str(row.get("last_opened_at", "")),
            str(row.get("display_name", "")),
        ),
        reverse=True,
    )
    return {
        "active_project_id": active_id,
        "updated_at": str(registry.get("updated_at", "")),
        "projects": summaries,
        "count": len(summaries),
        "hidden_count": hidden_count,
    }


def get_project(project_id: str) -> Optional[ProjectConfig]:
    project_id = str(project_id or "").strip()
    if not project_id:
        return None
    registry = ensure_registry_bootstrap()
    for row in registry.get("projects") or []:
        if str((row or {}).get("project_id", "")) == project_id:
            return _record_to_project(row)
    cfg = ProjectConfig.load(path=_project_config_path(project_id))
    if cfg is not None and cfg.project_id:
        return cfg
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
    try:
        _save_project_snapshot(config)
    except Exception:
        pass
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
    try:
        cfg_path = _project_config_path(project_id)
        if os.path.exists(cfg_path):
            os.remove(cfg_path)
        project_dir = _project_dir(project_id)
        if os.path.isdir(project_dir) and not os.listdir(project_dir):
            os.rmdir(project_dir)
    except Exception:
        pass
    _save_registry(registry)
    return {"active_project_id": str(registry.get("active_project_id", "")), "count": len(kept)}


def load_session_for_project(project_id: str, window_session_id: str = "") -> SessionState:
    path = _session_path_for_project(project_id, window_session_id)
    if os.path.exists(path):
        return SessionState.load(path=path)
    if window_session_id:
        fallback_path = _session_path_for_project(project_id)
        if os.path.exists(fallback_path):
            return SessionState.load(path=fallback_path)
    # Fallback for legacy migration period.
    return SessionState.load(path=SESSION_STATE_PATH)


def save_session_for_project(project_id: str, state: SessionState, window_session_id: str = "") -> bool:
    path = _session_path_for_project(project_id, window_session_id)
    return state.save(path=path)
