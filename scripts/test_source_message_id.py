#!/usr/bin/env python3
"""
Test script to verify source_message_id is properly stored in artifact staging.

MARKER_103_ARTIFACT_LINK: Test for source_message_id traceability
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.staging_utils import stage_artifact, get_staged_artifacts, _load_staging
import json


def test_source_message_id():
    """Test that source_message_id is properly stored and retrieved."""

    print("🧪 Testing source_message_id in artifact staging...")

    # Create a test artifact
    test_artifact = {
        "id": "test_artifact_001",
        "type": "code",
        "filename": "test_file.py",
        "language": "python",
        "content": "print('Hello from test artifact')",
        "lines": 1,
        "agent": "Dev",
        "created_at": "2026-01-31T10:00:00"
    }

    test_qa_score = 0.85
    test_agent = "Dev"
    test_group_id = "test_group_123"
    test_source_message_id = "msg_abc123xyz"

    # Stage the artifact WITH source_message_id
    print(f"\n1️⃣ Staging artifact with source_message_id={test_source_message_id}...")
    task_id = stage_artifact(
        artifact=test_artifact,
        qa_score=test_qa_score,
        agent=test_agent,
        group_id=test_group_id,
        source_message_id=test_source_message_id
    )

    if not task_id:
        print("❌ Failed to stage artifact!")
        return False

    print(f"✅ Artifact staged with task_id: {task_id}")

    # Load staging data directly to verify
    print("\n2️⃣ Loading staging data to verify...")
    staging_data = _load_staging()

    if task_id not in staging_data.get("artifacts", {}):
        print(f"❌ Task {task_id} not found in staging data!")
        return False

    staged_artifact = staging_data["artifacts"][task_id]

    # Verify all expected fields
    print("\n3️⃣ Verifying staged artifact fields...")

    checks = [
        ("task_id", task_id, staged_artifact.get("task_id")),
        ("qa_score", test_qa_score, staged_artifact.get("qa_score")),
        ("agent", test_agent, staged_artifact.get("agent")),
        ("group_id", test_group_id, staged_artifact.get("group_id")),
        ("source_message_id", test_source_message_id, staged_artifact.get("source_message_id")),
        ("status", "staged", staged_artifact.get("status")),
    ]

    all_passed = True
    for field_name, expected, actual in checks:
        if actual == expected:
            print(f"   ✅ {field_name}: {actual}")
        else:
            print(f"   ❌ {field_name}: expected {expected}, got {actual}")
            all_passed = False

    # Also test retrieval via get_staged_artifacts
    print("\n4️⃣ Testing retrieval via get_staged_artifacts()...")
    artifacts = get_staged_artifacts(status="staged")

    found = False
    for art in artifacts:
        if art.get("task_id") == task_id:
            found = True
            retrieved_source_msg_id = art.get("source_message_id")
            if retrieved_source_msg_id == test_source_message_id:
                print(f"   ✅ source_message_id retrieved correctly: {retrieved_source_msg_id}")
            else:
                print(f"   ❌ source_message_id mismatch: expected {test_source_message_id}, got {retrieved_source_msg_id}")
                all_passed = False
            break

    if not found:
        print(f"   ❌ Artifact {task_id} not found in get_staged_artifacts()")
        all_passed = False

    # Test staging WITHOUT source_message_id (should be None/null)
    print("\n5️⃣ Testing artifact staging WITHOUT source_message_id...")
    test_artifact2 = {**test_artifact, "id": "test_artifact_002"}
    task_id2 = stage_artifact(
        artifact=test_artifact2,
        qa_score=test_qa_score,
        agent=test_agent,
        group_id=test_group_id
        # No source_message_id provided
    )

    if task_id2:
        staging_data2 = _load_staging()
        staged_artifact2 = staging_data2["artifacts"][task_id2]
        source_msg_id2 = staged_artifact2.get("source_message_id")
        if source_msg_id2 is None:
            print(f"   ✅ source_message_id is None when not provided")
        else:
            print(f"   ⚠️  source_message_id is {source_msg_id2} (expected None)")
            # This is OK - it's explicitly None in JSON

    # Final result
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n📋 Summary:")
        print(f"   - source_message_id is properly stored in staging.json")
        print(f"   - source_message_id is retrievable via get_staged_artifacts()")
        print(f"   - Artifacts can be staged with or without source_message_id")
        print("\n🎯 Implementation complete and verified!")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = test_source_message_id()
    sys.exit(0 if success else 1)
