#!/usr/bin/env python3
"""
Chat History Migration Script
Adds missing 'node_path' and 'read' fields to existing chat messages.

Usage:
    python scripts/migrate_chat_history.py
    python scripts/migrate_chat_history.py --dry-run
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
import argparse


def migrate_chat_history(chat_dir: str = "data/chat_history", dry_run: bool = False):
    """
    Migrate all chat history files to include node_path and read fields.
    
    Args:
        chat_dir: Path to chat history directory
        dry_run: If True, only show what would be changed without saving
    
    Returns:
        Dict with migration statistics
    """
    
    chat_path = Path(chat_dir)
    
    if not chat_path.exists():
        print(f"❌ Directory not found: {chat_dir}")
        return {"error": "Directory not found"}
    
    # Statistics
    stats = {
        "files_processed": 0,
        "files_modified": 0,
        "messages_total": 0,
        "messages_updated": 0,
        "errors": []
    }
    
    # Create backup directory
    if not dry_run:
        backup_dir = chat_path.parent / f"chat_history_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(exist_ok=True)
        print(f"📦 Backup directory: {backup_dir}")
    
    # Process each JSON file
    json_files = list(chat_path.glob("*.json"))
    print(f"\n📂 Found {len(json_files)} chat history files\n")
    
    for json_file in json_files:
        stats["files_processed"] += 1
        file_modified = False
        
        try:
            # Read file
            with open(json_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            if not isinstance(messages, list):
                print(f"⚠️  {json_file.name}: Not a list, skipping")
                continue
            
            # Extract node identifier from filename
            # Filename format: 09e3bc97e31983f8.json or similar hash
            file_node_id = json_file.stem
            default_node_path = f"node_{file_node_id}"
            
            # Process each message
            for msg in messages:
                stats["messages_total"] += 1
                updated = False
                
                # Add node_path if missing
                if "node_path" not in msg:
                    # Try to derive from node_id or use filename
                    if "node_id" in msg:
                        msg["node_path"] = f"node_{msg['node_id']}"
                    else:
                        msg["node_path"] = default_node_path
                    updated = True
                
                # Add read field if missing
                if "read" not in msg:
                    # User messages are "read", assistant messages are "unread"
                    role = msg.get("role", "").lower()
                    msg["read"] = role == "user"
                    updated = True
                
                if updated:
                    stats["messages_updated"] += 1
                    file_modified = True
            
            # Save if modified
            if file_modified:
                stats["files_modified"] += 1
                
                if dry_run:
                    print(f"🔍 {json_file.name}: Would update {sum(1 for m in messages if 'node_path' in m)} messages")
                else:
                    # Backup original
                    shutil.copy2(json_file, backup_dir / json_file.name)
                    
                    # Save updated
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(messages, f, indent=2, ensure_ascii=False)
                    
                    print(f"✅ {json_file.name}: Updated {len(messages)} messages")
            else:
                print(f"⏭️  {json_file.name}: Already migrated")
                
        except json.JSONDecodeError as e:
            stats["errors"].append(f"{json_file.name}: Invalid JSON - {e}")
            print(f"❌ {json_file.name}: Invalid JSON")
        except Exception as e:
            stats["errors"].append(f"{json_file.name}: {e}")
            print(f"❌ {json_file.name}: {e}")
    
    return stats


def print_summary(stats: dict, dry_run: bool = False):
    """Print migration summary."""
    
    print("\n" + "=" * 50)
    print("📊 MIGRATION SUMMARY")
    print("=" * 50)
    
    if dry_run:
        print("🔍 DRY RUN - No changes made\n")
    
    print(f"Files processed:    {stats['files_processed']}")
    print(f"Files modified:     {stats['files_modified']}")
    print(f"Messages total:     {stats['messages_total']}")
    print(f"Messages updated:   {stats['messages_updated']}")
    
    if stats["errors"]:
        print(f"\n⚠️  Errors: {len(stats['errors'])}")
        for err in stats["errors"]:
            print(f"   - {err}")
    
    print("=" * 50)
    
    if not dry_run and stats["files_modified"] > 0:
        print("\n✅ Migration complete! Backup created.")
        print("   Run with --dry-run to preview changes next time.")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate chat history files to add node_path and read fields"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without saving"
    )
    parser.add_argument(
        "--dir",
        default="data/chat_history",
        help="Chat history directory (default: data/chat_history)"
    )
    
    args = parser.parse_args()
    
    print("🚀 Chat History Migration Script")
    print(f"   Directory: {args.dir}")
    print(f"   Dry run: {args.dry_run}")
    
    stats = migrate_chat_history(
        chat_dir=args.dir,
        dry_run=args.dry_run
    )
    
    print_summary(stats, args.dry_run)


if __name__ == "__main__":
    main()
