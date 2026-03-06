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
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.services.project_config import ProjectConfig, SessionState
from src.services.mcc_trm_config import resolve_trm_policy

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


async def _get_sandbox_status_cached(config: "ProjectConfig") -> dict:
    now = time.monotonic()
    source_mtime = _sandbox_source_mtime(config.sandbox_path)
    cached_status = _sandbox_status_cache.get("status")
    if (
        cached_status is not None
        and _sandbox_status_cache.get("sandbox_path") == config.sandbox_path
        and float(_sandbox_status_cache.get("source_mtime", 0.0)) == float(source_mtime)
        and (now - float(_sandbox_status_cache.get("ts", 0.0))) <= _SANDBOX_STATUS_TTL_SEC
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


def _load_active_session_state(project_id: str) -> "SessionState":
    # MARKER_161.7.MULTIPROJECT.API.ACTIVE_SESSION_RESOLVE.V1:
    # Session state is stored per active project when registry is available.
    try:
        from src.services.mcc_project_registry import load_session_for_project

        return load_session_for_project(project_id)
    except Exception:
        return SessionState.load()


def _save_active_session_state(project_id: str, state: "SessionState") -> bool:
    try:
        from src.services.mcc_project_registry import save_session_for_project

        return bool(save_session_for_project(project_id, state))
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
    projects: List[Dict[str, Any]] = []

class ProjectInitRequest(BaseModel):
    source_type: str       # "local" | "git" | "empty"
    source_path: str       # absolute path or git URL
    sandbox_path: str = "" # optional absolute path for playground/sandbox root
    quota_gb: int = 10

class ProjectInitResponse(BaseModel):
    success: bool
    project_id: str = ""
    sandbox_path: str = ""
    errors: list[str] = []


class ProjectActivateRequest(BaseModel):
    project_id: str

class StateRequest(BaseModel):
    level: str = "roadmap"
    roadmap_node_id: str = ""
    task_id: str = ""
    selected_key: Optional[Dict[str, Any]] = None
    history: list[str] = []


# ──────────────────────────────────────────────────────────────
# GET /api/mcc/init — Load project config + session state
# ──────────────────────────────────────────────────────────────

@router.get("/init", response_model=InitResponse)
async def mcc_init(project_id: str = Query("", description="Optional project_id to activate before init")):
    """
    Called on frontend mount. Returns:
    - has_project: bool — whether a project is configured
    - project_config: dict — project settings (if exists)
    - session_state: dict — last navigation state (if exists)

    MARKER_161.7.MULTIPROJECT.API.INIT_ACTIVE_PROJECT.V1:
    Migration point for active project tab context in MCC.
    """
    try:
        from src.services.mcc_project_registry import (
            activate_project,
            ensure_registry_bootstrap,
            list_projects,
        )

        ensure_registry_bootstrap()
        if str(project_id or "").strip():
            try:
                activate_project(str(project_id).strip())
            except Exception:
                # Ignore invalid activation in init path; fallback below.
                pass
        listing = list_projects()
    except Exception:
        listing = {"active_project_id": "", "projects": []}

    config = _load_active_project_config()
    if config is None:
        return InitResponse(
            has_project=False,
            active_project_id=str(listing.get("active_project_id", "")),
            projects=list(listing.get("projects") or []),
        )

    state = _load_active_session_state(config.project_id)
    from dataclasses import asdict
    return InitResponse(
        has_project=True,
        project_config=asdict(config),
        session_state=asdict(state),
        active_project_id=str(listing.get("active_project_id", "") or config.project_id),
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
    config = _load_active_project_config()
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    state = SessionState(
        level=req.level,
        roadmap_node_id=req.roadmap_node_id,
        task_id=req.task_id,
        selected_key=req.selected_key,
        history=req.history,
    )
    if not _save_active_session_state(config.project_id, state):
        raise HTTPException(status_code=500, detail="Failed to save session state")
    return {"ok": True}


# ──────────────────────────────────────────────────────────────
# GET /api/mcc/state — Get current session state
# ──────────────────────────────────────────────────────────────

@router.get("/state")
async def get_state():
    """Get current session state for Zustand hydration."""
    config = _load_active_project_config()
    if config is None:
        state = SessionState()
    else:
        state = _load_active_session_state(config.project_id)
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
    effective_source_type = req_source_type
    effective_source_path = req_source_path

    if req_source_type == "empty":
        temp_source = tempfile.mkdtemp(prefix="mycelium_empty_source_")
        try:
            with open(os.path.join(temp_source, "README.md"), "w", encoding="utf-8") as f:
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
        sandbox_path=str(req.sandbox_path or ""),
    )

    # Validate
    errors = config.validate()

    # Validate source exists
    if effective_source_type == "local":
        if not os.path.exists(effective_source_path):
            errors.append(f"Source path not found: {effective_source_path}")
        elif not os.path.isdir(effective_source_path):
            errors.append(f"Source path is not a directory: {effective_source_path}")

    if errors:
        return ProjectInitResponse(success=False, errors=errors)

    # Create sandbox directory
    skipped_copy_sources: list[str] = []
    try:
        os.makedirs(config.sandbox_path, exist_ok=True)

        if effective_source_type == "local":
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
                    'node_modules', '.git', '__pycache__', '*.pyc',
                    'dist', 'build', '.next', 'target',
                ),
                copy_function=_copy2_best_effort,
                ignore_dangling_symlinks=True,
                symlinks=True,
            )
        elif effective_source_type == "git":
            # Git clone — shallow
            import subprocess
            result = subprocess.run(
                ["git", "clone", "--depth=1", effective_source_path, config.sandbox_path],
                capture_output=True, text=True, timeout=120,
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
    _save_active_session_state(config.project_id, SessionState())

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
        sandbox_path=config.sandbox_path,
    )


@router.get("/projects/list")
async def list_projects():
    """
    MARKER_161.7.MULTIPROJECT.API.PROJECTS_LIST.V1
    List project registry summaries and active project pointer.
    """
    from src.services.mcc_project_registry import ensure_registry_bootstrap, list_projects as _list

    ensure_registry_bootstrap()
    result = _list()
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
async def delete_project():
    """
    Delete project config. Does NOT delete sandbox (use DELETE /api/mcc/sandbox).
    Allows reconfiguring with a new project.
    """
    from src.services.project_config import CONFIG_PATH, SESSION_STATE_PATH

    deleted = []
    config = _load_active_project_config()

    if config is not None:
        try:
            from src.services.mcc_project_registry import remove_project as _remove_project

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
async def sandbox_status():
    """
    Get sandbox disk usage and quota status.
    Used by SandboxDropdown to show [Sandbox ✓ 2.1/10GB] or [No Sandbox].
    """
    config = _load_active_project_config()
    if config is None:
        return SandboxStatusResponse(exists=False)
    status = await _get_sandbox_status_cached(config)
    return SandboxStatusResponse(**status)


class SandboxRecreateRequest(BaseModel):
    force: bool = False  # Force recreate even if exists


@router.post("/sandbox/recreate")
async def sandbox_recreate(req: SandboxRecreateRequest):
    """
    Delete and recreate sandbox from source.
    Used when sandbox gets corrupted or user wants a fresh copy.
    """
    config = _load_active_project_config()
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
            raise HTTPException(status_code=500, detail=f"Failed to delete sandbox: {e}")

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
                    'node_modules', '.git', '__pycache__', '*.pyc',
                    'dist', 'build', '.next', 'target',
                ),
            )
        elif config.source_type == "git":
            import subprocess
            result = subprocess.run(
                ["git", "clone", "--depth=1", config.source_path, config.sandbox_path],
                capture_output=True, text=True, timeout=120,
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
async def delete_sandbox():
    """
    Delete sandbox directory (but keep project config).
    Sandbox can be recreated via POST /api/mcc/sandbox/recreate.
    """
    config = _load_active_project_config()
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
async def update_quota(quota_gb: int):
    """Update project quota (1-100 GB)."""
    if quota_gb < 1 or quota_gb > 100:
        raise HTTPException(status_code=400, detail="quota_gb must be 1-100")

    config = _load_active_project_config()
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
async def get_roadmap():
    """
    Get the project roadmap DAG.
    Returns the saved roadmap or generates one if absent.
    """
    from src.services.roadmap_generator import RoadmapDAG, RoadmapGenerator

    config = _load_active_project_config()
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    dag = RoadmapDAG.load()
    if dag is None:
        # Auto-generate on first request
        dag = await RoadmapGenerator.analyze_project(config)

    return dag.to_frontend_format()


@router.get("/graph/condensed")
async def get_condensed_graph(
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

    config = _load_active_project_config()
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    resolved_scope = (scope_path or "").strip()
    if not resolved_scope:
        resolved_scope = config.source_path or config.sandbox_path
    resolved_scope = os.path.abspath(os.path.expanduser(resolved_scope))

    if not os.path.isdir(resolved_scope):
        raise HTTPException(status_code=400, detail=f"Invalid scope_path: {resolved_scope}")

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
        raise HTTPException(status_code=500, detail=f"Failed to build condensed graph: {e}")


@router.post("/roadmap/generate")
async def generate_roadmap():
    """Regenerate roadmap from current sandbox state."""
    from src.services.roadmap_generator import RoadmapGenerator

    config = _load_active_project_config()
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    if not config.sandbox_exists():
        raise HTTPException(status_code=400, detail="Sandbox not found. Create sandbox first.")

    dag = await RoadmapGenerator.analyze_project(config)
    return {"ok": True, "node_count": len(dag.nodes), "edge_count": len(dag.edges)}


@router.get("/workflows")
async def list_workflows():
    """List all available workflow templates."""
    from src.services.architect_prefetch import WorkflowTemplateLibrary
    return {"templates": WorkflowTemplateLibrary.list_templates()}


@router.get("/workflows/{workflow_key}")
async def get_workflow(workflow_key: str):
    """Get a specific workflow template by key."""
    from src.services.architect_prefetch import WorkflowTemplateLibrary
    tpl = WorkflowTemplateLibrary.get_template(workflow_key)
    if tpl is None:
        raise HTTPException(status_code=404, detail=f"Workflow template '{workflow_key}' not found")
    return tpl


class PrefetchRequest(BaseModel):
    task_description: str
    task_type: str = ""
    complexity: int = 5


class PredictGraphRequest(BaseModel):
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


class LayoutPreferenceUpdateRequest(BaseModel):
    user_id: str = "danila"
    scope_key: str
    profile: Dict[str, Any]


class MycoHiddenReindexRequest(BaseModel):
    max_files: int = 240
    max_chunks: int = 2400


class MycoContextRequest(BaseModel):
    user_id: str = "danila"
    focus: Dict[str, Any] = {}


class CreateDagVersionRequest(BaseModel):
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.API.V1
    Persist DAG build variant for compare/select workflow.
    """
    dag_payload: Dict[str, Any]
    name: str = ""
    author: str = "architect"
    source: str = "manual"
    build_meta: Dict[str, Any] = {}
    markers: List[str] = []
    set_primary: bool = False


class SetPrimaryDagVersionRequest(BaseModel):
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


def _with_trm_contract_meta(result: Dict[str, Any], trm_profile: str, trm_policy: Dict[str, Any]) -> Dict[str, Any]:
    """
    MARKER_161.TRM.CONFIG.CONTRACT.V1
    W1 contract extension only:
    - accepts TRM policy/profile inputs
    - publishes stable response metadata
    - does not mutate DAG behavior yet
    """
    out = dict(result or {})
    if isinstance(out.get("trm_meta"), dict):
        out["graph_source"] = str(out.get("graph_source") or ("trm_refined" if bool(out["trm_meta"].get("applied")) else "baseline"))
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


def _resolve_project_id_for_versions() -> str:
    config = _load_active_project_config()
    if config and config.project_id:
        return str(config.project_id)
    return "default_project"


@router.post("/prefetch")
async def run_prefetch(req: PrefetchRequest):
    """
    Run the Architect Prefetch Pipeline.
    Returns context for pipeline injection.
    """
    from src.services.architect_prefetch import ArchitectPrefetch
    from dataclasses import asdict

    config = _load_active_project_config()
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


@router.post("/graph/predict")
async def predict_graph_overlay(req: PredictGraphRequest):
    """
    MARKER_155.MODE_ARCH.V11.P15:
    Produce predictive overlay edges for MCC single-canvas graph.
    Current implementation is deterministic heuristic (JEPA contract stub).
    """
    from src.services.mcc_predictive_overlay import build_predictive_overlay
    from src.services.mcc_jepa_adapter import JepaRuntimeUnavailableError

    config = _load_active_project_config()
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    resolved_scope = (req.scope_path or "").strip()
    if not resolved_scope:
        resolved_scope = config.source_path or config.sandbox_path
    resolved_scope = os.path.abspath(os.path.expanduser(resolved_scope))

    if not os.path.isdir(resolved_scope):
        raise HTTPException(status_code=400, detail=f"Invalid scope_path: {resolved_scope}")

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
        raise HTTPException(status_code=500, detail=f"Failed to build predictive overlay: {e}")


@router.get("/graph/predict/runtime-health", response_model=PredictRuntimeHealthResponse)
async def predict_graph_runtime_health(
    runtime_module: str = Query("src.services.jepa_runtime", description="Runtime module path"),
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
            raise HTTPException(status_code=400, detail=f"runtime module has no runtime_health(): {module_path}")

        data = health_fn(bool(force))  # type: ignore[misc]
        if not isinstance(data, dict):
            raise HTTPException(status_code=500, detail=f"invalid runtime health payload from: {module_path}")

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

    config = _load_active_project_config()
    if config is None:
        raise HTTPException(status_code=404, detail="No project configured")

    resolved_scope = (req.scope_path or "").strip()
    if not resolved_scope:
        resolved_scope = config.source_path or config.sandbox_path
    resolved_scope = os.path.abspath(os.path.expanduser(resolved_scope))

    if not os.path.isdir(resolved_scope):
        raise HTTPException(status_code=400, detail=f"Invalid scope_path: {resolved_scope}")

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
        raise HTTPException(status_code=500, detail=f"Failed to build design graph: {e}")


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
        raise HTTPException(status_code=500, detail=f"Failed to build design graph from array: {e}")


@router.post("/dag-versions/create")
async def create_dag_version(req: CreateDagVersionRequest):
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.API.V1
    Create DAG version snapshot for current project.
    """
    from src.services.mcc_dag_versions import create_dag_version as _create

    project_id = _resolve_project_id_for_versions()
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
        raise HTTPException(status_code=500, detail=f"Failed to create DAG version: {e}")


@router.get("/dag-versions/list")
async def list_dag_versions():
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.API.V1
    List DAG version summaries for current project.
    """
    from src.services.mcc_dag_versions import list_dag_versions as _list

    project_id = _resolve_project_id_for_versions()
    try:
        result = await asyncio.to_thread(_list, project_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list DAG versions: {e}")


@router.get("/dag-versions/{version_id}")
async def get_dag_version(version_id: str):
    """
    MARKER_155.ARCHITECT_BUILD.DAG_VERSIONS.API.V1
    Get full DAG version payload by ID for current project.
    """
    from src.services.mcc_dag_versions import get_dag_version as _get

    project_id = _resolve_project_id_for_versions()
    try:
        result = await asyncio.to_thread(_get, project_id, str(version_id))
        if not result:
            raise HTTPException(status_code=404, detail=f"DAG version not found: {version_id}")
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
    project_id = _resolve_project_id_for_versions()
    try:
        result = await asyncio.to_thread(_set_primary, project_id, str(version_id))
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set primary DAG version: {e}")


@router.post("/dag-versions/auto-compare")
async def auto_compare_dag_versions(req: DagAutoCompareRequest):
    """
    MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.API.V1
    Auto-run DAG build variants, compute scorecards, optionally persist and set best primary.
    """
    from src.services.mcc_dag_compare import run_dag_auto_compare

    source_kind = str(req.source_kind or "scope").strip().lower()
    project_id = _resolve_project_id_for_versions()

    config = _load_active_project_config()
    resolved_scope = str(req.scope_path or "").strip()
    if source_kind == "scope":
        if not resolved_scope and config is not None:
            resolved_scope = str(config.source_path or config.sandbox_path or "")
        resolved_scope = os.path.abspath(os.path.expanduser(resolved_scope)) if resolved_scope else ""
        if not resolved_scope or not os.path.isdir(resolved_scope):
            raise HTTPException(status_code=400, detail=f"Invalid scope_path for source_kind=scope: {resolved_scope}")

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
        raise HTTPException(status_code=500, detail=f"Failed to auto-compare DAG variants: {e}")


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
        from src.memory.engram_user_memory import get_engram_user_memory
        engram = get_engram_user_memory()
        if not engram:
            return {"success": False, "error": "ENGRAM unavailable", "profile": None}

        profiles = engram.get_preference(user_id, "viewport_patterns", "dag_layout_profiles") or {}
        if not isinstance(profiles, dict):
            profiles = {}
        if scope_key:
            return {"success": True, "profile": profiles.get(scope_key), "scope_key": scope_key}
        return {"success": True, "profiles": profiles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read layout preferences: {e}")


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
        from src.memory.engram_user_memory import get_engram_user_memory
        engram = get_engram_user_memory()
        if not engram:
            raise HTTPException(status_code=503, detail="ENGRAM unavailable")

        profiles = engram.get_preference(req.user_id, "viewport_patterns", "dag_layout_profiles") or {}
        if not isinstance(profiles, dict):
            profiles = {}

        prev = profiles.get(scope_key) if isinstance(profiles.get(scope_key), dict) else {}
        next_profile = dict(prev)

        prev_samples = int(prev.get("sample_count") or 0)
        incoming_samples = max(1, int(req.profile.get("sample_count") or 1))
        total_samples = prev_samples + incoming_samples

        def _blend(key: str, default: float = 0.0) -> float:
            pv = float(prev.get(key, default))
            nv = float(req.profile.get(key, pv))
            return ((pv * prev_samples) + (nv * incoming_samples)) / max(1, total_samples)

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
                next_profile[key] = "focus_only" if key == "focus_overlay_preference" else "pin_first"

        next_profile["sample_count"] = total_samples
        next_profile["updated_at"] = req.profile.get("updated_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        profiles[scope_key] = next_profile
        engram.set_preference(
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
        raise HTTPException(status_code=500, detail=f"Failed to update layout preferences: {e}")


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

    config = _load_active_project_config()
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
