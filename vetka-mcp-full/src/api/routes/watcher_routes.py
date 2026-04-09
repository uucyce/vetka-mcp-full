"""
VETKA Watcher Routes - FastAPI Version

@file watcher_routes.py
@status ACTIVE
@phase Phase 54.3
@lastAudit 2026-01-08

Real-time file watcher API routes.
Endpoints for managing directory watches.

Endpoints:
- POST /api/watcher/add - Add directory to watch list (server path)
- POST /api/watcher/add-from-browser - Add files scanned from browser
- POST /api/watcher/remove - Remove directory from watch list
- GET /api/watcher/status - Get current watcher status
- GET /api/watcher/heat - Get adaptive scanner heat scores
"""

import os
import base64
import hashlib
import mimetypes
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Literal

from src.scanners.file_watcher import get_watcher, get_spam_detector, SKIP_PATTERNS
from src.scanners.qdrant_updater import get_qdrant_updater
from src.scanners.mime_policy import validate_ingest_target


router = APIRouter(prefix="/api/watcher", tags=["watcher"])


def _qdrant_base_url() -> str:
    """Resolve Qdrant base URL from runtime env (no src.config dependency)."""
    host = os.getenv("QDRANT_HOST", "127.0.0.1")
    port = os.getenv("QDRANT_PORT", "6333")
    return f"http://{host}:{port}"


# ============================================================
# PYDANTIC MODELS
# ============================================================

class AddWatchRequest(BaseModel):
    """Request to add a directory to watch."""
    path: str
    recursive: Optional[bool] = True
    rescan_existing: Optional[bool] = False


class RemoveWatchRequest(BaseModel):
    """Request to remove a directory from watch."""
    path: str


class BrowserFileInfo(BaseModel):
    """File info from browser FileSystem API."""
    name: str
    relativePath: str
    size: int
    type: str
    lastModified: int
    contentBase64: Optional[str] = None
    contentHash: Optional[str] = None


class AddFromBrowserRequest(BaseModel):
    """Request to add files scanned from browser FileSystem API."""
    rootName: str
    files: List[BrowserFileInfo]
    timestamp: Optional[int] = None
    mode: Literal["metadata_only", "content_small"] = "metadata_only"


class IndexFileRequest(BaseModel):
    """Request to index a single file by its real path."""
    path: str
    recursive: Optional[bool] = False


class CleanupFolderRequest(BaseModel):
    """Request to remove one folder from VETKA index only (disk files untouched)."""
    path: str
    dry_run: Optional[bool] = False
    block_watchdog: Optional[bool] = True


# ============================================================
# ROUTES
# ============================================================

@router.post("/add")
async def add_watch_directory(req: AddWatchRequest, request: Request):
    """
    Add directory to watch list.

    The watcher will monitor this directory for file changes
    and emit Socket.IO events when files are created, modified,
    or deleted.

    Args:
        path: Directory path to watch
        recursive: Watch subdirectories (default: True)

    Returns:
        success: True if added
        watching: List of all watched directories
        message: Status message
    """
    path = req.path
    recursive = req.recursive
    rescan_existing = bool(req.rescan_existing)

    if not path:
        raise HTTPException(status_code=400, detail="No path provided")

    # Expand user path (~)
    path = os.path.expanduser(path)

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Path does not exist: {path}")

    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")

    # Get socketio from app state if available
    socketio = getattr(request.app.state, 'socketio', None)

    # MARKER_90.5.0_FIX_START: Get Qdrant client - try multiple sources
    # Kimi K2 analysis: qdrant_manager is None, but memory_manager.qdrant_client works!
    qdrant_client = None

    # Try 1: app.state.qdrant_manager (QdrantAutoRetry)
    qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
    if qdrant_manager:
        if hasattr(qdrant_manager, 'is_ready') and qdrant_manager.is_ready():
            qdrant_client = qdrant_manager.client
            print(f"[Watcher] ✅ Qdrant client from qdrant_manager")

    # Try 2: memory_manager.qdrant_client (VetkaMemory) - THIS WORKS per Kimi K2
    if not qdrant_client:
        memory_manager = getattr(request.app.state, 'memory_manager', None)
        if memory_manager and hasattr(memory_manager, 'qdrant_client'):
            qdrant_client = memory_manager.qdrant_client
            if qdrant_client:
                print(f"[Watcher] ✅ Qdrant client from memory_manager")

    # Try 3: Direct from components_init singleton
    if not qdrant_client:
        try:
            from src.memory.qdrant_client import get_qdrant_client
            qdrant_client = get_qdrant_client()
            if qdrant_client:
                print(f"[Watcher] ✅ Qdrant client from singleton")
        except ImportError:
            pass

    if not qdrant_client:
        print(f"[Watcher] ⚠️ No Qdrant client available, scan will be skipped")
    # MARKER_90.5.0_FIX_END

    # Pass both socketio and qdrant_client to watcher
    watcher = get_watcher(socketio=socketio, qdrant_client=qdrant_client)

    # MARKER_90.5.1_FIX_START: Check if already watching BEFORE add_directory
    # Root cause: add_directory returns False when already watching, skipping scan!
    already_watching = path in watcher.watched_dirs
    # MARKER_90.5.1_FIX_END

    success = watcher.add_directory(path, recursive=recursive)

    # Phase 54.9: Scan existing files and index to Qdrant.
    # Default behavior: scan only on first add.
    # Rescan for already watched path requires explicit rescan_existing=true.
    indexed_count = 0
    should_scan = bool(success) or (bool(already_watching) and bool(rescan_existing))
    if should_scan:
        try:
            # MARKER_90.6_START: Use unified scan_directory from QdrantUpdater
            if qdrant_client:
                # TODO_95.9: MARKER_COHERENCE_BYPASS_001 - Direct Qdrant write bypasses TripleWriteManager
                # ROOT CAUSE: Watchdog scan uses QdrantUpdater which writes only to Qdrant
                # FIX_96.1: Now uses TripleWrite by default via enable_triple_write=True
                # - get_qdrant_updater default changed to True
                # - Writes now go to Qdrant + Weaviate + ChangeLog
                # STATUS: FIXED (partial - updater still has internal bypass for batch)
                updater = get_qdrant_updater(qdrant_client=qdrant_client, enable_triple_write=True)

                # Reset stop flag and stats before scan
                updater.reset_stop()
                updater.updated_count = 0
                updater.skipped_count = 0

                # Phase 92.4: Progress callback for real-time UI updates
                # Fixed: Run scan in thread executor so event loop can process emits
                import asyncio
                from concurrent.futures import ThreadPoolExecutor

                # Get the running event loop
                main_loop = asyncio.get_running_loop()

                async def emit_progress(current: int, total: int, file_path: str, file_size: int = 0, file_mtime: float = 0):
                    """Emit scan_progress event to frontend"""
                    if socketio:
                        try:
                            progress = int((current / total) * 100) if total > 0 else 0
                            await socketio.emit('scan_progress', {
                                'current': current,
                                'total': total,
                                'progress': progress,
                                'file_path': file_path,
                                'file_size': file_size,
                                'file_mtime': file_mtime,
                                'status': 'scanning'
                            })
                        except Exception as e:
                            pass  # Don't fail scan due to emit errors

                def progress_callback(current: int, total: int, file_path: str, file_size: int = 0, file_mtime: float = 0):
                    """Sync wrapper for async emit - uses run_coroutine_threadsafe"""
                    if socketio and main_loop:
                        try:
                            # Log every 50 files for debugging
                            if current % 50 == 0 or current == total:
                                print(f"[Watcher] Progress: {current}/{total} - {file_path.split('/')[-1]}")
                            # Schedule coroutine in the main event loop from thread
                            asyncio.run_coroutine_threadsafe(
                                emit_progress(current, total, file_path, file_size, file_mtime),
                                main_loop
                            )
                            # Fire and forget - don't wait for result
                        except Exception as e:
                            print(f"[Watcher] Progress callback error: {e}")  # Log errors for debugging

                # Run scan_directory in thread executor so event loop stays free
                # This allows emit_progress coroutines to actually execute
                def run_scan():
                    return updater.scan_directory(path, progress_callback=progress_callback)

                # Use to_thread (Python 3.9+) or run_in_executor
                indexed_count = await asyncio.to_thread(run_scan)

                print(f"[Watcher] Scan complete: {indexed_count} indexed, {updater.skipped_count} skipped (unchanged)")

                # Emit socket events for frontend
                if socketio:
                    try:
                        # Phase 92.3: Emit scan_complete with final count
                        await socketio.emit('scan_complete', {
                            'path': path,
                            'filesCount': indexed_count,
                            'nodes_count': indexed_count,
                            'status': 'complete'
                        })
                        print(f"[Watcher] Emitted scan_complete: {indexed_count} files")

                        await socketio.emit('directory_scanned', {
                            'path': path,
                            'files_count': indexed_count,
                            'root_name': os.path.basename(path)
                        })
                        print(f"[Watcher] Emitted directory_scanned: {path}")
                    except Exception as e:
                        print(f"[Watcher] Socket emit error: {e}")
            # MARKER_90.6_END

        except Exception as e:
            print(f"[Watcher] Scan error: {e}")
            indexed_count = 0

    # MARKER_90.5.1_FIX: Improved response message
    if success:
        message = f"Now watching: {path} ({indexed_count} files indexed)"
    elif already_watching and rescan_existing:
        message = f"Rescanned (already watching): {path} ({indexed_count} files indexed)"
    elif already_watching:
        message = f"Already watching: {path} (rescan skipped)"
    else:
        message = f"Failed to watch: {path}"

    # MARKER_136.W3A: Detect project type
    project_type = None
    try:
        from src.scanners.local_project_scanner import LocalProjectScanner
        scanner = LocalProjectScanner()
        project_type = scanner.detect_project_type(path)
    except Exception as e:
        print(f"[Watcher] Project type detection error: {e}")
        project_type = {"type": "unknown", "framework": None, "languages": [], "confidence": 0.0}

    return {
        'success': success or already_watching,  # True if watching OR rescanned
        'watching': list(watcher.watched_dirs),
        'indexed_count': indexed_count,
        'message': message,
        'project_type': project_type  # MARKER_136.W3A
    }


@router.post("/remove")
async def remove_watch_directory(req: RemoveWatchRequest, request: Request):
    """
    Remove directory from watch list.

    Stops monitoring the specified directory for changes.

    Args:
        path: Directory path to stop watching

    Returns:
        success: True if removed
        watching: List of remaining watched directories
        message: Status message
    """
    path = req.path

    if not path:
        raise HTTPException(status_code=400, detail="No path provided")

    # Expand user path (~)
    path = os.path.expanduser(path)
    path = os.path.abspath(path)

    # Get socketio and qdrant_client for consistency
    socketio = getattr(request.app.state, 'socketio', None)
    qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
    qdrant_client = None
    if qdrant_manager and hasattr(qdrant_manager, 'client'):
        qdrant_client = qdrant_manager.client

    watcher = get_watcher(socketio=socketio, qdrant_client=qdrant_client)
    success = watcher.remove_directory(path)

    return {
        'success': success,
        'watching': list(watcher.watched_dirs),
        'message': f"Stopped watching: {path}" if success else f"Was not watching: {path}"
    }


@router.get("/status")
async def get_watcher_status(request: Request):
    """
    Get current watcher status.

    Returns information about all watched directories,
    active observers, and heat scores.

    Returns:
        watching: List of watched directory paths
        count: Number of watched directories
        heat_scores: Adaptive scanner heat scores per directory
        observers_active: Number of active observer threads
    """
    # Get socketio and qdrant_client for consistency
    socketio = getattr(request.app.state, 'socketio', None)
    qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
    qdrant_client = None
    if qdrant_manager and hasattr(qdrant_manager, 'client'):
        qdrant_client = qdrant_manager.client

    watcher = get_watcher(socketio=socketio, qdrant_client=qdrant_client)
    return watcher.get_status()


@router.get("/heat")
async def get_heat_scores(request: Request):
    """
    Get adaptive scanner heat scores.

    Heat scores indicate how "hot" (frequently modified)
    each directory is. Higher scores mean more frequent scans.

    Returns:
        scores: Dictionary of directory -> heat score (0.0-1.0)
        intervals: Dictionary of directory -> scan interval (seconds)
    """
    # Get socketio and qdrant_client for consistency
    socketio = getattr(request.app.state, 'socketio', None)
    qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
    qdrant_client = None
    if qdrant_manager and hasattr(qdrant_manager, 'client'):
        qdrant_client = qdrant_manager.client

    watcher = get_watcher(socketio=socketio, qdrant_client=qdrant_client)
    heat_scores = watcher.adaptive_scanner.get_all_heat_scores()

    intervals = {
        path: watcher.adaptive_scanner.get_scan_interval(path)
        for path in heat_scores.keys()
    }

    return {
        'scores': heat_scores,
        'intervals': intervals
    }


@router.post("/add-from-browser")
async def add_from_browser(req: AddFromBrowserRequest, request: Request):
    """
    Add files scanned from browser FileSystem API.

    This endpoint receives file metadata from the browser's File System Access API.
    Browser cannot provide full file paths (security), so we receive file metadata
    and index them with relative paths under the root folder name.

    Args:
        rootName: Name of the root folder selected in browser
        files: List of file metadata (name, relativePath, size, type, lastModified)
        timestamp: Optional timestamp of scan

    Returns:
        success: True if indexed
        indexed_count: Number of files indexed
        root_name: The root folder name
    """
    root_name = req.rootName
    files = req.files
    mode = req.mode

    if not root_name:
        raise HTTPException(status_code=400, detail="No rootName provided")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Get Qdrant client from app state for indexing
    qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
    qdrant_client = None

    # QdrantAutoRetry has .client attribute with actual QdrantClient
    if qdrant_manager and hasattr(qdrant_manager, 'client'):
        qdrant_client = qdrant_manager.client

    indexed_count = 0
    errors = []

    if qdrant_client:
        # Use QdrantIncrementalUpdater for proper indexing
        updater = get_qdrant_updater(qdrant_client=qdrant_client)

        from qdrant_client.models import PointStruct
        import uuid
        import time as time_module

        for file_info in files:
            try:
                allowed, policy = validate_ingest_target(
                    file_info.relativePath or file_info.name,
                    int(file_info.size or 0),
                    file_info.type or None,
                )
                if not allowed:
                    errors.append(
                        f"{file_info.relativePath}: {policy.get('code')} ({policy.get('message')})"
                    )
                    continue

                # Phase 54.5: Use 'scanned_file' type so tree_routes can find them
                # Browser files use virtual paths: browser://root/relative/path
                virtual_path = f"browser://{root_name}/{file_info.relativePath}"
                point_id = uuid.uuid5(uuid.NAMESPACE_DNS, virtual_path).int & 0x7FFFFFFFFFFFFFFF

                # Parse parent folder from relative path
                path_parts = file_info.relativePath.rsplit('/', 1)
                if len(path_parts) > 1:
                    parent_folder = f"browser://{root_name}/{path_parts[0]}"
                else:
                    parent_folder = f"browser://{root_name}"

                # Get file extension
                ext_parts = file_info.name.rsplit('.', 1)
                extension = f".{ext_parts[1].lower()}" if len(ext_parts) > 1 else ""

                content_preview = f"[Browser file metadata only: {file_info.name}]"
                if mode == "content_small" and file_info.contentBase64:
                    try:
                        raw = base64.b64decode(file_info.contentBase64, validate=True)
                        if len(raw) > 1_000_000:
                            raise ValueError("contentBase64 too large (>1MB)")
                        decoded = raw.decode("utf-8", errors="replace")
                        if decoded.strip():
                            content_preview = decoded[:4000]
                        else:
                            digest = file_info.contentHash or hashlib.sha256(raw).hexdigest()
                            content_preview = (
                                f"[Binary browser content: mime={file_info.type or 'application/octet-stream'} "
                                f"size={len(raw)} sha256={digest[:16]}]"
                            )
                    except Exception as decode_err:
                        errors.append(f"{file_info.relativePath}: invalid contentBase64 ({decode_err})")

                # Create embedding from filename/path and optional small content payload.
                embed_text = (
                    f"File: {file_info.name}\n"
                    f"Path: {file_info.relativePath}\n"
                    f"Type: {file_info.type}\n"
                    f"Mode: {mode}\n\n"
                    f"{content_preview[:4000]}"
                )
                embedding = updater._get_embedding(embed_text)

                if embedding:
                    # Phase 54.5: Use 'scanned_file' type with all required fields for tree_routes
                    point = PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            'type': 'scanned_file',  # Changed from 'browser_file'
                            'source': 'browser_scanner',
                            'path': virtual_path,
                            'name': file_info.name,
                            'extension': extension,
                            'parent_folder': parent_folder,
                            'relative_path': file_info.relativePath,
                            'root': root_name,
                            'size_bytes': file_info.size,
                            'mime_type': file_info.type,
                            'created_time': file_info.lastModified / 1000,  # JS timestamp to seconds
                            'modified_time': file_info.lastModified / 1000,
                            'last_modified': file_info.lastModified,
                            'updated_at': time_module.time(),
                            'deleted': False,
                            'content': content_preview[:500],
                            'ingest_mode': mode,
                            'content_hash': file_info.contentHash,
                        }
                    )

                    # FIX_96.1: MARKER_COHERENCE_BYPASS_002 - Browser files now use TripleWrite
                    # Browser files have virtual paths and no real content, but we still
                    # want coherent writes to Qdrant + Weaviate + ChangeLog
                    try:
                        from src.orchestration.triple_write_manager import get_triple_write_manager
                        tw = get_triple_write_manager()
                        browser_content = (
                            f"{content_preview[:2000]}\n\n"
                            f"Path: {file_info.relativePath}\n"
                            f"Type: {file_info.type}\n"
                            f"Size: {file_info.size} bytes\n"
                            f"Ingest mode: {mode}"
                        )
                        tw_result = tw.write_file(
                            file_path=virtual_path,
                            content=browser_content,
                            embedding=embedding,
                            metadata={
                                'size': file_info.size,
                                'mtime': file_info.lastModified / 1000,
                                'extension': extension,
                                'depth': virtual_path.count('/'),
                                'source': 'browser_scanner',
                                'mime_type': file_info.type,
                                'ingest_mode': mode,
                            }
                        )
                        if tw_result.get('qdrant'):
                            indexed_count += 1
                        else:
                            # Fallback to direct Qdrant if TW failed
                            qdrant_client.upsert(
                                collection_name=updater.collection_name,
                                points=[point]
                            )
                            indexed_count += 1
                    except Exception as tw_err:
                        # Fallback to direct Qdrant on any TW error
                        print(f"[Watcher] TripleWrite error, using fallback: {tw_err}")
                        qdrant_client.upsert(
                            collection_name=updater.collection_name,
                            points=[point]
                        )
                        indexed_count += 1
                else:
                    errors.append(f"{file_info.relativePath}: embedding failed")

            except Exception as e:
                if len(errors) < 3:  # Only log first 3 errors
                    print(f"[Watcher] Qdrant error for {file_info.name}: {e}")
                errors.append(f"{file_info.relativePath}: {str(e)}")

        print(f"[Watcher] Browser scan: indexed {indexed_count}/{len(files)} files from '{root_name}'")
    else:
        # Fallback: just log the files
        indexed_count = len(files)
        print(f"[Watcher] Browser scan (no Qdrant): received {len(files)} files from '{root_name}'")

    # Track this as a "watched" directory (virtual)
    socketio = getattr(request.app.state, 'socketio', None)
    watcher = get_watcher(socketio=socketio, qdrant_client=qdrant_client)
    watcher.add_browser_directory(root_name, len(files))

    # Phase 54.4: Emit socket event for browser folder (for camera fly-to)
    socketio = getattr(request.app.state, 'socketio', None)
    if socketio:
        try:
            # Emit browser_folder_added event with folder info
            event_data = {
                'root_name': root_name,
                'files_count': len(files),
                'indexed_count': indexed_count,
                'virtual_path': f"browser://{root_name}"
            }
            # We're already in async context, just await
            await socketio.emit('browser_folder_added', event_data)
            print(f"[Watcher] Emitted browser_folder_added: {root_name}")
        except Exception as e:
            print(f"[Watcher] Socket emit error: {e}")

    return {
        'success': True,
        'indexed_count': indexed_count,
        'total_files': len(files),
        'root_name': root_name,
        'mode': mode,
        'errors': errors[:10] if errors else []  # Return first 10 errors
    }


@router.post("/stop-all")
async def stop_all_watchers(request: Request):
    """
    Stop all directory watchers.

    Use with caution - this stops all monitoring.

    Returns:
        success: True
        message: Confirmation message
    """
    # Get socketio and qdrant_client for consistency
    socketio = getattr(request.app.state, 'socketio', None)
    qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
    qdrant_client = None
    if qdrant_manager and hasattr(qdrant_manager, 'client'):
        qdrant_client = qdrant_manager.client

    watcher = get_watcher(socketio=socketio, qdrant_client=qdrant_client)
    watcher.stop_all()

    return {
        'success': True,
        'message': 'All watchers stopped'
    }


def _diagnose_embedding_failure() -> str:
    """MARKER_181.10: Diagnose why embedding failed — surface real error."""
    try:
        import ollama
        ollama.embeddings(model="embeddinggemma:300m", prompt="test")
        return "Ollama OK but embedding returned None — check text content"
    except ConnectionError:
        return "Ollama not running (connection refused). Start with: ollama serve"
    except Exception as e:
        err = str(e)
        if "not found" in err.lower():
            return f"Embedding model not found: {err}. Run: ollama pull embeddinggemma:300m"
        return f"Ollama error: {err}"


@router.post("/index-file")
async def index_single_file(req: IndexFileRequest, request: Request):
    """
    Phase 54.6: Index a single file by its real disk path.

    Used for drag & drop when we resolved the file's real path.
    Reads file content, generates embedding, and stores in Qdrant.

    Args:
        path: Absolute path to the file
        recursive: If path is directory, scan recursively (default: False)

    Returns:
        success: True if indexed
        path: The indexed file path
        message: Status message
    """
    import time as time_module
    import uuid
    from pathlib import Path

    file_path = req.path

    if not file_path:
        raise HTTPException(status_code=400, detail="No path provided")

    # Expand user path (~)
    file_path = os.path.expanduser(file_path)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File does not exist: {file_path}")

    if os.path.isdir(file_path):
        # For directories, use the /add endpoint logic
        raise HTTPException(status_code=400, detail="Use /add endpoint for directories")

    file_stat = os.stat(file_path)
    allowed, policy = validate_ingest_target(file_path, int(file_stat.st_size))
    if not allowed:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": policy.get("code", "INGEST_POLICY_BLOCK"),
                    "message": policy.get("message", "Ingest policy blocked file"),
                    "details": {
                        "path": file_path,
                        "extension": policy.get("extension"),
                        "category": policy.get("category"),
                        "mime_type": policy.get("mime_type"),
                    },
                }
            },
        )

    # Get Qdrant client from app state
    qdrant_manager = getattr(request.app.state, 'qdrant_manager', None)
    qdrant_client = None

    if qdrant_manager and hasattr(qdrant_manager, 'client'):
        qdrant_client = qdrant_manager.client

    if not qdrant_client:
        raise HTTPException(status_code=500, detail="Qdrant client not available")

    try:
        # Use QdrantIncrementalUpdater for proper indexing with embedding
        updater = get_qdrant_updater(qdrant_client=qdrant_client)

        # Read file content with binary-aware fallback
        file_obj = Path(file_path)
        mime_type, _ = mimetypes.guess_type(str(file_obj))
        mime_type = mime_type or "application/octet-stream"
        is_text_like = mime_type.startswith("text/") or file_obj.suffix.lower() in {
            ".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".ts", ".tsx", ".html", ".css"
        }
        media_chunks = []
        if is_text_like:
            content = file_obj.read_text(encoding='utf-8', errors='replace')
        else:
            # OCR route for image/PDF in drag-drop index path
            ocr_text = ""
            if file_obj.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}:
                try:
                    from src.ocr.ocr_processor import get_ocr_processor
                    ocr = get_ocr_processor()
                    ocr_result = ocr.process_pdf(str(file_obj)) if file_obj.suffix.lower() == ".pdf" else ocr.process_image(str(file_obj))
                    if ocr_result.get("text") and not ocr_result.get("error"):
                        ocr_text = ocr_result["text"][:8000]
                except Exception as ocr_err:
                    print(f"[Watcher] OCR error for {file_obj.name}: {ocr_err}")

            if ocr_text:
                content = ocr_text
            else:
                # AV transcription route for audio/video
                av_text = ""
                if file_obj.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".mp4", ".mov", ".mkv", ".avi", ".webm"}:
                    try:
                        from src.voice.stt_engine import WhisperSTT
                        stt = WhisperSTT(model_name="base")
                        tr = stt.transcribe(str(file_obj))
                        av_text = (tr.get("text") or "").strip()
                        segments = tr.get("segments", []) or []
                        for seg in segments[:128]:
                            try:
                                media_chunks.append(
                                    {
                                        "start_sec": float(seg.get("start", 0.0) or 0.0),
                                        "end_sec": float(seg.get("end", 0.0) or 0.0),
                                        "text": str(seg.get("text", "") or ""),
                                        "confidence": float(tr.get("confidence", 0.0) or 0.0),
                                    }
                                )
                            except Exception:
                                continue
                    except Exception as av_err:
                        print(f"[Watcher] AV transcription error for {file_obj.name}: {av_err}")

                if av_text:
                    content = av_text[:8000]
                else:
                    raw = file_obj.read_bytes()
                    digest = hashlib.sha256(raw).hexdigest()
                    content = (
                        f"[Binary file summary]\n"
                        f"mime={mime_type}\n"
                        f"size_bytes={len(raw)}\n"
                        f"sha256={digest}\n"
                        f"path={file_path}"
                    )

        # Generate point ID from path
        point_id = uuid.uuid5(uuid.NAMESPACE_DNS, file_path).int & 0x7FFFFFFFFFFFFFFF

        # Get file stats
        stat = file_obj.stat()

        # MARKER_181.10: No truncation — chunked embedding handles any text length
        embed_text = f"File: {file_obj.name}\n\n{content}"
        embedding = updater._get_embedding(embed_text)

        if not embedding:
            diag = _diagnose_embedding_failure()
            print(f"[Watcher] ❌ Embedding failed for {file_obj.name}: {diag}")
            raise HTTPException(status_code=500, detail=f"Embedding failed for {file_obj.name}: {diag}")

        from qdrant_client.models import PointStruct

        # Create Qdrant point with proper metadata
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                'type': 'scanned_file',
                'source': 'drag_drop_resolved',
                'path': file_path,
                'name': file_obj.name,
                'extension': file_obj.suffix.lower(),
                'parent_folder': str(file_obj.parent),
                'size_bytes': stat.st_size,
                'mime_type': mime_type,
                'created_time': stat.st_ctime,
                'modified_time': stat.st_mtime,
                'content': content[:500],  # Preview
                'content_hash': updater._get_content_hash(file_obj),
                'media_chunks': media_chunks[:32],
                'extraction_version': 'phase153_mm_v1',
                'updated_at': time_module.time(),
                'deleted': False
            }
        )

        # FIX_96.1: MARKER_COHERENCE_BYPASS_003 - Drag-drop files now use TripleWrite
        # Single file indexing now goes through TripleWrite for coherent persistence
        try:
            from src.orchestration.triple_write_manager import get_triple_write_manager
            tw = get_triple_write_manager()
            tw_result = tw.write_file(
                file_path=file_path,
                content=content,
                embedding=embedding,
                metadata={
                    'type': 'scanned_file',
                    'path': file_path,
                    'name': file_obj.name,
                    'parent_folder': str(file_obj.parent),
                    'size': stat.st_size,
                    'size_bytes': stat.st_size,
                    'mtime': stat.st_mtime,
                    'created_time': stat.st_ctime,
                    'modified_time': stat.st_mtime,
                    'mime_type': mime_type,
                    'extension': file_obj.suffix.lower(),
                    'depth': file_path.count('/'),
                    'source': 'drag_drop_resolved',
                    'deleted': False,
                    'content': content[:500],
                    'media_chunks': media_chunks[:32],
                    'extraction_version': 'phase153_mm_v1',
                    'content_hash': updater._get_content_hash(file_obj),
                    'updated_at': time_module.time(),
                }
            )
            if media_chunks:
                modality = 'audio' if file_obj.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"} else 'video'
                tw.write_media_chunks(
                    file_path=file_path,
                    media_chunks=media_chunks,
                    modality=modality,
                )
            if tw_result.get('qdrant'):
                print(f"[Watcher] Indexed via TripleWrite: {file_path}")
            else:
                # Fallback to direct Qdrant if TW Qdrant write failed
                qdrant_client.upsert(
                    collection_name='vetka_elisya',
                    points=[point]
                )
                print(f"[Watcher] Indexed via fallback Qdrant: {file_path}")
        except Exception as tw_err:
            # Fallback to direct Qdrant on any TW error
            print(f"[Watcher] TripleWrite error, using fallback: {tw_err}")
            qdrant_client.upsert(
                collection_name='vetka_elisya',
                points=[point]
            )
            print(f"[Watcher] Indexed file (fallback): {file_path}")

        # Emit socket event for tree reload
        socketio = getattr(request.app.state, 'socketio', None)
        if socketio:
            try:
                await socketio.emit('file_indexed', {
                    'path': file_path,
                    'name': file_obj.name,
                    'parent_folder': str(file_obj.parent)
                })
            except Exception as e:
                print(f"[Watcher] Socket emit error: {e}")

        return {
            'success': True,
            'path': file_path,
            'name': file_obj.name,
            'message': f'Indexed: {file_obj.name}'
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Watcher] Index file error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-event")
async def test_watcher_event(request: Request):
    """
    MARKER_90.10: Test watcher event processing.

    Simulates a file created event to verify the entire pipeline:
    1. VetkaFileHandler.on_any_event
    2. _on_file_change callback
    3. handle_watcher_event
    4. Qdrant indexing

    Use this to debug why automatic indexing isn't working.
    """
    import json

    body = await request.json()
    test_path = body.get('path', '/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/90_ph/TEST_EVENT.md')
    event_type = body.get('type', 'created')

    watcher = getattr(request.app.state, 'file_watcher', None)
    if not watcher:
        return {"error": "File watcher not initialized"}

    # Simulate event
    fake_event = {
        'type': event_type,
        'path': test_path,
        'time': time.time()
    }

    print(f"[TEST] Simulating watcher event: {fake_event}")

    try:
        # Call _on_file_change directly (bypasses debounce)
        watcher._on_file_change(fake_event)

        return {
            'success': True,
            'event': fake_event,
            'message': f'Simulated {event_type} event for {test_path}'
        }
    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


@router.delete("/cleanup-browser-files")
async def cleanup_browser_files():
    """
    Remove all browser:// virtual files from Qdrant.

    Browser-scanned files with virtual paths don't have real coordinates
    and clutter the database. This endpoint removes them.

    Phase 54.8: Cleanup utility for browser:// prefixed files.
    """
    try:
        from qdrant_client import QdrantClient, models

        qdrant_client = QdrantClient(url=_qdrant_base_url())

        # Delete all points with path starting with "browser://"
        qdrant_client.delete(
            collection_name='vetka_elisya',
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="path",
                            match=models.MatchText(text="browser://")
                        )
                    ]
                )
            )
        )

        print("[Watcher] Cleaned up browser:// virtual files")

        return {
            'success': True,
            'message': 'Browser files cleaned up from Qdrant'
        }

    except Exception as e:
        print(f"[Watcher] Cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup-playground-files")
async def cleanup_playground_files(dry_run: bool = False):
    """
    Remove indexed playground duplicates from Qdrant.

    Targets paths containing:
    - /data/playgrounds/
    - /.playgrounds/
    """
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointIdsList

        qdrant_client = QdrantClient(url=_qdrant_base_url())
        prefixes = ("/data/playgrounds/", "/.playgrounds/")

        matched_ids = []
        offset = None
        while True:
            points, offset = qdrant_client.scroll(
                collection_name='vetka_elisya',
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                path = str(payload.get("path", ""))
                if any(pref in path for pref in prefixes):
                    matched_ids.append(point.id)
            if offset is None:
                break

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "matched_count": len(matched_ids),
                "message": "Dry run complete; no points deleted",
            }

        deleted = 0
        batch_size = 200
        for i in range(0, len(matched_ids), batch_size):
            batch = matched_ids[i:i + batch_size]
            qdrant_client.delete(
                collection_name='vetka_elisya',
                points_selector=PointIdsList(points=batch),
                wait=True,
            )
            deleted += len(batch)

        print(f"[Watcher] Cleaned playground files from Qdrant: {deleted}")
        return {
            "success": True,
            "dry_run": False,
            "matched_count": len(matched_ids),
            "deleted_count": deleted,
            "message": "Playground files cleaned up from Qdrant",
        }

    except Exception as e:
        print(f"[Watcher] Playground cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MARKER_159.CLEAN_API_FOLDER_SCOPE
# Selective cleanup for one folder from VETKA stores + optional watchdog block.
@router.post("/cleanup-folder-from-vetka")
async def cleanup_folder_from_vetka(req: CleanupFolderRequest, request: Request):
    """
    Selectively remove one folder from VETKA index/storage.

    IMPORTANT:
    - Removes from VETKA stores only (Qdrant + Weaviate)
    - Does NOT delete files from disk
    - Optionally blocks watchdog updates for this folder
    """
    import requests as http_requests

    raw_path = (req.path or "").strip()
    if not raw_path:
        raise HTTPException(status_code=400, detail="Path is required")

    target_path = os.path.abspath(os.path.expanduser(raw_path))
    target_prefix = target_path.replace("\\", "/")
    if not os.path.isdir(target_path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {target_path}")

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointIdsList

        qdrant_client = QdrantClient(url=_qdrant_base_url())

        matched_ids = []
        matched_paths = set()
        offset = None

        while True:
            points, offset = qdrant_client.scroll(
                collection_name="vetka_elisya",
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                p = str(payload.get("path", "")).replace("\\", "/")
                if p and (p == target_prefix or p.startswith(target_prefix + "/")):
                    matched_ids.append(point.id)
                    matched_paths.add(p)
            if offset is None:
                break

        # Weaviate match pass (file_path prefix in VetkaLeaf objects)
        weaviate_url = "http://localhost:8080"
        weaviate_candidates = []
        try:
            resp = http_requests.get(
                f"{weaviate_url}/v1/objects?class=VetkaLeaf&limit=10000",
                timeout=15,
            )
            if resp.status_code == 200:
                weaviate_candidates = resp.json().get("objects", []) or []
        except Exception:
            weaviate_candidates = []

        weaviate_ids = []
        for obj in weaviate_candidates:
            props = obj.get("properties", {}) or {}
            file_path = str(props.get("file_path", "")).replace("\\", "/")
            if file_path and (file_path == target_prefix or file_path.startswith(target_prefix + "/")):
                obj_id = obj.get("id")
                if obj_id:
                    weaviate_ids.append(str(obj_id))

        # MARKER_159.CLEAN_API_DRY_RUN: Preview counts without mutating storage.
        if bool(req.dry_run):
            return {
                "success": True,
                "dry_run": True,
                "path": target_path,
                "message": "Dry run complete; no data deleted",
                "qdrant_matched": len(matched_ids),
                "weaviate_matched": len(weaviate_ids),
                "watchdog_will_block": bool(req.block_watchdog),
            }

        # Delete from Qdrant
        qdrant_deleted = 0
        batch_size = 200
        for i in range(0, len(matched_ids), batch_size):
            batch = matched_ids[i:i + batch_size]
            qdrant_client.delete(
                collection_name="vetka_elisya",
                points_selector=PointIdsList(points=batch),
                wait=True,
            )
            qdrant_deleted += len(batch)

        # Delete from Weaviate
        weaviate_deleted = 0
        for obj_id in weaviate_ids:
            try:
                d = http_requests.delete(
                    f"{weaviate_url}/v1/objects/VetkaLeaf/{obj_id}",
                    timeout=10,
                )
                if d.status_code in (200, 204):
                    weaviate_deleted += 1
            except Exception:
                continue

        # MARKER_159.CLEAN_WATCHDOG_BLOCK: Prevent re-index of cleaned folder.
        block_added = False
        removed_watchers = []
        if bool(req.block_watchdog):
            socketio = getattr(request.app.state, "socketio", None)
            qdrant_manager = getattr(request.app.state, "qdrant_manager", None)
            qdrant_for_watcher = None
            if qdrant_manager and hasattr(qdrant_manager, "client"):
                qdrant_for_watcher = qdrant_manager.client
            watcher = get_watcher(socketio=socketio, qdrant_client=qdrant_for_watcher)

            if hasattr(watcher, "add_user_block_pattern"):
                block_added = bool(watcher.add_user_block_pattern(target_path, persist=True))
            else:
                if target_path not in SKIP_PATTERNS:
                    SKIP_PATTERNS.append(target_path)
                    block_added = True

            for watched in list(watcher.watched_dirs):
                watched_norm = os.path.abspath(str(watched))
                if watched_norm == target_path or watched_norm.startswith(target_path + os.sep):
                    if watcher.remove_directory(watched_norm):
                        removed_watchers.append(watched_norm)

        # Invalidate tree cache immediately if route module is loaded
        try:
            from src.api.routes import tree_routes
            tree_routes._tree_structure_cache["folders"] = None
            tree_routes._tree_structure_cache["files_by_folder"] = None
        except Exception:
            pass

        return {
            "success": True,
            "dry_run": False,
            "path": target_path,
            "message": "Folder cleaned from VETKA index (disk files preserved)",
            "qdrant_deleted": qdrant_deleted,
            "weaviate_deleted": weaviate_deleted,
            "watchdog_blocked": bool(req.block_watchdog),
            "watchdog_block_added": block_added,
            "watchers_removed": removed_watchers,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Watcher] Folder cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SPAM DETECTOR ENDPOINTS — MARKER_146.5_SPAM
# ============================================================

@router.get("/spam-status")
async def get_spam_status():
    """Get currently muted directories from SpamDetector."""
    detector = get_spam_detector()
    muted = detector.get_muted_dirs()
    import time
    now = time.time()
    return {
        'muted_directories': [
            {
                'path': path,
                'unmute_in_seconds': round(unmute_at - now),
                'unmute_at': unmute_at
            }
            for path, unmute_at in muted.items()
        ],
        'skip_patterns': list(SKIP_PATTERNS),
        'total_skip_patterns': len(SKIP_PATTERNS)
    }


class AddSkipPatternRequest(BaseModel):
    """Request to add a pattern to SKIP_PATTERNS at runtime."""
    pattern: str


@router.post("/spam-block")
async def add_skip_pattern(req: AddSkipPatternRequest):
    """
    Add a pattern to SKIP_PATTERNS at runtime.
    This is a temporary block — survives until server restart.
    To make permanent, add to SKIP_PATTERNS in file_watcher.py.
    """
    pattern = req.pattern.strip()
    if not pattern:
        raise HTTPException(status_code=400, detail="Pattern cannot be empty")

    if pattern in SKIP_PATTERNS:
        return {'success': False, 'message': f"Pattern '{pattern}' already in SKIP_PATTERNS"}

    SKIP_PATTERNS.append(pattern)
    print(f"[Watcher] 🚫 Added runtime skip pattern: '{pattern}'")
    return {
        'success': True,
        'message': f"Pattern '{pattern}' added to SKIP_PATTERNS (runtime only)",
        'total_skip_patterns': len(SKIP_PATTERNS),
        'note': 'This is temporary. Add to SKIP_PATTERNS in file_watcher.py for permanence.'
    }
