"""
MARKER_153.1B: MCC REST API Routes.
MARKER_153.2B: Sandbox management — status, recreate, delete.
MARKER_153.4F: Roadmap + Workflow + Prefetch endpoints.
MARKER_153.7B: Architect Captain — recommend, accept, reject, progress.

Endpoints for Mycelium Command Center initialization, state persistence,
project setup, sandbox lifecycle, roadmap generation, workflow templates,
architect prefetch, and architect captain recommendations.

@phase 153
@wave 1-7
@status active
"""

import os
import shutil
import asyncio
import time
import tempfile
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.services.project_config import ProjectConfig, SessionState
from src.services.mcc_benchmark_store import get_mcc_benchmark_store
from src.services.mcc_trm_config import resolve_trm_policy
from src.services.mcc_local_run_registry import get_localguys_run_registry

router = APIRouter(prefix="/api/mcc", tags=["MCC"])

# MARKER_155.PERF.SANDBOX_STATUS_TRIGGER_CACHE:
# Avoid expensive sandbox disk scans on every UI poll.
_sandbox_status_cache = {
    "sandbox_path": "",
    "source_mtime": 0.0,
    "ts": 0.0,
    "status": None,
}
_SANDBOX_STATUS_TTL_SEC = 30.0


def _sandbox_source_mtime(path: str) -> float:
    if not path:
        return 0.0
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0.0


def _norm_abs(path: str) -> str:
    return os.path.realpath(
        os.path.abspath(os.path.expanduser(str(path or "").strip()))
    )


def _paths_overlap_or_nested(path_a: str, path_b: str) -> bool:
    """
    MARKER_161.9.MULTIPROJECT.ISOLATION.PATH_GUARD.V1
    True when paths are equal or one contains the other.
    """
    a = _norm_abs(path_a)
    b = _norm_abs(path_b)
    if not a or not b:
        return False
    try:
        common = os.path.commonpath([a, b])
    except Exception:
        return False
    return common == a or common == b


def _find_registry_path_conflict(candidate_path: str) -> tuple[bool, str]:
    """
    MARKER_161.9.MULTIPROJECT.ISOLATION.REGISTRY_GUARD.V1
    Ensure a new workspace path does not overlap with any existing project scope.
    """
    candidate = _norm_abs(candidate_path)
    if not candidate:
        return False, ""
    try:
        from src.services.mcc_project_registry import list_projects as _list_projects

        listing = _list_projects()
        for row in list(listing.get("projects") or []):
            pid = str(row.get("project_id") or "").strip()
            pname = str(row.get("display_name") or pid or "project").strip()
            existing_sandbox = str(row.get("sandbox_path") or "").strip()
            existing_source = str(row.get("source_path") or "").strip()
            existing_workspace = str(row.get("workspace_path") or "").strip()
            existing_scope = str(row.get("context_scope_path") or "").strip()
            for existing in (
                existing_sandbox,
                existing_workspace,
                existing_scope,
                existing_source,
            ):
                if not existing:
                    continue
                if _paths_overlap_or_nested(candidate, existing):
                    return (
                        True,
                        f"path overlaps with existing project '{pname}' ({pid})",
                    )
    except Exception:
        return False, ""
    return False, ""


async def _get_sandbox_status_cached(config: "ProjectConfig") -> dict:
    now = time.monotonic()
    source_mtime = _sandbox_source_mtime(config.sandbox_path)
    cached_status = _sandbox_status_cache.get("status")
    if (
        cached_status is not None
        and _sandbox_status_cache.get("sandbox_path") == config.sandbox_path
        and float(_sandbox_status_cache.get("source_mtime", 0.0)) == float(source_mtime)
        and (now - float(_sandbox_status_cache.get("ts", 0.0)))
        <= _SANDBOX_STATUS_TTL_SEC
    ):
        return cached_status

    status = await asyncio.to_thread(config.get_sandbox_status)
    _sandbox_status_cache["sandbox_path"] = config.sandbox_path
    _sandbox_status_cache["source_mtime"] = source_mtime
    _sandbox_status_cache["ts"] = time.monotonic()
    _sandbox_status_cache["status"] = status
    return status


def _load_active_project_config() -> Optional["ProjectConfig"]:
    # MARKER_161.7.MULTIPROJECT.API.ACTIVE_PROJECT_RESOLVE.V1:
    # Resolve active project from registry with legacy fallback.
    try:
        from src.services.mcc_project_registry import get_active_project

        cfg = get_active_project()
        if cfg is not None:
            return cfg
    except Exception:
        pass
    return ProjectConfig.load()


def _resolve_project_config(project_id: str = "") -> Optional["ProjectConfig"]:
    requested = str(project_id or "").strip()
    if requested:
        try:
            from src.services.mcc_project_registry import get_project

            cfg = get_project(requested)
            if cfg is not None:
                return cfg
        except Exception:
            pass
        return None
    return _load_active_project_config()


def _load_session_state(project_id: str, window_session_id: str = "") -> "SessionState":
    # MARKER_181.MCC.PROJECT_ID.STATE.WINDOW_SCOPE.V1:
    # Session state is stored per project and optionally per window session.
    try:
        from src.services.mcc_project_registry import load_session_for_project

        return load_session_for_project(project_id, window_session_id=window_session_id)
    except Exception:
        return SessionState.load()


def _active_project_scope_root(config: Optional["ProjectConfig"]) -> str:
    if config is None:
        return ""
    resolved_scope = str(config.resolved_context_scope_path() or "").strip()
    if resolved_scope:
        return _norm_abs(resolved_scope)
    return ""


def _resolve_project_scope_path(base_scope: str, requested_path: str) -> str:
    candidate = str(requested_path or "").strip()
    if not candidate:
        return base_scope
    resolved = (
        _norm_abs(candidate)
        if os.path.isabs(candidate)
        else _norm_abs(os.path.join(base_scope, candidate))
    )
    if os.path.commonpath([base_scope, resolved]) != base_scope:
        raise HTTPException(
            status_code=400,
            detail=f"path must be inside active project scope: {base_scope}",
        )
    return resolved


def _build_directory_tree(
    abs_path: str, root_scope: str, *, depth: int, limit: int
) -> Dict[str, Any]:
    target = _norm_abs(abs_path)
    root = _norm_abs(root_scope)
    if not os.path.isdir(target):
        raise HTTPException(status_code=404, detail=f"Directory not found: {target}")

    def _walk(current: str, remaining_depth: int) -> Dict[str, Any]:
        rel = os.path.relpath(current, root).replace("\\", "/")
        if rel == ".":
            rel = ""
        node: Dict[str, Any] = {
            "name": os.path.basename(current.rstrip(os.sep))
            or os.path.basename(root.rstrip(os.sep))
            or current,
            "path": rel,
            "kind": "directory",
            "children": [],
            "truncated": False,
        }
        if remaining_depth <= 0:
            return node
        try:
            entries = sorted(
                os.scandir(current),
                key=lambda item: (
                    not item.is_dir(follow_symlinks=False),
                    item.name.lower(),
                ),
            )
        except Exception:
            node["error"] = "unreadable"
            return node
        for idx, entry in enumerate(entries):
            if idx >= limit:
                node["truncated"] = True
                break
            child_abs = _norm_abs(entry.path)
            child_rel = os.path.relpath(child_abs, root).replace("\\", "/")
            if entry.is_dir(follow_symlinks=False):
                node["children"].append(_walk(child_abs, remaining_depth - 1))
            else:
                node["children"].append(
                    {
                        "name": entry.name,
                        "path": child_rel,
                        "kind": "file",
                    }
                )
        return node

    return _walk(target, max(1, int(depth)))


def _get_task_board_instance():
    from src.orchestration.task_board import get_task_board

    return get_task_board()


async def _create_localguys_playground(
    *,
    task_description: str,
    preset: str,
    source_branch: str,
) -> Dict[str, Any]:
    from src.orchestration.playground_manager import create_playground

    return await create_playground(
        task=task_description,
        preset=preset,
        auto_write=True,
    )


def _get_localguys_run_registry():
    return get_localguys_run_registry()


def _get_mcc_benchmark_store():
    return get_mcc_benchmark_store()


def _list_core_workflow_templates() -> List[Dict[str, Any]]:
    from src.services.architect_prefetch import WorkflowTemplateLibrary

    return list(WorkflowTemplateLibrary.list_templates() or [])


def _list_saved_workflow_templates() -> List[Dict[str, Any]]:
    from src.services.workflow_store import WorkflowStore

    return list(WorkflowStore().list_workflows() or [])


def _detect_saved_workflow_bank(row: Dict[str, Any]) -> str:
    """
    MARKER_167.STATS_WORKFLOW.CATALOG_BANK_CLASSIFY.V1
    Classify saved/imported workflows into explicit MCC banks.
    """
    meta = row.get("metadata", {})
    if not isinstance(meta, dict):
        meta = {}

    explicit_bank = str(meta.get("workflow_bank") or "").strip().lower()
    if explicit_bank in {"saved", "n8n", "comfyui", "imported"}:
        return explicit_bank

    imported_from = (
        str(meta.get("imported_from") or meta.get("import_format") or "")
        .strip()
        .lower()
    )
    if imported_from == "n8n":
        return "n8n"
    if imported_from.startswith("comfyui"):
        return "comfyui"
    if imported_from:
        return "imported"
    return "saved"


def _normalize_workflow_catalog_row(bank: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """
    MARKER_167.STATS_WORKFLOW.CATALOG_NORMALIZE.V1
    Normalize workflow rows across MCC banks into one UI-facing contract.
    """
    if bank == "core":
        family_meta = row.get("workflow_family", {})
        family = ""
        if isinstance(family_meta, dict):
            family = str(family_meta.get("family") or "").strip()
        tags = [
            str(t).strip() for t in list(row.get("task_types") or []) if str(t).strip()
        ]
        tags = sorted(dict.fromkeys(tags))
        return {
            "bank": "core",
            "id": str(row.get("key") or row.get("id") or "").strip(),
            "key": str(row.get("key") or row.get("id") or "").strip(),
            "title": str(
                row.get("name") or row.get("id") or row.get("key") or "Untitled"
            ).strip(),
            "family": family or "core_library",
            "source": "core_library",
            "description": str(row.get("description") or "").strip(),
            "compatibility_tags": tags,
            "metrics": {
                "node_count": int(row.get("node_count") or 0),
            },
        }

    meta = row.get("metadata", {})
    normalized_bank = _detect_saved_workflow_bank(row)
    family = ""
    if isinstance(meta, dict):
        family = str(
            meta.get("workflow_family") or meta.get("template_family") or ""
        ).strip()
    return {
        "bank": normalized_bank,
        "id": str(row.get("id") or "").strip(),
        "key": str(row.get("id") or "").strip(),
        "title": str(row.get("name") or row.get("id") or "Untitled").strip(),
        "family": family or f"{normalized_bank}_workflow",
        "source": "saved_workflow_store",
        "description": str(row.get("description") or "").strip(),
        "compatibility_tags": [],
        "metrics": {
            "node_count": int(row.get("node_count") or 0),
            "edge_count": int(row.get("edge_count") or 0),
        },
    }


def _build_workflow_catalog_payload() -> Dict[str, Any]:
    core_rows = [
        _normalize_workflow_catalog_row("core", row)
        for row in _list_core_workflow_templates()
    ]
    saved_rows = [
        _normalize_workflow_catalog_row("saved", row)
        for row in _list_saved_workflow_templates()
    ]
    workflows = core_rows + saved_rows
    bank_order = ["core", "saved", "n8n", "comfyui", "imported"]
    bank_labels = {
        "core": "Core",
        "saved": "Saved",
        "n8n": "n8n",
        "comfyui": "ComfyUI",
        "imported": "Imported",
    }
    counts = {key: 0 for key in bank_order}
    for row in workflows:
        key = str(row.get("bank") or "")
        if key in counts:
            counts[key] += 1
    return {
        "success": True,
        "banks": [
            {
                "key": key,
                "label": bank_labels[key],
                "count": counts[key],
                "available": True,
            }
            for key in bank_order
        ],
        "workflows": workflows,
        "total_count": len(workflows),
    }


def _complexity_to_int(raw: Any) -> int:
    value = str(raw or "").strip().lower()
    if value == "low":
        return 3
    if value == "high":
        return 8
    if value.isdigit():
        return max(1, min(10, int(value)))
    return 5


def _select_heuristic_workflow_binding(task: Dict[str, Any]) -> Dict[str, Any]:
    from src.services.architect_prefetch import WorkflowTemplateLibrary

    selection = WorkflowTemplateLibrary.select_workflow_with_policy(
        task_type=str(task.get("phase_type") or ""),
        complexity=_complexity_to_int(task.get("complexity")),
        task_description=" ".join(
            [
                str(task.get("title") or "").strip(),
                str(task.get("description") or "").strip(),
            ]
        ).strip(),
    )
    workflow_id = (
        str(selection.get("workflow_key") or "bmad_default").strip() or "bmad_default"
    )
    template = WorkflowTemplateLibrary.get_template(workflow_id) or {}
    family_meta = (template.get("metadata") or {}).get("workflow_family") or {}
    family = str(family_meta.get("family") or workflow_id).strip() or workflow_id
    return {
        "workflow_bank": "core",
        "workflow_id": workflow_id,
        "workflow_family": family,
        "team_profile": str(
            task.get("team_profile") or task.get("preset") or "dragon_silver"
        ).strip()
        or "dragon_silver",
        "selection_origin": "heuristic",
    }


def _resolve_task_workflow_binding(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    MARKER_167.STATS_WORKFLOW.RESTORE_ORDER.V1
    Resolve workflow binding with explicit task metadata priority.
    """
    explicit_workflow_id = str(task.get("workflow_id") or "").strip()
    explicit_workflow_bank = str(task.get("workflow_bank") or "").strip()
    explicit_workflow_family = str(task.get("workflow_family") or "").strip()
    explicit_selection_origin = str(task.get("workflow_selection_origin") or "").strip()
    explicit_team_profile = str(
        task.get("team_profile") or task.get("preset") or ""
    ).strip()

    if explicit_workflow_id and (
        explicit_workflow_bank
        or explicit_workflow_family
        or explicit_selection_origin
        in {"user-selected", "saved-task-binding", "restored"}
    ):
        return {
            "workflow_bank": explicit_workflow_bank or "core",
            "workflow_id": explicit_workflow_id,
            "workflow_family": explicit_workflow_family or explicit_workflow_id,
            "team_profile": explicit_team_profile or "dragon_silver",
            "selection_origin": explicit_selection_origin or "saved-task-binding",
        }

    if explicit_workflow_id:
        return {
            "workflow_bank": "core",
            "workflow_id": explicit_workflow_id,
            "workflow_family": explicit_workflow_family or explicit_workflow_id,
            "team_profile": explicit_team_profile or "dragon_silver",
            "selection_origin": "legacy-task-field",
        }

    return _select_heuristic_workflow_binding(task)


_LOCALGUYS_MODEL_MATRIX: Dict[str, Dict[str, Any]] = {
    "qwen3.5:latest": {
        "role_fit": ["coder", "architect", "researcher"],
        "prompt_style": "coder_compact_v1",
        "tool_budget_class": "medium",
        "workflow_usage": [
            "g3_localguys",
            "ralph_localguys",
            "quickfix_localguys",
            "testonly_localguys",
            "docs_localguys",
            "research_localguys",
            "dragons_localguys",
            "refactor_localguys",
            "bmad_localguys",
            "patchchain_localguys",
            "ownership_localguys",
        ],
    },
    "qwen3:8b": {
        "role_fit": ["coder", "architect", "researcher"],
        "prompt_style": "coder_compact_v1",
        "tool_budget_class": "medium",
        "workflow_usage": [
            "g3_localguys",
            "ralph_localguys",
            "quickfix_localguys",
            "testonly_localguys",
            "docs_localguys",
            "research_localguys",
            "dragons_localguys",
            "refactor_localguys",
            "bmad_localguys",
            "patchchain_localguys",
            "ownership_localguys",
        ],
    },
    "qwen2.5:7b": {
        "role_fit": ["coder", "architect", "researcher"],
        "prompt_style": "coder_compact_v1",
        "tool_budget_class": "medium",
        "workflow_usage": [
            "g3_localguys",
            "ralph_localguys",
            "quickfix_localguys",
            "testonly_localguys",
            "docs_localguys",
            "research_localguys",
            "dragons_localguys",
            "refactor_localguys",
            "bmad_localguys",
            "patchchain_localguys",
            "ownership_localguys",
        ],
    },
    "qwen2.5:3b": {
        "role_fit": ["coder", "support", "researcher"],
        "prompt_style": "coder_compact_v1",
        "tool_budget_class": "low",
        "workflow_usage": [
            "g3_localguys",
            "ralph_localguys",
            "quickfix_localguys",
            "testonly_localguys",
            "docs_localguys",
            "research_localguys",
            "dragons_localguys",
            "refactor_localguys",
            "bmad_localguys",
            "patchchain_localguys",
            "ownership_localguys",
        ],
    },
    "deepseek-r1:8b": {
        "role_fit": ["verifier", "architect"],
        "prompt_style": "verifier_attack_v1",
        "tool_budget_class": "low-medium",
        "workflow_usage": [
            "g3_localguys",
            "ralph_localguys",
            "quickfix_localguys",
            "testonly_localguys",
            "research_localguys",
            "dragons_localguys",
            "refactor_localguys",
            "bmad_localguys",
            "patchchain_localguys",
            "ownership_localguys",
        ],
    },
    "phi4-mini:latest": {
        "role_fit": ["router", "verifier", "scout", "approval"],
        "prompt_style": "router_tiny_v1",
        "tool_budget_class": "low",
        "workflow_usage": [
            "g3_localguys",
            "ralph_localguys",
            "quickfix_localguys",
            "testonly_localguys",
            "docs_localguys",
            "research_localguys",
            "dragons_localguys",
            "refactor_localguys",
            "bmad_localguys",
            "patchchain_localguys",
        ],
    },
    "qwen2.5vl:3b": {
        "role_fit": ["scout"],
        "prompt_style": "visual_scout_v1",
        "tool_budget_class": "low",
        "workflow_usage": [
            "g3_localguys",
            "quickfix_localguys",
            "testonly_localguys",
            "docs_localguys",
            "research_localguys",
            "dragons_localguys",
            "refactor_localguys",
            "bmad_localguys",
        ],
    },
    "embeddinggemma:300m": {
        "role_fit": ["retrieval"],
        "prompt_style": "embedding_only_v1",
        "tool_budget_class": "n/a",
        "workflow_usage": [
            "g3_localguys",
            "ralph_localguys",
            "quickfix_localguys",
            "testonly_localguys",
            "docs_localguys",
            "research_localguys",
            "dragons_localguys",
        ],
    },
}

_LOCALGUYS_CATALOG_IDS = [
    "qwen3.5:latest",
    "qwen3:8b",
    "qwen2.5:7b",
    "qwen2.5:3b",
    "deepseek-r1:8b",
    "phi4-mini:latest",
    "qwen2.5vl:3b",
    "embeddinggemma:300m",
]

_LOCALGUYS_OPERATOR_METHODS: Dict[str, Dict[str, str]] = {
    "g3_localguys": {
        "method": "g3",
        "source_family": "g3_critic_coder",
        "command_template": "localguys run g3 --task {task_id}",
    },
    "ralph_localguys": {
        "method": "ralph",
        "source_family": "ralph_loop",
        "command_template": "localguys run ralph --task {task_id}",
    },
    "quickfix_localguys": {
        "method": "quickfix",
        "source_family": "quick_fix",
        "command_template": "localguys run quickfix --task {task_id}",
    },
    "testonly_localguys": {
        "method": "testonly",
        "source_family": "test_only",
        "command_template": "localguys run testonly --task {task_id}",
    },
    "docs_localguys": {
        "method": "docs",
        "source_family": "docs_update",
        "command_template": "localguys run docs --task {task_id}",
    },
    "research_localguys": {
        "method": "research",
        "source_family": "research_first",
        "command_template": "localguys run research --task {task_id}",
    },
    "dragons_localguys": {
        "method": "dragons",
        "source_family": "dragons",
        "command_template": "localguys run dragons --task {task_id}",
    },
    "refactor_localguys": {
        "method": "refactor",
        "source_family": "refactor",
        "command_template": "localguys run refactor --task {task_id}",
    },
    "bmad_localguys": {
        "method": "bmad",
        "source_family": "bmad_default",
        "command_template": "localguys run bmad --task {task_id}",
    },
    "patchchain_localguys": {
        "method": "patchchain",
        "source_family": "local_patch_chain",
        "command_template": "localguys run patchchain --task {task_id}",
    },
    "ownership_localguys": {
        "method": "ownership",
        "source_family": "local_task_ownership",
        "command_template": "localguys run ownership --task {task_id}",
    },
}


def _infer_capability_values(model_id: str, model_registry: Any) -> List[str]:
    entry = (
        getattr(model_registry, "_models", {}).get(model_id)
        if model_registry is not None
        else None
    )
    if entry is not None:
        caps = []
        for cap in list(getattr(entry, "capabilities", []) or []):
            value = getattr(cap, "value", None)
            if isinstance(value, str) and value:
                caps.append(value)
        if caps:
            return sorted(dict.fromkeys(caps))

    model_lower = str(model_id or "").lower()
    caps = ["chat"]
    if (
        "coder" in model_lower
        or "code" in model_lower
        or model_lower.startswith("qwen")
    ):
        caps.append("code")
    if "vl" in model_lower or "vision" in model_lower:
        caps.append("vision")
    if "embedding" in model_lower or "embed" in model_lower:
        return ["embeddings"]
    if "reason" in model_lower or "deepseek-r1" in model_lower or "phi4" in model_lower:
        caps.append("reasoning")
    return sorted(dict.fromkeys(caps))


async def _build_local_model_descriptor(model_id: str) -> Dict[str, Any]:
    from src.elisya.llm_model_registry import get_llm_registry
    from src.services.model_registry import get_model_registry
    from src.services.model_policy import get_unified_policy

    llm_profile = await get_llm_registry().get_profile(model_id)
    model_registry = get_model_registry()
    entry = getattr(model_registry, "_models", {}).get(model_id)

    policy_obj = get_unified_policy(model_id)

    provider = (
        str(
            getattr(entry, "provider", "")
            or getattr(llm_profile, "provider", "")
            or ("ollama" if ":" in model_id and "/" not in model_id else "unknown")
        ).strip()
        or "unknown"
    )
    entry_type = str(getattr(getattr(entry, "type", None), "value", "") or "").strip()

    # Get workflow_usage from legacy matrix (for backward compatibility)
    legacy_policy = dict(_LOCALGUYS_MODEL_MATRIX.get(model_id, {}))

    return {
        "model_id": str(model_id),
        "provider": provider,
        "source": str(getattr(llm_profile, "source", "") or "").strip() or "fallback",
        "context_length": int(getattr(llm_profile, "context_length", 0) or 0),
        "output_tokens_per_second": float(
            getattr(llm_profile, "output_tokens_per_second", 0.0) or 0.0
        ),
        "input_tokens_per_second": float(
            getattr(llm_profile, "input_tokens_per_second", 0.0) or 0.0
        ),
        "ttft_ms": float(getattr(llm_profile, "ttft_ms", 0.0) or 0.0),
        "available": bool(getattr(entry, "available", True)),
        "model_type": entry_type or ("local" if provider == "ollama" else "unknown"),
        "capabilities": _infer_capability_values(model_id, model_registry),
        # From unified ModelPolicy
        "role_fit": policy_obj.role_fit,
        "prompt_style": str(legacy_policy.get("prompt_style") or "").strip(),
        "tool_budget_class": policy_obj.tool_budget_class,
        "workflow_usage": list(legacy_policy.get("workflow_usage") or []),
        "fc_reliability": policy_obj.fc_reliability,
        "max_tools": policy_obj.max_tools,
        "prefer_simple": policy_obj.prefer_simple,
    }


async def _build_local_model_catalog() -> List[Dict[str, Any]]:
    return [
        await _build_local_model_descriptor(model_id)
        for model_id in _LOCALGUYS_CATALOG_IDS
    ]


async def _build_model_group(model_ids: List[str]) -> List[Dict[str, Any]]:
    return [await _build_local_model_descriptor(model_id) for model_id in model_ids]


def _build_stage_tool_policy(
    steps: List[str],
    allowed_tools: List[str],
) -> Dict[str, List[str]]:
    allowed = list(
        dict.fromkeys(str(tool).strip() for tool in allowed_tools if str(tool).strip())
    )
    default_map = {
        "recon": ["context", "search", "artifacts", "stats"],
        "research": ["context", "search", "artifacts", "stats"],
        "plan": ["context", "tasks", "artifacts", "stats"],
        "execute": allowed,
        "verify": ["context", "tests", "artifacts", "git_diff", "stats"],
        "review": ["context", "artifacts", "git_diff", "stats"],
        "approve": ["context", "artifacts", "stats", "tasks"],
        "finalize": ["artifacts", "stats", "git_diff"],
    }
    policy: Dict[str, List[str]] = {}
    for step in steps:
        step_key = str(step).strip()
        candidates = default_map.get(step_key, allowed)
        policy[step_key] = [tool for tool in candidates if tool in allowed]
    return policy


def _derive_verification_target(completion_policy: Dict[str, Any]) -> str:
    if bool(completion_policy.get("requires_targeted_tests")):
        return "targeted_tests"
    if bool(completion_policy.get("requires_verifier_pass")):
        return "verifier_review"
    return "artifact_review"


def _derive_max_turns(
    steps: List[str],
    tool_budget: Dict[str, Dict[str, int]],
) -> int:
    turn_count = 0
    for step in steps:
        budget = dict(tool_budget.get(step) or {})
        turn_count += max(1, int(budget.get("max_retries") or 0) + 1)
    return max(4, turn_count)


async def _build_localguys_contract(
    *,
    workflow_family: str,
    roles: List[str],
    steps: List[str],
    model_policy: Dict[str, Dict[str, Any]],
    tool_budget: Dict[str, Dict[str, int]],
    required_artifacts: List[str],
    completion_policy: Dict[str, Any],
    allowed_tools: Optional[List[str]] = None,
    allowed_files: Optional[List[str]] = None,
    failure_stop_on: Optional[List[str]] = None,
    expected_sequence: Optional[List[str]] = None,
    direct_allowed_tools: Optional[List[str]] = None,
    reflex_policy: Optional[Dict[str, Any]] = None,
    write_opt_ins: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    operator_method = dict(_LOCALGUYS_OPERATOR_METHODS.get(workflow_family, {}))
    effective_allowed_tools = allowed_tools or [
        "context",
        "tasks",
        "artifacts",
        "stats",
        "search",
        "tests",
        "git_diff",
    ]
    effective_write_opt_ins = {
        "task_board": False,
        "edit_file": True,
        "playground_artifacts": True,
        "main_tree_write": False,
    }
    if isinstance(write_opt_ins, dict):
        effective_write_opt_ins.update(
            {str(key): bool(value) for key, value in write_opt_ins.items()}
        )
    return {
        "workflow_family": workflow_family,
        "version": "v1",
        "roles": roles,
        "steps": steps,
        "execution_mode": "staged_state_machine",
        "model_policy": model_policy,
        "tool_budget": tool_budget,
        "allowed_tools": effective_allowed_tools,
        "stage_tool_policy": _build_stage_tool_policy(steps, effective_allowed_tools),
        "allowed_files": allowed_files or [],
        "expected_sequence": list(expected_sequence or []),
        "direct_allowed_tools": list(direct_allowed_tools or []),
        "reflex_policy": dict(reflex_policy or {}),
        "write_opt_ins": effective_write_opt_ins,
        "artifact_contract": {
            "required": required_artifacts,
            "base_path": "artifacts/mcc_local/{task_id}/",
        },
        "verification_target": _derive_verification_target(completion_policy),
        "max_turns": _derive_max_turns(steps, tool_budget),
        "idle_nudge_template": (
            "Continue the current localguys step inside the playground. "
            "If blocked, write the blocker into artifacts and stop instead of widening scope."
        ),
        "failure_policy": {
            "stop_on": failure_stop_on
            or [
                "budget_exhausted",
                "playground_missing",
                "verifier_blocked",
                "required_artifact_missing",
                "required_test_failed",
            ],
            "terminal_states": ["blocked", "failed", "escalated"],
        },
        "sandbox_policy": {
            "mode": "playground_only",
            "requires_playground": True,
            "requires_branch": True,
            "allow_main_tree_write": False,
            "lock_to_playground_id": True,
        },
        "completion_policy": completion_policy,
        "operator_method": operator_method,
        "local_model_catalog": await _build_local_model_catalog(),
    }


async def _resolve_g3_localguys_contract() -> Dict[str, Any]:
    return await _build_localguys_contract(
        workflow_family="g3_localguys",
        roles=["coder", "verifier"],
        steps=["recon", "plan", "execute", "verify", "review", "finalize"],
        model_policy={
            "coder": {
                "preferred_models": await _build_model_group(
                    ["qwen3:8b", "qwen2.5:7b"]
                ),
                "fallback_models": await _build_model_group(["qwen2.5:3b"]),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 24000,
            },
            "verifier": {
                "preferred_models": await _build_model_group(["deepseek-r1:8b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "verifier_attack_v1",
                "max_context_chars": 18000,
            },
        },
        tool_budget={
            "recon": {"max_tool_calls": 6, "max_retries": 1},
            "plan": {"max_tool_calls": 2, "max_retries": 1},
            "execute": {"max_tool_calls": 8, "max_retries": 2},
            "verify": {"max_tool_calls": 4, "max_retries": 1},
            "review": {"max_tool_calls": 3, "max_retries": 1},
            "finalize": {"max_tool_calls": 2, "max_retries": 1},
        },
        required_artifacts=[
            "facts.json",
            "plan.json",
            "patch.diff",
            "test_output.txt",
            "review.json",
            "final_report.json",
        ],
        completion_policy={
            "requires_verifier_pass": True,
            "requires_required_artifacts": True,
            "requires_targeted_tests": True,
            "requires_final_report": True,
        },
    )


async def _resolve_ralph_localguys_contract() -> Dict[str, Any]:
    return await _build_localguys_contract(
        workflow_family="ralph_localguys",
        roles=["coder", "verifier"],
        steps=["recon", "execute", "verify", "finalize"],
        model_policy={
            "coder": {
                "preferred_models": await _build_model_group(["qwen3:8b"]),
                "fallback_models": await _build_model_group(
                    ["qwen2.5:7b", "qwen2.5:3b"]
                ),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 18000,
            },
            "verifier": {
                "preferred_models": await _build_model_group(["deepseek-r1:8b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "verifier_attack_v1",
                "max_context_chars": 12000,
            },
        },
        tool_budget={
            "recon": {"max_tool_calls": 4, "max_retries": 1},
            "execute": {"max_tool_calls": 6, "max_retries": 2},
            "verify": {"max_tool_calls": 3, "max_retries": 1},
            "finalize": {"max_tool_calls": 2, "max_retries": 1},
        },
        required_artifacts=[
            "facts.json",
            "patch.diff",
            "test_output.txt",
            "final_report.json",
        ],
        completion_policy={
            "requires_verifier_pass": True,
            "requires_required_artifacts": True,
            "requires_targeted_tests": True,
            "requires_final_report": True,
        },
    )


async def _resolve_quickfix_localguys_contract() -> Dict[str, Any]:
    return await _build_localguys_contract(
        workflow_family="quickfix_localguys",
        roles=["scout", "coder", "verifier"],
        steps=["recon", "execute", "verify", "review", "finalize"],
        model_policy={
            "scout": {
                "preferred_models": await _build_model_group(["qwen2.5vl:3b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "visual_scout_v1",
                "max_context_chars": 12000,
            },
            "coder": {
                "preferred_models": await _build_model_group(
                    ["qwen3:8b", "qwen2.5:7b"]
                ),
                "fallback_models": await _build_model_group(["qwen2.5:3b"]),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 20000,
            },
            "verifier": {
                "preferred_models": await _build_model_group(["deepseek-r1:8b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "verifier_attack_v1",
                "max_context_chars": 14000,
            },
        },
        tool_budget={
            "recon": {"max_tool_calls": 5, "max_retries": 1},
            "execute": {"max_tool_calls": 6, "max_retries": 2},
            "verify": {"max_tool_calls": 3, "max_retries": 1},
            "review": {"max_tool_calls": 2, "max_retries": 1},
            "finalize": {"max_tool_calls": 2, "max_retries": 1},
        },
        required_artifacts=[
            "facts.json",
            "patch.diff",
            "test_output.txt",
            "review.json",
            "final_report.json",
        ],
        completion_policy={
            "requires_verifier_pass": True,
            "requires_required_artifacts": True,
            "requires_targeted_tests": True,
            "requires_final_report": True,
        },
    )


async def _resolve_testonly_localguys_contract() -> Dict[str, Any]:
    return await _build_localguys_contract(
        workflow_family="testonly_localguys",
        roles=["scout", "coder", "verifier"],
        steps=["recon", "plan", "execute", "verify", "finalize"],
        model_policy={
            "scout": {
                "preferred_models": await _build_model_group(["qwen2.5vl:3b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "visual_scout_v1",
                "max_context_chars": 12000,
            },
            "coder": {
                "preferred_models": await _build_model_group(
                    ["qwen2.5:7b", "qwen3:8b"]
                ),
                "fallback_models": await _build_model_group(["qwen2.5:3b"]),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 20000,
            },
            "verifier": {
                "preferred_models": await _build_model_group(["deepseek-r1:8b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "verifier_attack_v1",
                "max_context_chars": 14000,
            },
        },
        tool_budget={
            "recon": {"max_tool_calls": 5, "max_retries": 1},
            "plan": {"max_tool_calls": 2, "max_retries": 1},
            "execute": {"max_tool_calls": 6, "max_retries": 2},
            "verify": {"max_tool_calls": 4, "max_retries": 1},
            "finalize": {"max_tool_calls": 2, "max_retries": 1},
        },
        required_artifacts=[
            "facts.json",
            "plan.json",
            "patch.diff",
            "test_output.txt",
            "review.json",
            "final_report.json",
        ],
        completion_policy={
            "requires_verifier_pass": True,
            "requires_required_artifacts": True,
            "requires_targeted_tests": True,
            "requires_final_report": True,
        },
    )


async def _resolve_docs_localguys_contract() -> Dict[str, Any]:
    return await _build_localguys_contract(
        workflow_family="docs_localguys",
        roles=["scout", "coder"],
        steps=["recon", "execute", "review", "finalize"],
        model_policy={
            "scout": {
                "preferred_models": await _build_model_group(["qwen2.5vl:3b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "visual_scout_v1",
                "max_context_chars": 10000,
            },
            "coder": {
                "preferred_models": await _build_model_group(
                    ["qwen3:8b", "qwen2.5:7b"]
                ),
                "fallback_models": await _build_model_group(["qwen2.5:3b"]),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 16000,
            },
        },
        tool_budget={
            "recon": {"max_tool_calls": 4, "max_retries": 1},
            "execute": {"max_tool_calls": 5, "max_retries": 2},
            "review": {"max_tool_calls": 2, "max_retries": 1},
            "finalize": {"max_tool_calls": 2, "max_retries": 1},
        },
        required_artifacts=[
            "facts.json",
            "patch.diff",
            "final_report.json",
        ],
        completion_policy={
            "requires_verifier_pass": False,
            "requires_required_artifacts": True,
            "requires_targeted_tests": False,
            "requires_final_report": True,
        },
    )


async def _resolve_research_localguys_contract() -> Dict[str, Any]:
    return await _build_localguys_contract(
        workflow_family="research_localguys",
        roles=["researcher", "architect", "coder", "verifier"],
        steps=["recon", "research", "plan", "execute", "verify", "review", "finalize"],
        model_policy={
            "researcher": {
                "preferred_models": await _build_model_group(["qwen3:8b"]),
                "fallback_models": await _build_model_group(
                    ["qwen2.5:7b", "phi4-mini:latest"]
                ),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 22000,
            },
            "architect": {
                "preferred_models": await _build_model_group(["qwen3:8b"]),
                "fallback_models": await _build_model_group(["qwen2.5:7b"]),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 20000,
            },
            "coder": {
                "preferred_models": await _build_model_group(
                    ["qwen3:8b", "qwen2.5:7b"]
                ),
                "fallback_models": await _build_model_group(["qwen2.5:3b"]),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 22000,
            },
            "verifier": {
                "preferred_models": await _build_model_group(["deepseek-r1:8b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "verifier_attack_v1",
                "max_context_chars": 16000,
            },
        },
        tool_budget={
            "recon": {"max_tool_calls": 5, "max_retries": 1},
            "research": {"max_tool_calls": 6, "max_retries": 1},
            "plan": {"max_tool_calls": 3, "max_retries": 1},
            "execute": {"max_tool_calls": 7, "max_retries": 2},
            "verify": {"max_tool_calls": 4, "max_retries": 1},
            "review": {"max_tool_calls": 3, "max_retries": 1},
            "finalize": {"max_tool_calls": 2, "max_retries": 1},
        },
        required_artifacts=[
            "facts.json",
            "plan.json",
            "patch.diff",
            "test_output.txt",
            "review.json",
            "final_report.json",
        ],
        completion_policy={
            "requires_verifier_pass": True,
            "requires_required_artifacts": True,
            "requires_targeted_tests": True,
            "requires_final_report": True,
        },
    )


async def _resolve_dragons_localguys_contract() -> Dict[str, Any]:
    return await _build_localguys_contract(
        workflow_family="dragons_localguys",
        roles=["scout", "architect", "coder", "verifier"],
        steps=["recon", "plan", "execute", "verify", "review", "finalize"],
        model_policy={
            "scout": {
                "preferred_models": await _build_model_group(["qwen2.5vl:3b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "visual_scout_v1",
                "max_context_chars": 14000,
            },
            "architect": {
                "preferred_models": await _build_model_group(
                    ["qwen3:8b", "qwen2.5:7b"]
                ),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 20000,
            },
            "coder": {
                "preferred_models": await _build_model_group(
                    ["qwen3:8b", "qwen2.5:7b"]
                ),
                "fallback_models": await _build_model_group(["qwen2.5:3b"]),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 22000,
            },
            "verifier": {
                "preferred_models": await _build_model_group(["deepseek-r1:8b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "verifier_attack_v1",
                "max_context_chars": 16000,
            },
        },
        tool_budget={
            "recon": {"max_tool_calls": 5, "max_retries": 1},
            "plan": {"max_tool_calls": 3, "max_retries": 1},
            "execute": {"max_tool_calls": 7, "max_retries": 2},
            "verify": {"max_tool_calls": 4, "max_retries": 1},
            "review": {"max_tool_calls": 3, "max_retries": 1},
            "finalize": {"max_tool_calls": 2, "max_retries": 1},
        },
        required_artifacts=[
            "facts.json",
            "plan.json",
            "patch.diff",
            "test_output.txt",
            "review.json",
            "final_report.json",
        ],
        completion_policy={
            "requires_verifier_pass": True,
            "requires_required_artifacts": True,
            "requires_targeted_tests": True,
            "requires_final_report": True,
            "requires_team_profile": True,
        },
    )


async def _resolve_refactor_localguys_contract() -> Dict[str, Any]:
    return await _build_localguys_contract(
        workflow_family="refactor_localguys",
        roles=["scout", "architect", "coder", "verifier"],
        steps=["recon", "research", "plan", "execute", "verify", "review", "finalize"],
        model_policy={
            "scout": {
                "preferred_models": await _build_model_group(["qwen2.5vl:3b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "visual_scout_v1",
                "max_context_chars": 16000,
            },
            "architect": {
                "preferred_models": await _build_model_group(
                    ["qwen3:8b", "qwen2.5:7b"]
                ),
                "fallback_models": await _build_model_group(["deepseek-r1:8b"]),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 24000,
            },
            "coder": {
                "preferred_models": await _build_model_group(
                    ["qwen3:8b", "qwen2.5:7b"]
                ),
                "fallback_models": await _build_model_group(["qwen2.5:3b"]),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 24000,
            },
            "verifier": {
                "preferred_models": await _build_model_group(["deepseek-r1:8b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "verifier_attack_v1",
                "max_context_chars": 18000,
            },
        },
        tool_budget={
            "recon": {"max_tool_calls": 6, "max_retries": 1},
            "research": {"max_tool_calls": 5, "max_retries": 1},
            "plan": {"max_tool_calls": 4, "max_retries": 1},
            "execute": {"max_tool_calls": 8, "max_retries": 2},
            "verify": {"max_tool_calls": 4, "max_retries": 1},
            "review": {"max_tool_calls": 3, "max_retries": 1},
            "finalize": {"max_tool_calls": 2, "max_retries": 1},
        },
        required_artifacts=[
            "facts.json",
            "plan.json",
            "patch.diff",
            "test_output.txt",
            "review.json",
            "final_report.json",
        ],
        completion_policy={
            "requires_verifier_pass": True,
            "requires_required_artifacts": True,
            "requires_targeted_tests": True,
            "requires_final_report": True,
            "requires_allowlist_scope": True,
        },
        allowed_tools=[
            "context",
            "tasks",
            "artifacts",
            "stats",
            "search",
            "tests",
            "git_diff",
        ],
    )


async def _resolve_patchchain_localguys_contract() -> Dict[str, Any]:
    return await _build_localguys_contract(
        workflow_family="patchchain_localguys",
        roles=["coder"],
        steps=["recon", "execute", "verify", "finalize"],
        model_policy={
            "coder": {
                "preferred_models": await _build_model_group(
                    ["qwen3.5:latest", "qwen3:8b"]
                ),
                "fallback_models": await _build_model_group(
                    ["qwen2.5:7b", "qwen2.5:3b"]
                ),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 20000,
            },
        },
        tool_budget={
            "recon": {"max_tool_calls": 4, "max_retries": 1},
            "execute": {"max_tool_calls": 5, "max_retries": 1},
            "verify": {"max_tool_calls": 3, "max_retries": 1},
            "finalize": {"max_tool_calls": 1, "max_retries": 1},
        },
        required_artifacts=[
            "facts.json",
            "patch.diff",
            "test_output.txt",
            "final_report.json",
        ],
        completion_policy={
            "requires_verifier_pass": False,
            "requires_required_artifacts": True,
            "requires_targeted_tests": True,
            "requires_final_report": True,
            "requires_expected_sequence": True,
        },
        allowed_tools=["context", "artifacts", "tests", "git_diff"],
        expected_sequence=["vetka_read_file", "vetka_edit_file", "vetka_run_tests"],
        direct_allowed_tools=["vetka_read_file", "vetka_edit_file", "vetka_run_tests"],
        reflex_policy={
            "enabled": True,
            "inject_system_hint": True,
            "reorder_tools": True,
            "normalize_native_tool_calls": True,
            "rehydrate_tool_arguments": True,
            "idle_nudge_loop": True,
        },
        failure_stop_on=[
            "budget_exhausted",
            "required_artifact_missing",
            "required_test_failed",
            "idle_stall",
        ],
    )


async def _resolve_ownership_localguys_contract() -> Dict[str, Any]:
    return await _build_localguys_contract(
        workflow_family="ownership_localguys",
        roles=["operator"],
        steps=["recon", "execute", "verify", "finalize"],
        model_policy={
            "operator": {
                "preferred_models": await _build_model_group(
                    ["qwen3.5:latest", "phi4-mini:latest"]
                ),
                "fallback_models": await _build_model_group(["qwen2.5:7b"]),
                "prompt_style": "router_tiny_v1",
                "max_context_chars": 12000,
            },
        },
        tool_budget={
            "recon": {"max_tool_calls": 3, "max_retries": 1},
            "execute": {"max_tool_calls": 3, "max_retries": 1},
            "verify": {"max_tool_calls": 2, "max_retries": 1},
            "finalize": {"max_tool_calls": 1, "max_retries": 1},
        },
        required_artifacts=[
            "facts.json",
            "final_report.json",
        ],
        completion_policy={
            "requires_verifier_pass": False,
            "requires_required_artifacts": True,
            "requires_targeted_tests": False,
            "requires_final_report": True,
            "requires_task_claim": True,
        },
        allowed_tools=["context", "tasks", "stats"],
        expected_sequence=["mycelium_task_board"],
        direct_allowed_tools=["mycelium_task_board"],
        reflex_policy={
            "enabled": True,
            "inject_system_hint": True,
            "reorder_tools": True,
            "normalize_native_tool_calls": True,
            "rehydrate_tool_arguments": True,
            "allow_task_board_writes": True,
        },
        write_opt_ins={
            "task_board": True,
            "edit_file": False,
            "playground_artifacts": False,
            "main_tree_write": False,
        },
        failure_stop_on=[
            "budget_exhausted",
            "task_board_write_denied",
            "required_artifact_missing",
        ],
    )


async def _resolve_bmad_localguys_contract() -> Dict[str, Any]:
    return await _build_localguys_contract(
        workflow_family="bmad_localguys",
        roles=["scout", "researcher", "architect", "coder", "verifier", "approval"],
        steps=[
            "recon",
            "research",
            "plan",
            "execute",
            "verify",
            "review",
            "approve",
            "finalize",
        ],
        model_policy={
            "scout": {
                "preferred_models": await _build_model_group(["qwen2.5vl:3b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "visual_scout_v1",
                "max_context_chars": 14000,
            },
            "researcher": {
                "preferred_models": await _build_model_group(["qwen3:8b"]),
                "fallback_models": await _build_model_group(
                    ["qwen2.5:7b", "qwen2.5:3b"]
                ),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 22000,
            },
            "architect": {
                "preferred_models": await _build_model_group(
                    ["qwen3:8b", "qwen2.5:7b"]
                ),
                "fallback_models": await _build_model_group(["deepseek-r1:8b"]),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 22000,
            },
            "coder": {
                "preferred_models": await _build_model_group(
                    ["qwen3:8b", "qwen2.5:7b"]
                ),
                "fallback_models": await _build_model_group(["qwen2.5:3b"]),
                "prompt_style": "coder_compact_v1",
                "max_context_chars": 24000,
            },
            "verifier": {
                "preferred_models": await _build_model_group(["deepseek-r1:8b"]),
                "fallback_models": await _build_model_group(["phi4-mini:latest"]),
                "prompt_style": "verifier_attack_v1",
                "max_context_chars": 18000,
            },
            "approval": {
                "preferred_models": await _build_model_group(["phi4-mini:latest"]),
                "fallback_models": await _build_model_group(["deepseek-r1:8b"]),
                "prompt_style": "router_tiny_v1",
                "max_context_chars": 12000,
            },
        },
        tool_budget={
            "recon": {"max_tool_calls": 6, "max_retries": 1},
            "research": {"max_tool_calls": 6, "max_retries": 1},
            "plan": {"max_tool_calls": 4, "max_retries": 1},
            "execute": {"max_tool_calls": 8, "max_retries": 2},
            "verify": {"max_tool_calls": 4, "max_retries": 1},
            "review": {"max_tool_calls": 3, "max_retries": 1},
            "approve": {"max_tool_calls": 2, "max_retries": 1},
            "finalize": {"max_tool_calls": 2, "max_retries": 1},
        },
        required_artifacts=[
            "facts.json",
            "plan.json",
            "patch.diff",
            "test_output.txt",
            "review.json",
            "approval.json",
            "final_report.json",
        ],
        completion_policy={
            "requires_verifier_pass": True,
            "requires_required_artifacts": True,
            "requires_targeted_tests": True,
            "requires_final_report": True,
            "requires_approval_gate": True,
        },
    )


async def _resolve_workflow_contract(workflow_family: str) -> Dict[str, Any] | None:
    family = str(workflow_family or "").strip().lower()
    if family == "g3_localguys":
        return await _resolve_g3_localguys_contract()
    if family == "ralph_localguys":
        return await _resolve_ralph_localguys_contract()
    if family == "quickfix_localguys":
        return await _resolve_quickfix_localguys_contract()
    if family == "testonly_localguys":
        return await _resolve_testonly_localguys_contract()
    if family == "docs_localguys":
        return await _resolve_docs_localguys_contract()
    if family == "research_localguys":
        return await _resolve_research_localguys_contract()
    if family == "dragons_localguys":
        return await _resolve_dragons_localguys_contract()
    if family == "refactor_localguys":
        return await _resolve_refactor_localguys_contract()
    if family == "patchchain_localguys":
        return await _resolve_patchchain_localguys_contract()
    if family == "ownership_localguys":
        return await _resolve_ownership_localguys_contract()
    if family == "bmad_localguys":
        return await _resolve_bmad_localguys_contract()
    return None


def _normalize_str_list(value: Any) -> List[str]:
    return [str(item).strip() for item in list(value or []) if str(item).strip()]


def _merge_unique_lists(*rows: Any) -> List[str]:
    merged: List[str] = []
    for row in rows:
        for item in _normalize_str_list(row):
            if item not in merged:
                merged.append(item)
    return merged


def _get_roadmap_node_snapshot(node_id: str) -> Dict[str, Any]:
    from src.services.roadmap_generator import RoadmapDAG

    target = str(node_id or "").strip()
    if not target:
        return {}
    dag = RoadmapDAG.load()
    if dag is None:
        return {}
    for node in list(dag.nodes or []):
        if isinstance(node, dict) and str(node.get("id") or "").strip() == target:
            return {
                **node,
                "_roadmap_project_id": str(getattr(dag, "project_id", "") or ""),
            }
    return {}


def _derive_attached_task_payload(
    body: Dict[str, Any], *, existing_task: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    requested_project_id = str(body.get("project_id") or "").strip()
    active_config = _resolve_project_config(requested_project_id)
    active_project_id = str(getattr(active_config, "project_id", "") or "").strip()
    node_id = str(
        body.get("node_id") or body.get("roadmap_node_id") or active_project_id or ""
    ).strip()
    node_label = str(body.get("node_label") or node_id or "Attached task").strip()
    node_path = str(body.get("node_path") or "").strip()
    graph_kind = str(body.get("node_graph_kind") or "").strip().lower()
    roadmap_node_id = str(body.get("roadmap_node_id") or node_id).strip()
    roadmap_node = _get_roadmap_node_snapshot(roadmap_node_id)

    roadmap_id = str(roadmap_node.get("_roadmap_project_id") or "").strip()
    roadmap_lane = str(roadmap_node.get("layer") or "").strip()
    roadmap_title = str(roadmap_node.get("label") or node_label).strip()
    lane = str(
        body.get("project_lane")
        or roadmap_node_id
        or body.get("project_id")
        or node_path
        or node_id
    ).strip()
    docs = _merge_unique_lists(body.get("architecture_docs"), roadmap_node.get("docs"))
    closure_files = _merge_unique_lists(
        body.get("closure_files"),
        [node_path] if node_path else [],
        roadmap_node.get("file_patterns"),
        roadmap_node.get("files"),
    )
    affected_nodes = _merge_unique_lists(
        body.get("affected_node_ids"), [node_id] if node_id else []
    )
    tags = _merge_unique_lists(
        body.get("tags"),
        ["anchored_task"],
        [f"roadmap:{roadmap_node_id}"] if roadmap_node_id else [],
    )

    explicit_phase = str(body.get("phase_type") or "").strip().lower()
    if explicit_phase:
        phase_type = explicit_phase
    elif roadmap_lane == "docs":
        phase_type = "research"
    elif roadmap_lane == "test":
        phase_type = "test"
    elif graph_kind in {"project_file", "project_task"}:
        phase_type = "fix"
    else:
        phase_type = "build"

    title = (
        str(body.get("title") or "").strip()
        or f"Attached: {roadmap_title or node_label}"[:100]
    )
    description = (
        str(body.get("description") or "").strip()
        or f"Attached to {roadmap_title or node_label}"
    )
    preset = str(body.get("preset") or "").strip()
    if not preset and isinstance(existing_task, dict):
        preset = str(existing_task.get("preset") or "").strip()
    if not preset:
        preset = "dragon_silver"
    project_id = str(
        body.get("project_id")
        or (existing_task or {}).get("project_id")
        or active_project_id
        or roadmap_id
        or lane
    ).strip()

    payload = {
        "title": title,
        "description": description,
        "priority": int(
            body.get(
                "priority",
                existing_task.get("priority", 3)
                if isinstance(existing_task, dict)
                else 3,
            )
            or 3
        ),
        "phase_type": phase_type,
        "preset": preset,
        "tags": tags,
        "module": node_path or roadmap_node_id or node_id,
        "primary_node_id": node_id,
        "affected_nodes": affected_nodes,
        "workflow_id": str(
            body.get("workflow_id") or f"wf_attach_{int(time.time() * 1000)}"
        ).strip(),
        "team_profile": preset,
        "task_origin": str(body.get("task_origin") or "mcc_attached").strip()
        or "mcc_attached",
        "source": str(body.get("source") or "mcc_attached").strip() or "mcc_attached",
        "workflow_selection_origin": str(
            body.get("workflow_selection_origin") or "mcc_attached"
        ).strip()
        or "mcc_attached",
        "project_id": project_id,
        "project_lane": lane or project_id,
        "roadmap_id": roadmap_id,
        "roadmap_node_id": roadmap_node_id,
        "roadmap_lane": roadmap_lane,
        "roadmap_title": roadmap_title,
        "architecture_docs": docs,
        "closure_files": closure_files,
    }
    if isinstance(existing_task, dict):
        payload["architecture_docs"] = _merge_unique_lists(
            existing_task.get("architecture_docs"), docs
        )
        payload["closure_files"] = _merge_unique_lists(
            existing_task.get("closure_files"), closure_files
        )
        payload["affected_nodes"] = _merge_unique_lists(
            existing_task.get("affected_nodes"), affected_nodes
        )
        payload["tags"] = _merge_unique_lists(existing_task.get("tags"), tags)
    return payload


def _save_session_state(
    project_id: str, state: "SessionState", window_session_id: str = ""
) -> bool:
    try:
        from src.services.mcc_project_registry import save_session_for_project

        return bool(
            save_session_for_project(
                project_id, state, window_session_id=window_session_id
            )
        )
    except Exception:
        return bool(state.save())


# ──────────────────────────────────────────────────────────────
# Request/Response models
# ──────────────────────────────────────────────────────────────


class InitResponse(BaseModel):
    has_project: bool
    project_config: Optional[dict] = None
    session_state: Optional[dict] = None
    active_project_id: str = ""
    window_session_id: str = ""
    updated_at: str = ""
    hidden_count: int = 0
    projects: List[Dict[str, Any]] = []


class ProjectInitRequest(BaseModel):
    source_type: str  # "local" | "git" | "empty"
    source_path: str  # absolute path or git URL
    execution_mode: str = "playground"
    project_kind: str = "user"
    sandbox_path: str = ""  # optional absolute path for playground/sandbox root
    # MARKER_161.9.MULTIPROJECT.NAMING.API_CONTRACT.V1
    project_name: str = ""  # optional user-facing project name (tab + display)
    quota_gb: int = 10


class ProjectInitResponse(BaseModel):
    success: bool
    project_id: str = ""
    # MARKER_161.9.MULTIPROJECT.NAMING.API_CONTRACT.V1
    project_name: str = ""
    execution_mode: str = ""
    project_kind: str = ""
    sandbox_path: str = ""
    errors: list[str] = []


class ProjectActivateRequest(BaseModel):
    project_id: str


class StateRequest(BaseModel):
    level: str = "roadmap"
    roadmap_node_id: str = ""
    task_id: str = ""
    project_id: str = ""
    window_session_id: str = ""
    selected_key: Optional[Dict[str, Any]] = None
    history: list[str] = []


class MCCTaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    preset: Optional[str] = None
    phase_type: Optional[str] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    workflow_family: Optional[str] = (
        None  # MARKER_175B: User-selected workflow template
    )
    project_id: Optional[str] = None
    project_lane: Optional[str] = None
    architecture_docs: Optional[List[str]] = None
    recon_docs: Optional[List[str]] = None
    closure_tests: Optional[List[str]] = None
    closure_files: Optional[List[str]] = None
    require_closure_proof: Optional[bool] = None


class MCCTaskFeedbackRequest(BaseModel):
    feedback: str = ""
    action: str = "redo"


class MCCAttachedTaskRequest(BaseModel):
    title: str = ""
    description: str = ""
    preset: str = "dragon_silver"
    phase_type: str = ""
    priority: int = 3
    node_id: str = ""
    node_label: str = ""
    node_path: str = ""
    node_graph_kind: str = ""
    roadmap_node_id: str = ""
    project_id: str = ""
    project_lane: str = ""
    tags: List[str] = []
    affected_node_ids: List[str] = []
    architecture_docs: List[str] = []
    closure_files: List[str] = []


# ──────────────────────────────────────────────────────────────
# GET /api/mcc/init — Load project config + session state
# ──────────────────────────────────────────────────────────────


@router.get("/init", response_model=InitResponse)
async def mcc_init(
    project_id: str = Query(
        "", description="Optional project_id to resolve for this window"
    ),
    window_session_id: str = Query(
        "", description="Optional per-window MCC session id"
    ),
):
    """
    Called on frontend mount. Returns:
    - has_project: bool — whether a project is configured
    - project_config: dict — project settings (if exists)
    - session_state: dict — last navigation state (if exists)

    MARKER_161.7.MULTIPROJECT.API.INIT_ACTIVE_PROJECT.V1:
    Migration point for active project tab context in MCC.
    """
    requested_project_id = str(project_id or "").strip()
    requested_window_session_id = str(window_session_id or "").strip()
    try:
        from src.services.mcc_project_registry import (
            ensure_registry_bootstrap,
            list_projects,
        )

        ensure_registry_bootstrap()
        listing = list_projects(always_include_project_id=requested_project_id)
    except Exception:
        listing = {"active_project_id": "", "projects": [], "hidden_count": 0}

    config = _resolve_project_config(requested_project_id)
    if config is None:
        return InitResponse(
            has_project=False,
            active_project_id=requested_project_id
            or str(listing.get("active_project_id", "")),
            window_session_id=requested_window_session_id,
            updated_at=str(listing.get("updated_at", "")),
            hidden_count=int(listing.get("hidden_count", 0) or 0),
            projects=list(listing.get("projects") or []),
        )

    state = _load_session_state(config.project_id, requested_window_session_id)
    from dataclasses import asdict

    return InitResponse(
        has_project=True,
        project_config=asdict(config),
        session_state=asdict(state),
        active_project_id=str(config.project_id),
        window_session_id=requested_window_session_id,
        updated_at=str(listing.get("updated_at", "")),
        hidden_count=int(listing.get("hidden_count", 0) or 0),
        projects=list(listing.get("projects") or []),
    )


# ──────────────────────────────────────────────────────────────
# POST /api/mcc/state — Save session state
# ──────────────────────────────────────────────────────────────


@router.post("/state")
async def save_state(req: StateRequest):
    """
    Called on every navigation change. Persists current level + selection.
    Survives server restart.
    """
    project_id = str(req.project_id or "").strip()
    config = _resolve_project_config(project_id)
    state = SessionState(
        level=req.level,
        roadmap_node_id=req.roadmap_node_id,
        task_id=req.task_id,
        selected_key=req.selected_key,
        history=req.history,
    )
    if config is None:
        if not state.save():
            raise HTTPException(status_code=500, detail="Failed to save session state")
        return {"ok": True}

    if not _save_session_state(
        config.project_id, state, str(req.window_session_id or "").strip()
    ):
        raise HTTPException(status_code=500, detail="Failed to save session state")
    return {"ok": True}


# ──────────────────────────────────────────────────────────────
# GET /api/mcc/state — Get current session state
# ──────────────────────────────────────────────────────────────


@router.get("/state")
async def get_state(
    project_id: str = Query(
        "", description="Optional explicit project_id for state resolution"
    ),
    window_session_id: str = Query(
        "", description="Optional per-window MCC session id"
    ),
):
    """Get current session state for Zustand hydration."""
    config = _resolve_project_config(project_id)
    if config is None:
        state = SessionState.load()
    else:
        state = _load_session_state(
            config.project_id, str(window_session_id or "").strip()
        )
    from dataclasses import asdict

    return asdict(state)


# ──────────────────────────────────────────────────────────────
# POST /api/mcc/project/init — First-time project setup
# ──────────────────────────────────────────────────────────────


@router.post("/project/init", response_model=ProjectInitResponse)
async def project_init(req: ProjectInitRequest):
    """
    First open flow:
    1. Validate source path
    2. Create ProjectConfig
    3. Create sandbox (copy project)
    4. Return config for frontend

    Note: Qdrant indexing and Roadmap generation happen asynchronously
    after this call returns (Wave 3-4).

    MARKER_161.7.MULTIPROJECT.API.PROJECT_CREATE.V1:
    Future behavior: create project record in registry and optionally auto-activate tab.
    """
    # MARKER_161.8.MULTIPROJECT.API.EMPTY_SOURCE_BOOTSTRAP.V1
    # Support "skip source" flow by creating an empty temporary source folder.
    req_source_type = str(req.source_type or "").strip().lower()
    req_source_path = str(req.source_path or "").strip()
    req_execution_mode = (
        str(req.execution_mode or "playground").strip().lower() or "playground"
    )
    req_project_kind = str(req.project_kind or "user").strip().lower() or "user"
    effective_source_type = req_source_type
    effective_source_path = req_source_path

    if req_source_type == "empty":
        temp_source = tempfile.mkdtemp(prefix="mycelium_empty_source_")
        try:
            with open(
                os.path.join(temp_source, "README.md"), "w", encoding="utf-8"
            ) as f:
                f.write("# New Project\n")
        except Exception:
            pass
        effective_source_type = "local"
        effective_source_path = temp_source

    # Create config
    config = ProjectConfig.create_new(
        source_type=effective_source_type,
        source_path=effective_source_path,
        quota_gb=req.quota_gb,
        execution_mode=req_execution_mode,
        project_kind=req_project_kind,
        sandbox_path=str(req.sandbox_path or ""),
        project_name=str(req.project_name or ""),
    )

    # Validate
    errors = config.validate()

    if req_execution_mode not in {"playground", "oauth_agent", "local_workspace"}:
        errors.append(f"Invalid execution_mode: {req_execution_mode}")
    if req_project_kind not in {"user", "fixture", "temp", "legacy"}:
        errors.append(f"Invalid project_kind: {req_project_kind}")

    # Validate source exists
    if effective_source_type == "local":
        if not os.path.exists(effective_source_path):
            errors.append(f"Source path not found: {effective_source_path}")
        elif not os.path.isdir(effective_source_path):
            errors.append(f"Source path is not a directory: {effective_source_path}")
        elif config.execution_mode == "playground" and _paths_overlap_or_nested(
            effective_source_path, config.sandbox_path
        ):
            errors.append(
                "sandbox_path must be isolated from source_path (no equal/nested paths)"
            )
    has_conflict, conflict_reason = _find_registry_path_conflict(config.sandbox_path)
    if config.sandbox_path and has_conflict:
        errors.append(
            f"sandbox_path must be isolated from existing projects ({conflict_reason})"
        )

    if errors:
        return ProjectInitResponse(success=False, errors=errors)

    # Create sandbox directory
    skipped_copy_sources: list[str] = []
    materialize_playground = str(config.execution_mode or "playground") == "playground"
    try:
        if materialize_playground:
            os.makedirs(config.sandbox_path, exist_ok=True)

        if materialize_playground and effective_source_type == "local":
            # Copy project to sandbox
            # shutil.copytree needs dst to not exist, so remove first
            if os.path.exists(config.sandbox_path):
                shutil.rmtree(config.sandbox_path)

            # MARKER_161.8.MULTIPROJECT.API.TOLERANT_LOCAL_COPY.V1
            # Some large trees mutate during copy (generated datasets, transient artifacts).
            # Do best-effort copy and skip files that vanish mid-flight.
            def _copy2_best_effort(src: str, dst: str) -> str:
                try:
                    return shutil.copy2(src, dst)
                except FileNotFoundError:
                    skipped_copy_sources.append(src)
                    return dst

            shutil.copytree(
                effective_source_path,
                config.sandbox_path,
                ignore=shutil.ignore_patterns(
                    "node_modules",
                    ".git",
                    "__pycache__",
                    "*.pyc",
                    "dist",
                    "build",
                    ".next",
                    "target",
                ),
                copy_function=_copy2_best_effort,
                ignore_dangling_symlinks=True,
                symlinks=True,
            )
        elif materialize_playground and effective_source_type == "git":
            # Git clone — shallow
            import subprocess

            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth=1",
                    effective_source_path,
                    config.sandbox_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                return ProjectInitResponse(
                    success=False,
                    errors=[f"Git clone failed: {result.stderr[:500]}"],
                )
    except PermissionError:
        return ProjectInitResponse(
            success=False,
            errors=[f"Permission denied: cannot read {effective_source_path}"],
        )
    except shutil.Error as e:
        # Keep previous behavior readable, but tolerate transient missing-file entries.
        transient = []
        fatal = []
        for item in list(getattr(e, "args", [])[:1] or []):
            if isinstance(item, list):
                for triple in item:
                    if isinstance(triple, (list, tuple)) and len(triple) >= 3:
                        src = str(triple[0])
                        err = str(triple[2])
                        if "No such file or directory" in err:
                            transient.append(src)
                        else:
                            fatal.append(str(triple))
        if fatal:
            return ProjectInitResponse(
                success=False,
                errors=[f"Copy failed: {fatal[:2]}"],
            )
        skipped_copy_sources.extend(transient)
    except OSError as e:
        return ProjectInitResponse(
            success=False,
            errors=[f"Copy failed: {str(e)[:500]}"],
        )

    # Save config
    if not config.save():
        return ProjectInitResponse(success=False, errors=["Failed to save config"])

    try:
        from src.services.mcc_project_registry import upsert_project

        upsert_project(config, set_active=True)
    except Exception:
        pass

    # Initialize default session state
    _save_session_state(config.project_id, SessionState())

    if skipped_copy_sources:
        try:
            print(
                f"[MCC] project/init skipped {len(skipped_copy_sources)} transient files during copy "
                f"(source={effective_source_path})"
            )
        except Exception:
            pass

    return ProjectInitResponse(
        success=True,
        project_id=config.project_id,
        project_name=str(config.display_name or ""),
        execution_mode=str(config.execution_mode or "playground"),
        project_kind=str(config.project_kind or "user"),
        sandbox_path=config.sandbox_path,
    )


@router.get("/projects/list")
async def list_projects(
    include_hidden: bool = Query(False, description="Include non-user projects"),
):
    """
    MARKER_161.7.MULTIPROJECT.API.PROJECTS_LIST.V1
    List project registry summaries and active project pointer.
    """
    from src.services.mcc_project_registry import (
        ensure_registry_bootstrap,
        list_projects as _list,
    )

    ensure_registry_bootstrap()
    result = _list(include_hidden=bool(include_hidden))
    return {"success": True, **result}


@router.post("/projects/activate")
async def activate_project(req: ProjectActivateRequest):
    """
    MARKER_161.7.MULTIPROJECT.API.PROJECTS_ACTIVATE.V1
    Activate project context for subsequent MCC /init and DAG operations.
    """
    from src.services.mcc_project_registry import activate_project as _activate

    try:
        result = _activate(str(req.project_id or "").strip())
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to activate project: {e}")


# ──────────────────────────────────────────────────────────────
# DELETE /api/mcc/project — Remove project config (allows reconfigure)
# ──────────────────────────────────────────────────────────────


@router.delete("/project")
async def delete_project(
    project_id: str = Query("", description="Optional explicit project_id"),
):
    """
    Delete project config. Does NOT delete sandbox (use DELETE /api/mcc/sandbox).
    Allows reconfiguring with a new project.
    """
    from src.services.project_config import CONFIG_PATH, SESSION_STATE_PATH

    deleted = []
    config = _resolve_project_config(project_id)

    if config is not None:
        try:
            from src.services.mcc_project_registry import (
                remove_project as _remove_project,
            )

            _remove_project(str(config.project_id))
            deleted.append(f"registry:{config.project_id}")
        except Exception:
            pass

    for path in [CONFIG_PATH, SESSION_STATE_PATH]:
        if os.path.exists(path):
            os.remove(path)
            deleted.append(os.path.basename(path))

    return {"ok": True, "deleted": deleted}


# ──────────────────────────────────────────────────────────────
# MARKER_153.2B: Sandbox management endpoints
# ──────────────────────────────────────────────────────────────


class SandboxStatusResponse(BaseModel):
    exists: bool
    sandbox_path: str = ""
    file_count: int = 0
    used_gb: float = 0.0
    quota_gb: int = 10
    percent: float = 0.0
    warning: bool = False
    exceeded: bool = False


@router.get("/sandbox/status", response_model=SandboxStatusResponse)
async def sandbox_status(
    project_id: str = Query("", description="Optional explicit project_id"),
):
    """
    Get sandbox disk usage and quota status.
    Used by SandboxDropdown to show [Sandbox ✓ 2.1/10GB] or [No Sandbox].
    """
    config = _resolve_project_config(project_id)
    if config is None:
        return SandboxStatusResponse(exists=False)
    status = await _get_sandbox_status_cached(config)
    return SandboxStatusResponse(**status)


class SandboxRecreateRequest(BaseModel):
    force: bool = False  # Force recreate even if exists
    project_id: str = ""


@router.post("/sandbox/recreate")
async def sandbox_recreate(req: SandboxRecreateRequest):
    """
    Delete and recreate sandbox from source.
    Used when sandbox gets corrupted or user wants a fresh copy.
    """
    config = _resolve_project_config(req.project_id)
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    # Check if sandbox exists and force isn't set
    if config.sandbox_exists() and not req.force:
        return {
            "ok": False,
            "error": "Sandbox already exists. Use force=true to recreate.",
            "status": await _get_sandbox_status_cached(config),
        }

    # Delete existing sandbox
    if config.sandbox_exists():
        try:
            shutil.rmtree(config.sandbox_path)
        except OSError as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete sandbox: {e}"
            )

    # Recreate from source
    try:
        if config.source_type == "local":
            if not os.path.isdir(config.source_path):
                raise HTTPException(
                    status_code=400,
                    detail=f"Source path not found: {config.source_path}",
                )
            shutil.copytree(
                config.source_path,
                config.sandbox_path,
                ignore=shutil.ignore_patterns(
                    "node_modules",
                    ".git",
                    "__pycache__",
                    "*.pyc",
                    "dist",
                    "build",
                    ".next",
                    "target",
                ),
            )
        elif config.source_type == "git":
            import subprocess

            result = subprocess.run(
                ["git", "clone", "--depth=1", config.source_path, config.sandbox_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"Git clone failed: {result.stderr[:500]}",
                )
    except HTTPException:
        raise
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Recreate failed: {str(e)[:500]}")

    return {
        "ok": True,
        "status": await _get_sandbox_status_cached(config),
    }


@router.delete("/sandbox")
async def delete_sandbox(
    project_id: str = Query("", description="Optional explicit project_id"),
):
    """
    Delete sandbox directory (but keep project config).
    Sandbox can be recreated via POST /api/mcc/sandbox/recreate.
    """
    config = _resolve_project_config(project_id)
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    if not config.sandbox_exists():
        return {"ok": True, "message": "Sandbox already absent"}

    try:
        shutil.rmtree(config.sandbox_path)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete sandbox: {e}")

    return {"ok": True, "sandbox_path": config.sandbox_path}


@router.patch("/sandbox/quota")
async def update_quota(
    quota_gb: int,
    project_id: str = Query("", description="Optional explicit project_id"),
):
    """Update project quota (1-100 GB)."""
    if quota_gb < 1 or quota_gb > 100:
        raise HTTPException(status_code=400, detail="quota_gb must be 1-100")

    config = _resolve_project_config(project_id)
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    config.quota_gb = quota_gb
    if not config.save():
        raise HTTPException(status_code=500, detail="Failed to save config")

    return {
        "ok": True,
        "quota_gb": quota_gb,
        "status": await _get_sandbox_status_cached(config),
    }


# ──────────────────────────────────────────────────────────────
# MARKER_153.4F: Roadmap, Workflow Templates, Prefetch
# ──────────────────────────────────────────────────────────────


@router.get("/roadmap")
async def get_roadmap(
    project_id: str = Query("", description="Optional explicit project_id"),
):
    """
    Get the project roadmap DAG.
    Returns the saved roadmap or generates one if absent.
    """
    from src.services.roadmap_generator import RoadmapDAG, RoadmapGenerator

    config = _resolve_project_config(project_id)
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    dag = RoadmapDAG.load_for_project(config.project_id)
    if dag is None:
        # Auto-generate on first request
        dag = await RoadmapGenerator.analyze_project(config)

    return dag.to_frontend_format()


@router.get("/graph/condensed")
async def get_condensed_graph(
    project_id: str = Query("", description="Optional explicit project_id"),
    scope_path: str = Query("", description="Optional absolute/relative scope path"),
    max_nodes: int = Query(600, ge=50, le=5000, description="L2 node budget"),
    include_artifacts: bool = Query(False, description="Include artifact/chat in L0"),
    refresh: bool = Query(False, description="Bypass in-process condensed cache"),
):
    """
    MARKER_155.MODE_ARCH.V11.P1:
    Build backend layers for MCC architecture:
    - L0 raw module graph
    - L1 SCC-condensed DAG
    - L2 layered view graph
    """
    from src.services.mcc_scc_graph import build_condensed_graph

    config = _resolve_project_config(project_id)
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    resolved_scope = (scope_path or "").strip()
    if not resolved_scope:
        # MARKER_161.9.MULTIPROJECT.ISOLATION.SANDBOX_SCOPE_DEFAULT.V1
        resolved_scope = config.sandbox_path or config.source_path
    resolved_scope = os.path.abspath(os.path.expanduser(resolved_scope))

    if not os.path.isdir(resolved_scope):
        raise HTTPException(
            status_code=400, detail=f"Invalid scope_path: {resolved_scope}"
        )

    try:
        result = await asyncio.to_thread(
            build_condensed_graph,
            resolved_scope,
            int(max_nodes),
            bool(include_artifacts),
            bool(refresh),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to build condensed graph: {e}"
        )


@router.post("/roadmap/generate")
async def generate_roadmap(
    project_id: str = Query("", description="Optional explicit project_id"),
):
    """Regenerate roadmap from current sandbox state."""
    from src.services.roadmap_generator import RoadmapGenerator

    config = _resolve_project_config(project_id)
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    if not config.sandbox_exists():
        raise HTTPException(
            status_code=400, detail="Sandbox not found. Create sandbox first."
        )

    dag = await RoadmapGenerator.analyze_project(config)
    return {"ok": True, "node_count": len(dag.nodes), "edge_count": len(dag.edges)}


@router.get("/workflows")
async def list_workflows():
    """List all available workflow templates."""
    from src.services.architect_prefetch import WorkflowTemplateLibrary

    return {"templates": WorkflowTemplateLibrary.list_templates()}


@router.get("/workflow-catalog")
async def get_workflow_catalog():
    """
    MARKER_167.STATS_WORKFLOW.CATALOG_API.V1
    Unified MCC workflow catalog across banks.
    """
    return _build_workflow_catalog_payload()


@router.patch("/tasks/{task_id}")
async def update_mcc_task(task_id: str, body: MCCTaskUpdateRequest):
    """
    MARKER_175.0A.MCC.TASK_PATCH.V1
    Update MCC task metadata from TaskEditPopup.
    """
    board = _get_task_board_instance()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    updates = body.model_dump(exclude_none=True)
    allowed_fields = {
        "title",
        "description",
        "preset",
        "phase_type",
        "priority",
        "tags",
        "workflow_family",
        "project_id",
        "project_lane",
        "architecture_docs",
        "recon_docs",
        "closure_tests",
        "closure_files",
        "require_closure_proof",
    }
    updates = {key: value for key, value in updates.items() if key in allowed_fields}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    ok = board.update_task(task_id, **updates)
    if not ok:
        raise HTTPException(
            status_code=500, detail=f"Failed to update task '{task_id}'"
        )

    return {
        "success": True,
        "task_id": task_id,
        "task": board.get_task(task_id) or {**task, **updates},
    }


@router.post("/tasks/create-attached")
async def create_mcc_attached_task(body: MCCAttachedTaskRequest):
    board = _get_task_board_instance()
    payload = _derive_attached_task_payload(body.model_dump())
    task_id = board.add_task(**payload)
    task = board.get_task(task_id)
    result = {
        "success": True,
        "task_id": task_id,
        "task": task or {"id": task_id, **payload},
    }
    # MARKER_189.5A: Hint if project_id is unknown in registry
    project_id = str(payload.get("project_id") or "").strip()
    if project_id:
        from src.services.mcc_project_registry import list_projects
        known = list_projects(include_hidden=True)
        if not any(str(p.get("project_id", "")) == project_id for p in known.get("projects", [])):
            result["project_unknown"] = True
            result["suggested_action"] = "create_project"
            result["suggested_project_id"] = project_id
    return result


@router.post("/tasks/{task_id}/attach-node")
async def attach_mcc_task_to_node(task_id: str, body: MCCAttachedTaskRequest):
    board = _get_task_board_instance()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    updates = _derive_attached_task_payload(body.model_dump(), existing_task=task)
    ok = board.update_task(task_id, **updates)
    if not ok:
        raise HTTPException(
            status_code=500, detail=f"Failed to attach task '{task_id}'"
        )
    return {
        "success": True,
        "task_id": task_id,
        "task": board.get_task(task_id) or {**task, **updates},
    }


@router.post("/tasks/{task_id}/feedback")
async def submit_mcc_task_feedback(task_id: str, body: MCCTaskFeedbackRequest):
    """
    MARKER_175.0B.MCC.TASK_FEEDBACK.V1
    Store user feedback for MCC redo/approve/reject flow.
    """
    board = _get_task_board_instance()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    action = str(body.action or "redo").strip().lower()
    if action not in {"redo", "approve", "reject"}:
        raise HTTPException(
            status_code=400, detail="action must be redo, approve, or reject"
        )

    updates: Dict[str, Any] = {
        "feedback": str(body.feedback or "").strip(),
        "result_status": {"redo": 0.5, "approve": 1.0, "reject": 0.0}[action],
    }
    if action == "redo":
        updates["status"] = "pending"

    ok = board.update_task(task_id, **updates)
    if not ok:
        raise HTTPException(
            status_code=500, detail=f"Failed to update feedback for task '{task_id}'"
        )

    return {
        "success": True,
        "task_id": task_id,
        "action": action,
        "task": board.get_task(task_id) or {**task, **updates},
    }


# MARKER_176.3B: Apply pipeline results — user accepts output
@router.post("/tasks/{task_id}/apply")
async def apply_task_result(task_id: str):
    """Mark task result as applied (accepted by user)."""
    board = _get_task_board_instance()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    board.update_task(task_id, result_status="applied", status="done")
    updated = board.get_task(task_id)
    return {"success": True, "task": updated}


# MARKER_176.3B: Reject pipeline results — user wants redo with feedback
@router.post("/tasks/{task_id}/reject")
async def reject_task_result(task_id: str, body: dict = Body(...)):
    """Reject result and requeue task with user feedback."""
    board = _get_task_board_instance()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    feedback = body.get("feedback", "")
    old_desc = task.get("description", "")
    new_desc = f"{old_desc}\n\n[USER FEEDBACK]: {feedback}" if feedback else old_desc
    board.update_task(
        task_id, result_status="rejected", status="pending", description=new_desc
    )
    updated = board.get_task(task_id)
    return {"success": True, "task": updated}


# MARKER_176.1B: Create tasks from roadmap node
@router.post("/roadmap/{node_id}/create-tasks")
async def create_tasks_from_roadmap_node(
    node_id: str,
    project_id: str = Query("", description="Optional explicit project_id"),
):
    """
    Generate task board entries from a specific roadmap module node.
    Users click a roadmap node → drill to tasks → 'Create Tasks' button calls this.
    """
    from src.services.roadmap_generator import RoadmapDAG
    from src.services.roadmap_task_sync import generate_task_payloads_from_roadmap_node

    config = _resolve_project_config(project_id)
    resolved_project_id = str(
        getattr(config, "project_id", "") or str(project_id or "").strip()
    )
    dag = RoadmapDAG.load_for_project(resolved_project_id)
    if dag is None:
        raise HTTPException(
            status_code=404, detail="No roadmap found. Generate roadmap first."
        )

    # Find the target node in the roadmap DAG
    target_node = None
    frontend_data = dag.to_frontend_format()
    for node in frontend_data.get("nodes", []):
        ndata = node.get("data", {})
        if node.get("id") == node_id or ndata.get("id") == node_id:
            target_node = {**ndata, "id": node.get("id", node_id)}
            break

    if not target_node:
        raise HTTPException(
            status_code=404, detail=f"Roadmap node '{node_id}' not found"
        )

    active_project_id = str(resolved_project_id or getattr(dag, "project_id", "") or "")
    board = _get_task_board_instance()
    created_tasks = []
    module_name = target_node.get("label", target_node.get("id", node_id))
    payloads = generate_task_payloads_from_roadmap_node(
        dict(target_node),
        roadmap_id=str(getattr(dag, "project_id", "") or ""),
    )

    main_task_id = ""
    for payload in payloads:
        payload.setdefault("preset", "dragon_silver")
        payload.setdefault("priority", target_node.get("priority", 5))
        payload["tags"] = list(payload.get("tags") or []) + [f"roadmap:{node_id}"]
        payload["project_id"] = str(payload.get("project_id") or active_project_id)
        payload["project_lane"] = str(payload.get("project_lane") or node_id)
        task_id = board.add_task(**payload)
        created_tasks.append(task_id)
        if not main_task_id:
            main_task_id = task_id

    # If node has children/sub-modules, create subtasks
    children = target_node.get("children", [])
    for sub in children[:5]:
        sub_label = sub.get("label", sub.get("id", "subtask"))
        sub_id = board.add_task(
            title=f"Subtask: {sub_label}"[:100],
            description=sub.get("description", f"Sub-module of {module_name}"),
            priority=target_node.get("priority", 5),
            phase_type="build",
            preset="dragon_silver",
            tags=[f"roadmap:{node_id}", f"parent:{main_task_id}"],
            project_id=active_project_id,
            project_lane=str(sub.get("id") or node_id),
            roadmap_id=str(getattr(dag, "project_id", "") or ""),
            roadmap_node_id=str(sub.get("id") or node_id),
            roadmap_lane=str(sub.get("layer") or target_node.get("layer") or "core"),
            roadmap_title=str(sub_label),
            task_origin="roadmap_sync",
            workflow_selection_origin="roadmap_sync",
        )
        created_tasks.append(sub_id)

    return {
        "success": True,
        "tasks": created_tasks,
        "count": len(created_tasks),
        "node_id": node_id,
    }


# MARKER_176.1B_END


@router.get("/tasks/{task_id}/workflow-binding")
async def get_task_workflow_binding(task_id: str):
    board = _get_task_board_instance()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {
        "success": True,
        "task_id": task_id,
        "binding": _resolve_task_workflow_binding(task),
    }


@router.put("/tasks/{task_id}/workflow-binding")
async def update_task_workflow_binding(task_id: str, body: "WorkflowBindingRequest"):
    """
    MARKER_167.STATS_WORKFLOW.TASK_BINDING.V1
    Persist explicit workflow binding on task metadata.
    """
    board = _get_task_board_instance()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    workflow_id = str(body.workflow_id or "").strip()
    if not workflow_id:
        raise HTTPException(status_code=400, detail="workflow_id is required")

    updates = {
        "workflow_id": workflow_id,
        "workflow_bank": str(body.workflow_bank or "core").strip() or "core",
        "workflow_family": str(body.workflow_family or workflow_id).strip()
        or workflow_id,
        "workflow_selection_origin": str(
            body.selection_origin or "user-selected"
        ).strip()
        or "user-selected",
        "team_profile": str(
            body.team_profile
            or task.get("team_profile")
            or task.get("preset")
            or "dragon_silver"
        ).strip()
        or "dragon_silver",
    }
    ok = board.update_task(task_id, **updates)
    if not ok:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update task '{task_id}' workflow binding",
        )
    next_task = board.get_task(task_id) or {**task, **updates}
    return {
        "success": True,
        "task_id": task_id,
        "binding": _resolve_task_workflow_binding(next_task),
    }


@router.get("/workflow-contract/{workflow_family}")
async def get_workflow_contract(workflow_family: str):
    contract = await _resolve_workflow_contract(workflow_family)
    if contract is None:
        raise HTTPException(
            status_code=404, detail=f"Workflow contract '{workflow_family}' not found"
        )
    return {
        "success": True,
        "workflow_family": str(contract.get("workflow_family") or workflow_family),
        "contract": contract,
    }


@router.get("/localguys/operator-methods")
async def list_localguys_operator_methods():
    rows = []
    for workflow_family, meta in sorted(_LOCALGUYS_OPERATOR_METHODS.items()):
        contract = await _resolve_workflow_contract(workflow_family)
        if contract is None:
            continue
        rows.append(
            {
                "workflow_family": workflow_family,
                "source_family": str(meta.get("source_family") or ""),
                "method": str(meta.get("method") or ""),
                "command_template": str(meta.get("command_template") or ""),
                "roles": list(contract.get("roles") or []),
                "steps": list(contract.get("steps") or []),
            }
        )
    return {
        "success": True,
        "count": len(rows),
        "methods": rows,
    }


@router.get("/localguys/benchmark-summary")
async def get_localguys_benchmark_summary(
    runtime_name: str = "",
    workflow_family: str = "",
    task_id: str = "",
    limit: int = 20,
):
    registry = _get_localguys_run_registry()
    run_summary = registry.summarize_runs(
        workflow_family=str(workflow_family or "").strip(),
        task_id=str(task_id or "").strip(),
        limit=max(1, min(int(limit or 20), 100)),
    )
    benchmark_rows = _get_mcc_benchmark_store().list_records(
        runtime_name=str(runtime_name or "").strip(),
        workflow_family=str(workflow_family or "").strip(),
        task_id=str(task_id or "").strip(),
        limit=max(1, min(int(limit or 20), 100)),
    )
    status_counts = dict(run_summary.get("status_counts") or {})
    model_counts = dict(run_summary.get("model_counts") or {})
    runtime_counts: Dict[str, int] = {}
    runtime_counts["localguys"] = int(run_summary.get("count") or 0)
    runtime_total = int(run_summary.get("avg_runtime_ms") or 0) * int(
        run_summary.get("count") or 0
    )
    missing_total = float(run_summary.get("avg_artifact_missing_count") or 0.0) * int(
        run_summary.get("count") or 0
    )
    required_total = float(run_summary.get("avg_required_artifact_count") or 0.0) * int(
        run_summary.get("count") or 0
    )
    success_total = float(run_summary.get("success_rate") or 0.0) * int(
        run_summary.get("count") or 0
    )

    merged_recent = list(run_summary.get("recent_runs") or [])
    for row in benchmark_rows:
        runtime = str(row.get("runtime_name") or "benchmark").strip() or "benchmark"
        runtime_counts[runtime] = runtime_counts.get(runtime, 0) + 1
        status = str(row.get("run_status") or "measured").strip() or "measured"
        status_counts[status] = status_counts.get(status, 0) + 1
        runtime_total += int(row.get("runtime_ms") or 0)
        missing_total += float(row.get("artifact_missing_count") or 0.0)
        required_total += float(row.get("required_artifact_count") or 0.0)
        success_total += float(row.get("success_rate") or 0.0)
        merged_recent.append(dict(row))

    count = int(run_summary.get("count") or 0) + len(benchmark_rows)
    summary = {
        **run_summary,
        "count": count,
        "status_counts": status_counts,
        "model_counts": model_counts,
        "runtime_counts": runtime_counts,
        "avg_runtime_ms": int(runtime_total / count) if count else 0,
        "avg_artifact_missing_count": round(missing_total / count, 2) if count else 0.0,
        "avg_required_artifact_count": round(required_total / count, 2)
        if count
        else 0.0,
        "success_rate": round(success_total / count, 2) if count else 0.0,
        "recent_runs": sorted(
            merged_recent,
            key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""),
            reverse=True,
        )[: max(1, min(int(limit or 20), 100))],
    }
    return {
        "success": True,
        "summary": summary,
    }


@router.post("/benchmarks")
async def create_benchmark_record(payload: "BenchmarkRecordRequest"):
    record = _get_mcc_benchmark_store().add_record(payload.model_dump())
    return {
        "success": True,
        "record": record,
    }


@router.get("/tasks/{task_id}/workflow-contract")
async def get_task_workflow_contract(task_id: str):
    board = _get_task_board_instance()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    binding = _resolve_task_workflow_binding(task)
    workflow_family = str(
        binding.get("workflow_family") or binding.get("workflow_id") or ""
    ).strip()
    contract = await _resolve_workflow_contract(workflow_family)
    if contract is None:
        raise HTTPException(
            status_code=404, detail=f"Workflow contract '{workflow_family}' not found"
        )
    return {
        "success": True,
        "task_id": task_id,
        "binding": binding,
        "contract": contract,
    }


@router.get("/tasks/{task_id}/context-packet")
async def get_task_context_packet(task_id: str):
    from src.services.roadmap_task_sync import build_task_context_packet
    from src.services.mcc_local_run_registry import get_localguys_run_registry

    board = _get_task_board_instance()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    binding = _resolve_task_workflow_binding(task)
    workflow_family = str(
        binding.get("workflow_family") or binding.get("workflow_id") or ""
    ).strip()
    contract = await _resolve_workflow_contract(workflow_family)
    history = (
        board.get_task_history(task_id)
        if hasattr(board, "get_task_history")
        else list(task.get("status_history") or [])
    )
    latest_run = get_localguys_run_registry().get_latest_for_task(task_id)
    packet = build_task_context_packet(
        task,
        workflow_binding=binding,
        workflow_contract=contract or {},
        task_history=history,
        localguys_run=latest_run or {},
    )
    return {
        "success": True,
        "task_id": task_id,
        "packet": packet,
    }


def _validate_localguys_run_update(
    body: "LocalguysRunUpdateRequest",
    contract: Dict[str, Any],
) -> None:
    allowed_statuses = {"queued", "running", "reviewing", "done", "blocked", "failed"}
    if body.status is not None and str(body.status).strip() not in allowed_statuses:
        raise HTTPException(status_code=400, detail="invalid localguys run status")

    steps = [
        str(step).strip()
        for step in list(contract.get("steps") or [])
        if str(step).strip()
    ]
    if body.current_step is not None and str(body.current_step).strip() not in steps:
        raise HTTPException(status_code=400, detail="invalid localguys run step")

    roles = [
        str(role).strip()
        for role in list(contract.get("roles") or [])
        if str(role).strip()
    ]
    if body.active_role is not None and str(body.active_role).strip() not in roles:
        raise HTTPException(status_code=400, detail="invalid localguys run role")


def _build_localguys_runtime_guard(
    run: Dict[str, Any], contract: Dict[str, Any]
) -> Dict[str, Any]:
    current_step = str(run.get("current_step") or "").strip()
    metadata = dict(run.get("metadata") or {})
    stage_tool_policy = dict(contract.get("stage_tool_policy") or {})
    write_opt_ins = dict(contract.get("write_opt_ins") or {})
    max_turns = int(contract.get("max_turns") or 0)
    turn_count = max(0, int(metadata.get("turn_count") or 0))
    return {
        "workflow_family": str(
            contract.get("workflow_family") or run.get("workflow_family") or ""
        ).strip(),
        "current_step": current_step,
        "allowed_tools": list(
            stage_tool_policy.get(current_step) or contract.get("allowed_tools") or []
        ),
        "write_opt_ins": write_opt_ins,
        "verification_target": str(contract.get("verification_target") or "").strip(),
        "sandbox_mode": str(
            (contract.get("sandbox_policy") or {}).get("mode") or ""
        ).strip(),
        "max_turns": max_turns,
        "turn_count": turn_count,
        "remaining_turns": max(0, max_turns - turn_count) if max_turns > 0 else 0,
        "idle_nudge_template": str(contract.get("idle_nudge_template") or "").strip(),
    }


def _prepare_localguys_runtime_metadata(
    body: "LocalguysRunUpdateRequest",
    *,
    run: Dict[str, Any],
    contract: Dict[str, Any],
) -> Dict[str, Any]:
    incoming = dict(body.metadata or {})
    metadata = dict(run.get("metadata") or {})
    current_step = str(body.current_step or run.get("current_step") or "").strip()
    stage_tool_policy = dict(contract.get("stage_tool_policy") or {})
    allowed_tools = _normalize_str_list(
        stage_tool_policy.get(current_step) or contract.get("allowed_tools") or []
    )
    used_tools = _normalize_str_list(incoming.get("used_tools"))
    disallowed_tools = [tool for tool in used_tools if tool not in allowed_tools]
    if disallowed_tools:
        raise HTTPException(
            status_code=400,
            detail=f"disallowed_tools_for_step:{current_step}:{', '.join(disallowed_tools)}",
        )

    write_opt_ins = dict(contract.get("write_opt_ins") or {})
    write_attempts = _normalize_str_list(incoming.get("write_attempts"))
    disallowed_writes = [
        scope for scope in write_attempts if not bool(write_opt_ins.get(scope))
    ]
    if disallowed_writes:
        raise HTTPException(
            status_code=400,
            detail=f"write_scope_not_allowed:{', '.join(disallowed_writes)}",
        )

    turn_increment = max(0, int(incoming.get("turn_increment") or 0))
    turn_count = max(0, int(metadata.get("turn_count") or 0)) + turn_increment
    max_turns = int(contract.get("max_turns") or 0)
    if max_turns > 0 and turn_count > max_turns:
        raise HTTPException(
            status_code=400, detail=f"max_turns_exceeded:{turn_count}/{max_turns}"
        )

    if turn_increment > 0:
        incoming["turn_count"] = turn_count
    elif "turn_count" not in incoming and "turn_count" in metadata:
        incoming["turn_count"] = int(metadata.get("turn_count") or 0)
    return incoming


@router.post("/tasks/{task_id}/localguys-run")
async def start_localguys_run(
    task_id: str, body: "LocalguysRunStartRequest" = Body(default=None)
):
    board = _get_task_board_instance()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    body = body or LocalguysRunStartRequest()
    binding = _resolve_task_workflow_binding(task)
    workflow_family = (
        str(body.workflow_family or "").strip()
        or str(
            binding.get("workflow_family") or binding.get("workflow_id") or ""
        ).strip()
    )
    contract = await _resolve_workflow_contract(workflow_family)
    if contract is None:
        raise HTTPException(
            status_code=404, detail=f"Workflow contract '{workflow_family}' not found"
        )

    preset = (
        str(
            body.preset
            or task.get("team_profile")
            or task.get("preset")
            or "dragon_silver"
        ).strip()
        or "dragon_silver"
    )
    task_description = (
        str(body.task_description or "").strip()
        or str(task.get("description") or task.get("title") or "").strip()
    )
    source_branch = str(body.source_branch or "main").strip() or "main"

    try:
        playground = await _create_localguys_playground(
            task_description=task_description,
            preset=preset,
            source_branch=source_branch,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"playground creation failed: {exc}"
        ) from exc

    registry = _get_localguys_run_registry()
    run = registry.create_run(
        task_id=task_id,
        workflow_family=workflow_family,
        contract=contract,
        playground=playground,
        task_snapshot=task,
    )
    return {
        "success": True,
        "task_id": task_id,
        "binding": binding,
        "contract": contract,
        "runtime_guard": _build_localguys_runtime_guard(run, contract),
        "run": run,
    }


@router.get("/tasks/{task_id}/localguys-run")
async def get_latest_localguys_run(task_id: str):
    board = _get_task_board_instance()
    task = board.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    registry = _get_localguys_run_registry()
    run = registry.get_latest_for_task(task_id)
    if run is None:
        raise HTTPException(
            status_code=404, detail=f"No localguys run found for task '{task_id}'"
        )
    contract = await _resolve_workflow_contract(str(run.get("workflow_family") or ""))
    return {
        "success": True,
        "task_id": task_id,
        "runtime_guard": _build_localguys_runtime_guard(run, contract or {}),
        "run": run,
    }


@router.get("/localguys-runs/{run_id}")
async def get_localguys_run(run_id: str):
    registry = _get_localguys_run_registry()
    run = registry.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=404, detail=f"Localguys run '{run_id}' not found"
        )
    contract = await _resolve_workflow_contract(str(run.get("workflow_family") or ""))
    return {
        "success": True,
        "runtime_guard": _build_localguys_runtime_guard(run, contract or {}),
        "run": run,
    }


@router.patch("/localguys-runs/{run_id}")
async def update_localguys_run(run_id: str, body: "LocalguysRunUpdateRequest"):
    registry = _get_localguys_run_registry()
    run = registry.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=404, detail=f"Localguys run '{run_id}' not found"
        )

    contract = await _resolve_workflow_contract(str(run.get("workflow_family") or ""))
    if contract is None:
        raise HTTPException(
            status_code=404, detail="Workflow contract for localguys run not found"
        )
    _validate_localguys_run_update(body, contract)
    update_metadata = _prepare_localguys_runtime_metadata(
        body, run=run, contract=contract
    )

    updated = registry.update_run(
        run_id,
        status=body.status,
        current_step=body.current_step,
        active_role=body.active_role,
        model_id=body.model_id,
        failure_reason=body.failure_reason,
        metadata=update_metadata,
    )
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"Localguys run '{run_id}' not found"
        )

    if str(body.status or "").strip() == "done":
        manifest = registry.validate_required_artifacts(run_id)
        missing = list((manifest or {}).get("missing") or [])
        if missing:
            registry.update_run(
                run_id,
                status="blocked",
                failure_reason=f"required_artifact_missing: {', '.join(missing)}",
            )
            raise HTTPException(
                status_code=400,
                detail=f"required_artifact_missing: {', '.join(missing)}",
            )
        updated = registry.get_run(run_id) or updated

    return {
        "success": True,
        "runtime_guard": _build_localguys_runtime_guard(updated, contract),
        "run": updated,
    }


@router.put("/localguys-runs/{run_id}/artifacts/{artifact_name:path}")
async def write_localguys_artifact(
    run_id: str,
    artifact_name: str,
    body: "LocalguysArtifactWriteRequest",
):
    registry = _get_localguys_run_registry()
    run = registry.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=404, detail=f"Localguys run '{run_id}' not found"
        )
    contract = await _resolve_workflow_contract(str(run.get("workflow_family") or ""))
    if contract is None:
        raise HTTPException(
            status_code=404, detail="Workflow contract for localguys run not found"
        )
    if not bool(
        (contract.get("write_opt_ins") or {}).get("playground_artifacts", True)
    ):
        raise HTTPException(
            status_code=400, detail="write_scope_not_allowed:playground_artifacts"
        )
    artifact = registry.write_artifact(
        run_id,
        artifact_name,
        body.content,
        metadata=body.metadata,
    )
    if artifact is None:
        raise HTTPException(
            status_code=404, detail=f"Localguys run '{run_id}' not found"
        )
    run = registry.get_run(run_id)
    return {
        "success": True,
        "artifact": artifact,
        "runtime_guard": _build_localguys_runtime_guard(run, contract),
        "run": run,
    }


@router.get("/workflows/{workflow_key}")
async def get_workflow(workflow_key: str):
    """Get a specific workflow template by key."""
    from src.services.architect_prefetch import WorkflowTemplateLibrary

    tpl = WorkflowTemplateLibrary.get_template(workflow_key)
    if tpl is None:
        raise HTTPException(
            status_code=404, detail=f"Workflow template '{workflow_key}' not found"
        )
    return tpl


class PrefetchRequest(BaseModel):
    task_description: str
    task_type: str = ""
    complexity: int = 5
    project_id: str = ""


class WorkflowBindingRequest(BaseModel):
    workflow_bank: str = "core"
    workflow_id: str
    workflow_family: str = ""
    team_profile: str = ""
    selection_origin: str = "user-selected"


class LocalguysRunStartRequest(BaseModel):
    workflow_family: str = ""
    preset: str = ""
    task_description: str = ""
    source_branch: str = "main"


class LocalguysRunUpdateRequest(BaseModel):
    status: Optional[str] = None
    current_step: Optional[str] = None
    active_role: Optional[str] = None
    model_id: Optional[str] = None
    failure_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LocalguysArtifactWriteRequest(BaseModel):
    content: str = ""
    metadata: Optional[Dict[str, Any]] = None


class BenchmarkRecordRequest(BaseModel):
    runtime_name: str
    workflow_family: str = ""
    task_id: str = ""
    run_status: str = "measured"
    device_profile: str = ""
    accelerator: str = ""
    cold_start_ms: int = 0
    avg_runtime_ms: int = 0
    runtime_ms: int = 0
    artifact_missing_count: int = 0
    required_artifact_count: int = 0
    artifact_present_count: int = 0
    success_rate: float = 0.0
    notes: str = ""


class WorkflowMycoHintRequest(BaseModel):
    workflow_bank: str = "core"
    workflow_id: str = ""
    workflow_family: str = ""
    role: str = ""
    task_label: str = ""
    scope: str = "task"
    focus: Dict[str, Any] = {}


class PredictGraphRequest(BaseModel):
    project_id: str = ""
    scope_path: str = ""
    max_nodes: int = 600
    max_predicted_edges: int = 120
    include_artifacts: bool = False
    min_confidence: float = 0.55
    focus_node_ids: List[str] = []
    jepa_provider: str = "auto"  # auto|runtime|embedding|deterministic
    jepa_runtime_module: str = ""
    jepa_strict: bool = False


class PredictRuntimeHealthResponse(BaseModel):
    ok: bool
    enabled: bool
    embed_url: str
    health_url: str
    detail: str
    backend: str
    backend_detail: str
    runtime_module: str


class BuildDesignGraphRequest(BaseModel):
    # MARKER_161.TRM.API.BUILD_DESIGN_INPUT.V1:
    # Phase-161 extension point for TRM policy/config payload (kept disabled by default).
    project_id: str = ""
    scope_path: str = ""
    max_nodes: int = 600
    include_artifacts: bool = False
    problem_statement: str = ""
    target_outcome: str = ""
    use_predictive_overlay: bool = True
    max_predicted_edges: int = 120
    min_confidence: float = 0.55
    trm_profile: str = "off"
    trm_policy: Dict[str, Any] = {}


class BuildDesignFromArrayRequest(BaseModel):
    """
    MARKER_155.ARCHITECT_BUILD.ARRAY_API.V1
    Generic array payload for algorithmic offload DAG build.

    MARKER_161.TRM.API.BUILD_FROM_ARRAY_INPUT.V1:
    Phase-161 extension point for TRM adapter policy over arbitrary record/relation arrays.
    """

    scope_name: str = "array_scope"
    records: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    max_nodes: int = 600
    use_predictive_overlay: bool = False
    max_predicted_edges: int = 120
    min_confidence: float = 0.55
    trm_profile: str = "off"
    trm_policy: Dict[str, Any] = {}


class MCCScopedFileSearchRequest(BaseModel):
    query: str
    project_id: str = ""
    limit: int = 20
    mode: str = "keyword"  # keyword|filename
    scope_path: str = ""


class LayoutPreferenceUpdateRequest(BaseModel):
    user_id: str = "danila"
    scope_key: str
    profile: Dict[str, Any]


class MycoHiddenReindexRequest(BaseModel):
    max_files: int = 240
    max_chunks: int = 2400


class MycoContextRequest(BaseModel):
    user_id: str = "danila"
    project_id: str = ""
    focus: Dict[str, Any] = {}


class CreateDagVersionRequest(BaseModel):
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.API.V1
    Persist DAG build variant for compare/select workflow.
    """

    project_id: str = ""
    dag_payload: Dict[str, Any]
    name: str = ""
    author: str = "architect"
    source: str = "manual"
    build_meta: Dict[str, Any] = {}
    markers: List[str] = []
    set_primary: bool = False


class SetPrimaryDagVersionRequest(BaseModel):
    project_id: str = ""
    set_primary: bool = True


class DagCompareVariantRequest(BaseModel):
    # MARKER_161.TRM.API.AUTO_COMPARE_INPUT.V1:
    # Phase-161 extension point for TRM profile toggles in compare variants.
    name: str = ""
    max_nodes: int = 600
    use_predictive_overlay: bool = False
    max_predicted_edges: int = 120
    min_confidence: float = 0.55
    problem_statement: str = ""
    target_outcome: str = ""
    trm_profile: str = "off"
    trm_policy: Dict[str, Any] = {}


class DagAutoCompareRequest(BaseModel):
    """
    MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.API.V1
    Auto-run several DAG variants and rank them by scorecard.
    """

    project_id: str = ""
    source_kind: str = "scope"  # scope|array
    scope_path: str = ""
    include_artifacts: bool = False
    scope_name: str = "array_scope"
    records: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    default_max_nodes: int = 600
    variants: List[DagCompareVariantRequest] = []
    persist_versions: bool = True
    set_primary_best: bool = False


def _workflow_required_tools(workflow_family: str, workflow_bank: str) -> List[str]:
    family = str(workflow_family or "").strip().lower()
    bank = str(workflow_bank or "").strip().lower()
    if bank == "n8n":
        return ["workflow bank", "tasks", "context"]
    if bank == "comfyui":
        return ["workflow bank", "context", "artifacts"]
    if family in {"mycelium_pipeline", "bmad_default"}:
        return ["tasks", "context", "stats", "balance"]
    if family == "ralph_loop":
        return ["context", "tasks", "stats"]
    if family == "g3_critic_coder":
        return ["context", "tasks", "stats", "chat"]
    return ["context", "tasks", "stats"]


def _role_required_tools(role: str) -> List[str]:
    r = str(role or "").strip().lower()
    if r == "architect":
        return ["context", "tasks", "stats"]
    if r == "coder":
        return ["context", "tasks", "artifacts"]
    if r in {"verifier", "eval"}:
        return ["context", "stats", "tasks"]
    if r in {"researcher", "scout"}:
        return ["context", "search", "tasks"]
    return []


def _project_context_tools(focus: Dict[str, Any]) -> List[str]:
    graph_kind = str((focus or {}).get("graphKind") or "").strip().lower()
    nav_level = str((focus or {}).get("navLevel") or "").strip().lower()
    tools: List[str] = []
    if nav_level == "workflow":
        tools.append("chat")
    if graph_kind in {"project_task", "task_workflow"}:
        tools.append("stream")
    return tools


def _dedupe_keep_order(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _with_trm_contract_meta(
    result: Dict[str, Any], trm_profile: str, trm_policy: Dict[str, Any]
) -> Dict[str, Any]:
    """
    MARKER_161.TRM.CONFIG.CONTRACT.V1
    W1 contract extension only:
    - accepts TRM policy/profile inputs
    - publishes stable response metadata
    - does not mutate DAG behavior yet
    """
    out = dict(result or {})
    if isinstance(out.get("trm_meta"), dict):
        out["graph_source"] = str(
            out.get("graph_source")
            or ("trm_refined" if bool(out["trm_meta"].get("applied")) else "baseline")
        )
        return out

    policy = resolve_trm_policy(trm_profile=trm_profile, trm_policy=trm_policy)
    out["graph_source"] = str(out.get("graph_source") or "baseline")
    out["trm_meta"] = {
        "status": "disabled",
        "enabled": False,
        "applied": False,
        "profile": str(policy.get("profile") or "off"),
        "policy": policy,
        "reason": "phase161_w1_contract_only",
        "markers": ["MARKER_161.TRM.CONFIG.CONTRACT.V1"],
    }
    return out


def _resolve_project_id_for_versions(project_id: str = "") -> str:
    requested = str(project_id or "").strip()
    config = _resolve_project_config(requested)
    if config and config.project_id:
        return str(config.project_id)
    if requested:
        return requested
    return "default_project"


@router.post("/prefetch")
async def run_prefetch(req: PrefetchRequest):
    """
    Run the Architect Prefetch Pipeline.
    Returns context for pipeline injection.
    """
    from src.services.architect_prefetch import ArchitectPrefetch
    from dataclasses import asdict

    config = _resolve_project_config(req.project_id)
    ctx = ArchitectPrefetch.prepare(
        task_description=req.task_description,
        task_type=req.task_type,
        complexity=req.complexity,
        config=config,
    )
    payload = asdict(ctx)
    payload["diagnostics"] = {
        "workflow_selection": {
            "workflow_id": str(ctx.workflow_id or ""),
            "workflow_name": str(ctx.workflow_name or ""),
            "reinforcement": list(ctx.workflow_reinforcement or []),
            "reinforcement_policy": dict(ctx.workflow_reinforcement_policy or {}),
            "reason": (
                "openhands_reinforcement_enabled"
                if bool((ctx.workflow_reinforcement_policy or {}).get("enabled"))
                else "base_family_only"
            ),
        }
    }
    return payload


@router.post("/search/file")
async def mcc_scoped_file_search(req: MCCScopedFileSearchRequest):
    """
    MARKER_165.MCC.CONTEXT_SEARCH.API_SCOPED_FILE_ROUTE.V1
    Scoped file search for MCC Context window.
    """
    from src.search.file_search_service import search_files

    config = _resolve_project_config(req.project_id)
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    sandbox_scope = (
        _norm_abs(str(config.sandbox_path or "").strip())
        if str(config.sandbox_path or "").strip()
        else ""
    )
    source_scope = (
        _norm_abs(str(config.source_path or "").strip())
        if str(config.source_path or "").strip()
        else ""
    )
    # MARKER_165.MCC.CONTEXT_SEARCH.ACTIVE_SCOPE_FALLBACK.V1
    # Prefer sandbox, but gracefully fallback to source when sandbox was not materialized yet.
    base_scope = ""
    if sandbox_scope and os.path.isdir(sandbox_scope):
        base_scope = sandbox_scope
    elif source_scope and os.path.isdir(source_scope):
        base_scope = source_scope
    if not base_scope:
        raise HTTPException(status_code=400, detail="No active project scope available")

    resolved_scope = str(req.scope_path or "").strip()
    resolved_scope = _norm_abs(resolved_scope) if resolved_scope else base_scope
    if not os.path.isdir(resolved_scope):
        raise HTTPException(
            status_code=400, detail=f"Invalid scope_path: {resolved_scope}"
        )

    # MARKER_165.MCC.CONTEXT_SEARCH.SCOPE_GUARD.V1
    # Prevent scope escape outside active project boundary.
    if os.path.commonpath([base_scope, resolved_scope]) != base_scope:
        raise HTTPException(
            status_code=400,
            detail=f"scope_path must be inside active project scope: {base_scope}",
        )

    safe_limit = max(1, min(int(req.limit or 20), 100))
    mode = (
        "filename" if str(req.mode or "").strip().lower() == "filename" else "keyword"
    )
    payload = await asyncio.to_thread(
        search_files,
        query=str(req.query or ""),
        limit=safe_limit,
        mode=mode,
        scope_roots=[resolved_scope],
    )

    rows = list((payload or {}).get("results") or [])
    filtered: List[Dict[str, Any]] = []
    for row in rows:
        path = str(row.get("path") or "").strip()
        if not path:
            continue
        try:
            path_abs = _norm_abs(path)
            if os.path.commonpath([resolved_scope, path_abs]) != resolved_scope:
                continue
        except Exception:
            continue
        filtered.append(row)
        if len(filtered) >= safe_limit:
            break

    # MARKER_165.MCC.CONTEXT_SEARCH.PATH_FILTER.V1
    out = dict(payload or {})
    out["success"] = bool(out.get("success", True))
    out["results"] = filtered
    out["count"] = len(filtered)
    out["scope_root"] = resolved_scope
    out["mode"] = mode
    out["marker"] = "MARKER_165.MCC.CONTEXT_SEARCH.API_SCOPED_FILE_ROUTE.V1"
    return out


@router.get("/directory-tree")
async def get_mcc_directory_tree(
    project_id: str = Query("", description="Optional explicit project_id"),
    path: str = Query(
        "", description="Directory path relative to active project scope"
    ),
    depth: int = Query(4, ge=1, le=8),
    limit: int = Query(200, ge=1, le=1000),
):
    config = _resolve_project_config(project_id)
    base_scope = _active_project_scope_root(config)
    if not base_scope:
        raise HTTPException(status_code=400, detail="No active project scope available")
    resolved_path = _resolve_project_scope_path(base_scope, path)
    tree = await asyncio.to_thread(
        _build_directory_tree,
        resolved_path,
        base_scope,
        depth=int(depth),
        limit=int(limit),
    )
    return {
        "success": True,
        "scope_root": base_scope,
        "path": tree.get("path", ""),
        "tree": tree,
    }


@router.post("/graph/predict")
async def predict_graph_overlay(req: PredictGraphRequest):
    """
    MARKER_155.MODE_ARCH.V11.P15:
    Produce predictive overlay edges for MCC single-canvas graph.
    Current implementation is deterministic heuristic (JEPA contract stub).
    """
    from src.services.mcc_predictive_overlay import build_predictive_overlay
    from src.services.mcc_jepa_adapter import JepaRuntimeUnavailableError

    config = _resolve_project_config(req.project_id)
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    resolved_scope = (req.scope_path or "").strip()
    if not resolved_scope:
        # MARKER_161.9.MULTIPROJECT.ISOLATION.SANDBOX_SCOPE_DEFAULT.V1
        resolved_scope = config.sandbox_path or config.source_path
    resolved_scope = os.path.abspath(os.path.expanduser(resolved_scope))

    if not os.path.isdir(resolved_scope):
        raise HTTPException(
            status_code=400, detail=f"Invalid scope_path: {resolved_scope}"
        )

    max_nodes = max(50, min(int(req.max_nodes), 5000))
    max_predicted_edges = max(0, min(int(req.max_predicted_edges), 2000))
    min_conf = max(0.0, min(float(req.min_confidence), 0.99))

    try:
        result = await asyncio.to_thread(
            build_predictive_overlay,
            resolved_scope,
            max_nodes,
            max_predicted_edges,
            bool(req.include_artifacts),
            min_conf,
            [str(x) for x in (req.focus_node_ids or []) if str(x).strip()],
            str(req.jepa_provider or "auto"),
            str(req.jepa_runtime_module or ""),
            bool(req.jepa_strict),
        )
        return result
    except JepaRuntimeUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to build predictive overlay: {e}"
        )


@router.get(
    "/graph/predict/runtime-health", response_model=PredictRuntimeHealthResponse
)
async def predict_graph_runtime_health(
    runtime_module: str = Query(
        "src.services.jepa_runtime", description="Runtime module path"
    ),
    force: bool = Query(False, description="Force health probe, bypass short cache"),
):
    """
    MARKER_155.P3_4.JEPA_RUNTIME_HEALTH_ROUTE.V1
    Operational health endpoint for JEPA runtime bridge used by predictive overlay.
    """
    module_path = str(runtime_module or "").strip() or "src.services.jepa_runtime"
    try:
        import importlib

        mod = importlib.import_module(module_path)
        health_fn = getattr(mod, "runtime_health", None)
        if not callable(health_fn):
            raise HTTPException(
                status_code=400,
                detail=f"runtime module has no runtime_health(): {module_path}",
            )

        data = health_fn(bool(force))  # type: ignore[misc]
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=500,
                detail=f"invalid runtime health payload from: {module_path}",
            )

        return PredictRuntimeHealthResponse(
            ok=bool(data.get("ok")),
            enabled=bool(data.get("enabled")),
            embed_url=str(data.get("embed_url") or ""),
            health_url=str(data.get("health_url") or ""),
            detail=str(data.get("detail") or ""),
            backend=str(data.get("backend") or ""),
            backend_detail=str(data.get("backend_detail") or ""),
            runtime_module=module_path,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"runtime health check failed: {e}")


@router.post("/graph/build-design")
async def build_design_graph(req: BuildDesignGraphRequest):
    """
    MARKER_155.ARCHITECT_BUILD.V1:
    Build architecture Design DAG package for Architect flow:
    - deterministic runtime graph
    - planning-ready design graph
    - optional JEPA-compatible predictive overlay
    - verifier/eval diagnostics
    """
    from src.services.mcc_architect_builder import build_design_dag

    config = _resolve_project_config(req.project_id)
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    resolved_scope = (req.scope_path or "").strip()
    if not resolved_scope:
        # MARKER_161.9.MULTIPROJECT.ISOLATION.SANDBOX_SCOPE_DEFAULT.V1
        resolved_scope = config.sandbox_path or config.source_path
    resolved_scope = os.path.abspath(os.path.expanduser(resolved_scope))

    if not os.path.isdir(resolved_scope):
        raise HTTPException(
            status_code=400, detail=f"Invalid scope_path: {resolved_scope}"
        )

    try:
        result = await asyncio.to_thread(
            build_design_dag,
            resolved_scope,
            int(req.max_nodes),
            bool(req.include_artifacts),
            str(req.problem_statement or ""),
            str(req.target_outcome or ""),
            bool(req.use_predictive_overlay),
            int(req.max_predicted_edges),
            float(req.min_confidence),
            str(req.trm_profile or "off"),
            dict(req.trm_policy or {}),
        )
        return _with_trm_contract_meta(
            result=dict(result or {}),
            trm_profile=str(req.trm_profile or "off"),
            trm_policy=dict(req.trm_policy or {}),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to build design graph: {e}"
        )


@router.post("/graph/build-design/from-array")
async def build_design_graph_from_array(req: BuildDesignFromArrayRequest):
    """
    MARKER_155.ARCHITECT_BUILD.ARRAY_API.V1
    Build Design DAG from arbitrary array payload (records + optional relations).
    """
    from src.services.mcc_architect_builder import build_design_dag_from_arrays

    if not req.records:
        raise HTTPException(status_code=400, detail="records array is required")

    try:
        result = await asyncio.to_thread(
            build_design_dag_from_arrays,
            [dict(r) for r in req.records],
            [dict(r) for r in req.relations],
            str(req.scope_name or "array_scope"),
            int(req.max_nodes),
            bool(req.use_predictive_overlay),
            int(req.max_predicted_edges),
            float(req.min_confidence),
            str(req.trm_profile or "off"),
            dict(req.trm_policy or {}),
        )
        return _with_trm_contract_meta(
            result=dict(result or {}),
            trm_profile=str(req.trm_profile or "off"),
            trm_policy=dict(req.trm_policy or {}),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to build design graph from array: {e}"
        )


@router.post("/dag-versions/create")
async def create_dag_version(req: CreateDagVersionRequest):
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.API.V1
    Create DAG version snapshot for current project.
    """
    from src.services.mcc_dag_versions import create_dag_version as _create

    project_id = _resolve_project_id_for_versions(req.project_id)
    try:
        result = await asyncio.to_thread(
            _create,
            project_id,
            dict(req.dag_payload or {}),
            name=str(req.name or ""),
            author=str(req.author or "architect"),
            source=str(req.source or "manual"),
            build_meta=dict(req.build_meta or {}),
            markers=[str(m) for m in (req.markers or [])],
            set_primary=bool(req.set_primary),
        )
        return {"success": True, "project_id": project_id, "version": result}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create DAG version: {e}"
        )


@router.get("/dag-versions/list")
async def list_dag_versions(
    project_id: str = Query("", description="Optional explicit project_id"),
):
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.API.V1
    List DAG version summaries for current project.
    """
    from src.services.mcc_dag_versions import list_dag_versions as _list

    project_id = _resolve_project_id_for_versions(project_id)
    try:
        result = await asyncio.to_thread(_list, project_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list DAG versions: {e}")


@router.get("/dag-versions/{version_id}")
async def get_dag_version(
    version_id: str,
    project_id: str = Query("", description="Optional explicit project_id"),
):
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.API.V1
    Get full DAG version payload by ID for current project.
    """
    from src.services.mcc_dag_versions import get_dag_version as _get

    project_id = _resolve_project_id_for_versions(project_id)
    try:
        result = await asyncio.to_thread(_get, project_id, str(version_id))
        if not result:
            raise HTTPException(
                status_code=404, detail=f"DAG version not found: {version_id}"
            )
        return {"success": True, "project_id": project_id, "version": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get DAG version: {e}")


@router.post("/dag-versions/{version_id}/set-primary")
async def set_primary_dag_version(version_id: str, req: SetPrimaryDagVersionRequest):
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.API.V1
    Set selected DAG version as primary for current project.
    """
    from src.services.mcc_dag_versions import set_primary_version as _set_primary

    if not req.set_primary:
        raise HTTPException(status_code=400, detail="set_primary must be true")
    project_id = _resolve_project_id_for_versions(req.project_id)
    try:
        result = await asyncio.to_thread(_set_primary, project_id, str(version_id))
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to set primary DAG version: {e}"
        )


@router.post("/dag-versions/auto-compare")
async def auto_compare_dag_versions(req: DagAutoCompareRequest):
    """
    MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.API.V1
    Auto-run DAG build variants, compute scorecards, optionally persist and set best primary.
    """
    from src.services.mcc_dag_compare import run_dag_auto_compare

    source_kind = str(req.source_kind or "scope").strip().lower()
    project_id = _resolve_project_id_for_versions(req.project_id)

    config = _resolve_project_config(req.project_id)
    resolved_scope = str(req.scope_path or "").strip()
    if source_kind == "scope":
        if not resolved_scope and config is not None:
            # MARKER_161.9.MULTIPROJECT.ISOLATION.SANDBOX_SCOPE_DEFAULT.V1
            resolved_scope = str(config.sandbox_path or config.source_path or "")
        resolved_scope = (
            os.path.abspath(os.path.expanduser(resolved_scope))
            if resolved_scope
            else ""
        )
        if not resolved_scope or not os.path.isdir(resolved_scope):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scope_path for source_kind=scope: {resolved_scope}",
            )

    try:
        variants_payload = [
            (v.model_dump() if hasattr(v, "model_dump") else dict(v))
            for v in (req.variants or [])
        ]
        result = await asyncio.to_thread(
            run_dag_auto_compare,
            project_id=project_id,
            variants=variants_payload,
            source_kind=source_kind,
            scope_root=resolved_scope,
            include_artifacts=bool(req.include_artifacts),
            records=[dict(r) for r in (req.records or [])],
            relations=[dict(r) for r in (req.relations or [])],
            scope_name=str(req.scope_name or "array_scope"),
            default_max_nodes=int(req.default_max_nodes or 600),
            persist_versions=bool(req.persist_versions),
            set_primary_best=bool(req.set_primary_best),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to auto-compare DAG variants: {e}"
        )


@router.get("/layout/preferences")
async def get_layout_preferences(
    user_id: str = Query("danila", description="User ID"),
    scope_key: str = Query("", description="Scope key (project/nav/graph)"),
):
    """
    MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1:
    Read DAG layout intent profiles from ENGRAM.
    Stored as viewport_patterns.dag_layout_profiles (no raw coordinates).
    """
    try:
        from src.memory.aura_store import get_aura_store

        aura = get_aura_store()
        if not aura:
            return {"success": False, "error": "AURA unavailable", "profile": None}

        profiles = (
            aura.get_preference(user_id, "viewport_patterns", "dag_layout_profiles")
            or {}
        )
        if not isinstance(profiles, dict):
            profiles = {}
        if scope_key:
            return {
                "success": True,
                "profile": profiles.get(scope_key),
                "scope_key": scope_key,
            }
        return {"success": True, "profiles": profiles}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read layout preferences: {e}"
        )


@router.post("/layout/preferences")
async def update_layout_preferences(req: LayoutPreferenceUpdateRequest):
    """
    MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1:
    Update scoped DAG layout intent profile in ENGRAM.
    Uses EMA-style merge by sample_count and confidence.
    """
    scope_key = (req.scope_key or "").strip()
    if not scope_key:
        raise HTTPException(status_code=400, detail="scope_key is required")
    if not isinstance(req.profile, dict):
        raise HTTPException(status_code=400, detail="profile must be object")

    try:
        from src.memory.aura_store import get_aura_store

        aura = get_aura_store()
        if not aura:
            raise HTTPException(status_code=503, detail="AURA unavailable")

        profiles = (
            aura.get_preference(req.user_id, "viewport_patterns", "dag_layout_profiles")
            or {}
        )
        if not isinstance(profiles, dict):
            profiles = {}

        prev = (
            profiles.get(scope_key) if isinstance(profiles.get(scope_key), dict) else {}
        )
        next_profile = dict(prev)

        prev_samples = int(prev.get("sample_count") or 0)
        incoming_samples = max(1, int(req.profile.get("sample_count") or 1))
        total_samples = prev_samples + incoming_samples

        def _blend(key: str, default: float = 0.0) -> float:
            pv = float(prev.get(key, default))
            nv = float(req.profile.get(key, pv))
            return ((pv * prev_samples) + (nv * incoming_samples)) / max(
                1, total_samples
            )

        for key in (
            "vertical_separation_bias",
            "sibling_spacing_bias",
            "branch_compactness_bias",
            "confidence",
        ):
            next_profile[key] = _blend(key, 0.0 if key != "confidence" else 0.5)

        for key in ("focus_overlay_preference", "pin_persistence_preference"):
            if key in req.profile:
                next_profile[key] = req.profile.get(key)
            elif key not in next_profile:
                next_profile[key] = (
                    "focus_only" if key == "focus_overlay_preference" else "pin_first"
                )

        next_profile["sample_count"] = total_samples
        next_profile["updated_at"] = req.profile.get("updated_at") or time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )

        profiles[scope_key] = next_profile
        aura.set_preference(
            req.user_id,
            "viewport_patterns",
            "dag_layout_profiles",
            profiles,
            confidence=float(next_profile.get("confidence", 0.7)),
        )

        return {"success": True, "scope_key": scope_key, "profile": next_profile}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update layout preferences: {e}"
        )


# ──────────────────────────────────────────────────────────────
# MARKER_162.P3: MYCO hidden memory + context bridge
# ──────────────────────────────────────────────────────────────


@router.post("/myco/hidden-index/reindex")
async def myco_hidden_index_reindex(req: MycoHiddenReindexRequest):
    """
    MARKER_162.P3.MYCO.HIDDEN_TRIPLE_MEMORY_INDEX.V1
    MARKER_162.P3.MYCO.README_SCAN_PIPELINE.V1
    Reindex hidden MYCO instruction corpus into triple-memory.
    """
    from src.services.myco_memory_bridge import reindex_hidden_instruction_memory

    try:
        result = reindex_hidden_instruction_memory(
            max_files=int(req.max_files),
            max_chunks=int(req.max_chunks),
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MYCO hidden reindex failed: {e}")


@router.post("/myco/context")
async def myco_context(req: MycoContextRequest):
    """
    MARKER_162.P3.MYCO.ENGRAM_USER_TASK_MEMORY.V1
    MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1
    MARKER_162.P3.MYCO.NO_UI_MEMORY_SURFACE.V1
    Return hidden MYCO context payload for backend/runtime usage.
    """
    from src.services.myco_memory_bridge import build_myco_memory_payload

    config = _resolve_project_config(req.project_id)
    project_id = str(config.project_id) if config else ""

    try:
        payload = build_myco_memory_payload(
            user_id=str(req.user_id or "danila"),
            active_project_id=project_id,
            focus=dict(req.focus or {}),
        )
        return {"success": True, "payload": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MYCO context build failed: {e}")


@router.post("/workflow/myco-hint")
async def workflow_myco_hint(req: WorkflowMycoHintRequest):
    """
    MARKER_167.STATS_WORKFLOW.MYCO_HINTS.V1
    MARKER_167.STATS_WORKFLOW.MYCO_TOOL_PRIORITY.V1
    Workflow-aware MYCO hint contract for Stats panel.
    """
    from src.services.myco_memory_bridge import retrieve_myco_hidden_context

    workflow_bank = str(req.workflow_bank or "core").strip() or "core"
    workflow_family = str(req.workflow_family or req.workflow_id or "").strip()
    role = str(req.role or "").strip().lower()
    task_label = str(req.task_label or "active task").strip()
    focus = dict(req.focus or {})

    workflow_tools = _workflow_required_tools(workflow_family, workflow_bank)
    role_tools = _role_required_tools(role)
    project_tools = _project_context_tools(focus)
    favorite_tools = ["tasks", "context"]

    tool_priority = {
        "workflow_required": _dedupe_keep_order(workflow_tools),
        "role_required": _dedupe_keep_order(role_tools),
        "project_context": _dedupe_keep_order(project_tools),
        "favorites": _dedupe_keep_order(favorite_tools),
    }
    ordered_tools = _dedupe_keep_order(
        tool_priority["workflow_required"]
        + tool_priority["role_required"]
        + tool_priority["project_context"]
        + tool_priority["favorites"]
    )

    query_parts = [workflow_family or req.workflow_id, role, task_label]
    retrieval = retrieve_myco_hidden_context(
        query=" ".join([part for part in query_parts if str(part or "").strip()]),
        focus=focus,
        top_k=2,
    )

    lead_tools = " > ".join(ordered_tools[:3]) if ordered_tools else "context > tasks"
    hint = (
        f"MYCO: for {workflow_family or req.workflow_id or 'workflow'} on {task_label}, "
        f"start with {lead_tools}"
    )
    if role:
        hint += f" · role:{role}"

    return {
        "success": True,
        "hint": hint,
        "tool_priority": tool_priority,
        "ordered_tools": ordered_tools,
        "retrieval": retrieval,
        "diagnostics": {
            "workflow_family": workflow_family,
            "workflow_bank": workflow_bank,
            "role": role,
            "retrieval_method": str(retrieval.get("method") or "none"),
            "retrieval_count": len(list(retrieval.get("items") or [])),
        },
    }


# ──────────────────────────────────────────────────────────────
# MARKER_153.7B: Architect Captain — Recommendations
# ──────────────────────────────────────────────────────────────


@router.get("/captain/recommend")
async def get_recommendation():
    """
    Get next task recommendation from the Architect Captain.
    Returns recommendation with module, workflow, team preset, and reason.
    """
    from src.services.architect_captain import ArchitectCaptain
    from dataclasses import asdict

    rec = ArchitectCaptain.recommend_next()
    if rec is None:
        return {"has_recommendation": False, "message": "No actionable modules found"}

    return {
        "has_recommendation": True,
        **asdict(rec),
    }


@router.post("/captain/accept")
async def accept_recommendation(module_id: str = ""):
    """
    Accept the current recommendation. Returns dispatch-ready context.
    If module_id is empty, accepts the top recommendation.
    """
    from src.services.architect_captain import ArchitectCaptain
    from dataclasses import asdict

    rec = ArchitectCaptain.recommend_next()
    if rec is None:
        raise HTTPException(status_code=404, detail="No recommendation available")

    if module_id and module_id != rec.module_id:
        # User wants a different module — re-recommend for that specific one
        # For now, just accept whatever is recommended
        pass

    result = ArchitectCaptain.accept_recommendation(rec)
    return result


@router.post("/captain/reject")
async def reject_recommendation():
    """
    Reject the current recommendation. Returns alternatives.
    """
    from src.services.architect_captain import ArchitectCaptain

    rec = ArchitectCaptain.recommend_next()
    if rec is None:
        raise HTTPException(status_code=404, detail="No recommendation available")

    result = ArchitectCaptain.reject_recommendation(rec)
    return result


@router.get("/captain/progress")
async def get_project_progress():
    """
    Get overall project progress (modules completed, active, pending).
    """
    from src.services.architect_captain import ArchitectCaptain

    return ArchitectCaptain.get_progress()
