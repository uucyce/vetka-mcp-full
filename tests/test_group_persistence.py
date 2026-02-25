#!/usr/bin/env python3
"""
Test script for group chat persistence.
Demonstrates save/load functionality for group chats.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.group_chat_manager import (
    GroupChatManager,
    GroupParticipant,
    GroupRole
)


async def test_persistence():
    """Test group chat save and load functionality."""

    print("=== Testing Group Chat Persistence ===\n")

    # Create manager
    manager = GroupChatManager()

    # Test 1: Create a group
    print("1. Creating test group...")
    admin = GroupParticipant(
        agent_id="@admin",
        model_id="claude-sonnet-4-5",
        role=GroupRole.ADMIN,
        display_name="Admin"
    )

    dev = GroupParticipant(
        agent_id="@dev",
        model_id="deepseek-r1",
        role=GroupRole.WORKER,
        display_name="Developer"
    )

    group = await manager.create_group(
        name="Test Project",
        admin_agent=admin,
        participants=[dev],
        description="Testing persistence"
    )

    print(f"   ✓ Created group: {group.name} (ID: {group.id})")

    # Test 2: Send some messages
    print("\n2. Sending test messages...")
    await manager.send_message(
        group_id=group.id,
        sender_id="@admin",
        content="Hello team! Let's test persistence.",
        message_type="chat"
    )

    await manager.send_message(
        group_id=group.id,
        sender_id="@dev",
        content="@admin Got it! This should be saved.",
        message_type="chat"
    )

    print(f"   ✓ Sent 2 messages")

    # Check saved file
    groups_file = manager.GROUPS_FILE
    if groups_file.exists():
        import json
        with open(groups_file, 'r') as f:
            data = json.load(f)
        print(f"\n   ✓ Groups saved to: {groups_file}")
        print(f"   ✓ File size: {groups_file.stat().st_size} bytes")
        print(f"   ✓ Groups in file: {len(data.get('groups', {}))}")
        print(f"   ✓ Messages in group: {len(data['groups'][group.id]['messages'])}")

    # Test 3: Reload groups
    print("\n3. Testing reload...")
    manager2 = GroupChatManager()
    await manager2.load_from_json()

    loaded_groups = manager2.get_all_groups()
    print(f"   ✓ Loaded {len(loaded_groups)} group(s)")

    if loaded_groups:
        loaded_group = loaded_groups[0]
        print(f"   ✓ Group name: {loaded_group['name']}")
        print(f"   ✓ Participants: {len(loaded_group['participants'])}")

        messages = manager2.get_messages(loaded_group['id'])
        print(f"   ✓ Messages: {len(messages)}")

        for i, msg in enumerate(messages, 1):
            print(f"      {i}. [{msg['sender_id']}]: {msg['content'][:50]}...")

    print("\n=== Persistence Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_persistence())
