"""
VETKA Qdrant Incremental Updater - efficient file indexing.

@status: active
@phase: 96
@depends: qdrant_client, hashlib, uuid, src.utils.embedding_service,
          src.orchestration.triple_write_manager
@used_by: src.scanners.file_watcher, src.api.routes.watcher_routes,
          src.api.routes.tree_routes

Efficient incremental updates to Qdrant based on file system events.
Features:
- Content hash comparison (only update if changed)
- Batch updates for bulk operations
- Soft delete support
- Integration with embedding pipeline
- Phase 96.1: TripleWrite integration for coherent writes (Qdrant + Weaviate + Changelog)
"""

import hashlib
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple, TYPE_CHECKING
from src.scanners.mime_policy import validate_ingest_target, normalize_mime, classify_extension

# FIX_95.9: Proper logging instead of print statements
logger = logging.getLogger(__name__)

# Type hints without circular import
if TYPE_CHECKING:
    from src.orchestration.triple_write_manager import TripleWriteManager

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


# ============================================================
# QDRANT INCREMENTAL UPDATER
# ============================================================

class QdrantIncrementalUpdater:
    """
    Efficient incremental updates to Qdrant.

    Only re-embeds files that have actually changed (based on content hash).
    Supports batch updates for bulk operations.

    Phase 83: Added stop mechanism for graceful scan interruption.
    """

    # TODO_95.9: MARKER_COHERENCE_ROOT_001 - This class writes directly to Qdrant only
    # ROOT CAUSE: All file watcher events bypass TripleWriteManager
    # ARCHITECTURE DEBT: Should integrate with TripleWriteManager.write_file()
    # FIX: Add method use_triple_write(tw_manager) and route writes through it
    # FALLBACK: If TripleWrite unavailable, use legacy direct Qdrant writes
    #
    # FIX_96.1: PARTIAL FIX APPLIED
    # - get_qdrant_updater() now defaults to enable_triple_write=True
    # - file_watcher.py explicitly passes enable_triple_write=True
    # - Watcher events now route through TripleWriteManager when TW available
    # REMAINING: watcher_routes.py still has 3 bypass points (BYPASS_001-003)

    def __init__(
        self,
        qdrant_client: Optional[Any] = None,
        collection_name: str = 'vetka_elisya',
        embedding_fn: Optional[Callable[[str], List[float]]] = None
    ):
        """
        Initialize updater.

        Args:
            qdrant_client: Qdrant client instance
            collection_name: Target collection name
            embedding_fn: Function to generate embeddings (text -> vector)
        """
        self.client = qdrant_client
        self.collection_name = collection_name
        self.embedding_fn = embedding_fn

        # Stats
        self.updated_count = 0
        self.skipped_count = 0
        self.deleted_count = 0
        self.error_count = 0

        # Phase 83: Stop flag for graceful interruption
        self._stop_requested: bool = False

        # FIX_95.9: TripleWrite integration for coherent writes
        self._triple_write: Optional['TripleWriteManager'] = None
        self._use_triple_write: bool = False  # Explicit flag to enable TW

    def request_stop(self) -> None:
        """
        Request the updater to stop processing.

        Phase 83: Sets the stop flag. The updater will exit gracefully
        at the next iteration checkpoint.
        """
        self._stop_requested = True
        logger.info("[QdrantUpdater] Stop requested - will exit at next checkpoint")

    def reset_stop(self) -> None:
        """
        Reset the stop flag before starting a new scan.

        Phase 83: Must be called before starting a new scan to ensure
        the stop flag from a previous scan doesn't affect the new one.
        """
        self._stop_requested = False

    def is_stop_requested(self) -> bool:
        """
        Check if stop has been requested.

        Phase 83: Returns True if a stop has been requested.
        """
        return self._stop_requested

    # ============================================================
    # FIX_95.9: TRIPLE WRITE INTEGRATION
    # ============================================================

    def use_triple_write(self, tw_manager: Optional['TripleWriteManager'] = None, enable: bool = True) -> None:
        """
        FIX_95.9: Enable/disable TripleWrite integration for coherent writes.

        When enabled, writes go through TripleWriteManager (Qdrant + Weaviate + Changelog).
        Falls back to direct Qdrant if TripleWrite fails.

        Args:
            tw_manager: TripleWriteManager instance (None = auto-get singleton)
            enable: True to enable, False to disable TW integration
        """
        self._use_triple_write = enable

        if enable:
            if tw_manager:
                self._triple_write = tw_manager
            else:
                # Lazy import to avoid circular dependency
                try:
                    from src.orchestration.triple_write_manager import get_triple_write_manager
                    self._triple_write = get_triple_write_manager()
                    logger.info("[QdrantUpdater] TripleWrite integration ENABLED (coherent writes)")
                except Exception as e:
                    logger.warning(f"[QdrantUpdater] Failed to init TripleWrite, using Qdrant-only: {e}")
                    self._triple_write = None
                    self._use_triple_write = False
        else:
            self._triple_write = None
            logger.info("[QdrantUpdater] TripleWrite integration DISABLED (Qdrant-only writes)")

    def _write_via_triple_write(
        self,
        file_path: Path,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        FIX_95.9: Write file via TripleWriteManager for coherence.

        Args:
            file_path: Path to file
            content: File content
            embedding: Vector embedding
            metadata: File metadata

        Returns:
            True if at least Qdrant write succeeded
        """
        if not self._triple_write:
            return False

        try:
            results = self._triple_write.write_file(
                file_path=str(file_path),
                content=content,
                embedding=embedding,
                metadata=metadata
            )

            # Log results
            total_targets = len(results)
            success_count = sum(1 for v in results.values() if bool(v))
            if total_targets > 0 and success_count == total_targets:
                logger.debug(
                    f"[QdrantUpdater] TripleWrite OK: {file_path.name} (all {total_targets} stores)"
                )
            elif success_count > 0:
                logger.warning(f"[QdrantUpdater] TripleWrite partial: {file_path.name} -> {results}")
            else:
                logger.error(f"[QdrantUpdater] TripleWrite FAILED: {file_path.name}")
                return False

            return results.get('qdrant', False)  # Return Qdrant result for compatibility

        except Exception as e:
            logger.error(f"[QdrantUpdater] TripleWrite error for {file_path.name}: {e}")
            return False

    def _get_content_hash(self, file_path: Path) -> str:
        """
        Calculate file content hash.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hash of file content
        """
        try:
            content = file_path.read_bytes()
            return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.error(f"[QdrantUpdater] Error hashing {file_path}: {e}")
            return ""

    def _get_point_id(self, file_path: str) -> int:
        """
        Generate deterministic point ID from file path.

        Uses UUID5 for collision-free IDs (same as embedding_pipeline.py).

        Args:
            file_path: File path string

        Returns:
            Integer point ID for Qdrant
        """
        return uuid.uuid5(uuid.NAMESPACE_DNS, file_path).int & 0x7FFFFFFFFFFFFFFF

    def _file_changed(self, file_path: Path) -> Tuple[bool, Optional[Dict]]:
        """
        Check if file content has changed compared to Qdrant.

        Args:
            file_path: Path to check

        Returns:
            Tuple of (changed: bool, existing_point: dict or None)
        """
        if not self.client:
            return True, None

        point_id = self._get_point_id(str(file_path))
        new_hash = self._get_content_hash(file_path)

        if not new_hash:
            return True, None  # Can't hash -> assume changed

        try:
            # Retrieve existing point
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id],
                with_payload=True,
                with_vectors=False
            )

            if not results:
                return True, None  # New file

            existing = results[0]
            old_hash = existing.payload.get('content_hash', '')

            if new_hash == old_hash:
                return False, existing  # Unchanged
            else:
                return True, existing  # Modified

        except Exception as e:
            logger.error(f"[QdrantUpdater] Error checking {file_path}: {e}")
            return True, None

    def _read_file_content(self, file_path: Path) -> str:
        """
        Read file content for embedding.

        Args:
            file_path: Path to file

        Returns:
            File content as string
        """
        try:
            # Try UTF-8 first
            return file_path.read_text(encoding='utf-8', errors='replace')
        except Exception:
            # Binary file - return empty
            return ""

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for text.

        Uses provided embedding_fn or falls back to EmbeddingService.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None
        """
        if self.embedding_fn:
            return self.embedding_fn(text)

        # Fallback to EmbeddingService
        try:
            from src.utils.embedding_service import get_embedding
            return get_embedding(text)
        except Exception as e:
            logger.error(f"[QdrantUpdater] Embedding error: {e}")
            return None

    def update_file(self, file_path: Path) -> bool:
        """
        Update single file in Qdrant.

        Only updates if content has changed.

        Args:
            file_path: Path to file

        Returns:
            True if updated, False if skipped/error
        """
        if not self.client:
            logger.info("[QdrantUpdater] No Qdrant client available")
            return False

        file_path = Path(file_path)

        if not file_path.exists():
            # File was deleted - soft delete
            return self.soft_delete(file_path)

        try:
            stat_pre = file_path.stat()
            allowed, policy = validate_ingest_target(str(file_path), int(stat_pre.st_size))
            if not allowed:
                logger.info(
                    "[QdrantUpdater] Ingest policy skipped %s: %s",
                    file_path.name,
                    policy.get("code", "INGEST_POLICY_BLOCK"),
                )
                self.skipped_count += 1
                return False
        except Exception:
            # Policy should be non-fatal for updater.
            pass

        # Check if changed
        changed, existing = self._file_changed(file_path)

        if not changed:
            logger.debug(f"[QdrantUpdater] Skipped (unchanged): {file_path.name}")
            self.skipped_count += 1
            return False

        # Read content and generate embedding
        content = self._read_file_content(file_path)
        embed_text = f"File: {file_path.name}\n\n{content[:8000]}"
        embedding = self._get_embedding(embed_text)

        if not embedding:
            logger.error(f"[QdrantUpdater] Failed to embed: {file_path.name}")
            self.error_count += 1
            return False

        # Prepare metadata
        stat = file_path.stat()
        # FIX_101.4: Add parent_folder and depth for hierarchy building
        parent_folder = str(file_path.parent)
        depth = len(file_path.parts) - 1

        metadata = {
            'type': 'scanned_file',
            'source': 'incremental_updater',
            'path': str(file_path),
            'name': file_path.name,
            'extension': file_path.suffix.lower(),
            'mime_type': normalize_mime(str(file_path)),
            'size_bytes': stat.st_size,
            'modified_time': stat.st_mtime,
            'content_hash': self._get_content_hash(file_path),
            'content': content[:500],  # Preview only
            'updated_at': time.time(),
            'deleted': False,
            # FIX_101.4: Hierarchy fields for tree building
            'parent_folder': parent_folder,
            'depth': depth,
            'modality': classify_extension(str(file_path))[1],
            'extraction_version': 'phase153_mm_v1',
        }

        # FIX_95.9: Try TripleWrite first for coherent writes across all stores
        # FIX_96.5: Added explicit logging to verify TW is being used
        if self._use_triple_write and self._triple_write:
            logger.info(f"[QdrantUpdater] Writing via TripleWrite: {file_path.name}")
            tw_success = self._write_via_triple_write(file_path, content, embedding, metadata)
            if tw_success:
                logger.info(f"[QdrantUpdater] ✅ TripleWrite OK: {file_path.name} (Qdrant+Weaviate)")
                self.updated_count += 1

                # MARKER_123.1E: Phase 123.1 - Emit glow for scanner indexing (TripleWrite path)
                try:
                    from src.services.activity_hub import get_activity_hub
                    hub = get_activity_hub()
                    hub.emit_glow_sync(str(file_path), 0.6, "scanner:indexed_tw")
                except Exception:
                    pass  # Non-critical

                return True
            else:
                logger.warning(f"[QdrantUpdater] TripleWrite failed, falling back to Qdrant-only: {file_path.name}")
        else:
            logger.debug(f"[QdrantUpdater] TripleWrite not active (use_tw={self._use_triple_write}, tw={self._triple_write is not None})")

        # Fallback: Direct Qdrant upsert (legacy behavior)
        try:
            point_id = self._get_point_id(str(file_path))
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=metadata
            )

            # Phase 92: Non-blocking upsert (Kimi K2 fix)
            # TODO_95.9: MARKER_COHERENCE_BYPASS_004 - Single file upsert bypasses Weaviate/Changelog
            # ROOT CAUSE: update_file() writes only to Qdrant when TripleWrite unavailable
            # FIX_96.1: TripleWrite now enabled by default in get_qdrant_updater()
            # This fallback path is now only used when:
            #   1. TripleWrite explicitly disabled
            #   2. TripleWrite write fails (Weaviate/Changelog down)
            # STATUS: MITIGATED - primary path now uses TripleWrite
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
                wait=False  # Non-blocking - UI won't freeze
            )

            logger.info(f"[QdrantUpdater] Updated (Qdrant-only): {file_path.name}")
            self.updated_count += 1

            # MARKER_123.1E: Phase 123.1 - Emit glow for scanner indexing
            try:
                from src.services.activity_hub import get_activity_hub
                hub = get_activity_hub()
                hub.emit_glow_sync(str(file_path), 0.6, "scanner:indexed")
            except Exception:
                pass  # Non-critical

            return True

        except Exception as e:
            logger.error(f"[QdrantUpdater] Error upserting {file_path.name}: {e}")
            self.error_count += 1
            return False

    def batch_update(self, file_paths: List[Path]) -> int:
        """
        Batch update multiple files.

        Filters unchanged files and updates only modified ones.
        Phase 83: Checks stop flag and exits gracefully if requested.

        Args:
            file_paths: List of file paths to update

        Returns:
            Number of files actually updated
        """
        if not self.client:
            logger.info("[QdrantUpdater] No Qdrant client available")
            return 0

        # Filter to only changed files
        to_update = []
        for fp in file_paths:
            # Phase 83: Check stop flag
            if self._stop_requested:
                logger.info("[QdrantUpdater] Stop requested - aborting batch filter")
                break

            fp = Path(fp)
            if not fp.exists():
                continue

            changed, _ = self._file_changed(fp)
            if changed:
                to_update.append(fp)
            else:
                self.skipped_count += 1

        if not to_update:
            logger.info("[QdrantUpdater] No files to update (all unchanged)")
            return 0

        # Phase 83: Check stop flag before starting batch
        if self._stop_requested:
            logger.info("[QdrantUpdater] Stop requested - skipping batch update")
            return 0

        logger.info(f"[QdrantUpdater] Batch updating {len(to_update)} files...")

        # Prepare all points
        points = []
        for fp in to_update:
            # Phase 83: Check stop flag in embedding loop
            if self._stop_requested:
                logger.info("[QdrantUpdater] Stop requested - aborting batch embedding")
                break

            content = self._read_file_content(fp)
            embed_text = f"File: {fp.name}\n\n{content[:8000]}"
            embedding = self._get_embedding(embed_text)

            if not embedding:
                self.error_count += 1
                continue

            stat = fp.stat()
            point_id = self._get_point_id(str(fp))

            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    'type': 'scanned_file',
                    'source': 'incremental_updater',
                    'path': str(fp),
                    'name': fp.name,
                    'extension': fp.suffix.lower(),
                    'size_bytes': stat.st_size,
                    'modified_time': stat.st_mtime,
                    'content_hash': self._get_content_hash(fp),
                    'content': content[:500],
                    'updated_at': time.time(),
                    'deleted': False
                }
            ))

        # Batch upsert
        # Phase 92: Non-blocking batch upsert (Kimi K2 fix)
        if points:
            try:
                # TODO_95.9: MARKER_COHERENCE_BYPASS_005 - Batch upsert bypasses Weaviate/Changelog
                # FIX: Implement tw.batch_write(files) or loop tw.write_file() for each
                # RECOMMEND: Batch writes need atomic transaction support in TripleWrite
                # FIX_96.1: PENDING - batch operations still bypass TW
                # REASON: TripleWriteManager lacks batch_write() method
                # IMPACT: Bulk operations (>10 files) still write only to Qdrant
                # WORKAROUND: For now, use scan_directory which calls update_file per file
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                    wait=False  # Non-blocking - UI won't freeze
                )
                self.updated_count += len(points)
                logger.info(f"[QdrantUpdater] Batch updated: {len(points)} files")
            except Exception as e:
                logger.error(f"[QdrantUpdater] Batch upsert error: {e}")
                self.error_count += len(points)

        return len(points)

    def soft_delete(self, file_path: Path) -> bool:
        """
        Mark file as deleted (soft delete).

        Doesn't remove from Qdrant, just marks as deleted.

        Args:
            file_path: Path to deleted file

        Returns:
            True if marked as deleted
        """
        if not self.client:
            return False

        try:
            point_id = self._get_point_id(str(file_path))

            # Update payload to mark as deleted
            self.client.set_payload(
                collection_name=self.collection_name,
                payload={
                    'deleted': True,
                    'deleted_at': time.time()
                },
                points=[point_id]
            )

            logger.info(f"[QdrantUpdater] Soft deleted: {file_path}")
            self.deleted_count += 1
            return True

        except Exception as e:
            logger.error(f"[QdrantUpdater] Error soft deleting {file_path}: {e}")
            self.error_count += 1
            return False

    def hard_delete(self, file_path: Path) -> bool:
        """
        Permanently remove file from Qdrant.

        Args:
            file_path: Path to file

        Returns:
            True if deleted
        """
        if not self.client:
            return False

        try:
            point_id = self._get_point_id(str(file_path))

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[point_id]
            )

            logger.info(f"[QdrantUpdater] Hard deleted: {file_path}")
            self.deleted_count += 1
            return True

        except Exception as e:
            logger.error(f"[QdrantUpdater] Error hard deleting {file_path}: {e}")
            self.error_count += 1
            return False

    def cleanup_deleted(self, older_than_hours: int = 24) -> int:
        """
        Remove soft-deleted files older than specified hours.

        Args:
            older_than_hours: Remove files deleted more than X hours ago

        Returns:
            Number of files removed
        """
        if not self.client:
            return 0

        cutoff_time = time.time() - (older_than_hours * 3600)

        try:
            # Find old deleted files
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="deleted",
                            match=MatchValue(value=True)
                        )
                    ]
                ),
                limit=1000,
                with_payload=True,
                with_vectors=False
            )

            points = results[0] if results else []
            to_delete = []

            for point in points:
                deleted_at = point.payload.get('deleted_at', 0)
                if deleted_at < cutoff_time:
                    to_delete.append(point.id)

            if to_delete:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=to_delete
                )
                logger.info(f"[QdrantUpdater] Cleaned up {len(to_delete)} old deleted files")

            return len(to_delete)

        except Exception as e:
            logger.error(f"[QdrantUpdater] Error cleaning up: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get updater statistics.

        Phase 83: Added stop_requested flag to stats.

        Returns:
            Dictionary with update stats
        """
        return {
            'updated_count': self.updated_count,
            'skipped_count': self.skipped_count,
            'deleted_count': self.deleted_count,
            'error_count': self.error_count,
            'collection': self.collection_name,
            'stop_requested': self._stop_requested  # Phase 83
        }

    # MARKER_90.6_START: Unified scan_directory for Manual Scan and Watchdog
    # Phase 92.3: Added progress_callback for real-time UI updates
    def scan_directory(
        self,
        path: str,
        skip_dirs: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Scan directory and index all files to Qdrant.

        Phase 90.6: Unified method for both Manual Scan and Watchdog.
        Phase 92.3: Added progress_callback for real-time UI updates.
        Uses update_file() for each file, which handles hash-based change detection.

        Args:
            path: Directory path to scan
            skip_dirs: Directories to skip (default: common ignore patterns)
            progress_callback: Optional callback(current, total, file_path) for progress updates

        Returns:
            Number of files indexed
        """
        import os

        if skip_dirs is None:
            # FIX_101.1: Added venv_mcp and site-packages to prevent indexing virtual env files
            # MARKER_149.SCAN_SKIP: Unified skip list — prevent indexing worktrees/playgrounds
            skip_dirs = ['node_modules', '__pycache__', 'venv', '.venv', 'venv_mcp',
                        'site-packages', 'dist', 'build', '.git', '.idea', '.vscode',
                        '.playgrounds', 'playgrounds', '.claude', 'Pods', 'target']

        # Phase 92.3: First pass - count total files for progress
        total_files = 0
        all_files = []
        for root, dirs, files in os.walk(path):
            # Filter directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in skip_dirs]
            for filename in files:
                if not filename.startswith('.'):
                    all_files.append(os.path.join(root, filename))
                    total_files += 1

        logger.info(f"[QdrantUpdater] Starting scan: {total_files} files to process in {path}")

        indexed_count = 0
        current = 0

        for file_path_str in all_files:
            # Phase 83: Check stop flag
            if self._stop_requested:
                logger.info("[QdrantUpdater] Stop requested - aborting directory scan")
                break

            current += 1
            file_path = Path(file_path_str)

            # Phase 92.3/92.4: Call progress callback with file metadata
            if progress_callback:
                try:
                    # Get file stats for size and modified time
                    file_size = file_path.stat().st_size if file_path.exists() else 0
                    file_mtime = file_path.stat().st_mtime if file_path.exists() else 0
                    progress_callback(current, total_files, str(file_path), file_size, file_mtime)
                except Exception as e:
                    logger.warning(f"[QdrantUpdater] Progress callback error: {e}")

            # Use unified update_file method (handles hash check, embedding, upsert)
            if self.update_file(file_path):
                indexed_count += 1

        logger.info(f"[QdrantUpdater] Directory scan complete: {indexed_count} files indexed from {path}")
        return indexed_count
    # MARKER_90.6_END


# ============================================================
# SINGLETON INSTANCE
# ============================================================

_updater_instance: Optional[QdrantIncrementalUpdater] = None


def get_qdrant_updater(
    qdrant_client: Optional[Any] = None,
    collection_name: str = 'vetka_elisya',
    enable_triple_write: bool = True  # FIX_96.1: Changed default to True for coherent writes
) -> QdrantIncrementalUpdater:
    """
    Get singleton updater instance.

    FIX_95.9: Added enable_triple_write parameter for coherent writes.
    FIX_96.1: Changed default to True - all writes now go through TripleWriteManager
             for coherent Qdrant + Weaviate + ChangeLog persistence.

    Args:
        qdrant_client: Qdrant client (only used on first call)
        collection_name: Collection name (only used on first call)
        enable_triple_write: Enable TripleWrite for coherent writes (default: True)

    Returns:
        QdrantIncrementalUpdater singleton
    """
    global _updater_instance

    if _updater_instance is None:
        _updater_instance = QdrantIncrementalUpdater(
            qdrant_client=qdrant_client,
            collection_name=collection_name
        )
    elif qdrant_client and _updater_instance.client is None:
        _updater_instance.client = qdrant_client

    # FIX_95.9: Enable TripleWrite if requested
    # FIX_96.5: Added explicit logging to debug TW activation
    if enable_triple_write:
        if not _updater_instance._use_triple_write:
            logger.info("[QdrantUpdater] Activating TripleWrite integration...")
            _updater_instance.use_triple_write(enable=True)
        else:
            logger.debug("[QdrantUpdater] TripleWrite already active")
    else:
        logger.debug("[QdrantUpdater] TripleWrite disabled by parameter")

    return _updater_instance


# ============================================================
# INTEGRATION WITH FILE WATCHER
# ============================================================

def handle_watcher_event(
    event: Dict[str, Any],
    qdrant_client: Optional[Any] = None,
    enable_triple_write: bool = True  # FIX_95.9: Default to coherent writes
) -> bool:
    """
    Handle file watcher event and update storage.

    FIX_95.9: Added enable_triple_write for coherent writes across all stores.

    Args:
        event: Event from VetkaFileWatcher
        qdrant_client: Qdrant client instance
        enable_triple_write: Use TripleWrite for coherent writes (default: True)

    Returns:
        True if handled successfully
    """
    updater = get_qdrant_updater(qdrant_client, enable_triple_write=enable_triple_write)

    event_type = event.get('type', '')
    path = event.get('path', '')

    if not path:
        return False

    file_path = Path(path)

    if event_type == 'created':
        return updater.update_file(file_path)

    elif event_type == 'modified':
        return updater.update_file(file_path)

    elif event_type == 'deleted':
        return updater.soft_delete(file_path)

    elif event_type == 'bulk_update':
        # For bulk updates, we'd need the list of files
        # This is a placeholder - actual implementation would
        # need to scan the directory for changed files
        logger.info(f"[QdrantUpdater] Bulk update detected at {path}")
        return True

    return False
