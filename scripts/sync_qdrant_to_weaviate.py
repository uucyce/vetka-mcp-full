#!/usr/bin/env python3
"""
Sync Qdrant 'vetka_elisya' collection to Weaviate 'VetkaLeaf' collection.

Reads all points from Qdrant and creates/updates objects in Weaviate
using batch operations for performance.

Usage:
    python scripts/sync_qdrant_to_weaviate.py

Requirements:
    - Qdrant running on localhost:6333
    - Weaviate running on localhost:8080
    - Collection 'vetka_elisya' exists in Qdrant
"""

import sys
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# Qdrant client
try:
    from qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.error("qdrant-client not installed. Run: pip install qdrant-client")

# Weaviate client v4
try:
    import weaviate
    from weaviate.classes.config import Configure, Property, DataType
    from weaviate.classes.data import DataObject
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False
    logger.error("weaviate-client not installed. Run: pip install weaviate-client")


class QdrantToWeaviateSync:
    """Syncs data from Qdrant vetka_elisya to Weaviate VetkaLeaf."""

    QDRANT_COLLECTION = "vetka_elisya"
    WEAVIATE_CLASS = "VetkaLeaf"
    BATCH_SIZE = 50  # Objects per batch
    CONTENT_MAX_LENGTH = 5000  # Truncate content for Weaviate

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        weaviate_url: str = "http://localhost:8080"
    ):
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.weaviate_url = weaviate_url

        self.qdrant_client: Optional[QdrantClient] = None
        self.weaviate_client = None

        # Statistics
        self.total_points = 0
        self.synced_count = 0
        self.error_count = 0
        self.errors: List[str] = []

    def connect(self) -> bool:
        """Connect to both Qdrant and Weaviate."""
        # Connect to Qdrant
        if not QDRANT_AVAILABLE:
            logger.error("Qdrant client not available")
            return False

        try:
            self.qdrant_client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port
            )
            # Test connection
            collections = self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.QDRANT_COLLECTION not in collection_names:
                logger.error(f"Qdrant collection '{self.QDRANT_COLLECTION}' not found")
                logger.info(f"Available collections: {collection_names}")
                return False

            logger.info(f"Connected to Qdrant ({self.qdrant_host}:{self.qdrant_port})")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            return False

        # Connect to Weaviate v4
        if not WEAVIATE_AVAILABLE:
            logger.error("Weaviate client not available")
            return False

        try:
            # Weaviate v4 API
            self.weaviate_client = weaviate.connect_to_local(
                host=self.weaviate_url.replace("http://", "").split(":")[0],
                port=int(self.weaviate_url.split(":")[-1]) if ":" in self.weaviate_url else 8080
            )
            if not self.weaviate_client.is_ready():
                logger.error("Weaviate is not ready")
                return False

            logger.info(f"Connected to Weaviate ({self.weaviate_url})")
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            return False

        return True

    def ensure_weaviate_schema(self) -> bool:
        """Ensure VetkaLeaf class exists with correct schema (Weaviate v4 API)."""
        if not self.weaviate_client:
            return False

        try:
            # Weaviate v4 API - check if collection exists
            existing_collections = [c.name for c in self.weaviate_client.collections.list_all().values()]

            if self.WEAVIATE_CLASS not in existing_collections:
                logger.info(f"Creating Weaviate collection '{self.WEAVIATE_CLASS}'...")
                self.weaviate_client.collections.create(
                    name=self.WEAVIATE_CLASS,
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
                logger.info(f"Created Weaviate collection '{self.WEAVIATE_CLASS}'")
            else:
                logger.info(f"Collection '{self.WEAVIATE_CLASS}' already exists")

            return True

        except Exception as e:
            logger.error(f"Failed to ensure Weaviate schema: {e}")
            return False

    def generate_uuid(self, file_path: str) -> str:
        """Generate deterministic UUID from file_path for idempotency."""
        return str(uuid.uuid5(uuid.NAMESPACE_URL, file_path))

    def to_rfc3339(self, timestamp: float) -> str:
        """Convert Unix timestamp to RFC3339 format for Weaviate."""
        if not timestamp or timestamp <= 0:
            timestamp = datetime.now().timestamp()

        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
        except Exception:
            return datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000000Z')

    def fetch_all_points(self) -> List[Dict[str, Any]]:
        """Fetch all points from Qdrant collection using scroll."""
        if not self.qdrant_client:
            return []

        all_points = []
        offset = None

        logger.info(f"Fetching points from Qdrant '{self.QDRANT_COLLECTION}'...")

        try:
            while True:
                # Scroll through all points
                points, next_offset = self.qdrant_client.scroll(
                    collection_name=self.QDRANT_COLLECTION,
                    limit=500,  # Fetch 500 at a time
                    offset=offset,
                    with_payload=True,
                    with_vectors=True  # Need vectors for Weaviate
                )

                if not points:
                    break

                all_points.extend(points)
                logger.info(f"Fetched {len(all_points)} points...")

                if next_offset is None:
                    break

                offset = next_offset

            self.total_points = len(all_points)
            logger.info(f"Total points fetched: {self.total_points}")
            return all_points

        except Exception as e:
            logger.error(f"Failed to fetch points from Qdrant: {e}")
            return []

    def transform_point(self, point) -> Optional[Dict[str, Any]]:
        """Transform Qdrant point to Weaviate object format."""
        try:
            payload = point.payload or {}

            # Extract fields from Qdrant payload
            file_path = payload.get('path', '')
            file_name = payload.get('name', '')
            content = payload.get('content', '')
            extension = payload.get('extension', '')
            size_bytes = payload.get('size_bytes', 0)
            modified_time = payload.get('modified_time', 0)
            created_time = payload.get('created_time', 0)

            # Derive file_name from path if not present
            if not file_name and file_path:
                file_name = file_path.split('/')[-1]

            # Calculate depth from path
            depth = file_path.count('/') if file_path else 0

            # Extract file_type (extension without dot)
            if extension:
                file_type = extension.lstrip('.')
            elif file_name:
                parts = file_name.rsplit('.', 1)
                file_type = parts[1] if len(parts) > 1 else 'unknown'
            else:
                file_type = 'unknown'

            # Truncate content
            if content and len(content) > self.CONTENT_MAX_LENGTH:
                content = content[:self.CONTENT_MAX_LENGTH]

            # Generate UUID from file_path
            if not file_path:
                logger.warning(f"Point {point.id} has no path, skipping")
                return None

            object_uuid = self.generate_uuid(file_path)

            # Get vector
            vector = point.vector
            if isinstance(vector, dict):
                # Handle named vectors
                vector = list(vector.values())[0] if vector else None

            # Build Weaviate object
            weaviate_obj = {
                'uuid': object_uuid,
                'class': self.WEAVIATE_CLASS,
                'properties': {
                    'file_path': file_path,
                    'file_name': file_name,
                    'content': content or '',
                    'file_type': file_type,
                    'depth': int(depth),
                    'size': int(size_bytes) if size_bytes else 0,
                    'created_at': self.to_rfc3339(created_time),
                    'modified_at': self.to_rfc3339(modified_time)
                },
                'vector': vector
            }

            return weaviate_obj

        except Exception as e:
            logger.error(f"Failed to transform point {point.id}: {e}")
            return None

    def sync_batch(self, batch: List[Dict[str, Any]]) -> int:
        """Sync a batch of objects to Weaviate (v4 API)."""
        if not self.weaviate_client or not batch:
            return 0

        success_count = 0

        try:
            # Get collection reference
            collection = self.weaviate_client.collections.get(self.WEAVIATE_CLASS)

            # Prepare batch objects for v4 API
            data_objects = []
            for obj in batch:
                try:
                    data_objects.append(DataObject(
                        properties=obj['properties'],
                        uuid=obj['uuid'],
                        vector=obj['vector']
                    ))
                except Exception as e:
                    error_msg = f"Failed to prepare object {obj.get('uuid')}: {e}"
                    logger.debug(error_msg)
                    self.errors.append(error_msg)
                    self.error_count += 1

            # Insert batch
            if data_objects:
                result = collection.data.insert_many(data_objects)
                # Count successes (failed uuids will be in result.errors)
                if hasattr(result, 'errors') and result.errors:
                    success_count = len(data_objects) - len(result.errors)
                    for err in result.errors.values():
                        self.errors.append(str(err))
                        self.error_count += 1
                else:
                    success_count = len(data_objects)

        except Exception as e:
            logger.error(f"Batch sync failed: {e}")
            # Try individual inserts as fallback
            collection = self.weaviate_client.collections.get(self.WEAVIATE_CLASS)
            for obj in batch:
                try:
                    collection.data.insert(
                        properties=obj['properties'],
                        uuid=obj['uuid'],
                        vector=obj['vector']
                    )
                    success_count += 1
                except Exception as e2:
                    # Try replace if insert fails (object exists)
                    try:
                        collection.data.replace(
                            properties=obj['properties'],
                            uuid=obj['uuid'],
                            vector=obj['vector']
                        )
                        success_count += 1
                    except Exception as e3:
                        error_msg = f"Individual sync failed for {obj.get('uuid')}: {e3}"
                        logger.debug(error_msg)
                        self.errors.append(error_msg)
                        self.error_count += 1

        return success_count

    def sync(self) -> bool:
        """Main sync process."""
        logger.info("=" * 60)
        logger.info("  QDRANT -> WEAVIATE SYNC")
        logger.info("=" * 60)

        # Connect to both databases
        if not self.connect():
            return False

        # Ensure Weaviate schema
        if not self.ensure_weaviate_schema():
            return False

        # Fetch all points from Qdrant
        points = self.fetch_all_points()
        if not points:
            logger.warning("No points found in Qdrant collection")
            return True

        # Transform and sync in batches
        logger.info(f"Starting sync of {len(points)} points in batches of {self.BATCH_SIZE}...")

        batch = []
        for i, point in enumerate(points):
            # Transform point
            weaviate_obj = self.transform_point(point)
            if weaviate_obj:
                batch.append(weaviate_obj)

            # Sync batch when full
            if len(batch) >= self.BATCH_SIZE:
                synced = self.sync_batch(batch)
                self.synced_count += synced
                batch = []

                # Log progress
                progress = (i + 1) / len(points) * 100
                logger.info(f"Synced {self.synced_count}/{len(points)} ({progress:.1f}%)")

        # Sync remaining batch
        if batch:
            synced = self.sync_batch(batch)
            self.synced_count += synced

        # Final log
        logger.info("=" * 60)
        logger.info("  SYNC COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total points in Qdrant: {self.total_points}")
        logger.info(f"Successfully synced:    {self.synced_count}")
        logger.info(f"Errors:                 {self.error_count}")

        if self.errors and len(self.errors) <= 10:
            logger.info("Error details:")
            for err in self.errors[:10]:
                logger.info(f"  - {err}")

        # Close Weaviate client (v4 requirement)
        if self.weaviate_client:
            try:
                self.weaviate_client.close()
            except:
                pass

        return self.error_count == 0


def main():
    """Entry point."""
    sync = QdrantToWeaviateSync(
        qdrant_host="localhost",
        qdrant_port=6333,
        weaviate_url="http://localhost:8080"
    )

    success = sync.sync()

    if success:
        logger.info("Sync completed successfully!")
        return 0
    else:
        logger.error("Sync completed with errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
