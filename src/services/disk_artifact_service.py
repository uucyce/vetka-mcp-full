"""
VETKA Phase 104.9 - Disk Artifact Service

MARKER_104_ARTIFACT_DISK

Saves large artifacts to disk for persistence.
Integrates with Socket.IO for artifact_approval events.

Flow:
1. Check content length >= 500 chars
2. Sanitize artifact name for security
3. Save to artifacts/{sanitized_name}.{ext}
4. Emit artifact_approval event if socketio provided

Security:
- Sanitizes names to prevent path traversal
- Limits filename length to 100 chars
- Only allows alphanumeric, underscore, hyphen, period

@file disk_artifact_service.py
@status ACTIVE
@phase 104.9
@depends pathlib, re, logging
@used_by src.orchestration, src.api.handlers
"""

import asyncio
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# MARKER_104_ARTIFACT_DISK
# Directory for saving artifacts
ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "artifacts"

# Extension mapping for artifact types
EXT_MAP = {
    "python": "py",
    "typescript": "ts",
    "javascript": "js",
    "markdown": "md",
    "rust": "rs",
    "go": "go",
    "java": "java",
    "cpp": "cpp",
    "c": "c",
    "csharp": "cs",
    "ruby": "rb",
    "php": "php",
    "swift": "swift",
    "kotlin": "kt",
    "scala": "scala",
    "sql": "sql",
    "bash": "sh",
    "shell": "sh",
    "yaml": "yaml",
    "json": "json",
    "html": "html",
    "css": "css",
}

# Minimum content length for disk persistence
MIN_CONTENT_LENGTH = 500


def sanitize_artifact_name(name: str) -> str:
    """
    Sanitize artifact name to prevent path traversal and security issues.

    MARKER_104_ARTIFACT_DISK

    Security measures:
    - Only allow alphanumeric, underscore, hyphen, period
    - Replace invalid chars with underscore
    - Prevent path traversal (..)
    - Limit length to 100 chars

    Args:
        name: Original artifact name

    Returns:
        Sanitized name safe for filesystem
    """
    # Replace any non-safe characters with underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_\-.]', '_', name)
    # Prevent path traversal by replacing .. with underscore
    sanitized = sanitized.replace('..', '_')
    # Remove leading/trailing underscores and periods (security)
    sanitized = sanitized.strip('_.')
    # Limit length to 100 chars
    sanitized = sanitized[:100]
    # Fallback if empty after sanitization
    if not sanitized:
        sanitized = f"artifact_{uuid.uuid4().hex[:8]}"

    return sanitized


async def create_disk_artifact(
    name: str,
    content: str,
    artifact_type: str,
    workflow_id: str,
    socketio=None
) -> Optional[str]:
    """
    Save large artifact to disk.

    MARKER_104_ARTIFACT_DISK

    Only saves if content >= 500 chars. Emits artifact_approval event via
    socketio if provided for UI notification.

    Args:
        name: Artifact name (will be sanitized)
        content: Artifact content (code/text)
        artifact_type: Type of artifact (python, typescript, etc.)
        workflow_id: Associated workflow ID
        socketio: Optional Socket.IO instance for emitting events

    Returns:
        Filepath if saved successfully, None otherwise

    Example:
        filepath = await create_disk_artifact(
            name="hello_world",
            content="def hello(): print('Hello, World!')\n" * 50,
            artifact_type="python",
            workflow_id="wf_12345",
            socketio=sio
        )
        # Returns: "artifacts/hello_world.py"
    """
    # MARKER_104_ARTIFACT_DISK: Check minimum content length
    if len(content) < MIN_CONTENT_LENGTH:
        logger.debug(
            f"[DiskArtifact] Skipping - content too short "
            f"({len(content)} < {MIN_CONTENT_LENGTH}): {name}"
        )
        return None

    try:
        # 1. Sanitize name for security
        safe_name = sanitize_artifact_name(name)

        # 2. Determine file extension
        ext = EXT_MAP.get(artifact_type.lower(), "txt")

        # GROK_FIX_BLOCKING_IO: Use executor for all file I/O operations
        loop = asyncio.get_running_loop()

        # 3. Ensure artifacts directory exists
        await loop.run_in_executor(None, lambda: ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True))

        # 4. Build filepath
        filename = f"{safe_name}.{ext}"
        filepath = ARTIFACTS_DIR / filename

        # 5. Handle duplicate filenames by appending timestamp
        if filepath.exists():
            timestamp = int(datetime.now().timestamp())
            filename = f"{safe_name}_{timestamp}.{ext}"
            filepath = ARTIFACTS_DIR / filename

        # 6. Write content to disk (non-blocking)
        await loop.run_in_executor(None, lambda: filepath.write_text(content, encoding='utf-8'))

        logger.info(
            f"[DiskArtifact] Saved: {filepath} "
            f"({len(content)} chars, type={artifact_type})"
        )

        # 7. Emit artifact_approval event if socketio provided
        if socketio:
            artifact_data = {
                "artifact_id": str(uuid.uuid4()),
                "name": safe_name,
                "filename": filename,
                "filepath": str(filepath),
                "artifact_type": artifact_type,
                "content_length": len(content),
                "content_preview": content[:200] + "..." if len(content) > 200 else content,
                "workflow_id": workflow_id,
                "created_at": datetime.now().isoformat(),
                "status": "pending_approval",
            }

            try:
                await socketio.emit('artifact_approval', artifact_data)
                logger.info(
                    f"[DiskArtifact] Emitted artifact_approval for: {filename}"
                )
            except Exception as emit_error:
                logger.warning(
                    f"[DiskArtifact] Failed to emit artifact_approval: {emit_error}"
                )

        # Return relative filepath from project root
        return str(filepath.relative_to(filepath.parent.parent))

    except Exception as e:
        logger.error(f"[DiskArtifact] Failed to save artifact '{name}': {e}")
        return None


def get_artifact_path(name: str, artifact_type: str) -> Path:
    """
    Get the expected path for an artifact.

    MARKER_104_ARTIFACT_DISK

    Args:
        name: Artifact name (will be sanitized)
        artifact_type: Type of artifact

    Returns:
        Path object for the artifact location
    """
    safe_name = sanitize_artifact_name(name)
    ext = EXT_MAP.get(artifact_type.lower(), "txt")
    return ARTIFACTS_DIR / f"{safe_name}.{ext}"


async def list_artifacts() -> list:
    """
    List all artifacts in the artifacts directory.

    MARKER_104_ARTIFACT_DISK

    Returns:
        List of dicts with artifact info: {name, path, size, modified}
    """
    # GROK_FIX_BLOCKING_IO: Use executor for directory iteration
    loop = asyncio.get_running_loop()

    def _list_artifacts_sync() -> list:
        artifacts = []

        if not ARTIFACTS_DIR.exists():
            return artifacts

        for filepath in ARTIFACTS_DIR.iterdir():
            if filepath.is_file() and not filepath.name.startswith('.'):
                try:
                    stat = filepath.stat()
                    artifacts.append({
                        "name": filepath.stem,
                        "filename": filepath.name,
                        "path": str(filepath),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "extension": filepath.suffix[1:] if filepath.suffix else "txt",
                    })
                except Exception as e:
                    logger.warning(f"[DiskArtifact] Failed to stat {filepath}: {e}")

        return sorted(artifacts, key=lambda x: x['modified'], reverse=True)

    return await loop.run_in_executor(None, _list_artifacts_sync)


async def read_artifact(name: str, artifact_type: str) -> Optional[str]:
    """
    Read artifact content from disk.

    MARKER_104_ARTIFACT_DISK

    Args:
        name: Artifact name
        artifact_type: Type of artifact

    Returns:
        Artifact content or None if not found
    """
    filepath = get_artifact_path(name, artifact_type)

    if not filepath.exists():
        logger.warning(f"[DiskArtifact] Artifact not found: {filepath}")
        return None

    # GROK_FIX_BLOCKING_IO: Use executor for file read
    loop = asyncio.get_running_loop()

    try:
        return await loop.run_in_executor(None, lambda: filepath.read_text(encoding='utf-8'))
    except Exception as e:
        logger.error(f"[DiskArtifact] Failed to read {filepath}: {e}")
        return None


async def delete_artifact(name: str, artifact_type: str) -> bool:
    """
    Delete artifact from disk.

    MARKER_104_ARTIFACT_DISK

    Args:
        name: Artifact name
        artifact_type: Type of artifact

    Returns:
        True if deleted, False otherwise
    """
    filepath = get_artifact_path(name, artifact_type)

    if not filepath.exists():
        logger.warning(f"[DiskArtifact] Cannot delete - not found: {filepath}")
        return False

    # GROK_FIX_BLOCKING_IO: Use executor for file delete
    loop = asyncio.get_running_loop()

    try:
        await loop.run_in_executor(None, filepath.unlink)
        logger.info(f"[DiskArtifact] Deleted: {filepath}")
        return True
    except Exception as e:
        logger.error(f"[DiskArtifact] Failed to delete {filepath}: {e}")
        return False


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'create_disk_artifact',
    'sanitize_artifact_name',
    'get_artifact_path',
    'list_artifacts',
    'read_artifact',
    'delete_artifact',
    'ARTIFACTS_DIR',
    'EXT_MAP',
    'MIN_CONTENT_LENGTH',
]
