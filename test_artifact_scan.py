#!/usr/bin/env python3
"""
Test script for artifact scanner functionality.
Phase 108.3 - Artifact scanning verification.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.artifact_scanner import (
    scan_artifacts,
    build_artifact_edges,
    update_artifact_positions
)


def test_artifact_scan():
    """Test artifact scanning."""
    print("=" * 80)
    print("ARTIFACT SCANNER TEST - Phase 108.3")
    print("=" * 80)
    print()

    # Step 1: Scan artifacts
    print("[1] Scanning artifacts directory...")
    artifacts = scan_artifacts()
    print(f"    Found {len(artifacts)} artifacts")
    print()

    # Step 2: Display sample artifacts
    print("[2] Sample artifact nodes:")
    for i, artifact in enumerate(artifacts[:3]):
        print(f"\n    Artifact {i+1}:")
        print(f"      ID: {artifact['id']}")
        print(f"      Name: {artifact['name']}")
        print(f"      Type: {artifact['metadata']['artifact_type']}")
        print(f"      Language: {artifact['metadata']['language']}")
        print(f"      Size: {artifact['metadata']['size_bytes']} bytes")
        print(f"      Parent: {artifact['parent_id']}")
        print(f"      Source Chat: {artifact['metadata']['source_chat_id']}")
        print(f"      Status: {artifact['metadata']['status']}")
        print(f"      Color: {artifact['visual_hints']['color']}")
        print(f"      Position: x={artifact['visual_hints']['layout_hint']['expected_x']}, "
              f"y={artifact['visual_hints']['layout_hint']['expected_y']}")

    if len(artifacts) > 3:
        print(f"\n    ... and {len(artifacts) - 3} more artifacts")
    print()

    # Step 3: Test edge building
    print("[3] Testing artifact edge building...")
    # Create mock chat nodes
    mock_chat_nodes = [
        {
            "id": "chat_test123",
            "type": "chat",
            "visual_hints": {
                "layout_hint": {
                    "expected_x": 50,
                    "expected_y": 30,
                    "expected_z": 0
                }
            }
        }
    ]

    edges = build_artifact_edges(artifacts, mock_chat_nodes)
    print(f"    Built {len(edges)} artifact edges")

    if edges:
        print(f"\n    Sample edge:")
        edge = edges[0]
        print(f"      From: {edge['from']}")
        print(f"      To: {edge['to']}")
        print(f"      Semantics: {edge['semantics']}")
        print(f"      Color: {edge['metadata']['color']}")
    print()

    # Step 4: Test position updates
    print("[4] Testing artifact position updates...")
    original_pos = artifacts[0]['visual_hints']['layout_hint'].copy() if artifacts else None
    update_artifact_positions(artifacts, mock_chat_nodes)

    if artifacts and original_pos:
        new_pos = artifacts[0]['visual_hints']['layout_hint']
        print(f"    Position update example:")
        print(f"      Before: x={original_pos['expected_x']}, y={original_pos['expected_y']}")
        print(f"      After:  x={new_pos['expected_x']}, y={new_pos['expected_y']}")
    print()

    # Step 5: Artifact type distribution
    print("[5] Artifact type distribution:")
    type_counts = {}
    for artifact in artifacts:
        art_type = artifact['metadata']['artifact_type']
        type_counts[art_type] = type_counts.get(art_type, 0) + 1

    for art_type, count in sorted(type_counts.items()):
        print(f"    {art_type}: {count}")
    print()

    # Step 6: Export sample JSON
    print("[6] Exporting sample artifact node JSON...")
    if artifacts:
        sample_file = Path("data/artifact_sample_node.json")
        with open(sample_file, 'w') as f:
            json.dump(artifacts[0], f, indent=2)
        print(f"    Saved to: {sample_file}")
    print()

    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()
    print(f"Summary:")
    print(f"  Total artifacts: {len(artifacts)}")
    print(f"  Total edges: {len(edges)}")
    print(f"  Artifact types: {len(type_counts)}")
    print()

    return artifacts, edges


if __name__ == "__main__":
    test_artifact_scan()
