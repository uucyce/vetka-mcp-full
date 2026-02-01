"""
MARKER_103.6_START: Universal Staging Utilities for VETKA

Shared staging logic for both Spawn and Artifacts.
Pattern: Generate → Stage (JSON/Qdrant) → Review → Apply

This unifies:
- Spawn pipeline results (code files from agents)
- Artifacts (code blocks from Dev responses)

MARKER_104_MEMORY_STAGING: Added ELISION compression for large entries
Large task results are optionally compressed to save disk space.

@status: active
@phase: 104
@depends: src/utils/artifact_extractor.py, src/memory/qdrant_client.py, src/memory/elision.py
@used_by: scripts/retro_apply.py, src/api/handlers/group_message_handler.py
"""

import json
import re
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# MARKER_103.6: Universal staging file (replaces separate files)
STAGING_FILE = Path(__file__).parent.parent.parent / "data" / "staging.json"


def _load_staging() -> Dict[str, Any]:
    """
    Load staging data from JSON, auto-expanding compressed entries.

    MARKER_104_MEMORY_STAGING: Handles decompression of ELISION-compressed results.
    Checks for _compressed flag and auto-expands using stored legend.
    """
    if STAGING_FILE.exists():
        try:
            data = json.loads(STAGING_FILE.read_text(encoding='utf-8'))

            # Auto-expand compressed entries
            data = _expand_compressed_entries(data)

            return data
        except json.JSONDecodeError:
            logger.warning("[Staging] Corrupt staging.json, starting fresh")
            return {"version": "1.0", "spawn": {}, "artifacts": {}}
    return {"version": "1.0", "spawn": {}, "artifacts": {}}


def _expand_compressed_entries(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Auto-expand ELISION-compressed entries in staging data.

    MARKER_104_MEMORY_STAGING: Decompression helper.
    Recursively traverses data structure and expands any entries with _compressed flag.
    """
    try:
        from src.memory.elision import get_elision_compressor
        compressor = get_elision_compressor()

        for category in ['spawn', 'artifacts']:
            if category in data:
                for task_id, task in data[category].items():
                    if isinstance(task, dict) and task.get('_compressed'):
                        if 'result' in task and isinstance(task['result'], str):
                            # Extract legend if present
                            legend = task.get('_legend', {})

                            try:
                                expanded = compressor.expand(task['result'], legend)
                                task['result'] = json.loads(expanded) if expanded.startswith('{') or expanded.startswith('[') else expanded

                                # Clean up compression metadata
                                task.pop('_compressed', None)
                                task.pop('_legend', None)
                                task.pop('_original_size', None)

                                logger.debug(f"[Staging] Expanded compressed task: {task_id}")
                            except Exception as e:
                                logger.warning(f"[Staging] Failed to expand {task_id}: {e}")
                                # Keep original compressed data if expansion fails
    except ImportError:
        # ELISION not available, skip decompression
        pass
    except Exception as e:
        logger.warning(f"[Staging] Error during decompression: {e}")

    return data


def _save_staging(data: Dict[str, Any], compress_large: bool = True) -> bool:
    """
    Save staging data to JSON (atomic write) with optional ELISION compression.

    MARKER_104_MEMORY_STAGING: Compresses large entries to save disk space.

    Args:
        data: Staging data to save
        compress_large: Whether to compress large entries (>2000 chars)

    Returns:
        True if save successful, False otherwise
    """
    try:
        # Optional ELISION compression for large entries
        if compress_large:
            data = _compress_large_entries(data)

        STAGING_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp_file = STAGING_FILE.with_suffix('.tmp')
        temp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        temp_file.rename(STAGING_FILE)
        return True
    except Exception as e:
        logger.error(f"[Staging] Failed to save: {e}")
        return False


def _compress_large_entries(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compress large entries in staging data using ELISION.

    MARKER_104_MEMORY_STAGING: Compression helper.
    Only compresses 'result' fields >2000 chars in spawn and artifacts categories.
    Stores compression metadata (_compressed, _legend, _original_size).
    """
    try:
        from src.memory.elision import get_elision_compressor
        compressor = get_elision_compressor()

        compression_stats = {
            'compressed_count': 0,
            'total_original_size': 0,
            'total_compressed_size': 0,
        }

        for category in ['spawn', 'artifacts']:
            if category in data:
                for task_id, task in data[category].items():
                    if isinstance(task, dict) and 'result' in task:
                        result = task['result']
                        result_str = str(result)

                        # Only compress if large enough
                        if len(result_str) > 2000:
                            try:
                                # Compress using level 2 (key abbreviation + path compression)
                                # Level 2 is safe and reversible, ~40-50% savings
                                compressed_result = compressor.compress(result, level=2)

                                # Store compressed version with metadata
                                task['result'] = compressed_result.compressed
                                task['_compressed'] = True
                                task['_legend'] = compressed_result.legend
                                task['_original_size'] = len(result_str)

                                compression_stats['compressed_count'] += 1
                                compression_stats['total_original_size'] += len(result_str)
                                compression_stats['total_compressed_size'] += len(compressed_result.compressed)

                                logger.debug(
                                    f"[Staging] Compressed {task_id} in {category}: "
                                    f"{len(result_str)} -> {len(compressed_result.compressed)} bytes "
                                    f"({compressed_result.compression_ratio:.1f}x)"
                                )
                            except Exception as e:
                                logger.warning(f"[Staging] Failed to compress {task_id}: {e}")
                                # Keep original if compression fails

        if compression_stats['compressed_count'] > 0:
            total_saved = compression_stats['total_original_size'] - compression_stats['total_compressed_size']
            logger.info(
                f"[Staging] Compression complete: {compression_stats['compressed_count']} entries, "
                f"saved {total_saved} bytes ({100*total_saved/compression_stats['total_original_size']:.1f}%)"
            )

    except ImportError:
        # ELISION not available, skip compression
        logger.debug("[Staging] ELISION not available, skipping compression")
    except Exception as e:
        logger.warning(f"[Staging] Error during compression: {e}")

    return data


# ============================================================
# ARTIFACT STAGING (from Dev agent responses)
# ============================================================

def stage_artifact(
    artifact: Dict[str, Any],
    qa_score: float,
    agent: str = "Dev",
    group_id: Optional[str] = None,
    source_message_id: Optional[str] = None
) -> Optional[str]:
    """
    Stage an artifact for later review/apply.

    Args:
        artifact: Dict from extract_artifacts() with keys:
                  {id, type, filename, language, content, lines, agent, created_at}
        qa_score: QA score (0-1) for this artifact
        agent: Agent that created it (Dev, Architect, etc.)
        group_id: Optional group chat ID for context
        source_message_id: Optional source message ID for traceability

    Returns:
        task_id if staged successfully, None otherwise
    """
    try:
        data = _load_staging()
        task_id = f"art_{int(datetime.now().timestamp())}_{str(uuid.uuid4())[:8]}"

        # MARKER_103_ARTIFACT_LINK: Added source_message_id for traceability
        staged_artifact = {
            **artifact,
            "task_id": task_id,
            "qa_score": qa_score,
            "agent": agent,
            "group_id": group_id,
            "source_message_id": source_message_id,
            "status": "staged",
            "staged_at": datetime.now().isoformat()
        }

        data["artifacts"][task_id] = staged_artifact

        if _save_staging(data):
            logger.info(f"[Staging] Artifact staged: {task_id} ({artifact.get('filename', 'unknown')})")
            return task_id
        return None

    except Exception as e:
        logger.error(f"[Staging] Failed to stage artifact: {e}")
        return None


def stage_artifacts_batch(
    artifacts: List[Dict[str, Any]],
    qa_score: float,
    agent: str = "Dev",
    group_id: Optional[str] = None,
    source_message_id: Optional[str] = None
) -> List[str]:
    """Stage multiple artifacts at once."""
    task_ids = []
    for artifact in artifacts:
        task_id = stage_artifact(artifact, qa_score, agent, group_id, source_message_id)
        if task_id:
            task_ids.append(task_id)
    return task_ids


def get_staged_artifacts(
    status: Optional[str] = None,
    min_qa_score: float = 0.0
) -> List[Dict[str, Any]]:
    """Get staged artifacts, optionally filtered."""
    data = _load_staging()
    artifacts = list(data.get("artifacts", {}).values())

    if status:
        artifacts = [a for a in artifacts if a.get("status") == status]
    if min_qa_score > 0:
        artifacts = [a for a in artifacts if a.get("qa_score", 0) >= min_qa_score]

    return sorted(artifacts, key=lambda x: x.get("staged_at", ""), reverse=True)


def update_artifact_status(task_id: str, status: str) -> bool:
    """Update artifact status (staged → approved → applied)."""
    data = _load_staging()
    if task_id in data.get("artifacts", {}):
        data["artifacts"][task_id]["status"] = status
        data["artifacts"][task_id]["updated_at"] = datetime.now().isoformat()
        return _save_staging(data)
    return False


# ============================================================
# SPAWN STAGING (from pipeline results)
# ============================================================

def stage_spawn_result(
    task_id: str,
    subtask: Dict[str, Any],
    content: str
) -> bool:
    """
    Stage a spawn subtask result (already handled by pipeline, but can re-stage).

    Note: Spawn results are primarily in pipeline_tasks.json.
    This is for unified access via staging.json.
    """
    try:
        data = _load_staging()

        staged = {
            "task_id": task_id,
            "description": subtask.get("description", ""),
            "marker": subtask.get("marker", ""),
            "content": content,
            "status": "staged",
            "staged_at": datetime.now().isoformat()
        }

        if "spawn" not in data:
            data["spawn"] = {}
        data["spawn"][task_id] = staged

        return _save_staging(data)
    except Exception as e:
        logger.error(f"[Staging] Failed to stage spawn: {e}")
        return False


# ============================================================
# FILE EXTRACTION & WRITING (shared by both)
# ============================================================

def extract_code_blocks(content: str) -> List[Dict[str, str]]:
    """
    Extract code blocks from markdown content.

    Returns list of {language, code, filename (if detected)}
    """
    blocks = []

    # Pattern: ```lang\ncode\n``` or ```\ncode\n```
    pattern = r'```(\w*)\s*\n(.*?)\n```'
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

    for lang, code in matches:
        code = code.strip()
        if not code:
            continue

        block = {
            "language": lang.lower() if lang else "python",
            "code": code,
            "filename": None
        }

        # Try to detect filename from first line comment
        first_line = code.split('\n')[0] if code else ""
        if "# " in first_line and "." in first_line:
            # e.g., "# src/voice/config.py" or "# config.py"
            filename_match = re.search(r'#\s*(\S+\.(?:py|js|ts|tsx|json|md))', first_line)
            if filename_match:
                block["filename"] = filename_match.group(1)

        blocks.append(block)

    return blocks


def determine_filepath(
    filename: Optional[str],
    description: str,
    marker: str,
    agent: str = "Dev",
    index: int = 0
) -> str:
    """
    Determine filepath for a code block.

    Priority:
    1. Explicit filename from code block
    2. Path extracted from description (e.g., "Create src/voice/config.py")
    3. Fallback to src/{agent.lower()}/{marker}.py
    """
    # 1. Use explicit filename if provided
    if filename:
        if filename.startswith("src/"):
            return filename
        return f"src/{agent.lower()}/{filename}"

    # 2. Extract from description
    if description:
        path_match = re.search(
            r'(src/[^\s]+?\.(?:py|js|ts|tsx|md|json))',
            description,
            re.IGNORECASE
        )
        if path_match:
            return path_match.group(1)

    # 3. Fallback
    safe_marker = re.sub(r'[^\w\-_.]', '_', str(marker or f"file_{index}"))
    return f"src/{agent.lower()}/{safe_marker}.py"


def write_file_safe(filepath: str, content: str, dry_run: bool = False) -> Optional[str]:
    """
    Write content to file with safety checks.

    Returns filepath if successful, None otherwise.
    """
    try:
        path = Path(filepath)

        if dry_run:
            logger.info(f"[DRY-RUN] Would create: {filepath} ({len(content)} chars)")
            return filepath

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write with UTF-8
        path.write_text(content, encoding='utf-8')
        logger.info(f"[Staging] Created: {filepath} ({len(content)} chars)")
        return filepath

    except Exception as e:
        logger.error(f"[Staging] Failed to write {filepath}: {e}")
        return None


def apply_staged_item(
    item: Dict[str, Any],
    item_type: str = "artifact",
    dry_run: bool = False
) -> List[str]:
    """
    Apply a single staged item (artifact or spawn result) to disk.

    Returns list of created filepaths.
    """
    files_created = []

    if item_type == "artifact":
        # Artifacts have content directly
        content = item.get("content", "")
        filename = item.get("filename")
        agent = item.get("agent", "Dev")

        filepath = determine_filepath(
            filename=filename,
            description=item.get("description", ""),
            marker=item.get("id", ""),
            agent=agent
        )

        result = write_file_safe(filepath, content, dry_run)
        if result:
            files_created.append(result)

    elif item_type == "spawn":
        # Spawn results may have multiple code blocks
        content = item.get("content", "") or item.get("result", "")
        blocks = extract_code_blocks(content)

        for i, block in enumerate(blocks):
            filepath = determine_filepath(
                filename=block.get("filename"),
                description=item.get("description", ""),
                marker=item.get("marker", f"spawn_{i}"),
                agent="Spawn"
            )

            result = write_file_safe(filepath, block["code"], dry_run)
            if result:
                files_created.append(result)

    return files_created


# ============================================================
# QDRANT INTEGRATION (optional, for semantic search)
# ============================================================

def upsert_to_qdrant(
    item: Dict[str, Any],
    item_type: str = "artifact"
) -> bool:
    """
    Upsert staged item to Qdrant VetkaLeaf collection.

    Adds type='artifact' or type='spawn_output' to payload.
    """
    try:
        from src.memory.qdrant_client import get_qdrant_client
        from src.utils.embedding_service import get_embedding

        client = get_qdrant_client()
        if not client or not client.client:
            logger.debug("[Staging] Qdrant not available, skipping upsert")
            return False

        content = item.get("content", "")[:2000]  # Truncate for embedding
        embedding = get_embedding(content)

        if not embedding:
            return False

        from qdrant_client.models import PointStruct
        import hashlib

        # Generate deterministic ID from content hash
        point_id = int(hashlib.md5(content.encode()).hexdigest()[:16], 16)

        # MARKER_103_ARTIFACT_LINK: Include source_message_id in Qdrant payload
        payload = {
            "type": item_type,
            "status": item.get("status", "staged"),
            "qa_score": item.get("qa_score", 0.0),
            "agent": item.get("agent", "unknown"),
            "filename": item.get("filename", ""),
            "content": content,
            "task_id": item.get("task_id", ""),
            "source_message_id": item.get("source_message_id", ""),
            "created_at": item.get("staged_at", datetime.now().isoformat())
        }

        point = PointStruct(id=point_id, vector=embedding, payload=payload)
        client.client.upsert(collection_name="VetkaLeaf", points=[point])

        logger.debug(f"[Staging] Upserted to Qdrant: {item.get('task_id')}")
        return True

    except Exception as e:
        logger.warning(f"[Staging] Qdrant upsert failed (graceful): {e}")
        return False


# ============================================================
# MARKER_104_MEMORY_STAGING: ELISION Compression Integration
# ============================================================
#
# ELISION compression for staging persistence:
# - Reduces disk space for large task results
# - Level 2 compression: Key abbreviation + path compression
# - ~40-50% savings without breaking reversibility
# - Auto-expansion on load via _expand_compressed_entries()
#
# Compression flow:
# 1. _save_staging(data, compress_large=True)
# 2. _compress_large_entries(data) -> Compresses result fields >2000 chars
# 3. Stores: _compressed=true, _legend={}, _original_size=N
#
# Decompression flow:
# 1. _load_staging()
# 2. _expand_compressed_entries(data) -> Auto-expands using legend
# 3. Cleans up compression metadata
#
# Features:
# - Graceful fallback if ELISION unavailable
# - Per-entry compression (only large results)
# - Comprehensive logging and stats
# - Transparent to calling code
# ============================================================

# MARKER_103.6_END
