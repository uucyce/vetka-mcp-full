#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.orchestration.task_board import get_task_board


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: import_taskboard_pack.py <pack.json>")
        return 2
    pack_path = Path(argv[1]).resolve()
    rows = json.loads(pack_path.read_text())
    if not isinstance(rows, list):
        raise SystemExit("pack must be a JSON list")

    board = get_task_board()
    existing = list(board.tasks.values())
    created = []
    skipped = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        workflow_family = str(row.get("workflow_family") or "").strip()
        task_origin = str(row.get("task_origin") or "").strip()
        duplicate = next(
            (
                task for task in existing
                if str(task.get("title") or "").strip() == title
                and str(task.get("workflow_family") or "").strip() == workflow_family
                and str(task.get("task_origin") or "").strip() == task_origin
            ),
            None,
        )
        if duplicate is not None:
            skipped.append({"title": title, "task_id": duplicate.get("id")})
            continue
        task_id = board.add_task(
            title=title,
            description=str(row.get("description") or "").strip(),
            priority=int(row.get("priority", 3) or 3),
            phase_type=str(row.get("phase_type") or "build").strip() or "build",
            preset=row.get("preset"),
            tags=list(row.get("tags") or []),
            dependencies=list(row.get("dependencies") or []),
            source=str(row.get("source") or "phase177_pack").strip() or "phase177_pack",
            created_by=str(row.get("created_by") or "codex").strip() or "codex",
            workflow_family=row.get("workflow_family"),
            workflow_selection_origin=row.get("workflow_selection_origin"),
            team_profile=row.get("team_profile"),
            task_origin=row.get("task_origin"),
            roadmap_id=row.get("roadmap_id"),
            roadmap_node_id=row.get("roadmap_node_id"),
            roadmap_lane=row.get("roadmap_lane"),
            roadmap_title=row.get("roadmap_title"),
        )
        created.append({"title": title, "task_id": task_id})
        existing.append(board.get_task(task_id) or {"id": task_id, "title": title})

    print(json.dumps({"success": True, "created": created, "skipped": skipped, "count_created": len(created), "count_skipped": len(skipped)}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
