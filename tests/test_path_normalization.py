#!/usr/bin/env python3
"""
Phase 51.1: Test path normalization fix for chat history.

This script verifies that different path representations resolve to the same chat.
"""

import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.chat.chat_history_manager import get_chat_history_manager


def test_path_normalization():
    """Test that different path representations resolve to same chat."""
    manager = get_chat_history_manager()

    # Use a real file from the project
    test_file = Path(__file__)  # Use the test file itself

    if not test_file.exists():
        print(f"⚠️  Test file doesn't exist: {test_file}")
        return False

    # Test different path representations
    paths_to_test = [
        str(test_file.resolve()),  # Absolute normalized
        str(test_file),  # Relative
        str(test_file.resolve()) + "/./",  # With ./ (will fail resolve but ok)
    ]

    chat_ids = []

    for path in paths_to_test:
        try:
            chat_id = manager.get_or_create_chat(path)
            chat_ids.append(chat_id)
            print(f"✓ Path: {path[:60]}...")
            print(f"  → chat_id: {chat_id}")
        except Exception as e:
            print(f"✗ Error with path {path}: {e}")
            return False

    # Check if all chat_ids are the same
    unique_chat_ids = set(chat_ids)

    if len(unique_chat_ids) == 1:
        print(f"\n✅ SUCCESS: All paths resolved to same chat: {chat_ids[0]}")

        # Verify we can retrieve messages
        messages = manager.get_chat_messages(chat_ids[0])
        print(f"✓ Chat has {len(messages)} messages")
        return True
    else:
        print(f"\n❌ FAILURE: Got {len(unique_chat_ids)} different chats:")
        for i, cid in enumerate(unique_chat_ids):
            print(f"  {i+1}. {cid}")
        return False


def test_edge_cases():
    """Test special path values."""
    manager = get_chat_history_manager()

    print("\n🔍 Testing edge cases...")

    # Test special values
    special_paths = ['unknown', 'root', '']

    for path in special_paths:
        try:
            chat_id = manager.get_or_create_chat(path)
            print(f"✓ Special path '{path}' → {chat_id}")
        except Exception as e:
            print(f"✗ Error with special path '{path}': {e}")
            return False

    print("✅ Edge cases handled correctly")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 51.1: PATH NORMALIZATION TEST")
    print("=" * 60)

    success = True

    # Run tests
    if not test_path_normalization():
        success = False

    if not test_edge_cases():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED")
        print("Path normalization is working correctly!")
    else:
        print("❌ SOME TESTS FAILED")
        print("Check the output above for details.")
    print("=" * 60)

    sys.exit(0 if success else 1)
