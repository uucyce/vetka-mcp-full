"""
MARKER_177.ROADMAP_TASKBOARD_SYNC.V1

Helpers for automatic roadmap <-> TaskBoard synchronization and task context packets.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from src.services.roadmap_generator import RoadmapDAG


ROADMAP_BINDING_FIELDS = {
    "roadmap_id",
    "roadmap_node_id",
    "roadmap_lane",
    "roadmap_title",
}


def _normalize_str_list(value: Any) -> List[str]:
    return [str(item).strip() for item in list(value or []) if str(item).strip()]


def apply_task_profile_defaults(payload: Dict[str, Any]) -> Dict[str, Any]:
    row = deepcopy(payload or {})
    profile = str(row.pop("profile", "") or "").strip().lower()
    if not profile:
        return row
    if profile != "p6":
        raise ValueError(f"Unsupported task profile: {profile}")

    lane = str(row.get("project_lane") or row.get("project_id") or row.get("roadmap_lane") or "").strip()
    docs = _normalize_str_list(row.get("architecture_docs"))
    tests = _normalize_str_list(row.get("closure_tests"))
    allowed_paths = _normalize_str_list(row.get("allowed_paths"))
    closure_files = _normalize_str_list(row.get("closure_files")) or allowed_paths
    tags = _normalize_str_list(row.get("tags"))
    completion_contract = _normalize_str_list(row.get("completion_contract"))

    missing: List[str] = []
    if not lane:
        missing.append("project_lane")
    if not docs:
        missing.append("architecture_docs")
    if not tests:
        missing.append("closure_tests")
    if missing:
        raise ValueError(f"p6 profile requires: {', '.join(missing)}")

    if "p6" not in tags:
        tags.append("p6")
    if "closure_proof" not in tags:
        tags.append("closure_proof")
    for rule in ["result_summary required", "closure proof required"]:
        if rule not in completion_contract:
            completion_contract.append(rule)

    row["project_lane"] = row.get("project_lane") or lane
    row["phase_type"] = str(row.get("phase_type") or "test").strip() or "test"
    row["architecture_docs"] = docs
    row["closure_tests"] = tests
    row["closure_files"] = closure_files
    row["require_closure_proof"] = True
    row["protocol_version"] = str(row.get("protocol_version") or "multitask_mcp_v1").strip() or "multitask_mcp_v1"
    row["task_origin"] = str(row.get("task_origin") or "p6_profile").strip() or "p6_profile"
    row["workflow_selection_origin"] = str(row.get("workflow_selection_origin") or "p6_profile").strip() or "p6_profile"
    row["completion_contract"] = completion_contract
    row["depends_on_docs"] = _normalize_str_list(row.get("depends_on_docs")) or docs
    row["tags"] = tags
    return row


def _node_id(node: Dict[str, Any]) -> str:
    return str(node.get("id") or node.get("node_id") or "").strip()


def _node_label(node: Dict[str, Any]) -> str:
    return str(node.get("label") or node.get("title") or _node_id(node)).strip()


def _derive_packet_gaps(*, docs: List[str], recon_docs: List[str], closure_files: List[str], closure_tests: List[str]) -> List[str]:
    gaps: List[str] = []
    if not docs and not recon_docs:
        gaps.append("missing_docs")
    if not closure_files:
        gaps.append("missing_code_scope")
    if not closure_tests:
        gaps.append("missing_tests")
    return gaps


def _build_localguys_compliance(
    *,
    workflow_contract: Optional[Dict[str, Any]] = None,
    localguys_run: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    contract = dict(workflow_contract or {})
    run = dict(localguys_run or {})
    workflow_family = str(contract.get("workflow_family") or run.get("workflow_family") or "").strip()
    if workflow_family and not workflow_family.endswith("_localguys"):
        return {}
    sandbox_policy = dict(contract.get("sandbox_policy") or {})
    write_opt_ins = dict(contract.get("write_opt_ins") or {})
    stage_tool_policy = dict(contract.get("stage_tool_policy") or {})
    telemetry = dict(run.get("telemetry") or {})
    active_step = str(run.get("current_step") or "").strip()
    return {
        "workflow_family": workflow_family,
        "execution_mode": str(contract.get("execution_mode") or "").strip(),
        "sandbox_mode": str(sandbox_policy.get("mode") or "").strip(),
        "requires_playground": bool(sandbox_policy.get("requires_playground")),
        "write_opt_ins": write_opt_ins,
        "verification_target": str(contract.get("verification_target") or telemetry.get("verification_target") or "").strip(),
        "max_turns": int(contract.get("max_turns") or 0),
        "idle_nudge_template": str(contract.get("idle_nudge_template") or "").strip(),
        "stage_tool_policy": stage_tool_policy,
        "active_step": active_step,
        "active_step_allowed_tools": list(stage_tool_policy.get(active_step) or []),
        "telemetry": {
            "recommended_tools": list(telemetry.get("recommended_tools") or []),
            "filtered_tool_schemas": list(telemetry.get("filtered_tool_schemas") or []),
            "idle_turn_count": int(telemetry.get("idle_turn_count") or 0),
            "verification_passed": bool(telemetry.get("verification_passed")),
        },
    }


def _recent_task_artifacts(task: Dict[str, Any]) -> Dict[str, Any]:
    closure_proof = task.get("closure_proof")
    closure_subtask = task.get("closure_subtask")
    artifacts = {
        "closure_proof": closure_proof,
        "closure_subtask": closure_subtask,
    }
    if isinstance(closure_proof, dict):
        artifacts["commit_hash"] = str(closure_proof.get("commit_hash") or "").strip()
        artifacts["tests"] = list(closure_proof.get("tests") or [])
    return artifacts


def _find_roadmap_node(roadmap_binding: Dict[str, Any]) -> Dict[str, Any]:
    roadmap_node_id = str(roadmap_binding.get("roadmap_node_id") or "").strip()
    if not roadmap_node_id:
        return {}
    dag = RoadmapDAG.load()
    if dag is None:
        return {}
    for node in list(dag.nodes or []):
        if isinstance(node, dict) and _node_id(node) == roadmap_node_id:
            return deepcopy(node)
    return {}


def generate_task_payloads_from_roadmap_node(node: Dict[str, Any], *, roadmap_id: str = "") -> List[Dict[str, Any]]:
    node_id = _node_id(node)
    title = _node_label(node) or "Roadmap task"
    lane = str(node.get("layer") or node.get("lane") or "core").strip() or "core"
    description = str(node.get("description") or "").strip()
    file_patterns = [str(row).strip() for row in list(node.get("file_patterns") or node.get("files") or []) if str(row).strip()]
    docs = [str(row).strip() for row in list(node.get("docs") or []) if str(row).strip()]

    payload = {
        "title": f"Implement: {title}"[:100],
        "description": description or title,
        "priority": 2,
        "phase_type": "build" if lane not in {"docs", "test"} else ("research" if lane == "docs" else "fix"),
        "tags": ["roadmap", lane, node_id],
        "module": title,
        "primary_node_id": node_id,
        "affected_nodes": [node_id],
        "roadmap_id": str(roadmap_id or "").strip(),
        "roadmap_node_id": node_id,
        "roadmap_lane": lane,
        "roadmap_title": title,
        "architecture_docs": docs,
        "closure_files": file_patterns,
        "task_origin": "roadmap_sync",
        "workflow_selection_origin": "roadmap_sync",
    }
    return [payload]


def build_task_context_packet(
    task: Dict[str, Any],
    *,
    workflow_binding: Optional[Dict[str, Any]] = None,
    workflow_contract: Optional[Dict[str, Any]] = None,
    task_history: Optional[List[Dict[str, Any]]] = None,
    localguys_run: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    row = deepcopy(task)
    roadmap_binding = {
        key: row.get(key)
        for key in ["roadmap_id", "roadmap_node_id", "roadmap_lane", "roadmap_title"]
        if row.get(key) not in (None, "", [])
    }
    docs = [str(item).strip() for item in list(row.get("architecture_docs") or []) if str(item).strip()]
    recon_docs = [str(item).strip() for item in list(row.get("recon_docs") or []) if str(item).strip()]
    closure_files = [str(item).strip() for item in list(row.get("closure_files") or []) if str(item).strip()]
    closure_tests = [str(item).strip() for item in list(row.get("closure_tests") or []) if str(item).strip()]
    roadmap_node = _find_roadmap_node(roadmap_binding)
    if roadmap_node:
        for path in list(roadmap_node.get("docs") or []):
            text = str(path or "").strip()
            if text and text not in docs:
                docs.append(text)
        for path in list(roadmap_node.get("file_patterns") or roadmap_node.get("files") or []):
            text = str(path or "").strip()
            if text and text not in closure_files:
                closure_files.append(text)
    history_rows = list(task_history or list(row.get("status_history") or []))
    recent_runs = []
    if isinstance(localguys_run, dict) and localguys_run:
        recent_runs.append(deepcopy(localguys_run))
    gaps = _derive_packet_gaps(
        docs=docs,
        recon_docs=recon_docs,
        closure_files=closure_files,
        closure_tests=closure_tests,
    )
    return {
        "task": row,
        "workflow_binding": dict(workflow_binding or {}),
        "workflow_contract": dict(workflow_contract or {}),
        "localguys_compliance": _build_localguys_compliance(
            workflow_contract=workflow_contract,
            localguys_run=localguys_run,
        ),
        "roadmap_binding": roadmap_binding,
        "governance": {
            "ownership_scope": str(row.get("ownership_scope") or "").strip(),
            "allowed_paths": [str(item).strip() for item in list(row.get("allowed_paths") or []) if str(item).strip()],
            "blocked_paths": [str(item).strip() for item in list(row.get("blocked_paths") or []) if str(item).strip()],
            "forbidden_scopes": [str(item).strip() for item in list(row.get("forbidden_scopes") or []) if str(item).strip()],
            "owner_agent": str(row.get("owner_agent") or "").strip(),
            "verification_agent": str(row.get("verification_agent") or "").strip(),
            "touch_policy": str(row.get("touch_policy") or "").strip(),
            "overlap_risk": str(row.get("overlap_risk") or "").strip(),
            "completion_contract": [str(item).strip() for item in list(row.get("completion_contract") or []) if str(item).strip()],
            "depends_on_docs": [str(item).strip() for item in list(row.get("depends_on_docs") or []) if str(item).strip()],
            "worktree_hint": str(row.get("worktree_hint") or "").strip(),
        },
        "roadmap_node": roadmap_node,
        "docs": {
            "architecture_docs": docs,
            "recon_docs": recon_docs,
        },
        "code_scope": {
            "primary_node_id": row.get("primary_node_id"),
            "affected_nodes": list(row.get("affected_nodes") or []),
            "closure_files": closure_files,
        },
        "tests": {
            "closure_tests": closure_tests,
            "require_closure_proof": bool(row.get("require_closure_proof")),
        },
        "artifacts": {
            **_recent_task_artifacts(row),
            "recent_localguys_runs": recent_runs,
        },
        "history": history_rows[-10:],
        "gaps": gaps,
    }


def build_role_context_slice(
    packet: Dict[str, Any],
    role: str,
    *,
    overlays: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    row = deepcopy(packet or {})
    role_key = str(role or "").strip().lower()
    base = {
        "task": dict(row.get("task") or {}),
        "workflow_binding": dict(row.get("workflow_binding") or {}),
        "workflow_contract": dict(row.get("workflow_contract") or {}),
        "localguys_compliance": dict(row.get("localguys_compliance") or {}),
        "governance": dict(row.get("governance") or {}),
        "gaps": list(row.get("gaps") or []),
    }
    docs = dict(row.get("docs") or {})
    code_scope = dict(row.get("code_scope") or {})
    tests = dict(row.get("tests") or {})
    artifacts = dict(row.get("artifacts") or {})
    history = list(row.get("history") or [])
    roadmap_binding = dict(row.get("roadmap_binding") or {})
    overlay_row = dict(row.get("ui_context") or {})
    overlay_row.update(dict(overlays or {}))

    def _role_ui_context(*, include_viewport: bool = False, include_pins: bool = False, include_myco_focus: bool = False) -> Dict[str, Any]:
        ui_context: Dict[str, Any] = {}
        viewport_summary = str(overlay_row.get("viewport_summary") or "").strip()
        pinned_summary = str(overlay_row.get("pinned_summary") or "").strip()
        myco_focus = dict(overlay_row.get("myco_focus") or {})
        if include_viewport and viewport_summary:
            ui_context["viewport_summary"] = viewport_summary
        if include_pins and pinned_summary:
            ui_context["pinned_summary"] = pinned_summary
        if include_myco_focus and myco_focus:
            ui_context["myco_focus"] = myco_focus
        return ui_context

    if role_key == "architect":
        base["roadmap_binding"] = roadmap_binding
        base["docs"] = docs
        base["code_scope"] = code_scope
        base["tests"] = tests
        base["history"] = history[-5:]
        ui_context = _role_ui_context(include_viewport=True, include_pins=True)
        if ui_context:
            base["ui_context"] = ui_context
        return base
    if role_key in {"coder", "dev"}:
        base["code_scope"] = code_scope
        base["tests"] = tests
        base["artifacts"] = artifacts
        ui_context = _role_ui_context(include_pins=True)
        if ui_context:
            base["ui_context"] = ui_context
        return base
    if role_key in {"verifier", "eval", "qa"}:
        base["tests"] = tests
        base["artifacts"] = artifacts
        return base
    if role_key in {"scout", "researcher"}:
        base["roadmap_binding"] = roadmap_binding
        base["docs"] = docs
        base["code_scope"] = code_scope
        return base
    if role_key == "myco":
        base["roadmap_binding"] = roadmap_binding
        base["docs"] = {
            "architecture_docs": list(docs.get("architecture_docs") or [])[:3],
            "recon_docs": list(docs.get("recon_docs") or [])[:3],
        }
        ui_context = _role_ui_context(include_viewport=True, include_pins=True, include_myco_focus=True)
        if ui_context:
            base["ui_context"] = ui_context
        return base
    return base


def sync_task_status_to_roadmap(
    task: Dict[str, Any],
    *,
    tasks: Optional[List[Dict[str, Any]]] = None,
    roadmap_path: Optional[str] = None,
) -> bool:
    roadmap_node_id = str(task.get("roadmap_node_id") or "").strip()
    if not roadmap_node_id:
        return False

    dag = RoadmapDAG.load(path=roadmap_path)
    if dag is None:
        return False

    target = None
    for node in list(dag.nodes or []):
        if isinstance(node, dict) and _node_id(node) == roadmap_node_id:
            target = node
            break
    if target is None:
        return False

    related_tasks = []
    for row in list(tasks or [task]):
        if not isinstance(row, dict):
            continue
        if str(row.get("roadmap_node_id") or "").strip() == roadmap_node_id:
            related_tasks.append(row)
    if not related_tasks:
        related_tasks = [task]

    statuses = [str(row.get("status") or "").strip().lower() for row in related_tasks]
    if statuses and all(status == "done" for status in statuses):
        roadmap_status = "completed"
    elif any(status in {"running", "claimed", "queued"} for status in statuses):
        roadmap_status = "active"
    elif any(status in {"failed", "cancelled", "hold"} for status in statuses):
        roadmap_status = "active"
    else:
        roadmap_status = "pending"

    completed_count = len([status for status in statuses if status == "done"])
    target["status"] = roadmap_status
    target["task_sync_status"] = str(task.get("status") or "").strip().lower()
    target["task_sync_task_id"] = str(task.get("id") or "")
    target["task_sync_result_status"] = task.get("result_status")
    target["task_sync_counts"] = {
        "total": len(related_tasks),
        "completed": completed_count,
        "active": len([status for status in statuses if status in {"running", "claimed", "queued"}]),
        "failed": len([status for status in statuses if status == "failed"]),
    }
    target["task_sync_progress"] = round((completed_count / len(related_tasks)) * 100.0, 2) if related_tasks else 0.0
    return bool(dag.save(path=roadmap_path))
