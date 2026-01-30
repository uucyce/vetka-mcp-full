#!/usr/bin/env python3
"""
Quick integration verification for group chat persistence.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.group_chat_manager import get_group_chat_manager


async def verify():
    """Verify integration with singleton pattern."""

    print("=== Integration Verification ===\n")

    # Test singleton pattern
    print("1. Testing singleton pattern...")
    manager1 = get_group_chat_manager()
    manager2 = get_group_chat_manager()

    assert manager1 is manager2, "Singleton broken!"
    print("   ✓ Singleton pattern working")

    # Test that groups.json exists
    groups_file = manager1.GROUPS_FILE
    if groups_file.exists():
        print(f"\n2. Persistence file found: {groups_file}")

        # Load existing groups
        await manager1.load_from_json()
        groups = manager1.get_all_groups()

        print(f"   ✓ Loaded {len(groups)} group(s)")

        for group in groups:
            print(f"\n   Group: {group['name']}")
            print(f"   - ID: {group['id']}")
            print(f"   - Participants: {len(group['participants'])}")
            print(f"   - Admin: {group.get('admin_id', 'N/A')}")
            print(f"   - Created: {group.get('created_at', 'N/A')[:19]}")

            # Get messages for this group
            messages = manager1.get_messages(group['id'], limit=5)
            print(f"   - Messages: {len(messages)} (showing last {min(5, len(messages))})")

            for i, msg in enumerate(messages[-5:], 1):
                sender = msg['sender_id']
                content = msg['content'][:60]
                if len(msg['content']) > 60:
                    content += "..."
                print(f"     {i}. [{sender}]: {content}")
    else:
        print(f"\n2. No persistence file found (first run)")

    print("\n✓ Integration verification complete")


if __name__ == "__main__":
    asyncio.run(verify())
