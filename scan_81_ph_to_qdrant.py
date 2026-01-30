#!/usr/bin/env python3
"""
Scan Phase 81 MCP Fixes documentation files into Qdrant collection vetka_elisya
"""

import os
import json
import requests
from typing import List, Dict, Any
from pathlib import Path

# Configuration
PROJECT_ROOT = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "vetka_elisya"
OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "embeddinggemma:300m"

# Files to scan
FILES_TO_SCAN = [
    "docs/81_ph_mcp_fixes/00_README.md",
    "docs/81_ph_mcp_fixes/AUDIT_CHAT_PERSISTENCE.md",
    "docs/81_ph_mcp_fixes/AUDIT_MCP_NOTIFICATIONS.md",
    "docs/81_ph_mcp_fixes/SESSION_SUMMARY.md",
]


def create_embedding(text: str) -> List[float]:
    """Create embedding using Ollama embeddinggemma:300m"""
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={
            "model": EMBEDDING_MODEL,
            "prompt": text
        }
    )
    response.raise_for_status()
    return response.json()["embedding"]


def read_file_content(file_path: str) -> str:
    """Read file content"""
    full_path = os.path.join(PROJECT_ROOT, file_path)
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()


def calculate_depth(file_path: str) -> int:
    """Calculate depth based on path separators"""
    return file_path.count('/')


def extract_parent_folder(file_path: str) -> str:
    """Extract parent folder from file path"""
    return os.path.dirname(file_path)


def upsert_to_qdrant(point_id: int, vector: List[float], payload: Dict[str, Any]) -> None:
    """Upsert point to Qdrant collection"""
    response = requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points",
        json={
            "points": [
                {
                    "id": point_id,
                    "vector": vector,
                    "payload": payload
                }
            ]
        }
    )
    if response.status_code != 200:
        print(f"  ❌ Qdrant error: {response.text}")
    response.raise_for_status()
    print(f"✅ Upserted: {payload['name']}")


def main():
    """Main scanning process"""
    print(f"🚀 Starting Phase 81 MCP Fixes scan to Qdrant collection: {COLLECTION_NAME}")
    print(f"📁 Project root: {PROJECT_ROOT}")
    print(f"📊 Files to scan: {len(FILES_TO_SCAN)}\n")

    scanned_count = 0

    for idx, file_path in enumerate(FILES_TO_SCAN, start=1):
        print(f"\n[{idx}/{len(FILES_TO_SCAN)}] Processing: {file_path}")

        # Read file content
        try:
            content = read_file_content(file_path)
            print(f"  📄 Content size: {len(content)} characters")
        except Exception as e:
            print(f"  ❌ Failed to read file: {e}")
            continue

        # Create embedding
        try:
            print(f"  🧠 Creating embedding with {EMBEDDING_MODEL}...")
            vector = create_embedding(content)
            print(f"  ✓ Embedding created: {len(vector)} dimensions")
        except Exception as e:
            print(f"  ❌ Failed to create embedding: {e}")
            continue

        # Prepare payload
        file_name = os.path.basename(file_path)
        parent_folder = extract_parent_folder(file_path)
        depth = calculate_depth(file_path)

        payload = {
            "path": file_path,
            "name": file_name,
            "content": content,
            "parent_folder": parent_folder,
            "depth": depth,
            "type": "scanned_file",
            "phase": "81_mcp_fixes",
            "category": "documentation",
            "scan_timestamp": "2026-01-21T16:00:00Z"
        }

        # Generate point ID (use hash of file path as integer ID)
        import hashlib
        point_id = int(hashlib.sha256(file_path.encode()).hexdigest()[:16], 16)

        # Upsert to Qdrant
        try:
            upsert_to_qdrant(point_id, vector, payload)
            scanned_count += 1
        except Exception as e:
            print(f"  ❌ Failed to upsert to Qdrant: {e}")
            continue

    print(f"\n{'='*60}")
    print(f"✨ Scan complete!")
    print(f"📊 Total files scanned: {scanned_count}/{len(FILES_TO_SCAN)}")
    print(f"🗄️  Collection: {COLLECTION_NAME}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
