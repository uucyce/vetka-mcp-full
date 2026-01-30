#!/usr/bin/env python3
"""
FIX_101.3 Backfill Script: Populate VetkaTree from vetka_elisya

This one-time script migrates existing file data from vetka_elisya (1760 points)
to VetkaTree collection for hierarchical storage.

Usage:
    python scripts/backfill_vetka_tree.py
"""

import os
import sys
import uuid
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

def backfill_vetka_tree():
    """Migrate data from vetka_elisya to VetkaTree."""
    print("=" * 60)
    print("VetkaTree Backfill Script - FIX_101.3")
    print("=" * 60)

    # Connect to Qdrant
    client = QdrantClient(url="http://127.0.0.1:6333")

    # Get VetkaTree client
    from src.memory.qdrant_client import get_qdrant_client
    vetka_client = get_qdrant_client()

    if not vetka_client or not vetka_client.client:
        print("❌ VetkaTree client not available")
        return

    # Check current state
    try:
        elisya_info = client.get_collection('vetka_elisya')
        tree_info = vetka_client.client.get_collection('VetkaTree')
        print(f"\nCurrent state:")
        print(f"  vetka_elisya: {elisya_info.points_count} points")
        print(f"  VetkaTree: {tree_info.points_count} points")
    except Exception as e:
        print(f"❌ Error getting collection info: {e}")
        return

    # Scroll through vetka_elisya
    print(f"\n🔄 Starting backfill from vetka_elisya to VetkaTree...")

    offset = None
    total_migrated = 0
    total_skipped = 0
    total_errors = 0
    batch_size = 100

    while True:
        # Get batch of points
        results, offset = client.scroll(
            collection_name='vetka_elisya',
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="type", match=MatchValue(value="scanned_file")),
                    FieldCondition(key="deleted", match=MatchValue(value=False))
                ]
            ),
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=True
        )

        if not results:
            break

        for point in results:
            try:
                payload = point.payload
                vector = point.vector

                if not vector:
                    total_skipped += 1
                    continue

                file_path = payload.get('path') or payload.get('file_path', '')
                if not file_path:
                    total_skipped += 1
                    continue

                # Generate IDs
                file_id = str(uuid.uuid5(uuid.NAMESPACE_URL, file_path))
                parent_path = os.path.dirname(file_path)
                parent_id = str(uuid.uuid5(uuid.NAMESPACE_URL, parent_path)) if parent_path else None

                # Prepare metadata
                tree_metadata = {
                    'type': 'scanned_file',
                    'source': 'backfill_101.3',
                    'parent_path': parent_path,
                    'parent_id': parent_id,
                    'depth': file_path.count('/'),
                    'name': payload.get('name', os.path.basename(file_path)),
                    'extension': payload.get('extension', ''),
                    'size_bytes': payload.get('size_bytes', 0),
                    'modified_time': payload.get('modified_time', 0),
                }

                # Write to VetkaTree
                result = vetka_client.triple_write(
                    workflow_id=f"backfill_{file_id[:8]}",
                    node_id=file_id,
                    path=file_path,
                    content=payload.get('content', '')[:500],
                    metadata=tree_metadata,
                    vector=vector
                )

                if result.get('qdrant', False):
                    total_migrated += 1
                else:
                    total_errors += 1

            except Exception as e:
                total_errors += 1
                print(f"  ❌ Error: {e}")

        print(f"  Processed batch: {total_migrated} migrated, {total_skipped} skipped, {total_errors} errors")

        if offset is None:
            break

    # Final stats
    print(f"\n{'=' * 60}")
    print(f"✅ Backfill Complete!")
    print(f"  Migrated: {total_migrated}")
    print(f"  Skipped: {total_skipped}")
    print(f"  Errors: {total_errors}")

    # Verify
    try:
        tree_info = vetka_client.client.get_collection('VetkaTree')
        print(f"\nVetkaTree now has: {tree_info.points_count} points")
    except Exception as e:
        print(f"❌ Error verifying: {e}")


if __name__ == "__main__":
    backfill_vetka_tree()
