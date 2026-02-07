"""
Triple Write Manager - ensures data consistency across all storage layers.

ARCHITECTURE:
    Scan/Index Operation
           |
           v
    TripleWriteManager.write()
           |
    +------+------+
    |      |      |
    v      v      v
Weaviate Qdrant ChangeLog
(semantic)(vector)(audit)

@status: active
@phase: 96
@depends: weaviate, qdrant_client, src.utils.embedding_service
@used_by: src.scanners.file_watcher, src.api.routes.triple_write_routes
"""

import os
import json
import uuid
import hashlib
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# FIX_95.8: Setup proper logging for TripleWrite errors
logger = logging.getLogger(__name__)

# Weaviate v4 API (MARKER_117.7C: migrated from v3)
try:
    import weaviate
    from weaviate.classes.config import Configure, Property, DataType
    from weaviate.classes.data import DataObject
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False

# Qdrant
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


class TripleWriteManager:
    """
    Manages atomic writes to Weaviate, Qdrant, and ChangeLog.
    Graceful degradation: if one storage fails, others continue.

    FIX_95.8: Added retry logic, thread safety, proper error logging
    """

    # FIX_95.8: Retry configuration
    MAX_RETRIES = 3
    BASE_DELAY = 0.5  # seconds

    def __init__(
        self,
        weaviate_url: str = "http://localhost:8080",
        qdrant_url: str = "http://127.0.0.1:6333",
        changelog_dir: str = "data/changelog",
        embedding_dim: int = 768
    ):
        self.weaviate_url = weaviate_url
        self.qdrant_url = qdrant_url
        self.changelog_dir = Path(changelog_dir)
        self.embedding_dim = embedding_dim

        # FIX_95.8: MARKER_TW_010_RACE_CONDITION - Thread lock for changelog writes
        self._changelog_lock = threading.Lock()

        # FIX_95.9: MARKER_TW_013_NO_WRITE_LOCK - Thread lock for write operations
        self._write_lock = threading.Lock()

        # Ensure changelog directory exists
        self.changelog_dir.mkdir(parents=True, exist_ok=True)

        # Initialize clients
        self._init_weaviate()
        self._init_qdrant()

        logger.info(f"[TripleWrite] Initialized:")
        logger.info(f"  - Weaviate: {'OK' if self.weaviate_client else 'UNAVAILABLE'}")
        logger.info(f"  - Qdrant: {'OK' if self.qdrant_client else 'UNAVAILABLE'}")
        logger.info(f"  - ChangeLog: OK ({self.changelog_dir})")

    def _retry_with_backoff(self, operation_name: str, operation_func, *args, **kwargs) -> bool:
        """
        FIX_95.8: MARKER_TW_004_SILENT_FAILURES - Retry with exponential backoff.

        Args:
            operation_name: Name for logging
            operation_func: Function to call
            *args, **kwargs: Arguments to pass to function

        Returns:
            True if operation succeeded, False otherwise
        """
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                result = operation_func(*args, **kwargs)
                # FIX_95.9: MARKER_TW_012_RETRY_FALSE_CONTINUES - False means client unavailable, don't retry
                if result is True:
                    if attempt > 0:
                        logger.info(f"[TripleWrite] {operation_name} succeeded on attempt {attempt + 1}")
                    return True
                elif result is False:
                    # Client unavailable - no point retrying
                    logger.debug(f"[TripleWrite] {operation_name} returned False (client unavailable)")
                    return False
            except Exception as e:
                last_error = e
                delay = self.BASE_DELAY * (2 ** attempt)  # Exponential backoff: 0.5, 1, 2 seconds
                logger.warning(
                    f"[TripleWrite] {operation_name} attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(delay)

        # All retries exhausted
        logger.error(f"[TripleWrite] {operation_name} FAILED after {self.MAX_RETRIES} attempts. Last error: {last_error}")
        return False

    def _init_weaviate(self):
        """Initialize Weaviate client and ensure schema exists.
        MARKER_117.7C: Migrated from v3 Client(url) to v4 connect_to_local().
        """
        self.weaviate_client = None

        if not WEAVIATE_AVAILABLE:
            logger.warning("[TripleWrite] Weaviate not available (import failed)")
            return

        try:
            # MARKER_117.7C: Weaviate v4 API — connect_to_local instead of Client(url)
            # Parse host and port from URL (e.g. "http://localhost:8080")
            url_clean = self.weaviate_url.replace("http://", "").replace("https://", "")
            parts = url_clean.split(":")
            host = parts[0] if parts else "localhost"
            port = int(parts[1]) if len(parts) > 1 else 8080

            self.weaviate_client = weaviate.connect_to_local(host=host, port=port)

            # Check connection
            if not self.weaviate_client.is_ready():
                logger.warning("[TripleWrite] Weaviate not ready")
                self.weaviate_client = None
                return

            # Ensure VetkaLeaf class exists with correct schema
            self._ensure_vetka_leaf_schema()
            logger.info("[TripleWrite] Weaviate: AVAILABLE (v4 API)")

        except Exception as e:
            logger.error(f"[TripleWrite] Weaviate init error: {e}")
            self.weaviate_client = None

    def _ensure_vetka_leaf_schema(self):
        """Create or update VetkaLeaf collection with file-oriented schema.
        MARKER_117.7C: Migrated from v3 schema API to v4 collections API.
        """
        if not self.weaviate_client:
            return

        try:
            # Weaviate v4 API: list collections
            existing_collections = [c.name for c in self.weaviate_client.collections.list_all().values()]

            if 'VetkaLeaf' not in existing_collections:
                logger.info("[TripleWrite] Creating VetkaLeaf collection (v4 API)...")
                self.weaviate_client.collections.create(
                    name="VetkaLeaf",
                    vectorizer_config=Configure.Vectorizer.none(),
                    properties=[
                        Property(name="file_path", data_type=DataType.TEXT, description="Full relative path"),
                        Property(name="file_name", data_type=DataType.TEXT, description="File name only"),
                        Property(name="content", data_type=DataType.TEXT, description="File content (truncated)"),
                        Property(name="file_type", data_type=DataType.TEXT, description="Extension without dot"),
                        Property(name="depth", data_type=DataType.INT, description="Directory depth"),
                        Property(name="size", data_type=DataType.INT, description="File size in bytes"),
                        Property(name="created_at", data_type=DataType.DATE, description="Index timestamp"),
                        Property(name="modified_at", data_type=DataType.DATE, description="File mtime")
                    ]
                )
                logger.info("[TripleWrite] VetkaLeaf collection created!")
            else:
                logger.info("[TripleWrite] VetkaLeaf collection exists")
        except Exception as e:
            logger.error(f"[TripleWrite] Schema setup error: {e}")

    def _init_qdrant(self):
        """Initialize Qdrant client and ensure collection exists."""
        self.qdrant_client = None

        if not QDRANT_AVAILABLE:
            logger.info("[TripleWrite] Qdrant not available (import failed)")
            return

        try:
            self.qdrant_client = QdrantClient(url=self.qdrant_url)

            # Ensure collection exists
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]

            # FIX_96.2: Changed from vetka_files to vetka_elisya for consistency
            # All other components (QdrantUpdater, tree_routes) use vetka_elisya
            if 'vetka_elisya' not in collection_names:
                logger.info("[TripleWrite] Creating vetka_elisya collection...")
                self.qdrant_client.create_collection(
                    collection_name='vetka_elisya',
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info("[TripleWrite] vetka_elisya collection created!")

        except Exception as e:
            logger.error(f"[TripleWrite] Qdrant init error: {e}")
            self.qdrant_client = None

    def write_file(
        self,
        file_path: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        Write file data to all three storage layers.
        FIX_95.9: Added input validation, embedding check, and write lock.

        Args:
            file_path: Relative path to file
            content: File content (will be truncated for Weaviate)
            embedding: Vector embedding (768 dims)
            metadata: Additional metadata (size, mtime, etc.)

        Returns:
            Dict with success status for each storage
        """
        results = {
            'weaviate': False,
            'qdrant': False,
            'changelog': False
        }

        # FIX_95.9: MARKER_TW_014_NO_INPUT_VALIDATION - validate inputs
        if not file_path or not file_path.strip():
            logger.error("[TripleWrite] Empty file_path provided")
            return results

        # FIX_95.9: MARKER_TW_011_NO_EMBEDDING_VALIDATION - validate embedding dimension
        if not embedding or len(embedding) != self.embedding_dim:
            logger.error(f"[TripleWrite] Invalid embedding: expected {self.embedding_dim} dims, got {len(embedding) if embedding else 0}")
            return results

        # Prepare common data
        file_name = os.path.basename(file_path)
        file_type = os.path.splitext(file_name)[1].lstrip('.').lower() or 'unknown'
        depth = file_path.count('/')
        now = datetime.now().isoformat()

        metadata = metadata or {}
        file_size = metadata.get('size', len(content.encode('utf-8')))

        # Handle mtime - can be float timestamp or string
        mtime_raw = metadata.get('mtime')
        if isinstance(mtime_raw, (int, float)) and mtime_raw > 0:
            mtime = datetime.fromtimestamp(mtime_raw).isoformat()
        elif isinstance(mtime_raw, str):
            mtime = mtime_raw
        else:
            mtime = now

        # Generate consistent ID from path
        file_id = str(uuid.uuid5(uuid.NAMESPACE_URL, file_path))

        # FIX_95.9: MARKER_TW_013_NO_WRITE_LOCK - protect concurrent writes to same file
        with self._write_lock:
            # 1. Write to Weaviate
            results['weaviate'] = self._write_weaviate(
                file_id=file_id,
                file_path=file_path,
                file_name=file_name,
                content=content[:5000],  # Truncate for Weaviate
                file_type=file_type,
                depth=depth,
                size=file_size,
                created_at=now,
                modified_at=mtime,
                embedding=embedding
            )

            # 2. Write to Qdrant
            results['qdrant'] = self._write_qdrant(
                file_id=file_id,
                file_path=file_path,
                file_name=file_name,
                file_type=file_type,
                depth=depth,
                embedding=embedding,
                metadata=metadata
            )

            # 3. Write to ChangeLog (always succeeds locally)
            results['changelog'] = self._write_changelog(
                operation='index_file',
                file_path=file_path,
                file_id=file_id,
                timestamp=now,
                results=results.copy()
            )

            # 4. FIX_101.3: Write to VetkaTree for hierarchy
            results['vetka_tree'] = self._write_vetka_tree(
                file_id=file_id,
                file_path=file_path,
                content=content,
                embedding=embedding,
                metadata=metadata
            )

        return results

    def _write_weaviate_internal(
        self,
        file_id: str,
        file_path: str,
        file_name: str,
        content: str,
        file_type: str,
        depth: int,
        size: int,
        created_at: str,
        modified_at: str,
        embedding: List[float]
    ) -> bool:
        """
        Internal Weaviate write - raises exceptions for retry logic.
        FIX_95.8: Separated from wrapper for proper retry handling.
        """
        if not self.weaviate_client:
            logger.debug(f"[TripleWrite] Weaviate client not available for {file_path}")
            return False

        # Weaviate requires RFC3339 format with Z suffix
        def to_rfc3339(dt_str):
            if dt_str and not dt_str.endswith('Z'):
                return dt_str.replace(' ', 'T').split('.')[0] + '.000000Z'
            return dt_str

        properties = {
            'file_path': file_path,
            'file_name': file_name,
            'content': content,
            'file_type': file_type,
            'depth': depth,
            'size': size,
            'created_at': to_rfc3339(created_at),
            'modified_at': to_rfc3339(modified_at)
        }

        # MARKER_117.7C: Weaviate v4 API — use collections.get() + data.insert/replace
        collection = self.weaviate_client.collections.get("VetkaLeaf")

        # Try to replace existing (upsert pattern)
        try:
            existing = collection.data.get_by_id(file_id)
            if existing:
                collection.data.replace(
                    uuid=file_id,
                    properties=properties,
                    vector=embedding
                )
                return True
        except Exception as e:
            # Object doesn't exist, will create below
            logger.debug(f"[TripleWrite] Object {file_id} not found, creating new: {e}")

        # Create new
        collection.data.insert(
            uuid=file_id,
            properties=properties,
            vector=embedding
        )
        # FIX_96.5: Log successful Weaviate write
        logger.info(f"[TripleWrite] \u2705 Weaviate write OK: {file_name}")
        return True

    def _write_weaviate(
        self,
        file_id: str,
        file_path: str,
        file_name: str,
        content: str,
        file_type: str,
        depth: int,
        size: int,
        created_at: str,
        modified_at: str,
        embedding: List[float]
    ) -> bool:
        """
        Write to Weaviate VetkaLeaf class with retry logic.
        FIX_95.8: MARKER_TW_004_SILENT_FAILURES - proper retry and logging.
        """
        return self._retry_with_backoff(
            f"Weaviate write [{file_path}]",
            self._write_weaviate_internal,
            file_id, file_path, file_name, content, file_type,
            depth, size, created_at, modified_at, embedding
        )

    def _write_qdrant_internal(
        self,
        file_id: str,
        file_path: str,
        file_name: str,
        file_type: str,
        depth: int,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Internal Qdrant write - raises exceptions for retry logic.
        FIX_95.8: Separated from wrapper for proper retry handling.
        """
        if not self.qdrant_client:
            logger.debug(f"[TripleWrite] Qdrant client not available for {file_path}")
            return False

        point = PointStruct(
            id=file_id,
            vector=embedding,
            payload={
                'file_path': file_path,
                'file_name': file_name,
                'file_type': file_type,
                'depth': depth,
                **metadata
            }
        )

        # FIX_96.2: Use vetka_elisya for consistency with rest of system
        self.qdrant_client.upsert(
            collection_name='vetka_elisya',
            points=[point]
        )
        return True

    def _write_qdrant(
        self,
        file_id: str,
        file_path: str,
        file_name: str,
        file_type: str,
        depth: int,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Write to Qdrant vetka_elisya collection with retry logic.
        FIX_95.8: MARKER_TW_004_SILENT_FAILURES - proper retry and logging.
        """
        return self._retry_with_backoff(
            f"Qdrant write [{file_path}]",
            self._write_qdrant_internal,
            file_id, file_path, file_name, file_type, depth, embedding, metadata
        )

    def _write_changelog(
        self,
        operation: str,
        file_path: str,
        file_id: str,
        timestamp: str,
        results: Dict[str, bool]
    ) -> bool:
        """
        Write to ChangeLog JSON file.
        FIX_95.8: MARKER_TW_010_RACE_CONDITION - Thread-safe with lock.
        """
        try:
            # Daily changelog files
            date_str = timestamp[:10]  # YYYY-MM-DD
            log_file = self.changelog_dir / f"changelog_{date_str}.json"

            # FIX_95.8: Thread-safe changelog write
            with self._changelog_lock:
                # Load existing or create new
                if log_file.exists():
                    with open(log_file, 'r') as f:
                        try:
                            logs = json.load(f)
                        except json.JSONDecodeError as e:
                            logger.warning(f"[TripleWrite] Corrupted changelog, starting fresh: {e}")
                            logs = []
                else:
                    logs = []

                # Append entry
                logs.append({
                    'operation': operation,
                    'file_path': file_path,
                    'file_id': file_id,
                    'timestamp': timestamp,
                    'results': results
                })

                # Save atomically (write to temp, then rename)
                temp_file = log_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(logs, f, indent=2)
                temp_file.replace(log_file)

            return True

        except Exception as e:
            logger.error(f"[TripleWrite] ChangeLog write error for {file_path}: {e}")
            return False

    def _write_vetka_tree(
        self,
        file_id: str,
        file_path: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        FIX_101.3: Write to VetkaTree collection for hierarchical storage.
        Uses QdrantVetkaClient.triple_write() method.
        """
        try:
            from src.memory.qdrant_client import get_qdrant_client
            vetka_client = get_qdrant_client()

            if not vetka_client or not vetka_client.client:
                logger.debug(f"[TripleWrite] VetkaTree client not available for {file_path}")
                return False

            # Compute parent_id for hierarchy
            parent_path = os.path.dirname(file_path)
            parent_id = str(uuid.uuid5(uuid.NAMESPACE_URL, parent_path)) if parent_path else None

            # Prepare metadata with hierarchy info
            tree_metadata = {
                'type': 'scanned_file',
                'parent_path': parent_path,
                'parent_id': parent_id,
                'depth': file_path.count('/'),
                **metadata
            }

            # Use VetkaTree triple_write
            result = vetka_client.triple_write(
                workflow_id=f"scan_{file_id}",
                node_id=file_id,
                path=file_path,
                content=content[:500],
                metadata=tree_metadata,
                vector=embedding
            )

            success = result.get('qdrant', False)
            if success:
                logger.info(f"[TripleWrite] ✅ VetkaTree write OK: {os.path.basename(file_path)}")
            return success

        except Exception as e:
            logger.error(f"[TripleWrite] VetkaTree write error for {file_path}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from all storage layers."""
        stats = {
            'weaviate': {'status': 'unavailable', 'count': 0},
            'qdrant': {'status': 'unavailable', 'count': 0},
            'changelog': {'status': 'unavailable', 'count': 0}
        }

        # Weaviate stats
        if self.weaviate_client:
            try:
                result = self.weaviate_client.query.aggregate('VetkaLeaf').with_meta_count().do()
                count = result.get('data', {}).get('Aggregate', {}).get('VetkaLeaf', [{}])[0].get('meta', {}).get('count', 0)
                stats['weaviate'] = {'status': 'ready', 'count': count}
            except Exception as e:
                stats['weaviate'] = {'status': 'error', 'count': 0, 'error': str(e)}

        # Qdrant stats - FIX_96.2: Use vetka_elisya
        if self.qdrant_client:
            try:
                info = self.qdrant_client.get_collection('vetka_elisya')
                stats['qdrant'] = {'status': 'ready', 'count': info.points_count}
            except Exception as e:
                stats['qdrant'] = {'status': 'error', 'count': 0, 'error': str(e)}

        # ChangeLog stats
        try:
            log_files = list(self.changelog_dir.glob('changelog_*.json'))
            total_entries = 0
            for f in log_files:
                with open(f, 'r') as file:
                    total_entries += len(json.load(file))
            stats['changelog'] = {'status': 'ready', 'count': total_entries, 'files': len(log_files)}
        except Exception as e:
            stats['changelog'] = {'status': 'error', 'count': 0, 'error': str(e)}

        return stats

    def clear_weaviate_eval_data(self) -> int:
        """Remove evaluation data from VetkaLeaf (wrong schema data)."""
        if not self.weaviate_client:
            return 0

        deleted = 0
        try:
            # Get all objects
            result = self.weaviate_client.data_object.get(class_name='VetkaLeaf', limit=1000)
            objects = result.get('objects', [])

            for obj in objects:
                props = obj.get('properties', {})
                # If it has 'task' or 'score' but not 'file_path' - it's eval data
                if ('task' in props or 'score' in props) and 'file_path' not in props:
                    self.weaviate_client.data_object.delete(
                        uuid=obj['id'],
                        class_name='VetkaLeaf'
                    )
                    deleted += 1

            logger.info(f"[TripleWrite] Cleaned {deleted} evaluation objects from VetkaLeaf")
            return deleted

        except Exception as e:
            logger.error(f"[TripleWrite] Cleanup error: {e}")
            return deleted

    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding using unified EmbeddingService (Phase 36.1).
        Falls back to hash-based pseudo-embedding if service fails.
        """
        from src.utils.embedding_service import get_embedding as unified_get_embedding

        embedding = unified_get_embedding(text[:2000])
        if embedding and len(embedding) >= self.embedding_dim:
            return embedding[:self.embedding_dim]

        # Fallback: use hash-based pseudo-embedding
        h = hashlib.sha256(text.encode()).hexdigest()
        embedding = []
        for i in range(0, min(len(h), self.embedding_dim * 2), 2):
            embedding.append(int(h[i:i+2], 16) / 255.0)

        # Pad to required dimension
        while len(embedding) < self.embedding_dim:
            embedding.append(0.0)

        return embedding[:self.embedding_dim]


# Singleton instance
_triple_write_manager = None

def get_triple_write_manager() -> TripleWriteManager:
    """Get or create singleton TripleWriteManager instance."""
    global _triple_write_manager
    if _triple_write_manager is None:
        _triple_write_manager = TripleWriteManager()
    return _triple_write_manager
