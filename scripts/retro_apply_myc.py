#!/usr/bin/env python3
"""
MARKER_103.4: Retro-apply spawn results to create files from pipeline_tasks.json

This script processes existing spawn results and creates the files that were
generated but not written to disk (before the post-processing fix).

Usage:
    python scripts/retro_apply_spawn.py
    python scripts/retro_apply_spawn.py --dry-run
    python scripts/retro_apply_spawn.py --task-filter "voice"
"""

import json
import re
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

# Paths
TASKS_FILE = Path(__file__).parent.parent / "data" / "pipeline_tasks.json"


@dataclass
class MockSubtask:
    """Mock subtask for extraction"""
    description: str = ""
    marker: str = ""


def extract_and_write_files(content: str, subtask: MockSubtask, dry_run: bool = False) -> List[str]:
    """Extract code blocks from content and write to disk."""
    files_created: List[str] = []

    # Pattern to match code blocks
    pattern = r'```(?:python|py|javascript|js|typescript|ts|)?\s*\n(.*?)\n```'
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

    if not matches:
        return files_created

    for i, code_block in enumerate(matches):
        code = code_block.strip()
        if not code:
            continue

        # Determine filepath from subtask description
        filepath = None
        if subtask.description:
            path_match = re.search(
                r'(src/[^\s]+?\.(?:py|js|ts|tsx|md|json))',
                subtask.description,
                re.IGNORECASE
            )
            if path_match:
                filepath = path_match.group(1)

        # Fallback: Use MARKER or generic name
        if not filepath:
            marker = subtask.marker or f'file_{i+1}'
            safe_marker = re.sub(r'[^\w\-_.]', '_', str(marker))
            filepath = f"src/vetka_out/{safe_marker}.py"

        if dry_run:
            print(f"  [DRY-RUN] Would create: {filepath} ({len(code)} chars)")
            files_created.append(filepath)
        else:
            try:
                path_obj = Path(filepath)
                path_obj.parent.mkdir(parents=True, exist_ok=True)
                path_obj.write_text(code, encoding='utf-8')
                files_created.append(filepath)
                print(f"  ✅ Created: {filepath} ({len(code)} chars)")
            except Exception as e:
                print(f"  ❌ Failed: {filepath} - {e}")

    return files_created


def main():
    parser = argparse.ArgumentParser(description="Retro-apply spawn results to create files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created without writing")
    parser.add_argument("--task-filter", type=str, help="Filter tasks by keyword (e.g., 'voice')")
    args = parser.parse_args()

    if not TASKS_FILE.exists():
        print(f"❌ Tasks file not found: {TASKS_FILE}")
        return

    print(f"📂 Loading tasks from: {TASKS_FILE}")
    tasks = json.loads(TASKS_FILE.read_text())

    total_files = 0
    processed_tasks = 0

    for task_id, task_data in tasks.items():
        task_desc = task_data.get("task", "")

        # Apply filter if specified
        if args.task_filter and args.task_filter.lower() not in task_desc.lower():
            continue

        # Only process build tasks with subtasks
        if task_data.get("phase_type") != "build":
            continue

        subtasks = task_data.get("subtasks", [])
        if not subtasks:
            continue

        print(f"\n🔧 Task: {task_id}")
        print(f"   Description: {task_desc[:80]}...")
        processed_tasks += 1

        for sub in subtasks:
            result = sub.get("result", "")
            if not result or "```" not in result:
                continue

            mock_subtask = MockSubtask(
                description=sub.get("description", ""),
                marker=sub.get("marker", "")
            )

            print(f"\n   📝 Subtask: {mock_subtask.description[:60]}...")
            files = extract_and_write_files(result, mock_subtask, dry_run=args.dry_run)
            total_files += len(files)

    print(f"\n{'='*50}")
    print(f"📊 Summary:")
    print(f"   Tasks processed: {processed_tasks}")
    print(f"   Files {'would be ' if args.dry_run else ''}created: {total_files}")

    if args.dry_run:
        print("\n💡 Run without --dry-run to actually create the files")


if __name__ == "__main__":
    main()
