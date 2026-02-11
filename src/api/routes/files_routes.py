"""
VETKA Files Routes - FastAPI Version

@file files_routes.py
@status ACTIVE
@phase Phase 54.6
@lastAudit 2026-01-08

File operations API routes.
Migrated from src/server/routes/files_routes.py (Flask Blueprint)

Endpoints:
- POST /api/files/read - Read file content (with artifact/binary support)
- POST /api/files/save - Save file content
- GET /api/files/raw - Raw file serving
- POST /api/files/resolve-path - Smart file path resolution for drag & drop

Note: VETKA is a local application. User decides what to scan.
If a file is indexed in VETKA, user wants to see it. No path restrictions.
"""

import os
import sys
import base64
import hashlib
import mimetypes
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List

from src.scanners.file_watcher import get_watcher


router = APIRouter(prefix="/api/files", tags=["files"])


# Project root for artifact storage only
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ============================================================
# PYDANTIC MODELS
# ============================================================

class FileReadRequest(BaseModel):
    """Request to read a file."""
    path: str


class FileSaveRequest(BaseModel):
    """Request to save a file."""
    path: str
    content: str


class FileResolveRequest(BaseModel):
    """Request to resolve a dropped file's real path."""
    filename: str
    relativePath: Optional[str] = None
    contentHash: Optional[str] = None
    fileSize: Optional[int] = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _resolve_path(file_path: str) -> tuple[str, bool]:
    """
    Resolve file path with special handling for artifacts.

    Args:
        file_path: Raw path from request

    Returns:
        Tuple of (resolved_path, is_artifact)
    """
    clean_path = file_path.lstrip("/")

    # Handle artifact paths: /artifact/xxx.md -> data/artifacts/xxx.md
    if clean_path.startswith("artifact/"):
        artifact_name = clean_path.replace("artifact/", "", 1)
        artifact_name = artifact_name.replace("..", "").replace("/", "_")
        real_path = os.path.abspath(os.path.join(PROJECT_ROOT, "data", "artifacts", artifact_name))
        return real_path, True
    elif file_path.startswith("/"):
        # Absolute path - use directly
        return os.path.realpath(file_path), False
    else:
        # Relative path - resolve from project root
        return os.path.realpath(os.path.join(PROJECT_ROOT, file_path)), False


# ============================================================
# ROUTES
# ============================================================

@router.post("/read")
async def read_file(req: FileReadRequest):
    """
    Read file content for Artifact Panel.

    Special paths:
    - /artifact/xxx.md -> data/artifacts/xxx.md

    No path restrictions - VETKA is a local app, user decides what to scan.

    Returns:
        content: File content (text or base64 for binary)
        encoding: 'utf-8' or 'base64'
        mimeType: Detected MIME type
        size: File size in bytes
        path: Resolved file path
    """
    file_path = req.path

    if not file_path:
        raise HTTPException(status_code=400, detail="No path provided")

    real_path, _ = _resolve_path(file_path)

    # Check file exists
    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if os.path.isdir(real_path):
        raise HTTPException(status_code=400, detail="Path is a directory, not a file")

    try:
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(real_path)
        mime_type = mime_type or "text/plain"

        # Get file size
        file_size = os.path.getsize(real_path)

        # For binary files, use base64
        is_binary = not mime_type.startswith(("text/", "application/json", "application/javascript", "application/xml"))

        if is_binary:
            with open(real_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("ascii")
            encoding = "base64"
        else:
            with open(real_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            encoding = "utf-8"

        return {
            "content": content,
            "encoding": encoding,
            "mimeType": mime_type,
            "size": file_size,
            "path": real_path
        }

    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_file(req: FileSaveRequest):
    """
    Save file content from Artifact Panel.

    Special paths:
    - /artifact/xxx.md -> data/artifacts/xxx.md (creates if not exists)

    No path restrictions - VETKA is a local app.

    Returns:
        success: True if saved
        path: Resolved file path
        size: Content size in bytes
    """
    file_path = req.path
    content = req.content

    if not file_path:
        raise HTTPException(status_code=400, detail="No path provided")

    real_path, is_artifact = _resolve_path(file_path)

    # For artifacts, create if not exists; for regular files, require existing
    if not is_artifact and not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    try:
        # Create directory if needed for artifacts
        if is_artifact:
            os.makedirs(os.path.dirname(real_path), exist_ok=True)

        with open(real_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "path": real_path,
            "size": len(content)
        }

    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/raw")
async def get_raw_file(path: str = Query(..., description="File path to serve")):
    """
    Serve raw file (for images, videos, PDFs, 3D models).

    No path restrictions - VETKA is a local app.

    Returns:
        Raw file content with appropriate MIME type
    """
    if not path:
        raise HTTPException(status_code=400, detail="No path provided")

    # Resolve path
    if path.startswith("/"):
        real_path = os.path.realpath(path)
    else:
        real_path = os.path.realpath(os.path.join(PROJECT_ROOT, path))

    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if os.path.isdir(real_path):
        raise HTTPException(status_code=400, detail="Path is a directory")

    try:
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(real_path)
        mime_type = mime_type or "application/octet-stream"

        # Return file with proper MIME type
        return FileResponse(
            path=real_path,
            media_type=mime_type,
            filename=os.path.basename(real_path)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PHASE 54.6: SMART FILE PATH RESOLUTION
# ============================================================

def _search_in_directory(directory: str, filename: str, timeout: int = 5) -> List[str]:
    """
    Search for a file in a directory using find command.

    Args:
        directory: Directory to search in
        filename: Filename to find
        timeout: Command timeout in seconds

    Returns:
        List of found file paths
    """
    try:
        result = subprocess.run(
            ['find', directory, '-name', filename, '-type', 'f', '-maxdepth', '15'],
            capture_output=True, text=True, timeout=timeout
        )
        paths = result.stdout.strip().split('\n')
        return [p for p in paths if p and os.path.exists(p)]
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"[FileResolve] find error in {directory}: {e}")
        return []


def _search_with_mdfind(filename: str, timeout: int = 5) -> List[str]:
    """
    Search for a file using macOS Spotlight (mdfind).
    Much faster than find for indexed locations.

    Args:
        filename: Filename to find
        timeout: Command timeout in seconds

    Returns:
        List of found file paths
    """
    if sys.platform != 'darwin':
        return []

    try:
        result = subprocess.run(
            ['mdfind', '-name', filename],
            capture_output=True, text=True, timeout=timeout
        )
        paths = result.stdout.strip().split('\n')
        return [p for p in paths if p and os.path.exists(p)]
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"[FileResolve] mdfind error: {e}")
        return []


def _compute_file_hash(file_path: str) -> Optional[str]:
    """Compute SHA256 hash of file content."""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


def _filter_by_hash(paths: List[str], target_hash: str) -> List[str]:
    """Filter paths to only those matching the target hash."""
    if not target_hash:
        return paths

    matching = []
    for path in paths:
        file_hash = _compute_file_hash(path)
        if file_hash == target_hash:
            matching.append(path)
    return matching


def _filter_by_size(paths: List[str], target_size: int) -> List[str]:
    """Filter paths to only those matching the target size."""
    if not target_size:
        return paths

    matching = []
    for path in paths:
        try:
            if os.path.getsize(path) == target_size:
                matching.append(path)
        except Exception:
            pass
    return matching


def _filter_by_relative_path(paths: List[str], relative_path: str) -> List[str]:
    """Filter paths to those ending with the relative path."""
    if not relative_path:
        return paths

    # Normalize relative path
    rel_normalized = relative_path.lstrip('./')

    matching = []
    for path in paths:
        if path.endswith(rel_normalized) or path.endswith('/' + rel_normalized):
            matching.append(path)
    return matching


@router.post("/resolve-path")
async def resolve_file_path(req: FileResolveRequest, request: Request):
    """
    Phase 54.6: Smart file path resolution for drag & drop.

    When a file is dropped from the browser, we don't get the full path
    due to security restrictions. This endpoint searches for the file
    on disk using the filename and optional metadata.

    Search strategy:
    1. First search in watched directories (fast, likely match)
    2. Then use mdfind (macOS Spotlight) for instant search
    3. Fallback to find in home directory

    Filtering:
    - By relative path (if folder structure matches)
    - By file size (quick check)
    - By content hash (definitive match)

    Returns:
        status: 'found' | 'multiple' | 'found_outside_watched' | 'not_found'
        path: Resolved path (if status='found')
        candidates: List of possible paths (if status='multiple' or 'found_outside_watched')
        message: Human-readable message
        needsWatchedDir: True if file is outside watched directories
    """
    filename = req.filename
    relative_path = req.relativePath
    content_hash = req.contentHash
    file_size = req.fileSize

    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    print(f"[FileResolve] Searching for: {filename}")
    print(f"[FileResolve]   relativePath: {relative_path}")
    print(f"[FileResolve]   fileSize: {file_size}")

    # Phase 87: Get socketio and qdrant_client from app state
    # This ensures watcher singleton gets qdrant_client for real-time indexing
    socketio = getattr(request.app.state, 'socketio', None)
    qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
    qdrant_client = None
    if qdrant_manager and hasattr(qdrant_manager, 'client'):
        qdrant_client = qdrant_manager.client

    # Step 1: Search in watched directories first
    watcher = get_watcher(socketio=socketio, qdrant_client=qdrant_client)
    watched_dirs = list(watcher.watched_dirs)

    # Filter out browser:// virtual paths
    real_watched_dirs = [d for d in watched_dirs if not d.startswith('browser://')]

    all_found_in_watched = []
    for watched_dir in real_watched_dirs:
        found = _search_in_directory(watched_dir, filename, timeout=3)
        all_found_in_watched.extend(found)

    # Remove duplicates while preserving order
    all_found_in_watched = list(dict.fromkeys(all_found_in_watched))

    if all_found_in_watched:
        # Apply filters
        candidates = all_found_in_watched

        if relative_path:
            filtered = _filter_by_relative_path(candidates, relative_path)
            if filtered:
                candidates = filtered

        if file_size and len(candidates) > 1:
            filtered = _filter_by_size(candidates, file_size)
            if filtered:
                candidates = filtered

        if content_hash and len(candidates) > 1:
            filtered = _filter_by_hash(candidates, content_hash)
            if filtered:
                candidates = filtered

        if len(candidates) == 1:
            print(f"[FileResolve] Found exact match: {candidates[0]}")
            return {
                'status': 'found',
                'path': candidates[0],
                'message': f'Found in watched directory',
                'needsWatchedDir': False
            }
        elif len(candidates) > 1:
            print(f"[FileResolve] Multiple matches: {len(candidates)}")
            return {
                'status': 'multiple',
                'candidates': candidates[:10],  # Max 10
                'message': f'Found {len(candidates)} files named "{filename}" in watched directories',
                'needsWatchedDir': False
            }

    # Step 2: Use mdfind (macOS Spotlight) - instant search
    spotlight_results = _search_with_mdfind(filename, timeout=5)

    if spotlight_results:
        # Apply filters
        candidates = spotlight_results

        if relative_path:
            filtered = _filter_by_relative_path(candidates, relative_path)
            if filtered:
                candidates = filtered

        if file_size and len(candidates) > 1:
            filtered = _filter_by_size(candidates, file_size)
            if filtered:
                candidates = filtered

        if content_hash and len(candidates) > 1:
            filtered = _filter_by_hash(candidates, content_hash)
            if filtered:
                candidates = filtered

        # Check if any are in watched directories (already checked above, so these are outside)
        print(f"[FileResolve] Found outside watched: {len(candidates)}")

        if len(candidates) == 1:
            return {
                'status': 'found_outside_watched',
                'path': candidates[0],
                'candidates': candidates,
                'message': f'Found "{filename}" outside watched directories',
                'needsWatchedDir': True,
                'suggestedWatchDir': str(Path(candidates[0]).parent)
            }
        elif len(candidates) > 1:
            return {
                'status': 'found_outside_watched',
                'candidates': candidates[:10],
                'message': f'Found {len(candidates)} files named "{filename}" outside watched directories',
                'needsWatchedDir': True
            }

    # Step 3: Fallback - search in home directory (slower)
    home_dir = str(Path.home())
    home_results = _search_in_directory(home_dir, filename, timeout=15)

    if home_results:
        candidates = home_results

        if relative_path:
            filtered = _filter_by_relative_path(candidates, relative_path)
            if filtered:
                candidates = filtered

        if file_size and len(candidates) > 1:
            filtered = _filter_by_size(candidates, file_size)
            if filtered:
                candidates = filtered

        print(f"[FileResolve] Found in home: {len(candidates)}")

        return {
            'status': 'found_outside_watched',
            'candidates': candidates[:10],
            'message': f'Found "{filename}" in home directory',
            'needsWatchedDir': True
        }

    # Not found anywhere
    print(f"[FileResolve] Not found: {filename}")
    return {
        'status': 'not_found',
        'message': f'Cannot find "{filename}" on disk. Is it a new file?',
        'needsWatchedDir': False
    }


# ============================================================
# PHASE 60.4: OPEN IN FINDER
# ============================================================

class OpenInFinderRequest(BaseModel):
    """Request to open a file in Finder."""
    path: str


# MARKER_136.FILE_CONNECTIONS_API
@router.get("/{file_id}/connections")
async def get_file_connections(
    file_id: str,
    path: Optional[str] = Query(None, description="Optional explicit file path override"),
    max_connections: int = Query(50, ge=1, le=200),
):
    """
    Get local file connections for knowledge mode.

    Route supports:
    - /api/files/{id}/connections
    - with optional ?path=/abs/or/relative/file.py
    """
    from src.api.handlers.file_connections import build_file_connections

    target_ref = path or file_id
    real_path, _ = _resolve_path(target_ref)
    result = build_file_connections(
        target_file=real_path,
        project_root=PROJECT_ROOT,
        max_connections=max_connections,
    )
    return {"success": "error" not in result, **result}


@router.post("/open-in-finder")
async def open_in_finder(req: OpenInFinderRequest):
    """
    Phase 60.4: Open file location in macOS Finder.

    Opens Finder and selects the file (reveals it).

    Returns:
        success: True if command executed
        path: The file path
    """
    file_path = req.path

    if not file_path:
        raise HTTPException(status_code=400, detail="No path provided")

    # Resolve path
    if file_path.startswith("/"):
        real_path = os.path.realpath(file_path)
    else:
        real_path = os.path.realpath(os.path.join(PROJECT_ROOT, file_path))

    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    try:
        if sys.platform == 'darwin':
            # macOS: Use 'open -R' to reveal file in Finder
            subprocess.run(['open', '-R', real_path], check=True)
        elif sys.platform == 'win32':
            # Windows: Use explorer /select
            subprocess.run(['explorer', '/select,', real_path], check=True)
        else:
            # Linux: Open parent directory
            parent_dir = os.path.dirname(real_path)
            subprocess.run(['xdg-open', parent_dir], check=True)

        return {
            'success': True,
            'path': real_path
        }

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to open Finder: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
