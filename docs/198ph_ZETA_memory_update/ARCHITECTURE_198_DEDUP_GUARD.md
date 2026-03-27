# Architecture: Task Dedup Guard — Duplicate Detection + Priority Boost

**Author:** Zeta | **Phase:** 198 | **Status:** RECON
**Task:** tb_1774433959_1

---

## Problem

329+ pending tasks accumulate duplicates. Multiple agents create overlapping tasks
without checking existing ones. QA wastes cycles verifying phantom or redundant work.

### Empirical Evidence (scan 2026-03-25)

| Metric | Value |
|--------|-------|
| Active tasks (pending/claimed/needs_fix) | 359 |
| Duplicate pairs (similarity > 0.6) | 62 |
| Distinct duplicate clusters | 12 |
| Worst cluster | 10 clones of `[DEBRIEF-IDEA] Read FCP7 PDF before coding` |

**Primary source:** debrief pipeline (`[DEBRIEF-IDEA]`, `[DEBRIEF-BUG]` prefixed tasks).
Batch-import ran across sessions without dedup check.
Agents independently file same observation → 3-way clusters for bugs like
`EFFECT_APPLY_MAP not exported` and `ExportDialog monochrome violation`.
Also: 3x `[BUG] None` — empty debrief Q1 answers creating phantom tasks.

## Core Insight

**A duplicate is not an error — it's a signal of importance.**

When an agent independently arrives at the same task idea, it means:
1. The task has high cross-domain visibility (multiple roles notice the gap)
2. Priority should be boosted (convergent demand)
3. The new perspective enriches the existing task (different docs, description angle)

## Design: Dedup Guard in `add_task`

### Flow

```
Agent calls action=add(title, description, docs...)
         │
         ▼
  ┌─────────────────┐
  │ Normalize title  │  Strip prefixes (ZETA-FIX:, ALPHA-MISSION:, 189.1:)
  │ + description    │  Lowercase, remove punctuation
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ Fuzzy match vs   │  Active pool: pending, claimed, needs_fix, queued
  │ active tasks     │  Using difflib.SequenceMatcher on normalized titles
  └────────┬────────┘
           │
     ┌─────┴──────┐
     │ similarity  │
     └─────┬──────┘
           │
    < 0.55 │  No match → create normally
           │
  0.55-0.8 │  WARN → create, but return `dedup_warnings` with matches
           │         Agent/Commander can decide to merge manually
           │
    > 0.8  │  ENRICH → Don't create new task. Instead:
           │  1. Boost existing task priority by -1 (min 1)
           │  2. Append new description to existing (as "--- Enrichment ---")
           │  3. Merge docs (union of architecture_docs + recon_docs)
           │  4. Record enrichment in status_history
           │  5. Return existing task_id + enrichment summary
```

### Title Normalization

```python
import re

_PREFIX_RE = re.compile(
    r'^(?:'
    r'[A-Z]+-(?:FIX|MISSION|GUARD|RECON|P\d+|T\d+):\s*'  # ZETA-FIX:, ALPHA-MISSION:
    r'|\d{3}\.\d+:\s*'                                      # 189.1:, 197.12:
    r'|MERGE-REQUEST:\s*'                                    # MERGE-REQUEST:
    r'|[A-Z]\d+\.\d+:\s*'                                   # A1.2:
    r')',
    re.IGNORECASE,
)

def _normalize_title(title: str) -> str:
    """Strip agent prefixes, phase numbers, lowercase."""
    title = _PREFIX_RE.sub('', title).strip()
    # Remove trailing markers like [task:tb_xxx]
    title = re.sub(r'\[task:[^\]]+\]', '', title).strip()
    return title.lower()
```

### Matching Strategy

```python
from difflib import SequenceMatcher

def _find_duplicates(
    new_title: str,
    active_tasks: List[Dict],
    threshold: float = 0.55,
) -> List[Tuple[Dict, float]]:
    """Find active tasks similar to new_title.

    Returns list of (task, similarity) sorted by score descending.
    """
    norm_new = _normalize_title(new_title)
    matches = []
    for task in active_tasks:
        norm_existing = _normalize_title(task["title"])
        score = SequenceMatcher(None, norm_new, norm_existing).ratio()
        if score >= threshold:
            matches.append((task, score))
    return sorted(matches, key=lambda x: -x[1])
```

### Enrichment Merge Strategy

When similarity > 0.8:

| Field | Strategy |
|-------|----------|
| priority | `min(existing, new, existing - 1)` — boost by 1 level |
| description | Append under `\n\n--- Enrichment (by {role}, {date}) ---\n{new_desc}` |
| architecture_docs | Union (deduplicated) |
| recon_docs | Union (deduplicated) |
| implementation_hints | Append if different |
| tags | Union |
| completion_contract | Union |

Fields NOT merged: title (keep original), allowed_paths (keep original scope),
role/domain (keep original owner).

### API Contract

**Normal create (no match):**
```json
{"success": true, "task_id": "tb_xxx", "dedup": null}
```

**Warn (0.55–0.8):**
```json
{
  "success": true,
  "task_id": "tb_xxx",
  "dedup": {
    "action": "warn",
    "matches": [
      {"task_id": "tb_yyy", "title": "...", "similarity": 0.72, "status": "pending"}
    ],
    "hint": "Similar task exists. Consider enriching tb_yyy instead."
  }
}
```

**Enrich (>0.8):**
```json
{
  "success": true,
  "task_id": "tb_yyy",
  "dedup": {
    "action": "enriched",
    "original_task_id": "tb_yyy",
    "similarity": 0.91,
    "priority_before": 3,
    "priority_after": 2,
    "fields_enriched": ["description", "architecture_docs"],
    "hint": "Merged into existing task tb_yyy (priority boosted 3→2)"
  }
}
```

### Bypass

`force_no_dedup=true` — skip duplicate check entirely.
Use for: intentional splits, subtasks, tasks with same title but different scope.

### Performance

Active pool ~330 tasks. SequenceMatcher on 330 short strings = <10ms.
No index needed. If pool grows to 1000+, consider pre-computing trigram index.

### Edge Cases

1. **Same title, different project_id** — still match but lower threshold (0.7 for warn, 0.9 for enrich)
2. **Closed duplicates** — only match against active pool (pending/claimed/needs_fix/queued)
3. **Enrichment of enrichment** — cap at 3 enrichments per task to prevent bloat
4. **Priority already at 1** — can't boost further, log but don't change

---

## Implementation Plan

1. Add `_normalize_title()` and `_find_duplicates()` to `task_board.py`
2. Add `_enrich_existing_task()` merge logic
3. Hook into `add_task()` — call before creating, return early if enriched
4. Wire through `task_board_tools.py` — pass `force_no_dedup` param
5. Tests: exact dup, near dup, different project, bypass, enrichment cap

## Originality Score

Side benefit: the similarity score is an **originality metric**.
- Score 0.0 = completely novel idea
- Score 0.5 = related but distinct
- Score 0.9 = near-duplicate (convergent thinking)

Could be surfaced in Commander's task board summary as a signal.
