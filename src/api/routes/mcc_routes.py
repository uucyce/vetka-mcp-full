"""
MARKER_153.1B: MCC REST API Routes.

Endpoints for Mycelium Command Center initialization, state persistence,
and project setup. Foundation for Phase 153 Matryoshka navigation.

@phase 153
@wave 1
@status active
"""

import os
import shutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.services.project_config import ProjectConfig, SessionState

router = APIRouter(prefix="/api/mcc", tags=["MCC"])


# ──────────────────────────────────────────────────────────────
# Request/Response models
# ──────────────────────────────────────────────────────────────

class InitResponse(BaseModel):
    has_project: bool
    project_config: Optional[dict] = None
    session_state: Optional[dict] = None

class ProjectInitRequest(BaseModel):
    source_type: str       # "local" | "git"
    source_path: str       # absolute path or git URL
    quota_gb: int = 10

class ProjectInitResponse(BaseModel):
    success: bool
    project_id: str = ""
    sandbox_path: str = ""
    errors: list[str] = []

class StateRequest(BaseModel):
    level: str = "roadmap"
    roadmap_node_id: str = ""
    task_id: str = ""
    history: list[str] = []


# ──────────────────────────────────────────────────────────────
# GET /api/mcc/init — Load project config + session state
# ──────────────────────────────────────────────────────────────

@router.get("/init", response_model=InitResponse)
async def mcc_init():
    """
    Called on frontend mount. Returns:
    - has_project: bool — whether a project is configured
    - project_config: dict — project settings (if exists)
    - session_state: dict — last navigation state (if exists)
    """
    config = ProjectConfig.load()
    if config is None:
        return InitResponse(has_project=False)

    state = SessionState.load()
    from dataclasses import asdict
    return InitResponse(
        has_project=True,
        project_config=asdict(config),
        session_state=asdict(state),
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
    state = SessionState(
        level=req.level,
        roadmap_node_id=req.roadmap_node_id,
        task_id=req.task_id,
        history=req.history,
    )
    if not state.save():
        raise HTTPException(status_code=500, detail="Failed to save session state")
    return {"ok": True}


# ──────────────────────────────────────────────────────────────
# GET /api/mcc/state — Get current session state
# ──────────────────────────────────────────────────────────────

@router.get("/state")
async def get_state():
    """Get current session state for Zustand hydration."""
    state = SessionState.load()
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
    """
    # Check if project already exists
    existing = ProjectConfig.load()
    if existing is not None:
        return ProjectInitResponse(
            success=False,
            errors=["Project already configured. Delete first to reconfigure."],
        )

    # Create config
    config = ProjectConfig.create_new(
        source_type=req.source_type,
        source_path=req.source_path,
        quota_gb=req.quota_gb,
    )

    # Validate
    errors = config.validate()

    # Validate source exists
    if req.source_type == "local":
        if not os.path.exists(req.source_path):
            errors.append(f"Source path not found: {req.source_path}")
        elif not os.path.isdir(req.source_path):
            errors.append(f"Source path is not a directory: {req.source_path}")

    if errors:
        return ProjectInitResponse(success=False, errors=errors)

    # Create sandbox directory
    try:
        os.makedirs(config.sandbox_path, exist_ok=True)

        if req.source_type == "local":
            # Copy project to sandbox
            # shutil.copytree needs dst to not exist, so remove first
            if os.path.exists(config.sandbox_path):
                shutil.rmtree(config.sandbox_path)
            shutil.copytree(
                req.source_path,
                config.sandbox_path,
                ignore=shutil.ignore_patterns(
                    'node_modules', '.git', '__pycache__', '*.pyc',
                    'dist', 'build', '.next', 'target',
                ),
            )
        elif req.source_type == "git":
            # Git clone — shallow
            import subprocess
            result = subprocess.run(
                ["git", "clone", "--depth=1", req.source_path, config.sandbox_path],
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
            errors=[f"Permission denied: cannot read {req.source_path}"],
        )
    except OSError as e:
        return ProjectInitResponse(
            success=False,
            errors=[f"Copy failed: {str(e)[:500]}"],
        )

    # Save config
    if not config.save():
        return ProjectInitResponse(success=False, errors=["Failed to save config"])

    # Initialize default session state
    SessionState().save()

    return ProjectInitResponse(
        success=True,
        project_id=config.project_id,
        sandbox_path=config.sandbox_path,
    )


# ──────────────────────────────────────────────────────────────
# DELETE /api/mcc/project — Remove project config (allows reconfigure)
# ──────────────────────────────────────────────────────────────

@router.delete("/project")
async def delete_project():
    """
    Delete project config. Does NOT delete sandbox (use /api/playground/delete).
    Allows reconfiguring with a new project.
    """
    from src.services.project_config import CONFIG_PATH, SESSION_STATE_PATH

    deleted = []
    for path in [CONFIG_PATH, SESSION_STATE_PATH]:
        if os.path.exists(path):
            os.remove(path)
            deleted.append(os.path.basename(path))

    return {"ok": True, "deleted": deleted}
