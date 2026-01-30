#!/usr/bin/env python3
"""
MARKER_103.7: Migrate existing chat history to VetkaGroupChat (Qdrant)

This script migrates existing chat history from JSON files to Qdrant
for semantic search and long-term memory.

Sources:
- data/chat_history.json (file-based chats)
- data/groups.json (group messages)

Usage:
    python scripts/migrate_chat_to_qdrant.py --dry-run
    python scripts/migrate_chat_to_qdrant.py --limit 100
    python scripts/migrate_chat_to_qdrant.py --all

@status: active
@phase: 103.7
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Paths
CHAT_HISTORY_FILE = Path(__file__).parent.parent / "data" / "chat_history.json"
GROUPS_FILE = Path(__file__).parent.parent / "data" / "groups.json"


def load_chat_history():
    """Load chat history from JSON."""
    if not CHAT_HISTORY_FILE.exists():
        return {}
    try:
        return json.loads(CHAT_HISTORY_FILE.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"❌ Error loading chat_history.json: {e}")
        return {}


def load_groups():
    """Load groups from JSON."""
    if not GROUPS_FILE.exists():
        return {}
    try:
        return json.loads(GROUPS_FILE.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"❌ Error loading groups.json: {e}")
        return {}


def migrate_chat_history(dry_run: bool = False, limit: int = None):
    """Migrate chat_history.json to Qdrant."""
    from src.memory.qdrant_client import upsert_chat_message, get_qdrant_client

    # Check Qdrant connection
    client = get_qdrant_client()
    if not client or not client.client:
        print("❌ Qdrant not available. Start Qdrant first!")
        return 0

    chat_data = load_chat_history()
    total_migrated = 0
    total_skipped = 0

    print(f"\n📂 Processing chat_history.json...")
    print(f"   Found {len(chat_data)} chats")

    for chat_id, chat_info in chat_data.items():
        messages = chat_info.get("messages", [])
        chat_name = chat_info.get("display_name", "unknown")

        if not messages:
            continue

        print(f"\n   📝 Chat: {chat_name} ({len(messages)} messages)")

        for msg in messages:
            if limit and total_migrated >= limit:
                print(f"\n⚠️  Reached limit of {limit} messages")
                return total_migrated

            content = msg.get("content", "")
            if not content or len(content) < 10:
                total_skipped += 1
                continue

            role = msg.get("role", "user")
            agent = msg.get("agent")
            model = msg.get("model")
            msg_id = msg.get("id", f"legacy_{chat_id}_{total_migrated}")
            timestamp = msg.get("timestamp", datetime.now().isoformat())

            if dry_run:
                print(f"      [DRY-RUN] Would migrate: {role} - {content[:50]}...")
                total_migrated += 1
            else:
                success = upsert_chat_message(
                    group_id=chat_id,
                    message_id=msg_id,
                    sender_id=agent or "user",
                    content=content,
                    role=role,
                    agent=agent,
                    model=model,
                    metadata={"source": "migration", "original_timestamp": timestamp}
                )
                if success:
                    total_migrated += 1
                else:
                    total_skipped += 1

    return total_migrated


def migrate_groups(dry_run: bool = False, limit: int = None):
    """Migrate groups.json to Qdrant."""
    from src.memory.qdrant_client import upsert_chat_message, get_qdrant_client

    # Check Qdrant connection
    client = get_qdrant_client()
    if not client or not client.client:
        print("❌ Qdrant not available")
        return 0

    raw_data = load_groups()
    # Handle nested structure: {"groups": {...}}
    groups_data = raw_data.get("groups", raw_data) if isinstance(raw_data, dict) else {}

    total_migrated = 0
    total_skipped = 0

    print(f"\n📂 Processing groups.json...")
    print(f"   Found {len(groups_data)} groups")

    for group_id, group_info in groups_data.items():
        if not isinstance(group_info, dict):
            continue
        messages = group_info.get("messages", [])
        group_name = group_info.get("name", "unknown")

        if not messages:
            continue

        print(f"\n   👥 Group: {group_name} ({len(messages)} messages)")

        for msg in messages:
            if limit and total_migrated >= limit:
                print(f"\n⚠️  Reached limit of {limit} messages")
                return total_migrated

            content = msg.get("content", "")
            if not content or len(content) < 10:
                total_skipped += 1
                continue

            sender_id = msg.get("sender_id", "unknown")
            msg_type = msg.get("message_type", "chat")
            msg_id = msg.get("id", f"legacy_{group_id}_{total_migrated}")
            timestamp = msg.get("created_at", datetime.now().isoformat())

            # Determine role
            role = "assistant" if sender_id.startswith("@") else "user"
            agent = sender_id if sender_id.startswith("@") else None

            if dry_run:
                print(f"      [DRY-RUN] Would migrate: {sender_id} - {content[:50]}...")
                total_migrated += 1
            else:
                success = upsert_chat_message(
                    group_id=group_id,
                    message_id=msg_id,
                    sender_id=sender_id,
                    content=content,
                    role=role,
                    agent=agent,
                    metadata={
                        "source": "migration",
                        "message_type": msg_type,
                        "original_timestamp": timestamp
                    }
                )
                if success:
                    total_migrated += 1
                else:
                    total_skipped += 1

    return total_migrated


def main():
    parser = argparse.ArgumentParser(
        description="Migrate chat history to VetkaGroupChat (Qdrant)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually doing it"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of messages to migrate"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Migrate all messages (no limit)"
    )
    parser.add_argument(
        "--source",
        choices=["chat_history", "groups", "all"],
        default="all",
        help="Which source to migrate"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("🔄 VETKA Chat History Migration")
    print("=" * 50)
    print(f"Dry-run: {args.dry_run}")
    print(f"Limit: {args.limit or 'unlimited' if args.all else args.limit or 100}")
    print(f"Source: {args.source}")
    print("=" * 50)

    limit = None if args.all else (args.limit or 100)
    total = 0

    if args.source in ["chat_history", "all"]:
        total += migrate_chat_history(dry_run=args.dry_run, limit=limit)

    if args.source in ["groups", "all"]:
        remaining = (limit - total) if limit else None
        total += migrate_groups(dry_run=args.dry_run, limit=remaining)

    print("\n" + "=" * 50)
    print(f"📊 Migration Summary:")
    action = "would be migrated" if args.dry_run else "migrated"
    print(f"   Messages {action}: {total}")
    print("=" * 50)

    if args.dry_run:
        print("\n💡 Run without --dry-run to actually migrate")


if __name__ == "__main__":
    main()
