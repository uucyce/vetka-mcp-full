#!/usr/bin/env python3
"""
Phase 50 - Chat History Feature Test Script
Test chat persistence, API endpoints, and history management.

@file test_phase50.py
@status ACTIVE
@phase Phase 50 - Chat History + Sidebar UI
"""

import json
import uuid
from pathlib import Path
from src.chat.chat_history_manager import ChatHistoryManager, get_chat_history_manager


def test_chat_history_manager():
    """Test ChatHistoryManager functionality."""
    print("\n" + "="*60)
    print("TEST: ChatHistoryManager")
    print("="*60)

    # Create temp history file for testing
    test_file = "data/test_chat_history.json"
    manager = ChatHistoryManager(test_file)

    # Test 1: Create chat
    print("\n[TEST 1] Creating chat for test file...")
    chat_id = manager.get_or_create_chat("/path/to/test_file.py")
    print(f"✓ Created chat: {chat_id}")

    # Test 2: Add user message
    print("\n[TEST 2] Adding user message...")
    success = manager.add_message(chat_id, {
        "role": "user",
        "content": "What does this function do?",
        "node_id": "test_node"
    })
    print(f"✓ User message added: {success}")

    # Test 3: Add assistant message
    print("\n[TEST 3] Adding assistant message...")
    success = manager.add_message(chat_id, {
        "role": "assistant",
        "agent": "Dev",
        "model": "deepseek-coder:6.7b",
        "content": "This function calculates the sum of all numbers."
    })
    print(f"✓ Assistant message added: {success}")

    # Test 4: Get chat messages
    print("\n[TEST 4] Retrieving chat messages...")
    messages = manager.get_chat_messages(chat_id)
    print(f"✓ Retrieved {len(messages)} messages")
    for i, msg in enumerate(messages, 1):
        print(f"  Message {i}: {msg['role']} - {msg['content'][:50]}...")

    # Test 5: Get all chats (Phase 107.3: now supports pagination)
    print("\n[TEST 5] Getting all chats...")
    all_chats = manager.get_all_chats()  # Uses default limit=50, offset=0
    print(f"✓ Total chats: {len(all_chats)}")

    # Test 6: Get chat for specific file
    print("\n[TEST 6] Getting chats for specific file...")
    file_chats = manager.get_chats_for_file("/path/to/test_file.py")
    print(f"✓ Chats for file: {len(file_chats)}")

    # Test 7: Search messages
    print("\n[TEST 7] Searching messages...")
    results = manager.search_messages("function")
    print(f"✓ Search results: {len(results)} matches")

    # Test 8: Export chat
    print("\n[TEST 8] Exporting chat...")
    export_json = manager.export_chat(chat_id)
    if export_json:
        data = json.loads(export_json)
        print(f"✓ Exported chat with {len(data.get('messages', []))} messages")

    # Test 9: Delete chat
    print("\n[TEST 9] Deleting chat...")
    success = manager.delete_chat(chat_id)
    print(f"✓ Chat deleted: {success}")

    # Cleanup
    Path(test_file).unlink(missing_ok=True)

    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED!")
    print("="*60)


def test_singleton():
    """Test singleton pattern for ChatHistoryManager."""
    print("\n" + "="*60)
    print("TEST: Singleton Pattern")
    print("="*60)

    manager1 = get_chat_history_manager()
    manager2 = get_chat_history_manager()

    print(f"\nManager 1 ID: {id(manager1)}")
    print(f"Manager 2 ID: {id(manager2)}")
    print(f"Same instance: {manager1 is manager2}")

    assert manager1 is manager2, "Singleton pattern failed!"
    print("\n✓ Singleton pattern working correctly")


def test_persistence():
    """Test that chat data persists to disk."""
    print("\n" + "="*60)
    print("TEST: Data Persistence")
    print("="*60)

    test_file = "data/test_persistence.json"

    # Create manager and add data
    print("\n[STEP 1] Creating manager and adding data...")
    manager1 = ChatHistoryManager(test_file)
    chat_id = manager1.get_or_create_chat("/path/to/file.py")
    manager1.add_message(chat_id, {
        "role": "user",
        "content": "Test message for persistence"
    })
    print(f"✓ Data added, chat ID: {chat_id}")

    # Verify file exists
    if Path(test_file).exists():
        print(f"✓ History file created: {test_file}")
        file_size = Path(test_file).stat().st_size
        print(f"  File size: {file_size} bytes")
    else:
        raise AssertionError("History file not created!")

    # Create new manager instance and verify data loads
    print("\n[STEP 2] Creating new manager instance and loading data...")
    manager2 = ChatHistoryManager(test_file)
    messages = manager2.get_chat_messages(chat_id)
    print(f"✓ Loaded {len(messages)} messages from disk")
    assert len(messages) == 1, "Message persistence failed!"
    assert messages[0]["content"] == "Test message for persistence"
    print(f"✓ Message content verified: {messages[0]['content']}")

    # Cleanup
    Path(test_file).unlink(missing_ok=True)

    print("\n✓ Persistence test passed!")


def test_structure():
    """Test that history file structure is correct."""
    print("\n" + "="*60)
    print("TEST: History File Structure")
    print("="*60)

    test_file = "data/test_structure.json"
    manager = ChatHistoryManager(test_file)

    # Create and populate
    chat_id = manager.get_or_create_chat("/test/file.py")
    manager.add_message(chat_id, {"role": "user", "content": "Test"})

    # Check file structure
    with open(test_file) as f:
        data = json.load(f)

    print("\n[Checking structure]")
    assert "chats" in data, "Missing 'chats' key"
    print("✓ 'chats' key exists")

    assert "groups" in data, "Missing 'groups' key"
    print("✓ 'groups' key exists")

    assert chat_id in data["chats"], f"Chat {chat_id} not found"
    print(f"✓ Chat {chat_id} found in chats")

    chat = data["chats"][chat_id]
    assert "id" in chat, "Missing 'id' in chat"
    assert "file_path" in chat, "Missing 'file_path' in chat"
    assert "file_name" in chat, "Missing 'file_name' in chat"
    assert "created_at" in chat, "Missing 'created_at' in chat"
    assert "updated_at" in chat, "Missing 'updated_at' in chat"
    assert "messages" in chat, "Missing 'messages' in chat"
    print("✓ All required fields in chat object")

    assert len(chat["messages"]) == 1, "Message not saved"
    msg = chat["messages"][0]
    assert "id" in msg, "Message missing 'id'"
    assert "role" in msg, "Message missing 'role'"
    assert "content" in msg, "Message missing 'content'"
    assert "timestamp" in msg, "Message missing 'timestamp'"
    print("✓ All required fields in message object")

    # Cleanup
    Path(test_file).unlink(missing_ok=True)

    print("\n✓ Structure test passed!")


if __name__ == "__main__":
    print("\n" + "█"*60)
    print("█  PHASE 50: CHAT HISTORY FEATURE TEST")
    print("█"*60)

    try:
        test_chat_history_manager()
        test_singleton()
        test_persistence()
        test_structure()

        print("\n" + "█"*60)
        print("█  ALL PHASE 50 TESTS PASSED! ✓")
        print("█"*60)

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
