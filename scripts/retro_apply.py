#!/usr/bin/env python3
"""
MARKER_103.6: Universal Retro-Apply Script for VETKA

Apply staged results (spawn outputs or artifacts) to disk.
Supports dry-run, filtering, review mode, and auto-apply.

Usage:
    python scripts/retro_apply.py --type spawn --dry-run
    python scripts/retro_apply.py --type artifacts --min-qa-score 0.75
    python scripts/retro_apply.py --type all --auto-apply
    python scripts/retro_apply.py --type spawn --task-filter "voice"
    python scripts/retro_apply.py --type artifacts --review

@status: active
@phase: 103.6
@depends: src/utils/staging_utils.py
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.staging_utils import (
    _load_staging,
    get_staged_artifacts,
    update_artifact_status,
    apply_staged_item,
    upsert_to_qdrant,
    extract_code_blocks,
    determine_filepath,
    write_file_safe
)

# Also support legacy pipeline_tasks.json for spawn
PIPELINE_TASKS_FILE = Path(__file__).parent.parent / "data" / "pipeline_tasks.json"


def load_spawn_tasks(task_filter: str = None) -> list:
    """Load spawn tasks from pipeline_tasks.json (legacy format)."""
    if not PIPELINE_TASKS_FILE.exists():
        return []

    tasks = json.loads(PIPELINE_TASKS_FILE.read_text())
    result = []

    for task_id, task_data in tasks.items():
        # Filter by keyword if specified
        if task_filter:
            task_desc = task_data.get("task", "").lower()
            if task_filter.lower() not in task_desc:
                continue

        # Only process build tasks
        if task_data.get("phase_type") != "build":
            continue

        subtasks = task_data.get("subtasks", [])
        for sub in subtasks:
            result_content = sub.get("result", "")
            if result_content and "```" in result_content:
                result.append({
                    "task_id": task_id,
                    "description": sub.get("description", ""),
                    "marker": sub.get("marker", ""),
                    "content": result_content,
                    "status": "staged"
                })

    return result


def apply_spawn_tasks(tasks: list, dry_run: bool = False, review: bool = False) -> int:
    """Apply spawn tasks to disk."""
    total_files = 0

    for task in tasks:
        print(f"\n📦 Task: {task['task_id']}")
        print(f"   Description: {task['description'][:60]}...")

        if review:
            # Show content preview
            blocks = extract_code_blocks(task['content'])
            for i, block in enumerate(blocks):
                filepath = determine_filepath(
                    filename=block.get("filename"),
                    description=task['description'],
                    marker=task.get('marker', f'file_{i}'),
                    agent="Spawn"
                )
                print(f"\n   File {i+1}: {filepath}")
                print(f"   Language: {block['language']}")
                print(f"   Preview: {block['code'][:200]}...")
                response = input("   Apply? (y/n/q): ").strip().lower()
                if response == 'q':
                    return total_files
                if response != 'y':
                    continue

                result = write_file_safe(filepath, block['code'], dry_run=dry_run)
                if result:
                    total_files += 1
        else:
            # Batch apply
            files = apply_staged_item(task, item_type="spawn", dry_run=dry_run)
            total_files += len(files)
            for f in files:
                prefix = "[DRY-RUN] Would create" if dry_run else "✅ Created"
                print(f"   {prefix}: {f}")

    return total_files


def apply_artifacts(
    min_qa_score: float = 0.0,
    dry_run: bool = False,
    review: bool = False,
    auto_apply: bool = False
) -> int:
    """Apply staged artifacts to disk."""
    artifacts = get_staged_artifacts(status="staged", min_qa_score=min_qa_score)

    if not artifacts:
        print("📭 No staged artifacts found")
        return 0

    print(f"\n📦 Found {len(artifacts)} staged artifacts")
    total_files = 0

    for artifact in artifacts:
        task_id = artifact.get("task_id", "unknown")
        filename = artifact.get("filename", "unknown")
        qa_score = artifact.get("qa_score", 0)

        print(f"\n🎯 Artifact: {task_id}")
        print(f"   File: {filename}")
        print(f"   QA Score: {qa_score:.2f}")
        print(f"   Agent: {artifact.get('agent', 'unknown')}")

        # Auto-apply check
        if auto_apply and qa_score < 0.75:
            print(f"   ⏭️  Skipped (QA score < 0.75)")
            continue

        if review:
            content = artifact.get("content", "")
            print(f"\n   Preview:\n   {content[:300]}...")
            response = input("\n   Apply? (y/n/q): ").strip().lower()
            if response == 'q':
                return total_files
            if response != 'y':
                update_artifact_status(task_id, "rejected")
                print("   ❌ Rejected")
                continue

        # Apply to disk
        files = apply_staged_item(artifact, item_type="artifact", dry_run=dry_run)
        total_files += len(files)

        for f in files:
            prefix = "[DRY-RUN] Would create" if dry_run else "✅ Created"
            print(f"   {prefix}: {f}")

        if not dry_run and files:
            update_artifact_status(task_id, "applied")
            # Optional: upsert to Qdrant
            upsert_to_qdrant(artifact, item_type="artifact")

    return total_files


def main():
    parser = argparse.ArgumentParser(
        description="Universal retro-apply for VETKA staging"
    )
    parser.add_argument(
        "--type",
        choices=["spawn", "artifacts", "all"],
        default="all",
        help="What to apply: spawn outputs, artifacts, or all"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without writing"
    )
    parser.add_argument(
        "--task-filter",
        type=str,
        help="Filter tasks by keyword (e.g., 'voice')"
    )
    parser.add_argument(
        "--min-qa-score",
        type=float,
        default=0.0,
        help="Minimum QA score for artifacts (0-1)"
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Interactive review mode (Y/N for each item)"
    )
    parser.add_argument(
        "--auto-apply",
        action="store_true",
        help="Auto-apply only items with QA score >= 0.75"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("🔄 VETKA Retro-Apply")
    print("=" * 50)
    print(f"Type: {args.type}")
    print(f"Dry-run: {args.dry_run}")
    if args.task_filter:
        print(f"Filter: {args.task_filter}")
    if args.min_qa_score > 0:
        print(f"Min QA Score: {args.min_qa_score}")
    print("=" * 50)

    total_spawn = 0
    total_artifacts = 0

    # Apply spawn outputs
    if args.type in ["spawn", "all"]:
        print("\n📂 Processing Spawn outputs...")
        spawn_tasks = load_spawn_tasks(task_filter=args.task_filter)
        if spawn_tasks:
            total_spawn = apply_spawn_tasks(
                spawn_tasks,
                dry_run=args.dry_run,
                review=args.review
            )
        else:
            print("   No spawn tasks found")

    # Apply artifacts
    if args.type in ["artifacts", "all"]:
        print("\n📂 Processing Artifacts...")
        total_artifacts = apply_artifacts(
            min_qa_score=args.min_qa_score,
            dry_run=args.dry_run,
            review=args.review,
            auto_apply=args.auto_apply
        )

    # Summary
    print("\n" + "=" * 50)
    print("📊 Summary:")
    if args.type in ["spawn", "all"]:
        action = "would be created" if args.dry_run else "created"
        print(f"   Spawn files {action}: {total_spawn}")
    if args.type in ["artifacts", "all"]:
        action = "would be created" if args.dry_run else "created"
        print(f"   Artifact files {action}: {total_artifacts}")
    print(f"   Total: {total_spawn + total_artifacts}")

    if args.dry_run:
        print("\n💡 Run without --dry-run to actually create the files")


if __name__ == "__main__":
    main()
