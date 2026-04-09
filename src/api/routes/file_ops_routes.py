"""
VETKA File Operations Routes - FastAPI Version

@file file_ops_routes.py
@status ACTIVE
@phase Phase 39.6
@lastAudit 2026-01-05

File system operations API routes.
Migrated from src/server/routes/file_ops_routes.py (Flask Blueprint)

Endpoints:
- POST /api/file/show-in-finder - Reveal file in Finder/Explorer

Changes from Flask version:
- Blueprint -> APIRouter
- request.get_json() -> Pydantic BaseModel
- return jsonify({}) -> return {}
- def -> async def
"""

import os
import subprocess
import platform
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/api/file", tags=["file_ops"])


# ============================================================
# PYDANTIC MODELS
# ============================================================

class ShowInFinderRequest(BaseModel):
    """Request to show file in Finder/Explorer."""
    path: str


# ============================================================
# ROUTES
# ============================================================

@router.post("/show-in-finder")
async def show_in_finder(req: ShowInFinderRequest):
    """
    Open file location in Finder (macOS), Explorer (Windows), or file manager (Linux).
    """
    try:
        file_path = req.path

        if not file_path:
            raise HTTPException(status_code=400, detail="No path provided")

        # Validate path exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")

        # macOS: use 'open -R' to reveal in Finder
        if platform.system() == "Darwin":
            subprocess.run(["open", "-R", file_path], check=True)
            return {'success': True, 'message': f'Revealed in Finder: {file_path}'}

        # Linux: use xdg-open on parent directory
        elif platform.system() == "Linux":
            parent_dir = os.path.dirname(file_path)
            subprocess.run(["xdg-open", parent_dir], check=True)
            return {'success': True, 'message': f'Opened directory: {parent_dir}'}

        # Windows: use explorer /select
        elif platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", file_path], check=True)
            return {'success': True, 'message': f'Revealed in Explorer: {file_path}'}

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform.system()}")

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to open: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
