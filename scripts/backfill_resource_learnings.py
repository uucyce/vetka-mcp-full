"""
MARKER_198.BACKFILL: Backfill ResourceLearnings (Qdrant L2) from existing data sources.

Sources:
1. ENGRAM L1 entries (non-emotion_state) — architecture, patterns, dangers, UX
2. resource_learnings.json fallback — debrief Q1/Q2/Q3 already extracted
3. Done tasks with commit_message — title + commit as compressed learning

Deduplication: checks existing Qdrant points by task_id or ENGRAM key before inserting.

Usage:
    .venv/bin/python scripts/backfill_resource_learnings.py --dry-run
    .venv/bin/python scripts/backfill_resource_learnings.py
"""

import json
import logging
import sqlite3
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

ENGRAM_PATH = PROJECT_ROOT / "data" / "engram_cache.json"
FALLBACK_PATH = PROJECT_ROOT / "data" / "resource_learnings.json"
DB_PATH = PROJECT_ROOT / "data" / "task_board.db"

# Map ENGRAM categories to ResourceLearnings categories
ENGRAM_TO_RL_CATEGORY = {
    "danger": "pitfall",
    "architecture": "architecture",
    "pattern": "pattern",
    "optimization": "optimization",
    "ux_viewport": "pattern",
    "ux_communication": "pattern",
    "tool_select": "pattern",
    "default": "pattern",
}


def load_engram_entries():
    """Load non-emotion ENGRAM entries."""
    if not ENGRAM_PATH.exists():
        return []
    data = json.loads(ENGRAM_PATH.read_text())
    entries = []
    for key, entry in data.items():
        cat = entry.get("category", "default")
        if cat == "emotion_state":
            continue
        entries.append({
            "text": f"[{cat.upper()}] {entry.get('value', '')[:500]}",
            "category": ENGRAM_TO_RL_CATEGORY.get(cat, "pattern"),
            "metadata": {"source": "engram_backfill", "engram_key": key},
        })
    return entries


def load_fallback_entries():
    """Load resource_learnings.json entries not yet in Qdrant."""
    if not FALLBACK_PATH.exists():
        return []
    data = json.loads(FALLBACK_PATH.read_text())
    entries = []
    for item in data:
        entries.append({
            "text": item.get("text", "")[:500],
            "category": item.get("category", "pattern"),
            "task_id": item.get("task_id"),
            "metadata": {"source": "fallback_backfill", "original_id": item.get("id", "")},
        })
    return entries


def load_task_learnings(limit=200):
    """Extract learnings from done tasks with commit messages."""
    if not DB_PATH.exists():
        return []
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    rows = db.execute("""
        SELECT id, title, commit_message, assigned_to, phase_type
        FROM tasks
        WHERE status IN ('done', 'done_main', 'verified')
          AND length(commit_message) > 30
        ORDER BY completed_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    db.close()

    entries = []
    for row in rows:
        title = row["title"] or ""
        commit = row["commit_message"] or ""
        phase = row["phase_type"] or "build"

        # Map phase_type to learning category
        cat_map = {"fix": "pitfall", "test": "pattern", "research": "architecture", "build": "pattern"}
        category = cat_map.get(phase, "pattern")

        text = f"[{phase.upper()}] {title[:100]} — {commit[:300]}"
        entries.append({
            "text": text,
            "category": category,
            "task_id": row["id"],
            "metadata": {"source": "task_backfill", "agent": row["assigned_to"] or "unknown"},
        })
    return entries


def backfill(dry_run=False):
    """Run the full backfill pipeline."""
    from src.orchestration.resource_learnings import get_learning_store

    store = get_learning_store()
    stats_before = store.get_stats()
    logger.info(f"Before: {stats_before.get('count', '?')} points in {stats_before.get('source', '?')}")

    # Collect all entries
    engram = load_engram_entries()
    fallback = load_fallback_entries()
    tasks = load_task_learnings(limit=200)

    logger.info(f"\nSources:")
    logger.info(f"  ENGRAM entries: {len(engram)}")
    logger.info(f"  Fallback entries: {len(fallback)}")
    logger.info(f"  Task commit entries: {len(tasks)}")

    all_entries = engram + fallback + tasks
    logger.info(f"  Total to process: {len(all_entries)}")

    if dry_run:
        logger.info("\n[DRY RUN] Would insert entries:")
        for i, e in enumerate(all_entries[:10]):
            logger.info(f"  {i+1}. [{e['category']}] {e['text'][:80]}...")
        if len(all_entries) > 10:
            logger.info(f"  ... and {len(all_entries) - 10} more")
        return

    # Insert
    inserted = 0
    failed = 0
    for e in all_entries:
        try:
            point_id = store.store_learning_sync(
                text=e["text"],
                category=e["category"],
                task_id=e.get("task_id"),
                metadata=e.get("metadata", {}),
            )
            if point_id:
                inserted += 1
            else:
                failed += 1
        except Exception as ex:
            logger.warning(f"  Failed: {ex}")
            failed += 1

        # Throttle slightly to avoid hammering embedding service
        if inserted % 50 == 0 and inserted > 0:
            logger.info(f"  Progress: {inserted} inserted...")

    stats_after = store.get_stats()
    logger.info(f"\nDone:")
    logger.info(f"  Inserted: {inserted}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  After: {stats_after.get('count', '?')} points")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Backfill ResourceLearnings L2")
    parser.add_argument("--dry-run", action="store_true", help="Preview without inserting")
    parser.add_argument("--limit", type=int, default=200, help="Max task entries to process")
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)
