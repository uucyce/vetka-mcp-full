"""
MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.V1

Persistent DAG version registry for MCC debug/selection workflow.
Stores multiple DAG variants per project with primary-version pointer.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.services.project_config import DATA_DIR

DAG_VERSIONS_PATH = os.path.join(DATA_DIR, "mcc_dag_versions.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_store() -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "updated_at": _utc_now_iso(),
        "projects": {},
    }


def _load_store() -> Dict[str, Any]:
    if not os.path.exists(DAG_VERSIONS_PATH):
        return _empty_store()
    try:
        with open(DAG_VERSIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _empty_store()
        if "projects" not in data or not isinstance(data.get("projects"), dict):
            data["projects"] = {}
        if "schema_version" not in data:
            data["schema_version"] = 1
        return data
    except Exception:
        return _empty_store()


def _save_store(store: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(DAG_VERSIONS_PATH), exist_ok=True)
    store["updated_at"] = _utc_now_iso()
    with open(DAG_VERSIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)


def _ensure_project_bucket(store: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    projects = store.setdefault("projects", {})
    bucket = projects.setdefault(
        project_id,
        {
            "primary_version_id": "",
            "versions": [],
        },
    )
    if not isinstance(bucket.get("versions"), list):
        bucket["versions"] = []
    if "primary_version_id" not in bucket:
        bucket["primary_version_id"] = ""
    return bucket


def _version_summary(v: Dict[str, Any]) -> Dict[str, Any]:
    build_meta = v.get("build_meta") or {}
    verifier = build_meta.get("verifier") or {}
    trm_meta = build_meta.get("trm_meta") or {}
    trm_variant = build_meta.get("trm_variant") or {}
    graph_source = str(build_meta.get("graph_source") or "")
    if not graph_source:
        graph_source = "trm_refined" if bool(trm_meta.get("applied")) else "baseline"
    return {
        "version_id": str(v.get("version_id", "")),
        "name": str(v.get("name", "")),
        "created_at": str(v.get("created_at", "")),
        "author": str(v.get("author", "architect")),
        "source": str(v.get("source", "manual")),
        "is_primary": bool(v.get("is_primary", False)),
        "node_count": int(v.get("node_count", 0)),
        "edge_count": int(v.get("edge_count", 0)),
        "decision": str(verifier.get("decision", "")),
        "graph_source": graph_source,
        "trm_status": str(trm_meta.get("status") or ""),
        "trm_profile": str(trm_meta.get("profile") or trm_variant.get("profile") or ""),
        "markers": list(v.get("markers") or []),
    }


def create_dag_version(
    project_id: str,
    dag_payload: Dict[str, Any],
    *,
    name: str = "",
    author: str = "architect",
    source: str = "manual",
    build_meta: Optional[Dict[str, Any]] = None,
    markers: Optional[List[str]] = None,
    set_primary: bool = False,
) -> Dict[str, Any]:
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.CREATE.V1
    Create and persist DAG version snapshot for project.
    """
    # MARKER_161.TRM.VERSION_META.V1:
    # Phase-161 hook: persist TRM policy/refinement metadata per DAG snapshot.
    store = _load_store()
    bucket = _ensure_project_bucket(store, project_id)
    versions: List[Dict[str, Any]] = bucket["versions"]

    version_id = f"dagv_{uuid.uuid4().hex[:12]}"
    created_at = _utc_now_iso()
    design_graph = (dag_payload or {}).get("design_graph") or {}
    nodes = design_graph.get("nodes") if isinstance(design_graph, dict) else []
    edges = design_graph.get("edges") if isinstance(design_graph, dict) else []
    build_meta_safe = dict(build_meta or {})
    if "verifier" not in build_meta_safe and isinstance(dag_payload, dict):
        build_meta_safe["verifier"] = dag_payload.get("verifier") or {}
    if "spectral" not in build_meta_safe:
        verifier = build_meta_safe.get("verifier") or {}
        if isinstance(verifier, dict):
            build_meta_safe["spectral"] = verifier.get("spectral") or {}
    if "overlay_stats" not in build_meta_safe and isinstance(dag_payload, dict):
        overlay = dag_payload.get("predictive_overlay") or {}
        build_meta_safe["overlay_stats"] = (overlay.get("stats") or {}) if isinstance(overlay, dict) else {}

    record: Dict[str, Any] = {
        "version_id": version_id,
        "name": str(name or f"DAG Version {len(versions) + 1}"),
        "created_at": created_at,
        "author": str(author or "architect"),
        "source": str(source or "manual"),
        "is_primary": False,
        "node_count": len(nodes) if isinstance(nodes, list) else 0,
        "edge_count": len(edges) if isinstance(edges, list) else 0,
        "build_meta": build_meta_safe,
        "markers": list(markers or []),
        "dag_payload": dag_payload or {},
    }
    versions.append(record)

    if set_primary or not bucket.get("primary_version_id"):
        set_primary_version(project_id, version_id, store=store, persist=False)

    _save_store(store)
    return record


def list_dag_versions(project_id: str) -> Dict[str, Any]:
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.LIST.V1
    List summaries + primary pointer for project DAG versions.
    """
    store = _load_store()
    bucket = _ensure_project_bucket(store, project_id)
    versions: List[Dict[str, Any]] = bucket["versions"]
    summaries = [_version_summary(v) for v in versions]
    summaries.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    return {
        "project_id": project_id,
        "primary_version_id": str(bucket.get("primary_version_id", "")),
        "versions": summaries,
        "count": len(summaries),
    }


def get_dag_version(project_id: str, version_id: str) -> Optional[Dict[str, Any]]:
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.GET.V1
    Get full stored DAG version payload by ID.
    """
    store = _load_store()
    bucket = _ensure_project_bucket(store, project_id)
    versions: List[Dict[str, Any]] = bucket["versions"]
    for v in versions:
        if str(v.get("version_id", "")) == version_id:
            return v
    return None


def set_primary_version(
    project_id: str,
    version_id: str,
    *,
    store: Optional[Dict[str, Any]] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.PRIMARY.V1
    Set selected DAG version as primary for project.
    """
    local_store = store or _load_store()
    bucket = _ensure_project_bucket(local_store, project_id)
    versions: List[Dict[str, Any]] = bucket["versions"]
    found = False
    for v in versions:
        is_target = str(v.get("version_id", "")) == version_id
        v["is_primary"] = bool(is_target)
        if is_target:
            found = True
    if not found:
        raise ValueError(f"version_id not found: {version_id}")
    bucket["primary_version_id"] = version_id
    if persist:
        _save_store(local_store)
    return {
        "project_id": project_id,
        "primary_version_id": version_id,
        "count": len(versions),
    }
